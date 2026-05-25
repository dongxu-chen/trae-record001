import os
from dataclasses import dataclass, field
from typing import List


@dataclass
class Config:
    REDIS_HOST: str = os.getenv('REDIS_HOST', 'localhost')
    REDIS_PORT: int = int(os.getenv('REDIS_PORT', 6379))
    REDIS_DB: int = int(os.getenv('REDIS_DB', 0))

    KAFKA_BROKERS: List[str] = field(
        default_factory=lambda: os.getenv('KAFKA_BROKERS', 'localhost:9092').split(',')
    )
    KAFKA_TOPIC_BEHAVIOR: str = os.getenv('KAFKA_TOPIC_BEHAVIOR', 'user_behavior')
    KAFKA_GROUP_ID: str = os.getenv('KAFKA_GROUP_ID', 'recommender_group')

    MODEL_PATH: str = os.getenv('MODEL_PATH', './models/deepfm_attention')
    EMBEDDING_DIM: int = int(os.getenv('EMBEDDING_DIM', 16))
    DNN_HIDDEN_UNITS: List[int] = field(default_factory=lambda: [128, 64, 32])
    LEARNING_RATE: float = float(os.getenv('LEARNING_RATE', 0.001))
    BATCH_SIZE: int = int(os.getenv('BATCH_SIZE', 256))
    EPOCHS: int = int(os.getenv('EPOCHS', 20))

    NUM_USERS: int = int(os.getenv('NUM_USERS', 1000))
    NUM_NEWS: int = int(os.getenv('NUM_NEWS', 5000))
    NUM_CATEGORIES: int = int(os.getenv('NUM_CATEGORIES', 10))

    RECOMMEND_TOP_N: int = int(os.getenv('RECOMMEND_TOP_N', 20))
    HOT_NEWS_COUNT: int = int(os.getenv('HOT_NEWS_COUNT', 5))
    DIVERSITY_PENALTY: float = float(os.getenv('DIVERSITY_PENALTY', 0.3))
    CATEGORY_MAX_RATIO: float = float(os.getenv('CATEGORY_MAX_RATIO', 0.4))

    BEHAVIOR_WEIGHTS = {
        'view': 1.0,
        'like': 3.0,
        'share': 5.0,
        'duration': 0.02
    }

    REAL_TIME_UPDATE_INTERVAL: int = int(os.getenv('REAL_TIME_UPDATE_INTERVAL', 60))
    USER_PROFILE_TTL: int = int(os.getenv('USER_PROFILE_TTL', 86400))
    NEWS_CACHE_TTL: int = int(os.getenv('NEWS_CACHE_TTL', 3600))

    FLASK_HOST: str = os.getenv('FLASK_HOST', '0.0.0.0')
    FLASK_PORT: int = int(os.getenv('FLASK_PORT', 5000))
    FLASK_DEBUG: bool = os.getenv('FLASK_DEBUG', 'True').lower() == 'true'

    CATEGORY_LIST: List[str] = None

    TREND_PREDICTION_WINDOW_HOURS: int = 6
    TREND_GROWTH_THRESHOLD: float = 1.5
    TREND_SOCIAL_WEIGHT: float = 0.6
    TREND_ENGAGEMENT_WEIGHT: float = 0.4
    TREND_DECAY_HOURS: int = 12

    MULTI_OBJECTIVE_CLICK_WEIGHT: float = 0.5
    MULTI_OBJECTIVE_DURATION_WEIGHT: float = 0.5
    MULTI_OBJECTIVE_DURATION_NORMALIZATION: float = 120.0

    EXPLANATION_MAX_REASONS: int = 3
    EXPLANATION_MIN_BEHAVIOR_COUNT: int = 2
    EXPLANATION_SIMILARITY_THRESHOLD: float = 0.7

    def __post_init__(self):
        if self.CATEGORY_LIST is None:
            self.CATEGORY_LIST = [
                '科技', '财经', '体育', '娱乐', '军事',
                '教育', '健康', '旅游', '美食', '汽车'
            ][:self.NUM_CATEGORIES]


config = Config()
