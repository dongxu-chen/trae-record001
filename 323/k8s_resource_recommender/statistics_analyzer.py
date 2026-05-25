import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import numpy as np
from scipy import stats

from .data_collector import MetricsData

logger = logging.getLogger(__name__)


@dataclass
class ConfidenceInterval:
    lower: float
    upper: float
    confidence_level: float
    margin_of_error: float

    def __str__(self) -> str:
        return f"[{self.lower:.4f}, {self.upper:.4f}] (±{self.margin_of_error:.4f}, {self.confidence_level * 100:.0f}% CI)"


@dataclass
class ResourceStatistics:
    mean: float
    median: float
    std: float
    min: float
    max: float
    p50: float
    p80: float
    p90: float
    p95: float
    p99: float
    p995: float
    skewness: float
    kurtosis: float
    cv: float
    ci_90: ConfidenceInterval
    ci_95: ConfidenceInterval
    ci_99: ConfidenceInterval
    data_points: int
    duration_hours: float
    percentiles: Dict[str, float] = field(default_factory=dict)


@dataclass
class ResourceForecast:
    horizon: str
    forecast_mean: float
    forecast_lower: float
    forecast_upper: float
    trend: float
    volatility: float


class StatisticsAnalyzer:
    def __init__(self, confidence_levels: Optional[List[float]] = None):
        self.confidence_levels = confidence_levels or [0.90, 0.95, 0.99]

    def analyze(
        self, metrics: MetricsData, resource_type: str = "cpu"
    ) -> Optional[ResourceStatistics]:
        if metrics.is_empty:
            logger.warning("Cannot analyze empty metrics data")
            return None

        if len(metrics.values) < 2:
            logger.warning("Insufficient data points for statistical analysis")
            return None

        values = metrics.values

        mean = float(np.mean(values))
        median = float(np.median(values))
        std = float(np.std(values, ddof=1))
        cv = std / mean if mean > 0 else 0.0

        p50 = float(np.percentile(values, 50))
        p80 = float(np.percentile(values, 80))
        p90 = float(np.percentile(values, 90))
        p95 = float(np.percentile(values, 95))
        p99 = float(np.percentile(values, 99))
        p995 = float(np.percentile(values, 99.5))

        skewness = float(stats.skew(values))
        kurtosis = float(stats.kurtosis(values))

        percentiles = {}
        for p in [1, 5, 10, 25, 50, 75, 80, 90, 95, 98, 99, 99.5, 99.9]:
            percentiles[str(p)] = float(np.percentile(values, p))

        ci_90 = self._calculate_confidence_interval(values, 0.90)
        ci_95 = self._calculate_confidence_interval(values, 0.95)
        ci_99 = self._calculate_confidence_interval(values, 0.99)

        return ResourceStatistics(
            mean=mean,
            median=median,
            std=std,
            min=float(np.min(values)),
            max=float(np.max(values)),
            p50=p50,
            p80=p80,
            p90=p90,
            p95=p95,
            p99=p99,
            p995=p995,
            skewness=skewness,
            kurtosis=kurtosis,
            cv=cv,
            ci_90=ci_90,
            ci_95=ci_95,
            ci_99=ci_99,
            data_points=len(values),
            duration_hours=metrics.duration_hours,
            percentiles=percentiles,
        )

    def _calculate_confidence_interval(
        self, values: np.ndarray, confidence_level: float
    ) -> ConfidenceInterval:
        n = len(values)
        mean = np.mean(values)
        std_err = stats.sem(values)

        if n < 30:
            t_critical = stats.t.ppf((1 + confidence_level) / 2, df=n - 1)
        else:
            t_critical = stats.norm.ppf((1 + confidence_level) / 2)

        margin_of_error = t_critical * std_err
        lower = max(0, mean - margin_of_error)
        upper = mean + margin_of_error

        return ConfidenceInterval(
            lower=float(lower),
            upper=float(upper),
            confidence_level=confidence_level,
            margin_of_error=float(margin_of_error),
        )

    def forecast(
        self,
        metrics: MetricsData,
        horizon_hours: int = 24,
        method: str = "exponential_smoothing",
    ) -> Optional[ResourceForecast]:
        if metrics.is_empty or len(metrics.values) < 10:
            return None

        values = metrics.values
        n = len(values)

        if method == "exponential_smoothing":
            alpha = 0.3
            smoothed = [values[0]]
            for i in range(1, n):
                smoothed.append(alpha * values[i] + (1 - alpha) * smoothed[i - 1])

            recent_values = values[-min(100, n):]
            trend = np.polyfit(range(len(recent_values)), recent_values, 1)[0]
            volatility = np.std(recent_values[-min(20, len(recent_values)):]) / np.mean(
                recent_values[-min(20, len(recent_values)):]
            )

            forecast_mean = float(smoothed[-1] + trend * horizon_hours)
            forecast_std = float(volatility * forecast_mean * np.sqrt(horizon_hours / 24))

            z_score = stats.norm.ppf(0.975)
            forecast_lower = max(0, forecast_mean - z_score * forecast_std)
            forecast_upper = forecast_mean + z_score * forecast_std

        elif method == "naive":
            recent_mean = np.mean(values[-min(100, n):])
            recent_std = np.std(values[-min(100, n):])

            forecast_mean = float(recent_mean)
            z_score = stats.norm.ppf(0.975)
            forecast_lower = max(0, forecast_mean - z_score * recent_std)
            forecast_upper = forecast_mean + z_score * recent_std

            trend = 0
            volatility = recent_std / recent_mean if recent_mean > 0 else 0
        else:
            raise ValueError(f"Unknown forecast method: {method}")

        return ResourceForecast(
            horizon=f"{horizon_hours}h",
            forecast_mean=forecast_mean,
            forecast_lower=forecast_lower,
            forecast_upper=forecast_upper,
            trend=float(trend),
            volatility=float(volatility),
        )

    def detect_anomalies(
        self, metrics: MetricsData, method: str = "iqr", threshold: float = 3.0
    ) -> List[Tuple[int, float, str]]:
        if metrics.is_empty:
            return []

        values = metrics.values
        anomalies = []

        if method == "iqr":
            q1 = np.percentile(values, 25)
            q3 = np.percentile(values, 75)
            iqr = q3 - q1
            lower_bound = q1 - threshold * iqr
            upper_bound = q3 + threshold * iqr

            for i, val in enumerate(values):
                if val < lower_bound:
                    anomalies.append((i, val, "below_lower_bound"))
                elif val > upper_bound:
                    anomalies.append((i, val, "above_upper_bound"))

        elif method == "zscore":
            mean = np.mean(values)
            std = np.std(values)
            if std > 0:
                z_scores = np.abs((values - mean) / std)
                for i, z in enumerate(z_scores):
                    if z > threshold:
                        anomalies.append((i, values[i], f"z_score={z:.2f}"))

        elif method == "mad":
            median = np.median(values)
            mad = np.median(np.abs(values - median))
            if mad > 0:
                modified_z = 0.6745 * (values - median) / mad
                for i, z in enumerate(modified_z):
                    if abs(z) > threshold:
                        anomalies.append((i, values[i], f"modified_z={z:.2f}"))

        return anomalies

    def analyze_stability(self, metrics: MetricsData) -> Dict:
        if metrics.is_empty or len(metrics.values) < 2:
            return {}

        values = metrics.values

        diffs = np.abs(np.diff(values))
        volatility = np.std(diffs) / np.mean(values) if np.mean(values) > 0 else 0

        rolling_std = []
        window_size = min(60, len(values) // 4)
        if window_size >= 5:
            for i in range(window_size, len(values)):
                window = values[i - window_size : i]
                rolling_std.append(np.std(window))
            rolling_std_mean = np.mean(rolling_std) if rolling_std else 0
        else:
            rolling_std_mean = np.std(values)

        noise_ratio = rolling_std_mean / np.mean(values) if np.mean(values) > 0 else 0

        spikes = 0
        if len(values) >= 3:
            local_mean = np.convolve(values, np.ones(5) / 5, mode="same")
            spikes = np.sum((values - local_mean) > 3 * np.std(values))

        return {
            "volatility": float(volatility),
            "noise_ratio": float(noise_ratio),
            "spike_count": int(spikes),
            "coefficient_of_variation": float(np.std(values) / np.mean(values) if np.mean(values) > 0 else 0),
            "max_spike": float(np.max(values) / np.mean(values) if np.mean(values) > 0 else 0),
        }

    def get_safety_margin(
        self,
        stats: ResourceStatistics,
        workload_type: str = "stateless",
        risk_tolerance: str = "medium",
    ) -> float:
        risk_multipliers = {
            "low": {"stateless": 1.2, "stateful": 1.3, "critical": 1.5},
            "medium": {"stateless": 1.5, "stateful": 1.8, "critical": 2.0},
            "high": {"stateless": 1.8, "stateful": 2.0, "critical": 2.5},
        }

        base_multiplier = risk_multipliers.get(risk_tolerance, {}).get(workload_type, 1.5)

        cv_factor = 1.0 + min(stats.cv, 1.0) * 0.5
        skew_factor = 1.0 + max(0, stats.skewness) * 0.3

        safety_margin = base_multiplier * cv_factor * skew_factor
        return float(min(safety_margin, 4.0))
