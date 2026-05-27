import json
import time
from typing import Dict, List, Callable, Optional, Any
from dataclasses import dataclass, asdict
from kafka import KafkaProducer, KafkaConsumer, TopicPartition
from kafka.errors import KafkaError
import yaml


@dataclass
class ClickMessage:
    click_id: str
    timestamp: float
    ip: str
    device_id: str
    user_agent: str
    publisher_id: str
    campaign_id: str
    ad_id: str
    referrer: str
    session_id: Optional[str] = None
    user_id: Optional[str] = None
    country: Optional[str] = None
    city: Optional[str] = None
    is_mobile: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict())

    @classmethod
    def from_json(cls, json_str: str) -> 'ClickMessage':
        data = json.loads(json_str)
        return cls(**data)


@dataclass
class FraudAlertMessage:
    click_id: str
    fraud_score: float
    is_fraud: bool
    reasons: List[str]
    rule_scores: Dict[str, float]
    anomaly_score: float
    timestamp: float
    ip: str
    device_id: str
    publisher_id: str
    action: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict())

    @classmethod
    def from_json(cls, json_str: str) -> 'FraudAlertMessage':
        data = json.loads(json_str)
        return cls(**data)


class KafkaClient:
    def __init__(self, config_path: str = 'config/config.yaml'):
        self.config = self._load_config(config_path)
        self.kafka_config = self.config['kafka']
        self.output_config = self.config.get('output', {})
        self.producer: Optional[KafkaProducer] = None
        self.consumer: Optional[KafkaConsumer] = None

    def _load_config(self, config_path: str) -> Dict:
        with open(config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)

    def create_producer(self) -> KafkaProducer:
        self.producer = KafkaProducer(
            bootstrap_servers=self.kafka_config['bootstrap_servers'],
            value_serializer=lambda v: json.dumps(v).encode('utf-8'),
            key_serializer=lambda k: k.encode('utf-8') if k else None,
            acks='all',
            retries=3,
            linger_ms=10
        )
        return self.producer

    def create_consumer(self, topic: Optional[str] = None, group_id: Optional[str] = None) -> KafkaConsumer:
        if topic is None:
            topic = self.kafka_config['topic']
        if group_id is None:
            group_id = self.kafka_config['consumer_group_id']

        self.consumer = KafkaConsumer(
            topic,
            bootstrap_servers=self.kafka_config['bootstrap_servers'],
            group_id=group_id,
            auto_offset_reset=self.kafka_config.get('auto_offset_reset', 'earliest'),
            enable_auto_commit=True,
            auto_commit_interval_ms=5000,
            value_deserializer=lambda m: json.loads(m.decode('utf-8'))
        )
        return self.consumer

    def send_click_log(self, click_message: ClickMessage) -> bool:
        if self.producer is None:
            self.create_producer()

        try:
            future = self.producer.send(
                self.kafka_config['topic'],
                key=click_message.ip,
                value=click_message.to_dict()
            )
            future.get(timeout=10)
            return True
        except KafkaError as e:
            print(f"发送点击日志失败: {e}")
            return False

    def send_click_log_batch(self, messages: List[ClickMessage]) -> int:
        if self.producer is None:
            self.create_producer()

        success_count = 0
        for msg in messages:
            if self.send_click_log(msg):
                success_count += 1
        return success_count

    def send_fraud_alert(self, alert_message: FraudAlertMessage) -> bool:
        if self.producer is None:
            self.create_producer()

        alert_topic = self.output_config.get('alert_topic', 'fraud_alerts')
        try:
            future = self.producer.send(
                alert_topic,
                key=alert_message.ip,
                value=alert_message.to_dict()
            )
            future.get(timeout=10)
            return True
        except KafkaError as e:
            print(f"发送欺诈告警失败: {e}")
            return False

    def consume_click_logs(self, callback: Callable[[Dict], None], max_messages: Optional[int] = None):
        if self.consumer is None:
            self.create_consumer()

        message_count = 0
        try:
            for message in self.consumer:
                callback(message.value)
                message_count += 1
                if max_messages and message_count >= max_messages:
                    break
        except KeyboardInterrupt:
            print("消费被中断")
        finally:
            if self.consumer:
                self.consumer.close()

    def consume_click_logs_batch(self, callback: Callable[[List[Dict]], None], 
                                  batch_size: int = 100, max_messages: Optional[int] = None):
        if self.consumer is None:
            self.create_consumer()

        batch = []
        total_count = 0
        try:
            for message in self.consumer:
                batch.append(message.value)
                total_count += 1
                
                if len(batch) >= batch_size:
                    callback(batch)
                    batch = []
                
                if max_messages and total_count >= max_messages:
                    if batch:
                        callback(batch)
                    break
        except KeyboardInterrupt:
            print("消费被中断")
            if batch:
                callback(batch)
        finally:
            if self.consumer:
                self.consumer.close()

    def get_latest_messages(self, topic: Optional[str] = None, count: int = 10) -> List[Dict]:
        if topic is None:
            topic = self.kafka_config['topic']

        temp_consumer = KafkaConsumer(
            bootstrap_servers=self.kafka_config['bootstrap_servers'],
            auto_offset_reset='latest',
            enable_auto_commit=False,
            value_deserializer=lambda m: json.loads(m.decode('utf-8'))
        )

        messages = []
        try:
            partitions = temp_consumer.partitions_for_topic(topic)
            if not partitions:
                return messages

            topic_partitions = [TopicPartition(topic, p) for p in partitions]
            temp_consumer.assign(topic_partitions)
            
            for tp in topic_partitions:
                end_offset = temp_consumer.end_offsets([tp])[tp]
                start_offset = max(0, end_offset - count)
                temp_consumer.seek(tp, start_offset)

            for _ in range(count * 2):
                poll_result = temp_consumer.poll(timeout_ms=1000)
                if not poll_result:
                    break
                for records in poll_result.values():
                    for record in records:
                        messages.append(record.value)
                        if len(messages) >= count:
                            return messages
        finally:
            temp_consumer.close()

        return messages[:count]

    def flush(self):
        if self.producer:
            self.producer.flush()

    def close(self):
        if self.producer:
            self.producer.close()
        if self.consumer:
            self.consumer.close()
