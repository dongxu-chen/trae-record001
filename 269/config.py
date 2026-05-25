import os


class Settings:
    REDIS_HOST: str = os.getenv("REDIS_HOST", "localhost")
    REDIS_PORT: int = int(os.getenv("REDIS_PORT", 6379))
    REDIS_DB: int = int(os.getenv("REDIS_DB", 0))
    REDIS_PASSWORD: str = os.getenv("REDIS_PASSWORD", "")
    
    CF_MODEL_PATH: str = os.getenv("CF_MODEL_PATH", "./models/cf_model.pkl")
    SIMILARITY_MATRIX_PATH: str = os.getenv("SIMILARITY_MATRIX_PATH", "./models/similarity_matrix.pkl")
    
    NUM_RECOMMENDATIONS: int = int(os.getenv("NUM_RECOMMENDATIONS", 10))
    CF_WEIGHT: float = float(os.getenv("CF_WEIGHT", 0.5))
    CONTENT_WEIGHT: float = float(os.getenv("CONTENT_WEIGHT", 0.5))
    
    BANDIT_EPSILON: float = float(os.getenv("BANDIT_EPSILON", 0.1))
    BANDIT_ALPHA: float = float(os.getenv("BANDIT_ALPHA", 1.0))
    BANDIT_BETA: float = float(os.getenv("BANDIT_BETA", 1.0))
    
    CACHE_TTL: int = int(os.getenv("CACHE_TTL", 3600))


settings = Settings()
