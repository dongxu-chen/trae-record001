#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""综合测试 - 验证所有新增功能"""

import sys
import os
import shutil

data_dir = os.path.join(os.path.dirname(__file__), 'data')
if os.path.exists(data_dir):
    shutil.rmtree(data_dir)

print("=" * 80)
print("股票因子回测平台 - 新增功能综合测试")
print("=" * 80)

try:
    print("\n" + "=" * 80)
    print("模块导入测试")
    print("=" * 80)
    
    from data_loader import DataLoader
    print("  ✓ data_loader.py")
    
    from factor_engine import FactorEngine
    print("  ✓ factor_engine.py")
    
    from backtest import BacktestEngine
    print("  ✓ backtest.py")
    
    from performance import PerformanceAnalyzer
    print("  ✓ performance.py")
    
    from visualization import Visualizer
    print("  ✓ visualization.py")
    
    from genetic_factor_mining import GeneticFactorMiner
    print("  ✓ genetic_factor_mining.py")
    
    from simulated_trading import TradingSimulator, SignalPusher, SimulatedBroker
    print("  ✓ simulated_trading.py")
    
    from attribution_analysis import FactorAttribution, AttributionVisualizer
    print("  ✓ attribution_analysis.py")
    
    print("\n所有模块导入成功!")
    
