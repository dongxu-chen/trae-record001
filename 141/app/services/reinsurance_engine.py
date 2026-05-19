import pandas as pd
from typing import Dict, List, Optional, Tuple
from decimal import Decimal, ROUND_HALF_UP
from app.models.schemas import (
    ReinsuranceContract, ReinsuranceType,
    ReinsuranceAllocation
)


class ReinsuranceEngine:
    def __init__(self):
        self._contracts: Dict[str, ReinsuranceContract] = {}
        self._global_limits = {
            'max_sum_insured': Decimal('100000000'),
            'max_single_risk': Decimal('50000000'),
            'max_cession_rate': Decimal('0.9')
        }
        self.precision = Decimal('0.01')

    def _round_decimal(self, value: Decimal) -> Decimal:
        return value.quantize(self.precision, rounding=ROUND_HALF_UP)

    def set_global_limits(self, limits: Dict[str, Any]):
        for key, value in limits.items():
            if key in self._global_limits:
                if isinstance(value, str):
                    self._global_limits[key] = Decimal(value)
                else:
                    self._global_limits[key] = Decimal(str(value))

    def add_contract(self, contract: ReinsuranceContract) -> ReinsuranceContract:
        if contract.id:
            self._contracts[contract.id] = contract
        return contract

    def get_contract(self, contract_id: str) -> Optional[ReinsuranceContract]:
        return self._contracts.get(contract_id)

    def get_all_contracts(self, active_only: bool = True) -> List[ReinsuranceContract]:
        contracts = list(self._contracts.values())
        if active_only:
            contracts = [c for c in contracts if c.is_active]
        return contracts

    def apply_sum_insured_cap(
        self,
        original_sum_insured: Decimal,
        contract: ReinsuranceContract
    ) -> Tuple[Decimal, bool]:
        max_sum_insured = self._global_limits['max_sum_insured']
        contract_cap = contract.max_sum_insured_cap or max_sum_insured
        cap_value = min(max_sum_insured, contract_cap)
        
        if original_sum_insured > cap_value:
            return cap_value, True
        return original_sum_insured, False

    def calculate_quota_share_allocation_vectorized(
        self,
        df: pd.DataFrame,
        cession_rate: Decimal
    ) -> pd.DataFrame:
        cession_rate_float = float(cession_rate)
        retention_rate_float = 1.0 - cession_rate_float
        
        df['cession_rate'] = cession_rate_float
        df['retention_rate'] = retention_rate_float
        
        df = df.eval(
            """
            ceded_premium_float = gross_premium_float * cession_rate
            net_premium_float = gross_premium_float - ceded_premium_float
            retention_amount_float = gross_premium_float * retention_rate
            """
        )
        
        df['ceded_premium'] = df['ceded_premium_float'].apply(
            lambda x: self._round_decimal(Decimal(str(x)))
        )
        df['net_premium'] = df['net_premium_float'].apply(
            lambda x: self._round_decimal(Decimal(str(x)))
        )
        df['retention_amount'] = df['retention_amount_float'].apply(
            lambda x: self._round_decimal(Decimal(str(x)))
        )
        
        return df

    def calculate_surplus_allocation_vectorized(
        self,
        df: pd.DataFrame,
        retention: Decimal,
        limit: Optional[Decimal] = None
    ) -> pd.DataFrame:
        retention_float = float(retention)
        limit_float = float(limit) if limit else float('inf')
        
        df['retention'] = retention_float
        
        df = df.eval(
            """
            surplus_amount_float = applied_sum_insured - retention
            surplus_amount_clamped_float = max(0, min(surplus_amount_float, @limit_float))
            cession_rate = surplus_amount_clamped_float / applied_sum_insured if applied_sum_insured > 0 else 0
            ceded_premium_float = gross_premium_float * cession_rate
            net_premium_float = gross_premium_float - ceded_premium_float
            """
        )
        
        df.loc[df['applied_sum_insured'] <= 0, 'cession_rate'] = 0
        df.loc[df['applied_sum_insured'] <= retention_float, 'ceded_premium_float'] = 0
        df.loc[df['applied_sum_insured'] <= retention_float, 'net_premium_float'] = df['gross_premium_float']
        
        df['ceded_premium'] = df['ceded_premium_float'].apply(
            lambda x: self._round_decimal(Decimal(str(x)))
        )
        df['net_premium'] = df['net_premium_float'].apply(
            lambda x: self._round_decimal(Decimal(str(x)))
        )
        df['surplus_amount'] = df['surplus_amount_clamped_float'].apply(
            lambda x: self._round_decimal(Decimal(str(x)))
        )
        df['retention_amount'] = Decimal(str(retention_float))
        
        return df

    def calculate_excess_of_loss_allocation_vectorized(
        self,
        df: pd.DataFrame,
        attachment_point: Decimal,
        limit: Decimal
    ) -> pd.DataFrame:
        attachment_float = float(attachment_point)
        limit_float = float(limit)
        exhaustion_float = attachment_float + limit_float
        
        df['attachment_point'] = attachment_float
        df['reinsurance_limit'] = limit_float
        df['exhaustion_point'] = exhaustion_float
        
        df['potential_loss'] = df['applied_sum_insured'] * 0.1
        
        df = df.eval(
            """
            loss_above_attachment = max(0, potential_loss - attachment_point)
            reinsurance_cover = min(loss_above_attachment, reinsurance_limit)
            cover_ratio = reinsurance_cover / potential_loss if potential_loss > 0 else 0
            ceded_premium_float = gross_premium_float * cover_ratio * 0.5
            net_premium_float = gross_premium_float - ceded_premium_float
            """
        )
        
        df['ceded_premium'] = df['ceded_premium_float'].apply(
            lambda x: self._round_decimal(Decimal(str(x)))
        )
        df['net_premium'] = df['net_premium_float'].apply(
            lambda x: self._round_decimal(Decimal(str(x)))
        )
        df['reinsurance_cover'] = df['reinsurance_cover'].apply(
            lambda x: self._round_decimal(Decimal(str(x)))
        )
        df['retention_amount'] = max(attachment_point, Decimal(0))
        
        return df

    def calculate_allocation(
        self,
        gross_premium: Decimal,
        contract: ReinsuranceContract,
        insured_amount: Optional[Decimal] = None,
        potential_loss: Optional[Decimal] = None
    ) -> ReinsuranceAllocation:
        original_sum_insured = insured_amount or Decimal('0')
        applied_sum_insured, is_capped = self.apply_sum_insured_cap(original_sum_insured, contract)
        
        data = {
            'gross_premium_float': [float(gross_premium)],
            'original_sum_insured': [float(original_sum_insured)],
            'applied_sum_insured': [float(applied_sum_insured)]
        }
        df = pd.DataFrame(data)
        
        cession_rate = Decimal('0')
        
        if contract.reinsurance_type == ReinsuranceType.QUOTA_SHARE:
            cession_rate = contract.cession_rate or Decimal('0')
            df = self.calculate_quota_share_allocation_vectorized(df, cession_rate)
            details = {
                'cession_rate': str(cession_rate),
                'retention_rate': str(Decimal('1') - cession_rate),
                'formula': '成数分保 = 总保费 * 分保比例'
            }
        elif contract.reinsurance_type == ReinsuranceType.SURPLUS:
            retention = contract.retention or Decimal('0')
            limit = contract.limit
            df = self.calculate_surplus_allocation_vectorized(df, retention, limit)
            cession_rate = Decimal(str(df['cession_rate'].iloc[0]))
            details = {
                'retention': str(retention),
                'surplus_amount': str(df['surplus_amount'].iloc[0]),
                'limit': str(limit) if limit else None,
                'cession_rate': str(cession_rate),
                'formula': '溢额分保比例 = (保额 - 自留额) / 保额',
                'surplus_treaty_applied': applied_sum_insured > retention
            }
        elif contract.reinsurance_type == ReinsuranceType.EXCESS_OF_LOSS:
            attachment_point = contract.attachment_point or contract.priority_amount or Decimal('0')
            limit = contract.limit or Decimal('0')
            df = self.calculate_excess_of_loss_allocation_vectorized(df, attachment_point, limit)
            cession_rate = Decimal(str(df['cover_ratio'].iloc[0])) * Decimal('0.5')
            details = {
                'attachment_point': str(attachment_point),
                'limit': str(limit),
                'potential_loss': str(df['potential_loss'].iloc[0]),
                'reinsurance_cover': str(df['reinsurance_cover'].iloc[0]),
                'cover_ratio': str(df['cover_ratio'].iloc[0]),
                'formula': '超赔分保保费 = 总保费 * 保障比例 * 0.5',
                'xl_treaty_applied': df['potential_loss'].iloc[0] > attachment_point
            }
        else:
            raise ValueError(f"Unknown reinsurance type: {contract.reinsurance_type}")
        
        row = df.iloc[0]
        
        max_cession = gross_premium * self._global_limits['max_cession_rate']
        if row['ceded_premium'] > max_cession:
            ceded_premium = max_cession
            net_premium = gross_premium - max_cession
            cession_rate = max_cession / gross_premium if gross_premium > 0 else Decimal('0')
        else:
            ceded_premium = row['ceded_premium']
            net_premium = row['net_premium']
        
        return ReinsuranceAllocation(
            gross_premium=self._round_decimal(gross_premium),
            net_premium=self._round_decimal(net_premium),
            ceded_premium=self._round_decimal(ceded_premium),
            retention_amount=row['retention_amount'] if isinstance(row['retention_amount'], Decimal) else self._round_decimal(Decimal(str(row['retention_amount']))),
            cession_rate=self._round_decimal(cession_rate),
            reinsurance_type=contract.reinsurance_type.value,
            sum_insured_capped=is_capped,
            capped_sum_insured=applied_sum_insured if is_capped else None,
            details=details
        )

    def batch_calculate_allocation(
        self,
        gross_premiums: List[Decimal],
        contracts: List[ReinsuranceContract],
        insured_amounts: Optional[List[Decimal]] = None
    ) -> List[ReinsuranceAllocation]:
        results = []
        insured_amounts = insured_amounts or [Decimal('0')] * len(gross_premiums)
        
        for gross_premium, contract, insured_amount in zip(gross_premiums, contracts, insured_amounts):
            allocation = self.calculate_allocation(gross_premium, contract, insured_amount)
            results.append(allocation)
        
        return results


reinsurance_engine = ReinsuranceEngine()
