import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import matplotlib.pyplot as plt
from lifelines import KaplanMeierFitter
import warnings
warnings.filterwarnings('ignore')

st.set_page_config(
    page_title="品牌忠诚度分析平台",
    page_icon="🏷️",
    layout="wide",
    initial_sidebar_state="expanded"
)

from loyalty_analyzer import BrandLoyaltyAnalyzer

@st.cache_resource(show_spinner=False)
def load_analyzer(n_customers=1000, use_cached=True):
    analyzer = BrandLoyaltyAnalyzer(n_customers=n_customers, use_cached_data=use_cached)
    return analyzer

@st.cache_data(show_spinner="正在分析数据...")
def run_analysis(_analyzer):
    return _analyzer.run_full_analysis()

def color_metric(value, reverse=False):
    if reverse:
        if value > 70:
            return "🔴"
        elif value > 40:
            return "🟡"
        else:
            return "🟢"
    else:
        if value > 70:
            return "🟢"
        elif value > 40:
            return "🟡"
        else:
            return "🔴"

def main():
    st.title("🏷️ 品牌忠诚度分析平台")
    st.markdown("---")
    
    with st.sidebar:
        st.header("⚙️ 分析设置")
        
        n_customers = st.slider("模拟用户数量", min_value=500, max_value=2000, value=1000, step=100)
        
        use_cached = st.checkbox("使用缓存数据", value=True)
        
        analyze_button = st.button("🚀 开始分析", type="primary", use_container_width=True)
        
        st.markdown("---")
        st.header("📊 分析模块")
        page = st.radio(
            "选择分析页面",
            ["📈 总览仪表盘", "🔄 复购率分析", "👍 NPS分析", 
             "⚠️ 投诉率分析", "🧮 忠诚度指数", "👥 用户分层", 
             "📉 生存分析", "🔍 影响因素归因", "💡 提升策略",
             "🏢 竞争对手流转", "🔮 忠诚度预测", "📣 口碑传播分析"],
            label_visibility="collapsed"
        )
        
        st.markdown("---")
        st.info("💡 本平台使用生存分析、聚类、归因模型等技术，全面分析品牌忠诚度")
    
    if analyze_button:
        st.cache_data.clear()
        st.cache_resource.clear()
    
    with st.spinner("正在初始化分析引擎..."):
        analyzer = load_analyzer(n_customers=n_customers, use_cached=use_cached)
        
        with st.spinner("正在进行全面分析..."):
            summary = run_analysis(analyzer)
    
    if page == "📈 总览仪表盘":
        show_dashboard(analyzer, summary)
    elif page == "🔄 复购率分析":
        show_repurchase_analysis(analyzer)
    elif page == "👍 NPS分析":
        show_nps_analysis(analyzer)
    elif page == "⚠️ 投诉率分析":
        show_complaint_analysis(analyzer)
    elif page == "🧮 忠诚度指数":
        show_loyalty_index(analyzer)
    elif page == "👥 用户分层":
        show_clustering(analyzer)
    elif page == "📉 生存分析":
        show_survival_analysis(analyzer)
    elif page == "🔍 影响因素归因":
        show_attribution(analyzer)
    elif page == "💡 提升策略":
        show_strategies(analyzer)
    elif page == "🏢 竞争对手流转":
        show_competitor_analysis(analyzer)
    elif page == "🔮 忠诚度预测":
        show_loyalty_prediction(analyzer)
    elif page == "📣 口碑传播分析":
        show_referral_analysis(analyzer)

def show_dashboard(analyzer, summary):
    st.header("📈 总览仪表盘")
    
    nps_metrics = analyzer.get_nps_metrics()
    complaint_metrics = analyzer.get_complaint_metrics()
    repurchase_metrics = analyzer.get_repurchase_metrics()
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        loyalty_avg = summary.get('loyalty_index', {}).get('overall_avg', 0)
        st.metric(
            "🏆 品牌忠诚度指数",
            f"{loyalty_avg:.1f}",
            delta=None,
            help="综合评分 (0-100)"
        )
    
    with col2:
        nps_val = nps_metrics['nps_score']
        st.metric(
            "👍 NPS 净推荐值",
            f"{nps_val:.1f}",
            delta=f"{nps_metrics['promoter_pct']:.1f}% 推荐者",
            help="净推荐值 = 推荐者% - 贬损者%"
        )
    
    with col3:
        repurchase_val = repurchase_metrics['repurchase_rate']
        st.metric(
            "🔄 用户复购率",
            f"{repurchase_val:.1f}%",
            delta=f"人均 {repurchase_metrics['avg_purchases_per_customer']:.1f} 次",
            help="购买两次及以上的用户占比"
        )
    
    with col4:
        complaint_val = complaint_metrics['complaint_rate']
        st.metric(
            "⚠️ 用户投诉率",
            f"{complaint_val:.1f}%",
            delta=f"{complaint_metrics['resolution_rate']:.1f}% 解决率",
            help="有投诉记录的用户占比",
            delta_color="off"
        )
    
    st.markdown("---")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader("🏷️ 忠诚度层级分布")
        
        cluster_dist = summary.get('clustering', {}).get('cluster_distribution', [])
        if cluster_dist:
            dist_df = pd.DataFrame(cluster_dist)
            dist_df['用户占比'] = dist_df['用户占比'] * 100
            
            fig = px.pie(
                dist_df,
                values='用户占比',
                names='忠诚度层级',
                color='忠诚度层级',
                color_discrete_map={'高': '#22c55e', '中': '#eab308', '低': '#ef4444'},
                hole=0.5,
                title='用户忠诚度分层占比'
            )
            fig.update_traces(textposition='inside', textinfo='percent+label')
            st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        st.subheader("📊 核心指标雷达图")
        
        radar_data = pd.DataFrame({
            '维度': ['复购能力', '推荐意愿', '投诉处理', '互动参与', '价值贡献'],
            '得分': [
                summary.get('loyalty_index', {}).get('high_tier_avg', 0) / 100 * 100 if summary.get('loyalty_index', {}).get('high_tier_avg', 0) else 65,
                nps_metrics['promoter_pct'],
                complaint_metrics['resolution_rate'],
                60,
                summary.get('loyalty_index', {}).get('high_tier_avg', 0) / 100 * 100 if summary.get('loyalty_index', {}).get('high_tier_avg', 0) else 70
            ]
        })
        
        fig = px.line_polar(
            radar_data, r='得分', theta='维度', line_close=True,
            range_r=[0, 100]
        )
        fig.update_traces(fill='toself', fillcolor='rgba(59, 130, 246, 0.3)')
        st.plotly_chart(fig, use_container_width=True)
    
    st.markdown("---")
    
    st.subheader("📋 各层级用户特征对比")
    
    if 'loyalty_index' in summary and 'tier_summary' in summary['loyalty_index']:
        tier_df = pd.DataFrame(summary['loyalty_index']['tier_summary'])
        
        display_cols = ['忠诚度层级', '平均指数', '复购评分', 'NPS评分', '投诉评分', '互动评分', '价值评分', '用户数量']
        if all(col in tier_df.columns for col in display_cols):
            tier_display = tier_df[display_cols].copy()
            
            numeric_cols = ['平均指数', '复购评分', 'NPS评分', '投诉评分', '互动评分', '价值评分']
            for col in numeric_cols:
                tier_display[col] = tier_display[col].round(2)
            
            def highlight_rows(row):
                if row['忠诚度层级'] == '高忠诚度':
                    return ['background-color: rgba(34, 197, 94, 0.1)'] * len(row)
                elif row['忠诚度层级'] == '中忠诚度':
                    return ['background-color: rgba(234, 179, 8, 0.1)'] * len(row)
                else:
                    return ['background-color: rgba(239, 68, 68, 0.1)'] * len(row)
            
            st.dataframe(
                tier_display.style.apply(highlight_rows, axis=1),
                use_container_width=True,
                hide_index=True
            )
    
    st.markdown("---")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📈 各细分群体忠诚度指数")
        if analyzer.loyalty_results:
            segment_indices = analyzer.loyalty_results.get('segment_indices')
            if segment_indices is not None:
                fig = px.bar(
                    segment_indices,
                    x='细分群体',
                    y='平均忠诚度指数',
                    color='平均忠诚度指数',
                    color_continuous_scale='RdYlGn',
                    text='平均忠诚度指数',
                    title='各用户细分群体忠诚度指数对比'
                )
                fig.update_traces(texttemplate='%{text:.1f}', textposition='outside')
                st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        st.subheader("📊 各渠道忠诚度指数")
        if analyzer.loyalty_results:
            channel_indices = analyzer.loyalty_results.get('channel_indices')
            if channel_indices is not None:
                fig = px.bar(
                    channel_indices,
                    x='渠道',
                    y='平均忠诚度指数',
                    color='平均忠诚度指数',
                    color_continuous_scale='Blues',
                    text='平均忠诚度指数',
                    title='各渠道用户忠诚度指数对比',
                    orientation='h'
                )
                fig.update_traces(texttemplate='%{text:.1f}', textposition='outside')
                st.plotly_chart(fig, use_container_width=True)

def show_repurchase_analysis(analyzer):
    st.header("🔄 用户复购率分析")
    
    repurchase_metrics = analyzer.get_repurchase_metrics()
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("复购率", f"{repurchase_metrics['repurchase_rate']:.1f}%")
    with col2:
        st.metric("复购用户数", f"{repurchase_metrics['repeat_customers']:,}")
    with col3:
        st.metric("人均购买次数", f"{repurchase_metrics['avg_purchases_per_customer']:.2f}")
    with col4:
        st.metric("平均购买间隔", f"{repurchase_metrics['avg_days_between_purchases']:.0f} 天")
    
    st.markdown("---")
    
    purchases = analyzer.data['purchases'].copy()
    purchases['purchase_date'] = pd.to_datetime(purchases['purchase_date'])
    
    purchases['month'] = purchases['purchase_date'].dt.to_period('M').astype(str)
    monthly_purchases = purchases.groupby('month').agg(
        orders=('purchase_date', 'count'),
        unique_customers=('customer_id', 'nunique'),
        total_amount=('purchase_amount', 'sum')
    ).reset_index()
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📈 月度购买趋势")
        fig = px.line(
            monthly_purchases,
            x='month',
            y=['orders', 'unique_customers'],
            title='月度订单数与用户数趋势'
        )
        fig.update_layout(legend_title_text='指标')
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        st.subheader("💰 月度消费金额")
        fig = px.area(
            monthly_purchases,
            x='month',
            y='total_amount',
            title='月度总消费金额趋势',
            color_discrete_sequence=['#10b981']
        )
        st.plotly_chart(fig, use_container_width=True)
    
    st.markdown("---")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📊 购买频次分布")
        customer_freq = purchases.groupby('customer_id').size().reset_index(name='purchase_count')
        
        fig = px.histogram(
            customer_freq,
            x='purchase_count',
            nbins=20,
            title='用户购买频次分布',
            color_discrete_sequence=['#6366f1']
        )
        fig.update_layout(xaxis_title='购买次数', yaxis_title='用户数量')
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        st.subheader("🏷️ 消费金额分布")
        fig = px.box(
            purchases,
            x='product_category',
            y='purchase_amount',
            title='各品类消费金额分布',
            color='product_category'
        )
        st.plotly_chart(fig, use_container_width=True)
    
    st.markdown("---")
    
    if analyzer.survival_results:
        surv_data = analyzer.survival_results['survival_data']
        
        st.subheader("🔮 复购概率预测")
        
        fig = px.histogram(
            surv_data,
            x='repurchase_probability',
            nbins=20,
            title='用户未来复购概率分布',
            color_discrete_sequence=['#f59e0b']
        )
        fig.update_layout(xaxis_title='复购概率', yaxis_title='用户数量')
        st.plotly_chart(fig, use_container_width=True)
        
        high_prob = (surv_data['repurchase_probability'] > 0.7).sum()
        medium_prob = ((surv_data['repurchase_probability'] >= 0.3) & (surv_data['repurchase_probability'] <= 0.7)).sum()
        low_prob = (surv_data['repurchase_probability'] < 0.3).sum()
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.info(f"🔵 高复购概率 (>70%): {high_prob} 人 ({high_prob/len(surv_data)*100:.1f}%)")
        with col2:
            st.info(f"🟡 中复购概率 (30-70%): {medium_prob} 人 ({medium_prob/len(surv_data)*100:.1f}%)")
        with col3:
            st.info(f"🔴 低复购概率 (<30%): {low_prob} 人 ({low_prob/len(surv_data)*100:.1f}%)")

