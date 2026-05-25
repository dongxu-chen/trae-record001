import json
import joblib
import numpy as np
import shap
from typing import Dict, List, Optional, Any
from pathlib import Path

from config import SHAP_EXPLAINER_FILE, FEATURE_NAMES_FILE
from model.feature_engineering import build_feature_vector, feature_vector_to_array, FEATURE_COLUMNS
from model.training import load_model, load_feature_names


FEATURE_DESCRIPTIONS = {
    "registered_capital": "注册资本规模",
    "paid_in_ratio": "实缴资本比例",
    "company_age_years": "公司经营年限",
    "employee_count": "员工数量",
    "operating_status_score": "经营状态评分",
    "shareholder_count": "股东数量",
    "avg_share_ratio": "平均持股比例",
    "shareholder_other_companies": "股东关联企业数",
    "corporate_shareholder_count": "法人股东数量",
    "shareholder_quality_score": "股东质量评分",
    "executive_count": "高管人数",
    "avg_executive_tenure": "高管平均任职年限",
    "industry_peer_count": "行业同业数量",
    "industry_peer_score": "行业地位评分",
    "supply_chain_partners": "供应链合作伙伴数",
    "avg_supply_strength": "供应链平均强度",
    "supply_chain_stability_score": "供应链稳定性评分",
    "legal_relation_count": "法律关联企业数",
    "total_legal_lawsuits": "关联诉讼总数",
    "legal_relation_score": "法律关系评分",
    "associated_companies": "关联公司数量",
    "associated_executives": "关联高管数量",
    "association_risk_score": "关联风险评分",
    "lawsuit_count": "诉讼案件数",
    "executed_person_count": "被执行人记录数",
    "total_executed_amount": "被执行总金额",
    "administrative_penalty_count": "行政处罚数",
    "total_penalty_amount": "处罚总金额",
    "contract_breach_count": "合同违约数",
    "abnormal_operation_records": "经营异常记录数",
    "dishonest_records": "失信被执行人记录",
    "patent_count": "专利总数",
    "invention_patent_count": "发明专利数",
    "utility_model_count": "实用新型数",
    "trademark_count": "商标数量",
    "copyright_count": "著作权数量",
    "patent_invalidation_count": "专利失效数",
    "tax_arrears_count": "欠税次数",
    "total_arrears_amount": "欠税总金额",
    "tax_credit_rating_score": "纳税信用等级分",
    "continuous_tax_years": "连续纳税年限",
    "annual_tax_amount": "年纳税金额",
    "revenue": "营业收入",
    "net_profit": "净利润",
    "profit_margin": "净利润率",
    "total_assets": "总资产",
    "total_liabilities": "总负债",
    "current_ratio": "流动比率",
    "debt_to_equity_ratio": "资产负债率",
    "roe": "净资产收益率",
    "loan_outstanding_ratio": "贷款余额比例",
    "overdue_days": "逾期天数",
    "kg_composite_score": "知识图谱综合评分",
}

FEATURE_CATEGORIES = {
    "工商基本信息": [
        "registered_capital", "paid_in_ratio", "company_age_years",
        "employee_count", "operating_status_score"
    ],
    "股东与治理": [
        "shareholder_count", "avg_share_ratio", "shareholder_other_companies",
        "corporate_shareholder_count", "shareholder_quality_score",
        "executive_count", "avg_executive_tenure"
    ],
    "知识图谱特征": [
        "industry_peer_count", "industry_peer_score",
        "supply_chain_partners", "avg_supply_strength", "supply_chain_stability_score",
        "legal_relation_count", "total_legal_lawsuits", "legal_relation_score",
        "associated_companies", "associated_executives", "association_risk_score",
        "kg_composite_score"
    ],
    "司法风险": [
        "lawsuit_count", "executed_person_count", "total_executed_amount",
        "administrative_penalty_count", "total_penalty_amount",
        "contract_breach_count", "abnormal_operation_records", "dishonest_records"
    ],
    "知识产权": [
        "patent_count", "invention_patent_count", "utility_model_count",
        "trademark_count", "copyright_count", "patent_invalidation_count"
    ],
    "纳税记录": [
        "tax_arrears_count", "total_arrears_amount", "tax_credit_rating_score",
        "continuous_tax_years", "annual_tax_amount"
    ],
    "财务状况": [
        "revenue", "net_profit", "profit_margin", "total_assets",
        "total_liabilities", "current_ratio", "debt_to_equity_ratio", "roe"
    ],
    "信贷记录": [
        "loan_outstanding_ratio", "overdue_days"
    ],
}


def create_explainer(model, X_background: np.ndarray) -> shap.TreeExplainer:
    explainer = shap.TreeExplainer(model, data=X_background[:100])
    return explainer


def save_explainer(explainer: shap.TreeExplainer) -> None:
    joblib.dump(explainer, str(SHAP_EXPLAINER_FILE))


