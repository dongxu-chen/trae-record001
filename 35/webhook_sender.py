import os
import json
import time
import hmac
import hashlib
import logging
from urllib.parse import urlparse

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

class WebhookSender:
    def __init__(self):
        self._max_retries = int(os.getenv('WEBHOOK_MAX_RETRIES', '3'))
        self._retry_delay = float(os.getenv('WEBHOOK_RETRY_DELAY', '2.0'))
        self._timeout = int(os.getenv('WEBHOOK_TIMEOUT', '10'))
        self._secret = os.getenv('WEBHOOK_SECRET')
        self._allowed_domains = os.getenv('WEBHOOK_ALLOWED_DOMAINS', '').split(',')
        self._allowed_domains = [d.strip() for d in self._allowed_domains if d.strip()]
    
    def _validate_url(self, url):
        if not url:
            return False, 'URL is required'
        
        try:
            parsed = urlparse(url)
            if parsed.scheme not in ('http', 'https'):
                return False, 'Only http and https URLs are allowed'
            
            if self._allowed_domains:
                domain = parsed.netloc.split(':')[0]
                if not any(domain.endswith(allowed) or domain == allowed for allowed in self._allowed_domains):
                    return False, f'Domain {domain} is not in the allowed list'
            
            return True, None
        except Exception as e:
            return False, f'Invalid URL: {str(e)}'
    
    def _generate_signature(self, payload):
        if not self._secret:
            return None
        
        payload_bytes = json.dumps(payload, separators=(',', ':')).encode('utf-8')
        signature = hmac.new(
            self._secret.encode('utf-8'),
            payload_bytes,
            hashlib.sha256
        ).hexdigest()
        return signature
    
    def _build_headers(self, payload):
        headers = {
            'Content-Type': 'application/json',
            'User-Agent': 'ImageProcessor-Webhook/1.0',
            'X-Webhook-Timestamp': str(int(time.time()))
        }
        
        signature = self._generate_signature(payload)
        if signature:
            headers['X-Webhook-Signature'] = signature
        
        return headers
    
    def _send_single(self, url, payload):
        if not HAS_REQUESTS:
            logger.error('requests library is not installed')
            return False, 'requests library is not installed'
        
        headers = self._build_headers(payload)
        
        try:
            response = requests.post(
                url,
                json=payload,
                headers=headers,
                timeout=self._timeout
            )
            
            if 200 <= response.status_code < 300:
                return True, f'Success (status: {response.status_code})'
            else:
                return False, f'HTTP {response.status_code}: {response.text[:200]}'
        except requests.exceptions.Timeout:
            return False, 'Request timeout'
        except requests.exceptions.ConnectionError as e:
            return False, f'Connection error: {str(e)}'
        except requests.exceptions.RequestException as e:
            return False, f'Request failed: {str(e)}'
    
    def send(self, url, event_type, data, extra_headers=None, max_retries=None):
        if not url:
            logger.info('No webhook URL provided, skipping notification')
            return True
        
        valid, error = self._validate_url(url)
        if not valid:
            logger.warning(f'Invalid webhook URL: {error}')
            return False
        
        max_retries = max_retries if max_retries is not None else self._max_retries
        
        payload = {
            'event': event_type,
            'timestamp': time.time(),
            'data': data
        }
        
        last_error = None
        for attempt in range(max_retries + 1):
            success, message = self._send_single(url, payload)
            
            if success:
                logger.info(f'Webhook sent successfully to {url} (attempt {attempt + 1})')
                return True
            else:
                last_error = message
                logger.warning(
                    f'Webhook attempt {attempt + 1}/{max_retries + 1} failed for {url}: {message}'
                )
                
                if attempt < max_retries:
                    delay = self._retry_delay * (2 ** attempt)
                    logger.info(f'Retrying in {delay} seconds...')
                    time.sleep(delay)
        
        logger.error(f'All webhook retries failed for {url}: {last_error}')
        return False
    
    def send_task_started(self, url, task_id, task_type, extra=None):
        data = {
            'task_id': task_id,
            'task_type': task_type,
            'status': 'started'
        }
        if extra:
            data.update(extra)
        return self.send(url, 'task.started', data)
    
    def send_task_completed(self, url, task_id, task_type, result, extra=None):
        data = {
            'task_id': task_id,
            'task_type': task_type,
            'status': 'completed',
            'result': result
        }
        if extra:
            data.update(extra)
        return self.send(url, 'task.completed', data)
    
    def send_task_failed(self, url, task_id, task_type, error, extra=None):
        data = {
            'task_id': task_id,
            'task_type': task_type,
            'status': 'failed',
            'error': str(error)
        }
        if extra:
            data.update(extra)
        return self.send(url, 'task.failed', data)
    
    def send_task_progress(self, url, task_id, task_type, progress, step, extra=None):
        data = {
            'task_id': task_id,
            'task_type': task_type,
            'status': 'processing',
            'progress': progress,
            'step': step
        }
        if extra:
            data.update(extra)
        return self.send(url, 'task.progress', data)

webhook_sender = WebhookSender()

def validate_webhook_signature(request_body, signature, secret):
    if not secret or not signature:
        return False
    
    expected = hmac.new(
        secret.encode('utf-8'),
        request_body,
        hashlib.sha256
    ).hexdigest()
    
    return hmac.compare_digest(expected, signature)
