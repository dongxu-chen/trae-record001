from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class CircuitState(str, Enum):
    CLOSED = "CLOSED"
    OPEN = "OPEN"
    HALF_OPEN = "HALF_OPEN"


class MetricData(BaseModel):
    timestamp: datetime = Field(default_factory=datetime.now)
    endpoint: str
    success_count: int = 0
    failure_count: int = 0
    total_requests: int = 0
    avg_latency: float = 0.0
    p50_latency: float = 0.0
    p95_latency: float = 0.0
    p99_latency: float = 0.0
    error_rate: float = 0.0
    throughput: float = 0.0


class CircuitBreakerConfig(BaseModel):
    timeout: float = Field(default=3.0, ge=0.1, le=30.0, description="超时时间（秒）")
    failure_threshold: float = Field(default=0.5, ge=0.1, le=1.0, description="失败率阈值")
    half_open_window: float = Field(default=10.0, ge=1.0, le=120.0, description="半开探测窗口（秒）")
    min_requests: int = Field(default=5, ge=1, le=100, description="触发熔断的最小请求数")
    open_duration: float = Field(default=30.0, ge=5.0, le=300.0, description="熔断持续时间（秒）")


class OptimizationResult(BaseModel):
    best_config: CircuitBreakerConfig
    best_score: float
    all_results: List[Dict[str, Any]]
    optimization_history: List[Dict[str, Any]]
    metrics_summary: Dict[str, Any]
    parameter_explanations: Dict[str, Dict[str, Any]] = {}


class RetryStormParams(BaseModel):
    enabled: bool = Field(default=False, description="是否启用重试风暴模拟")
    max_retries: int = Field(default=3, ge=1, le=10, description="最大重试次数")
    retry_delay_base: float = Field(default=0.1, ge=0.01, le=2.0, description="重试延迟基数（秒）")
    retry_backoff_multiplier: float = Field(default=2.0, ge=1.0, le=5.0, description="重试退避乘数")
    retry_jitter: float = Field(default=0.1, ge=0.0, le=0.5, description="重试抖动比例")
    retry_storm_trigger_threshold: float = Field(default=0.3, ge=0.1, le=0.8, description="触发重试风暴的错误率阈值")
    retry_amplification_factor: float = Field(default=3.0, ge=1.0, le=10.0, description="重试风暴流量放大倍数")


class SimulationParams(BaseModel):
    duration: float = Field(default=300.0, ge=60.0, le=3600.0, description="模拟时长（秒）")
    base_error_rate: float = Field(default=0.05, ge=0.0, le=1.0, description="基础错误率")
    base_latency: float = Field(default=0.2, ge=0.01, le=5.0, description="基础延迟（秒）")
    traffic_pattern: str = Field(default="steady", description="流量模式: steady, spike, periodic")
    traffic_multiplier: float = Field(default=1.0, ge=0.1, le=10.0, description="流量乘数")
    failure_spike_times: Optional[List[float]] = None
    retry_storm: RetryStormParams = Field(default_factory=RetryStormParams)


class ConfigPushResult(BaseModel):
    status: str
    endpoint: str
    old_config: Optional[Dict[str, Any]] = None
    new_config: Dict[str, Any]
    pushed_at: datetime = Field(default_factory=datetime.now)
    version: str = ""


class FaultInjectionParams(BaseModel):
    endpoint: str
    injection_type: str = Field(default="error", description="注入类型: error, latency, traffic")
    intensity: float = Field(default=0.5, ge=0.0, le=1.0, description="注入强度")
    duration: float = Field(default=30.0, ge=1.0, le=300.0, description="注入持续时间（秒）")
    start_delay: float = Field(default=5.0, ge=0.0, le=60.0, description="开始前延迟（秒）")
    target_latency: Optional[float] = None


class FaultInjectionResult(BaseModel):
    status: str
    task_id: str
    endpoint: str
    injection_type: str
    intensity: float
    duration: float
    events_before: List[Dict[str, Any]] = []
    events_during: List[Dict[str, Any]] = []
    events_after: List[Dict[str, Any]] = []
    circuit_breaker_triggered: bool = False
    trigger_time: Optional[float] = None
    recovery_time: Optional[float] = None
    success_rate_before: float = 0.0
    success_rate_during: float = 0.0
    success_rate_after: float = 0.0


class CircuitBreakerEvent(BaseModel):
    timestamp: datetime = Field(default_factory=datetime.now)
    endpoint: str
    event_type: str = Field(description="事件类型: state_change, reject, timeout, error")
    old_state: Optional[str] = None
    new_state: Optional[str] = None
    details: Dict[str, Any] = {}


class FalseTripAnalysis(BaseModel):
    endpoint: str
    event_count: int
    potential_false_trips: int
    false_trip_rate: float
    avg_time_between_trips: float
    min_requests_before_trip: int
    avg_error_rate_before_trip: float
    recommendations: List[str] = []


class EventAnalysisResult(BaseModel):
    endpoint: str
    total_events: int
    state_changes: int
    open_events: List[Dict[str, Any]]
    reject_events: List[Dict[str, Any]]
    false_trip_analysis: FalseTripAnalysis
    recommendations: List[str] = []


class ConfigHistory(BaseModel):
    endpoint: str
    configs: List[Dict[str, Any]] = []
    timestamps: List[datetime] = []
    versions: List[str] = []
