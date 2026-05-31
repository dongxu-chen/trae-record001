import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import sys

from pattern_recognition import PatternRecognizer
from backtest_engine import BacktestEngine, SlippageModel
from visualization import ChartVisualizer
from pattern_combo import (
    PatternComboDetector, PatternAlertSystem,
    PatternSuccessRateTracker, COMBO_RULES
)


def generate_test_data(days=200):
    dates = pd.date_range(end=datetime.now(), periods=days, freq='D')
    
    np.random.seed(42)
    
    base_price = 100
    returns = np.random.normal(0.001, 0.02, days)
    
    prices = base_price * (1 + returns).cumprod()
    
    opens = prices * (1 + np.random.normal(0, 0.005, days))
    highs = np.maximum(opens, prices) * (1 + np.abs(np.random.normal(0, 0.01, days)))
    lows = np.minimum(opens, prices) * (1 - np.abs(np.random.normal(0, 0.01, days)))
    closes = prices
    volumes = np.random.randint(1000000, 10000000, days)
    
    df = pd.DataFrame({
        'Open': opens,
        'High': highs,
        'Low': lows,
        'Close': closes,
        'Volume': volumes
    }, index=dates)
    
    return df


def test_pattern_recognition():
    print("测试1: 形态识别 (含动态阈值)...")
    df = generate_test_data(200)
    
    recognizer = PatternRecognizer(df, vol_lookback=20)
    patterns = recognizer.detect_all_patterns()
    
    print(f"  识别到 {len(patterns)} 个形态")
    for p in patterns[:3]:
        vf = p['details'].get('vol_factor', 1.0)
        print(f"  - {p['pattern']}: {p['date'].strftime('%Y-%m-%d')}, "
              f"预测: {p['prediction']}, 置信度: {p['confidence']:.1%}, "
              f"波动率因子: {vf:.2f}x")
    
    return patterns, df


def test_combo_detection(patterns, df):
    print("\n测试2: 组合形态识别...")
    
    print(f"  已注册 {len(COMBO_RULES)} 条组合规则:")
    for name, rule in COMBO_RULES.items():
        p_names = ' + '.join(rule['patterns'])
        print(f"    {rule['description']}: {p_names} (增强 {rule['boost']}x)")
    
    combo_detector = PatternComboDetector(patterns, df)
    combos = combo_detector.detect_combos()
    
    print(f"\n  识别到 {len(combos)} 个组合形态:")
    for combo in combos:
        pattern_names = ' + '.join([p['pattern'] for p in combo.patterns])
        print(f"    ⚡ {pattern_names}")
        print(f"      方向: {combo.direction.value}, 强度: {combo.strength:.1%}, "
              f"增强: {combo.boost_factor:.1f}x")
        print(f"      日期: {combo.start_date.strftime('%Y-%m-%d')} ~ "
              f"{combo.end_date.strftime('%Y-%m-%d')}")
    
    enhanced = combo_detector.get_enhanced_patterns()
    combo_count = sum(1 for p in enhanced if p.get('is_combo', False))
    single_count = len(enhanced) - combo_count
    print(f"\n  增强后信号: {len(enhanced)} 个 (单一: {single_count}, 组合: {combo_count})")
    
    return combos, enhanced


def test_alert_system(enhanced_patterns, df):
    print("\n测试3: 形态预警系统...")
    
    alert_system = PatternAlertSystem(
        min_confidence=0.5,
        combo_only=False,
        alert_cooldown=3
    )
    
    alerts = alert_system.generate_alerts(enhanced_patterns, df)
    summary = alert_system.get_alert_summary(alerts)
    
    print(f"  生成 {len(alerts)} 条预警:")
    print(f"    总预警: {summary['total_alerts']}")
    print(f"    看涨: {summary['bullish_alerts']}")
    print(f"    看跌: {summary['bearish_alerts']}")
    print(f"    组合: {summary['combo_alerts']}")
    print(f"    单一: {summary['single_alerts']}")
    print(f"    平均置信度: {summary['avg_confidence']:.1%}")
    
    for alert in alerts[:5]:
        icon = "🟢" if alert.direction.value == "bullish" else "🔴"
        combo_icon = "⚡" if alert.is_combo else "📌"
        print(f"    {icon} {combo_icon} {alert.pattern_name} | "
              f"{alert.date.strftime('%Y-%m-%d')} | "
              f"置信度: {alert.confidence:.1%}")
    
    return alerts


