import os
import json
import smtplib
import requests
from typing import List, Dict, Optional
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from dotenv import load_dotenv

load_dotenv()


class ChannelType(Enum):
    WECHAT_WORK = "wechat_work"
    EMAIL = "email"
    SMS = "sms"


@dataclass
class AlertConfig:
    enabled_channels: List[str] = field(default_factory=list)
    wechat_webhook_url: str = ""
    email_smtp_server: str = ""
    email_smtp_port: int = 587
    email_sender: str = ""
    email_password: str = ""
    email_recipients: List[str] = field(default_factory=list)
    sms_api_url: str = ""
    sms_api_key: str = ""
    sms_recipients: List[str] = field(default_factory=list)
    min_alert_severity: str = "medium"


class AlertChannel(ABC):
    @abstractmethod
    def send(self, alert: Dict, context: Dict = None) -> bool:
        pass
    
    @abstractmethod
    def is_enabled(self) -> bool:
        pass


class WeChatWorkChannel(AlertChannel):
    def __init__(self, webhook_url: str):
        self.webhook_url = webhook_url
    
    def is_enabled(self) -> bool:
        return bool(self.webhook_url)
    
    def send(self, alert: Dict, context: Dict = None) -> bool:
        if not self.is_enabled():
            return False
        
        severity_emoji = {
            'high': '🔴',
            'medium': '🟡',
            'low': '🟢'
        }.get(alert.get('severity', 'medium'), '⚪')
        
        message = f"""
{severity_emoji} 客户对话告警通知

**告警类型**: {alert.get('alert_type', 'unknown')}
**严重级别**: {alert.get('severity', 'medium')}
**消息内容**: {alert.get('message', '')}
**置信度**: {alert.get('confidence', 0):.2%}
**对话轮次**: 第{alert.get('turn_index', 0)}轮
        """
        
        if context:
            message += f"\n**会话ID**: {context.get('session_id', 'N/A')}"
            if context.get('customer_message'):
                message += f"\n**客户消息**: {context.get('customer_message')[:100]}..."
        
        payload = {
            "msgtype": "markdown",
            "markdown": {
                "content": message.strip()
            }
        }
        
        try:
            response = requests.post(self.webhook_url, json=payload, timeout=10)
            return response.status_code == 200 and response.json().get('errcode') == 0
        except Exception as e:
            print(f"WeChat Work alert failed: {e}")
            return False


class EmailChannel(AlertChannel):
    def __init__(self, smtp_server: str, smtp_port: int, sender: str, 
                 password: str, recipients: List[str]):
        self.smtp_server = smtp_server
        self.smtp_port = smtp_port
        self.sender = sender
        self.password = password
        self.recipients = recipients
    
    def is_enabled(self) -> bool:
        return all([
            self.smtp_server,
            self.sender,
            self.password,
            self.recipients
        ])
    
    def send(self, alert: Dict, context: Dict = None) -> bool:
        if not self.is_enabled():
            return False
        
        severity_map = {
            'high': '【严重】',
            'medium': '【中等】',
            'low': '【轻微】'
        }
        
        subject = f"{severity_map.get(alert.get('severity', 'medium'), '')}客户对话情感告警"
        
        html_content = f"""
<html>
<body style="font-family: Arial, sans-serif; padding: 20px;">
    <h2 style="color: {'#dc3545' if alert.get('severity') == 'high' else '#ffc107'};">
        ⚠️ 客户对话告警通知
    </h2>
    <table style="border-collapse: collapse; width: 100%; max-width: 600px;">
        <tr style="background: #f8f9fa;">
            <td style="padding: 10px; border: 1px solid #dee2e6;"><strong>告警类型</strong></td>
            <td style="padding: 10px; border: 1px solid #dee2e6;">{alert.get('alert_type', 'unknown')}</td>
        </tr>
        <tr>
            <td style="padding: 10px; border: 1px solid #dee2e6;"><strong>严重级别</strong></td>
            <td style="padding: 10px; border: 1px solid #dee2e6;">{alert.get('severity', 'medium')}</td>
        </tr>
        <tr style="background: #f8f9fa;">
            <td style="padding: 10px; border: 1px solid #dee2e6;"><strong>告警消息</strong></td>
            <td style="padding: 10px; border: 1px solid #dee2e6;">{alert.get('message', '')}</td>
        </tr>
        <tr>
            <td style="padding: 10px; border: 1px solid #dee2e6;"><strong>置信度</strong></td>
            <td style="padding: 10px; border: 1px solid #dee2e6;">{alert.get('confidence', 0):.2%}</td>
        </tr>
    </table>
</body>
</html>
        """
        
        try:
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = self.sender
            msg['To'] = ', '.join(self.recipients)
            
            html_part = MIMEText(html_content, 'html')
            msg.attach(html_part)
            
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.sender, self.password)
                server.send_message(msg)
            
            return True
        except Exception as e:
            print(f"Email alert failed: {e}")
            return False


