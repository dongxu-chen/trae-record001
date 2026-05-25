import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import numpy as np

from .data_collector import MetricsData, PodResourceData
from .statistics_analyzer import ResourceStatistics, StatisticsAnalyzer

logger = logging.getLogger(__name__)


@dataclass
class VerticalResourceRecommendation:
    target_request: float
    lower_bound: float
    upper_bound: float
    target_limit: float
    uncapped_target: float
    confidence: float
    percentile_used: float
    safety_margin: float
    estimation_method: str
    container_name: str = ""
    base_percentile_value: float = 0.0
    oom_buffer_percent: float = 0.0
    oom_buffer_amount: float = 0.0


@dataclass
class PodVerticalRecommendation:
    namespace: str
    pod: str
    cpu: VerticalResourceRecommendation
    memory: VerticalResourceRecommendation
    current_cpu_request: Optional[float] = None
    current_cpu_limit: Optional[float] = None
    current_memory_request: Optional[float] = None
    current_memory_limit: Optional[float] = None
    data_quality: str = "good"
    warnings: List[str] = field(default_factory=list)


DEFAULT_PERCENTILE_CONFIG = {
    "critical": {
        "cpu_percentile": 99.0,
        "memory_percentile": 99.0,
        "safety_margin_factor": 1.5,
    },
    "stateful": {
        "cpu_percentile": 90.0,
        "memory_percentile": 95.0,
        "safety_margin_factor": 1.3,
    },
    "stateless": {
        "cpu_percentile": 80.0,
        "memory_percentile": 90.0,
        "safety_margin_factor": 1.15,
    },
}


