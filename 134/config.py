import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    DB_HOST = os.getenv('DB_HOST', 'localhost')
    DB_PORT = int(os.getenv('DB_PORT', 3306))
    DB_USER = os.getenv('DB_USER', 'root')
    DB_PASSWORD = os.getenv('DB_PASSWORD', '')
    DB_NAME = os.getenv('DB_NAME', 'information_schema')
    
    HISTORY_FILE = 'deadlock_history.json'
    DEPENDENCY_GRAPH_FILE = 'deadlock_dependency_graph.html'
    REPORT_FILE = 'deadlock_report.html'
    TREND_REPORT_FILE = 'deadlock_trend_report.html'
    
    AUTO_KILL_ENABLED = os.getenv('AUTO_KILL_ENABLED', 'false').lower() == 'true'
    AUTO_KILL_THRESHOLD_SECONDS = int(os.getenv('AUTO_KILL_THRESHOLD_SECONDS', 30))
    AUTO_KILL_EXCLUDE_USERS = os.getenv('AUTO_KILL_EXCLUDE_USERS', 'root,replication').split(',')
    
    BINLOG_FORMAT = os.getenv('BINLOG_FORMAT', 'ROW')
    ENABLE_BINLOG_PARSING = os.getenv('ENABLE_BINLOG_PARSING', 'false').lower() == 'true'
    
    SLOW_QUERY_LOG_PATH = os.getenv('SLOW_QUERY_LOG_PATH', '')
    SLOW_QUERY_THRESHOLD = float(os.getenv('SLOW_QUERY_THRESHOLD', 1.0))
    
    DINGTALK_ENABLED = os.getenv('DINGTALK_ENABLED', 'false').lower() == 'true'
    DINGTALK_WEBHOOK = os.getenv('DINGTALK_WEBHOOK', '')
    DINGTALK_SECRET = os.getenv('DINGTALK_SECRET', '')
    DINGTALK_AT_MOBILES = os.getenv('DINGTALK_AT_MOBILES', '').split(',')
    
    ML_MODEL_PATH = os.getenv('ML_MODEL_PATH', 'deadlock_prediction_model.pkl')
    ML_PREDICTION_THRESHOLD = float(os.getenv('ML_PREDICTION_THRESHOLD', 0.7))
    ML_ENABLE_TRAINING = os.getenv('ML_ENABLE_TRAINING', 'true').lower() == 'true'
    
    EBPF_ENABLED = os.getenv('EBPF_ENABLED', 'true').lower() == 'true'
    EBPF_BPF_FILE = os.getenv('EBPF_BPF_FILE', 'ebpf_probes.c')
    EBPF_STATS_INTERVAL = int(os.getenv('EBPF_STATS_INTERVAL', 10))
    
    PROMETHEUS_ENABLED = os.getenv('PROMETHEUS_ENABLED', 'true').lower() == 'true'
    PROMETHEUS_PORT = int(os.getenv('PROMETHEUS_PORT', 9091))
    
    @classmethod
    def get_connection_params(cls):
        return {
            'host': cls.DB_HOST,
            'port': cls.DB_PORT,
            'user': cls.DB_USER,
            'password': cls.DB_PASSWORD,
            'database': cls.DB_NAME,
            'charset': 'utf8mb4',
            'cursorclass': None
        }
    
    @classmethod
    def get_db_params_without_db(cls):
        return {
            'host': cls.DB_HOST,
            'port': cls.DB_PORT,
            'user': cls.DB_USER,
            'password': cls.DB_PASSWORD,
            'charset': 'utf8mb4'
        }
