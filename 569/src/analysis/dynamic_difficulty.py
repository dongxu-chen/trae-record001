import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass, field
from collections import deque

from src.features.data_generator import SKILL_GROUPS, SKILL_GROUP_ORDER

FEATURE_RANGES = {
    'obstacle_density': (0.05, 0.45),
    'time_limit': (30, 180),
    'enemy_count': (0, 15),
    'platform_gap': (0.5, 3.0),
    'moving_obstacle_ratio': (0.0, 0.8),
    'powerup_count': (0, 5),
    'checkpoint_count': (0, 4),
    'level_length': (50, 300),
}

FEATURE_IMPACT = {
    'obstacle_density': {'direction': 1, 'weight': 0.20, 'chinese_name': '障碍密度'},
    'time_limit': {'direction': -1, 'weight': 0.15, 'chinese_name': '时间限制'},
    'enemy_count': {'direction': 1, 'weight': 0.18, 'chinese_name': '敌人数量'},
    'platform_gap': {'direction': 1, 'weight': 0.12, 'chinese_name': '平台间距'},
    'moving_obstacle_ratio': {'direction': 1, 'weight': 0.15, 'chinese_name': '移动障碍比例'},
    'powerup_count': {'direction': -1, 'weight': 0.08, 'chinese_name': '道具数量'},
    'checkpoint_count': {'direction': -1, 'weight': 0.07, 'chinese_name': '检查点数量'},
    'level_length': {'direction': 1, 'weight': 0.05, 'chinese_name': '关卡长度'},
}

ADJUSTABLE_FEATURES = ['obstacle_density', 'time_limit', 'enemy_count', 
                       'platform_gap', 'moving_obstacle_ratio', 'powerup_count', 
                       'checkpoint_count']


@dataclass
class PlayerPerformance:
    player_id: str
    skill_group: str
    completion_rate: float
    avg_attempts: float
    recent_attempts: List[int]
    recent_completions: List[bool]
    death_zones: Dict[str, int]
    play_duration: float
    timestamp: float
    
    def get_recent_trend(self, window: int = 5) -> Dict[str, float]:
        recent_comp = self.recent_completions[-window:]
        recent_att = self.recent_attempts[-window:]
        
        if len(recent_comp) < 2:
            return {'trend': 0, 'slope': 0, 'volatility': 0}
        
        x = np.arange(len(recent_comp))
        y_comp = np.array(recent_comp, dtype=float)
        y_att = np.array(recent_att, dtype=float)
        
        comp_slope = np.polyfit(x, y_comp, 1)[0] if len(x) > 1 else 0
        att_slope = np.polyfit(x, y_att, 1)[0] if len(x) > 1 else 0
        
        combined_slope = comp_slope * 0.6 - att_slope * 0.4
        volatility = np.std(y_comp) if len(y_comp) > 1 else 0
        
        trend = 0
        if combined_slope > 0.05:
            trend = 1
        elif combined_slope < -0.05:
            trend = -1
        
        return {
            'trend': trend,
            'slope': combined_slope,
            'volatility': volatility
        }


@dataclass
class DifficultyAdjustment:
    feature: str
    feature_name: str
    current_value: float
    suggested_value: float
    adjustment_percent: float
    action: str
    reason: str
    expected_impact: Dict[str, float]
    confidence: float


@dataclass
class DynamicAdjustmentResult:
    player_id: str
    skill_group: str
    current_params: Dict[str, float]
    adjusted_params: Dict[str, float]
    adjustments: List[DifficultyAdjustment]
    performance_summary: Dict[str, Any]
    target_metrics: Dict[str, float]
    expected_outcome: Dict[str, float]
    adjustment_strength: float
    risk_level: str


