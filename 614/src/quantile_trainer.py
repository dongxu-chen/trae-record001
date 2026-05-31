import pandas as pd
import numpy as np
import xgboost as xgb
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error, r2_score, mean_absolute_error
import joblib
import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from feature_engineering import FeatureEngineer

class QuantileFuelModel:
    def __init__(self, quantiles=[0.05, 0.5, 0.95]):
        self.quantiles = quantiles
        self.models = {}
        self.feature_engineer = None
        
    def pinball_loss(self, y_true, y_pred, quantile):
        residual = y_true - y_pred
        return np.where(residual >= 0, quantile * residual, (quantile - 1) * residual).mean()
    
    def train(self, X_train, y_train, X_test, y_test):
        for q in self.quantiles:
            print(f"\n训练分位数模型: {int(q*100)}%")
            model = xgb.XGBRegressor(
                objective='reg:quantileerror',
                quantile_alpha=q,
                n_estimators=300,
                max_depth=8,
                learning_rate=0.05,
                subsample=0.8,
                colsample_bytree=0.8,
                reg_alpha=0.1,
                reg_lambda=1.0,
                random_state=42,
                n_jobs=-1
            )
            
            model.fit(
                X_train, y_train,
                eval_set=[(X_test, y_test)],
                verbose=50
            )
            
            self.models[q] = model
            
            y_pred = model.predict(X_test)
            pinball = self.pinball_loss(y_test, y_pred, q)
            print(f"  {int(q*100)}% 分位数 - Pinball Loss: {pinball:.4f}")
            
            if q == 0.5:
                rmse = np.sqrt(mean_squared_error(y_test, y_pred))
                mae = mean_absolute_error(y_test, y_pred)
                r2 = r2_score(y_test, y_pred)
                print(f"  中位数模型 - RMSE: {rmse:.4f}, MAE: {mae:.4f}, R²: {r2:.4f}")
        
        return self
    
    def predict(self, X):
        predictions = {}
        for q, model in self.models.items():
            predictions[q] = model.predict(X)
        return predictions
    
    def predict_interval(self, X):
        preds = self.predict(X)
        lower = preds[0.05]
        median = preds[0.5]
        upper = preds[0.95]
        return lower, median, upper
    
    def evaluate_interval(self, X_test, y_test):
        lower, median, upper = self.predict_interval(X_test)
        
        coverage = np.mean((y_test >= lower) & (y_test <= upper))
        mean_width = np.mean(upper - lower)
        median_width = np.median(upper - lower)
        
        print(f"\n预测区间评估:")
        print(f"  90% 区间覆盖率: {coverage:.2%}")
        print(f"  平均区间宽度: {mean_width:.4f} L/100km")
        print(f"  中位数区间宽度: {median_width:.4f} L/100km")
        
        below = np.mean(y_test < lower)
        above = np.mean(y_test > upper)
        print(f"  低于下限比例: {below:.2%}")
        print(f"  高于上限比例: {above:.2%}")
        
        return {
            'coverage': coverage,
            'mean_width': mean_width,
            'median_width': median_width,
            'below_ratio': below,
            'above_ratio': above
        }
    
    def save(self, model_dir):
        os.makedirs(model_dir, exist_ok=True)
        for q, model in self.models.items():
            model_path = os.path.join(model_dir, f'quantile_model_{int(q*100)}.pkl')
            joblib.dump(model, model_path)
        print(f"\n分位数模型已保存至: {model_dir}")
    
    @classmethod
    def load(cls, model_dir, quantiles=[0.05, 0.5, 0.95]):
        q_model = cls(quantiles)
        for q in quantiles:
            model_path = os.path.join(model_dir, f'quantile_model_{int(q*100)}.pkl')
            q_model.models[q] = joblib.load(model_path)
        print(f"分位数模型已从 {model_dir} 加载")
        return q_model

def train_quantile_models():
    print("="*60)
    print("训练汽车油耗分位数回归模型")
    print("="*60)
    
    print("\n1. 加载数据...")
    df = pd.read_csv('d:\\Trae\\project\\record001\\614\\data\\fuel_consumption_data.csv', encoding='utf-8-sig')
    print(f"数据加载完成，共 {len(df)} 条记录")
    
    print("\n2. 特征工程...")
    fe = FeatureEngineer()
    X, y = fe.fit_transform(df)
    print(f"特征数量: {len(fe.feature_names)}")
    
    print("\n3. 划分数据集...")
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )
    print(f"训练集: {len(X_train)}, 测试集: {len(X_test)}")
    
    print("\n4. 训练分位数回归模型...")
    quantile_model = QuantileFuelModel(quantiles=[0.05, 0.5, 0.95])
    quantile_model.train(X_train, y_train, X_test, y_test)
    
    print("\n5. 评估预测区间...")
    quantile_model.evaluate_interval(X_test, y_test)
    
    print("\n6. 保存模型...")
    model_dir = 'd:\\Trae\\project\\record001\\614\\models'
    quantile_model.save(model_dir)
    fe.save(os.path.join(model_dir, 'feature_engineer.pkl'))
    
    print("\n" + "="*60)
    print("分位数回归模型训练完成!")
    print("="*60)
    
    return quantile_model, fe

if __name__ == "__main__":
    train_quantile_models()
