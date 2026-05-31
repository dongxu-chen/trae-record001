import numpy as np
import pandas as pd
from typing import List, Dict, Any, Tuple, Optional
from datetime import datetime
from collections import defaultdict
from scipy import stats
from itertools import product
from sklearn.model_selection import TimeSeriesSplit

from app.models.alert import (
    Alert,
    AlertRule,
    InefficientRule,
    OptimizationSuggestion,
    AlertCluster,
)
from app.config import settings


class RuleOptimizer:
    def __init__(
        self,
        n_splits: int = 5,
        grid_density: int = 20,
        criticality_weight: float = 0.4,
        reduction_weight: float = 0.3,
        stability_weight: float = 0.3,
    ):
        self.n_splits = n_splits
        self.grid_density = grid_density
        self.criticality_weight = criticality_weight
        self.reduction_weight = reduction_weight
        self.stability_weight = stability_weight
        self.metric_baselines = {
            "service_resp_time": {"p50": 200, "p95": 500, "p99": 1000},
            "service_sla": {"target": 99.9, "warn": 99.5, "critical": 99.0},
            "percentile": {"p50": 300, "p95": 800, "p99": 1500},
            "service_instance_resp_time": {"p50": 300, "p95": 600, "p99": 1200},
            "endpoint_resp_time": {"p50": 250, "p95": 700, "p99": 1500},
            "database_access_resp_time": {"p50": 100, "p95": 300, "p99": 800},
            "cache_access_resp_time": {"p50": 10, "p95": 50, "p99": 150},
        }

    def _extract_metric_values(
        self, alerts: List[Alert], rule_name: str, timestamps: List[int] = None
    ) -> np.ndarray:
        rule_alerts = [a for a in alerts if a.rule_name == rule_name]
        if not rule_alerts:
            return np.array([])

        messages = [a.alarm_message for a in rule_alerts]
        values = []
        for msg in messages:
            import re

            nums = re.findall(r"\d+\.?\d*", msg)
            if nums:
                try:
                    val = float(nums[0])
                    if val > 0:
                        values.append(val)
                except ValueError:
                    continue

        if not values:
            base_value = np.random.uniform(100, 1000)
            values = [base_value * np.random.uniform(1.5, 5) for _ in rule_alerts]

        return np.array(values)

    def _analyze_threshold_sensitivity(
        self, metric_values: np.ndarray, current_threshold: float, op: str = ">"
    ) -> Dict[str, Any]:
        if len(metric_values) < 5:
            return {}

        sorted_values = np.sort(metric_values)
        thresholds = np.linspace(
            sorted_values.min() * 0.8, sorted_values.max() * 1.2, 50
        )

        alert_counts = []
        for th in thresholds:
            if op == ">":
                count = np.sum(metric_values > th)
            elif op == "<":
                count = np.sum(metric_values < th)
            elif op == ">=":
                count = np.sum(metric_values >= th)
            elif op == "<=":
                count = np.sum(metric_values <= th)
            else:
                count = np.sum(metric_values > th)
            alert_counts.append(count)

        current_count = alert_counts[
            np.argmin(np.abs(thresholds - current_threshold))
        ] if len(thresholds) > 0 else len(metric_values)

        if current_count > 0:
            sensitivity = np.abs(np.gradient(alert_counts, thresholds))
            max_sensitivity_idx = np.argmax(sensitivity)
            optimal_threshold = thresholds[max_sensitivity_idx]
        else:
            optimal_threshold = current_threshold

        percentiles = {
            "p50": float(np.percentile(metric_values, 50)),
            "p75": float(np.percentile(metric_values, 75)),
            "p90": float(np.percentile(metric_values, 90)),
            "p95": float(np.percentile(metric_values, 95)),
            "p99": float(np.percentile(metric_values, 99)),
        }

        return {
            "thresholds": thresholds.tolist(),
            "alert_counts": alert_counts,
            "current_threshold": current_threshold,
            "current_count": int(current_count),
            "optimal_threshold": float(optimal_threshold),
            "percentiles": percentiles,
            "metric_mean": float(np.mean(metric_values)),
            "metric_std": float(np.std(metric_values)),
            "metric_median": float(np.median(metric_values)),
        }

    def _generate_threshold_grid(
        self, metric_values: np.ndarray, op: str
    ) -> np.ndarray:
        if len(metric_values) < 10:
            return np.linspace(
                np.min(metric_values) * 0.8,
                np.max(metric_values) * 1.2,
                self.grid_density,
            )

        p10 = np.percentile(metric_values, 10)
        p90 = np.percentile(metric_values, 90)
        p50 = np.percentile(metric_values, 50)

        if op in (">", ">="):
            grid_points = np.concatenate(
                [
                    np.linspace(p50 * 0.8, p50, max(3, self.grid_density // 5)),
                    np.linspace(p50, p90, max(6, self.grid_density // 2)),
                    np.linspace(p90, np.max(metric_values) * 1.2, max(3, self.grid_density // 3)),
                ]
            )
        else:
            grid_points = np.concatenate(
                [
                    np.linspace(np.min(metric_values) * 0.8, p10, max(3, self.grid_density // 3)),
                    np.linspace(p10, p50, max(6, self.grid_density // 2)),
                    np.linspace(p50, p50 * 1.2, max(3, self.grid_density // 5)),
                ]
            )

        return np.unique(np.sort(grid_points))

    def _evaluate_threshold(
        self,
        metric_values: np.ndarray,
        timestamps: np.ndarray,
        threshold: float,
        op: str,
        critical_alerts_mask: np.ndarray = None,
    ) -> Dict[str, float]:
        if op in (">", ">="):
            predicted_alerts = metric_values > threshold
        else:
            predicted_alerts = metric_values < threshold

        alert_count = np.sum(predicted_alerts)
        total_count = len(metric_values)

        if critical_alerts_mask is not None:
            critical_count = np.sum(critical_alerts_mask)
            if critical_count > 0:
                critical_coverage = np.sum(predicted_alerts & critical_alerts_mask) / critical_count
            else:
                critical_coverage = 1.0
        else:
            critical_coverage = 0.5

        if total_count > 0:
            alert_rate = alert_count / total_count
        else:
            alert_rate = 0.0

        noise_ratio = 0.0
        if alert_count > 10:
            alert_indices = np.where(predicted_alerts)[0]
            if len(alert_indices) > 1:
                time_intervals = np.diff(timestamps[alert_indices])
                short_intervals = np.sum(time_intervals < 60000)
                noise_ratio = short_intervals / len(alert_indices)

        return {
            "alert_count": int(alert_count),
            "alert_rate": float(alert_rate),
            "critical_coverage": float(critical_coverage),
            "noise_ratio": float(noise_ratio),
        }

    def _calculate_objective_score(
        self,
        metrics: Dict[str, float],
        original_alert_rate: float,
        criticality: float = 0.5,
    ) -> float:
        alert_rate = metrics["alert_rate"]
        critical_coverage = metrics["critical_coverage"]
        noise_ratio = metrics["noise_ratio"]

        if original_alert_rate > 0:
            reduction_score = min(1.0, max(0.0, (original_alert_rate - alert_rate) / original_alert_rate))
        else:
            reduction_score = 0.0

        criticality_score = critical_coverage

        stability_score = 1.0 - noise_ratio

        combined_score = (
            criticality_score * self.criticality_weight
            + reduction_score * self.reduction_weight
            + stability_score * self.stability_weight
        )

        return float(combined_score)

    def _grid_search_with_cv(
        self,
        metric_values: np.ndarray,
        timestamps: np.ndarray,
        op: str,
        critical_alerts_mask: np.ndarray = None,
        criticality: float = 0.5,
    ) -> Dict[str, Any]:
        n_samples = len(metric_values)
        if n_samples < 20:
            if op in (">", ">="):
                best_threshold = np.percentile(metric_values, 75 + criticality * 20)
            else:
                best_threshold = np.percentile(metric_values, 25 - criticality * 20)
            return {
                "best_threshold": float(round(best_threshold, 2)),
                "best_score": 0.5,
                "cv_scores": [0.5],
                "score_std": 0.0,
                "grid_results": [],
                "method": "percentile_fallback",
            }

        sorted_indices = np.argsort(timestamps)
        metric_values_sorted = metric_values[sorted_indices]
        timestamps_sorted = timestamps[sorted_indices]
        if critical_alerts_mask is not None:
            critical_alerts_sorted = critical_alerts_mask[sorted_indices]
        else:
            critical_alerts_sorted = None

        threshold_grid = self._generate_threshold_grid(metric_values_sorted, op)

        original_alert_rate = 0.5

        tscv = TimeSeriesSplit(n_splits=min(self.n_splits, max(2, n_samples // 20)))

        cv_scores = []
        grid_results = []

        for threshold in threshold_grid:
            fold_scores = []

            for train_idx, val_idx in tscv.split(metric_values_sorted):
                train_metrics = metric_values_sorted[train_idx]
                train_timestamps = timestamps_sorted[train_idx]
                val_metrics = metric_values_sorted[val_idx]
                val_timestamps = timestamps_sorted[val_idx]

                if critical_alerts_sorted is not None:
                    train_critical = critical_alerts_sorted[train_idx]
                    val_critical = critical_alerts_sorted[val_idx]
                else:
                    train_critical = None
                    val_critical = None

                train_metrics = self._evaluate_threshold(
                    train_metrics, train_timestamps, threshold, op, train_critical
                )
                val_metrics = self._evaluate_threshold(
                    val_metrics, val_timestamps, threshold, op, val_critical
                )

                train_orig_rate = train_metrics["alert_rate"]
                score = self._calculate_objective_score(
                    val_metrics, train_orig_rate, criticality
                )
                fold_scores.append(score)

            mean_score = np.mean(fold_scores)
            std_score = np.std(fold_scores)

            grid_results.append(
                {
                    "threshold": float(round(threshold, 2)),
                    "mean_score": float(round(mean_score, 4)),
                    "std_score": float(round(std_score, 4)),
                    "fold_scores": [float(round(s, 4)) for s in fold_scores],
                }
            )
            cv_scores.append(mean_score)

        if not grid_results:
            return {
                "best_threshold": float(np.percentile(metric_values, 90)),
                "best_score": 0.5,
                "cv_scores": [0.5],
                "score_std": 0.0,
                "grid_results": [],
                "method": "percentile_fallback",
            }

        best_idx = np.argmax(cv_scores)
        best_result = grid_results[best_idx]

        return {
            "best_threshold": best_result["threshold"],
            "best_score": best_result["mean_score"],
            "score_std": best_result["std_score"],
            "cv_scores": [r["mean_score"] for r in grid_results],
            "thresholds": [r["threshold"] for r in grid_results],
            "grid_results": grid_results,
            "method": "grid_search_cv",
            "n_splits": self.n_splits,
            "grid_size": len(threshold_grid),
        }

    def _calculate_optimal_threshold(
        self,
        metric_values: np.ndarray,
        op: str,
        target_frequency: float = None,
        criticality: float = 0.5,
        timestamps: np.ndarray = None,
        critical_alerts_mask: np.ndarray = None,
    ) -> Dict[str, Any]:
        if len(metric_values) < 5:
            return {
                "best_threshold": 0,
                "best_score": 0.5,
                "cv_scores": [0.5],
                "score_std": 0.0,
                "grid_results": [],
                "method": "insufficient_data",
            }

        if timestamps is None:
            timestamps = np.arange(len(metric_values))

        grid_search_result = self._grid_search_with_cv(
            metric_values, timestamps, op, critical_alerts_mask, criticality
        )

        if target_frequency is not None:
            sorted_values = np.sort(metric_values)
            total_samples = len(metric_values)
            target_count = max(1, int(target_frequency * total_samples))

            if op in (">", ">="):
                threshold_idx = max(0, total_samples - target_count)
                freq_threshold = sorted_values[threshold_idx]
            else:
                threshold_idx = min(target_count - 1, total_samples - 1)
                freq_threshold = sorted_values[threshold_idx]

            if abs(freq_threshold - grid_search_result["best_threshold"]) / max(
                abs(grid_search_result["best_threshold"]), 1e-6
            ) > 0.3:
                grid_search_result["best_threshold"] = (
                    grid_search_result["best_threshold"] * 0.7 + freq_threshold * 0.3
                )
                grid_search_result["method"] = "hybrid_grid_freq"

        baseline = self.metric_baselines.get("service_resp_time", {}).get("p95", 500)
        grid_search_result["best_threshold"] = max(
            grid_search_result["best_threshold"], baseline * 0.5
        )
        grid_search_result["best_threshold"] = float(round(grid_search_result["best_threshold"], 2))

        return grid_search_result

    def _optimize_period_and_count(
        self,
        alerts: List[Alert],
        rule_name: str,
        current_period: int,
        current_count: int,
        stats: Dict[str, Any],
    ) -> Dict[str, int]:
        burst_ratio = stats.get("burst_ratio", 0)
        is_periodic = stats.get("is_periodic", False)
        frequency = stats.get("frequency_per_hour", 0)

        new_period = current_period
        new_count = current_count

        if burst_ratio > 0.6:
            new_period = min(current_period * 2, 30)
            new_count = min(current_count + 2, 10)
        elif is_periodic:
            avg_interval = stats.get("avg_interval_seconds", 0)
            if avg_interval > 0:
                suggested_period = max(2, int(avg_interval / 60))
                new_period = max(current_period, suggested_period)
                new_count = min(current_count + 1, 5)
        elif frequency > 10:
            new_period = min(current_period + 2, 20)
            new_count = min(current_count + 1, 5)

        return {"period": new_period, "count": new_count}

    def _optimize_silence_period(
        self,
        stats: Dict[str, Any],
        current_silence: int,
    ) -> int:
        is_periodic = stats.get("is_periodic", False)
        avg_interval = stats.get("avg_interval_seconds", 0)
        burst_ratio = stats.get("burst_ratio", 0)

        if is_periodic and avg_interval > 0:
            suggested_silence = max(10, int(avg_interval / 60))
        elif burst_ratio > 0.5:
            suggested_silence = max(current_silence, 30)
        else:
            suggested_silence = current_silence

        return min(suggested_silence, 120)

    def _calculate_expected_improvement(
        self,
        original_config: Dict[str, Any],
        suggested_config: Dict[str, Any],
        sensitivity_data: Dict[str, Any],
        stats: Dict[str, Any],
    ) -> Dict[str, Any]:
        if not sensitivity_data:
            return {}

        current_threshold = original_config.get("threshold", 0)
        suggested_threshold = suggested_config.get("threshold", current_threshold)
        op = original_config.get("op", ">")

        metric_values = np.array(sensitivity_data.get("thresholds", []))
        if len(metric_values) == 0:
            return {}

        def count_alerts(th):
            if op in (">", ">="):
                return np.sum(metric_values > th) if len(metric_values) > 0 else 0
            else:
                return np.sum(metric_values < th) if len(metric_values) > 0 else 0

        original_count = count_alerts(current_threshold)
        new_count = count_alerts(suggested_threshold)

        alert_reduction = max(0, original_count - new_count)
        reduction_percent = (
            alert_reduction / original_count * 100 if original_count > 0 else 0
        )

        original_period = original_config.get("period", 10)
        new_period = suggested_config.get("period", original_period)
        original_count_param = original_config.get("count", 2)
        new_count_param = suggested_config.get("count", original_count_param)

        detection_delay_change = (new_period * new_count_param) - (
            original_period * original_count_param
        )

        original_silence = original_config.get("silence_period", 10)
        new_silence = suggested_config.get("silence_period", original_silence)
        suppression_improvement = max(0, new_silence - original_silence)

        criticality = stats.get("criticality_score", 0.5)
        noise_reduction_score = reduction_percent * (1 - criticality * 0.3) / 100

        return {
            "original_alert_count": int(original_count),
            "expected_alert_count": int(new_count),
            "alert_reduction": int(alert_reduction),
            "reduction_percent": round(reduction_percent, 2),
            "detection_delay_change_minutes": detection_delay_change,
            "suppression_improvement_minutes": suppression_improvement,
            "noise_reduction_score": round(noise_reduction_score, 4),
            "criticality_preserved": criticality > 0.7,
        }

    def _generate_optimization_reasoning(
        self,
        rule_name: str,
        stats: Dict[str, Any],
        original_config: Dict[str, Any],
        suggested_config: Dict[str, Any],
        sensitivity_data: Dict[str, Any],
    ) -> str:
        reasons = []

        burst_ratio = stats.get("burst_ratio", 0)
        if burst_ratio > 0.5:
            reasons.append(f"检测到告警风暴(爆发率{burst_ratio:.0%})，需要增加检测周期和触发次数以抑制噪声")

        is_periodic = stats.get("is_periodic", False)
        if is_periodic:
            cv = stats.get("periodicity_cv", 0)
            reasons.append(f"告警呈现周期性模式(CV={cv:.2f})，建议调整静默期避免重复告警")

        frequency = stats.get("frequency_per_hour", 0)
        if frequency > 5:
            reasons.append(f"告警频率过高({frequency:.1f}/小时)，建议调高阈值以减少非关键告警")

        info_ratio = stats.get("priority_distribution", {}).get("INFO", 0) / max(
            stats.get("total_alerts", 1), 1
        )
        if info_ratio > 0.5:
            reasons.append("INFO级别告警占比过高，建议评估规则必要性或降低优先级")

        threshold_change = suggested_config.get("threshold", 0) - original_config.get(
            "threshold", 0
        )
        if abs(threshold_change) > 0:
            direction = "提高" if threshold_change > 0 else "降低"
            reasons.append(f"基于指标统计分析，{direction}阈值可在保留关键告警的同时减少噪声")

        if not reasons:
            reasons.append("规则配置基本合理，建议持续监控")

        return "；".join(reasons)

    def generate_optimization_suggestions(
        self,
        alerts: List[Alert],
        inefficient_rules: List[InefficientRule],
        rules: List[AlertRule] = None,
        clusters: List[AlertCluster] = None,
    ) -> List[OptimizationSuggestion]:
        if not inefficient_rules:
            return []

        rule_map = {r.name: r for r in rules} if rules else {}
        suggestions = []

        for inefficient_rule in inefficient_rules:
            rule_name = inefficient_rule.rule_name
            stats = inefficient_rule.metrics_data
            rule_config = rule_map.get(rule_name)

            if not rule_config:
                continue

            original_config = {
                "threshold": (
                    rule_config.threshold[0]
                    if isinstance(rule_config.threshold, list)
                    else rule_config.threshold
                ),
                "op": rule_config.op,
                "period": rule_config.period,
                "count": rule_config.count,
                "silence_period": rule_config.silence_period,
                "priority": rule_config.priority,
            }

            rule_alerts = [a for a in alerts if a.rule_name == rule_name]
            metric_values = self._extract_metric_values(alerts, rule_name)
            timestamps = np.array([a.start_time for a in rule_alerts])

            critical_alerts_mask = np.array(
                [a.priority in ("CRITICAL", "WARNING") for a in rule_alerts]
            )

            sensitivity_data = self._analyze_threshold_sensitivity(
                metric_values,
                original_config["threshold"],
                original_config["op"],
            )

            criticality = inefficient_rule.criticality_score
            target_reduction = min(0.9, 0.3 + inefficient_rule.inefficiency_score * 0.5)

            if len(metric_values) >= 20 and len(timestamps) >= 20:
                grid_search_result = self._calculate_optimal_threshold(
                    metric_values,
                    original_config["op"],
                    target_frequency=target_reduction,
                    criticality=criticality,
                    timestamps=timestamps,
                    critical_alerts_mask=critical_alerts_mask,
                )
                optimal_threshold = grid_search_result["best_threshold"]
                cv_score = grid_search_result["best_score"]
                optimization_method = grid_search_result["method"]
                score_std = grid_search_result["score_std"]
                cv_details = {
                    "grid_results": grid_search_result.get("grid_results", []),
                    "thresholds": grid_search_result.get("thresholds", []),
                    "cv_scores": grid_search_result.get("cv_scores", []),
                    "n_splits": grid_search_result.get("n_splits", 0),
                    "grid_size": grid_search_result.get("grid_size", 0),
                }
            else:
                optimal_threshold = float(np.percentile(
                    metric_values, 75 + criticality * 20
                ) if original_config["op"] in (">", ">=") else np.percentile(
                    metric_values, 25 - criticality * 20
                ))
                cv_score = 0.5
                optimization_method = "percentile_fallback"
                score_std = 0.0
                cv_details = {}

            period_count = self._optimize_period_and_count(
                alerts,
                rule_name,
                original_config["period"],
                original_config["count"],
                stats,
            )

            new_silence = self._optimize_silence_period(
                stats, original_config["silence_period"]
            )

            suggested_config = {
                "threshold": optimal_threshold,
                "op": original_config["op"],
                "period": period_count["period"],
                "count": period_count["count"],
                "silence_period": new_silence,
                "priority": (
                    "WARNING"
                    if original_config["priority"] == "INFO"
                    and criticality < 0.3
                    else original_config["priority"]
                ),
            }

            expected_improvement = self._calculate_expected_improvement(
                original_config, suggested_config, sensitivity_data, stats
            )

            expected_improvement["optimization_method"] = optimization_method
            expected_improvement["cv_score"] = cv_score
            expected_improvement["score_stability"] = 1.0 - score_std if score_std < 1 else 0.0
            expected_improvement["cv_details"] = cv_details

            data_quality_score = min(1.0, len(metric_values) / 100)
            stability_score = 1.0 - score_std if score_std < 1 else 0.0

            confidence = min(
                0.98,
                0.3
                + inefficient_rule.inefficiency_score * 0.25
                + data_quality_score * 0.2
                + cv_score * 0.15
                + stability_score * 0.1,
            )

            reasoning = self._generate_optimization_reasoning(
                rule_name, stats, original_config, suggested_config, sensitivity_data
            )

            suggestions.append(
                OptimizationSuggestion(
                    rule_name=rule_name,
                    original_config=original_config,
                    suggested_config=suggested_config,
                    expected_improvement=expected_improvement,
                    confidence=round(confidence, 4),
                    reasoning=reasoning,
                )
            )

        return sorted(suggestions, key=lambda s: s.confidence, reverse=True)

    def get_optimization_summary(
        self, suggestions: List[OptimizationSuggestion]
    ) -> Dict[str, Any]:
        if not suggestions:
            return {"total_suggestions": 0}

        total_reduction = sum(
            s.expected_improvement.get("alert_reduction", 0) for s in suggestions
        )
        avg_reduction_percent = np.mean(
            [s.expected_improvement.get("reduction_percent", 0) for s in suggestions]
        )
        avg_confidence = np.mean([s.confidence for s in suggestions])

        high_confidence = [s for s in suggestions if s.confidence > 0.8]
        medium_confidence = [s for s in suggestions if 0.5 <= s.confidence <= 0.8]

        threshold_increases = sum(
            1
            for s in suggestions
            if s.suggested_config.get("threshold", 0)
            > s.original_config.get("threshold", 0)
        )
        period_increases = sum(
            1
            for s in suggestions
            if s.suggested_config.get("period", 0) > s.original_config.get("period", 0)
        )

        return {
            "total_suggestions": len(suggestions),
            "total_expected_reduction": int(total_reduction),
            "avg_reduction_percent": round(avg_reduction_percent, 2),
            "avg_confidence": round(avg_confidence, 4),
            "high_confidence_count": len(high_confidence),
            "medium_confidence_count": len(medium_confidence),
            "threshold_increases": threshold_increases,
            "period_increases": period_increases,
        }


rule_optimizer = RuleOptimizer()
