import pandas as pd
import numpy as np
from prophet import Prophet
from typing import Tuple, List, Dict, Optional
from datetime import datetime, timedelta


def get_chinese_ecommerce_holidays(start_year: int = 2020, end_year: int = 2027) -> pd.DataFrame:
    holidays = []
    
    for year in range(start_year, end_year + 1):
        holidays.append({
            'holiday': '春节',
            'ds': pd.Timestamp(f'{year}-02-10'),
            'lower_window': -7,
            'upper_window': 3
        })
        
        holidays.append({
            'holiday': '618大促',
            'ds': pd.Timestamp(f'{year}-06-18'),
            'lower_window': -7,
            'upper_window': 2
        })
        
        holidays.append({
            'holiday': '双11大促',
            'ds': pd.Timestamp(f'{year}-11-11'),
            'lower_window': -7,
            'upper_window': 2
        })
        
        holidays.append({
            'holiday': '双12大促',
            'ds': pd.Timestamp(f'{year}-12-12'),
            'lower_window': -3,
            'upper_window': 1
        })
        
        holidays.append({
            'holiday': '年货节',
            'ds': pd.Timestamp(f'{year}-01-20'),
            'lower_window': -5,
            'upper_window': 5
        })
        
        holidays.append({
            'holiday': '五一劳动节',
            'ds': pd.Timestamp(f'{year}-05-01'),
            'lower_window': -2,
            'upper_window': 3
        })
        
        holidays.append({
            'holiday': '国庆黄金周',
            'ds': pd.Timestamp(f'{year}-10-01'),
            'lower_window': -3,
            'upper_window': 4
        })
        
        holidays.append({
            'holiday': '七夕节',
            'ds': pd.Timestamp(f'{year}-08-22'),
            'lower_window': -2,
            'upper_window': 1
        })
        
        holidays.append({
            'holiday': '母亲节',
            'ds': pd.Timestamp(f'{year}-05-12'),
            'lower_window': -2,
            'upper_window': 1
        })
        
        holidays.append({
            'holiday': '父亲节',
            'ds': pd.Timestamp(f'{year}-06-16'),
            'lower_window': -2,
            'upper_window': 1
        })
    
    return pd.DataFrame(holidays)


class SalesForecaster:
    def __init__(self, changepoint_prior_scale: float = 0.05, 
                 seasonality_prior_scale: float = 10.0,
                 holidays_prior_scale: float = 10.0,
                 use_default_holidays: bool = True):
        self.changepoint_prior_scale = changepoint_prior_scale
        self.seasonality_prior_scale = seasonality_prior_scale
        self.holidays_prior_scale = holidays_prior_scale
        self.use_default_holidays = use_default_holidays
        self.model = None
        self.history = None
        self.custom_holidays = None

    def set_custom_holidays(self, holidays_df: pd.DataFrame):
        self.custom_holidays = holidays_df

    def prepare_data(self, sales_data: pd.DataFrame, promotions: pd.DataFrame = None) -> pd.DataFrame:
        df = sales_data.copy()
        df = df.rename(columns={'date': 'ds', 'sales': 'y'})
        df['ds'] = pd.to_datetime(df['ds'])
        
        if promotions is not None and not promotions.empty:
            promotions = promotions.copy()
            promotions['date'] = pd.to_datetime(promotions['date'])
            promotions = promotions.rename(columns={'date': 'ds'})
            df = df.merge(promotions, on='ds', how='left')
            df['promotion'] = df['promotion'].fillna(0)
        else:
            df['promotion'] = 0
        
        return df

    def fit(self, sales_data: pd.DataFrame, promotions: pd.DataFrame = None,
            custom_holidays: pd.DataFrame = None) -> None:
        df = self.prepare_data(sales_data, promotions)
        self.history = df.copy()
        
        holidays = None
        if custom_holidays is not None:
            holidays = custom_holidays
        elif self.custom_holidays is not None:
            holidays = self.custom_holidays
        elif self.use_default_holidays:
            min_year = df['ds'].dt.year.min()
            max_year = df['ds'].dt.year.max() + 2
            holidays = get_chinese_ecommerce_holidays(min_year, max_year)
        
        self.model = Prophet(
            changepoint_prior_scale=self.changepoint_prior_scale,
            seasonality_prior_scale=self.seasonality_prior_scale,
            holidays_prior_scale=self.holidays_prior_scale,
            yearly_seasonality=True,
            weekly_seasonality=True,
            daily_seasonality=False,
            holidays=holidays
        )
        
        if 'promotion' in df.columns and df['promotion'].sum() > 0:
            self.model.add_regressor('promotion')
        
        self.model.fit(df)

    def predict(self, periods: int, future_promotions: pd.DataFrame = None, 
                freq: str = 'D') -> Tuple[pd.DataFrame, pd.DataFrame]:
        future = self.model.make_future_dataframe(periods=periods, freq=freq)
        
        if future_promotions is not None and not future_promotions.empty:
            future_promotions = future_promotions.copy()
            future_promotions['date'] = pd.to_datetime(future_promotions['date'])
            future_promotions = future_promotions.rename(columns={'date': 'ds'})
            future = future.merge(future_promotions, on='ds', how='left')
            future['promotion'] = future['promotion'].fillna(0)
        
        if 'promotion' in self.history.columns and self.history['promotion'].sum() > 0:
            if 'promotion' not in future.columns:
                future['promotion'] = 0
        
        forecast = self.model.predict(future)
        
        historical_forecast = forecast[forecast['ds'] <= self.history['ds'].max()]
        future_forecast = forecast[forecast['ds'] > self.history['ds'].max()]
        
        return forecast, future_forecast

    def get_prediction_intervals(self, future_forecast: pd.DataFrame) -> pd.DataFrame:
        return future_forecast[['ds', 'yhat', 'yhat_lower', 'yhat_upper']].copy()

    def get_components(self, forecast: pd.DataFrame) -> Dict:
        components = {
            'trend': forecast[['ds', 'trend']],
            'yearly': forecast[['ds', 'yearly']] if 'yearly' in forecast.columns else None,
            'weekly': forecast[['ds', 'weekly']] if 'weekly' in forecast.columns else None,
            'holidays': forecast[['ds', 'holidays']] if 'holidays' in forecast.columns else None,
        }
        
        holiday_cols = [col for col in forecast.columns if col not in ['ds', 'trend', 'yearly', 'weekly', 
                                                                       'yhat', 'yhat_lower', 'yhat_upper',
                                                                       'trend_lower', 'trend_upper',
                                                                       'yearly_lower', 'yearly_upper',
                                                                       'weekly_lower', 'weekly_upper',
                                                                       'additive_terms', 'additive_terms_lower',
                                                                       'additive_terms_upper', 'multiplicative_terms',
                                                                       'multiplicative_terms_lower', 'multiplicative_terms_upper',
                                                                       'holidays_lower', 'holidays_upper']]
        if holiday_cols:
            components['individual_holidays'] = forecast[['ds'] + holiday_cols]
        
        return components

    def get_holiday_effects(self, forecast: pd.DataFrame) -> pd.DataFrame:
        if 'holidays' in forecast.columns:
            return forecast[['ds', 'holidays']].copy()
        return pd.DataFrame(columns=['ds', 'holidays'])


