import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.header import Header
from typing import Optional, Dict, List


class EmailNotifier:
    def __init__(
        self,
        enabled: bool,
        smtp_server: str,
        smtp_port: int,
        smtp_username: str,
        smtp_password: str,
        use_tls: bool,
        sender: str,
        recipients: List[str],
        logger: Optional[logging.Logger] = None
    ):
        self.enabled = enabled
        self.smtp_server = smtp_server
        self.smtp_port = smtp_port
        self.smtp_username = smtp_username
        self.smtp_password = smtp_password
        self.use_tls = use_tls
        self.sender = sender
        self.recipients = recipients
        self.logger = logger or logging.getLogger(__name__)

    def _send_email(self, subject: str, html_content: str) -> None:
        if not self.enabled:
            self.logger.debug("邮件通知未启用，跳过发送")
            return

        if not self.recipients:
            self.logger.warning("没有配置收件人，跳过发送邮件")
            return

        try:
            msg = MIMEMultipart('alternative')
            msg['From'] = self.sender
            msg['To'] = ', '.join(self.recipients)
            msg['Subject'] = Header(subject, 'utf-8')

            html_part = MIMEText(html_content, 'html', 'utf-8')
            msg.attach(html_part)

            self.logger.info(f"发送邮件通知: {subject}")
            
            with smtplib.SMTP(self.smtp_server, self.smtp_port, timeout=30) as server:
                if self.use_tls:
                    server.starttls()
                if self.smtp_username and self.smtp_password:
                    server.login(self.smtp_username, self.smtp_password)
                server.sendmail(self.sender, self.recipients, msg.as_string())
            
            self.logger.info("邮件发送成功")
        except Exception as e:
            self.logger.error(f"邮件发送失败: {e}")

    def send_backup_success(self, backup_summary: Dict) -> None:
        subject = f"[备份成功] {backup_summary['task_name']} - {backup_summary['timestamp']}"
        
        backup_type_cn = "全量" if backup_summary['backup_type'] == 'full' else "增量"
        
        html_content = f"""
        <html>
        <head>
            <style>
                body {{
                    font-family: 'Microsoft YaHei', Arial, sans-serif;
                    padding: 20px;
                    background-color: #f5f5f5;
                }}
                .container {{
                    max-width: 700px;
                    margin: 0 auto;
                    background-color: white;
                    border-radius: 8px;
                    box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                }}
                .header {{
                    background-color: #4CAF50;
                    color: white;
                    padding: 20px;
                    border-radius: 8px 8px 0 0;
                }}
                .header h2 {{
                    margin: 0;
                    font-size: 20px;
                }}
                .content {{
                    padding: 25px;
                }}
                .summary-grid {{
                    display: grid;
                    grid-template-columns: 1fr 1fr;
                    gap: 15px;
                    margin-bottom: 20px;
                }}
                .summary-item {{
                    background-color: #f9f9f9;
                    padding: 15px;
                    border-radius: 6px;
                    border-left: 4px solid #4CAF50;
                }}
                .summary-item-label {{
                    font-size: 12px;
                    color: #666;
                    margin-bottom: 5px;
                }}
                .summary-item-value {{
                    font-size: 18px;
                    font-weight: bold;
                    color: #333;
                }}
                .stats-table {{
                    width: 100%;
                    border-collapse: collapse;
                    margin-top: 20px;
                }}
                .stats-table th {{
                    background-color: #f0f0f0;
                    text-align: left;
                    padding: 12px;
                    font-weight: bold;
                    border-bottom: 2px solid #ddd;
                }}
                .stats-table td {{
                    padding: 12px;
                    border-bottom: 1px solid #eee;
                }}
                .stats-table tr:last-child td {{
                    border-bottom: none;
                }}
                .success {{
                    color: #4CAF50;
                    font-weight: bold;
                }}
                .info {{
                    color: #2196F3;
                }}
                .footer {{
                    margin-top: 25px;
                    padding-top: 20px;
                    border-top: 1px solid #eee;
                    color: #999;
                    font-size: 12px;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h2>✅ 备份任务执行成功</h2>
                </div>
                <div class="content">
                    <div class="summary-grid">
                        <div class="summary-item">
                            <div class="summary-item-label">任务名称</div>
                            <div class="summary-item-value">{backup_summary['task_name']}</div>
                        </div>
                        <div class="summary-item">
                            <div class="summary-item-label">备份类型</div>
                            <div class="summary-item-value">{backup_type_cn}备份</div>
                        </div>
                    </div>
                    
                    <table class="stats-table">
                        <thead>
                            <tr>
                                <th colspan="2">📊 文件统计</th>
                            </tr>
                        </thead>
                        <tbody>
                            <tr>
                                <td>总文件数</td>
                                <td class="info"><strong>{backup_summary['total_files']}</strong> 个文件</td>
                            </tr>
                            <tr>
                                <td>已备份文件数</td>
                                <td class="success"><strong>{backup_summary['files_backed_up']}</strong> 个文件</td>
                            </tr>
                            <tr>
                                <td>未变更文件数</td>
                                <td><strong>{backup_summary.get('unchanged_files', 0)}</strong> 个文件</td>
                            </tr>
                            <tr>
                                <td>压缩包大小</td>
                                <td><strong>{backup_summary['archive_size_mb']}</strong> MB</td>
                            </tr>
                        </tbody>
                    </table>
                    
                    <table class="stats-table">
                        <thead>
                            <tr>
                                <th colspan="2">🗑️ 旧备份清理</th>
                            </tr>
                        </thead>
                        <tbody>
                            <tr>
                                <td>清理旧备份数</td>
                                <td><strong>{backup_summary.get('deleted_old_backups', 0)}</strong> 个</td>
                            </tr>
                            <tr>
                                <td>释放空间</td>
                                <td><strong>{backup_summary.get('freed_space_mb', 0)}</strong> MB</td>
                            </tr>
                        </tbody>
                    </table>
                    
                    <table class="stats-table">
                        <thead>
                            <tr>
                                <th colspan="2">📋 详细信息</th>
                            </tr>
                        </thead>
                        <tbody>
                            <tr>
                                <td>源目录</td>
                                <td>{backup_summary['source_dir']}</td>
                            </tr>
                            <tr>
                                <td>备份时间</td>
                                <td>{backup_summary['timestamp']}</td>
                            </tr>
                        </tbody>
                    </table>
                    
                    <div class="footer">
                        <p>此邮件由自动备份系统发送，请勿直接回复。</p>
                    </div>
                </div>
            </div>
        </body>
        </html>
        """
        
        self._send_email(subject, html_content)

    def send_backup_failure(self, task_name: str, error_message: str, backup_type: str = "未知") -> None:
        subject = f"[备份失败] {task_name} - {self._get_current_time()}"
        
        backup_type_cn = "全量" if backup_type == 'full' else "增量" if backup_type == 'incremental' else backup_type
        
        html_content = f"""
        <html>
        <head>
            <style>
                body {{
                    font-family: 'Microsoft YaHei', Arial, sans-serif;
                    padding: 20px;
                    background-color: #f5f5f5;
                }}
                .container {{
                    max-width: 700px;
                    margin: 0 auto;
                    background-color: white;
                    border-radius: 8px;
                    box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                }}
                .header {{
                    background-color: #f44336;
                    color: white;
                    padding: 20px;
                    border-radius: 8px 8px 0 0;
                }}
                .header h2 {{
                    margin: 0;
                    font-size: 20px;
                }}
                .content {{
                    padding: 25px;
                }}
                .summary-grid {{
                    display: grid;
                    grid-template-columns: 1fr 1fr;
                    gap: 15px;
                    margin-bottom: 20px;
                }}
                .summary-item {{
                    background-color: #ffebee;
                    padding: 15px;
                    border-radius: 6px;
                    border-left: 4px solid #f44336;
                }}
                .summary-item-label {{
                    font-size: 12px;
                    color: #666;
                    margin-bottom: 5px;
                }}
                .summary-item-value {{
                    font-size: 18px;
                    font-weight: bold;
                    color: #d32f2f;
                }}
                .error-box {{
                    background-color: #ffebee;
                    border: 1px solid #ffcdd2;
                    border-radius: 6px;
                    padding: 15px;
                    margin-top: 20px;
                }}
                .error-title {{
                    color: #d32f2f;
                    font-weight: bold;
                    margin-bottom: 10px;
                }}
                .error-message {{
                    color: #c62828;
                    font-family: 'Courier New', monospace;
                    background-color: #fff;
                    padding: 10px;
                    border-radius: 4px;
                    white-space: pre-wrap;
                    word-break: break-all;
                }}
                .footer {{
                    margin-top: 25px;
                    padding-top: 20px;
                    border-top: 1px solid #eee;
                    color: #999;
                    font-size: 12px;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h2>❌ 备份任务执行失败</h2>
                </div>
                <div class="content">
                    <div class="summary-grid">
                        <div class="summary-item">
                            <div class="summary-item-label">任务名称</div>
                            <div class="summary-item-value">{task_name}</div>
                        </div>
                        <div class="summary-item">
                            <div class="summary-item-label">备份类型</div>
                            <div class="summary-item-value">{backup_type_cn}备份</div>
                        </div>
                    </div>
                    
                    <div class="error-box">
                        <div class="error-title">⚠️ 错误信息</div>
                        <div class="error-message">{error_message}</div>
                    </div>
                    
                    <div class="footer">
                        <p>此邮件由自动备份系统发送，请勿直接回复。</p>
                        <p>请检查备份配置和网络连接后重试。</p>
                    </div>
                </div>
            </div>
        </body>
        </html>
        """
        
        self._send_email(subject, html_content)

    def _get_current_time(self) -> str:
        from datetime import datetime
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
