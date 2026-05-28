import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import joblib
import os
import warnings
warnings.filterwarnings('ignore')

from data_generator import generate_all_data
from model_trainer import (
    build_features, build_monthly_features, train_model,
    get_risk_scores, generate_retention_suggestions, FEATURE_COLS
)
from shap_analyzer import (
    compute_shap_values, get_feature_shap_importance,
    get_top_shap_features, get_employee_shap_contribution,
    get_global_attrribution, get_attrition_factor_summary,
    get_risk_drivers_by_level, FEATURE_NAMES_CN
)
from time_series_analyzer import (
    analyze_department_trends, analyze_company_trends,
    forecast_trend, compute_risk_trend_score, detect_anomalies,
    compute_risk_index
)
from impact_analyzer import (
    assess_departure_impact, assess_team_impact, generate_impact_summary
)
from calibration import (
    compute_calibration_metrics, calibration_over_time,
    compare_actual_vs_predicted, suggest_calibration_adjustment
)
from succession_planner import (
    compute_succession_score, find_replacement_candidates,
    generate_succession_plan, batch_succession_planning
)

st.set_page_config(
    page_title="员工离职倾向分析仪表板",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)


@st.cache_data(show_spinner=False)
def load_or_generate_data():
    csv_files = ['employees.csv', 'attendance.csv', 'emails.csv', 'tasks.csv', 'surveys.csv']
    if all(os.path.exists(f) for f in csv_files):
        return {
            'employees': pd.read_csv('employees.csv', parse_dates=['hire_date']),
            'attendance': pd.read_csv('attendance.csv', parse_dates=['date']),
            'emails': pd.read_csv('emails.csv', parse_dates=['date']),
            'tasks': pd.read_csv('tasks.csv', parse_dates=['week_start', 'week_end']),
            'surveys': pd.read_csv('surveys.csv', parse_dates=['survey_date']),
        }
    return generate_all_data()


@st.cache_resource(show_spinner=False)
def load_or_train_model(data):
    model_path = 'model.joblib'
    scaler_path = 'scaler.joblib'
    if os.path.exists(model_path) and os.path.exists(scaler_path):
        model = joblib.load(model_path)
        scaler = joblib.load(scaler_path)
        df_features, encoders = build_features(data)
        X = df_features[FEATURE_COLS].copy()
        X_scaled = scaler.transform(X)
        X_scaled = pd.DataFrame(X_scaled, columns=FEATURE_COLS)
        _, _, _, _, _, feat_imp = train_model(df_features)
        return model, scaler, df_features, X_scaled, feat_imp
    else:
        df_features, encoders = build_features(data)
        model, scaler, X_train, X_test, y_train, y_test, feat_imp = train_model(df_features)
        X = df_features[FEATURE_COLS].copy()
        X_scaled = scaler.transform(X)
        X_scaled = pd.DataFrame(X_scaled, columns=FEATURE_COLS)
        joblib.dump(model, model_path)
        joblib.dump(scaler, scaler_path)
        return model, scaler, df_features, X_scaled, feat_imp


def sidebar():
    with st.sidebar:
        st.title("📊 控制面板")
        st.markdown("---")

        st.subheader("数据管理")
        if st.button("🔄 重新生成数据", use_container_width=True):
            for f in ['employees.csv', 'attendance.csv', 'emails.csv', 'tasks.csv', 'surveys.csv',
                       'model.joblib', 'scaler.joblib']:
                if os.path.exists(f):
                    os.remove(f)
            st.cache_data.clear()
            st.cache_resource.clear()
            st.success("数据已清除，请刷新页面")
            st.rerun()

        st.markdown("---")
        st.subheader("风险筛选")
        risk_filter = st.multiselect(
            "风险等级",
            options=["高风险", "中高风险", "中低风险", "低风险"],
            default=["高风险", "中高风险"]
        )

        st.markdown("---")
        st.subheader("部门筛选")
        dept_filter = st.multiselect(
            "部门",
            options=["工程部", "销售部", "市场部", "人力资源部", "财务部", "产品部", "客服部"],
            default=[]
        )

        st.markdown("---")
        st.subheader("显示设置")
        show_high_risk_only = st.checkbox("仅显示高风险员工", value=False)
        top_n = st.slider("显示员工数量", 10, 100, 20)

        return risk_filter, dept_filter, show_high_risk_only, top_n


def header_section():
    st.title("🔍 员工离职倾向分析仪表板")
    st.markdown("""
    基于机器学习的员工离职风险预测与归因分析系统
    综合分析考勤、邮件、任务绩效、满意度调查等多维数据
    """)
    st.markdown("---")


