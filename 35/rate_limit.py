import os
import time
import threading
from functools import wraps
from flask import request, jsonify
from dotenv import load_dotenv

load_dotenv()

try:
    import redis
    USE_REDIS = bool(os.getenv('REDIS_RATE_LIMIT_URL'))
except ImportError:
    USE_REDIS = False

class InMemoryTokenBucket:
    def __init__(self):
        self._buckets = {}
        self._lock = threading.Lock()
    
    def _get_bucket(self, key):
        if key not in self._buckets:
            return None
        return self._buckets[key]
    
    def _set_bucket(self, key, tokens, last_update):
        self._buckets[key] = {
            'tokens': tokens,
            'last_update': last_update
        }
    
    def consume(self, key, rate, capacity, cost=1):
        with self._lock:
            now = time.time()
            bucket = self._get_bucket(key)
            
            if bucket is None:
                self._set_bucket(key, capacity - cost, now)
                return True, capacity - cost, capacity
            
            tokens = bucket['tokens']
            last_update = bucket['last_update']
            
            elapsed = now - last_update
            tokens += elapsed * rate
            tokens = min(tokens, capacity)
            
            if tokens >= cost:
                tokens -= cost
                self._set_bucket(key, tokens, now)
                return True, tokens, capacity
            else:
                self._set_bucket(key, tokens, now)
                return False, tokens, capacity

class RedisTokenBucket:
    def __init__(self, redis_url):
        self._redis = redis.from_url(redis_url)
        self._lock = threading.Lock()
    
    def consume(self, key, rate, capacity, cost=1):
        now = time.time()
        redis_key = f'ratelimit:{key}'
        
        with self._lock:
            pipe = self._redis.pipeline()
            pipe.hgetall(redis_key)
            pipe.expire(redis_key, 3600)
            result = pipe.execute()
            
            bucket_data = result[0] or {}
            
            if not bucket_data:
                pipe = self._redis.pipeline()
                pipe.hset(redis_key, 'tokens', capacity - cost)
                pipe.hset(redis_key, 'last_update', now)
                pipe.expire(redis_key, 3600)
                pipe.execute()
                return True, capacity - cost, capacity
            
            tokens = float(bucket_data.get(b'tokens', capacity))
            last_update = float(bucket_data.get(b'last_update', now))
            
            elapsed = now - last_update
            tokens += elapsed * rate
            tokens = min(tokens, capacity)
            
            if tokens >= cost:
                tokens -= cost
                pipe = self._redis.pipeline()
                pipe.hset(redis_key, 'tokens', tokens)
                pipe.hset(redis_key, 'last_update', now)
                pipe.expire(redis_key, 3600)
                pipe.execute()
                return True, tokens, capacity
            else:
                pipe = self._redis.pipeline()
                pipe.hset(redis_key, 'tokens', tokens)
                pipe.hset(redis_key, 'last_update', now)
                pipe.expire(redis_key, 3600)
                pipe.execute()
                return False, tokens, capacity

class RateLimiter:
    def __init__(self):
        self._default_rate = float(os.getenv('RATE_LIMIT_DEFAULT_RATE', '5'))
        self._default_capacity = int(os.getenv('RATE_LIMIT_DEFAULT_CAPACITY', '20'))
        self._header_name = os.getenv('RATE_LIMIT_HEADER', 'X-API-Key')
        
        redis_url = os.getenv('REDIS_RATE_LIMIT_URL')
        if redis_url and USE_REDIS:
            self._bucket = RedisTokenBucket(redis_url)
        else:
            self._bucket = InMemoryTokenBucket()
    
    def _get_identifier(self):
        api_key = request.headers.get(self._header_name)
        if api_key:
            return f'api:{api_key}'
        
        forwarded = request.headers.get('X-Forwarded-For')
        if forwarded:
            ip = forwarded.split(',')[0].strip()
        else:
            ip = request.remote_addr or 'unknown'
        
        return f'ip:{ip}'
    
    def check_rate(self, rate=None, capacity=None, cost=1):
        rate = rate or self._default_rate
        capacity = capacity or self._default_capacity
        
        identifier = self._get_identifier()
        allowed, remaining, total = self._bucket.consume(
            key=identifier,
            rate=rate,
            capacity=capacity,
            cost=cost
        )
        
        return {
            'allowed': allowed,
            'remaining': int(remaining),
            'total': total,
            'identifier': identifier
        }

rate_limiter = RateLimiter()

def rate_limit(rate=None, capacity=None, cost=1):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            result = rate_limiter.check_rate(rate=rate, capacity=capacity, cost=cost)
            
            response_headers = {
                'X-RateLimit-Limit': str(result['total']),
                'X-RateLimit-Remaining': str(result['remaining']),
                'X-RateLimit-Reset': str(int(time.time() + (result['total'] - result['remaining']) / (rate or rate_limiter._default_rate)))
            }
            
            if not result['allowed']:
                response = jsonify({
                    'error': 'Rate limit exceeded',
                    'message': 'Too many requests. Please try again later.',
                    'limit': result['total'],
                    'remaining': result['remaining']
                })
                response.status_code = 429
                for key, value in response_headers.items():
                    response.headers[key] = value
                return response
            
            response = f(*args, **kwargs)
            
            if hasattr(response, 'headers'):
                for key, value in response_headers.items():
                    response.headers[key] = value
            
            return response
        
        return decorated_function
    return decorator
