import numpy as np
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field

from config import get_rating_thresholds, get_industry_baseline
from data.models import CompanyInput
from model.feature_engineering import score_to_rating, score_to_risk_level


RATINGS = ["AAA", "AA", "A", "BBB", "BB", "B", "CCC", "CC", "C", "D"]


@dataclass
class MigrationMatrix:
    ratings: List[str]
    matrix: List[List[float]]
    period: str = "1年"
    industry: str = "default"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ratings": self.ratings,
            "matrix": self.matrix,
            "period": self.period,
            "industry": self.industry,
            "cumulative_matrix": self._get_cumulative_matrix()
        }

    def _get_cumulative_matrix(self) -> List[List[float]]:
        cumulative = []
        for row in self.matrix:
            cum_row = []
            running_sum = 0.0
            for p in row:
                running_sum += p
                cum_row.append(round(running_sum, 4))
            cumulative.append(cum_row)
        return cumulative


@dataclass
class MigrationForecast:
    company_id: str
    current_rating: str
    current_score: float
    forecast_periods: List[str]
    migration_probabilities: Dict[str, Dict[str, float]]
    most_likely_rating: str
    upgrade_probability: float
    downgrade_probability: float
    maintain_probability: float
    industry: str
    risk_factors: Dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "company_id": self.company_id,
            "current_rating": self.current_rating,
            "current_score": self.current_score,
            "forecast_periods": self.forecast_periods,
            "migration_probabilities": self.migration_probabilities,
            "most_likely_rating": self.most_likely_rating,
            "upgrade_probability": round(self.upgrade_probability, 4),
            "downgrade_probability": round(self.downgrade_probability, 4),
            "maintain_probability": round(self.maintain_probability, 4),
            "industry": self.industry,
            "risk_factors": self.risk_factors,
            "recommendation": self._generate_recommendation()
        }

    def _generate_recommendation(self) -> str:
        if self.downgrade_probability > 0.3:
            return f"评级下调风险较高（{self.downgrade_probability:.1%}），建议加强监测，关注企业经营状况变化。"
        elif self.upgrade_probability > 0.2:
            return f"存在评级上调可能（{self.upgrade_probability:.1%}），可关注企业成长潜力，适时调整授信策略。"
        else:
            return f"评级维持概率较高（{self.maintain_probability:.1%}），建议维持现有授信政策，持续关注。"


_BASE_MIGRATION_MATRIX = [
    [0.9000, 0.0800, 0.0150, 0.0030, 0.0010, 0.0005, 0.0003, 0.0001, 0.0001, 0.0000],
    [0.0700, 0.8500, 0.0600, 0.0150, 0.0030, 0.0010, 0.0005, 0.0003, 0.0001, 0.0001],
    [0.0100, 0.0650, 0.8200, 0.0800, 0.0180, 0.0040, 0.0015, 0.0008, 0.0004, 0.0003],
    [0.0030, 0.0150, 0.0700, 0.7800, 0.1000, 0.0220, 0.0060, 0.0025, 0.0010, 0.0005],
    [0.0010, 0.0040, 0.0200, 0.1050, 0.7200, 0.1100, 0.0280, 0.0070, 0.0030, 0.0020],
    [0.0005, 0.0015, 0.0060, 0.0300, 0.1100, 0.6800, 0.1200, 0.0350, 0.0100, 0.0070],
    [0.0003, 0.0008, 0.0025, 0.0080, 0.0350, 0.1250, 0.5800, 0.1500, 0.0550, 0.0434],
    [0.0001, 0.0004, 0.0010, 0.0030, 0.0100, 0.0400, 0.1400, 0.5000, 0.1800, 0.1255],
    [0.0001, 0.0002, 0.0005, 0.0015, 0.0050, 0.0150, 0.0500, 0.1500, 0.4500, 0.3277],
    [0.0000, 0.0000, 0.0000, 0.0000, 0.0000, 0.0000, 0.0000, 0.0000, 0.0000, 1.0000],
]

