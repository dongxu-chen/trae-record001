import redis
import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from config import Config


class RedisStore:
    def __init__(self):
        self.client = redis.Redis(
            host=Config.REDIS_HOST,
            port=Config.REDIS_PORT,
            db=Config.REDIS_DB,
            decode_responses=True
        )
    
    def save_email(self, email_id: str, email_data: Dict[str, Any]) -> None:
        key = f"email:{email_id}"
        email_data['created_at'] = time.time()
        self.client.setex(key, 86400 * 30, json.dumps(email_data))
    
    def get_email(self, email_id: str) -> Optional[Dict[str, Any]]:
        key = f"email:{email_id}"
        data = self.client.get(key)
        return json.loads(data) if data else None
    
    def save_classification_result(self, email_id: str, result: Dict[str, Any]) -> None:
        key = f"classification:{email_id}"
        result['classified_at'] = time.time()
        self.client.setex(key, 86400 * 30, json.dumps(result))
    
    def get_classification_result(self, email_id: str) -> Optional[Dict[str, Any]]:
        key = f"classification:{email_id}"
        data = self.client.get(key)
        return json.loads(data) if data else None
    
    def get_sender_reputation(self, sender: str) -> float:
        key = f"reputation:{sender}"
        data = self.client.hgetall(key)
        
        if not data:
            return Config.INITIAL_REPUTATION
        
        score = float(data.get('score', Config.INITIAL_REPUTATION))
        last_updated = float(data.get('last_updated', time.time()))
        
        days_passed = (time.time() - last_updated) / (86400)
        decay_factor = 1 - (days_passed / Config.REPUTATION_DECAY_DAYS)
        decay_factor = max(0.5, min(1.0, decay_factor))
        
        decayed_score = score * decay_factor
        return max(Config.MIN_REPUTATION, min(Config.MAX_REPUTATION, decayed_score))
    
    def update_sender_reputation(self, sender: str, delta: float) -> float:
        key = f"reputation:{sender}"
        current_score = self.get_sender_reputation(sender)
        new_score = max(Config.MIN_REPUTATION, min(Config.MAX_REPUTATION, current_score + delta))
        
        self.client.hset(key, mapping={
            'score': str(new_score),
            'last_updated': str(time.time())
        })
        return new_score
    
    def increment_ip_count(self, ip: str) -> int:
        key = f"rate_limit:ip:{ip}"
        pipe = self.client.pipeline()
        pipe.incr(key)
        pipe.expire(key, Config.RATE_LIMIT_WINDOW)
        result, _ = pipe.execute()
        return result
    
    def get_ip_count(self, ip: str) -> int:
        key = f"rate_limit:ip:{ip}"
        return int(self.client.get(key) or 0)
    
    def save_rule(self, rule_id: str, rule: Dict[str, Any]) -> None:
        key = f"rule:{rule_id}"
        self.client.set(key, json.dumps(rule))
    
    def get_rule(self, rule_id: str) -> Optional[Dict[str, Any]]:
        key = f"rule:{rule_id}"
        data = self.client.get(key)
        return json.loads(data) if data else None
    
    def delete_rule(self, rule_id: str) -> bool:
        key = f"rule:{rule_id}"
        return bool(self.client.delete(key))
    
    def get_all_rules(self) -> List[Dict[str, Any]]:
        rules = []
        for key in self.client.scan_iter("rule:*"):
            data = self.client.get(key)
            if data:
                rule = json.loads(data)
                rule['id'] = key.replace("rule:", "")
                rules.append(rule)
        return rules
    
    def add_to_blacklist(self, list_type: str, value: str) -> None:
        key = f"blacklist:{list_type}"
        self.client.sadd(key, value)
    
    def remove_from_blacklist(self, list_type: str, value: str) -> bool:
        key = f"blacklist:{list_type}"
        return bool(self.client.srem(key, value))
    
    def is_blacklisted(self, list_type: str, value: str) -> bool:
        key = f"blacklist:{list_type}"
        return self.client.sismember(key, value)
    
    def get_blacklist(self, list_type: str) -> List[str]:
        key = f"blacklist:{list_type}"
        return list(self.client.smembers(key))
    
    def save_feedback(self, email_id: str, feedback: Dict[str, Any]) -> None:
        key = f"feedback:{email_id}"
        feedback['created_at'] = time.time()
        self.client.set(key, json.dumps(feedback))
    
    def get_feedback(self, email_id: str) -> Optional[Dict[str, Any]]:
        key = f"feedback:{email_id}"
        data = self.client.get(key)
        return json.loads(data) if data else None
    
    def get_recent_classifications(self, limit: int = 100) -> List[Dict[str, Any]]:
        classifications = []
        keys = []
        for key in self.client.scan_iter("classification:*"):
            keys.append(key)
        
        keys_with_time = []
        for key in keys:
            data = self.client.get(key)
            if data:
                result = json.loads(data)
                keys_with_time.append((result.get('classified_at', 0), key, result))
        
        keys_with_time.sort(reverse=True, key=lambda x: x[0])
        
        for _, key, result in keys_with_time[:limit]:
            email_id = key.replace("classification:", "")
            email = self.get_email(email_id)
            classifications.append({
                'email_id': email_id,
                'result': result,
                'email': email
            })
        
        return classifications
    
    def get_statistics(self) -> Dict[str, Any]:
        total_emails = 0
        spam_count = 0
        ham_count = 0
        total_score = 0.0
        
        for key in self.client.scan_iter("classification:*"):
            data = self.client.get(key)
            if data:
                result = json.loads(data)
                total_emails += 1
                total_score += result.get('spam_probability', 0)
                if result.get('is_spam', False):
                    spam_count += 1
                else:
                    ham_count += 1
        
        return {
            'total_emails': total_emails,
            'spam_count': spam_count,
            'ham_count': ham_count,
            'spam_rate': spam_count / total_emails if total_emails > 0 else 0,
            'avg_spam_score': total_score / total_emails if total_emails > 0 else 0
        }
