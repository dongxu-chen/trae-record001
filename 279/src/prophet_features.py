import pandas as pd
import numpy as np
from prophet import Prophet
import logging
logging.getLogger('prophet').setLevel(logging.WARNING)


class ProphetFeatureExtractor:
    def __init__(self):
        self.model = None
        self.forecast = None

    def fit(self, df):
        prophet_df = df[['ds', 'y']].copy()
        self.model = Prophet(
            yearly_seasonality=True,
            weekly_seasonality=True,
            daily_seasonality=False,
            interval_width=0.95
        )
        self.model.fit(prophet_df)
        return self

    def predict(self, df):
        prophet_df = df[['ds', 'y']].copy()
        self.forecast = self.model.predict(prophet_df)
        return self.forecast

    def extract_features(self, df):
        if self.forecast is None:
            self.fit(df)
            self.forecast = self.predict(df)

        features = pd.DataFrame()

        features['trend'] = self.forecast['trend'].values

        features['yearly'] = self.forecast['yearly'].values if 'yearly' in self.forecast.columns else 0
        features['weekly'] = self.forecast['weekly'].values if 'weekly' in self.forecast.columns else 0

        features['residual'] = df['y'].values - self.forecast['yhat'].values

        features['yhat_upper'] = self.forecast['yhat_upper'].values
        features['yhat_lower'] = self.forecast['yhat_lower'].values

        features['upper_violation'] = (df['y'].values > self.forecast['yhat_upper'].values).astype(int)
        features['lower_violation'] = (df['y'].values < self.forecast['yhat_lower'].values).astype(int)

        features['trend_change'] = features['trend'].diff().fillna(0)

        return features

    def get_anomaly_scores_from_prophet(self, df):
        if self.forecast is None:
            self.fit(df)
            self.forecast = self.predict(df)

        residual = df['y'].values - self.forecast['yhat'].values
        residual_std = np.std(residual)

        z_scores = np.abs(residual) / (residual_std + 1e-8)

        upper_violation = (df['y'].values - self.forecast['yhat_upper'].values) / (df['y'].values.std() + 1e-8)
        lower_violation = (self.forecast['yhat_lower'].values - df['y'].values) / (df['y'].values.std() + 1e-8)

        upper_violation = np.maximum(upper_violation, 0)
        lower_violation = np.maximum(lower_violation, 0)

        anomaly_scores = z_scores + upper_violation * 2 + lower_violation * 2

        return anomaly_scores

    def get_forecast_df(self):
        return self.forecast
