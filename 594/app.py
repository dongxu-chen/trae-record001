import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from data_generator import generate_sample_data
from social_media_api import SocialMediaAPI, FollowerAnalyzer, MultiSourceValidator
from influence_model import InfluenceScoreModel, EngagementAnalyzer, InfluencerComparison, FakeFollowerDetector
from attribution_analysis import ROICalculator, AttributionModel, ConversionAnalyzer
from budget_optimizer import BudgetOptimizer, RecommendationEngine, PerformanceForecaster, AudienceOverlapOptimizer
from brand_safety import BrandSafetyDetector
from competitor_analysis import CompetitorAnalyzer
from contract_manager import ContractManager


st.set_page_config(
    page_title="网红营销效果评估平台",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)


@st.cache_data
def load_data():
    influencer_df, demo_df, campaign_df = generate_sample_data()
    return influencer_df, demo_df, campaign_df


def main():
    st.title("📊 网红营销效果评估平台")
    st.markdown("---")
    
    influencer_df, demo_df, campaign_df = load_data()
    
    influence_model = InfluenceScoreModel()
    engagement_analyzer = EngagementAnalyzer()
    roi_calculator = ROICalculator()
    follower_analyzer = FollowerAnalyzer()
    budget_optimizer = BudgetOptimizer()
    recommendation_engine = RecommendationEngine()
    attribution_model = AttributionModel()
    conversion_analyzer = ConversionAnalyzer()
    performance_forecaster = PerformanceForecaster()
    influencer_comparison = InfluencerComparison()
    multi_source_validator = MultiSourceValidator()
    fake_follower_detector = FakeFollowerDetector()
    audience_overlap_optimizer = AudienceOverlapOptimizer()
    brand_safety_detector = BrandSafetyDetector()
    competitor_analyzer = CompetitorAnalyzer()
    contract_manager = ContractManager()
    
    influencer_df_with_score = influence_model.calculate_influence_score(influencer_df)
    campaign_df_with_roi = roi_calculator.calculate_basic_roi(campaign_df)
    
    page = st.sidebar.selectbox(
        "导航菜单",
        ["📊 数据概览", "👥 网红排名与分析", "🎯 粉丝画像分析", "💰 ROI与归因分析", "📈 预算分配优化", 
         "�️ 品牌安全检测", "🏢 竞品投放分析", "📋 合约管理", "�💡 合作建议"]
    )
    
    if page == "📊 数据概览":
        show_overview(influencer_df_with_score, campaign_df_with_roi)
    elif page == "👥 网红排名与分析":
        show_influencer_ranking(influencer_df_with_score, campaign_df_with_roi, influence_model, engagement_analyzer, influencer_comparison, fake_follower_detector)
    elif page == "🎯 粉丝画像分析":
        show_follower_analysis(demo_df, influencer_df, follower_analyzer, multi_source_validator)
    elif page == "💰 ROI与归因分析":
        show_roi_analysis(campaign_df_with_roi, roi_calculator, attribution_model, conversion_analyzer)
    elif page == "📈 预算分配优化":
        show_budget_optimization(influencer_df_with_score, campaign_df_with_roi, budget_optimizer, performance_forecaster, audience_overlap_optimizer, demo_df)
    elif page == "🛡️ 品牌安全检测":
        show_brand_safety(influencer_df_with_score, brand_safety_detector)
    elif page == "🏢 竞品投放分析":
        show_competitor_analysis(influencer_df_with_score, competitor_analyzer)
    elif page == "📋 合约管理":
        show_contract_management(influencer_df_with_score, contract_manager)
    elif page == "💡 合作建议":
        show_recommendations(influencer_df_with_score, recommendation_engine)


def show_overview(influencer_df, campaign_df):
    st.header("📊 数据概览")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            label="网红总数",
            value=len(influencer_df),
            delta=f"{len(influencer_df[influencer_df['influence_score'] > 60])} 位高影响力"
        )
    
    with col2:
        avg_roi = campaign_df['roi'].mean()
        st.metric(
            label="平均ROI",
            value=f"{avg_roi:.1f}%",
            delta=f"{(campaign_df['roi'] > 0).mean()*100:.1f}% 正向ROI"
        )
    
    with col3:
        total_reach = campaign_df['reach'].sum()
        st.metric(
            label="累计触达",
            value=f"{total_reach/10000:.1f}万",
            delta="历史活动累计"
        )
    
    with col4:
        total_conversions = campaign_df['conversions'].sum()
        st.metric(
            label="累计转化",
            value=f"{total_conversions:,}",
            delta=f"转化成本 ¥{campaign_df['cpa'].mean():.0f}"
        )
    
    st.markdown("---")
    
    col_left, col_right = st.columns(2)
    
    with col_left:
        st.subheader("平台分布")
        platform_dist = influencer_df['platform'].value_counts()
        fig = px.pie(
            values=platform_dist.values,
            names=platform_dist.index,
            title="网红平台分布",
            hole=0.4
        )
        st.plotly_chart(fig, use_container_width=True)
    
    with col_right:
        st.subheader("类目分布")
        category_dist = influencer_df['category'].value_counts()
        fig = px.bar(
            x=category_dist.index,
            y=category_dist.values,
            title="网红类目分布",
            color=category_dist.values,
            color_continuous_scale='Viridis'
        )
        st.plotly_chart(fig, use_container_width=True)
    
    st.markdown("---")
    
    col_left2, col_right2 = st.columns(2)
    
    with col_left2:
        st.subheader("影响力等级分布")
        tier_dist = influencer_df['influence_tier'].value_counts().sort_index()
        fig = px.bar(
            x=tier_dist.index,
            y=tier_dist.values,
            title="网红影响力等级分布",
            orientation='h',
            color=tier_dist.values
        )
        st.plotly_chart(fig, use_container_width=True)
    
    with col_right2:
        st.subheader("ROI分布")
        fig = px.histogram(
            campaign_df,
            x='roi',
            nbins=20,
            title="活动ROI分布",
            marginal="box"
        )
        st.plotly_chart(fig, use_container_width=True)
    
    st.markdown("---")
    st.subheader("数据预览")
    
    tab1, tab2, tab3 = st.tabs(["网红数据", "活动数据", "关键指标"])
    
    with tab1:
        st.dataframe(
            influencer_df[['id', 'name', 'platform', 'category', 'followers', 'influence_score', 'influence_tier', 'cooperation_price']],
            use_container_width=True
        )
    
    with tab2:
        st.dataframe(
            campaign_df[['campaign_id', 'campaign_name', 'influencer_name', 'platform', 'actual_cost', 'revenue', 'roi', 'conversions']],
            use_container_width=True
        )
    
    with tab3:
        benchmarks = roi_calculator.get_roi_benchmarks(campaign_df)
        col1, col2, col3 = st.columns(3)
        col1.metric("平均ROI", f"{benchmarks['avg_roi']:.1f}%")
        col2.metric("ROI中位数", f"{benchmarks['median_roi']:.1f}%")
        col3.metric("正向ROI占比", f"{benchmarks['positive_roi_ratio']:.1f}%")


