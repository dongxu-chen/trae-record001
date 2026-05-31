import numpy as np
from typing import Dict, Optional, List
from datetime import datetime
from scipy.stats import norm


class TimeoutAdvisor:
    def __init__(self, config: dict = None):
        self.config = config or {
            "target_success_rate": 0.99,
            "min_timeout_ms": 100,
            "max_timeout_ms": 30000,
            "safety_buffer_sigma": 2.0,
            "adaptation_rate": 0.1,
            "min_samples": 20,
            "percentile_targets": [0.95, 0.99, 0.999],
            "cost_weight": 0.3,
        }

    def recommend_timeout(
        self,
        predicted_ms: float,
        predicted_std_ms: float,
        historical_stats: Dict,
        endpoint: str,
        current_timeout_ms: Optional[float] = None,
        recent_actual_times: Optional[List[float]] = None
    ) -> Dict:
        target_sr = self.config["target_success_rate"]
        min_timeout = self.config["min_timeout_ms"]
        max_timeout = self.config["max_timeout_ms"]
        safety_sigma = self.config["safety_buffer_sigma"]

        z_for_target = norm.ppf(target_sr)

        prediction_based = predicted_ms + z_for_target * predicted_std_ms

        endpoint_avg = historical_stats.get("endpoint_avg", {}).get(endpoint, 0)
        endpoint_std = historical_stats.get("endpoint_std", {}).get(endpoint, 0)
        endpoint_p99 = historical_stats.get("endpoint_p99", {}).get(endpoint, 0)

        stats_based = 0
        if endpoint_avg > 0 and endpoint_std > 0:
            stats_based = endpoint_avg + z_for_target * endpoint_std

        p99_based = endpoint_p99 * self.config["safety_buffer_sigma"] / 2 if endpoint_p99 > 0 else 0

        empirical_based = 0
        if recent_actual_times and len(recent_actual_times) >= self.config["min_samples"]:
            empirical_p99 = np.percentile(recent_actual_times, 99)
            empirical_std = np.std(recent_actual_times)
            empirical_based = empirical_p99 + 0.5 * empirical_std

        candidates = {
            "prediction_based": prediction_based,
            "statistics_based": stats_based,
            "p99_based": p99_based,
            "empirical_based": empirical_based,
        }

        active_candidates = [v for v in candidates.values() if v > 0]
        if not active_candidates:
            return self._build_recommendation(
                recommended_ms=max_timeout,
                current_ms=current_timeout_ms,
                candidates=candidates,
                endpoint=endpoint,
                confidence="low",
                reason="insufficient_data"
            )

        weights = {}
        if prediction_based > 0:
            weights["prediction_based"] = 0.4
        if stats_based > 0:
            weights["statistics_based"] = 0.3
        if p99_based > 0:
            weights["p99_based"] = 0.2
        if empirical_based > 0:
            weights["empirical_based"] = 0.1

        total_weight = sum(weights.values())
        weights = {k: v / total_weight for k, v in weights.items()}

        weighted_timeout = sum(candidates[k] * w for k, w in weights.items() if candidates.get(k, 0) > 0)

        if current_timeout_ms and current_timeout_ms > 0:
            adaptation_rate = self.config["adaptation_rate"]
            recommended_ms = current_timeout_ms * (1 - adaptation_rate) + weighted_timeout * adaptation_rate
        else:
            recommended_ms = weighted_timeout

        recommended_ms = max(min_timeout, min(max_timeout, recommended_ms))
        recommended_ms = round(recommended_ms, 0)

        confidence = self._assess_confidence(
            predicted_std_ms, predicted_ms, len(recent_actual_times) if recent_actual_times else 0
        )

        change_analysis = self._analyze_change(current_timeout_ms, recommended_ms, predicted_ms)

        return self._build_recommendation(
            recommended_ms=recommended_ms,
            current_ms=current_timeout_ms,
            candidates=candidates,
            endpoint=endpoint,
            confidence=confidence,
            reason=change_analysis["reason"],
            change_analysis=change_analysis
        )

    def _assess_confidence(
        self,
        predicted_std_ms: float,
        predicted_ms: float,
        sample_count: int
    ) -> str:
        cv = predicted_std_ms / (predicted_ms + 1e-8)

        if sample_count >= 100 and cv < 0.2:
            return "high"
        elif sample_count >= 50 and cv < 0.4:
            return "medium"
        elif sample_count >= 20:
            return "low"
        else:
            return "very_low"

    def _analyze_change(
        self,
        current_ms: Optional[float],
        recommended_ms: float,
        predicted_ms: float
    ) -> Dict:
        if current_ms is None or current_ms <= 0:
            return {
                "direction": "new",
                "change_percent": 0,
                "reason": "no_current_timeout",
                "risk_if_unchanged": "unknown"
            }

        change_percent = (recommended_ms - current_ms) / current_ms * 100

        if change_percent > 20:
            direction = "increase"
            reason = "predicted_latency_higher"
        elif change_percent < -20:
            direction = "decrease"
            reason = "predicted_latency_lower"
        else:
            direction = "maintain"
            reason = "current_timeout_adequate"

        if predicted_ms > current_ms * 0.9:
            risk = "high_timeout_risk"
        elif predicted_ms > current_ms * 0.7:
            risk = "moderate_timeout_risk"
        else:
            risk = "low_timeout_risk"

        return {
            "direction": direction,
            "change_percent": round(change_percent, 1),
            "reason": reason,
            "risk_if_unchanged": risk
        }

    def _build_recommendation(
        self,
        recommended_ms: float,
        current_ms: Optional[float],
        candidates: Dict,
        endpoint: str,
        confidence: str,
        reason: str,
        change_analysis: Dict = None
    ) -> Dict:
        return {
            "endpoint": endpoint,
            "recommended_timeout_ms": recommended_ms,
            "current_timeout_ms": current_ms,
            "confidence": confidence,
            "recommendation_reason": reason,
            "tier_timeouts": {
                "conservative": round(recommended_ms * 1.3, 0),
                "balanced": recommended_ms,
                "aggressive": round(recommended_ms * 0.85, 0),
            },
            "component_timeouts_ms": {k: round(v, 0) for k, v in candidates.items() if v > 0},
            "change_analysis": change_analysis,
            "timestamp": datetime.now().isoformat()
        }

    def batch_recommend(
        self,
        endpoints: List[str],
        historical_stats: Dict,
        predictions: Dict[str, Dict],
        current_timeouts: Dict[str, float] = None
    ) -> Dict[str, Dict]:
        recommendations = {}
        current_timeouts = current_timeouts or {}

        for endpoint in endpoints:
            pred = predictions.get(endpoint, {})
            recommended = self.recommend_timeout(
                predicted_ms=pred.get("predicted_response_time_ms", historical_stats.get("endpoint_avg", {}).get(endpoint, 500)),
                predicted_std_ms=pred.get("prediction_std_ms", 50),
                historical_stats=historical_stats,
                endpoint=endpoint,
                current_timeout_ms=current_timeouts.get(endpoint)
            )
            recommendations[endpoint] = recommended

        return recommendations