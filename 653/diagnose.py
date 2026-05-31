import sys
sys.stdout.reconfigure(encoding='utf-8')

log_file = open("training_log.txt", "w", encoding="utf-8")

def log(msg):
    print(msg, flush=True)
    log_file.write(msg + "\n")
    log_file.flush()

log("="*60)
log("开始诊断训练流程")
log("="*60)

try:
    log("\n[1/7] 导入pandas...")
    import pandas as pd
    log("   ✓ pandas导入成功")
    
    log("\n[2/7] 读取数据...")
    df = pd.read_csv("job_salary_data.csv", encoding="utf-8-sig")
    log(f"   ✓ 数据加载成功，共 {len(df)} 条")
    
    log("\n[3/7] 导入FeatureEngineer...")
    from feature_engineering import FeatureEngineer
    log("   ✓ FeatureEngineer导入成功")
    
    log("\n[4/7] 执行特征工程...")
    fe = FeatureEngineer()
    X, feature_names = fe.fit_transform(df.head(500))
    log(f"   ✓ 特征工程完成，特征数量: {len(feature_names)}")
    
    log("\n[5/7] 训练XGBoost模型...")
    from xgboost import XGBRegressor
    import numpy as np
    
    y_lower = df["薪资下限"].head(500).values
    model_lower = XGBRegressor(n_estimators=100, max_depth=5, random_state=42)
    model_lower.fit(X, y_lower)
    log("   ✓ 薪资下限模型训练成功")
    
    y_upper = df["薪资上限"].head(500).values
    model_upper = XGBRegressor(n_estimators=100, max_depth=5, random_state=42)
    model_upper.fit(X, y_upper)
    log("   ✓ 薪资上限模型训练成功")
    
    log("\n[6/7] 保存模型...")
    import joblib
    import os
    
    os.makedirs("models", exist_ok=True)
    joblib.dump(model_lower, "models/model_lower.pkl")
    joblib.dump(model_upper, "models/model_upper.pkl")
    log("   ✓ 模型文件已保存")
    
    log("\n[7/7] 测试预测...")
    test_data = pd.DataFrame([{
        "岗位标题": "Python开发工程师",
        "岗位描述": "负责后端开发",
        "地区": "北京",
        "公司规模": "150-500人",
        "学历要求": "本科"
    }])
    
    X_test = fe.transform(test_data)
    pred_lower = model_lower.predict(X_test)[0]
    pred_upper = model_upper.predict(X_test)[0]
    log(f"   ✓ 预测结果: {int(pred_lower):,} - {int(pred_upper):,} 元/月")
    
    log("\n" + "="*60)
    log("✓ 所有步骤成功完成！")
    log("="*60)
    
except Exception as e:
    log(f"\n✗ 错误发生在步骤: {sys.exc_info()[-1].tb_lineno}")
    log(f"错误类型: {type(e).__name__}")
    log(f"错误信息: {str(e)}")
    import traceback
    log("堆栈跟踪:")
    traceback.print_exc(file=log_file)
    log_file.flush()

finally:
    log_file.close()
    print("\n详细日志已保存到 training_log.txt")
