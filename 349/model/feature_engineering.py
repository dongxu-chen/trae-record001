from typing import Dict, List, Any
from datetime import datetime
import numpy as np

from config import KG_FEATURE_WEIGHTS
from data.models import CompanyInput


FEATURE_COLUMNS = [
    "registered_capital",
    "paid_in_ratio",
    "company_age_years",
    "employee_count",
    "operating_status_score",
    "shareholder_count",
    "avg_share_ratio",
    "shareholder_other_companies",
    "corporate_shareholder_count",
    "shareholder_quality_score",
    "executive_count",
    "avg_executive_tenure",
    "industry_peer_count",
    "industry_peer_score",
    "supply_chain_partners",
    "avg_supply_strength",
    "supply_chain_stability_score",
    "legal_relation_count",
    "total_legal_lawsuits",
    "legal_relation_score",
    "associated_companies",
    "associated_executives",
    "association_risk_score",
    "lawsuit_count",
    "executed_person_count",
    "total_executed_amount",
    "administrative_penalty_count",
    "total_penalty_amount",
    "contract_breach_count",
    "abnormal_operation_records",
    "dishonest_records",
    "patent_count",
    "invention_patent_count",
    "utility_model_count",
    "trademark_count",
    "copyright_count",
    "patent_invalidation_count",
    "tax_arrears_count",
    "total_arrears_amount",
    "tax_credit_rating_score",
    "continuous_tax_years",
    "annual_tax_amount",
    "revenue",
    "net_profit",
    "profit_margin",
    "total_assets",
    "total_liabilities",
    "current_ratio",
    "debt_to_equity_ratio",
    "roe",
    "loan_outstanding_ratio",
    "overdue_days",
    "kg_composite_score",
]


def build_feature_vector(company: CompanyInput, kg_features: Dict[str, float]) -> Dict[str, float]:
    features = {}

    bi = company.business_info
    features["registered_capital"] = float(bi.registered_capital)
    features["paid_in_ratio"] = float(bi.paid_in_capital / bi.registered_capital) if bi.registered_capital > 0 else 0.0

    try:
        established = datetime.strptime(bi.established_date, "%Y-%m-%d")
        features["company_age_years"] = float((datetime.now() - established).days / 365.25)
    except (ValueError, TypeError):
        features["company_age_years"] = 5.0

    features["employee_count"] = float(bi.number_of_employees)
    features["operating_status_score"] = _status_score(bi.operating_status)

    jr = company.judicial_risk
    features["lawsuit_count"] = float(jr.lawsuit_count)
    features["executed_person_count"] = float(jr.executed_person_count)
    features["total_executed_amount"] = float(jr.total_executed_amount)
    features["administrative_penalty_count"] = float(jr.administrative_penalty_count)
    features["total_penalty_amount"] = float(jr.total_penalty_amount)
    features["contract_breach_count"] = float(jr.contract_breach_count)
    features["abnormal_operation_records"] = float(jr.abnormal_operation_records)
    features["dishonest_records"] = float(jr.dishonest_records)

    ip = company.ip
    features["patent_count"] = float(ip.patent_count)
    features["invention_patent_count"] = float(ip.invention_patent_count)
    features["utility_model_count"] = float(ip.utility_model_count)
    features["trademark_count"] = float(ip.trademark_count)
    features["copyright_count"] = float(ip.copyright_count)
    features["patent_invalidation_count"] = float(ip.patent_invalidation_count)

    tr = company.tax_record
    features["tax_arrears_count"] = float(tr.tax_arrears_count)
    features["total_arrears_amount"] = float(tr.total_arrears_amount)
    features["tax_credit_rating_score"] = _tax_rating_score(tr.tax_credit_rating)
    features["continuous_tax_years"] = float(tr.continuous_tax_years)
    features["annual_tax_amount"] = float(tr.annual_tax_amount)

    fi = company.financial_info
    features["revenue"] = float(fi.revenue)
    features["net_profit"] = float(fi.net_profit)
    features["profit_margin"] = float(fi.net_profit / fi.revenue) if fi.revenue > 0 else 0.0
    features["total_assets"] = float(fi.total_assets)
    features["total_liabilities"] = float(fi.total_liabilities)
    features["current_ratio"] = float(fi.current_ratio)
    features["debt_to_equity_ratio"] = float(fi.debt_to_equity_ratio)
    features["roe"] = float(fi.roe)

    if company.loan_records:
        total_principal = sum(l.principal_amount for l in company.loan_records)
        total_outstanding = sum(l.outstanding_amount for l in company.loan_records)
        max_overdue = max(l.overdue_days for l in company.loan_records)
        features["loan_outstanding_ratio"] = float(total_outstanding / total_principal) if total_principal > 0 else 0.0
        features["overdue_days"] = float(max_overdue)
    else:
        features["loan_outstanding_ratio"] = 0.0
        features["overdue_days"] = 0.0

    for key, val in kg_features.items():
        features[key] = float(val)

    features["kg_composite_score"] = _calc_kg_composite(kg_features)

    return features


