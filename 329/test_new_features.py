import warnings
warnings.filterwarnings('ignore')

import sys
import traceback
import numpy as np
import pandas as pd

print("=" * 60)
print("新增功能测试: 交叉弹性 + 动态定价 + 价格阈值")
print("=" * 60)

tests_passed = 0
tests_failed = 0

# 测试1: 交叉弹性分析
try:
    print("\n[1/3] 测试交叉弹性分析模块...")
    from data_generator import generate_multi_product_sales_data, preprocess_multi_product_data
    from cross_elasticity import CrossElasticityAnalyzer
    
    df_multi_raw = generate_multi_product_sales_data(n_products=5, n_periods=180)
    print(f"  OK 多商品数据生成成功: {len(df_multi_raw)} 行, {df_multi_raw['product_id'].nunique()} 个商品")
    
    df_multi_processed = preprocess_multi_product_data(df_multi_raw)
    print(f"  OK 多商品数据预处理成功: {len(df_multi_processed)} 行")
    
    cross_analyzer = CrossElasticityAnalyzer(n_bootstrap=100, confidence_level=0.95)
    cross_results = cross_analyzer.fit(df_multi_processed)
    print(f"  OK 交叉弹性模型训练成功")
    
    if 'cross_elasticity_matrix' in cross_results:
        print(f"  - 交叉弹性矩阵: {cross_results['cross_elasticity_matrix'].shape}")
        print(f"  - 对角线自弹性均值: {np.mean(np.diag(cross_results['cross_elasticity_matrix'].values)):.3f}")
    
    if 'significant_cross_pairs' in cross_results and len(cross_results['significant_cross_pairs']) > 0:
        print(f"  - 显著交叉关系: {len(cross_results['significant_cross_pairs'])} 对")
        for _, row in cross_results['significant_cross_pairs'].head(3).iterrows():
            print(f"    * {row['source_product']} -> {row['target_product']}: {row['cross_elasticity']:.3f} ({row['relationship_type']})")
    
    product_ids = sorted(df_multi_processed['product_id'].unique())
    cross_impact = cross_analyzer.simulate_price_change_impact(
        source_product_id=product_ids[0],
        price_change_pct=-0.10
    )
    print(f"  OK 调价影响模拟成功: {len(cross_impact)} 个商品受影响")
    print(f"  - 商品{product_ids[0]}降价10% 总销量变化: {cross_impact['expected_sales_change'].sum():+.0f} 件")
    
    heatmap_data = cross_analyzer.get_elasticity_heatmap_data()
    print(f"  OK 热力图数据生成成功")
    
    tests_passed += 1
    
except Exception as e:
    print(f"  FAIL 交叉弹性分析测试失败: {e}")
    traceback.print_exc()
    tests_failed += 1

# 测试2: 动态定价模拟
try:
    print("\n[2/3] 测试动态定价模拟模块...")
    from data_generator import generate_historical_sales_data, preprocess_data
    from logit_elasticity_model import PriceElasticityModel
    from dynamic_pricing import DynamicPricingSimulator, PricingStrategyType
    
    df_raw = generate_historical_sales_data(base_price=100.0, base_demand=500, price_elasticity=-2.5, n_periods=200)
    df_processed = preprocess_data(df_raw)
    
    model = PriceElasticityModel(threshold_quantile=0.5, decouple_promotion=True, n_bootstrap=100)
    model.fit(df_processed, feature_set='full')
    print(f"  OK 基础模型训练成功")
    
    dynamic_simulator = DynamicPricingSimulator(
        product_model=model,
        cross_analyzer=cross_analyzer if 'cross_analyzer' in locals() else None,
        variable_cost=50.0,
        fixed_cost=10000.0
    )
    print(f"  OK 动态定价模拟器初始化成功")
    
    default_strategies = dynamic_simulator.create_default_strategies(base_price=100.0, product_id=0)
    print(f"  OK 默认策略生成成功: {len(default_strategies)} 个策略")
    for s in default_strategies:
        print(f"    - {s.strategy_type.value}")
    
    test_strategy = next(s for s in default_strategies if s.strategy_type == PricingStrategyType.FIXED_PRICE)
    single_result = dynamic_simulator.simulate_strategy(df_processed, test_strategy, n_days=30)
    print(f"  OK 单策略模拟成功")
    print(f"  - 总收益: {single_result['comparison']['total_revenue']:,.0f} 元")
    print(f"  - 总利润: {single_result['comparison']['total_profit']:,.0f} 元")
    print(f"  - 收益变化: {single_result['comparison']['revenue_change_pct']*100:+.1f}%")
    
    compare_result = dynamic_simulator.compare_strategies(df_processed, default_strategies[:3], n_days=30)
    print(f"  OK 多策略对比成功: {len(compare_result['comparison_summary'])} 个策略")
    print(f"  - 最优策略: {compare_result['best_strategy']}")
    
    tests_passed += 1
    
