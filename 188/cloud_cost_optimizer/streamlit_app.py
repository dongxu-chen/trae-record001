import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import date, datetime, timedelta
import json

from .app import CloudCostOptimizer
from .config import Settings

st.set_page_config(
    page_title="多云费用分析优化工具",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="expanded",
)


def init_session_state():
    if "optimizer" not in st.session_state:
        settings = Settings()
        settings.aws.enabled = True
        settings.aliyun.enabled = True
        settings.tencent.enabled = True
        st.session_state.optimizer = CloudCostOptimizer(settings)

    if "dashboard_data" not in st.session_state:
        st.session_state.dashboard_data = None

    if "trend_data" not in st.session_state:
        st.session_state.trend_data = None

    if "anomaly_data" not in st.session_state:
        st.session_state.anomaly_data = None

    if "optimization_data" not in st.session_state:
        st.session_state.optimization_data = None

    if "allocation_data" not in st.session_state:
        st.session_state.allocation_data = None


def format_currency(value, currency="CNY"):
    if currency == "CNY":
        return f"¥{value:,.2f}"
    elif currency == "USD":
        return f"${value:,.2f}"
    return f"{value:,.2f}"


def get_severity_color(severity):
    colors = {
        "critical": "#ff4b4b",
        "high": "#ff9f43",
        "medium": "#ffd93d",
        "low": "#6bcb77",
    }
    return colors.get(severity, "#888888")


def get_priority_color(priority):
    colors = {
        "high": "#ff4b4b",
        "medium": "#ff9f43",
        "low": "#6bcb77",
    }
    return colors.get(priority, "#888888")


def sidebar():
    with st.sidebar:
        st.title("💰 多云费用分析优化工具")
        st.markdown("---")

        st.subheader("📅 时间范围")
        col1, col2 = st.columns(2)
        with col1:
            start_date = st.date_input(
                "开始日期",
                value=date.today() - timedelta(days=30),
                key="start_date",
            )
        with col2:
            end_date = st.date_input(
                "结束日期",
                value=date.today() + timedelta(days=1),
                key="end_date",
            )

        st.markdown("---")
        st.subheader("⚙️ 操作")

        if st.button("🔄 刷新数据", use_container_width=True):
            with st.spinner("正在获取最新数据..."):
                st.session_state.dashboard_data = st.session_state.optimizer.get_dashboard_data(30)
                st.success("数据已刷新！")

        if st.button("📊 完整分析", use_container_width=True):
            with st.spinner("正在执行完整分析..."):
                results = st.session_state.optimizer.run_full_analysis()
                st.session_state.dashboard_data = st.session_state.optimizer.get_dashboard_data(30)
                st.session_state.trend_data = results["trend_analysis"]
                st.session_state.anomaly_data = results["anomaly_detection"]
                st.session_state.optimization_data = results["optimization"]
                st.session_state.allocation_data = results["cost_allocation"]
                st.success("完整分析完成！")

        st.markdown("---")
        st.subheader("🏢 云厂商状态")
        provider_status = st.session_state.optimizer.get_provider_status()
        for name, status in provider_status.items():
            if status.get("enabled"):
                st.success(f"✅ {name} ({status.get('region', 'unknown')})")
            else:
                st.error(f"❌ {name}")

        st.markdown("---")
        st.caption("Powered by Python + ClickHouse + Streamlit")


def dashboard_page():
    st.header("📈 费用总览")

    if st.session_state.dashboard_data is None:
        with st.spinner("正在加载数据..."):
            st.session_state.dashboard_data = st.session_state.optimizer.get_dashboard_data(30)

    data = st.session_state.dashboard_data
    if "error" in data:
        st.warning(data["error"])
        return

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric(
            "总费用",
            format_currency(data["total_cost"]),
            delta=f"{data['period_days']}天",
        )
    with col2:
        st.metric("云厂商数量", data["provider_count"])
    with col3:
        st.metric("服务数量", data["service_count"])
    with col4:
        st.metric("资源数量", data["resource_count"])

    st.markdown("---")

    col1, col2 = st.columns([2, 1])

    with col1:
        st.subheader("📅 每日费用趋势")
        daily_df = pd.DataFrame(list(data["daily_cost"].items()), columns=["date", "cost"])
        daily_df["date"] = pd.to_datetime(daily_df["date"])
        daily_df = daily_df.sort_values("date")

        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=daily_df["date"],
            y=daily_df["cost"],
            name="日费用",
            marker_color="#4e79a7",
        ))
        fig.add_trace(go.Scatter(
            x=daily_df["date"],
            y=daily_df["cost"].rolling(7).mean(),
            name="7日移动平均",
            line=dict(color="#f28e2b", width=2),
        ))
        fig.update_layout(
            height=400,
            hovermode="x unified",
            showlegend=True,
            margin=dict(l=0, r=0, t=20, b=0),
        )
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.subheader("🏢 按云厂商分布")
        provider_df = pd.DataFrame(
            list(data["cost_by_provider"].items()),
            columns=["provider", "cost"],
        )
        fig = px.pie(
            provider_df,
            values="cost",
            names="provider",
            color_discrete_sequence=px.colors.qualitative.Set3,
        )
        fig.update_layout(height=400, margin=dict(l=0, r=0, t=20, b=0))
        st.plotly_chart(fig, use_container_width=True)

    st.markdown("---")

    col1, col2 = st.columns([3, 2])

    with col1:
        st.subheader("📦 Top 10 服务费用")
        services_df = pd.DataFrame(data["top_services"], columns=["service", "cost"])
        fig = px.bar(
            services_df,
            x="cost",
            y="service",
            orientation="h",
            color="cost",
            color_continuous_scale="Blues",
        )
        fig.update_layout(
            height=500,
            yaxis=dict(autorange="reversed"),
            margin=dict(l=0, r=0, t=20, b=0),
        )
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.subheader("📊 费用分布")
        st.dataframe(
            services_df.style.format({"cost": "{:,.2f}"}),
            use_container_width=True,
            height=500,
        )


