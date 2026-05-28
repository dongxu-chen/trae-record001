import numpy as np
import pandas as pd

ROLE_CATEGORIES = {
    '技术类': ['高级工程师', '中级工程师', '初级工程师'],
    '销售类': ['销售经理', '销售代表'],
    '运营类': ['市场专员', '客服代表'],
    '管理类': ['产品经理', 'HR专员', '财务分析师'],
}

LEVEL_ORDER = {'P4': 1, 'P5': 2, 'P6': 3, 'P7': 4, 'M1': 5, 'M2': 6}

ADJACENT_DEPARTMENTS = {
    '工程部': ['产品部'],
    '销售部': ['市场部'],
    '市场部': ['销售部', '客服部'],
    '人力资源部': ['财务部'],
    '财务部': ['人力资源部'],
    '产品部': ['工程部', '市场部'],
    '客服部': ['销售部', '市场部'],
}

KNOWLEDGE_TRANSFER_CHECKLISTS = {
    '技术类': [
        '代码审查与交接',
        '技术文档整理与移交',
        '系统架构说明',
        '开发环境与权限交接',
        '未完成缺陷与问题清单',
        '技术债务说明',
    ],
    '销售类': [
        '客户资源移交',
        '销售漏斗与商机交接',
        'CRM数据更新',
        '合同与协议整理',
        '客户关系维护要点',
        '业绩目标与进度说明',
    ],
    '运营类': [
        '运营活动交接',
        '客户数据与反馈整理',
        '流程文档移交',
        '供应商与合作伙伴信息',
        '营销素材与品牌资产',
        '客户投诉处理记录',
    ],
    '管理类': [
        '项目状态与进度交接',
        '团队管理职责移交',
        '预算与财务审批交接',
        '跨部门协调关系说明',
        '战略规划与目标文档',
        '制度流程与合规要求',
    ],
}

RISK_MITIGATION_TEMPLATES = {
    '技术类': [
        '安排核心代码知识转移会议',
        '建立技术文档备份机制',
        '指定技术负责人临时接管',
        '评估外部技术支持需求',
    ],
    '销售类': [
        '提前通知关键客户联系人变更',
        '安排客户关系平稳过渡',
        '确保销售数据完整备份',
        '调整销售团队目标分配',
    ],
    '运营类': [
        '制定运营工作临时分配方案',
        '确保客户服务不中断',
        '建立紧急响应机制',
        '准备运营数据备份',
    ],
    '管理类': [
        '安排管理权限临时代理',
        '确保项目里程碑不受影响',
        '制定团队稳定方案',
        '评估关键决策延误风险',
    ],
}


def _get_role_category(role):
    for category, roles in ROLE_CATEGORIES.items():
        if role in roles:
            return category
    return None


def _dept_adjacency_priority(dept1, dept2):
    if dept1 == dept2:
        return 2
    if dept2 in ADJACENT_DEPARTMENTS.get(dept1, []):
        return 1
    return 0


def _readiness_level(score):
    if score >= 75:
        return '立即接替'
    elif score >= 50:
        return '短期准备'
    else:
        return '长期培养'


def compute_succession_score(departing_emp, candidate_emp, df_features):
    breakdown = {}

    if departing_emp['department'] == candidate_emp['department']:
        breakdown['部门匹配'] = 30
    else:
        breakdown['部门匹配'] = 0

    dep_level = LEVEL_ORDER.get(departing_emp['level'], 0)
    cand_level = LEVEL_ORDER.get(candidate_emp['level'], 0)
    level_diff = abs(dep_level - cand_level)
    if level_diff == 0:
        breakdown['职级接近度'] = 25
    elif level_diff == 1:
        breakdown['职级接近度'] = 15
    elif level_diff == 2:
        breakdown['职级接近度'] = 5
    else:
        breakdown['职级接近度'] = 0

    if departing_emp['role'] == candidate_emp['role']:
        breakdown['角色匹配'] = 20
    else:
        dep_cat = _get_role_category(departing_emp['role'])
        cand_cat = _get_role_category(candidate_emp['role'])
        if dep_cat and dep_cat == cand_cat:
            breakdown['角色匹配'] = 10
        else:
            breakdown['角色匹配'] = 0

    dep_feat = df_features[df_features['employee_id'] == departing_emp['employee_id']]
    cand_feat = df_features[df_features['employee_id'] == candidate_emp['employee_id']]
    dep_completion = float(dep_feat['avg_completion_rate'].iloc[0]) if not dep_feat.empty else 0.0
    cand_completion = float(cand_feat['avg_completion_rate'].iloc[0]) if not cand_feat.empty else 0.0
    if cand_completion > dep_completion:
        breakdown['绩效匹配'] = 10
    else:
        breakdown['绩效匹配'] = 0

    if candidate_emp['tenure_years'] >= 1:
        breakdown['任职年限'] = 10
    else:
        breakdown['任职年限'] = 3

    is_high_risk = False
    if 'risk_level' in candidate_emp.index and pd.notna(candidate_emp.get('risk_level')):
        is_high_risk = candidate_emp['risk_level'] in ['高风险', '中高风险']
    elif 'risk_score' in candidate_emp.index and pd.notna(candidate_emp.get('risk_score')):
        is_high_risk = candidate_emp['risk_score'] > 0.5
    if not is_high_risk:
        breakdown['风险因素'] = 5
    else:
        breakdown['风险因素'] = 0

    total = min(sum(breakdown.values()), 100)
    return total, breakdown


