import json
import logging
from datetime import datetime
import threading
import time

logger = logging.getLogger(__name__)

try:
    from kafka import KafkaProducer, KafkaConsumer, KafkaAdminClient
    from kafka.admin import NewTopic
    from kafka.errors import TopicAlreadyExistsError, NoBrokersAvailable
    KAFKA_AVAILABLE = True
except ImportError:
    KAFKA_AVAILABLE = False
    logger.warning("kafka-python not installed. Kafka features will be disabled.")

from config import Config


class KafkaManager:
    def __init__(self):
        self.enabled = Config.ENABLE_KAFKA and KAFKA_AVAILABLE
        self.producer = None
        self.consumer = None
        self.admin_client = None
        self._stop_event = threading.Event()
        
        if self.enabled:
            self._init_producer()
            self._init_admin_client()
            self._create_topics()
    
    def _init_producer(self):
        try:
            self.producer = KafkaProducer(
                bootstrap_servers=Config.KAFKA_BOOTSTRAP_SERVERS,
                value_serializer=lambda v: json.dumps(v, ensure_ascii=False).encode('utf-8'),
                key_serializer=lambda k: k.encode('utf-8') if k else None,
                retries=3,
                acks='all'
            )
            logger.info("Kafka producer initialized successfully")
        except NoBrokersAvailable:
            logger.error(f"Could not connect to Kafka at {Config.KAFKA_BOOTSTRAP_SERVERS}")
            self.enabled = False
        except Exception as e:
            logger.error(f"Failed to initialize Kafka producer: {e}")
            self.enabled = False
    
    def _init_admin_client(self):
        if not self.enabled:
            return
        try:
            self.admin_client = KafkaAdminClient(
                bootstrap_servers=Config.KAFKA_BOOTSTRAP_SERVERS
            )
            logger.info("Kafka admin client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Kafka admin client: {e}")
    
    def _create_topics(self):
        if not self.enabled or not self.admin_client:
            return
        
        topics = [
            Config.KAFKA_RAW_DATA_TOPIC,
            Config.KAFKA_ANALYZED_DATA_TOPIC,
            Config.KAFKA_ALERT_TOPIC
        ]
        
        new_topics = []
        for topic in topics:
            new_topics.append(NewTopic(
                name=topic,
                num_partitions=3,
                replication_factor=1
            ))
        
        try:
            self.admin_client.create_topics(new_topics)
            logger.info(f"Created Kafka topics: {topics}")
        except TopicAlreadyExistsError:
            logger.info(f"Kafka topics already exist: {topics}")
        except Exception as e:
            logger.error(f"Failed to create Kafka topics: {e}")
    
    def send_raw_data(self, data):
        if not self.enabled or not self.producer:
            return None
        
        try:
            future = self.producer.send(
                Config.KAFKA_RAW_DATA_TOPIC,
                value=data,
                key=data.get('platform', 'unknown')
            )
            record_metadata = future.get(timeout=10)
            logger.debug(f"Sent raw data to Kafka: {record_metadata.topic}:{record_metadata.partition}:{record_metadata.offset}")
            return record_metadata
        except Exception as e:
            logger.error(f"Failed to send raw data to Kafka: {e}")
            return None
    
    def send_analyzed_data(self, data):
        if not self.enabled or not self.producer:
            return None
        
        try:
            future = self.producer.send(
                Config.KAFKA_ANALYZED_DATA_TOPIC,
                value=data,
                key=data.get('platform', 'unknown')
            )
            record_metadata = future.get(timeout=10)
            logger.debug(f"Sent analyzed data to Kafka: {record_metadata.topic}")
            return record_metadata
        except Exception as e:
            logger.error(f"Failed to send analyzed data to Kafka: {e}")
            return None
    
    def send_alert(self, alert_data):
        if not self.enabled or not self.producer:
            return None
        
        try:
            future = self.producer.send(
                Config.KAFKA_ALERT_TOPIC,
                value=alert_data,
                key=alert_data.get('severity', 'info')
            )
            record_metadata = future.get(timeout=10)
            logger.info(f"Sent alert to Kafka: {alert_data.get('alert_type')} - {alert_data.get('severity')}")
            return record_metadata
        except Exception as e:
            logger.error(f"Failed to send alert to Kafka: {e}")
            return None
    
    def consume_raw_data(self, callback, group_id='raw_data_group'):
        if not self.enabled:
            logger.warning("Kafka not enabled, cannot consume raw data")
            return
        
        consumer = None
        try:
            consumer = KafkaConsumer(
                Config.KAFKA_RAW_DATA_TOPIC,
                bootstrap_servers=Config.KAFKA_BOOTSTRAP_SERVERS,
                group_id=group_id,
                value_deserializer=lambda m: json.loads(m.decode('utf-8')),
                auto_offset_reset='earliest',
                enable_auto_commit=True,
                auto_commit_interval_ms=5000
            )
            
            logger.info(f"Started consuming from {Config.KAFKA_RAW_DATA_TOPIC}")
            
            for message in consumer:
                if self._stop_event.is_set():
                    break
                try:
                    callback(message.value)
                except Exception as e:
                    logger.error(f"Error in raw data consumer callback: {e}")
        
        except Exception as e:
            logger.error(f"Raw data consumer error: {e}")
        finally:
            if consumer:
                consumer.close()
    
    def consume_analyzed_data(self, callback, group_id='analyzed_data_group'):
        if not self.enabled:
            logger.warning("Kafka not enabled, cannot consume analyzed data")
            return
        
        consumer = None
        try:
            consumer = KafkaConsumer(
                Config.KAFKA_ANALYZED_DATA_TOPIC,
                bootstrap_servers=Config.KAFKA_BOOTSTRAP_SERVERS,
                group_id=group_id,
                value_deserializer=lambda m: json.loads(m.decode('utf-8')),
                auto_offset_reset='earliest',
                enable_auto_commit=True,
                auto_commit_interval_ms=5000
            )
            
            logger.info(f"Started consuming from {Config.KAFKA_ANALYZED_DATA_TOPIC}")
            
            for message in consumer:
                if self._stop_event.is_set():
                    break
                try:
                    callback(message.value)
                except Exception as e:
                    logger.error(f"Error in analyzed data consumer callback: {e}")
        
        except Exception as e:
            logger.error(f"Analyzed data consumer error: {e}")
        finally:
            if consumer:
                consumer.close()
    
    def consume_alerts(self, callback, group_id='alert_group'):
        if not self.enabled:
            logger.warning("Kafka not enabled, cannot consume alerts")
            return
        
        consumer = None
        try:
            consumer = KafkaConsumer(
                Config.KAFKA_ALERT_TOPIC,
                bootstrap_servers=Config.KAFKA_BOOTSTRAP_SERVERS,
                group_id=group_id,
                value_deserializer=lambda m: json.loads(m.decode('utf-8')),
                auto_offset_reset='earliest',
                enable_auto_commit=True,
                auto_commit_interval_ms=5000
            )
            
            logger.info(f"Started consuming from {Config.KAFKA_ALERT_TOPIC}")
            
            for message in consumer:
                if self._stop_event.is_set():
                    break
                try:
                    callback(message.value)
                except Exception as e:
                    logger.error(f"Error in alert consumer callback: {e}")
        
        except Exception as e:
            logger.error(f"Alert consumer error: {e}")
        finally:
            if consumer:
                consumer.close()
    
    def start_consumer_thread(self, topic, callback, group_id=None):
        if not self.enabled:
            logger.warning("Kafka not enabled, cannot start consumer thread")
            return None
        
        if group_id is None:
            group_id = f"{topic}_group_{datetime.utcnow().timestamp()}"
        
        def consumer_wrapper():
            if topic == Config.KAFKA_RAW_DATA_TOPIC:
                self.consume_raw_data(callback, group_id)
            elif topic == Config.KAFKA_ANALYZED_DATA_TOPIC:
                self.consume_analyzed_data(callback, group_id)
            elif topic == Config.KAFKA_ALERT_TOPIC:
                self.consume_alerts(callback, group_id)
        
        thread = threading.Thread(target=consumer_wrapper, daemon=True)
        thread.start()
        logger.info(f"Started consumer thread for topic: {topic}")
        return thread
    
    def stop_consumers(self):
        self._stop_event.set()
        logger.info("Stopping all Kafka consumers")
    
    def close(self):
        self.stop_consumers()
        if self.producer:
            self.producer.flush()
            self.producer.close(timeout=10)
        if self.admin_client:
            self.admin_client.close()
        logger.info("Kafka manager closed")
