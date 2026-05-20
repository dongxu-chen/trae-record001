import httpx
import json
import logging
from typing import Optional, Dict, Any
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class WebhookNotifier:
    @staticmethod
    def _serialize_data(data: Dict[str, Any]) -> Dict[str, Any]:
        serialized = {}
        for key, value in data.items():
            if isinstance(value, datetime):
                serialized[key] = value.isoformat()
            else:
                serialized[key] = value
        return serialized

    @classmethod
    async def send_notification(
        cls,
        url: str,
        method: str = "POST",
        headers: Optional[Dict[str, str]] = None,
        payload: Dict[str, Any] = None,
        timeout: int = 10
    ) -> tuple[bool, Optional[str]]:
        if headers is None:
            headers = {"Content-Type": "application/json"}
        
        if payload is None:
            payload = {}
        
        payload = cls._serialize_data(payload)
        
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                method = method.upper()
                if method == "GET":
                    response = await client.get(url, headers=headers, params=payload)
                else:
                    response = await client.request(
                        method,
                        url,
                        headers=headers,
                        json=payload
                    )
                
                if response.status_code >= 200 and response.status_code < 300:
                    logger.info(f"Webhook sent successfully to {url}")
                    return True, response.text
                else:
                    logger.error(f"Webhook failed with status {response.status_code}: {response.text}")
                    return False, response.text
                    
        except Exception as e:
            logger.error(f"Webhook error: {str(e)}")
            return False, str(e)

    @staticmethod
    def build_task_payload(task, task_log, status: str) -> Dict[str, Any]:
        return {
            "event": "task_execution",
            "task_id": task.id,
            "task_name": task.name,
            "status": status,
            "started_at": task_log.started_at,
            "completed_at": task_log.completed_at,
            "execution_time": task_log.execution_time,
            "retry_attempt": task_log.retry_attempt,
            "output": task_log.output,
            "error": task_log.error,
            "triggered_by": task_log.triggered_by,
            "timestamp": datetime.utcnow()
        }


def send_webhook_sync(
    url: str,
    method: str = "POST",
    headers: Optional[Dict[str, str]] = None,
    payload: Dict[str, Any] = None
):
    import asyncio
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop_loop(loop)
    
    return loop.run_until_complete(
        WebhookNotifier.send_notification(url, method, headers, payload)
    )