def show_nps_analysis(analyzer):
    st.header("👍 NPS 净推荐值分析")
    
    nps_metrics = analyzer.get_nps_metrics()
    nps_df = analyzer.data['nps'].copy()
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        nps_score = nps_metrics['nps_score']
        color = "🟢" if nps_score > 0 else "🔴"
        st.metric(f"{color} NPS 得分", f"{nps_score:.1f}")
    with col2:
        st.metric("🏆 推荐者占比", f"{nps_metrics['promoter_pct']:.1f}%")
    with col3:
        st.metric("😐 被动者占比", f"{nps_metrics['passive_pct']:.1f}%")
    with col4:
        st.metric("😠 贬损者占比", f"{nps_metrics['detractor_pct']:.1f}%")
    
    st.markdown("---")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📊 NPS 分布")
        
        def classify_nps(score):
            if score >= 9:
                return '推荐者 (9-10)'
            elif score >= 7:
                return '被动者 (7-8)'
            else:
                return '贬损者 (0-6)'
        
        nps_df['category'] = nps_df['nps_score'].apply(classify_nps)
        
        category_counts = nps_df['category'].value_counts().reset_index()
        category_counts.columns = ['category', 'count']
        category_counts['percentage'] = category_counts['count'] / len(nps_df) * 100
        
        fig = px.bar(
            category_counts,
            x='category',
            y='percentage',
            color='category',
            color_discrete_map={
                '推荐者 (9-10)': '#22c55e',
                '被动者 (7-8)': '#eab308',
                '贬损者 (0-6)': '#ef4444'
            },
            text='percentage',
            title='NPS 各类别占比'
        )
        fig.update_traces(texttemplate='%{text:.1f}%', textposition='outside')
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        st.subheader("📈 NPS 评分分布")
        fig = px.histogram(
            nps_df,
            x='nps_score',
            nbins=11,
            title='NPS 评分分布',
            color_discrete_sequence=['#3b82f6']
        )
        fig.update_layout(xaxis_title='NPS 评分 (0-10)', yaxis_title='数量')
        st.plotly_chart(fig, use_container_width=True)
    
    st.markdown("---")
    
    st.subheader("📋 子维度评分对比")
    
    subdimensions = pd.DataFrame({
        '维度': ['易用性', '产品质量', '客户服务'],
        '平均评分': [
            nps_df['ease_of_use'].mean(),
            nps_df['product_quality'].mean(),
            nps_df['customer_service'].mean()
        ]
    })
    
    fig = px.bar(
        subdimensions,
        x='维度',
        y='平均评分',
        color='平均评分',
        color_continuous_scale='RdYlGn',
        range_color=[0, 5],
        text='平均评分',
        title='NPS 子维度平均评分 (1-5分)'
    )
    fig.update_traces(texttemplate='%{text:.2f}', textposition='outside')
    st.plotly_chart(fig, use_container_width=True)
    
    st.markdown("---")
    
    if analyzer.clustering_results:
        features = analyzer.clustering_results['features_with_clusters']
        
        st.subheader("🏷️ 各忠诚度层级 NPS 对比")
        
        tier_nps = features.groupby('loyalty_level').agg(
            avg_nps=('avg_nps', 'mean'),
            avg_ease=('avg_ease_of_use', 'mean'),
            avg_quality=('avg_product_quality', 'mean'),
            avg_service=('avg_customer_service', 'mean'),
            count=('customer_id', 'count')
        ).reset_index()
        
        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=tier_nps['loyalty_level'],
            y=tier_nps['avg_nps'],
            name='平均NPS',
            marker_color='#3b82f6'
        ))
        fig.update_layout(
            title='各忠诚度层级平均 NPS 对比',
            xaxis_title='忠诚度层级',
            yaxis_title='平均 NPS 评分'
        )
        st.plotly_chart(fig, use_container_width=True)

def show_complaint_analysis(analyzer):
    st.header("⚠️ 投诉率分析")
    
    complaint_metrics = analyzer.get_complaint_metrics()
    complaints = analyzer.data['complaints'].copy()
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("用户投诉率", f"{complaint_metrics['complaint_rate']:.1f}%")
    with col2:
        st.metric("总投诉数", f"{complaint_metrics['total_complaints']:,}")
    with col3:
        st.metric("投诉解决率", f"{complaint_metrics['resolution_rate']:.1f}%")
    with col4:
        st.metric("平均解决时间", f"{complaint_metrics['avg_resolution_time_days']:.1f} 天")
    
    st.markdown("---")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📊 投诉类型分布")
        type_dist = complaints['complaint_type'].value_counts().reset_index()
        type_dist.columns = ['type', 'count']
        type_dist['percentage'] = type_dist['count'] / len(complaints) * 100
        
        fig = px.pie(
            type_dist,
            values='count',
            names='type',
            title='投诉类型分布',
            color_discrete_sequence=px.colors.qualitative.Set3
        )
        fig.update_traces(textposition='inside', textinfo='percent+label')
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        st.subheader("⚖️ 投诉严重程度分布")
        severity_dist = complaints['severity'].value_counts().reset_index()
        severity_dist.columns = ['severity', 'count']
        
        fig = px.bar(
            severity_dist,
            x='severity',
            y='count',
            color='severity',
            color_discrete_map={'Low': '#22c55e', 'Medium': '#eab308', 'High': '#ef4444'},
            title='投诉严重程度分布',
            text='count'
        )
        fig.update_traces(textposition='outside')
        st.plotly_chart(fig, use_container_width=True)
    
    st.markdown("---")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("⏱️ 投诉解决时间分布")
        resolved = complaints[complaints['is_resolved']].copy()
        
        fig = px.histogram(
            resolved,
            x='resolution_time_days',
            nbins=15,
            title='投诉解决时间分布',
            color_discrete_sequence=['#8b5cf6']
        )
        fig.update_layout(xaxis_title='解决天数', yaxis_title='投诉数量')
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        st.subheader("✅ 投诉解决状态")
        
        resolution_status = complaints['is_resolved'].value_counts().reset_index()
        resolution_status.columns = ['is_resolved', 'count']
        resolution_status['status'] = resolution_status['is_resolved'].map({True: '已解决', False: '未解决'})
        resolution_status['percentage'] = resolution_status['count'] / len(complaints) * 100
        
        fig = px.bar(
            resolution_status,
            x='status',
            y='percentage',
            color='status',
            color_discrete_map={'已解决': '#22c55e', '未解决': '#ef4444'},
            title='投诉解决状态占比',
            text='percentage'
        )
        fig.update_traces(texttemplate='%{text:.1f}%', textposition='outside')
        st.plotly_chart(fig, use_container_width=True)
    
    st.markdown("---")
    
    if analyzer.clustering_results:
        st.subheader("🏷️ 各忠诚度层级投诉对比")
        
        features = analyzer.clustering_results['features_with_clusters']
        
        tier_complaints = features.groupby('loyalty_level').agg(
            avg_complaints=('complaint_count', 'mean'),
            avg_unresolved=('unresolved_complaints', 'mean'),
            count=('customer_id', 'count')
        ).reset_index()
        
        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=tier_complaints['loyalty_level'],
            y=tier_complaints['avg_complaints'],
            name='平均投诉次数',
            marker_color='#ef4444'
        ))
        fig.update_layout(
            title='各忠诚度层级平均投诉次数',
            xaxis_title='忠诚度层级',
            yaxis_title='平均投诉次数'
        )
        st.plotly_chart(fig, use_container_width=True)

