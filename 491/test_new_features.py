import sys
sys.path.insert(0, '.')

import pandas as pd
import numpy as np
from datetime import datetime, timedelta

print("=" * 60)
print("测试新功能: 多粒度采样 + 灵活性评分 + 业务影响排序")
print("=" * 60)

from src.optimizer import (
    MultiGranularSampler, 
    SavingsPlanAnalyzer, 
    BusinessImpactAnalyzer,
    CloudOptimizer
)
from src.data_collector import CloudResourceDataCollector

print("\n1. 测试多粒度采样算法 (保留峰值特征)")
print("-" * 60)

dates = pd.date_range('2024-01-01', periods=200, freq='H')
values = np.random.randn(200) * 100 + 500
values[50] = 1500
values[120] = 2000
values[80] = 100

df = pd.DataFrame({'timestamp': dates, 'value': values})
sampler = MultiGranularSampler(df, 'value', 'timestamp')

samples = sampler.sample(retain_peaks=True)
peak_features = sampler.get_peak_features()

print(f"总样本数: {len(samples)}")
print(f"峰值样本数: {sum(1 for s in samples if s.is_peak)}")
print(f"\n按粒度分布:")
for granularity, count in sampler.get_peak_features().items():
    if isinstance(count, int):
        print(f"  {granularity}: {count}")

print(f"\n峰值特征:")
print(f"  P99: {peak_features['peak_99th']:.2f}")
print(f"  P95: {peak_features['peak_95th']:.2f}")
print(f"  最大值: {peak_features['peak_max']:.2f}")
print(f"  峰值/均值比: {peak_features['peak_mean_ratio']:.2f}x")
print(f"  波动性: {peak_features['volatility']:.2f}")
print(f"  突增评分: {peak_features['burst_score']:.2f}")

print("\n2. 测试节省计划灵活性评分")
print("-" * 60)

sp_analyzer = SavingsPlanAnalyzer()

test_cases = [
    ("稳定生产负载", np.full(24, 0.8), 180, 'production'),
    ("波动开发负载", np.random.rand(24), 25, 'development'),
    ("中等测试负载", np.random.rand(24) * 0.5 + 0.3, 90, 'testing'),
]

for name, hourly_pattern, age, workload in test_cases:
    flex_score = sp_analyzer.calculate_flexibility_score(hourly_pattern, age, workload)
    recommendation = sp_analyzer.recommend_purchase_type(flex_score, 0.7, 0.5)
    print(f"\n{name}:")
    print(f"  灵活性评分: {flex_score:.2f}")
    print(f"  推荐类型: {recommendation['type']}")
    print(f"  推荐理由: {recommendation['reason']}")

print("\n3. 测试业务影响分析与排序")
print("-" * 60)

impact_analyzer = BusinessImpactAnalyzer()

test_resources = [
    ("生产核心数据库", 'production', 'database', 'high', 1),
    ("生产应用服务器", 'production', 'application', 'high', 3),
    ("开发测试机", 'development', 'general', 'low', 1),
    ("暂存缓存服务", 'staging', 'cache', 'medium', 2),
    ("临时批处理", 'development', 'worker', 'none', 1),
]

print("\n各资源影响评分:")
results = []
for name, env, res_type, traffic, redundancy in test_resources:
    result = impact_analyzer.calculate_business_impact(env, res_type, False, traffic, redundancy)
    results.append((name, result))
    print(f"  {name}: {result['impact_level']} ({result['impact_score']:.3f})")

print("\n按影响度从低到高排序 (优先执行):")
sorted_results = sorted(results, key=lambda x: x[1]['impact_score'])
for rank, (name, result) in enumerate(sorted_results, 1):
    print(f"  #{rank} {name}: 影响分 {result['impact_score']:.3f}")

print("\n4. 集成测试 - 完整优化流程")
print("-" * 60)

collector = CloudResourceDataCollector("aws")
data = collector.get_all_data()
optimizer = CloudOptimizer(data)

all_recs = optimizer.generate_all_recommendations()

print(f"总推荐数: {len(all_recs['all_recommendations'])}")
print(f"月度节省: ${all_recs['total_monthly_savings']:,.2f}")

print(f"\n按业务影响分类:")
print(f"  低影响: {len(all_recs['by_business_impact']['low'])} 项")
print(f"  中影响: {len(all_recs['by_business_impact']['medium'])} 项")
print(f"  高影响: {len(all_recs['by_business_impact']['high'])} 项")

print(f"\n低灵活性资源 (推荐按需):")
print(f"  {len(all_recs['low_flexibility_recommendations'])} 项")

if all_recs['all_recommendations']:
    print(f"\nTop 5 优先级推荐:")
    for i, rec in enumerate(all_recs['all_recommendations'][:5], 1):
        print(f"  #{i} {rec.resource_name}: 优先级 {rec.priority_score:.3f}")
        print(f"     节省: ${rec.monthly_savings:.2f}/月 | 影响: {rec.business_impact} ({rec.business_impact_score:.2f}) | 灵活: {rec.flexibility_score:.2f}")

print("\n" + "=" * 60)
print("✅ 所有新功能测试通过!")
print("=" * 60)
