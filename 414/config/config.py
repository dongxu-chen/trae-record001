import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

KAFKA_CONFIG = {
    "bootstrap_servers": os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092"),
    "transaction_topic": "credit_card_transactions",
    "alert_topic": "fraud_alerts",
    "scored_topic": "scored_transactions",
    "group_id": "fraud_detection_group",
    "auto_offset_reset": "latest",
    "enable_auto_commit": True,
    "producer_acks": "all",
    "retries": 3,
}

REDIS_CONFIG = {
    "host": os.getenv("REDIS_HOST", "localhost"),
    "port": int(os.getenv("REDIS_PORT", 6379)),
    "db": int(os.getenv("REDIS_DB", 0)),
    "password": os.getenv("REDIS_PASSWORD", None),
    "socket_timeout": 5,
    "retry_on_timeout": True,
    "max_connections": 50,
}

FLINK_CONFIG = {
    "job_manager_address": os.getenv("FLINK_JOB_MANAGER", "localhost"),
    "job_manager_port": 8081,
    "parallelism": 4,
    "checkpoint_interval": 60000,
    "checkpoint_mode": "EXACTLY_ONCE",
    "state_backend": "filesystem",
    "state_backend_path": "file:///tmp/flink-state",
}

MODEL_CONFIG = {
    "isolation_forest_path": os.path.join(BASE_DIR, "models", "saved", "isolation_forest.joblib"),
    "autoencoder_path": os.path.join(BASE_DIR, "models", "saved", "autoencoder_model"),
    "scaler_path": os.path.join(BASE_DIR, "models", "saved", "scaler.joblib"),
    "threshold_path": os.path.join(BASE_DIR, "models", "saved", "thresholds.joblib"),
    "if_n_estimators": 100,
    "if_max_samples": "auto",
    "if_dynamic_quantile": 5,
    "if_min_user_samples": 20,
    "if_max_user_buffer": 500,
    "ae_input_dim": 30,
    "ae_hidden_dims": [16, 8, 4],
    "ae_learning_rate": 0.001,
    "ae_batch_size": 256,
    "ae_epochs": 50,
    "ae_early_stopping_patience": 5,
    "ae_min_user_samples": 10,
    "ae_max_user_buffer": 200,
    "ae_adapter_dim": 4,
    "ae_finetune_lr": 0.001,
    "ae_finetune_epochs": 3,
}

FRAUD_THRESHOLDS = {
    "high_risk_probability": 0.85,
    "medium_risk_probability": 0.60,
    "low_risk_probability": 0.30,
    "isolation_forest_anomaly_threshold": -0.5,
    "autoencoder_reconstruction_threshold": 2.5,
    "combined_fraud_threshold": 0.70,
}

RULE_ENGINE_CONFIG = {
    "amount_threshold_high": 10000.0,
    "amount_threshold_medium": 5000.0,
    "transaction_frequency_window_seconds": 3600,
    "transaction_frequency_threshold": 10,
    "geo_distance_threshold_km": 500,
    "new_merchant_risk_multiplier": 1.5,
    "odd_hours_start": 0,
    "odd_hours_end": 5,
    "velocity_check_window_seconds": 300,
    "velocity_check_amount_threshold": 5000,
}

ALERT_CONFIG = {
    "alert_levels": ["CRITICAL", "WARNING", "INFO"],
    "critical_actions": ["BLOCK"],
    "warning_actions": ["VERIFY", "HOLD"],
    "info_actions": ["ALLOW", "MONITOR"],
    "alert_cooldown_seconds": 60,
    "max_alerts_per_minute": 30,
    "webhook_url": os.getenv("ALERT_WEBHOOK_URL", ""),
    "sms_notification": os.getenv("SMS_NOTIFICATION", "false").lower() == "true",
    "email_notification": os.getenv("EMAIL_NOTIFICATION", "false").lower() == "true",
}

DISPOSITION_CONFIG = {
    "block_threshold": 0.85,
    "sms_verify_threshold": 0.60,
    "monitor_threshold": 0.30,
    "auto_block_rules": [
        "amount_exceeds_high",
        "geo_anomaly",
        "velocity_anomaly",
    ],
    "auto_sms_verify_rules": [
        "new_merchant",
        "odd_hours",
        "frequency_exceeds",
        "amount_exceeds_medium",
        "cross_border",
        "high_risk_category",
    ],
}

TRANSACTION_SIMULATION = {
    "normal_transaction_probability": 0.95,
    "fraud_transaction_probability": 0.05,
    "min_amount": 1.0,
    "max_normal_amount": 5000.0,
    "max_fraud_amount": 20000.0,
    "transaction_interval_ms": 100,
    "total_transactions": 100000,
}

LOGGING_CONFIG = {
    "log_level": "INFO",
    "log_format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    "log_file": os.path.join(BASE_DIR, "logs", "fraud_detection.log"),
    "max_log_size_mb": 100,
    "backup_count": 5,
}

NETWORK_ANALYSIS_CONFIG = {
    "min_ring_size": 2,
    "risk_multiplier_per_ring": 0.3,
    "risk_multiplier_per_connection": 0.05,
    "max_shared_entities": 20,
    "analysis_interval_seconds": 300,
}

EXPLAINABILITY_CONFIG = {
    "top_k_drivers": 5,
    "top_k_mitigators": 5,
    "loco_perturbation_count": 1,
    "include_all_contributions": True,
}

ONLINE_LEARNING_CONFIG = {
    "max_buffer_size": 1000,
    "min_samples_for_update": 50,
    "update_interval_seconds": 300,
    "learning_rate_decay": 0.95,
    "fraud_weight_boost": 5.0,
    "auto_save_after_update": True,
}
