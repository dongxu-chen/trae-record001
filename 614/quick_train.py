import pandas as pd
import numpy as np
import xgboost as xgb
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler, LabelEncoder
import joblib
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))
from feature_engineering import FeatureEngineer

print("="*60)
print("训练分位数回归模型")
print("="*60)

print("\n1. 加载数据...")
df = pd.read_csv('data/fuel_consumption_data.csv', encoding='utf-8-sig')
print(f"数据加载完成，共 {len(df)} 条记录，{len(df.columns)} 列")

print("\n2. 特征工程...")
fe = FeatureEngineer()
X, y = fe.fit_transform(df)
print(f"特征数量: {len(fe.feature_names)}")

print("\n3. 划分数据集...")
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42
)
print(f"训练集: {len(X_train)}, 测试集: {len(X_test)}")

print("\n4. 训练分位数回归模型 (5%, 50%, 95%)...")
quantiles = [0.05, 0.5, 0.95]
models = {}

for q in quantiles:
    print(f"\n  训练 {int(q*100)}% 分位数模型...")
    model = xgb.XGBRegressor(
        objective='reg:quantileerror',
        quantile_alpha=q,
        n_estimators=200,
        max_depth=8,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.8,
        random_state=42,
        n_jobs=-1
    )
    model.fit(X_train, y_train, verbose=False)
    models[q] = model
    
    y_pred = model.predict(X_test)
    
    def pinball_loss(y_true, y_pred, q):
        residual = y_true - y_pred
        return np.where(residual >= 0, q * residual, (q - 1) * residual).mean()
    
    pb = pinball_loss(y_test, y_pred, q)
    print(f"    Pinball Loss: {pb:.4f}")
    
    if q == 0.5:
        from sklearn.metrics import r2_score, mean_squared_error
        rmse = np.sqrt(mean_squared_error(y_test, y_pred))
        r2 = r2_score(y_test, y_pred)
        print(f"    RMSE: {rmse:.4f}, R²: {r2:.4f}")

print("\n5. 评估预测区间...")
lower = models[0.05].predict(X_test)
median = models[0.5].predict(X_test)
upper = models[0.95].predict(X_test)

coverage = np.mean((y_test >= lower) & (y_test <= upper))
mean_width = np.mean(upper - lower)
median_width = np.median(upper - lower)

print(f"  90% 区间覆盖率: {coverage:.2%}")
print(f"  平均区间宽度: {mean_width:.4f} L/100km")
print(f"  中位数区间宽度: {median_width:.4f} L/100km")
print(f"  区间宽度比传统方法(1.6L)窄: {(1 - mean_width/1.6)*100:.1f}%")

print("\n6. 保存模型...")
model_dir = 'models'
os.makedirs(model_dir, exist_ok=True)

for q in quantiles:
    model_path = os.path.join(model_dir, f'quantile_model_{int(q*100)}.pkl')
    joblib.dump(models[q], model_path)
    print(f"  已保存: {model_path}")

fe_path = os.path.join(model_dir, 'feature_engineer.pkl')
fe.save(fe_path)
print(f"  已保存: {fe_path}")

print("\n" + "="*60)
print("分位数回归模型训练完成!")
print("="*60)
