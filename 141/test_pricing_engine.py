#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.models.schemas import (
    PolicyInfo, PremiumCalculationRequest,
    FactorCreate, FactorType, ReinsuranceType
)
from app.services import factor_manager, actuarial_engine, reinsurance_engine


def test_factor_manager():
    print("=" * 60)
    print("测试1: 定价因子管理模块")
    print("=" * 60)

    factors = factor_manager.get_all_factors()
    print(f"当前因子数量: {len(factors)}")
    for f in factors[:3]:
        print(f"  - {f.name}: {f.value} ({f.factor_type})")

    new_factor = FactorCreate(
        name="测试因子-高风险职业",
        factor_type=FactorType.RISK_ADJUSTMENT,
        value=1.8,
        description="高风险职业调整因子",
        metadata={"occupation": "construction"}
    )
    created = factor_manager.create_factor(new_factor)
    print(f"\n创建新因子成功, ID: {created.id}")

    retrieved = factor_manager.get_factor(created.id)
    print(f"获取因子: {retrieved.name} = {retrieved.value}")

    print("✓ 定价因子管理测试通过\n")


def test_actuarial_engine():
    print("=" * 60)
    print("测试2: 精算模型计算模块")
    print("=" * 60)

    policy_info = PolicyInfo(
        policy_id="TEST001",
        product_type="车险",
        insured_amount=500000,
        coverage_period=12,
        risk_profile={
            "age": 35,
            "claims_history": 2,
            "occupation_risk": 5,
            "health_status": 7,
            "location_risk": 4
        },
        deductions=[]
    )

    print(f"保单信息:")
    print(f"  保单号: {policy_info.policy_id}")
    print(f"  产品类型: {policy_info.product_type}")
    print(f"  保额: {policy_info.insured_amount:,}")
    print(f"  保障期限: {policy_info.coverage_period}个月")

    factors = factor_manager.get_all_factors()
    breakdown, applied_factors = actuarial_engine.calculate_premium(policy_info, factors)

    print(f"\n保费明细:")
    print(f"  基础保费: {breakdown.base_premium:,.2f}")
    print(f"  风险调整: {breakdown.risk_adjustment:,.2f}")
    print(f"  折扣: {breakdown.discounts:,.2f}")
    print(f"  费用附加: {breakdown.expense_loading:,.2f}")
    print(f"  利润附加: {breakdown.profit_loading:,.2f}")
    print(f"  最终保费: {breakdown.final_premium:,.2f}")
    print(f"  应用因子数: {len(applied_factors)}")

    print("✓ 精算模型计算测试通过\n")


def test_reinsurance_engine():
    print("=" * 60)
    print("测试3: 再保分摊计算模块")
    print("=" * 60)

    contracts = reinsurance_engine.get_all_contracts()
    print(f"当前再保合同数量: {len(contracts)}")

    gross_premium = 12500.00
    insured_amount = 5000000

    print(f"\n测试保费: {gross_premium:,.2f}")
    print(f"测试保额: {insured_amount:,}\n")

    for contract in contracts:
        print(f"合同: {contract.name} ({contract.reinsurance_type.value})")
        allocation = reinsurance_engine.calculate_allocation(
            gross_premium=gross_premium,
            contract=contract,
            insured_amount=insured_amount
        )
        print(f"  总保费: {allocation.gross_premium:,.2f}")
        print(f"  分保费: {allocation.ceded_premium:,.2f}")
        print(f"  净保费: {allocation.net_premium:,.2f}")
        print(f"  自留额: {allocation.retention_amount:,.2f}")
        print()

    print("✓ 再保分摊计算测试通过\n")


def test_integration():
    print("=" * 60)
    print("测试4: 完整流程集成测试")
    print("=" * 60)

    policy_info = PolicyInfo(
        policy_id="POL-2024-0001",
        product_type="寿险",
        insured_amount=2000000,
        coverage_period=12,
        risk_profile={
            "age": 45,
            "claims_history": 0,
            "occupation_risk": 3,
            "health_status": 8,
            "location_risk": 2
        },
        deductions=[]
    )

    factors = factor_manager.get_all_factors()
    breakdown, applied_factors = actuarial_engine.calculate_premium(policy_info, factors)

    contracts = reinsurance_engine.get_all_contracts()
    quota_contract = contracts[0]

    allocation = reinsurance_engine.calculate_allocation(
        gross_premium=breakdown.final_premium,
        contract=quota_contract,
        insured_amount=policy_info.insured_amount
    )

    print("完整保单定价结果:")
    print(f"  保单号: {policy_info.policy_id}")
    print(f"  产品类型: {policy_info.product_type}")
    print(f"  最终保费: {breakdown.final_premium:,.2f}")
    print(f"  再保类型: {allocation.reinsurance_type}")
    print(f"  分保费: {allocation.ceded_premium:,.2f}")
    print(f"  净自留保费: {allocation.net_premium:,.2f}")

    print("\n✓ 集成测试通过\n")


def main():
    print("\n")
    print("╔" + "=" * 58 + "╗")
    print("║" + " " * 15 + "参数化保险定价引擎测试" + " " * 19 + "║")
    print("╚" + "=" * 58 + "╝")
    print("\n")

    try:
        test_factor_manager()
        test_actuarial_engine()
        test_reinsurance_engine()
        test_integration()

        print("=" * 60)
        print("所有测试通过! ✓")
        print("=" * 60)
        print("\n启动服务命令: uvicorn app.main:app --reload --host 0.0.0.0 --port 8000")
        print("API文档地址: http://localhost:8000/docs")

    except Exception as e:
        print(f"测试失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
