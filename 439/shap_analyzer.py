import pandas as pd
import numpy as np
import shap
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import warnings
warnings.filterwarnings('ignore')

plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

from model_trainer import FEATURE_COLS


FEATURE_NAMES_CN = {
    'age': '年龄',
    'tenure_years': '在职年限',
    'salary': '薪资',
    'commute_distance_norm': '通勤距离(归一化)',
    'commute_distance': '通勤距离(km)',
    'late_rate_adjusted': '迟到率(修正后)',
    'late_rate_raw': '迟到率(原始)',
    'late_rate': '迟到率',
    'absent_rate': '缺勤率',
    'avg_overtime_hours': '平均加班时长',
    'avg_work_hours': '平均工作时长',
    'avg_internal_emails': '内部邮件均值',
    'avg_external_emails': '外部邮件均值',
    'avg_total_emails': '邮件总量均值',
    'avg_response_hours': '平均响应时间(小时)',
    'avg_completion_rate': '任务完成率',
    'avg_ontime_rate': '按时完成率',
    'avg_task_hours': '平均任务耗时',
    'satisfaction_score': '满意度评分',
    'work_life_balance_score': '工作生活平衡',
    'leadership_score': '领导满意度',
    'career_growth_score': '职业发展满意度',
    'compensation_score': '薪酬满意度',
    'overall_satisfaction': '综合满意度',
    'dept_encoded': '部门编码',
    'role_encoded': '职位编码',
    'level_encoded': '职级编码',
}


def compute_shap_values(model, X_scaled):
    explainer = shap.TreeExplainer(model)
    shap_values = explainer.shap_values(X_scaled)

    if isinstance(shap_values, list):
        shap_values = shap_values[1]

    return explainer, shap_values


def get_feature_shap_importance(shap_values, X_scaled):
    mean_abs_shap = np.abs(shap_values).mean(axis=0)
    importance_df = pd.DataFrame({
        'feature': FEATURE_COLS,
        'feature_cn': [FEATURE_NAMES_CN.get(f, f) for f in FEATURE_COLS],
        'mean_abs_shap': mean_abs_shap,
    }).sort_values('mean_abs_shap', ascending=False)

    return importance_df


def get_top_shap_features(shap_values, X_scaled, top_n=10):
    importance = get_feature_shap_importance(shap_values, X_scaled)
    return importance.head(top_n)


def get_employee_shap_contribution(explainer, X_scaled, employee_idx):
    shap_val = explainer.shap_values(X_scaled.iloc[[employee_idx]])

    if isinstance(shap_val, list):
        shap_val = shap_val[1]

    contribution_df = pd.DataFrame({
        'feature': FEATURE_COLS,
        'feature_cn': [FEATURE_NAMES_CN.get(f, f) for f in FEATURE_COLS],
        'feature_value': X_scaled.iloc[employee_idx].values,
        'shap_value': shap_val[0],
        'abs_shap': np.abs(shap_val[0]),
    }).sort_values('abs_shap', ascending=False)

    return contribution_df


def get_global_attrribution(importance_df, top_n=10):
    top = importance_df.head(top_n).copy()
    total = importance_df['mean_abs_shap'].sum()
    top['contribution_pct'] = top['mean_abs_shap'] / total * 100
    top['cumulative_pct'] = top['contribution_pct'].cumsum()
    return top


def get_risk_drivers_by_level(importance_df, risk_level):
    drivers = importance_df.copy()

    if risk_level in ['高风险', '中高风险']:
        key_drivers = drivers[drivers['feature'].isin([
            'satisfaction_score', 'career_growth_score', 'overall_satisfaction',
            'late_rate', 'absent_rate', 'avg_completion_rate'
        ])]
    elif risk_level in ['中低风险']:
        key_drivers = drivers[drivers['feature'].isin([
            'avg_overtime_hours', 'work_life_balance_score',
            'avg_response_hours', 'avg_internal_emails'
        ])]
    else:
        key_drivers = drivers.head(5)

    return key_drivers


def get_attrition_factor_summary(importance_df):
    factor_groups = {
        '工作态度': ['late_rate', 'absent_rate', 'avg_work_hours', 'avg_overtime_hours'],
        '工作绩效': ['avg_completion_rate', 'avg_ontime_rate', 'avg_task_hours'],
        '沟通频率': ['avg_internal_emails', 'avg_external_emails', 'avg_total_emails', 'avg_response_hours'],
        '满意度': ['satisfaction_score', 'overall_satisfaction', 'work_life_balance_score'],
        '职业发展': ['career_growth_score', 'leadership_score', 'compensation_score'],
        '个人背景': ['age', 'tenure_years', 'salary'],
    }

    group_importance = {}
    for group, features in factor_groups.items():
        relevant = importance_df[importance_df['feature'].isin(features)]
        group_importance[group] = relevant['mean_abs_shap'].sum()

    total = sum(group_importance.values())
    result = []
    for group, value in sorted(group_importance.items(), key=lambda x: x[1], reverse=True):
        result.append({
            'factor_group': group,
            'importance': value,
            'percentage': (value / total * 100) if total > 0 else 0,
        })

    return pd.DataFrame(result)


