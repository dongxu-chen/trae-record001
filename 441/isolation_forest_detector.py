import pandas as pd
import numpy as np
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
from typing import Dict, List, Tuple
from config import Config

class IsolationForestDetector:
    def __init__(self, contamination: float = None, n_estimators: int = 100,
                 max_samples: str = 'auto', random_state: int = 42):
        self.contamination = contamination or Config.ISOLATION_FOREST_CONTAMINATION
        self.n_estimators = n_estimators
        self.max_samples = max_samples
        self.random_state = random_state
        self.scaler = StandardScaler()
        self.models = {}
        
    def _extract_features(self, df: pd.DataFrame, metric: str) -> np.ndarray:
        values = df[metric].values.reshape(-1, 1)
        
        features = [values.flatten()]
        
        if len(values) > 1:
            diff = np.diff(values.flatten())
            diff = np.insert(diff, 0, diff[0] if len(diff) > 0 else 0)
            features.append(diff)
            
            diff2 = np.diff(diff)
            diff2 = np.insert(diff2, 0, diff2[0] if len(diff2) > 0 else 0)
            features.append(diff2)
        
        rolling_mean = df[metric].rolling(window=12, min_periods=1).mean().values
        rolling_std = df[metric].rolling(window=12, min_periods=1).std().fillna(0).values
        features.append(rolling_mean)
        features.append(rolling_std)
        
        hour_of_day = df['timestamp'].dt.hour.values
        day_of_week = df['timestamp'].dt.dayofweek.values
        features.append(hour_of_day)
        features.append(day_of_week)
        
        return np.column_stack(features)
    
    def detect_anomalies(self, df: pd.DataFrame, metric: str) -> pd.DataFrame:
        features = self._extract_features(df, metric)
        
        scaled_features = self.scaler.fit_transform(features)
        
        model = IsolationForest(
            contamination=self.contamination,
            n_estimators=self.n_estimators,
            max_samples=self.max_samples,
            random_state=self.random_state
        )
        
        predictions = model.fit_predict(scaled_features)
        anomaly_scores = model.decision_function(scaled_features)
        
        self.models[metric] = model
        
        result_df = df[['timestamp', metric]].copy()
        result_df.columns = ['timestamp', 'actual']
        
        result_df['is_anomaly'] = predictions == -1
        
        normalized_scores = (anomaly_scores.max() - anomaly_scores) / (anomaly_scores.max() - anomaly_scores.min() + 1e-10)
        result_df['anomaly_score'] = np.where(result_df['is_anomaly'], normalized_scores, 0)
        
        result_df['anomaly_type'] = self._determine_anomaly_type(result_df, metric)
        result_df['metric'] = metric
        
        return result_df
    
    def _determine_anomaly_type(self, df: pd.DataFrame, metric: str) -> List[str]:
        types = []
        values = df['actual'].values
        mean_val = np.mean(values)
        std_val = np.std(values)
        
        for i, row in df.iterrows():
            if not row['is_anomaly']:
                types.append('normal')
            else:
                if row['actual'] > mean_val + std_val:
                    types.append('spike')
                elif row['actual'] < mean_val - std_val:
                    types.append('drop')
                else:
                    types.append('outlier')
        
        return types
    
    def detect_multi_metric(self, df: pd.DataFrame, metrics: List[str]) -> pd.DataFrame:
        all_features = []
        for metric in metrics:
            features = self._extract_features(df, metric)
            all_features.append(features)
        
        combined_features = np.concatenate(all_features, axis=1)
        scaled_features = self.scaler.fit_transform(combined_features)
        
        model = IsolationForest(
            contamination=self.contamination,
            n_estimators=self.n_estimators,
            max_samples=self.max_samples,
            random_state=self.random_state
        )
        
        predictions = model.fit_predict(scaled_features)
        anomaly_scores = model.decision_function(scaled_features)
        
        result_df = pd.DataFrame({
            'timestamp': df['timestamp'],
            'is_anomaly': predictions == -1
        })
        
        normalized_scores = (anomaly_scores.max() - anomaly_scores) / (anomaly_scores.max() - anomaly_scores.min() + 1e-10)
        result_df['anomaly_score'] = np.where(result_df['is_anomaly'], normalized_scores, 0)
        
        return result_df
    
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
                'detection_method': 'isolation_forest'
            })
        
        return anomaly_points
    
    def get_joint_anomaly_points(self, df: pd.DataFrame, metrics: List[str]) -> List[Dict]:
        result_df = self.detect_multi_metric(df, metrics)
        anomalies = result_df[result_df['is_anomaly']]
        
        anomaly_points = []
        for _, row in anomalies.iterrows():
            contributing_metrics = []
            for metric in metrics:
                single_df = self.detect_anomalies(df, metric)
                if single_df.loc[single_df['timestamp'] == row['timestamp'], 'is_anomaly'].iloc[0]:
                    contributing_metrics.append(metric)
            
            anomaly_points.append({
                'timestamp': row['timestamp'],
                'metrics': contributing_metrics,
                'anomaly_score': row['anomaly_score'],
                'detection_method': 'isolation_forest_joint'
            })
        
        return anomaly_points
