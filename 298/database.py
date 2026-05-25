import re
import logging
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass, field
import mysql.connector
import psycopg2
import numpy as np

from config import DatabaseConfig

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class ColumnInfo:
    name: str
    data_type: str
    is_nullable: bool
    cardinality: int = 0
    distinct_values: int = 0


@dataclass
class IndexInfo:
    name: str
    columns: List[str]
    index_type: str = "BTREE"
    is_unique: bool = False
    is_primary: bool = False
    cardinality: int = 0
    size_bytes: int = 0


@dataclass
class TableSchema:
    name: str
    columns: List[ColumnInfo] = field(default_factory=list)
    indexes: List[IndexInfo] = field(default_factory=list)
    row_count: int = 0
    size_bytes: int = 0


@dataclass
class QueryInfo:
    sql: str
    execution_time: float = 0.0
    rows_examined: int = 0
    rows_sent: int = 0
    tables: List[str] = field(default_factory=list)
    columns_used: List[str] = field(default_factory=list)
    where_columns: List[str] = field(default_factory=list)
    join_columns: List[str] = field(default_factory=list)
    orderby_columns: List[str] = field(default_factory=list)
    groupby_columns: List[str] = field(default_factory=list)


@dataclass
class QueryCost:
    estimated_cost: float = 0.0
    execution_time_ms: float = 0.0
    rows_examined: int = 0
    access_type: str = "ALL"


