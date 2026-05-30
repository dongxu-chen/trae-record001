import pymysql
import logging
import time
from typing import Dict, Any, Optional, Tuple

logger = logging.getLogger(__name__)


class MySQLConnection:
    def __init__(self, host: str, port: int, user: str, password: str, database: str = "mysql"):
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.database = database
        self.connection: Optional[pymysql.Connection] = None
        self._connect()

    def _connect(self) -> None:
        try:
            self.connection = pymysql.connect(
                host=self.host,
                port=self.port,
                user=self.user,
                password=self.password,
                database=self.database,
                charset='utf8mb4',
                cursorclass=pymysql.cursors.DictCursor,
                connect_timeout=10
            )
            logger.info(f"成功连接到MySQL: {self.host}:{self.port}")
        except Exception as e:
            logger.error(f"连接MySQL失败: {self.host}:{self.port}, 错误: {str(e)}")
            raise

    def _ensure_connection(self) -> None:
        if not self.connection or not self.connection.open:
            self._connect()

    def execute_query(self, sql: str, params: tuple = None) -> list:
        self._ensure_connection()
        try:
            with self.connection.cursor() as cursor:
                cursor.execute(sql, params or ())
                return cursor.fetchall()
        except Exception as e:
            logger.error(f"执行查询失败: {sql}, 错误: {str(e)}")
            raise

    def execute_update(self, sql: str, params: tuple = None) -> int:
        self._ensure_connection()
        try:
            with self.connection.cursor() as cursor:
                affected = cursor.execute(sql, params or ())
                self.connection.commit()
                return affected
        except Exception as e:
            logger.error(f"执行更新失败: {sql}, 错误: {str(e)}")
            self.connection.rollback()
            raise

    def get_slave_status(self) -> Dict[str, Any]:
        self._ensure_connection()
        try:
            with self.connection.cursor() as cursor:
                cursor.execute("SHOW SLAVE STATUS")
                result = cursor.fetchone()
                if result:
                    return {k.lower(): v for k, v in result.items()}
                return {}
        except Exception as e:
            logger.error(f"获取从库状态失败: {str(e)}")
            return {}

    def get_master_status(self) -> Dict[str, Any]:
        self._ensure_connection()
        try:
            with self.connection.cursor() as cursor:
                cursor.execute("SHOW MASTER STATUS")
                result = cursor.fetchone()
                if result:
                    return {k.lower(): v for k, v in result.items()}
                return {}
        except Exception as e:
            logger.error(f"获取主库状态失败: {str(e)}")
            return {}

    def get_processlist(self) -> list:
        return self.execute_query("SHOW FULL PROCESSLIST")

    def get_global_status(self) -> Dict[str, Any]:
        results = self.execute_query("SHOW GLOBAL STATUS")
        return {row['Variable_name'].lower(): row['Value'] for row in results}

    def get_global_variables(self) -> Dict[str, Any]:
        results = self.execute_query("SHOW GLOBAL VARIABLES")
        return {row['Variable_name'].lower(): row['Value'] for row in results}

    def get_innodb_status(self) -> str:
        results = self.execute_query("SHOW ENGINE INNODB STATUS")
        if results and len(results) > 0:
            return results[0].get('Status', '')
        return ''

    def ping(self) -> Tuple[bool, float]:
        start_time = time.time()
        try:
            self._ensure_connection()
            with self.connection.cursor() as cursor:
                cursor.execute("SELECT 1")
            latency = (time.time() - start_time) * 1000
            return True, latency
        except Exception as e:
            logger.error(f"ping失败: {str(e)}")
            return False, -1

    def close(self) -> None:
        if self.connection and self.connection.open:
            self.connection.close()
            logger.info(f"关闭MySQL连接: {self.host}:{self.port}")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
