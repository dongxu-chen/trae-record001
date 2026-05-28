import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.preprocessing import LabelEncoder, StandardScaler, MinMaxScaler
from sklearn.metrics import classification_report, roc_auc_score
import joblib
import warnings
warnings.filterwarnings('ignore')


FEATURE_COLS = [
    'age', 'tenure_years', 'salary', 'commute_distance_norm',
    'late_rate_adjusted', 'late_rate_raw', 'absent_rate',
    'avg_overtime_hours', 'avg_work_hours',
    'avg_internal_emails', 'avg_external_emails', 'avg_total_emails',
    'avg_response_hours',
    'avg_completion_rate', 'avg_ontime_rate', 'avg_task_hours',
    'satisfaction_score', 'work_life_balance_score', 'leadership_score',
    'career_growth_score', 'compensation_score', 'overall_satisfaction',
    'dept_encoded', 'role_encoded', 'level_encoded',
]


def build_features(data):
    df_emp = data['employees'].copy()
    df_att = data['attendance'].copy()
    df_email = data['emails'].copy()
    df_task = data['tasks'].copy()
    df_survey = data['surveys'].copy()

    att_stats = df_att.groupby('employee_id').agg(
        late_count=('status', lambda x: (x == '迟到').sum()),
        absent_count=('status', lambda x: (x == '缺勤').sum()),
        total_days=('status', 'count'),
        avg_overtime_hours=('overtime_hours', 'mean'),
        avg_work_hours=('work_hours', 'mean'),
    ).reset_index()
    att_stats['late_rate_raw'] = att_stats['late_count'] / att_stats['total_days']
    att_stats['absent_rate'] = att_stats['absent_count'] / att_stats['total_days']
    att_stats = att_stats.drop(columns=['late_count', 'absent_count', 'total_days'])

    cols_to_drop = ['late_rate_raw', 'late_rate_adjusted', 'commute_factor']
    df_emp = df_emp.drop(columns=[c for c in cols_to_drop if c in df_emp.columns], errors='ignore')

    df = df_emp.merge(att_stats, on='employee_id', how='left')

    commute_scaler = MinMaxScaler()
    df['commute_distance_norm'] = commute_scaler.fit_transform(
        df[['commute_distance']]
    )

    df['late_rate_adjusted'] = df.apply(
        lambda row: max(0, row.get('late_rate_raw', 0) - row['commute_distance_norm'] * 0.08),
        axis=1
    )

    if 'is_pre_holiday' in df_email.columns:
        df_email_workday = df_email[df_email['is_pre_holiday'] == False]
    else:
        df_email_workday = df_email

    email_stats = df_email_workday.groupby('employee_id').agg(
        avg_internal_emails=('internal_emails', 'mean'),
        avg_external_emails=('external_emails', 'mean'),
        avg_total_emails=('total_emails', 'mean'),
        avg_response_hours=('avg_response_hours', 'mean'),
    ).reset_index()

    email_baseline = {
        'total_emails': df_email_workday['total_emails'].mean(),
        'response_hours': df_email_workday['avg_response_hours'].mean(),
    }

    task_stats = df_task.groupby('employee_id').agg(
        avg_completion_rate=('completion_rate', 'mean'),
        avg_ontime_rate=('on_time_rate', 'mean'),
        avg_task_hours=('avg_task_hours', 'mean'),
    ).reset_index()

    survey_stats = df_survey.groupby('employee_id').agg(
        satisfaction_score=('satisfaction', 'mean'),
        work_life_balance_score=('work_life_balance', 'mean'),
        leadership_score=('leadership', 'mean'),
        career_growth_score=('career_growth', 'mean'),
        compensation_score=('compensation', 'mean'),
        overall_satisfaction=('overall_score', 'mean'),
    ).reset_index()

    df = df.merge(email_stats, on='employee_id', how='left')
    df = df.merge(task_stats, on='employee_id', how='left')
    df = df.merge(survey_stats, on='employee_id', how='left')

    dept_encoder = LabelEncoder()
    role_encoder = LabelEncoder()
    level_encoder = LabelEncoder()

    df['dept_encoded'] = dept_encoder.fit_transform(df['department'])
    df['role_encoded'] = role_encoder.fit_transform(df['role'])
    df['level_encoded'] = level_encoder.fit_transform(df['level'])

    for col in FEATURE_COLS:
        if col in df.columns:
            df[col] = df[col].fillna(df[col].median())

    df['target'] = df['is_attrited'].astype(int)

    return df, {
        'dept_encoder': dept_encoder,
        'role_encoder': role_encoder,
        'level_encoder': level_encoder,
        'commute_scaler': commute_scaler,
        'email_baseline': email_baseline,
    }


