import numpy as np
import pandas as pd
from typing import List, Dict, Any, Tuple, Optional
from datetime import datetime
from collections import defaultdict, Counter
from scipy import stats
import networkx as nx
from pydantic import BaseModel, Field
from enum import Enum

from app.models.alert import Alert, AlertRule, AlertCluster
from app.config import settings


class SuppressionType(str, Enum):
    DEPENDENCY = "dependency"
    STORM = "storm"
    REDUNDANT = "redundant"
    TOPOLOGICAL = "topological"


class SuppressionRule(BaseModel):
    suppression_id: str
    suppression_type: SuppressionType
    trigger_rule: str
    suppressed_rules: List[str]
    trigger_service: Optional[str] = None
    suppressed_services: List[str] = []
    time_window: int
    confidence: float
    support: float
    expected_reduction: int
    reasoning: str
    severity: str = "MEDIUM"
    enabled: bool = True


class StormPattern(BaseModel):
    pattern_id: str
    start_time: int
    end_time: int
    alert_count: int
    rule_count: int
    service_count: int
    rules: List[str]
    services: List[str]
    root_cause_candidates: List[Dict[str, Any]]
    severity: str


class AlertSuppressionOptimizer:
    def __init__(
        self,
        storm_threshold: int = 10,
        storm_time_window: int = 300000,
        dependency_time_window: int = 60000,
        min_suppression_confidence: float = 0.6,
        min_suppression_support: float = 0.1,
        max_suppressed_rules: int = 10,
    ):
        self.storm_threshold = storm_threshold
        self.storm_time_window = storm_time_window
        self.dependency_time_window = dependency_time_window
        self.min_suppression_confidence = min_suppression_confidence
        self.min_suppression_support = min_suppression_support
        self.max_suppressed_rules = max_suppressed_rules

    def _detect_storm_patterns(
        self, alerts: List[Alert]
    ) -> List[StormPattern]:
        if not alerts:
            return []

        df = pd.DataFrame([{
            "start_time": a.start_time,
            "rule_name": a.rule_name,
            "service": a.service,
            "priority": a.priority,
            "id": a.id,
        } for a in alerts])

        df = df.sort_values("start_time").reset_index(drop=True)

        storms = []
        current_storm = None
        storm_id = 0

        for i, row in df.iterrows():
            if current_storm is None:
                current_storm = {
                    "start_idx": i,
                    "end_idx": i,
                    "alerts": [row["id"]],
                    "rules": {row["rule_name"]},
                    "services": {row["service"]},
                    "priorities": [row["priority"]],
                }
            else:
                if row["start_time"] - df.loc[current_storm["start_idx"], "start_time"] <= self.storm_time_window:
                    current_storm["end_idx"] = i
                    current_storm["alerts"].append(row["id"])
                    current_storm["rules"].add(row["rule_name"])
                    current_storm["services"].add(row["service"])
                    current_storm["priorities"].append(row["priority"])
                else:
                    if len(current_storm["alerts"]) >= self.storm_threshold:
                        storm = StormPattern(
                            pattern_id=f"storm_{storm_id}",
                            start_time=int(df.loc[current_storm["start_idx"], "start_time"]),
                            end_time=int(df.loc[current_storm["end_idx"], "start_time"]),
                            alert_count=len(current_storm["alerts"]),
                            rule_count=len(current_storm["rules"]),
                            service_count=len(current_storm["services"]),
                            rules=list(current_storm["rules"]),
                            services=list(current_storm["services"]),
                            root_cause_candidates=[],
                            severity="HIGH" if "CRITICAL" in current_storm["priorities"] else "MEDIUM",
                        )
                        storms.append(storm)
                        storm_id += 1

                    current_storm = {
                        "start_idx": i,
                        "end_idx": i,
                        "alerts": [row["id"]],
                        "rules": {row["rule_name"]},
                        "services": {row["service"]},
                        "priorities": [row["priority"]],
                    }

        if current_storm and len(current_storm["alerts"]) >= self.storm_threshold:
            storm = StormPattern(
                pattern_id=f"storm_{storm_id}",
                start_time=int(df.loc[current_storm["start_idx"], "start_time"]),
                end_time=int(df.loc[current_storm["end_idx"], "start_time"]),
                alert_count=len(current_storm["alerts"]),
                rule_count=len(current_storm["rules"]),
                service_count=len(current_storm["services"]),
                rules=list(current_storm["rules"]),
                services=list(current_storm["services"]),
                root_cause_candidates=[],
                severity="HIGH" if "CRITICAL" in current_storm["priorities"] else "MEDIUM",
            )
            storms.append(storm)

        for storm in storms:
            storm_alerts = [a for a in alerts if a.id in [
                aid for aid in storm.rules
            ]]
            storm.root_cause_candidates = self._identify_root_causes(
                storm_alerts, storm.rules
            )

        return storms

    def _identify_root_causes(
        self, alerts: List[Alert], rules: List[str]
    ) -> List[Dict[str, Any]]:
        if not alerts:
            return []

        rule_first_times = {}
        rule_counts = Counter(a.rule_name for a in alerts)

        for alert in sorted(alerts, key=lambda a: a.start_time):
            if alert.rule_name not in rule_first_times:
                rule_first_times[alert.rule_name] = alert.start_time

        candidates = []
        for rule_name in rules:
            first_time = rule_first_times.get(rule_name, float("inf"))
            count = rule_counts.get(rule_name, 0)

            time_score = 1.0 - min(
                (first_time - min(rule_first_times.values())) / self.storm_time_window,
                1.0
            ) if len(rule_first_times) > 1 else 0.5

            frequency_score = min(count / max(rule_counts.values()), 1.0) if rule_counts else 0.5

            score = time_score * 0.6 + frequency_score * 0.4

            candidates.append({
                "rule_name": rule_name,
                "score": round(score, 4),
                "first_time": first_time,
                "alert_count": count,
                "is_earliest": first_time == min(rule_first_times.values()),
            })

        candidates.sort(key=lambda x: x["score"], reverse=True)
        return candidates[:5]

    def _build_dependency_graph(
        self, alerts: List[Alert]
    ) -> nx.DiGraph:
        G = nx.DiGraph()

        if not alerts:
            return G

        rules = list(set(a.rule_name for a in alerts))
        for rule in rules:
            G.add_node(rule)

        alerts_sorted = sorted(alerts, key=lambda a: a.start_time)

        for i, alert_a in enumerate(alerts_sorted):
            for alert_b in alerts_sorted[i+1:]:
                time_diff = alert_b.start_time - alert_a.start_time
                if time_diff > self.dependency_time_window:
                    break

                if alert_a.rule_name == alert_b.rule_name:
                    continue

                edge_key = (alert_a.rule_name, alert_b.rule_name)
                if not G.has_edge(*edge_key):
                    G.add_edge(*edge_key, weight=0, timestamps=[])

                G[alert_a.rule_name][alert_b.rule_name]["weight"] += 1
                G[alert_a.rule_name][alert_b.rule_name]["timestamps"].append(time_diff)

        for u, v, data in G.edges(data=True):
            weights = data.get("timestamps", [])
            if weights:
                avg_time = np.mean(weights)
                std_time = np.std(weights) if len(weights) > 1 else 0
                consistency = 1 - min(std_time / (avg_time + 1), 1)
                data["avg_time"] = avg_time
                data["consistency"] = consistency
                data["confidence"] = min(
                    data["weight"] / max(d["weight"] for _, _, d in G.edges(data=True)) * 0.5 +
                    consistency * 0.5,
                    1.0
                )

        return G

    def _generate_dependency_suppressions(
        self, dependency_graph: nx.DiGraph, alerts: List[Alert]
    ) -> List[SuppressionRule]:
        rules = []
        total_alerts = len(alerts)

        for trigger_rule in dependency_graph.nodes():
            successors = list(dependency_graph.successors(trigger_rule))

            if not successors:
                continue

            high_conf_successors = []
            for succ in successors:
                edge_data = dependency_graph[trigger_rule][succ]
                if edge_data.get("confidence", 0) >= self.min_suppression_confidence:
                    high_conf_successors.append({
                        "rule": succ,
                        "confidence": edge_data["confidence"],
                        "weight": edge_data["weight"],
                        "avg_time": edge_data.get("avg_time", 0),
                    })

            if not high_conf_successors:
                continue

            high_conf_successors.sort(key=lambda x: x["confidence"], reverse=True)
            suppressed = high_conf_successors[:self.max_suppressed_rules]

            support = sum(s["weight"] for s in suppressed) / max(total_alerts, 1)
            if support < self.min_suppression_support:
                continue

            trigger_alerts = [a for a in alerts if a.rule_name == trigger_rule]
            trigger_service = trigger_alerts[0].service if trigger_alerts else None

            suppressed_rules = [s["rule"] for s in suppressed]
            suppressed_services = list(set(
                a.service for a in alerts if a.rule_name in suppressed_rules
            ))

            avg_time = np.mean([s["avg_time"] for s in suppressed]) if suppressed else 60000
            time_window = max(int(avg_time * 2), 60000)

            expected_reduction = sum(s["weight"] for s in suppressed)
            avg_confidence = float(np.mean([s["confidence"] for s in suppressed]))

            rule = SuppressionRule(
                suppression_id=f"dep_{trigger_rule}",
                suppression_type=SuppressionType.DEPENDENCY,
                trigger_rule=trigger_rule,
                suppressed_rules=suppressed_rules,
                trigger_service=trigger_service,
                suppressed_services=suppressed_services,
                time_window=time_window,
                confidence=round(avg_confidence, 4),
                support=round(support, 4),
                expected_reduction=expected_reduction,
                reasoning=f"当{trigger_rule}触发后，{time_window/1000:.0f}秒内抑制{len(suppressed_rules)}个关联规则告警，基于{sum(s['weight'] for s in suppressed)}次共现模式",
                severity="HIGH" if avg_confidence > 0.8 else "MEDIUM",
            )
            rules.append(rule)

        return rules

    def _generate_storm_suppressions(
        self, storm_patterns: List[StormPattern], alerts: List[Alert]
    ) -> List[SuppressionRule]:
        rules = []

        for storm in storm_patterns:
            if not storm.root_cause_candidates:
                continue

            root_cause = storm.root_cause_candidates[0]
            trigger_rule = root_cause["rule_name"]

            suppressed_rules = [
                r for r in storm.rules if r != trigger_rule
            ]

            if not suppressed_rules:
                continue

            time_window = storm.end_time - storm.start_time
            time_window = max(time_window, self.storm_time_window)

            support = storm.alert_count / max(len(alerts), 1)
            confidence = root_cause["score"]

            if confidence < self.min_suppression_confidence:
                continue

            trigger_alerts = [a for a in alerts if a.rule_name == trigger_rule]
            trigger_service = trigger_alerts[0].service if trigger_alerts else None

            suppressed_services = [s for s in storm.services if s != trigger_service]

            rule = SuppressionRule(
                suppression_id=f"storm_{storm.pattern_id}",
                suppression_type=SuppressionType.STORM,
                trigger_rule=trigger_rule,
                suppressed_rules=suppressed_rules,
                trigger_service=trigger_service,
                suppressed_services=suppressed_services,
                time_window=time_window,
                confidence=round(confidence, 4),
                support=round(support, 4),
                expected_reduction=storm.alert_count - 1,
                reasoning=f"检测到{storm.alert_count}次告警风暴，识别{trigger_rule}为根因，抑制{len(suppressed_rules)}个衍生告警，时间窗口{time_window/1000:.0f}秒",
                severity=storm.severity,
            )
            rules.append(rule)

        return rules

    def _generate_redundant_suppressions(
        self, alerts: List[Alert], rules: List[AlertRule]
    ) -> List[SuppressionRule]:
        suppression_rules = []
        rule_names = list(set(a.rule_name for a in alerts))

        for i, rule_a in enumerate(rule_names):
            alerts_a = [a for a in alerts if a.rule_name == rule_a]
            if len(alerts_a) < 5:
                continue

            services_a = set(a.service for a in alerts_a)

            for rule_b in rule_names[i+1:]:
                alerts_b = [a for a in alerts if a.rule_name == rule_b]
                if len(alerts_b) < 5:
                    continue

                services_b = set(a.service for a in alerts_b)

                service_overlap = len(services_a & services_b) / max(len(services_a | services_b), 1)
                if service_overlap < 0.5:
                    continue

                co_occurrence = 0
                for a in alerts_a:
                    for b in alerts_b:
                        if abs(a.start_time - b.start_time) < self.dependency_time_window:
                            co_occurrence += 1
                            break

                support = co_occurrence / max(len(alerts_a), 1)
                if support < self.min_suppression_support:
                    continue

                confidence = min(service_overlap * 0.5 + support * 0.5, 1.0)
                if confidence < self.min_suppression_confidence:
                    continue

                if len(alerts_a) >= len(alerts_b):
                    trigger = rule_a
                    suppressed = [rule_b]
                    expected = len(alerts_b)
                else:
                    trigger = rule_b
                    suppressed = [rule_a]
                    expected = len(alerts_a)

                trigger_alerts = [a for a in alerts if a.rule_name == trigger]
                trigger_service = trigger_alerts[0].service if trigger_alerts else None

                suppression_rule = SuppressionRule(
                    suppression_id=f"red_{trigger}_{suppressed[0]}",
                    suppression_type=SuppressionType.REDUNDANT,
                    trigger_rule=trigger,
                    suppressed_rules=suppressed,
                    trigger_service=trigger_service,
                    suppressed_services=list(services_b if trigger == rule_a else services_a),
                    time_window=self.dependency_time_window,
                    confidence=round(confidence, 4),
                    support=round(support, 4),
                    expected_reduction=expected,
                    reasoning=f"{trigger}与{suppressed[0]}高度冗余，服务重叠率{service_overlap*100:.1f}%，共现率{support*100:.1f}%",
                    severity="MEDIUM",
                )
                suppression_rules.append(suppression_rule)

        return suppression_rules

    def optimize_suppressions(
        self,
        alerts: List[Alert],
        existing_rules: List[AlertRule] = None,
        clusters: List[AlertCluster] = None,
    ) -> Dict[str, Any]:
        if not alerts:
            return {
                "suppression_rules": [],
                "storm_patterns": [],
                "dependency_graph": {},
                "statistics": {},
            }

        storm_patterns = self._detect_storm_patterns(alerts)
        dependency_graph = self._build_dependency_graph(alerts)

        all_rules = []

        dep_rules = self._generate_dependency_suppressions(dependency_graph, alerts)
        all_rules.extend(dep_rules)

        storm_rules = self._generate_storm_suppressions(storm_patterns, alerts)
        all_rules.extend(storm_rules)

        if existing_rules:
            red_rules = self._generate_redundant_suppressions(alerts, existing_rules)
            all_rules.extend(red_rules)

        seen_ids = set()
        unique_rules = []
        for rule in all_rules:
            if rule.suppression_id not in seen_ids:
                seen_ids.add(rule.suppression_id)
                unique_rules.append(rule)

        unique_rules.sort(key=lambda r: r.confidence, reverse=True)

        type_counts = Counter(r.suppression_type for r in unique_rules)
        total_expected = sum(r.expected_reduction for r in unique_rules)
        total_original = len(alerts)

        graph_data = {
            "nodes": list(dependency_graph.nodes()),
            "edges": [
                {
                    "from": u,
                    "to": v,
                    "weight": d.get("weight", 0),
                    "confidence": round(d.get("confidence", 0), 4),
                    "avg_time": round(d.get("avg_time", 0), 2),
                }
                for u, v, d in dependency_graph.edges(data=True)
            ],
        }

        statistics = {
            "total_suppressions": len(unique_rules),
            "by_type": dict(type_counts),
            "storm_patterns_detected": len(storm_patterns),
            "total_expected_reduction": total_expected,
            "reduction_percentage": round(
                total_expected / max(total_original, 1) * 100, 2
            ),
            "avg_confidence": round(
                float(np.mean([r.confidence for r in unique_rules]))
                if unique_rules else 0, 4
            ),
            "high_severity_count": sum(1 for r in unique_rules if r.severity == "HIGH"),
            "rules_suppressed": len(set(
                rule for r in unique_rules for rule in r.suppressed_rules
            )),
        }

        return {
            "suppression_rules": unique_rules,
            "storm_patterns": storm_patterns,
            "dependency_graph": graph_data,
            "statistics": statistics,
        }

    def simulate_suppression(
        self, alerts: List[Alert], suppression_rules: List[SuppressionRule]
    ) -> Dict[str, Any]:
        if not alerts or not suppression_rules:
            return {
                "original_count": len(alerts),
                "suppressed_count": 0,
                "remaining_count": len(alerts),
                "reduction_percent": 0.0,
                "suppression_details": [],
            }

        alerts_sorted = sorted(alerts, key=lambda a: a.start_time)
        suppressed_alerts = set()
        suppression_details = []

        for rule in suppression_rules:
            rule_suppressed = []
            trigger_times = [
                a.start_time for a in alerts_sorted
                if a.rule_name == rule.trigger_rule
            ]

            for alert in alerts_sorted:
                if alert.id in suppressed_alerts:
                    continue
                if alert.rule_name not in rule.suppressed_rules:
                    continue

                for trigger_time in trigger_times:
                    if 0 <= alert.start_time - trigger_time <= rule.time_window:
                        suppressed_alerts.add(alert.id)
                        rule_suppressed.append({
                            "alert_id": alert.id,
                            "rule_name": alert.rule_name,
                            "service": alert.service,
                            "time": alert.start_time,
                            "trigger_time": trigger_time,
                            "delay_ms": alert.start_time - trigger_time,
                        })
                        break

            if rule_suppressed:
                suppression_details.append({
                    "suppression_id": rule.suppression_id,
                    "suppression_type": rule.suppression_type,
                    "trigger_rule": rule.trigger_rule,
                    "suppressed_count": len(rule_suppressed),
                    "suppressed_alerts": rule_suppressed,
                })

        original_count = len(alerts)
        suppressed_count = len(suppressed_alerts)
        remaining_count = original_count - suppressed_count

        return {
            "original_count": original_count,
            "suppressed_count": suppressed_count,
            "remaining_count": remaining_count,
            "reduction_percent": round(
                suppressed_count / max(original_count, 1) * 100, 2
            ),
            "suppression_details": suppression_details,
        }


suppression_optimizer = AlertSuppressionOptimizer()
