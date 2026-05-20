import os
import json
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field, asdict
from collections import defaultdict
import numpy as np
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')
import pandas as pd
from pathlib import Path
import base64
from io import BytesIO


@dataclass
class DefectRecord:
    id: str
    image_path: str
    class_id: int
    class_name: str
    confidence: float
    bbox: Dict[str, float]
    size_mm: Optional[Tuple[float, float]] = None
    position_3d: Optional[Tuple[float, float, float]] = None
    severity: str = 'medium'
    timestamp: datetime = field(default_factory=datetime.now)
    inspection_line: str = 'line_1'
    operator: str = 'auto'
    is_manual_verified: bool = False
    manual_class: Optional[int] = None


@dataclass
class ReportConfig:
    report_title: str = "X-Ray Defect Detection Report"
    company_name: str = "Industrial Inspection Co."
    department: str = "Quality Control"
    include_charts: bool = True
    include_tables: bool = True
    include_trend_analysis: bool = True
    chart_dpi: int = 150
    language: str = 'en'


class DefectDatabase:
    def __init__(self, db_path: str = "data/defect_database.json"):
        self.db_path = db_path
        self.records: List[DefectRecord] = []
        self._load()

    def _load(self):
        if os.path.exists(self.db_path):
            try:
                with open(self.db_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                for rec in data:
                    rec['timestamp'] = datetime.fromisoformat(rec['timestamp'])
                    self.records.append(DefectRecord(**rec))
                print(f"Loaded {len(self.records)} records from database")
            except Exception as e:
                print(f"Warning: Failed to load database: {e}")
                self.records = []

    def _save(self):
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        data = []
        for rec in self.records:
            rec_dict = asdict(rec)
            rec_dict['timestamp'] = rec.timestamp.isoformat()
            data.append(rec_dict)
        with open(self.db_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def add_record(self, record: DefectRecord):
        self.records.append(record)
        self._save()

    def add_records(self, records: List[DefectRecord]):
        self.records.extend(records)
        self._save()

    def get_records_by_date(self, start_date: datetime, end_date: datetime) -> List[DefectRecord]:
        return [r for r in self.records if start_date <= r.timestamp <= end_date]

    def get_records_by_class(self, class_id: int) -> List[DefectRecord]:
        return [r for r in self.records if r.class_id == class_id]

    def get_records_by_severity(self, severity: str) -> List[DefectRecord]:
        return [r for r in self.records if r.severity == severity]

    def get_all_classes(self) -> List[int]:
        return sorted(list(set(r.class_id for r in self.records)))

    def get_all_class_names(self) -> List[str]:
        return sorted(list(set(r.class_name for r in self.records)))

    def clear(self):
        self.records = []
        self._save()

    def export_to_csv(self, csv_path: str):
        data = []
        for rec in self.records:
            rec_dict = asdict(rec)
            rec_dict['timestamp'] = rec.timestamp.isoformat()
            rec_dict['bbox_x1'] = rec.bbox.get('x1', 0)
            rec_dict['bbox_y1'] = rec.bbox.get('y1', 0)
            rec_dict['bbox_x2'] = rec.bbox.get('x2', 0)
            rec_dict['bbox_y2'] = rec.bbox.get('y2', 0)
            if rec.size_mm:
                rec_dict['width_mm'] = rec.size_mm[0]
                rec_dict['height_mm'] = rec.size_mm[1]
            if rec.position_3d:
                rec_dict['x_3d'] = rec.position_3d[0]
                rec_dict['y_3d'] = rec.position_3d[1]
                rec_dict['z_3d'] = rec.position_3d[2]
            data.append(rec_dict)

        df = pd.DataFrame(data)
        df.to_csv(csv_path, index=False, encoding='utf-8-sig')
        print(f"Exported {len(data)} records to {csv_path}")


class DefectStatistics:
    def __init__(self, records: List[DefectRecord], class_names: Dict[int, str] = None):
        self.records = records
        self.class_names = class_names or {0: 'Porosity', 1: 'Crack', 2: 'Slag Inclusion'}
        self.severity_levels = ['low', 'medium', 'high', 'critical']

    def get_total_defects(self) -> int:
        return len(self.records)

    def get_defect_count_by_class(self) -> Dict[int, int]:
        counts = defaultdict(int)
        for r in self.records:
            counts[r.class_id] += 1
        return dict(counts)

    def get_defect_count_by_class_name(self) -> Dict[str, int]:
        counts = defaultdict(int)
        for r in self.records:
            counts[r.class_name] += 1
        return dict(counts)

    def get_defect_frequency_by_class(self) -> Dict[str, float]:
        total = len(self.records)
        if total == 0:
            return {}
        counts = self.get_defect_count_by_class_name()
        return {k: v / total for k, v in counts.items()}

    def get_defect_count_by_severity(self) -> Dict[str, int]:
        counts = defaultdict(int)
        for r in self.records:
            counts[r.severity] += 1
        return dict(counts)

    def get_daily_trend(self, days: int = 30) -> Dict[str, int]:
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)

        daily_counts = defaultdict(int)
        for r in self.records:
            if start_date <= r.timestamp <= end_date:
                date_key = r.timestamp.strftime('%Y-%m-%d')
                daily_counts[date_key] += 1

        return dict(sorted(daily_counts.items()))

    def get_weekly_trend(self, weeks: int = 12) -> Dict[str, int]:
        end_date = datetime.now()
        start_date = end_date - timedelta(weeks=weeks)

        weekly_counts = defaultdict(int)
        for r in self.records:
            if start_date <= r.timestamp <= end_date:
                week_key = r.timestamp.strftime('%Y-W%W')
                weekly_counts[week_key] += 1

        return dict(sorted(weekly_counts.items()))

    def get_class_trend(self, days: int = 30) -> Dict[str, Dict[str, int]]:
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)

        trend_data = defaultdict(lambda: defaultdict(int))
        for r in self.records:
            if start_date <= r.timestamp <= end_date:
                date_key = r.timestamp.strftime('%Y-%m-%d')
                trend_data[r.class_name][date_key] += 1

        result = {}
        for class_name, daily_data in trend_data.items():
            result[class_name] = dict(sorted(daily_data.items()))
        return result

    def get_avg_confidence_by_class(self) -> Dict[str, float]:
        confidences = defaultdict(list)
        for r in self.records:
            confidences[r.class_name].append(r.confidence)
        return {k: float(np.mean(v)) for k, v in confidences.items()}

    def get_defect_size_stats(self) -> Dict[str, Dict[str, float]]:
        sizes = defaultdict(list)
        for r in self.records:
            if r.size_mm:
                area = r.size_mm[0] * r.size_mm[1]
                sizes[r.class_name].append(area)

        result = {}
        for class_name, areas in sizes.items():
            if areas:
                result[class_name] = {
                    'mean_area': float(np.mean(areas)),
                    'median_area': float(np.median(areas)),
                    'max_area': float(np.max(areas)),
                    'min_area': float(np.min(areas)),
                    'std_area': float(np.std(areas)),
                    'count': len(areas)
                }
        return result

    def get_inspection_line_stats(self) -> Dict[str, int]:
        counts = defaultdict(int)
        for r in self.records:
            counts[r.inspection_line] += 1
        return dict(counts)

    def get_verification_rate(self) -> float:
        if not self.records:
            return 0.0
        verified = sum(1 for r in self.records if r.is_manual_verified)
        return verified / len(self.records)

    def calculate_defect_rate(self, total_inspections: int) -> float:
        if total_inspections == 0:
            return 0.0
        return len(self.records) / total_inspections


