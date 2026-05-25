import json
import time
from typing import Any, Dict, List, Optional, Tuple
from contextlib import contextmanager

import redis
from redis.connection import ConnectionPool

from config import config


class RedisClient:
    _instance = None
    _pool = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._init_pool()
        return cls._instance

    def _init_pool(self):
        redis_config = config.redis
        self._pool = ConnectionPool(
            host=redis_config.host,
            port=redis_config.port,
            db=redis_config.db,
            password=redis_config.password if redis_config.password else None,
            max_connections=redis_config.max_connections,
            socket_timeout=redis_config.socket_timeout,
            socket_connect_timeout=redis_config.socket_connect_timeout,
        )

    @contextmanager
    def get_client(self):
        client = redis.Redis(connection_pool=self._pool)
        try:
            yield client
        finally:
            pass

    def set_user_profile(self, user_id: str, profile: Dict[str, Any], ttl: int = 86400 * 7) -> bool:
        key = f"user:profile:{user_id}"
        with self.get_client() as r:
            return r.setex(key, ttl, json.dumps(profile))

    def get_user_profile(self, user_id: str) -> Optional[Dict[str, Any]]:
        key = f"user:profile:{user_id}"
        with self.get_client() as r:
            data = r.get(key)
            return json.loads(data) if data else None

    def _get_sliding_window_key(self, user_id: str, ad_id: str, window: str) -> str:
        return f"freq:sw:{user_id}:{ad_id}:{window}"

    def add_impression_sliding_window(
        self,
        user_id: str,
        ad_id: str,
        window: str,
        window_seconds: int,
        limit: int,
    ) -> Tuple[int, bool, int]:
        key = self._get_sliding_window_key(user_id, ad_id, window)
        timestamp = int(time.time() * 1000)
        member = f"{timestamp}:{time.time_ns()}"
        
        lua_script = """
        local key = KEYS[1]
        local timestamp = tonumber(ARGV[1])
        local member = ARGV[2]
        local window_ms = tonumber(ARGV[3])
        local limit = tonumber(ARGV[4])
        
        local cutoff = timestamp - window_ms
        
        redis.call('ZREMRANGEBYSCORE', key, '-inf', cutoff)
        
        redis.call('ZADD', key, timestamp, member)
        
        redis.call('EXPIRE', key, math.ceil(window_ms / 1000))
        
        local count = redis.call('ZCARD', key)
        
        local removed = redis.call('ZCOUNT', key, '-inf', cutoff)
        
        return {count, removed}
        """
        
        with self.get_client() as r:
            result = r.eval(lua_script, 1, key, timestamp, member, window_seconds * 1000, limit)
            count = int(result[0])
            removed = int(result[1])
            return count, count <= limit, removed

    def get_sliding_window_count(
        self,
        user_id: str,
        ad_id: str,
        window: str,
        window_seconds: int,
    ) -> int:
        key = self._get_sliding_window_key(user_id, ad_id, window)
        timestamp = int(time.time() * 1000)
        cutoff = timestamp - window_seconds * 1000
        
        lua_script = """
        local key = KEYS[1]
        local cutoff = tonumber(ARGV[1])
        
        redis.call('ZREMRANGEBYSCORE', key, '-inf', cutoff)
        
        local count = redis.call('ZCARD', key)
        
        return count
        """
        
        with self.get_client() as r:
            count = r.eval(lua_script, 1, key, cutoff)
            return int(count)

    def get_sliding_window_timestamps(
        self,
        user_id: str,
        ad_id: str,
        window: str,
        window_seconds: int,
    ) -> List[int]:
        key = self._get_sliding_window_key(user_id, ad_id, window)
        timestamp = int(time.time() * 1000)
        cutoff = timestamp - window_seconds * 1000
        
        with self.get_client() as r:
            r.zremrangebyscore(key, '-inf', cutoff)
            members = r.zrangebyscore(key, cutoff, '+inf')
            timestamps = []
            for m in members:
                if isinstance(m, bytes):
                    m = m.decode()
                ts = int(m.split(':')[0])
                timestamps.append(ts)
            return timestamps

    def check_sliding_window_limits(
        self,
        user_id: str,
        ad_id: str,
    ) -> Tuple[bool, List[str], Dict[str, int]]:
        violated = []
        counts = {}
        
        lua_script = """
        local user_id = ARGV[1]
        local ad_id = ARGV[2]
        local timestamp = tonumber(ARGV[3])
        local windows = cjson.decode(ARGV[4])
        
        local violated = {}
        local counts = {}
        
        for i, win in ipairs(windows) do
            local window_name = win[1]
            local limit = tonumber(win[2])
            local window_seconds = tonumber(win[3])
            local cutoff = timestamp - window_seconds * 1000
            local key = 'freq:sw:' .. user_id .. ':' .. ad_id .. ':' .. window_name
            
            redis.call('ZREMRANGEBYSCORE', key, '-inf', cutoff)
            
            local count = tonumber(redis.call('ZCARD', key))
            counts[window_name] = count
            
            if count >= limit then
                table.insert(violated, window_name)
            end
        end
        
        return {cjson.encode(violated), cjson.encode(counts)}
        """
        
        windows_array = []
        for window_name, (limit, window_seconds) in config.frequency.limits.items():
            windows_array.append([window_name, limit, window_seconds])
        
        import json
        windows_json = json.dumps(windows_array)
        timestamp = int(time.time() * 1000)
        
        with self.get_client() as r:
            try:
                result = r.eval(
                    lua_script, 0,
                    user_id, ad_id, timestamp, windows_json
                )
                violated = json.loads(result[0])
                counts = json.loads(result[1])
                counts = {k: int(v) for k, v in counts.items()}
            except Exception as e:
                for window_name, (limit, window_seconds) in config.frequency.limits.items():
                    count = self.get_sliding_window_count(user_id, ad_id, window_name, window_seconds)
                    counts[window_name] = count
                    if count >= limit:
                        violated.append(window_name)
        
        return len(violated) == 0, violated, counts

    def record_impression_sliding_window(
        self,
        user_id: str,
        ad_id: str,
    ) -> Tuple[Dict[str, int], Dict[str, bool]]:
        counts = {}
        within_limits = {}
        
        lua_script = """
        local user_id = ARGV[1]
        local ad_id = ARGV[2]
        local timestamp = tonumber(ARGV[3])
        local member_suffix = ARGV[4]
        local windows = cjson.decode(ARGV[5])
        
        local counts = {}
        local within_limits = {}
        
        for i, win in ipairs(windows) do
            local window_name = win[1]
            local limit = tonumber(win[2])
            local window_seconds = tonumber(win[3])
            local cutoff = timestamp - window_seconds * 1000
            local key = 'freq:sw:' .. user_id .. ':' .. ad_id .. ':' .. window_name
            local member = timestamp .. ':' .. member_suffix .. ':' .. i
            
            redis.call('ZREMRANGEBYSCORE', key, '-inf', cutoff)
            
            redis.call('ZADD', key, timestamp, member)
            
            redis.call('EXPIRE', key, math.ceil(window_seconds))
            
            local count = tonumber(redis.call('ZCARD', key))
            counts[window_name] = count
            within_limits[window_name] = (count <= limit)
        end
        
        return {cjson.encode(counts), cjson.encode(within_limits)}
        """
        
        windows_array = []
        for window_name, (limit, window_seconds) in config.frequency.limits.items():
            windows_array.append([window_name, limit, window_seconds])
        
        import json
        windows_json = json.dumps(windows_array)
        timestamp = int(time.time() * 1000)
        member_suffix = str(time.time_ns())
        
        with self.get_client() as r:
            try:
                result = r.eval(
                    lua_script, 0,
                    user_id, ad_id, timestamp, member_suffix, windows_json
                )
                counts = json.loads(result[0])
                within_limits = json.loads(result[1])
                counts = {k: int(v) for k, v in counts.items()}
                within_limits = {k: bool(v) for k, v in within_limits.items()}
            except Exception as e:
                for window_name, (limit, window_seconds) in config.frequency.limits.items():
                    count, within, _ = self.add_impression_sliding_window(
                        user_id, ad_id, window_name, window_seconds, limit
                    )
                    counts[window_name] = count
                    within_limits[window_name] = within
        
        return counts, within_limits

    def increment_frequency(self, user_id: str, ad_id: str, window: str, limit: int, ttl: int) -> Tuple[int, bool]:
        count, within, _ = self.add_impression_sliding_window(user_id, ad_id, window, ttl, limit)
        return count, within

    def get_frequency(self, user_id: str, ad_id: str, window: str) -> int:
        window_seconds = config.frequency.limits.get(window, (0, 3600))[1]
        return self.get_sliding_window_count(user_id, ad_id, window, window_seconds)

    def check_all_frequency_limits(self, user_id: str, ad_id: str) -> Tuple[bool, List[str]]:
        allowed, violated, _ = self.check_sliding_window_limits(user_id, ad_id)
        return allowed, violated

    def record_impression(self, user_id: str, ad_id: str) -> None:
        self.record_impression_sliding_window(user_id, ad_id)

    def set_budget(self, campaign_id: str, budget: float, init_spent: bool = True) -> bool:
        key = f"budget:{campaign_id}"
        with self.get_client() as r:
            pipe = r.pipeline()
            pipe.hset(key, "total", budget)
            if init_spent:
                pipe.hsetnx(key, "spent", 0)
            results = pipe.execute()
            return results[0] > 0

    def get_budget(self, campaign_id: str) -> Optional[Dict[str, float]]:
        key = f"budget:{campaign_id}"
        with self.get_client() as r:
            data = r.hgetall(key)
            if not data:
                return None
            return {k.decode(): float(v) for k, v in data.items()}

    def consume_budget(self, campaign_id: str, amount: float) -> bool:
        key = f"budget:{campaign_id}"
        with self.get_client() as r:
            pipe = r.pipeline()
            pipe.hincrbyfloat(key, "spent", amount)
            pipe.hget(key, "total")
            results = pipe.execute()
            spent, total = results[0], float(results[1] or 0)
            return spent <= total

    def get_remaining_budget(self, campaign_id: str) -> float:
        key = f"budget:{campaign_id}"
        with self.get_client() as r:
            pipe = r.pipeline()
            pipe.hget(key, "total")
            pipe.hget(key, "spent")
            results = pipe.execute()
            total = float(results[0] or 0)
            spent = float(results[1] or 0)
            return max(0, total - spent)

    def set_hourly_budget(self, campaign_id: str, hour: str, budget: float) -> bool:
        key = f"budget:hourly:{campaign_id}:{hour}"
        with self.get_client() as r:
            return r.setex(key, 86400, budget)

    def consume_hourly_budget(self, campaign_id: str, hour: str, amount: float) -> bool:
        key = f"budget:hourly:{campaign_id}:{hour}"
        with self.get_client() as r:
            current = float(r.get(key) or 0)
            if current >= amount:
                r.decrbyfloat(key, amount)
                return True
            return False

    def get_hourly_remaining(self, campaign_id: str, hour: str) -> float:
        key = f"budget:hourly:{campaign_id}:{hour}"
        with self.get_client() as r:
            return float(r.get(key) or 0)

    def set_traffic_layer_counter(self, layer_name: str, campaign_id: str, value: float) -> bool:
        key = f"traffic:layer:{layer_name}:{campaign_id}"
        with self.get_client() as r:
            return r.hincrbyfloat(key, "value", value) > 0

    def get_traffic_layer_stats(self, layer_name: str, campaign_id: str) -> Dict[str, float]:
        key = f"traffic:layer:{layer_name}:{campaign_id}"
        with self.get_client() as r:
            data = r.hgetall(key)
            return {k.decode(): float(v) for k, v in data.items()} if data else {}

    def cache_prediction(self, feature_hash: str, prediction: float, ttl: int = 3600) -> bool:
        key = f"pred:cache:{feature_hash}"
        with self.get_client() as r:
            return r.setex(key, ttl, prediction)

    def get_cached_prediction(self, feature_hash: str) -> Optional[float]:
        key = f"pred:cache:{feature_hash}"
        with self.get_client() as r:
            data = r.get(key)
            return float(data) if data else None

    def update_pace(self, campaign_id: str, pace: float) -> bool:
        key = f"pace:{campaign_id}"
        with self.get_client() as r:
            return r.setex(key, 3600, pace)

    def get_pace(self, campaign_id: str) -> float:
        key = f"pace:{campaign_id}"
        with self.get_client() as r:
            return float(r.get(key) or 1.0)

    def record_bid(self, bid_id: str, bid_data: Dict[str, Any], ttl: int = 86400) -> bool:
        key = f"bid:history:{bid_id}"
        with self.get_client() as r:
            return r.setex(key, ttl, json.dumps(bid_data))

    def get_bid_history(self, bid_id: str) -> Optional[Dict[str, Any]]:
        key = f"bid:history:{bid_id}"
        with self.get_client() as r:
            data = r.get(key)
            return json.loads(data) if data else None

    def get_all_keys(self, pattern: str) -> List[str]:
        with self.get_client() as r:
            return [k.decode() for k in r.keys(pattern)]

    def delete_key(self, key: str) -> bool:
        with self.get_client() as r:
            return r.delete(key) > 0

    def clear_all(self) -> None:
        with self.get_client() as r:
            r.flushdb()
