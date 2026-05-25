import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from enum import Enum

import numpy as np

from .data_collector import MetricsData, PodResourceData, DeploymentResourceData
from .statistics_analyzer import ResourceStatistics, StatisticsAnalyzer
from .cost_estimator import CostEstimator

logger = logging.getLogger(__name__)


class WasteCategory(str, Enum):
    IDLE = "idle"
    UNDERUTILIZED = "underutilized"
    OPTIMAL = "optimal"
    OVERUTILIZED = "overutilized"
    CRITICAL = "critical"


@dataclass
class ResourceWasteDetail:
    resource_type: str
    request: float
    usage_mean: float
    usage_median: float
    usage_percentile_95: float
    utilization: float
    waste_amount: float
    waste_percent: float
    category: WasteCategory
    monthly_waste_cost: float = 0.0


@dataclass
class PodWasteAnalysis:
    namespace: str
    pod: str
    cpu: ResourceWasteDetail
    memory: ResourceWasteDetail
    total_monthly_waste_cost: float = 0.0
    waste_severity: str = "low"
    recommendations: List[str] = field(default_factory=list)
    is_idle: bool = False


@dataclass
class DeploymentWasteAnalysis:
    namespace: str
    deployment: str
    pods: List[PodWasteAnalysis] = field(default_factory=list)
    total_monthly_waste_cost: float = 0.0
    total_pods: int = 0
    idle_pods: int = 0
    underutilized_pods: int = 0
    optimal_pods: int = 0
    overutilized_pods: int = 0
    critical_pods: int = 0
    recommendations: List[str] = field(default_factory=list)


@dataclass
class WasteSummary:
    total_pods: int = 0
    total_deployments: int = 0
    total_monthly_waste: float = 0.0
    total_annual_waste: float = 0.0
    idle_resources: float = 0.0
    underutilized_resources: float = 0.0
    optimal_resources: float = 0.0
    top_waste_pods: List[PodWasteAnalysis] = field(default_factory=list)
    category_breakdown: Dict[str, int] = field(default_factory=dict)


