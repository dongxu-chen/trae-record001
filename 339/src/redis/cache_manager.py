import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Set
from collections import defaultdict
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    print("Warning: redis-py not available. Using in-memory fallback.")

from common.logger import get_logger
from common.utils import (
    load_config,
    parse_json_safe,
    to_json_safe,
    get_risk_level
)

logger = get_logger("RedisCacheManager")


class InMemoryCache:
    def __init__(self):
        self._data: Dict[str, Any] = {}
        self._ttl: Dict[str, float] = {}
        self._sorted_sets: Dict[str, List] = defaultdict(list)
    
    def set(self, key: str, value: Any, ex: Optional[int] = None) -> bool:
        self._data[key] = value
        if ex:
            self._ttl[key] = time.time() + ex
        return True
    
    def get(self, key: str) -> Optional[Any]:
        if key in self._ttl and time.time() > self._ttl[key]:
            del self._data[key]
            del self._ttl[key]
            return None
        return self._data.get(key)
    
    def delete(self, key: str) -> int:
        deleted = 0
        if key in self._data:
            del self._data[key]
            deleted += 1
        if key in self._ttl:
            del self._ttl[key]
        if key in self._sorted_sets:
            del self._sorted_sets[key]
        return deleted
    
    def exists(self, key: str) -> int:
        return 1 if key in self._data else 0
    
    def hset(self, name: str, key: str, value: Any) -> int:
        if name not in self._data:
            self._data[name] = {}
        self._data[name][key] = value
        return 1
    
    def hget(self, name: str, key: str) -> Optional[Any]:
        data = self._data.get(name, {})
        return data.get(key) if isinstance(data, dict) else None
    
    def hgetall(self, name: str) -> Dict:
        data = self._data.get(name, {})
        return data if isinstance(data, dict) else {}
    
    def sadd(self, name: str, *values) -> int:
        if name not in self._data:
            self._data[name] = set()
        s = self._data[name]
        if not isinstance(s, set):
            s = set()
            self._data[name] = s
        added = 0
        for v in values:
            if v not in s:
                s.add(v)
                added += 1
        return added
    
    def smembers(self, name: str) -> Set:
        s = self._data.get(name, set())
        return s if isinstance(s, set) else set()
    
    def srem(self, name: str, *values) -> int:
        s = self._data.get(name, set())
        if not isinstance(s, set):
            return 0
        removed = 0
        for v in values:
            if v in s:
                s.remove(v)
                removed += 1
        return removed
    
    def zadd(self, name: str, mapping: Dict[str, float]) -> int:
        if name not in self._sorted_sets:
            self._sorted_sets[name] = []
        zset = self._sorted_sets[name]
        
        existing = {k: i for i, (k, _) in enumerate(zset)}
        added = 0
        
        for k, score in mapping.items():
            if k in existing:
                zset[existing[k]] = (k, float(score))
            else:
                zset.append((k, float(score)))
                added += 1
        
        zset.sort(key=lambda x: x[1])
        return added
    
    def zrange(self, name: str, start: int, end: int, 
               desc: bool = False, withscores: bool = False):
        zset = self._sorted_sets.get(name, [])
        
        if desc:
            zset = list(reversed(zset))
        
        if end == -1:
            end = len(zset) - 1
        
        result = zset[start:end+1]
        
        if withscores:
            return result
        else:
            return [k for k, _ in result]
    
    def zrem(self, name: str, *values) -> int:
        zset = self._sorted_sets.get(name, [])
        removed = 0
        values_set = set(values)
        new_zset = [(k, s) for k, s in zset if k not in values_set]
        removed = len(zset) - len(new_zset)
        self._sorted_sets[name] = new_zset
        return removed
    
    def zscore(self, name: str, value: str) -> Optional[float]:
        zset = self._sorted_sets.get(name, [])
        for k, s in zset:
            if k == value:
                return s
        return None
    
    def keys(self, pattern: str = "*") -> List[str]:
        import fnmatch
        return [k for k in self._data.keys() if fnmatch.fnmatch(k, pattern)]
    
    def scan_iter(self, match: str = "*"):
        for key in self.keys(match):
            yield key