def calculate_forecast_metrics(actual: pd.Series, predicted: pd.Series) -> Dict:
    mask = ~(actual.isna() | predicted.isna())
    actual = actual[mask]
    predicted = predicted[mask]
    
    if len(actual) == 0:
        return {'mae': None, 'mape': None, 'rmse': None}
    
    mae = np.mean(np.abs(actual - predicted))
    mape = np.mean(np.abs((actual - predicted) / actual)) * 100
    rmse = np.sqrt(np.mean((actual - predicted) ** 2))
    
    return {'mae': mae, 'mape': mape, 'rmse': rmse}


def estimate_cost_parameters(historical_sales: pd.DataFrame, 
                           historical_inventory: pd.DataFrame,
                           historical_orders: pd.DataFrame,
                           target_service_level: float = 0.95) -> Dict:
    sales = historical_sales.copy()
    sales['date'] = pd.to_datetime(sales['date'])
    sales = sales.sort_values('date')
    
    daily_demand = sales['sales'].values
    demand_mean = np.mean(daily_demand)
    demand_std = np.std(daily_demand)
    
    if historical_inventory is not None and len(historical_inventory) > 0:
        inv = historical_inventory.copy()
        inv['date'] = pd.to_datetime(inv['date'])
        inv = inv.sort_values('date')
        avg_inventory = inv['inventory'].mean()
    else:
        avg_inventory = demand_mean * 7
    
    stockout_events = 0
    total_periods = len(daily_demand)
    if historical_inventory is not None and len(historical_inventory) > 0:
        merged = inv.merge(sales, on='date', how='inner')
        stockout_events = len(merged[merged['inventory'] <= 0])
        total_periods = len(merged)
    
    stockout_rate = stockout_events / max(total_periods, 1) if total_periods > 0 else 0.05
    
    order_frequency = 0
    avg_order_qty = demand_mean * 7
    if historical_orders is not None and len(historical_orders) > 0:
        orders = historical_orders.copy()
        orders['date'] = pd.to_datetime(orders['date'])
        orders = orders.sort_values('date')
        order_frequency = len(orders) / max((orders['date'].max() - orders['date'].min()).days, 1)
        avg_order_qty = orders['quantity'].mean()
    
    holding_cost = avg_order_qty * 0.1
    
    stockout_cost = holding_cost * 10
    
    if stockout_rate > 0:
        stockout_cost = (holding_cost * avg_inventory) / max(stockout_rate, 0.01)
    
    z_score = 1.645
    
    estimated_safety_stock = z_score * demand_std
    
    if avg_order_qty > 0:
        implicit_service_level = norm.cdf((avg_order_qty - demand_mean) / max(demand_std, 1))
        implicit_service_level = min(max(implicit_service_level, 0.5), 0.99)
    else:
        implicit_service_level = target_service_level
    
    return {
        'estimated_holding_cost': holding_cost,
        'estimated_stockout_cost': stockout_cost,
        'demand_mean': demand_mean,
        'demand_std': demand_std,
        'avg_inventory': avg_inventory,
        'stockout_rate': stockout_rate,
        'order_frequency': order_frequency,
        'avg_order_qty': avg_order_qty,
        'estimated_safety_stock': estimated_safety_stock,
        'implicit_service_level': implicit_service_level
    }


from scipy.stats import norm
