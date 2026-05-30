import json
import logging
import smtplib
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any, Dict, List, Optional

from query_analyzer import DiagnosisResult

logger = logging.getLogger(__name__)

SEVERITY_EMOJI = {
    "critical": "🔴",
    "high": "🟠",
    "medium": "🟡",
    "low": "🔵",
}


@dataclass
class AlertMessage:
    title: str
    severity: str = "medium"
    diagnosis: Optional[DiagnosisResult] = None
    extra: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()

    def to_text(self) -> str:
        lines = [
            f"{SEVERITY_EMOJI.get(self.severity, '⚪')} ES慢查询告警 [{self.severity.upper()}]",
            f"时间: {self.timestamp}",
            "=" * 60,
        ]
        if self.diagnosis:
            sq = self.diagnosis.slow_query
            lines.extend([
                f"索引: {sq.index_name}",
                f"查询ID: {sq.query_id}",
                f"响应时间: {sq.response_time_ms:.1f}ms",
                f"查询类型: {sq.search_type}",
                f"分片: {sq.successful_shards}/{sq.total_shards}",
                f"结果数: {sq.hits_total}",
                f"分页: from={sq.from_offset}, size={sq.size}",
                "-" * 40,
                "原因分析:",
            ])
            for cause in self.diagnosis.causes:
                lines.append(f"  - {cause.value}")
            lines.append("-" * 40)
            lines.append("优化建议:")
            for i, suggestion in enumerate(self.diagnosis.suggestions, 1):
                lines.append(f"  {i}. {suggestion}")
            if self.diagnosis.details:
                lines.append("-" * 40)
                lines.append("详细信息:")
                lines.append(f"  {json.dumps(self.diagnosis.details, indent=2, ensure_ascii=False, default=str)}")
        return "\n".join(lines)

    def to_html(self) -> str:
        severity_color = {"critical": "#dc3545", "high": "#fd7e14", "medium": "#ffc107", "low": "#0dcaf0"}
        color = severity_color.get(self.severity, "#6c757d")
        html_parts = [
            '<div style="font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto;">',
            f'<div style="background: {color}; color: white; padding: 15px; border-radius: 8px 8px 0 0;">',
            f'<h2 style="margin:0;">ES慢查询告警 [{self.severity.upper()}]</h2>',
            f'<p style="margin:5px 0 0 0;">时间: {self.timestamp}</p>',
            '</div>',
            '<div style="border: 1px solid #ddd; padding: 20px; border-radius: 0 0 8px 8px;">',
        ]
        if self.diagnosis:
            sq = self.diagnosis.slow_query
            html_parts.extend([
                '<table style="width:100%; border-collapse: collapse;">',
                self._table_row("索引", sq.index_name),
                self._table_row("查询ID", sq.query_id),
                self._table_row("响应时间", f'<b style="color:{color}">{sq.response_time_ms:.1f}ms</b>'),
                self._table_row("查询类型", sq.search_type),
                self._table_row("分片", f"{sq.successful_shards}/{sq.total_shards}"),
                self._table_row("结果数", str(sq.hits_total)),
                self._table_row("分页", f"from={sq.from_offset}, size={sq.size}"),
                '</table>',
                '<h3 style="color:#333; margin-top:20px;">原因分析</h3>',
                '<ul>',
            ])
            for cause in self.diagnosis.causes:
                html_parts.append(f'<li style="margin:5px 0;"><b>{cause.value}</b></li>')
            html_parts.append('</ul>')
            html_parts.append('<h3 style="color:#333;">优化建议</h3><ol>')
            for suggestion in self.diagnosis.suggestions:
                html_parts.append(f'<li style="margin:5px 0;">{suggestion}</li>')
            html_parts.append('</ol>')
        html_parts.extend(['</div>', '</div>'])
        return "".join(html_parts)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "title": self.title,
            "severity": self.severity,
            "timestamp": self.timestamp,
            "diagnosis": self.diagnosis.to_dict() if self.diagnosis else None,
            "extra": self.extra,
        }

    @staticmethod
    def _table_row(label: str, value: str) -> str:
        return (
            f'<tr><td style="padding:8px;border-bottom:1px solid #eee;'
            f'font-weight:bold;width:120px;">{label}</td>'
            f'<td style="padding:8px;border-bottom:1px solid #eee;">{value}</td></tr>'
        )


