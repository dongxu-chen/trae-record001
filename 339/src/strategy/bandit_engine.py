import json
import time
import math
import random
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from collections import defaultdict
from dataclasses import dataclass, field, asdict
from enum import Enum
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False

from common.logger import get_logger
from common.utils import load_config, get_risk_level, to_json_safe, parse_json_safe
from redis.cache_manager import RedisCacheManager

logger = get_logger("BanditEngine")


class BanditStrategy(Enum):
    EPSILON_GREEDY = "epsilon_greedy"
    THOMPSON_SAMPLING = "thompson_sampling"
    UCB = "ucb"
    BAYESIAN_UCB = "bayesian_ucb"


ACTION_TYPES_BY_RISK = {
    "high": ["premium_offer", "personal_discount", "support_reach_out", "loyalty_reward"],
    "medium": ["newsletter", "feature_highlight", "loyalty_points", "survey"],
    "low": ["general_announcement", "new_feature_notify", "seasonal_promotion", "feedback_request"]
}

CHANNELS = ["push", "email", "sms", "in_app"]

NOTIFICATION_TEMPLATES = {
    "high": {
        "premium_offer": {
            "title": "专属VIP礼遇 - 限时领取",
            "body": "尊敬的用户，我们注意到您近期访问有所减少。为回馈您的支持，特献上专属8折VIP礼遇，立即领取让体验更精彩！",
            "cta": "立即领取",
            "priority": 10
        },
        "personal_discount": {
            "title": "您的专属折扣码已送达",
            "body": "好久不见！使用专属折扣码 WELCOMEBACK20，立享8折优惠，我们期待您的回归。",
            "cta": "立即使用",
            "priority": 9
        },
        "support_reach_out": {
            "title": "我们想念您 - 需要帮助吗？",
            "body": "您好！我们注意到您已有一段时间没有登录。遇到了什么问题吗？我们的客服团队随时为您提供服务。",
            "cta": "联系客服",
            "priority": 8
        },
        "loyalty_reward": {
            "title": "忠诚度奖励已解锁",
            "body": "感谢您一直以来的支持！我们为您准备了一份专属奖励，立即查看您的专属福利。",
            "cta": "查看奖励",
            "priority": 7
        }
    },
    "medium": {
        "newsletter": {
            "title": "本周精选 - 为您定制的内容",
            "body": "根据您的偏好，我们为您精选了本周最值得关注的内容和优惠活动...",
            "cta": "查看详情",
            "priority": 6
        },
        "feature_highlight": {
            "title": "新功能上线 - 提升您的体验",
            "body": "我们刚刚推出了全新的个性化推荐功能，让您更快找到想要的内容。",
            "cta": "立即体验",
            "priority": 5
        },
        "loyalty_points": {
            "title": "您的积分即将过期 - 快来兑换",
            "body": "提醒您有{points}积分将在7天后过期，立即兑换心仪礼品吧！",
            "cta": "查看积分",
            "priority": 4
        },
        "survey": {
            "title": "我们想听听您的意见",
            "body": "花2分钟完成简短调查，帮助我们为您提供更好的服务。完成后可获得50积分奖励。",
            "cta": "参与调查",
            "priority": 3
        }
    },
    "low": {
        "general_announcement": {
            "title": "系统升级通知",
            "body": "我们对系统进行了全面升级，带来更快的响应速度和更好的用户体验。",
            "cta": "了解更多",
            "priority": 2
        },
        "new_feature_notify": {
            "title": "探索我们的新功能",
            "body": "我们不断改进产品，最新推出的功能一定能给您带来惊喜。",
            "cta": "立即探索",
            "priority": 1
        },
        "seasonal_promotion": {
            "title": "限时特惠活动进行中",
            "body": "本季特惠活动正在进行中，精选商品低至5折，快来看看吧！",
            "cta": "查看活动",
            "priority": 2
        },
        "feedback_request": {
            "title": "您的反馈对我们很重要",
            "body": "我们希望了解您的使用体验，您的每一条建议都将帮助我们变得更好。",
            "cta": "提供反馈",
            "priority": 1
        }
    }
}

