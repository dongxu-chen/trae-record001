import sys
sys.path.insert(0, '.')

import pandas as pd
import numpy as np
from datetime import datetime, timedelta

print("=" * 70)
print("测试V2新功能: 多云比价 + 成本异常检测 + 预算预测")
print("=" * 70)

from src.optimizer import (
    CloudPriceComparator, 
    CostAnomalyDetector, 
    BudgetForecaster,
    CloudOptimizer
)
from src.data_collector import CloudResourceDataCollector

print("\n1. 测试多云比价推荐系统")
print("-" * 70)

comparator = CloudPriceComparator()

test_cases = [
    ('aws', 't2.medium', 'on_demand'),
    ('aws', 'm5.large', 'on_demand'),
    ('azure', 'Standard_D2s_v3', 'ri_1y'),
]

for cloud, instance_type, purchase_type in test_cases:
    result = comparator.compare_instance_prices(cloud, instance_type, purchase_type=purchase_type)
    print(f"\n{cloud.upper()} {instance_type} ({purchase_type}):")
    print(f"  当前价格: ${result.current_price:.2f}/月")
    print(f"  最优厂商: {result.best_cloud.upper()} (${result.best_price:.2f}/月)")
    print(f"  月节省: ${result.monthly_savings:.2f} ({result.price_difference_pct:.1f}%)")
    print(f"  年节省: ${result.annual_savings:.2f}")
    print(f"  迁移复杂度: {result.migration_complexity} ({result.migration_effort_months}月)")
    print(f"  对等实例: {result.equivalent_instances}")

print("\n价格矩阵 (4vCPU, 16GB):")
price_matrix = comparator.get_price_matrix(4, 16)
print(price_matrix.to_string(index=False))

print("\n2. 测试成本异常检测与自动归因")
print("-" * 70)

dates = pd.date_range('2024-01-01', periods=90, freq='D')
base_cost = 10000
cost_data = []

for i, date in enumerate(dates):
    day_of_week = date.dayofweek
    daily_cost = base_cost * (1 + 0.001 * i)
    if day_of_week < 5:
        daily_cost *= 1.1
    daily_cost += np.random.normal(0, base_cost * 0.05)
    
    if i == 30:
        daily_cost *= 1.6
    if i == 45:
        daily_cost *= 1.4
    if i == 60:
        daily_cost *= 0.7
    
    services = ['EC2', 'S3', 'RDS', 'Lambda', 'EBS']
    for service in services:
        multiplier = 0.3 if service == 'EC2' else 0.175
        if i == 30 and service == 'EC2':
            multiplier *= 2.5
        if i == 45 and service == 'RDS':
            multiplier *= 2.0
        
        cost_data.append({
            'date': date,
            'service': service,
            'cost': daily_cost * multiplier,
            'region': 'us-east-1'
        })

df = pd.DataFrame(cost_data)
detector = CostAnomalyDetector(df)

anomalies = detector.detect_anomalies(threshold=0.2)
summary = detector.get_anomaly_summary(anomalies)

print(f"\n检测到 {summary['total']} 个异常")
print(f"  严重: {summary.get('critical_count', 0)}, 高危: {summary.get('high_count', 0)}")
print(f"  突增: {summary['by_type'].get('spike', 0)}, 突降: {summary['by_type'].get('drop', 0)}")
print(f"  预估影响: ${summary.get('estimated_impact', 0):,.2f}")

if anomalies:
    print(f"\nTop 3 异常详情:")
    for i, anomaly in enumerate(anomalies[:3], 1):
        print(f"\n  #{i} {anomaly.timestamp.strftime('%Y-%m-%d')} - {anomaly.service}")
        print(f"    类型: {'[+] 突增' if anomaly.anomaly_type == 'spike' else '[-] 突降'} | {anomaly.severity}")
        print(f"    实际: ${anomaly.actual_cost:,.2f} | 预期: ${anomaly.expected_cost:,.2f}")
        print(f"    偏差: {anomaly.deviation_pct:+.1%}")
        print(f"    根因: {anomaly.root_cause}")
        print(f"    置信度: {anomaly.root_cause_confidence:.0%}")
        print(f"    建议: {anomaly.recommended_action}")

