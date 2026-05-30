import pandas as pd
import numpy as np
from prophet import Prophet
from typing import Dict, Tuple, Optional
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

from config import config
from utils import align_dataframe_to_prophet, generate_future_timestamps, truncate_to_hours


class ResourcePredictor:
    def __init__(self, changepoint_prior_scale: float = None,
                 seasonality_prior_scale: float = None):
        self.changepoint_prior_scale = changepoint_prior_scale or config.changepoint_prior_scale
        self.seasonality_prior_scale = seasonality_prior_scale or config.seasonality_prior_scale
        self.models: Dict[str, Prophet] = {}
        self.fitted = False
        self._df: Optional[pd.DataFrame] = None
        self._sliding_patterns: Dict[str, Dict] = {}

    def _create_model(self) -> Prophet:
        model = Prophet(
            changepoint_prior_scale=self.changepoint_prior_scale,
            seasonality_prior_scale=self.seasonality_prior_scale,
            weekly_seasonality=config.weekly_seasonality,
            daily_seasonality=config.daily_seasonality,
            yearly_seasonality=config.yearly_seasonality,
            interval_width=config.anomaly_confidence
        )
        return model

    def fit(self, df: pd.DataFrame, resource_types: list = None) -> None:
        if resource_types is None:
            resource_types = list(config.resources.keys())

        self._df = df.copy()

        for resource_type in resource_types:
            prophet_df = align_dataframe_to_prophet(df, resource_type)
            model = self._create_model()
            model.fit(prophet_df)
            self.models[resource_type] = model

            self._sliding_patterns[resource_type] = self._compute_sliding_window_patterns(
                df, resource_type
            )

        self.fitted = True

    def predict(self, resource_type: str, periods: int = None,
                freq: str = '5min') -> pd.DataFrame:
        if not self.fitted:
            raise RuntimeError("模型尚未训练，请先调用 fit() 方法")

        if resource_type not in self.models:
            raise ValueError(f"资源类型 {resource_type} 未找到已训练的模型")

        model = self.models[resource_type]

        if periods is None:
            hours = config.prediction_hours
            periods = int((hours * 60) // config.data_frequency_minutes)

        future = model.make_future_dataframe(
            periods=periods, freq=freq, include_history=True)

        forecast = model.predict(future)

        forecast = forecast[['ds', 'yhat', 'yhat_lower', 'yhat_upper',
                       'trend', 'weekly', 'daily']]

        forecast['yhat'] = forecast['yhat'].clip(0, 100)
        forecast['yhat_lower'] = forecast['yhat_lower'].clip(0, 100)
        forecast['yhat_upper'] = forecast['yhat_upper'].clip(0, 100)

        return forecast

    def predict_next_hours(self, resource_type: str, hours: int = 24) -> pd.DataFrame:
        forecast = self.predict(resource_type)
        return truncate_to_hours(forecast, hours)

    def _compute_sliding_window_patterns(self, df: pd.DataFrame,
                                          resource_type: str) -> Dict:
        freq_min = config.data_frequency_minutes
        points_per_hour = 60 // freq_min
        window_size = config.sliding_window_hours * points_per_hour
        step_size = config.sliding_window_step_hours * points_per_hour

        values = df[resource_type].values
        timestamps = df['ds'].values
        n = len(values)

        windows = []
        start = 0
        while start + window_size <= n:
            end = start + window_size
            window_values = values[start:end]
            window_ts = timestamps[start:end]
            windows.append((window_ts, window_values))
            start += step_size

        if len(windows) == 0:
            windows.append((timestamps, values))

        window_results = []
        for w_idx, (w_ts, w_vals) in enumerate(windows):
            daily_pattern = self._extract_daily_pattern_sliding(w_ts, w_vals)
            weekly_pattern = self._extract_weekly_pattern_sliding(w_ts, w_vals)
            trend_info = self._extract_trend_sliding(w_vals)

            window_results.append({
                'window_index': w_idx,
                'window_start': pd.Timestamp(w_ts[0]),
                'window_end': pd.Timestamp(w_ts[-1]),
                'daily_pattern': daily_pattern,
                'weekly_pattern': weekly_pattern,
                'trend_info': trend_info
            })

        pattern_stability = self._compute_pattern_stability(window_results)

        latest = window_results[-1]

        return {
            'windows': window_results,
            'latest_daily': latest['daily_pattern'],
            'latest_weekly': latest['weekly_pattern'],
            'latest_trend': latest['trend_info'],
            'pattern_stability': pattern_stability,
            'n_windows': len(window_results)
        }

    def _extract_daily_pattern_sliding(self, timestamps, values) -> Dict:
        ts_series = pd.Series(pd.DatetimeIndex(timestamps))
        hour_of_day = ts_series.dt.hour.values

        hourly_avg = {}
        hourly_std = {}
        for h in range(24):
            mask = hour_of_day == h
            if mask.any():
                hourly_avg[h] = float(np.mean(values[mask]))
                hourly_std[h] = float(np.std(values[mask]))
            else:
                hourly_avg[h] = float(np.mean(values))
                hourly_std[h] = 0.0

        peak_hour = max(hourly_avg, key=hourly_avg.get)
        valley_hour = min(hourly_avg, key=hourly_avg.get)

        return {
            'hourly_avg': hourly_avg,
            'hourly_std': hourly_std,
            'peak_hour': peak_hour,
            'valley_hour': valley_hour,
            'amplitude': round(hourly_avg[peak_hour] - hourly_avg[valley_hour], 2)
        }

    def _extract_weekly_pattern_sliding(self, timestamps, values) -> Dict:
        ts_series = pd.Series(pd.DatetimeIndex(timestamps))
        day_of_week = ts_series.dt.dayofweek.values

        daily_avg = {}
        daily_std = {}
        day_names = {0: '周一', 1: '周二', 2: '周三', 3: '周四', 4: '周五', 5: '周六', 6: '周日'}
        for d in range(7):
            mask = day_of_week == d
            if mask.any():
                daily_avg[d] = float(np.mean(values[mask]))
                daily_std[d] = float(np.std(values[mask]))
            else:
                daily_avg[d] = float(np.mean(values))
                daily_std[d] = 0.0

        peak_day = max(daily_avg, key=daily_avg.get)
        valley_day = min(daily_avg, key=daily_avg.get)

        return {
            'daily_avg': daily_avg,
            'daily_std': daily_std,
            'peak_day': peak_day,
            'peak_day_name': day_names[peak_day],
            'valley_day': valley_day,
            'valley_day_name': day_names[valley_day],
            'amplitude': round(daily_avg[peak_day] - daily_avg[valley_day], 2)
        }

    def _extract_trend_sliding(self, values) -> Dict:
        n = len(values)
        x = np.arange(n, dtype=float)
        if n < 3:
            return {'slope': 0.0, 'direction': 'stable', 'r_squared': 0.0}

        slope, intercept = np.polyfit(x, values, 1)
        y_pred = slope * x + intercept
        ss_res = np.sum((values - y_pred) ** 2)
        ss_tot = np.sum((values - np.mean(values)) ** 2)
        r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0.0

        points_per_day = (60 // config.data_frequency_minutes) * 24
        slope_per_day = slope * points_per_day

        direction = 'increasing' if slope_per_day > 0.01 else (
            'decreasing' if slope_per_day < -0.01 else 'stable')

        return {
            'slope': round(float(slope_per_day), 4),
            'direction': direction,
            'r_squared': round(float(r_squared), 4)
        }

    def _compute_pattern_stability(self, window_results: list) -> Dict:
        if len(window_results) < 2:
            return {
                'daily_stability': 1.0,
                'weekly_stability': 1.0,
                'trend_stability': 1.0,
                'overall_stability': 'stable',
                'pattern_shifts': []
            }

        daily_peaks = [w['daily_pattern']['peak_hour'] for w in window_results]
        weekly_peaks = [w['weekly_pattern']['peak_day'] for w in window_results]
        trends = [w['trend_info']['direction'] for w in window_results]

        daily_changes = sum(1 for i in range(1, len(daily_peaks)) if daily_peaks[i] != daily_peaks[i-1])
        weekly_changes = sum(1 for i in range(1, len(weekly_peaks)) if weekly_peaks[i] != weekly_peaks[i-1])
        trend_changes = sum(1 for i in range(1, len(trends)) if trends[i] != trends[i-1])

        n_windows = len(window_results)
        daily_stability = 1.0 - (daily_changes / max(n_windows - 1, 1))
        weekly_stability = 1.0 - (weekly_changes / max(n_windows - 1, 1))
        trend_stability = 1.0 - (trend_changes / max(n_windows - 1, 1))

        pattern_shifts = []
        sensitivity = config.pattern_change_sensitivity
        for i in range(1, len(window_results)):
            prev_daily = window_results[i-1]['daily_pattern']['hourly_avg']
            curr_daily = window_results[i]['daily_pattern']['hourly_avg']
            shift = np.mean([abs(prev_daily[h] - curr_daily[h]) for h in range(24)])
            if shift > sensitivity * np.mean(list(curr_daily.values())):
                pattern_shifts.append({
                    'window_index': i,
                    'window_start': window_results[i]['window_start'],
                    'shift_magnitude': round(float(shift), 2),
                    'type': 'daily_pattern_shift'
                })

        overall = (daily_stability + weekly_stability + trend_stability) / 3
        if overall >= 0.9:
            overall_label = 'stable'
        elif overall >= 0.7:
            overall_label = 'moderate'
        else:
            overall_label = 'volatile'

        return {
            'daily_stability': round(float(daily_stability), 3),
            'weekly_stability': round(float(weekly_stability), 3),
            'trend_stability': round(float(trend_stability), 3),
            'overall_stability': overall_label,
            'overall_score': round(float(overall), 3),
            'pattern_shifts': pattern_shifts,
            'n_shifts_detected': len(pattern_shifts)
        }

    def get_seasonality_components(self, resource_type: str) -> Dict[str, pd.DataFrame]:
        if not self.fitted:
            raise RuntimeError("模型尚未训练")

        model = self.models[resource_type]
        future = model.make_future_dataframe(periods=1, freq='D')
        forecast = model.predict(future)

        components = {}

        daily = forecast[['ds', 'daily']].copy()
        daily['hour'] = daily['ds'].dt.hour
        daily_pattern = daily.groupby('hour')['daily'].mean().reset_index()
        components['daily'] = daily_pattern

        weekly = forecast[['ds', 'weekly']].copy()
        weekly['dayofweek'] = weekly['ds'].dt.dayofweek
        weekly_pattern = weekly.groupby('dayofweek')['weekly'].mean().reset_index()
        weekly_pattern['dayname'] = weekly_pattern['dayofweek'].map(
            {0: '周一', 1: '周二', 2: '周三', 3: '周四', 4: '周五', 5: '周六', 6: '周日'}
        )
        components['weekly'] = weekly_pattern

        components['trend'] = forecast[['ds', 'trend']].copy()

        return components

    def get_sliding_window_components(self, resource_type: str) -> Dict[str, pd.DataFrame]:
        if resource_type not in self._sliding_patterns:
            raise ValueError(f"资源类型 {resource_type} 未找到滑动窗口分析结果")

        sp = self._sliding_patterns[resource_type]
        latest_daily = sp['latest_daily']
        latest_weekly = sp['latest_weekly']

        daily_df = pd.DataFrame([
            {'hour': h, 'daily': latest_daily['hourly_avg'][h], 'std': latest_daily['hourly_std'][h]}
            for h in range(24)
        ])

        day_names = {0: '周一', 1: '周二', 2: '周三', 3: '周四', 4: '周五', 5: '周六', 6: '周日'}
        weekly_df = pd.DataFrame([
            {'dayofweek': d, 'weekly': latest_weekly['daily_avg'][d],
             'dayname': day_names[d], 'std': latest_weekly['daily_std'][d]}
            for d in range(7)
        ])

        trend_df = pd.DataFrame()
        if self._df is not None:
            trend_df = self._df[['ds']].copy()
            values = self._df[resource_type].values
            freq_min = config.data_frequency_minutes
            points_per_day = (60 // freq_min) * 24
            x = np.arange(len(values), dtype=float)
            if len(x) >= 3:
                slope, intercept = np.polyfit(x, values, 1)
                trend_df['trend'] = slope * x + intercept
            else:
                trend_df['trend'] = values

        return {
            'daily': daily_df,
            'weekly': weekly_df,
            'trend': trend_df
        }

    def detect_periodic_patterns(self, resource_type: str) -> Dict[str, any]:
        if resource_type not in self._sliding_patterns:
            raise ValueError(f"资源类型 {resource_type} 未找到滑动窗口分析结果")

        sp = self._sliding_patterns[resource_type]
        latest_daily = sp['latest_daily']
        latest_weekly = sp['latest_weekly']
        stability = sp['pattern_stability']

        return {
            'daily_peak_hour': latest_daily['peak_hour'],
            'daily_valley_hour': latest_daily['valley_hour'],
            'daily_amplitude': latest_daily['amplitude'],
            'weekly_peak_day': latest_weekly['peak_day_name'],
            'weekly_valley_day': latest_weekly['valley_day_name'],
            'weekly_amplitude': latest_weekly['amplitude'],
            'daily_stability': stability['daily_stability'],
            'weekly_stability': stability['weekly_stability'],
            'overall_stability': stability['overall_stability'],
            'overall_stability_score': stability['overall_score'],
            'pattern_shifts_detected': stability['n_shifts_detected'],
            'n_windows_analyzed': sp['n_windows']
        }

    def get_pattern_evolution(self, resource_type: str) -> pd.DataFrame:
        if resource_type not in self._sliding_patterns:
            raise ValueError(f"资源类型 {resource_type} 未找到滑动窗口分析结果")

        sp = self._sliding_patterns[resource_type]
        rows = []
        for w in sp['windows']:
            rows.append({
                'window_start': w['window_start'],
                'window_end': w['window_end'],
                'daily_peak_hour': w['daily_pattern']['peak_hour'],
                'daily_amplitude': w['daily_pattern']['amplitude'],
                'weekly_peak_day': w['weekly_pattern']['peak_day_name'],
                'weekly_amplitude': w['weekly_pattern']['amplitude'],
                'trend_direction': w['trend_info']['direction'],
                'trend_slope': w['trend_info']['slope']
            })
        return pd.DataFrame(rows)

    def get_decomposition(self, resource_type: str) -> pd.DataFrame:
        if not self.fitted:
            raise RuntimeError("模型尚未训练")

        model = self.models[resource_type]
        prophet_df = align_dataframe_to_prophet(self._df, resource_type)
        forecast = model.predict(prophet_df[['ds']])

        result = pd.DataFrame()
        result['ds'] = prophet_df['ds']
        result['observed'] = prophet_df['y'].values
        result['trend'] = forecast['trend'].values
        result['seasonal'] = forecast['daily'].values + forecast['weekly'].values
        result['residual'] = result['observed'] - result['trend'] - result['seasonal']

        return result

    def get_threshold_forecast(self, resource_type: str, hours: int = 24) -> pd.DataFrame:
        forecast = self.predict_next_hours(resource_type, hours)
        res_config = config.resources[resource_type]

        forecast['warning_threshold'] = res_config.warning_threshold
        forecast['critical_threshold'] = res_config.critical_threshold

        forecast['is_warning'] = forecast['yhat'] >= res_config.warning_threshold
        forecast['is_critical'] = forecast['yhat'] >= res_config.critical_threshold

        return forecast

    def get_warning_periods(self, resource_type: str, hours: int = 24) -> Dict[str, list]:
        forecast = self.get_threshold_forecast(resource_type, hours)

        warning_periods = forecast[forecast['is_warning'] & ~forecast['is_critical']]['ds'].tolist()
        critical_periods = forecast[forecast['is_critical']]['ds'].tolist()

        return {
            'warnings': warning_periods,
            'criticals': critical_periods
        }

    def get_forecast_summary(self, resource_type: str, hours: int = 24) -> Dict[str, any]:
        forecast = self.predict_next_hours(resource_type, hours)
        future_only = forecast[forecast['ds'] > datetime.now()]

        if len(future_only) == 0:
            future_only = forecast

        res_config = config.resources[resource_type]

        summary = {
            'resource_type': resource_type,
            'max_predicted': round(future_only['yhat'].max(), 2),
            'min_predicted': round(future_only['yhat'].min(), 2),
            'mean_predicted': round(future_only['yhat'].mean(), 2),
            'will_exceed_warning': (future_only['yhat'] >= res_config.warning_threshold).any(),
            'will_exceed_critical': (future_only['yhat'] >= res_config.critical_threshold).any(),
            'warning_count': int((future_only['yhat'] >= res_config.warning_threshold).sum()),
            'critical_count': int((future_only['yhat'] >= res_config.critical_threshold).sum()),
            'first_warning_time': None,
            'first_critical_time': None
        }

        warning_mask = future_only['yhat'] >= res_config.warning_threshold
        if warning_mask.any():
            summary['first_warning_time'] = future_only[warning_mask]['ds'].iloc[0]

        critical_mask = future_only['yhat'] >= res_config.critical_threshold
        if critical_mask.any():
            summary['first_critical_time'] = future_only[critical_mask]['ds'].iloc[0]

        return summary


def train_and_predict(df: pd.DataFrame, resource_type: str,
                      hours: int = 24) -> Tuple[ResourcePredictor, pd.DataFrame]:
    predictor = ResourcePredictor()
    predictor.fit(df, [resource_type])
    forecast = predictor.predict_next_hours(resource_type, hours)
    return predictor, forecast
