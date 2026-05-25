import os
import logging
import argparse
import sys
from datetime import datetime, timedelta
from typing import Optional

import numpy as np
import tensorflow as tf

from config import config
from data.generator import DataGenerator
from data.models import UserProfile
from model.deepfm import DeepFMModel
from model.recommender import NewsRecommender
from model.online_learning import OnlineLearningManager
from cache.redis_client import RedisClient
from streaming.producer import BehaviorProducer
from streaming.consumer import BatchBehaviorConsumer
from strategy.diversity import DiversityController, BlockBasedDiversity, BlockConfig
from strategy.hot_news import HotNewsProvider
from feedback.updater import RealTimeUpdater, FeedbackLoopManager
from api.app import run_app, create_app

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def init_redis_with_data(redis_client: RedisClient, news_list, users=None):
    logger.info("Initializing Redis with news data...")

    for news in news_list:
        news_dict = news.to_dict()
        redis_client.set_news_info(news_dict)

    logger.info(f"Loaded {len(news_list)} news items into Redis")

    if users:
        logger.info(f"Loaded {len(users)} users")


def train_model_command(args):
    logger.info("Starting model training...")

    generator = DataGenerator()

    logger.info("Generating simulated data...")
    users = generator.generate_users(num_users=config.NUM_USERS)
    news_list = generator.generate_news(num_news=config.NUM_NEWS)
    behaviors = generator.generate_user_behaviors(users, news_list, num_behaviors=50000)

    logger.info(f"Generated {len(users)} users, {len(news_list)} news, {len(behaviors)} behaviors")

    logger.info("Preparing training data...")
    df = generator.generate_training_data(behaviors, news_list)
    logger.info(f"Training data shape: {df.shape}")
    logger.info(f"Label distribution: {df['label'].value_counts().to_dict()}")

    current_time = datetime.now()

    def create_dataset(df):
        user_ids = df['user_id'].values
        news_ids = df['news_id'].values
        category_ids = df['category_id'].values
        labels = df['label'].values
        weights = df['weight'].values

        def gen():
            for i in range(len(df)):
                recent_news = []
                recent_timestamps = []
                recent_publish_times = []

                yield (
                    int(user_ids[i]),
                    int(news_ids[i]),
                    int(category_ids[i]),
                    recent_news,
                    recent_timestamps,
                    recent_publish_times,
                    current_time,
                    float(labels[i]),
                    float(weights[i])
                )

        def map_fn(user_id, news_id, category_id, seq, ts_list, pt_list, cur_time, label, weight):
            seq_len = tf.shape(seq)[0]
            padded = tf.pad(seq, [[0, tf.maximum(0, 50 - seq_len)]])
            padded = padded[:50]
            mask = tf.sequence_mask(seq_len, maxlen=50, dtype=tf.float32)

            time_diffs = tf.zeros([50], dtype=tf.float32)
            news_ages = tf.zeros([50], dtype=tf.float32)
            candidate_age = tf.zeros([1], dtype=tf.float32)

            return (
                {
                    'user_id': user_id,
                    'news_id': news_id,
                    'category_id': category_id,
                    'behavior_sequence': padded,
                    'mask': mask,
                    'behavior_time_diffs': time_diffs,
                    'news_ages': news_ages,
                    'candidate_news_age': candidate_age
                },
                label,
                weight
            )

        dataset = tf.data.Dataset.from_generator(
            gen,
            output_signature=(
                tf.TensorSpec(shape=(), dtype=tf.int32),
                tf.TensorSpec(shape=(), dtype=tf.int32),
                tf.TensorSpec(shape=(), dtype=tf.int32),
                tf.TensorSpec(shape=(None,), dtype=tf.int32),
                tf.TensorSpec(shape=(None,), dtype=tf.float32),
                tf.TensorSpec(shape=(None,), dtype=tf.float32),
                tf.TensorSpec(shape=(), dtype=tf.float32),
                tf.TensorSpec(shape=(), dtype=tf.float32),
                tf.TensorSpec(shape=(), dtype=tf.float32)
            )
        )

        dataset = dataset.map(map_fn)
        return dataset

    train_size = int(0.8 * len(df))
    train_df = df.iloc[:train_size]
    val_df = df.iloc[train_size:]

    train_dataset = create_dataset(train_df)
    val_dataset = create_dataset(val_df)

    logger.info("Building DeepFM model with time-aware attention...")
    model = DeepFMModel(
        num_users=config.NUM_USERS,
        num_news=config.NUM_NEWS,
        num_categories=config.NUM_CATEGORIES,
        use_time_decay=True,
        use_news_age_decay=True,
        use_elastic_learning=False
    )

    model.model.summary(print_fn=logger.info)

    logger.info("Starting training...")
    history = model.train(
        train_dataset=train_dataset,
        val_dataset=val_dataset,
        epochs=config.EPOCHS,
        batch_size=config.BATCH_SIZE
    )

    logger.info("Training completed!")
    for metric, values in history.history.items():
        logger.info(f"{metric}: {values[-1]:.4f}")

    os.makedirs(config.MODEL_PATH, exist_ok=True)
    model.save(config.MODEL_PATH)
    logger.info(f"Model saved to {config.MODEL_PATH}")

    redis_client = RedisClient()
    init_redis_with_data(redis_client, news_list, users)
    redis_client.close()

    logger.info("Training pipeline completed successfully!")


