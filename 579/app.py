import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from data_generator import (
    generate_user_sessions,
    generate_ab_test_data,
    get_intervention_strategies,
    get_personalized_strategies,
    ABANDONMENT_REASONS,
    USER_SEGMENTS,
    PRODUCT_CATEGORIES,
)
from funnel_analysis import (
    compute_funnel,
    compute_funnel_by_segment,
    compute_funnel_by_category,
    compute_funnel_by_device,
    compute_overall_abandonment_rate,
    compute_stage_drop_off_analysis,
    compute_cart_abandonment_funnel,
)
from attribution_analysis import (
    compute_reason_attribution,
    compute_sub_reason_attribution,
    compute_reason_by_segment,
    compute_reason_by_category,
    compute_price_sensitivity_analysis,
    compute_price_sensitivity_by_user,
    compute_shipping_impact_analysis,
    compute_login_barrier_analysis,
    compute_attribution_summary,
    compute_survey_analysis,
    compute_competitor_impact,
    compute_competitor_by_category,
    compute_price_diff_abandonment,
    compute_competitor_by_sensitivity,
)
from ab_test import (
    compute_ab_test_results,
    perform_significance_test,
    perform_all_pairwise_tests,
    compute_ab_trend,
    compute_ab_reason_comparison,
    compute_sample_size_estimate,
)
from risk_prediction import (
    train_risk_model,
    predict_risk_for_user,
    compute_risk_distribution,
    compute_risk_by_segment,
    simulate_realtime_prediction,
)
from realtime_intervention import (
    compute_intervention_summary,
    compute_intervention_by_type,
    compute_intervention_by_reason,
    compute_intervention_by_timing,
    compute_intervention_timeline,
    simulate_realtime_intervention,
)

