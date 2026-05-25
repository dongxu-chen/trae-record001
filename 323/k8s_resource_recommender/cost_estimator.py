import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import numpy as np

from .hpa_recommender import DeploymentHorizontalRecommendation
from .vpa_recommender import PodVerticalRecommendation

logger = logging.getLogger(__name__)


@dataclass
class ResourceCost:
    cpu_cost_per_core_per_hour: float
    memory_cost_per_gb_per_hour: float
    cpu_unit: str = "core"
    memory_unit: str = "Gi"


@dataclass
class ClusterManagementConfig:
    enabled: bool = False
    monthly_fixed_cost: float = 100.0
    allocation_method: str = "by_core_ratio"
    min_allocation_per_pod: float = 5.0


@dataclass
class ClusterManagementAllocation:
    monthly_fixed_cost: float
    allocation_ratio: float
    current_monthly_cost: float
    recommended_monthly_cost: float
    monthly_savings: float
    allocation_method: str
    allocation_detail: str = ""


@dataclass
class VerticalCostAnalysis:
    current_monthly_cost: float
    recommended_monthly_cost: float
    monthly_savings: float
    savings_percent: float
    cpu_current_cost: float
    cpu_recommended_cost: float
    cpu_savings: float
    memory_current_cost: float
    memory_recommended_cost: float
    memory_savings: float
    confidence: float
    cluster_management: Optional[ClusterManagementAllocation] = None


@dataclass
class HorizontalCostAnalysis:
    current_monthly_cost: float
    recommended_monthly_cost: float
    monthly_savings: float
    savings_percent: float
    cpu_current_cost: float
    cpu_recommended_cost: float
    cpu_savings: float
    memory_current_cost: float
    memory_recommended_cost: float
    memory_savings: float
    replicas_current: int
    replicas_recommended: int
    confidence: float
    cluster_management: Optional[ClusterManagementAllocation] = None


@dataclass
class TotalCostAnalysis:
    vertical: Optional[VerticalCostAnalysis] = None
    horizontal: Optional[HorizontalCostAnalysis] = None
    combined_monthly_savings: float = 0.0
    combined_savings_percent: float = 0.0
    total_current_monthly_cost: float = 0.0
    total_recommended_monthly_cost: float = 0.0
    cluster_management: Optional[ClusterManagementAllocation] = None


