import streamlit as st
import pandas as pd
import numpy as np
import io
import base64
from data_generator import generate_sample_data, load_csv_data, validate_data, preprocess_data
from survival_analysis import ChurnSurvivalAnalyzer
from visualization import (
    plot_coefficients, plot_hazard_ratios, plot_kaplan_meier,
    plot_risk_distribution, plot_survival_curves, plot_risk_groups,
    plot_feature_importance, plot_heatmap, plot_bootstrap_survival,
    plot_schoenfeld_residuals, plot_intervention_simulation,
    plot_intervention_comparison, plot_warning_trend,
    plot_strategy_roi, plot_campaign_allocation
)
from user_segmentation import UserRiskSegmenter
from intervention_simulation import InterventionSimulator
from churn_early_warning import ChurnEarlyWarningSystem
from retention_strategy import RetentionStrategyEngine

st.set_page_config(
    page_title="用户流失归因分析平台",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.5rem;
    }
    .sub-header {
        color: #666;
        font-size: 1.1rem;
        margin-bottom: 2rem;
    }
    .section-title {
        font-size: 1.5rem;
        font-weight: bold;
        margin-top: 2rem;
        margin-bottom: 1rem;
        color: #333;
        border-left: 4px solid #667eea;
        padding-left: 10px;
    }
    .metric-card {
        background: white;
        padding: 1.5rem;
        border-radius: 10px;
        box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        margin-bottom: 1rem;
    }
    .metric-value {
        font-size: 2rem;
        font-weight: bold;
        color: #667eea;
    }
    .metric-label {
        color: #666;
        font-size: 0.9rem;
    }
    .insight-box {
        background: #f8f9fa;
        border-left: 4px solid #667eea;
        padding: 1rem;
        border-radius: 5px;
        margin: 1rem 0;
    }
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="main-header">📊 用户流失归因分析平台</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">基于生存分析模型(Cox回归)的用户流失风险识别与归因分析</div>', unsafe_allow_html=True)

def get_table_download_link(df, filename="churn_analysis_result.csv"):
    csv = df.to_csv(index=False, encoding='utf-8-sig')
    b64 = base64.b64encode(csv.encode('utf-8-sig')).decode()
    href = f'<a href="data:file/csv;base64,{b64}" download="{filename}">📥 下载分析结果</a>'
    return href