CHANNEL_EFFECTIVENESS_BASE = {
    "push": {"high": 0.85, "medium": 0.70, "low": 0.50, "cost": 0.1},
    "in_app": {"high": 0.80, "medium": 0.75, "low": 0.60, "cost": 0.05},
    "email": {"high": 0.65, "medium": 0.60, "low": 0.45, "cost": 0.02},
    "sms": {"high": 0.75, "medium": 0.50, "low": 0.30, "cost": 0.15}
}


@dataclass
class ArmStats:
    action_type: str
    channel: str
    risk_level: str
    success_count: int = 0
    total_count: int = 0
    total_reward: float = 0.0
    last_updated: str = ""
    alpha_prior: float = 1.0
    beta_prior: float = 1.0

    @property
    def conversion_rate(self) -> float:
        return self.success_count / max(self.total_count, 1)

    @property
    def avg_reward(self) -> float:
        return self.total_reward / max(self.total_count, 1)

    @property
    def alpha(self) -> float:
        return self.alpha_prior + self.success_count

    @property
    def beta(self) -> float:
        return self.beta_prior + (self.total_count - self.success_count)

    def get_key(self) -> str:
        return f"{self.risk_level}:{self.action_type}:{self.channel}"


@dataclass
class BanditRecommendation:
    user_id: str
    risk_level: str
    churn_probability: float
    action_type: str
    channel: str
    content: Dict
    arm_key: str
    confidence: float
    exploration_flag: bool
    strategy: str
    expected_reward: float
    priority: int
    stratum: str = ""
    generated_at: str = ""


class EpsilonGreedyBandit:
    def __init__(self, epsilon: float = 0.15, epsilon_decay: float = 0.995, min_epsilon: float = 0.05):
        self.epsilon = epsilon
        self.epsilon_decay = epsilon_decay
        self.min_epsilon = min_epsilon
        self.total_rounds = 0

    def select_arm(self, arms: List[Tuple[str, ArmStats]], explore_bonus: Optional[Dict] = None) -> str:
        self.total_rounds += 1
        self.epsilon = max(self.epsilon * self.epsilon_decay, self.min_epsilon)

        if random.random() < self.epsilon:
            return random.choice(arms)[0]

        best_arm = None
        best_reward = -float("inf")

        for arm_key, stats in arms:
            reward = stats.avg_reward
            if explore_bonus and arm_key in explore_bonus:
                reward += explore_bonus[arm_key]
            if reward > best_reward:
                best_reward = reward
                best_arm = arm_key

        return best_arm or arms[0][0]


class ThompsonSamplingBandit:
    def __init__(self, alpha_prior: float = 1.0, beta_prior: float = 1.0):
        self.alpha_prior = alpha_prior
        self.beta_prior = beta_prior

    def select_arm(self, arms: List[Tuple[str, ArmStats]], explore_bonus: Optional[Dict] = None) -> str:
        if not NUMPY_AVAILABLE:
            sampled_rates = {}
            for arm_key, stats in arms:
                alpha = self.alpha_prior + stats.success_count
                beta = self.beta_prior + (stats.total_count - stats.success_count)
                samples = [random.betavariate(alpha, max(beta, 0.01)) for _ in range(10)]
                sampled_rates[arm_key] = sum(samples) / len(samples)
        else:
            sampled_rates = {}
            for arm_key, stats in arms:
                alpha = self.alpha_prior + stats.success_count
                beta = self.beta_prior + (stats.total_count - stats.success_count)
                sampled_rates[arm_key] = np.random.beta(alpha, max(beta, 0.01))

        if explore_bonus:
            for arm_key in sampled_rates:
                if arm_key in explore_bonus:
                    sampled_rates[arm_key] += explore_bonus[arm_key]

        return max(sampled_rates.items(), key=lambda x: x[1])[0]


