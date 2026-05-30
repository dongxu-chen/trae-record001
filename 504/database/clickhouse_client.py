import clickhouse_connect
from typing import List, Dict, Any, Optional
import pandas as pd
from config import CLICKHOUSE_CONFIG, EVENT_TABLE


class ClickHouseClient:
    def __init__(self):
        self.config = CLICKHOUSE_CONFIG
        self.client = None
        self._connect()

    def _connect(self):
        try:
            self.client = clickhouse_connect.get_client(
                host=self.config['host'],
                port=self.config['port'],
                username=self.config['username'],
                password=self.config['password'],
                database=self.config['database'],
                secure=self.config['secure']
            )
        except Exception as e:
            print(f"ClickHouse连接失败: {e}")
            self.client = None

    def is_connected(self) -> bool:
        return self.client is not None

    def execute_query(self, query: str, params: Optional[Dict] = None) -> pd.DataFrame:
        if not self.is_connected():
            raise ConnectionError("ClickHouse未连接")
        return self.client.query_df(query, parameters=params or {})

    def execute_command(self, command: str, params: Optional[Dict] = None):
        if not self.is_connected():
            raise ConnectionError("ClickHouse未连接")
        return self.client.command(command, parameters=params or {})

    def create_database(self):
        self.execute_command(f"CREATE DATABASE IF NOT EXISTS {self.config['database']}")

    def create_events_table(self):
        create_table_sql = f"""
        CREATE TABLE IF NOT EXISTS {EVENT_TABLE} (
            user_id String,
            session_id String,
            event_name String,
            event_time DateTime,
            page_url String DEFAULT '',
            referrer String DEFAULT '',
            device_type String DEFAULT '',
            os String DEFAULT '',
            browser String DEFAULT '',
            user_group String DEFAULT 'default',
            event_properties Map(String, String) DEFAULT map()
        ) ENGINE = MergeTree()
        PARTITION BY toYYYYMM(event_time)
        ORDER BY (user_id, session_id, event_time)
        TTL event_time + INTERVAL 90 DAY
        SETTINGS index_granularity = 8192
        """
        self.execute_command(create_table_sql)

    def insert_events(self, df: pd.DataFrame):
        if not self.is_connected():
            raise ConnectionError("ClickHouse未连接")
        self.client.insert_df(EVENT_TABLE, df)

    def get_distinct_users(self, start_date: str, end_date: str) -> int:
        query = f"""
        SELECT COUNT(DISTINCT user_id) as user_count
        FROM {EVENT_TABLE}
        WHERE event_time BETWEEN '{start_date}' AND '{end_date}'
        """
        result = self.execute_query(query)
        return result['user_count'].iloc[0] if not result.empty else 0

    def get_distinct_events(self, start_date: str, end_date: str) -> List[str]:
        query = f"""
        SELECT DISTINCT event_name
        FROM {EVENT_TABLE}
        WHERE event_time BETWEEN '{start_date}' AND '{end_date}'
        ORDER BY event_name
        """
        result = self.execute_query(query)
        return result['event_name'].tolist() if not result.empty else []

    def get_user_groups(self) -> List[str]:
        query = f"""
        SELECT DISTINCT user_group
        FROM {EVENT_TABLE}
        ORDER BY user_group
        """
        result = self.execute_query(query)
        return result['user_group'].tolist() if not result.empty else ['default']

    def get_date_range(self) -> Dict[str, str]:
        query = f"""
        SELECT 
            MIN(event_time) as min_date,
            MAX(event_time) as max_date
        FROM {EVENT_TABLE}
        """
        result = self.execute_query(query)
        if not result.empty:
            return {
                'min': result['min_date'].iloc[0],
                'max': result['max_date'].iloc[0]
            }
        return {'min': None, 'max': None}
