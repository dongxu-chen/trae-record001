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
class CostAnomaly:
    provider: str
    service_name: str
    resource_id: str
    anomaly_date: date
    expected_cost: float
    actual_cost: float
    percentage_change: float
    severity: str
    anomaly_type: str
    description: str
    has_periodicity: bool = False
    periodicity_type: str = ""


class AnomalyDetector:
    """异常费用检测器 - 使用3-Sigma原则，支持周期性模式检测"""

    def __init__(self, settings: Settings):
        self.settings = settings
        self.config = settings.anomaly_detection
        self.config.threshold_std = 3.0

    def detect_anomalies(
        self,
        records: List[BillingRecord],
    ) -> List[CostAnomaly]:
        """检测所有异常"""
        anomalies = []

        daily_anomalies = self._detect_daily_spikes(records)
        anomalies.extend(daily_anomalies)

        service_anomalies = self._detect_service_level_anomalies(records)
        anomalies.extend(service_anomalies)

        resource_anomalies = self._detect_resource_level_anomalies(records)
        anomalies.extend(resource_anomalies)

        periodicity_anomalies = self._detect_periodicity_break(records)
        anomalies.extend(periodicity_anomalies)

        return anomalies

    def _detect_daily_spikes(
        self,
        records: List[BillingRecord],
    ) -> List[CostAnomaly]:
        """检测每日费用突增 - 使用3-Sigma"""
        anomalies = []

        daily_costs = defaultdict(float)
        for record in records:
            daily_costs[record.usage_start_date] += record.pretax_amount

        dates = sorted(daily_costs.keys())
        if len(dates) < self.config.min_days_for_baseline:
            return anomalies

        costs = np.array([daily_costs[d] for d in dates])

        periodicity = self._detect_periodicity(costs)
        adjusted_costs = self._remove_periodicity(costs, periodicity)

        for i in range(self.config.min_days_for_baseline, len(dates)):
            baseline = adjusted_costs[max(0, i - self.config.min_days_for_baseline):i]
            mean = np.mean(baseline)
            std = np.std(baseline)

            threshold = mean + self.config.threshold_std * std
            actual = adjusted_costs[i]

            if std > 0 and actual > threshold:
                original_actual = costs[i]
                pct_change = ((original_actual - mean) / mean * 100) if mean > 0 else 0

                if pct_change >= self.config.min_percentage_change:
                    severity = self._calculate_severity(pct_change)
                    anomalies.append(CostAnomaly(
                        provider="all",
                        service_name="total",
                        resource_id="",
                        anomaly_date=dates[i],
                        expected_cost=float(mean),
                        actual_cost=float(original_actual),
                        percentage_change=float(pct_change),
                        severity=severity,
                        anomaly_type="daily_spike",
                        description=f"整体日费用较预期增加 {pct_change:.1f}%，预期 {mean:.2f}，实际 {original_actual:.2f}",
                        has_periodicity=periodicity["found"],
                        periodicity_type=periodicity["type"],
                    ))

        return anomalies

    def _detect_service_level_anomalies(
        self,
        records: List[BillingRecord],
    ) -> List[CostAnomaly]:
        """检测服务级别的异常 - 使用3-Sigma"""
        anomalies = []

        service_daily = defaultdict(lambda: defaultdict(float))

        for record in records:
            service_daily[record.service_name][record.usage_start_date] += record.pretax_amount

        for service, daily_costs in service_daily.items():
            dates = sorted(daily_costs.keys())
            if len(dates) < self.config.min_days_for_baseline:
                continue

            costs = np.array([daily_costs[d] for d in dates])
            periodicity = self._detect_periodicity(costs)
            adjusted_costs = self._remove_periodicity(costs, periodicity)

            for i in range(self.config.min_days_for_baseline, len(dates)):
                baseline = adjusted_costs[max(0, i - self.config.min_days_for_baseline):i]
                mean = np.mean(baseline)
                std = np.std(baseline)

                threshold = mean + self.config.threshold_std * std
                actual = adjusted_costs[i]

                if std > 0 and actual > threshold:
                    original_actual = costs[i]
                    pct_change = ((original_actual - mean) / mean * 100) if mean > 0 else 0

                    if pct_change >= self.config.min_percentage_change:
                        severity = self._calculate_severity(pct_change)
                        anomalies.append(CostAnomaly(
                            provider="all",
                            service_name=service,
                            resource_id="",
                            anomaly_date=dates[i],
                            expected_cost=float(mean),
                            actual_cost=float(original_actual),
                            percentage_change=float(pct_change),
                            severity=severity,
                            anomaly_type="service_spike",
                            description=f"{service} 日费用较预期增加 {pct_change:.1f}%",
                            has_periodicity=periodicity["found"],
                            periodicity_type=periodicity["type"],
                        ))

        return anomalies

    def _detect_resource_level_anomalies(
        self,
        records: List[BillingRecord],
    ) -> List[CostAnomaly]:
        """检测资源级别的异常 - 使用3-Sigma"""
        anomalies = []

        resource_daily = defaultdict(lambda: {
            "daily_costs": defaultdict(float),
            "provider": "",
            "service": "",
        })

        for record in records:
            if not record.resource_id:
                continue
            resource_daily[record.resource_id]["daily_costs"][record.usage_start_date] += record.pretax_amount
            resource_daily[record.resource_id]["provider"] = record.provider
            resource_daily[record.resource_id]["service"] = record.service_name

        for resource_id, data in resource_daily.items():
            daily_costs = data["daily_costs"]
            dates = sorted(daily_costs.keys())

            if len(dates) < self.config.min_days_for_baseline:
                continue

            costs = np.array([daily_costs[d] for d in dates])
            periodicity = self._detect_periodicity(costs)
            adjusted_costs = self._remove_periodicity(costs, periodicity)

            for i in range(self.config.min_days_for_baseline, len(dates)):
                baseline = adjusted_costs[max(0, i - self.config.min_days_for_baseline):i]
                mean = np.mean(baseline)
                std = np.std(baseline)

                threshold = mean + self.config.threshold_std * std
                actual = adjusted_costs[i]

                if std > 0 and actual > threshold and costs[i] > 1.0:
                    original_actual = costs[i]
                    pct_change = ((original_actual - mean) / mean * 100) if mean > 0 else 0

                    if pct_change >= self.config.min_percentage_change:
                        severity = self._calculate_severity(pct_change)
                        anomalies.append(CostAnomaly(
                            provider=data["provider"],
                            service_name=data["service"],
                            resource_id=resource_id,
                            anomaly_date=dates[i],
                            expected_cost=float(mean),
                            actual_cost=float(original_actual),
                            percentage_change=float(pct_change),
                            severity=severity,
                            anomaly_type="resource_spike",
                            description=f"资源 {resource_id} 费用突增 {pct_change:.1f}%",
                            has_periodicity=periodicity["found"],
                            periodicity_type=periodicity["type"],
                        ))

        return anomalies

    def _detect_periodicity(self, data: np.ndarray) -> Dict[str, Any]:
        """检测时间序列的周期性模式"""
        if len(data) < 14:
            return {"found": False, "type": "", "strength": 0.0}

        result = {"found": False, "type": "", "strength": 0.0}

        if len(data) >= 14:
            weekly_strength = self._calculate_weekly_periodicity_strength(data)
            if weekly_strength > 0.6:
                result["found"] = True
                result["type"] = "weekly"
                result["strength"] = weekly_strength
                return result

        if len(data) >= 30:
            monthly_strength = self._calculate_monthly_periodicity_strength(data)
            if monthly_strength > 0.5:
                result["found"] = True
                result["type"] = "monthly"
                result["strength"] = monthly_strength
                return result

        return result

    def _calculate_weekly_periodicity_strength(self, data: np.ndarray) -> float:
        """计算周周期性强度"""
        if len(data) < 14:
            return 0.0

        weekly_avgs = []
        for day in range(7):
            day_indices = list(range(day, len(data), 7))
            if len(day_indices) >= 2:
                day_vals = data[day_indices]
                weekly_avgs.append(np.mean(day_vals))

        if len(weekly_avgs) >= 2:
            between_day_var = np.var(weekly_avgs)
            total_var = np.var(data)
            if total_var > 0:
                return min(1.0, between_day_var / total_var)

        return 0.0

    def _calculate_monthly_periodicity_strength(self, data: np.ndarray) -> float:
        """计算月周期性强度"""
        if len(data) < 30:
            return 0.0

        monthly_avgs = []
        for day in range(30):
            day_indices = list(range(day, len(data), 30))
            if len(day_indices) >= 2:
                day_vals = data[day_indices]
                monthly_avgs.append(np.mean(day_vals))

        if len(monthly_avgs) >= 2:
            between_day_var = np.var(monthly_avgs)
            total_var = np.var(data)
            if total_var > 0:
                return min(1.0, between_day_var / total_var)

        return 0.0

    def _remove_periodicity(self, data: np.ndarray, periodicity: Dict[str, Any]) -> np.ndarray:
        """去除周期性模式，得到残差序列"""
        if not periodicity["found"]:
            return data

        period = 7 if periodicity["type"] == "weekly" else 30
        adjusted = data.copy()

        for i in range(len(data)):
            same_period_indices = list(range(i % period, i, period))
            if same_period_indices:
                period_avg = np.mean(data[same_period_indices])
                global_avg = np.mean(data[:i + 1])
                adjusted[i] = data[i] - (period_avg - global_avg)

        return adjusted

    def _detect_periodicity_break(
        self,
        records: List[BillingRecord],
    ) -> List[CostAnomaly]:
        """检测周期性模式被打破的异常"""
        anomalies = []

        daily_costs = defaultdict(float)
        for record in records:
            daily_costs[record.usage_start_date] += record.pretax_amount

        dates = sorted(daily_costs.keys())
        if len(dates) < 30:
            return anomalies

        costs = np.array([daily_costs[d] for d in dates])
        periodicity = self._detect_periodicity(costs)

        if not periodicity["found"]:
            return anomalies

        period = 7 if periodicity["type"] == "weekly" else 30
        period_name = "周" if periodicity["type"] == "weekly" else "月"

        for i in range(period * 2, len(dates)):
            historical_period_indices = []
            for p in range(1, 4):
                idx = i - p * period
                if idx >= 0:
                    historical_period_indices.append(idx)

            if len(historical_period_indices) >= 2:
                historical_vals = costs[historical_period_indices]
                mean = np.mean(historical_vals)
                std = np.std(historical_vals)
                actual = costs[i]

                threshold_high = mean + self.config.threshold_std * std
                threshold_low = mean - self.config.threshold_std * std

                if actual > threshold_high or actual < threshold_low:
                    direction = "增加" if actual > threshold_high else "减少"
                    pct_change = abs((actual - mean) / mean * 100) if mean > 0 else 0

                    if pct_change >= self.config.min_percentage_change:
                        severity = self._calculate_severity(pct_change)
                        anomalies.append(CostAnomaly(
                            provider="all",
                            service_name="total",
                            resource_id="",
                            anomaly_date=dates[i],
                            expected_cost=float(mean),
                            actual_cost=float(actual),
                            percentage_change=float(pct_change),
                            severity=severity,
                            anomaly_type="periodicity_break",
                            description=f"{period_name}周期性模式被打破，费用{direction} {pct_change:.1f}%，"
                                        f"历史同期均值 {mean:.2f}，实际 {actual:.2f}",
                            has_periodicity=True,
                            periodicity_type=periodicity["type"],
                        ))

        return anomalies

    def detect_new_resources(
        self,
        records: List[BillingRecord],
        days_threshold: int = 7,
    ) -> List[CostAnomaly]:
        """检测新增资源（可能是意外创建的）"""
        anomalies = []

        resource_first_seen = {}
        resource_info = {}

        for record in records:
            if not record.resource_id:
                continue
            if record.resource_id not in resource_first_seen:
                resource_first_seen[record.resource_id] = record.usage_start_date
                resource_info[record.resource_id] = {
                    "provider": record.provider,
                    "service": record.service_name,
                }

        cutoff_date = date.today() - timedelta(days=days_threshold)

        for resource_id, first_seen in resource_first_seen.items():
            if first_seen >= cutoff_date:
                info = resource_info[resource_id]
                resource_cost = sum(
                    r.pretax_amount for r in records
                    if r.resource_id == resource_id
                )
                anomalies.append(CostAnomaly(
                    provider=info["provider"],
                    service_name=info["service"],
                    resource_id=resource_id,
                    anomaly_date=first_seen,
                    expected_cost=0.0,
                    actual_cost=resource_cost,
                    percentage_change=100.0,
                    severity="low",
                    anomaly_type="new_resource",
                    description=f"新资源 {resource_id} 于 {first_seen} 创建，累计费用 {resource_cost:.2f}",
                ))

        return anomalies

    def detect_weekday_weekend_anomalies(
        self,
        records: List[BillingRecord],
    ) -> List[CostAnomaly]:
        """检测周末/工作日的异常模式"""
        anomalies = []

        weekday_costs = []
        weekend_costs = []

        for record in records:
            if record.usage_start_date.weekday() < 5:
                weekday_costs.append(record.pretax_amount)
            else:
                weekend_costs.append(record.pretax_amount)

        if len(weekday_costs) < 10 or len(weekend_costs) < 4:
            return anomalies

        weekday_avg = np.mean(weekday_costs)
        weekend_avg = np.mean(weekend_costs)

        if weekend_avg > weekday_avg * 1.5 and weekend_avg > 100:
            pct_change = ((weekend_avg - weekday_avg) / weekday_avg * 100) if weekday_avg > 0 else 0
            anomalies.append(CostAnomaly(
                provider="all",
                service_name="total",
                resource_id="",
                anomaly_date=date.today(),
                expected_cost=float(weekday_avg),
                actual_cost=float(weekend_avg),
                percentage_change=float(pct_change),
                severity="medium",
                anomaly_type="weekend_pattern",
                description=f"周末平均费用 ({weekend_avg:.2f}) 比工作日 ({weekday_avg:.2f}) 高 {pct_change:.1f}%，请检查是否有非预期的周末作业",
            ))

        return anomalies

    def _calculate_severity(self, percentage_change: float) -> str:
        """根据变化百分比计算严重程度"""
        if percentage_change >= 200:
            return "critical"
        elif percentage_change >= 100:
            return "high"
        elif percentage_change >= 50:
            return "medium"
        else:
            return "low"

    def group_anomalies_by_severity(
        self,
        anomalies: List[CostAnomaly],
    ) -> Dict[str, List[CostAnomaly]]:
        """按严重程度分组异常"""
        grouped = {
            "critical": [],
            "high": [],
            "medium": [],
            "low": [],
        }

        for anomaly in anomalies:
            if anomaly.severity in grouped:
                grouped[anomaly.severity].append(anomaly)

        return grouped

    def generate_alert_summary(
        self,
        anomalies: List[CostAnomaly],
    ) -> Dict[str, Any]:
        """生成告警摘要"""
        grouped = self.group_anomalies_by_severity(anomalies)

        periodicity_count = sum(1 for a in anomalies if a.has_periodicity)

        return {
            "total_anomalies": len(anomalies),
            "critical_count": len(grouped["critical"]),
            "high_count": len(grouped["high"]),
            "medium_count": len(grouped["medium"]),
            "low_count": len(grouped["low"]),
            "periodicity_count": periodicity_count,
            "needs_attention": len(grouped["critical"]) + len(grouped["high"]) > 0,
            "top_anomalies": sorted(
                anomalies,
                key=lambda x: (
                    {"critical": 0, "high": 1, "medium": 2, "low": 3}[x.severity],
                    -x.percentage_change,
                )
            )[:10],
        }

    def anomaly_to_dict(self, anomaly: CostAnomaly) -> Dict[str, Any]:
        """将异常对象转换为字典"""
        return {
            "provider": anomaly.provider,
            "service_name": anomaly.service_name,
            "resource_id": anomaly.resource_id,
            "anomaly_date": anomaly.anomaly_date.isoformat() if isinstance(anomaly.anomaly_date, date) else anomaly.anomaly_date,
            "expected_cost": anomaly.expected_cost,
            "actual_cost": anomaly.actual_cost,
            "percentage_change": anomaly.percentage_change,
            "severity": anomaly.severity,
            "anomaly_type": anomaly.anomaly_type,
            "description": anomaly.description,
            "has_periodicity": anomaly.has_periodicity,
            "periodicity_type": anomaly.periodicity_type,
        }
