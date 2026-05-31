import os
from typing import Optional, Dict, List


class Config:
    REDIS_HOST: str = os.getenv("REDIS_HOST", "localhost")
    REDIS_PORT: int = int(os.getenv("REDIS_PORT", 6379))
    REDIS_DB: int = int(os.getenv("REDIS_DB", 0))
    REDIS_PASSWORD: Optional[str] = os.getenv("REDIS_PASSWORD", None)
    REDIS_HISTORY_KEY: str = "api_request_history"
    REDIS_MODEL_KEY: str = "api_response_model"

    MODEL_PATH: str = os.getenv("MODEL_PATH", "./models")
    DATA_PATH: str = os.getenv("DATA_PATH", "./data")

    TIMEOUT_THRESHOLD_MS: int = int(os.getenv("TIMEOUT_THRESHOLD_MS", 3000))
    ANOMALY_THRESHOLD: float = float(os.getenv("ANOMALY_THRESHOLD", 2.5))
    ANOMALY_HISTORY_WINDOW: int = int(os.getenv("ANOMALY_HISTORY_WINDOW", 100))

    DYNAMIC_THRESHOLD_PERCENTILE: int = int(os.getenv("DYNAMIC_THRESHOLD_PERCENTILE", 99))
    MIN_HISTORY_FOR_THRESHOLD: int = int(os.getenv("MIN_HISTORY_FOR_THRESHOLD", 50))
    THRESHOLD_SAFETY_MARGIN: float = float(os.getenv("THRESHOLD_SAFETY_MARGIN", 1.2))

    EARLY_WARNING: dict = {
        "enabled": True,
        "warning_window_seconds": 60,
        "prediction_horizon_requests": 5,
        "warning_threshold_probability": 0.6,
        "critical_threshold_probability": 0.85,
        "trend_window_size": 10,
        "trend_slope_threshold": 0.15,
    }

    DOWNSTREAM_SERVICES: Dict[str, List[str]] = {
        "/api/users": ["db_users", "cache_redis"],
        "/api/orders": ["db_orders", "db_users", "queue_kafka"],
        "/api/products": ["db_products", "search_elasticsearch"],
        "/api/payments": ["db_payments", "gateway_stripe", "queue_kafka"],
        "/api/inventory": ["db_inventory", "cache_redis"],
        "/api/reports": ["db_orders", "db_products", "s3_storage"],
        "/api/auth/login": ["db_users", "oauth_service"],
        "/api/search": ["search_elasticsearch", "db_products"],
    }

    DOWNSTREAM_SERVICE_TYPES: List[str] = [
        "db_users", "db_orders", "db_products", "db_payments", "db_inventory",
        "cache_redis", "queue_kafka", "search_elasticsearch", "s3_storage",
        "gateway_stripe", "oauth_service"
    ]

    FEATURE_ENGINEERING: dict = {
        "time_features": True,
        "user_features": True,
        "param_features": True,
        "historical_features": True,
        "downstream_features": True,
        "dependency_impact_features": True,
        "rolling_window_size": 10,
    }

    XGB_PARAMS: dict = {
        "objective": "reg:squarederror",
        "max_depth": 8,
        "learning_rate": 0.08,
        "n_estimators": 150,
        "subsample": 0.85,
        "colsample_bytree": 0.8,
        "random_state": 42,
    }

    API_HOST: str = os.getenv("API_HOST", "0.0.0.0")
    API_PORT: int = int(os.getenv("API_PORT", 8000))

    TIMEOUT_ADVISOR: dict = {
        "target_success_rate": 0.99,
        "min_timeout_ms": 100,
        "max_timeout_ms": 30000,
        "safety_buffer_sigma": 2.0,
        "adaptation_rate": 0.1,
        "min_samples": 20,
        "percentile_targets": [0.95, 0.99, 0.999],
        "cost_weight": 0.3,
    }

    ROOT_CAUSE_ANALYZER: dict = {
        "deviation_threshold": 0.3,
        "min_samples": 10,
        "feature_contribution_threshold": 0.1,
        "history_window": 50,
        "drift_detection_window": 100,
        "drift_significance_level": 0.05,
    }

    MODEL_UPDATER: dict = {
        "min_new_samples": 100,
        "max_new_samples": 5000,
        "update_interval_seconds": 3600,
        "performance_degradation_threshold": 0.05,
        "validation_split": 0.2,
        "rollback_enabled": True,
        "max_model_versions": 5,
        "incremental_learning_rate": 0.3,
        "drift_detection_enabled": True,
        "drift_window_size": 200,
        "drift_significance": 0.05,
    }


config = Config()