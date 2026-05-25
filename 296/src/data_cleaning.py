import pandas as pd
import numpy as np
from scipy import stats
from statsmodels.stats.stattools import medcouple


class DataCleaner:
    def __init__(self):
        self.fill_method = None
        self.anomaly_bounds = {}
        self.scaler = None

    def fill_missing_values(self, df, method='interpolate', **kwargs):
        self.fill_method = method
        df_clean = df.copy()

        if method == 'interpolate':
            df_clean = df_clean.interpolate(
                method=kwargs.get('interpolate_method', 'time'),
                limit_direction='both'
            )
        elif method == 'ffill':
            df_clean = df_clean.ffill().bfill()
        elif method == 'mean':
            for col in df_clean.select_dtypes(include=[np.number]).columns:
                df_clean[col] = df_clean[col].fillna(df_clean[col].mean())
        elif method == 'median':
            for col in df_clean.select_dtypes(include=[np.number]).columns:
                df_clean[col] = df_clean[col].fillna(df_clean[col].median())

        return df_clean

    def _calculate_adaptive_iqr_bounds(self, data):
        q1 = np.percentile(data, 25)
        q3 = np.percentile(data, 75)
        iqr = q3 - q1

        skewness = stats.skew(data)
        mc = medcouple(data)

        if abs(mc) < 0.2:
            k_lower = 1.5
            k_upper = 1.5
        elif mc > 0:
            k_lower = 1.5 * np.exp(-3 * mc)
            k_upper = 1.5 * np.exp(4 * mc)
        else:
            k_lower = 1.5 * np.exp(-4 * mc)
            k_upper = 1.5 * np.exp(3 * mc)

        k_lower = max(1.0, min(k_lower, 3.0))
        k_upper = max(1.0, min(k_upper, 3.0))

        lower_bound = q1 - k_lower * iqr
        upper_bound = q3 + k_upper * iqr

        return lower_bound, upper_bound, k_lower, k_upper, skewness, mc

    def detect_anomalies(self, df, method='adaptive_iqr', contamination=0.05):
        df_clean = df.copy()
        numeric_cols = df_clean.select_dtypes(include=[np.number]).columns

        if len(numeric_cols) == 0:
            return df_clean, pd.Series([False] * len(df_clean))

        self.anomaly_bounds = {}
        is_anomaly = pd.Series([False] * len(df_clean), index=df_clean.index)

        if method == 'adaptive_iqr':
            for col in numeric_cols:
                data = df_clean[col].dropna().values
                if len(data) < 10:
                    continue

                lower_bound, upper_bound, k_lower, k_upper, skewness, mc = \
                    self._calculate_adaptive_iqr_bounds(data)

                self.anomaly_bounds[col] = {
                    'lower': lower_bound,
                    'upper': upper_bound,
                    'k_lower': k_lower,
                    'k_upper': k_upper,
                    'skewness': skewness,
                    'medcouple': mc
                }

                col_anomalies = (df_clean[col] < lower_bound) | (df_clean[col] > upper_bound)
                is_anomaly = is_anomaly | col_anomalies

        elif method == 'iqr':
            for col in numeric_cols:
                q1 = df_clean[col].quantile(0.25)
                q3 = df_clean[col].quantile(0.75)
                iqr = q3 - q1
                lower_bound = q1 - 1.5 * iqr
                upper_bound = q3 + 1.5 * iqr

                self.anomaly_bounds[col] = {
                    'lower': lower_bound,
                    'upper': upper_bound
                }

                col_anomalies = (df_clean[col] < lower_bound) | (df_clean[col] > upper_bound)
                is_anomaly = is_anomaly | col_anomalies

        elif method == 'zscore':
            for col in numeric_cols:
                z_scores = np.abs((df_clean[col] - df_clean[col].mean()) / df_clean[col].std())
                is_anomaly = is_anomaly | (z_scores > 3)

        return df_clean, is_anomaly

    def handle_anomalies(self, df, is_anomaly, strategy='interpolate'):
        df_clean = df.copy()

        if strategy == 'interpolate':
            for col in df_clean.select_dtypes(include=[np.number]).columns:
                df_clean.loc[is_anomaly, col] = np.nan
                df_clean[col] = df_clean[col].interpolate(method='time', limit_direction='both')
        elif strategy == 'remove':
            df_clean = df_clean[~is_anomaly]
        elif strategy == 'cap':
            for col in df_clean.select_dtypes(include=[np.number]).columns:
                q1 = df_clean[col].quantile(0.01)
                q3 = df_clean[col].quantile(0.99)
                df_clean.loc[is_anomaly & (df_clean[col] < q1), col] = q1
                df_clean.loc[is_anomaly & (df_clean[col] > q3), col] = q3

        return df_clean

    def clean_data(self, df, fill_method='interpolate', anomaly_method='adaptive_iqr',
                   anomaly_strategy='interpolate', contamination=0.05):
        report = {}

        report['original_rows'] = len(df)
        report['original_missing'] = df.isnull().sum().sum()

        df_clean = self.fill_missing_values(df, method=fill_method)

        report['after_fill_missing'] = df_clean.isnull().sum().sum()

        df_clean, is_anomaly = self.detect_anomalies(
            df_clean, method=anomaly_method, contamination=contamination
        )

        report['anomalies_detected'] = is_anomaly.sum()

        df_clean = self.handle_anomalies(df_clean, is_anomaly, strategy=anomaly_strategy)

        report['final_rows'] = len(df_clean)
        report['final_missing'] = df_clean.isnull().sum().sum()

        return df_clean, report
