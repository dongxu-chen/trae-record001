import copy
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass

from data.models import CompanyInput
from model.feature_engineering import (
    build_feature_vector, feature_vector_to_array, score_to_rating,
    score_to_risk_level, FEATURE_COLUMNS
)
from model.training import load_model, predict_score
from analysis.risk_analysis import analyze_risk_factors, get_key_strengths, get_risk_warnings
from monitoring.post_loan import get_monitor


ADJUSTABLE_FACTORS = {
    "judicial_risk": {
        "lawsuit_count": {
            "label": "诉讼案件数",
            "category": "司法风险",
            "type": "integer",
            "min": 0,
            "max": 100,
            "impact_type": "negative",
            "unit": "件"
        },
        "executed_person_count": {
            "label": "被执行人记录数",
            "category": "司法风险",
            "type": "integer",
            "min": 0,
            "max": 50,
            "impact_type": "negative",
            "unit": "条"
        },
        "total_executed_amount": {
            "label": "被执行总金额",
            "category": "司法风险",
            "type": "float",
            "min": 0,
            "max": 10000000,
            "impact_type": "negative",
            "unit": "万元"
        },
        "administrative_penalty_count": {
            "label": "行政处罚数",
            "category": "司法风险",
            "type": "integer",
            "min": 0,
            "max": 50,
            "impact_type": "negative",
            "unit": "条"
        },
        "dishonest_records": {
            "label": "失信被执行人记录",
            "category": "司法风险",
            "type": "integer",
            "min": 0,
            "max": 20,
            "impact_type": "negative",
            "unit": "条"
        },
    },
    "financial_info": {
        "revenue": {
            "label": "营业收入",
            "category": "财务状况",
            "type": "float",
            "min": 0,
            "max": 100000,
            "impact_type": "positive",
            "unit": "万元"
        },
        "net_profit": {
            "label": "净利润",
            "category": "财务状况",
            "type": "float",
            "min": -10000,
            "max": 20000,
            "impact_type": "positive",
            "unit": "万元"
        },
        "total_assets": {
            "label": "总资产",
            "category": "财务状况",
            "type": "float",
            "min": 0,
            "max": 200000,
            "impact_type": "positive",
            "unit": "万元"
        },
        "debt_to_equity_ratio": {
            "label": "资产负债率",
            "category": "财务状况",
            "type": "float",
            "min": 0,
            "max": 5,
            "impact_type": "negative",
            "unit": "%"
        },
        "roe": {
            "label": "净资产收益率",
            "category": "财务状况",
            "type": "float",
            "min": -1,
            "max": 1,
            "impact_type": "positive",
            "unit": "%"
        },
    },
    "tax_record": {
        "tax_arrears_count": {
            "label": "欠税次数",
            "category": "纳税记录",
            "type": "integer",
            "min": 0,
            "max": 20,
            "impact_type": "negative",
            "unit": "次"
        },
        "total_arrears_amount": {
            "label": "欠税总金额",
            "category": "纳税记录",
            "type": "float",
            "min": 0,
            "max": 10000,
            "impact_type": "negative",
            "unit": "万元"
        },
        "tax_credit_rating": {
            "label": "纳税信用等级",
            "category": "纳税记录",
            "type": "enum",
            "options": ["A", "B", "C", "D"],
            "impact_type": "positive",
            "unit": ""
        },
        "continuous_tax_years": {
            "label": "连续纳税年限",
            "category": "纳税记录",
            "type": "integer",
            "min": 0,
            "max": 30,
            "impact_type": "positive",
            "unit": "年"
        },
        "annual_tax_amount": {
            "label": "年纳税金额",
            "category": "纳税记录",
            "type": "float",
            "min": 0,
            "max": 5000,
            "impact_type": "positive",
            "unit": "万元"
        },
    },
    "ip": {
        "patent_count": {
            "label": "专利总数",
            "category": "知识产权",
            "type": "integer",
            "min": 0,
            "max": 500,
            "impact_type": "positive",
            "unit": "件"
        },
        "invention_patent_count": {
            "label": "发明专利数",
            "category": "知识产权",
            "type": "integer",
            "min": 0,
            "max": 200,
            "impact_type": "positive",
            "unit": "件"
        },
    },
    "business_info": {
        "registered_capital": {
            "label": "注册资本",
            "category": "工商信息",
            "type": "float",
            "min": 0,
            "max": 100000,
            "impact_type": "positive",
            "unit": "万元"
        },
        "number_of_employees": {
            "label": "员工数量",
            "category": "工商信息",
            "type": "integer",
            "min": 0,
            "max": 10000,
            "impact_type": "positive",
            "unit": "人"
        },
    },
    "loan": {
        "overdue_days": {
            "label": "逾期天数",
            "category": "信贷记录",
            "type": "integer",
            "min": 0,
            "max": 365,
            "impact_type": "negative",
            "unit": "天"
        },
    },
    "kg_features": {
        "shareholder_quality_score": {
            "label": "股东质量评分",
            "category": "知识图谱",
            "type": "float",
            "min": 0,
            "max": 100,
            "impact_type": "positive",
            "unit": "分"
        },
        "supply_chain_stability_score": {
            "label": "供应链稳定性评分",
            "category": "知识图谱",
            "type": "float",
            "min": 0,
            "max": 100,
            "impact_type": "positive",
            "unit": "分"
        },
        "legal_relation_score": {
            "label": "法律关系评分",
            "category": "知识图谱",
            "type": "float",
            "min": 0,
            "max": 100,
            "impact_type": "positive",
            "unit": "分"
        },
    },
}


