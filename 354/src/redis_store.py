import json
import time
from typing import Dict, List, Optional, Any
from datetime import datetime
import redis
import yaml


class RedisStore:
    def __init__(self, config_path: str = 'config/config.yaml'):
        self.config = self._load_config(config_path)['redis']
        self.client = self._connect()

    def _load_config(self, config_path: str) -> Dict:
        with open(config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)

    def _connect(self) -> redis.Redis:
        return redis.Redis(
            host=self.config['host'],
            port=self.config['port'],
            db=self.config['db'],
            password=self.config.get('password'),
            socket_timeout=self.config.get('socket_timeout', 5000) / 1000,
            decode_responses=True
        )

    def is_connected(self) -> bool:
        try:
            self.client.ping()
            return True
        except redis.ConnectionError:
            return False

    def record_click(self, click_id: str, ip: str, device_id: str, timestamp: float, ttl: int = 86400):
        pipe = self.client.pipeline()
        
        pipe.zadd(f"ip:clicks:{ip}", {click_id: timestamp})
        pipe.zadd(f"device:clicks:{device_id}", {click_id: timestamp})
        pipe.set(f"click:{click_id}", json.dumps({
            'ip': ip,
            'device_id': device_id,
            'timestamp': timestamp
        }), ex=ttl)
        
        pipe.expire(f"ip:clicks:{ip}", ttl)
        pipe.expire(f"device:clicks:{device_id}", ttl)
        
        pipe.execute()

    def get_ip_click_count(self, ip: str, window_seconds: int = 60) -> int:
        current_time = time.time()
        min_score = current_time - window_seconds
        return self.client.zcount(f"ip:clicks:{ip}", min_score, current_time)

    def get_device_click_count(self, device_id: str, window_seconds: int = 60) -> int:
        current_time = time.time()
        min_score = current_time - window_seconds
        return self.client.zcount(f"device:clicks:{device_id}", min_score, current_time)

    def get_ip_click_timestamps(self, ip: str, window_seconds: int = 300) -> List[float]:
        current_time = time.time()
        min_score = current_time - window_seconds
        return [float(ts) for ts in self.client.zrangebyscore(f"ip:clicks:{ip}", min_score, current_time, withscores=True, score_cast_func=float)]

    def get_device_click_timestamps(self, device_id: str, window_seconds: int = 300) -> List[float]:
        current_time = time.time()
        min_score = current_time - window_seconds
        return [float(ts) for ts in self.client.zrangebyscore(f"device:clicks:{device_id}", min_score, current_time, withscores=True, score_cast_func=float)]

    def increment_session_clicks(self, session_id: str, ttl: int = 3600) -> int:
        key = f"session:clicks:{session_id}"
        count = self.client.incr(key)
        self.client.expire(key, ttl)
        return count

    def get_session_clicks(self, session_id: str) -> int:
        count = self.client.get(f"session:clicks:{session_id}")
        return int(count) if count else 0

    def set_session_start(self, session_id: str, timestamp: float, ttl: int = 3600):
        key = f"session:start:{session_id}"
        if not self.client.exists(key):
            self.client.set(key, timestamp, ex=ttl)

    def get_session_start(self, session_id: str) -> Optional[float]:
        start_time = self.client.get(f"session:start:{session_id}")
        return float(start_time) if start_time else None

    def add_publisher_for_ip(self, ip: str, publisher_id: str, ttl: int = 86400):
        key = f"ip:publishers:{ip}"
        self.client.sadd(key, publisher_id)
        self.client.expire(key, ttl)

    def get_unique_publishers_for_ip(self, ip: str) -> int:
        return self.client.scard(f"ip:publishers:{ip}")

    def add_ad_for_ip(self, ip: str, ad_id: str, ttl: int = 86400):
        key = f"ip:ads:{ip}"
        self.client.sadd(key, ad_id)
        self.client.expire(key, ttl)

    def get_unique_ads_for_ip(self, ip: str) -> int:
        return self.client.scard(f"ip:ads:{ip}")

    def increment_publisher_clicks(self, publisher_id: str, ip: str, ttl: int = 86400):
        pipe = self.client.pipeline()
        pipe.hincrby(f"publisher:clicks:{publisher_id}", 'total', 1)
        pipe.hincrby(f"publisher:clicks:{publisher_id}", ip, 1)
        pipe.expire(f"publisher:clicks:{publisher_id}", ttl)
        pipe.execute()

    def get_publisher_click_ratio(self, publisher_id: str, ip: str) -> float:
        data = self.client.hgetall(f"publisher:clicks:{publisher_id}")
        if not data:
            return 0.0
        total = int(data.get('total', 0))
        ip_clicks = int(data.get(ip, 0))
        return ip_clicks / total if total > 0 else 0.0

    def record_fraud_alert(self, click_id: str, fraud_score: float, reasons: List[str], details: Dict[str, Any]):
        alert_data = {
            'click_id': click_id,
            'fraud_score': fraud_score,
            'reasons': reasons,
            'details': details,
            'timestamp': time.time()
        }
        self.client.set(f"fraud:alert:{click_id}", json.dumps(alert_data), ex=86400 * 7)
        self.client.zadd("fraud:alerts", {click_id: time.time()})

    def get_recent_fraud_alerts(self, limit: int = 100) -> List[Dict]:
        alert_ids = self.client.zrevrange("fraud:alerts", 0, limit - 1)
        alerts = []
        for alert_id in alert_ids:
            alert_data = self.client.get(f"fraud:alert:{alert_id}")
            if alert_data:
                alerts.append(json.loads(alert_data))
        return alerts

    def block_ip(self, ip: str, duration_seconds: int = 3600, reason: str = ""):
        key = f"blocked:ip:{ip}"
        self.client.set(key, json.dumps({
            'reason': reason,
            'blocked_at': time.time(),
            'duration': duration_seconds
        }), ex=duration_seconds)

    def is_ip_blocked(self, ip: str) -> bool:
        return self.client.exists(f"blocked:ip:{ip}") > 0

    def block_device(self, device_id: str, duration_seconds: int = 3600, reason: str = ""):
        key = f"blocked:device:{device_id}"
        self.client.set(key, json.dumps({
            'reason': reason,
            'blocked_at': time.time(),
            'duration': duration_seconds
        }), ex=duration_seconds)

    def is_device_blocked(self, device_id: str) -> bool:
        return self.client.exists(f"blocked:device:{device_id}") > 0

    def get_stats(self) -> Dict[str, Any]:
        return {
            'total_ips_tracked': len(self.client.keys("ip:clicks:*")),
            'total_devices_tracked': len(self.client.keys("device:clicks:*")),
            'active_sessions': len(self.client.keys("session:clicks:*")),
            'blocked_ips': len(self.client.keys("blocked:ip:*")),
            'blocked_devices': len(self.client.keys("blocked:device:*")),
            'total_fraud_alerts': self.client.zcard("fraud:alerts")
        }

    def cleanup_old_data(self, older_than_days: int = 1):
        cutoff = time.time() - (older_than_days * 86400)
        
        for key in self.client.keys("ip:clicks:*"):
            self.client.zremrangebyscore(key, 0, cutoff)
        
        for key in self.client.keys("device:clicks:*"):
            self.client.zremrangebyscore(key, 0, cutoff)

    def clear_all(self):
        self.client.flushdb()

    def close(self):
        self.client.close()
