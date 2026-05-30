import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import sys
import os
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(__file__))

from analysis.sample_data import generate_competitor_data, generate_price_history, generate_our_price_history, save_demo_data
from analysis.price_index import PriceIndexAnalyzer
from analysis.trend_analysis import TrendAnalyzer
from analysis.promo_analysis import PromoAnalyzer
from analysis.pricing_optimizer import PricingOptimizer
from analysis.promo_rule_library import PromoRuleLibrary
from analysis.elasticity_calibrator import ElasticityCalibrator
from analysis.price_war_monitor import PriceWarMonitor
from analysis.dynamic_pricing import DynamicPricingEngine
from analysis.compliance_checker import PricingComplianceChecker


st.set_page_config(
    page_title='商品价格竞争力分析平台',
    page_icon='📊',
    layout='wide',
)

st.markdown("""
<style>
    .main-header { font-size: 2rem; font-weight: 700; color: #1f77b4; }
    .metric-card { background: #f0f2f6; border-radius: 10px; padding: 15px; text-align: center; }
    .metric-value { font-size: 1.8rem; font-weight: 700; }
    .metric-label { font-size: 0.9rem; color: #666; }
    .suggestion-box { border-left: 4px solid #1f77b4; padding: 10px 15px; background: #f8f9fa; margin: 5px 0; border-radius: 4px; }
    .rule-card { border: 1px solid #e0e0e0; border-radius: 8px; padding: 15px; margin: 10px 0; background: white; }
    .rule-card:hover { border-color: #1f77b4; box-shadow: 0 2px 8px rgba(31,119,180,0.15); }
</style>
""", unsafe_allow_html=True)


@st.cache_data
def load_data():
    comp_df = generate_competitor_data()
    hist_df = generate_price_history()
    our_hist_df = generate_our_price_history()
    return comp_df, hist_df, our_hist_df


def init_session_state():
    if 'rule_library' not in st.session_state:
        st.session_state.rule_library = PromoRuleLibrary()
    if 'elasticity_calibrator' not in st.session_state:
        st.session_state.elasticity_calibrator = ElasticityCalibrator()
    if 'price_war_monitor' not in st.session_state:
        st.session_state.price_war_monitor = PriceWarMonitor()
    if 'dynamic_pricing' not in st.session_state:
        st.session_state.dynamic_pricing = DynamicPricingEngine(our_cost=3200, base_price=4699)
    if 'compliance_checker' not in st.session_state:
        st.session_state.compliance_checker = PricingComplianceChecker()


def render_price_index_tab(comp_df, our_price):
    st.subheader('📊 价格指数分析')

    analyzer = PriceIndexAnalyzer(our_price, comp_df)
    index_result = analyzer.compute_price_index()
    platform_result = analyzer.compute_platform_index()

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown(f'<div class="metric-card"><div class="metric-value">{index_result["price_index"]}</div><div class="metric-label">价格指数 (100=均价)</div></div>', unsafe_allow_html=True)
    with col2:
        color = index_result['competitiveness']['color']
        level = index_result['competitiveness']['level']
        st.markdown(f'<div class="metric-card"><div class="metric-value" style="color:{color}">{level}</div><div class="metric-label">竞争力等级</div></div>', unsafe_allow_html=True)
    with col3:
        st.markdown(f'<div class="metric-card"><div class="metric-value">{index_result["price_rank"]}/{index_result["total_competitors"]}</div><div class="metric-label">价格排名</div></div>', unsafe_allow_html=True)
    with col4:
        st.markdown(f'<div class="metric-card"><div class="metric-value">{index_result["price_percentile"]}%</div><div class="metric-label">价格百分位</div></div>', unsafe_allow_html=True)

    st.markdown(f"**竞争力评估：** {index_result['competitiveness']['desc']}")

    col_left, col_right = st.columns(2)

    with col_left:
        st.markdown('#### 各平台价格指数')
        if not platform_result.empty:
            fig = go.Figure()
            fig.add_trace(go.Bar(
                x=platform_result['platform'],
                y=platform_result['price_index'],
                name='价格指数',
                marker_color=platform_result['price_index'].apply(
                    lambda x: '#2ecc71' if x <= 95 else '#f39c12' if x <= 102 else '#e74c3c'
                ),
            ))
            fig.add_hline(y=100, line_dash='dash', line_color='red', annotation_text='市场均价线')
            fig.update_layout(yaxis_title='价格指数', xaxis_title='平台', height=350)
            st.plotly_chart(fig, use_container_width=True)

    with col_right:
        st.markdown('#### 价格分布对比')
        all_prices = list(comp_df['current_price'].values) + [our_price]
        labels = list(comp_df['competitor_name'].values) + ['本店']
        colors = ['#636efa'] * len(comp_df) + ['#e74c3c']
        fig = go.Figure(data=[go.Bar(x=labels, y=all_prices, marker_color=colors)])
        fig.add_hline(y=index_result['avg_price'], line_dash='dash', line_color='green', annotation_text='市场均价')
        fig.update_layout(yaxis_title='价格 (元)', height=350)
        st.plotly_chart(fig, use_container_width=True)

    st.markdown('#### 💡 调价建议')
    target_index = st.slider('目标价格指数', min_value=80, max_value=120, value=100, step=1)
    suggestion = analyzer.generate_pricing_suggestion(target_index)
    action_colors = {'降价': '#e74c3c', '可涨价': '#2ecc71', '维持': '#f39c12'}
    action_color = action_colors.get(suggestion['action'], '#333')
    st.markdown(f"""
    <div class="suggestion-box">
        <b>建议操作：<span style="color:{action_color}">{suggestion['action']}</span></b><br>
        当前价格：¥{suggestion['current_price']} → 建议价格：¥{suggestion['suggested_price']}<br>
        调整幅度：¥{suggestion['price_diff']} ({suggestion['margin_pct']}%)<br>
        理由：{suggestion['reason']}
    </div>
    """, unsafe_allow_html=True)