@dataclass
class SimulationResult:
    original_score: float
    original_rating: str
    adjusted_score: float
    adjusted_rating: str
    score_change: float
    rating_change: str
    changed_factors: Dict[str, Any]
    original_risk_factors: List[Dict[str, Any]]
    adjusted_risk_factors: List[Dict[str, Any]]
    key_improvements: List[str]
    key_deteriorations: List[str]


class ScoreSimulator:
    def __init__(self):
        self.model, self.scaler = load_model()

    def get_adjustable_factors(self) -> Dict[str, Any]:
        return ADJUSTABLE_FACTORS

    def simulate(
        self,
        company: CompanyInput,
        kg_features: Dict[str, float],
        adjustments: Dict[str, Any]
    ) -> SimulationResult:
        original_score = predict_score(company, kg_features, self.model, self.scaler)
        original_rating = score_to_rating(original_score)
        original_risk_factors = analyze_risk_factors(company, kg_features, original_score)

        adjusted_company = copy.deepcopy(company)
        adjusted_kg_features = kg_features.copy()

        applied_changes = {}
        for path, value in adjustments.items():
            applied = self._apply_adjustment(
                adjusted_company, adjusted_kg_features, path, value
            )
            if applied:
                applied_changes[path] = value

        adjusted_score = predict_score(
            adjusted_company, adjusted_kg_features, self.model, self.scaler
        )
        adjusted_rating = score_to_rating(adjusted_score)
        adjusted_risk_factors = analyze_risk_factors(
            adjusted_company, adjusted_kg_features, adjusted_score
        )

        score_change = adjusted_score - original_score

        from config import get_rating_thresholds
        thresholds = get_rating_thresholds()
        rating_order = list(thresholds.keys())

        original_idx = rating_order.index(original_rating) if original_rating in rating_order else -1
        adjusted_idx = rating_order.index(adjusted_rating) if adjusted_rating in rating_order else -1

        if adjusted_idx < original_idx:
            rating_change = "升级"
        elif adjusted_idx > original_idx:
            rating_change = "降级"
        else:
            rating_change = "维持"

        original_strengths = set(
            f['description'] for f in original_risk_factors if f['direction'] == '正面影响'
        )
        adjusted_strengths = set(
            f['description'] for f in adjusted_risk_factors if f['direction'] == '正面影响'
        )
        key_improvements = list(adjusted_strengths - original_strengths)[:5]
        key_deteriorations = list(original_strengths - adjusted_strengths)[:5]

        return SimulationResult(
            original_score=round(original_score, 2),
            original_rating=original_rating,
            adjusted_score=round(adjusted_score, 2),
            adjusted_rating=adjusted_rating,
            score_change=round(score_change, 2),
            rating_change=rating_change,
            changed_factors=applied_changes,
            original_risk_factors=original_risk_factors[:10],
            adjusted_risk_factors=adjusted_risk_factors[:10],
            key_improvements=key_improvements,
            key_deteriorations=key_deteriorations,
        )

    def simulate_multiple_scenarios(
        self,
        company: CompanyInput,
        kg_features: Dict[str, float],
        scenarios: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        results = []
        for scenario in scenarios:
            scenario_name = scenario.get("name", "未命名场景")
            adjustments = scenario.get("adjustments", {})
            result = self.simulate(company, kg_features, adjustments)
            results.append({
                "scenario_name": scenario_name,
                **result.__dict__
            })
        return results

    def get_optimization_suggestions(
        self,
        company: CompanyInput,
        kg_features: Dict[str, float],
        target_score: float = 700
    ) -> List[Dict[str, Any]]:
        current_score = predict_score(company, kg_features, self.model, self.scaler)
        current_rating = score_to_rating(current_score)

        suggestions = []
        if current_score >= target_score:
            suggestions.append({
                "type": "info",
                "title": "已达到目标评分",
                "description": f"当前评分 {current_score:.1f} 已达到或超过目标评分 {target_score}",
                "impact": 0,
                "priority": "低"
            })
            return suggestions

        score_needed = target_score - current_score

        jr = company.judicial_risk
        if jr.lawsuit_count > 0:
            impact = min(jr.lawsuit_count * 8, score_needed * 0.3)
            suggestions.append({
                "type": "judicial",
                "title": "减少诉讼案件",
                "description": f"当前有 {jr.lawsuit_count} 件诉讼案件，如能妥善处理可显著提升评分",
                "estimated_impact": impact,
                "priority": "高" if jr.lawsuit_count > 5 else "中"
            })

        if jr.executed_person_count > 0:
            impact = min(jr.executed_person_count * 30, score_needed * 0.5)
            suggestions.append({
                "type": "judicial",
                "title": "消除被执行人记录",
                "description": f"当前有 {jr.executed_person_count} 条被执行人记录，建议尽快履行相关义务",
                "estimated_impact": impact,
                "priority": "高"
            })

        if jr.dishonest_records > 0:
            impact = min(jr.dishonest_records * 25, score_needed * 0.4)
            suggestions.append({
                "type": "judicial",
                "title": "消除失信记录",
                "description": f"当前有 {jr.dishonest_records} 条失信记录，对信用影响极大",
                "estimated_impact": impact,
                "priority": "高"
            })

        tr = company.tax_record
        if tr.tax_arrears_count > 0:
            impact = min(tr.tax_arrears_count * 10, score_needed * 0.25)
            suggestions.append({
                "type": "tax",
                "title": "补缴欠税",
                "description": f"当前有 {tr.tax_arrears_count} 次欠税记录，建议尽快补缴",
                "estimated_impact": impact,
                "priority": "高" if tr.tax_arrears_count > 2 else "中"
            })

        if tr.tax_credit_rating in ["C", "D"]:
            impact = 25 if tr.tax_credit_rating == "D" else 15
            suggestions.append({
                "type": "tax",
                "title": "提升纳税信用等级",
                "description": f"当前纳税信用等级为 {tr.tax_credit_rating}，提升至 A 级可显著加分",
                "estimated_impact": impact,
                "priority": "中"
            })

        fi = company.financial_info
        if fi.debt_to_equity_ratio > 1.0:
            impact = min((fi.debt_to_equity_ratio - 1.0) * 20, score_needed * 0.2)
            suggestions.append({
                "type": "financial",
                "title": "降低资产负债率",
                "description": f"当前资产负债率 {fi.debt_to_equity_ratio:.2f} 偏高，建议优化资本结构",
                "estimated_impact": impact,
                "priority": "中"
            })

        suggestions.sort(key=lambda x: x.get("estimated_impact", 0), reverse=True)

        return suggestions

    def _apply_adjustment(
        self,
        company: CompanyInput,
        kg_features: Dict[str, float],
        factor_path: str,
        value: Any
    ) -> bool:
        try:
            parts = factor_path.split(".")
            if len(parts) == 2:
                category, field = parts
                if category == "kg_features":
                    if field in kg_features:
                        kg_features[field] = float(value)
                        return True
                else:
                    obj = getattr(company, category, None)
                    if obj is not None and hasattr(obj, field):
                        if field == "tax_credit_rating":
                            setattr(obj, field, str(value))
                        else:
                            setattr(obj, field, type(getattr(obj, field))(value))
                        return True
            elif len(parts) == 3 and parts[0] == "loan":
                if company.loan_records:
                    field = parts[2]
                    if hasattr(company.loan_records[0], field):
                        setattr(company.loan_records[0], field, int(value))
                        return True
            return False
        except (ValueError, TypeError, AttributeError):
            return False


_simulator = ScoreSimulator()


def get_simulator() -> ScoreSimulator:
    return _simulator
