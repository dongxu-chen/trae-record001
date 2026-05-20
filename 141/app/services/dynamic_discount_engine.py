from typing import Dict, Any, Optional
from decimal import Decimal, ROUND_HALF_UP
from app.models.schemas import LoyaltyData, HealthScoreData, DrivingBehaviorData, DynamicDiscountResult


class DynamicDiscountEngine:
    def __init__(self):
        self.precision = Decimal('0.01')
        self.max_total_discount_rate = Decimal('0.40')
        self._init_loyalty_tiers()
        self._init_referral_bonuses()
        self._init_health_discount_rules()

    def _init_loyalty_tiers(self):
        self.loyalty_tiers = {
            'standard': {'min_tenure': 0, 'discount_rate': 0.00, 'description': '标准客户'},
            'silver': {'min_tenure': 1, 'discount_rate': 0.03, 'description': '白银会员 - 投保满1年'},
            'gold': {'min_tenure': 3, 'discount_rate': 0.06, 'description': '黄金会员 - 投保满3年'},
            'platinum': {'min_tenure': 5, 'discount_rate': 0.10, 'description': '铂金会员 - 投保满5年'}
        }
        
        self.renewal_bonuses = [
            {'min_renewals': 0, 'bonus': 0.00},
            {'min_renewals': 1, 'bonus': 0.02},
            {'min_renewals': 2, 'bonus': 0.03},
            {'min_renewals': 3, 'bonus': 0.04},
            {'min_renewals': 5, 'bonus': 0.06}
        ]

    def _init_referral_bonuses(self):
        self.referral_tiers = [
            {'min_referrals': 0, 'discount_rate': 0.00},
            {'min_referrals': 1, 'discount_rate': 0.02},
            {'min_referrals': 3, 'discount_rate': 0.04},
            {'min_referrals': 5, 'discount_rate': 0.06},
            {'min_referrals': 10, 'discount_rate': 0.08}
        ]

    def _init_health_discount_rules(self):
        self.bmi_tiers = [
            {'min': 18.5, 'max': 24.9, 'discount': 0.03, 'description': 'BMI正常范围'},
            {'min': 17.0, 'max': 27.9, 'discount': 0.01, 'description': 'BMI偏轻/偏重'},
            {'min': 0, 'max': float('inf'), 'discount': 0.00, 'description': 'BMI异常'}
        ]
        
        self.exercise_tiers = [
            {'min': 4, 'discount': 0.03, 'description': '每周运动≥4次'},
            {'min': 2, 'discount': 0.02, 'description': '每周运动2-3次'},
            {'min': 0, 'discount': 0.00, 'description': '每周运动<2次'}
        ]

        self.smoking_surcharge = 0.05

    def _round_decimal(self, value: Decimal) -> Decimal:
        return value.quantize(self.precision, rounding=ROUND_HALF_UP)

    def calculate_loyalty_discount(self, loyalty_data: LoyaltyData) -> Dict[str, Any]:
        tier_info = self.loyalty_tiers.get(loyalty_data.customer_grade, self.loyalty_tiers['standard'])
        base_discount = tier_info['discount_rate']
        
        renewal_bonus = 0.0
        for tier in reversed(self.renewal_bonuses):
            if loyalty_data.consecutive_renewal_count >= tier['min_renewals']:
                renewal_bonus = tier['bonus']
                break
        
        tenure_bonus = 0.0
        if loyalty_data.policy_tenure_years >= 10:
            tenure_bonus = 0.05
        elif loyalty_data.policy_tenure_years >= 7:
            tenure_bonus = 0.03
        
        total_loyalty_rate = base_discount + renewal_bonus + tenure_bonus
        
        return {
            'discount_rate': total_loyalty_rate,
            'customer_grade': loyalty_data.customer_grade,
            'grade_discount': base_discount,
            'renewal_bonus': renewal_bonus,
            'tenure_bonus': tenure_bonus,
            'policy_tenure': loyalty_data.policy_tenure_years,
            'consecutive_renewals': loyalty_data.consecutive_renewal_count,
            'description': tier_info['description']
        }

    def calculate_referral_discount(self, referral_count: int) -> Dict[str, Any]:
        discount_rate = 0.0
        for tier in reversed(self.referral_tiers):
            if referral_count >= tier['min_referrals']:
                discount_rate = tier['discount_rate']
                break
        
        return {
            'discount_rate': discount_rate,
            'referral_count': referral_count,
            'description': f'成功推荐{referral_count}位客户'
        }

    def calculate_health_discount(self, health_data: HealthScoreData) -> Dict[str, Any]:
        total_rate = 0.0
        breakdown = []
        
        if health_data.bmi is not None:
            for tier in self.bmi_tiers:
                if tier['min'] <= health_data.bmi <= tier['max']:
                    total_rate += tier['discount']
                    breakdown.append({'type': 'bmi', 'value': health_data.bmi, 'discount': tier['discount'], 'description': tier['description']})
                    break
        
        for tier in self.exercise_tiers:
            if health_data.exercise_frequency >= tier['min']:
                total_rate += tier['discount']
                breakdown.append({'type': 'exercise', 'value': health_data.exercise_frequency, 'discount': tier['discount'], 'description': tier['description']})
                break
        
        if health_data.smoking_status:
            total_rate -= self.smoking_surcharge
            breakdown.append({'type': 'smoking', 'value': True, 'discount': -self.smoking_surcharge, 'description': '吸烟附加费'})
        
        if health_data.chronic_condition_count > 0:
            chronic_surcharge = min(health_data.chronic_condition_count * 0.02, 0.06)
            total_rate -= chronic_surcharge
            breakdown.append({'type': 'chronic', 'value': health_data.chronic_condition_count, 'discount': -chronic_surcharge, 'description': f'{health_data.chronic_condition_count}种慢性病'})
        
        if health_data.health_check_score is not None:
            if health_data.health_check_score >= 90:
                total_rate += 0.04
                breakdown.append({'type': 'health_check', 'value': health_data.health_check_score, 'discount': 0.04, 'description': '体检优秀(≥90分)'})
            elif health_data.health_check_score >= 80:
                total_rate += 0.02
                breakdown.append({'type': 'health_check', 'value': health_data.health_check_score, 'discount': 0.02, 'description': '体检良好(80-89分)'})
        
        return {
            'discount_rate': max(0.0, total_rate),
            'breakdown': breakdown,
            'net_health_score': health_data.health_check_score
        }

    def calculate_safe_driving_discount(self, driving_data: Optional[DrivingBehaviorData]) -> Dict[str, Any]:
        if driving_data is None or driving_data.safe_driving_score is None:
            return {'discount_rate': 0.0, 'reason': '无驾驶行为数据'}
        
        score = driving_data.safe_driving_score
        discount_rate = 0.0
        
        if score >= 95:
            discount_rate = 0.08
        elif score >= 90:
            discount_rate = 0.06
        elif score >= 85:
            discount_rate = 0.04
        elif score >= 80:
            discount_rate = 0.02
        elif score >= 75:
            discount_rate = 0.01
        
        return {
            'discount_rate': discount_rate,
            'safe_driving_score': score,
            'description': f'安全驾驶评分{score}分'
        }

    def calculate_multi_policy_discount(self, policy_count: int) -> Dict[str, Any]:
        discount_rate = 0.0
        if policy_count >= 5:
            discount_rate = 0.10
        elif policy_count >= 3:
            discount_rate = 0.05
        elif policy_count >= 2:
            discount_rate = 0.03
        
        return {
            'discount_rate': discount_rate,
            'policy_count': policy_count,
            'description': f'同时投保{policy_count}张保单'
        }

    def calculate_dynamic_discounts(
        self,
        base_premium: Decimal,
        loyalty_data: Optional[LoyaltyData] = None,
        health_data: Optional[HealthScoreData] = None,
        driving_data: Optional[DrivingBehaviorData] = None,
        policy_count: int = 1
    ) -> DynamicDiscountResult:
        loyalty_result = self.calculate_loyalty_discount(loyalty_data or LoyaltyData())
        referral_result = self.calculate_referral_discount(loyalty_data.referral_count if loyalty_data else 0)
        health_result = self.calculate_health_discount(health_data or HealthScoreData())
        driving_result = self.calculate_safe_driving_discount(driving_data)
        multi_policy_result = self.calculate_multi_policy_discount(policy_count)
        
        total_rate = (
            loyalty_result['discount_rate'] +
            referral_result['discount_rate'] +
            health_result['discount_rate'] +
            driving_result['discount_rate'] +
            multi_policy_result['discount_rate']
        )
        
        max_rate = float(self.max_total_discount_rate)
        max_discount_applied = total_rate > max_rate
        if max_discount_applied:
            total_rate = max_rate
        
        total_discount_amount = base_premium * Decimal(str(total_rate))
        total_discount_amount = self._round_decimal(total_discount_amount)
        
        discount_breakdown = {
            'loyalty': loyalty_result,
            'referral': referral_result,
            'health': health_result,
            'safe_driving': driving_result,
            'multi_policy': multi_policy_result
        }
        
        return DynamicDiscountResult(
            loyalty_discount=self._round_decimal(base_premium * Decimal(str(loyalty_result['discount_rate']))),
            referral_discount=self._round_decimal(base_premium * Decimal(str(referral_result['discount_rate']))),
            health_discount=self._round_decimal(base_premium * Decimal(str(health_result['discount_rate']))),
            safe_driving_discount=self._round_decimal(base_premium * Decimal(str(driving_result['discount_rate']))),
            multi_policy_discount=self._round_decimal(base_premium * Decimal(str(multi_policy_result['discount_rate']))),
            total_dynamic_discount=total_discount_amount,
            max_discount_applied=max_discount_applied,
            discount_breakdown=discount_breakdown
        )

    def get_discount_config(self) -> Dict[str, Any]:
        return {
            'loyalty_tiers': self.loyalty_tiers,
            'renewal_bonuses': self.renewal_bonuses,
            'referral_tiers': self.referral_tiers,
            'bmi_tiers': self.bmi_tiers,
            'exercise_tiers': self.exercise_tiers,
            'smoking_surcharge': self.smoking_surcharge,
            'max_total_discount': float(self.max_total_discount_rate),
            'description': '动态折扣引擎配置，包含忠诚度、推荐、健康、安全驾驶等多维度优惠'
        }


dynamic_discount_engine = DynamicDiscountEngine()
