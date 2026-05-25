import numpy as np
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from collections import defaultdict
from datetime import datetime, timedelta


@dataclass
class UserHistory:
    user_id: str
    total_comments: int = 0
    total_likes: int = 0
    total_reports: int = 0
    average_likes_per_comment: float = 0.0
    report_rate: float = 0.0
    comment_history: List[Dict] = field(default_factory=list)
    account_age_days: int = 365
    is_verified: bool = False
    level: int = 1


@dataclass
class ReputationResult:
    overall_reputation_score: float
    trustworthiness_score: float
    influence_score: float
    consistency_score: float
    risk_score: float
    evidence: List[str]
    detailed_metrics: Dict


class UserReputationAnalyzer:
    def __init__(self):
        self._init_weight_config()
        self._init_thresholds()
    
    def _init_weight_config(self):
        self.weights = {
            'trustworthiness': 0.40,
            'influence': 0.30,
            'consistency': 0.20,
            'risk': 0.10
        }
        
        self.trustworthiness_weights = {
            'report_rate': 0.35,
            'verified_bonus': 0.20,
            'account_age': 0.15,
            'level': 0.15,
            'historical_quality': 0.15
        }
        
        self.influence_weights = {
            'total_likes': 0.40,
            'avg_likes_per_comment': 0.35,
            'total_comments': 0.25
        }
        
        self.consistency_weights = {
            'rating_consistency': 0.40,
            'length_consistency': 0.30,
            'quality_consistency': 0.30
        }
    
    def _init_thresholds(self):
        self.thresholds = {
            'report_rate_high_risk': 0.15,
            'report_rate_medium_risk': 0.05,
            'avg_likes_high': 20,
            'avg_likes_medium': 5,
            'total_comments_active': 50,
            'total_comments_new': 5,
            'account_age_new': 30,
            'account_age_mature': 365
        }
    
    def analyze(self, user_history: UserHistory, text_quality_scores: Optional[List[float]] = None) -> ReputationResult:
        if text_quality_scores is None:
            text_quality_scores = []
        
        trustworthiness_score, trust_evidence = self._calculate_trustworthiness(user_history, text_quality_scores)
        influence_score, influence_evidence = self._calculate_influence(user_history)
        consistency_score, consistency_evidence = self._calculate_consistency(user_history, text_quality_scores)
        risk_score, risk_evidence = self._calculate_risk(user_history)
        
        overall_reputation_score = (
            trustworthiness_score * self.weights['trustworthiness'] +
            influence_score * self.weights['influence'] +
            consistency_score * self.weights['consistency'] +
            (1 - risk_score) * self.weights['risk']
        )
        
        overall_reputation_score = max(0.0, min(1.0, overall_reputation_score))
        
        evidence = trust_evidence + influence_evidence + consistency_evidence + risk_evidence
        
        detailed_metrics = {
            'trustworthiness': {
                'score': trustworthiness_score,
                'components': self._get_trustworthiness_components(user_history, text_quality_scores)
            },
            'influence': {
                'score': influence_score,
                'components': self._get_influence_components(user_history)
            },
            'consistency': {
                'score': consistency_score,
                'components': self._get_consistency_components(user_history, text_quality_scores)
            },
            'risk': {
                'score': risk_score,
                'components': self._get_risk_components(user_history)
            },
            'user_statistics': {
                'total_comments': user_history.total_comments,
                'total_likes': user_history.total_likes,
                'total_reports': user_history.total_reports,
                'avg_likes_per_comment': user_history.average_likes_per_comment,
                'report_rate': user_history.report_rate,
                'account_age_days': user_history.account_age_days,
                'is_verified': user_history.is_verified,
                'level': user_history.level
            }
        }
        
        return ReputationResult(
            overall_reputation_score=round(overall_reputation_score, 4),
            trustworthiness_score=round(trustworthiness_score, 4),
            influence_score=round(influence_score, 4),
            consistency_score=round(consistency_score, 4),
            risk_score=round(risk_score, 4),
            evidence=evidence,
            detailed_metrics=detailed_metrics
        )
    
    def _calculate_trustworthiness(self, user_history: UserHistory, text_quality_scores: List[float]) -> Tuple[float, List[str]]:
        evidence = []
        components = self._get_trustworthiness_components(user_history, text_quality_scores)
        
        report_rate_score = components['report_rate_score']
        verified_bonus = components['verified_bonus']
        account_age_score = components['account_age_score']
        level_score = components['level_score']
        historical_quality_score = components['historical_quality_score']
        
        trustworthiness_score = (
            report_rate_score * self.trustworthiness_weights['report_rate'] +
            verified_bonus * self.trustworthiness_weights['verified_bonus'] +
            account_age_score * self.trustworthiness_weights['account_age'] +
            level_score * self.trustworthiness_weights['level'] +
            historical_quality_score * self.trustworthiness_weights['historical_quality']
        )
        
        if user_history.total_reports == 0:
            evidence.append("用户历史无被举报记录，信用良好")
        elif user_history.report_rate < self.thresholds['report_rate_medium_risk']:
            evidence.append(f"举报率{user_history.report_rate:.1%}，处于正常范围")
        elif user_history.report_rate < self.thresholds['report_rate_high_risk']:
            evidence.append(f"举报率{user_history.report_rate:.1%}，略高于平均值")
        else:
            evidence.append(f"举报率{user_history.report_rate:.1%}，存在较高风险")
        
        if user_history.is_verified:
            evidence.append("账号已实名认证，可信度提升")
        else:
            evidence.append("账号未实名认证，可信度一般")
        
        if user_history.account_age_days >= self.thresholds['account_age_mature']:
            evidence.append(f"账号注册{user_history.account_age_days}天，属于成熟账号")
        elif user_history.account_age_days >= self.thresholds['account_age_new']:
            evidence.append(f"账号注册{user_history.account_age_days}天，属于成长账号")
        else:
            evidence.append(f"账号注册{user_history.account_age_days}天，属于新账号")
        
        evidence.append(f"用户等级: Lv.{user_history.level}")
        
        if historical_quality_score >= 0.7:
            evidence.append("历史评论质量良好")
        elif historical_quality_score >= 0.4:
            evidence.append("历史评论质量中等")
        else:
            evidence.append("历史评论质量有待提升")
        
        trustworthiness_score = max(0.0, min(1.0, trustworthiness_score))
        
        return trustworthiness_score, evidence
    
    def _get_trustworthiness_components(self, user_history: UserHistory, text_quality_scores: List[float]) -> Dict:
        if user_history.total_comments > 0:
            report_rate = user_history.total_reports / user_history.total_comments
        else:
            report_rate = 0
        
        if report_rate >= self.thresholds['report_rate_high_risk']:
            report_rate_score = 0.0
        elif report_rate >= self.thresholds['report_rate_medium_risk']:
            report_rate_score = 0.5 - (report_rate - self.thresholds['report_rate_medium_risk']) / \
                              (self.thresholds['report_rate_high_risk'] - self.thresholds['report_rate_medium_risk']) * 0.5
        else:
            report_rate_score = 1.0 - report_rate / self.thresholds['report_rate_medium_risk'] * 0.5
        
        report_rate_score = max(0.0, min(1.0, report_rate_score))
        
        verified_bonus = 1.0 if user_history.is_verified else 0.3
        
        if user_history.account_age_days >= self.thresholds['account_age_mature']:
            account_age_score = 1.0
        elif user_history.account_age_days >= self.thresholds['account_age_new']:
            account_age_score = 0.5 + (user_history.account_age_days - self.thresholds['account_age_new']) / \
                                (self.thresholds['account_age_mature'] - self.thresholds['account_age_new']) * 0.5
        else:
            account_age_score = 0.3 + user_history.account_age_days / self.thresholds['account_age_new'] * 0.2
        
        level_score = min(1.0, user_history.level / 10.0)
        
        if text_quality_scores and len(text_quality_scores) > 0:
            historical_quality_score = float(np.mean(text_quality_scores))
        else:
            historical_quality_score = 0.5
        
        return {
            'report_rate_score': round(report_rate_score, 4),
            'verified_bonus': round(verified_bonus, 4),
            'account_age_score': round(account_age_score, 4),
            'level_score': round(level_score, 4),
            'historical_quality_score': round(historical_quality_score, 4)
        }
    
    def _calculate_influence(self, user_history: UserHistory) -> Tuple[float, List[str]]:
        evidence = []
        components = self._get_influence_components(user_history)
        
        total_likes_score = components['total_likes_score']
        avg_likes_score = components['avg_likes_score']
        total_comments_score = components['total_comments_score']
        
        influence_score = (
            total_likes_score * self.influence_weights['total_likes'] +
            avg_likes_score * self.influence_weights['avg_likes_per_comment'] +
            total_comments_score * self.influence_weights['total_comments']
        )
        
        evidence.append(f"累计获赞: {user_history.total_likes}次")
        
        if user_history.average_likes_per_comment >= self.thresholds['avg_likes_high']:
            evidence.append(f"平均每条获赞{user_history.average_likes_per_comment:.1f}，影响力较大")
        elif user_history.average_likes_per_comment >= self.thresholds['avg_likes_medium']:
            evidence.append(f"平均每条获赞{user_history.average_likes_per_comment:.1f}，有一定影响力")
        else:
            evidence.append(f"平均每条获赞{user_history.average_likes_per_comment:.1f}，影响力一般")
        
        if user_history.total_comments >= self.thresholds['total_comments_active']:
            evidence.append(f"累计评论{user_history.total_comments}条，属于活跃用户")
        elif user_history.total_comments >= self.thresholds['total_comments_new']:
            evidence.append(f"累计评论{user_history.total_comments}条，属于普通用户")
        else:
            evidence.append(f"累计评论{user_history.total_comments}条，属于新用户")
        
        influence_score = max(0.0, min(1.0, influence_score))
        
        return influence_score, evidence
    
    def _get_influence_components(self, user_history: UserHistory) -> Dict:
        total_likes_score = min(1.0, np.log1p(user_history.total_likes) / np.log1p(1000))
        avg_likes_score = min(1.0, np.log1p(user_history.average_likes_per_comment) / np.log1p(50))
        total_comments_score = min(1.0, np.log1p(user_history.total_comments) / np.log1p(200))
        
        return {
            'total_likes_score': round(total_likes_score, 4),
            'avg_likes_score': round(avg_likes_score, 4),
            'total_comments_score': round(total_comments_score, 4)
        }
    
    def _calculate_consistency(self, user_history: UserHistory, text_quality_scores: List[float]) -> Tuple[float, List[str]]:
        evidence = []
        components = self._get_consistency_components(user_history, text_quality_scores)
        
        rating_consistency = components['rating_consistency']
        length_consistency = components['length_consistency']
        quality_consistency = components['quality_consistency']
        
        consistency_score = (
            rating_consistency * self.consistency_weights['rating_consistency'] +
            length_consistency * self.consistency_weights['length_consistency'] +
            quality_consistency * self.consistency_weights['quality_consistency']
        )
        
        if len(user_history.comment_history) >= 5:
            if rating_consistency >= 0.7:
                evidence.append("用户评分风格一致，评价标准稳定")
            elif rating_consistency >= 0.4:
                evidence.append("用户评分风格基本一致")
            else:
                evidence.append("用户评分波动较大，可能存在情绪化评价")
            
            if quality_consistency >= 0.7:
                evidence.append("历史评论质量稳定，输出一致性好")
            elif quality_consistency >= 0.4:
                evidence.append("历史评论质量基本稳定")
            else:
                evidence.append("历史评论质量波动较大")
        else:
            evidence.append("历史评论数据不足，暂无法评估一致性")
            consistency_score = 0.5
        
        consistency_score = max(0.0, min(1.0, consistency_score))
        
        return consistency_score, evidence
    
    def _get_consistency_components(self, user_history: UserHistory, text_quality_scores: List[float]) -> Dict:
        if len(user_history.comment_history) >= 2:
            ratings = [c.get('rating', 3) for c in user_history.comment_history if 'rating' in c]
            if len(ratings) >= 2:
                rating_std = np.std(ratings)
                max_std = 2.0
                rating_consistency = max(0.0, 1.0 - rating_std / max_std)
            else:
                rating_consistency = 0.5
            
            lengths = [len(c.get('text', '')) for c in user_history.comment_history if 'text' in c]
            if len(lengths) >= 2:
                length_cv = np.std(lengths) / (np.mean(lengths) + 1e-10)
                length_consistency = max(0.0, 1.0 - min(length_cv, 1.0))
            else:
                length_consistency = 0.5
        else:
            rating_consistency = 0.5
            length_consistency = 0.5
        
        if len(text_quality_scores) >= 2:
            quality_std = np.std(text_quality_scores)
            quality_consistency = max(0.0, 1.0 - quality_std / 0.5)
        else:
            quality_consistency = 0.5
        
        return {
            'rating_consistency': round(rating_consistency, 4),
            'length_consistency': round(length_consistency, 4),
            'quality_consistency': round(quality_consistency, 4)
        }
    
    def _calculate_risk(self, user_history: UserHistory) -> Tuple[float, List[str]]:
        evidence = []
        components = self._get_risk_components(user_history)
        
        risk_score = max(components.values()) if components else 0.0
        
        risk_flags = []
        
        if user_history.report_rate >= self.thresholds['report_rate_high_risk']:
            risk_flags.append(f"高举报率 ({user_history.report_rate:.1%})")
        
        if user_history.account_age_days < self.thresholds['account_age_new'] and user_history.total_comments < 3:
            risk_flags.append("新账号低活跃度")
        
        if user_history.total_comments > 0 and user_history.total_reports >= 3:
            risk_flags.append(f"多次被举报 ({user_history.total_reports}次)")
        
        if len(user_history.comment_history) >= 3:
            time_diffs = []
            for i in range(1, len(user_history.comment_history)):
                t1 = user_history.comment_history[i-1].get('timestamp', datetime.now())
                t2 = user_history.comment_history[i].get('timestamp', datetime.now())
                if isinstance(t1, datetime) and isinstance(t2, datetime):
                    diff = abs((t2 - t1).total_seconds())
                    time_diffs.append(diff)
            
            if time_diffs and np.mean(time_diffs) < 60:
                risk_flags.append("评论间隔过短，疑似机器发布")
        
        if risk_flags:
            evidence.append("风险标记: " + ", ".join(risk_flags))
        else:
            evidence.append("未检测到明显风险信号")
        
        if risk_score >= 0.7:
            evidence.append("高风险用户，需重点关注")
        elif risk_score >= 0.4:
            evidence.append("中风险用户，可适当关注")
        else:
            evidence.append("低风险用户，信用良好")
        
        risk_score = max(0.0, min(1.0, risk_score))
        
        return risk_score, evidence
    
    def _get_risk_components(self, user_history: UserHistory) -> Dict:
        report_risk = min(1.0, user_history.report_rate / self.thresholds['report_rate_high_risk'])
        
        if user_history.account_age_days < self.thresholds['account_age_new']:
            age_risk = 1.0 - user_history.account_age_days / self.thresholds['account_age_new'] * 0.5
        else:
            age_risk = max(0.0, 0.5 - (user_history.account_age_days - self.thresholds['account_age_new']) / 
                          (self.thresholds['account_age_mature'] - self.thresholds['account_age_new']) * 0.5)
        
        if user_history.total_comments > 0:
            report_count_risk = min(1.0, user_history.total_reports / 5.0)
        else:
            report_count_risk = 0.3
        
        history_length = len(user_history.comment_history)
        if history_length >= 5:
            burst_risk = 0.0
            time_diffs = []
            for i in range(1, history_length):
                t1 = user_history.comment_history[i-1].get('timestamp', datetime.now())
                t2 = user_history.comment_history[i].get('timestamp', datetime.now())
                if isinstance(t1, datetime) and isinstance(t2, datetime):
                    diff = abs((t2 - t1).total_seconds())
                    time_diffs.append(diff)
            
            if time_diffs:
                short_interval_count = sum(1 for d in time_diffs if d < 60)
                burst_risk = min(1.0, short_interval_count / len(time_diffs))
        else:
            burst_risk = 0.2
        
        return {
            'report_rate_risk': round(report_risk, 4),
            'account_age_risk': round(age_risk, 4),
            'report_count_risk': round(report_count_risk, 4),
            'burst_posting_risk': round(burst_risk, 4)
        }
    
    def generate_user_profile(self, user_history: UserHistory) -> Dict:
        if user_history.total_comments >= 100 and user_history.average_likes_per_comment >= 10:
            user_type = '核心用户'
        elif user_history.total_comments >= 50:
            user_type = '活跃用户'
        elif user_history.total_comments >= 10:
            user_type = '普通用户'
        else:
            user_type = '新用户'
        
        if user_history.report_rate >= 0.1:
            risk_level = '高风险'
        elif user_history.report_rate >= 0.05:
            risk_level = '中风险'
        else:
            risk_level = '低风险'
        
        return {
            'user_type': user_type,
            'risk_level': risk_level,
            'trust_level': self._get_trust_level(user_history),
            'influence_level': self._get_influence_level(user_history)
        }
    
    def _get_trust_level(self, user_history: UserHistory) -> str:
        score = 0
        
        if user_history.is_verified:
            score += 2
        if user_history.account_age_days >= 365:
            score += 2
        elif user_history.account_age_days >= 180:
            score += 1
        if user_history.level >= 5:
            score += 2
        elif user_history.level >= 3:
            score += 1
        if user_history.total_reports == 0 and user_history.total_comments >= 10:
            score += 2
        elif user_history.report_rate < 0.05:
            score += 1
        
        if score >= 6:
            return '极高信任'
        elif score >= 4:
            return '高信任'
        elif score >= 2:
            return '中等信任'
        else:
            return '低信任'
    
    def _get_influence_level(self, user_history: UserHistory) -> str:
        score = 0
        
        if user_history.total_likes >= 1000:
            score += 3
        elif user_history.total_likes >= 100:
            score += 2
        elif user_history.total_likes >= 20:
            score += 1
        if user_history.average_likes_per_comment >= 20:
            score += 3
        elif user_history.average_likes_per_comment >= 10:
            score += 2
        elif user_history.average_likes_per_comment >= 5:
            score += 1
        if user_history.total_comments >= 200:
            score += 2
        elif user_history.total_comments >= 50:
            score += 1
        
        if score >= 6:
            return '极具影响力'
        elif score >= 4:
            return '有影响力'
        elif score >= 2:
            return '普通影响力'
        else:
            return '影响力较小'
