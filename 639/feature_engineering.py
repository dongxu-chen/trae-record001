import pandas as pd
import numpy as np
from sklearn.preprocessing import LabelEncoder, StandardScaler
import joblib


class FeatureEngineer:
    def __init__(self):
        self.label_encoders = {}
        self.scaler = None
        self.feature_names = []
        
    def create_time_series_features(self, df):
        df = df.copy()
        
        df['date'] = pd.to_datetime(df['date'])
        
        df['day_of_week'] = df['date'].dt.dayofweek
        df['day_of_month'] = df['date'].dt.day
        df['month'] = df['date'].dt.month
        df['quarter'] = df['date'].dt.quarter
        df['week_of_year'] = df['date'].dt.isocalendar().week.astype(int)
        
        df['is_morning'] = ((df['departure_hour'] >= 6) & (df['departure_hour'] < 12)).astype(int)
        df['is_afternoon'] = ((df['departure_hour'] >= 12) & (df['departure_hour'] < 18)).astype(int)
        df['is_evening'] = ((df['departure_hour'] >= 18) & (df['departure_hour'] < 24)).astype(int)
        df['is_peak_hour'] = (
            ((df['departure_hour'] >= 7) & (df['departure_hour'] <= 9)) |
            ((df['departure_hour'] >= 17) & (df['departure_hour'] <= 20))
        ).astype(int)
        
        df['departure_minute_of_day'] = df['departure_hour'] * 60 + df['departure_minute']
        
        df['is_weekend'] = df['is_weekend'].astype(int)
        df['is_peak_season'] = df['is_peak_season'].astype(int)
        
        df['is_business_day'] = ((df['day_of_week'] < 5) & (df['is_peak_season'] == 0)).astype(int)
        
        df['delay_trend'] = df['historical_delay_30d'] - df['historical_delay_7d']
        
        df['delay_ratio_7d_30d'] = df['historical_delay_7d'] / (df['historical_delay_30d'] + 1e-6)
        
        df['historical_delay_severity'] = pd.cut(
            df['historical_delay_30d'],
            bins=[-1, 15, 30, 60, 150],
            labels=[0, 1, 2, 3]
        ).astype(int)
        
        return df
    
    def encode_categorical_features(self, df, fit=True):
        df = df.copy()
        
        categorical_cols = [
            'airline', 'departure_airport', 'arrival_airport',
            'weather', 'flow_control'
        ]
        
        sector_cols = ['departure_sector', 'arrival_sector', 'departure_region', 'arrival_region']
        for col in sector_cols:
            if col not in df.columns:
                df[col] = '未知'
        categorical_cols.extend(sector_cols)
        
        for col in categorical_cols:
            if fit:
                le = LabelEncoder()
                df[f'{col}_encoded'] = le.fit_transform(df[col].astype(str))
                self.label_encoders[col] = le
            else:
                le = self.label_encoders.get(col)
                if le:
                    df[f'{col}_encoded'] = df[col].astype(str).apply(
                        lambda x: le.transform([x])[0] if x in le.classes_ else -1
                    )
                else:
                    df[f'{col}_encoded'] = -1
        
        df['route'] = df['departure_airport'] + '_' + df['arrival_airport']
        if fit:
            le_route = LabelEncoder()
            df['route_encoded'] = le_route.fit_transform(df['route'])
            self.label_encoders['route'] = le_route
        else:
            le_route = self.label_encoders['route']
            df['route_encoded'] = df['route'].apply(
                lambda x: le_route.transform([x])[0] if x in le_route.classes_ else -1
            )
        
        weather_map = {
            '晴朗': 0, '多云': 1, '小雨': 2, '中雨': 3,
            '雷暴': 4, '大雾': 5, '大雪': 6
        }
        df['weather_severity'] = df['weather'].map(weather_map).fillna(0)
        
        flow_map = {'无': 0, '轻度': 1, '中度': 2, '重度': 3}
        df['flow_severity'] = df['flow_control'].map(flow_map).fillna(0)
        
        df['weather_flow_interaction'] = df['weather_severity'] * df['flow_severity']
        
        df['is_same_sector'] = df.get('is_same_sector', True).astype(int)
        df['is_same_region'] = df.get('is_same_region', True).astype(int)
        
        if 'sector_congestion' not in df.columns:
            df['sector_congestion'] = 0.5
        if 'cross_region_penalty' not in df.columns:
            df['cross_region_penalty'] = 0.0
        
        df['sector_flow_combined'] = df['flow_severity'] * (1 + df['sector_congestion'] * 0.5)
        df['sector_weather_flow'] = df['sector_flow_combined'] * df['weather_severity']
        
        return df
    
    def scale_numeric_features(self, df, fit=True):
        df = df.copy()
        
        numeric_cols = [
            'historical_delay_7d', 'historical_delay_30d',
            'departure_hour', 'departure_minute_of_day',
            'day_of_week', 'day_of_month', 'month',
            'delay_trend', 'delay_ratio_7d_30d',
            'sector_congestion', 'cross_region_penalty',
            'sector_flow_combined', 'sector_weather_flow'
        ]
        
        if fit:
            self.scaler = StandardScaler()
            scaled_values = self.scaler.fit_transform(df[numeric_cols])
        else:
            scaled_values = self.scaler.transform(df[numeric_cols])
        
        for i, col in enumerate(numeric_cols):
            df[f'{col}_scaled'] = scaled_values[:, i]
        
        return df
    
    def prepare_features(self, df, fit=True):
        df = self.create_time_series_features(df)
        df = self.encode_categorical_features(df, fit=fit)
        df = self.scale_numeric_features(df, fit=fit)
        
        feature_cols = [
            'airline_encoded', 'departure_airport_encoded', 'arrival_airport_encoded',
            'weather_severity', 'flow_severity', 'weather_flow_interaction',
            'historical_delay_7d_scaled', 'historical_delay_30d_scaled',
            'day_of_week', 'day_of_month', 'month', 'quarter', 'week_of_year',
            'departure_hour_scaled', 'departure_minute_of_day_scaled',
            'is_morning', 'is_afternoon', 'is_evening', 'is_peak_hour',
            'is_weekend', 'is_peak_season', 'is_business_day',
            'delay_trend_scaled', 'delay_ratio_7d_30d_scaled',
            'historical_delay_severity', 'route_encoded',
            'departure_sector_encoded', 'arrival_sector_encoded',
            'departure_region_encoded', 'arrival_region_encoded',
            'is_same_sector', 'is_same_region',
            'sector_congestion_scaled', 'cross_region_penalty_scaled',
            'sector_flow_combined_scaled', 'sector_weather_flow_scaled'
        ]
        
        self.feature_names = feature_cols
        
        return df[feature_cols]
    
    def save(self, path):
        joblib.dump({
            'label_encoders': self.label_encoders,
            'scaler': self.scaler,
            'feature_names': self.feature_names
        }, path)
    
    def load(self, path):
        data = joblib.load(path)
        self.label_encoders = data['label_encoders']
        self.scaler = data['scaler']
        self.feature_names = data['feature_names']


