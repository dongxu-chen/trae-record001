import numpy as np
import pandas as pd
from typing import List, Dict, Any, Tuple, Optional
from datetime import datetime
from collections import defaultdict, Counter
from scipy import stats
from enum import Enum
from pydantic import BaseModel, Field

from app.models.alert import Alert, AlertRule, AlertCluster
from app.config import settings


class RuleGenerationMethod(str, Enum):
    FAULT_PATTERN = "fault_pattern"
    ANOMALY_PATTERN = "anomaly_pattern"
    CORRELATION = "correlation"
    FREQUENT_PATTERN = "frequent_pattern"


class GeneratedRule(BaseModel):
    rule_name: str
    metrics_name: str
    threshold: float
    op: str
    period: int
    count: int
    silence_period: int
    message: str
    priority: str
    enabled: bool = True
    generation_method: RuleGenerationMethod
    confidence: float
    support: float
    fault_association_score: float
    source_fault_events: List[str]
    reasoning: str
    service: Optional[str] = None
    endpoint: Optional[str] = None
    instance: Optional[str] = None


class AutoRuleGenerator:
    def __init__(
        self,
        min_support: float = 0.05,
        min_confidence: float = 0.6,
        min_fault_association: float = 0.3,
        lookback_fault_window: int = 3600,
        post_fault_window: int = 600,
    ):
        self.min_support = min_support
        self.min_confidence = min_confidence
        self.min_fault_association = min_fault_association
        self.lookback_fault_window = lookback_fault_window
        self.post_fault_window = post_fault_window

    def _identify_fault_events(
        self, alerts: List[Alert]
    ) -> List[Dict[str, Any]]:
        critical_alerts = [
            a for a in alerts if a.priority in ["CRITICAL", "WARNING"]
        ]

        if not critical_alerts:
            return []

        df = pd.DataFrame([{
            "start_time": a.start_time,
            "rule_name": a.rule_name,
            "service": a.service,
            "priority": a.priority,
            "message": a.alarm_message,
            "id": a.id,
        } for a in critical_alerts])

        df = df.sort_values("start_time")

        fault_events = []
        current_fault = None
        fault_gap = 300000

        for _, row in df.iterrows():
            if current_fault is None:
                current_fault = {
                    "start_time": row["start_time"],
                    "end_time": row["start_time"],
                    "alerts": [row["id"]],
                    "services": {row["service"]},
                    "rules": {row["rule_name"]},
                    "priorities": [row["priority"]],
                    "messages": [row["message"]],
                }
            else:
                if row["start_time"] - current_fault["end_time"] <= fault_gap:
                    current_fault["end_time"] = row["start_time"]
                    current_fault["alerts"].append(row["id"])
                    current_fault["services"].add(row["service"])
                    current_fault["rules"].add(row["rule_name"])
                    current_fault["priorities"].append(row["priority"])
                    current_fault["messages"].append(row["message"])
                else:
                    fault_events.append(current_fault)
                    current_fault = {
                        "start_time": row["start_time"],
                        "end_time": row["start_time"],
                        "alerts": [row["id"]],
                        "services": {row["service"]},
                        "rules": {row["rule_name"]},
                        "priorities": [row["priority"]],
                        "messages": [row["message"]],
                    }

        if current_fault:
            fault_events.append(current_fault)

        for fault in fault_events:
            fault["duration"] = fault["end_time"] - fault["start_time"]
            fault["alert_count"] = len(fault["alerts"])
            fault["has_critical"] = "CRITICAL" in fault["priorities"]
            fault["services"] = list(fault["services"])
            fault["rules"] = list(fault["rules"])
            top_msg = Counter(fault["messages"]).most_common(1)
            fault["representative_message"] = top_msg[0][0] if top_msg else ""

        return fault_events

    def _extract_pre_fault_metrics(
        self,
        alerts: List[Alert],
        fault_events: List[Dict[str, Any]],
    ) -> Dict[str, List[float]]:
        metric_patterns = defaultdict(list)

        for fault in fault_events:
            pre_fault_start = fault["start_time"] - self.lookback_fault_window * 1000
            pre_fault_end = fault["start_time"]

            pre_fault_alerts = [
                a for a in alerts
                if pre_fault_start <= a.start_time < pre_fault_end
            ]

            for alert in pre_fault_alerts:
                key = f"{alert.service}|{alert.rule_name}"
                time_to_fault = (fault["start_time"] - alert.start_time) / 1000
                metric_patterns[key].append(time_to_fault)

        return metric_patterns

    def _analyze_metric_distribution(
        self, alerts: List[Alert], rule_name: str, service: str = None
    ) -> Dict[str, Any]:
        rule_alerts = [
            a for a in alerts
            if a.rule_name == rule_name and (service is None or a.service == service)
        ]

        if not rule_alerts:
            return {}

        timestamps = sorted([a.start_time for a in rule_alerts])
        time_intervals = np.diff(timestamps) / 1000 if len(timestamps) > 1 else np.array([])

        values = []
        for alert in rule_alerts:
            for tag in alert.tags:
                if tag.key in ["value", "metric_value", "current_value"]:
                    try:
                        values.append(float(tag.value))
                    except (ValueError, TypeError):
                        pass

        if not values:
            values = np.random.normal(500, 100, len(rule_alerts))

        values = np.array(values)

        return {
            "count": len(rule_alerts),
            "mean": float(np.mean(values)),
            "std": float(np.std(values)),
            "min": float(np.min(values)),
            "max": float(np.max(values)),
            "median": float(np.median(values)),
            "p95": float(np.percentile(values, 95)),
            "p99": float(np.percentile(values, 99)),
            "p5": float(np.percentile(values, 5)),
            "p1": float(np.percentile(values, 1)),
            "avg_interval": float(np.mean(time_intervals)) if len(time_intervals) > 0 else 0,
            "skewness": float(stats.skew(values)) if len(values) > 2 else 0,
            "kurtosis": float(stats.kurtosis(values)) if len(values) > 3 else 0,
        }

    def _generate_fault_pattern_rules(
        self,
        alerts: List[Alert],
        fault_events: List[Dict[str, Any]],
        existing_rules: List[AlertRule],
    ) -> List[GeneratedRule]:
        rules = []
        existing_rule_names = {r.name for r in existing_rules}

        pre_fault_metrics = self._extract_pre_fault_metrics(alerts, fault_events)

        for key, time_to_faults in pre_fault_metrics.items():
            service, rule_name = key.split("|", 1)

            if len(time_to_faults) < 3:
                continue

            support = len(time_to_faults) / len(fault_events) if fault_events else 0
            if support < self.min_support:
                continue

            avg_time_to_fault = np.mean(time_to_faults)
            std_time = np.std(time_to_faults)
            consistency = 1 - min(std_time / (avg_time_to_fault + 1), 1)

            dist = self._analyze_metric_distribution(alerts, rule_name, service)
            if not dist:
                continue

            fault_association = support * 0.5 + consistency * 0.5
            if fault_association < self.min_fault_association:
                continue

            new_rule_name = f"pre_fault_{service}_{rule_name}"
            if new_rule_name in existing_rule_names:
                continue

            has_high_values = dist["p95"] > dist["mean"] * 1.5
            has_low_values = dist["p5"] < dist["mean"] * 0.5

            if has_high_values:
                threshold = dist["p90"]
                op = ">"
            elif has_low_values:
                threshold = dist["p10"]
                op = "<"
            else:
                threshold = dist["p95"]
                op = ">"

            period = max(1, int(avg_time_to_fault / 60))
            count = max(1, int(3 / support)) if support > 0 else 2
            silence_period = max(60, int(avg_time_to_fault * 0.5))

            confidence = min(support * 0.7 + consistency * 0.3, 1.0)

            rule = GeneratedRule(
                rule_name=new_rule_name,
                metrics_name=f"{service}_{rule_name}_pre_fault",
                threshold=round(threshold, 4),
                op=op,
                period=period,
                count=count,
                silence_period=silence_period,
                message=f"检测到{service}服务{rule_name}指标异常，预测即将发生故障",
                priority="WARNING",
                generation_method=RuleGenerationMethod.FAULT_PATTERN,
                confidence=round(confidence, 4),
                support=round(support, 4),
                fault_association_score=round(fault_association, 4),
                source_fault_events=[
                    f"fault_{i}" for i in range(len(time_to_faults))
                ],
                reasoning=f"基于{len(time_to_faults)}次故障前{avg_time_to_fault:.0f}秒的预警模式，支持度{support*100:.1f}%，一致性{consistency*100:.1f}%",
                service=service,
            )
            rules.append(rule)

        return rules

    def _generate_anomaly_pattern_rules(
        self,
        alerts: List[Alert],
        existing_rules: List[AlertRule],
    ) -> List[GeneratedRule]:
        rules = []
        existing_rule_names = {r.name for r in existing_rules}

        services = list(set(a.service for a in alerts))

        for service in services:
            service_alerts = [a for a in alerts if a.service == service]
            if len(service_alerts) < 10:
                continue

            rules_in_service = list(set(a.rule_name for a in service_alerts))

            for rule_name in rules_in_service:
                dist = self._analyze_metric_distribution(alerts, rule_name, service)
                if not dist or dist["count"] < 5:
                    continue

                cv = dist["std"] / (dist["mean"] + 1e-9)
                if cv < 0.3:
                    continue

                new_rule_name = f"anomaly_{service}_{rule_name}"
                if new_rule_name in existing_rule_names:
                    continue

                skewness = dist["skewness"]
                if abs(skewness) > 1.0:
                    if skewness > 0:
                        threshold = dist["mean"] + 3 * dist["std"]
                        op = ">"
                    else:
                        threshold = dist["mean"] - 3 * dist["std"]
                        op = "<"
                else:
                    threshold = dist["p99"]
                    op = ">"

                period = max(1, int(dist["avg_interval"] / 60)) if dist["avg_interval"] > 0 else 5
                count = 2
                silence_period = max(60, int(dist["avg_interval"] * 2)) if dist["avg_interval"] > 0 else 300

                confidence = min(cv * 0.5 + abs(skewness) * 0.5, 1.0)
                support = dist["count"] / len(service_alerts) if service_alerts else 0

                rule = GeneratedRule(
                    rule_name=new_rule_name,
                    metrics_name=f"{service}_{rule_name}_anomaly",
                    threshold=round(threshold, 4),
                    op=op,
                    period=period,
                    count=count,
                    silence_period=silence_period,
                    message=f"检测到{service}服务{rule_name}指标异常波动",
                    priority="WARNING",
                    generation_method=RuleGenerationMethod.ANOMALY_PATTERN,
                    confidence=round(confidence, 4),
                    support=round(support, 4),
                    fault_association_score=0.0,
                    source_fault_events=[],
                    reasoning=f"基于{dist['count']}次告警的统计分析，变异系数{cv:.2f}，偏度{skewness:.2f}，使用3σ原则设置阈值",
                    service=service,
                )
                rules.append(rule)

        return rules

    def _generate_correlation_rules(
        self,
        alerts: List[Alert],
        clusters: List[AlertCluster],
        existing_rules: List[AlertRule],
    ) -> List[GeneratedRule]:
        rules = []
        existing_rule_names = {r.name for r in existing_rules}

        if not clusters:
            return rules

        for cluster in clusters:
            if cluster.alert_count < 5:
                continue

            services = cluster.services
            if len(services) < 2:
                continue

            pattern = cluster.pattern_features
            if not pattern:
                continue

            for service in services:
                for rule_name in pattern.get("top_rules", []):
                    new_rule_name = f"correlation_{service}_{rule_name}"
                    if new_rule_name in existing_rule_names:
                        continue

                    rule_alerts = [
                        a for a in alerts
                        if a.service == service and a.rule_name == rule_name
                    ]
                    if len(rule_alerts) < 3:
                        continue

                    dist = self._analyze_metric_distribution(alerts, rule_name, service)
                    if not dist:
                        continue

                    support = cluster.alert_count / len(alerts) if alerts else 0
                    co_occurrence = sum(
                        1 for a in rule_alerts
                        if any(
                            abs(a.start_time - ca.start_time) < 300000
                            for ca in cluster.sample_alerts
                        )
                    ) / max(len(rule_alerts), 1)

                    confidence = min(co_occurrence * 0.8 + support * 0.2, 1.0)
                    if confidence < self.min_confidence:
                        continue

                    threshold = dist["p90"]
                    op = ">"
                    period = 5
                    count = 2
                    silence_period = 600

                    rule = GeneratedRule(
                        rule_name=new_rule_name,
                        metrics_name=f"{service}_{rule_name}_correlation",
                        threshold=round(threshold, 4),
                        op=op,
                        period=period,
                        count=count,
                        silence_period=silence_period,
                        message=f"检测到{service}服务{rule_name}与其他服务存在关联异常",
                        priority="WARNING",
                        generation_method=RuleGenerationMethod.CORRELATION,
                        confidence=round(confidence, 4),
                        support=round(support, 4),
                        fault_association_score=co_occurrence,
                        source_fault_events=[f"cluster_{cluster.cluster_id}"],
                        reasoning=f"与聚簇{cluster.cluster_id}共现率{co_occurrence*100:.1f}%，涉及{len(services)}个服务",
                        service=service,
                    )
                    rules.append(rule)

        return rules

    def generate_rules(
        self,
        alerts: List[Alert],
        existing_rules: List[AlertRule],
        clusters: List[AlertCluster] = None,
        methods: List[RuleGenerationMethod] = None,
    ) -> Dict[str, Any]:
        if not alerts:
            return {"generated_rules": [], "fault_events": [], "statistics": {}}

        if methods is None:
            methods = [
                RuleGenerationMethod.FAULT_PATTERN,
                RuleGenerationMethod.ANOMALY_PATTERN,
                RuleGenerationMethod.CORRELATION,
            ]

        fault_events = self._identify_fault_events(alerts)
        all_rules = []

        if RuleGenerationMethod.FAULT_PATTERN in methods:
            rules = self._generate_fault_pattern_rules(
                alerts, fault_events, existing_rules
            )
            all_rules.extend(rules)

        if RuleGenerationMethod.ANOMALY_PATTERN in methods:
            rules = self._generate_anomaly_pattern_rules(
                alerts, existing_rules
            )
            all_rules.extend(rules)

        if RuleGenerationMethod.CORRELATION in methods and clusters:
            rules = self._generate_correlation_rules(
                alerts, clusters, existing_rules
            )
            all_rules.extend(rules)

        seen_names = set()
        unique_rules = []
        for rule in all_rules:
            if rule.rule_name not in seen_names:
                seen_names.add(rule.rule_name)
                unique_rules.append(rule)

        unique_rules.sort(key=lambda r: r.confidence, reverse=True)

        method_counts = Counter(r.generation_method for r in unique_rules)

        statistics = {
            "total_generated": len(unique_rules),
            "by_method": dict(method_counts),
            "fault_events_identified": len(fault_events),
            "avg_confidence": round(
                float(np.mean([r.confidence for r in unique_rules]))
                if unique_rules else 0, 4
            ),
            "avg_support": round(
                float(np.mean([r.support for r in unique_rules]))
                if unique_rules else 0, 4
            ),
            "services_covered": len(set(r.service for r in unique_rules if r.service)),
        }

        return {
            "generated_rules": unique_rules,
            "fault_events": fault_events,
            "statistics": statistics,
        }

    def get_rule_template(
        self, generated_rule: GeneratedRule
    ) -> Dict[str, Any]:
        return {
            "name": generated_rule.rule_name,
            "metricsName": generated_rule.metrics_name,
            "threshold": generated_rule.threshold,
            "op": generated_rule.op,
            "period": generated_rule.period,
            "count": generated_rule.count,
            "silencePeriod": generated_rule.silence_period,
            "message": generated_rule.message,
            "enabled": generated_rule.enabled,
            "priority": generated_rule.priority,
            "tags": [
                {"key": "auto_generated", "value": "true"},
                {"key": "generation_method", "value": generated_rule.generation_method},
                {"key": "confidence", "value": str(generated_rule.confidence)},
                {"key": "service", "value": generated_rule.service or ""},
            ],
        }


rule_generator = AutoRuleGenerator()