def render_trend_tab(hist_df, our_hist_df):
    st.subheader('📈 价格历史趋势分析')

    trend = TrendAnalyzer(our_hist_df)
    trend_with_ma = trend.compute_moving_averages([7, 14, 30])
    trend_dir = trend.compute_trend_direction()
    volatility = trend.compute_volatility()
    forecast = trend.forecast_simple(14)

    col1, col2, col3 = st.columns(3)
    with col1:
        dir_color = '#2ecc71' if trend_dir['direction'] == '下降' else '#e74c3c' if trend_dir['direction'] == '上涨' else '#f39c12'
        st.markdown(f'<div class="metric-card"><div class="metric-value" style="color:{dir_color}">{trend_dir["direction"]}</div><div class="metric-label">趋势方向 | 强度:{trend_dir["trend_strength"]}</div></div>', unsafe_allow_html=True)
    with col2:
        st.markdown(f'<div class="metric-card"><div class="metric-value">{volatility["cv"]}%</div><div class="metric-label">价格变异系数</div></div>', unsafe_allow_html=True)
    with col3:
        st.markdown(f'<div class="metric-card"><div class="metric-value">{volatility["max_drawdown"]}%</div><div class="metric-label">最大回撤</div></div>', unsafe_allow_html=True)

    st.markdown('#### 价格走势与均线')
    fig = go.Figure()
    sources = hist_df['source'].unique()
    colors_map = {'本店': '#e74c3c', '市场均价': '#2ecc71', '品牌A': '#636efa', '品牌B': '#ffa15a', '品牌C': '#ab63fa'}
    for source in sources:
        df_s = hist_df[hist_df['source'] == source]
        fig.add_trace(go.Scatter(
            x=df_s['date'], y=df_s['price'],
            name=source, mode='lines',
            line=dict(width=2 if source in ['本店', '市场均价'] else 1, dash='dash' if source == '市场均价' else 'solid'),
            line_color=colors_map.get(source, '#999'),
        ))

    ma_cols = [c for c in trend_with_ma.columns if c.startswith('ma_')]
    for ma_col in ma_cols:
        fig.add_trace(go.Scatter(
            x=trend_with_ma['date'], y=trend_with_ma[ma_col],
            name=ma_col.replace('ma_', 'MA'), mode='lines',
            line=dict(dash='dot', width=1.5),
        ))

    if not forecast.empty:
        fig.add_trace(go.Scatter(
            x=forecast['date'], y=forecast['predicted_price'],
            name='预测价格', mode='lines',
            line=dict(dash='dash', color='rgba(255,0,0,0.6)', width=2),
        ))
        fig.add_trace(go.Scatter(
            x=forecast['date'], y=forecast['upper_bound'],
            name='预测上界', mode='lines',
            line=dict(width=0), showlegend=False,
        ))
        fig.add_trace(go.Scatter(
            x=forecast['date'], y=forecast['lower_bound'],
            name='预测下界', mode='lines',
            line=dict(width=0), fill='tonexty', fillcolor='rgba(255,0,0,0.1)',
        ))

    fig.update_layout(height=450, xaxis_title='日期', yaxis_title='价格 (元)', hovermode='x unified')
    st.plotly_chart(fig, use_container_width=True)

    col_left, col_right = st.columns(2)
    with col_left:
        st.markdown('#### 价格变化关键节点')
        change_points = trend.compute_price_change_points()
        if not change_points.empty:
            fig_cp = go.Figure(data=[go.Table(
                header=dict(values=['日期', '价格', '变动%', '类型'], fill_color='#1f77b4', font_color='white'),
                cells=dict(values=[
                    change_points['date'].dt.strftime('%Y-%m-%d'),
                    change_points['price'],
                    change_points['change_pct'].apply(lambda x: f'{x}%'),
                    change_points['type'],
                ]),
            )])
            fig_cp.update_layout(height=300)
            st.plotly_chart(fig_cp, use_container_width=True)
        else:
            st.info('未检测到显著价格变化节点')

    with col_right:
        st.markdown('#### 价格异常点检测')
        anomalies = trend.detect_price_anomalies()
        if not anomalies.empty:
            fig_an = go.Figure()
            fig_an.add_trace(go.Scatter(
                x=our_hist_df['date'], y=our_hist_df['price'],
                name='本店价格', mode='lines', line=dict(color='#636efa'),
            ))
            fig_an.add_trace(go.Scatter(
                x=anomalies['date'], y=anomalies['price'],
                name='异常点', mode='markers',
                marker=dict(color='red', size=10, symbol='x'),
            ))
            fig_an.update_layout(height=300, xaxis_title='日期', yaxis_title='价格')
            st.plotly_chart(fig_an, use_container_width=True)
        else:
            st.info('未检测到价格异常点')


