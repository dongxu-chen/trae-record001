import pandas as pd
import numpy as np
from sklearn.preprocessing import StandardScaler, LabelEncoder
from geopy.distance import geodesic
import joblib
import os

class FeatureEngineer:
    def __init__(self):
        self.label_encoders = {}
        self.scaler = StandardScaler()
        self.fitted = False
        
    def calculate_distance(self, lat1, lon1, lat2, lon2):
        return geodesic((lat1, lon1), (lat2, lon2)).kilometers
    
    def encode_categorical(self, df, columns):
        for col in columns:
            if col not in self.label_encoders:
                self.label_encoders[col] = LabelEncoder()
                df[col + '_encoded'] = self.label_encoders[col].fit_transform(df[col])
            else:
                df[col + '_encoded'] = self.label_encoders[col].transform(df[col])
        return df
    
    def extract_time_features(self, df, time_col):
        df[time_col] = pd.to_datetime(df[time_col])
        df['hour'] = df[time_col].dt.hour
        df['day_of_week'] = df[time_col].dt.dayofweek
        df['is_weekend'] = (df['day_of_week'] >= 5).astype(int)
        df['is_peak_hour'] = df['hour'].apply(
            lambda x: 1 if (11 <= x <= 13) or (17 <= x <= 19) else 0
        )
        
        df['time_of_day'] = pd.cut(df['hour'], 
                                   bins=[0, 6, 11, 14, 17, 20, 24],
                                   labels=['凌晨', '早晨', '午间', '下午', '晚间', '夜间'],
                                   include_lowest=True)
        return df
    
    def create_interaction_features(self, df):
        df['distance_x_weather'] = df['distance_km'] * df['weather_impact']
        df['distance_x_traffic'] = df['distance_km'] * df['traffic_impact']
        df['prep_x_peak'] = df['prep_time_min'] * df['is_peak_hour']
        df['elevator_x_floor'] = df['elevator_wait_min'] * df['floor']
        
        if 'is_office_building' in df.columns:
            df['office_x_floor'] = df['is_office_building'] * df['floor']
            df['office_x_elevator'] = df['is_office_building'] * (1 - df['has_elevator'].astype(int))
        else:
            df['office_x_floor'] = 0
            df['office_x_elevator'] = 0
        
        if 'restaurant_on_time_rate' in df.columns:
            df['prep_x_on_time_rate'] = df['prep_time_min'] * (1 - df['restaurant_on_time_rate'])
            df['on_time_x_peak'] = df['restaurant_on_time_rate'] * df['is_peak_hour']
        else:
            df['prep_x_on_time_rate'] = 0
            df['on_time_x_peak'] = 0
        
        if 'is_new_restaurant' in df.columns:
            df['new_rest_x_prep'] = df['is_new_restaurant'] * df['prep_time_min']
        else:
            df['new_rest_x_prep'] = 0
        
        complexity_components = [
            df['weather_impact'],
            df['traffic_impact'],
            df['is_peak_hour'] * 0.3,
            (1 - df['has_elevator'].astype(int)) * 0.2
        ]
        
        if 'is_office_building' in df.columns:
            complexity_components.append(df['is_office_building'] * 0.15)
        if 'is_new_restaurant' in df.columns:
            complexity_components.append(df['is_new_restaurant'] * 0.2)
        if 'restaurant_on_time_rate' in df.columns:
            complexity_components.append((1 - df['restaurant_on_time_rate']) * 0.25)
        
        df['complexity_score'] = sum(complexity_components)
        return df
    
    def transform(self, df, is_training=True):
        df = df.copy()
        
        if 'order_time' in df.columns:
            df = self.extract_time_features(df, 'order_time')
        
        if 'food_type' in df.columns:
            df = self.encode_categorical(df, ['food_type'])
        
        if 'weather_condition' in df.columns:
            df = self.encode_categorical(df, ['weather_condition'])
        
        if 'time_of_day' in df.columns:
            df = self.encode_categorical(df, ['time_of_day'])
        
        df = self.create_interaction_features(df)
        
        feature_cols = [
            'distance_km',
            'distance_rest_to_user_km',
            'distance_rider_to_rest_km',
            'prep_time_min',
            'elevator_wait_min',
            'floor',
            'has_elevator',
            'weather_impact',
            'traffic_impact',
            'traffic_index',
            'order_hour',
            'is_weekend',
            'is_peak_hour',
            'rider_avg_speed',
            'rider_experience_months',
            'rider_rating',
            'food_type_encoded',
            'weather_condition_encoded',
            'time_of_day_encoded',
            'distance_x_weather',
            'distance_x_traffic',
            'prep_x_peak',
            'elevator_x_floor',
            'office_x_floor',
            'office_x_elevator',
            'prep_x_on_time_rate',
            'on_time_x_peak',
            'new_rest_x_prep',
            'complexity_score'
        ]
        
        extra_optional_cols = ['is_new_restaurant', 'restaurant_on_time_rate', 
                                'restaurant_total_orders', 'is_office_building']
        for col in extra_optional_cols:
            if col in df.columns:
                feature_cols.append(col)
        
        available_cols = [col for col in feature_cols if col in df.columns]
        
        if is_training:
            self.feature_names = available_cols
            self.fitted = True
        
        return df[available_cols]
    
    def save(self, path):
        joblib.dump({
            'label_encoders': self.label_encoders,
            'scaler': self.scaler,
            'feature_names': self.feature_names,
            'fitted': self.fitted
        }, path)
    
    @classmethod
    def load(cls, path):
        fe = cls()
        data = joblib.load(path)
        fe.label_encoders = data['label_encoders']
        fe.scaler = data['scaler']
        fe.feature_names = data['feature_names']
        fe.fitted = data['fitted']
        return fe

def prepare_training_data(orders_df):
    fe = FeatureEngineer()
    X = fe.transform(orders_df, is_training=True)
    y = orders_df['delivery_time_min']
    
    return X, y, fe

if __name__ == '__main__':
    os.makedirs('data', exist_ok=True)
    os.makedirs('models', exist_ok=True)
    
    if os.path.exists('data/orders.csv'):
        orders = pd.read_csv('data/orders.csv')
        X, y, fe = prepare_training_data(orders)
        print(f"特征数量: {len(fe.feature_names)}")
        print(f"特征名: {fe.feature_names}")
        print(f"训练数据形状: {X.shape}")
        
        fe.save('models/feature_engineer.pkl')
        print("特征工程模型已保存")
    else:
        print("请先生成数据")
