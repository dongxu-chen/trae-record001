import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
from datetime import datetime

from config import config
from utils import align_dataframe_to_prophet


class AnomalyDetector:
    def __init__(self, iqr_multiplier: float = None, confidence: float = None):
        self.iqr_multiplier = iqr_multiplier or config.anomaly_iqr_multiplier
        self.confidence = confidence or config.anomaly_confidence
        self.scaler = StandardScaler()
        self.isolation_forest = IsolationForest(
            contamination=0.02,
            random_state=42,
            n_estimators=100
        )
        self._decomposition: Optional[pd.DataFrame] = None

    def decompose(self, predictor, resource_type: str) -> pd.DataFrame:
        self._decomposition = predictor.get_decomposition(resource_type)
        return self._decomposition

    def detect_residual_iqr(self, residuals: pd.Series) -> pd.Series:
        q1 = residuals.quantile(0.25)
        q3 = residuals.quantile(0.75)
        iqr = q3 - q1
        lower_bound = q1 - self.iqr_multiplier * iqr
        upper_bound = q3 + self.iqr_multiplier * iqr
        return (residuals < lower_bound) | (residuals > upper_bound)

    def detect_residual_zscore(self, residuals: pd.Series, threshold: float = 3.0) -> pd.Series:
        mean = residuals.mean()
        std = residuals.std()
        if std == 0:
            return pd.Series([False] * len(residuals), index=residuals.index)
        z_scores = np.abs((residuals - mean) / std)
        return z_scores > threshold

    def detect_residual_rolling(self, residuals: pd.Series,
                                 window_size: int = 288,
                                 threshold_std: float = 3.0) -> pd.Series:
        rolling_mean = residuals.rolling(window=window_size, min_periods=12).mean()
        rolling_std = residuals.rolling(window=window_size, min_periods=12).std()
        upper_bound = rolling_mean + threshold_std * rolling_std
        lower_bound = rolling_mean - threshold_std * rolling_std
        return (residuals < lower_bound) | (residuals > upper_bound)

    def detect_residual_iforest(self, residuals: pd.Series) -> pd.Series:
        features = residuals.values.reshape(-1, 1)
        features = np.nan_to_num(features, nan=0.0)
        features_scaled = self.scaler.fit_transform(features)
        predictions = self.isolation_forest.fit_predict(features_scaled)
        return pd.Series(predictions == -1, index=residuals.index)

    def detect_prophet_interval_anomaly(self, df: pd.DataFrame, resource_type: str,
                                         forecast: pd.DataFrame) -> pd.Series:
        prophet_df = align_dataframe_to_prophet(df, resource_type)
        merged = pd.merge(prophet_df, forecast[['ds', 'yhat_lower', 'yhat_upper']], on='ds', how='left')
        anomalies = (merged['y'] < merged['yhat_lower']) | (merged['y'] > merged['yhat_upper'])
        anomalies.index = prophet_df.index
        return anomalies.fillna(False)

    def detect_all_anomalies(self, df: pd.DataFrame, resource_type: str,
                              forecast: Optional[pd.DataFrame] = None,
                              predictor=None) -> pd.DataFrame:
        result = pd.DataFrame(index=df.index)
        result['ds'] = df['ds']
        result[resource_type] = df[resource_type]

        if predictor is not None:
            decomp = self.decompose(predictor, resource_type)
            residuals = decomp['residual']
            result['trend'] = decomp['trend'].values
            result['seasonal'] = decomp['seasonal'].values
            result['residual'] = residuals.values

            result['residual_iqr_anomaly'] = self.detect_residual_iqr(residuals).values
            result['residual_zscore_anomaly'] = self.detect_residual_zscore(residuals).values
            result['residual_rolling_anomaly'] = self.detect_residual_rolling(residuals).values
            result['residual_iforest_anomaly'] = self.detect_residual_iforest(residuals).values

            residual_anomaly_cols = [c for c in result.columns if c.startswith('residual_') and c.endswith('_anomaly')]
            result['residual_anomaly_score'] = result[residual_anomaly_cols].sum(axis=1)
            result['is_residual_anomaly'] = result['residual_anomaly_score'] >= 2

            observed = result[resource_type]
            expected = result['trend'] + result['seasonal']
            result['deviation_percent'] = ((observed - expected) / expected * 100).round(2)
        else:
            result['residual_iqr_anomaly'] = self.detect_residual_iqr(df[resource_type] - df[resource_type].rolling(12, min_periods=3).mean()).values
            result['residual_zscore_anomaly'] = self.detect_residual_zscore(df[resource_type]).values
            result['residual_rolling_anomaly'] = False
            result['residual_iforest_anomaly'] = False
            result['residual_anomaly_score'] = result[['residual_iqr_anomaly', 'residual_zscore_anomaly']].sum(axis=1)
            result['is_residual_anomaly'] = result['residual_anomaly_score'] >= 1

        if forecast is not None:
            result['prophet_interval_anomaly'] = self.detect_prophet_interval_anomaly(
                df, resource_type, forecast).values

        anomaly_columns = [col for col in result.columns
                           if col.endswith('_anomaly')]
        result['anomaly_score'] = result[anomaly_columns].sum(axis=1)

        residual_cols = [c for c in anomaly_columns if c.startswith('residual_')]
        if len(residual_cols) > 0:
            result['is_anomaly'] = result[residual_cols].sum(axis=1) >= 2
        else:
            result['is_anomaly'] = result['anomaly_score'] >= 2

        if 'prophet_interval_anomaly' in result.columns:
            result['is_anomaly'] = result['is_anomaly'] | result['prophet_interval_anomaly']

        return result

    def get_anomaly_summary(self, anomaly_df: pd.DataFrame, resource_type: str) -> Dict[str, any]:
        total_points = len(anomaly_df)
        anomaly_points = anomaly_df['is_anomaly'].sum()
        anomaly_rate = (anomaly_points / total_points) * 100 if total_points > 0 else 0

        residual_anomaly_count = int(anomaly_df.get('is_residual_anomaly', pd.Series([False])).sum())

        anomaly_details = []
        if anomaly_points > 0:
            anomalies = anomaly_df[anomaly_df['is_anomaly']]
            for _, row in anomalies.tail(10).iterrows():
                detail = {
                    'timestamp': row['ds'],
                    'value': round(row[resource_type], 2),
                    'score': int(row['anomaly_score']),
                    'methods': [col.replace('_anomaly', '') for col in anomaly_df.columns
                                if col.endswith('_anomaly') and row[col]]
                }
                if 'deviation_percent' in anomaly_df.columns:
                    detail['deviation_percent'] = float(row.get('deviation_percent', 0))
                if 'residual' in anomaly_df.columns:
                    detail['residual'] = round(float(row.get('residual', 0)), 2)
                anomaly_details.append(detail)

        res_config = config.resources[resource_type]
        high_value_anomalies = anomaly_df[
            (anomaly_df['is_anomaly']) &
            (anomaly_df[resource_type] >= res_config.warning_threshold)
        ]

        anomaly_types = {}
        for col in anomaly_df.columns:
            if col.endswith('_anomaly'):
                key = col.replace('_anomaly', '')
                anomaly_types[key] = int(anomaly_df[col].sum())

        summary = {
            'resource_type': resource_type,
            'total_points': total_points,
            'anomaly_count': int(anomaly_points),
            'anomaly_rate_percent': round(anomaly_rate, 2),
            'residual_anomaly_count': residual_anomaly_count,
            'high_value_anomaly_count': int(len(high_value_anomalies)),
            'recent_anomalies': anomaly_details,
            'anomaly_types': anomaly_types
        }

        if 'residual' in anomaly_df.columns:
            residuals = anomaly_df['residual']
            summary['residual_stats'] = {
                'mean': round(float(residuals.mean()), 4),
                'std': round(float(residuals.std()), 4),
                'max': round(float(residuals.max()), 2),
                'min': round(float(residuals.min()), 2)
            }

        return summary

    def detect_prediction_anomalies(self, forecast: pd.DataFrame,
                                     resource_type: str) -> pd.DataFrame:
        result = forecast[['ds', 'yhat', 'yhat_lower', 'yhat_upper']].copy()

        res_config = config.resources[resource_type]

        result['exceeds_warning'] = result['yhat'] >= res_config.warning_threshold
        result['exceeds_critical'] = result['yhat'] >= res_config.critical_threshold

        result['rate_of_change'] = result['yhat'].diff()
        mean_change = result['rate_of_change'].abs().mean()
        std_change = result['rate_of_change'].abs().std()
        result['sudden_change'] = result['rate_of_change'].abs() > (mean_change + 3 * std_change)

        result['is_prediction_anomaly'] = result['sudden_change'] | result['exceeds_critical']

        return result

    def analyze_anomaly_severity(self, anomaly_df: pd.DataFrame,
                                  resource_type: str) -> pd.DataFrame:
        result = anomaly_df.copy()

        res_config = config.resources[resource_type]
        value = anomaly_df[resource_type]

        conditions = [
            (value >= res_config.critical_threshold) & (anomaly_df['is_anomaly']),
            (value >= res_config.warning_threshold) & (anomaly_df['is_anomaly']),
            (anomaly_df['is_anomaly']) & (value < res_config.warning_threshold)
        ]

        severities = ['critical', 'warning', 'low']
        colors = [config.color_palette['critical'],
                  config.color_palette['warning'],
                  config.color_palette['normal']]

        result['severity'] = np.select(conditions, severities, default='normal')
        result['severity_color'] = np.select(conditions, colors, default=config.color_palette['normal'])

        return result


def run_full_anomaly_detection(df: pd.DataFrame, resource_type: str,
                                forecast: Optional[pd.DataFrame] = None,
                                predictor=None) -> Tuple[AnomalyDetector, pd.DataFrame, Dict]:
    detector = AnomalyDetector()
    anomaly_df = detector.detect_all_anomalies(df, resource_type, forecast, predictor)
    anomaly_df = detector.analyze_anomaly_severity(anomaly_df, resource_type)
    summary = detector.get_anomaly_summary(anomaly_df, resource_type)
    return detector, anomaly_df, summary
