import os
import datetime
import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication

logger = logging.getLogger(__name__)


class BackupReporter:
    def __init__(self, config):
        self.config = config
        self.report_dir = os.path.join(config['backup']['local_dir'], 'reports')
        os.makedirs(self.report_dir, exist_ok=True)

    def generate_report(self, backup_files, upload_results, cleanup_results, verify_results):
        timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        report_file = os.path.join(self.report_dir, f'backup_report_{timestamp}.html')

        total_backups = len(backup_files)
        successful_uploads = sum(1 for r in upload_results if r['success'])
        cleaned_files = len(cleanup_results)
        verified_count = len(verify_results)
        verify_success = sum(1 for v in verify_results if v.get('success', False))

        html_content = f"""
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <title>数据库备份巡检报告</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; background-color: #f5f5f5; }}
        .header {{ background-color: #2c3e50; color: white; padding: 20px; border-radius: 5px; }}
        .section {{ background-color: white; margin: 20px 0; padding: 20px; border-radius: 5px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); }}
        .summary {{ display: flex; justify-content: space-around; flex-wrap: wrap; }}
        .summary-item {{ text-align: center; padding: 20px; background-color: #ecf0f1; border-radius: 5px; min-width: 150px; margin: 10px; }}
        .summary-value {{ font-size: 32px; font-weight: bold; color: #2c3e50; }}
        .success {{ color: #27ae60; }}
        .warning {{ color: #f39c12; }}
        .error {{ color: #e74c3c; }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 10px; }}
        th, td {{ padding: 12px; text-align: left; border-bottom: 1px solid #ddd; }}
        th {{ background-color: #34495e; color: white; }}
        tr:hover {{ background-color: #f5f5f5; }}
        .footer {{ text-align: center; color: #7f8c8d; margin-top: 30px; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>📊 数据库备份巡检报告</h1>
        <p>生成时间: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
    </div>

    <div class="section">
        <h2>📈 执行概览</h2>
        <div class="summary">
            <div class="summary-item">
                <div class="summary-value {'success' if total_backups > 0 else 'warning'}">{total_backups}</div>
                <div>备份文件数</div>
            </div>
            <div class="summary-item">
                <div class="summary-value {'success' if successful_uploads == len(upload_results) else 'error'}">{successful_uploads}/{len(upload_results)}</div>
                <div>OSS上传成功</div>
            </div>
            <div class="summary-item">
                <div class="summary-value">{cleaned_files}</div>
                <div>清理过期文件</div>
            </div>
            <div class="summary-item">
                <div class="summary-value {'success' if verify_success == verified_count else 'error'}">{verify_success}/{verified_count}</div>
                <div>备份验证成功</div>
            </div>
        </div>
    </div>

    <div class="section">
        <h2>📦 备份文件列表</h2>
        <table>
            <tr><th>文件名</th><th>大小</th><th>类型</th></tr>
            {"".join([f'<tr><td>{os.path.basename(f)}</td><td>{os.path.getsize(f)/1024/1024:.2f} MB</td><td>{"增量" if "incremental" in f or "binlog" in f else "全量"}</td></tr>' for f in backup_files])}
        </table>
    </div>

    <div class="section">
        <h2>✅ 备份验证结果</h2>
        <table>
            <tr><th>文件</th><th>状态</th><th>表数量</th><th>备注</th></tr>
            {"".join([f'<tr><td>{os.path.basename(v.get("file", ""))}</td><td class="{'success' if v.get('success') else 'error'}">{'成功' if v.get('success') else '失败'}</td><td>{v.get('table_count', 0)}</td><td>{v.get('error', '-')}</td></tr>' for v in verify_results])}
        </table>
    </div>

    <div class="section">
        <h2>🗑️ 清理的过期文件</h2>
        <table>
            <tr><th>文件</th></tr>
            {"".join([f'<tr><td>{f}</td></tr>' for f in cleanup_results]) or '<tr><td>无</td></tr>'}
        </table>
    </div>

    <div class="footer">
        <p>本报告由数据库备份巡检系统自动生成</p>
    </div>
</body>
</html>
        """

        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(html_content)

        logger.info(f"巡检报告生成成功: {report_file}")
        return report_file

    def send_email(self, report_file, backup_files, verify_results):
        email_config = self.config.get('email', {})
        if not email_config.get('smtp_host'):
            logger.warning("未配置邮件服务器，跳过邮件发送")
            return False

        try:
            msg = MIMEMultipart()
            msg['From'] = email_config.get('from', 'backup@example.com')
            msg['To'] = ', '.join(email_config.get('to', []))
            msg['Subject'] = f"[备份巡检] {datetime.datetime.now().strftime('%Y-%m-%d')} 数据库备份报告"

            success_rate = sum(1 for v in verify_results if v.get('success')) / max(len(verify_results), 1) * 100

            body = f"""
尊敬的管理员：

数据库备份巡检已完成，详情如下：

- 备份文件数: {len(backup_files)}
- 备份验证成功率: {success_rate:.1f}%
- 报告生成时间: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

详细报告请查看附件。

--
数据库备份巡检系统
            """

            msg.attach(MIMEText(body, 'plain', 'utf-8'))

            with open(report_file, 'rb') as f:
                part = MIMEApplication(f.read(), Name=os.path.basename(report_file))
                part['Content-Disposition'] = f'attachment; filename="{os.path.basename(report_file)}"'
                msg.attach(part)

            with smtplib.SMTP(email_config['smtp_host'], email_config.get('smtp_port', 25)) as server:
                if email_config.get('use_tls', False):
                    server.starttls()
                if email_config.get('username') and email_config.get('password'):
                    server.login(email_config['username'], email_config['password'])
                server.send_message(msg)

            logger.info("邮件发送成功")
            return True

        except Exception as e:
            logger.error(f"邮件发送失败: {str(e)}")
            return False