def show_loyalty_index(analyzer):
    st.header("🧮 品牌忠诚度指数")
    
    if not analyzer.loyalty_results:
        st.warning("请先运行分析...")
        return
    
    metrics = analyzer.loyalty_results['metrics_with_index']
    index_summary = analyzer.loyalty_results['index_summary']
    
    overall = index_summary['overall']
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("📊 平均忠诚度指数", f"{overall['avg_loyalty_index']:.1f}")
    with col2:
        st.metric("📐 中位数指数", f"{overall['median_loyalty_index']:.1f}")
    with col3:
        st.metric("📉 标准差", f"{overall['std_loyalty_index']:.1f}")
    with col4:
        st.metric("↔️ 指数范围", f"{overall['min_loyalty_index']:.1f} - {overall['max_loyalty_index']:.1f}")
    
    st.markdown("---")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📈 忠诚度指数分布")
        
        fig = px.histogram(
            metrics,
            x='loyalty_index',
            nbins=20,
            title='用户忠诚度指数分布',
            color='loyalty_tier',
            color_discrete_map={'高忠诚度': '#22c55e', '中忠诚度': '#eab308', '低忠诚度': '#ef4444'}
        )
        fig.update_layout(xaxis_title='忠诚度指数 (0-100)', yaxis_title='用户数量')
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        st.subheader("🧭 五大维度得分")
        
        dimension_scores = pd.DataFrame({
            '维度': ['复购能力', '推荐意愿', '投诉处理', '互动参与', '价值贡献'],
            '平均得分': [
                metrics['repurchase_score'].mean() * 100,
                metrics['nps_score'].mean() * 100,
                metrics['complaint_score'].mean() * 100,
                metrics['engagement_score'].mean() * 100,
                metrics['value_score'].mean() * 100
            ],
            '权重': [30, 25, 15, 15, 15]
        })
        
        fig = px.bar(
            dimension_scores,
            x='维度',
            y='平均得分',
            color='平均得分',
            color_continuous_scale='Blues',
            text='平均得分',
            title='忠诚度指数各维度平均得分'
        )
        fig.update_traces(texttemplate='%{text:.1f}', textposition='outside')
        fig.add_annotation(
            x=0, y=1.1,
            text='权重: 复购30% | NPS25% | 投诉15% | 互动15% | 价值15%',
            showarrow=False,
            xref='paper', yref='paper',
            font=dict(size=12)
        )
        st.plotly_chart(fig, use_container_width=True)
    
    st.markdown("---")
    
    st.subheader("📊 各维度得分对比")
    
    tier_summary = index_summary['tier_summary']
    
    display_cols = ['忠诚度层级', '平均指数', '复购评分', 'NPS评分', '投诉评分', '互动评分', '价值评分', '用户数量', '用户占比']
    if all(col in tier_summary.columns for col in display_cols):
        tier_display = tier_summary[display_cols].copy()
        tier_display['用户占比'] = tier_display['用户占比'] * 100
        
        numeric_cols = ['平均指数', '复购评分', 'NPS评分', '投诉评分', '互动评分', '价值评分', '用户占比']
        for col in numeric_cols:
            tier_display[col] = tier_display[col].round(2)
        
        st.dataframe(
            tier_display,
            use_container_width=True,
            hide_index=True,
            column_config={
                '用户占比': st.column_config.NumberColumn('用户占比 (%)', format='%.1f %%')
            }
        )
    
    st.markdown("---")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("🏆 忠诚度最高的用户")
        
        leaders = analyzer.loyalty_results['loyalty_leaders'].head(10)
        if len(leaders) > 0:
            leaders_display = leaders[['customer_id', 'loyalty_index', 'loyalty_tier', 'total_spend', 'frequency']].copy()
            leaders_display['loyalty_index'] = leaders_display['loyalty_index'].round(1)
            leaders_display.columns = ['用户ID', '忠诚度指数', '忠诚度层级', '总消费', '购买频次']
            
            st.dataframe(leaders_display, use_container_width=True, hide_index=True)
    
    with col2:
        st.subheader("⚠️ 需要关注的用户")
        
        at_risk = analyzer.loyalty_results['at_risk_customers'].head(10)
        if len(at_risk) > 0:
            at_risk_display = at_risk[['customer_id', 'loyalty_index', 'loyalty_tier', 'total_spend', 'frequency']].copy()
            at_risk_display['loyalty_index'] = at_risk_display['loyalty_index'].round(1)
            at_risk_display.columns = ['用户ID', '忠诚度指数', '忠诚度层级', '总消费', '购买频次']
            
            st.dataframe(at_risk_display, use_container_width=True, hide_index=True)

def show_clustering(analyzer):
    st.header("👥 用户忠诚度分层")
    
    if not analyzer.clustering_results:
        st.warning("请先运行分析...")
        return
    
    results = analyzer.clustering_results
    features = results['features_with_clusters']
    profiles = results['cluster_profiles']
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📊 用户分层分布")
        
        fig = px.pie(
            profiles,
            values='用户数量',
            names='忠诚度层级',
            color='忠诚度层级',
            color_discrete_map={'高': '#22c55e', '中': '#eab308', '低': '#ef4444'},
            hole=0.5,
            title='忠诚度分层用户分布'
        )
        fig.update_traces(textposition='inside', textinfo='percent+label')
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        st.subheader("🌐 PCA 聚类可视化")
        
        pca_df = pd.DataFrame({
            'PCA1': features['pca_x'],
            'PCA2': features['pca_y'],
            '忠诚度层级': features['loyalty_level']
        })
        
        fig = px.scatter(
            pca_df,
            x='PCA1',
            y='PCA2',
            color='忠诚度层级',
            color_discrete_map={'高': '#22c55e', '中': '#eab308', '低': '#ef4444'},
            title='用户忠诚度分层聚类结果',
            opacity=0.7
        )
        st.plotly_chart(fig, use_container_width=True)
    
    st.markdown("---")
    
    st.subheader("📋 各层级用户特征详情")
    
    display_cols = ['忠诚度层级', '用户数量', '用户占比', '平均购买频次', '平均总消费', '平均客单价', '平均NPS', '复购率']
    if all(col in profiles.columns for col in display_cols):
        prof_display = profiles[display_cols].copy()
        prof_display['用户占比'] = prof_display['用户占比'] * 100
        
        numeric_cols = ['平均购买频次', '平均总消费', '平均客单价', '平均NPS', '复购率', '用户占比']
        for col in numeric_cols:
            prof_display[col] = prof_display[col].round(2)
        
        def highlight_rows(row):
            if row['忠诚度层级'] == '高':
                return ['background-color: rgba(34, 197, 94, 0.1)'] * len(row)
            elif row['忠诚度层级'] == '中':
                return ['background-color: rgba(234, 179, 8, 0.1)'] * len(row)
            else:
                return ['background-color: rgba(239, 68, 68, 0.1)'] * len(row)
        
        st.dataframe(
            prof_display.style.apply(highlight_rows, axis=1),
            use_container_width=True,
            hide_index=True,
            column_config={
                '用户占比': st.column_config.NumberColumn('用户占比 (%)', format='%.1f %%'),
                '复购率': st.column_config.NumberColumn('复购率 (%)', format='%.1f %%')
            }
        )
    
    st.markdown("---")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📈 各层级关键指标对比")
        
        comparison_df = profiles.melt(
            id_vars=['忠诚度层级'],
            value_vars=['平均购买频次', '平均总消费', '平均NPS', '复购率'],
            var_name='指标',
            value_name='数值'
        )
        
        fig = px.bar(
            comparison_df,
            x='指标',
            y='数值',
            color='忠诚度层级',
            barmode='group',
            color_discrete_map={'高': '#22c55e', '中': '#eab308', '低': '#ef4444'},
            title='各层级关键指标对比'
        )
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        st.subheader("👥 各层级用户细分分布")
        
        features['segment'] = features['segment'].astype(str)
        segment_dist = features.groupby(['loyalty_level', 'segment']).size().reset_index(name='count')
        
        fig = px.bar(
            segment_dist,
            x='loyalty_level',
            y='count',
            color='segment',
            title='各层级用户细分群体分布',
            barmode='stack'
        )
        fig.update_layout(xaxis_title='忠诚度层级', yaxis_title='用户数量', legend_title='用户细分')
        st.plotly_chart(fig, use_container_width=True)
    
    if results.get('optimal_k_results'):
        st.markdown("---")
        st.subheader("🔢 最优聚类数评估")
        
        optimal = results['optimal_k_results']
        optimal_df = pd.DataFrame(optimal)
        
        fig = make_subplots(rows=2, cols=2, subplot_titles=('肘部法则 (Inertia)', '轮廓系数', 'CH 指数', 'DB 指数'))
        
        fig.add_trace(go.Scatter(x=optimal_df['k'], y=optimal_df['inertia'], mode='lines+markers'), row=1, col=1)
        fig.add_trace(go.Scatter(x=optimal_df['k'], y=optimal_df['silhouette_score'], mode='lines+markers'), row=1, col=2)
        fig.add_trace(go.Scatter(x=optimal_df['k'], y=optimal_df['calinski_harabasz_score'], mode='lines+markers'), row=2, col=1)
        fig.add_trace(go.Scatter(x=optimal_df['k'], y=optimal_df['davies_bouldin_score'], mode='lines+markers'), row=2, col=2)
        
        fig.update_layout(height=600, showlegend=False)
        st.plotly_chart(fig, use_container_width=True)