def show_influencer_ranking(influencer_df, campaign_df, influence_model, engagement_analyzer, influencer_comparison, fake_follower_detector):
    st.header("👥 网红排名与分析")
    
    tab_ranking, tab_fake_detection = st.tabs(["🏆 网红排行榜", "🔍 粉丝质量检测"])
    
    st.sidebar.subheader("筛选条件")
    platform_filter = st.sidebar.multiselect(
        "平台",
        options=influencer_df['platform'].unique(),
        default=[],
        key="platform_filter_rank"
    )
    
    category_filter = st.sidebar.multiselect(
        "类目",
        options=influencer_df['category'].unique(),
        default=[],
        key="category_filter_rank"
    )
    
    min_followers = st.sidebar.slider(
        "最低粉丝数",
        min_value=0,
        max_value=int(influencer_df['followers'].max()),
        value=0,
        step=10000,
        key="min_followers_rank"
    )
    
    sort_by = st.sidebar.selectbox(
        "排序方式",
        options=["influence_score", "followers", "cooperation_price", "engagement_score"],
        index=0,
        format_func=lambda x: {
            'influence_score': '影响力评分',
            'followers': '粉丝数',
            'cooperation_price': '合作价格',
            'engagement_score': '互动率'
        }[x],
        key="sort_by_rank"
    )
    
    filtered_df = influencer_df.copy()
    if platform_filter:
        filtered_df = filtered_df[filtered_df['platform'].isin(platform_filter)]
    if category_filter:
        filtered_df = filtered_df[filtered_df['category'].isin(category_filter)]
    filtered_df = filtered_df[filtered_df['followers'] >= min_followers]
    
    filtered_df = filtered_df.sort_values(sort_by, ascending=False).reset_index(drop=True)
    filtered_df['rank'] = filtered_df.index + 1
    
    with tab_ranking:
        st.subheader(f"网红排行榜 (共 {len(filtered_df)} 位)")
        
        display_df = filtered_df[[
            'rank', 'id', 'name', 'platform', 'category', 'followers',
            'influence_score', 'influence_tier', 'cooperation_price'
        ]].copy()
        display_df.columns = ['排名', 'ID', '名称', '平台', '类目', '粉丝数', '影响力评分', '等级', '合作价格(元)']
        
        st.dataframe(display_df, use_container_width=True, hide_index=True)
        
        st.markdown("---")
        st.subheader("网红详情分析")
        
        selected_influencer = st.selectbox(
            "选择网红查看详情",
            options=filtered_df['name'].tolist(),
            format_func=lambda x: f"{x} - {filtered_df[filtered_df['name'] == x]['platform'].iloc[0]}",
            key="selected_influencer_detail"
        )
        
        if selected_influencer:
            influencer_data = filtered_df[filtered_df['name'] == selected_influencer].iloc[0]
            influencer_details = influence_model.get_influencer_details(influencer_df, influencer_data['id'])
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("### 基本信息")
                st.write(f"**ID**: {influencer_details['basic_info']['id']}")
                st.write(f"**名称**: {influencer_details['basic_info']['name']}")
                st.write(f"**平台**: {influencer_details['basic_info']['platform']}")
                st.write(f"**类目**: {influencer_details['basic_info']['category']}")
                st.write(f"**粉丝数**: {influencer_details['basic_info']['followers']:,}")
                st.write(f"**所在城市**: {influencer_details['basic_info']['city']}")
            
            with col2:
                st.markdown("### 影响力指标")
                metrics = influencer_details['influence_metrics']
                
                fig = go.Figure(data=go.Scatterpolar(
                    r=[
                        metrics['reach_score'],
                        metrics['engagement_score'],
                        metrics['growth_score'],
                        metrics['authenticity_score'],
                        metrics['content_quality_score']
                    ],
                    theta=['触达力', '互动率', '成长性', '真实性', '内容质量'],
                    fill='toself'
                ))
                
                fig.update_layout(
                    polar=dict(
                        radialaxis=dict(
                            visible=True,
                            range=[0, 100]
                        )
                    ),
                    showlegend=False,
                    title="影响力雷达图"
                )
                st.plotly_chart(fig, use_container_width=True)
            
            col3, col4 = st.columns(2)
            
            with col3:
                st.markdown("### ✅ 优势")
                for strength in influencer_details['strengths']:
                    st.success(f"• {strength}")
            
            with col4:
                st.markdown("### ⚠️ 待提升")
                for weakness in influencer_details['weaknesses']:
                    st.warning(f"• {weakness}")
            
            st.info(f"💡 {influencer_details['recommendation']}")
        
        st.markdown("---")
        st.subheader("网红对比分析")
        
        selected_for_comparison = st.multiselect(
            "选择要对比的网红（最多5位）",
            options=filtered_df['name'].tolist(),
            max_selections=5,
            key="comparison_select"
        )
        
        if len(selected_for_comparison) >= 2:
            selected_ids = filtered_df[filtered_df['name'].isin(selected_for_comparison)]['id'].tolist()
            comparison_df = influencer_comparison.compare_influencers(influencer_df, selected_ids)
            st.dataframe(comparison_df, use_container_width=True, hide_index=True)
            
            fig = px.bar(
                comparison_df,
                x='网红名称',
                y=['影响力评分', '性价比评分'],
                barmode='group',
                title="网红影响力与性价比对比"
            )
            st.plotly_chart(fig, use_container_width=True)
    
    with tab_fake_detection:
        st.subheader("🔍 僵尸粉丝检测与真实互动率")
        
        with st.spinner("正在进行粉丝质量检测..."):
            quality_df = fake_follower_detector.detect_fake_followers(filtered_df)
        
        sort_by_quality = st.selectbox(
            "按粉丝质量排序",
            options=['real_engagement_rate', 'fake_follower_suspicion_score', 'estimated_fake_percentage'],
            index=0,
            format_func=lambda x: {
                'real_engagement_rate': '真实互动率',
                'fake_follower_suspicion_score': '虚假粉丝可疑度',
                'estimated_fake_percentage': '估计虚假粉丝比例'
            }[x]
        )
        
        quality_display = quality_df.sort_values(sort_by_quality, ascending=False).reset_index(drop=True)
        quality_display['quality_rank'] = quality_display.index + 1
        
        quality_display_df = quality_display[[
            'quality_rank', 'name', 'platform', 'followers', 'estimated_real_followers',
            'estimated_fake_percentage', 'follower_quality_tier',
            'nominal_engagement_rate', 'real_engagement_rate', 'engagement_inflation_rate',
            'fake_follower_suspicion_score'
        ]].copy()
        
        quality_display_df.columns = [
            '排名', '网红名称', '平台', '名义粉丝数', '真实粉丝数估计',
            '虚假粉丝比例(%)', '粉丝质量等级', '名义互动率(%)',
            '真实互动率(%)', '互动水分率(%)', '虚假粉丝可疑度'
        ]
        
        st.dataframe(quality_display_df, use_container_width=True, hide_index=True)
        
        st.markdown("---")
        st.subheader("📊 互动率对比分析")
        
        selected_quality_influencer = st.selectbox(
            "选择网红查看详细粉丝质量报告",
            options=quality_df['name'].tolist(),
            key="quality_influencer_select"
        )
        
        if selected_quality_influencer:
            influencer_id = quality_df[quality_df['name'] == selected_quality_influencer]['id'].iloc[0]
            quality_report = fake_follower_detector.get_follower_quality_report(quality_df, influencer_id)
            
            col_q1, col_q2, col_q3, col_q4 = st.columns(4)
            
            with col_q1:
                st.metric("粉丝质量等级", quality_report['basic_info']['follower_quality_tier'])
            
            with col_q2:
                fake_pct = quality_report['basic_info']['estimated_fake_percentage']
                if fake_pct < 20:
                    st.success(f"虚假粉丝: {fake_pct}%")
                elif fake_pct < 40:
                    st.warning(f"虚假粉丝: {fake_pct}%")
                else:
                    st.error(f"虚假粉丝: {fake_pct}%")
            
            with col_q3:
                st.metric(
                    "名义粉丝",
                    f"{quality_report['basic_info']['nominal_followers']:,}"
                )
            
            with col_q4:
                st.metric(
                    "真实粉丝估计",
                    f"{quality_report['basic_info']['estimated_real_followers']:,}"
                )
            
            st.markdown("---")
            st.markdown("### 📈 名义 vs 真实互动数据对比")
            
            engagement_compare = pd.DataFrame({
                '指标': ['点赞数', '评论数', '分享数', '互动率(%)'],
                '名义数据': [
                    quality_report['engagement_comparison']['nominal_likes'],
                    quality_report['engagement_comparison']['nominal_comments'],
                    quality_report['engagement_comparison']['nominal_shares'],
                    quality_report['engagement_comparison']['nominal_engagement_rate']
                ],
                '真实数据': [
                    quality_report['engagement_comparison']['real_likes'],
                    quality_report['engagement_comparison']['real_comments'],
                    quality_report['engagement_comparison']['real_shares'],
                    quality_report['engagement_comparison']['real_engagement_rate']
                ],
                '水分率(%)': [
                    round((quality_report['engagement_comparison']['nominal_likes'] - quality_report['engagement_comparison']['real_likes']) / max(quality_report['engagement_comparison']['real_likes'], 1) * 100, 1),
                    round((quality_report['engagement_comparison']['nominal_comments'] - quality_report['engagement_comparison']['real_comments']) / max(quality_report['engagement_comparison']['real_comments'], 1) * 100, 1),
                    round((quality_report['engagement_comparison']['nominal_shares'] - quality_report['engagement_comparison']['real_shares']) / max(quality_report['engagement_comparison']['real_shares'], 1) * 100, 1),
                    quality_report['engagement_comparison']['engagement_inflation_rate']
                ]
            })
            
            st.dataframe(engagement_compare, use_container_width=True, hide_index=True)
            
            fig = go.Figure()
            fig.add_trace(go.Bar(
                x=['点赞', '评论', '分享'],
                y=[
                    quality_report['engagement_comparison']['nominal_likes'],
                    quality_report['engagement_comparison']['nominal_comments'],
                    quality_report['engagement_comparison']['nominal_shares']
                ],
                name='名义数据',
                marker_color='lightcoral'
            ))
            fig.add_trace(go.Bar(
                x=['点赞', '评论', '分享'],
                y=[
                    quality_report['engagement_comparison']['real_likes'],
                    quality_report['engagement_comparison']['real_comments'],
                    quality_report['engagement_comparison']['real_shares']
                ],
                name='真实数据',
                marker_color='lightgreen'
            ))
            fig.update_layout(
                title='名义数据 vs 真实数据对比',
                barmode='group'
            )
            st.plotly_chart(fig, use_container_width=True)
            
            st.markdown("---")
            st.subheader("⚠️ 可疑指标分析")
            
            suspicion_data = quality_report['suspicion_analysis']
            suspicion_df = pd.DataFrame({
                '检测维度': [
                    '年龄分布异常', '性别比例异常', '互动一致性',
                    '点赞评论比例', '浏览互动转化', '粉丝增长模式'
                ],
                '可疑度(%)': [
                    suspicion_data['abnormal_age_distribution'],
                    suspicion_data['abnormal_gender_ratio'],
                    suspicion_data['low_engagement_consistency'],
                    suspicion_data['abnormal_like_comment_ratio'],
                    suspicion_data['low_view_engagement'],
                    suspicion_data['suspicious_growth_pattern']
                ]
            })
            
            fig = px.bar(
                suspicion_df,
                x='可疑度(%)',
                y='检测维度',
                orientation='h',
                color='可疑度(%)',
                color_continuous_scale='RdYlGn_r',
                title='各维度虚假粉丝可疑度',
                range_x=[0, 100]
            )
            st.plotly_chart(fig, use_container_width=True)
            
            st.markdown("---")
            st.subheader("🚨 风险警告")
            
            warnings = quality_report['warnings']
            if warnings:
                for warning in warnings:
                    if warning['severity'] == '高':
                        st.error(f"【高风险】{warning['warning']}")
                    elif warning['severity'] == '中':
                        st.warning(f"【中风险】{warning['warning']}")
                    else:
                        st.info(f"【低风险】{warning['warning']}")
            else:
                st.success("✅ 未检测到明显的虚假粉丝风险")
            
            st.info(f"💡 {quality_report['recommendation']}")
            
            st.markdown("---")
            st.subheader("📊 粉丝质量分布")
            
            quality_dist = quality_df.groupby('follower_quality_tier').size().reset_index(name='数量')
            fig = px.pie(
                quality_dist,
                values='数量',
                names='follower_quality_tier',
                title='网红粉丝质量等级分布',
                color_discrete_sequence=['#00CC96', '#636EFA', '#FFA15A', '#EF553B', '#AB63FA']
            )
            st.plotly_chart(fig, use_container_width=True)


