import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
    REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
    REDIS_DB = int(os.getenv("REDIS_DB", 0))
    REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", None)
    
    RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "localhost")
    RABBITMQ_PORT = int(os.getenv("RABBITMQ_PORT", 5672))
    RABBITMQ_USER = os.getenv("RABBITMQ_USER", "guest")
    RABBITMQ_PASSWORD = os.getenv("RABBITMQ_PASSWORD", "guest")
    
    CACHE_TTL = int(os.getenv("CACHE_TTL", 86400 * 7))
    
    HIGH_RISK_THRESHOLD = float(os.getenv("HIGH_RISK_THRESHOLD", 0.8))
    LOW_RISK_THRESHOLD = float(os.getenv("LOW_RISK_THRESHOLD", 0.3))
    
    MODEL_PATH = os.getenv("MODEL_PATH", "./models/content_classifier.h5")
    IMAGE_SIZE = (224, 224)
    
    REVIEW_QUEUE_NAME = "review_queue"
    ASYNC_TASK_QUEUE = "async_audit_tasks"
    RESULT_EXCHANGE = "audit_results"
    
    MAX_BATCH_SIZE = int(os.getenv("MAX_BATCH_SIZE", 100))

config = Config()