def generate_shap_plots(model, X_scaled, output_dir='.'):
    import os
    os.makedirs(output_dir, exist_ok=True)

    explainer, shap_values = compute_shap_values(model, X_scaled)

    plt.figure(figsize=(10, 8))
    shap_importance = get_feature_shap_importance(shap_values, X_scaled)
    top_features = shap_importance.head(15)

    colors = plt.cm.RdYlGn_r(np.linspace(0.2, 0.8, len(top_features)))
    bars = plt.barh(range(len(top_features)), top_features['mean_abs_shap'].values[::-1],
                    color=colors[::-1])
    plt.yticks(range(len(top_features)), top_features['feature_cn'].values[::-1])
    plt.xlabel('平均 |SHAP值| (特征影响力)')
    plt.title('特征归因分析 - 全局特征重要性')
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, 'shap_feature_importance.png'), dpi=150)
    plt.close()

    plt.figure(figsize=(12, 8))
    shap.summary_plot(shap_values, X_scaled, feature_names=[
        FEATURE_NAMES_CN.get(f, f) for f in FEATURE_COLS
    ], show=False, max_display=20)
    plt.title('SHAP Summary Plot - 离职风险特征归因')
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, 'shap_summary.png'), dpi=150)
    plt.close()

    factor_df = get_attrition_factor_summary(shap_importance)
    plt.figure(figsize=(10, 6))
    colors_pie = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4', '#FFEAA7', '#DDA0DD']
    plt.pie(factor_df['percentage'], labels=factor_df['factor_group'],
            autopct='%1.1f%%', colors=colors_pie[:len(factor_df)], startangle=90)
    plt.title('离职因素归因 - 分类占比')
    plt.axis('equal')
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, 'factor_attribution.png'), dpi=150)
    plt.close()

    return explainer, shap_values, shap_importance


def generate_employee_waterfall(explainer, X_scaled, employee_idx, employee_id, output_dir='.'):
    import os
    os.makedirs(output_dir, exist_ok=True)

    shap_val = explainer.shap_values(X_scaled.iloc[[employee_idx]])
    if isinstance(shap_val, list):
        shap_val = shap_val[1]

    base_value = explainer.expected_value
    if isinstance(base_value, list):
        base_value = base_value[1]

    contrib_df = get_employee_shap_contribution(explainer, X_scaled, employee_idx)

    plt.figure(figsize=(10, 8))
    top_contrib = contrib_df.head(10)
    top_contrib = top_contrib.iloc[::-1]

    colors = ['#FF6B6B' if v > 0 else '#4ECDC4' for v in top_contrib['shap_value']]
    plt.barh(range(len(top_contrib)), top_contrib['shap_value'].values, color=colors)
    plt.yticks(range(len(top_contrib)), top_contrib['feature_cn'].values)
    plt.xlabel('SHAP 值 (对离职概率的影响)')
    plt.title(f'员工 {employee_id} 离职风险归因分析')
    plt.axvline(x=0, color='gray', linestyle='--', alpha=0.5)
    plt.tight_layout()

    safe_id = str(employee_id).replace('/', '_')
    plt.savefig(os.path.join(output_dir, f'waterfall_{safe_id}.png'), dpi=150)
    plt.close()

    return contrib_df


if __name__ == '__main__':
    from data_generator import generate_all_data
    from model_trainer import build_features, train_model

    print("生成数据...")
    data = generate_all_data()

    print("构建特征...")
    df_features, encoders = build_features(data)

    print("训练模型...")
    model, scaler, X_train, X_test, y_train, y_test, feat_imp = train_model(df_features)

    X = df_features[FEATURE_COLS].copy()
    X_scaled = scaler.transform(X)
    X_scaled = pd.DataFrame(X_scaled, columns=FEATURE_COLS)

    print("计算SHAP值...")
    explainer, shap_values, shap_importance = generate_shap_plots(
        model, X_scaled, output_dir='shap_output'
    )

    print("全局归因分析:")
    print(shap_importance.head(10).to_string(index=False))

    print("\n离职因素汇总:")
    factor_df = get_attrition_factor_summary(shap_importance)
    print(factor_df.to_string(index=False))

    print("\n图表已保存到 shap_output/ 目录")