def show_follower_analysis(demo_df, influencer_df, follower_analyzer, multi_source_validator):
    st.header("🎯 粉丝画像分析")
    
    tab_basic, tab_validation = st.tabs(["📊 基础画像分析", "🔍 多源交叉验证"])
    
    selected_influencer = st.selectbox(
        "选择网红查看粉丝画像",
        options=demo_df['influencer_name'].tolist(),
        key="follower_analysis_select"
    )
    
    if selected_influencer:
        influencer_id = demo_df[demo_df['influencer_name'] == selected_influencer]['influencer_id'].iloc[0]
        
        with tab_basic:
            demographics = follower_analyzer.analyze_demographics(demo_df, influencer_id)
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.subheader("年龄分布")
                age_data = pd.DataFrame({
                    '年龄段': list(demographics['age_distribution'].keys()),
                    '占比(%)': list(demographics['age_distribution'].values())
                })
                fig = px.pie(
                    age_data,
                    values='占比(%)',
                    names='年龄段',
                    title="粉丝年龄分布",
                    color_discrete_sequence=px.colors.qualitative.Set3
                )
                st.plotly_chart(fig, use_container_width=True)
            
            with col2:
                st.subheader("性别分布")
                gender_data = pd.DataFrame({
                    '性别': list(demographics['gender_distribution'].keys()),
                    '占比(%)': list(demographics['gender_distribution'].values())
                })
                fig = px.pie(
                    gender_data,
                    values='占比(%)',
                    names='性别',
                    title="粉丝性别分布",
                    color_discrete_sequence=['#4A90E2', '#E75480']
                )
                st.plotly_chart(fig, use_container_width=True)
            
            st.markdown("---")
            
            col3, col4 = st.columns(2)
            
            with col3:
                st.subheader("地域分布")
                location_data = pd.DataFrame({
                    '城市等级': list(demographics['location_distribution'].keys()),
                    '占比(%)': list(demographics['location_distribution'].values())
                })
                fig = px.bar(
                    location_data,
                    x='城市等级',
                    y='占比(%)',
                    title="粉丝地域分布",
                    color='城市等级'
                )
                st.plotly_chart(fig, use_container_width=True)
            
            with col4:
                st.subheader("兴趣分布")
                interest_data = pd.DataFrame({
                    '兴趣': list(demographics['interest_distribution'].keys()),
                    '占比(%)': list(demographics['interest_distribution'].values())
                }).sort_values('占比(%)', ascending=False)
                fig = px.bar(
                    interest_data,
                    x='占比(%)',
                    y='兴趣',
                    title="粉丝兴趣分布",
                    orientation='h',
                    color='兴趣'
                )
                st.plotly_chart(fig, use_container_width=True)
            
            st.markdown("---")
            st.subheader("受众匹配度评估")
            
            st.markdown("#### 设置目标受众")
            col5, col6, col7 = st.columns(3)
            
            with col5:
                target_age = st.multiselect(
                    "目标年龄层",
                    options=['18-24', '25-34', '35-44', '45+'],
                    default=['18-24', '25-34'],
                    key="target_age_basic"
                )
            
            with col6:
                target_gender = st.multiselect(
                    "目标性别",
                    options=['男性', '女性'],
                    default=['女性'],
                    key="target_gender_basic"
                )
            
            with col7:
                target_location = st.multiselect(
                    "目标地域",
                    options=['一线城市', '二线城市', '三线及以下'],
                    default=['一线城市', '二线城市'],
                    key="target_location_basic"
                )
            
            target_demo = {
                'age': target_age,
                'gender': target_gender,
                'location': target_location
            }
            
            quality_score = follower_analyzer.calculate_audience_quality_score(
                demo_df, influencer_id, target_demo
            )
            
            st.markdown("#### 匹配度评分")
            col8, col9, col10, col11 = st.columns(4)
            
            with col8:
                st.metric("整体匹配度", f"{quality_score['overall_score']:.1f}")
            
            with col9:
                st.metric("年龄匹配", f"{quality_score['age_match_score']:.1f}")
            
            with col10:
                st.metric("性别匹配", f"{quality_score['gender_match_score']:.1f}")
            
            with col11:
                st.metric("地域匹配", f"{quality_score['location_match_score']:.1f}")
            
            st.info(f"💡 {quality_score['recommendation']}")
        
        with tab_validation:
            st.subheader("🔍 多源数据交叉验证")
            
            with st.spinner("正在进行多源数据交叉验证..."):
                validation_result = multi_source_validator.cross_validate_demographics(demo_df, influencer_id)
            
            st.markdown("### 📋 验证概览")
            col_val1, col_val2, col_val3 = st.columns(3)
            
            with col_val1:
                confidence = validation_result['overall_confidence']
                if confidence >= 80:
                    st.success(f"### 数据置信度: {confidence:.1f}%")
                elif confidence >= 60:
                    st.warning(f"### 数据置信度: {confidence:.1f}%")
                else:
                    st.error(f"### 数据置信度: {confidence:.1f}%")
            
            with col_val2:
                bias_level = validation_result['bias_analysis']['overall_bias_level']
                if bias_level == '低':
                    st.success(f"### 偏差等级: {bias_level}")
                elif bias_level == '中':
                    st.warning(f"### 偏差等级: {bias_level}")
                else:
                    st.error(f"### 偏差等级: {bias_level}")
            
            with col_val3:
                warning_count = len(validation_result['deviation_warnings'])
                st.metric("异常警告数", warning_count)
            
            st.markdown("---")
            st.subheader("📊 多数据源对比")
            
            source_data = validation_result['data_sources']
            metrics_to_show = ['age_18_24', 'age_25_34', 'gender_male', 'location_tier1']
            
            for metric in metrics_to_show:
                st.markdown(f"#### {metric.replace('_', ' ').title()}")
                comparison_data = []
                for source_name, source_values in source_data.items():
                    if metric in source_values:
                        comparison_data.append({
                            '数据源': source_name,
                            '数值(%)': round(source_values[metric] * 100, 2),
                            '验证后数值(%)': round(validation_result['validated_demographics'][metric] * 100, 2)
                        })
                
                comparison_df = pd.DataFrame(comparison_data)
                
                fig = go.Figure()
                fig.add_trace(go.Bar(
                    x=comparison_df['数据源'],
                    y=comparison_df['数值(%)'],
                    name='各数据源',
                    marker_color='lightblue'
                ))
                fig.add_trace(go.Scatter(
                    x=comparison_df['数据源'],
                    y=comparison_df['验证后数值(%)'],
                    name='验证后结果',
                    mode='lines+markers',
                    line=dict(color='red', width=2),
                    marker=dict(size=10)
                ))
                fig.update_layout(title=f"{metric} 多数据源对比", yaxis_title="占比(%)")
                st.plotly_chart(fig, use_container_width=True)
            
            st.markdown("---")
            st.subheader("⚠️ 偏差检测结果")
            
            biases = validation_result['bias_analysis']['detected_biases']
            if biases:
                for bias in biases:
                    severity_color = "error" if bias['severity'] == '高' else "warning"
                    if severity_color == "error":
                        st.error(f"【{bias['severity']}】{bias['source']} - {bias['metric']}: {bias['deviation_percent']:.1f}% {bias['direction']}")
                    else:
                        st.warning(f"【{bias['severity']}】{bias['source']} - {bias['metric']}: {bias['deviation_percent']:.1f}% {bias['direction']}")
            else:
                st.success("✅ 未检测到显著的数据偏差")
            
            st.markdown("---")
            st.subheader("💡 数据一致性警告")
            
            warnings = validation_result['deviation_warnings']
            if warnings:
                for warning in warnings:
                    st.warning(f"⚠️ {warning['warning']}")
            else:
                st.success("✅ 各数据源一致性良好")
            
            st.markdown("---")
            st.subheader("📈 各指标置信度评分")
            
            confidence_scores = validation_result['confidence_scores']
            confidence_df = pd.DataFrame({
                '指标': list(confidence_scores.keys()),
                '置信度(%)': list(confidence_scores.values())
            }).sort_values('置信度(%)', ascending=False)
            
            fig = px.bar(
                confidence_df,
                x='置信度(%)',
                y='指标',
                orientation='h',
                color='置信度(%)',
                color_continuous_scale='RdYlGn',
                title="各指标数据置信度"
            )
            st.plotly_chart(fig, use_container_width=True)


