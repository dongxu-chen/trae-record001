import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.model_selection import train_test_split, GridSearchCV
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
import joblib
import os

class ETAPredictor:
    def __init__(self):
        self.model = None
        self.lower_model = None
        self.upper_model = None
        self.feature_importance = None
        
    def train(self, X_train, y_train, params=None):
        if params is None:
            params = {
                'n_estimators': 200,
                'max_depth': 6,
                'learning_rate': 0.1,
                'subsample': 0.8,
                'colsample_bytree': 0.8,
                'random_state': 42
            }
        
        self.model = xgb.XGBRegressor(**params)
        self.model.fit(X_train, y_train)
        
        self._train_quantile_models(X_train, y_train)
        
        self.feature_importance = pd.DataFrame({
            'feature': X_train.columns,
            'importance': self.model.feature_importances_
        }).sort_values('importance', ascending=False)
        
        return self
    
    def _train_quantile_models(self, X_train, y_train):
        params = {
            'n_estimators': 100,
            'max_depth': 5,
            'learning_rate': 0.05,
            'subsample': 0.8,
            'random_state': 42
        }
        
        self.lower_model = xgb.XGBRegressor(
            objective='reg:quantileerror',
            quantile_alpha=0.1,
            **params
        )
        self.lower_model.fit(X_train, y_train)
        
        self.upper_model = xgb.XGBRegressor(
            objective='reg:quantileerror',
            quantile_alpha=0.9,
            **params
        )
        self.upper_model.fit(X_train, y_train)
    
    def predict(self, X):
        if self.model is None:
            raise ValueError("模型未训练!")
        
        pred = self.model.predict(X)
        lower = self.lower_model.predict(X)
        upper = self.upper_model.predict(X)
        
        lower = np.minimum(lower, pred * 0.7)
        upper = np.maximum(upper, pred * 1.3)
        
        return {
            'prediction': pred,
            'lower_bound': lower,
            'upper_bound': upper,
            'confidence_interval': upper - lower
        }
    
    def predict_single(self, X):
        results = self.predict(X)
        return {
            'predicted_eta': round(float(results['prediction'][0]), 1),
            'lower_bound': round(float(results['lower_bound'][0]), 1),
            'upper_bound': round(float(results['upper_bound'][0]), 1),
            'confidence_range': round(float(results['confidence_interval'][0]), 1)
        }
    
    def evaluate(self, X_test, y_test):
        predictions = self.predict(X_test)
        pred = predictions['prediction']
        
        metrics = {
            'MAE': mean_absolute_error(y_test, pred),
            'RMSE': np.sqrt(mean_squared_error(y_test, pred)),
            'R2': r2_score(y_test, pred),
            'MAPE': np.mean(np.abs((y_test - pred) / y_test)) * 100
        }
        
        within_interval = np.mean((y_test >= predictions['lower_bound']) & 
                                  (y_test <= predictions['upper_bound']))
        metrics['coverage_probability'] = within_interval
        
        return metrics
    
    def analyze_delay_factors(self, X, predicted_eta, baseline_eta):
        delay_analysis = []
        feature_impact = {}
        
        weather_impact = X['weather_impact'].values[0]
        if weather_impact > 1.0:
            impact_minutes = baseline_eta * (weather_impact - 1)
            if impact_minutes > 1:
                feature_impact['天气'] = impact_minutes
                delay_analysis.append(f"天气影响增加约{impact_minutes:.1f}分钟")
        
        traffic_impact = X['traffic_impact'].values[0]
        if traffic_impact > 1.0:
            impact_minutes = baseline_eta * (traffic_impact - 1)
            if impact_minutes > 1:
                feature_impact['交通'] = impact_minutes
                delay_analysis.append(f"交通拥堵增加约{impact_minutes:.1f}分钟")
        
        is_peak = X['is_peak_hour'].values[0]
        if is_peak:
            impact_minutes = baseline_eta * 0.15
            feature_impact['高峰期'] = impact_minutes
            delay_analysis.append(f"用餐高峰期增加约{impact_minutes:.1f}分钟")
        
        has_elevator = X['has_elevator'].values[0]
        floor = X['floor'].values[0]
        if not has_elevator and floor > 3:
            impact_minutes = floor * 0.3
            feature_impact['无电梯'] = impact_minutes
            delay_analysis.append(f"无电梯高楼层增加约{impact_minutes:.1f}分钟")
        
        if 'is_office_building' in X.columns:
            is_office = X['is_office_building'].values[0]
            if is_office and floor > 10:
                impact_minutes = floor * 0.15
                feature_impact['写字楼'] = impact_minutes
                delay_analysis.append(f"写字楼高层电梯等待增加约{impact_minutes:.1f}分钟")
        
        if 'is_new_restaurant' in X.columns:
            is_new_rest = X['is_new_restaurant'].values[0]
            if is_new_rest:
                impact_minutes = baseline_eta * 0.12
                feature_impact['新餐厅'] = impact_minutes
                delay_analysis.append(f"新餐厅备餐波动增加约{impact_minutes:.1f}分钟")
        
        if 'restaurant_on_time_rate' in X.columns:
            on_time_rate = X['restaurant_on_time_rate'].values[0]
            if on_time_rate < 0.85:
                impact_minutes = baseline_eta * (0.9 - on_time_rate)
                if impact_minutes > 1:
                    feature_impact['餐厅准时率'] = impact_minutes
                    delay_analysis.append(f"餐厅历史准时率偏低({on_time_rate:.1%})，增加约{impact_minutes:.1f}分钟")
        
        total_delay = predicted_eta - baseline_eta
        
        return {
            'delay_reasons': delay_analysis if delay_analysis else ['无显著延迟因素'],
            'feature_impact': feature_impact,
            'total_delay_minutes': max(0, total_delay)
        }
    
    def save(self, path):
        joblib.dump({
            'model': self.model,
            'lower_model': self.lower_model,
            'upper_model': self.upper_model,
            'feature_importance': self.feature_importance
        }, path)
    
    @classmethod
    def load(cls, path):
        eta = cls()
        data = joblib.load(path)
        eta.model = data['model']
        eta.lower_model = data['lower_model']
        eta.upper_model = data['upper_model']
        eta.feature_importance = data['feature_importance']
        return eta

def train_and_save_model(X, y, save_path='models/eta_model.pkl'):
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )
    
    eta_predictor = ETAPredictor()
    eta_predictor.train(X_train, y_train)
    
    metrics = eta_predictor.evaluate(X_test, y_test)
    
    print("模型评估指标:")
    for k, v in metrics.items():
        print(f"  {k}: {v:.4f}")
    
    print("\n特征重要性Top 10:")
    print(eta_predictor.feature_importance.head(10))
    
    eta_predictor.save(save_path)
    print(f"\n模型已保存至 {save_path}")
    
    return eta_predictor, metrics

if __name__ == '__main__':
    os.makedirs('models', exist_ok=True)
    
    if os.path.exists('data/orders.csv') and os.path.exists('models/feature_engineer.pkl'):
        from feature_engineering import FeatureEngineer
        
        orders = pd.read_csv('data/orders.csv')
        fe = FeatureEngineer.load('models/feature_engineer.pkl')
        X = fe.transform(orders, is_training=False)
        y = orders['delivery_time_min']
        
        model, metrics = train_and_save_model(X, y)
    else:
        print("请先生成数据和特征工程模型")
