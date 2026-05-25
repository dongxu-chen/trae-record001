import warnings
warnings.filterwarnings('ignore')
import numpy as np
import pandas as pd

print("=" * 70)
print("商品价格弹性分析系统 - 新增功能验证")
print("=" * 70)

print("\n✅ 已实现的三大新增功能:")
print("-" * 70)

print("\n📊 功能1: 品类间交叉弹性分析")
print("  核心能力:")
print("  • 多商品价格-销量联合建模 (OLS回归)")
print("  • 交叉弹性矩阵计算 (替代品/互补品识别)")
print("  • Bootstrap稳健置信区间估计")
print("  • 某商品调价对其他商品的销量影响模拟")
print("  • 品类级弹性汇总分析")
print("  • 交叉弹性热力图可视化")

print("\n⚡ 功能2: 动态定价模拟")
print("  核心能力:")
print("  • 5种定价策略: 固定价格/跟随竞品/动态毛利/弹性优化/时段定价")
print("  • 考虑交叉弹性影响的收益预测")
print("  • 多策略对比分析与最优策略推荐")
print("  • 逐日定价模拟 (含库存、竞品价格动态)")
print("  • 收益、利润、销量多维度评估")

print("\n🎯 功能3: 价格阈值检测 (心理价位临界点)")
print("  核心能力:")
print("  • 4种检测方法: K-means聚类/相关系数突变/分位数导数/滚动弹性断点")
print("  • 多方法综合验证，提高检测可靠性")
print("  • 价格区间划分与弹性异质性分析")
print("  • 心理价位识别 (9尾数/整数/5尾数定价)")
print("  • 最优定价区间推荐")

print("\n" + "=" * 70)

# 验证模块导入
print("\n🔍 模块导入验证:")
try:
    from cross_elasticity import CrossElasticityAnalyzer
    print("  ✅ cross_elasticity 模块导入成功")
except Exception as e:
    print(f"  ❌ cross_elasticity 导入失败: {e}")

try:
    from dynamic_pricing import DynamicPricingSimulator, PricingStrategyType, PricingStrategy
    print("  ✅ dynamic_pricing 模块导入成功")
except Exception as e:
    print(f"  ❌ dynamic_pricing 导入失败: {e}")

try:
    from price_threshold import PriceThresholdDetector
    print("  ✅ price_threshold 模块导入成功")
except Exception as e:
    print(f"  ❌ price_threshold 导入失败: {e}")

try:
    from visualization import (
        plot_cross_elasticity_heatmap, plot_cross_elasticity_impact,
        plot_dynamic_pricing_comparison, plot_pricing_timeline,
        plot_price_thresholds, plot_price_segments_comparison
    )
    print("  ✅ 可视化函数导入成功")
except Exception as e:
    print(f"  ❌ 可视化函数导入失败: {e}")

# 验证数据生成
print("\n🔍 数据生成验证:")
try:
    from data_generator import generate_multi_product_sales_data, preprocess_multi_product_data
    from data_generator import generate_historical_sales_data, preprocess_data
    
    df_multi = generate_multi_product_sales_data(n_products=4, n_periods=90)
    print(f"  ✅ 多商品数据生成: {len(df_multi)} 行, {df_multi['product_id'].nunique()} 个商品")
    
    df_single = generate_historical_sales_data(n_periods=200)
    df_single_p = preprocess_data(df_single)
    print(f"  ✅ 单商品数据生成: {len(df_single_p)} 行")
except Exception as e:
    print(f"  ❌ 数据生成失败: {e}")
    import traceback
    traceback.print_exc()

# 验证核心功能
print("\n🔍 核心功能验证:")