_INDUSTRY_MIGRATION_ADJUSTMENTS = {
    "金融业": {
        "upgrade_mult": 0.9,
        "downgrade_mult": 1.2,
        "volatility": 1.2,
    },
    "房地产": {
        "upgrade_mult": 0.8,
        "downgrade_mult": 1.3,
        "volatility": 1.3,
    },
    "建筑业": {
        "upgrade_mult": 0.9,
        "downgrade_mult": 1.15,
        "volatility": 1.15,
    },
    "制造业": {
        "upgrade_mult": 1.0,
        "downgrade_mult": 1.0,
        "volatility": 1.0,
    },
    "信息技术": {
        "upgrade_mult": 1.1,
        "downgrade_mult": 1.1,
        "volatility": 1.15,
    },
    "生物医药": {
        "upgrade_mult": 1.0,
        "downgrade_mult": 1.2,
        "volatility": 1.25,
    },
    "新能源": {
        "upgrade_mult": 1.15,
        "downgrade_mult": 1.1,
        "volatility": 1.2,
    },
    "default": {
        "upgrade_mult": 1.0,
        "downgrade_mult": 1.0,
        "volatility": 1.0,
    },
}


class RatingMigrationAnalyzer:
    def __init__(self):
        self.ratings = RATINGS

    def get_migration_matrix(
        self,
        industry: str = "default",
        period: str = "1年"
    ) -> MigrationMatrix:
        base_matrix = np.array(_BASE_MIGRATION_MATRIX, dtype=np.float64)

        adjustment = _INDUSTRY_MIGRATION_ADJUSTMENTS.get(
            industry, _INDUSTRY_MIGRATION_ADJUSTMENTS["default"]
        )

        adjusted_matrix = self._adjust_matrix_for_industry(base_matrix, adjustment)

        if period == "3年":
            adjusted_matrix = np.linalg.matrix_power(adjusted_matrix, 3)
        elif period == "5年":
            adjusted_matrix = np.linalg.matrix_power(adjusted_matrix, 5)

        adjusted_matrix = np.round(adjusted_matrix, 4)
        for i in range(len(adjusted_matrix)):
            row_sum = adjusted_matrix[i].sum()
            if row_sum > 0:
                adjusted_matrix[i] = adjusted_matrix[i] / row_sum

        return MigrationMatrix(
            ratings=self.ratings,
            matrix=adjusted_matrix.tolist(),
            period=period,
            industry=industry
        )

    def get_company_migration_forecast(
        self,
        company: CompanyInput,
        current_score: float,
        forecast_years: List[int] = None
    ) -> MigrationForecast:
        if forecast_years is None:
            forecast_years = [1, 3, 5]

        current_rating = score_to_rating(current_score)
        industry = company.business_info.industry
        current_idx = self.ratings.index(current_rating) if current_rating in self.ratings else len(self.ratings) - 1

        migration_probs = {}
        for year in forecast_years:
            period = f"{year}年"
            matrix = self.get_migration_matrix(industry, period)
            probs = matrix.matrix[current_idx]
            migration_probs[period] = {
                rating: prob for rating, prob in zip(self.ratings, probs)
            }

        one_year_probs = migration_probs.get("1年", {})
        upgrade_prob = 0.0
        downgrade_prob = 0.0
        maintain_prob = one_year_probs.get(current_rating, 0.0)

        for rating, prob in one_year_probs.items():
            rating_idx = self.ratings.index(rating) if rating in self.ratings else -1
            if rating_idx < current_idx:
                upgrade_prob += prob
            elif rating_idx > current_idx:
                downgrade_prob += prob

        most_likely = max(one_year_probs.items(), key=lambda x: x[1])[0]

        risk_factors = self._calculate_migration_risk_factors(company, current_score)

        return MigrationForecast(
            company_id=company.business_info.company_id,
            current_rating=current_rating,
            current_score=round(current_score, 2),
            forecast_periods=[f"{y}年" for y in forecast_years],
            migration_probabilities=migration_probs,
            most_likely_rating=most_likely,
            upgrade_probability=upgrade_prob,
            downgrade_probability=downgrade_prob,
            maintain_probability=maintain_prob,
            industry=industry,
            risk_factors=risk_factors
        )

    def get_multi_year_migration_summary(
        self,
        current_rating: str,
        industry: str = "default"
    ) -> Dict[str, Any]:
        periods = ["1年", "3年", "5年"]
        summary = {
            "current_rating": current_rating,
            "industry": industry,
            "periods": {}
        }

        for period in periods:
            matrix = self.get_migration_matrix(industry, period)
            idx = self.ratings.index(current_rating) if current_rating in self.ratings else len(self.ratings) - 1
            probs = matrix.matrix[idx]

            upgrade = 0.0
            downgrade = 0.0
            maintain = probs[idx]

            for i, p in enumerate(probs):
                if i < idx:
                    upgrade += p
                elif i > idx:
                    downgrade += p

            summary["periods"][period] = {
                "upgrade_probability": round(upgrade, 4),
                "downgrade_probability": round(downgrade, 4),
                "maintain_probability": round(maintain, 4),
                "most_likely_rating": self.ratings[np.argmax(probs)],
                "default_probability": round(probs[-1], 4),
                "investment_grade_probability": round(sum(probs[:4]), 4),
                "speculative_grade_probability": round(sum(probs[4:]), 4),
            }

        return summary

    def calculate_transition_heatmap(
        self,
        industry: str = "default"
    ) -> Dict[str, Any]:
        matrix = self.get_migration_matrix(industry, "1年")
        heatmap_data = []
        for i, from_rating in enumerate(self.ratings):
            for j, to_rating in enumerate(self.ratings):
                prob = matrix.matrix[i][j]
                intensity = min(prob * 5, 1.0)
                heatmap_data.append({
                    "from": from_rating,
                    "to": to_rating,
                    "probability": prob,
                    "intensity": round(intensity, 4),
                    "type": self._classify_transition(i, j)
                })
        return {
            "industry": industry,
            "heatmap": heatmap_data,
            "matrix": matrix.matrix,
            "ratings": self.ratings
        }

    def _adjust_matrix_for_industry(
        self,
        matrix: np.ndarray,
        adjustment: Dict[str, float]
    ) -> np.ndarray:
        upgrade_mult = adjustment.get("upgrade_mult", 1.0)
        downgrade_mult = adjustment.get("downgrade_mult", 1.0)
        volatility = adjustment.get("volatility", 1.0)

        adjusted = matrix.copy()
        n = len(matrix)

        for i in range(n - 1):
            for j in range(n):
                if j < i:
                    adjusted[i, j] *= upgrade_mult * volatility
                elif j > i:
                    adjusted[i, j] *= downgrade_mult * volatility

            row_sum = adjusted[i].sum()
            if row_sum > 0:
                adjusted[i] = adjusted[i] / row_sum

        return adjusted

    def _calculate_migration_risk_factors(
        self,
        company: CompanyInput,
        current_score: float
    ) -> Dict[str, float]:
        jr = company.judicial_risk
        fi = company.financial_info
        tr = company.tax_record

        factors = {}

        industry_baseline = get_industry_baseline(company.business_info.industry)
        baseline_score = industry_baseline.get("baseline_score", 600)
        volatility = industry_baseline.get("volatility", 0.18)
        factors["score_vs_industry_baseline"] = round(current_score - baseline_score, 2)
        factors["industry_volatility"] = volatility

        if fi.debt_to_equity_ratio > 1.5:
            factors["high_leverage_risk"] = 0.3
        elif fi.debt_to_equity_ratio > 1.0:
            factors["moderate_leverage_risk"] = 0.15
        else:
            factors["leverage_safe"] = 0.05

        if fi.net_profit < 0:
            factors["loss_making_risk"] = 0.25
        elif fi.revenue > 0 and fi.net_profit / fi.revenue < 0.02:
            factors["low_margin_risk"] = 0.1
        else:
            factors["profitability_stable"] = 0.05

        if jr.lawsuit_count > 10:
            factors["high_litigation_risk"] = 0.35
        elif jr.lawsuit_count > 5:
            factors["moderate_litigation_risk"] = 0.15
        else:
            factors["litigation_low"] = 0.05

        if tr.tax_arrears_count > 0:
            factors["tax_arrears_risk"] = 0.2
        else:
            factors["tax_compliant"] = 0.05

        if jr.executed_person_count > 0:
            factors["execution_risk"] = 0.4

        if jr.dishonest_records > 0:
            factors["dishonest_risk"] = 0.5

        if company.loan_records:
            max_overdue = max(l.overdue_days for l in company.loan_records)
            if max_overdue > 90:
                factors["severe_overdue_risk"] = 0.45
            elif max_overdue > 30:
                factors["moderate_overdue_risk"] = 0.25
            elif max_overdue > 0:
                factors["minor_overdue_risk"] = 0.1

        return {k: round(v, 4) for k, v in factors.items()}

    def _classify_transition(self, from_idx: int, to_idx: int) -> str:
        if from_idx == to_idx:
            return "maintain"
        elif to_idx < from_idx:
            if from_idx - to_idx >= 2:
                return "major_upgrade"
            else:
                return "minor_upgrade"
        else:
            if to_idx - from_idx >= 2:
                return "major_downgrade"
            else:
                return "minor_downgrade"


_analyzer = RatingMigrationAnalyzer()


def get_migration_analyzer() -> RatingMigrationAnalyzer:
    return _analyzer
