import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime, timedelta
import time

from pattern_recognition import PatternRecognizer
from backtest_engine import BacktestEngine, SlippageModel
from visualization import ChartVisualizer
from pattern_combo import (
    PatternComboDetector, PatternAlertSystem, 
    PatternSuccessRateTracker, COMBO_RULES
)


st.set_page_config(
    page_title="股票K线形态识别系统",
    page_icon="📈",
    layout="wide"
)


st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        padding: 1rem 0;
    }
    .metric-card {
        background-color: #f8f9fa;
        border-radius: 10px;
        padding: 15px;
        box-shadow: 2px 2px 5px rgba(0,0,0,0.1);
    }
    .metric-value {
        font-size: 1.8rem;
        font-weight: bold;
    }
    .positive {
        color: #28a745;
    }
    .negative {
        color: #dc3545;
    }
    .stSpinner > div {
        border-color: #1f77b4 !important;
    }
</style>
""", unsafe_allow_html=True)


st.markdown('<div class="main-header">📈 股票K线形态识别系统</div>', unsafe_allow_html=True)


@st.cache_data(ttl=3600, show_spinner=False)
def load_data_cached(ticker, start_date, end_date, interval):
    try:
        df = yf.download(ticker, start=start_date, end=end_date, interval=interval)
        if df.empty:
            return None
        return df
    except Exception as e:
        return None


@st.cache_data(show_spinner=False)
def detect_patterns_cached(df_hash, params, vol_lookback=20):
    df = st.session_state.get('current_df')
    if df is None:
        return []
    
    recognizer = PatternRecognizer(df, vol_lookback=vol_lookback)
    patterns = recognizer.detect_all_patterns(params)
    return patterns


@st.cache_data(show_spinner=False)
def run_backtest_cached(df_hash, patterns, initial_capital, position_size, 
                        stop_loss_pct, take_profit_pct, hold_period,
                        fixed_slippage, percentage_slippage, commission_rate, min_commission):
    df = st.session_state.get('current_df')
    if df is None:
        return None
    
    slippage_model = SlippageModel(
        fixed_slippage=fixed_slippage,
        percentage_slippage=percentage_slippage,
        commission_rate=commission_rate,
        min_commission=min_commission
    )
    
    engine = BacktestEngine(
        df=df,
        initial_capital=initial_capital,
        position_size=position_size,
        stop_loss_pct=stop_loss_pct,
        take_profit_pct=take_profit_pct,
        hold_period=hold_period,
        slippage_model=slippage_model
    )
    
    result = engine.run_backtest(patterns)
    return result


pattern_name_map = {
    "Hammer (锤子线)": "hammer",
    "Hanging Man (上吊线)": "hanging_man",
    "Bullish Engulfing (看涨吞没)": "bullish_engulfing",
    "Bearish Engulfing (看跌吞没)": "bearish_engulfing",
    "Head & Shoulders (头肩顶)": "head_and_shoulders",
    "Inverse H&S (头肩底)": "inverse_head_and_shoulders",
    "Double Top (双顶)": "double_top",
    "Double Bottom (双底)": "double_bottom"
}

pattern_map = {
    'Hammer': 'hammer',
    'Hanging Man': 'hanging_man',
    'Bullish Engulfing': 'bullish_engulfing',
    'Bearish Engulfing': 'bearish_engulfing',
    'Head & Shoulders': 'head_and_shoulders',
    'Inverse H&S': 'inverse_head_and_shoulders',
    'Double Top': 'double_top',
    'Double Bottom': 'double_bottom'
}


with st.sidebar:
    st.header("📊 数据设置")
    
    with st.form("data_form"):
        ticker = st.text_input("股票代码", value="AAPL", help="例如: AAPL, GOOGL, 600519.SS")
        
        col1, col2 = st.columns(2)
        with col1:
            start_date = st.date_input("开始日期", value=datetime.now() - timedelta(days=365))
        with col2:
            end_date = st.date_input("结束日期", value=datetime.now())
        
        interval = st.selectbox(
            "时间周期",
            options=["1d", "1wk", "1mo", "1h", "30m"],
            format_func=lambda x: {
                "1d": "日线",
                "1wk": "周线",
                "1mo": "月线",
                "1h": "1小时",
                "30m": "30分钟"
            }[x]
        )
        
        vol_lookback = st.slider("波动率回看周期", 5, 60, 20, 5, 
                               help="用于计算动态阈值的ATR周期")
        
        load_data_btn = st.form_submit_button("📥 加载数据", use_container_width=True)
    
    if load_data_btn:
        with st.spinner("正在加载数据..."):
            df = load_data_cached(ticker, start_date, end_date, interval)
            if df is not None and len(df) > 0:
                st.session_state['current_df'] = df
                st.session_state['ticker'] = ticker
                st.session_state['data_loaded'] = True
                st.success(f"✅ 成功加载 {len(df)} 条数据")
            else:
                st.error("❌ 无法加载数据，请检查股票代码和日期设置")
                st.session_state['data_loaded'] = False
    
    if st.session_state.get('data_loaded', False):
        st.divider()
        st.header("🔍 形态选择与参数")
        
        with st.form("pattern_form"):
            patterns_to_detect = st.multiselect(
                "选择要识别的形态",
                options=[
                    "Hammer (锤子线)",
                    "Hanging Man (上吊线)",
                    "Bullish Engulfing (看涨吞没)",
                    "Bearish Engulfing (看跌吞没)",
                    "Head & Shoulders (头肩顶)",
                    "Inverse H&S (头肩底)",
                    "Double Top (双顶)",
                    "Double Bottom (双底)"
                ],
                default=[
                    "Hammer (锤子线)",
                    "Bullish Engulfing (看涨吞没)",
                    "Bearish Engulfing (看跌吞没)"
                ]
            )
            
            with st.expander("🔨 锤子线/上吊线参数"):
                hammer_body_ratio = st.slider("实体比例阈值", 0.1, 0.5, 0.3, 0.05, key="hammer_body")
                hammer_lower_shadow = st.slider("下影线倍数", 1.0, 4.0, 2.0, 0.2, key="hammer_shadow")
                hammer_upper_shadow = st.slider("上影线比例", 0.1, 1.0, 0.5, 0.1, key="hammer_upper")
            
            with st.expander("🔥 吞没形态参数"):
                engulfing_ratio = st.slider("实体倍数阈值", 1.0, 3.0, 1.5, 0.1, key="engulfing")
            
            with st.expander("👤 头肩形态参数"):
                hs_lookback = st.slider("回看周期", 15, 60, 30, 5, key="hs_lookback")
                hs_similarity = st.slider("肩部相似度", 0.7, 0.95, 0.85, 0.05, key="hs_similarity")
                hs_neckline = st.slider("颈线突破阈值", 0.01, 0.05, 0.03, 0.005, key="hs_neckline", format="%.1f%%")
            
            with st.expander("🔝🔚 双顶/双底参数"):
                dt_lookback = st.slider("回看周期", 10, 40, 20, 5, key="dt_lookback")
                dt_similarity = st.slider("峰/谷相似度", 0.85, 0.99, 0.95, 0.01, key="dt_similarity")
                dt_min_distance = st.slider("最小间距", 2, 10, 3, 1, key="dt_distance")
            
            with st.expander("⚡ 组合形态参数"):
                enable_combo = st.checkbox("启用组合形态识别", value=True, key="enable_combo")
                combo_min_confidence = st.slider("最低置信度", 0.3, 0.9, 0.5, 0.05, key="combo_min_conf")
            
            with st.expander("🔔 预警设置"):
                enable_alerts = st.checkbox("启用形态预警", value=True, key="enable_alerts")
                alert_min_confidence = st.slider("预警最低置信度", 0.3, 0.9, 0.5, 0.05, key="alert_min_conf")
                alert_combo_only = st.checkbox("仅组合形态预警", value=False, key="alert_combo_only")
            
            with st.expander("📊 成功率统计参数"):
                forward_period = st.slider("前瞻验证周期", 3, 30, 10, 1, 
                                          help="形态出现后多少根K线验证预测",
                                          key="forward_period")
                min_samples = st.slider("最少样本数", 2, 10, 3, 1, key="min_samples")
            
            analyze_btn = st.form_submit_button("🔍 识别形态", use_container_width=True, type="primary")
        
        if analyze_btn and st.session_state.get('data_loaded', False):
            params = {
                'hammer': {
                    'body_ratio': hammer_body_ratio,
                    'lower_shadow_ratio': hammer_lower_shadow,
                    'upper_shadow_ratio': hammer_upper_shadow
                },
                'hanging_man': {
                    'body_ratio': hammer_body_ratio,
                    'lower_shadow_ratio': hammer_lower_shadow,
                    'upper_shadow_ratio': hammer_upper_shadow
                },
                'bullish_engulfing': {'min_body_ratio': engulfing_ratio},
                'bearish_engulfing': {'min_body_ratio': engulfing_ratio},
                'head_and_shoulders': {
                    'lookback': hs_lookback,
                    'shoulder_similarity': hs_similarity,
                    'neckline_threshold': hs_neckline
                },
                'inverse_head_and_shoulders': {
                    'lookback': hs_lookback,
                    'shoulder_similarity': hs_similarity,
                    'neckline_threshold': hs_neckline
                },
                'double_top': {
                    'lookback': dt_lookback,
                    'peak_similarity': dt_similarity,
                    'min_distance': dt_min_distance
                },
                'double_bottom': {
                    'lookback': dt_lookback,
                    'trough_similarity': dt_similarity,
                    'min_distance': dt_min_distance
                }
            }
            
            df = st.session_state['current_df']
            df_hash = f"{len(df)}_{df.index[-1]}_{df['Close'].iloc[-1]:.2f}"
            
            with st.spinner("正在识别形态..."):
                all_patterns = detect_patterns_cached(df_hash, params, vol_lookback)
                
                selected_pattern_keys = [pattern_name_map[p] for p in patterns_to_detect]
                filtered_patterns = [
                    p for p in all_patterns 
                    if pattern_map.get(p['pattern'], p['pattern'].lower().replace(' ', '_')) in selected_pattern_keys
                ]
                
                enhanced_patterns = filtered_patterns
                combos = []
                alerts = []
                
                if enable_combo:
                    combo_detector = PatternComboDetector(filtered_patterns, df)
                    combos = combo_detector.detect_combos()
                    enhanced_patterns = combo_detector.get_enhanced_patterns()
                
                if enable_alerts:
                    alert_system = PatternAlertSystem(
                        min_confidence=alert_min_confidence,
                        combo_only=alert_combo_only
                    )
                    alerts = alert_system.generate_alerts(enhanced_patterns, df)
                    alert_summary = alert_system.get_alert_summary(alerts)
                else:
                    alert_summary = {
                        'total_alerts': 0, 'bullish_alerts': 0,
                        'bearish_alerts': 0, 'combo_alerts': 0,
                        'single_alerts': 0, 'avg_confidence': 0,
                        'latest_alert': None
                    }
                
                success_tracker = PatternSuccessRateTracker(
                    df, forward_period=forward_period, min_samples=min_samples
                )
                success_rates = success_tracker.calculate_success_rates(filtered_patterns)
                rolling_success = success_tracker.calculate_rolling_success_rate(filtered_patterns)
                combo_success = success_tracker.calculate_combo_success_rate(filtered_patterns, combos)
                
                st.session_state['patterns'] = filtered_patterns
                st.session_state['enhanced_patterns'] = enhanced_patterns
                st.session_state['combos'] = combos
                st.session_state['alerts'] = alerts
                st.session_state['alert_summary'] = alert_summary
                st.session_state['success_rates'] = success_rates
                st.session_state['rolling_success'] = rolling_success
                st.session_state['combo_success'] = combo_success
                st.session_state['params'] = params
                st.session_state['vol_lookback'] = vol_lookback
                st.session_state['patterns_detected'] = True
                
                combo_count = len(combos)
                alert_count = len(alerts)
                st.success(f"✅ 识别到 {len(filtered_patterns)} 个形态 | {combo_count} 个组合 | {alert_count} 条预警")
        
        if st.session_state.get('patterns_detected', False):
            st.divider()
            st.header("💹 回测设置")
            
            with st.form("backtest_form"):
                initial_capital = st.number_input("初始资金", 10000, 1000000, 100000, 10000)
                position_size = st.slider("单仓位比例", 0.05, 0.5, 0.1, 0.05, format="%.0f%%")
                stop_loss = st.slider("止损比例", 0.01, 0.1, 0.02, 0.01, format="%.0f%%")
                take_profit = st.slider("止盈比例", 0.02, 0.2, 0.04, 0.01, format="%.0f%%")
                hold_period = st.slider("最大持仓天数", 3, 30, 10, 1)
                
                st.subheader("💰 交易成本设置")
                col_s1, col_s2 = st.columns(2)
                with col_s1:
                    fixed_slippage = st.number_input("固定滑点(元)", 0.0, 1.0, 0.0, 0.01, 
                                                    help="每股固定滑点成本")
                with col_s2:
                    percentage_slippage = st.slider("百分比滑点", 0.0, 0.01, 0.001, 0.0005, 
                                                   format="%.2f%%",
                                                   help="按价格百分比计算的滑点")
                
                col_c1, col_c2 = st.columns(2)
                with col_c1:
                    commission_rate = st.slider("佣金率", 0.0, 0.005, 0.0003, 0.0001, 
                                               format="%.2f%%",
                                               help="按成交额比例计算的佣金")
                with col_c2:
                    min_commission = st.number_input("最低佣金(元)", 0.0, 50.0, 5.0, 1.0,
                                                    help="每笔交易最低佣金")
                
                run_backtest_btn = st.form_submit_button("📊 运行回测", use_container_width=True, type="primary")
            
            if run_backtest_btn and st.session_state.get('patterns_detected', False):
                df = st.session_state['current_df']
                patterns = st.session_state['patterns']
                df_hash = f"{len(df)}_{df.index[-1]}_{df['Close'].iloc[-1]:.2f}"
                patterns_hash = f"{len(patterns)}_{patterns[0]['index'] if patterns else 0}"
                
                with st.spinner("正在运行回测..."):
                    result = run_backtest_cached(
                        df_hash + patterns_hash,
                        patterns,
                        initial_capital,
                        position_size,
                        stop_loss,
                        take_profit,
                        hold_period,
                        fixed_slippage,
                        percentage_slippage,
                        commission_rate,
                        min_commission
                    )
                    
                    if result is not None:
                        st.session_state['backtest_result'] = result
                        st.session_state['backtest_done'] = True
                        st.success("✅ 回测完成")


if st.session_state.get('patterns_detected', False):
    df = st.session_state['current_df']
    patterns = st.session_state['patterns']
    enhanced_patterns = st.session_state.get('enhanced_patterns', patterns)
    combos = st.session_state.get('combos', [])
    alerts = st.session_state.get('alerts', [])
    alert_summary = st.session_state.get('alert_summary', {})
    success_rates = st.session_state.get('success_rates', pd.DataFrame())
    rolling_success = st.session_state.get('rolling_success', pd.DataFrame())
    combo_success = st.session_state.get('combo_success', pd.DataFrame())
    ticker = st.session_state.get('ticker', 'Unknown')
    visualizer = ChartVisualizer(df)
    
    tab_chart, tab_combo, tab_alerts, tab_success = st.tabs([
        "📊 K线图", "⚡ 组合形态", "🔔 预警中心", "📈 历史成功率"
    ])
    
    with tab_chart:
        st.subheader("K线图与形态标记")
        
        fig = visualizer.create_candlestick_chart(
            enhanced_patterns,
            title=f"{ticker} K线图 - {len(enhanced_patterns)} 个信号 (含 {len(combos)} 个组合)",
            show_volume=True
        )
        st.plotly_chart(fig, use_container_width=True)
        
        st.subheader("识别到的形态列表")
        
        if enhanced_patterns:
            pattern_df = pd.DataFrame([
                {
                    '形态名称': p['pattern'],
                    '类型': '看涨' if p['type'] == 'bullish' else '看跌',
                    '日期': p['date'],
                    '价格': f"{p['price']:.2f}",
                    '预测方向': '上涨' if p['prediction'] == 'up' else '下跌',
                    '置信度': f"{p['confidence']:.0%}",
                    '波动率因子': f"{p['details'].get('vol_factor', 1.0):.2f}x",
                    '组合': '⚡' if p.get('is_combo', False) else ''
                } for p in enhanced_patterns
            ])
            st.dataframe(pattern_df, use_container_width=True)
        else:
            st.info("在选定参数下未识别到任何形态，请尝试调整参数")
    
    with tab_combo:
        st.subheader("⚡ 组合形态识别")
        
        if combos:
            st.markdown(f"共识别到 **{len(combos)}** 个组合形态信号")
            
            combo_summary_cols = st.columns(min(len(combos), 4))
            for i, combo in enumerate(combos[:4]):
                col = combo_summary_cols[i]
                with col:
                    direction = '🟢 看涨' if combo.direction.value == 'bullish' else '🔴 看跌'
                    rule_info = COMBO_RULES.get(combo.combo_id, {})
                    desc = rule_info.get('description', combo.combo_id)
                    pattern_names = ' + '.join([p['pattern'] for p in combo.patterns])
                    
                    st.markdown(f"""
                    <div class="metric-card">
                        <div style="font-size:1.2rem;font-weight:bold;">{direction}</div>
                        <div style="font-size:0.9rem;color:#666;">{desc}</div>
                        <div style="font-size:0.85rem;margin-top:5px;">{pattern_names}</div>
                        <div style="font-size:1.4rem;font-weight:bold;margin-top:8px;"
                             class="{'positive' if combo.direction.value == 'bullish' else 'negative'}">
                            {combo.strength:.0%}
                        </div>
                        <div style="font-size:0.8rem;color:#888;">信号增强 {combo.boost_factor:.1f}x</div>
                        <div style="font-size:0.8rem;color:#888;">
                            {combo.start_date.strftime('%Y-%m-%d')} ~ {combo.end_date.strftime('%Y-%m-%d')}
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
            
            st.subheader("组合形态详情")
            combo_df = pd.DataFrame([
                {
                    '组合名称': COMBO_RULES.get(c.combo_id, {}).get('description', c.combo_id),
                    '方向': '看涨' if c.direction.value == 'bullish' else '看跌',
                    '包含形态': ' + '.join([p['pattern'] for p in c.patterns]),
                    '信号强度': f"{c.strength:.0%}",
                    '增强倍数': f"{c.boost_factor:.1f}x",
                    '起始日期': c.start_date.strftime('%Y-%m-%d'),
                    '结束日期': c.end_date.strftime('%Y-%m-%d'),
                    '价格': f"{c.price:.2f}"
                } for c in combos
            ])
            st.dataframe(combo_df, use_container_width=True)
            
            if not combo_success.empty:
                st.subheader("组合形态历史成功率")
                st.dataframe(combo_success.style.format({
                    'success_rate': '{:.1%}',
                    'avg_return': '{:.2%}'
                }), use_container_width=True)
        else:
            st.info("未识别到组合形态。组合形态需要多个单一形态在相邻K线中连续出现。")
            
            with st.expander("查看支持的组合形态规则"):
                rule_data = []
                for name, rule in COMBO_RULES.items():
                    rule_data.append({
                        '组合名称': rule['description'],
                        '包含形态': ' + '.join(rule['patterns']),
                        '方向': '看涨' if rule['direction'].value == 'bullish' else '看跌',
                        '信号增强': f"{rule['boost']:.1f}x",
                        '最大间距': f"{rule['max_gap']}根K线"
                    })
                st.dataframe(pd.DataFrame(rule_data), use_container_width=True)
    
    with tab_alerts:
        st.subheader("🔔 形态预警中心")
        
        summary_cols = st.columns(5)
        with summary_cols[0]:
            st.metric("总预警", alert_summary.get('total_alerts', 0))
        with summary_cols[1]:
            st.metric("看涨预警", alert_summary.get('bullish_alerts', 0))
        with summary_cols[2]:
            st.metric("看跌预警", alert_summary.get('bearish_alerts', 0))
        with summary_cols[3]:
            st.metric("组合预警", alert_summary.get('combo_alerts', 0))
        with summary_cols[4]:
            avg_conf = alert_summary.get('avg_confidence', 0)
            st.metric("平均置信度", f"{avg_conf:.0%}" if avg_conf else "N/A")
        
        if alerts:
            for alert in alerts:
                direction_icon = "🟢" if alert.direction.value == "bullish" else "🔴"
                combo_icon = "⚡" if alert.is_combo else "📌"
                prediction_text = '上涨' if alert.prediction == 'up' else '下跌'
                
                if alert.is_combo:
                    alert_type = st.success
                elif alert.direction.value == "bullish":
                    alert_type = st.info
                else:
                    alert_type = st.warning
                
                alert_type(
                    f"{direction_icon} {combo_icon} **{alert.pattern_name}** | "
                    f"{alert.date.strftime('%Y-%m-%d')} | "
                    f"价格: {alert.price:.2f} | "
                    f"预测: {prediction_text} | "
                    f"置信度: {alert.confidence:.0%}"
                )
                st.caption(alert.description)
            
            alert_fig = visualizer.create_alert_panel(alerts)
            st.plotly_chart(alert_fig, use_container_width=True)
        else:
            st.info("当前无预警。尝试降低预警最低置信度或识别更多形态。")
    
    with tab_success:
        st.subheader("📈 历史成功率统计")
        
        if not success_rates.empty:
            success_fig = visualizer.create_success_rate_chart(success_rates)
            st.plotly_chart(success_fig, use_container_width=True)
            
            st.subheader("各形态详细统计")
            display_df = success_rates.copy()
            display_df['success_rate'] = display_df['success_rate'].apply(
                lambda x: f"{x:.1%}" if pd.notna(x) else "样本不足"
            )
            display_df['avg_return'] = display_df['avg_return'].apply(
                lambda x: f"{x:.2%}" if pd.notna(x) else "N/A"
            )
            display_df['avg_success_return'] = display_df['avg_success_return'].apply(
                lambda x: f"{x:.2%}" if pd.notna(x) else "N/A"
            )
            display_df['avg_fail_return'] = display_df['avg_fail_return'].apply(
                lambda x: f"{x:.2%}" if pd.notna(x) else "N/A"
            )
            display_df['best_return'] = display_df['best_return'].apply(
                lambda x: f"{x:.2%}" if pd.notna(x) else "N/A"
            )
            display_df['worst_return'] = display_df['worst_return'].apply(
                lambda x: f"{x:.2%}" if pd.notna(x) else "N/A"
            )
            
            rename_map = {
                'pattern': '形态',
                'total': '样本数',
                'success': '成功次数',
                'fail': '失败次数',
                'success_rate': '历史胜率',
                'avg_return': '平均收益率',
                'avg_success_return': '平均成功收益',
                'avg_fail_return': '平均失败收益',
                'best_return': '最佳收益',
                'worst_return': '最差收益'
            }
            display_df = display_df.rename(columns=rename_map)
            st.dataframe(display_df, use_container_width=True)
            
            if not rolling_success.empty:
                st.subheader("滚动成功率趋势")
                rolling_fig = visualizer.create_rolling_success_chart(rolling_success)
                st.plotly_chart(rolling_fig, use_container_width=True)
        else:
            st.info("数据不足，无法计算历史成功率。请加载更多历史数据。")


