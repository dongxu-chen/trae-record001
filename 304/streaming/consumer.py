import json
import logging
import threading
import time
from typing import Callable, Optional, List, Dict
from datetime import datetime

try:
    from kafka import KafkaConsumer, TopicPartition
    from kafka.errors import KafkaError
    KAFKA_AVAILABLE = True
except ImportError:
    KAFKA_AVAILABLE = False
    logging.warning("kafka-python not installed. Using mock consumer.")

from config import config

logger = logging.getLogger(__name__)


class BehaviorConsumer:
    def __init__(
        self,
        brokers: list = None,
        topic: str = None,
        group_id: str = None,
        auto_offset_reset: str = 'latest'
    ):
        self.brokers = brokers or config.KAFKA_BROKERS
        self.topic = topic or config.KAFKA_TOPIC_BEHAVIOR
        self.group_id = group_id or config.KAFKA_GROUP_ID
        self.auto_offset_reset = auto_offset_reset
        self.consumer = None
        self._running = False
        self._thread = None
        self._message_handler = None
        self._mock_producer = None
        self._connect()

    def _connect(self):
        if not KAFKA_AVAILABLE:
            logger.info("Using mock Kafka consumer")
            self.consumer = None
            return

        try:
            self.consumer = KafkaConsumer(
                self.topic,
                bootstrap_servers=self.brokers,
                group_id=self.group_id,
                auto_offset_reset=self.auto_offset_reset,
                enable_auto_commit=True,
                auto_commit_interval_ms=5000,
                value_deserializer=lambda m: json.loads(m.decode('utf-8')),
                key_deserializer=lambda k: k.decode('utf-8') if k else None,
                session_timeout_ms=30000,
                heartbeat_interval_ms=10000,
                max_poll_interval_ms=300000,
                fetch_max_wait_ms=500,
                fetch_min_bytes=1,
                max_poll_records=500
            )
            logger.info(f"Kafka consumer connected to {self.brokers}, topic: {self.topic}")
        except Exception as e:
            logger.warning(f"Failed to connect to Kafka consumer: {e}. Using mock consumer.")
            self.consumer = None

    def set_message_handler(self, handler: Callable[[Dict], None]):
        self._message_handler = handler

    def set_mock_producer(self, producer):
        self._mock_producer = producer

    def start(self, handler: Callable[[Dict], None] = None):
        if handler:
            self.set_message_handler(handler)

        if not self._message_handler:
            raise ValueError("Message handler not set")

        self._running = True
        self._thread = threading.Thread(target=self._consume_loop, daemon=True)
        self._thread.start()
        logger.info("Consumer started")

    def _consume_loop(self):
        if self.consumer:
            try:
                for message in self.consumer:
                    if not self._running:
                        break

                    try:
                        data = message.value
                        self._message_handler(data)
                    except Exception as e:
                        logger.error(f"Error processing message: {e}, message: {message.value}")
            except KafkaError as e:
                logger.error(f"Kafka consumer error: {e}")
            finally:
                if self._running:
                    self._reconnect()
        else:
            self._mock_consume_loop()

    def _mock_consume_loop(self):
        processed_count = 0
        while self._running:
            try:
                if self._mock_producer:
                    messages = self._mock_producer.get_mock_messages()
                    if messages:
                        for message in messages:
                            if not self._running:
                                break
                            try:
                                self._message_handler(message)
                                processed_count += 1
                            except Exception as e:
                                logger.error(f"Error processing mock message: {e}")
                        self._mock_producer.clear_mock_messages()

                time.sleep(1.0)
            except Exception as e:
                logger.error(f"Mock consumer error: {e}")
                time.sleep(1.0)

    def _reconnect(self):
        logger.info("Attempting to reconnect Kafka consumer...")
        retry_count = 0
        max_retries = 10

        while self._running and retry_count < max_retries:
            try:
                self._connect()
                if self.consumer:
                    logger.info("Successfully reconnected to Kafka")
                    self._consume_loop()
                    return
            except Exception as e:
                logger.error(f"Reconnection attempt {retry_count + 1} failed: {e}")

            retry_count += 1
            time.sleep(min(2 ** retry_count, 60))

        logger.error("Max reconnection attempts reached")

    def poll(self, timeout_ms: int = 1000, max_records: int = None) -> List[Dict]:
        max_records = max_records or 500

        if self.consumer:
            try:
                records = self.consumer.poll(timeout_ms=timeout_ms, max_records=max_records)
                messages = []
                for _, record_list in records.items():
                    for record in record_list:
                        messages.append(record.value)
                return messages
            except KafkaError as e:
                logger.error(f"Poll error: {e}")
                return []
        else:
            if self._mock_producer:
                messages = self._mock_producer.get_mock_messages()
                self._mock_producer.clear_mock_messages()
                return messages
            return []

    def commit(self):
        if self.consumer:
            try:
                self.consumer.commit()
            except KafkaError as e:
                logger.error(f"Commit error: {e}")

    def seek_to_beginning(self):
        if self.consumer:
            partitions = self.consumer.partitions_for_topic(self.topic)
            if partitions:
                for partition in partitions:
                    tp = TopicPartition(self.topic, partition)
                    self.consumer.seek_to_beginning(tp)

    def seek_to_end(self):
        if self.consumer:
            partitions = self.consumer.partitions_for_topic(self.topic)
            if partitions:
                for partition in partitions:
                    tp = TopicPartition(self.topic, partition)
                    self.consumer.seek_to_end(tp)

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
            self._thread = None
        logger.info("Consumer stopped")

    def close(self):
        self.stop()
        if self.consumer:
            try:
                self.consumer.close()
                logger.info("Kafka consumer closed")
            except Exception as e:
                logger.error(f"Error closing consumer: {e}")


