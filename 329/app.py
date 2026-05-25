import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from data_generator import (
    generate_historical_sales_data,
    preprocess_data,
    create_price_bins,
    generate_multi_product_sales_data,
    preprocess_multi_product_data
)
from logit_elasticity_model import PriceElasticityModel
from optimal_pricing import OptimalPricing
from promotion_simulation import PromotionSimulator
from cross_elasticity import CrossElasticityAnalyzer
from dynamic_pricing import DynamicPricingSimulator, PricingStrategy, PricingStrategyType, generate_time_based_pattern
from price_threshold import PriceThresholdDetector
from visualization import (
    plot_price_sales_scatter,
    plot_elasticity_curve,
    plot_feature_importance,
    plot_sales_impact,
    plot_promotion_simulation,
    plot_time_series,
    plot_heatmap_correlation,
    plot_bootstrap_distribution,
    plot_post_promotion_effect,
    plot_promotion_timeline,
    plot_cross_elasticity_heatmap,
    plot_cross_elasticity_impact,
    plot_dynamic_pricing_comparison,
    plot_pricing_timeline,
    plot_price_thresholds,
    plot_price_segments_comparison
)

st.set_page_config(
    page_title="商品价格弹性分析系统",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        margin-bottom: 1rem;
    }
    .section-header {
        font-size: 1.5rem;
        font-weight: bold;
        color: #2ca02c;
        margin-top: 2rem;
        margin-bottom: 1rem;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        text-align: center;
    }
    .positive-change {
        color: #2ca02c;
        font-weight: bold;
    }
    .negative-change {
        color: #d62728;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)

@st.cache_data(show_spinner=True)
def load_and_preprocess_data(base_price, base_demand, price_elasticity, n_periods):
    df_raw = generate_historical_sales_data(
        base_price=base_price,
        base_demand=base_demand,
        price_elasticity=price_elasticity,
        n_periods=n_periods
    )
    df_processed = preprocess_data(df_raw)
    df_binned, bin_stats = create_price_bins(df_processed)
    return df_raw, df_processed, df_binned, bin_stats

@st.cache_resource(show_spinner=True)
def train_model(df_processed, threshold_quantile, feature_set, decouple_promotion, n_bootstrap, confidence_level):
    model = PriceElasticityModel(
        threshold_quantile=threshold_quantile,
        decouple_promotion=decouple_promotion,
        n_bootstrap=n_bootstrap,
        confidence_level=confidence_level
    )
    results = model.fit(df_processed, feature_set=feature_set)
    elasticity_df = model.calculate_price_elasticity(df_processed)
    elasticity_summary = model.get_elasticity_summary(elasticity_df)
    return model, results, elasticity_df, elasticity_summary

@st.cache_resource(show_spinner=True)
def get_optimal_pricing(_model, df_processed, variable_cost, fixed_cost):
    return OptimalPricing(_model, df_processed, variable_cost, fixed_cost)

@st.cache_resource(show_spinner=True)
def get_promotion_simulator(_model, df_processed, base_price, variable_cost):
    return PromotionSimulator(_model, df_processed, base_price, variable_cost)

@st.cache_data(show_spinner=True)
def load_multi_product_data(n_products, n_periods):
    df_multi_raw = generate_multi_product_sales_data(
        n_products=n_products,
        n_periods=n_periods
    )
    df_multi_processed = preprocess_multi_product_data(df_multi_raw)
    return df_multi_raw, df_multi_processed

@st.cache_resource(show_spinner=True)
def train_cross_elasticity(df_multi_processed, n_bootstrap, confidence_level):
    analyzer = CrossElasticityAnalyzer(
        n_bootstrap=n_bootstrap,
        confidence_level=confidence_level
    )
    cross_results = analyzer.fit(df_multi_processed)
    return analyzer, cross_results

@st.cache_resource(show_spinner=True)
def get_dynamic_pricing_simulator(_model, _cross_analyzer, variable_cost, fixed_cost):
    return DynamicPricingSimulator(
        product_model=_model,
        cross_analyzer=_cross_analyzer,
        variable_cost=variable_cost,
        fixed_cost=fixed_cost
    )

@st.cache_resource(show_spinner=True)
def get_price_threshold_detector(n_clusters):
    return PriceThresholdDetector(n_clusters=n_clusters)

with st.sidebar:
    st.title("⚙️ 模型参数设置")
    
    st.subheader("数据生成参数")
    base_price = st.slider("基础价格 (元)", min_value=10.0, max_value=500.0, value=100.0, step=10.0)
    base_demand = st.slider("基础需求量", min_value=100, max_value=2000, value=500, step=50)
    true_elasticity = st.slider("真实价格弹性系数", min_value=-5.0, max_value=-0.5, value=-2.5, step=0.1)
    n_periods = st.slider("历史数据天数", min_value=90, max_value=730, value=365, step=30)
    n_products = st.slider("交叉弹性分析商品数", min_value=3, max_value=10, value=5, step=1)
    
    st.subheader("模型训练参数")
    threshold_quantile = st.slider("高销量阈值分位数", min_value=0.3, max_value=0.7, value=0.5, step=0.05)
    feature_set = st.selectbox("特征集选择", ["full", "base", "price_only"], index=0,
                               format_func=lambda x: {"full": "全部特征", "base": "基础特征", "price_only": "仅价格特征"}[x])
    decouple_promotion = st.checkbox("解耦价格与促销影响", value=True)
    
    st.subheader("Bootstrap置信区间参数")
    n_bootstrap = st.slider("Bootstrap迭代次数", min_value=100, max_value=2000, value=1000, step=100)
    confidence_level = st.slider("置信水平", min_value=0.80, max_value=0.99, value=0.95, step=0.01)
    
    st.subheader("价格阈值检测参数")
    n_clusters = st.slider("价格区间聚类数", min_value=2, max_value=8, value=4, step=1)
    
    st.subheader("促销延后效应参数")
    post_promo_halflife = st.slider("促销后需求半衰期(天)", min_value=1, max_value=14, value=3, step=1)
    
    st.subheader("价格调整模拟")
    price_change_pct = st.slider("价格调整幅度 (%)", min_value=-30.0, max_value=30.0, value=-10.0, step=1.0) / 100
    
    simulation_days = 90
    
    regenerate = st.button("🔄 重新生成数据并训练模型", type="primary")

if regenerate or 'df_raw' not in st.session_state:
    with st.spinner("正在生成数据并训练模型（Bootstrap采样可能需要10-15秒）..."):
        df_raw, df_processed, df_binned, bin_stats = load_and_preprocess_data(
            base_price, base_demand, true_elasticity, n_periods
        )
        model, results, elasticity_df, elasticity_summary = train_model(
            df_processed, threshold_quantile, feature_set, decouple_promotion, n_bootstrap, confidence_level
        )
        optimal_pricing = get_optimal_pricing(model, df_processed, variable_cost, fixed_cost)
        promotion_simulator = get_promotion_simulator(model, df_processed, base_price, variable_cost)
        promotion_simulator.post_promo_halflife = post_promo_halflife
        
        df_multi_raw, df_multi_processed = load_multi_product_data(n_products, n_periods)
        cross_analyzer, cross_results = train_cross_elasticity(
            df_multi_processed, max(100, n_bootstrap // 2), confidence_level
        )
        
        dynamic_simulator = get_dynamic_pricing_simulator(model, cross_analyzer, variable_cost, fixed_cost)
        
        threshold_detector = get_price_threshold_detector(n_clusters)
        threshold_results = threshold_detector.detect_thresholds(df_processed)
        price_segments = threshold_detector.price_segments
        
        st.session_state.df_raw = df_raw
        st.session_state.df_processed = df_processed
        st.session_state.df_binned = df_binned
        st.session_state.bin_stats = bin_stats
        st.session_state.model = model
        st.session_state.results = results
        st.session_state.elasticity_df = elasticity_df
        st.session_state.elasticity_summary = elasticity_summary
        st.session_state.optimal_pricing = optimal_pricing
        st.session_state.promotion_simulator = promotion_simulator
        st.session_state.decouple_promotion = decouple_promotion
        st.session_state.n_bootstrap = n_bootstrap
        st.session_state.confidence_level = confidence_level
        st.session_state.post_promo_halflife = post_promo_halflife
        st.session_state.df_multi_raw = df_multi_raw
        st.session_state.df_multi_processed = df_multi_processed
        st.session_state.cross_analyzer = cross_analyzer
        st.session_state.cross_results = cross_results
        st.session_state.dynamic_simulator = dynamic_simulator
        st.session_state.threshold_detector = threshold_detector
        st.session_state.threshold_results = threshold_results
        st.session_state.price_segments = price_segments
else:
    df_raw = st.session_state.df_raw
    df_processed = st.session_state.df_processed
    df_binned = st.session_state.df_binned
    bin_stats = st.session_state.bin_stats
    model = st.session_state.model
    results = st.session_state.results
    elasticity_df = st.session_state.elasticity_df
    elasticity_summary = st.session_state.elasticity_summary
    optimal_pricing = st.session_state.optimal_pricing
    promotion_simulator = st.session_state.promotion_simulator
    if hasattr(st.session_state, 'post_promo_halflife'):
        promotion_simulator.post_promo_halflife = st.session_state.post_promo_halflife
    df_multi_raw = st.session_state.df_multi_raw
    df_multi_processed = st.session_state.df_multi_processed
    cross_analyzer = st.session_state.cross_analyzer
    cross_results = st.session_state.cross_results
    dynamic_simulator = st.session_state.dynamic_simulator
    threshold_detector = st.session_state.threshold_detector
    threshold_results = st.session_state.threshold_results
    price_segments = st.session_state.price_segments

st.markdown('<div class="main-header">📊 商品价格弹性分析系统</div>', unsafe_allow_html=True)
st.markdown("基于Logit模型的价格弹性分析、最优定价建议与促销模拟预测平台")

tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8, tab9, tab10 = st.tabs([
    "📈 数据概览", 
    "🎯 价格弹性分析", 
    "💰 最优定价建议", 
    "🎁 促销模拟预测", 
    "📊 模型诊断",
    "🔍 涨价/降价影响分析",
    "⏳ 促销延后效应",
    "🔗 交叉弹性分析",
    "⚡ 动态定价模拟",
    "🎯 价格阈值检测"
])

with tab1:
    st.markdown('<div class="section-header">📈 历史销售数据概览</div>', unsafe_allow_html=True)
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("平均价格", f"¥{df_raw['effective_price'].mean():.2f}")
    with col2:
        st.metric("平均销量", f"{df_raw['sales_quantity'].mean():,.0f}")
    with col3:
        st.metric("平均收入", f"¥{df_raw['revenue'].mean():,.0f}")
    with col4:
        st.metric("促销占比", f"{df_raw['is_promotion'].mean()*100:.1f}%")
    
    st.plotly_chart(plot_time_series(df_raw), use_container_width=True)
    
    col5, col6 = st.columns(2)
    with col5:
        st.plotly_chart(plot_price_sales_scatter(df_processed), use_container_width=True)
    with col6:
        st.plotly_chart(plot_heatmap_correlation(df_processed), use_container_width=True)
    
    st.markdown("#### 价格区间统计")
    st.dataframe(bin_stats, use_container_width=True)
    
    with st.expander("查看原始数据"):
        st.dataframe(df_raw, use_container_width=True)

with tab2:
    st.markdown('<div class="section-header">🎯 价格弹性分析</div>', unsafe_allow_html=True)
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("平均价格弹性", f"{elasticity_summary['avg_point_elasticity']:.3f}",
                  delta_color="inverse")
    with col2:
        st.metric("单位弹性价格", f"¥{elasticity_summary['unitary_elasticity_price']:.2f}")
    with col3:
        st.metric("弹性区间占比", f"{elasticity_summary['elastic_range_pct']:.1f}%")
    with col4:
        st.metric("最大收入价格", f"¥{elasticity_summary['max_revenue_price']:.2f}")
    
    if decouple_promotion and model.bootstrap_results:
        ci_promo = model.bootstrap_results.get('elasticity_promo_ci', {})
        ci_non_promo = model.bootstrap_results.get('elasticity_non_promo_ci', {})
        
        st.markdown("#### Bootstrap置信区间估计（促销vs非促销）")
        col5, col6 = st.columns(2)
        with col5:
            st.info(f"""
            **非促销期价格弹性**
            - 均值: {ci_non_promo.get('mean', 'N/A'):.3f}
            - {confidence_level*100:.0f}% CI: [{ci_non_promo.get('ci_lower', 'N/A'):.3f}, {ci_non_promo.get('ci_upper', 'N/A'):.3f}]
            - 标准误: {ci_non_promo.get('std_err', 'N/A'):.3f}
            """)
        with col6:
            st.info(f"""
            **促销期价格弹性**
            - 均值: {ci_promo.get('mean', 'N/A'):.3f}
            - {confidence_level*100:.0f}% CI: [{ci_promo.get('ci_lower', 'N/A'):.3f}, {ci_promo.get('ci_upper', 'N/A'):.3f}]
            - 标准误: {ci_promo.get('std_err', 'N/A'):.3f}
            """)
    
    st.plotly_chart(plot_elasticity_curve(elasticity_df, show_ci=True), use_container_width=True)
    
    if model.bootstrap_results is not None:
        st.markdown(f"#### Bootstrap系数分布（{n_bootstrap}次重采样）")
        st.plotly_chart(plot_bootstrap_distribution(model.bootstrap_results), use_container_width=True)
    
    st.markdown("#### 价格-弹性对照表")
    table_columns = ['price', 'purchase_probability', 'point_elasticity', 'elasticity_category']
    if 'is_promotion' in elasticity_df.columns:
        table_columns.insert(1, 'is_promotion')
    if 'prob_ci_lower' in elasticity_df.columns:
        table_columns.extend(['prob_ci_lower', 'prob_ci_upper'])
    price_elasticity_table = elasticity_df[table_columns].iloc[::10].reset_index(drop=True)
    st.dataframe(price_elasticity_table, use_container_width=True)
    
    with st.expander("弹性分类说明"):
        st.markdown("""
        - **极富弹性 (ε < -2)**: 价格变动1%，销量变动超过2%，降价效果显著
        - **富有弹性 (-2 ≤ ε < -1)**: 价格变动1%，销量变动1%-2%，降价可增加收入
        - **单位弹性 (-1 ≤ ε < -0.5)**: 价格变动1%，销量变动0.5%-1%，价格调整对收入影响较小
        - **缺乏弹性 (-0.5 ≤ ε < 0)**: 价格变动1%，销量变动不足0.5%，涨价可增加收入
        - **无弹性 (ε ≥ 0)**: 价格上涨销量反而增加，属反常情况
        """)

with tab3:
    st.markdown('<div class="section-header">💰 最优定价建议</div>', unsafe_allow_html=True)
    
    with st.spinner("正在计算最优价格..."):
        pricing_recommendations = optimal_pricing.generate_pricing_recommendations()
        profit_opt = pricing_recommendations['profit_analysis']
        revenue_opt = pricing_recommendations['revenue_analysis']
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("当前价格", f"¥{pricing_recommendations['current_price']:.2f}")
    with col2:
        st.metric("利润最大化价格", f"¥{pricing_recommendations['profit_optimal_price']:.2f}",
                 delta=f"¥{pricing_recommendations['profit_optimal_price'] - pricing_recommendations['current_price']:.2f}")
    with col3:
        st.metric("收入最大化价格", f"¥{pricing_recommendations['revenue_optimal_price']:.2f}",
                 delta=f"¥{pricing_recommendations['revenue_optimal_price'] - pricing_recommendations['current_price']:.2f}")
    
    st.markdown("#### 🎯 定价建议")
    for rec in pricing_recommendations['recommendations']:
        priority_color = {"高": "🔴", "中": "🟡", "低": "🟢"}[rec['priority']]
        st.info(f"{priority_color} **[{rec['priority']}优先级] {rec['type']}**\n\n{rec['description']}\n\n建议价格: ¥{rec['suggested_price']:.2f}\n\n{rec['expected_impact']}")
    
    st.markdown("#### 价格-利润/收入曲线")
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=profit_opt['prices_analysis']['price'],
        y=profit_opt['prices_analysis']['profit'],
        mode='lines',
        name='利润',
        line=dict(color='#2ca02c', width=3)
    ))
    fig.add_trace(go.Scatter(
        x=revenue_opt['prices_analysis']['price'],
        y=revenue_opt['prices_analysis']['revenue'],
        mode='lines',
        name='收入',
        line=dict(color='#1f77b4', width=3),
        yaxis='y2'
    ))
    fig.add_vline(
        x=profit_opt['optimal_price'],
        line_dash="dash", line_color="green",
        annotation_text=f"利润最优: ¥{profit_opt['optimal_price']:.2f}"
    )
    fig.add_vline(
        x=revenue_opt['optimal_price'],
        line_dash="dash", line_color="blue",
        annotation_text=f"收入最优: ¥{revenue_opt['optimal_price']:.2f}"
    )
    fig.update_layout(
        title='价格-利润/收入分析',
        xaxis_title='价格 (元)',
        yaxis_title='利润 (元)',
        yaxis=dict(titlefont=dict(color='#2ca02c')),
        yaxis2=dict(title='收入 (元)', titlefont=dict(color='#1f77b4'), overlaying='y', side='right'),
        height=500
    )
    st.plotly_chart(fig, use_container_width=True)
    
    st.markdown("#### 价格敏感度矩阵")
    sensitivity_matrix = optimal_pricing.calculate_price_sensitivity_matrix()
    st.dataframe(sensitivity_matrix, use_container_width=True)
    
    st.markdown("#### 价格区间细分分析")
    segment_analysis = optimal_pricing.analyze_price_segmentation()
    st.dataframe(segment_analysis, use_container_width=True)

