import numpy as np
from typing import Dict, List, Optional
from datetime import datetime
from collections import deque


class RootCauseAnalyzer:
    def __init__(self, config: dict = None):
        self.config = config or {
            "deviation_threshold": 0.3,
            "min_samples": 10,
            "feature_contribution_threshold": 0.1,
            "history_window": 50,
            "drift_detection_window": 100,
            "drift_significance_level": 0.05,
        }
        self.deviation_history = deque(maxlen=200)
        self.feature_drift_scores = {}

    def analyze_deviation(
        self,
        predicted_ms: float,
        actual_ms: float,
        features: Dict,
        historical_stats: Dict,
        endpoint: str,
        request_data: Dict
    ) -> Dict:
        deviation = actual_ms - predicted_ms
        deviation_percent = deviation / (predicted_ms + 1e-8)
        abs_deviation_percent = abs(deviation_percent)

        self.deviation_history.append({
            "endpoint": endpoint,
            "predicted": predicted_ms,
            "actual": actual_ms,
            "deviation": deviation,
            "deviation_percent": deviation_percent,
            "timestamp": datetime.now().isoformat()
        })

        is_significant = abs_deviation_percent > self.config["deviation_threshold"]

        if not is_significant:
            return {
                "is_significant_deviation": False,
                "deviation_ms": round(deviation, 2),
                "deviation_percent": round(deviation_percent * 100, 2),
                "endpoint": endpoint,
                "root_causes": [],
                "severity": "low",
                "timestamp": datetime.now().isoformat()
            }

        root_causes = []

        root_causes.extend(self._check_downstream_issues(
            request_data, deviation, historical_stats, endpoint
        ))

        root_causes.extend(self._check_temporal_anomaly(
            request_data, deviation, historical_stats, endpoint
        ))

        root_causes.extend(self._check_load_anomaly(
            request_data, deviation, historical_stats, endpoint
        ))

        root_causes.extend(self._check_feature_drift(
            features, historical_stats, endpoint
        ))

        root_causes.extend(self._check_historical_pattern(
            endpoint, deviation, historical_stats
        ))

        root_causes = sorted(root_causes, key=lambda x: x["contribution_score"], reverse=True)

        total_contribution = sum(rc["contribution_score"] for rc in root_causes)
        if total_contribution > 0:
            for rc in root_causes:
                rc["contribution_percent"] = round(rc["contribution_score"] / total_contribution * 100, 1)

        severity = self._assess_severity(deviation_percent, root_causes)

        return {
            "is_significant_deviation": True,
            "deviation_ms": round(deviation, 2),
            "deviation_percent": round(deviation_percent * 100, 2),
            "predicted_ms": round(predicted_ms, 2),
            "actual_ms": round(actual_ms, 2),
            "endpoint": endpoint,
            "root_causes": root_causes[:5],
            "severity": severity,
            "summary": self._generate_summary(root_causes[:3], deviation_percent),
            "recommended_investigations": self._get_investigation_steps(root_causes[:3]),
            "timestamp": datetime.now().isoformat()
        }

    def _check_downstream_issues(
        self,
        request_data: Dict,
        deviation: float,
        historical_stats: Dict,
        endpoint: str
    ) -> List[Dict]:
        causes = []

        has_degradation = request_data.get("has_downstream_degradation", False)
        has_outage = request_data.get("has_downstream_outage", False)
        degraded_count = request_data.get("downstream_degraded_count", 0)
        total_downstream = request_data.get("downstream_count", 0)
        downstream_latency = request_data.get("downstream_total_latency_ms", 0)

        if has_outage:
            contribution = min(1.0, abs(deviation) / (historical_stats.get("endpoint_avg", {}).get(endpoint, 500) + 1e-8) * 0.8)
            causes.append({
                "category": "downstream_outage",
                "description": f"Downstream service outage detected ({degraded_count}/{total_downstream} services affected)",
                "contribution_score": contribution * 0.6,
                "affected_services": degraded_count,
                "evidence": {
                    "has_outage": True,
                    "degraded_count": degraded_count,
                    "total_downstream": total_downstream
                }
            })
        elif has_degradation:
            contribution = min(0.6, abs(deviation) / (historical_stats.get("endpoint_avg", {}).get(endpoint, 500) + 1e-8) * 0.5)
            causes.append({
                "category": "downstream_degradation",
                "description": f"Downstream service degradation ({degraded_count}/{total_downstream} degraded)",
                "contribution_score": contribution * 0.4,
                "affected_services": degraded_count,
                "evidence": {
                    "has_degradation": True,
                    "degraded_count": degraded_count,
                    "downstream_latency_ms": downstream_latency
                }
            })

        endpoint_avg = historical_stats.get("endpoint_avg", {}).get(endpoint, 0)
        if downstream_latency > endpoint_avg * 0.5 and downstream_latency > 100:
            causes.append({
                "category": "high_downstream_latency",
                "description": f"Downstream latency ({downstream_latency:.0f}ms) significantly above baseline",
                "contribution_score": min(0.4, (downstream_latency - endpoint_avg * 0.3) / (endpoint_avg + 1e-8)),
                "evidence": {"downstream_latency_ms": downstream_latency, "baseline_ms": endpoint_avg * 0.3}
            })

        return causes

    def _check_temporal_anomaly(
        self,
        request_data: Dict,
        deviation: float,
        historical_stats: Dict,
        endpoint: str
    ) -> List[Dict]:
        causes = []

        hour = request_data.get("hour")
        is_peak = request_data.get("is_peak_hour", False)

        if deviation > 0 and is_peak:
            causes.append({
                "category": "peak_hour_congestion",
                "description": "Request during peak hours causing elevated latency",
                "contribution_score": 0.25,
                "evidence": {"hour": hour, "is_peak_hour": True}
            })

        return causes

    def _check_load_anomaly(
        self,
        request_data: Dict,
        deviation: float,
        historical_stats: Dict,
        endpoint: str
    ) -> List[Dict]:
        causes = []

        server_load = request_data.get("server_load", 0.5)

        if server_load > 0.8 and deviation > 0:
            contribution = (server_load - 0.8) / 0.2 * 0.4
            causes.append({
                "category": "high_server_load",
                "description": f"Server load critically high ({server_load:.0%})",
                "contribution_score": contribution,
                "evidence": {"server_load": server_load, "threshold": 0.8}
            })

        param_complexity = request_data.get("param_complexity", "simple")
        param_count = request_data.get("param_count", 2)
        payload_size = request_data.get("payload_size_kb", 5)

        if param_complexity == "complex" and deviation > 0:
            causes.append({
                "category": "complex_request_payload",
                "description": f"Complex request parameters ({param_count} params, {payload_size}KB payload)",
                "contribution_score": 0.15,
                "evidence": {"param_count": param_count, "payload_size_kb": payload_size}
            })

        return causes

    def _check_feature_drift(
        self,
        features: Dict,
        historical_stats: Dict,
        endpoint: str
    ) -> List[Dict]:
        causes = []

        for feature_name, current_value in features.items():
            if not isinstance(current_value, (int, float)):
                continue

            endpoint_key = f"endpoint_{feature_name}"
            hist_mean = historical_stats.get(endpoint_key, {}).get(endpoint)
            hist_std = historical_stats.get(endpoint_key, {}).get("_global_std")

            if hist_mean is not None and hist_std is not None and hist_std > 0:
                z_score = abs(current_value - hist_mean) / hist_std
                if z_score > 2.0:
                    self.feature_drift_scores[feature_name] = float(z_score)
                    causes.append({
                        "category": "feature_drift",
                        "description": f"Feature '{feature_name}' significantly drifted (z={z_score:.2f})",
                        "contribution_score": min(0.3, z_score * 0.1),
                        "evidence": {
                            "feature": feature_name,
                            "current_value": current_value,
                            "historical_mean": hist_mean,
                            "z_score": float(z_score)
                        }
                    })

        return causes

    def _check_historical_pattern(
        self,
        endpoint: str,
        deviation: float,
        historical_stats: Dict
    ) -> List[Dict]:
        causes = []

        endpoint_deviations = [
            d for d in self.deviation_history
            if d["endpoint"] == endpoint
        ]

        if len(endpoint_deviations) >= self.config["min_samples"]:
            recent_deviations = [d["deviation_percent"] for d in endpoint_deviations[-self.config["min_samples"]:]]
            avg_deviation = np.mean(recent_deviations)
            positive_rate = sum(1 for d in recent_deviations if d > 0) / len(recent_deviations)

            if avg_deviation > self.config["deviation_threshold"] and positive_rate > 0.7:
                causes.append({
                    "category": "systematic_underprediction",
                    "description": f"Consistent underprediction for {endpoint} (avg deviation: {avg_deviation:.1%})",
                    "contribution_score": 0.3,
                    "evidence": {
                        "avg_deviation_percent": round(avg_deviation * 100, 1),
                        "positive_deviation_rate": round(positive_rate, 2),
                        "sample_size": len(recent_deviations)
                    }
                })
            elif avg_deviation < -self.config["deviation_threshold"] and positive_rate < 0.3:
                causes.append({
                    "category": "systematic_overprediction",
                    "description": f"Consistent overprediction for {endpoint} (avg deviation: {avg_deviation:.1%})",
                    "contribution_score": 0.2,
                    "evidence": {
                        "avg_deviation_percent": round(avg_deviation * 100, 1),
                        "positive_deviation_rate": round(positive_rate, 2),
                        "sample_size": len(recent_deviations)
                    }
                })

        return causes

    def _assess_severity(self, deviation_percent: float, root_causes: List[Dict]) -> str:
        abs_dev = abs(deviation_percent)
        max_contribution = max((rc["contribution_score"] for rc in root_causes), default=0)

        if abs_dev > 1.0 or max_contribution > 0.5:
            return "critical"
        elif abs_dev > 0.5 or max_contribution > 0.3:
            return "high"
        elif abs_dev > 0.3 or max_contribution > 0.15:
            return "medium"
        else:
            return "low"

    def _generate_summary(self, top_causes: List[Dict], deviation_percent: float) -> str:
        if not top_causes:
            return f"Deviation of {deviation_percent:.1%} detected but root cause unclear"

        primary = top_causes[0]
        direction = "under" if deviation_percent > 0 else "over"
        return (
            f"Prediction {direction}estimated by {abs(deviation_percent):.1%}. "
            f"Primary cause: {primary['description']}"
        )

    def _get_investigation_steps(self, top_causes: List[Dict]) -> List[str]:
        steps = []
        categories_seen = set()

        for cause in top_causes:
            cat = cause["category"]
            if cat in categories_seen:
                continue
            categories_seen.add(cat)

            if cat == "downstream_outage":
                steps.append("Check downstream service health dashboards and error logs")
                steps.append("Verify network connectivity to affected downstream services")
            elif cat == "downstream_degradation":
                steps.append("Review downstream service metrics for slow queries or high load")
                steps.append("Check downstream service deployment history for recent changes")
            elif cat == "high_server_load":
                steps.append("Review server resource utilization (CPU, memory, connections)")
                steps.append("Check for resource-intensive background jobs or traffic spikes")
            elif cat == "peak_hour_congestion":
                steps.append("Compare current traffic patterns against typical peak hour baselines")
                steps.append("Consider autoscaling or load shedding strategies")
            elif cat == "feature_drift":
                feature = cause.get("evidence", {}).get("feature", "unknown")
                steps.append(f"Investigate why feature '{feature}' has drifted from historical norms")
                steps.append("Check for data pipeline issues or upstream service changes")
            elif cat == "systematic_underprediction":
                steps.append("Model may need retraining - systematic underprediction detected")
                steps.append("Review recent data distribution changes")
            elif cat == "systematic_overprediction":
                steps.append("Model may need retraining - systematic overprediction detected")
                steps.append("Check if performance optimizations were recently deployed")
            elif cat == "complex_request_payload":
                steps.append("Review if request complexity has increased beyond training distribution")
                steps.append("Consider adding request complexity as a stronger feature")
            elif cat == "high_downstream_latency":
                steps.append("Profile downstream service call latency")
                steps.append("Check for slow database queries or cache misses")

        if not steps:
            steps.append("Collect more data points for pattern analysis")
            steps.append("Monitor for recurring deviation patterns")

        return steps[:5]

    def get_endpoint_analysis_summary(self, endpoint: str) -> Dict:
        endpoint_deviations = [
            d for d in self.deviation_history
            if d["endpoint"] == endpoint
        ]

        if not endpoint_deviations:
            return {"endpoint": endpoint, "total_analyses": 0}

        deviations = [d["deviation_percent"] for d in endpoint_deviations]

        return {
            "endpoint": endpoint,
            "total_analyses": len(endpoint_deviations),
            "avg_deviation_percent": round(float(np.mean(deviations)) * 100, 2),
            "max_deviation_percent": round(float(np.max(np.abs(deviations))) * 100, 2),
            "significant_deviation_rate": round(
                sum(1 for d in deviations if abs(d) > self.config["deviation_threshold"]) / len(deviations), 4
            ),
            "drifted_features": dict(list(self.feature_drift_scores.items())[:10]),
            "last_analysis": endpoint_deviations[-1]["timestamp"] if endpoint_deviations else None
        }