def trend_page():
    st.header("📈 趋势分析")

    if st.button("运行趋势分析", type="primary"):
        with st.spinner("正在分析趋势..."):
            start = st.session_state.start_date
            end = st.session_state.end_date
            st.session_state.trend_data = st.session_state.optimizer.run_trend_analysis(start, end)
            st.success("趋势分析完成！")

    if st.session_state.trend_data is None:
        st.info("请点击上方按钮运行趋势分析")
        return

    data = st.session_state.trend_data
    if "error" in data:
        st.warning(data["error"])
        return

    col1, col2, col3 = st.columns(3)

    with col1:
        growth = data["growth_rate"]
        st.metric(
            f"{growth['period_days']}天增长率",
            f"{growth['growth_rate']:.1f}%",
            delta=f"{'增长' if growth['is_growing'] else '下降'}",
            delta_color="inverse",
        )

    with col2:
        forecast = data["forecast"]
        st.metric(
            "下月预测",
            format_currency(forecast["forecast"]),
            delta=f"置信度 {forecast['confidence']:.0%}",
        )

    with col3:
        monthly = data["monthly_summary"]
        if monthly:
            last_month = monthly[-1]
            st.metric(
                "本月费用",
                format_currency(last_month["total_cost"]),
                delta=f"{last_month['change_percentage']:.1f}%",
                delta_color="inverse",
            )

    st.markdown("---")

    st.subheader("📅 每日费用趋势明细")
    daily_df = pd.DataFrame(data["daily_trend"])
    if not daily_df.empty:
        daily_df["date"] = pd.to_datetime(daily_df["date"])
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=daily_df["date"],
            y=daily_df["total_cost"],
            mode="lines+markers",
            name="实际费用",
            line=dict(color="#4e79a7", width=2),
        ))
        fig.add_trace(go.Scatter(
            x=daily_df["date"],
            y=daily_df["moving_average_7d"],
            name="7日移动平均",
            line=dict(color="#f28e2b", width=2, dash="dash"),
        ))
        fig.update_layout(
            height=400,
            hovermode="x unified",
            margin=dict(l=0, r=0, t=20, b=0),
        )
        st.plotly_chart(fig, use_container_width=True)

        st.dataframe(
            daily_df[["date", "total_cost", "previous_day_cost", "change_percentage", "moving_average_7d"]]
            .sort_values("date", ascending=False)
            .style.format({
                "total_cost": "{:,.2f}",
                "previous_day_cost": "{:,.2f}",
                "change_percentage": "{:.1f}%",
                "moving_average_7d": "{:,.2f}",
            }),
            use_container_width=True,
        )

    st.markdown("---")

    st.subheader("📦 服务趋势分析")
    service_trend = data["service_trend"]
    if service_trend:
        services = list(service_trend.keys())
        selected_service = st.selectbox("选择服务", services)
        if selected_service:
            service_df = pd.DataFrame(service_trend[selected_service])
            if not service_df.empty:
                service_df["date"] = pd.to_datetime(service_df["date"])
                fig = px.line(
                    service_df,
                    x="date",
                    y="total_cost",
                    title=f"{selected_service} 费用趋势",
                )
                fig.update_layout(height=350)
                st.plotly_chart(fig, use_container_width=True)

    st.markdown("---")

    st.subheader("📊 月度汇总")
    monthly_df = pd.DataFrame(data["monthly_summary"])
    if not monthly_df.empty:
        monthly_df["month"] = pd.to_datetime(monthly_df["month"])
        st.dataframe(
            monthly_df.sort_values("month", ascending=False)
            .style.format({
                "total_cost": "{:,.2f}",
                "previous_month_cost": "{:,.2f}",
                "change_percentage": "{:.1f}%",
            }),
            use_container_width=True,
        )


