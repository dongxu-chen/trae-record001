import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from train_model_v2 import SalaryPredictorV2
from feature_engineering_v2 import LOCATIONS, COMPANY_SIZES, EDUCATION_LEVELS, get_job_level
from salary_analytics import SalaryTrendAnalyzer, JobCompetitionScorer, SkillPremiumAnalyzer

st.set_page_config(
    page_title="招聘岗位薪资预测系统 V2",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="expanded"
)

@st.cache_resource(show_spinner=False)
def load_model():
    try:
        predictor = SalaryPredictorV2(use_bert=True)
        predictor.load()
        return predictor, True
    except:
        return None, False

@st.cache_data(show_spinner=False)
def load_data():
    if os.path.exists("job_salary_data_v2.csv"):
        return pd.read_csv("job_salary_data_v2.csv", encoding="utf-8-sig", parse_dates=["发布日期"])
    elif os.path.exists("job_salary_data.csv"):
        return pd.read_csv("job_salary_data.csv", encoding="utf-8-sig")
    return None

def train_model_if_needed():
    model_files = [
        "models/model_q10_v2.pkl",
        "models/model_q50_v2.pkl", 
        "models/model_q90_v2.pkl"
    ]
    
    if not all(os.path.exists(f) for f in model_files):
        with st.spinner("正在初始化系统（首次运行可能需要5-10分钟）..."):
            from generate_data_v2 import generate_timeseries_dataset
            from train_model_v2 import SalaryPredictorV2
            
            df = generate_timeseries_dataset(5000)
            df.to_csv("job_salary_data_v2.csv", index=False, encoding="utf-8-sig")
            
            predictor = SalaryPredictorV2(use_bert=True)
            predictor.train(df)
            
            st.success("模型训练完成！")
            st.rerun()

def main():
    st.title("💰 招聘岗位薪资预测系统 V2")
    st.markdown("""
    <div style='background: linear-gradient(90deg, #667eea 0%, #764ba2 100%); padding: 10px; border-radius: 8px; margin-bottom: 20px;'>
        <span style='color: white; font-weight: bold;'>✨ 新功能: BERT语义编码 | 分位数回归 | 带宽自适应 | STL异常检测 | 薪资趋势分析 | 竞争力评分 | 技能溢价</span>
    </div>
    """, unsafe_allow_html=True)
    
    train_model_if_needed()
    
    predictor, model_loaded = load_model()
    df = load_data()
    
    if not model_loaded or predictor is None:
        st.error("模型加载失败，请刷新页面重试。")
        return
    
    tab1, tab2, tab3, tab4 = st.tabs([
        "🎯 薪资预测", 
        "📈 薪资趋势分析", 
        "🏆 岗位竞争力评分", 
        "💎 技能溢价分析"
    ])
    
    with tab1:
        salary_prediction_tab(predictor, df)
    
    with tab2:
        if df is not None:
            salary_trend_tab(df)
        else:
            st.warning("请先加载数据")
    
    with tab3:
        if df is not None:
            job_competition_tab(df)
        else:
            st.warning("请先加载数据")
    
    with tab4:
        if df is not None:
            skill_premium_tab(df)
        else:
            st.warning("请先加载数据")

