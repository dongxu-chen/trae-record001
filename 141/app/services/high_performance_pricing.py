import time
from typing import Dict, Any, Optional, List
from decimal import Decimal
from datetime import datetime
from functools import lru_cache

from app.engine.polars_engine import HighPerformancePricingEngine, BackendType
from app.models.schemas import DrivingBehaviorData, LoyaltyData, HealthScoreData


class CachedFactorProvider:
    def __init__(self):
        self._factors_cache: Dict[str, Any] = {}
        self._last_update: float = 0
    
    def get_base_rate(self, product_type: str) -> float:
        key = f"base_rate:{product_type}"
        if key not in self._factors_cache:
            rates = {
                "车险": 0.005,
                "寿险": 0.003,
                "健康险": 0.004,
                "责任险": 0.006
            }
            self._factors_cache[key] = rates.get(product_type, 0.005)
        return self._factors_cache[key]


cached_factors = CachedFactorProvider()


class OptimizedPricingService:
    _instance: Optional['OptimizedPricingService'] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self.engine = HighPerformancePricingEngine(BackendType.POLARS)
        self.engine.engine.warmup()
        self._model_cache: Dict[str, Any] = {}
    
    def get_engine_info(self) -> Dict[str, Any]:
        return self.engine.backend_info
    
    def calculate_single_premium(
        self,
        policy_id: str,
        product_type: str,
        insured_amount: float,
        coverage_period: int = 12,
        driving_data: Optional[DrivingBehaviorData] = None,
        loyalty_data: Optional[LoyaltyData] = None,
        health_data: Optional[HealthScoreData] = None
    ) -> Dict[str, Any]:
        start_time = time.perf_counter()
        
        policy_data = {
            "policy_id": policy_id,
            "product_type": product_type,
            "insured_amount": insured_amount,
            "coverage_period": coverage_period
        }
        
        if driving_data:
            policy_data.update({
                "annual_mileage": driving_data.annual_mileage,
                "hard_acceleration_count": driving_data.hard_acceleration_count,
                "hard_braking_count": driving_data.hard_braking_count,
                "night_driving_ratio": driving_data.night_driving_ratio,
                "speeding_ratio": driving_data.speeding_ratio,
                "safe_driving_score": driving_data.safe_driving_score or 70.0,
                "driving_years": driving_data.driving_years or 5
            })
        
        if loyalty_data:
            policy_data.update({
                "policy_tenure_years": loyalty_data.policy_tenure_years,
                "consecutive_renewal_count": loyalty_data.consecutive_renewal_count,
                "referral_count": loyalty_data.referral_count,
                "loyalty_grade": 1.0 if loyalty_data.customer_grade == "platinum" else \
                                 0.95 if loyalty_data.customer_grade == "gold" else \
                                 0.9 if loyalty_data.customer_grade == "silver" else 0.85
            })
        
        if health_data:
            policy_data.update({
                "bmi": health_data.bmi or 22.0,
                "smoking_status": 1.5 if health_data.smoking_status else 1.0,
                "exercise_frequency": health_data.exercise_frequency,
                "health_check_score": health_data.health_check_score or 75.0,
                "chronic_condition_count": health_data.chronic_condition_count
            })
        
        self.engine.load_single_policy(policy_data)
        
        base_rate = cached_factors.get_base_rate(product_type)
        
        risk_multipliers = {}
        discount_factors = {}
        
        if driving_data:
            if driving_data.hard_acceleration_count > 10:
                risk_multipliers["hard_acceleration_count"] = 0.1
            if driving_data.hard_braking_count > 10:
                risk_multipliers["hard_braking_count"] = 0.1
        
        result = self.engine.calculate_premium_fast(
            base_rate=base_rate,
            risk_multipliers=risk_multipliers,
            discount_factors=discount_factors
        )
        
        total_time = (time.perf_counter() - start_time) * 1000
        result["total_latency_ms"] = round(total_time, 3)
        
        return result
    
    def batch_calculate_premium(
        self,
        policies: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        start_time = time.perf_counter()
        
        self.engine.load_batch_policies(policies)
        result = self.engine.batch_calculate_premium()
        
        total_time = (time.perf_counter() - start_time) * 1000
        result["total_latency_ms"] = round(total_time, 3)
        
        return result
    
    def load_pricing_model(
        self,
        model_name: str,
        code: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        return self.engine.load_model(code, model_name, metadata)
    
    def run_pricing_model(
        self,
        model_name: str,
        policy_data: Dict[str, Any],
        func_name: str = "calculate_premium"
    ) -> Dict[str, Any]:
        self.engine.load_single_policy(policy_data)
        return self.engine.run_custom_pricing_model(model_name, func_name)
    
    def list_available_models(self) -> List[Dict[str, Any]]:
        return self.engine.list_models()
    
    def save_pricing_model(
        self,
        model_name: str,
        code: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        return self.engine.save_model(model_name, code, metadata)


_pricing_service: Optional[OptimizedPricingService] = None


def get_pricing_service() -> OptimizedPricingService:
    global _pricing_service
    if _pricing_service is None:
        _pricing_service = OptimizedPricingService()
    return _pricing_service
