import logging
import time
import hashlib
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, Tuple

from config import DatabaseConfig

logger = logging.getLogger(__name__)


class DatabaseDriver(ABC):
    def __init__(self, config: DatabaseConfig):
        self.config = config
        self.connection = None
        self.is_connected = False

    @abstractmethod
    def connect(self) -> bool:
        pass

    @abstractmethod
    def disconnect(self) -> None:
        pass

    @abstractmethod
    def get_tables(self) -> List[str]:
        pass

    @abstractmethod
    def get_row_count(self, table: str) -> int:
        pass

    @abstractmethod
    def get_table_columns(self, table: str) -> List[Dict[str, Any]]:
        pass

    @abstractmethod
    def get_sample_data(self, table: str, limit: int, offset: int = 0) -> List[Dict]:
        pass

    @abstractmethod
    def execute_query(self, query: str, params: tuple = None) -> List[Dict]:
        pass

    @abstractmethod
    def restore_backup(self, backup_file_path: str) -> bool:
        pass

    @abstractmethod
    def get_primary_key(self, table: str) -> Optional[str]:
        pass

    @abstractmethod
    def get_primary_key_range(self, table: str) -> Tuple[Optional[Any], Optional[Any]]:
        pass

    def get_table_checksum(self, table: str, columns: Optional[List[str]] = None) -> str:
        if not columns:
            columns_info = self.get_table_columns(table)
            columns = [col['name'] for col in columns_info]

        col_expr = ", ".join([f"COALESCE(CAST({c} AS CHAR), '')" for c in columns])
        query = f"SELECT MD5(GROUP_CONCAT(CONCAT({col_expr}) ORDER BY {columns[0]})) as checksum FROM {table}"
        result = self.execute_query(query)
        if result and len(result) > 0:
            return result[0].get('checksum', '')
        return ''

    def get_table_stats(self, table: str) -> Dict[str, Any]:
        row_count = self.get_row_count(table)
        columns = self.get_table_columns(table)
        return {
            'table_name': table,
            'row_count': row_count,
            'column_count': len(columns),
            'columns': [col['name'] for col in columns]
        }

    def test_connection(self) -> Tuple[bool, float]:
        if not self.is_connected:
            self.connect()

        start_time = time.time()
        try:
            self.execute_query("SELECT 1")
            elapsed = time.time() - start_time
            return True, elapsed
        except Exception as e:
            logger.error(f"Connection test failed: {e}")
            return False, 0.0


class MySQLDriver(DatabaseDriver):
    def __init__(self, config: DatabaseConfig):
        super().__init__(config)
        self.pymysql = None

    def _ensure_import(self):
        if self.pymysql is None:
            import pymysql
            self.pymysql = pymysql

    def connect(self) -> bool:
        try:
            self._ensure_import()
            self.connection = self.pymysql.connect(
                host=self.config.host,
                port=self.config.port,
                user=self.config.username,
                password=self.config.password,
                database=self.config.database,
                charset=self.config.charset,
                cursorclass=self.pymysql.cursors.DictCursor,
                **self.config.extra_params
            )
            self.is_connected = True
            logger.info(f"Connected to MySQL at {self.config.host}:{self.config.port}")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to MySQL: {e}")
            self.is_connected = False
            return False

    def disconnect(self) -> None:
        if self.connection:
            self.connection.close()
            self.is_connected = False
            logger.info("Disconnected from MySQL")

    def get_tables(self) -> List[str]:
        result = self.execute_query("SHOW TABLES")
        key = list(result[0].keys())[0] if result else ''
        return [row[key] for row in result]

    def get_row_count(self, table: str) -> int:
        result = self.execute_query(f"SELECT COUNT(*) as cnt FROM `{table}`")
        return result[0]['cnt'] if result else 0

    def get_table_columns(self, table: str) -> List[Dict[str, Any]]:
        result = self.execute_query(f"DESCRIBE `{table}`")
        return [{'name': row['Field'], 'type': row['Type'], 'nullable': row['Null'] == 'YES'} for row in result]

    def get_sample_data(self, table: str, limit: int, offset: int = 0) -> List[Dict]:
        return self.execute_query(f"SELECT * FROM `{table}` LIMIT %s OFFSET %s", (limit, offset))

    def execute_query(self, query: str, params: tuple = None) -> List[Dict]:
        cursor = self.connection.cursor()
        try:
            cursor.execute(query, params)
            return cursor.fetchall()
        finally:
            cursor.close()

    def restore_backup(self, backup_file_path: str) -> bool:
        import subprocess
        import os

        if not os.path.exists(backup_file_path):
            logger.error(f"Backup file not found: {backup_file_path}")
            return False

        mysql_bin = self.config.extra_params.get('mysql_bin', 'mysql')
        cmd = [
            mysql_bin,
            f"-h{self.config.host}",
            f"-P{self.config.port}",
            f"-u{self.config.username}",
            f"-p{self.config.password}",
            self.config.database
        ]

        try:
            with open(backup_file_path, 'r', encoding='utf-8') as f:
                subprocess.run(cmd, stdin=f, check=True, capture_output=True)
            logger.info(f"Backup restored successfully from {backup_file_path}")
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"Backup restoration failed: {e.stderr.decode()}")
            return False

    def get_primary_key(self, table: str) -> Optional[str]:
        result = self.execute_query(f"SHOW KEYS FROM `{table}` WHERE Key_name = 'PRIMARY'")
        if result and len(result) > 0:
            return result[0]['Column_name']
        logger.warning(f"No primary key found for table {table}")
        return None

    def get_primary_key_range(self, table: str) -> Tuple[Optional[Any], Optional[Any]]:
        pk = self.get_primary_key(table)
        if not pk:
            return None, None
        try:
            result = self.execute_query(
                f"SELECT MIN(`{pk}`) as min_val, MAX(`{pk}`) as max_val FROM `{table}`"
            )
            if result and len(result) > 0:
                return result[0]['min_val'], result[0]['max_val']
        except Exception as e:
            logger.error(f"Failed to get primary key range for {table}: {e}")
        return None, None


