import os
import re
import copy
import requests
import yaml
from typing import Dict, Any, List, Optional


class APITestRunner:
    def __init__(self):
        self.session = requests.Session()
        self.variables: Dict[str, Any] = {}
        self.test_results: List[Dict[str, Any]] = []
        self._base_url: str = ""
        self._config: Dict[str, Any] = {}
        self._param_datasets: Dict[str, List[Dict[str, Any]]] = {}

    def load_config(self) -> Dict[str, Any]:
        data_file = os.path.join(os.path.dirname(__file__), "test_data.yaml")
        with open(data_file, "r", encoding="utf-8") as f:
            self._config = yaml.safe_load(f) or {}

        self._base_url = self._config.get("base_url", "")

        global_vars = self._config.get("global_variables", {})
        self.variables.update(global_vars)

        datasets = self._config.get("param_datasets", [])
        for ds in datasets:
            self._param_datasets[ds["dataset_name"]] = ds.get("params", [])

        return self._config

    def _resolve_placeholder(self, value: Any) -> Any:
        if isinstance(value, str):
            pattern = r'\$\{([^}]+)\}'
            matches = re.findall(pattern, value)
            for var_name in matches:
                if var_name in self.variables:
                    var_value = str(self.variables[var_name])
                    value = value.replace(f'${{{var_name}}}', var_value)
                else:
                    raise ValueError(f"变量 {var_name} 未定义，可用变量: {list(self.variables.keys())}")
            return value
        elif isinstance(value, dict):
            return {k: self._resolve_placeholder(v) for k, v in value.items()}
        elif isinstance(value, list):
            return [self._resolve_placeholder(v) for v in value]
        return value

    def _extract_variables(self, response: requests.Response, extract_config: Dict[str, str]) -> None:
        if not extract_config:
            return

        import json
        try:
            response_json = response.json()
        except json.JSONDecodeError:
            response_json = None

        for var_name, json_path in extract_config.items():
            try:
                value = self._get_value_by_json_path(response_json, json_path)
                self.variables[var_name] = value
            except Exception as e:
                raise ValueError(f"提取变量 {var_name} 失败，路径 {json_path}: {e}")

    def _get_value_by_json_path(self, data: Any, path: str) -> Any:
        if not data:
            raise ValueError("响应数据为空")

        keys = self._parse_json_path(path)
        current = data

        for key in keys:
            if isinstance(current, dict):
                if key not in current:
                    raise ValueError(f"路径 '{path}' 在 {key} 处不存在")
                current = current[key]
            elif isinstance(current, list):
                try:
                    idx = int(key)
                    current = current[idx]
                except ValueError:
                    raise ValueError(f"路径 '{path}' 在列表索引 {key} 处无效")
                except IndexError:
                    raise ValueError(f"路径 '{path}' 索引 {key} 超出范围")
            else:
                raise ValueError(f"路径 '{path}' 在 {key} 处无法继续深入")

        return current

    def _parse_json_path(self, path: str) -> List[str]:
        path = path.strip()
        if path.startswith('$.'):
            path = path[2:]
        elif path.startswith('$'):
            path = path[1:]

        parts = []
        current = ''
        i = 0

        while i < len(path):
            c = path[i]
            if c == '.':
                if current:
                    parts.append(current)
                    current = ''
                i += 1
            elif c == '[':
                if current:
                    parts.append(current)
                    current = ''
                j = i + 1
                while j < len(path) and path[j] != ']':
                    current += path[j]
                    j += 1
                parts.append(current.strip().strip('"\''))
                current = ''
                i = j + 1
            else:
                current += c
                i += 1

        if current:
            parts.append(current)

        return parts

    def _check_dependencies(self, test_case: Dict[str, Any], executed_names: set) -> None:
        depends_on = test_case.get("depends_on", [])
        if isinstance(depends_on, str):
            depends_on = [depends_on]

        for dep in depends_on:
            if dep not in executed_names:
                raise ValueError(f"测试用例 '{test_case.get('name')}' 依赖 '{dep}'，但该用例未执行")

    def _expand_parametrized_test(self, test_case: Dict[str, Any]) -> List[Dict[str, Any]]:
        parametrize = test_case.get("parametrize")
        if not parametrize:
            return [test_case]

        dataset_name = parametrize.get("dataset")
        if not dataset_name or dataset_name not in self._param_datasets:
            return [test_case]

        dataset = self._param_datasets[dataset_name]
        expanded = []

        for idx, params in enumerate(dataset):
            tc = copy.deepcopy(test_case)
            param_name = params.get("name", f"param_{idx}")
            tc["name"] = f"{test_case['name']} [{param_name}]"

            tc_placeholders = copy.deepcopy(tc)
            for key, value in params.items():
                if key != "name":
                    if key not in self.variables:
                        self.variables[key] = value

            expanded.append(tc)

        return expanded

    def _run_db_checks(self, test_case: Dict[str, Any]) -> List[Dict[str, Any]]:
        from db_check import db_assertions, DatabaseConnectionError, DatabaseQueryError

        db_checks = test_case.get("db_checks", [])
        check_results = []

        if not db_checks:
            return check_results

        db_config = self._config.get("database", {})
        if not db_config.get("enabled", False):
            for check in db_checks:
                check_results.append({
                    "name": check.get("name", "db_check"),
                    "status": "skipped",
                    "error": "数据库校验未启用"
                })
            return check_results

        for check in db_checks:
            name = check.get("name", "db_check")
            sql = check.get("sql")
            assertions = check.get("assertions", [])

            result = {"name": name, "status": "passed", "error": None}

            try:
                resolved_sql = self._resolve_placeholder(sql)
                db_assertions.run_db_assertions(resolved_sql, assertions)
            except DatabaseConnectionError as e:
                result["status"] = "failed"
                result["error"] = f"数据库连接失败: {e}"
            except DatabaseQueryError as e:
                result["status"] = "failed"
                result["error"] = f"SQL 执行失败: {e}"
            except AssertionError as e:
                result["status"] = "failed"
                result["error"] = str(e)
            except Exception as e:
                result["status"] = "failed"
                result["error"] = f"数据库校验出错: {e}"

            check_results.append(result)

        return check_results

    def _run_single_test(self, test_case: Dict[str, Any]) -> Dict[str, Any]:
        from assertions import api_assertions

        name = test_case.get("name", "unnamed")
        result = {
            "name": name,
            "method": test_case.get("method", "GET"),
            "endpoint": test_case.get("endpoint", ""),
            "status": "passed",
            "error": None,
            "response_time_ms": 0,
            "db_checks": []
        }

        try:
            resolved_test_case = self._resolve_placeholder(test_case)

            method = resolved_test_case.get("method", "GET").upper()
            endpoint = resolved_test_case.get("endpoint", "")
            url = f"{self._base_url}{endpoint}"
            params = resolved_test_case.get("params")
            data = resolved_test_case.get("data")
            headers = resolved_test_case.get("headers")
            assertions = resolved_test_case.get("assertions", [])
            extract = resolved_test_case.get("extract")

            kwargs = {}
            if params:
                kwargs["params"] = params
            if data:
                kwargs["json"] = data
            if headers:
                kwargs["headers"] = headers

            env_config = self._config.get("env", {})
            timeout = env_config.get("timeout", 30)
            max_retries = env_config.get("max_retries", 0)

            response = None
            last_error = None

            for attempt in range(max_retries + 1):
                try:
                    response = self.session.request(
                        method=method,
                        url=url,
                        timeout=timeout,
                        **kwargs
                    )
                    break
                except Exception as e:
                    last_error = e
                    if attempt < max_retries:
                        continue
                    raise

            if response is None:
                raise last_error or Exception("请求失败")

            result["response_time_ms"] = response.elapsed.total_seconds() * 1000
            result["status_code"] = response.status_code

            api_assertions.run_assertions(response, assertions)

            if extract:
                self._extract_variables(response, extract)

            db_check_results = self._run_db_checks(resolved_test_case)
            result["db_checks"] = db_check_results

            failed_db_checks = [c for c in db_check_results if c["status"] == "failed"]
            if failed_db_checks:
                result["status"] = "failed"
                result["error"] = "; ".join([f"{c['name']}: {c['error']}" for c in failed_db_checks])

        except Exception as e:
            result["status"] = "failed"
            result["error"] = str(e)

        return result

    def run_all_tests(self) -> List[Dict[str, Any]]:
        self.load_config()
        test_cases = self._config.get("test_cases", [])

        self.test_results = []
        executed_names = set()

        for test_case in test_cases:
            try:
                self._check_dependencies(test_case, executed_names)
            except Exception as e:
                self.test_results.append({
                    "name": test_case.get("name", "unnamed"),
                    "method": test_case.get("method", "GET"),
                    "endpoint": test_case.get("endpoint", ""),
                    "status": "skipped",
                    "error": str(e),
                    "response_time_ms": 0
                })
                continue

            expanded_cases = self._expand_parametrized_test(test_case)

            all_passed = True
            for param_case in expanded_cases:
                result = self._run_single_test(param_case)
                self.test_results.append(result)

                if result["status"] != "passed":
                    all_passed = False

            if all_passed:
                executed_names.add(test_case.get("name"))
            elif test_case.get("stop_on_failure", True):
                break

        return self.test_results


def test_api_flow():
    runner = APITestRunner()
    results = runner.run_all_tests()

    passed = sum(1 for r in results if r["status"] == "passed")
    failed = sum(1 for r in results if r["status"] == "failed")
    skipped = sum(1 for r in results if r["status"] == "skipped")

    print(f"\n{'='*60}")
    print(f"测试结果汇总: 通过={passed}, 失败={failed}, 跳过={skipped}")
    print(f"{'='*60}")

    for r in results:
        status_icon = "✓" if r["status"] == "passed" else "✗" if r["status"] == "failed" else "⏭"
        print(f"{status_icon} {r['name']} [{r['method']} {r['endpoint']}] -> {r['status'].upper()}")
        if r["error"]:
            print(f"    错误: {r['error']}")
        if r.get("db_checks"):
            for dbc in r["db_checks"]:
                db_icon = "✓" if dbc["status"] == "passed" else "✗" if dbc["status"] == "failed" else "⏭"
                print(f"    {db_icon} 数据库校验: {dbc['name']} -> {dbc['status'].upper()}")
                if dbc["error"]:
                    print(f"        错误: {dbc['error']}")

    assert failed == 0, f"有 {failed} 个测试用例失败"


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
