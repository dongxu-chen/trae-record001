import os
import sys
import json
import time
from typing import Dict, List, Any
from datetime import datetime
import threading
import queue

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils import load_config, setup_logger, ensure_dir

try:
    from kafka import KafkaProducer, KafkaConsumer
    KAFKA_AVAILABLE = True
except ImportError:
    KAFKA_AVAILABLE = False
    print("kafka-python not installed, using mock mode")


class MockKafkaProducer:
    def __init__(self, **kwargs):
        self.messages = queue.Queue()
        self.logger = kwargs.get("logger", None)

    def send(self, topic, value=None, key=None):
        msg = {"topic": topic, "value": value, "key": key, "timestamp": time.time()}
        self.messages.put(msg)
        if self.logger:
            self.logger.debug(f"Mock sent to {topic}: {value}")
        return MockFuture()

    def flush(self):
        pass

    def close(self):
        pass


class MockFuture:
    def get(self, timeout=None):
        return True


class MockKafkaConsumer:
    def __init__(self, *topics, **kwargs):
        self.topics = topics
        self.messages = queue.Queue()
        self.running = False
        self.logger = kwargs.get("logger", None)

    def poll(self, timeout_ms=0):
        if not self.messages.empty():
            msg = self.messages.get()
            return {msg["topic"]: [MockRecord(msg)]}
        return {}

    def close(self):
        self.running = False


class MockRecord:
    def __init__(self, msg):
        self.value = msg["value"]
        self.key = msg["key"]
        self.topic = msg["topic"]
        self.timestamp = msg.get("timestamp", time.time())


