import os
import json
import time
import re
from datetime import datetime, timedelta
from collections import defaultdict
from db_connector import DBConnector


class SlowQueryCapture:
    def __init__(self):
        self.db = DBConnector()
        self._data_dir = os.path.join(os.path.dirname(__file__), 'data')
        self._history_file = os.path.join(self._data_dir, 'slow_query_history.json')
        self._ensure_data_dir()

    def _ensure_data_dir(self):
        os.makedirs(self._data_dir, exist_ok=True)

    def capture_slow_queries(self, start_time=None, end_time=None, min_query_time=1.0, limit=100):
        if start_time is None:
            start_time = (datetime.now() - timedelta(hours=24)).strftime('%Y-%m-%d %H:%M:%S')
        if end_time is None:
            end_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        result = self.db.get_slow_queries(start_time, end_time, min_query_time, limit)
        if result['success']:
            queries = result['data']
            self._save_to_history(queries)
            return {'success': True, 'queries': queries, 'count': len(queries)}
        return result

    def capture_from_general_log(self, start_time=None, end_time=None, limit=100):
        sql = """
            SELECT 
                event_time,
                user_host,
                argument AS sql_text
            FROM mysql.general_log
            WHERE command_type = 'Query'
        """
        params = []
        if start_time:
            sql += " AND event_time >= %s"
            params.append(start_time)
        if end_time:
            sql += " AND event_time <= %s"
            params.append(end_time)
        sql += " ORDER BY event_time DESC LIMIT %s"
        params.append(limit)
        return self.db.execute_query(sql, params)

    def analyze_slow_query(self, query_text):
        from sql_parser import parse_sql
        analysis = parse_sql(query_text)
        return analysis

    def get_slow_query_summary(self, queries):
        summary = {
            'total_count': len(queries),
            'total_time': 0,
            'avg_time': 0,
            'max_time': 0,
            'min_time': float('inf'),
            'by_table': defaultdict(int),
            'by_type': defaultdict(int),
            'query_types': defaultdict(int),
            'has_full_table_scan': 0,
            'has_filesort': 0,
            'has_temporary': 0
        }
        for q in queries:
            query_time = q.get('query_time', 0)
            if isinstance(query_time, timedelta):
                query_time = query_time.total_seconds()
            summary['total_time'] += query_time
            summary['max_time'] = max(summary['max_time'], query_time)
            summary['min_time'] = min(summary['min_time'], query_time)
            sql_text = q.get('sql_text', '') or q.get('argument', '')
            if sql_text:
                if 'SELECT' in sql_text.upper():
                    summary['query_types']['SELECT'] += 1
                elif 'INSERT' in sql_text.upper():
                    summary['query_types']['INSERT'] += 1
                elif 'UPDATE' in sql_text.upper():
                    summary['query_types']['UPDATE'] += 1
                elif 'DELETE' in sql_text.upper():
                    summary['query_types']['DELETE'] += 1
                tables = re.findall(r'FROM\s+(\w+)', sql_text, re.IGNORECASE)
                for t in tables:
                    summary['by_table'][t] += 1
        if summary['total_count'] > 0:
            summary['avg_time'] = summary['total_time'] / summary['total_count']
        summary['by_table'] = dict(summary['by_table'])
        summary['by_type'] = dict(summary['by_type'])
        return summary

    def _save_to_history(self, queries):
        history = self._load_history()
        timestamp = datetime.now().isoformat()
        for q in queries:
            entry = {
                'timestamp': timestamp,
                'query': q.get('sql_text', '') or q.get('argument', ''),
                'query_time': q.get('query_time', 0),
                'rows_examined': q.get('rows_examined', 0),
                'rows_sent': q.get('rows_sent', 0)
            }
            history.append(entry)
        if len(history) > 10000:
            history = history[-10000:]
        with open(self._history_file, 'w', encoding='utf-8') as f:
            json.dump(history, f, ensure_ascii=False, indent=2, default=str)

    def _load_history(self):
        if os.path.exists(self._history_file):
            try:
                with open(self._history_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                return []
        return []

    def get_history(self):
        return self._load_history()

    def get_history_stats(self):
        history = self._load_history()
        stats = {
            'total_captured': len(history),
            'unique_tables': set(),
            'by_date': defaultdict(int),
            'avg_query_time': 0,
            'total_query_time': 0
        }
        for entry in history:
            if entry.get('query_time'):
                qt = entry['query_time']
                if isinstance(qt, timedelta):
                    qt = qt.total_seconds()
                elif isinstance(qt, str):
                    parts = qt.split(':')
                    if len(parts) == 3:
                        qt = int(parts[0]) * 3600 + int(parts[1]) * 60 + float(parts[2])
                stats['total_query_time'] += qt
            query = entry.get('query', '')
            tables = re.findall(r'FROM\s+(\w+)', query, re.IGNORECASE)
            for t in tables:
                stats['unique_tables'].add(t)
            ts = entry.get('timestamp', '')
            if ts:
                date_str = ts[:10]
                stats['by_date'][date_str] += 1
        if len(history) > 0:
            stats['avg_query_time'] = stats['total_query_time'] / len(history)
        stats['unique_tables'] = list(stats['unique_tables'])
        stats['by_date'] = dict(stats['by_date'])
        return stats

    def get_query_fingerprint(self, query):
        fp = query.lower()
        fp = re.sub(r'\b\d+\b', '?', fp)
        fp = re.sub(r"'[^']*'", "?", fp)
        fp = re.sub(r'"[^"]*"', "?", fp)
        fp = re.sub(r'\s+', ' ', fp).strip()
        return fp

    def group_similar_queries(self, queries):
        groups = defaultdict(list)
        for q in queries:
            sql_text = q.get('sql_text', '') or q.get('argument', '')
            if sql_text:
                fp = self.get_query_fingerprint(sql_text)
                groups[fp].append(q)
        result = []
        for fp, group in groups.items():
            avg_time = 0
            total_time = 0
            for q in group:
                qt = q.get('query_time', 0)
                if isinstance(qt, timedelta):
                    qt = qt.total_seconds()
                elif isinstance(qt, str):
                    parts = qt.split(':')
                    if len(parts) == 3:
                        qt = int(parts[0]) * 3600 + int(parts[1]) * 60 + float(parts[2])
                total_time += qt
            if len(group) > 0:
                avg_time = total_time / len(group)
            result.append({
                'fingerprint': fp,
                'count': len(group),
                'avg_time': avg_time,
                'total_time': total_time,
                'sample_query': group[0].get('sql_text', '') or group[0].get('argument', '')
            })
        result.sort(key=lambda x: x['total_time'], reverse=True)
        return result

    def get_top_slow_queries(self, limit=20):
        history = self._load_history()
        grouped = self.group_similar_queries(history)
        return grouped[:limit]