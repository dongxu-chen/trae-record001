import uuid
import json
from typing import Dict, List, Optional
from datetime import datetime
from pathlib import Path
from decimal import Decimal
from app.models.schemas import PricingFactor, FactorCreate, FactorUpdate, FactorType


class FactorManager:
    def __init__(self, config_path: Optional[str] = None):
        self._factors: Dict[str, PricingFactor] = {}
        self._risk_weights: Dict[str, float] = {}
        self._calculation_rules: Dict[str, any] = {}
        self._config_last_modified: Optional[datetime] = None
        
        if config_path:
            self.load_from_json(config_path)
        else:
            self._init_default_factors()

    def _init_default_factors(self):
        default_factors = [
            FactorCreate(
                id="base_auto",
                name="基础费率-车险",
                factor_type=FactorType.BASE_RATE,
                value=Decimal('0.005'),
                description="机动车辆保险基础费率",
                metadata={'product_type': '车险'},
                priority=1
            ),
            FactorCreate(
                id="base_life",
                name="基础费率-寿险",
                factor_type=FactorType.BASE_RATE,
                value=Decimal('0.002'),
                description="人寿保险基础费率",
                metadata={'product_type': '寿险'},
                priority=1
            ),
            FactorCreate(
                id="base_health",
                name="基础费率-健康险",
                factor_type=FactorType.BASE_RATE,
                value=Decimal('0.0035'),
                description="健康保险基础费率",
                metadata={'product_type': '健康险'},
                priority=1
            ),
            FactorCreate(
                id="risk_high",
                name="高风险调整因子",
                factor_type=FactorType.RISK_ADJUSTMENT,
                value=Decimal('1.5'),
                description="高风险客户保费调整系数",
                metadata={'risk_threshold': 0.7, 'risk_category': 'high'},
                priority=2
            ),
            FactorCreate(
                id="risk_medium",
                name="中风险调整因子",
                factor_type=FactorType.RISK_ADJUSTMENT,
                value=Decimal('1.2'),
                description="中风险客户保费调整系数",
                metadata={'risk_threshold_min': 0.4, 'risk_threshold_max': 0.7, 'risk_category': 'medium'},
                priority=2
            ),
            FactorCreate(
                id="risk_low",
                name="低风险调整因子",
                factor_type=FactorType.RISK_ADJUSTMENT,
                value=Decimal('0.8'),
                description="低风险客户保费调整系数",
                metadata={'risk_threshold': 0.2, 'risk_category': 'low'},
                priority=2
            ),
            FactorCreate(
                id="discount_no_claim",
                name="无赔款优待折扣",
                factor_type=FactorType.DISCOUNT,
                value=Decimal('0.1'),
                description="连续无赔款折扣比例",
                metadata={'min_no_claim_years': 1, 'discount_type': 'percentage'},
                priority=3
            ),
            FactorCreate(
                id="discount_multi_policy",
                name="多保单折扣",
                factor_type=FactorType.DISCOUNT,
                value=Decimal('0.05'),
                description="多保单同时投保折扣",
                metadata={'min_policies': 2, 'discount_type': 'percentage'},
                priority=3
            ),
            FactorCreate(
                id="expense_loading",
                name="费用附加因子",
                factor_type=FactorType.EXPENSE_LOADING,
                value=Decimal('0.2'),
                description="运营费用附加比例",
                metadata={'expense_components': ['commission', 'administration', 'marketing']},
                priority=4
            ),
            FactorCreate(
                id="profit_loading",
                name="利润附加因子",
                factor_type=FactorType.PROFIT_LOADING,
                value=Decimal('0.1'),
                description="预期利润附加比例",
                metadata={'target_profit_margin': '10%'},
                priority=5
            )
        ]
        for factor in default_factors:
            self.create_factor(factor)
        
        self._risk_weights = {
            'age': 0.2,
            'claims_history': 0.3,
            'occupation_risk': 0.2,
            'health_status': 0.2,
            'location_risk': 0.1
        }
        self._calculation_rules = {
            'rounding_precision': 2,
            'max_discount_rate': 0.4,
            'min_premium': '100.00'
        }

    def load_from_json(self, config_path: str) -> bool:
        try:
            path = Path(config_path)
            if not path.exists():
                return False
            
            mod_time = datetime.fromtimestamp(path.stat().st_mtime)
            if self._config_last_modified and mod_time <= self._config_last_modified:
                return False
            
            with open(path, 'r', encoding='utf-8') as f:
                config_data = json.load(f)
            
            self._factors.clear()
            
            for factor_data in config_data.get('factors', []):
                factor_data['value'] = Decimal(str(factor_data['value']))
                if 'effective_date' in factor_data and factor_data['effective_date']:
                    factor_data['effective_date'] = datetime.fromisoformat(factor_data['effective_date'])
                factor = FactorCreate(**factor_data)
                if not factor.id:
                    factor.id = str(uuid.uuid4())
                self._factors[factor.id] = factor
            
            self._risk_weights = config_data.get('risk_weights', self._risk_weights)
            self._calculation_rules = config_data.get('calculation_rules', self._calculation_rules)
            self._config_last_modified = mod_time
            
            return True
        except Exception as e:
            print(f"Error loading factors from JSON: {e}")
            return False

    def reload_if_changed(self, config_path: str) -> bool:
        return self.load_from_json(config_path)

    def save_to_json(self, config_path: str) -> bool:
        try:
            factors_data = []
            for factor in self._factors.values():
                factor_dict = factor.model_dump()
                factor_dict['value'] = str(factor_dict['value'])
                if factor_dict.get('effective_date'):
                    factor_dict['effective_date'] = factor_dict['effective_date'].isoformat()
                if factor_dict.get('expiry_date'):
                    factor_dict['expiry_date'] = factor_dict['expiry_date'].isoformat()
                factors_data.append(factor_dict)
            
            config_data = {
                'version': '1.0.0',
                'last_updated': datetime.now().isoformat(),
                'factors': factors_data,
                'risk_weights': self._risk_weights,
                'calculation_rules': self._calculation_rules
            }
            
            path = Path(config_path)
            path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, ensure_ascii=False, indent=2)
            
            return True
        except Exception as e:
            print(f"Error saving factors to JSON: {e}")
            return False

    def create_factor(self, factor_create: FactorCreate) -> PricingFactor:
        if not factor_create.id:
            factor_id = str(uuid.uuid4())
            factor_create.id = factor_id
        
        factor = PricingFactor(
            **factor_create.model_dump(),
            effective_date=factor_create.effective_date or datetime.now()
        )
        self._factors[factor.id] = factor
        return factor

    def get_factor(self, factor_id: str) -> Optional[PricingFactor]:
        return self._factors.get(factor_id)

    def get_all_factors(self, factor_type: Optional[FactorType] = None, active_only: bool = True) -> List[PricingFactor]:
        factors = list(self._factors.values())
        if factor_type:
            factors = [f for f in factors if f.factor_type == factor_type]
        if active_only:
            factors = [f for f in factors if f.is_active]
        factors = sorted(factors, key=lambda x: x.priority)
        return factors

    def update_factor(self, factor_id: str, factor_update: FactorUpdate) -> Optional[PricingFactor]:
        if factor_id not in self._factors:
            return None
        existing_factor = self._factors[factor_id]
        update_data = factor_update.model_dump(exclude_unset=True)
        
        for key, value in update_data.items():
            if hasattr(existing_factor, key):
                setattr(existing_factor, key, value)
        
        self._factors[factor_id] = existing_factor
        return existing_factor

    def delete_factor(self, factor_id: str) -> bool:
        if factor_id in self._factors:
            del self._factors[factor_id]
            return True
        return False

    def get_factors_by_ids(self, factor_ids: List[str]) -> List[PricingFactor]:
        return [self._factors[fid] for fid in factor_ids if fid in self._factors]

    def get_risk_weights(self) -> Dict[str, float]:
        return self._risk_weights

    def get_calculation_rules(self) -> Dict[str, any]:
        return self._calculation_rules


_default_config_path = Path(__file__).parent.parent.parent / 'config' / 'pricing_factors.json'
factor_manager = FactorManager(str(_default_config_path) if _default_config_path.exists() else None)
