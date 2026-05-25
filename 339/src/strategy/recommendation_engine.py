import json
import random
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from collections import defaultdict
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from common.logger import get_logger
from common.utils import (
    load_config,
    get_risk_level,
    to_json_safe,
    parse_json_safe
)
from redis.cache_manager import RedisCacheManager

logger = get_logger("RecommendationEngine")


class RiskScoring:
    def __init__(self, cache_manager: RedisCacheManager):
        self.config = load_config()
        self.model_config = self.config["model"]
        self.cache = cache_manager
        
        self.high_threshold = self.model_config["high_risk_threshold"]
        self.medium_threshold = self.model_config["medium_risk_threshold"]
    
    def calculate_composite_score(self, user_id: str) -> Dict:
        risk_data = self.cache.get_risk_score(user_id)
        profile = self.cache.get_user_profile(user_id)
        features = self.cache.get_user_features(user_id)
        
        if not risk_data:
            return {"risk_level": "unknown", "composite_score": 0}
        
        base_score = risk_data.get("churn_probability", 0)
        
        feature_factor = 1.0
        if features:
            days_since = features.get("days_since_last_event", 0)
            event_freq = features.get("event_frequency", 0)
            error_rate = features.get("window_30d_error_rate", 0)
            
            if days_since > 14:
                feature_factor *= 1.3
            elif days_since > 7:
                feature_factor *= 1.15
            
            if event_freq < 0.1:
                feature_factor *= 1.2
            
            if error_rate > 0.1:
                feature_factor *= 1.1
        
        value_factor = 1.0
        if profile:
            total_spend = profile.get("total_spend", 0)
            if total_spend > 5000:
                value_factor *= 1.2
            elif total_spend > 1000:
                value_factor *= 1.1
        
        composite_score = min(base_score * feature_factor * value_factor, 1.0)
        risk_level = get_risk_level(composite_score, self.config)
        
        return {
            "user_id": user_id,
            "base_score": float(base_score),
            "composite_score": float(composite_score),
            "risk_level": risk_level,
            "feature_factor": float(feature_factor),
            "value_factor": float(value_factor),
            "calculated_at": datetime.now().isoformat()
        }


class NotificationTemplate:
    TEMPLATES = {
        "high": {
            "premium_offer": {
                "title": "专属优惠 - 为您保留的特权",
                "body": "尊敬的用户，我们注意到您最近访问较少。为您准备了专属VIP礼遇，立即享受8折优惠！",
                "cta": "立即领取",
                "priority": 10
            },
            "personal_discount": {
                "title": "您的专属折扣码已生成",
                "body": "好久不见！使用专享折扣码 COMEBACK20，立享8折优惠，期待您的回归。",
                "cta": "立即使用",
                "priority": 9
            },
            "support_reach_out": {
                "title": "我们想念您 - 需要帮助吗？",
                "body": "您好！我们注意到您已有一段时间没有登录。是否遇到了什么问题？我们的客服团队随时为您服务。",
                "cta": "联系客服",
                "priority": 8
            }
        },
        "medium": {
            "newsletter": {
                "title": "本周精选 - 您可能感兴趣的内容",
                "body": "根据您的偏好，我们为您精选了以下内容和优惠活动...",
                "cta": "查看详情",
                "priority": 7
            },
            "feature_highlight": {
                "title": "新功能上线 - 提升您的体验",
                "body": "我们刚刚推出了全新的个性化推荐功能，让您更快找到想要的内容。",
                "cta": "立即体验",
                "priority": 6
            },
            "loyalty_points": {
                "title": "您的积分即将过期 - 快来兑换",
                "body": "提醒您有{points}积分将在7天后过期，立即兑换心仪礼品吧！",
                "cta": "查看积分",
                "priority": 5
            }
        },
        "low": {
            "general_announcement": {
                "title": "系统升级通知",
                "body": "我们对系统进行了全面升级，带来更快的响应速度和更好的用户体验。",
                "cta": "了解更多",
                "priority": 4
            },
            "new_feature_notify": {
                "title": "探索我们的新功能",
                "body": "我们不断改进产品，最新推出的功能一定能给您带来惊喜。",
                "cta": "立即探索",
                "priority": 3
            }
        }
    }
    
    @classmethod
    def get_template(cls, risk_level: str, action_type: str) -> Optional[Dict]:
        return cls.TEMPLATES.get(risk_level, {}).get(action_type)
    
    @classmethod
    def generate_content(cls, template: Dict, user_data: Dict) -> Dict:
        content = template.copy()
        
        total_spend = user_data.get("profile", {}).get("total_spend", 0)
        points = int(total_spend / 10)
        
        for key in ["title", "body"]:
            if key in content:
                content[key] = content[key].format(points=points)
        
        return content


