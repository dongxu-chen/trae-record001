import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
import time
import warnings
warnings.filterwarnings('ignore')

st.set_page_config(
    page_title="股票技术指标回测平台",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

from backtest_engine import BacktestEngine
from parameter_optimizer import ParameterOptimizer
from visualization import BacktestVisualizer
from overfit_detector import OverfitDetector
from multi_timeframe import MultiTimeframeEngine
from live_simulator import LiveSimulator

STRATEGY_PARAMS = {
    '双均线策略': {
        'fast_period': {'label': '快速均线周期', 'default': 5, 'min': 2, 'max': 50},
        'slow_period': {'label': '慢速均线周期', 'default': 20, 'min': 10, 'max': 100},
    },
    'RSI策略': {
        'rsi_period': {'label': 'RSI周期', 'default': 14, 'min': 7, 'max': 30},
        'rsi_overbought': {'label': '超买阈值', 'default': 70, 'min': 50, 'max': 90},
        'rsi_oversold': {'label': '超卖阈值', 'default': 30, 'min': 10, 'max': 50},
    },
    'MACD策略': {
        'macd_fast': {'label': '快线周期', 'default': 12, 'min': 5, 'max': 20},
        'macd_slow': {'label': '慢线周期', 'default': 26, 'min': 15, 'max': 40},
        'macd_signal': {'label': '信号线周期', 'default': 9, 'min': 3, 'max': 20},
    },
    '布林带策略': {
        'bb_period': {'label': '周期', 'default': 20, 'min': 10, 'max': 50},
        'bb_dev': {'label': '标准差倍数', 'default': 2.0, 'min': 1.0, 'max': 4.0},
    },
}

OPTIMIZE_METRICS = [
    ('夏普比率', 'sharpe_ratio'),
    ('总收益率', 'total_return'),
    ('胜率', 'win_rate'),
    ('盈亏比', 'profit_factor'),
    ('最大回撤', 'max_drawdown'),
]

def init_session():
    defaults = {
        'data': None, 'metrics': None, 'strategy_params': {},
        'optimization_results': None, 'strategy_name': None,
        'overfit_results': None, 'multitf_results': None,
        'live_sim': None, 'live_log': [],
    }
    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val

def sidebar_config():
    with st.sidebar:
        st.header("⚙️ 回测设置")
        st.subheader("股票数据")
        ticker = st.text_input("股票代码", value="000001.SS")
        col1, col2 = st.columns(2)
        with col1:
            start_date = st.date_input("开始日期", value=datetime.now() - timedelta(days=365*3))
        with col2:
            end_date = st.date_input("结束日期", value=datetime.now())
        
        st.subheader("回测参数")
        initial_cash = st.number_input("初始资金 (元)", value=100000.0, min_value=1000.0, step=10000.0)
        col3, col4 = st.columns(2)
        with col3:
            commission = st.number_input("手续费率 (%)", value=0.1, min_value=0.0, max_value=1.0, step=0.05) / 100
        with col4:
            slippage = st.number_input("滑点 (%)", value=0.1, min_value=0.0, max_value=1.0, step=0.05) / 100
        
        st.subheader("策略选择")
        strategy_name = st.selectbox("选择策略", list(STRATEGY_PARAMS.keys()))
        st.subheader("策略参数")
        params = {}
        for param_name, param_config in STRATEGY_PARAMS[strategy_name].items():
            if isinstance(param_config['default'], int):
                params[param_name] = st.slider(param_config['label'], min_value=param_config['min'], max_value=param_config['max'], value=param_config['default'])
            else:
                params[param_name] = st.slider(param_config['label'], min_value=float(param_config['min']), max_value=float(param_config['max']), value=float(param_config['default']), step=0.1)
        st.session_state.strategy_params = params
        
        st.subheader("基准对比")
        benchmark_ticker = st.text_input("基准指数", value="000300.SS")
        enable_benchmark = st.checkbox("启用基准对比", value=True)
        
        st.markdown("---")
        if st.button("🚀 运行回测", type="primary", use_container_width=True):
            with st.spinner("正在加载数据并运行回测..."):
                try:
                    engine = BacktestEngine(initial_cash, commission, slippage)
                    data = engine.load_data(ticker, start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d"))
                    st.session_state.data = data
                    metrics = engine.run_backtest(strategy_name, data, params)
                    st.session_state.metrics = metrics
                    st.session_state.strategy_name = strategy_name
                    st.session_state.initial_cash = initial_cash
                    if enable_benchmark:
                        try:
                            bench_engine = BacktestEngine(initial_cash, commission, slippage)
                            bd = bench_engine.load_data(benchmark_ticker, start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d"))
                            st.session_state.benchmark_data = bd['close']
                        except:
                            st.warning("无法加载基准数据")
                    st.success("回测完成！")
                except Exception as e:
                    st.error(f"回测失败: {str(e)}")
        
        st.markdown("---")
        with st.expander("🔧 参数优化"):
            optimize_method = st.radio("优化方法", ["贝叶斯优化", "网格搜索", "遗传算法"])
            optimize_by = st.selectbox("优化目标", [m[0] for m in OPTIMIZE_METRICS])
            optimize_by_key = [m[1] for m in OPTIMIZE_METRICS if m[0] == optimize_by][0]
            if optimize_method == "贝叶斯优化":
                n_calls = st.slider("迭代次数", min_value=20, max_value=100, value=50)
                base_est = st.selectbox("基模型", ["高斯过程 (GP)", "随机森林"])
                base_est_key = 'gp' if "高斯" in base_est else 'rf'
            elif optimize_method == "遗传算法":
                pop_size = st.slider("种群大小", min_value=20, max_value=50, value=30)
                n_gen = st.slider("迭代代数", min_value=5, max_value=15, value=8)
                mut_rate = st.slider("变异率", min_value=0.1, max_value=0.5, value=0.2)
            if st.button("开始优化", use_container_width=True):
                if st.session_state.data is None:
                    st.warning("请先运行回测加载数据")
                else:
                    pbar = st.progress(0)
                    stxt = st.empty()
                    def pcb(current, total):
                        pbar.progress(current / total)
                        stxt.text(f"优化进度: {current}/{total}")
                    with st.spinner("正在进行参数优化..."):
                        try:
                            opt = ParameterOptimizer(initial_cash, commission, slippage)
                            if optimize_method == "贝叶斯优化":
                                res = opt.bayesian_optimization(strategy_name, st.session_state.data, optimize_by=optimize_by_key, n_calls=n_calls, base_estimator=base_est_key, progress_callback=pcb)
                            elif optimize_method == "网格搜索":
                                res = opt.grid_search(strategy_name, st.session_state.data, optimize_by=optimize_by_key, progress_callback=pcb)
                            else:
                                res = opt.genetic_algorithm(strategy_name, st.session_state.data, optimize_by=optimize_by_key, population_size=pop_size, generations=n_gen, mutation_rate=mut_rate, progress_callback=pcb)
                            st.session_state.optimization_results = res
                            st.session_state.optimize_by = optimize_by
                            st.success("优化完成！")
                        except Exception as e:
                            st.error(f"优化失败: {str(e)}")
            if st.session_state.optimization_results is not None:
                if st.button("应用最佳参数", use_container_width=True):
                    bp = st.session_state.optimization_results['best_params']
                    with st.spinner("正在用最佳参数重新回测..."):
                        engine = BacktestEngine(initial_cash, commission, slippage)
                        m = engine.run_backtest(strategy_name, st.session_state.data, bp)
                        st.session_state.metrics = m
                        st.session_state.strategy_params = bp
                        st.success("回测完成！")
    
    return ticker, initial_cash, commission, slippage, strategy_name, params

def display_overfit_tab(data, strategy_name, params, initial_cash, commission, slippage):
    st.subheader("🛡️ 过拟合检测")
    detector = OverfitDetector(initial_cash, commission, slippage)
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🔍 样本内外测试", key="oos_test"):
            with st.spinner("正在运行样本内外测试..."):
                try:
                    result = detector.in_sample_out_sample_test(strategy_name, data, params)
                    st.session_state.overfit_results = result
                except Exception as e:
                    st.error(f"测试失败: {str(e)}")
    with col2:
        if st.button("📊 滚动窗口回测", key="rw_test"):
            with st.spinner("正在运行滚动窗口回测..."):
                try:
                    result = detector.rolling_window_backtest(strategy_name, data, params)
                    if st.session_state.overfit_results is None:
                        st.session_state.overfit_results = {}
                    st.session_state.overfit_results['rolling'] = result
                except Exception as e:
                    st.error(f"测试失败: {str(e)}")
    
    of = st.session_state.overfit_results
    if of:
        if 'is_overfit' in of:
            severity = of['overfit_severity']
            color = {'none': '🟢', 'mild': '🟡', 'moderate': '🟠', 'severe': '🔴'}.get(severity, '⚪')
            st.markdown(f"### 过拟合检测结果: {color} {severity.upper()}")
            
            c1, c2, c3 = st.columns(3)
            with c1:
                st.metric("样本内收益率", f"{of['in_sample']['total_return']:.2f}%")
            with c2:
                st.metric("样本外收益率", f"{of['out_sample']['total_return']:.2f}%")
            with c3:
                st.metric("收益衰减", f"{of['return_degradation']:.1f}%", delta=f"{'过拟合' if of['is_overfit'] else '正常'}")
            
            c4, c5, c6 = st.columns(3)
            with c4:
                st.metric("样本内夏普", f"{of['in_sample']['sharpe_ratio']:.2f}")
            with c5:
                st.metric("样本外夏普", f"{of['out_sample']['sharpe_ratio']:.2f}")
            with c6:
                st.metric("夏普衰减", f"{of['sharpe_degradation']:.2f}")
            
            st.info(f"**样本内期间**: {of['in_sample_period'][0].date()} ~ {of['in_sample_period'][1].date()}")
            st.info(f"**样本外期间**: {of['out_sample_period'][0].date()} ~ {of['out_sample_period'][1].date()}")
        
        if 'rolling' in of:
            rw = of['rolling']
            st.markdown("### 滚动窗口回测结果")
            c1, c2, c3, c4 = st.columns(4)
            with c1:
                st.metric("稳定性评分", f"{rw['stability_score']:.1f}/100")
            with c2:
                st.metric("平均收益率", f"{rw['return_mean']:.2f}%")
            with c3:
                st.metric("收益率标准差", f"{rw['return_std']:.2f}%")
            with c4:
                st.metric("正收益窗口比", f"{rw['positive_ratio']*100:.0f}%")
            
            window_returns = [w['total_return'] for w in rw['window_results']]
            window_starts = [w['window_start'] for w in rw['window_results']]
            
            fig = go.Figure()
            fig.add_trace(go.Bar(
                x=window_starts,
                y=window_returns,
                marker_color=['#2ecc71' if r > 0 else '#e74c3c' for r in window_returns],
                name='窗口收益率'
            ))
            fig.add_hline(y=rw['return_mean'], line_dash="dash", line_color="blue", annotation_text=f"均值: {rw['return_mean']:.2f}%")
            fig.update_layout(title='滚动窗口收益率', xaxis_title='窗口起始日期', yaxis_title='收益率 (%)', template='plotly_white', height=400)
            st.plotly_chart(fig, use_container_width=True)

def display_multitf_tab(data, strategy_name, params, initial_cash, commission, slippage):
    st.subheader("🔄 多周期联合回测")
    
    tf_options = st.multiselect("选择时间周期", ['5m', '15m', '30m', '1h', '1d', '1w'], default=['1d', '1h'], key="mtf_select")
    
    if st.button("运行多周期回测", key="mtf_run"):
        with st.spinner("正在运行多周期回测..."):
            try:
                mtf = MultiTimeframeEngine(initial_cash, commission, slippage)
                result = mtf.multi_timeframe_backtest(strategy_name, data, tf_options, params)
                st.session_state.multitf_results = result
                st.success("多周期回测完成！")
            except Exception as e:
                st.error(f"多周期回测失败: {str(e)}")
    
    mr = st.session_state.multitf_results
    if mr:
        st.markdown("### 各周期回测对比")
        comparison_df = mr.get('comparison_df', None)
        if comparison_df is None:
            comparison_df = pd.DataFrame([{
                'timeframe': tf,
                'total_return': r['metrics']['total_return'],
                'sharpe_ratio': r['metrics']['sharpe_ratio'],
                'max_drawdown': r['metrics']['max_drawdown'],
                'win_rate': r['metrics']['win_rate'],
                'total_trades': r['metrics']['total_trades'],
            } for tf, r in mr['timeframe_results'].items()])
        st.dataframe(comparison_df.style.format({
            'total_return': '{:.2f}%', 'sharpe_ratio': '{:.2f}',
            'max_drawdown': '{:.2f}%', 'win_rate': '{:.1f}%'
        }), use_container_width=True, hide_index=True)
        
        resonance = mr.get('resonance_analysis', {})
        if resonance:
            st.markdown("### 周期共振分析")
            c1, c2, c3, c4 = st.columns(4)
            with c1:
                st.metric("共振信号数", resonance.get('resonance_count', 0))
            with c2:
                st.metric("共振比例", f"{resonance.get('resonance_ratio', 0)*100:.1f}%")
            with c3:
                st.metric("买入信号", resonance.get('buy_signals', 0))
            with c4:
                st.metric("卖出信号", resonance.get('sell_signals', 0))
            
            if resonance.get('signals'):
                res_df = pd.DataFrame(resonance['signals'])
                st.dataframe(res_df, use_container_width=True, hide_index=True)

def display_live_tab(ticker, strategy_name, params, initial_cash, commission, slippage):
    st.subheader("📡 实盘模拟交易")
    
    if st.session_state.live_sim is None:
        st.session_state.live_sim = LiveSimulator(initial_cash, commission, slippage, strategy_name, params)
    
    sim = st.session_state.live_sim
    
    c1, c2 = st.columns(2)
    with c1:
        sim_mode = st.radio("模式", ["模拟行情", "实时行情(Yahoo)"], key="live_mode")
        tick_interval = st.slider("刷新间隔(秒)", min_value=1, max_value=30, value=5)
    with c2:
        stop_loss_pct = st.number_input("止损 (%)", value=5.0, min_value=0.0) / 100
        take_profit_pct = st.number_input("止盈 (%)", value=10.0, min_value=0.0) / 100
    
    col_start, col_stop, col_reset = st.columns(3)
    
    with col_start:
        if st.button("▶️ 开始模拟", key="live_start"):
            sim.subscribe(ticker)
            mode = 'live' if "实时" in sim_mode else 'simulated'
            sim.start_simulation(ticker, mode=mode, interval_seconds=tick_interval)
            st.success("模拟已启动！")
    
    with col_stop:
        if st.button("⏹️ 停止模拟", key="live_stop"):
            sim.stop_simulation()
            sim.save_state()
            st.info("模拟已停止，状态已保存")
    
    with col_reset:
        if st.button("🔄 重置", key="live_reset"):
            sim.stop_simulation()
            st.session_state.live_sim = LiveSimulator(initial_cash, commission, slippage, strategy_name, params)
            sim = st.session_state.live_sim
            st.info("模拟已重置")
    
    if st.button("📤 手动买入", key="manual_buy"):
        price = sim.get_current_price(ticker)
        if price:
            qty = (sim.cash * 0.95) / price
            sim.place_order(ticker, 'buy', qty, 'market', stop_price=price*(1-stop_loss_pct) if stop_loss_pct > 0 else None)
            st.success(f"买入 {qty:.0f} 股 @ ¥{price:.2f}")
    
    if st.button("📥 手动卖出", key="manual_sell"):
        if ticker in sim.positions:
            pos = sim.positions[ticker]
            sim.place_order(ticker, 'sell', pos.size, 'market')
            st.success(f"卖出 {pos.size:.0f} 股")
    
    summary = sim.get_portfolio_summary()
    
    st.markdown("### 📊 账户概览")
    mc1, mc2, mc3, mc4 = st.columns(4)
    with mc1:
        st.metric("总资产", f"¥{summary['total_value']:,.2f}")
    with mc2:
        st.metric("现金", f"¥{summary['cash']:,.2f}")
    with mc3:
        delta_str = f"{summary['return_pct']:+.2f}%"
        st.metric("总收益率", delta_str)
    with mc4:
        st.metric("持仓数", summary['num_positions'])
    
    if summary['positions']:
        st.markdown("### 📋 当前持仓")
        pos_df = pd.DataFrame(summary['positions'])
        st.dataframe(pos_df, use_container_width=True, hide_index=True)
    
    stats = sim.get_trade_statistics()
    if stats['total_trades'] > 0:
        st.markdown("### 📈 交易统计")
        sc1, sc2, sc3, sc4 = st.columns(4)
        with sc1:
            st.metric("总交易", stats['total_trades'])
        with sc2:
            st.metric("胜率", f"{stats['win_rate']:.1f}%")
        with sc3:
            st.metric("总盈亏", f"¥{stats['total_pnl']:,.2f}")
        with sc4:
            st.metric("盈亏比", f"{stats['profit_factor']:.2f}")
    
    if sim.trade_history:
        st.markdown("### 📜 交易记录")
        th_df = pd.DataFrame(sim.trade_history)
        st.dataframe(th_df, use_container_width=True, hide_index=True)
    
    if sim.equity_history:
        eh_df = pd.DataFrame(sim.equity_history[-200:])
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=list(range(len(eh_df))), y=eh_df['total_value'], name='总资产', line=dict(color='#1f77b4', width=2)))
        fig.add_trace(go.Scatter(x=list(range(len(eh_df))), y=eh_df['cash'], name='现金', line=dict(color='#2ecc71', width=1, dash='dash')))
        fig.update_layout(title='实盘模拟资产曲线', xaxis_title='Tick', yaxis_title='金额 (¥)', template='plotly_white', height=350)
        st.plotly_chart(fig, use_container_width=True)

def main():
    st.title("📈 股票技术指标回测平台")
    st.markdown("---")
    init_session()
    ticker, initial_cash, commission, slippage, strategy_name, params = sidebar_config()
    
    if st.session_state.metrics is not None and st.session_state.data is not None:
        display_results(ticker, initial_cash, commission, slippage, strategy_name, params)
    else:
        display_welcome()

def display_welcome():
    st.info("👈 请在左侧配置回测参数，然后点击「运行回测」开始")
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.subheader("📊 策略回测")
        st.markdown("- 4种内置策略\n- 滑点+手续费\n- 贝叶斯优化")
    with c2:
        st.subheader("🛡️ 过拟合检测")
        st.markdown("- 滚动窗口回测\n- 样本内外对比\n- 稳定性评分")
    with c3:
        st.subheader("🔄 多周期回测")
        st.markdown("- 日线/小时线验证\n- 周期共振检测\n- 信号一致性分析")
    with c4:
        st.subheader("📡 实盘模拟")
        st.markdown("- 模拟/实时行情\n- 止损止盈\n- 持仓管理")

def display_results(ticker, initial_cash, commission, slippage, strategy_name, params):
    metrics = st.session_state.metrics
    data = st.session_state.data
    
    st.header("📊 回测结果")
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("最终资产", f"¥{metrics['final_value']:,.2f}", delta=f"{metrics['total_return']:+.2f}%")
    with c2:
        st.metric("年化收益率", f"{metrics['annual_return']:+.2f}%")
    with c3:
        st.metric("夏普比率", f"{metrics['sharpe_ratio']:.2f}")
    with c4:
        st.metric("最大回撤", f"{metrics['max_drawdown']:.2f}%", delta_color="inverse")
    
    c5, c6, c7, c8 = st.columns(4)
    with c5: st.metric("总交易次数", f"{metrics['total_trades']}")
    with c6: st.metric("胜率", f"{metrics['win_rate']:.1f}%")
    with c7: st.metric("盈亏比", f"{metrics['profit_factor']:.2f}")
    with c8: st.metric("盈利/亏损", f"{metrics['won_trades']}/{metrics['lost_trades']}")
    
    with st.expander("📋 交易成本详情"):
        cc1, cc2 = st.columns(2)
        with cc1: st.info(f"**总手续费**: ¥{metrics.get('total_commission', 0):,.2f}")
        with cc2: st.info(f"**平均滑点**: {metrics.get('avg_slippage', 0)*100:.4f}%")
    
    st.markdown("---")
    
    tabs = st.tabs([
        "📈 收益曲线", "💹 交易信号", "📉 回撤分析", "🔄 交易分析",
        "⚙️ 参数优化", "🛡️ 过拟合检测", "🔄 多周期回测", "📡 实盘模拟"
    ])
    
    with tabs[0]:
        st.subheader("资产净值曲线")
        bm = st.session_state.get('benchmark_data', None)
        fig = BacktestVisualizer.create_equity_curve(metrics, data, bm, initial_cash=st.session_state.get('initial_cash', 100000))
        st.plotly_chart(fig, use_container_width=True)
        st.subheader("月度收益热力图")
        st.plotly_chart(BacktestVisualizer.create_monthly_returns_heatmap(metrics, data), use_container_width=True)
    
    with tabs[1]:
        st.subheader("价格走势与交易信号")
        fig = BacktestVisualizer.create_price_with_signals(data.copy(), metrics['trades'], strategy_name, params)
        st.plotly_chart(fig, use_container_width=True)
        if metrics['trades']:
            tdf = pd.DataFrame(metrics['trades'])
            if 'timestamp' in tdf.columns:
                tdf = tdf.sort_values('timestamp')
                dcols = ['timestamp', 'type', 'price', 'size', 'commission', 'slippage', 'pnl']
            else:
                tdf = tdf.sort_values('date')
                dcols = ['date', 'type', 'price', 'size', 'commission', 'pnl']
            fmt = {'price': '{:.2f}', 'commission': '{:.2f}', 'slippage': '{:.4f}', 'pnl': '{:.2f}'}
            st.dataframe(tdf[dcols].style.format(fmt), use_container_width=True, hide_index=True)
    
    with tabs[2]:
        st.plotly_chart(BacktestVisualizer.create_drawdown_chart(metrics, data), use_container_width=True)
    
    with tabs[3]:
        st.plotly_chart(BacktestVisualizer.create_trade_analysis_chart(metrics['trades']), use_container_width=True)
        c1, c2 = st.columns(2)
        with c1: st.info(f"**平均盈利**: ¥{metrics['avg_win']:,.2f}")
        with c2: st.info(f"**平均亏损**: ¥{abs(metrics['avg_loss']):,.2f}")
    
    with tabs[4]:
        opt = st.session_state.optimization_results
        if opt:
            bp = opt['best_params']
            bm2 = opt['best_metrics']
            c1, c2 = st.columns(2)
            with c1:
                st.write("**最佳参数**")
                for k, v in bp.items(): st.info(f"{k}: {v}")
            with c2:
                st.write("**回测结果**")
                st.info(f"总收益率: {bm2['total_return']:.2f}%")
                st.info(f"夏普比率: {bm2['sharpe_ratio']:.2f}")
                st.info(f"最大回撤: {bm2['max_drawdown']:.2f}%")
        else:
            st.info("👈 请在左侧使用参数优化功能")
    
    with tabs[5]:
        display_overfit_tab(data, strategy_name, params, initial_cash, commission, slippage)
    
    with tabs[6]:
        display_multitf_tab(data, strategy_name, params, initial_cash, commission, slippage)
    
    with tabs[7]:
        display_live_tab(ticker, strategy_name, params, initial_cash, commission, slippage)

if __name__ == "__main__":
    main()