def show_survival_analysis(analyzer):
    st.header("📉 用户生存分析")
    
    if not analyzer.survival_results:
        st.warning("请先运行分析...")
        return
    
    results = analyzer.survival_results
    surv_data = results['survival_data']
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        churn_rate = surv_data['churned'].mean() * 100
        st.metric("📉 用户流失率", f"{churn_rate:.1f}%")
    with col2:
        median_survival = results['km_overall']['overall']['median_survival_time']
        st.metric("⏱️ 中位生存期", f"{median_survival:.0f} 天")
    with col3:
        avg_tenure = surv_data['tenure_days'].mean()
        st.metric("📅 平均留存天数", f"{avg_tenure:.0f} 天")
    with col4:
        avg_threshold = surv_data['dynamic_churn_threshold'].mean() if 'dynamic_churn_threshold' in surv_data.columns else 90
        st.metric("🎯 平均流失阈值", f"{avg_threshold:.0f} 天")
    
    st.markdown("---")
    
    if 'category_churn_thresholds' in results or 'category_stats' in results:
        st.subheader("📊 各品类差异化流失窗口设置")
        
        if 'category_stats' in results:
            cat_stats = results['category_stats']
            thresholds = results.get('category_churn_thresholds', {})
            medians = results.get('category_inter_purchase_medians', {})
            
            cat_display = cat_stats.copy()
            cat_display['流失阈值(天)'] = cat_display['product_category'].map(thresholds)
            cat_display['购买周期中位数(天)'] = cat_display['product_category'].map(medians)
            
            display_cols = ['product_category', 'median_inter_purchase', 'mean_inter_purchase', 
                           'std_inter_purchase', 'purchase_count', '购买周期中位数(天)', '流失阈值(天)']
            display_cols = [c for c in display_cols if c in cat_display.columns]
            
            cat_display = cat_display[display_cols]
            cat_display.columns = ['产品品类', '间隔中位数', '间隔均值', '间隔标准差', 
                                  '购买次数', '购买周期中位数(天)', '流失判定阈值(天)']
            
            col1, col2 = st.columns([1.5, 1])
            
            with col1:
                st.dataframe(
                    cat_display, 
                    use_container_width=True,
                    hide_index=True
                )
            
            with col2:
                threshold_df = pd.DataFrame({
                    '品类': list(thresholds.keys()),
                    '流失阈值(天)': list(thresholds.values()),
                    '购买周期中位数(天)': [medians.get(k, 0) for k in thresholds.keys()]
                }).melt(id_vars='品类', var_name='指标', value_name='天数')
                
                fig = px.bar(
                    threshold_df,
                    x='品类',
                    y='天数',
                    color='指标',
                    barmode='group',
                    title='各品类购买周期与流失阈值对比',
                    color_discrete_map={'流失阈值(天)': '#ef4444', '购买周期中位数(天)': '#3b82f6'}
                )
                st.plotly_chart(fig, use_container_width=True)
        
        st.info("💡 **差异化流失判定**: 不同品类采用不同的流失判定阈值，基于该品类用户购买间隔的中位数+2倍标准差计算，避免用固定90天判定所有品类的用户流失。")
        
        st.markdown("---")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📈 总体 Kaplan-Meier 生存曲线")
        
        kmf = KaplanMeierFitter()
        kmf.fit(surv_data['duration_days'], event_observed=surv_data['churned'])
        
        surv_df = kmf.survival_function_.reset_index()
        surv_df.columns = ['timeline', 'survival_prob']
        
        ci_df = kmf.confidence_interval_.reset_index()
        
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=surv_df['timeline'],
            y=surv_df['survival_prob'],
            mode='lines',
            name='生存概率',
            line=dict(color='#3b82f6', width=3)
        ))
        fig.add_trace(go.Scatter(
            x=ci_df['timeline'],
            y=ci_df.iloc[:, 1],
            mode='lines',
            line=dict(width=0),
            showlegend=False
        ))
        fig.add_trace(go.Scatter(
            x=ci_df['timeline'],
            y=ci_df.iloc[:, 2],
            mode='lines',
            line=dict(width=0),
            fill='tonexty',
            fillcolor='rgba(59, 130, 246, 0.2)',
            name='95% 置信区间'
        ))
        fig.update_layout(
            title='用户留存 Kaplan-Meier 曲线',
            xaxis_title='天数',
            yaxis_title='留存概率'
        )
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        st.subheader("🧩 不同用户群体生存曲线对比")
        
        if 'km_segment' in results and 'groups' in results['km_segment']:
            fig = go.Figure()
            
            for segment_name, segment_data in results['km_segment']['groups'].items():
                surv_func = segment_data['survival_function'].reset_index()
                surv_func.columns = ['timeline', 'survival_prob']
                
                fig.add_trace(go.Scatter(
                    x=surv_func['timeline'],
                    y=surv_func['survival_prob'],
                    mode='lines',
                    name=segment_name,
                    line=dict(width=2)
                ))
            
            fig.update_layout(
                title='各用户群体留存曲线对比',
                xaxis_title='天数',
                yaxis_title='留存概率',
                legend_title='用户群体'
            )
            st.plotly_chart(fig, use_container_width=True)
    
    st.markdown("---")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("🛒 不同渠道生存曲线对比")
        
        if 'km_channel' in results and 'groups' in results['km_channel']:
            fig = go.Figure()
            
            for channel_name, channel_data in results['km_channel']['groups'].items():
                surv_func = channel_data['survival_function'].reset_index()
                surv_func.columns = ['timeline', 'survival_prob']
                
                fig.add_trace(go.Scatter(
                    x=surv_func['timeline'],
                    y=surv_func['survival_prob'],
                    mode='lines',
                    name=channel_name,
                    line=dict(width=2)
                ))
            
            fig.update_layout(
                title='各渠道用户留存曲线对比',
                xaxis_title='天数',
                yaxis_title='留存概率',
                legend_title='购买渠道'
            )
            st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        st.subheader("📊 Cox 比例风险模型")
        
        if 'cox_results' in results:
            cox_summary = results['cox_results']['model_summary']
            
            hazard_ratios = results['cox_results']['hazard_ratios']
            
            hr_df = pd.DataFrame({
                '特征': hazard_ratios.index,
                '风险比': hazard_ratios.values,
                'p值': cox_summary['p'].values
            }).head(10)
            
            hr_df = hr_df.sort_values('风险比', ascending=False)
            
            fig = px.bar(
                hr_df,
                x='风险比',
                y='特征',
                color='风险比',
                color_continuous_scale='RdBu_r',
                orientation='h',
                title='Top 10 风险因素 (风险比 >1 表示增加流失风险)'
            )
            fig.add_vline(x=1, line_dash='dash', line_color='red')
            st.plotly_chart(fig, use_container_width=True)
            
            st.info(f"📊 模型 Concordance Index: {results['cox_results']['concordance_index']:.3f} | AIC: {results['cox_results']['aic']:.1f}")
    
    st.markdown("---")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("🛒 不同品类生存曲线对比")
        
        if 'km_category' in results and 'groups' in results['km_category']:
            fig = go.Figure()
            
            for category_name, category_data in results['km_category']['groups'].items():
                surv_func = category_data['survival_function'].reset_index()
                surv_func.columns = ['timeline', 'survival_prob']
                
                fig.add_trace(go.Scatter(
                    x=surv_func['timeline'],
                    y=surv_func['survival_prob'],
                    mode='lines',
                    name=category_name,
                    line=dict(width=2)
                ))
            
            fig.update_layout(
                title='各品类用户留存曲线对比',
                xaxis_title='天数',
                yaxis_title='留存概率',
                legend_title='产品品类'
            )
            st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        st.subheader("⏱️ 流失阈值分组分析")
        
        if 'km_threshold' in results and 'groups' in results['km_threshold']:
            fig = go.Figure()
            
            for threshold_name, threshold_data in results['km_threshold']['groups'].items():
                surv_func = threshold_data['survival_function'].reset_index()
                surv_func.columns = ['timeline', 'survival_prob']
                
                colors = {'Short Cycle': '#ef4444', 'Medium Cycle': '#eab308', 'Long Cycle': '#22c55e'}
                
                fig.add_trace(go.Scatter(
                    x=surv_func['timeline'],
                    y=surv_func['survival_prob'],
                    mode='lines',
                    name=threshold_name,
                    line=dict(width=2, color=colors.get(threshold_name, None))
                ))
            
            fig.update_layout(
                title='不同购买周期用户留存曲线对比',
                xaxis_title='天数',
                yaxis_title='留存概率',
                legend_title='购买周期'
            )
            st.plotly_chart(fig, use_container_width=True)
    
    if 'category_repurchase' in results:
        st.markdown("---")
        st.subheader("📊 品类级复购概率预测")
        
        cat_repurchase = results['category_repurchase']
        if isinstance(cat_repurchase, pd.DataFrame) and len(cat_repurchase) > 0:
            cat_summary = cat_repurchase.groupby('product_category').agg({
                'category_repurchase_prob': 'mean',
                'days_since_last': 'mean',
                'churned': 'mean',
                'total_purchases': 'mean'
            }).reset_index()
            
            cat_summary['churned'] = cat_summary['churned'] * 100
            
            cat_summary.columns = ['产品品类', '平均复购概率', '平均距上次购买天数', '品类流失率(%)', '平均购买次数']
            
            col1, col2 = st.columns([1.5, 1])
            
            with col1:
                st.dataframe(
                    cat_summary.style.format({
                        '平均复购概率': '{:.2%}',
                        '平均距上次购买天数': '{:.1f}',
                        '品类流失率(%)': '{:.1f}%',
                        '平均购买次数': '{:.1f}'
                    }),
                    use_container_width=True,
                    hide_index=True
                )
            
            with col2:
                fig = px.scatter(
                    cat_summary,
                    x='平均距上次购买天数',
                    y='平均复购概率',
                    size='平均购买次数',
                    color='产品品类',
                    title='各品类复购概率 vs 距上次购买天数',
                    labels={'平均复购概率': '复购概率', '平均距上次购买天数': '距上次购买天数'}
                )
                st.plotly_chart(fig, use_container_width=True)
    
    if 'logrank_test' in results.get('km_segment', {}):
        st.markdown("---")
        st.subheader("📋 统计显著性检验 (Log-Rank Test)")
        
        logrank_df = results['km_segment']['logrank_test']
        if logrank_df is not None:
            st.dataframe(logrank_df, use_container_width=True)