with tab4:
    st.markdown('<div class="section-header">🎁 促销模拟预测</div>', unsafe_allow_html=True)
    
    with st.spinner("正在运行促销模拟..."):
        simulation_results = promotion_simulator.run_multiple_simulations()
        promotion_analysis = promotion_simulator.analyze_promotion_strategies(simulation_results)
        optimal_promotion = promotion_simulator.find_optimal_promotion(simulation_results, 'profit')
        promo_thresholds = promotion_simulator.calculate_promotion_thresholds()
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        best_profit = promotion_analysis['best_by_profit']
        strategy_names = {'direct_discount': '直接折扣', 'buy_one_get_one': '买一送一', 'bundle': '捆绑销售', 'coupon': '优惠券'}
        st.metric("最优促销策略", strategy_names.get(best_profit['strategy'], best_profit['strategy']))
    with col2:
        st.metric("最优折扣力度", f"{best_profit['discount_pct']*100:.1f}%")
    with col3:
        st.metric("最优促销周期", f"{best_profit['duration_days']}天")
    with col4:
        st.metric("预计利润增长", f"¥{best_profit['profit_change']:,.0f}",
                 delta=f"{best_profit['profit_change_pct']*100:+.1f}%")
    
    st.plotly_chart(plot_promotion_simulation(simulation_results), use_container_width=True)
    
    st.markdown("#### 促销策略对比分析")
    st.dataframe(promotion_analysis['strategy_comparison'], use_container_width=True)
    
    st.markdown("#### 📋 促销建议")
    for rec in promotion_analysis['recommendations']:
        priority_color = {"高": "🔴", "中": "🟡", "低": "🟢"}[rec['priority']]
        st.info(f"{priority_color} **[{rec['priority']}优先级] {rec['type']}**\n\n{rec['recommendation']}\n\n{rec['expected_impact']}")
    
    st.markdown("#### 促销时间线模拟（含延后效应）")
    timeline_df = promotion_simulator.simulate_promotion_timeline(
        discount_pct=best_profit['discount_pct'],
        duration_days=best_profit['duration_days'],
        strategy=best_profit['strategy']
    )
    
    if 'post_promo_demand' in timeline_df.columns:
        total_post_promo_loss = timeline_df[timeline_df['period'] == '促销后']['profit_lost'].sum() if 'profit_lost' in timeline_df.columns else 0
        avg_decay = timeline_df[timeline_df['period'] == '促销后']['decay_factor'].mean() if 'decay_factor' in timeline_df.columns else 1
        
        col_post1, col_post2, col_post3 = st.columns(3)
        with col_post1:
            st.metric("促销后需求平均恢复率", f"{avg_decay*100:.1f}%", delta_color="inverse")
        with col_post2:
            st.metric("促销后需求回落期", f"{(timeline_df['period'] == '促销后').sum()}天")
        with col_post3:
            st.metric("促销后预计利润损失", f"¥{total_post_promo_loss:,.0f}", delta_color="inverse")
    
    st.plotly_chart(plot_promotion_timeline(timeline_df), use_container_width=True)
    
    with st.expander("自定义促销模拟"):
        col5, col6, col7 = st.columns(3)
        with col5:
            custom_discount = st.slider("折扣力度 (%)", min_value=5, max_value=50, value=20) / 100
        with col6:
            custom_duration = st.slider("促销周期 (天)", min_value=1, max_value=60, value=7)
        with col7:
            custom_strategy = st.selectbox("促销策略", ["direct_discount", "buy_one_get_one", "bundle", "coupon"],
                                          format_func=lambda x: strategy_names[x])
        
        custom_result = promotion_simulator.simulate_promotion(
            discount_pct=custom_discount,
            duration_days=custom_duration,
            strategy=custom_strategy
        )
        
        st.write("#### 模拟结果")
        col8, col9, col10 = st.columns(3)
        with col8:
            st.metric("销量提升", f"+{custom_result['sales_lift_pct']*100:.1f}%")
        with col9:
            st.metric("收入变化", f"¥{custom_result['revenue_change']:,.0f}",
                     delta=f"{custom_result['revenue_change_pct']*100:+.1f}%")
        with col10:
            st.metric("利润变化", f"¥{custom_result['profit_change']:,.0f}",
                     delta=f"{custom_result['profit_change_pct']*100:+.1f}%")

