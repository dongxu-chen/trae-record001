import logging
import numpy as np
import pandas as pd
from typing import Dict, Any, List, Tuple, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta

try:
    from statsmodels.tsa.arima.model import ARIMA
    from statsmodels.tsa.stattools import adfuller
    STATSMODELS_AVAILABLE = True
except ImportError:
    STATSMODELS_AVAILABLE = False

logger = logging.getLogger(__name__)


@dataclass
class PredictionResult:
    timestamp: float
    forecast_values: List[float]
    forecast_values_adjusted: List[float]
    confidence_intervals: List[Tuple[float, float]]
    trend: str
    trend_strength: float
    will_exceed_threshold: bool
    predicted_delay_at_risk: List[int]
    network_jitter_factor: float
    jitter_impact: float


class LatencyPredictor:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.forecast_steps = config.get('prediction', {}).get('forecast_steps', 10)
        self.warning_threshold = config.get('monitoring', {}).get('latency_threshold_warning', 5)
        self.model_type = config.get('prediction', {}).get('model', 'arima')
        self.jitter_weight = config.get('prediction', {}).get('jitter_weight', 0.3)
        self.history = []
        self.timestamps = []
        self.network_latency_history = []

    def add_history(self, latency: float, timestamp: Optional[datetime] = None) -> None:
        if timestamp is None:
            timestamp = datetime.now()
        self.history.append(latency)
        self.timestamps.append(timestamp)

        max_points = self.config.get('prediction', {}).get('history_points', 100)
        if len(self.history) > max_points:
            self.history.pop(0)
            self.timestamps.pop(0)

    def add_network_latency(self, network_latency_ms: float) -> None:
        self.network_latency_history.append(network_latency_ms)
        max_points = self.config.get('prediction', {}).get('history_points', 100)
        if len(self.network_latency_history) > max_points:
            self.network_latency_history.pop(0)

    def calculate_network_jitter(self) -> float:
        if len(self.network_latency_history) < 5:
            return 0.0

        recent = self.network_latency_history[-20:]
        if len(recent) < 3:
            return 0.0

        jitter = np.std(recent)
        mean_latency = np.mean(recent)

        if mean_latency > 0:
            jitter_ratio = jitter / mean_latency
        else:
            jitter_ratio = 0.0

        return min(jitter_ratio, 1.0)

    def get_network_trend(self) -> Tuple[str, float]:
        if len(self.network_latency_history) < 5:
            return 'stable', 0.0

        recent = self.network_latency_history[-10:]
        series = pd.Series(recent)
        return self._analyze_trend(series)

    def apply_jitter_correction(self, forecast_values: List[float], jitter_factor: float) -> List[float]:
        if jitter_factor <= 0:
            return forecast_values

        net_trend, net_strength = self.get_network_trend()

        adjusted = []
        for i, val in enumerate(forecast_values):
            jitter_impact = jitter_factor * self.jitter_weight

            if net_trend == 'increasing':
                correction = jitter_impact * (1 + i * 0.1)
                adjusted_val = val * (1 + correction)
            elif net_trend == 'decreasing':
                correction = jitter_impact * 0.5 * (1 + i * 0.05)
                adjusted_val = val * (1 - correction)
            else:
                adjusted_val = val * (1 + jitter_impact * 0.5)

            adjusted.append(max(0, adjusted_val))

        return adjusted

    def predict(self) -> Optional[PredictionResult]:
        if len(self.history) < 10:
            logger.warning("历史数据不足，无法进行预测")
            return None

        jitter_factor = self.calculate_network_jitter()

        if not STATSMODELS_AVAILABLE:
            return self._simple_predict(jitter_factor)

        try:
            return self._arima_predict(jitter_factor)
        except Exception as e:
            logger.error(f"ARIMA预测失败: {str(e)}，使用简单预测")
            return self._simple_predict(jitter_factor)

    def _arima_predict(self, jitter_factor: float) -> Optional[PredictionResult]:
        history_series = pd.Series(self.history)

        is_stationary = self._check_stationary(history_series)

        d = 0 if is_stationary else 1

        try:
            model = ARIMA(history_series, order=(2, d, 1))
            model_fit = model.fit()

            forecast = model_fit.get_forecast(steps=self.forecast_steps)
            forecast_values = forecast.predicted_mean.tolist()
            conf_int = forecast.conf_int(alpha=0.95)

            confidence_intervals = [
                (max(0, conf_int.iloc[i, 0]), conf_int.iloc[i, 1])
                for i in range(conf_int.shape[0])
            ]

        except Exception as e:
            logger.error(f"ARIMA拟合失败: {str(e)}")
            return self._simple_predict(jitter_factor)

        trend, trend_strength = self._analyze_trend(history_series)

        adjusted_values = self.apply_jitter_correction(forecast_values, jitter_factor)

        will_exceed = any(v > self.warning_threshold for v in adjusted_values)
        at_risk = [i for i, v in enumerate(adjusted_values) if v > self.warning_threshold]

        jitter_impact = (sum(adjusted_values) - sum(forecast_values)) / max(sum(forecast_values), 1) * 100

        return PredictionResult(
            timestamp=datetime.now().timestamp(),
            forecast_values=forecast_values,
            forecast_values_adjusted=adjusted_values,
            confidence_intervals=confidence_intervals,
            trend=trend,
            trend_strength=trend_strength,
            will_exceed_threshold=will_exceed,
            predicted_delay_at_risk=at_risk,
            network_jitter_factor=jitter_factor,
            jitter_impact=jitter_impact
        )

    def _simple_predict(self, jitter_factor: float) -> PredictionResult:
        std = 0.0
        if len(self.history) < 2:
            trend = "stable"
            trend_strength = 0.0
            forecast_values = [self.history[-1]] * self.forecast_steps
        else:
            recent = self.history[-10:]
            avg = np.mean(recent)
            std = np.std(recent)

            trend, trend_strength = self._analyze_trend(pd.Series(self.history))

            last_value = self.history[-1]
            forecast_values = []
            for i in range(self.forecast_steps):
                if trend == "increasing":
                    next_val = last_value + (trend_strength * (i + 1))
                elif trend == "decreasing":
                    next_val = max(0, last_value - (trend_strength * (i + 1)))
                else:
                    next_val = last_value
                forecast_values.append(max(0, next_val))

        adjusted_values = self.apply_jitter_correction(forecast_values, jitter_factor)

        confidence_intervals = [
            (max(0, v - std), v + std) for v in adjusted_values]

        will_exceed = any(v > self.warning_threshold for v in adjusted_values)
        at_risk = [i for i, v in enumerate(adjusted_values) if v > self.warning_threshold]

        jitter_impact = (sum(adjusted_values) - sum(forecast_values)) / max(sum(forecast_values), 1) * 100

        return PredictionResult(
            timestamp=datetime.now().timestamp(),
            forecast_values=forecast_values,
            forecast_values_adjusted=adjusted_values,
            confidence_intervals=confidence_intervals,
            trend=trend,
            trend_strength=trend_strength,
            will_exceed_threshold=will_exceed,
            predicted_delay_at_risk=at_risk,
            network_jitter_factor=jitter_factor,
            jitter_impact=jitter_impact
        )

    def _check_stationary(self, series: pd.Series) -> bool:
        try:
            result = adfuller(series.dropna())
            return result[1] <= 0.05
        except Exception:
            return False

    def _analyze_trend(self, series: pd.Series) -> Tuple[str, float]:
        if len(series) < 2:
            return "stable", 0.0

        x = np.arange(len(series))
        y = series.values

        slope = np.polyfit(x, y, 1)[0]

        if slope > 0.1:
            trend = "increasing"
        elif slope < -0.1:
            trend = "decreasing"
        else:
            trend = "stable"

        strength = abs(slope)

        return trend, strength

    def get_prediction_summary(self, result: PredictionResult) -> Dict[str, Any]:
        return {
            "timestamp": result.timestamp,
            "trend": result.trend,
            "trend_strength": result.trend_strength,
            "forecast_next_5_steps": result.forecast_values[:5],
            "forecast_next_5_steps_adjusted": result.forecast_values_adjusted[:5],
            "will_exceed_threshold": result.will_exceed_threshold,
            "risk_steps": result.predicted_delay_at_risk,
            "max_predicted": max(result.forecast_values),
            "min_predicted": min(result.forecast_values),
            "max_predicted_adjusted": max(result.forecast_values_adjusted),
            "network_jitter_factor": result.network_jitter_factor,
            "jitter_impact_percent": result.jitter_impact
        }