class CTRDataStream:
    def __init__(self, config_path: str = "configs/config.yaml"):
        self.config = load_config(config_path)
        self.logger = setup_logger("CTRDataStream", self.config)
        self.kafka_config = self.config["kafka"]
        self.bootstrap_servers = self.kafka_config["bootstrap_servers"]
        self.topics = self.kafka_config["topics"]
        self.producer = None
        self.consumers = {}
        self.use_mock = not KAFKA_AVAILABLE

    def create_producer(self):
        if self.use_mock:
            self.logger.info("Using mock Kafka producer")
            self.producer = MockKafkaProducer(logger=self.logger)
        else:
            producer_config = self.kafka_config.get("producer_config", {})
            self.producer = KafkaProducer(
                bootstrap_servers=self.bootstrap_servers,
                value_serializer=lambda v: json.dumps(v).encode("utf-8"),
                key_serializer=lambda k: k.encode("utf-8") if k else None,
                **producer_config
            )
        self.logger.info("Kafka producer created")
        return self.producer

    def send_impression(self, impression_data: Dict[str, Any]):
        if self.producer is None:
            self.create_producer()

        impression_data["event_type"] = "impression"
        impression_data["timestamp"] = datetime.now().isoformat()

        self.producer.send(
            self.topics["impressions"],
            value=impression_data,
            key=impression_data.get("user_id")
        )
        self.logger.debug(f"Sent impression: {impression_data.get('ad_id')}")

    def send_click(self, click_data: Dict[str, Any]):
        if self.producer is None:
            self.create_producer()

        click_data["event_type"] = "click"
        click_data["timestamp"] = datetime.now().isoformat()

        self.producer.send(
            self.topics["clicks"],
            value=click_data,
            key=click_data.get("user_id")
        )
        self.logger.debug(f"Sent click: {click_data.get('ad_id')}")

    def send_prediction(self, prediction_data: Dict[str, Any]):
        if self.producer is None:
            self.create_producer()

        prediction_data["event_type"] = "prediction"
        prediction_data["timestamp"] = datetime.now().isoformat()

        self.producer.send(
            self.topics["predictions"],
            value=prediction_data,
            key=prediction_data.get("user_id")
        )
        self.logger.debug(f"Sent prediction: {prediction_data.get('prediction_id')}")

    def create_consumer(self, topic: str, group_id: str = None):
        if group_id is None:
            group_id = self.kafka_config["consumer_group_id"]

        if self.use_mock:
            self.logger.info(f"Using mock Kafka consumer for topic: {topic}")
            consumer = MockKafkaConsumer(topic, logger=self.logger)
        else:
            consumer_config = self.kafka_config.get("consumer_config", {})
            consumer = KafkaConsumer(
                topic,
                bootstrap_servers=self.bootstrap_servers,
                group_id=group_id,
                value_deserializer=lambda m: json.loads(m.decode("utf-8")),
                **consumer_config
            )

        self.consumers[topic] = consumer
        self.logger.info(f"Kafka consumer created for topic: {topic}")
        return consumer

    def consume_impressions(self, callback, max_messages: int = None, duration: int = None):
        topic = self.topics["impressions"]
        consumer = self.consumers.get(topic) or self.create_consumer(topic)

        start_time = time.time()
        message_count = 0

        try:
            while True:
                if max_messages and message_count >= max_messages:
                    break
                if duration and time.time() - start_time > duration:
                    break

                records = consumer.poll(timeout_ms=1000)
                for topic_partition, messages in records.items():
                    for message in messages:
                        callback(message.value)
                        message_count += 1

        except KeyboardInterrupt:
            self.logger.info("Consumer stopped by user")
        finally:
            consumer.close()

        self.logger.info(f"Consumed {message_count} impressions")
        return message_count

    def consume_clicks(self, callback, max_messages: int = None, duration: int = None):
        topic = self.topics["clicks"]
        consumer = self.consumers.get(topic) or self.create_consumer(topic)

        start_time = time.time()
        message_count = 0

        try:
            while True:
                if max_messages and message_count >= max_messages:
                    break
                if duration and time.time() - start_time > duration:
                    break

                records = consumer.poll(timeout_ms=1000)
                for topic_partition, messages in records.items():
                    for message in messages:
                        callback(message.value)
                        message_count += 1

        except KeyboardInterrupt:
            self.logger.info("Consumer stopped by user")
        finally:
            consumer.close()

        self.logger.info(f"Consumed {message_count} clicks")
        return message_count

    def flush(self):
        if self.producer:
            self.producer.flush()

    def close(self):
        if self.producer:
            self.producer.close()
        for consumer in self.consumers.values():
            consumer.close()
        self.logger.info("All Kafka connections closed")


class StreamSimulator:
    def __init__(self, data_stream: CTRDataStream):
        self.data_stream = data_stream
        self.logger = data_stream.logger

    def simulate_impressions(self, num_impressions: int = 1000, delay: float = 0.01):
        import numpy as np
        np.random.seed(42)

        self.logger.info(f"Simulating {num_impressions} impressions...")

        for i in range(num_impressions):
            impression = {
                "impression_id": f"imp_{int(time.time() * 1000)}_{i}",
                "user_id": f"user_{np.random.randint(0, 10000)}",
                "ad_id": f"ad_{np.random.randint(0, 5000)}",
                "context_id": f"context_{np.random.randint(0, 20000)}",
                "position": np.random.randint(1, 10),
                "ab_test_group": np.random.choice(["control", "treatment"], p=[0.5, 0.5]),
                "model_version": np.random.choice(["deepfm_v1", "mmoe_v1"])
            }
            self.data_stream.send_impression(impression)

            if np.random.random() < 0.05:
                click = {
                    "impression_id": impression["impression_id"],
                    "user_id": impression["user_id"],
                    "ad_id": impression["ad_id"],
                    "click_timestamp": datetime.now().isoformat()
                }
                self.data_stream.send_click(click)

            time.sleep(delay)

        self.data_stream.flush()
        self.logger.info("Simulation complete")


def main():
    stream = CTRDataStream()
    print("CTR Data Stream Module")
    print(f"Kafka available: {KAFKA_AVAILABLE}")
    print("Use this module for real-time data streaming")


if __name__ == "__main__":
    main()
