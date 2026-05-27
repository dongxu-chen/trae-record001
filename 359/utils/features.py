import pandas as pd
import numpy as np
from datetime import datetime
from utils.weather_api import WeatherAPI
from utils.holiday_model import HolidayModel


class FeatureEngineer:
    _holiday_model = None
    
    @classmethod
    def get_holiday_model(cls):
        if cls._holiday_model is None:
            cls._holiday_model = HolidayModel()
        return cls._holiday_model
    
    @staticmethod
    def extract_time_features(order_time):
        if isinstance(order_time, str):
            order_time = pd.to_datetime(order_time)
        elif isinstance(order_time, datetime):
            order_time = pd.Timestamp(order_time)
        
        features = {
            'hour': order_time.hour,
            'day_of_week': order_time.dayofweek,
            'is_weekend': 1 if order_time.dayofweek >= 5 else 0,
            'month': order_time.month,
            'is_work_hour': 1 if 8 <= order_time.hour < 18 else 0,
            'is_night': 1 if (order_time.hour >= 22 or order_time.hour < 6) else 0,
            'quarter': (order_time.month - 1) // 3 + 1,
            'is_holiday_season': 1 if order_time.month in [1, 2, 10, 11, 12] else 0
        }
        return features
    
    @staticmethod
    def extract_holiday_features(order_time):
        if isinstance(order_time, str):
            order_time = pd.to_datetime(order_time)
        elif isinstance(order_time, datetime):
            order_time = pd.Timestamp(order_time)
        
        holiday_model = FeatureEngineer.get_holiday_model()
        holiday_info = holiday_model.get_holiday_info(order_time)
        holiday_features = holiday_model.get_holiday_impact_features(order_time)
        
        return holiday_features, holiday_info
    
    @staticmethod
    def encode_weather(weather):
        weather_map = {
            '晴': 0, '多云': 1, '阴': 2,
            '小雨': 3, '中雨': 4, '大雨': 5, '暴雨': 6, '雷阵雨': 7,
            '小雪': 8, '中雪': 9, '大雪': 10,
            '雾': 11, '霾': 12
        }
        return weather_map.get(weather, 0)
    
    @staticmethod
    def extract_distance_features(route_info):
        if not route_info:
            return {
                'distance': 0, 
                'duration': 0, 
                'tolls': 0,
                'from_cache': 0
            }
        return {
            'distance': route_info.get('distance', 0),
            'duration': route_info.get('duration', 0),
            'tolls': route_info.get('tolls', 0),
            'from_cache': 1 if route_info.get('from_cache') else 0
        }
    
    @staticmethod
    def extract_precipitation_features(weather):
        precip_rate = weather.get('precipitation_rate', 0)
        precip_max = weather.get('precipitation_max', 0)
        precip_coverage = weather.get('precipitation_coverage', 0)
        precip_type = weather.get('precipitation_type', 'none')
        
        type_encoding = {'none': 0, 'rain': 1, 'snow': 2, 'fog': 3, 'haze': 4}
        
        if precip_rate <= 0:
            intensity = 0
        elif precip_rate < 0.5:
            intensity = 1
        elif precip_rate < 2.5:
            intensity = 2
        elif precip_rate < 8:
            intensity = 3
        else:
            intensity = 4
        
        return {
            'precipitation_rate': precip_rate,
            'precipitation_max': precip_max,
            'precipitation_coverage': precip_coverage,
            'precipitation_type': type_encoding.get(precip_type, 0),
            'precipitation_intensity': intensity,
            'has_precipitation': 1 if precip_rate > 0 else 0,
            'heavy_precipitation': 1 if intensity >= 3 else 0
        }
    
    @staticmethod
    def calculate_busy_score(busy_level):
        busy_map = {
            '空闲': 0.2,
            '正常': 0.5,
            '繁忙': 0.8,
            '非常繁忙': 1.0
        }
        return busy_map.get(busy_level, 0.5)
    
    @staticmethod
    def build_features(from_address, to_address, order_time, weather, busy_level, route_info):
        features = {}
        
        time_features = FeatureEngineer.extract_time_features(order_time)
        features.update(time_features)
        
        holiday_features, holiday_info = FeatureEngineer.extract_holiday_features(order_time)
        features.update(holiday_features)
        
        distance_features = FeatureEngineer.extract_distance_features(route_info)
        features.update(distance_features)
        
        precipitation_features = FeatureEngineer.extract_precipitation_features(weather)
        features.update(precipitation_features)
        
        features['weather_encoded'] = FeatureEngineer.encode_weather(weather.get('weather', '晴'))
        features['temperature'] = weather.get('temperature', 20)
        features['humidity'] = weather.get('humidity', 50)
        features['windpower'] = float(str(weather.get('windpower', '2')).replace('级', ''))
        
        features['busy_score'] = FeatureEngineer.calculate_busy_score(busy_level)
        
        features['weather_impact'] = WeatherAPI.weather_to_score(
            weather.get('weather', '晴'),
            features['precipitation_rate'],
            features['precipitation_coverage']
        )
        
        features['busy_impact'] = 1.0 + (features['busy_score'] * 0.3)
        
        precip_impact = WeatherAPI.precipitation_to_impact(
            features['precipitation_rate'],
            weather.get('precipitation_type', 'none')
        )
        features['precipitation_impact'] = precip_impact
        features['overall_impact'] = features['weather_impact'] * (1 + precip_impact) * features['busy_impact']
        
        features['distance_log'] = np.log1p(features['distance'])
        features['speed_estimate'] = features['distance'] / max(features['duration'], 1) if features['duration'] > 0 else 60
        features['expected_drive_hours'] = features['distance'] / 60
        
        return features, holiday_info
