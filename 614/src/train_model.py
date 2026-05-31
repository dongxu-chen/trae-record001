import pandas as pd
import numpy as np
import xgboost as xgb
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.metrics import mean_squared_error, r2_score, mean_absolute_error
import joblib
import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from feature_engineering import FeatureEngineer

def train_model():
    print("="*50)
    print("开始训练汽车油耗预测模型")
    print("="*50)
    
    print("\n1. 加载数据...")
    df = pd.read_csv('d:\\Trae\\project\\record001\\614\\data\\fuel_consumption_data.csv', encoding='utf-8-sig')
    print(f"数据加载完成，共 {len(df)} 条记录")
    
    print("\n2. 特征工程...")
    fe = FeatureEngineer()
    X, y = fe.fit_transform(df)
    print(f"特征数量: {len(fe.feature_names)}")
    print(f"特征列表: {fe.feature_names}")
    
    print("\n3. 划分训练集和测试集...")
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )
    print(f"训练集: {len(X_train)} 条")
    print(f"测试集: {len(X_test)} 条")
    
    print("\n4. 训练XGBoost模型...")
    model = xgb.XGBRegressor(
        n_estimators=500,
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
    
    print("\n5. 模型评估...")
    y_pred_train = model.predict(X_train)
    y_pred_test = model.predict(X_test)
    
    print("\n训练集指标:")
    print(f"  RMSE: {np.sqrt(mean_squared_error(y_train, y_pred_train)):.4f}")
    print(f"  MAE: {mean_absolute_error(y_train, y_pred_train):.4f}")
    print(f"  R²: {r2_score(y_train, y_pred_train):.4f}")
    
    print("\n测试集指标:")
    print(f"  RMSE: {np.sqrt(mean_squared_error(y_test, y_pred_test)):.4f}")
    print(f"  MAE: {mean_absolute_error(y_test, y_pred_test):.4f}")
    print(f"  R²: {r2_score(y_test, y_pred_test):.4f}")
    
    print("\n6. 交叉验证...")
    cv_scores = cross_val_score(model, X, y, cv=5, scoring='r2')
    print(f"5折交叉验证 R²: {cv_scores.mean():.4f} (±{cv_scores.std():.4f})")
    
    print("\n7. 特征重要性...")
    feature_importance = pd.DataFrame({
        'feature': fe.feature_names,
        'importance': model.feature_importances_
    }).sort_values('importance', ascending=False)
    print(feature_importance.head(10).to_string(index=False))
    
    print("\n8. 保存模型...")
    model_path = 'd:\\Trae\\project\\record001\\614\\models\\fuel_model.pkl'
    fe_path = 'd:\\Trae\\project\\record001\\614\\models\\feature_engineer.pkl'
    
    joblib.dump(model, model_path)
    fe.save(fe_path)
    
    print(f"模型已保存至: {model_path}")
    print(f"特征处理器已保存至: {fe_path}")
    
    print("\n" + "="*50)
    print("模型训练完成!")
    print("="*50)
    
    return model, fe

if __name__ == "__main__":
    train_model()
