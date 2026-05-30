import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    REDIS_MODE = os.getenv('REDIS_MODE', 'standalone')
    
    REDIS_HOST = os.getenv('REDIS_HOST', 'localhost')
    REDIS_PORT = int(os.getenv('REDIS_PORT', 6379))
    REDIS_PASSWORD = os.getenv('REDIS_PASSWORD', None)
    REDIS_DB = int(os.getenv('REDIS_DB', 0))
    
    REDIS_CLUSTER_NODES = os.getenv('REDIS_CLUSTER_NODES', '').split(',') if os.getenv('REDIS_CLUSTER_NODES') else []
    
    FRAGMENTATION_THRESHOLD = float(os.getenv('FRAGMENTATION_THRESHOLD', 1.5))
    MIN_MEMORY_MB = int(os.getenv('MIN_MEMORY_MB', 1024))
    
    CELERY_BROKER_URL = os.getenv('CELERY_BROKER_URL', 'redis://localhost:6379/1')
    CELERY_RESULT_BACKEND = os.getenv('CELERY_RESULT_BACKEND', 'redis://localhost:6379/1')
    
    SCHEDULE_INTERVAL_MINUTES = int(os.getenv('SCHEDULE_INTERVAL_MINUTES', 60))
    
    STORAGE_REDIS_URL = os.getenv('STORAGE_REDIS_URL', 'redis://localhost:6379/2')
    
    PURGE_TIMEOUT = int(os.getenv('PURGE_TIMEOUT', 300))