with tab5:
    st.markdown('<div class="section-header">📊 模型诊断</div>', unsafe_allow_html=True)
    
    col1, col2, col3, col4, col5 = st.columns(5)
    metrics = results['metrics']
    with col1:
        st.metric("准确率", f"{metrics['accuracy']:.4f}")
    with col2:
        st.metric("精确率", f"{metrics['precision']:.4f}")
    with col3:
        st.metric("召回率", f"{metrics['recall']:.4f}")
    with col4:
        st.metric("F1分数", f"{metrics['f1']:.4f}")
    with col5:
        st.metric("AUC", f"{metrics['roc_auc']:.4f}")
    
    st.markdown("#### 模型系数摘要")
    st.text(str(results['model_summary']))
    
    st.plotly_chart(plot_feature_importance(results['feature_importance']), use_container_width=True)
    
    st.markdown("#### 混淆矩阵")
    cm = metrics['confusion_matrix']
    cm_df = pd.DataFrame(
        cm,
        index=['实际低销量', '实际高销量'],
        columns=['预测低销量', '预测高销量']
    )
    
    fig = go.Figure(data=go.Heatmap(
        z=cm_df.values,
        x=cm_df.columns,
        y=cm_df.index,
        text=cm_df.values,
        texttemplate="%{text}",
        textfont={"size": 14},
        colorscale='Blues'
    ))
    fig.update_layout(title='混淆矩阵', height=400)
    st.plotly_chart(fig, use_container_width=True)
    
    st.markdown("#### 特征重要性详情")
    st.dataframe(results['feature_importance'], use_container_width=True)

