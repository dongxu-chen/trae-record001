from fastapi import APIRouter, HTTPException, Query, Body
from typing import List, Optional, Dict, Any
from datetime import datetime
from decimal import Decimal
from app.models.schemas import (
    PricingFactor, FactorCreate, FactorUpdate, FactorType,
    ReinsuranceContract, ReinsuranceType,
    PremiumCalculationRequest, PremiumCalculationResponse,
    FactorConfigResponse, ReinsuranceConfigResponse,
    DrivingBehaviorData, LoyaltyData, HealthScoreData,
    UBIPremiumAdjustment, DynamicDiscountResult, RiskScoreCardResult,
    ExtendedPremiumCalculationRequest, ExtendedPremiumCalculationResponse,
    PricingScenario, PricingComparisonResponse
)
from app.services import (
    factor_manager, actuarial_engine, reinsurance_engine,
    ubi_pricing_engine, dynamic_discount_engine, risk_scorecard_engine,
    pricing_comparison_engine, get_pricing_service
)
from pathlib import Path


router = APIRouter()

actuarial_engine.set_risk_weights(factor_manager.get_risk_weights())
actuarial_engine.set_calculation_rules(factor_manager.get_calculation_rules())


@router.get("/factors/config", response_model=FactorConfigResponse, tags=["定价因子管理"])
def get_factor_config():
    factors = factor_manager.get_all_factors(active_only=False)
    return FactorConfigResponse(
        version="1.0.0",
        last_updated=datetime.now().isoformat(),
        factor_count=len(factors),
        factors=factors,
        risk_weights=factor_manager.get_risk_weights(),
        calculation_rules=factor_manager.get_calculation_rules()
    )


@router.post("/factors/reload", tags=["定价因子管理"])
def reload_factors_from_config(
    config_path: Optional[str] = Query(None, description="配置文件路径")
):
    default_path = Path(__file__).parent.parent.parent / 'config' / 'pricing_factors.json'
    path = config_path or str(default_path)
    reloaded = factor_manager.reload_if_changed(path)
    if reloaded:
        actuarial_engine.set_risk_weights(factor_manager.get_risk_weights())
        actuarial_engine.set_calculation_rules(factor_manager.get_calculation_rules())
    return {
        "reloaded": reloaded,
        "message": "配置已重新加载" if reloaded else "配置未变化或加载失败",
        "config_path": path
    }


@router.get("/factors/", response_model=List[PricingFactor], tags=["定价因子管理"])
def list_factors(
    factor_type: Optional[FactorType] = None,
    active_only: bool = True
):
    return factor_manager.get_all_factors(factor_type=factor_type, active_only=active_only)


@router.get("/factors/{factor_id}", response_model=PricingFactor, tags=["定价因子管理"])
def get_factor(factor_id: str):
    factor = factor_manager.get_factor(factor_id)
    if not factor:
        raise HTTPException(status_code=404, detail="因子不存在")
    return factor


@router.post("/factors/", response_model=PricingFactor, tags=["定价因子管理"])
def create_factor(factor: FactorCreate):
    return factor_manager.create_factor(factor)


@router.put("/factors/{factor_id}", response_model=PricingFactor, tags=["定价因子管理"])
def update_factor(factor_id: str, factor_update: FactorUpdate):
    updated = factor_manager.update_factor(factor_id, factor_update)
    if not updated:
        raise HTTPException(status_code=404, detail="因子不存在")
    return updated


@router.delete("/factors/{factor_id}", tags=["定价因子管理"])
def delete_factor(factor_id: str):
    success = factor_manager.delete_factor(factor_id)
    if not success:
        raise HTTPException(status_code=404, detail="因子不存在")
    return {"message": "因子删除成功"}


@router.get("/reinsurance/config", response_model=ReinsuranceConfigResponse, tags=["再保合同管理"])
def get_reinsurance_config():
    contracts = reinsurance_engine.get_all_contracts(active_only=False)
    return ReinsuranceConfigResponse(
        version="1.0.0",
        last_updated=datetime.now().isoformat(),
        contract_count=len(contracts),
        contracts=contracts,
        global_limits={k: str(v) if isinstance(v, Decimal) else v for k, v in reinsurance_engine._global_limits.items()},
        allocation_rules={'rounding_precision': 2}
    )


