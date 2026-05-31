import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from collections import defaultdict
import warnings
warnings.filterwarnings('ignore')

class TimeSeriesForecaster:
    def __init__(self, window_size=7):
        self.window_size = window_size
        self.historical_data = None
        self.hourly_patterns = defaultdict(list)
        self.daily_patterns = defaultdict(list)
        
    def fit(self, orders_df):
        orders_df = orders_df.copy()
        orders_df['order_time'] = pd.to_datetime(orders_df['order_time'])
        orders_df['date'] = orders_df['order_time'].dt.date
        orders_df['hour'] = orders_df['order_time'].dt.hour
        orders_df['day_of_week'] = orders_df['order_time'].dt.dayofweek
        
        self.historical_data = orders_df
        
        hourly_stats = orders_df.groupby(['day_of_week', 'hour']).agg({
            'delivery_time_min': ['mean', 'std', 'count'],
            'order_id': 'count'
        }).reset_index()
        hourly_stats.columns = ['day_of_week', 'hour', 'avg_delivery', 'std_delivery', 'count', 'order_count']
        self.hourly_stats = hourly_stats
        
        for (dow, hour), group in orders_df.groupby(['day_of_week', 'hour']):
            self.hourly_patterns[(dow, hour)] = group['delivery_time_min'].values
        
        return self
    
    def predict_hourly_demand(self, target_date, hours_ahead=24):
        predictions = []
        base_time = pd.to_datetime(target_date)
        
        for i in range(hours_ahead):
            forecast_time = base_time + timedelta(hours=i)
            dow = forecast_time.dayofweek
            hour = forecast_time.hour
            
            mask = (self.hourly_stats['day_of_week'] == dow) & (self.hourly_stats['hour'] == hour)
            stats = self.hourly_stats[mask]
            
            if len(stats) > 0:
                avg_delivery = stats['avg_delivery'].values[0]
                std_delivery = stats['std_delivery'].values[0]
                order_count = stats['order_count'].values[0]
                
                hour_factor = 1.0
                if 11 <= hour <= 13 or 17 <= hour <= 19:
                    hour_factor = 1.2
                
                is_weekend = 1 if dow >= 5 else 0
                if is_weekend:
                    order_count *= 1.15
                
                predictions.append({
                    'timestamp': forecast_time,
                    'hour': hour,
                    'day_of_week': dow,
                    'is_weekend': is_weekend,
                    'predicted_orders': int(order_count * hour_factor),
                    'avg_delivery_time': round(avg_delivery * hour_factor, 1),
                    'delivery_std': round(std_delivery, 1)
                })
            else:
                predictions.append({
                    'timestamp': forecast_time,
                    'hour': hour,
                    'day_of_week': dow,
                    'is_weekend': 1 if dow >= 5 else 0,
                    'predicted_orders': 20,
                    'avg_delivery_time': 35.0,
                    'delivery_std': 8.0
                })
        
        return pd.DataFrame(predictions)
    
    def predict_delivery_time_trend(self, target_date, days=7):
        daily_predictions = []
        base_date = pd.to_datetime(target_date).date()
        
        for i in range(days):
            forecast_date = base_date + timedelta(days=i)
            dow = forecast_date.weekday()
            
            day_data = self.historical_data[
                self.historical_data['order_time'].dt.dayofweek == dow
            ]
            
            if len(day_data) > 0:
                avg_delivery = day_data['delivery_time_min'].mean()
                peak_hours_data = day_data[
                    (day_data['hour'] >= 11) & (day_data['hour'] <= 13) |
                    (day_data['hour'] >= 17) & (day_data['hour'] <= 19)
                ]
                peak_avg = peak_hours_data['delivery_time_min'].mean() if len(peak_hours_data) > 0 else avg_delivery * 1.2
                
                daily_predictions.append({
                    'date': forecast_date,
                    'day_of_week': dow,
                    'is_weekend': 1 if dow >= 5 else 0,
                    'avg_delivery_time': round(avg_delivery, 1),
                    'peak_delivery_time': round(peak_avg, 1),
                    'expected_orders': len(day_data)
                })
        
        return pd.DataFrame(daily_predictions)
    
    def calculate_anomaly_score(self, current_delivery_time, hour, day_of_week):
        mask = (self.hourly_stats['day_of_week'] == day_of_week) & (self.hourly_stats['hour'] == hour)
        stats = self.hourly_stats[mask]
        
        if len(stats) > 0:
            avg = stats['avg_delivery'].values[0]
            std = stats['std_delivery'].values[0]
            if std > 0:
                z_score = (current_delivery_time - avg) / std
                return z_score
        
        return 0
    
    def get_peak_hours(self, day_of_week=None):
        if day_of_week is not None:
            data = self.hourly_stats[self.hourly_stats['day_of_week'] == day_of_week]
        else:
            data = self.hourly_stats
        
        data = data.groupby('hour')['order_count'].mean().reset_index()
        data = data.sort_values('order_count', ascending=False)
        
        return data.head(5)

if __name__ == '__main__':
    import os
    
    if os.path.exists('data/orders.csv'):
        orders = pd.read_csv('data/orders.csv')
        forecaster = TimeSeriesForecaster()
        forecaster.fit(orders)
        
        target_date = datetime(2024, 1, 8)
        hourly_pred = forecaster.predict_hourly_demand(target_date, hours_ahead=12)
        print("未来12小时预测:")
        print(hourly_pred[['timestamp', 'predicted_orders', 'avg_delivery_time']])
        
        print("\n高峰时段:")
        print(forecaster.get_peak_hours(0))
    else:
        print("请先生成数据")
