import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Tuple, List, Dict
from config import config


def generate_time_range(start_date: datetime, end_date: datetime, freq_minutes: int = 5) -> pd.DatetimeIndex:
    return pd.date_range(start=start_date, end=end_date, freq=f'{freq_minutes}min')


def format_timestamp(dt: datetime) -> str:
    return dt.strftime('%Y-%m-%d %H:%M:%S')


def get_resource_status(value: float, resource_type: str) -> Tuple[str, str]:
    res_config = config.resources[resource_type]
    if value >= res_config.critical_threshold:
        return 'critical', config.color_palette['critical']
    elif value >= res_config.warning_threshold:
        return 'warning', config.color_palette['warning']
    else:
        return 'normal', config.color_palette['normal']


def calculate_statistics(series: pd.Series) -> Dict[str, float]:
    return {
        'mean': round(series.mean(), 2),
        'median': round(series.median(), 2),
        'max': round(series.max(), 2),
        'min': round(series.min(), 2),
        'std': round(series.std(), 2),
        'p95': round(series.quantile(0.95), 2),
        'p99': round(series.quantile(0.99), 2)
    }


def detect_peak_hours(df: pd.DataFrame, value_col: str, threshold_percentile: float = 0.8) -> List[int]:
    hourly_avg = df.groupby(df['ds'].dt.hour)[value_col].mean()
    threshold = hourly_avg.quantile(threshold_percentile)
    peak_hours = hourly_avg[hourly_avg >= threshold].index.tolist()
    return sorted(peak_hours)


def generate_future_timestamps(hours: int = 24, freq_minutes: int = 5) -> pd.DataFrame:
    now = datetime.now()
    future_end = now + timedelta(hours=hours)
    future_dates = pd.date_range(start=now, end=future_end, freq=f'{freq_minutes}min')
    return pd.DataFrame({'ds': future_dates})


def align_dataframe_to_prophet(df: pd.DataFrame, value_col: str) -> pd.DataFrame:
    prophet_df = df[['ds', value_col]].copy()
    prophet_df.columns = ['ds', 'y']
    prophet_df['ds'] = pd.to_datetime(prophet_df['ds'])
    return prophet_df


def format_warning_message(resource_type: str, value: float, threshold: float, timestamp: datetime) -> str:
    res_config = config.resources[resource_type]
    time_str = format_timestamp(timestamp)
    return f"⚠️ [{time_str}] {res_config.name}达到 {value}{res_config.unit}，超过阈值 {threshold}{res_config.unit}"


def format_critical_message(resource_type: str, value: float, threshold: float, timestamp: datetime) -> str:
    res_config = config.resources[resource_type]
    time_str = format_timestamp(timestamp)
    return f"🔴 [{time_str}] {res_config.name}达到 {value}{res_config.unit}，超过危险阈值 {threshold}{res_config.unit}"


def truncate_to_hours(future_df: pd.DataFrame, hours: int) -> pd.DataFrame:
    now = datetime.now()
    cutoff = now + timedelta(hours=hours)
    return future_df[future_df['ds'] <= cutoff].copy()
