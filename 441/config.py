import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
    
    ES_HOST = os.getenv('ES_HOST', 'localhost')
    ES_PORT = int(os.getenv('ES_PORT', '9200'))
    ES_USER = os.getenv('ES_USER', '')
    ES_PASSWORD = os.getenv('ES_PASSWORD', '')
    ES_INDEX = os.getenv('ES_INDEX', 'anomaly_detection')
    
    THREE_SIGMA_THRESHOLD = float(os.getenv('THREE_SIGMA_THRESHOLD', '3.0'))
    ISOLATION_FOREST_CONTAMINATION = float(os.getenv('ISOLATION_FOREST_CONTAMINATION', '0.05'))
    PROPHET_ANOMALY_THRESHOLD = float(os.getenv('PROPHET_ANOMALY_THRESHOLD', '0.95'))
    
    METRICS = ['qps', 'latency', 'error_rate']
    
    ANOMALY_SCORE_WEIGHTS = {
        'prophet': 0.35,
        'three_sigma': 0.30,
        'isolation_forest': 0.35
    }
    
    ROOT_CAUSE_HISTORY_WINDOW = int(os.getenv('ROOT_CAUSE_HISTORY_WINDOW', '7'))
