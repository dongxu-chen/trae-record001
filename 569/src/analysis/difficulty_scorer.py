import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass, field
import warnings
warnings.filterwarnings('ignore')

from src.features.data_generator import SKILL_GROUPS, SKILL_GROUP_ORDER


@dataclass
class BehavioralScore:
    total_death_density: float
    frustration_index: float
    consecutive_fail_rate: float
    rage_quit_rate: float
    avg_death_position: float
    death_concentration: float
    death_zones: Dict[str, float]
    checkpoint_utilization: float
    overall_behavioral_score: float
    
    def get_issues(self) -> List[Dict[str, Any]]:
        issues = []
        
        if self.frustration_index > 0.7:
            issues.append({
                'type': 'critical',
                'feature': 'frustration_index',
                'name': '挫败指数过高',
                'value': self.frustration_index,
                'threshold': 0.7,
                'description': '玩家挫败感极强，容易产生负面情绪'
            })
        elif self.frustration_index > 0.5:
            issues.append({
                'type': 'warning',
                'feature': 'frustration_index',
                'name': '挫败指数偏高',
                'value': self.frustration_index,
                'threshold': 0.5,
                'description': '玩家挫败感较强，需关注'
            })
        
        if self.rage_quit_rate > 0.3:
            issues.append({
                'type': 'critical',
                'feature': 'rage_quit_rate',
                'name': '愤怒流失率过高',
                'value': self.rage_quit_rate,
                'threshold': 0.3,
                'description': '大量玩家因愤怒而放弃游戏'
            })
        
        if self.consecutive_fail_rate > 0.6:
            issues.append({
                'type': 'critical',
                'feature': 'consecutive_fail_rate',
                'name': '连续失败率过高',
                'value': self.consecutive_fail_rate,
                'threshold': 0.6,
                'description': '玩家容易陷入连续失败的恶性循环'
            })
        
        if self.death_concentration > 0.7:
            primary_zone = max(self.death_zones, key=self.death_zones.get)
            zone_value = self.death_zones[primary_zone]
            issues.append({
                'type': 'warning',
                'feature': 'death_concentration',
                'name': '死亡点过于集中',
                'value': self.death_concentration,
                'threshold': 0.7,
                'primary_zone': primary_zone,
                'zone_value': zone_value,
                'description': f'死亡高度集中在 {primary_zone} ({zone_value:.1%})，可能存在设计瓶颈'
            })
        
        if self.total_death_density > 0.6:
            issues.append({
                'type': 'warning',
                'feature': 'total_death_density',
                'name': '整体死亡密度过高',
                'value': self.total_death_density,
                'threshold': 0.6,
                'description': '关卡死亡率过高，玩家容易产生挫败感'
            })
        
        return issues


@dataclass
class DifficultyScore:
    score: float
    rating: str
    rating_color: str
    completion_rate: float
    avg_attempts: float
    estimated_quit_rate: float
    components: Dict[str, float] = field(default_factory=dict)
    recommendations: List[Dict[str, Any]] = field(default_factory=list)
    behavioral_score: Optional[BehavioralScore] = None
    skill_group: Optional[str] = None
    
    def __str__(self):
        group_str = f"[{SKILL_GROUPS[self.skill_group]['name']}] " if self.skill_group else ""
        return (f"{group_str}难度评分: {self.score:.2f}/100 | 等级: {self.rating} | "
                f"通关率: {self.completion_rate:.1%} | 平均尝试: {self.avg_attempts:.1f}")


