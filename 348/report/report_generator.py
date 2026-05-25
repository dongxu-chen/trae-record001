import logging
import os
import json
from datetime import datetime
from typing import Dict, Any, List, Optional
from jinja2 import Environment, FileSystemLoader, select_autoescape

from core.validation_engine import CheckStatus, CheckResult

logger = logging.getLogger(__name__)


class ReportGenerator:
    def __init__(self, output_dir: str, template_path: Optional[str] = None, include_detailed_log: bool = True):
        self.output_dir = output_dir
        self.include_detailed_log = include_detailed_log
        self._ensure_output_dir()

        self.jinja_env = self._setup_jinja_env(template_path)

    def _ensure_output_dir(self):
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)
            logger.info(f"Created output directory: {self.output_dir}")

    def _setup_jinja_env(self, template_path: Optional[str] = None):
        if template_path and os.path.exists(template_path):
            template_dir = os.path.dirname(template_path)
            env = Environment(
                loader=FileSystemLoader(template_dir),
                autoescape=select_autoescape(['html', 'xml'])
            )
            self.template_file = os.path.basename(template_path)
        else:
            default_dir = os.path.join(os.path.dirname(__file__), 'templates')
            if os.path.exists(default_dir):
                env = Environment(
                    loader=FileSystemLoader(default_dir),
                    autoescape=select_autoescape(['html', 'xml'])
                )
            else:
                env = Environment(autoescape=select_autoescape(['html', 'xml']))
            self.template_file = 'validation_report.html'

        env.filters['format_datetime'] = self._format_datetime
        env.filters['format_duration'] = self._format_duration
        env.filters['status_badge'] = self._status_badge
        env.filters['status_color'] = self._status_color
        env.filters['truncate'] = self._truncate_string

        return env

    def _format_datetime(self, timestamp: Optional[float]) -> str:
        if timestamp is None:
            return "N/A"
        return datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')

    def _format_duration(self, seconds: float) -> str:
        if seconds < 60:
            return f"{seconds:.2f}s"
        elif seconds < 3600:
            minutes = seconds / 60
            return f"{minutes:.2f}m"
        else:
            hours = seconds / 3600
            return f"{hours:.2f}h"

    def _status_badge(self, status: CheckStatus) -> str:
        badges = {
            CheckStatus.PASSED: '✓ PASSED',
            CheckStatus.FAILED: '✗ FAILED',
            CheckStatus.WARNING: '⚠ WARNING',
            CheckStatus.SKIPPED: '⊘ SKIPPED',
            CheckStatus.ERROR: '✕ ERROR'
        }
        return badges.get(status, str(status))

    def _status_color(self, status: CheckStatus) -> str:
        colors = {
            CheckStatus.PASSED: '#28a745',
            CheckStatus.FAILED: '#dc3545',
            CheckStatus.WARNING: '#ffc107',
            CheckStatus.SKIPPED: '#6c757d',
            CheckStatus.ERROR: '#dc3545'
        }
        return colors.get(status, '#6c757d')

    def _truncate_string(self, text: str, length: int = 100) -> str:
        if len(text) <= length:
            return text
        return text[:length] + '...'

    def generate_report(
        self,
        restore_result: Dict[str, Any],
        validation_summary: Dict[str, Any],
        config: Dict[str, Any]
    ) -> str:
        report_data = {
            'generated_at': datetime.now().timestamp(),
            'restore_result': restore_result,
            'validation': validation_summary,
            'config': config,
            'include_detailed_log': self.include_detailed_log
        }

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

        html_path = self._generate_html(report_data, timestamp)
        json_path = self._generate_json(report_data, timestamp)

        logger.info(f"Reports generated: HTML={html_path}, JSON={json_path}")
        return html_path

    def _generate_html(self, data: Dict[str, Any], timestamp: str) -> str:
        try:
            template = self.jinja_env.get_template(self.template_file)
        except Exception as e:
            logger.warning(f"Failed to load template {self.template_file}: {e}, using built-in template")
            template = self.jinja_env.from_string(self._get_builtin_template())

        html_content = template.render(**data)

        file_name = f"validation_report_{timestamp}.html"
        file_path = os.path.join(self.output_dir, file_name)

        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(html_content)

        logger.info(f"HTML report saved: {file_path}")
        return file_path

    def _generate_json(self, data: Dict[str, Any], timestamp: str) -> str:
        json_data = self._convert_to_serializable(data)
        file_name = f"validation_report_{timestamp}.json"
        file_path = os.path.join(self.output_dir, file_name)

        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(json_data, f, indent=2, ensure_ascii=False, default=str)

        logger.info(f"JSON report saved: {file_path}")
        return file_path

    def _convert_to_serializable(self, obj: Any) -> Any:
        if isinstance(obj, CheckStatus):
            return obj.value
        elif isinstance(obj, CheckResult):
            return {
                'check_name': obj.check_name,
                'status': obj.status.value,
                'table_name': obj.table_name,
                'message': obj.message,
                'details': self._convert_to_serializable(obj.details),
                'duration_seconds': obj.duration_seconds
            }
        elif isinstance(obj, dict):
            return {k: self._convert_to_serializable(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._convert_to_serializable(item) for item in obj]
        elif isinstance(obj, datetime):
            return obj.isoformat()
        else:
            return obj

    def _get_builtin_template(self) -> str:
        return """<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>数据库备份恢复验证报告</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: #f5f7fa; color: #333; }
        .container { max-width: 1200px; margin: 0 auto; padding: 20px; }
        .header { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; border-radius: 10px; margin-bottom: 20px; }
        .header h1 { font-size: 24px; margin-bottom: 10px; }
        .header .meta { font-size: 14px; opacity: 0.9; }
        .summary-cards { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; margin-bottom: 20px; }
        .card { background: white; border-radius: 10px; padding: 20px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        .card h3 { font-size: 14px; color: #666; margin-bottom: 10px; }
        .card .value { font-size: 28px; font-weight: bold; }
        .card .sub { font-size: 12px; color: #999; margin-top: 5px; }
        .card.passed .value { color: #28a745; }
        .card.failed .value { color: #dc3545; }
        .card.warning .value { color: #ffc107; }
        .card.info .value { color: #17a2b8; }
        .section { background: white; border-radius: 10px; padding: 20px; margin-bottom: 20px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        .section h2 { font-size: 18px; margin-bottom: 15px; padding-bottom: 10px; border-bottom: 2px solid #f0f0f0; }
        table { width: 100%; border-collapse: collapse; margin-top: 10px; }
        th, td { padding: 12px; text-align: left; border-bottom: 1px solid #eee; }
        th { background: #f8f9fa; font-weight: 600; font-size: 13px; color: #555; }
        tr:hover { background: #f8f9fa; }
        .badge { display: inline-block; padding: 4px 12px; border-radius: 20px; font-size: 12px; font-weight: 600; }
        .badge.passed { background: #d4edda; color: #155724; }
        .badge.failed { background: #f8d7da; color: #721c24; }
        .badge.warning { background: #fff3cd; color: #856404; }
        .badge.skipped { background: #e2e3e5; color: #383d41; }
        .badge.error { background: #f8d7da; color: #721c24; }
        .detail-box { background: #f8f9fa; padding: 10px; border-radius: 5px; font-family: monospace; font-size: 12px; max-height: 200px; overflow-y: auto; }
        .expandable { cursor: pointer; }
        .expandable::after { content: ' ▼'; font-size: 10px; }
        .expandable.expanded::after { content: ' ▲'; }
        .hidden { display: none; }
        .progress-bar { height: 8px; background: #e9ecef; border-radius: 4px; overflow: hidden; }
        .progress-bar .fill { height: 100%; transition: width 0.3s; }
        .progress-bar .fill.passed { background: #28a745; }
        .progress-bar .fill.failed { background: #dc3545; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>数据库备份恢复验证报告</h1>
            <div class="meta">
                报告生成时间: {{ generated_at | format_datetime }} |
                备份文件: {{ restore_result.backup_file | default('N/A') }}
            </div>
        </div>

        <div class="summary-cards">
            <div class="card passed">
                <h3>通过</h3>
                <div class="value">{{ validation.passed }}</div>
                <div class="sub">检查项通过数量</div>
            </div>
            <div class="card {{ 'failed' if validation.failed > 0 else 'passed' }}">
                <h3>失败</h3>
                <div class="value">{{ validation.failed }}</div>
                <div class="sub">检查项失败数量</div>
            </div>
            <div class="card {{ 'warning' if validation.warnings > 0 else 'info' }}">
                <h3>警告</h3>
                <div class="value">{{ validation.warnings }}</div>
                <div class="sub">警告数量</div>
            </div>
            <div class="card info">
                <h3>通过率</h3>
                <div class="value">{{ '%.1f' | format(validation.pass_rate) }}%</div>
                <div class="sub">总通过率</div>
            </div>
            <div class="card info">
                <h3>恢复耗时</h3>
                <div class="value">{{ restore_result.duration_seconds | format_duration }}</div>
                <div class="sub">备份恢复时间</div>
            </div>
        </div>

        <div class="section">
            <h2>恢复结果</h2>
            <table>
                <tr><th>状态</th><td><span class="badge {{ 'passed' if restore_result.success else 'failed' }}">{{ '成功' if restore_result.success else '失败' }}</span></td></tr>
                <tr><th>开始时间</th><td>{{ restore_result.start_time | format_datetime }}</td></tr>
                <tr><th>结束时间</th><td>{{ restore_result.end_time | format_datetime }}</td></tr>
                <tr><th>恢复耗时</th><td>{{ restore_result.duration_seconds | format_duration }}</td></tr>
                <tr><th>加密验证</th><td>{{ '已验证' if restore_result.encryption_verified else '未启用' }}</td></tr>
                {% if restore_result.error %}
                <tr><th>错误信息</th><td style="color: #dc3545;">{{ restore_result.error }}</td></tr>
                {% endif %}
            </table>
        </div>

        <div class="section">
            <h2>验证结果详情</h2>
            <table>
                <thead>
                    <tr>
                        <th>检查类型</th>
                        <th>表名</th>
                        <th>状态</th>
                        <th>消息</th>
                        <th>耗时</th>
                    </tr>
                </thead>
                <tbody>
                    {% for result in validation.results %}
                    <tr class="result-row">
                        <td>{{ result.check_name }}</td>
                        <td>{{ result.table_name | default('-') }}</td>
                        <td><span class="badge {{ result.status.value | lower }}">{{ result.status | status_badge }}</span></td>
                        <td>{{ result.message | truncate(150) }}</td>
                        <td>{{ result.duration_seconds | format_duration }}</td>
                    </tr>
                    {% if include_detailed_log and result.details %}
                    <tr class="detail-row hidden">
                        <td colspan="5">
                            <div class="detail-box">{{ result.details | tojson }}</div>
                        </td>
                    </tr>
                    {% endif %}
                    {% endfor %}
                </tbody>
            </table>
        </div>

        <div class="section">
            <h2>配置信息</h2>
            <table>
                <tr><th>源数据库</th><td>{{ config.source_db.host }}:{{ config.source_db.port }}/{{ config.source_db.database }}</td></tr>
                <tr><th>验证数据库</th><td>{{ config.verification_db.host }}:{{ config.verification_db.port }}/{{ config.verification_db.database }}</td></tr>
                <tr><th>备份文件</th><td>{{ config.backup.backup_file_path }}</td></tr>
                <tr><th>备份类型</th><td>{{ config.backup.backup_type }}</td></tr>
                <tr><th>加密算法</th><td>{{ config.backup.encryption_algorithm | default('未加密') }}</td></tr>
                <tr><th>行数容差</th><td>{{ config.validation.row_count_tolerance }}%</td></tr>
                <tr><th>抽样比例</th><td>{{ config.validation.sample_percentage }}%</td></tr>
            </table>
        </div>
    </div>

    <script>
        document.querySelectorAll('.result-row').forEach(row => {
            row.addEventListener('click', function() {
                const nextRow = this.nextElementSibling;
                if (nextRow && nextRow.classList.contains('detail-row')) {
                    nextRow.classList.toggle('hidden');
                }
            });
        });
    </script>
</body>
</html>"""
