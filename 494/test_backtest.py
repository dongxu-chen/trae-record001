import warnings
warnings.filterwarnings('ignore')

import numpy as np
import pandas as pd
from datetime import datetime, timedelta

from backtest_engine import BacktestEngine
from parameter_optimizer import ParameterOptimizer
from visualization import BacktestVisualizer
from overfit_detector import OverfitDetector
from multi_timeframe import MultiTimeframeEngine
from live_simulator import LiveSimulator, Position, Order


def _make_sample_data(days=500):
    np.random.seed(42)
    dates = pd.bdate_range(end=datetime.now(), periods=days)
    price = 50.0
    prices = []
    for _ in range(days):
        price *= (1 + np.random.normal(0.0005, 0.02))
        prices.append(price)
    close = np.array(prices)
    high = close * (1 + np.abs(np.random.normal(0, 0.01, days)))
    low = close * (1 - np.abs(np.random.normal(0, 0.01, days)))
    open_ = close * (1 + np.random.normal(0, 0.005, days))
    volume = np.random.randint(100000, 5000000, days).astype(float)
    data = pd.DataFrame({
        'open': open_, 'high': high, 'low': low, 'close': close, 'volume': volume
    }, index=dates)
    return data


def test_backtest():
    print("=" * 50)
    print("测试回测引擎（含滑点模型）...")
    print("=" * 50)
    engine = BacktestEngine(initial_cash=100000, commission=0.001, slippage=0.001)
    try:
        data = _make_sample_data(500)
        print(f"✓ 样本数据生成: {len(data)} 条记录")
        metrics = engine.run_backtest("双均线策略", data, {"fast_period": 5, "slow_period": 20})
        print(f"✓ 回测完成")
        print(f"  最终资产: ¥{metrics['final_value']:,.2f}")
        print(f"  总收益率: {metrics['total_return']:+.2f}%")
        print(f"  夏普比率: {metrics['sharpe_ratio']:.2f}")
        print(f"  最大回撤: {metrics['max_drawdown']:.2f}%")
        print(f"  胜率: {metrics['win_rate']:.1f}%")
        print(f"  交易次数: {metrics['total_trades']}")
        print(f"  总手续费: ¥{metrics.get('total_commission', 0):,.2f}")
        print(f"  平均滑点: {metrics.get('avg_slippage', 0)*100:.4f}%")
        return True
    except Exception as e:
        print(f"✗ 回测失败: {e}")
        import traceback; traceback.print_exc()
        return False


def test_bayesian_optimization():
    print("\n" + "=" * 50)
    print("测试贝叶斯优化...")
    print("=" * 50)
    optimizer = ParameterOptimizer(initial_cash=100000, commission=0.001, slippage=0.001)
    try:
        data = _make_sample_data(300)
        results = optimizer.bayesian_optimization(
            "双均线策略", data,
            param_ranges={'fast_period': (5, 15, 5), 'slow_period': (20, 40, 10)},
            optimize_by='sharpe_ratio', n_calls=10, base_estimator='gp'
        )
        print(f"✓ 贝叶斯优化完成")
        print(f"  最佳参数: {results['best_params']}")
        print(f"  最佳夏普比率: {results['best_metrics']['sharpe_ratio']:.2f}")
        return True
    except ImportError as e:
        print(f"⚠ 需要 scikit-optimize: {e}")
        return True
    except Exception as e:
        print(f"✗ 贝叶斯优化失败: {e}")
        import traceback; traceback.print_exc()
        return False