with st.sidebar:
    st.header("📁 数据源配置")
    
    data_source = st.radio(
        "选择数据源",
        ["使用示例数据", "上传CSV文件"],
        index=0
    )
    
    if data_source == "使用示例数据":
        n_users = st.slider("用户数量", min_value=500, max_value=5000, value=1000, step=100)
        if st.button("生成示例数据", type="primary"):
            with st.spinner("正在生成示例数据..."):
                st.session_state.df = generate_sample_data(n_users=n_users)
                st.success(f"已生成 {n_users} 条用户行为数据")
    else:
        uploaded_file = st.file_uploader("上传CSV文件", type=["csv"])
        if uploaded_file is not None:
            try:
                st.session_state.df = load_csv_data(uploaded_file)
                st.success(f"已加载 {len(st.session_state.df)} 条数据")
            except Exception as e:
                st.error(f"文件加载失败: {e}")
    
    if 'df' in st.session_state:
        st.markdown("---")
        st.header("⚙️ 模型配置")
        
        all_columns = st.session_state.df.columns.tolist()
        
        duration_col = st.selectbox(
            "生存时间列",
            options=all_columns,
            index=all_columns.index('tenure_days') if 'tenure_days' in all_columns else 0
        )
        
        event_col = st.selectbox(
            "事件列 (1=流失, 0=留存)",
            options=all_columns,
            index=all_columns.index('churned') if 'churned' in all_columns else 0
        )
        
        exclude_cols = st.multiselect(
            "排除列 (非特征列)",
            options=all_columns,
            default=['user_id'] if 'user_id' in all_columns else []
        )
        
        standardize = st.checkbox("标准化特征", value=True)
        
        with st.expander("🔬 PH假设检验与分层", expanded=False):
            check_ph = st.checkbox("运行Schoenfeld残差检验", value=True)
            ph_p_threshold = st.slider("P值阈值", min_value=0.01, max_value=0.10, value=0.05, step=0.01)
            auto_stratify = st.checkbox("自动对违反PH假设的特征分层", value=False)
            manual_strata_cols = st.multiselect(
                "手动选择分层特征",
                options=[c for c in all_columns if c not in exclude_cols + [duration_col, event_col]],
                default=[]
            )
        
        with st.expander("📊 Bootstrap配置", expanded=False):
            enable_bootstrap = st.checkbox("启用Bootstrap置信区间", value=True)
            n_bootstrap = st.slider("Bootstrap迭代次数", min_value=50, max_value=500, value=100, step=10)
        
        with st.expander("👥 用户分群配置", expanded=False):
            segment_method = st.selectbox(
                "分群方法",
                options=['kmeans', 'quantile', 'custom'],
                index=0,
                format_func=lambda x: {
                    'kmeans': 'K-means聚类',
                    'quantile': '按百分位数',
                    'custom': '自定义阈值'
                }[x]
            )
            
            n_groups = st.selectbox("分群数量", options=[2, 3], index=1)
            
            if segment_method == 'quantile':
                if n_groups == 3:
                    q1 = st.slider("中/高风险分位数", min_value=0.2, max_value=0.5, value=0.33, step=0.01)
                    q2 = st.slider("低/中风险分位数", min_value=0.5, max_value=0.8, value=0.66, step=0.01)
                    custom_quantiles = [q1, q2]
                else:
                    q1 = st.slider("高/低风险分位数", min_value=0.3, max_value=0.7, value=0.5, step=0.01)
                    custom_quantiles = [q1]
            elif segment_method == 'custom':
                if n_groups == 3:
                    medium_thresh = st.number_input("中/高风险阈值", value=0.5)
                    low_thresh = st.number_input("低/中风险阈值", value=1.0)
                    custom_thresholds = {'medium': medium_thresh, 'low': low_thresh}
                else:
                    high_low_thresh = st.number_input("高/低风险阈值", value=0.8)
                    custom_thresholds = {'low': high_low_thresh}
        
        if st.button("运行Cox回归分析", type="primary"):
            with st.spinner("正在训练生存分析模型..."):
                try:
                    errors = validate_data(st.session_state.df, duration_col, event_col)
                    if errors:
                        for error in errors:
                            st.error(error)
                    else:
                        df_clean, feature_cols = preprocess_data(
                            st.session_state.df, duration_col, event_col, exclude_cols
                        )
                        
                        analyzer = ChurnSurvivalAnalyzer()
                        
                        strata_cols = manual_strata_cols if manual_strata_cols else None
                        
                        if strata_cols:
                            analyzer.fit_stratified_cox_model(
                                df_clean, duration_col, event_col, feature_cols, 
                                strata_cols=strata_cols, standardize=standardize
                            )
                        else:
                            analyzer.fit_cox_model(
                                df_clean, duration_col, event_col, feature_cols, standardize
                            )
                        
                        ph_test_df = None
                        if check_ph:
                            with st.spinner("正在进行Schoenfeld残差检验..."):
                                ph_test_df = analyzer.check_proportional_hazards(p_threshold=ph_p_threshold)
                                
                                if auto_stratify and analyzer.violated_features:
                                    st.info(f"检测到{len(analyzer.violated_features)}个特征违反PH假设，正在重新训练分层模型...")
                                    analyzer.fit_stratified_cox_model(
                                        df_clean, duration_col, event_col, feature_cols,
                                        strata_cols=analyzer.violated_features, standardize=standardize
                                    )
                        
                        st.session_state.analyzer = analyzer
                        st.session_state.feature_cols = feature_cols
                        st.session_state.df_clean = df_clean
                        st.session_state.ph_test_df = ph_test_df
                        
                        risk_scores = analyzer.predict_risk_scores(df_clean)
                        surv_funcs = analyzer.predict_survival_function(df_clean)
                        
                        churn_30d = 1 - surv_funcs.iloc[min(29, len(surv_funcs)-1)].values
                        churn_90d = 1 - surv_funcs.iloc[min(89, len(surv_funcs)-1)].values
                        
                        if enable_bootstrap:
                            with st.spinner(f"正在进行{n_bootstrap}次Bootstrap..."):
                                bootstrap_df, bootstrap_matrix = analyzer.bootstrap_survival_curves(
                                    n_bootstrap=n_bootstrap
                                )
                                st.session_state.bootstrap_df = bootstrap_df
                                st.session_state.bootstrap_matrix = bootstrap_matrix
                        else:
                            st.session_state.bootstrap_df = None
                            st.session_state.bootstrap_matrix = None
                        
                        if segment_method == 'kmeans':
                            segmenter = UserRiskSegmenter(n_groups=n_groups, method='kmeans')
                        elif segment_method == 'quantile':
                            segmenter = UserRiskSegmenter(
                                n_groups=n_groups, 
                                method='quantile', 
                                quantiles=custom_quantiles
                            )
                        else:
                            segmenter = UserRiskSegmenter(
                                n_groups=n_groups, 
                                method='custom', 
                                thresholds=custom_thresholds
                            )
                        
                        segmented_df = segmenter.get_user_segments(
                            st.session_state.df, risk_scores, churn_30d, churn_90d
                        )
                        
                        st.session_state.segmented_df = segmented_df
                        st.session_state.segmenter = segmenter
                        st.session_state.risk_scores = risk_scores
                        st.session_state.surv_funcs = surv_funcs
                        st.session_state.segment_method = segment_method
                        
                        simulator = InterventionSimulator(analyzer, df_clean, feature_cols)
                        warning_system = ChurnEarlyWarningSystem(segmented_df, feature_cols, coef_df)
                        strategy_engine = RetentionStrategyEngine(segmented_df, feature_cols, coef_df)
                        
                        st.session_state.simulator = simulator
                        st.session_state.warning_system = warning_system
                        st.session_state.strategy_engine = strategy_engine
                        
                        success_msg = "模型训练完成！"
                        if ph_test_df is not None:
                            n_violated = len(analyzer.violated_features)
                            if n_violated > 0:
                                success_msg += f" 检测到{n_violated}个特征违反PH假设。"
                            else:
                                success_msg += " 所有特征均满足PH假设。"
                        st.success(success_msg)
                except Exception as e:
                    st.error(f"模型训练失败: {e}")
                    import traceback
                    st.code(traceback.format_exc())

