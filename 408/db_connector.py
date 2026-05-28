import pymysql
from dbutils.pooled_db import PooledDB
import threading
import time
import json
import os
from datetime import datetime


class DBConnector:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, host=None, port=None, user=None, password=None, database=None):
        if hasattr(self, '_initialized'):
            return
        self._initialized = True
        self.host = host or os.environ.get('DB_HOST', '127.0.0.1')
        self.port = port or int(os.environ.get('DB_PORT', 3306))
        self.user = user or os.environ.get('DB_USER', 'root')
        self.password = password or os.environ.get('DB_PASSWORD', '')
        self.database = database or os.environ.get('DB_NAME', '')
        self.pool = None
        self._config_file = os.path.join(os.path.dirname(__file__), 'db_config.json')
        self._load_config()
        self._init_pool()

    def _load_config(self):
        if os.path.exists(self._config_file):
            try:
                with open(self._config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                self.host = config.get('host', self.host)
                self.port = config.get('port', self.port)
                self.user = config.get('user', self.user)
                self.password = config.get('password', self.password)
                self.database = config.get('database', self.database)
            except Exception:
                pass

    def save_config(self, host, port, user, password, database):
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.database = database
        config = {
            'host': host,
            'port': port,
            'user': user,
            'password': password,
            'database': database
        }
        try:
            with open(self._config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
        except Exception:
            pass
        self._init_pool()

    def _init_pool(self):
        try:
            self.pool = PooledDB(
                creator=pymysql,
                maxconnections=10,
                mincached=2,
                maxcached=5,
                host=self.host,
                port=self.port,
                user=self.user,
                password=self.password,
                database=self.database,
                charset='utf8mb4',
                cursorclass=pymysql.cursors.DictCursor,
                connect_timeout=10,
                read_timeout=30,
                write_timeout=30
            )
        except Exception as e:
            self.pool = None
            print(f"连接池初始化失败: {e}")

    def test_connection(self, host=None, port=None, user=None, password=None, database=None):
        try:
            conn = pymysql.connect(
                host=host or self.host,
                port=port or self.port,
                user=user or self.user,
                password=password or self.password,
                database=database or self.database,
                charset='utf8mb4',
                connect_timeout=10
            )
            conn.close()
            return True, "连接成功"
        except Exception as e:
            return False, str(e)

    def get_connection(self):
        if self.pool is None:
            self._init_pool()
        if self.pool is None:
            raise Exception("数据库连接池未初始化，请先配置数据库连接")
        return self.pool.connection()

    def execute_query(self, sql, params=None, fetch=True, timeout=30):
        conn = None
        cursor = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            start_time = time.time()
            cursor.execute(sql, params)
            if fetch:
                result = cursor.fetchall()
            else:
                result = cursor.rowcount
            elapsed = time.time() - start_time
            return {
                'success': True,
                'data': result,
                'elapsed': elapsed,
                'rows_affected': cursor.rowcount
            }
        except pymysql.err.OperationalError as e:
            return {'success': False, 'error': f"连接错误: {str(e)}"}
        except pymysql.err.ProgrammingError as e:
            return {'success': False, 'error': f"SQL语法错误: {str(e)}"}
        except Exception as e:
            return {'success': False, 'error': f"执行错误: {str(e)}"}
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()

    def execute_explain(self, sql, params=None):
        return self.execute_query(f"EXPLAIN {sql}", params)

    def execute_explain_format(self, sql, params=None, fmt='JSON'):
        return self.execute_query(f"EXPLAIN FORMAT={fmt} {sql}", params)

    def get_slow_queries(self, start_time=None, end_time=None, min_query_time=1.0, limit=100):
        sql = """
            SELECT * FROM mysql.slow_log
            WHERE 1=1
        """
        params = []
        if start_time:
            sql += " AND start_time >= %s"
            params.append(start_time)
        if end_time:
            sql += " AND start_time <= %s"
            params.append(end_time)
        sql += " AND query_time >= %s"
        params.append(min_query_time)
        sql += " ORDER BY start_time DESC LIMIT %s"
        params.append(limit)
        return self.execute_query(sql, params)

    def enable_slow_log(self, long_query_time=1):
        results = []
        r1 = self.execute_query("SET GLOBAL slow_query_log = 'ON'", fetch=False)
        results.append(r1)
        r2 = self.execute_query(f"SET GLOBAL long_query_time = {long_query_time}", fetch=False)
        results.append(r2)
        r3 = self.execute_query("SET GLOBAL log_queries_not_using_indexes = 'ON'", fetch=False)
        results.append(r3)
        return {'success': all(r.get('success', False) for r in results), 'results': results}

    def disable_slow_log(self):
        return self.execute_query("SET GLOBAL slow_query_log = 'OFF'", fetch=False)

    def get_slow_log_status(self):
        return self.execute_query("SHOW VARIABLES LIKE 'slow_query%'")

    def get_processlist(self):
        return self.execute_query("SHOW FULL PROCESSLIST")

    def get_table_indexes(self, table_name):
        return self.execute_query(f"SHOW INDEX FROM `{table_name}`")

    def get_table_status(self, table_name):
        return self.execute_query(f"SHOW TABLE STATUS LIKE '{table_name}'")

    def get_table_columns(self, table_name):
        return self.execute_query(f"SHOW COLUMNS FROM `{table_name}`")

    def get_tables(self):
        return self.execute_query("SHOW TABLES")

    def get_database_size(self):
        sql = """
            SELECT 
                table_schema AS database_name,
                ROUND(SUM(data_length + index_length) / 1024 / 1024, 2) AS size_mb,
                COUNT(*) AS table_count
            FROM information_schema.tables
            WHERE table_schema NOT IN ('information_schema', 'mysql', 'performance_schema', 'sys')
            GROUP BY table_schema
            ORDER BY size_mb DESC
        """
        return self.execute_query(sql)

    def get_top_large_tables(self, limit=20):
        sql = """
            SELECT 
                table_schema,
                table_name,
                ROUND(data_length / 1024 / 1024, 2) AS data_mb,
                ROUND(index_length / 1024 / 1024, 2) AS index_mb,
                table_rows
            FROM information_schema.tables
            WHERE table_schema NOT IN ('information_schema', 'mysql', 'performance_schema', 'sys')
            ORDER BY (data_length + index_length) DESC
            LIMIT %s
        """
        return self.execute_query(sql, [limit])

    def get_config(self):
        return {
            'host': self.host,
            'port': self.port,
            'user': self.user,
            'database': self.database,
            'pool_initialized': self.pool is not None
        }