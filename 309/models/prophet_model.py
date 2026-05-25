import pandas as pd
import numpy as np
from typing import Dict, Optional, List, Tuple
import logging
from datetime import timedelta
import warnings
warnings.filterwarnings('ignore')

try:
    from prophet import Prophet
    from prophet.plot import plot_plotly, plot_components_plotly
except ImportError:
    Prophet = None

from config import Config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ProphetModel:
    def __init__(self, config: Optional[Dict] = None):
        self.config = config or Config().get('models.prophet', {})
        self.model = None
        self.holidays_df = None
        self.future_dates = None
        self.product_id = None
        self.region = None
        self.warehouse = None

    def _prepare_data(self, df: pd.DataFrame, target_col: str = 'quantity') -> pd.DataFrame:
        prophet_df = df[['date', target_col]].copy()
        prophet_df.columns = ['ds', 'y']
        prophet_df['ds'] = pd.to_datetime(prophet_df['ds'])
        prophet_df = prophet_df.sort_values('ds')
        prophet_df = prophet_df.groupby('ds')['y'].sum().reset_index()
        return prophet_df

    def _prepare_holidays(self, df: pd.DataFrame) -> Optional[pd.DataFrame]:
        if 'is_promotion' not in df.columns:
            return None

        promo_events = []
        for _, row in df[df['is_promotion'] == 1].iterrows():
            promo_events.append({
                'holiday': f"promo_{row['promotion_type']}",
                'ds': row['date'],
                'lower_window': 0,
                'upper_window': 0
            })

        if len(promo_events) > 0:
            holidays_df = pd.DataFrame(promo_events)
            return holidays_df
        return None

    def fit(self, df: pd.DataFrame, target_col: str = 'quantity',
            product_id: str = None, region: str = None, warehouse: str = None) -> 'ProphetModel':
        if Prophet is None:
            raise ImportError("Prophet is not installed. Please install it with: pip install prophet")

        self.product_id = product_id
        self.region = region
        self.warehouse = warehouse

        logger.info(f"Fitting Prophet model for {product_id} - {region} - {warehouse}")

        prophet_df = self._prepare_data(df, target_col)
        self.holidays_df = self._prepare_holidays(df)

        model_params = {
            'changepoint_prior_scale': self.config.get('changepoint_prior_scale', 0.05),
            'seasonality_prior_scale': self.config.get('seasonality_prior_scale', 10.0),
            'yearly_seasonality': self.config.get('yearly_seasonality', True),
            'weekly_seasonality': self.config.get('weekly_seasonality', True),
            'daily_seasonality': self.config.get('daily_seasonality', False),
            'seasonality_mode': self.config.get('seasonality_mode', 'additive'),
            'holidays': self.holidays_df
        }

        self.model = Prophet(**model_params)

        if 'is_holiday' in df.columns:
            self.model.add_regressor('is_holiday')
            prophet_df['is_holiday'] = df.groupby('date')['is_holiday'].max().values

        self.model.fit(prophet_df)
        return self

    def predict(self, periods: int = 180, freq: str = 'D',
                future_exog: pd.DataFrame = None) -> pd.DataFrame:
        if self.model is None:
            raise ValueError("Model has not been fitted yet")

        logger.info(f"Predicting {periods} periods with frequency {freq}")

        self.future_dates = self.model.make_future_dataframe(periods=periods, freq=freq)

        if future_exog is not None and 'is_holiday' in future_exog.columns:
            self.future_dates['is_holiday'] = future_exog['is_holiday'].values[:len(self.future_dates)]

        forecast = self.model.predict(self.future_dates)

        forecast_df = forecast[['ds', 'yhat', 'yhat_lower', 'yhat_upper',
                                'trend', 'trend_lower', 'trend_upper',
                                'yearly', 'yearly_lower', 'yearly_upper',
                                'weekly', 'weekly_lower', 'weekly_upper']].copy()
        forecast_df.columns = ['date', 'forecast', 'forecast_lower', 'forecast_upper',
                               'trend', 'trend_lower', 'trend_upper',
                               'yearly_seasonality', 'yearly_lower', 'yearly_upper',
                               'weekly_seasonality', 'weekly_lower', 'weekly_upper']

        if self.product_id:
            forecast_df['product_id'] = self.product_id
        if self.region:
            forecast_df['region'] = self.region
        if self.warehouse:
            forecast_df['warehouse'] = self.warehouse

        return forecast_df

    def get_components(self) -> Optional[pd.DataFrame]:
        if self.model is None or self.future_dates is None:
            return None
        forecast = self.model.predict(self.future_dates)
        return forecast

    def plot_forecast(self, forecast: pd.DataFrame = None):
        if self.model is None:
            raise ValueError("Model has not been fitted yet")
        if forecast is None:
            forecast = self.model.predict(self.future_dates)
        try:
            return plot_plotly(self.model, forecast)
        except Exception as e:
            logger.warning(f"Could not create interactive plot: {e}")
            return None

    def plot_components(self, forecast: pd.DataFrame = None):
        if self.model is None:
            raise ValueError("Model has not been fitted yet")
        if forecast is None:
            forecast = self.model.predict(self.future_dates)
        try:
            return plot_components_plotly(self.model, forecast)
        except Exception as e:
            logger.warning(f"Could not create components plot: {e}")
            return None

    def evaluate(self, test_df: pd.DataFrame, target_col: str = 'quantity') -> Dict[str, float]:
        logger.info("Evaluating Prophet model...")

        forecast = self.predict(periods=len(test_df))
        test_dates = pd.to_datetime(test_df['date'].unique())
        forecast_test = forecast[forecast['date'].isin(test_dates)].copy()

        actual_test = test_df.groupby('date')[target_col].sum().reset_index()
        merged = forecast_test.merge(actual_test, on='date', how='inner')

        if len(merged) == 0:
            return {'mape': np.nan, 'rmse': np.nan, 'mae': np.nan}

        y_true = merged[target_col].values
        y_pred = merged['forecast'].values

        mape = np.mean(np.abs((y_true - y_pred) / np.maximum(y_true, 1))) * 100
        rmse = np.sqrt(np.mean((y_true - y_pred) ** 2))
        mae = np.mean(np.abs(y_true - y_pred))

        metrics = {
            'mape': mape,
            'rmse': rmse,
            'mae': mae
        }

        logger.info(f"Prophet model metrics: {metrics}")
        return metrics

    def get_cross_validation_metrics(self, horizon: str = '30 days',
                                      initial: str = '365 days',
                                      period: str = '90 days') -> Optional[pd.DataFrame]:
        if self.model is None:
            raise ValueError("Model has not been fitted yet")

        try:
            from prophet.diagnostics import cross_validation, performance_metrics
            df_cv = cross_validation(self.model, horizon=horizon,
                                     initial=initial, period=period)
            df_p = performance_metrics(df_cv)
            return df_p
        except Exception as e:
            logger.warning(f"Cross-validation failed: {e}")
            return None

    def detect_changepoints(self) -> Optional[pd.DataFrame]:
        if self.model is None:
            return None

        changepoints = pd.DataFrame({
            'date': self.model.changepoints,
            'trend_change': self.model.params['delta'].mean(axis=0)
        })

        significant_changepoints = changepoints[
            abs(changepoints['trend_change']) > abs(changepoints['trend_change']).mean()
        ].sort_values('trend_change', ascending=False)

        return significant_changepoints