except Exception as e:
    print(f"  FAIL 动态定价模拟测试失败: {e}")
    traceback.print_exc()
    tests_failed += 1

# 测试3: 价格阈值检测
try:
    print("\n[3/3] 测试价格阈值检测模块...")
    from price_threshold import PriceThresholdDetector
    
    detector = PriceThresholdDetector(n_clusters=4, min_bootstrap_samples=100, confidence_level=0.95)
    print(f"  OK 阈值检测器初始化成功")
    
    threshold_results = detector.detect_thresholds(
        df_processed,
        price_col='effective_price',
        sales_col='sales_quantity',
        method='combined'
    )
    print(f"  OK 阈值检测完成")
    
    for method_name in ['kmeans', 'changepoint', 'quantile', 'elasticity']:
        if method_name in threshold_results:
            n_thresh = len(threshold_results[method_name].get('thresholds', []))
            print(f"  - {method_name}方法: {n_thresh} 个阈值")
    
    thresholds = threshold_results.get('combined', {}).get('thresholds', [])
    print(f"  - 综合检测到阈值数: {len(thresholds)} 个")
    for t in thresholds[:3]:
        methods = ','.join(t.get('detection_methods', []))
        print(f"    * {t['threshold_price']:.0f} 元 (置信度: {t.get('confidence', 0):.0%}, 方法: {methods})")
    
    price_segments = detector.price_segments
    if price_segments is not None and len(price_segments) > 0:
        print(f"  OK 价格区间划分成功: {len(price_segments)} 个区间")
        for _, seg in price_segments.iterrows():
            elast = seg['price_elasticity'] if seg['price_elasticity'] is not None else 'N/A'
            print(f"    * {seg['price_range_lower']:.0f}-{seg['price_range_upper']:.0f}元: 弹性={elast}, 销量={seg['avg_sales']:.0f}")
    
    recommendations = detector.get_threshold_recommendations()
    print(f"  OK 定价建议生成成功")
    if recommendations['optimal_price_segment']:
        opt = recommendations['optimal_price_segment']
        print(f"  - 最优定价区间: {opt['price_range_lower']:.0f} - {opt['price_range_upper']:.0f} 元")
    
    if recommendations['psychological_prices']:
        print(f"  - 心理价位点: {len(recommendations['psychological_prices'])} 个")
        for p in recommendations['psychological_prices'][:3]:
            print(f"    * {p['price']:.0f} 元 ({p['type']})")
    
    segment_data = detector.get_segment_comparison_data()
    print(f"  OK 区间对比数据生成成功")
    
    tests_passed += 1
    
except Exception as e:
    print(f"  FAIL 价格阈值检测测试失败: {e}")
    traceback.print_exc()
    tests_failed += 1

print("\n" + "=" * 60)
print(f"测试完成: {tests_passed}/{tests_passed + tests_failed} 通过")
print("=" * 60)

if tests_failed > 0:
    print(f"\n[FAIL] 有 {tests_failed} 个测试失败")
    sys.exit(1)
else:
    print("\n[PASS] 所有新增功能测试通过！")
    sys.exit(0)