@router.get("/reinsurance/contracts/", response_model=List[ReinsuranceContract], tags=["再保合同管理"])
def list_reinsurance_contracts(active_only: bool = True):
    return reinsurance_engine.get_all_contracts(active_only=active_only)


@router.get("/reinsurance/contracts/{contract_id}", response_model=ReinsuranceContract, tags=["再保合同管理"])
def get_reinsurance_contract(contract_id: str):
    contract = reinsurance_engine.get_contract(contract_id)
    if not contract:
        raise HTTPException(status_code=404, detail="再保合同不存在")
    return contract


@router.post("/reinsurance/contracts/", response_model=ReinsuranceContract, tags=["再保合同管理"])
def create_reinsurance_contract(contract: ReinsuranceContract):
    return reinsurance_engine.add_contract(contract)


@router.post("/premium/calculate/", response_model=PremiumCalculationResponse, tags=["保费计算"])
def calculate_premium(request: PremiumCalculationRequest):
    if request.apply_factors:
        factors = factor_manager.get_factors_by_ids(request.apply_factors)
    else:
        factors = factor_manager.get_all_factors(active_only=True)
    
    policy_info = request.policy_info
    original_sum_insured = policy_info.insured_amount
    
    if request.reinsurance_contract_id:
        contract = reinsurance_engine.get_contract(request.reinsurance_contract_id)
        if contract:
            applied_sum_insured, is_capped = reinsurance_engine.apply_sum_insured_cap(original_sum_insured, contract)
            policy_info.insured_amount = applied_sum_insured
        else:
            applied_sum_insured = original_sum_insured
            is_capped = False
    else:
        applied_sum_insured = original_sum_insured
        is_capped = False
    
    premium_breakdown, applied_factor_ids = actuarial_engine.calculate_premium(policy_info, factors)
    
    reinsurance_allocation = None
    if request.reinsurance_contract_id:
        contract = reinsurance_engine.get_contract(request.reinsurance_contract_id)
        if contract:
            reinsurance_allocation = reinsurance_engine.calculate_allocation(
                gross_premium=premium_breakdown.final_premium,
                contract=contract,
                insured_amount=applied_sum_insured
            )
    
    return PremiumCalculationResponse(
        policy_id=policy_info.policy_id,
        original_sum_insured=original_sum_insured,
        applied_sum_insured=applied_sum_insured,
        sum_insured_capped=is_capped,
        premium_breakdown=premium_breakdown,
        reinsurance_allocation=reinsurance_allocation,
        applied_factors=applied_factor_ids,
        calculation_date=datetime.now(),
        calculation_version="2.0.0"
    )


@router.post("/premium/batch-calculate/", response_model=List[PremiumCalculationResponse], tags=["保费计算"])
def batch_calculate_premium(requests: List[PremiumCalculationRequest]):
    responses = []
    
    policies_data = []
    for request in requests:
        policies_data.append(request.policy_info)
    
    all_factors = factor_manager.get_all_factors(active_only=True)
    results = actuarial_engine.batch_calculate_premium(policies_data, all_factors)
    
    for idx, (premium_breakdown, applied_factor_ids) in enumerate(results):
        request = requests[idx]
        policy_info = request.policy_info
        original_sum_insured = policy_info.insured_amount
        
        reinsurance_allocation = None
        is_capped = False
        applied_sum_insured = original_sum_insured
        
        if request.reinsurance_contract_id:
            contract = reinsurance_engine.get_contract(request.reinsurance_contract_id)
            if contract:
                applied_sum_insured, is_capped = reinsurance_engine.apply_sum_insured_cap(original_sum_insured, contract)
                reinsurance_allocation = reinsurance_engine.calculate_allocation(
                    gross_premium=premium_breakdown.final_premium,
                    contract=contract,
                    insured_amount=applied_sum_insured
                )
        
        responses.append(PremiumCalculationResponse(
            policy_id=policy_info.policy_id,
            original_sum_insured=original_sum_insured,
            applied_sum_insured=applied_sum_insured,
            sum_insured_capped=is_capped,
            premium_breakdown=premium_breakdown,
            reinsurance_allocation=reinsurance_allocation,
            applied_factors=applied_factor_ids,
            calculation_date=datetime.now(),
            calculation_version="2.0.0"
        ))
    
    return responses