class CostEstimator:
    def __init__(
        self,
        cost_config: Optional[ResourceCost] = None,
        cluster_management_config: Optional[ClusterManagementConfig] = None,
        hours_per_month: float = 730.0,
    ):
        self.cost_config = cost_config or ResourceCost(
            cpu_cost_per_core_per_hour=0.023,
            memory_cost_per_gb_per_hour=0.003,
        )
        self.cluster_management_config = cluster_management_config or ClusterManagementConfig()
        self.hours_per_month = hours_per_month
        self._cluster_total_cpu_cores: Optional[float] = None

    def set_cluster_total_cpu_cores(self, total_cores: float):
        self._cluster_total_cpu_cores = total_cores

    def _allocate_cluster_management_cost(
        self,
        current_cpu_cores: float,
        recommended_cpu_cores: float,
        cluster_total_cores: Optional[float] = None,
        pod_count: int = 1,
    ) -> Optional[ClusterManagementAllocation]:
        if not self.cluster_management_config.enabled:
            return None

        total_cores = cluster_total_cores or self._cluster_total_cpu_cores
        if total_cores is None or total_cores <= 0:
            total_cores = max(current_cpu_cores * 10, 1.0)

        allocation_method = self.cluster_management_config.allocation_method
        monthly_fixed_cost = self.cluster_management_config.monthly_fixed_cost
        min_allocation = self.cluster_management_config.min_allocation_per_pod * pod_count

        if allocation_method == "by_core_ratio":
            current_ratio = current_cpu_cores / total_cores
            recommended_ratio = recommended_cpu_cores / total_cores
            allocation_detail = f"核数比例: 占用集群总核数 {current_ratio*100:.2f}%"
        else:
            current_ratio = pod_count / 100
            recommended_ratio = pod_count / 100
            allocation_detail = "按Pod平均分摊"

        current_cost = max(monthly_fixed_cost * current_ratio, min_allocation)
        recommended_cost = max(monthly_fixed_cost * recommended_ratio, min_allocation)

        return ClusterManagementAllocation(
            monthly_fixed_cost=monthly_fixed_cost,
            allocation_ratio=current_ratio,
            current_monthly_cost=current_cost,
            recommended_monthly_cost=recommended_cost,
            monthly_savings=current_cost - recommended_cost,
            allocation_method=allocation_method,
            allocation_detail=allocation_detail,
        )

    def estimate_vertical_cost(
        self,
        recommendation: PodVerticalRecommendation,
        cpu_current: Optional[float] = None,
        memory_current: Optional[float] = None,
        cpu_recommended: Optional[float] = None,
        memory_recommended: Optional[float] = None,
    ) -> Optional[VerticalCostAnalysis]:
        cpu_current = cpu_current or recommendation.current_cpu_request or 0
        memory_current = memory_current or recommendation.current_memory_request or 0
        cpu_recommended = cpu_recommended or recommendation.cpu.target_request or 0
        memory_recommended = memory_recommended or recommendation.memory.target_request or 0

        if cpu_current <= 0 and memory_current <= 0:
            logger.warning("Cannot estimate cost with zero current resources")
            return None

        memory_current_gb = memory_current / (1024 ** 3)
        memory_recommended_gb = memory_recommended / (1024 ** 3)

        cpu_current_cost = self._calculate_cpu_monthly_cost(cpu_current)
        cpu_recommended_cost = self._calculate_cpu_monthly_cost(cpu_recommended)
        cpu_savings = cpu_current_cost - cpu_recommended_cost

        memory_current_cost = self._calculate_memory_monthly_cost(memory_current_gb)
        memory_recommended_cost = self._calculate_memory_monthly_cost(memory_recommended_gb)
        memory_savings = memory_current_cost - memory_recommended_cost

        current_monthly_cost = cpu_current_cost + memory_current_cost
        recommended_monthly_cost = cpu_recommended_cost + memory_recommended_cost
        monthly_savings = current_monthly_cost - recommended_monthly_cost
        savings_percent = (monthly_savings / current_monthly_cost * 100) if current_monthly_cost > 0 else 0

        confidence = min(recommendation.cpu.confidence, recommendation.memory.confidence)

        cluster_mgmt = self._allocate_cluster_management_cost(
            current_cpu_cores=cpu_current,
            recommended_cpu_cores=cpu_recommended,
            pod_count=1,
        )

        if cluster_mgmt:
            current_monthly_cost += cluster_mgmt.current_monthly_cost
            recommended_monthly_cost += cluster_mgmt.recommended_monthly_cost
            monthly_savings += cluster_mgmt.monthly_savings
            savings_percent = (monthly_savings / current_monthly_cost * 100) if current_monthly_cost > 0 else 0

        return VerticalCostAnalysis(
            current_monthly_cost=current_monthly_cost,
            recommended_monthly_cost=recommended_monthly_cost,
            monthly_savings=monthly_savings,
            savings_percent=savings_percent,
            cpu_current_cost=cpu_current_cost,
            cpu_recommended_cost=cpu_recommended_cost,
            cpu_savings=cpu_savings,
            memory_current_cost=memory_current_cost,
            memory_recommended_cost=memory_recommended_cost,
            memory_savings=memory_savings,
            confidence=confidence,
            cluster_management=cluster_mgmt,
        )

    def estimate_horizontal_cost(
        self,
        recommendation: DeploymentHorizontalRecommendation,
        cpu_request_per_pod: float,
        memory_request_per_pod: float,
    ) -> Optional[HorizontalCostAnalysis]:
        rec = recommendation.recommendation

        if cpu_request_per_pod <= 0 and memory_request_per_pod <= 0:
            logger.warning("Cannot estimate cost with zero resource requests per pod")
            return None

        memory_per_pod_gb = memory_request_per_pod / (1024 ** 3)

        cpu_current_cost = self._calculate_cpu_monthly_cost(
            rec.current_replicas * cpu_request_per_pod
        )
        cpu_recommended_cost = self._calculate_cpu_monthly_cost(
            rec.target_replicas * cpu_request_per_pod
        )
        cpu_savings = cpu_current_cost - cpu_recommended_cost

        memory_current_cost = self._calculate_memory_monthly_cost(
            rec.current_replicas * memory_per_pod_gb
        )
        memory_recommended_cost = self._calculate_memory_monthly_cost(
            rec.target_replicas * memory_per_pod_gb
        )
        memory_savings = memory_current_cost - memory_recommended_cost

        current_cpu_cores = rec.current_replicas * cpu_request_per_pod
        recommended_cpu_cores = rec.target_replicas * cpu_request_per_pod

        current_monthly_cost = cpu_current_cost + memory_current_cost
        recommended_monthly_cost = cpu_recommended_cost + memory_recommended_cost
        monthly_savings = current_monthly_cost - recommended_monthly_cost
        savings_percent = (monthly_savings / current_monthly_cost * 100) if current_monthly_cost > 0 else 0

        cluster_mgmt = self._allocate_cluster_management_cost(
            current_cpu_cores=current_cpu_cores,
            recommended_cpu_cores=recommended_cpu_cores,
            pod_count=rec.current_replicas,
        )

        if cluster_mgmt:
            current_monthly_cost += cluster_mgmt.current_monthly_cost
            recommended_monthly_cost += cluster_mgmt.recommended_monthly_cost
            monthly_savings += cluster_mgmt.monthly_savings
            savings_percent = (monthly_savings / current_monthly_cost * 100) if current_monthly_cost > 0 else 0

        return HorizontalCostAnalysis(
            current_monthly_cost=current_monthly_cost,
            recommended_monthly_cost=recommended_monthly_cost,
            monthly_savings=monthly_savings,
            savings_percent=savings_percent,
            cpu_current_cost=cpu_current_cost,
            cpu_recommended_cost=cpu_recommended_cost,
            cpu_savings=cpu_savings,
            memory_current_cost=memory_current_cost,
            memory_recommended_cost=memory_recommended_cost,
            memory_savings=memory_savings,
            replicas_current=rec.current_replicas,
            replicas_recommended=rec.target_replicas,
            confidence=rec.confidence,
            cluster_management=cluster_mgmt,
        )

    def estimate_combined_cost(
        self,
        vertical_recommendations: List[PodVerticalRecommendation],
        horizontal_recommendation: Optional[DeploymentHorizontalRecommendation] = None,
        cpu_request_per_pod: Optional[float] = None,
        memory_request_per_pod: Optional[float] = None,
    ) -> TotalCostAnalysis:
        total_current = 0.0
        total_recommended = 0.0
        vertical_analysis = None
        horizontal_analysis = None

        if vertical_recommendations:
            cpu_current_total = sum(
                (r.current_cpu_request or 0) for r in vertical_recommendations
            )
            memory_current_total = sum(
                (r.current_memory_request or 0) for r in vertical_recommendations
            )
            cpu_recommended_total = sum(
                r.cpu.target_request for r in vertical_recommendations
            )
            memory_recommended_total = sum(
                r.memory.target_request for r in vertical_recommendations
            )

            avg_confidence = np.mean(
                [min(r.cpu.confidence, r.memory.confidence) for r in vertical_recommendations]
            )

            memory_current_gb = memory_current_total / (1024 ** 3)
            memory_recommended_gb = memory_recommended_total / (1024 ** 3)

            cpu_current_cost = self._calculate_cpu_monthly_cost(cpu_current_total)
            cpu_recommended_cost = self._calculate_cpu_monthly_cost(cpu_recommended_total)
            memory_current_cost = self._calculate_memory_monthly_cost(memory_current_gb)
            memory_recommended_cost = self._calculate_memory_monthly_cost(memory_recommended_gb)

            current_total = cpu_current_cost + memory_current_cost
            recommended_total = cpu_recommended_cost + memory_recommended_cost
            monthly_savings = current_total - recommended_total
            savings_percent = monthly_savings / current_total * 100 if current_total > 0 else 0

            cluster_mgmt = self._allocate_cluster_management_cost(
                current_cpu_cores=cpu_current_total,
                recommended_cpu_cores=cpu_recommended_total,
                pod_count=len(vertical_recommendations),
            )

            if cluster_mgmt:
                current_total += cluster_mgmt.current_monthly_cost
                recommended_total += cluster_mgmt.recommended_monthly_cost
                monthly_savings += cluster_mgmt.monthly_savings
                savings_percent = monthly_savings / current_total * 100 if current_total > 0 else 0

            vertical_analysis = VerticalCostAnalysis(
                current_monthly_cost=current_total,
                recommended_monthly_cost=recommended_total,
                monthly_savings=monthly_savings,
                savings_percent=savings_percent,
                cpu_current_cost=cpu_current_cost,
                cpu_recommended_cost=cpu_recommended_cost,
                cpu_savings=cpu_current_cost - cpu_recommended_cost,
                memory_current_cost=memory_current_cost,
                memory_recommended_cost=memory_recommended_cost,
                memory_savings=memory_current_cost - memory_recommended_cost,
                confidence=avg_confidence,
                cluster_management=cluster_mgmt,
            )

            total_current = current_total
            total_recommended = recommended_total
            total_cluster_mgmt = cluster_mgmt

            if not cpu_request_per_pod:
                cpu_request_per_pod = cpu_recommended_total / max(len(vertical_recommendations), 1)
            if not memory_request_per_pod:
                memory_request_per_pod = memory_recommended_total / max(len(vertical_recommendations), 1)

        if horizontal_recommendation and cpu_request_per_pod and memory_request_per_pod:
            horizontal_analysis = self.estimate_horizontal_cost(
                horizontal_recommendation,
                cpu_request_per_pod,
                memory_request_per_pod,
            )
            if horizontal_analysis:
                if total_current > 0:
                    ratio = horizontal_analysis.current_monthly_cost / (total_current + 1e-9)
                    total_recommended = total_recommended * ratio + horizontal_analysis.monthly_savings * -1
                else:
                    total_current = horizontal_analysis.current_monthly_cost
                    total_recommended = horizontal_analysis.recommended_monthly_cost

                if horizontal_analysis.cluster_management:
                    total_cluster_mgmt = horizontal_analysis.cluster_management

        combined_savings = total_current - total_recommended
        combined_savings_percent = (combined_savings / total_current * 100) if total_current > 0 else 0

        return TotalCostAnalysis(
            vertical=vertical_analysis,
            horizontal=horizontal_analysis,
            combined_monthly_savings=combined_savings,
            combined_savings_percent=combined_savings_percent,
            total_current_monthly_cost=total_current,
            total_recommended_monthly_cost=total_recommended,
            cluster_management=total_cluster_mgmt if 'total_cluster_mgmt' in locals() else None,
        )

    def _calculate_cpu_monthly_cost(self, cpu_cores: float) -> float:
        return cpu_cores * self.cost_config.cpu_cost_per_core_per_hour * self.hours_per_month

    def _calculate_memory_monthly_cost(self, memory_gb: float) -> float:
        return memory_gb * self.cost_config.memory_cost_per_gb_per_hour * self.hours_per_month

    @staticmethod
    def format_cost(amount: float, currency: str = "$") -> str:
        if amount >= 1000:
            return f"{currency}{amount:,.2f}"
        elif amount >= 1:
            return f"{currency}{amount:.2f}"
        else:
            return f"{currency}{amount:.4f}"

    def _cluster_mgmt_to_dict(self, cm: Optional[ClusterManagementAllocation]) -> Optional[Dict]:
        if not cm:
            return None
        return {
            "monthly_fixed_cost": cm.monthly_fixed_cost,
            "allocation_ratio": cm.allocation_ratio,
            "current_monthly_cost": cm.current_monthly_cost,
            "recommended_monthly_cost": cm.recommended_monthly_cost,
            "monthly_savings": cm.monthly_savings,
            "allocation_method": cm.allocation_method,
            "allocation_detail": cm.allocation_detail,
        }

    def generate_cost_summary(
        self,
        cost_analysis: TotalCostAnalysis,
    ) -> Dict:
        summary = {
            "total_current_monthly_cost": cost_analysis.total_current_monthly_cost,
            "total_recommended_monthly_cost": cost_analysis.total_recommended_monthly_cost,
            "total_monthly_savings": cost_analysis.combined_monthly_savings,
            "total_savings_percent": cost_analysis.combined_savings_percent,
            "breakdown": {},
        }

        if cost_analysis.vertical:
            summary["breakdown"]["vertical"] = {
                "current_monthly_cost": cost_analysis.vertical.current_monthly_cost,
                "recommended_monthly_cost": cost_analysis.vertical.recommended_monthly_cost,
                "monthly_savings": cost_analysis.vertical.monthly_savings,
                "savings_percent": cost_analysis.vertical.savings_percent,
                "cpu_savings": cost_analysis.vertical.cpu_savings,
                "memory_savings": cost_analysis.vertical.memory_savings,
                "confidence": cost_analysis.vertical.confidence,
                "cluster_management": self._cluster_mgmt_to_dict(cost_analysis.vertical.cluster_management),
            }

        if cost_analysis.horizontal:
            summary["breakdown"]["horizontal"] = {
                "current_monthly_cost": cost_analysis.horizontal.current_monthly_cost,
                "recommended_monthly_cost": cost_analysis.horizontal.recommended_monthly_cost,
                "monthly_savings": cost_analysis.horizontal.monthly_savings,
                "savings_percent": cost_analysis.horizontal.savings_percent,
                "cpu_savings": cost_analysis.horizontal.cpu_savings,
                "memory_savings": cost_analysis.horizontal.memory_savings,
                "replicas_change": cost_analysis.horizontal.replicas_recommended - cost_analysis.horizontal.replicas_current,
                "confidence": cost_analysis.horizontal.confidence,
                "cluster_management": self._cluster_mgmt_to_dict(cost_analysis.horizontal.cluster_management),
            }

        if cost_analysis.cluster_management:
            summary["cluster_management"] = self._cluster_mgmt_to_dict(cost_analysis.cluster_management)

        summary["annualized"] = {
            "savings": cost_analysis.combined_monthly_savings * 12,
            "current_cost": cost_analysis.total_current_monthly_cost * 12,
            "recommended_cost": cost_analysis.total_recommended_monthly_cost * 12,
        }

        return summary

    def set_cost_config(
        self,
        cpu_cost_per_core_per_hour: Optional[float] = None,
        memory_cost_per_gb_per_hour: Optional[float] = None,
    ):
        if cpu_cost_per_core_per_hour is not None:
            self.cost_config.cpu_cost_per_core_per_hour = cpu_cost_per_core_per_hour
        if memory_cost_per_gb_per_hour is not None:
            self.cost_config.memory_cost_per_gb_per_hour = memory_cost_per_gb_per_hour

    @staticmethod
    def get_cloud_provider_pricing(cloud_provider: str = "aws") -> ResourceCost:
        pricing = {
            "aws": ResourceCost(
                cpu_cost_per_core_per_hour=0.023,
                memory_cost_per_gb_per_hour=0.003,
            ),
            "gcp": ResourceCost(
                cpu_cost_per_core_per_hour=0.020,
                memory_cost_per_gb_per_hour=0.0025,
            ),
            "azure": ResourceCost(
                cpu_cost_per_core_per_hour=0.021,
                memory_cost_per_gb_per_hour=0.0027,
            ),
            "alibaba": ResourceCost(
                cpu_cost_per_core_per_hour=0.018,
                memory_cost_per_gb_per_hour=0.002,
            ),
            "onprem": ResourceCost(
                cpu_cost_per_core_per_hour=0.010,
                memory_cost_per_gb_per_hour=0.0015,
            ),
        }
        return pricing.get(cloud_provider, pricing["aws"])
