import numpy as np
import pandas as pd
from typing import List, Dict, Any, Tuple
from datetime import datetime
from collections import defaultdict
from scipy import stats
import hashlib

from app.models.alert import Alert, AlertRule, InefficientRule, AlertCluster
from app.config import settings


class RuleAnalyzer:
    def __init__(self):
        self.priority_weights = {
            "CRITICAL": 1.0,
            "WARNING": 0.5,
            "INFO": 0.2,
        }
        self.critical_rules = [
            "service_sla_rule",
            "service_resp_time_rule",
            "service_error_rate_rule",
        ]

    def _extract_rule_stats(
        self, alerts: List[Alert], rule_name: str
    ) -> Dict[str, Any]:
        rule_alerts = [a for a in alerts if a.rule_name == rule_name]
        if not rule_alerts:
            return {}

        df = pd.DataFrame([{
            "start_time": a.start_time,
            "priority": a.priority,
            "service": a.service,
            "scope": a.scope,
        } for a in rule_alerts])

        timestamps = sorted(df["start_time"].values)
        time_intervals = np.diff(timestamps) / 1000.0 if len(timestamps) > 1 else np.array([0])

        hours_span = (timestamps[-1] - timestamps[0]) / 3600000.0 if len(timestamps) > 1 else 0
        frequency_per_hour = len(rule_alerts) / max(hours_span, 1)

        priority_counts = df["priority"].value_counts().to_dict()
        unique_services = df["service"].nunique()
        unique_scopes = df["scope"].nunique()

        if len(time_intervals) > 1:
            cv = np.std(time_intervals) / np.mean(time_intervals) if np.mean(time_intervals) > 0 else 0
            is_periodic = cv < 0.3
        else:
            is_periodic = False

        silent_periods = []
        if len(time_intervals) > 0:
            silent_periods = [t for t in time_intervals if t > 600]

        burst_count = sum(1 for t in time_intervals if t < 60) if len(time_intervals) > 0 else 0
        burst_ratio = burst_count / len(time_intervals) if len(time_intervals) > 0 else 0

        return {
            "total_alerts": len(rule_alerts),
            "frequency_per_hour": round(frequency_per_hour, 2),
            "hours_span": round(hours_span, 2),
            "avg_interval_seconds": round(float(np.mean(time_intervals)), 2),
            "median_interval_seconds": round(float(np.median(time_intervals)), 2),
            "min_interval_seconds": round(float(np.min(time_intervals)), 2),
            "max_interval_seconds": round(float(np.max(time_intervals)), 2),
            "priority_distribution": priority_counts,
            "unique_services": unique_services,
            "unique_scopes": unique_scopes,
            "is_periodic": is_periodic,
            "periodicity_cv": round(float(cv if len(time_intervals) > 1 else 0), 2),
            "silent_periods_count": len(silent_periods),
            "burst_count": burst_count,
            "burst_ratio": round(burst_ratio, 2),
            "timestamps": timestamps,
        }

    def _calculate_frequency_score(
        self, stats: Dict[str, Any], all_rule_stats: Dict[str, Any]
    ) -> float:
        if not stats:
            return 0.0

        total_alerts = stats.get("total_alerts", 0)
        frequency = stats.get("frequency_per_hour", 0)
        burst_ratio = stats.get("burst_ratio", 0)

        all_frequencies = [
            s.get("frequency_per_hour", 0) for s in all_rule_stats.values() if s
        ]
        if all_frequencies:
            freq_percentile = stats.percentileofscore(all_frequencies, frequency) / 100
        else:
            freq_percentile = 0.5

        threshold = settings.alert_frequency_threshold
        freq_score = min(total_alerts / threshold, 1.0)
        combined_score = (freq_score * 0.4 + freq_percentile * 0.4 + burst_ratio * 0.2)

        return round(min(combined_score, 1.0), 4)

    def _calculate_criticality_score(
        self, rule_name: str, stats: Dict[str, Any], rule_config: AlertRule = None
    ) -> float:
        if not stats:
            return 0.0

        base_score = 0.5

        if rule_name in self.critical_rules:
            base_score = 1.0
        elif rule_config and rule_config.priority == "CRITICAL":
            base_score = 0.9
        elif rule_config and rule_config.priority == "WARNING":
            base_score = 0.6
        elif rule_config and rule_config.priority == "INFO":
            base_score = 0.3

        priority_dist = stats.get("priority_distribution", {})
        critical_ratio = priority_dist.get("CRITICAL", 0) / max(stats.get("total_alerts", 1), 1)
        warning_ratio = priority_dist.get("WARNING", 0) / max(stats.get("total_alerts", 1), 1)

        priority_score = critical_ratio * 1.0 + warning_ratio * 0.5
        combined = base_score * 0.7 + priority_score * 0.3

        return round(combined, 4)

    def _calculate_noise_score(
        self, stats: Dict[str, Any], clusters: List[AlertCluster] = None
    ) -> float:
        if not stats:
            return 0.0

        noise_components = []

        burst_ratio = stats.get("burst_ratio", 0)
        noise_components.append(burst_ratio * 0.3)

        if stats.get("is_periodic", False):
            cv = stats.get("periodicity_cv", 1.0)
            periodicity_score = max(0, 1 - cv)
            noise_components.append(periodicity_score * 0.3)

        info_ratio = stats.get("priority_distribution", {}).get("INFO", 0) / max(stats.get("total_alerts", 1), 1)
        noise_components.append(info_ratio * 0.2)

        total_alerts = stats.get("total_alerts", 0)
        unique_services = stats.get("unique_services", 1)
        if unique_services > 1 and total_alerts > 10:
            service_spread = min(unique_services / 5, 1.0)
            noise_components.append(service_spread * 0.2)

        if clusters:
            rule_clusters = [c for c in clusters if c.rule_name == stats.get("rule_name", "")]
            if rule_clusters:
                cluster_alerts = sum(c.alert_count for c in rule_clusters)
                clustered_ratio = cluster_alerts / max(total_alerts, 1)
                noise_components.append(clustered_ratio * 0.15)

        noise_score = sum(noise_components)
        return round(min(noise_score, 1.0), 4)

    def _calculate_inefficiency_score(
        self, frequency_score: float, criticality_score: float, noise_score: float
    ) -> float:
        inefficiency = (frequency_score * 0.4 + noise_score * 0.4) * (1 - criticality_score * 0.5)
        return round(min(inefficiency, 1.0), 4)

    def _generate_recommendation(
        self,
        rule_name: str,
        inefficiency_score: float,
        stats: Dict[str, Any],
        frequency_score: float,
        criticality_score: float,
        noise_score: float,
    ) -> Tuple[str, str]:
        recommendations = []

        if frequency_score > 0.7:
            if stats.get("is_periodic", False):
                recommendations.append(
                    "告警呈现周期性模式，建议调整静默期(silencePeriod)或增加触发计数阈值"
                )
            if stats.get("burst_ratio", 0) > 0.5:
                recommendations.append(
                    "存在告警风暴，建议增加触发周期(period)或计数阈值(count)"
                )
            recommendations.append(
                f"告警频率过高({stats.get('frequency_per_hour', 0):.1f}/小时)，建议调高阈值或调整检测周期"
            )

        if noise_score > 0.6:
            recommendations.append(
                "高噪声告警，建议优化规则匹配条件，增加更具体的过滤条件"
            )
            if stats.get("unique_services", 0) > 3:
                recommendations.append(
                    "告警跨多个服务，建议为关键服务单独配置规则"
                )

        if criticality_score < 0.4:
            recommendations.append(
                "规则优先级较低，可考虑降级为INFO或在非工作时间抑制"
            )

        if stats.get("silent_periods_count", 0) > 5:
            recommendations.append(
                "存在长时间静默期，建议评估规则时效性，考虑设置告警时间段"
            )

        if not recommendations:
            recommendations.append("规则运行正常，建议持续监控")

        severity = "HIGH" if inefficiency_score > 0.7 else (
            "MEDIUM" if inefficiency_score > 0.4 else "LOW"
        )

        return "；".join(recommendations), severity

    def analyze_inefficient_rules(
        self,
        alerts: List[Alert],
        rules: List[AlertRule] = None,
        clusters: List[AlertCluster] = None,
    ) -> List[InefficientRule]:
        if not alerts:
            return []

        rule_names = list(set(a.rule_name for a in alerts))
        rule_map = {r.name: r for r in rules} if rules else {}

        all_rule_stats = {}
        for rule_name in rule_names:
            stats = self._extract_rule_stats(alerts, rule_name)
            stats["rule_name"] = rule_name
            all_rule_stats[rule_name] = stats

        inefficient_rules = []
        for rule_name in rule_names:
            stats = all_rule_stats[rule_name]
            if not stats or stats.get("total_alerts", 0) < 3:
                continue

            rule_config = rule_map.get(rule_name)

            frequency_score = self._calculate_frequency_score(stats, all_rule_stats)
            criticality_score = self._calculate_criticality_score(rule_name, stats, rule_config)
            noise_score = self._calculate_noise_score(stats, clusters)
            inefficiency_score = self._calculate_inefficiency_score(
                frequency_score, criticality_score, noise_score
            )

            if inefficiency_score < 0.3:
                continue

            recommendation, severity = self._generate_recommendation(
                rule_name,
                inefficiency_score,
                stats,
                frequency_score,
                criticality_score,
                noise_score,
            )

            metrics_data = {
                k: v for k, v in stats.items() if k != "timestamps"
            }
            metrics_data.update({
                "frequency_score": frequency_score,
                "criticality_score": criticality_score,
                "noise_score": noise_score,
            })

            inefficient_rules.append(InefficientRule(
                rule_name=rule_name,
                total_alerts=stats.get("total_alerts", 0),
                frequency_score=frequency_score,
                criticality_score=criticality_score,
                noise_score=noise_score,
                inefficiency_score=inefficiency_score,
                recommendation=recommendation,
                severity=severity,
                metrics_data=metrics_data,
            ))

        return sorted(inefficient_rules, key=lambda r: r.inefficiency_score, reverse=True)

    def get_overall_statistics(
        self, alerts: List[Alert], inefficient_rules: List[InefficientRule]
    ) -> Dict[str, Any]:
        if not alerts:
            return {}

        df = pd.DataFrame([{
            "rule_name": a.rule_name,
            "priority": a.priority,
            "start_time": a.start_time,
            "service": a.service,
        } for a in alerts])

        total_alerts = len(alerts)
        unique_rules = df["rule_name"].nunique()
        unique_services = df["service"].nunique()

        priority_dist = df["priority"].value_counts().to_dict()

        inefficient_count = len(inefficient_rules)
        alerts_from_inefficient = sum(
            r.total_alerts for r in inefficient_rules
        )

        high_severity = [r for r in inefficient_rules if r.severity == "HIGH"]
        medium_severity = [r for r in inefficient_rules if r.severity == "MEDIUM"]

        avg_inefficiency = (
            sum(r.inefficiency_score for r in inefficient_rules) / len(inefficient_rules)
            if inefficient_rules else 0
        )

        potential_reduction = alerts_from_inefficient * (
            avg_inefficiency * 0.7
        ) if inefficient_rules else 0

        return {
            "total_alerts": total_alerts,
            "unique_rules": unique_rules,
            "unique_services": unique_services,
            "priority_distribution": priority_dist,
            "inefficient_rules_count": inefficient_count,
            "inefficient_rules_percentage": round(
                inefficient_count / max(unique_rules, 1) * 100, 2
            ),
            "alerts_from_inefficient": alerts_from_inefficient,
            "alerts_from_inefficient_percentage": round(
                alerts_from_inefficient / max(total_alerts, 1) * 100, 2
            ),
            "high_severity_count": len(high_severity),
            "medium_severity_count": len(medium_severity),
            "avg_inefficiency_score": round(avg_inefficiency, 4),
            "potential_alert_reduction": int(potential_reduction),
            "potential_reduction_percentage": round(
                potential_reduction / max(total_alerts, 1) * 100, 2
            ),
            "time_range": {
                "start": int(df["start_time"].min()),
                "end": int(df["start_time"].max()),
            },
        }


rule_analyzer = RuleAnalyzer()