if 'df' in st.session_state:
    st.markdown('<div class="section-title">📋 数据概览</div>', unsafe_allow_html=True)
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value">{len(st.session_state.df)}</div>
            <div class="metric-label">总用户数</div>
        </div>
        """, unsafe_allow_html=True)
    with col2:
        churn_rate = st.session_state.df['churned'].mean() if 'churned' in st.session_state.df.columns else 0
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value">{churn_rate:.1%}</div>
            <div class="metric-label">流失率</div>
        </div>
        """, unsafe_allow_html=True)
    with col3:
        avg_tenure = st.session_state.df['tenure_days'].mean() if 'tenure_days' in st.session_state.df.columns else 0
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value">{avg_tenure:.1f}</div>
            <div class="metric-label">平均生存期 (天)</div>
        </div>
        """, unsafe_allow_html=True)
    with col4:
        n_features = len([c for c in st.session_state.df.columns if c not in ['user_id', 'tenure_days', 'churned']])
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value">{n_features}</div>
            <div class="metric-label">特征数量</div>
        </div>
        """, unsafe_allow_html=True)
    
    with st.expander("查看原始数据", expanded=False):
        st.dataframe(st.session_state.df.head(100), use_container_width=True)

if 'analyzer' in st.session_state:
    analyzer = st.session_state.analyzer
    feature_cols = st.session_state.feature_cols
    
    st.markdown('<div class="section-title">📈 模型评估</div>', unsafe_allow_html=True)
    
    summary = analyzer.get_model_summary()
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("观察样本数", f"{summary['n_observations']}")
    with col2:
        st.metric("事件数 (流失)", f"{summary['n_events']}")
    with col3:
        st.metric("删失率", f"{summary['censoring_rate']:.1%}")
    with col4:
        st.metric("C-Index", f"{summary['concordance_index']:.3f}")
    
    coef_df = analyzer.get_coefficients()
    
    tab1, tab2, tab3 = st.tabs(["特征系数", "风险比", "特征重要性"])
    
    with tab1:
        fig_coef = plot_coefficients(coef_df, top_n=15)
        st.plotly_chart(fig_coef, use_container_width=True)
        
        with st.expander("查看详细系数表", expanded=False):
            display_df = coef_df.copy()
            display_df['coef'] = display_df['coef'].round(4)
            display_df['hazard_ratio'] = display_df['hazard_ratio'].round(4)
            display_df['p_value'] = display_df['p_value'].apply(lambda x: f"{x:.4f}")
            display_df['ci_lower'] = display_df['ci_lower'].round(4)
            display_df['ci_upper'] = display_df['ci_upper'].round(4)
            display_df['se'] = display_df['se'].round(4)
            display_df = display_df.rename(columns={
                'feature': '特征',
                'coef': '系数',
                'hazard_ratio': '风险比(HR)',
                'p_value': 'P值',
                'ci_lower': '95%CI下限',
                'ci_upper': '95%CI上限',
                'se': '标准误',
                'significance': '显著性'
            })
            st.dataframe(display_df, use_container_width=True)
    
    with tab2:
        fig_hr = plot_hazard_ratios(coef_df, top_n=15)
        st.plotly_chart(fig_hr, use_container_width=True)
    
    with tab3:
        importance_df = analyzer.feature_importance()
        fig_imp = plot_feature_importance(importance_df, top_n=10)
        st.plotly_chart(fig_imp, use_container_width=True)
    
    st.markdown('<div class="insight-box">💡 <strong>解读说明:</strong> 风险比 HR > 1 表示该特征是风险因素（增加流失风险），HR < 1 表示是保护因素（降低流失风险）。P值 < 0.05 表示统计显著。</div>', unsafe_allow_html=True)
    
    if st.session_state.ph_test_df is not None:
        st.markdown('<div class="section-title">� 比例风险假设检验 (Schoenfeld残差)</div>', unsafe_allow_html=True)
        
        ph_test_df = st.session_state.ph_test_df
        violated_features = analyzer.violated_features
        
        col1, col2 = st.columns([3, 1])
        
        with col1:
            fig_ph = plot_schoenfeld_residuals(ph_test_df, violated_features)
            st.plotly_chart(fig_ph, use_container_width=True)
        
        with col2:
            n_total = len(ph_test_df)
            n_violated = len(violated_features)
            n_satisfied = n_total - n_violated
            
            st.metric("检验特征总数", f"{n_total}")
            st.metric("满足PH假设", f"{n_satisfied}", delta_color="normal")
            st.metric("违反PH假设", f"{n_violated}", delta_color="inverse")
            
            if violated_features:
                st.warning(f"⚠️ 以下特征违反比例风险假设: {', '.join(violated_features)}")
                if analyzer.strata_cols:
                    st.success(f"✅ 已对这些特征进行分层处理")
                else:
                    st.info("💡 建议对这些特征进行分层或使用时依协变量模型")
            else:
                st.success("✅ 所有特征均满足比例风险假设")
        
        with st.expander("查看详细检验结果", expanded=False):
            display_ph_df = ph_test_df.copy()
            display_ph_df['p'] = display_ph_df['p'].apply(lambda x: f"{x:.4f}")
            display_ph_df['test_statistic'] = display_ph_df['test_statistic'].round(4)
            display_ph_df = display_ph_df.rename(columns={
                'feature': '特征',
                'test_statistic': '检验统计量',
                'p': 'P值',
                'satisfies_ph': '满足PH假设'
            })
            st.dataframe(display_ph_df, use_container_width=True)
    
    st.markdown('<div class="section-title">� 生存曲线分析</div>', unsafe_allow_html=True)
    
    if st.session_state.bootstrap_df is not None:
        tab1, tab2 = st.tabs(["Bootstrap置信区间", "标准KM曲线"])
        
        with tab1:
            col1, col2 = st.columns([3, 1])
            
            with col1:
                n_curves = st.slider("显示Bootstrap样本曲线数", min_value=0, max_value=50, value=20)
                fig_boot = plot_bootstrap_survival(
                    st.session_state.bootstrap_df, 
                    st.session_state.bootstrap_matrix,
                    n_curves_to_show=n_curves
                )
                st.plotly_chart(fig_boot, use_container_width=True)
            
            with col2:
                boot_df = st.session_state.bootstrap_df
                median_time_idx = (boot_df['median_survival'] <= 0.5).idxmax()
                median_time = boot_df.loc[median_time_idx, 'time'] if median_time_idx > 0 else None
                
                st.metric("中位生存期", f"{median_time:.1f}天" if median_time else ">180天")
                st.metric("90天留存率(均值)", f"{boot_df.iloc[min(89, len(boot_df)-1)]['mean_survival']:.1%}")
                st.metric("90天留存率(95%CI下限)", f"{boot_df.iloc[min(89, len(boot_df)-1)]['ci_lower']:.1%}")
                st.metric("90天留存率(95%CI上限)", f"{boot_df.iloc[min(89, len(boot_df)-1)]['ci_upper']:.1%}")
                
                st.info("📊 Bootstrap方法通过重抽样估计生存曲线的不确定性，阴影区域为95%置信区间")
        
        with tab2:
            col1, col2 = st.columns(2)
            
            with col1:
                kmf = analyzer.get_kaplan_meier_curve()
                fig_km = plot_kaplan_meier(kmf)
                st.plotly_chart(fig_km, use_container_width=True)
            
            with col2:
                fig_risk_dist = plot_risk_distribution(st.session_state.risk_scores, bins=30)
                st.plotly_chart(fig_risk_dist, use_container_width=True)
    else:
        col1, col2 = st.columns(2)
        
        with col1:
            kmf = analyzer.get_kaplan_meier_curve()
            fig_km = plot_kaplan_meier(kmf)
            st.plotly_chart(fig_km, use_container_width=True)
        
        with col2:
            fig_risk_dist = plot_risk_distribution(st.session_state.risk_scores, bins=30)
            st.plotly_chart(fig_risk_dist, use_container_width=True)
    
    st.markdown("### 个体用户生存曲线")
    n_users_to_plot = st.slider("显示用户数量", min_value=1, max_value=20, value=5)
    fig_surv = plot_survival_curves(
        st.session_state.surv_funcs, 
        user_indices=st.session_state.surv_funcs.columns[:n_users_to_plot]
    )
    st.plotly_chart(fig_surv, use_container_width=True)
    
    st.markdown('<div class="section-title">👥 用户风险分群</div>', unsafe_allow_html=True)
    
    segmented_df = st.session_state.segmented_df
    segmenter = st.session_state.segmenter
    
    threshold_info = segmenter.get_threshold_info()
    
    method_names = {
        'kmeans': 'K-means聚类',
        'quantile': '百分位数',
        'custom': '自定义阈值'
    }
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.info(f"📊 分群方法: {method_names.get(threshold_info['method'], threshold_info['method'])}")
    with col2:
        st.info(f"👥 分群数量: {threshold_info['n_groups']}组")
    with col3:
        if threshold_info.get('thresholds'):
            thresh = threshold_info['thresholds']
            if threshold_info['n_groups'] == 3:
                st.info(f"📏 阈值: 高<{thresh.get('medium', 'N/A'):.2f} ≤中<{thresh.get('low', 'N/A'):.2f} ≤低")
            else:
                st.info(f"📏 阈值: 高<{thresh.get('low', 'N/A'):.2f} ≤低")
    
    fig_groups = plot_risk_groups(segmented_df)
    st.plotly_chart(fig_groups, use_container_width=True)
    
    group_features = segmenter.get_top_features_by_group(
        segmented_df, feature_cols, coef_df, top_n=5
    )
    insights = segmenter.generate_segment_insights(group_features, coef_df)
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("### 🔴 高风险用户")
        high_risk_count = (segmented_df['risk_group'] == '高风险').sum()
        high_risk_pct = high_risk_count / len(segmented_df) * 100
        st.metric("用户数", f"{high_risk_count} ({high_risk_pct:.1f}%)")
        high_risk_churn = segmented_df[segmented_df['risk_group'] == '高风险']['churn_prob_30d'].mean()
        st.metric("30天平均流失概率", f"{high_risk_churn:.1%}")
        st.info(insights.get('高风险', '暂无分析'))
    
    with col2:
        st.markdown("### 🟡 中风险用户")
        med_risk_count = (segmented_df['risk_group'] == '中风险').sum()
        med_risk_pct = med_risk_count / len(segmented_df) * 100
        st.metric("用户数", f"{med_risk_count} ({med_risk_pct:.1f}%)")
        med_risk_churn = segmented_df[segmented_df['risk_group'] == '中风险']['churn_prob_30d'].mean()
        st.metric("30天平均流失概率", f"{med_risk_churn:.1%}")
        st.info(insights.get('中风险', '暂无分析'))
    
    with col3:
        st.markdown("### 🟢 低风险用户")
        low_risk_count = (segmented_df['risk_group'] == '低风险').sum()
        low_risk_pct = low_risk_count / len(segmented_df) * 100
        st.metric("用户数", f"{low_risk_count} ({low_risk_pct:.1f}%)")
        low_risk_churn = segmented_df[segmented_df['risk_group'] == '低风险']['churn_prob_30d'].mean()
        st.metric("30天平均流失概率", f"{low_risk_churn:.1%}")
        st.info(insights.get('低风险', '暂无分析'))
    
    st.markdown('<div class="section-title">🔍 特征相关性</div>', unsafe_allow_html=True)
    fig_heatmap = plot_heatmap(st.session_state.df_clean, feature_cols, max_features=10)
    st.plotly_chart(fig_heatmap, use_container_width=True)
    
    st.markdown('<div class="section-title">🎯 干预措施模拟</div>', unsafe_allow_html=True)
    
    simulator = st.session_state.simulator
    coef_df = analyzer.get_coefficients()
    
    tab1, tab2 = st.tabs(["单用户模拟", "最优干预推荐"])
    
    with tab1:
        col1, col2, col3 = st.columns(3)
        
        with col1:
            high_risk_users = segmented_df[segmented_df['risk_group'] == '高风险']['user_id'].tolist()
            if 'user_id' in segmented_df.columns:
                user_options = segmented_df['user_id'].tolist()
                default_idx = user_options.index(high_risk_users[0]) if high_risk_users else 0
                selected_user = st.selectbox("选择用户", options=user_options, index=default_idx)
                user_idx = segmented_df[segmented_df['user_id'] == selected_user].index[0]
            else:
                user_idx = st.selectbox("选择用户索引", options=range(len(segmented_df)))
                selected_user = f"user_{user_idx}"
        
        with col2:
            intervention_feature = st.selectbox(
                "选择干预特征",
                options=feature_cols,
                format_func=lambda x: f"{x} (HR={coef_df[coef_df['feature']==x]['hazard_ratio'].values[0]:.2f})"
            )
        
        with col3:
            intervention_type = st.selectbox(
                "调整方式",
                options=['absolute', 'percentage', 'set_value'],
                format_func=lambda x: {'absolute': '绝对值调整', 'percentage': '百分比调整', 'set_value': '设定为目标值'}[x]
            )
        
        feature_stats = simulator.feature_stats[intervention_feature]
        col1, col2 = st.columns(2)
        with col1:
            st.info(f"特征范围: [{feature_stats['min']:.2f}, {feature_stats['max']:.2f}] | 均值: {feature_stats['mean']:.2f}")
        with col2:
            current_val = segmented_df.loc[user_idx, intervention_feature]
            st.info(f"用户当前值: {current_val:.2f}")
        
        if intervention_type == 'absolute':
            adjustment = st.slider(
                "调整量",
                min_value=feature_stats['min'] - current_val,
                max_value=feature_stats['max'] - current_val,
                value=0.0,
                step=0.1
            )
        elif intervention_type == 'percentage':
            adjustment = st.slider(
                "调整百分比 (%)",
                min_value=-50.0,
                max_value=100.0,
                value=0.0,
                step=1.0
            )
        else:
            adjustment = st.slider(
                "目标值",
                min_value=feature_stats['min'],
                max_value=feature_stats['max'],
                value=feature_stats['mean'],
                step=0.1
            )
        
        if st.button("运行干预模拟", type="primary"):
            with st.spinner("正在模拟干预效果..."):
                result = simulator.simulate_intervention(
                    user_idx, intervention_feature, adjustment, intervention_type
                )
                
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    delta_churn = result['churn_reduction_30d'] * 100
                    st.metric("30天流失率变化", f"{result['modified_churn_30d']:.1%}", delta=f"-{delta_churn:.1f}%", delta_color="normal")
                with col2:
                    delta_risk = result['risk_change_pct']
                    st.metric("风险评分变化", f"{result['modified_risk_score']:.2f}", delta=f"{delta_risk:.1f}%", delta_color="inverse")
                with col3:
                    st.metric("原值 → 目标值", f"{result['original_value']:.2f} → {result['modified_value']:.2f}")
                with col4:
                    saved = result['churn_reduction_30d'] * 100
                    st.metric("预期挽留用户", f"{saved:.1f}%")
                
                fig_interv = plot_intervention_simulation(result)
                st.plotly_chart(fig_interv, use_container_width=True)
    
    with tab2:
        if st.button("为该用户生成最优干预方案", type="primary"):
            with st.spinner("正在分析最优干预方案..."):
                optimal_options = simulator.find_optimal_intervention(user_idx, coef_df)
                
                if not optimal_options.empty:
                    col1, col2 = st.columns([2, 1])
                    
                    with col1:
                        fig_optimal = plot_intervention_comparison(optimal_options, top_n=5)
                        st.plotly_chart(fig_optimal, use_container_width=True)
                    
                    with col2:
                        st.markdown("### 📊 干预效果预估")
                        for _, row in optimal_options.head(3).iterrows():
                            st.info(f"""
                            **{row['feature']}**
                            - 类型: {row['intervention_type']}
                            - 调整: {row['current_value']:.2f} → {row['target_value']:.2f}
                            - 30天流失率降低: {row['churn_reduction_30d']*100:.1f}%
                            - 风险降低: {abs(row['risk_reduction']):.1f}%
                            """)
                else:
                    st.info("该用户暂无明显可优化的风险因素")
    
    st.markdown('<div class="section-title">🚨 流失预警名单</div>', unsafe_allow_html=True)
    
    warning_system = st.session_state.warning_system
    
    col1, col2, col3 = st.columns(3)
    with col1:
        min_churn_prob = st.slider("最小30天流失概率阈值", min_value=0.1, max_value=0.9, value=0.3, step=0.05)
    with col2:
        top_n = st.selectbox("显示预警人数", options=[50, 100, 200, 500, '全部'], index=1)
        top_n_val = None if top_n == '全部' else top_n
    with col3:
        risk_filter = st.selectbox("风险等级筛选", options=['全部', '高风险', '中风险', '低风险'], index=0)
        risk_filter_val = None if risk_filter == '全部' else risk_filter
    
    warning_df = warning_system.generate_warning_list(
        min_churn_prob=min_churn_prob,
        top_n=top_n_val,
        risk_group=risk_filter_val
    )
    
    report = warning_system.generate_daily_report(warning_df)
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("预警总人数", f"{report['total_warnings']}")
    with col2:
        st.metric("高危用户", f"{report['total_high_risk']}", delta_color="inverse")
    with col3:
        st.metric("平均30天流失概率", f"{report['avg_churn_prob_30d']:.1%}")
    with col4:
        cb = warning_system.calculate_cost_benefit(warning_df)
        st.metric("预期ROI", cb['roi_multiple'])
    
    tab1, tab2 = st.tabs(["预警名单", "趋势分析"])
    
    with tab1:
        display_cols = ['user_id', 'warning_level', 'churn_prob_30d', 'churn_prob_90d', 
                       'risk_score', 'days_to_churn', 'high_risk_features', 'weak_protective_features']
        display_cols = [c for c in display_cols if c in warning_df.columns]
        
        display_warning_df = warning_df[display_cols].copy()
        display_warning_df['churn_prob_30d'] = (display_warning_df['churn_prob_30d'] * 100).round(2)
        display_warning_df['churn_prob_90d'] = (display_warning_df['churn_prob_90d'] * 100).round(2)
        display_warning_df['risk_score'] = display_warning_df['risk_score'].round(3)
        
        st.dataframe(display_warning_df, use_container_width=True)
        
        col1, col2, col3 = st.columns(3)
        with col1:
            push_format = st.selectbox("导出格式", options=['email', 'sms', 'webhook', 'csv'])
        with col2:
            st.markdown("<br>", unsafe_allow_html=True)
            export_data = warning_system.export_for_push(warning_df, platform=push_format)
            
            if push_format == 'csv':
                st.markdown(get_table_download_link(display_warning_df, f"churn_warning_list_{pd.Timestamp.now().strftime('%Y%m%d')}.csv"), unsafe_allow_html=True)
            else:
                if push_format == 'webhook':
                    st.json(export_data[:3] if isinstance(export_data, list) else export_data)
                else:
                    st.dataframe(export_data.head(10), use_container_width=True)
        with col3:
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("📤 生成推送通知", type="primary"):
                st.success(f"已生成 {len(warning_df)} 条预警推送通知，可通过{push_format}渠道发送")
    
    with tab2:
        trend_df = warning_system.get_risk_trend(days=30)
        fig_trend = plot_warning_trend(trend_df)
        st.plotly_chart(fig_trend, use_container_width=True)
        
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("### 📈 成本效益分析")
            cb = warning_system.calculate_cost_benefit(warning_df)
            st.info(f"""
            - 需要干预用户: {cb['users_to_intervene']}人
            - 预计挽留: {cb['estimated_users_saved']:.0f}人
            - 干预成本: ¥{cb['intervention_cost']:,.0f}
            - 预计挽回收入: ¥{cb['revenue_saved']:,.0f}
            - 投资回报率: **{cb['roi_multiple']}**
            """)
        with col2:
            st.markdown("### 🎯 核心风险特征")
            top_risk_features = report['top_risk_features']
            for _, row in top_risk_features.iterrows():
                deviation = row['deviation_pct']
                icon = "⚠️" if deviation > 20 else "📊"
                st.info(f"""
                {icon} **{row['feature']}** (HR={row['hazard_ratio']:.2f})
                - 预警组均值: {row['avg_in_warning']:.2f}
                - 整体均值: {row['overall_avg']:.2f}
                - 偏离: {'+' if deviation > 0 else ''}{deviation:.1f}%
                """)
    
    st.markdown('<div class="section-title">💡 留存策略推荐</div>', unsafe_allow_html=True)
    
    strategy_engine = st.session_state.strategy_engine
    
    tab1, tab2, tab3 = st.tabs(["分群策略推荐", "活动方案规划", "ROI分析"])
    
    with tab1:
        target_group = st.selectbox("选择目标分群", options=['高风险', '中风险', '低风险'], index=0)
        
        col1, col2 = st.columns([1, 1])
        
        with col1:
            st.markdown("### 🎯 分群特征画像")
            profile = strategy_engine.get_segment_profile(target_group)
            
            st.metric("用户数", f"{profile['user_count']}人")
            st.metric("平均30天流失率", f"{profile['avg_churn_30d']:.1%}")
            st.metric("平均风险评分", f"{profile['avg_risk_score']:.2f}")
            
            st.markdown("**关键特征:**")
            for char in profile['key_characteristics']:
                icon = "🔴" if char['type'] == 'risk' else "🟢"
                dev = char['deviation_pct']
                st.info(f"{icon} {char['feature']}: {'+' if dev > 0 else ''}{dev:.1f}%")
        
        with col2:
            st.markdown("### 📋 推荐策略")
            strategies = strategy_engine.get_strategies_for_segment(target_group, top_n=4)
            
            for strategy in strategies:
                urgency_color = {"high": "#e74c3c", "medium": "#f39c12", "low": "#27ae60"}[strategy['urgency']]
                st.markdown(f"""
                <div style="border-left: 4px solid {urgency_color}; padding-left: 10px; margin-bottom: 10px;">
                    <strong>{strategy['name']}</strong> [{strategy['type']}]<br>
                    <small>{strategy['description']}</small><br>
                    <small>
                        💰 成本: ¥{strategy['cost_per_user']}/人 | 
                        📉 预期降低: {strategy['expected_churn_reduction']*100:.0f}% | 
                        📈 ROI: {strategy['roi']}x |
                        📅 有效期: {strategy['duration_days']}天
                    </small>
                </div>
                """, unsafe_allow_html=True)
        
        actions = strategy_engine.generate_action_items(target_group)
        st.markdown("### 🎬 优先行动项")
        for action in actions:
            priority_icon = {"high": "🔴", "medium": "🟡", "low": "🟢"}[action['priority']]
            st.info(f"""
            {priority_icon} **{action['action']}**
            - {action['description']}
            - 建议策略: {', '.join(action['suggested_strategies'])}
            """)
    
    with tab2:
        col1, col2 = st.columns(2)
        with col1:
            campaign_group = st.selectbox("活动目标分群", options=['高风险', '中风险', '低风险'], key='campaign_group')
        with col2:
            campaign_budget = st.number_input("活动预算 (元)", min_value=1000, max_value=1000000, value=10000, step=1000)
        
        if st.button("生成活动方案", type="primary"):
            campaign_plan = strategy_engine.generate_campaign_plan(campaign_group, budget=campaign_budget)
            
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("已用预算", f"¥{campaign_plan['used_budget']:,.0f}")
            with col2:
                st.metric("触达用户", f"{campaign_plan['total_users_reached']}人")
            with col3:
                st.metric("预计挽留", f"{campaign_plan['total_expected_users_saved']:.0f}人")
            with col4:
                st.metric("预期ROI", f"{campaign_plan['overall_expected_roi']:.1f}x")
            
            fig_campaign = plot_campaign_allocation(campaign_plan)
            st.plotly_chart(fig_campaign, use_container_width=True)
            
            st.markdown("### 📝 活动明细")
            plan_df = pd.DataFrame(campaign_plan['strategies'])
            plan_df['total_cost'] = plan_df['total_cost'].apply(lambda x: f"¥{x:,.0f}")
            plan_df['expected_users_saved'] = plan_df['expected_users_saved'].round(0).astype(int)
            plan_df = plan_df.rename(columns={
                'strategy': '策略名称',
                'strategy_id': '策略ID',
                'users_reached': '触达用户',
                'total_cost': '总成本',
                'expected_users_saved': '预期挽留用户',
                'expected_roi': '预期ROI'
            })
            st.table(plan_df)
    
    with tab3:
        if 'user_id' in segmented_df.columns:
            user_for_strategy = st.selectbox(
                "选择用户查看个性化策略",
                options=segmented_df['user_id'].tolist(),
                key='strategy_user'
            )
            user_row_idx = segmented_df[segmented_df['user_id'] == user_for_strategy].index[0]
        else:
            user_row_idx = st.selectbox("选择用户索引", options=range(len(segmented_df)), key='strategy_user_idx')
            user_for_strategy = f"user_{user_row_idx}"
        
        user_row = segmented_df.loc[user_row_idx]
        personal_strategies = strategy_engine.recommend_strategies_for_user(user_row, top_n=3)
        
        col1, col2 = st.columns([1, 1])
        
        with col1:
            st.markdown("### 👤 用户画像")
            st.info(f"""
            **用户ID**: {user_for_strategy}
            **风险分组**: {user_row['risk_group']}
            **30天流失概率**: {user_row['churn_prob_30d']:.1%}
            **风险评分**: {user_row['risk_score']:.2f}
            """)
            
            st.markdown("**关键特征:**")
            risk_factors = coef_df[coef_df['coef'] > 0]['feature'].tolist()[:5]
            for f in risk_factors:
                if f in feature_cols:
                    user_val = user_row[f]
                    mean_val = segmented_df[f].mean()
                    if user_val > mean_val:
                        st.warning(f"⚠️ {f}: {user_val:.2f} (均值: {mean_val:.2f})")
            
            prot_factors = coef_df[coef_df['coef'] < 0]['feature'].tolist()[:3]
            for f in prot_factors:
                if f in feature_cols:
                    user_val = user_row[f]
                    mean_val = segmented_df[f].mean()
                    if user_val < mean_val:
                        st.info(f"💡 {f}: {user_val:.2f} (均值: {mean_val:.2f})")
        
        with col2:
            st.markdown("### 🎯 个性化推荐策略")
            fig_roi = plot_strategy_roi(personal_strategies)
            st.plotly_chart(fig_roi, use_container_width=True)
        
        st.markdown("### 📋 策略详情")
        for i, strategy in enumerate(personal_strategies, 1):
            match_pct = strategy['match_score'] * 100
            st.markdown(f"""
            <div style="background: #f8f9fa; padding: 15px; border-radius: 8px; margin-bottom: 10px;">
                <h4>推荐 {i}: {strategy['name']} (匹配度: {match_pct:.0f}%)</h4>
                <p><strong>类型:</strong> {strategy['type']} | <strong>预期ROI:</strong> {strategy['adjusted_roi']:.1f}x | <strong>成本:</strong> ¥{strategy['cost_per_user']}/人</p>
                <p>{strategy['description']}</p>
                <p><small>
                    📉 预期流失率降低: {strategy['expected_churn_reduction']*100:.0f}% | 
                    📱 推送渠道: {', '.join(strategy['channels'])} |
                    ⏰ 有效期: {strategy['duration_days']}天
                </small></p>
            </div>
            """, unsafe_allow_html=True)
    
    st.markdown('<div class="section-title">📥 分析结果导出</div>', unsafe_allow_html=True)
    
    result_cols = ['user_id', 'risk_group', 'risk_score', 'churn_prob_30d', 'churn_prob_90d']
    result_cols = [c for c in result_cols if c in segmented_df.columns]
    
    export_df = segmented_df[result_cols + feature_cols].copy()
    export_df['churn_prob_30d'] = (export_df['churn_prob_30d'] * 100).round(2)
    export_df['churn_prob_90d'] = (export_df['churn_prob_90d'] * 100).round(2)
    export_df = export_df.rename(columns={
        'risk_group': '风险分组',
        'risk_score': '风险评分',
        'churn_prob_30d': '30天流失概率(%)',
        'churn_prob_90d': '90天流失概率(%)'
    })
    
    st.dataframe(export_df.head(100), use_container_width=True)
    
    st.markdown(get_table_download_link(export_df, "churn_analysis_result.csv"), unsafe_allow_html=True)