except Exception as e:
    print(f"\n模块导入失败: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

try:
    print("\n" + "=" * 80)
    print("功能1: 遗传编程因子挖掘测试")
    print("=" * 80)
    
    print("\n[1/3] 加载数据...")
    loader = DataLoader()
    loader.generate_sample_data(n_stocks=40, start_date='2022-01-01', end_date='2023-06-30')
    price, factors, suspend, delist, industry = loader.load_data()
    returns = loader.calculate_daily_returns()
    mkt_cap = factors.get('MKT_CAP')
    print(f"  ✓ 数据加载完成: {price.shape[1]} 只股票")
    
    print("\n[2/3] 准备回测...")
    backtest = BacktestEngine(returns, suspend, delist, industry, mkt_cap)
    rebalance_dates = backtest.get_rebalance_dates(freq='M')
    
    print("\n[3/3] 运行遗传挖掘 (简化版)...")
    miner = GeneticFactorMiner(
        factors, returns, rebalance_dates,
        base_factors=['PE', 'PB', 'ROE'],
        population_size=15,
        max_generations=2
    )
    
    best_factors = miner.mine_factors(verbose=True)
    
    print(f"\n  ✓ 挖掘完成，找到 {len(best_factors)} 个有效因子")
    if best_factors:
        print(f"  ✓ 最佳因子: {best_factors[0].expression}")
        print(f"  ✓ 适应度: {best_factors[0].fitness:.4f}")
        print(f"  ✓ 过拟合分数: {best_factors[0].overfitting_score:.4f}")
    
except Exception as e:
    print(f"\n遗传编程因子挖掘测试失败: {e}")
    import traceback
    traceback.print_exc()

try:
    print("\n" + "=" * 80)
    print("功能2: 归因分析测试")
    print("=" * 80)
    
    print("\n[1/3] 计算因子...")
    engine = FactorEngine(factors)
    factor = engine.calculate_factor('1 / PE')
    factor_ffill = loader.forward_fill_factor_for_suspend(factor)
    print(f"  ✓ 因子计算完成")
    
    print("\n[2/3] 分组回测...")
    groups = backtest.assign_groups(factor_ffill, rebalance_dates)
    print(f"  ✓ 分组完成")
    
    print("\n[3/3] 运行归因分析...")
    attribution = FactorAttribution(returns, industry, factors)
    attribution.calculate_industry_returns()
    attribution.calculate_style_returns()
    
    result = attribution.decompose_group_returns(groups, group=1)
    
    print(f"\n  ✓ Group 1 收益分解:")
    print(f"    总收益: {result.total_return*100:.2f}%")
    print(f"    行业收益: {result.industry_return*100:.2f}%")
    print(f"    风格收益: {result.style_return*100:.2f}%")
    print(f"    特异性收益: {result.specific_return*100:.2f}%")
    
    print("\n  ✓ 生成可视化图表...")
    visualizer = AttributionVisualizer()
    
    group1_weights = (groups == 1).astype(float).div(
        (groups == 1).sum(axis=1), axis=0
    ).fillna(0)
    attribution_df = attribution.decompose_returns(group1_weights)
    
    visualizer.plot_attribution_breakdown(attribution_df, 'Test_Attr', save=True, show=False)
    print("  ✓ 归因分析图表生成完成")
    
except Exception as e:
    print(f"\n归因分析测试失败: {e}")
    import traceback
    traceback.print_exc()

try:
    print("\n" + "=" * 80)
    print("功能3: WebSocket模拟交易组件测试")
    print("=" * 80)
    
    print("\n[1/2] 测试模拟经纪商...")
    broker = SimulatedBroker(initial_capital=1000000.0)
    print(f"  ✓ 初始资金: {broker.cash:.2f}")
    
    order = broker.place_order('STOCK_001', 'BUY', 100, 50.0)
    if order:
        print(f"  ✓ 订单执行: {order.side} {order.quantity} {order.stock} @ {order.price}")
        print(f"  ✓ 剩余资金: {broker.cash:.2f}")
        print(f"  ✓ 持仓数: {len(broker.positions)}")
    
    print("\n[2/2] 测试信号生成...")
    simulator = TradingSimulator(factor_ffill, price, groups)
    signals = simulator.generate_signals(factor_ffill.index[0], 'Test_Factor')
    print(f"  ✓ 单日期信号数: {len(signals)}")
    if signals:
        print(f"  ✓ 信号示例: {signals[0].stock} Group {signals[0].group} {signals[0].action}")
    
    print("\n  ✓ WebSocket组件测试完成")
    print("    (完整的WebSocket服务端/客户端测试请独立运行)")
    
except Exception as e:
    print(f"\nWebSocket模拟交易测试失败: {e}")
    import traceback
    traceback.print_exc()

try:
    print("\n" + "=" * 80)
    print("功能4: 基础回测功能验证")
    print("=" * 80)
    
    print("\n[1/3] 运行完整回测...")
    backtest_results = backtest.run_backtest(
        factor_ffill, rebalance_freq='M',
        neutralize=True, industry_neutral=True
    )
    print("  ✓ 回测完成")
    
    print("\n[2/3] 绩效分析...")
    analyzer = PerformanceAnalyzer()
    report = analyzer.generate_report(backtest_results, factor_ffill, returns)
    
    print(f"  ✓ Group 1 年化收益: {report['group_performance'].loc[1, 'Annualized Return']*100:.2f}%")
    print(f"  ✓ 调仓周期IC Mean: {report['ic_stats']['rebalance']['Mean IC']:.4f}")
    print(f"  ✓ 调仓周期IC IR: {report['ic_stats']['rebalance']['IR']:.4f}")
    
    print("\n[3/3] 可视化生成...")
    viz = Visualizer()
    viz.generate_all_plots(backtest_results, report, 'Test_Full', save=True, show=False)
    print("  ✓ 图表生成完成")
    
except Exception as e:
    print(f"\n基础回测功能验证失败: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 80)
print("所有测试完成!")
print("=" * 80)

print("\n" + "=" * 80)
print("新增功能汇总")
print("=" * 80)
print("""
1. ✓ 遗传编程因子挖掘
   - 自动组合因子表达式
   - 基于IC IR的适应度评估
   - 训练/测试集分离评估过拟合风险
   - 输出Top因子及过拟合分数

2. ✓ WebSocket模拟交易对接
   - SignalPusher: WebSocket信号推送服务
   - SimulatedBroker: 模拟经纪商（下单、持仓、资产计算）
   - TradingSimulator: 模拟交易引擎
   - MockTradingClient: 客户端监听
   - 消息类型: SIGNAL, PORTFOLIO, ORDER_CONFIRM

3. ✓ 归因分析
   - FactorAttribution: 收益分解（行业、风格、特异性）
   - 行业暴露收益分解
   - 风格因子收益分解（市值、价值、盈利）
   - 特异性收益（Alpha）
   - AttributionVisualizer: 归因分析可视化

4. ✓ 按调仓周期计算IC
   - 消除预测周期错配
   - 月度因子对应月度收益
   - 更准确的因子有效性评估
""")
print("=" * 80)
