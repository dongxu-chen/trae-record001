from typing import List, Any, Optional
import pymysql
from pymysql.cursors import DictCursor

from .connector import DatabaseConnector, QueryResult
from config import DatabaseConfig


class MySQLConnector(DatabaseConnector):
    def __init__(self, config: DatabaseConfig):
        super().__init__(config)
        self._charset = "utf8mb4"

    def connect(self) -> bool:
        try:
            self._connection = pymysql.connect(
                host=self.config.host,
                port=self.config.port,
                user=self.config.user,
                password=self.config.password,
                database=self.config.database,
                charset=self._charset,
                cursorclass=DictCursor,
                connect_timeout=10,
                read_timeout=30,
                write_timeout=30,
            )
            self._cursor = self._connection.cursor()
            return True
        except Exception as e:
            self._connection = None
            self._cursor = None
            return False

    def disconnect(self) -> None:
        if self._cursor:
            try:
                self._cursor.close()
            except Exception:
                pass
            self._cursor = None

        if self._connection:
            try:
                self._connection.close()
            except Exception:
                pass
            self._connection = None

    def is_connected(self) -> bool:
        if self._connection is None:
            return False
        try:
            self._connection.ping(reconnect=False)
            return True
        except Exception:
            return False

    def _get_explain_sql(self, sql: str) -> str:
        return f"EXPLAIN FORMAT=JSON {sql}"

    def _execute_query(self, sql: str, params: Optional[List[Any]] = None) -> QueryResult:
        result = QueryResult(sql=sql)

        try:
            if params:
                self._cursor.execute(sql, params)
            else:
                self._cursor.execute(sql)

            result.columns = [desc[0] for desc in self._cursor.description] if self._cursor.description else []
            result.rows = self._cursor.fetchall()
            result.affected_rows = self._cursor.rowcount

            if result.columns and result.rows:
                converted_rows = []
                for row in result.rows:
                    if isinstance(row, dict):
                        converted_rows.append(tuple(row[col] for col in result.columns))
                    else:
                        converted_rows.append(row)
                result.rows = converted_rows

            self._connection.commit()
            result.success = True

        except Exception as e:
            result.error = str(e)
            if self._connection:
                try:
                    self._connection.rollback()
                except Exception:
                    pass

        return result

    def get_tables(self) -> List[str]:
        if not self.is_connected():
            if not self.connect():
                return []

        try:
            self._cursor.execute("SHOW TABLES")
            rows = self._cursor.fetchall()
            tables = []
            for row in rows:
                if isinstance(row, dict):
                    tables.append(list(row.values())[0])
                else:
                    tables.append(row[0])
            return sorted(tables)
        except Exception:
            return []

    def get_table_schema(self, table_name: str) -> List[dict]:
        if not self.is_connected():
            if not self.connect():
                return []

        try:
            self._cursor.execute(f"DESCRIBE {table_name}")
            rows = self._cursor.fetchall()
            columns = []
            for row in rows:
                if isinstance(row, dict):
                    columns.append({
                        "name": row.get("Field", ""),
                        "type": row.get("Type", ""),
                        "nullable": row.get("Null", "") == "YES",
                        "key": row.get("Key", ""),
                        "default": row.get("Default", None),
                    })
            return columns
        except Exception:
            return []

    def get_indexes(self, table_name: str) -> List[dict]:
        if not self.is_connected():
            if not self.connect():
                return []

        try:
            self._cursor.execute(f"SHOW INDEX FROM {table_name}")
            rows = self._cursor.fetchall()
            indexes = []
            for row in rows:
                if isinstance(row, dict):
                    indexes.append({
                        "table": row.get("Table", ""),
                        "non_unique": row.get("Non_unique", 1) == 1,
                        "name": row.get("Key_name", ""),
                        "column": row.get("Column_name", ""),
                        "cardinality": row.get("Cardinality", 0),
                    })
            return indexes
        except Exception:
            return []