class ChartGenerator:
    def __init__(self, statistics: DefectStatistics, dpi: int = 150):
        self.stats = statistics
        self.dpi = dpi
        self.class_colors = {
            'Porosity': '#2ecc71',
            'Crack': '#e74c3c',
            'Slag Inclusion': '#3498db'
        }

    def _fig_to_base64(self, fig) -> str:
        buf = BytesIO()
        fig.savefig(buf, format='png', dpi=self.dpi, bbox_inches='tight')
        buf.seek(0)
        img_base64 = base64.b64encode(buf.read()).decode('utf-8')
        plt.close(fig)
        return img_base64

    def create_class_distribution_chart(self) -> str:
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))

        counts = self.stats.get_defect_count_by_class_name()
        if counts:
            classes = list(counts.keys())
            values = list(counts.values())
            colors = [self.class_colors.get(c, '#95a5a6') for c in classes]

            ax1.bar(classes, values, color=colors, alpha=0.8, edgecolor='black')
            ax1.set_title('Defect Count by Type', fontsize=12, fontweight='bold')
            ax1.set_ylabel('Number of Defects')
            for i, v in enumerate(values):
                ax1.text(i, v + max(values) * 0.02, str(v), ha='center', fontweight='bold')

            ax2.pie(values, labels=classes, colors=colors, autopct='%1.1f%%',
                     startangle=90, textprops={'fontsize': 10})
            ax2.set_title('Defect Distribution', fontsize=12, fontweight='bold')

        plt.tight_layout()
        return self._fig_to_base64(fig)

    def create_severity_distribution_chart(self) -> str:
        fig, ax = plt.subplots(figsize=(8, 5))

        counts = self.stats.get_defect_count_by_severity()
        if counts:
            severities = ['low', 'medium', 'high', 'critical']
            colors = ['#2ecc71', '#f1c40f', '#e67e22', '#e74c3c']
            values = [counts.get(s, 0) for s in severities]

            bars = ax.bar(severities, values, color=colors, alpha=0.8, edgecolor='black')
            ax.set_title('Defect Distribution by Severity', fontsize=12, fontweight='bold')
            ax.set_xlabel('Severity Level')
            ax.set_ylabel('Number of Defects')

            for bar, v in zip(bars, values):
                if v > 0:
                    ax.text(bar.get_x() + bar.get_width() / 2, v + max(values) * 0.02,
                            str(v), ha='center', fontweight='bold')

        plt.tight_layout()
        return self._fig_to_base64(fig)

    def create_daily_trend_chart(self, days: int = 30) -> str:
        fig, ax = plt.subplots(figsize=(12, 5))

        daily_counts = self.stats.get_daily_trend(days=days)
        if daily_counts:
            dates = list(daily_counts.keys())
            counts = list(daily_counts.values())

            ax.plot(dates, counts, marker='o', linewidth=2, markersize=6,
                    color='#3498db', markerfacecolor='#2980b9')
            ax.fill_between(dates, counts, alpha=0.2, color='#3498db')

            ax.set_title(f'Daily Defect Trend (Last {days} Days)', fontsize=12, fontweight='bold')
            ax.set_xlabel('Date')
            ax.set_ylabel('Number of Defects')
            ax.grid(True, alpha=0.3)
            plt.xticks(rotation=45, ha='right')

            z = np.polyfit(range(len(counts)), counts, 1)
            p = np.poly1d(z)
            ax.plot(dates, p(range(len(counts))), "--", color='#e74c3c', alpha=0.7,
                    label=f'Trend: {z[0]:.2f} per day')
            ax.legend()

        plt.tight_layout()
        return self._fig_to_base64(fig)

    def create_class_trend_chart(self, days: int = 30) -> str:
        fig, ax = plt.subplots(figsize=(12, 6))

        class_trend = self.stats.get_class_trend(days=days)
        if class_trend:
            for class_name, daily_data in class_trend.items():
                if daily_data:
                    dates = list(daily_data.keys())
                    counts = list(daily_data.values())
                    color = self.class_colors.get(class_name, '#95a5a6')
                    ax.plot(dates, counts, marker='o', linewidth=2, markersize=5,
                            color=color, label=class_name)

            ax.set_title(f'Defect Trend by Type (Last {days} Days)', fontsize=12, fontweight='bold')
            ax.set_xlabel('Date')
            ax.set_ylabel('Number of Defects')
            ax.grid(True, alpha=0.3)
            ax.legend(loc='upper right')
            plt.xticks(rotation=45, ha='right')

        plt.tight_layout()
        return self._fig_to_base64(fig)

    def create_confidence_distribution_chart(self) -> str:
        fig, ax = plt.subplots(figsize=(8, 5))

        confidences_by_class = defaultdict(list)
        for r in self.stats.records:
            confidences_by_class[r.class_name].append(r.confidence)

        if confidences_by_class:
            data = []
            labels = []
            colors = []
            for class_name, confs in confidences_by_class.items():
                data.append(confs)
                labels.append(class_name)
                colors.append(self.class_colors.get(class_name, '#95a5a6'))

            bp = ax.boxplot(data, labels=labels, patch_artist=True, vert=True)
            for patch, color in zip(bp['boxes'], colors):
                patch.set_facecolor(color)
                patch.set_alpha(0.7)
            for element in ['whiskers', 'caps', 'medians']:
                plt.setp(bp[element], color='#2c3e50', linewidth=1.5)

            ax.set_title('Detection Confidence Distribution by Defect Type',
                          fontsize=12, fontweight='bold')
            ax.set_ylabel('Confidence Score')
            ax.set_ylim(0, 1.1)
            ax.grid(True, alpha=0.3, axis='y')

        plt.tight_layout()
        return self._fig_to_base64(fig)

    def create_size_distribution_chart(self) -> str:
        fig, ax = plt.subplots(figsize=(10, 6))

        size_stats = self.stats.get_defect_size_stats()
        if size_stats:
            classes = list(size_stats.keys())
            mean_areas = [size_stats[c]['mean_area'] for c in classes]
            std_areas = [size_stats[c]['std_area'] for c in classes]
            colors = [self.class_colors.get(c, '#95a5a6') for c in classes]

            bars = ax.bar(classes, mean_areas, yerr=std_areas, capsize=10,
                          color=colors, alpha=0.8, edgecolor='black')
            ax.set_title('Average Defect Size by Type', fontsize=12, fontweight='bold')
            ax.set_xlabel('Defect Type')
            ax.set_ylabel('Mean Area (mm²)')
            ax.grid(True, alpha=0.3, axis='y')

            for bar, stats in zip(bars, size_stats.values()):
                ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() * 1.02,
                        f"n={stats['count']}", ha='center', fontsize=9,
                        fontweight='bold')

        plt.tight_layout()
        return self._fig_to_base64(fig)


