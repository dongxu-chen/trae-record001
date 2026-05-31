import streamlit as st
import numpy as np
import pandas as pd
import io
from datetime import datetime

from pmf_model import PMF, auto_select_factors
from data_utils import (
    generate_simulated_data,
    load_data_from_file,
    preprocess_data,
    get_data_summary,
    identify_source_type,
    calculate_source_contribution_percent
)
from uncertainty import (
    run_complete_uncertainty_analysis,
    calculate_uncertainty_metrics,
    calculate_contribution_uncertainty,
    get_confidence_interval_data
)
from visualization import (
    plot_source_profile,
    plot_source_contribution_timeseries,
    plot_contribution_pie,
    plot_residual_analysis,
    plot_concentration_heatmap,
    plot_uncertainty_analysis,
    plot_monthly_contribution,
    plot_source_contribution_with_events,
    plot_factor_selection_metrics,
    plot_event_timeline,
    plot_multiple_confidence_intervals,
    plot_spatial_heatmap,
    plot_emission_reduction,
    plot_reduction_comparison,
    plot_weather_correlation,
    plot_seasonal_variation,
    plot_wind_rose
)
from event_analysis import (
    run_event_analysis_pipeline,
    get_event_summary,
    create_manual_event,
    verify_event_alignment,
    detect_anomaly_events,
    EmissionEvent
)
from spatial_analysis import (
    run_spatial_analysis,
    get_hotspot_summary
)
from emission_reduction import (
    simulate_emission_reduction,
    simulate_multiple_scenarios,
    compare_scenarios,
    find_optimized_reduction,
    DEFAULT_SCENARIOS,
    create_custom_scenario
)
from weather_attribution import (
    run_weather_attribution_analysis,
    get_seasonal_summary
)

st.set_page_config(
    page_title="空气污染源解析系统 - PMF模型",
    page_icon="🌫️",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1E3A5F;
        text-align: center;
        padding: 1rem 0;
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    .sub-header {
        font-size: 1.2rem;
        color: #5A6778;
        text-align: center;
        margin-bottom: 2rem;
    }
    .section-header {
        font-size: 1.5rem;
        font-weight: bold;
        color: #2C3E50;
        padding: 0.5rem 0;
        border-left: 4px solid #667eea;
        padding-left: 1rem;
        margin: 1.5rem 0;
    }
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 1rem;
        border-radius: 10px;
        text-align: center;
    }
    .info-box {
        background-color: #E8F4FD;
        border-left: 5px solid #2196F3;
        padding: 1rem;
        margin: 1rem 0;
        border-radius: 5px;
    }
    .success-box {
        background-color: #E8F5E9;
        border-left: 5px solid #4CAF50;
        padding: 1rem;
        margin: 1rem 0;
        border-radius: 5px;
    }
    .warning-box {
        background-color: #FFF8E1;
        border-left: 5px solid #FFC107;
        padding: 1rem;
        margin: 1rem 0;
        border-radius: 5px;
    }
