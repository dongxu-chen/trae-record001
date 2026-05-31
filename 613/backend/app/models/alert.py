from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime


class AlertTag(BaseModel):
    key: str
    value: str


class Alert(BaseModel):
    id: str
    rule_name: str = Field(alias="ruleName")
    alarm_message: str = Field(alias="alarmMessage")
    scope: str
    service: str
    service_instance: Optional[str] = Field(None, alias="serviceInstance")
    endpoint_name: Optional[str] = Field(None, alias="endpointName")
    start_time: int = Field(alias="startTime")
    priority: str
    tags: List[AlertTag] = []

    class Config:
        populate_by_name = True


class AlertRule(BaseModel):
    id: int
    name: str
    metrics_name: str = Field(alias="metricsName")
    threshold: Any
    op: str
    period: int
    count: int
    silence_period: int = Field(alias="silencePeriod")
    message: str
    enabled: bool
    priority: str

    class Config:
        populate_by_name = True


class AlertCluster(BaseModel):
    cluster_id: str
    rule_name: str
    alert_count: int
    services: List[str]
    time_span: Dict[str, int]
    priority_distribution: Dict[str, int]
    sample_alerts: List[Alert]
    pattern_features: Dict[str, Any]


class InefficientRule(BaseModel):
    rule_name: str
    total_alerts: int
    frequency_score: float
    criticality_score: float
    noise_score: float
    inefficiency_score: float
    recommendation: str
    severity: str
    metrics_data: Dict[str, Any]


class OptimizationSuggestion(BaseModel):
    rule_name: str
    original_config: Dict[str, Any]
    suggested_config: Dict[str, Any]
    expected_improvement: Dict[str, Any]
    confidence: float
    reasoning: str


class EvaluationResult(BaseModel):
    metric_name: str
    original_value: float
    optimized_value: float
    improvement_percent: float


class RuleOptimizationResult(BaseModel):
    rule_name: str
    optimization_applied: bool
    original_config: Dict[str, Any]
    optimized_config: Dict[str, Any]
    evaluation: List[EvaluationResult]
    simulation_results: Dict[str, Any]


class AnalysisReport(BaseModel):
    analysis_period: Dict[str, int]
    total_alerts: int
    unique_rules: int
    clusters: List[AlertCluster]
    inefficient_rules: List[InefficientRule]
    optimization_suggestions: List[OptimizationSuggestion]
    overall_summary: Dict[str, Any]
