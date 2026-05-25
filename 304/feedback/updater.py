import logging
import threading
import time
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from collections import defaultdict

from config import config
from data.models import UserProfile, NewsFeatures
from model.recommender import NewsRecommender
from model.online_learning import OnlineLearningManager
from cache.redis_client import RedisClient
from streaming.consumer import BatchBehaviorConsumer

logger = logging.getLogger(__name__)


class RealTimeUpdater:
    def __init__(
        self,
        redis_client: RedisClient,
        recommender: Optional[NewsRecommender] = None,
        consumer: Optional[BatchBehaviorConsumer] = None,
        online_manager: Optional[OnlineLearningManager] = None
    ):
        self.redis = redis_client
        self.recommender = recommender
        self.consumer = consumer
        self.online_manager = online_manager
        self._running = False
        self._update_thread = None
        self._last_update_times = {}
        self._behavior_buffer = defaultdict(list)
        self._last_online_training = None

    def start(self, interval: int = None):
        interval = interval or config.REAL_TIME_UPDATE_INTERVAL
        self._running = True

        if self.consumer:
            self.consumer.set_mock_producer(None)
            self.consumer.start_batch(self._process_behavior_batch)

        self._update_thread = threading.Thread(
            target=self._periodic_update_loop,
            args=(interval,),
            daemon=True
        )
        self._update_thread.start()

        logger.info(f"Real-time updater started with interval {interval}s")

    def stop(self):
        self._running = False
        if self._update_thread:
            self._update_thread.join(timeout=10)
            self._update_thread = None
        if self.consumer:
            self.consumer.stop()
        logger.info("Real-time updater stopped")

    def _process_behavior_batch(self, messages: List[Dict]):
        try:
            user_behaviors = defaultdict(list)
            for msg in messages:
                user_id = msg.get('user_id')
                if user_id is not None:
                    user_behaviors[user_id].append(msg)

            for user_id, behaviors in user_behaviors.items():
                self._buffer_behaviors(user_id, behaviors)
                self._add_behaviors_to_online_buffer(user_id, behaviors)

            updated_users = []
            for user_id, behaviors in user_behaviors.items():
                if self._should_update_user(user_id):
                    if self.update_user_profile(user_id):
                        updated_users.append(user_id)

            logger.info(
                f"Processed batch of {len(messages)} messages, "
                f"updated {len(updated_users)} user profiles"
            )

        except Exception as e:
            logger.error(f"Error processing behavior batch: {e}", exc_info=True)

    def _add_behaviors_to_online_buffer(self, user_id: int, behaviors: List[Dict]):
        if not self.online_manager or not self.recommender:
            return

        try:
            profile = self.redis.get_user_profile(user_id)
            if not profile:
                return

            for behavior in behaviors:
                news_id = behavior.get('news_id')
                category_id = behavior.get('category_id', 0)
                behavior_type = behavior.get('behavior_type', 'view')

                label = self._behavior_to_label(behavior)
                if label is None:
                    continue

                candidate_publish_time = behavior.get('publish_time', datetime.now())
                if isinstance(candidate_publish_time, str):
                    try:
                        candidate_publish_time = datetime.fromisoformat(candidate_publish_time)
                    except:
                        candidate_publish_time = datetime.now()

                self.recommender.add_feedback_for_online_learning(
                    user_id=user_id,
                    news_id=news_id,
                    category_id=category_id,
                    user_profile=profile,
                    label=label,
                    current_time=datetime.now()
                )

            logger.debug(f"Added {len(behaviors)} behaviors to online buffer for user {user_id}")

        except Exception as e:
            logger.warning(f"Failed to add behaviors to online buffer for user {user_id}: {e}")

    def _behavior_to_label(self, behavior: Dict) -> Optional[float]:
        behavior_type = behavior.get('behavior_type', 'view')
        label_map = {
            'view': 0.6,
            'like': 1.0,
            'share': 1.0,
            'rating': None,
            'skip': 0.0
        }

        if behavior_type == 'rating':
            rating = behavior.get('extra', {}).get('rating', 0)
            return min(1.0, max(0.0, rating / 5.0))

        duration = behavior.get('duration', 0.0)
        if behavior_type == 'view' and duration > 0:
            if duration < 5:
                return 0.2
            elif duration < 30:
                return 0.5
            elif duration < 60:
                return 0.8
            else:
                return 1.0

        return label_map.get(behavior_type, 0.5)

    def _buffer_behaviors(self, user_id: int, behaviors: List[Dict]):
        self._behavior_buffer[user_id].extend(behaviors)

        max_buffer_size = 100
        if len(self._behavior_buffer[user_id]) > max_buffer_size:
            self._behavior_buffer[user_id] = self._behavior_buffer[user_id][-max_buffer_size:]

    def _should_update_user(self, user_id: int) -> bool:
        last_update = self._last_update_times.get(user_id, datetime.min)
        time_since_update = (datetime.now() - last_update).total_seconds()

        min_interval = config.REAL_TIME_UPDATE_INTERVAL / 2
        if time_since_update < min_interval:
            return False

        behavior_count = len(self._behavior_buffer.get(user_id, []))
        if behavior_count >= 5:
            return True

        return time_since_update >= config.REAL_TIME_UPDATE_INTERVAL

    def _should_trigger_online_training(self) -> bool:
        if not self.online_manager:
            return False

        if not self.online_manager.buffer.should_train():
            return False

        if self._last_online_training is None:
            return True

        min_interval = 30 * 60
        time_since_last = (datetime.now() - self._last_online_training).total_seconds()
        return time_since_last >= min_interval

    def update_user_profile(self, user_id: int) -> bool:
        try:
            logger.debug(f"Updating profile for user {user_id}")

            history = self.redis.get_user_behavior_history(user_id, count=200)
            buffered = self._behavior_buffer.pop(user_id, [])

            all_behaviors = buffered + history

            if not all_behaviors:
                logger.debug(f"No behavior data for user {user_id}")
                return False

            profile = self.redis.get_user_profile(user_id)
            if not profile:
                profile = UserProfile(user_id=user_id)

            if self.recommender:
                category_preferences = self.recommender.calculate_category_preferences(
                    all_behaviors,
                    config.CATEGORY_LIST
                )
                profile.category_preferences = category_preferences

                recent_news_ids = [
                    b.get('news_id') for b in all_behaviors[:50]
                    if b.get('news_id') is not None
                ]

                try:
                    updated_embedding = self.recommender.update_user_embedding(
                        user_id,
                        recent_news_ids
                    )
                    profile.embedding = updated_embedding
                except Exception as e:
                    logger.warning(f"Failed to update embedding for user {user_id}: {e}")

            profile.recent_behavior = all_behaviors[:100]
            profile.last_updated = datetime.now()

            success = self.redis.set_user_profile(user_id, profile)

            self._last_update_times[user_id] = datetime.now()

            self.redis.set_recommendations(user_id, [], ttl=1)

            logger.info(f"Successfully updated profile for user {user_id}")
            return success

        except Exception as e:
            logger.error(f"Error updating user profile {user_id}: {e}", exc_info=True)
            return False

    def _periodic_update_loop(self, interval: int):
        while self._running:
            try:
                start_time = time.time()

                pending_users = list(self._behavior_buffer.keys())
                updated_count = 0

                for user_id in pending_users:
                    if self._should_update_user(user_id):
                        if self.update_user_profile(user_id):
                            updated_count += 1

                if updated_count > 0:
                    logger.info(f"Periodic update: updated {updated_count} user profiles")

                if self._should_trigger_online_training():
                    self._trigger_online_training()

                self._update_news_statistics()

                elapsed = time.time() - start_time
                sleep_time = max(0, interval - elapsed)
                time.sleep(sleep_time)

            except Exception as e:
                logger.error(f"Error in periodic update loop: {e}", exc_info=True)
                time.sleep(interval)

    def _trigger_online_training(self):
        if not self.recommender or not self.online_manager:
            return

        try:
            logger.info("Triggering online model training...")
            history = self.recommender.trigger_online_training(
                num_samples=2000,
                epochs=1,
                batch_size=64,
                time_window_hours=24
            )

            if history is not None:
                self._last_online_training = datetime.now()
                logger.info("Online training completed successfully")
            else:
                logger.info("Online training skipped (not enough samples)")

        except Exception as e:
            logger.error(f"Error during online training: {e}", exc_info=True)

    def _update_news_statistics(self):
        try:
            all_news_ids = self.redis.get_all_news_ids()

            updated_count = 0
            for news_id in all_news_ids[:1000]:
                stats = self.redis._execute('hgetall', f"news:stats:{news_id}")
                if stats:
                    clicks = int(stats.get('click_count', 0))
                    likes = int(stats.get('like_count', 0))
                    shares = int(stats.get('share_count', 0))

                    popularity_score = clicks + likes * 3 + shares * 5

                    features = self.redis.get_news_features(news_id)
                    if not features:
                        news_info = self.redis.get_news_info(news_id)
                        if news_info:
                            features = NewsFeatures(
                                news_id=news_id,
                                category_id=news_info.get('category_id', 0)
                            )
                        else:
                            continue

                    features.popularity_score = popularity_score
                    features.click_count = clicks
                    features.like_count = likes
                    features.share_count = shares
                    features.hot_score = self._calculate_hot_score(clicks, likes, shares)

                    self.redis.set_news_features(news_id, features)
                    updated_count += 1

            if updated_count > 0:
                logger.debug(f"Updated statistics for {updated_count} news items")

        except Exception as e:
            logger.error(f"Error updating news statistics: {e}", exc_info=True)

    def _calculate_hot_score(self, clicks: int, likes: int, shares: int) -> float:
        base_score = clicks * 1.0 + likes * 3.0 + shares * 5.0

        import numpy as np
        now = datetime.now()
        hours_passed = 1.0
        time_decay = np.exp(-np.log(2) * hours_passed / 12)
        hot_score = base_score * time_decay

        return hot_score

    def process_single_behavior(self, behavior: Dict) -> bool:
        user_id = behavior.get('user_id')
        if user_id is None:
            return False

        self._buffer_behaviors(user_id, [behavior])
        self._add_behaviors_to_online_buffer(user_id, [behavior])

        if self._should_update_user(user_id):
            return self.update_user_profile(user_id)

        return True

    def get_user_update_status(self, user_id: int) -> Dict:
        return {
            'user_id': user_id,
            'last_updated': self._last_update_times.get(user_id),
            'pending_behaviors': len(self._behavior_buffer.get(user_id, [])),
            'should_update': self._should_update_user(user_id)
        }

    def force_update_all_users(self):
        user_ids = set()
        for key in self.redis._execute('keys', 'user:behavior:*') or []:
            try:
                user_id = int(key.split(':')[-1])
                user_ids.add(user_id)
            except (ValueError, IndexError):
                continue

        for user_id in list(self._behavior_buffer.keys()):
            user_ids.add(user_id)

        logger.info(f"Force updating {len(user_ids)} user profiles")

        updated_count = 0
        for user_id in user_ids:
            if self.update_user_profile(user_id):
                updated_count += 1

        logger.info(f"Force update completed: {updated_count}/{len(user_ids)} profiles updated")
        return updated_count, len(user_ids)

    def get_online_learning_stats(self) -> Dict:
        if self.online_manager:
            return self.online_manager.get_stats()
        return {'online_learning': False}


