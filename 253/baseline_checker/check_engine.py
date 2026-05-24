import re
import logging
import yaml
from typing import Dict, List, Optional, Any
from .ssh_client import SSHClient

logger = logging.getLogger(__name__)


class ValueNormalizer:
    UNIT_MULTIPLIERS = {
        'bytes': 1, 'b': 1,
        'kb': 1024, 'k': 1024,
        'mb': 1024 * 1024, 'm': 1024 * 1024,
        'gb': 1024 * 1024 * 1024, 'g': 1024 * 1024 * 1024,
        'seconds': 1, 'sec': 1, 's': 1,
        'minutes': 60, 'min': 60,
        'hours': 3600, 'h': 3600,
        'days': 86400, 'd': 86400,
    }

    @classmethod
    def parse_value(cls, value: str, unit_type: str = None) -> Optional[float]:
        if value is None or value == '':
            return None

        value = str(value).strip().lower()

        match = re.match(r'^([\d.]+)\s*([a-zA-Z]*)$', value)
        if not match:
            try:
                return float(value)
            except ValueError:
                return None

        num = float(match.group(1))
        unit = match.group(2)

        if unit and unit in cls.UNIT_MULTIPLIERS:
            return num * cls.UNIT_MULTIPLIERS[unit]

        return num

    @classmethod
    def to_bytes(cls, value: str) -> Optional[float]:
        return cls.parse_value(value, 'bytes')

    @classmethod
    def to_seconds(cls, value: str) -> Optional[float]:
        return cls.parse_value(value, 'seconds')

    @classmethod
    def normalize_values(cls, actual: str, expected: str, unit_type: str = None) -> tuple:
        actual_norm = cls.parse_value(actual, unit_type)
        expected_norm = cls.parse_value(expected, unit_type)
        return actual_norm, expected_norm


class SSHConfigParser:
    @staticmethod
    def parse(content: str) -> Dict[str, Any]:
        config = {}
        if not content:
            return config

        for line in content.split('\n'):
            line = line.strip()
            if not line or line.startswith('#'):
                continue

            match = re.match(r'^(\w+)\s+(.+)$', line)
            if match:
                key = match.group(1)
                value = match.group(2).strip()

                if key in config:
                    if isinstance(config[key], list):
                        config[key].append(value)
                    else:
                        config[key] = [config[key], value]
                else:
                    config[key] = value

        return config

    @staticmethod
    def get_port(config: Dict[str, Any]) -> List[int]:
        ports = []
        port_value = config.get('Port', '22')

        if isinstance(port_value, list):
            for p in port_value:
                try:
                    ports.append(int(p))
                except ValueError:
                    pass
        else:
            try:
                ports.append(int(port_value))
            except ValueError:
                ports.append(22)

        return ports if ports else [22]

    @staticmethod
    def get_listen_address(config: Dict[str, Any]) -> List[str]:
        addresses = []
        addr_value = config.get('ListenAddress', '0.0.0.0')

        if isinstance(addr_value, list):
            addresses = addr_value
        else:
            addresses = [addr_value]

        return addresses