class TouchChannelSelector:
    CHANNEL_EFFECTIVENESS = {
        "push": {"high": 0.85, "medium": 0.70, "low": 0.50, "cost": 0.1},
        "in_app": {"high": 0.80, "medium": 0.75, "low": 0.60, "cost": 0.05},
        "email": {"high": 0.65, "medium": 0.60, "low": 0.45, "cost": 0.02},
        "sms": {"high": 0.75, "medium": 0.50, "low": 0.30, "cost": 0.15}
    }
    
    def __init__(self):
        self.config = load_config()
        self.default_channel = self.config["strategy"]["default_channel"]
    
    def select_best_channel(self, user_id: str, risk_level: str, 
                           user_data: Dict) -> Tuple[str, float]:
        user_actions = user_data.get("actions", [])
        
        channel_success = defaultdict(lambda: {"success": 0, "total": 0})
        for action in user_actions:
            if action.get("result"):
                channel = action.get("channel", self.default_channel)
                channel_success[channel]["total"] += 1
                if action["result"].get("converted", False):
                    channel_success[channel]["success"] += 1
        
        channel_scores = {}
        for channel in self.config["strategy"]["notification_channels"]:
            base_effect = self.CHANNEL_EFFECTIVENESS.get(channel, {}).get(risk_level, 0.5)
            cost = self.CHANNEL_EFFECTIVENESS.get(channel, {}).get("cost", 0)
            
            history = channel_success[channel]
            if history["total"] > 0:
                history_rate = history["success"] / history["total"]
                effect = 0.7 * base_effect + 0.3 * history_rate
            else:
                effect = base_effect
            
            roi = effect / max(cost, 0.01)
            channel_scores[channel] = {"effectiveness": effect, "cost": cost, "roi": roi}
        
        best_channel = max(channel_scores.items(), key=lambda x: x[1]["roi"])[0]
        best_score = channel_scores[best_channel]
        
        logger.debug(f"Selected channel {best_channel} for user {user_id} "
                    f"(effectiveness={best_score['effectiveness']:.2f}, "
                    f"cost={best_score['cost']:.2f}, roi={best_score['roi']:.2f})")
        
        return best_channel, best_score["effectiveness"]


