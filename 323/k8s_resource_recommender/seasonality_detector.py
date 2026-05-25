import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from enum import Enum

import numpy as np
from scipy import signal, stats

from .data_collector import MetricsData, PodResourceData
from .statistics_analyzer import ResourceStatistics, StatisticsAnalyzer

logger = logging.getLogger(__name__)


class SeasonalPattern(str, Enum):
    DAILY = "daily"
    WEEKLY = "weekly"
    HOURLY = "hourly"
    NONE = "none"


@dataclass
class SeasonalPeriod:
    pattern: SeasonalPattern
    period_hours: float
    confidence: float
    peak_values: np.ndarray
    trough_values: np.ndarray
    peak_timestamps: np.ndarray
    trough_timestamps: np.ndarray
    peak_to_trough_ratio: float


@dataclass
class SeasonalityAnalysis:
    pattern: SeasonalPattern
    confidence: float
    dominant_period_hours: Optional[float]
    peak_periods: List[SeasonalPeriod] = field(default_factory=list)
    seasonal_strength: float = 0.0
    peak_resource_multiplier: float = 1.0
    trough_resource_multiplier: float = 1.0
    recommendations: List[str] = field(default_factory=list)
    has_strong_seasonality: bool = False


@dataclass
class SeasonalResourceRecommendation:
    base_recommendation: float
    peak_recommendation: float
    trough_recommendation: float
    seasonal_adjustment_factor: float
    peak_schedule: List[str]
    trough_schedule: List[str]
    is_seasonal: bool = False