def show_attribution(analyzer):
    st.header("🔍 忠诚度影响因素归因")
    
    if not analyzer.attribution_results:
        st.warning("请先运行分析...")
        return
    
    results = analyzer.attribution_results
    
    st.subheader("🏆 影响忠诚度的关键因素")
    
    importance_df = results['importance_results']['importance_df']
    
    col1, col2 = st.columns(2)
    
    with col1:
        feature_names = {
            'frequency': '购买频次',
            'total_spend': '总消费金额',
            'avg_nps': 'NPS评分',
            'recency_days': '最近购买天数',
            'complaint_count': '投诉次数',
            'unresolved_complaints': '未解决投诉数',
            'avg_customer_service': '客户服务评分',
            'return_rate': '退货率',
            'total_interactions': '互动次数',
            'tenure_days': '客户留存天数',
            'avg_order_value': '平均客单价',
            'repurchase_rate': '复购率',
            'avg_product_quality': '产品质量评分',
            'avg_ease_of_use': '易用性评分',
            'spend_growth_rate': '消费增长率',
            'App Visit': 'APP访问次数',
            'Click-Through': '点击率',
            'Email Open': '邮件打开率',
            'Social Media': '社交媒体互动',
            'Support Call': '客服电话次数',
            'price_sensitivity': '价格敏感度',
            'promotion_responsiveness': '促销响应度',
            'avg_discount_pct': '平均折扣率',
            'max_discount_pct': '最高折扣率',
            'total_discount_amount': '累计折扣金额',
            'promotion_purchase_rate': '促销购买占比',
            'promotion_purchase_count': '促销购买次数',
            'avg_base_price': '平均基准价格',
            'total_base_value': '累计基准价值',
            'avg_final_price': '平均实际支付价格',
            'price_value_ratio': '价格价值比',
            'deal_hunter_score': '淘优惠倾向指数',
            'savings_consciousness': '省钱意识指数',
            'promo_sensitivity': '促销敏感度',
            'only_promo_buyer': '纯促销购买者',
            'never_promo_buyer': '非促销购买者',
            'high_price_sensitivity': '高价格敏感型',
            'low_price_sensitivity': '低价格敏感型',
            'active_categories': '活跃品类数',
            'dynamic_churn_threshold': '动态流失阈值'
        }
        
        top_features = importance_df.copy()
        top_features['feature_cn'] = top_features['feature'].map(feature_names).fillna(top_features['feature'])
        
        fig = px.bar(
            top_features.head(15),
            x='ensemble_score',
            y='feature_cn',
            color='ensemble_score',
            color_continuous_scale='viridis',
            orientation='h',
            text='ensemble_score',
            title='Top 15 关键影响因素'
        )
        fig.update_traces(texttemplate='%{text:.3f}', textposition='outside')
        fig.update_layout(yaxis_title='影响因素', xaxis_title='重要性得分')
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        st.subheader("💡 SHAP 特征重要性")
        
        shap_summary = results['shap_results']['shap_summary'].head(15)
        shap_summary['feature_cn'] = shap_summary['feature'].map(feature_names).fillna(shap_summary['feature'])
        
        fig = px.bar(
            shap_summary,
            x='mean_abs_shap_value',
            y='feature_cn',
            color='mean_shap_value',
            color_continuous_scale='RdBu',
            orientation='h',
            title='SHAP 特征重要性 (平均绝对SHAP值)'
        )
        fig.update_layout(yaxis_title='影响因素', xaxis_title='平均绝对 SHAP 值')
        st.plotly_chart(fig, use_container_width=True)
    
    st.markdown("---")
    
    st.subheader("📊 各因素对忠诚度的影响")
    
    factor_impact = results['factor_impact'].copy()
    factor_impact['factor_cn'] = factor_impact['factor'].map(feature_names).fillna(factor_impact['factor'])
    
    factor_display = factor_impact[['factor_cn', 'high_loyalty_avg', 'medium_loyalty_avg', 'low_loyalty_avg', 'high_low_difference', 'correlation_with_loyalty', 'impact_direction']].copy()
    
    factor_display.columns = ['影响因素', '高忠诚度均值', '中忠诚度均值', '低忠诚度均值', '高低差', '相关系数', '影响方向']
    
    for col in ['高忠诚度均值', '中忠诚度均值', '低忠诚度均值', '高低差', '相关系数']:
        factor_display[col] = factor_display[col].round(3)
    
    st.dataframe(
        factor_display,
        use_container_width=True,
        hide_index=True
    )
    
    st.markdown("---")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("⚠️ 流失驱动因素分析")
        
        churn_drivers = results['churn_drivers'].copy()
        churn_drivers['factor_cn'] = churn_drivers['factor'].map(feature_names).fillna(churn_drivers['factor'])
        
        fig = px.bar(
            churn_drivers,
            x='percent_difference',
            y='factor_cn',
            color='is_significant',
            color_discrete_map={True: '#ef4444', False: '#9ca3af'},
            orientation='h',
            text='percent_difference',
            title='高低忠诚度用户差异 (%)'
        )
        fig.update_traces(texttemplate='%{text:.1f}%', textposition='outside')
        fig.add_vline(x=0, line_dash='dash', line_color='gray')
        fig.update_layout(yaxis_title='影响因素', xaxis_title='低忠诚度用户 vs 高忠诚度用户 差异%')
        st.plotly_chart(fig, use_container_width=True)
    with col2:
        st.subheader("📈 相关性热力图")
        
        corr_features = ['frequency', 'total_spend', 'avg_nps', 'complaint_count', 'recency_days', 'total_interactions', 'avg_order_value']
        
        if analyzer.clustering_results:
            features = analyzer.clustering_results['features_with_clusters']
            features['loyalty_num'] = features['loyalty_level'].map({'高': 2, '中': 1, '低': 0})
            
            corr_cols = corr_features + ['loyalty_num']
            corr_data = features[corr_cols].corr()
            
            corr_data.columns = [feature_names.get(col, col) for col in corr_data.columns]
            corr_data.index = [feature_names.get(col, col) for col in corr_data.index]
            
            fig = px.imshow(
                corr_data,
                color_continuous_scale='RdBu_r',
                zmin=-1, zmax=1,
                title='关键特征相关性热力图'
            )
            st.plotly_chart(fig, use_container_width=True)
    
    if 'segment_attribution' in results:
        st.markdown("---")
        st.subheader("👥 各用户群体关键影响因素")
        
        segments = list(results['segment_attribution'].keys())
        selected_segment = st.selectbox("选择用户群体", segments)
        
        if selected_segment:
            seg_impact = results['segment_attribution'][selected_segment].copy()
            seg_impact['factor_cn'] = seg_impact['factor'].map(feature_names).fillna(seg_impact['factor'])
            
            fig = px.bar(
                seg_impact,
                x='correlation_with_loyalty',
                y='factor_cn',
                color='impact_direction',
                color_discrete_map={'positive': '#22c55e', 'negative': '#ef4444'},
                orientation='h',
                title=f'{selected_segment} 群体各因素与忠诚度相关性'
            )
            fig.add_vline(x=0, line_dash='dash', line_color='gray')
            st.plotly_chart(fig, use_container_width=True)
    
    if 'price_promotion_impact' in results:
        st.markdown("---")
        st.subheader("💰 价格与促销因素影响分析")
        
        pp_impact = results['price_promotion_impact']
        
        tab1, tab2, tab3, tab4 = st.tabs(["📊 总体影响", "🛒 品类分析", "🎁 促销类型", "👥 细分群体"])
        
        with tab1:
            if 'overall' in pp_impact:
                overall = pp_impact['overall']
                
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    tiers = list(overall['price_sensitivity_by_tier'].keys())
                    values = [overall['price_sensitivity_by_tier'].get(t, 0) for t in tiers]
                    fig = px.bar(
                        x=tiers, y=values,
                        title='各层级价格敏感度',
                        labels={'x': '忠诚度层级', 'y': '价格敏感度'},
                        color=tiers,
                        color_discrete_map={'高': '#22c55e', '中': '#eab308', '低': '#ef4444'}
                    )
                    st.plotly_chart(fig, use_container_width=True)
                
                with col2:
                    tiers = list(overall['promotion_responsiveness_by_tier'].keys())
                    values = [overall['promotion_responsiveness_by_tier'].get(t, 0) for t in tiers]
                    fig = px.bar(
                        x=tiers, y=values,
                        title='各层级促销响应度',
                        labels={'x': '忠诚度层级', 'y': '促销响应度'},
                        color=tiers,
                        color_discrete_map={'高': '#22c55e', '中': '#eab308', '低': '#ef4444'}
                    )
                    st.plotly_chart(fig, use_container_width=True)
                
                with col3:
                    tiers = list(overall['promo_purchase_rate_by_tier'].keys())
                    values = [overall['promo_purchase_rate_by_tier'].get(t, 0) * 100 for t in tiers]
                    fig = px.bar(
                        x=tiers, y=values,
                        title='各层级促销购买占比 (%)',
                        labels={'x': '忠诚度层级', 'y': '促销购买占比 (%)'},
                        color=tiers,
                        color_discrete_map={'高': '#22c55e', '中': '#eab308', '低': '#ef4444'}
                    )
                    st.plotly_chart(fig, use_container_width=True)
                
                if 'correlations' in pp_impact:
                    corr_data = pd.DataFrame({
                        '特征': list(pp_impact['correlations'].keys()),
                        '相关系数': list(pp_impact['correlations'].values())
                    })
                    corr_data = corr_data[corr_data['特征'] != 'loyalty_numeric'].sort_values('相关系数', ascending=False)
                    
                    fig = px.bar(
                        corr_data,
                        x='相关系数',
                        y='特征',
                        color='相关系数',
                        color_continuous_scale='RdBu_r',
                        range_color=[-1, 1],
                        orientation='h',
                        title='价格促销特征与忠诚度相关性'
                    )
                    fig.add_vline(x=0, line_dash='dash', line_color='gray')
                    st.plotly_chart(fig, use_container_width=True)
        
        with tab2:
            if 'category' in pp_impact:
                cat_data = pp_impact['category']
                
                categories = list(cat_data.keys())
                metrics = ['high_loyal_avg_discount', 'low_loyal_avg_discount', 'discount_correlation']
                
                cat_display = pd.DataFrame([{
                    '品类': cat,
                    '高忠诚度平均折扣': cat_data[cat].get('high_loyal_avg_discount', 0) * 100,
                    '低忠诚度平均折扣': cat_data[cat].get('low_loyal_avg_discount', 0) * 100,
                    '折扣与忠诚度相关系数': cat_data[cat].get('discount_correlation', 0),
                    '高忠诚度平均消费': cat_data[cat].get('high_loyal_spend', 0),
                    '低忠诚度平均消费': cat_data[cat].get('low_loyal_spend', 0)
                } for cat in categories])
                
                fig = px.bar(
                    cat_display.melt(id_vars='品类', 
                                    value_vars=['高忠诚度平均折扣', '低忠诚度平均折扣'],
                                    var_name='层级', value_name='折扣率(%)'),
                    x='品类',
                    y='折扣率(%)',
                    color='层级',
                    barmode='group',
                    title='各品类高低忠诚度用户折扣对比'
                )
                st.plotly_chart(fig, use_container_width=True)
                
                col1, col2 = st.columns(2)
                
                with col1:
                    fig = px.bar(
                        cat_display,
                        x='品类',
                        y='折扣与忠诚度相关系数',
                        color='折扣与忠诚度相关系数',
                        color_continuous_scale='RdBu_r',
                        range_color=[-1, 1],
                        title='各品类折扣与忠诚度相关性'
                    )
                    fig.add_hline(y=0, line_dash='dash', line_color='gray')
                    st.plotly_chart(fig, use_container_width=True)
                
                with col2:
                    spend_data = cat_display.melt(id_vars='品类',
                                                value_vars=['高忠诚度平均消费', '低忠诚度平均消费'],
                                                var_name='层级', value_name='平均消费')
                    fig = px.bar(
                        spend_data,
                        x='品类',
                        y='平均消费',
                        color='层级',
                        barmode='group',
                        title='各品类高低忠诚度用户消费对比'
                    )
                    st.plotly_chart(fig, use_container_width=True)
        
        with tab3:
            if 'promotion_types' in pp_impact:
                promo_data = pp_impact['promotion_types']
                
                promo_df = pd.DataFrame([{
                    '促销类型': promo,
                    '高忠诚度使用率': data.get('high_loyal_usage', 0),
                    '低忠诚度使用率': data.get('low_loyal_usage', 0),
                    '与忠诚度相关性': data.get('correlation', 0)
                } for promo, data in promo_data.items()])
                
                promo_df_melt = promo_df.melt(id_vars='促销类型',
                                              value_vars=['高忠诚度使用率', '低忠诚度使用率'],
                                              var_name='层级', value_name='使用率')
                
                fig = px.bar(
                    promo_df_melt,
                    x='促销类型',
                    y='使用率',
                    color='层级',
                    barmode='group',
                    title='各促销类型在高低忠诚度用户中的使用率'
                )
                st.plotly_chart(fig, use_container_width=True)
        
        with tab4:
            if 'segments' in pp_impact:
                seg_data = pp_impact['segments']
                
                seg_df = pd.DataFrame([{
                    '细分群体': seg,
                    '平均价格敏感度': data.get('avg_price_sensitivity', 0),
                    '平均促销响应度': data.get('avg_promo_responsiveness', 0),
                    '促销购买率': data.get('promo_purchase_rate', 0),
                    '高忠诚度占比': data.get('high_loyal_ratio', 0) * 100
                } for seg, data in seg_data.items()])
                
                col1, col2 = st.columns(2)
                
                with col1:
                    fig = px.scatter(
                        seg_df,
                        x='平均价格敏感度',
                        y='平均促销响应度',
                        size='促销购买率',
                        color='高忠诚度占比',
                        hover_data=['细分群体'],
                        title='各细分群体价格敏感度 vs 促销响应度'
                    )
                    st.plotly_chart(fig, use_container_width=True)
                
                with col2:
                    seg_melt = seg_df.melt(id_vars='细分群体',
                                           value_vars=['平均价格敏感度', '平均促销响应度'],
                                           var_name='特征', value_name='数值')
                    fig = px.bar(
                        seg_melt,
                        x='细分群体',
                        y='数值',
                        color='特征',
                        barmode='group',
                        title='各细分群体价格与促销特征对比'
                    )
                    st.plotly_chart(fig, use_container_width=True)

