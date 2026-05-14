import os
import json
import time
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime, timedelta
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    logger.warning("Redis not installed. Install with 'pip install redis' to enable caching.")

REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", None)
REDIS_DB = int(os.getenv("REDIS_DB", "0"))
CACHE_ENABLED = os.getenv("CACHE_ENABLED", "false").lower() == "true"

HOT_POSTS_KEY = "hot_posts"
HOT_POSTS_TTL = 600
POST_VIEW_PREFIX = "post_view:"
POST_VIEW_TTL = 3600


class CacheManager:
    _instance: Optional['CacheManager'] = None
    _redis_client: Optional['redis.Redis'] = None

    def __new__(cls) -> 'CacheManager':
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._init_redis()
        return cls._instance

    def _init_redis(self) -> None:
        if not REDIS_AVAILABLE or not CACHE_ENABLED:
            self._redis_client = None
            return
        try:
            self._redis_client = redis.Redis(
                host=REDIS_HOST,
                port=REDIS_PORT,
                password=REDIS_PASSWORD,
                db=REDIS_DB,
                decode_responses=True,
                socket_timeout=5,
                socket_connect_timeout=5,
            )
            self._redis_client.ping()
            logger.info("Redis connected successfully")
        except Exception as e:
            logger.warning(f"Failed to connect to Redis: {e}")
            self._redis_client = None

    def is_available(self) -> bool:
        return self._redis_client is not None

    def _serialize(self, data: Any) -> str:
        def default(obj: Any) -> Any:
            if isinstance(obj, datetime):
                return obj.isoformat()
            raise TypeError(f"Object of type {type(obj)} is not JSON serializable")
        return json.dumps(data, default=default)

    def _deserialize(self, data: str) -> Any:
        return json.loads(data)

    def get_hot_posts(self) -> Optional[List[Dict[str, Any]]]:
        if not self.is_available():
            return None
        try:
            data = self._redis_client.get(HOT_POSTS_KEY)
            if data:
                return self._deserialize(data)
        except Exception as e:
            logger.error(f"Error getting hot posts from cache: {e}")
        return None

    def set_hot_posts(self, posts: List[Dict[str, Any]]) -> bool:
        if not self.is_available():
            return False
        try:
            serialized = self._serialize(posts)
            self._redis_client.setex(HOT_POSTS_KEY, HOT_POSTS_TTL, serialized)
            return True
        except Exception as e:
            logger.error(f"Error setting hot posts to cache: {e}")
            return False

    def invalidate_hot_posts(self) -> bool:
        if not self.is_available():
            return False
        try:
            self._redis_client.delete(HOT_POSTS_KEY)
            return True
        except Exception as e:
            logger.error(f"Error invalidating hot posts cache: {e}")
            return False

    def increment_view_count(self, post_id: int) -> int:
        if not self.is_available():
            return 0
        try:
            key = f"{POST_VIEW_PREFIX}{post_id}"
            count = self._redis_client.incr(key)
            if count == 1:
                self._redis_client.expire(key, POST_VIEW_TTL)
            return count
        except Exception as e:
            logger.error(f"Error incrementing view count: {e}")
            return 0

    def get_view_count(self, post_id: int) -> int:
        if not self.is_available():
            return 0
        try:
            key = f"{POST_VIEW_PREFIX}{post_id}"
            count = self._redis_client.get(key)
            return int(count) if count else 0
        except Exception as e:
            logger.error(f"Error getting view count: {e}")
            return 0

    def get_all_view_counts(self) -> Dict[int, int]:
        if not self.is_available():
            return {}
        try:
            pattern = f"{POST_VIEW_PREFIX}*"
            keys = self._redis_client.keys(pattern)
            counts = {}
            for key in keys:
                post_id = int(key.replace(POST_VIEW_PREFIX, ""))
                count = self._redis_client.get(key)
                if count:
                    counts[post_id] = int(count)
            return counts
        except Exception as e:
            logger.error(f"Error getting all view counts: {e}")
            return {}

    def clear_view_count(self, post_id: int) -> bool:
        if not self.is_available():
            return False
        try:
            key = f"{POST_VIEW_PREFIX}{post_id}"
            self._redis_client.delete(key)
            return True
        except Exception as e:
            logger.error(f"Error clearing view count: {e}")
            return False


cache_manager = CacheManager()


def get_hot_posts_from_cache() -> Optional[List[Dict[str, Any]]]:
    return cache_manager.get_hot_posts()


def set_hot_posts_to_cache(posts: List[Dict[str, Any]]) -> bool:
    return cache_manager.set_hot_posts(posts)


def invalidate_hot_posts_cache() -> bool:
    return cache_manager.invalidate_hot_posts()


def increment_post_view(post_id: int) -> int:
    return cache_manager.increment_view_count(post_id)


def get_post_view_count(post_id: int) -> int:
    return cache_manager.get_view_count(post_id)
