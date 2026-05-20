import logging
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from ..cloud_providers import BillingRecord
from ..config import Settings
from .dependency_checker import DependencyChecker

logger = logging.getLogger(__name__)


@dataclass
class OptimizationSuggestion:
    provider: str
    resource_id: str
    service_name: str
    suggestion_type: str
    current_cost: float
    estimated_savings: float
    savings_percentage: float
    description: str
    details: str
    priority: str
    can_release: bool = True
    risk_level: str = "low"
    dependent_resources: List[str] = field(default_factory=list)
    dependency_warnings: List[str] = field(default_factory=list)
    dependency_suggestions: List[str] = field(default_factory=list)


class ResourceOptimizer:
    """资源优化建议器"""

    def __init__(self, settings: Settings):
        self.settings = settings
        self.config = settings.optimization
        self.dependency_checker = DependencyChecker()

    def generate_all_suggestions(
        self,
        records: List[BillingRecord],
        resource_metrics: Optional[Dict[str, Dict[str, Any]]] = None,
    ) -> List[OptimizationSuggestion]:
        """生成所有优化建议"""
        suggestions = []

        idle_suggestions = self.detect_idle_resources(records, resource_metrics)
        suggestions.extend(idle_suggestions)

        ri_suggestions = self.suggest_reserved_instances(records)
        suggestions.extend(ri_suggestions)

        rightsize_suggestions = self.suggest_rightsizing(records, resource_metrics)
        suggestions.extend(rightsize_suggestions)

        storage_suggestions = self.optimize_storage_cost(records)
        suggestions.extend(storage_suggestions)

        return suggestions

    def detect_idle_resources(
        self,
        records: List[BillingRecord],
        resource_metrics: Optional[Dict[str, Dict[str, Any]]] = None,
    ) -> List[OptimizationSuggestion]:
        """检测闲置资源"""
        suggestions = []

        resource_costs = defaultdict(float)
        resource_info = {}

        for record in records:
            if not record.resource_id:
                continue
            resource_costs[record.resource_id] += record.pretax_amount
            resource_info[record.resource_id] = {
                "provider": record.provider,
                "service_name": record.service_name,
                "instance_type": record.instance_type,
            }

        for resource_id, total_cost in resource_costs.items():
            if total_cost < 10:
                continue

            info = resource_info[resource_id]
            is_idle = False
            idle_reason = ""

            metrics = resource_metrics.get(resource_id, {}) if resource_metrics else {}

            avg_cpu = metrics.get("avg_cpu_utilization")
            avg_network_in = metrics.get("avg_network_in")
            avg_network_out = metrics.get("avg_network_out")

            if avg_cpu is not None and avg_cpu < self.config.idle_cpu_threshold:
                is_idle = True
                idle_reason = f"平均CPU利用率仅 {avg_cpu:.1f}%，低于阈值 {self.config.idle_cpu_threshold}%"

            if avg_network_in is not None and avg_network_out is not None:
                total_network = avg_network_in + avg_network_out
                if total_network < self.config.idle_network_threshold:
                    is_idle = True
                    idle_reason = f"网络流量较低（{total_network:.0f} KB/s）"

            if not metrics and total_cost > 100:
                is_idle = True
                idle_reason = "无监控数据，建议检查资源使用情况"

            if is_idle:
                savings = total_cost * 0.9
                savings_pct = 90.0

                resource_type = self.dependency_checker._infer_resource_type(info["service_name"])
                dep_check = self.dependency_checker.can_release_resource(
                    resource_id, resource_type, [], records
                )

                details = f"{idle_reason}。建议终止或释放该资源，预计可节省 {savings:.2f} ({savings_pct:.0f}%)。"

                if not dep_check.can_release:
                    details += f" ⚠️ 警告：存在依赖资源：{', '.join(dep_check.dependent_resources)}"
                    if dep_check.warnings:
                        details += f" 风险提示：{'; '.join(dep_check.warnings)}"

                suggestions.append(OptimizationSuggestion(
                    provider=info["provider"],
                    resource_id=resource_id,
                    service_name=info["service_name"],
                    suggestion_type="idle_resource",
                    current_cost=total_cost,
                    estimated_savings=savings,
                    savings_percentage=savings_pct,
                    description=f"检测到闲置资源 {resource_id}",
                    details=details,
                    priority=self._calculate_priority(savings),
                    can_release=dep_check.can_release,
                    risk_level=dep_check.risk_level,
                    dependent_resources=dep_check.dependent_resources,
                    dependency_warnings=dep_check.warnings,
                    dependency_suggestions=dep_check.suggestions,
                ))

        return suggestions

    def suggest_reserved_instances(
        self,
        records: List[BillingRecord],
    ) -> List[OptimizationSuggestion]:
        """建议购买预留实例"""
        suggestions = []

        instance_type_costs = defaultdict(lambda: {
            "total_cost": 0.0,
            "running_hours": 0.0,
            "resource_ids": set(),
            "provider": "",
            "service_name": "",
            "os": "",
        })

        for record in records:
            if not record.instance_type:
                continue
            if not self._is_ri_eligible(record.service_name):
                continue

            key = (record.provider, record.instance_type, record.operating_system or "Linux")
            data = instance_type_costs[key]
            data["total_cost"] += record.pretax_amount
            data["running_hours"] += record.usage_amount
            data["resource_ids"].add(record.resource_id)
            data["provider"] = record.provider
            data["service_name"] = record.service_name
            data["os"] = record.operating_system or "Linux"

        for (provider, instance_type, os), data in instance_type_costs.items():
            if data["total_cost"] < 100:
                continue

            monthly_cost = data["total_cost"]
            ri_savings_pct = self._get_ri_discount(provider, instance_type)
            estimated_savings = monthly_cost * ri_savings_pct

            if estimated_savings >= self.config.ri_savings_threshold:
                resource_count = len(data["resource_ids"])
                suggestions.append(OptimizationSuggestion(
                    provider=provider,
                    resource_id=",".join(list(data["resource_ids"])[:5]),
                    service_name=data["service_name"],
                    suggestion_type="reserved_instance",
                    current_cost=monthly_cost,
                    estimated_savings=estimated_savings,
                    savings_percentage=ri_savings_pct * 100,
                    description=f"建议为 {instance_type} ({os}) 购买预留实例",
                    details=f"当前 {resource_count} 个实例月花费约 {monthly_cost:.2f}。"
                            f"购买 1 年期预留实例可节省约 {ri_savings_pct * 100:.0f}%，"
                            f"预计每月节省 {estimated_savings:.2f}。",
                    priority=self._calculate_priority(estimated_savings),
                ))

        return suggestions

    def suggest_rightsizing(
        self,
        records: List[BillingRecord],
        resource_metrics: Optional[Dict[str, Dict[str, Any]]] = None,
    ) -> List[OptimizationSuggestion]:
        """建议资源规格调整（升降配）"""
        suggestions = []

        if not resource_metrics:
            return suggestions

        resource_costs = defaultdict(float)
        resource_info = {}

        for record in records:
            if not record.resource_id:
                continue
            resource_costs[record.resource_id] += record.pretax_amount
            resource_info[record.resource_id] = {
                "provider": record.provider,
                "service_name": record.service_name,
                "instance_type": record.instance_type,
            }

        for resource_id, metrics in resource_metrics.items():
            avg_cpu = metrics.get("avg_cpu_utilization")
            max_cpu = metrics.get("max_cpu_utilization")

            if avg_cpu is None or max_cpu is None:
                continue

            total_cost = resource_costs.get(resource_id, 0)
            if total_cost < 50:
                continue

            info = resource_info.get(resource_id, {})

            if avg_cpu < 20 and max_cpu < 30:
                savings = total_cost * 0.5
                suggestions.append(OptimizationSuggestion(
                    provider=info.get("provider", ""),
                    resource_id=resource_id,
                    service_name=info.get("service_name", ""),
                    suggestion_type="downsize",
                    current_cost=total_cost,
                    estimated_savings=savings,
                    savings_percentage=50.0,
                    description=f"建议降配资源 {resource_id}",
                    details=f"平均CPU利用率 {avg_cpu:.1f}%，峰值 {max_cpu:.1f}%，"
                            f"资源利用率低。建议降配到下一规格，预计可节省 {savings:.2f}/月。",
                    priority=self._calculate_priority(savings),
                ))
            elif avg_cpu > 80 or max_cpu > 95:
                suggestions.append(OptimizationSuggestion(
                    provider=info.get("provider", ""),
                    resource_id=resource_id,
                    service_name=info.get("service_name", ""),
                    suggestion_type="upsize",
                    current_cost=total_cost,
                    estimated_savings=0,
                    savings_percentage=0,
                    description=f"建议升配资源 {resource_id}",
                    details=f"平均CPU利用率 {avg_cpu:.1f}%，峰值 {max_cpu:.1f}%，"
                            f"资源可能成为瓶颈。建议升配以保证服务稳定性。",
                    priority="medium",
                ))

        return suggestions

    def optimize_storage_cost(
        self,
        records: List[BillingRecord],
    ) -> List[OptimizationSuggestion]:
        """存储成本优化建议"""
        suggestions = []

        storage_costs = defaultdict(lambda: {
            "total_cost": 0.0,
            "provider": "",
            "service_name": "",
        })

        for record in records:
            if self._is_storage_service(record.service_name):
                storage_costs[record.service_name]["total_cost"] += record.pretax_amount
                storage_costs[record.service_name]["provider"] = record.provider
                storage_costs[record.service_name]["service_name"] = record.service_name

        for service_name, data in storage_costs.items():
            if data["total_cost"] < 200:
                continue

            estimated_savings = data["total_cost"] * 0.3
            suggestions.append(OptimizationSuggestion(
                provider=data["provider"],
                resource_id="",
                service_name=service_name,
                suggestion_type="storage_optimization",
                current_cost=data["total_cost"],
                estimated_savings=estimated_savings,
                savings_percentage=30.0,
                description=f"建议优化 {service_name} 存储成本",
                details=f"当前存储月花费 {data['total_cost']:.2f}。"
                        f"建议：1) 启用生命周期策略，将冷数据归档到低频存储；"
                        f"2) 清理无用数据；3) 启用智能分层。预计可节省约 30% ({estimated_savings:.2f}/月)。",
                priority=self._calculate_priority(estimated_savings),
            ))

        return suggestions

    def _is_ri_eligible(self, service_name: str) -> bool:
        """判断服务是否支持预留实例"""
        eligible_keywords = ["ECS", "EC2", "CVM", "RDS", "CDB", "Redis", "MongoDB"]
        return any(kw in service_name for kw in eligible_keywords)

    def _is_storage_service(self, service_name: str) -> bool:
        """判断是否为存储服务"""
        storage_keywords = ["S3", "OSS", "COS", "存储", "Storage", "EBS", "云盘"]
        return any(kw in service_name for kw in storage_keywords)

    def _get_ri_discount(self, provider: str, instance_type: str) -> float:
        """获取预留实例折扣率"""
        discounts = {
            "AWS": 0.40,
            "阿里云": 0.35,
            "腾讯云": 0.35,
        }
        return discounts.get(provider, 0.30)

    def _calculate_priority(self, estimated_savings: float) -> str:
        """根据预估节省金额计算优先级"""
        if estimated_savings >= 500:
            return "high"
        elif estimated_savings >= 200:
            return "medium"
        else:
            return "low"

    def calculate_total_savings(
        self,
        suggestions: List[OptimizationSuggestion],
    ) -> Dict[str, Any]:
        """计算总节省潜力"""
        total_savings = 0.0
        total_current_cost = 0.0
        type_savings = defaultdict(float)
        priority_counts = defaultdict(int)

        for suggestion in suggestions:
            total_savings += suggestion.estimated_savings
            total_current_cost += suggestion.current_cost
            type_savings[suggestion.suggestion_type] += suggestion.estimated_savings
            priority_counts[suggestion.priority] += 1

        overall_savings_pct = (total_savings / total_current_cost * 100) if total_current_cost > 0 else 0.0

        return {
            "total_suggestions": len(suggestions),
            "total_current_cost": total_current_cost,
            "total_estimated_savings": total_savings,
            "overall_savings_percentage": overall_savings_pct,
            "savings_by_type": dict(type_savings),
            "priority_counts": dict(priority_counts),
        }

    def suggestion_to_dict(self, suggestion: OptimizationSuggestion) -> Dict[str, Any]:
        """将建议对象转换为字典"""
        return {
            "provider": suggestion.provider,
            "resource_id": suggestion.resource_id,
            "service_name": suggestion.service_name,
            "suggestion_type": suggestion.suggestion_type,
            "current_cost": suggestion.current_cost,
            "estimated_savings": suggestion.estimated_savings,
            "savings_percentage": suggestion.savings_percentage,
            "description": suggestion.description,
            "details": suggestion.details,
            "priority": suggestion.priority,
            "can_release": suggestion.can_release,
            "risk_level": suggestion.risk_level,
            "dependent_resources": suggestion.dependent_resources,
            "dependency_warnings": suggestion.dependency_warnings,
            "dependency_suggestions": suggestion.dependency_suggestions,
        }
