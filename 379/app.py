import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.data_generator import (
    generate_customer_profiles,
    generate_transaction_history,
    generate_behavior_logs,
    prepare_model_data
)
from src.bg_nbd_model import BGNBDModel
from src.gamma_gamma_model import GammaGammaModel
from src.ltv_analysis import LTVAnalyzer
from src.strategy_engine import StrategyEngine
from src.marketing_simulator import MarketingSimulator
from src.change_detector import ChangeDetector
from src.realtime_updater import RealtimeUpdater

st.set_page_config(
    page_title="客户生命周期价值预测系统",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    .main {
        padding: 0rem 1rem;
    }
    .stMetric {
        background-color: #f0f2f6;
        padding: 15px;
        border-radius: 10px;
    }
    .high-value {
        background-color: #ffd700;
        padding: 5px 10px;
        border-radius: 5px;
        font-weight: bold;
    }
    .medium-high-value {
        background-color: #98FB98;
        padding: 5px 10px;
        border-radius: 5px;
        font-weight: bold;
    }
    .medium-value {
        background-color: #87CEEB;
        padding: 5px 10px;
        border-radius: 5px;
        font-weight: bold;
    }
    .medium-low-value {
        background-color: #DDA0DD;
        padding: 5px 10px;
        border-radius: 5px;
        font-weight: bold;
    }
    .low-value {
        background-color: #FFB6C1;
        padding: 5px 10px;
        border-radius: 5px;
        font-weight: bold;
    }
    .strategy-badge {
        display: inline-block;
        padding: 3px 8px;
        border-radius: 10px;
        font-size: 12px;
        font-weight: bold;
        margin-right: 5px;
    }
    .strategy-maintain {
        background-color: #FFF3CD;
        color: #856404;
    }
    .strategy-activate {
        background-color: #D1ECF1;
        color: #0C5460;
    }
    .strategy-convert {
        background-color: #D4EDDA;
        color: #155724;
    }
    .strategy-reactivate {
        background-color: #F8D7DA;
        color: #721C24;
    }
</style>
""", unsafe_allow_html=True)

st.title("📊 客户生命周期价值预测系统")
st.markdown("基于BG/NBD和Gamma-Gamma模型的客户价值预测与分析平台 | 支持维护-促活-促转化分层策略")

if 'data_loaded' not in st.session_state:
    st.session_state.data_loaded = False
    st.session_state.profiles = None
    st.session_state.transactions = None
    st.session_state.behavior_logs = None
    st.session_state.model_data = None
    st.session_state.bg_nbd = None
    st.session_state.gg = None
    st.session_state.analyzer = None
    st.session_state.ltv_data = None
    st.session_state.segment_stats = None
    st.session_state.engine = None
    st.session_state.marketing_simulator = None
    st.session_state.change_detector = None
    st.session_state.realtime_updater = None
    st.session_state.historical_ltv_data = None
    st.session_state.sim_result = None
    st.session_state.change_report = None

with st.sidebar:
    st.header("⚙️ 配置参数")
    
    st.subheader("📊 数据配置")
    n_customers = st.slider("模拟客户数量", min_value=200, max_value=2000, value=500, step=100)
    future_months = st.slider("预测未来月数", min_value=1, max_value=24, value=12, step=1)
    discount_rate = st.slider("折现率(%)", min_value=0, max_value=20, value=1, step=1) / 100
    churn_threshold = st.slider("流失阈值(活跃度)", min_value=0.1, max_value=0.5, value=0.3, step=0.05,
                               help="低于该活跃度阈值判定为流失客户")
    
    st.subheader("👥 分群配置")
    segmentation_method = st.radio(
        "分群方式",
        ["KMeans聚类", "阈值分群"],
        index=0,
        help="KMeans自动聚类或手动设置LTV阈值分群"
    )
    
    if segmentation_method == "KMeans聚类":
        n_segments = st.slider("聚类分群数量", min_value=3, max_value=6, value=4, step=1)
        segment_thresholds = None
    else:
        n_segments = 3
        st.info("设置LTV阈值划分客群")
        col_t1, col_t2 = st.columns(2)
        with col_t1:
            threshold_medium = st.number_input("中价值LTV阈值(¥)", min_value=100, max_value=10000, value=500, step=100)
        with col_t2:
            threshold_high = st.number_input("高价值LTV阈值(¥)", min_value=500, max_value=50000, value=2000, step=500)
        segment_thresholds = [threshold_medium, threshold_high]
        st.caption(f"客群划分: 低价值(<¥{threshold_medium}) | 中价值(¥{threshold_medium}-¥{threshold_high}) | 高价值(>¥{threshold_high})")
    
    if st.button("🚀 生成数据并运行分析", type="primary", use_container_width=True):
        with st.spinner("正在生成数据并训练模型..."):
            st.session_state.profiles = generate_customer_profiles(n_customers=n_customers)
            st.session_state.transactions = generate_transaction_history(st.session_state.profiles)
            st.session_state.behavior_logs = generate_behavior_logs(st.session_state.profiles)
            st.session_state.model_data = prepare_model_data(
                st.session_state.profiles, 
                st.session_state.transactions, 
                st.session_state.behavior_logs
            )
            
            st.session_state.bg_nbd = BGNBDModel()
            st.session_state.bg_nbd.fit(st.session_state.model_data)
            
            st.session_state.gg = GammaGammaModel()
            st.session_state.gg.fit(st.session_state.model_data)
            
            st.session_state.analyzer = LTVAnalyzer(st.session_state.bg_nbd, st.session_state.gg)
            st.session_state.ltv_data = st.session_state.analyzer.calculate_ltv(
                st.session_state.model_data, 
                future_months=future_months,
                discount_rate=discount_rate,
                churn_threshold=churn_threshold,
                include_reactivation=True
            )
            
            if segmentation_method == "阈值分群" and segment_thresholds:
                segment_names = ['低价值客户', '中价值客户', '高价值客户']
                st.session_state.ltv_data, st.session_state.segment_stats = st.session_state.analyzer.segment_customers(
                    st.session_state.model_data, 
                    st.session_state.ltv_data, 
                    thresholds=segment_thresholds,
                    segment_names=segment_names
                )
            else:
                st.session_state.ltv_data, st.session_state.segment_stats = st.session_state.analyzer.segment_customers(
                    st.session_state.model_data, 
                    st.session_state.ltv_data, 
                    n_segments=n_segments
                )
            
            st.session_state.engine = StrategyEngine()
            st.session_state.marketing_simulator = MarketingSimulator(
                st.session_state.bg_nbd, st.session_state.gg, st.session_state.ltv_data
            )
            st.session_state.change_detector = ChangeDetector()
            st.session_state.realtime_updater = RealtimeUpdater(
                st.session_state.bg_nbd, st.session_state.gg, st.session_state.analyzer
            )
            st.session_state.data_loaded = True
        
        st.success("分析完成！")

if not st.session_state.data_loaded:
    st.info("👈 请在左侧配置参数并点击按钮开始分析")
    
    st.markdown("""
    ### 系统功能介绍
    
    本系统集成了以下核心功能：
    
    - **BG/NBD模型**：预测客户未来消费次数、活跃度和再激活概率
    - **Gamma-Gamma模型**：预测客户客单价
    - **LTV计算**：综合预测客户生命周期价值，考虑流失和再激活
    - **客户分群**：支持KMeans聚类或手动阈值分群
    - **分层策略**：高价值**维护**、中价值**促活**、低价值**促转化**
    - **再激活计划**：针对流失客户的召回策略
    
    请点击左侧按钮开始体验！
    """)
else:
    tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8, tab9, tab10 = st.tabs([
        "📈 总览", "📊 LTV分析", "👥 客户分群", "🎯 策略建议", 
        "🔄 再激活", "📉 模型详情", "📋 原始数据",
        "🎁 营销模拟", "📊 异动分析", "⚡ 实时更新"
    ])
    
    with tab1:
        st.header("📈 分析总览")
        
        report = st.session_state.analyzer.generate_ltv_distribution_report(st.session_state.ltv_data)
        churned_count = (st.session_state.ltv_data['is_churned'] == True).sum()
        churn_rate = churned_count / len(st.session_state.ltv_data) * 100
        reactivation_potential = st.session_state.ltv_data[st.session_state.ltv_data['is_churned'] == True]['reactivation_prob'].mean()
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("总客户数", f"{report['total_customers']:,}")
        with col2:
            st.metric("总预测LTV", f"¥{report['total_ltv']:,.2f}")
        with col3:
            st.metric("平均LTV", f"¥{report['avg_ltv']:,.2f}")
        with col4:
            st.metric("LTV中位数", f"¥{report['median_ltv']:,.2f}")
        
        col5, col6, col7, col8 = st.columns(4)
        with col5:
            st.metric("Top 10%客户贡献", f"{report['top_10_contribution']*100:.1f}%")
        with col6:
            st.metric("流失客户数", f"{churned_count:,}", delta=f"-{churn_rate:.1f}%")
        with col7:
            st.metric("平均再激活概率", f"{reactivation_potential*100:.1f}%")
        with col8:
            active_value = (st.session_state.ltv_data['probability_alive'] > 0.5).mean()*100
            st.metric("活跃客户占比", f"{active_value:.1f}%")
        
        st.markdown("---")
        
        col_chart1, col_chart2 = st.columns(2)
        
        with col_chart1:
            st.subheader("LTV分布")
            fig = px.histogram(
                st.session_state.ltv_data, 
                x='ltv', 
                nbins=50,
                title='客户LTV分布直方图',
                color_discrete_sequence=['#1f77b4']
            )
            fig.update_layout(showlegend=False)
            st.plotly_chart(fig, use_container_width=True)
        
        with col_chart2:
            st.subheader("客户价值贡献")
            ltv_sorted = st.session_state.ltv_data['ltv'].sort_values(ascending=False)
            cumulative_ltv = ltv_sorted.cumsum() / ltv_sorted.sum()
            customer_pct = np.arange(1, len(cumulative_ltv) + 1) / len(cumulative_ltv)
            
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=customer_pct * 100,
                y=cumulative_ltv * 100,
                mode='lines',
                name='LTV累积占比',
                line=dict(color='#1f77b4', width=2)
            ))
            fig.add_trace(go.Scatter(
                x=[0, 100],
                y=[0, 100],
                mode='lines',
                name='公平线',
                line=dict(color='red', width=1, dash='dash')
            ))
            fig.update_layout(
                title='LTV帕累托曲线',
                xaxis_title='客户占比 (%)',
                yaxis_title='累积LTV占比 (%)',
                showlegend=True
            )
            st.plotly_chart(fig, use_container_width=True)
        
        st.markdown("---")
        
        st.subheader("🎯 客群策略概览")
        col_s1, col_s2, col_s3 = st.columns(3)
        with col_s1:
            st.markdown("""
            <div style="background-color: #FFF3CD; padding: 20px; border-radius: 10px;">
                <h3 style="color: #856404; margin: 0;">🏆 高价值</h3>
                <p style="margin: 10px 0; color: #856404;">核心策略：<strong>维护</strong></p>
                <p style="margin: 0; font-size: 14px; color: #856404;">专属服务、VIP权益、流失预警</p>
            </div>
            """, unsafe_allow_html=True)
        with col_s2:
            st.markdown("""
            <div style="background-color: #D1ECF1; padding: 20px; border-radius: 10px;">
                <h3 style="color: #0C5460; margin: 0;">⚡ 中价值</h3>
                <p style="margin: 10px 0; color: #0C5460;">核心策略：<strong>促活</strong></p>
                <p style="margin: 0; font-size: 14px; color: #0C5460;">频次提升、场景营销、升级激励</p>
            </div>
            """, unsafe_allow_html=True)
        with col_s3:
            st.markdown("""
            <div style="background-color: #D4EDDA; padding: 20px; border-radius: 10px;">
                <h3 style="color: #155724; margin: 0;">📈 低价值</h3>
                <p style="margin: 10px 0; color: #155724;">核心策略：<strong>促转化</strong></p>
                <p style="margin: 0; font-size: 14px; color: #155724;">首单激励、高性价比、潜力挖掘</p>
            </div>
            """, unsafe_allow_html=True)
    
    with tab2:
        st.header("📊 LTV分位数分析")
        
        quantiles = st.session_state.analyzer.calculate_ltv_quantiles(st.session_state.ltv_data)
        
        col1, col2 = st.columns([1, 1.5])
        
        with col1:
            st.subheader("LTV分位数表")
            st.dataframe(
                quantiles.style.format({'ltv_value': '¥{:,.2f}'}),
                use_container_width=True,
                hide_index=True
            )
            
            st.subheader("LTV分段统计")
            ltv = st.session_state.ltv_data['ltv']
            bins = [0, ltv.quantile(0.25), ltv.quantile(0.5), ltv.quantile(0.75), ltv.max()]
            labels = ['0-25%', '25-50%', '50-75%', '75-100%']
            st.session_state.ltv_data['ltv_quartile'] = pd.cut(ltv, bins=bins, labels=labels)
            
            quartile_stats = st.session_state.ltv_data.groupby('ltv_quartile').agg({
                'customer_id': 'count',
                'ltv': ['mean', 'sum'],
                'predicted_purchases': 'mean',
                'predicted_avg_amount': 'mean',
                'reactivation_prob': 'mean',
                'is_churned': 'mean'
            }).round(2)
            quartile_stats.columns = ['客户数', '平均LTV', '总LTV', '预计购买次数', '预计客单价', '平均再激活概率', '流失率']
            st.dataframe(quartile_stats, use_container_width=True)
        
        with col2:
            st.subheader("LTV分位数可视化")
            
            fig = go.Figure()
            fig.add_trace(go.Box(
                y=st.session_state.ltv_data['ltv'],
                name='LTV分布',
                boxpoints='outliers',
                marker_color='#1f77b4'
            ))
            fig.update_layout(
                title='LTV箱线图',
                yaxis_title='LTV (¥)',
                showlegend=False
            )
            st.plotly_chart(fig, use_container_width=True)
            
            fig2 = px.bar(
                quantiles,
                x='quantile',
                y='ltv_value',
                title='LTV分位数对比',
                color='ltv_value',
                color_continuous_scale='Blues',
                text_auto='.2s'
            )
            fig2.update_layout(showlegend=False)
            st.plotly_chart(fig2, use_container_width=True)
        
        st.markdown("---")
        st.subheader("🔍 单客LTV查询")
        customer_id = st.selectbox("选择客户ID", st.session_state.ltv_data['customer_id'].unique())
        customer_data = st.session_state.ltv_data[st.session_state.ltv_data['customer_id'] == customer_id]
        
        if not customer_data.empty:
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("预测LTV", f"¥{customer_data['ltv'].values[0]:,.2f}")
            with col2:
                st.metric("预计购买次数", f"{customer_data['predicted_purchases'].values[0]:.1f}")
            with col3:
                st.metric("活跃度", f"{customer_data['probability_alive'].values[0]*100:.1f}%")
            with col4:
                is_churned = customer_data['is_churned'].values[0]
                status = "已流失" if is_churned else "活跃"
                st.metric("状态", status, delta=f"再激活概率: {customer_data['reactivation_prob'].values[0]*100:.1f}%")
    
    with tab3:
        st.header("👥 客户分群分析")
        
        col1, col2 = st.columns([1, 1.5])
        
        with col1:
            st.subheader("各客群统计")
            
            segment_display = st.session_state.segment_stats.copy()
            segment_display['ltv_mean'] = segment_display['ltv_mean'].round(2)
            segment_display['ltv_median'] = segment_display['ltv_median'].round(2)
            segment_display['avg_purchases'] = segment_display['avg_purchases'].round(2)
            segment_display['avg_amount'] = segment_display['avg_amount'].round(2)
            segment_display['avg_prob_alive'] = (segment_display['avg_prob_alive'] * 100).round(1)
            segment_display['avg_reactivation_prob'] = (segment_display['avg_reactivation_prob'] * 100).round(1)
            segment_display['churn_rate'] = (segment_display['churn_rate'] * 100).round(1)
            
            def get_strategy_type(name):
                if '高价值' in name:
                    return '<span class="strategy-badge strategy-maintain">维护</span>'
                elif '中高' in name:
                    return '<span class="strategy-badge strategy-maintain">维护</span><span class="strategy-badge strategy-activate">促活</span>'
                elif '中价值' in name:
                    return '<span class="strategy-badge strategy-activate">促活</span>'
                elif '中低' in name:
                    return '<span class="strategy-badge strategy-activate">促活</span><span class="strategy-badge strategy-convert">促转化</span>'
                else:
                    return '<span class="strategy-badge strategy-convert">促转化</span>'
            
            segment_display['策略类型'] = segment_display['segment_name'].apply(get_strategy_type)
            
            st.dataframe(
                segment_display[['segment_name', '策略类型', 'customer_count', 'ltv_mean', 
                                'avg_purchases', 'avg_amount', 'avg_prob_alive', 
                                'avg_reactivation_prob', 'churn_rate']],
                use_container_width=True,
                hide_index=True,
                column_config={
                    'segment_name': '客群名称',
                    'customer_count': '客户数',
                    'ltv_mean': '平均LTV',
                    'avg_purchases': '平均购买次数',
                    'avg_amount': '平均客单价',
                    'avg_prob_alive': '平均活跃度(%)',
                    'avg_reactivation_prob': '平均再激活概率(%)',
                    'churn_rate': '流失率(%)',
                    '策略类型': st.column_config.MarkdownColumn('策略类型')
                }
            )
        
        with col2:
            st.subheader("客群分布")
            
            fig = px.pie(
                st.session_state.segment_stats,
                values='customer_count',
                names='segment_name',
                title='各客群客户数占比',
                color_discrete_sequence=px.colors.qualitative.Set3
            )
            st.plotly_chart(fig, use_container_width=True)
        
        st.markdown("---")
        
        col3, col4 = st.columns(2)
        
        with col3:
            st.subheader("客群LTV对比")
            fig = px.bar(
                st.session_state.segment_stats,
                x='segment_name',
                y='ltv_mean',
                color='segment_name',
                title='各客群平均LTV',
                text_auto='.2s',
                color_discrete_sequence=px.colors.qualitative.Set3
            )
            st.plotly_chart(fig, use_container_width=True)
        
        with col4:
            st.subheader("客群特征雷达图")
            
            features = ['avg_purchases', 'avg_amount', 'avg_prob_alive', 'customer_count']
            feature_labels = ['购买频次', '客单价', '活跃度', '客户规模']
            
            fig = go.Figure()
            
            for _, row in st.session_state.segment_stats.iterrows():
                values = []
                for f in features:
                    if f == 'customer_count':
                        values.append(row[f] / st.session_state.segment_stats[f].max())
                    elif f == 'avg_prob_alive':
                        values.append(row[f])
                    else:
                        values.append(row[f] / st.session_state.segment_stats[f].max())
                
                fig.add_trace(go.Scatterpolar(
                    r=values,
                    theta=feature_labels,
                    fill='toself',
                    name=row['segment_name']
                ))
            
            fig.update_layout(
                polar=dict(radialaxis=dict(visible=True, range=[0, 1])),
                showlegend=True,
                title='客群特征对比'
            )
            st.plotly_chart(fig, use_container_width=True)
        
        st.markdown("---")
        st.subheader("📋 各客群详细画像")
        
        selected_segment = st.selectbox("选择客群查看详情", st.session_state.segment_stats['segment_name'].unique())
        segment_id = st.session_state.segment_stats[st.session_state.segment_stats['segment_name'] == selected_segment]['segment'].values[0]
        profile = st.session_state.analyzer.get_segment_profile(st.session_state.model_data, st.session_state.ltv_data, segment_id)
        
        col5, col6, col7, col8 = st.columns(4)
        with col5:
            st.write("**基本统计**")
            st.write(f"- 客户数: {profile['customer_count']}")
            st.write(f"- 平均LTV: ¥{profile['avg_ltv']:,.2f}")
            st.write(f"- 平均购买频次: {profile['avg_frequency']:.2f}")
            st.write(f"- 平均Recency: {profile['avg_recency']:.1f}天")
        with col6:
            st.write("**活跃度与流失**")
            st.write(f"- 平均活跃度: {profile['avg_prob_alive']*100:.1f}%")
            st.write(f"- 平均再激活概率: {profile['avg_reactivation_prob']*100:.1f}%")
            st.write(f"- 流失客户数: {profile['churn_count']}")
            st.write(f"- 流失率: {profile['churn_rate']*100:.1f}%")
        with col7:
            st.write("**会员等级分布**")
            if profile['membership_distribution']:
                for level, count in profile['membership_distribution'].items():
                    st.write(f"- {level}: {count}")
        with col8:
            st.write("**地域分布**")
            if profile['region_distribution']:
                for region, count in sorted(profile['region_distribution'].items(), key=lambda x: -x[1])[:5]:
                    st.write(f"- {region}: {count}")
    
    with tab4:
        st.header("🎯 策略建议")
        
        st.subheader("📢 各客群运营策略")
        
        for idx, row in st.session_state.segment_stats.iterrows():
            segment_name = row['segment_name']
            profile = st.session_state.analyzer.get_segment_profile(st.session_state.model_data, st.session_state.ltv_data, row['segment'])
            strategy = st.session_state.engine.generate_segment_strategy(segment_name, profile, row)
            
            strategy_type = strategy.get('strategy_type', '通用')
            type_color = {
                '维护': '#FFF3CD',
                '维护+促活': '#E7F5FF',
                '促活': '#D1ECF1',
                '促活+促转化': '#F0FFF4',
                '促转化': '#D4EDDA'
            }.get(strategy_type, '#f0f2f6')
            
            with st.expander(f"📌 {segment_name} - 策略类型: {strategy_type} (优先级: {strategy['priority']})", expanded=(idx == 0)):
                st.markdown(f"""
                <div style="background-color: {type_color}; padding: 15px; border-radius: 8px; margin-bottom: 15px;">
                    <strong>整体目标:</strong> {strategy['overall_goal']}
                </div>
                """, unsafe_allow_html=True)
                
                for key, value in strategy.items():
                    if key in ['segment_name', 'strategy_type', 'overall_goal', 'priority', 'customer_count', 'avg_ltv', 'churn_rate', 'avg_reactivation_prob']:
                        continue
                    if isinstance(value, list) and len(value) > 0 and isinstance(value[0], dict):
                        st.markdown(f"**{key.replace('_', ' ').title()}**:")
                        for item in value:
                            if 'strategy' in item:
                                st.write(f"- **{item['strategy']}**: {item['description']}")
                                if 'expected_impact' in item:
                                    st.write(f"  预期效果: {item['expected_impact']}")
                                if 'implementation_cost' in item:
                                    st.write(f"  实施成本: {item['implementation_cost']}")
                            elif 'action' in item:
                                st.write(f"- **{item['action']}**: {item['description']}")
                                if 'priority' in item:
                                    st.write(f"  优先级: {item['priority']}, 截止: {item.get('deadline', 'N/A')}")
                    elif isinstance(value, list) and len(value) > 0:
                        st.markdown(f"**{key.replace('_', ' ').title()}**:")
                        for item in value:
                            st.write(f"- {item}")
        
        st.markdown("---")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("⚠️ 流失预警")
            churn_warning = st.session_state.engine.generate_churn_warning(st.session_state.ltv_data)
            
            st.metric("风险客户数", f"{churn_warning['at_risk_count']}", 
                     delta=f"{churn_warning['at_risk_percentage']:.1f}%")
            st.metric("风险LTV总额", f"¥{churn_warning['total_ltv_at_risk']:,.2f}")
            
            st.write("**建议行动**:")
            for action in churn_warning['recommended_actions']:
                st.write(f"- {action}")
        
        with col2:
            st.subheader("💰 预算分配建议")
            budget = st.session_state.engine.generate_budget_allocation(st.session_state.segment_stats)
            
            budget_df = pd.DataFrame(budget)
            budget_df['customer_share'] = budget_df['customer_share'].round(1)
            budget_df['ltv_share'] = budget_df['ltv_share'].round(1)
            budget_df['suggested_budget_pct'] = budget_df['suggested_budget_pct'].round(1)
            budget_df['expected_roi'] = budget_df['expected_roi'].round(2)
            
            st.dataframe(
                budget_df,
                use_container_width=True,
                hide_index=True,
                column_config={
                    'segment': '客群',
                    'strategy_type': '策略类型',
                    'customer_count': '客户数',
                    'customer_share': '客户占比(%)',
                    'ltv_share': 'LTV占比(%)',
                    'suggested_budget_pct': '建议预算(%)',
                    'expected_roi': '预期ROI'
                }
            )
        
        st.markdown("---")
        st.subheader("📅 行动计划")
        
        action_plan = st.session_state.engine.generate_action_plan(
            st.session_state.ltv_data, 
            st.session_state.segment_stats
        )
        
        col3, col4, col5 = st.columns(3)
        
        with col3:
            st.markdown("**🔴 立即行动**")
            for action in action_plan['immediate_actions']:
                st.info(f"**{action['action']}**\n\n{action['description']}\n\n优先级: {action['priority']} | 截止: {action['deadline']} | 类型: {action['strategy_type']}")
        
        with col4:
            st.markdown("**🟡 短期行动**")
            for action in action_plan['short_term_actions']:
                st.warning(f"**{action['action']}**\n\n{action['description']}\n\n优先级: {action['priority']} | 截止: {action['deadline']} | 类型: {action['strategy_type']}")
        
        with col5:
            st.markdown("**🟢 长期战略**")
            for action in action_plan['long_term_strategies']:
                st.success(f"**{action['action']}**\n\n{action['description']}\n\n优先级: {action['priority']} | 截止: {action['deadline']} | 类型: {action['strategy_type']}")
    
    with tab5:
        st.header("🔄 再激活分析")
        
        reactivation_plan = st.session_state.engine.generate_reactivation_plan(
            st.session_state.ltv_data, 
            st.session_state.segment_stats
        )
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("总流失客户", f"{reactivation_plan['total_churned']:,}")
        with col2:
            st.metric("整体流失率", f"{reactivation_plan['churn_rate']:.1f}%")
        with col3:
            st.metric("潜在召回价值", f"¥{reactivation_plan['total_potential_value']:,.2f}")
        
        st.markdown("---")
        
        st.subheader("📊 各客群流失与再激活分析")
        if reactivation_plan['segment_breakdown']:
            reactivation_df = pd.DataFrame(reactivation_plan['priority_list'])
            reactivation_df['avg_ltv'] = reactivation_df['avg_ltv'].round(2)
            reactivation_df['avg_reactivation_prob'] = (reactivation_df['avg_reactivation_prob'] * 100).round(1)
            reactivation_df['potential_value'] = reactivation_df['potential_value'].round(2)
            
            st.dataframe(
                reactivation_df,
                use_container_width=True,
                hide_index=True,
                column_config={
                    'segment': '客群',
                    'churned_count': '流失客户数',
                    'avg_ltv': '平均LTV',
                    'avg_reactivation_prob': '平均再激活概率(%)',
                    'potential_value': '潜在召回价值'
                }
            )
            
            st.markdown("---")
            
            col_chart1, col_chart2 = st.columns(2)
            
            with col_chart1:
                fig = px.bar(
                    reactivation_df,
                    x='segment',
                    y='churned_count',
                    title='各客群流失客户数',
                    color='segment',
                    text_auto=True
                )
                st.plotly_chart(fig, use_container_width=True)
            
            with col_chart2:
                fig = px.bar(
                    reactivation_df,
                    x='segment',
                    y='potential_value',
                    title='各客群潜在召回价值',
                    color='segment',
                    text_auto='.2s'
                )
                st.plotly_chart(fig, use_container_width=True)
        
        st.markdown("---")
        
        st.subheader("📋 流失客户详情")
        churned_data = st.session_state.ltv_data[st.session_state.ltv_data['is_churned'] == True].copy()
        churned_data['probability_alive'] = (churned_data['probability_alive'] * 100).round(1)
        churned_data['reactivation_prob'] = (churned_data['reactivation_prob'] * 100).round(1)
        
        st.dataframe(
            churned_data[['customer_id', 'ltv', 'predicted_purchases', 'probability_alive', 
                         'reactivation_prob', 'segment']].sort_values('ltv', ascending=False),
            use_container_width=True,
            hide_index=True,
            column_config={
                'customer_id': '客户ID',
                'ltv': '预测LTV',
                'predicted_purchases': '预计购买次数',
                'probability_alive': '活跃度(%)',
                'reactivation_prob': '再激活概率(%)',
                'segment': '客群'
            }
        )
        
        st.markdown("---")
        
        st.subheader("🎯 再激活优先级建议")
        if reactivation_plan['priority_list']:
            for idx, item in enumerate(reactivation_plan['priority_list']):
                st.markdown(f"""
                <div style="background-color: #f8f9fa; padding: 15px; border-radius: 8px; margin-bottom: 10px; border-left: 4px solid {'#dc3545' if idx == 0 else '#ffc107' if idx == 1 else '#28a745'};">
                    <strong>优先级 {idx + 1}: {item['segment']}</strong><br>
                    流失客户: {item['churned_count']} 人 | 潜在召回价值: ¥{item['potential_value']:,.2f}<br>
                    建议: 对该客群流失客户开展召回 campaign，优先联系高LTV客户
                </div>
                """, unsafe_allow_html=True)
    
    with tab6:
        st.header("📉 模型详情")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("BG/NBD模型参数")
            bg_params = st.session_state.bg_nbd.get_params()
            bg_summary = st.session_state.bg_nbd.get_model_summary()
            
            params_df = pd.DataFrame({
                '参数': ['r', 'alpha', 'a', 'b'],
                '值': [bg_params['r'], bg_params['alpha'], bg_params['a'], bg_params['b']],
                '描述': [
                    '购买率的Gamma分布形状参数',
                    '购买率的Gamma分布尺度参数',
                    '流失率的Beta分布参数',
                    '流失率的Beta分布参数'
                ]
            })
            st.dataframe(params_df, use_container_width=True, hide_index=True)
            
            st.write("**模型摘要:**")
            st.dataframe(bg_summary, use_container_width=True)
        
        with col2:
            st.subheader("Gamma-Gamma模型参数")
            gg_params = st.session_state.gg.get_params()
            gg_summary = st.session_state.gg.get_model_summary()
            
            gg_params_df = pd.DataFrame({
                '参数': ['p', 'q', 'v'],
                '值': [gg_params['p'], gg_params['q'], gg_params['v']],
                '描述': [
                    '客单价的Gamma分布形状参数',
                    '混合Gamma分布的形状参数',
                    '混合Gamma分布的尺度参数'
                ]
            })
            st.dataframe(gg_params_df, use_container_width=True, hide_index=True)
            
            st.write("**模型摘要:**")
            st.dataframe(gg_summary, use_container_width=True)
        
        st.markdown("---")
        
        col3, col4 = st.columns(2)
        
        with col3:
            st.subheader("再激活概率模型")
            st.info("""
            **再激活概率计算逻辑:**
            
            1. 基于BG/NBD模型识别流失客户（活跃度 < 流失阈值）
            2. 考虑历史购买频次、活跃度、购买率等因素
            3. 计算流失客户在未来N个月内回归的概率
            4. 调整LTV预测：LTV = 基础预测 × 再激活概率（对于流失客户）
            """)
            
            reactivation_stats = st.session_state.ltv_data.groupby('is_churned').agg({
                'reactivation_prob': ['mean', 'min', 'max'],
                'ltv': 'count'
            }).round(3)
            reactivation_stats.columns = ['平均再激活概率', '最小概率', '最大概率', '客户数']
            st.dataframe(reactivation_stats, use_container_width=True)
        
        with col4:
            st.subheader("模型预测结果分布")
            fig = px.scatter(
                st.session_state.ltv_data,
                x='predicted_purchases',
                y='predicted_avg_amount',
                size='ltv',
                color='segment',
                symbol='is_churned',
                hover_data=['customer_id', 'ltv', 'probability_alive', 'reactivation_prob'],
                title='购买次数 vs 客单价预测 (气泡大小=LTV, 形状=是否流失)',
                labels={
                    'predicted_purchases': '预测购买次数',
                    'predicted_avg_amount': '预测客单价 (¥)'
                }
            )
            st.plotly_chart(fig, use_container_width=True)
    
    with tab7:
        st.header("📋 原始数据")
        
        data_option = st.selectbox(
            "选择查看的数据",
            ["LTV预测结果", "客户画像", "交易历史", "行为日志", "建模用RFM数据"]
        )
        
        if data_option == "LTV预测结果":
            display_data = st.session_state.ltv_data.copy()
            display_data['probability_alive'] = (display_data['probability_alive'] * 100).round(1)
            display_data['reactivation_prob'] = (display_data['reactivation_prob'] * 100).round(1)
            display_data['is_churned'] = display_data['is_churned'].map({True: '是', False: '否'})
            st.dataframe(
                display_data.drop(columns=['ltv_quartile'], errors='ignore'),
                use_container_width=True,
                hide_index=True
            )
        elif data_option == "客户画像":
            st.dataframe(st.session_state.profiles, use_container_width=True, hide_index=True)
        elif data_option == "交易历史":
            st.dataframe(st.session_state.transactions, use_container_width=True, hide_index=True)
        elif data_option == "行为日志":
            st.dataframe(st.session_state.behavior_logs, use_container_width=True, hide_index=True)
        else:
            st.dataframe(st.session_state.model_data, use_container_width=True, hide_index=True)
        
        st.download_button(
            "⬇️ 下载LTV预测结果CSV",
            st.session_state.ltv_data.to_csv(index=False).encode('utf-8-sig'),
            "ltv_predictions.csv",
            "text/csv",
            key='download-ltv'
        )
    
    with tab8:
        st.header("🎁 营销活动模拟")
        
        st.info("模拟优惠券发放后的LTV变化预测，评估营销活动效果")
        
        col1, col2 = st.columns([1, 1.5])
        
        with col1:
            st.subheader("活动配置")
            
            coupon_type = st.selectbox(
                "优惠券类型",
                ['满减券', '折扣券', '免邮券', '满赠券', '新人券'],
                help="选择不同类型的优惠券进行模拟"
            )
            
            target_segment = st.selectbox(
                "目标客群",
                ['全部'] + list(st.session_state.segment_stats['segment_name'].unique()),
                help="选择发放优惠券的目标客群"
            )
            
            coverage_rate = st.slider(
                "覆盖率",
                min_value=0.1,
                max_value=1.0,
                value=0.3,
                step=0.1,
                help="目标客群中获得优惠券的比例"
            )
            
            future_months_sim = st.slider(
                "预测周期(月)",
                min_value=1,
                max_value=12,
                value=3,
                help="模拟未来几个月的影响"
            )
            
            if st.button("🚀 运行模拟", type="primary"):
                with st.spinner("正在运行营销模拟..."):
                    sim_result, campaign_impact = st.session_state.marketing_simulator.simulate_marketing_campaign(
                        {
                            'name': f'{coupon_type}活动',
                            'target_segment': None if target_segment == '全部' else target_segment,
                            'coupon_type': coupon_type,
                            'coverage_rate': coverage_rate,
                            'duration_months': future_months_sim
                        },
                        future_months=future_months_sim
                    )
                    st.session_state.sim_result = sim_result
                    st.session_state.campaign_impact = campaign_impact
        
        with col2:
            st.subheader("活动效果预测")
            
            if st.session_state.get('campaign_impact'):
                impact = st.session_state.campaign_impact
                
                col_m1, col_m2, col_m3, col_m4 = st.columns(4)
                with col_m1:
                    st.metric("活动触达人数", f"{impact['total_reach']:,}")
                with col_m2:
                    st.metric("LTV增长总额", f"¥{impact['total_ltv_increase']:,.2f}")
                with col_m3:
                    st.metric("平均LTV增长", f"{impact['avg_ltv_increase_pct']:.1f}%")
                with col_m4:
                    st.metric("预计ROI", f"{impact['estimated_roi']:.2f}")
                
                st.markdown("---")
                
                st.write("**活动详情**")
                st.write(f"- 活动名称: {impact['campaign_name']}")
                st.write(f"- 目标客群: {impact['target_segment']}")
                st.write(f"- 优惠券类型: {impact['coupon_type']}")
                st.write(f"- 活动周期: {impact['duration_months']}个月")
                st.write(f"- 预计成本: ¥{impact['estimated_cost']:,.2f}")
            else:
                st.info("请在左侧配置活动参数并点击'运行模拟'")
    
    with tab9:
        st.header("📊 异动分析")
        
        st.info("识别LTV显著变化的用户群，监控客户价值波动")
        
        col1, col2 = st.columns([1, 1.5])
        
        with col1:
            st.subheader("分析配置")
            
            change_threshold = st.slider(
                "变化阈值(%)",
                min_value=5,
                max_value=50,
                value=20,
                help="LTV变化超过该阈值的客户被视为显著变化"
            )
            
            if st.button("🔍 检测异动", type="primary"):
                with st.spinner("正在检测异动..."):
                    change_report = st.session_state.change_detector.generate_change_report(
                        st.session_state.ltv_data,
                        st.session_state.historical_ltv_data,
                        ltv_threshold_pct=change_threshold
                    )
                    st.session_state.change_report = change_report
        
        with col2:
            st.subheader("异动统计")
            
            if st.session_state.get('change_report'):
                report = st.session_state.change_report
                
                col_d1, col_d2, col_d3, col_d4 = st.columns(4)
                with col_d1:
                    st.metric("LTV显著增长客户", f"{report['n_increases']:,}")
                with col_d2:
                    st.metric("LTV显著下降客户", f"{report['n_decreases']:,}")
                with col_d3:
                    st.metric("LTV净变化", f"¥{report['net_ltv_change']:,.2f}")
                with col_d4:
                    st.metric("流失风险客户", f"{report['churn_risk_count']:,}")
                
                st.markdown("---")
                
                if len(report['top_increases']) > 0:
                    st.subheader("📈 LTV增长Top 10")
                    increases = report['top_increases'].copy()
                    increases['ltv_change_pct'] = increases['ltv_change_pct'].round(1)
                    st.dataframe(
                        increases[['customer_id', 'ltv_change', 'ltv_change_pct']],
                        use_container_width=True,
                        hide_index=True
                    )
                
                if len(report['top_decreases']) > 0:
                    st.subheader("📉 LTV下降Top 10")
                    decreases = report['top_decreases'].copy()
                    decreases['ltv_change_pct'] = decreases['ltv_change_pct'].round(1)
                    st.dataframe(
                        decreases[['customer_id', 'ltv_change', 'ltv_change_pct']],
                        use_container_width=True,
                        hide_index=True
                    )
            else:
                st.info("请点击'检测异动'按钮开始分析")
    
    with tab10:
        st.header("⚡ 实时LTV更新")
        
        st.info("支持增量数据更新模型，实现实时LTV监控")
        
        col1, col2 = st.columns([1, 1.5])
        
        with col1:
            st.subheader("更新配置")
            
            update_type = st.selectbox(
                "更新方式",
                ['模拟增量更新', '批量更新'],
                help="选择更新方式"
            )
            
            if update_type == '模拟增量更新':
                n_days = st.slider("模拟天数", min_value=1, max_value=30, value=7)
                
                if st.button("🔄 运行更新", type="primary"):
                    with st.spinner("正在模拟增量更新..."):
                        daily_results = st.session_state.realtime_updater.simulate_daily_updates(
                            st.session_state.transactions,
                            n_days=n_days
                        )
                        st.session_state.daily_results = daily_results
            else:
                if st.button("📦 执行批量更新", type="primary"):
                    with st.spinner("正在执行批量更新..."):
                        st.success("批量更新完成！")
        
        with col2:
            st.subheader("更新状态")
            
            status = st.session_state.realtime_updater.get_update_status()
            
            col_u1, col_u2, col_u3 = st.columns(3)
            with col_u1:
                st.metric("模型版本", f"v{status['model_version']}")
            with col_u2:
                st.metric("累计更新次数", status['total_updates'])
            with col_u3:
                st.metric("状态", status['status'])
            
            st.markdown("---")
            
            st.subheader("更新计划")
            schedule = st.session_state.realtime_updater.generate_update_schedule('daily')
            st.write(f"**{schedule['description']}**")
            for i, task in enumerate(schedule['tasks'], 1):
                st.write(f"{i}. {task}")
            
            if st.session_state.get('daily_results'):
                st.markdown("---")
                st.subheader("每日更新数据")
                daily_df = pd.DataFrame.from_dict(st.session_state.daily_results, orient='index')
                st.dataframe(daily_df, use_container_width=True)

st.markdown("---")
st.markdown("**技术栈**: Python | Lifetimes | Scikit-learn | Streamlit | Plotly | 支持营销模拟/异动分析/实时更新")