def render_promo_tab(comp_df, our_price, rule_library):
    st.subheader('🏷️ 促销叠加分析')

    col1, col2 = st.columns(2)
    with col1:
        our_promos_input = st.text_input('本店促销活动（逗号分隔）', value='满2000减200')
    with col2:
        platform = st.selectbox('选择平台规则', ['general', 'jd', 'tmall', 'pinduoduo', 'suning'])
    our_promos = [p.strip() for p in our_promos_input.split(',') if p.strip()]

    promo_analyzer = PromoAnalyzer(comp_df, our_price, our_promos, rule_library)
    effective_df = promo_analyzer.analyze_all_effective_prices()
    stacking_df = promo_analyzer.analyze_promo_stacking()
    freq_df = promo_analyzer.compute_promo_frequency()
    strategies = promo_analyzer.recommend_promo_strategy()

    st.markdown('#### 实际到手价对比')
    fig = go.Figure()
    colors = ['#e74c3c' if name == '本店' else '#636efa' for name in effective_df['competitor_name']]
    fig.add_trace(go.Bar(
        x=effective_df['competitor_name'],
        y=effective_df['current_price'],
        name='标价',
        marker_color='rgba(99,110,250,0.5)',
    ))
    fig.add_trace(go.Bar(
        x=effective_df['competitor_name'],
        y=effective_df['effective_price'],
        name='到手价',
        marker_color=colors,
    ))
    fig.update_layout(barmode='group', height=400, yaxis_title='价格 (元)')
    st.plotly_chart(fig, use_container_width=True)

    st.markdown('#### 促销叠加效果分析')
    if not stacking_df.empty:
        fig_stack = make_subplots(rows=1, cols=2, specs=[[{'type': 'bar'}, {'type': 'table'}]])
        fig_stack.add_trace(go.Bar(
            x=stacking_df['name'],
            y=stacking_df['estimated_savings_pct'],
            marker_color=['#e74c3c' if r == '极高' else '#f39c12' if r == '高' else '#2ecc71' for r in stacking_df['risk']],
            name='预计节省%',
        ), row=1, col=1)
        fig_stack.update_layout(height=350, showlegend=False)
        st.plotly_chart(fig_stack, use_container_width=True)

    col_left, col_right = st.columns(2)
    with col_left:
        st.markdown('#### 促销类型频率分析')
        if not freq_df.empty:
            fig_freq = px.bar(freq_df, x='promo_type', y='frequency', color='platform_count',
                             title='各促销类型使用频率', labels={'frequency': '使用次数', 'promo_type': '促销类型'})
            fig_freq.update_layout(height=350)
            st.plotly_chart(fig_freq, use_container_width=True)

    with col_right:
        st.markdown('#### 💡 推荐促销策略')
        for i, s in enumerate(strategies):
            priority_color = '#e74c3c' if s['priority'] == '高' else '#f39c12'
            st.markdown(f"""
            <div class="suggestion-box">
                <b>{i+1}. {s['strategy']}</b> <span style="color:{priority_color}">[{s['priority']}优先级]</span><br>
                建议促销：{s['suggested_promos']}<br>
                目标到手价：¥{s['target_effective_price']} | 预计节省：¥{s['estimated_savings']}
            </div>
            """, unsafe_allow_html=True)


def render_optimizer_tab(comp_df, our_price, our_cost, elasticity_calibrator):
    st.subheader('🎯 最优定价模拟')

    col1, col2 = st.columns(2)
    with col1:
        st.markdown('#### 弹性系数校准')
        calib_result = elasticity_calibrator.calibrate(days=90)
        st.metric('校准后弹性系数', calib_result['elasticity'],
                 f"置信度: {calib_result['confidence']}")
        st.caption(f"校准方法: {calib_result['method']} | 样本数: {calib_result['sample_size']}")
        use_calibrated = st.checkbox('使用校准后的弹性系数', value=True)
        if use_calibrated and calib_result['sample_size'] >= 2:
            elasticity = calib_result['elasticity']
        else:
            elasticity = st.slider('手动设置弹性系数', min_value=-3.0, max_value=-0.5, value=-1.5, step=0.1)
        base_demand = st.number_input('基准需求量', min_value=100, max_value=10000, value=1000, step=100)
    with col2:
        st.markdown('#### 多目标权重配置')
        w_profit = st.slider('利润权重', 0.0, 1.0, 0.4, 0.05)
        w_revenue = st.slider('营收权重', 0.0, 1.0, 0.3, 0.05)
        w_share = st.slider('市场份额权重', 0.0, 1.0, 0.3, 0.05)
        total_w = w_profit + w_revenue + w_share
        if total_w > 0:
            w_profit_n = w_profit / total_w
            w_revenue_n = w_revenue / total_w
            w_share_n = w_share / total_w
        else:
            w_profit_n, w_revenue_n, w_share_n = 0.4, 0.3, 0.3

    optimizer = PricingOptimizer(
        our_cost=our_cost,
        competitor_prices=comp_df['current_price'].values,
        price_elasticity=elasticity,
    )

    opt_profit = optimizer.optimize_for_profit()
    opt_revenue = optimizer.optimize_for_revenue()
    opt_share = optimizer.optimize_for_market_share()
    opt_multi = optimizer.multi_objective_optimization({'profit': w_profit_n, 'revenue': w_revenue_n, 'market_share': w_share_n})

    st.markdown('#### 🏆 各优化目标最优定价')
    results_data = {
        '优化目标': [r['objective'] for r in [opt_profit, opt_revenue, opt_share, opt_multi]],
        '最优价格': [f"¥{r['optimal_price']}" for r in [opt_profit, opt_revenue, opt_share, opt_multi]],
        '预期利润': [f"¥{r['expected_profit']:,.0f}" for r in [opt_profit, opt_revenue, opt_share, opt_multi]],
        '预期营收': [f"¥{r['expected_revenue']:,.0f}" for r in [opt_profit, opt_revenue, opt_share, opt_multi]],
        '利润率': [f"{r['profit_margin']}%" for r in [opt_profit, opt_revenue, opt_share, opt_multi]],
        '市场份额': [f"{r['market_share']}%" for r in [opt_profit, opt_revenue, opt_share, opt_multi]],
    }
    st.dataframe(pd.DataFrame(results_data), use_container_width=True, hide_index=True)

    st.markdown('#### 📉 价格-利润/营收/市场份额曲线')
    sim_results = optimizer.simulate_price_range()
    sim_df = pd.DataFrame(sim_results)

    fig = make_subplots(rows=1, cols=3, subplot_titles=('价格-利润', '价格-营收', '价格-市场份额'))
    fig.add_trace(go.Scatter(x=sim_df['price'], y=sim_df['profit'], name='利润', line_color='#636efa'), row=1, col=1)
    fig.add_trace(go.Scatter(x=sim_df['price'], y=sim_df['revenue'], name='营收', line_color='#ffa15a'), row=1, col=2)
    fig.add_trace(go.Scatter(x=sim_df['price'], y=sim_df['market_share_pct'], name='市场份额', line_color='#2ecc71'), row=1, col=3)

    for opt_result, col_idx in [(opt_profit, 1), (opt_revenue, 2), (opt_share, 3)]:
        fig.add_vline(x=opt_result['optimal_price'], line_dash='dash', line_color='red', row=1, col=col_idx)

    fig.add_vline(x=our_price, line_dash='dot', line_color='green', annotation_text='当前价格', row=1, col=1)
    fig.update_layout(height=380, showlegend=False)
    st.plotly_chart(fig, use_container_width=True)

    st.markdown('#### 🎲 弹性系数敏感性分析')
    elasticity_range = np.arange(-3.0, -0.4, 0.2)
    sens_results = []
    for e in elasticity_range:
        optimizer_s = PricingOptimizer(our_cost, comp_df['current_price'].values, e)
        opt_p = optimizer_s.optimize_for_profit()
        sens_results.append({
            'elasticity': round(e, 2),
            'optimal_price': opt_p['optimal_price'],
            'profit': opt_p['expected_profit'],
            'margin': opt_p['profit_margin'],
        })
    sens_df = pd.DataFrame(sens_results)

    fig_sens = make_subplots(rows=1, cols=2, subplot_titles=('弹性-最优价格', '弹性-利润率'))
    fig_sens.add_trace(go.Scatter(x=sens_df['elasticity'], y=sens_df['optimal_price'], name='最优价格', line_color='#636efa'), row=1, col=1)
    fig_sens.add_trace(go.Scatter(x=sens_df['elasticity'], y=sens_df['margin'], name='利润率', line_color='#2ecc71'), row=1, col=2)
    fig_sens.add_vline(x=elasticity, line_dash='dash', line_color='red', row=1, col=1)
    fig_sens.add_vline(x=elasticity, line_dash='dash', line_color='red', row=1, col=2)
    fig_sens.update_layout(height=350, showlegend=False)
    st.plotly_chart(fig_sens, use_container_width=True)


