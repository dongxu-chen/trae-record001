import json
import logging
import time
from typing import Dict, Optional
from datetime import datetime

try:
    from kafka import KafkaProducer
    from kafka.errors import KafkaError
    KAFKA_AVAILABLE = True
except ImportError:
    KAFKA_AVAILABLE = False
    logging.warning("kafka-python not installed. Using mock producer.")

from config import config

logger = logging.getLogger(__name__)


class BehaviorProducer:
    def __init__(self, brokers: list = None, topic: str = None):
        self.brokers = brokers or config.KAFKA_BROKERS
        self.topic = topic or config.KAFKA_TOPIC_BEHAVIOR
        self.producer = None
        self._connect()

    def _connect(self):
        if not KAFKA_AVAILABLE:
            logger.info("Using mock Kafka producer")
            self.producer = None
            self._mock_messages = []
            return

        try:
            self.producer = KafkaProducer(
                bootstrap_servers=self.brokers,
                value_serializer=lambda v: json.dumps(v, ensure_ascii=False).encode('utf-8'),
                key_serializer=lambda k: str(k).encode('utf-8'),
                retries=3,
                acks='all',
                linger_ms=10,
                batch_size=16384,
                compression_type='gzip',
                request_timeout_ms=30000,
                max_in_flight_requests_per_connection=5
            )
            logger.info(f"Connected to Kafka brokers: {self.brokers}")
        except Exception as e:
            logger.warning(f"Failed to connect to Kafka: {e}. Using mock producer.")
            self.producer = None
            self._mock_messages = []

    def send_behavior(
        self,
        user_id: int,
        news_id: int,
        behavior_type: str,
        duration: float = 0.0,
        timestamp: Optional[datetime] = None,
        extra: Optional[Dict] = None
    ) -> bool:
        timestamp = timestamp or datetime.now()

        message = {
            'user_id': user_id,
            'news_id': news_id,
            'behavior_type': behavior_type,
            'duration': duration,
            'timestamp': timestamp.isoformat(),
            'extra': extra or {}
        }

        return self._send(str(user_id), message)

    def _send(self, key: str, message: Dict) -> bool:
        if self.producer:
            try:
                future = self.producer.send(
                    self.topic,
                    key=key,
                    value=message
                )
                future.add_callback(self._on_send_success)
                future.add_errback(self._on_send_error)
                return True
            except KafkaError as e:
                logger.error(f"Failed to send message to Kafka: {e}")
                self._mock_messages.append(message)
                return False
        else:
            self._mock_messages.append(message)
            logger.debug(f"Mock send: {message}")
            return True

    def _on_send_success(self, record_metadata):
        logger.debug(
            f"Message sent to topic {record_metadata.topic}, "
            f"partition {record_metadata.partition}, "
            f"offset {record_metadata.offset}"
        )

    def _on_send_error(self, exception):
        logger.error(f"Error sending message: {exception}")

    def send_batch(self, messages: list) -> int:
        success_count = 0
        for msg in messages:
            key = str(msg.get('user_id', 'unknown'))
            if self._send(key, msg):
                success_count += 1
        return success_count

    def flush(self, timeout: int = 10):
        if self.producer:
            try:
                self.producer.flush(timeout=timeout)
            except Exception as e:
                logger.error(f"Error flushing producer: {e}")

    def get_mock_messages(self) -> list:
        if not self.producer:
            return self._mock_messages.copy()
        return []

    def clear_mock_messages(self):
        if not self.producer:
            self._mock_messages = []

    def close(self):
        if self.producer:
            try:
                self.producer.flush()
                self.producer.close()
                logger.info("Kafka producer closed")
            except Exception as e:
                logger.error(f"Error closing producer: {e}")


class AsyncBehaviorProducer(BehaviorProducer):
    def __init__(self, brokers: list = None, topic: str = None):
        super().__init__(brokers, topic)
        self._pending = []

    async def send_behavior_async(
        self,
        user_id: int,
        news_id: int,
        behavior_type: str,
        duration: float = 0.0,
        timestamp: Optional[datetime] = None,
        extra: Optional[Dict] = None
    ) -> bool:
        import asyncio
        timestamp = timestamp or datetime.now()

        message = {
            'user_id': user_id,
            'news_id': news_id,
            'behavior_type': behavior_type,
            'duration': duration,
            'timestamp': timestamp.isoformat(),
            'extra': extra or {}
        }

        if self.producer:
            try:
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(
                    None,
                    lambda: self.producer.send(
                        self.topic,
                        key=str(user_id),
                        value=message
                    ).get(timeout=5)
                )
                return True
            except Exception as e:
                logger.error(f"Async send failed: {e}")
                return False
        else:
            self._mock_messages.append(message)
            return True
