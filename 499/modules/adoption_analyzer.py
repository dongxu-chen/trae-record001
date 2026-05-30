import math
from datetime import datetime
from typing import List, Tuple, Optional
import logging

logger = logging.getLogger(__name__)

from config import settings
from schemas import (
    ReviewItem, ReviewInteraction, AdoptionAnalysisResult
)


class AdoptionAnalyzer:
    def __init__(self):
        pass

    def _calculate_purchase_influence(
        self,
        review: ReviewItem,
        interaction: Optional[ReviewInteraction]
    ) -> Tuple[float, List[str]]:
        warnings = []

        if interaction is None:
            return 50.0, ["无互动数据，使用默认购买影响力"]

        view_count = max(interaction.view_count, 1)

        purchase_rate = interaction.purchase_after_view_count / view_count
        cart_rate = interaction.add_to_cart_after_view_count / view_count

        combined_rate = purchase_rate * 0.7 + cart_rate * 0.3

        if purchase_rate >= settings.ADOPTION_PURCHASE_RATE_EXCELLENT:
            purchase_score = 100.0
        elif purchase_rate >= settings.ADOPTION_PURCHASE_RATE_GOOD:
            progress = (purchase_rate - settings.ADOPTION_PURCHASE_RATE_GOOD) / (
                settings.ADOPTION_PURCHASE_RATE_EXCELLENT - settings.ADOPTION_PURCHASE_RATE_GOOD
            )
            purchase_score = 70.0 + progress * 30.0
        elif purchase_rate >= settings.ADOPTION_PURCHASE_RATE_AVERAGE:
            progress = (purchase_rate - settings.ADOPTION_PURCHASE_RATE_AVERAGE) / (
                settings.ADOPTION_PURCHASE_RATE_GOOD - settings.ADOPTION_PURCHASE_RATE_AVERAGE
            )
            purchase_score = 40.0 + progress * 30.0
        else:
            purchase_score = purchase_rate / settings.ADOPTION_PURCHASE_RATE_AVERAGE * 40.0

        if view_count < settings.ADOPTION_MIN_VIEWS_FOR_SIGNIFICANCE:
            significance_factor = view_count / settings.ADOPTION_MIN_VIEWS_FOR_SIGNIFICANCE
            purchase_score *= significance_factor
            if significance_factor < 0.5:
                warnings.append(f"浏览量过低({view_count})，购买影响力数据不够显著")

        if purchase_rate > 0.3:
            warnings.append("购买转化率异常高，可能存在数据偏差")

        return round(min(100.0, max(0.0, purchase_score)), 2), warnings

    def _calculate_engagement_quality(
        self,
        review: ReviewItem,
        interaction: Optional[ReviewInteraction]
    ) -> Tuple[float, List[str]]:
        warnings = []

        if interaction is None:
            return 40.0, ["无互动数据，使用默认参与度"]

        view_count = max(interaction.view_count, 1)

        helpful_rate = interaction.helpful_votes / view_count
        unhelpful_rate = interaction.unhelpful_votes / view_count if interaction.unhelpful_votes > 0 else 0.0
        share_rate = interaction.share_count / view_count
        collect_rate = interaction.collect_count / view_count
        comment_rate = interaction.comment_count / view_count

        helpful_score = min(helpful_rate * 500, 100.0)

        if unhelpful_rate > 0 and helpful_rate > 0:
            net_helpful = helpful_rate / (helpful_rate + unhelpful_rate)
        else:
            net_helpful = 1.0 if helpful_rate > 0 else 0.5

        share_score = min(share_rate * 1000, 50.0)
        collect_score = min(collect_rate * 800, 40.0)
        comment_score = min(comment_rate * 500, 30.0)

        engagement_score = (
            helpful_score * 0.40 +
            net_helpful * 30.0 +
            share_score * 0.10 +
            collect_score * 0.10 +
            comment_score * 0.10
        )

        if interaction.helpful_votes > 0 and interaction.unhelpful_votes > 0:
            if unhelpful_rate > helpful_rate:
                warnings.append("踩多于赞，参与质量偏低")
                engagement_score *= 0.7

        if interaction.comment_count > 5:
            warnings.append("评论引发了较多讨论，具有决策参考价值")
            engagement_score = min(engagement_score * 1.1, 100.0)

        return round(min(100.0, max(0.0, engagement_score)), 2), warnings

    def _calculate_decision_helpfulness(
        self,
        review: ReviewItem,
        interaction: Optional[ReviewInteraction]
    ) -> Tuple[float, List[str]]:
        warnings = []
        score = 0.0

        content = review.content
        has_pros_cons = (
            any(kw in content for kw in ["优点", "长处", "好处"]) and
            any(kw in content for kw in ["缺点", "不足", "问题"])
        )
        if has_pros_cons:
            score += 30.0

        has_comparison = any(kw in content for kw in ["比", "对比", "相比", "之前", "以前", "原来", "替代"])
        if has_comparison:
            score += 20.0

        has_specific_details = bool(
            any(kw in content for kw in ["尺寸", "大小", "重量", "厚度", "容量", "功率", "续航", "材质"])
        )
        if has_specific_details:
            score += 20.0

        if review.has_images or review.has_videos:
            score += 15.0

        if review.is_verified_purchase:
            score += 10.0

        if review.rating in [2, 3, 4]:
            score += 5.0
            warnings.append("中等评分评论通常包含更客观的决策参考")
        elif review.rating in [1, 5]:
            score -= 5.0

        has_usage = any(kw in content for kw in ["使用", "体验", "效果", "实测", "测量"])
        if has_usage:
            score += 10.0

        if review.merchant_reply is not None:
            score += 5.0

        return round(min(100.0, max(0.0, score)), 2), warnings

    def analyze_adoption(
        self,
        review: ReviewItem,
        interaction: Optional[ReviewInteraction] = None
    ) -> AdoptionAnalysisResult:
        if interaction is None:
            interaction = review.interaction

        purchase_score, purchase_warnings = self._calculate_purchase_influence(review, interaction)
        engagement_score, engagement_warnings = self._calculate_engagement_quality(review, interaction)
        decision_score, decision_warnings = self._calculate_decision_helpfulness(review, interaction)

        all_warnings = purchase_warnings + engagement_warnings + decision_warnings

        adoption_score = (
            purchase_score * settings.ADOPTION_PURCHASE_INFLUENCE_WEIGHT +
            engagement_score * settings.ADOPTION_ENGAGEMENT_WEIGHT +
            decision_score * settings.ADOPTION_DECISION_WEIGHT
        )

        return AdoptionAnalysisResult(
            review_id=review.review_id,
            adoption_score=round(min(100.0, max(0.0, adoption_score)), 2),
            purchase_influence=purchase_score,
            engagement_quality=engagement_score,
            decision_helpfulness=decision_score,
            warnings=all_warnings
        )

    def rank_by_adoption(
        self,
        reviews: List[ReviewItem],
        interactions: Optional[List[ReviewInteraction]] = None
    ) -> List[AdoptionAnalysisResult]:
        interaction_map = {}
        if interactions:
            for inter in interactions:
                interaction_map[inter.review_id] = inter

        results = []
        for review in reviews:
            inter = interaction_map.get(review.review_id, review.interaction)
            result = self.analyze_adoption(review, inter)
            results.append(result)

        results.sort(key=lambda x: x.adoption_score, reverse=True)

        for rank, result in enumerate(results, 1):
            result.adoption_rank = rank

        return results[:settings.ADOPTION_TOP_K]

    def find_top_decision_reviews(
        self,
        reviews: List[ReviewItem],
        top_k: int = 5
    ) -> List[AdoptionAnalysisResult]:
        ranked = self.rank_by_adoption(reviews)
        decision_ranked = sorted(ranked, key=lambda x: x.decision_helpfulness, reverse=True)
        return decision_ranked[:top_k]
