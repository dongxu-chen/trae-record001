import json
from datetime import datetime, timedelta
from collections import defaultdict
from config import Config

class TrendAnalyzer:
    def __init__(self):
        self.history_file = Config.HISTORY_FILE
        self.history = self._load_history()
    
    def _load_history(self):
        try:
            with open(self.history_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return []
    
    def analyze_time_distribution(self):
        hourly_counts = defaultdict(int)
        daily_counts = defaultdict(int)
        weekday_counts = defaultdict(int)
        monthly_counts = defaultdict(int)
        
        for deadlock in self.history:
            ts = deadlock.get('timestamp', '')
            try:
                if isinstance(ts, str):
                    if 'T' in ts:
                        dt = datetime.fromisoformat(ts)
                    else:
                        dt = datetime.strptime(ts, '%Y-%m-%d %H:%M:%S')
                else:
                    continue
                
                hour_key = dt.strftime('%Y-%m-%d %H:00')
                day_key = dt.strftime('%Y-%m-%d')
                weekday_key = dt.strftime('%A')
                month_key = dt.strftime('%Y-%m')
                
                hourly_counts[hour_key] += 1
                daily_counts[day_key] += 1
                weekday_counts[weekday_key] += 1
                monthly_counts[month_key] += 1
                
            except Exception as e:
                print(f"解析时间错误: {e}")
                continue
        
        return {
            'hourly': dict(hourly_counts),
            'daily': dict(daily_counts),
            'weekday': dict(weekday_counts),
            'monthly': dict(monthly_counts)
        }
    
    def analyze_heatmap_data(self):
        heatmap_data = defaultdict(lambda: defaultdict(int))
        
        for deadlock in self.history:
            ts = deadlock.get('timestamp', '')
            try:
                if isinstance(ts, str):
                    if 'T' in ts:
                        dt = datetime.fromisoformat(ts)
                    else:
                        dt = datetime.strptime(ts, '%Y-%m-%d %H:%M:%S')
                else:
                    continue
                
                day_of_week = dt.weekday()
                hour = dt.hour
                
                heatmap_data[day_of_week][hour] += 1
                
            except:
                continue
        
        result = []
        day_names = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        
        for day in range(7):
            for hour in range(24):
                result.append({
                    'day': day,
                    'day_name': day_names[day],
                    'hour': hour,
                    'count': heatmap_data[day][hour]
                })
        
        return result
    
    def analyze_table_trends(self):
        table_trends = defaultdict(lambda: defaultdict(int))
        
        for deadlock in self.history:
            ts = deadlock.get('timestamp', '')
            try:
                if isinstance(ts, str):
                    if 'T' in ts:
                        dt = datetime.fromisoformat(ts)
                    else:
                        dt = datetime.strptime(ts, '%Y-%m-%d %H:%M:%S')
                else:
                    continue
                
                day_key = dt.strftime('%Y-%m-%d')
                
                tables = set()
                for txn in deadlock.get('transactions', []):
                    for hold in txn.get('holds', []):
                        table = hold.get('table')
                        if table and table != 'UNKNOWN':
                            tables.add(table)
                    waiting = txn.get('waiting_for')
                    if waiting:
                        table = waiting.get('table')
                        if table and table != 'UNKNOWN':
                            tables.add(table)
                
                for table in tables:
                    table_trends[table][day_key] += 1
                
            except:
                continue
        
        return dict(table_trends)
    
    def calculate_statistics(self):
        total = len(self.history)
        if total == 0:
            return {
                'total': 0,
                'avg_daily': 0,
                'peak_hour': None,
                'peak_day': None,
                'trend': 'stable'
            }
        
        distribution = self.analyze_time_distribution()
        
        daily = distribution['daily']
        avg_daily = sum(daily.values()) / len(daily) if daily else 0
        
        hourly = distribution['hourly']
        peak_hour = max(hourly.items(), key=lambda x: x[1])[0] if hourly else None
        
        weekday = distribution['weekday']
        peak_day = max(weekday.items(), key=lambda x: x[1])[0] if weekday else None
        
        recent_7_days = 0
        previous_7_days = 0
        now = datetime.now()
        
        for deadlock in self.history:
            ts = deadlock.get('timestamp', '')
            try:
                if isinstance(ts, str):
                    if 'T' in ts:
                        dt = datetime.fromisoformat(ts)
                    else:
                        dt = datetime.strptime(ts, '%Y-%m-%d %H:%M:%S')
                else:
                    continue
                
                days_ago = (now - dt).days
                if days_ago < 7:
                    recent_7_days += 1
                elif days_ago < 14:
                    previous_7_days += 1
            except:
                continue
        
        if previous_7_days > 0:
            change_pct = (recent_7_days - previous_7_days) / previous_7_days * 100
            if change_pct > 20:
                trend = 'increasing'
            elif change_pct < -20:
                trend = 'decreasing'
            else:
                trend = 'stable'
        else:
            trend = 'stable' if recent_7_days == 0 else 'increasing'
        
        return {
            'total': total,
            'avg_daily': round(avg_daily, 2),
            'peak_hour': peak_hour,
            'peak_day': peak_day,
            'recent_7_days': recent_7_days,
            'previous_7_days': previous_7_days,
            'trend': trend
        }
    
    def generate_trend_report(self, output_file=None):
        if not output_file:
            output_file = Config.TREND_REPORT_FILE
        
        stats = self.calculate_statistics()
        distribution = self.analyze_time_distribution()
        heatmap = self.analyze_heatmap_data()
        table_trends = self.analyze_table_trends()
        
        html_content = f"""
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>死锁趋势分析报告</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }}
        .container {{
            max-width: 1400px;
            margin: 0 auto;
            background: white;
            border-radius: 15px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            overflow: hidden;
        }}
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            text-align: center;
        }}
        .header h1 {{
            font-size: 32px;
            margin-bottom: 10px;
        }}
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            padding: 30px;
        }}
        .stat-card {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 25px;
            border-radius: 12px;
            text-align: center;
            box-shadow: 0 4px 15px rgba(102, 126, 234, 0.4);
        }}
        .stat-card.warning {{
            background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
        }}
        .stat-card.success {{
            background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
        }}
        .stat-value {{
            font-size: 36px;
            font-weight: bold;
            margin-bottom: 5px;
        }}
        .stat-label {{
            font-size: 14px;
            opacity: 0.9;
        }}
        .trend-indicator {{
            display: inline-block;
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 12px;
            margin-top: 10px;
        }}
        .trend-up {{ background: #f5576c; }}
        .trend-down {{ background: #4facfe; }}
        .trend-stable {{ background: #43e97b; }}
        
        .charts-section {{
            padding: 30px;
        }}
        .chart-row {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 30px;
            margin-bottom: 30px;
        }}
        @media (max-width: 768px) {{
            .chart-row {{
                grid-template-columns: 1fr;
            }}
        }}
        .chart-container {{
            background: #f8f9fa;
            padding: 20px;
            border-radius: 12px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        .chart-container h3 {{
            color: #2d3748;
            margin-bottom: 15px;
            font-size: 18px;
        }}
        
        .heatmap-container {{
            background: #f8f9fa;
            padding: 20px;
            border-radius: 12px;
            margin: 0 30px 30px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        .heatmap-container h3 {{
            color: #2d3748;
            margin-bottom: 20px;
        }}
        .heatmap {{
            display: grid;
            grid-template-columns: auto repeat(24, 1fr);
            gap: 2px;
        }}
        .heatmap-header {{
            display: contents;
        }}
        .heatmap-header .corner {{
            background: #e9ecef;
            border-radius: 4px 0 0 0;
        }}
        .heatmap-header .hour-label {{
            background: #e9ecef;
            padding: 5px;
            text-align: center;
            font-size: 10px;
            font-weight: bold;
            color: #495057;
        }}
        .heatmap-row {{
            display: contents;
        }}
        .day-label {{
            background: #e9ecef;
            padding: 8px 5px;
            text-align: right;
            font-size: 11px;
            font-weight: bold;
            color: #495057;
            min-width: 80px;
        }}
        .heat-cell {{
            aspect-ratio: 1;
            border-radius: 3px;
            cursor: pointer;
            transition: transform 0.2s;
            position: relative;
        }}
        .heat-cell:hover {{
            transform: scale(1.2);
            z-index: 10;
        }}
        .heat-cell .tooltip {{
            position: absolute;
            bottom: 100%;
            left: 50%;
            transform: translateX(-50%);
            background: #2d3748;
            color: white;
            padding: 5px 10px;
            border-radius: 4px;
            font-size: 12px;
            white-space: nowrap;
            opacity: 0;
            pointer-events: none;
            transition: opacity 0.2s;
        }}
        .heat-cell:hover .tooltip {{
            opacity: 1;
        }}
        
        .table-trends {{
            padding: 0 30px 30px;
        }}
        .table-trends h3 {{
            color: #2d3748;
            margin-bottom: 15px;
        }}
        .table-list {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
            gap: 15px;
        }}
        .table-item {{
            background: #f8f9fa;
            padding: 15px;
            border-radius: 8px;
            border-left: 4px solid #667eea;
        }}
        .table-name {{
            font-weight: bold;
            color: #2d3748;
            margin-bottom: 8px;
        }}
        .table-stats {{
            font-size: 13px;
            color: #718096;
        }}
        
        .footer {{
            text-align: center;
            padding: 20px;
            color: #718096;
            font-size: 13px;
            border-top: 1px solid #e9ecef;
        }}
        
        .legend {{
            display: flex;
            justify-content: center;
            gap: 20px;
            margin-top: 15px;
        }}
        .legend-item {{
            display: flex;
            align-items: center;
            gap: 5px;
            font-size: 12px;
        }}
        .legend-color {{
            width: 15px;
            height: 15px;
            border-radius: 3px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📈 死锁趋势分析报告</h1>
            <p>生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        </div>
        
        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-value">{stats['total']}</div>
                <div class="stat-label">总死锁次数</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{stats['avg_daily']}</div>
                <div class="stat-label">日均死锁数</div>
            </div>
            <div class="stat-card {'warning' if stats['trend'] == 'increasing' else 'success'}">
                <div class="stat-value">{stats['recent_7_days']}</div>
                <div class="stat-label">近7天死锁数</div>
                <span class="trend-indicator trend-{stats['trend']}">
                    {{ '上升' if stats['trend'] == 'increasing' else '下降' if stats['trend'] == 'decreasing' else '稳定' }}
                </span>
            </div>
        </div>
        
        <div class="charts-section">
            <div class="chart-row">
                <div class="chart-container">
                    <h3>📊 每日死锁趋势</h3>
                    <canvas id="dailyChart"></canvas>
                </div>
                <div class="chart-container">
                    <h3>📅 星期分布</h3>
                    <canvas id="weekdayChart"></canvas>
                </div>
            </div>
        </div>
        
        <div class="heatmap-container">
            <h3>🔥 死锁时间分布热力图 (星期 x 小时)</h3>
            <div class="heatmap" id="heatmap"></div>
            <div class="legend">
                <div class="legend-item">
                    <div class="legend-color" style="background: #e3f2fd;"></div>
                    <span>低</span>
                </div>
                <div class="legend-item">
                    <div class="legend-color" style="background: #90caf9;"></div>
                    <span>中</span>
                </div>
                <div class="legend-item">
                    <div class="legend-color" style="background: #f44336;"></div>
                    <span>高</span>
                </div>
            </div>
        </div>
        
        <div class="table-trends">
            <h3>📋 各表死锁趋势</h3>
            <div class="table-list" id="tableTrends"></div>
        </div>
        
        <div class="footer">
            数据库死锁自动诊断器 - 趋势分析报告
        </div>
    </div>
    
    <script>
        const dailyData = {json.dumps(distribution['daily'])};
        const weekdayData = {json.dumps(distribution['weekday'])};
        const heatmapData = {json.dumps(heatmap)};
        const tableTrendsData = {json.dumps(table_trends)};
        
        const dailyLabels = Object.keys(dailyData).sort().slice(-30);
        const dailyValues = dailyLabels.map(label => dailyData[label]);
        
        new Chart(document.getElementById('dailyChart'), {{
            type: 'line',
            data: {{
                labels: dailyLabels,
                datasets: [{{
                    label: '死锁次数',
                    data: dailyValues,
                    borderColor: '#667eea',
                    backgroundColor: 'rgba(102, 126, 234, 0.1)',
                    fill: true,
                    tension: 0.4
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
                        ticks: {{ stepSize: 1 }}
                    }}
                }}
            }}
        }});
        
        const weekdayOrder = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'];
        const weekdayLabelsCn = ['周一', '周二', '周三', '周四', '周五', '周六', '周日'];
        const weekdayValues = weekdayOrder.map(day => weekdayData[day] || 0);
        
        new Chart(document.getElementById('weekdayChart'), {{
            type: 'bar',
            data: {{
                labels: weekdayLabelsCn,
                datasets: [{{
                    label: '死锁次数',
                    data: weekdayValues,
                    backgroundColor: [
                        'rgba(102, 126, 234, 0.8)',
                        'rgba(118, 75, 162, 0.8)',
                        'rgba(79, 209, 197, 0.8)',
                        'rgba(250, 112, 154, 0.8)',
                        'rgba(168, 237, 234, 0.8)',
                        'rgba(254, 225, 64, 0.8)',
                        'rgba(55, 226, 119, 0.8)'
                    ],
                    borderRadius: 8
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
                        ticks: {{ stepSize: 1 }}
                    }}
                }}
            }}
        }});
        
        const maxCount = Math.max(...heatmapData.map(d => d.count), 1);
        
        function getHeatColor(count, max) {{
            if (count === 0) return '#f8f9fa';
            const ratio = count / max;
            if (ratio < 0.3) return '#e3f2fd';
            if (ratio < 0.6) return '#90caf9';
            if (ratio < 0.9) return '#f44336';
            return '#d32f2f';
        }}
        
        const heatmapContainer = document.getElementById('heatmap');
        const dayNamesCn = ['周一', '周二', '周三', '周四', '周五', '周六', '周日'];
        
        let headerHtml = '<div class="heatmap-header"><div class="corner"></div>';
        for (let h = 0; h < 24; h++) {{
            headerHtml += `<div class="hour-label">${{h}}</div>`;
        }}
        headerHtml += '</div>';
        heatmapContainer.innerHTML = headerHtml;
        
        for (let d = 0; d < 7; d++) {{
            let rowHtml = `<div class="heatmap-row"><div class="day-label">${{dayNamesCn[d]}}</div>`;
            for (let h = 0; h < 24; h++) {{
                const data = heatmapData.find(item => item.day === d && item.hour === h);
                const count = data ? data.count : 0;
                const color = getHeatColor(count, maxCount);
                rowHtml += `<div class="heat-cell" style="background: ${{color}};"><div class="tooltip">${{dayNamesCn[d]}} ${{h}}:00 - ${{count}}次</div></div>`;
            }}
            rowHtml += '</div>';
            heatmapContainer.innerHTML += rowHtml;
        }}
        
        const tableTrendsContainer = document.getElementById('tableTrends');
        Object.entries(tableTrendsData).forEach(([table, days]) => {{
            const sortedDays = Object.entries(days).sort((a, b) => b[1] - a[1]);
            const total = Object.values(days).reduce((a, b) => a + b, 0);
            const peakDay = sortedDays[0] ? sortedDays[0][0] : 'N/A';
            const peakCount = sortedDays[0] ? sortedDays[0][1] : 0;
            
            tableTrendsContainer.innerHTML += `
                <div class="table-item">
                    <div class="table-name">${{table}}</div>
                    <div class="table-stats">
                        总计: ${{total}} 次 | 峰值: ${{peakDay}} (${{peakCount}}次)
                    </div>
                </div>
            `;
        }});
        
        if (Object.keys(tableTrendsData).length === 0) {{
            tableTrendsContainer.innerHTML = '<p style="color: #718096; text-align: center;">暂无表级趋势数据</p>';
        }}
    </script>
</body>
</html>
        """
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        return output_file
    
    def get_risk_periods(self):
        heatmap = self.analyze_heatmap_data()
        max_count = max((d['count'] for d in heatmap), default=0)
        
        if max_count == 0:
            return []
        
        threshold = max_count * 0.6
        risk_periods = []
        
        for data in heatmap:
            if data['count'] >= threshold:
                risk_periods.append({
                    'day': data['day_name'],
                    'hour': data['hour'],
                    'count': data['count']
                })
        
        return sorted(risk_periods, key=lambda x: x['count'], reverse=True)
