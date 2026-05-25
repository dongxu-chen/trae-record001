import json
import pickle
import redis
from typing import Optional, Any, List, Dict
from datetime import datetime
from config import settings


class RedisCache:
    def __init__(self, host: str = None, port: int = None, 
                 db: int = None, password: str = None):
        self.host = host or settings.REDIS_HOST
        self.port = port or settings.REDIS_PORT
        self.db = db or settings.REDIS_DB
        self.password = password or settings.REDIS_PASSWORD
        self.ttl = settings.CACHE_TTL
        self._client = None
    
    @property
    def client(self) -> redis.Redis:
        if self._client is None:
            try:
                self._client = redis.Redis(
                    host=self.host,
                    port=self.port,
                    db=self.db,
                    password=self.password if self.password else None,
                    decode_responses=False
                )
                self._client.ping()
            except Exception as e:
                print(f"Warning: Redis connection failed: {e}")
                print("Using in-memory cache fallback")
                self._client = InMemoryCache()
        return self._client
    
    def _make_key(self, prefix: str, key: str) -> str:
        return f"{prefix}:{key}"
    
    def set(self, prefix: str, key: str, value: Any, ttl: Optional[int] = None):
        full_key = self._make_key(prefix, key)
        ttl = ttl or self.ttl
        
        try:
            serialized = pickle.dumps(value)
            self.client.setex(full_key, ttl, serialized)
        except Exception:
            serialized = json.dumps(value, default=str)
            self.client.setex(full_key, ttl, serialized)
    
    def get(self, prefix: str, key: str) -> Optional[Any]:
        full_key = self._make_key(prefix, key)
        value = self.client.get(full_key)
        
        if value is None:
            return None
        
        try:
            return pickle.loads(value)
        except Exception:
            try:
                return json.loads(value)
            except Exception:
                return value
    
    def delete(self, prefix: str, key: str):
        full_key = self._make_key(prefix, key)
        self.client.delete(full_key)
    
    def exists(self, prefix: str, key: str) -> bool:
        full_key = self._make_key(prefix, key)
        return bool(self.client.exists(full_key))
    
    def clear_pattern(self, pattern: str):
        keys = self.client.keys(pattern)
        if keys:
            self.client.delete(*keys)
    
    def clear_prefix(self, prefix: str):
        self.clear_pattern(f"{prefix}:*")
    
    def close(self):
        if self._client and hasattr(self._client, 'close'):
            self._client.close()


class InMemoryCache:
    def __init__(self):
        self._cache = {}
    
    def setex(self, key: str, ttl: int, value: Any):
        self._cache[key] = value
    
    def get(self, key: str) -> Optional[Any]:
        return self._cache.get(key)
    
    def delete(self, *keys):
        for key in keys:
            self._cache.pop(key, None)
    
    def exists(self, key: str) -> bool:
        return key in self._cache
    
    def keys(self, pattern: str) -> List[str]:
        import fnmatch
        return [k for k in self._cache.keys() if fnmatch.fnmatch(k, pattern)]


class RecommendationCache:
    def __init__(self, cache: RedisCache = None):
        self.cache = cache or RedisCache()
        self._prefix_recommendations = "recs"
        self._prefix_user_profile = "user_profile"
        self._prefix_bandit = "bandit"
    
    def get_recommendations(self, user_id: str) -> Optional[List[Dict]]:
        return self.cache.get(self._prefix_recommendations, user_id)
    
    def set_recommendations(self, user_id: str, recommendations: List[Dict], ttl: int = None):
        self.cache.set(self._prefix_recommendations, user_id, recommendations, ttl)
    
    def delete_recommendations(self, user_id: str):
        self.cache.delete(self._prefix_recommendations, user_id)
    
    def get_user_profile(self, user_id: str) -> Optional[Dict]:
        return self.cache.get(self._prefix_user_profile, user_id)
    
    def set_user_profile(self, user_id: str, profile: Dict, ttl: int = None):
        self.cache.set(self._prefix_user_profile, user_id, profile, ttl)
    
    def get_bandit_state(self, bandit_id: str) -> Optional[Dict]:
        return self.cache.get(self._prefix_bandit, bandit_id)
    
    def set_bandit_state(self, bandit_id: str, state: Dict, ttl: int = None):
        self.cache.set(self._prefix_bandit, bandit_id, state, ttl)
    
    def invalidate_user(self, user_id: str):
        self.delete_recommendations(user_id)
        self.cache.delete(self._prefix_user_profile, user_id)
