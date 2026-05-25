import json
import logging
from typing import List, Dict, Optional, Any
from datetime import datetime

import redis

from config import config
from data.models import UserProfile, NewsFeatures, RecommendationResult

logger = logging.getLogger(__name__)


class RedisClient:
    def __init__(self, host: str = None, port: int = None, db: int = None):
        self.host = host or config.REDIS_HOST
        self.port = port or config.REDIS_PORT
        self.db = db or config.REDIS_DB
        self.redis = None
        self._connect()

    def _connect(self):
        try:
            self.redis = redis.Redis(
                host=self.host,
                port=self.port,
                db=self.db,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5,
                retry_on_timeout=True
            )
            self.redis.ping()
            logger.info(f"Connected to Redis at {self.host}:{self.port}/{self.db}")
        except Exception as e:
            logger.warning(f"Failed to connect to Redis: {e}. Using in-memory cache.")
            self.redis = None
            self._memory_cache = {}

    def _execute(self, operation: str, *args, **kwargs) -> Any:
        if self.redis:
            try:
                return getattr(self.redis, operation)(*args, **kwargs)
            except Exception as e:
                logger.warning(f"Redis operation {operation} failed: {e}")
                return self._fallback(operation, *args, **kwargs)
        else:
            return self._fallback(operation, *args, **kwargs)

    def _fallback(self, operation: str, *args, **kwargs) -> Any:
        key = args[0] if args else ''
        if operation == 'get':
            return self._memory_cache.get(key)
        elif operation == 'set':
            self._memory_cache[key] = args[1]
            return True
        elif operation == 'setex':
            self._memory_cache[key] = args[2]
            return True
        elif operation == 'delete':
            self._memory_cache.pop(key, None)
            return 1
        elif operation == 'exists':
            return key in self._memory_cache
        elif operation == 'hget':
            hash_key = key
            field = args[1]
            hash_data = self._memory_cache.get(hash_key, {})
            return hash_data.get(field)
        elif operation == 'hset':
            hash_key = key
            mapping = kwargs.get('mapping') or {args[1]: args[2]}
            if hash_key not in self._memory_cache:
                self._memory_cache[hash_key] = {}
            self._memory_cache[hash_key].update(mapping)
            return len(mapping)
        elif operation == 'hgetall':
            return self._memory_cache.get(key, {})
        elif operation == 'zadd':
            sorted_key = key
            mapping = kwargs.get('mapping') or {args[1]: args[2]}
            if sorted_key not in self._memory_cache:
                self._memory_cache[sorted_key] = {}
            self._memory_cache[sorted_key].update(mapping)
            return len(mapping)
        elif operation == 'zrange':
            sorted_key = key
            start, end = args[1], args[2]
            desc = kwargs.get('desc', False)
            withscores = kwargs.get('withscores', False)
            data = self._memory_cache.get(sorted_key, {})
            sorted_items = sorted(data.items(), key=lambda x: x[1], reverse=desc)
            result = sorted_items[start:end + 1] if end != -1 else sorted_items[start:]
            if withscores:
                return result
            return [item[0] for item in result]
        elif operation == 'zincrby':
            sorted_key = key
            amount, value = args[1], args[2]
            if sorted_key not in self._memory_cache:
                self._memory_cache[sorted_key] = {}
            self._memory_cache[sorted_key][value] = self._memory_cache[sorted_key].get(value, 0) + amount
            return self._memory_cache[sorted_key][value]
        elif operation == 'incr':
            self._memory_cache[key] = self._memory_cache.get(key, 0) + 1
            return self._memory_cache[key]
        elif operation == 'lpush':
            list_key = key
            values = args[1:]
            if list_key not in self._memory_cache:
                self._memory_cache[list_key] = []
            for value in reversed(values):
                self._memory_cache[list_key].insert(0, value)
            return len(self._memory_cache[list_key])
        elif operation == 'lrange':
            list_key = key
            start, end = args[1], args[2]
            data = self._memory_cache.get(list_key, [])
            return data[start:end + 1] if end != -1 else data[start:]
        elif operation == 'ltrim':
            list_key = key
            start, end = args[1], args[2]
            if list_key in self._memory_cache:
                data = self._memory_cache[list_key]
                self._memory_cache[list_key] = data[start:end + 1] if end != -1 else data[start:]
            return True
        elif operation == 'sadd':
            set_key = key
            members = args[1:]
            if set_key not in self._memory_cache:
                self._memory_cache[set_key] = set()
            count = 0
            for member in members:
                if member not in self._memory_cache[set_key]:
                    self._memory_cache[set_key].add(member)
                    count += 1
            return count
        elif operation == 'smembers':
            return list(self._memory_cache.get(key, set()))
        return None

    def set_user_profile(self, user_id: int, profile: UserProfile, ttl: int = None) -> bool:
        key = f"user:profile:{user_id}"
        ttl = ttl or config.USER_PROFILE_TTL
        profile_dict = profile.to_dict()
        value = json.dumps(profile_dict, ensure_ascii=False)
        return self._execute('setex', key, ttl, value)

    def get_user_profile(self, user_id: int) -> Optional[UserProfile]:
        key = f"user:profile:{user_id}"
        value = self._execute('get', key)
        if not value:
            return None

        try:
            data = json.loads(value)
            import numpy as np
            embedding = np.array(data['embedding']) if data.get('embedding') else None
            last_updated = datetime.fromisoformat(data['last_updated']) if data.get('last_updated') else datetime.now()

            return UserProfile(
                user_id=data['user_id'],
                category_preferences=data.get('category_preferences', {}),
                recent_behavior=data.get('recent_behavior', []),
                embedding=embedding,
                last_updated=last_updated
            )
        except (json.JSONDecodeError, KeyError) as e:
            logger.error(f"Failed to parse user profile {user_id}: {e}")
            return None

    def set_news_features(self, news_id: int, features: NewsFeatures, ttl: int = None) -> bool:
        key = f"news:features:{news_id}"
        ttl = ttl or config.NEWS_CACHE_TTL
        features_dict = features.to_dict()
        value = json.dumps(features_dict, ensure_ascii=False)
        return self._execute('setex', key, ttl, value)

    def get_news_features(self, news_id: int) -> Optional[NewsFeatures]:
        key = f"news:features:{news_id}"
        value = self._execute('get', key)
        if not value:
            return None

        try:
            data = json.loads(value)
            import numpy as np
            embedding = np.array(data['embedding']) if data.get('embedding') else None

            return NewsFeatures(
                news_id=data['news_id'],
                category_id=data['category_id'],
                popularity_score=data.get('popularity_score', 0.0),
                embedding=embedding,
                hot_score=data.get('hot_score', 0.0),
                click_count=data.get('click_count', 0),
                like_count=data.get('like_count', 0),
                share_count=data.get('share_count', 0)
            )
        except (json.JSONDecodeError, KeyError) as e:
            logger.error(f"Failed to parse news features {news_id}: {e}")
            return None

    def get_batch_news_features(self, news_ids: List[int]) -> Dict[int, NewsFeatures]:
        if not news_ids:
            return {}

        pipe = self.redis.pipeline() if self.redis else None
        if pipe:
            for news_id in news_ids:
                pipe.get(f"news:features:{news_id}")
            try:
                values = pipe.execute()
            except Exception as e:
                logger.warning(f"Pipeline get failed: {e}")
                values = [self.get_news_features(nid) for nid in news_ids]
        else:
            values = [self.get_news_features(nid) for nid in news_ids]

        results = {}
        for news_id, value in zip(news_ids, values):
            if isinstance(value, str):
                try:
                    data = json.loads(value)
                    import numpy as np
                    embedding = np.array(data['embedding']) if data.get('embedding') else None
                    results[news_id] = NewsFeatures(
                        news_id=data['news_id'],
                        category_id=data['category_id'],
                        popularity_score=data.get('popularity_score', 0.0),
                        embedding=embedding,
                        hot_score=data.get('hot_score', 0.0),
                        click_count=data.get('click_count', 0),
                        like_count=data.get('like_count', 0),
                        share_count=data.get('share_count', 0)
                    )
                except Exception:
                    continue
            elif isinstance(value, NewsFeatures):
                results[news_id] = value

        return results

    def update_news_statistics(self, news_id: int, behavior_type: str) -> bool:
        key = f"news:stats:{news_id}"
        field_map = {
            'view': 'click_count',
            'like': 'like_count',
            'share': 'share_count'
        }

        field = field_map.get(behavior_type)
        if not field:
            return False

        result = self._execute('hincrby', key, field, 1)

        self._update_hot_score(news_id)

        return result is not None

    def _update_hot_score(self, news_id: int):
        key = f"news:stats:{news_id}"
        stats = self._execute('hgetall', key)

        if stats:
            clicks = int(stats.get('click_count', 0))
            likes = int(stats.get('like_count', 0))
            shares = int(stats.get('share_count', 0))

            hot_score = clicks * 1.0 + likes * 3.0 + shares * 5.0

            self._execute('zadd', 'news:hot', mapping={str(news_id): hot_score})

    def get_hot_news(self, count: int = None) -> List[tuple]:
        count = count or config.HOT_NEWS_COUNT
        results = self._execute(
            'zrange',
            'news:hot',
            0,
            count - 1,
            desc=True,
            withscores=True
        )
        return [(int(news_id), score) for news_id, score in results]

    def add_user_behavior(self, user_id: int, behavior: Dict, max_history: int = 100) -> bool:
        key = f"user:behavior:{user_id}"
        value = json.dumps(behavior, ensure_ascii=False)
        self._execute('lpush', key, value)
        self._execute('ltrim', key, 0, max_history - 1)
        return True

    def get_user_behavior_history(self, user_id: int, count: int = 50) -> List[Dict]:
        key = f"user:behavior:{user_id}"
        values = self._execute('lrange', key, 0, count - 1)

        behaviors = []
        for value in values:
            try:
                behaviors.append(json.loads(value))
            except json.JSONDecodeError:
                continue

        return behaviors

    def add_recent_viewed(self, user_id: int, news_id: int, max_count: int = 200) -> bool:
        key = f"user:viewed:{user_id}"
        self._execute('sadd', key, str(news_id))

        members = self._execute('smembers', key)
        if len(members) > max_count:
            self._execute('delete', key)

        return True

    def get_recent_viewed(self, user_id: int) -> List[int]:
        key = f"user:viewed:{user_id}"
        members = self._execute('smembers', key)
        return [int(m) for m in members]

    def set_recommendations(
        self,
        user_id: int,
        recommendations: List[RecommendationResult],
        ttl: int = 300
    ) -> bool:
        key = f"user:recommendations:{user_id}"
        value = json.dumps([r.to_dict() for r in recommendations], ensure_ascii=False)
        return self._execute('setex', key, ttl, value)

    def get_recommendations(self, user_id: int) -> Optional[List[RecommendationResult]]:
        key = f"user:recommendations:{user_id}"
        value = self._execute('get', key)
        if not value:
            return None

        try:
            data = json.loads(value)
            return [RecommendationResult(
                news_id=r['news_id'],
                score=r['score'],
                category=r['category'],
                rank=r['rank'],
                is_hot=r.get('is_hot', False),
                reason=r.get('reason', '')
            ) for r in data]
        except (json.JSONDecodeError, KeyError) as e:
            logger.error(f"Failed to parse recommendations for user {user_id}: {e}")
            return None

    def set_news_info(self, news_dict: Dict) -> bool:
        key = f"news:info:{news_dict['news_id']}"
        value = json.dumps(news_dict, ensure_ascii=False)
        return self._execute('setex', key, config.NEWS_CACHE_TTL, value)

    def get_news_info(self, news_id: int) -> Optional[Dict]:
        key = f"news:info:{news_id}"
        value = self._execute('get', key)
        if not value:
            return None

        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return None

    def get_batch_news_info(self, news_ids: List[int]) -> Dict[int, Dict]:
        if not news_ids:
            return {}

        results = {}
        for news_id in news_ids:
            info = self.get_news_info(news_id)
            if info:
                results[news_id] = info

        return results

    def clear_user_cache(self, user_id: int) -> bool:
        keys = [
            f"user:profile:{user_id}",
            f"user:behavior:{user_id}",
            f"user:viewed:{user_id}",
            f"user:recommendations:{user_id}"
        ]
        for key in keys:
            self._execute('delete', key)
        return True

    def get_all_news_ids(self) -> List[int]:
        if self.redis:
            try:
                keys = self.redis.keys("news:info:*")
                return [int(k.split(':')[-1]) for k in keys]
            except Exception as e:
                logger.warning(f"Failed to get news keys: {e}")
        return list(range(config.NUM_NEWS))

    def update_category_popularity(self, category_id: int, increment: float = 1.0) -> float:
        key = "category:popularity"
        return self._execute('zincrby', key, increment, str(category_id))

    def get_category_popularity(self, top_n: int = 10) -> List[tuple]:
        results = self._execute(
            'zrange',
            'category:popularity',
            0,
            top_n - 1,
            desc=True,
            withscores=True
        )
        return [(int(cat_id), score) for cat_id, score in results]

    def close(self):
        if self.redis:
            self.redis.close()
            logger.info("Redis connection closed")
