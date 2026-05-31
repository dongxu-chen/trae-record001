import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from train_model import SalaryPredictor
from feature_engineering import LOCATIONS, COMPANY_SIZES, EDUCATION_LEVELS

st.set_page_config(
    page_title="招聘岗位薪资预测系统",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="expanded"
)

@st.cache_resource(show_spinner=False)
def load_model():
    try:
        predictor = SalaryPredictor()
        predictor.load()
        return predictor, True
    except:
        return None, False

@st.cache_data(show_spinner=False)
def load_data():
    if os.path.exists("job_salary_data.csv"):
        return pd.read_csv("job_salary_data.csv", encoding="utf-8-sig")
    return None

def train_model_if_needed():
    if not os.path.exists("models") or not os.path.exists("models/model_lower.pkl"):
        with st.spinner("正在训练模型，请稍候..."):
            from generate_data import generate_dataset
            from train_model import SalaryPredictor
            
            df = generate_dataset(5000)
            df.to_csv("job_salary_data.csv", index=False, encoding="utf-8-sig")
            
            predictor = SalaryPredictor()
            predictor.train(df)
            
            st.success("模型训练完成！")
            st.rerun()

def main():
    st.title("💰 招聘岗位薪资预测系统")
    st.markdown("---")
    
    train_model_if_needed()
    
    predictor, model_loaded = load_model()
    df = load_data()
    
    if not model_loaded or predictor is None:
        st.error("模型加载失败，请刷新页面重试。")
        return
    
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
            placeholder="请输入岗位描述，包括职责、要求、技能等信息..."
        )
        
        check_anomaly = st.checkbox("启用薪资异常检测", value=False)
        
        actual_lower = None
        actual_upper = None
        if check_anomaly:
            st.markdown("### 实际薪资（用于异常检测）")
            actual_lower = st.number_input("实际薪资下限（元）", min_value=0, value=10000, step=1000)
            actual_upper = st.number_input("实际薪资上限（元）", min_value=0, value=20000, step=1000)
        
        predict_button = st.button("🔍 预测薪资", type="primary", use_container_width=True)
    
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
        
        with st.spinner("正在分析..."):
            result = predictor.predict(input_data)
            
            X = predictor.feature_engineer.transform(input_data)
            shap_result = predictor.get_shap_analysis(X, 0)
            
            importance = predictor.get_feature_importance(top_n=15)
        
        col1, col2 = st.columns([1, 1])
        
        with col1:
            st.subheader("📊 薪资预测结果")
            
            pred_lower = result["预测薪资下限"].values[0]
            pred_upper = result["预测薪资上限"].values[0]
            pred_mean = result["预测薪资均值"].values[0]
            
            fig = go.Figure()
            
            fig.add_trace(go.Indicator(
                mode="number",
                value=pred_mean,
                title={"text": "预测薪资均值", "font": {"size": 20}},
                number={"prefix": "¥", "suffix": " 元/月", "font": {"size": 40}},
                domain={'row': 0, 'column': 0}
            ))
            
            fig.update_layout(height=200, margin=dict(l=20, r=20, t=40, b=20))
            st.plotly_chart(fig, use_container_width=True)
            
            st.markdown("### 薪资区间")
            col_lower, col_upper = st.columns(2)
            with col_lower:
                st.metric("预测下限", f"¥{pred_lower:,} 元/月")
            with col_upper:
                st.metric("预测上限", f"¥{pred_upper:,} 元/月")
            
            fig_range = go.Figure()
            fig_range.add_trace(go.Bar(
                y=["薪资范围"],
                x=[pred_upper - pred_lower],
                base=pred_lower,
                orientation='h',
                marker_color='rgba(55, 83, 109, 0.7)',
                name='薪资范围'
            ))
            fig_range.add_trace(go.Scatter(
                y=["薪资范围"],
                x=[pred_mean],
                mode='markers',
                marker=dict(size=15, color='red'),
                name='均值'
            ))
            fig_range.update_layout(
                height=150,
                showlegend=True,
                xaxis_title="薪资（元/月）",
                margin=dict(l=20, r=20, t=20, b=20)
            )
            st.plotly_chart(fig_range, use_container_width=True)
        
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
            st.subheader("📈 特征重要性")
            
            importance_df = importance["importance_df"]
            
            fig_importance = px.bar(
                importance_df.head(10),
                x="importance",
                y="feature",
                orientation='h',
                title="Top 10 特征重要性（XGBoost）",
                labels={"importance": "重要性", "feature": "特征"},
                color="importance",
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
            st.subheader("⚠️ 薪资异常检测")
            
            anomaly_data = input_data.copy()
            anomaly_data["薪资下限"] = actual_lower
            anomaly_data["薪资上限"] = actual_upper
            
            anomaly_result = predictor.detect_anomaly(anomaly_data)
            
            anomaly_type = anomaly_result["异常类型"].values[0]
            is_anomaly = anomaly_result["是否异常(Z分数)"].values[0]
            
            if is_anomaly:
                if anomaly_type == "薪资偏高":
                    st.warning(f"⚠️ 检测结果：{anomaly_type}，该薪资水平显著高于市场预期")
                else:
                    st.warning(f"⚠️ 检测结果：{anomaly_type}，该薪资水平显著低于市场预期")
            else:
                st.success("✅ 检测结果：薪资正常，该薪资水平符合市场预期")
            
            col_anomaly1, col_anomaly2, col_anomaly3 = st.columns(3)
            with col_anomaly1:
                st.metric("实际薪资均值", f"¥{(actual_lower + actual_upper) // 2:,}")
            with col_anomaly2:
                st.metric("预测薪资均值", f"¥{pred_mean:,}")
            with col_anomaly3:
                diff = ((actual_lower + actual_upper) / 2) - pred_mean
                st.metric("差异", f"¥{diff:,.0f}", f"{diff/pred_mean:.1%}")
            
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
            
            st.markdown("### 📍 各地区平均薪资")
            location_stats = df.groupby("地区").agg({
                "薪资下限": "mean",
                "薪资上限": "mean"
            }).reset_index()
            location_stats["平均薪资"] = (location_stats["薪资下限"] + location_stats["薪资上限"]) / 2
            location_stats = location_stats.sort_values("平均薪资", ascending=False)
            
            fig_loc = px.bar(
                location_stats,
                x="地区",
                y="平均薪资",
                title="各地区平均薪资对比",
                color="平均薪资",
                color_continuous_scale='Blues'
            )
            fig_loc.update_layout(height=400)
            st.plotly_chart(fig_loc, use_container_width=True)
            
            st.markdown("### 🎓 不同学历平均薪资")
            edu_stats = df.groupby("学历要求").agg({
                "薪资下限": "mean",
                "薪资上限": "mean"
            }).reset_index()
            edu_stats["平均薪资"] = (edu_stats["薪资下限"] + edu_stats["薪资上限"]) / 2
            
            fig_edu = px.bar(
                edu_stats,
                x="学历要求",
                y=["薪资下限", "薪资上限"],
                title="不同学历薪资范围",
                barmode="group"
            )
            fig_edu.update_layout(height=400, yaxis_title="薪资（元/月）")
            st.plotly_chart(fig_edu, use_container_width=True)

if __name__ == "__main__":
    main()
