import json
import redis
from typing import Dict, List, Optional, Any
from datetime import datetime
import uuid
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import config

class RuleCategory:
    CONTENT_THRESHOLD = "content_threshold"
    SENSITIVE_WORDS = "sensitive_words"
    REVIEW_RULES = "review_rules"
    VIDEO_SETTINGS = "video_settings"

class ContentTypeThresholds:
    def __init__(self):
        self.porn_high = 0.85
        self.porn_low = 0.5
        self.swimwear_high = 0.95
        self.swimwear_low = 0.7
        self.violence_high = 0.8
        self.violence_low = 0.4
        self.ad_high = 0.75
        self.ad_low = 0.35
    
    def to_dict(self) -> Dict:
        return {
            "porn": {"high": self.porn_high, "low": self.porn_low},
            "swimwear": {"high": self.swimwear_high, "low": self.swimwear_low},
            "violence": {"high": self.violence_high, "low": self.violence_low},
            "advertisement": {"high": self.ad_high, "low": self.ad_low}
        }

class RulesConfigManager:
    def __init__(self):
        self.redis_client = redis.Redis(
            host=config.REDIS_HOST,
            port=config.REDIS_PORT,
            db=config.REDIS_DB,
            password=config.REDIS_PASSWORD,
            decode_responses=True
        )
        self._prefix = "audit:config:"
        self._init_default_config()
    
    def _init_default_config(self):
        if not self.redis_client.exists(f"{self._prefix}{RuleCategory.CONTENT_THRESHOLD}"):
            thresholds = ContentTypeThresholds()
            self.set_content_thresholds(thresholds.to_dict())
        
        if not self.redis_client.exists(f"{self._prefix}{RuleCategory.SENSITIVE_WORDS}"):
            self.set_sensitive_words([])
        
        if not self.redis_client.exists(f"{self._prefix}{RuleCategory.REVIEW_RULES}"):
            default_rules = {
                "auto_submit_high_risk": True,
                "auto_submit_low_confidence": True,
                "low_confidence_threshold": 0.6,
                "review_priority_high_risk": "urgent",
                "review_priority_low_confidence": "low",
                "require_manual_review": False
            }
            self.set_review_rules(default_rules)
        
        if not self.redis_client.exists(f"{self._prefix}{RuleCategory.VIDEO_SETTINGS}"):
            video_settings = {
                "sample_interval": 1.0,
                "min_risk_level": "low_risk",
                "enable_frame_cache": True,
                "max_video_duration": 3600
            }
            self.set_video_settings(video_settings)
    
    def get_content_thresholds(self) -> Dict:
        data = self.redis_client.get(f"{self._prefix}{RuleCategory.CONTENT_THRESHOLD}")
        return json.loads(data) if data else {}
    
    def set_content_thresholds(self, thresholds: Dict) -> bool:
        thresholds["updated_at"] = datetime.utcnow().isoformat()
        return self.redis_client.set(
            f"{self._prefix}{RuleCategory.CONTENT_THRESHOLD}",
            json.dumps(thresholds)
        )
    
    def update_content_threshold(self, content_type: str, high: float = None, low: float = None) -> bool:
        thresholds = self.get_content_thresholds()
        if content_type not in thresholds:
            thresholds[content_type] = {}
        
        if high is not None:
            thresholds[content_type]["high"] = high
        if low is not None:
            thresholds[content_type]["low"] = low
        
        return self.set_content_thresholds(thresholds)
    
    def get_sensitive_words(self, category: str = None) -> List[str]:
        data = self.redis_client.get(f"{self._prefix}{RuleCategory.SENSITIVE_WORDS}")
        words_data = json.loads(data) if data else {}
        
        if category:
            return words_data.get(category, [])
        return words_data.get("all", [])
    
    def set_sensitive_words(self, words: List[str], category: str = "all") -> bool:
        data = self.redis_client.get(f"{self._prefix}{RuleCategory.SENSITIVE_WORDS}")
        words_data = json.loads(data) if data else {}
        
        words_data[category] = words
        words_data["updated_at"] = datetime.utcnow().isoformat()
        
        all_words = set()
        for cat_words in words_data.values():
            if isinstance(cat_words, list):
                all_words.update(cat_words)
        words_data["all"] = list(all_words)
        
        return self.redis_client.set(
            f"{self._prefix}{RuleCategory.SENSITIVE_WORDS}",
            json.dumps(words_data)
        )
    
    def add_sensitive_word(self, word: str, category: str = "all") -> bool:
        words = self.get_sensitive_words(category)
        if word not in words:
            words.append(word)
            return self.set_sensitive_words(words, category)
        return True
    
    def remove_sensitive_word(self, word: str, category: str = "all") -> bool:
        words = self.get_sensitive_words(category)
        if word in words:
            words.remove(word)
            return self.set_sensitive_words(words, category)
        return True
    
    def check_sensitive_content(self, text: str) -> Dict:
        all_words = self.get_sensitive_words("all")
        found_words = []
        
        for word in all_words:
            if word and word.lower() in text.lower():
                found_words.append(word)
        
        return {
            "has_sensitive": len(found_words) > 0,
            "matched_words": found_words,
            "count": len(found_words)
        }
    
    def get_review_rules(self) -> Dict:
        data = self.redis_client.get(f"{self._prefix}{RuleCategory.REVIEW_RULES}")
        return json.loads(data) if data else {}
    
    def set_review_rules(self, rules: Dict) -> bool:
        rules["updated_at"] = datetime.utcnow().isoformat()
        return self.redis_client.set(
            f"{self._prefix}{RuleCategory.REVIEW_RULES}",
            json.dumps(rules)
        )
    
    def should_auto_submit_review(self, risk_level: str, confidence: float) -> tuple[bool, str]:
        rules = self.get_review_rules()
        
        if risk_level == "high_risk" and rules.get("auto_submit_high_risk", True):
            return True, rules.get("review_priority_high_risk", "urgent")
        
        if (confidence < rules.get("low_confidence_threshold", 0.6) and 
            rules.get("auto_submit_low_confidence", True)):
            return True, rules.get("review_priority_low_confidence", "low")
        
        return False, "medium"
    
    def get_video_settings(self) -> Dict:
        data = self.redis_client.get(f"{self._prefix}{RuleCategory.VIDEO_SETTINGS}")
        return json.loads(data) if data else {}
    
    def set_video_settings(self, settings: Dict) -> bool:
        settings["updated_at"] = datetime.utcnow().isoformat()
        return self.redis_client.set(
            f"{self._prefix}{RuleCategory.VIDEO_SETTINGS}",
            json.dumps(settings)
        )
    
    def get_all_config(self) -> Dict:
        return {
            "content_thresholds": self.get_content_thresholds(),
            "sensitive_words": self.get_sensitive_words(),
            "review_rules": self.get_review_rules(),
            "video_settings": self.get_video_settings()
        }
    
    def reset_to_default(self) -> bool:
        self.redis_client.delete(f"{self._prefix}{RuleCategory.CONTENT_THRESHOLD}")
        self.redis_client.delete(f"{self._prefix}{RuleCategory.SENSITIVE_WORDS}")
        self.redis_client.delete(f"{self._prefix}{RuleCategory.REVIEW_RULES}")
        self.redis_client.delete(f"{self._prefix}{RuleCategory.VIDEO_SETTINGS}")
        self._init_default_config()
        return True

rules_config = RulesConfigManager()
