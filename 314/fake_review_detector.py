#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
虚假评论检测模块
识别三类虚假评论：
1. 刷单评论：商家自刷好评
2. 水军评论：批量发布的相似评论
3. 竞品恶意评论：竞争对手发布的恶意差评
"""

import re
import json
import math
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Optional, Tuple, Any
from collections import Counter, defaultdict
from datetime import datetime, timedelta
import hashlib


class FakeReviewType(Enum):
    LEGITIMATE = "legitimate"
    BRUSHING = "brushing"
    WATER_ARMY = "water_army"
    COMPETITOR_MALICIOUS = "competitor_malicious"


class SuspicionLevel(Enum):
    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class ReviewForDetection:
    review_id: str
    user_id: str
    product_id: str
    content: str
    rating: int
    timestamp: datetime
    ip_address: Optional[str] = None
    device_id: Optional[str] = None
    user_account_age_days: Optional[int] = None
    user_total_reviews: Optional[int] = None
    user_average_rating: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DetectionEvidence:
    feature_name: str
    feature_value: float
    threshold: float
    description: str
    impact: float


@dataclass
class FakeReviewDetectionResult:
    review_id: str
    is_fake: bool
    fake_type: FakeReviewType
    suspicion_level: SuspicionLevel
    suspicion_score: float
    evidence: List[DetectionEvidence]
    brushing_score: float
    water_army_score: float
    competitor_score: float
    details: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return {
            'review_id': self.review_id,
            'is_fake': self.is_fake,
            'fake_type': self.fake_type.value,
            'suspicion_level': self.suspicion_level.value,
            'suspicion_score': self.suspicion_score,
            'brushing_score': self.brushing_score,
            'water_army_score': self.water_army_score,
            'competitor_score': self.competitor_score,
            'evidence': [
                {
                    'feature_name': e.feature_name,
                    'feature_value': e.feature_value,
                    'threshold': e.threshold,
                    'description': e.description,
                    'impact': e.impact
                } for e in self.evidence
            ]
        }


@dataclass
class GroupDetectionResult:
    group_id: str
    suspicious_users: List[str]
    suspicious_reviews: List[str]
    suspicion_score: float
    evidence: List[str]
    detection_time: datetime = field(default_factory=datetime.now)


class FakeReviewDetector:
    def __init__(self, threshold: float = 0.7):
        self.threshold = threshold
        self.brushing_keywords = [
            '好评', '好评返现', '返现', '返红包', '优惠券',
            '商家给力', '服务好', '发货快', '物流快',
            '超级赞', '太棒了', '非常好', '特别好',
            '物美价廉', '性价比高', '值得购买', '推荐购买'
        ]
        self.competitor_brands_patterns = [
            r'(?:华为|小米|苹果|三星|OPPO|vivo|荣耀|真我|iQOO)',
            r'(?:耐克|阿迪|安踏|李宁|特步|361度)',
            r'(?:奔驰|宝马|奥迪|特斯拉|比亚迪|蔚来|理想)',
            r'(?:可口可乐|百事可乐|农夫山泉|康师傅|统一)'
        ]
        self.suspicious_phrases = [
            '垃圾', '骗子', '不要买', '千万别买', '太差了',
            '假货', '山寨', '骗子公司', '黑心商家',
            '不如', '比不上', '还是', '买', '更好'
        ]
        self.template_patterns = [
            r'^.{5,15}[，。！？].{5,15}[，。！？].{5,15}[，。！？]$',
            r'^[好棒赞].{2,5}[，。].{2,10}[，。].{2,10}$',
            r'^.{3,8}，.{3,8}，.{3,8}，.{3,8}$',
        ]

    def detect(
        self,
        review: ReviewForDetection,
        all_reviews: Optional[List[ReviewForDetection]] = None,
        user_reviews: Optional[List[ReviewForDetection]] = None
    ) -> FakeReviewDetectionResult:
        evidence = []
        brushing_score = 0.0
        water_army_score = 0.0
        competitor_score = 0.0

        brushing_score, ev_brush = self._check_brushing_features(review)
        evidence.extend(ev_brush)

        if all_reviews and len(all_reviews) > 1:
            water_army_score, ev_water = self._check_water_army_features(review, all_reviews)
            evidence.extend(ev_water)

        competitor_score, ev_comp = self._check_competitor_features(review)
        evidence.extend(ev_comp)

        if user_reviews and len(user_reviews) > 1:
            user_brush_score, ev_user_brush = self._check_user_brushing_pattern(review, user_reviews)
            brushing_score = max(brushing_score, user_brush_score)
            evidence.extend(ev_user_brush)

            user_comp_score, ev_user_comp = self._check_user_competitor_pattern(review, user_reviews)
            competitor_score = max(competitor_score, user_comp_score)
            evidence.extend(ev_user_comp)

        max_score = max(brushing_score, water_army_score, competitor_score)
        if max_score == brushing_score and brushing_score > 0.3:
            fake_type = FakeReviewType.BRUSHING
        elif max_score == water_army_score and water_army_score > 0.3:
            fake_type = FakeReviewType.WATER_ARMY
        elif max_score == competitor_score and competitor_score > 0.3:
            fake_type = FakeReviewType.COMPETITOR_MALICIOUS
        else:
            fake_type = FakeReviewType.LEGITIMATE

        is_fake = max_score >= self.threshold
        suspicion_level = self._get_suspicion_level(max_score)

        return FakeReviewDetectionResult(
            review_id=review.review_id,
            is_fake=is_fake,
            fake_type=fake_type,
            suspicion_level=suspicion_level,
            suspicion_score=max_score,
            evidence=evidence,
            brushing_score=brushing_score,
            water_army_score=water_army_score,
            competitor_score=competitor_score,
            details={
                'rating': review.rating,
                'content_length': len(review.content),
                'timestamp': review.timestamp.isoformat()
            }
        )

    def detect_group(self, reviews: List[ReviewForDetection]) -> List[GroupDetectionResult]:
        results = []
        ip_groups = defaultdict(list)
        for r in reviews:
            if r.ip_address:
                ip_groups[r.ip_address].append(r)

        for ip, group_reviews in ip_groups.items():
            if len(group_reviews) >= 3:
                result = self._analyze_ip_group(ip, group_reviews)
                if result:
                    results.append(result)

        content_groups = self._cluster_by_content_similarity(reviews)
        for cluster_id, cluster_reviews in content_groups.items():
            if len(cluster_reviews) >= 3:
                result = self._analyze_content_cluster(cluster_id, cluster_reviews)
                if result:
                    results.append(result)

        time_groups = self._cluster_by_time_burst(reviews)
        for time_id, time_reviews in time_groups.items():
            if len(time_reviews) >= 3:
                result = self._analyze_time_group(time_id, time_reviews)
                if result:
                    results.append(result)

        return results

    def _check_brushing_features(self, review: ReviewForDetection) -> Tuple[float, List[DetectionEvidence]]:
        score = 0.0
        evidence = []
        rating = review.rating
        if rating == 5:
            score += 0.20
            evidence.append(DetectionEvidence(
                'extreme_rating', rating, 5.0,
                '5星满分评价，刷单风险较高', 0.20
            ))
        elif rating == 1:
            score += 0.15
            evidence.append(DetectionEvidence(
                'extreme_rating', rating, 1.0,
                '1星极低评价，恶意差评风险较高', 0.15
            ))

        content = review.content
        content_len = len(content)
        if content_len < 15 and rating == 5:
            impact = 0.15
            score += impact
            evidence.append(DetectionEvidence(
                'short_content_5star', content_len, 15.0,
                f'极短5星好评（{content_len}字），刷单特征', impact
            ))

        keyword_matches = []
        for kw in self.brushing_keywords:
            if kw in content:
                keyword_matches.append(kw)
        if len(keyword_matches) >= 3:
            impact = min(0.25, len(keyword_matches) * 0.08)
            score += impact
            evidence.append(DetectionEvidence(
                'brushing_keywords', len(keyword_matches), 3.0,
                f'包含{len(keyword_matches)}个刷单关键词：{"、".join(keyword_matches)}', impact
            ))

        if content_len < 10 and len(keyword_matches) >= 2:
            impact = 0.20
            score += impact
            evidence.append(DetectionEvidence(
                'short_template', content_len, 10.0,
                '短文本+刷单关键词组合，典型刷单模板', impact
            ))

        for pattern in self.template_patterns:
            if re.match(pattern, content):
                impact = 0.15
                score += impact
                evidence.append(DetectionEvidence(
                    'template_pattern', 1.0, 0.5,
                    '文本结构符合常见刷单模板特征', impact
                ))
                break

        if review.user_account_age_days is not None and review.user_account_age_days < 30:
            impact = 0.10
            score += impact
            evidence.append(DetectionEvidence(
                'new_account', review.user_account_age_days, 30.0,
                f'账号创建仅{review.user_account_age_days}天，新账号刷单风险高', impact
            ))

        if review.user_total_reviews is not None and review.user_total_reviews < 5:
            impact = 0.08
            score += impact
            evidence.append(DetectionEvidence(
                'low_activity', review.user_total_reviews, 5.0,
                f'用户历史评论仅{review.user_total_reviews}条，活跃度低', impact
            ))

        if review.user_average_rating is not None and review.user_average_rating >= 4.8:
            impact = 0.12
            score += impact
            evidence.append(DetectionEvidence(
                'high_avg_rating', review.user_average_rating, 4.8,
                f'用户平均评分{review.user_average_rating:.1f}，普遍偏高', impact
            ))

        return min(score, 1.0), evidence

    def _check_water_army_features(
        self,
        review: ReviewForDetection,
        all_reviews: List[ReviewForDetection]
    ) -> Tuple[float, List[DetectionEvidence]]:
        score = 0.0
        evidence = []

        if review.ip_address:
            same_ip_count = sum(
                1 for r in all_reviews
                if r.ip_address == review.ip_address and r.review_id != review.review_id
            )
            if same_ip_count >= 3:
                impact = min(0.30, same_ip_count * 0.10)
                score += impact
                evidence.append(DetectionEvidence(
                    'same_ip_cluster', same_ip_count, 3.0,
                    f'同一IP下有{same_ip_count}个账号同时评论，水军特征', impact
                ))

        if review.device_id:
            same_device_count = sum(
                1 for r in all_reviews
                if r.device_id == review.device_id and r.review_id != review.review_id
            )
            if same_device_count >= 2:
                impact = 0.25
                score += impact
                evidence.append(DetectionEvidence(
                    'same_device_cluster', same_device_count, 2.0,
                    f'同一设备发布{same_device_count}个账号评论，水军特征', impact
                ))

        time_window = timedelta(hours=1)
        same_time_count = sum(
            1 for r in all_reviews
            if abs((r.timestamp - review.timestamp).total_seconds()) < time_window.total_seconds()
            and r.review_id != review.review_id
        )
        if same_time_count >= 5:
            impact = min(0.25, same_time_count * 0.05)
            score += impact
            evidence.append(DetectionEvidence(
                'time_burst', same_time_count, 5.0,
                f'1小时内有{same_time_count}条评论集中发布，水军刷量特征', impact
            ))

        content_hash = self._simhash(review.content)
        similar_content_count = 0
        for r in all_reviews:
            if r.review_id != review.review_id:
                other_hash = self._simhash(r.content)
                similarity = self._hamming_similarity(content_hash, other_hash)
                if similarity >= 0.8:
                    similar_content_count += 1

        if similar_content_count >= 3:
            impact = min(0.35, similar_content_count * 0.10)
            score += impact
            evidence.append(DetectionEvidence(
                'content_similarity', similar_content_count, 3.0,
                f'与{similar_content_count}条其他评论内容高度相似，水军特征', impact
            ))

        return min(score, 1.0), evidence

    def _check_competitor_features(self, review: ReviewForDetection) -> Tuple[float, List[DetectionEvidence]]:
        score = 0.0
        evidence = []

        if review.rating == 1 or review.rating == 2:
            score += 0.15
            evidence.append(DetectionEvidence(
                'low_rating', review.rating, 2.0,
                f'{review.rating}星极低评价，恶意差评风险', 0.15
            ))

        content = review.content
        mentioned_brands = []
        for pattern in self.competitor_brands_patterns:
            matches = re.findall(pattern, content)
            mentioned_brands.extend(matches)

        if len(mentioned_brands) >= 2:
            impact = 0.30
            score += impact
            evidence.append(DetectionEvidence(
                'competitor_mentions', len(mentioned_brands), 2.0,
                f'评论中提及{len(mentioned_brands)}个竞品品牌：{"、".join(set(mentioned_brands))}', impact
            ))
        elif len(mentioned_brands) == 1:
            impact = 0.10
            score += impact
            evidence.append(DetectionEvidence(
                'competitor_mentions', 1, 2.0,
                f'评论中提及竞品品牌：{mentioned_brands[0]}', impact
            ))

        suspicious_matches = []
        for phrase in self.suspicious_phrases:
            if phrase in content:
                suspicious_matches.append(phrase)
        if len(suspicious_matches) >= 2:
            impact = min(0.25, len(suspicious_matches) * 0.10)
            score += impact
            evidence.append(DetectionEvidence(
                'suspicious_phrases', len(suspicious_matches), 2.0,
                f'包含{len(suspicious_matches)}个攻击性/极端用词：{"、".join(suspicious_matches)}', impact
            ))

        if (review.rating == 1 or review.rating == 2) and len(mentioned_brands) >= 1:
            impact = 0.20
            score += impact
            evidence.append(DetectionEvidence(
                'low_rating+competitor', 1, 0.5,
                '低评分+竞品提及组合，典型竞品恶意差评特征', impact
            ))

        extreme_words_count = len(re.findall(r'(垃圾|骗子|差|烂|假|骗)', content))
        if extreme_words_count >= 3:
            impact = min(0.20, extreme_words_count * 0.06)
            score += impact
            evidence.append(DetectionEvidence(
                'extreme_words', extreme_words_count, 3.0,
                f'使用{extreme_words_count}个极端负面词汇，情绪化评论', impact
            ))

        if len(content) > 50 and review.rating == 1 and len(mentioned_brands) >= 1:
            impact = 0.15
            score += impact
            evidence.append(DetectionEvidence(
                'long_negative_review', len(content), 50.0,
                '长文本+1星+竞品提及，专业差评师特征', impact
            ))

        return min(score, 1.0), evidence

    def _check_user_brushing_pattern(
        self,
        review: ReviewForDetection,
        user_reviews: List[ReviewForDetection]
    ) -> Tuple[float, List[DetectionEvidence]]:
        score = 0.0
        evidence = []

        if len(user_reviews) >= 5:
            high_rating_ratio = sum(1 for r in user_reviews if r.rating >= 4) / len(user_reviews)
            if high_rating_ratio >= 0.9:
                impact = 0.20
                score += impact
                evidence.append(DetectionEvidence(
                    'user_high_rating_ratio', high_rating_ratio, 0.9,
                    f'用户历史{high_rating_ratio:.0%}为4-5星好评，刷好评特征', impact
                ))

            time_diffs = []
            sorted_reviews = sorted(user_reviews, key=lambda r: r.timestamp)
            for i in range(1, len(sorted_reviews)):
                diff = (sorted_reviews[i].timestamp - sorted_reviews[i - 1].timestamp).total_seconds()
                time_diffs.append(diff)

            if time_diffs:
                avg_interval = sum(time_diffs) / len(time_diffs)
                if avg_interval < 3600:
                    impact = 0.15
                    score += impact
                    evidence.append(DetectionEvidence(
                        'user_short_interval', avg_interval, 3600.0,
                        f'用户评论平均间隔仅{avg_interval:.0f}秒，密集刷单特征', impact
                    ))

        return min(score, 1.0), evidence

    def _check_user_competitor_pattern(
        self,
        review: ReviewForDetection,
        user_reviews: List[ReviewForDetection]
    ) -> Tuple[float, List[DetectionEvidence]]:
        score = 0.0
        evidence = []

        if len(user_reviews) >= 3:
            low_rating_ratio = sum(1 for r in user_reviews if r.rating <= 2) / len(user_reviews)
            if low_rating_ratio >= 0.7:
                impact = 0.25
                score += impact
                evidence.append(DetectionEvidence(
                    'user_low_rating_ratio', low_rating_ratio, 0.7,
                    f'用户历史{low_rating_ratio:.0%}为1-2星差评，恶意差评师特征', impact
                ))

            product_ids = set(r.product_id for r in user_reviews)
            if len(product_ids) <= 2 and low_rating_ratio >= 0.5:
                impact = 0.15
                score += impact
                evidence.append(DetectionEvidence(
                    'user_targeted_attack', len(product_ids), 2.0,
                    f'用户只针对{len(product_ids)}个商品/品牌发布差评，定向攻击特征', impact
                ))

        return min(score, 1.0), evidence

    def _analyze_ip_group(self, ip: str, reviews: List[ReviewForDetection]) -> Optional[GroupDetectionResult]:
        suspicion_score = 0.0
        evidence = []
        suspicion_score += min(0.4, len(reviews) * 0.10)
        evidence.append(f'同一IP下{len(reviews)}个账号发布评论')

        ratings = [r.rating for r in reviews]
        if len(set(ratings)) == 1:
            suspicion_score += 0.25
            evidence.append(f'所有评论评分一致（{ratings[0]}星）')

        contents = [r.content for r in reviews]
        content_similarities = []
        for i in range(len(contents)):
            for j in range(i + 1, len(contents)):
                sim = self._text_similarity(contents[i], contents[j])
                content_similarities.append(sim)
        if content_similarities and sum(content_similarities) / len(content_similarities) > 0.6:
            suspicion_score += 0.25
            evidence.append('群组内评论内容高度相似')

        if suspicion_score >= 0.6:
            return GroupDetectionResult(
                group_id=f'ip_{ip.replace(".", "_")}',
                suspicious_users=[r.user_id for r in reviews],
                suspicious_reviews=[r.review_id for r in reviews],
                suspicion_score=min(suspicion_score, 1.0),
                evidence=evidence
            )
        return None

    def _analyze_content_cluster(self, cluster_id: str, reviews: List[ReviewForDetection]) -> Optional[GroupDetectionResult]:
        suspicion_score = 0.0
        evidence = []
        suspicion_score += min(0.35, len(reviews) * 0.08)
        evidence.append(f'{len(reviews)}条评论内容高度相似')

        user_ids = set(r.user_id for r in reviews)
        if len(user_ids) >= 3:
            suspicion_score += 0.25
            evidence.append(f'涉及{len(user_ids)}个不同账号')

        timestamps = [r.timestamp for r in reviews]
        time_range = (max(timestamps) - min(timestamps)).total_seconds()
        if time_range < 7200:
            suspicion_score += 0.20
            evidence.append(f'评论集中在{time_range/60:.0f}分钟内发布')

        if suspicion_score >= 0.6:
            return GroupDetectionResult(
                group_id=f'content_{cluster_id}',
                suspicious_users=[r.user_id for r in reviews],
                suspicious_reviews=[r.review_id for r in reviews],
                suspicion_score=min(suspicion_score, 1.0),
                evidence=evidence
            )
        return None

    def _analyze_time_group(self, time_id: str, reviews: List[ReviewForDetection]) -> Optional[GroupDetectionResult]:
        suspicion_score = 0.0
        evidence = []
        suspicion_score += min(0.30, len(reviews) * 0.06)
        evidence.append(f'{len(reviews)}条评论集中发布')

        ratings = [r.rating for r in reviews]
        rating_mode = Counter(ratings).most_common(1)[0][0]
        rating_ratio = sum(1 for r in ratings if r == rating_mode) / len(ratings)
        if rating_ratio >= 0.8:
            suspicion_score += 0.20
            evidence.append(f'{rating_ratio:.0%}的评分为{rating_mode}星，一致性极高')

        if suspicion_score >= 0.55:
            return GroupDetectionResult(
                group_id=f'time_{time_id}',
                suspicious_users=[r.user_id for r in reviews],
                suspicious_reviews=[r.review_id for r in reviews],
                suspicion_score=min(suspicion_score, 1.0),
                evidence=evidence
            )
        return None

    def _cluster_by_content_similarity(self, reviews: List[ReviewForDetection]) -> Dict[str, List[ReviewForDetection]]:
        clusters = {}
        unassigned = list(reviews)
        cluster_counter = 0

        while unassigned:
            current = unassigned.pop(0)
            current_hash = self._simhash(current.content)
            cluster = [current]

            i = 0
            while i < len(unassigned):
                other = unassigned[i]
                other_hash = self._simhash(other.content)
                similarity = self._hamming_similarity(current_hash, other_hash)
                if similarity >= 0.75:
                    cluster.append(other)
                    unassigned.pop(i)
                else:
                    i += 1

            if len(cluster) >= 2:
                cluster_id = f'cluster_{cluster_counter}'
                clusters[cluster_id] = cluster
                cluster_counter += 1

        return clusters

    def _cluster_by_time_burst(self, reviews: List[ReviewForDetection]) -> Dict[str, List[ReviewForDetection]]:
        clusters = {}
        sorted_reviews = sorted(reviews, key=lambda r: r.timestamp)
        time_window = timedelta(minutes=30)
        cluster_counter = 0
        i = 0

        while i < len(sorted_reviews):
            cluster = [sorted_reviews[i]]
            j = i + 1
            while j < len(sorted_reviews):
                if (sorted_reviews[j].timestamp - sorted_reviews[i].timestamp) <= time_window:
                    cluster.append(sorted_reviews[j])
                    j += 1
                else:
                    break

            if len(cluster) >= 3:
                cluster_id = f'burst_{cluster_counter}'
                clusters[cluster_id] = cluster
                cluster_counter += 1
                i = j
            else:
                i += 1

        return clusters

    @staticmethod
    def _simhash(text: str) -> int:
        hash_obj = hashlib.md5(text.encode('utf-8'))
        hash_bytes = hash_obj.digest()
        return int.from_bytes(hash_bytes[:8], 'big')

    @staticmethod
    def _hamming_similarity(hash1: int, hash2: int) -> float:
        xor = hash1 ^ hash2
        distance = bin(xor).count('1')
        return 1.0 - (distance / 64.0)

    @staticmethod
    def _text_similarity(text1: str, text2: str) -> float:
        if not text1 or not text2:
            return 0.0
        set1 = set(text1)
        set2 = set(text2)
        if not set1 or not set2:
            return 0.0
        return len(set1 & set2) / len(set1 | set2)

    @staticmethod
    def _get_suspicion_level(score: float) -> SuspicionLevel:
        if score >= 0.9:
            return SuspicionLevel.CRITICAL
        elif score >= 0.7:
            return SuspicionLevel.HIGH
        elif score >= 0.5:
            return SuspicionLevel.MEDIUM
        elif score >= 0.3:
            return SuspicionLevel.LOW
        else:
            return SuspicionLevel.NONE

    def batch_detect(self, reviews: List[ReviewForDetection]) -> List[FakeReviewDetectionResult]:
        results = []
        user_reviews_map = defaultdict(list)
        for r in reviews:
            user_reviews_map[r.user_id].append(r)

        for review in reviews:
            result = self.detect(
                review,
                all_reviews=reviews,
                user_reviews=user_reviews_map[review.user_id]
            )
            results.append(result)

        return results