class SMSChannel(AlertChannel):
    def __init__(self, api_url: str, api_key: str, recipients: List[str]):
        self.api_url = api_url
        self.api_key = api_key
        self.recipients = recipients
    
    def is_enabled(self) -> bool:
        return all([
            self.api_url,
            self.api_key,
            self.recipients
        ])
    
    def send(self, alert: Dict, context: Dict = None) -> bool:
        if not self.is_enabled():
            return False
        
        severity_text = {
            'high': '严重',
            'medium': '中等',
            'low': '轻微'
        }.get(alert.get('severity', 'medium'), '未知')
        
        message = f"【客户对话告警】{severity_text}: {alert.get('message', '')} 请及时处理。"
        
        try:
            for recipient in self.recipients:
                payload = {
                    'api_key': self.api_key,
                    'phone': recipient,
                    'message': message
                }
                response = requests.post(self.api_url, json=payload, timeout=10)
                if response.status_code != 200:
                    print(f"SMS failed for {recipient}")
            
            return True
        except Exception as e:
            print(f"SMS alert failed: {e}")
            return False


class MultiChannelAlertManager:
    def __init__(self, config: AlertConfig = None):
        self.config = config or AlertConfig()
        self.channels: Dict[str, AlertChannel] = {}
        self._init_channels()
    
    def _init_channels(self):
        if ChannelType.WECHAT_WORK.value in self.config.enabled_channels:
            self.channels[ChannelType.WECHAT_WORK.value] = WeChatWorkChannel(
                self.config.wechat_webhook_url
            )
        
        if ChannelType.EMAIL.value in self.config.enabled_channels:
            self.channels[ChannelType.EMAIL.value] = EmailChannel(
                self.config.email_smtp_server,
                self.config.email_smtp_port,
                self.config.email_sender,
                self.config.email_password,
                self.config.email_recipients
            )
        
        if ChannelType.SMS.value in self.config.enabled_channels:
            self.channels[ChannelType.SMS.value] = SMSChannel(
                self.config.sms_api_url,
                self.config.sms_api_key,
                self.config.sms_recipients
            )
    
    def update_config(self, config: AlertConfig):
        self.config = config
        self._init_channels()
    
    def get_enabled_channels(self) -> List[str]:
        return [name for name, channel in self.channels.items() if channel.is_enabled()]
    
    def send_alert(self, alert: Dict, context: Dict = None) -> Dict[str, bool]:
        severity_order = {'low': 1, 'medium': 2, 'high': 3}
        min_severity = self.config.min_alert_severity
        
        if severity_order.get(alert.get('severity', 'medium'), 2) < severity_order.get(min_severity, 2):
            return {}
        
        results = {}
        for name, channel in self.channels.items():
            if channel.is_enabled():
                try:
                    results[name] = channel.send(alert, context)
                except Exception as e:
                    print(f"Channel {name} error: {e}")
                    results[name] = False
        
        return results
    
    def test_channel(self, channel_name: str) -> bool:
        if channel_name not in self.channels:
            return False
        
        test_alert = {
            'alert_type': 'test',
            'severity': 'low',
            'message': '这是一条测试告警消息',
            'confidence': 1.0,
            'turn_index': 0
        }
        
        channel = self.channels[channel_name]
        if channel.is_enabled():
            return channel.send(test_alert, {'session_id': 'test-session'})
        
        return False


def create_alert_config_from_env() -> AlertConfig:
    config = AlertConfig()
    
    enabled_channels = os.getenv('ALERT_CHANNELS', '')
    if enabled_channels:
        config.enabled_channels = [c.strip() for c in enabled_channels.split(',')]
    
    config.wechat_webhook_url = os.getenv('WECHAT_WEBHOOK_URL', '')
    config.email_smtp_server = os.getenv('EMAIL_SMTP_SERVER', '')
    config.email_smtp_port = int(os.getenv('EMAIL_SMTP_PORT', '587'))
    config.email_sender = os.getenv('EMAIL_SENDER', '')
    config.email_password = os.getenv('EMAIL_PASSWORD', '')
    
    email_recipients = os.getenv('EMAIL_RECIPIENTS', '')
    if email_recipients:
        config.email_recipients = [e.strip() for e in email_recipients.split(',')]
    
    config.sms_api_url = os.getenv('SMS_API_URL', '')
    config.sms_api_key = os.getenv('SMS_API_KEY', '')
    
    sms_recipients = os.getenv('SMS_RECIPIENTS', '')
    if sms_recipients:
        config.sms_recipients = [s.strip() for s in sms_recipients.split(',')]
    
    config.min_alert_severity = os.getenv('MIN_ALERT_SEVERITY', 'medium')
    
    return config


def create_multi_channel_alert_manager() -> MultiChannelAlertManager:
    config = create_alert_config_from_env()
    return MultiChannelAlertManager(config)
