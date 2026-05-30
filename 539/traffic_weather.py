import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import random

class TrafficAPIClient:
    def __init__(self):
        self.road_segments = self._init_road_segments()
    
    def _init_road_segments(self):
        return {
            '中心商业区': {'base_speed': 40, 'congestion_factor': 1.0},
            '东部工业区': {'base_speed': 50, 'congestion_factor': 0.9},
            '西部住宅区': {'base_speed': 35, 'congestion_factor': 1.1},
            '南部科技园区': {'base_speed': 45, 'congestion_factor': 0.95},
            '北部大学城': {'base_speed': 30, 'congestion_factor': 1.15},
            '环城快速路': {'base_speed': 60, 'congestion_factor': 0.8}
        }
    
    def get_hourly_traffic_pattern(self, hour, day_of_week):
        is_weekend = day_of_week >= 5
        
        if is_weekend:
            if 10 <= hour < 12 or 14 <= hour < 18:
                return 1.2
            elif 12 <= hour < 14:
                return 1.3
            else:
                return 1.0
        else:
            if 7 <= hour < 9 or 17 <= hour < 19:
                return 1.8
            elif 9 <= hour < 17:
                return 1.2
            else:
                return 0.9
    
    def get_real_time_traffic(self, pickup_lat, pickup_lon, dropoff_lat, dropoff_lon, 
                              current_time=None):
        if current_time is None:
            current_time = datetime.now()
        
        hour = current_time.hour
        day_of_week = current_time.weekday()
        
        hourly_factor = self.get_hourly_traffic_pattern(hour, day_of_week)
        
        random_factor = np.random.uniform(0.9, 1.1)
        
        distance_km = np.sqrt((dropoff_lat - pickup_lat)**2 + 
                              (dropoff_lon - pickup_lon)**2) * 111
        
        base_speed = 35
        if distance_km < 2:
            base_speed = 25
        elif distance_km > 10:
            base_speed = 45
        
        effective_speed = base_speed / (hourly_factor * random_factor)
        expected_time_minutes = (distance_km / effective_speed) * 60
        
        if hourly_factor > 1.5:
            condition = '严重拥堵'
        elif hourly_factor > 1.2:
            condition = '拥堵'
        elif hourly_factor > 1.0:
            condition = '缓行'
        else:
            condition = '畅通'
        
        avg_speed = effective_speed * np.random.uniform(0.8, 1.2)
        
        return {
            'traffic_condition': condition,
            'avg_speed_kmh': round(avg_speed, 1),
            'expected_travel_time_min': round(expected_time_minutes, 1),
            'congestion_level': round(hourly_factor, 2),
            'timestamp': current_time.strftime('%Y-%m-%d %H:%M:%S')
        }
    
    def get_route_traffic_segments(self, route_points, current_time=None):
        segments = []
        for i in range(len(route_points) - 1):
            start = route_points[i]
            end = route_points[i + 1]
            traffic_info = self.get_real_time_traffic(
                start[0], start[1], end[0], end[1], current_time
            )
            segments.append({
                'start': start,
                'end': end,
                **traffic_info
            })
        return segments

class WeatherAPIClient:
    def __init__(self):
        self.weather_types = ['晴', '多云', '小雨', '中雨', '大雨', '小雪', '中雪']
    
    def get_current_weather(self, lat, lon, current_time=None):
        if current_time is None:
            current_time = datetime.now()
        
        month = current_time.month
        
        if month in [12, 1, 2]:
            weather_probs = [0.4, 0.25, 0.15, 0.05, 0.02, 0.08, 0.05]
        elif month in [3, 4, 5]:
            weather_probs = [0.35, 0.25, 0.2, 0.12, 0.06, 0.01, 0.01]
        elif month in [6, 7, 8]:
            weather_probs = [0.3, 0.2, 0.25, 0.15, 0.09, 0.005, 0.005]
        else:
            weather_probs = [0.35, 0.25, 0.2, 0.12, 0.05, 0.02, 0.01]
        
        weather = np.random.choice(self.weather_types, p=weather_probs)
        
        base_temp = {
            1: 5, 2: 8, 3: 12, 4: 18, 5: 24, 6: 28,
            7: 32, 8: 31, 9: 27, 10: 21, 11: 14, 12: 7
        }[month]
        
        temperature = base_temp + np.random.uniform(-5, 5)
        
        humidity = np.random.uniform(40, 90)
        wind_speed = np.random.uniform(5, 30)
        
        visibility_impact = {
            '晴': 1.0, '多云': 0.95, '小雨': 0.8, '中雨': 0.6,
            '大雨': 0.4, '小雪': 0.7, '中雪': 0.5
        }[weather]
        
        return {
            'weather': weather,
            'temperature_c': round(temperature, 1),
            'humidity_pct': round(humidity, 1),
            'wind_speed_kmh': round(wind_speed, 1),
            'visibility_factor': visibility_impact,
            'timestamp': current_time.strftime('%Y-%m-%d %H:%M:%S')
        }
    
    def get_forecast(self, lat, lon, hours=24):
        forecasts = []
        current_time = datetime.now()
        
        for h in range(hours):
            forecast_time = current_time + timedelta(hours=h)
            weather_info = self.get_current_weather(lat, lon, forecast_time)
            weather_info['forecast_time'] = forecast_time.strftime('%Y-%m-%d %H:%M:%S')
            forecasts.append(weather_info)
        
        return forecasts

def get_environmental_features(pickup_lat, pickup_lon, dropoff_lat, dropoff_lon, current_time=None):
    traffic_client = TrafficAPIClient()
    weather_client = WeatherAPIClient()
    
    traffic_info = traffic_client.get_real_time_traffic(
        pickup_lat, pickup_lon, dropoff_lat, dropoff_lon, current_time
    )
    
    weather_info = weather_client.get_current_weather(pickup_lat, pickup_lon, current_time)
    
    return {
        **traffic_info,
        **weather_info
    }

class DeliveryMonitor:
    def __init__(self):
        self.active_deliveries = {}
    
    def start_delivery(self, delivery_id, eta_prediction, order_time):
        self.active_deliveries[delivery_id] = {
            'eta_prediction': eta_prediction,
            'order_time': order_time,
            'checkpoints': [],
            'status': 'in_progress',
            'delay_warning': False,
            'delay_minutes': 0
        }
    
    def update_checkpoint(self, delivery_id, current_time, current_location, progress_pct):
        if delivery_id not in self.active_deliveries:
            return
        
        delivery = self.active_deliveries[delivery_id]
        elapsed_minutes = (current_time - delivery['order_time']).total_seconds() / 60
        
        expected_elapsed = delivery['eta_prediction'] * (progress_pct / 100)
        time_diff = elapsed_minutes - expected_elapsed
        
        if time_diff > 5 and progress_pct < 80:
            delivery['delay_warning'] = True
            delivery['delay_minutes'] = max(delivery['delay_minutes'], time_diff)
        
        delivery['checkpoints'].append({
            'time': current_time,
            'location': current_location,
            'progress_pct': progress_pct,
            'elapsed_minutes': elapsed_minutes,
            'expected_elapsed': expected_elapsed,
            'time_diff': time_diff
        })
        
        return delivery

if __name__ == '__main__':
    print('测试路况API...')
    traffic_client = TrafficAPIClient()
    traffic_info = traffic_client.get_real_time_traffic(
        31.2304, 121.4737, 31.2400, 121.5000
    )
    print('路况信息:', traffic_info)
    
    print('\n测试天气API...')
    weather_client = WeatherAPIClient()
    weather_info = weather_client.get_current_weather(31.2304, 121.4737)
    print('天气信息:', weather_info)
