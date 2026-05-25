import pandas as pd
import numpy as np
from typing import Dict, Optional, List, Tuple
import logging
from tqdm import tqdm
from datetime import timedelta

from models.ensemble_model import EnsembleModel
from data.feature_engineer import FeatureEngineer
from config import Config
from .reconciliation import ForecastReconciler

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class HierarchicalForecaster:
    def __init__(self, hierarchy_levels: List[str] = None, config: Optional[Dict] = None):
        self.config = config or Config().config
        self.hierarchy_levels = hierarchy_levels or self.config.get(
            'forecasting.hierarchy_levels', ['product', 'region', 'warehouse']
        )
        self.forecast_horizon = self.config.get('forecasting.forecast_horizon', 180)
        self.forecast_freq = self.config.get('forecasting.forecast_frequency', 'D')
        self.confidence_level = self.config.get('forecasting.confidence_level', 0.95)

        self.models: Dict[str, EnsembleModel] = {}
        self.forecasts: Dict[str, pd.DataFrame] = {}
        self.metrics: Dict[str, Dict] = {}
        self.residuals: Dict[str, pd.DataFrame] = {}
        self.feature_engineer = FeatureEngineer()
        self.reconciler = ForecastReconciler()

    def _aggregate_data(self, df: pd.DataFrame, level: List[str]) -> pd.DataFrame:
        logger.info(f"Aggregating data at level: {level}")

        agg_cols = level + ['date']
        df_agg = df.groupby(agg_cols)['quantity'].sum().reset_index()

        if 'is_promotion' in df.columns:
            promo_agg = df.groupby(agg_cols)['is_promotion'].max().reset_index()
            df_agg = df_agg.merge(promo_agg, on=agg_cols, how='left')

        if 'is_holiday' in df.columns:
            holiday_agg = df.groupby(agg_cols)['is_holiday'].max().reset_index()
            df_agg = df_agg.merge(holiday_agg, on=agg_cols, how='left')

        if 'promotion_discount' in df.columns:
            discount_agg = df.groupby(agg_cols)['promotion_discount'].mean().reset_index()
            df_agg = df_agg.merge(discount_agg, on=agg_cols, how='left')

        return df_agg

    def _get_hierarchy_key(self, row: pd.Series, level: List[str]) -> str:
        return "_".join([str(row[l]) for l in level])

    def _split_data(self, df: pd.DataFrame, test_days: int = 30) -> Tuple[pd.DataFrame, pd.DataFrame]:
        max_date = df['date'].max()
        split_date = max_date - timedelta(days=test_days)

        train_df = df[df['date'] < split_date].copy()
        test_df = df[df['date'] >= split_date].copy()

        return train_df, test_df

    def fit(self, df: pd.DataFrame, levels: Optional[List[List[str]]] = None) -> 'HierarchicalForecaster':
        if levels is None:
            levels = [
                ['product_id'],
                ['region'],
                ['warehouse'],
                ['product_id', 'region'],
                ['product_id', 'warehouse'],
                ['region', 'warehouse'],
                ['product_id', 'region', 'warehouse']
            ]

        logger.info(f"Fitting hierarchical models at {len(levels)} levels")

        for level in tqdm(levels, desc="Fitting hierarchy levels"):
            level_name = "_".join(level)
            logger.info(f"Processing level: {level_name}")

            df_agg = self._aggregate_data(df, level)

            groups = df_agg.groupby(level)
            logger.info(f"Found {len(groups)} groups at level {level_name}")

            for group_key, group_df in tqdm(groups, desc=f"Fitting {level_name}", leave=False):
                group_key_str = "_".join([str(k) for k in group_key]) if isinstance(group_key, tuple) else str(group_key)
                model_key = f"{level_name}_{group_key_str}"

                try:
                    group_df = group_df.sort_values('date')

                    train_df, test_df = self._split_data(group_df)

                    if len(train_df) < 90:
                        logger.warning(f"Skipping {model_key}: insufficient training data ({len(train_df)} rows)")
                        continue

                    train_df_features = self.feature_engineer.create_all_features(
                        train_df, include_lags=True, include_rolling=True
                    )

                    feature_cols = self.feature_engineer.get_feature_columns(train_df_features)

                    test_df_features = self.feature_engineer.create_all_features(
                        test_df, include_lags=True, include_rolling=True
                    )
                    for col in feature_cols:
                        if col not in test_df_features.columns:
                            test_df_features[col] = 0

                    valid_split = int(len(train_df) * 0.8)
                    train_part = train_df_features.iloc[:valid_split]
                    valid_part = train_df_features.iloc[valid_split:]

                    model = EnsembleModel(self.config)
                    model.fit(
                        train_part,
                        feature_cols=feature_cols,
                        target_col='quantity',
                        valid_df=valid_part,
                        product_id=group_key[0] if len(group_key) > 0 and 'product_id' in level else None,
                        region=group_key[level.index('region')] if 'region' in level else None,
                        warehouse=group_key[level.index('warehouse')] if 'warehouse' in level else None
                    )

                    test_metrics = model.evaluate(test_df_features, target_col='quantity')

                    test_predictions = model.predict(periods=len(test_df_features), freq=self.forecast_freq)
                    test_actual = test_df_features[['date', 'quantity']].copy()
                    test_actual.columns = ['date', 'quantity']
                    residual_df = test_actual.merge(test_predictions[['date', 'forecast']], on='date', how='left')
                    residual_df['residual'] = residual_df['quantity'] - residual_df['forecast']
                    residual_df['model_key'] = model_key

                    self.models[model_key] = model
                    self.metrics[model_key] = test_metrics
                    self.residuals[model_key] = residual_df

                except Exception as e:
                    logger.error(f"Error fitting model {model_key}: {e}")
                    continue

        return self

    def predict(self, periods: Optional[int] = None,
                freq: Optional[str] = None) -> Dict[str, pd.DataFrame]:
        periods = periods or self.forecast_horizon
        freq = freq or self.forecast_freq

        logger.info(f"Generating hierarchical forecasts for {periods} periods")

        all_forecasts = []

        for model_key, model in tqdm(self.models.items(), desc="Generating forecasts"):
            try:
                forecast = model.predict(
                    periods=periods,
                    freq=freq,
                    confidence=self.confidence_level
                )
                forecast['model_key'] = model_key

                level_parts = model_key.split('_')
                if 'product_id' in model_key:
                    forecast['level'] = 'product'
                elif 'region' in model_key:
                    forecast['level'] = 'region'
                elif 'warehouse' in model_key:
                    forecast['level'] = 'warehouse'
                else:
                    forecast['level'] = 'combined'

                all_forecasts.append(forecast)
                self.forecasts[model_key] = forecast

            except Exception as e:
                logger.error(f"Error generating forecast for {model_key}: {e}")
                continue

        combined_forecasts = pd.concat(all_forecasts, ignore_index=True)
        self.forecasts['all'] = combined_forecasts

        return self.forecasts

    def reconcile_forecasts(self, method: str = 'mint_shrink',
                              validation_df: pd.DataFrame = None) -> pd.DataFrame:
        logger.info(f"Reconciling forecasts using {method} method")

        if 'all' not in self.forecasts:
            raise ValueError("No forecasts available. Run predict() first.")

        all_forecasts = self.forecasts['all'].copy()

        residuals_df = None
        if len(self.residuals) > 0:
            residuals_df = pd.concat(list(self.residuals.values()), ignore_index=True)

        if validation_df is not None:
            residuals_df = self.reconciler.compute_residuals(all_forecasts, validation_df)

        return self.reconciler.reconcile(
            all_forecasts,
            method=method,
            residuals_df=residuals_df,
            metrics_dict=self.metrics
        )

    def reconcile_all_methods(self, validation_df: pd.DataFrame = None) -> Dict[str, pd.DataFrame]:
        if 'all' not in self.forecasts:
            raise ValueError("No forecasts available. Run predict() first.")

        all_forecasts = self.forecasts['all'].copy()

        residuals_df = None
        if len(self.residuals) > 0:
            residuals_df = pd.concat(list(self.residuals.values()), ignore_index=True)

        if validation_df is not None:
            residuals_df = self.reconciler.compute_residuals(all_forecasts, validation_df)

        return self.reconciler.reconcile_all_methods(
            all_forecasts,
            residuals_df=residuals_df,
            metrics_dict=self.metrics
        )

    def compare_reconciliation_methods(self, reconciled_results: Dict[str, pd.DataFrame],
                                         actual_df: pd.DataFrame = None) -> pd.DataFrame:
        return self.reconciler.compare_methods(reconciled_results, actual_df)

    def get_all_residuals(self) -> pd.DataFrame:
        if not self.residuals:
            return pd.DataFrame(columns=['date', 'model_key', 'quantity', 'forecast', 'residual'])
        return pd.concat(list(self.residuals.values()), ignore_index=True)

    def _reconcile_bottom_up(self, forecasts_df: pd.DataFrame) -> pd.DataFrame:
        logger.info("Performing bottom-up reconciliation")

        bottom_level = forecasts_df[forecasts_df['level'] == 'combined'].copy()

        product_level = bottom_level.groupby(['date', 'product_id']).agg({
            'forecast': 'sum',
            'forecast_lower': 'sum',
            'forecast_upper': 'sum'
        }).reset_index()
        product_level['level'] = 'product'
        product_level['region'] = 'ALL'
        product_level['warehouse'] = 'ALL'

        region_level = bottom_level.groupby(['date', 'region']).agg({
            'forecast': 'sum',
            'forecast_lower': 'sum',
            'forecast_upper': 'sum'
        }).reset_index()
        region_level['level'] = 'region'
        region_level['product_id'] = 'ALL'
        region_level['warehouse'] = 'ALL'

        warehouse_level = bottom_level.groupby(['date', 'warehouse']).agg({
            'forecast': 'sum',
            'forecast_lower': 'sum',
            'forecast_upper': 'sum'
        }).reset_index()
        warehouse_level['level'] = 'warehouse'
        warehouse_level['product_id'] = 'ALL'
        warehouse_level['region'] = 'ALL'

        total_level = bottom_level.groupby(['date']).agg({
            'forecast': 'sum',
            'forecast_lower': 'sum',
            'forecast_upper': 'sum'
        }).reset_index()
        total_level['level'] = 'total'
        total_level['product_id'] = 'ALL'
        total_level['region'] = 'ALL'
        total_level['warehouse'] = 'ALL'

        reconciled = pd.concat([
            bottom_level,
            product_level,
            region_level,
            warehouse_level,
            total_level
        ], ignore_index=True)

        return reconciled

    def _reconcile_top_down(self, forecasts_df: pd.DataFrame) -> pd.DataFrame:
        logger.info("Performing top-down reconciliation")

        total_forecast = forecasts_df[forecasts_df['level'] == 'product'].copy()
        total_forecast = total_forecast.groupby('date')['forecast'].sum().reset_index()
        total_forecast.columns = ['date', 'total_forecast']

        bottom_level = forecasts_df[forecasts_df['level'] == 'combined'].copy()

        bottom_with_total = bottom_level.merge(total_forecast, on='date', how='left')

        bottom_group_totals = bottom_level.groupby('date')['forecast'].sum().reset_index()
        bottom_group_totals.columns = ['date', 'bottom_total']

        bottom_with_total = bottom_with_total.merge(bottom_group_totals, on='date', how='left')

        bottom_with_total['adjustment_factor'] = np.where(
            bottom_with_total['bottom_total'] > 0,
            bottom_with_total['total_forecast'] / bottom_with_total['bottom_total'],
            1
        )

        bottom_with_total['forecast'] = (
            bottom_with_total['forecast'] * bottom_with_total['adjustment_factor']
        )
        bottom_with_total['forecast_lower'] = (
            bottom_with_total['forecast_lower'] * bottom_with_total['adjustment_factor']
        )
        bottom_with_total['forecast_upper'] = (
            bottom_with_total['forecast_upper'] * bottom_with_total['adjustment_factor']
        )

        return bottom_with_total

    def _reconcile_optimal(self, forecasts_df: pd.DataFrame) -> pd.DataFrame:
        logger.info("Performing optimal reconciliation (MinT)")

        bottom_level = forecasts_df[forecasts_df['level'] == 'combined'].copy()

        if len(self.metrics) > 0:
            errors = []
            for model_key, metrics in self.metrics.items():
                if 'ensemble' in metrics:
                    errors.append({
                        'model_key': model_key,
                        'rmse': metrics['ensemble'].get('rmse', np.nan),
                        'mape': metrics['ensemble'].get('mape', np.nan)
                    })

            if len(errors) > 0:
                error_df = pd.DataFrame(errors)
                error_df['weight'] = 1 / (error_df['rmse'] + 1e-6)
                error_df['weight'] = error_df['weight'] / error_df['weight'].sum()

                bottom_level['model_key_base'] = bottom_level['model_key'].apply(
                    lambda x: x.split('_')[0] if '_' in x else x
                )

        return self._reconcile_bottom_up(forecasts_df)

    def get_forecast_by_level(self, level: str) -> pd.DataFrame:
        if 'all' not in self.forecasts:
            raise ValueError("No forecasts available. Run predict() first.")

        return self.forecasts['all'][self.forecasts['all']['level'] == level].copy()

    def get_metrics_summary(self) -> pd.DataFrame:
        if not self.metrics:
            return pd.DataFrame()

        metrics_list = []
        for model_key, metrics in self.metrics.items():
            for model_type, metric_values in metrics.items():
                metrics_list.append({
                    'model_key': model_key,
                    'model_type': model_type,
                    'mape': metric_values.get('mape', np.nan),
                    'rmse': metric_values.get('rmse', np.nan),
                    'mae': metric_values.get('mae', np.nan)
                })

        return pd.DataFrame(metrics_list)

    def get_aggregate_forecast(self, by: List[str] = None) -> pd.DataFrame:
        if by is None:
            by = ['product_id', 'region', 'warehouse']

        if 'all' not in self.forecasts:
            raise ValueError("No forecasts available. Run predict() first.")

        forecasts = self.forecasts['all'].copy()
        agg_cols = ['date'] + by

        result = forecasts.groupby(agg_cols).agg({
            'forecast': 'sum',
            'forecast_lower': 'sum',
            'forecast_upper': 'sum'
        }).reset_index()

        return result
