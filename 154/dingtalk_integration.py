import logging
import json
import requests
import hashlib
import hmac
import base64
import time
import urllib.parse
from typing import Dict, Optional


class DingTalkIntegration:
    def __init__(self, webhook_url: str, secret: str = None):
        self.webhook_url = webhook_url
        self.secret = secret
        self.logger = logging.getLogger(__name__)

    def _sign(self, timestamp: str) -> str:
        if not self.secret:
            return None
        
        string_to_sign = f"{timestamp}\n{self.secret}"
        hmac_code = hmac.new(
            self.secret.encode('utf-8'),
            string_to_sign.encode('utf-8'),
            digestmod=hashlib.sha256
        ).digest()
        
        sign = base64.b64encode(hmac_code).decode('utf-8')
        return urllib.parse.quote(sign)

    def _get_url(self) -> str:
        if self.secret:
            timestamp = str(round(time.time() * 1000))
            sign = self._sign(timestamp)
            return f"{self.webhook_url}&timestamp={timestamp}&sign={sign}"
        return self.webhook_url

    def send_event(self, event: Dict, count: int = 1) -> bool:
        event_type = event.get('type', 'UNKNOWN')
        obj = event.get('object', {})
        metadata = obj.get('metadata', {})
        namespace = metadata.get('namespace', 'default')
        name = obj.get('involvedObject', {}).get('name', '')
        if not name:
            name = metadata.get('name', 'unknown')
        
        reason = obj.get('reason', 'Unknown')
        message = obj.get('message', 'No message')
        event_time = obj.get('lastTimestamp', obj.get('firstTimestamp', 'Unknown time'))
        
        title = f"Kubernetes Event: {reason}" + (f" (x{count})" if count > 1 else "")
        
        text = f"""### {title}

**Type**: {event_type}
**Namespace**: {namespace}
**Pod**: {name}
**Time**: {event_time}

**Message**:
{message}
"""
        
        return self._send_markdown(title, text)

    def send_diagnosis(self, diagnosis: Dict, pod_name: str = None) -> bool:
        if not diagnosis:
            return False
        
        severity_emoji = {
            'high': '🔴',
            'medium': '🟠',
            'low': '🟡'
        }.get(diagnosis['severity'], '⚪')
        
        title = f"{severity_emoji} Fault Diagnosis: {diagnosis['name']}"
        
        causes_text = "\n".join([f"- {c}" for c in diagnosis['causes']])
        solutions_text = "\n".join([f"- {s}" for s in diagnosis['solutions']])
        commands_text = "\n".join([f"`{cmd}`" for cmd in diagnosis['commands']])
        
        text = f"""### {title}

**Description**: {diagnosis['description']}

**Possible Causes**:
{causes_text}

**Solutions**:
{solutions_text}

**Commands**:
{commands_text}
"""
        
        return self._send_markdown(title, text)

    def send_daily_report(self, report: Dict) -> bool:
        title = f"📅 Kubernetes Daily Report - {report['date']}"
        
        text = f"""### {title}

**Period**: {report['period']}

**Summary**:
- Total Events: {report['summary']['total_events']}
- Critical Events: {report['summary']['critical_events']}
- Warning Events: {report['summary']['warning_events']}
- Pod Restarts: {report['summary']['pod_restarts']}

**Namespace Details**:
"""
        
        for namespace, ns_report in report['namespaces'].items():
            text += f"\n**{namespace}**: \n"
            text += f"- Pods: {ns_report['pods']['running']}/{ns_report['pods']['total']} running\n"
            text += f"- Restarts: {ns_report['pod_restarts']}\n"
            
            if ns_report['issues']:
                text += "- Issues:\n"
                for issue in ns_report['issues']:
                    text += f"  ⚠️ {issue['pod']}: {issue['message']}\n"
        
        text += "\n⚠️ Please handle issues promptly!"
        
        return self._send_markdown(title, text)

    def _send_markdown(self, title: str, text: str) -> bool:
        data = {
            "msgtype": "markdown",
            "markdown": {
                "title": title,
                "text": text
            }
        }
        
        return self._send_request(data)

    def _send_request(self, data: Dict) -> bool:
        try:
            url = self._get_url()
            response = requests.post(
                url,
                headers={'Content-Type': 'application/json'},
                data=json.dumps(data),
                timeout=10
            )
            
            result = response.json()
            if result.get('errcode') == 0:
                self.logger.info("Successfully sent message to DingTalk")
                return True
            else:
                self.logger.error(f"Failed to send message to DingTalk: {result}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error sending message to DingTalk: {e}")
            return False
