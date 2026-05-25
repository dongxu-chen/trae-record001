import json
import time
import random
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

KAFKA_AVAILABLE = False
try:
    from kafka import KafkaProducer, KafkaAdminClient
    from kafka.admin import NewTopic
    from kafka.errors import TopicAlreadyExistsError
    KAFKA_AVAILABLE = True
except ImportError:
    KafkaProducer = None
    KafkaAdminClient = None
    NewTopic = None
    class TopicAlreadyExistsError(Exception):
        pass

from common.logger import get_logger
from common.utils import (
    load_config,
    generate_user_id,
    generate_event_id,
    datetime_to_timestamp
)

logger = get_logger("EventProducer")

class UserEventProducer:
    def __init__(self):
        self.config = load_config()
        kafka_config = self.config["kafka"]
        
        self.bootstrap_servers = kafka_config["bootstrap_servers"]
        self.topic = kafka_config["topics"]["user_events"]
        self.num_partitions = kafka_config["num_partitions"]
        self.replication_factor = kafka_config["replication_factor"]
        
        self.producer = None
        self.user_pool = self._generate_user_pool(1000)
        
    def _generate_user_pool(self, size: int) -> List[Dict]:
        event_types = self.config["features"]["event_types"]
        regions = ["north", "south", "east", "west", "central"]
        channels = ["organic", "paid", "referral", "social", "email"]
        user_levels = ["new", "bronze", "silver", "gold", "platinum"]
        
        users = []
        for i in range(size):
            signup_days_ago = random.randint(1, 365)
            users.append({
                "user_id": generate_user_id(),
                "user_level": random.choice(user_levels),
                "region": random.choice(regions),
                "channel": random.choice(channels),
                "total_spend": round(random.uniform(0, 10000), 2),
                "signup_date": datetime_to_timestamp(
                    datetime.now() - timedelta(days=signup_days_ago)
                ),
                "event_preferences": {
                    et: random.uniform(0.1, 1.0) for et in event_types
                },
                "churn_risk": random.uniform(0, 1)
            })
        return users
    
    def _ensure_topic_exists(self):
        try:
            admin_client = KafkaAdminClient(
                bootstrap_servers=self.bootstrap_servers
            )
            
            existing_topics = admin_client.list_topics()
            if self.topic not in existing_topics:
                new_topic = NewTopic(
                    name=self.topic,
                    num_partitions=self.num_partitions,
                    replication_factor=self.replication_factor
                )
                admin_client.create_topics([new_topic])
                logger.info(f"Created topic: {self.topic}")
            
            admin_client.close()
        except TopicAlreadyExistsError:
            logger.info(f"Topic {self.topic} already exists")
        except Exception as e:
            logger.error(f"Error ensuring topic exists: {e}")
    
    def connect(self):
        if not KAFKA_AVAILABLE:
            logger.warning("kafka-python not installed. Using in-memory mode for event generation.")
            self.producer = "in_memory"
            return
        
        try:
            self.producer = KafkaProducer(
                bootstrap_servers=self.bootstrap_servers,
                value_serializer=lambda v: json.dumps(v, ensure_ascii=False).encode("utf-8"),
                key_serializer=lambda k: k.encode("utf-8") if k else None,
                retries=3,
                acks="all",
                linger_ms=10,
                batch_size=16384
            )
            self._ensure_topic_exists()
            logger.info("Connected to Kafka successfully")
        except Exception as e:
            logger.warning(f"Failed to connect to Kafka, using in-memory mode: {e}")
            self.producer = "in_memory"
    
    def generate_event(self, user: Optional[Dict] = None) -> Dict:
        event_types = self.config["features"]["event_types"]
        
        if user is None:
            user = random.choice(self.user_pool)
        
        event_preferences = user["event_preferences"]
        event_type = random.choices(
            event_types,
            weights=[event_preferences[et] for et in event_types],
            k=1
        )[0]
        
        session_duration = 0
        if event_type == "login":
            session_duration = random.randint(60, 3600)
        
        purchase_amount = 0
        if event_type == "purchase":
            purchase_amount = round(random.uniform(10, 500), 2)
        
        error_code = None
        if event_type == "error":
            error_code = random.choice([400, 401, 403, 404, 500, 502, 503])
        
        page_url = None
        if event_type in ["view", "click"]:
            page_url = random.choice([
                "/home", "/products", "/product/123", "/cart", "/checkout",
                "/profile", "/settings", "/support", "/about", "/deals"
            ])
        
        churn_factor = user["churn_risk"]
        if churn_factor > 0.7:
            time_since_last_event = random.randint(7 * 24 * 3600, 30 * 24 * 3600)
        elif churn_factor > 0.4:
            time_since_last_event = random.randint(24 * 3600, 7 * 24 * 3600)
        else:
            time_since_last_event = random.randint(60, 24 * 3600)
        
        event_time = datetime_to_timestamp(
            datetime.now() - timedelta(seconds=time_since_last_event)
        )
        
        event = {
            "event_id": generate_event_id(),
            "user_id": user["user_id"],
            "event_type": event_type,
            "event_time": event_time,
            "event_time_iso": datetime.fromtimestamp(event_time).isoformat(),
            "user_profile": {
                "user_level": user["user_level"],
                "region": user["region"],
                "channel": user["channel"],
                "total_spend": user["total_spend"],
                "signup_date": user["signup_date"]
            },
            "event_properties": {
                "session_duration": session_duration,
                "purchase_amount": purchase_amount,
                "error_code": error_code,
                "page_url": page_url,
                "ip_address": f"192.168.{random.randint(0,255)}.{random.randint(0,255)}",
                "user_agent": random.choice([
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)",
                    "Mozilla/5.0 (iPhone; CPU iPhone OS 14_7)",
                    "Mozilla/5.0 (Android 11; Mobile)"
                ])
            },
            "metadata": {
                "source": "simulator",
                "version": "1.0.0",
                "generated_at": datetime_to_timestamp()
            }
        }
        
        return event
    
    def send_event(self, event: Dict):
        if not self.producer:
            raise RuntimeError("Producer not connected. Call connect() first.")
        
        if self.producer == "in_memory":
            logger.debug(f"[In-Memory] Event: {event['event_id']} for user: {event['user_id']} type={event['event_type']}")
            return
        
        try:
            future = self.producer.send(
                self.topic,
                key=event["user_id"],
                value=event
            )
            future.get(timeout=10)
            logger.debug(f"Sent event: {event['event_id']} for user: {event['user_id']}")
        except Exception as e:
            logger.error(f"Failed to send event: {e}")
    
    def generate_and_send_batch(self, num_events: int = 100):
        for i in range(num_events):
            user = random.choice(self.user_pool)
            event = self.generate_event(user)
            self.send_event(event)
            
            if i % 100 == 0:
                self.producer.flush()
                logger.info(f"Sent {i + 1} events")
        
        self.producer.flush()
        logger.info(f"Completed sending {num_events} events")
    
    def start_continuous_production(self, events_per_second: int = 10):
        logger.info(f"Starting continuous event production at {events_per_second} events/second")
        
        interval = 1.0 / events_per_second
        
        try:
            while True:
                user = random.choice(self.user_pool)
                event = self.generate_event(user)
                self.send_event(event)
                time.sleep(interval)
        except KeyboardInterrupt:
            logger.info("Stopping event production")
        finally:
            self.close()
    
    def close(self):
        if self.producer:
            self.producer.flush()
            self.producer.close()
            logger.info("Kafka producer closed")


def main():
    producer = UserEventProducer()
    producer.connect()
    
    logger.info("1. Send batch events")
    logger.info("2. Start continuous production")
    logger.info("3. Generate single test event")
    
    choice = input("Enter your choice (1-3): ").strip()
    
    if choice == "1":
        num = int(input("Enter number of events to send: "))
        producer.generate_and_send_batch(num)
    elif choice == "2":
        eps = int(input("Enter events per second: "))
        producer.start_continuous_production(eps)
    elif choice == "3":
        event = producer.generate_event()
        print(json.dumps(event, indent=2, ensure_ascii=False))
        producer.send_event(event)
        logger.info("Test event sent")
    
    producer.close()


if __name__ == "__main__":
    main()
