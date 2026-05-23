import pandas as pd
import numpy as np
import lightgbm as lgb
from datetime import datetime, timedelta
import pickle
import os
import math
from concurrent.futures import ThreadPoolExecutor, as_completed
import holidays

class AdaptiveGrid:
    def __init__(self, center_lat=39.9042, center_lng=116.4074, 
                 min_lat=39.8, max_lat=40.1, min_lng=116.2, max_lng=116.6):
        self.center_lat = center_lat
        self.center_lng = center_lng
        self.min_lat = min_lat
        self.max_lat = max_lat
        self.min_lng = min_lng
        self.max_lng = max_lng
        self.zones = []
        self.zone_lookup = {}
        
    def calculate_zone_key(self, level, i, j):
        return f"L{level}_{i}_{j}"
    
    def distance_to_center(self, lat, lng):
        return math.sqrt((lat - self.center_lat)**2 + (lng - self.center_lng)**2)
    
    def generate_adaptive_zones(self):
        self.zones = []
        
        level_0_size = 0.08
        level_1_size = 0.04
        level_2_size = 0.02
        
        center_radius_0 = 0.04
        center_radius_1 = 0.12
        
        level_0_i_start = int((self.center_lat - center_radius_0 - self.min_lat) / level_0_size)
        level_0_i_end = int((self.center_lat + center_radius_0 - self.min_lat) / level_0_size)
        level_0_j_start = int((self.center_lng - center_radius_0 - self.min_lng) / level_0_size)
        level_0_j_end = int((self.center_lng + center_radius_0 - self.min_lng) / level_0_size)
        
        for i in range(max(0, level_0_i_start), level_0_i_end + 1):
            for j in range(max(0, level_0_j_start), level_0_j_end + 1):
                zone_lat_min = self.min_lat + i * level_2_size
                zone_lng_min = self.min_lng + j * level_2_size
                if zone_lat_min + level_2_size < self.max_lat and \
                   zone_lng_min + level_2_size < self.max_lng:
                    zone = {
                        'key': self.calculate_zone_key(2, i, j),
                        'level': 2,
                        'size': level_2_size,
                        'lat_min': zone_lat_min,
                        'lat_max': zone_lat_min + level_2_size,
                        'lng_min': zone_lng_min,
                        'lng_max': zone_lng_min + level_2_size,
                        'center_lat': zone_lat_min + level_2_size / 2,
                        'center_lng': zone_lng_min + level_2_size / 2
                    }
                    self.zones.append(zone)
        
        level_1_i_start = int((self.center_lat - center_radius_1 - self.min_lat) / level_1_size)
        level_1_i_end = int((self.center_lat + center_radius_1 - self.min_lat) / level_1_size)
        level_1_j_start = int((self.center_lng - center_radius_1 - self.min_lng) / level_1_size)
        level_1_j_end = int((self.center_lng + center_radius_1 - self.min_lng) / level_1_size)
        
        for i in range(max(0, level_1_i_start), level_1_i_end + 1):
            for j in range(max(0, level_1_j_start), level_1_j_end + 1):
                zone_lat_min = self.min_lat + i * level_1_size
                zone_lng_min = self.min_lng + j * level_1_size
                zone_lat_max = zone_lat_min + level_1_size
                zone_lng_max = zone_lng_min + level_1_size
                
                dist = self.distance_to_center(
                    (zone_lat_min + zone_lat_max) / 2,
                    (zone_lng_min + zone_lng_max) / 2
                )
                
                if dist > center_radius_0:
                    zone = {
                        'key': self.calculate_zone_key(1, i, j),
                        'level': 1,
                        'size': level_1_size,
                        'lat_min': zone_lat_min,
                        'lat_max': zone_lat_max,
                        'lng_min': zone_lng_min,
                        'lng_max': zone_lng_max,
                        'center_lat': (zone_lat_min + zone_lat_max) / 2,
                        'center_lng': (zone_lng_min + zone_lng_max) / 2
                    }
                    self.zones.append(zone)
        
        coarse_size = level_0_size
        n_i = int((self.max_lat - self.min_lat) / coarse_size)
        n_j = int((self.max_lng - self.min_lng) / coarse_size)
        
        for i in range(n_i + 1):
            for j in range(n_j + 1):
                zone_lat_min = self.min_lat + i * coarse_size
                zone_lng_min = self.min_lng + j * coarse_size
                zone_lat_max = min(zone_lat_min + coarse_size, self.max_lat)
                zone_lng_max = min(zone_lng_min + coarse_size, self.max_lng)
                
                dist = self.distance_to_center(
                    (zone_lat_min + zone_lat_max) / 2,
                    (zone_lng_min + zone_lng_max) / 2
                )
                
                if dist > center_radius_1:
                    zone = {
                        'key': self.calculate_zone_key(0, i, j),
                        'level': 0,
                        'size': coarse_size,
                        'lat_min': zone_lat_min,
                        'lat_max': zone_lat_max,
                        'lng_min': zone_lng_min,
                        'lng_max': zone_lng_max,
                        'center_lat': (zone_lat_min + zone_lat_max) / 2,
                        'center_lng': (zone_lng_min + zone_lng_max) / 2
                    }
                    self.zones.append(zone)
        
        print(f"生成自适应网格: {len(self.zones)} 个区域")
        print(f"  - Level 2 (最细): {len([z for z in self.zones if z['level']==2])} 区")
        print(f"  - Level 1 (中等): {len([z for z in self.zones if z['level']==1])} 区")
        print(f"  - Level 0 (最粗): {len([z for z in self.zones if z['level']==0])} 区")
        
        return self.zones
    
    def find_zone(self, lat, lng):
        for zone in self.zones:
            if zone['lat_min'] <= lat < zone['lat_max'] and \
               zone['lng_min'] <= lng < zone['lng_max']:
                return zone
        return None
    
    def get_all_zones(self):
        return self.zones