def show_roi_analysis(campaign_df, roi_calculator, attribution_model, conversion_analyzer):
    st.header("💰 ROI与归因分析")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        avg_roi = campaign_df['roi'].mean()
        st.metric("平均ROI", f"{avg_roi:.1f}%")
    
    with col2:
        avg_roas = campaign_df['roas'].mean()
        st.metric("平均ROAS", f"{avg_roas:.2f}x")
    
    with col3:
        avg_cpa = campaign_df['cpa'].mean()
        st.metric("平均CPA", f"¥{avg_cpa:.0f}")
    
    with col4:
        avg_cvr = campaign_df['conversion_rate'].mean()
        st.metric("平均转化率", f"{avg_cvr:.2f}%")
    
    st.markdown("---")
    
    tab1, tab2, tab3 = st.tabs(["ROI分析", "转化漏斗", "归因模型"])
    
    with tab1:
        st.subheader("ROI深度分析")
        
        col_left, col_right = st.columns(2)
        
        with col_left:
            platform_roi = campaign_df.groupby('platform')['roi'].mean().sort_values(ascending=False)
            fig = px.bar(
                x=platform_roi.index,
                y=platform_roi.values,
                title="各平台平均ROI",
                color=platform_roi.values,
                color_continuous_scale='RdYlGn'
            )
            st.plotly_chart(fig, use_container_width=True)
        
        with col_right:
            category_roi = campaign_df.groupby('category')['roi'].mean().sort_values(ascending=False)
            fig = px.bar(
                x=category_roi.index,
                y=category_roi.values,
                title="各类目平均ROI",
                color=category_roi.values,
                color_continuous_scale='Viridis'
            )
            st.plotly_chart(fig, use_container_width=True)
        
        st.subheader("ROI最高的网红TOP10")
        influencer_roi = roi_calculator.calculate_influencer_roi(campaign_df)
        top_roi = influencer_roi.sort_values('overall_roi', ascending=False).head(10)
        
        display_roi = top_roi[[
            'influencer_name', 'campaign_count', 'actual_cost', 'revenue',
            'profit', 'overall_roi', 'roas'
        ]].copy()
        display_roi.columns = ['网红名称', '合作次数', '总投入', '总收入', '总利润', 'ROI(%)', 'ROAS']
        st.dataframe(display_roi, use_container_width=True, hide_index=True)
    
    with tab2:
        st.subheader("转化漏斗分析")
        
        funnel = conversion_analyzer.analyze_conversion_funnel(campaign_df)
        
        fig = go.Figure(go.Funnel(
            y=['曝光', '点击', '转化'],
            x=[funnel['impressions'], funnel['clicks'], funnel['conversions']],
            textinfo="value+percent initial",
            marker={"color": ["#636EFA", "#00CC96", "#AB63FA"]}
        ))
        
        fig.update_layout(title="整体转化漏斗")
        st.plotly_chart(fig, use_container_width=True)
        
        col5, col6, col7 = st.columns(3)
        col5.metric("点击率(CTR)", f"{funnel['ctr']:.2f}%")
        col6.metric("转化率(CVR)", f"{funnel['conversion_rate']:.2f}%")
        col7.metric("曝光到转化", f"{funnel['impression_to_conversion']:.3f}%")
    
    with tab3:
        st.subheader("多触点归因分析")
        
        st.markdown("""
        归因模型说明：
        - **首次触点**: 100% 转化归功于第一次互动
        - **末次触点**: 100% 转化归功于最后一次互动
        - **线性归因**: 平均分配转化功劳
        - **时间衰减**: 越接近转化的触点权重越高
        - **U型归因**: 首次和末次各占40%，中间触点平分20%
        """)
        
        sample_touchpoints = [
            {'influencer_id': 'INF0001', 'timestamp': 1, 'type': 'view'},
            {'influencer_id': 'INF0003', 'timestamp': 2, 'type': 'click'},
            {'influencer_id': 'INF0007', 'timestamp': 3, 'type': 'click'},
            {'influencer_id': 'INF0005', 'timestamp': 4, 'type': 'conversion'}
        ]
        
        comparison = attribution_model.compare_attribution_models(sample_touchpoints)
        
        fig = px.bar(
            comparison,
            x='model',
            y='attribution_weight',
            color='influencer_id',
            title="不同归因模型的转化权重分配",
            barmode='stack'
        )
        st.plotly_chart(fig, use_container_width=True)


def show_budget_optimization(influencer_df, campaign_df, budget_optimizer, performance_forecaster, audience_overlap_optimizer, demo_df):
    st.header("📈 预算分配优化")
    
    tab_budget, tab_deduplication = st.tabs(["💰 预算分配", "🔄 去重优化"])
    
    with tab_budget:
        st.subheader("设置预算参数")
        
        col1, col2 = st.columns(2)
        
        with col1:
            total_budget = st.number_input(
                "总预算(元)",
                min_value=10000,
                max_value=10000000,
                value=100000,
                step=10000,
                key="total_budget_main"
            )
        
        with col2:
            risk_tolerance = st.select_slider(
                "风险偏好",
                options=['conservative', 'moderate', 'aggressive'],
                value='moderate',
                format_func=lambda x: {
                    'conservative': '保守（稳健型）',
                    'moderate': '中等（平衡型）',
                    'aggressive': '激进（增长型）'
                }[x],
                key="risk_tolerance_main"
            )
        
        st.markdown("#### 平台权重分配")
        col3, col4, col5, col6, col7 = st.columns(5)
        
        with col3:
            tiktok_weight = st.slider("TikTok", 0, 100, 30, key="tiktok_weight")
        with col4:
            xhs_weight = st.slider("小红书", 0, 100, 25, key="xhs_weight")
        with col5:
            weibo_weight = st.slider("微博", 0, 100, 20, key="weibo_weight")
        with col6:
            ig_weight = st.slider("Instagram", 0, 100, 15, key="ig_weight")
        with col7:
            yt_weight = st.slider("YouTube", 0, 100, 10, key="yt_weight")
        
        total_weight = tiktok_weight + xhs_weight + weibo_weight + ig_weight + yt_weight
        
        if total_weight != 100:
            st.warning(f"当前权重总和: {total_weight}%，建议调整为100%")
        
        platform_weights = {
            'TikTok': tiktok_weight / 100,
            'Xiaohongshu': xhs_weight / 100,
            'Weibo': weibo_weight / 100,
            'Instagram': ig_weight / 100,
            'YouTube': yt_weight / 100
        }
        
        if st.button("生成预算分配方案", type="primary", key="generate_budget_btn"):
            with st.spinner("正在优化预算分配..."):
                overall_result = budget_optimizer.optimize_budget(
                    influencer_df, total_budget, campaign_df, risk_tolerance=risk_tolerance
                )
                
                platform_result = budget_optimizer.optimize_by_platform(
                    influencer_df, total_budget, platform_weights
                )
                
                scenarios = budget_optimizer.generate_budget_scenarios(influencer_df, total_budget)
            
            st.markdown("---")
            st.subheader("🎯 优化结果概览")
            
            col8, col9, col10, col11 = st.columns(4)
            
            with col8:
                st.metric("分配网红数量", overall_result['number_of_influencers'])
            
            with col9:
                st.metric("预算使用率", f"{overall_result['budget_utilization']:.1f}%")
            
            with col10:
                st.metric("已分配预算", f"¥{overall_result['total_allocated']:,.0f}")
            
            with col11:
                st.metric("预期ROI", f"{overall_result['expected_roi']:.1f}%")
            
            st.markdown("---")
            st.subheader("📊 详细分配方案")
            
            allocation_df = pd.DataFrame(overall_result['allocation'])
            display_allocation = allocation_df[[
                'influencer_name', 'platform', 'category', 'followers',
                'influence_score', 'base_price', 'allocated_budget',
                'budget_percentage', 'expected_roi'
            ]].copy()
            display_allocation.columns = [
                '网红名称', '平台', '类目', '粉丝数', '影响力评分',
                '基础报价(元)', '分配预算(元)', '预算占比(%)', '预期ROI(%)'
            ]
            
            st.dataframe(display_allocation, use_container_width=True, hide_index=True)
            
            st.markdown("---")
            st.subheader("📈 平台分配情况")
            
            platform_summary = []
            for platform, data in platform_result.items():
                platform_summary.append({
                    '平台': platform,
                    '预算分配(元)': data['budget'],
                    '占比(%)': data['weight'],
                    '网红数量': len(data['influencers']),
                    '预期ROI(%)': data['expected_roi']
                })
            
            platform_df = pd.DataFrame(platform_summary)
            st.dataframe(platform_df, use_container_width=True, hide_index=True)
            
            fig = px.pie(
                platform_df,
                values='预算分配(元)',
                names='平台',
                title="预算平台分布"
            )
            st.plotly_chart(fig, use_container_width=True)
            
            st.markdown("---")
            st.subheader("🔮 效果预测")
            
            forecast = performance_forecaster.forecast_campaign_performance(
                influencer_df, overall_result['allocation']
            )
            
            col12, col13, col14, col15 = st.columns(4)
            
            with col12:
                st.metric("预期触达", f"{forecast['total_expected_reach']:,}")
            
            with col13:
                st.metric("预期互动", f"{forecast['total_expected_engagement']:,}")
            
            with col14:
                st.metric("预期转化", f"{forecast['total_expected_conversions']:,}")
            
            with col15:
                st.metric("整体ROI预测", f"{forecast['expected_roi']:.1f}%")
            
            st.markdown("---")
            st.subheader("📋 多情景对比")
            
            scenarios_comparison = []
            for scenario_name, scenario_data in scenarios.items():
                scenario_forecast = performance_forecaster.forecast_campaign_performance(
                    influencer_df, scenario_data['allocation']
                )
                scenarios_comparison.append({
                    '策略': {
                        'conservative': '保守策略(70%预算)',
                        'moderate': '中等策略(100%预算)',
                        'aggressive': '激进策略(150%预算)'
                    }[scenario_name],
                    '网红数量': scenario_data['number_of_influencers'],
                    '总预算(元)': scenario_data['total_allocated'],
                    '预期触达': scenario_forecast['total_expected_reach'],
                    '预期转化': scenario_forecast['total_expected_conversions'],
                    '预期ROI(%)': scenario_forecast['expected_roi']
                })
            
            scenarios_df = pd.DataFrame(scenarios_comparison)
            st.dataframe(scenarios_df, use_container_width=True, hide_index=True)
    
    with tab_deduplication:
        st.subheader("🔄 受众去重优化")
        
        st.markdown("""
        通过分析网红之间的受众重叠程度，避免同一用户被多个网红多次触达造成的预算浪费。
        """)
        
        col_d1, col_d2 = st.columns(2)
        
        with col_d1:
            dedup_budget = st.number_input(
                "总预算(元)",
                min_value=10000,
                max_value=10000000,
                value=100000,
                step=10000,
                key="dedup_budget"
            )
        
        with col_d2:
            max_influencers = st.slider(
                "最大网红数量",
                min_value=2,
                max_value=15,
                value=8,
                key="max_influencers_dedup"
            )
        
        top_influencers = influencer_df.sort_values('influence_score', ascending=False).head(max_influencers * 2)
        selected_for_dedup = st.multiselect(
            "选择要分析的网红（建议3-8位）",
            options=top_influencers['name'].tolist(),
            max_selections=max_influencers,
            default=top_influencers['name'].head(5).tolist()
        )
        
        if len(selected_for_dedup) >= 2:
            selected_inf_df = top_influencers[top_influencers['name'].isin(selected_for_dedup)]
            
            if st.button("进行去重优化分析", type="primary", key="dedup_analyze_btn"):
                with st.spinner("正在分析受众重叠并进行去重优化..."):
                    selected_ids = selected_inf_df['id'].tolist()
                    overlap_matrix = audience_overlap_optimizer.calculate_overlap_matrix(
                        influencer_df, selected_ids, demo_df
                    )
                    original_allocation = budget_optimizer.optimize_budget(
                        selected_inf_df, dedup_budget, campaign_df
                    )
                    optimized_result = audience_overlap_optimizer.optimize_allocation_with_deduplication(
                        selected_inf_df, dedup_budget, overlap_matrix, original_allocation
                    )
                
                st.markdown("---")
                st.subheader("📊 受众重叠矩阵")
                
                overlap_display = overlap_matrix.copy()
                overlap_display = overlap_display.set_index('网红名称')
                overlap_display = overlap_display.drop(columns=['网红ID'])
                
                st.dataframe(
                    overlap_display.style.background_gradient(cmap='YlOrRd', vmin=0, vmax=100)
                        .format(precision=1),
                    use_container_width=True
                )
                
                st.caption("数值越高表示两位网红的受众重叠越大（50%+黄色警告，70%+红色警告）")
                
                high_overlap_pairs = audience_overlap_optimizer.get_high_overlap_warnings(overlap_matrix)
                if high_overlap_pairs:
                    st.markdown("---")
                    st.subheader("⚠️ 高重叠组合警告")
                    for pair in high_overlap_pairs:
                        if pair['severity'] == '高':
                            st.error(f"【高度重叠 - {pair['overlap_percentage']}%】{pair['pair']} - {pair['recommendation']}")
                        else:
                            st.warning(f"【中度重叠 - {pair['overlap_percentage']}%】{pair['pair']} - {pair['recommendation']}")
                
                st.markdown("---")
                st.subheader("🎯 去重优化效果对比")
                
                col_o1, col_o2, col_o3, col_o4 = st.columns(4)
                
                with col_o1:
                    delta_reach = optimized_result['net_effect']['dedup_reach'] - optimized_result['net_effect']['original_reach']
                    st.metric(
                        "去重后有效触达",
                        f"{optimized_result['net_effect']['dedup_reach']:,}",
                        delta=f"{delta_reach:+,}" if delta_reach != 0 else "0"
                    )
                
                with col_o2:
                    waste_saved = optimized_result['net_effect']['budget_wasted']
                    st.metric(
                        "浪费预算节省",
                        f"¥{waste_saved:,.0f}"
                    )
                
                with col_o3:
                    roi_improvement = optimized_result['net_effect']['roi_improvement']
                    st.metric(
                        "ROI提升",
                        f"{roi_improvement:+.1f}%"
                    )
                
                with col_o4:
                    dedup_rate = optimized_result['net_effect']['dedup_rate']
                    st.metric(
                        "去重率",
                        f"{dedup_rate:.1f}%"
                    )
                
                st.markdown("---")
                st.subheader("📋 原始分配 vs 去重优化分配")
                
                comparison_df = pd.DataFrame(optimized_result['comparison'])
                comparison_display = comparison_df[[
                    'influencer_name', 'original_budget', 'optimized_budget',
                    'budget_change', 'overlap_adjustment_reason'
                ]].copy()
                comparison_display.columns = [
                    '网红名称', '原始预算(元)', '优化后预算(元)',
                    '预算变动(元)', '调整原因'
                ]
                
                st.dataframe(comparison_display, use_container_width=True, hide_index=True)
                
                fig = go.Figure()
                fig.add_trace(go.Bar(
                    x=comparison_df['influencer_name'],
                    y=comparison_df['original_budget'],
                    name='原始预算',
                    marker_color='lightcoral'
                ))
                fig.add_trace(go.Bar(
                    x=comparison_df['influencer_name'],
                    y=comparison_df['optimized_budget'],
                    name='优化后预算',
                    marker_color='lightgreen'
                ))
                fig.update_layout(
                    title='原始预算 vs 去重优化后预算对比',
                    barmode='group',
                    xaxis_title='网红名称',
                    yaxis_title='预算(元)'
                )
                st.plotly_chart(fig, use_container_width=True)
                
                st.markdown("---")
                st.subheader("📈 优化后详细分配方案")
                
                optimized_allocation = pd.DataFrame(optimized_result['optimized_allocation'])
                opt_display = optimized_allocation[[
                    'influencer_name', 'platform', 'category', 'followers',
                    'influence_score', 'allocated_budget', 'budget_percentage',
                    'audience_overlap_score', 'expected_roi'
                ]].copy()
                opt_display.columns = [
                    '网红名称', '平台', '类目', '粉丝数', '影响力评分',
                    '分配预算(元)', '预算占比(%)', '受众重叠度(%)', '预期ROI(%)'
                ]
                
                st.dataframe(opt_display, use_container_width=True, hide_index=True)
                
                st.markdown("---")
                st.subheader("🔮 去重后效果预测")
                
                dedup_forecast = performance_forecaster.forecast_campaign_performance(
                    influencer_df, optimized_result['optimized_allocation']
                )
                
                col_f1, col_f2, col_f3, col_f4 = st.columns(4)
                
                with col_f1:
                    st.metric("预期有效触达", f"{int(dedup_forecast['total_expected_reach'] * (1 - optimized_result['net_effect']['dedup_rate'] / 100)):,}")
                
                with col_f2:
                    st.metric("预期互动", f"{int(dedup_forecast['total_expected_engagement'] * 0.9):,}")
                
                with col_f3:
                    st.metric("预期转化", f"{int(dedup_forecast['total_expected_conversions'] * 0.9):,}")
                
                with col_f4:
                    final_roi = dedup_forecast['expected_roi'] + optimized_result['net_effect']['roi_improvement']
                    st.metric("调整后ROI预测", f"{final_roi:.1f}%")
                
                st.markdown("---")
                st.subheader("💡 去重优化建议")
                
                for rec in optimized_result['recommendations']:
                    if '高重叠' in rec or '警告' in rec:
                        st.warning(f"⚠️ {rec}")
                    elif '节省' in rec or '提升' in rec:
                        st.success(f"✅ {rec}")
                    else:
                        st.info(f"📌 {rec}")