class VPARecommender:
    def __init__(
        self,
        analyzer: Optional[StatisticsAnalyzer] = None,
        recommendation_mode: str = "initial",
        percentile_config: Optional[Dict[str, Dict[str, float]]] = None,
        memory_oom_buffer_percent: float = 10.0,
        min_cpu_millicores: float = 10.0,
        min_memory_bytes: float = 10 * 1024 * 1024,
        limit_over_request_ratio: float = 1.5,
    ):
        self.analyzer = analyzer or StatisticsAnalyzer()
        self.recommendation_mode = recommendation_mode
        self.percentile_config = percentile_config or DEFAULT_PERCENTILE_CONFIG
        self.memory_oom_buffer_percent = memory_oom_buffer_percent
        self.min_cpu_millicores = min_cpu_millicores
        self.min_memory_bytes = min_memory_bytes
        self.limit_over_request_ratio = limit_over_request_ratio

    def recommend_for_pod(
        self,
        pod_data: PodResourceData,
        workload_type: str = "stateless",
        risk_tolerance: str = "medium",
    ) -> Optional[PodVerticalRecommendation]:
        logger.info(f"Generating VPA recommendation for pod {pod_data.namespace}/{pod_data.pod}")

        warnings = []
        data_quality = "good"

        if pod_data.cpu_usage.is_empty or pod_data.memory_usage.is_empty:
            logger.error(f"Insufficient usage data for pod {pod_data.pod}")
            return None

        if len(pod_data.cpu_usage.values) < 10:
            warnings.append("Limited CPU usage data, recommendation may be less accurate")
            data_quality = "medium"

        if len(pod_data.memory_usage.values) < 10:
            warnings.append("Limited memory usage data, recommendation may be less accurate")
            data_quality = "medium"

        if pod_data.cpu_usage.duration_hours < 1:
            warnings.append("CPU data duration < 1 hour, recommendation may be less accurate")
            data_quality = "medium" if data_quality == "good" else data_quality

        if pod_data.memory_usage.duration_hours < 1:
            warnings.append("Memory data duration < 1 hour, recommendation may be less accurate")
            data_quality = "medium" if data_quality == "good" else data_quality

        cpu_stats = self.analyzer.analyze(pod_data.cpu_usage, "cpu")
        memory_stats = self.analyzer.analyze(pod_data.memory_usage, "memory")

        if cpu_stats is None or memory_stats is None:
            logger.error(f"Failed to compute statistics for pod {pod_data.pod}")
            return None

        cpu_recommendation = self._compute_resource_recommendation(
            cpu_stats, "cpu", workload_type, risk_tolerance
        )
        memory_recommendation = self._compute_resource_recommendation(
            memory_stats, "memory", workload_type, risk_tolerance
        )

        cpu_recommendation = self._apply_minimums(cpu_recommendation, "cpu")
        memory_recommendation = self._apply_minimums(memory_recommendation, "memory")

        if self.recommendation_mode == "auto":
            cpu_recommendation = self._apply_smoothing(cpu_recommendation, pod_data.cpu_request)
            memory_recommendation = self._apply_smoothing(memory_recommendation, pod_data.memory_request)

        return PodVerticalRecommendation(
            namespace=pod_data.namespace,
            pod=pod_data.pod,
            cpu=cpu_recommendation,
            memory=memory_recommendation,
            current_cpu_request=pod_data.cpu_request,
            current_cpu_limit=pod_data.cpu_limit,
            current_memory_request=pod_data.memory_request,
            current_memory_limit=pod_data.memory_limit,
            data_quality=data_quality,
            warnings=warnings,
        )

    def _get_percentile_for_workload(self, workload_type: str, resource_type: str) -> float:
        config = self.percentile_config.get(workload_type, self.percentile_config["stateless"])
        if resource_type == "cpu":
            return config.get("cpu_percentile", 85.0)
        else:
            return config.get("memory_percentile", 95.0)

    def _get_safety_margin_for_workload(self, workload_type: str) -> float:
        config = self.percentile_config.get(workload_type, self.percentile_config["stateless"])
        return config.get("safety_margin_factor", 1.15)

    def _compute_resource_recommendation(
        self,
        stats: ResourceStatistics,
        resource_type: str,
        workload_type: str,
        risk_tolerance: str,
    ) -> VerticalResourceRecommendation:
        percentile = self._get_percentile_for_workload(workload_type, resource_type)
        base_safety_margin = self._get_safety_margin_for_workload(workload_type)

        base_value = self._get_percentile_value(stats, percentile)
        peak_value = self._get_percentile_value(stats, 99.5)

        safety_margin = self.analyzer.get_safety_margin(stats, workload_type, risk_tolerance)
        safety_margin = max(safety_margin, base_safety_margin)

        target_request = base_value * safety_margin
        uncapped_target = target_request

        oom_buffer_percent = 0.0
        oom_buffer_amount = 0.0
        if resource_type == "memory" and self.memory_oom_buffer_percent > 0:
            oom_buffer_percent = self.memory_oom_buffer_percent
            oom_buffer_amount = target_request * (oom_buffer_percent / 100.0)
            target_request = target_request + oom_buffer_amount

        ci_lower = stats.ci_95.lower * safety_margin
        ci_upper = stats.ci_95.upper * safety_margin
        if resource_type == "memory" and oom_buffer_amount > 0:
            ci_lower = ci_lower + oom_buffer_amount
            ci_upper = ci_upper + oom_buffer_amount

        lower_bound = min(target_request * 0.8, ci_lower)
        upper_bound = max(peak_value * safety_margin * 0.9, ci_upper)
        if resource_type == "memory" and oom_buffer_amount > 0:
            upper_bound = max(upper_bound, target_request * 1.1)

        target_limit = target_request * self.limit_over_request_ratio

        confidence = self._calculate_confidence(stats, resource_type)

        estimation_method = self._select_estimation_method(stats, resource_type)

        return VerticalResourceRecommendation(
            target_request=target_request,
            lower_bound=lower_bound,
            upper_bound=upper_bound,
            target_limit=target_limit,
            uncapped_target=uncapped_target,
            confidence=confidence,
            percentile_used=percentile,
            safety_margin=safety_margin,
            estimation_method=estimation_method,
            base_percentile_value=base_value,
            oom_buffer_percent=oom_buffer_percent,
            oom_buffer_amount=oom_buffer_amount,
        )

    def _get_percentile_value(self, stats: ResourceStatistics, percentile: float) -> float:
        key = str(int(percentile)) if percentile == int(percentile) else str(percentile)
        if key in stats.percentiles:
            return stats.percentiles[key]

        sorted_percentiles = sorted([float(k) for k in stats.percentiles.keys()])

        lower_p = None
        upper_p = None
        for p in sorted_percentiles:
            if p <= percentile:
                lower_p = p
            if p >= percentile and upper_p is None:
                upper_p = p
                break

        def _get_key(p: float) -> str:
            return str(int(p)) if p == int(p) else str(p)

        if lower_p is not None and upper_p is not None and upper_p != lower_p:
            lower_val = stats.percentiles[_get_key(lower_p)]
            upper_val = stats.percentiles[_get_key(upper_p)]
            ratio = (percentile - lower_p) / (upper_p - lower_p)
            return lower_val + ratio * (upper_val - lower_val)
        elif lower_p is not None:
            return stats.percentiles[_get_key(lower_p)]
        elif upper_p is not None:
            return stats.percentiles[_get_key(upper_p)]
        else:
            return stats.p95 if percentile > 90 else stats.p50

    def _calculate_confidence(self, stats: ResourceStatistics, resource_type: str) -> float:
        if stats.data_points < 10 or stats.duration_hours < 0.5:
            return 0.3

        data_points_score = min(1.0, stats.data_points / 100.0)
        duration_score = min(1.0, stats.duration_hours / 24.0)
        ci_score = max(0.0, 1.0 - (stats.ci_95.margin_of_error / max(stats.mean, 1e-9)))
        stability_score = max(0.0, 1.0 - min(stats.cv, 1.0))

        weights = [0.25, 0.25, 0.25, 0.25]
        scores = [data_points_score, duration_score, ci_score, stability_score]

        confidence = sum(w * s for w, s in zip(weights, scores))

        if resource_type == "memory":
            confidence = min(1.0, confidence * 1.1)

        return float(max(0.1, min(1.0, confidence)))

    def _select_estimation_method(self, stats: ResourceStatistics, resource_type: str) -> str:
        if stats.skewness > 2.0 or stats.kurtosis > 5.0:
            return "percentile_with_peak_handling"
        elif stats.cv > 0.5:
            return "high_variance_adjusted"
        elif stats.duration_hours < 1:
            return "short_window_conservative"
        elif resource_type == "memory":
            return "memory_peak_focused"
        else:
            return "standard_percentile"

    def _apply_minimums(
        self, recommendation: VerticalResourceRecommendation, resource_type: str
    ) -> VerticalResourceRecommendation:
        if resource_type == "cpu":
            min_value = self.min_cpu_millicores / 1000.0
        else:
            min_value = self.min_memory_bytes

        if recommendation.target_request < min_value:
            recommendation.target_request = min_value
            recommendation.lower_bound = min_value * 0.8
            recommendation.upper_bound = min(recommendation.upper_bound, min_value * 2.0)
            recommendation.target_limit = min(recommendation.target_limit, min_value * self.limit_over_request_ratio)

        return recommendation

    def _apply_smoothing(
        self, recommendation: VerticalResourceRecommendation, current_value: Optional[float]
    ) -> VerticalResourceRecommendation:
        if current_value is None or current_value <= 0:
            return recommendation

        change_ratio = recommendation.target_request / current_value

        if 0.9 <= change_ratio <= 1.1:
            recommendation.target_request = current_value
        elif change_ratio > 1.1:
            recommendation.target_request = current_value + (recommendation.target_request - current_value) * 0.7
        elif change_ratio < 0.9:
            recommendation.target_request = current_value + (recommendation.target_request - current_value) * 0.5

        return recommendation

    def calculate_change_impact(
        self,
        recommendation: PodVerticalRecommendation,
    ) -> Dict:
        impact = {
            "cpu": {},
            "memory": {},
        }

        if recommendation.current_cpu_request and recommendation.current_cpu_request > 0:
            cpu_change = (recommendation.cpu.target_request - recommendation.current_cpu_request) / recommendation.current_cpu_request
            impact["cpu"]["request_change_percent"] = cpu_change * 100
            impact["cpu"]["request_change_direction"] = "increase" if cpu_change > 0 else "decrease"
            impact["cpu"]["request_change_amount"] = recommendation.cpu.target_request - recommendation.current_cpu_request

        if recommendation.current_cpu_limit and recommendation.current_cpu_limit > 0:
            cpu_limit_change = (recommendation.cpu.target_limit - recommendation.current_cpu_limit) / recommendation.current_cpu_limit
            impact["cpu"]["limit_change_percent"] = cpu_limit_change * 100

        if recommendation.current_memory_request and recommendation.current_memory_request > 0:
            memory_change = (recommendation.memory.target_request - recommendation.current_memory_request) / recommendation.current_memory_request
            impact["memory"]["request_change_percent"] = memory_change * 100
            impact["memory"]["request_change_direction"] = "increase" if memory_change > 0 else "decrease"
            impact["memory"]["request_change_amount"] = recommendation.memory.target_request - recommendation.current_memory_request

        if recommendation.current_memory_limit and recommendation.current_memory_limit > 0:
            memory_limit_change = (recommendation.memory.target_limit - recommendation.current_memory_limit) / recommendation.current_memory_limit
            impact["memory"]["limit_change_percent"] = memory_limit_change * 100

        return impact
