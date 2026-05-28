import json
import logging
import time
from typing import Any, Dict, List, Optional

import redis

from config.config import REDIS_CONFIG

logger = logging.getLogger(__name__)


class RedisManager:
    _instance = None
    _client = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, config: Optional[Dict] = None):
        if self._client is None:
            cfg = config or REDIS_CONFIG
            self._client = redis.Redis(
                host=cfg["host"],
                port=cfg["port"],
                db=cfg["db"],
                password=cfg.get("password"),
                socket_timeout=cfg.get("socket_timeout", 5),
                retry_on_timeout=cfg.get("retry_on_timeout", True),
                max_connections=cfg.get("max_connections", 50),
                decode_responses=True,
            )
            logger.info("Redis connection pool initialized: %s:%d/%d", cfg["host"], cfg["port"], cfg["db"])

    @property
    def client(self) -> redis.Redis:
        return self._client

    def ping(self) -> bool:
        try:
            return self._client.ping()
        except redis.ConnectionError as e:
            logger.error("Redis ping failed: %s", e)
            return False

    def set(self, key: str, value: Any, ttl_seconds: Optional[int] = None) -> bool:
        try:
            if isinstance(value, (dict, list)):
                value = json.dumps(value, default=str)
            elif not isinstance(value, (str, bytes, int, float)):
                value = str(value)
            self._client.set(key, value, ex=ttl_seconds)
            return True
        except redis.RedisError as e:
            logger.error("Redis set failed for key %s: %s", key, e)
            return False

    def get(self, key: str) -> Optional[Any]:
        try:
            raw = self._client.get(key)
            if raw is None:
                return None
            try:
                return json.loads(raw)
            except (json.JSONDecodeError, TypeError):
                return raw
        except redis.RedisError as e:
            logger.error("Redis get failed for key %s: %s", key, e)
            return None

    def delete(self, key: str) -> bool:
        try:
            return bool(self._client.delete(key))
            return True
        except redis.RedisError as e:
            logger.error("Redis delete failed for key %s: %s", key, e)
            return False

    def exists(self, key: str) -> bool:
        try:
            return bool(self._client.exists(key))
        except redis.RedisError as e:
            logger.error("Redis exists failed for key %s: %s", key, e)
            return False

    def hset(self, key: str, field: str, value: Any, ttl_seconds: Optional[int] = None) -> bool:
        try:
            if isinstance(value, (dict, list)):
                value = json.dumps(value, default=str)
            self._client.hset(key, field, value)
            if ttl_seconds:
                self._client.expire(key, ttl_seconds)
            return True
        except redis.RedisError as e:
            logger.error("Redis hset failed for key %s field %s: %s", key, field, e)
            return False

    def hget(self, key: str, field: str) -> Optional[Any]:
        try:
            raw = self._client.hget(key, field)
            if raw is None:
                return None
            try:
                return json.loads(raw)
            except (json.JSONDecodeError, TypeError):
                return raw
        except redis.RedisError as e:
            logger.error("Redis hget failed for key %s field %s: %s", key, field, e)
            return None

    def hgetall(self, key: str) -> Optional[Dict[str, Any]]:
        try:
            raw = self._client.hgetall(key)
            result = {}
            for k, v in raw.items():
                try:
                    result[k] = json.loads(v)
                except (json.JSONDecodeError, TypeError):
                    result[k] = v
            return result
        except redis.RedisError as e:
            logger.error("Redis hgetall failed for key %s: %s", key, e)
            return None

    def lpush(self, key: str, value: Any, ttl_seconds: Optional[int] = None) -> bool:
        try:
            if isinstance(value, (dict, list)):
                value = json.dumps(value, default=str)
            self._client.lpush(key, value)
            if ttl_seconds:
                self._client.expire(key, ttl_seconds)
            return True
        except redis.RedisError as e:
            logger.error("Redis lpush failed for key %s: %s", key, e)
            return False

    def lrange(self, key: str, start: int = 0, end: int = -1) -> List[Any]:
        try:
            raw_list = self._client.lrange(key, start, end)
            result = []
            for raw in raw_list:
                try:
                    result.append(json.loads(raw))
                except (json.JSONDecodeError, TypeError):
                    result.append(raw)
            return result
        except redis.RedisError as e:
            logger.error("Redis lrange failed for key %s: %s", key, e)
            return []

    def incr(self, key: str, amount: int = 1, ttl_seconds: Optional[int] = None) -> Optional[int]:
        try:
            result = self._client.incrby(key, amount)
            if ttl_seconds and self._client.ttl(key) < 0:
                self._client.expire(key, ttl_seconds)
            return result
        except redis.RedisError as e:
            logger.error("Redis incr failed for key %s: %s", key, e)
            return None

    def zadd(self, key: str, value: str, score: float) -> bool:
        try:
            return bool(self._client.zadd(key, {value: score}))
            return True
        except redis.RedisError as e:
            logger.error("Redis zadd failed for key %s: %s", key, e)
            return False

    def zscore(self, key: str, value: str) -> Optional[float]:
        try:
            return self._client.zscore(key, value)
        except redis.RedisError as e:
            logger.error("Redis zscore failed for key %s value %s: %s", key, value, e)
            return None

    def get_customer_profile(self, customer_id: str) -> Optional[Dict]:
        return self.hgetall(f"customer:{customer_id}", "profile")

    def update_customer_profile(self, customer_id: str, profile: Dict) -> bool:
        return self.hset(f"customer:{customer_id}", "profile", profile)

    def get_transaction_history(self, customer_id: str, limit: int = 20) -> List:
        return self.lrange(f"customer:{customer_id}:tx_history", 0, limit - 1)

    def add_transaction_to_history(self, customer_id: str, transaction: Dict) -> bool:
        key = f"customer:{customer_id}:tx_history"
        result = self.lpush(key, transaction)
        if result:
            self._client.ltrim(key, 0, 99)
        return result

    def get_customer_fraud_score(self, customer_id: str) -> Optional[float]:
        return self.zscore("customer_risk_scores", customer_id)

    def set_customer_fraud_score(self, customer_id: str, score: float) -> bool:
        return self.zadd("customer_risk_scores", customer_id, float(score))

    def get_merchant_risk(self, merchant_id: str) -> Optional[Dict]:
        return self.hgetall(f"merchant:{merchant_id}", "risk")

    def set_merchant_risk(self, merchant_id: str, risk_data: Dict) -> bool:
        return self.hset(f"merchant:{merchant_id}", "risk", risk_data)

    def get_customer_velocity(self, customer_id: str, window_seconds: int = 300) -> Dict:
        now = int(time.time())
        key = f"customer:{customer_id}:velocity"
        recent = self.lrange(key, 0, -1)
        cutoff = now - window_seconds
        recent_amount = [v for v in recent if isinstance(v, dict) and v.get("timestamp", 0) > cutoff]
        self._client.ltrim(key, 0, len(recent_amount))
        return {
            "count": len(recent_amount),
            "total_amount": sum(t.get("amount", 0) for t in recent_amount),
            "window_seconds": window_seconds,
        }

    def record_velocity_entry(self, customer_id: str, amount: float, timestamp: float) -> bool:
        key = f"customer:{customer_id}:velocity"
        return self.lpush(key, {"amount": amount, "timestamp": timestamp})

    def get_alert_rate_limit(self, customer_id: str) -> int:
        key = f"alert_rate:{customer_id}"
        current = self.get(key)
        return int(current) if current else 0

    def increment_alert_rate(self, customer_id: str, cooldown: int = 60) -> int:
        key = f"alert_rate:{customer_id}"
        current = self.incr(key, 1, ttl_seconds=cooldown)
        return current or 0

    def get_model_version(self, model_name: str) -> Optional[str]:
        return self.hget("model_versions", model_name)

    def set_model_version(self, model_name: str, version: str) -> bool:
        return self.hset("model_versions", model_name, version)

    def get_scored_transaction(self, tx_id: str) -> Optional[Dict]:
        return self.hgetall(f"scored:{tx_id}")

    def cache_scored_transaction(self, tx_id: str, score_data: Dict, ttl: int = 3600) -> bool:
        return self.hset(f"scored:{tx_id}", "data", score_data, ttl_seconds=ttl)