def anomaly_page():
    st.header("⚠️ 异常检测")

    if st.button("运行异常检测", type="primary"):
        with st.spinner("正在检测异常..."):
            start = st.session_state.start_date
            end = st.session_state.end_date
            st.session_state.anomaly_data = st.session_state.optimizer.run_anomaly_detection(start, end)
            st.success("异常检测完成！")

    if st.session_state.anomaly_data is None:
        st.info("请点击上方按钮运行异常检测")
        return

    data = st.session_state.anomaly_data
    if "error" in data:
        st.warning(data["error"])
        return

    col1, col2, col3, col4, col5, col6 = st.columns(6)
    with col1:
        st.metric("总异常数", data["total_anomalies"])
    with col2:
        st.metric("🔴 严重", data["critical_count"])
    with col3:
        st.metric("🟠 高", data["high_count"])
    with col4:
        st.metric("🟡 中", data["medium_count"])
    with col5:
        st.metric("🟢 低", data["low_count"])
    with col6:
        st.metric("📅 周期性异常", data.get("periodicity_count", 0))

    if data["needs_attention"]:
        st.error("⚠️ 发现需要关注的异常，请查看下方详情！")

    st.markdown("---")

    if "anomalies" in data and data["anomalies"]:
        anomalies_df = pd.DataFrame(data["anomalies"])
        anomalies_df["severity_order"] = anomalies_df["severity"].map(
            {"critical": 0, "high": 1, "medium": 2, "low": 3}
        )
        anomalies_df = anomalies_df.sort_values(
            ["severity_order", "percentage_change"],
            ascending=[True, False],
        ).drop("severity_order", axis=1)

        severity_filter = st.multiselect(
            "按严重程度过滤",
            ["critical", "high", "medium", "low"],
            default=["critical", "high"],
        )
        type_filter = st.multiselect(
            "按异常类型过滤",
            anomalies_df["anomaly_type"].unique().tolist(),
            default=anomalies_df["anomaly_type"].unique().tolist(),
        )

        if severity_filter:
            anomalies_df = anomalies_df[anomalies_df["severity"].isin(severity_filter)]
        if type_filter:
            anomalies_df = anomalies_df[anomalies_df["anomaly_type"].isin(type_filter)]

        st.subheader("📋 异常列表")

        for _, row in anomalies_df.iterrows():
            with st.expander(
                f"{get_severity_icon(row['severity'])} "
                f"[{row['severity'].upper()}] "
                f"{row['anomaly_date']} - {row['service_name']} "
                f"(+{row['percentage_change']:.1f}%)"
            ):
                col1, col2 = st.columns(2)
                with col1:
                    st.write(f"**云厂商:** {row['provider']}")
                    st.write(f"**服务:** {row['service_name']}")
                    if row["resource_id"]:
                        st.write(f"**资源:** {row['resource_id']}")
                with col2:
                    st.write(f"**预期费用:** {format_currency(row['expected_cost'])}")
                    st.write(f"**实际费用:** {format_currency(row['actual_cost'])}")
                    st.write(f"**变化:** {row['percentage_change']:.1f}%")
                st.info(f"📝 {row['description']}")

        st.markdown("---")

        st.subheader("📊 异常分布")
        col1, col2 = st.columns(2)
        with col1:
            severity_counts = anomalies_df["severity"].value_counts()
            fig = px.pie(
                values=severity_counts.values,
                names=severity_counts.index,
                title="按严重程度分布",
                color=severity_counts.index,
                color_discrete_map={
                    "critical": "#ff4b4b",
                    "high": "#ff9f43",
                    "medium": "#ffd93d",
                    "low": "#6bcb77",
                },
            )
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            type_counts = anomalies_df["anomaly_type"].value_counts()
            fig = px.bar(
                x=type_counts.values,
                y=type_counts.index,
                orientation="h",
                title="按异常类型分布",
            )
            st.plotly_chart(fig, use_container_width=True)


def get_severity_icon(severity):
    icons = {
        "critical": "🔴",
        "high": "🟠",
        "medium": "🟡",
        "low": "🟢",
    }
    return icons.get(severity, "⚪")


