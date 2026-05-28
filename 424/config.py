"""
全局配置文件
"""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

MONGODB = {
    'host': os.getenv('MONGO_HOST', 'localhost'),
    'port': int(os.getenv('MONGO_PORT', 27017)),
    'database': os.getenv('MONGO_DB', 'price_monitor'),
    'username': os.getenv('MONGO_USER', ''),
    'password': os.getenv('MONGO_PASS', ''),
}

REDIS = {
    'host': os.getenv('REDIS_HOST', 'localhost'),
    'port': int(os.getenv('REDIS_PORT', 6379)),
    'db': int(os.getenv('REDIS_DB', 0)),
    'password': os.getenv('REDIS_PASS', ''),
}

PROXY = {
    'enable': True,
    'redis_key': 'proxy:pool',
    'check_url': 'https://httpbin.org/ip',
    'check_timeout': 5,
    'min_pool_size': 20,
    'max_pool_size': 50,
    'refresh_interval': 300,
    'health_check_interval': 60,
    'max_failures': 3,
    'probation_timeout': 300,
    'sources': [
        {
            'name': 'kuaidaili',
            'url': 'https://www.kuaidaili.com/free/',
            'enabled': False,
        },
        {
            'name': 'xiladaili',
            'url': 'http://www.xiladaili.com/',
            'enabled': False,
        },
    ],
}

SCRAPY_SETTINGS = {
    'CONCURRENT_REQUESTS': 16,
    'DOWNLOAD_DELAY': 1,
    'RANDOMIZE_DOWNLOAD_DELAY': True,
    'COOKIES_ENABLED': False,
    'RETRY_TIMES': 3,
    'RETRY_HTTP_CODES': [500, 502, 503, 504, 408, 429],
    'PLAYWRIGHT_LAUNCH_OPTIONS': {
        'headless': True,
        'args': [
            '--disable-gpu',
            '--disable-dev-shm-usage',
            '--no-sandbox',
        ],
    },
    'PLAYWRIGHT_BROWSER_TYPE': 'chromium',
    'PLAYWRIGHT_DEFAULT_NAVIGATION_TIMEOUT': 30000,
}

SPIDER_CONFIG = {
    'default_schedule_interval': 1800,
    'price_change_threshold': 0.05,
    'promo_keywords': [
        '促销', '优惠', '折扣', '特价', '秒杀', '限时',
        '满减', '满赠', '买赠', '券', 'promotion', 'discount',
        'sale', 'deal', 'offer',
    ],
    'competitors': [
        {
            'name': 'example_competitor_a',
            'domain': 'example-a.com',
            'start_urls': [
                'https://example-a.com/products/category1',
                'https://example-a.com/products/category2',
            ],
            'enabled': True,
            'use_playwright': False,
            'schedule_interval': 1800,
        },
        {
            'name': 'example_competitor_b',
            'domain': 'example-b.com',
            'start_urls': [
                'https://example-b.com/products',
            ],
            'enabled': True,
            'use_playwright': True,
            'schedule_interval': 3600,
        },
    ],
}

ALERT_CONFIG = {
    'enable': True,
    'enable_yoy_analysis': True,
    'yoy_days_back': 7,
    'yoy_tolerance_hours': 12,
    'email': {
        'smtp_server': os.getenv('SMTP_SERVER', 'smtp.qq.com'),
        'smtp_port': int(os.getenv('SMTP_PORT', 465)),
        'sender': os.getenv('SMTP_SENDER', ''),
        'password': os.getenv('SMTP_PASS', ''),
        'receivers': os.getenv('SMTP_RECEIVERS', '').split(','),
        'use_ssl': True,
    },
    'webhook': {
        'url': os.getenv('WEBHOOK_URL', ''),
        'secret': os.getenv('WEBHOOK_SECRET', ''),
    },
    'alert_rules': [
        {
            'type': 'price_drop',
            'threshold': 0.10,
            'enabled': True,
        },
        {
            'type': 'price_rise',
            'threshold': 0.05,
            'enabled': True,
        },
        {
            'type': 'stock_out',
            'enabled': True,
        },
        {
            'type': 'promotion',
            'enabled': True,
        },
        {
            'type': 'new_product',
            'enabled': True,
        },
    ],
}

FLASK_CONFIG = {
    'host': '0.0.0.0',
    'port': 5000,
    'debug': True,
    'secret_key': os.getenv('FLASK_SECRET', 'change-this-secret-key-in-production'),
}

LOG_CONFIG = {
    'log_dir': BASE_DIR / 'logs',
    'log_level': 'INFO',
    'max_size': '10 MB',
    'retention': '30 days',
}

SCHEDULER_CONFIG = {
    'timezone': 'Asia/Shanghai',
    'job_defaults': {
        'coalesce': True,
        'max_instances': 1,
        'misfire_grace_time': 300,
    },
}

ANALYSIS_CONFIG = {
    'enable_price_prediction': True,
    'prediction_days': 7,
    'min_data_points': 5,
    'moving_avg_window': 7,
    'trend_threshold': 0.03,
    'seasonality_days': 7,
    'prediction_alert_thresholds': {
        'high_drop': -0.10,
        'moderate_drop': -0.05,
        'high_rise': 0.10,
        'moderate_rise': 0.05,
    },
    'enable_cross_promo': True,
    'cross_promo_keywords': {
        'buy_x_get_y': ['买.*送', '买.*赠', '买一送', 'buy.*get', 'bundle'],
        'package_deal': ['套餐', '组合', '套装', 'combo', 'package'],
        'bundle_discount': ['两件', '三件', '第2件', '第3件', '2件', '3件'],
        'conditional_discount': ['满.*送', '满.*减', '满.*享', 'spend.*save'],
        'free_gift': ['赠品', '礼品', 'free gift', 'gift with'],
    },
    'price_relation_threshold': 0.1,
    'enable_fraud_detection': True,
    'fraud_window_days': 30,
    'baseline_days': 7,
    'min_rise_ratio': 0.05,
    'min_drop_ratio': 0.10,
    'min_original_price_deviation': 0.30,
    'fake_discount_threshold': 0.50,
    'short_term_window': 7,
    'fraud_alert_severity': ['high', 'critical'],
}