with tab6:
    st.markdown('<div class="section-header">🔍 涨价/降价影响分析</div>', unsafe_allow_html=True)
    
    impact_data = model.predict_sales_impact(
        df_processed,
        base_price=base_price,
        price_change_pct=price_change_pct
    )
    
    col1, col2, col3 = st.columns(3)
    with col1:
        change_direction = "涨价" if price_change_pct > 0 else "降价"
        st.metric(f"价格调整", f"{price_change_pct*100:+.1f}% ({change_direction})")
    with col2:
        sales_delta_color = "positive-change" if impact_data['sales_change_pct'] > 0 else "negative-change"
        st.metric("预计销量变化", 
                 f"{impact_data['sales_change_pct']*100:+.1f}%",
                 delta=f"{impact_data['sales_change']:,.0f}件")
    with col3:
        revenue_delta_color = "positive-change" if impact_data['revenue_change_pct'] > 0 else "negative-change"
        st.metric("预计收入变化",
                 f"¥{impact_data['revenue_change']:,.0f}",
                 delta=f"{impact_data['revenue_change_pct']*100:+.1f}%")
    
    st.plotly_chart(plot_sales_impact(impact_data), use_container_width=True)
    
    st.markdown("#### 详细影响分析")
    col4, col5 = st.columns(2)
    with col4:
        st.info(f"""
        **基准情况:**
        - 基准价格: ¥{impact_data['base_price']:.2f}
        - 基准购买概率: {impact_data['base_probability']*100:.2f}%
        - 基准销量预估: {impact_data['base_sales_estimate']:,.0f} 件
        - 基准收入预估: ¥{impact_data['base_revenue_estimate']:,.0f}
        """)
    with col5:
        st.info(f"""
        **调整后预测:**
        - 调整后价格: ¥{impact_data['new_price']:.2f}
        - 调整后购买概率: {impact_data['new_probability']*100:.2f}%
        - 预测销量: {impact_data['predicted_sales']:,.0f} 件
        - 预测收入: ¥{impact_data['predicted_revenue']:,.0f}
        """)
    
    elasticity_category = elasticity_df['elasticity_category'].iloc[
        np.argmin(np.abs(elasticity_df['price'] - base_price))
    ]
    
    st.markdown("#### 📝 分析结论")
    avg_elasticity = impact_data['average_elasticity']
    
    if price_change_pct < 0:
        if avg_elasticity < -1:
            st.success(f"""
            ✅ **降价策略建议执行**
            
            当前价格弹性为 {avg_elasticity:.3f}，属于{elasticity_category}区间。
            降价 {abs(price_change_pct)*100:.1f}% 预计可使销量提升 {impact_data['sales_change_pct']*100:.1f}%，
            收入{ '增加' if impact_data['revenue_change_pct'] > 0 else '减少'} {abs(impact_data['revenue_change_pct'])*100:.1f}%。
            
            { '由于需求富有弹性，降价可有效提升整体收入，建议执行此降价策略。' if impact_data['revenue_change_pct'] > 0 
              else '虽然销量提升明显，但由于降价幅度过大，总收入反而下降。建议缩小降价幅度或搭配其他促销手段。' }
            """)
        else:
            st.warning(f"""
            ⚠️ **降价策略需谨慎评估**
            
            当前价格弹性为 {avg_elasticity:.3f}，属于{elasticity_category}区间。
            降价 {abs(price_change_pct)*100:.1f}% 预计可使销量提升 {impact_data['sales_change_pct']*100:.1f}%，
            但收入{ '增加' if impact_data['revenue_change_pct'] > 0 else '减少'} {abs(impact_data['revenue_change_pct'])*100:.1f}%。
            
            由于需求弹性不足，降价带来的销量增长不足以弥补价格下降的损失。
            建议考虑其他营销策略如捆绑销售、提升产品附加值等。
            """)
    else:
        if avg_elasticity > -1:
            st.success(f"""
            ✅ **涨价策略建议执行**
            
            当前价格弹性为 {avg_elasticity:.3f}，属于{elasticity_category}区间。
            涨价 {price_change_pct*100:.1f}% 预计仅使销量下降 {abs(impact_data['sales_change_pct'])*100:.1f}%，
            收入预计{ '增加' if impact_data['revenue_change_pct'] > 0 else '减少'} {abs(impact_data['revenue_change_pct'])*100:.1f}%。
            
            由于需求缺乏弹性，涨价可在销量小幅下降的情况下有效提升整体收入，建议执行此涨价策略。
            """)
        else:
            st.warning(f"""
            ⚠️ **涨价策略需谨慎评估**
            
            当前价格弹性为 {avg_elasticity:.3f}，属于{elasticity_category}区间。
            涨价 {price_change_pct*100:.1f}% 预计将使销量下降 {abs(impact_data['sales_change_pct'])*100:.1f}%，
            收入预计{ '增加' if impact_data['revenue_change_pct'] > 0 else '减少'} {abs(impact_data['revenue_change_pct'])*100:.1f}%。
            
            由于需求富有弹性，涨价可能导致销量大幅下滑，从而抵消价格上涨带来的收益。
            建议谨慎考虑涨价幅度，或采取渐进式涨价策略。
            """)
    
    st.markdown("#### 多场景价格调整分析")
    price_scenarios = np.linspace(-0.3, 0.3, 13)
    scenario_results = []
    
    for pct in price_scenarios:
        result = model.predict_sales_impact(df_processed, base_price=base_price, price_change_pct=pct)
        scenario_results.append({
            'price_change_pct': pct * 100,
            'new_price': result['new_price'],
            'sales_change_pct': result['sales_change_pct'] * 100,
            'revenue_change_pct': result['revenue_change_pct'] * 100,
            'revenue': result['predicted_revenue']
        })
    
    scenario_df = pd.DataFrame(scenario_results)
    
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=scenario_df['price_change_pct'],
        y=scenario_df['sales_change_pct'],
        mode='lines+markers',
        name='销量变化率',
        line=dict(color='#1f77b4', width=3),
        marker=dict(size=8)
    ))
    fig.add_trace(go.Scatter(
        x=scenario_df['price_change_pct'],
        y=scenario_df['revenue_change_pct'],
        mode='lines+markers',
        name='收入变化率',
        line=dict(color='#2ca02c', width=3),
        marker=dict(size=8)
    ))
    fig.add_hline(y=0, line_dash="dash", line_color="black")
    fig.add_vline(x=price_change_pct*100, line_dash="dash", line_color="red",
                 annotation_text=f"当前设置: {price_change_pct*100:+.1f}%")
    fig.update_layout(
        title='价格调整影响分析',
        xaxis_title='价格调整幅度 (%)',
        yaxis_title='变化率 (%)',
        height=500
    )
    st.plotly_chart(fig, use_container_width=True)
    
    st.dataframe(scenario_df.round(2), use_container_width=True)