def load_explainer() -> Optional[shap.TreeExplainer]:
    if SHAP_EXPLAINER_FILE.exists():
        return joblib.load(str(SHAP_EXPLAINER_FILE))
    return None


def get_shap_values(
    company,
    kg_features: Dict[str, float],
    explainer: Optional[shap.TreeExplainer] = None,
    model=None,
    scaler=None
) -> np.ndarray:
    if model is None or scaler is None:
        model, scaler = load_model()

    features = build_feature_vector(company, kg_features)
    X = feature_vector_to_array(features).reshape(1, -1)
    X_scaled = scaler.transform(X)

    if explainer is None:
        explainer = load_explainer()
        if explainer is None:
            explainer = shap.TreeExplainer(model)

    shap_values = explainer.shap_values(X_scaled)
    if isinstance(shap_values, list):
        shap_values = shap_values[0]

    return shap_values[0] if len(shap_values.shape) > 1 else shap_values


def analyze_risk_factors(
    company,
    kg_features: Dict[str, float],
    predicted_score: float
) -> List[Dict[str, Any]]:
    feature_names = load_feature_names()
    shap_vals = get_shap_values(company, kg_features)

    risk_factors = []
    for i, (name, shap_val) in enumerate(zip(feature_names, shap_vals)):
        abs_impact = abs(float(shap_val))
        if abs_impact > 1.0:
            description = FEATURE_DESCRIPTIONS.get(name, name)
            category = _get_feature_category(name)
            direction = "正面影响" if shap_val > 0 else "负面影响"

            normalized_impact = min(abs_impact / 50.0, 1.0)

            risk_factors.append({
                "feature": name,
                "description": description,
                "category": category,
                "impact": round(float(shap_val), 2),
                "absolute_impact": round(abs_impact, 2),
                "normalized_impact": round(normalized_impact, 4),
                "direction": direction,
                "severity": _get_severity(normalized_impact),
            })

    risk_factors.sort(key=lambda x: x["absolute_impact"], reverse=True)
    return risk_factors


def get_key_strengths(risk_factors: List[Dict[str, Any]], top_n: int = 5) -> List[str]:
    positive_factors = [f for f in risk_factors if f["direction"] == "正面影响"]
    positive_factors.sort(key=lambda x: x["absolute_impact"], reverse=True)

    strengths = []
    for f in positive_factors[:top_n]:
        strengths.append(f"{f['description']}：{f['direction']}（影响值：{f['impact']}）")
    return strengths


def get_risk_warnings(risk_factors: List[Dict[str, Any]], top_n: int = 5) -> List[str]:
    negative_factors = [f for f in risk_factors if f["direction"] == "负面影响"]
    negative_factors.sort(key=lambda x: x["absolute_impact"], reverse=True)

    warnings = []
    for f in negative_factors[:top_n]:
        warnings.append(f"{f['description']}：{f['direction']}（影响值：{f['impact']}）")
    return warnings


def get_category_contributions(risk_factors: List[Dict[str, Any]]) -> Dict[str, float]:
    category_contrib = {}
    for f in risk_factors:
        cat = f["category"]
        if cat not in category_contrib:
            category_contrib[cat] = 0.0
        category_contrib[cat] += f["impact"]

    return dict(sorted(category_contrib.items(), key=lambda x: x[1], reverse=True))


def generate_recommendation(risk_factors: List[Dict[str, Any]], score: float) -> str:
    negative = [f for f in risk_factors if f["direction"] == "负面影响" and f["severity"] in ["高", "中"]]
    positive = [f for f in risk_factors if f["direction"] == "正面影响" and f["severity"] in ["高", "中"]]

    recommendations = []

    if score >= 800:
        recommendations.append("企业信用状况优异，建议给予优质客户待遇，可考虑提高授信额度。")
    elif score >= 600:
        recommendations.append("企业信用状况良好，风险可控，建议维持现有授信政策。")
    elif score >= 400:
        recommendations.append("企业存在一定信用风险，建议加强贷后监测频率，适当控制授信额度。")
    else:
        recommendations.append("企业信用风险较高，建议审慎授信，加强担保措施，密切监控经营状况。")

    if negative:
        severe_issues = [f for f in negative if f["severity"] == "高"]
        if severe_issues:
            issues_text = "、".join([f["description"] for f in severe_issues[:3]])
            recommendations.append(f"重点关注：{issues_text}，建议尽快核实并采取风险缓释措施。")

    if positive:
        strengths_text = "、".join([f["description"] for f in positive[:3]])
        recommendations.append(f"核心优势：{strengths_text}，可作为风险缓释因素纳入评估。")

    return " ".join(recommendations)


def _get_feature_category(feature_name: str) -> str:
    for category, features in FEATURE_CATEGORIES.items():
        if feature_name in features:
            return category
    return "其他"


def _get_severity(normalized_impact: float) -> str:
    if normalized_impact >= 0.7:
        return "高"
    elif normalized_impact >= 0.3:
        return "中"
    else:
        return "低"
