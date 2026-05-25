import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import List, Optional, Dict


def generate_historical_sales_data(
    base_price: float = 100.0,
    base_demand: int = 500,
    price_elasticity: float = -2.5,
    n_periods: int = 365,
    random_seed: int = 42,
) -> pd.DataFrame:
    np.random.seed(random_seed)
    
    dates = [datetime(2024, 1, 1) + timedelta(days=i) for i in range(n_periods)]
    
    price_variations = np.random.normal(0, 0.15, n_periods)
    prices = base_price * (1 + price_variations)
    prices = np.clip(prices, base_price * 0.5, base_price * 1.5)
    
    promotions = np.random.choice([0, 1], n_periods, p=[0.7, 0.3])
    promotion_discount = np.where(promotions == 1, np.random.uniform(0.1, 0.3, n_periods), 0)
    effective_prices = prices * (1 - promotion_discount)
    
    seasonality = 1 + 0.3 * np.sin(2 * np.pi * np.arange(n_periods) / 365)
    trend = 1 + 0.0005 * np.arange(n_periods)
    
    price_effect = (effective_prices / base_price) ** price_elasticity
    
    noise = np.random.normal(1, 0.1, n_periods)
    
    demand = base_demand * price_effect * seasonality * trend * noise
    demand = np.maximum(demand, base_demand * 0.2).astype(int)
    
    advertising = np.random.randint(0, 100, n_periods)
    competitor_price = base_price * np.random.uniform(0.8, 1.2, n_periods)
    temperature = 15 + 15 * np.sin(2 * np.pi * np.arange(n_periods) / 365) + np.random.normal(0, 3, n_periods)
    
    df = pd.DataFrame({
        'date': dates,
        'price': prices.round(2),
        'effective_price': effective_prices.round(2),
        'sales_quantity': demand,
        'is_promotion': promotions,
        'promotion_discount': promotion_discount.round(3),
        'advertising_spend': advertising,
        'competitor_price': competitor_price.round(2),
        'temperature': temperature.round(1),
        'seasonality': seasonality.round(3),
        'revenue': (effective_prices * demand).round(2)
    })
    
    return df


