import pandas as pd
import numpy as np
from prophet import Prophet
from typing import Dict, List, Tuple
import warnings
warnings.filterwarnings('ignore')

class ProphetAnomalyDetector:
    def __init__(self, interval_width: float = 0.95, yearly_seasonality: bool = False,
                 weekly_seasonality: bool = True, daily_seasonality: bool = True):
        self.interval_width = interval_width
        self.yearly_seasonality = yearly_seasonality
        self.weekly_seasonality = weekly_seasonality
        self.daily_seasonality = daily_seasonality
        self.models = {}
        
    def _prepare_data(self, df: pd.DataFrame, metric: str) -> pd.DataFrame:
        prophet_df = df[['timestamp', metric]].copy()
        prophet_df.columns = ['ds', 'y']
        return prophet_df
    
    def fit_predict(self, df: pd.DataFrame, metric: str) -> Tuple[pd.DataFrame, pd.DataFrame]:
        prophet_df = self._prepare_data(df, metric)
        
        model = Prophet(
            interval_width=self.interval_width,
            yearly_seasonality=self.yearly_seasonality,
            weekly_seasonality=self.weekly_seasonality,
            daily_seasonality=self.daily_seasonality
        )
        
        model.fit(prophet_df)
        forecast = model.predict(prophet_df)
        
        self.models[metric] = model
        
        result_df = pd.DataFrame({
            'timestamp': df['timestamp'],
            'actual': df[metric],
            'predicted': forecast['yhat'],
            'upper_bound': forecast['yhat_upper'],
            'lower_bound': forecast['yhat_lower']
        })
        
        return result_df, forecast
    
    def detect_anomalies(self, df: pd.DataFrame, metric: str) -> pd.DataFrame:
        result_df, _ = self.fit_predict(df, metric)
        
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
                predicted = row['predicted']
                upper = row['upper_bound']
                lower = row['lower_bound']
                
                if actual > upper:
                    deviation = (actual - upper) / (upper - predicted + 1e-10)
                else:
                    deviation = (lower - actual) / (predicted - lower + 1e-10)
                
                score = min(1.0, deviation / 5.0)
                scores[i] = score
        
        return scores
    
    def detect_all_metrics(self, df: pd.DataFrame, metrics: List[str]) -> Dict[str, pd.DataFrame]:
        results = {}
        for metric in metrics:
            results[metric] = self.detect_anomalies(df, metric)
        return results
    
    def get_anomaly_points(self, df: pd.DataFrame, metric: str) -> List[Dict]:
        anomaly_df = self.detect_anomalies(df, metric)
        anomalies = anomaly_df[anomaly_df['is_anomaly']]
        
        anomaly_points = []
        for _, row in anomalies.iterrows():
            anomaly_points.append({
                'timestamp': row['timestamp'],
                'metric': metric,
                'anomaly_type': row['anomaly_type'],
                'anomaly_score': row['anomaly_score'],
                'actual_value': row['actual'],
                'predicted_value': row['predicted'],
                'detection_method': 'prophet'
            })
        
        return anomaly_points
