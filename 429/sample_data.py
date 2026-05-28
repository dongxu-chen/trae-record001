import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Tuple, List


def generate_ecommerce_holidays(start_year: int = 2020, end_year: int = 2027) -> pd.DataFrame:
    holidays = []
    
    for year in range(start_year, end_year + 1):
        holidays.append({
            'holiday': '春节',
            'ds': pd.Timestamp(f'{year}-02-10'),
            'lower_window': -7,
            'upper_window': 3,
            'demand_boost': 1.8
        })
        
        holidays.append({
            'holiday': '618大促',
            'ds': pd.Timestamp(f'{year}-06-18'),
            'lower_window': -7,
            'upper_window': 2,
            'demand_boost': 2.5
        })
        
        holidays.append({
            'holiday': '双11大促',
            'ds': pd.Timestamp(f'{year}-11-11'),
            'lower_window': -7,
            'upper_window': 2,
            'demand_boost': 3.0
        })
        
        holidays.append({
            'holiday': '双12大促',
            'ds': pd.Timestamp(f'{year}-12-12'),
            'lower_window': -3,
            'upper_window': 1,
            'demand_boost': 2.0
        })
        
        holidays.append({
            'holiday': '年货节',
            'ds': pd.Timestamp(f'{year}-01-20'),
            'lower_window': -5,
            'upper_window': 5,
            'demand_boost': 2.2
        })
        
        holidays.append({
            'holiday': '五一劳动节',
            'ds': pd.Timestamp(f'{year}-05-01'),
            'lower_window': -2,
            'upper_window': 3,
            'demand_boost': 1.5
        })
        
        holidays.append({
            'holiday': '国庆黄金周',
            'ds': pd.Timestamp(f'{year}-10-01'),
            'lower_window': -3,
            'upper_window': 4,
            'demand_boost': 1.8
        })
        
        holidays.append({
            'holiday': '七夕节',
            'ds': pd.Timestamp(f'{year}-08-22'),
            'lower_window': -2,
            'upper_window': 1,
            'demand_boost': 1.6
        })
        
        holidays.append({
            'holiday': '母亲节',
            'ds': pd.Timestamp(f'{year}-05-12'),
            'lower_window': -2,
            'upper_window': 1,
            'demand_boost': 1.4
        })
        
        holidays.append({
            'holiday': '父亲节',
            'ds': pd.Timestamp(f'{year}-06-16'),
            'lower_window': -2,
            'upper_window': 1,
            'demand_boost': 1.3
        })
    
    return pd.DataFrame(holidays)


def generate_sample_sales_data(days: int = 365, base_demand: float = 100, 
                             seasonal_amplitude: float = 30, 
                             noise_level: float = 15,
                             include_holiday_effect: bool = True,
                             random_seed: int = 42) -> pd.DataFrame:
    np.random.seed(random_seed)
    
    end_date = datetime.now() - timedelta(days=1)
    start_date = end_date - timedelta(days=days - 1)
    
    dates = pd.date_range(start=start_date, end=end_date, freq='D')
    
    t = np.arange(days)
    
    trend = 0.05 * t
    
    weekly_seasonality = 10 * np.sin(2 * np.pi * t / 7)
    yearly_seasonality = seasonal_amplitude * np.sin(2 * np.pi * t / 365 + np.pi / 2)
    
    noise = np.random.normal(0, noise_level, days)
    
    sales = base_demand + trend + weekly_seasonality + yearly_seasonality + noise
    
    if include_holiday_effect:
        min_year = dates.year.min()
        max_year = dates.year.max()
        holidays_df = generate_ecommerce_holidays(min_year, max_year)
        
        for _, holiday in holidays_df.iterrows():
            holiday_date = holiday['ds']
            lower = holiday['lower_window']
            upper = holiday['upper_window']
            boost = holiday['demand_boost']
            
            for offset in range(lower, upper + 1):
                effect_date = holiday_date + pd.Timedelta(days=offset)
                if effect_date >= start_date and effect_date <= end_date:
                    day_idx = (effect_date - start_date).days
                    if 0 <= day_idx < len(sales):
                        if offset == 0:
                            sales[day_idx] *= boost
                        else:
                            decay = 1 - abs(offset) / max(abs(lower), abs(upper), 1)
                            sales[day_idx] *= (1 + (boost - 1) * decay * 0.5)
    
    sales = np.maximum(10, sales)
    
    return pd.DataFrame({
        'date': dates,
        'sales': sales.astype(int)
    })


