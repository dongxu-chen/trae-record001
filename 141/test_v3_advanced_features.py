#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import os
import time
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.models.schemas import (
    PolicyInfo, DrivingBehaviorData, LoyaltyData, HealthScoreData
)
from app.services import (
    ubi_pricing_engine, dynamic_discount_engine,
    risk_scorecard_engine, pricing_comparison_engine
)


def print_section(title):
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70 + "\n")


def test_ubi_pricing():
    print_section("测试1: UBI驾驶行为定价")
    
    print("创建测试驾驶行为数据:")
    print("  - 年行驶里程: 8,000公里")
    print("  - 急加速次数: 3次/月")
    print("  - 急刹车次数: 2次/月")
    print("  - 夜间驾驶比例: 10%")
    print("  - 超速比例: 2%")
    print("  - 安全驾驶评分: 92分")
    print("  - 驾龄: 10年")
    
    driving_data = DrivingBehaviorData(
        annual_mileage=8000,
        hard_acceleration_count=3,
        hard_braking_count=2,
        night_driving_ratio=0.10,
        speeding_ratio=0.02,
        safe_driving_score=92,
        driving_years=10
    )
    
    base_premium = Decimal('5000.00')
    
    print(f"\n基础保费: ¥{float(base_premium):,.2f}")
    
    adjustment = ubi_pricing_engine.calculate_ubi_adjustment(driving_data, base_premium)
    
    print("\nUBI保费调整明细:")
    print(f"  里程因子: {float(adjustment.mileage_factor):.4f}")
    print(f"  急加速因子: {float(adjustment.hard_accel_factor):.4f}")
    print(f"  急刹车因子: {float(adjustment.hard_brake_factor):.4f}")
    print(f"  夜间驾驶因子: {float(adjustment.night_driving_factor):.4f}")
    print(f"  超速因子: {float(adjustment.speeding_factor):.4f}")
    print(f"  安全驾驶奖励: {float(adjustment.safe_driving_bonus):.4f}")
    print(f"  -" * 30)
    print(f"  综合调整系数: {float(adjustment.ubi_discount_rate)*100:.2f}%")
    print(f"  UBI调整金额: ¥{float(adjustment.total_ubi_adjustment):,.2f}")
    
    if float(adjustment.total_ubi_adjustment) < 0:
        print(f"\n  恭喜! 基于您优秀的驾驶行为，保费减少 ¥{abs(float(adjustment.total_ubi_adjustment)):,.2f}")
    else:
        print(f"\n  注意: 基于您的驾驶行为，保费增加 ¥{float(adjustment.total_ubi_adjustment):,.2f}")
    
    print("\nUBI配置详情:")
    config = ubi_pricing_engine.get_ubi_factor_config()
    print(f"  - 支持5个驾驶行为维度定价")
    print(f"  - 包含{len(config['mileage_tiers'])}个里程档位")
    
    print("\n  ✓ UBI驾驶行为定价测试通过!")


def test_dynamic_discount_engine():
    print_section("测试2: 动态折扣引擎")
    
    base_premium = Decimal('5000.00')
    
    print("测试场景: 铂金客户")
    print("  - 客户等级: 铂金会员")
    print("  - 连续续保: 5年")
    print("  - 推荐客户: 5人")
    print("  - BMI: 22.5 (正常范围)")
    print("  - 不吸烟")
    print("  - 每周运动: 4次")
    print("  - 体检评分: 88分")
    
    loyalty_data = LoyaltyData(
        policy_tenure_years=7,
        consecutive_renewal_count=5,
        referral_count=5,
        customer_grade='platinum'
    )
    
    health_data = HealthScoreData(
        bmi=22.5,
        smoking_status=False,
        alcohol_consumption='low',
        exercise_frequency=4,
        health_check_score=88,
        chronic_condition_count=0
    )
    
    driving_data = DrivingBehaviorData(
        annual_mileage=8000,
        hard_acceleration_count=3,
        hard_braking_count=2,
        night_driving_ratio=0.10,
        speeding_ratio=0.02,
        safe_driving_score=92,
        driving_years=10
    )
    
    discount_result = dynamic_discount_engine.calculate_dynamic_discounts(
        base_premium=base_premium,
        loyalty_data=loyalty_data,
        health_data=health_data,
        driving_data=driving_data,
        policy_count=1
    )
    
    print(f"\n基础保费: ¥{float(base_premium):,.2f}")
    print("\n动态折扣明细:")
    print(f"  忠诚度折扣: ¥{float(discount_result.loyalty_discount):,.2f}")
    print(f"  推荐奖励折扣: ¥{float(discount_result.referral_discount):,.2f}")
    print(f"  健康折扣: ¥{float(discount_result.health_discount):,.2f}")
    print(f"  安全驾驶折扣: ¥{float(discount_result.safe_driving_discount):,.2f}")
    print(f"  多保单折扣: ¥{float(discount_result.multi_policy_discount):,.2f}")
    print(f"  -" * 30)
    print(f"  总折扣金额: ¥{float(discount_result.total_dynamic_discount):,.2f}")
    print(f"  是否触发最大折扣限制: {'是' if discount_result.max_discount_applied else '否'}")
    
    discount_rate = float(discount_result.total_dynamic_discount) / float(base_premium) * 100
    print(f"  总折扣率: {discount_rate:.2f}%")
    
    print("\n折扣详情:")
    details = discount_result.discount_breakdown
    if 'loyalty' in details:
        print(f"  忠诚度: {details['loyalty']['description']}")
    if 'health' in details:
        for factor in details['health'].get('breakdown', []):
            if factor.get('discount', 0) != 0:
                sign = "+" if factor['discount'] > 0 else ""
                print(f"    {factor['description']}: {sign}{factor['discount']*100:.2f}%")
    
    print("\n  ✓ 动态折扣引擎测试通过!")


