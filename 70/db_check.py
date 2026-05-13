import os
import yaml
import threading
from typing import Dict, Any, List, Optional, Tuple


class DatabaseConnectionError(Exception):
    pass


class DatabaseQueryError(Exception):
    pass


class DatabaseCheck:
    _instance = None
    _lock = threading.Lock()
    _connections: Dict[str, Any] = {}

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._config = None
        return cls._instance

    def load_config(self) -> Dict[str, Any]:
        if self._config is None:
            config_file = os.path.join(os.path.dirname(__file__), "test_data.yaml")
            with open(config_file, "r", encoding="utf-8") as f:
                full_config = yaml.safe_load(f) or {}
            self._config = full_config.get("database", {})
        return self._config

    def _get_connection(self):
        config = self.load_config()
        db_type = config.get("type", "mysql")
        conn_key = f"{db_type}_{config.get('host', 'localhost')}_{config.get('database', '')}"

        if conn_key in self._connections:
            return self._connections[conn_key]

        try:
            if db_type == "mysql":
                import pymysql
                connection = pymysql.connect(
                    host=config.get("host", "localhost"),
                    port=config.get("port", 3306),
                    user=config.get("user", "root"),
                    password=config.get("password", ""),
                    database=config.get("database", ""),
                    charset="utf8mb4",
                    cursorclass=pymysql.cursors.DictCursor
                )
            elif db_type == "postgresql":
                import psycopg2
                from psycopg2.extras import RealDictCursor
                connection = psycopg2.connect(
                    host=config.get("host", "localhost"),
                    port=config.get("port", 5432),
                    user=config.get("user", "postgres"),
                    password=config.get("password", ""),
                    database=config.get("database", ""),
                    cursor_factory=RealDictCursor
                )
            elif db_type == "sqlite":
                import sqlite3
                db_path = config.get("database", ":memory:")
                connection = sqlite3.connect(db_path)
                connection.row_factory = sqlite3.Row
            else:
                raise DatabaseConnectionError(f"不支持的数据库类型: {db_type}")

            self._connections[conn_key] = connection
            return connection
        except ImportError as e:
            raise DatabaseConnectionError(f"缺少数据库驱动: {e}")
        except Exception as e:
            raise DatabaseConnectionError(f"数据库连接失败: {e}")

    def execute_query(self, sql: str, params: Optional[tuple] = None) -> List[Dict[str, Any]]:
        connection = self._get_connection()
        try:
            cursor = connection.cursor()
            cursor.execute(sql, params or ())
            rows = cursor.fetchall()

            result = []
            for row in rows:
                if isinstance(row, dict):
                    result.append(dict(row))
                else:
                    result.append(dict(zip([desc[0] for desc in cursor.description], row)))

            return result
        except Exception as e:
            raise DatabaseQueryError(f"执行 SQL 失败: {e}\nSQL: {sql}")

    def execute_update(self, sql: str, params: Optional[tuple] = None) -> int:
        connection = self._get_connection()
        try:
            cursor = connection.cursor()
            cursor.execute(sql, params or ())
            affected = cursor.rowcount
            connection.commit()
            return affected
        except Exception as e:
            connection.rollback()
            raise DatabaseQueryError(f"执行更新失败: {e}\nSQL: {sql}")

    def close_all(self):
        for key, conn in self._connections.items():
            try:
                conn.close()
            except Exception:
                pass
        self._connections.clear()


class DatabaseAssertions:
    def __init__(self):
        self.db = DatabaseCheck()

    def assert_row_count(self, sql: str, expected: int, params: Optional[tuple] = None) -> None:
        rows = self.db.execute_query(sql, params)
        actual = len(rows)
        assert actual == expected, \
            f"行数量不匹配。期望: {expected}，实际: {actual}\nSQL: {sql}"

    def assert_row_exists(self, sql: str, params: Optional[tuple] = None) -> None:
        rows = self.db.execute_query(sql, params)
        assert len(rows) > 0, \
            f"期望的行不存在。SQL: {sql}"

    def assert_row_not_exists(self, sql: str, params: Optional[tuple] = None) -> None:
        rows = self.db.execute_query(sql, params)
        assert len(rows) == 0, \
            f"期望行不存在，但找到 {len(rows)} 行。SQL: {sql}"

    def assert_column_value(self, sql: str, column: str, expected: Any, params: Optional[tuple] = None) -> None:
        rows = self.db.execute_query(sql, params)
        assert len(rows) > 0, f"查询没有返回任何数据。SQL: {sql}"

        for idx, row in enumerate(rows):
            if column not in row:
                raise AssertionError(f"结果集中不存在列: {column}")

            actual = row[column]
            if actual == expected:
                return

        raise AssertionError(
            f"列 '{column}' 的值不匹配。期望: {expected}，实际值: {[r.get(column) for r in rows]}"
        )

    def assert_all_columns(self, sql: str, expected: Dict[str, Any], params: Optional[tuple] = None) -> None:
        rows = self.db.execute_query(sql, params)
        assert len(rows) > 0, f"查询没有返回任何数据。SQL: {sql}"

        for column, expected_value in expected.items():
            for row in rows:
                if column not in row:
                    raise AssertionError(f"结果集中不存在列: {column}")

                if row[column] == expected_value:
                    break
            else:
                raise AssertionError(
                    f"列 '{column}' 的值不匹配。期望: {expected_value}"
                )

    def run_db_assertions(self, sql: str, assertions: List[Dict[str, Any]], params: Optional[tuple] = None) -> None:
        for assertion in assertions:
            assertion_type = assertion.get("type")

            if assertion_type == "row_count":
                self.assert_row_count(sql, assertion["expected"], params)
            elif assertion_type == "row_exists":
                self.assert_row_exists(sql, params)
            elif assertion_type == "row_not_exists":
                self.assert_row_not_exists(sql, params)
            elif assertion_type == "column_value":
                self.assert_column_value(sql, assertion["column"], assertion["expected"], params)
            elif assertion_type == "all_columns":
                self.assert_all_columns(sql, assertion["expected"], params)
            else:
                raise ValueError(f"未知的数据库断言类型: {assertion_type}")


db_check = DatabaseCheck()
db_assertions = DatabaseAssertions()
