import math
from typing import Tuple, List, Dict, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

from config import settings
from schemas import UserProfile, ReputationEvent, ReputationEventType


class UserReputationModel:
    def __init__(self):
        self.default_reputation = 50.0
        self._reputation_cache: Dict[str, float] = {}

    def _calculate_account_age_score(self, age_days: int) -> float:
        if age_days <= 0:
            return 20.0

        score = 100.0 * (1 - math.exp(-age_days / 180.0))
        return min(100.0, max(0.0, score))

    def _calculate_review_history_score(self, profile: UserProfile) -> float:
        if profile.total_reviews == 0:
            return 40.0

        verified_ratio = profile.verified_purchases / max(profile.total_reviews, 1)
        verified_score = 30.0 + verified_ratio * 70.0

        review_count_score = min(profile.total_reviews * 5, 100.0)

        avg_rating = profile.average_rating
        if avg_rating >= 4.8 or avg_rating <= 1.2:
            rating_bias_penalty = 30.0
        elif avg_rating >= 4.5 or avg_rating <= 1.5:
            rating_bias_penalty = 15.0
        else:
            rating_bias_penalty = 0.0

        history_score = (
            verified_score * 0.5 +
            review_count_score * 0.3 +
            (100.0 - rating_bias_penalty) * 0.2
        )

        return history_score

    def _calculate_helpfulness_score(self, profile: UserProfile) -> float:
        if profile.total_reviews == 0:
            return 50.0

        avg_helpful = profile.helpful_votes_received / max(profile.total_reviews, 1)

        if avg_helpful == 0:
            return 30.0

        score = 50.0 + 50.0 * (1 - math.exp(-avg_helpful / 5.0))
        return min(100.0, max(0.0, score))

    def _calculate_removal_penalty(self, removal_count: int) -> float:
        if removal_count == 0:
            return 100.0

        penalty = min(removal_count * 20.0, 80.0)
        return max(0.0, 100.0 - penalty)

    def _process_event_impact(self, event: ReputationEvent, now: datetime) -> float:
        event_type_str = event.event_type.value if isinstance(event.event_type, ReputationEventType) else event.event_type
        base_impact = settings.REPUTATION_EVENT_WEIGHTS.get(event_type_str, 0.0)

        if base_impact == 0.0:
            return 0.0

        days_since_event = max(0, (now - event.event_time).total_seconds() / 86400.0)
        decay_factor = math.exp(-days_since_event / settings.REPUTATION_EVENT_DECAY_DAYS)

        severity_multiplier = event.severity

        return base_impact * decay_factor * severity_multiplier

    def _calculate_event_driven_score(self, profile: UserProfile, now: datetime) -> Tuple[float, List[str]]:
        warnings = []
        total_impact = 0.0

        negative_events = []
        positive_events = []

        for event in profile.reputation_events:
            impact = self._process_event_impact(event, now)
            total_impact += impact

            event_type_str = event.event_type.value if isinstance(event.event_type, ReputationEventType) else event.event_type
            if impact < 0:
                negative_events.append((event, impact))
            elif impact > 0:
                positive_events.append((event, impact))

        recent_malicious = [
            (e, imp) for e, imp in negative_events
            if (now - e.event_time).total_seconds() < 7 * 86400
        ]

        if recent_malicious:
            total_malicious_impact = sum(imp for _, imp in recent_malicious)
            if total_malicious_impact < -30:
                total_impact *= 1.5
                warnings.append(f"近7天内存在严重恶意行为，额外降权50%")

        brush_events = [
            e for e in profile.reputation_events
            if (isinstance(e.event_type, ReputationEventType) and e.event_type == ReputationEventType.BRUSH_ORDER_REPORTED)
            or e.event_type == "brush_order_reported"
        ]
        if len(brush_events) >= 2:
            total_impact += -10.0 * len(brush_events)
            warnings.append(f"多次刷单举报记录({len(brush_events)}次)，严重降权")

        fake_events = [
            e for e in profile.reputation_events
            if (isinstance(e.event_type, ReputationEventType) and e.event_type == ReputationEventType.FAKE_REVIEW_DETECTED)
            or e.event_type == "fake_review_detected"
        ]
        if len(fake_events) >= 2:
            total_impact += -8.0 * len(fake_events)
            warnings.append(f"多次虚假评论检测({len(fake_events)}次)，严重降权")

        event_score = max(0.0, min(100.0, 50.0 + total_impact))

        if negative_events:
            recent_neg = [
                e for e, _ in negative_events
                if (now - e.event_time).total_seconds() < 3 * 86400
            ]
            for e in recent_neg:
                event_type_str = e.event_type.value if isinstance(e.event_type, ReputationEventType) else e.event_type
                if event_type_str == "fake_review_detected":
                    warnings.append("近期存在虚假评论检测记录，信誉实时降权")
                elif event_type_str == "brush_order_reported":
                    warnings.append("近期存在刷单举报记录，信誉实时降权")
                elif event_type_str == "malicious_review_reported":
                    warnings.append("近期存在恶意评论举报，信誉实时降权")
                elif event_type_str == "review_removed":
                    warnings.append("近期有评论被移除，信誉受影响")

        return event_score, warnings

    def calculate_reputation(self, profile: UserProfile, now: datetime = None) -> Tuple[float, List[str]]:
        if now is None:
            now = datetime.now()

        warnings = []

        base_age_score = self._calculate_account_age_score(profile.account_age_days)
        base_history_score = self._calculate_review_history_score(profile)
        base_helpfulness_score = self._calculate_helpfulness_score(profile)
        base_removal_score = self._calculate_removal_penalty(profile.review_removal_count)

        if profile.account_age_days < 7:
            warnings.append("账号注册时间较短")

        if profile.total_reviews == 0:
            warnings.append("用户无历史评论记录")

        if profile.verified_purchases < profile.total_reviews * 0.5:
            warnings.append("已验证购买比例较低")

        if profile.review_removal_count > 0:
            warnings.append(f"用户有 {profile.review_removal_count} 条评论被移除记录")

        if profile.average_rating >= 4.8:
            warnings.append("用户历史评分普遍偏高，可能存在好评偏好")
        elif profile.average_rating <= 1.2:
            warnings.append("用户历史评分普遍偏低，可能存在差评偏好")

        base_reputation = (
            base_age_score * 0.25 +
            base_history_score * 0.35 +
            base_helpfulness_score * 0.25 +
            base_removal_score * 0.15
        )

        if profile.reputation_events:
            event_score, event_warnings = self._calculate_event_driven_score(profile, now)
            warnings.extend(event_warnings)

            reputation_score = base_reputation * 0.4 + event_score * 0.6
        else:
            reputation_score = base_reputation

        reputation_score = round(
            min(settings.REPUTATION_MAX_SCORE, max(settings.REPUTATION_MIN_SCORE, reputation_score)),
            2
        )

        self._reputation_cache[profile.user_id] = reputation_score

        return reputation_score, warnings

    def process_event(self, user_id: str, event: ReputationEvent, current_profile: UserProfile) -> Tuple[float, List[str]]:
        now = event.event_time

        updated_events = list(current_profile.reputation_events) + [event]
        updated_removal_count = current_profile.review_removal_count
        if event.event_type in (ReputationEventType.REVIEW_REMOVED, "review_removed"):
            updated_removal_count += 1

        updated_profile = UserProfile(
            user_id=current_profile.user_id,
            account_age_days=current_profile.account_age_days,
            total_reviews=current_profile.total_reviews,
            verified_purchases=current_profile.verified_purchases,
            helpful_votes_received=current_profile.helpful_votes_received,
            review_removal_count=updated_removal_count,
            average_rating=current_profile.average_rating,
            registration_date=current_profile.registration_date,
            reputation_events=updated_events,
            current_reputation_score=None
        )

        new_score, warnings = self.calculate_reputation(updated_profile, now)

        updated_profile.current_reputation_score = new_score

        event_type_str = event.event_type.value if isinstance(event.event_type, ReputationEventType) else event.event_type
        if event_type_str in ["fake_review_detected", "brush_order_reported", "malicious_review_reported"]:
            old_score = self._reputation_cache.get(user_id, self.default_reputation)
            drop = old_score - new_score
            if drop > 0:
                warnings.append(f"恶意行为检测，信誉分实时下降 {drop:.1f} 分")

        return new_score, warnings, updated_profile

    def get_reputation_history(self, profile: UserProfile) -> List[Dict]:
        if not profile.reputation_events:
            return []

        history = []
        cumulative_score = self.default_reputation

        for event in sorted(profile.reputation_events, key=lambda e: e.event_time):
            impact = self._process_event_impact(event, event.event_time)
            cumulative_score = max(0.0, min(100.0, cumulative_score + impact))
            event_type_str = event.event_type.value if isinstance(event.event_type, ReputationEventType) else event.event_type

            history.append({
                "event_type": event_type_str,
                "event_time": event.event_time.isoformat(),
                "severity": event.severity,
                "impact": round(impact, 2),
                "cumulative_score": round(cumulative_score, 2)
            })

        return history

    def get_default_reputation(self, user_id: str) -> Tuple[float, List[str]]:
        return self.default_reputation, ["无用户画像数据，使用默认信誉分"]