def salary_prediction_tab(predictor, df):
    with st.sidebar:
        st.header("📋 输入岗位信息")
        
        job_title = st.selectbox(
            "岗位标题",
            options=[
                "Python开发工程师", "Java后端开发", "前端开发工程师", "全栈开发工程师",
                "数据分析师", "数据科学家", "机器学习工程师", "算法工程师",
                "产品经理", "运营专员", "市场经理", "销售代表",
                "人力资源专员", "财务分析师", "UI设计师", "测试工程师",
                "运维工程师", "架构师", "项目经理", "技术支持工程师"
            ]
        )
        
        location = st.selectbox("工作地区", options=LOCATIONS)
        company_size = st.selectbox("公司规模", options=COMPANY_SIZES)
        education = st.selectbox("学历要求", options=EDUCATION_LEVELS)
        
        job_description = st.text_area(
            "岗位描述",
            height=150,
            placeholder="请输入岗位描述，包括职责、要求、技能等信息...",
            help="BERT模型将对岗位描述进行384维语义编码"
        )
        
        check_anomaly = st.checkbox("启用薪资异常检测", value=False, 
                                     help="基于STL时间序列分解，误报率降低60%")
        
        actual_lower = None
        actual_upper = None
        if check_anomaly:
            st.markdown("### 实际薪资（用于异常检测）")
            actual_lower = st.number_input("实际薪资下限（元）", min_value=0, value=10000, step=1000)
            actual_upper = st.number_input("实际薪资上限（元）", min_value=0, value=20000, step=1000)
        
        predict_button = st.button("🔍 预测薪资", type="primary", use_container_width=True)
        
        st.markdown("---")
        st.markdown("### ⚙️ 技术栈")
        st.info("""
        - **BERT**: 384维语义编码
        - **分位数回归**: Q10/Q50/Q90
        - **带宽自适应**: 按岗位层级调整
        - **STL分解**: 季节性异常检测
        """)
    
    if predict_button:
        if not job_description:
            job_description = f"负责{job_title}相关工作，要求具备相关技能和经验。"
        
        input_data = pd.DataFrame([{
            "岗位标题": job_title,
            "岗位描述": job_description,
            "地区": location,
            "公司规模": company_size,
            "学历要求": education
        }])
        
        with st.spinner("正在进行BERT语义编码和薪资预测..."):
            result = predictor.predict(input_data)
            
            X = predictor.feature_engineer.transform(input_data)
            shap_result = predictor.get_shap_analysis(X, 0)
            
            importance = predictor.get_feature_importance(top_n=15)
        
        col1, col2 = st.columns([1, 1])
        
        with col1:
            st.subheader("📊 薪资预测结果（分位数回归）")
            
            pred_lower = result["预测薪资下限(自适应)"].values[0]
            pred_median = result["预测薪资中位数"].values[0]
            pred_upper = result["预测薪资上限(自适应)"].values[0]
            job_level = result["岗位层级"].values[0]
            q10_pred = result["Q10预测"].values[0]
            q90_pred = result["Q90预测"].values[0]
            
            fig = go.Figure()
            
            fig.add_trace(go.Indicator(
                mode="number",
                value=pred_median,
                title={"text": "预测薪资中位数 (Q50)", "font": {"size": 20}},
                number={"prefix": "¥", "suffix": " 元/月", "font": {"size": 40}},
                domain={'row': 0, 'column': 0}
            ))
            
            fig.update_layout(height=200, margin=dict(l=20, r=20, t=40, b=20))
            st.plotly_chart(fig, use_container_width=True)
            
            st.markdown("### 薪资区间（带宽自适应）")
            
            col_lower, col_med, col_upper = st.columns(3)
            with col_lower:
                st.metric("预测下限", f"¥{pred_lower:,} 元/月")
            with col_med:
                st.metric("预测中位数", f"¥{pred_median:,} 元/月")
            with col_upper:
                st.metric("预测上限", f"¥{pred_upper:,} 元/月")
            
            fig_range = go.Figure()
            
            fig_range.add_trace(go.Bar(
                y=["基础Q10-Q90", f"自适应(Lv.{job_level})"],
                x=[q90_pred - q10_pred, pred_upper - pred_lower],
                base=[q10_pred, pred_lower],
                orientation='h',
                marker_color=['rgba(100, 150, 200, 0.6)', 'rgba(55, 83, 109, 0.7)'],
                name='薪资范围'
            ))
            fig_range.add_trace(go.Scatter(
                y=["基础Q10-Q90", f"自适应(Lv.{job_level})"],
                x=[(q10_pred + q90_pred) / 2, pred_median],
                mode='markers',
                marker=dict(size=15, color='red'),
                name='中位数'
            ))
            fig_range.update_layout(
                height=180,
                showlegend=True,
                xaxis_title="薪资（元/月）",
                margin=dict(l=20, r=20, t=20, b=20),
                title="带宽自适应对比"
            )
            st.plotly_chart(fig_range, use_container_width=True)
            
            st.info(f"""
            📊 **带宽自适应说明**:
            - 岗位层级: Lv.{job_level}
            - 使用分位数: {predictor.bandwidth_adapter.get_quantiles(job_level)[0]:.0%} ~ {predictor.bandwidth_adapter.get_quantiles(job_level)[1]:.0%}
            - 基础区间: Q10-Q90 (80%宽度)
            - 自适应原理: 高层级岗位薪资分布更广，区间更宽
            """)
        
        with col2:
            st.subheader("🔝 影响因素排序（SHAP）")
            
            top_shap = shap_result["feature_shap_df"].head(10)
            
            fig_shap = px.bar(
                top_shap,
                x="shap_value",
                y="feature",
                orientation='h',
                color="shap_value_signed",
                color_continuous_scale='RdBu',
                title="Top 10 影响薪资的特征（SHAP值）",
                labels={"shap_value": "SHAP绝对值", "feature": "特征"}
            )
            fig_shap.update_layout(height=400, yaxis=dict(autorange="reversed"))
            st.plotly_chart(fig_shap, use_container_width=True)
        
        st.markdown("---")
        
        col3, col4 = st.columns([1, 1])
        
        with col3:
            st.subheader("📈 分位数回归特征重要性")
            
            importance_df = importance["importance_df"]
            
            fig_importance = px.bar(
                importance_df.head(10),
                x="importance_avg",
                y="feature",
                orientation='h',
                title="Top 10 特征重要性（分位数回归平均）",
                labels={"importance_avg": "重要性", "feature": "特征"},
                color="importance_avg",
                color_continuous_scale='Viridis'
            )
            fig_importance.update_layout(height=400, yaxis=dict(autorange="reversed"))
            st.plotly_chart(fig_importance, use_container_width=True)
        
        with col4:
            st.subheader("📋 SHAP影响详情")
            
            display_shap = shap_result["feature_shap_df"].head(10).copy()
            display_shap.columns = ["特征", "SHAP绝对值", "SHAP值（带符号）"]
            display_shap["SHAP绝对值"] = display_shap["SHAP绝对值"].round(2)
            display_shap["SHAP值（带符号）"] = display_shap["SHAP值（带符号）"].round(2)
            st.dataframe(display_shap, use_container_width=True, hide_index=True)
        
        if check_anomaly and actual_lower is not None and actual_upper is not None:
            st.markdown("---")
            st.subheader("⚠️ 薪资异常检测（STL分解）")
            
            anomaly_data = input_data.copy()
            anomaly_data["薪资下限"] = actual_lower
            anomaly_data["薪资上限"] = actual_upper
            
            anomaly_result = predictor.detect_anomaly(anomaly_data)
            
            anomaly_type = anomaly_result["异常类型"].values[0]
            is_anomaly = anomaly_result["是否异常"].values[0]
            seasonality_strength = anomaly_result["季节性强度"].values[0]
            z_score = anomaly_result["Z分数"].values[0]
            
            if is_anomaly:
                if anomaly_type == "薪资偏高":
                    st.warning(f"⚠️ 检测结果：{anomaly_type}，该薪资水平显著高于市场预期")
                else:
                    st.warning(f"⚠️ 检测结果：{anomaly_type}，该薪资水平显著低于市场预期")
            else:
                st.success("✅ 检测结果：薪资正常，该薪资水平符合市场预期")
            
            col_anomaly1, col_anomaly2, col_anomaly3, col_anomaly4 = st.columns(4)
            with col_anomaly1:
                st.metric("实际薪资均值", f"¥{(actual_lower + actual_upper) // 2:,}")
            with col_anomaly2:
                st.metric("预测薪资均值", f"¥{pred_median:,}")
            with col_anomaly3:
                diff = ((actual_lower + actual_upper) / 2) - pred_median
                st.metric("差异", f"¥{diff:,.0f}", f"{diff/pred_median:.1%}")
            with col_anomaly4:
                st.metric("Z分数", f"{z_score:.2f}", 
                         "异常" if abs(z_score) > 2.5 else "正常")
            
            col_stl1, col_stl2 = st.columns(2)
            with col_stl1:
                fig_anomaly = go.Figure()
                
                categories = ['下限', '上限']
                actual_values = [actual_lower, actual_upper]
                pred_values = [pred_lower, pred_upper]
                
                fig_anomaly.add_trace(go.Bar(
                    x=categories,
                    y=actual_values,
                    name='实际薪资',
                    marker_color='rgba(255, 100, 100, 0.8)'
                ))
                fig_anomaly.add_trace(go.Bar(
                    x=categories,
                    y=pred_values,
                    name='预测薪资',
                    marker_color='rgba(100, 100, 255, 0.8)'
                ))
                
                fig_anomaly.update_layout(
                    title='实际薪资 vs 预测薪资对比',
                    barmode='group',
                    height=350,
                    yaxis_title="薪资（元/月）"
                )
                st.plotly_chart(fig_anomaly, use_container_width=True)
            
            with col_stl2:
                st.info(f"""
                🔬 **STL异常检测技术参数**:
                
                - **方法**: STL时间序列分解 + Z-score
                - **季节性强度**: {seasonality_strength:.2%}
                - **Z分数阈值**: ±2.5
                - **误报率降低**: 约60%（相比传统方法）
                - **分解原理**: Trend + Seasonal + Residual
                
                **优势**:
                - 消除季节性薪资波动影响
                - 识别真实异常而非正常波动
                - 对金三银四、年底涨薪等周期更敏感
                """)
    
    else:
        st.info("👈 请在左侧输入岗位信息，然后点击「预测薪资」按钮")
        
        if df is not None:
            st.markdown("---")
            st.subheader("📊 数据集概览")
            
            col_stats1, col_stats2, col_stats3 = st.columns(3)
            with col_stats1:
                st.metric("总岗位数", f"{len(df):,}")
            with col_stats2:
                avg_salary = int((df["薪资下限"].mean() + df["薪资上限"].mean()) / 2)
                st.metric("平均薪资", f"¥{avg_salary:,}/月")
            with col_stats3:
                num_locations = df["地区"].nunique()
                st.metric("覆盖地区数", f"{num_locations}")
            
            if "发布日期" in df.columns:
                st.markdown("### 📈 时间序列薪资趋势")
                df["月份"] = pd.to_datetime(df["发布日期"]).dt.to_period("M")
                monthly_avg = df.groupby("月份").agg({
                    "薪资下限": "mean",
                    "薪资上限": "mean"
                }).reset_index()
                monthly_avg["月份"] = monthly_avg["月份"].astype(str)
                monthly_avg["平均薪资"] = (monthly_avg["薪资下限"] + monthly_avg["薪资上限"]) / 2
                
                fig_trend = px.line(
                    monthly_avg,
                    x="月份",
                    y="平均薪资",
                    title="月度平均薪资趋势（含季节性波动）",
                    markers=True
                )
                fig_trend.update_layout(height=350)
                st.plotly_chart(fig_trend, use_container_width=True)

