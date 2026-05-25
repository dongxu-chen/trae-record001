"""
季节性和趋势分解模块
使用STL分解、傅里叶分析和多尺度趋势提取
更准确地建模气象时间序列的结构性变化
"""

import numpy as np
import pandas as pd
from typing import Tuple, Dict, Optional, List
from dataclasses import dataclass
from collections import defaultdict

try:
    from statsmodels.tsa.seasonal import STL
    HAS_STL = True
except ImportError:
    HAS_STL = False

try:
    from scipy import signal as scipy_signal
    from scipy.fft import fft, ifft, fftfreq
    HAS_SCIPY = True
except ImportError:
    HAS_SCIPY = False


@dataclass
class DecompositionConfig:
    seasonal_period: int = 365
    trend_window: int = 31
    seasonal_window: int = 7
    low_pass_window: int = 31
    robust: bool = True
    n_fourier_components: int = 10
    use_stl: bool = True


@dataclass
class DecompositionResult:
    original: np.ndarray
    trend: np.ndarray
    seasonal: np.ndarray
    residual: np.ndarray
    trend_slope: float
    seasonal_amplitude: float
    seasonal_phase: float
    residual_std: float
    ar1_coefficient: float
    fourier_coefficients: np.ndarray
    component_variance_ratio: Dict


