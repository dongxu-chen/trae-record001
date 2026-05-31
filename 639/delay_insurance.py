import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta


@dataclass
class InsuranceProduct:
    id: str
    name: str
    provider: str
    premium: float
    coverage_amount: float
    min_delay_minutes: int
    max_delay_minutes: Optional[int]
    covered_reasons: List[str]
    description: str
    rating: float


INSURANCE_PRODUCTS = [
    InsuranceProduct(
        id='INS001',
        name='延误无忧-基础版',
        provider='平安保险',
        premium=20.0,
        coverage_amount=200.0,
        min_delay_minutes=60,
        max_delay_minutes=None,
        covered_reasons=['天气原因', '流量控制', '空中交通管制', '航空公司计划'],
        description='航班延误60分钟以上赔付200元',
        rating=4.5
    ),
    InsuranceProduct(
        id='INS002',
        name='延误无忧-进阶版',
        provider='平安保险',
        premium=40.0,
        coverage_amount=400.0,
        min_delay_minutes=60,
        max_delay_minutes=None,
        covered_reasons=['天气原因', '流量控制', '空中交通管制', '航空公司计划', '机械故障'],
        description='航班延误60分钟以上赔付400元，涵盖机械故障',
        rating=4.7
    ),
    InsuranceProduct(
        id='INS003',
        name='速达保障计划',
        provider='太平洋保险',
        premium=30.0,
        coverage_amount=300.0,
        min_delay_minutes=120,
        max_delay_minutes=None,
        covered_reasons=['天气原因', '流量控制', '空中交通管制', '航空公司计划'],
        description='航班延误2小时以上赔付300元，性价比高',
        rating=4.3
    ),
    InsuranceProduct(
        id='INS004',
        name='白金延误险',
        provider='中国人寿',
        premium=68.0,
        coverage_amount=800.0,
        min_delay_minutes=60,
        max_delay_minutes=None,
        covered_reasons=['天气原因', '流量控制', '空中交通管制', '航空公司计划', '机械故障', '机场保障', '油料供应'],
        description='高保额全保障，延误60分钟赔付800元',
        rating=4.8
    ),
    InsuranceProduct(
        id='INS005',
        name='经济实惠险',
        provider='泰康保险',
        premium=12.0,
        coverage_amount=100.0,
        min_delay_minutes=180,
        max_delay_minutes=None,
        covered_reasons=['天气原因', '流量控制', '空中交通管制'],
        description='低保费高门槛，延误3小时赔付100元',
        rating=4.0
    ),
    InsuranceProduct(
        id='INS006',
        name='取消改签险',
        provider='新华保险',
        premium=50.0,
        coverage_amount=500.0,
        min_delay_minutes=240,
        max_delay_minutes=None,
        covered_reasons=['天气原因', '流量控制', '空中交通管制', '航空公司计划', '机械故障'],
        description='延误4小时赔付500元，支持免费改签',
        rating=4.6
    ),
]