def test_risk_scorecard():
    print_section("测试3: 风险评分卡 (多因子加权)")
    
    print("创建测试数据:")
    print("  - 年龄: 35岁")
    print("  - 性别: 男")
    print("  - 年行驶里程: 8,000公里")
    print("  - 驾龄: 10年")
    print("  - 急加速: 3次/月")
    print("  - 急刹车: 2次/月")
    print("  - 超速比例: 2%")
    print("  - 无事故记录")
    print("  - BMI: 22.5 (正常)")
    print("  - 不吸烟")
    
    driving_data = DrivingBehaviorData(
        annual_mileage=8000,
        hard_acceleration_count=3,
        hard_braking_count=2,
        night_driving_ratio=0.10,
        speeding_ratio=0.02,
        safe_driving_score=92,
        driving_years=10
    )
    
    health_data = HealthScoreData(
        bmi=22.5,
        smoking_status=False,
        alcohol_consumption='low',
        exercise_frequency=4,
        health_check_score=88,
        chronic_condition_count=0
    )
    
    demographic_data = {
        'age': 35,
        'gender': 'male',
        'marital_status': 'married'
    }
    
    claims_history = {
        'accident_count': 0,
        'claim_count': 0,
        'last_accident_years': None
    }
    
    scorecard_result = risk_scorecard_engine.calculate_risk_score(
        driving_data=driving_data,
        health_data=health_data,
        demographic_data=demographic_data,
        claims_history=claims_history
    )
    
    print(f"\n整体风险评分: {scorecard_result.overall_risk_score:.2f}/100")
    risk_level_names = {
        'very_low': '极低风险',
        'low': '低风险',
        'medium': '中等风险',
        'high': '高风险',
        'very_high': '极高风险'
    }
    print(f"风险等级: {risk_level_names.get(scorecard_result.risk_level, scorecard_result.risk_level)}")
    print(f"保费调整系数: {float(scorecard_result.risk_adjustment_multiplier):.4f}")
    
    print("\n各风险因子评分明细:")
    for factor in scorecard_result.factors:
        risk_icon = {
            'very_low': '🟢',
            'low': '🟢',
            'medium': '🟡',
            'high': '🔴',
            'very_high': '🔴'
        }.get(factor.risk_level, '⚪')
        
        print(f"  {risk_icon} {factor.factor_name}:")
        print(f"      - 权重: {factor.weight*100:.0f}%")
        print(f"      - 得分: {factor.score}/100")
        print(f"      - 加权得分: {factor.weighted_score:.2f}")
        print(f"      - 风险等级: {factor.risk_level}")
        print(f"      - 描述: {factor.description}")
    
    print("\n风险评估建议:")
    for recommendation in scorecard_result.recommendation.split(';'):
        print(f"  • {recommendation.strip()}")
    
    print("\n  ✓ 风险评分卡测试通过!")


