import numpy as np
import pandas as pd
from typing import List, Dict, Any, Tuple, Optional
from datetime import datetime, timedelta
from collections import defaultdict, Counter
from pydantic import BaseModel, Field
from enum import Enum

from app.models.alert import Alert, AlertRule, OptimizationSuggestion, RuleOptimizationResult
from app.config import settings


class ReviewGranularity(str, Enum):
    HOURLY = "hourly"
    DAILY = "daily"
    CUSTOM = "custom"


class TimeSeriesDataPoint(BaseModel):
    timestamp: int
    datetime: str
    original_count: int = 0
    optimized_count: int = 0
    reduction_count: int = 0
    reduction_percent: float = 0.0


class RuleComparison(BaseModel):
    rule_name: str
    original_count: int
    optimized_count: int
    reduction_count: int
    reduction_percent: float
    priority: str = "INFO"
    service: str = ""
    threshold_changed: bool = False
    original_threshold: Optional[float] = None
    optimized_threshold: Optional[float] = None


class ServiceComparison(BaseModel):
    service_name: str
    original_count: int
    optimized_count: int
    reduction_count: int
    reduction_percent: float
    rules_affected: int
    top_rules: List[str]


class PriorityComparison(BaseModel):
    priority: str
    original_count: int
    optimized_count: int
    reduction_count: int
    reduction_percent: float


class AlertReviewReport(BaseModel):
    review_period: Dict[str, int]
    time_series: List[TimeSeriesDataPoint]
    by_rule: List[RuleComparison]
    by_service: List[ServiceComparison]
    by_priority: List[PriorityComparison]
    summary: Dict[str, Any]
    recommendations: List[str]