with tab7:
    st.markdown('<div class="section-header">⏳ 促销延后效应分析</div>', unsafe_allow_html=True)
    
    with st.spinner("正在分析促销延后效应..."):
        post_promo_sensitivity = promotion_simulator._analyze_post_promo_sensitivity()
        sensitivity_df = post_promo_sensitivity['sensitivity_data']
        
        best_profit = promotion_analysis['best_by_profit']
        demo_result = promotion_simulator.simulate_promotion(
            discount_pct=best_profit['discount_pct'],
            duration_days=best_profit['duration_days'],
            strategy=best_profit['strategy'],
            include_post_promo=True
        )
        post_promo_data = demo_result.get('post_promo_data', None)
    
    st.markdown("#### 📊 延后效应核心指标")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("促销后需求半衰期", f"{post_promo_halflife}天")
    with col2:
        st.metric("促销后总利润损失", f"¥{demo_result.get('post_promo_loss', 0):,.0f}",
                 delta_color="inverse")
    with col3:
        st.metric("净利润变化", f"¥{demo_result.get('net_profit_change', 0):,.0f}",
                 delta=f"{demo_result.get('net_profit_change_pct', 0)*100:+.1f}%")
    with col4:
        st.metric("损失占比", f"{demo_result.get('post_promo_loss_ratio', 0)*100:.1f}%",
                 delta_color="inverse")
    
    if post_promo_data is not None and len(post_promo_data) > 0:
        st.markdown("#### 📈 促销后需求回落趋势")
        st.plotly_chart(plot_post_promotion_effect(post_promo_data), use_container_width=True)
    
    st.markdown("#### 🔍 不同促销策略的延后效应对比")
    sensitivity_display = sensitivity_df.copy()
    sensitivity_display['discount'] = (sensitivity_display['discount'] * 100).round(1).astype(str) + '%'
    sensitivity_display['gross_profit'] = sensitivity_display['gross_profit'].round(0).astype(int)
    sensitivity_display['post_promo_loss'] = sensitivity_display['post_promo_loss'].round(0).astype(int)
    sensitivity_display['net_profit'] = sensitivity_display['net_profit'].round(0).astype(int)
    sensitivity_display['loss_ratio'] = (sensitivity_display['loss_ratio'] * 100).round(1).astype(str) + '%'
    sensitivity_display.columns = [
        '促销周期(天)', '折扣力度', '毛利增长(元)', '延后损失(元)', 
        '净利增长(元)', '损失占比'
    ]
    st.dataframe(sensitivity_display, use_container_width=True)
    
    st.markdown("#### 💡 延后效应敏感性分析")
    fig = go.Figure()
    for discount in sensitivity_df['discount'].unique():
        subset = sensitivity_df[sensitivity_df['discount'] == discount]
        fig.add_trace(go.Scatter(
            x=subset['duration'],
            y=subset['net_profit'],
            mode='lines+markers',
            name=f'折扣{discount*100:.0f}%（净利）',
            line=dict(width=3),
            marker=dict(size=10)
        ))
        fig.add_trace(go.Scatter(
            x=subset['duration'],
            y=subset['gross_profit'],
            mode='lines',
            name=f'折扣{discount*100:.0f}%（毛利）',
            line=dict(width=2, dash='dash'),
            opacity=0.6
        ))
    
    fig.add_hline(y=0, line_dash="dash", line_color="black", annotation_text="盈亏平衡线")
    fig.update_layout(
        title='促销周期vs净利润（考虑延后效应）',
        xaxis_title='促销周期（天）',
        yaxis_title='利润变化（元）',
        height=500,
        hovermode='x unified'
    )
    st.plotly_chart(fig, use_container_width=True)
    
    st.info(f"""
    **最优策略建议（考虑延后效应）**
    
    {post_promo_sensitivity['recommendation']}
    
    **说明：**
    - 实线表示考虑延后效应后的净利润
    - 虚线表示不考虑延后效应的毛利润
    - 促销时间越长、折扣越大，延后效应的损失越显著
    - 短期大力度促销往往比长期小力度促销更有利
    """)
    
    with st.expander("查看延后效应详细说明"):
        st.markdown("""
        **促销延后效应产生原因：**
        
        1. **前置购买效应（Stockpiling）**：消费者在促销期间囤积商品，导致促销后需求下降
        2. **价格参考效应**：促销后消费者对价格的感知变化，对原价产生抵触
        3. **消费习惯改变**：促销期间培养的消费习惯在促销结束后难以维持
        
        **建模方法：**
        
        本系统使用指数衰减模型模拟促销后需求回落：
        - 需求衰减因子 = exp(-天数 × ln(2) / 半衰期)
        - 同时考虑促销滞后变量（post_promo_1 ~ post_promo_7）的系数估计
        - 结合囤货调整系数，根据折扣力度动态调整需求回落幅度
        
        **管理启示：**
        
        - 促销频率不宜过高，避免消费者形成"等促销"的购买习惯
        - 促销周期建议控制在半衰期×2以内，减少延后损失
        - 促销后可搭配营销策略（如会员专享、新品推荐）平滑需求回落
        """)