def build_monthly_features(data):
    df_emp = data['employees'].copy()
    df_att = data['attendance'].copy()
    df_email = data['emails'].copy()
    df_task = data['tasks'].copy()
    df_survey = data['surveys'].copy()

    df_att['month'] = df_att['date'].dt.to_period('M')
    df_email['month'] = df_email['date'].dt.to_period('M')
    df_task['month'] = df_task['week_start'].dt.to_period('M')
    df_survey['month'] = df_survey['survey_date'].dt.to_period('M')

    if 'is_pre_holiday' in df_email.columns:
        df_email = df_email[df_email['is_pre_holiday'] == False]

    att_monthly = df_att.groupby(['employee_id', 'month']).agg(
        late_count=('status', lambda x: (x == '迟到').sum()),
        absent_count=('status', lambda x: (x == '缺勤').sum()),
        total_days=('status', 'count'),
        avg_overtime_hours=('overtime_hours', 'mean'),
        avg_work_hours=('work_hours', 'mean'),
    ).reset_index()
    att_monthly['late_rate'] = att_monthly['late_count'] / att_monthly['total_days']
    att_monthly['absent_rate'] = att_monthly['absent_count'] / att_monthly['total_days']

    email_monthly = df_email.groupby(['employee_id', 'month']).agg(
        avg_internal_emails=('internal_emails', 'mean'),
        avg_external_emails=('external_emails', 'mean'),
        avg_total_emails=('total_emails', 'mean'),
        avg_response_hours=('avg_response_hours', 'mean'),
    ).reset_index()

    task_monthly = df_task.groupby(['employee_id', 'month']).agg(
        avg_completion_rate=('completion_rate', 'mean'),
        avg_ontime_rate=('on_time_rate', 'mean'),
        avg_task_hours=('avg_task_hours', 'mean'),
    ).reset_index()

    survey_monthly = df_survey.groupby(['employee_id', 'month']).agg(
        overall_satisfaction=('overall_score', 'mean'),
        satisfaction_score=('satisfaction', 'mean'),
    ).reset_index()

    monthly = att_monthly.merge(email_monthly, on=['employee_id', 'month'], how='outer')
    monthly = monthly.merge(task_monthly, on=['employee_id', 'month'], how='outer')
    monthly = monthly.merge(survey_monthly, on=['employee_id', 'month'], how='outer')

    monthly = monthly.merge(
        df_emp[['employee_id', 'department', 'age', 'tenure_years', 'commute_distance', 'is_attrited']],
        on='employee_id', how='left'
    )
    monthly['month'] = monthly['month'].astype(str)
    monthly = monthly.sort_values(['employee_id', 'month'])

    return monthly


def train_model(df):
    X = df[FEATURE_COLS].copy()
    y = df['target']

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    X_scaled = pd.DataFrame(X_scaled, columns=FEATURE_COLS)

    X_train, X_test, y_train, y_test = train_test_split(
        X_scaled, y, test_size=0.3, random_state=42, stratify=y
    )

    model = GradientBoostingClassifier(
        n_estimators=200,
        max_depth=5,
        learning_rate=0.1,
        subsample=0.8,
        random_state=42,
    )

    cv_scores = cross_val_score(model, X_scaled, y, cv=5, scoring='roc_auc')
    print(f"交叉验证 ROC-AUC: {cv_scores.mean():.4f} ± {cv_scores.std():.4f}")

    model.fit(X_train, y_train)

    y_pred = model.predict(X_test)
    y_pred_proba = model.predict_proba(X_test)[:, 1]

    print("\n分类报告:")
    print(classification_report(y_test, y_pred))

    print(f"测试集 ROC-AUC: {roc_auc_score(y_test, y_pred_proba):.4f}")

    feature_importance = pd.DataFrame({
        'feature': FEATURE_COLS,
        'importance': model.feature_importances_,
    }).sort_values('importance', ascending=False)

    print("\n特征重要性:")
    for _, row in feature_importance.head(10).iterrows():
        print(f"  {row['feature']:30s} {row['importance']:.4f}")

    return model, scaler, X_train, X_test, y_train, y_test, feature_importance


def get_risk_scores(model, scaler, df):
    X = df[FEATURE_COLS].copy()
    X_scaled = scaler.transform(X)
    X_scaled = pd.DataFrame(X_scaled, columns=FEATURE_COLS)

    proba = model.predict_proba(X_scaled)[:, 1]

    df_result = df[[
        'employee_id', 'department', 'role', 'level', 'age',
        'tenure_years', 'commute_distance', 'late_rate_raw', 'late_rate_adjusted'
    ]].copy()
    df_result['risk_score'] = proba
    df_result['risk_level'] = pd.cut(
        proba,
        bins=[-0.01, 0.3, 0.5, 0.7, 1.01],
        labels=['低风险', '中低风险', '中高风险', '高风险']
    )
    df_result = df_result.sort_values('risk_score', ascending=False)

    return df_result


