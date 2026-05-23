import os
import json
from datetime import datetime
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

from .report import QualityReport
from .quality_gate import QualityGateResult


@dataclass
class TrendData:
    timestamp: str
    total_errors: int
    total_warnings: int
    scores: Dict[str, float]


class HTMLReportGenerator:
    def __init__(self, output_dir: str = "quality-reports"):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)

    def generate(
        self,
        report: QualityReport,
        quality_gate_result: Optional[QualityGateResult] = None,
        trend_history: Optional[List[TrendData]] = None,
        filename: Optional[str] = None,
    ) -> str:
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"quality_report_{timestamp}.html"

        filepath = os.path.join(self.output_dir, filename)

        html_content = self._build_html(report, quality_gate_result, trend_history)

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(html_content)

        return filepath

    def _load_trend_history(self) -> List[TrendData]:
        history_file = os.path.join(self.output_dir, "trend_history.json")
        if not os.path.exists(history_file):
            return []

        try:
            with open(history_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            return [TrendData(**item) for item in data]
        except Exception:
            return []

    def _save_trend_data(self, report: QualityReport):
        history_file = os.path.join(self.output_dir, "trend_history.json")
        history = self._load_trend_history()

        scores = {}
        for result in report.results:
            if result.score is not None:
                scores[result.linter_name] = result.score

        trend_data = TrendData(
            timestamp=report.timestamp,
            total_errors=report.total_errors,
            total_warnings=report.total_warnings,
            scores=scores,
        )

        history.append(trend_data)

        if len(history) > 30:
            history = history[-30:]

        with open(history_file, "w", encoding="utf-8") as f:
            json.dump([d.__dict__ for d in history], f, indent=2)

    def _build_html(
        self,
        report: QualityReport,
        quality_gate_result: Optional[QualityGateResult],
        trend_history: Optional[List[TrendData]],
    ) -> str:
        if trend_history is None:
            trend_history = self._load_trend_history()
            self._save_trend_data(report)
            trend_history = self._load_trend_history()

        overall_status = "PASS" if report.threshold_passed else "FAIL"
        status_color = "#28a745" if report.threshold_passed else "#dc3545"

        html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Code Quality Report</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        {self._get_css()}
    </style>
</head>
<body>
    <div class="container">
        <header class="header">
            <h1>📊 Code Quality Report</h1>
            <p class="timestamp">Generated at: {report.timestamp}</p>
            <div class="overall-status" style="background-color: {status_color}">
                {overall_status}
            </div>
        </header>

        <section class="summary-section">
            <h2>📈 Summary</h2>
            <div class="stats-grid">
                <div class="stat-card">
                    <div class="stat-value">{report.total_files_checked}</div>
                    <div class="stat-label">Files Checked</div>
                </div>
                <div class="stat-card error">
                    <div class="stat-value">{report.total_errors}</div>
                    <div class="stat-label">Errors</div>
                </div>
                <div class="stat-card warning">
                    <div class="stat-value">{report.total_warnings}</div>
                    <div class="stat-label">Warnings</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value">{len(report.results)}</div>
                    <div class="stat-label">Linters Run</div>
                </div>
            </div>
        </section>

        <section class="charts-section">
            <h2>📉 Charts</h2>
            <div class="charts-grid">
                <div class="chart-container">
                    <h3>Issues by Linter</h3>
                    <canvas id="issuesChart"></canvas>
                </div>
                <div class="chart-container">
                    <h3>Trend (Last {len(trend_history)} runs)</h3>
                    <canvas id="trendChart"></canvas>
                </div>
            </div>
        </section>

        {self._get_quality_gate_html(quality_gate_result)}

        <section class="linters-section">
            <h2>🔍 Linter Details</h2>
            {self._get_linters_html(report)}
        </section>

        {self._get_issues_html(report)}

        <footer class="footer">
            <p>Code Quality Checker - Automated Code Quality Analysis</p>
        </footer>
    </div>

    <script>
        {self._get_charts_js(report, trend_history)}
    </script>
</body>
</html>"""
        return html

    def _get_css(self) -> str:
        return """
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }

        .container {
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 16px;
            box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
            overflow: hidden;
        }

        .header {
            background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
            color: white;
            padding: 40px;
            text-align: center;
            position: relative;
        }

        .header h1 {
            font-size: 2.5rem;
            margin-bottom: 10px;
        }

        .timestamp {
            opacity: 0.8;
        }

        .overall-status {
            position: absolute;
            top: 50%;
            right: 40px;
            transform: translateY(-50%);
            padding: 12px 30px;
            border-radius: 50px;
            font-weight: bold;
            font-size: 1.2rem;
            color: white;
            text-transform: uppercase;
            letter-spacing: 2px;
        }

        section {
            padding: 30px 40px;
            border-bottom: 1px solid #eee;
        }

        section h2 {
            color: #1e3c72;
            margin-bottom: 20px;
            font-size: 1.5rem;
        }

        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
        }

        .stat-card {
            background: #f8f9fa;
            padding: 25px;
            border-radius: 12px;
            text-align: center;
            transition: transform 0.3s;
        }

        .stat-card:hover {
            transform: translateY(-5px);
        }

        .stat-card.error {
            background: linear-gradient(135deg, #ff6b6b 0%, #ee5a5a 100%);
            color: white;
        }

        .stat-card.warning {
            background: linear-gradient(135deg, #feca57 0%, #ff9f43 100%);
            color: white;
        }

        .stat-value {
            font-size: 2.5rem;
            font-weight: bold;
            margin-bottom: 8px;
        }

        .stat-label {
            font-size: 0.9rem;
            opacity: 0.8;
        }

        .charts-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
            gap: 30px;
        }

        .chart-container {
            background: #f8f9fa;
            padding: 20px;
            border-radius: 12px;
        }

        .chart-container h3 {
            color: #555;
            margin-bottom: 15px;
            font-size: 1rem;
        }

        .quality-gate {
            background: #fff8e1;
            border-left: 4px solid #ffc107;
        }

        .quality-gate.passed {
            background: #e8f5e9;
            border-left-color: #4caf50;
        }

        .quality-gate.failed {
            background: #ffebee;
            border-left-color: #f44336;
        }

        .quality-gate h3 {
            color: #333;
            margin-bottom: 15px;
        }

        .violation-item {
            padding: 10px 15px;
            margin: 8px 0;
            background: rgba(244, 67, 54, 0.1);
            border-radius: 6px;
            color: #c62828;
        }

        .linter-card {
            background: #f8f9fa;
            padding: 20px;
            border-radius: 12px;
            margin-bottom: 15px;
        }

        .linter-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 15px;
        }

        .linter-name {
            font-size: 1.2rem;
            font-weight: bold;
            color: #1e3c72;
            text-transform: uppercase;
        }

        .linter-status {
            padding: 5px 15px;
            border-radius: 20px;
            font-size: 0.85rem;
            font-weight: bold;
        }

        .linter-status.pass {
            background: #4caf50;
            color: white;
        }

        .linter-status.fail {
            background: #f44336;
            color: white;
        }

        .linter-stats {
            display: flex;
            gap: 20px;
        }

        .linter-stat {
            text-align: center;
        }

        .linter-stat-value {
            font-size: 1.5rem;
            font-weight: bold;
        }

        .linter-stat-label {
            font-size: 0.8rem;
            color: #666;
        }

        .issues-table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 20px;
        }

        .issues-table th,
        .issues-table td {
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #eee;
        }

        .issues-table th {
            background: #1e3c72;
            color: white;
            font-weight: 600;
        }

        .issues-table tr:hover {
            background: #f5f5f5;
        }

        .severity-error {
            color: #f44336;
            font-weight: bold;
        }

        .severity-warning {
            color: #ff9800;
            font-weight: bold;
        }

        .footer {
            background: #1e3c72;
            color: white;
            text-align: center;
            padding: 20px;
        }

        .collapsible {
            cursor: pointer;
            user-select: none;
        }

        .collapsible-content {
            display: none;
            overflow: hidden;
        }

        .collapsible-content.active {
            display: block;
        }

        .badge {
            display: inline-block;
            padding: 3px 10px;
            border-radius: 12px;
            font-size: 0.75rem;
            font-weight: bold;
            margin-left: 10px;
        }

        .badge-fixable {
            background: #4caf50;
            color: white;
        }
        """

    def _get_quality_gate_html(self, result: Optional[QualityGateResult]) -> str:
        if result is None:
            return ""

        status_class = "passed" if result.passed else "failed"
        status_text = "PASSED" if result.passed else "FAILED"

        violations_html = ""
        if not result.passed:
            violations_html = "<div class='violations'>"
            for v in result.violations:
                violations_html += f"<div class='violation-item'>❌ {v.message}</div>"
            violations_html += "</div>"

        return f"""
        <section class="quality-gate {status_class}">
            <h2>🚪 Quality Gate</h2>
            <div class="quality-gate-header">
                <h3>Status: <span style="color: {'#4caf50' if result.passed else '#f44336'}">{status_text}</span></h3>
            </div>
            {violations_html}
        </section>
        """

    def _get_linters_html(self, report: QualityReport) -> str:
        html = ""

        for result in report.results:
            status_class = "pass" if result.success else "fail"
            status_text = "PASS" if result.success else "FAIL"
            score_html = ""

            if result.score is not None:
                score_color = "#4caf50" if result.score >= 8.0 else "#ff9800" if result.score >= 6.0 else "#f44336"
                score_html = f"""
                <div class="linter-stat">
                    <div class="linter-stat-value" style="color: {score_color}">{result.score:.2f}</div>
                    <div class="linter-stat-label">Score</div>
                </div>
                """

            html += f"""
            <div class="linter-card">
                <div class="linter-header">
                    <span class="linter-name">{result.linter_name}</span>
                    <span class="linter-status {status_class}">{status_text}</span>
                </div>
                <div class="linter-stats">
                    <div class="linter-stat">
                        <div class="linter-stat-value" style="color: #f44336">{result.error_count}</div>
                        <div class="linter-stat-label">Errors</div>
                    </div>
                    <div class="linter-stat">
                        <div class="linter-stat-value" style="color: #ff9800">{result.warning_count}</div>
                        <div class="linter-stat-label">Warnings</div>
                    </div>
                    <div class="linter-stat">
                        <div class="linter-stat-value">{len(result.files_checked)}</div>
                        <div class="linter-stat-label">Files</div>
                    </div>
                    {score_html}
                </div>
            </div>
            """

        return html

    def _get_issues_html(self, report: QualityReport) -> str:
        all_issues = []
        for result in report.results:
            for issue in result.issues:
                all_issues.append({
                    "linter": result.linter_name,
                    **issue.to_dict()
                })

        if not all_issues:
            return """
        <section class="issues-section">
            <h2>⚠️ Issues</h2>
            <p style="color: #4caf50; font-size: 1.1rem;">✅ No issues found!</p>
        </section>
            """

        issues_html = f"""
        <section class="issues-section">
            <h2>⚠️ Issues ({len(all_issues)} total)</h2>
            <table class="issues-table">
                <thead>
                    <tr>
                        <th>Linter</th>
                        <th>File</th>
                        <th>Line</th>
                        <th>Col</th>
                        <th>Severity</th>
                        <th>Rule</th>
                        <th>Message</th>
                    </tr>
                </thead>
                <tbody>
        """

        for issue in all_issues[:100]:
            severity_class = f"severity-{issue['severity']}"
            fixable_badge = '<span class="badge badge-fixable">Fixable</span>' if issue.get('fixable') else ''
            issues_html += f"""
                    <tr>
                        <td><strong>{issue['linter']}</strong></td>
                        <td>{issue['file']}</td>
                        <td>{issue['line']}</td>
                        <td>{issue['column']}</td>
                        <td class="{severity_class}">{issue['severity']}</td>
                        <td>{issue['rule']}{fixable_badge}</td>
                        <td>{issue['message']}</td>
                    </tr>
            """

        if len(all_issues) > 100:
            issues_html += f"""
                    <tr>
                        <td colspan="7" style="text-align: center; color: #666;">
                            ... and {len(all_issues) - 100} more issues
                        </td>
                    </tr>
            """

        issues_html += """
                </tbody>
            </table>
        </section>
        """

        return issues_html

    def _get_charts_js(self, report: QualityReport, trend_history: List[TrendData]) -> str:
        linter_names = []
        error_counts = []
        warning_counts = []

        for result in report.results:
            linter_names.append(result.linter_name)
            error_counts.append(result.error_count)
            warning_counts.append(result.warning_count)

        trend_labels = []
        trend_errors = []
        trend_warnings = []

        for data in trend_history[-10:]:
            trend_labels.append(data.timestamp.split()[-1] if len(data.timestamp.split()) > 1 else data.timestamp)
            trend_errors.append(data.total_errors)
            trend_warnings.append(data.total_warnings)

        return f"""
        // Issues by Linter Chart
        const issuesCtx = document.getElementById('issuesChart').getContext('2d');
        new Chart(issuesCtx, {{
            type: 'bar',
            data: {{
                labels: {json.dumps(linter_names)},
                datasets: [
                    {{
                        label: 'Errors',
                        data: {json.dumps(error_counts)},
                        backgroundColor: 'rgba(244, 67, 54, 0.8)',
                        borderColor: 'rgba(244, 67, 54, 1)',
                        borderWidth: 1
                    }},
                    {{
                        label: 'Warnings',
                        data: {json.dumps(warning_counts)},
                        backgroundColor: 'rgba(255, 152, 0, 0.8)',
                        borderColor: 'rgba(255, 152, 0, 1)',
                        borderWidth: 1
                    }}
                ]
            }},
            options: {{
                responsive: true,
                plugins: {{
                    legend: {{
                        position: 'top',
                    }}
                }},
                scales: {{
                    y: {{
                        beginAtZero: true,
                        ticks: {{
                            stepSize: 1
                        }}
                    }}
                }}
            }}
        }});

        // Trend Chart
        const trendCtx = document.getElementById('trendChart').getContext('2d');
        new Chart(trendCtx, {{
            type: 'line',
            data: {{
                labels: {json.dumps(trend_labels)},
                datasets: [
                    {{
                        label: 'Errors',
                        data: {json.dumps(trend_errors)},
                        borderColor: 'rgba(244, 67, 54, 1)',
                        backgroundColor: 'rgba(244, 67, 54, 0.1)',
                        fill: true,
                        tension: 0.4
                    }},
                    {{
                        label: 'Warnings',
                        data: {json.dumps(trend_warnings)},
                        borderColor: 'rgba(255, 152, 0, 1)',
                        backgroundColor: 'rgba(255, 152, 0, 0.1)',
                        fill: true,
                        tension: 0.4
                    }}
                ]
            }},
            options: {{
                responsive: true,
                plugins: {{
                    legend: {{
                        position: 'top',
                    }}
                }},
                scales: {{
                    y: {{
                        beginAtZero: true
                    }}
                }}
            }}
        }});
        """
