import logging
from typing import List, Dict, Optional
from datetime import datetime

from flask import Flask, request, jsonify
from flask_cors import CORS

from config import config
from data.models import UserProfile, RecommendationResult
from model.recommender import NewsRecommender
from model.online_learning import OnlineLearningManager
from cache.redis_client import RedisClient
from streaming.producer import BehaviorProducer
from strategy.diversity import DiversityController, BlockBasedDiversity, BlockConfig
from strategy.hot_news import HotNewsProvider

logger = logging.getLogger(__name__)


def create_app(
    recommender: Optional[NewsRecommender] = None,
    redis_client: Optional[RedisClient] = None,
    producer: Optional[BehaviorProducer] = None,
    online_manager: Optional[OnlineLearningManager] = None
):
    app = Flask(__name__)
    CORS(app)

    app.config['JSON_AS_ASCII'] = False

    app.recommender = recommender
    app.redis = redis_client or RedisClient()
    app.producer = producer or BehaviorProducer()
    app.online_manager = online_manager

    app.diversity_controller = DiversityController(use_block_based=True)
    app.block_diversity = BlockBasedDiversity(
        category_list=config.CATEGORY_LIST,
        block_config=BlockConfig(
            block_size=10,
            min_blocks_per_category=1,
            max_blocks_per_category=5,
            intra_block_dedup=True,
            inter_block_dedup=True,
            round_robin=True,
            capacity_based_on_priority=True
        )
    )
    app.hot_news_provider = HotNewsProvider()

    @app.route('/health', methods=['GET'])
    def health_check():
        return jsonify({
            'status': 'healthy',
            'timestamp': datetime.now().isoformat(),
            'service': 'news_recommender_api',
            'online_learning': online_manager is not None
        })

    @app.route('/api/v1/recommend/<int:user_id>', methods=['GET'])
    def get_recommendations(user_id: int):
        try:
            top_n = int(request.args.get('top_n', config.RECOMMEND_TOP_N))
            use_cache = request.args.get('use_cache', 'true').lower() == 'true'
            apply_diversity = request.args.get('apply_diversity', 'true').lower() == 'true'
            use_block_diversity = request.args.get('use_block_diversity', 'true').lower() == 'true'
            use_ensemble = request.args.get('use_ensemble', 'true').lower() == 'true'

            if use_cache:
                cached = app.redis.get_recommendations(user_id)
                if cached and len(cached) >= top_n:
                    logger.info(f"Cache hit for user {user_id}")
                    return jsonify({
                        'success': True,
                        'user_id': user_id,
                        'from_cache': True,
                        'recommendations': [r.to_dict() for r in cached[:top_n]]
                    })

            user_profile = app.redis.get_user_profile(user_id)
            if not user_profile:
                user_profile = UserProfile(user_id=user_id)

            exclude_ids = app.redis.get_recent_viewed(user_id)

            all_news_ids = app.redis.get_all_news_ids()
            candidate_news_info = app.redis.get_batch_news_info(all_news_ids)

            candidate_news = list(candidate_news_info.values())

            if not candidate_news:
                logger.warning(f"No candidate news available for user {user_id}")
                hot_recs = app.hot_news_provider.fallback_to_hot(
                    user_id,
                    [],
                    {},
                    top_n
                )
                return jsonify({
                    'success': True,
                    'user_id': user_id,
                    'fallback': True,
                    'recommendations': [r.to_dict() for r in hot_recs]
                })

            has_enough_behavior = len(user_profile.recent_behavior) >= 5
            has_model = app.recommender and app.recommender.model is not None

            if has_model and has_enough_behavior:
                recommendations = app.recommender.generate_recommendations(
                    user_id=user_id,
                    candidate_news=candidate_news,
                    user_profile=user_profile,
                    top_n=top_n * 3,
                    exclude_news_ids=exclude_ids,
                    use_ensemble=use_ensemble
                )
            else:
                logger.info(f"User {user_id}: Cold start or no model available")
                recommendations = app.hot_news_provider.cold_start_recommend(
                    user_id=user_id,
                    all_news=candidate_news,
                    news_stats={},
                    user_preferences=user_profile.category_preferences if user_profile.category_preferences else None,
                    top_n=top_n * 3
                )

            diversity_metrics = None
            if apply_diversity and recommendations:
                if use_block_diversity:
                    block_stats = app.block_diversity.get_block_statistics(
                        recommendations,
                        user_profile.category_preferences
                    )
                    logger.info(f"User {user_id}: Block stats - {block_stats['total_blocks']} blocks across "
                               f"{len(block_stats['categories'])} categories")

                    recommendations = app.block_diversity.apply_block_diversity(
                        recommendations,
                        top_n=top_n,
                        user_preferences=user_profile.category_preferences,
                        use_round_robin=True
                    )
                else:
                    recommendations = app.diversity_controller.apply_diversity(
                        recommendations,
                        top_n=top_n,
                        user_preferences=user_profile.category_preferences
                    )

                diversity_metrics = app.block_diversity.calculate_diversity_score(recommendations)
                logger.info(f"User {user_id}: Diversity score: {diversity_metrics}")

            hot_news = app.hot_news_provider.get_hot_news(candidate_news, {}, top_n=config.HOT_NEWS_COUNT)
            if hot_news and recommendations:
                recommendations = app.hot_news_provider.merge_hot_news(
                    personalized_recommendations=recommendations,
                    hot_news=hot_news,
                    news_info=candidate_news_info,
                    hot_count=config.HOT_NEWS_COUNT
                )

            recommendations = recommendations[:top_n]

            app.redis.set_recommendations(user_id, recommendations, ttl=300)

            response = {
                'success': True,
                'user_id': user_id,
                'from_cache': False,
                'fallback': not (has_model and has_enough_behavior),
                'diversity_score': diversity_metrics,
                'use_block_diversity': use_block_diversity,
                'use_ensemble': use_ensemble,
                'recommendations': [r.to_dict() for r in recommendations]
            }

            if has_model and app.recommender.use_online_learning:
                response['online_learning_stats'] = app.recommender.get_online_stats()

            return jsonify(response)

        except Exception as e:
            logger.error(f"Error generating recommendations for user {user_id}: {e}", exc_info=True)
            return jsonify({
                'success': False,
                'user_id': user_id,
                'error': str(e)
            }), 500

    @app.route('/api/v1/behavior', methods=['POST'])
    def record_behavior():
        try:
            data = request.get_json(force=True)

            user_id = data.get('user_id')
            news_id = data.get('news_id')
            behavior_type = data.get('behavior_type')
            duration = float(data.get('duration', 0.0))
            category_id = int(data.get('category_id', 0))

            if user_id is None or news_id is None or behavior_type is None:
                return jsonify({
                    'success': False,
                    'error': 'Missing required fields: user_id, news_id, behavior_type'
                }), 400

            timestamp = datetime.now()

            app.producer.send_behavior(
                user_id=user_id,
                news_id=news_id,
                behavior_type=behavior_type,
                duration=duration,
                timestamp=timestamp,
                category_id=category_id
            )

            if behavior_type == 'view':
                app.redis.add_recent_viewed(user_id, news_id)

            app.redis.update_news_statistics(news_id, behavior_type)

            news_info = app.redis.get_news_info(news_id)
            if news_info:
                behavior_record = {
                    'news_id': news_id,
                    'behavior_type': behavior_type,
                    'duration': duration,
                    'timestamp': timestamp.isoformat(),
                    'category': news_info.get('category', ''),
                    'category_id': news_info.get('category_id', 0),
                    'publish_time': news_info.get('publish_time')
                }
                app.redis.add_user_behavior(user_id, behavior_record)

                if app.recommender and app.recommender.use_online_learning:
                    user_profile = app.redis.get_user_profile(user_id)
                    if user_profile:
                        label = 1.0 if behavior_type in ['like', 'share'] else 0.6
                        app.recommender.add_feedback_for_online_learning(
                            user_id=user_id,
                            news_id=news_id,
                            category_id=category_id,
                            user_profile=user_profile,
                            label=label,
                            current_time=timestamp
                        )

            return jsonify({
                'success': True,
                'message': 'Behavior recorded successfully',
                'timestamp': timestamp.isoformat(),
                'online_learning_updated': app.recommender.use_online_learning if app.recommender else False
            })

        except Exception as e:
            logger.error(f"Error recording behavior: {e}", exc_info=True)
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    @app.route('/api/v1/hot', methods=['GET'])
    def get_hot_news():
        try:
            top_n = int(request.args.get('top_n', config.HOT_NEWS_COUNT * 2))
            category = request.args.get('category', None)

            all_news_ids = app.redis.get_all_news_ids()
            candidate_news_info = app.redis.get_batch_news_info(all_news_ids)
            candidate_news = list(candidate_news_info.values())

            if category:
                candidate_news = [n for n in candidate_news if n.get('category') == category]

            hot_news = app.hot_news_provider.get_hot_news(
                candidate_news,
                {},
                top_n=top_n
            )

            results = []
            for rank, (news_id, score) in enumerate(hot_news, 1):
                news = candidate_news_info.get(news_id, {})
                results.append({
                    'news_id': news_id,
                    'score': float(score),
                    'category': news.get('category', ''),
                    'title': news.get('title', ''),
                    'rank': rank,
                    'is_hot': True
                })

            return jsonify({
                'success': True,
                'count': len(results),
                'hot_news': results
            })

        except Exception as e:
            logger.error(f"Error getting hot news: {e}", exc_info=True)
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    @app.route('/api/v1/similar/<int:news_id>', methods=['GET'])
    def get_similar_news(news_id: int):
        try:
            top_k = int(request.args.get('top_k', 10))

            if not app.recommender or not app.recommender.model:
                return jsonify({
                    'success': False,
                    'error': 'Recommendation model not available'
                }), 503

            all_news_ids = app.redis.get_all_news_ids()
            candidate_news_info = app.redis.get_batch_news_info(all_news_ids)
            candidate_news = list(candidate_news_info.values())

            similar_news = app.recommender.get_similar_news(
                news_id=news_id,
                all_news=candidate_news,
                top_k=top_k
            )

            results = []
            for rank, (sim_news_id, similarity) in enumerate(similar_news, 1):
                news = candidate_news_info.get(sim_news_id, {})
                results.append({
                    'news_id': sim_news_id,
                    'similarity': float(similarity),
                    'category': news.get('category', ''),
                    'title': news.get('title', ''),
                    'rank': rank
                })

            return jsonify({
                'success': True,
                'news_id': news_id,
                'similar_news': results
            })

        except Exception as e:
            logger.error(f"Error getting similar news for {news_id}: {e}", exc_info=True)
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    @app.route('/api/v1/user/<int:user_id>/profile', methods=['GET'])
    def get_user_profile(user_id: int):
        try:
            profile = app.redis.get_user_profile(user_id)
            if not profile:
                return jsonify({
                    'success': False,
                    'user_id': user_id,
                    'error': 'User profile not found'
                }), 404

            behavior_history = app.redis.get_user_behavior_history(user_id, count=20)
            recent_viewed = app.redis.get_recent_viewed(user_id)

            return jsonify({
                'success': True,
                'user_id': user_id,
                'category_preferences': profile.category_preferences,
                'recent_behavior_count': len(profile.recent_behavior),
                'recent_behavior': behavior_history,
                'recent_viewed_count': len(recent_viewed),
                'last_updated': profile.last_updated.isoformat() if profile.last_updated else None
            })

        except Exception as e:
            logger.error(f"Error getting user profile for {user_id}: {e}", exc_info=True)
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    @app.route('/api/v1/user/<int:user_id>/preferences', methods=['POST'])
    def update_user_preferences(user_id: int):
        try:
            data = request.get_json(force=True)
            preferences = data.get('preferences', {})

            profile = app.redis.get_user_profile(user_id)
            if not profile:
                profile = UserProfile(user_id=user_id)

            for category, score in preferences.items():
                if category in config.CATEGORY_LIST:
                    profile.category_preferences[category] = float(score)

            app.redis.set_user_profile(user_id, profile)

            return jsonify({
                'success': True,
                'user_id': user_id,
                'preferences': profile.category_preferences,
                'message': 'Preferences updated successfully'
            })

        except Exception as e:
            logger.error(f"Error updating preferences for user {user_id}: {e}", exc_info=True)
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    @app.route('/api/v1/trigger_update/<int:user_id>', methods=['POST'])
    def trigger_profile_update(user_id: int):
        try:
            if not app.recommender or not app.recommender.model:
                return jsonify({
                    'success': False,
                    'error': 'Recommendation model not available'
                }), 503

            from feedback.updater import RealTimeUpdater
            updater = RealTimeUpdater(
                redis_client=app.redis,
                recommender=app.recommender,
                online_manager=app.online_manager
            )

            success = updater.update_user_profile(user_id)

            return jsonify({
                'success': success,
                'user_id': user_id,
                'message': 'Profile update triggered' if success else 'Update failed'
            })

        except Exception as e:
            logger.error(f"Error triggering update for user {user_id}: {e}", exc_info=True)
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    @app.route('/api/v1/online_learning/status', methods=['GET'])
    def get_online_learning_status():
        try:
            if not app.online_manager:
                return jsonify({
                    'success': True,
                    'online_learning_enabled': False,
                    'message': 'Online learning not enabled'
                })

            stats = app.online_manager.get_stats()
            return jsonify({
                'success': True,
                'online_learning_enabled': True,
                'stats': stats
            })

        except Exception as e:
            logger.error(f"Error getting online learning status: {e}", exc_info=True)
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    @app.route('/api/v1/online_learning/train', methods=['POST'])
    def trigger_online_training():
        try:
            if not app.recommender or not app.recommender.use_online_learning:
                return jsonify({
                    'success': False,
                    'error': 'Online learning not enabled'
                }), 400

            data = request.get_json(force=True, silent=True) or {}
            num_samples = int(data.get('num_samples', 2000))
            epochs = int(data.get('epochs', 1))
            batch_size = int(data.get('batch_size', 64))
            time_window_hours = data.get('time_window_hours')

            history = app.recommender.trigger_online_training(
                num_samples=num_samples,
                epochs=epochs,
                batch_size=batch_size,
                time_window_hours=time_window_hours
            )

            if history is None:
                return jsonify({
                    'success': False,
                    'message': 'Not enough samples for training'
                })

            return jsonify({
                'success': True,
                'message': 'Online training completed',
                'final_loss': float(history.history.get('loss', [0])[-1]),
                'final_auc': float(history.history.get('auc', [0])[-1]),
                'epochs_run': len(history.history.get('loss', []))
            })

        except Exception as e:
            logger.error(f"Error triggering online training: {e}", exc_info=True)
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    @app.route('/api/v1/online_learning/merge', methods=['POST'])
    def merge_online_model():
        try:
            if not app.online_manager:
                return jsonify({
                    'success': False,
                    'error': 'Online learning not enabled'
                }), 400

            data = request.get_json(force=True, silent=True) or {}
            merge_ratio = float(data.get('merge_ratio', 0.1))

            app.online_manager.merge_online_into_offline(merge_ratio=merge_ratio)

            return jsonify({
                'success': True,
                'message': f'Models merged with ratio {merge_ratio}'
            })

        except Exception as e:
            logger.error(f"Error merging models: {e}", exc_info=True)
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    @app.route('/api/v1/recommend/explainable', methods=['POST'])
    def get_explainable_recommendations():
        try:
            data = request.get_json(force=True, silent=True) or {}
            user_id = int(data.get('user_id', 0))
            top_n = int(data.get('top_n', config.RECOMMEND_TOP_N))
            exclude_news_ids = data.get('exclude_news_ids', [])
            use_multi_objective = data.get('use_multi_objective', True)

            user_profile = app.recommender.get_user_profile(user_id)
            candidate_news = app.recommender.get_candidate_news()
            news_stats = app.recommender.get_news_stats()

            explained = app.recommender.generate_explainable_recommendations(
                user_id=user_id,
                candidate_news=candidate_news,
                user_profile=user_profile,
                top_n=top_n,
                exclude_news_ids=exclude_news_ids,
                use_multi_objective=use_multi_objective,
                news_stats=news_stats
            )

            return jsonify({
                'success': True,
                'user_id': user_id,
                'recommendations': [er.to_dict() for er in explained],
                'total_count': len(explained)
            })

        except Exception as e:
            logger.error(f"Error getting explainable recommendations: {e}", exc_info=True)
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    @app.route('/api/v1/recommend/trending', methods=['POST'])
    def get_trending_recommendations():
        try:
            data = request.get_json(force=True, silent=True) or {}
            user_id = data.get('user_id')
            top_n = int(data.get('top_n', config.RECOMMEND_TOP_N))
            prefer_emerging = data.get('prefer_emerging', True)
            personalize = data.get('personalize', True)

            candidate_news = app.recommender.get_candidate_news()
            news_stats = app.recommender.get_news_stats()

            user_profile = None
            if personalize and user_id is not None:
                user_id = int(user_id)
                user_profile = app.recommender.get_user_profile(user_id)

            trending = app.recommender.generate_trending_recommendations(
                user_id=user_id if user_id is not None else -1,
                candidate_news=candidate_news,
                news_stats=news_stats,
                user_profile=user_profile,
                top_n=top_n,
                prefer_emerging=prefer_emerging
            )

            return jsonify({
                'success': True,
                'user_id': user_id,
                'personalized': user_profile is not None,
                'recommendations': [rec.to_dict() for rec in trending],
                'total_count': len(trending)
            })

        except Exception as e:
            logger.error(f"Error getting trending recommendations: {e}", exc_info=True)
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    @app.route('/api/v1/trends/predict', methods=['GET'])
    def predict_trending_news():
        try:
            top_n = int(request.args.get('top_n', 20))

            candidate_news = app.recommender.get_candidate_news()
            news_stats = app.recommender.get_news_stats()

            predictions = app.recommender.predict_trending_news(
                all_news=candidate_news,
                news_stats=news_stats,
                top_n=top_n
            )

            return jsonify({
                'success': True,
                'predictions': [
                    {
                        'news_id': p.news_id,
                        'predicted_hot_score': float(p.predicted_hot_score),
                        'trend_score': float(p.trend_score),
                        'growth_potential': float(p.growth_potential),
                        'time_to_peak_hours': float(p.time_to_peak),
                        'confidence': float(p.confidence),
                        'related_trends': p.related_trends,
                        'is_emerging': p.is_emerging
                    }
                    for p in predictions
                ],
                'total_count': len(predictions)
            })

        except Exception as e:
            logger.error(f"Error predicting trending news: {e}", exc_info=True)
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    @app.route('/api/v1/multi_objective/weights', methods=['POST'])
    def adjust_multi_objective_weights():
        try:
            data = request.get_json(force=True, silent=True) or {}
            click_weight = data.get('click_weight')
            duration_weight = data.get('duration_weight')
            like_weight = data.get('like_weight')
            share_weight = data.get('share_weight')

            if click_weight is None and duration_weight is None and like_weight is None and share_weight is None:
                return jsonify({
                    'success': False,
                    'error': 'At least one weight must be provided'
                }), 400

            app.recommender.multi_objective_optimizer.adjust_weights(
                click_weight=click_weight,
                duration_weight=duration_weight,
                like_weight=like_weight,
                share_weight=share_weight
            )

            weights = app.recommender.multi_objective_optimizer.weights
            return jsonify({
                'success': True,
                'message': 'Multi-objective weights updated',
                'current_weights': {
                    'click': float(weights.click_weight),
                    'duration': float(weights.duration_weight),
                    'like': float(weights.like_weight),
                    'share': float(weights.share_weight)
                }
            })

        except Exception as e:
            logger.error(f"Error adjusting multi-objective weights: {e}", exc_info=True)
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    @app.route('/api/v1/multi_objective/weights', methods=['GET'])
    def get_multi_objective_weights():
        try:
            weights = app.recommender.multi_objective_optimizer.weights
            return jsonify({
                'success': True,
                'weights': {
                    'click': float(weights.click_weight),
                    'duration': float(weights.duration_weight),
                    'like': float(weights.like_weight),
                    'share': float(weights.share_weight)
                }
            })

        except Exception as e:
            logger.error(f"Error getting multi-objective weights: {e}", exc_info=True)
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    @app.route('/api/v1/trends/social', methods=['POST'])
    def ingest_social_trends():
        try:
            data = request.get_json(force=True, silent=True) or {}
            social_data = data.get('social_data', [])

            if not social_data:
                return jsonify({
                    'success': False,
                    'error': 'No social data provided'
                }), 400

            trends = app.recommender.trend_predictor.detect_trends_from_social(social_data)
            stats = app.recommender.trend_predictor.get_trend_statistics()

            return jsonify({
                'success': True,
                'detected_trends': len(trends),
                'trend_ids': [t.trend_id for t in trends],
                'statistics': stats
            })

        except Exception as e:
            logger.error(f"Error ingesting social trends: {e}", exc_info=True)
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    @app.errorhandler(404)
    def not_found(error):
        return jsonify({
            'success': False,
            'error': 'Endpoint not found'
        }), 404

    @app.errorhandler(500)
    def internal_error(error):
        return jsonify({
            'success': False,
            'error': 'Internal server error'
        }), 500

    return app


def run_app(
    recommender: Optional[NewsRecommender] = None,
    redis_client: Optional[RedisClient] = None,
    producer: Optional[BehaviorProducer] = None,
    online_manager: Optional[OnlineLearningManager] = None,
    host: str = None,
    port: int = None,
    debug: bool = None
):
    host = host or config.FLASK_HOST
    port = port or config.FLASK_PORT
    debug = debug if debug is not None else config.FLASK_DEBUG

    app = create_app(recommender, redis_client, producer, online_manager)

    logger.info(f"Starting recommendation API on {host}:{port}")
    logger.info(f"Online learning enabled: {online_manager is not None}")
    app.run(host=host, port=port, debug=debug, threaded=True)

    return app