def show_recommendations(influencer_df, recommendation_engine):
    st.header("💡 合作建议")
    
    top_influencers = influencer_df.sort_values('influence_score', ascending=False).head(20)
    
    selected_influencer = st.selectbox(
        "选择网红获取合作建议",
        options=top_influencers['name'].tolist()
    )
    
    if selected_influencer:
        influencer_data = top_influencers[top_influencers['name'] == selected_influencer].iloc[0]
        influencer_id = influencer_data['id']
        
        influencer_details = {
            'basic_info': {
                'id': influencer_data['id'],
                'name': influencer_data['name'],
                'platform': influencer_data['platform'],
                'category': influencer_data['category'],
                'followers': influencer_data['followers'],
                'city': influencer_data.get('city', '未知')
            },
            'influence_metrics': {
                'influence_score': influencer_data['influence_score'],
                'influence_tier': influencer_data['influence_tier'],
                'reach_score': influencer_data['reach_score'] * 100,
                'engagement_score': influencer_data['engagement_score'] * 100,
                'growth_score': influencer_data['growth_score'] * 100,
                'authenticity_score': influencer_data['authenticity_score'] * 100,
                'content_quality_score': influencer_data['content_quality_score'] * 100
            }
        }
        
        recommendations = recommendation_engine.generate_cooperation_recommendation(influencer_details)
        
        st.markdown("---")
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("🎯 合作优先级")
            priority = recommendations['cooperation_priority']
            if 'P0' in priority:
                st.error(priority)
            elif 'P1' in priority:
                st.warning(priority)
            else:
                st.info(priority)
            
            st.subheader("💼 推荐合作形式")
            for coop_type in recommendations['cooperation_type']:
                st.success(f"• {coop_type}")
            
            st.subheader("📝 内容建议")
            for content in recommendations['content_suggestions']:
                st.info(f"• {content}")
        
        with col2:
            st.subheader("💰 预算建议")
            budget_info = recommendations['recommended_budget']
            st.write(f"**推荐单次合作预算**: ¥{budget_info['recommended_single_budget']:,}")
            st.write(f"**合理预算区间**: ¥{budget_info['budget_range']}")
            st.write(f"**每千粉丝价格**: ¥{budget_info['price_per_1000_followers']:.2f}")
            
            st.subheader("📊 预期效果")
            outcomes = recommendations['expected_outcomes']
            col3, col4 = st.columns(2)
            col3.metric("预期浏览量", f"{outcomes['expected_views']:,}")
            col4.metric("预期互动量", f"{outcomes['expected_engagement']:,}")
            col3.metric("预期转化量", f"{outcomes['expected_conversions']:,}")
            col4.metric("置信度", outcomes['confidence_level'])
        
        st.markdown("---")
        st.subheader("⚠️ 风险评估")
        
        risk_info = recommendations['risk_assessment']
        risk_level = risk_info['overall_risk_level']
        
        if risk_level == '低':
            st.success(f"风险等级: {risk_level}")
        elif risk_level == '中':
            st.warning(f"风险等级: {risk_level}")
        else:
            st.error(f"风险等级: {risk_level}")
        
        col5, col6 = st.columns(2)
        
        with col5:
            st.markdown("**风险因素**")
            for risk in risk_info['risk_factors']:
                st.warning(f"• {risk}")
        
        with col6:
            st.markdown("**缓解建议**")
            for suggestion in risk_info['mitigation_suggestions']:
                st.info(f"• {suggestion}")
        
        st.markdown("---")
        st.subheader("🏆 推荐合作组合")
        
        st.markdown("#### 高性价比组合（预算 ¥50,000）")
        budget_influencers = influencer_df.copy()
        budget_influencers['value_score'] = budget_influencers['influence_score'] / budget_influencers['cooperation_price'] * 1000
        top_value = budget_influencers.sort_values('value_score', ascending=False).head(5)
        
        col7, col8, col9 = st.columns(3)
        col7.metric("网红数量", "5位")
        col8.metric("总预算", f"¥{top_value['cooperation_price'].sum():,.0f}")
        col9.metric("平均影响力评分", f"{top_value['influence_score'].mean():.1f}")
        
        combination_df = top_value[['name', 'platform', 'category', 'followers', 'influence_score', 'cooperation_price']].copy()
        combination_df.columns = ['网红名称', '平台', '类目', '粉丝数', '影响力评分', '合作价格(元)']
        st.dataframe(combination_df, use_container_width=True, hide_index=True)