def optimization_page():
    st.header("💡 优化建议")

    if st.button("运行优化分析", type="primary"):
        with st.spinner("正在分析优化机会..."):
            start = st.session_state.start_date
            end = st.session_state.end_date
            st.session_state.optimization_data = st.session_state.optimizer.run_optimization_analysis(start, end)
            st.success("优化分析完成！")

    if st.session_state.optimization_data is None:
        st.info("请点击上方按钮运行优化分析")
        return

    data = st.session_state.optimization_data
    if "error" in data:
        st.warning(data["error"])
        return

    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        st.metric(
            "总节省潜力",
            format_currency(data["total_estimated_savings"]),
            delta=f"{data['overall_savings_percentage']:.1f}%",
        )
    with col2:
        st.metric("优化建议数量", data["total_suggestions"])
    with col3:
        st.metric("涉及成本", format_currency(data["total_current_cost"]))
    with col4:
        st.metric("✅ 可安全释放", data.get("safe_suggestions_count", data["total_suggestions"]))
    with col5:
        st.metric("⚠️ 存在依赖", data.get("risky_suggestions_count", 0))

    st.markdown("---")

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("📊 节省分布")
        if "savings_by_type" in data:
            savings_df = pd.DataFrame(
                list(data["savings_by_type"].items()),
                columns=["type", "savings"],
            )
            fig = px.pie(
                savings_df,
                values="savings",
                names="type",
                title="按优化类型分布",
            )
            st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.subheader("🎯 优先级分布")
        if "priority_counts" in data:
            priority_df = pd.DataFrame(
                list(data["priority_counts"].items()),
                columns=["priority", "count"],
            )
            fig = px.bar(
                priority_df,
                x="count",
                y="priority",
                orientation="h",
                color="priority",
                color_discrete_map={
                    "high": "#ff4b4b",
                    "medium": "#ff9f43",
                    "low": "#6bcb77",
                },
                title="按优先级分布",
            )
            st.plotly_chart(fig, use_container_width=True)

    st.markdown("---")

    if "suggestions" in data and data["suggestions"]:
        suggestions_df = pd.DataFrame(data["suggestions"])
        suggestions_df["priority_order"] = suggestions_df["priority"].map(
            {"high": 0, "medium": 1, "low": 2}
        )
        suggestions_df = suggestions_df.sort_values(
            ["priority_order", "estimated_savings"],
            ascending=[True, False],
        ).drop("priority_order", axis=1)

        priority_filter = st.multiselect(
            "按优先级过滤",
            ["high", "medium", "low"],
            default=["high", "medium"],
        )
        type_filter = st.multiselect(
            "按建议类型过滤",
            suggestions_df["suggestion_type"].unique().tolist(),
            default=suggestions_df["suggestion_type"].unique().tolist(),
        )

        if priority_filter:
            suggestions_df = suggestions_df[suggestions_df["priority"].isin(priority_filter)]
        if type_filter:
            suggestions_df = suggestions_df[suggestions_df["suggestion_type"].isin(type_filter)]

        st.subheader("📋 优化建议列表")

        for _, row in suggestions_df.iterrows():
            icon = get_suggestion_icon(row["suggestion_type"])
            risk_icon = "⚠️" if not row.get("can_release", True) else "✅"
            risk_label = "存在依赖" if not row.get("can_release", True) else "可安全操作"

            with st.expander(
                f"{icon} {risk_icon} "
                f"[{row['priority'].upper()}] "
                f"{row['description']} "
                f"({format_currency(row['estimated_savings'])} 节省)"
            ):
                col1, col2 = st.columns(2)
                with col1:
                    st.write(f"**云厂商:** {row['provider']}")
                    st.write(f"**服务:** {row['service_name']}")
                    if row["resource_id"]:
                        st.write(f"**资源:** {row['resource_id']}")
                    st.write(f"**操作风险:** {row.get('risk_level', 'low').upper()}")
                    st.write(f"**安全释放:** {'是' if row.get('can_release', True) else '否'}")
                with col2:
                    st.write(f"**当前成本:** {format_currency(row['current_cost'])}")
                    st.write(f"**预估节省:** {format_currency(row['estimated_savings'])}")
                    st.write(f"**节省比例:** {row['savings_percentage']:.1f}%")

                st.success(f"💡 {row['details']}")

                if not row.get("can_release", True):
                    st.warning(f"⚠️ 该资源存在依赖关系，请谨慎操作！")
                    if row.get("dependent_resources"):
                        st.write(f"**依赖资源:** {', '.join(row['dependent_resources'])}")
                    if row.get("dependency_warnings"):
                        for warning in row["dependency_warnings"]:
                            st.write(f"  - {warning}")
                    if row.get("dependency_suggestions"):
                        st.info("💡 建议操作：")
                        for suggestion in row["dependency_suggestions"]:
                            st.write(f"  - {suggestion}")


def get_suggestion_icon(suggestion_type):
    icons = {
        "idle_resource": "🗑️",
        "reserved_instance": "📅",
        "downsize": "⬇️",
        "upsize": "⬆️",
        "storage_optimization": "💾",
    }
    return icons.get(suggestion_type, "💡")