class RedisCacheManager:
    def __init__(self, use_redis: bool = True):
        self.config = load_config()
        self.redis_config = self.config["redis"]
        
        self.use_redis = use_redis and REDIS_AVAILABLE
        self.client = None
        self._in_memory = InMemoryCache()
        
        self.ttl_profile = self.redis_config["ttl"]["user_profile"]
        self.ttl_risk = self.redis_config["ttl"]["risk_score"]
        self.ttl_features = self.redis_config["ttl"]["feature_cache"]
        
        self._init_client()
        
        self._high_risk_key = "high_risk_users"
        self._user_prefix = "user:"
        self._risk_prefix = "risk:"
        self._profile_prefix = "profile:"
        self._features_prefix = "features:"
        self._action_prefix = "action:"
        self._notification_prefix = "notification:"
    
    def _init_client(self):
        if self.use_redis:
            try:
                self.client = redis.Redis(
                    host=self.redis_config["host"],
                    port=self.redis_config["port"],
                    db=self.redis_config["db"],
                    password=self.redis_config["password"],
                    max_connections=self.redis_config["max_connections"],
                    decode_responses=True,
                    socket_timeout=5,
                    socket_connect_timeout=5
                )
                
                self.client.ping()
                logger.info("Connected to Redis successfully")
            except Exception as e:
                logger.warning(f"Failed to connect to Redis: {e}. Using in-memory fallback.")
                self.use_redis = False
                self.client = None
        else:
            logger.info("Using in-memory cache")
    
    def _execute(self, method: str, *args, **kwargs):
        if self.use_redis and self.client:
            try:
                return getattr(self.client, method)(*args, **kwargs)
            except Exception as e:
                logger.error(f"Redis error on {method}: {e}")
        
        return getattr(self._in_memory, method)(*args, **kwargs)
    
    def store_user_profile(self, user_id: str, profile: Dict) -> bool:
        key = f"{self._profile_prefix}{user_id}"
        value = to_json_safe(profile)
        
        self._execute("set", key, value, ex=self.ttl_profile)
        
        for k, v in profile.items():
            self._execute("hset", f"{self._user_prefix}{user_id}", k, 
                         to_json_safe(v) if isinstance(v, (dict, list)) else v)
        
        logger.debug(f"Stored profile for user: {user_id}")
        return True
    
    def get_user_profile(self, user_id: str) -> Optional[Dict]:
        key = f"{self._profile_prefix}{user_id}"
        value = self._execute("get", key)
        
        if value:
            return parse_json_safe(value)
        
        hash_data = self._execute("hgetall", f"{self._user_prefix}{user_id}")
        if hash_data:
            profile = {}
            for k, v in hash_data.items():
                parsed = parse_json_safe(v)
                profile[k] = parsed if parsed is not None else v
            return profile
        
        return None
    
    def store_user_features(self, user_id: str, features: Dict) -> bool:
        key = f"{self._features_prefix}{user_id}"
        value = to_json_safe(features)
        
        self._execute("set", key, value, ex=self.ttl_features)
        
        feature_key = f"{self._user_prefix}{user_id}:features"
        for k, v in features.items():
            if isinstance(v, (int, float)):
                self._execute("hset", feature_key, k, str(v))
        
        logger.debug(f"Stored features for user: {user_id}")
        return True
    
    def get_user_features(self, user_id: str) -> Optional[Dict]:
        key = f"{self._features_prefix}{user_id}"
        value = self._execute("get", key)
        
        if value:
            return parse_json_safe(value)
        
        feature_key = f"{self._user_prefix}{user_id}:features"
        hash_data = self._execute("hgetall", feature_key)
        if hash_data:
            features = {}
            for k, v in hash_data.items():
                try:
                    features[k] = float(v) if "." in v else int(v)
                except (ValueError, TypeError):
                    features[k] = v
            return features
        
        return None
    
    def store_risk_score(self, user_id: str, prediction: Dict) -> bool:
        key = f"{self._risk_prefix}{user_id}"
        value = to_json_safe(prediction)
        
        self._execute("set", key, value, ex=self.ttl_risk)
        
        risk_key = f"{self._user_prefix}{user_id}:risk"
        self._execute("hset", risk_key, "probability", 
                     str(prediction.get("churn_probability", 0)))
        self._execute("hset", risk_key, "level", prediction.get("risk_level", "low"))
        self._execute("hset", risk_key, "score", str(prediction.get("risk_score", 0)))
        self._execute("hset", risk_key, "expected_days", 
                     str(prediction.get("expected_days_to_churn", 0)))
        self._execute("hset", risk_key, "timestamp", prediction.get("prediction_timestamp", ""))
        
        risk_score = prediction.get("risk_score", 0)
        self._execute("zadd", "user_risk_scores", {user_id: float(risk_score)})
        
        logger.debug(f"Stored risk score for user: {user_id}, "
                    f"level: {prediction.get('risk_level')}, "
                    f"prob: {prediction.get('churn_probability', 0):.4f}")
        return True
    
    def get_risk_score(self, user_id: str) -> Optional[Dict]:
        key = f"{self._risk_prefix}{user_id}"
        value = self._execute("get", key)
        
        if value:
            return parse_json_safe(value)
        
        risk_key = f"{self._user_prefix}{user_id}:risk"
        hash_data = self._execute("hgetall", risk_key)
        if hash_data:
            return {
                "churn_probability": float(hash_data.get("probability", 0)),
                "risk_level": hash_data.get("level", "low"),
                "risk_score": float(hash_data.get("score", 0)),
                "expected_days_to_churn": float(hash_data.get("expected_days", 0)),
                "prediction_timestamp": hash_data.get("timestamp", "")
            }
        
        return None
    
    def tag_high_risk_user(self, user_id: str, prediction: Dict) -> bool:
        self._execute("sadd", self._high_risk_key, user_id)
        
        tag_data = {
            "user_id": user_id,
            "tagged_at": datetime.now().isoformat(),
            "churn_probability": prediction.get("churn_probability", 0),
            "risk_score": prediction.get("risk_score", 0),
            "expected_days_to_churn": prediction.get("expected_days_to_churn", 0),
            "status": "active"
        }
        
        self._execute("hset", f"{self._high_risk_key}:{user_id}", "data", 
                     to_json_safe(tag_data))
        
        logger.info(f"Tagged high risk user: {user_id}, "
                   f"probability: {prediction.get('churn_probability', 0):.4f}")
        return True
    
    def untag_high_risk_user(self, user_id: str) -> bool:
        self._execute("srem", self._high_risk_key, user_id)
        self._execute("delete", f"{self._high_risk_key}:{user_id}")
        logger.info(f"Untagged high risk user: {user_id}")
        return True
    
    def get_high_risk_users(self, limit: Optional[int] = None) -> List[Dict]:
        members = self._execute("smembers", self._high_risk_key)
        users = []
        
        for user_id in list(members)[:limit] if limit else list(members):
            tag_data = self._execute("hget", f"{self._high_risk_key}:{user_id}", "data")
            if tag_data:
                parsed = parse_json_safe(tag_data)
                if parsed:
                    users.append(parsed)
        
        users.sort(key=lambda x: x.get("churn_probability", 0), reverse=True)
        return users
    
    def get_top_risk_users(self, n: int = 100, min_prob: float = 0.0) -> List[Dict]:
        top_users = self._execute("zrange", "user_risk_scores", 0, n - 1, 
                                 desc=True, withscores=True)
        
        result = []
        for user_id, score in top_users:
            risk_data = self.get_risk_score(user_id)
            if risk_data and risk_data.get("churn_probability", 0) >= min_prob:
                risk_data["user_id"] = user_id
                result.append(risk_data)
        
        return result
    
    def record_action_taken(self, user_id: str, action: str, 
                           channel: str, metadata: Optional[Dict] = None) -> str:
        action_id = f"act_{int(time.time()*1000)}_{user_id[:8]}"
        
        action_data = {
            "action_id": action_id,
            "user_id": user_id,
            "action": action,
            "channel": channel,
            "timestamp": datetime.now().isoformat(),
            "metadata": metadata or {},
            "status": "pending"
        }
        
        key = f"{self._action_prefix}{action_id}"
        self._execute("set", key, to_json_safe(action_data), ex=86400 * 30)
        
        self._execute("hset", f"{self._user_prefix}{user_id}:actions", 
                     action_id, to_json_safe(action_data))
        
        self._execute("set", f"{self._user_prefix}{user_id}:last_action", 
                     to_json_safe(action_data), 
                     ex=self.config["strategy"]["action_cooldown_hours"] * 3600)
        
        logger.info(f"Recorded action: {action} for user {user_id} via {channel}")
        return action_id
    
    def update_action_status(self, action_id: str, status: str, 
                            result: Optional[Dict] = None) -> bool:
        key = f"{self._action_prefix}{action_id}"
        action_data_str = self._execute("get", key)
        
        if not action_data_str:
            return False
        
        action_data = parse_json_safe(action_data_str)
        action_data["status"] = status
        action_data["updated_at"] = datetime.now().isoformat()
        if result:
            action_data["result"] = result
        
        self._execute("set", key, to_json_safe(action_data), ex=86400 * 30)
        
        user_id = action_data.get("user_id", "")
        if user_id:
            self._execute("hset", f"{self._user_prefix}{user_id}:actions", 
                         action_id, to_json_safe(action_data))
        
        logger.info(f"Updated action {action_id} status to: {status}")
        return True
    
    def get_user_actions(self, user_id: str, limit: int = 10) -> List[Dict]:
        action_ids = self._execute("hgetall", f"{self._user_prefix}{user_id}:actions")
        
        actions = []
        for action_id, action_str in list(action_ids.items())[-limit:]:
            action = parse_json_safe(action_str)
            if action:
                actions.append(action)
        
        actions.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
        return actions
    
    def check_action_cooldown(self, user_id: str) -> bool:
        last_action = self._execute("get", f"{self._user_prefix}{user_id}:last_action")
        return last_action is not None
    
    def store_notification(self, user_id: str, notification: Dict) -> str:
        notif_id = f"notif_{int(time.time()*1000)}_{user_id[:8]}"
        
        notif_data = {
            "notification_id": notif_id,
            "user_id": user_id,
            **notification,
            "created_at": datetime.now().isoformat(),
            "status": "queued"
        }
        
        self._execute("zadd", f"{self._notification_prefix}queue", 
                     {notif_id: time.time()})
        
        key = f"{self._notification_prefix}{notif_id}"
        self._execute("set", key, to_json_safe(notif_data), ex=86400 * 7)
        
        return notif_id
    
    def get_pending_notifications(self, limit: int = 100) -> List[Dict]:
        notif_ids = self._execute("zrange", f"{self._notification_prefix}queue", 
                                 0, limit - 1)
        
        notifications = []
        for notif_id in notif_ids:
            key = f"{self._notification_prefix}{notif_id}"
            notif_str = self._execute("get", key)
            if notif_str:
                notif = parse_json_safe(notif_str)
                if notif and notif.get("status") == "queued":
                    notifications.append(notif)
        
        return notifications
    
    def mark_notification_sent(self, notif_id: str, sent_at: Optional[str] = None) -> bool:
        key = f"{self._notification_prefix}{notif_id}"
        notif_str = self._execute("get", key)
        
        if not notif_str:
            return False
        
        notif = parse_json_safe(notif_str)
        notif["status"] = "sent"
        notif["sent_at"] = sent_at or datetime.now().isoformat()
        
        self._execute("set", key, to_json_safe(notif), ex=86400 * 7)
        self._execute("zrem", f"{self._notification_prefix}queue", notif_id)
        
        return True
    
    def get_user_risk_history(self, user_id: str, limit: int = 30) -> List[Dict]:
        pattern = f"{self._risk_prefix}{user_id}:*"
        keys = self._execute("keys", pattern) if hasattr(self._execute("keys", ""), '__iter__') else []
        
        history = []
        for key in sorted(keys, reverse=True)[:limit]:
            value = self._execute("get", key)
            if value:
                parsed = parse_json_safe(value)
                if parsed:
                    history.append(parsed)
        
        return history
    
    def get_user_full_data(self, user_id: str) -> Dict:
        return {
            "user_id": user_id,
            "profile": self.get_user_profile(user_id),
            "features": self.get_user_features(user_id),
            "risk": self.get_risk_score(user_id),
            "actions": self.get_user_actions(user_id, limit=5),
            "is_high_risk": self._execute("sismember", self._high_risk_key, user_id) 
                          if hasattr(self._in_memory, 'sismember') or self.client 
                          else user_id in self._execute("smembers", self._high_risk_key)
        }
    
    def get_statistics(self) -> Dict:
        high_risk_count = len(self._execute("smembers", self._high_risk_key))
        
        all_users = self._execute("keys", f"{self._profile_prefix}*")
        total_users = len(all_users) if isinstance(all_users, list) else 0
        
        users_with_risk = self._execute("keys", f"{self._risk_prefix}*")
        total_scored = len(users_with_risk) if isinstance(users_with_risk, list) else 0
        
        risk_distribution = {"high": 0, "medium": 0, "low": 0}
        if self.client and total_scored > 0:
            for key in list(self._execute("scan_iter", f"{self._risk_prefix}*"))[:1000]:
                value = self._execute("get", key)
                if value:
                    parsed = parse_json_safe(value)
                    if parsed:
                        level = parsed.get("risk_level", "low")
                        risk_distribution[level] = risk_distribution.get(level, 0) + 1
        
        return {
            "total_users": total_users,
            "users_with_risk_scores": total_scored,
            "high_risk_users": high_risk_count,
            "risk_distribution": risk_distribution,
            "cache_type": "redis" if self.use_redis else "in_memory"
        }
    
    def clear_all(self):
        if self.use_redis and self.client:
            self.client.flushdb()
        else:
            self._in_memory = InMemoryCache()
        logger.info("Cleared all cache data")