def show_brand_safety(influencer_df, brand_safety_detector):
    st.header("🛡️ 品牌安全检测")
    
    tab_overview, tab_detail, tab_brand_fit = st.tabs(["📊 安全概览", "🔍 网红详情", "🎯 品牌适配"])
    
    with st.spinner("正在进行品牌安全检测..."):
        safety_df = brand_safety_detector.batch_analyze_safety(influencer_df)
    
    with tab_overview:
        st.subheader("品牌安全整体概览")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            safe_count = len(safety_df[safety_df['risk_level'].str.contains('A|B')])
            st.metric("安全/低风险网红", f"{safe_count}位", f"{safe_count/len(safety_df)*100:.1f}%")
        
        with col2:
            high_risk = len(safety_df[safety_df['risk_level'].str.contains('D|E')])
            st.metric("高风险网红", f"{high_risk}位", f"{high_risk/len(safety_df)*100:.1f}%")
        
        with col3:
            avg_risk = safety_df['overall_risk_score'].mean()
            st.metric("平均风险评分", f"{avg_risk:.1f}", f"{100-avg_risk:.1f}分安全度")
        
        with col4:
            high_risk_items = safety_df['high_risk_count'].sum()
            st.metric("高风险内容总数", f"{high_risk_items}项")
        
        st.markdown("---")
        st.subheader("风险等级分布")
        
        risk_dist = safety_df.groupby('risk_level').size().reset_index(name='数量')
        fig = px.pie(
            risk_dist,
            values='数量',
            names='risk_level',
            title="网红风险等级分布",
            color_discrete_map={
                'A - 安全': '#00CC96',
                'B - 低风险': '#636EFA',
                'C - 中等风险': '#FFA15A',
                'D - 高风险': '#EF553B',
                'E - 极高风险': '#AB63FA'
            }
        )
        st.plotly_chart(fig, use_container_width=True)
        
        st.markdown("---")
        st.subheader("网红安全排行榜")
        
        sort_by_risk = st.selectbox(
            "排序方式",
            options=['overall_risk_score', 'risk_category_count', 'high_risk_count'],
            index=0,
            format_func=lambda x: {
                'overall_risk_score': '综合风险评分',
                'risk_category_count': '风险类别数',
                'high_risk_count': '高风险内容数'
            }[x]
        )
        
        safety_display = safety_df.sort_values(sort_by_risk, ascending=True).reset_index(drop=True)
        safety_display['rank'] = safety_display.index + 1
        
        display_cols = safety_display[['rank', 'name', 'platform', 'category', 'overall_risk_score', 
                                       'risk_level', 'risk_category_count', 'high_risk_count']].copy()
        display_cols.columns = ['排名', '网红名称', '平台', '类目', '综合风险评分', '风险等级', '风险类别数', '高风险内容数']
        
        st.dataframe(display_cols, use_container_width=True, hide_index=True)
    
    with tab_detail:
        st.subheader("网红内容风险详情")
        
        selected_influencer = st.selectbox(
            "选择网红查看详细风险报告",
            options=safety_df['name'].tolist(),
            key="safety_detail_select"
        )
        
        if selected_influencer:
            influencer_id = safety_df[safety_df['name'] == selected_influencer]['id'].iloc[0]
            safety_report = brand_safety_detector.get_safety_report(influencer_df, influencer_id)
            
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                risk_level = safety_report['risk_summary']['risk_level']
                if 'A' in risk_level or 'B' in risk_level:
                    st.success(f"风险等级: {risk_level}")
                elif 'C' in risk_level:
                    st.warning(f"风险等级: {risk_level}")
                else:
                    st.error(f"风险等级: {risk_level}")
            
            with col2:
                st.metric("内容安全度", f"{safety_report['safety_score']:.1f}分")
            
            with col3:
                st.metric("检测风险项", f"{safety_report['risk_summary']['total_risk_items']}项")
            
            with col4:
                st.metric("高风险项", f"{safety_report['risk_summary']['high_risk_items']}项")
            
            st.markdown("---")
            st.subheader("风险类别详情")
            
            risk_details = safety_report['risk_details']
            risk_data = []
            for cat_key, cat_data in risk_details.items():
                cat_name = brand_safety_detector.risk_categories[cat_key]['name']
                risk_data.append({
                    '风险类别': cat_name,
                    '风险评分': cat_data['score'],
                    '严重程度': cat_data['severity'],
                    '匹配关键词': ', '.join(cat_data['matched_keywords'][:5])
                })
            
            risk_df = pd.DataFrame(risk_data)
            st.dataframe(risk_df, use_container_width=True, hide_index=True)
            
            fig = px.bar(
                risk_df,
                x='风险评分',
                y='风险类别',
                color='风险评分',
                color_continuous_scale='RdYlGn_r',
                orientation='h',
                title='各风险类别评分',
                range_x=[0, 100]
            )
            st.plotly_chart(fig, use_container_width=True)
            
            st.markdown("---")
            st.subheader("⚠️ 近期高风险内容")
            
            recent_risks = safety_report['recent_high_risk_content']
            if recent_risks:
                for risk in recent_risks:
                    with st.expander(f"📅 {risk['date']} - {risk['risk_category']} (浏览量: {risk['views']:,})"):
                        st.write(f"**平台**: {risk['platform']}")
                        st.write(f"**内容摘要**: {risk['content']}")
            else:
                st.success("✅ 近期未检测到高风险内容")
            
            st.markdown("---")
            st.subheader("💡 安全建议")
            
            for rec in safety_report['recommendations']:
                if '不建议' in rec or '高风险' in rec:
                    st.error(f"⚠️ {rec}")
                elif '谨慎' in rec:
                    st.warning(f"⚠️ {rec}")
                else:
                    st.info(f"💡 {rec}")
    
    with tab_brand_fit:
        st.subheader("品牌适配度评估")
        
        col1, col2 = st.columns(2)
        
        with col1:
            brand_category = st.selectbox(
                "选择品牌类目",
                options=['beauty', 'fashion', 'food', 'tech', 'fitness', 'travel', 'parenting', 'finance'],
                format_func=lambda x: {
                    'beauty': '美妆护肤',
                    'fashion': '时尚穿搭',
                    'food': '食品饮料',
                    'tech': '科技数码',
                    'fitness': '健身运动',
                    'travel': '旅游出行',
                    'parenting': '母婴育儿',
                    'finance': '金融理财'
                }[x]
            )
        
        with col2:
            top_n = st.slider("展示Top N网红", 5, 30, 10)
        
        if st.button("计算品牌适配度", type="primary"):
            with st.spinner("正在计算品牌适配度..."):
                fit_results = []
                for _, row in influencer_df.iterrows():
                    fit_score = brand_safety_detector.calculate_brand_fit_score(row, brand_category)
                    fit_results.append(fit_score)
                
                fit_df = pd.DataFrame(fit_results)
                fit_df = fit_df.sort_values('overall_brand_fit_score', ascending=False).head(top_n).reset_index(drop=True)
                fit_df['rank'] = fit_df.index + 1
                
                st.markdown("---")
                st.subheader(f"Top {top_n} 品牌适配网红")
                
                display_fit = fit_df[['rank', 'influencer_name', 'overall_brand_fit_score', 'fit_level',
                                      'category_match_score', 'safety_score', 'value_alignment_score']].copy()
                display_fit.columns = ['排名', '网红名称', '综合适配分', '适配等级', '类目匹配分', '内容安全分', '价值观契合分']
                
                st.dataframe(display_fit, use_container_width=True, hide_index=True)
                
                st.markdown("---")
                st.subheader("适配度分布")
                
                fit_dist = fit_df.groupby('fit_level').size().reset_index(name='数量')
                fig = px.bar(
                    fit_dist,
                    x='fit_level',
                    y='数量',
                    title='品牌适配等级分布',
                    color='fit_level',
                    color_discrete_map={
                        '完美匹配': '#00CC96',
                        '较好匹配': '#636EFA',
                        '一般匹配': '#FFA15A',
                        '匹配度低': '#EF553B'
                    }
                )
                st.plotly_chart(fig, use_container_width=True)


