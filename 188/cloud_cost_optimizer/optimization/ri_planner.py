import logging
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple
from collections import defaultdict

import numpy as np

from ..cloud_providers import BillingRecord
from ..config import Settings

logger = logging.getLogger(__name__)


@dataclass
class RIInstanceType:
    """RI实例类型配置"""
    provider: str
    instance_type: str
    instance_family: str
    operating_system: str
    region: str
    on_demand_price: float
    ri_1y_price: float
    ri_3y_price: float
    cpu: int
    memory: float


@dataclass
class RIRunningHours:
    """实例运行时长统计"""
    resource_id: str
    instance_type: str
    operating_system: str
    provider: str
    total_hours: float
    total_cost: float
    utilization_rate: float
    peak_usage_hours: float
    average_hours_per_day: float


@dataclass
class RIRecommendation:
    """RI购买建议"""
    provider: str
    instance_type: str
    operating_system: str
    recommendation_type: str
    quantity: int
    current_on_demand_cost: float
    estimated_ri_cost: float
    estimated_savings: float
    savings_percentage: float
    break_even_months: float
    utilization_threshold: float
    risk_level: str
    confidence: float
    instance_details: List[Dict[str, Any]]


@dataclass
class RIPlan:
    """完整的RI购买计划"""
    total_recommendations: int
    total_current_cost: float
    total_ri_cost: float
    total_savings: float
    overall_savings_percentage: float
    recommendations: List[RIRecommendation]
    risk_assessment: Dict[str, Any]
    implementation_plan: List[Dict[str, Any]]