def get_compensation_range(compensation):
    if compensation == 0:
        return '无赔付'
    elif compensation <= 150:
        return '0-150元'
    elif compensation <= 300:
        return '150-300元'
    elif compensation <= 500:
        return '300-500元'
    elif compensation <= 800:
        return '500-800元'
    else:
        return '800元以上'


def prepare_training_data(df):
    fe = FeatureEngineer()
    X = fe.prepare_features(df, fit=True)
    
    y_delay = df['is_delayed'].astype(int)
    y_minutes = df['delay_minutes']
    y_compensation = df['compensation']
    
    df['compensation_range'] = df['compensation'].apply(get_compensation_range)
    range_encoder = LabelEncoder()
    y_compensation_range = range_encoder.fit_transform(df['compensation_range'])
    
    return X, y_delay, y_minutes, y_compensation, y_compensation_range, range_encoder, fe


if __name__ == '__main__':
    from data_generator import generate_flight_data
    
    df = generate_flight_data(n_samples=2000)
    X, y_delay, y_minutes, y_comp, y_range, range_enc, fe = prepare_training_data(df)
    
    print(f"特征数量: {X.shape[1]}")
    print(f"特征名称: {X.columns.tolist()}")
    print(f"样本数量: {X.shape[0]}")
    print(f"延误率: {y_delay.mean():.2%}")
    print(f"平均赔付: {y_comp.mean():.2f}元")