else:
    st.info("👈 请在左侧边栏生成示例数据或上传您的CSV文件，然后运行分析")
    
    st.markdown("""
    ### 📖 使用说明
    
    1. **数据源**: 可以使用系统生成的示例数据，或上传您自己的CSV文件
    2. **数据格式要求**:
       - 包含生存时间列（用户留存天数）
       - 包含事件列（1表示流失，0表示留存/删失）
       - 其他列作为特征变量
    3. **模型配置**:
       - **PH假设检验**: Schoenfeld残差检验验证比例风险假设，违反的特征可自动分层
       - **Bootstrap**: 启用后通过重抽样估计生存曲线的95%置信区间
       - **用户分群**: 支持K-means聚类、百分位数、自定义阈值三种分群方式
    4. **核心功能**:
       - **特征系数**: 显示各特征对流失风险的影响方向和大小
       - **风险比(HR)**: HR>1为风险因素，HR<1为保护因素
       - **生存曲线**: 展示用户留存概率随时间的变化，含Bootstrap置信区间
       - **用户分群**: 基于风险评分将用户分为高/中/低风险三组，阈值可自定义
       - **干预模拟**: 调整风险因子预测流失率变化，推荐最优干预措施
       - **流失预警**: 按预测风险排序生成预警名单，支持多渠道推送
       - **策略推荐**: 针对不同风险分群推荐优惠券/活动，支持活动方案规划
    """)