DIFFICULTY_RATINGS = [
    (0, 20, '简单', '#22c55e'),
    (20, 40, '较易', '#84cc16'),
    (40, 60, '中等', '#eab308'),
    (60, 75, '较难', '#f97316'),
    (75, 90, '困难', '#ef4444'),
    (90, 100, '专家', '#9333ea'),
]


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
    'obstacle_density': {'weight': 0.25, 'direction': 1, 'chinese_name': '障碍密度', 'unit': ''},
    'time_limit': {'weight': 0.20, 'direction': -1, 'chinese_name': '时间限制', 'unit': '秒'},
    'enemy_count': {'weight': 0.20, 'direction': 1, 'chinese_name': '敌人数量', 'unit': '个'},
    'moving_obstacle_ratio': {'weight': 0.15, 'direction': 1, 'chinese_name': '移动障碍比例', 'unit': ''},
    'platform_gap': {'weight': 0.10, 'direction': 1, 'chinese_name': '平台间距', 'unit': ''},
    'level_length': {'weight': 0.10, 'direction': 1, 'chinese_name': '关卡长度', 'unit': ''},
    'powerup_count': {'weight': 0.05, 'direction': -1, 'chinese_name': '道具数量', 'unit': '个'},
    'checkpoint_count': {'weight': 0.05, 'direction': -1, 'chinese_name': '检查点数量', 'unit': '个'},
}


DEATH_ZONE_NAMES = {
    'death_zone_1': '障碍物区域',
    'death_zone_2': '敌人密集区',
    'death_zone_3': '平台跳跃区',
    'death_zone_4': '时间压力区',
    'death_zone_5': '移动障碍区',
}


BEHAVIOR_WEIGHTS = {
    'frustration_index': 0.25,
    'rage_quit_rate': 0.25,
    'consecutive_fail_rate': 0.20,
    'total_death_density': 0.15,
    'death_concentration': 0.15,
}


