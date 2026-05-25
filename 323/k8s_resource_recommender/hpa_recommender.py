import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import numpy as np

from .data_collector import DeploymentResourceData
from .statistics_analyzer import ResourceStatistics, StatisticsAnalyzer

logger = logging.getLogger(__name__)


@dataclass
class HorizontalResourceRecommendation:
    target_replicas: int
    min_replicas: int
    max_replicas: int
    lower_bound: int
    upper_bound: int
    cpu_utilization_target: float
    memory_utilization_target: float
    current_replicas: int
    confidence: float
    driving_resource: str
    utilization_based_on: str
    reasoning: List[str] = field(default_factory=list)


@dataclass
class DeploymentHorizontalRecommendation:
    namespace: str
    deployment: str
    recommendation: HorizontalResourceRecommendation
    cpu_statistics: Optional[ResourceStatistics] = None
    memory_statistics: Optional[ResourceStatistics] = None
    current_replicas_history: Optional[List[int]] = None
    warnings: List[str] = field(default_factory=list)


class HPARecommender:
    def __init__(
        self,
        analyzer: Optional[StatisticsAnalyzer] = None,
        cpu_target_utilization: float = 70.0,
        memory_target_utilization: float = 75.0,
        min_replicas: int = 1,
        max_replicas: int = 10,
        scale_down_stabilization_window_minutes: int = 5,
        scale_up_stabilization_window_minutes: int = 3,
        tolerance: float = 0.1,
    ):
        self.analyzer = analyzer or StatisticsAnalyzer()
        self.cpu_target_utilization = cpu_target_utilization
        self.memory_target_utilization = memory_target_utilization
        self.min_replicas = min_replicas
        self.max_replicas = max_replicas
        self.scale_down_stabilization_window_minutes = scale_down_stabilization_window_minutes
        self.scale_up_stabilization_window_minutes = scale_up_stabilization_window_minutes
        self.tolerance = tolerance

    def recommend_for_deployment(
        self,
        deployment_data: DeploymentResourceData,
        cpu_request_per_pod: float,
        memory_request_per_pod: float,
        current_replicas: Optional[int] = None,
        workload_type: str = "stateless",
        risk_tolerance: str = "medium",
    ) -> Optional[DeploymentHorizontalRecommendation]:
        logger.info(
            f"Generating HPA recommendation for deployment {deployment_data.namespace}/{deployment_data.deployment}"
        )

        warnings = []

        if not deployment_data.pods:
            warnings.append(
                "No pod data available for deployment, recommendation based on aggregated metrics only"
            )

        if deployment_data.aggregated_cpu.is_empty and deployment_data.aggregated_memory.is_empty:
            logger.error(
                f"No usage data available for deployment {deployment_data.deployment}"
            )
            return None

        if cpu_request_per_pod <= 0 or memory_request_per_pod <= 0:
            logger.error("Invalid resource requests per pod")
            return None

        cpu_replicas = None
        memory_replicas = None
        cpu_stats = None
        memory_stats = None

        if not deployment_data.aggregated_cpu.is_empty:
            cpu_stats = self.analyzer.analyze(deployment_data.aggregated_cpu, "cpu")
            if cpu_stats:
                cpu_replicas = self._calculate_replicas_by_utilization(
                    cpu_stats,
                    cpu_request_per_pod,
                    self.cpu_target_utilization,
                    "cpu",
                )

        if not deployment_data.aggregated_memory.is_empty:
            memory_stats = self.analyzer.analyze(deployment_data.aggregated_memory, "memory")
            if memory_stats:
                memory_replicas = self._calculate_replicas_by_utilization(
                    memory_stats,
                    memory_request_per_pod,
                    self.memory_target_utilization,
                    "memory",
                )

        if cpu_replicas is None and memory_replicas is None:
            logger.error("Failed to calculate replicas for both CPU and memory")
            return None

        current_replicas = current_replicas or self._get_current_replicas(deployment_data)

        recommendation = self._combine_recommendations(
            cpu_replicas,
            memory_replicas,
            current_replicas,
            deployment_data,
            cpu_stats,
            memory_stats,
            workload_type,
            risk_tolerance,
        )

        recommendation.reasoning = self._generate_reasoning(
            recommendation,
            cpu_replicas,
            memory_replicas,
            cpu_stats,
            memory_stats,
            current_replicas,
        )

        return DeploymentHorizontalRecommendation(
            namespace=deployment_data.namespace,
            deployment=deployment_data.deployment,
            recommendation=recommendation,
            cpu_statistics=cpu_stats,
            memory_statistics=memory_stats,
            warnings=warnings,
        )

    def _calculate_replicas_by_utilization(
        self,
        stats: ResourceStatistics,
        request_per_pod: float,
        target_utilization_percent: float,
        resource_type: str,
    ) -> Dict:
        target_utilization = target_utilization_percent / 100.0

        p90_usage = stats.p90
        p95_usage = stats.p95
        p99_usage = stats.p99

        avg_usage = stats.mean

        replicas_by_avg = np.ceil(avg_usage / (request_per_pod * target_utilization))
        replicas_by_p90 = np.ceil(p90_usage / (request_per_pod * target_utilization))
        replicas_by_p95 = np.ceil(p95_usage / (request_per_pod * target_utilization))
        replicas_by_p99 = np.ceil(p99_usage / (request_per_pod * target_utilization))

        ci_lower_usage = stats.ci_95.lower
        ci_upper_usage = stats.ci_95.upper

        replicas_by_ci_lower = max(
            1, int(np.ceil(ci_lower_usage / (request_per_pod * target_utilization)))
        )
        replicas_by_ci_upper = int(
            np.ceil(ci_upper_usage / (request_per_pod * target_utilization))
        )

        base_replicas = max(
            replicas_by_avg,
            replicas_by_p90 * 0.6 + replicas_by_p95 * 0.3 + replicas_by_p99 * 0.1,
        )

        cv = stats.cv
        if cv > 0.5:
            base_replicas = max(base_replicas, replicas_by_p95)
        if cv > 1.0:
            base_replicas = max(base_replicas, replicas_by_p99)

        return {
            "base": int(np.ceil(base_replicas)),
            "conservative": int(np.ceil(replicas_by_p99)),
            "aggressive": int(np.ceil(replicas_by_avg)),
            "ci_lower": replicas_by_ci_lower,
            "ci_upper": replicas_by_ci_upper,
            "avg_usage": avg_usage,
            "p95_usage": p95_usage,
            "utilization_percent": (avg_usage / request_per_pod) * 100,
            "current_peak_usage_percent": (stats.max / request_per_pod) * 100,
        }

    def _combine_recommendations(
        self,
        cpu_replicas: Optional[Dict],
        memory_replicas: Optional[Dict],
        current_replicas: int,
        deployment_data: DeploymentResourceData,
        cpu_stats: Optional[ResourceStatistics],
        memory_stats: Optional[ResourceStatistics],
        workload_type: str,
        risk_tolerance: str,
    ) -> HorizontalResourceRecommendation:
        if cpu_replicas and memory_replicas:
            if cpu_replicas["base"] >= memory_replicas["base"]:
                base_replicas = cpu_replicas["base"]
                driving_resource = "cpu"
            else:
                base_replicas = memory_replicas["base"]
                driving_resource = "memory"

            lower_bound = max(cpu_replicas["ci_lower"], memory_replicas["ci_lower"])
            upper_bound = max(cpu_replicas["ci_upper"], memory_replicas["ci_upper"])
            conservative_replicas = max(
                cpu_replicas["conservative"], memory_replicas["conservative"]
            )

            current_cpu_utilization = cpu_replicas["utilization_percent"]
            current_memory_utilization = memory_replicas["utilization_percent"]

        elif cpu_replicas:
            base_replicas = cpu_replicas["base"]
            driving_resource = "cpu"
            lower_bound = cpu_replicas["ci_lower"]
            upper_bound = cpu_replicas["ci_upper"]
            conservative_replicas = cpu_replicas["conservative"]
            current_cpu_utilization = cpu_replicas["utilization_percent"]
            current_memory_utilization = 0

        else:
            base_replicas = memory_replicas["base"]
            driving_resource = "memory"
            lower_bound = memory_replicas["ci_lower"]
            upper_bound = memory_replicas["ci_upper"]
            conservative_replicas = memory_replicas["conservative"]
            current_cpu_utilization = 0
            current_memory_utilization = memory_replicas["utilization_percent"]

        risk_factors = {
            "low": {"stateless": 1.0, "stateful": 1.0, "critical": 1.0},
            "medium": {"stateless": 1.1, "stateful": 1.15, "critical": 1.2},
            "high": {"stateless": 1.2, "stateful": 1.3, "critical": 1.5},
        }

        risk_factor = risk_factors.get(risk_tolerance, {}).get(workload_type, 1.1)

        target_replicas = int(np.ceil(base_replicas * risk_factor))
        target_replicas = self._apply_stabilization(
            target_replicas, current_replicas, deployment_data
        )

        target_replicas = max(self.min_replicas, min(target_replicas, self.max_replicas))
        min_replicas = max(self.min_replicas, min(lower_bound, self.min_replicas))
        max_replicas = min(
            self.max_replicas, max(upper_bound, conservative_replicas)
        )

        confidence = self._calculate_hpa_confidence(
            cpu_stats, memory_stats, deployment_data
        )

        utilization_based_on = []
        if cpu_replicas and memory_replicas:
            utilization_based_on = "both"
        elif cpu_replicas:
            utilization_based_on = "cpu_only"
        else:
            utilization_based_on = "memory_only"

        return HorizontalResourceRecommendation(
            target_replicas=target_replicas,
            min_replicas=min_replicas,
            max_replicas=max_replicas,
            lower_bound=lower_bound,
            upper_bound=upper_bound,
            cpu_utilization_target=self.cpu_target_utilization,
            memory_utilization_target=self.memory_target_utilization,
            current_replicas=current_replicas,
            confidence=confidence,
            driving_resource=driving_resource,
            utilization_based_on=utilization_based_on,
        )

    def _apply_stabilization(
        self,
        target_replicas: int,
        current_replicas: int,
        deployment_data: DeploymentResourceData,
    ) -> int:
        if not deployment_data.replicas_history.is_empty:
            replicas_values = deployment_data.replicas_history.values
            if len(replicas_values) >= 5:
                recent_max = int(np.max(replicas_values[-10:]))
                recent_min = int(np.min(replicas_values[-10:]))

                if target_replicas < current_replicas:
                    if target_replicas < recent_min * (1 - self.tolerance):
                        target_replicas = int(
                            max(target_replicas, int(recent_min * (1 - self.tolerance)))
                        )
                elif target_replicas > current_replicas:
                    if target_replicas > recent_max * (1 + self.tolerance):
                        target_replicas = int(
                            min(target_replicas, int(recent_max * (1 + self.tolerance)))
                        )

        return target_replicas

    def _calculate_hpa_confidence(
        self,
        cpu_stats: Optional[ResourceStatistics],
        memory_stats: Optional[ResourceStatistics],
        deployment_data: DeploymentResourceData,
    ) -> float:
        scores = []

        if cpu_stats:
            cpu_confidence = min(1.0, cpu_stats.data_points / 100.0)
            scores.append(cpu_confidence)

        if memory_stats:
            memory_confidence = min(1.0, memory_stats.data_points / 100.0)
            scores.append(memory_confidence)

        if deployment_data.pods:
            pod_count_score = min(1.0, len(deployment_data.pods) / 5.0)
            scores.append(pod_count_score)

        if not deployment_data.replicas_history.is_empty:
            history_score = min(1.0, len(deployment_data.replicas_history.values) / 50.0)
            scores.append(history_score)

        if scores:
            return float(np.mean(scores))
        return 0.3

    def _get_current_replicas(self, deployment_data: DeploymentResourceData) -> int:
        if not deployment_data.replicas_history.is_empty:
            return int(deployment_data.replicas_history.values[-1])
        if deployment_data.pods:
            return len(deployment_data.pods)
        return self.min_replicas

    def _generate_reasoning(
        self,
        recommendation: HorizontalResourceRecommendation,
        cpu_replicas: Optional[Dict],
        memory_replicas: Optional[Dict],
        cpu_stats: Optional[ResourceStatistics],
        memory_stats: Optional[ResourceStatistics],
        current_replicas: int,
    ) -> List[str]:
        reasoning = []

        if cpu_replicas:
            reasoning.append(
                f"CPU: 当前平均利用率 {cpu_replicas['utilization_percent']:.1f}%, "
                f"推荐基于P95数据需 {cpu_replicas['base']} 副本"
            )

        if memory_replicas:
            reasoning.append(
                f"Memory: 当前平均利用率 {memory_replicas['utilization_percent']:.1f}%, "
                f"推荐基于P95数据需 {memory_replicas['base']} 副本"
            )

        if recommendation.driving_resource:
            reasoning.append(
                f"主要驱动资源: {recommendation.driving_resource.upper()}"
            )

        change = recommendation.target_replicas - current_replicas
        if change > 0:
            reasoning.append(
                f"建议扩容: 当前 {current_replicas} -> {recommendation.target_replicas} (+{change})")
        elif change < 0:
            reasoning.append(
                f"建议缩容: 当前 {current_replicas} -> {recommendation.target_replicas} ({change})")
        else:
            reasoning.append("当前副本数已处于合理范围，无需调整")

        reasoning.append(
            f"推荐置信度: {recommendation.confidence * 100:.0f}%"
        )

        return reasoning

    def calculate_horizontal_change_impact(
        self,
        recommendation: DeploymentHorizontalRecommendation,
        cpu_request_per_pod: float,
        memory_request_per_pod: float,
    ) -> Dict:
        rec = recommendation.recommendation
        current_replicas = rec.current_replicas
        target_replicas = rec.target_replicas

        current_cpu_total = current_replicas * cpu_request_per_pod
        target_cpu_total = target_replicas * cpu_request_per_pod
        current_memory_total = current_replicas * memory_request_per_pod
        target_memory_total = target_replicas * memory_request_per_pod

        change_replicas = target_replicas - current_replicas
        change_percent = (change_replicas / current_replicas * 100) if current_replicas > 0 else 0

        return {
            "replicas_change": change_replicas,
            "replicas_change_percent": change_percent,
            "current_cpu_total": current_cpu_total,
            "target_cpu_total": target_cpu_total,
            "cpu_change": target_cpu_total - current_cpu_total,
            "current_memory_total": current_memory_total,
            "target_memory_total": target_memory_total,
            "memory_change": target_memory_total - current_memory_total,
        }
