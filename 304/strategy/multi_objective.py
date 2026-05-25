import logging
from typing import List, Dict, Optional, Tuple
from datetime import datetime
import numpy as np
from dataclasses import dataclass, field

from config import config
from data.models import RecommendationResult

logger = logging.getLogger(__name__)


@dataclass
class ObjectiveWeights:
    click_weight: float = 0.5
    duration_weight: float = 0.5
    like_weight: float = 0.0
    share_weight: float = 0.0

    def normalize(self):
        total = self.click_weight + self.duration_weight + self.like_weight + self.share_weight
        if total > 0:
            self.click_weight /= total
            self.duration_weight /= total
            self.like_weight /= total
            self.share_weight /= total


@dataclass
class MultiObjectiveScore:
    news_id: int
    click_score: float
    duration_score: float
    like_score: float = 0.0
    share_score: float = 0.0
    combined_score: float = 0.0
    pareto_rank: int = 0
    objective_values: Dict[str, float] = field(default_factory=dict)


class MultiObjectiveOptimizer:
    def __init__(
        self,
        click_weight: float = None,
        duration_weight: float = None,
        duration_normalization: float = None
    ):
        self.click_weight = click_weight or config.MULTI_OBJECTIVE_CLICK_WEIGHT
        self.duration_weight = duration_weight or config.MULTI_OBJECTIVE_DURATION_WEIGHT
        self.duration_normalization = duration_normalization or config.MULTI_OBJECTIVE_DURATION_NORMALIZATION

        self._objective_stats: Dict[str, Dict] = {
            'click': {'min': 0.0, 'max': 1.0, 'mean': 0.5},
            'duration': {'min': 0.0, 'max': 1.0, 'mean': 0.5},
            'like': {'min': 0.0, 'max': 1.0, 'mean': 0.5},
            'share': {'min': 0.0, 'max': 1.0, 'mean': 0.5}
        }

        self.weights = ObjectiveWeights(
            click_weight=self.click_weight,
            duration_weight=self.duration_weight
        )
        self.weights.normalize()

    def _normalize_score(
        self,
        value: float,
        objective: str,
        use_stats: bool = False
    ) -> float:
        if use_stats and objective in self._objective_stats:
            stats = self._objective_stats[objective]
            if stats['max'] > stats['min']:
                return (value - stats['min']) / (stats['max'] - stats['min'])
        return value

    def _sigmoid(self, x: float) -> float:
        return 1.0 / (1.0 + np.exp(-x))

    def calculate_duration_score(
        self,
        predicted_duration: float,
        category: str = "",
        use_category_adjustment: bool = True
    ) -> float:
        if predicted_duration <= 0:
            return 0.0

        normalized = predicted_duration / self.duration_normalization
        score = self._sigmoid(3.0 * (normalized - 0.5))

        if use_category_adjustment and category:
            category_factors = {
                '科技': 1.1,
                '财经': 1.0,
                '体育': 0.9,
                '娱乐': 0.9,
                '教育': 1.1,
                '健康': 1.0,
                '军事': 1.0,
                '旅游': 0.9,
                '美食': 0.9,
                '汽车': 1.0
            }
            factor = category_factors.get(category, 1.0)
            score = min(1.0, score * factor)

        return float(score)

    def calculate_click_score(
        self,
        predicted_ctr: float,
        base_rate: float = 0.05
    ) -> float:
        if predicted_ctr <= 0:
            return 0.0

        if base_rate > 0:
            normalized = predicted_ctr / (base_rate * 5.0)
        else:
            normalized = predicted_ctr

        score = min(1.0, normalized)
        return float(score)

    def calculate_like_score(
        self,
        predicted_like_prob: float
    ) -> float:
        return float(min(1.0, predicted_like_prob))

    def calculate_share_score(
        self,
        predicted_share_prob: float
    ) -> float:
        return float(min(1.0, predicted_share_prob * 2.0))

    def calculate_combined_score(
        self,
        click_score: float,
        duration_score: float,
        like_score: float = 0.0,
        share_score: float = 0.0,
        use_uncertainty_adjustment: bool = False,
        uncertainty: float = 0.0
    ) -> float:
        base_score = (
            self.weights.click_weight * click_score +
            self.weights.duration_weight * duration_score +
            self.weights.like_weight * like_score +
            self.weights.share_weight * share_score
        )

        if use_uncertainty_adjustment:
            ucb_bonus = np.sqrt(2.0 * np.log(1000) / max(1, uncertainty))
            base_score += ucb_bonus * 0.1

        return float(base_score)

    def score_recommendations(
        self,
        recommendations: List[RecommendationResult],
        predicted_durations: Optional[Dict[int, float]] = None,
        predicted_ctrs: Optional[Dict[int, float]] = None,
        predicted_likes: Optional[Dict[int, float]] = None,
        predicted_shares: Optional[Dict[int, float]] = None,
        news_stats: Optional[Dict[int, Dict]] = None
    ) -> List[MultiObjectiveScore]:
        scored = []
        predicted_durations = predicted_durations or {}
        predicted_ctrs = predicted_ctrs or {}

        for rec in recommendations:
            news_id = rec.news_id

            base_score = rec.score

            if news_id in predicted_ctrs:
                click_score = self.calculate_click_score(predicted_ctrs[news_id])
            else:
                click_score = self.calculate_click_score(base_score)

            if news_id in predicted_durations:
                duration_score = self.calculate_duration_score(
                    predicted_durations[news_id],
                    category=rec.category
                )
            else:
                if news_stats and news_id in news_stats:
                    avg_duration = news_stats[news_id].get('avg_duration', 0.0)
                    duration_score = self.calculate_duration_score(
                        avg_duration,
                        category=rec.category
                    )
                else:
                    duration_score = 0.5

            like_score = self.calculate_like_score(predicted_likes.get(news_id, 0.0)) if predicted_likes else 0.0
            share_score = self.calculate_share_score(predicted_shares.get(news_id, 0.0)) if predicted_shares else 0.0

            combined_score = self.calculate_combined_score(
                click_score=click_score,
                duration_score=duration_score,
                like_score=like_score,
                share_score=share_score
            )

            obj_score = MultiObjectiveScore(
                news_id=news_id,
                click_score=click_score,
                duration_score=duration_score,
                like_score=like_score,
                share_score=share_score,
                combined_score=combined_score,
                objective_values={
                    'click': click_score,
                    'duration': duration_score,
                    'like': like_score,
                    'share': share_score
                }
            )

            scored.append(obj_score)

        return scored

    def _dominates(
        self,
        a: MultiObjectiveScore,
        b: MultiObjectiveScore,
        objectives: List[str] = None
    ) -> bool:
        objectives = objectives or ['click', 'duration']

        at_least_one_better = False
        for obj in objectives:
            a_val = a.objective_values.get(obj, 0.0)
            b_val = b.objective_values.get(obj, 0.0)
            if a_val < b_val:
                return False
            if a_val > b_val:
                at_least_one_better = True

        return at_least_one_better

    def calculate_pareto_ranks(
        self,
        scores: List[MultiObjectiveScore],
        objectives: List[str] = None
    ) -> List[MultiObjectiveScore]:
        objectives = objectives or ['click', 'duration']
        n = len(scores)

        if n == 0:
            return scores

        dominated_count = [0] * n
        dominating = [[] for _ in range(n)]

        for i in range(n):
            for j in range(n):
                if i != j and self._dominates(scores[i], scores[j], objectives):
                    dominated_count[j] += 1
                    dominating[i].append(j)

        ranks = [0] * n
        current_rank = 0
        remaining = set(range(n))

        while remaining:
            current_front = [i for i in remaining if dominated_count[i] == 0]

            if not current_front:
                break

            for i in current_front:
                ranks[i] = current_rank
                remaining.remove(i)
                for j in dominating[i]:
                    dominated_count[j] -= 1

            current_rank += 1

        for i, score in enumerate(scores):
            score.pareto_rank = ranks[i]

        return scores

    def optimize_recommendations(
        self,
        recommendations: List[RecommendationResult],
        top_n: int = None,
        predicted_durations: Optional[Dict[int, float]] = None,
        predicted_ctrs: Optional[Dict[int, float]] = None,
        predicted_likes: Optional[Dict[int, float]] = None,
        predicted_shares: Optional[Dict[int, float]] = None,
        news_stats: Optional[Dict[int, Dict]] = None,
        use_pareto: bool = True,
        tradeoff_lambda: float = 1.0
    ) -> List[RecommendationResult]:
        top_n = top_n or config.RECOMMEND_TOP_N

        if len(recommendations) <= top_n:
            return recommendations

        scores = self.score_recommendations(
            recommendations,
            predicted_durations,
            predicted_ctrs,
            predicted_likes,
            predicted_shares,
            news_stats
        )

        if use_pareto:
            scores = self.calculate_pareto_ranks(scores)

            score_map = {s.news_id: s for s in scores}

            recs_with_scores = []
            for rec in recommendations:
                obj_score = score_map.get(rec.news_id)
                if obj_score:
                    adjusted_score = (
                        obj_score.combined_score * tradeoff_lambda -
                        obj_score.pareto_rank * 0.01
                    )
                    recs_with_scores.append((rec, adjusted_score, obj_score))
                else:
                    recs_with_scores.append((rec, rec.score, None))

            recs_with_scores.sort(key=lambda x: x[1], reverse=True)
        else:
            score_map = {s.news_id: s for s in scores}

            recs_with_scores = []
            for rec in recommendations:
                obj_score = score_map.get(rec.news_id)
                if obj_score:
                    recs_with_scores.append((rec, obj_score.combined_score, obj_score))
                else:
                    recs_with_scores.append((rec, rec.score, None))

            recs_with_scores.sort(key=lambda x: x[1], reverse=True)

        selected = []
        for rank, (rec, _, obj_score) in enumerate(recs_with_scores[:top_n], 1):
            rec.rank = rank
            rec.score = _

            if obj_score:
                reason_parts = []
                if obj_score.click_score > 0.7:
                    reason_parts.append("高点击率预估")
                if obj_score.duration_score > 0.7:
                    reason_parts.append("预计较长停留时间")
                if obj_score.pareto_rank == 0 and use_pareto:
                    reason_parts.append("帕累托最优")

                if reason_parts and not rec.reason:
                    rec.reason = " · ".join(reason_parts)
                elif reason_parts:
                    rec.reason = rec.reason + " · " + " · ".join(reason_parts)

            selected.append(rec)

        return selected

    def update_objective_statistics(
        self,
        click_values: List[float] = None,
        duration_values: List[float] = None,
        like_values: List[float] = None,
        share_values: List[float] = None
    ):
        if click_values:
            self._objective_stats['click'].update({
                'min': min(self._objective_stats['click']['min'], min(click_values)),
                'max': max(self._objective_stats['click']['max'], max(click_values)),
                'mean': np.mean([self._objective_stats['click']['mean'], np.mean(click_values)])
            })

        if duration_values:
            self._objective_stats['duration'].update({
                'min': min(self._objective_stats['duration']['min'], min(duration_values)),
                'max': max(self._objective_stats['duration']['max'], max(duration_values)),
                'mean': np.mean([self._objective_stats['duration']['mean'], np.mean(duration_values)])
            })

        logger.info(f"Updated objective stats: {self._objective_stats}")

    def adjust_weights(
        self,
        click_weight: Optional[float] = None,
        duration_weight: Optional[float] = None,
        like_weight: Optional[float] = None,
        share_weight: Optional[float] = None
    ):
        if click_weight is not None:
            self.weights.click_weight = click_weight
        if duration_weight is not None:
            self.weights.duration_weight = duration_weight
        if like_weight is not None:
            self.weights.like_weight = like_weight
        if share_weight is not None:
            self.weights.share_weight = share_weight

        self.weights.normalize()
        logger.info(f"Adjusted weights: {self.weights}")

    def get_objective_breakdown(
        self,
        recommendations: List[RecommendationResult],
        news_stats: Optional[Dict[int, Dict]] = None
    ) -> Dict:
        scores = self.score_recommendations(recommendations, news_stats=news_stats)

        avg_click = np.mean([s.click_score for s in scores]) if scores else 0.0
        avg_duration = np.mean([s.duration_score for s in scores]) if scores else 0.0
        avg_combined = np.mean([s.combined_score for s in scores]) if scores else 0.0

        pareto_front = [s for s in scores if s.pareto_rank == 0] if scores else []

        return {
            'average_click_score': float(avg_click),
            'average_duration_score': float(avg_duration),
            'average_combined_score': float(avg_combined),
            'weights': {
                'click': self.weights.click_weight,
                'duration': self.weights.duration_weight,
                'like': self.weights.like_weight,
                'share': self.weights.share_weight
            },
            'pareto_optimal_count': len(pareto_front),
            'total_candidates': len(scores)
        }

    def predict_duration_from_content(
        self,
        content_length: int,
        category: str = "",
        is_long_form: bool = False
    ) -> float:
        base_reading_speed = 500.0
        estimated_read_time = content_length / base_reading_speed * 60.0

        category_multipliers = {
            '科技': 1.2,
            '财经': 1.1,
            '体育': 0.8,
            '娱乐': 0.9,
            '教育': 1.3,
            '健康': 1.1,
            '军事': 1.0,
            '旅游': 0.9,
            '美食': 0.9,
            '汽车': 1.0
        }

        multiplier = category_multipliers.get(category, 1.0)

        if is_long_form:
            multiplier *= 1.5

        return float(estimated_read_time * multiplier)
