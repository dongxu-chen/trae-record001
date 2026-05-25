import json
from typing import Callable, Optional, List, Dict
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

KAFKA_AVAILABLE = False
try:
    from kafka import KafkaConsumer
    from kafka.errors import KafkaError
    KAFKA_AVAILABLE = True
except ImportError:
    KafkaConsumer = None
    class KafkaError(Exception):
        pass

from common.logger import get_logger
from common.utils import load_config, parse_json_safe

logger = get_logger("EventConsumer")

class UserEventConsumer:
    def __init__(self, topic: Optional[str] = None):
        self.config = load_config()
        kafka_config = self.config["kafka"]
        
        self.bootstrap_servers = kafka_config["bootstrap_servers"]
        self.group_id = kafka_config["group_id"]
        self.topic = topic or kafka_config["topics"]["user_events"]
        
        self.consumer = None
        
    def connect(self, auto_offset_reset: str = "latest"):
        if not KAFKA_AVAILABLE:
            logger.warning("kafka-python not installed. Consumer will run in simulated mode.")
            self.consumer = "in_memory"
            return
        
        try:
            self.consumer = KafkaConsumer(
                self.topic,
                bootstrap_servers=self.bootstrap_servers,
                group_id=self.group_id,
                value_deserializer=lambda m: parse_json_safe(m.decode("utf-8")),
                key_deserializer=lambda k: k.decode("utf-8") if k else None,
                auto_offset_reset=auto_offset_reset,
                enable_auto_commit=True,
                auto_commit_interval_ms=5000,
                session_timeout_ms=30000,
                heartbeat_interval_ms=10000
            )
            logger.info(f"Connected to Kafka topic: {self.topic}")
        except Exception as e:
            logger.warning(f"Failed to connect to Kafka, using simulated mode: {e}")
            self.consumer = "in_memory"
    
    def poll(self, timeout_ms: int = 1000, max_records: int = 500) -> List[Dict]:
        if not self.consumer:
            raise RuntimeError("Consumer not connected. Call connect() first.")
        
        events = []
        try:
            records = self.consumer.poll(
                timeout_ms=timeout_ms,
                max_records=max_records
            )
            
            for _, messages in records.items():
                for message in messages:
                    if message.value:
                        events.append(message.value)
            
            logger.debug(f"Polled {len(events)} events")
        except KafkaError as e:
            logger.error(f"Error polling Kafka: {e}")
        
        return events
    
    def consume(self, handler: Callable[[Dict], None], 
                batch_size: int = 100,
                timeout_ms: int = 1000):
        if not self.consumer:
            raise RuntimeError("Consumer not connected. Call connect() first.")
        
        logger.info(f"Starting consumption from topic: {self.topic}")
        
        try:
            batch = []
            for message in self.consumer:
                if message.value:
                    batch.append(message.value)
                    
                    if len(batch) >= batch_size:
                        for event in batch:
                            handler(event)
                        self.consumer.commit()
                        logger.debug(f"Processed batch of {len(batch)} events")
                        batch = []
            
            if batch:
                for event in batch:
                    handler(event)
                self.consumer.commit()
                
        except KeyboardInterrupt:
            logger.info("Stopping consumer")
        except Exception as e:
            logger.error(f"Error during consumption: {e}")
        finally:
            self.close()
    
    def process_batch(self, events: List[Dict]) -> List[Dict]:
        processed = []
        for event in events:
            try:
                processed_event = self._validate_event(event)
                if processed_event:
                    processed.append(processed_event)
            except Exception as e:
                logger.warning(f"Skipping invalid event: {e}")
        
        return processed
    
    def _validate_event(self, event: Dict) -> Optional[Dict]:
        required_fields = ["event_id", "user_id", "event_type", "event_time"]
        
        for field in required_fields:
            if field not in event:
                logger.warning(f"Missing required field: {field}")
                return None
        
        if not isinstance(event["event_time"], (int, float)):
            logger.warning(f"Invalid event_time type: {type(event['event_time'])}")
            return None
        
        return event
    
    def seek_to_beginning(self):
        if not self.consumer:
            raise RuntimeError("Consumer not connected. Call connect() first.")
        
        self.consumer.seek_to_beginning()
        logger.info("Seeked to beginning of topic")
    
    def close(self):
        if self.consumer:
            self.consumer.close()
            logger.info("Kafka consumer closed")


def main():
    consumer = UserEventConsumer()
    consumer.connect(auto_offset_reset="earliest")
    
    def print_handler(event):
        print(json.dumps(event, indent=2, ensure_ascii=False))
        print("-" * 50)
    
    logger.info("1. Consume and print events")
    logger.info("2. Poll and display statistics")
    logger.info("3. Consume from beginning")
    
    choice = input("Enter your choice (1-3): ").strip()
    
    if choice == "1":
        consumer.consume(print_handler, batch_size=1)
    elif choice == "2":
        event_count = 0
        event_types = {}
        
        while True:
            events = consumer.poll(timeout_ms=2000)
            if not events:
                break
            
            event_count += len(events)
            for event in events:
                et = event.get("event_type", "unknown")
                event_types[et] = event_types.get(et, 0) + 1
            
            print(f"\rProcessed {event_count} events | Types: {event_types}", end="")
        
        print(f"\nFinal: {event_count} events processed")
        print(f"Event types: {json.dumps(event_types, indent=2, ensure_ascii=False)}")
    elif choice == "3":
        consumer.seek_to_beginning()
        consumer.consume(print_handler, batch_size=10)
    
    consumer.close()


if __name__ == "__main__":
    main()
