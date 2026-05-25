"""
Safety DB 漏洞数据库接口
"""
import os
import json
import requests
import tempfile
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path

from ..models import Dependency, PackageManager


class SafetyDB:
    """Safety DB 漏洞数据库"""

    DEFAULT_DB_URL = "https://raw.githubusercontent.com/pyupio/safety-db/master/data/insecure_full.json"
    CACHE_FILE = "safety_db_cache.json"
    CACHE_TTL = 86400

    def __init__(self, db_path: Optional[str] = None, auto_update: bool = True, use_builtin_only: bool = True):
        self.db_path = db_path or os.path.join(tempfile.gettempdir(), self.CACHE_FILE)
        self.auto_update = auto_update
        self.use_builtin_only = use_builtin_only
        self._db: Dict[str, Any] = {}
        self._remote_db: Dict[str, Any] = {}
        self._loaded = False

    def load(self) -> bool:
        """加载漏洞数据库"""
        if self._loaded:
            return True

        self._db = self._get_builtin_db()

        if not self.use_builtin_only:
            if os.path.exists(self.db_path):
                try:
                    with open(self.db_path, "r", encoding="utf-8") as f:
                        self._remote_db = json.load(f)
                    self._merge_databases()
                except Exception:
                    pass

            if self.auto_update and not self._remote_db:
                if self.update():
                    self._merge_databases()

        self._loaded = True
        return True

    def _merge_databases(self) -> None:
        """合并远程数据库到内置数据库"""
        if not self._remote_db:
            return

        for pkg_name, vulns in self._remote_db.items():
            pkg_lower = pkg_name.lower()
            if pkg_lower in self._db:
                existing_cves = {v.get("cve", "") for v in self._db[pkg_lower]}
                for vuln in vulns:
                    cve = vuln.get("cve", "")
                    if cve and cve not in existing_cves:
                        self._db[pkg_lower].append(vuln)
            else:
                self._db[pkg_lower] = vulns

    def update(self) -> bool:
        """从远程更新漏洞数据库"""
        try:
            response = requests.get(self.DEFAULT_DB_URL, timeout=30)
            response.raise_for_status()
            self._remote_db = response.json()

            os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
            with open(self.db_path, "w", encoding="utf-8") as f:
                json.dump(self._remote_db, f, ensure_ascii=False, indent=2)

            return True
        except Exception as e:
            return False

    def _get_builtin_db(self) -> Dict[str, Any]:
        """获取内置的漏洞数据库（常见漏洞）"""
        return {
            "django": [
                {
                    "v": "<2.2.28,>=2.2,<3.2.16,>=3.2,<4.0.8,>=4.0",
                    "cve": "CVE-2022-34265",
                    "description": "Potential SQL injection via Trunc(kind) and Extract(lookup_name) arguments",
                    "cvss": 7.5,
                },
                {
                    "v": "<3.2.18,>=3.2,<4.0.10,>=4.0,<4.1.3,>=4.1",
                    "cve": "CVE-2023-31047",
                    "description": "Bypass of validation in file uploads",
                    "cvss": 9.8,
                },
            ],
            "flask": [
                {
                    "v": "<2.2.5,>=2.2,<2.3.3,>=2.3",
                    "cve": "CVE-2023-30861",
                    "description": "Possible cookie leak when all cookies are set with the same key",
                    "cvss": 7.5,
                },
            ],
            "requests": [
                {
                    "v": "<2.31.0",
                    "cve": "CVE-2023-32681",
                    "description": "Unintended leak of Proxy-Authorization header",
                    "cvss": 6.1,
                },
            ],
            "lodash": [
                {
                    "v": "<4.17.21",
                    "cve": "CVE-2021-23337",
                    "description": "Command Injection in lodash",
                    "cvss": 7.2,
                },
            ],
            "axios": [
                {
                    "v": "<0.21.2,>=0.21.0,<0.22.0",
                    "cve": "CVE-2021-3749",
                    "description": "Regular Expression Denial of Service",
                    "cvss": 7.5,
                },
                {
                    "v": "<0.25.0",
                    "cve": "CVE-2023-45857",
                    "description": "Axios Cross-Site Request Forgery",
                    "cvss": 6.5,
                },
            ],
            "log4j-core": [
                {
                    "v": "<2.16.0,>=2.0-beta9",
                    "cve": "CVE-2021-44228",
                    "description": "Log4Shell - Remote code injection in Log4j",
                    "cvss": 10.0,
                },
                {
                    "v": "<2.17.1,>=2.0-beta9",
                    "cve": "CVE-2021-44832",
                    "description": "Remote code execution via JDBC Appender",
                    "cvss": 6.6,
                },
            ],
            "spring-core": [
                {
                    "v": "<5.2.20,>=5.2.0,<5.3.18,>=5.3.0",
                    "cve": "CVE-2022-22965",
                    "description": "Spring4Shell - Remote code execution via data binding",
                    "cvss": 9.8,
                },
            ],
            "struts2-core": [
                {
                    "v": "<2.3.32,>=2.0.0,<2.5.10.1,>=2.5",
                    "cve": "CVE-2017-5638",
                    "description": "Remote code execution via Jakarta Multipart parser",
                    "cvss": 10.0,
                },
            ],
            "golang.org/x/net": [
                {
                    "v": "<0.17.0",
                    "cve": "CVE-2023-39325",
                    "description": "HTTP/2 rapid reset attack",
                    "cvss": 7.5,
                },
            ],
        }

    def get_vulnerabilities_for_package(
        self, package_name: str, package_manager: PackageManager
    ) -> List[Dict[str, Any]]:
        """获取指定包的漏洞列表"""
        if not self._loaded:
            self.load()

        lookup_names = self._get_lookup_names(package_name, package_manager)

        vulnerabilities = []
        for name in lookup_names:
            name_lower = name.lower()
            if name_lower in self._db:
                for vuln in self._db[name_lower]:
                    vuln_copy = dict(vuln)
                    vuln_copy["package"] = name
                    vulnerabilities.append(vuln_copy)

        return vulnerabilities

    def _get_lookup_names(self, package_name: str, package_manager: PackageManager) -> List[str]:
        """获取用于查询的包名变体"""
        names = [package_name]

        name_lower = package_name.lower()
        names.append(name_lower)

        base_name = package_name.split("/")[-1]
        if base_name != package_name:
            names.append(base_name)
            names.append(base_name.lower())

        if package_manager == PackageManager.MAVEN:
            parts = package_name.split(":")
            if len(parts) >= 2:
                artifact_id = parts[-1]
                names.append(artifact_id)
                names.append(artifact_id.lower())
                group_id = parts[-2] if len(parts) >= 2 else ""
                if group_id:
                    group_parts = group_id.split(".")
                    for part in group_parts:
                        combined = f"{part}:{artifact_id}"
                        names.append(combined)
                        names.append(combined.lower())

        if package_manager == PackageManager.GO:
            parts = package_name.split("/")
            if len(parts) >= 2:
                short_name = "/".join(parts[-2:])
                names.append(short_name)
                names.append(short_name.lower())
                names.append(parts[-1])
                names.append(parts[-1].lower())

        if package_manager == PackageManager.NPM:
            if package_name.startswith("@"):
                scope_parts = package_name.split("/")
                if len(scope_parts) >= 2:
                    names.append(scope_parts[-1])
                    names.append(scope_parts[-1].lower())

        normalized = package_name.replace("_", "-").replace(".", "-")
        if normalized != package_name:
            names.append(normalized)
            names.append(normalized.lower())

        return list(set(names))

    def check_dependency(self, dependency: Dependency) -> List[Dict[str, Any]]:
        """检查单个依赖的漏洞"""
        from .version_utils import is_version_affected

        vulnerabilities = []
        pkg_vulns = self.get_vulnerabilities_for_package(
            dependency.full_name, dependency.package_manager
        )

        for vuln in pkg_vulns:
            version_range = vuln.get("v", "")
            if is_version_affected(dependency.version, [version_range]):
                vulnerabilities.append(vuln)

        return vulnerabilities

    def check_dependencies(self, dependencies: List[Dependency]) -> Dict[str, List[Dict[str, Any]]]:
        """批量检查依赖漏洞"""
        results = {}
        for dep in dependencies:
            vulns = self.check_dependency(dep)
            if vulns:
                results[dep.full_name] = vulns
        return results
