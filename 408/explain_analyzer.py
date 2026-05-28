import json
import re
from collections import defaultdict


class ExplainAnalyzer:
    ACCESS_TYPE_SCORES = {
        'system': 100,
        'const': 95,
        'eq_ref': 90,
        'ref': 80,
        'fulltext': 70,
        'ref_or_null': 65,
        'index_merge': 60,
        'unique_subquery': 55,
        'index_subquery': 50,
        'range': 40,
        'index': 30,
        'ALL': 10
    }

    ACCESS_TYPE_LABELS = {
        'system': '系统表',
        'const': '常量',
        'eq_ref': '等值引用',
        'ref': '索引引用',
        'fulltext': '全文索引',
        'ref_or_null': '索引引用+NULL',
        'index_merge': '索引合并',
        'unique_subquery': '唯一子查询',
        'index_subquery': '索引子查询',
        'range': '范围扫描',
        'index': '索引树扫描',
        'ALL': '全表扫描'
    }

    def __init__(self):
        self.plan_rows = []
        self.analysis = {}

    def analyze(self, explain_result, sql=None):
        self.plan_rows = explain_result if isinstance(explain_result, list) else []
        if not self.plan_rows:
            return {'success': False, 'error': '无执行计划数据'}

        self.analysis = {
            'success': True,
            'has_full_table_scan': self._detect_full_table_scan(),
            'has_temporary': self._detect_temporary(),
            'has_filesort': self._detect_filesort(),
            'has_index_merge': self._detect_index_merge(),
            'total_rows_examined': self._calculate_total_rows(),
            'worst_access_type': self._get_worst_access_type(),
            'table_scans': self._get_table_scans(),
            'possible_indexes': self._get_possible_indexes(),
            'used_indexes': self._get_used_indexes(),
            'extra_info': self._get_extra_info(),
            'warnings': self._generate_warnings(),
            'cost_estimate': self._estimate_cost(),
            'tree_data': self._build_collapsible_tree_data(sql),
            'grouped_tree_data': self._build_grouped_tree_data(),
            'table_details': self._get_table_details()
        }
        return self.analysis

    def _detect_full_table_scan(self):
        for row in self.plan_rows:
            if row.get('type', '').upper() == 'ALL':
                return True
        return False

    def _detect_temporary(self):
        for row in self.plan_rows:
            extra = row.get('Extra', '') or ''
            if 'Using temporary' in extra:
                return True
        return False

    def _detect_filesort(self):
        for row in self.plan_rows:
            extra = row.get('Extra', '') or ''
            if 'Using filesort' in extra:
                return True
        return False

    def _detect_index_merge(self):
        for row in self.plan_rows:
            if row.get('type', '').upper() == 'INDEX_MERGE':
                return True
        return False

    def _calculate_total_rows(self):
        total = 0
        for row in self.plan_rows:
            rows = row.get('rows', 0)
            if rows:
                try:
                    total += int(rows)
                except (ValueError, TypeError):
                    pass
        return total

    def _get_worst_access_type(self):
        worst = 'system'
        worst_score = 100
        for row in self.plan_rows:
            access_type = row.get('type', '') or ''
            score = self.ACCESS_TYPE_SCORES.get(access_type, 0)
            if score < worst_score:
                worst_score = score
                worst = access_type
        return worst

    def _get_table_scans(self):
        scans = []
        for row in self.plan_rows:
            access_type = row.get('type', '') or ''
            if access_type.upper() == 'ALL':
                scans.append({
                    'table': row.get('table', ''),
                    'rows': row.get('rows', 0),
                    'filtered': row.get('filtered', 100),
                    'extra': row.get('Extra', '')
                })
        return scans

    def _get_possible_indexes(self):
        indexes = {}
        for row in self.plan_rows:
            table = row.get('table', '')
            possible = row.get('possible_keys', '')
            if table and possible:
                if table not in indexes:
                    indexes[table] = []
                idx_list = [idx.strip() for idx in possible.split(',') if idx.strip()]
                indexes[table].extend(idx_list)
        return indexes

    def _get_used_indexes(self):
        indexes = {}
        for row in self.plan_rows:
            table = row.get('table', '')
            used = row.get('key', '')
            if table and used and used != '(NULL)':
                indexes[table] = used
        return indexes

    def _get_extra_info(self):
        extras = []
        for row in self.plan_rows:
            extra = row.get('Extra', '') or ''
            if extra:
                extras.append({
                    'table': row.get('table', ''),
                    'extra': extra
                })
        return extras

    def _generate_warnings(self):
        warnings = []
        if self._detect_full_table_scan():
            tables = [s['table'] for s in self._get_table_scans()]
            warnings.append({
                'level': 'high',
                'type': 'full_table_scan',
                'message': f"存在全表扫描，涉及表: {', '.join(tables)}",
                'suggestion': '建议添加合适的索引以避免全表扫描'
            })

        if self._detect_temporary():
            warnings.append({
                'level': 'medium',
                'type': 'temporary_table',
                'message': '使用了临时表（Using temporary）',
                'suggestion': '检查GROUP BY和ORDER BY字段，考虑添加索引或优化查询'
            })

        if self._detect_filesort():
            warnings.append({
                'level': 'medium',
                'type': 'filesort',
                'message': '使用了文件排序（Using filesort）',
                'suggestion': '为ORDER BY字段添加索引以避免文件排序'
            })

        for row in self.plan_rows:
            possible = row.get('possible_keys', '')
            used = row.get('key', '')
            if possible and (not used or used == '(NULL)'):
                warnings.append({
                    'level': 'medium',
                    'type': 'unused_index',
                    'message': f"表 {row.get('table', '')} 有可用索引但未使用: {possible}",
                    'suggestion': '检查查询条件是否能利用索引，可能需要调整查询写法'
                })

        total_rows = self._calculate_total_rows()
        if total_rows > 100000:
            warnings.append({
                'level': 'high',
                'type': 'large_rows_examined',
                'message': f"预计扫描行数过多: {total_rows} 行",
                'suggestion': '建议优化查询条件，减少扫描行数'
            })

        for row in self.plan_rows:
            filtered = row.get('filtered', 100)
            if filtered and float(filtered) < 30:
                warnings.append({
                    'level': 'low',
                    'type': 'low_filtered',
                    'message': f"表 {row.get('table', '')} 过滤率低: {filtered}%",
                    'suggestion': '考虑优化索引或查询条件'
                })

        return warnings

    def _estimate_cost(self):
        cost = 0
        details = []
        for row in self.plan_rows:
            row_cost = 0
            access_type = row.get('type', '') or ''
            type_score = self.ACCESS_TYPE_SCORES.get(access_type, 0)
            row_cost += (100 - type_score) * 10
            rows = int(row.get('rows', 0) or 0)
            row_cost += min(rows / 100, 100) * 10
            extra = row.get('Extra', '') or ''
            if 'Using temporary' in extra:
                row_cost += 50
            if 'Using filesort' in extra:
                row_cost += 30
            if 'Using where' in extra:
                row_cost += 5
            details.append({
                'table': row.get('table', ''),
                'cost': row_cost,
                'reason': f"访问类型: {access_type}, 行数: {rows}, Extra: {extra}"
            })
            cost += row_cost
        return {
            'total_cost': cost,
            'details': details,
            'rating': self._get_rating(cost)
        }

    def _get_rating(self, cost):
        if cost < 50:
            return {'grade': 'A', 'label': '优秀', 'color': '#52c41a'}
        elif cost < 150:
            return {'grade': 'B', 'label': '良好', 'color': '#1890ff'}
        elif cost < 300:
            return {'grade': 'C', 'label': '一般', 'color': '#faad14'}
        elif cost < 500:
            return {'grade': 'D', 'label': '较差', 'color': '#fa8c16'}
        else:
            return {'grade': 'E', 'label': '很差', 'color': '#f5222d'}

    def _build_collapsible_tree_data(self, sql=None):
        if not self.plan_rows:
            return {'nodes': [], 'links': [], 'groups': []}

        nodes = []
        links = []
        groups = self._group_nodes_by_type()

        for i, row in enumerate(self.plan_rows):
            table = row.get('table', '') or f'subquery_{i}'
            access_type = row.get('type', '') or 'unknown'
            rows = int(row.get('rows', 0) or 0)
            key = row.get('key', '') or '无'
            extra = row.get('Extra', '') or ''
            possible_keys = row.get('possible_keys', '') or '无'
            filtered = row.get('filtered', 100)

            node_id = f"node_{i}"
            group_id = self._get_group_id(access_type, extra)

            color = self._get_node_color(access_type, extra)
            risk_level = self._get_risk_level(access_type, extra, rows)

            nodes.append({
                'id': node_id,
                'name': table,
                'group': group_id,
                'access_type': access_type,
                'access_type_label': self.ACCESS_TYPE_LABELS.get(access_type, access_type),
                'rows': rows,
                'key': key,
                'possible_keys': possible_keys,
                'extra': extra,
                'filtered': filtered,
                'risk_level': risk_level,
                'collapsed': False,
                'symbolSize': min(max(rows / 10, 30), 100),
                'itemStyle': {'color': color},
                'label': {
                    'show': True,
                    'formatter': f"{table}\n[{self.ACCESS_TYPE_LABELS.get(access_type, access_type)}]",
                    'fontSize': 11
                },
                'tooltip': {
                    'formatter': (
                        f"<b>{table}</b><br/>"
                        f"访问类型: {self.ACCESS_TYPE_LABELS.get(access_type, access_type)}<br/>"
                        f"扫描行数: {rows:,}<br/>"
                        f"使用索引: {key}<br/>"
                        f"可能索引: {possible_keys}<br/>"
                        f"过滤率: {filtered}%<br/>"
                        f"Extra: {extra}"
                    )
                }
            })

            if i > 0:
                links.append({
                    'source': f"node_{i-1}",
                    'target': node_id,
                    'lineStyle': {
                        'width': 2,
                        'curveness': 0.1,
                        'color': '#999'
                    }
                })

        return {
            'nodes': nodes,
            'links': links,
            'groups': groups
        }

    def _group_nodes_by_type(self):
        groups = defaultdict(list)
        for i, row in enumerate(self.plan_rows):
            access_type = row.get('type', '') or 'unknown'
            extra = row.get('Extra', '') or ''
            group_id = self._get_group_id(access_type, extra)
            groups[group_id].append({
                'index': i,
                'node_id': f"node_{i}",
                'table': row.get('table', '')
            })

        result = []
        for group_id, members in groups.items():
            result.append({
                'id': group_id,
                'name': self._get_group_name(group_id),
                'members': members,
                'collapsed': False
            })
        return result

    def _get_group_id(self, access_type, extra):
        if access_type.upper() == 'ALL':
            return 'full_scan'
        elif 'Using temporary' in extra:
            return 'temporary'
        elif 'Using filesort' in extra:
            return 'filesort'
        elif access_type.upper() in ('INDEX_MERGE',):
            return 'index_merge'
        elif access_type.upper() in ('SYSTEM', 'CONST', 'EQ_REF'):
            return 'optimal'
        elif access_type.upper() in ('REF', 'REF_OR_NULL', 'RANGE'):
            return 'index_usage'
        elif access_type.upper() in ('INDEX',):
            return 'index_scan'
        elif access_type.upper() in ('UNIQUE_SUBQUERY', 'INDEX_SUBQUERY'):
            return 'subquery'
        else:
            return 'other'

    def _get_group_name(self, group_id):
        names = {
            'full_scan': '全表扫描',
            'temporary': '临时表',
            'filesort': '文件排序',
            'index_merge': '索引合并',
            'optimal': '最优访问',
            'index_usage': '索引使用',
            'index_scan': '索引扫描',
            'subquery': '子查询',
            'other': '其他'
        }
        return names.get(group_id, group_id)

    def _get_risk_level(self, access_type, extra, rows):
        score = self.ACCESS_TYPE_SCORES.get(access_type, 0)
        if score <= 20 or 'Using temporary' in extra:
            return 'high'
        elif score <= 50 or 'Using filesort' in extra:
            return 'medium'
        else:
            return 'low'

    def _build_grouped_tree_data(self):
        grouped = defaultdict(list)
        for i, row in enumerate(self.plan_rows):
            access_type = row.get('type', '') or 'unknown'
            extra = row.get('Extra', '') or ''
            group_id = self._get_group_id(access_type, extra)
            grouped[group_id].append({
                'index': i,
                'table': row.get('table', ''),
                'access_type': access_type,
                'rows': row.get('rows', 0)
            })

        result = []
        for group_id, members in grouped.items():
            result.append({
                'id': group_id,
                'name': self._get_group_name(group_id),
                'count': len(members),
                'total_rows': sum(int(m.get('rows', 0) or 0) for m in members),
                'members': members,
                'collapsed': False
            })
        return result

    def _get_node_color(self, access_type, extra):
        type_colors = {
            'system': '#52c41a',
            'const': '#52c41a',
            'eq_ref': '#52c41a',
            'ref': '#1890ff',
            'range': '#1890ff',
            'index': '#faad14',
            'ALL': '#f5222d',
            'index_merge': '#fa8c16',
            'ref_or_null': '#1890ff',
            'unique_subquery': '#faad14',
            'index_subquery': '#faad14'
        }
        base_color = type_colors.get(access_type, '#d9d9d9')
        if 'Using temporary' in extra:
            base_color = '#f5222d'
        elif 'Using filesort' in extra:
            base_color = '#fa8c16'
        return base_color

    def _get_table_details(self):
        details = []
        for row in self.plan_rows:
            details.append({
                'table': row.get('table', ''),
                'type': row.get('type', ''),
                'possible_keys': row.get('possible_keys', ''),
                'key': row.get('key', ''),
                'key_len': row.get('key_len', ''),
                'ref': row.get('ref', ''),
                'rows': row.get('rows', 0),
                'filtered': row.get('filtered', 100),
                'extra': row.get('Extra', '')
            })
        return details