class UCBBandit:
    def __init__(self, confidence: float = 0.95):
        self.confidence = confidence
        self.total_rounds = 0

    def select_arm(self, arms: List[Tuple[str, ArmStats]], explore_bonus: Optional[Dict] = None) -> str:
        self.total_rounds += 1
        c = math.sqrt(2 * math.log(max(self.total_rounds, 2)))

        ucb_values = {}
        for arm_key, stats in arms:
            if stats.total_count == 0:
                ucb_values[arm_key] = float("inf")
            else:
                mean_reward = stats.avg_reward
                exploration_bonus = c / math.sqrt(stats.total_count)
                ucb_values[arm_key] = mean_reward + exploration_bonus

            if explore_bonus and arm_key in explore_bonus:
                ucb_values[arm_key] += explore_bonus[arm_key]

        return max(ucb_values.items(), key=lambda x: x[1])[0]


class BanditRecommendationEngine:
    def __init__(self, cache_manager: RedisCacheManager, strategy: BanditStrategy = BanditStrategy.THOMPSON_SAMPLING):
        self.config = load_config()
        self.cache = cache_manager
        self.strategy = strategy

        self.arm_stats: Dict[str, ArmStats] = {}
        self.user_arm_history: Dict[str, List[Dict]] = defaultdict(list)

        self.epsilon_greedy = EpsilonGreedyBandit(epsilon=0.15)
        self.thompson_sampling = ThompsonSamplingBandit()
        self.ucb = UCBBandit()

        self.min_samples_per_arm: int = 5
        self.default_cooldown_hours: int = 48

        self._initialize_arms()
        self._load_stats_from_cache()

        logger.info(f"BanditEngine initialized with strategy: {strategy.value}")

    def _initialize_arms(self):
        for risk_level in ACTION_TYPES_BY_RISK:
            for action_type in ACTION_TYPES_BY_RISK[risk_level]:
                for channel in CHANNELS:
                    key = f"{risk_level}:{action_type}:{channel}"
                    if key not in self.arm_stats:
                        self.arm_stats[key] = ArmStats(
                            action_type=action_type,
                            channel=channel,
                            risk_level=risk_level
                        )

    def _load_stats_from_cache(self):
        stats_data = self.cache._execute("get", "bandit_arm_stats")
        if stats_data:
            try:
                if isinstance(stats_data, bytes):
                    stats_data = stats_data.decode("utf-8")
                saved_stats = json.loads(stats_data)
                for key, data in saved_stats.items():
                    if key in self.arm_stats:
                        self.arm_stats[key].success_count = data.get("success_count", 0)
                        self.arm_stats[key].total_count = data.get("total_count", 0)
                        self.arm_stats[key].total_reward = data.get("total_reward", 0.0)
                logger.info(f"Loaded stats for {len(saved_stats)} arms from cache")
            except Exception as e:
                logger.warning(f"Failed to load arm stats from cache: {e}")

    def _save_stats_to_cache(self):
        try:
            stats_dict = {}
            for key, stats in self.arm_stats.items():
                stats_dict[key] = {
                    "success_count": stats.success_count,
                    "total_count": stats.total_count,
                    "total_reward": stats.total_reward,
                    "last_updated": datetime.now().isoformat()
                }
            self.cache._execute("set", "bandit_arm_stats", json.dumps(stats_dict))
        except Exception as e:
            logger.warning(f"Failed to save arm stats to cache: {e}")

    def _get_arms_for_risk_level(self, risk_level: str) -> List[Tuple[str, ArmStats]]:
        arms = []
        for action_type in ACTION_TYPES_BY_RISK.get(risk_level, []):
            for channel in CHANNELS:
                key = f"{risk_level}:{action_type}:{channel}"
                if key in self.arm_stats:
                    arms.append((key, self.arm_stats[key]))
        return arms

    def _calculate_exploration_bonus(self, risk_level: str, user_data: Dict) -> Dict[str, float]:
        bonuses = {}
        arms = self._get_arms_for_risk_level(risk_level)

        for arm_key, stats in arms:
            bonus = 0.0
            if stats.total_count < self.min_samples_per_arm:
                bonus += 0.3 * (1 - stats.total_count / self.min_samples_per_arm)

            days_since_update = 365
            if stats.last_updated:
                try:
                    last_update = datetime.fromisoformat(stats.last_updated)
                    days_since_update = (datetime.now() - last_update).days
                except Exception:
                    pass
            bonus += 0.1 * min(days_since_update / 30, 1.0)

            total_arms = len(arms)
            if total_arms > 0:
                avg_count = sum(s.total_count for _, s in arms) / total_arms
                if stats.total_count < avg_count * 0.5:
                    bonus += 0.1

            bonuses[arm_key] = bonus

        return bonuses

    def _select_channel(self, risk_level: str, action_type: str, user_data: Dict) -> Tuple[str, float]:
        channel_rewards = {}
        for channel in CHANNELS:
            key = f"{risk_level}:{action_type}:{channel}"
            stats = self.arm_stats.get(key)
            if stats and stats.total_count > 0:
                channel_rewards[channel] = stats.avg_reward
            else:
                base_effect = CHANNEL_EFFECTIVENESS_BASE.get(channel, {}).get(risk_level, 0.5)
                channel_rewards[channel] = base_effect

        profile = user_data.get("profile", {})
        total_spend = profile.get("total_spend", 0)
        if total_spend > 5000:
            channel_rewards["push"] += 0.1
            channel_rewards["sms"] += 0.1

        best_channel = max(channel_rewards.items(), key=lambda x: x[1])
        return best_channel

    def select_action(self, user_id: str, risk_data: Dict, user_data: Dict) -> Optional[BanditRecommendation]:
        if not risk_data:
            return None

        risk_level = risk_data.get("risk_level", "low")
        churn_prob = risk_data.get("churn_probability", 0)

        if self.cache.check_action_cooldown(user_id):
            logger.debug(f"User {user_id} is in cooldown period")
            return None

        arms = self._get_arms_for_risk_level(risk_level)
        if not arms:
            return None

        explore_bonus = self._calculate_exploration_bonus(risk_level, user_data)

        if self.strategy == BanditStrategy.EPSILON_GREEDY:
            selected_key = self.epsilon_greedy.select_arm(arms, explore_bonus)
            is_exploration = random.random() < self.epsilon_greedy.epsilon
        elif self.strategy == BanditStrategy.UCB:
            selected_key = self.ucb.select_arm(arms, explore_bonus)
            arm_stats = self.arm_stats[selected_key]
            is_exploration = arm_stats.total_count < self.min_samples_per_arm
        else:
            selected_key = self.thompson_sampling.select_arm(arms, explore_bonus)
            arm_stats = self.arm_stats[selected_key]
            if NUMPY_AVAILABLE:
                alpha = arm_stats.alpha
                beta = max(arm_stats.beta, 0.01)
                sampled_rate = np.random.beta(alpha, beta)
            else:
                alpha = arm_stats.alpha
                beta = max(arm_stats.beta, 0.01)
                samples = [random.betavariate(alpha, beta) for _ in range(10)]
                sampled_rate = sum(samples) / len(samples)
            is_exploration = sampled_rate < 0.3 and arm_stats.total_count < 20

        action_type, channel = selected_key.split(":")[1], selected_key.split(":")[2]

        template = NOTIFICATION_TEMPLATES.get(risk_level, {}).get(action_type, {})
        content = self._generate_content(template, user_data) if template else {}

        arm_stats = self.arm_stats[selected_key]
        confidence = arm_stats.conversion_rate if arm_stats.total_count > 0 else 0.5
        expected_reward = arm_stats.avg_reward if arm_stats.total_count > 0 else 0.5

        stratum = ""
        profile = user_data.get("profile", {})
        if profile:
            user_level = profile.get("user_level", "new")
            level_map = {0: "new", 1: "bronze", 2: "silver", 3: "gold", 4: "platinum"}
            if isinstance(user_level, int):
                user_level = level_map.get(user_level, "new")
            stratum_map = {"new": "new_users", "bronze": "low_value", "silver": "mid_value", "gold": "high_value", "platinum": "premium"}
            stratum = stratum_map.get(user_level, "new_users")

        return BanditRecommendation(
            user_id=user_id,
            risk_level=risk_level,
            churn_probability=churn_prob,
            action_type=action_type,
            channel=channel,
            content=content,
            arm_key=selected_key,
            confidence=confidence,
            exploration_flag=is_exploration,
            strategy=self.strategy.value,
            expected_reward=expected_reward,
            priority=template.get("priority", 0),
            stratum=stratum,
            generated_at=datetime.now().isoformat()
        )

    def _generate_content(self, template: Dict, user_data: Dict) -> Dict:
        content = {}
        profile = user_data.get("profile", {})
        total_spend = profile.get("total_spend", 0)
        points = int(total_spend / 10)

        for key in ["title", "body", "cta"]:
            if key in template:
                content[key] = template[key].format(points=points)
        return content

    def record_result(self, user_id: str, arm_key: str, reward: float, converted: bool):
        if arm_key not in self.arm_stats:
            logger.warning(f"Unknown arm key: {arm_key}")
            return

        stats = self.arm_stats[arm_key]
        stats.total_count += 1
        stats.total_reward += reward
        if converted:
            stats.success_count += 1
        stats.last_updated = datetime.now().isoformat()

        self.user_arm_history[user_id].append({
            "arm_key": arm_key,
            "reward": reward,
            "converted": converted,
            "timestamp": datetime.now().isoformat()
        })

        self._save_stats_to_cache()
        logger.debug(f"Updated arm {arm_key}: reward={reward:.2f}, converted={converted}")

    def batch_recommend(self, user_ids: List[str]) -> List[BanditRecommendation]:
        recommendations = []
        for user_id in user_ids:
            user_data = self.cache.get_user_full_data(user_id)
            risk_data = user_data.get("risk")
            if risk_data:
                rec = self.select_action(user_id, risk_data, user_data)
                if rec:
                    recommendations.append(rec)

        recommendations.sort(key=lambda x: x.priority, reverse=True)
        return recommendations

    def execute_recommendation(self, recommendation: BanditRecommendation) -> str:
        metadata = {
            "risk_level": recommendation.risk_level,
            "churn_probability": recommendation.churn_probability,
            "content": recommendation.content,
            "strategy": recommendation.strategy,
            "exploration": recommendation.exploration_flag,
            "arm_key": recommendation.arm_key,
            "confidence": recommendation.confidence,
            "expected_reward": recommendation.expected_reward,
            "stratum": recommendation.stratum
        }

        action_id = self.cache.record_action_taken(
            user_id=recommendation.user_id,
            action=recommendation.action_type,
            channel=recommendation.channel,
            metadata=metadata
        )

        notification = {
            "action_id": action_id,
            "action_type": recommendation.action_type,
            "channel": recommendation.channel,
            "content": recommendation.content,
            "strategy": recommendation.strategy,
            "exploration": recommendation.exploration_flag,
            "arm_key": recommendation.arm_key
        }

        notif_id = self.cache.store_notification(recommendation.user_id, notification)

        logger.info(f"Bandit recommendation executed for user {recommendation.user_id}: "
                    f"action={recommendation.action_type}, channel={recommendation.channel}, "
                    f"strategy={recommendation.strategy}, exploration={recommendation.exploration_flag}")

        return action_id

    def process_high_risk_users(self, limit: int = 100) -> List[str]:
        high_risk_users = self.cache.get_high_risk_users(limit=limit)
        user_ids = [u["user_id"] for u in high_risk_users]

        recommendations = self.batch_recommend(user_ids)

        executed_ids = []
        for rec in recommendations:
            action_id = self.execute_recommendation(rec)
            if action_id:
                executed_ids.append(action_id)

        logger.info(f"Processed {len(high_risk_users)} high risk users with bandit, "
                    f"executed {len(executed_ids)} recommendations")

        return executed_ids

    def get_arm_performance(self) -> Dict:
        performance = {}
        for risk_level in ACTION_TYPES_BY_RISK:
            performance[risk_level] = {}
            for action_type in ACTION_TYPES_BY_RISK[risk_level]:
                performance[risk_level][action_type] = {}
                for channel in CHANNELS:
                    key = f"{risk_level}:{action_type}:{channel}"
                    stats = self.arm_stats.get(key)
                    if stats and stats.total_count > 0:
                        performance[risk_level][action_type][channel] = {
                            "impressions": stats.total_count,
                            "conversions": stats.success_count,
                            "conversion_rate": stats.conversion_rate,
                            "avg_reward": stats.avg_reward
                        }
                    else:
                        performance[risk_level][action_type][channel] = {
                            "impressions": 0,
                            "conversions": 0,
                            "conversion_rate": 0.0,
                            "avg_reward": 0.0
                        }

        return performance

    def get_summary(self) -> Dict:
        total_arms = len(self.arm_stats)
        trained_arms = sum(1 for s in self.arm_stats.values() if s.total_count > 0)
        total_impressions = sum(s.total_count for s in self.arm_stats.values())
        total_conversions = sum(s.success_count for s in self.arm_stats.values())

        best_arms = {}
        for risk_level in ACTION_TYPES_BY_RISK:
            best_reward = -1
            best_key = ""
            for action_type in ACTION_TYPES_BY_RISK[risk_level]:
                for channel in CHANNELS:
                    key = f"{risk_level}:{action_type}:{channel}"
                    stats = self.arm_stats.get(key)
                    if stats and stats.total_count > 0 and stats.avg_reward > best_reward:
                        best_reward = stats.avg_reward
                        best_key = key
            best_arms[risk_level] = {
                "best_arm": best_key,
                "best_reward": best_reward if best_reward > 0 else 0
            }

        return {
            "strategy": self.strategy.value,
            "total_arms": total_arms,
            "trained_arms": trained_arms,
            "total_impressions": total_impressions,
            "total_conversions": total_conversions,
            "overall_conversion_rate": total_conversions / max(total_impressions, 1),
            "best_arms_by_risk_level": best_arms,
            "epsilon": self.epsilon_greedy.epsilon,
            "min_samples_per_arm": self.min_samples_per_arm
        }

    def simulate_conversion(self, action_id: str, converted: bool, reward_magnitude: float = 1.0):
        actions = self.cache._execute("hgetall", f"action:{action_id}")
        if not actions:
            return

        try:
            if isinstance(actions, dict):
                metadata = parse_json_safe(actions.get("metadata", "{}"))
                arm_key = metadata.get("arm_key", "")
                user_id = actions.get("user_id", "")
            else:
                metadata = parse_json_safe(actions)
                arm_key = metadata.get("arm_key", "")
                user_id = metadata.get("user_id", "")
        except Exception:
            return

        reward = reward_magnitude if converted else 0.0
        if arm_key:
            self.record_result(user_id, arm_key, reward, converted)

    def update_strategy(self, strategy: BanditStrategy):
        self.strategy = strategy
        logger.info(f"Strategy updated to: {strategy.value}")


