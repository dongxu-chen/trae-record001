import html
from typing import Dict, List, Tuple
from datetime import datetime
from stats import StatisticsCollector

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Nginx 日志分析报告</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 40px 20px;
        }}
        .container {{ max-width: 1400px; margin: 0 auto; }}
        .header {{
            background: white;
            border-radius: 16px;
            padding: 40px;
            margin-bottom: 30px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.1);
        }}
        .header h1 {{
            color: #1a1a2e;
            font-size: 2.5em;
            margin-bottom: 10px;
        }}
        .header .subtitle {{
            color: #666;
            font-size: 1.1em;
        }}
        .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 20px; margin-bottom: 30px; }}
        .card {{
            background: white;
            border-radius: 12px;
            padding: 25px;
            box-shadow: 0 4px 20px rgba(0,0,0,0.08);
            transition: transform 0.3s ease;
        }}
        .card:hover {{ transform: translateY(-5px); }}
        .card h2 {{ color: #1a1a2e; font-size: 1.3em; margin-bottom: 20px; border-bottom: 2px solid #e0e0e0; padding-bottom: 10px; }}
        .stat-item {{ display: flex; justify-content: space-between; align-items: center; padding: 12px 0; border-bottom: 1px solid #f0f0f0; }}
        .stat-item:last-child {{ border-bottom: none; }}
        .stat-label {{ color: #555; font-weight: 500; }}
        .stat-value {{ color: #1a1a2e; font-weight: 700; font-size: 1.2em; }}
        .summary-card {{
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            color: white;
        }}
        .summary-card h2 {{ color: white; border-bottom-color: rgba(255,255,255,0.2); }}
        .summary-card .stat-label {{ color: #b8c1ec; }}
        .summary-card .stat-value {{ color: white; }}
        .table-card {{ grid-column: 1 / -1; }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 15px;
        }}
        th, td {{
            padding: 15px;
            text-align: left;
            border-bottom: 1px solid #eee;
        }}
        th {{
            background: #f8f9fa;
            color: #1a1a2e;
            font-weight: 600;
            font-size: 0.95em;
        }}
        td {{ color: #555; }}
        tr:hover {{ background: #f8f9fa; }}
        .progress-bar {{
            height: 8px;
            background: #e0e0e0;
            border-radius: 4px;
            overflow: hidden;
            margin-top: 5px;
        }}
        .progress-bar .fill {{
            height: 100%;
            background: linear-gradient(90deg, #667eea, #764ba2);
            border-radius: 4px;
            transition: width 0.5s ease;
        }}
        .status-2xx {{ color: #28a745; }}
        .status-3xx {{ color: #17a2b8; }}
        .status-4xx {{ color: #ffc107; }}
        .status-5xx {{ color: #dc3545; }}
        .count {{ font-weight: 600; color: #1a1a2e; }}
        .footer {{
            text-align: center;
            padding: 30px;
            color: rgba(255,255,255,0.8);
            font-size: 0.9em;
        }}
        .badge {{
            display: inline-block;
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 0.85em;
            font-weight: 600;
        }}
        .badge-2xx {{ background: #d4edda; color: #155724; }}
        .badge-3xx {{ background: #d1ecf1; color: #0c5460; }}
        .badge-4xx {{ background: #fff3cd; color: #856404; }}
        .badge-5xx {{ background: #f8d7da; color: #721c24; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Nginx 日志分析报告</h1>
            <p class="subtitle">生成时间: {generated_at}</p>
        </div>
        {summary_section}
        {sections}
        <div class="footer">
            <p>Nginx Log Analyzer - 日志分析工具</p>
        </div>
    </div>
</body>
</html>
"""

class HTMLReporter:
    def __init__(self, collector: StatisticsCollector, top_n: int = 10):
        self.collector = collector
        self.top_n = top_n
    
    def _escape_html(self, value) -> str:
        if value is None:
            return ""
        return html.escape(str(value), quote=True)
    
    def _format_bytes(self, bytes_val: int) -> str:
        if bytes_val < 1024:
            return f"{bytes_val} B"
        elif bytes_val < 1024 * 1024:
            return f"{bytes_val / 1024:.2f} KB"
        elif bytes_val < 1024 * 1024 * 1024:
            return f"{bytes_val / (1024 * 1024):.2f} MB"
        else:
            return f"{bytes_val / (1024 * 1024 * 1024):.2f} GB"
    
    def _get_status_badge_class(self, status: int) -> str:
        if 200 <= status < 300:
            return "badge-2xx"
        elif 300 <= status < 400:
            return "badge-3xx"
        elif 400 <= status < 500:
            return "badge-4xx"
        elif 500 <= status < 600:
            return "badge-5xx"
        return ""
    
    def _generate_summary_section(self) -> str:
        stats = self.collector.stats
        status_summary = self.collector.get_status_code_summary()
        bandwidth_mb = self.collector.get_bandwidth_mb()
        
        return f"""
        <div class="grid">
            <div class="card summary-card">
                <h2>总览统计</h2>
                <div class="stat-item">
                    <span class="stat-label">总请求数</span>
                    <span class="stat-value">{stats.total_requests:,}</span>
                </div>
                <div class="stat-item">
                    <span class="stat-label">总带宽</span>
                    <span class="stat-value">{self._format_bytes(stats.total_bytes)}</span>
                </div>
                <div class="stat-item">
                    <span class="stat-label">平均请求大小</span>
                    <span class="stat-value">{self._format_bytes(stats.total_bytes // stats.total_requests) if stats.total_requests > 0 else '0 B'}</span>
                </div>
                <div class="stat-item">
                    <span class="stat-label">唯一 IP 数</span>
                    <span class="stat-value">{len(stats.ips):,}</span>
                </div>
            </div>
            <div class="card summary-card">
                <h2>状态码分布</h2>
                <div class="stat-item">
                    <span class="stat-label">2xx (成功)</span>
                    <span class="stat-value">{status_summary.get('2xx', 0):,}</span>
                </div>
                <div class="stat-item">
                    <span class="stat-label">3xx (重定向)</span>
                    <span class="stat-value">{status_summary.get('3xx', 0):,}</span>
                </div>
                <div class="stat-item">
                    <span class="stat-label">4xx (客户端错误)</span>
                    <span class="stat-value">{status_summary.get('4xx', 0):,}</span>
                </div>
                <div class="stat-item">
                    <span class="stat-label">5xx (服务器错误)</span>
                    <span class="stat-value">{status_summary.get('5xx', 0):,}</span>
                </div>
            </div>
            <div class="card summary-card">
                <h2>请求方法分布</h2>
                {''.join([
                    f'<div class="stat-item"><span class="stat-label">{self._escape_html(method)}</span><span class="stat-value">{count:,}</span></div>'
                    for method, count in stats.methods.most_common(5)
                ])}
            </div>
        </div>
        """
    
    def _generate_table_section(self, title: str, items: List[Tuple], headers: List[str]) -> str:
        if not items:
            return f"""
            <div class="card table-card">
                <h2>{title}</h2>
                <p style="color: #666; padding: 20px;">暂无数据</p>
            </div>
            """
        
        max_count = max(count for _, count in items)
        
        rows = []
        for i, (item, count) in enumerate(items):
            percentage = (count / max_count * 100) if max_count > 0 else 0
            row_cells = []
            row_cells.append(f'<td>{i + 1}</td>')
            
            escaped_item = self._escape_html(item)
            if len(headers) == 3:
                if headers[1] == '状态码':
                    badge_class = self._get_status_badge_class(item)
                    row_cells.append(f'<td><span class="badge {badge_class}">{escaped_item}</span></td>')
                else:
                    row_cells.append(f'<td>{escaped_item}</td>')
                row_cells.append(f'<td><span class="count">{count:,}</span><div class="progress-bar"><div class="fill" style="width: {percentage}%;"></div></div></td>')
            else:
                row_cells.append(f'<td>{escaped_item}</td>')
                row_cells.append(f'<td><span class="count">{count:,}</span><div class="progress-bar"><div class="fill" style="width: {percentage}%;"></div></div></td>')
            
            rows.append(f'<tr>{"".join(row_cells)}</tr>')
        
        return f"""
        <div class="card table-card">
            <h2>{title}</h2>
            <table>
                <thead>
                    <tr>
                        <th style="width: 60px;">#</th>
                        {''.join(f'<th>{h}</th>' for h in headers)}
                    </tr>
                </thead>
                <tbody>
                    {''.join(rows)}
                </tbody>
            </table>
        </div>
        """
    
    def _generate_hourly_section(self) -> str:
        hours = self.collector.stats.requests_per_hour
        if not hours:
            return ""
        
        sorted_hours = sorted(hours.items())
        max_count = max(count for _, count in sorted_hours)
        
        rows = []
        for hour, count in sorted_hours:
            percentage = (count / max_count * 100) if max_count > 0 else 0
            rows.append(f"""
            <tr>
                <td>{hour:02d}:00</td>
                <td><span class="count">{count:,}</span><div class="progress-bar"><div class="fill" style="width: {percentage}%;"></div></div></td>
            </tr>
            """)
        
        return f"""
        <div class="card table-card">
            <h2>每小时请求分布</h2>
            <table>
                <thead>
                    <tr>
                        <th>时间段</th>
                        <th>请求数</th>
                    </tr>
                </thead>
                <tbody>
                    {''.join(rows)}
                </tbody>
            </table>
        </div>
        """
    
    def generate(self, output_path: str) -> None:
        sections = []
        
        top_ips = self.collector.get_top_ips(self.top_n)
        if top_ips:
            sections.append(self._generate_table_section("Top IP 访问", top_ips, ["IP 地址", "请求数"]))
        
        top_status = self.collector.get_top_status_codes(self.top_n)
        if top_status:
            sections.append(self._generate_table_section("状态码统计", top_status, ["状态码", "请求数"]))
        
        top_paths = self.collector.get_top_paths(self.top_n)
        if top_paths:
            sections.append(self._generate_table_section("Top 请求路径", top_paths, ["路径", "请求数"]))
        
        top_ua = self.collector.get_top_user_agents(self.top_n)
        if top_ua:
            sections.append(self._generate_table_section("Top User-Agent", top_ua, ["User-Agent", "请求数"]))
        
        top_referers = self.collector.get_top_referers(self.top_n)
        if top_referers:
            sections.append(self._generate_table_section("Top 来源页面", top_referers, ["Referer", "请求数"]))
        
        hourly_section = self._generate_hourly_section()
        if hourly_section:
            sections.append(hourly_section)
        
        html_content = HTML_TEMPLATE.format(
            generated_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            summary_section=self._generate_summary_section(),
            sections="".join(sections)
        )
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        print(f"报告已生成: {output_path}")
