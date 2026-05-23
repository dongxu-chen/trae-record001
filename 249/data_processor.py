import pandas as pd
import numpy as np
import holidays
from datetime import datetime, timedelta
from config import STATIONS, WEATHER_TYPES


class DataProcessor:
    def __init__(self):
        self.cn_holidays = holidays.CN()

    def generate_sample_data(self, start_date, days=30):
        dates = pd.date_range(start=start_date, periods=days*24, freq='h')
        data = []
        
        for station in STATIONS:
            for dt in dates:
                hour = dt.hour
                weekday = dt.weekday()
                is_holiday = dt in self.cn_holidays
                
                base_flow = 200
                
                if 7 <= hour <= 9:
                    base_flow *= 3
                elif 17 <= hour <= 19:
                    base_flow *= 2.5
                elif 0 <= hour <= 5:
                    base_flow *= 0.1
                
                if weekday >= 5 or is_holiday:
                    base_flow *= 0.7
                
                in_flow = int(np.random.normal(base_flow, base_flow * 0.1))
                out_flow = int(np.random.normal(base_flow * 0.95, base_flow * 0.1))
                
                in_flow = max(0, in_flow)
                out_flow = max(0, out_flow)
                
                data.append({
                    'timestamp': dt,
                    'station': station,
                    'in_flow': in_flow,
                    'out_flow': out_flow,
                    'hour': hour,
                    'weekday': weekday,
                    'is_holiday': is_holiday
                })
        
        return pd.DataFrame(data)

    def generate_weather_data(self, start_date, days=30):
        dates = pd.date_range(start=start_date, periods=days*24, freq='h')
        weather_data = []
        
        current_weather = np.random.choice(WEATHER_TYPES)
        weather_streak = 0
        
        for dt in dates:
            weather_streak += 1
            if weather_streak > np.random.randint(3, 8):
                current_weather = np.random.choice(WEATHER_TYPES)
                weather_streak = 0
            
            temp = 15 + 10 * np.sin((dt.month - 1) * np.pi / 6)
            temp += np.random.normal(0, 3)
            
            weather_data.append({
                'timestamp': dt,
                'weather': current_weather,
                'temperature': round(temp, 1),
                'weather_code': WEATHER_TYPES.index(current_weather)
            })
        
        return pd.DataFrame(weather_data)

    def generate_od_matrix(self, date_time, top_n=None):
        n = len(STATIONS)
        od_matrix = np.zeros((n, n), dtype=int)
        
        hour = date_time.hour
        is_peak = (7 <= hour <= 9) or (17 <= hour <= 19)
        
        for i in range(n):
            for j in range(n):
                if i != j:
                    base = 20 if is_peak else 8
                    distance_factor = 1 + abs(i - j) * 0.05
                    od_matrix[i, j] = int(np.random.normal(base * distance_factor, base * 0.3))
        
        if top_n is not None:
            return self._get_top_routes(od_matrix, top_n)
        
        return od_matrix

    def _get_top_routes(self, od_matrix, top_n):
        n = od_matrix.shape[0]
        routes = []
        
        for i in range(n):
            for j in range(n):
                if i != j:
                    routes.append({
                        'from_idx': i,
                        'to_idx': j,
                        'from_station': STATIONS[i],
                        'to_station': STATIONS[j],
                        'flow': int(od_matrix[i, j])
                    })
        
        routes.sort(key=lambda x: x['flow'], reverse=True)
        top_routes = routes[:top_n]
        
        top_matrix = np.zeros((n, n), dtype=int)
        for route in top_routes:
            top_matrix[route['from_idx'], route['to_idx']] = route['flow']
        
        return {
            'full_matrix': od_matrix.tolist(),
            'top_matrix': top_matrix.tolist(),
            'top_routes': top_routes
        }

    def add_time_features(self, df):
        df = df.copy()
        df['hour_sin'] = np.sin(df['hour'] * 2 * np.pi / 24)
        df['hour_cos'] = np.cos(df['hour'] * 2 * np.pi / 24)
        df['weekday_sin'] = np.sin(df['weekday'] * 2 * np.pi / 7)
        df['weekday_cos'] = np.cos(df['weekday'] * 2 * np.pi / 7)
        return df

    def merge_weather_data(self, flow_df, weather_df):
        return pd.merge(flow_df, weather_df, on='timestamp', how='left')

    def prepare_prophet_data(self, df, station, flow_type='in_flow'):
        station_df = df[df['station'] == station].copy()
        prophet_df = station_df[['timestamp', flow_type]].rename(
            columns={'timestamp': 'ds', flow_type: 'y'}
        )
        return prophet_df

    def prepare_gbdt_features(self, df):
        features = ['hour', 'weekday', 'is_holiday', 'weather_code', 'temperature',
                   'hour_sin', 'hour_cos', 'weekday_sin', 'weekday_cos']
        return df[features].values

    def get_date_type(self, dt):
        if dt in self.cn_holidays:
            return '节假日'
        elif dt.weekday() >= 5:
            return '周末'
        else:
            return '工作日'
