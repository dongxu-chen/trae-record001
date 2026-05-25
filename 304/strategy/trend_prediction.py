import logging
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta
from collections import defaultdict, deque
import numpy as np
from dataclasses import dataclass, field

from config import config
from data.models import RecommendationResult

logger = logging.getLogger(__name__)


@dataclass
class SocialMediaTrend:
    trend_id: int
    keyword: str
    category: str
    volume: int
    growth_rate: float
    velocity: float
    sentiment: float
    peak_time: Optional[datetime] = None
    related_news_ids: List[int] = field(default_factory=list)
    source: str = "social"


@dataclass
class TrendingNewsPrediction:
    news_id: int
    predicted_hot_score: float
    trend_score: float
    growth_potential: float
    time_to_peak: float
    confidence: float
    related_trends: List[str] = field(default_factory=list)
    is_emerging: bool = False


class TrendPredictor:
    def __init__(
        self,
        prediction_window_hours: int = None,
        growth_threshold: float = None,
        social_weight: float = None,
        engagement_weight: float = None,
        decay_hours: int = None
    ):
        self.prediction_window = prediction_window_hours or config.TREND_PREDICTION_WINDOW_HOURS
        self.growth_threshold = growth_threshold or config.TREND_GROWTH_THRESHOLD
        self.social_weight = social_weight or config.TREND_SOCIAL_WEIGHT
        self.engagement_weight = engagement_weight or config.TREND_ENGAGEMENT_WEIGHT
        self.decay_hours = decay_hours or config.TREND_DECAY_HOURS

        self._trend_history: Dict[str, deque] = defaultdict(lambda: deque(maxlen=24))
        self._social_trends: Dict[str, SocialMediaTrend] = {}
        self._news_trend_scores: Dict[int, List[float]] = defaultdict(list)

    def _calculate_growth_rate(
        self,
        current_volume: int,
        past_volumes: List[int]
    ) -> float:
        if not past_volumes:
            return 1.0

        avg_past = np.mean(past_volumes)
        if avg_past <= 0:
            return float('inf') if current_volume > 0 else 1.0

        return current_volume / avg_past

    def _calculate_velocity(
        self,
        volume_series: List[int],
        time_intervals_hours: List[float]
    ) -> float:
        if len(volume_series) < 2:
            return 0.0

        velocities = []
        for i in range(1, len(volume_series)):
            dt = max(time_intervals_hours[i], 0.1)
            dv = volume_series[i] - volume_series[i-1]
            velocities.append(dv / dt)

        return float(np.mean(velocities)) if velocities else 0.0

    def _time_decay(self, hours_passed: float) -> float:
        return float(np.exp(-np.log(2) * hours_passed / self.decay_hours))

    def detect_trends_from_social(
        self,
        social_data: List[Dict]
    ) -> List[SocialMediaTrend]:
        trend_id_counter = max(self._social_trends.keys(), default=0) + 1
        new_trends = []

        keyword_groups = defaultdict(list)
        for data in social_data:
            keyword = data.get('keyword', '').lower()
            if keyword:
                keyword_groups[keyword].append(data)

        for keyword, posts in keyword_groups.items():
            current_volume = len(posts)
            timestamps = [self._parse_time(p.get('timestamp')) for p in posts if p.get('timestamp')]
            timestamps.sort()

            category = posts[0].get('category', '') if posts else ''
            sentiment = np.mean([p.get('sentiment', 0.0) for p in posts]) if posts else 0.0

            past_data = list(self._trend_history.get(keyword, []))
            past_volumes = [d['volume'] for d in past_data] if past_data else []

            growth_rate = self._calculate_growth_rate(current_volume, past_volumes)

            volume_series = past_volumes + [current_volume]
            time_intervals = [1.0] * len(volume_series)
            velocity = self._calculate_velocity(volume_series, time_intervals)

            related_news = []
            for p in posts:
                nid = p.get('news_id')
                if nid is not None:
                    related_news.append(nid)

            peak_time = None
            if velocity < 0 and len(volume_series) > 2:
                peak_idx = volume_series.index(max(volume_series))
                if peak_idx < len(volume_series) - 1:
                    peak_time = datetime.now() - timedelta(hours=(len(volume_series) - 1 - peak_idx))

            trend = SocialMediaTrend(
                trend_id=trend_id_counter,
                keyword=keyword,
                category=category,
                volume=current_volume,
                growth_rate=growth_rate,
                velocity=velocity,
                sentiment=sentiment,
                peak_time=peak_time,
                related_news_ids=list(set(related_news))
            )

            self._social_trends[keyword] = trend
            self._trend_history[keyword].append({
                'timestamp': datetime.now(),
                'volume': current_volume,
                'growth_rate': growth_rate
            })

            new_trends.append(trend)
            trend_id_counter += 1

        logger.info(f"Detected {len(new_trends)} social trends")
        return new_trends

    def _parse_time(self, ts) -> Optional[datetime]:
        if isinstance(ts, datetime):
            return ts
        if isinstance(ts, str):
            try:
                return datetime.fromisoformat(ts)
            except (ValueError, TypeError):
                pass
        return datetime.now()

    def predict_trending_news(
        self,
        all_news: List[Dict],
        news_stats: Dict[int, Dict],
        social_trends: Optional[List[SocialMediaTrend]] = None,
        top_n: int = 20
    ) -> List[TrendingNewsPrediction]:
        social_trends = social_trends or list(self._social_trends.values())

        keyword_to_news = defaultdict(list)
        for trend in social_trends:
            for news_id in trend.related_news_ids:
                keyword_to_news[news_id].append(trend)

        predictions = []
        now = datetime.now()

        for news in all_news:
            news_id = news['news_id']
            stats = news_stats.get(news_id, {})
            publish_time = self._parse_time(news.get('publish_time', now.isoformat()))
            hours_since_publish = (now - publish_time).total_seconds() / 3600

            engagement_score = self._calculate_engagement_score(stats, hours_since_publish)
            social_score, related_trends_list = self._calculate_social_score(news_id, keyword_to_news)

            trend_score = (
                self.social_weight * social_score +
                self.engagement_weight * engagement_score
            )

            click_growth = stats.get('click_growth_rate', 1.0)
            like_growth = stats.get('like_growth_rate', 1.0)
            share_growth = stats.get('share_growth_rate', 1.0)
            avg_growth = np.mean([click_growth, like_growth, share_growth])

            is_emerging = (
                avg_growth >= self.growth_threshold and
                hours_since_publish < self.prediction_window * 4
            )

            growth_potential = self._calculate_growth_potential(
                avg_growth, hours_since_publish, social_score
            )

            time_to_peak = self._estimate_time_to_peak(
                avg_growth, hours_since_publish, social_score
            )

            confidence = self._calculate_prediction_confidence(
                stats, social_score, hours_since_publish
            )

            predicted_hot_score = trend_score * growth_potential * self._time_decay(hours_since_publish)

            prediction = TrendingNewsPrediction(
                news_id=news_id,
                predicted_hot_score=float(predicted_hot_score),
                trend_score=float(trend_score),
                growth_potential=float(growth_potential),
                time_to_peak=float(time_to_peak),
                confidence=float(confidence),
                related_trends=related_trends_list,
                is_emerging=is_emerging
            )

            predictions.append(prediction)

        predictions.sort(key=lambda x: x.predicted_hot_score, reverse=True)
        return predictions[:top_n]

    def _calculate_engagement_score(
        self,
        stats: Dict,
        hours_since_publish: float
    ) -> float:
        clicks = stats.get('click_count', 0)
        likes = stats.get('like_count', 0)
        shares = stats.get('share_count', 0)
        total_duration = stats.get('total_duration', 0.0)

        if hours_since_publish < 0.1:
            return 0.0

        click_rate = clicks / hours_since_publish
        like_rate = likes / hours_since_publish
        share_rate = shares / hours_since_publish
        duration_rate = total_duration / hours_since_publish

        base_score = (
            click_rate * 1.0 +
            like_rate * 3.0 +
            share_rate * 5.0 +
            duration_rate * 0.01
        )

        normalized = 1.0 - np.exp(-base_score / 100.0)
        return normalized

    def _calculate_social_score(
        self,
        news_id: int,
        keyword_to_news: Dict[int, List[SocialMediaTrend]]
    ) -> Tuple[float, List[str]]:
        related_trends = keyword_to_news.get(news_id, [])

        if not related_trends:
            return 0.0, []

        scores = []
        trend_keywords = []
        for trend in related_trends:
            growth_component = min(trend.growth_rate / 5.0, 1.0)
            volume_component = min(np.log1p(trend.volume) / 5.0, 1.0)
            sentiment_component = (trend.sentiment + 1.0) / 2.0

            trend_score = (
                0.5 * growth_component +
                0.3 * volume_component +
                0.2 * sentiment_component
            )

            scores.append(trend_score)
            trend_keywords.append(trend.keyword)

        if scores:
            return float(max(scores)), list(set(trend_keywords))
        return 0.0, []

    def _calculate_growth_potential(
        self,
        avg_growth: float,
        hours_since_publish: float,
        social_score: float
    ) -> float:
        growth_factor = min(avg_growth, 10.0)
        recency_factor = self._time_decay(hours_since_publish)
        social_factor = 1.0 + social_score

        potential = growth_factor * recency_factor * social_factor
        return min(potential, 5.0)

    def _estimate_time_to_peak(
        self,
        avg_growth: float,
        hours_since_publish: float,
        social_score: float
    ) -> float:
        if avg_growth <= 1.0:
            return 0.0

        base_peak = self.prediction_window

        if avg_growth > 3.0:
            base_peak *= 0.5
        elif avg_growth > 2.0:
            base_peak *= 0.7

        if social_score > 0.7:
            base_peak *= 0.6

        remaining = max(0.0, base_peak - hours_since_publish)
        return remaining

    def _calculate_prediction_confidence(
        self,
        stats: Dict,
        social_score: float,
        hours_since_publish: float
    ) -> float:
        data_points = (
            stats.get('click_count', 0) +
            stats.get('like_count', 0) +
            stats.get('share_count', 0)
        )

        data_confidence = min(np.log1p(data_points) / np.log(100), 1.0)
        social_confidence = social_score

        if hours_since_publish < 1:
            time_confidence = 0.5
        elif hours_since_publish < 6:
            time_confidence = 0.7
        else:
            time_confidence = min(1.0, hours_since_publish / 24.0)

        confidence = 0.4 * data_confidence + 0.3 * social_confidence + 0.3 * time_confidence
        return confidence

    def get_emerging_news(
        self,
        predictions: List[TrendingNewsPrediction],
        top_n: int = 10
    ) -> List[TrendingNewsPrediction]:
        emerging = [p for p in predictions if p.is_emerging]
        emerging.sort(key=lambda x: x.growth_potential, reverse=True)
        return emerging[:top_n]

    def get_trending_recommendations(
        self,
        all_news: List[Dict],
        news_stats: Dict[int, Dict],
        social_trends: Optional[List[SocialMediaTrend]] = None,
        top_n: int = 10,
        prefer_emerging: bool = True
    ) -> List[RecommendationResult]:
        predictions = self.predict_trending_news(all_news, news_stats, social_trends, top_n=top_n * 2)
        news_dict = {news['news_id']: news for news in all_news}

        if prefer_emerging:
            emerging = self.get_emerging_news(predictions, top_n=top_n)
            remaining = [p for p in predictions if not p.is_emerging]
            selected = emerging + remaining
        else:
            selected = predictions

        selected = selected[:top_n]

        results = []
        for rank, pred in enumerate(selected, 1):
            news = news_dict.get(pred.news_id, {})
            category = news.get('category', '')

            reason_parts = []
            if pred.is_emerging:
                reason_parts.append("正在快速升温")
            if pred.related_trends:
                top_trends = pred.related_trends[:2]
                reason_parts.append(f"关联话题: {', '.join(top_trends)}")
            if pred.growth_potential > 2.0:
                reason_parts.append("高增长潜力")

            reason = " · ".join(reason_parts) if reason_parts else "趋势预测"

            results.append(RecommendationResult(
                news_id=pred.news_id,
                score=pred.predicted_hot_score,
                category=category,
                rank=rank,
                is_hot=True,
                reason=reason
            ))

        return results

    def update_trend_for_news(
        self,
        news_id: int,
        interaction_type: str,
        timestamp: Optional[datetime] = None
    ):
        timestamp = timestamp or datetime.now()
        self._news_trend_scores[news_id].append(timestamp.timestamp())

        if len(self._news_trend_scores[news_id]) > 100:
            self._news_trend_scores[news_id] = self._news_trend_scores[news_id][-100:]

    def get_trend_statistics(self) -> Dict:
        return {
            'active_trends': len(self._social_trends),
            'growing_trends': sum(1 for t in self._social_trends.values() if t.growth_rate > 1.5),
            'decaying_trends': sum(1 for t in self._social_trends.values() if t.peak_time is not None),
            'monitored_news': len(self._news_trend_scores)
        }