class DelayInsuranceRecommender:
    def __init__(self, products: List[InsuranceProduct] = None):
        self.products = products or INSURANCE_PRODUCTS
        
    def calculate_expected_payout(self, product: InsuranceProduct, 
                                   delay_probability: float,
                                   delay_minutes: float,
                                   delay_reason: str = None) -> float:
        if delay_probability < 0.1:
            return 0.0
        
        delay_threshold = product.min_delay_minutes
        if delay_minutes < delay_threshold:
            prob_meeting_threshold = delay_probability * (delay_minutes / max(delay_threshold, delay_minutes))
        else:
            prob_meeting_threshold = delay_probability
        
        reason_covered = True
        if delay_reason and delay_reason != '无延误':
            reason_covered = delay_reason in product.covered_reasons
        
        expected_payout = product.coverage_amount * prob_meeting_threshold
        if not reason_covered:
            expected_payout *= 0.3
        
        return expected_payout
    
    def calculate_value_score(self, product: InsuranceProduct, 
                               expected_payout: float) -> Dict:
        net_value = expected_payout - product.premium
        roi = (expected_payout / product.premium - 1) * 100 if product.premium > 0 else 0
        value_score = net_value * 0.6 + roi * 0.01 + product.rating * 10
        
        return {
            'expected_payout': expected_payout,
            'net_value': net_value,
            'roi': roi,
            'value_score': value_score
        }
    
    def recommend_insurance(self, delay_probability: float,
                            predicted_delay_minutes: float,
                            predicted_delay_reason: str = None,
                            risk_preference: str = 'balanced',
                            budget: float = None) -> List[Dict]:
        recommendations = []
        
        for product in self.products:
            expected_payout = self.calculate_expected_payout(
                product, delay_probability, predicted_delay_minutes, predicted_delay_reason
            )
            
            scores = self.calculate_value_score(product, expected_payout)
            
            if budget and product.premium > budget:
                continue
            
            recommendation = {
                'product_id': product.id,
                'product_name': product.name,
                'provider': product.provider,
                'premium': product.premium,
                'coverage_amount': product.coverage_amount,
                'min_delay_minutes': product.min_delay_minutes,
                'covered_reasons': product.covered_reasons,
                'description': product.description,
                'rating': product.rating,
                'expected_payout': round(expected_payout, 2),
                'net_value': round(scores['net_value'], 2),
                'roi': round(scores['roi'], 2),
                'value_score': round(scores['value_score'], 2),
                'recommendation_level': self._get_recommendation_level(
                    scores['value_score'], delay_probability, risk_preference
                )
            }
            recommendations.append(recommendation)
        
        recommendations = self._adjust_for_risk_preference(
            recommendations, risk_preference, delay_probability
        )
        
        recommendations.sort(key=lambda x: x['value_score'], reverse=True)
        
        return recommendations
    
    def _get_recommendation_level(self, value_score: float, delay_prob: float, 
                                    risk_preference: str) -> str:
        if risk_preference == 'conservative':
            threshold_high, threshold_med = 50, 30
        elif risk_preference == 'aggressive':
            threshold_high, threshold_med = 70, 50
        else:
            threshold_high, threshold_med = 60, 40
        
        if delay_prob < 0.2:
            return '不推荐'
        
        if value_score >= threshold_high:
            return '强烈推荐'
        elif value_score >= threshold_med:
            return '推荐'
        elif value_score >= 0:
            return '可考虑'
        else:
            return '不推荐'
    
    def _adjust_for_risk_preference(self, recommendations: List[Dict], 
                                      risk_preference: str, 
                                      delay_prob: float) -> List[Dict]:
        for rec in recommendations:
            if risk_preference == 'conservative':
                if rec['premium'] < 30 and delay_prob < 0.5:
                    rec['value_score'] += 15
            elif risk_preference == 'aggressive':
                if rec['coverage_amount'] >= 400:
                    rec['value_score'] += 20
        
        return recommendations
    
    def get_best_recommendation(self, recommendations: List[Dict]) -> Optional[Dict]:
        if not recommendations:
            return None
        
        for rec in recommendations:
            if rec['recommendation_level'] in ['强烈推荐', '推荐']:
                return rec
        
        return recommendations[0]
    
    def generate_insurance_comparison_table(self, recommendations: List[Dict]) -> pd.DataFrame:
        df = pd.DataFrame(recommendations)
        display_df = df[[
            'product_name', 'provider', 'premium', 'coverage_amount',
            'min_delay_minutes', 'rating', 'expected_payout', 
            'net_value', 'roi', 'recommendation_level'
        ]].copy()
        
        display_df.columns = [
            '产品名称', '保险公司', '保费(元)', '保额(元)',
            '最低延误(分钟)', '评分', '预期赔付(元)',
            '净收益(元)', '投资回报率(%)', '推荐等级'
        ]
        
        return display_df


def get_risk_preference_description(preference: str) -> str:
    descriptions = {
        'conservative': '保守型：优先考虑低保费、低风险产品，适合准点率较高的航班',
        'balanced': '平衡型：在保费和保障之间寻求平衡，适合大多数情况',
        'aggressive': '进取型：优先考虑高保额产品，适合高延误风险的航班'
    }
    return descriptions.get(preference, '')


if __name__ == '__main__':
    recommender = DelayInsuranceRecommender()
    
    print("=== 测试延误保险推荐 ===")
    
    test_cases = [
        (0.7, 120, '天气原因', 'balanced'),
        (0.3, 45, '流量控制', 'conservative'),
        (0.8, 180, '机械故障', 'aggressive'),
    ]
    
    for delay_prob, delay_min, reason, risk_pref in test_cases:
        print(f"\n--- 测试场景: 延误概率={delay_prob*100:.0f}%, 延误时间={delay_min}分钟, 原因={reason}, 风险偏好={risk_pref}")
        recs = recommender.recommend_insurance(delay_prob, delay_min, reason, risk_pref)
        best = recommender.get_best_recommendation(recs)
        if best:
            print(f"最佳推荐: {best['product_name']} - {best['recommendation_level']}")
            print(f"  保费: ¥{best['premium']}, 保额: ¥{best['coverage_amount']}")
            print(f"  预期赔付: ¥{best['expected_payout']}, 净收益: ¥{best['net_value']}")
