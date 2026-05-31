import redis
import json
import pickle
from typing import Optional, Any, Dict, List
import logging
from datetime import timedelta

from ..config import settings

logger = logging.getLogger(__name__)


class CacheService:
    def __init__(self):
        self.client: Optional[redis.Redis] = None
        self._connect()

    def _connect(self):
        try:
            self.client = redis.Redis(
                host=settings.redis_host,
                port=settings.redis_port,
                db=settings.redis_db,
                password=settings.redis_password,
                decode_responses=True,
                socket_timeout=5
            )
            self.client.ping()
            logger.info("Connected to Redis successfully")
        except Exception as e:
            logger.warning(f"Redis connection failed: {e}. Using in-memory cache.")
            self.client = None
            self._memory_cache: Dict[str, Any] = {}

    def get(self, key: str) -> Optional[Any]:
        try:
            if self.client:
                data = self.client.get(key)
                if data:
                    return json.loads(data) if isinstance(data, str) else data
            else:
                return self._memory_cache.get(key)
        except Exception as e:
            logger.warning(f"Cache get error for {key}: {e}")
        return None

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        try:
            serialized = json.dumps(value, default=str)
            if self.client:
                if ttl:
                    self.client.setex(key, ttl, serialized)
                else:
                    self.client.set(key, serialized)
            else:
                self._memory_cache[key] = value
            return True
        except Exception as e:
            logger.warning(f"Cache set error for {key}: {e}")
            return False

    def delete(self, key: str) -> bool:
        try:
            if self.client:
                self.client.delete(key)
            else:
                self._memory_cache.pop(key, None)
            return True
        except Exception as e:
            logger.warning(f"Cache delete error for {key}: {e}")
            return False

    def exists(self, key: str) -> bool:
        try:
            if self.client:
                return self.client.exists(key) > 0
            else:
                return key in self._memory_cache
        except Exception as e:
            logger.warning(f"Cache exists error for {key}: {e}")
            return False

    def get_or_set(self, key: str, fetch_func, ttl: Optional[int] = None) -> Any:
        cached = self.get(key)
        if cached is not None:
            logger.debug(f"Cache hit for {key}")
            return cached

        logger.debug(f"Cache miss for {key}, fetching...")
        value = fetch_func()
        if value is not None:
            self.set(key, value, ttl)
        return value

    def clear_pattern(self, pattern: str) -> int:
        try:
            if self.client:
                keys = self.client.keys(pattern)
                if keys:
                    return self.client.delete(*keys)
            else:
                deleted = 0
                for key in list(self._memory_cache.keys()):
                    if self._match_pattern(key, pattern):
                        del self._memory_cache[key]
                        deleted += 1
                return deleted
        except Exception as e:
            logger.warning(f"Cache clear pattern error: {e}")
            return 0

    def _match_pattern(self, key: str, pattern: str) -> bool:
        import fnmatch
        return fnmatch.fnmatch(key, pattern)

    def set_search(self, query: str, source: str, data: Any) -> bool:
        key = f"search:{source}:{query.lower()}"
        return self.set(key, data, settings.cache_ttl_search)

    def get_search(self, query: str, source: str) -> Optional[Any]:
        key = f"search:{source}:{query.lower()}"
        return self.get(key)

    def set_paper(self, doi: str, data: Any) -> bool:
        key = f"paper:{doi}"
        return self.set(key, data, settings.cache_ttl_paper)

    def get_paper(self, doi: str) -> Optional[Any]:
        key = f"paper:{doi}"
        return self.get(key)

    def set_graph(self, graph_id: str, data: Any) -> bool:
        key = f"graph:{graph_id}"
        return self.set(key, data, settings.cache_ttl_graph)

    def get_graph(self, graph_id: str) -> Optional[Any]:
        key = f"graph:{graph_id}"
        return self.get(key)

    def set_trends(self, cache_key: str, data: Any) -> bool:
        key = f"trends:{cache_key}"
        return self.set(key, data, 3600)

    def get_trends(self, cache_key: str) -> Optional[Any]:
        key = f"trends:{cache_key}"
        return self.get(key)

    def clear_all(self) -> bool:
        try:
            if self.client:
                self.client.flushdb()
            else:
                self._memory_cache.clear()
            logger.info("Cache cleared")
            return True
        except Exception as e:
            logger.warning(f"Cache clear error: {e}")
            return False
