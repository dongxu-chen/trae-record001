import time
import re
from datetime import datetime
from db_connector import DBConnector


class IndexValidator:
    def __init__(self):
        self.db = DBConnector()
        self._created_indexes = []

    def _parse_index_name(self, table, columns):
        col_str = '_'.join(columns[:3])
        return f"idx_auto_{table}_{col_str}"

    def _extract_columns_from_sql(self, sql):
        where_cols = []
        join_cols = []
        order_cols = []
        group_cols = []
        where_match = re.search(r'WHERE\s+(.+?)(?:ORDER|GROUP|LIMIT|$)', sql, re.IGNORECASE | re.DOTALL)
        if where_match:
            where_clause = where_match.group(1)
            conditions = re.split(r'\s+AND\s+', where_clause, flags=re.IGNORECASE)
            for cond in conditions:
                match = re.match(r'(\w+)\s*[=<>]', cond.strip())
                if match:
                    where_cols.append(match.group(1))
        join_matches = re.findall(r'JOIN\s+\w+\s+ON\s+(\w+)\.(\w+)\s*=\s*(\w+)\.(\w+)', sql, re.IGNORECASE)
        for m in join_matches:
            join_cols.append(m[1])
            join_cols.append(m[3])
        order_match = re.search(r'ORDER\s+BY\s+(.+?)(?:LIMIT|$)', sql, re.IGNORECASE | re.DOTALL)
        if order_match:
            order_parts = order_match.group(1).split(',')
            for p in order_parts:
                col = re.match(r'(\w+)', p.strip())
                if col:
                    order_cols.append(col.group(1))
        group_match = re.search(r'GROUP\s+BY\s+(.+?)(?:ORDER|HAVING|LIMIT|$)', sql, re.IGNORECASE | re.DOTALL)
        if group_match:
            group_parts = group_match.group(1).split(',')
            for p in group_parts:
                col = re.match(r'(\w+)', p.strip())
                if col:
                    group_cols.append(col.group(1))
        return {
            'where_columns': list(set(where_cols)),
            'join_columns': list(set(join_cols)),
            'order_columns': list(set(order_cols)),
            'group_columns': list(set(group_cols))
        }

    def suggest_indexes_for_query(self, sql):
        from sql_parser import SQLParser
        parser = SQLParser()
        analysis = parser.parse(sql)
        table = analysis.get('tables', [''])[0] if analysis.get('tables') else None
        if not table:
            return []
        columns = self._extract_columns_from_sql(sql)
        suggestions = []
        if columns['where_columns']:
            suggestions.append({
                'table': table,
                'columns': columns['where_columns'],
                'type': 'WHERE条件索引',
                'reason': '用于加速WHERE条件过滤'
            })
        if columns['join_columns']:
            suggestions.append({
                'table': table,
                'columns': columns['join_columns'],
                'type': 'JOIN关联索引',
                'reason': '用于加速表连接'
            })
        if columns['order_columns']:
            suggestions.append({
                'table': table,
                'columns': columns['order_columns'],
                'type': 'ORDER BY排序索引',
                'reason': '避免文件排序'
            })
        if columns['group_columns']:
            suggestions.append({
                'table': table,
                'columns': columns['group_columns'],
                'type': 'GROUP BY分组索引',
                'reason': '加速分组聚合'
            })
        if columns['where_columns'] and columns['order_columns']:
            combined = columns['where_columns'] + [c for c in columns['order_columns'] if c not in columns['where_columns']]
            suggestions.append({
                'table': table,
                'columns': combined,
                'type': '复合索引(过滤+排序)',
                'reason': '同时优化过滤和排序'
            })
        return suggestions

    def create_index(self, table, columns, index_name=None, index_type='INDEX'):
        if not index_name:
            index_name = self._parse_index_name(table, columns)
        col_str = ', '.join(columns)
        try:
            existing = self.db.execute_query(f"SHOW INDEX FROM {table} WHERE Key_name = %s", [index_name])
            if existing and existing.get('data') and len(existing['data']) > 0:
                return {
                    'success': True,
                    'index_name': index_name,
                    'table': table,
                    'columns': columns,
                    'created': False,
                    'message': '索引已存在'
                }
            start_time = time.time()
            result = self.db.execute_query(f"CREATE {index_type} INDEX {index_name} ON {table} ({col_str})")
            elapsed = time.time() - start_time
            if result.get('success', True):
                self._created_indexes.append({
                    'index_name': index_name,
                    'table': table,
                    'columns': columns,
                    'created_at': datetime.now().isoformat(),
                    'create_time': elapsed
                })
                return {
                    'success': True,
                    'index_name': index_name,
                    'table': table,
                    'columns': columns,
                    'created': True,
                    'create_time': elapsed,
                    'message': '索引创建成功'
                }
            return {
                'success': False,
                'index_name': index_name,
                'table': table,
                'columns': columns,
                'error': result.get('error', '创建失败')
            }
        except Exception as e:
            return {
                'success': False,
                'index_name': index_name,
                'table': table,
                'columns': columns,
                'error': str(e)
            }

    def drop_index(self, table, index_name):
        try:
            result = self.db.execute_query(f"DROP INDEX {index_name} ON {table}")
            return {
                'success': result.get('success', True),
                'index_name': index_name,
                'table': table
            }
        except Exception as e:
            return {
                'success': False,
                'index_name': index_name,
                'table': table,
                'error': str(e)
            }

    def execute_query_with_timing(self, sql, params=None):
        try:
            start_time = time.time()
            result = self.db.execute_query(sql, params)
            elapsed = time.time() - start_time
            return {
                'success': result.get('success', True),
                'execution_time': elapsed,
                'rows_affected': len(result.get('data', [])) if result.get('data') else 0,
                'error': result.get('error')
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

    def get_explain_plan(self, sql):
        result = self.db.explain_query(sql)
        return result

    def validate_index_improvement(self, sql, table, columns):
        baseline_explain = self.get_explain_plan(sql)
        baseline_time = self.execute_query_with_timing(sql)
        create_result = self.create_index(table, columns)
        if not create_result['success']:
            return {
                'success': False,
                'error': create_result.get('error'),
                'phase': 'create_index'
            }
        new_explain = self.get_explain_plan(sql)
        new_time = self.execute_query_with_timing(sql)
        improvement = self._calculate_improvement(baseline_explain, baseline_time, new_explain, new_time)
        return {
            'success': True,
            'index_created': create_result,
            'baseline': {
                'explain': baseline_explain,
                'execution_time': baseline_time.get('execution_time', 0)
            },
            'after_index': {
                'explain': new_explain,
                'execution_time': new_time.get('execution_time', 0)
            },
            'improvement': improvement
        }

    def _calculate_improvement(self, baseline_explain, baseline_time, new_explain, new_time):
        baseline_rows = 0
        new_rows = 0
        baseline_type = 'ALL'
        new_type = 'ALL'
        baseline_extra = []
        new_extra = []
        if baseline_explain and baseline_explain.get('data'):
            for row in baseline_explain['data']:
                baseline_rows += row.get('rows', 0)
                baseline_type = row.get('type', 'ALL')
                if row.get('Extra'):
                    baseline_extra.append(row['Extra'])
        if new_explain and new_explain.get('data'):
            for row in new_explain['data']:
                new_rows += row.get('rows', 0)
                new_type = row.get('type', 'ALL')
                if row.get('Extra'):
                    new_extra.append(row['Extra'])
        base_time = baseline_time.get('execution_time', 1)
        new_exec_time = new_time.get('execution_time', 0)
        time_improvement = ((base_time - new_exec_time) / base_time) * 100 if base_time > 0 else 0
        row_improvement = ((baseline_rows - new_rows) / baseline_rows) * 100 if baseline_rows > 0 else 0
        access_type_order = ['ALL', 'index', 'range', 'ref', 'eq_ref', 'const', 'system']
        baseline_rank = access_type_order.index(baseline_type) if baseline_type in access_type_order else 0
        new_rank = access_type_order.index(new_type) if new_type in access_type_order else 0
        access_improved = new_rank > baseline_rank
        has_filesort_before = any('Using filesort' in e for e in baseline_extra)
        has_filesort_after = any('Using filesort' in e for e in new_extra)
        has_temporary_before = any('Using temporary' in e for e in baseline_extra)
        has_temporary_after = any('Using temporary' in e for e in new_extra)
        return {
            'time_improvement_percent': round(time_improvement, 2),
            'row_improvement_percent': round(row_improvement, 2),
            'access_type_improved': access_improved,
            'baseline_access_type': baseline_type,
            'new_access_type': new_type,
            'baseline_rows': baseline_rows,
            'new_rows': new_rows,
            'filesort_eliminated': has_filesort_before and not has_filesort_after,
            'temporary_eliminated': has_temporary_before and not has_temporary_after,
            'is_worthwhile': time_improvement > 10 or access_improved or row_improvement > 50,
            'rating': self._rate_improvement(time_improvement, access_improved, has_filesort_before and not has_filesort_after)
        }

    def _rate_improvement(self, time_improvement, access_improved, filesort_eliminated):
        score = 0
        if time_improvement > 50:
            score += 3
        elif time_improvement > 20:
            score += 2
        elif time_improvement > 10:
            score += 1
        if access_improved:
            score += 2
        if filesort_eliminated:
            score += 2
        if score >= 5:
            return 'excellent'
        elif score >= 3:
            return 'good'
        elif score >= 1:
            return 'moderate'
        else:
            return 'minimal'

    def auto_validate_indexes(self, sql, auto_cleanup=True):
        suggestions = self.suggest_indexes_for_query(sql)
        if not suggestions:
            return {
                'success': True,
                'message': '没有索引建议',
                'validations': []
            }
        validations = []
        created_indexes = []
        for suggestion in suggestions:
            result = self.validate_index_improvement(
                sql,
                suggestion['table'],
                suggestion['columns']
            )
            result['suggestion'] = suggestion
            validations.append(result)
            if result.get('index_created', {}).get('created'):
                created_indexes.append({
                    'table': suggestion['table'],
                    'index_name': result['index_created']['index_name']
                })
        if auto_cleanup:
            for idx in created_indexes:
                self.drop_index(idx['table'], idx['index_name'])
        worthwhile = [v for v in validations if v.get('improvement', {}).get('is_worthwhile', False)]
        return {
            'success': True,
            'total_suggestions': len(suggestions),
            'worthwhile_count': len(worthwhile),
            'validations': validations,
            'cleanup_performed': auto_cleanup
        }

    def get_created_indexes(self):
        return self._created_indexes

    def cleanup_created_indexes(self):
        results = []
        for idx in self._created_indexes:
            result = self.drop_index(idx['table'], idx['index_name'])
            results.append(result)
        self._created_indexes = []
        return results

    def get_existing_indexes(self, table):
        result = self.db.execute_query(f"SHOW INDEX FROM {table}")
        if result and result.get('data'):
            indexes = {}
            for row in result['data']:
                key_name = row.get('Key_name')
                if key_name not in indexes:
                    indexes[key_name] = {
                        'name': key_name,
                        'table': table,
                        'columns': [],
                        'unique': row.get('Non_unique') == 0,
                        'cardinality': row.get('Cardinality', 0)
                    }
                indexes[key_name]['columns'].append(row.get('Column_name'))
            return list(indexes.values())
        return []