def allocation_page():
    st.header("🏷️ 费用分摊")

    if st.button("运行费用分摊", type="primary"):
        with st.spinner("正在执行费用分摊..."):
            st.session_state.allocation_data = st.session_state.optimizer.run_cost_allocation()
            st.success("费用分摊完成！")

    if st.session_state.allocation_data is None:
        st.info("请点击上方按钮运行费用分摊")
        return

    data = st.session_state.allocation_data
    if "error" in data:
        st.warning(data["error"])
        return

    label_keys = [k for k in data.keys() if k != "unallocated"]
    selected_label = st.selectbox("选择标签键", label_keys)

    if selected_label and selected_label in data:
        allocations = data[selected_label]["allocations"]

        if allocations:
            col1, col2 = st.columns([2, 1])

            with col1:
                st.subheader(f"📊 按 {selected_label} 分摊")
                alloc_df = pd.DataFrame(allocations)
                fig = px.bar(
                    alloc_df,
                    x="total_cost",
                    y="label_value",
                    orientation="h",
                    color="total_cost",
                    color_continuous_scale="Viridis",
                )
                fig.update_layout(
                    height=500,
                    yaxis=dict(autorange="reversed"),
                )
                st.plotly_chart(fig, use_container_width=True)

            with col2:
                st.subheader("💰 费用分布")
                fig = px.pie(
                    alloc_df,
                    values="total_cost",
                    names="label_value",
                )
                fig.update_layout(height=500)
                st.plotly_chart(fig, use_container_width=True)

            st.markdown("---")
            st.subheader("📋 分摊明细")

            display_df = alloc_df[["label_value", "total_cost", "resource_count"]].copy()
            display_df["percentage"] = (
                display_df["total_cost"] / display_df["total_cost"].sum() * 100
            )
            st.dataframe(
                display_df.style.format({
                    "total_cost": "{:,.2f}",
                    "percentage": "{:.1f}%",
                }),
                use_container_width=True,
            )

    if "unallocated" in data:
        st.markdown("---")
        unallocated = data["unallocated"]
        st.subheader("⚠️ 未分摊资源")

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("未分摊费用", format_currency(unallocated["total_cost"]))
        with col2:
            st.metric("资源数量", unallocated["resource_count"])
        with col3:
            st.metric("记录数量", unallocated["record_count"])

        if unallocated["services"]:
            st.warning("以下服务存在未打标签的资源，请补充标签以便准确分摊：")
            services_df = pd.DataFrame(
                unallocated["services"],
                columns=["service", "cost"],
            ).sort_values("cost", ascending=False)
            st.dataframe(
                services_df.style.format({"cost": "{:,.2f}"}),
                use_container_width=True,
            )


def product_mapping_page():
    st.header("🗂️ 产品映射表")

    if "product_mapping_data" not in st.session_state:
        st.session_state.product_mapping_data = None

    if st.button("执行产品映射", type="primary"):
        with st.spinner("正在执行产品名称统一映射..."):
            st.session_state.product_mapping_data = st.session_state.optimizer.run_product_mapping()
            st.success("产品映射完成！")

    if st.session_state.product_mapping_data is None:
        st.info("请点击上方按钮执行产品映射")
        return

    data = st.session_state.product_mapping_data
    if "error" in data:
        st.warning(data["error"])
        return

    stats = data["mapping_stats"]
    info = data["mapping_info"]

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("总记录数", stats["total_records"])
    with col2:
        st.metric("已映射", stats["mapped_count"])
    with col3:
        st.metric("未映射", stats["unmapped_count"])
    with col4:
        mapping_rate = (stats["mapped_count"] / stats["total_records"] * 100) if stats["total_records"] > 0 else 0
        st.metric("映射率", f"{mapping_rate:.1f}%")

    st.markdown("---")

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("📊 按云厂商统计")
        provider_stats = []
        for provider, p_stats in stats["by_provider"].items():
            provider_stats.append({
                "云厂商": provider,
                "总记录": p_stats["total"],
                "已映射": p_stats["mapped"],
                "未映射": p_stats["unmapped"],
                "映射率": f"{p_stats['mapped']/p_stats['total']*100:.1f}%" if p_stats["total"] > 0 else "0%",
            })
        provider_df = pd.DataFrame(provider_stats)
        st.dataframe(provider_df, use_container_width=True)

    with col2:
        st.subheader("📁 按分类统计")
        category_df = pd.DataFrame(
            list(stats["by_category"].items()),
            columns=["产品分类", "记录数"],
        ).sort_values("记录数", ascending=False)
        fig = px.bar(
            category_df,
            x="记录数",
            y="产品分类",
            orientation="h",
            title="产品分类分布",
        )
        fig.update_layout(height=400, yaxis=dict(autorange="reversed"))
        st.plotly_chart(fig, use_container_width=True)

    st.markdown("---")

    if stats["unmapped_services"]:
        st.subheader("⚠️ 未映射的服务")
        for provider, services in stats["unmapped_services"].items():
            if services:
                with st.expander(f"{provider} ({len(services)} 个未映射)"):
                    for service in services:
                        st.write(f"- {service}")
                    st.info("💡 您可以通过 `ProductMapper.add_custom_mapping()` 添加自定义映射规则")

    st.markdown("---")

    st.subheader("📋 映射结果预览")
    if "mapped_records" in data:
        mapped_df = pd.DataFrame(data["mapped_records"][:100])
        display_columns = [
            "provider", "service_name", "unified_product_name",
            "category", "pretax_amount", "mapping_found",
        ]
        available_columns = [c for c in display_columns if c in mapped_df.columns]
        st.dataframe(
            mapped_df[available_columns].style.format({"pretax_amount": "{:,.2f}"}),
            use_container_width=True,
        )
        st.caption(f"仅显示前 100 条记录，共 {len(data['mapped_records'])} 条")

    st.markdown("---")

    st.subheader("ℹ️ 映射库信息")
    info_df = pd.DataFrame(
        list(info["by_provider"].items()),
        columns=["云厂商", "已定义产品数"],
    )
    st.dataframe(info_df, use_container_width=True)
    st.write(f"**总产品分类数:** {info['total_categories']}")
    st.write(f"**总映射规则数:** {info['total_mappings']}")