class SeasonalityDetector:
    def __init__(
        self,
        analyzer: Optional[StatisticsAnalyzer] = None,
        min_data_points: int = 100,
        seasonality_threshold: float = 0.3,
        confidence_threshold: float = 0.7,
    ):
        self.analyzer = analyzer or StatisticsAnalyzer()
        self.min_data_points = min_data_points
        self.seasonality_threshold = seasonality_threshold
        self.confidence_threshold = confidence_threshold

    def detect_seasonality(
        self,
        metrics_data: MetricsData,
        resource_type: str = "cpu",
    ) -> SeasonalityAnalysis:
        if metrics_data.values is None or len(metrics_data.values) < self.min_data_points:
            return SeasonalityAnalysis(
                pattern=SeasonalPattern.NONE,
                confidence=0.0,
                dominant_period_hours=None,
                recommendations=["数据点不足，无法检测季节性"],
            )

        values = metrics_data.values
        timestamps = metrics_data.timestamps

        if timestamps is None or len(timestamps) < 2:
            return SeasonalityAnalysis(
                pattern=SeasonalPattern.NONE,
                confidence=0.0,
                dominant_period_hours=None,
                recommendations=["时间戳数据不足"],
            )

        from datetime import datetime
        if isinstance(timestamps[0], datetime):
            timestamps = np.array([t.timestamp() for t in timestamps])

        total_duration_hours = (timestamps[-1] - timestamps[0]) / 3600

        if total_duration_hours < 24:
            return SeasonalityAnalysis(
                pattern=SeasonalPattern.NONE,
                confidence=0.0,
                dominant_period_hours=None,
                recommendations=["数据时长不足24小时，无法检测季节性"],
            )

        detrended = self._detrend(values)
        autocorr = self._autocorrelation(detrended)

        peak_periods = []
        best_pattern = SeasonalPattern.NONE
        best_confidence = 0.0
        best_period = None

        patterns_to_check = [
            (SeasonalPattern.HOURLY, 1.0, 0.5, 2.0),
            (SeasonalPattern.DAILY, 24.0, 20.0, 28.0),
            (SeasonalPattern.WEEKLY, 168.0, 140.0, 196.0),
        ]

        for pattern, expected_hours, min_hours, max_hours in patterns_to_check:
            if total_duration_hours < expected_hours * 2:
                continue

            period_info = self._check_periodicity(
                detrended, timestamps, autocorr, expected_hours, min_hours, max_hours
            )

            if period_info and period_info.confidence >= self.confidence_threshold:
                peak_periods.append(period_info)
                if period_info.confidence > best_confidence:
                    best_confidence = period_info.confidence
                    best_pattern = pattern
                    best_period = period_info.period_hours

        seasonal_strength = self._calculate_seasonal_strength(detrended, autocorr)
        has_strong_seasonality = seasonal_strength >= self.seasonality_threshold

        recommendations = self._generate_recommendations(
            best_pattern, best_confidence, seasonal_strength, total_duration_hours
        )

        peak_multiplier = 1.0
        trough_multiplier = 1.0
        if peak_periods:
            best_peak = max(peak_periods, key=lambda p: p.confidence)
            peak_multiplier = np.percentile(best_peak.peak_values, 90) / np.mean(values)
            trough_multiplier = np.percentile(best_peak.trough_values, 10) / np.mean(values)

        return SeasonalityAnalysis(
            pattern=best_pattern,
            confidence=best_confidence,
            dominant_period_hours=best_period,
            peak_periods=peak_periods,
            seasonal_strength=seasonal_strength,
            peak_resource_multiplier=peak_multiplier,
            trough_resource_multiplier=trough_multiplier,
            recommendations=recommendations,
            has_strong_seasonality=has_strong_seasonality,
        )

    def _detrend(self, values: np.ndarray) -> np.ndarray:
        try:
            if len(values) >= 50:
                window = min(len(values) // 4, 50)
                trend = np.convolve(values, np.ones(window) / window, mode="same")
                return values - trend
            return values - np.mean(values)
        except Exception:
            return values - np.mean(values)

    def _autocorrelation(self, values: np.ndarray, max_lag: Optional[int] = None) -> np.ndarray:
        n = len(values)
        if max_lag is None:
            max_lag = min(n // 3, 500)

        mean = np.mean(values)
        var = np.var(values)

        if var == 0:
            return np.zeros(max_lag)

        autocorr = np.zeros(max_lag)
        for lag in range(1, max_lag + 1):
            cov = np.mean((values[:-lag] - mean) * (values[lag:] - mean))
            autocorr[lag - 1] = cov / var

        return autocorr

    def _check_periodicity(
        self,
        detrended: np.ndarray,
        timestamps: np.ndarray,
        autocorr: np.ndarray,
        expected_hours: float,
        min_hours: float,
        max_hours: float,
    ) -> Optional[SeasonalPeriod]:
        if len(timestamps) < 2:
            return None

        from datetime import datetime
        if isinstance(timestamps[0], datetime):
            timestamps = np.array([t.timestamp() for t in timestamps])

        avg_interval = (timestamps[-1] - timestamps[0]) / (len(timestamps) - 1)
        expected_lag = int(expected_hours * 3600 / avg_interval)
        min_lag = int(min_hours * 3600 / avg_interval)
        max_lag = int(max_hours * 3600 / avg_interval)

        search_start = max(1, min_lag)
        search_end = min(len(autocorr), max_lag)

        if search_start >= search_end:
            return None

        search_region = autocorr[search_start - 1 : search_end]
        if len(search_region) == 0:
            return None

        peak_idx = np.argmax(search_region) + search_start
        peak_autocorr = autocorr[peak_idx - 1] if peak_idx <= len(autocorr) else 0

        if peak_autocorr < 0.3:
            return None

        detected_period_hours = peak_idx * avg_interval / 3600

        peaks, troughs, peak_times, trough_times = self._find_peaks_and_troughs(
            detrended, timestamps, detected_period_hours
        )

        if len(peaks) == 0 or len(troughs) == 0:
            return None

        peak_mean = np.mean(peaks)
        trough_mean = np.mean(troughs)
        peak_to_trough_ratio = peak_mean / trough_mean if trough_mean > 0 else float("inf")

        confidence = min(peak_autocorr, 0.95) * (
            min(len(peaks), len(troughs)) / 5.0
        )
        confidence = min(confidence, 1.0)

        return SeasonalPeriod(
            pattern=SeasonalPattern(expected_hours),
            period_hours=detected_period_hours,
            confidence=confidence,
            peak_values=peaks,
            trough_values=troughs,
            peak_timestamps=peak_times,
            trough_timestamps=trough_times,
            peak_to_trough_ratio=peak_to_trough_ratio,
        )

    def _find_peaks_and_troughs(
        self,
        values: np.ndarray,
        timestamps: np.ndarray,
        period_hours: float,
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        try:
            from datetime import datetime
            if isinstance(timestamps[0], datetime):
                timestamps = np.array([t.timestamp() for t in timestamps])

            avg_interval = (timestamps[-1] - timestamps[0]) / (len(timestamps) - 1)
            min_distance = int(period_hours * 3600 / avg_interval * 0.5)

            peaks, _ = signal.find_peaks(values, distance=min_distance, prominence=np.std(values) * 0.5)
            troughs, _ = signal.find_peaks(-values, distance=min_distance, prominence=np.std(values) * 0.5)

            peak_values = values[peaks]
            trough_values = values[troughs]
            peak_times = timestamps[peaks]
            trough_times = timestamps[troughs]

            return peak_values, trough_values, peak_times, trough_times
        except Exception as e:
            logger.warning(f"Error finding peaks: {e}")
            return np.array([]), np.array([]), np.array([]), np.array([])

    def _calculate_seasonal_strength(self, detrended: np.ndarray, autocorr: np.ndarray) -> float:
        if len(autocorr) == 0:
            return 0.0

        significant_peaks = len([a for a in autocorr if abs(a) >= 0.3])
        max_autocorr = np.max(np.abs(autocorr)) if len(autocorr) > 0 else 0

        strength = (significant_peaks / len(autocorr)) * max_autocorr * 3
        return min(strength, 1.0)

    def _generate_recommendations(
        self,
        pattern: SeasonalPattern,
        confidence: float,
        seasonal_strength: float,
        total_duration_hours: float,
    ) -> List[str]:
        recommendations = []

        if pattern == SeasonalPattern.NONE:
            recommendations.append("未检测到显著的季节性模式")
            if total_duration_hours < 168:
                recommendations.append(f"建议收集至少7天数据以检测周度季节性（当前：{total_duration_hours:.1f}小时）")
            return recommendations

        pattern_names = {
            SeasonalPattern.HOURLY: "小时级",
            SeasonalPattern.DAILY: "日度",
            SeasonalPattern.WEEKLY: "周度",
        }

        pattern_name = pattern_names.get(pattern, pattern.value)
        recommendations.append(f"检测到{pattern_name}季节性模式，置信度：{confidence * 100:.0f}%")

        if seasonal_strength >= 0.6:
            recommendations.append("季节性强度较高，强烈建议使用周期性资源调度")
        elif seasonal_strength >= 0.3:
            recommendations.append("季节性强度中等，建议考虑使用周期性资源调度")

        if confidence >= 0.8:
            recommendations.append("季节性置信度高，可用于自动化资源调度")
        elif confidence >= 0.6:
            recommendations.append("季节性置信度中等，建议结合人工判断")

        return recommendations

    def generate_seasonal_recommendation(
        self,
        analysis: SeasonalityAnalysis,
        base_recommendation: float,
        buffer_percent: float = 10.0,
    ) -> SeasonalResourceRecommendation:
        if analysis.pattern == SeasonalPattern.NONE or not analysis.has_strong_seasonality:
            return SeasonalResourceRecommendation(
                base_recommendation=base_recommendation,
                peak_recommendation=base_recommendation,
                trough_recommendation=base_recommendation,
                seasonal_adjustment_factor=1.0,
                peak_schedule=[],
                trough_schedule=[],
                is_seasonal=False,
            )

        buffer = 1 + buffer_percent / 100

        peak_recommendation = base_recommendation * analysis.peak_resource_multiplier * buffer
        trough_recommendation = base_recommendation * analysis.trough_resource_multiplier * 0.9
        trough_recommendation = max(trough_recommendation, base_recommendation * 0.3)

        peak_schedule = self._generate_schedule(analysis, "peak")
        trough_schedule = self._generate_schedule(analysis, "trough")

        adjustment_factor = analysis.peak_resource_multiplier * buffer

        return SeasonalResourceRecommendation(
            base_recommendation=base_recommendation,
            peak_recommendation=peak_recommendation,
            trough_recommendation=trough_recommendation,
            seasonal_adjustment_factor=adjustment_factor,
            peak_schedule=peak_schedule,
            trough_schedule=trough_schedule,
            is_seasonal=True,
        )

    def _generate_schedule(self, analysis: SeasonalityAnalysis, schedule_type: str) -> List[str]:
        if not analysis.peak_periods:
            return []

        best_period = max(analysis.peak_periods, key=lambda p: p.confidence)
        timestamps = best_period.peak_timestamps if schedule_type == "peak" else best_period.trough_timestamps

        if len(timestamps) == 0:
            return []

        from datetime import datetime

        hours = []
        for ts in timestamps:
            dt = datetime.fromtimestamp(ts)
            hour = dt.hour
            weekday = dt.weekday()
            hours.append((weekday, hour))

        if len(hours) == 0:
            return []

        by_day = {}
        for weekday, hour in hours:
            if weekday not in by_day:
                by_day[weekday] = []
            by_day[weekday].append(hour)

        schedules = []
        day_names = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]

        if analysis.pattern == SeasonalPattern.DAILY:
            all_hours = [h for hours in by_day.values() for h in hours]
            if all_hours:
                avg_hour = int(np.mean(all_hours))
                hour_range = max(1, int(np.std(all_hours)))
                start_hour = max(0, avg_hour - hour_range)
                end_hour = min(23, avg_hour + hour_range)
                schedules.append(f"每日 {start_hour:02d}:00 - {end_hour:02d}:00")
        elif analysis.pattern == SeasonalPattern.WEEKLY:
            for weekday, hours_list in by_day.items():
                if hours_list:
                    avg_hour = int(np.mean(hours_list))
                    schedules.append(f"{day_names[weekday]} {avg_hour:02d}:00 左右")
        elif analysis.pattern == SeasonalPattern.HOURLY:
            schedules.append("每小时周期性波动")

        return schedules