with tab8:
    st.markdown('<div class="section-header">🔗 品类间交叉弹性分析</div>', unsafe_allow_html=True)
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("分析商品数", f"{n_products}个")
    with col2:
        st.metric("显著相关关系", f"{len(cross_results.get('significant_cross_pairs', pd.DataFrame()))}对")
    with col3:
        if 'own_elasticities' in cross_results:
            sig_own = cross_results['own_elasticities'][cross_results['own_elasticities']['significant']]
            st.metric("显著自弹性商品", f"{len(sig_own)}个")
        else:
            st.metric("显著自弹性商品", "0个")
    with col4:
        st.metric("品类数", f"{len(cross_results.get('product_info', {}))}个品类")
    
    st.markdown("#### 📊 交叉弹性热力图")
    heatmap_data = cross_analyzer.get_elasticity_heatmap_data()
    st.plotly_chart(plot_cross_elasticity_heatmap(heatmap_data), use_container_width=True)
    
    st.markdown("#### 🔍 调价影响模拟")
    col5, col6 = st.columns(2)
    with col5:
        product_ids = list(cross_results.get('product_info', {}).keys())
        product_names = [cross_results['product_info'][pid]['name'] for pid in product_ids]
        selected_product_idx = st.selectbox(
            "选择调价商品", 
            range(len(product_ids)),
            format_func=lambda i: f"{product_names[i]} ({cross_results['product_info'][product_ids[i]]['category']})"
        )
        selected_product_id = product_ids[selected_product_idx]
    with col6:
        cross_price_change = st.slider(
            "价格调整幅度 (%)", 
            min_value=-30.0, 
            max_value=30.0, 
            value=-10.0, 
            step=1.0,
            key="cross_price_change"
        ) / 100
    
    with st.spinner("正在计算调价影响..."):
        cross_impact = cross_analyzer.simulate_price_change_impact(
            source_product_id=selected_product_id,
            price_change_pct=cross_price_change
        )
    
    st.plotly_chart(plot_cross_elasticity_impact(cross_impact), use_container_width=True)
    
    st.markdown("#### 📋 影响明细")
    impact_display = cross_impact.copy()
    impact_display['cross_elasticity'] = impact_display['cross_elasticity'].round(3)
    impact_display['sales_change_pct'] = (impact_display['sales_change_pct'] * 100).round(2)
    impact_display['expected_sales_change'] = impact_display['expected_sales_change'].round(0).astype(int)
    impact_display['expected_revenue_change'] = impact_display['expected_revenue_change'].round(0).astype(int)
    impact_display['p_value'] = impact_display['p_value'].round(4)
    
    display_cols = [
        'product_name', 'category', 'impact_type', 'cross_elasticity',
        'p_value', 'significant', 'sales_change_pct',
        'expected_sales_change', 'expected_revenue_change'
    ]
    impact_display = impact_display[display_cols]
    impact_display.columns = [
        '商品名称', '品类', '影响类型', '交叉弹性',
        'P值', '显著', '销量变化(%)',
        '销量变化(件)', '收入变化(元)'
    ]
    
    def highlight_significant(s):
        return ['background-color: rgba(44, 160, 44, 0.1)' if v else '' for v in s]
    
    st.dataframe(
        impact_display.style.apply(highlight_significant, subset=['显著']),
        use_container_width=True
    )
    
    total_sales_change = cross_impact['expected_sales_change'].sum()
    total_revenue_change = cross_impact['expected_revenue_change'].sum()
    
    st.info(f"""
    **总体影响总结：**
    
    - {product_names[selected_product_idx]} 价格调整 {cross_price_change*100:+.1f}% 后，
    - 所有商品总销量预计变化: **{total_sales_change:+.0f} 件**
    - 所有商品总收入预计变化: **{total_revenue_change:+,.0f} 元**
    - 其中 {product_names[selected_product_idx]} 自身销量变化: **{cross_impact[cross_impact['product_id']==selected_product_id]['expected_sales_change'].values[0]:+.0f} 件**
    """)
    
    st.markdown("#### 📈 品类层面分析")
    cat_analysis = cross_analyzer.get_category_level_analysis()
    if 'category_summary' in cat_analysis and len(cat_analysis['category_summary']) > 0:
        cat_display = cat_analysis['category_summary'].copy()
        cat_display = cat_display.round(3)
        st.dataframe(cat_display, use_container_width=True)