class DifficultyScorer:
    def __init__(self, target_completion_rate: float = 0.6, 
                 target_avg_attempts: float = 4.0):
        self.target_completion_rate = target_completion_rate
        self.target_avg_attempts = target_avg_attempts
    
    def _normalize_feature(self, feature: str, value: float) -> float:
        min_val, max_val = FEATURE_RANGES[feature]
        normalized = (value - min_val) / (max_val - min_val)
        return np.clip(normalized, 0, 1)
    
    def _get_rating(self, score: float) -> Tuple[str, str]:
        for lower, upper, rating, color in DIFFICULTY_RATINGS:
            if lower <= score < upper:
                return rating, color
        return '专家', '#9333ea'
    
    def calculate_behavioral_score(self, level_data: pd.Series, 
                                  skill_group: str) -> Optional[BehavioralScore]:
        prefix = f'{skill_group}_'
        
        try:
            death_zones = {}
            for i in range(1, 6):
                zone_key = f'{prefix}death_zone_{i}'
                if zone_key in level_data:
                    death_zones[DEATH_ZONE_NAMES[f'death_zone_{i}']] = float(level_data[zone_key])
            
            total_death_density = float(level_data.get(f'{prefix}total_death_density', 0))
            frustration_index = float(level_data.get(f'{prefix}frustration_index', 0))
            consecutive_fail_rate = float(level_data.get(f'{prefix}consecutive_fail_rate', 0))
            rage_quit_rate = float(level_data.get(f'{prefix}rage_quit_rate', 0))
            avg_death_position = float(level_data.get(f'{prefix}avg_death_position', 0.5))
            death_concentration = float(level_data.get(f'{prefix}death_concentration', 0))
            checkpoint_utilization = float(level_data.get(f'{prefix}checkpoint_utilization', 0))
            
            behavioral_score = (
                frustration_index * BEHAVIOR_WEIGHTS['frustration_index'] +
                rage_quit_rate * BEHAVIOR_WEIGHTS['rage_quit_rate'] +
                consecutive_fail_rate * BEHAVIOR_WEIGHTS['consecutive_fail_rate'] +
                total_death_density * BEHAVIOR_WEIGHTS['total_death_density'] +
                death_concentration * BEHAVIOR_WEIGHTS['death_concentration']
            )
            
            return BehavioralScore(
                total_death_density=total_death_density,
                frustration_index=frustration_index,
                consecutive_fail_rate=consecutive_fail_rate,
                rage_quit_rate=rage_quit_rate,
                avg_death_position=avg_death_position,
                death_concentration=death_concentration,
                death_zones=death_zones,
                checkpoint_utilization=checkpoint_utilization,
                overall_behavioral_score=behavioral_score
            )
        except Exception as e:
            return None
    
    def calculate_score(self, completion_rate: float, avg_attempts: float,
                       level_params: Optional[Dict[str, float]] = None,
                       behavioral_data: Optional[pd.Series] = None,
                       skill_group: Optional[str] = None,
                       shap_contributions: Optional[pd.DataFrame] = None) -> DifficultyScore:
        completion_component = (1 - completion_rate) * 100
        attempts_component = np.clip((avg_attempts - 1) / (15 - 1) * 100, 0, 100)
        
        w_completion = 0.6
        w_attempts = 0.4
        
        score = w_completion * completion_component + w_attempts * attempts_component
        
        behavioral_score = None
        if behavioral_data is not None and skill_group is not None:
            behavioral_score = self.calculate_behavioral_score(behavioral_data, skill_group)
            
            if behavioral_score is not None:
                behavioral_component = behavioral_score.overall_behavioral_score * 100
                w_behavioral = 0.3
                score = (1 - w_behavioral) * score + w_behavioral * behavioral_component
        
        score = np.clip(score, 0, 100)
        rating, color = self._get_rating(score)
        
        estimated_quit_rate = np.clip(
            0.05 + (score / 100) ** 1.5 * 0.6,
            0.05, 0.7
        )
        
        components = {
            'completion_component': completion_component,
            'attempts_component': attempts_component,
            'weighted_score': score
        }
        
        if level_params is not None:
            feature_components = {}
            for feat, impact in FEATURE_IMPACT.items():
                if feat in level_params:
                    normalized = self._normalize_feature(feat, level_params[feat])
                    if impact['direction'] < 0:
                        normalized = 1 - normalized
                    feature_components[feat] = normalized * impact['weight'] * 100
            components.update(feature_components)
        
        if behavioral_score is not None:
            components['behavioral_score'] = behavioral_score.overall_behavioral_score * 100
        
        recommendations = self._generate_recommendations(
            completion_rate, avg_attempts, score, level_params, 
            behavioral_score, skill_group
        )
        
        return DifficultyScore(
            score=score,
            rating=rating,
            rating_color=color,
            completion_rate=completion_rate,
            avg_attempts=avg_attempts,
            estimated_quit_rate=estimated_quit_rate,
            components=components,
            recommendations=recommendations,
            behavioral_score=behavioral_score,
            skill_group=skill_group
        )
    
    def _calculate_quantum_adjustment(self, feature: str, current_value: float,
                                     direction: str, gap_magnitude: float) -> Dict[str, Any]:
        info = FEATURE_IMPACT[feature]
        min_val, max_val = FEATURE_RANGES[feature]
        range_val = max_val - min_val
        
        base_adjust_percent = 0.15
        adjustment_percent = base_adjust_percent * min(gap_magnitude * 3, 1.0)
        
        if (info['direction'] > 0 and direction == 'decrease') or \
           (info['direction'] < 0 and direction == 'increase'):
            adjustment_percent = -adjustment_percent
        
        raw_new_value = current_value * (1 + adjustment_percent)
        new_value = float(np.clip(raw_new_value, min_val, max_val))
        
        actual_change_percent = ((new_value - current_value) / current_value * 100) if current_value != 0 else 0
        
        impact_direction = '降低' if adjustment_percent < 0 else '增加'
        difficulty_impact = '降低' if (
            (info['direction'] > 0 and adjustment_percent < 0) or
            (info['direction'] < 0 and adjustment_percent > 0)
        ) else '增加'
        
        unit = info.get('unit', '')
        value_str = f"{new_value:.3f}{unit}" if unit else f"{new_value:.3f}"
        
        return {
            'feature': feature,
            'feature_name': info['chinese_name'],
            'action': '减少' if adjustment_percent < 0 else '增加',
            'adjustment_percent': abs(adjustment_percent) * 100,
            'current_value': current_value,
            'current_value_str': f"{current_value:.3f}{unit}" if unit else f"{current_value:.3f}",
            'suggested_value': new_value,
            'suggested_value_str': value_str,
            'actual_change_percent': actual_change_percent,
            'impact_direction': impact_direction,
            'difficulty_impact': difficulty_impact,
            'expected_completion_change': gap_magnitude * 0.15 * 100,
            'expected_attempts_change': -gap_magnitude * 0.5,
        }
    
    def _generate_behavioral_recommendations(self, behavioral_score: BehavioralScore,
                                             level_params: Optional[Dict[str, float]]) -> List[Dict[str, Any]]:
        recommendations = []
        issues = behavioral_score.get_issues()
        
        for issue in issues:
            if issue['feature'] == 'frustration_index' and issue['type'] in ['critical', 'warning']:
                gap_magnitude = (issue['value'] - 0.4) / 0.6
                
                rec = {
                    'type': 'danger' if issue['type'] == 'critical' else 'warning',
                    'priority': 'high',
                    'title': f"⚠️ {issue['name']}: {issue['value']:.1%}",
                    'description': issue['description'],
                    'behavioral_issue': True,
                    'issue_type': 'frustration',
                    'current_value': f"{issue['value']:.1%}",
                    'target_value': "< 40%",
                }
                
                if level_params is not None:
                    quant_adjustments = []
                    if level_params.get('obstacle_density', 0) > 0.2:
                        quant_adjustments.append(
                            self._calculate_quantum_adjustment(
                                'obstacle_density', level_params['obstacle_density'],
                                'decrease', gap_magnitude
                            )
                        )
                    if level_params.get('enemy_count', 0) > 5:
                        quant_adjustments.append(
                            self._calculate_quantum_adjustment(
                                'enemy_count', level_params['enemy_count'],
                                'decrease', gap_magnitude
                            )
                        )
                    if level_params.get('moving_obstacle_ratio', 0) > 0.3:
                        quant_adjustments.append(
                            self._calculate_quantum_adjustment(
                                'moving_obstacle_ratio', level_params['moving_obstacle_ratio'],
                                'decrease', gap_magnitude
                            )
                        )
                    
                    rec['quantified_adjustments'] = quant_adjustments
                
                recommendations.append(rec)
            
            elif issue['feature'] == 'rage_quit_rate' and issue['type'] == 'critical':
                gap_magnitude = (issue['value'] - 0.2) / 0.3
                
                rec = {
                    'type': 'danger',
                    'priority': 'high',
                    'title': f"🔥 {issue['name']}: {issue['value']:.1%}",
                    'description': issue['description'],
                    'behavioral_issue': True,
                    'issue_type': 'rage_quit',
                    'current_value': f"{issue['value']:.1%}",
                    'target_value': "< 20%",
                }
                
                if level_params is not None:
                    quant_adjustments = []
                    if level_params.get('checkpoint_count', 0) < 2:
                        quant_adjustments.append(
                            self._calculate_quantum_adjustment(
                                'checkpoint_count', level_params['checkpoint_count'],
                                'increase', gap_magnitude
                            )
                        )
                    if level_params.get('powerup_count', 0) < 2:
                        quant_adjustments.append(
                            self._calculate_quantum_adjustment(
                                'powerup_count', level_params['powerup_count'],
                                'increase', gap_magnitude
                            )
                        )
                    quant_adjustments.append(
                        self._calculate_quantum_adjustment(
                            'obstacle_density', level_params.get('obstacle_density', 0.3),
                            'decrease', gap_magnitude
                        )
                    )
                    rec['quantified_adjustments'] = quant_adjustments
                
                recommendations.append(rec)
            
            elif issue['feature'] == 'death_concentration' and issue['type'] == 'warning':
                rec = {
                    'type': 'warning',
                    'priority': 'medium',
                    'title': f"📍 {issue['name']}: {issue['value']:.1%}",
                    'description': issue['description'],
                    'behavioral_issue': True,
                    'issue_type': 'death_concentration',
                    'primary_zone': issue.get('primary_zone', ''),
                    'zone_value': f"{issue.get('zone_value', 0):.1%}",
                    'current_value': f"{issue['value']:.1%}",
                    'target_value': "< 70%",
                    'suggested_action': (
                        f"重点优化 '{issue.get('primary_zone', '')}' 区域设计，"
                        f"降低该区域难度或增加检查点"
                    )
                }
                recommendations.append(rec)
            
            elif issue['feature'] == 'consecutive_fail_rate' and issue['type'] == 'critical':
                gap_magnitude = (issue['value'] - 0.4) / 0.2
                
                rec = {
                    'type': 'danger',
                    'priority': 'high',
                    'title': f"🔄 {issue['name']}: {issue['value']:.1%}",
                    'description': issue['description'],
                    'behavioral_issue': True,
                    'issue_type': 'consecutive_fail',
                    'current_value': f"{issue['value']:.1%}",
                    'target_value': "< 40%",
                }
                
                if level_params is not None:
                    quant_adjustments = [
                        self._calculate_quantum_adjustment(
                            'checkpoint_count', level_params.get('checkpoint_count', 0),
                            'increase', gap_magnitude
                        ),
                        self._calculate_quantum_adjustment(
                            'obstacle_density', level_params.get('obstacle_density', 0.3),
                            'decrease', gap_magnitude
                        ),
                        self._calculate_quantum_adjustment(
                            'platform_gap', level_params.get('platform_gap', 1.5),
                            'decrease', gap_magnitude
                        )
                    ]
                    rec['quantified_adjustments'] = quant_adjustments
                
                recommendations.append(rec)
        
        return recommendations
    
    def _generate_recommendations(self, completion_rate: float, 
                                  avg_attempts: float,
                                  current_score: float,
                                  level_params: Optional[Dict[str, float]],
                                  behavioral_score: Optional[BehavioralScore] = None,
                                  skill_group: Optional[str] = None) -> List[Dict[str, Any]]:
        recommendations = []
        
        if behavioral_score is not None:
            behavioral_recs = self._generate_behavioral_recommendations(
                behavioral_score, level_params
            )
            recommendations.extend(behavioral_recs)
        
        gap_completion = self.target_completion_rate - completion_rate
        gap_attempts = self.target_avg_attempts - avg_attempts
        
        if abs(gap_completion) < 0.05 and abs(gap_attempts) < 0.5 and len(recommendations) == 0:
            recommendations.append({
                'type': 'success',
                'priority': 'low',
                'title': '✅ 难度设计优秀',
                'description': '当前关卡难度接近目标值，玩家体验良好。',
                'action': '保持当前设计'
            })
            return recommendations
        
        if completion_rate < self.target_completion_rate - 0.1:
            gap_magnitude = min(abs(gap_completion) / 0.3, 1.0)
            
            quant_adjustments = []
            if level_params is not None:
                priority_features = sorted(
                    FEATURE_IMPACT.items(),
                    key=lambda x: x[1]['weight'] * abs(x[1]['direction']),
                    reverse=True
                )
                
                for feat, impact in priority_features[:4]:
                    if feat not in level_params:
                        continue
                    if impact['direction'] > 0:
                        quant_adjustments.append(
                            self._calculate_quantum_adjustment(
                                feat, level_params[feat], 'decrease', gap_magnitude
                            )
                        )
                    else:
                        quant_adjustments.append(
                            self._calculate_quantum_adjustment(
                                feat, level_params[feat], 'increase', gap_magnitude
                            )
                        )
            
            recommendations.append({
                'type': 'warning',
                'priority': 'high',
                'title': f"📉 通关率过低: {completion_rate:.1%} (目标 {self.target_completion_rate:.1%})",
                'description': f'通关率低于目标 {gap_completion*100:.1f} 个百分点',
                'gap_magnitude': gap_magnitude,
                'quantified_adjustments': quant_adjustments
            })
        
        elif completion_rate > self.target_completion_rate + 0.1:
            gap_magnitude = min(abs(gap_completion) / 0.3, 1.0)
            
            quant_adjustments = []
            if level_params is not None:
                priority_features = sorted(
                    FEATURE_IMPACT.items(),
                    key=lambda x: x[1]['weight'] * abs(x[1]['direction']),
                    reverse=True
                )
                
                for feat, impact in priority_features[:4]:
                    if feat not in level_params:
                        continue
                    if impact['direction'] > 0:
                        quant_adjustments.append(
                            self._calculate_quantum_adjustment(
                                feat, level_params[feat], 'increase', gap_magnitude
                            )
                        )
                    else:
                        quant_adjustments.append(
                            self._calculate_quantum_adjustment(
                                feat, level_params[feat], 'decrease', gap_magnitude
                            )
                        )
            
            recommendations.append({
                'type': 'info',
                'priority': 'medium',
                'title': f"📈 通关率过高: {completion_rate:.1%} (目标 {self.target_completion_rate:.1%})",
                'description': f'通关率高于目标 {abs(gap_completion)*100:.1f} 个百分点',
                'gap_magnitude': gap_magnitude,
                'quantified_adjustments': quant_adjustments
            })
        
        if avg_attempts > self.target_avg_attempts + 2:
            gap_magnitude = min(abs(gap_attempts) / 6, 1.0)
            
            quant_adjustments = []
            if level_params is not None:
                quant_adjustments = [
                    self._calculate_quantum_adjustment(
                        'obstacle_density', level_params.get('obstacle_density', 0.3),
                        'decrease', gap_magnitude
                    ),
                    self._calculate_quantum_adjustment(
                        'enemy_count', level_params.get('enemy_count', 5),
                        'decrease', gap_magnitude
                    ),
                    self._calculate_quantum_adjustment(
                        'moving_obstacle_ratio', level_params.get('moving_obstacle_ratio', 0.3),
                        'decrease', gap_magnitude
                    ),
                    self._calculate_quantum_adjustment(
                        'checkpoint_count', level_params.get('checkpoint_count', 1),
                        'increase', gap_magnitude
                    ),
                ]
            
            recommendations.append({
                'type': 'warning',
                'priority': 'high',
                'title': f"🔄 重试次数过多: {avg_attempts:.1f} 次 (目标 {self.target_avg_attempts:.1f} 次)",
                'description': f'平均尝试次数高于目标 {avg_attempts - self.target_avg_attempts:.1f} 次',
                'gap_magnitude': gap_magnitude,
                'quantified_adjustments': quant_adjustments
            })
        
        elif avg_attempts < self.target_avg_attempts - 1:
            gap_magnitude = min(abs(gap_attempts) / 3, 1.0)
            
            quant_adjustments = []
            if level_params is not None:
                quant_adjustments = [
                    self._calculate_quantum_adjustment(
                        'obstacle_density', level_params.get('obstacle_density', 0.3),
                        'increase', gap_magnitude
                    ),
                    self._calculate_quantum_adjustment(
                        'enemy_count', level_params.get('enemy_count', 5),
                        'increase', gap_magnitude
                    ),
                    self._calculate_quantum_adjustment(
                        'moving_obstacle_ratio', level_params.get('moving_obstacle_ratio', 0.3),
                        'increase', gap_magnitude
                    ),
                    self._calculate_quantum_adjustment(
                        'powerup_count', level_params.get('powerup_count', 2),
                        'decrease', gap_magnitude
                    ),
                ]
            
            recommendations.append({
                'type': 'info',
                'priority': 'medium',
                'title': f"🎯 重试次数不足: {avg_attempts:.1f} 次 (目标 {self.target_avg_attempts:.1f} 次)",
                'description': f'平均尝试次数低于目标 {self.target_avg_attempts - avg_attempts:.1f} 次',
                'gap_magnitude': gap_magnitude,
                'quantified_adjustments': quant_adjustments
            })
        
        if current_score > 80:
            recommendations.append({
                'type': 'danger',
                'priority': 'high',
                'title': f"🚨 难度过高警告: {current_score:.1f}/100",
                'description': '当前难度可能导致大量玩家流失，建议大幅调整。',
                'estimated_quit_rate': f'{current_score * 0.7:.1%}'
            })
        elif current_score < 20 and len(recommendations) == 0:
            recommendations.append({
                'type': 'info',
                'priority': 'low',
                'title': f"😴 难度偏低: {current_score:.1f}/100",
                'description': '关卡可能过于简单，缺乏挑战性。'
            })
        
        return recommendations
    
    def calculate_score_for_all_groups(self, predictions_by_group: Dict[str, Dict[str, float]],
                                       level_params: Optional[Dict[str, float]] = None,
                                       level_behavioral_data: Optional[pd.Series] = None
                                       ) -> Dict[str, DifficultyScore]:
        scores = {}
        
        for group in SKILL_GROUP_ORDER:
            if group not in predictions_by_group:
                continue
            
            pred = predictions_by_group[group]
            
            completion_rate = pred.get(
                f'actual_{group}_completion_rate', 
                pred.get(f'{group}_completion_rate', 0)
            )
            avg_attempts = pred.get(
                f'actual_{group}_avg_attempts',
                pred.get(f'{group}_avg_attempts', 0)
            )
            
            score = self.calculate_score(
                completion_rate, avg_attempts,
                level_params, level_behavioral_data, group
            )
            scores[group] = score
        
        return scores
    
    def format_quantified_table(self, adjustments: List[Dict[str, Any]]) -> pd.DataFrame:
        if not adjustments:
            return pd.DataFrame()
        
        rows = []
        for adj in adjustments:
            rows.append({
                '参数名称': adj['feature_name'],
                '调整方向': f"{adj['action']} {adj['adjustment_percent']:.0f}%",
                '当前值': adj['current_value_str'],
                '建议值': adj['suggested_value_str'],
                '对难度影响': f"{adj['difficulty_impact']}",
                '预期通关率变化': f"{adj['expected_completion_change']:+.1f}%",
                '预期尝试变化': f"{adj['expected_attempts_change']:+.1f} 次",
            })
        
        return pd.DataFrame(rows)