class AlertReviewer:
    def __init__(
        self,
        default_granularity: ReviewGranularity = ReviewGranularity.HOURLY,
    ):
        self.default_granularity = default_granularity

    def _aggregate_by_time(
        self,
        alerts: List[Alert],
        start_time: int,
        end_time: int,
        granularity: ReviewGranularity,
    ) -> Dict[int, List[Alert]]:
        if granularity == ReviewGranularity.HOURLY:
            interval_ms = 3600000
        elif granularity == ReviewGranularity.DAILY:
            interval_ms = 86400000
        else:
            interval_ms = 3600000

        buckets = defaultdict(list)

        for alert in alerts:
            bucket_start = (alert.start_time - start_time) // interval_ms * interval_ms + start_time
            if start_time <= bucket_start <= end_time:
                buckets[bucket_start].append(alert)

        return buckets

    def _simulate_optimized_alerts(
        self,
        alerts: List[Alert],
        suggestions: List[OptimizationSuggestion],
        suppression_rules: List = None,
    ) -> List[Alert]:
        if not suggestions and not suppression_rules:
            return alerts

        optimized_alerts = []
        rule_configs = {s.rule_name: s.suggested_config for s in suggestions}
        original_configs = {s.rule_name: s.original_config for s in suggestions}

        for alert in alerts:
            should_keep = True

            if alert.rule_name in rule_configs:
                config = rule_configs[alert.rule_name]
                original_config = original_configs.get(alert.rule_name, {})

                threshold = config.get("threshold", original_config.get("threshold", 0))
                op = config.get("op", original_config.get("op", ">"))
                period = config.get("period", original_config.get("period", 1))
                count = config.get("count", original_config.get("count", 1))

                alert_value = None
                for tag in alert.tags:
                    if tag.key in ["value", "metric_value", "current_value"]:
                        try:
                            alert_value = float(tag.value)
                            break
                        except (ValueError, TypeError):
                            pass

                if alert_value is not None:
                    if op == ">" and alert_value <= threshold:
                        should_keep = False
                    elif op == ">=" and alert_value < threshold:
                        should_keep = False
                    elif op == "<" and alert_value >= threshold:
                        should_keep = False
                    elif op == "<=" and alert_value > threshold:
                        should_keep = False
                    elif op == "==" and alert_value != threshold:
                        should_keep = False
                    elif op == "!=" and alert_value == threshold:
                        should_keep = False

            if should_keep:
                optimized_alerts.append(alert)

        if suppression_rules:
            from app.analysis.suppression_optimizer import suppression_optimizer
            sim_result = suppression_optimizer.simulate_suppression(
                optimized_alerts, suppression_rules
            )
            suppressed_ids = set()
            for detail in sim_result["suppression_details"]:
                for sa in detail["suppressed_alerts"]:
                    suppressed_ids.add(sa["alert_id"])
            optimized_alerts = [a for a in optimized_alerts if a.id not in suppressed_ids]

        return optimized_alerts

    def _generate_time_series(
        self,
        original_alerts: List[Alert],
        optimized_alerts: List[Alert],
        start_time: int,
        end_time: int,
        granularity: ReviewGranularity,
    ) -> List[TimeSeriesDataPoint]:
        if granularity == ReviewGranularity.HOURLY:
            interval_ms = 3600000
        elif granularity == ReviewGranularity.DAILY:
            interval_ms = 86400000
        else:
            interval_ms = 3600000

        orig_buckets = self._aggregate_by_time(
            original_alerts, start_time, end_time, granularity
        )
        opt_buckets = self._aggregate_by_time(
            optimized_alerts, start_time, end_time, granularity
        )

        time_series = []
        current_time = start_time
        while current_time <= end_time:
            orig_count = len(orig_buckets.get(current_time, []))
            opt_count = len(opt_buckets.get(current_time, []))
            reduction = orig_count - opt_count
            reduction_pct = reduction / max(orig_count, 1) * 100

            data_point = TimeSeriesDataPoint(
                timestamp=current_time,
                datetime=datetime.fromtimestamp(current_time / 1000).strftime("%Y-%m-%d %H:%M:%S"),
                original_count=orig_count,
                optimized_count=opt_count,
                reduction_count=reduction,
                reduction_percent=round(reduction_pct, 2),
            )
            time_series.append(data_point)
            current_time += interval_ms

        return time_series

    def _generate_rule_comparison(
        self,
        original_alerts: List[Alert],
        optimized_alerts: List[Alert],
        suggestions: List[OptimizationSuggestion],
    ) -> List[RuleComparison]:
        orig_counts = Counter(a.rule_name for a in original_alerts)
        opt_counts = Counter(a.rule_name for a in optimized_alerts)

        all_rules = list(set(list(orig_counts.keys()) + list(opt_counts.keys())))
        rule_services = {}
        rule_priorities = {}

        for alert in original_alerts:
            if alert.rule_name not in rule_services:
                rule_services[alert.rule_name] = alert.service
            if alert.rule_name not in rule_priorities:
                rule_priorities[alert.rule_name] = alert.priority

        suggestion_map = {s.rule_name: s for s in suggestions}

        comparisons = []
        for rule_name in all_rules:
            orig_count = orig_counts.get(rule_name, 0)
            opt_count = opt_counts.get(rule_name, 0)
            reduction = orig_count - opt_count
            reduction_pct = reduction / max(orig_count, 1) * 100

            suggestion = suggestion_map.get(rule_name)
            threshold_changed = False
            orig_threshold = None
            opt_threshold = None

            if suggestion:
                orig_threshold = suggestion.original_config.get("threshold")
                opt_threshold = suggestion.suggested_config.get("threshold")
                if orig_threshold is not None and opt_threshold is not None:
                    try:
                        threshold_changed = float(orig_threshold) != float(opt_threshold)
                    except (ValueError, TypeError):
                        threshold_changed = str(orig_threshold) != str(opt_threshold)

            comparison = RuleComparison(
                rule_name=rule_name,
                original_count=orig_count,
                optimized_count=opt_count,
                reduction_count=reduction,
                reduction_percent=round(reduction_pct, 2),
                priority=rule_priorities.get(rule_name, "INFO"),
                service=rule_services.get(rule_name, ""),
                threshold_changed=threshold_changed,
                original_threshold=orig_threshold,
                optimized_threshold=opt_threshold,
            )
            comparisons.append(comparison)

        comparisons.sort(key=lambda x: x.reduction_count, reverse=True)
        return comparisons

    def _generate_service_comparison(
        self,
        original_alerts: List[Alert],
        optimized_alerts: List[Alert],
    ) -> List[ServiceComparison]:
        orig_by_service = defaultdict(list)
        opt_by_service = defaultdict(list)

        for alert in original_alerts:
            orig_by_service[alert.service].append(alert)
        for alert in optimized_alerts:
            opt_by_service[alert.service].append(alert)

        all_services = list(set(list(orig_by_service.keys()) + list(opt_by_service.keys())))
        comparisons = []

        for service in all_services:
            orig_alerts = orig_by_service.get(service, [])
            opt_alerts = opt_by_service.get(service, [])
            orig_count = len(orig_alerts)
            opt_count = len(opt_alerts)
            reduction = orig_count - opt_count
            reduction_pct = reduction / max(orig_count, 1) * 100

            rule_counts = Counter(a.rule_name for a in orig_alerts)
            top_rules = [r for r, _ in rule_counts.most_common(5)]
            rules_affected = len(set(a.rule_name for a in orig_alerts))

            comparison = ServiceComparison(
                service_name=service,
                original_count=orig_count,
                optimized_count=opt_count,
                reduction_count=reduction,
                reduction_percent=round(reduction_pct, 2),
                rules_affected=rules_affected,
                top_rules=top_rules,
            )
            comparisons.append(comparison)

        comparisons.sort(key=lambda x: x.reduction_count, reverse=True)
        return comparisons

    def _generate_priority_comparison(
        self,
        original_alerts: List[Alert],
        optimized_alerts: List[Alert],
    ) -> List[PriorityComparison]:
        orig_counts = Counter(a.priority for a in original_alerts)
        opt_counts = Counter(a.priority for a in optimized_alerts)

        all_priorities = ["CRITICAL", "WARNING", "INFO"]
        comparisons = []

        for priority in all_priorities:
            orig_count = orig_counts.get(priority, 0)
            opt_count = opt_counts.get(priority, 0)
            reduction = orig_count - opt_count
            reduction_pct = reduction / max(orig_count, 1) * 100

            comparison = PriorityComparison(
                priority=priority,
                original_count=orig_count,
                optimized_count=opt_count,
                reduction_count=reduction,
                reduction_percent=round(reduction_pct, 2),
            )
            comparisons.append(comparison)

        return comparisons

    def _generate_recommendations(
        self,
        time_series: List[TimeSeriesDataPoint],
        rule_comparisons: List[RuleComparison],
        service_comparisons: List[ServiceComparison],
        priority_comparisons: List[PriorityComparison],
    ) -> List[str]:
        recommendations = []

        total_orig = sum(d.original_count for d in time_series)
        total_opt = sum(d.optimized_count for d in time_series)
        total_reduction = total_orig - total_opt
        reduction_pct = total_reduction / max(total_orig, 1) * 100

        if reduction_pct > 50:
            recommendations.append(
                f"告警量减少{reduction_pct:.1f}%，优化效果显著，建议持续监控并考虑推广到更多规则"
            )
        elif reduction_pct > 20:
            recommendations.append(
                f"告警量减少{reduction_pct:.1f}%，优化效果良好，建议进一步调整阈值提升效果"
            )
        elif reduction_pct > 0:
            recommendations.append(
                f"告警量减少{reduction_pct:.1f}%，优化效果有限，建议检查规则配置和数据质量"
            )
        else:
            recommendations.append(
                "告警量未减少甚至增加，建议重新评估优化策略和阈值设置"
            )

        high_impact_rules = [r for r in rule_comparisons if r.reduction_percent > 50]
        if high_impact_rules:
            rule_names = ", ".join(r.rule_name for r in high_impact_rules[:3])
            recommendations.append(
                f"以下规则优化效果显著：{rule_names}，建议作为典型案例推广"
            )

        critical_reduction = next(
            (p.reduction_percent for p in priority_comparisons if p.priority == "CRITICAL"),
            0
        )
        warning_reduction = next(
            (p.reduction_percent for p in priority_comparisons if p.priority == "WARNING"),
            0
        )

        if critical_reduction < 0:
            recommendations.append(
                f"CRITICAL级别告警增加了{abs(critical_reduction):.1f}%，请检查是否存在关键告警被误抑制"
            )
        elif critical_reduction > 30:
            recommendations.append(
                f"CRITICAL级别告警减少了{critical_reduction:.1f}%，请确认没有遗漏关键故障告警"
            )

        problem_services = [
            s for s in service_comparisons
            if s.reduction_percent > 30 and s.original_count > 10
        ]
        if problem_services:
            svc_names = ", ".join(s.service_name for s in problem_services[:3])
            recommendations.append(
                f"以下服务告警量下降明显：{svc_names}，建议关注服务稳定性是否有实质性提升"
            )

        peak_hours = sorted(
            time_series, key=lambda x: x.original_count, reverse=True
        )[:3]
        if peak_hours:
            hour_info = ", ".join(
                f"{d.datetime.split(' ')[1][:2]}时({d.original_count}次)"
                for d in peak_hours
            )
            recommendations.append(
                f"告警高发时段：{hour_info}，建议在这些时段加强监控"
            )

        return recommendations

    def generate_review_report(
        self,
        original_alerts: List[Alert],
        suggestions: List[OptimizationSuggestion] = None,
        suppression_rules: List = None,
        granularity: ReviewGranularity = None,
        custom_start_time: int = None,
        custom_end_time: int = None,
    ) -> AlertReviewReport:
        if not original_alerts:
            return AlertReviewReport(
                review_period={"start": 0, "end": 0},
                time_series=[],
                by_rule=[],
                by_service=[],
                by_priority=[],
                summary={"total_original": 0, "total_optimized": 0},
                recommendations=[],
            )

        if suggestions is None:
            suggestions = []
        if granularity is None:
            granularity = self.default_granularity

        timestamps = [a.start_time for a in original_alerts]
        start_time = custom_start_time if custom_start_time else min(timestamps)
        end_time = custom_end_time if custom_end_time else max(timestamps)

        optimized_alerts = self._simulate_optimized_alerts(
            original_alerts, suggestions, suppression_rules
        )

        time_series = self._generate_time_series(
            original_alerts, optimized_alerts, start_time, end_time, granularity
        )

        rule_comparisons = self._generate_rule_comparison(
            original_alerts, optimized_alerts, suggestions
        )

        service_comparisons = self._generate_service_comparison(
            original_alerts, optimized_alerts
        )

        priority_comparisons = self._generate_priority_comparison(
            original_alerts, optimized_alerts
        )

        total_original = sum(d.original_count for d in time_series)
        total_optimized = sum(d.optimized_count for d in time_series)
        total_reduction = total_original - total_optimized
        total_reduction_pct = total_reduction / max(total_original, 1) * 100

        peak_reduction = max(d.reduction_percent for d in time_series) if time_series else 0
        avg_reduction = np.mean([d.reduction_percent for d in time_series]) if time_series else 0

        rules_improved = sum(1 for r in rule_comparisons if r.reduction_count > 0)
        rules_worsened = sum(1 for r in rule_comparisons if r.reduction_count < 0)

        summary = {
            "total_original": total_original,
            "total_optimized": total_optimized,
            "total_reduction": total_reduction,
            "total_reduction_percent": round(total_reduction_pct, 2),
            "peak_reduction_percent": round(peak_reduction, 2),
            "avg_reduction_percent": round(float(avg_reduction), 2),
            "rules_analyzed": len(rule_comparisons),
            "rules_improved": rules_improved,
            "rules_worsened": rules_worsened,
            "services_affected": len(service_comparisons),
            "granularity": granularity.value,
            "period_start": start_time,
            "period_end": end_time,
            "period_hours": round((end_time - start_time) / 3600000, 2),
        }

        recommendations = self._generate_recommendations(
            time_series, rule_comparisons, service_comparisons, priority_comparisons
        )

        return AlertReviewReport(
            review_period={"start": start_time, "end": end_time},
            time_series=time_series,
            by_rule=rule_comparisons,
            by_service=service_comparisons,
            by_priority=priority_comparisons,
            summary=summary,
            recommendations=recommendations,
        )

    def export_report_data(
        self, report: AlertReviewReport, format: str = "json"
    ) -> Any:
        if format == "json":
            return report.model_dump()
        elif format == "csv":
            data = []
            for dp in report.time_series:
                data.append({
                    "timestamp": dp.timestamp,
                    "datetime": dp.datetime,
                    "original_count": dp.original_count,
                    "optimized_count": dp.optimized_count,
                    "reduction_count": dp.reduction_count,
                    "reduction_percent": dp.reduction_percent,
                })
            return pd.DataFrame(data).to_csv(index=False)
        else:
            raise ValueError(f"Unsupported format: {format}")


alert_reviewer = AlertReviewer()