def overview_metrics(risk_df):
    total = len(risk_df)
    high_risk = len(risk_df[risk_df['risk_level'] == '高风险'])
    medium_high = len(risk_df[risk_df['risk_level'] == '中高风险'])
    medium_low = len(risk_df[risk_df['risk_level'] == '中低风险'])
    low = len(risk_df[risk_df['risk_level'] == '低风险'])
    avg_risk = risk_df['risk_score'].mean()

    col1, col2, col3, col4, col5, col6 = st.columns(6)
    col1.metric("总员工数", total)
    col2.metric("🔴 高风险", high_risk)
    col3.metric("🟠 中高风险", medium_high)
    col4.metric("🟡 中低风险", medium_low)
    col5.metric("🟢 低风险", low)
    col6.metric("平均风险分", f"{avg_risk:.2f}")


def risk_distribution_chart(risk_df):
    st.subheader("📈 风险分布分析")
    col1, col2 = st.columns(2)

    with col1:
        fig = px.histogram(
            risk_df, x='risk_score', nbins=30,
            title="风险评分分布",
            color_discrete_sequence=['#FF6B6B'],
        )
        fig.update_layout(
            xaxis_title="风险评分",
            yaxis_title="员工数量",
            height=350,
        )
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        risk_counts = risk_df['risk_level'].value_counts().reindex(
            ['高风险', '中高风险', '中低风险', '低风险']
        )
        colors = ['#FF4444', '#FF8800', '#FFCC00', '#44CC44']
        fig = go.Figure(data=[go.Pie(
            labels=risk_counts.index,
            values=risk_counts.values,
            marker_colors=colors,
            hole=0.4,
        )])
        fig.update_layout(title="风险等级占比", height=350)
        st.plotly_chart(fig, use_container_width=True)


def department_risk_analysis(risk_df):
    st.subheader("🏢 部门风险分析")
    dept_stats = risk_df.groupby('department').agg(
        count=('employee_id', 'count'),
        avg_risk=('risk_score', 'mean'),
        high_risk_count=('risk_level', lambda x: (x == '高风险').sum()),
    ).reset_index()
    dept_stats['high_risk_pct'] = dept_stats['high_risk_count'] / dept_stats['count'] * 100
    dept_stats = dept_stats.sort_values('avg_risk', ascending=False)

    col1, col2 = st.columns(2)

    with col1:
        fig = px.bar(
            dept_stats, x='department', y='avg_risk',
            title="各部门平均风险评分",
            color='avg_risk',
            color_continuous_scale='RdYlGn_r',
        )
        fig.update_layout(
            xaxis_title="部门",
            yaxis_title="平均风险评分",
            height=350,
        )
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        fig = px.bar(
            dept_stats, x='department', y='high_risk_pct',
            title="各部门高风险员工占比 (%)",
            color='high_risk_pct',
            color_continuous_scale='Reds',
        )
        fig.update_layout(
            xaxis_title="部门",
            yaxis_title="高风险员工占比 (%)",
            height=350,
        )
        st.plotly_chart(fig, use_container_width=True)


def high_risk_employee_table(risk_df, dept_filter, risk_filter, top_n):
    st.subheader("⚠️ 高风险员工列表")

    filtered = risk_df.copy()

    if risk_filter:
        filtered = filtered[filtered['risk_level'].isin(risk_filter)]
    if dept_filter:
        filtered = filtered[filtered['department'].isin(dept_filter)]

    filtered = filtered.head(top_n)

    def highlight_risk(val):
        if val == '高风险':
            return 'background-color: #FF4444; color: white'
        elif val == '中高风险':
            return 'background-color: #FF8800; color: white'
        elif val == '中低风险':
            return 'background-color: #FFCC00'
        return ''

    display_cols = ['employee_id', 'department', 'role', 'level', 'age',
                    'tenure_years', 'commute_distance', 'late_rate_raw',
                    'late_rate_adjusted', 'risk_score', 'risk_level']
    styled_df = filtered[display_cols].style.applymap(highlight_risk, subset=['risk_level'])

    st.dataframe(styled_df, use_container_width=True, height=400)

    st.markdown(f"**显示 {len(filtered)} 名员工** (共 {len(risk_df)} 名)")
    st.caption("说明: 迟到率(修正后)已扣除通勤距离因素影响，更准确反映员工工作态度")