def start_server_command(args):
    logger.info("Starting recommendation server...")

    use_online_learning = not getattr(args, 'disable_online_learning', False)
    use_multi_objective = not getattr(args, 'disable_multi_objective', False)
    use_explainable = not getattr(args, 'disable_explainable', True)
    use_trend_prediction = not getattr(args, 'disable_trend_prediction', False)

    recommender = NewsRecommender(
        use_online_learning=use_online_learning,
        use_multi_objective=use_multi_objective,
        use_explainable=use_explainable
    )
    online_manager = None

    try:
        if os.path.exists(config.MODEL_PATH):
            recommender.load_model(config.MODEL_PATH)
            logger.info("Recommendation model loaded successfully")

            if use_online_learning:
                logger.info("Initializing online learning manager...")
                online_manager = OnlineLearningManager(
                    offline_model=recommender.model,
                    buffer_max_size=100000,
                    min_samples_for_train=100,
                    online_learning_rate=0.0001,
                    ewc_lambda=100.0,
                    use_elastic_learning=True,
                    use_ewc=False,
                    fusion_alpha=0.7
                )
                recommender.online_manager = online_manager
                logger.info("Online learning manager initialized with elastic learning")
        else:
            logger.warning(f"Model not found at {config.MODEL_PATH}. Running with fallback to hot news.")
    except Exception as e:
        logger.warning(f"Failed to load model: {e}. Running with fallback to hot news.")

    redis_client = RedisClient()

    all_news_ids = redis_client.get_all_news_ids()
    if not all_news_ids or max(all_news_ids) < 100:
        logger.info("No data in Redis, generating initial data...")
        generator = DataGenerator()
        news_list = generator.generate_news(num_news=config.NUM_NEWS)
        init_redis_with_data(redis_client, news_list)

    producer = BehaviorProducer()
    consumer = BatchBehaviorConsumer()
    consumer.set_mock_producer(producer)

    updater = RealTimeUpdater(
        redis_client=redis_client,
        recommender=recommender,
        consumer=consumer,
        online_manager=online_manager
    )
    updater.start()

    try:
        run_app(
            recommender=recommender,
            redis_client=redis_client,
            producer=producer,
            online_manager=online_manager,
            host=args.host,
            port=args.port,
            debug=args.debug
        )
    except KeyboardInterrupt:
        logger.info("Server shutdown requested")
    finally:
        updater.stop()
        producer.close()
        consumer.close()
        redis_client.close()


