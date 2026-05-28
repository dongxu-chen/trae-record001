import pandas as pd
import numpy as np
import joblib
import os
from datetime import datetime
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder, StandardScaler
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
import xgboost as xgb
from prophet import Prophet

class AirlinePriceModel:
    def __init__(self):
        self.xgb_model = None
        self.prophet_model = None
        self.label_encoders = {}
        self.scaler = StandardScaler()
        self.feature_columns = None
        
    def prepare_features(self, df, is_training=True):
        df = df.copy()
        
        categorical_cols = ['route', 'origin', 'destination', 'airline']
        for col in categorical_cols:
            if col in df.columns:
                if is_training:
                    le = LabelEncoder()
                    df[col] = le.fit_transform(df[col].astype(str))
                    self.label_encoders[col] = le
                else:
                    if col in self.label_encoders:
                        le = self.label_encoders[col]
                        df[col] = df[col].astype(str).map(lambda x: le.transform([x])[0] if x in le.classes_ else -1)
            else:
                if col == 'airline':
                    df[col] = 0
        
        df['departure_month'] = df['departure_date'].dt.month
        df['departure_day'] = df['departure_date'].dt.day
        df['departure_weekday'] = df['departure_date'].dt.weekday
        df['is_weekend'] = (df['departure_weekday'] >= 5).astype(int)
        
        df['search_month'] = df['search_date'].dt.month
        df['search_day'] = df['search_date'].dt.day
        
        df['booking_days_log'] = np.log1p(df['booking_days'])
        
        enhanced_features = [
            'oil_futures_price', 'oil_volatility', 'fuel_surcharge',
            'is_promotion', 'discount_amount', 'event_impact', 'seasonal_effect'
        ]
        for feat in enhanced_features:
            if feat not in df.columns:
                if feat == 'is_promotion':
                    df[feat] = 0
                elif feat == 'discount_amount':
                    df[feat] = 0
                elif feat == 'event_impact':
                    df[feat] = 1.0
                elif feat == 'seasonal_effect':
                    df[feat] = 1.0
                elif feat == 'oil_futures_price':
                    df[feat] = df['oil_price']
                elif feat == 'oil_volatility':
                    df[feat] = 0.025
                elif feat == 'fuel_surcharge':
                    df[feat] = 100
        
        if is_training:
            self.feature_columns = [
                'route', 'booking_days', 'booking_days_log', 'oil_price', 
                'oil_futures_price', 'oil_volatility', 'fuel_surcharge',
                'is_holiday', 'is_promotion', 'discount_amount', 
                'event_impact', 'seasonal_effect',
                'departure_month', 'departure_day', 'departure_weekday', 
                'is_weekend', 'search_month', 'search_day'
            ]
        
        return df
    
    def train_xgboost(self, df):
        print('正在训练增强版XGBoost模型...')
        
        df = self.prepare_features(df, is_training=True)
        
        X = df[self.feature_columns]
        y = df['price']
        
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
        
        self.xgb_model = xgb.XGBRegressor(
            n_estimators=300,
            max_depth=10,
            learning_rate=0.03,
            subsample=0.85,
            colsample_bytree=0.85,
            reg_alpha=0.1,
            reg_lambda=1.5,
            min_child_weight=5,
            random_state=42
        )
        
        self.xgb_model.fit(X_train, y_train)
        
        y_pred = self.xgb_model.predict(X_test)
        mae = mean_absolute_error(y_test, y_pred)
        rmse = np.sqrt(mean_squared_error(y_test, y_pred))
        r2 = r2_score(y_test, y_pred)
        
        print(f'增强版XGBoost模型评估结果:')
        print(f'  MAE: {mae:.2f}')
        print(f'  RMSE: {rmse:.2f}')
        print(f'  R²: {r2:.4f}')
        
        feature_importance = pd.DataFrame({
            'feature': self.feature_columns,
            'importance': self.xgb_model.feature_importances_
        }).sort_values('importance', ascending=False)
        print('\n特征重要性 Top 10:')
        print(feature_importance.head(10))
        
        return self.xgb_model
    
    def train_prophet(self, df, route=None):
        print(f'正在训练Prophet时间序列模型...')
        
        if route:
            route_data = df[df['route'] == route].copy()
        else:
            route_data = df.copy()
        
        daily_avg = route_data.groupby('departure_date')['price'].mean().reset_index()
        daily_avg.columns = ['ds', 'y']
        daily_avg = daily_avg.sort_values('ds')
        
        self.prophet_model = Prophet(
            changepoint_prior_scale=0.05,
            seasonality_prior_scale=10.0,
            yearly_seasonality=True,
            weekly_seasonality=True,
            daily_seasonality=False
        )
        
        self.prophet_model.add_seasonality(name='monthly', period=30.5, fourier_order=5)
        self.prophet_model.add_seasonality(name='quarterly', period=91.25, fourier_order=3)
        
        self.prophet_model.fit(daily_avg)
        
        return self.prophet_model
    
    def predict_with_xgboost(self, features):
        if self.xgb_model is None:
            raise Exception('XGBoost模型未训练，请先调用train_xgboost()')
        
        features = self.prepare_features(features, is_training=False)
        X = features[self.feature_columns]
        
        predictions = self.xgb_model.predict(X)
        return predictions
    
    def predict_with_prophet(self, periods=30):
        if self.prophet_model is None:
            raise Exception('Prophet模型未训练，请先调用train_prophet()')
        
        future = self.prophet_model.make_future_dataframe(periods=periods)
        forecast = self.prophet_model.predict(future)
        
        return forecast[['ds', 'yhat', 'yhat_lower', 'yhat_upper']]
    
    def get_feature_importance(self):
        if self.xgb_model is None:
            return None
        
        feature_importance = pd.DataFrame({
            'feature': self.feature_columns,
            'importance': self.xgb_model.feature_importances_
        }).sort_values('importance', ascending=False)
        
        return feature_importance
    
    def save_models(self, save_dir='models'):
        os.makedirs(save_dir, exist_ok=True)
        
        if self.xgb_model is not None:
            joblib.dump(self.xgb_model, os.path.join(save_dir, 'xgb_model.pkl'))
        
        if self.prophet_model is not None:
            joblib.dump(self.prophet_model, os.path.join(save_dir, 'prophet_model.pkl'))
        
        joblib.dump(self.label_encoders, os.path.join(save_dir, 'label_encoders.pkl'))
        joblib.dump(self.feature_columns, os.path.join(save_dir, 'feature_columns.pkl'))
        
        print(f'增强版模型已保存到 {save_dir}/ 目录')
    
    def load_models(self, load_dir='models'):
        self.xgb_model = joblib.load(os.path.join(load_dir, 'xgb_model.pkl'))
        self.prophet_model = joblib.load(os.path.join(load_dir, 'prophet_model.pkl'))
        self.label_encoders = joblib.load(os.path.join(load_dir, 'label_encoders.pkl'))
        self.feature_columns = joblib.load(os.path.join(load_dir, 'feature_columns.pkl'))
        print('增强版模型加载成功')

def train_all_models(data_path='historical_data.csv'):
    print('加载数据...')
    df = pd.read_csv(data_path, parse_dates=['departure_date', 'search_date'])
    print(f'数据加载完成，共 {len(df)} 条记录')
    
    model = AirlinePriceModel()
    
    model.train_xgboost(df)
    model.train_prophet(df)
    
    model.save_models()
    
    return model

if __name__ == '__main__':
    if os.path.exists('historical_data.csv'):
        train_all_models()
    else:
        print('请先生成历史数据')
