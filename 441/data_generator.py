import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional

class TimeSeriesDataGenerator:
    def __init__(self, start_date: Optional[str] = None, days: int = 30, freq: str = '5min'):
        self.start_date = start_date or (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d %H:%M:%S')
        self.days = days
        self.freq = freq
        
    def generate_daily_pattern(self, n_points: int, base_value: float, amplitude: float) -> np.ndarray:
        hours_per_day = 24
        points_per_hour = 60 // int(self.freq.replace('min', '')) if 'min' in self.freq else 1
        points_per_day = hours_per_day * points_per_hour
        t = np.arange(n_points)
        daily_pattern = amplitude * np.sin(2 * np.pi * t / points_per_day)
        return daily_pattern
    
    def generate_weekly_pattern(self, n_points: int, amplitude: float) -> np.ndarray:
        hours_per_day = 24
        points_per_hour = 60 // int(self.freq.replace('min', '')) if 'min' in self.freq else 1
        points_per_day = hours_per_day * points_per_hour
        points_per_week = 7 * points_per_day
        t = np.arange(n_points)
        weekly_pattern = amplitude * np.sin(2 * np.pi * t / points_per_week)
        return weekly_pattern
    
    def generate_qps(self, timestamps: pd.DatetimeIndex) -> pd.Series:
        n_points = len(timestamps)
        base_qps = 1000
        daily_amplitude = 500
        weekly_amplitude = 200
        
        daily_pattern = self.generate_daily_pattern(n_points, base_qps, daily_amplitude)
        weekly_pattern = self.generate_weekly_pattern(n_points, weekly_amplitude)
        noise = np.random.normal(0, 50, n_points)
        
        qps = base_qps + daily_pattern + weekly_pattern + noise
        qps = np.maximum(qps, 100)
        
        return pd.Series(qps, index=timestamps, name='qps')
    
    def generate_latency(self, timestamps: pd.DatetimeIndex) -> pd.Series:
        n_points = len(timestamps)
        base_latency = 50
        daily_amplitude = 20
        weekly_amplitude = 10
        
        daily_pattern = self.generate_daily_pattern(n_points, base_latency, daily_amplitude)
        weekly_pattern = self.generate_weekly_pattern(n_points, weekly_amplitude)
        noise = np.random.normal(0, 5, n_points)
        
        latency = base_latency + daily_pattern + weekly_pattern + noise
        latency = np.maximum(latency, 10)
        
        return pd.Series(latency, index=timestamps, name='latency')
    
    def generate_error_rate(self, timestamps: pd.DatetimeIndex) -> pd.Series:
        n_points = len(timestamps)
        base_error = 0.02
        noise = np.random.normal(0, 0.005, n_points)
        
        error_rate = base_error + noise
        error_rate = np.clip(error_rate, 0, 1)
        
        return pd.Series(error_rate, index=timestamps, name='error_rate')
    
    def inject_anomalies(self, data: pd.Series, anomaly_type: str, 
                         start_idx: int, duration: int, magnitude: float) -> pd.Series:
        data = data.copy()
        
        if anomaly_type == 'spike':
            data.iloc[start_idx:start_idx + duration] *= magnitude
        elif anomaly_type == 'drop':
            data.iloc[start_idx:start_idx + duration] /= magnitude
        elif anomaly_type == 'level_shift':
            data.iloc[start_idx:] *= magnitude
            
        return data
    
    def generate_metrics_data(self, inject_anomalies: bool = True) -> pd.DataFrame:
        start_dt = datetime.strptime(self.start_date, '%Y-%m-%d %H:%M:%S')
        end_dt = start_dt + timedelta(days=self.days)
        timestamps = pd.date_range(start=start_dt, end=end_dt, freq=self.freq)
        
        qps = self.generate_qps(timestamps)
        latency = self.generate_latency(timestamps)
        error_rate = self.generate_error_rate(timestamps)
        
        df = pd.DataFrame({
            'timestamp': timestamps,
            'qps': qps.values,
            'latency': latency.values,
            'error_rate': error_rate.values
        })
        
        if inject_anomalies:
            anomaly_points = self._inject_random_anomalies(df)
            return df, anomaly_points
        
        return df, []
    
    def _inject_random_anomalies(self, df: pd.DataFrame) -> List[Dict]:
        anomaly_points = []
        n_points = len(df)
        
        anomalies_config = [
            {'metric': 'qps', 'type': 'spike', 'magnitude': 2.5, 'duration': 6},
            {'metric': 'qps', 'type': 'drop', 'magnitude': 3, 'duration': 4},
            {'metric': 'latency', 'type': 'spike', 'magnitude': 3, 'duration': 3},
            {'metric': 'error_rate', 'type': 'spike', 'magnitude': 8, 'duration': 2},
        ]
        
        for config in anomalies_config:
            start_idx = np.random.randint(n_points // 4, 3 * n_points // 4)
            metric = config['metric']
            
            if config['type'] == 'spike':
                df.loc[start_idx:start_idx + config['duration'], metric] *= config['magnitude']
            elif config['type'] == 'drop':
                df.loc[start_idx:start_idx + config['duration'], metric] /= config['magnitude']
            
            for i in range(config['duration']):
                anomaly_points.append({
                    'timestamp': df['timestamp'].iloc[start_idx + i],
                    'metric': metric,
                    'anomaly_type': config['type'],
                    'is_injected': True
                })
        
        return anomaly_points
