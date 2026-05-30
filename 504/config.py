import os
from dotenv import load_dotenv

load_dotenv()

CLICKHOUSE_CONFIG = {
    'host': os.getenv('CLICKHOUSE_HOST', 'localhost'),
    'port': int(os.getenv('CLICKHOUSE_PORT', 8123)),
    'username': os.getenv('CLICKHOUSE_USER', 'default'),
    'password': os.getenv('CLICKHOUSE_PASSWORD', ''),
    'database': os.getenv('CLICKHOUSE_DATABASE', 'user_behavior'),
    'secure': False
}

APP_TITLE = "用户行为路径分析工具"
APP_ICON = "📊"

EVENT_TABLE = 'user_events'
SESSION_TIMEOUT = 1800
MAX_PATH_LENGTH = 10
MIN_PATH_FREQUENCY = 5
