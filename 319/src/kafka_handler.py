import json
import time
import uuid
from typing import Any, Callable, Dict, List, Optional

from kafka import KafkaProducer, KafkaConsumer, TopicPartition
from kafka.errors import KafkaError

from config import config
from src.bid_engine import BidRequest, BidResponse, BidEngine
from src.redis_client import RedisClient


class KafkaHandler:
    def __init__(self):
        self.config = config.kafka
        self.producer: Optional[KafkaProducer] = None
        self.consumer: Optional[KafkaConsumer] = None
        self.redis_client = RedisClient()
        self.bid_engine = BidEngine()

    def _create_producer(self) -> KafkaProducer:
        return KafkaProducer(
            bootstrap_servers=self.config.bootstrap_servers,
            value_serializer=lambda v: json.dumps(v).encode("utf-8"),
            key_serializer=lambda k: str(k).encode("utf-8") if k else None,
            acks="all",
            retries=3,
            linger_ms=10,
            batch_size=16384,
        )

    def _create_consumer(self, topics: List[str]) -> KafkaConsumer:
        return KafkaConsumer(
            *topics,
            bootstrap_servers=self.config.bootstrap_servers,
            group_id=self.config.consumer_group_id,
            auto_offset_reset=self.config.auto_offset_reset,
            enable_auto_commit=self.config.enable_auto_commit,
            value_deserializer=lambda m: json.loads(m.decode("utf-8")),
            session_timeout_ms=30000,
            heartbeat_interval_ms=10000,
        )

    def connect(self):
        try:
            self.producer = self._create_producer()
            self.consumer = self._create_consumer([self.config.bid_request_topic])
            print(f"Connected to Kafka at {self.config.bootstrap_servers}")
        except Exception as e:
            print(f"Failed to connect to Kafka: {e}")
            raise

    def disconnect(self):
        if self.producer:
            self.producer.flush()
            self.producer.close()
        if self.consumer:
            self.consumer.close()
        print("Disconnected from Kafka")

    def send_bid_request(self, bid_request: Dict[str, Any]) -> Optional[str]:
        if not self.producer:
            self.connect()
        request_id = bid_request.get("request_id", str(uuid.uuid4()))
        bid_request["request_id"] = request_id
        bid_request["timestamp"] = int(time.time() * 1000)
        try:
            future = self.producer.send(
                self.config.bid_request_topic,
                key=request_id,
                value=bid_request,
            )
            record_metadata = future.get(timeout=10)
            print(f"Sent bid request {request_id} to {record_metadata.topic}:{record_metadata.partition}:{record_metadata.offset}")
            return request_id
        except KafkaError as e:
            print(f"Failed to send bid request: {e}")
            return None

    def send_bid_response(self, bid_response: Dict[str, Any]) -> bool:
        if not self.producer:
            self.connect()
        try:
            future = self.producer.send(
                self.config.bid_response_topic,
                key=bid_response.get("request_id"),
                value=bid_response,
            )
            future.get(timeout=10)
            return True
        except KafkaError as e:
            print(f"Failed to send bid response: {e}")
            return False

    def send_impression(self, impression_data: Dict[str, Any]) -> bool:
        if not self.producer:
            self.connect()
        try:
            impression_data["timestamp"] = int(time.time() * 1000)
            future = self.producer.send(
                self.config.impression_topic,
                key=impression_data.get("bid_id"),
                value=impression_data,
            )
            future.get(timeout=10)
            return True
        except KafkaError as e:
            print(f"Failed to send impression: {e}")
            return False

    def send_click(self, click_data: Dict[str, Any]) -> bool:
        if not self.producer:
            self.connect()
        try:
            click_data["timestamp"] = int(time.time() * 1000)
            future = self.producer.send(
                self.config.click_topic,
                key=click_data.get("bid_id"),
                value=click_data,
            )
            future.get(timeout=10)
            self.bid_engine.record_click(click_data.get("bid_id", ""))
            return True
        except KafkaError as e:
            print(f"Failed to send click: {e}")
            return False

    def send_conversion(self, conversion_data: Dict[str, Any]) -> bool:
        if not self.producer:
            self.connect()
        try:
            conversion_data["timestamp"] = int(time.time() * 1000)
            future = self.producer.send(
                self.config.conversion_topic,
                key=conversion_data.get("bid_id"),
                value=conversion_data,
            )
            future.get(timeout=10)
            return True
        except KafkaError as e:
            print(f"Failed to send conversion: {e}")
            return False

    def _dict_to_bid_request(self, data: Dict[str, Any]) -> BidRequest:
        return BidRequest(
            request_id=data.get("request_id", str(uuid.uuid4())),
            user_id=data.get("user_id", ""),
            ad_id=data.get("ad_id", ""),
            campaign_id=data.get("campaign_id", "default"),
            user_profile=data.get("user_profile", {}),
            context=data.get("context", {}),
            ad_info=data.get("ad_info", {}),
            floor_price=data.get("floor_price", 0.01),
            cpa_goal=data.get("cpa_goal", 10.0),
        )

    def consume_bid_requests(self, callback: Optional[Callable[[Dict[str, Any]], None]] = None):
        if not self.consumer:
            self.connect()
        print(f"Started consuming from {self.config.bid_request_topic}")
        try:
            for message in self.consumer:
                try:
                    bid_request_data = message.value
                    print(f"Received bid request: {bid_request_data.get('request_id')}")
                    bid_request = self._dict_to_bid_request(bid_request_data)
                    bid_response = self.bid_engine.process_bid(bid_request)
                    response_dict = bid_response.to_dict()
                    self.send_bid_response(response_dict)
                    if callback:
                        callback(response_dict)
                    if self.config.enable_auto_commit:
                        self.consumer.commit()
                except Exception as e:
                    print(f"Error processing bid request: {e}")
        except KeyboardInterrupt:
            print("Consumer stopped by user")
        finally:
            self.disconnect()

    def consume_clicks(self):
        consumer = self._create_consumer([self.config.click_topic])
        print(f"Started consuming from {self.config.click_topic}")
        try:
            for message in consumer:
                try:
                    click_data = message.value
                    bid_id = click_data.get("bid_id", "")
                    print(f"Received click for bid: {bid_id}")
                    self.bid_engine.record_click(bid_id)
                except Exception as e:
                    print(f"Error processing click: {e}")
        except KeyboardInterrupt:
            print("Click consumer stopped by user")
        finally:
            consumer.close()

    def get_last_offsets(self, topic: str) -> Dict[int, int]:
        if not self.consumer:
            self.connect()
        partitions = self.consumer.partitions_for_topic(topic)
        if not partitions:
            return {}
        offsets = {}
        for partition in partitions:
            tp = TopicPartition(topic, partition)
            self.consumer.assign([tp])
            self.consumer.seek_to_end(tp)
            last_offset = self.consumer.position(tp)
            offsets[partition] = last_offset
        return offsets

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.disconnect()
