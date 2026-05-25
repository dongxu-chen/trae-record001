import os
import pickle
import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from typing import Dict, Optional, Tuple
from datetime import datetime
from config import Config


class XGBoostPredictor:
    def __init__(self):
        self.model = None
        self.scaler = None
        self.route_encoder = LabelEncoder()
        self.feature_columns = [
            'route_encoded', 'current_station_idx', 'distance_to_next',
            'traffic_level', 'hour', 'day_of_week', 'speed', 'dwell_time',
            'is_peak_hour', 'distance_speed_ratio',
            'stop_light_density', 'stop_light_wait_estimate',
            'traffic_stoplight_interaction',
            'passenger_load_factor', 'boarding_count', 'alighting_count',
            'passenger_traffic_interaction'
        ]
        self._load_or_train_model()
    
    def _load_or_train_model(self):
        model_dir = os.path.dirname(Config.MODEL_PATH)
        if not os.path.exists(model_dir):
            os.makedirs(model_dir)
        
        if os.path.exists(Config.MODEL_PATH) and os.path.exists(Config.SCALER_PATH):
            self._load_model()
        else:
            self._train_model()
    
    def _load_model(self):
        try:
            self.model = xgb.XGBRegressor()
            self.model.load_model(Config.MODEL_PATH)
            
            with open(Config.SCALER_PATH, 'rb') as f:
                data = pickle.load(f)
                self.scaler = data['scaler']
                self.route_encoder = data['route_encoder']
            
            print(f"模型已加载: {Config.MODEL_PATH}")
        except Exception as e:
            print(f"加载模型失败，重新训练: {e}")
            self._train_model()
    
    def _train_model(self):
        print("开始训练XGBoost模型...")
        
        from data.data_generator import DataGenerator
        generator = DataGenerator()
        training_data = generator.generate_training_data(15000)
        
        df = pd.DataFrame(training_data)
        
        df['route_encoded'] = self.route_encoder.fit_transform(df['route_id'])
        df['is_peak_hour'] = df['hour'].apply(lambda x: 1 if (7 <= x <= 9 or 17 <= x <= 19) else 0)
        df['distance_speed_ratio'] = df['distance_to_next'] / (df['speed'] + 1)
        
        df['stop_light_density'] = df['distance_to_next'].apply(
            lambda x: np.random.choice([0.5, 1.0, 1.5, 2.0, 2.5, 3.0], 
                                      p=[0.1, 0.2, 0.3, 0.25, 0.1, 0.05])
        )
        
        df['stop_light_wait_estimate'] = df.apply(
            lambda row: row['stop_light_density'] * np.random.uniform(15, 45) * (1 + row['traffic_level'] * 0.2),
            axis=1
        )
        
        df['traffic_stoplight_interaction'] = df['traffic_level'] * df['stop_light_density']
        
        df['passenger_load_factor'] = np.random.uniform(0.3, 0.95, size=len(df))
        df['boarding_count'] = np.random.randint(5, 25, size=len(df))
        df['alighting_count'] = np.random.randint(3, 20, size=len(df))
        
        df['passenger_traffic_interaction'] = df['passenger_load_factor'] * df['traffic_level']
        
        df['dwell_time'] = df.apply(
            lambda row: 10 + (row['boarding_count'] + row['alighting_count']) * 1.5 + 
                       row['passenger_load_factor'] * 10 + row['traffic_level'] * 3,
            axis=1
        )
        
        df['arrival_seconds'] = df.apply(
            lambda row: row['arrival_seconds'] + row['stop_light_wait_estimate'] * 0.3 +
                       row['passenger_load_factor'] * 15,
            axis=1
        )
        
        X = df[self.feature_columns]
        y = df['arrival_seconds']
        
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42
        )
        
        self.scaler = StandardScaler()
        X_train_scaled = self.scaler.fit_transform(X_train)
        X_test_scaled = self.scaler.transform(X_test)
        
        self.model = xgb.XGBRegressor(
            objective='reg:squarederror',
            n_estimators=200,
            max_depth=8,
            learning_rate=0.1,
            subsample=0.8,
            colsample_bytree=0.8,
            random_state=42
        )
        
        self.model.fit(X_train_scaled, y_train)
        
        y_pred = self.model.predict(X_test_scaled)
        mae = mean_absolute_error(y_test, y_pred)
        rmse = np.sqrt(mean_squared_error(y_test, y_pred))
        r2 = r2_score(y_test, y_pred)
        
        print(f"模型训练完成:")
        print(f"  MAE: {mae:.2f} 秒")
        print(f"  RMSE: {rmse:.2f} 秒")
        print(f"  R²: {r2:.4f}")
        
        self.model.save_model(Config.MODEL_PATH)
        
        with open(Config.SCALER_PATH, 'wb') as f:
            pickle.dump({
                'scaler': self.scaler,
                'route_encoder': self.route_encoder
            }, f)
        
        print(f"模型已保存: {Config.MODEL_PATH}")
    
    def predict_arrival_time(self, 
                           route_id: str,
                           current_station_idx: int,
                           distance_to_next: float,
                           traffic_level: int,
                           speed: float,
                           dwell_time: float = 20.0,
                           stop_light_density: float = 1.0,
                           passenger_load_factor: float = 0.5,
                           boarding_count: int = 10,
                           alighting_count: int = 8) -> Tuple[float, float]:
        now = datetime.now()
        hour = now.hour
        day_of_week = now.weekday()
        is_peak_hour = 1 if (7 <= hour <= 9 or 17 <= hour <= 19) else 0
        distance_speed_ratio = distance_to_next / (speed + 1)
        
        stop_light_wait_estimate = stop_light_density * 30 * (1 + traffic_level * 0.2)
        traffic_stoplight_interaction = traffic_level * stop_light_density
        passenger_traffic_interaction = passenger_load_factor * traffic_level
        
        try:
            route_encoded = self.route_encoder.transform([route_id])[0]
        except ValueError:
            route_encoded = 0
        
        features = pd.DataFrame([{
            'route_encoded': route_encoded,
            'current_station_idx': current_station_idx,
            'distance_to_next': distance_to_next,
            'traffic_level': traffic_level,
            'hour': hour,
            'day_of_week': day_of_week,
            'speed': speed,
            'dwell_time': dwell_time,
            'is_peak_hour': is_peak_hour,
            'distance_speed_ratio': distance_speed_ratio,
            'stop_light_density': stop_light_density,
            'stop_light_wait_estimate': stop_light_wait_estimate,
            'traffic_stoplight_interaction': traffic_stoplight_interaction,
            'passenger_load_factor': passenger_load_factor,
            'boarding_count': boarding_count,
            'alighting_count': alighting_count,
            'passenger_traffic_interaction': passenger_traffic_interaction
        }])
        
        features = features[self.feature_columns]
        features_scaled = self.scaler.transform(features)
        
        predicted_seconds = float(self.model.predict(features_scaled)[0])
        
        base_prediction = distance_to_next / (speed * 1000 / 3600) if speed > 0 else 300
        confidence = max(0.5, 1.0 - abs(predicted_seconds - base_prediction) / base_prediction)
        confidence = min(1.0, confidence)
        
        return max(0, predicted_seconds), confidence
    
    def get_feature_importance(self) -> Dict[str, float]:
        if self.model is None:
            return {}
        
        importance = self.model.feature_importances_
        return {col: float(imp) for col, imp in zip(self.feature_columns, importance)}
