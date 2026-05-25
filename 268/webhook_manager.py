import requests
import json
import threading
from typing import Dict, List, Optional, Callable
from datetime import datetime
from enum import Enum


class WebhookEventType(Enum):
    REQUEST_CREATED = "request.created"
    REQUEST_APPROVED = "request.approved"
    REQUEST_REJECTED = "request.rejected"
    REQUEST_EXECUTED = "request.executed"
    OPTIMIZATION_COMPLETED = "optimization.completed"
    ANALYSIS_COMPLETED = "analysis.completed"


class WebhookManager:
    def __init__(self, config: Dict = None):
        self.config = config or {}
        self.webhooks = self.config.get('webhooks', [])
        self.timeout = self.config.get('timeout', 10)
        self.max_retries = self.config.get('max_retries', 3)
        self.enabled = self.config.get('enabled', True)
        self.auto_execute_on_approve = self.config.get('auto_execute_on_approve', True)

    def add_webhook(self, url: str, events: List[str] = None, 
                    secret: str = None, method: str = 'POST'):
        webhook = {
            'url': url,
            'events': events or [e.value for e in WebhookEventType],
            'secret': secret,
            'method': method.upper(),
            'enabled': True
        }
        self.webhooks.append(webhook)
        return webhook

    def remove_webhook(self, url: str):
        self.webhooks = [w for w in self.webhooks if w['url'] != url]

    def _generate_payload(self, event_type: WebhookEventType, 
                           data: Dict, 
                           timestamp: datetime = None) -> Dict:
        return {
            'event_type': event_type.value,
            'timestamp': (timestamp or datetime.now()).isoformat(),
            'data': data,
            'version': '1.0'
        }

    def _send_webhook(self, webhook: Dict, payload: Dict):
        if not webhook.get('enabled', True):
            return False, 'Webhook disabled'

        url = webhook['url']
        method = webhook.get('method', 'POST')
        
        headers = {
            'Content-Type': 'application/json',
            'X-Webhook-Event': payload['event_type'],
            'X-Webhook-Timestamp': payload['timestamp']
        }
        
        if webhook.get('secret'):
            import hashlib
            import hmac
            signature = hmac.new(
                webhook['secret'].encode(),
                json.dumps(payload).encode(),
                hashlib.sha256
            ).hexdigest()
            headers['X-Webhook-Signature'] = signature

        for attempt in range(self.max_retries):
            try:
                if method == 'POST':
                    response = requests.post(
                        url, 
                        json=payload, 
                        headers=headers,
                        timeout=self.timeout
                    )
                elif method == 'GET':
                    response = requests.get(
                        url, 
                        params=payload,
                        headers=headers,
                        timeout=self.timeout
                    )
                else:
                    return False, f'Unsupported method: {method}'

                if 200 <= response.status_code < 300:
                    return True, f'Success (status: {response.status_code})'
                else:
                    print(f"Webhook attempt {attempt + 1} failed: {response.status_code}")
            except Exception as e:
                print(f"Webhook attempt {attempt + 1} error: {e}")

        return False, f'Failed after {self.max_retries} retries'

    def trigger_event(self, event_type: WebhookEventType, data: Dict, 
                       async_mode: bool = True) -> Dict:
        if not self.enabled:
            return {'status': 'disabled', 'triggered': 0}

        payload = self._generate_payload(event_type, data)
        matching_webhooks = [
            w for w in self.webhooks 
            if event_type.value in w.get('events', [])
        ]

        results = []
        
        def send_all():
            for webhook in matching_webhooks:
                success, message = self._send_webhook(webhook, payload)
                results.append({
                    'url': webhook['url'],
                    'success': success,
                    'message': message
                })

        if async_mode:
            thread = threading.Thread(target=send_all)
            thread.start()
            return {
                'status': 'async',
                'event_type': event_type.value,
                'webhook_count': len(matching_webhooks)
            }
        else:
            send_all()
            return {
                'status': 'sync',
                'event_type': event_type.value,
                'webhook_count': len(matching_webhooks),
                'results': results
            }

    def on_request_approved(self, request_data: Dict, 
                             execute_callback: Callable = None) -> Dict:
        result = self.trigger_event(WebhookEventType.REQUEST_APPROVED, request_data)
        
        if self.auto_execute_on_approve and execute_callback:
            try:
                execute_result = execute_callback(request_data['request_id'])
                if execute_result:
                    self.trigger_event(WebhookEventType.REQUEST_EXECUTED, {
                        'request_id': request_data['request_id'],
                        'execute_result': 'success'
                    })
            except Exception as e:
                print(f"Auto-execute failed: {e}")
        
        return result

    def test_webhook(self, url: str, method: str = 'POST') -> Dict:
        test_data = {
            'test': True,
            'message': 'Webhook test from Cloud Cost Optimizer'
        }
        webhook = {'url': url, 'method': method, 'enabled': True}
        payload = self._generate_payload(WebhookEventType.REQUEST_CREATED, test_data)
        success, message = self._send_webhook(webhook, payload)
        return {'success': success, 'message': message}
