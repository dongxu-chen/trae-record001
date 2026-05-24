import pandas as pd
import numpy as np
import shap
import os
from train_model import load_model, load_data, preprocess_data
from collections import defaultdict


FEATURE_BUSINESS_MEANING = {
    'past_fraud_count': {
        'name': '历史欺诈次数',
        'description': '申请人过去的理赔欺诈记录次数',
        'business_impact': '有历史欺诈记录的申请人再次欺诈的概率显著升高，是最重要的风险指标',
        'high_risk': '历史欺诈次数 ≥ 1',
        'low_risk': '历史欺诈次数 = 0',
        'recommendation': '对有历史欺诈记录的申请人，需进行严格审核和深入调查'
    },
    'medical_expense': {
        'name': '医疗费用',
        'description': '理赔申请中申报的医疗费用金额',
        'business_impact': '医疗费用异常偏高是重要的欺诈信号，可能存在虚报费用',
        'high_risk': '医疗费用超过同类型事故平均水平的1.5倍',
        'low_risk': '医疗费用在正常范围内波动',
        'recommendation': '核实医疗费用明细，联系医疗机构确认费用真实性'
    },
    'vehicle_repair_cost': {
        'name': '车辆维修费用',
        'description': '理赔申请中申报的车辆维修费用',
        'business_impact': '维修费用与车辆价值、损失程度不匹配时，存在欺诈风险',
        'high_risk': '维修费用超过车辆价值的50%或明显高于市场行情',
        'low_risk': '维修费用与车辆损失程度相匹配',
        'recommendation': '要求提供详细维修清单，核实配件价格合理性'
    },
    'past_claims_count': {
        'name': '历史理赔次数',
        'description': '申请人过去的理赔申请总次数',
        'business_impact': '频繁理赔可能表明高风险驾驶行为或故意制造事故',
        'high_risk': '过去1年内理赔次数 ≥ 3次',
        'low_risk': '过去1年内理赔次数 ≤ 1次',
        'recommendation': '对频繁理赔的申请人加强风险监控'
    },
    'past_claims_total': {
        'name': '历史理赔总金额',
        'description': '申请人过去所有理赔的总金额',
        'business_impact': '历史理赔金额过高可能存在道德风险',
        'high_risk': '历史理赔总金额超过保费的5倍',
        'low_risk': '历史理赔总金额在合理范围内',
        'recommendation': '结合理赔次数综合评估风险'
    },
    'medical_invoice': {
        'name': '医疗发票',
        'description': '是否提供了真实有效的医疗发票',
        'business_impact': '无法提供医疗发票或发票伪造是欺诈的典型特征',
        'high_risk': '未提供医疗发票或发票存疑',
        'low_risk': '提供正规医疗发票且可核实',
        'recommendation': '核实发票真伪，必要时联系开票机构确认'
    },
    'witness_present': {
        'name': '现场目击者',
        'description': '事故发生时是否有第三方目击者',
        'business_impact': '无目击者的单方事故欺诈风险显著高于有目击者的事故',
        'high_risk': '无现场目击者',
        'low_risk': '有独立第三方目击者',
        'recommendation': '无目击者时需重点核实事故真实性'
    },
    'police_report': {
        'name': '警方报告',
        'description': '是否向警方报案并取得事故认定书',
        'business_impact': '故意制造事故或虚假理赔通常不会向警方报案',
        'high_risk': '未报警或无法提供警方事故认定书',
        'low_risk': '已报警并取得正规事故认定书',
        'recommendation': '核实警方报告真实性，必要时联系交警部门确认'
    },
    'total_claim_amount': {
        'name': '理赔总金额',
        'description': '本次理赔申请的总金额',
        'business_impact': '理赔金额与保险金额、实际损失不匹配时存在欺诈风险',
        'high_risk': '理赔金额接近或超过保险金额',
        'low_risk': '理赔金额在合理损失范围内',
        'recommendation': '评估理赔金额合理性，与同类案例对比'
    },
    'claim_amount': {
        'name': '实际赔付金额',
        'description': '扣除免赔额后的实际赔付金额',
        'business_impact': '赔付金额是保险公司的实际损失，需重点审核',
        'high_risk': '赔付金额显著高于类似案例',
        'low_risk': '赔付金额在预期范围内',
        'recommendation': '确保赔付金额计算正确，无超额赔付'
    },
    'claim_ratio': {
        'name': '赔付率',
        'description': '理赔金额与保费的比率',
        'business_impact': '高赔付率表明可能存在逆向选择或道德风险',
        'high_risk': '赔付率 > 300%',
        'low_risk': '赔付率 < 100%',
        'recommendation': '高赔付率案例需重点审核'
    },
    'expense_to_value_ratio': {
        'name': '费用价值比',
        'description': '理赔金额与车辆价值的比率',
        'business_impact': '维修费用接近或超过车辆价值时，可能存在故意制造事故骗取全损赔付',
        'high_risk': '费用价值比 > 50%',
        'low_risk': '费用价值比 < 30%',
        'recommendation': '评估车辆是否值得维修，是否存在全损欺诈'
    },
    'same_day_claim': {
        'name': '当日理赔',
        'description': '是否在事故发生当天就提出理赔申请',
        'business_impact': '事故当天立即申请理赔可能是预谋欺诈的特征',
        'high_risk': '事故当天申请理赔',
        'low_risk': '事故后3天以上申请理赔',
        'recommendation': '当日理赔案例需核查事故时间线'
    },
    'high_value_ratio': {
        'name': '高价值比率',
        'description': '理赔金额是否超过车辆价值的50%',
        'business_impact': '高价值比率可能表明故意损坏高价值车辆骗取保险金',
        'high_risk': '是',
        'low_risk': '否',
        'recommendation': '对高价值比率案例进行深度调查'
    },
    'suspicious_time': {
        'name': '可疑时间',
        'description': '事故是否发生在夜间/晚高峰且天气良好',
        'business_impact': '夜间、无目击者、天气良好时的单方事故欺诈风险高',
        'high_risk': '夜间或晚高峰、天气晴朗',
        'low_risk': '日间、恶劣天气',
        'recommendation': '可疑时间发生的事故需核实真实性'
    },
    'fraud_indicators': {
        'name': '欺诈指标数',
        'description': '该理赔案例符合的欺诈特征数量',
        'business_impact': '多个欺诈特征同时出现时，欺诈概率呈指数级上升',
        'high_risk': '欺诈指标数 ≥ 3',
        'low_risk': '欺诈指标数 = 0',
        'recommendation': '根据欺诈指标数量调整审核等级'
    },
    'photos_provided': {
        'name': '现场照片',
        'description': '是否提供事故现场照片',
        'business_impact': '无法提供现场照片或照片与事故描述不符是重要信号',
        'high_risk': '未提供现场照片',
        'low_risk': '提供多角度现场照片',
        'recommendation': '审核照片真实性，检查是否有PS痕迹或旧照片复用'
    },
    'repair_invoice': {
        'name': '维修发票',
        'description': '是否提供车辆维修发票',
        'business_impact': '伪造维修发票是车险欺诈的常见手段',
        'high_risk': '未提供维修发票或发票异常',
        'low_risk': '提供正规维修厂发票',
        'recommendation': '核实维修厂资质和发票真伪'
    },
    'hospital_days': {
        'name': '住院天数',
        'description': '伤者住院治疗的天数',
        'business_impact': '住院天数与伤情不符可能存在挂床骗保',
        'high_risk': '住院天数明显超过伤情需要',
        'low_risk': '住院天数与诊断相符',
        'recommendation': '核实住院记录和医嘱，检查是否存在挂床'
    },
    'disability_level': {
        'name': '伤残等级',
        'description': '伤者的伤残评定等级',
        'business_impact': '伪造或夸大伤残等级是人身险欺诈的常见方式',
        'high_risk': '高伤残等级但缺乏客观医学证据',
        'low_risk': '伤残等级有充分医学证明支持',
        'recommendation': '要求提供完整的伤残鉴定报告，必要时重新鉴定'
    }
}


