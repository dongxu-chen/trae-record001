import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

KAFKA_CONFIG = {
    'bootstrap_servers': 'localhost:9092',
    'group_id': 'live-dashboard-group',
    'auto_offset_reset': 'latest',
}

KAFKA_TOPICS = {
    'viewer': 'live-viewer',
    'online': 'live-online',
    'like': 'live-like',
    'transaction': 'live-transaction',
    'product_click': 'live-product-click',
    'danmu': 'live-danmu',
}

FLINK_CONFIG = {
    'parallelism': 2,
    'checkpoint_interval': 5000,
    'window_size': 1,
    'window_slide': 1,
}

WEBSOCKET_CONFIG = {
    'host': '0.0.0.0',
    'port': 8765,
}

SENTIMENT_CONFIG = {
    'positive_threshold': 0.6,
    'negative_threshold': 0.4,
}

HOTWORDS_CONFIG = {
    'top_n': 20,
    'window_size': 300,
}

ADVISOR_CONFIG = {
    'check_interval': 10,
    'low_interaction_threshold': 0.3,
    'high_conversion_threshold': 0.15,
}
