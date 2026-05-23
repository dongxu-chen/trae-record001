import warnings
warnings.filterwarnings('ignore')

import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

from data_generator import generate_hr_data
from feature_engineering import FeatureEngineering
from model_training import ModelTrainer
from feature_analysis import FeatureAnalysis
from shap_explainer import SHAPExplainer
from model_updater import ModelUpdater
from threshold_optimizer import ThresholdOptimizer

def main():
    print("="*80)
    print("员工离职风险预测模型 - 增强版")
    print("Employee Attrition Risk Prediction - Enhanced")
    print("="*80)
    
    print("\n【步骤1】生成HR员工数据...")
    df = generate_hr_data(num_samples=2000, random_seed=42)
    df.to_csv('hr_employee_data.csv', index=False)
    print(f"✓ 生成 {len(df)} 条员工记录，共 {df.shape[1]} 个特征")
    print(f"✓ 整体离职率: {df['Attrition'].mean():.2%}")
    
    print("\n" + "="*80)
    print("【步骤2】特征工程...")
    fe = FeatureEngineering(scaling_method='standard')
    
    print("\n2.1 创建衍生特征...")
    df_enhanced = fe.create_additional_features(df)
    print(f"✓ 衍生特征后: {df_enhanced.shape[1]} 个特征")
    
    print("\n2.2 缺失值处理、编码和归一化...")
    print("  - 数值特征: 中位数填充 + StandardScaler归一化")
    print("  - 类别特征: 众数填充 + OneHotEncoder编码")
    X_processed, y = fe.fit_transform(df_enhanced)
    print(f"✓ 处理后: {X_processed.shape[1]} 个特征")
    
    print("\n" + "="*80)
    print("【步骤3】模型训练...")
    trainer = ModelTrainer(random_state=42)
    
    print("\n3.1 划分训练集和测试集...")
    X_train, X_test, y_train, y_test = trainer.train_test_split(X_processed, y)
    
    print("\n3.2 训练所有模型 (类别平衡处理)...")
    print("  - 逻辑回归: class_weight='balanced'")
    print("  - 随机森林: class_weight='balanced'")
    print("  - XGBoost: scale_pos_weight 自动计算")
    models, results = trainer.train_all_models(X_train, y_train, X_test, y_test)
    
    print("\n" + "="*80)
    print("【步骤4】模型性能对比...")
    comparison_df = trainer.compare_models()
    
    print("\n" + "="*80)
    print("【步骤5】SHAP模型解释...")
    print("5.1 初始化SHAP解释器 (XGBoost)...")
    best_model = trainer.models[trainer.best_model_name]
    shap_explainer = SHAPExplainer(best_model, trainer.best_model_name, 
                                    fe.get_feature_names(), X_train)
    
    X_sample = X_test.head(20).copy()
    shap_explainer.compute_shap_values(X_sample)
    print("✓ SHAP值计算完成")
    
    print("\n5.2 员工预测结果解释示例:")
    for i in range(3):
        risk_prob = trainer.predict_employee_risk(trainer.best_model_name, 
                                                   X_sample.iloc[i:i+1])[0]
        shap_explainer.print_employee_explanation(X_sample, employee_idx=i, 
                                                   risk_prob=risk_prob, top_n=5)
    
    print("\n" + "="*80)
    print("【步骤6】模型持久化与版本管理...")
    updater = ModelUpdater(model_dir='models')
    
    model_path, version = updater.save_model(best_model, 'Attrition_Prediction', fe)
    print(f"✓ 模型已保存: {model_path}")
    print(f"✓ 模型版本: v{version}")
    
    print("\n6.1 模拟增量数据更新...")
    df_new = generate_hr_data(num_samples=500, random_seed=100)
    df_new_enhanced = fe.create_additional_features(df_new)
    X_new, y_new = fe.transform(df_new_enhanced)
    
    updated_model, update_metrics = updater.incremental_update(
        'Attrition_Prediction', X_new, y_new, model_type='xgboost'
    )
    updater.save_model(updated_model, 'Attrition_Prediction', fe)
    updater.print_history('Attrition_Prediction')
    
    print("\n" + "="*80)
    print("【步骤7】阈值优化与调节...")
    y_prob = best_model.predict_proba(X_test)[:, 1]
    optimizer = ThresholdOptimizer(best_model, y_prob, y_test)
    
    print("\n7.1 寻找最佳阈值 (F1最优)...")
    best_threshold = optimizer.find_optimal_threshold(metric='f1')
    
    print("\n7.2 业务场景阈值建议:")
    optimizer.get_threshold_recommendation('balanced')
    
    print("\n" + "="*80)
    print("【总结】")
    print(f"最佳模型: {trainer.best_model_name}")
    print(f"最佳模型 ROC AUC: {results[trainer.best_model_name]['metrics']['roc_auc']:.4f}")
    print(f"最佳分类阈值: {best_threshold:.2f}")
    print("\n关键离职风险因素 (Top 8):")
    best_importance = trainer.get_feature_importance(trainer.best_model_name, fe.get_feature_names())
    for i, row in best_importance.head(8).iterrows():
        print(f"  {i+1}. {row['Feature']}")
    
    print("\n新增功能模块:")
    print("  ✓ SHAP模型解释 - 每个员工的决策贡献因素")
    print("  ✓ 模型在线更新 - 每周增量训练与版本管理")
    print("  ✓ 阈值调节工具 - 精确率/召回率平衡滑块")
    
    print("\n" + "="*80)
    print("模型训练完成！所有结果已保存。")
    print("="*80)
    
    return {
        'data': df,
        'X_processed': X_processed,
        'feature_engineering': fe,
        'trainer': trainer,
        'shap_explainer': shap_explainer,
        'model_updater': updater,
        'threshold_optimizer': optimizer,
        'models': models,
        'results': results,
        'best_threshold': best_threshold
    }

if __name__ == "__main__":
    results = main()
