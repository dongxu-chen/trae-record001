import logging
import json
import requests
from typing import Dict, Optional


class TeamsIntegration:
    def __init__(self, webhook_url: str):
        self.webhook_url = webhook_url
        self.logger = logging.getLogger(__name__)

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
        
        theme_color = self._get_color_for_event(event_type, reason)
        
        card = {
            "type": "message",
            "attachments": [
                {
                    "contentType": "application/vnd.microsoft.card.adaptive",
                    "contentUrl": None,
                    "content": {
                        "type": "AdaptiveCard",
                        "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
                        "version": "1.3",
                        "themeColor": theme_color,
                        "body": [
                            {
                                "type": "TextBlock",
                                "size": "Large",
                                "weight": "Bolder",
                                "text": f"Kubernetes Event: {reason}" + (f" (x{count})" if count > 1 else "")
                            },
                            {
                                "type": "FactSet",
                                "facts": [
                                    {"title": "Type", "value": event_type},
                                    {"title": "Namespace", "value": namespace},
                                    {"title": "Pod", "value": name},
                                    {"title": "Time", "value": str(event_time)}
                                ]
                            },
                            {
                                "type": "TextBlock",
                                "text": "Message:",
                                "weight": "Bolder"
                            },
                            {
                                "type": "TextBlock",
                                "text": message,
                                "isSubtle": True,
                                "wrap": True
                            }
                        ]
                    }
                }
            ]
        }
        
        return self._send_card(card)

    def send_diagnosis(self, diagnosis: Dict, pod_name: str = None) -> bool:
        if not diagnosis:
            return False
        
        severity_emoji = {
            'high': '🔴',
            'medium': '🟠',
            'low': '🟡'
        }.get(diagnosis['severity'], '⚪')
        
        card = {
            "type": "message",
            "attachments": [
                {
                    "contentType": "application/vnd.microsoft.card.adaptive",
                    "content": {
                        "type": "AdaptiveCard",
                        "version": "1.3",
                        "body": [
                            {
                                "type": "TextBlock",
                                "size": "Large",
                                "weight": "Bolder",
                                "text": f"{severity_emoji} Fault Diagnosis: {diagnosis['name']}"
                            },
                            {
                                "type": "TextBlock",
                                "text": f"Description: {diagnosis['description']}",
                                "wrap": True
                            },
                            {
                                "type": "TextBlock",
                                "text": "Possible Causes:",
                                "weight": "Bolder"
                            },
                            {
                                "type": "TextBlock",
                                "text": "\n".join([f"- {c}" for c in diagnosis['causes']]),
                                "wrap": True
                            },
                            {
                                "type": "TextBlock",
                                "text": "Solutions:",
                                "weight": "Bolder"
                            },
                            {
                                "type": "TextBlock",
                                "text": "\n".join([f"- {s}" for s in diagnosis['solutions']]),
                                "wrap": True
                            },
                            {
                                "type": "TextBlock",
                                "text": "Commands:",
                                "weight": "Bolder"
                            },
                            {
                                "type": "TextBlock",
                                "text": "\n".join([f"`{cmd}`" for cmd in diagnosis['commands']]),
                                "wrap": True
                            }
                        ]
                    }
                }
            ]
        }
        
        return self._send_card(card)

    def send_daily_report(self, report: Dict) -> bool:
        card = {
            "type": "message",
            "attachments": [
                {
                    "contentType": "application/vnd.microsoft.card.adaptive",
                    "content": {
                        "type": "AdaptiveCard",
                        "version": "1.3",
                        "body": [
                            {
                                "type": "TextBlock",
                                "size": "Large",
                                "weight": "Bolder",
                                "text": f"📅 Kubernetes Daily Report - {report['date']}"
                            },
                            {
                                "type": "TextBlock",
                                "text": f"Period: {report['period']}",
                                "isSubtle": True
                            },
                            {
                                "type": "FactSet",
                                "facts": [
                                    {"title": "Total Events", "value": str(report['summary']['total_events'])},
                                    {"title": "Critical Events", "value": str(report['summary']['critical_events'])},
                                    {"title": "Warning Events", "value": str(report['summary']['warning_events'])},
                                    {"title": "Pod Restarts", "value": str(report['summary']['pod_restarts'])}
                                ]
                            },
                            {
                                "type": "TextBlock",
                                "text": "Namespace Details:",
                                "weight": "Bolder"
                            },
                            *self._build_namespace_details(report['namespaces'])
                        ]
                    }
                }
            ]
        }
        
        return self._send_card(card)

    def _build_namespace_details(self, namespaces: Dict) -> list:
        details = []
        for namespace, ns_report in namespaces.items():
            details.append({
                "type": "TextBlock",
                "weight": "Bolder",
                "text": namespace
            })
            
            pods_info = f"Pods: {ns_report['pods']['running']}/{ns_report['pods']['total']} running"
            details.append({"type": "TextBlock", "text": pods_info, "isSubtle": True})
            
            if ns_report['issues']:
                details.append({"type": "TextBlock", "text": "Issues:", "weight": "Bolder"})
                for issue in ns_report['issues']:
                    details.append({
                        "type": "TextBlock",
                        "text": f"⚠️ {issue['pod']}: {issue['message']}",
                        "isSubtle": True,
                        "wrap": True
                    })
        
        return details

    def _get_color_for_event(self, event_type: str, reason: str) -> str:
        if event_type == 'ERROR' or 'Failed' in reason or 'Error' in reason:
            return 'FF0000'
        elif event_type == 'WARNING' or 'Warning' in reason:
            return 'FFA500'
        elif event_type == 'NORMAL' or 'Started' in reason or 'Created' in reason:
            return '00FF00'
        return '888888'

    def _send_card(self, card: Dict) -> bool:
        try:
            response = requests.post(
                self.webhook_url,
                headers={'Content-Type': 'application/json'},
                data=json.dumps(card),
                timeout=10
            )
            
            if response.status_code == 200:
                self.logger.info("Successfully sent message to Teams")
                return True
            else:
                self.logger.error(f"Failed to send message to Teams: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error sending message to Teams: {e}")
            return False