class ReportGenerator:
    def __init__(self, config: ReportConfig = None):
        self.config = config or ReportConfig()

    def _generate_html_header(self) -> str:
        return f"""
<!DOCTYPE html>
<html lang="{self.config.language}">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{self.config.report_title}</title>
    <style>
        body {{
            font-family: 'Segoe UI', Arial, sans-serif;
            margin: 0;
            padding: 20px;
            background-color: #f5f6fa;
            color: #2c3e50;
        }}
        .header {{
            background: linear-gradient(135deg, #2c3e50, #34495e);
            color: white;
            padding: 30px;
            border-radius: 10px;
            margin-bottom: 20px;
        }}
        .header h1 {{
            margin: 0;
            font-size: 28px;
        }}
        .header .subinfo {{
            opacity: 0.9;
            margin-top: 10px;
            font-size: 14px;
        }}
        .summary-cards {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin-bottom: 25px;
        }}
        .card {{
            background: white;
            padding: 20px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            text-align: center;
        }}
        .card .value {{
            font-size: 32px;
            font-weight: bold;
            color: #3498db;
        }}
        .card .label {{
            font-size: 14px;
            color: #7f8c8d;
            margin-top: 5px;
        }}
        .card.green .value {{ color: #27ae60; }}
        .card.red .value {{ color: #e74c3c; }}
        .card.orange .value {{ color: #e67e22; }}
        .section {{
            background: white;
            padding: 25px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            margin-bottom: 20px;
        }}
        .section h2 {{
            color: #2c3e50;
            border-bottom: 3px solid #3498db;
            padding-bottom: 10px;
            margin-top: 0;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 15px;
        }}
        th, td {{
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #ecf0f1;
        }}
        th {{
            background-color: #34495e;
            color: white;
            font-weight: bold;
        }}
        tr:hover {{
            background-color: #f8f9fa;
        }}
        .chart-container {{
            text-align: center;
            margin: 20px 0;
        }}
        .chart-container img {{
            max-width: 100%;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        .trend-up {{ color: #e74c3c; font-weight: bold; }}
        .trend-down {{ color: #27ae60; font-weight: bold; }}
        .trend-stable {{ color: #f39c12; font-weight: bold; }}
        .footer {{
            text-align: center;
            margin-top: 30px;
            padding: 20px;
            color: #7f8c8d;
            font-size: 12px;
            border-top: 1px solid #ecf0f1;
        }}
        .severity-low {{ color: #27ae60; font-weight: bold; }}
        .severity-medium {{ color: #f39c12; font-weight: bold; }}
        .severity-high {{ color: #e67e22; font-weight: bold; }}
        .severity-critical {{ color: #e74c3c; font-weight: bold; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>{self.config.report_title}</h1>
        <div class="subinfo">
            <strong>{self.config.company_name}</strong> | {self.config.department} | 
            Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        </div>
    </div>
"""

    def _generate_html_footer(self) -> str:
        return f"""
    <div class="footer">
        <p>{self.config.report_title} | © {datetime.now().year} {self.config.company_name}</p>
        <p>Generated by X-Ray Defect Detection System</p>
    </div>
</body>
</html>
"""

    def _generate_summary_cards(self, stats: DefectStatistics, time_period: str) -> str:
        total_defects = stats.get_total_defects()
        class_counts = stats.get_defect_count_by_class_name()
        severity_counts = stats.get_defect_count_by_severity()
        verification_rate = stats.get_verification_rate()

        critical_count = severity_counts.get('critical', 0)
        high_count = severity_counts.get('high', 0)

        trend = "stable"
        daily = stats.get_daily_trend(7)
        if len(daily) >= 2:
            vals = list(daily.values())
            recent = vals[-3:]
            earlier = vals[:-3]
            if len(earlier) > 0 and len(recent) > 0:
                if np.mean(recent) > np.mean(earlier) * 1.1:
                    trend = "up"
                elif np.mean(recent) < np.mean(earlier) * 0.9:
                    trend = "down"

        trend_class = {"up": "trend-up", "down": "trend-down", "stable": "trend-stable"}[trend]
        trend_text = {"up": "↑ Rising", "down": "↓ Falling", "stable": "→ Stable"}[trend]

        cards = f"""
    <div class="summary-cards">
        <div class="card">
            <div class="value">{total_defects}</div>
            <div class="label">Total Defects ({time_period})</div>
        </div>
        <div class="card red">
            <div class="value">{critical_count + high_count}</div>
            <div class="label">High/Critical Defects</div>
        </div>
        <div class="card orange">
            <div class="value">{len(class_counts)}</div>
            <div class="label">Defect Types</div>
        </div>
        <div class="card green">
            <div class="value">{verification_rate * 100:.1f}%</div>
            <div class="label">Manual Verification Rate</div>
        </div>
        <div class="card">
            <div class="value {trend_class}">{trend_text}</div>
            <div class="label">Weekly Trend</div>
        </div>
    </div>
"""
        return cards

    def _generate_class_statistics_table(self, stats: DefectStatistics) -> str:
        class_counts = stats.get_defect_count_by_class_name()
        class_freq = stats.get_defect_frequency_by_class()
        avg_conf = stats.get_avg_confidence_by_class()
        size_stats = stats.get_defect_size_stats()

        if not class_counts:
            return ""

        table = """
        <table>
            <thead>
                <tr>
                    <th>Defect Type</th>
                    <th>Count</th>
                    <th>Frequency</th>
                    <th>Avg. Confidence</th>
                    <th>Avg. Size (mm²)</th>
                    <th>Max Size (mm²)</th>
                </tr>
            </thead>
            <tbody>
"""

        class_colors = {
            'Porosity': 'background-color: rgba(46, 204, 113, 0.1)',
            'Crack': 'background-color: rgba(231, 76, 60, 0.1)',
            'Slag Inclusion': 'background-color: rgba(52, 152, 219, 0.1)'
        }

        for class_name, count in sorted(class_counts.items(), key=lambda x: -x[1]):
            freq = class_freq.get(class_name, 0)
            conf = avg_conf.get(class_name, 0)
            size_data = size_stats.get(class_name, {})
            avg_size = size_data.get('mean_area', 0)
            max_size = size_data.get('max_area', 0)
            bg_color = class_colors.get(class_name, '')

            table += f"""
                <tr style="{bg_color}">
                    <td><strong>{class_name}</strong></td>
                    <td>{count}</td>
                    <td>{freq * 100:.1f}%</td>
                    <td>{conf:.3f}</td>
                    <td>{avg_size:.2f}</td>
                    <td>{max_size:.2f}</td>
                </tr>
"""

        table += """
            </tbody>
        </table>
"""
        return table

    def _generate_severity_table(self, stats: DefectStatistics) -> str:
        severity_counts = stats.get_defect_count_by_severity()
        if not severity_counts:
            return ""

        total = sum(severity_counts.values())
        severities = ['critical', 'high', 'medium', 'low']

        table = """
        <table>
            <thead>
                <tr>
                    <th>Severity</th>
                    <th>Count</th>
                    <th>Percentage</th>
                    <th>Recommended Action</th>
                </tr>
            </thead>
            <tbody>
"""

        severity_info = {
            'critical': {'class': 'severity-critical', 'action': 'Immediate recall & repair'},
            'high': {'class': 'severity-high', 'action': 'Enhanced inspection required'},
            'medium': {'class': 'severity-medium', 'action': 'Monitor production process'},
            'low': {'class': 'severity-low', 'action': 'Routine monitoring'}
        }

        for sev in severities:
            count = severity_counts.get(sev, 0)
            if count > 0:
                pct = count / total * 100 if total > 0 else 0
                info = severity_info[sev]
                table += f"""
                <tr>
                    <td><span class="{info['class']}">{sev.upper()}</span></td>
                    <td>{count}</td>
                    <td>{pct:.1f}%</td>
                    <td>{info['action']}</td>
                </tr>
"""

        table += """
            </tbody>
        </table>
"""
        return table

    def _generate_recent_defects_table(self, records: List[DefectRecord], limit: int = 20) -> str:
        if not records:
            return ""

        sorted_records = sorted(records, key=lambda r: r.timestamp, reverse=True)[:limit]

        table = f"""
        <table>
            <thead>
                <tr>
                    <th>Time</th>
                    <th>Image</th>
                    <th>Defect Type</th>
                    <th>Confidence</th>
                    <th>Severity</th>
                    <th>Size (mm)</th>
                    <th>Verified</th>
                </tr>
            </thead>
            <tbody>
"""

        for rec in sorted_records:
            severity_class = f"severity-{rec.severity}"
            size_str = f"{rec.size_mm[0]:.1f} x {rec.size_mm[1]:.1f}" if rec.size_mm else "-"
            verified = "✓" if rec.is_manual_verified else "✗"

            table += f"""
                <tr>
                    <td>{rec.timestamp.strftime('%Y-%m-%d %H:%M:%S')}</td>
                    <td>{Path(rec.image_path).name}</td>
                    <td>{rec.class_name}</td>
                    <td>{rec.confidence:.3f}</td>
                    <td><span class="{severity_class}">{rec.severity}</span></td>
                    <td>{size_str}</td>
                    <td>{verified}</td>
                </tr>
"""

        table += """
            </tbody>
        </table>
"""
        return table

    def generate_html_report(self, records: List[DefectRecord],
                             output_path: str,
                             time_period_days: int = 30) -> str:
        stats = DefectStatistics(records)
        charts = ChartGenerator(stats, dpi=self.config.chart_dpi)

        end_date = datetime.now()
        start_date = end_date - timedelta(days=time_period_days)
        period_label = f"{start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}"

        html_content = self._generate_html_header()
        html_content += self._generate_summary_cards(stats, period_label)

        if self.config.include_charts:
            html_content += """
    <div class="section">
        <h2>Defect Distribution Analysis</h2>
        <div class="chart-container">
            <img src="data:image/png;base64,{}" alt="Class Distribution">
        </div>
        <div class="chart-container">
            <img src="data:image/png;base64,{}" alt="Severity Distribution">
        </div>
    </div>
""".format(charts.create_class_distribution_chart(),
           charts.create_severity_distribution_chart())

        if self.config.include_tables:
            html_content += """
    <div class="section">
        <h2>Defect Statistics Summary</h2>
{}
    </div>
""".format(self._generate_class_statistics_table(stats))

            html_content += """
    <div class="section">
        <h2>Severity Analysis</h2>
{}
    </div>
""".format(self._generate_severity_table(stats))

        if self.config.include_trend_analysis:
            html_content += """
    <div class="section">
        <h2>Trend Analysis</h2>
        <div class="chart-container">
            <img src="data:image/png;base64,{}" alt="Daily Trend">
        </div>
        <div class="chart-container">
            <img src="data:image/png;base64,{}" alt="Class Trend">
        </div>
    </div>
""".format(charts.create_daily_trend_chart(time_period_days),
           charts.create_class_trend_chart(time_period_days))

            html_content += """
    <div class="section">
        <h2>Detection Quality Analysis</h2>
        <div class="chart-container">
            <img src="data:image/png;base64,{}" alt="Confidence Distribution">
        </div>
        <div class="chart-container">
            <img src="data:image/png;base64,{}" alt="Size Distribution">
        </div>
    </div>
""".format(charts.create_confidence_distribution_chart(),
           charts.create_size_distribution_chart())

        html_content += """
    <div class="section">
        <h2>Recent Defects</h2>
{}
    </div>
""".format(self._generate_recent_defects_table(records))

        html_content += self._generate_html_footer()

        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html_content)

        print(f"HTML report generated: {output_path}")
        return output_path


