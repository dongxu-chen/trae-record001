import logging
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta
import numpy as np

from config import config
from data.models import RecommendationResult

logger = logging.getLogger(__name__)


class HotNewsProvider:
    def __init__(
        self,
        category_list: List[str] = None,
        hot_news_count: int = None
    ):
        self.category_list = category_list or config.CATEGORY_LIST
        self.hot_news_count = hot_news_count or config.HOT_NEWS_COUNT
        self.hot_score_decay_hours = 24
        self.hot_score_half_life = 12

    def calculate_hot_score(
        self,
        click_count: int,
        like_count: int,
        share_count: int,
        publish_time: datetime,
        view_duration: float = 0.0
    ) -> float:
        now = datetime.now()
        hours_passed = (now - publish_time).total_seconds() / 3600

        time_decay = np.exp(-np.log(2) * hours_passed / self.hot_score_half_life)

        base_score = (
            click_count * 1.0 +
            like_count * 3.0 +
            share_count * 5.0 +
            view_duration * 0.01
        )

        hot_score = base_score * time_decay

        gravity = 1.8
        if hours_passed > 0:
            hot_score = hot_score / (hours_passed + 2) ** gravity

        return hot_score

    def get_hot_news(
        self,
        all_news: List[Dict],
        news_stats: Dict[int, Dict],
        top_n: int = None
    ) -> List[Tuple[int, float]]:
        top_n = top_n or self.hot_news_count

        scored_news = []
        for news in all_news:
            news_id = news['news_id']
            stats = news_stats.get(news_id, {})

            publish_time = self._parse_datetime(news.get('publish_time'))
            if not publish_time:
                publish_time = datetime.now() - timedelta(hours=1)

            hot_score = self.calculate_hot_score(
                click_count=stats.get('click_count', 0),
                like_count=stats.get('like_count', 0),
                share_count=stats.get('share_count', 0),
                publish_time=publish_time,
                view_duration=stats.get('total_duration', 0.0)
            )

            scored_news.append((news_id, hot_score))

        scored_news.sort(key=lambda x: x[1], reverse=True)

        return scored_news[:top_n]

    def get_category_hot_news(
        self,
        all_news: List[Dict],
        news_stats: Dict[int, Dict],
        top_per_category: int = 3
    ) -> Dict[str, List[Tuple[int, float]]]:
        news_by_category = {}
        for news in all_news:
            category = news.get('category', '')
            if category not in news_by_category:
                news_by_category[category] = []
            news_by_category[category].append(news)

        category_hot = {}
        for category, news_list in news_by_category.items():
            category_hot[category] = self.get_hot_news(
                news_list,
                news_stats,
                top_n=top_per_category
            )

        return category_hot

    def merge_hot_news(
        self,
        personalized_recommendations: List[RecommendationResult],
        hot_news: List[Tuple[int, float]],
        news_info: Dict[int, Dict],
        hot_count: int = None
    ) -> List[RecommendationResult]:
        hot_count = hot_count or self.hot_news_count

        if not hot_news:
            return personalized_recommendations

        personalized_ids = {rec.news_id for rec in personalized_recommendations}
        hot_news_ids = {news_id for news_id, _ in hot_news}

        missing_hot = [(nid, score) for nid, score in hot_news if nid not in personalized_ids]

        if not missing_hot:
            return personalized_recommendations

        positions = list(range(0, min(len(personalized_recommendations), hot_count * 2), 2))
        positions = positions[:len(missing_hot)]

        merged = personalized_recommendations.copy()

        for idx, (news_id, hot_score) in enumerate(missing_hot[:hot_count]):
            news = news_info.get(news_id, {})
            category = news.get('category', '')

            hot_rec = RecommendationResult(
                news_id=news_id,
                score=hot_score,
                category=category,
                rank=0,
                is_hot=True,
                reason="热门推荐"
            )

            insert_pos = positions[idx] if idx < len(positions) else len(merged)
            merged.insert(insert_pos, hot_rec)

        for i, rec in enumerate(merged):
            rec.rank = i + 1

        return merged

    def fallback_to_hot(
        self,
        user_id: int,
        all_news: List[Dict],
        news_stats: Dict[int, Dict],
        top_n: int = None
    ) -> List[RecommendationResult]:
        top_n = top_n or config.RECOMMEND_TOP_N

        logger.info(f"User {user_id}: Falling back to hot news recommendations")

        hot_news = self.get_hot_news(all_news, news_stats, top_n=top_n)

        results = []
        for rank, (news_id, score) in enumerate(hot_news, 1):
            news = next((n for n in all_news if n['news_id'] == news_id), {})
            category = news.get('category', '')

            results.append(RecommendationResult(
                news_id=news_id,
                score=score,
                category=category,
                rank=rank,
                is_hot=True,
                reason="热门推荐"
            ))

        return results

    def cold_start_recommend(
        self,
        user_id: int,
        all_news: List[Dict],
        news_stats: Dict[int, Dict],
        user_preferences: Optional[Dict[str, float]] = None,
        top_n: int = None
    ) -> List[RecommendationResult]:
        top_n = top_n or config.RECOMMEND_TOP_N

        if user_preferences:
            logger.info(f"User {user_id}: Cold start with preferences: {user_preferences}")

            category_hot = self.get_category_hot_news(all_news, news_stats)

            selected = []
            used_news = set()

            pref_categories = sorted(
                user_preferences.items(),
                key=lambda x: x[1],
                reverse=True
            )

            per_category = max(1, top_n // max(len(pref_categories), 1))

            for category, pref_score in pref_categories:
                category_news = category_hot.get(category, [])
                count = 0
                for news_id, score in category_news:
                    if news_id not in used_news and count < per_category:
                        news = next((n for n in all_news if n['news_id'] == news_id), {})
                        selected.append(RecommendationResult(
                            news_id=news_id,
                            score=score * pref_score,
                            category=category,
                            rank=0,
                            is_hot=True,
                            reason=f"您可能对{category}感兴趣"
                        ))
                        used_news.add(news_id)
                        count += 1

                if len(selected) >= top_n:
                    break

            while len(selected) < top_n:
                hot_news = self.get_hot_news(all_news, news_stats, top_n=top_n)
                for news_id, score in hot_news:
                    if news_id not in used_news and len(selected) < top_n:
                        news = next((n for n in all_news if n['news_id'] == news_id), {})
                        category = news.get('category', '')
                        selected.append(RecommendationResult(
                            news_id=news_id,
                            score=score,
                            category=category,
                            rank=0,
                            is_hot=True,
                            reason="热门推荐"
                        ))
                        used_news.add(news_id)

            selected.sort(key=lambda x: x.score, reverse=True)
            for i, rec in enumerate(selected):
                rec.rank = i + 1

            return selected
        else:
            return self.fallback_to_hot(user_id, all_news, news_stats, top_n)

    def get_trending_news(
        self,
        all_news: List[Dict],
        news_stats: Dict[int, Dict],
        time_window_hours: int = 6,
        top_n: int = 10
    ) -> List[Tuple[int, float]]:
        now = datetime.now()
        window_start = now - timedelta(hours=time_window_hours)

        recent_news = [
            news for news in all_news
            if self._parse_datetime(news.get('publish_time', datetime.now().isoformat())) >= window_start
        ]

        return self.get_hot_news(recent_news, news_stats, top_n=top_n)

    def _parse_datetime(self, datetime_str: Optional[str]) -> Optional[datetime]:
        if not datetime_str:
            return None

        try:
            return datetime.fromisoformat(datetime_str)
        except (ValueError, TypeError):
            return None

    def update_hot_scores(
        self,
        news_ids: List[int],
        news_stats: Dict[int, Dict],
        all_news: List[Dict]
    ) -> Dict[int, float]:
        news_dict = {news['news_id']: news for news in all_news}
        updated_scores = {}

        for news_id in news_ids:
            news = news_dict.get(news_id)
            if not news:
                continue

            stats = news_stats.get(news_id, {})
            publish_time = self._parse_datetime(news.get('publish_time'))
            if not publish_time:
                publish_time = datetime.now() - timedelta(hours=1)

            hot_score = self.calculate_hot_score(
                click_count=stats.get('click_count', 0),
                like_count=stats.get('like_count', 0),
                share_count=stats.get('share_count', 0),
                publish_time=publish_time,
                view_duration=stats.get('total_duration', 0.0)
            )

            updated_scores[news_id] = hot_score

        return updated_scores
