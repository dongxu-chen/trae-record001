import pandas as pd
import numpy as np
from datetime import datetime
from geopy.distance import geodesic

class FeatureEngineer:
    def __init__(self):
        self.weather_mapping = {
            '晴': 0, '多云': 1, '小雨': 2, '中雨': 3,
            '大雨': 4, '小雪': 5, '中雪': 6
        }
        self.traffic_mapping = {
            '畅通': 0, '缓行': 1, '拥堵': 2, '严重拥堵': 3
        }
        self.time_period_mapping = {
            '早高峰': 0, '日间': 1, '晚高峰': 2, '夜间': 3
        }
    
    def extract_time_features(self, df, datetime_col='order_datetime'):
        if isinstance(df[datetime_col].iloc[0], str):
            df[datetime_col] = pd.to_datetime(df[datetime_col])
        
        df['hour'] = df[datetime_col].dt.hour
        df['day_of_week'] = df[datetime_col].dt.dayofweek
        df['day_of_month'] = df[datetime_col].dt.day
        df['month'] = df[datetime_col].dt.month
        df['week_of_year'] = df[datetime_col].dt.isocalendar().week
        df['is_weekend'] = (df[datetime_col].dt.dayofweek >= 5).astype(int)
        
        df['hour_sin'] = np.sin(2 * np.pi * df['hour'] / 24)
        df['hour_cos'] = np.cos(2 * np.pi * df['hour'] / 24)
        df['day_sin'] = np.sin(2 * np.pi * df['day_of_week'] / 7)
        df['day_cos'] = np.cos(2 * np.pi * df['day_of_week'] / 7)
        
        def get_time_period(hour):
            if 7 <= hour < 10:
                return '早高峰'
            elif 10 <= hour < 17:
                return '日间'
            elif 17 <= hour < 20:
                return '晚高峰'
            else:
                return '夜间'
        
        df['time_period'] = df['hour'].apply(get_time_period)
        df['is_rush_hour'] = df['time_period'].isin(['早高峰', '晚高峰']).astype(int)
        
        return df
    
    def extract_weather_features(self, df):
        df['weather_encoded'] = df['weather'].map(self.weather_mapping)
        
        weather_severity = {
            '晴': 0, '多云': 0, '小雨': 1, '中雨': 2,
            '大雨': 3, '小雪': 1, '中雪': 2
        }
        df['weather_severity'] = df['weather'].map(weather_severity)
        
        df['is_rain'] = df['weather'].str.contains('雨').astype(int)
        df['is_snow'] = df['weather'].str.contains('雪').astype(int)
        df['is_bad_weather'] = (df['weather_severity'] >= 2).astype(int)
        
        return df
    
    def extract_traffic_features(self, df):
        df['traffic_encoded'] = df['traffic_condition'].map(self.traffic_mapping)
        
        traffic_factor = {
            '畅通': 1.0, '缓行': 1.2, '拥堵': 1.5, '严重拥堵': 1.8
        }
        df['traffic_factor'] = df['traffic_condition'].map(traffic_factor)
        
        return df
    
    def extract_courier_features(self, df):
        df['time_period_encoded'] = df['time_period'].map(self.time_period_mapping)
        
        df['speed_distance_ratio'] = df['courier_avg_speed'] / df['distance_km']
        
        df['courier_efficiency'] = (
            df['courier_avg_speed'] * df['courier_reliability'] * 
            np.sqrt(df['courier_experience'] / 12)
        )
        
        df['workload_score'] = df['courier_on_time_rate'] / (df['courier_avg_speed'] / 25)
        
        return df
    
    def extract_spatial_features(self, df):
        city_center = (31.2304, 121.4737)
        
        df['pickup_to_center'] = df.apply(
            lambda x: geodesic((x['pickup_lat'], x['pickup_lon']), city_center).km, axis=1
        )
        df['dropoff_to_center'] = df.apply(
            lambda x: geodesic((x['dropoff_lat'], x['dropoff_lon']), city_center).km, axis=1
        )
        
        df['lat_diff'] = df['dropoff_lat'] - df['pickup_lat']
        df['lon_diff'] = df['dropoff_lon'] - df['pickup_lon']
        
        df['direction'] = np.arctan2(df['lat_diff'], df['lon_diff'])
        
        return df
    
    def extract_historical_features(self, df, decay_half_life_days=14):
        if isinstance(df['order_datetime'].iloc[0], str):
            df['order_datetime'] = pd.to_datetime(df['order_datetime'])
        
        max_date = df['order_datetime'].max()
        
        df['days_before_current'] = (max_date - df['order_datetime']).dt.days
        
        df['time_decay_weight'] = np.exp(-df['days_before_current'] * np.log(2) / decay_half_life_days)
        
        def weighted_avg(group):
            weights = group['time_decay_weight']
            weighted_time = np.average(group['actual_delivery_minutes'], weights=weights)
            weighted_ot = np.average(group['on_time'], weights=weights)
            weighted_dist = np.average(group['distance_km'], weights=weights)
            
            diffs = group['actual_delivery_minutes'] - weighted_time
            weighted_std = np.sqrt(np.average(diffs**2, weights=weights))
            
            return pd.Series({
                'courier_avg_time': weighted_time,
                'courier_std_time': weighted_std,
                'courier_avg_distance': weighted_dist,
                'courier_ot_rate': weighted_ot
            })
        
        courier_stats = df.groupby('courier_id').apply(weighted_avg).reset_index()
        
        simple_stats = df.groupby('courier_id').agg({
            'actual_delivery_minutes': ['mean', 'median']
        }).reset_index()
        simple_stats.columns = ['courier_id', 'simple_avg_time', 'simple_median_time']
        
        courier_stats = courier_stats.merge(simple_stats, on='courier_id', how='left')
        
        courier_stats['recency_bias'] = courier_stats['courier_avg_time'] / courier_stats['simple_avg_time']
        
        df = df.merge(courier_stats, on='courier_id', how='left')
        
        df['expected_time_by_distance'] = df['distance_km'] * (df['courier_avg_time'] / df['courier_avg_distance'])
        
        df['recent_perf_trend'] = df['courier_avg_time'] / df['simple_median_time']
        
        return df
    
    def engineer_features(self, df, is_training=True):
        df = self.extract_time_features(df)
        df = self.extract_weather_features(df)
        df = self.extract_traffic_features(df)
        df = self.extract_courier_features(df)
        df = self.extract_spatial_features(df)
        
        if is_training:
            df = self.extract_historical_features(df)
        
        return df
    
    def get_feature_columns(self):
        return [
            'distance_km',
            'hour', 'day_of_week', 'is_weekend',
            'hour_sin', 'hour_cos', 'day_sin', 'day_cos',
            'is_rush_hour',
            'weather_encoded', 'weather_severity', 'is_rain', 'is_snow', 'is_bad_weather',
            'traffic_encoded', 'traffic_factor',
            'courier_avg_speed', 'courier_reliability', 'courier_experience', 'courier_on_time_rate',
            'speed_distance_ratio', 'courier_efficiency', 'workload_score',
            'pickup_to_center', 'dropoff_to_center',
            'lat_diff', 'lon_diff', 'direction'
        ]

def prepare_training_data(df):
    engineer = FeatureEngineer()
    df_processed = engineer.engineer_features(df, is_training=True)
    
    feature_cols = engineer.get_feature_columns() + [
        'courier_avg_time', 'courier_std_time',
        'courier_avg_distance', 'courier_ot_rate', 
        'expected_time_by_distance',
        'recency_bias', 'recent_perf_trend'
    ]
    
    X = df_processed[feature_cols]
    y = df_processed['actual_delivery_minutes']
    
    return X, y, feature_cols, engineer

if __name__ == '__main__':
    from data_generator import generate_historical_data
    
    print('生成测试数据...')
    df = generate_historical_data(1000)
    
    print('特征工程处理...')
    X, y, feature_cols, engineer = prepare_training_data(df)
    
    print(f'特征数量: {len(feature_cols)}')
    print(f'样本数量: {len(X)}')
    print('特征列:', feature_cols[:5], '...')