@router.post("/ubi/calculate/", response_model=UBIPremiumAdjustment, tags=["UBI驾驶行为定价"])
def calculate_ubi_adjustment(
    driving_data: DrivingBehaviorData,
    base_premium: Decimal = Query(..., description="基础保费金额")
):
    adjustment = ubi_pricing_engine.calculate_ubi_adjustment(driving_data, base_premium)
    return adjustment


@router.get("/ubi/config", tags=["UBI驾驶行为定价"])
def get_ubi_config():
    return ubi_pricing_engine.get_ubi_factor_config()


@router.post("/dynamic-discount/calculate/", response_model=DynamicDiscountResult, tags=["动态折扣引擎"])
def calculate_dynamic_discount(
    base_premium: Decimal = Query(..., description="基础保费金额"),
    loyalty_data: Optional[LoyaltyData] = Body(None, description="忠诚度数据"),
    health_data: Optional[HealthScoreData] = Body(None, description="健康数据"),
    driving_data: Optional[DrivingBehaviorData] = Body(None, description="驾驶行为数据"),
    policy_count: int = Query(1, description="投保保单数量")
):
    discount_result = dynamic_discount_engine.calculate_dynamic_discounts(
        base_premium, loyalty_data, health_data, driving_data, policy_count
    )
    return discount_result


@router.get("/dynamic-discount/config", tags=["动态折扣引擎"])
def get_discount_config():
    return dynamic_discount_engine.get_discount_config()


@router.post("/risk-scorecard/calculate/", response_model=RiskScoreCardResult, tags=["风险评分卡"])
def calculate_risk_scorecard(
    driving_data: Optional[DrivingBehaviorData] = Body(None, description="驾驶行为数据"),
    health_data: Optional[HealthScoreData] = Body(None, description="健康数据"),
    demographic_data: Optional[Dict[str, Any]] = Body(None, description="人口统计学数据"),
    claims_history: Optional[Dict[str, Any]] = Body(None, description="理赔历史数据")
):
    scorecard_result = risk_scorecard_engine.calculate_risk_score(
        driving_data, health_data, demographic_data, claims_history
    )
    return scorecard_result


@router.get("/risk-scorecard/config", tags=["风险评分卡"])
def get_scorecard_config():
    return risk_scorecard_engine.get_scorecard_config()


