import streamlit as st
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots

from order_book import (
    OrderBookSimulator, MarketImpactCalculator,
    HighFrequencyOrderBook, QuadraticImpactModel, OrderSide
)
from impact_models import (
    MarketImpactModel, MLImpactPredictor, OptimalExecution,
    TimeConstrainedOptimalExecution, ExecutionConstraints, TimeHorizon
)
from dark_pool import (
    DarkPoolSimulator, ImpactPredictionInterval,
    TradingCostAttribution
)

st.set_page_config(
    page_title="股票市场冲击成本模型 - 专业版",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
    <style>
    .main {
        background-color: #0e1117;
    }
    .stMetric {
        background-color: #262730;
        padding: 15px;
        border-radius: 10px;
    }
    </style>
    """, unsafe_allow_html=True)

st.title("📊 股票市场冲击成本模型 - 专业版")
st.markdown("**高频订单簿 • 二次型冲击 • 暗池分析 • 预测区间 • 成本归因**")
st.markdown("---")

with st.sidebar:
    st.header("⚙️ 参数设置")
    
    st.subheader("订单簿参数")
    mid_price = st.slider("中间价格", 50.0, 500.0, 100.0, 10.0)
    base_depth = st.slider("基础深度(股)", 500, 5000, 1500, 100)
    depth_decay = st.slider("深度衰减系数", 0.70, 0.95, 0.85, 0.01)
    spread = st.slider("买卖价差", 0.01, 0.10, 0.02, 0.01)
    num_levels = st.slider("订单簿档位", 10, 30, 20, 1)
    
    st.subheader("交易参数")
    side = st.selectbox("交易方向", ["buy", "sell"], format_func=lambda x: "买入" if x == "buy" else "卖出")
    total_quantity = st.slider("总交易量(股)", 100, 20000, 5000, 100)
    
    st.subheader("时效约束参数")
    max_duration = st.slider("最大执行时长(秒)", 30, 600, 300, 10)
    urgency = st.slider("执行迫切度", 0.0, 1.0, 0.5, 0.1)
    impact_weight = st.slider("冲击成本权重", 0.1, 3.0, 1.0, 0.1)
    time_weight = st.slider("时间成本权重", 0.1, 3.0, 1.0, 0.1)
    
    st.subheader("暗池参数")
    dark_fill_rate = st.slider("暗池成交率", 0.3, 0.9, 0.65, 0.05)
    dark_price_improvement = st.slider("暗池价格改善(bps)", 0.0, 5.0, 2.0, 0.5)
    adverse_selection = st.slider("逆向选择系数", 0.0, 0.5, 0.3, 0.05)
    
    st.subheader("高频模拟参数")
    sim_duration_ms = st.slider("模拟时长(毫秒)", 100, 5000, 1000, 100)
    snapshot_interval_us = st.slider("采样间隔(微秒)", 10, 500, 100, 10)
    
    if st.button("🔄 重新生成订单簿"):
        st.rerun()

constraints = ExecutionConstraints(
    max_duration_seconds=max_duration,
    urgency=urgency,
    impact_weight=impact_weight,
    time_weight=time_weight
)

dark_pool_params = {
    'dark_pool_participation_rate': 0.15,
    'dark_pool_fill_rate': dark_fill_rate,
    'dark_pool_midpoint_execution': True,
    'dark_pool_price_improvement_bps': dark_price_improvement,
    'information_leakage_factor': 0.1,
    'dark_pool_delay_seconds': 5.0,
    'adverse_selection_factor': adverse_selection,
    'min_fill_size': 100,
    'dark_pool_venue_count': 3
}

@st.cache_data
def generate_order_book(mid_price, base_depth, depth_decay, spread, num_levels):
    simulator = OrderBookSimulator(
        mid_price=mid_price,
        spread=spread,
        num_levels=num_levels,
        liquidity_params={
            'base_depth': base_depth,
            'depth_decay': depth_decay,
            'volatility': 0.001,
            'bid_ask_imbalance': 0.0,
            'shape_param': 1.5
        }
    )
    return simulator.generate_order_book(), simulator.get_book_summary()

@st.cache_data
def simulate_hft(mid_price, duration_ns, snapshot_interval_ns):
    hft_book = HighFrequencyOrderBook(initial_mid_price=mid_price, num_levels=50)
    snapshots = hft_book.simulate_hft_events(
        duration_ns=duration_ns,
        snapshot_interval_ns=snapshot_interval_ns
    )
    return snapshots, hft_book

order_book_df, book_summary = generate_order_book(mid_price, base_depth, depth_decay, spread, num_levels)

col1, col2, col3, col4, col5 = st.columns(5)
with col1:
    st.metric("中间价格", f"${book_summary['mid_price']:.2f}")
with col2:
    st.metric("买卖价差(bps)", f"{book_summary['spread_bps']:.2f}")
with col3:
    st.metric("买单总深度", f"{book_summary['total_bid_depth']:,}")
with col4:
    st.metric("卖单总深度", f"{book_summary['total_ask_depth']:,}")
with col5:
    st.metric("订单簿不平衡", f"{book_summary['book_imbalance']*100:.1f}%")

st.markdown("---")

tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8, tab9 = st.tabs([
    "📚 订单簿可视化",
    "⚡ 高频订单簿模拟",
    "📈 冲击成本曲线",
    "🌑 暗池交易分析",
    "📏 冲击预测区间",
    "💰 成本归因分析",
    "🤖 ML预测模型",
    "⏱️ 时效约束最优执行",
    "💡 策略对比分析"
])

with tab1:
    st.header("订单簿深度可视化")
    
    calculator = MarketImpactCalculator(order_book_df)
    depth_summary = calculator.get_depth_summary()
    
    fig = make_subplots(rows=1, cols=2, subplot_titles=("订单簿分布", "累计深度曲线"))
    
    fig.add_trace(
        go.Bar(
            y=depth_summary['bid_price'],
            x=depth_summary['bid_quantity'],
            name='买单',
            orientation='h',
            marker_color='#00ff9d',
            opacity=0.7
        ),
        row=1, col=1
    )
    
    fig.add_trace(
        go.Bar(
            y=depth_summary['ask_price'],
            x=depth_summary['ask_quantity'],
            name='卖单',
            orientation='h',
            marker_color='#ff4757',
            opacity=0.7
        ),
        row=1, col=1
    )
    
    fig.add_trace(
        go.Scatter(
            x=depth_summary['cumulative_bid'],
            y=depth_summary['bid_price'],
            name='累计买单',
            line=dict(color='#00ff9d', width=2)
        ),
        row=1, col=2
    )
    
    fig.add_trace(
        go.Scatter(
            x=depth_summary['cumulative_ask'],
            y=depth_summary['ask_price'],
            name='累计卖单',
            line=dict(color='#ff4757', width=2)
        ),
        row=1, col=2
    )
    
    fig.update_layout(
        height=450,
        showlegend=True,
        template="plotly_dark",
        barmode='overlay'
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    st.subheader("订单簿数据")
    display_df = order_book_df[['level', 'bid_price', 'bid_quantity', 'ask_price', 'ask_quantity']].copy()
    display_df.columns = ['档位', '买价', '买量', '卖价', '卖量']
    st.dataframe(display_df, use_container_width=True, height=400)

with tab2:
    st.header("⚡ 高频订单簿模拟 (纳秒级)")
    
    with st.spinner("正在生成高频订单簿数据..."):
        duration_ns = sim_duration_ms * 1_000_000
        snapshot_interval_ns = snapshot_interval_us * 1000
        hft_snapshots, hft_book = simulate_hft(mid_price, duration_ns, snapshot_interval_ns)
    
    if len(hft_snapshots) > 0:
        col1, col2 = st.columns(2)
        
        with col1:
            st.metric("采样点数", f"{len(hft_snapshots):,}")
        with col2:
            avg_interval = (hft_snapshots['timestamp'].diff().mean().value / 1000 
                          if len(hft_snapshots) > 1 else 0)
            st.metric("平均采样间隔", f"{avg_interval:.1f} μs")
        
        fig = make_subplots(
            rows=2, cols=2,
            subplot_titles=(
                "中间价格变化",
                "买卖深度变化",
                "价差变化",
                "订单簿不平衡"
            ),
            vertical_spacing=0.15
        )
        
        fig.add_trace(
            go.Scatter(
                x=hft_snapshots['timestamp'],
                y=hft_snapshots['mid_price'],
                name='中间价格',
                line=dict(color='#f1c40f', width=2)
            ),
            row=1, col=1
        )
        
        fig.add_trace(
            go.Scatter(
                x=hft_snapshots['timestamp'],
                y=hft_snapshots['bid_depth'],
                name='买单深度',
                line=dict(color='#00ff9d', width=2)
            ),
            row=1, col=2
        )
        fig.add_trace(
            go.Scatter(
                x=hft_snapshots['timestamp'],
                y=hft_snapshots['ask_depth'],
                name='卖单深度',
                line=dict(color='#ff4757', width=2)
            ),
            row=1, col=2
        )
        
        fig.add_trace(
            go.Scatter(
                x=hft_snapshots['timestamp'],
                y=hft_snapshots['spread'] * 10000 / hft_snapshots['mid_price'],
                name='价差(bps)',
                line=dict(color='#9b59b6', width=2),
                fill='tozeroy'
            ),
            row=2, col=1
        )
        
        fig.add_trace(
            go.Scatter(
                x=hft_snapshots['timestamp'],
                y=hft_snapshots['book_imbalance'] * 100,
                name='不平衡(%)',
                line=dict(color='#e74c3c', width=2),
                fill='tozeroy'
            ),
            row=2, col=2
        )
        
        fig.update_layout(
            height=600,
            showlegend=True,
            template="plotly_dark"
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        st.subheader("高频数据统计")
        stats_df = pd.DataFrame({
            '指标': [
                '价格波动率(std)',
                '平均价差(bps)',
                '平均买单深度',
                '平均卖单深度',
                '平均不平衡度(%)'
            ],
            '数值': [
                f"{hft_snapshots['mid_price'].std():.4f}",
                f"{(hft_snapshots['spread'] * 10000 / hft_snapshots['mid_price']).mean():.2f}",
                f"{hft_snapshots['bid_depth'].mean():,.0f}",
                f"{hft_snapshots['ask_depth'].mean():,.0f}",
                f"{hft_snapshots['book_imbalance'].mean() * 100:.2f}"
            ]
        })
        st.dataframe(stats_df, use_container_width=True, hide_index=True)
    else:
        st.warning("请增加模拟时长以生成更多采样点")

with tab3:
    st.header("市场冲击成本曲线 (二次型模型)")
    
    quadratic_model = QuadraticImpactModel(order_book_df)
    calculator = MarketImpactCalculator(order_book_df)
    
    max_qty = max(total_quantity * 2, 10000)
    
    quadratic_curve = quadratic_model.get_impact_curve(max_qty, steps=30)
    linear_curve = calculator.get_impact_curve(max_qty, steps=30)
    
    model_params = quadratic_model.get_model_parameters()
    
    st.subheader("二次型模型参数")
    param_col1, param_col2, param_col3, param_col4 = st.columns(4)
    with param_col1:
        st.metric("买单弹性", f"{model_params['bid_elasticity']:.2f}")
    with param_col2:
        st.metric("卖单弹性", f"{model_params['ask_elasticity']:.2f}")
    with param_col3:
        st.metric("买单二次项系数", f"{model_params['bid_quadratic_coeff']:.2e}")
    with param_col4:
        st.metric("卖单二次项系数", f"{model_params['ask_quadratic_coeff']:.2e}")
    
    col1, col2 = st.columns(2)
    
    with col1:
        fig1 = go.Figure()
        
        fig1.add_trace(
            go.Scatter(
                x=quadratic_curve['quantity'],
                y=quadratic_curve['buy_slippage_bps'],
                name='二次型-买入',
                line=dict(color='#ff4757', width=3),
                fill='tozeroy',
                opacity=0.3
            )
        )
        
        fig1.add_trace(
            go.Scatter(
                x=quadratic_curve['quantity'],
                y=quadratic_curve['sell_slippage_bps'],
                name='二次型-卖出',
                line=dict(color='#00ff9d', width=3),
                fill='tozeroy',
                opacity=0.3
            )
        )
        
        fig1.add_trace(
            go.Scatter(
                x=linear_curve['quantity'],
                y=linear_curve['buy_slippage_bps'],
                name='线性插值-买入',
                line=dict(color='#ff6b6b', width=2, dash='dash')
            )
        )
        
        fig1.add_trace(
            go.Scatter(
                x=linear_curve['quantity'],
                y=linear_curve['sell_slippage_bps'],
                name='线性插值-卖出',
                line=dict(color='#6bff6b', width=2, dash='dash')
            )
        )
        
        fig1.add_vline(
            x=total_quantity,
            line_dash="dash",
            line_color="yellow",
            annotation_text=f"当前交易量: {total_quantity:,}股"
        )
        
        fig1.update_layout(
            title="滑点 vs 交易量 (bps) - 模型对比",
            xaxis_title="交易量 (股)",
            yaxis_title="滑点 (bps)",
            template="plotly_dark",
            height=400
        )
        
        st.plotly_chart(fig1, use_container_width=True)
    
    with col2:
        fig2 = go.Figure()
        
        fig2.add_trace(
            go.Scatter(
                x=quadratic_curve['quantity'],
                y=quadratic_curve['buy_quadratic_component_bps'],
                name='买入二次项',
                line=dict(color='#9b59b6', width=3),
                fill='tozeroy'
            )
        )
        
        fig2.add_trace(
            go.Scatter(
                x=quadratic_curve['quantity'],
                y=quadratic_curve['sell_quadratic_component_bps'],
                name='卖出二次项',
                line=dict(color='#e74c3c', width=3),
                fill='tozeroy'
            )
        )
        
        fig2.add_vline(
            x=total_quantity,
            line_dash="dash",
            line_color="yellow"
        )
        
        fig2.update_layout(
            title="二次项贡献 (非线性效应)",
            xaxis_title="交易量 (股)",
            yaxis_title="二次项滑点 (bps)",
            template="plotly_dark",
            height=400
        )
        
        st.plotly_chart(fig2, use_container_width=True)
    
    st.subheader("当前交易冲击分析")
    q_avg_price, q_slippage_bps, q_quad = quadratic_model.calculate_impact(total_quantity, side)
    l_avg_price, l_slippage_bps, _ = calculator.calculate_impact(total_quantity, side)
    
    metric_col1, metric_col2, metric_col3 = st.columns(3)
    
    with metric_col1:
        st.metric(
            "二次型模型滑点",
            f"{q_slippage_bps:.2f} bps",
            f"${q_slippage_bps * q_avg_price / 10000:.4f}/股"
        )
    with metric_col2:
        st.metric(
            "线性模型滑点",
            f"{l_slippage_bps:.2f} bps",
            f"${l_slippage_bps * l_avg_price / 10000:.4f}/股"
        )
    with metric_col3:
        diff = q_slippage_bps - l_slippage_bps
        st.metric(
            "非线性差异",
            f"{diff:.2f} bps",
            f"{'高估' if diff > 0 else '低估'}"
        )

with tab4:
    st.header("🌑 暗池交易分析")
    
    dark_sim = DarkPoolSimulator(mid_price, dark_pool_params=dark_pool_params)
    dark_comparison = dark_sim.compare_lit_vs_dark(total_quantity, side, order_book_df)
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric(
            "明池滑点",
            f"{dark_comparison['lit_only']['slippage_bps']:.2f} bps"
        )
    with col2:
        st.metric(
            "暗池+明池组合滑点",
            f"{dark_comparison['dark_pool']['combined_slippage_bps']:.2f} bps"
        )
    with col3:
        savings = dark_comparison['savings_bps']
        st.metric(
            "暗池节省",
            f"{savings:.2f} bps",
            f"{'✅ 节省' if savings > 0 else '❌ 无节省'}"
        )
    with col4:
        st.metric(
            "暗池成交率",
            f"{dark_comparison['dark_pool']['dark_fill_rate']*100:.1f}%"
        )
    
    st.subheader("📊 暗池执行详情")
    
    dp = dark_comparison['dark_pool']
    detail_col1, detail_col2 = st.columns(2)
    
    with detail_col1:
        st.markdown("#### 暗池部分")
        dp_detail = pd.DataFrame({
            '指标': [
                '暗池成交数量',
                '暗池成交价格',
                '暗池滑点(bps)',
                '逆向选择成本(bps)',
                '信息泄漏(bps)',
                '暗池总成本'
            ],
            '数值': [
                f"{dp['dark_filled_qty']:,} 股",
                f"${dp['dark_avg_price']:.4f}",
                f"{dp['dark_slippage_bps']:.2f}",
                f"{dp['adverse_selection_bps']:.2f}",
                f"{dp['info_leakage_bps']:.2f}",
                f"${dp['dark_total_cost']:,.2f}"
            ]
        })
        st.dataframe(dp_detail, use_container_width=True, hide_index=True)
    
    with detail_col2:
        st.markdown("#### 明池部分(暗池未成交溢出)")
        lit_detail = pd.DataFrame({
            '指标': [
                '明池溢出数量',
                '明池成交价格',
                '明池滑点(bps)',
                '明池总成本',
                '组合平均价格',
                '组合总成本'
            ],
            '数值': [
                f"{dp['lit_unfilled_qty']:,} 股",
                f"${dp['lit_avg_price']:.4f}" if dp['lit_unfilled_qty'] > 0 else "N/A",
                f"{dp['lit_slippage_bps']:.2f}",
                f"${dp['lit_total_cost']:,.2f}",
                f"${dp['combined_avg_price']:.4f}",
                f"${dp['combined_total_cost']:,.2f}"
            ]
        })
        st.dataframe(lit_detail, use_container_width=True, hide_index=True)
    
    st.subheader("📈 暗池 vs 明池冲击曲线对比")
    
    dark_curve = dark_sim.dark_pool_impact_curve(max_qty, side, order_book_df, steps=20)
    
    fig = go.Figure()
    
    fig.add_trace(
        go.Scatter(
            x=dark_curve['quantity'],
            y=dark_curve['lit_slippage_bps'],
            name='明池滑点',
            line=dict(color='#ff4757', width=3),
            mode='lines+markers'
        )
    )
    
    fig.add_trace(
        go.Scatter(
            x=dark_curve['quantity'],
            y=dark_curve['dark_slippage_bps'],
            name='暗池+明池组合',
            line=dict(color='#9b59b6', width=3),
            mode='lines+markers'
        )
    )
    
    fig.add_trace(
        go.Scatter(
            x=dark_curve['quantity'],
            y=dark_curve['savings_bps'],
            name='暗池节省(bps)',
            line=dict(color='#2ecc71', width=2, dash='dash'),
            fill='tozeroy'
        )
    )
    
    fig.add_vline(
        x=total_quantity,
        line_dash="dash",
        line_color="yellow",
        annotation_text=f"当前交易量"
    )
    
    fig.update_layout(
        title="暗池 vs 明池冲击成本对比",
        xaxis_title="交易量 (股)",
        yaxis_title="滑点 (bps)",
        template="plotly_dark",
        height=450
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    st.subheader("⚖️ 暗池风险分析")
    
    risk_col1, risk_col2 = st.columns(2)
    
    with risk_col1:
        fig_risk = go.Figure()
        
        fill_rates = np.linspace(0.3, 0.9, 20)
        savings_by_fill = []
        for fr in fill_rates:
            test_params = dark_pool_params.copy()
            test_params['dark_pool_fill_rate'] = fr
            test_sim = DarkPoolSimulator(mid_price, dark_pool_params=test_params)
            test_result = test_sim.compare_lit_vs_dark(total_quantity, side, order_book_df)
            savings_by_fill.append(test_result['savings_bps'])
        
        fig_risk.add_trace(
            go.Scatter(
                x=fill_rates * 100,
                y=savings_by_fill,
                name='暗池节省(bps)',
                line=dict(color='#2ecc71', width=3),
                fill='tozeroy'
            )
        )
        
        fig_risk.update_layout(
            title="暗池成交率 vs 节省幅度",
            xaxis_title="暗池成交率 (%)",
            yaxis_title="节省 (bps)",
            template="plotly_dark",
            height=350
        )
        st.plotly_chart(fig_risk, use_container_width=True)
    
    with risk_col2:
        fig_adverse = go.Figure()
        
        adverse_levels = np.linspace(0.0, 0.5, 20)
        savings_by_adverse = []
        for adv in adverse_levels:
            test_params = dark_pool_params.copy()
            test_params['adverse_selection_factor'] = adv
            test_sim = DarkPoolSimulator(mid_price, dark_pool_params=test_params)
            test_result = test_sim.compare_lit_vs_dark(total_quantity, side, order_book_df)
            savings_by_adverse.append(test_result['savings_bps'])
        
        fig_adverse.add_trace(
            go.Scatter(
                x=adverse_levels,
                y=savings_by_adverse,
                name='暗池节省(bps)',
                line=dict(color='#e74c3c', width=3),
                fill='tozeroy'
            )
        )
        
        fig_adverse.update_layout(
            title="逆向选择 vs 暗池节省",
            xaxis_title="逆向选择系数",
            yaxis_title="节省 (bps)",
            template="plotly_dark",
            height=350
        )
        st.plotly_chart(fig_adverse, use_container_width=True)
    
    st.info("""
    **暗池交易说明：**
    - **暗池优势**: 以中间价成交，避免买卖价差；不公开订单信息，减少前置运行
    - **暗池风险**: 逆向选择（有毒订单流）、成交不确定、信息泄漏
    - **推荐策略**: 当暗池成交率>60%且逆向选择较低时，优先使用暗池+明池组合
    """)

with tab5:
    st.header("📏 冲击成本预测区间")
    
    interval_predictor = ImpactPredictionInterval(order_book_df)
    prediction = interval_predictor.predict_interval(total_quantity, side)
    
    st.subheader("点估计与不确定性")
    
    est_col1, est_col2, est_col3 = st.columns(3)
    with est_col1:
        st.metric("点估计滑点", f"{prediction['point_estimate_bps']:.2f} bps")
    with est_col2:
        st.metric("不确定性(1σ)", f"±{prediction['uncertainty_bps']:.2f} bps")
    with est_col3:
        st.metric("变异系数", f"{prediction['uncertainty_bps'] / max(prediction['point_estimate_bps'], 0.01) * 100:.1f}%")
    
    st.subheader("不同置信水平下的冲击范围")
    
    confidence_df = interval_predictor.get_multi_confidence_curve(total_quantity, side)
    
    fig_conf = go.Figure()
    
    for _, row in confidence_df.iterrows():
        cl = row['confidence_level']
        lower = row['lower_bps']
        upper = row['upper_bps']
        
        opacity = float(cl.replace('%', '')) / 100 * 0.5
        
        fig_conf.add_trace(
            go.Scatter(
                x=[lower, upper],
                y=[cl, cl],
                name=f'{cl} CI',
                line=dict(width=8),
                opacity=0.3 + opacity
            )
        )
    
    fig_conf.add_vline(
        x=prediction['point_estimate_bps'],
        line_dash="dash",
        line_color="white",
        annotation_text="点估计"
    )
    
    fig_conf.update_layout(
        title="冲击成本预测区间 (不同置信水平)",
        xaxis_title="滑点 (bps)",
        yaxis_title="置信水平",
        template="plotly_dark",
        height=400,
        showlegend=True
    )
    
    st.plotly_chart(fig_conf, use_container_width=True)
    
    st.dataframe(confidence_df.style.format({
        'lower_bps': '{:.2f}',
        'upper_bps': '{:.2f}',
        'width_bps': '{:.2f}',
        'z_score': '{:.2f}'
    }), use_container_width=True, hide_index=True)
    
    st.subheader("📈 预测区间 vs 交易量")
    
    selected_conf = st.selectbox("选择置信水平", [0.50, 0.68, 0.80, 0.90, 0.95, 0.99], index=3, 
                                 format_func=lambda x: f"{int(x*100)}%")
    
    interval_curve = interval_predictor.get_interval_curve(max_qty, side, selected_conf, steps=25)
    
    fig_iv = go.Figure()
    
    fig_iv.add_trace(
        go.Scatter(
            x=interval_curve['quantity'],
            y=interval_curve['upper'],
            name=f'上限 ({int(selected_conf*100)}%)',
            line=dict(color='#ff6b6b', width=2)
        )
    )
    
    fig_iv.add_trace(
        go.Scatter(
            x=interval_curve['quantity'],
            y=interval_curve['lower'],
            name=f'下限 ({int(selected_conf*100)}%)',
            line=dict(color='#6bff6b', width=2),
            fill='tonexty',
            fillcolor='rgba(128,128,128,0.2)'
        )
    )
    
    fig_iv.add_trace(
        go.Scatter(
            x=interval_curve['quantity'],
            y=interval_curve['point_estimate'],
            name='点估计',
            line=dict(color='#f1c40f', width=3)
        )
    )
    
    fig_iv.add_vline(
        x=total_quantity,
        line_dash="dash",
        line_color="yellow",
        annotation_text="当前交易量"
    )
    
    fig_iv.update_layout(
        title=f"冲击成本预测区间 ({int(selected_conf*100)}% 置信水平)",
        xaxis_title="交易量 (股)",
        yaxis_title="滑点 (bps)",
        template="plotly_dark",
        height=450
    )
    
    st.plotly_chart(fig_iv, use_container_width=True)
    
    st.subheader("不同置信水平区间宽度对比")
    
    all_curves = {}
    for cl in [0.68, 0.90, 0.95]:
        curve = interval_predictor.get_interval_curve(max_qty, side, cl, steps=20)
        all_curves[cl] = curve
    
    fig_width = go.Figure()
    for cl, curve in all_curves.items():
        fig_width.add_trace(
            go.Scatter(
                x=curve['quantity'],
                y=curve['width'],
                name=f'{int(cl*100)}% CI宽度',
                line=dict(width=2),
                mode='lines+markers'
            )
        )
    
    fig_width.update_layout(
        title="预测区间宽度 vs 交易量",
        xaxis_title="交易量 (股)",
        yaxis_title="区间宽度 (bps)",
        template="plotly_dark",
        height=350
    )
    st.plotly_chart(fig_width, use_container_width=True)

with tab6:
    st.header("💰 交易成本归因分析")
    
    cost_attribution = TradingCostAttribution(order_book_df, total_quantity, side)
    attribution = cost_attribution.attribute_costs()
    
    st.subheader("成本归因总览")
    
    total_col1, total_col2 = st.columns(2)
    with total_col1:
        st.metric("总交易成本", f"{attribution['total_cost_bps']:.2f} bps")
    with total_col2:
        st.metric("总交易金额成本", f"${attribution['total_cost_dollar']:,.2f}")
    
    comp = attribution['components']
    
    component_df = pd.DataFrame({
        '成本类型': list(comp.keys()),
        '滑点(bps)': [comp[k]['bps'] for k in comp],
        '金额($)': [comp[k]['dollar'] for k in comp],
        '占比(%)': [comp[k]['share_pct'] for k in comp],
        '说明': [comp[k]['description'] for k in comp]
    })
    
    st.dataframe(component_df.style.format({
        '滑点(bps)': '{:.2f}',
        '金额($)': '${:,.2f}',
        '占比(%)': '{:.1f}%'
    }), use_container_width=True, hide_index=True)
    
    st.subheader("📊 成本构成可视化")
    
    col_pie, col_bar = st.columns(2)
    
    with col_pie:
        fig_pie = px.pie(
            component_df,
            values='滑点(bps)',
            names='成本类型',
            title='成本归因占比',
            template="plotly_dark",
            color_discrete_sequence=px.colors.qualitative.Set2
        )
        fig_pie.update_traces(textposition='inside', textinfo='percent+label')
        fig_pie.update_layout(height=400)
        st.plotly_chart(fig_pie, use_container_width=True)
    
    with col_bar:
        fig_bar = go.Figure()
        fig_bar.add_trace(
            go.Bar(
                x=component_df['成本类型'],
                y=component_df['滑点(bps)'],
                name='滑点(bps)',
                marker_color=['#3498db', '#e74c3c', '#f1c40f', '#9b59b6', '#2ecc71'],
                text=component_df['滑点(bps)'].round(2),
                textposition='auto'
            )
        )
        fig_bar.update_layout(
            title='各成本类型滑点(bps)',
            xaxis_title='成本类型',
            yaxis_title='滑点 (bps)',
            template="plotly_dark",
            height=400
        )
        st.plotly_chart(fig_bar, use_container_width=True)
    
    st.subheader("📈 市场冲击 vs 其他成本")
    
    impact_vs = attribution['impact_vs_others']
    
    col_imp1, col_imp2, col_imp3 = st.columns(3)
    with col_imp1:
        st.metric("市场冲击占比", f"{impact_vs['market_impact_pct']:.1f}%")
    with col_imp2:
        st.metric("其他成本占比", f"{impact_vs['other_costs_pct']:.1f}%")
    with col_imp3:
        if impact_vs['impact_is_dominant']:
            st.metric("主导因素", "🔴 市场冲击")
        else:
            st.metric("主导因素", "🔵 其他成本")
    
    st.subheader("📉 成本归因随交易量变化")
    
    attr_curve = cost_attribution.get_attribution_curve(max_qty, steps=20)
    
    fig_stack = go.Figure()
    
    colors = {
        'spread_bps': '#3498db',
        'impact_bps': '#e74c3c',
        'timing_bps': '#f1c40f',
        'opportunity_bps': '#9b59b6',
        'commission_bps': '#2ecc71'
    }
    labels = {
        'spread_bps': '买卖价差',
        'impact_bps': '市场冲击',
        'timing_bps': '时机成本',
        'opportunity_bps': '机会成本',
        'commission_bps': '佣金'
    }
    
    for col_name in ['spread_bps', 'impact_bps', 'timing_bps', 'opportunity_bps', 'commission_bps']:
        fig_stack.add_trace(
            go.Scatter(
                x=attr_curve['quantity'],
                y=attr_curve[col_name],
                name=labels[col_name],
                line=dict(color=colors[col_name], width=2),
                stackgroup='one'
            )
        )
    
    fig_stack.add_vline(
        x=total_quantity,
        line_dash="dash",
        line_color="yellow",
        annotation_text="当前交易量"
    )
    
    fig_stack.update_layout(
        title="成本归因堆叠图 (随交易量变化)",
        xaxis_title="交易量 (股)",
        yaxis_title="成本 (bps)",
        template="plotly_dark",
        height=450
    )
    st.plotly_chart(fig_stack, use_container_width=True)
    
    st.subheader("暗池场景下的成本归因对比")
    
    dark_attr = TradingCostAttribution(order_book_df, total_quantity, side)
    dark_attribution = dark_attr.attribute_costs()
    
    dark_sim_compare = DarkPoolSimulator(mid_price, dark_pool_params=dark_pool_params)
    dark_result = dark_sim_compare.simulate_dark_pool_execution(total_quantity, side, order_book_df)
    
    compare_attribution = pd.DataFrame({
        '成本类型': ['买卖价差', '市场冲击', '时机成本', '机会成本', '佣金'],
        '纯明池(bps)': [
            attribution['components']['spread']['bps'],
            attribution['components']['market_impact']['bps'],
            attribution['components']['timing']['bps'],
            attribution['components']['opportunity']['bps'],
            attribution['components']['commission']['bps']
        ],
        '暗池+明池(bps)': [
            attribution['components']['spread']['bps'] * (1 - dark_result['dark_fill_rate']),
            attribution['components']['market_impact']['bps'] * (1 - dark_result['dark_fill_rate'] * 0.3),
            attribution['components']['timing']['bps'],
            attribution['components']['opportunity']['bps'] * 0.5,
            attribution['components']['commission']['bps']
        ]
    })
    compare_attribution['节省(bps)'] = compare_attribution['纯明池(bps)'] - compare_attribution['暗池+明池(bps)']
    
    fig_dark_attr = go.Figure()
    fig_dark_attr.add_trace(go.Bar(name='纯明池', x=compare_attribution['成本类型'],
                                   y=compare_attribution['纯明池(bps)'], marker_color='#e74c3c'))
    fig_dark_attr.add_trace(go.Bar(name='暗池+明池', x=compare_attribution['成本类型'],
                                   y=compare_attribution['暗池+明池(bps)'], marker_color='#9b59b6'))
    fig_dark_attr.update_layout(
        title='纯明池 vs 暗池+明池 成本归因对比',
        barmode='group',
        template="plotly_dark",
        height=400
    )
    st.plotly_chart(fig_dark_attr, use_container_width=True)

with tab7:
    st.header("机器学习冲击预测模型")
    
    @st.cache_resource
    def train_ml_model():
        ml_predictor = MLImpactPredictor()
        with st.spinner("正在训练ML模型 (约2000个样本)..."):
            metrics = ml_predictor.train(n_samples=2000)
        return ml_predictor, metrics
    
    ml_predictor, metrics = train_ml_model()
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("模型性能指标")
        perf_df = pd.DataFrame({
            '指标': ['训练集MSE', '测试集MSE', '训练集R²', '测试集R²', '训练集RMSE', '测试集RMSE'],
            '数值': [
                f"{metrics['train_mse']:.4f}",
                f"{metrics['test_mse']:.4f}",
                f"{metrics['train_r2']:.4f}",
                f"{metrics['test_r2']:.4f}",
                f"{metrics['train_rmse']:.4f}",
                f"{metrics['test_rmse']:.4f}"
            ]
        })
        st.dataframe(perf_df, use_container_width=True, hide_index=True)
    
    with col2:
        st.subheader("特征重要性")
        feature_importance = ml_predictor.get_feature_importance()
        fig = px.bar(
            feature_importance.head(10),
            x='importance',
            y='feature',
            orientation='h',
            title='Top 10 特征重要性',
            template="plotly_dark",
            color='importance',
            color_continuous_scale='Viridis'
        )
        fig.update_layout(height=400)
        st.plotly_chart(fig, use_container_width=True)
    
    st.subheader("多模型预测对比")
    
    ml_prediction = ml_predictor.predict(order_book_df, total_quantity, side)
    
    comparison_df = pd.DataFrame({
        '方法': ['订单簿实际计算', '二次型模型', 'ML模型预测', '平方根模型'],
        '滑点(bps)': [
            l_slippage_bps,
            q_slippage_bps,
            ml_prediction,
            0.5 * np.sqrt(total_quantity / base_depth / 100) * 10
        ]
    })
    
    fig = px.bar(
        comparison_df,
        x='方法',
        y='滑点(bps)',
        color='方法',
        text_auto='.2f',
        template="plotly_dark",
        title="不同模型预测对比"
    )
    fig.update_layout(height=400)
    st.plotly_chart(fig, use_container_width=True)

with tab8:
    st.header("⏱️ 时效约束最优执行")
    
    with st.spinner("正在进行带时效约束的优化..."):
        time_exec = TimeConstrainedOptimalExecution(order_book_df, total_quantity, side)
        
        optimal_result = time_exec.optimize_execution(constraints, num_orders_range=(3, 15))
        twap_result = time_exec.generate_twap_schedule(10, constraints)
        vwap_result = time_exec.generate_vwap_schedule(10, constraints)
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📊 约束条件")
        constraint_df = pd.DataFrame({
            '参数': [
                '最大执行时长',
                '执行迫切度',
                '冲击成本权重',
                '时间成本权重'
            ],
            '数值': [
                f"{max_duration} 秒",
                f"{urgency:.2f}",
                f"{impact_weight:.1f}",
                f"{time_weight:.1f}"
            ]
        })
        st.dataframe(constraint_df, use_container_width=True, hide_index=True)
    
    with col2:
        st.subheader("🏆 最优策略结果")
        result_df = pd.DataFrame({
            '策略': ['最优执行', 'TWAP', 'VWAP'],
            '订单数': [
                optimal_result['num_orders'],
                twap_result['num_orders'],
                vwap_result['num_orders']
            ],
            '预计滑点(bps)': [
                f"{optimal_result['expected_impact_bps']:.2f}",
                f"{twap_result['expected_impact_bps']:.2f}",
                f"{vwap_result['expected_impact_bps']:.2f}"
            ],
            '执行时长(秒)': [
                f"{optimal_result['total_duration']:.1f}",
                f"{twap_result['total_duration']:.1f}",
                f"{vwap_result['total_duration']:.1f}"
            ],
            '完成概率': [
                f"{optimal_result['completion_probability']*100:.1f}%",
                f"{twap_result['completion_probability']*100:.1f}%",
                f"{vwap_result['completion_probability']*100:.1f}%"
            ]
        })
        st.dataframe(result_df, use_container_width=True, hide_index=True)
    
    st.subheader("⚖️ 冲击-时效权衡曲线")
    
    pareto_results = []
    for urgency_level in [0.1, 0.3, 0.5, 0.7, 0.9]:
        test_constraints = ExecutionConstraints(
            max_duration_seconds=max_duration,
            urgency=urgency_level,
            impact_weight=impact_weight,
            time_weight=time_weight
        )
        result = time_exec.optimize_execution(test_constraints, num_orders_range=(3, 12))
        pareto_results.append({
            'urgency': urgency_level,
            'impact': result['expected_impact_bps'],
            'duration': result['total_duration']
        })
    
    pareto_df = pd.DataFrame(pareto_results)
    
    fig = px.scatter(
        pareto_df,
        x='duration',
        y='impact',
        color='urgency',
        size=[100]*len(pareto_df),
        title='Pareto前沿: 冲击成本 vs 执行时间',
        labels={
            'duration': '执行时间(秒)',
            'impact': '冲击成本(bps)',
            'urgency': '迫切度'
        },
        template="plotly_dark",
        color_continuous_scale='RdYlGn_r'
    )
    fig.update_layout(height=400)
    st.plotly_chart(fig, use_container_width=True)

with tab9:
    st.header("💡 策略对比分析")
    
    optimal_exec = OptimalExecution(order_book_df, total_quantity, side)
    strategy_results = optimal_exec.get_optimal_strategy(risk_aversion=0.5)
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📊 全策略对比")
        
        comparison_data = pd.DataFrame([
            {
                '策略': '单笔订单',
                '拆单数': 1,
                '预计滑点(bps)': strategy_results['single_order']['slippage_bps'],
                '预计节省(bps)': 0
            },
            {
                '策略': '最优TWAP',
                '拆单数': strategy_results['optimal_twap']['num_orders'],
                '预计滑点(bps)': strategy_results['optimal_twap']['slippage_bps'],
                '预计节省(bps)': strategy_results['optimal_twap']['savings_bps']
            },
            {
                '策略': '最优VWAP',
                '拆单数': strategy_results['optimal_vwap']['num_orders'],
                '预计滑点(bps)': strategy_results['optimal_vwap']['slippage_bps'],
                '预计节省(bps)': strategy_results['optimal_vwap']['savings_bps']
            },
            {
                '策略': '时效约束最优',
                '拆单数': optimal_result['num_orders'],
                '预计滑点(bps)': optimal_result['expected_impact_bps'],
                '预计节省(bps)': strategy_results['single_order']['slippage_bps'] - optimal_result['expected_impact_bps']
            },
            {
                '策略': '暗池+明池',
                '拆单数': '-',
                '预计滑点(bps)': dark_comparison['dark_pool']['combined_slippage_bps'],
                '预计节省(bps)': dark_comparison['savings_bps']
            }
        ])
        
        st.dataframe(comparison_data.style.format({
            '预计滑点(bps)': '{:.2f}',
            '预计节省(bps)': '{:.2f}'
        }), use_container_width=True, hide_index=True)
    
    with col2:
        st.subheader("🏆 综合推荐")
        
        all_savings = {
            'TWAP': strategy_results['optimal_twap']['savings_bps'],
            'VWAP': strategy_results['optimal_vwap']['savings_bps'],
            '时效约束最优': strategy_results['single_order']['slippage_bps'] - optimal_result['expected_impact_bps'],
            '暗池+明池': dark_comparison['savings_bps']
        }
        
        best_strategy = max(all_savings, key=all_savings.get)
        best_savings = all_savings[best_strategy]
        
        st.success(f"**推荐策略: {best_strategy}**")
        st.write(f"• 相比单笔订单节省 **{best_savings:.2f} bps**")
        
        if best_strategy == '暗池+明池':
            st.write(f"• 暗池成交率 **{dark_comparison['dark_pool']['dark_fill_rate']*100:.1f}%**")
            st.write(f"• 暗池节省 **${dark_comparison['savings_dollar']:,.2f}**")
        elif best_strategy == '时效约束最优':
            st.write(f"• 拆分为 **{optimal_result['num_orders']}** 笔订单")
            st.write(f"• 执行时间 **{optimal_result['total_duration']:.1f}** 秒")
    
    st.subheader("📉 拆单数量优化曲线")
    
    optimization_df = optimal_exec.optimize_split(max_orders=20)
    
    fig = go.Figure()
    
    fig.add_trace(
        go.Scatter(
            x=optimization_df['num_orders'],
            y=optimization_df['twap_slippage'],
            name='TWAP策略',
            line=dict(color='#3498db', width=3),
            mode='lines+markers'
        )
    )
    
    fig.add_trace(
        go.Scatter(
            x=optimization_df['num_orders'],
            y=optimization_df['vwap_slippage'],
            name='VWAP策略',
            line=dict(color='#e74c3c', width=3),
            mode='lines+markers'
        )
    )
    
    fig.add_hline(
        y=strategy_results['single_order']['slippage_bps'],
        line_dash="dash",
        line_color="gray",
        annotation_text="单笔订单滑点"
    )
    
    fig.add_hline(
        y=dark_comparison['dark_pool']['combined_slippage_bps'],
        line_dash="dash",
        line_color="#9b59b6",
        annotation_text="暗池+明池"
    )
    
    fig.update_layout(
        title="拆单数量 vs 预计滑点",
        xaxis_title="拆单数量",
        yaxis_title="预计滑点 (bps)",
        template="plotly_dark",
        height=400
    )
    
    st.plotly_chart(fig, use_container_width=True)

st.markdown("---")
st.markdown("""
<div style='text-align: center; color: gray;'>
    <p>📊 股票市场冲击成本模型 专业版 | 高频订单簿 • 二次型冲击 • 暗池分析 • 预测区间 • 成本归因</p>
</div>
""", unsafe_allow_html=True)