class AlertChannel(ABC):
    @abstractmethod
    def send(self, message: AlertMessage) -> bool:
        pass


class ConsoleAlertChannel(AlertChannel):
    def send(self, message: AlertMessage) -> bool:
        try:
            print("\n" + "=" * 70)
            print(message.to_text())
            print("=" * 70 + "\n")
            return True
        except Exception as e:
            logger.error("Console alert failed: %s", e)
            return False


class FileAlertChannel(AlertChannel):
    def __init__(self, file_path: str = "slow_query_alerts.jsonl"):
        self.file_path = file_path

    def send(self, message: AlertMessage) -> bool:
        try:
            with open(self.file_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(message.to_dict(), ensure_ascii=False, default=str) + "\n")
            return True
        except Exception as e:
            logger.error("File alert failed: %s", e)
            return False


class EmailAlertChannel(AlertChannel):
    def __init__(self, smtp_host: str, smtp_port: int = 587,
                 username: str = "", password: str = "",
                 from_addr: str = "", to_addrs: List[str] = None,
                 use_tls: bool = True):
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.username = username
        self.password = password
        self.from_addr = from_addr
        self.to_addrs = to_addrs or []
        self.use_tls = use_tls

    def send(self, message: AlertMessage) -> bool:
        if not self.to_addrs:
            logger.warning("No email recipients configured")
            return False
        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = message.title
            msg["From"] = self.from_addr
            msg["To"] = ", ".join(self.to_addrs)
            msg.attach(MIMEText(message.to_text(), "plain", "utf-8"))
            msg.attach(MIMEText(message.to_html(), "html", "utf-8"))

            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                if self.use_tls:
                    server.starttls()
                if self.username and self.password:
                    server.login(self.username, self.password)
                server.sendmail(self.from_addr, self.to_addrs, msg.as_string())
            logger.info("Email alert sent to %s", self.to_addrs)
            return True
        except Exception as e:
            logger.error("Email alert failed: %s", e)
            return False


class WebhookAlertChannel(AlertChannel):
    def __init__(self, webhook_url: str, headers: Optional[Dict[str, str]] = None):
        self.webhook_url = webhook_url
        self.headers = headers or {"Content-Type": "application/json"}

    def send(self, message: AlertMessage) -> bool:
        try:
            import urllib.request
            data = json.dumps(message.to_dict(), ensure_ascii=False, default=str).encode("utf-8")
            req = urllib.request.Request(
                self.webhook_url, data=data, headers=self.headers, method="POST"
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                if resp.status >= 400:
                    logger.error("Webhook returned status %d", resp.status)
                    return False
            logger.info("Webhook alert sent to %s", self.webhook_url)
            return True
        except Exception as e:
            logger.error("Webhook alert failed: %s", e)
            return False


class Alerter:
    def __init__(self, channels: Optional[List[AlertChannel]] = None,
                 min_severity: str = "medium"):
        self.channels = channels or [ConsoleAlertChannel()]
        self.min_severity = min_severity
        self._severity_level = {"low": 0, "medium": 1, "high": 2, "critical": 3}

    def alert(self, diagnosis: DiagnosisResult) -> bool:
        if not self._should_alert(diagnosis.severity):
            logger.debug("Skipping alert for severity %s (min: %s)",
                         diagnosis.severity, self.min_severity)
            return False

        message = AlertMessage(
            title=f"ES慢查询告警 - {diagnosis.slow_query.index_name} "
                  f"({diagnosis.slow_query.response_time_ms:.0f}ms)",
            severity=diagnosis.severity,
            diagnosis=diagnosis,
        )

        success = False
        for channel in self.channels:
            try:
                if channel.send(message):
                    success = True
            except Exception as e:
                logger.error("Alert channel %s failed: %s", type(channel).__name__, e)
        return success

    def _should_alert(self, severity: str) -> bool:
        return self._severity_level.get(severity, 0) >= self._severity_level.get(self.min_severity, 1)
