#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
EXPLAIN分析模块
分析SQL执行计划，推荐具体的索引创建语句
"""

import re
import json
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple
import sqlparse


@dataclass
class IndexRecommendation:
    table_name: str
    index_columns: List[str]
    index_type: str = 'BTREE'
    index_name: str = ''
    reason: str = ''
    estimated_benefit: int = 0
    create_statement: str = ''
    explain_output: str = ''
    sql_sample: str = ''

    def __post_init__(self):
        if not self.index_name:
            cols = '_'.join(col.replace('.', '_') for col in self.index_columns)
            self.index_name = f"idx_{self.table_name}_{cols}"[:64]

        if not self.create_statement:
            cols_str = ', '.join(f"`{c}`" for c in self.index_columns)
            self.create_statement = (
                f"CREATE INDEX `{self.index_name}` "
                f"ON `{self.table_name}` ({cols_str});"
            )


@dataclass
class ExplainAnalysisResult:
    sql: str
    table_name: str
    has_index: bool = False
    used_index: Optional[str] = None
    type: str = ''
    rows_examined: int = 0
    rows_expected: int = 0
    extra: List[str] = field(default_factory=list)
    recommendations: List[IndexRecommendation] = field(default_factory=list)
    has_full_table_scan: bool = False
    has_filesort: bool = False
    has_temporary: bool = False
    warnings: List[str] = field(default_factory=list)
    explain_output: str = ''


class ExplainAnalyzer:
    def __init__(self, db_type: str = 'mysql'):
        self.db_type = db_type.lower()

    def analyze_sql(self, sql: str, explain_output: Optional[str] = None) -> ExplainAnalysisResult:
        table_name = self._extract_table_name(sql)
        result = ExplainAnalysisResult(
            sql=sql,
            table_name=table_name
        )

        if explain_output:
            result = self._parse_explain_output(explain_output, result)
        else:
            result = self._analyze_sql_structure(sql, result)

        result = self._generate_recommendations(sql, result)

        return result

    def _extract_table_name(self, sql: str) -> str:
        try:
            parsed = sqlparse.parse(sql)
            if parsed:
                for token in parsed[0].tokens:
                    if isinstance(token, sqlparse.sql.IdentifierList):
                        for identifier in token.get_identifiers():
                            return identifier.get_name() or ''
                    elif isinstance(token, sqlparse.sql.Identifier):
                        name = token.get_name()
                        if name and name.upper() not in ('WHERE', 'FROM', 'JOIN', 'INNER', 'LEFT', 'RIGHT'):
                            return name

            patterns = [
                r'FROM\s+`?(\w+)`?',
                r'INTO\s+`?(\w+)`?',
                r'UPDATE\s+`?(\w+)`?',
                r'JOIN\s+`?(\w+)`?',
                r'FROM\s+(\w+\.\w+)',
            ]
            for pattern in patterns:
                match = re.search(pattern, sql, re.IGNORECASE)
                if match:
                    return match.group(1).split('.')[-1].strip('`')
        except Exception:
            pass

        return 'unknown'

    def _parse_explain_output(self, explain_output: str, result: ExplainAnalysisResult) -> ExplainAnalysisResult:
        try:
            if self.db_type == 'mysql':
                result = self._parse_mysql_explain(explain_output, result)
            elif self.db_type == 'postgresql':
                result = self._parse_postgresql_explain(explain_output, result)
        except Exception as e:
            result.warnings.append(f"解析EXPLAIN输出失败: {str(e)}")

        return result

    def _parse_mysql_explain(self, explain_output: str, result: ExplainAnalysisResult) -> ExplainAnalysisResult:
        if explain_output.strip().startswith('{'):
            try:
                explain_json = json.loads(explain_output)
                return self._parse_mysql_explain_json(explain_json, result)
            except json.JSONDecodeError:
                pass

        lines = explain_output.strip().split('\n')
        if len(lines) < 2:
            return result

        header = lines[0]
        cols = re.split(r'\s{2,}|\t', header)
        col_indices = {}
        for i, col in enumerate(cols):
            col_indices[col.lower()] = i

        for line in lines[1:]:
            if not line.strip():
                continue
            parts = re.split(r'\s{2,}|\t', line)
            if len(parts) < len(col_indices):
                continue

            if 'type' in col_indices and col_indices['type'] < len(parts):
                result.type = parts[col_indices['type']].strip()
                if result.type in ('ALL', 'index'):
                    result.has_full_table_scan = True

            if 'key' in col_indices and col_indices['key'] < len(parts):
                used_key = parts[col_indices['key']].strip()
                if used_key and used_key != 'NULL':
                    result.used_index = used_key
                    result.has_index = True

            if 'rows' in col_indices and col_indices['rows'] < len(parts):
                try:
                    result.rows_expected = int(parts[col_indices['rows']].strip())
                except ValueError:
                    pass

            if 'extra' in col_indices and col_indices['extra'] < len(parts):
                extra = parts[col_indices['extra']].strip()
                if extra:
                    result.extra.append(extra)
                    if 'Using filesort' in extra:
                        result.has_filesort = True
                    if 'Using temporary' in extra:
                        result.has_temporary = True
                    if 'Using where' in extra and not result.has_index:
                        result.warnings.append("使用WHERE条件但未使用索引，建议添加索引")

        result.explain_output = explain_output
        return result

    def _parse_mysql_explain_json(self, explain_json: Dict[str, Any], result: ExplainAnalysisResult) -> ExplainAnalysisResult:
        query_block = explain_json.get('query_block', {})

        if 'table' in query_block:
            table_data = query_block['table']
            result.table_name = table_data.get('table_name', result.table_name)
            result.type = table_data.get('access_type', '')

            if result.type in ('ALL', 'index'):
                result.has_full_table_scan = True

            if 'key' in table_data and table_data['key']:
                result.used_index = table_data['key']
                result.has_index = True

            if 'rows_examined_per_scan' in table_data:
                result.rows_examined = table_data['rows_examined_per_scan']
            if 'rows_produced_per_join' in table_data:
                result.rows_expected = table_data['rows_produced_per_join']

            if 'used_columns' in table_data:
                result.warnings.append(f"使用列: {', '.join(table_data['used_columns'])}")

        if 'attached_condition' in query_block:
            result.extra.append(f"WHERE条件: {query_block['attached_condition']}")

        if 'filesort' in explain_json:
            result.has_filesort = True
            result.extra.append("使用filesort排序")

        if 'using_temporary_table' in explain_json:
            result.has_temporary = True
            result.extra.append("使用临时表")

        result.explain_output = json.dumps(explain_json, indent=2, ensure_ascii=False)
        return result

    def _parse_postgresql_explain(self, explain_output: str, result: ExplainAnalysisResult) -> ExplainAnalysisResult:
        if 'Seq Scan' in explain_output:
            result.has_full_table_scan = True
            result.type = 'Seq Scan'
            result.warnings.append("使用顺序扫描，建议添加索引")

        if 'Index Scan' in explain_output:
            result.has_index = True
            match = re.search(r'Index Scan using (\w+)', explain_output)
            if match:
                result.used_index = match.group(1)

        if 'Sort' in explain_output:
            result.has_filesort = True

        if 'HashAggregate' in explain_output:
            result.has_temporary = True

        rows_match = re.search(r'rows=(\d+)', explain_output)
        if rows_match:
            try:
                result.rows_expected = int(rows_match.group(1))
            except ValueError:
                pass

        result.explain_output = explain_output
        return result

    def _analyze_sql_structure(self, sql: str, result: ExplainAnalysisResult) -> ExplainAnalysisResult:
        where_cols = self._extract_where_columns(sql)
        join_cols = self._extract_join_columns(sql)
        order_cols = self._extract_order_columns(sql)
        group_cols = self._extract_group_columns(sql)

        all_cols = list(dict.fromkeys(where_cols + join_cols + order_cols + group_cols))

        if not where_cols and not join_cols and not order_cols and not group_cols:
            result.warnings.append("SQL缺少WHERE条件或索引列，可能导致全表扫描")

        if 'SELECT *' in sql.upper():
            result.warnings.append("使用SELECT *，建议只查询需要的列")

        if 'LIKE' in sql.upper() and '%' in sql:
            like_match = re.search(r"LIKE\s+'?%(\w+)", sql, re.IGNORECASE)
            if like_match:
                result.warnings.append("前导通配符LIKE查询无法使用索引")

        if 'ORDER BY' in sql.upper() and not result.has_index:
            result.warnings.append("ORDER BY缺少合适索引，可能导致filesort")

        if 'GROUP BY' in sql.upper() and not result.has_index:
            result.warnings.append("GROUP BY缺少合适索引，可能使用临时表")

        result.sql_sample = sql[:200]
        return result

    def _extract_where_columns(self, sql: str) -> List[str]:
        cols = []
        where_match = re.search(r'WHERE\s+(.+?)(?:ORDER BY|GROUP BY|LIMIT|$)', sql, re.IGNORECASE | re.DOTALL)
        if not where_match:
            return cols

        where_clause = where_match.group(1)

        patterns = [
            r'(\w+\.\w+|\w+)\s*=\s*',
            r'(\w+\.\w+|\w+)\s+IN\s*\(',
            r'(\w+\.\w+|\w+)\s+BETWEEN\s+',
            r'(\w+\.\w+|\w+)\s*>\s*',
            r'(\w+\.\w+|\w+)\s*<\s*',
            r'(\w+\.\w+|\w+)\s*>=\s*',
            r'(\w+\.\w+|\w+)\s*<=\s*',
            r'(\w+\.\w+|\w+)\s+LIKE\s+',
        ]

        for pattern in patterns:
            for match in re.finditer(pattern, where_clause, re.IGNORECASE):
                col = match.group(1)
                col = col.split('.')[-1]
                if col not in cols and col.lower() not in ('and', 'or', 'not'):
                    cols.append(col)

        return cols

    def _extract_join_columns(self, sql: str) -> List[str]:
        cols = []
        join_matches = re.finditer(r'JOIN\s+.+?\s+ON\s+(.+?)(?:\s+JOIN|\s+WHERE|\s+ORDER|$)', sql, re.IGNORECASE | re.DOTALL)

        for match in join_matches:
            on_clause = match.group(1)
            on_cols = re.findall(r'(\w+\.\w+|\w+)\s*=\s*', on_clause)
            for col in on_cols:
                col = col.split('.')[-1]
                if col not in cols:
                    cols.append(col)

        return cols

    def _extract_order_columns(self, sql: str) -> List[str]:
        cols = []
        order_match = re.search(r'ORDER BY\s+(.+?)(?:LIMIT|$)', sql, re.IGNORECASE | re.DOTALL)
        if order_match:
            order_clause = order_match.group(1)
            col_matches = re.findall(r'(\w+\.\w+|\w+)(?:\s+(?:ASC|DESC))?', order_clause, re.IGNORECASE)
            for col in col_matches:
                col = col.split('.')[-1]
                if col not in cols and col.lower() not in ('asc', 'desc', ','):
                    cols.append(col)
        return cols

    def _extract_group_columns(self, sql: str) -> List[str]:
        cols = []
        group_match = re.search(r'GROUP BY\s+(.+?)(?:HAVING|ORDER|$)', sql, re.IGNORECASE | re.DOTALL)
        if group_match:
            group_clause = group_match.group(1)
            col_matches = re.findall(r'(\w+\.\w+|\w+)', group_clause, re.IGNORECASE)
            for col in col_matches:
                col = col.split('.')[-1]
                if col not in cols and col.lower() not in ('and', 'or'):
                    cols.append(col)
        return cols

    def _generate_recommendations(self, sql: str, result: ExplainAnalysisResult) -> ExplainAnalysisResult:
        where_cols = self._extract_where_columns(sql)
        join_cols = self._extract_join_columns(sql)
        order_cols = self._extract_order_columns(sql)
        group_cols = self._extract_group_columns(sql)

        if result.table_name == 'unknown':
            return result

        if not result.has_index:
            if where_cols:
                rec = IndexRecommendation(
                    table_name=result.table_name,
                    index_columns=where_cols,
                    reason=f"WHERE条件列: {', '.join(where_cols)}",
                    estimated_benefit="避免全表扫描，大幅提升查询性能",
                    sql_sample=sql[:200]
                )
                if result.has_full_table_scan:
                    rec.reason += "，当前存在全表扫描"
                result.recommendations.append(rec)

            if join_cols and join_cols not in [r.index_columns for r in result.recommendations]:
                rec = IndexRecommendation(
                    table_name=result.table_name,
                    index_columns=join_cols,
                    reason=f"JOIN连接列: {', '.join(join_cols)}",
                    estimated_benefit="提升JOIN查询效率",
                    sql_sample=sql[:200]
                )
                result.recommendations.append(rec)

            if order_cols and not result.has_index:
                combined_cols = list(dict.fromkeys(where_cols + order_cols))
                if combined_cols and combined_cols not in [r.index_columns for r in result.recommendations]:
                    rec = IndexRecommendation(
                        table_name=result.table_name,
                        index_columns=combined_cols,
                        reason=f"WHERE+ORDER BY组合: {', '.join(combined_cols)}",
                        estimated_benefit="避免filesort，提升排序性能",
                        sql_sample=sql[:200]
                    )
                    result.recommendations.append(rec)

            if group_cols and not result.has_index:
                combined_cols = list(dict.fromkeys(where_cols + group_cols))
                if combined_cols and combined_cols not in [r.index_columns for r in result.recommendations]:
                    rec = IndexRecommendation(
                        table_name=result.table_name,
                        index_columns=combined_cols,
                        reason=f"WHERE+GROUP BY组合: {', '.join(combined_cols)}",
                        estimated_benefit="避免临时表，提升分组聚合性能",
                        sql_sample=sql[:200]
                    )
                    result.recommendations.append(rec)

        if result.has_filesort and order_cols:
            existing_cols = [r.index_columns for r in result.recommendations]
            if where_cols:
                combined_cols = list(dict.fromkeys(where_cols + order_cols))
                if combined_cols not in existing_cols:
                    rec = IndexRecommendation(
                        table_name=result.table_name,
                        index_columns=combined_cols,
                        reason=f"消除filesort: {', '.join(combined_cols)}",
                        estimated_benefit="避免磁盘排序，显著提升ORDER BY性能",
                        sql_sample=sql[:200]
                    )
                    result.recommendations.append(rec)

        if result.has_temporary and group_cols:
            existing_cols = [r.index_columns for r in result.recommendations]
            if where_cols:
                combined_cols = list(dict.fromkeys(where_cols + group_cols))
                if combined_cols not in existing_cols:
                    rec = IndexRecommendation(
                        table_name=result.table_name,
                        index_columns=combined_cols,
                        reason=f"消除临时表: {', '.join(combined_cols)}",
                        estimated_benefit="避免磁盘临时表，提升GROUP BY性能",
                        sql_sample=sql[:200]
                    )
                    result.recommendations.append(rec)

        for rec in result.recommendations:
            rec.explain_output = result.explain_output

        return result

    def analyze_multiple(self, sqls: List[str], explain_outputs: Optional[Dict[str, str]] = None) -> List[ExplainAnalysisResult]:
        results = []
        explain_outputs = explain_outputs or {}

        for sql in sqls:
            normalized_sql = sql.strip()[:200]
            explain_out = explain_outputs.get(normalized_sql)
            result = self.analyze_sql(sql, explain_out)
            results.append(result)

        return results

    def get_all_recommendations(self, results: List[ExplainAnalysisResult]) -> List[IndexRecommendation]:
        all_recs = []
        seen_keys = set()

        for result in results:
            for rec in result.recommendations:
                key = f"{rec.table_name}_{'_'.join(rec.index_columns)}"
                if key not in seen_keys:
                    seen_keys.add(key)
                    all_recs.append(rec)

        return all_recs