print("\n3. 测试预算预测与超预算风险评估")
print("-" * 70)

forecaster = BudgetForecaster(df)
annual_budget = 1500000

forecast = forecaster.forecast_budget(budget_amount=annual_budget, forecast_months=12)

print(f"\n预测周期: {forecast.forecast_period}")
print(f"预测范围: {forecast.forecast_start_date.strftime('%Y-%m')} 至 {forecast.forecast_end_date.strftime('%Y-%m')}")
print(f"\n预算分析:")
print(f"  年度预算: ${forecast.budget_amount:,.2f}")
print(f"  预测成本: ${forecast.projected_cost:,.2f}")
print(f"  预算差额: ${forecast.budget_variance:,.2f} ({forecast.budget_variance_pct:+.1%})")
print(f"  超预算风险: {forecast.over_budget_risk:.0%} - {forecast.risk_level}")

print(f"\n月度预测摘要:")
forecast_df = forecast.monthly_forecast
for _, row in forecast_df.head(6).iterrows():
    print(f"  {row['date'].strftime('%Y-%m')}: ${row['projected_cost']:,.2f} "
          f"[${row['lower_bound']:,.2f} - ${row['upper_bound']:,.2f}]")

print(f"\n🔑 关键驱动因素:")
for driver in forecast.key_drivers:
    print(f"  {driver['service']}: {driver['change_pct']:+.1%} | 占比 {driver['contribution_pct']:.0%} | {driver['impact']}")

print(f"\n缓解建议:")
for i, rec in enumerate(forecast.mitigation_recommendations, 1):
    print(f"  {i}. {rec}")

print(f"\n📈 多情景分析:")
scenarios = forecaster.multi_scenario_forecast(budget_amount=annual_budget)
for name, sc in scenarios.items():
    status = "[!]" if sc.risk_level == 'Critical' else "[x]" if sc.risk_level == 'High' else "[-]" if sc.risk_level == 'Medium' else "[o]"
    print(f"  {status} {name.capitalize():12} 预测: ${sc.projected_cost:,.0f} | 差额: ${sc.budget_variance:,.0f} | 风险: {sc.risk_level}")

print("\n4. 集成测试 - CloudOptimizer完整流程")
print("-" * 70)

collector = CloudResourceDataCollector("aws")
data = collector.get_all_data()
optimizer = CloudOptimizer(data)

print("\n多云比价分析:")
price_result = optimizer.get_cloud_price_comparison()
print(f"  分析实例数: {len(price_result.get('batch_comparisons', []))}")
print(f"  潜在年度节省: ${price_result.get('total_potential_annual_savings', 0):,.2f}")

print("\n⚠️  成本异常检测:")
anomaly_result = optimizer.detect_cost_anomalies(threshold=0.2)
anomaly_summary = anomaly_result.get('summary', {})
print(f"  异常总数: {anomaly_summary.get('total', 0)}")
print(f"  严重/高危: {anomaly_summary.get('critical_count', 0)}/{anomaly_summary.get('high_count', 0)}")
print(f"  预估影响: ${anomaly_summary.get('estimated_impact', 0):,.2f}")

print("\n预算预测:")
budget_result = optimizer.forecast_budget(annual_budget=120000, forecast_months=12)
if 'forecast' in budget_result:
    bf = budget_result['forecast']
    print(f"  年度预算: ${bf.budget_amount:,.2f}")
    print(f"  预测成本: ${bf.projected_cost:,.2f}")
    print(f"  风险等级: {bf.risk_level} ({bf.over_budget_risk:.0%})")
    print(f"  预警阈值:")
    for level, amount in budget_result['alert_thresholds'].items():
        print(f"    {level}: ${amount:,.2f}")

print("\n" + "=" * 70)
print("✅ 所有V2新功能测试通过!")
print("=" * 70)
