import pandas as pd
from typing import Dict, Any, List, Optional
from decimal import Decimal, ROUND_HALF_UP
from datetime import datetime
from app.models.schemas import (
    PricingComparisonResponse, PricingComparisonItem,
    PricingScenario, PolicyInfo, DrivingBehaviorData,
    LoyaltyData, HealthScoreData, PremiumBreakdown
)
from app.services import actuarial_engine, ubi_pricing_engine, dynamic_discount_engine


class PricingComparisonEngine:
    def __init__(self):
        self.precision = Decimal('0.01')
        self._init_default_scenarios()

    def _init_default_scenarios(self):
        self.default_scenarios = [
            PricingScenario(
                scenario_name='基础定价',
                scenario_id='base_pricing',
                description='仅使用基础费率和传统风险因子，不使用UBI和动态折扣',
                apply_ubi=False,
                apply_dynamic_discount=False,
                apply_risk_scorecard=False
            ),
            PricingScenario(
                scenario_name='UBI定价',
                scenario_id='ubi_pricing',
                description='使用驾驶行为数据进行UBI保费调整',
                apply_ubi=True,
                apply_dynamic_discount=False,
                apply_risk_scorecard=False
            ),
            PricingScenario(
                scenario_name='动态折扣定价',
                scenario_id='dynamic_discount_pricing',
                description='使用忠诚度、健康等多维度动态折扣',
                apply_ubi=False,
                apply_dynamic_discount=True,
                apply_risk_scorecard=False
            ),
            PricingScenario(
                scenario_name='风险评分卡定价',
                scenario_id='scorecard_pricing',
                description='使用多维度风险评分卡进行保费调整',
                apply_ubi=False,
                apply_dynamic_discount=False,
                apply_risk_scorecard=True
            ),
            PricingScenario(
                scenario_name='综合定价(全功能)',
                scenario_id='full_pricing',
                description='同时使用UBI、动态折扣和风险评分卡的综合定价',
                apply_ubi=True,
                apply_dynamic_discount=True,
                apply_risk_scorecard=True
            )
        ]

    def _round_decimal(self, value: Decimal) -> Decimal:
        return value.quantize(self.precision, rounding=ROUND_HALF_UP)

    def calculate_scenario_premium(
        self,
        policy_info: PolicyInfo,
        scenario: PricingScenario,
        driving_data: Optional[DrivingBehaviorData] = None,
        loyalty_data: Optional[LoyaltyData] = None,
        health_data: Optional[HealthScoreData] = None,
        risk_adjustment: Optional[Decimal] = None
    ) -> PricingComparisonItem:
        factors = []
        base_premium = Decimal('5000.00')
        risk_adjust_amount = risk_adjustment or Decimal('0')
        ubi_adjustment = Decimal('0')
        dynamic_discount_amount = Decimal('0')

        if policy_info.product_type == '车险':
            base_premium = Decimal('4500.00')
        elif policy_info.product_type == '寿险':
            base_premium = Decimal('8000.00')
        elif policy_info.product_type == '健康险':
            base_premium = Decimal('3500.00')

        coverage_multiplier = Decimal(str(policy_info.coverage_period / 12))
        base_premium = base_premium * coverage_multiplier

        if risk_adjustment is None:
            risk_multiplier = (Decimal('1000000') - policy_info.insured_amount).abs() / Decimal('1000000')
            risk_adjust_amount = base_premium * risk_multiplier * Decimal('0.1')

        if scenario.apply_ubi and driving_data:
            ubi_result = ubi_pricing_engine.calculate_ubi_adjustment(driving_data, base_premium)
            ubi_adjustment = ubi_result.total_ubi_adjustment

        if scenario.apply_dynamic_discount:
            discount_result = dynamic_discount_engine.calculate_dynamic_discounts(
                base_premium, loyalty_data, health_data, driving_data
            )
            dynamic_discount_amount = discount_result.total_dynamic_discount

        final_premium = base_premium + risk_adjust_amount + ubi_adjustment - dynamic_discount_amount
        final_premium = self._round_decimal(final_premium)
        base_premium = self._round_decimal(base_premium)
        risk_adjust_amount = self._round_decimal(risk_adjust_amount)
        ubi_adjustment = self._round_decimal(ubi_adjustment)
        dynamic_discount_amount = self._round_decimal(dynamic_discount_amount)

        total_savings = self._round_decimal(base_premium - final_premium)
        savings_percentage = float(total_savings / base_premium * Decimal('100')) if base_premium > 0 else 0

        return PricingComparisonItem(
            scenario_name=scenario.scenario_name,
            scenario_id=scenario.scenario_id,
            base_premium=base_premium,
            risk_adjustment=risk_adjust_amount,
            ubi_adjustment=ubi_adjustment,
            dynamic_discounts=dynamic_discount_amount,
            final_premium=final_premium,
            total_savings=total_savings,
            savings_percentage=round(savings_percentage, 2)
        )

    def compare_scenarios(
        self,
        policy_info: PolicyInfo,
        scenarios: Optional[List[PricingScenario]] = None,
        driving_data: Optional[DrivingBehaviorData] = None,
        loyalty_data: Optional[LoyaltyData] = None,
        health_data: Optional[HealthScoreData] = None
    ) -> PricingComparisonResponse:
        scenarios = scenarios or self.default_scenarios

        base_scenario = next((s for s in scenarios if s.scenario_id == 'base_pricing'), scenarios[0])
        base_result = self.calculate_scenario_premium(
            policy_info, base_scenario, driving_data, loyalty_data, health_data
        )

        comparison_results = []
        for scenario in scenarios:
            if scenario.scenario_id != base_scenario.scenario_id:
                result = self.calculate_scenario_premium(
                    policy_info, scenario, driving_data, loyalty_data, health_data
                )
                comparison_results.append(result)

        all_results = [base_result] + comparison_results
        best_scenario = min(all_results, key=lambda x: x.final_premium)
        max_savings = best_scenario.total_savings

        chart_data = self._generate_chart_data(base_result, comparison_results)
        recommendations = self._generate_recommendations(all_results, best_scenario)

        return PricingComparisonResponse(
            policy_id=policy_info.policy_id,
            base_scenario=base_result,
            comparison_scenarios=comparison_results,
            best_scenario=best_scenario.scenario_id,
            max_savings=max_savings,
            chart_data=chart_data,
            recommendations=recommendations,
            calculation_date=datetime.now()
        )

    def _generate_chart_data(self, base_scenario: PricingComparisonItem, comparison_scenarios: List[PricingComparisonItem]) -> Dict[str, Any]:
        all_scenarios = [base_scenario] + comparison_scenarios

        labels = [s.scenario_name for s in all_scenarios]
        final_premiums = [float(s.final_premium) for s in all_scenarios]
        savings = [float(s.total_savings) for s in all_scenarios]
        savings_percentages = [s.savings_percentage for s in all_scenarios]

        breakdown_data = {
            'base_premium': [float(s.base_premium) for s in all_scenarios],
            'risk_adjustment': [float(s.risk_adjustment) for s in all_scenarios],
            'ubi_adjustment': [float(s.ubi_adjustment) for s in all_scenarios],
            'dynamic_discounts': [float(s.dynamic_discounts) for s in all_scenarios]
        }

        return {
            'chart_type': 'bar',
            'labels': labels,
            'final_premiums': final_premiums,
            'savings': savings,
            'savings_percentages': savings_percentages,
            'breakdown': breakdown_data,
            'recommended_scenario': labels[savings.index(max(savings))]
        }

    def _generate_recommendations(self, all_results: List[PricingComparisonItem], best_result: PricingComparisonItem) -> List[str]:
        recommendations = []

        recommendations.append(f"推荐选择「{best_result.scenario_name}」，可节省 ¥{float(best_result.total_savings):,.2f}（{best_result.savings_percentage:.2f}%）")

        ubi_scenarios = [s for s in all_results if 'UBI' in s.scenario_name]
        if ubi_scenarios and float(ubi_scenarios[0].ubi_adjustment) < 0:
            savings_from_ubi = abs(float(ubi_scenarios[0].ubi_adjustment))
            recommendations.append(f"UBI驾驶行为定价可为您节省 ¥{savings_from_ubi:,.2f}，建议安装OBD设备获取准确数据")

        discount_scenarios = [s for s in all_results if '动态折扣' in s.scenario_name]
        if discount_scenarios and float(discount_scenarios[0].dynamic_discounts) > 0:
            discount_amount = float(discount_scenarios[0].dynamic_discounts)
            recommendations.append(f"动态折扣已为您节省 ¥{discount_amount:,.2f}，继续保持良好的驾驶和健康习惯")

        full_pricing = [s for s in all_results if '综合定价' in s.scenario_name]
        if full_pricing:
            total_savings = float(full_pricing[0].total_savings)
            if total_savings > 0:
                recommendations.append(f"使用综合定价（UBI+动态折扣+风险评分）可获得最大优惠，累计节省 ¥{total_savings:,.2f}")

        return recommendations

    def get_default_scenarios(self) -> List[PricingScenario]:
        return self.default_scenarios

    def generate_comparison_report(
        self,
        comparison_result: PricingComparisonResponse
    ) -> Dict[str, Any]:
        all_scenarios = [comparison_result.base_scenario] + comparison_result.comparison_scenarios
        sorted_scenarios = sorted(all_scenarios, key=lambda x: x.final_premium)

        report = {
            'policy_id': comparison_result.policy_id,
            'calculation_date': comparison_result.calculation_date.isoformat(),
            'summary': {
                'total_scenarios': len(all_scenarios),
                'best_scenario': sorted_scenarios[0].scenario_name,
                'max_savings': float(sorted_scenarios[0].total_savings),
                'max_savings_percentage': sorted_scenarios[0].savings_percentage,
                'worst_scenario': sorted_scenarios[-1].scenario_name,
                'price_range': float(sorted_scenarios[-1].final_premium - sorted_scenarios[0].final_premium)
            },
            'detailed_comparison': [
                {
                    'rank': idx + 1,
                    'scenario_name': s.scenario_name,
                    'scenario_id': s.scenario_id,
                    'final_premium': float(s.final_premium),
                    'savings': float(s.total_savings),
                    'savings_percentage': s.savings_percentage
                }
                for idx, s in enumerate(sorted_scenarios)
            ],
            'visualization': comparison_result.chart_data,
            'recommendations': comparison_result.recommendations
        }

        return report


pricing_comparison_engine = PricingComparisonEngine()
