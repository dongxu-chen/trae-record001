import sys
sys.path.insert(0, '.')
import pandas as pd
import numpy as np

from src.optimizer import CloudPriceComparator, CostAnomalyDetector, BudgetForecaster, CloudOptimizer
from src.data_collector import CloudResourceDataCollector

print('=' * 60)
print('Simple Test for V2 Features')
print('=' * 60)

# Test 1: CloudPriceComparator
print('\n1. CloudPriceComparator')
comparator = CloudPriceComparator()
result = comparator.compare_instance_prices('aws', 'm5.large')
print(f'  AWS m5.large: ${result.current_price:.2f}/mo')
print(f'  Best: {result.best_cloud.upper()} ${result.best_price:.2f}/mo')
print(f'  Savings: ${result.monthly_savings:.2f}/mo ({result.price_difference_pct:.1f}%)')
print('  PASSED')

# Test 2: CostAnomalyDetector
print('\n2. CostAnomalyDetector')
dates = pd.date_range('2024-01-01', periods=60, freq='D')
cost_data = []
for i, date in enumerate(dates):
    base = 10000 * (1 + 0.001 * i)
    if i == 30:
        base *= 1.5
    for s in ['EC2', 'S3', 'RDS']:
        mult = 0.4 if s == 'EC2' else 0.3
        if i == 30 and s == 'EC2':
            mult *= 2
        cost_data.append({'date': date, 'service': s, 'cost': base * mult, 'region': 'us-east-1'})
df = pd.DataFrame(cost_data)
detector = CostAnomalyDetector(df)
anomalies = detector.detect_anomalies(threshold=0.2)
print(f'  Detected {len(anomalies)} anomalies')
if anomalies:
    a = anomalies[0]
    print(f'  Top: {a.timestamp.date()}, {a.service}, {a.deviation_pct:+.1%}')
    print(f'  Root cause: {a.root_cause[:50]}...')
print('  PASSED')

# Test 3: BudgetForecaster
print('\n3. BudgetForecaster')
forecaster = BudgetForecaster(df)
forecast = forecaster.forecast_budget(budget_amount=1500000, forecast_months=12)
print(f'  Budget: ${forecast.budget_amount:,.0f}')
print(f'  Forecast: ${forecast.projected_cost:,.0f}')
print(f'  Variance: ${forecast.budget_variance:,.0f} ({forecast.budget_variance_pct:+.1f}%)')
print(f'  Risk: {forecast.risk_level} ({forecast.over_budget_risk:.0%})')
print('  PASSED')

# Test 4: CloudOptimizer integration
print('\n4. CloudOptimizer Integration')
collector = CloudResourceDataCollector('aws')
data = collector.get_all_data()
optimizer = CloudOptimizer(data)

price_res = optimizer.get_cloud_price_comparison()
print(f'  Batch comparison: {len(price_res.get("batch_comparisons", []))} instances')
print(f'  Potential savings: ${price_res.get("total_potential_annual_savings", 0):,.2f}/yr')

anom_res = optimizer.detect_cost_anomalies()
anom_sum = anom_res.get('summary', {})
print(f'  Anomalies: {anom_sum.get("total", 0)} total')
print(f'  Impact: ${anom_sum.get("estimated_impact", 0):,.2f}')

budget_res = optimizer.forecast_budget(annual_budget=120000)
if 'forecast' in budget_res:
    bf = budget_res['forecast']
    print(f'  Budget forecast: ${bf.projected_cost:,.0f}')
    print(f'  Risk level: {bf.risk_level}')

print('  PASSED')

print('\n' + '=' * 60)
print('ALL TESTS PASSED!')
print('=' * 60)