def generate_sample_promotions(sales_data: pd.DataFrame, 
                             num_promotions: int = 12) -> pd.DataFrame:
    np.random.seed(42)
    
    dates = pd.Series(sales_data['date']).sample(n=num_promotions, random_state=42).sort_values()
    
    promotions = []
    for date in dates:
        duration = np.random.randint(1, 4)
        promotion_dates = pd.date_range(start=date, periods=duration, freq='D')
        for prom_date in promotion_dates:
            promotions.append({
                'date': prom_date,
                'promotion': np.random.uniform(0.3, 0.8)
            })
    
    promo_df = pd.DataFrame(promotions)
    promo_df = promo_df.drop_duplicates(subset=['date'], keep='last')
    
    return promo_df


def generate_future_promotions(future_days: int = 90, 
                             num_promotions: int = 3) -> pd.DataFrame:
    np.random.seed(42)
    
    start_date = datetime.now()
    dates = pd.date_range(start=start_date + timedelta(days=7), 
                         periods=future_days - 14, freq='D')
    
    selected_dates = pd.Series(dates).sample(n=num_promotions, random_state=42).sort_values()
    
    promotions = []
    for date in selected_dates:
        duration = np.random.randint(2, 5)
        promotion_dates = pd.date_range(start=date, periods=duration, freq='D')
        for prom_date in promotion_dates:
            promotions.append({
                'date': prom_date,
                'promotion': np.random.uniform(0.4, 0.9)
            })
    
    promo_df = pd.DataFrame(promotions)
    promo_df = promo_df.drop_duplicates(subset=['date'], keep='last')
    
    return promo_df


def generate_historical_inventory(sales_data: pd.DataFrame, 
                                initial_stock: float = 500,
                                reorder_point: float = 300,
                                order_quantity: float = 500,
                                lead_time_days: int = 7) -> pd.DataFrame:
    sales = sales_data.copy()
    sales = sales.sort_values('date')
    
    inventory_records = []
    current_stock = initial_stock
    pending_orders = []
    
    for idx, row in sales.iterrows():
        date = row['date']
        daily_sales = row['sales']
        
        for order_date, qty in pending_orders[:]:
            if order_date <= date:
                current_stock += qty
                pending_orders.remove((order_date, qty))
        
        current_stock = max(0, current_stock - daily_sales)
        
        if current_stock <= reorder_point and not pending_orders:
            arrival_date = date + pd.Timedelta(days=lead_time_days)
            pending_orders.append((arrival_date, order_quantity))
        
        inventory_records.append({
            'date': date,
            'inventory': current_stock
        })
    
    return pd.DataFrame(inventory_records)


def generate_historical_orders(sales_data: pd.DataFrame,
                             review_period_days: int = 7,
                             base_order_qty: float = 500) -> pd.DataFrame:
    sales = sales_data.copy()
    sales = sales.sort_values('date')
    
    order_records = []
    n_days = len(sales)
    
    for i in range(0, n_days, review_period_days):
        period_sales = sales.iloc[i:i + review_period_days]['sales'].sum()
        avg_daily = period_sales / max(review_period_days, 1)
        
        order_qty = int(base_order_qty + np.random.normal(0, base_order_qty * 0.1))
        order_qty = max(100, order_qty)
        
        order_records.append({
            'date': sales.iloc[i]['date'],
            'quantity': order_qty,
            'period_demand': period_sales,
            'avg_daily_demand': avg_daily
        })
    
    return pd.DataFrame(order_records)


def get_sample_data() -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    sales_data = generate_sample_sales_data(days=365, base_demand=100)
    promotions = generate_sample_promotions(sales_data)
    future_promotions = generate_future_promotions(future_days=90)
    
    return sales_data, promotions, future_promotions


