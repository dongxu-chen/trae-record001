import scrapy
from datetime import datetime
import json
import logging
from config import Config

logger = logging.getLogger(__name__)


class BaseSocialSpider(scrapy.Spider):
    custom_settings = Config.SCRAPY_SETTINGS

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.kafka_producer = None
        if Config.ENABLE_KAFKA:
            try:
                from kafka import KafkaProducer
                self.kafka_producer = KafkaProducer(
                    bootstrap_servers=Config.KAFKA_BOOTSTRAP_SERVERS,
                    value_serializer=lambda v: json.dumps(v, ensure_ascii=False).encode('utf-8')
                )
            except Exception as e:
                logger.warning(f"Kafka producer init failed: {e}")

    def parse(self, response):
        pass

    def send_to_kafka(self, data):
        if self.kafka_producer:
            try:
                self.kafka_producer.send(Config.KAFKA_RAW_DATA_TOPIC, value=data)
                self.kafka_producer.flush()
            except Exception as e:
                logger.error(f"Failed to send to Kafka: {e}")

    def create_post_item(self, platform, post_id, content, **kwargs):
        item = {
            'platform': platform,
            'post_id': str(post_id),
            'content': content,
            'author': kwargs.get('author', ''),
            'author_id': kwargs.get('author_id', ''),
            'post_url': kwargs.get('post_url', ''),
            'timestamp': kwargs.get('timestamp', datetime.utcnow().isoformat()),
            'likes': kwargs.get('likes', 0),
            'shares': kwargs.get('shares', 0),
            'comments': kwargs.get('comments', 0),
            'views': kwargs.get('views', 0),
            'raw_data': kwargs.get('raw_data', ''),
            'collected_at': datetime.utcnow().isoformat()
        }
        self.send_to_kafka(item)
        return item

    def closed(self, reason):
        if self.kafka_producer:
            self.kafka_producer.close()
