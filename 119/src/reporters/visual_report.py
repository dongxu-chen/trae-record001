#!/usr/bin/env python3
"""
可视化成本报告生成器
生成带图表的 HTML 交互式报告，展示资源-成本映射关系
"""
import json
import argparse
from datetime import datetime
from typing import Dict, List
from collections import defaultdict
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from analyzers.tfstate_analyzer import TfstateAnalyzer


class VisualReportGenerator:
    def __init__(self, analysis_data: Dict):
        self.data = analysis_data
        self.summary = analysis_data.get('summary', {})
        self.resources = analysis_data.get('resources', [])

    def generate_cost_by_provider_chart(self) -> str:
        cost_by_provider = self.summary.get('cost_by_provider', {})
        if not cost_by_provider:
            return ""
        
        labels = list(cost_by_provider.keys())
        values = list(cost_by_provider.values())
        total = sum(values)
        percentages = [round(v/total*100, 1) if total > 0 else 0 for v in values]
        
        colors = {
            'aws': '#FF9900',
            'azure': '#0078D4',
            'gcp': '#4285F4',
        }
        bg_colors = [colors.get(p, '#888888') for p in labels]
        
        return f"""
        <div class="chart-container">
            <h3>💰 成本分布 - 按云服务商</h3>
            <div style="display: flex; align-items: center; gap: 30px;">
                <div style="flex: 1;">
                    <canvas id="providerChart"></canvas>
                </div>
                <div style="flex: 1;">
                    <table class="data-table">
                        <thead>
                            <tr><th>服务商</th><th>月度成本</th><th>占比</th></tr>
                        </thead>
                        <tbody>
                            {''.join([f'<tr><td style="color:{bg_colors[i]}">{labels[i].upper()}</td><td>${values[i]:.2f}</td><td>{percentages[i]}%</td></tr>' for i in range(len(labels))])}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
        
        <script>
        new Chart(document.getElementById('providerChart'), {{
            type: 'pie',
            data: {{
                labels: {json.dumps([l.upper() for l in labels])},
                datasets: [{{
                    data: {json.dumps(values)},
                    backgroundColor: {json.dumps(bg_colors)},
                    borderWidth: 2,
                    borderColor: '#fff'
                }}]
            }},
            options: {{
                responsive: true,
                plugins: {{
                    legend: {{ position: 'bottom' }},
                    tooltip: {{
                        callbacks: {{
                            label: function(context) {{
                                return context.label + ': $' + context.parsed.toFixed(2) + '/mo';
                            }}
                        }}
                    }}
                }}
            }}
        }});
        </script>
        """

    def generate_cost_by_type_chart(self) -> str:
        cost_by_type = self.summary.get('cost_by_resource_type', {})
        if not cost_by_type:
            return ""
        
        sorted_types = sorted(cost_by_type.items(), key=lambda x: -x[1])[:10]
        labels = [k.split('_')[-1] if '_' in k else k for k, v in sorted_types]
        values = [v for k, v in sorted_types]
        
        return f"""
        <div class="chart-container">
            <h3>📊 成本分布 - 按资源类型 (Top 10)</h3>
            <canvas id="typeChart" height="300"></canvas>
        </div>
        
        <script>
        new Chart(document.getElementById('typeChart'), {{
            type: 'bar',
            data: {{
                labels: {json.dumps(labels)},
                datasets: [{{
                    label: '月度成本 ($)',
                    data: {json.dumps(values)},
                    backgroundColor: 'rgba(54, 162, 235, 0.8)',
                    borderColor: 'rgba(54, 162, 235, 1)',
                    borderWidth: 1
                }}]
            }},
            options: {{
                responsive: true,
                indexAxis: 'y',
                plugins: {{
                    legend: {{ display: false }}
                }},
                scales: {{
                    x: {{
                        beginAtZero: true,
                        ticks: {{ callback: v => '$' + v.toFixed(2) }}
                    }}
                }}
            }}
        }});
        </script>
        """

    def generate_cost_by_region_chart(self) -> str:
        cost_by_region = self.summary.get('cost_by_region', {})
        if not cost_by_region:
            return ""
        
        sorted_regions = sorted(cost_by_region.items(), key=lambda x: -x[1])[:8]
        labels = [k for k, v in sorted_regions]
        values = [v for k, v in sorted_regions]
        
        return f"""
        <div class="chart-container">
            <h3>🌍 成本分布 - 按区域</h3>
            <canvas id="regionChart" height="250"></canvas>
        </div>
        
        <script>
        new Chart(document.getElementById('regionChart'), {{
            type: 'bar',
            data: {{
                labels: {json.dumps(labels)},
                datasets: [{{
                    label: '月度成本 ($)',
                    data: {json.dumps(values)},
                    backgroundColor: [
                        'rgba(75, 192, 192, 0.8)',
                        'rgba(153, 102, 255, 0.8)',
                        'rgba(255, 159, 64, 0.8)',
                        'rgba(255, 99, 132, 0.8)',
                        'rgba(54, 162, 235, 0.8)',
                        'rgba(201, 203, 207, 0.8)',
                        'rgba(255, 205, 86, 0.8)',
                        'rgba(60, 179, 113, 0.8)'
                    ],
                    borderWidth: 1
                }}]
            }},
            options: {{
                responsive: true,
                plugins: {{
                    legend: {{ display: false }}
                }},
                scales: {{
                    y: {{
                        beginAtZero: true,
                        ticks: {{ callback: v => '$' + v.toFixed(2) }}
                    }}
                }}
            }}
        }});
        </script>
        """

    def generate_resource_table(self) -> str:
        if not self.resources:
            return "<p>暂无资源数据</p>"
        
        sorted_resources = sorted(self.resources, key=lambda x: -x['estimated_monthly_cost'])
        high_cost = [r for r in sorted_resources if r['estimated_monthly_cost'] > 50]
        
        rows = []
        for r in sorted_resources[:20]:
            cost = r['estimated_monthly_cost']
            cost_badge = "high" if cost > 100 else "medium" if cost > 50 else "low"
            
            provider_colors = {
                'aws': '#FF9900',
                'azure': '#0078D4',
                'gcp': '#4285F4',
            }
            provider_color = provider_colors.get(r['provider'], '#888')
            
            tag_count = len(r.get('tags', {}))
            tag_status = "✅" if tag_count >= 2 else "⚠️" if tag_count > 0 else "❌"
            
            rows.append(f"""
            <tr>
                <td><span class="provider-badge" style="background: {provider_color}">{r['provider'].upper()}</span></td>
                <td style="font-family: monospace; font-size: 12px;">{r['resource_address']}</td>
                <td>{r['resource_type'].split('_')[-1] if '_' in r['resource_type'] else r['resource_type']}</td>
                <td><span class="cost-badge {cost_badge}">${cost:.2f}/mo</span></td>
                <td>{r['region']}</td>
                <td>{tag_status} {tag_count}</td>
            </tr>
            """)
        
        return f"""
        <div class="chart-container">
            <h3>📋 资源清单（按成本排序，Top 20）</h3>
            <div class="table-wrapper">
                <table class="data-table">
                    <thead>
                        <tr>
                            <th>服务商</th>
                            <th>资源地址</th>
                            <th>类型</th>
                            <th>月度成本</th>
                            <th>区域</th>
                            <th>标签</th>
                        </tr>
                    </thead>
                    <tbody>
                        {''.join(rows)}
                    </tbody>
                </table>
            </div>
        </div>
        """

    def generate_summary_cards(self) -> str:
        total_monthly = self.summary.get('total_monthly_cost', 0)
        total_annual = self.summary.get('total_annual_cost', 0)
        resource_count = self.summary.get('total_resources', 0)
        untagged = self.summary.get('resources_without_tags', 0)
        
        monthly_trend = "+0%"
        annual_savings = total_monthly * 0.3
        
        return f"""
        <div class="summary-cards">
            <div class="card primary">
                <div class="card-icon">💰</div>
                <div class="card-content">
                    <div class="card-label">月度总成本</div>
                    <div class="card-value">${total_monthly:.2f}</div>
                    <div class="card-trend">{monthly_trend}</div>
                </div>
            </div>
            <div class="card success">
                <div class="card-icon">📅</div>
                <div class="card-content">
                    <div class="card-label">年度总成本</div>
                    <div class="card-value">${total_annual:.2f}</div>
                    <div class="card-trend">预估</div>
                </div>
            </div>
            <div class="card warning">
                <div class="card-icon">☁️</div>
                <div class="card-content">
                    <div class="card-label">托管资源数</div>
                    <div class="card-value">{resource_count}</div>
                    <div class="card-trend">个资源</div>
                </div>
            </div>
            <div class="card info">
                <div class="card-icon">💡</div>
                <div class="card-content">
                    <div class="card-label">预估年节省 (RI)</div>
                    <div class="card-value">${annual_savings:.2f}</div>
                    <div class="card-trend">约 30%</div>
                </div>
            </div>
        </div>
        
        <div class="alert-box {'warning' if untagged > 0 else 'success'}">
            <span style="font-size: 20px;">{'⚠️' if untagged > 0 else '✅'}</span>
            <div style="margin-left: 15px;">
                <strong>{'标签治理需要关注' if untagged > 0 else '标签治理良好'}</strong>
                <p>{untagged} 个资源缺少必要标签，建议补充 Environment、Project、Owner 等标签以便成本归因。</p>
            </div>
        </div>
        """

    def generate_html(self) -> str:
        analysis_date = self.summary.get('analysis_date', datetime.now().isoformat())
        
        html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Terraform 成本分析报告</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); min-height: 100vh; padding: 20px; }}
        .container {{ max-width: 1200px; margin: 0 auto; }}
        .header {{ background: white; border-radius: 16px; padding: 30px; margin-bottom: 20px; box-shadow: 0 10px 40px rgba(0,0,0,0.1); }}
        .header h1 {{ color: #1a202c; font-size: 28px; margin-bottom: 10px; }}
        .header p {{ color: #718096; }}
        .summary-cards {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 20px; margin-bottom: 20px; }}
        .card {{ background: white; border-radius: 12px; padding: 20px; display: flex; align-items: center; gap: 15px; box-shadow: 0 4px 20px rgba(0,0,0,0.08); transition: transform 0.3s; }}
        .card:hover {{ transform: translateY(-5px); }}
        .card-icon {{ font-size: 36px; }}
        .card-content {{ flex: 1; }}
        .card-label {{ color: #718096; font-size: 13px; text-transform: uppercase; letter-spacing: 0.5px; }}
        .card-value {{ font-size: 28px; font-weight: 700; color: #1a202c; margin: 5px 0; }}
        .card-trend {{ font-size: 12px; color: #48bb78; font-weight: 500; }}
        .card.primary .card-value {{ color: #667eea; }}
        .card.success .card-value {{ color: #48bb78; }}
        .card.warning .card-value {{ color: #ed8936; }}
        .card.info .card-value {{ color: #4299e1; }}
        .alert-box {{ background: white; border-radius: 12px; padding: 20px; display: flex; align-items: center; margin-bottom: 20px; border-left: 4px solid; box-shadow: 0 4px 20px rgba(0,0,0,0.08); }}
        .alert-box.warning {{ border-left-color: #ed8936; background: linear-gradient(90deg, #fffaf0, white); }}
        .alert-box.success {{ border-left-color: #48bb78; background: linear-gradient(90deg, #f0fff4, white); }}
        .alert-box strong {{ display: block; color: #1a202c; font-size: 16px; margin-bottom: 5px; }}
        .alert-box p {{ color: #718096; font-size: 14px; }}
        .chart-container {{ background: white; border-radius: 12px; padding: 25px; margin-bottom: 20px; box-shadow: 0 4px 20px rgba(0,0,0,0.08); }}
        .chart-container h3 {{ color: #1a202c; margin-bottom: 20px; font-size: 18px; }}
        .data-table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
        .data-table th, .data-table td {{ padding: 12px 15px; text-align: left; border-bottom: 1px solid #e2e8f0; }}
        .data-table th {{ background: #f7fafc; color: #4a5568; font-weight: 600; }}
        .data-table tr:hover {{ background: #f7fafc; }}
        .table-wrapper {{ overflow-x: auto; }}
        .provider-badge {{ display: inline-block; padding: 3px 8px; border-radius: 4px; color: white; font-size: 11px; font-weight: 600; }}
        .cost-badge {{ display: inline-block; padding: 4px 10px; border-radius: 20px; font-size: 12px; font-weight: 600; }}
        .cost-badge.high {{ background: #fed7d7; color: #c53030; }}
        .cost-badge.medium {{ background: #feebc8; color: #c05621; }}
        .cost-badge.low {{ background: #c6f6d5; color: #276749; }}
        .footer {{ text-align: center; color: rgba(255,255,255,0.8); margin-top: 30px; font-size: 13px; }}
        @media (max-width: 768px) {{
            .summary-cards {{ grid-template-columns: 1fr 1fr; }}
            .card-value {{ font-size: 22px; }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🌤️ Terraform 云成本分析报告</h1>
            <p>分析时间: {analysis_date[:19]} | 基于 terraform.tfstate 静态分析</p>
        </div>

        {self.generate_summary_cards()}

        {self.generate_cost_by_provider_chart()}

        {self.generate_cost_by_type_chart()}

        {self.generate_cost_by_region_chart()}

        {self.generate_resource_table()}

        <div class="footer">
            <p>📊 成本为估算值，实际费用以云服务商账单为准</p>
            <p>建议启用预留实例 (RI)、资源调度、标签优化等策略降低成本</p>
        </div>
    </div>
</body>
</html>"""
        return html

    def save(self, output_path: str = "cost_report.html"):
        html = self.generate_html()
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html)
        print(f"Visual report saved to {output_path}")
        return output_path


def main():
    parser = argparse.ArgumentParser(description='Generate Visual Cost Report from TFState')
    parser.add_argument('--state', required=True, help='Path to terraform.tfstate')
    parser.add_argument('--output', default='cost_report.html', help='Output HTML path')
    
    args = parser.parse_args()
    
    print(f"Analyzing {args.state}...")
    analyzer = TfstateAnalyzer(args.state)
    analyzer.analyze()
    
    report_data = {
        'summary': analyzer.get_summary(),
        'resources': [r.__dict__ for r in analyzer.resources],
    }
    
    generator = VisualReportGenerator(report_data)
    generator.save(args.output)
    
    print(f"\n✅ Report generated successfully!")
    print(f"   Total resources: {report_data['summary']['total_resources']}")
    print(f"   Estimated monthly cost: ${report_data['summary']['total_monthly_cost']:.2f}")
    print(f"\n   Open {args.output} in your browser to view the report.")


if __name__ == '__main__':
    main()