def budget_management_page():
    st.header("💰 预算管理")

    if "budget_data" not in st.session_state:
        st.session_state.budget_data = None

    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        st.subheader("📊 预算执行情况")
    with col2:
        if st.button("刷新预算数据", type="primary"):
            with st.spinner("正在分析预算..."):
                st.session_state.budget_data = st.session_state.optimizer.run_budget_analysis()
                st.success("预算分析完成！")
    with col3:
        with st.expander("➕ 创建预算"):
            with st.form("create_budget_form"):
                budget_name = st.text_input("预算名称")
                budget_amount = st.number_input("预算金额", min_value=0.0, step=1000.0)
                budget_period = st.selectbox("预算周期", ["monthly", "quarterly", "yearly"])
                submitted = st.form_submit_button("创建预算")
                if submitted and budget_name and budget_amount > 0:
                    result = st.session_state.optimizer.create_budget(budget_name, budget_amount, budget_period)
                    st.success(f"预算创建成功: {result['name']}")

    if st.session_state.budget_data is None:
        st.info("请点击上方按钮刷新预算数据")
        return

    data = st.session_state.budget_data
    if "error" in data:
        st.warning(data["error"])
        return

    period = data.get("period", {})
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("本月总支出", format_currency(data.get("total_spend", 0)))
    with col2:
        st.metric("已过天数", f"{period.get('days_elapsed', 0)} 天")
    with col3:
        st.metric("剩余天数", f"{period.get('days_remaining', 0)} 天")
    with col4:
        alerts = data.get("alerts", {})
        st.metric("告警数量", alerts.get("total", 0))

    st.markdown("---")

    st.subheader("📋 预算列表")
    budgets = data.get("budgets", [])
    if budgets:
        for budget in budgets:
            with st.expander(
                f"{get_budget_status_icon(budget['percentage'])} "
                f"{budget['name']} - ¥{budget['current_spend']:,.2f} / ¥{budget['amount']:,.2f} "
                f"({budget['percentage']:.1f}%)"
            ):
                col1, col2 = st.columns(2)
                with col1:
                    st.write(f"**预算金额:** ¥{budget['amount']:,.2f}")
                    st.write(f"**已使用:** ¥{budget['current_spend']:,.2f} ({budget['percentage']:.1f}%)")
                    st.write(f"**日均消费:** ¥{budget['daily_avg']:,.2f}")
                with col2:
                    st.write(f"**预测支出:** ¥{budget['forecasted_spend']:,.2f}")
                    if budget['projected_overage'] > 0:
                        st.warning(f"⚠️ 预计超支: ¥{budget['projected_overage']:,.2f}")
                    st.write(f"**趋势:** {get_trend_text(budget['trend'])}")

                progress_col = st.columns(1)[0]
                with progress_col:
                    progress = min(budget['percentage'] / 100, 1.0)
                    st.progress(
                        progress,
                        text=f"预算使用进度: {budget['percentage']:.1f}%"
                    )

    st.markdown("---")

    if alerts.get("total", 0) > 0:
        st.subheader("⚠️ 告警信息")
        for alert in alerts.get("list", []):
            severity_color = get_severity_color(alert["severity"])
            st.markdown(
                f"<div style='background-color: {severity_color}20; padding: 10px; "
                f"border-radius: 5px; border-left: 4px solid {severity_color};'>"
                f"<strong>[{alert['severity'].upper()}]</strong> {alert['message']}"
                f"</div>",
                unsafe_allow_html=True,
            )
            st.markdown("")

    st.markdown("---")

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("🏢 按云厂商分布")
        provider_data = data.get("provider_breakdown", {})
        if provider_data:
            provider_df = pd.DataFrame(
                list(provider_data.items()),
                columns=["云厂商", "费用"],
            )
            fig = px.pie(provider_df, values="费用", names="云厂商")
            st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.subheader("📦 按服务分布 (Top 10)")
        service_data = data.get("service_breakdown", {})
        if service_data:
            service_df = pd.DataFrame(
                sorted(service_data.items(), key=lambda x: x[1], reverse=True)[:10],
                columns=["服务", "费用"],
            )
            fig = px.bar(service_df, x="费用", y="服务", orientation="h")
            fig.update_layout(yaxis=dict(autorange="reversed"))
            st.plotly_chart(fig, use_container_width=True)


def get_budget_status_icon(percentage):
    if percentage >= 120:
        return "🔴"
    elif percentage >= 100:
        return "🟠"
    elif percentage >= 90:
        return "🟡"
    elif percentage >= 70:
        return "🟢"
    else:
        return "✅"


def get_trend_text(trend):
    trend_map = {
        "normal": "✅ 正常",
        "approaching": "🟡 接近预算",
        "over_budget": "🟠 已超预算",
        "high_growth": "🔴 快速增长",
    }
    return trend_map.get(trend, "❓ 未知")


