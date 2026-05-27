import time
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass, field
from enum import Enum
import yaml

from .data_models import ClickLog, ClickFeatures
from .rule_engine import RuleEngine, RuleResult
from .anomaly_detector import AnomalyDetector


class FraudAction(Enum):
    ALLOW = "allow"
    FLAG = "flag"
    BLOCK = "block"
    CHALLENGE = "challenge"


@dataclass
class FraudAssessment:
    click_id: str
    timestamp: float
    final_fraud_score: float
    rule_based_score: float
    anomaly_score: float
    is_fraud: bool
    triggered_rules: List[str]
    rule_details: Dict[str, Dict]
    top_anomaly_features: List[Tuple[str, float]]
    recommended_action: FraudAction
    action_reason: str
    confidence: float
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            'click_id': self.click_id,
            'timestamp': self.timestamp,
            'final_fraud_score': self.final_fraud_score,
            'rule_based_score': self.rule_based_score,
            'anomaly_score': self.anomaly_score,
            'is_fraud': self.is_fraud,
            'triggered_rules': self.triggered_rules,
            'rule_details': self.rule_details,
            'top_anomaly_features': [list(item) for item in self.top_anomaly_features],
            'recommended_action': self.recommended_action.value,
            'action_reason': self.action_reason,
            'confidence': self.confidence,
            'details': self.details
        }


class FraudScorer:
    def __init__(self, config_path: str = 'config/config.yaml'):
        self.config = self._load_config(config_path)
        self.fraud_threshold = self.config['output'].get('fraud_threshold', 0.7)
        self.rule_engine = RuleEngine(config_path)
        self.anomaly_detector = AnomalyDetector(config_path)
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

    def assess(self, click_log: ClickLog, features: ClickFeatures) -> FraudAssessment:
        rule_results = self.rule_engine.evaluate_all_rules(click_log, features)
        rule_based_score = self.rule_engine.get_aggregated_rule_score(rule_results)
        
        is_anomaly, anomaly_score, feature_contributions = self.anomaly_detector.predict(features)
        top_features = self.anomaly_detector.get_top_anomaly_features(features, top_k=5)
        
        final_score = self._fuse_scores(rule_based_score, anomaly_score)
        
        triggered_rules = [r.rule_name for r in rule_results if r.triggered]
        rule_details = {r.rule_name: {'score': r.fraud_score, 'reason': r.reason, 'details': r.details} 
                       for r in rule_results if r.triggered}
        
        is_fraud = final_score >= self.fraud_threshold
        
        action, action_reason = self._determine_action(final_score, triggered_rules, is_anomaly)
        
        confidence = self._calculate_confidence(rule_results, anomaly_score, final_score)
        
        return FraudAssessment(
            click_id=click_log.click_id,
            timestamp=time.time(),
            final_fraud_score=final_score,
            rule_based_score=rule_based_score,
            anomaly_score=anomaly_score,
            is_fraud=is_fraud,
            triggered_rules=triggered_rules,
            rule_details=rule_details,
            top_anomaly_features=top_features,
            recommended_action=action,
            action_reason=action_reason,
            confidence=confidence,
            details={
                'feature_contributions': feature_contributions,
                'is_anomaly_from_model': is_anomaly
            }
        )

    def _fuse_scores(self, rule_score: float, anomaly_score: float) -> float:
        if rule_score > 0.8 and anomaly_score > 0.8:
            return max(rule_score, anomaly_score) * 1.05
        
        weighted_score = (rule_score * self.rule_weight) + (anomaly_score * self.anomaly_weight)
        
        if rule_score > 0.5 and anomaly_score > 0.5:
            weighted_score = min(1.0, weighted_score * 1.1)
        
        return min(1.0, weighted_score)

    def _determine_action(self, final_score: float, triggered_rules: List[str], is_anomaly: bool) -> Tuple[FraudAction, str]:
        high_risk_rules = ['high_frequency_ip', 'fixed_interval_ip', 'user_agent_anomaly']
        has_high_risk = any(rule in triggered_rules for rule in high_risk_rules)
        
        if final_score >= 0.9 or (has_high_risk and final_score >= 0.7):
            return FraudAction.BLOCK, "高风险欺诈检测，立即阻止"
        elif final_score >= 0.7:
            return FraudAction.CHALLENGE, "中等风险，需要额外验证"
        elif final_score >= 0.5 or (is_anomaly and len(triggered_rules) > 0):
            return FraudAction.FLAG, "低风险，标记供人工审核"
        else:
            return FraudAction.ALLOW, "正常流量，允许通过"

    def _calculate_confidence(self, rule_results: List[RuleResult], anomaly_score: float, final_score: float) -> float:
        triggered_count = len([r for r in rule_results if r.triggered])
        total_rules = len(rule_results)
        
        rule_consistency = 1.0 if triggered_count == 0 else min(1.0, triggered_count / 3)
        
        agreement = 1.0 - abs(final_score - anomaly_score)
        
        score_separation = min(1.0, abs(final_score - 0.5) * 2)
        
        confidence = (rule_consistency * 0.35 + agreement * 0.35 + score_separation * 0.3)
        return min(1.0, max(0.0, confidence))

    def batch_assess(self, click_logs: List[ClickLog], features_list: List[ClickFeatures]) -> List[FraudAssessment]:
        assessments = []
        for click_log, features in zip(click_logs, features_list):
            assessments.append(self.assess(click_log, features))
        return assessments

    def update_weights(self, rule_weight: float, anomaly_weight: float):
        if abs(rule_weight + anomaly_weight - 1.0) > 0.001:
            raise ValueError("权重之和必须等于1")
        self.rule_weight = rule_weight
        self.anomaly_weight = anomaly_weight

    def get_statistics(self) -> Dict[str, Any]:
        return {
            'rule_weight': self.rule_weight,
            'anomaly_weight': self.anomaly_weight,
            'fraud_threshold': self.fraud_threshold,
            'model_trained': self.anomaly_detector.is_trained
        }

    def retrain_model(self, features_list: List[ClickFeatures], save: bool = True):
        self.anomaly_detector.train(features_list)
        if save:
            self.anomaly_detector.save_model()