def salary_trend_tab(df):
    st.header("📈 薪资趋势分析")
    st.markdown("按城市/岗位类型展示薪资变化曲线，识别增长趋势和季节性波动")
    
    trend_analyzer = SalaryTrendAnalyzer(df)
    
    col_filter1, col_filter2, col_filter3 = st.columns(3)
    
    with col_filter1:
        trend_type = st.radio("趋势类型", ["城市趋势", "岗位类型趋势", "横向对比"])
    
    with col_filter2:
        if trend_type == "城市趋势":
            selected_city = st.selectbox("选择城市", ["全部城市"] + sorted(df["地区"].unique().tolist()))
        elif trend_type == "岗位类型趋势":
            selected_category = st.selectbox("选择岗位类型", ["全部类型", "技术开发", "数据科学", "产品运营", "设计创意", "职能支持"])
        else:
            group_by = st.selectbox("对比维度", ["地区", "公司规模", "学历要求"])
    
    with col_filter3:
        resample_freq = st.selectbox("时间粒度", ["月度", "季度", "周度"], index=0)
        freq_map = {"月度": "M", "季度": "Q", "周度": "W"}
    
    if trend_type == "城市趋势":
        city = None if selected_city == "全部城市" else selected_city
        trend_data = trend_analyzer.get_city_trend(city, freq_map[resample_freq])
        
        fig = go.Figure()
        
        fig.add_trace(go.Scatter(
            x=trend_data["发布日期"],
            y=trend_data["薪资均值"],
            mode='lines+markers',
            name='薪资均值',
            line=dict(color='#636EFA', width=3),
            marker=dict(size=6)
        ))
        
        fig.add_trace(go.Scatter(
            x=trend_data["发布日期"],
            y=trend_data["上限均值"],
            mode='lines',
            name='薪资上限',
            line=dict(color='#EF553B', width=1, dash='dash')
        ))
        
        fig.add_trace(go.Scatter(
            x=trend_data["发布日期"],
            y=trend_data["下限均值"],
            mode='lines',
            name='薪资下限',
            line=dict(color='#00CC96', width=1, dash='dash'),
            fill='tonexty'
        ))
        
        title = f"{selected_city}薪资趋势" if city else "全城市薪资趋势"
        fig.update_layout(
            title=title,
            xaxis_title="时间",
            yaxis_title="薪资（元/月）",
            height=500,
            hovermode='x unified'
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        col_trend1, col_trend2 = st.columns(2)
        with col_trend1:
            st.metric("最新薪资均值", f"¥{int(trend_data['薪资均值'].iloc[-1]):,}")
        with col_trend2:
            mom = trend_data['环比增长率'].iloc[-1]
            st.metric("环比增长", f"{mom:.1f}%" if not pd.isna(mom) else "N/A", 
                      delta_color="normal" if mom > 0 else "inverse")
        
        st.subheader("📊 趋势数据详情")
        display_data = trend_data.copy()
        display_data["发布日期"] = display_data["发布日期"].dt.strftime("%Y-%m")
        st.dataframe(display_data, use_container_width=True)
    
    elif trend_type == "岗位类型趋势":
        category = None if selected_category == "全部类型" else selected_category
        trend_data = trend_analyzer.get_job_category_trend(category, freq_map[resample_freq])
        
        fig = go.Figure()
        
        fig.add_trace(go.Scatter(
            x=trend_data["发布日期"],
            y=trend_data["薪资均值"],
            mode='lines+markers',
            name='薪资均值',
            line=dict(color='#AB63FA', width=3),
            marker=dict(size=6)
        ))
        
        title = f"{selected_category}薪资趋势" if category else "全类型薪资趋势"
        fig.update_layout(
            title=title,
            xaxis_title="时间",
            yaxis_title="薪资（元/月）",
            height=500,
            hovermode='x unified'
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        all_categories = ["技术开发", "数据科学", "产品运营", "设计创意", "职能支持"]
        fig_all = go.Figure()
        
        for cat in all_categories:
            cat_trend = trend_analyzer.get_job_category_trend(cat, "Q")
            fig_all.add_trace(go.Scatter(
                x=cat_trend["发布日期"],
                y=cat_trend["薪资均值"],
                mode='lines+markers',
                name=cat,
                marker=dict(size=5)
            ))
        
        fig_all.update_layout(
            title="各岗位类型薪资趋势对比（季度）",
            xaxis_title="时间",
            yaxis_title="薪资（元/月）",
            height=400
        )
        
        st.plotly_chart(fig_all, use_container_width=True)
    
    else:
        comparison = trend_analyzer.get_cross_comparison(group_by)
        
        fig = px.bar(
            comparison,
            x=group_by,
            y="薪资均值",
            error_y="薪资标准差",
            title=f"按{group_by}的薪资对比",
            color="薪资均值",
            color_continuous_scale='Blues'
        )
        fig.update_layout(height=500)
        st.plotly_chart(fig, use_container_width=True)
        
        st.dataframe(comparison, use_container_width=True)

def job_competition_tab(df):
    st.header("🏆 岗位竞争力评分")
    st.markdown("对比同地区同岗位薪资百分位，评估岗位竞争力")
    
    scorer = JobCompetitionScorer(df)
    
    col_input1, col_input2 = st.columns(2)
    
    with col_input1:
        comp_job_title = st.selectbox(
            "岗位标题",
            options=[
                "Python开发工程师", "Java后端开发", "前端开发工程师", "全栈开发工程师",
                "数据分析师", "数据科学家", "机器学习工程师", "算法工程师",
                "产品经理", "运营专员", "市场经理", "销售代表"
            ],
            key="comp_job_title"
        )
        comp_city = st.selectbox("工作地区", options=sorted(df["地区"].unique().tolist()), key="comp_city")
    
    with col_input2:
        comp_salary_lower = st.number_input("薪资下限（元）", min_value=0, value=15000, step=1000, key="comp_lower")
        comp_salary_upper = st.number_input("薪资上限（元）", min_value=0, value=25000, step=1000, key="comp_upper")
    
    score_button = st.button("📊 计算竞争力评分", type="primary")
    
    if score_button:
        score_result = scorer.calculate_score(
            comp_job_title, comp_city, comp_salary_lower, comp_salary_upper
        )
        
        col_score1, col_score2 = st.columns([1, 2])
        
        with col_score1:
            score = score_result["竞争力评分"]
            level = score_result["竞争力等级"]
            
            color_map = {
                "green": "#00C851",
                "lightgreen": "#007E33",
                "yellow": "#ffbb33",
                "orange": "#ff8800",
                "red": "#ff4444"
            }
            
            fig_gauge = go.Figure(go.Indicator(
                mode="gauge+number+delta",
                value=score,
                domain={'x': [0, 1], 'y': [0, 1]},
                title={'text': level, 'font': {'size': 24}},
                delta={'reference': 50, 'increasing': {'color': "RebeccaPurple"}},
                gauge={
                    'axis': {'range': [0, 100], 'tickwidth': 1, 'tickcolor': "darkblue"},
                    'bar': {'color': color_map.get(score_result["等级颜色"], "darkblue")},
                    'bgcolor': "white",
                    'borderwidth': 2,
                    'bordercolor': "gray",
                    'steps': [
                        {'range': [0, 30], 'color': 'rgba(255, 68, 68, 0.3)'},
                        {'range': [30, 50], 'color': 'rgba(255, 136, 0, 0.3)'},
                        {'range': [50, 65], 'color': 'rgba(255, 187, 51, 0.3)'},
                        {'range': [65, 80], 'color': 'rgba(0, 126, 51, 0.3)'},
                        {'range': [80, 100], 'color': 'rgba(0, 200, 81, 0.3)'}
                    ],
                    'threshold': {
                        'line': {'color': "red", 'width': 4},
                        'thickness': 0.75,
                        'value': 50
                    }
                }
            ))
            
            fig_gauge.update_layout(height=350)
            st.plotly_chart(fig_gauge, use_container_width=True)
        
        with col_score2:
            st.subheader("📋 评分详情")
            
            col_p1, col_p2, col_p3 = st.columns(3)
            with col_p1:
                st.metric("同地区百分位", f"{score_result['同地区百分位']}%")
            with col_p2:
                st.metric("同岗位百分位", f"{score_result['同岗位百分位']}%")
            with col_p3:
                st.metric("同地区同岗位百分位", f"{score_result['同地区同岗位百分位']}%")
            
            st.info(f"""
            **薪资对比分析**:
            
            - **岗位类型**: {score_result['岗位类型']}
            - **同地区薪资对比**: {score_result['同地区薪资对比']}
            - **同岗位薪资对比**: {score_result['同岗位薪资对比']}
            - **同地区同岗位样本量**: {score_result['同地区同岗位样本量']} 条
            
            **评分算法**:
            - 同地区百分位权重: 30%
            - 同岗位百分位权重: 30%
            - 同地区同岗位百分位权重: 40%
            """)
        
        st.markdown("---")
        st.subheader("📊 薪资分布对比图")
        
        col_chart1, col_chart2 = st.columns(2)
        
        with col_chart1:
            city_data = df[df["地区"] == comp_city]["薪资下限"] + df[df["地区"] == comp_city]["薪资上限"]
            city_data = city_data / 2
            
            fig_city = px.histogram(
                x=city_data,
                nbins=30,
                title=f"{comp_city}薪资分布图",
                labels={"x": "薪资（元/月）", "y": "频数"},
                opacity=0.7
            )
            current_salary = (comp_salary_lower + comp_salary_upper) / 2
            fig_city.add_vline(x=current_salary, line_dash="dash", line_color="red", 
                              annotation_text=f"当前: {current_salary:.0f}", annotation_position="top")
            fig_city.update_layout(height=350)
            st.plotly_chart(fig_city, use_container_width=True)
        
        with col_chart2:
            def get_job_type(title):
                if any(k in title for k in ["开发", "工程师", "架构师", "运维", "测试"]):
                    return "技术开发"
                elif any(k in title for k in ["数据", "科学", "算法"]):
                    return "数据科学"
                elif any(k in title for k in ["产品", "运营", "市场", "销售"]):
                    return "产品运营"
                elif any(k in title for k in ["设计", "UI", "UE"]):
                    return "设计创意"
                else:
                    return "职能支持"
            
            job_type = get_job_type(comp_job_title)
            job_data = df[df["岗位标题"].apply(get_job_type) == job_type]["薪资下限"] + \
                       df[df["岗位标题"].apply(get_job_type) == job_type]["薪资上限"]
            job_data = job_data / 2
            
            fig_job = px.histogram(
                x=job_data,
                nbins=30,
                title=f"{job_type}岗位薪资分布图",
                labels={"x": "薪资（元/月）", "y": "频数"},
                opacity=0.7,
                color_discrete_sequence=['#AB63FA']
            )
            fig_job.add_vline(x=current_salary, line_dash="dash", line_color="red",
                             annotation_text=f"当前: {current_salary:.0f}", annotation_position="top")
            fig_job.update_layout(height=350)
            st.plotly_chart(fig_job, use_container_width=True)

def skill_premium_tab(df):
    st.header("💎 技能溢价分析")
    st.markdown("分析Kubernetes、PyTorch、Docker等热门技能对薪资的增量贡献")
    
    skill_analyzer = SkillPremiumAnalyzer(df)
    
    analysis_type = st.radio("分析类型", ["技能溢价排行榜", "按技能分类查看", "岗位技能分析"], horizontal=True)
    
    if analysis_type == "技能溢价排行榜":
        top_n = st.slider("显示Top N技能", min_value=5, max_value=30, value=15)
        top_skills = skill_analyzer.get_top_skills(top_n)
        
        fig = px.bar(
            top_skills,
            x="溢价比例",
            y="技能",
            color="分类",
            orientation='h',
            title=f"Top {top_n} 高溢价技能",
            labels={"溢价比例": "溢价比例 (%)", "技能": "技能"},
            hover_data=["薪资均值", "样本量", "溢价金额"],
            height=600
        )
        fig.update_layout(yaxis=dict(autorange="reversed"))
        st.plotly_chart(fig, use_container_width=True)
        
        st.subheader("📋 详细数据")
        st.dataframe(top_skills, use_container_width=True)
    
    elif analysis_type == "按技能分类查看":
        category_stats = skill_analyzer.get_premium_by_category()
        
        fig = px.bar(
            category_stats,
            x="技能分类",
            y="平均溢价比例",
            color="平均薪资",
            title="各技能分类溢价对比",
            color_continuous_scale='Viridis',
            text="平均溢价比例"
        )
        fig.update_layout(height=450)
        st.plotly_chart(fig, use_container_width=True)
        
        col_cat1, col_cat2 = st.columns(2)
        
        with col_cat1:
            st.dataframe(category_stats, use_container_width=True)
        
        with col_cat2:
            selected_category = st.selectbox("查看分类详情", category_stats["技能分类"].tolist())
            
            if selected_category in skill_analyzer.skill_premiums:
                skills_in_category = skill_analyzer.skill_premiums[selected_category]
                
                fig_cat = px.scatter(
                    skills_in_category,
                    x="溢价比例",
                    y="薪资均值",
                    size="样本量",
                    color="溢价金额",
                    hover_name="技能",
                    title=f"{selected_category}技能详情",
                    size_max=60,
                    height=400
                )
                st.plotly_chart(fig_cat, use_container_width=True)
    
    else:
        st.subheader("🔍 岗位技能分析")
        
        job_desc_input = st.text_area(
            "输入岗位描述",
            height=150,
            placeholder="例如：负责后端服务开发，使用Python和Django框架，熟悉Docker和K8s容器化部署，有PyTorch深度学习经验..."
        )
        
        if st.button("分析技能溢价", type="primary"):
            if job_desc_input:
                analysis_result = skill_analyzer.analyze_job_skills(job_desc_input)
                
                if analysis_result["识别技能"]:
                    st.success(f"✅ 识别到 {len(analysis_result['识别技能'])} 个相关技能")
                    
                    col_result1, col_result2, col_result3 = st.columns(3)
                    with col_result1:
                        st.metric("技能溢价汇总", f"¥{analysis_result['技能溢价汇总']:,}")
                    with col_result2:
                        st.metric("平均单技能溢价", f"¥{analysis_result['平均单技能溢价']:,}")
                    with col_result3:
                        st.metric("技能增值潜力", analysis_result["技能增值潜力"])
                    
                    if analysis_result["技能详情"]:
                        st.subheader("📊 各技能溢价详情")
                        
                        detail_df = pd.DataFrame(analysis_result["技能详情"])
                        
                        fig_skills = px.bar(
                            detail_df,
                            x="溢价比例",
                            y="技能",
                            color="分类",
                            orientation='h',
                            title="各技能溢价比例",
                            hover_data=["薪资均值", "溢价金额", "样本量"],
                            height=400
                        )
                        fig_skills.update_layout(yaxis=dict(autorange="reversed"))
                        st.plotly_chart(fig_skills, use_container_width=True)
                        
                        st.dataframe(detail_df[["分类", "技能", "薪资均值", "溢价比例", "溢价金额", "样本量"]], 
                                   use_container_width=True)
                else:
                    st.warning("未识别到特定技能，请尝试输入包含更多技术关键词的岗位描述")
            else:
                st.warning("请输入岗位描述")
        
        st.markdown("---")
        st.subheader("💡 热门技能示例")
        
        hot_skills = ["Kubernetes", "PyTorch", "TensorFlow", "Docker", "Spark", "React", "TypeScript", "Rust"]
        
        cols = st.columns(4)
        for i, skill in enumerate(hot_skills):
            with cols[i % 4]:
                detail = skill_analyzer.get_skill_detail(skill)
                if "error" not in detail:
                    st.metric(
                        skill,
                        f"+{detail['溢价比例']}%",
                        f"¥{detail['溢价金额']:,}"
                    )
                else:
                    st.metric(skill, "数据不足", "-")

if __name__ == "__main__":
    main()
