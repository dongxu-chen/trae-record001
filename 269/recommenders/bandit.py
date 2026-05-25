import random
import numpy as np
from typing import List, Dict, Tuple, Optional
from collections import defaultdict
from config import settings


class EpsilonGreedyBandit:
    def __init__(self, epsilon: float = None):
        self.epsilon = epsilon or settings.BANDIT_EPSILON
        self.arm_stats: Dict[str, Dict[str, float]] = defaultdict(lambda: {"count": 0, "sum": 0.0})
    
    def select_arm(self, arms: List[str], exploit_scores: Optional[Dict[str, float]] = None) -> str:
        if random.random() < self.epsilon:
            return random.choice(arms)
        else:
            if exploit_scores:
                return max(arms, key=lambda x: exploit_scores.get(x, 0))
            else:
                def _get_score(arm):
                    stats = self.arm_stats[arm]
                    if stats["count"] == 0:
                        return 2.5
                    return stats["sum"] / stats["count"]
                return max(arms, key=_get_score)
    
    def select_arms(self, arms: List[str], n: int, 
                    exploit_scores: Optional[Dict[str, float]] = None) -> List[str]:
        selected = []
        available_arms = list(arms)
        
        for _ in range(min(n, len(arms))):
            if not available_arms:
                break
            chosen = self.select_arm(available_arms, exploit_scores)
            selected.append(chosen)
            available_arms.remove(chosen)
            
            if exploit_scores:
                exploit_scores.pop(chosen, None)
        
        return selected
    
    def update(self, arm: str, reward: float):
        self.arm_stats[arm]["count"] += 1
        self.arm_stats[arm]["sum"] += reward
    
    def get_arm_stats(self, arm: str) -> Dict[str, float]:
        stats = self.arm_stats[arm]
        return {
            "count": stats["count"],
            "average_reward": stats["sum"] / stats["count"] if stats["count"] > 0 else 0
        }


class ThompsonSamplingBandit:
    def __init__(self, alpha: float = None, beta: float = None):
        self.alpha = alpha or settings.BANDIT_ALPHA
        self.beta = beta or settings.BANDIT_BETA
        self.arm_stats: Dict[str, Dict[str, int]] = defaultdict(lambda: {"successes": 0, "failures": 0})
    
    def select_arm(self, arms: List[str]) -> str:
        samples = {}
        for arm in arms:
            stats = self.arm_stats[arm]
            samples[arm] = np.random.beta(
                self.alpha + stats["successes"],
                self.beta + stats["failures"]
            )
        return max(arms, key=lambda x: samples[x])
    
    def select_arms(self, arms: List[str], n: int) -> List[str]:
        selected = []
        available_arms = list(arms)
        
        for _ in range(min(n, len(arms))):
            if not available_arms:
                break
            chosen = self.select_arm(available_arms)
            selected.append(chosen)
            available_arms.remove(chosen)
        
        return selected
    
    def update(self, arm: str, success: bool):
        if success:
            self.arm_stats[arm]["successes"] += 1
        else:
            self.arm_stats[arm]["failures"] += 1
    
    def update_with_reward(self, arm: str, reward: float):
        if reward >= 3.5:
            self.update(arm, True)
        else:
            self.update(arm, False)
    
    def get_arm_stats(self, arm: str) -> Dict[str, float]:
        stats = self.arm_stats[arm]
        total = stats["successes"] + stats["failures"]
        return {
            "successes": stats["successes"],
            "failures": stats["failures"],
            "success_rate": stats["successes"] / total if total > 0 else 0
        }


class UCBBandit:
    def __init__(self, c: float = 2.0):
        self.c = c
        self.arm_stats: Dict[str, Dict[str, float]] = defaultdict(lambda: {"count": 0, "sum": 0.0})
        self.total_counts = 0
    
    def select_arm(self, arms: List[str]) -> str:
        ucb_values = {}
        for arm in arms:
            stats = self.arm_stats[arm]
            if stats["count"] == 0:
                return arm
            
            avg_reward = stats["sum"] / stats["count"]
            exploration = self.c * np.sqrt(np.log(self.total_counts) / stats["count"])
            ucb_values[arm] = avg_reward + exploration
        
        return max(arms, key=lambda x: ucb_values[x])
    
    def select_arms(self, arms: List[str], n: int) -> List[str]:
        selected = []
        available_arms = list(arms)
        
        for _ in range(min(n, len(arms))):
            if not available_arms:
                break
            chosen = self.select_arm(available_arms)
            selected.append(chosen)
            available_arms.remove(chosen)
        
        return selected
    
    def update(self, arm: str, reward: float):
        self.arm_stats[arm]["count"] += 1
        self.arm_stats[arm]["sum"] += reward
        self.total_counts += 1
    
    def get_arm_stats(self, arm: str) -> Dict[str, float]:
        stats = self.arm_stats[arm]
        return {
            "count": stats["count"],
            "average_reward": stats["sum"] / stats["count"] if stats["count"] > 0 else 0
        }


class ContextualBandit:
    def __init__(self, num_features: int, learning_rate: float = 0.1):
        self.num_features = num_features
        self.learning_rate = learning_rate
        self.weights: Dict[str, np.ndarray] = {}
    
    def _get_features(self, context: Dict) -> np.ndarray:
        features = np.zeros(self.num_features)
        for i, key in enumerate(sorted(context.keys())):
            if i < self.num_features:
                features[i] = float(context[key]) if isinstance(context[key], (int, float)) else 0.0
        return features
    
    def predict(self, arm: str, context: Dict) -> float:
        if arm not in self.weights:
            self.weights[arm] = np.zeros(self.num_features)
        
        features = self._get_features(context)
        return np.dot(self.weights[arm], features)
    
    def select_arm(self, arms: List[str], context: Dict, epsilon: float = 0.1) -> str:
        if random.random() < epsilon:
            return random.choice(arms)
        else:
            return max(arms, key=lambda x: self.predict(x, context))
    
    def update(self, arm: str, context: Dict, reward: float):
        if arm not in self.weights:
            self.weights[arm] = np.zeros(self.num_features)
        
        features = self._get_features(context)
        prediction = np.dot(self.weights[arm], features)
        error = reward - prediction
        self.weights[arm] += self.learning_rate * error * features
