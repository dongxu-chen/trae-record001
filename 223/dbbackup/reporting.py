import os
import json
import logging
import smtplib
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage


class ReportGenerator:
    def __init__(self, config, db_type):
        self.config = config
        self.db_type = db_type
        self.logger = logging.getLogger('dbbackup')
        
        from .storage import StorageFactory
        self.storage = StorageFactory.get_storage(config.get_storage_config())
        
        backup_config = config.get_backup_config()
        self.temp_dir = backup_config.get('temp_dir', './temp')
        self.report_dir = backup_config.get('report_dir', './reports')
        
        os.makedirs(self.report_dir, exist_ok=True)
        
        self.report_config = config.config.get('reporting', {})
        self.email_config = self.report_config.get('email', {})

    def generate_weekly_report(self):
        self.logger.info("Generating weekly backup report...")
        
        end_date = datetime.now()
        start_date = end_date - timedelta(days=7)
        
        backups = self._get_backups_in_range(start_date, end_date)
        
        report_data = {
            'period': {
                'start': start_date.isoformat(),
                'end': end_date.isoformat()
            },
            'db_type': self.db_type,
            'summary': self._calculate_summary(backups, start_date, end_date),
            'backups': backups,
            'storage_status': self._get_storage_status(),
            'verification_results': self._get_verification_results(backups),
            'data_trend': self._calculate_data_trend(backups)
        }
        
        report_path = self._save_report(report_data)
        
        if self.email_config.get('enabled', False):
            self._send_email_report(report_data)
        
        return report_data, report_path

    def _get_backups_in_range(self, start_date, end_date):
        prefix = f"{self.db_type}/"
        files = self.storage.list_files(prefix)
        
        backups = []
        for f in files:
            if f.endswith('.json'):
                local_path = os.path.join(self.temp_dir, os.path.basename(f))
                try:
                    self.storage.download(f, local_path)
                    with open(local_path, 'r') as fp:
                        backup_info = json.load(fp)
                        backup_time = datetime.fromisoformat(backup_info['timestamp'])
                        if start_date <= backup_time <= end_date:
                            backups.append(backup_info)
                    os.remove(local_path)
                except:
                    pass
        
        return sorted(backups, key=lambda x: x['timestamp'])

    def _calculate_summary(self, backups, start_date, end_date):
        total_backups = len(backups)
        successful = sum(1 for b in backups if b.get('status') == 'completed')
        failed = total_backups - successful
        
        full_backups = [b for b in backups if b.get('strategy') == 'full']
        inc_backups = [b for b in backups if b.get('strategy') == 'incremental']
        
        total_data = sum(b.get('final_size', 0) for b in backups)
        avg_data = total_data / total_backups if total_backups > 0 else 0
        
        success_rate = (successful / total_backups * 100) if total_backups > 0 else 0
        
        return {
            'total_backups': total_backups,
            'successful': successful,
            'failed': failed,
            'success_rate': round(success_rate, 2),
            'full_backups': len(full_backups),
            'incremental_backups': len(inc_backups),
            'total_data_bytes': total_data,
            'avg_data_bytes': avg_data,
            'period_days': (end_date - start_date).days
        }

    def _get_storage_status(self):
        if hasattr(self.storage, 'health_check'):
            return self.storage.health_check()
        return []

    def _get_verification_results(self, backups):
        verified = 0
        passed = 0
        
        for backup in backups:
            if backup.get('verification'):
                verified += 1
                if backup['verification'].get('success'):
                    passed += 1
        
        return {
            'total_verified': verified,
            'passed': passed,
            'pass_rate': round(passed / verified * 100, 2) if verified > 0 else 0
        }

    def _calculate_data_trend(self, backups):
        if len(backups) < 2:
            return None
        
        sorted_backups = sorted(backups, key=lambda x: x['timestamp'])
        first_size = sorted_backups[0].get('final_size', 0)
        last_size = sorted_backups[-1].get('final_size', 0)
        
        change = last_size - first_size
        change_percent = (change / first_size * 100) if first_size > 0 else 0
        
        return {
            'start_size_bytes': first_size,
            'end_size_bytes': last_size,
            'change_bytes': change,
            'change_percent': round(change_percent, 2)
        }

    def _save_report(self, report_data):
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        report_path = os.path.join(self.report_dir, f'weekly_report_{self.db_type}_{timestamp}.json')
        
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(report_data, f, indent=2, ensure_ascii=False)
        
        return report_path

    def _format_size(self, bytes_val):
        if bytes_val < 1024:
            return f"{bytes_val} B"
        elif bytes_val < 1024 * 1024:
            return f"{bytes_val / 1024:.2f} KB"
        elif bytes_val < 1024 * 1024 * 1024:
            return f"{bytes_val / (1024 * 1024):.2f} MB"
        else:
            return f"{bytes_val / (1024 * 1024 * 1024):.2f} GB"

    def _generate_html_report(self, report_data):
        summary = report_data['summary']
        storage_status = report_data['storage_status']
        verification = report_data['verification_results']
        trend = report_data['data_trend']
        
        storage_rows = ''
        for status in storage_status:
            status_color = 'green' if status['success'] else 'red'
            storage_rows += f"""
            <tr>
                <td>{status['storage']}</td>
                <td style="color: {status_color}; font-weight: bold;">{'✓ OK' if status['success'] else '✗ Failed'}</td>
                <td>{status['message']}</td>
            </tr>
            """
        
        trend_html = ''
        if trend:
            change_color = 'green' if trend['change_bytes'] >= 0 else 'red'
            change_sign = '+' if trend['change_bytes'] >= 0 else ''
            trend_html = f"""
            <div style="background: #f8f9fa; padding: 15px; border-radius: 5px; margin-top: 20px;">
                <h3 style="margin-top: 0;">📊 数据量变化趋势</h3>
                <p>期初: <strong>{self._format_size(trend['start_size_bytes'])}</strong></p>
                <p>期末: <strong>{self._format_size(trend['end_size_bytes'])}</strong></p>
                <p style="color: {change_color};">变化: <strong>{change_sign}{self._format_size(trend['change_bytes'])}</strong> 
                   ({change_sign}{trend['change_percent']}%)</p>
            </div>
            """
        
        html = f"""
        <html>
        <head>
            <meta charset="utf-8">
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                          color: white; padding: 20px; border-radius: 10px; }}
                .summary {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 15px; margin: 20px 0; }}
                .card {{ background: #f8f9fa; padding: 15px; border-radius: 8px; text-align: center; }}
                .card-value {{ font-size: 24px; font-weight: bold; color: #667eea; }}
                .card-label {{ color: #666; font-size: 12px; }}
                table {{ width: 100%; border-collapse: collapse; margin: 15px 0; }}
                th, td {{ padding: 10px; text-align: left; border-bottom: 1px solid #ddd; }}
                th {{ background: #f8f9fa; font-weight: bold; }}
                .success {{ color: #28a745; }}
                .failed {{ color: #dc3545; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1 style="margin: 0;">📦 数据库备份周报</h1>
                <p style="margin: 5px 0 0 0; opacity: 0.9;">
                    {report_data['period']['start'][:10]} 至 {report_data['period']['end'][:10]}
                </p>
                <p style="margin: 5px 0 0 0; opacity: 0.9;">
                    数据库类型: {report_data['db_type'].upper()}
                </p>
            </div>
            
            <h2>📈 执行概览</h2>
            <div class="summary">
                <div class="card">
                    <div class="card-value">{summary['total_backups']}</div>
                    <div class="card-label">总备份次数</div>
                </div>
                <div class="card">
                    <div class="card-value {'success' if summary['success_rate'] >= 95 else 'failed'}">{summary['success_rate']}%</div>
                    <div class="card-label">成功率</div>
                </div>
                <div class="card">
                    <div class="card-value">{self._format_size(summary['total_data_bytes'])}</div>
                    <div class="card-label">总数据量</div>
                </div>
            </div>
            
            <h2>💾 备份统计</h2>
            <table>
                <tr>
                    <th>指标</th>
                    <th>数值</th>
                </tr>
                <tr>
                    <td>全量备份</td>
                    <td>{summary['full_backups']} 次</td>
                </tr>
                <tr>
                    <td>增量备份</td>
                    <td>{summary['incremental_backups']} 次</td>
                </tr>
                <tr>
                    <td>成功备份</td>
                    <td class="success">{summary['successful']} 次</td>
                </tr>
                <tr>
                    <td>失败备份</td>
                    <td class="failed">{summary['failed']} 次</td>
                </tr>
                <tr>
                    <td>平均备份大小</td>
                    <td>{self._format_size(summary['avg_data_bytes'])}</td>
                </tr>
            </table>
            
            <h2>✅ 验证结果</h2>
            <table>
                <tr>
                    <th>指标</th>
                    <th>数值</th>
                </tr>
                <tr>
                    <td>已验证备份</td>
                    <td>{verification['total_verified']} 次</td>
                </tr>
                <tr>
                    <td>验证通过</td>
                    <td class="success">{verification['passed']} 次</td>
                </tr>
                <tr>
                    <td>验证通过率</td>
                    <td class="{'success' if verification['pass_rate'] >= 95 else 'failed'}">{verification['pass_rate']}%</td>
                </tr>
            </table>
            
            <h2>☁️ 存储状态</h2>
            <table>
                <tr>
                    <th>存储服务</th>
                    <th>状态</th>
                    <th>消息</th>
                </tr>
                {storage_rows}
            </table>
            
            {trend_html}
            
            <div style="margin-top: 30px; padding-top: 20px; border-top: 1px solid #eee; color: #999; font-size: 12px;">
                <p>此邮件由数据库备份系统自动生成，请勿回复。</p>
                <p>生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            </div>
        </body>
        </html>
        """
        
        return html

    def _send_email_report(self, report_data):
        smtp_config = self.email_config.get('smtp', {})
        
        smtp_host = smtp_config.get('host')
        smtp_port = smtp_config.get('port', 587)
        smtp_user = smtp_config.get('user')
        smtp_password = smtp_config.get('password')
        use_tls = smtp_config.get('use_tls', True)
        
        from_addr = self.email_config.get('from', smtp_user)
        to_addrs = self.email_config.get('to', [])
        
        if not all([smtp_host, smtp_user, smtp_password, to_addrs]):
            self.logger.warning("Email configuration incomplete, skipping report email")
            return False
        
        subject = f"[备份周报] {report_data['db_type'].upper()} - {datetime.now().strftime('%Y-%m-%d')}"
        
        html_content = self._generate_html_report(report_data)
        
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = from_addr
        msg['To'] = ', '.join(to_addrs)
        
        html_part = MIMEText(html_content, 'html', 'utf-8')
        msg.attach(html_part)
        
        try:
            if use_tls:
                server = smtplib.SMTP(smtp_host, smtp_port)
                server.starttls()
            else:
                server = smtplib.SMTP_SSL(smtp_host, smtp_port)
            
            server.login(smtp_user, smtp_password)
            server.sendmail(from_addr, to_addrs, msg.as_string())
            server.quit()
            
            self.logger.info(f"Report email sent to: {to_addrs}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to send report email: {e}")
            return False
