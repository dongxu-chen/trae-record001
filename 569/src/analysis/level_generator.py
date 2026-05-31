import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional, Any, Union
from dataclasses import dataclass, field
import warnings
warnings.filterwarnings('ignore')

from src.features.data_generator import SKILL_GROUPS, SKILL_GROUP_ORDER
from src.features.preprocessing import FEATURE_COLUMNS, prepare_single_prediction
from src.models.xgboost_model import GroupedDifficultyModel

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

LEVEL_TYPES = {
    'platforming': {
        'name': '平台跳跃',
        'emphasis': ['platform_gap', 'obstacle_density', 'level_length'],
        'suppress': ['enemy_count'],
        'description': '侧重跳跃和躲避的关卡'
    },
    'combat': {
        'name': '战斗挑战',
        'emphasis': ['enemy_count', 'moving_obstacle_ratio'],
        'suppress': ['platform_gap'],
        'description': '侧重战斗和敌人击杀的关卡'
    },
    'speedrun': {
        'name': '速通挑战',
        'emphasis': ['time_limit', 'level_length', 'moving_obstacle_ratio'],
        'suppress': ['checkpoint_count', 'powerup_count'],
        'description': '侧重速度和时间压力的关卡'
    },
    'exploration': {
        'name': '探索收集',
        'emphasis': ['level_length', 'powerup_count', 'checkpoint_count'],
        'suppress': ['enemy_count', 'time_limit'],
        'description': '侧重探索和收集的关卡'
    },
    'balanced': {
        'name': '综合平衡',
        'emphasis': [],
        'suppress': [],
        'description': '各要素均衡的综合关卡'
    },
}


@dataclass
class GeneratedLevel:
    level_id: str
    level_type: str
    target_difficulty: float
    target_skill_group: str
    params: Dict[str, float]
    predicted_metrics: Dict[str, float]
    difficulty_score: float
    difficulty_rating: str
    behavioral_risk: Dict[str, float]
    generation_score: float
    constraints_satisfied: bool
    generation_notes: List[str]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'level_id': self.level_id,
            'level_type': self.level_type,
            'level_type_name': LEVEL_TYPES[self.level_type]['name'],
            'target_difficulty': self.target_difficulty,
            'target_skill_group': self.target_skill_group,
            'target_skill_name': SKILL_GROUPS[self.target_skill_group]['name'],
            **self.params,
            **self.predicted_metrics,
            'difficulty_score': self.difficulty_score,
            'difficulty_rating': self.difficulty_rating,
            'generation_score': self.generation_score,
            'constraints_satisfied': self.constraints_satisfied,
        }


