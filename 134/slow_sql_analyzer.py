import re
import json
import pymysql
from datetime import datetime
from collections import defaultdict, Counter
from config import Config
from sql_fingerprint import SQLFingerprint

class SlowSQLAnalyzer:
    def __init__(self):
        self.fingerprint = SQLFingerprint()
        self.slow_queries = []
    
    def parse_slow_log_from_file(self, file_path):
        if not file_path:
            print("未指定慢查询日志文件路径")
            return []
        
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
        except Exception as e:
            print(f"读取慢查询日志文件失败: {e}")
            return []
        
        return self._parse_slow_log_content(content)
    
    def _parse_slow_log_content(self, content):
        queries = []
        current_query = {
            'time': None,
            'user': None,
            'host': None,
            'query_time': None,
            'lock_time': None,
            'rows_sent': None,
            'rows_examined': None,
            'sql': ''
        }
        
        lines = content.split('\n')
        i = 0
        while i < len(lines):
            line = lines[i]
            
            time_match = re.match(r'# Time:\s+(.+)', line)
            if time_match:
                if current_query['sql']:
                    queries.append(current_query.copy())
                    current_query['sql'] = ''
                
                time_str = time_match.group(1).strip()
                try:
                    current_query['time'] = datetime.strptime(time_str, '%y%m%d %H:%M:%S').isoformat()
                except:
                    current_query['time'] = time_str
            
            user_match = re.match(r'# User@Host:\s+(\w+)\[@]\s+host:\s+([\w\-.]+', line)
            if user_match:
                current_query['user'] = user_match.group(1)
                current_query['host'] = user_match.group(2)
            
            query_time_match = re.match(r'# Query_time:\s+([\d.]+)\s+Lock_time:\s+([\d.]+)\s+Rows_sent:\s+(\d+)\s+Rows_examined:\s+(\d+)', line)
            if query_time_match:
                current_query['query_time'] = float(query_time_match.group(1))
                current_query['lock_time'] = float(query_time_match.group(2))
                current_query['rows_sent'] = int(query_time_match.group(3))
                current_query['rows_examined'] = int(query_time_match.group(4))
            
            if line and not line.startswith('#') and not line.startswith('SET timestamp='):
                current_query['sql'] += line + ' '
            
            i += 1
        
        if current_query['sql']:
            queries.append(current_query)
        
        self.slow_queries = queries
        return queries
    
    def get_slow_queries_from_db(self):
        conn = None
        try:
            conn_params = Config.get_db_params_without_db()
            conn = pymysql.connect(**conn_params)
            
            with conn.cursor(pymysql.cursors.DictCursor) as cursor:
                cursor.execute("SHOW VARIABLES LIKE 'slow_query_log'")
                log_status = cursor.fetchone()
                
                cursor.execute("SHOW VARIABLES LIKE 'long_query_time'")
                long_query_time = cursor.fetchone()
                
                cursor.execute("""
                    SELECT 
                        start_time,
                        user_host,
                        query_time,
                        lock_time,
                        rows_sent,
                        rows_examined,
                        db,
                        sql_text
                    FROM mysql.slow_log
                    WHERE sql_text NOT LIKE '%slow_log%'
                    ORDER BY start_time DESC
                    LIMIT 1000
                """)
                raw_queries = cursor.fetchall()
                
                queries = []
                for q in raw_queries:
                    sql_text = q['sql_text']
                    if isinstance(sql_text, bytes):
                        sql_text = sql_text.decode('utf-8', errors='ignore')
                    
                    queries.append({
                        'time': q['start_time'].isoformat() if q['start_time'] else None,
                        'user': q['user_host'],
                        'query_time': float(q['query_time'].total_seconds() if hasattr(q['query_time'], 'total_seconds') else q['query_time']),
                        'lock_time': float(q['lock_time'].total_seconds() if hasattr(q['lock_time'], 'total_seconds') else q['lock_time']),
                        'rows_sent': q['rows_sent'],
                        'rows_examined': q['rows_examined'],
                        'db': q['db'],
                        'sql': sql_text
                    })
                
                self.slow_queries = queries
                return queries
                
        except Exception as e:
            print(f"从数据库获取慢查询日志失败: {e}")
            return []
        finally:
            if conn:
                conn.close()
    
    def analyze_slow_queries(self, slow_queries=None):
        if slow_queries is None:
            slow_queries = self.slow_queries
        
        if not slow_queries:
            return {
                'total': 0,
                'avg_query_time': 0,
                'fingerprint_stats': [],
                'table_analysis': {},
                'top_slow_queries': []
            }
        
        fingerprint_counts = defaultdict(list)
        table_counts = Counter()
        type_counts = Counter()
        
        for query in slow_queries:
            sql = query.get('sql', '')
            fp = self.fingerprint.generate_fingerprint(sql)
            tables = self.fingerprint.extract_tables(sql)
            query_type = self.fingerprint.classify_query_type(sql)
            
            if fp:
                fingerprint_counts[fp].append(query)
            
            for table in tables:
                table_counts[table] += 1
            
            type_counts[query_type] += 1
        
        fingerprint_stats = []
        for fp, queries_list in fingerprint_counts.items():
            avg_query_times = [q.get('query_time', 0) for q in queries_list]
            lock_times = [q.get('lock_time', 0) for q in queries_list]
            
            fingerprint_stats.append({
                'fingerprint': fp,
                'count': len(queries_list),
                'avg_query_time': sum(avg_query_times) / len(avg_query_times) if avg_query_times else 0,
                'max_query_time': max(avg_query_times) if avg_query_times else 0,
                'avg_lock_time': sum(lock_times) / len(lock_times) if lock_times else 0
            })
        
        fingerprint_stats.sort(key=lambda x: x['count'], reverse=True)
        
        sorted_slow = sorted(slow_queries, key=lambda x: x.get('query_time', 0), reverse=True)[:20]
        
        return {
            'total': len(slow_queries),
            'avg_query_time': sum(q.get('query_time', 0) for q in slow_queries) / len(slow_queries) if slow_queries else 0,
            'fingerprint_stats': fingerprint_stats,
            'table_analysis': dict(table_counts),
            'type_analysis': dict(type_counts),
            'top_slow_queries': sorted_slow
        }
    
    def correlate_with_deadlocks(self, deadlocks):
        slow_queries = self.slow_queries
        
        correlations = []
        
        for deadlock in deadlocks:
            deadlock_time = deadlock.get('timestamp')
            if not deadlock_time:
                continue
            
            try:
                dt_deadlock = datetime.fromisoformat(deadlock_time)
            except:
                continue
            
            deadlock_tables = set()
            deadlock_queries = []
            
            for txn in deadlock.get('transactions', []):
                for sql in txn.get('queries', []):
                    deadlock_queries.append(sql)
                
                for hold in txn.get('holds', []):
                    table = hold.get('table')
                    if table and table != 'UNKNOWN':
                        deadlock_tables.add(table)
                
                waiting = txn.get('waiting_for')
                if waiting:
                    table = waiting.get('table')
                    if table and table != 'UNKNOWN':
                        deadlock_tables.add(table)
            
            related_slow_queries = []
            
            for slow_query in slow_queries:
                slow_time = slow_query.get('time')
                if not slow_time:
                    continue
                
                try:
                    dt_slow = datetime.fromisoformat(slow_time)
                except:
                    continue
                
                time_diff = abs((dt_deadlock - dt_slow).total_seconds())
                
                if time_diff < 300:
                    slow_tables = self.fingerprint.extract_tables(slow_query.get('sql', ''))
                    
                    table_overlap = deadlock_tables.intersection(set(slow_tables))
                    table_overlap_score = len(table_overlap) > 0 or time_diff < 60
                    
                    if table_overlap_score:
                        related_slow_queries.append({
                            'slow_query': slow_query,
                            'time_diff_seconds': time_diff,
                            'table_overlap': list(table_overlap)
                        })
            
            if related_slow_queries:
                correlations.append({
                    'deadlock_time': deadlock_time,
                    'deadlock_tables': list(deadlock_tables),
                    'related_slow_queries': related_slow_queries,
                    'root_cause_score': min(related_slow_queries, key=lambda x: x['time_diff_seconds'])
                })
        
        return correlations
    
    def generate_optimization_suggestions(self, analysis_result):
        suggestions = []
        
        for fp_stat in analysis_result.get('fingerprint_stats', [])[:10]:
            fp = fp_stat['fingerprint']
            avg_time = fp_stat['avg_query_time']
            
            suggestion = {
                'fingerprint': fp,
                'severity': 'high' if avg_time > 5 else 'medium' if avg_time > 1 else 'low',
                'avg_query_time': avg_time,
                'suggestions': []
            }
            
            if 'SELECT' in fp.upper():
                suggestion['suggestions'].append('检查是否缺少索引，考虑在WHERE条件字段添加索引')
                suggestion['suggestions'].append('考虑优化JOIN条件，避免全表扫描')
            
            if 'UPDATE' in fp.upper() or 'DELETE' in fp.upper():
                suggestion['suggestions'].append('更新/删除操作可能持有锁竞争，考虑批量操作')
            
            if '?' in fp:
                suggestion['suggestions'].append('使用批量操作考虑使用Prepared Statements提高执行')
            
            suggestions.append(suggestion)
        
        table_suggestions = {}
        for table, count in analysis_result.get('table_analysis', {}).items():
            if count > 10:
                table_suggestions[table] = [
                    '该表慢查询较多，考虑分表分库',
                    '检查表结构是否合理',
                    '考虑添加合适的索引策略'
                ]
        
        return {
            'query_suggestions': suggestions,
            'table_suggestions': table_suggestions,
            'general_suggestions': [
                '监控慢查询阈值，根据业务调整',
                '定期分析执行计划',
                '优化配置MySQL配置是否合理',
            ]
        }
    
    def generate_report(self, output_file='slow_sql_report.html'):
        analysis = self.analyze_slow_queries()
        
        html_content = f"""
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>慢SQL分析报告</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); min-height: 100vh; padding: 20px; }}
        .container {{ max-width: 1200px; margin: 0 auto; background: white; border-radius: 15px; box-shadow: 0 20px 60px rgba(0,0,0,0.3); }}
        .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; text-align: center; }}
        .stats-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; padding: 30px; }}
        .stat-card {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 25px; border-radius: 12px; text-align: center; }}
        .stat-value {{ font-size: 36px; font-weight: bold; }}
        .section {{ padding: 30px; border-top: 1px solid #e9ecef; }}
        h2 {{ color: #2d3748; margin-bottom: 20px; }}
        table {{ width: 100%; border-collapse: collapse; }}
        th, td {{ padding: 12px; text-align: left; border-bottom: 1px solid #e9ecef; }}
        th {{ background: #f8f9fa; }}
        tr:hover {{ background: #f8f9fa; }}
        .sql-code {{ background: #2d3748; color: #f8f9fa; padding: 15px; border-radius: 8px; font-family: monospace; font-size: 12px; overflow-x: auto; }}
        .badge-high {{ background: #f56565; color: white; padding: 3px 8px; border-radius: 12px; font-size: 12px; }}
        .badge-medium {{ background: #ed8936; color: white; padding: 3px 8px; border-radius: 12px; font-size: 12px; }}
        .badge-low {{ background: #48bb78; color: white; padding: 3px 8px; border-radius: 12px; font-size: 12px; }}
        .suggestion-item {{ background: #f7fafc; border-left: 4px solid #4299e1; padding: 15px; margin: 10px 0; border-radius: 0 8px 8px 0; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🐢 慢SQL分析报告</h1>
            <p>生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        </div>
        
        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-value">{analysis['total']}</div>
                <div>慢查询总数</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{analysis['avg_query_time']:.2f}s</div>
                <div>平均查询时间</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{len(analysis.get('table_analysis', {}))}</div>
                <div>涉及表数</div>
            </div>
        </div>
        
        <div class="section">
            <h2>📊 SQL指纹统计</h2>
            <table>
                <tr><th>SQL指纹</th><th>出现次数</th><th>平均查询时间</th><th>最大查询时间</th><th>严重程度</th></tr>
                {"".join(f"<tr><td><code style='word-break: break-all;'>{fp['fingerprint']}</code></td><td>{fp['count']}</td><td>{fp['avg_query_time']:.2f}s</td><td>{fp['max_query_time']:.2f}s</td><td><span class='badge-{fp['severity']}'>{fp['severity']}</span></td></tr>" for fp in analysis['fingerprint_stats'][:10])}
            </table>
        </div>
        
        <div class="section">
            <h2>📋 表级分析</h2>
            <table>
                <tr><th>表名</th><th>出现次数</th></tr>
                {"".join(f"<tr><td>{table}</td><td>{count}</td></tr>" for table, count in sorted(analysis.get('table_analysis', {}).items(), key=lambda x: x[1], reverse=True))}
            </table>
        </div>
        
        <div class="section">
            <h2>💡 优化建议</h2>
            {"".join(f"<div class='suggestion-item'><h4>{s['fingerprint'][:100]}...</h4><ul>{"".join(f"<li>{sug}</li>" for sug in s['suggestions'])}</ul></div>" for s in self.generate_optimization_suggestions(analysis).get('query_suggestions', []))}
        </div>
        
        <div class="section">
            <h2>🔝 TOP 20 最慢查询</h2>
            {"".join(f"<div class='sql-code'>{q['sql'][:500]}...</div><p>查询时间: {q['query_time']:.2f}s | 锁等待: {q['lock_time']:.2f}s | 扫描行数: {q['rows_examined']}</p><hr>" for q in analysis['top_slow_queries'])}
        </div>
    </div>
</body>
</html>
        """
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        return output_file