def analyze_explain(explain_result, sql=None):
    analyzer = ExplainAnalyzer()
    return analyzer.analyze(explain_result, sql)


def parse_explain_json(json_result):
    try:
        if isinstance(json_result, list):
            return json_result
        if isinstance(json_result, str):
            return json.loads(json_result)
        if isinstance(json_result, dict):
            return [json_result]
    except Exception:
        return []
    return []


def generate_collapsible_tree_echarts(tree_data):
    nodes = tree_data.get('nodes', [])
    links = tree_data.get('links', [])
    groups = tree_data.get('groups', [])

    graph_nodes = []
    for n in nodes:
        graph_nodes.append({
            'id': n['id'],
            'name': n['name'],
            'value': n['rows'],
            'category': groups.index(next((g for g in groups if g['id'] == n['group']), {'id': 'other'})),
            'symbolSize': n['symbolSize'],
            'itemStyle': n['itemStyle'],
            'label': n.get('label', {}),
            'tooltip': n.get('tooltip', {})
        })

    categories = [{'name': g['name']} for g in groups]
    if not categories:
        categories = [{'name': '默认'}]

    return {
        'tooltip': {
            'trigger': 'item',
            'triggerOn': 'mousemove'
        },
        'legend': {
            'data': [c['name'] for c in categories],
            'top': 10,
            'selectedMode': True
        },
        'series': [{
            'type': 'graph',
            'layout': 'force',
            'data': graph_nodes,
            'links': links,
            'categories': categories,
            'roam': True,
            'draggable': True,
            'force': {
                'repulsion': 400,
                'edgeLength': [100, 200],
                'gravity': 0.1,
                'friction': 0.6
            },
            'label': {
                'show': True,
                'position': 'bottom',
                'fontSize': 11
            },
            'lineStyle': {
                'color': '#999',
                'width': 2,
                'curveness': 0.1
            },
            'emphasis': {
                'focus': 'adjacency',
                'lineStyle': {'width': 4}
            }
        }]
    }