class RecommendationEngine:
    def __init__(self, cache_manager: RedisCacheManager):
        self.config = load_config()
        self.cache = cache_manager
        self.risk_scoring = RiskScoring(cache_manager)
        self.channel_selector = TouchChannelSelector()
        
        self.strategy_config = self.config["strategy"]
        self.high_risk_actions = self.strategy_config["high_risk_actions"]
        self.medium_risk_actions = self.strategy_config["medium_risk_actions"]
        self.low_risk_actions = self.strategy_config["low_risk_actions"]
        self.cooldown_hours = self.strategy_config["action_cooldown_hours"]
    
    def get_recommendation(self, user_id: str, 
                          ab_variant: Optional[str] = None) -> Dict:
        user_data = self.cache.get_user_full_data(user_id)
        risk_data = user_data.get("risk")
        
        if not risk_data:
            return {
                "user_id": user_id,
                "recommended": False,
                "reason": "no_risk_data"
            }
        
        risk_level = risk_data.get("risk_level", "low")
        
        if self.cache.check_action_cooldown(user_id):
            return {
                "user_id": user_id,
                "recommended": False,
                "reason": "cooldown_active"
            }
        
        composite_score = self.risk_scoring.calculate_composite_score(user_id)
        
        action_type = self._select_action_type(risk_level, composite_score, user_data, ab_variant)
        
        if not action_type:
            return {
                "user_id": user_id,
                "recommended": False,
                "reason": "no_suitable_action"
            }
        
        channel, effectiveness = self.channel_selector.select_best_channel(
            user_id, risk_level, user_data
        )
        
        template = NotificationTemplate.get_template(risk_level, action_type)
        if not template:
            template = NotificationTemplate.get_template("medium", "newsletter")
        
        content = NotificationTemplate.generate_content(template, user_data)
        
        recommendation = {
            "user_id": user_id,
            "risk_level": risk_level,
            "churn_probability": risk_data.get("churn_probability", 0),
            "composite_score": composite_score.get("composite_score", 0),
            "expected_days_to_churn": risk_data.get("expected_days_to_churn", 0),
            "action_type": action_type,
            "channel": channel,
            "channel_effectiveness": effectiveness,
            "priority": template.get("priority", 0),
            "content": content,
            "ab_variant": ab_variant,
            "recommended": True,
            "generated_at": datetime.now().isoformat()
        }
        
        return recommendation
    
    def _select_action_type(self, risk_level: str, 
                           composite_score: Dict,
                           user_data: Dict,
                           ab_variant: Optional[str]) -> str:
        if ab_variant == "aggressive":
            return self.high_risk_actions[0]
        elif ab_variant == "conservative":
            return self.medium_risk_actions[0]
        
        actions = []
        if risk_level == "high":
            actions = self.high_risk_actions.copy()
        elif risk_level == "medium":
            actions = self.medium_risk_actions.copy()
        else:
            actions = self.low_risk_actions.copy()
        
        profile = user_data.get("profile", {})
        features = user_data.get("features", {})
        
        scored_actions = []
        for action in actions:
            score = 0
            
            if action == "premium_offer" and profile.get("total_spend", 0) > 1000:
                score += 10
            if action == "personal_discount" and composite_score["composite_score"] > 0.8:
                score += 8
            if action == "support_reach_out" and features and features.get("window_30d_error_count", 0) > 0:
                score += 10
            
            if action == "loyalty_points" and profile.get("total_spend", 0) > 500:
                score += 5
            
            scored_actions.append((action, score))
        
        scored_actions.sort(key=lambda x: x[1], reverse=True)
        
        if scored_actions and scored_actions[0][1] > 0:
            return scored_actions[0][0]
        elif actions:
            return random.choice(actions)
        
        return ""
    
    def batch_recommend(self, user_ids: List[str], 
                       ab_assignments: Optional[Dict[str, str]] = None) -> List[Dict]:
        recommendations = []
        
        for user_id in user_ids:
            ab_variant = ab_assignments.get(user_id) if ab_assignments else None
            rec = self.get_recommendation(user_id, ab_variant)
            recommendations.append(rec)
        
        recommendations.sort(key=lambda x: x.get("priority", 0), reverse=True)
        return recommendations
    
    def execute_recommendation(self, recommendation: Dict) -> str:
        if not recommendation.get("recommended", False):
            return ""
        
        user_id = recommendation["user_id"]
        action_type = recommendation["action_type"]
        channel = recommendation["channel"]
        
        metadata = {
            "risk_level": recommendation["risk_level"],
            "churn_probability": recommendation["churn_probability"],
            "content": recommendation["content"],
            "ab_variant": recommendation.get("ab_variant"),
            "priority": recommendation.get("priority", 0)
        }
        
        action_id = self.cache.record_action_taken(
            user_id=user_id,
            action=action_type,
            channel=channel,
            metadata=metadata
        )
        
        notification = {
            "action_id": action_id,
            "action_type": action_type,
            "channel": channel,
            "content": recommendation["content"],
            "priority": recommendation.get("priority", 0),
            "ab_variant": recommendation.get("ab_variant")
        }
        
        notif_id = self.cache.store_notification(user_id, notification)
        
        logger.info(f"Executed recommendation for user {user_id}: "
                   f"action={action_type}, channel={channel}, "
                   f"action_id={action_id}, notification_id={notif_id}")
        
        return action_id
    
    def process_high_risk_users(self, limit: int = 100, 
                               ab_assignments: Optional[Dict[str, str]] = None) -> List[str]:
        high_risk_users = self.cache.get_high_risk_users(limit=limit)
        
        user_ids = [u["user_id"] for u in high_risk_users]
        recommendations = self.batch_recommend(user_ids, ab_assignments)
        
        executed_ids = []
        for rec in recommendations:
            if rec.get("recommended", False):
                action_id = self.execute_recommendation(rec)
                if action_id:
                    executed_ids.append(action_id)
        
        logger.info(f"Processed {len(high_risk_users)} high risk users, "
                   f"executed {len(executed_ids)} recommendations")
        
        return executed_ids
    
    def get_action_performance(self, days: int = 7) -> Dict:
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        performance = {
            "total_actions": 0,
            "actions_by_channel": defaultdict(int),
            "actions_by_type": defaultdict(int),
            "actions_by_risk_level": defaultdict(int),
            "conversion_rate": 0.0,
            "churn_prevention_rate": 0.0
        }
        
        all_user_keys = self.cache._execute("keys", "user:*:actions")
        if isinstance(all_user_keys, list):
            for key in all_user_keys:
                actions_data = self.cache._execute("hgetall", key)
                for action_id, action_str in actions_data.items():
                    action = parse_json_safe(action_str)
                    if not action:
                        continue
                    
                    action_time = datetime.fromisoformat(action["timestamp"])
                    if action_time < start_date:
                        continue
                    
                    performance["total_actions"] += 1
                    performance["actions_by_channel"][action["channel"]] += 1
                    performance["actions_by_type"][action["action"]] += 1
                    
                    risk_level = action.get("metadata", {}).get("risk_level", "unknown")
                    performance["actions_by_risk_level"][risk_level] += 1
        
        return performance
    
    def get_strategy_summary(self) -> Dict:
        stats = self.cache.get_statistics()
        
        return {
            "total_users": stats["total_users"],
            "high_risk_users": stats["high_risk_users"],
            "risk_distribution": stats["risk_distribution"],
            "available_actions": {
                "high": self.high_risk_actions,
                "medium": self.medium_risk_actions,
                "low": self.low_risk_actions
            },
            "available_channels": self.strategy_config["notification_channels"],
            "cooldown_hours": self.cooldown_hours,
            "notification_templates": list(NotificationTemplate.TEMPLATES.keys())
        }