def test_overfit_detection():
    print("\n" + "=" * 50)
    print("测试过拟合检测...")
    print("=" * 50)
    detector = OverfitDetector(initial_cash=100000, commission=0.001, slippage=0.001)
    try:
        data = _make_sample_data(500)
        
        print("\n--- 样本内外测试 ---")
        result = detector.in_sample_out_sample_test("双均线策略", data, {"fast_period": 5, "slow_period": 20})
        print(f"✓ 样本内外测试完成")
        print(f"  样本内收益率: {result['in_sample']['total_return']:.2f}%")
        print(f"  样本外收益率: {result['out_sample']['total_return']:.2f}%")
        print(f"  收益衰减: {result['return_degradation']:.1f}%")
        print(f"  过拟合判定: {'是' if result['is_overfit'] else '否'} ({result['overfit_severity']})")
        
        print("\n--- 滚动窗口回测 ---")
        rw_result = detector.rolling_window_backtest("双均线策略", data, {"fast_period": 5, "slow_period": 20}, window_ratio=0.5, step_ratio=0.2)
        print(f"✓ 滚动窗口回测完成")
        print(f"  窗口数: {rw_result['num_windows']}")
        print(f"  稳定性评分: {rw_result['stability_score']:.1f}/100")
        print(f"  平均收益率: {rw_result['return_mean']:.2f}%")
        print(f"  正收益窗口比: {rw_result['positive_ratio']*100:.0f}%")
        
        print("\n--- 前向分析 ---")
        wfa = detector.walk_forward_analysis("双均线策略", data, {"fast_period": 5, "slow_period": 20}, n_splits=3)
        print(f"✓ 前向分析完成")
        print(f"  折数: {len(wfa['fold_results'])}")
        print(f"  平均测试收益率: {wfa['avg_test_return']:.2f}%")
        print(f"  一致性: {wfa['consistency']*100:.0f}%")
        
        return True
    except Exception as e:
        print(f"✗ 过拟合检测失败: {e}")
        import traceback; traceback.print_exc()
        return False


def test_multi_timeframe():
    print("\n" + "=" * 50)
    print("测试多周期联合回测...")
    print("=" * 50)
    mtf = MultiTimeframeEngine(initial_cash=100000, commission=0.001, slippage=0.001)
    try:
        data = _make_sample_data(500)
        
        print("\n--- 数据重采样 ---")
        resampled = mtf.resample_data(data, '1w')
        print(f"✓ 重采样为周线: {len(resampled)} 条")
        
        print("\n--- 多周期联合回测 ---")
        result = mtf.multi_timeframe_backtest("双均线策略", data, ['1d', '1w'], {"fast_period": 5, "slow_period": 20})
        print(f"✓ 多周期回测完成")
        
        for tf, tf_res in result['timeframe_results'].items():
            m = tf_res['metrics']
            print(f"  周期 {tf}: 收益={m['total_return']:.2f}%, 夏普={m['sharpe_ratio']:.2f}, 回撤={m['max_drawdown']:.2f}%")
        
        resonance = result.get('resonance_analysis', {})
        if resonance:
            print(f"  共振信号数: {resonance.get('resonance_count', 0)}")
            print(f"  共振比例: {resonance.get('resonance_ratio', 0)*100:.1f}%")
        
        comparison = mtf.get_timeframe_comparison(result)
        print(f"✓ 周期对比表:")
        print(comparison.to_string(index=False))
        
        return True
    except Exception as e:
        print(f"✗ 多周期回测失败: {e}")
        import traceback; traceback.print_exc()
        return False


