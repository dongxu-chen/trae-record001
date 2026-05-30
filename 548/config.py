from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class ResourceConfig:
    name: str
    unit: str
    warning_threshold: float
    critical_threshold: float
    max_capacity: float = 100.0


@dataclass
class AppConfig:
    resources: Dict[str, ResourceConfig] = field(default_factory=lambda: {
        "cpu": ResourceConfig(
            name="CPU使用率",
            unit="%",
            warning_threshold=70.0,
            critical_threshold=85.0,
            max_capacity=100.0
        ),
        "memory": ResourceConfig(
            name="内存使用率",
            unit="%",
            warning_threshold=75.0,
            critical_threshold=90.0,
            max_capacity=100.0
        ),
        "disk": ResourceConfig(
            name="磁盘使用率",
            unit="%",
            warning_threshold=80.0,
            critical_threshold=95.0,
            max_capacity=100.0
        )
    })

    prediction_hours: int = 24
    historical_days: int = 30
    data_frequency_minutes: int = 5

    anomaly_confidence: float = 0.95
    anomaly_iqr_multiplier: float = 3.0

    weekly_seasonality: bool = True
    daily_seasonality: bool = True
    yearly_seasonality: bool = False

    changepoint_prior_scale: float = 0.05
    seasonality_prior_scale: float = 10.0

    sliding_window_hours: int = 168
    sliding_window_step_hours: int = 24
    sliding_window_min_periods: int = 3
    pattern_change_sensitivity: float = 0.15

    safety_buffer_percent: float = 20.0

    auto_scaling_enabled: bool = True
    auto_scaling_cooldown_minutes: int = 30
    auto_scaling_min_instances: int = 1
    auto_scaling_max_instances: int = 10
    auto_scaling_step_percent: float = 20.0
    auto_scaling_down_step_percent: float = 10.0

    idle_threshold_percent: float = 20.0
    idle_detection_hours: int = 72
    idle_downscale_suggestion_percent: float = 30.0

    cross_app_correlation_threshold: float = 0.6

    plotly_template: str = "plotly_white"
    color_palette: Dict[str, str] = field(default_factory=lambda: {
        "cpu": "#FF6B6B",
        "memory": "#4ECDC4",
        "disk": "#45B7D1",
        "warning": "#FFA500",
        "critical": "#FF0000",
        "normal": "#2ECC71",
        "prediction": "#9B59B6",
        "anomaly": "#E74C3C",
        "app1": "#3498DB",
        "app2": "#9B59B6",
        "app3": "#E67E22",
        "app4": "#1ABC9C",
        "app5": "#F39C12"
    })


config = AppConfig()