ACTION_PLANS = {
    'satisfaction_score': {
        'category': '满意度',
        'actions': [
            {'action': '安排员工关怀访谈，了解具体不满原因', 'timeline': '1周内'},
            {'action': '优化工作环境和团队氛围建设', 'timeline': '2周内'},
            {'action': '建立定期反馈机制', 'timeline': '持续进行'},
        ],
        'threshold': 3.0,
    },
    'career_growth_score': {
        'category': '职业发展',
        'actions': [
            {'action': '制定个人发展计划(IDP)', 'timeline': '2周内'},
            {'action': '提供内部培训或外部学习机会', 'timeline': '1个月内'},
            {'action': '安排导师或跨部门轮岗', 'timeline': '1个月内'},
        ],
        'threshold': 3.0,
    },
    'late_rate_adjusted': {
        'category': '考勤纪律',
        'actions': [
            {'action': '了解迟到原因，是否有特殊困难', 'timeline': '3天内'},
            {'action': '讨论弹性工作时间可能性', 'timeline': '1周内'},
            {'action': '制定考勤改进目标', 'timeline': '1周内'},
        ],
        'threshold': 0.05,
    },
    'absent_rate': {
        'category': '出勤情况',
        'actions': [
            {'action': '了解缺勤原因，关注身心健康', 'timeline': '3天内'},
            {'action': '提供EAP心理健康支持', 'timeline': '1周内'},
            {'action': '评估工作负荷是否合理', 'timeline': '2周内'},
        ],
        'threshold': 0.03,
    },
    'avg_overtime_hours': {
        'category': '工作负荷',
        'actions': [
            {'action': '分析加班原因，优化工作流程', 'timeline': '2周内'},
            {'action': '合理分配工作任务', 'timeline': '1周内'},
            {'action': '推行工作生活平衡文化', 'timeline': '持续进行'},
        ],
        'threshold': 1.5,
    },
    'avg_response_hours': {
        'category': '沟通效率',
        'actions': [
            {'action': '了解响应慢的原因', 'timeline': '1周内'},
            {'action': '优化沟通工具和流程', 'timeline': '2周内'},
            {'action': '设定沟通响应SLA', 'timeline': '1个月内'},
        ],
        'threshold': 4.0,
    },
    'avg_total_emails': {
        'category': '沟通参与度',
        'actions': [
            {'action': '了解工作参与度下降原因', 'timeline': '1周内'},
            {'action': '增加团队协作活动', 'timeline': '2周内'},
            {'action': '评估工作内容是否有吸引力', 'timeline': '2周内'},
        ],
        'threshold': 8.0,
        'is_lower_bad': True,
    },
    'avg_completion_rate': {
        'category': '工作绩效',
        'actions': [
            {'action': '分析任务完成率低的原因', 'timeline': '1周内'},
            {'action': '提供技能培训或工作指导', 'timeline': '2周内'},
            {'action': '调整任务难度或数量', 'timeline': '1周内'},
        ],
        'threshold': 0.8,
        'is_lower_bad': True,
    },
    'compensation_score': {
        'category': '薪酬福利',
        'actions': [
            {'action': '进行市场薪酬对标分析', 'timeline': '2周内'},
            {'action': '讨论薪酬调整或奖金方案', 'timeline': '1个月内'},
            {'action': '优化非现金福利体系', 'timeline': '1个月内'},
        ],
        'threshold': 3.0,
    },
    'work_life_balance_score': {
        'category': '工作生活平衡',
        'actions': [
            {'action': '评估工作负荷和压力水平', 'timeline': '1周内'},
            {'action': '推行弹性工作制或远程办公', 'timeline': '2周内'},
            {'action': '鼓励合理休息和年假使用', 'timeline': '持续进行'},
        ],
        'threshold': 3.0,
    },
    'leadership_score': {
        'category': '领导力',
        'actions': [
            {'action': '了解对管理的具体意见', 'timeline': '1周内'},
            {'action': '安排与上级直接沟通', 'timeline': '2周内'},
            {'action': '管理者领导力提升培训', 'timeline': '1个月内'},
        ],
        'threshold': 3.0,
    },
}


