import json
import os
from datetime import datetime
from config import Config
from sql_fingerprint import SQLFingerprint

class DeadlockReport:
    def __init__(self):
        self.history_file = Config.HISTORY_FILE
        self.history = self._load_history()
        self.sql_fingerprint = SQLFingerprint()
    
    def _load_history(self):
        if os.path.exists(self.history_file):
            try:
                with open(self.history_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                return []
        return []
    
    def _save_history(self):
        with open(self.history_file, 'w', encoding='utf-8') as f:
            json.dump(self.history, f, indent=2, ensure_ascii=False)
    
    def add_deadlock(self, deadlock_data):
        deadlock_data['id'] = len(self.history) + 1
        self.history.append(deadlock_data)
        self._save_history()
    
    def get_history(self):
        return self.history
    
    def get_deadlock_by_id(self, deadlock_id):
        for item in self.history:
            if item.get('id') == deadlock_id:
                return item
        return None
    
    def get_statistics(self):
        total_deadlocks = len(self.history)
        
        table_counts = {}
        query_type_counts = {}
        fingerprint_counts = {}
        
        for deadlock in self.history:
            for txn in deadlock.get('transactions', []):
                for sql in txn.get('queries', []):
                    tables = self.sql_fingerprint.extract_tables(sql)
                    query_type = self.sql_fingerprint.classify_query_type(sql)
                    fingerprint = self.sql_fingerprint.generate_fingerprint(sql)
                    
                    for table in tables:
                        table_counts[table] = table_counts.get(table, 0) + 1
                    
                    query_type_counts[query_type] = query_type_counts.get(query_type, 0) + 1
                    
                    if fingerprint:
                        fingerprint_counts[fingerprint] = fingerprint_counts.get(fingerprint, 0) + 1
        
        return {
            'total_deadlocks': total_deadlocks,
            'table_counts': table_counts,
            'query_type_counts': query_type_counts,
            'fingerprint_counts': dict(sorted(fingerprint_counts.items(), key=lambda x: x[1], reverse=True)[:10])
        }
    
    def generate_html_report(self, output_file=None):
        if not output_file:
            output_file = Config.REPORT_FILE
        
        stats = self.get_statistics()
        
        html_content = f"""
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>数据库死锁诊断报告</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; background-color: #f5f5f5; }}
        .container {{ max-width: 1200px; margin: 0 auto; background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
        h1 {{ color: #333; border-bottom: 3px solid #e74c3c; padding-bottom: 10px; }}
        h2 {{ color: #555; margin-top: 30px; }}
        .stats-box {{ display: flex; gap: 20px; margin: 20px 0; }}
        .stat-item {{ background: #f8f9fa; padding: 20px; border-radius: 8px; flex: 1; text-align: center; }}
        .stat-value {{ font-size: 32px; font-weight: bold; color: #e74c3c; }}
        .stat-label {{ color: #666; margin-top: 5px; }}
        table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
        th, td {{ padding: 12px; text-align: left; border-bottom: 1px solid #ddd; }}
        th {{ background-color: #f8f9fa; font-weight: bold; }}
        tr:hover {{ background-color: #f5f5f5; }}
        .deadlock-item {{ border: 1px solid #ddd; border-radius: 8px; padding: 15px; margin: 15px 0; }}
        .txn-box {{ background: #f8f9fa; padding: 10px; margin: 10px 0; border-radius: 4px; border-left: 4px solid #3498db; }}
        .sql-code {{ background: #2d2d2d; color: #f8f8f2; padding: 10px; border-radius: 4px; font-family: monospace; overflow-x: auto; margin: 10px 0; }}
        .timestamp {{ color: #666; font-size: 0.9em; }}
        .badge {{ display: inline-block; padding: 3px 8px; border-radius: 12px; font-size: 12px; margin-right: 5px; }}
        .badge-select {{ background: #3498db; color: white; }}
        .badge-update {{ background: #f39c12; color: white; }}
        .badge-insert {{ background: #2ecc71; color: white; }}
        .badge-delete {{ background: #e74c3c; color: white; }}
        .badge-other {{ background: #95a5a6; color: white; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🔒 数据库死锁诊断报告</h1>
        <p class="timestamp">报告生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        
        <h2>📊 统计概览</h2>
        <div class="stats-box">
            <div class="stat-item">
                <div class="stat-value">{stats['total_deadlocks']}</div>
                <div class="stat-label">总死锁次数</div>
            </div>
        </div>
        
        <h2>📋 涉及表统计</h2>
        <table>
            <tr><th>表名</th><th>出现次数</th></tr>
            {self._generate_table_rows(stats['table_counts'])}
        </table>
        
        <h2>📝 查询类型统计</h2>
        <table>
            <tr><th>查询类型</th><th>出现次数</th></tr>
            {self._generate_query_type_rows(stats['query_type_counts'])}
        </table>
        
        <h2>🔍 高频SQL指纹</h2>
        <table>
            <tr><th>SQL指纹</th><th>出现次数</th></tr>
            {self._generate_fingerprint_rows(stats['fingerprint_counts'])}
        </table>
        
        <h2>📜 死锁历史记录</h2>
        {self._generate_deadlock_history()}
    </div>
</body>
</html>
        """
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        return output_file
    
    def _generate_table_rows(self, data):
        rows = []
        for table, count in sorted(data.items(), key=lambda x: x[1], reverse=True):
            rows.append(f"<tr><td><code>{table}</code></td><td>{count}</td></tr>")
        return '\n'.join(rows) if rows else '<tr><td colspan="2">暂无数据</td></tr>'
    
    def _generate_query_type_rows(self, data):
        rows = []
        badge_classes = {
            'SELECT': 'badge-select',
            'UPDATE': 'badge-update',
            'INSERT': 'badge-insert',
            'DELETE': 'badge-delete',
            'OTHER': 'badge-other'
        }
        for qtype, count in sorted(data.items(), key=lambda x: x[1], reverse=True):
            badge_class = badge_classes.get(qtype, 'badge-other')
            rows.append(f"<tr><td><span class='badge {badge_class}'>{qtype}</span></td><td>{count}</td></tr>")
        return '\n'.join(rows) if rows else '<tr><td colspan="2">暂无数据</td></tr>'
    
    def _generate_fingerprint_rows(self, data):
        rows = []
        for fingerprint, count in data.items():
            rows.append(f"<tr><td><code style='word-break: break-all;'>{fingerprint}</code></td><td>{count}</td></tr>")
        return '\n'.join(rows) if rows else '<tr><td colspan="2">暂无数据</td></tr>'
    
    def _generate_deadlock_history(self):
        if not self.history:
            return "<p>暂无死锁记录</p>"
        
        items = []
        for deadlock in reversed(self.history):
            txn_html = []
            for txn in deadlock.get('transactions', []):
                queries_html = []
                for sql in txn.get('queries', []):
                    qtype = self.sql_fingerprint.classify_query_type(sql)
                    badge_class = {
                        'SELECT': 'badge-select',
                        'UPDATE': 'badge-update',
                        'INSERT': 'badge-insert',
                        'DELETE': 'badge-delete',
                        'OTHER': 'badge-other'
                    }.get(qtype, 'badge-other')
                    
                    queries_html.append(f"""
                        <div>
                            <span class='badge {badge_class}'>{qtype}</span>
                            <div class='sql-code'>{sql}</div>
                        </div>
                    """)
                
                holds_html = []
                for hold in txn.get('holds', []):
                    holds_html.append(f"<li>{hold.get('mode', '?')} lock on {hold.get('table', '?')} (index: {hold.get('index', '?')})</li>")
                
                waiting_html = ""
                waiting = txn.get('waiting_for')
                if waiting:
                    waiting_html = f"""
                        <p><strong>等待锁:</strong> {waiting.get('mode', '?')} lock on {waiting.get('table', '?')}</p>
                    """
                
                txn_html.append(f"""
                    <div class='txn-box'>
                        <h4>事务 {txn.get('transaction_id', 'unknown')} (线程: {txn.get('thread_id', '?')})</h4>
                        <p><strong>执行SQL:</strong></p>
                        {''.join(queries_html)}
                        <p><strong>持有锁:</strong></p>
                        <ul>{''.join(holds_html) if holds_html else '<li>无</li>'}</ul>
                        {waiting_html}
                    </div>
                """)
            
            items.append(f"""
                <div class='deadlock-item'>
                    <h3>死锁 #{deadlock.get('id')} - {deadlock.get('timestamp', '?')}</h3>
                    {''.join(txn_html)}
                </div>
            """)
        
        return '\n'.join(items)
    
    def clear_history(self):
        self.history = []
        self._save_history()
