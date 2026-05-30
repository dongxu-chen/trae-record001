import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import matplotlib.pyplot as plt
import seaborn as sns
import shap
import networkx as nx

from data_generator import (
    generate_attribution_data, get_user_journeys, 
    calculate_channel_metrics, calculate_conversion_cycle,
    apply_attribution_window
)
from attribution_models import run_all_attribution_models, regularize_weights
from shap_attribution import shap_based_attribution, combine_all_attributions
from budget_optimizer import run_budget_analysis
from cross_device_attribution import cross_device_attribution_analysis
from mmm_analysis import run_mmm_analysis
from incrementality_analysis import run_full_incrementality_analysis

st.set_page_config(
    page_title="用户转化归因分析平台",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("📊 用户转化归因分析平台")
st.markdown("---")

@st.cache_data
def load_data(n_users=5000):
    users_df, touchpoints_df = generate_attribution_data(n_users=n_users)
    journeys_df = get_user_journeys(touchpoints_df)
    channel_metrics = calculate_channel_metrics(touchpoints_df)
    cycle_stats, cycle_details = calculate_conversion_cycle(touchpoints_df, users_df)
    return users_df, touchpoints_df, journeys_df, channel_metrics, cycle_stats, cycle_details

@st.cache_data
def apply_window_and_analyze(touchpoints_df, users_df, window_days, reg_alpha, shap_reg):
    filtered_tp, actual_window = apply_attribution_window(
        touchpoints_df, users_df, window_days=window_days
    )
    
    rule_attributions = run_all_attribution_models(filtered_tp)
    shap_attr, shap_model = shap_based_attribution(
        filtered_tp, regularization_strength=shap_reg
    )
    combined = combine_all_attributions(
        rule_attributions, shap_attr, prior_alpha=reg_alpha
    )
    return rule_attributions, shap_attr, combined, shap_model, filtered_tp, actual_window

@st.cache_data
def run_budget_optimization(touchpoints_df, attribution_df, total_budget):
    return run_budget_analysis(touchpoints_df, attribution_df, total_budget=total_budget)

@st.cache_data
def run_cross_device_analysis(_users_df, _touchpoints_df):
    return cross_device_attribution_analysis(_touchpoints_df, _users_df)

@st.cache_data
def run_marketing_mix_modeling(_users_df, _touchpoints_df, target='total_conversions'):
    return run_mmm_analysis(_touchpoints_df, _users_df, target=target)

@st.cache_data
def run_incrementality_analysis(_touchpoints_df, _users_df, _attribution_df, weight_col='ensemble_weight'):
    return run_full_incrementality_analysis(
        _touchpoints_df, _users_df, _attribution_df, weight_col
    )

with st.sidebar:
    st.header("⚙️ 分析设置")
    
    n_users = st.slider("模拟用户数量", min_value=1000, max_value=10000, value=5000, step=1000)
    
    st.markdown("### 🪟 归因窗口期")
    use_auto_window = st.checkbox("按中位数转化周期自动设置", value=True)
    window_days = None
    if not use_auto_window:
        window_days = st.number_input(
            "自定义窗口期 (天)",
            min_value=1, max_value=180, value=30, step=1
        )
    
    st.markdown("### 📐 正则化控制")
    reg_alpha = st.slider(
        "Dirichlet先验强度 (集成权重平滑)",
        min_value=0.0, max_value=5.0, value=1.0, step=0.1,
        help="值越大，各渠道权重越趋向均匀分布，防止极端波动"
    )
    shap_reg = st.slider(
        "SHAP模型正则化强度",
        min_value=0.5, max_value=3.0, value=1.0, step=0.1,
        help="值越大，模型越保守，防止过拟合"
    )
    
    st.markdown("### 🎯 归因方法")
    attribution_method = st.selectbox(
        "主要归因方法",
        ["集成归因", "末次点击", "首次点击", "线性归因", "时间衰减", "位置归因", "Markov链", "SHAP数据驱动"],
        index=0
    )
    
    total_budget = st.number_input(
        "总营销预算 (¥)",
        min_value=1000,
        max_value=100000,
        value=20000,
        step=1000
    )
    
    st.markdown("---")
    st.markdown("### 📋 功能说明")
    st.markdown("""
    - **数据概览**: 渠道转化数据 + 转化周期统计
    - **归因分析**: 多模型归因对比 (含正则化)
    - **跨设备归因**: 登录用户跨设备关联分析
    - **营销组合建模**: 渠道协同效应分析
    - **增量性评估**: 有无渠道的转化差异
    - **SHAP分析**: 数据驱动归因解释
    - **预算优化**: 边际收益曲线 + 最优预算点
    - **深度分析**: 转化漏斗和用户旅程模式
    """)

with st.spinner("正在生成数据并进行全面分析..."):
    users_df, touchpoints_df, journeys_df, channel_metrics, cycle_stats, cycle_details = load_data(n_users=n_users)
    
    rule_attributions, shap_attr, combined, shap_model, filtered_tp, actual_window = apply_window_and_analyze(
        touchpoints_df, users_df, window_days, reg_alpha, shap_reg
    )
    
    budget_results = run_budget_optimization(filtered_tp, combined, total_budget=total_budget)
    
    cross_device_results = run_cross_device_analysis(users_df, touchpoints_df)
    
    mmm_results = run_marketing_mix_modeling(users_df, touchpoints_df)
    
    inc_results = run_incrementality_analysis(
        filtered_tp, users_df, combined, weight_col='ensemble_weight'
    )

tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8 = st.tabs([
    "📈 数据概览", 
    "🎯 归因分析",
    "📱 跨设备归因",
    "🔗 营销组合建模",
    "📊 增量性评估",
    "🔍 SHAP解释", 
    "💰 预算优化",
    "📉 深度分析"
])

with tab1:
    st.header("📈 数据概览")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("总用户数", f"{len(users_df):,}")
    with col2:
        conversion_rate = users_df['converted'].mean() * 100
        st.metric("转化率", f"{conversion_rate:.1f}%")
    with col3:
        total_value = users_df['conversion_value'].sum()
        st.metric("总转化价值", f"¥{total_value:,.0f}")
    with col4:
        total_cost = touchpoints_df['cost'].sum()
        st.metric("总营销成本", f"¥{total_cost:,.0f}")
    
    st.markdown("---")
    
    st.subheader("🪟 转化周期与归因窗口期")
    
    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        st.metric("中位数周期", f"{cycle_stats['median_days']:.1f} 天")
    with col2:
        st.metric("平均周期", f"{cycle_stats['mean_days']:.1f} 天")
    with col3:
        st.metric("P75周期", f"{cycle_stats['p75_days']:.1f} 天")
    with col4:
        st.metric("P90周期", f"{cycle_stats['p90_days']:.1f} 天")
    with col5:
        st.metric("实际窗口期", f"{actual_window:.1f} 天", 
                  delta=f"推荐 {cycle_stats['recommended_window_days']:.1f} 天 (1.5×中位数)")
    
    fig_cycle = px.histogram(
        cycle_details,
        x='conversion_cycle_days',
        nbins=50,
        title='转化周期分布 (首次触达到转化)',
        labels={'conversion_cycle_days': '转化周期 (天)'},
        color_discrete_sequence=['#636EFA']
    )
    fig_cycle.add_vline(
        x=cycle_stats['median_days'], line_dash="dash", line_color="red",
        annotation_text=f"中位数: {cycle_stats['median_days']:.1f}天"
    )
    fig_cycle.add_vline(
        x=actual_window, line_dash="dash", line_color="green",
        annotation_text=f"窗口期: {actual_window:.1f}天"
    )
    fig_cycle.add_vline(
        x=cycle_stats['p75_days'], line_dash="dot", line_color="orange",
        annotation_text=f"P75: {cycle_stats['p75_days']:.1f}天"
    )
    st.plotly_chart(fig_cycle, use_container_width=True)
    
    st.markdown("---")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("渠道转化概览")
        
        fig_channel = px.bar(
            channel_metrics.sort_values('users_converted', ascending=True),
            x='users_converted',
            y='channel',
            orientation='h',
            title='各渠道转化用户数',
            color='conversion_rate',
            color_continuous_scale='Viridis',
            labels={'users_converted': '转化用户数', 'channel': '渠道', 'conversion_rate': '转化率%'}
        )
        st.plotly_chart(fig_channel, use_container_width=True)
    
    with col2:
        st.subheader("渠道ROI对比")
        
        fig_roi = px.scatter(
            channel_metrics,
            x='total_cost',
            y='total_conversion_value',
            size='users_reached',
            color='roi',
            hover_name='channel',
            title='渠道投入产出分析',
            labels={'total_cost': '总成本', 'total_conversion_value': '总转化价值', 'roi': 'ROI%'},
            color_continuous_scale='RdYlGn',
            size_max=50
        )
        st.plotly_chart(fig_roi, use_container_width=True)
    
    st.markdown("---")
    
    st.subheader("用户旅程分析")
    
    journey_lengths = touchpoints_df.groupby('user_id').size().value_counts().sort_index()
    fig_journey = px.bar(
        x=journey_lengths.index,
        y=journey_lengths.values,
        title='用户旅程长度分布',
        labels={'x': '接触点数量', 'y': '用户数'}
    )
    st.plotly_chart(fig_journey, use_container_width=True)

with tab2:
    st.header("🎯 归因分析")
    
    attribution_mapping = {
        "末次点击": "last_touch_weight",
        "首次点击": "first_touch_weight",
        "线性归因": "linear_weight",
        "时间衰减": "time_decay_weight",
        "位置归因": "position_weight",
        "Markov链": "markov_weight",
        "SHAP数据驱动": "shap_weight",
        "集成归因": "ensemble_weight"
    }
    
    weight_col = attribution_mapping[attribution_method]
    
    st.info(f"🪟 归因窗口期: {actual_window:.1f} 天 | 📐 正则化先验 α={reg_alpha}")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader(f"{attribution_method} - 渠道贡献度")
        
        display_df = combined.copy()
        display_df = display_df.sort_values(weight_col, ascending=True)
        
        fig = px.bar(
            display_df,
            x=weight_col,
            y='channel',
            orientation='h',
            title=f'基于{attribution_method}的渠道贡献度',
            labels={weight_col: '贡献权重', 'channel': '渠道'},
            color=weight_col,
            color_continuous_scale='Blues',
            text=display_df[weight_col].apply(lambda x: f'{x*100:.1f}%')
        )
        fig.update_traces(textposition='outside')
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        st.subheader("归因结果详情")
        
        result_df = combined[['channel', weight_col]].copy()
        result_df.columns = ['渠道', '贡献权重']
        result_df['贡献权重'] = result_df['贡献权重'].apply(lambda x: f'{x*100:.2f}%')
        result_df = result_df.sort_values('贡献权重', ascending=False, key=lambda x: x.str.rstrip('%').astype(float))
        result_df = result_df.reset_index(drop=True)
        result_df.index = result_df.index + 1
        
        st.dataframe(result_df, use_container_width=True, height=400)
    
    st.markdown("---")
    
    st.subheader("正则化效果对比")
    
    raw_cols = ['last_touch_weight', 'first_touch_weight', 'linear_weight',
                'time_decay_weight', 'position_weight', 'markov_weight', 'shap_weight']
    reg_cols = [c + '_regularized' for c in raw_cols]
    available_reg = [c for c in reg_cols if c in combined.columns]
    
    if available_reg:
        compare_data = []
        for col_raw, col_reg in zip(raw_cols, reg_cols):
            if col_reg in combined.columns:
                raw_std = combined[col_raw].std()
                reg_std = combined[col_reg].std()
                model_name = col_raw.replace('_weight', '')
                compare_data.append({
                    'model': model_name,
                    'raw_std': raw_std,
                    'regularized_std': reg_std,
                    'reduction': (1 - reg_std / raw_std) * 100 if raw_std > 0 else 0
                })
        
        compare_df = pd.DataFrame(compare_data)
        
        fig_reg = go.Figure()
        fig_reg.add_trace(go.Bar(
            name='原始权重标准差',
            x=compare_df['model'],
            y=compare_df['raw_std'],
            marker_color='lightcoral'
        ))
        fig_reg.add_trace(go.Bar(
            name='正则化后标准差',
            x=compare_df['model'],
            y=compare_df['regularized_std'],
            marker_color='steelblue'
        ))
        fig_reg.update_layout(
            title='正则化前后渠道权重波动对比 (标准差越小越稳定)',
            barmode='group',
            xaxis_title='归因模型',
            yaxis_title='权重标准差'
        )
        st.plotly_chart(fig_reg, use_container_width=True)
    
    st.markdown("---")
    
    st.subheader("多模型归因对比")
    
    compare_cols = [
        'last_touch_weight', 'first_touch_weight', 'linear_weight',
        'time_decay_weight', 'position_weight', 'markov_weight', 'shap_weight'
    ]
    compare_names = [
        '末次点击', '首次点击', '线性', '时间衰减', '位置', 'Markov链', 'SHAP'
    ]
    
    heatmap_data = combined[['channel'] + compare_cols].copy()
    heatmap_data.columns = ['channel'] + compare_names
    heatmap_data = heatmap_data.set_index('channel')
    
    fig_heatmap = go.Figure(data=go.Heatmap(
        z=heatmap_data.values,
        x=heatmap_data.columns,
        y=heatmap_data.index,
        colorscale='RdBu_r',
        text=heatmap_data.values,
        texttemplate='%{text:.1%}',
        textfont={"size": 10},
        hoverongaps=False
    ))
    fig_heatmap.update_layout(
        title='各归因模型渠道权重对比热力图',
        xaxis_title='归因模型',
        yaxis_title='渠道',
        height=500
    )
    st.plotly_chart(fig_heatmap, use_container_width=True)

with tab3:
    st.header("📱 跨设备归因")
    
    cd_summary = cross_device_results['summary']
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("登录用户数", f"{cd_summary['logged_in_users']:,}")
    with col2:
        st.metric("跨设备用户", f"{cd_summary['cross_device_users']:,}", 
                  delta=f"{cd_summary['cross_device_rate']}%")
    with col3:
        st.metric("跨设备转化", f"{cd_summary['cross_device_conversion_rate']}%")
    with col4:
        st.metric("多设备价值提升", f"{cd_summary['cross_device_value_lift']}%",
                  delta="vs 单设备用户")
    
    st.markdown("---")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("设备类型分布")
        
        device_stats = cross_device_results['device_analysis']['device_stats']
        
        fig_device = px.bar(
            device_stats,
            x='device',
            y='unique_users',
            color='conversion_rate',
            title='各设备触达用户与转化率',
            labels={'unique_users': '触达用户数', 'device': '设备', 'conversion_rate': '转化率%'},
            color_continuous_scale='Blues',
            text=device_stats['conversion_rate'].apply(lambda x: f'{x:.1f}%')
        )
        st.plotly_chart(fig_device, use_container_width=True)
    
    with col2:
        st.subheader("设备归因权重")
        
        device_attr = cross_device_results['attribution_results']['device_attribution']
        
        fig_device_attr = px.pie(
            device_attr,
            values='device_conversions',
            names='device',
            title='各设备转化贡献占比',
            color_discrete_sequence=px.colors.qualitative.Set2
        )
        st.plotly_chart(fig_device_attr, use_container_width=True)
    
    st.markdown("---")
    
    st.subheader("渠道×设备交叉归因")
    
    device_channel_attr = cross_device_results['attribution_results']['device_channel_attribution']
    
    fig_dc = go.Figure(data=go.Heatmap(
        x=device_channel_attr['device'],
        y=device_channel_attr['channel'],
        z=device_channel_attr['conversions'],
        colorscale='Viridis',
        text=device_channel_attr['conversions'],
        texttemplate='%{text}',
        hoverongaps=False
    ))
    fig_dc.update_layout(
        title='渠道×设备 转化交叉归因 (按末次接触)',
        xaxis_title='设备',
        yaxis_title='渠道',
        height=500
    )
    st.plotly_chart(fig_dc, use_container_width=True)
    
    st.markdown("---")
    
    st.subheader("用户设备使用统计")
    
    device_dist = cross_device_results['device_analysis']['device_distribution']
    
    fig_dist = px.bar(
        x=device_dist.index,
        y=device_dist.values,
        title='用户使用设备数量分布',
        labels={'x': '使用设备数', 'y': '用户数'},
        color=device_dist.index,
        color_discrete_sequence=px.colors.qualitative.Pastel
    )
    st.plotly_chart(fig_dist, use_container_width=True)
    
    with st.expander("📊 登录状态对比"):
        login_stats = cross_device_results['device_analysis']['login_stats']
        login_stats_display = login_stats.copy()
        login_stats_display['is_logged_in'] = login_stats_display['is_logged_in'].map({0: '未登录', 1: '已登录'})
        login_stats_display = login_stats_display[['is_logged_in', 'total_users', 'conversions', 'conversion_rate', 'avg_devices']]
        login_stats_display.columns = ['登录状态', '总用户数', '转化数', '转化率%', '平均设备数']
        st.dataframe(login_stats_display, use_container_width=True)

with tab4:
    st.header("🔗 营销组合建模 (MMM)")
    
    mmm_stats = mmm_results['model_stats']
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("模型 R²", f"{mmm_stats['r2']:.4f}")
    with col2:
        st.metric("CV R² 均值", f"{mmm_stats['cv_r2_mean']:.4f}",
                  delta=f"±{mmm_stats['cv_r2_std']:.4f}")
    with col3:
        st.metric("MAE", f"{mmm_stats['mae']:.4f}")
    with col4:
        st.metric("分析渠道数", f"{len(mmm_results['channels'])}")
    
    st.markdown("---")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("MMM 渠道贡献度")
        
        mmm_contrib = mmm_results['contributions']
        mmm_contrib = mmm_contrib.sort_values('mmm_weight', ascending=True)
        
        fig_mmm = px.bar(
            mmm_contrib,
            x='mmm_weight',
            y='channel',
            orientation='h',
            title='营销组合模型 - 渠道贡献权重',
            labels={'mmm_weight': 'MMM权重', 'channel': '渠道'},
            color='mmm_weight',
            color_continuous_scale='Teal',
            text=mmm_contrib['mmm_weight'].apply(lambda x: f'{x*100:.1f}%')
        )
        fig_mmm.update_traces(textposition='outside')
        st.plotly_chart(fig_mmm, use_container_width=True)
    
    with col2:
        st.subheader("渠道协同效应热力图")
        
        synergy_matrix = mmm_results['synergy_matrix']
        
        fig_syn = px.imshow(
            synergy_matrix,
            labels=dict(color="协同效应"),
            x=synergy_matrix.columns,
            y=synergy_matrix.index,
            color_continuous_scale='RdBu_r',
            aspect='auto',
            text_auto='.4f',
            title='渠道间协同效应 (正=协同促进, 负=相互替代)'
        )
        st.plotly_chart(fig_syn, use_container_width=True)
    
    st.markdown("---")
    
    st.subheader("🔥 强协同效应渠道对")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### ✅ 正向协同 (1+1>2)")
        pos_syn = mmm_results['synergy_pairs']['positive_synergies'][:10]
        if pos_syn:
            pos_df = pd.DataFrame(pos_syn, columns=['渠道A', '渠道B', '协同效应'])
            pos_df['协同效应'] = pos_df['协同效应'].apply(lambda x: f'{x:.6f}')
            pos_df.index = pos_df.index + 1
            st.dataframe(pos_df, use_container_width=True)
        else:
            st.info("未发现显著的正向协同效应")
    
    with col2:
        st.markdown("#### ❌ 负向协同 (渠道替代)")
        neg_syn = mmm_results['synergy_pairs']['negative_synergies'][:10]
        if neg_syn:
            neg_df = pd.DataFrame(neg_syn, columns=['渠道A', '渠道B', '协同效应'])
            neg_df['协同效应'] = neg_df['协同效应'].apply(lambda x: f'{x:.6f}')
            neg_df.index = neg_df.index + 1
            st.dataframe(neg_df, use_container_width=True)
        else:
            st.info("未发现显著的负向协同效应")
    
    st.markdown("---")
    
    st.subheader("MMM 时间序列拟合")
    
    mmm_df = mmm_results['mmm_df']
    model = mmm_results['model']
    
    fig_fit = go.Figure()
    fig_fit.add_trace(go.Scatter(
        x=mmm_df['period'],
        y=mmm_df['total_conversions'],
        mode='lines+markers',
        name='实际转化',
        line=dict(color='#636EFA', width=2)
    ))
    
    y_pred = model.model.predict(model.X_scaled)
    fig_fit.add_trace(go.Scatter(
        x=mmm_df['period'],
        y=y_pred,
        mode='lines',
        name='MMM预测',
        line=dict(color='red', width=2, dash='dash')
    ))
    fig_fit.update_layout(
        title='MMM模型拟合效果: 实际 vs 预测转化',
        xaxis_title='时间',
        yaxis_title='周转化数',
        height=400
    )
    st.plotly_chart(fig_fit, use_container_width=True)

with tab5:
    st.header("📊 增量性评估")
    
    st.info("核心分析：对比 **有** 该渠道 vs **无** 该渠道的转化差异，计算渠道的真实增量贡献")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("渠道移除效应")
        
        removal_effect = inc_results['removal_effect']
        removal_plot = removal_effect.sort_values('incremental_conversions', ascending=True)
        
        fig_removal = px.bar(
            removal_plot,
            x='incremental_conversions',
            y='channel',
            orientation='h',
            title='各渠道增量转化数 (移除该渠道损失的转化)',
            labels={'incremental_conversions': '增量转化数', 'channel': '渠道'},
            color='incremental_roi',
            color_continuous_scale='RdYlGn',
            text=removal_plot['incremental_conversions'].apply(lambda x: f'{x:.0f}')
        )
        fig_removal.update_traces(textposition='outside')
        st.plotly_chart(fig_removal, use_container_width=True)
    
    with col2:
        st.subheader("转化率提升对比")
        
        uplift_summary = inc_results['uplift_summary']
        uplift_plot = uplift_summary.sort_values('observed_uplift_pct', ascending=True)
        
        fig_uplift = px.bar(
            uplift_plot,
            x='observed_uplift_pct',
            y='channel',
            orientation='h',
            title='接触该渠道的用户转化率提升',
            labels={'observed_uplift_pct': '转化率提升 (%)', 'channel': '渠道'},
            color='observed_uplift_pct',
            color_continuous_scale='PiYG',
            text=uplift_plot['observed_uplift_pct'].apply(lambda x: f'{x:.1f}%')
        )
        fig_uplift.update_traces(textposition='outside')
        st.plotly_chart(fig_uplift, use_container_width=True)
    
    st.markdown("---")
    
    st.subheader("🔍 单渠道显著性检验")
    
    selected_channel = st.selectbox(
        "选择渠道进行显著性检验",
        inc_results['channels'],
        index=0,
        key='sig_channel'
    )
    
    sig_test = inc_results['significance_tests'][selected_channel]
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric(
            "转化率提升",
            f"{sig_test['observed_diff_conv_pct']:.2f}%",
            delta=f"p={sig_test['p_value_conv']:.4f}"
        )
    with col2:
        st.metric(
            "95%置信区间",
            f"[{sig_test['ci_95_lower_conv']:.2f}%, {sig_test['ci_95_upper_conv']:.2f}%]"
        )
    with col3:
        status = "✅ 统计显著" if sig_test['is_significant_conv'] else "⚠️ 不显著"
        st.metric("显著性", status)
    
    fig_bootstrap = go.Figure()
    
    bootstrap_diffs = sig_test['bootstrap_diffs_conv'] * 100
    fig_bootstrap.add_trace(go.Histogram(
        x=bootstrap_diffs,
        nbins=50,
        name='Bootstrap分布',
        marker_color='lightblue',
        opacity=0.7
    ))
    fig_bootstrap.add_vline(
        x=0, line_dash="dash", line_color="red",
        annotation_text="零假设 (无差异)"
    )
    fig_bootstrap.add_vline(
        x=sig_test['observed_diff_conv_pct'], line_dash="dash", line_color="green",
        annotation_text=f"观测值: {sig_test['observed_diff_conv_pct']:.2f}%"
    )
    fig_bootstrap.update_layout(
        title=f'{selected_channel}: Bootstrap检验 - 转化率提升分布',
        xaxis_title='转化率提升 (%)',
        yaxis_title='频次',
        height=400
    )
    st.plotly_chart(fig_bootstrap, use_container_width=True)
    
    st.markdown("---")
    
    st.subheader("📋 增量性评估总表")
    
    inc_display = removal_effect[[
        'channel', 'attribution_weight', 'conversion_rate_with',
        'conversion_rate_without', 'conversion_lift_pct',
        'incremental_conversions', 'incremental_value',
        'incremental_roi', 'incremental_roas'
    ]].copy()
    inc_display.columns = [
        '渠道', '归因权重', '有渠道转化率%', '无渠道转化率%',
        '转化率提升%', '增量转化数', '增量价值', '增量ROI%', '增量ROAS'
    ]
    inc_display = inc_display.sort_values('增量转化数', ascending=False)
    inc_display = inc_display.round(2)
    inc_display = inc_display.reset_index(drop=True)
    inc_display.index = inc_display.index + 1
    
    st.dataframe(inc_display, use_container_width=True)

with tab6:
    st.header("🔍 SHAP数据驱动归因分析")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("SHAP归因权重")
        
        shap_plot_df = shap_attr.sort_values('shap_weight', ascending=True)
        
        fig_shap = px.bar(
            shap_plot_df,
            x='shap_weight',
            y='channel',
            orientation='h',
            title=f'基于SHAP的渠道贡献度 (正则化强度={shap_reg})',
            labels={'shap_weight': 'SHAP权重', 'channel': '渠道'},
            color='shap_avg_value',
            color_continuous_scale='RdYlGn',
            text=shap_plot_df['shap_weight'].apply(lambda x: f'{x*100:.1f}%')
        )
        fig_shap.update_traces(textposition='outside')
        st.plotly_chart(fig_shap, use_container_width=True)
    
    with col2:
        st.subheader("特征重要性")
        
        feature_importance = shap_model.get_feature_importance().head(15)
        
        fig_feature = px.bar(
            feature_importance.sort_values('shap_importance', ascending=True),
            x='shap_importance',
            y='feature',
            orientation='h',
            title='Top 15 特征重要性 (SHAP)',
            labels={'shap_importance': 'SHAP重要性', 'feature': '特征'},
            color='shap_importance',
            color_continuous_scale='Purples'
        )
        st.plotly_chart(fig_feature, use_container_width=True)
    
    st.markdown("---")
    
    st.subheader("SHAP Summary Plot")
    
    shap_data = shap_model.get_shap_summary_data()
    
    fig, ax = plt.subplots(figsize=(10, 8))
    shap.summary_plot(
        shap_data['shap_values'],
        shap_data['features'],
        feature_names=shap_data['feature_names'],
        max_display=15,
        plot_type='bar',
        show=False
    )
    plt.tight_layout()
    st.pyplot(fig)
    
    fig2, ax2 = plt.subplots(figsize=(12, 8))
    shap.summary_plot(
        shap_data['shap_values'],
        shap_data['features'],
        feature_names=shap_data['feature_names'],
        max_display=15,
        show=False
    )
    plt.tight_layout()
    st.pyplot(fig2)

with tab7:
    st.header("💰 预算优化")
    
    col1, col2, col3 = st.columns(3)
    
    current_total = budget_results['roi_metrics']['current_spend'].sum()
    projected_value = budget_results['recommendations']['projected_value'].sum()
    current_roi = (budget_results['roi_metrics']['attributed_value'].sum() - current_total) / current_total * 100
    
    with col1:
        st.metric("当前总预算", f"¥{current_total:,.0f}")
    with col2:
        st.metric("优化总预算", f"¥{total_budget:,.0f}")
    with col3:
        st.metric("预期ROI", f"{((projected_value - total_budget) / total_budget * 100):.1f}%", 
                  delta=f"{((projected_value - total_budget) / total_budget * 100 - current_roi):.1f}%")
    
    st.markdown("---")
    
    st.subheader("📈 边际收益曲线 (核心)")
    
    marginal_analysis = budget_results['marginal_analysis']
    
    selected_channels = st.multiselect(
        "选择展示的渠道",
        marginal_analysis['channel'].tolist(),
        default=marginal_analysis.nlargest(5, 'current_spend')['channel'].tolist(),
        key='marginal_channels'
    )
    
    if selected_channels:
        fig_marginal = go.Figure()
        
        colors = px.colors.qualitative.Set2[:len(selected_channels)]
        
        for idx, channel in enumerate(selected_channels):
            row = marginal_analysis[marginal_analysis['channel'] == channel].iloc[0]
            curve_data = row['curve_data']
            current_spend = row['current_spend']
            optimal_spend = row['optimal_spend']
            
            fig_marginal.add_trace(go.Scatter(
                x=curve_data['spend'],
                y=curve_data['marginal_return'],
                mode='lines',
                name=f'{channel}',
                line=dict(color=colors[idx % len(colors)], width=2)
            ))
            
            fig_marginal.add_trace(go.Scatter(
                x=[current_spend],
                y=[row['marginal_return_at_current']],
                mode='markers',
                name=f'{channel} (当前)',
                marker=dict(size=12, color=colors[idx % len(colors)], symbol='diamond'),
                showlegend=False
            ))
            
            fig_marginal.add_trace(go.Scatter(
                x=[optimal_spend],
                y=[row['marginal_return_at_optimal']],
                mode='markers',
                name=f'{channel} (最优)',
                marker=dict(size=12, color=colors[idx % len(colors)], symbol='star'),
                showlegend=False
            ))
        
        fig_marginal.add_hline(
            y=1.0, line_dash="dash", line_color="red",
            annotation_text="边际收益 = 边际成本 (最优预算点)"
        )
        
        fig_marginal.update_layout(
            title='边际收益曲线 — 找到边际收益=边际成本的最优预算点',
            xaxis_title='预算投入 (¥)',
            yaxis_title='边际收益 (每增加1元投入的回报)',
            height=500,
            hovermode='x unified'
        )
        st.plotly_chart(fig_marginal, use_container_width=True)
        
        st.markdown("""
        **解读**: 
        - 📉 曲线下降表示边际收益递减
        - ⭐ 星标 = 最优预算点 (边际收益=边际成本)
        - ◆ 菱形 = 当前预算位置
        - 当前预算在最优点左侧 → 应增加投入; 在右侧 → 应减少投入
        """)
    
    st.markdown("---")
    
    st.subheader("各渠道响应曲线")
    
    if selected_channels:
        fig_response = go.Figure()
        
        for idx, channel in enumerate(selected_channels):
            row = marginal_analysis[marginal_analysis['channel'] == channel].iloc[0]
            curve_data = row['curve_data']
            
            fig_response.add_trace(go.Scatter(
                x=curve_data['spend'],
                y=curve_data['value'],
                mode='lines',
                name=channel,
                line=dict(color=colors[idx % len(colors)], width=2)
            ))
        
        fig_response.update_layout(
            title='渠道响应曲线 (投入-产出关系)',
            xaxis_title='预算投入 (¥)',
            yaxis_title='预期转化价值 (¥)',
            height=400
        )
        st.plotly_chart(fig_response, use_container_width=True)
    
    st.markdown("---")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("预算分配对比")
        
        budget_compare = budget_results['recommendations'].copy()
        budget_compare['current_spend'] = budget_compare['current_spend'].round(0)
        budget_compare['recommended_spend'] = budget_compare['recommended_spend'].round(0)
        
        fig_budget = go.Figure()
        
        fig_budget.add_trace(go.Bar(
            y=budget_compare['channel'],
            x=budget_compare['current_spend'],
            name='当前预算',
            orientation='h',
            marker_color='lightgray'
        ))
        
        fig_budget.add_trace(go.Bar(
            y=budget_compare['channel'],
            x=budget_compare['recommended_spend'],
            name='推荐预算',
            orientation='h',
            marker_color='rgb(55, 83, 109)'
        ))
        
        fig_budget.update_layout(
            title='当前预算 vs 推荐预算',
            barmode='group',
            xaxis_title='预算金额 (¥)',
            yaxis_title='渠道',
            height=500
        )
        st.plotly_chart(fig_budget, use_container_width=True)
    
    with col2:
        st.subheader("预算变化详情")
        
        budget_detail = budget_results['recommendations'].copy()
        budget_detail['change_dir'] = budget_detail['change_amount'].apply(
            lambda x: '增加' if x > 0 else '减少'
        )
        
        fig_change = px.bar(
            budget_detail,
            x='change_amount',
            y='channel',
            orientation='h',
            title='预算变化金额',
            color='change_dir',
            color_discrete_map={'增加': 'green', '减少': 'red'},
            labels={'change_amount': '变化金额 (¥)', 'channel': '渠道'}
        )
        st.plotly_chart(fig_change, use_container_width=True)
    
    st.markdown("---")
    
    st.subheader("💡 智能洞察与建议")
    
    for insight in budget_results['insights']:
        emoji = "✅" if insight['type'] == 'opportunity' else ("⚠️" if insight['type'] == 'warning' else "📋")
        with st.expander(f"{emoji} {insight['title']}", expanded=True):
            st.write(insight['content'])
    
    st.markdown("---")
    
    st.subheader("边际收益与最优预算详情")
    
    marginal_display = marginal_analysis[[
        'channel', 'current_spend', 'optimal_spend',
        'marginal_return_at_current', 'marginal_return_at_optimal',
        'optimal_projected_value', 'spend_efficiency'
    ]].copy()
    marginal_display.columns = [
        '渠道', '当前预算', '最优预算', 
        '当前边际收益', '最优点边际收益',
        '最优点预期价值', '预算效率比'
    ]
    marginal_display = marginal_display.sort_values('当前边际收益', ascending=False)
    marginal_display = marginal_display.round(2)
    marginal_display = marginal_display.reset_index(drop=True)
    marginal_display.index = marginal_display.index + 1
    
    st.dataframe(marginal_display, use_container_width=True)

with tab8:
    st.header("📉 深度分析")
    
    st.subheader("渠道转化漏斗")
    
    funnel_data = pd.DataFrame({
        '阶段': ['总触达用户', '首次互动', '多次互动', '转化用户'],
        '用户数': [
            len(users_df),
            filtered_tp[filtered_tp['touchpoint_position'] == 1]['user_id'].nunique(),
            filtered_tp[filtered_tp['total_touchpoints'] > 1]['user_id'].nunique(),
            users_df['converted'].sum()
        ]
    })
    
    fig_funnel = px.funnel(
        funnel_data,
        x='用户数',
        y='阶段',
        title='用户转化漏斗',
        color='阶段'
    )
    st.plotly_chart(fig_funnel, use_container_width=True)
    
    st.markdown("---")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("首次 vs 末次接触渠道对比")
        
        first_vs_last = pd.DataFrame({
            '渠道': combined['channel'],
            '首次接触权重': combined['first_touch_weight'],
            '末次接触权重': combined['last_touch_weight']
        })
        first_vs_last['差异'] = first_vs_last['末次接触权重'] - first_vs_last['首次接触权重']
        
        fig_first_last = px.scatter(
            first_vs_last,
            x='首次接触权重',
            y='末次接触权重',
            size=first_vs_last[['首次接触权重', '末次接触权重']].max(axis=1) * 100,
            color='差异',
            hover_name='渠道',
            title='首次接触 vs 末次接触 渠道贡献',
            color_continuous_scale='RdBu',
            size_max=30
        )
        
        max_val = max(first_vs_last['首次接触权重'].max(), first_vs_last['末次接触权重'].max())
        fig_first_last.add_trace(
            go.Scatter(
                x=[0, max_val],
                y=[0, max_val],
                mode='lines',
                line=dict(dash='dash', color='gray'),
                name='平衡线'
            )
        )
        st.plotly_chart(fig_first_last, use_container_width=True)
    
    with col2:
        st.subheader("归因一致性分析")
        
        weight_cols = ['last_touch_weight', 'first_touch_weight', 'linear_weight', 
                       'time_decay_weight', 'position_weight', 'markov_weight', 'shap_weight']
        corr_matrix = combined[weight_cols].corr()
        
        fig_corr = px.imshow(
            corr_matrix,
            labels=dict(color="相关系数"),
            x=['末次', '首次', '线性', '时间衰减', '位置', 'Markov', 'SHAP'],
            y=['末次', '首次', '线性', '时间衰减', '位置', 'Markov', 'SHAP'],
            color_continuous_scale='RdBu_r',
            aspect='auto',
            text_auto='.2f',
            title='各归因模型相关性'
        )
        st.plotly_chart(fig_corr, use_container_width=True)
    
    st.markdown("---")
    
    st.subheader("热门转化路径")
    
    top_journeys = journeys_df[journeys_df['converted'] == 1]['journey'].value_counts().head(10)
    
    fig_journeys = px.bar(
        x=top_journeys.values,
        y=top_journeys.index,
        orientation='h',
        title='Top 10 转化用户旅程',
        labels={'x': '转化数', 'y': '用户旅程'},
        color=top_journeys.values,
        color_continuous_scale='Blues'
    )
    st.plotly_chart(fig_journeys, use_container_width=True)

st.markdown("---")
st.markdown("### 📝 使用说明")
st.markdown("""
1. **数据概览**: 查看转化周期统计与归因窗口期设定
2. **归因分析**: 对比不同归因模型的渠道贡献度，含正则化平滑效果
3. **跨设备归因**: 登录用户多设备行为关联与交叉归因
4. **营销组合建模**: 分析渠道间协同效应与相互替代关系
5. **增量性评估**: 通过移除效应和显著性检验评估渠道真实增量
6. **SHAP解释**: 查看基于正则化模型的数据驱动归因分析
7. **预算优化**: 通过边际收益曲线找到各渠道最优预算点
8. **深度分析**: 探索转化漏斗和用户旅程模式
""")