def find_replacement_candidates(emp_id, df_employees, df_features, risk_df, top_n=5):
    dep_row = df_employees[df_employees['employee_id'] == emp_id]
    if dep_row.empty:
        return []
    departing_emp = dep_row.iloc[0]

    candidates_df = df_employees.copy()

    risk_cols = ['employee_id']
    merge_cols = []
    if 'risk_level' not in candidates_df.columns and 'risk_level' in risk_df.columns:
        merge_cols.append('risk_level')
    if 'risk_score' not in candidates_df.columns and 'risk_score' in risk_df.columns:
        merge_cols.append('risk_score')

    if merge_cols:
        risk_info = risk_df[risk_cols + merge_cols].copy()
        candidates_df = candidates_df.merge(risk_info, on='employee_id', how='left')

    candidates_df = candidates_df[candidates_df['employee_id'] != emp_id]
    if 'is_attrited' in candidates_df.columns:
        candidates_df = candidates_df[candidates_df['is_attrited'] != True]

    results = []
    for _, candidate in candidates_df.iterrows():
        score, breakdown = compute_succession_score(
            departing_emp, candidate, df_features
        )
        adjacency = _dept_adjacency_priority(
            departing_emp['department'], candidate['department']
        )
        results.append({
            'candidate_id': candidate['employee_id'],
            'department': candidate['department'],
            'role': candidate['role'],
            'level': candidate['level'],
            'tenure_years': candidate['tenure_years'],
            'score': score,
            'score_breakdown': breakdown,
            'readiness_level': _readiness_level(score),
            '_adjacency': adjacency,
        })

    results.sort(key=lambda x: (x['score'], x['_adjacency']), reverse=True)

    for r in results:
        del r['_adjacency']

    return results[:top_n]


def generate_succession_plan(emp_id, df_employees, df_features, risk_df):
    dep_row = df_employees[df_employees['employee_id'] == emp_id]
    if dep_row.empty:
        return None
    departing_emp = dep_row.iloc[0]

    dep_risk = risk_df[risk_df['employee_id'] == emp_id]
    risk_score = float(dep_risk['risk_score'].iloc[0]) if not dep_risk.empty else 0.0
    risk_level = str(dep_risk['risk_level'].iloc[0]) if not dep_risk.empty else '未知'

    candidates = find_replacement_candidates(
        emp_id, df_employees, df_features, risk_df, top_n=5
    )

    role_cat = _get_role_category(departing_emp['role'])
    checklist = KNOWLEDGE_TRANSFER_CHECKLISTS.get(
        role_cat, KNOWLEDGE_TRANSFER_CHECKLISTS['管理类']
    )

    if candidates:
        best_readiness = candidates[0]['readiness_level']
        if best_readiness == '立即接替':
            transition_period = '1-2周'
        elif best_readiness == '短期准备':
            transition_period = '2-4周'
        else:
            transition_period = '1-3个月'
    else:
        transition_period = '3-6个月'

    mitigation = list(RISK_MITIGATION_TEMPLATES.get(
        role_cat, RISK_MITIGATION_TEMPLATES['管理类']
    ))

    if risk_level == '高风险':
        mitigation.extend([
            '启动紧急人才盘点',
            '联系外部招聘渠道作为备选',
            '制定业务连续性预案',
        ])
    elif risk_level == '中高风险':
        mitigation.extend([
            '加快内部培养进度',
            '评估外部招聘可行性',
            '准备临时替代方案',
        ])

    return {
        'employee_id': emp_id,
        'department': departing_emp['department'],
        'role': departing_emp['role'],
        'level': departing_emp['level'],
        'risk_score': round(risk_score, 4),
        'risk_level': risk_level,
        'replacement_candidates': candidates,
        'knowledge_transfer_checklist': checklist,
        'transition_period': transition_period,
        'risk_mitigation_actions': mitigation,
    }


def batch_succession_planning(risk_df, df_employees, df_features, max_emps=10):
    high_risk = risk_df[risk_df['risk_level'] == '高风险']

    if len(high_risk) < max_emps:
        medium_high = risk_df[risk_df['risk_level'] == '中高风险']
        high_risk = pd.concat([high_risk, medium_high])

    high_risk = high_risk.sort_values('risk_score', ascending=False).head(max_emps)

    plans = []
    for _, row in high_risk.iterrows():
        emp_id = row['employee_id']
        plan = generate_succession_plan(emp_id, df_employees, df_features, risk_df)
        if plan is not None:
            plans.append(plan)

    return plans
