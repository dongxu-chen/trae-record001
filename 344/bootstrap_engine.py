"""
非参数Bootstrap气象模拟引擎
从历史数据重采样，保留分布特征、季节性和自相关结构
"""

import numpy as np
import pandas as pd
from typing import Tuple, Optional, Dict, List
from dataclasses import dataclass
from collections import defaultdict


@dataclass
class BootstrapConfig:
    block_size: int = 7
    n_bootstrap_samples: int = 10000
    preserve_seasonality: bool = True
    preserve_autocorrelation: bool = True
    seasonal_window: int = 15
    random_seed: Optional[int] = None


class BootstrapWeatherSimulator:
    """非参数Bootstrap天气模拟器"""

    def __init__(self, historical_data: pd.DataFrame, config: BootstrapConfig = None):
        self.historical_data = historical_data.copy()
        self.config = config or BootstrapConfig()
        self.rng = np.random.RandomState(self.config.random_seed)

        self._prepare_data()
        self._build_seasonal_blocks()

    def _prepare_data(self):
        self.historical_data['date'] = pd.to_datetime(self.historical_data['date'])
        self.historical_data['day_of_year'] = self.historical_data['date'].dt.dayofyear
        self.historical_data['month'] = self.historical_data['date'].dt.month
        self.historical_data['year'] = self.historical_data['date'].dt.year

        if 'HDD' not in self.historical_data.columns:
            self.historical_data['HDD'] = np.maximum(18.0 - self.historical_data['temperature'], 0)
        if 'CDD' not in self.historical_data.columns:
            self.historical_data['CDD'] = np.maximum(self.historical_data['temperature'] - 18.0, 0)
        if 'rainfall' not in self.historical_data.columns:
            self.historical_data['rainfall'] = 0

        self.years = sorted(self.historical_data['year'].unique())
        self.n_years = len(self.years)

    def _build_seasonal_blocks(self):
        self.seasonal_blocks = defaultdict(list)
        window = self.config.seasonal_window

        for year in self.years:
            year_data = self.historical_data[self.historical_data['year'] == year]
            year_data = year_data.sort_values('day_of_year')

            if len(year_data) < 365:
                continue

            for day in range(1, 366):
                day_data = year_data[year_data['day_of_year'] == day]
                if len(day_data) == 0:
                    continue

                start_idx = max(1, day - window)
                end_idx = min(366, day + window + 1)

                block_data = year_data[
                    (year_data['day_of_year'] >= start_idx) &
                    (year_data['day_of_year'] < end_idx)
                ]

                if len(block_data) > 0:
                    self.seasonal_blocks[day].append({
                        'year': year,
                        'data': block_data[['temperature', 'HDD', 'CDD', 'rainfall']].values,
                        'days': block_data['day_of_year'].values
                    })

    def bootstrap_sample_single_path(self,
                                     start_day: int = 1,
                                     n_days: int = 365,
                                     method: str = 'seasonal_block') -> np.ndarray:
        if method == 'seasonal_block':
            return self._seasonal_block_bootstrap(start_day, n_days)
        elif method == 'moving_block':
            return self._moving_block_bootstrap(start_day, n_days)
        elif method == 'circular_block':
            return self._circular_block_bootstrap(start_day, n_days)
        elif method == 'iid':
            return self._iid_bootstrap(start_day, n_days)
        else:
            raise ValueError(f"Unknown bootstrap method: {method}")

    def _seasonal_block_bootstrap(self, start_day: int, n_days: int) -> np.ndarray:
        sample = np.zeros((n_days, 4))

        for i in range(n_days):
            current_day = ((start_day + i - 1) % 365) + 1

            if current_day in self.seasonal_blocks and len(self.seasonal_blocks[current_day]) > 0:
                block_idx = self.rng.randint(0, len(self.seasonal_blocks[current_day]))
                block = self.seasonal_blocks[current_day][block_idx]
                block_data = block['data']
                block_days = block['days']

                match_idx = np.where(block_days == current_day)[0]
                if len(match_idx) > 0:
                    sample[i] = block_data[match_idx[0]]
                else:
                    closest_idx = np.argmin(np.abs(block_days - current_day))
                    sample[i] = block_data[closest_idx]
            else:
                all_blocks = []
                for blocks in self.seasonal_blocks.values():
                    all_blocks.extend(blocks)

                if all_blocks:
                    idx = self.rng.randint(0, len(all_blocks))
                    sample[i] = all_blocks[idx]['data'][0]
                else:
                    sample[i] = [15.0, 3.0, 0.0, 0.0]

        return sample

    def _moving_block_bootstrap(self, start_day: int, n_days: int) -> np.ndarray:
        sample = np.zeros((n_days, 4))
        block_size = self.config.block_size

        year_data = self.historical_data.sort_values(['year', 'day_of_year'])
        temp_data = year_data[['temperature', 'HDD', 'CDD', 'rainfall']].values

        n_total = len(temp_data)
        i = 0

        while i < n_days:
            if n_total > block_size:
                start_idx = self.rng.randint(0, n_total - block_size)
                block = temp_data[start_idx:start_idx + block_size]
            else:
                block = temp_data.copy()
                self.rng.shuffle(block)

            for j in range(min(block_size, n_days - i)):
                sample[i + j] = block[j]
            i += block_size

        return sample[:n_days]

    def _circular_block_bootstrap(self, start_day: int, n_days: int) -> np.ndarray:
        sample = np.zeros((n_days, 4))
        block_size = self.config.block_size

        year_data = self.historical_data.sort_values(['year', 'day_of_year'])
        temp_data = year_data[['temperature', 'HDD', 'CDD', 'rainfall']].values
        n_total = len(temp_data)

        if n_total == 0:
            return np.full((n_days, 4), [15.0, 3.0, 0.0, 0.0])

        circular_data = np.tile(temp_data, (3, 1))

        i = 0
        while i < n_days:
            start_idx = self.rng.randint(n_total, 2 * n_total)
            end_idx = min(start_idx + block_size, len(circular_data))
            block = circular_data[start_idx:end_idx]

            for j in range(min(len(block), n_days - i)):
                sample[i + j] = block[j]
            i += len(block)

        return sample[:n_days]

    def _iid_bootstrap(self, start_day: int, n_days: int) -> np.ndarray:
        year_data = self.historical_data.sort_values(['year', 'day_of_year'])
        temp_data = year_data[['temperature', 'HDD', 'CDD', 'rainfall']].values

        n_total = len(temp_data)
        indices = self.rng.randint(0, n_total, size=n_days)

        return temp_data[indices]

    def generate_bootstrap_samples(self,
                                   start_day: int = 1,
                                   n_days: int = 365,
                                   n_samples: int = None,
                                   method: str = 'seasonal_block') -> np.ndarray:
        if n_samples is None:
            n_samples = self.config.n_bootstrap_samples

        samples = np.zeros((n_samples, n_days, 4))

        for i in range(n_samples):
            samples[i] = self.bootstrap_sample_single_path(start_day, n_days, method)

        return samples

    def estimate_hdd_distribution(self,
                                  start_day: int = 1,
                                  n_days: int = 365,
                                  n_samples: int = None,
                                  method: str = 'seasonal_block') -> Dict:
        if n_samples is None:
            n_samples = self.config.n_bootstrap_samples

        samples = self.generate_bootstrap_samples(start_day, n_days, n_samples, method)

        hdd_sum = samples[:, :, 1].sum(axis=1)
        cdd_sum = samples[:, :, 2].sum(axis=1)
        rainfall_sum = samples[:, :, 3].sum(axis=1)

        return {
            'hdd': {
                'mean': np.mean(hdd_sum),
                'std': np.std(hdd_sum),
                'median': np.median(hdd_sum),
                'q5': np.percentile(hdd_sum, 5),
                'q25': np.percentile(hdd_sum, 25),
                'q75': np.percentile(hdd_sum, 75),
                'q95': np.percentile(hdd_sum, 95),
                'min': np.min(hdd_sum),
                'max': np.max(hdd_sum),
                'skewness': float(stats_skew(hdd_sum)),
                'kurtosis': float(stats_kurtosis(hdd_sum)),
                'all_values': hdd_sum
            },
            'cdd': {
                'mean': np.mean(cdd_sum),
                'std': np.std(cdd_sum),
                'median': np.median(cdd_sum),
                'all_values': cdd_sum
            },
            'rainfall': {
                'mean': np.mean(rainfall_sum),
                'std': np.std(rainfall_sum),
                'all_values': rainfall_sum
            }
        }

    def get_historical_extremes(self,
                                metric: str = 'HDD',
                                n_extremes: int = 10,
                                mode: str = 'max') -> pd.DataFrame:
        yearly_metrics = self.historical_data.groupby('year').agg({
            metric: 'sum',
            'temperature': 'mean',
            'rainfall': 'sum'
        }).reset_index()

        if mode == 'max':
            extremes = yearly_metrics.nlargest(n_extremes, metric)
        else:
            extremes = yearly_metrics.nsmallest(n_extremes, metric)

        return extremes

    def get_extreme_weather_events(self,
                                   metric: str = 'temperature',
                                   threshold: float = None,
                                   n_days: int = 7) -> List[Dict]:
        if threshold is None:
            if metric == 'temperature':
                threshold = self.historical_data[metric].quantile(0.95)
            elif metric == 'HDD':
                threshold = self.historical_data[metric].quantile(0.95)
            elif metric == 'rainfall':
                threshold = self.historical_data[metric].quantile(0.99)

        if metric == 'temperature':
            mask = self.historical_data[metric] <= threshold
        else:
            mask = self.historical_data[metric] >= threshold

        extreme_days = self.historical_data[mask].copy()
        extreme_days['event_id'] = (extreme_days['date'].diff().dt.days > 1).cumsum()

        events = []
        for event_id, group in extreme_days.groupby('event_id'):
            if len(group) >= 1:
                events.append({
                    'start_date': group['date'].iloc[0],
                    'end_date': group['date'].iloc[-1],
                    'duration_days': len(group),
                    'avg_temperature': group['temperature'].mean(),
                    'min_temperature': group['temperature'].min(),
                    'max_temperature': group['temperature'].max(),
                    'total_HDD': group['HDD'].sum(),
                    'total_rainfall': group['rainfall'].sum(),
                    'year': group['year'].iloc[0]
                })

        return sorted(events, key=lambda x: x['total_HDD'], reverse=True)[:20]

    def simulate_with_historical_analog(self,
                                        target_start_date: str,
                                        n_days: int = 365,
                                        n_analogs: int = 5) -> List[Dict]:
        target_date = pd.to_datetime(target_start_date)
        target_day = target_date.dayofyear

        analog_years = []
        for year in self.years:
            year_data = self.historical_data[self.historical_data['year'] == year]
            day_data = year_data[year_data['day_of_year'] == target_day]

            if len(day_data) > 0:
                analog_years.append({
                    'year': year,
                    'temperature': day_data['temperature'].values[0],
                    'data': year_data
                })

        target_temp = self.historical_data[
            self.historical_data['day_of_year'] == target_day
        ]['temperature'].mean()

        analog_years.sort(key=lambda x: abs(x['temperature'] - target_temp))
        selected = analog_years[:n_analogs]

        results = []
        for analog in selected:
            year_data = analog['data'].sort_values('day_of_year')
            year_data = year_data[year_data['day_of_year'] >= target_day].head(n_days)

            if len(year_data) > 0:
                results.append({
                    'year': analog['year'],
                    'start_temp': analog['temperature'],
                    'total_HDD': year_data['HDD'].sum(),
                    'total_CDD': year_data['CDD'].sum(),
                    'total_rainfall': year_data['rainfall'].sum(),
                    'avg_temp': year_data['temperature'].mean()
                })

        return results


def stats_skew(x: np.ndarray) -> float:
    n = len(x)
    if n < 3:
        return 0.0
    mean = np.mean(x)
    std = np.std(x, ddof=1)
    if std == 0:
        return 0.0
    return (n / ((n - 1) * (n - 2))) * np.sum(((x - mean) / std) ** 3)


def stats_kurtosis(x: np.ndarray) -> float:
    n = len(x)
    if n < 4:
        return 0.0
    mean = np.mean(x)
    std = np.std(x, ddof=1)
    if std == 0:
        return 0.0
    m4 = np.sum(((x - mean) / std) ** 4) / n
    m2 = np.sum(((x - mean) / std) ** 2) / n
    return (m4 / (m2 ** 2)) - 3.0
