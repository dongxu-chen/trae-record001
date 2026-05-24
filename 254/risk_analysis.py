import numpy as np
import pandas as pd
import os
import shap
import matplotlib.pyplot as plt
from matplotlib import font_manager
import warnings
warnings.filterwarnings('ignore')
from train_model import load_model, preprocess_data, load_data
from predict import create_suspicious_claim, create_sample_claim


def analyze_risk_factors(model, X_test, feature_names, top_n=20):
    print("\n" + "="*60)
    print("RISK FACTOR ANALYSIS USING SHAP")
    print("="*60)
    
    explainer = shap.TreeExplainer(model)
    
    shap_values = explainer.shap_values(X_test)
    
    if isinstance(shap_values, list):
        shap_values = shap_values[1]
    
    print("\n1. Global Feature Importance (Top 20)")
    print("-" * 60)
    
    mean_abs_shap = np.mean(np.abs(shap_values), axis=0)
    feature_importance = pd.DataFrame({
        'feature': feature_names[:len(mean_abs_shap)],
        'mean_abs_shap_value': mean_abs_shap
    }).sort_values('mean_abs_shap_value', ascending=False)
    
    print(feature_importance.head(top_n).to_string(index=False))
    
    print("\n2. Top Risk Factors with Direction")
    print("-" * 60)
    
    mean_shap = np.mean(shap_values, axis=0)
    feature_direction = pd.DataFrame({
        'feature': feature_names[:len(mean_shap)],
        'mean_shap_value': mean_shap,
        'mean_abs_shap_value': mean_abs_shap
    }).sort_values('mean_abs_shap_value', ascending=False)
    
    feature_direction['risk_direction'] = feature_direction['mean_shap_value'].apply(
        lambda x: '增加欺诈风险' if x > 0 else '降低欺诈风险'
    )
    
    print(feature_direction[['feature', 'mean_shap_value', 'risk_direction', 'mean_abs_shap_value']].head(top_n).to_string(index=False))
    
    return {
        'shap_values': shap_values,
        'explainer': explainer,
        'feature_importance': feature_importance,
        'feature_direction': feature_direction
    }


def analyze_single_claim(claim_data, model, preprocessor, feature_names, explainer, claim_id="Unknown", output_dir='plots'):
    print(f"\n" + "="*60)
    print(f"DETAILED RISK ANALYSIS FOR CLAIM: {claim_id}")
    print("="*60)
    
    if isinstance(claim_data, dict):
        claim_df = pd.DataFrame([claim_data])
    else:
        claim_df = claim_data
    
    X_processed, _, _, _ = preprocess_data(claim_df, is_train=False, preprocessor=preprocessor)
    
    fraud_prob = model.predict_proba(X_processed)[0, 1]
    
    if fraud_prob >= 0.7:
        risk_level = "高风险"
        color = "🔴"
    elif fraud_prob >= 0.4:
        risk_level = "中风险"
        color = "🟡"
    else:
        risk_level = "低风险"
        color = "🟢"
    
    print(f"\n欺诈概率: {fraud_prob:.4f}")
    print(f"风险等级: {color} {risk_level}")
    
    shap_values_single = explainer.shap_values(X_processed)
    if isinstance(shap_values_single, list):
        shap_values_single = shap_values_single[1]
    
    base_value = explainer.expected_value
    if isinstance(base_value, list):
        base_value = base_value[1]
    
    print(f"\n基准预测值 (Base Value): {base_value:.4f}")
    print(f"模型预测值 (Model Output): {base_value + shap_values_single.sum():.4f}")
    
    shap_df = pd.DataFrame({
        'feature': feature_names[:shap_values_single.shape[1]],
        'shap_value': shap_values_single[0],
        'feature_value': X_processed[0]
    })
    
    shap_df['abs_shap'] = shap_df['shap_value'].abs()
    shap_df = shap_df.sort_values('abs_shap', ascending=False)
    
    print(f"\n3. Top 10 风险驱动因子:")
    print("-" * 60)
    
    for _, row in shap_df.head(10).iterrows():
        impact = "增加风险" if row['shap_value'] > 0 else "降低风险"
        print(f"{row['feature']:35s} | SHAP: {row['shap_value']:+.4f} | {impact}")
    
    risk_drivers = shap_df[shap_df['shap_value'] > 0].head(5)
    risk_mitigators = shap_df[shap_df['shap_value'] < 0].head(5)
    
    print(f"\n4. SHAP Force Plot 可视化")
    print("-" * 60)
    force_plot_path = save_force_plot(explainer, shap_values_single, X_processed, feature_names, claim_id, output_dir)
    print(f"   Force Plot 已保存: {force_plot_path}")
    
    return {
        'fraud_probability': fraud_prob,
        'risk_level': risk_level,
        'risk_color': color,
        'shap_values': shap_values_single,
        'base_value': base_value,
        'top_risk_drivers': risk_drivers,
        'top_risk_mitigators': risk_mitigators,
        'force_plot_path': force_plot_path
    }