def shap_attribution_section(model, X_scaled, df_features):
    st.subheader("🔬 SHAP 离职因素归因分析")

    with st.spinner("正在计算 SHAP 值..."):
        explainer, shap_values = compute_shap_values(model, X_scaled)
        importance_df = get_feature_shap_importance(shap_values, X_scaled)
        factor_summary = get_attrition_factor_summary(importance_df)

    tab1, tab2, tab3 = st.tabs(["全局归因", "离职因素分类", "员工详情归因"])

    with tab1:
        col1, col2 = st.columns(2)
        with col1:
            top_features = importance_df.head(15)
            fig = px.bar(
                top_features, x='mean_abs_shap', y='feature_cn',
                orientation='h',
                title="Top 15 特征重要性 (SHAP)",
                color='mean_abs_shap',
                color_continuous_scale='RdYlGn_r',
            )
            fig.update_layout(
                xaxis_title="平均 |SHAP值|",
                yaxis_title="特征",
                height=500,
            )
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            top_features_display = importance_df.head(10).copy()
            top_features_display['mean_abs_shap'] = top_features_display['mean_abs_shap'].round(4)
            st.dataframe(
                top_features_display[['feature_cn', 'mean_abs_shap']],
                use_container_width=True,
                hide_index=True,
                column_config={
                    'feature_cn': '特征名称',
                    'mean_abs_shap': 'SHAP重要性',
                }
            )

    with tab2:
        col1, col2 = st.columns(2)
        with col1:
            fig = go.Figure(data=[go.Pie(
                labels=factor_summary['factor_group'],
                values=factor_summary['importance'],
                marker_colors=['#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4', '#FFEAA7', '#DDA0DD'],
                hole=0.4,
            )])
            fig.update_layout(title="离职因素分类占比", height=400)
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            st.dataframe(
                factor_summary,
                use_container_width=True,
                hide_index=True,
                column_config={
                    'factor_group': '因素类别',
                    'importance': '重要性',
                    'percentage': '占比(%)',
                }
            )

    with tab3:
        employee_options = df_features['employee_id'].tolist()
        selected_emp = st.selectbox("选择员工查看详情归因", employee_options, key='shap_emp_select')

        emp_idx = df_features[df_features['employee_id'] == selected_emp]
        if len(emp_idx) > 0:
            emp_idx = emp_idx.index[0]
            contrib_df = get_employee_shap_contribution(explainer, X_scaled, emp_idx)

            top_contrib = contrib_df.head(10)
            top_contrib = top_contrib.iloc[::-1]

            fig = go.Figure()
            for _, row in top_contrib.iterrows():
                color = '#FF6B6B' if row['shap_value'] > 0 else '#4ECDC4'
                fig.add_trace(go.Bar(
                    x=[row['shap_value']],
                    y=[row['feature_cn']],
                    orientation='h',
                    marker_color=color,
                    showlegend=False,
                ))

            fig.add_vline(x=0, line_dash="dash", line_color="gray")
            fig.update_layout(
                title=f"员工 {selected_emp} - 离职风险归因 (Top 10)",
                xaxis_title="SHAP 值 (对离职概率的影响)",
                yaxis_title="特征",
                height=400,
            )
            st.plotly_chart(fig, use_container_width=True)


