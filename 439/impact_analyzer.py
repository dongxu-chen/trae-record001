import numpy as np
import pandas as pd

SENIORITY_WEIGHTS = {
    'M2': 100, 'M1': 90, 'P7': 65, 'P6': 45, 'P5': 25, 'P4': 15,
}

ROLE_CRITICALITY = {
    '高级工程师': 90, '产品经理': 85, '中级工程师': 70,
    '销售经理': 65, '财务分析师': 55, '市场专员': 50,
    'HR专员': 45, '初级工程师': 40, '销售代表': 35, '客服代表': 25,
}

MORALE_WEIGHTS = {
    '职级影响': 0.25,
    '团队规模': 0.20,
    '满意度影响': 0.20,
    '沟通连接度': 0.15,
    '部门风险': 0.20,
}

PROJECT_WEIGHTS = {
    '任务完成率': 0.30,
    '加班贡献度': 0.20,
    '角色关键性': 0.30,
    '产能损失': 0.20,
}

OVERALL_MORALE_WEIGHT = 0.45
OVERALL_PROJECT_WEIGHT = 0.55

IMPACT_THRESHOLDS = [
    (75, '严重'),
    (50, '较高'),
    (25, '中等'),
    (0, '较低'),
]


def _seniority_score(level):
    return float(SENIORITY_WEIGHTS.get(level, 25))


def _team_size_score(team_size):
    if team_size <= 5:
        return 100.0
    if team_size >= 50:
        return 10.0
    return 100.0 - (team_size - 5) / 45.0 * 90.0


def _satisfaction_impact_score(satisfaction):
    return float(np.clip((satisfaction - 1.0) / 4.0 * 100.0, 0, 100))


def _email_volume_score(avg_total_emails, max_emails=25.0):
    return float(np.clip(avg_total_emails / max_emails * 100.0, 0, 100))


def _dept_risk_score(dept_avg_risk):
    return float(np.clip(dept_avg_risk * 100.0, 0, 100))


def _completion_score(completion_rate):
    return float(np.clip(completion_rate * 100.0, 0, 100))


def _overtime_score(avg_overtime_hours, max_overtime=3.0):
    return float(np.clip(avg_overtime_hours / max_overtime * 100.0, 0, 100))


def _criticality_score(role):
    return float(ROLE_CRITICALITY.get(role, 50))


def _capacity_loss_score(team_size):
    return float(np.clip(500.0 / team_size, 0, 100))


def _impact_level(overall_impact):
    for threshold, label in IMPACT_THRESHOLDS:
        if overall_impact >= threshold:
            return label
    return '较低'


def assess_departure_impact(emp_id, df_employees, df_features, risk_df):
    emp_row = df_employees[df_employees['employee_id'] == emp_id]
    if emp_row.empty:
        return None
    emp = emp_row.iloc[0]

    feat_row = df_features[df_features['employee_id'] == emp_id]
    if feat_row.empty:
        return None
    feat = feat_row.iloc[0]

    risk_row = risk_df[risk_df['employee_id'] == emp_id]
    if risk_row.empty:
        return None

    dept = emp['department']
    level = emp['level']
    role = emp['role']

    team_size = len(df_employees[df_employees['department'] == dept])
    dept_avg_risk = risk_df[risk_df['department'] == dept]['risk_score'].mean()

    s_seniority = _seniority_score(level)
    s_team_size = _team_size_score(team_size)
    s_satisfaction = _satisfaction_impact_score(
        feat.get('overall_satisfaction', 3.0)
    )
    s_email = _email_volume_score(
        feat.get('avg_total_emails', 5.0)
    )
    s_dept_risk = _dept_risk_score(dept_avg_risk)

    morale_factors = {
        '职级影响': round(s_seniority, 1),
        '团队规模': round(s_team_size, 1),
        '满意度影响': round(s_satisfaction, 1),
        '沟通连接度': round(s_email, 1),
        '部门风险': round(s_dept_risk, 1),
    }

    morale_impact = sum(
        morale_factors[k] * MORALE_WEIGHTS[k] for k in MORALE_WEIGHTS
    )
    morale_impact = float(np.clip(morale_impact, 0, 100))

    s_completion = _completion_score(
        feat.get('avg_completion_rate', 0.85)
    )
    s_overtime = _overtime_score(
        feat.get('avg_overtime_hours', 0.5)
    )
    s_criticality = _criticality_score(role)
    s_capacity = _capacity_loss_score(team_size)

    project_factors = {
        '任务完成率': round(s_completion, 1),
        '加班贡献度': round(s_overtime, 1),
        '角色关键性': round(s_criticality, 1),
        '产能损失': round(s_capacity, 1),
    }

    project_impact = sum(
        project_factors[k] * PROJECT_WEIGHTS[k] for k in PROJECT_WEIGHTS
    )
    project_impact = float(np.clip(project_impact, 0, 100))

    overall_impact = float(np.clip(
        morale_impact * OVERALL_MORALE_WEIGHT
        + project_impact * OVERALL_PROJECT_WEIGHT,
        0, 100
    ))

    return {
        'employee_id': emp_id,
        'department': dept,
        'role': role,
        'level': level,
        'morale_impact': round(morale_impact, 1),
        'project_impact': round(project_impact, 1),
        'overall_impact': round(overall_impact, 1),
        'impact_level': _impact_level(overall_impact),
        'morale_factors': morale_factors,
        'project_factors': project_factors,
    }