@dataclass
class GenerationConstraints:
    min_obstacle_density: Optional[float] = None
    max_obstacle_density: Optional[float] = None
    min_time_limit: Optional[int] = None
    max_time_limit: Optional[int] = None
    min_enemy_count: Optional[int] = None
    max_enemy_count: Optional[int] = None
    min_platform_gap: Optional[float] = None
    max_platform_gap: Optional[float] = None
    require_powerups: bool = False
    require_checkpoints: bool = False
    preferred_feature_ranges: Dict[str, Tuple[float, float]] = field(default_factory=dict)
    
    def apply(self, params: Dict[str, float]) -> Dict[str, float]:
        constrained = params.copy()
        
        for feature, (min_val, max_val) in FEATURE_RANGES.items():
            constrained[feature] = np.clip(constrained[feature], min_val, max_val)
        
        if self.min_obstacle_density is not None:
            constrained['obstacle_density'] = max(constrained['obstacle_density'], self.min_obstacle_density)
        if self.max_obstacle_density is not None:
            constrained['obstacle_density'] = min(constrained['obstacle_density'], self.max_obstacle_density)
        
        if self.min_time_limit is not None:
            constrained['time_limit'] = max(constrained['time_limit'], self.min_time_limit)
        if self.max_time_limit is not None:
            constrained['time_limit'] = min(constrained['time_limit'], self.max_time_limit)
        
        if self.min_enemy_count is not None:
            constrained['enemy_count'] = max(constrained['enemy_count'], self.min_enemy_count)
        if self.max_enemy_count is not None:
            constrained['enemy_count'] = min(constrained['enemy_count'], self.max_enemy_count)
        
        if self.min_platform_gap is not None:
            constrained['platform_gap'] = max(constrained['platform_gap'], self.min_platform_gap)
        if self.max_platform_gap is not None:
            constrained['platform_gap'] = min(constrained['platform_gap'], self.max_platform_gap)
        
        if self.require_powerups:
            constrained['powerup_count'] = max(constrained['powerup_count'], 1)
        if self.require_checkpoints:
            constrained['checkpoint_count'] = max(constrained['checkpoint_count'], 1)
        
        for feature, (f_min, f_max) in self.preferred_feature_ranges.items():
            if feature in constrained:
                constrained[feature] = np.clip(constrained[feature], f_min, f_max)
        
        constrained['enemy_count'] = int(round(constrained['enemy_count']))
        constrained['powerup_count'] = int(round(constrained['powerup_count']))
        constrained['checkpoint_count'] = int(round(constrained['checkpoint_count']))
        constrained['time_limit'] = int(round(constrained['time_limit']))
        constrained['level_length'] = int(round(constrained['level_length']))
        
        return constrained
    
    def check(self, params: Dict[str, float]) -> Tuple[bool, List[str]]:
        satisfied = True
        notes = []
        
        if self.min_obstacle_density is not None and params['obstacle_density'] < self.min_obstacle_density:
            satisfied = False
            notes.append(f"障碍密度低于最小值 {self.min_obstacle_density}")
        if self.max_obstacle_density is not None and params['obstacle_density'] > self.max_obstacle_density:
            satisfied = False
            notes.append(f"障碍密度高于最大值 {self.max_obstacle_density}")
        
        if self.require_powerups and params['powerup_count'] < 1:
            satisfied = False
            notes.append("需要至少1个道具")
        if self.require_checkpoints and params['checkpoint_count'] < 1:
            satisfied = False
            notes.append("需要至少1个检查点")
        
        return satisfied, notes


