import pandas as pd
import numpy as np
from typing import Dict, Any, Optional
from decimal import Decimal, ROUND_HALF_UP
from app.models.schemas import DrivingBehaviorData, UBIPremiumAdjustment


class UBIPricingEngine:
    def __init__(self):
        self.precision = Decimal('0.01')
        self._init_mileage_tiers()
        self._init_behavior_factors()

    def _init_mileage_tiers(self):
        self.mileage_tiers = [
            {'max_mileage': 5000, 'factor': 0.85, 'description': '年里程≤5000公里，最低风险'},
            {'max_mileage': 10000, 'factor': 0.90, 'description': '年里程5001-10000公里，低风险'},
            {'max_mileage': 15000, 'factor': 0.95, 'description': '年里程10001-15000公里，中低风险'},
            {'max_mileage': 20000, 'factor': 1.00, 'description': '年里程15001-20000公里，基准风险'},
            {'max_mileage': 30000, 'factor': 1.10, 'description': '年里程20001-30000公里，中高风险'},
            {'max_mileage': float('inf'), 'factor': 1.25, 'description': '年里程>30000公里，高风险'}
        ]

    def _init_behavior_factors(self):
        self.hard_accel_tiers = [
            {'max_count': 5, 'factor': 1.00, 'description': '急加速≤5次/月，安全'},
            {'max_count': 15, 'factor': 1.03, 'description': '急加速6-15次/月，较安全'},
            {'max_count': 30, 'factor': 1.08, 'description': '急加速16-30次/月，一般'},
            {'max_count': float('inf'), 'factor': 1.15, 'description': '急加速>30次/月，危险'}
        ]
        
        self.hard_brake_tiers = [
            {'max_count': 5, 'factor': 1.00, 'description': '急刹车≤5次/月，安全'},
            {'max_count': 15, 'factor': 1.05, 'description': '急刹车6-15次/月，较安全'},
            {'max_count': 30, 'factor': 1.12, 'description': '急刹车16-30次/月，一般'},
            {'max_count': float('inf'), 'factor': 1.20, 'description': '急刹车>30次/月，危险'}
        ]

        self.night_driving_tiers = [
            {'max_ratio': 0.10, 'factor': 1.00, 'description': '夜间驾驶≤10%，安全'},
            {'max_ratio': 0.25, 'factor': 1.03, 'description': '夜间驾驶10%-25%，较安全'},
            {'max_ratio': 0.40, 'factor': 1.08, 'description': '夜间驾驶25%-40%，一般'},
            {'max_ratio': float('inf'), 'factor': 1.15, 'description': '夜间驾驶>40%，危险'}
        ]

        self.speeding_tiers = [
            {'max_ratio': 0.02, 'factor': 1.00, 'description': '超速≤2%，安全'},
            {'max_ratio': 0.08, 'factor': 1.05, 'description': '超速2%-8%，较安全'},
            {'max_ratio': 0.15, 'factor': 1.12, 'description': '超速8%-15%，一般'},
            {'max_ratio': float('inf'), 'factor': 1.25, 'description': '超速>15%，危险'}
        ]

    def _round_decimal(self, value: Decimal) -> Decimal:
        return value.quantize(self.precision, rounding=ROUND_HALF_UP)

    def _get_tier_factor(self, value: float, tiers: list) -> float:
        for tier in tiers:
            if value <= tier['max_count']:
                return tier['factor']
        return tiers[-1]['factor']

    def _get_mileage_tier(self, mileage: float) -> Dict[str, Any]:
        for tier in self.mileage_tiers:
            if mileage <= tier['max_mileage']:
                return tier
        return self.mileage_tiers[-1]

    def calculate_mileage_factor(self, annual_mileage: float) -> Dict[str, Any]:
        tier = self._get_mileage_tier(annual_mileage)
        return {
            'factor': tier['factor'],
            'tier_description': tier['description'],
            'annual_mileage': annual_mileage,
            'tier_max': tier['max_mileage']
        }

    def calculate_hard_accel_factor(self, count: int) -> Dict[str, Any]:
        factor = self._get_tier_factor(count, self.hard_accel_tiers)
        tier = next(t for t in self.hard_accel_tiers if factor == t['factor'])
        return {
            'factor': factor,
            'count': count,
            'description': tier['description']
        }

    def calculate_hard_brake_factor(self, count: int) -> Dict[str, Any]:
        factor = self._get_tier_factor(count, self.hard_brake_tiers)
        tier = next(t for t in self.hard_brake_tiers if factor == t['factor'])
        return {
            'factor': factor,
            'count': count,
            'description': tier['description']
        }

    def calculate_night_driving_factor(self, ratio: float) -> Dict[str, Any]:
        factor = self._get_tier_factor(ratio, self.night_driving_tiers)
        tier = next(t for t in self.night_driving_tiers if factor == t['factor'])
        return {
            'factor': factor,
            'ratio': ratio,
            'percentage': round(ratio * 100, 2),
            'description': tier['description']
        }

    def calculate_speeding_factor(self, ratio: float) -> Dict[str, Any]:
        factor = self._get_tier_factor(ratio, self.speeding_tiers)
        tier = next(t for t in self.speeding_tiers if factor == t['factor'])
        return {
            'factor': factor,
            'ratio': ratio,
            'percentage': round(ratio * 100, 2),
            'description': tier['description']
        }

    def calculate_safe_driving_bonus(self, safe_score: Optional[float], driving_years: Optional[int]) -> Dict[str, Any]:
        bonus_factor = 1.0
        reasons = []

        if safe_score is not None:
            if safe_score >= 90:
                bonus_factor *= 0.92
                reasons.append('安全驾驶评分≥90分，享受8%优惠')
            elif safe_score >= 80:
                bonus_factor *= 0.95
                reasons.append('安全驾驶评分80-89分，享受5%优惠')
            elif safe_score >= 70:
                bonus_factor *= 0.98
                reasons.append('安全驾驶评分70-79分，享受2%优惠')

        if driving_years is not None:
            if driving_years >= 10:
                bonus_factor *= 0.95
                reasons.append('驾龄≥10年，享受5%优惠')
            elif driving_years >= 5:
                bonus_factor *= 0.98
                reasons.append('驾龄5-9年，享受2%优惠')

        return {
            'factor': bonus_factor,
            'safe_score': safe_score,
            'driving_years': driving_years,
            'reasons': reasons
        }

    def calculate_ubi_adjustment(
        self,
        driving_data: DrivingBehaviorData,
        base_premium: Decimal
    ) -> UBIPremiumAdjustment:
        mileage_result = self.calculate_mileage_factor(driving_data.annual_mileage)
        hard_accel_result = self.calculate_hard_accel_factor(driving_data.hard_acceleration_count)
        hard_brake_result = self.calculate_hard_brake_factor(driving_data.hard_braking_count)
        night_result = self.calculate_night_driving_factor(driving_data.night_driving_ratio)
        speeding_result = self.calculate_speeding_factor(driving_data.speeding_ratio)
        safe_bonus_result = self.calculate_safe_driving_bonus(
            driving_data.safe_driving_score,
            driving_data.driving_years
        )

        mileage_factor = Decimal(str(mileage_result['factor']))
        hard_accel_factor = Decimal(str(hard_accel_result['factor']))
        hard_brake_factor = Decimal(str(hard_brake_result['factor']))
        night_driving_factor = Decimal(str(night_result['factor']))
        speeding_factor = Decimal(str(speeding_result['factor']))
        safe_bonus_factor = Decimal(str(safe_bonus_result['factor']))

        combined_factor = (
            mileage_factor *
            hard_accel_factor *
            hard_brake_factor *
            night_driving_factor *
            speeding_factor *
            safe_bonus_factor
        )

        adjustment_amount = base_premium * (combined_factor - Decimal('1'))
        adjustment_amount = self._round_decimal(adjustment_amount)

        ubi_discount_rate = max(Decimal('0'), Decimal('1') - combined_factor)
        ubi_discount_rate = self._round_decimal(ubi_discount_rate)

        details = {
            'mileage_tier': mileage_result,
            'hard_acceleration': hard_accel_result,
            'hard_braking': hard_brake_result,
            'night_driving': night_result,
            'speeding': speeding_result,
            'safe_driving_bonus': safe_bonus_result,
            'combined_factor': float(combined_factor),
            'adjustment_direction': 'discount' if combined_factor < 1 else 'surcharge'
        }

        return UBIPremiumAdjustment(
            mileage_factor=self._round_decimal(mileage_factor),
            hard_accel_factor=self._round_decimal(hard_accel_factor),
            hard_brake_factor=self._round_decimal(hard_brake_factor),
            night_driving_factor=self._round_decimal(night_driving_factor),
            speeding_factor=self._round_decimal(speeding_factor),
            safe_driving_bonus=self._round_decimal(safe_bonus_factor),
            total_ubi_adjustment=adjustment_amount,
            ubi_discount_rate=ubi_discount_rate,
            details=details
        )

    def batch_calculate_ubi(
        self,
        driving_data_list: list,
        base_premiums: list
    ) -> list:
        results = []
        for driving_data, base_premium in zip(driving_data_list, base_premiums):
            adjustment = self.calculate_ubi_adjustment(driving_data, base_premium)
            results.append(adjustment)
        return results

    def get_ubi_factor_config(self) -> Dict[str, Any]:
        return {
            'mileage_tiers': self.mileage_tiers,
            'hard_acceleration_tiers': self.hard_accel_tiers,
            'hard_braking_tiers': self.hard_brake_tiers,
            'night_driving_tiers': self.night_driving_tiers,
            'speeding_tiers': self.speeding_tiers,
            'description': 'UBI驾驶行为定价因子配置，基于里程、急加速、急刹车、夜间驾驶、超速等维度'
        }


ubi_pricing_engine = UBIPricingEngine()