def test_live_simulator():
    print("\n" + "=" * 50)
    print("测试实盘模拟器...")
    print("=" * 50)
    try:
        sim = LiveSimulator(initial_cash=100000, commission=0.001, slippage=0.001, strategy_name='双均线策略')
        
        sim.current_prices['TEST.SS'] = 100.0
        
        print("\n--- 价格模拟 ---")
        for i in range(5):
            tick = sim.simulate_price_tick('TEST.SS')
            print(f"  Tick {i+1}: ¥{tick['price']:.2f} ({tick['change_pct']:+.3f}%)")
        
        print("\n--- 手动买入 ---")
        qty = (sim.cash * 0.9) / sim.current_prices['TEST.SS']
        order = sim.place_order('TEST.SS', 'buy', qty, 'market')
        print(f"  状态: {order.status}, 成交价: ¥{order.fill_price:.2f}, 数量: {order.quantity:.0f}")
        
        print("\n--- 持仓检查 ---")
        if 'TEST.SS' in sim.positions:
            pos = sim.positions['TEST.SS']
            pos.stop_loss = pos.entry_price * 0.95
            pos.take_profit = pos.entry_price * 1.10
            print(f"  持仓: {pos.size:.0f}股, 入场价: ¥{pos.entry_price:.2f}")
            print(f"  止损: ¥{pos.stop_loss:.2f}, 止盈: ¥{pos.take_profit:.2f}")
        
        print("\n--- 账户概览 ---")
        summary = sim.get_portfolio_summary()
        print(f"  总资产: ¥{summary['total_value']:,.2f}")
        print(f"  现金: ¥{summary['cash']:,.2f}")
        print(f"  收益率: {summary['return_pct']:+.2f}%")
        
        print("\n--- 手动卖出 ---")
        if 'TEST.SS' in sim.positions:
            sim.place_order('TEST.SS', 'sell', sim.positions['TEST.SS'].size, 'market')
        
        stats = sim.get_trade_statistics()
        print(f"  总交易: {stats['total_trades']}, 胜率: {stats['win_rate']:.1f}%")
        print(f"  总盈亏: ¥{stats['total_pnl']:,.2f}")
        
        print("\n--- 状态保存/加载 ---")
        sim.save_state()
        sim2 = LiveSimulator(initial_cash=100000)
        loaded = sim2.load_state()
        print(f"  状态加载: {'成功' if loaded else '失败'}")
        if loaded:
            s2 = sim2.get_portfolio_summary()
            print(f"  总资产: ¥{s2['total_value']:,.2f}")
        
        import os
        if os.path.exists('live_sim_state.json'):
            os.remove('live_sim_state.json')
        
        return True
    except Exception as e:
        print(f"✗ 实盘模拟器失败: {e}")
        import traceback; traceback.print_exc()
        return False


def test_timestamp_alignment():
    print("\n" + "=" * 50)
    print("测试时间戳对齐...")
    print("=" * 50)
    try:
        engine = BacktestEngine(initial_cash=100000, commission=0.001, slippage=0.001)
        data = _make_sample_data(500)
        metrics = engine.run_backtest("双均线策略", data, {"fast_period": 5, "slow_period": 20})
        trades = metrics['trades']
        if trades:
            print(f"✓ 交易记录包含时间戳")
            for i, trade in enumerate(trades[:3]):
                if 'timestamp' in trade:
                    print(f"  交易{i+1}: {trade['timestamp']} - {trade['type']} @ ¥{trade['price']:.2f}")
        aligned_trades = BacktestVisualizer._align_trades_with_data(data, trades)
        print(f"✓ 时间戳对齐成功")
        print(f"  原始交易数: {len(trades)}, 对齐后交易数: {len(aligned_trades)}")
        return True
    except Exception as e:
        print(f"✗ 时间戳对齐测试失败: {e}")
        import traceback; traceback.print_exc()
        return False


if __name__ == "__main__":
    print("股票技术指标回测平台 - 系统测试（v3 新增功能）\n")
    
    results = []
    results.append(("回测引擎（含滑点）", test_backtest()))
    results.append(("贝叶斯优化", test_bayesian_optimization()))
    results.append(("时间戳对齐", test_timestamp_alignment()))
    results.append(("过拟合检测", test_overfit_detection()))
    results.append(("多周期联合回测", test_multi_timeframe()))
    results.append(("实盘模拟器", test_live_simulator()))
    
    print("\n" + "=" * 50)
    print("测试结果汇总")
    print("=" * 50)
    for name, result in results:
        status = "✓ 通过" if result else "✗ 失败"
        print(f"  {name}: {status}")
    
    all_passed = all(r[1] for r in results)
    print("\n" + ("✓ 所有测试通过!" if all_passed else "✗ 部分测试失败"))