class LevelGenerator:
    def __init__(
        self,
        model: Optional[GroupedDifficultyModel] = None,
        engineer: Optional[Any] = None,
        random_state: int = 42
    ):
        self.model = model
        self.engineer = engineer
        self.random_state = random_state
        np.random.seed(random_state)
    
    def _calculate_base_difficulty(self, params: Dict[str, float]) -> float:
        obstacle_effect = params['obstacle_density'] * 1.2
        time_pressure_effect = (180 - params['time_limit']) / 180 * 0.8
        enemy_effect = params['enemy_count'] / 15 * 0.9
        gap_effect = (params['platform_gap'] - 0.5) / 2.5 * 0.5
        moving_effect = params['moving_obstacle_ratio'] * 0.7
        powerup_help = params['powerup_count'] / 5 * 0.3
        checkpoint_help = params['checkpoint_count'] / 4 * 0.25
        length_effect = (params['level_length'] - 50) / 250 * 0.4
        
        base_difficulty = (
            obstacle_effect +
            time_pressure_effect +
            enemy_effect +
            gap_effect +
            moving_effect +
            length_effect -
            powerup_help -
            checkpoint_help
        ) / 7.0
        
        return np.clip(base_difficulty, 0, 1)
    
    def _generate_initial_params(
        self,
        target_difficulty: float,
        level_type: str,
        skill_group: str
    ) -> Dict[str, float]:
        group_factor = {
            'novice': 0.6,
            'intermediate': 1.0,
            'expert': 1.4
        }.get(skill_group, 1.0)
        
        adjusted_target = target_difficulty * group_factor
        
        params = {}
        type_config = LEVEL_TYPES.get(level_type, LEVEL_TYPES['balanced'])
        
        for feature, (min_val, max_val) in FEATURE_RANGES.items():
            base_value = min_val + (max_val - min_val) * adjusted_target
            
            if feature in type_config['emphasis']:
                base_value = min_val + (max_val - min_val) * (adjusted_target * 1.3)
            elif feature in type_config['suppress']:
                base_value = min_val + (max_val - min_val) * (adjusted_target * 0.7)
            
            impact = FEATURE_IMPACT.get(feature, {'direction': 1, 'weight': 0.1})
            if impact['direction'] < 0:
                base_value = min_val + (max_val - min_val) * (1 - adjusted_target)
            
            noise = np.random.uniform(-0.1, 0.1) * (max_val - min_val)
            params[feature] = np.clip(base_value + noise, min_val, max_val)
        
        params['enemy_count'] = int(round(params['enemy_count']))
        params['powerup_count'] = int(round(params['powerup_count']))
        params['checkpoint_count'] = int(round(params['checkpoint_count']))
        params['time_limit'] = int(round(params['time_limit']))
        params['level_length'] = int(round(params['level_length']))
        
        return params
    
    def _predict_metrics(
        self,
        params: Dict[str, float],
        skill_group: str
    ) -> Dict[str, float]:
        if self.model is None or self.engineer is None:
            base_diff = self._calculate_base_difficulty(params)
            group_factor = {'novice': 1.8, 'intermediate': 1.0, 'expert': 0.6}[skill_group]
            adjusted_diff = base_diff * group_factor
            
            predicted_completion = np.clip(0.9 - adjusted_diff * 0.8, 0.1, 0.95)
            predicted_attempts = max(1.0, 2.0 + adjusted_diff * 8.0)
            
            return {
                'completion_rate': predicted_completion,
                'avg_attempts': predicted_attempts,
                'base_difficulty': base_diff
            }
        
        X = prepare_single_prediction(params, self.engineer)
        predictions = self.model.predict_single_group(X, skill_group)
        
        return {
            'completion_rate': predictions.get(f'{skill_group}_completion_rate', 0.5),
            'avg_attempts': predictions.get(f'{skill_group}_avg_attempts', 4.0),
        }
    
    def _calculate_behavioral_risk(
        self,
        params: Dict[str, float],
        target_difficulty: float
    ) -> Dict[str, float]:
        frustration_index = (
            params['obstacle_density'] * 0.25 +
            params['enemy_count'] / 15 * 0.25 +
            params['moving_obstacle_ratio'] * 0.2 +
            (180 - params['time_limit']) / 180 * 0.15 +
            params['platform_gap'] / 3 * 0.15
        )
        
        death_zones = {
            'obstacle_zone': params['obstacle_density'] * 0.3 * target_difficulty,
            'enemy_zone': params['enemy_count'] / 15 * 0.25 * target_difficulty,
            'platform_zone': params['platform_gap'] / 3 * 0.2 * target_difficulty,
            'time_zone': (180 - params['time_limit']) / 180 * 0.15 * target_difficulty,
            'moving_zone': params['moving_obstacle_ratio'] * 0.2 * target_difficulty,
        }
        
        rage_quit_rate = frustration_index * target_difficulty * 0.4
        consecutive_fail_rate = frustration_index * target_difficulty * 0.5
        
        return {
            'frustration_index': frustration_index,
            'rage_quit_rate': rage_quit_rate,
            'consecutive_fail_rate': consecutive_fail_rate,
            'death_zones': death_zones,
            'death_concentration': max(death_zones.values()) if death_zones else 0,
        }
    
    def _calculate_generation_score(
        self,
        params: Dict[str, float],
        target_difficulty: float,
        predicted_metrics: Dict[str, float],
        target_completion_rate: float = 0.6
    ) -> Tuple[float, List[str]]:
        notes = []
        
        actual_difficulty = self._calculate_base_difficulty(params)
        difficulty_error = abs(actual_difficulty - target_difficulty)
        difficulty_score = max(0, 1 - difficulty_error * 2)
        
        if difficulty_error > 0.2:
            notes.append(f"难度偏差较大: 目标{target_difficulty:.2f}, 实际{actual_difficulty:.2f}")
        
        completion_error = abs(predicted_metrics['completion_rate'] - target_completion_rate)
        completion_score = max(0, 1 - completion_error * 2)
        
        params_list = list(params.values())
        variance = np.var(params_list / np.array(list(FEATURE_RANGES.values()))[:, 1])
        diversity_score = min(1, variance * 5)
        
        behavioral_risk = self._calculate_behavioral_risk(params, target_difficulty)
        risk_penalty = max(0, behavioral_risk['frustration_index'] - 0.6) * 0.5
        
        total_score = (
            difficulty_score * 0.4 +
            completion_score * 0.3 +
            diversity_score * 0.2 -
            risk_penalty
        )
        total_score = np.clip(total_score, 0, 1)
        
        return total_score, notes
    
    def _get_difficulty_rating(self, score: float) -> str:
        if score < 20:
            return '简单'
        elif score < 35:
            return '较易'
        elif score < 50:
            return '中等'
        elif score < 65:
            return '较难'
        elif score < 80:
            return '困难'
        else:
            return '专家'
    
    def generate_level(
        self,
        target_difficulty: float,
        skill_group: str = 'intermediate',
        level_type: str = 'balanced',
        constraints: Optional[GenerationConstraints] = None,
        level_id: Optional[str] = None,
        max_attempts: int = 50
    ) -> Optional[GeneratedLevel]:
        if constraints is None:
            constraints = GenerationConstraints()
        
        best_level = None
        best_score = -1
        
        for attempt in range(max_attempts):
            params = self._generate_initial_params(target_difficulty, level_type, skill_group)
            params = constraints.apply(params)
            
            constrained_ok, constraint_notes = constraints.check(params)
            
            predicted = self._predict_metrics(params, skill_group)
            gen_score, gen_notes = self._calculate_generation_score(
                params, target_difficulty, predicted
            )
            
            all_notes = constraint_notes + gen_notes
            
            base_diff = self._calculate_base_difficulty(params)
            difficulty_score_100 = base_diff * 100
            rating = self._get_difficulty_rating(difficulty_score_100)
            
            behavioral_risk = self._calculate_behavioral_risk(params, target_difficulty)
            
            level = GeneratedLevel(
                level_id=level_id or f"Gen_{attempt+1:03d}",
                level_type=level_type,
                target_difficulty=target_difficulty,
                target_skill_group=skill_group,
                params=params,
                predicted_metrics=predicted,
                difficulty_score=difficulty_score_100,
                difficulty_rating=rating,
                behavioral_risk=behavioral_risk,
                generation_score=gen_score,
                constraints_satisfied=constrained_ok,
                generation_notes=all_notes
            )
            
            if constrained_ok and gen_score > best_score:
                best_score = gen_score
                best_level = level
            
            if constrained_ok and gen_score > 0.8:
                break
        
        return best_level
    
    def generate_multiple_levels(
        self,
        n_levels: int,
        target_difficulty: float,
        skill_group: str = 'intermediate',
        level_types: Optional[List[str]] = None,
        constraints: Optional[GenerationConstraints] = None,
        diverse: bool = True
    ) -> List[GeneratedLevel]:
        if level_types is None:
            level_types = list(LEVEL_TYPES.keys())
        
        levels = []
        
        for i in range(n_levels):
            if diverse:
                level_type = level_types[i % len(level_types)]
            else:
                level_type = np.random.choice(level_types)
            
            level = self.generate_level(
                target_difficulty=target_difficulty,
                skill_group=skill_group,
                level_type=level_type,
                constraints=constraints,
                level_id=f"Gen_{i+1:03d}",
                max_attempts=30
            )
            
            if level is not None:
                levels.append(level)
        
        levels.sort(key=lambda l: l.generation_score, reverse=True)
        
        return levels
    
    def generate_level_curve(
        self,
        n_levels: int,
        start_difficulty: float = 0.2,
        end_difficulty: float = 0.8,
        skill_group: str = 'intermediate',
        curve_type: str = 'linear',
        constraints: Optional[GenerationConstraints] = None
    ) -> List[GeneratedLevel]:
        if curve_type == 'linear':
            difficulties = np.linspace(start_difficulty, end_difficulty, n_levels)
        elif curve_type == 'exponential':
            difficulties = start_difficulty + (end_difficulty - start_difficulty) * (np.linspace(0, 1, n_levels) ** 2)
        elif curve_type == 'sigmoid':
            x = np.linspace(-5, 5, n_levels)
            sigmoid = 1 / (1 + np.exp(-x))
            difficulties = start_difficulty + (end_difficulty - start_difficulty) * sigmoid
        else:
            difficulties = np.linspace(start_difficulty, end_difficulty, n_levels)
        
        levels = []
        for i, diff in enumerate(difficulties):
            level = self.generate_level(
                target_difficulty=diff,
                skill_group=skill_group,
                level_type='balanced',
                constraints=constraints,
                level_id=f"Curve_{i+1:03d}",
                max_attempts=30
            )
            if level:
                levels.append(level)
        
        return levels
    
    def levels_to_dataframe(self, levels: List[GeneratedLevel]) -> pd.DataFrame:
        data = [level.to_dict() for level in levels]
        return pd.DataFrame(data)
