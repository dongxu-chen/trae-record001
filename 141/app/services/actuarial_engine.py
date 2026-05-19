import pandas as pd
import numpy as np
from typing import List, Dict, Any, Tuple, Optional
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from app.models.schemas import (
    PolicyInfo, PricingFactor, FactorType,
    PremiumBreakdown
)


class ActuarialEngine:
    def __init__(self):
        self.precision = Decimal('0.01')
        self.max_discount_rate = Decimal('0.4')
        self.min_premium = Decimal('100.00')
        self.risk_weights_cache = None

    def set_calculation_rules(self, rules: Dict[str, Any]):
        self.precision = Decimal(f"0.{'0' * rules.get('rounding_precision', 2)}")
        self.max_discount_rate = Decimal(str(rules.get('max_discount_rate', 0.4)))
        self.min_premium = Decimal(str(rules.get('min_premium', '100.00')))

    def set_risk_weights(self, weights: Dict[str, float]):
        self.risk_weights_cache = weights

    def _round_decimal(self, value: Decimal) -> Decimal:
        return value.quantize(self.precision, rounding=ROUND_HALF_UP)

    def calculate_base_premium_vectorized(
        self,
        policies_df: pd.DataFrame,
        base_rate_factors: List[PricingFactor]
    ) -> pd.DataFrame:
        factor_data = []
        for factor in base_rate_factors:
            product_type = factor.metadata.get('product_type', '') if factor.metadata else ''
            factor_data.append({
                'product_type': product_type,
                'base_rate': float(factor.value)
            })
        
        factors_df = pd.DataFrame(factor_data)
        
        if not factors_df.empty:
            merged_df = policies_df.merge(
                factors_df,
                on='product_type',
                how='left'
            )
            merged_df['base_rate'] = merged_df['base_rate'].fillna(0.005)
        else:
            policies_df['base_rate'] = 0.005
            merged_df = policies_df
        
        merged_df['coverage_multiplier'] = merged_df['coverage_period'] / 12.0
        
        merged_df['base_premium_float'] = merged_df.eval(
            'insured_amount * base_rate * coverage_multiplier'
        )
        
        merged_df['base_premium'] = merged_df['base_premium_float'].apply(
            lambda x: self._round_decimal(Decimal(str(x)))
        )
        
        return merged_df

    def calculate_risk_score_vectorized(self, risk_profile_df: pd.DataFrame) -> pd.Series:
        weights = self.risk_weights_cache or {
            'age': 0.2,
            'claims_history': 0.3,
            'occupation_risk': 0.2,
            'health_status': 0.2,
            'location_risk': 0.1
        }
        
        for col, weight in weights.items():
            if col in risk_profile_df.columns:
                risk_profile_df[f'{col}_weighted'] = risk_profile_df[col] / 10.0 * weight
            else:
                risk_profile_df[f'{col}_weighted'] = 0.0
        
        weighted_cols = [col for col in risk_profile_df.columns if col.endswith('_weighted')]
        risk_profile_df['risk_score'] = risk_profile_df[weighted_cols].sum(axis=1)
        
        return risk_profile_df['risk_score']

    def apply_risk_adjustment_vectorized(
        self,
        df: pd.DataFrame,
        risk_factors: List[PricingFactor]
    ) -> pd.DataFrame:
        conditions = []
        adjustment_values = []
        
        for factor in risk_factors:
            metadata = factor.metadata or {}
            if 'risk_threshold' in metadata:
                threshold = metadata['risk_threshold']
                if factor.name == '低风险调整因子':
                    conditions.append(df['risk_score'] <= threshold)
                else:
                    conditions.append(df['risk_score'] >= threshold)
            elif 'risk_threshold_min' in metadata and 'risk_threshold_max' in metadata:
                conditions.append(
                    (df['risk_score'] >= metadata['risk_threshold_min']) &
                    (df['risk_score'] < metadata['risk_threshold_max'])
                )
            else:
                conditions.append(pd.Series(False, index=df.index))
            adjustment_values.append(float(factor.value))
        
        default_adjustment = 1.0
        df['adjustment_factor'] = default_adjustment
        
        for condition, adj_value in zip(conditions, adjustment_values):
            df.loc[condition, 'adjustment_factor'] = adj_value
        
        df['risk_adjustment_float'] = df.eval(
            'base_premium_float * (adjustment_factor - 1)'
        )
        df['total_risk_premium_float'] = df.eval(
            'base_premium_float + risk_adjustment_float'
        )
        
        df['risk_adjustment'] = df['risk_adjustment_float'].apply(
            lambda x: self._round_decimal(Decimal(str(x)))
        )
        df['total_risk_premium'] = df['total_risk_premium_float'].apply(
            lambda x: self._round_decimal(Decimal(str(x)))
        )
        
        return df

    def calculate_discounts_vectorized(
        self,
        df: pd.DataFrame,
        discount_factors: List[PricingFactor]
    ) -> pd.DataFrame:
        total_discount_rate = sum(float(factor.value) for factor in discount_factors)
        total_discount_rate = min(total_discount_rate, float(self.max_discount_rate))
        
        df['total_discount_rate'] = total_discount_rate
        
        df['discounts_float'] = df.eval(
            'total_risk_premium_float * total_discount_rate'
        )
        df['total_discounted_premium_float'] = df.eval(
            'total_risk_premium_float - discounts_float'
        )
        
        df['discounts'] = df['discounts_float'].apply(
            lambda x: self._round_decimal(Decimal(str(x)))
        )
        df['total_discounted_premium'] = df['total_discounted_premium_float'].apply(
            lambda x: self._round_decimal(Decimal(str(x)))
        )
        
        return df

    def calculate_loadings_vectorized(
        self,
        df: pd.DataFrame,
        expense_factors: List[PricingFactor],
        profit_factors: List[PricingFactor]
    ) -> pd.DataFrame:
        expense_rate = sum(float(factor.value) for factor in expense_factors)
        profit_rate = sum(float(factor.value) for factor in profit_factors)
        
        df['expense_rate'] = expense_rate
        df['profit_rate'] = profit_rate
        
        df['expense_loading_float'] = df.eval(
            'total_discounted_premium_float * expense_rate'
        )
        df['profit_loading_float'] = df.eval(
            'total_discounted_premium_float * profit_rate'
        )
        df['final_premium_float'] = df.eval(
            'total_discounted_premium_float + expense_loading_float + profit_loading_float'
        )
        
        df['expense_loading'] = df['expense_loading_float'].apply(
            lambda x: self._round_decimal(Decimal(str(x)))
        )
        df['profit_loading'] = df['profit_loading_float'].apply(
            lambda x: self._round_decimal(Decimal(str(x)))
        )
        df['final_premium'] = df['final_premium_float'].apply(
            lambda x: self._round_decimal(Decimal(str(x)))
        )
        
        df['min_premium_applied'] = False
        min_prem_float = float(self.min_premium)
        below_min_mask = df['final_premium_float'] < min_prem_float
        df.loc[below_min_mask, 'final_premium'] = self.min_premium
        df.loc[below_min_mask, 'min_premium_applied'] = True
        
        return df

    def calculate_premium(
        self,
        policy_info: PolicyInfo,
        all_factors: List[PricingFactor]
    ) -> Tuple[PremiumBreakdown, List[str]]:
        data = {
            'policy_id': [policy_info.policy_id],
            'product_type': [policy_info.product_type],
            'insured_amount': [float(policy_info.insured_amount)],
            'coverage_period': [policy_info.coverage_period]
        }
        df = pd.DataFrame(data)
        
        risk_profile = policy_info.risk_profile
        risk_data = {}
        for key in ['age', 'claims_history', 'occupation_risk', 'health_status', 'location_risk']:
            risk_data[key] = [float(risk_profile.get(key, 0))]
        risk_df = pd.DataFrame(risk_data)
        
        self.calculate_risk_score_vectorized(risk_df)
        df['risk_score'] = risk_df['risk_score'].iloc[0]
        
        base_rate_factors = [f for f in all_factors if f.factor_type == FactorType.BASE_RATE]
        risk_factors = [f for f in all_factors if f.factor_type == FactorType.RISK_ADJUSTMENT]
        discount_factors = [f for f in all_factors if f.factor_type == FactorType.DISCOUNT]
        expense_factors = [f for f in all_factors if f.factor_type == FactorType.EXPENSE_LOADING]
        profit_factors = [f for f in all_factors if f.factor_type == FactorType.PROFIT_LOADING]
        
        risk_factors_sorted = sorted(risk_factors, key=lambda x: x.priority)
        
        df = self.calculate_base_premium_vectorized(df, base_rate_factors)
        df = self.apply_risk_adjustment_vectorized(df, risk_factors_sorted)
        df = self.calculate_discounts_vectorized(df, discount_factors)
        df = self.calculate_loadings_vectorized(df, expense_factors, profit_factors)
        
        applied_factor_ids = [f.id for f in all_factors if f.id]
        
        row = df.iloc[0]
        breakdown = PremiumBreakdown(
            base_premium=row['base_premium'],
            risk_adjustment=row['risk_adjustment'],
            total_risk_premium=row['total_risk_premium'],
            discounts=row['discounts'],
            total_discounted_premium=row['total_discounted_premium'],
            expense_loading=row['expense_loading'],
            profit_loading=row['profit_loading'],
            final_premium=row['final_premium'],
            min_premium_applied=row['min_premium_applied']
        )
        
        return breakdown, applied_factor_ids

    def batch_calculate_premium(
        self,
        policies: List[PolicyInfo],
        all_factors: List[PricingFactor]
    ) -> List[Tuple[PremiumBreakdown, List[str]]]:
        if not policies:
            return []
        
        data = []
        risk_data_list = []
        
        for policy in policies:
            data.append({
                'policy_id': policy.policy_id,
                'product_type': policy.product_type,
                'insured_amount': float(policy.insured_amount),
                'coverage_period': policy.coverage_period
            })
            
            risk_profile = policy.risk_profile
            risk_data = {}
            for key in ['age', 'claims_history', 'occupation_risk', 'health_status', 'location_risk']:
                risk_data[key] = float(risk_profile.get(key, 0))
            risk_data_list.append(risk_data)
        
        df = pd.DataFrame(data)
        risk_df = pd.DataFrame(risk_data_list)
        
        self.calculate_risk_score_vectorized(risk_df)
        df['risk_score'] = risk_df['risk_score']
        
        base_rate_factors = [f for f in all_factors if f.factor_type == FactorType.BASE_RATE]
        risk_factors = [f for f in all_factors if f.factor_type == FactorType.RISK_ADJUSTMENT]
        discount_factors = [f for f in all_factors if f.factor_type == FactorType.DISCOUNT]
        expense_factors = [f for f in all_factors if f.factor_type == FactorType.EXPENSE_LOADING]
        profit_factors = [f for f in all_factors if f.factor_type == FactorType.PROFIT_LOADING]
        
        risk_factors_sorted = sorted(risk_factors, key=lambda x: x.priority)
        
        df = self.calculate_base_premium_vectorized(df, base_rate_factors)
        df = self.apply_risk_adjustment_vectorized(df, risk_factors_sorted)
        df = self.calculate_discounts_vectorized(df, discount_factors)
        df = self.calculate_loadings_vectorized(df, expense_factors, profit_factors)
        
        applied_factor_ids = [f.id for f in all_factors if f.id]
        results = []
        
        for _, row in df.iterrows():
            breakdown = PremiumBreakdown(
                base_premium=row['base_premium'],
                risk_adjustment=row['risk_adjustment'],
                total_risk_premium=row['total_risk_premium'],
                discounts=row['discounts'],
                total_discounted_premium=row['total_discounted_premium'],
                expense_loading=row['expense_loading'],
                profit_loading=row['profit_loading'],
                final_premium=row['final_premium'],
                min_premium_applied=row['min_premium_applied']
            )
            results.append((breakdown, applied_factor_ids))
        
        return results


actuarial_engine = ActuarialEngine()
