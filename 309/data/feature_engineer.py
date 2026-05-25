import pandas as pd
import numpy as np
from typing import List, Dict, Optional
import logging
from datetime import timedelta
import holidays

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class FeatureEngineer:
    def __init__(self, country_code: str = 'CN'):
        self.country_code = country_code
        self.holidays = self._load_holidays()

    def _load_holidays(self) -> pd.DataFrame:
        try:
            holiday_list = holidays.CountryHoliday(self.country_code, years=range(2020, 2030))
            holiday_df = pd.DataFrame({
                'date': list(holiday_list.keys()),
                'holiday_name': list(holiday_list.values())
            })
            holiday_df['date'] = pd.to_datetime(holiday_df['date'])
            holiday_df['is_holiday'] = 1
            return holiday_df
        except Exception as e:
            logger.warning(f"Could not load holidays: {e}")
            return pd.DataFrame(columns=['date', 'holiday_name', 'is_holiday'])

    def create_time_features(self, df: pd.DataFrame) -> pd.DataFrame:
        logger.info("Creating time features...")
        df = df.copy()
        df['date'] = pd.to_datetime(df['date'])
        df['year'] = df['date'].dt.year
        df['quarter'] = df['date'].dt.quarter
        df['month'] = df['date'].dt.month
        df['week'] = df['date'].dt.isocalendar().week
        df['day'] = df['date'].dt.day
        df['day_of_week'] = df['date'].dt.dayofweek
        df['day_of_year'] = df['date'].dt.dayofyear
        df['is_weekend'] = (df['day_of_week'] >= 5).astype(int)
        df['is_month_start'] = df['date'].dt.is_month_start.astype(int)
        df['is_month_end'] = df['date'].dt.is_month_end.astype(int)
        df['is_quarter_start'] = df['date'].dt.is_quarter_start.astype(int)
        df['is_quarter_end'] = df['date'].dt.is_quarter_end.astype(int)

        df['month_sin'] = np.sin(2 * np.pi * df['month'] / 12)
        df['month_cos'] = np.cos(2 * np.pi * df['month'] / 12)
        df['week_sin'] = np.sin(2 * np.pi * df['week'] / 52)
        df['week_cos'] = np.cos(2 * np.pi * df['week'] / 52)
        df['day_sin'] = np.sin(2 * np.pi * df['day_of_week'] / 7)
        df['day_cos'] = np.cos(2 * np.pi * df['day_of_week'] / 7)

        return df

    def create_holiday_features(self, df: pd.DataFrame) -> pd.DataFrame:
        logger.info("Creating holiday features...")
        df = df.copy()
        df['date'] = pd.to_datetime(df['date'])

        if not self.holidays.empty:
            df = df.merge(self.holidays[['date', 'is_holiday']], on='date', how='left')
            df['is_holiday'] = df['is_holiday'].fillna(0).astype(int)

            df['days_until_holiday'] = df.apply(
                lambda row: self._days_until_next_holiday(row['date']), axis=1
            )
            df['days_since_holiday'] = df.apply(
                lambda row: self._days_since_last_holiday(row['date']), axis=1
            )
        else:
            df['is_holiday'] = 0
            df['days_until_holiday'] = -1
            df['days_since_holiday'] = -1

        return df

    def _days_until_next_holiday(self, current_date: pd.Timestamp) -> int:
        if self.holidays.empty:
            return -1
        future_holidays = self.holidays[self.holidays['date'] > current_date]['date']
        if len(future_holidays) > 0:
            next_holiday = future_holidays.min()
            return (next_holiday - current_date).days
        return -1

    def _days_since_last_holiday(self, current_date: pd.Timestamp) -> int:
        if self.holidays.empty:
            return -1
        past_holidays = self.holidays[self.holidays['date'] < current_date]['date']
        if len(past_holidays) > 0:
            last_holiday = past_holidays.max()
            return (current_date - last_holiday).days
        return -1

    def create_lag_features(self, df: pd.DataFrame, target_col: str = 'quantity',
                            lags: List[int] = [1, 7, 14, 30, 60, 90]) -> pd.DataFrame:
        logger.info(f"Creating lag features for {target_col}...")
        df = df.copy()
        df = df.sort_values(['product_id', 'region', 'warehouse', 'date'])

        for lag in lags:
            df[f'lag_{lag}'] = df.groupby(['product_id', 'region', 'warehouse'])[target_col].shift(lag)

        return df

    def create_rolling_features(self, df: pd.DataFrame, target_col: str = 'quantity',
                                windows: List[int] = [7, 14, 30, 60, 90]) -> pd.DataFrame:
        logger.info(f"Creating rolling features for {target_col}...")
        df = df.copy()
        df = df.sort_values(['product_id', 'region', 'warehouse', 'date'])

        for window in windows:
            df[f'rolling_mean_{window}'] = df.groupby(
                ['product_id', 'region', 'warehouse']
            )[target_col].transform(
                lambda x: x.shift(1).rolling(window=window, min_periods=1).mean()
            )
            df[f'rolling_std_{window}'] = df.groupby(
                ['product_id', 'region', 'warehouse']
            )[target_col].transform(
                lambda x: x.shift(1).rolling(window=window, min_periods=1).std()
            )
            df[f'rolling_min_{window}'] = df.groupby(
                ['product_id', 'region', 'warehouse']
            )[target_col].transform(
                lambda x: x.shift(1).rolling(window=window, min_periods=1).min()
            )
            df[f'rolling_max_{window}'] = df.groupby(
                ['product_id', 'region', 'warehouse']
            )[target_col].transform(
                lambda x: x.shift(1).rolling(window=window, min_periods=1).max()
            )

        return df

    def create_expanding_features(self, df: pd.DataFrame, target_col: str = 'quantity') -> pd.DataFrame:
        logger.info(f"Creating expanding features for {target_col}...")
        df = df.copy()
        df = df.sort_values(['product_id', 'region', 'warehouse', 'date'])

        df['expanding_mean'] = df.groupby(
            ['product_id', 'region', 'warehouse']
        )[target_col].transform(
            lambda x: x.shift(1).expanding(min_periods=1).mean()
        )
        df['expanding_std'] = df.groupby(
            ['product_id', 'region', 'warehouse']
        )[target_col].transform(
            lambda x: x.shift(1).expanding(min_periods=1).std()
        )

        return df

    def create_promotion_features(self, df: pd.DataFrame) -> pd.DataFrame:
        logger.info("Creating promotion features...")
        df = df.copy()

        if 'is_promotion' in df.columns:
            df = df.sort_values(['product_id', 'region', 'warehouse', 'date'])

            df['promotion_rollout'] = df.groupby(
                ['product_id', 'region', 'warehouse']
            )['is_promotion'].transform(
                lambda x: (x == 1).cumsum()
            )

            df['days_since_last_promo'] = df.groupby(
                ['product_id', 'region', 'warehouse']
            )['is_promotion'].transform(
                lambda x: x.shift(1).rolling(window=365, min_periods=1).apply(
                    lambda y: (y == 0).cumprod().sum() if len(y) > 0 else 0
                )
            )

            df['promo_next_7d'] = df.groupby(
                ['product_id', 'region', 'warehouse']
            )['is_promotion'].transform(
                lambda x: x.shift(-1).rolling(window=7, min_periods=1).max()
            )

        return df

    def create_categorical_features(self, df: pd.DataFrame,
                                    cat_cols: List[str] = None) -> pd.DataFrame:
        logger.info("Creating categorical features...")
        df = df.copy()

        if cat_cols is None:
            cat_cols = ['product_id', 'region', 'warehouse', 'category', 'promotion_type']

        for col in cat_cols:
            if col in df.columns:
                df[f'{col}_encoded'] = df[col].astype('category').cat.codes

        return df

    def create_all_features(self, df: pd.DataFrame, target_col: str = 'quantity',
                            include_lags: bool = True, include_rolling: bool = True,
                            lags: List[int] = None, windows: List[int] = None) -> pd.DataFrame:
        logger.info("Creating all features...")
        df = df.copy()

        df = self.create_time_features(df)
        df = self.create_holiday_features(df)

        if include_lags:
            df = self.create_lag_features(df, target_col, lags or [1, 7, 14, 30, 60, 90])

        if include_rolling:
            df = self.create_rolling_features(df, target_col, windows or [7, 14, 30, 60, 90])

        df = self.create_expanding_features(df, target_col)
        df = self.create_promotion_features(df)
        df = self.create_categorical_features(df)

        df = df.replace([np.inf, -np.inf], np.nan)
        df = df.fillna(0)

        return df

    def get_feature_columns(self, df: pd.DataFrame, exclude_cols: List[str] = None) -> List[str]:
        if exclude_cols is None:
            exclude_cols = ['date', 'quantity', 'product_name', 'supplier_name',
                            'launch_date', 'holiday_name']

        feature_cols = [col for col in df.columns if col not in exclude_cols
                        and df[col].dtype in [np.int64, np.float64, int, float]]

        return feature_cols

    def split_train_test(self, df: pd.DataFrame, test_size: float = 0.2,
                         sort_by: str = 'date') -> tuple:
        logger.info("Splitting train and test sets...")
        df = df.copy()
        df = df.sort_values(sort_by)

        split_idx = int(len(df) * (1 - test_size))
        train_df = df.iloc[:split_idx]
        test_df = df.iloc[split_idx:]

        return train_df, test_df

    def split_by_date(self, df: pd.DataFrame, split_date: str,
                      date_col: str = 'date') -> tuple:
        logger.info(f"Splitting data by date: {split_date}...")
        df = df.copy()
        df[date_col] = pd.to_datetime(df[date_col])
        split_dt = pd.to_datetime(split_date)

        train_df = df[df[date_col] < split_dt]
        test_df = df[df[date_col] >= split_dt]

        return train_df, test_df