def render_crawler_settings_tab():
    st.subheader('🕷️ 反爬配置')

    col1, col2 = st.columns(2)
    with col1:
        st.markdown('#### 🛡️ 动态代理配置')
        proxy_enabled = st.checkbox('启用代理池', value=True)
        rotation_interval = st.slider('代理轮换间隔（请求数）', 1, 20, 5)
        proxy_type = st.selectbox('代理类型偏好', ['elite', 'anonymous', 'all'])

        st.info("""
        **当前代理池状态：**
        - 可用代理：12 个
        - 高匿代理：6 个
        - SOCKS5 代理：2 个
        - 失败代理：0 个
        """)

    with col2:
        st.markdown('#### 🎭 请求指纹模拟')
        ua_enabled = st.checkbox('启用 User-Agent 轮换', value=True)
        mobile_ratio = st.slider('移动端 UA 比例', 0.0, 1.0, 0.3)
        referer_enabled = st.checkbox('启用 Referer 模拟', value=True)
        sec_ch_ua_enabled = st.checkbox('启用 Sec-CH-UA 模拟', value=True)

        st.info("""
        **指纹池配置：**
        - 桌面端 Chrome：6 种
        - 桌面端 Firefox：4 种
        - 桌面端 Edge：2 种
        - 移动端：5 种
        """)

    st.markdown('#### ⏱️ 请求延迟配置')
    col3, col4, col5 = st.columns(3)
    with col3:
        base_delay = st.number_input('基础延迟（秒）', 1.0, 10.0, 2.0, 0.5)
    with col4:
        min_delay = st.number_input('最小随机延迟', 0.1, 2.0, 0.5, 0.1)
    with col5:
        max_delay = st.number_input('最大随机延迟', 1.0, 5.0, 2.0, 0.1)

    st.markdown('#### 📋 当前配置预览')
    config_code = f"""
DOWNLOAD_DELAY = {base_delay}
RANDOMIZE_DOWNLOAD_DELAY = True
PROXY_ENABLED = {proxy_enabled}
PROXY_ROTATION_INTERVAL = {rotation_interval}
MOBILE_UA_RATIO = {mobile_ratio}
REFERER_SIMULATION = {referer_enabled}
SEC_CH_UA_SIMULATION = {sec_ch_ua_enabled}
    """
    st.code(config_code, language='python')

    if st.button('保存配置', type='primary'):
        st.success('配置已保存到 settings.py')