class DefectReportSystem:
    def __init__(self, db_path: str = "data/defect_database.json"):
        self.db = DefectDatabase(db_path)

    def add_detection_results(self, image_path: str, detections: List[Dict[str, Any]],
                               inspection_line: str = 'line_1',
                               operator: str = 'auto') -> List[DefectRecord]:
        records = []
        for det in detections:
            severity = self._calculate_severity(det)
            record = DefectRecord(
                id=f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{det['class_id']}_{len(records)}",
                image_path=image_path,
                class_id=det['class_id'],
                class_name=det['class_name'],
                confidence=det['confidence'],
                bbox=det['bbox'],
                size_mm=det.get('size_mm'),
                position_3d=det.get('position_3d'),
                severity=severity,
                inspection_line=inspection_line,
                operator=operator
            )
            records.append(record)

        self.db.add_records(records)
        return records

    def _calculate_severity(self, detection: Dict[str, Any]) -> str:
        size_mm = detection.get('size_mm')
        conf = detection['confidence']

        if size_mm:
            area = size_mm[0] * size_mm[1]
            if area > 100 or conf > 0.95:
                return 'critical'
            elif area > 50 or conf > 0.85:
                return 'high'
            elif area > 10 or conf > 0.6:
                return 'medium'
            else:
                return 'low'
        else:
            if conf > 0.95:
                return 'high'
            elif conf > 0.7:
                return 'medium'
            else:
                return 'low'

    def generate_report(self, output_dir: str = "reports",
                        time_period_days: int = 30,
                        report_format: str = 'html') -> str:
        end_date = datetime.now()
        start_date = end_date - timedelta(days=time_period_days)
        records = self.db.get_records_by_date(start_date, end_date)

        if not records:
            print("No records found for the specified time period.")
            return ""

        os.makedirs(output_dir, exist_ok=True)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

        if report_format == 'html':
            output_path = os.path.join(output_dir, f"defect_report_{timestamp}.html")
            config = ReportConfig(include_charts=True, include_tables=True,
                                   include_trend_analysis=True)
            generator = ReportGenerator(config)
            return generator.generate_html_report(records, output_path, time_period_days)

        elif report_format == 'csv':
            output_path = os.path.join(output_dir, f"defect_report_{timestamp}.csv")
            self.db.export_to_csv(output_path)
            return output_path

        else:
            raise ValueError(f"Unsupported report format: {report_format}")

    def get_summary_statistics(self, days: int = 30) -> Dict[str, Any]:
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        records = self.db.get_records_by_date(start_date, end_date)
        stats = DefectStatistics(records)

        return {
            'period_days': days,
            'total_defects': stats.get_total_defects(),
            'defect_counts_by_class': stats.get_defect_count_by_class_name(),
            'defect_frequencies': stats.get_defect_frequency_by_class(),
            'severity_counts': stats.get_defect_count_by_severity(),
            'avg_confidence': stats.get_avg_confidence_by_class(),
            'verification_rate': stats.get_verification_rate(),
            'daily_trend': stats.get_daily_trend(days),
            'class_trend': stats.get_class_trend(days)
        }

    def print_summary(self, days: int = 30):
        summary = self.get_summary_statistics(days)

        print("\n" + "=" * 60)
        print("DEFECT STATISTICS SUMMARY")
        print(f"Period: Last {days} days")
        print("=" * 60)

        print(f"\nTotal Defects: {summary['total_defects']}")

        print("\nDefect Counts by Type:")
        for class_name, count in sorted(summary['defect_counts_by_class'].items(),
                                          key=lambda x: -x[1]):
            freq = summary['defect_frequencies'].get(class_name, 0) * 100
            print(f"  {class_name:20s}: {count:5d} ({freq:5.1f}%)")

        print("\nSeverity Distribution:")
        for sev in ['critical', 'high', 'medium', 'low']:
            count = summary['severity_counts'].get(sev, 0)
            if count > 0:
                print(f"  {sev:10s}: {count}")

        print(f"\nManual Verification Rate: {summary['verification_rate'] * 100:.1f}%")

        print("\nAverage Detection Confidence:")
        for class_name, conf in summary['avg_confidence'].items():
            print(f"  {class_name:20s}: {conf:.3f}")

        print("\n" + "=" * 60 + "\n")