def preprocess_data(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    
    df['price_change'] = df['effective_price'].pct_change()
    df['sales_change'] = df['sales_quantity'].pct_change()
    
    df['price_ratio'] = df['effective_price'] / df['effective_price'].mean()
    df['relative_price'] = df['effective_price'] / df['competitor_price']
    
    df['day_of_week'] = df['date'].dt.dayofweek
    df['month'] = df['date'].dt.month
    df['is_weekend'] = (df['day_of_week'] >= 5).astype(int)
    
    df['lag_price_1'] = df['effective_price'].shift(1)
    df['lag_sales_1'] = df['sales_quantity'].shift(1)
    df['rolling_avg_price_7'] = df['effective_price'].rolling(window=7).mean()
    df['rolling_avg_sales_7'] = df['sales_quantity'].rolling(window=7).mean()
    
    df['log_price'] = np.log(df['effective_price'])
    df['log_sales'] = np.log(df['sales_quantity'])
    
    df = df.dropna()
    
    return df


def create_price_bins(df: pd.DataFrame, n_bins: int = 10) -> pd.DataFrame:
    df = df.copy()
    df['price_bin'] = pd.qcut(df['effective_price'], q=n_bins, labels=False)
    
    bin_stats = df.groupby('price_bin').agg({
        'effective_price': ['mean', 'min', 'max'],
        'sales_quantity': ['mean', 'std', 'count'],
        'revenue': ['mean', 'sum']
    }).round(2)
    
    bin_stats.columns = ['_'.join(col).strip() for col in bin_stats.columns.values]
    bin_stats = bin_stats.reset_index()
    
    return df, bin_stats


def generate_multi_product_sales_data(
    n_products: int = 5,
    n_periods: int = 365,
    base_prices: Optional[List[float]] = None,
    base_demands: Optional[List[int]] = None,
    cross_elasticity_matrix: Optional[np.ndarray] = None,
    random_seed: int = 42,
    category_mapping: Optional[Dict[int, str]] = None
) -> pd.DataFrame:
    np.random.seed(random_seed)
    
    if base_prices is None:
        base_prices = [100.0, 80.0, 150.0, 60.0, 120.0][:n_products]
    if base_demands is None:
        base_demands = [500, 600, 300, 700, 400][:n_products]
    if category_mapping is None:
        categories = ['零食', '饮料', '日用品', '零食', '饮料']
        category_mapping = {i: categories[i] for i in range(n_products)}
    
    if cross_elasticity_matrix is None:
        cross_elasticity_matrix = np.zeros((n_products, n_products))
        for i in range(n_products):
            for j in range(n_products):
                if i == j:
                    cross_elasticity_matrix[i, j] = np.random.uniform(-2.5, -1.5)
                elif category_mapping[i] == category_mapping[j]:
                    cross_elasticity_matrix[i, j] = np.random.uniform(0.3, 0.8)
                else:
                    cross_elasticity_matrix[i, j] = np.random.uniform(-0.2, 0.2)
    
    dates = [datetime(2024, 1, 1) + timedelta(days=i) for i in range(n_periods)]
    
    all_data = []
    
    for p in range(n_products):
        product_seasonality = 1 + np.random.uniform(0.1, 0.3) * np.sin(2 * np.pi * np.arange(n_periods) / 365 + np.random.uniform(0, 2 * np.pi))
        product_trend = 1 + np.random.uniform(0.0002, 0.0008) * np.arange(n_periods)
        
        price_variations = np.random.normal(0, 0.12, n_periods)
        prices = base_prices[p] * (1 + price_variations)
        prices = np.clip(prices, base_prices[p] * 0.5, base_prices[p] * 1.5)
        
        promotions = np.random.choice([0, 1], n_periods, p=[0.75, 0.25])
        promotion_discount = np.where(promotions == 1, np.random.uniform(0.1, 0.3, n_periods), 0)
        effective_prices = prices * (1 - promotion_discount)
        
        demand = np.ones(n_periods) * base_demands[p]
        for j in range(n_products):
            price_ratio = effective_prices / base_prices[p]
            if j == p:
                demand *= price_ratio ** cross_elasticity_matrix[p, j]
            else:
                other_effective = prices * (1 - np.random.choice([0, np.random.uniform(0.1, 0.3)], n_periods))
                other_price_ratio = other_effective / base_prices[j]
                demand *= other_price_ratio ** cross_elasticity_matrix[p, j]
        
        noise = np.random.normal(1, 0.1, n_periods)
        demand *= product_seasonality * product_trend * noise
        demand = np.maximum(demand, base_demands[p] * 0.15).astype(int)
        
        advertising = np.random.randint(0, 80, n_periods)
        competitor_price = base_prices[p] * np.random.uniform(0.85, 1.15, n_periods)
        temperature = 15 + 15 * np.sin(2 * np.pi * np.arange(n_periods) / 365) + np.random.normal(0, 3, n_periods)
        
        product_df = pd.DataFrame({
            'date': dates,
            'product_id': p,
            'product_name': f'商品_{p+1}',
            'category': category_mapping[p],
            'price': prices.round(2),
            'effective_price': effective_prices.round(2),
            'base_price': base_prices[p],
            'sales_quantity': demand,
            'is_promotion': promotions,
            'promotion_discount': promotion_discount.round(3),
            'advertising_spend': advertising,
            'competitor_price': competitor_price.round(2),
            'temperature': temperature.round(1),
            'revenue': (effective_prices * demand).round(2)
        })
        
        all_data.append(product_df)
    
    final_df = pd.concat(all_data, ignore_index=True)
    
    return final_df


def preprocess_multi_product_data(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    
    for product_id in df['product_id'].unique():
        mask = df['product_id'] == product_id
        df.loc[mask, 'price_change'] = df.loc[mask, 'effective_price'].pct_change()
        df.loc[mask, 'sales_change'] = df.loc[mask, 'sales_quantity'].pct_change()
        df.loc[mask, 'price_ratio'] = df.loc[mask, 'effective_price'] / df.loc[mask, 'effective_price'].mean()
        df.loc[mask, 'relative_price'] = df.loc[mask, 'effective_price'] / df.loc[mask, 'competitor_price']
        df.loc[mask, 'lag_price_1'] = df.loc[mask, 'effective_price'].shift(1)
        df.loc[mask, 'lag_sales_1'] = df.loc[mask, 'sales_quantity'].shift(1)
        df.loc[mask, 'rolling_avg_price_7'] = df.loc[mask, 'effective_price'].rolling(window=7).mean()
        df.loc[mask, 'rolling_avg_sales_7'] = df.loc[mask, 'sales_quantity'].rolling(window=7).mean()
        df.loc[mask, 'log_price'] = np.log(df.loc[mask, 'effective_price'])
        df.loc[mask, 'log_sales'] = np.log(df.loc[mask, 'sales_quantity'])
    
    df['day_of_week'] = df['date'].dt.dayofweek
    df['month'] = df['date'].dt.month
    df['is_weekend'] = (df['day_of_week'] >= 5).astype(int)
    
    df = df.dropna()
    
    return df
