from pydantic import BaseModel, Field, field_validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum
from decimal import Decimal


class FactorType(str, Enum):
    BASE_RATE = "base_rate"
    RISK_ADJUSTMENT = "risk_adjustment"
    DISCOUNT = "discount"
    EXPENSE_LOADING = "expense_loading"
    PROFIT_LOADING = "profit_loading"


class PricingFactor(BaseModel):
    id: Optional[str] = None
    name: str = Field(..., description="因子名称")
    factor_type: FactorType = Field(..., description="因子类型")
    value: Decimal = Field(..., description="因子值")
    description: Optional[str] = Field(None, description="因子描述")
    effective_date: Optional[datetime] = Field(None, description="生效日期")
    expiry_date: Optional[datetime] = Field(None, description="失效日期")
    is_active: bool = Field(True, description="是否激活")
    metadata: Optional[Dict[str, Any]] = Field(None, description="元数据")
    priority: int = Field(1, description="计算优先级")

    class Config:
        json_encoders = {
            Decimal: lambda v: str(v)
        }


class FactorCreate(PricingFactor):
    pass


class FactorUpdate(BaseModel):
    name: Optional[str] = None
    factor_type: Optional[FactorType] = None
    value: Optional[Decimal] = None
    description: Optional[str] = None
    effective_date: Optional[datetime] = None
    expiry_date: Optional[datetime] = None
    is_active: Optional[bool] = None
    metadata: Optional[Dict[str, Any]] = None
    priority: Optional[int] = None

    class Config:
        json_encoders = {
            Decimal: lambda v: str(v)
        }


class ReinsuranceType(str, Enum):
    QUOTA_SHARE = "quota_share"
    SURPLUS = "surplus"
    EXCESS_OF_LOSS = "excess_of_loss"


class ReinsuranceContract(BaseModel):
    id: Optional[str] = None
    name: str = Field(..., description="再保合同名称")
    reinsurance_type: ReinsuranceType = Field(..., description="再保类型")
    cession_rate: Optional[Decimal] = Field(None, description="成数分保比例")
    retention_rate: Optional[Decimal] = Field(None, description="自留比例")
    retention: Optional[Decimal] = Field(None, description="自留额")
    limit: Optional[Decimal] = Field(None, description="限额")
    priority_amount: Optional[Decimal] = Field(None, description="优先赔付额")
    attachment_point: Optional[Decimal] = Field(None, description="起赔点")
    exhaustion_point: Optional[Decimal] = Field(None, description="耗尽点")
    max_sum_insured_cap: Optional[Decimal] = Field(None, description="保额上限截断")
    min_premium: Optional[Decimal] = Field(None, description="最低保费")
    max_premium: Optional[Decimal] = Field(None, description="最高保费")
    is_active: bool = Field(True, description="是否激活")
    priority: int = Field(1, description="合同优先级")
    applicable_products: Optional[List[str]] = Field(default_factory=list, description="适用产品类型")

    class Config:
        json_encoders = {
            Decimal: lambda v: str(v)
        }


class PolicyInfo(BaseModel):
    policy_id: str = Field(..., description="保单号")
    product_type: str = Field(..., description="产品类型")
    insured_amount: Decimal = Field(..., description="保额")
    coverage_period: int = Field(..., description="保障期限（月）")
    risk_profile: Dict[str, Any] = Field(..., description="风险画像")
    deductions: Optional[List[Decimal]] = Field(default_factory=list, description="免赔额")

    class Config:
        json_encoders = {
            Decimal: lambda v: str(v)
        }


class PremiumCalculationRequest(BaseModel):
    policy_info: PolicyInfo
    apply_factors: Optional[List[str]] = Field(None, description="应用的因子ID列表")
    reinsurance_contract_id: Optional[str] = Field(None, description="再保合同ID")


class PremiumBreakdown(BaseModel):
    base_premium: Decimal
    risk_adjustment: Decimal
    total_risk_premium: Decimal
    discounts: Decimal
    total_discounted_premium: Decimal
    expense_loading: Decimal
    profit_loading: Decimal
    final_premium: Decimal
    min_premium_applied: bool = Field(False, description="是否触发最低保费")

    class Config:
        json_encoders = {
            Decimal: lambda v: str(v)
        }


class ReinsuranceAllocation(BaseModel):
    gross_premium: Decimal
    net_premium: Decimal
    ceded_premium: Decimal
    retention_amount: Decimal
    cession_rate: Decimal
    reinsurance_type: str
    sum_insured_capped: bool = Field(False, description="保额是否被截断")
    capped_sum_insured: Optional[Decimal] = Field(None, description="截断后的保额")
    details: Dict[str, Any]

    class Config:
        json_encoders = {
            Decimal: lambda v: str(v)
        }


class PremiumCalculationResponse(BaseModel):
    policy_id: str
    original_sum_insured: Decimal
    applied_sum_insured: Decimal
    sum_insured_capped: bool
    premium_breakdown: PremiumBreakdown
    reinsurance_allocation: Optional[ReinsuranceAllocation] = None
    applied_factors: List[str]
    calculation_date: datetime
    calculation_version: str = "2.0.0"

    class Config:
        json_encoders = {
            Decimal: lambda v: str(v)
        }