class DynamicDifficultyAdjuster:
    def __init__(
        self,
        target_completion_rate: float = 0.6,
        target_avg_attempts: float = 4.0,
        max_adjustment_percent: float = 0.25,
        history_window: int = 10,
        learning_rate: float = 0.3
    ):
        self.target_completion_rate = target_completion_rate
        self.target_avg_attempts = target_avg_attempts
        self.max_adjustment_percent = max_adjustment_percent
        self.history_window = history_window
        self.learning_rate = learning_rate
        
        self.adjustment_history: Dict[str, deque] = {}
        self.performance_history: Dict[str, deque] = {}
    
    def _init_player_history(self, player_id: str):
        if player_id not in self.adjustment_history:
            self.adjustment_history[player_id] = deque(maxlen=self.history_window)
        if player_id not in self.performance_history:
            self.performance_history[player_id] = deque(maxlen=self.history_window)
    
    def _calculate_gap(self, performance: PlayerPerformance) -> Dict[str, float]:
        completion_gap = self.target_completion_rate - performance.completion_rate
        attempts_gap = performance.avg_attempts - self.target_avg_attempts
        
        normalized_completion_gap = completion_gap / 0.5
        normalized_attempts_gap = attempts_gap / 8.0
        
        combined_gap = normalized_completion_gap * 0.6 + normalized_attempts_gap * 0.4
        
        trend = performance.get_recent_trend()
        trend_modifier = trend['slope'] * 0.5
        
        final_gap = combined_gap + trend_modifier
        final_gap = np.clip(final_gap, -1.0, 1.0)
        
        return {
            'completion_gap': completion_gap,
            'attempts_gap': attempts_gap,
            'normalized_gap': final_gap,
            'trend': trend
        }
    
    def _calculate_adjustment_strength(self, gap: Dict[str, float]) -> Tuple[float, str]:
        abs_gap = abs(gap['normalized_gap'])
        
        if abs_gap < 0.1:
            return 0.0, 'stable'
        elif abs_gap < 0.25:
            strength = 0.3
            risk_level = 'low'
        elif abs_gap < 0.5:
            strength = 0.6
            risk_level = 'medium'
        else:
            strength = 1.0
            risk_level = 'high'
        
        if gap['trend']['trend'] * np.sign(gap['normalized_gap']) > 0:
            strength *= 0.7
        
        if gap['trend']['volatility'] > 0.3:
            strength *= 0.8
        
        return strength * self.learning_rate, risk_level
    
    def _generate_adjustments(
        self,
        current_params: Dict[str, float],
        gap: Dict[str, float],
        strength: float,
        performance: PlayerPerformance
    ) -> List[DifficultyAdjustment]:
        adjustments = []
        direction = 'decrease' if gap['normalized_gap'] > 0 else 'increase'
        
        sorted_features = sorted(
            ADJUSTABLE_FEATURES,
            key=lambda f: FEATURE_IMPACT[f]['weight'],
            reverse=True
        )
        
        death_zones = performance.death_zones
        zone_priorities = {
            'obstacle_density': death_zones.get('obstacle_zone', 0) + death_zones.get('moving_zone', 0),
            'enemy_count': death_zones.get('enemy_zone', 0),
            'platform_gap': death_zones.get('platform_zone', 0),
            'time_limit': death_zones.get('time_zone', 0),
            'moving_obstacle_ratio': death_zones.get('moving_zone', 0),
            'powerup_count': 0,
            'checkpoint_count': 0,
        }
        
        for feature in sorted_features:
            current_value = current_params.get(feature, 0)
            if current_value is None:
                continue
            
            info = FEATURE_IMPACT[feature]
            min_val, max_val = FEATURE_RANGES[feature]
            
            zone_priority = zone_priorities.get(feature, 0)
            weight_modifier = 1.0 + zone_priority * 0.5
            
            base_adjust = self.max_adjustment_percent * strength * weight_modifier
            
            if (info['direction'] > 0 and direction == 'decrease') or \
               (info['direction'] < 0 and direction == 'increase'):
                adjust_percent = -base_adjust
                action = '减少'
            else:
                adjust_percent = base_adjust
                action = '增加'
            
            raw_new_value = current_value * (1 + adjust_percent)
            new_value = float(np.clip(raw_new_value, min_val, max_val))
            
            actual_adjust_percent = (new_value - current_value) / current_value if current_value != 0 else 0
            
            if abs(actual_adjust_percent) < 0.02:
                continue
            
            if zone_priority > 0.3:
                reason = f"玩家在{feature}相关区域死亡占比{zone_priority:.0%}，需针对性调整"
            elif gap['trend']['trend'] != 0:
                trend_desc = "上升" if gap['trend']['trend'] > 0 else "下降"
                reason = f"玩家表现呈{trend_desc}趋势，需动态调整难度"
            else:
                reason = f"当前通关率{performance.completion_rate:.1%}，目标{self.target_completion_rate:.0%}"
            
            expected_comp_change = actual_adjust_percent * info['direction'] * info['weight'] * 100
            expected_attempts_change = actual_adjust_percent * info['direction'] * info['weight'] * -3
            
            confidence = 0.5 + strength * 0.3 + min(zone_priority, 0.5) * 0.2
            
            adjustments.append(DifficultyAdjustment(
                feature=feature,
                feature_name=info['chinese_name'],
                current_value=current_value,
                suggested_value=new_value,
                adjustment_percent=abs(actual_adjust_percent) * 100,
                action=action,
                reason=reason,
                expected_impact={
                    'completion_rate_change': expected_comp_change,
                    'avg_attempts_change': expected_attempts_change
                },
                confidence=confidence
            ))
        
        return adjustments[:5]
    
    def adjust_difficulty(
        self,
        performance: PlayerPerformance,
        current_params: Dict[str, float]
    ) -> DynamicAdjustmentResult:
        self._init_player_history(performance.player_id)
        
        gap = self._calculate_gap(performance)
        strength, risk_level = self._calculate_adjustment_strength(gap)
        
        if strength < 0.05:
            adjusted_params = current_params.copy()
            adjustments = []
        else:
            adjustments = self._generate_adjustments(
                current_params, gap, strength, performance
            )
            
            adjusted_params = current_params.copy()
            for adj in adjustments:
                adjusted_params[adj.feature] = adj.suggested_value
        
        total_comp_change = sum(adj.expected_impact['completion_rate_change'] for adj in adjustments)
        total_att_change = sum(adj.expected_impact['avg_attempts_change'] for adj in adjustments)
        
        expected_outcome = {
            'new_completion_rate': np.clip(performance.completion_rate + total_comp_change / 100, 0.1, 0.95),
            'new_avg_attempts': max(1.0, performance.avg_attempts + total_att_change),
            'total_completion_change': total_comp_change,
            'total_attempts_change': total_att_change
        }
        
        result = DynamicAdjustmentResult(
            player_id=performance.player_id,
            skill_group=performance.skill_group,
            current_params=current_params.copy(),
            adjusted_params=adjusted_params,
            adjustments=adjustments,
            performance_summary={
                'current_completion_rate': performance.completion_rate,
                'current_avg_attempts': performance.avg_attempts,
                'gap': gap,
                'play_duration': performance.play_duration
            },
            target_metrics={
                'target_completion_rate': self.target_completion_rate,
                'target_avg_attempts': self.target_avg_attempts
            },
            expected_outcome=expected_outcome,
            adjustment_strength=strength,
            risk_level=risk_level
        )
        
        self.adjustment_history[performance.player_id].append(result)
        self.performance_history[performance.player_id].append(performance)
        
        return result
    
    def batch_adjust(
        self,
        performances: List[PlayerPerformance],
        current_params: Dict[str, float]
    ) -> Dict[str, DynamicAdjustmentResult]:
        results = {}
        for perf in performances:
            results[perf.player_id] = self.adjust_difficulty(perf, current_params)
        return results
    
    def simulate_adjustment_impact(
        self,
        performance: PlayerPerformance,
        current_params: Dict[str, float],
        n_simulations: int = 100
    ) -> Dict[str, Any]:
        base_result = self.adjust_difficulty(performance, current_params)
        
        if not base_result.adjustments:
            return {
                'mean_completion': performance.completion_rate,
                'lower_completion': performance.completion_rate,
                'upper_completion': performance.completion_rate,
                'mean_attempts': performance.avg_attempts,
                'lower_attempts': performance.avg_attempts,
                'upper_attempts': performance.avg_attempts,
                'success_probability': 1.0,
                'simulations': []
            }
        
        simulated_completions = []
        simulated_attempts = []
        
        base_change_comp = base_result.expected_outcome['total_completion_change'] / 100
        base_change_att = base_result.expected_outcome['total_attempts_change']
        
        for _ in range(n_simulations):
            noise_comp = np.random.normal(0, abs(base_change_comp) * 0.3)
            noise_att = np.random.normal(0, abs(base_change_att) * 0.3)
            
            new_comp = np.clip(performance.completion_rate + base_change_comp + noise_comp, 0.1, 0.95)
            new_att = max(1.0, performance.avg_attempts + base_change_att + noise_att)
            
            simulated_completions.append(new_comp)
            simulated_attempts.append(new_att)
        
        comp_mean = np.mean(simulated_completions)
        comp_lower = np.percentile(simulated_completions, 10)
        comp_upper = np.percentile(simulated_completions, 90)
        
        att_mean = np.mean(simulated_attempts)
        att_lower = np.percentile(simulated_attempts, 10)
        att_upper = np.percentile(simulated_attempts, 90)
        
        success_prob = sum(
            1 for c in simulated_completions 
            if abs(c - self.target_completion_rate) < abs(performance.completion_rate - self.target_completion_rate)
        ) / n_simulations
        
        return {
            'mean_completion': comp_mean,
            'lower_completion': comp_lower,
            'upper_completion': comp_upper,
            'mean_attempts': att_mean,
            'lower_attempts': att_lower,
            'upper_attempts': att_upper,
            'success_probability': success_prob,
            'simulations': list(zip(simulated_completions, simulated_attempts))
        }