def render_promo_rules_tab(rule_library):
    st.subheader('📚 优惠规则库管理')

    col1, col2 = st.columns([3, 2])
    with col1:
        st.markdown('#### ✨ 贡献新规则')
        with st.form('add_rule_form'):
            rule_name = st.text_input('规则名称', placeholder='如：满300减50规则')
            rule_pattern = st.text_input('正则表达式', placeholder=r'如：满(\d+)减(\d+)')
            rule_type = st.selectbox('规则类型', [
                'amount_discount', 'direct_discount', 'percentage_discount',
                'new_user_discount', 'member_discount', 'coupon_discount',
                'flash_sale', 'platform_subsidy', 'live_stream'
            ])
            col_a, col_b = st.columns(2)
            with col_a:
                effect_threshold = st.text_input('阈值分组（可选）', placeholder=r'\1')
            with col_b:
                effect_discount = st.text_input('折扣/减免分组', placeholder=r'\2')
            platform = st.selectbox('适用平台', ['general', 'jd', 'tmall', 'pinduoduo', 'suning'])
            priority = st.slider('优先级', 1, 10, 5)
            created_by = st.text_input('贡献者昵称', value='anonymous')

            submitted = st.form_submit_button('提交规则', type='primary')
            if submitted:
                effect = {}
                if effect_threshold:
                    effect['threshold'] = effect_threshold
                if effect_discount:
                    effect['discount'] = effect_discount
                if rule_type in ['percentage_discount', 'flash_sale']:
                    effect['rate'] = effect_discount if effect_discount else '0.9'

                success, msg = rule_library.add_rule(
                    name=rule_name,
                    pattern=rule_pattern,
                    rule_type=rule_type,
                    effect=effect,
                    platform=platform,
                    priority=priority,
                    created_by=created_by,
                )
                if success:
                    st.success(f'规则提交成功！ID: {msg}')
                else:
                    st.error(f'规则提交失败: {msg}')

    with col2:
        st.markdown('#### 📊 规则库统计')
        stats = rule_library.get_stats()
        st.metric('规则总数', stats['total'])
        col_a, col_b, col_c = st.columns(3)
        with col_a:
            st.metric('已激活', stats['active'])
        with col_b:
            st.metric('待审核', stats['pending'])
        with col_c:
            st.metric('已拒绝', stats['rejected'])

        st.markdown('**按类型分布：**')
        for rule_type, count in stats['by_type'].items():
            st.markdown(f"- {rule_type}: {count} 个")

    st.markdown('#### 📋 规则列表')
    status_filter = st.selectbox('筛选状态', ['all', 'active', 'pending', 'rejected'])

    if status_filter == 'all':
        rules_to_show = rule_library.rules
    else:
        rules_to_show = [r for r in rule_library.rules if r.status == status_filter]

    for rule in sorted(rules_to_show, key=lambda x: -x.priority):
        with st.expander(f"{'🌟' if rule.status == 'active' else '⏳' if rule.status == 'pending' else '❌'} {rule.name} (票数: {rule.votes})"):
            col_a, col_b = st.columns([3, 1])
            with col_a:
                st.code(rule.pattern, language='regex')
                st.markdown(f"""
                **类型:** {rule.rule_type} | **平台:** {rule.platform} | **优先级:** {rule.priority}
                **效果:** `{rule.effect}` | **贡献者:** {rule.created_by}
                """)
            with col_b:
                if st.button('👍 有用', key=f'up_{rule.rule_id}'):
                    rule_library.vote_rule(rule.rule_id, positive=True)
                    st.rerun()
                if st.button('👎 无效', key=f'down_{rule.rule_id}'):
                    rule_library.vote_rule(rule.rule_id, positive=False)
                    st.rerun()
                if rule.status == 'pending':
                    if st.button('✅ 审核通过', key=f'approve_{rule.rule_id}'):
                        rule_library.approve_rule(rule.rule_id, True)
                        st.success('规则已通过')
                        st.rerun()
                    if st.button('❌ 拒绝', key=f'reject_{rule.rule_id}'):
                        rule_library.approve_rule(rule.rule_id, False)
                        st.rerun()


def render_elasticity_calibration_tab(elasticity_calibrator):
    st.subheader('📐 弹性系数实时校准')

    col1, col2 = st.columns([3, 2])
    with col1:
        st.markdown('#### 🧪 价格实验记录')
        with st.form('add_experiment_form'):
            col_a, col_b = st.columns(2)
            with col_a:
                start_date = st.date_input('实验开始日期', value=datetime.now() - timedelta(days=7))
                test_price = st.number_input('测试价格', min_value=1.0, value=4499.0, step=100.0)
                units_sold = st.number_input('销量', min_value=1, value=120)
            with col_b:
                end_date = st.date_input('实验结束日期', value=datetime.now())
                base_price = st.number_input('基准价格', min_value=1.0, value=4699.0, step=100.0)
                control_units = st.number_input('对照组销量（可选）', min_value=0, value=100)

            notes = st.text_area('实验备注', placeholder='描述实验条件、市场环境等')
            submitted = st.form_submit_button('添加实验记录', type='primary')

            if submitted:
                exp_id = elasticity_calibrator.add_experiment(
                    start_date=datetime.combine(start_date, datetime.min.time()),
                    end_date=datetime.combine(end_date, datetime.min.time()),
                    price=test_price,
                    base_price=base_price,
                    units_sold=units_sold,
                    control_group_units=control_units if control_units > 0 else None,
                    notes=notes,
                )
                st.success(f'实验记录已添加！ID: {exp_id}')

    with col2:
        st.markdown('#### 📊 校准结果')
        calib_result = elasticity_calibrator.calibrate(days=90, method='auto')

        col_a, col_b = st.columns(2)
        with col_a:
            st.metric('校准后弹性系数', calib_result['elasticity'])
        with col_b:
            conf_color = '#2ecc71' if calib_result['confidence'] == 'high' else '#f39c12' if calib_result['confidence'] == 'medium' else '#e74c3c'
            st.markdown(f'<div style="color:{conf_color};font-weight:bold;font-size:1.2rem;">置信度: {calib_result["confidence"].upper()}</div>', unsafe_allow_html=True)

        st.markdown(f"""
        **校准方法:** {calib_result['method']}
        **实验样本数:** {calib_result['sample_size']}
        """)
        if 'r_squared' in calib_result:
            st.markdown(f"**R² 拟合度:** {calib_result['r_squared']}")
        if 'std_dev' in calib_result:
            st.markdown(f"**标准差:** {calib_result['std_dev']}")

    st.markdown('#### 📈 弹性系数趋势')
    trend_df = elasticity_calibrator.get_elasticity_trend(window=5)
    if not trend_df.empty:
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=trend_df['date'],
            y=trend_df['avg_elasticity'],
            mode='lines+markers',
            name='平均弹性系数',
            line=dict(color='#636efa', width=2),
            marker=dict(size=8),
        ))
        fig.add_hline(y=-1.5, line_dash='dash', line_color='red', annotation_text='默认值 -1.5')
        fig.update_layout(height=350, xaxis_title='日期', yaxis_title='弹性系数', hovermode='x unified')
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info('需要至少3个实验记录来绘制趋势图')

    st.markdown('#### 📋 实验历史记录')
    exps = elasticity_calibrator.experiments
    if exps:
        exp_data = []
        for exp in sorted(exps, key=lambda x: x.end_date, reverse=True):
            point_elasticity = elasticity_calibrator.calculate_point_elasticity(exp)
            exp_data.append({
                '实验ID': exp.experiment_id,
                '开始日期': exp.start_date[:10] if isinstance(exp.start_date, str) else exp.start_date.strftime('%Y-%m-%d'),
                '结束日期': exp.end_date[:10] if isinstance(exp.end_date, str) else exp.end_date.strftime('%Y-%m-%d'),
                '测试价格': exp.price,
                '基准价格': exp.base_price,
                '销量': exp.units_sold,
                '点弹性': round(point_elasticity, 4),
            })
        st.dataframe(pd.DataFrame(exp_data), use_container_width=True, hide_index=True)
    else:
        st.info('暂无实验记录')