def main():
    cache = RedisCacheManager(use_redis=False)
    engine = RecommendationEngine(cache)
    
    print("=" * 60)
    print("Recommendation Engine")
    print("=" * 60)
    
    print("\n1. Generate recommendation for test user")
    print("2. Process high risk users")
    print("3. Show strategy summary")
    print("4. Show action performance")
    
    choice = input("\nEnter your choice (1-4): ").strip()
    
    if choice == "1":
        user_id = input("Enter user ID: ").strip() or "test_user_001"
        
        profile = {
            "user_id": user_id,
            "user_level": "gold",
            "region": "north",
            "total_spend": 5000,
            "signup_date": datetime.now().timestamp() - 86400 * 180
        }
        cache.store_user_profile(user_id, profile)
        
        features = {
            "window_7d_total_events": 5,
            "window_30d_total_events": 10,
            "days_since_last_event": 10,
            "event_frequency": 0.1,
            "window_30d_error_count": 1
        }
        cache.store_user_features(user_id, features)
        
        risk_level = input("Enter risk level (high/medium/low): ").strip() or "high"
        prob = float(input("Enter churn probability (0-1): ").strip() or "0.75")
        
        prediction = {
            "churn_probability": prob,
            "expected_days_to_churn": 7,
            "risk_level": risk_level,
            "risk_score": prob * 1000,
            "prediction_timestamp": datetime.now().isoformat()
        }
        cache.store_risk_score(user_id, prediction)
        
        ab_variant = input("Enter A/B variant (control/aggressive/conservative, optional): ").strip() or None
        
        rec = engine.get_recommendation(user_id, ab_variant)
        
        print("\n" + "=" * 60)
        print("Recommendation:")
        print(f"  User ID: {rec['user_id']}")
        print(f"  Recommended: {rec['recommended']}")
        if rec["recommended"]:
            print(f"  Risk Level: {rec['risk_level'].upper()}")
            print(f"  Churn Probability: {rec['churn_probability']:.2%}")
            print(f"  Expected Days to Churn: {rec['expected_days_to_churn']:.1f}")
            print(f"  Action Type: {rec['action_type']}")
            print(f"  Channel: {rec['channel']}")
            print(f"  Priority: {rec['priority']}")
            print(f"  Content Title: {rec['content']['title']}")
            print(f"  Content Body: {rec['content']['body'][:80]}...")
            if rec.get('ab_variant'):
                print(f"  A/B Variant: {rec['ab_variant']}")
            
            execute = input("\nExecute this recommendation? (y/n): ").strip().lower()
            if execute == "y":
                action_id = engine.execute_recommendation(rec)
                print(f"Executed. Action ID: {action_id}")
        else:
            print(f"  Reason: {rec.get('reason', 'unknown')}")
        print("=" * 60)
    
    elif choice == "2":
        num_users = int(input("Number of high risk users to create and process: "))
        
        import random
        for i in range(num_users):
            uid = f"high_risk_{i:03d}"
            profile = {
                "user_id": uid,
                "user_level": random.choice(["silver", "gold", "platinum"]),
                "total_spend": random.uniform(100, 10000)
            }
            cache.store_user_profile(uid, profile)
            
            prob = random.uniform(0.7, 0.99)
            prediction = {
                "churn_probability": prob,
                "expected_days_to_churn": random.randint(1, 14),
                "risk_level": "high",
                "risk_score": prob * 1000,
                "prediction_timestamp": datetime.now().isoformat()
            }
            cache.store_risk_score(uid, prediction)
            cache.tag_high_risk_user(uid, prediction)
        
        action_ids = engine.process_high_risk_users(limit=num_users)
        print(f"Processed {num_users} users, executed {len(action_ids)} actions")
        for aid in action_ids[:5]:
            print(f"  - {aid}")
    
    elif choice == "3":
        summary = engine.get_strategy_summary()
        print("\n" + "=" * 60)
        print("Strategy Summary:")
        print(f"  Total Users: {summary['total_users']}")
        print(f"  High Risk Users: {summary['high_risk_users']}")
        print(f"  Risk Distribution: {summary['risk_distribution']}")
        print(f"\n  Actions by Risk Level:")
        for level, actions in summary["available_actions"].items():
            print(f"    {level.upper()}: {', '.join(actions)}")
        print(f"\n  Available Channels: {', '.join(summary['available_channels'])}")
        print(f"  Action Cooldown: {summary['cooldown_hours']} hours")
        print("=" * 60)
    
    elif choice == "4":
        days = int(input("Enter number of days to analyze: ") or "7")
        perf = engine.get_action_performance(days=days)
        
        print("\n" + "=" * 60)
        print(f"Action Performance (last {days} days):")
        print(f"  Total Actions: {perf['total_actions']}")
        print(f"\n  By Channel:")
        for channel, count in perf["actions_by_channel"].items():
            print(f"    {channel}: {count}")
        print(f"\n  By Type:")
        for action, count in perf["actions_by_type"].items():
            print(f"    {action}: {count}")
        print(f"\n  By Risk Level:")
        for level, count in perf["actions_by_risk_level"].items():
            print(f"    {level}: {count}")
        print("=" * 60)


if __name__ == "__main__":
    main()