class DemandPredictor:
    def __init__(self):
        self.grid = AdaptiveGrid()
        self.grid.generate_adaptive_zones()
        self.models = {}
        self.model_stats = {}
        self.cn_holidays = holidays.CN()
        
    def is_holiday(self, date):
        if isinstance(date, pd.Timestamp):
            date = date.to_pydatetime().date()
        elif isinstance(date, datetime):
            date = date.date()
        return date in self.cn_holidays
    
    def get_holiday_adjustment_factor(self, date):
        if not self.is_holiday(date):
            return 1.0
        
        if isinstance(date, pd.Timestamp):
            hour = date.hour
        elif isinstance(date, datetime):
            hour = date.hour
        else:
            hour = 12
        
        if 9 <= hour <= 11 or 14 <= hour <= 18:
            return 1.5
        elif 11 < hour < 14:
            return 1.3
        else:
            return 0.8
    
    def extract_features(self, timestamps):
        if not isinstance(timestamps, pd.DatetimeIndex):
            timestamps = pd.to_datetime(timestamps)
        
        is_holiday_arr = [self.is_holiday(ts) for ts in timestamps]
        
        features = pd.DataFrame({
            'hour': timestamps.hour,
            'day_of_week': timestamps.dayofweek,
            'day_of_month': timestamps.day,
            'month': timestamps.month,
            'is_weekend': (timestamps.dayofweek >= 5).astype(int),
            'is_holiday': is_holiday_arr,
            'is_rush_hour_morning': timestamps.hour.isin([7, 8, 9]).astype(int),
            'is_rush_hour_evening': timestamps.hour.isin([17, 18, 19]).astype(int),
            'hour_sin': np.sin(2 * np.pi * timestamps.hour / 24),
            'hour_cos': np.cos(2 * np.pi * timestamps.hour / 24),
            'dow_sin': np.sin(2 * np.pi * timestamps.dayofweek / 7),
            'dow_cos': np.cos(2 * np.pi * timestamps.dayofweek / 7),
        })
        
        return features.values
    
    def prepare_training_data(self, df):
        df['datetime'] = pd.to_datetime(df['timestamp'])
        
        zone_data = {}
        for _, row in df.iterrows():
            zone = self.grid.find_zone(row['lat'], row['lng'])
            if zone:
                zone_key = zone['key']
                if zone_key not in zone_data:
                    zone_data[zone_key] = {'zone': zone, 'data': []
                zone_data[zone_key]['data'].append({
                    'datetime': row['datetime'],
                    'order_count': row['order_count']
                })
        
        prepared_data = {}
        for zone_key, zd in zone_data.items():
            zone_df = pd.DataFrame(zd['data'])
            if len(zone_df) < 24:
                continue
                
            zone_df = zone_df.set_index('datetime').resample('1H').sum().reset_index()
            zone_df = zone_df.fillna(0)
            
            features = self.extract_features(zone_df['datetime'])
            targets = zone_df['order_count'].values
            
            prepared_data[zone_key] = {
                'zone': zd['zone'],
                'X': features,
                'y': targets,
                'timestamps': zone_df['datetime']
            }
        
        return prepared_data
    
    def train_single_model(self, zone_key, data):
        X = data['X']
        y = data['y']
        
        params = {
            'objective': 'regression',
            'metric': 'rmse',
            'boosting_type': 'gbdt',
            'num_leaves': 15,
            'learning_rate': 0.08,
            'feature_fraction': 0.8,
            'bagging_fraction': 0.8,
            'bagging_freq': 5,
            'verbose': -1,
            'min_data_in_leaf': 5,
            'max_depth': 5,
            'n_estimators': 50
        }
        
        train_size = int(len(X) * 0.8)
        X_train, y_train = X[:train_size], y[:train_size]
        X_val, y_val = X[train_size:], y[train_size:]
        
        model = lgb.LGBMRegressor(**params)
        model.fit(
            X_train, y_train,
            eval_set=[(X_val, y_val)],
            callbacks=[lgb.early_stopping(stopping_rounds=10, verbose=False)]
        )
        
        return zone_key, model, data['zone']
    
    def train_models(self, df):
        zone_data = self.prepare_training_data(df)
        print(f"准备训练 {len(zone_data)} 个区域的模型")
        
        trained_count = 0
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = []
            for zone_key, data in zone_data.items():
                futures.append(executor.submit(
                    self.train_single_model, zone_key, data
                ))
            
            for future in as_completed(futures):
                zone_key, model, zone = future.result()
                self.models[zone_key] = model
                self.model_stats[zone_key] = zone
                trained_count += 1
                
                if trained_count % 10 == 0:
                    print(f"已训练 {trained_count}/{len(zone_data)} 个模型")
        
        print(f"训练完成: {len(self.models)} 个区域模型")
        
    def predict_zone(self, zone_key, future_dates):
        if zone_key not in self.models:
            return None
        
        model = self.models[zone_key]
        features = self.extract_features(future_dates)
        predictions = model.predict(features)
        
        adjusted_preds = []
        for i, pred in enumerate(predictions):
            adjust_factor = self.get_holiday_adjustment_factor(future_dates[i])
            adjusted_preds.append(pred * adjust_factor)
        
        return np.maximum(0, np.array(adjusted_preds))
    
    def predict_next_hour(self):
        now = datetime.now()
        future_dates = pd.DatetimeIndex([now + timedelta(hours=i) for i in range(1, 2)])
        
        is_holiday = self.is_holiday(future_dates[0])
        holiday_name = self.cn_holidays.get(future_dates[0].date()) if is_holiday else None
        
        predictions = []
        for zone_key, zone in self.model_stats.items():
            pred = self.predict_zone(zone_key, future_dates)
            if pred is not None:
                demand = pred[0]
                
                if demand < 5:
                    level = 'low'
                elif demand < 15:
                    level = 'medium'
                else:
                    level = 'high'
                
                predictions.append({
                    'zone': zone_key,
                    'lat': zone['center_lat'],
                    'lng': zone['center_lng'],
                    'grid_level': zone['level'],
                    'demand': float(demand),
                    'demand_level': level,
                    'timestamp': future_dates[0].isoformat(),
                    'is_holiday': is_holiday,
                    'holiday_name': holiday_name
                })
        
        return predictions
    
    def predict_hours(self, hours=12):
        now = datetime.now()
        future_dates = pd.DatetimeIndex([now + timedelta(hours=i) for i in range(1, hours + 1)])
        
        all_predictions = []
        for zone_key, zone in self.model_stats.items():
            preds = self.predict_zone(zone_key, future_dates)
            if preds is not None:
                for i, demand in enumerate(preds):
                    if demand < 5:
                        level = 'low'
                    elif demand < 15:
                        level = 'medium'
                    else:
                        level = 'high'
                    
                    is_holiday = self.is_holiday(future_dates[i])
                    holiday_name = self.cn_holidays.get(future_dates[i].date()) if is_holiday else None
                    
                    all_predictions.append({
                        'zone': zone_key,
                        'lat': zone['center_lat'],
                        'lng': zone['center_lng'],
                        'grid_level': zone['level'],
                        'demand': float(demand),
                        'demand_level': level,
                        'timestamp': future_dates[i].isoformat(),
                        'is_holiday': is_holiday,
                        'holiday_name': holiday_name
                    })
        
        return all_predictions
    
    def save_models(self, path='models.pkl'):
        save_data = {
            'models': self.models,
            'model_stats': self.model_stats,
            'grid_zones': self.grid.zones
        }
        with open(path, 'wb') as f:
            pickle.dump(save_data, f, protocol=pickle.HIGHEST_PROTOCOL)
        
        model_size = os.path.getsize(path) / 1024
        print(f"模型已保存，大小: {model_size:.2f} KB")
    
    def load_models(self, path='models.pkl'):
        if os.path.exists(path):
            with open(path, 'rb') as f:
                data = pickle.load(f)
                self.models = data['models']
                self.model_stats = data['model_stats']
                if 'grid_zones' in data:
                    self.grid.zones = data['grid_zones']
            
            model_size = os.path.getsize(path) / 1024
            print(f"已加载 {len(self.models)} 个模型，大小: {model_size:.2f} KB")
            return True
        return False
    
    def get_grid_bounds(self):
        return {
            'min_lat': self.grid.min_lat,
            'max_lat': self.grid.max_lat,
            'min_lng': self.grid.min_lng,
            'max_lng': self.grid.max_lng,
            'center_lat': self.grid.center_lat,
            'center_lng': self.grid.center_lng
        }
