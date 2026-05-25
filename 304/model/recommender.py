import numpy as np
import tensorflow as tf
from typing import List, Dict, Tuple, Optional
from datetime import datetime

from config import config
from data.models import UserProfile, NewsFeatures, RecommendationResult
from .deepfm import DeepFMModel
from .online_learning import OnlineLearningManager
from strategy.trend_prediction import TrendPredictor, TrendingNewsPrediction
from strategy.multi_objective import MultiObjectiveOptimizer
from strategy.explainable import RecommendationExplainer, ExplainableRecommendation

import logging
logger = logging.getLogger(__name__)


class NewsRecommender:
    def __init__(
        self,
        model: Optional[DeepFMModel] = None,
        online_manager: Optional[OnlineLearningManager] = None,
        use_online_learning: bool = True,
        trend_predictor: Optional[TrendPredictor] = None,
        multi_objective_optimizer: Optional[MultiObjectiveOptimizer] = None,
        explainer: Optional[RecommendationExplainer] = None,
        use_multi_objective: bool = True,
        use_explainable: bool = True
    ):
        self.model = model
        self.online_manager = online_manager
        self.use_online_learning = use_online_learning and online_manager is not None
        self.embedding_dim = config.EMBEDDING_DIM
        self.max_sequence_length = 50

        self.trend_predictor = trend_predictor or TrendPredictor()
        self.multi_objective_optimizer = multi_objective_optimizer or MultiObjectiveOptimizer()
        self.explainer = explainer or RecommendationExplainer()
        self.use_multi_objective = use_multi_objective
        self.use_explainable = use_explainable

    def load_model(self, path: str = None):
        self.model = DeepFMModel.load(path)

    def _extract_time_features(
        self,
        user_profile: UserProfile,
        candidate_news: List[Dict],
        current_time: Optional[datetime] = None
    ) -> Tuple[List[List[datetime]], List[List[datetime]], List[datetime]]:
        current_time = current_time or datetime.now()

        behavior_timestamps = [
            b.get('timestamp', current_time) for b in user_profile.recent_behavior
            if b.get('news_id') is not None
        ][-self.max_sequence_length:]

        while len(behavior_timestamps) < self.max_sequence_length:
            behavior_timestamps.append(current_time)

        news_publish_times = [
            b.get('publish_time', current_time) for b in user_profile.recent_behavior
            if b.get('news_id') is not None
        ][-self.max_sequence_length:]

        while len(news_publish_times) < self.max_sequence_length:
            news_publish_times.append(current_time)

        candidate_publish_times = []
        for news in candidate_news:
            publish_time = news.get('publish_time')
            if isinstance(publish_time, str):
                try:
                    publish_time = datetime.fromisoformat(publish_time)
                except (ValueError, TypeError):
                    publish_time = current_time
            elif publish_time is None:
                publish_time = current_time
            candidate_publish_times.append(publish_time)

        return (
            [behavior_timestamps] * len(candidate_news),
            [news_publish_times] * len(candidate_news),
            candidate_publish_times
        )

    def predict_scores(
        self,
        user_id: int,
        candidate_news: List[Dict],
        user_profile: UserProfile,
        current_time: Optional[datetime] = None,
        use_ensemble: bool = True
    ) -> List[Tuple[int, float]]:
        if not self.model:
            raise ValueError("Model not loaded. Please train or load a model first.")

        if not candidate_news:
            return []

        current_time = current_time or datetime.now()

        user_ids = [user_id] * len(candidate_news)
        news_ids = [news['news_id'] for news in candidate_news]
        category_ids = [news['category_id'] for news in candidate_news]

        recent_news_ids = [
            b.get('news_id') for b in user_profile.recent_behavior
            if b.get('news_id') is not None
        ][-self.max_sequence_length:]

        behavior_sequences = [recent_news_ids] * len(candidate_news)

        behavior_timestamps, news_publish_times, candidate_publish_times = self._extract_time_features(
            user_profile, candidate_news, current_time
        )

        features = self.model.prepare_features(
            user_ids=user_ids,
            news_ids=news_ids,
            category_ids=category_ids,
            behavior_sequences=behavior_sequences,
            behavior_timestamps=behavior_timestamps,
            news_publish_times=news_publish_times,
            candidate_publish_times=candidate_publish_times,
            current_time=current_time
        )

        if self.use_online_learning and self.online_manager is not None:
            scores = self.online_manager.predict(features, use_ensemble=use_ensemble).flatten()
        else:
            scores = self.model.predict(features).flatten()

        results = []
        for i, news in enumerate(candidate_news):
            adjusted_score = self._adjust_score(
                base_score=float(scores[i]),
                user_profile=user_profile,
                news=news,
                current_time=current_time
            )
            results.append((news['news_id'], adjusted_score))

        results.sort(key=lambda x: x[1], reverse=True)

        return results

    def predict_multi_objective(
        self,
        user_id: int,
        candidate_news: List[Dict],
        user_profile: UserProfile,
        current_time: Optional[datetime] = None,
        use_ensemble: bool = True
    ) -> Dict[str, np.ndarray]:
        if not self.model:
            raise ValueError("Model not loaded. Please train or load a model first.")

        if not candidate_news:
            return {'click_prob': np.array([]), 'predicted_duration': np.array([])}

        current_time = current_time or datetime.now()

        user_ids = [user_id] * len(candidate_news)
        news_ids = [news['news_id'] for news in candidate_news]
        category_ids = [news['category_id'] for news in candidate_news]

        recent_news_ids = [
            b.get('news_id') for b in user_profile.recent_behavior
            if b.get('news_id') is not None
        ][-self.max_sequence_length:]

        behavior_sequences = [recent_news_ids] * len(candidate_news)

        behavior_timestamps, news_publish_times, candidate_publish_times = self._extract_time_features(
            user_profile, candidate_news, current_time
        )

        features = self.model.prepare_features(
            user_ids=user_ids,
            news_ids=news_ids,
            category_ids=category_ids,
            behavior_sequences=behavior_sequences,
            behavior_timestamps=behavior_timestamps,
            news_publish_times=news_publish_times,
            candidate_publish_times=candidate_publish_times,
            current_time=current_time
        )

        if self.use_online_learning and self.online_manager is not None:
            if hasattr(self.online_manager, 'predict_multi_objective'):
                return self.online_manager.predict_multi_objective(features, use_ensemble=use_ensemble)

        return self.model.predict_multi_objective(features)

    def _adjust_score(
        self,
        base_score: float,
        user_profile: UserProfile,
        news: Dict,
        current_time: Optional[datetime] = None
    ) -> float:
        current_time = current_time or datetime.now()
        adjusted_score = base_score

        category = news.get('category', '')
        pref_score = user_profile.category_preferences.get(category, 0.5)
        adjusted_score *= (0.7 + 0.3 * pref_score)

        popularity_score = news.get('popularity_score', 0.0)
        if popularity_score > 0:
            normalized_popularity = min(popularity_score / 100.0, 1.0)
            adjusted_score += normalized_popularity * 0.1

        hot_score = news.get('hot_score', 0.0)
        if hot_score > 0:
            normalized_hot = min(hot_score / 10.0, 1.0)
            adjusted_score += normalized_hot * 0.05

        return min(adjusted_score, 1.0)

    def _calculate_time_decay(self, publish_time_str: Optional[str]) -> float:
        if not publish_time_str:
            return 1.0

        try:
            if isinstance(publish_time_str, datetime):
                publish_time = publish_time_str
            else:
                publish_time = datetime.fromisoformat(publish_time_str)
            now = datetime.now()
            hours_passed = (now - publish_time).total_seconds() / 3600

            half_life = 72.0
            decay = np.exp(-np.log(2) * hours_passed / half_life)

            return max(decay, 0.5)
        except (ValueError, TypeError):
            return 1.0

    def generate_recommendations(
        self,
        user_id: int,
        candidate_news: List[Dict],
        user_profile: UserProfile,
        top_n: int = None,
        exclude_news_ids: Optional[List[int]] = None,
        use_block_diversity: bool = True,
        use_ensemble: bool = True,
        use_multi_objective: bool = None,
        use_explainable: bool = None,
        news_stats: Optional[Dict[int, Dict]] = None
    ) -> List[RecommendationResult]:
        top_n = top_n or config.RECOMMEND_TOP_N
        exclude_news_ids = exclude_news_ids or []
        use_multi_objective = use_multi_objective if use_multi_objective is not None else self.use_multi_objective
        use_explainable = use_explainable if use_explainable is not None else self.use_explainable

        filtered_candidates = [
            news for news in candidate_news
            if news['news_id'] not in exclude_news_ids
        ]

        if use_multi_objective:
            mo_predictions = self.predict_multi_objective(
                user_id, filtered_candidates, user_profile,
                use_ensemble=use_ensemble
            )

            click_probs = mo_predictions['click_prob'].flatten()
            predicted_durations = mo_predictions['predicted_duration'].flatten()

            scored_news = []
            for i, news in enumerate(filtered_candidates):
                base_score = float(click_probs[i])
                adjusted_score = self._adjust_score(
                    base_score=base_score,
                    user_profile=user_profile,
                    news=news
                )
                scored_news.append((news['news_id'], adjusted_score))

            scored_news.sort(key=lambda x: x[1], reverse=True)

            predicted_ctrs_dict = {filtered_candidates[i]['news_id']: float(click_probs[i])
                                  for i in range(len(filtered_candidates))}
            predicted_durations_dict = {filtered_candidates[i]['news_id']: float(predicted_durations[i])
                                        for i in range(len(filtered_candidates))}
        else:
            scored_news = self.predict_scores(
                user_id, filtered_candidates, user_profile,
                use_ensemble=use_ensemble
            )
            predicted_ctrs_dict = None
            predicted_durations_dict = None

        results = []
        news_dict = {news['news_id']: news for news in filtered_candidates}

        for news_id, score in scored_news:
            news = news_dict.get(news_id)
            if not news:
                continue

            category = news.get('category', '')
            reason = self._generate_reason(score, user_profile, category)

            results.append(RecommendationResult(
                news_id=news_id,
                score=score,
                category=category,
                rank=0,
                is_hot=news.get('hot_score', 0) > 5.0,
                reason=reason
            ))

        if use_multi_objective and self.multi_objective_optimizer:
            results = self.multi_objective_optimizer.optimize_recommendations(
                recommendations=results,
                top_n=top_n,
                predicted_durations=predicted_durations_dict,
                predicted_ctrs=predicted_ctrs_dict,
                news_stats=news_stats,
                use_pareto=True
            )

        return results

    def generate_explainable_recommendations(
        self,
        user_id: int,
        candidate_news: List[Dict],
        user_profile: UserProfile,
        top_n: int = None,
        exclude_news_ids: Optional[List[int]] = None,
        use_block_diversity: bool = True,
        use_ensemble: bool = True,
        use_multi_objective: bool = None,
        news_stats: Optional[Dict[int, Dict]] = None,
        news_embeddings: Optional[Dict[int, np.ndarray]] = None,
        recommendation_embeddings: Optional[Dict[int, np.ndarray]] = None,
        trend_infos: Optional[Dict[int, Dict]] = None,
        friend_behaviors: Optional[List[Dict]] = None
    ) -> List[ExplainableRecommendation]:
        top_n = top_n or config.RECOMMEND_TOP_N

        recommendations = self.generate_recommendations(
            user_id=user_id,
            candidate_news=candidate_news,
            user_profile=user_profile,
            top_n=top_n,
            exclude_news_ids=exclude_news_ids,
            use_block_diversity=use_block_diversity,
            use_ensemble=use_ensemble,
            use_multi_objective=use_multi_objective,
            use_explainable=True,
            news_stats=news_stats
        )

        objective_scores = None
        if self.use_multi_objective and news_stats:
            objective_scores = {}
            for rec in recommendations:
                if rec.news_id in news_stats:
                    stats = news_stats[rec.news_id]
                    objective_scores[rec.news_id] = {
                        'click': stats.get('click_rate', 0.0),
                        'duration': stats.get('avg_duration', 0.0) / 120.0
                    }

        explained = self.explainer.generate_explanations(
            user_profile=user_profile,
            recommendations=recommendations,
            news_embeddings=news_embeddings,
            recommendation_embeddings=recommendation_embeddings,
            trend_infos=trend_infos,
            objective_scores=objective_scores,
            friend_behaviors=friend_behaviors
        )

        return explained

    def generate_trending_recommendations(
        self,
        user_id: int,
        candidate_news: List[Dict],
        news_stats: Dict[int, Dict],
        user_profile: Optional[UserProfile] = None,
        top_n: int = None,
        prefer_emerging: bool = True
    ) -> List[RecommendationResult]:
        top_n = top_n or config.RECOMMEND_TOP_N

        trending_recs = self.trend_predictor.get_trending_recommendations(
            all_news=candidate_news,
            news_stats=news_stats,
            top_n=top_n,
            prefer_emerging=prefer_emerging
        )

        if user_profile is not None and self.model is not None:
            try:
                news_dict = {news['news_id']: news for news in candidate_news}
                trending_news_list = [news_dict.get(rec.news_id, {}) for rec in trending_recs if rec.news_id in news_dict]

                if trending_news_list:
                    personalized = self.generate_recommendations(
                        user_id=user_id,
                        candidate_news=trending_news_list,
                        user_profile=user_profile,
                        top_n=top_n,
                        use_multi_objective=True,
                        news_stats=news_stats
                    )

                    return personalized
            except Exception as e:
                logger.warning(f"Failed to personalize trending recommendations: {e}")

        return trending_recs

    def predict_trending_news(
        self,
        all_news: List[Dict],
        news_stats: Dict[int, Dict],
        top_n: int = 20
    ) -> List[TrendingNewsPrediction]:
        return self.trend_predictor.predict_trending_news(
            all_news=all_news,
            news_stats=news_stats,
            top_n=top_n
        )

    def _generate_reason(
        self,
        score: float,
        user_profile: UserProfile,
        category: str
    ) -> str:
        reasons = []

        pref = user_profile.category_preferences.get(category, 0.0)
        if pref > 0.7:
            reasons.append(f"您对{category}内容感兴趣")

        if score > 0.8:
            reasons.append("高匹配度推荐")
        elif score > 0.6:
            reasons.append("根据您的阅读习惯推荐")

        if not reasons:
            reasons.append("为您精选")

        return "；".join(reasons)

    def get_similar_news(
        self,
        news_id: int,
        all_news: List[Dict],
        top_k: int = 10
    ) -> List[Tuple[int, float]]:
        if not self.model:
            raise ValueError("Model not loaded.")

        target_emb = self.model.get_news_embedding(news_id).numpy()
        embeddings = self.model.get_embedding_weights()['news_embeddings']

        news_ids = [news['news_id'] for news in all_news if news['news_id'] != news_id]

        if not news_ids:
            return []

        candidate_embs = embeddings[news_ids]

        similarities = np.dot(candidate_embs, target_emb) / (
            np.linalg.norm(candidate_embs, axis=1) * np.linalg.norm(target_emb)
        )

        results = list(zip(news_ids, similarities))
        results.sort(key=lambda x: x[1], reverse=True)

        return results[:top_k]

    def update_user_embedding(
        self,
        user_id: int,
        behavior_sequence: List[int]
    ) -> np.ndarray:
        if not self.model:
            raise ValueError("Model not loaded.")

        embeddings = self.model.get_embedding_weights()['news_embeddings']

        valid_ids = [nid for nid in behavior_sequence if nid < len(embeddings)]
        if not valid_ids:
            user_emb = self.model.get_user_embedding(user_id).numpy()
            return user_emb

        behavior_embs = embeddings[valid_ids]
        weights = np.linspace(0.5, 1.0, len(valid_ids))
        weights = weights / weights.sum()

        weighted_emb = np.average(behavior_embs, weights=weights, axis=0)

        user_emb = self.model.get_user_embedding(user_id).numpy()
        updated_emb = 0.3 * weighted_emb + 0.7 * user_emb

        return updated_emb

    def calculate_category_preferences(
        self,
        behaviors: List[Dict],
        category_list: List[str]
    ) -> Dict[str, float]:
        category_scores = {cat: 0.0 for cat in category_list}
        category_counts = {cat: 0 for cat in category_list}

        total_weight = 0.0
        for behavior in behaviors:
            behavior_type = behavior.get('behavior_type', 'view')
            category = behavior.get('category', '')
            duration = behavior.get('duration', 0.0)

            weight = config.BEHAVIOR_WEIGHTS.get(behavior_type, 1.0)
            if duration > 0:
                weight += duration * config.BEHAVIOR_WEIGHTS['duration']

            time_decay = self._calculate_behavior_time_decay(behavior.get('timestamp'))
            weight *= time_decay

            if category in category_scores:
                category_scores[category] += weight
                category_counts[category] += 1
                total_weight += weight

        if total_weight > 0:
            for cat in category_scores:
                if category_counts[cat] > 0:
                    category_scores[cat] = category_scores[cat] / total_weight

        max_score = max(category_scores.values()) if category_scores else 1.0
        if max_score > 0:
            for cat in category_scores:
                category_scores[cat] = category_scores[cat] / max_score

        return category_scores

    def _calculate_behavior_time_decay(self, timestamp: Optional[str]) -> float:
        if not timestamp:
            return 1.0

        try:
            if isinstance(timestamp, datetime):
                ts = timestamp
            else:
                ts = datetime.fromisoformat(timestamp)
            now = datetime.now()
            hours_passed = (now - ts).total_seconds() / 3600

            half_life = 168.0
            decay = np.exp(-np.log(2) * hours_passed / half_life)

            return max(decay, 0.3)
        except (ValueError, TypeError):
            return 1.0

    def add_feedback_for_online_learning(
        self,
        user_id: int,
        news_id: int,
        category_id: int,
        user_profile: UserProfile,
        label: float,
        current_time: Optional[datetime] = None
    ):
        if not self.use_online_learning or self.online_manager is None:
            logger.warning("Online learning not enabled, skipping feedback")
            return

        current_time = current_time or datetime.now()

        recent_news_ids = [
            b.get('news_id') for b in user_profile.recent_behavior
            if b.get('news_id') is not None
        ][-self.max_sequence_length:]

        behavior_timestamps = [
            b.get('timestamp', current_time) for b in user_profile.recent_behavior
            if b.get('news_id') is not None
        ][-self.max_sequence_length:]

        news_publish_times = [
            b.get('publish_time', current_time) for b in user_profile.recent_behavior
            if b.get('news_id') is not None
        ][-self.max_sequence_length:]

        candidate_publish_time = current_time

        self.online_manager.add_feedback(
            user_id=user_id,
            news_id=news_id,
            category_id=category_id,
            behavior_sequence=recent_news_ids,
            behavior_timestamps=behavior_timestamps,
            news_publish_times=news_publish_times,
            candidate_publish_time=candidate_publish_time,
            label=label,
            current_time=current_time
        )

    def trigger_online_training(
        self,
        num_samples: int = 2000,
        epochs: int = 1,
        batch_size: int = 64,
        time_window_hours: Optional[float] = None
    ):
        if not self.use_online_learning or self.online_manager is None:
            logger.warning("Online learning not enabled, skipping training")
            return None

        history = self.online_manager.train_online(
            num_samples=num_samples,
            epochs=epochs,
            batch_size=batch_size,
            time_window_hours=time_window_hours
        )

        if history is not None:
            self.online_manager.update_fusion_weights()

        return history

    def get_online_stats(self) -> Dict:
        if self.online_manager is not None:
            return self.online_manager.get_stats()
        return {'online_learning': False}