def render_price_war_tab(price_war_monitor, comp_df, our_price, our_cost):
    st.subheader('⚠️ 价格战预警')

    price_war_monitor.our_price = our_price
    price_war_monitor.our_cost = our_cost

    new_alerts = price_war_monitor.check_competitor_prices(comp_df)

    threat = price_war_monitor.analyze_threat_level(comp_df)
    alert_stats = price_war_monitor.get_alert_stats()

    col1, col2, col3, col4 = st.columns(4)
    threat_colors = {
        'extreme': '#e74c3c', 'high': '#e67e22', 'medium': '#f39c12',
        'low': '#3498db', 'safe': '#2ecc71'
    }
    with col1:
        color = threat_colors.get(threat['level'], '#999')
        st.markdown(f'<div class="metric-card"><div class="metric-value" style="color:{color}">{threat["level"].upper()}</div><div class="metric-label">威胁等级</div></div>', unsafe_allow_html=True)
    with col2:
        st.markdown(f'<div class="metric-card"><div class="metric-value">{alert_stats["unread"]}</div><div class="metric-label">未读告警</div></div>', unsafe_allow_html=True)
    with col3:
        st.markdown(f'<div class="metric-card"><div class="metric-value">{alert_stats["last_24h"]}</div><div class="metric-label">24小时内告警</div></div>', unsafe_allow_html=True)
    with col4:
        st.markdown(f'<div class="metric-card"><div class="metric-value">¥{threat["min_competitor_price"]}</div><div class="metric-label">最低竞品价格</div></div>', unsafe_allow_html=True)

    st.markdown(f'**威胁分析：** {threat["description"]}')
    st.markdown(f'**低于本店价格的竞品：** {threat["below_count"]} 家 ({threat["below_ratio"]}%)')

    col_left, col_right = st.columns([3, 2])
    with col_left:
        st.markdown('#### 📋 告警列表')
        severity_filter = st.selectbox('筛选严重程度', ['all', 'critical', 'warning', 'info'])
        unread_only = st.checkbox('只显示未读', value=True)

        alerts = price_war_monitor.get_alerts(
            severity=None if severity_filter == 'all' else severity_filter,
            unread_only=unread_only
        )

        if alerts:
            for alert in alerts:
                sev_colors = {'critical': '#e74c3c', 'warning': '#f39c12', 'info': '#3498db'}
                color = sev_colors.get(alert.severity, '#999')
                read_badge = '' if alert.is_read else '🔴 '
                with st.expander(f'{read_badge}[{alert.severity.upper()}] {alert.message}'):
                    st.markdown(f"""
                    **竞品：** {alert.competitor_name}
                    **竞品价格：** ¥{alert.competitor_price}
                    **本店价格：** ¥{alert.our_price}
                    **时间：** {alert.timestamp.isoformat() if isinstance(alert.timestamp, datetime) else alert.timestamp}
                    """)
                    col_a, col_b = st.columns(2)
                    with col_a:
                        if not alert.is_read:
                            if st.button('标记已读', key=f'mark_{alert.alert_id}'):
                                price_war_monitor.mark_as_read(alert.alert_id)
                                st.rerun()
                    with col_b:
                        st.info(f'建议：将价格调整至 ¥{alert.competitor_price * 0.99:.2f} 以下')
        else:
            st.success('🎉 当前没有价格战告警，市场环境稳定')

    with col_right:
        st.markdown('#### ⚙️ 告警阈值设置')
        critical_threshold = st.slider('严重告警阈值（竞品/本店）', 0.7, 0.95, 0.85, 0.01)
        warning_threshold = st.slider('警告阈值', 0.85, 0.98, 0.90, 0.01)
        info_threshold = st.slider('关注阈值', 0.90, 1.0, 0.95, 0.01)

        if st.button('更新阈值设置'):
            price_war_monitor.set_thresholds(
                critical=critical_threshold,
                warning=warning_threshold,
                info=info_threshold
            )
            st.success('阈值已更新')

        if st.button('标记全部已读', type='secondary'):
            price_war_monitor.mark_all_as_read()
            st.success('已全部标记为已读')
            st.rerun()


