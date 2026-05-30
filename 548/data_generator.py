import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, Optional
from config import config
from utils import generate_time_range


class ServerDataGenerator:
    def __init__(self, seed: Optional[int] = None):
        self.seed = seed if seed is not None else np.random.randint(0, 10000)
        np.random.seed(self.seed)

    def _add_daily_pattern(self, timestamps: pd.DatetimeIndex, base_value: float, amplitude: float) -> np.ndarray:
        hour_of_day = timestamps.hour
        daily_pattern = amplitude * np.sin(2 * np.pi * (hour_of_day - 6) / 24)
        return base_value + daily_pattern

    def _add_weekly_pattern(self, timestamps: pd.DatetimeIndex, amplitude: float) -> np.ndarray:
        day_of_week = timestamps.dayofweek
        is_weekend = (day_of_week >= 5).astype(float)
        weekly_pattern = -amplitude * is_weekend
        return weekly_pattern

    def _add_trend(self, timestamps: pd.DatetimeIndex, start_value: float, trend_rate: float) -> np.ndarray:
        days_passed = (timestamps - timestamps[0]).total_seconds() / (24 * 3600)
        trend = trend_rate * days_passed
        return start_value + trend

    def _add_noise(self, size: int, noise_level: float) -> np.ndarray:
        return np.random.normal(0, noise_level, size)

    def _add_anomalies(self, data: np.ndarray, anomaly_rate: float = 0.02,
                       anomaly_magnitude: float = 15.0) -> np.ndarray:
        n_anomalies = int(len(data) * anomaly_rate)
        if n_anomalies == 0:
            return data

        anomaly_indices = np.random.choice(len(data), n_anomalies, replace=False)
        anomaly_directions = np.random.choice([-1, 1], n_anomalies)
        anomaly_values = np.random.uniform(anomaly_magnitude * 0.5, anomaly_magnitude, n_anomalies)

        data_with_anomalies = np.array(data.copy(), dtype=np.float64)
        for idx, direction, magnitude in zip(anomaly_indices.astype(int), anomaly_directions, anomaly_values):
            data_with_anomalies[idx] = data_with_anomalies[idx] + direction * magnitude

        return data_with_anomalies

    def _generate_resource_data(self, timestamps: pd.DatetimeIndex,
                                resource_type: str) -> np.ndarray:
        if resource_type == 'cpu':
            base = 45.0
            daily_amp = 25.0
            weekly_amp = 10.0
            trend_rate = 0.15
            noise = 4.0
        elif resource_type == 'memory':
            base = 55.0
            daily_amp = 15.0
            weekly_amp = 5.0
            trend_rate = 0.08
            noise = 2.5
        elif resource_type == 'disk':
            base = 60.0
            daily_amp = 5.0
            weekly_amp = 2.0
            trend_rate = 0.02
            noise = 1.0
        else:
            raise ValueError(f"Unknown resource type: {resource_type}")

        trend = self._add_trend(timestamps, base, trend_rate)
        daily = self._add_daily_pattern(timestamps, 0, daily_amp)
        weekly = self._add_weekly_pattern(timestamps, weekly_amp)
        noise = self._add_noise(len(timestamps), noise)

        data = trend + daily + weekly + noise
        data = self._add_anomalies(data)

        data = np.clip(data, 0, 100)
        return data

    def generate_historical_data(self, days: int = None,
                                 freq_minutes: int = None) -> pd.DataFrame:
        if days is None:
            days = config.historical_days
        if freq_minutes is None:
            freq_minutes = config.data_frequency_minutes

        end_date = datetime.now().replace(second=0, microsecond=0)
        start_date = end_date - timedelta(days=days)

        timestamps = generate_time_range(start_date, end_date, freq_minutes)

        df = pd.DataFrame({'ds': timestamps})

        for resource_type in config.resources.keys():
            df[resource_type] = self._generate_resource_data(timestamps, resource_type)

        return df

    def generate_live_data_point(self, historical_df: pd.DataFrame) -> Dict[str, float]:
        last_timestamp = historical_df['ds'].iloc[-1]
        new_timestamp = last_timestamp + timedelta(minutes=config.data_frequency_minutes)

        timestamps = pd.DatetimeIndex([new_timestamp])
        result = {'ds': new_timestamp}

        for resource_type in config.resources.keys():
            value = self._generate_resource_data(timestamps, resource_type)[0]
            result[resource_type] = value

        return result


def generate_sample_data(days: int = 30) -> pd.DataFrame:
    generator = ServerDataGenerator(seed=42)
    return generator.generate_historical_data(days=days)


if __name__ == '__main__':
    df = generate_sample_data(days=7)
    print(f"生成的数据形状: {df.shape}")
    print(f"\n前5行数据:")
    print(df.head())
    print(f"\n统计信息:")
    print(df.describe())
