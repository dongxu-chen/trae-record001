import re
from datetime import datetime
from typing import Tuple, List, Optional
import logging

logger = logging.getLogger(__name__)

from config import settings
from schemas import (
    ReviewItem, MerchantReply, MerchantReplyImpact
)


class MerchantReplyAnalyzer:
    def __init__(self):
        self._solution_keywords = [
            "换货", "退货", "退款", "补发", "赔偿", "解决",
            "修复", "更换", "处理", "改进", "优化", "升级",
            "联系客服", "售后", "维修", "补偿方案"
        ]
        self._compensation_keywords = [
            "赔偿", "补偿", "退款", "优惠券", "折扣", "减免",
            "返现", "赠送", "免运费", "包邮", "积分"
        ]
        self._apology_keywords = [
            "抱歉", "对不起", "不好意思", "歉意", "深表歉意",
            "非常抱歉", "诚挚道歉", "致歉", "恳请谅解"
        ]

    def _analyze_reply_content(self, reply: MerchantReply) -> Tuple[bool, bool, bool, List[str]]:
        content = reply.reply_content
        warnings = []

        mentions_solution = reply.mentions_solution or any(
            kw in content for kw in self._solution_keywords
        )
        mentions_compensation = reply.mentions_compensation or any(
            kw in content for kw in self._compensation_keywords
        )
        is_apologetic = reply.is_apologetic or any(
            kw in content for kw in self._apology_keywords
        )

        if mentions_compensation and not mentions_solution:
            warnings.append("商家仅提及补偿未提供实质解决方案")

        if len(content) < 10:
            warnings.append("商家回复内容过短，缺乏诚意")

        return mentions_solution, mentions_compensation, is_apologetic, warnings

    def _calculate_trust_boost(
        self,
        review: ReviewItem,
        reply: MerchantReply,
        mentions_solution: bool,
        mentions_compensation: bool,
        is_apologetic: bool
    ) -> float:
        trust_boost = settings.MERCHANT_REPLY_TRUST_BOOST

        if mentions_solution:
            trust_boost += settings.MERCHANT_REPLY_SOLUTION_BONUS

        if is_apologetic:
            trust_boost += settings.MERCHANT_REPLY_APOLOGY_BONUS

        if mentions_compensation:
            trust_boost += settings.MERCHANT_REPLY_COMPENSATION_BONUS

        if not reply.is_official:
            trust_boost *= 0.5

        reply_delay_days = (reply.reply_time - review.create_time).total_seconds() / 86400.0
        if reply_delay_days > settings.MERCHANT_REPLY_LATE_DAYS_THRESHOLD:
            late_penalty = settings.MERCHANT_REPLY_LATE_PENALTY * (
                reply_delay_days / settings.MERCHANT_REPLY_LATE_DAYS_THRESHOLD - 1.0
            )
            trust_boost -= min(late_penalty, settings.MERCHANT_REPLY_TRUST_BOOST * 0.5)

        if review.rating <= 2:
            trust_boost *= settings.MERCHANT_REPLY_NEGATIVE_REVIEW_MULTIPLIER

        return trust_boost

    def _calculate_quality_delta(
        self,
        review: ReviewItem,
        reply: MerchantReply,
        trust_boost: float
    ) -> Tuple[float, str, List[str]]:
        warnings = []

        delta = min(trust_boost, settings.MERCHANT_REPLY_QUALITY_DELTA_MAX)

        if delta <= 0:
            impact_level = "negative"
        elif delta < 3:
            impact_level = "minimal"
        elif delta < 8:
            impact_level = "moderate"
        elif delta < 12:
            impact_level = "significant"
        else:
            impact_level = "high"

        if review.rating >= 4 and delta > 5:
            delta *= 0.7
            warnings.append("正面评论的商家回复影响适度衰减")
            impact_level = "moderate"

        if review.rating <= 2 and delta > 3:
            warnings.append("商家积极回复负面评论，显著提升信任感")

        return round(delta, 2), impact_level, warnings

    def _calculate_satisfaction_improvement(
        self,
        review: ReviewItem,
        reply: MerchantReply,
        mentions_solution: bool,
        is_apologetic: bool
    ) -> float:
        improvement = 0.0

        if review.rating <= 2:
            if mentions_solution:
                improvement += 25.0
            if is_apologetic:
                improvement += 15.0
            if reply.is_official:
                improvement += 10.0

            reply_speed_hours = (reply.reply_time - review.create_time).total_seconds() / 3600.0
            if reply_speed_hours <= 2:
                improvement += 15.0
            elif reply_speed_hours <= 24:
                improvement += 10.0
            elif reply_speed_hours <= 72:
                improvement += 5.0

        elif review.rating == 3:
            if mentions_solution:
                improvement += 15.0
            if is_apologetic:
                improvement += 8.0

        else:
            improvement += 5.0
            if mentions_solution:
                improvement += 5.0

        return round(min(improvement, 100.0), 2)

    def analyze_reply_impact(
        self,
        review: ReviewItem,
        reply: Optional[MerchantReply] = None
    ) -> MerchantReplyImpact:
        if reply is None:
            reply = review.merchant_reply

        if reply is None:
            return MerchantReplyImpact(
                review_id=review.review_id,
                impact_level="none"
            )

        mentions_solution, mentions_compensation, is_apologetic, reply_warnings = (
            self._analyze_reply_content(reply)
        )

        trust_boost = self._calculate_trust_boost(
            review, reply, mentions_solution, mentions_compensation, is_apologetic
        )

        quality_delta, impact_level, delta_warnings = self._calculate_quality_delta(
            review, reply, trust_boost
        )

        satisfaction_improvement = self._calculate_satisfaction_improvement(
            review, reply, mentions_solution, is_apologetic
        )

        adjusted_overall_score = None

        all_warnings = reply_warnings + delta_warnings

        return MerchantReplyImpact(
            reply_id=reply.reply_id,
            review_id=review.review_id,
            quality_delta=quality_delta,
            trust_boost=round(trust_boost, 2),
            satisfaction_improvement=satisfaction_improvement,
            adjusted_overall_score=adjusted_overall_score,
            impact_level=impact_level,
            warnings=all_warnings
        )

    def apply_reply_to_score(
        self,
        review: ReviewItem,
        base_score: float
    ) -> Tuple[float, MerchantReplyImpact]:
        impact = self.analyze_reply_impact(review)

        if impact.impact_level == "none":
            return base_score, impact

        adjusted = base_score + impact.quality_delta
        adjusted = round(min(100.0, max(0.0, adjusted)), 2)
        impact.adjusted_overall_score = adjusted

        return adjusted, impact