class RIPlanner:
    """预留实例（RI）购买规划器"""

    # 云厂商RI定价配置（示例数据）
    RI_PRICING = {
        "AWS": {
            "t2.medium": RIInstanceType(
                provider="AWS", instance_type="t2.medium", instance_family="t2",
                operating_system="Linux", region="us-east-1",
                on_demand_price=0.0464, ri_1y_price=0.0269, ri_3y_price=0.0177,
                cpu=2, memory=4.0,
            ),
            "t3.medium": RIInstanceType(
                provider="AWS", instance_type="t3.medium", instance_family="t3",
                operating_system="Linux", region="us-east-1",
                on_demand_price=0.0416, ri_1y_price=0.024, ri_3y_price=0.0158,
                cpu=2, memory=4.0,
            ),
            "m5.large": RIInstanceType(
                provider="AWS", instance_type="m5.large", instance_family="m5",
                operating_system="Linux", region="us-east-1",
                on_demand_price=0.096, ri_1y_price=0.055, ri_3y_price=0.036,
                cpu=2, memory=8.0,
            ),
        },
        "阿里云": {
            "ecs.t6-c1m1.large": RIInstanceType(
                provider="阿里云", instance_type="ecs.t6-c1m1.large", instance_family="t6",
                operating_system="Linux", region="cn-hangzhou",
                on_demand_price=0.4, ri_1y_price=0.24, ri_3y_price=0.16,
                cpu=2, memory=2.0,
            ),
            "ecs.g6.large": RIInstanceType(
                provider="阿里云", instance_type="ecs.g6.large", instance_family="g6",
                operating_system="Linux", region="cn-hangzhou",
                on_demand_price=0.55, ri_1y_price=0.33, ri_3y_price=0.22,
                cpu=2, memory=8.0,
            ),
            "ecs.c6.large": RIInstanceType(
                provider="阿里云", instance_type="ecs.c6.large", instance_family="c6",
                operating_system="Linux", region="cn-hangzhou",
                on_demand_price=0.48, ri_1y_price=0.29, ri_3y_price=0.19,
                cpu=2, memory=4.0,
            ),
        },
        "腾讯云": {
            "S5.MEDIUM2": RIInstanceType(
                provider="腾讯云", instance_type="S5.MEDIUM2", instance_family="S5",
                operating_system="Linux", region="ap-shanghai",
                on_demand_price=0.3, ri_1y_price=0.18, ri_3y_price=0.12,
                cpu=2, memory=4.0,
            ),
            "S5.LARGE8": RIInstanceType(
                provider="腾讯云", instance_type="S5.LARGE8", instance_family="S5",
                operating_system="Linux", region="ap-shanghai",
                on_demand_price=0.5, ri_1y_price=0.3, ri_3y_price=0.2,
                cpu=4, memory=8.0,
            ),
            "M5.MEDIUM4": RIInstanceType(
                provider="腾讯云", instance_type="M5.MEDIUM4", instance_family="M5",
                operating_system="Linux", region="ap-shanghai",
                on_demand_price=0.35, ri_1y_price=0.21, ri_3y_price=0.14,
                cpu=2, memory=4.0,
            ),
        },
    }

    def __init__(self, settings: Settings):
        self.settings = settings
        self.min_utilization_threshold = 0.6
        self.min_savings_percentage = 0.15

    def analyze_instance_usage(
        self,
        records: List[BillingRecord],
        analysis_days: int = 60,
    ) -> List[RIRunningHours]:
        """分析实例使用情况"""
        instance_usage = defaultdict(lambda: {
            "hours": 0.0,
            "cost": 0.0,
            "days_active": set(),
            "provider": "",
            "operating_system": "",
        })

        cutoff_date = date.today() - timedelta(days=analysis_days)

        for record in records:
            if record.usage_start_date < cutoff_date:
                continue
            if not record.instance_type or not record.resource_id:
                continue

            instance_key = record.resource_id
            data = instance_usage[instance_key]
            data["hours"] += record.usage_amount
            data["cost"] += record.pretax_amount
            data["days_active"].add(record.usage_start_date)
            data["provider"] = record.provider
            data["instance_type"] = record.instance_type
            if record.operating_system:
                data["operating_system"] = record.operating_system

        results = []
        for instance_id, data in instance_usage.items():
            total_days = len(data["days_active"])
            total_hours = data["hours"]
            utilization_rate = total_hours / (analysis_days * 24)
            avg_hours_per_day = total_hours / total_days if total_days > 0 else 0

            results.append(RIRunningHours(
                resource_id=instance_id,
                instance_type=data.get("instance_type", ""),
                operating_system=data.get("operating_system", "Linux"),
                provider=data["provider"],
                total_hours=total_hours,
                total_cost=data["cost"],
                utilization_rate=utilization_rate,
                peak_usage_hours=total_hours / max(total_days, 1) * 1.5,
                average_hours_per_day=avg_hours_per_day,
            ))

        return results

    def group_instances_by_type(
        self,
        instances: List[RIRunningHours],
    ) -> Dict[str, List[RIRunningHours]]:
        """按实例类型分组"""
        grouped = defaultdict(list)
        for instance in instances:
            key = f"{instance.provider}|{instance.instance_type}|{instance.operating_system}"
            grouped[key].append(instance)
        return grouped

    def calculate_optimal_quantity(
        self,
        instances: List[RIRunningHours],
        ri_term: str = "1y",
    ) -> Dict[str, Any]:
        """计算最优购买数量"""
        if not instances:
            return None

        provider = instances[0].provider
        instance_type = instances[0].instance_type
        os = instances[0].operating_system

        total_instances = len(instances)
        total_on_demand_cost = sum(i.total_cost for i in instances)
        avg_utilization = np.mean([i.utilization_rate for i in instances])
        max_utilization = max([i.utilization_rate for i in instances])

        ri_pricing = self._get_ri_pricing(provider, instance_type, os)
        if ri_pricing is None:
            return None

        if ri_term == "1y":
            ri_price = ri_pricing.ri_1y_price
            discount_pct = 1 - (ri_price / ri_pricing.on_demand_price)
        else:
            ri_price = ri_pricing.ri_3y_price
            discount_pct = 1 - (ri_price / ri_pricing.on_demand_price)

        base_quantity = max(1, int(total_instances * avg_utilization))
        buffer_factor = 1.0 + max(0, 0.2 - (avg_utilization - 0.8))
        optimal_quantity = int(base_quantity * buffer_factor)
        optimal_quantity = max(1, min(optimal_quantity, total_instances))

        monthly_hours = 30 * 24
        current_monthly_cost = total_on_demand_cost / (len(instances[0].days_active) / 30) if hasattr(instances[0], 'days_active') else total_on_demand_cost

        current_monthly_cost = total_on_demand_cost / 2
        ri_monthly_cost = optimal_quantity * ri_price * monthly_hours
        estimated_savings = current_monthly_cost - ri_monthly_cost
        savings_percentage = (estimated_savings / current_monthly_cost * 100) if current_monthly_cost > 0 else 0

        if savings_percentage < self.min_savings_percentage * 100:
            return None

        risk_level = self._assess_risk(avg_utilization, optimal_quantity, total_instances)
        confidence = self._calculate_confidence(instances, avg_utilization)

        return {
            "provider": provider,
            "instance_type": instance_type,
            "operating_system": os,
            "total_instances": total_instances,
            "avg_utilization": avg_utilization,
            "max_utilization": max_utilization,
            "optimal_quantity": optimal_quantity,
            "current_monthly_cost": current_monthly_cost,
            "ri_monthly_cost": ri_monthly_cost,
            "estimated_savings": estimated_savings,
            "savings_percentage": savings_percentage,
            "discount_percentage": discount_pct * 100,
            "break_even_months": self._calculate_break_even(ri_pricing, ri_term),
            "risk_level": risk_level,
            "confidence": confidence,
            "instances": instances,
        }

    def generate_recommendations(
        self,
        records: List[BillingRecord],
        analysis_days: int = 60,
    ) -> RIPlan:
        """生成RI购买建议"""
        instances = self.analyze_instance_usage(records, analysis_days)
        eligible_instances = [i for i in instances if i.utilization_rate >= self.min_utilization_threshold]

        if not eligible_instances:
            return RIPlan(
                total_recommendations=0,
                total_current_cost=0,
                total_ri_cost=0,
                total_savings=0,
                overall_savings_percentage=0,
                recommendations=[],
                risk_assessment={"risk_level": "low", "message": "无符合条件的实例"},
                implementation_plan=[],
            )

        grouped = self.group_instances_by_type(eligible_instances)
        recommendations = []
        total_current_cost = 0
        total_ri_cost = 0
        total_savings = 0

        for key, instances in grouped.items():
            for ri_term in ["1y", "3y"]:
                analysis = self.calculate_optimal_quantity(instances, ri_term)
                if analysis is None:
                    continue

                recommendation = RIRecommendation(
                    provider=analysis["provider"],
                    instance_type=analysis["instance_type"],
                    operating_system=analysis["operating_system"],
                    recommendation_type=ri_term,
                    quantity=analysis["optimal_quantity"],
                    current_on_demand_cost=analysis["current_monthly_cost"],
                    estimated_ri_cost=analysis["ri_monthly_cost"],
                    estimated_savings=analysis["estimated_savings"],
                    savings_percentage=analysis["savings_percentage"],
                    break_even_months=analysis["break_even_months"],
                    utilization_threshold=analysis["avg_utilization"],
                    risk_level=analysis["risk_level"],
                    confidence=analysis["confidence"],
                    instance_details=[
                        {
                            "resource_id": i.resource_id,
                            "total_cost": i.total_cost,
                            "utilization_rate": i.utilization_rate,
                            "average_hours_per_day": i.average_hours_per_day,
                        }
                        for i in instances
                    ],
                )
                recommendations.append(recommendation)
                total_current_cost += analysis["current_monthly_cost"]
                total_ri_cost += analysis["ri_monthly_cost"]
                total_savings += analysis["estimated_savings"]

        recommendations.sort(key=lambda x: x.estimated_savings, reverse=True)

        overall_savings_pct = (total_savings / total_current_cost * 100) if total_current_cost > 0 else 0

        risk_assessment = self._assess_overall_risk(recommendations)
        implementation_plan = self._generate_implementation_plan(recommendations)

        return RIPlan(
            total_recommendations=len(recommendations),
            total_current_cost=total_current_cost,
            total_ri_cost=total_ri_cost,
            total_savings=total_savings,
            overall_savings_percentage=overall_savings_pct,
            recommendations=recommendations,
            risk_assessment=risk_assessment,
            implementation_plan=implementation_plan,
        )

    def _get_ri_pricing(
        self,
        provider: str,
        instance_type: str,
        operating_system: str,
    ) -> Optional[RIInstanceType]:
        """获取RI定价信息"""
        if provider in self.RI_PRICING:
            if instance_type in self.RI_PRICING[provider]:
                return self.RI_PRICING[provider][instance_type]

        for prov, pricing in self.RI_PRICING.items():
            for itype, info in pricing.items():
                if info.instance_family.lower() in instance_type.lower():
                    return info

        default_pricing = list(self.RI_PRICING.get(provider, {}).values())
        if default_pricing:
            return default_pricing[0]

        return RIInstanceType(
            provider=provider,
            instance_type=instance_type,
            instance_family="general",
            operating_system=operating_system or "Linux",
            region="cn-shanghai",
            on_demand_price=0.5,
            ri_1y_price=0.3,
            ri_3y_price=0.2,
            cpu=2,
            memory=4.0,
        )

    def _calculate_break_even(
        self,
        pricing: RIInstanceType,
        ri_term: str,
    ) -> float:
        """计算回本周期"""
        if ri_term == "1y":
            upfront_cost = pricing.ri_1y_price * 12 * 30 * 24
        else:
            upfront_cost = pricing.ri_3y_price * 36 * 30 * 24

        monthly_savings = (pricing.on_demand_price - pricing.ri_1y_price) * 30 * 24
        if monthly_savings <= 0:
            return float("inf")

        return upfront_cost / monthly_savings / 30

    def _assess_risk(
        self,
        avg_utilization: float,
        quantity: int,
        total_instances: int,
    ) -> str:
        """评估风险等级"""
        coverage_ratio = quantity / total_instances if total_instances > 0 else 0

        if avg_utilization >= 0.9 and coverage_ratio <= 0.8:
            return "low"
        elif avg_utilization >= 0.7 and coverage_ratio <= 0.9:
            return "medium"
        else:
            return "high"

    def _calculate_confidence(
        self,
        instances: List[RIRunningHours],
        avg_utilization: float,
    ) -> float:
        """计算置信度"""
        if len(instances) < 3:
            return 0.6

        utilization_std = np.std([i.utilization_rate for i in instances])
        if utilization_std < 0.1:
            base_confidence = 0.9
        elif utilization_std < 0.2:
            base_confidence = 0.8
        else:
            base_confidence = 0.7

        days_factor = min(1.0, len(instances) * 0.1)
        return min(0.95, base_confidence * (0.8 + days_factor * 0.2))

    def _assess_overall_risk(
        self,
        recommendations: List[RIRecommendation],
    ) -> Dict[str, Any]:
        """评估整体风险"""
        if not recommendations:
            return {"risk_level": "low", "message": "无推荐"}

        high_risk = sum(1 for r in recommendations if r.risk_level == "high")
        total_investment = sum(r.estimated_ri_cost * 12 for r in recommendations)

        if high_risk > len(recommendations) * 0.5 or total_investment > 100000:
            risk_level = "high"
        elif high_risk > 0 or total_investment > 50000:
            risk_level = "medium"
        else:
            risk_level = "low"

        return {
            "risk_level": risk_level,
            "high_risk_count": high_risk,
            "total_investment": total_investment,
            "message": f"整体风险等级: {risk_level}",
        }

    def _generate_implementation_plan(
        self,
        recommendations: List[RIRecommendation],
    ) -> List[Dict[str, Any]]:
        """生成实施计划"""
        plan = []

        sorted_recommendations = sorted(
            recommendations,
            key=lambda x: (x.risk_level == "high", -x.savings_percentage),
        )

        for i, rec in enumerate(sorted_recommendations, 1):
            plan.append({
                "step": i,
                "action": f"购买 {rec.quantity} 个 {rec.provider} {rec.instance_type} {rec.recommendation_type} RI",
                "priority": "high" if rec.risk_level == "low" else "medium" if rec.risk_level == "medium" else "low",
                "estimated_cost": f"¥{rec.estimated_ri_cost * 12:,.2f}/年",
                "estimated_savings": f"¥{rec.estimated_savings * 12:,.2f}/年",
                "roi": f"{rec.savings_percentage:.1f}%",
                "break_even": f"{rec.break_even_months:.1f} 个月",
                "notes": self._generate_recommendation_notes(rec),
            })

        return plan

    def _generate_recommendation_notes(self, rec: RIRecommendation) -> str:
        """生成建议备注"""
        notes = []
        if rec.risk_level == "high":
            notes.append("建议先购买1-2个试用，确认使用情况后再扩大")
        elif rec.risk_level == "medium":
            notes.append("建议分阶段购买，先覆盖50%的实例")
        else:
            notes.append("可以一次性购买，风险较低")

        if rec.confidence < 0.7:
            notes.append("数据周期较短，建议持续观察后再决策")

        if rec.utilization_threshold < 0.7:
            notes.append("部分实例利用率较低，建议先优化后再购买")

        return "; ".join(notes) if notes else "可以直接购买"

    def recommendation_to_dict(self, rec: RIRecommendation) -> Dict[str, Any]:
        """将建议转换为字典"""
        return {
            "provider": rec.provider,
            "instance_type": rec.instance_type,
            "operating_system": rec.operating_system,
            "recommendation_type": rec.recommendation_type,
            "quantity": rec.quantity,
            "current_on_demand_cost": rec.current_on_demand_cost,
            "estimated_ri_cost": rec.estimated_ri_cost,
            "estimated_savings": rec.estimated_savings,
            "savings_percentage": rec.savings_percentage,
            "break_even_months": rec.break_even_months,
            "utilization_threshold": rec.utilization_threshold,
            "risk_level": rec.risk_level,
            "confidence": rec.confidence,
            "instance_details": rec.instance_details,
        }

    def plan_to_dict(self, plan: RIPlan) -> Dict[str, Any]:
        """将计划转换为字典"""
        return {
            "total_recommendations": plan.total_recommendations,
            "total_current_cost": plan.total_current_cost,
            "total_ri_cost": plan.total_ri_cost,
            "total_savings": plan.total_savings,
            "overall_savings_percentage": plan.overall_savings_percentage,
            "recommendations": [self.recommendation_to_dict(r) for r in plan.recommendations],
            "risk_assessment": plan.risk_assessment,
            "implementation_plan": plan.implementation_plan,
        }
