import time
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass, field
from enum import Enum
import yaml

from .data_models import ClickLog, ClickFeatures
from .rule_engine_v2 import RuleEngineV2, RuleResult
from .anomaly_detector import AnomalyDetector
from .threshold_manager import PublisherThresholdManager


class ActionType(Enum):
    OBSERVE = "observe"
    DISCOUNT = "discount"
    HEAVY_DISCOUNT = "heavy_discount"
    BLOCK = "block"


@dataclass
class PenaltyLevel:
    level: int
    name: str
    action: ActionType
    description: str
    penalty_rate: float
    score_min: float
    score_max: float


@dataclass
class FraudAssessmentV2:
    click_id: str
    timestamp: float
    publisher_id: str
    final_fraud_score: float
    rule_based_score: float
    anomaly_score: float
    publisher_threshold: float
    is_fraud: bool
    triggered_rules: List[str]
    rule_details: Dict[str, Dict]
    top_anomaly_features: List[Tuple[str, float]]
    penalty_level: PenaltyLevel
    action_reason: str
    confidence: float
    repeat_offense_count: int
    is_escalated: bool
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            'click_id': self.click_id,
            'timestamp': self.timestamp,
            'publisher_id': self.publisher_id,
            'final_fraud_score': self.final_fraud_score,
            'rule_based_score': self.rule_based_score,
            'anomaly_score': self.anomaly_score,
            'publisher_threshold': self.publisher_threshold,
            'is_fraud': self.is_fraud,
            'triggered_rules': self.triggered_rules,
            'rule_details': self.rule_details,
            'top_anomaly_features': [list(item) for item in self.top_anomaly_features],
            'penalty_level': {
                'level': self.penalty_level.level,
                'name': self.penalty_level.name,
                'action': self.penalty_level.action.value,
                'description': self.penalty_level.description,
                'penalty_rate': self.penalty_level.penalty_rate
            },
            'action_reason': self.action_reason,
            'confidence': self.confidence,
            'repeat_offense_count': self.repeat_offense_count,
            'is_escalated': self.is_escalated,
            'details': self.details
        }


class GradedPenaltyManager:
    def __init__(self, config_path: str = 'config/config.yaml'):
        self.config = self._load_config(config_path)
        self.action_config = self.config.get('action', {})
        self.graded_config = self.action_config.get('graded_penalty', {})
        self.escalation_config = self.graded_config.get('escalation', {})
        
        self.enabled = self.graded_config.get('enabled', True)
        self.penalty_levels: List[PenaltyLevel] = self._load_penalty_levels()
        self.penalty_levels.sort(key=lambda x: x.level)
        
        self.escalation_enabled = self.escalation_config.get('enabled', True)
        self.repeat_offense_window = self.escalation_config.get('repeat_offense_window_seconds', 86400)
        self.max_offenses = self.escalation_config.get('max_offenses', 3)
        self.escalation_levels = self.escalation_config.get('escalation_levels', 1)
        
        self.penalty_durations = self.graded_config.get('ip_penalty_duration', {
            'observe': 0,
            'discount': 3600,
            'heavy_discount': 7200,
            'block': 86400
        })
        
        self.ip_offense_history: Dict[str, List[float]] = {}

    def _load_config(self, config_path: str) -> Dict:
        with open(config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)

    def _load_penalty_levels(self) -> List[PenaltyLevel]:
        levels = []
        for level_config in self.graded_config.get('levels', []):
            score_range = level_config.get('score_range', [0, 1])
            levels.append(PenaltyLevel(
                level=level_config['level'],
                name=level_config['name'],
                action=ActionType(level_config['action']),
                description=level_config['description'],
                penalty_rate=level_config.get('penalty_rate', 0.0),
                score_min=score_range[0],
                score_max=score_range[1]
            ))
        return levels

    def get_penalty_level(self, fraud_score: float, ip: str = None) -> Tuple[PenaltyLevel, int, bool]:
        base_level = self._get_base_penalty_level(fraud_score)
        offense_count = 0
        is_escalated = False
        
        if self.escalation_enabled and ip:
            offense_count = self._get_repeat_offense_count(ip)
            if offense_count >= self.max_offenses:
                base_level = self._escalate_penalty(base_level, self.escalation_levels)
                is_escalated = True
        
        return base_level, offense_count, is_escalated

    def _get_base_penalty_level(self, fraud_score: float) -> PenaltyLevel:
        for level in self.penalty_levels:
            if level.score_min <= fraud_score < level.score_max:
                return level
        return self.penalty_levels[-1] if self.penalty_levels else PenaltyLevel(
            level=0, name="未知", action=ActionType.OBSERVE,
            description="", penalty_rate=0.0, score_min=0, score_max=1
        )

    def _escalate_penalty(self, current_level: PenaltyLevel, escalation_levels: int) -> PenaltyLevel:
        current_idx = next((i for i, l in enumerate(self.penalty_levels) if l.level == current_level.level), -1)
        if current_idx == -1:
            return current_level
        
        new_idx = min(len(self.penalty_levels) - 1, current_idx + escalation_levels)
        return self.penalty_levels[new_idx]

    def _get_repeat_offense_count(self, ip: str) -> int:
        if ip not in self.ip_offense_history:
            return 0
        
        current_time = time.time()
        recent_offenses = [
            t for t in self.ip_offense_history[ip]
            if current_time - t <= self.repeat_offense_window
        ]
        self.ip_offense_history[ip] = recent_offenses
        return len(recent_offenses)

    def record_offense(self, ip: str):
        if ip not in self.ip_offense_history:
            self.ip_offense_history[ip] = []
        self.ip_offense_history[ip].append(time.time())
        
        current_time = time.time()
        self.ip_offense_history[ip] = [
            t for t in self.ip_offense_history[ip]
            if current_time - t <= self.repeat_offense_window
        ]

    def get_penalty_duration(self, action: ActionType) -> int:
        return self.penalty_durations.get(action.value, 0)


