import logging
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from ..cloud_providers import BillingRecord
from ..config import Settings

logger = logging.getLogger(__name__)


@dataclass
class TrendMetrics:
    period: date
    total_cost: float
    previous_period_cost: float
    change_percentage: float
    moving_average: float
    cumulative_cost: float


class TrendAnalyzer:
    """费用趋势分析器"""

    def __init__(self, settings: Settings):
        self.settings = settings

    def calculate_daily_trend(
        self,
        records: List[BillingRecord],
    ) -> List[Dict[str, Any]]:
        """计算每日费用趋势"""
        daily_costs = defaultdict(float)
        for record in records:
            daily_costs[record.usage_start_date] += record.pretax_amount

        dates = sorted(daily_costs.keys())
        if not dates:
            return []

        costs = [daily_costs[d] for d in dates]
        moving_avg = self._calculate_moving_average(costs, window=7)
        cumulative = np.cumsum(costs).tolist()

        trend_data = []
        for i, d in enumerate(dates):
            prev_cost = costs[i - 1] if i > 0 else 0.0
            change_pct = ((costs[i] - prev_cost) / prev_cost * 100) if prev_cost > 0 else 0.0

            trend_data.append({
                "date": d,
                "total_cost": costs[i],
                "previous_day_cost": prev_cost,
                "change_percentage": change_pct,
                "moving_average_7d": moving_avg[i],
                "cumulative_cost": cumulative[i],
            })

        return trend_data

    def calculate_service_trend(
        self,
        records: List[BillingRecord],
        top_n: int = 10,
    ) -> Dict[str, List[Dict[str, Any]]]:
        """按服务计算费用趋势"""
        service_daily = defaultdict(lambda: defaultdict(float))
        for record in records:
            service_daily[record.service_name][record.usage_start_date] += record.pretax_amount

        service_totals = {
            service: sum(costs.values())
            for service, costs in service_daily.items()
        }
        top_services = sorted(
            service_totals.items(),
            key=lambda x: x[1],
            reverse=True
        )[:top_n]

        results = {}
        for service, _ in top_services:
            daily = service_daily[service]
            dates = sorted(daily.keys())
            costs = [daily[d] for d in dates]
            moving_avg = self._calculate_moving_average(costs, window=7)

            trend_data = []
            for i, d in enumerate(dates):
                prev_cost = costs[i - 1] if i > 0 else 0.0
                change_pct = ((costs[i] - prev_cost) / prev_cost * 100) if prev_cost > 0 else 0.0

                trend_data.append({
                    "date": d,
                    "total_cost": costs[i],
                    "previous_day_cost": prev_cost,
                    "change_percentage": change_pct,
                    "moving_average_7d": moving_avg[i],
                })

            results[service] = trend_data

        return results

    def calculate_monthly_summary(
        self,
        records: List[BillingRecord],
    ) -> List[Dict[str, Any]]:
        """计算月度费用汇总"""
        monthly_costs = defaultdict(float)
        for record in records:
            month_key = record.usage_start_date.replace(day=1)
            monthly_costs[month_key] += record.pretax_amount

        months = sorted(monthly_costs.keys())
        if not months:
            return []

        results = []
        for i, month in enumerate(months):
            prev_cost = monthly_costs[months[i - 1]] if i > 0 else 0.0
            change_pct = ((monthly_costs[month] - prev_cost) / prev_cost * 100) if prev_cost > 0 else 0.0

            results.append({
                "month": month,
                "total_cost": monthly_costs[month],
                "previous_month_cost": prev_cost,
                "change_percentage": change_pct,
            })

        return results

    def calculate_growth_rate(
        self,
        records: List[BillingRecord],
        days: int = 30,
    ) -> Dict[str, Any]:
        """计算增长率"""
        today = date.today()
        current_start = today - timedelta(days=days)
        previous_start = current_start - timedelta(days=days)

        current_cost = sum(
            r.pretax_amount for r in records
            if r.usage_start_date >= current_start and r.usage_start_date < today
        )
        previous_cost = sum(
            r.pretax_amount for r in records
            if r.usage_start_date >= previous_start and r.usage_start_date < current_start
        )

        growth_rate = ((current_cost - previous_cost) / previous_cost * 100) if previous_cost > 0 else 0.0

        return {
            "period_days": days,
            "current_period_cost": current_cost,
            "previous_period_cost": previous_cost,
            "growth_rate": growth_rate,
            "is_growing": growth_rate > 0,
        }

    def forecast_next_month(
        self,
        records: List[BillingRecord],
    ) -> Dict[str, Any]:
        """预测下月费用"""
        daily_costs = defaultdict(float)
        for record in records:
            daily_costs[record.usage_start_date] += record.pretax_amount

        if not daily_costs:
            return {"forecast": 0.0, "confidence": 0.0}

        dates = sorted(daily_costs.keys())
        costs = [daily_costs[d] for d in dates]

        if len(costs) < 7:
            avg = np.mean(costs)
            forecast = avg * 30
            confidence = 0.5
        else:
            recent_avg = np.mean(costs[-7:])
            month_avg = np.mean(costs[-30:]) if len(costs) >= 30 else np.mean(costs)
            trend = (recent_avg - month_avg) / month_avg if month_avg > 0 else 0
            forecast = recent_avg * 30 * (1 + trend * 0.5)
            confidence = min(0.9, 0.5 + len(costs) * 0.01)

        return {
            "forecast": float(forecast),
            "confidence": float(confidence),
            "method": "moving_average" if len(costs) >= 7 else "simple_average",
            "days_used": min(len(costs), 90),
        }

    def _calculate_moving_average(
        self,
        values: List[float],
        window: int = 7,
    ) -> List[float]:
        """计算移动平均值"""
        if not values:
            return []

        result = []
        for i in range(len(values)):
            start = max(0, i - window + 1)
            window_values = values[start:i + 1]
            result.append(float(np.mean(window_values)))

        return result

    def compare_periods(
        self,
        records: List[BillingRecord],
        period1_start: date,
        period1_end: date,
        period2_start: date,
        period2_end: date,
    ) -> Dict[str, Any]:
        """比较两个时期的费用"""
        period1_cost = sum(
            r.pretax_amount for r in records
            if r.usage_start_date >= period1_start and r.usage_start_date < period1_end
        )
        period2_cost = sum(
            r.pretax_amount for r in records
            if r.usage_start_date >= period2_start and r.usage_start_date < period2_end
        )

        change_amount = period2_cost - period1_cost
        change_pct = (change_amount / period1_cost * 100) if period1_cost > 0 else 0.0

        period1_services = defaultdict(float)
        period2_services = defaultdict(float)
        for r in records:
            if r.usage_start_date >= period1_start and r.usage_start_date < period1_end:
                period1_services[r.service_name] += r.pretax_amount
            if r.usage_start_date >= period2_start and r.usage_start_date < period2_end:
                period2_services[r.service_name] += r.pretax_amount

        service_changes = []
        all_services = set(period1_services.keys()) | set(period2_services.keys())
        for service in all_services:
            p1 = period1_services.get(service, 0)
            p2 = period2_services.get(service, 0)
            change = p2 - p1
            change_pct_s = (change / p1 * 100) if p1 > 0 else 0.0
            service_changes.append({
                "service_name": service,
                "period1_cost": p1,
                "period2_cost": p2,
                "change_amount": change,
                "change_percentage": change_pct_s,
            })

        service_changes.sort(key=lambda x: abs(x["change_amount"]), reverse=True)

        return {
            "period1": {
                "start": period1_start,
                "end": period1_end,
                "total_cost": period1_cost,
            },
            "period2": {
                "start": period2_start,
                "end": period2_end,
                "total_cost": period2_cost,
            },
            "change_amount": change_amount,
            "change_percentage": change_pct,
            "top_service_changes": service_changes[:10],
        }