if __name__ == "__main__":
    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    
    from src.features.data_generator import generate_full_dataset
    
    print("生成数据...")
    df_levels, df_players = generate_full_dataset(n_levels=50, n_players=200)
    
    print("\n=== 难度评分系统测试（含行为特征和量化建议）===")
    scorer = DifficultyScorer(target_completion_rate=0.6, target_avg_attempts=4.0)
    
    sample_row = df_levels.iloc[0]
    
    from src.features.preprocessing import FEATURE_COLUMNS
    sample_params = sample_row[FEATURE_COLUMNS].to_dict()
    
    print(f"\n测试关卡参数: {sample_params}")
    
    for group in SKILL_GROUP_ORDER:
        group_name = SKILL_GROUPS[group]['name']
        completion_rate = sample_row[f'{group}_completion_rate']
        avg_attempts = sample_row[f'{group}_avg_attempts']
        
        score = scorer.calculate_score(
            completion_rate, avg_attempts,
            sample_params, sample_row, group
        )
        
        print(f"\n{'='*50}")
        print(f"【{group_name}】{score}")
        print(f"{'='*50}")
        
        if score.behavioral_score:
            print(f"\n行为特征评分:")
            print(f"  挫败指数: {score.behavioral_score.frustration_index:.2f}")
            print(f"  愤怒流失率: {score.behavioral_score.rage_quit_rate:.1%}")
            print(f"  连续失败率: {score.behavioral_score.consecutive_fail_rate:.1%}")
            print(f"  死亡集中度: {score.behavioral_score.death_concentration:.2f}")
            print(f"  主要死区: {max(score.behavioral_score.death_zones, key=score.behavioral_score.death_zones.get)}")
        
        print(f"\n调整建议 ({len(score.recommendations)} 条):")
        for i, rec in enumerate(score.recommendations[:3], 1):
            print(f"\n  {i}. [{rec['priority'].upper()}] {rec['title']}")
            print(f"     {rec.get('description', '')}")
            
            if 'quantified_adjustments' in rec:
                adj_df = scorer.format_quantified_table(rec['quantified_adjustments'])
                if not adj_df.empty:
                    print(f"\n     量化调整方案:")
                    for _, row in adj_df.iterrows():
                        print(f"       • {row['参数名称']}: {row['当前值']} → {row['建议值']} "
                              f"({row['调整方向']}, 通关率{row['预期通关率变化']})")