def ri_planning_page():
    st.header("📅 预留实例 (RI) 购买规划")

    if "ri_data" not in st.session_state:
        st.session_state.ri_data = None

    col1, col2 = st.columns([3, 1])
    with col1:
        st.subheader("💡 RI购买建议")
    with col2:
        if st.button("生成RI建议", type="primary"):
            with st.spinner("正在分析实例使用情况..."):
                st.session_state.ri_data = st.session_state.optimizer.run_ri_analysis()
                st.success("RI分析完成！")

    if st.session_state.ri_data is None:
        st.info("请点击上方按钮生成RI购买建议")
        return

    data = st.session_state.ri_data
    if "error" in data:
        st.warning(data["error"])
        return

    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        st.metric("建议数量", data.get("total_recommendations", 0))
    with col2:
        st.metric("当前按需成本", format_currency(data.get("total_current_cost", 0)))
    with col3:
        st.metric("预估RI成本", format_currency(data.get("total_ri_cost", 0)))
    with col4:
        st.metric("年节省金额", format_currency(data.get("total_savings", 0) * 12))
    with col5:
        st.metric("节省比例", f"{data.get('overall_savings_percentage', 0):.1f}%")

    risk_assessment = data.get("risk_assessment", {})
    risk_color = get_risk_color(risk_assessment.get("risk_level", "low"))
    st.info(
        f"**风险评估:** {risk_assessment.get('message', '')} | "
        f"高风险建议: {risk_assessment.get('high_risk_count', 0)} 个 | "
        f"总投资: ¥{risk_assessment.get('total_investment', 0):,.2f}"
    )

    st.markdown("---")

    recommendations = data.get("recommendations", [])
    if recommendations:
        st.subheader("📋 购买建议详情")

        for rec in recommendations:
            risk_icon = "🔴" if rec["risk_level"] == "high" else "🟡" if rec["risk_level"] == "medium" else "🟢"
            with st.expander(
                f"{risk_icon} [{rec['recommendation_type'].upper()}] "
                f"{rec['provider']} {rec['instance_type']} - "
                f"购买 {rec['quantity']} 个, 月节省 ¥{rec['estimated_savings']:,.2f}"
            ):
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.write(f"**云厂商:** {rec['provider']}")
                    st.write(f"**实例类型:** {rec['instance_type']}")
                    st.write(f"**操作系统:** {rec['operating_system']}")
                    st.write(f"**购买数量:** {rec['quantity']} 个")
                with col2:
                    st.write(f"**当前按需成本:** ¥{rec['current_on_demand_cost']:,.2f}/月")
                    st.write(f"**预估RI成本:** ¥{rec['estimated_ri_cost']:,.2f}/月")
                    st.write(f"**月节省金额:** ¥{rec['estimated_savings']:,.2f}")
                    st.write(f"**节省比例:** {rec['savings_percentage']:.1f}%")
                with col3:
                    st.write(f"**平均利用率:** {rec['utilization_threshold']*100:.1f}%")
                    st.write(f"**回本周期:** {rec['break_even_months']:.1f} 个月")
                    st.write(f"**风险等级:** {rec['risk_level'].upper()}")
                    st.write(f"**置信度:** {rec['confidence']:.0%}")

                instance_details = rec.get("instance_details", [])
                if instance_details:
                    st.markdown("**涉及实例:**")
                    details_df = pd.DataFrame(instance_details)
                    st.dataframe(
                        details_df.style.format({
                            "total_cost": "{:,.2f}",
                            "utilization_rate": "{:.1%}",
                            "average_hours_per_day": "{:.1f}",
                        }),
                        use_container_width=True,
                    )

    st.markdown("---")

    implementation_plan = data.get("implementation_plan", [])
    if implementation_plan:
        st.subheader("📋 实施计划")
        plan_df = pd.DataFrame(implementation_plan)
        st.dataframe(plan_df, use_container_width=True)


def get_risk_color(risk_level):
    colors = {
        "high": "#ff4b4b",
        "medium": "#ff9f43",
        "low": "#6bcb77",
    }
    return colors.get(risk_level, "#888888")


