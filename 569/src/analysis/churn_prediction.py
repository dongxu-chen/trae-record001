import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass, field
from collections import deque
import warnings
warnings.filterwarnings('ignore')

from src.features.data_generator import SKILL_GROUPS, SKILL_GROUP_ORDER


@dataclass
class PlayerBehaviorData:
    player_id: str
    skill_group: str
    level_id: str
    completion_rate: float
    avg_attempts: float
    play_duration: float
    recent_completions: List[bool]
    recent_attempts: List[int]
    death_zones: Dict[str, int]
    frustration_events: int
    consecutive_failures: int
    rage_quits: int
    session_count: int
    days_since_last_play: int
    total_play_time: float
    level_difficulty: float
    timestamp: float


@dataclass
class ChurnRiskFactors:
    difficulty_stress: float
    frustration_risk: float
    boredom_risk: float
    behavior_risk: float
    engagement_risk: float
    skill_progress_risk: float
    overall_risk: float
    
    def get_dominant_factors(self, threshold: float = 0.6) -> List[Tuple[str, float, str]]:
        factor_names = {
            'difficulty_stress': ('难度压力', '关卡难度过高导致玩家压力过大'),
            'frustration_risk': ('挫败风险', '频繁失败产生挫败感'),
            'boredom_risk': ('厌倦风险', '关卡过于简单导致无聊'),
            'behavior_risk': ('行为风险', '愤怒退出、连续失败等行为信号'),
            'engagement_risk': ('参与风险', '游戏频率和时长下降'),
            'skill_progress_risk': ('技能进展风险', '技能提升停滞'),
        }
        
        dominant = []
        for key, (name, desc) in factor_names.items():
            value = getattr(self, key)
            if value >= threshold:
                dominant.append((name, value, desc))
        
        dominant.sort(key=lambda x: x[1], reverse=True)
        return dominant


@dataclass
class ChurnWarning:
    level: str
    message: str
    risk_score: float
    suggested_action: str
    affected_group: str
    urgency: str


@dataclass
class ChurnPredictionResult:
    player_id: str
    skill_group: str
    churn_risk: float
    churn_probability: float
    risk_level: str
    risk_factors: ChurnRiskFactors
    warnings: List[ChurnWarning]
    retention_strategy: Dict[str, Any]
    intervention_priority: int
    expected_retention_impact: float
    feature_contributions: Dict[str, float]


