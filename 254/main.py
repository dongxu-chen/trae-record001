import os
import sys
import argparse
from generate_data import generate_insurance_claims, save_data
from train_model import main as train_model
from predict import predict_single_claim, predict_batch, create_sample_claim, create_suspicious_claim
from risk_analysis import analyze_risk_factors, analyze_single_claim, generate_tiered_decision, save_shap_plots
from train_model import load_model, load_data, preprocess_data
from network_analysis import analyze_network
from interpretability_report import generate_interpretability_report
from review_simulator import run_simulator
import pandas as pd
import numpy as np


def main():
    parser = argparse.ArgumentParser(description='保险理赔欺诈风险预测系统')
    parser.add_argument('--mode', type=str, default='full', 
                        choices=['full', 'generate', 'train', 'predict', 'analyze', 
                                'network', 'interpretability', 'simulator'],
                        help='运行模式: full(完整流程), generate(生成数据), train(训练模型), predict(预测), analyze(风险分析), network(网络分析), interpretability(可解释性报告), simulator(模拟审核)')
    parser.add_argument('--n_samples', type=int, default=10000, help='生成样本数量')
    parser.add_argument('--fraud_ratio', type=float, default=0.08, help='欺诈样本比例')
    parser.add_argument('--claim_file', type=str, default=None, help='待预测理赔数据文件路径')
    args = parser.parse_args()
    
    print("="*70)
    print("保险理赔欺诈风险预测系统")
    print("Insurance Claim Fraud Risk Prediction System")
    print("="*70)
    
    if args.mode in ['full', 'generate']:
        print("\n📊 步骤1: 生成模拟理赔数据 (含网络标识字段)")
        print("-"*70)
        df = generate_insurance_claims(n_samples=args.n_samples, fraud_ratio=args.fraud_ratio, fraud_group_ratio=0.3)
        train_df, test_df = save_data(df)
        print(f"✓ 数据生成完成: {len(df)} 条记录")
        print(f"  - 包含手机号、地址、医院、银行账号用于网络分析")
    
    if args.mode in ['full', 'train']:
        print("\n🤖 步骤2: 训练 XGBoost 模型 (CV-SMOTE避免数据泄露)")
        print("-"*70)
        model, preprocessor, feature_names, metrics = train_model()
        print(f"✓ 模型训练完成")
        print(f"  Test ROC-AUC: {metrics['roc_auc']:.4f}")
        print(f"  Test PR-AUC: {metrics['pr_auc']:.4f}")
        if metrics.get('cv_scores_roc') is not None:
            print(f"  CV ROC-AUC:   {metrics['cv_scores_roc'].mean():.4f} (±{metrics['cv_scores_roc'].std():.4f})")
    
    if args.mode in ['full', 'predict']:
        print("\n🔮 步骤3: 理赔欺诈风险预测")
        print("-"*70)
        
        model, preprocessor, feature_names = load_model()
        
        if args.claim_file and os.path.exists(args.claim_file):
            print(f"从文件加载理赔数据: {args.claim_file}")
            claims_df = pd.read_csv(args.claim_file, encoding='utf-8-sig')
            results = predict_batch(claims_df, model, preprocessor, feature_names)
            print("\n批量预测结果:")
            print(results.to_string(index=False))
            
            output_file = 'predictions.csv'
            results.to_csv(output_file, index=False, encoding='utf-8-sig')
            print(f"\n✓ 预测结果已保存到: {output_file}")
        else:
            print("测试单条理赔预测:")
            
            print("\n【正常理赔案例】")
            normal_claim = create_sample_claim()
            normal_result = predict_single_claim(normal_claim, model, preprocessor, feature_names)
            print(f"  欺诈概率: {normal_result['fraud_probability']:.4f}")
            print(f"  风险等级: {normal_result['risk_color']} {normal_result['risk_level']}")
            
            print("\n【疑似欺诈案例】")
            suspicious_claim = create_suspicious_claim()
            suspicious_result = predict_single_claim(suspicious_claim, model, preprocessor, feature_names)
            print(f"  欺诈概率: {suspicious_result['fraud_probability']:.4f}")
            print(f"  风险等级: {suspicious_result['risk_color']} {suspicious_result['risk_level']}")
    
    if args.mode in ['full', 'analyze']:
        print("\n📈 步骤4: 风险因子分析与分级决策建议 (SHAP)")
        print("-"*70)
        
        model, preprocessor, feature_names = load_model()
        train_df, test_df = load_data()
        X_test, y_test, _, _ = preprocess_data(test_df, is_train=False, preprocessor=preprocessor)
        
        analysis_results = analyze_risk_factors(model, X_test, feature_names)
        
        print("\n【🔴 高风险案例详细分析】")
        high_risk_claim = create_suspicious_claim()
        high_risk_result = analyze_single_claim(high_risk_claim, model, preprocessor, feature_names,
                                                analysis_results['explainer'], "HIGH_RISK_001")
        generate_tiered_decision(high_risk_result, high_risk_claim)
        
        print("\n【🟡 中风险案例详细分析】")
        medium_risk_claim = create_suspicious_claim()
        medium_risk_claim['past_fraud_count'] = 1
        medium_risk_claim['police_report'] = 1
        medium_risk_claim['fraud_indicators'] = 2
        medium_risk_result = analyze_single_claim(medium_risk_claim, model, preprocessor, feature_names,
                                                  analysis_results['explainer'], "MEDIUM_RISK_001")
        generate_tiered_decision(medium_risk_result, medium_risk_claim)
        
        print("\n【🟢 低风险案例详细分析】")
        normal_claim = create_sample_claim()
        normal_result = analyze_single_claim(normal_claim, model, preprocessor, feature_names,
                                             analysis_results['explainer'], "LOW_RISK_001")
        generate_tiered_decision(normal_result, normal_claim)
        
        save_shap_plots(analysis_results, X_test, feature_names)
    
    if args.mode in ['full', 'network']:
        print("\n🕸️  步骤5: 理赔网络分析 - 识别团伙欺诈")
        print("-"*70)
        
        full_path = 'data/claims_full.csv'
        if not os.path.exists(full_path):
            print("完整数据文件不存在，跳转到可解释性报告...")
        else:
            print("加载完整理赔数据进行网络分析...")
            df = pd.read_csv(full_path, encoding='utf-8-sig')
            print(f"加载 {len(df)} 条理赔记录")
            
            if 'fraud_probability' not in df.columns:
                print("\n为网络分析添加欺诈概率预测...")
                model, preprocessor, feature_names = load_model()
                
                fraud_probs = []
                batch_size = 1000
                for i in range(0, len(df), batch_size):
                    batch = df.iloc[i:i+batch_size]
                    X_batch, _, _, _ = preprocess_data(batch, is_train=False, preprocessor=preprocessor)
                    probs = model.predict_proba(X_batch)[:, 1]
                    fraud_probs.extend(probs)
                
                df['fraud_probability'] = fraud_probs
            
            analyzer, fraud_rings = analyze_network(df)
            
            print(f"\n✓ 网络分析完成")
            print(f"  - 发现 {len(fraud_rings)} 个潜在欺诈团伙")
            if fraud_rings:
                high_risk_rings = [r for r in fraud_rings if r['suspicion_score'] >= 0.5]
                print(f"  - 其中 {len(high_risk_rings)} 个为高风险团伙")
    
    if args.mode in ['full', 'interpretability']:
        print("\n📑 步骤6: 生成模型可解释性报告")
        print("-"*70)
        
        try:
            report_generator, feature_importance = generate_interpretability_report()
            print("✓ 可解释性报告已生成: reports/model_interpretability_report.txt")
        except Exception as e:
            print(f"可解释性报告生成跳过: {e}")
    
    if args.mode == 'simulator':
        print("\n🎯 启动理赔审核模拟系统")
        print("-"*70)
        run_simulator()
        return
    
    print("\n" + "="*70)
    print("✓ 所有步骤完成!")
    print("="*70)
    print("\n其他可用功能:")
    print("  python main.py --mode simulator   # 启动交互式模拟审核系统")
    print("  python review_simulator.py        # 独立运行模拟审核")
    print("  python network_analysis.py        # 独立运行网络分析")
    print("  python interpretability_report.py # 独立生成可解释性报告")


if __name__ == '__main__':
    main()