def _status_score(status: str) -> float:
    mapping = {
        "存续（在营）": 100.0,
        "在营": 95.0,
        "开业": 90.0,
        "迁出": 40.0,
        "注销": 0.0,
    }
    return mapping.get(status, 50.0)


def _tax_rating_score(rating: str) -> float:
    mapping = {
        "A": 100.0,
        "B": 75.0,
        "C": 50.0,
        "D": 25.0,
    }
    return mapping.get(rating, 50.0)


def _calc_kg_composite(kg_features: Dict[str, float]) -> float:
    weighted_sum = 0.0
    total_weight = 0.0
    for feature_name, weight in KG_FEATURE_WEIGHTS.items():
        if feature_name in kg_features:
            weighted_sum += kg_features[feature_name] * weight
            total_weight += weight
    if total_weight > 0:
        return weighted_sum / total_weight
    return 50.0


def feature_vector_to_array(feature_dict: Dict[str, float]) -> np.ndarray:
    vector = []
    for col in FEATURE_COLUMNS:
        vector.append(feature_dict.get(col, 0.0))
    return np.array(vector, dtype=np.float32)


def compute_ground_truth_score(company: CompanyInput, kg_features: Dict[str, float]) -> float:
    bi = company.business_info
    jr = company.judicial_risk
    ip = company.ip
    tr = company.tax_record
    fi = company.financial_info

    base_score = 600.0

    base_score += min(bi.registered_capital / 100, 100)
    base_score += (bi.paid_in_capital / bi.registered_capital) * 50 if bi.registered_capital > 0 else 0
    base_score += min(float(bi.number_of_employees) / 20, 50)

    base_score -= jr.lawsuit_count * 8
    base_score -= jr.executed_person_count * 30
    base_score -= min(jr.total_executed_amount / 10000, 50)
    base_score -= jr.administrative_penalty_count * 5
    base_score -= jr.contract_breach_count * 6
    base_score -= jr.abnormal_operation_records * 15
    base_score -= jr.dishonest_records * 25

    base_score += ip.patent_count * 2
    base_score += ip.invention_patent_count * 5
    base_score -= ip.patent_invalidation_count * 8

    base_score -= tr.tax_arrears_count * 10
    base_score -= min(tr.total_arrears_amount / 10000, 40)
    base_score += _tax_rating_score(tr.tax_credit_rating) * 0.3
    base_score += tr.continuous_tax_years * 3

    base_score += min(fi.revenue / 100, 80)
    if fi.revenue > 0:
        base_score += (fi.net_profit / fi.revenue) * 100
    base_score += min(fi.roe * 100, 50) if fi.roe > 0 else fi.roe * 50
    base_score -= max(0, (fi.debt_to_equity_ratio - 1.0)) * 20

    if company.loan_records:
        for loan in company.loan_records:
            base_score -= loan.overdue_days * 0.5

    kg_composite = _calc_kg_composite(kg_features)
    base_score += (kg_composite - 50) * 1.5

    return max(0.0, min(1000.0, base_score))


def score_to_rating(score: float) -> str:
    from config import get_rating_thresholds
    thresholds = get_rating_thresholds()
    for rating, (low, high) in thresholds.items():
        if low <= score < high:
            return rating
    return "D"


def score_to_risk_level(score: float) -> str:
    from config import RISK_LEVELS
    rating = score_to_rating(score)
    return RISK_LEVELS.get(rating, "未知风险")