def save_force_plot(explainer, shap_values_single, X_processed, feature_names, claim_id, output_dir='plots'):
    os.makedirs(output_dir, exist_ok=True)
    
    base_value = explainer.expected_value
    if isinstance(base_value, list):
        base_value = base_value[1]
    
    try:
        top_features = 15
        abs_shap = np.abs(shap_values_single[0])
        top_indices = np.argsort(abs_shap)[-top_features:][::-1]
        
        shap_values_top = shap_values_single[0][top_indices]
        features_top = [feature_names[i] for i in top_indices]
        X_top = X_processed[0][top_indices]
        
        fig, ax = plt.subplots(figsize=(14, 8))
        
        y_pos = np.arange(len(shap_values_top))
        
        colors = ['#ff6b6b' if v > 0 else '#4ecdc4' for v in shap_values_top]
        
        bars = ax.barh(y_pos, shap_values_top, color=colors, height=0.7)
        
        ax.set_yticks(y_pos)
        ax.set_yticklabels(features_top, fontsize=10)
        ax.set_xlabel('SHAP Value (Impact on Fraud Probability)', fontsize=12)
        ax.set_title(f'Factor Contribution Analysis - Claim {claim_id}\n(Red = Increase Fraud Risk, Green = Decrease Fraud Risk)', fontsize=14, fontweight='bold')
        
        ax.axvline(x=0, color='black', linestyle='--', linewidth=1, alpha=0.7)
        
        for i, (bar, val) in enumerate(zip(bars, shap_values_top)):
            width = bar.get_width()
            ha = 'left' if width >= 0 else 'right'
            ax.text(width + (0.05 if width >= 0 else -0.05), i, f'{val:+.3f}', 
                    ha=ha, va='center', fontsize=9, fontweight='bold')
        
        ax.grid(axis='x', alpha=0.3)
        ax.invert_yaxis()
        
        plt.tight_layout()
        
        safe_claim_id = claim_id.replace('/', '_').replace('\\', '_')
        plot_path = f'{output_dir}/force_plot_{safe_claim_id}.png'
        plt.savefig(plot_path, dpi=150, bbox_inches='tight')
        plt.close()
        
        return plot_path
    except Exception as e:
        print(f"   ⚠️ Force plot generation failed: {e}")
        return None


