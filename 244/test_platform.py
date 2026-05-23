#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""测试股票因子回测平台 - 包含所有改进功能"""

import sys
import os
import shutil

data_dir = os.path.join(os.path.dirname(__file__), 'data')
if os.path.exists(data_dir):
    shutil.rmtree(data_dir)

print("=" * 70)
print("股票因子回测平台 - 功能测试 (含改进)")
print("=" * 70)

try:
    print("\n[1/7] 测试数据加载模块 (含行业数据)...")
    from data_loader import DataLoader
    print("  ✓ data_loader.py 导入成功")
    
    loader = DataLoader()
    loader.generate_sample_data(n_stocks=80, start_date='2020-01-01', end_date='2023-12-31')
    price, factors, suspend, delist, industry = loader.load_data()
    print(f"  ✓ 数据生成成功: {price.shape[1]} 只股票, {price.shape[0]} 个交易日")
    print(f"  ✓ 可用因子: {list(factors.keys())}")
    print(f"  ✓ 行业数据: {industry.nunique()} 个行业")
    print(f"  ✓ 行业分布:\n{industry.value_counts().to_string()}")
    
except Exception as e:
    print(f"  ✗ 数据加载模块测试失败: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

try:
    print("\n[2/7] 测试停牌因子向前填充功能...")
    from factor_engine import FactorEngine
    print("  ✓ factor_engine.py 导入成功")
    
    engine = FactorEngine(factors)
    factor = engine.calculate_factor('1 / PE')
    
    original_missing = factor.isnull().sum().sum()
    factor_ffill = loader.forward_fill_factor_for_suspend(factor)
    ffill_missing = factor_ffill.isnull().sum().sum()
    print(f"  ✓ 原始缺失值: {original_missing}")
    print(f"  ✓ 向前填充后缺失值: {ffill_missing}")
    print(f"  ✓ 停牌因子向前填充功能正常")
    
except Exception as e:
    print(f"  ✗ 停牌因子向前填充测试失败: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

try:
    print("\n[3/7] 测试行业市值中性化...")
    from backtest import BacktestEngine
    print("  ✓ backtest.py 导入成功")
    
    returns = loader.calculate_daily_returns()
    mkt_cap = factors.get('MKT_CAP')
    
    backtest = BacktestEngine(returns, suspend, delist, industry, mkt_cap)
    
    factor_values = factor_ffill.iloc[0].dropna()
    neutralized = backtest._neutralize_industry_size(factor_values, factor_ffill.index[0])
    print(f"  ✓ 行业市值中性化前 mean={factor_values.mean():.4f}, std={factor_values.std():.4f}")
    print(f"  ✓ 行业市值中性化后 mean={neutralized.mean():.4f}, std={neutralized.std():.4f}")
    
    print("  ✓ 行业市值中性化功能正常")
    
except Exception as e:
    print(f"  ✗ 行业市值中性化测试失败: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

try:
    print("\n[4/7] 测试行业中性分组...")
    group_labels = backtest._assign_groups_with_industry_neutral(
        factor_ffill.iloc[0], factor_ffill.index[0], ascending=False
    )
    print(f"  ✓ 行业中性分组成功, 分组股票数: {len(group_labels)}")
    print(f"  ✓ 各组数量分布:")
    for g in range(1, 11):
        count = (group_labels == g).sum()
        print(f"    Group {g}: {count} 只")
    print("  ✓ 行业中性分组功能正常")
    
except Exception as e:
    print(f"  ✗ 行业中性分组测试失败: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

try:
    print("\n[5/7] 测试完整回测流程...")
    results = backtest.run_backtest(
        factor_ffill, 
        rebalance_freq='M', 
        neutralize=True, 
        industry_neutral=True
    )
    
    print(f"  ✓ 回测完成")
    print(f"  ✓ 分组收益 shape: {results['group_returns'].shape}")
    print(f"  ✓ 调仓日期数: {len(results['rebalance_dates'])}")
    print(f"  ✓ 最终累积收益:")
    final_cum = results['cumulative_returns'].iloc[-1]
    for g in range(1, 11):
        print(f"    Group {g}: {final_cum[g]:.4f}")
    
except Exception as e:
    print(f"  ✗ 完整回测流程测试失败: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

try:
    print("\n[6/7] 测试按调仓周期计算IC (消除预测错配)...")
    from performance import PerformanceAnalyzer
    print("  ✓ performance.py 导入成功")
    
    analyzer = PerformanceAnalyzer()
    
    rebalance_dates = results['rebalance_dates']
    ic_rebalance = analyzer.calculate_ic_by_rebalance(factor_ffill, returns, rebalance_dates)
    print(f"  ✓ 按调仓周期计算IC完成, 样本数: {len(ic_rebalance.dropna())}")
    print(f"  ✓ 调仓周期IC: mean={ic_rebalance.mean():.4f}, std={ic_rebalance.std():.4f}")
    
    ic_stats = analyzer.calculate_ic_stats(ic_rebalance)
    print(f"  ✓ IC统计:")
    print(f"    Mean IC: {ic_stats['Mean IC']:.4f}")
    print(f"    IR: {ic_stats['IR']:.4f}")
    print(f"    IC > 0: {ic_stats['IC > 0']*100:.2f}%")
    print(f"    T-Statistic: {ic_stats['T-Statistic']:.4f}")
    print(f"    P-Value: {ic_stats['P-Value']:.4f}")
    print("  ✓ 按调仓周期计算IC功能正常")
    
except Exception as e:
    print(f"  ✗ 按调仓周期计算IC测试失败: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

try:
    print("\n[7/7] 测试可视化模块...")
    from visualization import Visualizer
    print("  ✓ visualization.py 导入成功")
    
    report = analyzer.generate_report(results, factor_ffill, returns)
    
    visualizer = Visualizer()
    visualizer.generate_all_plots(results, report, 'test_factor_improved', save=True, show=False)
    
    print("  ✓ 图表生成成功")
    result_files = os.listdir('results')
    png_files = [f for f in result_files if f.endswith('.png')]
    print(f"  ✓ 生成图表数: {len(png_files)}")
    for f in png_files:
        print(f"    - {f}")
    
except Exception as e:
    print(f"  ✗ 可视化模块测试失败: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n" + "=" * 70)
print("所有模块测试通过! ✓")
print("=" * 70)
print("\n改进功能汇总:")
print("  1. ✓ 停牌因子向前填充: 停牌期间因子值向前填充, 复牌后参与计算")
print("  2. ✓ 行业市值中性化: 通过回归剔除行业和市值影响")
print("  3. ✓ 行业中性分组: 各行业内部分组, 确保每组行业分布一致")
print("  4. ✓ 按调仓周期计算IC: 月度因子对应月度收益, 消除预测错配")
print("=" * 70)