</style>
""", unsafe_allow_html=True)

st.markdown('<h1 class="main-header">🌫️ 空气污染源解析系统</h1>', unsafe_allow_html=True)
st.markdown('<p class="sub-header">基于PMF正定矩阵因子分解模型的污染源贡献解析</p>', unsafe_allow_html=True)

if 'pmf_model' not in st.session_state:
    st.session_state.pmf_model = None
if 'df_concentration' not in st.session_state:
    st.session_state.df_concentration = None
if 'df_uncertainty' not in st.session_state:
    st.session_state.df_uncertainty = None
if 'X' not in st.session_state:
    st.session_state.X = None
if 'U' not in st.session_state:
    st.session_state.U = None
if 'species' not in st.session_state:
    st.session_state.species = None
if 'index' not in st.session_state:
    st.session_state.index = None
if 'uncertainty_result' not in st.session_state:
    st.session_state.uncertainty_result = None
if 'source_names' not in st.session_state:
    st.session_state.source_names = None
if 'factor_selection_result' not in st.session_state:
    st.session_state.factor_selection_result = None
if 'event_analysis_result' not in st.session_state:
    st.session_state.event_analysis_result = None
if 'manual_events' not in st.session_state:
    st.session_state.manual_events = []
if 'spatial_result' not in st.session_state:
    st.session_state.spatial_result = None
if 'reduction_results' not in st.session_state:
    st.session_state.reduction_results = None
if 'reduction_comparison' not in st.session_state:
    st.session_state.reduction_comparison = None
if 'weather_result' not in st.session_state:
    st.session_state.weather_result = None
if 'weather_data' not in st.session_state:
    st.session_state.weather_data = None

with st.sidebar:
    st.header("⚙️ 系统设置")
    
    data_source = st.radio(
        "数据来源",
        ["使用模拟数据", "上传数据文件"],
        index=0
    )
    
    if data_source == "使用模拟数据":
        n_samples = st.slider("样本数量（天数）", min_value=30, max_value=730, value=365, step=30)
        start_date = st.date_input("开始日期", value=datetime(2024, 1, 1))
        random_seed = st.number_input("随机种子", min_value=0, max_value=9999, value=42)
        
        if st.button("生成模拟数据", type="primary", use_container_width=True):
            with st.spinner("正在生成模拟数据..."):
                df_conc, df_unc = generate_simulated_data(
                    n_samples=n_samples,
                    start_date=start_date.strftime('%Y-%m-%d'),
                    random_state=random_seed
                )
                st.session_state.df_concentration = df_conc
                st.session_state.df_uncertainty = df_unc
                st.success("✅ 模拟数据生成成功！")
    else:
        uploaded_file = st.file_uploader(
            "上传数据文件 (CSV/Excel)",
            type=['csv', 'xlsx'],
            help="文件应包含日期列和PM2.5、PM10、NO2、SO2、O3等污染物浓度列，\
                  可选列名如PM2.5_U表示对应不确定性"
        )
        
        if uploaded_file is not None:
            try:
                file_path = f"temp_{uploaded_file.name}"
                with open(file_path, "wb") as f:
                    f.write(uploaded_file.getbuffer())
                
                df_conc, df_unc = load_data_from_file(file_path)
                st.session_state.df_concentration = df_conc
                st.session_state.df_uncertainty = df_unc
                st.success("✅ 数据加载成功！")
                
                import os
                os.remove(file_path)
            except Exception as e:
                st.error(f"❌ 数据加载失败: {str(e)}")
    
    st.markdown("---")
    st.header("📊 PMF模型参数")
    
    auto_select_n_factors = st.checkbox("自动选择因子数", value=False, help="基于残差分析和稳定性校验自动选择最优因子数")
    
    if auto_select_n_factors:
        min_factors = st.slider("最小因子数", min_value=2, max_value=4, value=2, step=1)
        max_factors = st.slider("最大因子数", min_value=3, max_value=8, value=6, step=1)
        n_factors_runs = st.slider("稳定性校验次数", min_value=3, max_value=15, value=8, step=1)
        n_factors = None
    else:
        n_factors = st.slider("因子数量（污染源数）", min_value=2, max_value=8, value=3, step=1)
    
    max_iter = st.number_input("最大迭代次数", min_value=1000, max_value=20000, value=5000, step=1000)
    tol = st.selectbox("收敛阈值", [1e-4, 1e-6, 1e-8, 1e-10], index=2)
    n_starts = st.slider("随机初始化次数", min_value=5, max_value=50, value=20, step=5)
    
    uncertainty_method = st.selectbox(
        "不确定性计算方法",
        ["default", "relative", "absolute"],
        index=0,
        help="default: 0.1*X + 0.01*mean(X); relative: 0.15*X; absolute: 5.0"
    )
    
    source_names_input = st.text_input(
        "污染源名称（用逗号分隔）",
        value="工业源,交通源,扬尘源,燃煤源,生活源,农业源",
        help="名称数量应与因子数量一致"
    )
    
    auto_identify = st.checkbox("自动识别污染源类型", value=True)
    
    st.markdown("---")
    st.header("🔬 不确定性分析")
    
    run_uncertainty = st.checkbox("运行Bootstrap不确定性分析", value=False)
    n_bootstrap = st.slider("Bootstrap次数", min_value=10, max_value=200, value=50, step=10)
    
    confidence_levels_input = st.text_input(
        "置信区间级别（用逗号分隔）",
        value="10,50,80,90,95",
        help="支持多种置信区间级别，如10,50,80,90,95"
    )
    
    st.markdown("---")
    
    confidence_levels = [int(x.strip()) for x in confidence_levels_input.split(',')]
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("运行模型", type="primary", use_container_width=True):
            if st.session_state.df_concentration is None:
                st.error("❌ 请先加载数据！")
            else:
                try:
                    source_names = [s.strip() for s in source_names_input.split(',')]
                    
                    X, U, species, index = preprocess_data(
                        st.session_state.df_concentration,
                        st.session_state.df_uncertainty,
                        uncertainty_method=uncertainty_method
                    )
                    
                    st.session_state.X = X
                    st.session_state.U = U
                    st.session_state.species = species
                    st.session_state.index = index
                    
                    if auto_select_n_factors:
                        with st.spinner("正在自动选择最优因子数..."):
                            factor_result = auto_select_factors(
                                X, U, species,
                                min_factors=min_factors,
                                max_factors=max_factors,
                                n_runs=n_factors_runs,
                                max_iter=max_iter,
                                tol=tol,
                                random_state=42
                            )
                            st.session_state.factor_selection_result = factor_result
                            n_factors = factor_result.optimal_n_factors
                            st.success(f"✅ 自动选择最优因子数: {n_factors}")
                    else:
                        st.session_state.factor_selection_result = None
                    
                    with st.spinner(f"正在运行PMF模型 (因子数={n_factors})..."):
                        pmf = PMF(
                            n_factors=n_factors,
                            max_iter=max_iter,
                            tol=tol,
                            n_starts=n_starts,
                            random_state=42,
                            source_names=source_names[:n_factors]
                        )
                        
                        pmf.fit(X, U, species)
                        st.session_state.pmf_model = pmf
                        
                        if auto_identify:
                            identified_names = identify_source_type(pmf.result_.F, species)
                            pmf.source_names = identified_names
                            pmf.result_.source_names = identified_names
                            st.session_state.source_names = identified_names
                        else:
                            st.session_state.source_names = source_names[:n_factors]
                        
                        if run_uncertainty:
                            with st.spinner(f"正在运行Bootstrap分析 ({n_bootstrap}次)..."):
                                try:
                                    unc_result = run_complete_uncertainty_analysis(
                                        X, U, species,
                                        n_factors=n_factors,
                                        n_bootstrap=n_bootstrap,
                                        base_F=pmf.result_.F,
                                        source_names=st.session_state.source_names,
                                        index=index,
                                        random_state=42,
                                        confidence_levels=confidence_levels
                                    )
                                    st.session_state.uncertainty_result = unc_result
                                except Exception as e:
                                    st.warning(f"⚠️ 不确定性分析运行失败: {str(e)}")
                                    st.session_state.uncertainty_result = None
                        else:
                            st.session_state.uncertainty_result = None
                        
                        with st.spinner("正在运行事件分析..."):
                            try:
                                source_contribution = pmf.get_source_contribution(index)
                                event_result = run_event_analysis_pipeline(
                                    source_contribution,
                                    st.session_state.df_concentration,
                                    manual_events=st.session_state.manual_events
                                )
                                st.session_state.event_analysis_result = event_result
                            except Exception as e:
                                st.warning(f"⚠️ 事件分析运行失败: {str(e)}")
                                st.session_state.event_analysis_result = None
                        
                        with st.spinner("正在运行空间分布分析..."):
                            try:
                                spatial_result = run_spatial_analysis(source_contribution)
                                st.session_state.spatial_result = spatial_result
                            except Exception as e:
                                st.warning(f"⚠️ 空间分析运行失败: {str(e)}")
                                st.session_state.spatial_result = None
                        
                        with st.spinner("正在运行减排模拟分析..."):
                            try:
                                source_profile = pmf.get_source_profile()
                                reduction_results = simulate_multiple_scenarios(
                                    source_contribution,
                                    st.session_state.df_concentration,
                                    source_profile,
                                    DEFAULT_SCENARIOS
                                )
                                st.session_state.reduction_results = reduction_results
                                st.session_state.reduction_comparison = compare_scenarios(
                                    reduction_results,
                                    DEFAULT_SCENARIOS
                                )
                            except Exception as e:
                                st.warning(f"⚠️ 减排模拟运行失败: {str(e)}")
                                st.session_state.reduction_results = None
                                st.session_state.reduction_comparison = None
                        
                        with st.spinner("正在运行天气归因分析..."):
                            try:
                                weather_result = run_weather_attribution_analysis(
                                    source_contribution
                                )
                                st.session_state.weather_result = weather_result
                            except Exception as e:
                                st.warning(f"⚠️ 天气分析运行失败: {str(e)}")
                                st.session_state.weather_result = None
                        
                        st.success("✅ 模型运行成功！")
                        
                except Exception as e:
                    st.error(f"❌ 模型运行失败: {str(e)}")
                    import traceback
                    st.error(traceback.format_exc())
    
    with col2:
        if st.button("重置", use_container_width=True):
            for key in st.session_state.keys():
                del st.session_state[key]
            st.rerun()

tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8, tab9 = st.tabs([
    "📊 数据预览", "🔬 模型结果", "📈 可视化分析", "❌ 残差诊断", "📋 不确定性分析", "📅 事件分析", "🗺️ 空间分布", "♻️ 减排模拟", "🌤️ 天气归因"
])

with tab1:
    st.markdown('<h2 class="section-header">数据预览</h2>', unsafe_allow_html=True)
    
    if st.session_state.df_concentration is not None:
        df_conc = st.session_state.df_concentration
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("样本数", len(df_conc))
        with col2:
            st.metric("污染物种类", len(df_conc.columns))
        with col3:
            st.metric("时间范围", f"{df_conc.index.min().date()} ~ {df_conc.index.max().date()}")
        with col4:
            st.metric("数据完整性", f"{(1 - df_conc.isnull().sum().sum() / (len(df_conc) * len(df_conc.columns))) * 100:.1f}%")
        
        st.subheader("污染物浓度数据")
        st.dataframe(
            df_conc.style.highlight_max(axis=0, color='#FFCDD2')
                    .highlight_min(axis=0, color='#C8E6C9')
                    .format("{:.2f}"),
            use_container_width=True,
            height=300
        )
        
        if st.session_state.df_uncertainty is not None:
            st.subheader("不确定性数据")
            st.dataframe(
                st.session_state.df_uncertainty.style.format("{:.2f}"),
                use_container_width=True,
                height=200
            )
        
        st.subheader("描述性统计")
        summary_df = get_data_summary(df_conc)
        st.dataframe(summary_df, use_container_width=True)
        
        st.subheader("污染物相关性分析")
        fig_heatmap = plot_concentration_heatmap(df_conc)
        st.plotly_chart(fig_heatmap, use_container_width=True)
        
        st.subheader("浓度时间序列")
        fig_ts = plot_source_contribution_timeseries(df_conc)
        fig_ts.update_layout(title='污染物浓度时间序列', yaxis_title='浓度 (μg/m³)')
        st.plotly_chart(fig_ts, use_container_width=True)
        
    else:
        st.info("👈 请在左侧边栏生成模拟数据或上传数据文件")

with tab2:
    st.markdown('<h2 class="section-header">PMF模型结果</h2>', unsafe_allow_html=True)
    
    if st.session_state.pmf_model is not None:
        pmf = st.session_state.pmf_model
        
        stats = pmf.get_statistics()
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Q值", f"{stats['Q值']:.2f}")
        with col2:
            st.metric("Q/自由度", f"{stats['Q/自由度']:.4f}")
        with col3:
            st.metric("因子数", stats['因子数'])
        with col4:
            st.metric("迭代次数", stats['迭代次数'])
        
        if stats['Q/自由度'] < 1.5:
            st.success("✅ 模型拟合效果良好 (Q/自由度 < 1.5)")
        elif stats['Q/自由度'] < 2.0:
            st.warning("⚠️ 模型拟合效果一般 (1.5 < Q/自由度 < 2.0)")
        else:
            st.error("❌ 模型拟合效果较差，建议调整因子数量 (Q/自由度 > 2.0)")
        
        if st.session_state.factor_selection_result is not None:
            st.markdown("---")
            st.subheader("🎯 因子数自动选择结果")
            st.info(f"💡 最优因子数: {st.session_state.factor_selection_result.optimal_n_factors}")
            st.caption(f"选择理由: {st.session_state.factor_selection_result.reason}")
            
            st.dataframe(
                st.session_state.factor_selection_result.metrics.style.format({
                    'Q均值': '{:.2f}',
                    'Q标准差': '{:.2f}',
                    'Q/自由度': '{:.4f}',
                    '解释方差(%)': '{:.2f}',
                    '稳定性得分': '{:.3f}',
                    '残差均值': '{:.4f}',
                    '残差标准差': '{:.4f}',
                    '异常值比例(%)': '{:.2f}'
                }),
                use_container_width=True
            )
            
            fig_factor = plot_factor_selection_metrics(st.session_state.factor_selection_result.metrics)
            st.plotly_chart(fig_factor, use_container_width=True)
        
        st.markdown("---")
        st.subheader("污染源谱 (Source Profile)")
        st.info("💡 源谱表示各污染源中不同污染物的相对比例")
        
        source_profile = pmf.get_source_profile()
        st.dataframe(
            source_profile.style.format("{:.3f}")
                            .highlight_max(axis=1, color='#FFCDD2'),
            use_container_width=True
        )
        
        col1, col2 = st.columns(2)
        with col1:
            fig_profile = plot_source_profile(
                source_profile,
                uncertainty_result=st.session_state.uncertainty_result
            )
            st.plotly_chart(fig_profile, use_container_width=True)
        
        with col2:
            fig_pie = plot_contribution_pie(pmf.get_source_contribution(st.session_state.index))
            st.plotly_chart(fig_pie, use_container_width=True)
        
        st.markdown("---")
        st.subheader("源贡献时间序列")
        st.info("💡 表示各污染源在不同时间点的贡献浓度")
        
        source_contribution = pmf.get_source_contribution(st.session_state.index)
        st.dataframe(
            source_contribution.style.format("{:.2f}"),
            use_container_width=True,
            height=250
        )
        
        fig_contribution = plot_source_contribution_timeseries(
            source_contribution,
            uncertainty_result=st.session_state.uncertainty_result
        )
        st.plotly_chart(fig_contribution, use_container_width=True)
        
        st.markdown("---")
        st.subheader("月均源贡献")
        fig_monthly = plot_monthly_contribution(source_contribution)
        st.plotly_chart(fig_monthly, use_container_width=True)
        
        st.markdown("---")
        st.subheader("各污染源平均贡献统计")
        avg_contribution = source_contribution.mean()
        total_contribution = avg_contribution.sum()
        percent_contribution = (avg_contribution / total_contribution * 100).round(2)
        
        contribution_stats = pd.DataFrame({
            '平均贡献浓度 (μg/m³)': avg_contribution.round(2),
            '贡献占比 (%)': percent_contribution,
            '标准差': source_contribution.std().round(2),
            '最大值': source_contribution.max().round(2),
            '最小值': source_contribution.min().round(2),
        })
        st.dataframe(contribution_stats, use_container_width=True)
        
    else:
        st.info("👈 请先加载数据并运行模型")

with tab3:
    st.markdown('<h2 class="section-header">可视化分析</h2>', unsafe_allow_html=True)
    
    if st.session_state.pmf_model is not None:
        pmf = st.session_state.pmf_model
        source_profile = pmf.get_source_profile()
        source_contribution = pmf.get_source_contribution(st.session_state.index)
        
        chart_type = st.selectbox(
            "选择图表类型",
            ["污染源谱图", "源贡献时间序列", "贡献占比饼图", 
             "月均贡献堆叠图", "污染物相关性热力图"],
            index=0
        )
        
        use_plotly = st.checkbox("使用Plotly交互式图表", value=True)
        
        if chart_type == "污染源谱图":
            fig = plot_source_profile(
                source_profile,
                uncertainty_result=st.session_state.uncertainty_result,
                use_plotly=use_plotly
            )
            if use_plotly:
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.pyplot(fig, use_container_width=True)
                
        elif chart_type == "源贡献时间序列":
            fig = plot_source_contribution_timeseries(
                source_contribution,
                uncertainty_result=st.session_state.uncertainty_result,
                use_plotly=use_plotly
            )
            if use_plotly:
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.pyplot(fig, use_container_width=True)
                
        elif chart_type == "贡献占比饼图":
            fig = plot_contribution_pie(source_contribution, use_plotly=use_plotly)
            if use_plotly:
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.pyplot(fig, use_container_width=True)
                
        elif chart_type == "月均贡献堆叠图":
            fig = plot_monthly_contribution(source_contribution, use_plotly=use_plotly)
            if use_plotly:
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.pyplot(fig, use_container_width=True)
                
        elif chart_type == "污染物相关性热力图":
            fig = plot_concentration_heatmap(st.session_state.df_concentration, use_plotly=use_plotly)
            if use_plotly:
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.pyplot(fig, use_container_width=True)
        
        st.markdown("---")
        st.subheader("🔽 结果导出")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            csv_profile = source_profile.to_csv(index=True, encoding='utf-8-sig')
            st.download_button(
                "📥 下载源谱表",
                csv_profile,
                "source_profile.csv",
                "text/csv",
                use_container_width=True
            )
        
        with col2:
            csv_contribution = source_contribution.to_csv(index=True, encoding='utf-8-sig')
            st.download_button(
                "📥 下载源贡献表",
                csv_contribution,
                "source_contribution.csv",
                "text/csv",
                use_container_width=True
            )
        
        with col3:
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                source_profile.to_excel(writer, sheet_name='源谱')
                source_contribution.to_excel(writer, sheet_name='源贡献')
                contribution_stats.to_excel(writer, sheet_name='统计摘要')
                if st.session_state.uncertainty_result is not None:
                    unc_metrics = calculate_uncertainty_metrics(st.session_state.uncertainty_result)
                    unc_metrics.to_excel(writer, sheet_name='不确定性分析', index=False)
            
            excel_data = output.getvalue()
            st.download_button(
                "📥 下载完整报告(Excel)",
                excel_data,
                "PMF_source_apportionment_report.xlsx",
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )
    else:
        st.info("👈 请先加载数据并运行模型")

with tab4:
    st.markdown('<h2 class="section-header">残差诊断</h2>', unsafe_allow_html=True)
    
    if st.session_state.pmf_model is not None:
        pmf = st.session_state.pmf_model
        
        st.info("💡 残差分析用于评估模型拟合效果。理想情况下，标准化残差应服从均值为0的正态分布，且在±3范围内。")
        
        fig_residual = plot_residual_analysis(
            st.session_state.X,
            pmf.result_.residuals,
            pmf.result_.scaled_residuals,
            st.session_state.species
        )
        st.plotly_chart(fig_residual, use_container_width=True)
        
        st.markdown("---")
        st.subheader("残差统计")
        
        residual_df = pd.DataFrame({
            '污染物': st.session_state.species,
            '平均残差': pmf.result_.residuals.mean(axis=0).round(4),
            '残差标准差': pmf.result_.residuals.std(axis=0).round(4),
            '平均标准化残差': pmf.result_.scaled_residuals.mean(axis=0).round(4),
            '标准化残差标准差': pmf.result_.scaled_residuals.std(axis=0).round(4),
            '|标准化残差|>3比例(%)': (np.abs(pmf.result_.scaled_residuals) > 3).mean(axis=0).round(4) * 100,
        })
        
        st.dataframe(residual_df, use_container_width=True)
        
        bad_points = np.any(np.abs(pmf.result_.scaled_residuals) > 3, axis=1)
        if bad_points.sum() > 0:
            st.warning(f"⚠️ 检测到 {bad_points.sum()} 个样本存在较大残差 (|标准化残差| > 3)")
            bad_dates = st.session_state.index[bad_points]
            st.write("异常样本日期:")
            st.dataframe(pd.DataFrame({'日期': bad_dates}), use_container_width=True)
        else:
            st.success("✅ 所有样本的残差均在合理范围内 (|标准化残差| < 3)")
        
        st.markdown("---")
        st.subheader("Q值收敛曲线")
        
        q_history = pmf.result_.Q_history
        if len(q_history) > 1:
            import plotly.graph_objects as go
            fig_q = go.Figure()
            fig_q.add_trace(go.Scatter(
                x=list(range(len(q_history))),
                y=q_history,
                mode='lines',
                line=dict(color='#667eea', width=2),
                name='Q值'
            ))
            fig_q.update_layout(
                title='Q值收敛曲线',
                xaxis_title='迭代次数',
                yaxis_title='Q值',
                height=400,
                template='plotly_white'
            )
            st.plotly_chart(fig_q, use_container_width=True)
            
            st.info(f"💡 初始Q值: {q_history[0]:.2f}，最终Q值: {q_history[-1]:.2f}，下降了 {(1 - q_history[-1]/q_history[0])*100:.2f}%")
    else:
        st.info("👈 请先加载数据并运行模型")

with tab5:
    st.markdown('<h2 class="section-header">不确定性分析</h2>', unsafe_allow_html=True)
    
    if st.session_state.uncertainty_result is not None:
        unc_result = st.session_state.uncertainty_result
        
        st.success(f"✅ Bootstrap分析完成，成功运行 {unc_result.bootstrap_runs} 次")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Bootstrap次数", unc_result.bootstrap_runs)
        with col2:
            st.metric("Q值均值", f"{np.mean(unc_result.Q_values):.2f}")
        with col3:
            st.metric("Q值标准差", f"{np.std(unc_result.Q_values):.2f}")
        
        if unc_result.confidence_levels:
            st.markdown("---")
            st.subheader("多置信区间对比")
            selected_source_for_ci = st.selectbox(
                "选择污染源查看多置信区间",
                unc_result.source_names,
                index=0
            )
            source_idx = unc_result.source_names.index(selected_source_for_ci)
            
            fig_multi_ci = plot_multiple_confidence_intervals(
                st.session_state.pmf_model.get_source_contribution(st.session_state.index),
                unc_result,
                source_idx=source_idx,
                confidence_levels=unc_result.confidence_levels
            )
            st.plotly_chart(fig_multi_ci, use_container_width=True)
        
        st.markdown("---")
        st.subheader("源谱不确定性统计")
        selected_cl = st.selectbox(
            "选择置信区间级别",
            unc_result.confidence_levels or [95],
            index=len(unc_result.confidence_levels) - 1 if unc_result.confidence_levels else 0
        )
        unc_metrics = calculate_uncertainty_metrics(unc_result, confidence_level=selected_cl)
        st.dataframe(
            unc_metrics.style.format({
                '平均值': '{:.4f}',
                '标准差': '{:.4f}',
                '变异系数(%)': '{:.2f}',
                f'{selected_cl}%置信下限': '{:.4f}',
                f'{selected_cl}%置信上限': '{:.4f}'
            }),
            use_container_width=True
        )
        
        high_cv = unc_metrics[unc_metrics['变异系数(%)'] > 30]
        if len(high_cv) > 0:
            st.warning(f"⚠️ 检测到 {len(high_cv)} 个源谱元素变异系数 > 30%，可能存在较大不确定性")
        else:
            st.success("✅ 所有源谱元素的变异系数均在合理范围内 (< 30%)")
        
        st.markdown("---")
        st.subheader("源贡献不确定性")
        unc_contribution = calculate_contribution_uncertainty(unc_result)
        st.dataframe(
            unc_contribution.style.format("{:.2f}"),
            use_container_width=True,
            height=300
        )
        
        st.markdown("---")
        st.subheader("带置信区间的源贡献时间序列")
        selected_source = st.selectbox(
            "选择污染源",
            unc_result.source_names,
            index=0
        )
        source_idx = unc_result.source_names.index(selected_source)
        
        import plotly.graph_objects as go
        fig_ci = go.Figure()
        
        fig_ci.add_trace(go.Scatter(
            x=unc_result.index,
            y=unc_result.G_upper[:, source_idx],
            mode='lines',
            line=dict(width=0),
            showlegend=False,
            name='95%置信上限'
        ))
        
        fig_ci.add_trace(go.Scatter(
            x=unc_result.index,
            y=unc_result.G_lower[:, source_idx],
            mode='lines',
            line=dict(width=0),
            fillcolor='rgba(102, 126, 234, 0.2)',
            fill='tonexty',
            showlegend=False,
            name='95%置信下限'
        ))
        
        fig_ci.add_trace(go.Scatter(
            x=unc_result.index,
            y=unc_result.G_mean[:, source_idx],
            mode='lines',
            line=dict(color='#667eea', width=2),
            name='均值'
        ))
        
        fig_ci.update_layout(
            title=f'{selected_source} 贡献时间序列 (带95%置信区间)',
            xaxis_title='日期',
            yaxis_title='源贡献浓度 (μg/m³)',
            height=500,
            template='plotly_white',
            hovermode='x unified'
        )
        
        st.plotly_chart(fig_ci, use_container_width=True)
        
        st.markdown("---")
        csv_unc = unc_metrics.to_csv(index=False, encoding='utf-8-sig')
        st.download_button(
            "📥 下载不确定性分析结果",
            csv_unc,
            "uncertainty_analysis.csv",
            "text/csv",
            use_container_width=True
        )
        
    elif st.session_state.pmf_model is not None:
        st.info("💡 如需进行不确定性分析，请在左侧边栏勾选「运行Bootstrap不确定性分析」后重新运行模型")
        
        st.warning("⚠️ Bootstrap分析可能需要较长时间，请耐心等待")
    else:
        st.info("👈 请先加载数据并运行模型")

with tab6:
    st.markdown('<h2 class="section-header">📅 事件分析</h2>', unsafe_allow_html=True)
    
    if st.session_state.event_analysis_result is not None and st.session_state.pmf_model is not None:
        event_result = st.session_state.event_analysis_result
        pmf = st.session_state.pmf_model
        source_contribution = pmf.get_source_contribution(st.session_state.index)
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("检测事件数", event_result.detection_metrics['检测事件数'])
        with col2:
            st.metric("手动事件数", event_result.detection_metrics['手动事件数'])
        with col3:
            st.metric("总事件数", event_result.detection_metrics['总事件数'])
        with col4:
            st.metric("平均置信度", f"{event_result.detection_metrics['平均置信度']:.2f}")
        
        st.markdown("---")
        st.subheader("📋 事件列表")
        
        if len(event_result.events) > 0:
            events_df = get_event_summary(event_result.events)
            st.dataframe(events_df, use_container_width=True)
            
            st.markdown("---")
            st.subheader("📈 事件时间线")
            fig_timeline = plot_event_timeline(event_result.events)
            st.plotly_chart(fig_timeline, use_container_width=True)
            
            st.markdown("---")
            st.subheader("📊 源贡献时间序列（带事件标注）")
            
            selected_cl_event = st.selectbox(
                "选择置信区间级别用于显示",
                [90, 80, 50, 95, 10] if st.session_state.uncertainty_result is None 
                else (st.session_state.uncertainty_result.confidence_levels or [90]),
                index=0
            )
            
            fig_events = plot_source_contribution_with_events(
                source_contribution,
                event_result.events,
                uncertainty_result=st.session_state.uncertainty_result,
                confidence_level=selected_cl_event
            )
            st.plotly_chart(fig_events, use_container_width=True)
            
            st.markdown("---")
            st.subheader("📉 事件影响分析")
            st.dataframe(event_result.event_impact, use_container_width=True)
            
            st.markdown("---")
            st.subheader("🔍 排放事件对齐验证")
            if len(event_result.events) > 0:
                selected_event_id = st.selectbox(
                    "选择事件进行对齐验证",
                    [e.event_id for e in event_result.events],
                    index=0
                )
                
                selected_event = next((e for e in event_result.events if e.event_id == selected_event_id), None)
                if selected_event:
                    alignment_result = verify_event_alignment(
                        selected_event,
                        source_contribution
                    )
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        st.metric("是否对齐", "✅ 是" if alignment_result['aligned'] else "❌ 否")
                        st.metric("重叠天数", alignment_result['overlap_days'])
                    with col2:
                        st.metric("均值增幅", f"{alignment_result['mean_increase_ratio']*100:.1f}%")
                        st.metric("峰值增幅", f"{alignment_result['peak_increase_ratio']*100:.1f}%")
                    
                    if alignment_result['sources_impacted']:
                        st.success(f"💡 受影响的污染源: {', '.join(alignment_result['sources_impacted'])}")
                    else:
                        st.warning("⚠️ 未检测到显著受影响的污染源")
        else:
            st.info("未检测到异常排放事件")
        
        st.markdown("---")
        st.subheader("✏️ 添加手动事件")
        
        with st.form("add_event_form"):
            col1, col2 = st.columns(2)
            with col1:
                event_id = st.text_input("事件ID", value=f"MANUAL_{len(st.session_state.manual_events) + 1:04d}")
                event_type = st.selectbox("事件类型", ["工厂检修", "交通管制", "扬尘天气", "节日排放", "其他"])
                start_date = st.date_input("开始日期")
            
            with col2:
                end_date = st.date_input("结束日期")
                sources_involved = st.multiselect(
                    "涉及污染源",
                    st.session_state.source_names or ['工业源', '交通源', '扬尘源'],
                    default=st.session_state.source_names or ['工业源', '交通源', '扬尘源']
                )
                description = st.text_area("事件描述")
            
            if st.form_submit_button("添加事件"):
                new_event = create_manual_event(
                    event_id=event_id,
                    start_date=str(start_date),
                    end_date=str(end_date),
                    event_type=event_type,
                    description=description,
                    sources_involved=sources_involved
                )
                st.session_state.manual_events.append(new_event)
                st.success(f"✅ 事件 {event_id} 添加成功！请重新运行模型以分析事件影响")
        
        if st.session_state.manual_events:
            st.markdown("---")
            st.subheader("📝 已添加的手动事件")
            manual_df = get_event_summary(st.session_state.manual_events)
            st.dataframe(manual_df, use_container_width=True)
            
            if st.button("清除所有手动事件"):
                st.session_state.manual_events = []
                st.rerun()
        
    elif st.session_state.pmf_model is not None:
        st.info("💡 事件分析将在模型运行后自动执行")
        st.warning("⚠️ 请先运行模型以进行事件分析")
    else:
        st.info("👈 请先加载数据并运行模型")

with tab7:
    st.markdown('<h2 class="section-header">🗺️ 污染源空间分布</h2>', unsafe_allow_html=True)
    
    if st.session_state.spatial_result is not None:
        spatial_result = st.session_state.spatial_result
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("监测站点数", len(spatial_result.points))
        with col2:
            st.metric("污染源数", len(spatial_result.source_names))
        with col3:
            st.metric("网格分辨率", f"{spatial_result.grid_lat.shape[0]}×{spatial_result.grid_lat.shape[1]}")
        with col4:
            hotspot_count = sum(len(hs) for hs in spatial_result.hotspots.values())
            st.metric("热点区域数", hotspot_count)
        
        st.markdown("---")
        st.subheader("📍 空间分布热力图")
        
        selected_source_spatial = st.selectbox(
            "选择污染源查看空间分布",
            spatial_result.source_names,
            index=0
        )
        source_idx_spatial = spatial_result.source_names.index(selected_source_spatial)
        
        fig_spatial = plot_spatial_heatmap(spatial_result, source_idx_spatial)
        st.plotly_chart(fig_spatial, use_container_width=True)
        
        st.markdown("---")
        st.subheader("📊 空间分布统计")
        st.dataframe(
            spatial_result.spatial_stats.style.format({
                '最小值': '{:.2f}',
                '最大值': '{:.2f}',
                '平均值': '{:.2f}',
                '标准差': '{:.2f}',
                '变异系数': '{:.3f}',
                '空间分布均匀度': '{:.3f}'
            }),
            use_container_width=True
        )
        
        st.markdown("---")
        st.subheader("🔥 污染源热点区域")
        
        hotspot_df = get_hotspot_summary(spatial_result.hotspots)
        if len(hotspot_df) > 0:
            st.dataframe(
                hotspot_df.style.format({
                    '纬度': '{:.4f}',
                    '经度': '{:.4f}',
                    '源贡献': '{:.2f}'
                }),
                use_container_width=True
            )
        else:
            st.info("未检测到热点区域")
        
        st.markdown("---")
        st.subheader("📍 监测站点信息")
        site_data = []
        for point in spatial_result.points:
            site_data.append({
                '站点名称': point.site_name,
                '纬度': point.latitude,
                '经度': point.longitude,
                **point.source_contributions
            })
        site_df = pd.DataFrame(site_data)
        st.dataframe(site_df, use_container_width=True, height=300)
        
    elif st.session_state.pmf_model is not None:
        st.info("💡 空间分布分析将在模型运行后自动执行")
        st.warning("⚠️ 请先运行模型以进行空间分布分析")
    else:
        st.info("👈 请先加载数据并运行模型")

with tab8:
    st.markdown('<h2 class="section-header">♻️ 减排模拟分析</h2>', unsafe_allow_html=True)
    
    if st.session_state.reduction_results is not None and st.session_state.reduction_comparison is not None:
        reduction_results = st.session_state.reduction_results
        reduction_comparison = st.session_state.reduction_comparison
        
        st.success("✅ 减排模拟完成，共分析了5个预设场景")
        
        st.markdown("---")
        st.subheader("📊 不同减排场景效果对比")
        
        fig_comparison = plot_reduction_comparison(reduction_comparison)
        st.plotly_chart(fig_comparison, use_container_width=True)
        
        st.dataframe(reduction_comparison, use_container_width=True)
        
        st.markdown("---")
        st.subheader("📈 单场景详细分析")
        
        scenario_names = [s.name for s in DEFAULT_SCENARIOS]
        selected_scenario_name = st.selectbox(
            "选择减排场景查看详细结果",
            scenario_names,
            index=0
        )
        selected_scenario = DEFAULT_SCENARIOS[scenario_names.index(selected_scenario_name)]
        selected_result = reduction_results[selected_scenario.scenario_id]
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("总减排率", f"{selected_result.total_reduction_stats['总相对减排率(%)']:.2f}%")
        with col2:
            st.metric("PM2.5减排率", f"{selected_result.total_reduction_stats['PM2.5减排率(%)']:.2f}%")
        with col3:
            st.metric("PM10减排率", f"{selected_result.total_reduction_stats['PM10减排率(%)']:.2f}%")
        
        st.info(f"📝 场景描述: {selected_scenario.description}")
        
        selected_pollutant = st.selectbox(
            "选择污染物查看减排效果时间序列",
            selected_result.original_concentration.columns.tolist(),
            index=0
        )
        
        fig_reduction = plot_emission_reduction(selected_result, selected_pollutant)
        st.plotly_chart(fig_reduction, use_container_width=True)
        
        st.markdown("---")
        st.subheader("🧮 各污染物减排效果")
        st.dataframe(
            selected_result.pollutant_reductions.style.format({
                '原始均值': '{:.2f}',
                '减排后均值': '{:.2f}',
                '绝对变化': '{:.2f}',
                '相对变化(%)': '{:.2f}'
            }),
            use_container_width=True
        )
        
        st.markdown("---")
        st.subheader("🔧 自定义减排方案")
        
        with st.form("custom_reduction_form"):
            col1, col2 = st.columns(2)
            with col1:
                custom_source = st.selectbox(
                    "选择减排污染源",
                    st.session_state.source_names or ['工业源', '交通源', '扬尘源'],
                    index=0
                )
                reduction_percent = st.slider(
                    "减排比例 (%)",
                    min_value=5,
                    max_value=95,
                    value=30,
                    step=5
                )
            
            with col2:
                target_pollutant = st.selectbox(
                    "目标污染物",
                    ['PM2.5', 'PM10', 'NO2', 'SO2', 'O3'],
                    index=0
                )
            
            if st.form_submit_button("运行自定义减排模拟"):
                custom_reductions = {custom_source: reduction_percent / 100.0}
                pmf = st.session_state.pmf_model
                source_profile = pmf.get_source_profile()
                source_contribution = pmf.get_source_contribution(st.session_state.index)
                
                custom_result = simulate_emission_reduction(
                    source_contribution,
                    st.session_state.df_concentration,
                    source_profile,
                    custom_reductions
                )
                
                st.success(f"✅ 自定义减排模拟完成！")
                
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("总减排率", f"{custom_result.total_reduction_stats['总相对减排率(%)']:.2f}%")
                with col2:
                    st.metric(f"{target_pollutant}减排率", 
                             f"{custom_result.total_reduction_stats.get(f'{target_pollutant}减排率(%)', 0):.2f}%")
                
                fig_custom = plot_emission_reduction(custom_result, target_pollutant)
                st.plotly_chart(fig_custom, use_container_width=True)
        
        st.markdown("---")
        st.subheader("🎯 优化减排方案推荐")
        
        with st.form("optimized_reduction_form"):
            col1, col2 = st.columns(2)
            with col1:
                target_pollutant_opt = st.selectbox(
                    "目标污染物",
                    ['PM2.5', 'PM10', 'NO2', 'SO2', 'O3'],
                    index=0,
                    key="opt_target"
                )
            with col2:
                target_reduction = st.slider(
                    "目标减排比例 (%)",
                    min_value=10,
                    max_value=50,
                    value=30,
                    step=5
                )
            
            if st.form_submit_button("生成优化减排方案"):
                pmf = st.session_state.pmf_model
                source_profile = pmf.get_source_profile()
                source_contribution = pmf.get_source_contribution(st.session_state.index)
                
                optimized = find_optimized_reduction(
                    source_contribution,
                    st.session_state.df_concentration,
                    source_profile,
                    target_pollutant=target_pollutant_opt,
                    target_reduction_percent=target_reduction
                )
                
                st.success("✅ 优化减排方案已生成！")
                
                opt_df = pd.DataFrame({
                    '污染源': list(optimized.keys()),
                    '建议减排比例 (%)': [v * 100 for v in optimized.values()]
                })
                st.dataframe(opt_df.style.format({'建议减排比例 (%)': '{:.1f}'}), 
                           use_container_width=True)
                
                opt_result = simulate_emission_reduction(
                    source_contribution,
                    st.session_state.df_concentration,
                    source_profile,
                    optimized
                )
                
                fig_opt = plot_emission_reduction(opt_result, target_pollutant_opt)
                st.plotly_chart(fig_opt, use_container_width=True)
        
    elif st.session_state.pmf_model is not None:
        st.info("💡 减排模拟将在模型运行后自动执行")
        st.warning("⚠️ 请先运行模型以进行减排模拟分析")
    else:
        st.info("👈 请先加载数据并运行模型")

with tab9:
    st.markdown('<h2 class="section-header">🌤️ 天气归因分析</h2>', unsafe_allow_html=True)
    
    if st.session_state.weather_result is not None:
        weather_result = st.session_state.weather_result
        
        st.success("✅ 天气归因分析完成")
        
        st.markdown("---")
        st.subheader("🔥 污染源-气象因子相关性")
        
        fig_corr = plot_weather_correlation(weather_result.source_weather_correlation)
        st.plotly_chart(fig_corr, use_container_width=True)
        
        st.markdown("---")
        st.subheader("📋 显著影响因子")
        
        for source, factors in weather_result.significant_weather_factors.items():
            if len(factors) > 0:
                st.info(f"**{source}**: 受 {', '.join(factors)} 等气象因子显著影响")
            else:
                st.info(f"**{source}**: 未检测到显著影响的气象因子")
        
        st.markdown("---")
        st.subheader("🌡️ 季节变化分析")
        
        fig_seasonal = plot_seasonal_variation(weather_result.seasonal_analysis)
        st.plotly_chart(fig_seasonal, use_container_width=True)
        
        st.markdown("---")
        st.subheader("📊 季节贡献摘要")
        seasonal_summary = get_seasonal_summary(weather_result.seasonal_analysis)
        st.dataframe(seasonal_summary, use_container_width=True)
        
        st.markdown("---")
        st.subheader("💨 风向影响分析（风向玫瑰图）")
        
        selected_source_wind = st.selectbox(
            "选择污染源查看风向影响",
            weather_result.wind_rose_data.keys(),
            index=0
        )
        
        if selected_source_wind in weather_result.wind_rose_data:
            wind_data = weather_result.wind_rose_data[selected_source_wind]
            if len(wind_data) > 0:
                fig_wind = plot_wind_rose(wind_data, selected_source_wind)
                st.plotly_chart(fig_wind, use_container_width=True)
            else:
                st.info("该污染源无风向影响数据")
        
        st.markdown("---")
        st.subheader("📈 气象因子分层分析")
        
        selected_weather_factor = st.selectbox(
            "选择气象因子查看分层贡献",
            list(weather_result.weather_source_contribution.keys()),
            index=0
        )
        
        if selected_weather_factor in weather_result.weather_source_contribution:
            weather_df = weather_result.weather_source_contribution[selected_weather_factor]
            
            fig_weather = go.Figure()
            for i, source in enumerate(weather_df['污染源'].unique()):
                source_data = weather_df[weather_df['污染源'] == source]
                fig_weather.add_trace(go.Bar(
                    x=source_data['分类'],
                    y=source_data['平均贡献'],
                    name=source,
                    marker_color=COLORS[i % len(COLORS)],
                    opacity=0.85,
                    error_y=dict(
                        type='data',
                        array=source_data['贡献标准差'],
                        visible=True
                    )
                ))
            
            fig_weather.update_layout(
                title=f'{selected_weather_factor} 分层污染源贡献',
                xaxis_title='分层区间',
                yaxis_title='平均源贡献浓度 (μg/m³)',
                barmode='group',
                height=500,
                template='plotly_white',
                legend=dict(
                    orientation='h',
                    yanchor='bottom',
                    y=1.02,
                    xanchor='right',
                    x=1
                )
            )
            st.plotly_chart(fig_weather, use_container_width=True)
            
            st.dataframe(
                weather_df.style.format({
                    '平均贡献': '{:.2f}',
                    '贡献标准差': '{:.2f}',
                    '中位数贡献': '{:.2f}'
                }),
                use_container_width=True
            )
        
    elif st.session_state.pmf_model is not None:
        st.info("💡 天气归因分析将在模型运行后自动执行")
        st.warning("⚠️ 请先运行模型以进行天气归因分析")
    else:
        st.info("👈 请先加载数据并运行模型")

st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #888; padding: 1rem;">
    <p>🌫️ 空气污染源解析系统 v1.0 | 基于PMF正定矩阵因子分解模型</p>
    <p style="font-size: 0.8rem;">支持PM2.5、PM10、NO2、SO2、O3等污染物的污染源解析</p>
</div>
""", unsafe_allow_html=True)
