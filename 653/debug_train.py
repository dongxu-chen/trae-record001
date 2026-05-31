import sys
sys.stdout.reconfigure(encoding='utf-8')

print("=== 开始调试 ===", flush=True)

try:
    print("1. 导入pandas...", flush=True)
    import pandas as pd
    print("   pandas导入成功", flush=True)
    
    print("2. 读取数据...", flush=True)
    df = pd.read_csv("job_salary_data.csv", encoding="utf-8-sig")
    print(f"   数据行数: {len(df)}", flush=True)
    
    print("3. 导入feature_engineering...", flush=True)
    from feature_engineering import FeatureEngineer
    print("   feature_engineering导入成功", flush=True)
    
    print("4. 特征工程...", flush=True)
    fe = FeatureEngineer()
    X, feature_names = fe.fit_transform(df.head(100))
    print(f"   特征矩阵形状: {X.shape}", flush=True)
    
    print("5. 导入xgboost...", flush=True)
    from xgboost import XGBRegressor
    print("   xgboost导入成功", flush=True)
    
    print("6. 训练模型...", flush=True)
    y_lower = df["薪资下限"].head(100).values
    model = XGBRegressor(n_estimators=50, max_depth=3, random_state=42)
    model.fit(X, y_lower)
    print("   模型训练成功", flush=True)
    
    print("7. 保存模型...", flush=True)
    import joblib
    joblib.dump(model, "models/test_model.pkl")
    print("   模型保存成功", flush=True)
    
    print("\n=== 所有步骤成功！ ===", flush=True)
    
except Exception as e:
    print(f"\n=== 错误发生 ===", flush=True)
    print(f"错误类型: {type(e).__name__}", flush=True)
    print(f"错误信息: {e}", flush=True)
    import traceback
    print("堆栈跟踪:", flush=True)
    traceback.print_exc()
    sys.exit(1)