class ActionExecutor:
    def __init__(self, redis_store=None):
        self.redis_store = redis_store
        self.action_handlers = {
            FraudAction.ALLOW: self._handle_allow,
            FraudAction.FLAG: self._handle_flag,
            FraudAction.BLOCK: self._handle_block,
            FraudAction.CHALLENGE: self._handle_challenge
        }

    def execute(self, assessment: FraudAssessment, ip: str, device_id: str) -> Dict[str, Any]:
        handler = self.action_handlers.get(assessment.recommended_action, self._handle_allow)
        return handler(assessment, ip, device_id)

    def _handle_allow(self, assessment: FraudAssessment, ip: str, device_id: str) -> Dict[str, Any]:
        return {
            'action': 'allow',
            'status': 'success',
            'message': '请求已允许',
            'click_id': assessment.click_id
        }

    def _handle_flag(self, assessment: FraudAssessment, ip: str, device_id: str) -> Dict[str, Any]:
        if self.redis_store:
            self.redis_store.record_fraud_alert(
                assessment.click_id,
                assessment.final_fraud_score,
                assessment.triggered_rules,
                assessment.details
            )
        return {
            'action': 'flag',
            'status': 'flagged',
            'message': '请求已标记，需人工审核',
            'click_id': assessment.click_id,
            'flag_reasons': assessment.triggered_rules
        }

    def _handle_block(self, assessment: FraudAssessment, ip: str, device_id: str) -> Dict[str, Any]:
        if self.redis_store:
            self.redis_store.block_ip(ip, duration_seconds=3600, reason=f"欺诈检测: {assessment.action_reason}")
            self.redis_store.block_device(device_id, duration_seconds=7200, reason=f"欺诈检测: {assessment.action_reason}")
            self.redis_store.record_fraud_alert(
                assessment.click_id,
                assessment.final_fraud_score,
                assessment.triggered_rules,
                assessment.details
            )
        return {
            'action': 'block',
            'status': 'blocked',
            'message': '请求已阻止',
            'click_id': assessment.click_id,
            'block_duration': 'IP: 1小时, 设备: 2小时',
            'block_reasons': assessment.triggered_rules
        }

    def _handle_challenge(self, assessment: FraudAssessment, ip: str, device_id: str) -> Dict[str, Any]:
        if self.redis_store:
            self.redis_store.record_fraud_alert(
                assessment.click_id,
                assessment.final_fraud_score,
                assessment.triggered_rules,
                assessment.details
            )
        return {
            'action': 'challenge',
            'status': 'challenge_required',
            'message': '需要额外验证',
            'click_id': assessment.click_id,
            'challenge_type': 'captcha',
            'challenge_reasons': assessment.triggered_rules
        }
