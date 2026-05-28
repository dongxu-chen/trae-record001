import re
from collections import defaultdict
from sql_parser import parse_sql, extract_table_aliases


class QueryOptimizer:
    TRANSFORM_STRATEGIES = {
        'subquery_to_join': {
            'name': '子查询改JOIN',
            'description': '将相关子查询改写为JOIN，通常性能更好',
            'pattern': r'\(SELECT\s+.*?\s+FROM\s+(\w+)\s+WHERE\s+.*?\s*=\s*.*?\)',
            'benefit': '减少子查询重复执行，利用JOIN优化器'
        },
        'not_in_to_left_join': {
            'name': 'NOT IN改LEFT JOIN',
            'description': '将NOT IN子查询改写为LEFT JOIN...WHERE NULL',
            'pattern': r'NOT\s+IN\s*\(\s*SELECT\s+.*?\s+FROM\s+(\w+)',
            'benefit': '避免NULL值问题，更好利用索引'
        },
        'or_to_union': {
            'name': 'OR改UNION ALL',
            'description': '将OR条件拆分为UNION ALL，各自利用索引',
            'pattern': r'\bOR\b',
            'benefit': '每个分支可独立使用索引'
        },
        'union_to_union_all': {
            'name': 'UNION改UNION ALL',
            'description': '如果确定无重复数据，使用UNION ALL替代UNION',
            'pattern': r'\bUNION\b(?!\s+ALL)',
            'benefit': '避免去重排序开销'
        },
        'count_star_to_count_1': {
            'name': 'COUNT(*)改COUNT(1)',
            'description': '在某些引擎中COUNT(1)比COUNT(*)更快',
            'pattern': r'COUNT\(\*\)',
            'benefit': '轻微性能提升'
        },
        'offset_to_cursor': {
            'name': 'OFFSET改游标分页',
            'description': '将LIMIT offset, size改为WHERE id > last_id LIMIT size',
            'pattern': r'LIMIT\s+\d+\s*,\s*\d+',
            'benefit': '避免扫描大量不需要的行'
        },
        'implicit_join_to_explicit': {
            'name': '隐式JOIN改显式JOIN',
            'description': '将逗号分隔的表改为显式JOIN...ON',
            'pattern': r'FROM\s+\w+\s*,\s*\w+\s+WHERE',
            'benefit': '更清晰的语义，更好的优化器支持'
        },
        'function_on_column_to_range': {
            'name': '列上函数改范围查询',
            'description': '将DATE(col) = ? 改为 col >= ? AND col < ?',
            'pattern': r'(DATE|YEAR|MONTH)\s*\(\s*\w+\s*\)\s*=',
            'benefit': '允许使用列上的索引'
        },
        'select_star_to_specific': {
            'name': 'SELECT *改指定列',
            'description': '明确指定所需列名',
            'pattern': r'SELECT\s+\*',
            'benefit': '减少数据传输，可能使用覆盖索引'
        },
        'distinct_to_group_by': {
            'name': 'DISTINCT改GROUP BY',
            'description': '在某些情况下GROUP BY比DISTINCT更高效',
            'pattern': r'SELECT\s+DISTINCT',
            'benefit': '可能更好利用索引'
        },
        'null_comparison_fix': {
            'name': 'NULL比较修正',
            'description': '将= NULL改为IS NULL，!= NULL改为IS NOT NULL',
            'pattern': r'[=!<>]=\s*NULL',
            'benefit': '正确的语义，可能使用索引'
        },
        'string_to_int_cast': {
            'name': '字符串转整数修正',
            'description': '将col = \'123\'改为col = 123（如果col是整数类型）',
            'pattern': r"=\s*'\d+'",
            'benefit': '避免隐式类型转换，使用索引'
        }
    }

    def __init__(self):
        self.rewrite_rules = self._init_rewrite_rules()

    def _init_rewrite_rules(self):
        return {
            'select_star': {
                'pattern': r'SELECT\s+\*',
                'message': '避免使用 SELECT *',
                'suggestion': '明确指定需要的列名，减少数据传输和内存消耗',
                'example': 'SELECT id, name, email FROM users'
            },
            'select_distinct': {
                'pattern': r'SELECT\s+DISTINCT',
                'message': '使用 DISTINCT 可能影响性能',
                'suggestion': '考虑使用 GROUP BY 或 EXISTS 替代 DISTINCT',
                'example': 'SELECT id FROM users GROUP BY id'
            },
            'like_prefix_wildcard': {
                'pattern': r"LIKE\s+['\"]%",
                'message': 'LIKE 前导通配符无法使用索引',
                'suggestion': '避免前导通配符，或考虑使用全文索引',
                'example': "WHERE name LIKE '张%' 代替 WHERE name LIKE '%张%'"
            },
            'or_in_where': {
                'pattern': r'\bOR\b',
                'message': 'OR 条件可能导致索引失效',
                'suggestion': '使用 UNION ALL 替代 OR，或确保 OR 两端列都有索引',
                'example': "WHERE a = 1 UNION ALL WHERE b = 2"
            },
            'null_comparison': {
                'pattern': r'[=!<>]=\s*NULL',
                'message': 'NULL 比较写法不正确',
                'suggestion': '使用 IS NULL 或 IS NOT NULL 代替 = NULL 或 != NULL',
                'example': "WHERE col IS NULL 代替 WHERE col = NULL"
            },
            'implicit_cast': {
                'pattern': r"WHERE\s+\w+\s*=\s*'\d+'|WHERE\s+\w+\s*=\s*\d+",
                'message': '可能存在隐式类型转换',
                'suggestion': '确保比较两侧类型一致，避免隐式转换导致索引失效',
                'example': "WHERE id = 123 代替 WHERE id = '123'"
            },
            'function_on_column': {
                'pattern': r'WHERE\s+\w+\(\s*\w+\s*\)',
                'message': '在列上使用函数会导致索引失效',
                'suggestion': '改写查询条件，将函数移到值侧或使用函数索引',
                'example': "WHERE created_at >= '2024-01-01' 代替 WHERE DATE(created_at) = '2024-01-01'"
            },
            'order_by_rand': {
                'pattern': r'ORDER\s+BY\s+RAND\(\)',
                'message': 'ORDER BY RAND() 性能极差',
                'suggestion': '使用子查询或 JOIN 方式替代 ORDER BY RAND()',
                'example': 'SELECT * FROM table WHERE id >= (SELECT RAND() * MAX(id) FROM table) LIMIT 1'
            },
            'limit_offset': {
                'pattern': r'LIMIT\s+\d+\s*,\s*\d+',
                'message': 'LIMIT 大偏移量分页性能差',
                'suggestion': '使用游标分页（WHERE id > last_id LIMIT N）替代 OFFSET 分页',
                'example': 'WHERE id > 100000 LIMIT 10 代替 LIMIT 100000, 10'
            },
            'not_in_subquery': {
                'pattern': r'NOT\s+IN\s*\(SELECT',
                'message': 'NOT IN 子查询可能性能较差',
                'suggestion': '使用 LEFT JOIN ... WHERE NULL 或 NOT EXISTS 替代 NOT IN',
                'example': 'SELECT a.* FROM a LEFT JOIN b ON a.id = b.id WHERE b.id IS NULL'
            },
            'count_star': {
                'pattern': r'COUNT\(\*\)',
                'message': 'COUNT(*) 在某些引擎下可能较慢',
                'suggestion': '对于大表，考虑使用 COUNT(1) 或近似计数（information_schema）',
                'example': "SELECT COUNT(1) FROM table 或 SHOW TABLE STATUS"
            },
            'update_without_limit': {
                'pattern': r'UPDATE\s+\w+\s+SET(?!.*LIMIT)',
                'message': 'UPDATE 缺少 LIMIT 限制',
                'suggestion': '添加 LIMIT 限制批量更新，避免锁表',
                'example': 'UPDATE table SET col = val WHERE condition LIMIT 1000'
            },
            'delete_without_limit': {
                'pattern': r'DELETE\s+FROM\s+\w+(?!.*LIMIT)',
                'message': 'DELETE 缺少 LIMIT 限制',
                'suggestion': '添加 LIMIT 限制批量删除，避免锁表',
                'example': 'DELETE FROM table WHERE condition LIMIT 1000'
            }
        }

    def analyze_query(self, sql, explain_analysis=None):
        suggestions = []
        sql_upper = sql.upper().strip()

        sql_analysis = parse_sql(sql)
        suggestions.extend(self._check_sql_patterns(sql))
        suggestions.extend(self._check_sql_analysis(sql_analysis))

        if explain_analysis:
            suggestions.extend(self._check_explain_issues(explain_analysis))

        suggestions.sort(key=lambda x: {'high': 0, 'medium': 1, 'low': 2}.get(x.get('priority', 'low'), 2))
        return suggestions

    def _check_sql_patterns(self, sql):
        suggestions = []
        for rule_name, rule in self.rewrite_rules.items():
            pattern = rule['pattern']
            if re.search(pattern, sql, re.IGNORECASE):
                priority = 'high' if rule_name in ['select_star', 'like_prefix_wildcard', 'order_by_rand', 'function_on_column'] else 'medium'
                suggestions.append({
                    'type': 'pattern_match',
                    'rule': rule_name,
                    'priority': priority,
                    'message': rule['message'],
                    'suggestion': rule['suggestion'],
                    'example': rule['example']
                })
        return suggestions

    def _check_sql_analysis(self, analysis):
        suggestions = []
        if analysis.get('has_subquery'):
            suggestions.append({
                'type': 'analysis',
                'priority': 'medium',
                'message': '查询包含子查询',
                'suggestion': '考虑将子查询改写为 JOIN，通常性能更好'
            })
        if analysis.get('has_union'):
            suggestions.append({
                'type': 'analysis',
                'priority': 'low',
                'message': '查询包含 UNION',
                'suggestion': '确保 UNION 两侧的查询都能有效利用索引'
            })
        if analysis.get('has_implicit_cast'):
            suggestions.append({
                'type': 'analysis',
                'priority': 'high',
                'message': '可能存在隐式类型转换',
                'suggestion': '确保比较两侧类型一致，避免隐式转换导致索引失效'
            })
        if analysis.get('has_like_prefix'):
            suggestions.append({
                'type': 'analysis',
                'priority': 'high',
                'message': 'LIKE 前导通配符无法使用索引',
                'suggestion': '避免前导通配符，或考虑使用全文索引'
            })
        if analysis.get('has_null_comparison'):
            suggestions.append({
                'type': 'analysis',
                'priority': 'medium',
                'message': 'NULL 比较写法不正确',
                'suggestion': '使用 IS NULL 或 IS NOT NULL 代替 = NULL'
            })
        if analysis.get('has_or_in_where'):
            suggestions.append({
                'type': 'analysis',
                'priority': 'medium',
                'message': 'WHERE 子句包含 OR 条件',
                'suggestion': '使用 UNION ALL 替代 OR，或确保 OR 两端列都有索引'
            })
        if analysis.get('uses_select_star'):
            suggestions.append({
                'type': 'analysis',
                'priority': 'high',
                'message': '使用 SELECT * 选择所有列',
                'suggestion': '明确指定需要的列名，减少数据传输和内存消耗'
            })
        return suggestions

    def _check_explain_issues(self, explain_analysis):
        suggestions = []
        if explain_analysis.get('has_full_table_scan'):
            table_scans = explain_analysis.get('table_scans', [])
            for scan in table_scans:
                suggestions.append({
                    'type': 'explain',
                    'priority': 'high',
                    'message': f"表 {scan['table']} 存在全表扫描（扫描 {scan['rows']} 行）",
                    'suggestion': '为 WHERE/JOIN 条件涉及的列添加索引，避免全表扫描'
                })
        if explain_analysis.get('has_temporary'):
            suggestions.append({
                'type': 'explain',
                'priority': 'high',
                'message': '执行计划中出现 Using temporary',
                'suggestion': '检查 GROUP BY 和 ORDER BY 字段，考虑添加复合索引覆盖排序字段'
            })
        if explain_analysis.get('has_filesort'):
            suggestions.append({
                'type': 'explain',
                'priority': 'medium',
                'message': '执行计划中出现 Using filesort',
                'suggestion': '为 ORDER BY 字段添加索引，或调整查询顺序'
            })
        if explain_analysis.get('has_index_merge'):
            suggestions.append({
                'type': 'explain',
                'priority': 'low',
                'message': '使用了索引合并（Index Merge）',
                'suggestion': '考虑创建复合索引替代索引合并，提高查询效率'
            })
        total_rows = explain_analysis.get('total_rows_examined', 0)
        if total_rows > 100000:
            suggestions.append({
                'type': 'explain',
                'priority': 'high',
                'message': f"预计扫描行数过多：{total_rows} 行",
                'suggestion': '优化查询条件，添加合适的索引以减少扫描行数'
            })
        return suggestions

    def suggest_indexes(self, sql, table_info=None):
        index_suggestions = []
        sql_analysis = parse_sql(sql)
        where_columns = []
        for cond in sql_analysis.get('where_conditions', []):
            col = cond.get('column', '')
            if col and col != '*':
                where_columns.append(col)
        join_columns = []
        tables = sql_analysis.get('tables', [])
        group_by = sql_analysis.get('group_by', [])
        order_by = sql_analysis.get('order_by', [])

        if where_columns:
            for table in tables:
                for col in where_columns:
                    col_name = col.split('.')[-1] if '.' in col else col
                    index_suggestions.append({
                        'table': table,
                        'columns': [col_name],
                        'index_type': 'B-tree',
                        'reason': f"WHERE 条件中使用了 {col_name}"
                    })
        if group_by:
            for table in tables:
                index_suggestions.append({
                    'table': table,
                    'columns': group_by,
                    'index_type': 'B-tree',
                    'reason': f"GROUP BY 字段: {', '.join(group_by)}"
                })
        if order_by:
            for table in tables:
                index_suggestions.append({
                    'table': table,
                    'columns': order_by,
                    'index_type': 'B-tree',
                    'reason': f"ORDER BY 字段: {', '.join(order_by)}"
                })
        if where_columns and order_by:
            for table in tables:
                combined = where_columns + order_by
                if len(set(combined)) > len(where_columns):
                    index_suggestions.append({
                        'table': table,
                        'columns': combined,
                        'index_type': '复合索引',
                        'reason': '同时覆盖 WHERE 和 ORDER BY 条件，避免文件排序'
                    })
        index_suggestions = self._deduplicate_index_suggestions(index_suggestions)
        return index_suggestions

    def _deduplicate_index_suggestions(self, suggestions):
        seen = set()
        result = []
        for s in suggestions:
            key = (s['table'], tuple(sorted(s['columns'])))
            if key not in seen:
                seen.add(key)
                result.append(s)
        return result

    def generate_equivalent_transforms(self, sql):
        transforms = []
        sql_upper = sql.upper().strip()

        if re.search(r'SELECT\s+DISTINCT', sql, re.IGNORECASE) and re.search(r'FROM\s+(\w+)', sql, re.IGNORECASE):
            table_match = re.search(r'FROM\s+(\w+)', sql, re.IGNORECASE)
            if table_match:
                table = table_match.group(1)
                transformed = re.sub(
                    r'SELECT\s+DISTINCT\s+(.*?)\s+FROM\s+' + table,
                    r'SELECT \1 FROM ' + table + ' GROUP BY \1',
                    sql,
                    flags=re.IGNORECASE | re.DOTALL
                )
                if transformed != sql:
                    transforms.append({
                        'type': 'distinct_to_group_by',
                        'name': 'DISTINCT改GROUP BY',
                        'original': sql,
                        'transformed': transformed,
                        'estimated_improvement': 'medium',
                        'reason': 'GROUP BY可能更好利用索引'
                    })

        if re.search(r'NOT\s+IN\s*\(\s*SELECT', sql, re.IGNORECASE):
            transforms.append({
                'type': 'not_in_to_left_join',
                'name': 'NOT IN改LEFT JOIN',
                'original': sql,
                'transformed': None,
                'estimated_improvement': 'high',
                'reason': 'LEFT JOIN可以避免NULL值问题并更好利用索引',
                'hint': '将NOT IN子查询改写为LEFT JOIN...WHERE b.id IS NULL'
            })

        if re.search(r'\bOR\b', sql, re.IGNORECASE) and 'WHERE' in sql_upper:
            transforms.append({
                'type': 'or_to_union',
                'name': 'OR改UNION ALL',
                'original': sql,
                'transformed': None,
                'estimated_improvement': 'medium',
                'reason': '每个分支可以独立使用索引',
                'hint': '将OR条件拆分为多个SELECT，使用UNION ALL合并'
            })

        if re.search(r'\bUNION\b(?!\s+ALL)', sql, re.IGNORECASE):
            transformed = re.sub(r'\bUNION\b', 'UNION ALL', sql, flags=re.IGNORECASE)
            transforms.append({
                'type': 'union_to_union_all',
                'name': 'UNION改UNION ALL',
                'original': sql,
                'transformed': transformed,
                'estimated_improvement': 'medium',
                'reason': '避免去重排序开销（请确保无重复数据）'
            })

        if re.search(r'LIMIT\s+\d+\s*,\s*\d+', sql, re.IGNORECASE):
            transforms.append({
                'type': 'offset_to_cursor',
                'name': 'OFFSET改游标分页',
                'original': sql,
                'transformed': None,
                'estimated_improvement': 'high',
                'reason': '避免扫描大量不需要的行',
                'hint': '使用 WHERE id > last_id LIMIT N 替代 LIMIT offset, N'
            })

        if re.search(r'DATE\s*\(\s*\w+\s*\)\s*=', sql, re.IGNORECASE):
            transforms.append({
                'type': 'function_on_column_to_range',
                'name': 'DATE函数改范围查询',
                'original': sql,
                'transformed': None,
                'estimated_improvement': 'high',
                'reason': '允许使用列上的索引',
                'hint': '将 DATE(col) = ? 改为 col >= ? AND col < ?+1天'
            })

        if re.search(r'SELECT\s+\*', sql, re.IGNORECASE):
            transforms.append({
                'type': 'select_star_to_specific',
                'name': 'SELECT *改指定列',
                'original': sql,
                'transformed': None,
                'estimated_improvement': 'medium',
                'reason': '减少数据传输，可能使用覆盖索引',
                'hint': '明确指定所需的列名'
            })

        if re.search(r'=\s*NULL', sql, re.IGNORECASE) or re.search(r'!=\s*NULL', sql, re.IGNORECASE):
            transformed = re.sub(r'(?<![<>!])=\s*NULL', ' IS NULL', sql, flags=re.IGNORECASE)
            transformed = re.sub(r'!=\s*NULL', ' IS NOT NULL', transformed, flags=re.IGNORECASE)
            transformed = re.sub(r'<>\s*NULL', ' IS NOT NULL', transformed, flags=re.IGNORECASE)
            if transformed != sql:
                transforms.append({
                    'type': 'null_comparison_fix',
                    'name': 'NULL比较修正',
                    'original': sql,
                    'transformed': transformed,
                    'estimated_improvement': 'medium',
                    'reason': '正确的NULL比较，可能使用索引'
                })

        if re.search(r"=\s*'\d+'", sql, re.IGNORECASE):
            transforms.append({
                'type': 'string_to_int_cast',
                'name': '字符串转整数修正',
                'original': sql,
                'transformed': None,
                'estimated_improvement': 'medium',
                'reason': '避免隐式类型转换',
                'hint': "将 col = '123' 改为 col = 123（如果col是整数类型）"
            })

        return transforms

    def estimate_cost(self, sql, table_info=None):
        base_cost = 100
        costs = []

        if re.search(r'SELECT\s+\*', sql, re.IGNORECASE):
            costs.append({'factor': 'SELECT *', 'penalty': 20})
            base_cost += 20

        if re.search(r'SELECT\s+DISTINCT', sql, re.IGNORECASE):
            costs.append({'factor': 'DISTINCT', 'penalty': 30})
            base_cost += 30

        if re.search(r'\bOR\b', sql, re.IGNORECASE):
            costs.append({'factor': 'OR条件', 'penalty': 25})
            base_cost += 25

        if re.search(r'NOT\s+IN\s*\(\s*SELECT', sql, re.IGNORECASE):
            costs.append({'factor': 'NOT IN子查询', 'penalty': 40})
            base_cost += 40

        if re.search(r'ORDER\s+BY\s+RAND\(\)', sql, re.IGNORECASE):
            costs.append({'factor': 'ORDER BY RAND()', 'penalty': 100})
            base_cost += 100

        if re.search(r'LIMIT\s+\d+\s*,\s*\d+', sql, re.IGNORECASE):
            limit_match = re.search(r'LIMIT\s+(\d+)\s*,\s*\d+', sql, re.IGNORECASE)
            if limit_match:
                offset = int(limit_match.group(1))
                penalty = min(offset / 1000, 50)
                costs.append({'factor': f'LIMIT OFFSET ({offset})', 'penalty': penalty})
                base_cost += penalty

        if re.search(r'DATE\s*\(\s*\w+\s*\)\s*=', sql, re.IGNORECASE):
            costs.append({'factor': '列上函数', 'penalty': 35})
            base_cost += 35

        if re.search(r"LIKE\s+['\"]%", sql, re.IGNORECASE):
            costs.append({'factor': '前导LIKE', 'penalty': 25})
            base_cost += 25

        if re.search(r'[=!<>]=\s*NULL', sql, re.IGNORECASE):
            costs.append({'factor': 'NULL比较', 'penalty': 15})
            base_cost += 15

        if re.search(r'\bUNION\b(?!\s+ALL)', sql, re.IGNORECASE):
            costs.append({'factor': 'UNION(非ALL)', 'penalty': 30})
            base_cost += 30

        if re.search(r"=\s*'\d+'", sql, re.IGNORECASE):
            costs.append({'factor': '隐式类型转换', 'penalty': 20})
            base_cost += 20

        if re.search(r'\(SELECT', sql, re.IGNORECASE):
            costs.append({'factor': '子查询', 'penalty': 25})
            base_cost += 25

        if re.search(r'FROM\s+\w+\s*,\s*\w+', sql, re.IGNORECASE):
            costs.append({'factor': '隐式JOIN', 'penalty': 15})
            base_cost += 15

        rating = 'A'
        if base_cost >= 150:
            rating = 'C'
        elif base_cost >= 100:
            rating = 'B'
        if base_cost >= 250:
            rating = 'D'
        if base_cost >= 400:
            rating = 'E'

        return {
            'base_cost': base_cost,
            'rating': rating,
            'cost_factors': costs,
            'estimated_rows': self._estimate_rows(sql, table_info)
        }

    def _estimate_rows(self, sql, table_info=None):
        tables = re.findall(r'FROM\s+(\w+)', sql, re.IGNORECASE)
        if not tables:
            return 0
        base_rows = 10000
        if table_info:
            for t in tables:
                if t in table_info:
                    base_rows = max(base_rows, table_info[t].get('rows', 10000))
        return base_rows

    def rewrite_query(self, sql):
        original = sql
        rewritten = sql
        rewrite_actions = []

        if re.search(r'SELECT\s+\*', rewritten, re.IGNORECASE):
            rewrite_actions.append({
                'action': '警告',
                'detail': '检测到 SELECT *，建议手动明确指定所需列名'
            })

        if re.search(r'ORDER\s+BY\s+RAND\(\)', rewritten, re.IGNORECASE):
            rewrite_actions.append({
                'action': '建议',
                'detail': 'ORDER BY RAND() 性能极差，建议使用子查询加 LIMIT 方式替代'
            })

        if re.search(r"\b=\s*NULL", rewritten, re.IGNORECASE):
            rewritten = re.sub(r"(?<![<>!])=\s*NULL", " IS NULL", rewritten, flags=re.IGNORECASE)
            rewrite_actions.append({
                'action': '修正',
                'detail': '将 = NULL 修正为 IS NULL'
            })

        if re.search(r"!=\s*NULL|<>\s*NULL", rewritten, re.IGNORECASE):
            rewritten = re.sub(r"(!=|<>)\s*NULL", " IS NOT NULL", rewritten, flags=re.IGNORECASE)
            rewrite_actions.append({
                'action': '修正',
                'detail': '将 != NULL/<> NULL 修正为 IS NOT NULL'
            })

        if re.search(r'LIMIT\s+\d+\s*,\s*\d+', rewritten, re.IGNORECASE):
            rewrite_actions.append({
                'action': '建议',
                'detail': 'LIMIT 大偏移量分页性能差，建议使用游标分页（WHERE id > last_id LIMIT N）'
            })

        return {
            'original': original,
            'rewritten': rewritten,
            'actions': rewrite_actions,
            'has_changes': original != rewritten
        }

    def get_optimization_report(self, sql, explain_analysis=None, table_info=None):
        suggestions = self.analyze_query(sql, explain_analysis)
        index_suggestions = self.suggest_indexes(sql, table_info)
        rewrite_result = self.rewrite_query(sql)
        transforms = self.generate_equivalent_transforms(sql)
        cost_estimate = self.estimate_cost(sql, table_info)

        return {
            'suggestions': suggestions,
            'index_suggestions': index_suggestions,
            'rewrite_result': rewrite_result,
            'equivalent_transforms': transforms,
            'cost_estimate': cost_estimate,
            'summary': self._generate_summary(suggestions, index_suggestions, transforms)
        }

    def _generate_summary(self, suggestions, index_suggestions, transforms):
        high_count = sum(1 for s in suggestions if s.get('priority') == 'high')
        medium_count = sum(1 for s in suggestions if s.get('priority') == 'medium')
        low_count = sum(1 for s in suggestions if s.get('priority') == 'low')
        return {
            'total_suggestions': len(suggestions),
            'high_priority': high_count,
            'medium_priority': medium_count,
            'low_priority': low_count,
            'index_suggestions_count': len(index_suggestions),
            'transform_options_count': len(transforms)
        }


def optimize_query(sql, explain_analysis=None, table_info=None):
    optimizer = QueryOptimizer()
    return optimizer.get_optimization_report(sql, explain_analysis, table_info)


def suggest_indexes(sql, table_info=None):
    optimizer = QueryOptimizer()
    return optimizer.suggest_indexes(sql, table_info)


def rewrite_query(sql):
    optimizer = QueryOptimizer()
    return optimizer.rewrite_query(sql)


def generate_equivalent_transforms(sql):
    optimizer = QueryOptimizer()
    return optimizer.generate_equivalent_transforms(sql)


def estimate_cost(sql, table_info=None):
    optimizer = QueryOptimizer()
    return optimizer.estimate_cost(sql, table_info)