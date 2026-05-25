import math
import random
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any
from enum import Enum


class ExplorationStrategy(Enum):
    EPSILON_GREEDY = "epsilon_greedy"
    UCB = "ucb"
    THOMPSON_SAMPLING = "thompson_sampling"
    BOLTZMANN = "boltzmann"


@dataclass
class StrategyStats:
    name: str
    trials: int = 0
    successes: int = 0
    total_reward: float = 0.0
    squared_reward: float = 0.0
    last_used: float = 0.0
    estimated_value: float = 0.0
    confidence_bound: float = 0.0
    
    @property
    def success_rate(self) -> float:
        return self.successes / self.trials if self.trials > 0 else 0.0
    
    @property
    def mean_reward(self) -> float:
        return self.total_reward / self.trials if self.trials > 0 else 0.0
    
    @property
    def variance(self) -> float:
        if self.trials < 2:
            return 1.0
        mean = self.mean_reward
        return (self.squared_reward / self.trials) - mean * mean
    
    @property
    def std_dev(self) -> float:
        return math.sqrt(max(0.0, self.variance))


@dataclass
class BiddingStrategy:
    name: str
    bid_multiplier: float = 1.0
    frequency_penalty_weight: float = 1.0
    budget_pace_weight: float = 1.0
    ctr_weight: float = 1.0
    cvr_weight: float = 1.0
    floor_price_bonus: float = 0.0
    is_exploratory: bool = False


