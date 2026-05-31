import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    NEO4J_URI: str = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    NEO4J_USER: str = os.getenv("NEO4J_USER", "neo4j")
    NEO4J_PASSWORD: str = os.getenv("NEO4J_PASSWORD", "password")
    
    CLUSTER_THRESHOLD: float = 0.75
    ADAPTIVE_THRESHOLD_ENABLED: bool = True
    ADAPTIVE_THRESHOLD_MIN: float = 0.65
    ADAPTIVE_THRESHOLD_MAX: float = 0.85
    ADAPTIVE_SIZE_WEIGHT: float = 0.3
    ADAPTIVE_DENSITY_WEIGHT: float = 0.4
    ADAPTIVE_LIFECYCLE_WEIGHT: float = 0.3
    
    MIN_CLUSTER_SIZE: int = 3
    TOPIC_KEYWORDS_COUNT: int = 10
    
    WEBSOCKET_HOST: str = "0.0.0.0"
    WEBSOCKET_PORT: int = 8000
    
    NEWS_BATCH_SIZE: int = 50
    INFLUENCE_DECAY: float = 0.95
    BURST_THRESHOLD: float = 2.0
    DECAY_THRESHOLD: float = 0.3
    
    SHARE_WEIGHT: float = 0.25
    REACH_WEIGHT: float = 0.25
    ENGAGEMENT_WEIGHT: float = 0.2
    VELOCITY_WEIGHT: float = 0.15
    MOMENTUM_WEIGHT: float = 0.15
    
    WARNING_MIN_CONFIDENCE: float = 0.4
    WARNING_SIZE_GROWTH_THRESHOLD: float = 2.0
    WARNING_VELOCITY_THRESHOLD: float = 5.0
    WARNING_MOMENTUM_THRESHOLD: float = 1.0
    WARNING_SOCIAL_THRESHOLD: float = 0.5
    WARNING_SOCIAL_ACCELERATION_THRESHOLD: float = 50.0
    BURST_TARGET_SIZE: int = 50
    
    PROPAGATION_MIN_ARTICLES: int = 3
    PROPAGATION_IGNITION_TIME_GAP_FACTOR: float = 2.0
    
    COMPARISON_MIN_HISTORY_POINTS: int = 5
    COMPARISON_SIMILARITY_THRESHOLD: float = 0.5

    class Config:
        env_file = ".env"

settings = Settings()