def time_series_section(data):
    st.subheader("📉 时间序列趋势分析")

    with st.spinner("正在分析时间序列数据..."):
        monthly_df = build_monthly_features(data)
        company_trends = analyze_company_trends(monthly_df)
        dept_trends = analyze_department_trends(monthly_df)
        monthly_df = compute_risk_index(monthly_df)

    tab1, tab2, tab3 = st.tabs(["公司整体趋势", "部门趋势对比", "员工个人趋势"])

    with tab1:
        metrics_options = {
            '迟到率': 'late_rate',
            '缺勤率': 'absent_rate',
            '平均加班时长': 'avg_overtime_hours',
            '邮件沟通量': 'avg_total_emails',
            '任务完成率': 'avg_completion_rate',
            '综合满意度': 'overall_satisfaction',
        }

        selected_metric = st.selectbox("选择指标", list(metrics_options.keys()))
        metric_col = metrics_options[selected_metric]

        company_trends_plot = company_trends.set_index('month')
        data_series = company_trends_plot[metric_col].dropna()

        hist, forecast = forecast_trend(data_series, periods=3)

        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=data_series.index, y=data_series.values,
            mode='lines+markers', name='历史数据',
            line=dict(color='#4ECDC4', width=2),
        ))

        if hist is not None and forecast is not None:
            fig.add_trace(go.Scatter(
                x=forecast.index, y=forecast.values,
                mode='lines', name='预测趋势',
                line=dict(color='#FF6B6B', width=2, dash='dash'),
            ))

        fig.update_layout(
            title=f"公司{selected_metric}趋势 (含预测)",
            xaxis_title="月份",
            yaxis_title=selected_metric,
            height=400,
            hovermode='x unified',
        )
        st.plotly_chart(fig, use_container_width=True)

        if 'attrition_count' in company_trends_plot.columns:
            st.markdown("---")
            attr_data = company_trends_plot['attrition_count'].dropna()
            fig = go.Figure()
            fig.add_trace(go.Bar(
                x=attr_data.index, y=attr_data.values,
                name='离职人数',
                marker_color='#FF6B6B',
            ))
            fig.update_layout(
                title="月度离职人数",
                xaxis_title="月份",
                yaxis_title="离职人数",
                height=300,
            )
            st.plotly_chart(fig, use_container_width=True)

    with tab2:
        dept_options = dept_trends['department'].unique().tolist()
        selected_depts = st.multiselect("选择部门对比", dept_options, default=dept_options[:3])

        if selected_depts:
            dept_data = dept_trends[dept_trends['department'].isin(selected_depts)]
            fig = px.line(
                dept_data, x='month', y='overall_satisfaction',
                color='department',
                title="各部门综合满意度趋势",
                markers=True,
            )
            fig.update_layout(
                xaxis_title="月份",
                yaxis_title="综合满意度",
                height=400,
            )
            st.plotly_chart(fig, use_container_width=True)

            dept_risk = monthly_df.groupby(['month', 'department'])['risk_index'].mean().reset_index()
            dept_risk_filtered = dept_risk[dept_risk['department'].isin(selected_depts)]
            fig = px.line(
                dept_risk_filtered, x='month', y='risk_index',
                color='department',
                title="各部门风险指数趋势",
                markers=True,
            )
            fig.update_layout(
                xaxis_title="月份",
                yaxis_title="风险指数",
                height=400,
            )
            st.plotly_chart(fig, use_container_width=True)

    with tab3:
        employee_options = data['employees']['employee_id'].tolist()
        selected_emp = st.selectbox("选择员工", employee_options, key='ts_emp_select')

        if selected_emp:
            trend_info = compute_risk_trend_score(monthly_df, selected_emp)
            if trend_info and trend_info['metrics']:
                col1, col2 = st.columns([1, 3])
                with col1:
                    st.metric("风险趋势", trend_info['risk_trend_label'],
                             delta=f"{trend_info['risk_trend_score']:.2f}")
                with col2:
                    metrics_to_plot = {
                        '迟到率': 'late_rate',
                        '邮件量': 'avg_total_emails',
                        '任务完成率': 'avg_completion_rate',
                        '满意度': 'overall_satisfaction',
                    }

                    fig = make_subplots(rows=2, cols=2, subplot_titles=list(metrics_to_plot.keys()))
                    for idx, (name, col) in enumerate(metrics_to_plot.items()):
                        if col in trend_info['metrics']:
                            hist_data = trend_info['metrics'][col]['history']
                            row, col_pos = (idx // 2) + 1, (idx % 2) + 1
                            fig.add_trace(
                                go.Scatter(y=hist_data, mode='lines+markers', name=name),
                                row=row, col=col_pos
                            )
                    fig.update_layout(height=450, showlegend=False, title_text=f"员工 {selected_emp} 指标趋势")
                    st.plotly_chart(fig, use_container_width=True)


def retention_suggestions_section(risk_df, model, X_scaled, df_features):
    st.subheader("💡 个性化留存行动计划")

    high_risk_emps = risk_df[risk_df['risk_level'].isin(['高风险', '中高风险'])].head(10)

    if len(high_risk_emps) == 0:
        st.info("当前没有高风险或中高风险员工")
        return

    with st.spinner("正在计算SHAP归因并生成个性化行动计划..."):
        explainer, shap_values = compute_shap_values(model, X_scaled)

        shap_contributions_dict = {}
        for idx, row in df_features.iterrows():
            emp_id = row['employee_id']
            contrib = get_employee_shap_contribution(explainer, X_scaled, idx)
            shap_contributions_dict[emp_id] = contrib

        action_plans = generate_retention_suggestions(risk_df, shap_contributions_dict, df_features)

    for _, emp in high_risk_emps.iterrows():
        emp_id = emp['employee_id']
        plan = next((p for p in action_plans if p['employee_id'] == emp_id), None)

        emp_shap = shap_contributions_dict.get(emp_id)
        top_drivers = emp_shap.head(5) if emp_shap is not None else []

        with st.expander(f"👤 {emp_id} - {emp['department']} | 风险分: {emp['risk_score']:.2f} | {emp['risk_level']}"):
            if plan:
                st.info(f"**风险评估**: {plan['summary']}")

                if plan['key_drivers']:
                    st.markdown("### 🎯 关键影响因素")
                    drivers_df = pd.DataFrame(plan['key_drivers'])
                    drivers_df['影响程度'] = drivers_df['shap_value'].abs().round(4)
                    drivers_df['方向'] = drivers_df['impact']
                    drivers_display = drivers_df[['feature_cn', '方向', '影响程度']].head(5)
                    st.dataframe(drivers_display, use_container_width=True, hide_index=True)

                if plan['actions']:
                    st.markdown("### 📋 个性化行动计划")

                    risk_colors = {'高风险': '#FF4444', '中高风险': '#FF8800', '中低风险': '#FFCC00'}
                    color = risk_colors.get(emp['risk_level'], '#44CC44')

                    for idx, action in enumerate(plan['actions']):
                        icon = '🔴' if action['priority'] <= 2 else ('🟡' if action['priority'] <= 4 else '🔵')
                        with st.container():
                            cols = st.columns([0.1, 0.3, 0.4, 0.2])
                            with cols[0]:
                                st.markdown(f"**{icon}**")
                            with cols[1]:
                                st.markdown(f"**{action['category']}**")
                            with cols[2]:
                                st.markdown(f"**{action['action']}**")
                                if 'driver' in action and action['driver']:
                                    st.caption(f"驱动因素: {action['driver']}")
                            with cols[3]:
                                st.markdown(f"⏱️ {action['timeline']}")
                            st.markdown("---")
            else:
                st.info("该员工暂无特定行动计划")

            if len(top_drivers) > 0:
                st.markdown("### 📊 SHAP归因详情")
                top_drivers_display = top_drivers.copy()
                top_drivers_display['feature_cn'] = top_drivers_display['feature_cn']
                top_drivers_display['影响方向'] = top_drivers_display['shap_value'].apply(
                    lambda x: "↑ 增加离职风险" if x > 0 else "↓ 降低离职风险"
                )
                top_drivers_display['SHAP值'] = top_drivers_display['shap_value'].round(4)
                st.dataframe(
                    top_drivers_display[['feature_cn', '影响方向', 'SHAP值']],
                    use_container_width=True,
                    hide_index=True
                )


def anomaly_detection_section(monthly_df):
    st.subheader("🚨 异常检测")

    metric_options = {
        '迟到率': 'late_rate',
        '缺勤率': 'absent_rate',
        '邮件量': 'avg_total_emails',
        '任务完成率': 'avg_completion_rate',
        '满意度': 'overall_satisfaction',
    }

    selected_metric = st.selectbox("选择检测指标", list(metric_options.keys()), key='anomaly_metric')
    threshold = st.slider("异常阈值 (Z-Score)", 1.5, 3.5, 2.0, 0.1)

    with st.spinner("正在检测异常..."):
        anomalies = detect_anomalies(monthly_df, metric_options[selected_metric], threshold)

    if len(anomalies) > 0:
        st.warning(f"发现 {len(anomalies)} 个异常数据点")
        st.dataframe(
            anomalies,
            use_container_width=True,
            hide_index=True,
            column_config={
                'employee_id': '员工ID',
                'month': '月份',
                'metric': '指标',
                'value': '数值',
                'z_score': 'Z-Score',
                'anomaly_type': '异常类型',
            }
        )
    else:
        st.success("未检测到显著异常")


def departure_impact_section(risk_df, df_features, data):
    st.subheader("💥 离职影响评估")

    with st.spinner("正在评估离职影响..."):
        df_employees = data['employees']
        impact_results = assess_team_impact(risk_df, df_employees, df_features)

    if impact_results is None or len(impact_results) == 0:
        st.info("当前无高风险员工需要评估影响")
        return

    impact_summary = generate_impact_summary(impact_results)

    tab1, tab2, tab3 = st.tabs(["影响总览", "员工影响详情", "部门影响汇总"])

    with tab1:
        col1, col2, col3, col4 = st.columns(4)
        company_summary = impact_summary.get('company_summary', {})
        col1.metric("受影响员工数", company_summary.get('total_affected', 0))
        col2.metric("平均影响分", f"{company_summary.get('avg_impact', 0):.1f}")
        col3.metric("最高影响分", f"{company_summary.get('max_impact', 0):.1f}")
        col4.metric("涉及部门数", company_summary.get('departments_affected', 0))

        st.markdown("---")

        col1, col2 = st.columns(2)

        with col1:
            impact_dist = impact_results['impact_level'].value_counts().reindex(
                ['严重', '较高', '中等', '较低'], fill_value=0
            )
            fig = go.Figure(data=[go.Pie(
                labels=impact_dist.index,
                values=impact_dist.values,
                marker_colors=['#FF4444', '#FF8800', '#FFCC00', '#44CC44'],
                hole=0.4,
            )])
            fig.update_layout(title="离职影响等级分布", height=350)
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            fig = px.scatter(
                impact_results, x='risk_score', y='overall_impact',
                color='impact_level',
                color_discrete_map={'严重': '#FF4444', '较高': '#FF8800', '中等': '#FFCC00', '较低': '#44CC44'},
                hover_data=['employee_id', 'department'],
                title="风险评分 vs 离职影响",
            )
            fig.update_layout(
                xaxis_title="离职风险评分",
                yaxis_title="离职影响分",
                height=350,
            )
            st.plotly_chart(fig, use_container_width=True)

    with tab2:
        selected_emp = st.selectbox(
            "选择员工查看影响详情",
            impact_results['employee_id'].tolist(),
            key='impact_emp_select'
        )

        if selected_emp:
            impact_detail = assess_departure_impact(
                selected_emp, df_employees, df_features, risk_df
            )
            if impact_detail:
                col1, col2, col3 = st.columns(3)
                col1.metric(
                    "团队士气影响",
                    f"{impact_detail['morale_impact']:.1f}",
                    delta=f"{'严重' if impact_detail['morale_impact'] >= 60 else '可控'}"
                )
                col2.metric(
                    "项目进度影响",
                    f"{impact_detail['project_impact']:.1f}",
                    delta=f"{'严重' if impact_detail['project_impact'] >= 60 else '可控'}"
                )
                col3.metric(
                    "综合影响",
                    f"{impact_detail['overall_impact']:.1f}",
                    delta=impact_detail['impact_level']
                )

                st.markdown("---")
                col1, col2 = st.columns(2)

                with col1:
                    st.markdown("#### 🧠 士气影响因素分解")
                    morale_factors = impact_detail.get('morale_factors', {})
                    if morale_factors:
                        fig = go.Figure(data=[go.Bar(
                            x=list(morale_factors.values()),
                            y=list(morale_factors.keys()),
                            orientation='h',
                            marker_color='#4ECDC4',
                        )])
                        fig.update_layout(
                            xaxis_title="影响分",
                            yaxis_title="因素",
                            height=300,
                        )
                        st.plotly_chart(fig, use_container_width=True)

                with col2:
                    st.markdown("#### 📋 项目影响因素分解")
                    project_factors = impact_detail.get('project_factors', {})
                    if project_factors:
                        fig = go.Figure(data=[go.Bar(
                            x=list(project_factors.values()),
                            y=list(project_factors.keys()),
                            orientation='h',
                            marker_color='#FF6B6B',
                        )])
                        fig.update_layout(
                            xaxis_title="影响分",
                            yaxis_title="因素",
                            height=300,
                        )
                        st.plotly_chart(fig, use_container_width=True)

    with tab3:
        dept_summaries = impact_summary.get('department_summaries', {})
        if dept_summaries:
            dept_rows = []
            for dept, summary in dept_summaries.items():
                dept_rows.append({
                    '部门': dept,
                    '受影响人数': summary.get('affected_count', 0),
                    '平均影响分': round(summary.get('avg_impact', 0), 1),
                    '最高影响分': round(summary.get('max_impact', 0), 1),
                    '严重/较高占比': f"{summary.get('high_impact_pct', 0):.0%}",
                    '关键风险角色': summary.get('critical_role', '-'),
                })
            dept_df = pd.DataFrame(dept_rows)
            st.dataframe(dept_df, use_container_width=True, hide_index=True)

            fig = px.bar(
                dept_df, x='部门', y='平均影响分',
                title="各部门离职影响评分",
                color='平均影响分',
                color_continuous_scale='Reds',
            )
            fig.update_layout(height=350)
            st.plotly_chart(fig, use_container_width=True)


def calibration_section(model, scaler, df_features, risk_df, data):
    st.subheader("🎯 离职预测校准分析")

    df_employees = data['employees']

    with st.spinner("正在分析模型校准..."):
        X = df_features[FEATURE_COLS].copy()
        X_scaled_data = scaler.transform(X)
        y_true = df_features['target'].values
        y_pred_proba = model.predict_proba(X_scaled_data)[:, 1]

        cal_metrics = compute_calibration_metrics(y_true, y_pred_proba)
        comparison = compare_actual_vs_predicted(risk_df, df_employees)
        adjustment = suggest_calibration_adjustment(cal_metrics)

    tab1, tab2, tab3 = st.tabs(["校准曲线", "实际vs预测对比", "校准建议"])

    with tab1:
        col1, col2 = st.columns(2)

        with col1:
            cal_curve = cal_metrics.get('calibration_curve')
            if cal_curve is not None and len(cal_curve) > 0:
                fig = go.Figure()
                fig.add_trace(go.Scatter(
                    x=cal_curve['平均预测概率'],
                    y=cal_curve['平均实际概率'],
                    mode='lines+markers',
                    name='模型校准线',
                    line=dict(color='#4ECDC4', width=2),
                    marker=dict(size=8),
                ))
                fig.add_trace(go.Scatter(
                    x=[0, 1], y=[0, 1],
                    mode='lines',
                    name='完美校准',
                    line=dict(color='gray', dash='dash'),
                ))
                fig.update_layout(
                    title="校准曲线 (Calibration Curve)",
                    xaxis_title="平均预测概率",
                    yaxis_title="平均实际概率",
                    height=400,
                )
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("校准曲线数据不足")

        with col2:
            st.markdown("#### 📊 校准指标")
            metrics_display = {
                'Brier Score': f"{cal_metrics.get('brier_score', 0):.4f}",
                'ECE (期望校准误差)': f"{cal_metrics.get('ece', 0):.4f}",
                'AUC-ROC': f"{cal_metrics.get('auc_roc', 0):.4f}" if cal_metrics.get('auc_roc') else 'N/A',
                '准确率': f"{cal_metrics.get('accuracy', 0):.2%}",
            }
            for name, value in metrics_display.items():
                st.metric(name, value)

            st.markdown("---")
            cal_curve_detail = cal_metrics.get('calibration_curve')
            if cal_curve_detail is not None and len(cal_curve_detail) > 0:
                st.dataframe(
                    cal_curve_detail,
                    use_container_width=True,
                    hide_index=True,
                )

    with tab2:
        comparison_df = comparison.get('comparison_df')
        confusion = comparison.get('confusion_matrix')

        col1, col2 = st.columns(2)

        with col1:
            if comparison_df is not None and len(comparison_df) > 0:
                st.markdown("#### 各风险等级对比")
                st.dataframe(comparison_df, use_container_width=True, hide_index=True)

        with col2:
            if confusion is not None:
                st.markdown("#### 混淆矩阵")
                fig = go.Figure(data=go.Heatmap(
                    z=confusion.values,
                    x=confusion.columns.tolist(),
                    y=confusion.index.tolist(),
                    text=confusion.values,
                    texttemplate="%{text}",
                    colorscale='Blues',
                ))
                fig.update_layout(height=350)
                st.plotly_chart(fig, use_container_width=True)

        accuracy_by_risk = comparison.get('accuracy_by_risk_level')
        if accuracy_by_risk:
            st.markdown("#### 各风险等级预测准确率")
            acc_df = pd.DataFrame([
                {'风险等级': k, '准确率': f"{v:.2%}"} for k, v in accuracy_by_risk.items()
            ])
            st.dataframe(acc_df, use_container_width=True, hide_index=True)

    with tab3:
        st.markdown("#### 🔧 校准调整建议")
        col1, col2, col3 = st.columns(3)
        col1.metric("当前阈值", f"{adjustment.get('current_threshold', 0.5):.2f}")
        col2.metric("建议阈值", f"{adjustment.get('suggested_threshold', 0.5):.2f}")
        col3.metric("调整方向", adjustment.get('adjustment_direction', '-'))

        st.info(f"**原因**: {adjustment.get('adjustment_reason', '无')}")
        if adjustment.get('platt_scaling_recommended'):
            st.warning("💡 建议使用 Platt Scaling 或 Isotonic Regression 对模型输出进行后处理校准")

        st.markdown("---")
        st.markdown("#### 📅 时序校准分析")
        with st.spinner("正在计算时序校准..."):
            time_cal = calibration_over_time(model, scaler, df_features, data)
            if time_cal is not None and len(time_cal) > 0:
                fig = make_subplots(
                    rows=1, cols=3,
                    subplot_titles=['Brier Score', 'ECE', 'AUC-ROC']
                )
                fig.add_trace(go.Bar(
                    x=time_cal['时期'], y=time_cal['brier_score'],
                    name='Brier Score', marker_color='#FF6B6B'
                ), row=1, col=1)
                fig.add_trace(go.Bar(
                    x=time_cal['时期'], y=time_cal['ece'],
                    name='ECE', marker_color='#4ECDC4'
                ), row=1, col=2)
                fig.add_trace(go.Bar(
                    x=time_cal['时期'], y=time_cal['auc_roc'],
                    name='AUC-ROC', marker_color='#45B7D1'
                ), row=1, col=3)
                fig.update_layout(height=350, showlegend=False)
                st.plotly_chart(fig, use_container_width=True)


def succession_planning_section(risk_df, df_features, data):
    st.subheader("🔄 接替计划推荐")

    df_employees = data['employees']

    high_risk_emps = risk_df[risk_df['risk_level'].isin(['高风险', '中高风险'])].head(10)

    if len(high_risk_emps) == 0:
        st.info("当前没有高风险或中高风险员工需要接替计划")
        return

    tab1, tab2 = st.tabs(["接替计划总览", "个人接替方案"])

    with tab1:
        with st.spinner("正在生成接替计划..."):
            plans = batch_succession_planning(risk_df, df_employees, df_features)

        if plans:
            for plan in plans:
                emp_id = plan['departing_employee']['employee_id']
                dept = plan['departing_employee']['department']
                role = plan['departing_employee']['role']
                risk_score = plan['departing_employee']['risk_score']
                transition = plan['transition_period']

                candidates = plan['candidates']
                best_score = candidates[0]['score'] if candidates else 0

                with st.expander(f"👤 {emp_id} - {dept}/{role} | 风险: {risk_score:.2f} | 过渡期: {transition}"):
                    if candidates:
                        cand_rows = []
                        for c in candidates:
                            cand_rows.append({
                                '候选人': c['candidate_id'],
                                '部门': c['department'],
                                '职位': c['role'],
                                '职级': c['level'],
                                '年限': c['tenure_years'],
                                '匹配分': c['score'],
                                '就绪度': c['readiness_level'],
                            })
                        st.dataframe(
                            pd.DataFrame(cand_rows),
                            use_container_width=True,
                            hide_index=True,
                        )

    with tab2:
        selected_emp = st.selectbox(
            "选择离职员工查看详细接替方案",
            high_risk_emps['employee_id'].tolist(),
            key='succession_emp_select'
        )

        if selected_emp:
            plan = generate_succession_plan(selected_emp, df_employees, df_features, risk_df)

            if plan:
                departing = plan['departing_employee']
                st.markdown(f"### 📋 {departing['employee_id']} 接替方案")
                st.markdown(f"**部门**: {departing['department']} | **职位**: {departing['role']} | **职级**: {departing['level']}")
                st.markdown(f"**风险评分**: {departing['risk_score']:.2f} | **预计过渡期**: {plan['transition_period']}")

                st.markdown("---")
                st.markdown("#### 🏆 推荐接替人选")

                candidates = plan['candidates']
                if candidates:
                    for idx, c in enumerate(candidates):
                        readiness_icon = {'立即接替': '🟢', '短期准备': '🟡', '长期培养': '🔴'}.get(c['readiness_level'], '⚪')
                        with st.container():
                            cols = st.columns([0.15, 0.2, 0.2, 0.15, 0.15, 0.15])
                            cols[0].markdown(f"**{readiness_icon} #{idx+1}**")
                            cols[1].markdown(f"**{c['candidate_id']}**")
                            cols[2].markdown(f"{c['department']}/{c['role']}")
                            cols[3].markdown(f"匹配分: **{c['score']:.0f}**")
                            cols[4].markdown(f"{c['readiness_level']}")
                            cols[5].markdown(f"年限: {c['tenure_years']}年")

                        if idx == 0:
                            breakdown = c.get('score_breakdown', {})
                            if breakdown:
                                fig = go.Figure(data=[go.Bar(
                                    x=list(breakdown.values()),
                                    y=list(breakdown.keys()),
                                    orientation='h',
                                    marker_color='#4ECDC4',
                                )])
                                fig.update_layout(
                                    title="最佳候选人匹配分分解",
                                    xaxis_title="得分",
                                    height=250,
                                )
                                st.plotly_chart(fig, use_container_width=True)

                st.markdown("---")
                col1, col2 = st.columns(2)

                with col1:
                    st.markdown("#### 📝 知识交接清单")
                    checklist = plan.get('knowledge_transfer', [])
                    for item in checklist:
                        st.checkbox(item, key=f"kt_{selected_emp}_{item[:20]}")

                with col2:
                    st.markdown("#### ⚠️ 风险缓解措施")
                    mitigations = plan.get('risk_mitigation', [])
                    for m in mitigations:
                        st.markdown(f"- {m}")


def main():
    header_section()
    risk_filter, dept_filter, show_high_risk_only, top_n = sidebar()

    with st.spinner("正在加载数据和模型..."):
        data = load_or_generate_data()
        model, scaler, df_features, X_scaled, feat_imp = load_or_train_model(data)
        risk_df = get_risk_scores(model, scaler, df_features)
        monthly_df = build_monthly_features(data)

    st.markdown("---")
    st.subheader("📊 整体概览")
    overview_metrics(risk_df)

    st.markdown("---")
    risk_distribution_chart(risk_df)

    st.markdown("---")
    department_risk_analysis(risk_df)

    st.markdown("---")
    high_risk_employee_table(risk_df, dept_filter, risk_filter, top_n)

    st.markdown("---")
    shap_attribution_section(model, X_scaled, df_features)

    st.markdown("---")
    time_series_section(data)

    st.markdown("---")
    retention_suggestions_section(risk_df, model, X_scaled, df_features)

    st.markdown("---")
    departure_impact_section(risk_df, df_features, data)

    st.markdown("---")
    calibration_section(model, scaler, df_features, risk_df, data)

    st.markdown("---")
    succession_planning_section(risk_df, df_features, data)

    st.markdown("---")
    anomaly_detection_section(monthly_df)

    st.markdown("---")
    st.markdown("*© 2025 员工离职倾向分析系统 | 数据仅供参考*")


if __name__ == '__main__':
    main()