import pandas as pd
import numpy as np
from typing import Dict, Optional, List, Tuple
import logging
from datetime import timedelta

from .prophet_model import ProphetModel
from .lightgbm_model import LightGBMModel
from config import Config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class EnsembleModel:
    def __init__(self, config: Optional[Dict] = None):
        self.config = config or Config().config
        self.prophet_model = ProphetModel(self.config.get('models.prophet', {}))
        self.lgbm_model = LightGBMModel(self.config.get('models.lightgbm', {}))
        self.weights = {'prophet': 0.5, 'lgbm': 0.5}
        self.fitted = False

    def fit(self, train_df: pd.DataFrame, feature_cols: List[str],
            target_col: str = 'quantity',
            valid_df: Optional[pd.DataFrame] = None,
            product_id: str = None, region: str = None, warehouse: str = None) -> 'EnsembleModel':
        logger.info(f"Fitting ensemble model for {product_id} - {region} - {warehouse}")

        self.prophet_model.fit(train_df, target_col, product_id, region, warehouse)
        self.lgbm_model.fit(train_df, feature_cols, target_col, valid_df,
                            product_id, region, warehouse)

        if valid_df is not None and len(valid_df) > 0:
            self._optimize_weights(valid_df, target_col)

        self.fitted = True
        return self

    def _optimize_weights(self, valid_df: pd.DataFrame, target_col: str = 'quantity'):
        logger.info("Optimizing ensemble weights based on validation data...")

        prophet_pred = self.prophet_model.predict(periods=len(valid_df))
        prophet_pred = prophet_pred[prophet_pred['date'].isin(valid_df['date'])]['forecast'].values

        lgbm_pred = self.lgbm_model.predict(valid_df).values

        y_true = valid_df.groupby('date')[target_col].sum().values

        best_mape = float('inf')
        best_weights = None

        for prophet_weight in np.arange(0, 1.01, 0.1):
            lgbm_weight = 1 - prophet_weight
            ensemble_pred = prophet_weight * prophet_pred + lgbm_weight * lgbm_pred

            mape = np.mean(np.abs((y_true - ensemble_pred) / np.maximum(y_true, 1))) * 100

            if mape < best_mape:
                best_mape = mape
                best_weights = {'prophet': prophet_weight, 'lgbm': lgbm_weight}

        if best_weights:
            self.weights = best_weights
            logger.info(f"Optimized weights: {self.weights}, MAPE: {best_mape:.2f}%")

    def predict(self, periods: int = 180, freq: str = 'D',
                future_df: Optional[pd.DataFrame] = None,
                confidence: float = 0.95) -> pd.DataFrame:
        if not self.fitted:
            raise ValueError("Models have not been fitted yet")

        logger.info("Generating ensemble predictions...")

        prophet_forecast = self.prophet_model.predict(periods=periods, freq=freq)

        if future_df is not None:
            lgbm_forecast = self.lgbm_model.predict_with_interval(future_df, confidence=confidence)
        else:
            future_dates = prophet_forecast['date'].unique()
            future_dates = pd.date_range(
                start=future_dates.min(),
                end=future_dates.max(),
                freq=freq
            )
            future_template = pd.DataFrame({'date': future_dates})
            future_template['product_id'] = self.prophet_model.product_id
            future_template['region'] = self.prophet_model.region
            future_template['warehouse'] = self.prophet_model.warehouse

            if self.lgbm_model.feature_cols and len(self.lgbm_model.feature_cols) > 0:
                for col in self.lgbm_model.feature_cols:
                    if col not in future_template.columns:
                        future_template[col] = 0

            lgbm_forecast = self.lgbm_model.predict_with_interval(future_template, confidence=confidence)

        prophet_forecast = prophet_forecast.sort_values('date')
        lgbm_forecast = lgbm_forecast.sort_values('date')

        min_len = min(len(prophet_forecast), len(lgbm_forecast))
        prophet_forecast = prophet_forecast.head(min_len).reset_index(drop=True)
        lgbm_forecast = lgbm_forecast.head(min_len).reset_index(drop=True)

        ensemble_forecast = pd.DataFrame()
        ensemble_forecast['date'] = prophet_forecast['date']
        ensemble_forecast['product_id'] = prophet_forecast.get('product_id', '')
        ensemble_forecast['region'] = prophet_forecast.get('region', '')
        ensemble_forecast['warehouse'] = prophet_forecast.get('warehouse', '')

        prophet_forecast['forecast'] = prophet_forecast['forecast'].fillna(0)
        lgbm_forecast['forecast'] = lgbm_forecast['forecast'].fillna(0)
        prophet_forecast['forecast_lower'] = prophet_forecast['forecast_lower'].fillna(0)
        lgbm_forecast['forecast_lower'] = lgbm_forecast['forecast_lower'].fillna(0)
        prophet_forecast['forecast_upper'] = prophet_forecast['forecast_upper'].fillna(0)
        lgbm_forecast['forecast_upper'] = lgbm_forecast['forecast_upper'].fillna(0)

        ensemble_forecast['prophet_forecast'] = prophet_forecast['forecast']
        ensemble_forecast['lgbm_forecast'] = lgbm_forecast['forecast']

        ensemble_forecast['forecast'] = (
            self.weights['prophet'] * prophet_forecast['forecast'] +
            self.weights['lgbm'] * lgbm_forecast['forecast']
        )

        ensemble_forecast['forecast_lower'] = (
            self.weights['prophet'] * prophet_forecast['forecast_lower'] +
            self.weights['lgbm'] * lgbm_forecast['forecast_lower']
        )

        ensemble_forecast['forecast_upper'] = (
            self.weights['prophet'] * prophet_forecast['forecast_upper'] +
            self.weights['lgbm'] * lgbm_forecast['forecast_upper']
        )

        if 'yearly_seasonality' in prophet_forecast.columns:
            ensemble_forecast['yearly_seasonality'] = prophet_forecast['yearly_seasonality']
        if 'weekly_seasonality' in prophet_forecast.columns:
            ensemble_forecast['weekly_seasonality'] = prophet_forecast['weekly_seasonality']
        if 'trend' in prophet_forecast.columns:
            ensemble_forecast['trend'] = prophet_forecast['trend']

        ensemble_forecast['forecast'] = ensemble_forecast['forecast'].clip(lower=0)
        ensemble_forecast['forecast_lower'] = ensemble_forecast['forecast_lower'].clip(lower=0)

        ensemble_forecast['prophet_weight'] = self.weights['prophet']
        ensemble_forecast['lgbm_weight'] = self.weights['lgbm']

        return ensemble_forecast

    def evaluate(self, test_df: pd.DataFrame, target_col: str = 'quantity') -> Dict[str, Dict]:
        logger.info("Evaluating ensemble model...")

        prophet_metrics = self.prophet_model.evaluate(test_df, target_col)
        lgbm_metrics = self.lgbm_model.evaluate(test_df)

        periods = len(test_df['date'].unique())
        forecast = self.predict(periods=periods)
        forecast = forecast[forecast['date'].isin(test_df['date'])]

        actual = test_df.groupby('date')[target_col].sum().reset_index()
        merged = forecast.merge(actual, on='date', how='inner')

        if len(merged) > 0:
            y_true = merged[target_col].values
            y_pred = merged['forecast'].values

            ensemble_mape = np.mean(np.abs((y_true - y_pred) / np.maximum(y_true, 1))) * 100
            ensemble_rmse = np.sqrt(np.mean((y_true - y_pred) ** 2))
            ensemble_mae = np.mean(np.abs(y_true - y_pred))
        else:
            ensemble_mape = np.nan
            ensemble_rmse = np.nan
            ensemble_mae = np.nan

        ensemble_metrics = {
            'mape': ensemble_mape,
            'rmse': ensemble_rmse,
            'mae': ensemble_mae
        }

        all_metrics = {
            'prophet': prophet_metrics,
            'lightgbm': lgbm_metrics,
            'ensemble': ensemble_metrics
        }

        logger.info(f"Ensemble metrics: {all_metrics}")
        return all_metrics

    def get_feature_importance(self) -> pd.DataFrame:
        return self.lgbm_model.get_feature_importance()

    def get_prophet_components(self) -> Optional[pd.DataFrame]:
        return self.prophet_model.get_components()

    def detect_changepoints(self) -> Optional[pd.DataFrame]:
        return self.prophet_model.detect_changepoints()