def generate_tiered_decision(analysis_result, claim_data):
    print("\n" + "="*60)
    print("TIERED DECISION WORKFLOW")
    print("分级决策流程")
    print("="*60)
    
    fraud_prob = analysis_result['fraud_probability']
    risk_level = analysis_result['risk_level']
    risk_drivers = analysis_result['top_risk_drivers']
    risk_mitigators = analysis_result['top_risk_mitigators']
    
    print(f"\n风险评估: {analysis_result['risk_color']} {risk_level} (欺诈概率: {fraud_prob:.2%})")
    
    workflow = {
        'tier': risk_level,
        'workflow_steps': [],
        'auto_approved': False,
        'requires_investigation': False,
        'requires_on_site': False
    }
    
    if risk_level == "高风险":
        workflow['requires_investigation'] = True
        workflow['requires_on_site'] = True
        workflow['workflow_steps'] = [
            ("LEVEL 4 - 高风险处理流程", "header"),
            ("", ""),
            ("🔴 第一步: 自动拦截", "系统自动标记为高风险，暂停理赔流程"),
            ("", ""),
            ("🔴 第二步: 指派调查员", "指派专职理赔调查员，24小时内响应"),
            ("", ""),
            ("🔴 第三步: 现场查勘", "必须进行现场查勘，核实事故真实性"),
            ("   - 勘查事故现场，拍摄照片、测量痕迹", "必做"),
            ("   - 调取周边监控录像", "必做"),
            ("   - 比对车辆损失与事故描述一致性", "必做"),
            ("", ""),
            ("🔴 第四步: 文档核查", "全面核实所有证明文件"),
            ("   - 联系医疗机构核实医疗记录真实性", "必做"),
            ("   - 核实修车发票真伪，联系维修厂", "必做"),
            ("   - 核查警方报告真实性", "必做"),
            ("   - 比对历史理赔记录", "必做"),
            ("", ""),
            ("🔴 第五步: 当事人约谈", "约谈当事人和目击者，制作笔录"),
            ("   - 询问事故经过细节，核实时间线一致性", "必做"),
            ("   - 如有矛盾，进行二次约谈", "可选"),
            ("", ""),
            ("🔴 第六步: 集体审议", "提交理赔审议委员会讨论"),
            ("   - 欺诈嫌疑较大的，予以拒赔并保留追诉权", "决策"),
            ("   - 证据不足的，要求补充材料后再审", "决策"),
            ("   - 排除嫌疑的，升级为中风险流程", "决策"),
        ]
        
        if isinstance(claim_data, dict) and claim_data.get('past_fraud_count', 0) > 0:
            workflow['workflow_steps'].append(("", ""))
            workflow['workflow_steps'].append(("⚠️ 重点关注", "申请人有历史欺诈记录，需从严审查"))
        
        if isinstance(claim_data, dict) and not claim_data.get('police_report', 1):
            workflow['workflow_steps'].append(("⚠️ 重点关注", "缺少警方报告，需核实事故真实性"))
        
        if isinstance(claim_data, dict) and not claim_data.get('witness_present', 1):
            workflow['workflow_steps'].append(("⚠️ 重点关注", "无现场目击者，需重点核实"))
    
    elif risk_level == "中风险":
        workflow['requires_investigation'] = True
        workflow['requires_on_site'] = False
        workflow['workflow_steps'] = [
            ("LEVEL 2-3 - 中风险常规审核", "header"),
            ("", ""),
            ("🟡 第一步: 标准审核", "进入常规人工审核队列"),
            ("", ""),
            ("🟡 第二步: 文档审核", "审核人员全面审核理赔材料"),
            ("   - 核对所有证明文件完整性", "必做"),
            ("   - 验证医疗费用合理性（与当地医疗水平比对）", "必做"),
            ("   - 验证修车费用合理性（与车型、配件价格比对）", "必做"),
            ("   - 交叉核对历史理赔记录", "必做"),
            ("", ""),
            ("🟡 第三步: 风险点核查", "针对风险因子进行重点核查"),
            ("   - 对Top 3风险驱动因子逐一核实", "必做"),
            ("   - 如有疑问，电话联系申请人确认", "必做"),
            ("", ""),
            ("🟡 第四步: 补充材料", "材料缺失或存疑时要求补充"),
            ("   - 要求提供警方报告（如缺失）", "可选"),
            ("   - 要求提供详细医疗明细", "可选"),
            ("   - 要求提供车辆维修明细", "可选"),
            ("", ""),
            ("🟡 第五步: 审核决策", "根据审核结果作出决定"),
            ("   - 材料完整、无疑问 → 审核通过，安排付款", "决策"),
            ("   - 存疑但无法核实 → 升级至高风险流程", "决策"),
            ("   - 发现欺诈线索 → 直接拒赔", "决策"),
        ]
    
    else:
        workflow['auto_approved'] = True
        workflow['requires_investigation'] = False
        workflow['requires_on_site'] = False
        workflow['workflow_steps'] = [
            ("LEVEL 1 - 低风险自动通过", "header"),
            ("", ""),
            ("🟢 第一步: 自动审核通过", "系统自动审核通过，无需人工干预"),
            ("", ""),
            ("🟢 第二步: 快速理赔通道", "进入快速理赔流程"),
            ("   - 自动生成赔付通知书", "系统自动"),
            ("   - 财务自动安排付款（T+1到账）", "系统自动"),
            ("", ""),
            ("🟢 第三步: 事后抽检", "按比例进行事后抽检监控"),
            ("   - 系统随机抽取5%进行复核", "定期"),
            ("   - 如发现问题，追溯调整风险等级", "触发"),
            ("", ""),
            ("🟢 第四步: 客户通知", "自动发送理赔完成通知"),
            ("   - 短信通知赔付金额和到账时间", "系统自动"),
            ("   - 提供电子保单和理赔凭证下载", "系统自动"),
        ]
    
    print("\n" + "="*60)
    print("决策流程:")
    print("="*60)
    
    for step, detail in workflow['workflow_steps']:
        if detail == "header":
            print(f"\n{'='*60}")
            print(f"  {step}")
            print(f"{'='*60}")
        elif step == "" and detail == "":
            print()
        else:
            if detail:
                print(f"  {step:<50s} [{detail}]")
            else:
                print(f"  {step}")
    
    print("\n" + "="*60)
    print("关键风险因子 (Risk Drivers):")
    print("="*60)
    for _, row in risk_drivers.head(5).iterrows():
        print(f"  ⚠️ {row['feature']:<35s} SHAP = {row['shap_value']:+.4f}")
    
    if not risk_mitigators.empty:
        print("\n风险缓解因子 (Risk Mitigators):")
        for _, row in risk_mitigators.head(3).iterrows():
            print(f"  ✅ {row['feature']:<35s} SHAP = {row['shap_value']:+.4f}")
    
    print(f"\n{'='*60}")
    if workflow['auto_approved']:
        print("  ✅ 结论: 自动通过，快速理赔")
    elif workflow['requires_on_site']:
        print("  🔴 结论: 需现场查勘，深入调查")
    else:
        print("  🟡 结论: 常规审核，人工处理")
    print(f"{'='*60}")
    
    return workflow