def generate_personalized_action_plan(emp_row, shap_contributions, df_features):
    emp_id = emp_row['employee_id']
    risk_score = emp_row['risk_score']
    risk_level = emp_row['risk_level']

    plan = {
        'employee_id': emp_id,
        'risk_score': risk_score,
        'risk_level': risk_level,
        'summary': '',
        'key_drivers': [],
        'actions': [],
    }

    if risk_level == '高风险':
        plan['summary'] = '该员工离职风险极高，需立即介入干预'
    elif risk_level == '中高风险':
        plan['summary'] = '该员工离职风险较高，建议尽快采取措施'
    elif risk_level == '中低风险':
        plan['summary'] = '该员工有一定离职倾向，建议关注'
    else:
        plan['summary'] = '该员工状态稳定，继续保持关注'

    top_drivers = shap_contributions.head(8)

    for _, driver in top_drivers.iterrows():
        feature = driver['feature']
        shap_val = driver['shap_value']
        feature_cn = driver['feature_cn']

        if abs(shap_val) < 0.02:
            continue

        driver_info = {
            'feature': feature,
            'feature_cn': feature_cn,
            'impact': '增加离职风险' if shap_val > 0 else '降低离职风险',
            'shap_value': shap_val,
            'recommendation': '',
        }

        plan['key_drivers'].append(driver_info)

        if shap_val <= 0:
            continue

        if feature in ACTION_PLANS:
            config = ACTION_PLANS[feature]

            feature_values = df_features[df_features['employee_id'] == emp_id][FEATURE_COLS].iloc[0]
            actual_value = feature_values.get(feature, 0)

            is_concerning = False
            if config.get('is_lower_bad', False):
                is_concerning = actual_value < config['threshold']
            else:
                is_concerning = actual_value > config['threshold']

            if is_concerning:
                for idx, action in enumerate(config['actions']):
                    plan['actions'].append({
                        'category': config['category'],
                        'action': action['action'],
                        'timeline': action['timeline'],
                        'priority': idx + 1,
                        'driver': feature_cn,
                    })

    if risk_level in ['高风险', '中高风险'] and len(plan['actions']) < 3:
        urgent_actions = [
            {'category': '紧急', 'action': '立即安排HR与直属领导联合面谈', 'timeline': '3天内', 'priority': 1},
            {'category': '紧急', 'action': '深入了解离职意向和主要顾虑', 'timeline': '1周内', 'priority': 2},
            {'category': '保留', 'action': '制定个性化保留方案', 'timeline': '2周内', 'priority': 3},
        ]
        for action in urgent_actions:
            if not any(a['action'] == action['action'] for a in plan['actions']):
                plan['actions'].append(action)

    plan['actions'] = sorted(plan['actions'], key=lambda x: x['priority'])

    return plan


def generate_retention_suggestions(risk_df, shap_contributions_dict, df_features):
    plans = []
    for _, emp_row in risk_df.iterrows():
        emp_id = emp_row['employee_id']
        if emp_id in shap_contributions_dict:
            shap_contrib = shap_contributions_dict[emp_id]
            plan = generate_personalized_action_plan(emp_row, shap_contrib, df_features)
            plans.append(plan)
    return plans


if __name__ == '__main__':
    from data_generator import generate_all_data

    print("=" * 60)
    print("生成合成数据...")
    print("=" * 60)
    data = generate_all_data()

    print("\n" + "=" * 60)
    print("构建特征工程...")
    print("=" * 60)
    df_features, encoders = build_features(data)

    print("\n" + "=" * 60)
    print("训练机器学习模型...")
    print("=" * 60)
    model, scaler, X_train, X_test, y_train, y_test, feat_imp = train_model(df_features)

    print("\n" + "=" * 60)
    print("生成风险评分...")
    print("=" * 60)
    risk_df = get_risk_scores(model, scaler, df_features)

    print("\n高风险员工 (Top 10):")
    cols = ['employee_id', 'department', 'risk_score', 'risk_level', 'commute_distance']
    print(risk_df.head(10)[cols].to_string(index=False))

    print("\n通勤距离对迟到率的修正示例:")
    sample = risk_df[risk_df['late_rate_raw'] != risk_df['late_rate_adjusted']].head(5)
    for _, row in sample.iterrows():
        print(f"  {row['employee_id']}: 原始迟到率 {row['late_rate_raw']:.2%} -> "
              f"修正后 {row['late_rate_adjusted']:.2%} "
              f"(通勤距离 {row['commute_distance']}km)")

    joblib.dump(model, 'model.joblib')
    joblib.dump(scaler, 'scaler.joblib')
    joblib.dump(encoders, 'encoders.joblib')
    df_features.to_csv('features.csv', index=False)
    risk_df.to_csv('risk_scores.csv', index=False)
    feat_imp.to_csv('feature_importance.csv', index=False)

    print("\n模型与数据已保存完毕。")