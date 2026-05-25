import pandas as pd
import numpy as np
from sklearn.preprocessing import StandardScaler, MinMaxScaler
from statsmodels.tsa.stattools import acf
from scipy.signal import find_peaks
import warnings
warnings.filterwarnings('ignore')


class TimeSeriesFeatureEngineer:
    def __init__(self):
        self.scaler = None
        self.feature_columns = []
        self.detected_seasonality = None

    def create_time_features(self, df, datetime_col=None):
        df_feat = df.copy()

        if datetime_col is None:
            datetime_col = df_feat.index.name if df_feat.index.name else 'index'

        if not isinstance(df_feat.index, pd.DatetimeIndex):
            if datetime_col in df_feat.columns:
                df_feat[datetime_col] = pd.to_datetime(df_feat[datetime_col])
                df_feat = df_feat.set_index(datetime_col)

        df_feat['year'] = df_feat.index.year
        df_feat['quarter'] = df_feat.index.quarter
        df_feat['month'] = df_feat.index.month
        df_feat['week'] = df_feat.index.isocalendar().week.astype(int)
        df_feat['day'] = df_feat.index.day
        df_feat['dayofweek'] = df_feat.index.dayofweek
        df_feat['dayofyear'] = df_feat.index.dayofyear
        df_feat['hour'] = df_feat.index.hour
        df_feat['is_weekend'] = (df_feat.index.dayofweek >= 5).astype(int)
        df_feat['is_month_start'] = df_feat.index.is_month_start.astype(int)
        df_feat['is_month_end'] = df_feat.index.is_month_end.astype(int)

        df_feat['month_sin'] = np.sin(2 * np.pi * df_feat['month'] / 12)
        df_feat['month_cos'] = np.cos(2 * np.pi * df_feat['month'] / 12)
        df_feat['day_sin'] = np.sin(2 * np.pi * df_feat['dayofweek'] / 7)
        df_feat['day_cos'] = np.cos(2 * np.pi * df_feat['dayofweek'] / 7)
        df_feat['hour_sin'] = np.sin(2 * np.pi * df_feat['hour'] / 24)
        df_feat['hour_cos'] = np.cos(2 * np.pi * df_feat['hour'] / 24)

        return df_feat

    def detect_seasonality(self, data, max_lag=365):
        data = data.dropna().values
        if len(data) < 50:
            return None, [1, 2, 3, 7], [7, 14]

        try:
            acf_values = acf(data, nlags=min(max_lag, len(data) // 2), fft=True)

            peaks, properties = find_peaks(
                acf_values,
                height=0.2,
                distance=5,
                prominence=0.05
            )

            if len(peaks) > 0:
                peak_heights = properties['peak_heights']
                top_peaks = peaks[np.argsort(peak_heights)[-3:]]
                top_peaks = sorted(top_peaks)

                seasonal_period = top_peaks[-1] if top_peaks else 7

                lags = set([1, 2, 3])
                for peak in top_peaks:
                    if peak > 0:
                        lags.add(peak)
                        if peak > 1:
                            lags.add(peak - 1)
                        lags.add(peak + 1)

                lags = sorted([l for l in lags if l > 0 and l < len(data) // 4])[:10]

                window_sizes = set()
                for peak in top_peaks:
                    if peak > 3:
                        window_sizes.add(min(peak, 30))
                window_sizes = sorted([w for w in window_sizes if w >= 3])[:5]
                if not window_sizes:
                    window_sizes = [7, 14]

                self.detected_seasonality = {
                    'seasonal_period': seasonal_period,
                    'acf_peaks': top_peaks.tolist(),
                    'peak_heights': peak_heights[np.argsort(peak_heights)[-3:]].tolist()
                }

                return seasonal_period, lags, window_sizes

        except Exception as e:
            pass

        return 7, [1, 2, 3, 7, 14], [7, 14, 28]

    def create_lag_features(self, df, target_col, lags=None, window_sizes=None, auto_detect=True):
        df_feat = df.copy()

        if auto_detect and lags is None:
            _, lags, window_sizes = self.detect_seasonality(df_feat[target_col])
        else:
            if lags is None:
                lags = [1, 2, 3, 7, 14, 28]
            if window_sizes is None:
                window_sizes = [7, 14, 28]

        for lag in lags:
            df_feat[f'lag_{lag}'] = df_feat[target_col].shift(lag)

        for window in window_sizes:
            df_feat[f'rolling_mean_{window}'] = df_feat[target_col].rolling(
                window=window, min_periods=1
            ).mean()
            df_feat[f'rolling_std_{window}'] = df_feat[target_col].rolling(
                window=window, min_periods=1
            ).std()
            df_feat[f'rolling_min_{window}'] = df_feat[target_col].rolling(
                window=window, min_periods=1
            ).min()
            df_feat[f'rolling_max_{window}'] = df_feat[target_col].rolling(
                window=window, min_periods=1
            ).max()

        for window in window_sizes:
            df_feat[f'ewm_mean_{window}'] = df_feat[target_col].ewm(
                span=window, adjust=False
            ).mean()

        df_feat['diff_1'] = df_feat[target_col].diff()
        df_feat['pct_change_1'] = df_feat[target_col].pct_change()

        return df_feat

    def scale_features(self, df, method='standard', fit=True):
        df_scaled = df.copy()
        numeric_cols = df_scaled.select_dtypes(include=[np.number]).columns

        if fit:
            if method == 'standard':
                self.scaler = StandardScaler()
            elif method == 'minmax':
                self.scaler = MinMaxScaler()

            df_scaled[numeric_cols] = self.scaler.fit_transform(df_scaled[numeric_cols])
        else:
            df_scaled[numeric_cols] = self.scaler.transform(df_scaled[numeric_cols])

        return df_scaled

    def inverse_transform(self, df, target_col):
        df_inv = df.copy()
        if self.scaler:
            target_idx = list(df.select_dtypes(include=[np.number]).columns).index(target_col)
            df_inv[target_col] = self.scaler.inverse_transform(
                df_inv[df.select_dtypes(include=[np.number]).columns]
            )[:, target_idx]
        return df_inv

    def engineer_features(self, df, target_col, datetime_col=None,
                          create_time=True, create_lag=True,
                          lags=None, window_sizes=None,
                          auto_detect_seasonality=True,
                          scale=False, scale_method='standard'):
        df_feat = df.copy()
        report = {}

        report['original_columns'] = len(df_feat.columns)
        report['original_rows'] = len(df_feat)

        if create_time:
            df_feat = self.create_time_features(df_feat, datetime_col)

        if create_lag:
            df_feat = self.create_lag_features(
                df_feat, target_col, lags, window_sizes,
                auto_detect=auto_detect_seasonality
            )

        if self.detected_seasonality:
            report['detected_seasonality'] = self.detected_seasonality
            report['auto_lags'] = lags if lags else 'auto-detected'
            report['auto_windows'] = window_sizes if window_sizes else 'auto-detected'

        if scale:
            df_feat = self.scale_features(df_feat, method=scale_method, fit=True)

        df_feat = df_feat.dropna()

        report['final_columns'] = len(df_feat.columns)
        report['final_rows'] = len(df_feat)
        report['new_features'] = report['final_columns'] - report['original_columns']

        self.feature_columns = [col for col in df_feat.columns if col != target_col]

        return df_feat, report

    def prepare_forecast_data(self, df, target_col, forecast_horizon):
        df_feat = df.copy()

        X = df_feat.drop(columns=[target_col])
        y = df_feat[target_col]

        train_size = len(df_feat) - forecast_horizon
        X_train, X_test = X.iloc[:train_size], X.iloc[train_size:]
        y_train, y_test = y.iloc[:train_size], y.iloc[train_size:]

        return X_train, X_test, y_train, y_test