@router.post("/premium/extended-calculate/", response_model=ExtendedPremiumCalculationResponse, tags=["保费计算"])
def calculate_extended_premium(request: ExtendedPremiumCalculationRequest):
    if request.apply_factors:
        factors = factor_manager.get_factors_by_ids(request.apply_factors)
    else:
        factors = factor_manager.get_all_factors(active_only=True)
    
    policy_info = request.policy_info
    original_sum_insured = policy_info.insured_amount
    
    if request.reinsurance_contract_id:
        contract = reinsurance_engine.get_contract(request.reinsurance_contract_id)
        if contract:
            applied_sum_insured, is_capped = reinsurance_engine.apply_sum_insured_cap(original_sum_insured, contract)
            policy_info.insured_amount = applied_sum_insured
        else:
            applied_sum_insured = original_sum_insured
            is_capped = False
    else:
        applied_sum_insured = original_sum_insured
        is_capped = False
    
    premium_breakdown, applied_factor_ids = actuarial_engine.calculate_premium(policy_info, factors)
    
    ubi_adjustment = None
    dynamic_discounts = None
    risk_scorecard = None
    
    if request.enable_ubi_pricing and request.driving_behavior:
        ubi_adjustment = ubi_pricing_engine.calculate_ubi_adjustment(
            request.driving_behavior, premium_breakdown.base_premium
        )
        premium_breakdown.final_premium += ubi_adjustment.total_ubi_adjustment
    
    if request.enable_dynamic_discount:
        dynamic_discounts = dynamic_discount_engine.calculate_dynamic_discounts(
            premium_breakdown.base_premium,
            request.loyalty_data,
            request.health_data,
            request.driving_behavior
        )
        premium_breakdown.final_premium -= dynamic_discounts.total_dynamic_discount
    
    if request.enable_risk_scorecard:
        risk_scorecard = risk_scorecard_engine.calculate_risk_score(
            request.driving_behavior,
            request.health_data,
            {
                'age': 35,
                'gender': 'standard'
            }
        )
        premium_breakdown.final_premium = (
            premium_breakdown.final_premium * risk_scorecard.risk_adjustment_multiplier
        )
    
    reinsurance_allocation = None
    if request.reinsurance_contract_id:
        contract = reinsurance_engine.get_contract(request.reinsurance_contract_id)
        if contract:
            reinsurance_allocation = reinsurance_engine.calculate_allocation(
                gross_premium=premium_breakdown.final_premium,
                contract=contract,
                insured_amount=applied_sum_insured
            )
    
    from app.models.schemas import ExtendedPremiumBreakdown
    extended_breakdown = ExtendedPremiumBreakdown(
        **premium_breakdown.model_dump(),
        ubi_adjustment=ubi_adjustment.total_ubi_adjustment if ubi_adjustment else Decimal('0'),
        dynamic_discounts=dynamic_discounts.total_dynamic_discount if dynamic_discounts else Decimal('0'),
        ubi_details=ubi_adjustment,
        discount_details=dynamic_discounts,
        risk_scorecard=risk_scorecard
    )
    
    return ExtendedPremiumCalculationResponse(
        policy_id=policy_info.policy_id,
        original_sum_insured=original_sum_insured,
        applied_sum_insured=applied_sum_insured,
        sum_insured_capped=is_capped,
        premium_breakdown=extended_breakdown,
        reinsurance_allocation=reinsurance_allocation,
        applied_factors=applied_factor_ids,
        calculation_date=datetime.now(),
        calculation_version="3.0.0",
        ubi_adjustment=ubi_adjustment,
        dynamic_discounts=dynamic_discounts,
        risk_scorecard=risk_scorecard
    )


@router.post("/pricing/compare/", response_model=PricingComparisonResponse, tags=["定价结果对比分析"])
def compare_pricing_scenarios(
    policy_info: PolicyInfo,
    driving_data: Optional[DrivingBehaviorData] = Body(None, description="驾驶行为数据"),
    loyalty_data: Optional[LoyaltyData] = Body(None, description="忠诚度数据"),
    health_data: Optional[HealthScoreData] = Body(None, description="健康数据"),
    custom_scenarios: Optional[List[PricingScenario]] = Body(None, description="自定义对比场景")
):
    comparison_result = pricing_comparison_engine.compare_scenarios(
        policy_info, custom_scenarios, driving_data, loyalty_data, health_data
    )
    return comparison_result


@router.get("/pricing/scenarios", tags=["定价结果对比分析"])
def get_default_scenarios():
    scenarios = pricing_comparison_engine.get_default_scenarios()
    return {
        "default_scenarios": scenarios,
        "count": len(scenarios)
    }


@router.get("/health", tags=["系统"])
def health_check():
    return {
        "status": "healthy",
        "service": "Insurance Pricing Engine",
        "version": "4.0.0",
        "decimal_support": True,
        "pandas_optimized": True,
        "dynamic_config": True,
        "ubi_pricing": True,
        "dynamic_discount": True,
        "risk_scorecard": True,
        "pricing_comparison": True,
        "polars_engine": True,
        "zero_copy": True,
        "gpu_acceleration": True,
        "hot_model_loading": True
    }


@router.get("/high-performance/info", tags=["高性能定价引擎"])
def get_engine_info():
    service = get_pricing_service()
    return service.get_engine_info()