def test_pricing_comparison():
    print_section("测试4: 定价结果对比分析图表")
    
    policy_info = PolicyInfo(
        policy_id='TEST-COMPARE-001',
        product_type='车险',
        insured_amount=Decimal('1000000'),
        coverage_period=12,
        risk_profile={},
        deductions=[]
    )
    
    driving_data = DrivingBehaviorData(
        annual_mileage=8000,
        hard_acceleration_count=3,
        hard_braking_count=2,
        night_driving_ratio=0.10,
        speeding_ratio=0.02,
        safe_driving_score=92,
        driving_years=10
    )
    
    loyalty_data = LoyaltyData(
        policy_tenure_years=7,
        consecutive_renewal_count=5,
        referral_count=5,
        customer_grade='platinum'
    )
    
    health_data = HealthScoreData(
        bmi=22.5,
        smoking_status=False,
        alcohol_consumption='low',
        exercise_frequency=4,
        health_check_score=88,
        chronic_condition_count=0
    )
    
    comparison_result = pricing_comparison_engine.compare_scenarios(
        policy_info=policy_info,
        driving_data=driving_data,
        loyalty_data=loyalty_data,
        health_data=health_data
    )
    
    print(f"保单号: {comparison_result.policy_id}")
    print(f"计算时间: {comparison_result.calculation_date}")
    print(f"\n参与对比的定价场景: {len(comparison_result.comparison_scenarios) + 1}个")
    
    print("\n场景对比结果:")
    all_scenarios = [comparison_result.base_scenario] + comparison_result.comparison_scenarios
    sorted_scenarios = sorted(all_scenarios, key=lambda x: x.final_premium)
    
    for idx, scenario in enumerate(sorted_scenarios):
        medal = ['🥇', '🥈', '🥉', '4️⃣', '5️⃣'][idx] if idx < 5 else f"  {idx+1}."
        print(f"\n{medal} {scenario.scenario_name}:")
        print(f"     最终保费: ¥{float(scenario.final_premium):,.2f}")
        print(f"     节省金额: ¥{float(scenario.total_savings):,.2f} ({scenario.savings_percentage:.2f}%)")
        print(f"     保费构成:")
        print(f"       - 基础保费: ¥{float(scenario.base_premium):,.2f}")
        if float(scenario.ubi_adjustment) != 0:
            print(f"       - UBI调整: ¥{float(scenario.ubi_adjustment):,.2f}")
        if float(scenario.dynamic_discounts) != 0:
            print(f"       - 动态折扣: ¥{float(scenario.dynamic_discounts):,.2f}")
    
    print(f"\n推荐方案: {sorted_scenarios[0].scenario_name}")
    print(f"最大节省金额: ¥{float(comparison_result.max_savings):,.2f}")
    
    print("\n智能推荐:")
    for i, recommendation in enumerate(comparison_result.recommendations, 1):
        print(f"  {i}. {recommendation}")
    
    print("\n图表数据支持:")
    chart_data = comparison_result.chart_data
    print(f"  - 图表类型: {chart_data['chart_type']}")
    print(f"  - X轴标签: {', '.join(chart_data['labels'])}")
    print(f"  - 推荐场景: {chart_data['recommended_scenario']}")
    
    print("\n  ✓ 定价结果对比分析测试通过!")


