import pika
import json
import time
import threading
from typing import Callable, Dict, Optional
from config import config

class PriorityLevel:
    URGENT = 10
    HIGH = 7
    MEDIUM = 5
    LOW = 2

class ConsumerType:
    ASYNC_AUDIT = "async_audit"
    REVIEW = "review"

class RabbitMQClient:
    def __init__(self, worker_id: Optional[str] = None):
        self.connection = None
        self.channel = None
        self.worker_id = worker_id or f"worker_{threading.get_ident()}"
        self._lock = threading.Lock()
        self._connect()
    
    def _connect(self):
        credentials = pika.PlainCredentials(
            config.RABBITMQ_USER,
            config.RABBITMQ_PASSWORD
        )
        parameters = pika.ConnectionParameters(
            host=config.RABBITMQ_HOST,
            port=config.RABBITMQ_PORT,
            credentials=credentials,
            heartbeat=600,
            connection_attempts=5,
            retry_delay=5,
            blocked_connection_timeout=300
        )
        self.connection = pika.BlockingConnection(parameters)
        self.channel = self.connection.channel()
        
        self.channel.queue_declare(
            queue=config.ASYNC_TASK_QUEUE,
            durable=True,
            arguments={"x-max-priority": 10}
        )
        
        self.channel.queue_declare(
            queue=config.REVIEW_QUEUE_NAME,
            durable=True,
            arguments={"x-max-priority": 10}
        )
        
        self.channel.exchange_declare(
            exchange=config.RESULT_EXCHANGE,
            exchange_type='fanout',
            durable=True
        )
    
    def _ensure_connection(self):
        with self._lock:
            if not self.connection or self.connection.is_closed:
                self._connect()
            elif not self.channel or self.channel.is_closed:
                self.channel = self.connection.channel()
    
    def _get_priority(self, priority_str: str) -> int:
        priority_map = {
            "urgent": PriorityLevel.URGENT,
            "high": PriorityLevel.HIGH,
            "medium": PriorityLevel.MEDIUM,
            "low": PriorityLevel.LOW
        }
        return priority_map.get(priority_str.lower(), PriorityLevel.MEDIUM)
    
    def publish_async_task(self, task_data: Dict, priority: str = "medium") -> bool:
        try:
            self._ensure_connection()
            self.channel.basic_publish(
                exchange='',
                routing_key=config.ASYNC_TASK_QUEUE,
                body=json.dumps(task_data),
                properties=pika.BasicProperties(
                    delivery_mode=2,
                    content_type='application/json',
                    priority=self._get_priority(priority)
                )
            )
            return True
        except Exception as e:
            print(f"[{self.worker_id}] Failed to publish async task: {e}")
            return False
    
    def publish_review_task(self, review_data: Dict) -> bool:
        try:
            self._ensure_connection()
            priority = review_data.get("priority", "medium")
            self.channel.basic_publish(
                exchange='',
                routing_key=config.REVIEW_QUEUE_NAME,
                body=json.dumps(review_data),
                properties=pika.BasicProperties(
                    delivery_mode=2,
                    content_type='application/json',
                    priority=self._get_priority(priority)
                )
            )
            return True
        except Exception as e:
            print(f"[{self.worker_id}] Failed to publish review task: {e}")
            return False
    
    def publish_result(self, result_data: Dict) -> bool:
        try:
            self._ensure_connection()
            self.channel.basic_publish(
                exchange=config.RESULT_EXCHANGE,
                routing_key='',
                body=json.dumps(result_data),
                properties=pika.BasicProperties(
                    delivery_mode=1,
                    content_type='application/json'
                )
            )
            return True
        except Exception as e:
            print(f"[{self.worker_id}] Failed to publish result: {e}")
            return False
    
    def consume_tasks(self, queue_name: str, callback: Callable, 
                      prefetch_count: int = 1, auto_ack: bool = False):
        self._ensure_connection()
        
        def on_message(ch, method, properties, body):
            try:
                task_data = json.loads(body)
                task_data["_worker_id"] = self.worker_id
                callback(task_data)
                if not auto_ack:
                    ch.basic_ack(delivery_tag=method.delivery_tag)
            except Exception as e:
                print(f"[{self.worker_id}] Error processing task: {e}")
                if not auto_ack:
                    ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)
        
        self.channel.basic_qos(prefetch_count=prefetch_count)
        self.channel.basic_consume(
            queue=queue_name,
            on_message_callback=on_message,
            auto_ack=auto_ack,
            consumer_tag=self.worker_id
        )
        
        print(f"[{self.worker_id}] Started consuming from queue: {queue_name}")
        
        try:
            self.channel.start_consuming()
        except KeyboardInterrupt:
            print(f"[{self.worker_id}] Stopping consumer...")
            self.channel.stop_consuming()
    
    def consume_async_tasks(self, callback: Callable, prefetch_count: int = 1, 
                            auto_ack: bool = False):
        self.consume_tasks(config.ASYNC_TASK_QUEUE, callback, prefetch_count, auto_ack)
    
    def consume_review_tasks(self, callback: Callable, prefetch_count: int = 1,
                             auto_ack: bool = False):
        self.consume_tasks(config.REVIEW_QUEUE_NAME, callback, prefetch_count, auto_ack)
    
    def get_queue_size(self, queue_name: str) -> int:
        self._ensure_connection()
        queue = self.channel.queue_declare(queue=queue_name, durable=True, passive=True)
        return queue.method.message_count
    
    def get_async_queue_size(self) -> int:
        return self.get_queue_size(config.ASYNC_TASK_QUEUE)
    
    def get_review_queue_size(self) -> int:
        return self.get_queue_size(config.REVIEW_QUEUE_NAME)
    
    def purge_queue(self, queue_name: str) -> int:
        self._ensure_connection()
        result = self.channel.queue_purge(queue=queue_name)
        return result.method.message_count
    
    def close(self):
        if self.connection and not self.connection.is_closed:
            self.connection.close()

def create_mq_client(worker_id: Optional[str] = None) -> RabbitMQClient:
    return RabbitMQClient(worker_id)

mq_client = RabbitMQClient()
