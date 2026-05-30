import math
from datetime import datetime
from typing import List, Tuple, Optional
import logging

logger = logging.getLogger(__name__)

from config import settings
from schemas import (
    ReviewItem, ReviewQualityResult, DimensionScores,
    GangDetectionResult, AdoptionAnalysisResult, MerchantReplyImpact,
    VoteRecord
)


class ScoringEngine:
    def __init__(
        self,
        authenticity_analyzer,
        user_reputation_model,
        rule_engine,
        gang_detector=None,
        adoption_analyzer=None,
        merchant_reply_analyzer=None
    ):
        self.authenticity_analyzer = authenticity_analyzer
        self.user_reputation_model = user_reputation_model
        self.rule_engine = rule_engine
        self.gang_detector = gang_detector
        self.adoption_analyzer = adoption_analyzer
        self.merchant_reply_analyzer = merchant_reply_analyzer

    def _calculate_overall_score(self, dimensions: DimensionScores) -> float:
        score = (
            dimensions.authenticity * settings.AUTHENTICITY_WEIGHT +
            dimensions.usefulness * settings.USEFULNESS_WEIGHT +
            dimensions.completeness * settings.COMPLETENESS_WEIGHT +
            dimensions.user_reputation * settings.REPUTATION_WEIGHT
        )
        return round(score, 2)

    def _calculate_time_factor(
        self,
        review: ReviewItem,
        now: datetime
    ) -> float:
        days_old = max(0, (now - review.create_time).total_seconds() / 86400.0)

        half_life = settings.TIME_DECAY_HALF_LIFE_DAYS
        base_decay = math.exp(-math.log(2) * days_old / half_life)

        recency_window = settings.RECENCY_BOOST_WINDOW_DAYS
        recency_boost = settings.RECENCY_BOOST_FACTOR
        transition_days = settings.RECENCY_TRANSITION_DAYS
        long_tail_factor = settings.RECENCY_LONG_TAIL_FACTOR

        if days_old <= recency_window:
            recency_factor = recency_boost
        elif days_old <= recency_window + transition_days:
            progress = (days_old - recency_window) / transition_days
            recency_factor = recency_boost - (recency_boost - 1.0) * progress
        else:
            recency_factor = 1.0 - (1.0 - long_tail_factor) * min(
                (days_old - recency_window - transition_days) / 60.0, 1.0
            )
            recency_factor = max(long_tail_factor, recency_factor)

        time_factor = base_decay * recency_factor

        return round(time_factor, 6)

    def _calculate_sort_score(
        self,
        review: ReviewItem,
        overall_score: float,
        now: datetime
    ) -> Tuple[float, float]:
        time_factor = self._calculate_time_factor(review, now)

        helpful_boost = 1.0 + min(review.helpful_votes * 0.01, 0.5)

        verified_boost = 1.1 if review.is_verified_purchase else 1.0

        media_boost = 1.0
        if review.has_images:
            media_boost *= 1.05
        if review.has_videos:
            media_boost *= 1.05

        quality_normalized = overall_score / 100.0

        sort_score = (
            quality_normalized *
            time_factor *
            helpful_boost *
            verified_boost *
            media_boost
        )

        return round(sort_score, 6), time_factor

    def _should_collapse(self, overall_score: float) -> bool:
        return overall_score < settings.COLLAPSE_THRESHOLD

    def _is_low_quality(self, overall_score: float) -> bool:
        return overall_score < settings.LOW_QUALITY_THRESHOLD

    def score_review(
        self,
        review: ReviewItem,
        now: datetime = None,
        gang_results: Optional[List[GangDetectionResult]] = None
    ) -> ReviewQualityResult:
        if now is None:
            now = datetime.now()

        all_warnings = []

        authenticity_score, auth_warnings, purchase_detail = self.authenticity_analyzer.analyze(review)
        all_warnings.extend(auth_warnings)

        gang_detection = None
        if self.gang_detector and gang_results:
            gang_penalty, gang_warnings = self.gang_detector.calculate_gang_penalty(
                review.user_id, gang_results
            )
            if gang_penalty > 0:
                authenticity_score = max(0.0, authenticity_score - gang_penalty)
                all_warnings.extend(gang_warnings)

            user_gangs = self.gang_detector.check_user_in_gangs(review.user_id, gang_results)
            if user_gangs:
                gang_detection = user_gangs[0]

        if review.user_profile is not None:
            reputation_score, rep_warnings = self.user_reputation_model.calculate_reputation(
                review.user_profile, now
            )
        else:
            reputation_score, rep_warnings = self.user_reputation_model.get_default_reputation(
                review.user_id
            )
        all_warnings.extend(rep_warnings)

        usefulness_score, use_warnings = self.rule_engine.analyze_usefulness(review)
        all_warnings.extend(use_warnings)

        completeness_score, comp_warnings = self.rule_engine.analyze_completeness(review)
        all_warnings.extend(comp_warnings)

        dimension_scores = DimensionScores(
            authenticity=authenticity_score,
            usefulness=usefulness_score,
            completeness=completeness_score,
            user_reputation=reputation_score
        )

        overall_score = self._calculate_overall_score(dimension_scores)

        adoption_analysis = None
        if self.adoption_analyzer:
            adoption_analysis = self.adoption_analyzer.analyze_adoption(review)

        merchant_reply_impact = None
        if self.merchant_reply_analyzer and review.merchant_reply:
            overall_score, merchant_reply_impact = self.merchant_reply_analyzer.apply_reply_to_score(
                review, overall_score
            )

        should_collapse = self._should_collapse(overall_score)
        is_low_quality = self._is_low_quality(overall_score)

        sort_score, time_factor = self._calculate_sort_score(review, overall_score, now)

        return ReviewQualityResult(
            review_id=review.review_id,
            overall_score=overall_score,
            dimension_scores=dimension_scores,
            purchase_verification=purchase_detail,
            should_collapse=should_collapse,
            is_low_quality=is_low_quality,
            sort_score=sort_score,
            time_factor=time_factor,
            gang_detection=gang_detection,
            adoption_analysis=adoption_analysis,
            merchant_reply_impact=merchant_reply_impact,
            warnings=all_warnings,
            processed_at=now
        )

    def score_batch(
        self,
        reviews: List[ReviewItem],
        vote_records: Optional[List[VoteRecord]] = None
    ) -> Tuple[List[ReviewQualityResult], int, int, int, List[GangDetectionResult], List[AdoptionAnalysisResult]]:
        now = datetime.now()

        gang_results = []
        if self.gang_detector and vote_records:
            gang_results = self.gang_detector.detect_gangs(reviews, vote_records)

        results = []
        for review in reviews:
            result = self.score_review(review, now, gang_results)
            results.append(result)

        top_adopted = []
        if self.adoption_analyzer:
            top_adopted = self.adoption_analyzer.rank_by_adoption(reviews)

        low_quality_count = sum(1 for r in results if r.is_low_quality)
        collapsed_count = sum(1 for r in results if r.should_collapse)

        return results, len(results), low_quality_count, collapsed_count, gang_results, top_adopted

    def sort_reviews(
        self,
        results: List[ReviewQualityResult],
        collapse_low_quality: bool = True
    ) -> List[ReviewQualityResult]:
        filtered = results
        if collapse_low_quality:
            filtered = [r for r in results if not r.should_collapse]

        sorted_results = sorted(
            filtered,
            key=lambda x: x.sort_score,
            reverse=True
        )

        return sorted_results
