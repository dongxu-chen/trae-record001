"""漏洞趋势仪表盘模块"""

import json
import os
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class TrendDataPoint:
    """趋势数据点"""
    date: str
    total_vulnerabilities: int = 0
    by_language: Dict[str, int] = field(default_factory=dict)
    by_type: Dict[str, int] = field(default_factory=dict)
    by_severity: Dict[str, int] = field(default_factory=dict)
    auto_fixable: int = 0
    non_auto_fixable: int = 0


@dataclass
class DashboardReport:
    """仪表盘报告"""
    generated_at: str
    current: TrendDataPoint
    trend: List[TrendDataPoint] = field(default_factory=list)
    summary: Dict[str, Any] = field(default_factory=dict)


class TrendTracker:
    """漏洞趋势跟踪器"""

    def __init__(self, data_dir: str = ".security_fixer"):
        self.data_dir = Path(data_dir)
        self.history_file = self.data_dir / "scan_history.json"
        self.data_dir.mkdir(parents=True, exist_ok=True)

    def record_scan(self, scan_results: List) -> TrendDataPoint:
        """记录扫描结果"""
        today = datetime.now().strftime("%Y-%m-%d")
        data_point = TrendDataPoint(date=today)

        history = self._load_history()

        for result in scan_results:
            if hasattr(result, 'vulnerabilities'):
                for vuln in result.vulnerabilities:
                    data_point.total_vulnerabilities += 1

                    lang = self._detect_language(result.file_path)
                    data_point.by_language[lang] = data_point.by_language.get(lang, 0) + 1

                    vuln_type = vuln.vuln_type.value if hasattr(vuln.vuln_type, 'value') else str(vuln.vuln_type)
                    data_point.by_type[vuln_type] = data_point.by_type.get(vuln_type, 0) + 1

                    severity = vuln.severity.value if hasattr(vuln.severity, 'value') else str(vuln.severity)
                    data_point.by_severity[severity] = data_point.by_severity.get(severity, 0) + 1

                    if vuln.auto_fixable:
                        data_point.auto_fixable += 1
                    else:
                        data_point.non_auto_fixable += 1

        history["scans"].append({
            "date": today,
            "data": self._serialize_datapoint(data_point)
        })

        self._save_history(history)

        return data_point

    def _detect_language(self, file_path: str) -> str:
        """根据文件扩展名检测语言"""
        ext = Path(file_path).suffix.lower()
        if ext == ".py":
            return "python"
        elif ext == ".java":
            return "java"
        elif ext in (".js", ".jsx", ".ts", ".tsx"):
            return "javascript"
        else:
            return "unknown"

    def _serialize_datapoint(self, dp: TrendDataPoint) -> Dict:
        """序列化数据点"""
        return {
            "date": dp.date,
            "total_vulnerabilities": dp.total_vulnerabilities,
            "by_language": dp.by_language,
            "by_type": dp.by_type,
            "by_severity": dp.by_severity,
            "auto_fixable": dp.auto_fixable,
            "non_auto_fixable": dp.non_auto_fixable,
        }

    def _deserialize_datapoint(self, data: Dict) -> TrendDataPoint:
        """反序列化数据点"""
        return TrendDataPoint(
            date=data.get("date", ""),
            total_vulnerabilities=data.get("total_vulnerabilities", 0),
            by_language=data.get("by_language", {}),
            by_type=data.get("by_type", {}),
            by_severity=data.get("by_severity", {}),
            auto_fixable=data.get("auto_fixable", 0),
            non_auto_fixable=data.get("non_auto_fixable", 0),
        )

    def _load_history(self) -> Dict:
        """加载历史数据"""
        if self.history_file.exists():
            try:
                return json.loads(self.history_file.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, IOError):
                pass
        return {"scans": []}

    def _save_history(self, history: Dict):
        """保存历史数据"""
        self.history_file.write_text(json.dumps(history, indent=2), encoding="utf-8")

    def get_trend(self, days: int = 30) -> List[TrendDataPoint]:
        """获取趋势数据"""
        history = self._load_history()
        trend = []

        cutoff_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")

        for scan in history.get("scans", []):
            if scan["date"] >= cutoff_date:
                trend.append(self._deserialize_datapoint(scan["data"]))

        return trend

    def get_dashboard_report(self, current_scan_results: List = None) -> DashboardReport:
        """生成仪表盘报告"""
        current = TrendDataPoint(date=datetime.now().strftime("%Y-%m-%d"))

        if current_scan_results:
            current = self.record_scan(current_scan_results)

        trend = self.get_trend(days=30)

        summary = {
            "current_total": current.total_vulnerabilities,
            "current_auto_fixable": current.auto_fixable,
            "current_non_auto_fixable": current.non_auto_fixable,
            "languages_analyzed": list(current.by_language.keys()),
            "vulnerability_types": list(current.by_type.keys()),
            "history_points": len(trend),
        }

        if len(trend) > 1:
            first = trend[0].total_vulnerabilities
            last = trend[-1].total_vulnerabilities
            summary["trend_direction"] = "improving" if last < first else "worsening" if last > first else "stable"
            summary["trend_change"] = last - first

        return DashboardReport(
            generated_at=datetime.now().isoformat(),
            current=current,
            trend=trend,
            summary=summary
        )