st.set_page_config(
    page_title="购物车放弃分析平台",
    page_icon="🛒",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
<style>
    .main-header { font-size: 2.2rem; font-weight: 700; color: #1a1a2e; margin-bottom: 0.5rem; }
    .sub-header { font-size: 1.1rem; color: #6c757d; margin-bottom: 2rem; }
    .metric-card { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 1.5rem; border-radius: 1rem; color: white; }
    .metric-value { font-size: 2rem; font-weight: 700; }
    .metric-label { font-size: 0.9rem; opacity: 0.9; }
    .insight-box { background: #f8f9fa; border-left: 4px solid #667eea; padding: 1rem; margin: 0.5rem 0; border-radius: 0 0.5rem 0.5rem 0; }
    .strategy-card { background: white; border: 1px solid #e9ecef; border-radius: 0.75rem; padding: 1rem; margin: 0.5rem 0; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    .impact-high { color: #dc3545; font-weight: 600; }
    .impact-medium { color: #ffc107; font-weight: 600; }
    .impact-low { color: #28a745; font-weight: 600; }
</style>
""",
    unsafe_allow_html=True,
)


@st.cache_data
def load_data(n_sessions=5000):
    return generate_user_sessions(n_sessions)


def render_sidebar(df):
    st.sidebar.markdown("## 🔍 数据筛选")

    date_range = st.sidebar.date_input(
        "日期范围",
        value=(df["session_timestamp"].min().date(), df["session_timestamp"].max().date()),
        min_value=df["session_timestamp"].min().date(),
        max_value=df["session_timestamp"].max().date(),
    )

    segments = st.sidebar.multiselect("用户群体", USER_SEGMENTS, default=USER_SEGMENTS)
    categories = st.sidebar.multiselect("商品品类", PRODUCT_CATEGORIES, default=PRODUCT_CATEGORIES)
    devices = st.sidebar.multiselect("设备类型", df["device"].unique().tolist(), default=df["device"].unique().tolist())

    filtered = df.copy()
    if len(date_range) == 2:
        filtered = filtered[
            (filtered["session_timestamp"].dt.date >= date_range[0])
            & (filtered["session_timestamp"].dt.date <= date_range[1])
        ]
    if segments:
        filtered = filtered[filtered["user_segment"].isin(segments)]
    if categories:
        filtered = filtered[filtered["product_category"].isin(categories)]
    if devices:
        filtered = filtered[filtered["device"].isin(devices)]

    return filtered


def render_overview_metrics(df):
    cart_df = df[df["behavior_path"].str.contains("加入购物车")]
    total_sessions = len(df)
    cart_sessions = len(cart_df)
    completed = cart_df["completed"].sum()
    abandoned = cart_sessions - completed
    abandonment_rate = (abandoned / cart_sessions * 100) if cart_sessions > 0 else 0
    avg_cart_value = cart_df["cart_value"].mean()
    lost_revenue = cart_df[~cart_df["completed"]]["cart_value"].sum()

    col1, col2, col3, col4, col5 = st.columns(5)

    with col1:
        st.markdown(
            f'<div class="metric-card"><div class="metric-value">{total_sessions:,}</div><div class="metric-label">总会话数</div></div>',
            unsafe_allow_html=True,
        )
    with col2:
        st.markdown(
            f'<div class="metric-card" style="background:linear-gradient(135deg,#f093fb 0%,#f5576c 100%)"><div class="metric-value">{cart_sessions:,}</div><div class="metric-label">加购会话</div></div>',
            unsafe_allow_html=True,
        )
    with col3:
        st.markdown(
            f'<div class="metric-card" style="background:linear-gradient(135deg,#fa709a 0%,#fee140 100%)"><div class="metric-value">{abandonment_rate:.1f}%</div><div class="metric-label">放弃率</div></div>',
            unsafe_allow_html=True,
        )
    with col4:
        st.markdown(
            f'<div class="metric-card" style="background:linear-gradient(135deg,#a18cd1 0%,#fbc2eb 100%)"><div class="metric-value">¥{avg_cart_value:,.0f}</div><div class="metric-label">平均客单价</div></div>',
            unsafe_allow_html=True,
        )
    with col5:
        st.markdown(
            f'<div class="metric-card" style="background:linear-gradient(135deg,#ff9a9e 0%,#fecfef 100%)"><div class="metric-value">¥{lost_revenue:,.0f}</div><div class="metric-label">流失金额</div></div>',
            unsafe_allow_html=True,
        )


def render_funnel_analysis(df):
    st.markdown("### 📊 转化漏斗分析")

    tab1, tab2, tab3 = st.tabs(["整体漏斗", "分组对比", "放弃阶段分析"])

    with tab1:
        funnel = compute_funnel(df)
        cart_funnel = compute_cart_abandonment_funnel(df)

        col1, col2 = st.columns(2)

        with col1:
            fig = go.Figure()
            fig.add_trace(
                go.Funnel(
                    y=funnel["stage"].tolist(),
                    x=funnel["count"].tolist(),
                    textinfo="value+percent initial",
                    marker=dict(
                        color=[
                            "#667eea",
                            "#764ba2",
                            "#f093fb",
                            "#f5576c",
                            "#fa709a",
                            "#fee140",
                            "#a8e063",
                            "#56ab2f",
                        ]
                    ),
                )
            )
            fig.update_layout(title="全链路转化漏斗", height=500)
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            fig = go.Figure()
            fig.add_trace(
                go.Funnel(
                    y=cart_funnel["stage"].tolist(),
                    x=cart_funnel["count"].tolist(),
                    textinfo="value+percent initial",
                    marker=dict(
                        color=[
                            "#764ba2",
                            "#f093fb",
                            "#f5576c",
                            "#fa709a",
                            "#fee140",
                            "#a8e063",
                            "#56ab2f",
                        ]
                    ),
                )
            )
            fig.update_layout(title="购物车转化漏斗（从加购开始）", height=500)
            st.plotly_chart(fig, use_container_width=True)

        st.markdown("#### 漏斗转化明细")
        st.dataframe(
            funnel.style.format({"rate": "{:.2f}%", "drop_off_rate": "{:.2f}%", "conversion_from_prev": "{:.2f}%"}),
            use_container_width=True,
        )

    with tab2:
        dim = st.selectbox("选择分组维度", ["用户群体", "商品品类", "设备类型"])

        if dim == "用户群体":
            funnel_by = compute_funnel_by_segment(df)
            group_col = "segment"
        elif dim == "商品品类":
            funnel_by = compute_funnel_by_category(df)
            group_col = "category"
        else:
            funnel_by = compute_funnel_by_device(df)
            group_col = "device"

        groups = funnel_by[group_col].unique()
        colors = px.colors.qualitative.Set2[: len(groups)]

        fig = go.Figure()
        for i, group in enumerate(groups):
            gdf = funnel_by[funnel_by[group_col] == group]
            fig.add_trace(
                go.Funnel(
                    name=group,
                    y=gdf["stage"].tolist(),
                    x=gdf["count"].tolist(),
                    textinfo="value+percent initial",
                    marker=dict(color=colors[i]),
                )
            )
        fig.update_layout(title=f"按{dim}分组的转化漏斗", height=600)
        st.plotly_chart(fig, use_container_width=True)

        completion_by_group = (
            df[df["behavior_path"].str.contains("加入购物车")]
            .groupby(group_col if group_col != "segment" else "user_segment")
            .apply(lambda x: pd.Series({"completion_rate": x["completed"].mean() * 100, "count": len(x)}))
            .reset_index()
        )
        col_name = group_col if group_col != "segment" else "user_segment"

        fig2 = px.bar(
            completion_by_group,
            x=col_name,
            y="completion_rate",
            color=col_name,
            title=f"各{dim}完成率对比",
            text="completion_rate",
        )
        fig2.update_traces(texttemplate="%{text:.1f}%", textposition="outside")
        fig2.update_layout(yaxis_title="完成率 (%)", showlegend=False)
        st.plotly_chart(fig2, use_container_width=True)

    with tab3:
        drop_off = compute_stage_drop_off_analysis(df)
        st.markdown("#### 放弃用户的最后行为节点")

        fig = px.bar(
            drop_off,
            x="last_event",
            y="count",
            color="last_event",
            text="percentage",
            title="放弃用户在各阶段的分布",
        )
        fig.update_traces(texttemplate="%{text:.1f}%", textposition="outside")
        fig.update_layout(xaxis_title="最后行为", yaxis_title="用户数", showlegend=False)
        st.plotly_chart(fig, use_container_width=True)

        st.markdown('<div class="insight-box">💡 <b>关键洞察</b>：大部分放弃发生在查看购物车后未进入结算环节，建议优化购物车页面的引导和激励。</div>', unsafe_allow_html=True)


def render_trend_analysis(df):
    st.markdown("### 📈 放弃率趋势分析")

    cart_df = df[df["behavior_path"].str.contains("加入购物车")].copy()

    tab1, tab2, tab3 = st.tabs(["月度趋势", "周度趋势", "群体趋势"])

    with tab1:
        monthly = (
            cart_df.groupby("month")
            .apply(lambda x: pd.Series({"abandonment_rate": (1 - x["completed"].mean()) * 100, "total": len(x), "completed": x["completed"].sum(), "avg_value": x["cart_value"].mean()}))
            .reset_index()
        )

        fig = make_subplots(specs=[[{"secondary_y": True}]])
        fig.add_trace(
            go.Scatter(x=monthly["month"], y=monthly["abandonment_rate"], mode="lines+markers", name="放弃率 (%)", line=dict(color="#f5576c", width=3)),
            secondary_y=False,
        )
        fig.add_trace(
            go.Bar(x=monthly["month"], y=monthly["total"], name="加购会话数", marker_color="#667eea", opacity=0.5),
            secondary_y=True,
        )
        fig.update_layout(title="月度购物车放弃率趋势", height=450)
        fig.update_yaxes(title_text="放弃率 (%)", secondary_y=False)
        fig.update_yaxes(title_text="加购会话数", secondary_y=True)
        st.plotly_chart(fig, use_container_width=True)

        st.dataframe(
            monthly.style.format({"abandonment_rate": "{:.2f}%", "avg_value": "¥{:.2f}"}),
            use_container_width=True,
        )

    with tab2:
        weekly = (
            cart_df.groupby("week")
            .apply(lambda x: pd.Series({"abandonment_rate": (1 - x["completed"].mean()) * 100, "total": len(x)}))
            .reset_index()
        )

        fig = go.Figure()
        fig.add_trace(
            go.Scatter(
                x=weekly["week"],
                y=weekly["abandonment_rate"],
                mode="lines+markers",
                name="周度放弃率",
                line=dict(color="#764ba2", width=2),
                fill="tozeroy",
                fillcolor="rgba(118, 75, 162, 0.1)",
            )
        )
        fig.update_layout(title="周度购物车放弃率趋势", height=450, xaxis_title="周", yaxis_title="放弃率 (%)")
        st.plotly_chart(fig, use_container_width=True)

    with tab3:
        segment_trend = (
            cart_df.groupby(["month", "user_segment"])
            .apply(lambda x: pd.Series({"abandonment_rate": (1 - x["completed"].mean()) * 100}))
            .reset_index()
        )

        fig = px.line(
            segment_trend,
            x="month",
            y="abandonment_rate",
            color="user_segment",
            markers=True,
            title="各用户群体月度放弃率趋势",
        )
        fig.update_layout(yaxis_title="放弃率 (%)", height=450)
        st.plotly_chart(fig, use_container_width=True)

        cat_trend = (
            cart_df.groupby(["month", "product_category"])
            .apply(lambda x: pd.Series({"abandonment_rate": (1 - x["completed"].mean()) * 100}))
            .reset_index()
        )

        fig = px.line(
            cat_trend,
            x="month",
            y="abandonment_rate",
            color="product_category",
            markers=True,
            title="各品类月度放弃率趋势",
        )
        fig.update_layout(yaxis_title="放弃率 (%)", height=450)
        st.plotly_chart(fig, use_container_width=True)


def render_attribution_analysis(df):
    st.markdown("### 🎯 放弃原因归因分析")

    tab1, tab2, tab3, tab4, tab5 = st.tabs(["原因总览", "📋 用户调研", "价格敏感度", "运费影响", "登录门槛"])

    with tab1:
        reason_attr = compute_reason_attribution(df)

        col1, col2 = st.columns(2)

        with col1:
            fig = px.pie(
                reason_attr,
                values="count",
                names="reason",
                title="放弃原因分布",
                hole=0.4,
                color_discrete_sequence=px.colors.qualitative.Set2,
            )
            fig.update_traces(textposition="inside", textinfo="percent+label")
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            fig = px.bar(
                reason_attr,
                x="reason",
                y="percentage",
                color="reason",
                title="放弃原因占比",
                text="percentage",
            )
            fig.update_traces(texttemplate="%{text:.1f}%", textposition="outside")
            fig.update_layout(showlegend=False, yaxis_title="占比 (%)")
            st.plotly_chart(fig, use_container_width=True)

        selected_reason = st.selectbox("选择查看子原因", list(ABANDONMENT_REASONS.keys()))
        sub_reason = compute_sub_reason_attribution(df, selected_reason)

        fig = px.bar(
            sub_reason,
            x="sub_reason",
            y="percentage",
            color="sub_reason",
            title=f"'{selected_reason}'的子原因分布",
            text="percentage",
        )
        fig.update_traces(texttemplate="%{text:.1f}%", textposition="outside")
        fig.update_layout(showlegend=False, yaxis_title="占比 (%)")
        st.plotly_chart(fig, use_container_width=True)

        cross, cross_pct = compute_reason_by_segment(df)
        st.markdown("#### 各用户群体 × 放弃原因交叉分析")
        st.dataframe(cross_pct.style.format("{:.1f}%"), use_container_width=True)

    with tab2:
        survey = compute_survey_analysis(df)

        st.markdown(f"#### 📋 用户调研弹窗结果")
        st.markdown(
            f'<div class="insight-box">📝 <b>调研响应率</b>：{survey["response_rate"]:.1f}% 的放弃用户参与了调研弹窗</div>',
            unsafe_allow_html=True,
        )

        st.markdown(f"**行为归因与调研归因一致性**：{survey['survey_vs_behavior_consistency']:.1f}%")

        col1, col2 = st.columns(2)

        with col1:
            if not survey["reason_distribution"].empty:
                fig = px.pie(
                    survey["reason_distribution"],
                    values="count",
                    names="survey_reason",
                    title="调研：用户自述放弃原因",
                    hole=0.4,
                    color_discrete_sequence=px.colors.qualitative.Pastel,
                )
                fig.update_traces(textposition="inside", textinfo="percent+label")
                st.plotly_chart(fig, use_container_width=True)

        with col2:
            if not survey["price_feel_distribution"].empty:
                fig = px.bar(
                    survey["price_feel_distribution"],
                    x="price_feel",
                    y="percentage",
                    color="price_feel",
                    title="调研：用户价格感受分布",
                    text="percentage",
                )
                fig.update_traces(texttemplate="%{text:.1f}%", textposition="outside")
                fig.update_layout(showlegend=False, yaxis_title="占比 (%)")
                st.plotly_chart(fig, use_container_width=True)

        if not survey["return_willingness"].empty:
            fig = px.bar(
                survey["return_willingness"],
                x="return_willingness",
                y="percentage",
                color="return_willingness",
                title="调研：用户回归意愿",
                text="percentage",
            )
            fig.update_traces(texttemplate="%{text:.1f}%", textposition="outside")
            fig.update_layout(showlegend=False, yaxis_title="占比 (%)")
            st.plotly_chart(fig, use_container_width=True)

        if not survey["reason_vs_behavior"].empty:
            st.markdown("#### 行为归因 × 调研归因 交叉验证")
            st.dataframe(survey["reason_vs_behavior"], use_container_width=True)

            st.markdown(
                f'<div class="insight-box">💡 <b>调研洞察</b>：行为推断与用户自述一致性为 {survey["survey_vs_behavior_consistency"]:.1f}%，'
                f"{'高于70%说明行为归因较为可靠' if survey['survey_vs_behavior_consistency'] > 70 else '低于70%说明行为归因存在偏差，需结合调研修正'}。</div>",
                unsafe_allow_html=True,
            )

    with tab3:
        price_analysis = compute_price_sensitivity_analysis(df)

        fig = make_subplots(specs=[[{"secondary_y": True}]])
        fig.add_trace(
            go.Bar(x=price_analysis["price_range"].astype(str), y=price_analysis["abandonment_rate"], name="放弃率 (%)", marker_color="#f5576c"),
            secondary_y=False,
        )
        fig.add_trace(
            go.Scatter(x=price_analysis["price_range"].astype(str), y=price_analysis["avg_value"], mode="lines+markers", name="平均客单价", line=dict(color="#667eea", width=2)),
            secondary_y=True,
        )
        fig.update_layout(title="价格敏感度分析：购物车金额 vs 放弃率", height=450)
        fig.update_yaxes(title_text="放弃率 (%)", secondary_y=False)
        fig.update_yaxes(title_text="平均客单价 (¥)", secondary_y=True)
        st.plotly_chart(fig, use_container_width=True)

        st.dataframe(price_analysis.style.format({"abandonment_rate": "{:.2f}%", "avg_value": "¥{:.2f}"}), use_container_width=True)

        user_sensitivity, level_summary = compute_price_sensitivity_by_user(df)

        st.markdown("#### 用户价格敏感度分层")
        fig = px.bar(
            level_summary,
            x="sensitivity_level",
            y="avg_abandonment_rate",
            color="sensitivity_level",
            title="不同价格敏感度用户的放弃率",
            text="avg_abandonment_rate",
        )
        fig.update_traces(texttemplate="%{text:.1f}%", textposition="outside")
        fig.update_layout(yaxis_title="平均放弃率 (%)", xaxis_title="敏感度层级", showlegend=False)
        st.plotly_chart(fig, use_container_width=True)

        st.dataframe(
            level_summary.style.format({"avg_abandonment_rate": "{:.2f}%", "avg_sensitivity_score": "{:.4f}", "avg_cart_value": "¥{:.2f}"}),
            use_container_width=True,
        )

        st.markdown(
            '<div class="insight-box">💡 <b>价格洞察</b>：高客单价区间放弃率显著上升，建议针对高金额订单提供分期付款或额外优惠。</div>',
            unsafe_allow_html=True,
        )

    with tab4:
        shipping_analysis = compute_shipping_impact_analysis(df)

        fig = px.bar(
            shipping_analysis,
            x="has_shipping_fee",
            y="abandonment_rate",
            color="has_shipping_fee",
            title="运费对放弃率的影响",
            text="abandonment_rate",
        )
        fig.update_traces(texttemplate="%{text:.1f}%", textposition="outside")
        fig.update_layout(showlegend=False, yaxis_title="放弃率 (%)", xaxis_title="")
        st.plotly_chart(fig, use_container_width=True)

        st.dataframe(shipping_analysis, use_container_width=True)

        no_fee_rate = shipping_analysis[shipping_analysis["has_shipping_fee"] == "免运费"]["abandonment_rate"].values
        has_fee_rate = shipping_analysis[shipping_analysis["has_shipping_fee"] == "有运费"]["abandonment_rate"].values
        if len(no_fee_rate) > 0 and len(has_fee_rate) > 0:
            delta = has_fee_rate[0] - no_fee_rate[0]
            st.markdown(
                f'<div class="insight-box">💡 <b>运费洞察</b>：有运费时放弃率比免运费高出 <b>{delta:.1f}%</b>，运费是重要放弃因素。</div>',
                unsafe_allow_html=True,
            )

    with tab5:
        checkout_analysis, login_pct = compute_login_barrier_analysis(df)

        fig = px.bar(
            checkout_analysis,
            x="stage",
            y="percentage",
            color="stage",
            title="放弃用户的结算阶段分布",
            text="percentage",
        )
        fig.update_traces(texttemplate="%{text:.1f}%", textposition="outside")
        fig.update_layout(showlegend=False, yaxis_title="占比 (%)", xaxis_title="结算阶段")
        st.plotly_chart(fig, use_container_width=True)

        st.markdown(
            f'<div class="insight-box">💡 <b>登录门槛洞察</b>：约 <b>{login_pct:.1f}%</b> 的放弃用户在登录/注册环节流失，建议优化登录流程或提供游客结算。</div>',
            unsafe_allow_html=True,
        )


def render_ab_test(df):
    st.markdown("### 🧪 A/B 测试评估")

    tab1, tab2, tab3 = st.tabs(["测试结果", "显著性检验", "样本量估算"])

    with tab1:
        ab_results = compute_ab_test_results(df)

        st.markdown("#### 各组核心指标")
        display_df = ab_results[["group", "total_sessions", "completed", "abandonment_rate", "avg_cart_value", "avg_session_duration", "avg_pages_viewed"]].copy()
        display_df.columns = ["分组", "加购会话数", "完成数", "放弃率", "平均客单价", "平均时长(秒)", "平均页面数"]
        display_df["放弃率"] = display_df["放弃率"].apply(lambda x: f"{x * 100:.2f}%")
        display_df["平均客单价"] = display_df["平均客单价"].apply(lambda x: f"¥{x:.2f}")
        st.dataframe(display_df, use_container_width=True)

        col1, col2 = st.columns(2)
        with col1:
            fig = px.bar(
                ab_results,
                x="group",
                y="abandonment_rate",
                color="group",
                title="各组放弃率对比",
                text="abandonment_rate",
            )
            fig.update_traces(texttemplate="%{text:.2%}", textposition="outside")
            fig.update_layout(yaxis_title="放弃率", showlegend=False)
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            fig = px.bar(
                ab_results,
                x="group",
                y="avg_cart_value",
                color="group",
                title="各组平均客单价对比",
                text="avg_cart_value",
            )
            fig.update_traces(texttemplate="¥%{text:.2f}", textposition="outside")
            fig.update_layout(yaxis_title="平均客单价 (¥)", showlegend=False)
            st.plotly_chart(fig, use_container_width=True)

        cross, cross_pct = compute_ab_reason_comparison(df)
        st.markdown("#### 各组放弃原因分布对比")
        st.dataframe(cross_pct.style.format("{:.1f}%"), use_container_width=True)

    with tab2:
        st.markdown("#### 显著性检验")

        col1, col2 = st.columns(2)
        with col1:
            group_a = st.selectbox("对照组", df["ab_group"].unique().tolist(), index=0)
        with col2:
            group_b = st.selectbox("实验组", df["ab_group"].unique().tolist(), index=1)

        n_groups = len(df["ab_group"].unique())
        n_comparisons = n_groups * (n_groups - 1) // 2

        if group_a != group_b:
            result = perform_significance_test(df, group_a, group_b, n_comparisons)

            if "error" not in result:
                st.markdown("#### 检验结果")

                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric(f"{group_a} 完成率", f"{result['rate_a']:.2%}")
                with col2:
                    st.metric(f"{group_b} 完成率", f"{result['rate_b']:.2%}")
                with col3:
                    st.metric("提升幅度", f"{result['lift']:.2f}%", delta=f"{result['difference']:.4f}")
                with col4:
                    st.metric("P值", f"{result['p_value']:.6f}")

                sig_text = "✅ 统计显著" if result["significant_005"] else "❌ 不显著"
                st.markdown(f"**常规检验结论**：{sig_text}（α=0.05）")

                if result["significant_001"]:
                    st.markdown("**🌟 高度显著**（α=0.01）")

                st.markdown(f"**95%置信区间**：[{result['ci_95'][0]:.4f}, {result['ci_95'][1]:.4f}]")
                st.markdown(f"**Z值**：{result['z_score']:.4f}")

                st.markdown("---")
                st.markdown("#### 🔬 Bonferroni 校正（控制多重比较假阳性）")

                st.markdown(
                    f"当前共 <b>{n_groups}</b> 个组别，产生 <b>{n_comparisons}</b> 次两两比较。",
                    unsafe_allow_html=True,
                )

                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Bonferroni校正α", f"{result['bonferroni_alpha']:.6f}",
                               help=f"原始α=0.05 / 比较次数{n_comparisons}")
                with col2:
                    st.metric("校正后P值", f"{result['bonferroni_p_value']:.6f}",
                               help=f"原始P值 × {n_comparisons}，上限为1.0")
                with col3:
                    bonf_sig = result["bonferroni_significant"]
                    sig_label = "✅ 校正后仍显著" if bonf_sig else "❌ 校正后不显著"
                    st.metric("Bonferroni显著性", sig_label)

                st.markdown(
                    f'<div class="insight-box">🔬 <b>Bonferroni校正洞察</b>：校正后显著性阈值从0.05收紧至{result["bonferroni_alpha"]:.4f}，'
                    f'{"结果依然显著，假阳性风险可控" if bonf_sig else "校正后不再显著，原有差异可能由多重比较导致假阳性"}。</div>',
                    unsafe_allow_html=True,
                )

                st.markdown("#### 所有两两比较结果（含Bonferroni校正）")
                all_results = perform_all_pairwise_tests(df)
                comparison_rows = []
                for r in all_results:
                    if "error" not in r:
                        comparison_rows.append({
                            "对比": f"{r['group_a']} vs {r['group_b']}",
                            "A完成率": f"{r['rate_a']:.2%}",
                            "B完成率": f"{r['rate_b']:.2%}",
                            "原始P值": f"{r['p_value']:.6f}",
                            "原始显著": "✅" if r["significant_005"] else "❌",
                            "校正P值": f"{r['bonferroni_p_value']:.6f}",
                            "Bonferroni显著": "✅" if r["bonferroni_significant"] else "❌",
                            "提升幅度": f"{r['lift']:.2f}%",
                        })
                if comparison_rows:
                    st.dataframe(pd.DataFrame(comparison_rows), use_container_width=True)

                ab_trend = compute_ab_trend(df, group_a, group_b)
                if not ab_trend.empty:
                    fig = go.Figure()
                    fig.add_trace(go.Scatter(x=ab_trend["month"], y=ab_trend[f"rate_{group_a}"], mode="lines+markers", name=group_a, line=dict(color="#667eea")))
                    fig.add_trace(go.Scatter(x=ab_trend["month"], y=ab_trend[f"rate_{group_b}"], mode="lines+markers", name=group_b, line=dict(color="#f5576c")))
                    fig.update_layout(title="A/B组月度完成率趋势对比", yaxis_title="完成率", height=400)
                    st.plotly_chart(fig, use_container_width=True)
            else:
                st.warning(result["error"])
        else:
            st.warning("请选择不同的对照组和实验组")

    with tab3:
        st.markdown("#### A/B测试样本量估算器")

        col1, col2, col3, col4 = st.columns(4)
        with col1:
            baseline = st.number_input("基线完成率", value=0.30, min_value=0.01, max_value=0.99, step=0.01)
        with col2:
            mde = st.number_input("最小可检测效应(MDE)", value=0.10, min_value=0.01, max_value=1.0, step=0.01)
        with col3:
            alpha = st.number_input("显著性水平(α)", value=0.05, min_value=0.001, max_value=0.20, step=0.01)
        with col4:
            power = st.number_input("统计功效(Power)", value=0.80, min_value=0.50, max_value=0.99, step=0.01)

        estimate = compute_sample_size_estimate(baseline, mde, alpha, power)

        st.markdown(f"""
        **估算结果：**
        - 基线完成率：{estimate['baseline_rate']:.2%}
        - 期望实验组完成率：{estimate['expected_rate_treatment']:.2%}
        - **每组需要样本量：{estimate['sample_size_per_group']:,}**
        - **总样本量：{estimate['total_sample_size']:,}**
        """)


def render_strategies(df):
    st.markdown("### 💡 个性化干预策略建议")

    reason_attr = compute_reason_attribution(df)
    top_reason = reason_attr.iloc[0]["reason"]

    cart_df = df[df["behavior_path"].str.contains("加入购物车")]
    avg_sensitivity = cart_df["price_sensitivity_score"].mean()

    st.markdown(f"#### 基于当前数据，首要放弃原因为：<b style='color:#f5576c'>{top_reason}</b>")
    st.markdown(f"#### 全局平均价格敏感度：<b style='color:#764ba2'>{avg_sensitivity:.4f}</b>（0=不敏感，1=极度敏感）")

    st.markdown("---")
    st.markdown("### 🎯 个性化策略（按用户价格敏感度分层）")

    selected_reason = st.selectbox("选择放弃原因查看个性化策略", list(ABANDONMENT_REASONS.keys()), key="personalized_reason")

    for level in ["高", "中", "低"]:
        if level == "高":
            score_val = 0.75
        elif level == "中":
            score_val = 0.35
        else:
            score_val = 0.10

        strategies = get_personalized_strategies(selected_reason, score_val)

        level_emoji = {"高": "🔴", "中": "🟡", "低": "🟢"}
        level_desc = {"高": "score > 0.5 — 极度关注价格", "中": "0.2 < score ≤ 0.5 — 价格是考量因素", "低": "score ≤ 0.2 — 价格不敏感"}

        with st.expander(f"{level_emoji[level]} 价格敏感度【{level}】({level_desc[level]}) — {len(strategies)} 条策略"):
            for s in strategies:
                impact_class = "impact-high" if s["expected_impact"] == "高" else ("impact-medium" if s["expected_impact"] == "中" else "impact-low")
                effort_label = {"低": "🟢 低成本", "中": "🟡 中等", "高": "🔴 较高"}.get(s["implementation_effort"], s["implementation_effort"])

                st.markdown(f"""
                <div class="strategy-card">
                    <h4>{s['strategy']}</h4>
                    <p>{s['description']}</p>
                    <p>预期影响：<span class="{impact_class}">{s['expected_impact']}</span> | 实施成本：{effort_label} | 个性化力度：<b>{s.get('personalized_discount', '-')}</b></p>
                </div>
                """, unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("#### 📋 综合优先级建议（个性化加权）")

    all_strategies = []
    for _, row in reason_attr.iterrows():
        reason = row["reason"]
        pct = row["percentage"]
        for level, score_val in [("高", 0.75), ("中", 0.35), ("低", 0.10)]:
            for s in get_personalized_strategies(reason, score_val):
                s["reason"] = reason
                s["reason_pct"] = pct
                impact_score = {"高": 3, "中": 2, "低": 1}.get(s["expected_impact"], 1)
                effort_score = {"低": 3, "中": 2, "高": 1}.get(s["implementation_effort"], 1)
                sensitivity_weight = {"高": 1.5, "中": 1.0, "低": 0.6}.get(level, 1.0)
                s["priority_score"] = round(pct * impact_score * effort_score * sensitivity_weight / 100, 2)
                s["sensitivity_level"] = level
                all_strategies.append(s)

    all_strategies.sort(key=lambda x: x["priority_score"], reverse=True)

    for i, s in enumerate(all_strategies[:15], 1):
        impact_class = "impact-high" if s["expected_impact"] == "高" else ("impact-medium" if s["expected_impact"] == "中" else "impact-low")
        level_emoji = {"高": "🔴", "中": "🟡", "低": "🟢"}.get(s.get("sensitivity_level", ""), "")
        st.markdown(f"""
        **{i}. {s['strategy']}** | 归因：{s['reason']}({s['reason_pct']:.1f}%) | 敏感度：{level_emoji}{s.get('sensitivity_level', '')} | 预期影响：<span class="{impact_class}">{s['expected_impact']}</span> | 个性化：{s.get('personalized_discount', '-')} | 优先级：{s['priority_score']}

        {s['description']}

        ---
        """, unsafe_allow_html=True)


def render_risk_prediction(df):
    st.markdown("### ⚡ 放弃风险预测")

    tab1, tab2, tab3 = st.tabs(["风险模型", "风险分布", "实时预测模拟"])

    with tab1:
        with st.spinner("正在训练风险预测模型..."):
            model_result = train_risk_model(df)

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("模型AUC", f"{model_result['auc']:.4f}", help="模型区分度，越接近1越好")
        with col2:
            st.metric("5折交叉验证AUC", f"{model_result['cv_auc_mean']:.4f} ± {model_result['cv_auc_std']:.4f}")
        with col3:
            predictions = model_result["predictions"]
            high_risk = (predictions["risk_level"] == "高风险").sum()
            st.metric("高风险会话数", f"{high_risk:,}")

        st.markdown("#### 特征重要性（逻辑回归系数绝对值）")
        fi = model_result["feature_importance"].head(15)
        fig = px.bar(
            fi, x="abs_coefficient", y="feature", orientation="h",
            title="Top 15 特征重要性",
            color="abs_coefficient", color_continuous_scale="Reds",
        )
        fig.update_layout(yaxis=dict(autorange="reversed"), height=500, showlegend=False)
        st.plotly_chart(fig, use_container_width=True)

        st.markdown("#### 特征系数方向（正=促进完成，负=促进放弃）")
        fi_direction = model_result["feature_importance"].copy()
        fig2 = px.bar(
            fi_direction, x="coefficient", y="feature", orientation="h",
            title="特征系数方向性",
            color=fi_direction["coefficient"].apply(lambda x: "促进完成" if x > 0 else "促进放弃"),
            color_discrete_map={"促进完成": "#28a745", "促进放弃": "#dc3545"},
        )
        fig2.update_layout(yaxis=dict(autorange="reversed"), height=500)
        st.plotly_chart(fig2, use_container_width=True)

    with tab2:
        risk_dist = compute_risk_distribution(df, model_result)

        col1, col2 = st.columns(2)

        with col1:
            fig = px.bar(
                risk_dist, x="risk_level", y="count", color="risk_level",
                title="风险等级分布",
                text="count",
                color_discrete_map={"低风险": "#28a745", "中风险": "#ffc107", "高风险": "#dc3545"},
            )
            fig.update_traces(textposition="outside")
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            fig = px.bar(
                risk_dist, x="risk_level", y="actual_abandon_rate", color="risk_level",
                title="各风险等级实际放弃率",
                text="actual_abandon_rate",
                color_discrete_map={"低风险": "#28a745", "中风险": "#ffc107", "高风险": "#dc3545"},
            )
            fig.update_traces(texttemplate="%{text:.1f}%", textposition="outside")
            fig.update_layout(yaxis_title="实际放弃率 (%)")
            st.plotly_chart(fig, use_container_width=True)

        st.dataframe(risk_dist, use_container_width=True)

        seg_risk = compute_risk_by_segment(df, model_result)
        st.markdown("#### 各用户群体风险画像")
        fig = px.bar(
            seg_risk, x="user_segment", y="avg_risk_score", color="user_segment",
            title="各群体平均风险评分",
        )
        fig.update_layout(yaxis_title="平均风险评分", showlegend=False)
        st.plotly_chart(fig, use_container_width=True)
        st.dataframe(seg_risk, use_container_width=True)

    with tab3:
        st.markdown("#### 实时风险预测模拟")
        st.markdown("模拟用户进入购物车页面时的实时风险评分计算逻辑")

        realtime_df = simulate_realtime_prediction(df)

        risk_level_counts = realtime_df["realtime_risk_level"].value_counts()
        fig = px.pie(
            values=risk_level_counts.values,
            names=risk_level_counts.index,
            title="实时风险等级分布",
            hole=0.4,
            color_discrete_map={"低风险": "#28a745", "中风险": "#ffc107", "高风险": "#dc3545"},
        )
        fig.update_traces(textposition="inside", textinfo="percent+label")
        st.plotly_chart(fig, use_container_width=True)

        risk_accuracy = realtime_df.groupby("realtime_risk_level").agg(
            total=("session_id", "count"),
            actual_abandon_rate=("completed", lambda x: (1 - x).mean() * 100),
        ).reset_index()
        risk_accuracy["actual_abandon_rate"] = risk_accuracy["actual_abandon_rate"].round(2)

        st.dataframe(risk_accuracy, use_container_width=True)

        st.markdown("#### 触发干预规则示例")
        st.markdown("""
        | 风险信号 | 条件 | 触发动作 |
        |---------|------|---------|
        | 犹豫评分 ≥ 5 | 反复浏览/离开/切换标签 | 弹窗挽留 |
        | 价格敏感度 > 0.5 + 竞品更低价 | 用户可能被竞品吸引 | 即时比价展示/限时优惠 |
        | 有运费 + 低客单价 | 运费占比过高 | 凑单免运费提醒 |
        | 新用户 + 犹豫评分 ≥ 3 | 新用户不熟悉流程 | 引导简化结算 |
        """)


def render_realtime_intervention(df):
    st.markdown("### 🚀 实时干预引擎")

    tab1, tab2, tab3 = st.tabs(["干预总览", "干预效果分析", "实时模拟"])

    with tab1:
        summary = compute_intervention_summary(df)

        col1, col2, col3, col4, col5 = st.columns(5)
        with col1:
            st.metric("放弃会话数", f"{summary['total_abandoned']:,}")
        with col2:
            st.metric("干预触发率", f"{summary['trigger_rate']:.1f}%")
        with col3:
            st.metric("干预接受率", f"{summary['accept_rate']:.1f}%")
        with col4:
            st.metric("干预转化率", f"{summary['convert_rate']:.1f}%")
        with col5:
            st.metric("整体挽回率", f"{summary['overall_recovery_rate']:.1f}%")

        st.markdown(
            f'<div class="insight-box">🚀 <b>实时干预效果</b>：在{summary["total_abandoned"]:,}个放弃会话中，'
            f'触发干预{summary["intervention_triggered_count"]:,}次，'
            f'成功挽回{summary["intervention_converted_count"]:,}单，'
            f'整体挽回率{summary["overall_recovery_rate"]:.1f}%。</div>',
            unsafe_allow_html=True,
        )

        reason_stats = compute_intervention_by_reason(df)
        if not reason_stats.empty:
            st.markdown("#### 各放弃原因的干预效果")
            fig = px.bar(
                reason_stats, x="abandonment_reason", y="convert_rate", color="abandonment_reason",
                title="各原因干预转化率",
                text="convert_rate",
            )
            fig.update_traces(texttemplate="%{text:.1f}%", textposition="outside")
            fig.update_layout(showlegend=False, yaxis_title="干预转化率 (%)")
            st.plotly_chart(fig, use_container_width=True)

    with tab2:
        type_stats = compute_intervention_by_type(df)
        if not type_stats.empty:
            st.markdown("#### 各干预类型效果对比")
            fig = make_subplots(rows=1, cols=2, subplot_titles=("接受率", "转化率"))
            fig.add_trace(go.Bar(x=type_stats["intervention_type"], y=type_stats["accept_rate"], name="接受率", marker_color="#667eea"), row=1, col=1)
            fig.add_trace(go.Bar(x=type_stats["intervention_type"], y=type_stats["convert_rate"], name="转化率", marker_color="#f5576c"), row=1, col=2)
            fig.update_layout(height=400, showlegend=False)
            st.plotly_chart(fig, use_container_width=True)

            st.dataframe(type_stats, use_container_width=True)

        timing_stats = compute_intervention_by_timing(df)
        if not timing_stats.empty:
            st.markdown("#### 干预时机效果分析")
            fig = px.bar(
                timing_stats, x="timing_bucket", y="convert_rate", color="timing_bucket",
                title="不同干预时机的转化率",
                text="convert_rate",
            )
            fig.update_traces(texttemplate="%{text:.1f}%", textposition="outside")
            fig.update_layout(showlegend=False, xaxis_title="干预时机", yaxis_title="转化率 (%)")
            st.plotly_chart(fig, use_container_width=True)

        timeline = compute_intervention_timeline(df)
        if not timeline.empty:
            fig = make_subplots(specs=[[{"secondary_y": True}]])
            fig.add_trace(go.Scatter(x=timeline["month"], y=timeline["accept_rate"], mode="lines+markers", name="接受率", line=dict(color="#667eea")), secondary_y=False)
            fig.add_trace(go.Scatter(x=timeline["month"], y=timeline["convert_rate"], mode="lines+markers", name="转化率", line=dict(color="#f5576c")), secondary_y=True)
            fig.update_layout(title="干预效果月度趋势", height=400)
            fig.update_yaxes(title_text="接受率 (%)", secondary_y=False)
            fig.update_yaxes(title_text="转化率 (%)", secondary_y=True)
            st.plotly_chart(fig, use_container_width=True)

    with tab3:
        st.markdown("#### 实时干预模拟器")

        risk_threshold = st.slider("干预触发风险阈值", 0.0, 1.0, 0.6, 0.05)

        sim = simulate_realtime_intervention(df, risk_threshold)

        st.markdown(f"**当前阈值**：{sim['risk_threshold_used']} | **高风险会话**：{sim['total_high_risk_sessions']:,}")

        st.markdown("##### 高风险用户干预场景分布")
        for scenario, count in sim["intervention_breakdown"].items():
            pct = count / sim["total_high_risk_sessions"] * 100 if sim["total_high_risk_sessions"] > 0 else 0
            st.markdown(f"- **{scenario}**：{count:,} 个会话 ({pct:.1f}%)")

        st.markdown("##### 最优干预时机建议")
        for timing, desc in sim["optimal_timing_guidance"].items():
            st.markdown(f"- **{timing}**：{desc}")


def render_competitor_analysis(df):
    st.markdown("### 🏷️ 竞品价格影响分析")

    tab1, tab2, tab3, tab4 = st.tabs(["竞品总览", "价差与放弃率", "品类对比", "敏感度交叉"])

    with tab1:
        comp_impact = compute_competitor_impact(df)

        col1, col2 = st.columns(2)
        with col1:
            fig = px.bar(
                comp_impact, x="has_lower_competitor", y="abandonment_rate", color="has_lower_competitor",
                title="竞品价格对放弃率的影响",
                text="abandonment_rate",
            )
            fig.update_traces(texttemplate="%{text:.1f}%", textposition="outside")
            fig.update_layout(showlegend=False, yaxis_title="放弃率 (%)", xaxis_title="")
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            fig = px.bar(
                comp_impact, x="has_lower_competitor", y="avg_price_diff", color="has_lower_competitor",
                title="平均价差（本平台 - 竞品最低价）",
                text="avg_price_diff",
            )
            fig.update_traces(texttemplate="¥%{text:.2f}", textposition="outside")
            fig.update_layout(showlegend=False, yaxis_title="价差 (¥)", xaxis_title="")
            st.plotly_chart(fig, use_container_width=True)

        st.dataframe(comp_impact, use_container_width=True)

        lower_row = comp_impact[comp_impact["has_lower_competitor"] == "竞品更低价"]
        no_lower_row = comp_impact[comp_impact["has_lower_competitor"] == "本平台最低价"]
        if not lower_row.empty and not no_lower_row.empty:
            delta = lower_row["abandonment_rate"].values[0] - no_lower_row["abandonment_rate"].values[0]
            st.markdown(
                f'<div class="insight-box">🏷️ <b>竞品洞察</b>：存在竞品更低价时放弃率比本平台最低价时高出 <b>{delta:.1f}%</b>，竞品价格显著影响转化。</div>',
                unsafe_allow_html=True,
            )

    with tab2:
        price_diff = compute_price_diff_abandonment(df)

        fig = px.bar(
            price_diff, x="price_diff_bucket", y="abandonment_rate", color="price_diff_bucket",
            title="价差区间 vs 放弃率",
            text="abandonment_rate",
            color_discrete_sequence=px.colors.RdYlGn_r,
        )
        fig.update_traces(texttemplate="%{text:.1f}%", textposition="outside")
        fig.update_layout(xaxis_title="价差区间", yaxis_title="放弃率 (%)", showlegend=False)
        st.plotly_chart(fig, use_container_width=True)

        st.dataframe(price_diff, use_container_width=True)

        st.markdown(
            '<div class="insight-box">💡 <b>价差洞察</b>：本平台价格高出竞品10%以上时放弃率急剧上升，建议对高价差商品启动价格匹配或限时优惠。</div>',
            unsafe_allow_html=True,
        )

    with tab3:
        cat_comp = compute_competitor_by_category(df)

        fig = make_subplots(specs=[[{"secondary_y": True}]])
        fig.add_trace(
            go.Bar(x=cat_comp["product_category"], y=cat_comp["abandonment_rate"], name="放弃率", marker_color="#f5576c"),
            secondary_y=False,
        )
        fig.add_trace(
            go.Scatter(x=cat_comp["product_category"], y=cat_comp["has_lower_pct"], mode="lines+markers", name="竞品更低价占比", line=dict(color="#667eea", width=2)),
            secondary_y=True,
        )
        fig.update_layout(title="各品类放弃率 vs 竞品更低价占比", height=450)
        fig.update_yaxes(title_text="放弃率 (%)", secondary_y=False)
        fig.update_yaxes(title_text="竞品更低价占比 (%)", secondary_y=True)
        st.plotly_chart(fig, use_container_width=True)

        st.dataframe(cat_comp, use_container_width=True)

    with tab4:
        sens_comp = compute_competitor_by_sensitivity(df)

        fig = px.bar(
            sens_comp, x="sensitivity_level", y="abandonment_rate", color="has_lower_competitor",
            barmode="group",
            title="价格敏感度 × 竞品价格 对放弃率的交叉影响",
            text="abandonment_rate",
        )
        fig.update_traces(texttemplate="%{text:.1f}%", textposition="outside")
        fig.update_layout(yaxis_title="放弃率 (%)")
        st.plotly_chart(fig, use_container_width=True)

        st.dataframe(sens_comp, use_container_width=True)

        st.markdown(
            '<div class="insight-box">🏷️ <b>交叉洞察</b>：高敏感度+竞品更低价的组合放弃率最高，应优先对此类用户推送价格保障或限时优惠。</div>',
            unsafe_allow_html=True,
        )


def main():
    st.markdown('<div class="main-header">🛒 电商购物车放弃分析平台</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">分析用户加购后未下单的行为路径 · 识别放弃原因 · 输出干预策略与A/B测试评估</div>', unsafe_allow_html=True)

    df = load_data()
    filtered_df = render_sidebar(df)

    render_overview_metrics(filtered_df)

    st.markdown("---")

    page = st.sidebar.radio(
        "📍 功能导航",
        ["📊 漏斗分析", "📈 趋势分析", "🎯 归因分析", "🏷️ 竞品对比", "⚡ 风险预测", "🚀 实时干预", "🧪 A/B测试", "💡 策略建议"],
    )

    if page == "📊 漏斗分析":
        render_funnel_analysis(filtered_df)
    elif page == "📈 趋势分析":
        render_trend_analysis(filtered_df)
    elif page == "🎯 归因分析":
        render_attribution_analysis(filtered_df)
    elif page == "🏷️ 竞品对比":
        render_competitor_analysis(filtered_df)
    elif page == "⚡ 风险预测":
        render_risk_prediction(filtered_df)
    elif page == "🚀 实时干预":
        render_realtime_intervention(filtered_df)
    elif page == "🧪 A/B测试":
        render_ab_test(filtered_df)
    elif page == "💡 策略建议":
        render_strategies(filtered_df)

    with st.sidebar.expander("📊 数据概览"):
        st.write(f"数据量：{len(filtered_df):,} 条会话")
        st.write(f"时间范围：{filtered_df['date'].min()} ~ {filtered_df['date'].max()}")
        st.write(f"用户群体：{', '.join(filtered_df['user_segment'].unique())}")
        st.write(f"商品品类：{', '.join(filtered_df['product_category'].unique())}")
        if st.button("🔄 刷新数据"):
            st.cache_data.clear()
            st.rerun()


if __name__ == "__main__":
    main()