def generate_tree_view_echarts(tree_data):
    nodes = tree_data.get('nodes', [])
    if not nodes:
        return {'series': []}

    tree_root = {
        'name': nodes[0]['name'],
        'value': nodes[0]['rows'],
        'itemStyle': nodes[0]['itemStyle'],
        'collapsed': False,
        'children': []
    }

    current = tree_root
    for i in range(1, len(nodes)):
        n = nodes[i]
        child = {
            'name': n['name'],
            'value': n['rows'],
            'itemStyle': n['itemStyle'],
            'collapsed': False,
            'children': []
        }
        current['children'].append(child)
        current = child

    return {
        'tooltip': {
            'trigger': 'item',
            'formatter': '{b}<br/>扫描行数: {c}'
        },
        'series': [{
            'type': 'tree',
            'data': [tree_root],
            'top': '5%',
            'left': '10%',
            'bottom': '5%',
            'right': '20%',
            'symbolSize': 15,
            'orient': 'LR',
            'label': {
                'position': 'left',
                'verticalAlign': 'middle',
                'align': 'right',
                'fontSize': 11
            },
            'leaves': {
                'label': {
                    'position': 'right',
                    'verticalAlign': 'middle',
                    'align': 'left'
                }
            },
            'expandAndCollapse': True,
            'initialTreeDepth': 3,
            'animationDuration': 550,
            'animationDurationUpdate': 750
        }]
    }


