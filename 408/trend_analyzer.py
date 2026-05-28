import os
import json
import re
from datetime import datetime, timedelta
from collections import defaultdict
from slow_query_capture import SlowQueryCapture


class TrendAnalyzer:
    GRANULARITY_OPTIONS = {
        'hour': {
            'label': '小时',
            'format': '%Y-%m-%d %H:00',
            'group_key': lambda dt: dt.strftime('%Y-%m-%d %H:00'),
            'sort_key': lambda x: x
        },
        'day': {
            'label': '日',
            'format': '%Y-%m-%d',
            'group_key': lambda dt: dt.strftime('%Y-%m-%d'),
            'sort_key': lambda x: x
        },
        'week': {
            'label': '周',
            'format': '%Y-W%W',
            'group_key': lambda dt: f"{dt.isocalendar()[0]}-W{dt.isocalendar()[1]:02d}",
            'sort_key': lambda x: x
        }
    }

    def __init__(self):
        self.slow_query_capture = SlowQueryCapture()
        self._data_dir = os.path.join(os.path.dirname(__file__), 'data')
        self._trend_file = os.path.join(self._data_dir, 'trend_data.json')
        self._ensure_data_dir()

    def _ensure_data_dir(self):
        os.makedirs(self._data_dir, exist_ok=True)

    def analyze_trends(self, days=7, granularity='day'):
        history = self.slow_query_capture.get_history()
        if not history:
            return {
                'success': False,
                'error': '无历史数据，请先捕获慢查询'
            }

        if granularity not in self.GRANULARITY_OPTIONS:
            granularity = 'day'

        time_stats = self._calculate_time_stats(history, days, granularity)
        table_trends = self._calculate_table_trends(history, days)
        query_type_trends = self._calculate_query_type_trends(history, days)
        performance_summary = self._calculate_performance_summary(history, days)

        return {
            'success': True,
            'granularity': granularity,
            'granularity_label': self.GRANULARITY_OPTIONS[granularity]['label'],
            'time_stats': time_stats,
            'table_trends': table_trends,
            'query_type_trends': query_type_trends,
            'performance_summary': performance_summary,
            'anomalies': self._detect_anomalies(time_stats, granularity)
        }

    def _calculate_time_stats(self, history, days, granularity='day'):
        config = self.GRANULARITY_OPTIONS[granularity]
        stats = defaultdict(lambda: {
            'count': 0,
            'total_time': 0,
            'max_time': 0,
            'avg_time': 0,
            'tables': set()
        })

        cutoff_date = datetime.now() - timedelta(days=days)

        for entry in history:
            ts = entry.get('timestamp', '')
            if not ts:
                continue
            try:
                dt = datetime.fromisoformat(ts)
                if dt < cutoff_date:
                    continue

                key = config['group_key'](dt)
                qt = self._parse_query_time(entry.get('query_time', 0))

                stats[key]['count'] += 1
                stats[key]['total_time'] += qt
                stats[key]['max_time'] = max(stats[key]['max_time'], qt)

                query = entry.get('query', '')
                tables = re.findall(r'FROM\s+(\w+)', query, re.IGNORECASE)
                stats[key]['tables'].update(tables)
            except Exception:
                continue

        result = []
        for key in sorted(stats.keys(), key=config['sort_key']):
            s = stats[key]
            s['avg_time'] = s['total_time'] / s['count'] if s['count'] > 0 else 0
            s['tables'] = list(s['tables'])
            s['period'] = key
            result.append(s)
        return result

    def _parse_query_time(self, qt):
        if isinstance(qt, str):
            parts = qt.split(':')
            if len(parts) == 3:
                return int(parts[0]) * 3600 + int(parts[1]) * 60 + float(parts[2])
        elif isinstance(qt, timedelta):
            return qt.total_seconds()
        return float(qt) if qt else 0

    def _calculate_table_trends(self, history, days):
        table_stats = defaultdict(lambda: {
            'count': 0,
            'total_time': 0,
            'max_time': 0,
            'avg_time': 0
        })

        cutoff_date = datetime.now() - timedelta(days=days)

        for entry in history:
            ts = entry.get('timestamp', '')
            if ts:
                try:
                    dt = datetime.fromisoformat(ts)
                    if dt < cutoff_date:
                        continue
                except Exception:
                    continue

            query = entry.get('query', '')
            tables = re.findall(r'FROM\s+(\w+)', query, re.IGNORECASE)
            qt = self._parse_query_time(entry.get('query_time', 0))

            for table in tables:
                table_stats[table]['count'] += 1
                table_stats[table]['total_time'] += qt
                table_stats[table]['max_time'] = max(table_stats[table]['max_time'], qt)

        result = []
        for table, s in sorted(table_stats.items(), key=lambda x: x[1]['total_time'], reverse=True):
            s['table'] = table
            s['avg_time'] = s['total_time'] / s['count'] if s['count'] > 0 else 0
            result.append(s)
        return result

    def _calculate_query_type_trends(self, history, days):
        type_stats = defaultdict(lambda: {
            'count': 0,
            'total_time': 0,
            'avg_time': 0
        })

        cutoff_date = datetime.now() - timedelta(days=days)

        for entry in history:
            ts = entry.get('timestamp', '')
            if ts:
                try:
                    dt = datetime.fromisoformat(ts)
                    if dt < cutoff_date:
                        continue
                except Exception:
                    continue

            query = entry.get('query', '')
            query_upper = query.upper().strip()
            qt = self._parse_query_time(entry.get('query_time', 0))

            if query_upper.startswith('SELECT'):
                qtype = 'SELECT'
            elif query_upper.startswith('INSERT'):
                qtype = 'INSERT'
            elif query_upper.startswith('UPDATE'):
                qtype = 'UPDATE'
            elif query_upper.startswith('DELETE'):
                qtype = 'DELETE'
            else:
                qtype = 'OTHER'
            type_stats[qtype]['count'] += 1
            type_stats[qtype]['total_time'] += qt

        result = []
        for qtype, s in type_stats.items():
            s['type'] = qtype
            s['avg_time'] = s['total_time'] / s['count'] if s['count'] > 0 else 0
            result.append(s)
        return result

    def _calculate_performance_summary(self, history, days):
        cutoff_date = datetime.now() - timedelta(days=days)
        filtered = []

        for entry in history:
            ts = entry.get('timestamp', '')
            if ts:
                try:
                    dt = datetime.fromisoformat(ts)
                    if dt < cutoff_date:
                        continue
                except Exception:
                    continue
            filtered.append(entry)

        total_count = len(filtered)
        total_time = 0
        max_time = 0
        min_time = float('inf')
        time_values = []

        for entry in filtered:
            qt = self._parse_query_time(entry.get('query_time', 0))
            total_time += qt
            max_time = max(max_time, qt)
            min_time = min(min_time, qt)
            time_values.append(qt)

        time_values.sort()
        p95 = time_values[int(len(time_values) * 0.95)] if time_values else 0
        p99 = time_values[int(len(time_values) * 0.99)] if time_values else 0
        median = time_values[len(time_values) // 2] if time_values else 0

        return {
            'total_count': total_count,
            'total_time': round(total_time, 4),
            'avg_time': round(total_time / total_count, 4) if total_count > 0 else 0,
            'max_time': round(max_time, 4),
            'min_time': round(min_time if min_time != float('inf') else 0, 4),
            'median_time': round(median, 4),
            'p95_time': round(p95, 4),
            'p99_time': round(p99, 4)
        }

    def _detect_anomalies(self, time_stats, granularity='day'):
        if len(time_stats) < 3:
            return []

        anomalies = []
        avg_count = sum(s['count'] for s in time_stats) / len(time_stats)
        avg_time = sum(s['avg_time'] for s in time_stats) / len(time_stats)

        for s in time_stats:
            if s['count'] > avg_count * 2:
                anomalies.append({
                    'period': s['period'],
                    'type': 'count_spike',
                    'message': f"查询数量异常: {s['count']}次，均值: {avg_count:.0f}次",
                    'severity': 'high'
                })
            if s['avg_time'] > avg_time * 2:
                anomalies.append({
                    'period': s['period'],
                    'type': 'time_spike',
                    'message': f"平均耗时异常: {s['avg_time']:.4f}秒，均值: {avg_time:.4f}秒",
                    'severity': 'high'
                })

        return anomalies

    def get_trend_chart_data(self, days=7, granularity='day'):
        trends = self.analyze_trends(days, granularity)
        if not trends.get('success'):
            return trends

        time_stats = trends.get('time_stats', [])
        periods = [s['period'] for s in time_stats]
        counts = [s['count'] for s in time_stats]
        avg_times = [round(s['avg_time'], 4) for s in time_stats]
        max_times = [round(s['max_time'], 4) for s in time_stats]

        table_trends = trends.get('table_trends', [])
        table_names = [s['table'] for s in table_trends]
        table_counts = [s['count'] for s in table_trends]
        table_times = [round(s['avg_time'], 4) for s in table_trends]

        query_types = trends.get('query_type_trends', [])
        type_names = [s['type'] for s in query_types]
        type_counts = [s['count'] for s in query_types]

        return {
            'success': True,
            'granularity': granularity,
            'granularity_label': trends.get('granularity_label', '日'),
            'time_trend': {
                'periods': periods,
                'counts': counts,
                'avg_times': avg_times,
                'max_times': max_times
            },
            'table_stats': {
                'tables': table_names,
                'counts': table_counts,
                'avg_times': table_times
            },
            'query_type_stats': {
                'types': type_names,
                'counts': type_counts
            },
            'performance_summary': trends.get('performance_summary', {}),
            'anomalies': trends.get('anomalies', [])
        }

    def get_multi_granularity_data(self, days=7):
        result = {}
        for granularity in ['hour', 'day', 'week']:
            result[granularity] = self.get_trend_chart_data(days, granularity)
        return result

    def export_trend_report(self, days=7, granularity='day'):
        chart_data = self.get_trend_chart_data(days, granularity)
        if not chart_data.get('success'):
            return chart_data
        return {
            'success': True,
            'report': {
                'generated_at': datetime.now().isoformat(),
                'period_days': days,
                'granularity': granularity,
                'granularity_label': chart_data.get('granularity_label', ''),
                'performance': chart_data.get('performance_summary', {}),
                'time_trend': chart_data.get('time_trend', {}),
                'anomalies': chart_data.get('anomalies', [])
            }
        }


def analyze_trends(days=7, granularity='day'):
    analyzer = TrendAnalyzer()
    return analyzer.analyze_trends(days, granularity)


def get_trend_chart_data(days=7, granularity='day'):
    analyzer = TrendAnalyzer()
    return analyzer.get_trend_chart_data(days, granularity)


def get_multi_granularity_data(days=7):
    analyzer = TrendAnalyzer()
    return analyzer.get_multi_granularity_data(days)