def assess_team_impact(risk_df, df_employees, df_features):
    high_risk = risk_df[risk_df['risk_level'].isin(['高风险', '中高风险'])]

    if high_risk.empty:
        return pd.DataFrame(columns=[
            'employee_id', 'department', 'role', 'level',
            'morale_impact', 'project_impact', 'overall_impact',
            'impact_level', 'risk_score', 'risk_level',
            'morale_factors', 'project_factors',
        ])

    results = []
    for _, row in high_risk.iterrows():
        emp_id = row['employee_id']
        impact = assess_departure_impact(
            emp_id, df_employees, df_features, risk_df
        )
        if impact is None:
            continue

        impact['risk_score'] = round(float(row['risk_score']), 4)
        impact['risk_level'] = str(row['risk_level'])
        results.append(impact)

    if not results:
        return pd.DataFrame(columns=[
            'employee_id', 'department', 'role', 'level',
            'morale_impact', 'project_impact', 'overall_impact',
            'impact_level', 'risk_score', 'risk_level',
            'morale_factors', 'project_factors',
        ])

    df_result = pd.DataFrame(results)
    df_result = df_result.sort_values('overall_impact', ascending=False)
    df_result = df_result.reset_index(drop=True)

    return df_result


def generate_impact_summary(impact_results):
    if isinstance(impact_results, pd.DataFrame):
        if impact_results.empty:
            return {'department_summaries': {}, 'company_summary': {}}
        df = impact_results.copy()
    elif isinstance(impact_results, list):
        if not impact_results:
            return {'department_summaries': {}, 'company_summary': {}}
        df = pd.DataFrame(impact_results)
    else:
        return {'department_summaries': {}, 'company_summary': {}}

    dept_summaries = {}
    for dept in df['department'].unique():
        dept_df = df[df['department'] == dept]
        dept_summaries[dept] = {
            '受影响人数': int(len(dept_df)),
            '平均士气影响': round(float(dept_df['morale_impact'].mean()), 1),
            '平均项目影响': round(float(dept_df['project_impact'].mean()), 1),
            '平均综合影响': round(float(dept_df['overall_impact'].mean()), 1),
            '最高综合影响': round(float(dept_df['overall_impact'].max()), 1),
            '影响等级分布': dept_df['impact_level'].value_counts().to_dict(),
            '关键角色': dept_df.loc[
                dept_df['project_impact'].idxmax(),
                ['role', 'employee_id']
            ].to_dict() if len(dept_df) > 0 else {},
        }

    level_dist = df['impact_level'].value_counts().to_dict()
    company_summary = {
        '总受影响人数': int(len(df)),
        '涉及部门数': int(df['department'].nunique()),
        '公司平均士气影响': round(float(df['morale_impact'].mean()), 1),
        '公司平均项目影响': round(float(df['project_impact'].mean()), 1),
        '公司平均综合影响': round(float(df['overall_impact'].mean()), 1),
        '影响等级分布': level_dist,
        '最严重部门': max(
            dept_summaries,
            key=lambda d: dept_summaries[d]['平均综合影响']
        ) if dept_summaries else '',
        '最高影响员工': df.loc[
            df['overall_impact'].idxmax(),
            ['employee_id', 'department', 'role']
        ].to_dict() if len(df) > 0 else {},
    }

    return {
        'department_summaries': dept_summaries,
        'company_summary': company_summary,
    }
