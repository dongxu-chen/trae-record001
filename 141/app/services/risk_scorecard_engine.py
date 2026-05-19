import pandas as pd
from typing import Dict, Any, Optional, List
from decimal import Decimal, ROUND_HALF_UP
from app.models.schemas import RiskScoreCardResult, RiskScoreCardFactor, DrivingBehaviorData, HealthScoreData


class RiskScoreCardEngine:
    def __init__(self):
        self.precision = Decimal('0.01')
        self._init_risk_factors()
        self._init_score_ranges()

    def _init_risk_factors(self):
        self.risk_factors = {
            'demographic': {
                'age': {
                    'weight': 0.15,
                    'tiers': [
                        {'min': 18, 'max': 25, 'score': 40, 'risk': 'high', 'description': '年轻驾驶员风险较高'},
                        {'min': 26, 'max': 35, 'score': 60, 'risk': 'medium', 'description': '成年驾驶员中等风险'},
                        {'min': 36, 'max': 55, 'score': 85, 'risk': 'low', 'description': '成熟驾驶员低风险'},
                        {'min': 56, 'max': 75, 'score': 70, 'risk': 'medium', 'description': '中老年驾驶员中等风险'},
                        {'min': 76, 'max': 150, 'score': 50, 'risk': 'high', 'description': '高龄驾驶员较高风险'}
                    ]
                },
                'gender': {
                    'weight': 0.05,
                    'tiers': {
                        'male': {'score': 70, 'risk': 'medium', 'description': '男性驾驶员'},
                        'female': {'score': 80, 'risk': 'low', 'description': '女性驾驶员'},
                        'other': {'score': 75, 'risk': 'medium', 'description': '其他性别'}
                    }
                },
                'marital_status': {
                    'weight': 0.05,
                    'tiers': {
                        'single': {'score': 65, 'risk': 'medium', 'description': '未婚人士'},
                        'married': {'score': 80, 'risk': 'low', 'description': '已婚人士'},
                        'divorced': {'score': 70, 'risk': 'medium', 'description': '离异人士'},
                        'widowed': {'score': 75, 'risk': 'medium', 'description': '丧偶人士'}
                    }
                }
            },
            'driving': {
                'annual_mileage': {
                    'weight': 0.15,
                    'tiers': [
                        {'min': 0, 'max': 5000, 'score': 90, 'risk': 'low', 'description': '年里程≤5000公里'},
                        {'min': 5001, 'max': 10000, 'score': 80, 'risk': 'low', 'description': '年里程5001-10000公里'},
                        {'min': 10001, 'max': 20000, 'score': 70, 'risk': 'medium', 'description': '年里程10001-20000公里'},
                        {'min': 20001, 'max': 30000, 'score': 55, 'risk': 'high', 'description': '年里程20001-30000公里'},
                        {'min': 30001, 'max': float('inf'), 'score': 40, 'risk': 'high', 'description': '年里程>30000公里'}
                    ]
                },
                'driving_experience': {
                    'weight': 0.10,
                    'tiers': [
                        {'min': 0, 'max': 1, 'score': 40, 'risk': 'high', 'description': '新手司机(≤1年)'},
                        {'min': 2, 'max': 3, 'score': 55, 'risk': 'high', 'description': '初级司机(2-3年)'},
                        {'min': 4, 'max': 5, 'score': 70, 'risk': 'medium', 'description': '中级司机(4-5年)'},
                        {'min': 6, 'max': 10, 'score': 85, 'risk': 'low', 'description': '熟练司机(6-10年)'},
                        {'min': 11, 'max': float('inf'), 'score': 95, 'risk': 'low', 'description': '资深司机(>10年)'}
                    ]
                },
                'accident_history': {
                    'weight': 0.15,
                    'tiers': [
                        {'min': 0, 'max': 0, 'score': 90, 'risk': 'low', 'description': '无事故记录'},
                        {'min': 1, 'max': 1, 'score': 70, 'risk': 'medium', 'description': '1次事故记录'},
                        {'min': 2, 'max': 3, 'score': 50, 'risk': 'high', 'description': '2-3次事故记录'},
                        {'min': 4, 'max': float('inf'), 'score': 30, 'risk': 'very_high', 'description': '≥4次事故记录'}
                    ]
                }
            },
            'behavioral': {
                'hard_acceleration': {
                    'weight': 0.08,
                    'tiers': [
                        {'min': 0, 'max': 3, 'score': 90, 'risk': 'low', 'description': '几乎无急加速'},
                        {'min': 4, 'max': 10, 'score': 70, 'risk': 'medium', 'description': '少量急加速'},
                        {'min': 11, 'max': 20, 'score': 50, 'risk': 'high', 'description': '较多急加速'},
                        {'min': 21, 'max': float('inf'), 'score': 30, 'risk': 'very_high', 'description': '频繁急加速'}
                    ]
                },
                'hard_braking': {
                    'weight': 0.08,
                    'tiers': [
                        {'min': 0, 'max': 3, 'score': 90, 'risk': 'low', 'description': '几乎无急刹车'},
                        {'min': 4, 'max': 10, 'score': 70, 'risk': 'medium', 'description': '少量急刹车'},
                        {'min': 11, 'max': 20, 'score': 50, 'risk': 'high', 'description': '较多急刹车'},
                        {'min': 21, 'max': float('inf'), 'score': 30, 'risk': 'very_high', 'description': '频繁急刹车'}
                    ]
                },
                'speeding_ratio': {
                    'weight': 0.09,
                    'tiers': [
                        {'min': 0.0, 'max': 0.02, 'score': 90, 'risk': 'low', 'description': '几乎不超速'},
                        {'min': 0.021, 'max': 0.08, 'score': 70, 'risk': 'medium', 'description': '偶尔超速'},
                        {'min': 0.081, 'max': 0.15, 'score': 50, 'risk': 'high', 'description': '经常超速'},
                        {'min': 0.151, 'max': 1.0, 'score': 30, 'risk': 'very_high', 'description': '频繁超速'}
                    ]
                }
            },
            'health': {
                'bmi': {
                    'weight': 0.05,
                    'tiers': [
                        {'min': 18.5, 'max': 24.9, 'score': 90, 'risk': 'low', 'description': 'BMI正常范围'},
                        {'min': 17.0, 'max': 27.9, 'score': 70, 'risk': 'medium', 'description': 'BMI偏轻/偏重'},
                        {'min': 0, 'max': 16.9, 'score': 50, 'risk': 'high', 'description': 'BMI过轻'},
                        {'min': 28.0, 'max': float('inf'), 'score': 40, 'risk': 'high', 'description': 'BMI肥胖'}
                    ]
                },
                'smoking': {
                    'weight': 0.05,
                    'tiers': {
                        True: {'score': 50, 'risk': 'high', 'description': '吸烟人士'},
                        False: {'score': 85, 'risk': 'low', 'description': '不吸烟人士'}
                    ]
                }
            }
        }

    def _init_score_ranges(self):
        self.score_ranges = {
            'very_low': {'min': 85, 'max': 100, 'adjustment': 0.80, 'description': '风险极低 - 享受20%优惠'},
            'low': {'min': 70, 'max': 84, 'adjustment': 0.90, 'description': '风险低 - 享受10%优惠'},
            'medium': {'min': 55, 'max': 69, 'adjustment': 1.00, 'description': '风险中等 - 基准费率'},
            'high': {'min': 40, 'max': 54, 'adjustment': 1.20, 'description': '风险高 - 上浮20%'},
            'very_high': {'min': 0, 'max': 39, 'adjustment': 1.50, 'description': '风险极高 - 上浮50%'}
        }

    def _round_decimal(self, value: Decimal) -> Decimal:
        return value.quantize(self.precision, rounding=ROUND_HALF_UP)

    def _get_tiered_score(self, value: float, factor_config: Dict[str, Any]) -> Dict[str, Any]:
        for tier in factor_config['tiers']:
            if tier['min'] <= value <= tier['max']:
                return {
                    'score': tier['score'],
                    'weight': factor_config['weight'],
                    'weighted_score': tier['score'] * factor_config['weight'],
                    'risk_level': tier['risk'],
                    'description': tier['description'],
                    'factor_value': value
                }
        return {
            'score': 50,
            'weight': factor_config['weight'],
            'weighted_score': 50 * factor_config['weight'],
            'risk_level': 'medium',
            'description': '无法匹配风险等级，使用默认值',
            'factor_value': value
        }

    def _get_categorical_score(self, category: str, factor_config: Dict[str, Any]) -> Dict[str, Any]:
        tier = factor_config['tiers'].get(category, factor_config['tiers'].get('other', factor_config['tiers'].get(False, factor_config['tiers'].get('standard'))))
        if tier is None:
            tier = {'score': 60, 'risk': 'medium', 'description': '默认风险等级'}
        return {
            'score': tier['score'],
            'weight': factor_config['weight'],
            'weighted_score': tier['score'] * factor_config['weight'],
            'risk_level': tier['risk'],
            'description': tier['description'],
            'factor_value': category
        }

    def calculate_risk_score(
        self,
        driving_data: Optional[DrivingBehaviorData] = None,
        health_data: Optional[HealthScoreData] = None,
        demographic_data: Optional[Dict[str, Any]] = None,
        claims_history: Optional[Dict[str, Any]] = None
    ) -> RiskScoreCardResult:
        factor_results: List[RiskScoreCardFactor] = []
        total_weighted_score = 0.0
        total_weight = 0.0

        demographic_data = demographic_data or {}
        claims_history = claims_history or {}

        age = demographic_data.get('age', 35)
        result = self._get_tiered_score(age, self.risk_factors['demographic']['age'])
        factor_results.append(RiskScoreCardFactor(
            factor_name='年龄',
            weight=result['weight'],
            score=result['score'],
            weighted_score=result['weighted_score'],
            factor_value=result['factor_value'],
            risk_level=result['risk_level'],
            description=result['description']
        ))
        total_weighted_score += result['weighted_score']
        total_weight += result['weight']

        gender = demographic_data.get('gender', 'other')
        result = self._get_categorical_score(gender, self.risk_factors['demographic']['gender'])
        factor_results.append(RiskScoreCardFactor(
            factor_name='性别',
            weight=result['weight'],
            score=result['score'],
            weighted_score=result['weighted_score'],
            factor_value=result['factor_value'],
            risk_level=result['risk_level'],
            description=result['description']
        ))
        total_weighted_score += result['weighted_score']
        total_weight += result['weight']

        if driving_data:
            mileage = driving_data.annual_mileage
            result = self._get_tiered_score(mileage, self.risk_factors['driving']['annual_mileage'])
            factor_results.append(RiskScoreCardFactor(
                factor_name='年行驶里程',
                weight=result['weight'],
                score=result['score'],
                weighted_score=result['weighted_score'],
                factor_value=result['factor_value'],
                risk_level=result['risk_level'],
                description=result['description']
            ))
            total_weighted_score += result['weighted_score']
            total_weight += result['weight']

            driving_years = driving_data.driving_years or 5
            result = self._get_tiered_score(driving_years, self.risk_factors['driving']['driving_experience'])
            factor_results.append(RiskScoreCardFactor(
                factor_name='驾龄',
                weight=result['weight'],
                score=result['score'],
                weighted_score=result['weighted_score'],
                factor_value=result['factor_value'],
                risk_level=result['risk_level'],
                description=result['description']
            ))
            total_weighted_score += result['weighted_score']
            total_weight += result['weight']

            hard_accel = driving_data.hard_acceleration_count
            result = self._get_tiered_score(hard_accel, self.risk_factors['behavioral']['hard_acceleration'])
            factor_results.append(RiskScoreCardFactor(
                factor_name='急加速次数',
                weight=result['weight'],
                score=result['score'],
                weighted_score=result['weighted_score'],
                factor_value=result['factor_value'],
                risk_level=result['risk_level'],
                description=result['description']
            ))
            total_weighted_score += result['weighted_score']
            total_weight += result['weight']

            hard_brake = driving_data.hard_braking_count
            result = self._get_tiered_score(hard_brake, self.risk_factors['behavioral']['hard_braking'])
            factor_results.append(RiskScoreCardFactor(
                factor_name='急刹车次数',
                weight=result['weight'],
                score=result['score'],
                weighted_score=result['weighted_score'],
                factor_value=result['factor_value'],
                risk_level=result['risk_level'],
                description=result['description']
            ))
            total_weighted_score += result['weighted_score']
            total_weight += result['weight']

            speeding_ratio = driving_data.speeding_ratio
            result = self._get_tiered_score(speeding_ratio, self.risk_factors['behavioral']['speeding_ratio'])
            factor_results.append(RiskScoreCardFactor(
                factor_name='超速比例',
                weight=result['weight'],
                score=result['score'],
                weighted_score=result['weighted_score'],
                factor_value=result['factor_value'],
                risk_level=result['risk_level'],
                description=result['description']
            ))
            total_weighted_score += result['weighted_score']
            total_weight += result['weight']

        accident_count = claims_history.get('accident_count', 0)
        result = self._get_tiered_score(accident_count, self.risk_factors['driving']['accident_history'])
        factor_results.append(RiskScoreCardFactor(
            factor_name='事故历史',
            weight=result['weight'],
            score=result['score'],
            weighted_score=result['weighted_score'],
            factor_value=result['factor_value'],
            risk_level=result['risk_level'],
            description=result['description']
        ))
        total_weighted_score += result['weighted_score']
        total_weight += result['weight']

        if health_data:
            bmi = health_data.bmi or 22.0
            result = self._get_tiered_score(bmi, self.risk_factors['health']['bmi'])
            factor_results.append(RiskScoreCardFactor(
                factor_name='BMI指数',
                weight=result['weight'],
                score=result['score'],
                weighted_score=result['weighted_score'],
                factor_value=result['factor_value'],
                risk_level=result['risk_level'],
                description=result['description']
            ))
            total_weighted_score += result['weighted_score']
            total_weight += result['weight']

            result = self._get_categorical_score(health_data.smoking_status, self.risk_factors['health']['smoking'])
            factor_results.append(RiskScoreCardFactor(
                factor_name='吸烟状态',
                weight=result['weight'],
                score=result['score'],
                weighted_score=result['weighted_score'],
                factor_value=result['factor_value'],
                risk_level=result['risk_level'],
                description=result['description']
            ))
            total_weighted_score += result['weighted_score']
            total_weight += result['weight']

        if total_weight > 0:
            overall_score = total_weighted_score / total_weight * 100
        else:
            overall_score = 65.0

        risk_level = 'medium'
        adjustment_multiplier = Decimal('1.00')
        for level, config in self.score_ranges.items():
            if config['min'] <= overall_score <= config['max']:
                risk_level = level
                adjustment_multiplier = Decimal(str(config['adjustment']))
                break

        recommendations = self._generate_recommendations(risk_level, factor_results)

        return RiskScoreCardResult(
            overall_risk_score=round(overall_score, 2),
            risk_level=risk_level,
            risk_score_range={k: v['adjustment'] for k, v in self.score_ranges.items()},
            factors=factor_results,
            risk_adjustment_multiplier=self._round_decimal(adjustment_multiplier),
            recommendation=recommendations
        )

    def _generate_recommendations(self, risk_level: str, factors: List[RiskScoreCardFactor]) -> str:
        recommendations = []

        high_risk_factors = [f for f in factors if f.risk_level in ['high', 'very_high']]
        if high_risk_factors:
            high_risk_names = ', '.join([f.factor_name for f in high_risk_factors])
            recommendations.append(f"需要重点关注的风险因素：{high_risk_names}")

        medium_risk_factors = [f for f in factors if f.risk_level == 'medium']
        if medium_risk_factors:
            medium_risk_names = ', '.join([f.factor_name for f in medium_risk_factors])
            recommendations.append(f"建议改进的风险因素：{medium_risk_names}")

        if risk_level == 'very_low':
            recommendations.append("风险极低，建议给予最大优惠")
        elif risk_level == 'low':
            recommendations.append("风险较低，可给予保费优惠")
        elif risk_level == 'medium':
            recommendations.append("风险中等，适用基准费率")
        elif risk_level == 'high':
            recommendations.append("风险较高，建议上浮保费并增加风险管控")
        else:
            recommendations.append("风险极高，建议审慎承保或大幅上浮费率")

        return '; '.join(recommendations)

    def get_scorecard_config(self) -> Dict[str, Any]:
        return {
            'risk_factors': self.risk_factors,
            'score_ranges': self.score_ranges,
            'description': '风险评分卡配置，包含人口统计学、驾驶习惯、行为特征、健康状况等维度'
        }


risk_scorecard_engine = RiskScoreCardEngine()