def cost_forecast_page():
    st.header("🔮 费用预测")

    if "forecast_data" not in st.session_state:
        st.session_state.forecast_data = None

    col1, col2 = st.columns([3, 1])
    with col1:
        st.subheader("📊 下月费用预测")
    with col2:
        if st.button("生成预测", type="primary"):
            with st.spinner("正在分析历史数据并生成预测..."):
                st.session_state.forecast_data = st.session_state.optimizer.run_cost_forecast()
                st.success("预测完成！")

    if st.session_state.forecast_data is None:
        st.info("请点击上方按钮生成费用预测")
        return

    data = st.session_state.forecast_data
    if "error" in data:
        st.warning(data["error"])
        return

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric(
            "下月预测支出",
            format_currency(data.get("total_forecast", 0)),
            delta=f"置信度 {data.get('confidence', 0):.0%}",
        )
    with col2:
        st.metric(
            "预测下限",
            format_currency(data.get("lower_bound", 0)),
        )
    with col3:
        st.metric(
            "预测上限",
            format_currency(data.get("upper_bound", 0)),
        )
    with col4:
        st.metric("预测方法", data.get("method", "ensemble"))

    trend_analysis = data.get("trend_analysis", {})
    trend = trend_analysis.get("trend", "unknown")
    trend_icon = "📈" if trend == "upward" else "📉" if trend == "downward" else "➡️"
    st.info(
        f"{trend_icon} **趋势分析:** {get_trend_description(trend)} | "
        f"变化率: {trend_analysis.get('change_percentage', 0):.1f}% | "
        f"波动性: {trend_analysis.get('volatility', 0):.1%}"
    )

    st.markdown("---")

    historical_data = data.get("historical_data", {})
    if historical_data:
        st.subheader("📈 历史数据统计")
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("分析天数", f"{historical_data.get('days', 0)} 天")
        with col2:
            st.metric("总历史支出", format_currency(historical_data.get("total_historical_cost", 0)))
        with col3:
            st.metric("日均消费", format_currency(historical_data.get("daily_avg", 0)))
        with col4:
            st.metric("日消费标准差", format_currency(historical_data.get("daily_std", 0)))

    st.markdown("---")

    daily_forecasts = data.get("daily_forecasts", [])
    if daily_forecasts:
        st.subheader("📅 未来30天预测")
        forecast_df = pd.DataFrame(daily_forecasts)
        forecast_df["date"] = pd.to_datetime(forecast_df["date"])

        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=forecast_df["date"],
            y=forecast_df["forecast"],
            mode="lines",
            name="预测值",
            line=dict(color="#4e79a7", width=2),
        ))
        fig.add_trace(go.Scatter(
            x=forecast_df["date"],
            y=forecast_df["upper"],
            mode="lines",
            name="上限",
            line=dict(color="#e15759", width=1, dash="dash"),
        ))
        fig.add_trace(go.Scatter(
            x=forecast_df["date"],
            y=forecast_df["lower"],
            mode="lines",
            name="下限",
            line=dict(color="#76b7b2", width=1, dash="dash"),
            fill="tonexty",
            fillcolor="rgba(78, 121, 167, 0.1)",
        ))
        fig.update_layout(
            height=400,
            hovermode="x unified",
            margin=dict(l=0, r=0, t=20, b=0),
        )
        st.plotly_chart(fig, use_container_width=True)

    st.markdown("---")

    recommendations = data.get("recommendations", [])
    if recommendations:
        st.subheader("💡 建议")
        for rec in recommendations:
            st.write(f"• {rec}")

    st.markdown("---")

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("🏢 按云厂商预测")
        provider_forecasts = data.get("provider_forecasts", {})
        if provider_forecasts:
            provider_data = []
            for provider, fc in provider_forecasts.items():
                provider_data.append({
                    "云厂商": provider,
                    "预测支出": fc.get("total_forecast", 0),
                    "置信度": fc.get("confidence", 0),
                })
            provider_df = pd.DataFrame(provider_data)
            fig = px.bar(
                provider_df,
                x="预测支出",
                y="云厂商",
                orientation="h",
                title="各云厂商下月预测支出",
            )
            fig.update_layout(yaxis=dict(autorange="reversed"))
            st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.subheader("📦 按服务预测 (Top 5)")
        service_forecasts = data.get("service_forecasts", {})
        if service_forecasts:
            service_data = []
            for service, fc in service_forecasts.items():
                service_data.append({
                    "服务": service,
                    "预测支出": fc.get("total_forecast", 0),
                    "置信度": fc.get("confidence", 0),
                })
            service_df = pd.DataFrame(service_data).sort_values("预测支出", ascending=False)
            st.dataframe(
                service_df.style.format({
                    "预测支出": "{:,.2f}",
                    "置信度": "{:.0%}",
                }),
                use_container_width=True,
            )


def get_trend_description(trend):
    descriptions = {
        "upward": "费用呈上升趋势",
        "downward": "费用呈下降趋势",
        "stable": "费用趋势稳定",
        "insufficient_data": "数据不足，无法判断趋势",
    }
    return descriptions.get(trend, "未知趋势")


def main():
    init_session_state()
    sidebar()

    st.title("💰 多云费用分析优化工具")
    st.markdown("---")

    page = st.tabs([
        "📈 总览",
        "📊 趋势分析",
        "⚠️ 异常检测",
        "💡 优化建议",
        "🏷️ 费用分摊",
        "🗂️ 产品映射",
        "💰 预算管理",
        "📅 RI购买规划",
        "🔮 费用预测",
    ])

    with page[0]:
        dashboard_page()
    with page[1]:
        trend_page()
    with page[2]:
        anomaly_page()
    with page[3]:
        optimization_page()
    with page[4]:
        allocation_page()
    with page[5]:
        product_mapping_page()
    with page[6]:
        budget_management_page()
    with page[7]:
        ri_planning_page()
    with page[8]:
        cost_forecast_page()


if __name__ == "__main__":
    main()