def show_strategies(analyzer):
    st.header("💡 忠诚度提升策略")
    
    if not analyzer.loyalty_results:
        st.warning("请先运行分析...")
        return
    
    strategies = analyzer.loyalty_results['tiered_strategies']
    
    for tier, info in strategies.items():
        with st.expander(f"🎯 {tier} 用户策略"):
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("用户数量", f"{info['count']:,}")
            with col2:
                st.metric("平均忠诚度指数", f"{info['avg_index']:.1f}")
            with col3:
                st.metric("策略重点", info['focus'])
            
            st.markdown("##### 📋 核心策略建议:")
            
            for i, strategy in enumerate(info['key_strategies']):
                st.markdown(f"{i+1}. {strategy}")
            
            st.markdown(f"##### 📊 预期效果: **{info['expected_impact']}**")
            
            st.markdown(f"##### 📈 关注指标: {', '.join(info['key_metrics'])}")
            
            if 'positive_drivers' in info:
                col1, col2 = st.columns(2)
                with col1:
                    st.info(f"✅ 正向驱动因素: {', '.join(info['positive_drivers'][:3])}")
                with col2:
                    st.warning(f"⚠️ 负向驱动因素: {', '.join(info['negative_drivers'][:2])}")
            
            if 'avg_price_sensitivity' in info:
                st.markdown("##### 💰 价格与促销特征:")
                col1, col2 = st.columns(2)
                with col1:
                    st.info(f"📊 平均价格敏感度: {info['avg_price_sensitivity']:.3f}")
                with col2:
                    st.info(f"🎁 平均促销响应度: {info['avg_promotion_responsiveness']:.3f}")
    
    if 'segment_recommendations' in analyzer.loyalty_results:
        st.markdown("---")
        st.subheader("💰 价格促销分群策略")
        
        seg_recs = analyzer.loyalty_results['segment_recommendations']
        
        for seg, info in seg_recs.items():
            with st.expander(f"📊 {seg} 群体策略 ({info['user_count']} 用户)"):
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.metric("平均忠诚度指数", f"{info['avg_loyalty_index']:.1f}")
                with col2:
                    st.metric("平均总消费", f"{info['avg_total_spend']:,.0f}")
                with col3:
                    st.metric("群体描述", info['segment_description'])
                
                st.markdown("##### 🎯 针对性策略:")
                for i, strategy in enumerate(info['targeted_strategies']):
                    st.markdown(f"{i+1}. {strategy}")
                
                if 'tier_distribution' in info:
                    st.markdown("##### 📈 层级分布:")
                    tier_df = pd.DataFrame([{
                        '层级': tier,
                        '用户数': count
                    } for tier, count in info['tier_distribution'].items()])
                    st.dataframe(tier_df, use_container_width=True, hide_index=True)
    
    if 'personalized_recommendations' in analyzer.loyalty_results:
        st.markdown("---")
        st.subheader("👤 用户级个性化推荐")
        
        personal_recs = analyzer.loyalty_results['personalized_recommendations']
        
        if len(personal_recs) > 0:
            user_tiers = ['全部', '高忠诚度', '中忠诚度', '低忠诚度']
            selected_tier = st.selectbox("筛选用户层级", user_tiers, key="personal_tier_filter")
            
            filtered_recs = personal_recs
            if selected_tier != '全部':
                filtered_recs = personal_recs[personal_recs['loyalty_tier'] == selected_tier]
            
            st.dataframe(
                filtered_recs[['customer_id', 'loyalty_tier', 'loyalty_index', 'user_segment', 'priority_score', 'expected_outcome']],
                use_container_width=True,
                hide_index=True
            )
            
            selected_user = st.selectbox(
                "选择用户查看详细推荐", 
                filtered_recs['customer_id'].tolist(),
                key="personal_user_select"
            )
            
            if selected_user:
                user_data = filtered_recs[filtered_recs['customer_id'] == selected_user].iloc[0]
                
                st.markdown("---")
                st.markdown(f"### 📋 用户 {selected_user} 个性化分析")
                
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    st.metric("忠诚度层级", user_data['loyalty_tier'])
                with col2:
                    st.metric("忠诚度指数", f"{user_data['loyalty_index']:.1f}")
                with col3:
                    st.metric("用户细分类型", user_data['user_segment'])
                with col4:
                    st.metric("优先级分数", f"{user_data['priority_score']}/5")
                
                preferences = user_data['preferences']
                if isinstance(preferences, dict):
                    st.markdown("#### 🎯 用户偏好识别")
                    
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        st.markdown("**🛒 品类偏好**")
                        top_cats = preferences.get('top_categories', [])
                        for i, cat in enumerate(top_cats, 1):
                            st.markdown(f"{i}. {cat}")
                    
                    with col2:
                        st.markdown("**💰 价格特征**")
                        st.markdown(f"- 价格敏感度: **{preferences.get('price_sensitivity_level', 'N/A')}**")
                        st.markdown(f"- 促销响应度: **{preferences.get('promotion_responsiveness', 'N/A')}**")
                        st.markdown(f"- 促销购买占比: **{preferences.get('promotion_purchase_rate', 0):.1%}**")
                    
                    with col3:
                        st.markdown("**📊 行为特征**")
                        st.markdown(f"- 活跃程度: **{preferences.get('activity_level', 'N/A')}**")
                        st.markdown(f"- 购买频次: **{preferences.get('purchase_frequency_level', 'N/A')}**")
                        st.markdown(f"- 消费水平: **{preferences.get('spending_level', 'N/A')}**")
                
                st.markdown("#### 💡 个性化提升策略")
                for i, strategy in enumerate(user_data['personalized_strategies'], 1):
                    if isinstance(strategy, dict):
                        st.markdown(f"**{i}. [{strategy.get('type', '').upper()}] {strategy.get('strategy', '')}**")
                        st.markdown(f"   - 预期效果: {strategy.get('expected_impact', '')}")
                
                if len(user_data['product_recommendations']) > 0:
                    st.markdown("#### 🛒 产品推荐")
                    for i, rec in enumerate(user_data['product_recommendations'], 1):
                        if isinstance(rec, dict):
                            st.markdown(f"{i}. **{rec.get('category', '')}** ({rec.get('recommendation_type', '')})")
                            st.markdown(f"   - {rec.get('rationale', '')}")
                
                if len(user_data['promotion_recommendations']) > 0:
                    st.markdown("#### 🎁 促销推荐")
                    for i, rec in enumerate(user_data['promotion_recommendations'], 1):
                        if isinstance(rec, dict):
                            st.markdown(f"{i}. **{rec.get('promo_type', '')}** - {rec.get('target_category', '')}")
                            st.markdown(f"   - {rec.get('rationale', '')}")
                
                if len(user_data['communication_recommendations']) > 0:
                    st.markdown("#### 📱 沟通推荐")
                    for i, rec in enumerate(user_data['communication_recommendations'], 1):
                        if isinstance(rec, dict):
                            st.markdown(f"{i}. **{rec.get('channel', '')}** ({rec.get('frequency', '')})")
                            st.markdown(f"   - 最佳时间: {rec.get('best_time', '')}")
                
                st.markdown(f"#### 🎯 预期结果: **{user_data['expected_outcome']}**")
    
    st.markdown("---")
    
    st.subheader("📊 基于归因分析的提升策略")
    
    if analyzer.attribution_results:
        recommendations = analyzer.attribution_results['recommendations']
        
        for _, rec in recommendations.iterrows():
            priority_color = {"high": "🔴", "medium": "🟡", "low": "🟢"}
            type_zh = {"enhance": "提升", "mitigate": "降低", "churn_prevention": "流失预防"}
            
            with st.container():
                col1, col2, col3 = st.columns([1, 4, 1])
                
                with col1:
                    st.metric("优先级", f"{priority_color.get(rec['priority'], '⚪')}")
                with col2:
                    st.markdown(f"**[{type_zh.get(rec['type'], rec['type'])}] {rec['strategy']}")
                with col3:
                    impact_value = rec['impact']
                    if isinstance(impact_value, (int, float)):
                        impact_display = f"{impact_value:.2f}"
                    else:
                        impact_display = str(impact_value)
                    st.metric("影响程度", impact_display)
    
    st.markdown("---")
    
    st.subheader("📈 分维度提升方案")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("### 🔄 复购率提升")
        st.markdown("""
        - **个性化推荐系统
        - 订阅制服务
        - 忠诚度积分奖励
        - 定期购买提醒
        - 复购专属优惠
        """)
    
    with col2:
        st.markdown("### 👍 NPS 提升")
        st.markdown("""
        - 产品质量持续改进
        - 客户服务培训
        - 购买后跟进关怀
        - 推荐奖励计划
        - 用户反馈快速响应
        """)
    
    with col3:
        st.markdown("### ⚠️ 投诉率降低")
        st.markdown("""
        - 优化投诉处理流程
        - 建立投诉预警机制
        - 提高首次解决率
        - 客服授权赋能
        - 定期客户满意度调查
        """)
    
    st.markdown("---")
    
    st.subheader("📊 行动计划优先级矩阵")
    
    action_matrix = pd.DataFrame({
        '行动项': [
            '建立VIP会员专属权益体系',
            '推出个性化推荐引擎',
            '优化客户投诉处理流程',
            '实施NPS持续改进闭环',
            '建立流失预警模型',
            '开展高价值客户关怀',
            '优化全渠道体验整合',
            '推出用户推荐奖励计划'
        ],
        '优先级': ['高', '高', '高', '中', '高', '中', '中', '低'],
        '预期效果': ['提升高价值用户留存 15%', '提升复购率 10%', '降低投诉率 20%', '提升NPS 15分', '降低流失率 12%', '提升客单价 8%', '提升用户体验', '提升推荐率 10%'],
        '投入成本': ['中', '高', '低', '低', '中', '低', '高', '低']
    })
    
    def color_priority(row):
        if row['优先级'] == '高':
            return ['background-color: rgba(239, 68, 68, 0.1)'] * len(row)
        elif row['优先级'] == '中':
            return ['background-color: rgba(234, 179, 8, 0.1)'] * len(row)
        else:
            return ['background-color: rgba(34, 197, 94, 0.1)'] * len(row)
    
    st.dataframe(
        action_matrix.style.apply(color_priority, axis=1),
        use_container_width=True,
        hide_index=True
    )
    
    st.markdown("---")
    
    st.subheader("📈 预期收益估算")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("📈 预期CLV提升", "+15-25%", help="客户终身价值提升")
    with col2:
        st.metric("🔄 复购率提升", "+10-15%")
    with col3:
        st.metric("👍 NPS提升", "+10-20 分")
    with col4:
        st.metric("📉 流失率降低", "-8-15%")
    
    st.info("💡 提示: 点击左侧按钮可重新生成数据并进行不同场景的分析")

