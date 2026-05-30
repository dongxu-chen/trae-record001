import redis
import os
from dotenv import load_dotenv

load_dotenv()

redis_client = None


def init_redis(app=None):
    global redis_client
    host = os.getenv('REDIS_HOST', 'localhost')
    port = int(os.getenv('REDIS_PORT', 6379))
    password = os.getenv('REDIS_PASSWORD')
    db = int(os.getenv('REDIS_DB', 0))
    
    redis_client = redis.Redis(
        host=host,
        port=port,
        password=password,
        db=db,
        decode_responses=True
    )
    return redis_client


def get_redis():
    global redis_client
    if redis_client is None:
        init_redis()
    return redis_client