class FraudScorerV2:
    def __init__(self, config_path: str = 'config/config.yaml', use_redis: bool = True):
        self.config = self._load_config(config_path)
        self.config_path = config_path
        
        self.rule_engine = RuleEngineV2(config_path, use_redis=use_redis)
        self.anomaly_detector = AnomalyDetector(config_path)
        self.threshold_manager = PublisherThresholdManager(config_path)
        self.penalty_manager = GradedPenaltyManager(config_path)
        
        self.rule_weight = 0.6
        self.anomaly_weight = 0.4
        
        self._init_model()

    def _load_config(self, config_path: str) -> Dict:
        with open(config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)

    def _init_model(self):
        try:
            self.anomaly_detector.load_model()
        except FileNotFoundError:
            training_data = self.anomaly_detector.generate_training_data(n_samples=2000, fraud_ratio=0.15)
            self.anomaly_detector.train(training_data)
            self.anomaly_detector.save_model()

    def assess(self, click_log: ClickLog, features: ClickFeatures) -> FraudAssessmentV2:
        publisher_id = click_log.publisher_id
        ip = click_log.ip
        
        rule_results = self.rule_engine.evaluate_all_rules(click_log, features)
        rule_based_score = self.rule_engine.get_aggregated_rule_score(rule_results)
        
        is_anomaly, anomaly_score, feature_contributions = self.anomaly_detector.predict(features)
        top_features = self.anomaly_detector.get_top_anomaly_features(features, top_k=5)
        
        final_score = self._fuse_scores(rule_based_score, anomaly_score)
        
        self.threshold_manager.record_score(publisher_id, final_score)
        
        publisher_threshold = self.threshold_manager.get_threshold(publisher_id)
        is_fraud = final_score >= publisher_threshold
        
        triggered_rules = [r.rule_name for r in rule_results if r.triggered]
        rule_details = {r.rule_name: {'score': r.fraud_score, 'reason': r.reason, 'details': r.details} 
                       for r in rule_results if r.triggered}
        
        if is_fraud:
            self.penalty_manager.record_offense(ip)
        
        penalty_level, offense_count, is_escalated = self.penalty_manager.get_penalty_level(final_score, ip)
        
        action_reason = self._build_action_reason(
            final_score, publisher_threshold, triggered_rules, penalty_level, offense_count, is_escalated
        )
        
        confidence = self._calculate_confidence(rule_results, anomaly_score, final_score, publisher_threshold)
        
        return FraudAssessmentV2(
            click_id=click_log.click_id,
            timestamp=time.time(),
            publisher_id=publisher_id,
            final_fraud_score=final_score,
            rule_based_score=rule_based_score,
            anomaly_score=anomaly_score,
            publisher_threshold=publisher_threshold,
            is_fraud=is_fraud,
            triggered_rules=triggered_rules,
            rule_details=rule_details,
            top_anomaly_features=top_features,
            penalty_level=penalty_level,
            action_reason=action_reason,
            confidence=confidence,
            repeat_offense_count=offense_count,
            is_escalated=is_escalated,
            details={
                'feature_contributions': feature_contributions,
                'is_anomaly_from_model': is_anomaly
            }
        )

    def _fuse_scores(self, rule_score: float, anomaly_score: float) -> float:
        if rule_score > 0.8 and anomaly_score > 0.8:
            return min(1.0, max(rule_score, anomaly_score) * 1.05)
        
        weighted_score = (rule_score * self.rule_weight) + (anomaly_score * self.anomaly_weight)
        
        if rule_score > 0.5 and anomaly_score > 0.5:
            weighted_score = min(1.0, weighted_score * 1.1)
        
        return min(1.0, weighted_score)

    def _build_action_reason(self, final_score: float, threshold: float, 
                            triggered_rules: List[str], penalty_level: PenaltyLevel,
                            offense_count: int, is_escalated: bool) -> str:
        reasons = []
        
        if triggered_rules:
            reasons.append(f"触发规则: {', '.join(triggered_rules[:3])}")
        
        reasons.append(f"欺诈分数 {final_score:.2f} >= 阈值 {threshold:.2f}")
        
        if is_escalated:
            reasons.append(f"屡犯加重处罚({offense_count}次违规)")
        
        reasons.append(f"执行{penalty_level.name}({penalty_level.description})")
        
        return "; ".join(reasons)

    def _calculate_confidence(self, rule_results: List[RuleResult], anomaly_score: float, 
                             final_score: float, threshold: float) -> float:
        triggered_count = len([r for r in rule_results if r.triggered])
        total_rules = len(rule_results)
        
        rule_consistency = 1.0 if triggered_count == 0 else min(1.0, triggered_count / 3)
        
        agreement = 1.0 - abs(final_score - anomaly_score)
        
        threshold_distance = abs(final_score - threshold)
        score_separation = min(1.0, threshold_distance * 5)
        
        confidence = (rule_consistency * 0.35 + agreement * 0.35 + score_separation * 0.3)
        return min(1.0, max(0.0, confidence))

    def batch_assess(self, click_logs: List[ClickLog], features_list: List[ClickFeatures]) -> List[FraudAssessmentV2]:
        assessments = []
        for click_log, features in zip(click_logs, features_list):
            assessments.append(self.assess(click_log, features))
        return assessments

    def get_publisher_stats(self, publisher_id: str) -> Dict:
        return self.threshold_manager.get_publisher_stats(publisher_id)

    def get_all_publisher_stats(self) -> Dict[str, Dict]:
        return self.threshold_manager.get_all_publisher_stats()

    def update_weights(self, rule_weight: float, anomaly_weight: float):
        if abs(rule_weight + anomaly_weight - 1.0) > 0.001:
            raise ValueError("权重之和必须等于1")
        self.rule_weight = rule_weight
        self.anomaly_weight = anomaly_weight

    def get_statistics(self) -> Dict[str, Any]:
        return {
            'rule_weight': self.rule_weight,
            'anomaly_weight': self.anomaly_weight,
            'dynamic_threshold_enabled': self.threshold_manager.enabled,
            'graded_penalty_enabled': self.penalty_manager.enabled,
            'model_trained': self.anomaly_detector.is_trained,
            'publisher_thresholds': self.get_all_publisher_stats()
        }


