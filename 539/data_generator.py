import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import random
from geopy.distance import geodesic

np.random.seed(42)
random.seed(42)

CITY_CENTER = (31.2304, 121.4737)
COURIER_NAMES = [f'配送员{i:02d}' for i in range(1, 21)]
WEATHER_TYPES = ['晴', '多云', '小雨', '中雨', '大雨', '小雪', '中雪']
TRAFFIC_LEVELS = ['畅通', '缓行', '拥堵', '严重拥堵']
TIME_PERIODS = ['早高峰', '日间', '晚高峰', '夜间']

def generate_random_coords(center, max_distance_km=15):
    lat, lon = center
    lat_offset = np.random.uniform(-max_distance_km/111, max_distance_km/111)
    lon_offset = np.random.uniform(-max_distance_km/(111*np.cos(np.radians(lat))), 
                                    max_distance_km/(111*np.cos(np.radians(lat))))
    return (lat + lat_offset, lon + lon_offset)

def calculate_distance(pickup, dropoff):
    return geodesic(pickup, dropoff).kilometers

def get_time_period(hour):
    if 7 <= hour < 10:
        return '早高峰'
    elif 10 <= hour < 17:
        return '日间'
    elif 17 <= hour < 20:
        return '晚高峰'
    else:
        return '夜间'

def generate_courier_performance():
    performance = {}
    for courier in COURIER_NAMES:
        performance[courier] = {
            'avg_speed': np.random.uniform(18, 30),
            'reliability_score': np.random.uniform(0.7, 1.0),
            'experience_months': np.random.randint(3, 36),
            'on_time_rate': np.random.uniform(0.82, 0.97),
            'avg_daily_deliveries': np.random.randint(25, 50)
        }
    return performance

def generate_historical_data(n_records=5000, start_date='2024-01-01'):
    courier_perf = generate_courier_performance()
    start_dt = datetime.strptime(start_date, '%Y-%m-%d')
    
    data = []
    
    for i in range(n_records):
        order_date = start_dt + timedelta(days=np.random.randint(0, 90),
                                          hours=np.random.randint(7, 22),
                                          minutes=np.random.randint(0, 60))
        
        pickup_coords = generate_random_coords(CITY_CENTER, 8)
        dropoff_coords = generate_random_coords(CITY_CENTER, 15)
        
        distance = calculate_distance(pickup_coords, dropoff_coords)
        distance = max(0.5, min(distance, 20))
        
        courier = random.choice(COURIER_NAMES)
        courier_data = courier_perf[courier]
        
        weather = np.random.choice(WEATHER_TYPES, p=[0.45, 0.25, 0.15, 0.08, 0.04, 0.02, 0.01])
        traffic = np.random.choice(TRAFFIC_LEVELS, p=[0.4, 0.3, 0.2, 0.1])
        time_period = get_time_period(order_date.hour)
        
        weather_factor = {
            '晴': 1.0, '多云': 1.05, '小雨': 1.2, '中雨': 1.35,
            '大雨': 1.5, '小雪': 1.25, '中雪': 1.45
        }[weather]
        
        traffic_factor = {
            '畅通': 1.0, '缓行': 1.2, '拥堵': 1.5, '严重拥堵': 1.8
        }[traffic]
        
        time_factor = {
            '早高峰': 1.25, '日间': 1.0, '晚高峰': 1.3, '夜间': 0.9
        }[time_period]
        
        courier_factor = 1.0 / (courier_data['reliability_score'] * 
                                (courier_data['experience_months'] / 20 + 0.5))
        
        base_time = distance * 3.5
        
        actual_delivery_minutes = base_time * weather_factor * traffic_factor * time_factor * courier_factor
        actual_delivery_minutes += np.random.normal(0, actual_delivery_minutes * 0.12)
        actual_delivery_minutes = max(5, actual_delivery_minutes)
        
        eta_prediction = actual_delivery_minutes * np.random.uniform(0.85, 1.15)
        
        on_time = 1 if actual_delivery_minutes <= eta_prediction * 1.1 else 0
        
        order_id = f'ORD{order_date.strftime("%Y%m%d")}{i:05d}'
        
        data.append({
            'order_id': order_id,
            'order_datetime': order_date,
            'pickup_lat': pickup_coords[0],
            'pickup_lon': pickup_coords[1],
            'dropoff_lat': dropoff_coords[0],
            'dropoff_lon': dropoff_coords[1],
            'distance_km': round(distance, 2),
            'courier_id': courier,
            'courier_avg_speed': round(courier_data['avg_speed'], 2),
            'courier_reliability': round(courier_data['reliability_score'], 3),
            'courier_experience': courier_data['experience_months'],
            'courier_on_time_rate': round(courier_data['on_time_rate'], 3),
            'weather': weather,
            'traffic_condition': traffic,
            'time_period': time_period,
            'hour': order_date.hour,
            'day_of_week': order_date.weekday(),
            'is_weekend': 1 if order_date.weekday() >= 5 else 0,
            'eta_predicted': round(eta_prediction, 1),
            'actual_delivery_minutes': round(actual_delivery_minutes, 1),
            'on_time': on_time
        })
    
    df = pd.DataFrame(data)
    return df

def generate_couriers_data():
    courier_perf = generate_courier_performance()
    couriers = []
    
    for courier, perf in courier_perf.items():
        couriers.append({
            'courier_id': courier,
            'avg_speed': perf['avg_speed'],
            'reliability_score': perf['reliability_score'],
            'experience_months': perf['experience_months'],
            'on_time_rate': perf['on_time_rate'],
            'avg_daily_deliveries': perf['avg_daily_deliveries'],
            'current_load': np.random.randint(0, 8),
            'status': np.random.choice(['空闲', '配送中', '休息'], p=[0.3, 0.6, 0.1]),
            'current_lat': CITY_CENTER[0] + np.random.uniform(-0.05, 0.05),
            'current_lon': CITY_CENTER[1] + np.random.uniform(-0.05, 0.05)
        })
    
    return pd.DataFrame(couriers)

if __name__ == '__main__':
    print('生成历史配送数据...')
    df = generate_historical_data(5000)
    df.to_csv('data/historical_deliveries.csv', index=False, encoding='utf-8-sig')
    print(f'已生成 {len(df)} 条历史配送数据')
    
    print('生成配送员数据...')
    couriers_df = generate_couriers_data()
    couriers_df.to_csv('data/couriers.csv', index=False, encoding='utf-8-sig')
    print(f'已生成 {len(couriers_df)} 名配送员数据')
