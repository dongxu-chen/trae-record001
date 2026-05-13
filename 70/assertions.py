import json
from typing import Any, Dict, List


class JSONPathError(Exception):
    def __init__(self, message: str, path: str = "", data: Any = None):
        super().__init__(message)
        self.path = path
        self.data = data

    def __str__(self):
        return f"JSONPath错误 [路径: {self.path}] - {super().__str__()}"


class APIAssertions:
    def _parse_json_path(self, path: str) -> List[str]:
        try:
            path = path.strip()
            if not path:
                raise JSONPathError("JSONPath 路径为空", path=path)

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
                    if j >= len(path):
                        raise JSONPathError("JSONPath 中缺少闭合的 ']'", path=path)
                    parts.append(current.strip().strip('"\''))
                    current = ''
                    i = j + 1
                else:
                    current += c
                    i += 1

            if current:
                parts.append(current)

            return parts
        except JSONPathError:
            raise
        except Exception as e:
            raise JSONPathError(f"解析 JSONPath 失败: {e}", path=path) from e

    def _get_value_by_json_path(self, data: Any, path: str) -> Any:
        if data is None:
            raise JSONPathError("响应数据为空", path=path)

        if not isinstance(data, (dict, list)):
            raise JSONPathError(f"响应数据不是有效的 JSON 对象或数组", path=path)

        keys = self._parse_json_path(path)
        current = data
        traversed = []

        for idx, key in enumerate(keys):
            traversed.append(key)

            if isinstance(current, dict):
                if key not in current:
                    available_keys = list(current.keys())
                    raise JSONPathError(
                        f"键 '{key}' 不存在于当前节点中。可用键: {available_keys}",
                        path=path
                    )
                current = current[key]
            elif isinstance(current, list):
                try:
                    idx_int = int(key)
                except ValueError:
                    raise JSONPathError(
                        f"数组索引 '{key}' 不是有效整数",
                        path=path
                    )
                try:
                    current = current[idx_int]
                except IndexError:
                    raise JSONPathError(
                        f"数组索引 {idx_int} 超出范围。数组长度: {len(current)}",
                        path=path
                    )
            else:
                raise JSONPathError(
                    f"路径在 '{'.'.join(traversed)}' 处无法继续深入。当前值类型: {type(current).__name__}",
                    path=path
                )

        return current

    def assert_status_code(self, response, expected_status: int) -> None:
        assert response.status_code == expected_status, \
            f"期望状态码 {expected_status}，实际得到 {response.status_code}"

    def assert_json_path_exists(self, response, json_path: str) -> None:
        try:
            response_json = response.json()
        except json.JSONDecodeError:
            raise AssertionError("响应不是有效的 JSON 格式")

        try:
            self._get_value_by_json_path(response_json, json_path)
        except JSONPathError as e:
            raise AssertionError(f"JSONPath 路径不存在: {e}")

    def assert_json_path_value(self, response, json_path: str, expected_value: Any) -> None:
        try:
            response_json = response.json()
        except json.JSONDecodeError:
            raise AssertionError("响应不是有效的 JSON 格式")

        try:
            actual_value = self._get_value_by_json_path(response_json, json_path)
        except JSONPathError as e:
            raise AssertionError(f"JSONPath 错误: {e}")

        assert actual_value == expected_value, \
            f"JSONPath '{json_path}' 的值不匹配。期望: {expected_value}，实际: {actual_value}"

    def assert_json_path_contains(self, response, json_path: str, expected_subset: Any) -> None:
        try:
            response_json = response.json()
        except json.JSONDecodeError:
            raise AssertionError("响应不是有效的 JSON 格式")

        try:
            actual_value = self._get_value_by_json_path(response_json, json_path)
        except JSONPathError as e:
            raise AssertionError(f"JSONPath 错误: {e}")

        if isinstance(actual_value, dict) and isinstance(expected_subset, dict):
            for key, value in expected_subset.items():
                if key not in actual_value:
                    raise AssertionError(
                        f"路径 '{json_path}' 中缺少键 '{key}'"
                    )
                if actual_value[key] != value:
                    raise AssertionError(
                        f"路径 '{json_path}.{key}' 的值不匹配。期望: {value}，实际: {actual_value[key]}"
                    )
        elif isinstance(actual_value, list) and isinstance(expected_subset, list):
            for item in expected_subset:
                if item not in actual_value:
                    raise AssertionError(
                        f"路径 '{json_path}' 的列表中缺少元素: {item}"
                    )
        else:
            assert actual_value == expected_subset, \
                f"路径 '{json_path}' 的值不匹配。期望: {expected_subset}，实际: {actual_value}"

    def assert_json_contains(self, response, key: str, expected_value: Any) -> None:
        try:
            response_json = response.json()
        except json.JSONDecodeError:
            raise AssertionError("响应不是有效的 JSON 格式")

        if key not in response_json:
            raise AssertionError(f"响应中不包含键: {key}")

        actual_value = response_json[key]
        assert actual_value == expected_value, \
            f"键 '{key}' 的值不匹配。期望: {expected_value}，实际: {actual_value}"

    def assert_response_time(self, response, max_ms: int) -> None:
        actual_ms = response.elapsed.total_seconds() * 1000
        assert actual_ms <= max_ms, \
            f"响应时间 {actual_ms:.2f}ms 超过最大允许值 {max_ms}ms"

    def assert_header_exists(self, response, header_name: str) -> None:
        assert header_name in response.headers, \
            f"响应头中不包含: {header_name}"

    def assert_header_value(self, response, header_name: str, expected_value: str) -> None:
        self.assert_header_exists(response, header_name)
        actual_value = response.headers.get(header_name)
        assert actual_value == expected_value, \
            f"响应头 '{header_name}' 的值不匹配。期望: {expected_value}，实际: {actual_value}"

    def assert_contains_text(self, response, text: str) -> None:
        assert text in response.text, \
            f"响应文本中不包含: {text}"

    def run_assertions(self, response, assertions: List[Dict[str, Any]]) -> None:
        for assertion in assertions:
            assertion_type = assertion.get("type")

            try:
                if assertion_type == "status_code":
                    self.assert_status_code(response, assertion["value"])
                elif assertion_type == "json_contains":
                    self.assert_json_contains(response, assertion["key"], assertion["value"])
                elif assertion_type == "json_path_exists":
                    self.assert_json_path_exists(response, assertion["path"])
                elif assertion_type == "json_path_value":
                    self.assert_json_path_value(response, assertion["path"], assertion["value"])
                elif assertion_type == "json_path_contains":
                    self.assert_json_path_contains(response, assertion["path"], assertion["value"])
                elif assertion_type == "response_time":
                    self.assert_response_time(response, assertion["max_ms"])
                elif assertion_type == "header_exists":
                    self.assert_header_exists(response, assertion["header_name"])
                elif assertion_type == "header_value":
                    self.assert_header_value(response, assertion["header_name"], assertion["value"])
                elif assertion_type == "contains_text":
                    self.assert_contains_text(response, assertion["text"])
                else:
                    raise ValueError(f"未知的断言类型: {assertion_type}")
            except AssertionError:
                raise
            except JSONPathError as e:
                raise AssertionError(str(e))
            except Exception as e:
                raise AssertionError(f"断言执行失败: {e}")


api_assertions = APIAssertions()