class FeedbackLoopManager:
    def __init__(
        self,
        redis_client: RedisClient,
        recommender: NewsRecommender,
        consumer: Optional[BatchBehaviorConsumer] = None,
        online_manager: Optional[OnlineLearningManager] = None
    ):
        self.redis = redis_client
        self.recommender = recommender
        self.online_manager = online_manager
        self.consumer = consumer or BatchBehaviorConsumer()
        self.updater = RealTimeUpdater(
            redis_client=redis_client,
            recommender=recommender,
            consumer=self.consumer,
            online_manager=online_manager
        )
        self._running = False

    def start(self):
        self._running = True
        self.updater.start()
        logger.info("Feedback loop manager started")

    def stop(self):
        self._running = False
        self.updater.stop()
        logger.info("Feedback loop manager stopped")

    def record_implicit_feedback(
        self,
        user_id: int,
        news_id: int,
        behavior_type: str,
        duration: float = 0.0
    ):
        try:
            from streaming.producer import BehaviorProducer
            producer = BehaviorProducer()
            producer.send_behavior(
                user_id=user_id,
                news_id=news_id,
                behavior_type=behavior_type,
                duration=duration
            )
            producer.flush()
        except Exception as e:
            logger.error(f"Error recording implicit feedback: {e}")

    def record_explicit_feedback(
        self,
        user_id: int,
        news_id: int,
        rating: int,
        comment: Optional[str] = None
    ):
        try:
            extra = {'rating': rating, 'comment': comment}
            from streaming.producer import BehaviorProducer
            producer = BehaviorProducer()
            producer.send_behavior(
                user_id=user_id,
                news_id=news_id,
                behavior_type='rating',
                extra=extra
            )
            producer.flush()

            self.updater.process_single_behavior({
                'user_id': user_id,
                'news_id': news_id,
                'behavior_type': 'rating',
                'timestamp': datetime.now().isoformat(),
                'extra': extra
            })

        except Exception as e:
            logger.error(f"Error recording explicit feedback: {e}")

    def get_recommendation_explanations(
        self,
        user_id: int,
        recommendations: List
    ) -> List[Dict]:
        profile = self.redis.get_user_profile(user_id)
        if not profile:
            return [{} for _ in recommendations]

        explanations = []
        for rec in recommendations:
            explanation = {
                'news_id': rec.news_id,
                'score': rec.score,
                'reasons': []
            }

            category = rec.category
            pref = profile.category_preferences.get(category, 0.0)
            if pref > 0.7:
                explanation['reasons'].append(
                    f"您对{category}内容的偏好度为{pref:.2f}"
                )

            recent_clicks = [
                b for b in profile.recent_behavior
                if b.get('behavior_type') == 'view'
                and b.get('category') == category
            ]
            if recent_clicks:
                explanation['reasons'].append(
                    f"您最近阅读了{len(recent_clicks)}篇{category}相关文章"
                )

            if rec.is_hot:
                explanation['reasons'].append("这是当前热门文章")

            if rec.reason:
                explanation['reasons'].append(rec.reason)

            explanations.append(explanation)

        return explanations

    def trigger_online_learning(self) -> Dict:
        if not self.online_manager:
            return {'success': False, 'message': 'Online learning not enabled'}

        try:
            history = self.recommender.trigger_online_training(
                num_samples=2000,
                epochs=1,
                batch_size=64
            )

            if history is None:
                return {
                    'success': False,
                    'message': 'Not enough samples for training'
                }

            return {
                'success': True,
                'message': 'Online training completed',
                'loss': history.history.get('loss', [])[-1] if history.history else None,
                'auc': history.history.get('auc', [])[-1] if history.history else None
            }

        except Exception as e:
            logger.error(f"Error triggering online learning: {e}", exc_info=True)
            return {'success': False, 'error': str(e)}

    def get_online_learning_status(self) -> Dict:
        return {
            'online_learning_enabled': self.online_manager is not None,
            'stats': self.updater.get_online_learning_stats(),
            'last_online_training': self.updater._last_online_training.isoformat()
            if self.updater._last_online_training else None
        }