def main():
    cache = RedisCacheManager(use_redis=False)
    engine = BanditRecommendationEngine(cache, strategy=BanditStrategy.THOMPSON_SAMPLING)

    print("=" * 60)
    print("MULTI-ARMED BANDIT RECOMMENDATION ENGINE")
    print("=" * 60)
    print(f"\nStrategy: {engine.strategy.value}")
    print(f"Total arms: {engine.get_summary()['total_arms']}")

    print("\n" + "-" * 60)
    print("SIMULATING USER RECOMMENDATIONS")
    print("-" * 60)

    test_users = []
    user_levels = ["new", "bronze", "silver", "gold", "platinum"]
    for i in range(20):
        uid = f"bandit_user_{i:03d}"
        level = user_levels[i % len(user_levels)]
        risk = random.choice(["high", "medium", "low"])
        prob = {"high": random.uniform(0.7, 0.99),
                "medium": random.uniform(0.4, 0.7),
                "low": random.uniform(0.01, 0.4)}[risk]

        profile = {
            "user_id": uid,
            "user_level": level,
            "total_spend": random.uniform(100, 10000),
            "region": random.choice(["north", "south", "east", "west"])
        }
        cache.store_user_profile(uid, profile)

        features = {
            "window_30d_total_events": random.randint(0, 100),
            "days_since_last_event": random.randint(0, 30),
            "event_frequency": random.uniform(0, 1.0),
            "window_30d_error_count": random.randint(0, 5)
        }
        cache.store_user_features(uid, features)

        risk_data = {
            "churn_probability": prob,
            "risk_level": risk,
            "expected_days_to_churn": random.randint(1, 30),
            "risk_score": prob * 1000
        }
        cache.store_risk_score(uid, risk_data)
        if risk == "high":
            cache.tag_high_risk_user(uid, risk_data)

        test_users.append(uid)

    print("\nRecommendations:")
    recommendations = engine.batch_recommend(test_users)
    for i, rec in enumerate(recommendations[:10]):
        print(f"\n  [{i+1}] User: {rec.user_id}")
        print(f"      Risk: {rec.risk_level.upper()} (prob={rec.churn_probability:.2%})")
        print(f"      Action: {rec.action_type} via {rec.channel}")
        print(f"      Strategy: {rec.strategy}, Exploration: {rec.exploration_flag}")
        print(f"      Confidence: {rec.confidence:.2f}, Expected Reward: {rec.expected_reward:.2f}")
        if rec.content:
            print(f"      Content: {rec.content.get('title', '')[:50]}...")

    print("\n" + "-" * 60)
    print("SIMULATING CONVERSIONS")
    print("-" * 60)

    for rec in recommendations:
        action_id = engine.execute_recommendation(rec)
        if action_id:
            converted = random.random() < (0.3 if rec.risk_level == "high" else 0.15)
            engine.record_result(rec.user_id, rec.arm_key, 1.0 if converted else 0.0, converted)

    print(f"\nSimulated conversions for {len(recommendations)} recommendations")

    print("\n" + "-" * 60)
    print("BANDIT PERFORMANCE SUMMARY")
    print("-" * 60)

    summary = engine.get_summary()
    print(f"\n  Strategy: {summary['strategy']}")
    print(f"  Total Impressions: {summary['total_impressions']}")
    print(f"  Total Conversions: {summary['total_conversions']}")
    print(f"  Overall Conversion Rate: {summary['overall_conversion_rate']:.2%}")
    print(f"  Trained Arms: {summary['trained_arms']}/{summary['total_arms']}")
    print(f"  Epsilon: {summary['epsilon']:.4f}")

    print("\n  Best Arms by Risk Level:")
    for risk_level, data in summary["best_arms_by_risk_level"].items():
        if data["best_arm"]:
            parts = data["best_arm"].split(":")
            print(f"    {risk_level.upper()}: {parts[1]} via {parts[2]} (avg reward: {data['best_reward']:.3f})")

    print("\n" + "=" * 60)


if __name__ == "__main__":
    main()