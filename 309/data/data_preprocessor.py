import pandas as pd
import numpy as np
from typing import Dict, Optional, Union, List
import logging
from datetime import timedelta

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DataPreprocessor:
    def __init__(self):
        self.processed_data = {}

    def preprocess_sales(self, sales_df: pd.DataFrame) -> pd.DataFrame:
        logger.info("Preprocessing sales data...")
        df = sales_df.copy()
        df = df.sort_values(['product_id', 'region', 'warehouse', 'date'])
        df = df.drop_duplicates(subset=['date', 'product_id', 'region', 'warehouse'], keep='last')
        df['quantity'] = df['quantity'].fillna(0)
        df['quantity'] = df['quantity'].clip(lower=0)
        date_range = self._get_complete_date_range(df)
        df = self._fill_missing_dates(df, date_range)
        df['year'] = df['date'].dt.year
        df['month'] = df['date'].dt.month
        df['week'] = df['date'].dt.isocalendar().week
        df['day_of_week'] = df['date'].dt.dayofweek
        df['is_weekend'] = (df['day_of_week'] >= 5).astype(int)
        self.processed_data['sales'] = df
        return df

    def preprocess_inventory(self, inventory_df: pd.DataFrame) -> pd.DataFrame:
        logger.info("Preprocessing inventory data...")
        df = inventory_df.copy()
        df = df.sort_values(['product_id', 'warehouse', 'date'])
        df['stock_quantity'] = df['stock_quantity'].fillna(method='ffill').fillna(0)
        df['stock_quantity'] = df['stock_quantity'].clip(lower=0)
        self.processed_data['inventory'] = df
        return df

    def preprocess_promotion(self, promotion_df: pd.DataFrame) -> pd.DataFrame:
        logger.info("Preprocessing promotion data...")
        df = promotion_df.copy()
        df['promotion_duration'] = (df['end_date'] - df['start_date']).dt.days + 1
        df['discount'] = df['discount'].fillna(0)
        self.processed_data['promotion'] = df
        return df

    def preprocess_all(self, data: Dict[str, pd.DataFrame]) -> Dict[str, pd.DataFrame]:
        processed = {}
        if 'sales' in data:
            processed['sales'] = self.preprocess_sales(data['sales'])
        if 'inventory' in data:
            processed['inventory'] = self.preprocess_inventory(data['inventory'])
        if 'promotion' in data:
            processed['promotion'] = self.preprocess_promotion(data['promotion'])
        if 'supplier' in data:
            processed['supplier'] = data['supplier'].copy()
        if 'product' in data:
            df = data['product'].copy()
            df['launch_date'] = pd.to_datetime(df['launch_date'])
            processed['product'] = df
        return processed

    def merge_for_forecasting(self, processed_data: Dict[str, pd.DataFrame]) -> pd.DataFrame:
        logger.info("Merging data for forecasting...")
        sales_df = processed_data.get('sales')
        if sales_df is None:
            raise ValueError("Sales data is required for forecasting")

        merged_df = sales_df.copy()

        if 'promotion' in processed_data:
            promo_df = processed_data['promotion']
            merged_df = self._merge_promotions(merged_df, promo_df)

        if 'product' in processed_data:
            product_df = processed_data['product']
            merged_df = merged_df.merge(product_df, on='product_id', how='left')

        if 'supplier' in processed_data:
            supplier_df = processed_data['supplier']
            merged_df = merged_df.merge(supplier_df, on='product_id', how='left')

        if 'inventory' in processed_data:
            inv_df = processed_data['inventory']
            merged_df = merged_df.merge(
                inv_df, on=['date', 'product_id', 'warehouse'], how='left'
            )
            merged_df['stock_quantity'] = merged_df['stock_quantity'].fillna(method='ffill').fillna(0)

        return merged_df

    def _get_complete_date_range(self, df: pd.DataFrame) -> pd.DatetimeIndex:
        min_date = df['date'].min()
        max_date = df['date'].max()
        return pd.date_range(start=min_date, end=max_date, freq='D')

    def _fill_missing_dates(self, df: pd.DataFrame, date_range: pd.DatetimeIndex) -> pd.DataFrame:
        group_cols = ['product_id', 'region', 'warehouse']
        groups = df[group_cols].drop_duplicates()

        expanded_dfs = []
        for _, group in groups.iterrows():
            mask = (
                (df['product_id'] == group['product_id']) &
                (df['region'] == group['region']) &
                (df['warehouse'] == group['warehouse'])
            )
            group_df = df[mask].set_index('date')
            group_df = group_df.reindex(date_range)
            group_df['product_id'] = group['product_id']
            group_df['region'] = group['region']
            group_df['warehouse'] = group['warehouse']
            group_df['quantity'] = group_df['quantity'].fillna(0)
            group_df = group_df.reset_index().rename(columns={'index': 'date'})
            expanded_dfs.append(group_df)

        return pd.concat(expanded_dfs, ignore_index=True)

    def _merge_promotions(self, sales_df: pd.DataFrame, promo_df: pd.DataFrame) -> pd.DataFrame:
        sales_df = sales_df.copy()
        sales_df['is_promotion'] = 0
        sales_df['promotion_discount'] = 0.0
        sales_df['promotion_type'] = 'None'

        for _, promo in promo_df.iterrows():
            mask = (
                (sales_df['product_id'] == promo['product_id']) &
                (sales_df['date'] >= promo['start_date']) &
                (sales_df['date'] <= promo['end_date'])
            )
            sales_df.loc[mask, 'is_promotion'] = 1
            sales_df.loc[mask, 'promotion_discount'] = promo['discount']
            sales_df.loc[mask, 'promotion_type'] = promo['promotion_type']

        return sales_df

    def detect_outliers(self, df: pd.DataFrame, column: str = 'quantity',
                        threshold: float = 3.0) -> pd.DataFrame:
        logger.info(f"Detecting outliers in {column}...")
        df = df.copy()
        df['z_score'] = df.groupby(['product_id', 'region', 'warehouse'])[column].transform(
            lambda x: (x - x.mean()) / x.std() if x.std() > 0 else 0
        )
        df['is_outlier'] = (abs(df['z_score']) > threshold).astype(int)
        return df

    def smooth_data(self, df: pd.DataFrame, column: str = 'quantity',
                    window: int = 7) -> pd.DataFrame:
        logger.info(f"Smoothing {column} with {window}-day moving average...")
        df = df.copy()
        df[f'{column}_smoothed'] = df.groupby(['product_id', 'region', 'warehouse'])[column].transform(
            lambda x: x.rolling(window=window, min_periods=1, center=True).mean()
        )
        return df