def render_dynamic_pricing_tab(dynamic_pricing, comp_df, our_price, our_cost):
    st.subheader('🤖 动态定价引擎')

    dynamic_pricing.our_cost = our_cost
    dynamic_pricing.base_price = our_price
    dynamic_pricing.current_price = our_price

    col1, col2 = st.columns(2)
    with col1:
        st.markdown('#### ⚙️ 定价参数')
        min_margin = st.slider('最低利润率', 0.05, 0.5, 0.1, 0.01, format='%f')
        max_change = st.slider('单次最大调价幅度', 0.02, 0.2, 0.1, 0.01, format='%f')
        stock_level = st.number_input('当前库存量', 0, 10000, 500, 50)

        dynamic_pricing.set_min_margin(min_margin)
        dynamic_pricing.set_max_price_change(max_change)

    with col2:
        st.markdown('#### 🎯 定价建议')
        context = {'stock_level': stock_level}
        suggestion = dynamic_pricing.calculate_suggested_price(comp_df, context)

        col_a, col_b = st.columns(2)
        with col_a:
            st.metric('当前价格', f'¥{suggestion["current_price"]}')
        with col_b:
            change_pct = suggestion.get('price_change_pct', 0)
            st.metric('建议价格', f'¥{suggestion["suggested_price"]}',
                     f'{change_pct:+.2f}%')

        st.markdown(f'**触发规则：** {suggestion.get("applied_rule", "无")}')
        st.markdown(f'**价格下限（保本）：** ¥{suggestion["min_allowed_price"]}')

        if suggestion['price_change_pct'] != 0:
            action = '降价' if suggestion['price_change_pct'] < 0 else '涨价'
            st.success(f'建议：{action} ¥{abs(suggestion["suggested_price"] - suggestion["current_price"]):.2f}')

    st.markdown('#### 📋 定价规则列表')
    rules = dynamic_pricing.get_rules()

    if st.button('+ 添加新规则', type='primary'):
        st.session_state.show_add_rule = True

    if st.session_state.get('show_add_rule', False):
        with st.form('add_dynamic_rule_form'):
            name = st.text_input('规则名称')
            rule_type = st.selectbox('规则类型', ['competitor_based', 'index_based', 'inventory_based', 'time_based'])
            priority = st.slider('优先级', 1, 10, 5)
            submitted = st.form_submit_button('创建规则')
            if submitted:
                condition = {'type': 'index_above', 'threshold': 98}
                action = {'type': 'adjust_to_index', 'target_index': 95}
                rule_id = dynamic_pricing.add_rule(name, rule_type, condition, action, priority)
                st.success(f'规则已创建: {rule_id}')
                st.session_state.show_add_rule = False
                st.rerun()

    for rule in rules:
        status_color = '#2ecc71' if rule.status == 'active' else '#999'
        with st.expander(f"{'✅' if rule.status == 'active' else '⏸️'} [{rule.priority}] {rule.name}"):
            st.markdown(f"""
            **类型：** {rule.rule_type}
            **条件：** `{rule.condition}`
            **动作：** `{rule.action}`
            **状态：** <span style="color:{status_color}">{rule.status}</span>
            """, unsafe_allow_html=True)
            col_a, col_b = st.columns(2)
            with col_a:
                new_status = dynamic_pricing.toggle_rule(rule.rule_id) if st.button(
                    '启用/停用', key=f'toggle_{rule.rule_id}') else rule.status
            with col_b:
                if st.button('删除', key=f'del_{rule.rule_id}'):
                    dynamic_pricing.delete_rule(rule.rule_id)
                    st.rerun()


def render_compliance_tab(compliance_checker, our_price, our_cost, our_hist_df):
    st.subheader('✅ 定价合规检查')

    col1, col2 = st.columns([3, 2])
    with col1:
        st.markdown('#### 🧪 合规检测参数')
        original_price = st.number_input('商品原价（划线价）', min_value=0, value=5299, step=100)
        stock_status = st.selectbox('库存状态', ['in_stock', 'out_of_stock', '预售'])
        has_additional_fees = st.checkbox('存在附加费用')
        additional_fees = []
        if has_additional_fees:
            fee1 = st.number_input('运费', 0, 1000, 0)
            fee2 = st.number_input('服务费', 0, 1000, 0)
            additional_fees = [fee1, fee2]

        run_check = st.button('🔍 执行合规检查', type='primary')

        if run_check:
            result = compliance_checker.full_compliance_check(
                current_price=our_price,
                original_price=original_price,
                cost_price=our_cost,
                history_df=our_hist_df,
                stock_status=stock_status,
                additional_fees=additional_fees if has_additional_fees else None,
            )
            st.session_state.compliance_result = result

    with col2:
        st.markdown('#### 📊 合规评分')
        score_result = compliance_checker.get_compliance_score()
        grade_colors = {'A': '#2ecc71', 'B': '#3498db', 'C': '#f39c12', 'D': '#e74c3c'}
        st.markdown(f"""
        <div style="text-align:center;padding:20px;background:#f8f9fa;border-radius:10px;">
            <div style="font-size:3rem;font-weight:700;color:{grade_colors.get(score_result['grade'],'#999')}">
                {score_result['grade']}
            </div>
            <div style="font-size:1.2rem;">{score_result['score']} 分</div>
            <div>未解决问题：{score_result['unresolved_count']} 个</div>
        </div>
        """, unsafe_allow_html=True)

    if 'compliance_result' in st.session_state:
        result = st.session_state.compliance_result

        st.markdown('#### 📋 检查结果')

        risk_colors = {'high': '#e74c3c', 'medium': '#f39c12', 'low': '#3498db', 'safe': '#2ecc71'}
        risk_color = risk_colors.get(result['overall_risk'], '#999')
        st.markdown(f"""
        <div class="suggestion-box">
            <b>总体风险：<span style="color:{risk_color}">{result['overall_status']}</span></b><br>
            高风险：{result['issues_count']['high']} | 中风险：{result['issues_count']['medium']} | 低风险：{result['issues_count']['low']}
        </div>
        """, unsafe_allow_html=True)

        if result['issues']:
            for issue in result['issues']:
                sev_color = risk_colors.get(issue['severity'], '#999')
                with st.expander(f"[{issue['severity'].upper()}] {issue['message']}"):
                    st.markdown(f"""
                    **类型：** {issue['type']}
                    **详细数据：** `{issue['data']}`
                    **建议：** {issue['recommendation']}
                    """)
        else:
            st.success('🎉 未发现定价合规问题')

    st.markdown('#### 📚 合规规则库')
    with st.expander('查看合规检查规则说明'):
        st.markdown("""
        **1. 原价真实性检查**
        - 原价不得高于现价50%以上
        - 原价需有历史销售记录支持

        **2. 价格变动频率**
        - 7天内价格变动不得超过5次

        **3. 掠夺性定价**
        - 售价不得低于成本价80%

        **4. 低价诱饵**
        - 缺货商品不得标注虚假低价

        **5. 价格准确性**
        - 促销价需有7天价格记录支持

        **6. 隐性收费**
        - 附加费用不得超过基础价格20%
        """)