def show_competitor_analysis(analyzer):
    st.header("🏢 竞争对手流转分析")
    
    if not analyzer.competitor_results:
        st.warning("请先运行分析...")
        return
    
    results = analyzer.competitor_results
    overview = results.get('switch_overview', {})
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("🔄 总流转用户数", f"{overview.get('unique_switchers', 0):,}")
    with col2:
        st.metric("💰 流转前平均消费", f"¥{overview.get('avg_previous_spend', 0):,.0f}")
    with col3:
        st.metric("📊 流转用户平均忠诚度", f"{overview.get('avg_loyalty_tendency', 0):.2f}")
    with col4:
        st.metric("🔙 用户回归率", f"{overview.get('return_rate', 0):.1%}")
    
    st.markdown("---")
    
    switch_reasons = results.get('switch_reasons', {})
    if switch_reasons:
        st.subheader("📊 用户转向竞品原因分析")
        
        col1, col2 = st.columns(2)
        
        with col1:
            primary_reasons = switch_reasons.get('primary_reason_distribution', {})
            if primary_reasons:
                reason_df = pd.DataFrame({
                    '原因': list(primary_reasons.keys()),
                    '人数': list(primary_reasons.values())
                })
                fig = px.bar(reason_df, x='人数', y='原因', color='人数',
                           color_continuous_scale='Reds', orientation='h',
                           title='主要流转原因排名')
                st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            all_reasons = switch_reasons.get('all_reasons_distribution', {})
            if all_reasons:
                top_reasons = dict(list(all_reasons.items())[:8])
                fig = px.pie(values=list(top_reasons.values()), names=list(top_reasons.keys()),
                           title='所有流转原因占比', hole=0.4)
                st.plotly_chart(fig, use_container_width=True)
        
        price_pct = switch_reasons.get('price_driven_pct', 0)
        quality_pct = switch_reasons.get('quality_driven_pct', 0)
        
        col1, col2 = st.columns(2)
        with col1:
            st.info(f"💰 **价格驱动型流转**: {price_pct:.1f}% 的用户因价格/促销原因转向竞品")
        with col2:
            st.info(f"🏆 **品质驱动型流转**: {quality_pct:.1f}% 的用户因品质/服务原因转向竞品")
    
    st.markdown("---")
    
    competitor_analysis = results.get('competitor_analysis', {})
    if competitor_analysis:
        st.subheader("🏪 竞品流向分析")
        
        market_share_loss = competitor_analysis.get('market_share_loss', {})
        if market_share_loss:
            comp_df = pd.DataFrame({
                '竞品': list(market_share_loss.keys()),
                '用户流失占比(%)': list(market_share_loss.values())
            })
            
            col1, col2 = st.columns(2)
            
            with col1:
                fig = px.bar(comp_df, x='竞品', y='用户流失占比(%)',
                           color='用户流失占比(%)', color_continuous_scale='Oranges',
                           title='用户流向各竞品占比')
                st.plotly_chart(fig, use_container_width=True)
            
            with col2:
                return_rates = competitor_analysis.get('competitor_return_rates', {})
                if return_rates:
                    ret_df = pd.DataFrame({
                        '竞品': list(return_rates.keys()),
                        '回归率': [f"{v:.1%}" for v in return_rates.values()]
                    })
                    st.dataframe(ret_df, use_container_width=True, hide_index=True)
        
        competitor_reasons = competitor_analysis.get('competitor_reasons', {})
        if competitor_reasons:
            st.subheader("🔍 各竞品吸引用户的差异化原因")
            for comp, reasons in competitor_reasons.items():
                if reasons:
                    reason_str = ' | '.join([f"{k}: {v}人" for k, v in list(reasons.items())[:3]])
                    st.markdown(f"**{comp}**: {reason_str}")
    
    st.markdown("---")
    
    switch_prediction = results.get('switch_prediction', {})
    if switch_prediction:
        st.subheader("⚠️ 流转风险预测")
        
        risk_dist = switch_prediction.get('risk_distribution', {})
        model_acc = switch_prediction.get('model_accuracy', 0)
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("🟢 低风险用户", f"{risk_dist.get('low_risk', 0):,}")
        with col2:
            st.metric("🟡 中风险用户", f"{risk_dist.get('medium_risk', 0):,}")
        with col3:
            st.metric("🔴 高风险用户", f"{risk_dist.get('high_risk', 0):,}")
        with col4:
            st.metric("🎯 模型准确率", f"{model_acc:.1%}")
        
        high_risk = switch_prediction.get('high_risk_customers', [])
        if high_risk:
            st.markdown("##### 🚨 高风险流失用户TOP10")
            risk_df = pd.DataFrame(high_risk[:10])
            risk_df['switch_risk_score'] = risk_df['switch_risk_score'].round(3)
            risk_df.columns = ['用户ID', '流转风险评分']
            st.dataframe(risk_df, use_container_width=True, hide_index=True)
    
    st.markdown("---")
    
    return_analysis = results.get('return_analysis', {})
    if return_analysis:
        st.subheader("🔙 用户回归分析")
        
        col1, col2 = st.columns(2)
        
        with col1:
            ret_rate = return_analysis.get('return_rate', 0)
            ret_loyalty = return_analysis.get('returned_avg_loyalty', 0)
            noret_loyalty = return_analysis.get('not_returned_avg_loyalty', 0)
            
            fig = px.bar(
                x=['回归用户', '未回归用户'],
                y=[ret_loyalty, noret_loyalty],
                color=['回归用户', '未回归用户'],
                color_discrete_map={'回归用户': '#22c55e', '未回归用户': '#ef4444'},
                title=f'回归 vs 未回归用户忠诚度倾向 (回归率: {ret_rate:.1%})',
                labels={'x': '用户类型', 'y': '平均忠诚度倾向'}
            )
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            return_by_reason = return_analysis.get('return_by_reason', {})
            if return_by_reason:
                fig = px.bar(
                    x=list(return_by_reason.keys()),
                    y=list(return_by_reason.values()),
                    title='回归用户的原始流转原因分布',
                    color=list(return_by_reason.values()),
                    color_continuous_scale='Greens'
                )
                st.plotly_chart(fig, use_container_width=True)
    
    st.markdown("---")
    
    strategies = results.get('prevention_strategies', [])
    if strategies:
        st.subheader("🛡️ 流转预防策略")
        
        for i, strat in enumerate(strategies):
            priority_color = {'high': '🔴', 'medium': '🟡', 'low': '🟢'}.get(strat.get('priority', 'low'), '⚪')
            with st.expander(f"{priority_color} [{strat.get('priority', '').upper()}] {strat.get('strategy', '')}"):
                col1, col2 = st.columns(2)
                with col1:
                    st.info(f"📋 **依据**: {strat.get('rationale', '')}")
                    st.info(f"🎯 **目标群体**: {strat.get('target_segment', '')}")
                with col2:
                    st.success(f"📈 **预期效果**: {strat.get('expected_impact', '')}")

def show_loyalty_prediction(analyzer):
    st.header("🔮 忠诚度预测")
    
    if not analyzer.prediction_results:
        st.warning("请先运行分析...")
        return
    
    results = analyzer.prediction_results
    trend_overview = results.get('trend_overview', {})
    
    trend_dist = trend_overview.get('trend_direction_distribution', {})
    overall_change = trend_overview.get('overall_change', {})
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("📈 上升趋势", f"{trend_dist.get('improving_pct', 0):.1f}%",
                  delta=f"{trend_dist.get('improving', 0)} 用户")
    with col2:
        st.metric("📉 下降趋势", f"{trend_dist.get('declining_pct', 0):.1f}%",
                  delta=f"{trend_dist.get('declining', 0)} 用户", delta_color="inverse")
    with col3:
        st.metric("➡️ 稳定趋势", f"{trend_dist.get('stable_pct', 0):.1f}%",
                  delta=f"{trend_dist.get('stable', 0)} 用户")
    with col4:
        avg_change = overall_change.get('avg_change', 0)
        st.metric("📊 平均忠诚度变化", f"{avg_change:+.1f}",
                  delta=f"从{overall_change.get('avg_first_period', 0):.1f}到{overall_change.get('avg_last_period', 0):.1f}")
    
    st.markdown("---")
    
    period_trends = trend_overview.get('period_trends', {})
    if period_trends:
        st.subheader("📈 忠诚度季度趋势")
        
        trend_df = pd.DataFrame([
            {
                '季度': period,
                '平均忠诚度': data.get('avg_score', 0),
                '中位数忠诚度': data.get('median_score', 0),
                '上升占比(%)': data.get('up_trend_pct', 0),
                '下降占比(%)': data.get('down_trend_pct', 0)
            }
            for period, data in period_trends.items()
        ])
        
        fig = make_subplots(rows=1, cols=2, subplot_titles=('忠诚度得分趋势', '趋势方向占比'))
        
        fig.add_trace(go.Scatter(x=trend_df['季度'], y=trend_df['平均忠诚度'],
                                mode='lines+markers', name='平均忠诚度', line=dict(width=3)), row=1, col=1)
        fig.add_trace(go.Scatter(x=trend_df['季度'], y=trend_df['中位数忠诚度'],
                                mode='lines+markers', name='中位数忠诚度', line=dict(width=2, dash='dash')), row=1, col=1)
        
        fig.add_trace(go.Bar(x=trend_df['季度'], y=trend_df['上升占比(%)'], name='上升占比', marker_color='#22c55e'), row=1, col=2)
        fig.add_trace(go.Bar(x=trend_df['季度'], y=trend_df['下降占比(%)'], name='下降占比', marker_color='#ef4444'), row=1, col=2)
        
        fig.update_layout(height=450, showlegend=True)
        st.plotly_chart(fig, use_container_width=True)
    
    st.markdown("---")
    
    prediction = results.get('loyalty_prediction', {})
    if prediction:
        st.subheader("🔮 未来忠诚度预测")
        
        overall_forecast = prediction.get('overall_forecast', {})
        period_predictions = prediction.get('period_predictions', {})
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("📊 当前平均忠诚度", f"{overall_forecast.get('avg_current_score', 0):.1f}")
        with col2:
            pred_next = overall_forecast.get('avg_predicted_next_q', 0)
            pred_change = overall_forecast.get('avg_predicted_change', 0)
            st.metric("🔮 下季度预测", f"{pred_next:.1f}", delta=f"{pred_change:+.1f}")
        with col3:
            st.metric("📉 预测下降用户", f"{overall_forecast.get('declining_count', 0):,} ({overall_forecast.get('declining_pct', 0):.1f}%)")
        
        if period_predictions:
            pred_df = pd.DataFrame([
                {
                    '预测季度': q_name,
                    '预测平均忠诚度': data.get('avg_predicted_score', 0),
                    '预测上升占比(%)': data.get('improving_pct', 0),
                    '预测下降占比(%)': data.get('declining_pct', 0)
                }
                for q_name, data in period_predictions.items()
            ])
            
            fig = go.Figure()
            fig.add_trace(go.Bar(x=pred_df['预测季度'], y=pred_df['预测上升占比(%)'],
                                name='上升占比', marker_color='#22c55e'))
            fig.add_trace(go.Bar(x=pred_df['预测季度'], y=pred_df['预测下降占比(%)'],
                                name='下降占比', marker_color='#ef4444'))
            fig.update_layout(title='未来季度忠诚度趋势预测', barmode='group')
            st.plotly_chart(fig, use_container_width=True)
    
    st.markdown("---")
    
    transition = results.get('transition_matrix', {})
    if transition:
        st.subheader("🔄 忠诚度层级转换矩阵")
        
        probs = transition.get('transition_probabilities', {})
        if probs:
            matrix_data = []
            for from_tier in ['高', '中', '低']:
                row = []
                for to_tier in ['高', '中', '低']:
                    row.append(probs.get(from_tier, {}).get(to_tier, 0))
                matrix_data.append(row)
            
            matrix_df = pd.DataFrame(matrix_data, index=['高→', '中→', '低→'], columns=['→高', '→中', '→低'])
            
            fig = px.imshow(matrix_df, text_auto='.1%', color_continuous_scale='RdYlGn',
                          range_color=[0, 1], title='忠诚度层级转换概率矩阵',
                          labels=dict(x='目标层级', y='起始层级', color='转换概率'))
            st.plotly_chart(fig, use_container_width=True)
        
        insights = transition.get('key_insights', {})
        col1, col2 = st.columns(2)
        with col1:
            st.success(f"🔒 高忠诚度保持率: {insights.get('high_retention_rate', 0):.1%}")
            st.info(f"📈 中忠诚度升级率: {insights.get('medium_upgrade_rate', 0):.1%}")
        with col2:
            st.error(f"⚠️ 高忠诚度跌落率: {insights.get('high_to_low_rate', 0):.1%}")
            st.warning(f"🔴 低忠诚度固化率: {insights.get('low_churn_escalation', 0):.1%}")
    
    st.markdown("---")
    
    risk_forecast = results.get('risk_forecast', {})
    if risk_forecast:
        st.subheader("⚠️ 风险用户预警")
        
        risk_dist = risk_forecast.get('risk_distribution', {})
        total_at_risk = risk_forecast.get('total_at_risk', 0)
        at_risk_pct = risk_forecast.get('at_risk_pct', 0)
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("🚨 关键风险", f"{risk_dist.get('critical', 0)} 用户")
        with col2:
            st.metric("⚠️ 高风险", f"{risk_dist.get('high', 0)} 用户")
        with col3:
            st.metric("📊 总风险用户", f"{total_at_risk} ({at_risk_pct:.1f}%)")
    
    st.markdown("---")
    
    intervention = results.get('intervention_timing', {})
    if intervention:
        st.subheader("⏰ 干预时机建议")
        
        timing_dist = intervention.get('timing_distribution', {})
        actions = intervention.get('recommended_actions', {})
        
        timing_df = pd.DataFrame({
            '时机': list(timing_dist.keys()),
            '用户数': list(timing_dist.values()),
            '建议行动': [actions.get(k, '') for k in timing_dist.keys()]
        })
        
        timing_name_map = {
            'immediate': '🚨 立即行动',
            'within_1_month': '⚠️ 1个月内',
            'within_3_months': '🟡 3个月内',
            'within_6_months': '🟢 6个月内',
            'routine': '⚪ 常规维护'
        }
        timing_df['时机'] = timing_df['时机'].map(timing_name_map).fillna(timing_df['时机'])
        
        st.dataframe(timing_df, use_container_width=True, hide_index=True)

