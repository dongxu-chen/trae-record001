from typing import List, Any, Optional
import psycopg2
from psycopg2.extras import RealDictCursor

from .connector import DatabaseConnector, QueryResult
from config import DatabaseConfig


class PostgreSQLConnector(DatabaseConnector):
    def __init__(self, config: DatabaseConfig):
        super().__init__(config)
        self._charset = "utf8"

    def connect(self) -> bool:
        try:
            self._connection = psycopg2.connect(
                host=self.config.host,
                port=self.config.port,
                user=self.config.user,
                password=self.config.password,
                database=self.config.database,
                connect_timeout=10,
                options="-c statement_timeout=30000",
            )
            self._connection.autocommit = False
            self._cursor = self._connection.cursor(cursor_factory=RealDictCursor)
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
            cur = self._connection.cursor()
            cur.execute("SELECT 1")
            cur.close()
            return True
        except Exception:
            return False

    def _get_explain_sql(self, sql: str) -> str:
        return f"EXPLAIN (FORMAT JSON, ANALYZE, BUFFERS) {sql}"

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
            self._cursor.execute("""
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public'
                ORDER BY table_name
            """)
            rows = self._cursor.fetchall()
            tables = []
            for row in rows:
                if isinstance(row, dict):
                    tables.append(row.get("table_name", ""))
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
            self._cursor.execute("""
                SELECT
                    column_name,
                    data_type,
                    is_nullable,
                    column_default,
                    ordinal_position
                FROM information_schema.columns
                WHERE table_name = %s
                AND table_schema = 'public'
                ORDER BY ordinal_position
            """, (table_name,))
            rows = self._cursor.fetchall()
            columns = []
            for row in rows:
                if isinstance(row, dict):
                    columns.append({
                        "name": row.get("column_name", ""),
                        "type": row.get("data_type", ""),
                        "nullable": row.get("is_nullable", "") == "YES",
                        "key": "",
                        "default": row.get("column_default", None),
                    })
            return columns
        except Exception:
            return []

    def get_indexes(self, table_name: str) -> List[dict]:
        if not self.is_connected():
            if not self.connect():
                return []

        try:
            self._cursor.execute("""
                SELECT
                    t.relname AS table_name,
                    i.relname AS index_name,
                    a.attname AS column_name,
                    ix.indisunique AS is_unique,
                    ix.indisprimary AS is_primary
                FROM pg_class t
                JOIN pg_index ix ON t.oid = ix.indrelid
                JOIN pg_class i ON i.oid = ix.indexrelid
                JOIN pg_attribute a ON a.attrelid = t.oid AND a.attnum = ANY(ix.indkey)
                WHERE t.relname = %s
                AND t.relkind = 'r'
                ORDER BY i.relname, array_position(ix.indkey, a.attnum)
            """, (table_name,))
            rows = self._cursor.fetchall()
            indexes = []
            for row in rows:
                if isinstance(row, dict):
                    indexes.append({
                        "table": row.get("table_name", ""),
                        "non_unique": not row.get("is_unique", False),
                        "name": row.get("index_name", ""),
                        "column": row.get("column_name", ""),
                        "cardinality": 0,
                    })
            return indexes
        except Exception:
            return []