def show_competitor_analysis(influencer_df, competitor_analyzer):
    st.header("🏢 竞品投放分析")
    
    tab_overview, tab_competitor, tab_market, tab_overlap = st.tabs(
        ["📊 竞品概览", "🔍 单竞品详情", "🌐 市场情报", "🔄 网红重叠"]
    )
    
    competitor_list = list(competitor_analyzer.competitors.keys())
    competitor_names = {k: v['name'] for k, v in competitor_analyzer.competitors.items()}
    
    with tab_overview:
        st.subheader("竞品投放对比")
        
        selected_competitors = st.multiselect(
            "选择要对比的竞品",
            options=competitor_list,
            default=competitor_list[:3],
            format_func=lambda x: competitor_names[x]
        )
        
        if selected_competitors:
            with st.spinner("正在分析竞品投放数据..."):
                comparison_df = competitor_analyzer.compare_competitors(influencer_df, selected_competitors)
                
                st.dataframe(comparison_df, use_container_width=True, hide_index=True)
                
                st.markdown("---")
                st.subheader("投放花费对比")
                
                fig = px.bar(
                    comparison_df,
                    x='竞品名称',
                    y='预估总花费(元)',
                    color='竞品名称',
                    title='竞品预估总花费对比'
                )
                st.plotly_chart(fig, use_container_width=True)
                
                col1, col2 = st.columns(2)
                
                with col1:
                    fig = px.bar(
                        comparison_df,
                        x='竞品名称',
                        y='平均ROI(%)',
                        color='竞品名称',
                        title='竞品平均ROI对比'
                    )
                    st.plotly_chart(fig, use_container_width=True)
                
                with col2:
                    fig = px.bar(
                        comparison_df,
                        x='竞品名称',
                        y='投放网红数',
                        color='竞品名称',
                        title='竞品合作网红数量对比'
                    )
                    st.plotly_chart(fig, use_container_width=True)
    
    with tab_competitor:
        st.subheader("竞品投放详情分析")
        
        selected_competitor = st.selectbox(
            "选择竞品",
            options=competitor_list,
            format_func=lambda x: competitor_names[x],
            key="single_competitor_select"
        )
        
        if selected_competitor:
            with st.spinner("正在分析竞品投放策略..."):
                summary = competitor_analyzer.get_competitor_summary(influencer_df, selected_competitor)
                strategy = competitor_analyzer.analyze_competitor_strategy(influencer_df, selected_competitor)
                
                comp_info = summary['competitor_info']
                metrics = summary['summary_metrics']
                
                st.markdown("### 📋 竞品基本信息")
                col1, col2, col3, col4 = st.columns(4)
                col1.metric("竞品名称", comp_info['name'])
                col2.metric("所属类目", comp_info['category'])
                col3.metric("市场定位", comp_info['market_position'])
                col4.metric("月度预算估计", f"¥{comp_info['monthly_budget_estimate']:,}")
                
                st.markdown("---")
                st.markdown("### 📊 投放效果概览")
                col5, col6, col7, col8 = st.columns(4)
                col5.metric("总投放次数", metrics['total_campaigns'])
                col6.metric("合作网红数", metrics['unique_influencers'])
                col7.metric("预估总花费", f"¥{metrics['total_spent']:,}")
                col8.metric("平均ROI", f"{metrics['avg_roi']}%")
                
                col9, col10, col11 = st.columns(3)
                col9.metric("CPM(元/千次)", f"{metrics['cpm']:.2f}")
                col10.metric("CPE(元)", f"{metrics['cpe']:.2f}")
                col11.metric("预估总触达", f"{metrics['total_views']:,}")
                
                st.markdown("---")
                st.subheader("🎯 投放策略洞察")
                
                for insight in strategy['strategy_insights']:
                    st.info(f"💡 {insight}")
                
                st.markdown("---")
                st.subheader("📱 平台偏好分析")
                
                platform_df = pd.DataFrame(strategy['platform_preference'])
                fig = px.pie(
                    platform_df,
                    values='budget_percentage',
                    names='platform',
                    title='平台预算分配'
                )
                st.plotly_chart(fig, use_container_width=True)
                
                st.markdown("---")
                st.subheader("👥 网红层级策略")
                
                tier_df = pd.DataFrame(strategy['influencer_tier_strategy'])
                fig = px.bar(
                    tier_df,
                    x='网红层级',
                    y='总预算',
                    color='平均ROI',
                    title='各层级网红投放预算与ROI'
                )
                st.plotly_chart(fig, use_container_width=True)
                
                st.markdown("---")
                st.subheader("🏆 Top 10 合作网红")
                
                top_inf_df = pd.DataFrame(summary['top_influencers'])
                top_inf_display = top_inf_df[['influencer_name', 'estimated_budget', 'estimated_roi', 'campaign_id']].copy()
                top_inf_display.columns = ['网红名称', '合作总金额(元)', '平均ROI(%)', '合作次数']
                st.dataframe(top_inf_display, use_container_width=True, hide_index=True)
    
    with tab_market:
        st.subheader("整体市场情报")
        
        with st.spinner("正在收集市场情报..."):
            market_intel = competitor_analyzer.get_market_intelligence(influencer_df)
            market_summary = market_intel['market_summary']
            
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("监测竞品数", market_summary['total_competitors'])
            col2.metric("追踪投放活动", market_summary['total_campaigns_tracked'])
            col3.metric("市场总花费估计", f"¥{market_summary['total_market_spend']:,}")
            col4.metric("市场平均ROI", f"{market_summary['avg_market_roi']}%")
            
            st.metric("活跃网红总数", market_summary['active_influencers'])
            
            st.markdown("---")
            st.subheader("📱 平台市场份额")
            
            platform_share_df = pd.DataFrame(market_intel['platform_market_share'])
            fig = px.bar(
                platform_share_df,
                x='market_share',
                y='platform',
                orientation='h',
                title='各平台市场投放份额(%)',
                color='market_share',
                color_continuous_scale='Blues'
            )
            st.plotly_chart(fig, use_container_width=True)
            
            st.markdown("---")
            st.subheader("📈 竞品花费排行")
            
            category_df = pd.DataFrame(market_intel['category_breakdown'])
            fig = px.bar(
                category_df,
                x='competitor_name',
                y='estimated_budget',
                color='estimated_roi',
                title='竞品投放花费与ROI对比'
            )
            st.plotly_chart(fig, use_container_width=True)
            
            st.markdown("---")
            st.subheader("🔥 热门内容类型")
            
            trending_df = pd.DataFrame(market_intel['trending_content_types'])
            fig = px.scatter(
                trending_df,
                x='estimated_budget',
                y='estimated_roi',
                size='estimated_budget',
                color='campaign_type',
                title='内容类型投放分布 - 气泡大小代表花费',
                hover_data=['campaign_type', 'estimated_budget', 'estimated_roi']
            )
            st.plotly_chart(fig, use_container_width=True)
    
    with tab_overlap:
        st.subheader("网红重叠分析")
        
        col1, col2 = st.columns(2)
        
        with col1:
            my_top_n = st.slider("我方选择Top N网红", 10, 50, 20)
            my_influencers = influencer_df.sort_values('influence_score', ascending=False).head(my_top_n)['id'].tolist()
        
        with col2:
            overlap_competitor = st.selectbox(
                "选择对比竞品",
                options=competitor_list,
                format_func=lambda x: competitor_names[x],
                key="overlap_competitor_select"
            )
        
        if st.button("分析重叠情况", type="primary"):
            with st.spinner("正在分析网红重叠情况..."):
                overlap_result = competitor_analyzer.find_competitor_overlap(
                    my_influencers, influencer_df, overlap_competitor
                )
                
                col3, col4, col5 = st.columns(3)
                col3.metric("竞品使用网红数", overlap_result['total_influencers_used'])
                col4.metric("重叠网红数", overlap_result['overlap_count'])
                col5.metric("重叠占比", f"{overlap_result['overlap_percentage']}%")
                
                st.markdown("---")
                st.subheader("⚠️ 重叠网红详情")
                
                if len(overlap_result['overlap_influencers']) > 0:
                    overlap_display = overlap_result['overlap_influencers'].copy()
                    overlap_display = overlap_display[['name', 'platform', 'followers', 'competitor_campaign_count',
                                                       'total_spent_by_competitor', 'avg_roi_for_competitor',
                                                       'last_collaboration', 'risk_level']]
                    overlap_display.columns = ['网红名称', '平台', '粉丝数', '竞品合作次数',
                                               '竞品总花费(元)', '竞品平均ROI(%)', '最近合作时间', '竞争风险']
                    
                    st.dataframe(overlap_display, use_container_width=True, hide_index=True)
                    
                    st.markdown("---")
                    st.subheader("💡 建议")
                    for rec in overlap_result['recommendations']:
                        st.info(f"💡 {rec}")
                else:
                    st.success("✅ 未发现与竞品重叠的网红，网红池差异化较好")


