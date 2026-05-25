import re
import logging
from typing import List, Dict, Set, Optional
from dataclasses import dataclass, field
import sqlparse
from sqlparse.sql import IdentifierList, Identifier, Where, Comparison, Parenthesis
from sqlparse.tokens import Keyword, DML, Whitespace

from database import QueryInfo

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SlowQueryLogParser:
    def __init__(self):
        self.mysql_patterns = {
            'time': re.compile(r'# Time:\s+(.+)'),
            'user_host': re.compile(r'# User@Host:\s+(.+)'),
            'query_time': re.compile(r'# Query_time:\s+([\d.]+)\s+Lock_time:\s+([\d.]+)\s+Rows_sent:\s+(\d+)\s+Rows_examined:\s+(\d+)'),
            'use_db': re.compile(r'USE\s+(\w+)', re.IGNORECASE),
            'set_timestamp': re.compile(r'SET\s+timestamp=\d+', re.IGNORECASE),
        }
        
        self.postgres_patterns = {
            'duration': re.compile(r'duration:\s+([\d.]+)\s+ms'),
            'statement': re.compile(r'statement:\s+(.+)'),
        }
        
        self.aggregated_queries: Dict[str, QueryInfo] = {}

    def parse_mysql_slow_log(self, log_path: str) -> List[QueryInfo]:
        queries = []
        current_query = None
        current_sql = []
        
        try:
            with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
                for line in f:
                    line = line.strip()
                    
                    if line.startswith('# Time:'):
                        if current_query and current_sql:
                            current_query.sql = ' '.join(current_sql)
                            self._process_query(current_query)
                            queries.append(current_query)
                        
                        current_query = QueryInfo(sql='')
                        current_sql = []
                    
                    elif line.startswith('# Query_time:'):
                        match = self.mysql_patterns['query_time'].match(line)
                        if match and current_query:
                            current_query.execution_time = float(match.group(1))
                            current_query.rows_sent = int(match.group(3))
                            current_query.rows_examined = int(match.group(4))
                    
                    elif line.startswith('#'):
                        continue
                    
                    elif self.mysql_patterns['use_db'].match(line):
                        continue
                    elif self.mysql_patterns['set_timestamp'].match(line):
                        continue
                    
                    else:
                        if current_query:
                            current_sql.append(line)
                
                if current_query and current_sql:
                    current_query.sql = ' '.join(current_sql)
                    self._process_query(current_query)
                    queries.append(current_query)
        
        except Exception as e:
            logger.error(f"Error parsing MySQL slow log: {e}")
        
        return queries

    def parse_postgres_log(self, log_path: str) -> List[QueryInfo]:
        queries = []
        current_query = None
        
        try:
            with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
                for line in f:
                    line = line.strip()
                    
                    duration_match = self.postgres_patterns['duration'].search(line)
                    if duration_match:
                        if current_query:
                            self._process_query(current_query)
                            queries.append(current_query)
                        
                        current_query = QueryInfo(sql='')
                        current_query.execution_time = float(duration_match.group(1)) / 1000.0
                    
                    statement_match = self.postgres_patterns['statement'].search(line)
                    if statement_match and current_query:
                        current_query.sql = statement_match.group(1)
                
                if current_query and current_query.sql:
                    self._process_query(current_query)
                    queries.append(current_query)
        
        except Exception as e:
            logger.error(f"Error parsing PostgreSQL log: {e}")
        
        return queries

    def _process_query(self, query: QueryInfo):
        parsed = self.parse_sql(query.sql)
        query.tables = parsed['tables']
        query.columns_used = parsed['columns']
        query.where_columns = parsed['where_columns']
        query.join_columns = parsed['join_columns']
        query.orderby_columns = parsed['orderby_columns']
        query.groupby_columns = parsed['groupby_columns']

    def parse_sql(self, sql: str) -> Dict:
        result = {
            'tables': set(),
            'columns': set(),
            'where_columns': set(),
            'join_columns': set(),
            'orderby_columns': set(),
            'groupby_columns': set(),
        }
        
        try:
            parsed = sqlparse.parse(sql)[0]
            self._walk_statement(parsed.tokens, result)
        except Exception as e:
            logger.debug(f"SQL parse error: {e}")
        
        for key in result:
            result[key] = list(result[key])
        
        return result

    def _walk_statement(self, tokens, result: Dict):
        in_where = False
        in_from = False
        in_join = False
        in_order_by = False
        in_group_by = False
        
        for token in tokens:
            if token.ttype is Whitespace:
                continue
            
            if token.ttype is Keyword:
                token_upper = token.value.upper()
                if 'FROM' in token_upper:
                    in_from = True
                    in_where = False
                    in_join = False
                    in_order_by = False
                    in_group_by = False
                elif 'WHERE' in token_upper:
                    in_where = True
                    in_from = False
                    in_join = False
                elif 'JOIN' in token_upper:
                    in_join = True
                    in_from = False
                elif 'ORDER BY' in token_upper:
                    in_order_by = True
                    in_where = False
                elif 'GROUP BY' in token_upper:
                    in_group_by = True
                    in_where = False
                elif token_upper in ('LIMIT', 'HAVING', 'UNION'):
                    in_where = False
                    in_order_by = False
                    in_group_by = False
            
            elif isinstance(token, Where):
                in_where = True
                self._extract_columns_from_token(token, result['where_columns'])
            
            elif isinstance(token, (Identifier, IdentifierList)):
                if in_from:
                    self._extract_tables(token, result['tables'])
                elif in_join:
                    self._extract_tables(token, result['tables'])
                    self._extract_join_columns(token, result['join_columns'])
                elif in_where:
                    self._extract_columns_from_token(token, result['where_columns'])
                elif in_order_by:
                    self._extract_columns_from_token(token, result['orderby_columns'])
                elif in_group_by:
                    self._extract_columns_from_token(token, result['groupby_columns'])
                else:
                    self._extract_columns_from_token(token, result['columns'])
            
            elif hasattr(token, 'tokens'):
                sub_result = self._walk_statement(token.tokens, result)
                if sub_result:
                    for key in result:
                        result[key].update(sub_result[key])
        
        return result

    def _extract_tables(self, token, tables: Set[str]):
        if isinstance(token, IdentifierList):
            for identifier in token.get_identifiers():
                self._extract_single_table(identifier, tables)
        elif isinstance(token, Identifier):
            self._extract_single_table(token, tables)

    def _extract_single_table(self, identifier: Identifier, tables: Set[str]):
        name = identifier.get_real_name()
        if name:
            tables.add(name)

    def _extract_columns_from_token(self, token, columns: Set[str]):
        if isinstance(token, IdentifierList):
            for identifier in token.get_identifiers():
                self._extract_single_column(identifier, columns)
        elif isinstance(token, Identifier):
            self._extract_single_column(token, columns)
        elif isinstance(token, Comparison):
            left = token.left
            if isinstance(left, Identifier):
                columns.add(left.get_real_name() or left.value)
        elif hasattr(token, 'tokens'):
            for sub in token.tokens:
                self._extract_columns_from_token(sub, columns)

    def _extract_single_column(self, identifier: Identifier, columns: Set[str]):
        name = identifier.get_real_name()
        if name and name != '*':
            columns.add(name)

    def _extract_join_columns(self, token, columns: Set[str]):
        if hasattr(token, 'tokens'):
            for sub in token.tokens:
                if isinstance(sub, Comparison):
                    if isinstance(sub.left, Identifier):
                        columns.add(sub.left.get_real_name() or sub.left.value)
                    if isinstance(sub.right, Identifier):
                        columns.add(sub.right.get_real_name() or sub.right.value)

    def aggregate_queries(self, queries: List[QueryInfo]) -> Dict[str, QueryInfo]:
        aggregated: Dict[str, QueryInfo] = {}
        
        for query in queries:
            normalized_sql = self._normalize_sql(query.sql)
            
            if normalized_sql in aggregated:
                agg = aggregated[normalized_sql]
                agg.execution_time += query.execution_time
                agg.rows_examined += query.rows_examined
                agg.rows_sent += query.rows_sent
            else:
                aggregated[normalized_sql] = QueryInfo(
                    sql=query.sql,
                    execution_time=query.execution_time,
                    rows_examined=query.rows_examined,
                    rows_sent=query.rows_sent,
                    tables=query.tables.copy(),
                    columns_used=query.columns_used.copy(),
                    where_columns=query.where_columns.copy(),
                    join_columns=query.join_columns.copy(),
                    orderby_columns=query.orderby_columns.copy(),
                    groupby_columns=query.groupby_columns.copy(),
                )
        
        return aggregated

    def _normalize_sql(self, sql: str) -> str:
        sql = re.sub(r'\'[^\']*\'', '?', sql)
        sql = re.sub(r'"[^"]*"', '?', sql)
        sql = re.sub(r'\b\d+\b', '?', sql)
        sql = re.sub(r'\s+', ' ', sql)
        return sql.strip().lower()

    def get_top_queries(self, queries: List[QueryInfo], top_n: int = 10) -> List[QueryInfo]:
        return sorted(queries, key=lambda q: q.execution_time, reverse=True)[:top_n]

    def get_candidate_columns(self, queries: List[QueryInfo], tables: List[str]) -> Dict[str, List[str]]:
        table_columns: Dict[str, List[str]] = {table: [] for table in tables}
        column_scores: Dict[str, Dict[str, float]] = {table: {} for table in tables}
        
        for query in queries:
            weight = max(query.execution_time, 1.0)
            
            for table in query.tables:
                if table in table_columns:
                    for col in query.where_columns:
                        column_scores[table][col] = column_scores[table].get(col, 0) + weight * 2
                    for col in query.join_columns:
                        column_scores[table][col] = column_scores[table].get(col, 0) + weight * 1.5
                    for col in query.orderby_columns:
                        column_scores[table][col] = column_scores[table].get(col, 0) + weight * 1.2
                    for col in query.groupby_columns:
                        column_scores[table][col] = column_scores[table].get(col, 0) + weight * 1.2
        
        for table in tables:
            sorted_cols = sorted(column_scores[table].items(), key=lambda x: x[1], reverse=True)
            table_columns[table] = [col for col, score in sorted_cols if score > 0]
        
        return table_columns