class ActionExecutorV2:
    def __init__(self, redis_store=None):
        self.redis_store = redis_store

    def execute(self, assessment: FraudAssessmentV2, ip: str, device_id: str) -> Dict[str, Any]:
        action = assessment.penalty_level.action
        
        handlers = {
            ActionType.OBSERVE: self._handle_observe,
            ActionType.DISCOUNT: self._handle_discount,
            ActionType.HEAVY_DISCOUNT: self._handle_heavy_discount,
            ActionType.BLOCK: self._handle_block
        }
        
        handler = handlers.get(action, self._handle_observe)
        return handler(assessment, ip, device_id)

    def _handle_observe(self, assessment: FraudAssessmentV2, ip: str, device_id: str) -> Dict[str, Any]:
        if self.redis_store and assessment.is_fraud:
            self.redis_store.record_fraud_alert(
                assessment.click_id,
                assessment.final_fraud_score,
                assessment.triggered_rules,
                assessment.details
            )
        return {
            'action': 'observe',
            'action_name': assessment.penalty_level.name,
            'status': 'observed',
            'message': '标记观察，记录日志',
            'click_id': assessment.click_id,
            'penalty_rate': assessment.penalty_level.penalty_rate,
            'fraud_score': assessment.final_fraud_score
        }

    def _handle_discount(self, assessment: FraudAssessmentV2, ip: str, device_id: str) -> Dict[str, Any]:
        duration = assessment.penalty_manager.get_penalty_duration(ActionType.DISCOUNT) if hasattr(assessment, 'penalty_manager') else 3600
        
        if self.redis_store:
            self.redis_store.record_fraud_alert(
                assessment.click_id,
                assessment.final_fraud_score,
                assessment.triggered_rules,
                assessment.details
            )
        
        return {
            'action': 'discount',
            'action_name': assessment.penalty_level.name,
            'status': 'discounted',
            'message': f'流量扣量{assessment.penalty_level.penalty_rate * 100:.0f}%计费',
            'click_id': assessment.click_id,
            'penalty_rate': assessment.penalty_level.penalty_rate,
            'penalty_duration': duration,
            'fraud_score': assessment.final_fraud_score,
            'discount_reasons': assessment.triggered_rules
        }

    def _handle_heavy_discount(self, assessment: FraudAssessmentV2, ip: str, device_id: str) -> Dict[str, Any]:
        duration = assessment.penalty_manager.get_penalty_duration(ActionType.HEAVY_DISCOUNT) if hasattr(assessment, 'penalty_manager') else 7200
        
        if self.redis_store:
            self.redis_store.record_fraud_alert(
                assessment.click_id,
                assessment.final_fraud_score,
                assessment.triggered_rules,
                assessment.details
            )
        
        return {
            'action': 'heavy_discount',
            'action_name': assessment.penalty_level.name,
            'status': 'heavy_discounted',
            'message': f'流量扣量{assessment.penalty_level.penalty_rate * 100:.0f}%计费',
            'click_id': assessment.click_id,
            'penalty_rate': assessment.penalty_level.penalty_rate,
            'penalty_duration': duration,
            'fraud_score': assessment.final_fraud_score,
            'discount_reasons': assessment.triggered_rules
        }

    def _handle_block(self, assessment: FraudAssessmentV2, ip: str, device_id: str) -> Dict[str, Any]:
        duration = assessment.penalty_manager.get_penalty_duration(ActionType.BLOCK) if hasattr(assessment, 'penalty_manager') else 86400
        
        if self.redis_store:
            self.redis_store.block_ip(ip, duration_seconds=duration, reason=assessment.action_reason)
            self.redis_store.block_device(device_id, duration_seconds=duration, reason=assessment.action_reason)
            self.redis_store.record_fraud_alert(
                assessment.click_id,
                assessment.final_fraud_score,
                assessment.triggered_rules,
                assessment.details
            )
        
        return {
            'action': 'block',
            'action_name': assessment.penalty_level.name,
            'status': 'blocked',
            'message': '直接拦截，不计费',
            'click_id': assessment.click_id,
            'penalty_rate': assessment.penalty_level.penalty_rate,
            'penalty_duration': duration,
            'fraud_score': assessment.final_fraud_score,
            'block_reasons': assessment.triggered_rules,
            'repeat_offense_count': assessment.repeat_offense_count,
            'is_escalated': assessment.is_escalated
        }