def test_success_rate(patterns, df, combos):
    print("\n测试4: 历史成功率统计...")
    
    tracker = PatternSuccessRateTracker(df, forward_period=10, min_samples=2)
    
    success_rates = tracker.calculate_success_rates(patterns)
    print(f"  各形态历史胜率:")
    for _, row in success_rates.iterrows():
        sr = row['success_rate']
        sr_str = f"{sr:.1%}" if pd.notna(sr) else "样本不足"
        ar = row['avg_return']
        ar_str = f"{ar:.2%}" if pd.notna(ar) else "N/A"
        print(f"    {row['pattern']}: 胜率 {sr_str}, "
              f"平均收益 {ar_str}, 样本 {int(row['total'])}")
    
    rolling = tracker.calculate_rolling_success_rate(patterns)
    if not rolling.empty:
        print(f"\n  滚动成功率: {len(rolling)} 条记录")
        latest = rolling.iloc[-1]
        print(f"    最新滚动胜率: {latest['rolling_success_rate']:.1%}")
        print(f"    最新滚动收益: {latest['rolling_avg_return']:.2%}")
    
    combo_success = tracker.calculate_combo_success_rate(patterns, combos)
    if not combo_success.empty:
        print(f"\n  组合形态成功率:")
        for _, row in combo_success.iterrows():
            sr = row['success_rate']
            sr_str = f"{sr:.1%}" if pd.notna(sr) else "N/A"
            print(f"    {row['combo']}: 胜率 {sr_str}, 样本 {int(row['total'])}")
    
    return success_rates


def test_visualization_new(patterns, df, enhanced, alerts, success_rates):
    print("\n测试5: 新增可视化图表...")
    
    visualizer = ChartVisualizer(df)
    
    fig = visualizer.create_candlestick_chart(enhanced)
    print("  K线图(含组合标记)创建成功")
    
    fig = visualizer.create_success_rate_chart(success_rates)
    print("  成功率图表创建成功")
    
    rolling_tracker = PatternSuccessRateTracker(df, forward_period=10)
    rolling_df = rolling_tracker.calculate_rolling_success_rate(patterns)
    if not rolling_df.empty:
        fig = visualizer.create_rolling_success_chart(rolling_df)
        print("  滚动成功率图表创建成功")
    
    if alerts:
        fig = visualizer.create_alert_panel(alerts)
        print("  预警面板图表创建成功")
    
    return True


def test_backtest_with_slippage(patterns, df):
    print("\n测试6: 含滑点的回测...")
    
    slippage_model = SlippageModel(
        fixed_slippage=0.01,
        percentage_slippage=0.001,
        commission_rate=0.0003,
        min_commission=5.0
    )
    
    engine = BacktestEngine(
        df=df,
        initial_capital=100000,
        position_size=0.1,
        stop_loss_pct=0.02,
        take_profit_pct=0.04,
        hold_period=10,
        slippage_model=slippage_model
    )
    
    result = engine.run_backtest(patterns)
    
    print(f"  总收益率: {result.total_return:.1%}")
    print(f"  年化收益率: {result.annual_return:.1%}")
    print(f"  最大回撤: {result.max_drawdown:.1%}")
    print(f"  夏普比率: {result.sharpe_ratio:.2f}")
    print(f"  总交易次数: {result.total_trades}")
    print(f"  胜率: {result.win_rate:.1%}")
    print(f"  总滑点成本: ¥{result.total_slippage:.2f}")
    print(f"  总佣金成本: ¥{result.total_commission:.2f}")
    print(f"  总交易成本: ¥{result.total_trading_cost:.2f}")
    
    return result


def main():
    print("=" * 70)
    print("股票K线形态识别系统 - 全功能测试")
    print("=" * 70)
    
    tests = [
        ("形态识别", lambda: test_pattern_recognition()),
    ]
    
    try:
        patterns, df = test_pattern_recognition()
    except Exception as e:
        print(f"形态识别测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    try:
        combos, enhanced = test_combo_detection(patterns, df)
    except Exception as e:
        print(f"组合识别测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    try:
        alerts = test_alert_system(enhanced, df)
    except Exception as e:
        print(f"预警系统测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    try:
        success_rates = test_success_rate(patterns, df, combos)
    except Exception as e:
        print(f"成功率统计测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    try:
        test_visualization_new(patterns, df, enhanced, alerts, success_rates)
    except Exception as e:
        print(f"可视化测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    try:
        test_backtest_with_slippage(patterns, df)
    except Exception as e:
        print(f"回测测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    print("\n" + "=" * 70)
    print("所有功能测试通过! ✅")
    print("=" * 70)
    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