class ModelInterpretabilityReport:
    def __init__(self, model, preprocessor, feature_names, X_test, y_test):
        self.model = model
        self.preprocessor = preprocessor
        self.feature_names = feature_names
        self.X_test = X_test
        self.y_test = y_test
        self.explainer = shap.TreeExplainer(model)
        self.shap_values = self.explainer.shap_values(X_test)
        
        if isinstance(self.shap_values, list):
            self.shap_values = self.shap_values[1]
    
    def generate_feature_report(self, top_n=20):
        print("\n" + "="*80)
        print("MODEL INTERPRETABILITY REPORT")
        print("模型可解释性报告")
        print("="*80)
        
        mean_abs_shap = np.mean(np.abs(self.shap_values), axis=0)
        mean_shap = np.mean(self.shap_values, axis=0)
        
        feature_importance = pd.DataFrame({
            'feature': self.feature_names[:len(mean_abs_shap)],
            'mean_abs_shap': mean_abs_shap,
            'mean_shap': mean_shap
        }).sort_values('mean_abs_shap', ascending=False)
        
        base_features = []
        for _, row in feature_importance.head(top_n).iterrows():
            feature_name = row['feature']
            base_name = feature_name.split('_')[0] if '_' in feature_name else feature_name
            
            if base_name in FEATURE_BUSINESS_MEANING:
                base_features.append(base_name)
            elif feature_name in FEATURE_BUSINESS_MEANING:
                base_features.append(feature_name)
        
        base_features = list(dict.fromkeys(base_features))[:10]
        
        print(f"\n1. TOP {len(base_features)} RISK FACTORS - BUSINESS INTERPRETATION")
        print("-"*80)
        
        for i, feature_key in enumerate(base_features, 1):
            info = FEATURE_BUSINESS_MEANING.get(feature_key, {})
            if not info:
                continue
            
            matching_rows = feature_importance[feature_importance['feature'].str.contains(feature_key, case=False)]
            if not matching_rows.empty:
                shap_value = matching_rows.iloc[0]['mean_abs_shap']
                direction = "增加风险" if matching_rows.iloc[0]['mean_shap'] > 0 else "降低风险"
            else:
                shap_value = 0
                direction = "N/A"
            
            print(f"\n{i}. {info.get('name', feature_key)} (SHAP: {shap_value:.4f}, {direction})")
            print("   " + "-"*60)
            print(f"   描述: {info.get('description', 'N/A')}")
            print(f"   业务影响: {info.get('business_impact', 'N/A')}")
            print(f"   高风险特征: {info.get('high_risk', 'N/A')}")
            print(f"   低风险特征: {info.get('low_risk', 'N/A')}")
            print(f"   审核建议: {info.get('recommendation', 'N/A')}")
        
        print(f"\n" + "="*80)
        print("2. RISK THRESHOLD GUIDELINES")
        print("风险阈值参考")
        print("-"*80)
        
        thresholds = [
            ("🔴 高风险", "≥ 70%", "启动深入调查，现场查勘"),
            ("🟡 中风险", "40% - 70%", "常规人工审核，重点核查"),
            ("🟢 低风险", "< 40%", "自动审核通过，快速理赔")
        ]
        
        print(f"\n{'风险等级':<15} {'欺诈概率':<15} {'处理建议'}")
        print("-"*80)
        for level, prob, action in thresholds:
            print(f"{level:<15} {prob:<15} {action}")
        
        print(f"\n" + "="*80)
        print("3. FRAUD INDICATOR CHECKLIST")
        print("欺诈指标核查清单")
        print("-"*80)
        
        indicators = [
            ("📋 文档完整性", [
                "□ 警方事故报告",
                "□ 现场照片（多角度）",
                "□ 医疗发票和明细",
                "□ 维修发票和清单",
                "□ 驾驶证、行驶证",
                "□ 保险单"
            ]),
            ("🔍 真实性核查", [
                "□ 核实事故时间、地点合理性",
                "□ 比对历史理赔记录",
                "□ 核实报案人身份",
                "□ 检查照片是否有PS痕迹",
                "□ 核实医院/维修厂资质"
            ]),
            ("⚠️  风险信号", [
                "□ 历史欺诈记录",
                "□ 频繁理赔（≥3次/年）",
                "□ 无现场目击者",
                "□ 未报警",
                "□ 夜间单方事故",
                "□ 理赔金额异常偏高",
                "□ 多方信息不一致"
            ])
        ]
        
        for category, items in indicators:
            print(f"\n{category}")
            for item in items:
                print(f"  {item}")
        
        return feature_importance
    
    def generate_complete_report(self, output_file='reports/model_interpretability_report.txt'):
        os.makedirs('reports', exist_ok=True)
        
        feature_importance = self.generate_feature_report()
        
        report_lines = []
        report_lines.append("="*80)
        report_lines.append("INSURANCE FRAUD DETECTION MODEL - INTERPRETABILITY REPORT")
        report_lines.append("保险理赔欺诈检测模型 - 可解释性报告")
        report_lines.append("="*80)
        report_lines.append(f"Generated on: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        report_lines.append(f"\n1. MODEL PERFORMANCE")
        report_lines.append("-"*80)
        
        y_pred = self.model.predict(self.X_test)
        y_pred_proba = self.model.predict_proba(self.X_test)[:, 1]
        
        from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, roc_auc_score
        report_lines.append(f"Accuracy:    {accuracy_score(self.y_test, y_pred):.4f}")
        report_lines.append(f"Precision:   {precision_score(self.y_test, y_pred):.4f}")
        report_lines.append(f"Recall:      {recall_score(self.y_test, y_pred):.4f}")
        report_lines.append(f"F1 Score:    {f1_score(self.y_test, y_pred):.4f}")
        report_lines.append(f"ROC-AUC:     {roc_auc_score(self.y_test, y_pred_proba):.4f}")
        
        report_lines.append(f"\n2. FEATURE IMPORTANCE (TOP 20)")
        report_lines.append("-"*80)
        
        for i, (_, row) in enumerate(feature_importance.head(20).iterrows(), 1):
            direction = "↑" if row['mean_shap'] > 0 else "↓"
            report_lines.append(f"{i:2d}. {row['feature']:<45s} | SHAP: {row['mean_abs_shap']:.4f} {direction}")
        
        report_lines.append(f"\n3. RISK FACTOR BUSINESS INTERPRETATION")
        report_lines.append("-"*80)
        
        for feature_key, info in FEATURE_BUSINESS_MEANING.items():
            matching_rows = feature_importance[feature_importance['feature'].str.contains(feature_key, case=False)]
            if matching_rows.empty:
                continue
            
            shap_value = matching_rows.iloc[0]['mean_abs_shap']
            direction = "增加风险" if matching_rows.iloc[0]['mean_shap'] > 0 else "降低风险"
            
            report_lines.append(f"\n【{info['name']}】")
            report_lines.append(f"  SHAP重要性: {shap_value:.4f} ({direction})")
            report_lines.append(f"  描述: {info['description']}")
            report_lines.append(f"  业务影响: {info['business_impact']}")
            report_lines.append(f"  高风险: {info['high_risk']}")
            report_lines.append(f"  低风险: {info['low_risk']}")
            report_lines.append(f"  建议: {info['recommendation']}")
        
        report_text = "\n".join(report_lines)
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(report_text)
        
        print(f"\n\nComplete report saved to: {output_file}")
        
        return feature_importance


def generate_interpretability_report():
    print("Loading model and data...")
    model, preprocessor, feature_names = load_model()
    train_df, test_df = load_data()
    
    X_test, y_test, _, _ = preprocess_data(test_df, is_train=False, preprocessor=preprocessor)
    
    report_generator = ModelInterpretabilityReport(model, preprocessor, feature_names, X_test, y_test)
    
    feature_importance = report_generator.generate_complete_report()
    
    return report_generator, feature_importance


if __name__ == '__main__':
    generate_interpretability_report()