def test_recommendation_command(args):
    logger.info("Testing recommendation system...")

    redis_client = RedisClient()
    producer = BehaviorProducer()

    all_news_ids = redis_client.get_all_news_ids()
    if not all_news_ids or max(all_news_ids) < 100:
        logger.info("Generating test data...")
        generator = DataGenerator()
        news_list = generator.generate_news(num_news=500)
        users = generator.generate_users(num_users=100)
        init_redis_with_data(redis_client, news_list, users)

        user_id = args.user_id
        for _ in range(10):
            news_id = np.random.choice(200)
            producer.send_behavior(
                user_id=user_id,
                news_id=news_id,
                behavior_type='view',
                duration=np.random.uniform(30, 120)
            )
        producer.flush()

        for _ in range(3):
            news_id = np.random.choice(50)
            producer.send_behavior(
                user_id=user_id,
                news_id=news_id,
                behavior_type='like'
            )
        producer.flush()

        news_info = redis_client.get_news_info(0)
        category = news_info.get('category', '') if news_info else ''
        for _ in range(5):
            news_id = np.random.choice(100)
            producer.send_behavior(
                user_id=user_id,
                news_id=news_id,
                behavior_type='view',
                duration=np.random.uniform(60, 180),
                extra={'category': category}
            )
        producer.flush()

    consumer = BatchBehaviorConsumer()
    consumer.set_mock_producer(producer)

    use_online_learning = not args.disable_online_learning
    recommender = NewsRecommender(use_online_learning=use_online_learning)
    online_manager = None

    if os.path.exists(config.MODEL_PATH):
        try:
            recommender.load_model(config.MODEL_PATH)
            logger.info("Model loaded for testing")

            if use_online_learning:
                online_manager = OnlineLearningManager(
                    offline_model=recommender.model,
                    buffer_max_size=10000,
                    min_samples_for_train=50,
                    online_learning_rate=0.0001,
                    use_elastic_learning=True
                )
                recommender.online_manager = online_manager
                logger.info("Online learning enabled for testing")
        except Exception as e:
            logger.warning(f"Could not load model: {e}")

    updater = RealTimeUpdater(
        redis_client=redis_client,
        recommender=recommender,
        consumer=consumer,
        online_manager=online_manager
    )
    updater.update_user_profile(args.user_id)

    profile = redis_client.get_user_profile(args.user_id)
    if profile:
        logger.info(f"User {args.user_id} profile:")
        logger.info(f"  Category preferences: {profile.category_preferences}")
        logger.info(f"  Recent behaviors: {len(profile.recent_behavior)}")

    use_block_diversity = not args.disable_block_diversity

    if use_block_diversity:
        logger.info("Using block-based diversity control")
        diversity_controller = BlockBasedDiversity(
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
    else:
        logger.info("Using legacy diversity control")
        diversity_controller = DiversityController(use_block_based=False)

    hot_news_provider = HotNewsProvider()

    all_news_ids = redis_client.get_all_news_ids()
    news_info = redis_client.get_batch_news_info(all_news_ids)
    candidate_news = list(news_info.values())

    if recommender.model is not None:
        recommendations = recommender.generate_recommendations(
            user_id=args.user_id,
            candidate_news=candidate_news,
            user_profile=profile or UserProfile(user_id=args.user_id),
            top_n=args.top_n * 3,
            use_ensemble=use_online_learning
        )
    else:
        recommendations = hot_news_provider.cold_start_recommend(
            user_id=args.user_id,
            all_news=candidate_news,
            news_stats={},
            user_preferences=profile.category_preferences if profile else None,
            top_n=args.top_n * 3
        )

    if use_block_diversity:
        block_stats = diversity_controller.get_block_statistics(
            recommendations,
            profile.category_preferences if profile else None
        )
        logger.info(f"Block statistics: {block_stats['total_blocks']} blocks")

        recommendations = diversity_controller.apply_block_diversity(
            recommendations,
            top_n=args.top_n,
            user_preferences=profile.category_preferences if profile else None,
            use_round_robin=True
        )
    else:
        recommendations = diversity_controller.apply_diversity(
            recommendations,
            top_n=args.top_n,
            user_preferences=profile.category_preferences if profile else None
        )

    hot_news = hot_news_provider.get_hot_news(candidate_news, {})
    recommendations = hot_news_provider.merge_hot_news(
        personalized_recommendations=recommendations,
        hot_news=hot_news,
        news_info=news_info
    )

    diversity_score = diversity_controller.calculate_diversity_score(recommendations)

    logger.info("\n=== Recommendations for User %d ===", args.user_id)
    logger.info(f"Diversity Score: {diversity_score}")
    logger.info(f"Block-based diversity: {use_block_diversity}")
    logger.info(f"Online learning: {use_online_learning}")
    logger.info(f"{'Rank':<6}{'News ID':<10}{'Score':<10}{'Category':<12}{'Hot':<6}{'Reason'}")
    logger.info("-" * 80)

    for rec in recommendations[:args.top_n]:
        hot_marker = "✓" if rec.is_hot else ""
        logger.info(f"{rec.rank:<6}{rec.news_id:<10}{rec.score:<10.4f}{rec.category:<12}{hot_marker:<6}{rec.reason}")

    category_counts = {}
    for rec in recommendations[:args.top_n]:
        category_counts[rec.category] = category_counts.get(rec.category, 0) + 1
    logger.info(f"\nCategory distribution: {category_counts}")

    if use_online_learning and online_manager and args.simulate_online:
        logger.info("\n=== Testing Online Learning ===")

        logger.info("Adding simulated feedback samples...")
        for i in range(150):
            news_id = np.random.randint(0, 200)
            label = np.random.choice([0.0, 0.6, 1.0], p=[0.3, 0.4, 0.3])
            recommender.add_feedback_for_online_learning(
                user_id=args.user_id,
                news_id=news_id,
                category_id=np.random.randint(0, config.NUM_CATEGORIES),
                user_profile=profile or UserProfile(user_id=args.user_id),
                label=label
            )

        logger.info(f"Buffer size: {len(online_manager.buffer)}")

        if online_manager.buffer.should_train():
            logger.info("Triggering online training...")
            history = recommender.trigger_online_training(num_samples=100, epochs=1)
            if history:
                logger.info(f"Online training loss: {history.history.get('loss', [0])[-1]:.4f}")
                logger.info(f"Online training AUC: {history.history.get('auc', [0])[-1]:.4f}")
            else:
                logger.info("Online training skipped")
        else:
            logger.info("Not enough samples for online training")

        stats = online_manager.get_stats()
        logger.info(f"Online learning stats: {stats}")

    feedback_manager = FeedbackLoopManager(
        redis_client=redis_client,
        recommender=recommender,
        consumer=consumer,
        online_manager=online_manager
    )

    if recommendations:
        top_news = recommendations[0]
        explanations = feedback_manager.get_recommendation_explanations(
            user_id=args.user_id,
            recommendations=[top_news]
        )
        if explanations:
            logger.info(f"\nExplanation for top recommendation (News {top_news.news_id}):")
            for reason in explanations[0]['reasons']:
                logger.info(f"  - {reason}")

    producer.close()
    consumer.close()
    redis_client.close()

    logger.info("\nRecommendation test completed!")


def test_explainable_command(args):
    logger.info("Testing explainable recommendations...")

    redis_client = RedisClient()
    generator = DataGenerator()

    all_news_ids = redis_client.get_all_news_ids()
    if not all_news_ids or max(all_news_ids) < 100:
        logger.info("Generating initial data...")
        news_list = generator.generate_news(num_news=config.NUM_NEWS)
        init_redis_with_data(redis_client, news_list)

    user_id = args.user_id
    user_profile = redis_client.get_user_profile(user_id)
    if not user_profile:
        user_profile = UserProfile(user_id=user_id)
        for _ in range(10):
            user_profile.recent_behavior.append({
                'news_id': np.random.choice(200),
                'category': np.random.choice(config.CATEGORY_LIST),
                'behavior_type': 'view',
                'timestamp': datetime.now().isoformat()
            })
        user_profile.category_preferences = {cat: np.random.uniform(0.3, 0.9) for cat in config.CATEGORY_LIST}
        redis_client.set_user_profile(user_profile)

    recommender = NewsRecommender(
        use_multi_objective=not args.disable_multi_objective,
        use_explainable=True
    )

    if os.path.exists(config.MODEL_PATH):
        try:
            recommender.load_model(config.MODEL_PATH)
            logger.info("Model loaded")
        except Exception as e:
            logger.warning(f"Could not load model: {e}")

    all_news_ids = redis_client.get_all_news_ids()
    news_info = redis_client.get_batch_news_info(all_news_ids)
    candidate_news = list(news_info.values())
    news_stats = {nid: {'click_count': np.random.randint(10, 500),
                        'like_count': np.random.randint(5, 200),
                        'share_count': np.random.randint(1, 100),
                        'avg_duration': np.random.uniform(30, 180)}
                   for nid in all_news_ids}

    profile = redis_client.get_user_profile(user_id)

    explained = recommender.generate_explainable_recommendations(
        user_id=user_id,
        candidate_news=candidate_news,
        user_profile=profile,
        top_n=args.top_n,
        news_stats=news_stats
    )

    logger.info(f"\n=== Explainable Recommendations for User {user_id} ===")
    logger.info(f"Multi-objective enabled: {not args.disable_multi_objective}")
    logger.info(f"{'Rank':<6}{'News ID':<10}{'Score':<10}{'Category':<12}{'Primary Reason'}")
    logger.info("-" * 90)

    for i, er in enumerate(explained, 1):
        logger.info(f"{i:<6}{er.news_id:<10}{er.score:<10.4f}{er.category:<12}{er.primary_reason}")

    logger.info(f"\n=== Detailed Reasons ===")
    for i, er in enumerate(explained[:3], 1):
        logger.info(f"\nRank {i} - News {er.news_id}:")
        for reason in er.reasons:
            logger.info(f"  [{reason.reason_type}] {reason.description} (confidence: {reason.confidence:.2f})")
            if reason.related_news_ids:
                logger.info(f"    Related news: {', '.join(map(str, reason.related_news_ids[:3]))}")

    redis_client.close()
    logger.info("\nExplainable recommendation test completed!")


def test_trending_command(args):
    logger.info("Testing trend prediction...")

    redis_client = RedisClient()
    generator = DataGenerator()

    all_news_ids = redis_client.get_all_news_ids()
    if not all_news_ids or max(all_news_ids) < 100:
        logger.info("Generating initial data...")
        news_list = generator.generate_news(num_news=config.NUM_NEWS)
        init_redis_with_data(redis_client, news_list)

    recommender = NewsRecommender()

    all_news_ids = redis_client.get_all_news_ids()
    news_info = redis_client.get_batch_news_info(all_news_ids)
    candidate_news = list(news_info.values())

    news_stats = {}
    for nid in all_news_ids:
        growth_rate = np.random.uniform(0.5, 5.0)
        news_stats[nid] = {
            'click_count': np.random.randint(10, 1000),
            'like_count': np.random.randint(5, 500),
            'share_count': np.random.randint(1, 200),
            'total_duration': np.random.uniform(600, 10000),
            'click_growth_rate': growth_rate,
            'like_growth_rate': growth_rate * np.random.uniform(0.8, 1.2),
            'share_growth_rate': growth_rate * np.random.uniform(0.8, 1.2)
        }

    social_data = []
    for i in range(50):
        keyword = np.random.choice(['AI', '科技', '股市', '世界杯', '新能源', '人工智能', '经济', '健康'])
        category = np.random.choice(config.CATEGORY_LIST)
        social_data.append({
            'keyword': keyword,
            'category': category,
            'news_id': np.random.choice(all_news_ids),
            'timestamp': datetime.now().isoformat(),
            'sentiment': np.random.uniform(-1, 1)
        })

    trends = recommender.trend_predictor.detect_trends_from_social(social_data)
    logger.info(f"Detected {len(trends)} social trends")

    predictions = recommender.predict_trending_news(
        all_news=candidate_news,
        news_stats=news_stats,
        top_n=args.top_n
    )

    logger.info(f"\n=== Predicted Trending News ===")
    logger.info(f"{'Rank':<6}{'News ID':<10}{'Pred. Score':<12}{'Growth':<10}{'Peak (h)':<10}{'Conf':<8}{'Emerging'}")
    logger.info("-" * 80)

    for i, p in enumerate(predictions, 1):
        emerging_mark = "✓" if p.is_emerging else ""
        logger.info(f"{i:<6}{p.news_id:<10}{p.predicted_hot_score:<12.4f}{p.growth_potential:<10.2f}"
                     f"{p.time_to_peak:<10.1f}{p.confidence:<8.2f}{emerging_mark}")

    user_profile = None
    if not args.no_personalize:
        user_profile = redis_client.get_user_profile(args.user_id)
        if not user_profile:
            user_profile = UserProfile(user_id=args.user_id)

    trending_recs = recommender.generate_trending_recommendations(
        user_id=args.user_id,
        candidate_news=candidate_news,
        news_stats=news_stats,
        user_profile=user_profile if not args.no_personalize else None,
        top_n=args.top_n,
        prefer_emerging=args.prefer_emerging
    )

    logger.info(f"\n=== Trending Recommendations for User {args.user_id} ===")
    logger.info(f"Personalized: {not args.no_personalize}")
    logger.info(f"{'Rank':<6}{'News ID':<10}{'Score':<10}{'Category':<12}{'Reason'}")
    logger.info("-" * 80)

    for rec in trending_recs:
        logger.info(f"{rec.rank:<6}{rec.news_id:<10}{rec.score:<10.4f}{rec.category:<12}{rec.reason}")

    redis_client.close()
    logger.info("\nTrend prediction test completed!")


def test_multi_objective_command(args):
    logger.info("Testing multi-objective optimization...")

    redis_client = RedisClient()
    generator = DataGenerator()

    all_news_ids = redis_client.get_all_news_ids()
    if not all_news_ids or max(all_news_ids) < 100:
        logger.info("Generating initial data...")
        news_list = generator.generate_news(num_news=config.NUM_NEWS)
        init_redis_with_data(redis_client, news_list)

    recommender = NewsRecommender(use_multi_objective=True)
    recommender.multi_objective_optimizer.adjust_weights(
        click_weight=args.click_weight,
        duration_weight=args.duration_weight
    )

    if os.path.exists(config.MODEL_PATH):
        try:
            recommender.load_model(config.MODEL_PATH)
            logger.info("Model loaded")
        except Exception as e:
            logger.warning(f"Could not load model: {e}")

    all_news_ids = redis_client.get_all_news_ids()
    news_info = redis_client.get_batch_news_info(all_news_ids)
    candidate_news = list(news_info.values())
    news_stats = {nid: {'click_count': np.random.randint(10, 500),
                        'like_count': np.random.randint(5, 200),
                        'share_count': np.random.randint(1, 100),
                        'avg_duration': np.random.uniform(30, 180)}
                   for nid in all_news_ids}

    user_profile = redis_client.get_user_profile(args.user_id)
    if not user_profile:
        user_profile = UserProfile(user_id=args.user_id)

    recommendations = recommender.generate_recommendations(
        user_id=args.user_id,
        candidate_news=candidate_news,
        user_profile=user_profile,
        top_n=args.top_n,
        use_multi_objective=True,
        news_stats=news_stats
    )

    weights = recommender.multi_objective_optimizer.weights
    breakdown = recommender.multi_objective_optimizer.get_objective_breakdown(
        recommendations,
        news_stats=news_stats
    )

    logger.info(f"\n=== Multi-Objective Optimization Test ===")
    logger.info(f"Weights - Click: {weights.click_weight:.2f}, Duration: {weights.duration_weight:.2f}")
    logger.info(f"Average Click Score: {breakdown['average_click_score']:.4f}")
    logger.info(f"Average Duration Score: {breakdown['average_duration_score']:.4f}")
    logger.info(f"Pareto Optimal Count: {breakdown['pareto_optimal_count']}/{breakdown['total_candidates']}")
    logger.info(f"\n{'Rank':<6}{'News ID':<10}{'Score':<10}{'Category':<12}{'Click':<8}{'Duration':<10}{'Reason'}")
    logger.info("-" * 90)

    scored = recommender.multi_objective_optimizer.score_recommendations(
        recommendations,
        news_stats=news_stats
    )
    score_map = {s.news_id: s for s in scored}

    for rec in recommendations:
        s = score_map.get(rec.news_id)
        click_str = f"{s.click_score:.3f}" if s else "N/A"
        dur_str = f"{s.duration_score:.3f}" if s else "N/A"
        logger.info(f"{rec.rank:<6}{rec.news_id:<10}{rec.score:<10.4f}{rec.category:<12}"
                     f"{click_str:<8}{dur_str:<10}{rec.reason}")

    logger.info(f"\n=== Pareto Front Analysis ===")
    pareto_scores = [s for s in scored if s.pareto_rank == 0]
    if pareto_scores:
        logger.info(f"Pareto front has {len(pareto_scores)} solutions")
        for s in pareto_scores[:5]:
            logger.info(f"  News {s.news_id}: Click={s.click_score:.3f}, Duration={s.duration_score:.3f}")

    redis_client.close()
    logger.info("\nMulti-objective optimization test completed!")


def simulate_behavior_command(args):
    logger.info("Simulating user behaviors...")

    redis_client = RedisClient()
    producer = BehaviorProducer()

    generator = DataGenerator()
    all_news_ids = redis_client.get_all_news_ids()

    if not all_news_ids or max(all_news_ids) < 100:
        logger.info("Generating initial data...")
        news_list = generator.generate_news(num_news=config.NUM_NEWS)
        init_redis_with_data(redis_client, news_list)

    news_info = redis_client.get_batch_news_info(list(range(min(500, config.NUM_NEWS))))
    news_by_category = {}
    for nid, info in news_info.items():
        cat = info.get('category', '')
        if cat not in news_by_category:
            news_by_category[cat] = []
        news_by_category[cat].append(nid)

    user_preferences = {}
    for user_id in range(args.num_users):
        pref_cats = np.random.choice(config.CATEGORY_LIST, size=np.random.randint(2, 5), replace=False)
        user_preferences[user_id] = {cat: np.random.uniform(0.5, 2.0) for cat in pref_cats}

    logger.info(f"Simulating {args.num_behaviors} behaviors for {args.num_users} users...")

    behavior_types = ['view', 'view', 'view', 'view', 'like', 'share']
    count = 0

    try:
        for _ in range(args.num_behaviors):
            user_id = np.random.randint(0, args.num_users)
            prefs = user_preferences.get(user_id, {})

            if prefs and np.random.random() < 0.7:
                cats = list(prefs.keys())
                weights = list(prefs.values())
                category = cats[np.random.choice(len(cats), p=[w/sum(weights) for w in weights])]
            else:
                category = np.random.choice(config.CATEGORY_LIST)

            candidates = news_by_category.get(category, list(news_info.keys()))
            if not candidates:
                continue

            news_id = int(np.random.choice(candidates))
            behavior_type = np.random.choice(behavior_types)
            duration = np.random.uniform(10, 300) if behavior_type == 'view' else 0.0

            news_detail = news_info.get(news_id, {})
            category_id = news_detail.get('category_id', 0)

            producer.send_behavior(
                user_id=user_id,
                news_id=news_id,
                behavior_type=behavior_type,
                duration=duration,
                category_id=category_id
            )

            count += 1
            if count % 1000 == 0:
                producer.flush()
                logger.info(f"  Sent {count}/{args.num_behaviors} behaviors")

            if args.delay > 0:
                import time
                time.sleep(args.delay / 1000.0)

    except KeyboardInterrupt:
        logger.info(f"Simulation stopped after {count} behaviors")
    finally:
        producer.flush()
        producer.close()
        redis_client.close()

    logger.info(f"Simulation completed: {count} behaviors sent")


def main():
    parser = argparse.ArgumentParser(description='News Recommendation System')
    subparsers = parser.add_subparsers(dest='command', help='Available commands')

    train_parser = subparsers.add_parser('train', help='Train the recommendation model')
    train_parser.add_argument('--epochs', type=int, default=config.EPOCHS, help='Number of epochs')
    train_parser.add_argument('--use_time_decay', action='store_true', default=True,
                             help='Enable time decay in attention')

    server_parser = subparsers.add_parser('serve', help='Start the recommendation API server')
    server_parser.add_argument('--host', type=str, default=config.FLASK_HOST, help='Server host')
    server_parser.add_argument('--port', type=int, default=config.FLASK_PORT, help='Server port')
    server_parser.add_argument('--debug', action='store_true', default=config.FLASK_DEBUG, help='Debug mode')
    server_parser.add_argument('--disable_online_learning', action='store_true',
                              help='Disable online learning')

    test_parser = subparsers.add_parser('test', help='Test recommendation system')
    test_parser.add_argument('--user_id', type=int, default=0, help='User ID to test')
    test_parser.add_argument('--top_n', type=int, default=20, help='Number of recommendations')
    test_parser.add_argument('--disable_block_diversity', action='store_true',
                            help='Use legacy diversity instead of block-based')
    test_parser.add_argument('--disable_online_learning', action='store_true',
                            help='Disable online learning')
    test_parser.add_argument('--simulate_online', action='store_true',
                            help='Simulate online learning during test')
    test_parser.add_argument('--disable_multi_objective', action='store_true',
                            help='Use single objective (CTR only) instead of multi-objective')
    test_parser.add_argument('--disable_explainable', action='store_true',
                            help='Disable explainable recommendations')

    simulate_parser = subparsers.add_parser('simulate', help='Simulate user behaviors')
    simulate_parser.add_argument('--num_users', type=int, default=100, help='Number of users')
    simulate_parser.add_argument('--num_behaviors', type=int, default=10000, help='Number of behaviors')
    simulate_parser.add_argument('--delay', type=float, default=0, help='Delay between behaviors (ms)')

    test_explainable_parser = subparsers.add_parser('test_explainable', help='Test explainable recommendations')
    test_explainable_parser.add_argument('--user_id', type=int, default=0, help='User ID to test')
    test_explainable_parser.add_argument('--top_n', type=int, default=10, help='Number of recommendations')
    test_explainable_parser.add_argument('--disable_multi_objective', action='store_true',
                                         help='Disable multi-objective optimization')

    test_trending_parser = subparsers.add_parser('test_trending', help='Test trend prediction')
    test_trending_parser.add_argument('--user_id', type=int, default=0, help='User ID to test')
    test_trending_parser.add_argument('--top_n', type=int, default=20, help='Number of trending news')
    test_trending_parser.add_argument('--no_personalize', action='store_true',
                                     help='Do not personalize trending results')
    test_trending_parser.add_argument('--prefer_emerging', action='store_true', default=True,
                                     help='Prefer emerging trends')

    test_mo_parser = subparsers.add_parser('test_multi_objective', help='Test multi-objective optimization')
    test_mo_parser.add_argument('--user_id', type=int, default=0, help='User ID to test')
    test_mo_parser.add_argument('--top_n', type=int, default=20, help='Number of recommendations')
    test_mo_parser.add_argument('--click_weight', type=float, default=0.5, help='Weight for CTR')
    test_mo_parser.add_argument('--duration_weight', type=float, default=0.5, help='Weight for duration')

    args = parser.parse_args()

    if args.command == 'train':
        train_model_command(args)
    elif args.command == 'serve':
        start_server_command(args)
    elif args.command == 'test':
        test_recommendation_command(args)
    elif args.command == 'simulate':
        simulate_behavior_command(args)
    elif args.command == 'test_explainable':
        test_explainable_command(args)
    elif args.command == 'test_trending':
        test_trending_command(args)
    elif args.command == 'test_multi_objective':
        test_multi_objective_command(args)
    else:
        parser.print_help()
        print("\nExample usage:")
        print("  python main.py train                  # Train the model")
        print("  python main.py serve                  # Start the API server")
        print("  python main.py test --user_id 0       # Test recommendations")
        print("  python main.py test_explainable       # Test explainable recommendations")
        print("  python main.py test_trending          # Test trend prediction")
        print("  python main.py test_multi_objective   # Test multi-objective optimization")
        print("  python main.py simulate               # Simulate user behaviors")


if __name__ == '__main__':
    main()
