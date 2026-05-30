import streamlit as st
import time
from src.utils import RestaurantConfig, SimulationResult, ReservationConfig, RetentionConfig
from src.simulation_engine import RestaurantSimulation, compare_strategies
from src.strategies import get_all_strategies
from src.queueing_model import QueueingModel
from src.visualization import (
    create_heatmap,
    create_hourly_comparison,
    create_queue_length_chart,
    create_table_utilization_chart,
    create_strategy_comparison_chart,
    create_wait_time_distribution,
    create_radar_comparison,
    create_turnover_forecast,
    create_satisfaction_comparison,
    create_satisfaction_wait_scatter,
    create_hourly_satisfaction_chart,
    create_dining_time_distribution,
    create_reservation_gap_chart,
    create_retention_analysis_chart,
    create_dish_impact_chart,
    create_no_show_turnover_impact,
)

st.set_page_config(
    page_title="餐厅翻台率优化系统",
    page_icon="🍽️",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    .main {
        background-color: #f8f9fa;
    }
    .stMetric {
        background-color: white;
        padding: 15px;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    h1, h2, h3 {
        color: #1e3a5f;
    }
    .stButton>button {
        background-color: #ff6b35;
        color: white;
        border-radius: 8px;
        padding: 10px 24px;
        border: none;
        font-weight: 600;
    }
    .stButton>button:hover {
        background-color: #e55a25;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("🍽️ 餐厅翻台率优化系统")
st.markdown("---")

with st.sidebar:
    st.header("⚙️ 餐厅配置")

    st.subheader("桌位设置")
    tables_2_seat = st.slider("2人桌数量", 2, 20, 10)
    tables_4_seat = st.slider("4人桌数量", 2, 15, 8)
    tables_6_seat = st.slider("6人桌数量", 1, 10, 4)

    st.subheader("客流参数")
    arrival_rate = st.slider("平均到店率 (组/小时)", 1.0, 10.0, 3.0, 0.5)
    peak_multiplier = st.slider("高峰时段客流倍数", 1.0, 4.0, 2.0, 0.5)

    st.subheader("用餐时长分布")
    avg_dining_time = st.slider("平均用餐时间 (分钟)", 30, 120, 60, 5)
    std_dining_time = st.slider("用餐时间标准差 (分钟)", 5, 45, 15, 5)
    lognormal_weight = st.slider("对数正态分布权重", 0.1, 0.95, 0.7, 0.05)
    lognormal_mu = st.slider("对数正态 μ", 3.0, 5.0, 4.0, 0.1)
    lognormal_sigma = st.slider("对数正态 σ", 0.1, 0.8, 0.35, 0.05)
    exponential_scale = st.slider("指数分布尺度 (分钟)", 10, 60, 30, 5)

    st.subheader("满意度模型")
    satisfaction_threshold = st.slider("满意等位阈值 (分钟)", 5, 30, 15, 1)
    satisfaction_decay_rate = st.slider("满意度衰减率", 0.01, 0.15, 0.05, 0.01)

    st.subheader("预约配置")
    reservation_rate = st.slider("预约比例", 0.0, 0.6, 0.25, 0.05)
    no_show_rate = st.slider("未到店率", 0.0, 0.4, 0.15, 0.05)
    late_arrival_rate = st.slider("迟到率", 0.0, 0.4, 0.20, 0.05)

    st.subheader("挽留策略")
    retention_wait_threshold = st.slider("挽留触发等位时间 (分钟)", 10, 40, 20, 5)
    retention_discount = st.slider("优惠折扣率", 0.05, 0.25, 0.10, 0.05)
    retention_success_rate = st.slider("挽留成功率", 0.3, 0.9, 0.65, 0.05)

    st.subheader("营业时间")
    open_hour = st.slider("开始营业时间", 6, 12, 10)
    close_hour = st.slider("结束营业时间", 18, 24, 22)

    st.subheader("经济参数")
    avg_spend = st.slider("人均消费 (元)", 30, 300, 80, 10)

    st.subheader("仿真设置")
    num_runs = st.slider("仿真次数", 1, 10, 3)

    run_simulation = st.button("🚀 运行仿真", use_container_width=True)

config = RestaurantConfig(
    tables_2_seat=tables_2_seat,
    tables_4_seat=tables_4_seat,
    tables_6_seat=tables_6_seat,
    arrival_rate=arrival_rate,
    avg_dining_time=avg_dining_time,
    std_dining_time=std_dining_time,
    lognormal_weight=lognormal_weight,
    lognormal_mu=lognormal_mu,
    lognormal_sigma=lognormal_sigma,
    exponential_scale=exponential_scale,
    satisfaction_threshold=satisfaction_threshold,
    satisfaction_decay_rate=satisfaction_decay_rate,
    peak_multiplier=peak_multiplier,
    open_hour=open_hour,
    close_hour=close_hour,
    avg_spend_per_person=avg_spend,
    reservation_config=ReservationConfig(
        reservation_rate=reservation_rate,
        no_show_rate=no_show_rate,
        late_arrival_rate=late_arrival_rate,
    ),
    retention_config=RetentionConfig(
        wait_threshold=retention_wait_threshold,
        discount_rate=retention_discount,
        retention_success_rate=retention_success_rate,
    ),
)

tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(
    ["📊 运营仪表盘", "📈 策略对比", "📞 预约分析", "🍲 菜品分析", "🔮 预测分析", "💡 优化建议"]
)

if "baseline_result" not in st.session_state:
    st.session_state.baseline_result = None
if "comparison_results" not in st.session_state:
    st.session_state.comparison_results = None

if run_simulation:
    with st.spinner("正在运行仿真..."):
        strategies = get_all_strategies()
        results = compare_strategies(config, strategies, num_runs=num_runs)

        st.session_state.baseline_result = results.get("fifo")
        st.session_state.comparison_results = results

    st.success("✅ 仿真完成！")

with tab1:
    st.subheader("📊 运营数据分析")

    if st.session_state.baseline_result:
        result = st.session_state.baseline_result

        col1, col2, col3, col4, col5, col6 = st.columns(6)
        with col1:
            st.metric(
                "翻台率",
                f"{result.table_turnover_rate:.2f} 次/桌/天",
                delta=f"+{result.table_turnover_rate * 0.15:.2f} (预计提升)",
            )
        with col2:
            st.metric(
                "平均等待时间",
                f"{result.average_wait_time:.1f} 分钟",
                delta=f"-{result.average_wait_time * 0.2:.1f} 分钟 (优化后)",
                delta_color="inverse",
            )
        with col3:
            st.metric("总接待组数", f"{result.total_served} 组")
        with col4:
            st.metric(
                "顾客满意度",
                f"{result.satisfaction_score:.2f}",
                delta=f"惩罚: {result.wait_time_penalty:.1f}",
                delta_color="inverse",
            )
        with col5:
            st.metric(
                "预约到店率",
                f"{result.reservation_show_rate:.0%}",
                delta=f"未到店: {result.reservation_no_shows}组",
                delta_color="inverse",
            )
        with col6:
            st.metric("净收益", f"¥{result.net_benefit:,.0f}")

        st.markdown("---")

        col1, col2 = st.columns(2)
        with col1:
            fig_heatmap = create_heatmap(result, config)
            st.plotly_chart(fig_heatmap, use_container_width=True)

        with col2:
            fig_hourly = create_hourly_comparison(result, config)
            st.plotly_chart(fig_hourly, use_container_width=True)

        col1, col2 = st.columns(2)
        with col1:
            fig_sat_hourly = create_hourly_satisfaction_chart(result, config)
            st.plotly_chart(fig_sat_hourly, use_container_width=True)

        with col2:
            fig_dist = create_dining_time_distribution(result)
            st.plotly_chart(fig_dist, use_container_width=True)

        col1, col2 = st.columns(2)
        with col1:
            fig_queue = create_queue_length_chart(result, config)
            st.plotly_chart(fig_queue, use_container_width=True)

        with col2:
            fig_wait = create_wait_time_distribution(result)
            st.plotly_chart(fig_wait, use_container_width=True)

        fig_util = create_table_utilization_chart(result)
        st.plotly_chart(fig_util, use_container_width=True)

    else:
        st.info("👈 请在左侧配置参数后点击'运行仿真'按钮")

with tab2:
    st.subheader("📈 策略模拟对比")

    if st.session_state.comparison_results:
        results = st.session_state.comparison_results

        metric_options = [
            ("翻台率", "table_turnover_rate"),
            ("平均等待时间", "average_wait_time"),
            ("总接待组数", "total_served"),
            ("预估营收", "revenue"),
            ("整体利用率", "overall_utilization"),
            ("顾客满意度", "satisfaction_score"),
            ("净收益", "net_benefit"),
        ]

        selected_metric = st.selectbox(
            "选择对比指标",
            options=[m[0] for m in metric_options],
            index=0,
        )

        metric_key = [m[1] for m in metric_options if m[0] == selected_metric][0]

        fig_compare = create_strategy_comparison_chart(results, metric_key)
        st.plotly_chart(fig_compare, use_container_width=True)

        st.markdown("---")
        st.subheader("😊 满意度与惩罚项对比")
        fig_sat_compare = create_satisfaction_comparison(results)
        st.plotly_chart(fig_sat_compare, use_container_width=True)

        col1, col2 = st.columns(2)
        with col1:
            fig_sat_scatter = create_satisfaction_wait_scatter(results)
            st.plotly_chart(fig_sat_scatter, use_container_width=True)

        with col2:
            fig_radar = create_radar_comparison(results)
            st.plotly_chart(fig_radar, use_container_width=True)

        st.subheader("📋 详细对比表")

        comparison_data = []
        for name, res in results.items():
            comparison_data.append(
                {
                    "策略": res.strategy_name,
                    "翻台率": f"{res.table_turnover_rate:.2f}",
                    "平均等待(分钟)": f"{res.average_wait_time:.1f}",
                    "接待组数": res.total_served,
                    "流失组数": res.total_lost,
                    "利用率(%)": f"{res.overall_utilization:.1f}",
                    "满意度": f"{res.satisfaction_score:.2f}",
                    "等位惩罚": f"{res.wait_time_penalty:.1f}",
                    "净收益(元)": f"{res.net_benefit:,.0f}",
                    "预估营收(元)": f"{res.revenue:,.0f}",
                }
            )

        import pandas as pd

        df = pd.DataFrame(comparison_data)
        st.dataframe(
            df.style.highlight_max(
                subset=["翻台率", "接待组数", "利用率(%)", "满意度", "净收益(元)", "预估营收(元)"],
                color="#90EE90",
            ).highlight_min(
                subset=["平均等待(分钟)", "流失组数", "等位惩罚"],
                color="#90EE90",
            ),
            use_container_width=True,
        )

    else:
        st.info("👈 请先运行仿真以查看策略对比")

with tab3:
    st.subheader("� 预约-到店缺口分析")

    if st.session_state.baseline_result:
        result = st.session_state.baseline_result

        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("总预约数", f"{result.total_reservations} 组")
        with col2:
            st.metric("未到店", f"{result.reservation_no_shows} 组")
        with col3:
            st.metric("到店率", f"{result.reservation_show_rate:.0%}")
        with col4:
            st.metric(
                "翻台率损失",
                f"-{result.no_show_impact_on_turnover:.3f}",
                delta=f"浪费{result.no_show_wasted_minutes:.0f}分钟",
                delta_color="inverse",
            )

        st.markdown("---")

        fig_res_gap = create_reservation_gap_chart(result, config)
        st.plotly_chart(fig_res_gap, use_container_width=True)

        col1, col2 = st.columns(2)
        with col1:
            fig_ns_impact = create_no_show_turnover_impact(result, config)
            st.plotly_chart(fig_ns_impact, use_container_width=True)

        with col2:
            st.subheader("🤝 智能挽留效果")
            if result.retention_offers_sent > 0:
                fig_retention = create_retention_analysis_chart(result, config)
                st.plotly_chart(fig_retention, use_container_width=True)
            else:
                st.info("当前基线策略无挽留机制，请在策略对比中查看「智能挽留策略」效果")

        st.markdown("---")
        st.subheader("📋 预约缺口影响总结")
        if result.total_reservations > 0:
            st.markdown(
                f"""
                - **预约未到店率**: {result.reservation_show_rate:.0%} 到店率 → {result.reservation_no_shows}组浪费
                - **桌位空闲浪费**: 约{result.no_show_wasted_minutes:.0f}分钟的桌位空等
                - **翻台率影响**: 未到店导致翻台率降低 {result.no_show_impact_on_turnover:.3f} 次/桌/天
                - **建议**: 收取预约押金、提前15分钟确认、超时释放桌位给等位顾客
                """
            )
    else:
        st.info("👈 请先运行仿真以查看预约分析")

with tab4:
    st.subheader("🍲 菜品组合分析")

    if st.session_state.baseline_result:
        result = st.session_state.baseline_result

        fig_dish = create_dish_impact_chart(result, config)
        st.plotly_chart(fig_dish, use_container_width=True)

        if result.dish_combination_impact:
            st.markdown("---")
            st.subheader("📋 菜品用餐时长详情")

            import pandas as pd

            dish_data = []
            for name, info in result.dish_combination_impact.items():
                dish_data.append({
                    "菜品类型": name,
                    "平均用餐时长(分钟)": info["avg_dining_time"],
                    "标准差(分钟)": info["std_dining_time"],
                    "点单数": info["count"],
                    "翻台贡献度": info["turnover_impact"],
                })

            df_dish = pd.DataFrame(dish_data)
            st.dataframe(
                df_dish.style.highlight_max(
                    subset=["翻台贡献度"], color="#90EE90"
                ).highlight_min(
                    subset=["平均用餐时长(分钟)"], color="#90EE90"
                ),
                use_container_width=True,
            )

            st.markdown("---")
            st.subheader("💡 菜品优化建议")

            if result.dish_combination_impact:
                fastest = min(
                    result.dish_combination_impact.items(),
                    key=lambda x: x[1]["avg_dining_time"],
                )
                slowest = max(
                    result.dish_combination_impact.items(),
                    key=lambda x: x[1]["avg_dining_time"],
                )
                st.markdown(
                    f"""
                    - **最快翻台**: {fastest[0]}（平均{fastest[1]['avg_dining_time']:.1f}分钟，贡献度{fastest[1]['turnover_impact']:.2f}）
                    - **最慢翻台**: {slowest[0]}（平均{slowest[1]['avg_dining_time']:.1f}分钟，贡献度{slowest[1]['turnover_impact']:.2f}）
                    - 高峰时段推荐主推**{fastest[0]}**类菜品，提升翻台效率
                    - 平峰时段可推广**{slowest[0]}**类菜品，提升客单价
                    - 考虑设置**限时套餐**，对用餐时长超{result.average_dining_time:.0f}分钟的菜品组合提供优惠引导提前结账
                    """
                )
    else:
        st.info("👈 请先运行仿真以查看菜品分析")

with tab5:
    st.subheader("� 翻台率提升预测")

    if st.session_state.comparison_results:
        results = st.session_state.comparison_results

        baseline = results.get("fifo")
        optimized = results.get("size_match", baseline)

        col1, col2, col3 = st.columns(3)

        improvement = (
            (optimized.table_turnover_rate - baseline.table_turnover_rate)
            / baseline.table_turnover_rate
            * 100
        )
        revenue_diff = optimized.revenue - baseline.revenue

        with col1:
            st.metric(
                "翻台率提升",
                f"{improvement:.1f}%",
                delta=f"+{improvement:.1f}%",
            )
        with col2:
            st.metric(
                "日营收增加",
                f"¥{revenue_diff:,.0f}",
                delta=f"+¥{revenue_diff:,.0f}",
            )
        with col3:
            st.metric(
                "月营收增加",
                f"¥{revenue_diff * 30:,.0f}",
                delta=f"+¥{revenue_diff * 30:,.0f}",
            )

        st.markdown("---")

        fig_forecast = create_turnover_forecast(baseline, optimized)
        st.plotly_chart(fig_forecast, use_container_width=True)

        st.markdown("---")
        st.subheader("📊 排队论模型预测")

        qm = QueueingModel(config)
        baseline_metrics = qm.get_baseline_metrics()

        hours = list(baseline_metrics.keys())
        utilizations = [m["utilization"] * 100 for m in baseline_metrics.values()]
        wait_times = [m["avg_wait_time"] for m in baseline_metrics.values()]

        col1, col2 = st.columns(2)
        with col1:
            import plotly.graph_objects as go

            fig_util = go.Figure()
            fig_util.add_trace(
                go.Scatter(
                    x=hours,
                    y=utilizations,
                    mode="lines+markers",
                    line=dict(color="#1e3a5f", width=2),
                    fill="tozeroy",
                    fillcolor="rgba(30, 58, 95, 0.2)",
                )
            )
            fig_util.update_layout(
                title="M/M/c排队论 - 桌位利用率预测",
                xaxis_title="时间",
                yaxis_title="利用率 (%)",
                height=350,
            )
            st.plotly_chart(fig_util, use_container_width=True)

        with col2:
            fig_wait = go.Figure()
            fig_wait.add_trace(
                go.Scatter(
                    x=hours,
                    y=wait_times,
                    mode="lines+markers",
                    line=dict(color="#ff6b35", width=2),
                    fill="tozeroy",
                    fillcolor="rgba(255, 107, 53, 0.2)",
                )
            )
            fig_wait.update_layout(
                title="M/M/c排队论 - 平均等待时间预测",
                xaxis_title="时间",
                yaxis_title="等待时间 (分钟)",
                height=350,
            )
            st.plotly_chart(fig_wait, use_container_width=True)

    else:
        st.info("👈 请先运行仿真以查看预测分析")

with tab6:
    st.subheader("💡 优化建议")

    if st.session_state.comparison_results:
        results = st.session_state.comparison_results

        best_strategy = max(
            results.items(), key=lambda x: x[1].satisfaction_score * x[1].table_turnover_rate
        )

        st.success(
            f"🏆 推荐使用 **{best_strategy[1].strategy_name}** 策略，满意度×翻台率综合最优！"
        )

        st.markdown("---")

        col1, col2 = st.columns(2)

        with col1:
            st.markdown("### 🎯 排号策略建议")
            st.markdown(
                """
            - **高峰时段**：使用「大小匹配优先」策略，最大化桌位利用率
            - **平峰时段**：使用「先来先服务」策略，保证公平性
            - **超长队列**：考虑「短用餐时间优先」，快速减少排队长度
            """
            )

            st.markdown("### ⏰ 时段管理建议")
            peak_hours_str = ", ".join([f"{h}:00" for h in config.peak_hours])
            st.markdown(
                f"""
            - **高峰时段**：{peak_hours_str}
            - 建议提前15分钟做好准备工作
            - 高峰时段增加临时服务人员
            - 可考虑推出限时优惠引导错峰就餐
            """
            )

        with col2:
            st.markdown("### 🪑 桌位优化建议")
            total_tables = tables_2_seat + tables_4_seat + tables_6_seat
            avg_party_size = 2.5
            optimal_2_seat = int(total_tables * 0.4)
            optimal_4_seat = int(total_tables * 0.4)
            optimal_6_seat = total_tables - optimal_2_seat - optimal_4_seat

            st.markdown(
                f"""
            - **当前配置**：{tables_2_seat}张2人桌 / {tables_4_seat}张4人桌 / {tables_6_seat}张6人桌
            - **推荐配置**：{optimal_2_seat}张2人桌 / {optimal_4_seat}张4人桌 / {optimal_6_seat}张6人桌
            - 建议增加2人桌比例以适应小桌客流
            - 考虑设置可拼接桌位提高灵活性
            """
            )

            st.markdown("### 💰 收益提升估算")
            baseline = results.get("fifo")
            best = best_strategy[1]
            daily_gain = best.revenue - baseline.revenue
            sat_improvement = best.satisfaction_score - baseline.satisfaction_score

            smart_ret = results.get("smart_retention")
            retention_note = ""
            if smart_ret and smart_ret.retention_offers_sent > 0:
                retention_note = f"""
            - **挽留挽回营收**: ¥{smart_ret.retention_revenue_saved:,.0f}
            - **挽留优惠成本**: ¥{smart_ret.retention_discount_cost:,.0f}
            - **挽留净收益**: ¥{smart_ret.retention_revenue_saved - smart_ret.retention_discount_cost:,.0f}
            """

            st.markdown(
                f"""
            - **日收益提升**：¥{daily_gain:,.0f}
            - **月收益提升**：¥{daily_gain * 30:,.0f}
            - **年收益提升**：¥{daily_gain * 365:,.0f}
            - **满意度提升**：{sat_improvement:+.2f}
            - **等位惩罚降低**：{baseline.wait_time_penalty - best.wait_time_penalty:.1f}
            - **净收益提升**：¥{best.net_benefit - baseline.net_benefit:,.0f}
            - **预约未到店浪费**：{baseline.no_show_wasted_minutes:.0f}分钟
            {retention_note}
            """
            )

        st.markdown("---")
        st.subheader("📋 行动计划")

        actions = [
            ("立即执行", "培训员工掌握新的排号策略", 1),
            ("1周内", "调整部分桌位布局，增加灵活性", 2),
            ("2周内", "收集真实数据，验证仿真效果", 3),
            ("1个月内", "建立持续优化机制，定期复盘", 4),
        ]

        for phase, action, priority in actions:
            with st.expander(f"📌 {phase} - {action}"):
                st.markdown(
                    f"""
                **优先级**：{'⭐' * priority}

                **具体措施**：
                - 制定详细的执行计划
                - 明确责任人
                - 设置检查节点
                - 评估执行效果
                """
                )

    else:
        st.info("👈 请先运行仿真以获取优化建议")

st.markdown("---")
st.caption("🍽️ 餐厅翻台率优化系统 | 基于排队论与离散事件仿真")
