"""
告警通知模块
支持邮件、Webhook等多种通知方式
"""
import json
import smtplib
import hashlib
import hmac
import base64
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from typing import List, Dict, Optional

import requests
from loguru import logger

from config import ALERT_CONFIG


class Notifier:
    def __init__(self, config=None):
        if config is None:
            config = ALERT_CONFIG
        self.config = config
        self.enabled = config.get('enable', True)
        self.email_config = config.get('email', {})
        self.webhook_config = config.get('webhook', {})

    def send_alert(self, alert_data: dict):
        if not self.enabled:
            logger.debug("告警功能已禁用")
            return

        results = {}

        if self.email_config.get('sender') and self.email_config.get('receivers'):
            try:
                self._send_email(alert_data)
                results['email'] = 'success'
            except Exception as e:
                logger.error(f"邮件发送失败: {e}")
                results['email'] = f'failed: {e}'

        if self.webhook_config.get('url'):
            try:
                self._send_webhook(alert_data)
                results['webhook'] = 'success'
            except Exception as e:
                logger.error(f"Webhook发送失败: {e}")
                results['webhook'] = f'failed: {e}'

        return results

    def send_batch_alerts(self, alerts: List[dict]):
        results = []
        for alert in alerts:
            result = self.send_alert(alert)
            results.append({
                'alert': alert,
                'results': result,
            })
        return results

    def _send_email(self, alert_data: dict):
        msg = MIMEMultipart()
        msg['From'] = self.email_config['sender']
        msg['To'] = ', '.join(self.email_config['receivers'])
        msg['Subject'] = self._build_email_subject(alert_data)

        body = self._build_email_body(alert_data)
        msg.attach(MIMEText(body, 'html', 'utf-8'))

        if self.email_config.get('use_ssl', True):
            server = smtplib.SMTP_SSL(
                self.email_config['smtp_server'],
                self.email_config['smtp_port'],
            )
        else:
            server = smtplib.SMTP(
                self.email_config['smtp_server'],
                self.email_config['smtp_port'],
            )
            server.starttls()

        try:
            server.login(self.email_config['sender'], self.email_config['password'])
            server.send_message(msg)
            logger.info(f"邮件告警已发送: {alert_data.get('message', '')}")
        finally:
            server.quit()

    def _build_email_subject(self, alert_data: dict) -> str:
        alert_type = alert_data.get('alert_type', '')
        type_names = {
            'price_drop': '价格下跌',
            'price_rise': '价格上涨',
            'stock_out': '商品缺货',
            'promotion': '促销活动',
            'new_product': '新品上架',
        }
        type_name = type_names.get(alert_type, alert_type)
        return f"[价格监控] {type_name} - {alert_data.get('product_name', '')}"

    def _build_email_body(self, alert_data: dict) -> str:
        html = f"""
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <div style="background-color: #f8f9fa; padding: 20px; border-radius: 8px;">
                <h2 style="color: #333; margin-top: 0;">价格监控告警</h2>
                <div style="background-color: white; padding: 16px; border-radius: 4px; margin-top: 16px;">
                    <p><strong>告警类型:</strong> {alert_data.get('alert_type', '')}</p>
                    <p><strong>商品名称:</strong> {alert_data.get('product_name', '')}</p>
                    <p><strong>来源:</strong> {alert_data.get('source', '')}</p>
        """

        if alert_data.get('old_price') is not None:
            html += f"<p><strong>原价:</strong> ¥{alert_data['old_price']}</p>"
        if alert_data.get('new_price') is not None:
            html += f"<p><strong>现价:</strong> ¥{alert_data['new_price']}</p>"
        if alert_data.get('change_ratio') is not None:
            change = alert_data['change_ratio'] * 100
            color = '#28a745' if change < 0 else '#dc3545'
            html += f"<p><strong>变动幅度:</strong> <span style='color: {color};'>{change:+.1f}%</span></p>"

        if alert_data.get('promotion_info'):
            html += f"<p><strong>促销信息:</strong> {alert_data['promotion_info']}</p>"

        html += f"""
                    <p><strong>详细信息:</strong> {alert_data.get('message', '')}</p>
                    <p style="color: #999; font-size: 12px;">
                        告警时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
                    </p>
                </div>
            </div>
        </div>
        """
        return html

    def _send_webhook(self, alert_data: dict):
        url = self.webhook_config['url']
        secret = self.webhook_config.get('secret', '')

        payload = {
            'msgtype': 'text',
            'text': {
                'content': self._build_webhook_message(alert_data),
            },
            'alert_type': alert_data.get('alert_type', ''),
            'product_id': alert_data.get('product_id', ''),
            'product_name': alert_data.get('product_name', ''),
            'source': alert_data.get('source', ''),
        }

        headers = {'Content-Type': 'application/json'}

        if secret:
            timestamp = str(int(datetime.now().timestamp() * 1000))
            sign_str = f"{timestamp}\n{secret}"
            hmac_code = hmac.new(
                secret.encode(),
                sign_str.encode(),
                digestmod=hashlib.sha256,
            ).digest()
            sign = base64.b64encode(hmac_code).decode('utf-8')
            payload['timestamp'] = timestamp
            payload['sign'] = sign

        resp = requests.post(url, json=payload, headers=headers, timeout=10)
        resp.raise_for_status()
        logger.info(f"Webhook告警已发送: {alert_data.get('message', '')}")

    def _build_webhook_message(self, alert_data: dict) -> str:
        lines = [
            f"【价格监控告警】",
            f"类型: {alert_data.get('alert_type', '')}",
            f"商品: {alert_data.get('product_name', '')}",
            f"来源: {alert_data.get('source', '')}",
        ]

        if alert_data.get('old_price') is not None:
            lines.append(f"原价: ¥{alert_data['old_price']}")
        if alert_data.get('new_price') is not None:
            lines.append(f"现价: ¥{alert_data['new_price']}")
        if alert_data.get('change_ratio') is not None:
            change = alert_data['change_ratio'] * 100
            lines.append(f"幅度: {change:+.1f}%")

        lines.append(f"详情: {alert_data.get('message', '')}")
        lines.append(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        return '\n'.join(lines)


notifier: Optional[Notifier] = None


def get_notifier():
    global notifier
    if notifier is None:
        notifier = Notifier()
    return notifier