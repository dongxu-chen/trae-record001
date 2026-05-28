import pandas as pd
import numpy as np
from typing import Dict, List
from config import Config

class ThreeSigmaDetector:
    def __init__(self, threshold: float = None, window_size: int = None):
        self.threshold = threshold or Config.THREE_SIGMA_THRESHOLD
        self.window_size = window_size
        self.stats = {}
        
    def _calculate_stats(self, data: np.ndarray) -> Dict[str, float]:
        mean = np.mean(data)
        std = np.std(data)
        return {
            'mean': mean,
            'std': std,
            'upper': mean + self.threshold * std,
            'lower': mean - self.threshold * std
        }
    
    def detect_anomalies(self, df: pd.DataFrame, metric: str, 
                         use_rolling: bool = False) -> pd.DataFrame:
        values = df[metric].values
        result_df = df[['timestamp', metric]].copy()
        result_df.columns = ['timestamp', 'actual']
        
        if use_rolling and self.window_size:
            rolling_mean = df[metric].rolling(window=self.window_size).mean()
            rolling_std = df[metric].rolling(window=self.window_size).std()
            
            result_df['mean'] = rolling_mean
            result_df['std'] = rolling_std
            result_df['upper_bound'] = rolling_mean + self.threshold * rolling_std
            result_df['lower_bound'] = rolling_mean - self.threshold * rolling_std
        else:
            stats = self._calculate_stats(values)
            self.stats[metric] = stats
            
            result_df['mean'] = stats['mean']
            result_df['std'] = stats['std']
            result_df['upper_bound'] = stats['upper']
            result_df['lower_bound'] = stats['lower']
        
        result_df['is_anomaly'] = (
            (result_df['actual'] > result_df['upper_bound']) |
            (result_df['actual'] < result_df['lower_bound'])
        )
        
        result_df['anomaly_type'] = 'normal'
        result_df.loc[result_df['actual'] > result_df['upper_bound'], 'anomaly_type'] = 'spike'
        result_df.loc[result_df['actual'] < result_df['lower_bound'], 'anomaly_type'] = 'drop'
        
        result_df['anomaly_score'] = self._calculate_anomaly_score(result_df)
        result_df['metric'] = metric
        
        return result_df
    
    def _calculate_anomaly_score(self, df: pd.DataFrame) -> np.ndarray:
        scores = np.zeros(len(df))
        
        for i, row in df.iterrows():
            if row['is_anomaly']:
                actual = row['actual']
                mean = row['mean']
                std = row['std'] if row['std'] > 0 else 1e-10
                
                z_score = abs(actual - mean) / std
                score = min(1.0, (z_score - self.threshold) / (2 * self.threshold))
                scores[i] = max(0, score)
        
        return scores
    
    def detect_all_metrics(self, df: pd.DataFrame, metrics: List[str],
                           use_rolling: bool = False) -> Dict[str, pd.DataFrame]:
        results = {}
        for metric in metrics:
            results[metric] = self.detect_anomalies(df, metric, use_rolling)
        return results
    
    def get_anomaly_points(self, df: pd.DataFrame, metric: str,
                           use_rolling: bool = False) -> List[Dict]:
        anomaly_df = self.detect_anomalies(df, metric, use_rolling)
        anomalies = anomaly_df[anomaly_df['is_anomaly']]
        
        anomaly_points = []
        for _, row in anomalies.iterrows():
            anomaly_points.append({
                'timestamp': row['timestamp'],
                'metric': metric,
                'anomaly_type': row['anomaly_type'],
                'anomaly_score': row['anomaly_score'],
                'actual_value': row['actual'],
                'mean_value': row['mean'],
                'upper_bound': row['upper_bound'],
                'lower_bound': row['lower_bound'],
                'detection_method': 'three_sigma'
            })
        
        return anomaly_points
    
    def detect_periodicity_break(self, df: pd.DataFrame, metric: str,
                                  period: int = 288) -> List[Dict]:
        values = df[metric].values
        n = len(values)
        
        if n < 2 * period:
            return []
        
        breaks = []
        for i in range(period, n - period, period // 2):
            window1 = values[i - period:i]
            window2 = values[i:i + period]
            
            mean1 = np.mean(window1)
            mean2 = np.mean(window2)
            std1 = np.std(window1)
            std2 = np.std(window2)
            
            mean_change = abs(mean2 - mean1) / (mean1 + 1e-10)
            std_change = abs(std2 - std1) / (std1 + 1e-10)
            
            if mean_change > 0.3 or std_change > 0.5:
                breaks.append({
                    'timestamp': df['timestamp'].iloc[i],
                    'metric': metric,
                    'anomaly_type': 'periodicity_break',
                    'anomaly_score': min(1.0, (mean_change + std_change) / 2),
                    'mean_change': mean_change,
                    'std_change': std_change,
                    'detection_method': 'three_sigma_periodicity'
                })
        
        return breaks