def show_referral_analysis(analyzer):
    st.header("📣 口碑传播分析")
    
    if not analyzer.referral_results:
        st.warning("请先运行分析...")
        return
    
    results = analyzer.referral_results
    overview = results.get('referral_overview', {})
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("📣 总推荐次数", f"{overview.get('total_referrals', 0):,}")
    with col2:
        st.metric("👥 推荐人数量", f"{overview.get('unique_referrers', 0):,}")
    with col3:
        st.metric("✅ 推荐转化率", f"{overview.get('conversion_rate', 0):.1%}")
    with col4:
        st.metric("💰 被推荐人平均消费", f"¥{overview.get('avg_referred_spend', 0):,.0f}")
    
    st.markdown("---")
    
    viral = results.get('viral_coefficient', {})
    if viral:
        st.subheader("🦠 病毒传播系数分析")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            vc = viral.get('viral_coefficient', 0)
            st.metric("病毒系数(K)", f"{vc:.2f}", 
                      delta=viral.get('interpretation', ''))
        with col2:
            evc = viral.get('effective_viral_coefficient', 0)
            st.metric("有效病毒系数", f"{evc:.2f}",
                      delta=viral.get('growth_potential', ''))
        with col3:
            st.metric("人均邀请数", f"{viral.get('invites_per_user', 0):.2f}")
        with col4:
            st.metric("有效转化率", f"{viral.get('effective_conversion_rate', 0):.1%}")
        
        if vc > 1:
            st.success("🚀 病毒系数 > 1，具备自增长潜力！")
        elif vc > 0.5:
            st.info("📊 病毒系数在0.5-1之间，有增长空间但需要推动")
        else:
            st.warning("⚠️ 病毒系数 < 0.5，需要大力改善推荐机制")
    
    st.markdown("---")
    
    conversion = results.get('conversion_analysis', {})
    if conversion:
        st.subheader("📊 推荐转化分析")
        
        col1, col2 = st.columns(2)
        
        with col1:
            conv_by_channel = conversion.get('conversion_by_channel', {})
            if conv_by_channel:
                ch_df = pd.DataFrame({
                    '渠道': list(conv_by_channel.keys()),
                    '转化率': [f"{v:.1%}" for v in conv_by_channel.values()]
                })
                
                ch_df_numeric = pd.DataFrame({
                    '渠道': list(conv_by_channel.keys()),
                    '转化率': list(conv_by_channel.values())
                })
                fig = px.bar(ch_df_numeric, x='渠道', y='转化率', color='转化率',
                           color_continuous_scale='Greens', title='各推荐渠道转化率')
                fig.update_traces(texttemplate=[f'{v:.1%}' for v in conv_by_channel.values()], textposition='outside')
                st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            conv_by_segment = conversion.get('conversion_by_segment', {})
            if conv_by_segment:
                seg_df = pd.DataFrame({
                    '用户细分': list(conv_by_segment.keys()),
                    '转化率': list(conv_by_segment.values())
                })
                fig = px.bar(seg_df, x='用户细分', y='转化率', color='转化率',
                           color_continuous_scale='Blues', title='各用户细分推荐转化率')
                st.plotly_chart(fig, use_container_width=True)
        
        still_active = conversion.get('still_active_rate', 0)
        avg_days = conversion.get('avg_days_to_convert')
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("🔒 被推荐新客留存率", f"{still_active:.1%}")
        with col2:
            if avg_days is not None:
                st.metric("⏱️ 平均转化天数", f"{avg_days:.1f}天")
        with col3:
            st.metric("💰 被推荐人平均首购金额", f"¥{conversion.get('converted_avg_spend', 0):,.0f}")
    
    st.markdown("---")
    
    channel_eff = results.get('channel_effectiveness', {})
    if channel_eff:
        st.subheader("📢 推荐渠道效果评估")
        
        channel_stats = channel_eff.get('channel_stats', [])
        if channel_stats:
            ch_stats_df = pd.DataFrame(channel_stats)
            
            fig = make_subplots(rows=1, cols=2, 
                              subplot_titles=('各渠道转化率', '各渠道单推荐收入'))
            
            fig.add_trace(go.Bar(x=ch_stats_df['referral_channel'], 
                               y=ch_stats_df['conversion_rate'],
                               name='转化率', marker_color='#3b82f6'), row=1, col=1)
            
            fig.add_trace(go.Bar(x=ch_stats_df['referral_channel'],
                               y=ch_stats_df['revenue_per_referral'],
                               name='单推荐收入', marker_color='#22c55e'), row=1, col=2)
            
            fig.update_layout(height=400, showlegend=True)
            st.plotly_chart(fig, use_container_width=True)
            
            best_channel = channel_eff.get('best_channel_by_revenue', 'N/A')
            best_conv = channel_eff.get('best_channel_by_conversion', 'N/A')
            
            col1, col2 = st.columns(2)
            with col1:
                st.success(f"💰 收入最高渠道: **{best_channel}**")
            with col2:
                st.success(f"✅ 转化最高渠道: **{best_conv}**")
    
    st.markdown("---")
    
    referred_value = results.get('referred_customer_value', {})
    if referred_value:
        st.subheader("💰 被推荐新客价值评估")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("💵 人均首购金额", f"¥{referred_value.get('avg_first_spend', 0):,.0f}")
        with col2:
            st.metric("🔄 人均购买频次", f"{referred_value.get('avg_frequency', 0):.1f}")
        with col3:
            st.metric("💎 人均客户价值", f"¥{referred_value.get('avg_customer_value', 0):,.0f}")
        with col4:
            st.metric("📊 总推荐收入", f"¥{referred_value.get('total_referred_revenue', 0):,.0f}")
        
        active_val = referred_value.get('active_referred_value', 0)
        churned_val = referred_value.get('churned_referred_value', 0)
        retention = referred_value.get('retention_rate', 0)
        
        fig = px.bar(
            x=['留存新客', '流失新客'],
            y=[active_val, churned_val],
            color=['留存新客', '流失新客'],
            color_discrete_map={'留存新客': '#22c55e', '流失新客': '#ef4444'},
            title=f'被推荐新客价值对比 (留存率: {retention:.1%})',
            labels={'x': '新客状态', 'y': '平均首购金额'}
        )
        st.plotly_chart(fig, use_container_width=True)
    
    st.markdown("---")
    
    referral_prediction = results.get('referral_prediction', {})
    if referral_prediction:
        st.subheader("🔮 推荐潜力预测")
        
        col1, col2 = st.columns(2)
        
        with col1:
            current_pct = referral_prediction.get('current_referrer_pct', 0)
            potential_pct = referral_prediction.get('potential_referrer_pct', 0)
            
            fig = px.bar(
                x=['当前推荐人占比', '潜在推荐人占比'],
                y=[current_pct, potential_pct],
                color=['当前', '潜在'],
                color_discrete_map={'当前': '#3b82f6', '潜在': '#22c55e'},
                title='推荐人覆盖率'
            )
            fig.update_layout(yaxis_title='占比(%)')
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            potential_dist = referral_prediction.get('potential_distribution', {})
            if potential_dist:
                fig = px.pie(
                    values=list(potential_dist.values()),
                    names=['高潜力', '中潜力', '低潜力'],
                    title='用户推荐潜力分布',
                    hole=0.4,
                    color=['高潜力', '中潜力', '低潜力'],
                    color_discrete_map={'高潜力': '#22c55e', '中潜力': '#eab308', '低潜力': '#ef4444'}
                )
                st.plotly_chart(fig, use_container_width=True)
        
        top_potential = referral_prediction.get('top_potential_referrers', [])
        if top_potential:
            st.markdown("##### 🌟 推荐潜力最大的未参与用户")
            pot_df = pd.DataFrame(top_potential[:10])
            pot_df['referral_potential'] = pot_df['referral_potential'].round(2)
            pot_df.columns = ['用户ID', '推荐潜力评分']
            st.dataframe(pot_df, use_container_width=True, hide_index=True)
    
    st.markdown("---")
    
    loyalty_corr = results.get('loyalty_referral_correlation', {})
    if loyalty_corr:
        st.subheader("🔗 忠诚度与推荐效果关联")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("📊 忠诚度-转化相关性", f"{loyalty_corr.get('loyalty_conversion_correlation', 0):.3f}")
        with col2:
            st.metric("🏆 高忠诚度推荐转化率", f"{loyalty_corr.get('high_loyalty_conversion_rate', 0):.1%}")
        with col3:
            st.metric("📉 低忠诚度推荐转化率", f"{loyalty_corr.get('low_loyalty_conversion_rate', 0):.1%}")
    
    st.markdown("---")
    
    strategies = results.get('optimization_strategies', [])
    if strategies:
        st.subheader("🚀 推荐优化策略")
        
        for i, strat in enumerate(strategies):
            priority_color = {'high': '🔴', 'medium': '🟡', 'low': '🟢'}.get(strat.get('priority', 'low'), '⚪')
            with st.expander(f"{priority_color} [{strat.get('priority', '').upper()}] {strat.get('strategy', '')}"):
                col1, col2 = st.columns(2)
                with col1:
                    st.info(f"📋 **依据**: {strat.get('rationale', '')}")
                    st.info(f"🎯 **目标群体**: {strat.get('target_segment', '')}")
                with col2:
                    st.success(f"📈 **预期效果**: {strat.get('expected_impact', '')}")

if __name__ == "__main__":
    main()