class WasteAnalyzer:
    def __init__(
        self,
        analyzer: Optional[StatisticsAnalyzer] = None,
        idle_threshold: float = 0.05,
        underutilized_threshold: float = 0.3,
        optimal_low: float = 0.3,
        optimal_high: float = 0.7,
        overutilized_threshold: float = 0.9,
        critical_threshold: float = 0.95,
    ):
        self.analyzer = analyzer or StatisticsAnalyzer()
        self.idle_threshold = idle_threshold
        self.underutilized_threshold = underutilized_threshold
        self.optimal_low = optimal_low
        self.optimal_high = optimal_high
        self.overutilized_threshold = overutilized_threshold
        self.critical_threshold = critical_threshold

    def analyze_pod_waste(
        self,
        pod_data: PodResourceData,
        cost_estimator: Optional[CostEstimator] = None,
    ) -> PodWasteAnalysis:
        logger.info(f"Analyzing waste for pod {pod_data.namespace}/{pod_data.pod}")

        cpu_detail = self._analyze_resource_waste(
            pod_data.cpu_usage,
            pod_data.cpu_request or 0,
            "cpu",
            cost_estimator,
        )

        memory_detail = self._analyze_resource_waste(
            pod_data.memory_usage,
            pod_data.memory_request or 0,
            "memory",
            cost_estimator,
        )

        total_monthly_waste = cpu_detail.monthly_waste_cost + memory_detail.monthly_waste_cost
        is_idle = cpu_detail.category == WasteCategory.IDLE and memory_detail.category == WasteCategory.IDLE

        waste_severity = self._determine_severity(cpu_detail, memory_detail, total_monthly_waste, is_idle)

        recommendations = self._generate_pod_recommendations(
            cpu_detail, memory_detail, total_monthly_waste, is_idle
        )

        return PodWasteAnalysis(
            namespace=pod_data.namespace,
            pod=pod_data.pod,
            cpu=cpu_detail,
            memory=memory_detail,
            total_monthly_waste_cost=total_monthly_waste,
            waste_severity=waste_severity,
            recommendations=recommendations,
            is_idle=is_idle,
        )

    def _analyze_resource_waste(
        self,
        metrics_data: Optional[MetricsData],
        request: float,
        resource_type: str,
        cost_estimator: Optional[CostEstimator],
    ) -> ResourceWasteDetail:
        if metrics_data is None or metrics_data.values is None or len(metrics_data.values) == 0:
            return ResourceWasteDetail(
                resource_type=resource_type,
                request=request,
                usage_mean=0.0,
                usage_median=0.0,
                usage_percentile_95=0.0,
                utilization=0.0,
                waste_amount=request,
                waste_percent=100.0 if request > 0 else 0.0,
                category=WasteCategory.IDLE,
                monthly_waste_cost=0.0,
            )

        values = metrics_data.values
        usage_mean = np.mean(values)
        usage_median = np.median(values)
        usage_percentile_95 = np.percentile(values, 95)

        if request <= 0:
            utilization = 1.0 if usage_mean > 0 else 0.0
            waste_amount = 0.0
            waste_percent = 0.0
        else:
            utilization = usage_percentile_95 / request
            waste_amount = max(0, request - usage_percentile_95 * 1.1)
            waste_percent = (waste_amount / request * 100) if request > 0 else 0.0

        category = self._categorize_utilization(utilization)

        monthly_waste_cost = 0.0
        if cost_estimator and waste_amount > 0:
            monthly_waste_cost = self._calculate_waste_cost(
                waste_amount, resource_type, cost_estimator
            )

        return ResourceWasteDetail(
            resource_type=resource_type,
            request=request,
            usage_mean=usage_mean,
            usage_median=usage_median,
            usage_percentile_95=usage_percentile_95,
            utilization=utilization,
            waste_amount=waste_amount,
            waste_percent=waste_percent,
            category=category,
            monthly_waste_cost=monthly_waste_cost,
        )

    def _categorize_utilization(self, utilization: float) -> WasteCategory:
        if utilization < self.idle_threshold:
            return WasteCategory.IDLE
        elif utilization < self.underutilized_threshold:
            return WasteCategory.UNDERUTILIZED
        elif utilization < self.overutilized_threshold:
            return WasteCategory.OPTIMAL
        elif utilization < self.critical_threshold:
            return WasteCategory.OVERUTILIZED
        else:
            return WasteCategory.CRITICAL

    def _calculate_waste_cost(
        self,
        waste_amount: float,
        resource_type: str,
        cost_estimator: CostEstimator,
    ) -> float:
        try:
            if resource_type == "cpu":
                return cost_estimator._calculate_cpu_monthly_cost(waste_amount)
            else:
                memory_gb = waste_amount / (1024 ** 3)
                return cost_estimator._calculate_memory_monthly_cost(memory_gb)
        except Exception as e:
            logger.warning(f"Error calculating waste cost: {e}")
            return 0.0

    def _determine_severity(
        self,
        cpu_detail: ResourceWasteDetail,
        memory_detail: ResourceWasteDetail,
        total_waste: float,
        is_idle: bool,
    ) -> str:
        if is_idle:
            return "critical"

        if total_waste >= 50:
            return "high"
        elif total_waste >= 10:
            return "medium"
        elif cpu_detail.category in [WasteCategory.OVERUTILIZED, WasteCategory.CRITICAL] or \
             memory_detail.category in [WasteCategory.OVERUTILIZED, WasteCategory.CRITICAL]:
            return "high"
        elif cpu_detail.category == WasteCategory.UNDERUTILIZED or \
             memory_detail.category == WasteCategory.UNDERUTILIZED:
            return "medium"
        else:
            return "low"

    def _generate_pod_recommendations(
        self,
        cpu_detail: ResourceWasteDetail,
        memory_detail: ResourceWasteDetail,
        total_waste: float,
        is_idle: bool,
    ) -> List[str]:
        recommendations = []

        if is_idle:
            recommendations.append("⚠️  Pod几乎完全闲置，建议评估是否可以删除或缩容到0")
            recommendations.append(f"   CPU使用率: {cpu_detail.utilization*100:.1f}%, 内存使用率: {memory_detail.utilization*100:.1f}%")
            return recommendations

        if cpu_detail.category == WasteCategory.IDLE:
            recommendations.append(f"CPU闲置严重（使用率{cpu_detail.utilization*100:.1f}%），建议大幅减少CPU请求")
        elif cpu_detail.category == WasteCategory.UNDERUTILIZED:
            recommendations.append(f"CPU利用率偏低（{cpu_detail.utilization*100:.1f}%），建议减少CPU请求约{cpu_detail.waste_percent:.0f}%")
        elif cpu_detail.category == WasteCategory.OVERUTILIZED:
            recommendations.append(f"CPU利用率偏高（{cpu_detail.utilization*100:.1f}%），建议增加CPU资源")
        elif cpu_detail.category == WasteCategory.CRITICAL:
            recommendations.append(f"⚠️  CPU利用率极高（{cpu_detail.utilization*100:.1f}%），存在性能风险，建议立即扩容")

        if memory_detail.category == WasteCategory.IDLE:
            recommendations.append(f"内存闲置严重（使用率{memory_detail.utilization*100:.1f}%），建议大幅减少内存请求")
        elif memory_detail.category == WasteCategory.UNDERUTILIZED:
            recommendations.append(f"内存利用率偏低（{memory_detail.utilization*100:.1f}%），建议减少内存请求约{memory_detail.waste_percent:.0f}%")
        elif memory_detail.category == WasteCategory.OVERUTILIZED:
            recommendations.append(f"内存利用率偏高（{memory_detail.utilization*100:.1f}%），建议增加内存资源")
        elif memory_detail.category == WasteCategory.CRITICAL:
            recommendations.append(f"⚠️  内存利用率极高（{memory_detail.utilization*100:.1f}%），存在OOM风险，建议立即扩容")

        if total_waste > 0:
            recommendations.append(f"💰 预计每月可节省成本: ${total_waste:.2f}（年度: ${total_waste*12:.2f}）")

        if cpu_detail.category == WasteCategory.OPTIMAL and memory_detail.category == WasteCategory.OPTIMAL:
            recommendations.append("✅ 资源配置合理，CPU和内存利用率均处于最优区间")

        return recommendations

    def analyze_deployment_waste(
        self,
        deployment_data: DeploymentResourceData,
        cost_estimator: Optional[CostEstimator] = None,
    ) -> DeploymentWasteAnalysis:
        logger.info(f"Analyzing waste for deployment {deployment_data.namespace}/{deployment_data.deployment}")

        pod_analyses = []
        for pod_data in deployment_data.pods:
            pod_analysis = self.analyze_pod_waste(pod_data, cost_estimator)
            pod_analyses.append(pod_analysis)

        analysis = DeploymentWasteAnalysis(
            namespace=deployment_data.namespace,
            deployment=deployment_data.deployment,
            pods=pod_analyses,
            total_pods=len(pod_analyses),
        )

        for pod in pod_analyses:
            analysis.total_monthly_waste_cost += pod.total_monthly_waste_cost

            if pod.cpu.category == WasteCategory.IDLE and pod.memory.category == WasteCategory.IDLE:
                analysis.idle_pods += 1
            elif pod.cpu.category == WasteCategory.UNDERUTILIZED or pod.memory.category == WasteCategory.UNDERUTILIZED:
                analysis.underutilized_pods += 1
            elif pod.cpu.category == WasteCategory.OPTIMAL and pod.memory.category == WasteCategory.OPTIMAL:
                analysis.optimal_pods += 1
            elif pod.cpu.category == WasteCategory.OVERUTILIZED or pod.memory.category == WasteCategory.OVERUTILIZED:
                analysis.overutilized_pods += 1
            elif pod.cpu.category == WasteCategory.CRITICAL or pod.memory.category == WasteCategory.CRITICAL:
                analysis.critical_pods += 1

        analysis.recommendations = self._generate_deployment_recommendations(analysis)

        return analysis

    def _generate_deployment_recommendations(self, analysis: DeploymentWasteAnalysis) -> List[str]:
        recommendations = []

        if analysis.idle_pods > 0:
            recommendations.append(f"⚠️  发现 {analysis.idle_pods} 个闲置Pod，占比 {analysis.idle_pods/analysis.total_pods*100:.0f}%")
            recommendations.append("   建议：评估业务需求，考虑删除或缩容闲置实例")

        if analysis.critical_pods > 0:
            recommendations.append(f"🚨 发现 {analysis.critical_pods} 个资源严重不足的Pod，存在稳定性风险")
            recommendations.append("   建议：立即为这些Pod增加资源配置")

        if analysis.underutilized_pods > analysis.total_pods * 0.5:
            recommendations.append(f"📉 超过半数Pod（{analysis.underutilized_pods}/{analysis.total_pods}）资源利用率偏低")
            recommendations.append("   建议：统一调整资源请求，优化资源配置")

        if analysis.total_monthly_waste_cost > 100:
            recommendations.append(f"💰 该Deployment每月浪费成本约 ${analysis.total_monthly_waste_cost:.2f}")
            recommendations.append(f"   年度预计浪费: ${analysis.total_monthly_waste_cost * 12:.2f}")

        if analysis.optimal_pods == analysis.total_pods:
            recommendations.append("✅ 所有Pod资源配置合理，利用率均处于最优区间")

        return recommendations

    def generate_summary(
        self,
        pod_analyses: List[PodWasteAnalysis],
        deployment_analyses: Optional[List[DeploymentWasteAnalysis]] = None,
    ) -> WasteSummary:
        summary = WasteSummary(
            total_pods=len(pod_analyses),
            total_deployments=len(deployment_analyses) if deployment_analyses else 0,
        )

        for pod in pod_analyses:
            summary.total_monthly_waste += pod.total_monthly_waste_cost

            if pod.is_idle:
                summary.idle_resources += 1
            elif pod.cpu.category == WasteCategory.UNDERUTILIZED or pod.memory.category == WasteCategory.UNDERUTILIZED:
                summary.underutilized_resources += 1
            elif pod.cpu.category == WasteCategory.OPTIMAL and pod.memory.category == WasteCategory.OPTIMAL:
                summary.optimal_resources += 1

            category = pod.waste_severity
            summary.category_breakdown[category] = summary.category_breakdown.get(category, 0) + 1

        summary.total_annual_waste = summary.total_monthly_waste * 12

        sorted_pods = sorted(pod_analyses, key=lambda p: p.total_monthly_waste_cost, reverse=True)
        summary.top_waste_pods = sorted_pods[:10]

        return summary