class FactorConfigResponse(BaseModel):
    version: str
    last_updated: str
    factor_count: int
    factors: List[PricingFactor]
    risk_weights: Dict[str, float]
    calculation_rules: Dict[str, Any]


class ReinsuranceConfigResponse(BaseModel):
    version: str
    last_updated: str
    contract_count: int
    contracts: List[ReinsuranceContract]
    global_limits: Dict[str, Any]
    allocation_rules: Dict[str, Any]


class DrivingBehaviorData(BaseModel):
    annual_mileage: float = Field(..., description="年行驶里程（公里）")
    hard_acceleration_count: int = Field(0, description="急加速次数")
    hard_braking_count: int = Field(0, description="急刹车次数")
    night_driving_ratio: float = Field(0.0, description="夜间驾驶比例")
    speeding_ratio: float = Field(0.0, description="超速驾驶比例")
    safe_driving_score: Optional[float] = Field(None, description="安全驾驶评分(0-100)")
    driving_years: Optional[int] = Field(None, description="驾龄")


class LoyaltyData(BaseModel):
    policy_tenure_years: int = Field(0, description="保单持有年限")
    consecutive_renewal_count: int = Field(0, description="连续续保次数")
    referral_count: int = Field(0, description="推荐成功次数")
    customer_grade: str = Field("standard", description="客户等级: standard, silver, gold, platinum")


class HealthScoreData(BaseModel):
    bmi: Optional[float] = Field(None, description="身体质量指数")
    smoking_status: bool = Field(False, description="是否吸烟")
    alcohol_consumption: str = Field("low", description="饮酒频率: none, low, medium, high")
    exercise_frequency: int = Field(0, description="每周运动次数")
    health_check_score: Optional[float] = Field(None, description="体检评分")
    chronic_condition_count: int = Field(0, description="慢性病数量")


class UBIPremiumAdjustment(BaseModel):
    mileage_factor: Decimal
    hard_accel_factor: Decimal
    hard_brake_factor: Decimal
    night_driving_factor: Decimal
    speeding_factor: Decimal
    safe_driving_bonus: Decimal
    total_ubi_adjustment: Decimal
    ubi_discount_rate: Decimal
    details: Dict[str, Any]

    class Config:
        json_encoders = {Decimal: lambda v: str(v)}


class DynamicDiscountResult(BaseModel):
    loyalty_discount: Decimal
    referral_discount: Decimal
    health_discount: Decimal
    safe_driving_discount: Decimal
    multi_policy_discount: Decimal
    total_dynamic_discount: Decimal
    max_discount_applied: bool
    discount_breakdown: Dict[str, Any]

    class Config:
        json_encoders = {Decimal: lambda v: str(v)}


class RiskScoreCardFactor(BaseModel):
    factor_name: str
    weight: float
    score: float
    weighted_score: float
    factor_value: Any
    risk_level: str
    description: str


class RiskScoreCardResult(BaseModel):
    overall_risk_score: float
    risk_level: str
    risk_score_range: Dict[str, float]
    factors: List[RiskScoreCardFactor]
    risk_adjustment_multiplier: Decimal
    recommendation: str

    class Config:
        json_encoders = {Decimal: lambda v: str(v)}


class PricingScenario(BaseModel):
    scenario_name: str
    scenario_id: str
    description: str
    apply_ubi: bool
    apply_dynamic_discount: bool
    apply_risk_scorecard: bool
    factor_overrides: Optional[Dict[str, Decimal]] = None


class PricingComparisonItem(BaseModel):
    scenario_name: str
    scenario_id: str
    base_premium: Decimal
    risk_adjustment: Decimal
    ubi_adjustment: Decimal
    dynamic_discounts: Decimal
    final_premium: Decimal
    total_savings: Decimal
    savings_percentage: float

    class Config:
        json_encoders = {Decimal: lambda v: str(v)}


class PricingComparisonResponse(BaseModel):
    policy_id: str
    base_scenario: PricingComparisonItem
    comparison_scenarios: List[PricingComparisonItem]
    best_scenario: str
    max_savings: Decimal
    chart_data: Dict[str, Any]
    recommendations: List[str]
    calculation_date: datetime

    class Config:
        json_encoders = {Decimal: lambda v: str(v)}


class ExtendedPremiumBreakdown(PremiumBreakdown):
    ubi_adjustment: Decimal
    dynamic_discounts: Decimal
    ubi_details: Optional[UBIPremiumAdjustment] = None
    discount_details: Optional[DynamicDiscountResult] = None
    risk_scorecard: Optional[RiskScoreCardResult] = None


class ExtendedPremiumCalculationRequest(PremiumCalculationRequest):
    driving_behavior: Optional[DrivingBehaviorData] = None
    loyalty_data: Optional[LoyaltyData] = None
    health_data: Optional[HealthScoreData] = None
    enable_ubi_pricing: bool = Field(False, description="是否启用UBI定价")
    enable_dynamic_discount: bool = Field(False, description="是否启用动态折扣")
    enable_risk_scorecard: bool = Field(False, description="是否启用风险评分卡")


class ExtendedPremiumCalculationResponse(PremiumCalculationResponse):
    premium_breakdown: ExtendedPremiumBreakdown
    ubi_adjustment: Optional[UBIPremiumAdjustment] = None
    dynamic_discounts: Optional[DynamicDiscountResult] = None
    risk_scorecard: Optional[RiskScoreCardResult] = None