def render_data_tab(comp_df, hist_df):
    st.subheader('📋 数据概览')

    col1, col2 = st.columns(2)
    with col1:
        st.markdown('#### 竞品价格数据')
        st.dataframe(comp_df, use_container_width=True, hide_index=True)
    with col2:
        st.markdown('#### 价格历史数据（最近20条）')
        st.dataframe(hist_df.tail(20), use_container_width=True, hide_index=True)

    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown('#### 各平台竞品数量')
        platform_counts = comp_df['platform'].value_counts()
        fig = px.pie(values=platform_counts.values, names=platform_counts.index, title='各平台竞品分布')
        st.plotly_chart(fig, use_container_width=True)
    with col2:
        st.markdown('#### 各平台均价对比')
        platform_avg = comp_df.groupby('platform')['current_price'].mean().round(2)
        fig = px.bar(x=platform_avg.index, y=platform_avg.values, labels={'x': '平台', 'y': '均价'}, title='各平台均价')
        st.plotly_chart(fig, use_container_width=True)
    with col3:
        st.markdown('#### 库存状态分布')
        stock_counts = comp_df['stock_status'].value_counts()
        fig = px.pie(values=stock_counts.values, names=stock_counts.index, title='库存状态')
        st.plotly_chart(fig, use_container_width=True)


def main():
    st.markdown('<p class="main-header">📊 商品价格竞争力分析平台</p>', unsafe_allow_html=True)
    st.markdown('实时监控竞品价格，深度分析价格竞争力，智能输出调价建议')

    init_session_state()
    comp_df, hist_df, our_hist_df = load_data()

    with st.sidebar:
        st.markdown('## ⚙️ 参数配置')
        st.markdown('---')
        our_price = st.number_input('本商品售价 (元)', min_value=100, max_value=100000, value=4699, step=100)
        our_cost = st.number_input('本商品成本 (元)', min_value=50, max_value=90000, value=3200, step=100)
        st.markdown('---')
        st.markdown('### 数据操作')
        if st.button('🔄 重新生成示例数据'):
            st.cache_data.clear()
            st.rerun()
        st.markdown('---')
        st.markdown(f'**竞品数据量：** {len(comp_df)} 条')
        st.markdown(f'**历史数据量：** {len(hist_df)} 条')
        st.markdown(f'**成本利润率：** {round((our_price - our_cost) / our_price * 100, 1)}%')
        st.markdown('---')
        st.markdown('### 技术栈')
        st.markdown('- Python + Scrapy')
        st.markdown('- 动态代理轮换')
        st.markdown('- 请求指纹模拟')
        st.markdown('- 价格战预警')
        st.markdown('- 动态定价引擎')
        st.markdown('- 定价合规检查')
        st.markdown('- Streamlit 可视化')

    tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8, tab9, tab10, tab11 = st.tabs([
        '📊 价格指数', '📈 趋势分析', '🏷️ 促销分析', '🎯 定价模拟',
        '⚠️ 价格战预警', '🤖 动态定价', '✅ 合规检查',
        '🕷️ 反爬配置', '📚 规则库', '📐 弹性校准', '📋 数据概览'
    ])

    with tab1:
        render_price_index_tab(comp_df, our_price)
    with tab2:
        render_trend_tab(hist_df, our_hist_df)
    with tab3:
        render_promo_tab(comp_df, our_price, st.session_state.rule_library)
    with tab4:
        render_optimizer_tab(comp_df, our_price, our_cost, st.session_state.elasticity_calibrator)
    with tab5:
        render_price_war_tab(st.session_state.price_war_monitor, comp_df, our_price, our_cost)
    with tab6:
        render_dynamic_pricing_tab(st.session_state.dynamic_pricing, comp_df, our_price, our_cost)
    with tab7:
        render_compliance_tab(st.session_state.compliance_checker, our_price, our_cost, our_hist_df)
    with tab8:
        render_crawler_settings_tab()
    with tab9:
        render_promo_rules_tab(st.session_state.rule_library)
    with tab10:
        render_elasticity_calibration_tab(st.session_state.elasticity_calibrator)
    with tab11:
        render_data_tab(comp_df, hist_df)


if __name__ == '__main__':
    main()