class ChurnPredictor:
    def __init__(
        self,
        high_risk_threshold: float = 0.7,
        medium_risk_threshold: float = 0.4,
        history_window: int = 20
    ):
        self.high_risk_threshold = high_risk_threshold
        self.medium_risk_threshold = medium_risk_threshold
        self.history_window = history_window
        
        self.prediction_history: Dict[str, deque] = {}
        self.intervention_effectiveness: Dict[str, List[Dict[str, Any]]] = {}
    
    def _calculate_difficulty_stress(
        self, data: PlayerBehaviorData) -> float:
        difficulty = data.level_difficulty
        completion = data.completion_rate
        attempts = data.avg_attempts
        
        difficulty_factor = difficulty
        completion_penalty = max(0, 0.6 - completion) * 1.2
        attempts_penalty = max(0, attempts - 4.0) / 10.0
        
        stress = (
            difficulty_factor * 0.4 +
            completion_penalty * 0.4 +
            attempts_penalty * 0.2
        )
        
        if difficulty > 0.7 and completion < 0.3:
            stress = min(1.0, stress + 0.2)
        
        return np.clip(stress, 0, 1)
    
    def _calculate_frustration_risk(
        self, data: PlayerBehaviorData) -> float:
        total_deaths = sum(data.death_zones.values()) if data.death_zones else 0
        death_concentration = (
            max(data.death_zones.values()) / (total_deaths + 0.001)
            if total_deaths > 0 else 0
        )
        
        frustration_index = (
            data.frustration_events / max(1, data.session_count) * 0.3 +
            data.consecutive_failures / max(1, data.session_count) * 0.3 +
            death_concentration * 0.2 +
            min(1.0, data.rage_quits / max(1, data.session_count)) * 0.2
        )
        
        if data.consecutive_failures >= 3:
            frustration_index = min(1.0, frustration_index + 0.2)
        
        return np.clip(frustration_index, 0, 1)
    
    def _calculate_boredom_risk(
        self, data: PlayerBehaviorData) -> float:
        if data.level_difficulty < 0.3 and data.completion_rate > 0.8:
            boredom = (
                (0.8 - data.level_difficulty) * 0.5 +
                (data.completion_rate - 0.8) * 0.5
            )
        else:
            boredom = 0.0
        
        if data.avg_attempts < 1.5 and data.completion_rate > 0.9:
            boredom = min(1.0, boredom + 0.2)
        
        return np.clip(boredom, 0, 1)
    
    def _calculate_behavior_risk(
        self, data: PlayerBehaviorData) -> float:
        if data.rage_quits > 0:
            rage_factor = min(1.0, data.rage_quits / max(1, data.session_count) * 1.5)
        else:
            rage_factor = 0.0
        
        if data.consecutive_failures > 0:
            consecutive_factor = min(1.0, data.consecutive_failures / 5.0)
        else:
            consecutive_factor = 0.0
        
        if len(data.recent_completions) >= 5:
            recent_comp = data.recent_completions[-5:]
            failure_streak = 0
            for c in reversed(recent_comp):
                if not c:
                    failure_streak += 1
                else:
                    break
            streak_factor = min(1.0, failure_streak / 5.0)
        else:
            streak_factor = 0.0
        
        behavior_risk = (
            rage_factor * 0.5 +
            consecutive_factor * 0.3 +
            streak_factor * 0.2
        )
        
        return np.clip(behavior_risk, 0, 1)
    
    def _calculate_engagement_risk(
        self, data: PlayerBehaviorData) -> float:
        recency_factor = min(1.0, data.days_since_last_play / 14.0)
        
        if data.total_play_time > 0:
            duration_factor = max(0, 1.0 - data.play_duration / 60.0)
        else:
            duration_factor = 0.5
        
        if len(data.recent_completions) >= 3:
            recent = data.recent_completions[-3:]
            frequency_factor = 1.0 - (sum(recent) / len(recent))
        else:
            frequency_factor = 0.0
        
        engagement_risk = (
            recency_factor * 0.5 +
            duration_factor * 0.3 +
            frequency_factor * 0.2
        )
        
        return np.clip(engagement_risk, 0, 1)
    
    def _calculate_skill_progress_risk(
        self, data: PlayerBehaviorData) -> float:
        if len(data.recent_completions) < 6:
            return 0.0
        
        first_half = data.recent_completions[:len(data.recent_completions)//2]
        second_half = data.recent_completions[len(data.recent_completions)//2:]
        
        first_rate = sum(first_half) / len(first_half)
        second_rate = sum(second_half) / len(second_half)
        
        improvement = second_rate - first_rate
        
        if improvement < -0.1:
            progress_risk = min(1.0, -improvement * 2)
        elif improvement < 0:
            progress_risk = min(1.0, -improvement)
        else:
            progress_risk = 0.0
        
        attempts_trend = 0
        if len(data.recent_attempts) >= 6:
            first_att = data.recent_attempts[:len(data.recent_attempts)//2]
            second_att = data.recent_attempts[len(data.recent_attempts)//2:]
            
            if np.mean(second_att) > np.mean(first_att) * 1.2:
                attempts_trend = 0.3
        
        return np.clip(progress_risk + attempts_trend, 0, 1)
    
    def _calculate_overall_risk(
        self, factors: ChurnRiskFactors) -> float:
        weights = {
            'difficulty_stress': 0.25,
            'frustration_risk': 0.25,
            'behavior_risk': 0.20,
            'engagement_risk': 0.15,
            'skill_progress_risk': 0.10,
            'boredom_risk': 0.05,
        }
        
        overall = (
            factors.difficulty_stress * weights['difficulty_stress'] +
            factors.frustration_risk * weights['frustration_risk'] +
            factors.behavior_risk * weights['behavior_risk'] +
            factors.engagement_risk * weights['engagement_risk'] +
            factors.skill_progress_risk * weights['skill_progress_risk'] +
            factors.boredom_risk * weights['boredom_risk']
        )
        
        high_factors = [
            factors.difficulty_stress,
            factors.frustration_risk,
            factors.behavior_risk,
        ]
        if any(f > 0.8 for f in high_factors):
            overall = min(1.0, overall + 0.1)
        
        if all(f < 0.2 for f in [
            factors.difficulty_stress,
            factors.frustration_risk,
            factors.behavior_risk,
        ]):
            overall = max(0.0, overall - 0.1)
        
        return np.clip(overall, 0, 1)
    
    def _get_risk_level(self, risk: float) -> str:
        if risk >= self.high_risk_threshold:
            return 'high'
        elif risk >= self.medium_risk_threshold:
            return 'medium'
        else:
            return 'low'
    
    def _generate_warnings(
        self,
        data: PlayerBehaviorData,
        factors: ChurnRiskFactors,
        risk_level: str
    ) -> List[ChurnWarning]:
        warnings = []
        
        if factors.difficulty_stress > 0.7:
            warnings.append(ChurnWarning(
                level='critical' if factors.difficulty_stress > 0.85 else 'warning',
                message=f"难度压力过高，玩家可能因难度过大产生挫败感",
                risk_score=factors.difficulty_stress,
                suggested_action="降低关卡难度或增加辅助道具",
                affected_group=data.skill_group,
                urgency='high'
            ))
        
        if factors.frustration_risk > 0.7:
            warnings.append(ChurnWarning(
                level='critical' if factors.frustration_risk > 0.85 else 'warning',
                message=f"挫败指数过高，玩家频繁失败",
                risk_score=factors.frustration_risk,
                suggested_action="增加检查点或降低失败惩罚",
                affected_group=data.skill_group,
                urgency='high'
            ))
        
        if factors.behavior_risk > 0.6:
            if data.rage_quits > 0:
                warnings.append(ChurnWarning(
                    level='critical',
                    message=f"检测到愤怒退出行为，玩家情绪失控",
                    risk_score=factors.behavior_risk,
                    suggested_action="立即调整难度或提供情绪调节机制",
                    affected_group=data.skill_group,
                    urgency='immediate'
                ))
        
        if factors.boredom_risk > 0.6:
            warnings.append(ChurnWarning(
                level='warning',
                message=f"关卡过于简单，玩家可能感到无聊",
                risk_score=factors.boredom_risk,
                suggested_action="提高关卡难度或增加挑战元素",
                affected_group=data.skill_group,
                urgency='medium'
            ))
        
        if factors.engagement_risk > 0.6:
            if data.days_since_last_play > 7:
                warnings.append(ChurnWarning(
                    level='warning',
                    message=f"玩家已7天未登录，存在流失风险",
                    risk_score=factors.engagement_risk,
                    suggested_action="发送召回活动或个性化推荐",
                    affected_group=data.skill_group,
                    urgency='medium'
                ))
        
        if factors.skill_progress_risk > 0.6:
            warnings.append(ChurnWarning(
                level='warning',
                message=f"玩家技能进展停滞，可能失去兴趣",
                risk_score=factors.skill_progress_risk,
                suggested_action="提供技能训练或新玩法引导",
                affected_group=data.skill_group,
                urgency='medium'
            ))
        
        if risk_level == 'high' and not warnings:
            warnings.append(ChurnWarning(
                level='warning',
                message="综合流失风险较高",
                risk_score=factors.overall_risk,
                suggested_action="综合评估并调整游戏体验",
                affected_group=data.skill_group,
                urgency='high'
            ))
        
        return warnings
    
    def _generate_retention_strategy(
        self,
        data: PlayerBehaviorData,
        factors: ChurnRiskFactors,
        risk_level: str
    ) -> Dict[str, Any]:
        strategy = {
            'immediate_actions': [],
            'short_term_actions': [],
            'long_term_actions': [],
            'personalized_suggestions': [],
            'estimated_success_probability': 0.0,
        }
        
        dominant = factors.get_dominant_factors(0.5)
        
        for name, value, desc in dominant[:3]:
            if '难度' in name or '挫败' in name:
                strategy['immediate_actions'].append({
                    'action': '动态难度调整',
                    'target': '降低关卡难度15-25%',
                    'expected_impact': '预计降低流失风险20-30%',
                    'priority': 'high'
                })
                strategy['personalized_suggestions'].append(
                    f"针对{name}问题，建议在玩家下次游戏时动态降低相关参数"
                )
            elif '行为' in name or '愤怒' in desc:
                strategy['immediate_actions'].append({
                    'action': '情绪安抚机制',
                    'target': '增加失败缓冲和鼓励提示',
                    'expected_impact': '预计降低流失风险15-25%',
                    'priority': 'high'
                })
            elif '参与' in name or '登录' in desc:
                strategy['short_term_actions'].append({
                    'action': '召回活动',
                    'target': '发送个性化推荐和奖励',
                    'expected_impact': '预计召回成功率30-40%',
                    'priority': 'medium'
                })
            elif '无聊' in name:
                strategy['short_term_actions'].append({
                    'action': '增加挑战',
                    'target': '提高难度或新增挑战模式',
                    'expected_impact': '预计提高参与度20-30%',
                    'priority': 'medium'
                })
            elif '进展' in name or '技能' in name:
                strategy['long_term_actions'].append({
                    'action': '技能引导',
                    'target': '提供技能训练和成长反馈',
                    'expected_impact': '预计提高留存率15-20%',
                    'priority': 'medium'
                })
        
        if risk_level == 'high':
            strategy['immediate_actions'].append({
                'action': '紧急干预',
                'target': '暂停难度自动下调',
                'expected_impact': '紧急降低流失风险',
                'priority': 'critical'
            })
        
        if len(strategy['immediate_actions']) > 0:
            strategy['estimated_success_probability'] = 0.7
        elif len(strategy['short_term_actions']) > 0:
            strategy['estimated_success_probability'] = 0.5
        else:
            strategy['estimated_success_probability'] = 0.3
        
        return strategy
    
    def _calculate_feature_contributions(
        self,
        data: PlayerBehaviorData,
        factors: ChurnRiskFactors
    ) -> Dict[str, float]:
        return {
            '难度压力': factors.difficulty_stress,
            '挫败风险': factors.frustration_risk,
            '厌倦风险': factors.boredom_risk,
            '行为风险': factors.behavior_risk,
            '参与风险': factors.engagement_risk,
            '技能进展风险': factors.skill_progress_risk,
        }
    
    def predict_churn(
        self,
        data: PlayerBehaviorData
    ) -> ChurnPredictionResult:
        difficulty_stress = self._calculate_difficulty_stress(data)
        frustration_risk = self._calculate_frustration_risk(data)
        boredom_risk = self._calculate_boredom_risk(data)
        behavior_risk = self._calculate_behavior_risk(data)
        engagement_risk = self._calculate_engagement_risk(data)
        skill_progress_risk = self._calculate_skill_progress_risk(data)
        
        factors = ChurnRiskFactors(
            difficulty_stress=difficulty_stress,
            frustration_risk=frustration_risk,
            boredom_risk=boredom_risk,
            behavior_risk=behavior_risk,
            engagement_risk=engagement_risk,
            skill_progress_risk=skill_progress_risk,
            overall_risk=0.0
        )
        
        overall_risk = self._calculate_overall_risk(factors)
        factors.overall_risk = overall_risk
        
        risk_level = self._get_risk_level(overall_risk)
        
        warnings = self._generate_warnings(data, factors, risk_level)
        strategy = self._generate_retention_strategy(data, factors, risk_level)
        contributions = self._calculate_feature_contributions(data, factors)
        
        if risk_level == 'high':
            priority = 1
        elif risk_level == 'medium':
            priority = 2
        else:
            priority = 3
        
        expected_impact = strategy['estimated_success_probability']
        
        result = ChurnPredictionResult(
            player_id=data.player_id,
            skill_group=data.skill_group,
            churn_risk=overall_risk,
            churn_probability=overall_risk,
            risk_level=risk_level,
            risk_factors=factors,
            warnings=warnings,
            retention_strategy=strategy,
            intervention_priority=priority,
            expected_retention_impact=expected_impact,
            feature_contributions=contributions
        )
        
        if data.player_id not in self.prediction_history:
            self.prediction_history[data.player_id] = deque(maxlen=self.history_window)
        self.prediction_history[data.player_id].append(result)
        
        return result
    
    def batch_predict(
        self,
        players_data: List[PlayerBehaviorData]
    ) -> List[ChurnPredictionResult]:
        results = []
        for data in players_data:
            results.append(self.predict_churn(data))
        return results
    
    def identify_at_risk_players(
        self,
        players_data: List[PlayerBehaviorData],
        min_risk_level: str = 'medium'
    ) -> List[ChurnPredictionResult]:
        results = self.batch_predict(players_data)
        
        risk_order = {'low': 0, 'medium': 1, 'high': 2}
        min_level = risk_order.get(min_risk_level, 1)
        
        at_risk = [
            r for r in results 
            if risk_order.get(r.risk_level, 0) >= min_level
        ]
        
        at_risk.sort(key=lambda x: (-x.churn_risk, x.intervention_priority))
        
        return at_risk
    
    def simulate_intervention_impact(
        self,
        data: PlayerBehaviorData,
        intervention_type: str,
        n_simulations: int = 100
    ) -> Dict[str, Any]:
        base_result = self.predict_churn(data)
        base_risk = base_result.churn_risk
        
        simulated_risks = []
        
        for _ in range(n_simulations):
            modified_data = PlayerBehaviorData(
                player_id=data.player_id,
                skill_group=data.skill_group,
                level_id=data.level_id,
                completion_rate=np.clip(data.completion_rate + np.random.uniform(0, 0.2), 0, 1),
                avg_attempts=max(1, data.avg_attempts * np.random.uniform(0.6, 1.0)),
                play_duration=data.play_duration,
                recent_completions=data.recent_completions,
                recent_attempts=data.recent_attempts,
                death_zones=data.death_zones,
                frustration_events=max(0, data.frustration_events - np.random.randint(0, 3)),
                consecutive_failures=max(0, data.consecutive_failures - np.random.randint(0, 2)),
                rage_quits=max(0, data.rage_quits - np.random.randint(0, 1)),
                session_count=data.session_count,
                days_since_last_play=max(0, data.days_since_last_play - np.random.randint(0, 3)),
                total_play_time=data.total_play_time,
                level_difficulty=np.clip(data.level_difficulty * np.random.uniform(0.7, 1.0), 0, 1),
                timestamp=data.timestamp
            )
            
            new_result = self.predict_churn(modified_data)
            simulated_risks.append(new_result.churn_risk)
        
        mean_new_risk = np.mean(simulated_risks)
        risk_reduction = base_risk - mean_new_risk
        success_probability = sum(1 for r in simulated_risks if r < base_risk) / n_simulations
        
        intervention_effect = {
            'base_risk': base_risk,
            'mean_new_risk': mean_new_risk,
            'risk_reduction': risk_reduction,
            'risk_reduction_percent': (risk_reduction / base_risk * 100 if base_risk > 0 else 0),
            'success_probability': success_probability,
            'lower_bound': np.percentile(simulated_risks, 10),
            'upper_bound': np.percentile(simulated_risks, 90),
            'simulations': simulated_risks,
        }
        
        return intervention_effect
    
    def get_risk_distribution(
        self,
        results: List[ChurnPredictionResult]
    ) -> Dict[str, Any]:
        total = len(results)
        high_risk = sum(1 for r in results if r.risk_level == 'high')
        medium_risk = sum(1 for r in results if r.risk_level == 'medium')
        low_risk = sum(1 for r in results if r.risk_level == 'low')
        
        by_group = {}
        for group in SKILL_GROUP_ORDER:
            group_results = [r for r in results if r.skill_group == group]
            if group_results:
                by_group[SKILL_GROUPS[group]['name']] = {
                    'total': len(group_results),
                    'high_risk': sum(1 for r in group_results if r.risk_level == 'high'),
                    'medium_risk': sum(1 for r in group_results if r.risk_level == 'medium'),
                    'low_risk': sum(1 for r in group_results if r.risk_level == 'low'),
                    'avg_risk': np.mean([r.churn_risk for r in group_results]),
                }
        
        top_warnings = {}
        all_warnings = []
        for r in results:
            all_warnings.extend(r.warnings)
        for w in all_warnings[:10]:
            key = w.message
            if key in top_warnings:
                top_warnings[key] = top_warnings.get(key, 0) + 1
            else:
                top_warnings[key] = 1
        
        sorted_warnings = sorted(top_warnings.items(), key=lambda x: x[1], reverse=True)
        
        return {
            'total_players': total,
            'high_risk_count': high_risk,
            'medium_risk_count': medium_risk,
            'low_risk_count': low_risk,
            'high_risk_percent': high_risk / total * 100 if total > 0 else 0,
            'medium_risk_percent': medium_risk / total * 100 if total > 0 else 0,
            'low_risk_percent': low_risk / total * 100 if total > 0 else 0,
            'avg_risk': np.mean([r.churn_risk for r in results]) if results else 0,
            'by_skill_group': by_group,
            'top_warnings': sorted_warnings[:5],
        }
