import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'nginx-log-analyzer-secret-key')
    
    ACCESS_LOG_PATH = os.environ.get('ACCESS_LOG_PATH', os.path.join(BASE_DIR, 'logs', 'access.log'))
    ERROR_LOG_PATH = os.environ.get('ERROR_LOG_PATH', os.path.join(BASE_DIR, 'logs', 'error.log'))
    
    GEOIP_DB_PATH = os.environ.get('GEOIP_DB_PATH', os.path.join(BASE_DIR, 'GeoLite2-City.mmdb'))
    
    GEOIP_CACHE_TTL = int(os.environ.get('GEOIP_CACHE_TTL', 3600))
    
    GEOIP_CACHE_CLEANUP_INTERVAL = int(os.environ.get('GEOIP_CACHE_CLEANUP_INTERVAL', 300))
    
    USE_FILE_WATCHER = os.environ.get('USE_FILE_WATCHER', 'true').lower() == 'true'
    
    FILE_WATCHER_DEBOUNCE = float(os.environ.get('FILE_WATCHER_DEBOUNCE', 0.5))
    
    AGGREGATE_SLOW_REQUESTS = os.environ.get('AGGREGATE_SLOW_REQUESTS', 'true').lower() == 'true'
    
    AGGREGATE_PATH_PATTERNS = [
        r'/\d+',
        r'/[a-f0-9]{8}-?[a-f0-9]{4}-?[a-f0-9]{4}-?[a-f0-9]{4}-?[a-f0-9]{12}',
        r'/[a-f0-9]{24,}',
    ]
    
    AGGREGATE_QUERY_PARAMS = os.environ.get('AGGREGATE_QUERY_PARAMS', 'true').lower() == 'true'
    
    SLOW_REQUEST_THRESHOLD = float(os.environ.get('SLOW_REQUEST_THRESHOLD', 1.0))
    
    REFRESH_INTERVAL = int(os.environ.get('REFRESH_INTERVAL', 5000))
    
    MAX_LOG_LINES = int(os.environ.get('MAX_LOG_LINES', 100000))
    
    ENABLE_ALERT_ENGINE = os.environ.get('ENABLE_ALERT_ENGINE', 'true').lower() == 'true'
    
    ALERT_CHECK_INTERVAL = int(os.environ.get('ALERT_CHECK_INTERVAL', 60))
    
    ALERT_COOLDOWN_PERIOD = int(os.environ.get('ALERT_COOLDOWN_PERIOD', 300))
    
    DEFAULT_ALERT_RULES = [
        {
            'id': '5xx_spike',
            'name': '5xx错误突增',
            'enabled': True,
            'type': 'error_spike',
            'params': {
                'status_code_range': '5xx',
                'threshold': 5,
                'window_minutes': 5,
                'compare_to': 'baseline',
                'baseline_multiplier': 3.0
            },
            'severity': 'critical',
            'webhook_urls': []
        },
        {
            'id': 'log_missing',
            'name': '日志缺失检测',
            'enabled': True,
            'type': 'log_missing',
            'params': {
                'no_logs_minutes': 10,
                'min_expected_logs': 1
            },
            'severity': 'warning',
            'webhook_urls': []
        },
        {
            'id': 'traffic_anomaly',
            'name': '流量异常检测',
            'enabled': True,
            'type': 'traffic_anomaly',
            'params': {
                'window_minutes': 5,
                'baseline_minutes': 60,
                'spike_multiplier': 5.0,
                'drop_multiplier': 0.2
            },
            'severity': 'warning',
            'webhook_urls': []
        }
    ]
    
    DEFAULT_WEBHOOKS = []
    
    MAX_ALERT_HISTORY = int(os.environ.get('MAX_ALERT_HISTORY', 1000))
    
    ENABLE_LOG_REPLAY = os.environ.get('ENABLE_LOG_REPLAY', 'true').lower() == 'true'
    
    LOG_REPLAY_MAX_SPEED = float(os.environ.get('LOG_REPLAY_MAX_SPEED', 10.0))
    
    LOG_REPLAY_DEFAULT_SPEED = float(os.environ.get('LOG_REPLAY_DEFAULT_SPEED', 1.0))