class CheckEngine:
    def __init__(self, ssh_client: SSHClient, baseline_template: str):
        self.ssh_client = ssh_client
        self.baseline = self._load_baseline(baseline_template)
        self.results: List[Dict] = []
        self._sshd_config_cache: Optional[Dict[str, Any]] = None

    def _load_baseline(self, template_path: str) -> Dict:
        try:
            with open(template_path, "r", encoding="utf-8") as f:
                return yaml.safe_load(f)
        except Exception as e:
            logger.error(f"Failed to load baseline template: {str(e)}")
            raise

    def _get_sshd_config(self) -> Dict[str, Any]:
        if self._sshd_config_cache is None:
            content = self.ssh_client.read_file("/etc/ssh/sshd_config")
            self._sshd_config_cache = SSHConfigParser.parse(content)
        return self._sshd_config_cache

    def run_all_checks(self, categories: Optional[List[str]] = None) -> List[Dict]:
        self.results = []
        checks = self.baseline.get("checks", {})

        if categories:
            check_categories = {k: v for k, v in checks.items() if k in categories}
        else:
            check_categories = checks

        for category, category_checks in check_categories.items():
            logger.info(f"Running checks for category: {category}")
            for check in category_checks:
                result = self._run_single_check(check)
                result["category"] = category
                self.results.append(result)

        return self.results

    def _run_single_check(self, check: Dict) -> Dict:
        check_id = check.get("id")
        check_name = check.get("name")
        check_type = check.get("check_type")
        severity = check.get("severity", "medium")
        warn_only = check.get("warn_only", False)

        result = {
            "id": check_id,
            "name": check_name,
            "severity": severity,
            "check_type": check_type,
            "status": "unknown",
            "actual_value": "",
            "expected_value": check.get("expected_value", ""),
            "description": check.get("description", ""),
            "fix_command": check.get("fix_command", ""),
            "warn_only": warn_only,
            "message": ""
        }

        try:
            check_handlers = {
                "file_content": self._check_file_content,
                "file_permission": self._check_file_permission,
                "sysctl": self._check_sysctl,
                "command": self._check_command,
                "service_status": self._check_service_status,
                "ssh_config": self._check_ssh_config,
                "port_listening": self._check_port_listening,
                "regex_match": self._check_regex_match,
            }

            handler = check_handlers.get(check_type)
            if handler:
                handler(check, result)
            else:
                result["status"] = "skipped"
                result["message"] = f"Unknown check type: {check_type}"
        except Exception as e:
            result["status"] = "error"
            result["message"] = f"Check failed with error: {str(e)}"
            logger.error(f"Check {check_id} failed: {str(e)}")

        return result

    def _check_file_content(self, check: Dict, result: Dict):
        file_path = check["file_path"]
        pattern = check["pattern"]
        expected = check["expected_value"]
        match_type = check.get("match_type", "exact")

        content = self.ssh_client.read_file(file_path)
        if content is None:
            result["status"] = "error"
            result["message"] = f"Cannot read file: {file_path}"
            return

        matches = re.findall(pattern, content, re.MULTILINE)
        if not matches:
            result["status"] = "fail"
            result["actual_value"] = "Not found"
            result["message"] = f"Pattern '{pattern}' not found in {file_path}"
            return

        actual_value = matches[0].strip()
        result["actual_value"] = actual_value

        self._compare_values(actual_value, expected, match_type, result)

    def _check_ssh_config(self, check: Dict, result: Dict):
        sshd_key = check.get("sshd_key")
        expected = check["expected_value"]
        match_type = check.get("match_type", "exact")
        allow_multiple = check.get("allow_multiple", False)

        sshd_config = self._get_sshd_config()
        actual_value = sshd_config.get(sshd_key)

        if actual_value is None:
            result["status"] = "fail"
            result["actual_value"] = "Not configured"
            result["message"] = f"SSH config key '{sshd_key}' not found"
            return

        if isinstance(actual_value, list):
            if allow_multiple:
                result["actual_value"] = ", ".join(actual_value)
                for val in actual_value:
                    if self._single_value_match(val, expected, match_type):
                        result["status"] = "pass"
                        return
                result["status"] = "fail"
                result["message"] = f"None of the values match expected: {expected}"
            else:
                result["actual_value"] = actual_value[-1]
                self._compare_values(actual_value[-1], expected, match_type, result)
        else:
            result["actual_value"] = actual_value
            self._compare_values(actual_value, expected, match_type, result)

    def _check_port_listening(self, check: Dict, result: Dict):
        port = check.get("port")
        expected_status = check.get("expected_status", "listening")

        if port is None:
            sshd_config = self._get_sshd_config()
            ports = SSHConfigParser.get_port(sshd_config)
            port = ports[0] if ports else 22

        exit_code, output, _ = self.ssh_client.execute_command(
            f"ss -tlnp | grep -E ':{port}\\b' || netstat -tlnp | grep -E ':{port}\\b' || ss -tln | grep -E ':{port}\\b'"
        )

        is_listening = exit_code == 0 and output.strip()
        result["actual_value"] = f"Port {port}: {'listening' if is_listening else 'not listening'}"

        if expected_status == "listening" and is_listening:
            result["status"] = "pass"
        elif expected_status == "not_listening" and not is_listening:
            result["status"] = "pass"
        else:
            result["status"] = "fail"
            result["message"] = f"Port {port} is {'listening' if is_listening else 'not listening'}, expected {expected_status}"

    def _check_regex_match(self, check: Dict, result: Dict):
        file_path = check.get("file_path", "")
        content = check.get("content", "")
        pattern = check["pattern"]
        expected = check.get("expected_value", "")
        match_type = check.get("match_type", "contains")

        if file_path:
            content = self.ssh_client.read_file(file_path)
            if content is None:
                result["status"] = "error"
                result["message"] = f"Cannot read file: {file_path}"
                return

        if content is None:
            result["status"] = "error"
            result["message"] = "No content to check"
            return

        actual_value = content.strip()
        result["actual_value"] = actual_value[:200]

        match = re.search(pattern, content, re.MULTILINE)

        if match_type == "matches":
            if match:
                result["status"] = "pass"
            else:
                result["status"] = "fail"
                result["message"] = f"Pattern does not match"
        elif match_type == "not_matches":
            if not match:
                result["status"] = "pass"
            else:
                result["status"] = "fail"
                result["message"] = f"Pattern matches but should not"
        else:
            self._compare_values(actual_value, expected, match_type, result)

    def _check_file_permission(self, check: Dict, result: Dict):
        file_path = check["file_path"]
        expected_perm = check.get("expected_permission", "")
        expected_owner = check.get("expected_owner", "")
        expected_group = check.get("expected_group", "")

        stat = self.ssh_client.get_file_stat(file_path)
        if stat is None:
            result["status"] = "error"
            result["message"] = f"Cannot stat file: {file_path}"
            return

        result["actual_value"] = f"perm={stat['permission']}, uid={stat['owner']}, gid={stat['group']}"

        perm_ok = (not expected_perm) or stat["permission"] == expected_perm

        owner_ok = True
        if expected_owner:
            exit_code, output, _ = self.ssh_client.execute_command(
                f"id -u {expected_owner}"
            )
            if exit_code == 0:
                owner_ok = str(stat["owner"]) == output.strip()
            else:
                owner_ok = False

        group_ok = True
        if expected_group:
            exit_code, output, _ = self.ssh_client.execute_command(
                f"getent group {expected_group} | cut -d: -f3"
            )
            if exit_code == 0:
                group_ok = str(stat["group"]) == output.strip()
            else:
                group_ok = False

        if perm_ok and owner_ok and group_ok:
            result["status"] = "pass"
        else:
            result["status"] = "fail"
            issues = []
            if not perm_ok:
                issues.append(f"expected perm={expected_perm}, got {stat['permission']}")
            if not owner_ok:
                issues.append(f"expected owner={expected_owner}")
            if not group_ok:
                issues.append(f"expected group={expected_group}")
            result["message"] = "; ".join(issues)

    def _check_sysctl(self, check: Dict, result: Dict):
        parameter = check["parameter"]
        expected = check["expected_value"]
        unit = check.get("unit")
        compare_type = check.get("compare", "eq")

        exit_code, output, _ = self.ssh_client.execute_command(f"sysctl -n {parameter}")
        if exit_code != 0:
            result["status"] = "error"
            result["message"] = f"Cannot get sysctl parameter: {parameter}"
            return

        actual_value = output.strip()
        result["actual_value"] = actual_value

        if unit:
            actual_norm, expected_norm = ValueNormalizer.normalize_values(actual_value, expected, unit)
            if actual_norm is not None and expected_norm is not None:
                result["actual_value"] = f"{actual_value} (normalized: {actual_norm})"
                result["expected_value"] = f"{expected} (normalized: {expected_norm})"
                self._compare_numeric(actual_norm, expected_norm, compare_type, result)
                return

        self._compare_values(actual_value, expected, "exact", result)

    def _compare_numeric(self, actual: float, expected: float, compare_type: str, result: Dict):
        comparisons = {
            "eq": lambda a, e: a == e,
            "ne": lambda a, e: a != e,
            "gt": lambda a, e: a > e,
            "ge": lambda a, e: a >= e,
            "lt": lambda a, e: a < e,
            "le": lambda a, e: a <= e,
        }

        compare = comparisons.get(compare_type, comparisons["eq"])
        if compare(actual, expected):
            result["status"] = "pass"
        else:
            result["status"] = "fail"
            result["message"] = f"Value {actual} is not {compare_type} {expected}"

    def _check_command(self, check: Dict, result: Dict):
        command = check["command"]
        expected = check.get("expected_output", "")
        match_type = check.get("match_type", "exact")

        exit_code, output, _ = self.ssh_client.execute_command(command)
        actual_value = output.strip()
        result["actual_value"] = actual_value

        if match_type == "exact":
            if actual_value == expected:
                result["status"] = "pass"
            else:
                result["status"] = "fail"
                if actual_value:
                    result["message"] = f"Found issues: {actual_value[:100]}..."
                else:
                    result["message"] = "No output as expected"
                    result["status"] = "pass"
        elif match_type == "contains":
            if expected.lower() in actual_value.lower():
                result["status"] = "pass"
            else:
                result["status"] = "fail"
                result["message"] = f"Output does not contain expected string: {expected}"
        elif match_type == "exists":
            if actual_value:
                result["status"] = "warn"
                result["message"] = f"Found items, please review: {actual_value[:100]}..."
            else:
                result["status"] = "pass"
        elif match_type == "not_exists":
            if not actual_value:
                result["status"] = "pass"
            else:
                result["status"] = "fail"
                result["message"] = f"Found unexpected items: {actual_value[:100]}..."
        elif match_type == "exit_code":
            expected_code = int(expected) if expected else 0
            if exit_code == expected_code:
                result["status"] = "pass"
            else:
                result["status"] = "fail"
                result["message"] = f"Expected exit code {expected_code}, got {exit_code}"

    def _check_service_status(self, check: Dict, result: Dict):
        service_name = check["service_name"]
        expected_status = check.get("expected_status", "active")
        alt_service = check.get("alt_service_name")

        exit_code, output, _ = self.ssh_client.execute_command(
            f"systemctl is-active {service_name}"
        )
        actual_status = output.strip()
        result["actual_value"] = actual_status

        if actual_status == expected_status:
            result["status"] = "pass"
        elif alt_service:
            exit_code, output, _ = self.ssh_client.execute_command(
                f"systemctl is-active {alt_service}"
            )
            if output.strip() == expected_status:
                result["actual_value"] = f"{alt_service}: {output.strip()}"
                result["status"] = "pass"
            else:
                result["status"] = "fail"
                result["message"] = f"Neither {service_name} nor {alt_service} is {expected_status}"
        else:
            result["status"] = "fail"
            result["message"] = f"Service {service_name} is {actual_status}, expected {expected_status}"

    def _single_value_match(self, actual: str, expected: str, match_type: str) -> bool:
        if match_type == "regex":
            return bool(re.match(expected, actual))
        elif match_type == "contains":
            return expected.lower() in actual.lower()
        else:
            return actual == expected

    def _compare_values(self, actual: str, expected: str, match_type: str, result: Dict):
        if match_type == "regex":
            if re.match(expected, actual):
                result["status"] = "pass"
            else:
                result["status"] = "fail"
                result["message"] = f"Value does not match expected pattern: {expected}"
        elif match_type == "contains":
            if expected.lower() in actual.lower():
                result["status"] = "pass"
            else:
                result["status"] = "fail"
                result["message"] = f"Value does not contain expected string: {expected}"
        elif match_type == "not_contains":
            if expected.lower() not in actual.lower():
                result["status"] = "pass"
            else:
                result["status"] = "fail"
                result["message"] = f"Value contains unexpected string: {expected}"
        else:
            if actual == expected:
                result["status"] = "pass"
            else:
                result["status"] = "fail"
                result["message"] = f"Expected '{expected}', got '{actual}'"

    def get_summary(self) -> Dict:
        summary = {
            "total": len(self.results),
            "pass": 0,
            "fail": 0,
            "warn": 0,
            "error": 0,
            "skipped": 0,
            "by_severity": {
                "critical": {"pass": 0, "fail": 0, "warn": 0, "error": 0},
                "high": {"pass": 0, "fail": 0, "warn": 0, "error": 0},
                "medium": {"pass": 0, "fail": 0, "warn": 0, "error": 0},
                "low": {"pass": 0, "fail": 0, "warn": 0, "error": 0}
            },
            "by_category": {}
        }

        for result in self.results:
            status = result["status"]
            severity = result["severity"]
            category = result.get("category", "unknown")

            summary[status] = summary.get(status, 0) + 1

            if severity in summary["by_severity"]:
                summary["by_severity"][severity][status] = \
                    summary["by_severity"][severity].get(status, 0) + 1

            if category not in summary["by_category"]:
                summary["by_category"][category] = {"total": 0, "pass": 0, "fail": 0, "warn": 0, "error": 0}
            summary["by_category"][category]["total"] += 1
            summary["by_category"][category][status] = summary["by_category"][category].get(status, 0) + 1

        return summary

    def get_failed_checks(self, include_warn: bool = False) -> List[Dict]:
        failed = [r for r in self.results if r["status"] == "fail"]
        if include_warn:
            failed.extend([r for r in self.results if r["status"] == "warn"])
        return sorted(failed, key=lambda x: {"critical": 0, "high": 1, "medium": 2, "low": 3}.get(x["severity"], 4))