def main():
    manager = RedisCacheManager(use_redis=False)
    
    print("=" * 60)
    print("Redis Cache Manager")
    print("=" * 60)
    
    print("\n1. Store test user data")
    print("2. Get user data")
    print("3. Tag high risk users")
    print("4. Get high risk users list")
    print("5. Show statistics")
    
    choice = input("\nEnter your choice (1-5): ").strip()
    
    if choice == "1":
        user_id = input("Enter user ID: ").strip() or "test_user_001"
        
        profile = {
            "user_id": user_id,
            "user_level": "gold",
            "region": "north",
            "channel": "organic",
            "total_spend": 5000,
            "signup_date": datetime.now().timestamp() - 86400 * 180
        }
        manager.store_user_profile(user_id, profile)
        
        features = {
            "window_7d_total_events": 15,
            "window_30d_total_events": 50,
            "days_since_last_event": 3,
            "event_frequency": 0.5,
            "conversion_rate": 0.15
        }
        manager.store_user_features(user_id, features)
        
        prediction = {
            "churn_probability": 0.75,
            "hazard_ratio": 2.5,
            "expected_days_to_churn": 7,
            "risk_level": "high",
            "risk_score": 750,
            "survival_quantiles": {"quantile_50": 7, "quantile_75": 14},
            "prediction_timestamp": datetime.now().isoformat()
        }
        manager.store_risk_score(user_id, prediction)
        
        if prediction["risk_level"] == "high":
            manager.tag_high_risk_user(user_id, prediction)
        
        print(f"Stored data for user: {user_id}")
        print(f"  Profile: {profile}")
        print(f"  Risk Level: {prediction['risk_level']}")
        print(f"  Churn Probability: {prediction['churn_probability']:.2%}")
    
    elif choice == "2":
        user_id = input("Enter user ID: ").strip() or "test_user_001"
        
        data = manager.get_user_full_data(user_id)
        
        print(f"\nFull data for user: {user_id}")
        print("-" * 60)
        print(f"Profile: {json.dumps(data['profile'], indent=2, ensure_ascii=False)}")
        print(f"Features: {json.dumps(data['features'], indent=2, ensure_ascii=False)}")
        print(f"Risk: {json.dumps(data['risk'], indent=2, ensure_ascii=False)}")
        print(f"Is High Risk: {data['is_high_risk']}")
        print(f"Recent Actions: {len(data['actions'])} actions")
    
    elif choice == "3":
        num_users = int(input("Number of high risk users to tag: "))
        
        for i in range(num_users):
            user_id = f"high_risk_user_{i:03d}"
            prediction = {
                "churn_probability": round(random.uniform(0.7, 0.99), 4),
                "expected_days_to_churn": random.randint(1, 14),
                "risk_level": "high",
                "risk_score": random.randint(700, 999),
                "prediction_timestamp": datetime.now().isoformat()
            }
            manager.tag_high_risk_user(user_id, prediction)
            manager.store_risk_score(user_id, prediction)
            print(f"  Tagged: {user_id} (prob={prediction['churn_probability']:.2%})")
    
    elif choice == "4":
        high_risk = manager.get_high_risk_users(limit=20)
        print(f"\nHigh Risk Users ({len(high_risk)} total):")
        print("-" * 60)
        for i, user in enumerate(high_risk[:20], 1):
            print(f"{i:2d}. {user['user_id']}: "
                  f"prob={user['churn_probability']:.2%}, "
                  f"days={user.get('expected_days_to_churn', 0):.0f}, "
                  f"tagged={user['tagged_at']}")
    
    elif choice == "5":
        stats = manager.get_statistics()
        print("\nCache Statistics:")
        print("-" * 60)
        print(f"  Cache Type: {stats['cache_type']}")
        print(f"  Total Users: {stats['total_users']}")
        print(f"  Users with Risk Scores: {stats['users_with_risk_scores']}")
        print(f"  High Risk Users: {stats['high_risk_users']}")
        print(f"  Risk Distribution: {stats['risk_distribution']}")


if __name__ == "__main__":
    import random
    main()