def generate_grouped_view_echarts(tree_data):
    groups = tree_data.get('groups', [])
    if not groups:
        return {'series': []}

    pie_data = []
    for g in groups:
        pie_data.append({
            'name': g['name'],
            'value': g['count'],
            'members': g.get('members', [])
        })

    return {
        'tooltip': {
            'trigger': 'item'
        },
        'series': [{
            'type': 'pie',
            'radius': ['40%', '70%'],
            'data': pie_data,
            'label': {
                'show': True,
                'formatter': '{b}\n{c}个'
            },
            'emphasis': {
                'itemStyle': {
                    'shadowBlur': 10,
                    'shadowOffsetX': 0,
                    'shadowColor': 'rgba(0, 0, 0, 0.5)'
                }
            }
        }]
    }


def _convert_to_echarts_tree(tree_data):
    nodes = tree_data.get('nodes', [])
    if not nodes:
        return {'name': 'root', 'children': []}
    if len(nodes) == 1:
        n = nodes[0]
        return {
            'name': n.get('name', 'unknown'),
            'value': n.get('label', ''),
            'itemStyle': n.get('itemStyle', {}),
            'children': []
        }
    root = {
        'name': nodes[0].get('name', 'root'),
        'value': nodes[0].get('label', ''),
        'itemStyle': nodes[0].get('itemStyle', {}),
        'children': []
    }
    current = root
    for i in range(1, len(nodes)):
        n = nodes[i]
        child = {
            'name': n.get('name', 'unknown'),
            'value': n.get('label', ''),
            'itemStyle': n.get('itemStyle', {}),
            'children': []
        }
        current['children'].append(child)
        current = child
    return root