class DatabaseConnector:
    def __init__(self, config: DatabaseConfig):
        self.config = config
        self.connection = None
        self._connect()

    def _connect(self):
        try:
            if self.config.db_type == "mysql":
                self.connection = mysql.connector.connect(
                    host=self.config.host,
                    port=self.config.port,
                    user=self.config.user,
                    password=self.config.password,
                    database=self.config.database
                )
            elif self.config.db_type == "postgresql":
                self.connection = psycopg2.connect(
                    host=self.config.host,
                    port=self.config.port,
                    user=self.config.user,
                    password=self.config.password,
                    database=self.config.database
                )
            logger.info(f"Connected to {self.config.db_type} database: {self.config.database}")
        except Exception as e:
            logger.error(f"Failed to connect to database: {e}")
            raise

    def close(self):
        if self.connection:
            self.connection.close()
            logger.info("Database connection closed")

    def execute_query(self, sql: str, params: Optional[Tuple] = None) -> List[Tuple]:
        cursor = self.connection.cursor()
        try:
            cursor.execute(sql, params or ())
            return cursor.fetchall()
        except Exception as e:
            logger.error(f"Query execution error: {e}")
            raise
        finally:
            cursor.close()

    def get_table_names(self) -> List[str]:
        if self.config.db_type == "mysql":
            sql = "SHOW TABLES"
        elif self.config.db_type == "postgresql":
            sql = "SELECT tablename FROM pg_tables WHERE schemaname = 'public'"
        
        rows = self.execute_query(sql)
        return [row[0] for row in rows]

    def get_table_schema(self, table_name: str) -> TableSchema:
        schema = TableSchema(name=table_name)
        
        if self.config.db_type == "mysql":
            schema.columns = self._get_mysql_columns(table_name)
            schema.indexes = self._get_mysql_indexes(table_name)
            schema.row_count, schema.size_bytes = self._get_mysql_table_stats(table_name)
        elif self.config.db_type == "postgresql":
            schema.columns = self._get_postgres_columns(table_name)
            schema.indexes = self._get_postgres_indexes(table_name)
            schema.row_count, schema.size_bytes = self._get_postgres_table_stats(table_name)
        
        return schema

    def _get_mysql_columns(self, table_name: str) -> List[ColumnInfo]:
        sql = f"""
            SELECT COLUMN_NAME, DATA_TYPE, IS_NULLABLE, CARDINALITY
            FROM INFORMATION_SCHEMA.STATISTICS
            WHERE TABLE_SCHEMA = '{self.config.database}' 
            AND TABLE_NAME = '{table_name}'
        """
        stats = {row[0]: row[3] for row in self.execute_query(sql)}
        
        sql = f"""
            SELECT COLUMN_NAME, DATA_TYPE, IS_NULLABLE
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = '{self.config.database}' 
            AND TABLE_NAME = '{table_name}'
        """
        rows = self.execute_query(sql)
        
        columns = []
        for row in rows:
            columns.append(ColumnInfo(
                name=row[0],
                data_type=row[1],
                is_nullable=(row[2] == "YES"),
                cardinality=stats.get(row[0], 0)
            ))
        return columns

    def _get_mysql_indexes(self, table_name: str) -> List[IndexInfo]:
        sql = f"""
            SELECT INDEX_NAME, COLUMN_NAME, NON_UNIQUE, INDEX_TYPE, SEQ_IN_INDEX, CARDINALITY
            FROM INFORMATION_SCHEMA.STATISTICS
            WHERE TABLE_SCHEMA = '{self.config.database}' 
            AND TABLE_NAME = '{table_name}'
            ORDER BY INDEX_NAME, SEQ_IN_INDEX
        """
        rows = self.execute_query(sql)
        
        indexes_dict: Dict[str, Dict] = {}
        for row in rows:
            idx_name = row[0]
            if idx_name not in indexes_dict:
                indexes_dict[idx_name] = {
                    'columns': [],
                    'non_unique': row[2],
                    'type': row[3],
                    'cardinality': row[5]
                }
            indexes_dict[idx_name]['columns'].append(row[1])
        
        indexes = []
        for idx_name, idx_info in indexes_dict.items():
            indexes.append(IndexInfo(
                name=idx_name,
                columns=idx_info['columns'],
                index_type=idx_info['type'],
                is_unique=(idx_info['non_unique'] == 0),
                is_primary=(idx_name == 'PRIMARY'),
                cardinality=idx_info['cardinality']
            ))
        return indexes

    def _get_mysql_table_stats(self, table_name: str) -> Tuple[int, int]:
        sql = f"""
            SELECT TABLE_ROWS, DATA_LENGTH + INDEX_LENGTH
            FROM INFORMATION_SCHEMA.TABLES
            WHERE TABLE_SCHEMA = '{self.config.database}' 
            AND TABLE_NAME = '{table_name}'
        """
        rows = self.execute_query(sql)
        if rows:
            return rows[0][0] or 0, rows[0][1] or 0
        return 0, 0

    def _get_postgres_columns(self, table_name: str) -> List[ColumnInfo]:
        sql = f"""
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns
            WHERE table_schema = 'public' 
            AND table_name = '{table_name}'
        """
        rows = self.execute_query(sql)
        
        columns = []
        for row in rows:
            columns.append(ColumnInfo(
                name=row[0],
                data_type=row[1],
                is_nullable=(row[2] == 'YES'
            ))
        return columns

    def _get_postgres_indexes(self, table_name: str) -> List[IndexInfo]:
        sql = f"""
            SELECT
                i.relname AS index_name,
                a.attname AS column_name,
                ix.indisunique,
                am.amname AS index_type,
                array_position(ix.indkey, a.attnum) AS seq_in_index
            FROM pg_index ix
            JOIN pg_class i ON i.oid = ix.indexrelid
            JOIN pg_class t ON t.oid = ix.indrelid
            JOIN pg_am am ON i.relam = am.oid
            JOIN pg_attribute a ON a.attrelid = t.oid AND a.attnum = ANY(ix.indkey)
            WHERE t.relname = '{table_name}'
            ORDER BY index_name, seq_in_index
        """
        rows = self.execute_query(sql)
        
        indexes_dict: Dict[str, Dict] = {}
        for row in rows:
            idx_name = row[0]
            if idx_name not in indexes_dict:
                indexes_dict[idx_name] = {
                    'columns': [],
                    'is_unique': row[2],
                    'type': row[3]
                }
            indexes_dict[idx_name]['columns'].append(row[1])
        
        indexes = []
        for idx_name, idx_info in indexes_dict.items():
            indexes.append(IndexInfo(
                name=idx_name,
                columns=idx_info['columns'],
                index_type=idx_info['type'],
                is_unique=idx_info['is_unique'],
                is_primary=(idx_name.endswith('_pkey')
            ))
        return indexes

    def _get_postgres_table_stats(self, table_name: str) -> Tuple[int, int]:
        sql = f"""
            SELECT
                c.reltuples::bigint,
                pg_total_relation_size('{table_name}')
            FROM pg_class c
            JOIN pg_namespace n ON c.relnamespace = n.oid
            WHERE c.relname = '{table_name}' AND n.nspname = 'public'
        """
        rows = self.execute_query(sql)
        if rows:
            return rows[0][0] or 0, rows[0][1] or 0
        return 0, 0

    def explain_query(self, sql: str) -> QueryCost:
        cursor = self.connection.cursor()
        try:
            if self.config.db_type == "mysql":
                cursor.execute(f"EXPLAIN FORMAT=JSON {sql}")
                result = cursor.fetchone()
                return self._parse_mysql_explain(result[0] if result else "")
            elif self.config.db_type == "postgresql":
                cursor.execute(f"EXPLAIN (FORMAT JSON) {sql}")
                result = cursor.fetchone()
                return self._parse_postgres_explain(result[0] if result else "")
            return QueryCost()
        except Exception as e:
            logger.warning(f"EXPLAIN failed: {e}")
            return QueryCost(estimated_cost=float('inf'))
        finally:
            cursor.close()

    def _parse_mysql_explain(self, explain_json: Any) -> QueryCost:
        cost = QueryCost()
        try:
            if isinstance(explain_json, str):
                import json
                explain_json = json.loads(explain_json)
            
            query_block = explain_json.get('query_block', {})
            cost.estimated_cost = float(query_block.get('cost_info', {}).get('query_cost', 0))
            
            table_info = query_block.get('table', {})
            if isinstance(table_info, list):
                table_info = table_info[0] if table_info else {}
            
            cost.access_type = table_info.get('access_type', 'ALL')
            cost.rows_examined = int(table_info.get('rows_examined_per_scan', 0))
        except Exception as e:
            logger.debug(f"Failed to parse MySQL EXPLAIN: {e}")
        return cost

    def _parse_postgres_explain(self, explain_json: Any) -> QueryCost:
        cost = QueryCost()
        try:
            if isinstance(explain_json, list) and explain_json:
                plan = explain_json[0].get('Plan', {})
                cost.estimated_cost = plan.get('Total Cost', 0)
                cost.rows_examined = plan.get('Plan Rows', 0)
                cost.access_type = plan.get('Node Type', 'Seq Scan')
        except Exception as e:
            logger.debug(f"Failed to parse PostgreSQL EXPLAIN: {e}")
        return cost

    def create_index(self, table_name: str, columns: List[str], index_name: Optional[str] = None) -> bool:
        if not index_name:
            index_name = f"idx_{table_name}_{'_'.join(columns)}"
        
        col_str = ', '.join(columns)
        sql = f"CREATE INDEX {index_name} ON {table_name} ({col_str})"
        
        try:
            cursor = self.connection.cursor()
            cursor.execute(sql)
            self.connection.commit()
            cursor.close()
            logger.info(f"Created index: {index_name}")
            return True
        except Exception as e:
            logger.error(f"Failed to create index {index_name}: {e}")
            self.connection.rollback()
            return False

    def drop_index(self, table_name: str, index_name: str) -> bool:
        try:
            cursor = self.connection.cursor()
            if self.config.db_type == "mysql":
                cursor.execute(f"DROP INDEX {index_name} ON {table_name}")
            elif self.config.db_type == "postgresql":
                cursor.execute(f"DROP INDEX {index_name}")
            self.connection.commit()
            cursor.close()
            logger.info(f"Dropped index: {index_name}")
            return True
        except Exception as e:
            logger.error(f"Failed to drop index {index_name}: {e}")
            self.connection.rollback()
            return False

    def get_all_schemas(self, tables: Optional[List[str]] = None) -> Dict[str, TableSchema]:
        if not tables:
            tables = self.get_table_names()
        
        schemas = {}
        for table in tables:
            schemas[table] = self.get_table_schema(table)
        return schemas
