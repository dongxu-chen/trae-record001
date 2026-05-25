import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from enum import Enum

import numpy as np

from .data_collector import MetricsData, PodResourceData, DeploymentResourceData
from .statistics_analyzer import ResourceStatistics, StatisticsAnalyzer
from .vpa_recommender import PodVerticalRecommendation, VerticalResourceRecommendation
from .hpa_recommender import DeploymentHorizontalRecommendation
from .cost_estimator import CostEstimator, VerticalCostAnalysis, HorizontalCostAnalysis

logger = logging.getLogger(__name__)


class SimulationStatus(str, Enum):
    SUCCESS = "success"
    WARNING = "warning"
    FAILURE = "failure"


@dataclass
class ResourceEvent:
    timestamp: float
    resource_type: str
    event_type: str
    value: float
    threshold: float
    description: str


@dataclass
class SimulationMetric:
    name: str
    current_value: float
    simulated_value: float
    improvement: float
    unit: str = ""


@dataclass
class PodSimulationResult:
    pod: str
    namespace: str
    status: SimulationStatus
    cpu_evictions: int = 0
    memory_evictions: int = 0
    cpu_throttling_events: int = 0
    oom_events: int = 0
    p95_cpu_latency_impact: float = 0.0
    p99_memory_usage: float = 0.0
    max_cpu_usage: float = 0.0
    max_memory_usage: float = 0.0
    cost_analysis: Optional[VerticalCostAnalysis] = None
    events: List[ResourceEvent] = field(default_factory=list)
    metrics: List[SimulationMetric] = field(default_factory=list)
    risk_level: str = "low"
    summary: str = ""


@dataclass
class DeploymentSimulationResult:
    deployment: str
    namespace: str
    status: SimulationStatus
    pods: List[PodSimulationResult] = field(default_factory=list)
    total_evictions: int = 0
    total_oom_events: int = 0
    total_throttling_events: int = 0
    cost_savings_monthly: float = 0.0
    availability_impact: float = 0.0
    performance_impact: str = "neutral"
    recommendations: List[str] = field(default_factory=list)
    summary: str = ""

    @property
    def risk_level(self) -> str:
        if not self.pods:
            return "low"
        risk_order = {"low": 0, "medium": 1, "high": 2}
        max_risk = max((p.risk_level for p in self.pods), key=lambda x: risk_order.get(x, 0))
        return max_risk


@dataclass
class SimulationConfig:
    enable_throttling_simulation: bool = True
    enable_oom_simulation: bool = True
    enable_eviction_simulation: bool = True
    throttling_threshold: float = 0.9
    oom_threshold: float = 0.95
    eviction_threshold: float = 1.0
    safety_margin: float = 1.1
    simulation_duration_days: int = 7
    stress_scenario: str = "normal"