def show_contract_management(influencer_df, contract_manager):
    st.header("📋 合约管理")
    
    @st.cache_data
    def load_contracts():
        return contract_manager.generate_sample_contracts(influencer_df, 20)
    
    contracts_df = load_contracts()
    summary = contract_manager.get_contract_summary(contracts_df)
    
    tab_overview, tab_list, tab_payment, tab_performance = st.tabs(
        ["📊 合约概览", "📋 合同列表", "💰 付款追踪", "📈 效果追踪"]
    )
    
    with tab_overview:
        st.subheader("合约整体概览")
        
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("合同总数", summary['total_contracts'])
        col2.metric("合同总金额", f"¥{summary['total_contract_value']:,}")
        col3.metric("已支付金额", f"¥{summary['total_paid_amount']:,}")
        col4.metric("待支付金额", f"¥{summary['total_pending_amount']:,}")
        
        col5, col6, col7 = st.columns(3)
        col5.metric("付款完成率", f"{summary['payment_completion_rate']}%")
        col6.metric("执行中合同", summary['active_contracts_count'])
        col7.metric("平均合同金额", f"¥{summary['avg_contract_value']:,.0f}")
        
        st.markdown("---")
        st.subheader("合同状态分布")
        
        status_df = pd.DataFrame(summary['status_breakdown'])
        fig = px.pie(
            status_df,
            values='合同金额',
            names='状态',
            title='合同金额分布（按状态）'
        )
        st.plotly_chart(fig, use_container_width=True)
        
        st.markdown("---")
        st.subheader("合同类型分布")
        
        type_df = pd.DataFrame(summary['type_breakdown'])
        fig = px.bar(
            type_df,
            x='合同类型',
            y='合同金额',
            color='合同数量',
            title='各类型合同金额与数量'
        )
        st.plotly_chart(fig, use_container_width=True)
        
        st.markdown("---")
        st.subheader("📆 月度支出预测")
        
        forecast_df = contract_manager.get_monthly_spending_forecast(contracts_df, 6)
        fig = px.bar(
            forecast_df,
            x='月份',
            y='预计支付金额',
            title='未来6个月预计支付金额',
            text='预计支付笔数'
        )
        st.plotly_chart(fig, use_container_width=True)
        
        aging_report = contract_manager.get_aging_report(contracts_df)
        if aging_report['total_overdue'] > 0:
            st.markdown("---")
            st.subheader("⚠️ 逾期付款预警")
            
            col8, col9 = st.columns(2)
            col8.metric("逾期总金额", f"¥{aging_report['total_overdue']:,}")
            col9.metric("逾期笔数", aging_report['overdue_count'])
            
            aging_df = pd.DataFrame([
                {'逾期区间': k, '金额(元)': v} 
                for k, v in aging_report['aging_buckets'].items()
            ])
            fig = px.bar(
                aging_df,
                x='逾期区间',
                y='金额(元)',
                title='逾期账龄分布',
                color='金额(元)',
                color_continuous_scale='Reds'
            )
            st.plotly_chart(fig, use_container_width=True)
    
    with tab_list:
        st.subheader("合同列表")
        
        status_filter = st.multiselect(
            "筛选合同状态",
            options=contracts_df['status'].unique().tolist(),
            default=[]
        )
        
        type_filter = st.multiselect(
            "筛选合同类型",
            options=contracts_df['contract_type'].unique().tolist(),
            default=[]
        )
        
        filtered_contracts = contracts_df.copy()
        if status_filter:
            filtered_contracts = filtered_contracts[filtered_contracts['status'].isin(status_filter)]
        if type_filter:
            filtered_contracts = filtered_contracts[filtered_contracts['contract_type'].isin(type_filter)]
        
        display_contracts = filtered_contracts[[
            'contract_id', 'influencer_name', 'platform', 'contract_type',
            'total_amount', 'status', 'start_date', 'end_date'
        ]].copy()
        display_contracts.columns = [
            '合同编号', '网红名称', '平台', '合同类型', '合同金额(元)', 
            '状态', '开始日期', '结束日期'
        ]
        
        st.dataframe(display_contracts, use_container_width=True, hide_index=True)
        
        st.markdown("---")
        st.subheader("合同详情")
        
        selected_contract_id = st.selectbox(
            "选择合同查看详情",
            options=contracts_df['contract_id'].tolist(),
            format_func=lambda x: f"{x} - {contracts_df[contracts_df['contract_id'] == x]['influencer_name'].iloc[0]}"
        )
        
        if selected_contract_id:
            contract = contracts_df[contracts_df['contract_id'] == selected_contract_id].iloc[0].to_dict()
            details = contract_manager.get_contract_details(contract, influencer_df)
            
            basic = details['basic_info']
            financial = details['financial_summary']
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("### 📄 基本信息")
                st.write(f"**合同编号**: {basic['contract_id']}")
                st.write(f"**合同类型**: {basic['contract_type']}")
                st.write(f"**合同状态**: {basic['status']}")
                st.write(f"**创建时间**: {basic['created_at']}")
                st.write(f"**签署时间**: {basic['signed_at'] or '未签署'}")
                st.write(f"**开始日期**: {basic['start_date']}")
                st.write(f"**结束日期**: {basic['end_date']}")
                st.write(f"**剩余天数**: {basic['days_remaining']}天")
                st.write(f"**合同期限**: {basic['duration_days']}天")
            
            with col2:
                st.markdown("### 💰 财务信息")
                st.write(f"**合同总额**: ¥{financial['total_amount']:,}")
                st.write(f"**已支付**: ¥{financial['paid_amount']:,}")
                st.write(f"**待支付**: ¥{financial['pending_amount']:,}")
                st.write(f"**付款进度**: {financial['payment_progress']}%")
                st.progress(financial['payment_progress'] / 100)
            
            st.markdown("---")
            st.subheader("📋 交付物要求")
            for i, deliverable in enumerate(details['deliverables'], 1):
                st.write(f"{i}. {deliverable}")
            
            st.markdown("---")
            st.subheader("📅 里程碑追踪")
            
            milestone_df = pd.DataFrame(details['milestones'])
            milestone_display = milestone_df[['name', 'date', 'status']].copy()
            milestone_display.columns = ['里程碑', '日期', '状态']
            
            def highlight_status(s):
                if s['状态'] == '已完成':
                    return ['background-color: #d4edda; color: #155724'] * len(s)
                elif s['状态'] == '进行中':
                    return ['background-color: #fff3cd; color: #856404'] * len(s)
                elif s['is_overdue']:
                    return ['background-color: #f8d7da; color: #721c24'] * len(s)
                else:
                    return [''] * len(s)
            
            st.dataframe(
                milestone_display.style.apply(highlight_status, axis=1),
                use_container_width=True,
                hide_index=True
            )
    
    with tab_payment:
        st.subheader("付款追踪")
        
        payment_df = contract_manager.get_payment_tracking(contracts_df)
        
        status_filter_pay = st.multiselect(
            "筛选付款状态",
            options=payment_df['status'].unique().tolist(),
            default=[],
            key="payment_status_filter"
        )
        
        filtered_payments = payment_df.copy()
        if status_filter_pay:
            filtered_payments = filtered_payments[filtered_payments['status'].isin(status_filter_pay)]
        
        display_payments = filtered_payments[[
            'payment_id', 'contract_id', 'influencer_name', 'payment_type',
            'amount', 'due_date', 'status', 'is_overdue'
        ]].copy()
        display_payments.columns = [
            '付款编号', '合同编号', '网红名称', '付款类型', 
            '金额(元)', '到期日', '状态', '是否逾期'
        ]
        
        st.dataframe(display_payments, use_container_width=True, hide_index=True)
        
        st.markdown("---")
        st.subheader("📊 付款状态统计")
        
        payment_status_df = payment_df.groupby('status').agg({
            'payment_id': 'count',
            'amount': 'sum'
        }).reset_index()
        payment_status_df.columns = ['状态', '笔数', '金额(元)']
        
        fig = px.pie(
            payment_status_df,
            values='金额(元)',
            names='状态',
            title='付款金额分布'
        )
        st.plotly_chart(fig, use_container_width=True)
    
    with tab_performance:
        st.subheader("KPI效果追踪")
        
        contract_for_perf = st.selectbox(
            "选择合同查看效果",
            options=contracts_df['contract_id'].tolist(),
            format_func=lambda x: f"{x} - {contracts_df[contracts_df['contract_id'] == x]['influencer_name'].iloc[0]}",
            key="performance_contract_select"
        )
        
        if contract_for_perf:
            contract = contracts_df[contracts_df['contract_id'] == contract_for_perf].iloc[0].to_dict()
            performance = contract_manager.track_performance(contract)
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("### 🎯 KPI目标")
                targets = performance['targets']
                st.write(f"**最低浏览量**: {targets['min_views']:,}")
                st.write(f"**最低互动率**: {targets['min_engagement_rate']}%")
                st.write(f"**最低转化量**: {targets['min_conversions']:,}")
            
            with col2:
                st.markdown("### 📊 实际数据")
                actual = performance['actual_data']
                st.write(f"**实际浏览量**: {actual['actual_views']:,}")
                st.write(f"**实际互动率**: {actual['actual_engagement_rate']}%")
                st.write(f"**实际转化量**: {actual['actual_conversions']:,}")
            
            st.markdown("---")
            st.subheader("📈 得分详情")
            
            scores = performance['scores']
            score_df = pd.DataFrame({
                '指标': ['浏览量', '互动率', '转化量', '综合得分'],
                '目标达成率(%)': [
                    scores['views_score'],
                    scores['engagement_score'],
                    scores['conversion_score'],
                    scores['overall_score']
                ]
            })
            
            fig = px.bar(
                score_df,
                x='目标达成率(%)',
                y='指标',
                orientation='h',
                title='KPI目标达成率',
                color='目标达成率(%)',
                color_continuous_scale='RdYlGn',
                range_x=[0, 150]
            )
            st.plotly_chart(fig, use_container_width=True)
            
            col3, col4, col5 = st.columns(3)
            
            with col3:
                perf_level = performance['performance_level']
                if 'S' in perf_level or 'A' in perf_level:
                    st.success(f"效果等级: {perf_level}")
                elif 'B' in perf_level:
                    st.info(f"效果等级: {perf_level}")
                elif 'C' in perf_level:
                    st.warning(f"效果等级: {perf_level}")
                else:
                    st.error(f"效果等级: {perf_level}")
            
            with col4:
                if performance['bonus_eligibility']:
                    st.success(f"奖金资格: 符合 (¥{performance['bonus_amount']:,.0f})")
                else:
                    st.warning("奖金资格: 不符合")
            
            with col5:
                if performance['kpi_met']:
                    st.success("KPI达标: ✅ 是")
                else:
                    st.error("KPI达标: ❌ 否")
            
            st.markdown("---")
            st.subheader("💡 效果建议")
            
            for rec in performance['recommendations']:
                if '远超预期' in rec or '优秀' in rec:
                    st.success(f"✅ {rec}")
                elif '未达预期' in rec or '暂停' in rec or '不达标' in rec:
                    st.error(f"⚠️ {rec}")
                else:
                    st.info(f"💡 {rec}")


if __name__ == "__main__":
    main()
