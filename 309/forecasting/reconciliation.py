import pandas as pd
import numpy as np
from typing import Dict, Optional, List, Tuple, Union
import logging
from scipy.linalg import inv, pinv, block_diag
from scipy.optimize import minimize

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ForecastReconciler:
    def __init__(self, hierarchy_structure: Dict = None):
        self.hierarchy_structure = hierarchy_structure or {
            'total': [],
            'product': ['product_id'],
            'region': ['region'],
            'warehouse': ['warehouse'],
            'product_region': ['product_id', 'region'],
            'product_warehouse': ['product_id', 'warehouse'],
            'region_warehouse': ['region', 'warehouse'],
            'bottom': ['product_id', 'region', 'warehouse']
        }
        self.reconciliation_methods = {
            'bottom_up': self._bottom_up,
            'top_down': self._top_down,
            'middle_out': self._middle_out,
            'ols': self._ols_reconciliation,
            'wls': self._wls_reconciliation,
            'mint_shrink': self._mint_shrink,
            'mint_sample': self._mint_sample,
            'struct': self._struct_reconciliation
        }

    def _build_summary_matrix(self, bottom_forecasts: pd.DataFrame,
                               levels: List[List[str]]) -> np.ndarray:
        n_bottom = len(bottom_forecasts)
        n_periods = bottom_forecasts['date'].nunique()
        n_bottom_series = n_bottom // n_periods

        S_rows = []

        for level_cols in levels:
            if not level_cols:
                row = np.ones(n_bottom_series)
                S_rows.append(row)
            else:
                level_groups = bottom_forecasts.groupby(level_cols + ['date'])['forecast'].sum().reset_index()
                groups = bottom_forecasts.groupby(level_cols).size().reset_index().index

                for _ in groups:
                    mask = np.zeros(n_bottom_series)
                    S_rows.append(mask)

        S_rows.append(np.eye(n_bottom_series))

        S = np.array(S_rows)
        return S

    def _get_residual_covariance(self, residuals_df: pd.DataFrame,
                                  method: str = 'shrink') -> np.ndarray:
        n_series = residuals_df['model_key'].nunique()
        n_periods = len(residuals_df) // n_series

        residuals_matrix = []
        for _, group in residuals_df.groupby('model_key'):
            residuals_matrix.append(group['residual'].values)

        R = np.array(residuals_matrix).T

        if method == 'sample':
            cov_matrix = np.cov(R, rowvar=False)
        elif method == 'shrink':
            sample_cov = np.cov(R, rowvar=False)

            lambda_h = self._shrinkage_intensity(R, sample_cov)

            diag = np.diag(np.diag(sample_cov))
            cov_matrix = lambda_h * diag + (1 - lambda_h) * sample_cov
        elif method == 'diagonal':
            sample_cov = np.cov(R, rowvar=False)
            cov_matrix = np.diag(np.diag(sample_cov))
        else:
            cov_matrix = np.eye(n_series)

        return cov_matrix

    def _shrinkage_intensity(self, R: np.ndarray, sample_cov: np.ndarray) -> float:
        T, N = R.shape
        R_demeaned = R - R.mean(axis=0)

        diag = np.diag(sample_cov)
        target = np.mean(diag)

        pi_hat = 0
        for i in range(N):
            for j in range(N):
                sample_cov_ij = sample_cov[i, j]
                target_ij = target if i == j else 0
                diff = (R_demeaned[:, i] * R_demeaned[:, j] - sample_cov_ij)
                pi_hat += np.sum(diff ** 2) / T

        pi_hat /= T

        rho_hat = 0
        for i in range(N):
            for j in range(N):
                if i == j:
                    continue
                sample_cov_ij = sample_cov[i, j]
                theta_ij = np.sum(
                    (R_demeaned[:, i] * R_demeaned[:, j] - sample_cov_ij) ** 2
                ) / T
                rho_hat += theta_ij

        rho_hat /= T * (N ** 2 - N) if N > 1 else 1

        gamma_hat = np.sum((sample_cov - target * np.eye(N)) ** 2)

        lambda_h = max(0, min(1, (pi_hat - rho_hat) / gamma_hat)) if gamma_hat > 0 else 0
        return lambda_h

    def _bottom_up(self, forecasts_df: pd.DataFrame,
                    bottom_level: str = 'combined') -> pd.DataFrame:
        logger.info("Performing bottom-up reconciliation")

        bottom_level_df = forecasts_df[forecasts_df['level'] == bottom_level].copy()

        if bottom_level_df.empty:
            bottom_level_df = forecasts_df[forecasts_df['level'] == 'product_region_warehouse'].copy()

        if bottom_level_df.empty:
            raise ValueError("No bottom-level forecasts found")

        all_levels = []

        all_levels.append(bottom_level_df.assign(level='bottom'))

        product_level = bottom_level_df.groupby(['date', 'product_id']).agg({
            'forecast': 'sum',
            'forecast_lower': 'sum',
            'forecast_upper': 'sum'
        }).reset_index()
        product_level['level'] = 'product'
        product_level['region'] = 'ALL'
        product_level['warehouse'] = 'ALL'
        all_levels.append(product_level)

        region_level = bottom_level_df.groupby(['date', 'region']).agg({
            'forecast': 'sum',
            'forecast_lower': 'sum',
            'forecast_upper': 'sum'
        }).reset_index()
        region_level['level'] = 'region'
        region_level['product_id'] = 'ALL'
        region_level['warehouse'] = 'ALL'
        all_levels.append(region_level)

        warehouse_level = bottom_level_df.groupby(['date', 'warehouse']).agg({
            'forecast': 'sum',
            'forecast_lower': 'sum',
            'forecast_upper': 'sum'
        }).reset_index()
        warehouse_level['level'] = 'warehouse'
        warehouse_level['product_id'] = 'ALL'
        warehouse_level['region'] = 'ALL'
        all_levels.append(warehouse_level)

        product_region_level = bottom_level_df.groupby(['date', 'product_id', 'region']).agg({
            'forecast': 'sum',
            'forecast_lower': 'sum',
            'forecast_upper': 'sum'
        }).reset_index()
        product_region_level['level'] = 'product_region'
        product_region_level['warehouse'] = 'ALL'
        all_levels.append(product_region_level)

        product_warehouse_level = bottom_level_df.groupby(['date', 'product_id', 'warehouse']).agg({
            'forecast': 'sum',
            'forecast_lower': 'sum',
            'forecast_upper': 'sum'
        }).reset_index()
        product_warehouse_level['level'] = 'product_warehouse'
        product_warehouse_level['region'] = 'ALL'
        all_levels.append(product_warehouse_level)

        region_warehouse_level = bottom_level_df.groupby(['date', 'region', 'warehouse']).agg({
            'forecast': 'sum',
            'forecast_lower': 'sum',
            'forecast_upper': 'sum'
        }).reset_index()
        region_warehouse_level['level'] = 'region_warehouse'
        region_warehouse_level['product_id'] = 'ALL'
        all_levels.append(region_warehouse_level)

        total_level = bottom_level_df.groupby(['date']).agg({
            'forecast': 'sum',
            'forecast_lower': 'sum',
            'forecast_upper': 'sum'
        }).reset_index()
        total_level['level'] = 'total'
        total_level['product_id'] = 'ALL'
        total_level['region'] = 'ALL'
        total_level['warehouse'] = 'ALL'
        all_levels.append(total_level)

        reconciled = pd.concat(all_levels, ignore_index=True)
        return reconciled

    def _top_down(self, forecasts_df: pd.DataFrame,
                   top_level: str = 'total',
                   proportion_method: str = 'historical') -> pd.DataFrame:
        logger.info("Performing top-down reconciliation")

        total_forecast = forecasts_df[forecasts_df['level'] == top_level].copy()
        if total_forecast.empty:
            total_forecast = forecasts_df[forecasts_df['level'] == 'product'].copy()
            total_forecast = total_forecast.groupby('date')['forecast'].sum().reset_index()

        bottom_level_df = forecasts_df[forecasts_df['level'] == 'combined'].copy()
        if bottom_level_df.empty:
            bottom_level_df = forecasts_df[forecasts_df['level'] == 'product_region_warehouse'].copy()

        bottom_agg = bottom_level_df.groupby('date')['forecast'].sum().reset_index()
        bottom_agg.columns = ['date', 'bottom_total']

        if proportion_method == 'historical':
            n_series = len(bottom_level_df) // bottom_level_df['date'].nunique()
            avg_forecasts = bottom_level_df.groupby(
                ['product_id', 'region', 'warehouse']
            )['forecast'].mean().reset_index()

            total_avg = avg_forecasts['forecast'].sum()
            avg_forecasts['proportion'] = avg_forecasts['forecast'] / total_avg if total_avg > 0 else 1 / n_series

            proportions = bottom_level_df[['date', 'product_id', 'region', 'warehouse']].merge(
                avg_forecasts[['product_id', 'region', 'warehouse', 'proportion']],
                on=['product_id', 'region', 'warehouse'],
                how='left'
            )
        elif proportion_method == 'forecast':
            proportions = bottom_level_df.merge(bottom_agg, on='date', how='left')
            proportions['proportion'] = np.where(
                proportions['bottom_total'] > 0,
                proportions['forecast'] / proportions['bottom_total'],
                1 / (len(bottom_level_df) / bottom_level_df['date'].nunique())
            )
        else:
            raise ValueError(f"Unknown proportion method: {proportion_method}")

        bottom_reconciled = proportions.merge(total_forecast[['date', 'forecast']], on='date', how='left')
        bottom_reconciled['forecast_reconciled'] = (
            bottom_reconciled['proportion'] * bottom_reconciled['forecast_y']
        )
        bottom_reconciled['forecast_lower_reconciled'] = (
            bottom_reconciled['proportion'] * bottom_reconciled['forecast_y'] * 0.8
        )
        bottom_reconciled['forecast_upper_reconciled'] = (
            bottom_reconciled['proportion'] * bottom_reconciled['forecast_y'] * 1.2
        )

        bottom_reconciled = bottom_reconciled[[
            'date', 'product_id', 'region', 'warehouse',
            'forecast_reconciled', 'forecast_lower_reconciled', 'forecast_upper_reconciled'
        ]].rename(columns={
            'forecast_reconciled': 'forecast',
            'forecast_lower_reconciled': 'forecast_lower',
            'forecast_upper_reconciled': 'forecast_upper'
        })

        bottom_reconciled['level'] = 'bottom'

        return self._bottom_up(bottom_reconciled, bottom_level='bottom')

    def _middle_out(self, forecasts_df: pd.DataFrame,
                    middle_level: str = 'product') -> pd.DataFrame:
        logger.info(f"Performing middle-out reconciliation from {middle_level} level")

        middle_df = forecasts_df[forecasts_df['level'] == middle_level].copy()
        if middle_df.empty:
            raise ValueError(f"Middle level '{middle_level}' not found in forecasts")

        bottom_level_df = forecasts_df[forecasts_df['level'] == 'combined'].copy()
        if bottom_level_df.empty:
            bottom_level_df = forecasts_df[forecasts_df['level'] == 'product_region_warehouse'].copy()

        if middle_level == 'product':
            group_cols = ['product_id']
            bottom_group_cols = ['product_id']
        elif middle_level == 'region':
            group_cols = ['region']
            bottom_group_cols = ['region']
        elif middle_level == 'warehouse':
            group_cols = ['warehouse']
            bottom_group_cols = ['warehouse']
        else:
            raise ValueError(f"Middle level '{middle_level}' not supported")

        bottom_totals = bottom_level_df.groupby(['date'] + bottom_group_cols)['forecast'].sum().reset_index()
        bottom_totals.columns = ['date'] + bottom_group_cols + ['bottom_total']

        middle_totals = middle_df.groupby(['date'] + group_cols)['forecast'].sum().reset_index()
        middle_totals.columns = ['date'] + group_cols + ['middle_total']

        ratios = bottom_totals.merge(middle_totals, on=['date'] + group_cols, how='left')
        ratios['ratio'] = np.where(
            ratios['bottom_total'] > 0,
            ratios['middle_total'] / ratios['bottom_total'],
            1
        )

        bottom_reconciled = bottom_level_df.merge(
            ratios[['date'] + bottom_group_cols + ['ratio']],
            on=['date'] + bottom_group_cols,
            how='left'
        )

        bottom_reconciled['forecast'] = bottom_reconciled['forecast'] * bottom_reconciled['ratio']
        bottom_reconciled['forecast_lower'] = bottom_reconciled['forecast_lower'] * bottom_reconciled['ratio']
        bottom_reconciled['forecast_upper'] = bottom_reconciled['forecast_upper'] * bottom_reconciled['ratio']

        bottom_reconciled = bottom_reconciled.drop(columns=['ratio'])
        bottom_reconciled['level'] = 'bottom'

        return self._bottom_up(bottom_reconciled, bottom_level='bottom')

    def _ols_reconciliation(self, forecasts_df: pd.DataFrame,
                             residuals_df: pd.DataFrame = None) -> pd.DataFrame:
        logger.info("Performing OLS reconciliation")

        bottom_level_df = forecasts_df[forecasts_df['level'] == 'combined'].copy()
        if bottom_level_df.empty:
            bottom_level_df = forecasts_df[forecasts_df['level'] == 'product_region_warehouse'].copy()

        dates = bottom_level_df['date'].unique()
        n_bottom = len(bottom_level_df) // len(dates)

        all_level_forecasts = []
        for level in ['total', 'product', 'region', 'warehouse',
                      'product_region', 'product_warehouse', 'region_warehouse']:
            level_df = forecasts_df[forecasts_df['level'] == level].copy()
            if not level_df.empty:
                level_df = level_df.sort_values('date')
                all_level_forecasts.append(level_df['forecast'].values)

        all_level_forecasts.append(bottom_level_df.sort_values('date')['forecast'].values)

        y_hat = np.array(all_level_forecasts)

        n_total = y_hat.shape[0]
        S = np.zeros((n_total, n_bottom))

        S[0, :] = 1

        idx = 1
        products = bottom_level_df['product_id'].unique()
        for p in products:
            mask = (bottom_level_df['product_id'] == p).values[:n_bottom]
            S[idx, mask] = 1
            idx += 1

        regions = bottom_level_df['region'].unique()
        for r in regions:
            mask = (bottom_level_df['region'] == r).values[:n_bottom]
            S[idx, mask] = 1
            idx += 1

        warehouses = bottom_level_df['warehouse'].unique()
        for w in warehouses:
            mask = (bottom_level_df['warehouse'] == w).values[:n_bottom]
            S[idx, mask] = 1
            idx += 1

        for _, group in bottom_level_df.groupby(['product_id', 'region']):
            if len(group) > 0:
                mask = np.zeros(n_bottom)
                bottom_indices = bottom_level_df[
                    (bottom_level_df['product_id'] == group.iloc[0]['product_id']) &
                    (bottom_level_df['region'] == group.iloc[0]['region'])
                ].index[:n_bottom]
                mask[bottom_indices] = 1
                S[idx, mask] = 1
                idx += 1

        S[-n_bottom:, :] = np.eye(n_bottom)

        try:
            W = np.eye(n_total)
            M = pinv(S.T @ inv(W) @ S) @ S.T @ inv(W)

            reconciled_bottom = M @ y_hat

            bottom_reconciled = bottom_level_df.sort_values('date').copy()
            bottom_reconciled['forecast'] = reconciled_bottom[-n_bottom:, :].T.flatten()

            cv_lower = np.quantile(reconciled_bottom[-n_bottom:, :], 0.025, axis=0)
            cv_upper = np.quantile(reconciled_bottom[-n_bottom:, :], 0.975, axis=0)
            bottom_reconciled['forecast_lower'] = np.maximum(0, cv_lower.repeat(len(dates)))
            bottom_reconciled['forecast_upper'] = cv_upper.repeat(len(dates))

            bottom_reconciled['forecast'] = np.maximum(0, bottom_reconciled['forecast'])
            bottom_reconciled['level'] = 'bottom'

            return self._bottom_up(bottom_reconciled, bottom_level='bottom')

        except Exception as e:
            logger.warning(f"OLS reconciliation failed, falling back to bottom-up: {e}")
            return self._bottom_up(forecasts_df)

    def _wls_reconciliation(self, forecasts_df: pd.DataFrame,
                             metrics_dict: Dict = None) -> pd.DataFrame:
        logger.info("Performing WLS reconciliation")

        if metrics_dict is None:
            logger.warning("No metrics provided for WLS, using OLS instead")
            return self._ols_reconciliation(forecasts_df)

        bottom_level_df = forecasts_df[forecasts_df['level'] == 'combined'].copy()
        if bottom_level_df.empty:
            bottom_level_df = forecasts_df[forecasts_df['level'] == 'product_region_warehouse'].copy()

        dates = bottom_level_df['date'].unique()
        n_bottom = len(bottom_level_df) // len(dates)

        all_level_forecasts = []
        weights = []

        for level in ['total', 'product', 'region', 'warehouse',
                      'product_region', 'product_warehouse', 'region_warehouse']:
            level_df = forecasts_df[forecasts_df['level'] == level].copy()
            if not level_df.empty:
                level_df = level_df.sort_values('date')
                all_level_forecasts.append(level_df['forecast'].values)

                level_rmse = np.nanmean([
                    metrics_dict.get(key, {}).get('ensemble', {}).get('rmse', 1.0)
                    for key in metrics_dict if level in key
                ])
                weights.append(1 / (level_rmse ** 2 + 1e-6))

        all_level_forecasts.append(bottom_level_df.sort_values('date')['forecast'].values)

        bottom_rmse = np.nanmean([
            metrics_dict.get(key, {}).get('ensemble', {}).get('rmse', 1.0)
            for key in metrics_dict if 'combined' in key or 'product_region_warehouse' in key
        ])
        weights.append(1 / (bottom_rmse ** 2 + 1e-6))

        y_hat = np.array(all_level_forecasts)
        W = np.diag(weights)

        n_total = y_hat.shape[0]
        S = np.zeros((n_total, n_bottom))
        S[0, :] = 1

        idx = 1
        products = bottom_level_df['product_id'].unique()
        for p in products:
            mask = (bottom_level_df['product_id'] == p).values[:n_bottom]
            S[idx, mask] = 1
            idx += 1

        regions = bottom_level_df['region'].unique()
        for r in regions:
            mask = (bottom_level_df['region'] == r).values[:n_bottom]
            S[idx, mask] = 1
            idx += 1

        warehouses = bottom_level_df['warehouse'].unique()
        for w in warehouses:
            mask = (bottom_level_df['warehouse'] == w).values[:n_bottom]
            S[idx, mask] = 1
            idx += 1

        S[-n_bottom:, :] = np.eye(n_bottom)

        try:
            M = pinv(S.T @ W @ S) @ S.T @ W
            reconciled_bottom = M @ y_hat

            bottom_reconciled = bottom_level_df.sort_values('date').copy()
            bottom_reconciled['forecast'] = reconciled_bottom[-n_bottom:, :].T.flatten()
            bottom_reconciled['forecast'] = np.maximum(0, bottom_reconciled['forecast'])

            residuals = y_hat[-n_bottom:, :] - reconciled_bottom[-n_bottom:, :]
            std_resid = np.std(residuals, axis=0)
            bottom_reconciled['forecast_lower'] = np.maximum(
                0, bottom_reconciled['forecast'] - 1.96 * std_resid.repeat(len(dates))
            )
            bottom_reconciled['forecast_upper'] = (
                bottom_reconciled['forecast'] + 1.96 * std_resid.repeat(len(dates))
            )

            bottom_reconciled['level'] = 'bottom'
            return self._bottom_up(bottom_reconciled, bottom_level='bottom')

        except Exception as e:
            logger.warning(f"WLS reconciliation failed, falling back to bottom-up: {e}")
            return self._bottom_up(forecasts_df)

    def _mint_shrink(self, forecasts_df: pd.DataFrame,
                      residuals_df: pd.DataFrame) -> pd.DataFrame:
        logger.info("Performing MinT (Shrink) reconciliation")
        return self._mint_reconciliation(forecasts_df, residuals_df, method='shrink')

    def _mint_sample(self, forecasts_df: pd.DataFrame,
                      residuals_df: pd.DataFrame) -> pd.DataFrame:
        logger.info("Performing MinT (Sample) reconciliation")
        return self._mint_reconciliation(forecasts_df, residuals_df, method='sample')

    def _mint_reconciliation(self, forecasts_df: pd.DataFrame,
                              residuals_df: pd.DataFrame,
                              method: str = 'shrink') -> pd.DataFrame:
        if residuals_df is None or len(residuals_df) == 0:
            logger.warning("No residuals provided for MinT, using WLS instead")
            return self._wls_reconciliation(forecasts_df)

        bottom_level_df = forecasts_df[forecasts_df['level'] == 'combined'].copy()
        if bottom_level_df.empty:
            bottom_level_df = forecasts_df[forecasts_df['level'] == 'product_region_warehouse'].copy()

        dates = bottom_level_df['date'].unique()
        n_bottom = len(bottom_level_df) // len(dates)

        try:
            W = self._get_residual_covariance(residuals_df, method=method)

            all_level_forecasts = []
            for level in ['total', 'product', 'region', 'warehouse',
                          'product_region', 'product_warehouse', 'region_warehouse']:
                level_df = forecasts_df[forecasts_df['level'] == level].copy()
                if not level_df.empty:
                    level_df = level_df.sort_values('date')
                    all_level_forecasts.append(level_df['forecast'].values)

            all_level_forecasts.append(bottom_level_df.sort_values('date')['forecast'].values)
            y_hat = np.array(all_level_forecasts)

            n_total = y_hat.shape[0]
            S = np.zeros((n_total, n_bottom))
            S[0, :] = 1

            idx = 1
            products = bottom_level_df['product_id'].unique()
            for p in products:
                mask = (bottom_level_df['product_id'] == p).values[:n_bottom]
                S[idx, mask] = 1
                idx += 1

            regions = bottom_level_df['region'].unique()
            for r in regions:
                mask = (bottom_level_df['region'] == r).values[:n_bottom]
                S[idx, mask] = 1
                idx += 1

            warehouses = bottom_level_df['warehouse'].unique()
            for w in warehouses:
                mask = (bottom_level_df['warehouse'] == w).values[:n_bottom]
                S[idx, mask] = 1
                idx += 1

            S[-n_bottom:, :] = np.eye(n_bottom)

            if W.shape[0] < n_total:
                W_full = np.eye(n_total)
                W_full[-W.shape[0]:, -W.shape[1]:] = W
                W = W_full

            M = pinv(S.T @ pinv(W) @ S) @ S.T @ pinv(W)
            reconciled_bottom = M @ y_hat

            bottom_reconciled = bottom_level_df.sort_values('date').copy()
            bottom_reconciled['forecast'] = reconciled_bottom[-n_bottom:, :].T.flatten()
            bottom_reconciled['forecast'] = np.maximum(0, bottom_reconciled['forecast'])

            residuals = y_hat - S @ reconciled_bottom[-n_bottom:, :]
            std_resid = np.std(residuals[-n_bottom:, :], axis=0)

            bottom_reconciled['forecast_lower'] = np.maximum(
                0, bottom_reconciled['forecast'] - 1.96 * std_resid.repeat(len(dates))
            )
            bottom_reconciled['forecast_upper'] = (
                bottom_reconciled['forecast'] + 1.96 * std_resid.repeat(len(dates))
            )

            bottom_reconciled['level'] = 'bottom'
            return self._bottom_up(bottom_reconciled, bottom_level='bottom')

        except Exception as e:
            logger.warning(f"MinT reconciliation failed, falling back to bottom-up: {e}")
            return self._bottom_up(forecasts_df)

    def _struct_reconciliation(self, forecasts_df: pd.DataFrame) -> pd.DataFrame:
        logger.info("Performing structure-based reconciliation")

        bottom_level_df = forecasts_df[forecasts_df['level'] == 'combined'].copy()
        if bottom_level_df.empty:
            bottom_level_df = forecasts_df[forecasts_df['level'] == 'product_region_warehouse'].copy()

        dates = bottom_level_df['date'].unique()
        n_bottom = len(bottom_level_df) // len(dates)

        bottom_level_df = bottom_level_df.sort_values('date').copy()

        struct_weights = {
            'total': 0.1,
            'product': 0.15,
            'region': 0.15,
            'warehouse': 0.15,
            'product_region': 0.1,
            'product_warehouse': 0.1,
            'region_warehouse': 0.1,
            'bottom': 0.15
        }

        for date_idx, date in enumerate(dates):
            date_mask = bottom_level_df['date'] == date

            bottom_forecasts = bottom_level_df.loc[date_mask, 'forecast'].values

            product_forecasts = {}
            for p in bottom_level_df['product_id'].unique():
                mask = date_mask & (bottom_level_df['product_id'] == p)
                product_forecasts[p] = bottom_level_df.loc[mask, 'forecast'].sum()

            region_forecasts = {}
            for r in bottom_level_df['region'].unique():
                mask = date_mask & (bottom_level_df['region'] == r)
                region_forecasts[r] = bottom_level_df.loc[mask, 'forecast'].sum()

            warehouse_forecasts = {}
            for w in bottom_level_df['warehouse'].unique():
                mask = date_mask & (bottom_level_df['warehouse'] == w)
                warehouse_forecasts[w] = bottom_level_df.loc[mask, 'forecast'].sum()

            for idx in bottom_level_df[date_mask].index:
                p = bottom_level_df.loc[idx, 'product_id']
                r = bottom_level_df.loc[idx, 'region']
                w = bottom_level_df.loc[idx, 'warehouse']

                original = bottom_level_df.loc[idx, 'forecast']

                product_total = product_forecasts[p]
                region_total = region_forecasts[r]
                warehouse_total = warehouse_forecasts[w]

                product_share = original / product_total if product_total > 0 else 1 / len(bottom_forecasts)
                region_share = original / region_total if region_total > 0 else 1 / len(bottom_forecasts)
                warehouse_share = original / warehouse_total if warehouse_total > 0 else 1 / len(bottom_forecasts)

                top_level = forecasts_df[forecasts_df['level'] == 'product']
                if not top_level.empty:
                    product_target = top_level[
                        (top_level['date'] == date) &
                        (top_level['product_id'] == p)
                    ]['forecast'].values
                    if len(product_target) > 0:
                        product_adjusted = product_share * product_target[0]
                    else:
                        product_adjusted = original
                else:
                    product_adjusted = original

                top_region = forecasts_df[forecasts_df['level'] == 'region']
                if not top_region.empty:
                    region_target = top_region[
                        (top_region['date'] == date) &
                        (top_region['region'] == r)
                    ]['forecast'].values
                    if len(region_target) > 0:
                        region_adjusted = region_share * region_target[0]
                    else:
                        region_adjusted = original
                else:
                    region_adjusted = original

                top_warehouse = forecasts_df[forecasts_df['level'] == 'warehouse']
                if not top_warehouse.empty:
                    warehouse_target = top_warehouse[
                        (top_warehouse['date'] == date) &
                        (top_warehouse['warehouse'] == w)
                    ]['forecast'].values
                    if len(warehouse_target) > 0:
                        warehouse_adjusted = warehouse_share * warehouse_target[0]
                    else:
                        warehouse_adjusted = original
                else:
                    warehouse_adjusted = original

                final_forecast = (
                    struct_weights['product'] * product_adjusted +
                    struct_weights['region'] * region_adjusted +
                    struct_weights['warehouse'] * warehouse_adjusted +
                    struct_weights['bottom'] * original
                )

                bottom_level_df.loc[idx, 'forecast'] = max(0, final_forecast)
                bottom_level_df.loc[idx, 'forecast_lower'] = max(0, final_forecast * 0.85)
                bottom_level_df.loc[idx, 'forecast_upper'] = final_forecast * 1.15

        bottom_level_df['level'] = 'bottom'
        return self._bottom_up(bottom_level_df, bottom_level='bottom')

    def reconcile(self, forecasts_df: pd.DataFrame,
                  method: str = 'bottom_up',
                  residuals_df: pd.DataFrame = None,
                  metrics_dict: Dict = None) -> pd.DataFrame:
        if method not in self.reconciliation_methods:
            raise ValueError(
                f"Unknown reconciliation method: {method}. "
                f"Available methods: {list(self.reconciliation_methods.keys())}"
            )

        logger.info(f"Running {method} reconciliation")

        if method in ['ols', 'struct']:
            return self.reconciliation_methods[method](forecasts_df)
        elif method == 'wls':
            return self._wls_reconciliation(forecasts_df, metrics_dict)
        elif method in ['mint_shrink', 'mint_sample']:
            if residuals_df is None:
                logger.warning(f"Residuals required for {method}, using WLS instead")
                return self._wls_reconciliation(forecasts_df, metrics_dict)
            return self.reconciliation_methods[method](forecasts_df, residuals_df)
        else:
            return self.reconciliation_methods[method](forecasts_df)

    def reconcile_all_methods(self, forecasts_df: pd.DataFrame,
                                residuals_df: pd.DataFrame = None,
                                metrics_dict: Dict = None) -> Dict[str, pd.DataFrame]:
        results = {}
        methods = ['bottom_up', 'top_down', 'ols', 'wls', 'mint_shrink', 'struct']

        for method in methods:
            try:
                results[method] = self.reconcile(
                    forecasts_df, method, residuals_df, metrics_dict
                )
                logger.info(f"{method}: SUCCESS")
            except Exception as e:
                logger.warning(f"{method}: FAILED - {e}")

        return results

    def compare_methods(self, reconciled_results: Dict[str, pd.DataFrame],
                         actual_df: pd.DataFrame = None) -> pd.DataFrame:
        comparison = []

        for method_name, reconciled_df in reconciled_results.items():
            bottom_df = reconciled_df[reconciled_df['level'] == 'bottom'].copy()

            total_forecast = bottom_df.groupby('date')['forecast'].sum()
            product_forecasts = bottom_df.groupby(['date', 'product_id'])['forecast'].sum().unstack()
            region_forecasts = bottom_df.groupby(['date', 'region'])['forecast'].sum().unstack()
            warehouse_forecasts = bottom_df.groupby(['date', 'warehouse'])['forecast'].sum().unstack()

            total_row = {
                'method': method_name,
                'total_forecast_sum': total_forecast.sum(),
                'product_count': len(product_forecasts.columns),
                'region_count': len(region_forecasts.columns),
                'warehouse_count': len(warehouse_forecasts.columns),
                'total_mean': total_forecast.mean(),
                'total_std': total_forecast.std()
            }

            if actual_df is not None:
                actual_total = actual_df.groupby('date')['quantity'].sum()
                common_dates = total_forecast.index.intersection(actual_total.index)
                if len(common_dates) > 0:
                    y_true = actual_total.loc[common_dates].values
                    y_pred = total_forecast.loc[common_dates].values
                    mape = np.mean(np.abs((y_true - y_pred) / np.maximum(y_true, 1))) * 100
                    rmse = np.sqrt(np.mean((y_true - y_pred) ** 2))
                    total_row['mape'] = mape
                    total_row['rmse'] = rmse

            comparison.append(total_row)

        return pd.DataFrame(comparison)

    def compute_residuals(self, forecasts_df: pd.DataFrame,
                          actual_df: pd.DataFrame) -> pd.DataFrame:
        logger.info("Computing residuals for reconciliation")

        residuals = []
        for level in forecasts_df['level'].unique():
            level_forecast = forecasts_df[forecasts_df['level'] == level].copy()

            if level == 'total':
                actual_agg = actual_df.groupby('date')['quantity'].sum().reset_index()
                forecast_agg = level_forecast.groupby('date')['forecast'].sum().reset_index()
            elif level == 'product':
                actual_agg = actual_df.groupby(['date', 'product_id'])['quantity'].sum().reset_index()
                forecast_agg = level_forecast.groupby(['date', 'product_id'])['forecast'].sum().reset_index()
            elif level == 'region':
                actual_agg = actual_df.groupby(['date', 'region'])['quantity'].sum().reset_index()
                forecast_agg = level_forecast.groupby(['date', 'region'])['forecast'].sum().reset_index()
            elif level == 'warehouse':
                actual_agg = actual_df.groupby(['date', 'warehouse'])['quantity'].sum().reset_index()
                forecast_agg = level_forecast.groupby(['date', 'warehouse'])['forecast'].sum().reset_index()
            elif level == 'combined' or level == 'bottom':
                actual_agg = actual_df.groupby(['date', 'product_id', 'region', 'warehouse'])['quantity'].sum().reset_index()
                forecast_agg = level_forecast.groupby(['date', 'product_id', 'region', 'warehouse'])['forecast'].sum().reset_index()
            else:
                continue

            merge_cols = ['date']
            if 'product_id' in actual_agg.columns:
                merge_cols.append('product_id')
            if 'region' in actual_agg.columns:
                merge_cols.append('region')
            if 'warehouse' in actual_agg.columns:
                merge_cols.append('warehouse')

            merged = actual_agg.merge(forecast_agg, on=merge_cols, how='inner')
            if len(merged) > 0:
                merged['residual'] = merged['quantity'] - merged['forecast']
                merged['model_key'] = f"{level}_{merged.get('product_id', 'ALL').astype(str)}"
                residuals.append(merged[['date', 'model_key', 'residual']])

        if residuals:
            return pd.concat(residuals, ignore_index=True)
        return pd.DataFrame(columns=['date', 'model_key', 'residual'])