def save_shap_plots(analysis_results, X_test, feature_names, output_dir='plots'):
    os.makedirs(output_dir, exist_ok=True)
    
    shap_values = analysis_results['shap_values']
    explainer = analysis_results['explainer']
    
    try:
        plt.figure(figsize=(12, 8))
        shap.summary_plot(shap_values, X_test, feature_names=feature_names[:shap_values.shape[1]], 
                         show=False, plot_size=(12, 8))
        plt.tight_layout()
        plt.savefig(f'{output_dir}/shap_summary.png', dpi=150, bbox_inches='tight')
        plt.close()
        print(f"\nSHAP summary plot saved to {output_dir}/shap_summary.png")
    except Exception as e:
        print(f"\nCould not save SHAP summary plot: {e}")
    
    try:
        plt.figure(figsize=(10, 8))
        shap_importance = pd.DataFrame({
            'feature': feature_names[:shap_values.shape[1]],
            'importance': np.mean(np.abs(shap_values), axis=0)
        }).sort_values('importance', ascending=True).tail(20)
        
        plt.barh(shap_importance['feature'], shap_importance['importance'], color='#4a90e2')
        plt.xlabel('Mean |SHAP Value|')
        plt.title('Top 20 Feature Importance (Global)')
        plt.tight_layout()
        plt.savefig(f'{output_dir}/feature_importance.png', dpi=150, bbox_inches='tight')
        plt.close()
        print(f"Feature importance plot saved to {output_dir}/feature_importance.png")
    except Exception as e:
        print(f"Could not save feature importance plot: {e}")


def main():
    if not os.path.exists('models/xgboost_model.pkl'):
        print("Model not found. Training model first...")
        from train_model import main as train_main
        train_main()
    
    print("Loading model and data...")
    model, preprocessor, feature_names = load_model()
    train_df, test_df = load_data()
    
    X_test, y_test, _, _ = preprocess_data(test_df, is_train=False, preprocessor=preprocessor)
    
    analysis_results = analyze_risk_factors(model, X_test, feature_names)
    
    print("\n" + "="*60)
    print("ANALYZING HIGH RISK CLAIM")
    print("="*60)
    suspicious_claim = create_suspicious_claim()
    suspicious_result = analyze_single_claim(suspicious_claim, model, preprocessor, feature_names, 
                                             analysis_results['explainer'], "HIGH_RISK_001")
    generate_tiered_decision(suspicious_result, suspicious_claim)
    
    print("\n" + "="*60)
    print("ANALYZING MEDIUM RISK CLAIM")
    print("="*60)
    medium_claim = create_suspicious_claim()
    medium_claim['past_fraud_count'] = 1
    medium_claim['police_report'] = 1
    medium_claim['fraud_indicators'] = 2
    medium_result = analyze_single_claim(medium_claim, model, preprocessor, feature_names,
                                         analysis_results['explainer'], "MEDIUM_RISK_001")
    generate_tiered_decision(medium_result, medium_claim)
    
    print("\n" + "="*60)
    print("ANALYZING LOW RISK CLAIM")
    print("="*60)
    normal_claim = create_sample_claim()
    normal_result = analyze_single_claim(normal_claim, model, preprocessor, feature_names,
                                         analysis_results['explainer'], "LOW_RISK_001")
    generate_tiered_decision(normal_result, normal_claim)
    
    save_shap_plots(analysis_results, X_test, feature_names)
    
    return analysis_results, suspicious_result, normal_result


if __name__ == '__main__':
    main()