if st.session_state.get('backtest_done', False):
    result = st.session_state['backtest_result']
    df = st.session_state['current_df']
    visualizer = ChartVisualizer(df)
    
    st.divider()
    st.subheader("💹 回测结果")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.markdown("**总收益率**")
        return_class = "positive" if result.total_return >= 0 else "negative"
        st.markdown(f'<div class="metric-value {return_class}">{result.total_return:.1%}</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col2:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.markdown("**年化收益率**")
        return_class = "positive" if result.annual_return >= 0 else "negative"
        st.markdown(f'<div class="metric-value {return_class}">{result.annual_return:.1%}</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col3:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.markdown("**最大回撤**")
        return_class = "negative" if result.max_drawdown < -0.1 else "positive"
        st.markdown(f'<div class="metric-value {return_class}">{result.max_drawdown:.1%}</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col4:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.markdown("**夏普比率**")
        return_class = "positive" if result.sharpe_ratio >= 1 else ""
        st.markdown(f'<div class="metric-value {return_class}">{result.sharpe_ratio:.2f}</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
    
    col5, col6, col7, col8 = st.columns(4)
    
    with col5:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.markdown("**总交易次数**")
        st.markdown(f'<div class="metric-value">{result.total_trades}</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col6:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.markdown("**胜率**")
        return_class = "positive" if result.win_rate >= 0.5 else "negative"
        st.markdown(f'<div class="metric-value {return_class}">{result.win_rate:.1%}</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col7:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.markdown("**盈亏比**")
        profit_factor = result.profit_factor if result.profit_factor != float('inf') else 0
        return_class = "positive" if profit_factor >= 1.5 else ""
        st.markdown(f'<div class="metric-value {return_class}">{profit_factor:.2f}</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col8:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.markdown("**平均每笔盈亏**")
        return_class = "positive" if result.avg_pnl_per_trade >= 0 else "negative"
        st.markdown(f'<div class="metric-value {return_class}">¥{result.avg_pnl_per_trade:.2f}</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
    
    st.subheader("💰 交易成本统计")
    cost_col1, cost_col2, cost_col3 = st.columns(3)
    with cost_col1:
        st.metric("总滑点成本", f"¥{result.total_slippage:.2f}")
    with cost_col2:
        st.metric("总佣金成本", f"¥{result.total_commission:.2f}")
    with cost_col3:
        st.metric("总交易成本", f"¥{result.total_trading_cost:.2f}")
    
    col_equity, col_drawdown = st.columns(2)
    
    with col_equity:
        equity_fig = visualizer.create_equity_curve(
            result.equity_curve,
            title="资金曲线"
        )
        st.plotly_chart(equity_fig, use_container_width=True)
    
    with col_drawdown:
        drawdown_fig = visualizer.create_drawdown_chart(
            result.equity_curve,
            title="回撤曲线"
        )
        st.plotly_chart(drawdown_fig, use_container_width=True)
    
    st.subheader("📈 各形态表现统计")
    
    backtest_engine = BacktestEngine(df)
    pattern_stats = backtest_engine.get_pattern_analysis(result.trades)
    pattern_fig = visualizer.create_pattern_performance_chart(pattern_stats)
    st.plotly_chart(pattern_fig, use_container_width=True)
    
    if not pattern_stats.empty:
        st.dataframe(pattern_stats.style.format({
            'total_pnl': '¥{:.2f}',
            'avg_pnl': '¥{:.2f}',
            'win_rate': '{:.1%}',
            'total_cost': '¥{:.2f}'
        }), use_container_width=True)
    
    if result.trades:
        st.subheader("📝 交易记录")
        
        trades_df = pd.DataFrame([
            {
                '形态': t.pattern,
                '方向': '做多' if t.position_type.value == 'long' else '做空',
                '入场日期': t.entry_date,
                '入场价格': f"{t.entry_price:.2f}",
                '出场日期': t.exit_date,
                '出场价格': f"{t.exit_price:.2f}",
                '盈亏': f"¥{t.pnl:.2f}",
                '盈亏率': f"{t.pnl_pct:.1%}",
                '交易成本': f"¥{t.total_cost:.2f}"
            } for t in result.trades
        ])
        st.dataframe(trades_df, use_container_width=True)


if not st.session_state.get('data_loaded', False):
    st.info("👈 请在左侧设置股票代码和日期范围，点击「加载数据」开始分析")


st.markdown("---")
st.markdown("### 📖 使用说明")
st.markdown("""
1. **数据加载**: 设置股票代码、日期范围和时间周期，点击「加载数据」
2. **形态识别**: 选择要识别的形态并调整参数，点击「识别形态」
3. **组合识别**: 启用组合形态识别，多形态连续出现时信号增强 (1.4x ~ 2.2x)
4. **预警推送**: 形态出现时自动生成预警，支持置信度过滤
5. **成功率统计**: 查看各形态历史胜率、平均收益率和滚动趋势
6. **回测验证**: 设置交易参数和成本模型，点击「运行回测」

**核心功能**:
- ⚡ **组合形态**: 12种组合规则，多形态连续出现信号增强
- 🔔 **预警推送**: 按置信度和类型过滤，组合形态优先预警
- 📈 **历史胜率**: 前瞻验证各形态预测准确性，滚动成功率趋势
- 🎯 **动态阈值**: 基于ATR波动率自动调整识别阈值
- 💰 **滑点模型**: 固定滑点+百分比滑点+佣金完整成本计算
- 🔄 **异步防抖**: 参数调节不触发计算，点击按钮执行

**风险提示**: 本系统仅供学习和研究使用，不构成投资建议。
""")
