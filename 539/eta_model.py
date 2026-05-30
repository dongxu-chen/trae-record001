import pandas as pd
import numpy as np
import lightgbm as lgb
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
import joblib
import os

class ETAPredictor:
    def __init__(self, model_dir='models'):
        self.model_dir = model_dir
        self.models = {}
        self.feature_cols = None
        self.courier_stats = None
        self.interval_calibration = {}
        
        if not os.path.exists(model_dir):
            os.makedirs(model_dir)
    
    def train_quantile_model(self, X_train, y_train, X_valid, y_valid, quantile):
        params = {
            'objective': 'quantile',
            'alpha': quantile,
            'metric': 'quantile',
            'boosting_type': 'gbdt',
            'num_leaves': 23,
            'learning_rate': 0.08,
            'feature_fraction': 0.85,
            'bagging_fraction': 0.75,
            'bagging_freq': 5,
            'verbose': -1,
            'min_data_in_leaf': 30,
            'max_depth': 6,
            'lambda_l1': 0.5,
            'lambda_l2': 1.0
        }
        
        train_data = lgb.Dataset(X_train, label=y_train)
        valid_data = lgb.Dataset(X_valid, label=y_valid, reference=train_data)
        
        model = lgb.train(
            params,
            train_data,
            num_boost_round=600,
            valid_sets=[valid_data],
            callbacks=[lgb.early_stopping(stopping_rounds=40),
                      lgb.log_evaluation(period=0)]
        )
        
        return model
    
    def train_mean_model(self, X_train, y_train, X_valid, y_valid):
        params = {
            'objective': 'regression',
            'metric': 'mae',
            'boosting_type': 'gbdt',
            'num_leaves': 27,
            'learning_rate': 0.07,
            'feature_fraction': 0.88,
            'bagging_fraction': 0.78,
            'bagging_freq': 5,
            'verbose': -1,
            'min_data_in_leaf': 25,
            'max_depth': 7,
            'lambda_l1': 0.3,
            'lambda_l2': 0.8
        }
        
        train_data = lgb.Dataset(X_train, label=y_train)
        valid_data = lgb.Dataset(X_valid, label=y_valid, reference=train_data)
        
        model = lgb.train(
            params,
            train_data,
            num_boost_round=600,
            valid_sets=[valid_data],
            callbacks=[lgb.early_stopping(stopping_rounds=40),
                      lgb.log_evaluation(period=0)]
        )
        
        return model
    
    def calibrate_intervals(self, X_valid, y_valid):
        print('校准置信区间...')
        
        mean_pred = self.models['mean'].predict(X_valid, num_iteration=self.models['mean'].best_iteration)
        
        for q in [10, 20, 30, 70, 80, 90]:
            pred = self.models[f'q{q}'].predict(
                X_valid, num_iteration=self.models[f'q{q}'].best_iteration
            )
            
            if q < 50:
                actual_coverage = np.mean(y_valid >= pred)
                target_coverage = q / 100
            else:
                actual_coverage = np.mean(y_valid <= pred)
                target_coverage = q / 100
            
            adjustment_factor = target_coverage / actual_coverage if actual_coverage > 0 else 1.0
            adjustment_factor = max(0.8, min(1.2, adjustment_factor))
            
            self.interval_calibration[f'q{q}'] = adjustment_factor
        
        print('校准系数:', self.interval_calibration)
    
    def train(self, X, y, test_size=0.2, random_state=42):
        X_train, X_valid, y_train, y_valid = train_test_split(
            X, y, test_size=test_size, random_state=random_state
        )
        
        print('训练均值预测模型...')
        self.models['mean'] = self.train_mean_model(X_train, y_train, X_valid, y_valid)
        
        print('训练分位数模型 (置信区间)...')
        quantiles = [0.10, 0.20, 0.30, 0.50, 0.70, 0.80, 0.90]
        for q in quantiles:
            print(f'  训练 {int(q*100)}% 分位数模型...')
            self.models[f'q{int(q*100)}'] = self.train_quantile_model(
                X_train, y_train, X_valid, y_valid, q
            )
        
        self.calibrate_intervals(X_valid, y_valid)
        
        self.feature_cols = X.columns.tolist()
        
        y_pred = self.models['mean'].predict(X_valid, num_iteration=self.models['mean'].best_iteration)
        mae = mean_absolute_error(y_valid, y_pred)
        rmse = np.sqrt(mean_squared_error(y_valid, y_pred))
        r2 = r2_score(y_valid, y_pred)
        
        pred_results = self.predict(X_valid, confidence_level=0.8)
        coverage = np.mean(
            (y_valid >= pred_results['lower_bound']) & 
            (y_valid <= pred_results['upper_bound'])
        )
        avg_width = np.mean(pred_results['confidence_interval'])
        
        print(f'\n模型验证结果:')
        print(f'  MAE: {mae:.2f} 分钟')
        print(f'  RMSE: {rmse:.2f} 分钟')
        print(f'  R²: {r2:.4f}')
        print(f'  80%置信区间覆盖率: {coverage:.2%}')
        print(f'  80%置信区间平均宽度: {avg_width:.2f} 分钟')
        
        return {'mae': mae, 'rmse': rmse, 'r2': r2, 'coverage': coverage, 'avg_width': avg_width}
    
    def predict(self, X, confidence_level=0.8):
        if 'mean' not in self.models:
            raise ValueError('模型未训练，请先调用 train() 方法')
        
        mean_pred = self.models['mean'].predict(X, num_iteration=self.models['mean'].best_iteration)
        
        if confidence_level <= 0.6:
            lower_q, upper_q = 20, 80
        elif confidence_level <= 0.75:
            lower_q, upper_q = 15, 85
        elif confidence_level <= 0.85:
            lower_q, upper_q = 10, 90
        else:
            lower_q, upper_q = 5, 95
        
        lower_key = f'q{max(10, lower_q)}'
        upper_key = f'q{min(90, upper_q)}'
        
        lower_pred = self.models[lower_key].predict(
            X, num_iteration=self.models[lower_key].best_iteration
        )
        upper_pred = self.models[upper_key].predict(
            X, num_iteration=self.models[upper_key].best_iteration
        )
        
        if self.interval_calibration:
            lower_adj = self.interval_calibration.get(lower_key, 1.0)
            upper_adj = self.interval_calibration.get(upper_key, 1.0)
            
            lower_deviation = mean_pred - lower_pred
            upper_deviation = upper_pred - mean_pred
            
            shrinkage_factor = 0.85
            
            lower_pred = mean_pred - lower_deviation * lower_adj * shrinkage_factor
            upper_pred = mean_pred + upper_deviation * upper_adj * shrinkage_factor
        
        lower_bound = np.minimum(mean_pred, lower_pred)
        upper_bound = np.maximum(mean_pred, upper_pred)
        
        min_interval = mean_pred * 0.08
        interval_width = upper_bound - lower_bound
        too_narrow = interval_width < min_interval
        
        lower_bound = np.where(too_narrow, mean_pred - min_interval / 2, lower_bound)
        upper_bound = np.where(too_narrow, mean_pred + min_interval / 2, upper_bound)
        
        results = {
            'predicted_minutes': mean_pred,
            'lower_bound': lower_bound,
            'upper_bound': upper_bound,
            'confidence_interval': upper_bound - lower_bound,
            'confidence_level': confidence_level,
            'lower_quantile': lower_q,
            'upper_quantile': upper_q
        }
        
        return results
    
    def predict_single(self, features, confidence_level=0.9):
        X = pd.DataFrame([features])
        X = X[self.feature_cols]
        results = self.predict(X, confidence_level)
        return {k: float(v[0]) for k, v in results.items()}
    
    def get_feature_importance(self, importance_type='gain'):
        if 'mean' not in self.models:
            raise ValueError('模型未训练')
        
        importance = self.models['mean'].feature_importance(
            importance_type=importance_type
        )
        feature_imp = pd.DataFrame({
            'feature': self.feature_cols,
            'importance': importance
        }).sort_values('importance', ascending=False)
        
        return feature_imp
    
    def save_models(self):
        model_path = os.path.join(self.model_dir, 'eta_models.pkl')
        joblib.dump({
            'models': self.models,
            'feature_cols': self.feature_cols,
            'interval_calibration': self.interval_calibration
        }, model_path)
        print(f'模型已保存到 {model_path}')
    
    def load_models(self):
        model_path = os.path.join(self.model_dir, 'eta_models.pkl')
        if os.path.exists(model_path):
            data = joblib.load(model_path)
            self.models = data['models']
            self.feature_cols = data['feature_cols']
            self.interval_calibration = data.get('interval_calibration', {})
            print(f'模型已从 {model_path} 加载')
            return True
        return False

def calculate_prediction_metrics(y_true, y_pred, y_lower, y_upper):
    coverage = np.mean((y_true >= y_lower) & (y_true <= y_upper))
    interval_width = np.mean(y_upper - y_lower)
    mae = mean_absolute_error(y_true, y_pred)
    
    return {
        'coverage_rate': coverage,
        'avg_interval_width': interval_width,
        'mae': mae
    }

if __name__ == '__main__':
    from data_generator import generate_historical_data
    from feature_engineering import prepare_training_data
    
    print('生成训练数据...')
    df = generate_historical_data(3000)
    
    print('特征工程...')
    X, y, feature_cols, engineer = prepare_training_data(df)
    
    print('训练ETA预测模型...')
    predictor = ETAPredictor()
    metrics = predictor.train(X, y)
    
    print('保存模型...')
    predictor.save_models()
    
    print('特征重要性:')
    print(predictor.get_feature_importance().head(10))
