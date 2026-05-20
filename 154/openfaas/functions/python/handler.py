import json
import os
import logging
import requests
from typing import Dict, Any

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class EventHandler:
    def __init__(self):
        self.slack_webhook = os.getenv("SLACK_WEBHOOK_URL")
        self.teams_webhook = os.getenv("TEAMS_WEBHOOK_URL")
        self.dingtalk_webhook = os.getenv("DINGTALK_WEBHOOK_URL")

    def handle(self, event: Dict[str, Any]) -> Dict[str, Any]:
        logger.info(f"Processing event: {event.get('object', {}).get('reason', 'Unknown')}")

        result = {
            "status": "processed",
            "event_type": event.get("type", "Unknown"),
            "notifications": []
        }

        try:
            event_obj = event.get("object", {})
            if not event_obj:
                raise ValueError("Invalid event format: missing 'object'")

            event_data = self._extract_event_data(event_obj)
            
            if self.slack_webhook:
                slack_result = self._send_slack_notification(event_data)
                result["notifications"].append({"channel": "slack", "status": slack_result})
            
            if self.teams_webhook:
                teams_result = self._send_teams_notification(event_data)
                result["notifications"].append({"channel": "teams", "status": teams_result})
            
            if self.dingtalk_webhook:
                dingtalk_result = self._send_dingtalk_notification(event_data)
                result["notifications"].append({"channel": "dingtalk", "status": dingtalk_result})

        except Exception as e:
            logger.error(f"Error processing event: {e}")
            result["status"] = "error"
            result["error"] = str(e)

        return result

    def _extract_event_data(self, event_obj: Dict[str, Any]) -> Dict[str, Any]:
        metadata = event_obj.get("metadata", {})
        involved = event_obj.get("involvedObject", {})
        
        return {
            "name": involved.get("name", metadata.get("name", "Unknown")),
            "namespace": involved.get("namespace", metadata.get("namespace", "default")),
            "kind": involved.get("kind", "Unknown"),
            "reason": event_obj.get("reason", "Unknown"),
            "message": event_obj.get("message", "No message"),
            "type": event_obj.get("type", "Normal"),
            "first_timestamp": event_obj.get("firstTimestamp", ""),
            "last_timestamp": event_obj.get("lastTimestamp", ""),
            "count": event_obj.get("count", 1),
            "source": event_obj.get("source", {}).get("component", "Unknown")
        }

    def _send_slack_notification(self, event_data: Dict[str, Any]) -> str:
        try:
            color = "#36a64f" if event_data["type"] == "Normal" else "#ff0000"
            
            blocks = [
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": f"Kubernetes Event: {event_data['reason']}"
                    }
                },
                {
                    "type": "section",
                    "fields": [
                        {"type": "mrkdwn", "text": f"*Type:*\n{event_data['type']}"},
                        {"type": "mrkdwn", "text": f"*Namespace:*\n{event_data['namespace']}"},
                        {"type": "mrkdwn", "text": f"*Name:*\n{event_data['name']}"},
                        {"type": "mrkdwn", "text": f"*Count:*\n{event_data['count']}"}
                    ]
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*Message:*\n```{event_data['message'][:500]}```"
                    }
                }
            ]

            payload = {
                "text": f"K8s Event: {event_data['reason']} - {event_data['name']}",
                "blocks": blocks
            }

            response = requests.post(self.slack_webhook, json=payload, timeout=10)
            response.raise_for_status()
            return "sent"
        except Exception as e:
            logger.error(f"Slack notification failed: {e}")
            return f"failed: {str(e)}"

    def _send_teams_notification(self, event_data: Dict[str, Any]) -> str:
        try:
            theme_color = "00FF00" if event_data["type"] == "Normal" else "FF0000"
            
            card = {
                "type": "message",
                "attachments": [{
                    "contentType": "application/vnd.microsoft.card.adaptive",
                    "content": {
                        "type": "AdaptiveCard",
                        "version": "1.2",
                        "themeColor": theme_color,
                        "body": [
                            {
                                "type": "TextBlock",
                                "size": "Large",
                                "weight": "Bolder",
                                "text": f"Kubernetes Event: {event_data['reason']}"
                            },
                            {
                                "type": "FactSet",
                                "facts": [
                                    {"title": "Type", "value": event_data["type"]},
                                    {"title": "Namespace", "value": event_data["namespace"]},
                                    {"title": "Name", "value": event_data["name"]},
                                    {"title": "Count", "value": str(event_data["count"])}
                                ]
                            },
                            {
                                "type": "TextBlock",
                                "text": event_data["message"][:500],
                                "wrap": True
                            }
                        ]
                    }
                }]
            }

            response = requests.post(self.teams_webhook, json=card, timeout=10)
            response.raise_for_status()
            return "sent"
        except Exception as e:
            logger.error(f"Teams notification failed: {e}")
            return f"failed: {str(e)}"

    def _send_dingtalk_notification(self, event_data: Dict[str, Any]) -> str:
        try:
            markdown_text = f"""
### Kubernetes Event: {event_data['reason']}

**Type**: {event_data['type']}
**Namespace**: {event_data['namespace']}
**Name**: {event_data['name']}
**Count**: {event_data['count']}

**Message**:
{event_data['message'][:500]}
            """

            payload = {
                "msgtype": "markdown",
                "markdown": {
                    "title": f"K8s Event: {event_data['reason']}",
                    "text": markdown_text.strip()
                }
            }

            response = requests.post(self.dingtalk_webhook, json=payload, timeout=10)
            response.raise_for_status()
            return "sent"
        except Exception as e:
            logger.error(f"DingTalk notification failed: {e}")
            return f"failed: {str(e)}"


handler = EventHandler()


def handle(event, context):
    try:
        if isinstance(event, str):
            event_data = json.loads(event)
        elif isinstance(event, dict):
            event_data = event
        else:
            event_data = json.loads(event.body.decode())
        
        result = handler.handle(event_data)
        
        return {
            "statusCode": 200,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps(result)
        }
    except Exception as e:
        logger.error(f"Handler error: {e}")
        return {
            "statusCode": 500,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"status": "error", "error": str(e)})
        }