class PostgreSQLDriver(DatabaseDriver):
    def __init__(self, config: DatabaseConfig):
        super().__init__(config)
        self.psycopg2 = None
        self._imported = False

    def _ensure_import(self):
        if not self._imported:
            import psycopg2
            import psycopg2.extras
            self.psycopg2 = psycopg2
            self._imported = True

    def connect(self) -> bool:
        try:
            self._ensure_import()
            self.connection = self.psycopg2.connect(
                host=self.config.host,
                port=self.config.port,
                user=self.config.username,
                password=self.config.password,
                dbname=self.config.database,
                **self.config.extra_params
            )
            self.connection.autocommit = True
            self.is_connected = True
            logger.info(f"Connected to PostgreSQL at {self.config.host}:{self.config.port}")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to PostgreSQL: {e}")
            self.is_connected = False
            return False

    def disconnect(self) -> None:
        if self.connection:
            self.connection.close()
            self.is_connected = False
            logger.info("Disconnected from PostgreSQL")

    def get_tables(self) -> List[str]:
        query = """
            SELECT tablename FROM pg_tables
            WHERE schemaname = %s
            ORDER BY tablename
        """
        schema = self.config.schema or 'public'
        result = self.execute_query(query, (schema,))
        return [row['tablename'] for row in result]

    def get_row_count(self, table: str) -> int:
        schema = self.config.schema or 'public'
        result = self.execute_query(f'SELECT COUNT(*) as cnt FROM "{schema}"."{table}"')
        return result[0]['cnt'] if result else 0

    def get_table_columns(self, table: str) -> List[Dict[str, Any]]:
        schema = self.config.schema or 'public'
        query = """
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns
            WHERE table_schema = %s AND table_name = %s
            ORDER BY ordinal_position
        """
        result = self.execute_query(query, (schema, table))
        return [{'name': row['column_name'], 'type': row['data_type'], 'nullable': row['is_nullable'] == 'YES'} for row in result]

    def get_sample_data(self, table: str, limit: int, offset: int = 0) -> List[Dict]:
        schema = self.config.schema or 'public'
        return self.execute_query(
            f'SELECT * FROM "{schema}"."{table}" LIMIT %s OFFSET %s',
            (limit, offset)
        )

    def execute_query(self, query: str, params: tuple = None) -> List[Dict]:
        self._ensure_import()
        cursor = self.connection.cursor(cursor_factory=self.psycopg2.extras.RealDictCursor)
        try:
            cursor.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]
        finally:
            cursor.close()

    def restore_backup(self, backup_file_path: str) -> bool:
        import subprocess
        import os

        if not os.path.exists(backup_file_path):
            logger.error(f"Backup file not found: {backup_file_path}")
            return False

        psql_bin = self.config.extra_params.get('psql_bin', 'psql')
        env = os.environ.copy()
        env['PGPASSWORD'] = self.config.password

        cmd = [
            psql_bin,
            f"-h{self.config.host}",
            f"-p{self.config.port}",
            f"-U{self.config.username}",
            f"-d{self.config.database}",
            "-f", backup_file_path
        ]

        try:
            subprocess.run(cmd, env=env, check=True, capture_output=True)
            logger.info(f"Backup restored successfully from {backup_file_path}")
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"Backup restoration failed: {e.stderr.decode()}")
            return False

    def get_primary_key(self, table: str) -> Optional[str]:
        schema = self.config.schema or 'public'
        query = """
            SELECT kcu.column_name
            FROM information_schema.table_constraints tc
            JOIN information_schema.key_column_usage kcu
              ON tc.constraint_name = kcu.constraint_name
              AND tc.table_schema = kcu.table_schema
            WHERE tc.constraint_type = 'PRIMARY KEY'
              AND tc.table_schema = %s
              AND tc.table_name = %s
            ORDER BY kcu.ordinal_position
            LIMIT 1
        """
        result = self.execute_query(query, (schema, table))
        if result and len(result) > 0:
            return result[0]['column_name']
        logger.warning(f"No primary key found for table {schema}.{table}")
        return None

    def get_primary_key_range(self, table: str) -> Tuple[Optional[Any], Optional[Any]]:
        schema = self.config.schema or 'public'
        pk = self.get_primary_key(table)
        if not pk:
            return None, None
        try:
            result = self.execute_query(
                f'SELECT MIN("{pk}") as min_val, MAX("{pk}") as max_val FROM "{schema}"."{table}"'
            )
            if result and len(result) > 0:
                return result[0]['min_val'], result[0]['max_val']
        except Exception as e:
            logger.error(f"Failed to get primary key range for {schema}.{table}: {e}")
        return None, None


class DatabaseDriverFactory:
    _drivers = {
        'mysql': MySQLDriver,
        'postgresql': PostgreSQLDriver,
    }

    @classmethod
    def create(cls, config: DatabaseConfig) -> DatabaseDriver:
        db_type = config.db_type.lower()
        driver_class = cls._drivers.get(db_type)
        if not driver_class:
            raise ValueError(f"Unsupported database type: {db_type}. Supported: {list(cls._drivers.keys())}")
        return driver_class(config)

    @classmethod
    def register_driver(cls, db_type: str, driver_class: type):
        cls._drivers[db_type.lower()] = driver_class


def create_driver(config: DatabaseConfig) -> DatabaseDriver:
    return DatabaseDriverFactory.create(config)
