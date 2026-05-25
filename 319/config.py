import os
from dataclasses import dataclass, field
from typing import Dict, List, Tuple


@dataclass
class RedisConfig:
    host: str = field(default_factory=lambda: os.getenv("REDIS_HOST", "localhost"))
    port: int = field(default_factory=lambda: int(os.getenv("REDIS_PORT", "6379")))
    db: int = field(default_factory=lambda: int(os.getenv("REDIS_DB", "0")))
    password: str = field(default_factory=lambda: os.getenv("REDIS_PASSWORD", ""))
    max_connections: int = 50
    socket_timeout: int = 5
    socket_connect_timeout: int = 5


@dataclass
class KafkaConfig:
    bootstrap_servers: str = field(
        default_factory=lambda: os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
    )
    bid_request_topic: str = "bid_requests"
    bid_response_topic: str = "bid_responses"
    impression_topic: str = "impressions"
    click_topic: str = "clicks"
    conversion_topic: str = "conversions"
    consumer_group_id: str = "rtb_consumer_group"
    auto_offset_reset: str = "latest"
    enable_auto_commit: bool = True


@dataclass
class ModelConfig:
    ctr_model_path: str = "models/ctr_xgboost.model"
    cvr_model_path: str = "models/cvr_xgboost.model"
    feature_dim: int = 50
    prediction_batch_size: int = 100
    use_gpu: bool = False


@dataclass
class BudgetConfig:
    total_budget: float = 10000.0
    daily_budget: float = 1000.0
    hourly_budget: float = field(default_factory=lambda: 1000.0 / 24)
    smooth_factor: float = 0.8
    emergency_threshold: float = 0.2
    pace_adjust_interval: int = 60
    min_bid: float = 0.01
    max_bid: float = 10.0
    pid_enabled: bool = True
    pid_kp_init: float = 1.0
    pid_ki_init: float = 0.1
    pid_kd_init: float = 0.05
    pid_adaptation_rate: float = 0.1


@dataclass
class FrequencyConfig:
    limits: Dict[str, Tuple[int, int]] = field(
        default_factory=lambda: {
            "1h": (3, 3600),
            "6h": (10, 21600),
            "24h": (20, 86400),
            "7d": (50, 604800),
        }
    )
    decay_factor: float = 0.7
    use_sliding_window: bool = True
    time_recovery_enabled: bool = True
    forecast_enabled: bool = True


@dataclass
class TrafficLayerConfig:
    layers: List[Dict] = field(
        default_factory=lambda: [
            {"name": "S", "min_ctr": 0.05, "bid_multiplier": 1.5, "budget_share": 0.4},
            {"name": "A", "min_ctr": 0.02, "bid_multiplier": 1.2, "budget_share": 0.3},
            {"name": "B", "min_ctr": 0.01, "bid_multiplier": 1.0, "budget_share": 0.2},
            {"name": "C", "min_ctr": 0.0, "bid_multiplier": 0.7, "budget_share": 0.1},
        ]
    )


@dataclass
class ExplorationConfig:
    enabled: bool = True
    strategy: str = "ucb"
    epsilon: float = 0.1
    epsilon_decay: float = 0.9995
    min_epsilon: float = 0.01
    ucb_c: float = 2.0
    boltzmann_temperature: float = 1.0
    min_trials_for_exploitation: int = 100
    exploration_budget_share: float = 0.1
    reward_click_weight: float = 1.0
    reward_conversion_weight: float = 5.0
    reward_cost_penalty: float = 0.1


@dataclass
class SimulatorConfig:
    num_auctions: int = 1000
    min_bid: float = 0.01
    max_bid: float = 10.0
    num_competitors: int = 5
    competitor_bid_std: float = 0.5
    click_probability_base: float = 0.02
    conversion_probability_base: float = 0.005
    reserve_price: float = 0.01
    random_seed: int = 42


@dataclass
class AutoTunerConfig:
    enabled: bool = True
    n_trials: int = 50
    timeout: int = 300
    direction: str = "maximize"
    metric: str = "total_profit"
    study_name: str = "rtb_bid_optimization"
    save_best_params: bool = True


@dataclass
class SystemConfig:
    redis: RedisConfig = field(default_factory=RedisConfig)
    kafka: KafkaConfig = field(default_factory=KafkaConfig)
    model: ModelConfig = field(default_factory=ModelConfig)
    budget: BudgetConfig = field(default_factory=BudgetConfig)
    frequency: FrequencyConfig = field(default_factory=FrequencyConfig)
    traffic: TrafficLayerConfig = field(default_factory=TrafficLayerConfig)
    exploration: ExplorationConfig = field(default_factory=ExplorationConfig)
    simulator: SimulatorConfig = field(default_factory=SimulatorConfig)
    auto_tuner: AutoTunerConfig = field(default_factory=AutoTunerConfig)
    log_level: str = "INFO"
    service_port: int = 8000
    worker_count: int = 4


config = SystemConfig()