class DashboardGenerator:
    """仪表盘报告生成器"""

    def __init__(self, data_dir: str = ".security_fixer"):
        self.tracker = TrendTracker(data_dir)

    def generate_text_report(self, scan_results: List = None) -> str:
        """生成文本格式的仪表盘报告"""
        report = self.tracker.get_dashboard_report(scan_results)

        lines = []
        lines.append("=" * 70)
        lines.append("🔒 安全漏洞趋势仪表盘")
        lines.append("=" * 70)
        lines.append(f"📅 生成时间: {report.generated_at}")
        lines.append("")

        lines.append("📊 当前状态:")
        lines.append(f"  漏洞总数: {report.current.total_vulnerabilities}")
        lines.append(f"  可自动修复: {report.current.auto_fixable}")
        lines.append(f"  需人工修复: {report.current.non_auto_fixable}")
        lines.append("")

        lines.append("📈 按语言分布:")
        for lang, count in sorted(report.current.by_language.items(), key=lambda x: -x[1]):
            bar = "█" * min(count, 20)
            lines.append(f"  {lang:12} {bar} {count}")
        lines.append("")

        lines.append("📈 按漏洞类型分布:")
        for vtype, count in sorted(report.current.by_type.items(), key=lambda x: -x[1]):
            bar = "█" * min(count, 20)
            lines.append(f"  {vtype:20} {bar} {count}")
        lines.append("")

        lines.append("📈 按严重程度分布:")
        for sev, count in sorted(report.current.by_severity.items(), key=lambda x: -x[1]):
            bar = "█" * min(count, 20)
            lines.append(f"  {sev:12} {bar} {count}")
        lines.append("")

        if report.trend:
            lines.append("📉 历史趋势 (最近30天):")
            for dp in report.trend[-10:]:
                lines.append(f"  {dp.date}: {dp.total_vulnerabilities} 个漏洞")
            lines.append("")

        lines.append("📋 汇总:")
        for key, value in report.summary.items():
            lines.append(f"  {key}: {value}")

        lines.append("=" * 70)

        return "\n".join(lines)

    def generate_html_report(self, scan_results: List = None, output_path: str = "dashboard.html") -> str:
        """生成HTML格式的仪表盘报告"""
        report = self.tracker.get_dashboard_report(scan_results)

        html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>安全漏洞趋势仪表盘</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #1a1a2e; color: #eee; padding: 20px; }}
        .container {{ max-width: 1200px; margin: 0 auto; }}
        h1 {{ color: #00d9ff; margin-bottom: 20px; }}
        .stats {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; margin-bottom: 30px; }}
        .stat-card {{ background: #16213e; padding: 20px; border-radius: 10px; border-left: 4px solid #00d9ff; }}
        .stat-card.critical {{ border-color: #ff4757; }}
        .stat-card.warning {{ border-color: #ffa502; }}
        .stat-card.success {{ border-color: #2ed573; }}
        .stat-number {{ font-size: 2em; font-weight: bold; color: #00d9ff; }}
        .stat-label {{ color: #888; font-size: 0.9em; }}
        .chart-section {{ background: #16213e; padding: 20px; border-radius: 10px; margin-bottom: 20px; }}
        .chart-title {{ color: #00d9ff; margin-bottom: 15px; }}
        .bar-chart {{ display: flex; flex-direction: column; gap: 10px; }}
        .bar-row {{ display: flex; align-items: center; gap: 10px; }}
        .bar-label {{ width: 120px; font-size: 0.9em; }}
        .bar-container {{ flex: 1; height: 20px; background: #0f3460; border-radius: 10px; overflow: hidden; }}
        .bar {{ height: 100%; background: linear-gradient(90deg, #00d9ff, #0099cc); transition: width 0.5s; }}
        .bar-value {{ width: 50px; text-align: right; font-weight: bold; }}
        .trend-table {{ width: 100%; border-collapse: collapse; }}
        .trend-table th, .trend-table td {{ padding: 10px; text-align: left; border-bottom: 1px solid #333; }}
        .trend-table th {{ color: #00d9ff; }}
        .footer {{ text-align: center; color: #666; margin-top: 30px; font-size: 0.9em; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🔒 安全漏洞趋势仪表盘</h1>
        <p style="color: #888; margin-bottom: 20px;">生成时间: {report.generated_at}</p>

        <div class="stats">
            <div class="stat-card critical">
                <div class="stat-number">{report.current.total_vulnerabilities}</div>
                <div class="stat-label">漏洞总数</div>
            </div>
            <div class="stat-card success">
                <div class="stat-number">{report.current.auto_fixable}</div>
                <div class="stat-label">可自动修复</div>
            </div>
            <div class="stat-card warning">
                <div class="stat-number">{report.current.non_auto_fixable}</div>
                <div class="stat-label">需人工修复</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">{len(report.current.by_language)}</div>
                <div class="stat-label">涉及语言</div>
            </div>
        </div>

        <div class="chart-section">
            <h2 class="chart-title">📈 按语言分布</h2>
            <div class="bar-chart">
"""

        max_count = max(report.current.by_language.values()) if report.current.by_language else 1
        for lang, count in sorted(report.current.by_language.items(), key=lambda x: -x[1]):
            percentage = (count / max_count) * 100
            html += f"""
                <div class="bar-row">
                    <span class="bar-label">{lang}</span>
                    <div class="bar-container"><div class="bar" style="width: {percentage}%"></div></div>
                    <span class="bar-value">{count}</span>
                </div>"""

        html += """
            </div>
        </div>

        <div class="chart-section">
            <h2 class="chart-title">📈 按漏洞类型分布</h2>
            <div class="bar-chart">
"""

        max_type = max(report.current.by_type.values()) if report.current.by_type else 1
        for vtype, count in sorted(report.current.by_type.items(), key=lambda x: -x[1]):
            percentage = (count / max_type) * 100
            html += f"""
                <div class="bar-row">
                    <span class="bar-label">{vtype}</span>
                    <div class="bar-container"><div class="bar" style="width: {percentage}%"></div></div>
                    <span class="bar-value">{count}</span>
                </div>"""

        html += """
            </div>
        </div>

        <div class="chart-section">
            <h2 class="chart-title">📈 按严重程度分布</h2>
            <div class="bar-chart">
"""

        max_sev = max(report.current.by_severity.values()) if report.current.by_severity else 1
        for sev, count in sorted(report.current.by_severity.items(), key=lambda x: -x[1]):
            percentage = (count / max_sev) * 100
            html += f"""
                <div class="bar-row">
                    <span class="bar-label">{sev}</span>
                    <div class="bar-container"><div class="bar" style="width: {percentage}%"></div></div>
                    <span class="bar-value">{count}</span>
                </div>"""

        html += """
            </div>
        </div>
"""

        if report.trend:
            html += """
        <div class="chart-section">
            <h2 class="chart-title">📉 历史趋势</h2>
            <table class="trend-table">
                <tr><th>日期</th><th>漏洞总数</th><th>可自动修复</th><th>需人工修复</th></tr>
"""
            for dp in report.trend[-10:]:
                html += f"""
                <tr>
                    <td>{dp.date}</td>
                    <td>{dp.total_vulnerabilities}</td>
                    <td>{dp.auto_fixable}</td>
                    <td>{dp.non_auto_fixable}</td>
                </tr>"""

            html += """
            </table>
        </div>
"""

        html += f"""
        <div class="footer">
            Security Fixer Dashboard | {report.generated_at}
        </div>
    </div>
</body>
</html>"""

        Path(output_path).write_text(html, encoding="utf-8")
        return output_path

    def generate_json_report(self, scan_results: List = None, output_path: str = "dashboard.json") -> str:
        """生成JSON格式的仪表盘报告"""
        report = self.tracker.get_dashboard_report(scan_results)

        data = {
            "generated_at": report.generated_at,
            "current": {
                "date": report.current.date,
                "total_vulnerabilities": report.current.total_vulnerabilities,
                "by_language": report.current.by_language,
                "by_type": report.current.by_type,
                "by_severity": report.current.by_severity,
                "auto_fixable": report.current.auto_fixable,
                "non_auto_fixable": report.current.non_auto_fixable,
            },
            "trend": [
                {
                    "date": dp.date,
                    "total": dp.total_vulnerabilities,
                    "by_language": dp.by_language,
                    "by_type": dp.by_type,
                }
                for dp in report.trend
            ],
            "summary": report.summary,
        }

        Path(output_path).write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        return output_path