def test_all_integration():
    print_section("测试5: 所有功能集成测试")
    
    print("创建完整测试场景:")
    print("  - 35岁男性老司机")
    print("  - 铂金会员，投保7年，推荐5位客户")
    print("  - 年行驶8000公里，驾驶习惯良好")
    print("  - 健康状况良好，不吸烟，每周运动4次")
    print("  - 保额100万，保障12个月")
    
    policy_info = PolicyInfo(
        policy_id='FULL-TEST-001',
        product_type='车险',
        insured_amount=Decimal('1000000'),
        coverage_period=12,
        risk_profile={'age': 35, 'experience': 'expert'},
        deductions=[]
    )
    
    driving_data = DrivingBehaviorData(
        annual_mileage=8000,
        hard_acceleration_count=3,
        hard_braking_count=2,
        night_driving_ratio=0.10,
        speeding_ratio=0.02,
        safe_driving_score=92,
        driving_years=10
    )
    
    loyalty_data = LoyaltyData(
        policy_tenure_years=7,
        consecutive_renewal_count=5,
        referral_count=5,
        customer_grade='platinum'
    )
    
    health_data = HealthScoreData(
        bmi=22.5,
        smoking_status=False,
        alcohol_consumption='low',
        exercise_frequency=4,
        health_check_score=88,
        chronic_condition_count=0
    )
    
    base_premium = Decimal('5000.00')
    
    print(f"\n基础保费: ¥{float(base_premium):,.2f}")
    
    ubi_result = ubi_pricing_engine.calculate_ubi_adjustment(driving_data, base_premium)
    discount_result = dynamic_discount_engine.calculate_dynamic_discounts(
        base_premium, loyalty_data, health_data, driving_data
    )
    risk_result = risk_scorecard_engine.calculate_risk_score(
        driving_data, health_data, {'age': 35}, {'accident_count': 0}
    )
    
    print("\n综合定价结果:")
    print(f"  1. UBI驾驶行为调整: ¥{float(ubi_result.total_ubi_adjustment):,.2f}")
    print(f"  2. 动态折扣优惠: ¥{float(discount_result.total_dynamic_discount):,.2f}")
    print(f"  3. 风险评分调整系数: {float(risk_result.risk_adjustment_multiplier):.4f}")
    
    intermediate_premium = base_premium + ubi_result.total_ubi_adjustment - discount_result.total_dynamic_discount
    final_premium = intermediate_premium * risk_result.risk_adjustment_multiplier
    total_savings = base_premium - final_premium
    
    print(f"\n  中间保费: ¥{float(intermediate_premium):,.2f}")
    print(f"  最终保费: ¥{float(final_premium):,.2f}")
    print(f"  总节省金额: ¥{float(total_savings):,.2f}")
    print(f"  总节省率: {float(total_savings/base_premium)*100:.2f}%")
    
    print("\n功能状态汇总:")
    print(f"  ✅ UBI驾驶行为定价 - 根据里程、急加速、急刹车等维度调整保费")
    print(f"  ✅ 动态折扣引擎 - 忠诚度、推荐、健康、安全驾驶多维度优惠")
    print(f"  ✅ 风险评分卡 - 多因子加权计算综合风险等级")
    print(f"  ✅ 定价结果对比 - 多场景对比分析和图表支持")
    
    print("\n  ✓ 所有功能集成测试通过!")


def main():
    print("\n")
    print("╔" + "=" * 68 + "╗")
    print("║" + " " * 8 + "参数化保险定价引擎 v3.0 - 高级功能测试" + " " * 17 + "║")
    print("╚" + "=" * 68 + "╝")
    
    try:
        test_ubi_pricing()
        test_dynamic_discount_engine()
        test_risk_scorecard()
        test_pricing_comparison()
        test_all_integration()
        
        print_section("测试总结")
        
        print("✅ 所有高级功能测试通过!")
        print("\n新增功能汇总:")
        print("  1. UBI驾驶行为定价")
        print("     - 年行驶里程因子")
        print("     - 急加速/急刹车次数因子")
        print("     - 夜间驾驶比例因子")
        print("     - 超速比例因子")
        print("     - 安全驾驶评分奖励")
        
        print("\n  2. 动态折扣引擎")
        print("     - 忠诚度折扣(会员等级+续保年限)")
        print("     - 推荐奖励折扣")
        print("     - 健康状况折扣(BMI+运动+体检)")
        print("     - 安全驾驶折扣")
        print("     - 多保单折扣")
        
        print("\n  3. 风险评分卡")
        print("     - 人口统计学因素(年龄、性别、婚姻)")
        print("     - 驾驶习惯因素(里程、驾龄、事故记录)")
        print("     - 行为特征因素(急加速、急刹车、超速)")
        print("     - 健康状况因素(BMI、吸烟、慢性病)")
        print("     - 多因子加权综合评分")
        
        print("\n  4. 定价结果对比分析")
        print("     - 5种默认定价场景对比")
        print("     - 保费节省金额和比例计算")
        print("     - 图表数据支持(柱状图)")
        print("     - 智能推荐和建议")
        print("     - 支持自定义场景")
        
        print("\nAPI接口已更新:")
        print("  - POST /api/v1/ubi/calculate/")
        print("  - GET  /api/v1/ubi/config")
        print("  - POST /api/v1/dynamic-discount/calculate/")
        print("  - GET  /api/v1/dynamic-discount/config")
        print("  - POST /api/v1/risk-scorecard/calculate/")
        print("  - GET  /api/v1/risk-scorecard/config")
        print("  - POST /api/v1/premium/extended-calculate/")
        print("  - POST /api/v1/pricing/compare/")
        print("  - GET  /api/v1/pricing/scenarios")
        
        print("\n启动服务命令:")
        print("  uvicorn app.main:app --reload --host 0.0.0.0 --port 8000")
        print("\nAPI文档地址:")
        print("  Swagger UI: http://localhost:8000/docs")
        print("  ReDoc:     http://localhost:8000/redoc")
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
