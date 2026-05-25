#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
评论排序优化模块
高质量评论优先展示，支持多种排序策略
"""

import math
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Optional, Any, Tuple
from datetime import datetime, timedelta
from collections import defaultdict


class SortStrategy(Enum):
    QUALITY_FIRST = "quality_first"
    HELPFULNESS_FIRST = "helpfulness_first"
    TIME_DECAY = "time_decay"
    BALANCED = "balanced"
    NEWEST_FIRST = "newest_first"
    MOST_HELPFUL = "most_helpful"
    CONTROVERSIAL = "controversial"


@dataclass
class ReviewForRanking:
    review_id: str
    quality_score: float
    user_reputation: float
    helpful_votes: int = 0
    unhelpful_votes: int = 0
    reply_count: int = 0
    timestamp: datetime = field(default_factory=datetime.now)
    content_length: int = 0
    is_verified_purchase: bool = False
    fake_review_score: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RankingFeature:
    name: str
    value: float
    weight: float
    normalized_value: float
    description: str


@dataclass
class RankingResult:
    review_id: str
    final_rank: int
    final_score: float
    features: List[RankingFeature]
    explanation: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            'review_id': self.review_id,
            'final_rank': self.final_rank,
            'final_score': self.final_score,
            'features': [
                {
                    'name': f.name,
                    'value': f.value,
                    'weight': f.weight,
                    'normalized_value': f.normalized_value,
                    'description': f.description
                } for f in self.features
            ],
            'explanation': self.explanation
        }


@dataclass
class RankingConfig:
    strategy: SortStrategy = SortStrategy.BALANCED
    quality_weight: float = 0.35
    helpfulness_weight: float = 0.25
    recency_weight: float = 0.15
    reputation_weight: float = 0.10
    interaction_weight: float = 0.10
    detail_weight: float = 0.05

    fake_review_penalty_factor: float = 0.5
    time_decay_half_life_days: int = 30
    helpfulness_smoothing: int = 10

    boost_verified_purchase: bool = True
    verified_boost: float = 0.10


class ReviewRanker:
    def __init__(self, config: Optional[RankingConfig] = None):
        self.config = config or RankingConfig()

    def rank_reviews(
        self,
        reviews: List[ReviewForRanking],
        strategy: Optional[SortStrategy] = None,
        custom_weights: Optional[Dict[str, float]] = None
    ) -> List[Tuple[ReviewForRanking, RankingResult]]:
        if not reviews:
            return []

        current_config = self._apply_strategy(strategy)
        if custom_weights:
            current_config = self._apply_custom_weights(current_config, custom_weights)

        scored_reviews = []
        for review in reviews:
            score, features = self._calculate_ranking_score(review, current_config, reviews)
            scored_reviews.append((review, score, features))

        scored_reviews.sort(key=lambda x: x[1], reverse=True)

        results = []
        for rank, (review, score, features) in enumerate(scored_reviews, 1):
            explanation = self._generate_explanation(features, score, rank)
            result = RankingResult(
                review_id=review.review_id,
                final_rank=rank,
                final_score=score,
                features=features,
                explanation=explanation
            )
            results.append((review, result))

        return results

    def _apply_strategy(self, strategy: Optional[SortStrategy]) -> RankingConfig:
        config = RankingConfig()
        config.fake_review_penalty_factor = self.config.fake_review_penalty_factor
        config.time_decay_half_life_days = self.config.time_decay_half_life_days
        config.helpfulness_smoothing = self.config.helpfulness_smoothing
        config.boost_verified_purchase = self.config.boost_verified_purchase
        config.verified_boost = self.config.verified_boost

        strategy = strategy or self.config.strategy

        if strategy == SortStrategy.QUALITY_FIRST:
            config.quality_weight = 0.60
            config.helpfulness_weight = 0.15
            config.recency_weight = 0.10
            config.reputation_weight = 0.10
            config.interaction_weight = 0.03
            config.detail_weight = 0.02
        elif strategy == SortStrategy.HELPFULNESS_FIRST:
            config.quality_weight = 0.15
            config.helpfulness_weight = 0.60
            config.recency_weight = 0.10
            config.reputation_weight = 0.05
            config.interaction_weight = 0.08
            config.detail_weight = 0.02
        elif strategy == SortStrategy.TIME_DECAY:
            config.quality_weight = 0.25
            config.helpfulness_weight = 0.20
            config.recency_weight = 0.35
            config.reputation_weight = 0.10
            config.interaction_weight = 0.07
            config.detail_weight = 0.03
        elif strategy == SortStrategy.BALANCED:
            config.quality_weight = 0.35
            config.helpfulness_weight = 0.25
            config.recency_weight = 0.15
            config.reputation_weight = 0.10
            config.interaction_weight = 0.10
            config.detail_weight = 0.05
        elif strategy == SortStrategy.NEWEST_FIRST:
            config.quality_weight = 0.10
            config.helpfulness_weight = 0.05
            config.recency_weight = 0.70
            config.reputation_weight = 0.05
            config.interaction_weight = 0.05
            config.detail_weight = 0.05
        elif strategy == SortStrategy.MOST_HELPFUL:
            config.quality_weight = 0.20
            config.helpfulness_weight = 0.55
            config.recency_weight = 0.05
            config.reputation_weight = 0.05
            config.interaction_weight = 0.10
            config.detail_weight = 0.05
        elif strategy == SortStrategy.CONTROVERSIAL:
            config.quality_weight = 0.15
            config.helpfulness_weight = 0.30
            config.recency_weight = 0.10
            config.reputation_weight = 0.05
            config.interaction_weight = 0.30
            config.detail_weight = 0.10

        return config

    def _apply_custom_weights(self, config: RankingConfig, weights: Dict[str, float]) -> RankingConfig:
        if 'quality_weight' in weights:
            config.quality_weight = weights['quality_weight']
        if 'helpfulness_weight' in weights:
            config.helpfulness_weight = weights['helpfulness_weight']
        if 'recency_weight' in weights:
            config.recency_weight = weights['recency_weight']
        if 'reputation_weight' in weights:
            config.reputation_weight = weights['reputation_weight']
        if 'interaction_weight' in weights:
            config.interaction_weight = weights['interaction_weight']
        if 'detail_weight' in weights:
            config.detail_weight = weights['detail_weight']

        total = (config.quality_weight + config.helpfulness_weight + config.recency_weight +
                 config.reputation_weight + config.interaction_weight + config.detail_weight)

        if total > 0:
            config.quality_weight /= total
            config.helpfulness_weight /= total
            config.recency_weight /= total
            config.reputation_weight /= total
            config.interaction_weight /= total
            config.detail_weight /= total

        return config

    def _calculate_ranking_score(
        self,
        review: ReviewForRanking,
        config: RankingConfig,
        all_reviews: List[ReviewForRanking]
    ) -> Tuple[float, List[RankingFeature]]:
        features = []

        quality_feature = self._calculate_quality_feature(review, config)
        features.append(quality_feature)

        helpfulness_feature = self._calculate_helpfulness_feature(review, config, all_reviews)
        features.append(helpfulness_feature)

        recency_feature = self._calculate_recency_feature(review, config)
        features.append(recency_feature)

        reputation_feature = self._calculate_reputation_feature(review, config)
        features.append(reputation_feature)

        interaction_feature = self._calculate_interaction_feature(review, config, all_reviews)
        features.append(interaction_feature)

        detail_feature = self._calculate_detail_feature(review, config, all_reviews)
        features.append(detail_feature)

        final_score = sum(f.normalized_value * f.weight for f in features)

        if config.boost_verified_purchase and review.is_verified_purchase:
            final_score *= (1 + config.verified_boost)

        if review.fake_review_score > 0:
            penalty = 1 - (review.fake_review_score * config.fake_review_penalty_factor)
            final_score *= penalty

        return max(0.0, min(1.0, final_score)), features

    def _calculate_quality_feature(self, review: ReviewForRanking, config: RankingConfig) -> RankingFeature:
        quality_score = max(0.0, min(1.0, review.quality_score))
        description = f"评论质量分: {quality_score:.4f}（权重 {config.quality_weight:.1%}）"
        return RankingFeature(
            name='quality_score',
            value=review.quality_score,
            weight=config.quality_weight,
            normalized_value=quality_score,
            description=description
        )

    def _calculate_helpfulness_feature(
        self,
        review: ReviewForRanking,
        config: RankingConfig,
        all_reviews: List[ReviewForRanking]
    ) -> RankingFeature:
        total_votes = review.helpful_votes + review.unhelpful_votes

        if total_votes == 0:
            smoothed_ratio = 0.5
            description = f"暂无投票，使用默认值 0.5000（权重 {config.helpfulness_weight:.1%}）"
        else:
            global_avg_helpful = sum(r.helpful_votes for r in all_reviews) / max(
                sum(r.helpful_votes + r.unhelpful_votes for r in all_reviews), 1
            )
            smoothed_ratio = (
                review.helpful_votes + config.helpfulness_smoothing * global_avg_helpful
            ) / (total_votes + config.helpfulness_smoothing)
            description = (
                f"有用性: {review.helpful_votes}/{total_votes} = {review.helpful_votes / total_votes:.4f}, "
                f"平滑后: {smoothed_ratio:.4f}（权重 {config.helpfulness_weight:.1%}）"
            )

        return RankingFeature(
            name='helpfulness',
            value=review.helpful_votes - review.unhelpful_votes,
            weight=config.helpfulness_weight,
            normalized_value=smoothed_ratio,
            description=description
        )

    def _calculate_recency_feature(self, review: ReviewForRanking, config: RankingConfig) -> RankingFeature:
        now = datetime.now()
        age_days = (now - review.timestamp).total_seconds() / 86400.0

        half_life = config.time_decay_half_life_days
        decay_factor = math.exp(-math.log(2) * age_days / half_life)
        decay_factor = max(0.01, min(1.0, decay_factor))

        description = (
            f"评论时效: {age_days:.1f}天, "
            f"半衰期 {half_life}天, "
            f"衰减系数: {decay_factor:.4f}（权重 {config.recency_weight:.1%}）"
        )

        return RankingFeature(
            name='recency',
            value=age_days,
            weight=config.recency_weight,
            normalized_value=decay_factor,
            description=description
        )

    def _calculate_reputation_feature(self, review: ReviewForRanking, config: RankingConfig) -> RankingFeature:
        reputation = max(0.0, min(1.0, review.user_reputation))
        description = f"用户信誉: {reputation:.4f}（权重 {config.reputation_weight:.1%}）"
        return RankingFeature(
            name='user_reputation',
            value=review.user_reputation,
            weight=config.reputation_weight,
            normalized_value=reputation,
            description=description
        )

    def _calculate_interaction_feature(
        self,
        review: ReviewForRanking,
        config: RankingConfig,
        all_reviews: List[ReviewForRanking]
    ) -> RankingFeature:
        if not all_reviews:
            normalized = 0.5
        else:
            max_replies = max(r.reply_count for r in all_reviews)
            if max_replies == 0:
                normalized = 0.5 if review.reply_count > 0 else 0.0
            else:
                normalized = min(1.0, review.reply_count / max_replies)

        description = (
            f"评论互动: {review.reply_count}条回复, "
            f"标准化: {normalized:.4f}（权重 {config.interaction_weight:.1%}）"
        )

        return RankingFeature(
            name='interaction',
            value=review.reply_count,
            weight=config.interaction_weight,
            normalized_value=normalized,
            description=description
        )

    def _calculate_detail_feature(
        self,
        review: ReviewForRanking,
        config: RankingConfig,
        all_reviews: List[ReviewForRanking]
    ) -> RankingFeature:
        if not all_reviews:
            normalized = 0.5
        else:
            lengths = [r.content_length for r in all_reviews if r.content_length > 0]
            if not lengths:
                normalized = 0.5
            else:
                avg_length = sum(lengths) / len(lengths)
                std_length = (sum((l - avg_length) ** 2 for l in lengths) / len(lengths)) ** 0.5

                if std_length == 0:
                    normalized = 0.5 if review.content_length > 0 else 0.0
                else:
                    z_score = (review.content_length - avg_length) / std_length
                    normalized = 1 / (1 + math.exp(-z_score))

        description = (
            f"内容详细度: {review.content_length}字, "
            f"标准化: {normalized:.4f}（权重 {config.detail_weight:.1%}）"
        )

        return RankingFeature(
            name='detail_level',
            value=review.content_length,
            weight=config.detail_weight,
            normalized_value=normalized,
            description=description
        )

    def _generate_explanation(self, features: List[RankingFeature], score: float, rank: int) -> str:
        top_features = sorted(features, key=lambda f: f.normalized_value * f.weight, reverse=True)[:3]

        parts = [
            f"综合排序分数: {score:.4f}, 排名第 {rank} 位",
            "主要贡献因素:"
        ]

        for idx, feature in enumerate(top_features, 1):
            contribution = feature.normalized_value * feature.weight
            parts.append(
                f"  {idx}. {feature.name}: "
                f"{feature.normalized_value:.4f} × {feature.weight:.1%} = {contribution:.4f}"
            )

        return "\n".join(parts)

    def rerank_with_diversity(
        self,
        ranked_results: List[Tuple[ReviewForRanking, RankingResult]],
        diversity_window: int = 5,
        max_same_user_in_window: int = 2
    ) -> List[Tuple[ReviewForRanking, RankingResult]]:
        if len(ranked_results) <= diversity_window:
            return ranked_results

        results = list(ranked_results)
        reranked = []
        used_users = defaultdict(int)

        while results:
            current_window = min(diversity_window, len(results))
            selected_idx = 0

            for idx in range(current_window):
                review, result = results[idx]
                user_count = used_users[review.review_id.split('_')[0]]

                if user_count < max_same_user_in_window:
                    selected_idx = idx
                    break

            selected = results.pop(selected_idx)
            reranked.append(selected)

            user_id = selected[0].review_id.split('_')[0]
            used_users[user_id] += 1

            for user in list(used_users.keys()):
                if used_users[user] > 0 and user != user_id:
                    used_users[user] = max(0, used_users[user] - 1)

        for rank, (review, result) in enumerate(reranked, 1):
            result.final_rank = rank

        return reranked

    def get_strategy_comparison(
        self,
        reviews: List[ReviewForRanking]
    ) -> Dict[str, List[Tuple[ReviewForRanking, RankingResult]]]:
        strategies = [
            SortStrategy.QUALITY_FIRST,
            SortStrategy.HELPFULNESS_FIRST,
            SortStrategy.TIME_DECAY,
            SortStrategy.BALANCED,
            SortStrategy.NEWEST_FIRST,
            SortStrategy.MOST_HELPFUL
        ]

        results = {}
        for strategy in strategies:
            results[strategy.value] = self.rank_reviews(reviews, strategy=strategy)

        return results

    def print_ranking_comparison(
        self,
        reviews: List[ReviewForRanking],
        top_n: int = 5
    ) -> None:
        results = self.get_strategy_comparison(reviews)

        print("=" * 90)
        print(f"{'排序策略对比':^90}")
        print("=" * 90)
        print(f"{'策略':<20} |", end="")
        for i in range(1, top_n + 1):
            print(f"  Top{i:2d}(ID,分数)", end="")
        print()
        print("-" * 90)

        strategy_names = {
            'quality_first': '质量优先',
            'helpfulness_first': '有用性优先',
            'time_decay': '时间衰减',
            'balanced': '综合平衡',
            'newest_first': '最新优先',
            'most_helpful': '最多有用'
        }

        for strategy_name, ranked in results.items():
            print(f"{strategy_names.get(strategy_name, strategy_name):<20} |", end="")
            for i in range(min(top_n, len(ranked))):
                review, result = ranked[i]
                short_id = review.review_id[:8]
                print(f"  {short_id}({result.final_score:.3f})", end="")
            print()
        print()

    def print_ranking_details(
        self,
        ranked_results: List[Tuple[ReviewForRanking, RankingResult]],
        top_n: int = 10
    ) -> None:
        print("=" * 90)
        print(f"{'评论排序详情':^90}")
        print("=" * 90)

        for idx, (review, result) in enumerate(ranked_results[:top_n], 1):
            print(f"\n【第 {idx} 名】 评论ID: {review.review_id}")
            print(f"  综合排序分: {result.final_score:.4f}")
            print(f"  质量分: {review.quality_score:.4f} | 用户信誉: {review.user_reputation:.4f}")
            print(f"  有用: {review.helpful_votes} | 无用: {review.unhelpful_votes} | 回复: {review.reply_count}")
            print(f"  发布时间: {review.timestamp.strftime('%Y-%m-%d %H:%M')} | 字数: {review.content_length}")
            if review.is_verified_purchase:
                print(f"  ✓ 已验证购买")
            if review.fake_review_score > 0.3:
                print(f"  ⚠️  虚假评论嫌疑: {review.fake_review_score:.2%}")

            print(f"  特征分解:")
            for feature in sorted(result.features, key=lambda f: f.weight * f.normalized_value, reverse=True):
                contribution = feature.normalized_value * feature.weight
                bar = "█" * int(contribution * 50)
                print(f"    {feature.name:<18} {bar:<50} {contribution:.4f}")
                print(f"      {feature.description}")

            print(f"  解释: {result.explanation.splitlines()[0]}")

        print("\n" + "=" * 90)
