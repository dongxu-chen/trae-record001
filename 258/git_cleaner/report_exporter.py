"""报告导出模块"""
import json
import os
from datetime import datetime
from typing import List, Dict, Optional
from pathlib import Path

class ReportExporter:
    """导出清理报告"""
    
    def __init__(self, output_dir: str = "cleanup_reports"):
        self.output_dir = output_dir
        Path(output_dir).mkdir(parents=True, exist_ok=True)
    
    def export_json(self, data: Dict, filename: Optional[str] = None) -> str:
        """导出JSON格式报告"""
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"cleanup_report_{timestamp}.json"
        
        filepath = os.path.join(self.output_dir, filename)
        
        def default_serializer(obj):
            if hasattr(obj, 'isoformat'):
                return obj.isoformat()
            return str(obj)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, default=default_serializer, ensure_ascii=False)
        
        return filepath
    
    def export_html(self, data: Dict, filename: Optional[str] = None) -> str:
        """导出HTML格式报告"""
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"cleanup_report_{timestamp}.html"
        
        filepath = os.path.join(self.output_dir, filename)
        
        html_content = self._generate_html(data)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        return filepath
    
    def _generate_html(self, data: Dict) -> str:
        """生成HTML内容"""
        large_files = data.get('large_files', [])
        sensitive_findings = data.get('sensitive_findings', [])
        stale_branches = data.get('stale_branches', [])
        storage_analysis = data.get('storage_analysis', {})
        cleanup_savings = data.get('cleanup_savings', {})
        
        total_large_size = sum(f.get('size', 0) for f in large_files)
        saved_mb = round(total_large_size / (1024 * 1024), 2)
        
        html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Git仓库清理报告</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #f5f5f5; color: #333; line-height: 1.6; }}
        .container {{ max-width: 1200px; margin: 0 auto; padding: 20px; }}
        .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; border-radius: 10px; margin-bottom: 30px; }}
        .header h1 {{ font-size: 28px; margin-bottom: 10px; }}
        .stats {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; margin-bottom: 30px; }}
        .stat-card {{ background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
        .stat-card h3 {{ color: #667eea; font-size: 14px; text-transform: uppercase; margin-bottom: 10px; }}
        .stat-card .value {{ font-size: 32px; font-weight: bold; }}
        .stat-card .value.red {{ color: #e74c3c; }}
        .stat-card .value.yellow {{ color: #f39c12; }}
        .stat-card .value.green {{ color: #27ae60; }}
        section {{ background: white; padding: 25px; border-radius: 8px; margin-bottom: 20px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
        section h2 {{ color: #333; margin-bottom: 20px; padding-bottom: 10px; border-bottom: 2px solid #667eea; }}
        table {{ width: 100%; border-collapse: collapse; }}
        th, td {{ padding: 12px; text-align: left; border-bottom: 1px solid #eee; }}
        th {{ background: #f8f9fa; font-weight: 600; }}
        tr:hover {{ background: #f5f5f5; }}
        .savings {{ background: #d4edda; border-left: 4px solid #27ae60; padding: 20px; border-radius: 4px; margin-bottom: 20px; }}
        .savings h3 {{ color: #155724; margin-bottom: 10px; }}
        .warning {{ background: #fff3cd; border-left: 4px solid #f39c12; padding: 15px; border-radius: 4px; margin: 10px 0; }}
        .danger {{ background: #f8d7da; border-left: 4px solid #e74c3c; padding: 15px; border-radius: 4px; margin: 10px 0; }}
        .badge {{ display: inline-block; padding: 4px 12px; border-radius: 20px; font-size: 12px; font-weight: 600; }}
        .badge.red {{ background: #f8d7da; color: #721c24; }}
        .badge.yellow {{ background: #fff3cd; color: #856404; }}
        .badge.green {{ background: #d4edda; color: #155724; }}
        .footer {{ text-align: center; padding: 20px; color: #666; font-size: 14px; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🗂️ Git仓库清理报告</h1>
            <p>生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            <p>仓库路径: {data.get('repo_path', 'N/A')}</p>
        </div>
        
        <div class="stats">
            <div class="stat-card">
                <h3>大文件数量</h3>
                <div class="value yellow">{len(large_files)}</div>
            </div>
            <div class="stat-card">
                <h3>敏感信息</h3>
                <div class="value red">{len(sensitive_findings)}</div>
            </div>
            <div class="stat-card">
                <h3>陈旧分支</h3>
                <div class="value yellow">{len(stale_branches)}</div>
            </div>
            <div class="stat-card">
                <h3>可节省空间</h3>
                <div class="value green">{saved_mb} MB</div>
            </div>
        </div>
        
        <div class="savings">
            <h3>💰 预计清理效果</h3>
            <p>清理大文件后预计可释放 <strong>{saved_mb} MB</strong> 存储空间</p>
        </div>
        
        <section>
            <h2>📁 大文件清单</h2>
            {self._generate_large_files_table(large_files)}
        </section>
        
        <section>
            <h2>🔐 敏感信息发现</h2>
            {self._generate_sensitive_table(sensitive_findings)}
        </section>
        
        <section>
            <h2>🌿 陈旧分支</h2>
            {self._generate_branches_table(stale_branches)}
        </section>
        
        {self._generate_storage_section(storage_analysis)}
        
        <div class="footer">
            <p>由 Git仓库归档清理工具 生成</p>
        </div>
    </div>
</body>
</html>"""
        return html
    
    def _generate_large_files_table(self, large_files: List[Dict]) -> str:
        """生成大文件表格"""
        if not large_files:
            return '<p class="badge green">✓ 未发现大文件</p>'
        
        rows = []
        for f in large_files[:50]:
            size_mb = round(f.get('size', 0) / (1024 * 1024), 2)
            rows.append(f"""
            <tr>
                <td>{f.get('path', 'N/A')}</td>
                <td>{size_mb} MB</td>
                <td>{f.get('commit_date', 'N/A')[:10]}</td>
                <td><code>{f.get('commit', 'N/A')[:12]}</code></td>
            </tr>""")
        
        return f"""
        <table>
            <thead>
                <tr>
                    <th>文件路径</th>
                    <th>大小</th>
                    <th>首次提交日期</th>
                    <th>Commit ID</th>
                </tr>
            </thead>
            <tbody>
                {''.join(rows)}
            </tbody>
        </table>
        {len(large_files) > 50 and f'<p style="margin-top:10px;color:#666;">... 还有 {len(large_files) - 50} 个文件未显示</p>' or ''}
        """
    
    def _generate_sensitive_table(self, findings: List[Dict]) -> str:
        """生成敏感信息表格"""
        if not findings:
            return '<p class="badge green">✓ 未发现敏感信息</p>'
        
        rows = []
        for f in findings[:50]:
            rows.append(f"""
            <tr>
                <td><span class="badge red">{f.get('type', 'Unknown')}</span></td>
                <td>{f.get('path', 'N/A')}</td>
                <td>{f.get('line', 'N/A')}</td>
                <td><code>{f.get('match', 'N/A')[:80]}</code></td>
            </tr>""")
        
        return f"""
        <table>
            <thead>
                <tr>
                    <th>类型</th>
                    <th>文件路径</th>
                    <th>行号</th>
                    <th>匹配内容</th>
                </tr>
            </thead>
            <tbody>
                {''.join(rows)}
            </tbody>
        </table>
        {len(findings) > 50 and f'<p style="margin-top:10px;color:#666;">... 还有 {len(findings) - 50} 处未显示</p>' or ''}
        """
    
    def _generate_branches_table(self, branches: List[Dict]) -> str:
        """生成陈旧分支表格"""
        if not branches:
            return '<p class="badge green">✓ 未发现陈旧分支</p>'
        
        rows = []
        for b in branches:
            branch_type = "远程" if b.get('is_remote') else "本地"
            rows.append(f"""
            <tr>
                <td><span class="badge yellow">{branch_type}</span></td>
                <td>{b.get('name', 'N/A')}</td>
                <td>{b.get('days_since_update', 'N/A')} 天</td>
                <td>{b.get('last_committer', 'N/A')}</td>
            </tr>""")
        
        return f"""
        <table>
            <thead>
                <tr>
                    <th>类型</th>
                    <th>分支名称</th>
                    <th>未更新天数</th>
                    <th>最后提交者</th>
                </tr>
            </thead>
            <tbody>
                {''.join(rows)}
            </tbody>
        </table>
        """
    
    def _generate_storage_section(self, storage: Dict) -> str:
        """生成存储分析部分"""
        if not storage or 'error' in storage:
            return ''
        
        pred = storage.get('prediction', {})
        trend = storage.get('trend', {})
        
        current_gb = round(pred.get('current_size_gb', 0), 2)
        monthly_mb = round(trend.get('avg_monthly_growth_mb', 0), 2)
        
        thresholds = pred.get('time_to_thresholds', [])
        
        thresholds_html = ''
        if thresholds:
            threshold_rows = []
            for t in thresholds:
                threshold_rows.append(f"<li>达到 <strong>{t['threshold']}</strong>: 预计 {t['months_needed']} 个月后 ({t['estimated_date']})</li>")
            thresholds_html = f"""
            <div class="warning">
                <h4>📈 仓库膨胀预测</h4>
                <ul>
                    {''.join(threshold_rows)}
                </ul>
            </div>
            """
        
        return f"""
        <section>
            <h2>📊 存储空间分析</h2>
            <div class="stats" style="grid-template-columns: repeat(2, 1fr);">
                <div class="stat-card">
                    <h3>当前仓库大小</h3>
                    <div class="value">{current_gb} GB</div>
                </div>
                <div class="stat-card">
                    <h3>月均增长</h3>
                    <div class="value yellow">{monthly_mb} MB</div>
                </div>
            </div>
            {thresholds_html}
        </section>
        """
    
    def generate_cleanup_report_data(self, repo_path: str, large_files: List[Dict], 
                                  sensitive_findings: List[Dict], 
                                  stale_branches: List[Dict],
                                  storage_analysis: Dict = None) -> Dict:
        """生成完整的报告数据"""
        total_large_size = sum(f.get('size', 0) for f in large_files)
        
        return {
            'repo_path': repo_path,
            'generated_at': datetime.now().isoformat(),
            'large_files': large_files,
            'sensitive_findings': sensitive_findings,
            'stale_branches': stale_branches,
            'summary': {
                'large_file_count': len(large_files),
                'sensitive_findings_count': len(sensitive_findings),
                'stale_branches_count': len(stale_branches),
                'total_large_size_bytes': total_large_size,
                'total_large_size_mb': round(total_large_size / (1024 * 1024), 2),
            },
            'storage_analysis': storage_analysis,
        }