def get_sample_inventory_params() -> dict:
    return {
        'cost_price': 50.0,
        'selling_price': 120.0,
        'salvage_value': 20.0,
        'service_level': 0.95,
        'lead_time_days': 7,
        'initial_stock': 500,
        'holding_cost': 1.0,
        'stockout_cost': 50.0
    }


def get_full_sample_data() -> dict:
    sales_data, promotions, future_promotions = get_sample_data()
    
    inventory_data = generate_historical_inventory(sales_data)
    orders_data = generate_historical_orders(sales_data)
    
    holidays = generate_ecommerce_holidays(
        sales_data['date'].dt.year.min(),
        sales_data['date'].dt.year.max() + 2
    )
    
    return {
        'sales_data': sales_data,
        'promotions': promotions,
        'future_promotions': future_promotions,
        'inventory_data': inventory_data,
        'orders_data': orders_data,
        'holidays': holidays,
        'inventory_params': get_sample_inventory_params(),
        'supplier_deliveries': generate_supplier_deliveries(),
        'multi_echelon_data': generate_multi_echelon_data()
    }


def generate_supplier_deliveries(num_deliveries: int = 50, 
                                 random_seed: int = 42) -> pd.DataFrame:
    np.random.seed(random_seed)
    
    suppliers = [
        {'supplier_id': 'SUP001', 'supplier_name': '优质供应商A', 'base_lead_time': 7, 'variability': 0.1},
        {'supplier_id': 'SUP002', 'supplier_name': '稳定供应商B', 'base_lead_time': 10, 'variability': 0.05},
        {'supplier_id': 'SUP003', 'supplier_name': '风险供应商C', 'base_lead_time': 14, 'variability': 0.35},
        {'supplier_id': 'SUP004', 'supplier_name': '不可靠供应商D', 'base_lead_time': 21, 'variability': 0.5},
    ]
    
    end_date = datetime.now()
    start_date = end_date - timedelta(days=365)
    
    deliveries = []
    
    for i in range(num_deliveries):
        supplier = suppliers[i % len(suppliers)]
        
        order_date = start_date + timedelta(days=np.random.randint(0, 300))
        promised_lead_time = supplier['base_lead_time']
        actual_lead_time = max(1, int(promised_lead_time * (1 + np.random.normal(0, supplier['variability']))))
        
        promised_date = order_date + timedelta(days=promised_lead_time)
        actual_date = order_date + timedelta(days=actual_lead_time)
        
        order_qty = np.random.randint(200, 800)
        delivered_qty = int(order_qty * np.random.uniform(0.85, 1.0))
        
        deliveries.append({
            'supplier_id': supplier['supplier_id'],
            'supplier_name': supplier['supplier_name'],
            'order_date': order_date,
            'promised_delivery_date': promised_date,
            'actual_delivery_date': actual_date,
            'order_quantity': order_qty,
            'delivered_quantity': delivered_qty,
            'promised_lead_time': promised_lead_time,
            'actual_lead_time': actual_lead_time,
            'deviation': actual_lead_time - promised_lead_time,
            'fulfillment_rate': delivered_qty / order_qty
        })
    
    return pd.DataFrame(deliveries)


def generate_multi_echelon_data() -> dict:
    np.random.seed(42)
    
    warehouse_demand_mean = 500
    warehouse_demand_std = 80
    
    stores = [
        {
            'name': '门店A-北京',
            'demand_mean': 150,
            'demand_std': 25,
            'current_stock': 800,
            'capacity': 2000
        },
        {
            'name': '门店B-上海',
            'demand_mean': 180,
            'demand_std': 30,
            'current_stock': 600,
            'capacity': 2000
        },
        {
            'name': '门店C-广州',
            'demand_mean': 120,
            'demand_std': 20,
            'current_stock': 300,
            'capacity': 1500
        },
        {
            'name': '门店D-成都',
            'demand_mean': 100,
            'demand_std': 18,
            'current_stock': 150,
            'capacity': 1500
        },
    ]
    
    return {
        'warehouse': {
            'name': '中心仓库',
            'demand_mean': warehouse_demand_mean,
            'demand_std': warehouse_demand_std,
            'current_stock': 3000,
            'capacity': 10000
        },
        'stores': stores,
        'transfer_cost_per_unit': 0.5,
        'emergency_transfer_cost': 2.0
    }
