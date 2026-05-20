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
class Budget:
    """预算定义"""
    budget_id: str
    name: str
    amount: float
    currency: str = "CNY"
    period: str = "monthly"
    scope: Dict[str, Any] = field(default_factory=dict)
    alert_thresholds: List[float] = field(default_factory=lambda: [80.0, 90.0, 100.0])
    alert_channels: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    is_active: bool = True


@dataclass
class BudgetAlert:
    """预算告警"""
    budget_id: str
    budget_name: str
    alert_type: str
    current_spend: float
    budget_amount: float
    percentage: float
    threshold: float
    message: str
    severity: str
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class BudgetForecast:
    """预算预测"""
    budget_id: str
    budget_name: str
    budget_amount: float
    forecasted_spend: float
    forecast_confidence: float
    projected_overage: float
    overage_percentage: float
    projection_period: str
    trend: str


class BudgetManager:
    """预算管理器"""

    def __init__(self, settings: Settings):
        self.settings = settings
        self.budgets: Dict[str, Budget] = {}
        self._init_default_budgets()

    def _init_default_budgets(self):
        """初始化默认预算"""
        default_budget = Budget(
            budget_id="default_total",
            name="总月度预算",
            amount=10000.0,
            currency=self.settings.currency,
            period="monthly",
            alert_thresholds=[70.0, 90.0, 100.0, 120.0],
        )
        self.budgets[default_budget.budget_id] = default_budget

    def create_budget(
        self,
        name: str,
        amount: float,
        period: str = "monthly",
        currency: Optional[str] = None,
        scope: Optional[Dict[str, Any]] = None,
        alert_thresholds: Optional[List[float]] = None,
    ) -> Budget:
        """创建新预算"""
        budget_id = f"budget_{len(self.budgets) + 1}"
        budget = Budget(
            budget_id=budget_id,
            name=name,
            amount=amount,
            currency=currency or self.settings.currency,
            period=period,
            scope=scope or {},
            alert_thresholds=alert_thresholds or [70.0, 90.0, 100.0, 120.0],
        )
        self.budgets[budget_id] = budget
        logger.info(f"Created budget: {name} (¥{amount})")
        return budget

    def update_budget(
        self,
        budget_id: str,
        amount: Optional[float] = None,
        name: Optional[str] = None,
        alert_thresholds: Optional[List[float]] = None,
        is_active: Optional[bool] = None,
    ) -> Optional[Budget]:
        """更新预算"""
        if budget_id not in self.budgets:
            logger.warning(f"Budget not found: {budget_id}")
            return None

        budget = self.budgets[budget_id]
        if amount is not None:
            budget.amount = amount
        if name is not None:
            budget.name = name
        if alert_thresholds is not None:
            budget.alert_thresholds = sorted(alert_thresholds)
        if is_active is not None:
            budget.is_active = is_active

        logger.info(f"Updated budget: {budget.name}")
        return budget

    def delete_budget(self, budget_id: str) -> bool:
        """删除预算"""
        if budget_id in self.budgets:
            del self.budgets[budget_id]
            logger.info(f"Deleted budget: {budget_id}")
            return True
        return False

    def get_budget(self, budget_id: str) -> Optional[Budget]:
        """获取预算"""
        return self.budgets.get(budget_id)

    def list_budgets(self, include_inactive: bool = False) -> List[Budget]:
        """列出所有预算"""
        budgets = list(self.budgets.values())
        if not include_inactive:
            budgets = [b for b in budgets if b.is_active]
        return budgets

    def calculate_spend(
        self,
        records: List[BillingRecord],
        period_start: Optional[date] = None,
        period_end: Optional[date] = None,
        scope: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """计算指定时间段的支出"""
        if period_start is None:
            today = date.today()
            period_start = today.replace(day=1)
        if period_end is None:
            period_end = date.today() + timedelta(days=1)

        period_records = [
            r for r in records
            if period_start <= r.usage_start_date < period_end
        ]

        if scope:
            if "providers" in scope:
                period_records = [r for r in period_records if r.provider in scope["providers"]]
            if "services" in scope:
                period_records = [r for r in period_records if r.service_name in scope["services"]]
            if "tags" in scope:
                period_records = [
                    r for r in period_records
                    if any(
                        r.tags.get(k) == v for k, v in scope["tags"].items()
                    )
                ]

        daily_spend = defaultdict(float)
        provider_spend = defaultdict(float)
        service_spend = defaultdict(float)

        for record in period_records:
            day = record.usage_start_date.isoformat()
            daily_spend[day] += record.pretax_amount
            provider_spend[record.provider] += record.pretax_amount
            service_spend[record.service_name] += record.pretax_amount

        total_spend = sum(r.pretax_amount for r in period_records)
        days_elapsed = (date.today() - period_start).days + 1
        days_in_period = (period_end - period_start).days

        return {
            "total_spend": total_spend,
            "daily_spend": dict(daily_spend),
            "provider_spend": dict(provider_spend),
            "service_spend": dict(service_spend),
            "days_elapsed": days_elapsed,
            "days_in_period": days_in_period,
            "record_count": len(period_records),
            "period_start": period_start.isoformat(),
            "period_end": period_end.isoformat(),
        }

    def check_budgets(
        self,
        records: List[BillingRecord],
    ) -> List[BudgetAlert]:
        """检查所有预算，生成告警"""
        alerts = []

        today = date.today()
        period_start = today.replace(day=1)
        period_end = self._get_month_end(today)

        for budget in self.budgets.values():
            if not budget.is_active:
                continue

            spend = self.calculate_spend(
                records, period_start, period_end, budget.scope
            )
            percentage = (spend["total_spend"] / budget.amount * 100) if budget.amount > 0 else 0

            budget_alerts = self._generate_alerts(
                budget, spend["total_spend"], percentage
            )
            alerts.extend(budget_alerts)

        return alerts

    def _generate_alerts(
        self,
        budget: Budget,
        current_spend: float,
        percentage: float,
    ) -> List[BudgetAlert]:
        """根据预算阈值生成告警"""
        alerts = []
        thresholds = sorted(budget.alert_thresholds, reverse=True)

        triggered_threshold = None
        for threshold in thresholds:
            if percentage >= threshold:
                triggered_threshold = threshold
                break

        if triggered_threshold is not None:
            if percentage >= 120:
                severity = "critical"
                alert_type = "budget_critical"
                message = f"预算严重超支！当前支出已达预算的 {percentage:.1f}%"
            elif percentage >= 100:
                severity = "high"
                alert_type = "budget_over"
                message = f"预算已超支！当前支出 {current_spend:.2f}，预算 {budget.amount:.2f}"
            elif percentage >= 90:
                severity = "medium"
                alert_type = "budget_warning"
                message = f"预算即将用尽！已使用 {percentage:.1f}%"
            elif percentage >= 70:
                severity = "low"
                alert_type = "budget_notice"
                message = f"预算已使用 {percentage:.1f}%，请注意控制成本"
            else:
                severity = "info"
                alert_type = "budget_info"
                message = f"预算使用正常，已使用 {percentage:.1f}%"

            alerts.append(BudgetAlert(
                budget_id=budget.budget_id,
                budget_name=budget.name,
                alert_type=alert_type,
                current_spend=current_spend,
                budget_amount=budget.amount,
                percentage=percentage,
                threshold=triggered_threshold,
                message=message,
                severity=severity,
            ))

        return alerts

    def forecast_budget_spend(
        self,
        records: List[BillingRecord],
        budget: Budget,
    ) -> BudgetForecast:
        """预测预算周期内的总支出"""
        today = date.today()
        period_start = today.replace(day=1)
        period_end = self._get_month_end(today)

        spend = self.calculate_spend(records, period_start, period_end, budget.scope)

        daily_costs = list(spend["daily_spend"].values())
        if len(daily_costs) < 3:
            forecasted_spend = spend["total_spend"]
            confidence = 0.5
        else:
            avg_daily = np.mean(daily_costs[-7:]) if len(daily_costs) >= 7 else np.mean(daily_costs)
            remaining_days = (period_end - today).days
            forecasted_spend = spend["total_spend"] + avg_daily * remaining_days
            confidence = min(0.9, 0.5 + len(daily_costs) * 0.03)

        projected_overage = max(0, forecasted_spend - budget.amount)
        overage_percentage = (projected_overage / budget.amount * 100) if budget.amount > 0 else 0

        if forecasted_spend > budget.amount * 1.1:
            trend = "high_growth"
        elif forecasted_spend > budget.amount:
            trend = "over_budget"
        elif forecasted_spend > budget.amount * 0.9:
            trend = "approaching"
        else:
            trend = "normal"

        return BudgetForecast(
            budget_id=budget.budget_id,
            budget_name=budget.name,
            budget_amount=budget.amount,
            forecasted_spend=forecasted_spend,
            forecast_confidence=confidence,
            projected_overage=projected_overage,
            overage_percentage=overage_percentage,
            projection_period=f"{period_start} ~ {period_end}",
            trend=trend,
        )

    def get_budget_dashboard(
        self,
        records: List[BillingRecord],
    ) -> Dict[str, Any]:
        """获取预算仪表板数据"""
        today = date.today()
        period_start = today.replace(day=1)
        period_end = self._get_month_end(today)

        total_spend_data = self.calculate_spend(records, period_start, period_end)

        budgets_data = []
        alerts = self.check_budgets(records)

        for budget in self.list_budgets():
            spend = self.calculate_spend(records, period_start, period_end, budget.scope)
            forecast = self.forecast_budget_spend(records, budget)
            percentage = (spend["total_spend"] / budget.amount * 100) if budget.amount > 0 else 0

            budgets_data.append({
                "budget_id": budget.budget_id,
                "name": budget.name,
                "amount": budget.amount,
                "current_spend": spend["total_spend"],
                "percentage": percentage,
                "forecasted_spend": forecast.forecasted_spend,
                "projected_overage": forecast.projected_overage,
                "trend": forecast.trend,
                "days_elapsed": spend["days_elapsed"],
                "days_in_period": spend["days_in_period"],
                "daily_avg": spend["total_spend"] / spend["days_elapsed"] if spend["days_elapsed"] > 0 else 0,
            })

        critical_alerts = [a for a in alerts if a.severity == "critical"]
        high_alerts = [a for a in alerts if a.severity == "high"]
        medium_alerts = [a for a in alerts if a.severity == "medium"]

        return {
            "period": {
                "start": period_start.isoformat(),
                "end": period_end.isoformat(),
                "days_elapsed": (today - period_start).days + 1,
                "days_remaining": (period_end - today).days,
            },
            "total_spend": total_spend_data["total_spend"],
            "provider_breakdown": total_spend_data["provider_spend"],
            "service_breakdown": total_spend_data["service_spend"],
            "budgets": budgets_data,
            "alerts": {
                "total": len(alerts),
                "critical": len(critical_alerts),
                "high": len(high_alerts),
                "medium": len(medium_alerts),
                "list": [self._alert_to_dict(a) for a in alerts],
            },
        }

    def _get_month_end(self, d: date) -> date:
        """获取当月最后一天"""
        if d.month == 12:
            return date(d.year + 1, 1, 1)
        return date(d.year, d.month + 1, 1)

    def _alert_to_dict(self, alert: BudgetAlert) -> Dict[str, Any]:
        """将告警转换为字典"""
        return {
            "budget_id": alert.budget_id,
            "budget_name": alert.budget_name,
            "alert_type": alert.alert_type,
            "current_spend": alert.current_spend,
            "budget_amount": alert.budget_amount,
            "percentage": alert.percentage,
            "threshold": alert.threshold,
            "message": alert.message,
            "severity": alert.severity,
            "created_at": alert.created_at.isoformat(),
        }

    def generate_budget_report(
        self,
        records: List[BillingRecord],
        output_format: str = "dict",
    ) -> Any:
        """生成预算报告"""
        dashboard = self.get_budget_dashboard(records)

        if output_format == "dict":
            return dashboard
        elif output_format == "text":
            return self._generate_text_report(dashboard)
        else:
            return dashboard

    def _generate_text_report(self, dashboard: Dict[str, Any]) -> str:
        """生成文本格式的预算报告"""
        lines = []
        lines.append("=" * 60)
        lines.append("📊 预算执行报告")
        lines.append("=" * 60)

        period = dashboard["period"]
        lines.append(f"\n统计周期: {period['start']} ~ {period['end']}")
        lines.append(f"已过天数: {period['days_elapsed']} 天")
        lines.append(f"剩余天数: {period['days_remaining']} 天")

        lines.append(f"\n💰 本月总支出: ¥{dashboard['total_spend']:,.2f}")

        lines.append("\n📋 预算执行情况:")
        for budget in dashboard["budgets"]:
            status_icon = "🔴" if budget["percentage"] >= 100 else "🟡" if budget["percentage"] >= 90 else "🟢"
            lines.append(f"\n{status_icon} {budget['name']}")
            lines.append(f"   预算金额: ¥{budget['amount']:,.2f}")
            lines.append(f"   已使用: ¥{budget['current_spend']:,.2f} ({budget['percentage']:.1f}%)")
            lines.append(f"   预测支出: ¥{budget['forecasted_spend']:,.2f}")
            if budget["projected_overage"] > 0:
                lines.append(f"   ⚠️ 预计超支: ¥{budget['projected_overage']:,.2f}")

        if dashboard["alerts"]["total"] > 0:
            lines.append(f"\n⚠️ 告警信息 ({dashboard['alerts']['total']} 条):")
            for alert in dashboard["alerts"]["list"]:
                severity_icon = {"critical": "🔴", "high": "🟠", "medium": "🟡", "low": "🟢", "info": "🔵"}[alert["severity"]]
                lines.append(f"   {severity_icon} {alert['message']}")

        lines.append("\n" + "=" * 60)
        return "\n".join(lines)