with tab9:
    st.markdown('<div class="section-header">⚡ 动态定价模拟</div>', unsafe_allow_html=True)
    
    st.markdown("#### 🎯 定价策略选择")
    col1, col2 = st.columns(2)
    with col1:
        selected_strategies = st.multiselect(
            "选择要对比的定价策略",
            ["固定价格", "跟随竞品", "动态毛利", "弹性优化", "时段定价"],
            default=["固定价格", "跟随竞品", "弹性优化", "时段定价"]
        )
    with col2:
        sim_days = st.slider(
            "模拟天数",
            min_value=30,
            max_value=180,
            value=90,
            step=10,
            key="dynamic_sim_days"
        )
    
    strategy_map = {
        "固定价格": PricingStrategyType.FIXED_PRICE,
        "跟随竞品": PricingStrategyType.FOLLOW_COMPETITOR,
        "动态毛利": PricingStrategyType.DYNAMIC_MARGIN,
        "弹性优化": PricingStrategyType.ELASTICITY_BASED,
        "时段定价": PricingStrategyType.TIME_BASED
    }
    
    strategies = []
    for s in selected_strategies:
        default_strategies = dynamic_simulator.create_default_strategies(base_price=base_price, product_id=0)
        strategy = next((x for x in default_strategies if x.strategy_type == strategy_map[s]), None)
        if strategy:
            strategies.append(strategy)
    
    if len(strategies) > 0:
        with st.spinner("正在进行动态定价模拟..."):
            comparison_result = dynamic_simulator.compare_strategies(
                df_processed,
                strategies,
                n_days=sim_days
            )
        
        st.markdown("#### 📊 策略对比分析")
        st.plotly_chart(
            plot_dynamic_pricing_comparison(
                comparison_result['comparison_summary'],
                comparison_result['all_results']
            ),
            use_container_width=True
        )
        
        st.markdown("#### 🏆 策略收益排名")
        rank_display = comparison_result['comparison_summary'].copy()
        rank_display = rank_display.sort_values('total_profit', ascending=False)
        rank_display['rank'] = range(1, len(rank_display) + 1)
        
        rank_display['total_revenue'] = (rank_display['total_revenue'] / 10000).round(1).astype(str) + '万'
        rank_display['total_profit'] = (rank_display['total_profit'] / 10000).round(1).astype(str) + '万'
        rank_display['revenue_change_pct'] = (rank_display['revenue_change_pct'] * 100).round(1).astype(str) + '%'
        rank_display['profit_change_pct'] = (rank_display['profit_change_pct'] * 100).round(1).astype(str) + '%'
        rank_display['cross_revenue_impact'] = (rank_display['cross_revenue_impact'] / 10000).round(2).astype(str) + '万'
        rank_display['net_revenue'] = (rank_display['net_revenue'] / 10000).round(1).astype(str) + '万'
        
        rank_cols = ['rank', 'description', 'total_revenue', 'total_profit', 
                     'revenue_change_pct', 'profit_change_pct', 
                     'cross_revenue_impact', 'net_revenue']
        rank_display = rank_display[rank_cols]
        rank_display.columns = [
            '排名', '策略名称', '总收入', '总利润',
            '收入变化', '利润变化', '交叉影响', '净收入'
        ]
        
        def highlight_best(s):
            return ['background-color: rgba(44, 160, 44, 0.2)' if i == 0 else '' for i in range(len(s))]
        
        st.dataframe(
            rank_display.style.apply(highlight_best, subset=['排名']),
            use_container_width=True
        )
        
        if comparison_result['best_strategy']:
            best_desc = dynamic_simulator._get_strategy_description(
                PricingStrategy(PricingStrategyType(comparison_result['best_strategy']))
            )
            st.success(f"🏆 **最优策略推荐：{best_desc}**")
        
        st.markdown("#### 📈 最佳策略时间线")
        if comparison_result['best_strategy'] in comparison_result['all_results']:
            best_result = comparison_result['all_results'][comparison_result['best_strategy']]
            st.plotly_chart(
                plot_pricing_timeline(best_result['simulation_data']),
                use_container_width=True
            )
        
        with st.expander("📚 各定价策略说明"):
            st.markdown("""
            **1. 固定价格策略 (Fixed Price)**
            - 保持固定价格不变，作为基准策略
            - 适用于需求稳定、市场成熟的产品
            
            **2. 跟随竞品策略 (Follow Competitor)**
            - 根据竞品价格动态调整，保持一定的加价率
            - 参数：加价率、价格上下限、反应滞后天数
            - 适用于竞争激烈、价格透明度高的市场
            
            **3. 动态毛利策略 (Dynamic Margin)**
            - 基于目标毛利率自动计算定价
            - 参数：目标毛利率、变动成本、价格下限
            - 适用于成本波动较大的产品
            
            **4. 弹性优化策略 (Elasticity Based)**
            - 基于价格弹性系数计算最优加价率
            - 公式：最优加价率 = -1 / (1 + 弹性系数)
            - 适用于弹性稳定、数据充分的产品
            
            **5. 时段定价策略 (Time Based)**
            - 根据历史销售的时间规律进行动态调价
            - 在需求高峰期涨价，低谷期降价
            - 适用于需求有明显时间规律的产品
            """)

