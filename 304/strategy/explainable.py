import logging
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta
from collections import defaultdict
import numpy as np
from dataclasses import dataclass, field

from config import config
from data.models import UserProfile, RecommendationResult

logger = logging.getLogger(__name__)


@dataclass
class ReasonDetail:
    reason_type: str
    description: str
    confidence: float
    evidence: Dict = field(default_factory=dict)
    related_news_ids: List[int] = field(default_factory=list)


@dataclass
class ExplainableRecommendation:
    news_id: int
    score: float
    category: str
    reasons: List[ReasonDetail] = field(default_factory=list)
    primary_reason: str = ""

    def to_dict(self) -> Dict:
        return {
            'news_id': self.news_id,
            'score': float(self.score),
            'category': self.category,
            'primary_reason': self.primary_reason,
            'reasons': [
                {
                    'type': r.reason_type,
                    'description': r.description,
                    'confidence': float(r.confidence),
                    'evidence': r.evidence,
                    'related_news_ids': r.related_news_ids
                }
                for r in self.reasons
            ]
        }


class RecommendationExplainer:
    def __init__(
        self,
        max_reasons: int = None,
        min_behavior_count: int = None,
        similarity_threshold: float = None
    ):
        self.max_reasons = max_reasons or config.EXPLANATION_MAX_REASONS
        self.min_behavior_count = min_behavior_count or config.EXPLANATION_MIN_BEHAVIOR_COUNT
        self.similarity_threshold = similarity_threshold or config.EXPLANATION_SIMILARITY_THRESHOLD

        self._news_titles_cache: Dict[int, Dict] = {}

    def _parse_time(self, ts) -> Optional[datetime]:
        if isinstance(ts, datetime):
            return ts
        if isinstance(ts, str):
            try:
                return datetime.fromisoformat(ts)
            except (ValueError, TypeError):
                pass
        return datetime.now()

    def _calculate_category_similarity(
        self,
        target_category: str,
        behavior_categories: List[str]
    ) -> float:
        if not behavior_categories:
            return 0.0

        match_count = sum(1 for c in behavior_categories if c == target_category)
        match_ratio = match_count / len(behavior_categories)
        return min(1.0, 0.3 + 0.7 * match_ratio)

    def _get_recent_behavior_categories(
        self,
        user_profile: UserProfile,
        hours: int = 168
    ) -> List[str]:
        if not user_profile.recent_behavior:
            return []

        cutoff = datetime.now() - timedelta(hours=hours)
        categories = []

        for behavior in user_profile.recent_behavior:
            ts = self._parse_time(behavior.get('timestamp'))
            if ts >= cutoff:
                cat = behavior.get('category')
                if cat:
                    categories.append(cat)

        return categories

    def _get_read_news_for_category(
        self,
        user_profile: UserProfile,
        category: str,
        limit: int = 3
    ) -> List[Dict]:
        if not user_profile.recent_behavior:
            return []

        matching = []
        for behavior in user_profile.recent_behavior:
            if (behavior.get('category') == category and
                behavior.get('behavior_type') in ['view', 'like', 'share']):
                matching.append(behavior)
                if len(matching) >= limit:
                    break

        return matching

    def explain_by_category_preference(
        self,
        user_profile: UserProfile,
        recommendation: RecommendationResult
    ) -> Optional[ReasonDetail]:
        category = recommendation.category
        pref_score = user_profile.category_preferences.get(category, 0.0)

        if pref_score < 0.6:
            return None

        read_news = self._get_read_news_for_category(user_profile, category, limit=3)

        if len(read_news) < self.min_behavior_count:
            return None

        related_news_ids = [b.get('news_id') for b in read_news if b.get('news_id') is not None]

        confidence = min(1.0, 0.5 + 0.5 * pref_score)

        if related_news_ids:
            description = f"因您阅读过{category}类别的新闻"
            if len(related_news_ids) >= 2:
                description += f"（如新闻 {', '.join(map(str, related_news_ids[:2]))}）"
            else:
                description += f"（如新闻 {related_news_ids[0]}）"
        else:
            description = f"基于您对{category}内容的偏好"

        return ReasonDetail(
            reason_type="category_preference",
            description=description,
            confidence=confidence,
            evidence={
                'category': category,
                'preference_score': pref_score,
                'related_news_count': len(read_news)
            },
            related_news_ids=related_news_ids
        )

    def explain_by_similar_behavior(
        self,
        user_profile: UserProfile,
        recommendation: RecommendationResult,
        news_embeddings: Optional[Dict[int, np.ndarray]] = None,
        recommendation_embedding: Optional[np.ndarray] = None
    ) -> Optional[ReasonDetail]:
        if not user_profile.recent_behavior or news_embeddings is None or recommendation_embedding is None:
            return None

        similar_behaviors = []
        for behavior in user_profile.recent_behavior[:20]:
            news_id = behavior.get('news_id')
            if news_id is None or news_id not in news_embeddings:
                continue

            behavior_emb = news_embeddings[news_id]
            similarity = np.dot(recommendation_embedding, behavior_emb) / (
                np.linalg.norm(recommendation_embedding) * np.linalg.norm(behavior_emb)
            )

            if similarity >= self.similarity_threshold:
                similar_behaviors.append((behavior, similarity))

        if not similar_behaviors:
            return None

        similar_behaviors.sort(key=lambda x: x[1], reverse=True)
        top_similar = similar_behaviors[:3]

        avg_similarity = np.mean([s[1] for s in top_similar])
        related_news_ids = [s[0].get('news_id') for s in top_similar if s[0].get('news_id') is not None]

        description_parts = ["与您之前阅读过的"]
        if related_news_ids:
            description_parts.append(f"新闻 {', '.join(map(str, related_news_ids[:2]))}")
        else:
            description_parts.append("文章")
        description_parts.append("内容相似")

        return ReasonDetail(
            reason_type="content_similarity",
            description="".join(description_parts),
            confidence=float(avg_similarity),
            evidence={
                'average_similarity': float(avg_similarity),
                'similar_count': len(similar_behaviors)
            },
            related_news_ids=related_news_ids
        )

    def explain_by_hot_trend(
        self,
        recommendation: RecommendationResult,
        trend_info: Optional[Dict] = None
    ) -> Optional[ReasonDetail]:
        if not recommendation.is_hot and not trend_info:
            return None

        confidence = 0.8 if recommendation.is_hot else 0.6
        description = "热门推荐"
        evidence = {'is_hot': recommendation.is_hot}

        if trend_info:
            if trend_info.get('is_emerging'):
                description = "正在快速升温的热门新闻"
                confidence = max(confidence, 0.85)
            if trend_info.get('related_trends'):
                trends = trend_info['related_trends'][:2]
                description += f"（关联话题: {', '.join(trends)}）"
            evidence.update(trend_info)

        return ReasonDetail(
            reason_type="hot_trend",
            description=description,
            confidence=confidence,
            evidence=evidence
        )

    def explain_by_multi_objective(
        self,
        recommendation: RecommendationResult,
        objective_scores: Optional[Dict[str, float]] = None
    ) -> Optional[ReasonDetail]:
        if not objective_scores:
            return None

        reasons = []

        click_score = objective_scores.get('click', 0.0)
        duration_score = objective_scores.get('duration', 0.0)

        if click_score >= 0.7:
            reasons.append(("高点击率预估", click_score))

        if duration_score >= 0.7:
            reasons.append(("预计您会感兴趣并停留较长时间", duration_score))

        if not reasons:
            return None

        reasons.sort(key=lambda x: x[1], reverse=True)
        best_reason, confidence = reasons[0]

        return ReasonDetail(
            reason_type="multi_objective",
            description=best_reason,
            confidence=confidence,
            evidence=objective_scores,
            related_news_ids=[]
        )

    def explain_by_time_pattern(
        self,
        user_profile: UserProfile,
        recommendation: RecommendationResult
    ) -> Optional[ReasonDetail]:
        if not user_profile.recent_behavior:
            return None

        now = datetime.now()
        current_hour = now.hour
        current_weekday = now.weekday()

        category = recommendation.category

        time_patterns = defaultdict(lambda: defaultdict(int))
        weekday_patterns = defaultdict(lambda: defaultdict(int))

        for behavior in user_profile.recent_behavior:
            ts = self._parse_time(behavior.get('timestamp'))
            hour = ts.hour
            weekday = ts.weekday()
            cat = behavior.get('category')

            if cat:
                time_patterns[hour][cat] += 1
                weekday_patterns[weekday][cat] += 1

        current_hour_categories = time_patterns.get(current_hour, {})
        current_weekday_categories = weekday_patterns.get(current_weekday, {})

        hour_count = current_hour_categories.get(category, 0)
        weekday_count = current_weekday_categories.get(category, 0)

        if hour_count < self.min_behavior_count and weekday_count < self.min_behavior_count:
            return None

        total_hour = sum(current_hour_categories.values())
        total_weekday = sum(current_weekday_categories.values())

        hour_ratio = hour_count / total_hour if total_hour > 0 else 0
        weekday_ratio = weekday_count / total_weekday if total_weekday > 0 else 0

        confidence = max(hour_ratio, weekday_ratio)

        if hour_count >= self.min_behavior_count and weekday_count >= self.min_behavior_count:
            description = f"您通常在这个时间喜欢阅读{category}新闻"
            confidence = min(1.0, confidence + 0.2)
        elif hour_count >= self.min_behavior_count:
            description = f"您这个时段常看{category}内容"
        else:
            description = f"您今天常看{category}内容"

        return ReasonDetail(
            reason_type="time_pattern",
            description=description,
            confidence=float(min(1.0, confidence)),
            evidence={
                'current_hour': current_hour,
                'current_weekday': current_weekday,
                'hour_count': hour_count,
                'weekday_count': weekday_count
            }
        )

    def explain_by_friends_activity(
        self,
        recommendation: RecommendationResult,
        friend_behaviors: Optional[List[Dict]] = None
    ) -> Optional[ReasonDetail]:
        if not friend_behaviors:
            return None

        matching = []
        for fb in friend_behaviors:
            if fb.get('news_id') == recommendation.news_id:
                matching.append(fb)

        if not matching:
            return None

        friend_names = list(set([fb.get('friend_name', '朋友') for fb in matching]))
        confidence = min(1.0, 0.5 + 0.1 * len(matching))

        if len(friend_names) >= 3:
            description = f"{len(friend_names)}等多位朋友也在看"
        elif len(friend_names) >= 2:
            description = f"{', '.join(friend_names)}也在看"
        else:
            description = f"{friend_names[0]}也在看"

        return ReasonDetail(
            reason_type="social",
            description=description,
            confidence=confidence,
            evidence={
                'friend_count': len(matching),
                'friend_names': friend_names
            },
            related_news_ids=[recommendation.news_id]
        )

    def generate_explanations(
        self,
        user_profile: UserProfile,
        recommendations: List[RecommendationResult],
        news_embeddings: Optional[Dict[int, np.ndarray]] = None,
        recommendation_embeddings: Optional[Dict[int, np.ndarray]] = None,
        trend_infos: Optional[Dict[int, Dict]] = None,
        objective_scores: Optional[Dict[int, Dict[str, float]]] = None,
        friend_behaviors: Optional[List[Dict]] = None
    ) -> List[ExplainableRecommendation]:
        explained = []

        for rec in recommendations:
            reasons = []

            category_reason = self.explain_by_category_preference(user_profile, rec)
            if category_reason:
                reasons.append(category_reason)

            rec_emb = None
            if recommendation_embeddings and rec.news_id in recommendation_embeddings:
                rec_emb = recommendation_embeddings[rec.news_id]

            similar_reason = self.explain_by_similar_behavior(
                user_profile, rec, news_embeddings, rec_emb
            )
            if similar_reason:
                reasons.append(similar_reason)

            trend_info = None
            if trend_infos and rec.news_id in trend_infos:
                trend_info = trend_infos[rec.news_id]
            hot_reason = self.explain_by_hot_trend(rec, trend_info)
            if hot_reason:
                reasons.append(hot_reason)

            obj_scores = None
            if objective_scores and rec.news_id in objective_scores:
                obj_scores = objective_scores[rec.news_id]
            mo_reason = self.explain_by_multi_objective(rec, obj_scores)
            if mo_reason:
                reasons.append(mo_reason)

            time_reason = self.explain_by_time_pattern(user_profile, rec)
            if time_reason:
                reasons.append(time_reason)

            social_reason = self.explain_by_friends_activity(rec, friend_behaviors)
            if social_reason:
                reasons.append(social_reason)

            reasons.sort(key=lambda r: r.confidence, reverse=True)
            reasons = reasons[:self.max_reasons]

            primary_reason = reasons[0].description if reasons else ""

            explained_rec = ExplainableRecommendation(
                news_id=rec.news_id,
                score=rec.score,
                category=rec.category,
                reasons=reasons,
                primary_reason=primary_reason
            )

            explained.append(explained_rec)

            if rec.reason and not primary_reason:
                explained_rec.primary_reason = rec.reason
            elif rec.reason and primary_reason:
                explained_rec.primary_reason = f"{primary_reason} · {rec.reason}"

        return explained

    def format_explanations_for_api(
        self,
        explained_recommendations: List[ExplainableRecommendation]
    ) -> List[Dict]:
        return [er.to_dict() for er in explained_recommendations]

    def get_explanation_statistics(
        self,
        explained_recommendations: List[ExplainableRecommendation]
    ) -> Dict:
        reason_type_counts = defaultdict(int)
        avg_confidences = []

        for er in explained_recommendations:
            for reason in er.reasons:
                reason_type_counts[reason.reason_type] += 1
                avg_confidences.append(reason.confidence)

        return {
            'total_recommendations': len(explained_recommendations),
            'reason_type_distribution': dict(reason_type_counts),
            'average_confidence': float(np.mean(avg_confidences)) if avg_confidences else 0.0,
            'reasons_per_recommendation': float(np.mean([len(er.reasons) for er in explained_recommendations])) if explained_recommendations else 0.0
        }