@router.post("/high-performance/calculate", tags=["高性能定价引擎"])
def calculate_premium_high_performance(
    policy_id: str = Query(..., description="保单ID"),
    product_type: str = Query(..., description="产品类型"),
    insured_amount: float = Query(..., description="保额"),
    coverage_period: int = Query(12, description="保障期限(月)"),
    annual_mileage: Optional[float] = Query(None, description="年行驶里程"),
    hard_acceleration_count: Optional[int] = Query(None, description="急加速次数"),
    hard_braking_count: Optional[int] = Query(None, description="急刹车次数"),
    night_driving_ratio: Optional[float] = Query(None, description="夜间驾驶比例"),
    speeding_ratio: Optional[float] = Query(None, description="超速比例"),
    safe_driving_score: Optional[float] = Query(None, description="安全驾驶评分"),
    driving_years: Optional[int] = Query(None, description="驾龄")
):
    service = get_pricing_service()
    
    driving_data = None
    if annual_mileage is not None:
        driving_data = DrivingBehaviorData(
            annual_mileage=annual_mileage,
            hard_acceleration_count=hard_acceleration_count or 0,
            hard_braking_count=hard_braking_count or 0,
            night_driving_ratio=night_driving_ratio or 0.0,
            speeding_ratio=speeding_ratio or 0.0,
            safe_driving_score=safe_driving_score,
            driving_years=driving_years
        )
    
    result = service.calculate_single_premium(
        policy_id=policy_id,
        product_type=product_type,
        insured_amount=insured_amount,
        coverage_period=coverage_period,
        driving_data=driving_data
    )
    
    return result


@router.post("/high-performance/batch", tags=["高性能定价引擎"])
def batch_calculate_premium_high_performance(
    policies: List[Dict[str, Any]]
):
    service = get_pricing_service()
    return service.batch_calculate_premium(policies)


@router.post("/models/upload", tags=["定价模型热加载"])
def upload_pricing_model(
    model_name: str = Query(..., description="模型名称"),
    code: str = Body(..., description="Python代码"),
    description: Optional[str] = Body(None, description="模型描述")
):
    service = get_pricing_service()
    metadata = {"description": description} if description else None
    result = service.load_pricing_model(model_name, code, metadata)
    return {
        "message": "模型加载成功",
        "model_name": model_name,
        "functions": result.get("functions", []),
        "classes": result.get("classes", [])
    }


@router.get("/models/", tags=["定价模型热加载"])
def list_pricing_models():
    service = get_pricing_service()
    return {
        "models": service.list_available_models()
    }


@router.post("/models/run/{model_name}", tags=["定价模型热加载"])
def run_pricing_model(
    model_name: str,
    policy_data: Dict[str, Any],
    func_name: str = Query("calculate_premium", description="执行的函数名")
):
    service = get_pricing_service()
    return service.run_pricing_model(model_name, policy_data, func_name)


@router.post("/models/save", tags=["定价模型热加载"])
def save_pricing_model(
    model_name: str = Query(..., description="模型名称"),
    code: str = Body(..., description="Python代码"),
    description: Optional[str] = Body(None, description="模型描述")
):
    service = get_pricing_service()
    metadata = {"description": description} if description else None
    file_path = service.save_pricing_model(model_name, code, metadata)
    return {
        "message": "模型保存成功",
        "model_name": model_name,
        "file_path": file_path
    }


@router.post("/performance/benchmark", tags=["性能测试"])
def run_performance_benchmark(
    iterations: int = Query(100, description="迭代次数"),
    policy_count: int = Query(1, description="每批保单数量")
):
    import time
    
    service = get_pricing_service()
    
    test_policies = []
    for i in range(policy_count):
        test_policies.append({
            "policy_id": f"TEST_{i}",
            "product_type": "车险",
            "insured_amount": 1000000.0 + i * 10000,
            "coverage_period": 12,
            "annual_mileage": 8000.0 + i * 100,
            "hard_acceleration_count": 3 + i % 10,
            "hard_braking_count": 2 + i % 8,
            "safe_driving_score": 85.0 + i % 15
        })
    
    start_time = time.perf_counter()
    for _ in range(iterations):
        service.batch_calculate_premium(test_policies)
    elapsed = (time.perf_counter() - start_time) * 1000
    
    per_request = elapsed / iterations
    per_policy = per_request / policy_count
    
    return {
        "iterations": iterations,
        "policy_count_per_batch": policy_count,
        "total_time_ms": round(elapsed, 3),
        "avg_time_per_request_ms": round(per_request, 3),
        "avg_time_per_policy_ms": round(per_policy, 5),
        "target_met": per_request < 10.0,
        "target_ms": 10.0
    }
