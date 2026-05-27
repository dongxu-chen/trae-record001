import pandas as pd
import numpy as np
import random
from datetime import datetime, timedelta
from config import Config
from utils.map_api import MapAPI
from utils.weather_api import WeatherAPI
from utils.features import FeatureEngineer
from utils.holiday_model import HolidayModel
from utils.delay_analyzer import DelayAnalyzer


def generate_training_data(n_samples=5000):
    cities = list(Config.CITY_COORDS.keys())
    weather_types = ['晴', '多云', '阴', '小雨', '中雨', '大雨', '雷阵雨', '小雪', '中雪', '雾']
    weather_weights = [0.35, 0.25, 0.15, 0.1, 0.05, 0.03, 0.02, 0.02, 0.02, 0.01]
    busy_levels = ['空闲', '正常', '繁忙', '非常繁忙']
    busy_weights = [0.15, 0.45, 0.3, 0.1]
    
    map_api = MapAPI(use_mock=True, cache_enabled=True)
    weather_api = WeatherAPI(use_mock=True, cache_enabled=True)
    holiday_model = HolidayModel()
    delay_analyzer = DelayAnalyzer()
    
    data = []
    for i in range(n_samples):
        from_city = random.choice(cities)
        to_city = random.choice([c for c in cities if c != from_city])
        
        from_address = f"{from_city}市某某区某某路{random.randint(1, 100)}号"
        to_address = f"{to_city}市某某区某某路{random.randint(1, 100)}号"
        
        route_info = map_api.calculate_distance(from_address, to_address)
        distance = route_info['distance'] if route_info else random.randint(100, 1500)
        
        order_time = datetime(2024, random.randint(1, 12), random.randint(1, 28),
                              random.randint(0, 23), random.randint(0, 59))
        
        holiday_info = holiday_model.get_holiday_info(order_time)
        
        weather = random.choices(weather_types, weights=weather_weights, k=1)[0]
        temperature = random.randint(-10, 35)
        humidity = random.randint(30, 95)
        windpower = random.randint(1, 6)
        
        to_coords = Config.CITY_COORDS[to_city]
        grid_data = weather_api.get_weather_grid(to_coords[0], to_coords[1], order_time)
        
        precipitation_rate = grid_data['avg_precipitation']
        precipitation_max = grid_data['max_precipitation']
        precipitation_coverage = grid_data['precipitation_coverage']
        
        weather_info = {
            'weather': weather,
            'temperature': temperature,
            'humidity': humidity,
            'windpower': str(windpower),
            'precipitation_rate': precipitation_rate,
            'precipitation_max': precipitation_max,
            'precipitation_coverage': precipitation_coverage
        }
        
        busy_level = random.choices(busy_levels, weights=busy_weights, k=1)[0]
        
        base_hours = distance / 50
        
        time_features = FeatureEngineer.extract_time_features(order_time)
        if time_features['is_weekend']:
            base_hours *= 1.1
        if time_features['is_night']:
            base_hours *= 1.3
        
        base_hours *= holiday_info['delay_factor']
        
        weather_impact = WeatherAPI.weather_to_score(weather, precipitation_rate, precipitation_coverage)
        base_hours /= weather_impact
        
        precipitation_impact = WeatherAPI.precipitation_to_impact(
            precipitation_rate, 
            'snow' if ('雪' in weather and temperature < 2) else ('rain' if '雨' in weather else 'none')
        )
        base_hours *= (1 + precipitation_impact)
        
        busy_score = FeatureEngineer.calculate_busy_score(busy_level)
        base_hours *= (1 + busy_score * 0.3)
        
        base_hours += 4
        
        noise_std = base_hours * 0.12
        noise = np.random.normal(0, noise_std)
        delivery_hours = max(1, base_hours + noise)
        
        expected_hours = distance / 60 + 4
        delay_hours = max(0, delivery_hours - expected_hours)
        delay_pct = (delay_hours / max(expected_hours, 1)) * 100
        
        if delay_pct > 30:
            if precipitation_rate > 2:
                dominant_reason = '天气'
            elif holiday_info['delay_factor'] > 1.3:
                dominant_reason = '爆仓'
            elif busy_score > 0.7:
                dominant_reason = '拥堵'
            else:
                dominant_reason = '天气' if precipitation_rate > 0.5 else '拥堵'
        elif delay_pct > 10:
            if precipitation_rate > 0.5:
                dominant_reason = '天气'
            elif busy_score > 0.5:
                dominant_reason = '拥堵'
            else:
                dominant_reason = '正常'
        else:
            dominant_reason = '正常'
        
        data.append({
            'from_address': from_address,
            'to_address': to_address,
            'from_city': from_city,
            'to_city': to_city,
            'order_time': order_time,
            'weather': weather,
            'temperature': temperature,
            'humidity': humidity,
            'windpower': windpower,
            'precipitation_rate': round(precipitation_rate, 3),
            'precipitation_max': round(precipitation_max, 3),
            'precipitation_coverage': round(precipitation_coverage, 3),
            'busy_level': busy_level,
            'distance': distance,
            'delivery_hours': round(delivery_hours, 2),
            'is_holiday': 1 if holiday_info['is_holiday'] else 0,
            'holiday_name': holiday_info['holiday_name'] if holiday_info['is_holiday'] else '',
            'holiday_volume_factor': holiday_info['volume_factor'],
            'holiday_delay_factor': holiday_info['delay_factor'],
            'delay_hours': round(delay_hours, 2),
            'delay_pct': round(delay_pct, 1),
            'delay_reason': dominant_reason
        })
    
    df = pd.DataFrame(data)
    return df


if __name__ == '__main__':
    print("正在生成训练数据...")
    df = generate_training_data(5000)
    df.to_csv(Config.DATA_PATH, index=False, encoding='utf-8-sig')
    print(f"数据已保存到 {Config.DATA_PATH}")
    print(f"共生成 {len(df)} 条样本")
    print("\n数据概览:")
    print(df.head())
    print("\n统计信息:")
    print(df[['delivery_hours', 'distance', 'precipitation_rate']].describe())