class WeatherDecomposer:
    """气象数据分解器 - 提取趋势、季节性和残差成分"""

    def __init__(self, config: DecompositionConfig = None):
        self.config = config or DecompositionConfig()

    def decompose(self,
                  temperature: pd.Series,
                  dates: pd.Series = None) -> DecompositionResult:
        values = temperature.values.astype(float)
        n = len(values)

        if dates is not None:
            dates = pd.to_datetime(dates)
        else:
            dates = pd.date_range(start='2020-01-01', periods=n, freq='D')

        trend = self._extract_trend(values, dates)
        detrended = values - trend

        seasonal = self._extract_seasonality(detrended, dates)
        residual = values - trend - seasonal

        trend_slope = self._estimate_trend_slope(trend)
        seasonal_amp = np.max(seasonal) - np.min(seasonal)
        seasonal_phase = self._estimate_seasonal_phase(seasonal, dates)
        residual_std = np.std(residual)
        ar1_coeff = np.corrcoef(residual[:-1], residual[1:])[0, 1] if n > 1 else 0

        fourier_coeffs = self._extract_fourier_components(seasonal)

        var_ratio = self._compute_variance_ratio(values, trend, seasonal, residual)

        return DecompositionResult(
            original=values,
            trend=trend,
            seasonal=seasonal,
            residual=residual,
            trend_slope=trend_slope,
            seasonal_amplitude=seasonal_amp,
            seasonal_phase=seasonal_phase,
            residual_std=residual_std,
            ar1_coefficient=ar1_coeff,
            fourier_coefficients=fourier_coeffs,
            component_variance_ratio=var_ratio
        )

    def _extract_trend(self, values: np.ndarray, dates: pd.Series) -> np.ndarray:
        n = len(values)

        if self.config.use_stl and HAS_STL and n > self.config.seasonal_period:
            try:
                stl = STL(
                    values,
                    period=self.config.seasonal_period,
                    trend=self.config.trend_window,
                    seasonal=self.config.seasonal_window,
                    low_pass=self.config.low_pass_window,
                    robust=self.config.robust
                )
                result = stl.fit()
                return result.trend
            except Exception:
                pass

        return self._moving_average_trend(values)

    def _moving_average_trend(self, values: np.ndarray) -> np.ndarray:
        window = self.config.trend_window
        if window % 2 == 0:
            window += 1

        trend = np.zeros(len(values))
        half = window // 2

        for i in range(len(values)):
            start = max(0, i - half)
            end = min(len(values), i + half + 1)
            weights = np.ones(end - start)

            if i < half:
                weights[:half - i] = np.linspace(0, 1, half - i)
            if i > len(values) - half - 1:
                weights[-(i - (len(values) - half - 1)):] = np.linspace(1, 0, i - (len(values) - half - 1))

            trend[i] = np.average(values[start:end], weights=weights)

        return trend

    def _extract_seasonality(self,
                             detrended: np.ndarray,
                             dates: pd.Series) -> np.ndarray:
        n = len(detrended)
        doy = dates.dt.dayofyear.values

        seasonal = np.zeros(n)

        for day in range(1, 367):
            mask = doy == day
            if np.any(mask):
                seasonal[mask] = np.mean(detrended[mask])

        if self.config.n_fourier_components > 0 and HAS_SCIPY:
            fourier_seasonal = self._fourier_smoothing(seasonal)
            if len(fourier_seasonal) == n:
                seasonal = fourier_seasonal

        return seasonal

    def _fourier_smoothing(self, seasonal: np.ndarray) -> np.ndarray:
        n = len(seasonal)
        fft_vals = fft(seasonal)
        freqs = fftfreq(n)

        n_components = min(self.config.n_fourier_components, n // 2)

        mask = np.zeros(n, dtype=bool)
        mask[0] = True
        for k in range(1, n_components + 1):
            mask[k] = True
            mask[-k] = True

        fft_filtered = fft_vals * mask
        smoothed = np.real(ifft(fft_filtered))

        return smoothed

    def _extract_fourier_components(self, seasonal: np.ndarray) -> np.ndarray:
        n = len(seasonal)
        if not HAS_SCIPY:
            return np.array([])

        fft_vals = fft(seasonal)
        n_components = min(self.config.n_fourier_components, n // 2)

        coefficients = []
        for k in range(1, n_components + 1):
            amplitude = 2 * np.abs(fft_vals[k]) / n
            phase = np.angle(fft_vals[k])
            coefficients.append({
                'harmonic': k,
                'amplitude': amplitude,
                'phase': phase,
                'period_days': n / k if k > 0 else float('inf')
            })

        return np.array(coefficients)

    def _estimate_trend_slope(self, trend: np.ndarray) -> float:
        n = len(trend)
        if n < 2:
            return 0.0

        x = np.arange(n)
        A = np.vstack([x, np.ones(n)]).T
        slope, _ = np.linalg.lstsq(A, trend, rcond=None)[0]

        return slope

    def _estimate_seasonal_phase(self,
                                  seasonal: np.ndarray,
                                  dates: pd.Series) -> float:
        peak_idx = np.argmax(seasonal)
        peak_date = dates.iloc[peak_idx]

        return peak_date.dayofyear

    def _compute_variance_ratio(self,
                                 original: np.ndarray,
                                 trend: np.ndarray,
                                 seasonal: np.ndarray,
                                 residual: np.ndarray) -> Dict:
        total_var = np.var(original)

        if total_var == 0:
            return {'trend': 0, 'seasonal': 0, 'residual': 0}

        return {
            'trend': np.var(trend) / total_var,
            'seasonal': np.var(seasonal) / total_var,
            'residual': np.var(residual) / total_var
        }

    def forecast_decomposition(self,
                                result: DecompositionResult,
                                n_forecast_days: int,
                                start_date: str) -> pd.DataFrame:
        start = pd.to_datetime(start_date)
        future_dates = pd.date_range(start=start, periods=n_forecast_days, freq='D')

        trend_forecast = self._forecast_trend(result, n_forecast_days)
        seasonal_forecast = self._forecast_seasonality(result, future_dates)
        residual_forecast = self._simulate_residuals(result, n_forecast_days)

        forecast = trend_forecast + seasonal_forecast + residual_forecast

        return pd.DataFrame({
            'date': future_dates,
            'temperature': forecast,
            'trend': trend_forecast,
            'seasonal': seasonal_forecast,
            'residual': residual_forecast
        })

    def _forecast_trend(self,
                         result: DecompositionResult,
                         n_days: int) -> np.ndarray:
        last_trend = result.trend[-1]
        trend_values = last_trend + result.trend_slope * np.arange(1, n_days + 1)

        return trend_values

    def _forecast_seasonality(self,
                               result: DecompositionResult,
                               future_dates: pd.Series) -> np.ndarray:
        doy = future_dates.dt.dayofyear.values
        n_history = len(result.seasonal)

        seasonal_forecast = np.zeros(len(future_dates))

        for i, day in enumerate(doy):
            idx = (day - 1) % n_history
            seasonal_forecast[i] = result.seasonal[idx]

        return seasonal_forecast

    def _simulate_residuals(self,
                             result: DecompositionResult,
                             n_days: int) -> np.ndarray:
        rng = np.random.RandomState(42)

        residuals = np.zeros(n_days)
        residuals[0] = rng.normal(0, result.residual_std)

        for i in range(1, n_days):
            residuals[i] = (
                result.ar1_coefficient * residuals[i-1] +
                rng.normal(0, result.residual_std * np.sqrt(1 - result.ar1_coefficient**2))
            )

        return residuals

    def analyze_multiple_years(self,
                                historical_data: pd.DataFrame,
                                value_col: str = 'temperature') -> List[DecompositionResult]:
        years = sorted(historical_data['year'].unique())
        results = []

        for year in years:
            year_data = historical_data[historical_data['year'] == year].sort_values('date')

            if len(year_data) > 30:
                result = self.decompose(
                    year_data[value_col],
                    year_data['date']
                )
                results.append(result)

        return results

    def compute_climate_indices(self,
                                 result: DecompositionResult,
                                 dates: pd.Series) -> Dict:
        values = result.original
        trend = result.trend

        anomalies = values - trend

        warm_days = np.sum(anomalies > result.residual_std)
        cold_days = np.sum(anomalies < -result.residual_std)

        heat_wave_days = self._count_heat_waves(anomalies, result.residual_std)
        cold_wave_days = self._count_cold_waves(anomalies, result.residual_std)

        return {
            'total_days': len(values),
            'warm_anomaly_days': warm_days,
            'cold_anomaly_days': cold_days,
            'heat_wave_days': heat_wave_days,
            'cold_wave_days': cold_wave_days,
            'trend_acceleration': self._estimate_trend_acceleration(trend),
            'max_daily_trend_deviation': np.max(np.abs(values - trend)),
            'avg_daily_trend_deviation': np.mean(np.abs(values - trend))
        }

    def _count_heat_waves(self, anomalies: np.ndarray, threshold: float) -> int:
        heat_wave = 0
        max_heat_wave = 0
        current = 0

        for a in anomalies:
            if a > threshold:
                current += 1
                if current > max_heat_wave:
                    max_heat_wave = current
            else:
                if current >= 3:
                    heat_wave += current
                current = 0

        if current >= 3:
            heat_wave += current

        return heat_wave

    def _count_cold_waves(self, anomalies: np.ndarray, threshold: float) -> int:
        cold_wave = 0
        max_cold_wave = 0
        current = 0

        for a in anomalies:
            if a < -threshold:
                current += 1
                if current > max_cold_wave:
                    max_cold_wave = current
            else:
                if current >= 3:
                    cold_wave += current
                current = 0

        if current >= 3:
            cold_wave += current

        return cold_wave

    def _estimate_trend_acceleration(self, trend: np.ndarray) -> float:
        if len(trend) < 3:
            return 0.0

        second_diff = np.diff(trend, n=2)
        return np.mean(second_diff)

    def simulate_from_decomposition(self,
                                     result: DecompositionResult,
                                     n_days: int,
                                     n_scenarios: int = 100,
                                     start_date: str = None) -> np.ndarray:
        if start_date:
            start = pd.to_datetime(start_date)
        else:
            start = pd.Timestamp.now()

        future_dates = pd.date_range(start=start, periods=n_days, freq='D')
        doy = future_dates.dt.dayofyear.values
        n_history = len(result.seasonal)

        rng = np.random.RandomState(12345)
        scenarios = np.zeros((n_scenarios, n_days))

        for s in range(n_scenarios):
            trend_forecast = result.trend[-1] + result.trend_slope * np.arange(1, n_days + 1)

            seasonal_forecast = np.zeros(n_days)
            for i, day in enumerate(doy):
                idx = (day - 1) % n_history
                seasonal_forecast[i] = result.seasonal[idx]

            residuals = np.zeros(n_days)
            residuals[0] = rng.normal(0, result.residual_std)

            for i in range(1, n_days):
                residuals[i] = (
                    result.ar1_coefficient * residuals[i-1] +
                    rng.normal(0, result.residual_std * np.sqrt(1 - result.ar1_coefficient**2))
                )

            scenarios[s] = trend_forecast + seasonal_forecast + residuals

        return scenarios