# 1. 交叉弹性分析
print("\n  1. 交叉弹性分析:")
try:
    df_multi_p = preprocess_multi_product_data(df_multi)
    analyzer = CrossElasticityAnalyzer(n_bootstrap=10, confidence_level=0.95)
    result = analyzer.fit(df_multi_p)
    
    matrix_shape = result['cross_elasticity_matrix'].shape
    n_significant = len(result['significant_cross_pairs'])
    
    print(f"     ✅ 交叉弹性矩阵: {matrix_shape[0]}x{matrix_shape[1]}")
    print(f"     ✅ 显著交叉关系: {n_significant} 对")
    
    # 测试调价影响模拟
    pids = sorted(df_multi_p['product_id'].unique())
    impact = analyzer.simulate_price_change_impact(pids[0], -0.10)
    print(f"     ✅ 调价影响模拟: 影响 {len(impact)} 个商品")
    
    # 测试热力图数据
    heatmap = analyzer.get_elasticity_heatmap_data()
    print(f"     ✅ 热力图数据生成成功")
    
except Exception as e:
    print(f"     ❌ 失败: {e}")
    import traceback
    traceback.print_exc()

# 2. 动态定价模拟
print("\n  2. 动态定价模拟:")
try:
    from logit_elasticity_model import PriceElasticityModel
    
    model = PriceElasticityModel(threshold_quantile=0.5, n_bootstrap=10)
    model.fit(df_single_p, feature_set='full')
    
    simulator = DynamicPricingSimulator(
        product_model=model,
        variable_cost=50.0,
        fixed_cost=10000.0
    )
    
    strategies = simulator.create_default_strategies(base_price=100.0)
    print(f"     ✅ 定价策略生成: {len(strategies)} 个策略")
    
    # 模拟单个策略
    result = simulator.simulate_strategy(df_single_p, strategies[0], n_days=14)
    print(f"     ✅ 单策略模拟: {len(result['simulation_data'])} 天")
    print(f"       总收益: {result['comparison']['total_revenue']:,.0f} 元")
    print(f"       总利润: {result['comparison']['total_profit']:,.0f} 元")
    
    # 多策略对比
    compare = simulator.compare_strategies(df_single_p, strategies[:3], n_days=14)
    print(f"     ✅ 多策略对比: {len(compare['comparison_summary'])} 个策略")
    print(f"       最优策略: {compare['best_strategy']}")
    
except Exception as e:
    print(f"     ❌ 失败: {e}")
    import traceback
    traceback.print_exc()

# 3. 价格阈值检测
print("\n  3. 价格阈值检测:")
try:
    detector = PriceThresholdDetector(n_clusters=4, min_bootstrap_samples=50)
    thresholds = detector.detect_thresholds(
        df_single_p,
        price_col='effective_price',
        sales_col='sales_quantity',
        method='combined'
    )
    
    n_combined = len(thresholds.get('combined', {}).get('thresholds', []))
    n_segments = len(detector.price_segments) if detector.price_segments is not None else 0
    
    print(f"     ✅ 阈值检测完成: {n_combined} 个综合阈值")
    print(f"     ✅ 价格区间划分: {n_segments} 个区间")
    
    # 测试推荐
    recs = detector.get_threshold_recommendations()
    if recs['optimal_price_segment']:
        opt = recs['optimal_price_segment']
        print(f"     ✅ 最优定价区间: {opt['price_range_lower']:.0f} - {opt['price_range_upper']:.0f} 元")
    
    if recs['psychological_prices']:
        print(f"     ✅ 心理价位点: {len(recs['psychological_prices'])} 个")
    
    # 测试区间对比数据
    seg_data = detector.get_segment_comparison_data()
    print(f"     ✅ 区间对比数据生成成功")
    
except Exception as e:
    print(f"     ❌ 失败: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 70)
print("🎉 所有新增功能验证完成!")
print("=" * 70)

print("\n📁 新增文件清单:")
print("  • cross_elasticity.py - 交叉弹性分析模块")
print("  • dynamic_pricing.py - 动态定价模拟模块")
print("  • price_threshold.py - 价格阈值检测模块")

print("\n🔄 更新文件清单:")
print("  • data_generator.py - 新增多商品数据生成函数")
print("  • visualization.py - 新增6个可视化图表函数")
print("  • app.py - 新增3个功能标签页的UI界面")
print("  • test_model.py - 新增3个功能测试用例")