class RecommendationSimulator:
    def __init__(
        self,
        analyzer: Optional[StatisticsAnalyzer] = None,
        config: Optional[SimulationConfig] = None,
    ):
        self.analyzer = analyzer or StatisticsAnalyzer()
        self.config = config or SimulationConfig()

    def simulate_pod_recommendation(
        self,
        pod_data: PodResourceData,
        recommendation: PodVerticalRecommendation,
        cost_estimator: Optional[CostEstimator] = None,
    ) -> PodSimulationResult:
        logger.info(f"Simulating recommendation for pod {pod_data.namespace}/{pod_data.pod}")

        result = PodSimulationResult(
            pod=pod_data.pod,
            namespace=pod_data.namespace,
            status=SimulationStatus.SUCCESS,
        )

        if pod_data.cpu_usage is None or pod_data.memory_usage is None:
            result.status = SimulationStatus.FAILURE
            result.summary = "缺少历史使用数据，无法进行模拟"
            return result

        cpu_result = self._simulate_resource(
            pod_data.cpu_usage,
            recommendation.cpu,
            "cpu",
        )

        memory_result = self._simulate_resource(
            pod_data.memory_usage,
            recommendation.memory,
            "memory",
        )

        result.cpu_throttling_events = cpu_result["throttling_events"]
        result.cpu_evictions = cpu_result["evictions"]
        result.max_cpu_usage = cpu_result["max_usage"]
        result.oom_events = memory_result["oom_events"]
        result.memory_evictions = memory_result["evictions"]
        result.max_memory_usage = memory_result["max_usage"]
        result.p99_memory_usage = memory_result["p99_usage"]
        result.events = cpu_result["events"] + memory_result["events"]

        total_issues = result.cpu_throttling_events + result.oom_events + result.cpu_evictions + result.memory_evictions

        if total_issues > 0:
            result.status = SimulationStatus.WARNING
            result.risk_level = self._assess_risk(total_issues, result)
        else:
            result.risk_level = "low"

        result.p95_cpu_latency_impact = self._calculate_latency_impact(
            pod_data.cpu_usage,
            recommendation.cpu,
            result.cpu_throttling_events,
        )

        result.metrics = self._calculate_metrics(
            pod_data, recommendation, result
        )

        if cost_estimator:
            result.cost_analysis = cost_estimator.estimate_vertical_cost(recommendation)

        result.summary = self._generate_summary(result, recommendation)

        return result

    def _simulate_resource(
        self,
        metrics_data: MetricsData,
        recommendation: VerticalResourceRecommendation,
        resource_type: str,
    ) -> Dict:
        if metrics_data.values is None or len(metrics_data.values) == 0:
            return {
                "throttling_events": 0,
                "oom_events": 0,
                "evictions": 0,
                "max_usage": 0.0,
                "p99_usage": 0.0,
                "events": [],
            }

        values = metrics_data.values
        timestamps = metrics_data.timestamps or np.arange(len(values))

        target_request = recommendation.target_request
        target_limit = recommendation.target_limit
        lower_bound = recommendation.lower_bound
        upper_bound = recommendation.upper_bound

        throttling_threshold = target_limit * self.config.throttling_threshold
        oom_threshold = target_limit * self.config.oom_threshold
        eviction_threshold = target_limit * self.config.eviction_threshold

        throttling_events = 0
        oom_events = 0
        evictions = 0
        events = []

        stress_factor = self._get_stress_factor()
        simulated_values = values * stress_factor

        for i, (ts, usage) in enumerate(zip(timestamps, simulated_values)):
            usage_ratio = usage / target_limit if target_limit > 0 else 0

            if self.config.enable_throttling_simulation and usage_ratio >= throttling_threshold:
                if resource_type == "cpu":
                    throttling_events += 1
                    events.append(ResourceEvent(
                        timestamp=ts,
                        resource_type=resource_type,
                        event_type="throttling",
                        value=usage,
                        threshold=throttling_threshold,
                        description=f"{resource_type.upper()} 使用率达到 {usage_ratio*100:.1f}%，可能发生节流",
                    ))

            if self.config.enable_oom_simulation and usage_ratio >= oom_threshold:
                if resource_type == "memory":
                    oom_events += 1
                    events.append(ResourceEvent(
                        timestamp=ts,
                        resource_type=resource_type,
                        event_type="oom",
                        value=usage,
                        threshold=oom_threshold,
                        description=f"内存使用率达到 {usage_ratio*100:.1f}%，存在OOM风险",
                    ))

            if self.config.enable_eviction_simulation and usage_ratio >= eviction_threshold:
                evictions += 1
                events.append(ResourceEvent(
                    timestamp=ts,
                    resource_type=resource_type,
                    event_type="eviction",
                    value=usage,
                    threshold=eviction_threshold,
                    description=f"{resource_type.upper()} 使用率达到 {usage_ratio*100:.1f}%，可能被驱逐",
                ))

        return {
            "throttling_events": throttling_events,
            "oom_events": oom_events,
            "evictions": evictions,
            "max_usage": float(np.max(simulated_values)),
            "p99_usage": float(np.percentile(simulated_values, 99)),
            "events": events,
        }

    def _get_stress_factor(self) -> float:
        stress_factors = {
            "normal": 1.0,
            "moderate": 1.2,
            "high": 1.5,
            "extreme": 2.0,
        }
        return stress_factors.get(self.config.stress_scenario, 1.0)

    def _assess_risk(self, total_issues: int, result: PodSimulationResult) -> str:
        if result.oom_events > 0 or result.cpu_evictions > 0 or result.memory_evictions > 0:
            return "high"
        elif total_issues > 10:
            return "high"
        elif total_issues > 3:
            return "medium"
        else:
            return "low"

    def _calculate_latency_impact(
        self,
        cpu_data: MetricsData,
        cpu_recommendation: VerticalResourceRecommendation,
        throttling_events: int,
    ) -> float:
        if cpu_data.values is None or len(cpu_data.values) == 0:
            return 0.0

        throttling_ratio = throttling_events / len(cpu_data.values)

        if throttling_ratio == 0:
            return 0.0

        base_latency_factor = 1.0 + throttling_ratio * 2.0

        return (base_latency_factor - 1.0) * 100

    def _calculate_metrics(
        self,
        pod_data: PodResourceData,
        recommendation: PodVerticalRecommendation,
        result: PodSimulationResult,
    ) -> List[SimulationMetric]:
        metrics = []

        if pod_data.cpu_request and pod_data.cpu_request > 0:
            cpu_reduction = (1 - recommendation.cpu.target_request / pod_data.cpu_request) * 100
            metrics.append(SimulationMetric(
                name="CPU请求变化",
                current_value=pod_data.cpu_request,
                simulated_value=recommendation.cpu.target_request,
                improvement=cpu_reduction,
                unit="cores",
            ))

        if pod_data.memory_request and pod_data.memory_request > 0:
            memory_reduction = (1 - recommendation.memory.target_request / pod_data.memory_request) * 100
            metrics.append(SimulationMetric(
                name="内存请求变化",
                current_value=pod_data.memory_request,
                simulated_value=recommendation.memory.target_request,
                improvement=memory_reduction,
                unit="bytes",
            ))

        if result.max_cpu_usage > 0 and recommendation.cpu.target_limit > 0:
            cpu_headroom = (1 - result.max_cpu_usage / recommendation.cpu.target_limit) * 100
            metrics.append(SimulationMetric(
                name="CPU峰值预留空间",
                current_value=0.0,
                simulated_value=cpu_headroom,
                improvement=cpu_headroom,
                unit="%",
            ))

        if result.max_memory_usage > 0 and recommendation.memory.target_limit > 0:
            memory_headroom = (1 - result.max_memory_usage / recommendation.memory.target_limit) * 100
            metrics.append(SimulationMetric(
                name="内存峰值预留空间",
                current_value=0.0,
                simulated_value=memory_headroom,
                improvement=memory_headroom,
                unit="%",
            ))

        metrics.append(SimulationMetric(
            name="CPU节流事件",
            current_value=0.0,
            simulated_value=result.cpu_throttling_events,
            improvement=-result.cpu_throttling_events,
            unit="次",
        ))

        metrics.append(SimulationMetric(
            name="OOM风险事件",
            current_value=0.0,
            simulated_value=result.oom_events,
            improvement=-result.oom_events,
            unit="次",
        ))

        return metrics

    def _generate_summary(
        self,
        result: PodSimulationResult,
        recommendation: PodVerticalRecommendation,
    ) -> str:
        if result.status == SimulationStatus.FAILURE:
            return "模拟失败：缺少必要的历史数据"

        issues = []
        if result.cpu_throttling_events > 0:
            issues.append(f"{result.cpu_throttling_events}次CPU节流")
        if result.oom_events > 0:
            issues.append(f"{result.oom_events}次OOM风险")
        if result.cpu_evictions > 0 or result.memory_evictions > 0:
            issues.append(f"{result.cpu_evictions + result.memory_evictions}次驱逐风险")

        if result.risk_level == "high":
            return f"⚠️  高风险：模拟检测到{', '.join(issues)}。建议谨慎应用或调整推荐配置。"
        elif result.risk_level == "medium":
            return f"⚠️  中等风险：模拟检测到{', '.join(issues)}。建议在非高峰期逐步应用。"
        else:
            if result.cost_analysis and result.cost_analysis.monthly_savings > 0:
                return f"✅ 模拟成功！应用推荐后预计每月节省 ${result.cost_analysis.monthly_savings:.2f}，无明显风险。"
            elif result.cost_analysis and result.cost_analysis.monthly_savings < 0:
                return f"✅ 模拟成功！需要增加资源投入 ${abs(result.cost_analysis.monthly_savings):.2f}/月以提高稳定性，无明显风险。"
            else:
                return "✅ 模拟成功！当前配置已为最优状态，无明显风险。"

    def simulate_deployment_recommendation(
        self,
        deployment_data: DeploymentResourceData,
        vpa_recommendations: List[PodVerticalRecommendation],
        hpa_recommendation: Optional[DeploymentHorizontalRecommendation] = None,
        cost_estimator: Optional[CostEstimator] = None,
    ) -> DeploymentSimulationResult:
        logger.info(f"Simulating recommendation for deployment {deployment_data.namespace}/{deployment_data.deployment}")

        result = DeploymentSimulationResult(
            deployment=deployment_data.deployment,
            namespace=deployment_data.namespace,
            status=SimulationStatus.SUCCESS,
        )

        pod_results = []
        vpa_map = {r.pod: r for r in vpa_recommendations}

        for pod_data in deployment_data.pods:
            vpa_rec = vpa_map.get(pod_data.pod)
            if vpa_rec:
                pod_sim = self.simulate_pod_recommendation(pod_data, vpa_rec, cost_estimator)
                pod_results.append(pod_sim)

                result.total_throttling_events += pod_sim.cpu_throttling_events
                result.total_oom_events += pod_sim.oom_events
                result.total_evictions += pod_sim.cpu_evictions + pod_sim.memory_evictions

                if pod_sim.status == SimulationStatus.FAILURE:
                    result.status = SimulationStatus.FAILURE
                elif pod_sim.status == SimulationStatus.WARNING and result.status != SimulationStatus.FAILURE:
                    result.status = SimulationStatus.WARNING

                if pod_sim.cost_analysis:
                    result.cost_savings_monthly += pod_sim.cost_analysis.monthly_savings

        result.pods = pod_results

        if hpa_recommendation:
            hpa_impact = self._assess_hpa_impact(deployment_data, hpa_recommendation)
            result.availability_impact = hpa_impact["availability_impact"]
            result.performance_impact = hpa_impact["performance_impact"]

        result.recommendations = self._generate_deployment_recommendations(result, hpa_recommendation)
        result.summary = self._generate_deployment_summary(result, hpa_recommendation)

        return result

    def _assess_hpa_impact(
        self,
        deployment_data: DeploymentResourceData,
        hpa_recommendation: DeploymentHorizontalRecommendation,
    ) -> Dict:
        rec = hpa_recommendation.recommendation
        current_replicas = rec.current_replicas
        target_replicas = rec.target_replicas

        replica_change = target_replicas - current_replicas

        if replica_change > 0:
            availability_impact = min(replica_change / max(current_replicas, 1) * 20, 10)
            performance_impact = "positive"
        elif replica_change < 0:
            availability_impact = max(replica_change / max(current_replicas, 1) * 30, -15)
            performance_impact = "neutral" if abs(replica_change) <= 1 else "caution"
        else:
            availability_impact = 0.0
            performance_impact = "neutral"

        return {
            "availability_impact": availability_impact,
            "performance_impact": performance_impact,
            "replica_change": replica_change,
        }

    def _generate_deployment_recommendations(
        self,
        result: DeploymentSimulationResult,
        hpa_recommendation: Optional[DeploymentHorizontalRecommendation],
    ) -> List[str]:
        recommendations = []

        if result.status == SimulationStatus.FAILURE:
            recommendations.append("❌ 模拟失败，请检查数据完整性后重试")
            return recommendations

        if result.total_evictions > 0:
            recommendations.append(f"🚨 检测到 {result.total_evictions} 次Pod驱逐风险，强烈建议调整资源配置")
            recommendations.append("   建议：增加resources.limit或优化应用内存使用")

        if result.total_oom_events > 0:
            recommendations.append(f"⚠️  检测到 {result.total_oom_events} 次OOM风险事件")
            recommendations.append("   建议：增加内存请求或限制，或排查内存泄漏")

        if result.total_throttling_events > 0:
            recommendations.append(f"⚠️  检测到 {result.total_throttling_events} 次CPU节流事件")
            recommendations.append("   建议：适当增加CPU限制以减少性能影响")

        if hpa_recommendation:
            rec = hpa_recommendation.recommendation
            replica_change = rec.target_replicas - rec.current_replicas
            if replica_change > 0:
                recommendations.append(f"📈 建议将副本数从 {rec.current_replicas} 增加到 {rec.target_replicas}")
                recommendations.append(f"   预计可用性提升 {abs(result.availability_impact):.1f}%")
            elif replica_change < 0:
                recommendations.append(f"📉 建议将副本数从 {rec.current_replicas} 减少到 {rec.target_replicas}")
                recommendations.append(f"   预计成本降低，可用性影响 {result.availability_impact:.1f}%")
            else:
                recommendations.append("✅ 当前副本数配置合理")

        high_risk_pods = [p for p in result.pods if p.risk_level == "high"]
        if high_risk_pods:
            recommendations.append(f"🔴 {len(high_risk_pods)} 个Pod存在高风险：")
            for pod in high_risk_pods[:3]:
                recommendations.append(f"   - {pod.pod}: {pod.summary}")

        if result.cost_savings_monthly > 0:
            recommendations.append(f"💰 优化后预计每月节省 ${result.cost_savings_monthly:.2f}（年度 ${result.cost_savings_monthly*12:.2f}）")
        elif result.cost_savings_monthly < 0:
            recommendations.append(f"💰 需要增加资源投入 ${abs(result.cost_savings_monthly):.2f}/月 以提高稳定性")

        if result.status == SimulationStatus.SUCCESS and result.risk_level == "low":
            recommendations.append("✅ 所有Pod模拟通过，可以安全应用推荐配置")

        return recommendations

    def _generate_deployment_summary(
        self,
        result: DeploymentSimulationResult,
        hpa_recommendation: Optional[DeploymentHorizontalRecommendation],
    ) -> str:
        if result.status == SimulationStatus.FAILURE:
            return "模拟失败：部分Pod缺少必要数据"

        total_pods = len(result.pods)
        high_risk = sum(1 for p in result.pods if p.risk_level == "high")
        medium_risk = sum(1 for p in result.pods if p.risk_level == "medium")
        low_risk = sum(1 for p in result.pods if p.risk_level == "low")

        base = f"共 {total_pods} 个Pod：{high_risk} 个高风险，{medium_risk} 个中等风险，{low_risk} 个低风险"

        if result.total_evictions > 0 or result.total_oom_events > 0:
            return f"⚠️  存在严重风险：{base}。建议先调整有风险的Pod配置。"
        elif result.total_throttling_events > 0:
            return f"⚠️  存在性能风险：{base}。建议逐步应用并监控。"
        elif result.cost_savings_monthly > 0:
            return f"✅ 模拟成功！{base}。应用推荐后预计每月节省 ${result.cost_savings_monthly:.2f}。"
        else:
            return f"✅ 模拟成功！{base}。当前配置已处于较优状态。"
