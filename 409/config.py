import os
from datetime import timedelta

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
    
    DATABASE_URL = os.environ.get('DATABASE_URL', 'sqlite:///' + os.path.join(BASE_DIR, 'data', 'sentiment.db'))
    
    KAFKA_BOOTSTRAP_SERVERS = os.environ.get('KAFKA_BOOTSTRAP_SERVERS', 'localhost:9092')
    KAFKA_RAW_DATA_TOPIC = 'raw_social_data'
    KAFKA_ANALYZED_DATA_TOPIC = 'analyzed_data'
    KAFKA_ALERT_TOPIC = 'alerts'
    
    SCRAPY_SETTINGS = {
        'USER_AGENT': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'DOWNLOAD_DELAY': 2,
        'CONCURRENT_REQUESTS': 16,
        'ROBOTSTXT_OBEY': True,
    }
    
    SENTIMENT_THRESHOLD = {
        'positive': 0.6,
        'negative': 0.4,
    }
    
    LDA_NUM_TOPICS = 5
    LDA_NUM_KEYWORDS = 10
    
    ALERT_CONFIG = {
        'negative_ratio_threshold': 0.3,
        'volume_spike_threshold': 2.0,
        'check_interval': 300,
    }
    
    WEIBO_SEARCH_KEYWORDS = ['舆情', '热点', '新闻', '事件']
    TWITTER_SEARCH_KEYWORDS = ['#trending', '#news', '#breaking']
    FORUM_URLS = [
        'https://bbs.hupu.com',
        'https://www.zhihu.com',
        'https://tieba.baidu.com',
    ]
    
    ENABLE_KAFKA = os.environ.get('ENABLE_KAFKA', 'false').lower() == 'true'
    ENABLE_MONGO = os.environ.get('ENABLE_MONGO', 'false').lower() == 'true'
    
    MONGO_URI = os.environ.get('MONGO_URI', 'mongodb://localhost:27017/')
    MONGO_DB = 'sentiment_analysis'
