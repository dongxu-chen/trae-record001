import pandas as pd
import numpy as np
import holidays
from datetime import datetime, timedelta
import random

def generate_airline_routes():
    routes = [
        ('北京', '上海'), ('北京', '广州'), ('北京', '深圳'), ('北京', '成都'),
        ('北京', '杭州'), ('上海', '广州'), ('上海', '深圳'), ('上海', '成都'),
        ('上海', '重庆'), ('广州', '成都'), ('广州', '西安'), ('深圳', '杭州'),
        ('深圳', '成都'), ('成都', '西安'), ('北京', '三亚'), ('上海', '三亚'),
        ('广州', '三亚'), ('北京', '厦门'), ('上海', '厦门'), ('北京', '青岛')
    ]
    return routes

def generate_oil_prices(start_date, end_date):
    date_range = pd.date_range(start=start_date, end=end_date, freq='D')
    base_price = 80
    prices = []
    current_price = base_price
    for _ in range(len(date_range)):
        change = np.random.normal(0, 2)
        current_price = max(40, min(150, current_price + change))
        prices.append(current_price)
    return pd.DataFrame({'date': date_range, 'oil_price': prices})

def is_holiday(date):
    cn_holidays = holidays.CN(years=range(2022, 2027))
    if date in cn_holidays:
        return 1
    if date.weekday() >= 5:
        return 0.5
    return 0

def generate_historical_data(start_date='2023-01-01', end_date='2025-12-31', n_samples=50000):
    routes = generate_airline_routes()
    oil_prices = generate_oil_prices(start_date, end_date)
    oil_prices.set_index('date', inplace=True)
    
    data = []
    route_base_prices = {route: random.randint(400, 1500) for route in routes}
    
    for _ in range(n_samples):
        route = random.choice(routes)
        origin, dest = route
        
        departure_date = pd.to_datetime(start_date) + pd.DateOffset(days=random.randint(0, (pd.to_datetime(end_date) - pd.to_datetime(start_date)).days))
        booking_days = random.randint(0, 120)
        search_date = departure_date - pd.DateOffset(days=booking_days)
        
        if search_date < pd.to_datetime(start_date):
            continue
        
        base_price = route_base_prices[route]
        
        oil_price = oil_prices.loc[search_date.strftime('%Y-%m-%d'), 'oil_price'] if search_date.strftime('%Y-%m-%d') in oil_prices.index else 80
        
        holiday_factor = is_holiday(departure_date)
        
        month = departure_date.month
        season_factor = 1.0
        if month in [1, 2, 7, 8]:
            season_factor = 1.3
        elif month in [4, 5, 9, 10]:
            season_factor = 1.1
        
        booking_factor = 1.0
        if booking_days <= 7:
            booking_factor = 1.5
        elif booking_days <= 14:
            booking_factor = 1.2
        elif booking_days <= 30:
            booking_factor = 1.0
        elif booking_days <= 60:
            booking_factor = 0.9
        else:
            booking_factor = 0.85
        
        route_distance_factor = 1.0
        long_routes = [('北京', '三亚'), ('上海', '三亚'), ('北京', '成都'), ('深圳', '成都')]
        if route in long_routes:
            route_distance_factor = 1.4
        
        price = base_price * booking_factor * season_factor * (1 + (oil_price - 80) * 0.005) * (1 + holiday_factor * 0.4) * route_distance_factor
        price = price * np.random.normal(1, 0.15)
        price = max(100, round(price, 0))
        
        data.append({
            'origin': origin,
            'destination': dest,
            'route': f'{origin}-{dest}',
            'departure_date': departure_date,
            'search_date': search_date,
            'booking_days': booking_days,
            'oil_price': oil_price,
            'is_holiday': holiday_factor,
            'month': month,
            'day_of_week': departure_date.weekday(),
            'price': price
        })
    
    df = pd.DataFrame(data)
    return df

if __name__ == '__main__':
    print('正在生成历史数据...')
    df = generate_historical_data()
    print(f'生成数据量: {len(df)} 条')
    print('前5条数据:')
    print(df.head())
    df.to_csv('historical_data.csv', index=False, encoding='utf-8-sig')
    print('数据已保存到 historical_data.csv')