with tab10:
    st.markdown('<div class="section-header">🎯 价格阈值检测与心理价位分析</div>', unsafe_allow_html=True)
    
    st.markdown("#### 🔍 检测到的价格阈值")
    thresholds = threshold_results.get('combined', {}).get('thresholds', [])
    
    if len(thresholds) > 0:
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("检测到的阈值数", f"{len(thresholds)}个")
        with col2:
            high_conf = [t for t in thresholds if t.get('confidence', 0) > 0.7]
            st.metric("高置信度阈值", f"{len(high_conf)}个")
        with col3:
            multi_method = [t for t in thresholds if t.get('n_methods', 1) >= 2]
            st.metric("多方法验证阈值", f"{len(multi_method)}个")
        
        st.markdown("#### 📊 阈值检测可视化")
        st.plotly_chart(
            plot_price_thresholds(threshold_results, price_segments, df_processed),
            use_container_width=True
        )
        
        st.markdown("#### 📋 阈值详情")
        threshold_details = []
        for t in thresholds:
            methods = ','.join(t.get('detection_methods', []))
            threshold_details.append({
                '阈值价格 (元)': t['threshold_price'],
                '置信度': f"{t.get('confidence', 0):.1%}",
                '检测方法': methods,
                '方法数': t.get('n_methods', 1)
            })
        threshold_df = pd.DataFrame(threshold_details)
        threshold_df = threshold_df.sort_values('置信度', ascending=False)
        st.dataframe(threshold_df, use_container_width=True)
        
        st.markdown("#### 📈 价格区间特征对比")
        segment_data = threshold_detector.get_segment_comparison_data()
        st.plotly_chart(
            plot_price_segments_comparison(segment_data),
            use_container_width=True
        )
        
        st.markdown("#### 💡 定价建议")
        recommendations = threshold_detector.get_threshold_recommendations()
        
        if recommendations['optimal_price_segment']:
            opt = recommendations['optimal_price_segment']
            st.success(f"""
            🏆 **最优定价区间建议：{opt['price_range_lower']:.0f} - {opt['price_range_upper']:.0f} 元**
            
            - 区间中点价格: {opt['price_range_mid']:.2f} 元
            - 平均销量: {opt['avg_sales']:.0f} 件
            - 价格弹性: {opt['price_elasticity']:.3f}
            - 样本点数: {opt['n_points']} 个
            
            该区间的价格弹性为 {opt['price_elasticity']:.3f}，
            {'处于富有弹性区间，降价可有效提升收入' if opt['price_elasticity'] < -1 else 
             '处于缺乏弹性区间，涨价可提升毛利'}。
            """)
        
        if len(recommendations['critical_points']) > 0:
            st.markdown("#### ⚠️ 关键价格临界点")
            for point in recommendations['critical_points']:
                st.info(f"💰 **{point['price']:.0f} 元** - {point['description']}")
        
        if len(recommendations['psychological_prices']) > 0:
            st.markdown("#### 🧠 检测到的心理价位")
            psych_df = pd.DataFrame(recommendations['psychological_prices'])
            psych_df['confidence'] = (psych_df['confidence'] * 100).round(1).astype(str) + '%'
            psych_df.columns = ['价格 (元)', '心理价位类型', '置信度']
            st.dataframe(psych_df, use_container_width=True)
        
        with st.expander("📚 价格阈值检测方法说明"):
            st.markdown("""
            **本系统使用四种方法综合检测价格阈值：**
            
            **1. K-Means聚类法**
            - 将价格-销量数据点聚类，识别不同的价格区间
            - 通过肘部法则确定最优聚类数
            - 优点：直观，能发现非线性关系
            
            **2. 相关系数突变检测**
            - 滚动计算价格与销量的相关系数
            - 检测相关系数突变的位置作为阈值
            - 优点：能捕捉价格-销量关系的结构性变化
            
            **3. 分位数与导数法**
            - 基于销量分位数识别价格阈值
            - 检测销量对价格的导数突变点
            - 优点：能发现销量加速下降的临界点
            
            **4. 滚动弹性断点检测**
            - 滚动窗口估计价格弹性
            - 检测弹性系数突变的位置
            - 优点：直接从经济理论角度识别阈值
            
            **综合判断：**
            系统会综合四种方法的结果，合并相近的阈值点，
            并根据检测方法数量和稳定性计算置信度。
            置信度 > 70% 的阈值建议重点参考。
            """)

st.markdown("---")
st.markdown("### 📚 关于价格弹性分析")
with st.expander("查看方法学说明"):
    st.markdown("""
    **Logit模型价格弹性分析方法**
    
    本系统使用Logit（逻辑回归）模型来估计价格弹性，核心思想是将"高销量"作为二元目标变量，
    通过分析价格及其他因素对购买概率的影响，计算价格弹性系数。
    
    **弹性系数计算公式:**
    - 点弹性: ε = β × P × (1 - P)，其中β是Logit模型中价格变量的系数，P是购买概率
    - 弧弹性: ε = [(Q2-Q1)/Q1] / [(P2-P1)/P1]
    
    **弹性区间解读:**
    - |ε| > 1: 富有弹性，降价可增加总收入
    - |ε| = 1: 单位弹性，价格变化不影响总收入
    - |ε| < 1: 缺乏弹性，涨价可增加总收入
    
    **最优定价原理:**
    基于模型预测的需求曲线，结合成本结构，找到使利润（收入-成本）最大化的价格点。
    
    **促销模拟方法:**
    通过模拟不同折扣力度、促销周期和促销策略下的需求变化，评估各方案的投资回报率(ROI)。
    """)
