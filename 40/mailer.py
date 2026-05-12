#!/usr/bin/env python3
import json
import os
import smtplib
import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from email.utils import formatdate, make_msgid
from typing import List, Dict, Any, Optional


class EmailSender:
    def __init__(self, config: Dict[str, Any] = None):
        if config is None:
            config = {}

        email_config = config.get("email", {}) if isinstance(config, dict) else {}

        self.smtp_host = email_config.get("smtp_host", "")
        self.smtp_port = email_config.get("smtp_port", 587)
        self.smtp_username = email_config.get("smtp_username", "")
        self.smtp_password = email_config.get("smtp_password", "")
        self.use_tls = email_config.get("use_tls", True)
        self.use_ssl = email_config.get("use_ssl", False)

        self.sender = email_config.get("sender", self.smtp_username)
        self.sender_name = email_config.get("sender_name", "Git 仓库清理工具")
        self.recipients = email_config.get("recipients", [])
        self.subject_prefix = email_config.get("subject_prefix", "[Git Cleanup]")

    def _create_message(self, subject: str, body_text: str, body_html: Optional[str] = None,
                        attachments: Optional[List[str]] = None) -> MIMEMultipart:
        msg = MIMEMultipart("mixed")
        msg["From"] = f"{self.sender_name} <{self.sender}>"
        msg["To"] = ", ".join(self.recipients)
        msg["Subject"] = f"{self.subject_prefix} {subject}"
        msg["Date"] = formatdate(localtime=True)
        msg["Message-ID"] = make_msgid()

        alternative = MIMEMultipart("alternative")
        alternative.attach(MIMEText(body_text, "plain", "utf-8"))

        if body_html:
            alternative.attach(MIMEText(body_html, "html", "utf-8"))

        msg.attach(alternative)

        if attachments:
            for file_path in attachments:
                if os.path.exists(file_path):
                    with open(file_path, "rb") as f:
                        part = MIMEBase("application", "octet-stream")
                        part.set_payload(f.read())
                    encoders.encode_base64(part)
                    filename = os.path.basename(file_path)
                    part.add_header(
                        "Content-Disposition",
                        f"attachment; filename=\"{filename}\""
                    )
                    msg.attach(part)

        return msg

    def send(self, subject: str, body_text: str, body_html: Optional[str] = None,
             attachments: Optional[List[str]] = None, dry_run: bool = False,
             verbose: bool = False) -> bool:
        if not self.smtp_host:
            print("错误: 未配置 SMTP 服务器信息")
            return False

        if not self.sender:
            print("错误: 未配置发件人")
            return False

        if not self.recipients:
            print("警告: 未配置收件人，邮件将不发送")
            return False

        msg = self._create_message(subject, body_text, body_html, attachments)

        if verbose:
            print(f"准备发送邮件: {msg['Subject']}")
            print(f"发件人: {msg['From']}")
            print(f"收件人: {msg['To']}")
            if attachments:
                print(f"附件: {attachments}")

        if dry_run:
            print("[DRY RUN] 未实际发送邮件")
            return True

        try:
            if self.use_ssl:
                context = ssl.create_default_context()
                with smtplib.SMTP_SSL(self.smtp_host, self.smtp_port, context=context) as server:
                    if self.smtp_username and self.smtp_password:
                        server.login(self.smtp_username, self.smtp_password)
                    server.sendmail(self.sender, self.recipients, msg.as_string())
            else:
                with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                    if self.use_tls:
                        context = ssl.create_default_context()
                        server.starttls(context=context)
                    if self.smtp_username and self.smtp_password:
                        server.login(self.smtp_username, self.smtp_password)
                    server.sendmail(self.sender, self.recipients, msg.as_string())

            if verbose:
                print("邮件发送成功")
            return True

        except Exception as e:
            print(f"发送邮件时出错: {e}")
            return False

    def send_report(self, reporter, report_files: Dict[str, str], summary: Dict[str, Any],
                    dry_run: bool = False, verbose: bool = False) -> bool:
        subject = "Git 仓库清理执行报告"

        body_text = self._generate_text_email_body(summary)
        body_html = self._generate_html_email_body(summary)

        attachments = []
        if "text" in report_files:
            attachments.append(report_files["text"])
        if "html" in report_files:
            attachments.append(report_files["html"])

        return self.send(
            subject=subject,
            body_text=body_text,
            body_html=body_html,
            attachments=attachments,
            dry_run=dry_run,
            verbose=verbose
        )

    def _generate_text_email_body(self, summary: Dict[str, Any]) -> str:
        lines = []
        lines.append("Git 仓库清理执行报告")
        lines.append("=" * 50)
        lines.append("")
        lines.append("执行摘要:")
        lines.append(f"  - 处理的仓库数: {summary.get('repos_processed', 0)}")
        lines.append(f"  - 删除的分支总数: {summary.get('branches_deleted', 0)}")
        lines.append(f"  - 删除的大文件数: {summary.get('large_files_deleted', 0)}")
        lines.append(f"  - 释放的总空间: {summary.get('total_size_saved_mb', 0)} MB")
        lines.append(f"  - 历史重写次数: {summary.get('history_cleanups', 0)}")
        lines.append(f"  - 总操作数: {summary.get('total_operations', 0)}")
        lines.append("")
        lines.append("详细报告请查看附件。")
        lines.append("")
        lines.append("--")
        lines.append("Git 仓库自动清理工具")

        return "\n".join(lines)

    def _generate_html_email_body(self, summary: Dict[str, Any]) -> str:
        html = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <style>
        body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
        .container { max-width: 600px; margin: 0 auto; padding: 20px; }
        .header { background: #3498db; color: white; padding: 20px; text-align: center; border-radius: 5px; }
        .header h1 { margin: 0; font-size: 24px; }
        .summary { margin-top: 20px; background: #f8f9fa; padding: 20px; border-radius: 5px; }
        .summary h2 { margin-top: 0; color: #2c3e50; font-size: 18px; }
        .stat-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); gap: 10px; margin-top: 15px; }
        .stat-item { background: white; padding: 15px; text-align: center; border-radius: 5px; border: 1px solid #e9ecef; }
        .stat-number { font-size: 28px; font-weight: bold; color: #2980b9; }
        .stat-label { font-size: 12px; color: #6c757d; margin-top: 5px; }
        .footer { margin-top: 30px; padding-top: 20px; border-top: 1px solid #e9ecef; font-size: 12px; color: #6c757d; text-align: center; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Git 仓库清理执行报告</h1>
        </div>
        <div class="summary">
            <h2>执行摘要</h2>
            <div class="stat-grid">
                <div class="stat-item">
                    <div class="stat-number">""" + str(summary.get('repos_processed', 0)) + """</div>
                    <div class="stat-label">处理的仓库数</div>
                </div>
                <div class="stat-item">
                    <div class="stat-number">""" + str(summary.get('branches_deleted', 0)) + """</div>
                    <div class="stat-label">删除的分支总数</div>
                </div>
                <div class="stat-item">
                    <div class="stat-number">""" + str(summary.get('large_files_deleted', 0)) + """</div>
                    <div class="stat-label">删除的大文件数</div>
                </div>
                <div class="stat-item">
                    <div class="stat-number">""" + str(summary.get('total_size_saved_mb', 0)) + """</div>
                    <div class="stat-label">释放空间 (MB)</div>
                </div>
                <div class="stat-item">
                    <div class="stat-number">""" + str(summary.get('history_cleanups', 0)) + """</div>
                    <div class="stat-label">历史重写次数</div>
                </div>
                <div class="stat-item">
                    <div class="stat-number">""" + str(summary.get('total_operations', 0)) + """</div>
                    <div class="stat-label">总操作数</div>
                </div>
            </div>
        </div>
        <div class="footer">
            详细报告请查看附件。<br>
            Git 仓库自动清理工具
        </div>
    </div>
</body>
</html>
"""
        return html


def load_config(config_path: str = "config.json") -> dict:
    if os.path.exists(config_path):
        with open(config_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="测试邮件发送功能")
    parser.add_argument("-c", "--config", default="config.json", help="配置文件路径")
    parser.add_argument("-t", "--test", action="store_true", help="发送测试邮件")
    parser.add_argument("-v", "--verbose", action="store_true", help="详细输出")
    args = parser.parse_args()

    config = load_config(args.config)
    email_sender = EmailSender(config)

    if args.test:
        success = email_sender.send(
            subject="测试邮件",
            body_text="这是一封来自 Git 仓库清理工具的测试邮件。",
            body_html="<html><body><h3>测试邮件</h3><p>这是一封来自 Git 仓库清理工具的测试邮件。</p></body></html>",
            verbose=args.verbose
        )
        if success:
            print("测试邮件发送成功")
        else:
            print("测试邮件发送失败")