class BatchBehaviorConsumer(BehaviorConsumer):
    def __init__(
        self,
        brokers: list = None,
        topic: str = None,
        group_id: str = None,
        batch_size: int = 100,
        batch_timeout: int = 5
    ):
        super().__init__(brokers, topic, group_id)
        self.batch_size = batch_size
        self.batch_timeout = batch_timeout
        self._batch_handler = None

    def set_batch_handler(self, handler: Callable[[List[Dict]], None]):
        self._batch_handler = handler

    def start_batch(self, handler: Callable[[List[Dict]], None] = None):
        if handler:
            self.set_batch_handler(handler)

        if not self._batch_handler:
            raise ValueError("Batch handler not set")

        self._running = True
        self._thread = threading.Thread(target=self._batch_consume_loop, daemon=True)
        self._thread.start()
        logger.info(f"Batch consumer started (batch_size={self.batch_size}, timeout={self.batch_timeout}s)")

    def _batch_consume_loop(self):
        batch = []
        last_batch_time = time.time()

        def process_batch():
            nonlocal batch, last_batch_time
            if batch:
                try:
                    self._batch_handler(batch)
                except Exception as e:
                    logger.error(f"Error processing batch: {e}")
                batch = []
                last_batch_time = time.time()

        while self._running:
            try:
                if self.consumer:
                    records = self.consumer.poll(timeout_ms=1000, max_records=self.batch_size)
                    for _, record_list in records.items():
                        for record in record_list:
                            if not self._running:
                                break
                            batch.append(record.value)

                            if len(batch) >= self.batch_size:
                                process_batch()

                    if batch and (time.time() - last_batch_time) >= self.batch_timeout:
                        process_batch()
                else:
                    if self._mock_producer:
                        messages = self._mock_producer.get_mock_messages()
                        if messages:
                            batch.extend(messages)
                            self._mock_producer.clear_mock_messages()

                    if len(batch) >= self.batch_size or (batch and (time.time() - last_batch_time) >= self.batch_timeout):
                        process_batch()
                    else:
                        time.sleep(0.5)

            except Exception as e:
                logger.error(f"Batch consumer error: {e}")
                time.sleep(1.0)

        if batch:
            try:
                self._batch_handler(batch)
            except Exception as e:
                logger.error(f"Error processing final batch: {e}")