class ExplorationEngine:
    def __init__(
        self,
        strategy: ExplorationStrategy = ExplorationStrategy.UCB,
        epsilon: float = 0.1,
        epsilon_decay: float = 0.9995,
        min_epsilon: float = 0.01,
        ucb_c: float = 2.0,
        boltzmann_temperature: float = 1.0,
        min_trials_for_exploitation: int = 100,
        exploration_budget_share: float = 0.1,
        history_size: int = 10000,
    ):
        self.strategy = strategy
        self.epsilon = epsilon
        self.epsilon_decay = epsilon_decay
        self.min_epsilon = min_epsilon
        self.ucb_c = ucb_c
        self.boltzmann_temperature = boltzmann_temperature
        self.min_trials_for_exploitation = min_trials_for_exploitation
        self.exploration_budget_share = exploration_budget_share
        
        self.strategies: Dict[str, BiddingStrategy] = {}
        self.strategy_stats: Dict[str, StrategyStats] = {}
        
        self.total_trials = 0
        self.exploration_trials = 0
        self.exploitation_trials = 0
        
        self.reward_history = deque(maxlen=history_size)
        self.choice_history = deque(maxlen=history_size)
        
        self._initialize_default_strategies()
    
    def _initialize_default_strategies(self):
        default_strategies = [
            BiddingStrategy(
                name="conservative",
                bid_multiplier=0.8,
                frequency_penalty_weight=1.5,
                budget_pace_weight=1.2,
                is_exploratory=False,
            ),
            BiddingStrategy(
                name="balanced",
                bid_multiplier=1.0,
                frequency_penalty_weight=1.0,
                budget_pace_weight=1.0,
                is_exploratory=False,
            ),
            BiddingStrategy(
                name="aggressive",
                bid_multiplier=1.3,
                frequency_penalty_weight=0.7,
                budget_pace_weight=0.8,
                is_exploratory=False,
            ),
            BiddingStrategy(
                name="explore_high_ctr",
                bid_multiplier=1.0,
                ctr_weight=1.5,
                cvr_weight=0.8,
                is_exploratory=True,
            ),
            BiddingStrategy(
                name="explore_high_cvr",
                bid_multiplier=1.0,
                ctr_weight=0.8,
                cvr_weight=1.5,
                is_exploratory=True,
            ),
            BiddingStrategy(
                name="explore_low_freq",
                bid_multiplier=1.2,
                frequency_penalty_weight=0.3,
                is_exploratory=True,
            ),
            BiddingStrategy(
                name="explore_value_bid",
                bid_multiplier=0.9,
                floor_price_bonus=0.02,
                is_exploratory=True,
            ),
        ]
        
        for strategy in default_strategies:
            self.add_strategy(strategy)
    
    def add_strategy(self, strategy: BiddingStrategy):
        self.strategies[strategy.name] = strategy
        if strategy.name not in self.strategy_stats:
            self.strategy_stats[strategy.name] = StrategyStats(name=strategy.name)
    
    def get_available_strategies(self) -> List[str]:
        return list(self.strategies.keys())
    
    def get_exploration_rate(self) -> float:
        if self.total_trials < self.min_trials_for_exploitation:
            return max(self.epsilon, 0.3)
        return self.epsilon
    
    def should_explore(self) -> bool:
        current_epsilon = self.get_exploration_rate()
        return random.random() < current_epsilon
    
    def _select_strategy_epsilon_greedy(self) -> str:
        exploratory = [n for n, s in self.strategies.items() if s.is_exploratory]
        non_exploratory = [n for n, s in self.strategies.items() if not s.is_exploratory]
        
        if self.should_explore() and exploratory:
            return random.choice(exploratory)
        
        return self._get_best_strategy(non_exploratory)
    
    def _select_strategy_ucb(self) -> str:
        strategy_names = list(self.strategies.keys())
        ucb_values = {}
        
        for name in strategy_names:
            stats = self.strategy_stats[name]
            if stats.trials == 0:
                ucb_values[name] = float('inf')
            else:
                exploitation = stats.mean_reward
                exploration = self.ucb_c * math.sqrt(
                    2 * math.log(self.total_trials + 1) / stats.trials
                )
                bonus = 0.5 if self.strategies[name].is_exploratory else 0.0
                ucb_values[name] = exploitation + exploration + bonus
        
        return max(ucb_values.items(), key=lambda x: x[1])[0]
    
    def _select_strategy_thompson_sampling(self) -> str:
        samples = {}
        for name, stats in self.strategy_stats.items():
            alpha = stats.successes + 1
            beta = stats.trials - stats.successes + 1
            samples[name] = random.betavariate(alpha, beta)
        
        return max(samples.items(), key=lambda x: x[1])[0]
    
    def _select_strategy_boltzmann(self) -> str:
        strategy_names = list(self.strategies.keys())
        values = []
        
        for name in strategy_names:
            stats = self.strategy_stats[name]
            if stats.trials == 0:
                values.append(1.0)
            else:
                values.append(stats.mean_reward / self.boltzmann_temperature)
        
        max_val = max(values)
        exp_values = [math.exp(v - max_val) for v in values]
        sum_exp = sum(exp_values)
        probabilities = [e / sum_exp for e in exp_values]
        
        return random.choices(strategy_names, weights=probabilities, k=1)[0]
    
    def _get_best_strategy(self, candidates: Optional[List[str]] = None) -> str:
        if candidates is None:
            candidates = list(self.strategies.keys())
        
        best_strategy = None
        best_value = -float('inf')
        
        for name in candidates:
            stats = self.strategy_stats[name]
            value = stats.mean_reward if stats.trials > 0 else 0.0
            if value > best_value:
                best_value = value
                best_strategy = name
        
        return best_strategy or "balanced"
    
    def select_strategy(
        self,
        context: Optional[Dict[str, Any]] = None,
    ) -> Tuple[str, BiddingStrategy, Dict[str, Any]]:
        if self.strategy == ExplorationStrategy.EPSILON_GREEDY:
            selected_name = self._select_strategy_epsilon_greedy()
        elif self.strategy == ExplorationStrategy.UCB:
            selected_name = self._select_strategy_ucb()
        elif self.strategy == ExplorationStrategy.THOMPSON_SAMPLING:
            selected_name = self._select_strategy_thompson_sampling()
        elif self.strategy == ExplorationStrategy.BOLTZMANN:
            selected_name = self._select_strategy_boltzmann()
        else:
            selected_name = self._select_strategy_epsilon_greedy()
        
        strategy = self.strategies[selected_name]
        is_exploration = strategy.is_exploratory or (
            self.strategy == ExplorationStrategy.EPSILON_GREEDY and self.should_explore()
        )
        
        if is_exploration:
            self.exploration_trials += 1
        else:
            self.exploitation_trials += 1
        
        self.total_trials += 1
        self.epsilon = max(self.min_epsilon, self.epsilon * self.epsilon_decay)
        
        details = {
            "strategy_name": selected_name,
            "is_exploration": is_exploration,
            "exploration_rate": self.get_exploration_rate(),
            "total_trials": self.total_trials,
            "exploration_trials": self.exploration_trials,
            "exploitation_trials": self.exploitation_trials,
            "strategy_stats": {
                "trials": self.strategy_stats[selected_name].trials,
                "mean_reward": self.strategy_stats[selected_name].mean_reward,
                "success_rate": self.strategy_stats[selected_name].success_rate,
            },
        }
        
        self.choice_history.append({
            "time": time.time(),
            "strategy": selected_name,
            "is_exploration": is_exploration,
            "context": context or {},
        })
        
        return selected_name, strategy, details
    
    def apply_strategy_to_bid(
        self,
        base_bid: float,
        strategy: BiddingStrategy,
        ctr: float,
        cvr: float,
        frequency_penalty: float = 1.0,
        budget_pace: float = 1.0,
        floor_price: float = 0.0,
    ) -> float:
        weighted_ctr = ctr ** strategy.ctr_weight
        weighted_cvr = cvr ** strategy.cvr_weight
        
        adjusted_bid = base_bid * strategy.bid_multiplier
        adjusted_bid = adjusted_bid * (weighted_ctr + weighted_cvr) / (ctr + cvr + 1e-10)
        adjusted_bid = adjusted_bid * (frequency_penalty ** strategy.frequency_penalty_weight)
        adjusted_bid = adjusted_bid * (budget_pace ** strategy.budget_pace_weight)
        adjusted_bid += strategy.floor_price_bonus
        
        return max(floor_price, adjusted_bid)
    
    def record_result(
        self,
        strategy_name: str,
        reward: float,
        success: bool = True,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        if strategy_name not in self.strategy_stats:
            return
        
        stats = self.strategy_stats[strategy_name]
        stats.trials += 1
        if success:
            stats.successes += 1
        stats.total_reward += reward
        stats.squared_reward += reward * reward
        stats.last_used = time.time()
        stats.estimated_value = stats.mean_reward
        
        self.reward_history.append({
            "time": time.time(),
            "strategy": strategy_name,
            "reward": reward,
            "success": success,
            "metadata": metadata or {},
        })
    
    def get_strategy_summary(self) -> Dict[str, Any]:
        summary = {
            "total_trials": self.total_trials,
            "exploration_trials": self.exploration_trials,
            "exploitation_trials": self.exploitation_trials,
            "current_epsilon": self.epsilon,
            "exploration_rate": self.get_exploration_rate(),
            "strategy": self.strategy.value,
            "best_strategy": self._get_best_strategy(),
            "strategies": {},
        }
        
        for name, stats in self.strategy_stats.items():
            summary["strategies"][name] = {
                "trials": stats.trials,
                "successes": stats.successes,
                "success_rate": stats.success_rate,
                "mean_reward": stats.mean_reward,
                "std_dev": stats.std_dev,
                "is_exploratory": self.strategies[name].is_exploratory,
                "bid_multiplier": self.strategies[name].bid_multiplier,
            }
        
        return summary
    
    def get_top_strategies(self, top_n: int = 3) -> List[Tuple[str, float]]:
        ranked = sorted(
            self.strategy_stats.items(),
            key=lambda x: x[1].mean_reward if x[1].trials > 0 else -1,
            reverse=True,
        )
        return [(name, stats.mean_reward) for name, stats in ranked[:top_n]]
    
    def get_exploration_heatmap(self) -> Dict[str, int]:
        heatmap = defaultdict(int)
        for record in self.choice_history:
            heatmap[record["strategy"]] += 1
        return dict(heatmap)
    
    def reset(self):
        for name in self.strategy_stats:
            self.strategy_stats[name] = StrategyStats(name=name)
        
        self.total_trials = 0
        self.exploration_trials = 0
        self.exploitation_trials = 0
        self.reward_history.clear()
        self.choice_history.clear()
    
    def save_state(self) -> Dict[str, Any]:
        return {
            "strategy": self.strategy.value,
            "epsilon": self.epsilon,
            "total_trials": self.total_trials,
            "exploration_trials": self.exploration_trials,
            "exploitation_trials": self.exploitation_trials,
            "strategies": {
                name: {
                    "trials": stats.trials,
                    "successes": stats.successes,
                    "total_reward": stats.total_reward,
                    "squared_reward": stats.squared_reward,
                }
                for name, stats in self.strategy_stats.items()
            },
        }
    
    def load_state(self, state: Dict[str, Any]):
        self.strategy = ExplorationStrategy(state.get("strategy", "ucb"))
        self.epsilon = state.get("epsilon", self.epsilon)
        self.total_trials = state.get("total_trials", 0)
        self.exploration_trials = state.get("exploration_trials", 0)
        self.exploitation_trials = state.get("exploitation_trials", 0)
        
        for name, stats_data in state.get("strategies", {}).items():
            if name in self.strategy_stats:
                stats = self.strategy_stats[name]
                stats.trials = stats_data.get("trials", 0)
                stats.successes = stats_data.get("successes", 0)
                stats.total_reward = stats_data.get("total_reward", 0.0)
                stats.squared_reward = stats_data.get("squared_reward", 0.0)
