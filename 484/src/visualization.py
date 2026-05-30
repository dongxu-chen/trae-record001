import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import numpy as np
from typing import Dict, List, Tuple
from .utils import RestaurantConfig, SimulationResult, format_time


def create_kpi_card(title: str, value: str, subtitle: str = "", color: str = "#1e3a5f"):
    fig = go.Figure()
    fig.add_annotation(
        text=title,
        x=0.5,
        y=0.85,
        showarrow=False,
        font=dict(size=14, color="gray"),
        xanchor="center",
    )
    fig.add_annotation(
        text=value,
        x=0.5,
        y=0.5,
        showarrow=False,
        font=dict(size=28, color=color, weight="bold"),
        xanchor="center",
    )
    if subtitle:
        fig.add_annotation(
            text=subtitle,
            x=0.5,
            y=0.2,
            showarrow=False,
            font=dict(size=12, color="lightgray"),
            xanchor="center",
        )
    fig.update_layout(
        height=120,
        margin=dict(l=10, r=10, t=10, b=10),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(showticklabels=False, showgrid=False, zeroline=False),
        yaxis=dict(showticklabels=False, showgrid=False, zeroline=False),
    )
    return fig


def create_heatmap(
    result: SimulationResult, config: RestaurantConfig
) -> go.Figure:
    table_ids = sorted(result.table_utilization.keys())
    table_labels = [
        f"桌{tid}({result.table_utilization[tid][0]}人)" for tid in table_ids
    ]

    open_min = config.open_hour * 60
    close_min = config.close_hour * 60
    slot_size = 15
    time_slots = list(range(open_min, close_min, slot_size))
    slot_labels = [format_time(t) for t in time_slots]

    heatmap_data = np.zeros((len(table_ids), len(time_slots)))
    event_markers = []

    for tid_idx, table_id in enumerate(table_ids):
        occupancy = result.table_occupancy_timeline.get(table_id, [])
        for slot_idx, slot_start in enumerate(time_slots):
            slot_end = slot_start + slot_size
            for start, end, group_size in occupancy:
                overlap = min(end, slot_end) - max(start, slot_start)
                if overlap > 0:
                    ratio = min(1.0, overlap / slot_size)
                    heatmap_data[tid_idx, slot_idx] = max(
                        heatmap_data[tid_idx, slot_idx], ratio
                    )

    for evt in result.state_change_events:
        if evt["type"] == "seat":
            evt_time = evt["time"]
            if open_min <= evt_time < close_min:
                slot_idx = min(int((evt_time - open_min) / slot_size), len(time_slots) - 1)
                tid = evt.get("table_id")
                if tid is not None:
                    tid_idx = table_ids.index(tid) if tid in table_ids else None
                    if tid_idx is not None:
                        event_markers.append({
                            "x": slot_labels[slot_idx],
                            "y": table_labels[tid_idx],
                            "wait": evt.get("wait_time", 0),
                            "sat": evt.get("satisfaction", 1.0),
                            "group_size": evt.get("group_size", 0),
                        })

    fig = go.Figure(
        data=go.Heatmap(
            z=heatmap_data,
            x=slot_labels,
            y=table_labels,
            colorscale=[
                [0.0, "#f0f2f6"],
                [0.3, "#ffe0cc"],
                [0.7, "#ff9955"],
                [1.0, "#ff6b35"],
            ],
            showscale=True,
            colorbar=dict(
                title="占用强度",
                tickvals=[0, 0.5, 1],
                ticktext=["空闲", "部分", "满占"],
            ),
        )
    )

    seat_events = [e for e in event_markers if e["wait"] > 0]
    if seat_events:
        low_sat = [e for e in seat_events if e["sat"] < 0.5]
        mid_sat = [e for e in seat_events if 0.5 <= e["sat"] < 0.8]
        high_sat = [e for e in seat_events if e["sat"] >= 0.8]

        if low_sat:
            fig.add_trace(go.Scatter(
                x=[e["x"] for e in low_sat],
                y=[e["y"] for e in low_sat],
                mode="markers",
                marker=dict(symbol="x", size=10, color="#ef4444", line=dict(width=2)),
                name="低满意度 (<0.5)",
                hovertemplate="等位: %{customdata[0]:.0f}分<br>满意度: %{customdata[1]:.2f}<extra></extra>",
                customdata=[[e["wait"], e["sat"]] for e in low_sat],
            ))
        if mid_sat:
            fig.add_trace(go.Scatter(
                x=[e["x"] for e in mid_sat],
                y=[e["y"] for e in mid_sat],
                mode="markers",
                marker=dict(symbol="triangle-up", size=8, color="#eab308"),
                name="中满意度 (0.5-0.8)",
                hovertemplate="等位: %{customdata[0]:.0f}分<br>满意度: %{customdata[1]:.2f}<extra></extra>",
                customdata=[[e["wait"], e["sat"]] for e in mid_sat],
            ))
        if high_sat:
            fig.add_trace(go.Scatter(
                x=[e["x"] for e in high_sat],
                y=[e["y"] for e in high_sat],
                mode="markers",
                marker=dict(symbol="circle", size=7, color="#22c55e", opacity=0.7),
                name="高满意度 (≥0.8)",
                hovertemplate="等位: %{customdata[0]:.0f}分<br>满意度: %{customdata[1]:.2f}<extra></extra>",
                customdata=[[e["wait"], e["sat"]] for e in high_sat],
            ))

    fig.update_layout(
        title="桌位占用热力图（事件驱动 · 状态变化标注）",
        xaxis_title="时间（15分钟粒度）",
        yaxis_title="桌位",
        height=500,
        xaxis=dict(tickangle=45),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )

    return fig


def create_hourly_comparison(
    result: SimulationResult, config: RestaurantConfig
) -> go.Figure:
    hours = list(range(config.open_hour, config.close_hour))
    hour_labels = [f"{h}:00" for h in hours]

    fig = go.Figure()

    fig.add_trace(
        go.Bar(
            x=hour_labels,
            y=result.hourly_arrivals,
            name="到店客流",
            marker_color="#1e3a5f",
        )
    )

    fig.add_trace(
        go.Bar(
            x=hour_labels,
            y=result.hourly_served,
            name="已接待",
            marker_color="#ff6b35",
        )
    )

    fig.update_layout(
        title="每小时客流对比",
        barmode="group",
        xaxis_title="时间",
        yaxis_title="顾客组数",
        height=400,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )

    return fig


def create_queue_length_chart(
    result: SimulationResult, config: RestaurantConfig
) -> go.Figure:
    times = [format_time(t) for t, _ in result.queue_length_history]
    lengths = [l for _, l in result.queue_length_history]

    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=times,
            y=lengths,
            mode="lines",
            fill="tozeroy",
            line=dict(color="#ff6b35", width=2),
            fillcolor="rgba(255, 107, 53, 0.3)",
        )
    )

    fig.update_layout(
        title="排队长度变化",
        xaxis_title="时间",
        yaxis_title="排队组数",
        height=350,
    )

    return fig


def create_table_utilization_chart(
    result: SimulationResult,
) -> go.Figure:
    table_ids = sorted(result.table_utilization.keys())
    utilizations = [result.table_utilization[tid][1] for tid in table_ids]
    capacities = [result.table_utilization[tid][0] for tid in table_ids]

    colors = []
    for u in utilizations:
        if u >= 80:
            colors.append("#22c55e")
        elif u >= 60:
            colors.append("#eab308")
        else:
            colors.append("#ef4444")

    fig = go.Figure()

    fig.add_trace(
        go.Bar(
            x=[f"桌{tid}({c}人)" for tid, c in zip(table_ids, capacities)],
            y=utilizations,
            marker_color=colors,
            text=[f"{u:.1f}%" for u in utilizations],
            textposition="auto",
        )
    )

    fig.update_layout(
        title="各桌位利用率",
        xaxis_title="桌位",
        yaxis_title="利用率 (%)",
        height=400,
        yaxis=dict(range=[0, 100]),
    )

    return fig


def create_strategy_comparison_chart(
    results: Dict[str, SimulationResult], metric: str = "table_turnover_rate"
) -> go.Figure:
    strategy_names = []
    metric_values = []

    metric_labels = {
        "table_turnover_rate": "翻台率 (次/桌/天)",
        "average_wait_time": "平均等待时间 (分钟)",
        "total_served": "总接待组数",
        "revenue": "预估营收 (元)",
        "overall_utilization": "整体利用率 (%)",
        "satisfaction_score": "顾客满意度",
        "net_benefit": "净收益 (元)",
    }

    for name, result in results.items():
        strategy_names.append(result.strategy_name)
        metric_values.append(getattr(result, metric))

    colors = ["#1e3a5f", "#ff6b35", "#22c55e", "#8b5cf6", "#f59e0b"]

    fig = go.Figure()

    fig.add_trace(
        go.Bar(
            x=strategy_names,
            y=metric_values,
            marker_color=colors[: len(strategy_names)],
            text=[f"{v:.2f}" for v in metric_values],
            textposition="auto",
        )
    )

    fig.update_layout(
        title=f"策略对比 - {metric_labels.get(metric, metric)}",
        xaxis_title="排号策略",
        yaxis_title=metric_labels.get(metric, metric),
        height=400,
    )

    return fig


def create_wait_time_distribution(result: SimulationResult) -> go.Figure:
    if not result.wait_times:
        return go.Figure()

    fig = go.Figure()

    fig.add_trace(
        go.Histogram(
            x=result.wait_times,
            nbinsx=20,
            marker_color="#ff6b35",
            opacity=0.7,
        )
    )

    fig.add_vline(
        x=result.average_wait_time,
        line_dash="dash",
        line_color="red",
        annotation_text=f"平均: {result.average_wait_time:.1f}分钟",
        annotation_position="top right",
    )

    fig.update_layout(
        title="等待时间分布",
        xaxis_title="等待时间 (分钟)",
        yaxis_title="顾客组数",
        height=350,
    )

    return fig


def create_radar_comparison(results: Dict[str, SimulationResult]) -> go.Figure:
    categories = ["翻台率", "接待量", "利用率", "满意度", "净收益", "等待体验"]

    fig = go.Figure()

    colors = ["#1e3a5f", "#ff6b35", "#22c55e", "#8b5cf6"]

    all_values = []
    for result in results.values():
        values = [
            result.table_turnover_rate,
            result.total_served,
            result.overall_utilization / 10,
            result.satisfaction_score,
            result.net_benefit / 1000,
            max(0, 10 - result.average_wait_time / 5),
        ]
        all_values.append(values)

    max_values = [max(v[i] for v in all_values) if max(v[i] for v in all_values) > 0 else 1 for i in range(len(categories))]

    for idx, (name, result) in enumerate(results.items()):
        values = [
            result.table_turnover_rate / max_values[0],
            result.total_served / max_values[1],
            result.overall_utilization / 100,
            result.satisfaction_score / max_values[3] if max_values[3] > 0 else 0,
            (result.net_benefit / 1000) / max_values[4] if max_values[4] > 0 else 0,
            max(0, 10 - result.average_wait_time / 5) / max_values[5] if max_values[5] > 0 else 0,
        ]

        fig.add_trace(
            go.Scatterpolar(
                r=values,
                theta=categories,
                fill="toself",
                name=result.strategy_name,
                line=dict(color=colors[idx % len(colors)]),
                fillcolor=f"rgba{tuple(int(colors[idx % len(colors)].lstrip('#')[i:i+2], 16) for i in (0, 2, 4)) + (0.3,)}",
            )
        )

    fig.update_layout(
        polar=dict(radialaxis=dict(visible=True, range=[0, 1])),
        title="策略综合对比（含满意度）",
        height=450,
    )

    return fig


def create_turnover_forecast(
    baseline_result: SimulationResult, optimized_result: SimulationResult
) -> go.Figure:
    days = list(range(1, 31))
    baseline_daily = baseline_result.table_turnover_rate
    optimized_daily = optimized_result.table_turnover_rate
    improvement = (optimized_daily - baseline_daily) / baseline_daily * 100

    baseline_cumulative = [baseline_daily * d for d in days]
    optimized_cumulative = [optimized_daily * d for d in days]

    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=days,
            y=baseline_cumulative,
            mode="lines",
            name="基线策略",
            line=dict(color="#1e3a5f", width=2),
        )
    )

    fig.add_trace(
        go.Scatter(
            x=days,
            y=optimized_cumulative,
            mode="lines",
            name="优化策略",
            line=dict(color="#ff6b35", width=2),
            fill="tonexty",
            fillcolor="rgba(255, 107, 53, 0.2)",
        )
    )

    fig.update_layout(
        title=f"翻台率提升预测 (预计提升: {improvement:.1f}%)",
        xaxis_title="天数",
        yaxis_title="累计翻台次数",
        height=400,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )

    return fig


def create_satisfaction_comparison(
    results: Dict[str, SimulationResult],
) -> go.Figure:
    strategy_names = []
    satisfaction_vals = []
    penalty_vals = []
    net_benefit_vals = []

    for name, result in results.items():
        strategy_names.append(result.strategy_name)
        satisfaction_vals.append(result.satisfaction_score)
        penalty_vals.append(result.wait_time_penalty)
        net_benefit_vals.append(result.net_benefit)

    fig = make_subplots(
        rows=1, cols=3,
        subplot_titles=("顾客满意度", "等位时间惩罚", "净收益"),
    )

    colors = ["#1e3a5f", "#ff6b35", "#22c55e", "#8b5cf6"]

    fig.add_trace(
        go.Bar(
            x=strategy_names,
            y=satisfaction_vals,
            marker_color=colors[: len(strategy_names)],
            text=[f"{v:.2f}" for v in satisfaction_vals],
            textposition="auto",
            showlegend=False,
        ),
        row=1, col=1,
    )

    fig.add_trace(
        go.Bar(
            x=strategy_names,
            y=penalty_vals,
            marker_color=["#ef4444"] * len(strategy_names),
            text=[f"{v:.1f}" for v in penalty_vals],
            textposition="auto",
            showlegend=False,
        ),
        row=1, col=2,
    )

    fig.add_trace(
        go.Bar(
            x=strategy_names,
            y=net_benefit_vals,
            marker_color=colors[: len(strategy_names)],
            text=[f"¥{v:,.0f}" for v in net_benefit_vals],
            textposition="auto",
            showlegend=False,
        ),
        row=1, col=3,
    )

    fig.update_layout(
        title="满意度与惩罚项对比",
        height=400,
    )

    return fig


def create_satisfaction_wait_scatter(
    results: Dict[str, SimulationResult],
) -> go.Figure:
    fig = go.Figure()

    colors = ["#1e3a5f", "#ff6b35", "#22c55e", "#8b5cf6"]

    for idx, (name, result) in enumerate(results.items()):
        if result.wait_times and result.satisfaction_scores:
            fig.add_trace(
                go.Scatter(
                    x=result.wait_times,
                    y=result.satisfaction_scores,
                    mode="markers",
                    name=result.strategy_name,
                    marker=dict(
                        color=colors[idx % len(colors)],
                        size=6,
                        opacity=0.6,
                    ),
                    hovertemplate="等位: %{x:.0f}分<br>满意度: %{y:.2f}<extra></extra>",
                )
            )

    fig.update_layout(
        title="等位时间 vs 满意度分布",
        xaxis_title="等位时间 (分钟)",
        yaxis_title="满意度",
        height=400,
        yaxis=dict(range=[0, 1.05]),
    )

    return fig


def create_hourly_satisfaction_chart(
    result: SimulationResult, config: RestaurantConfig
) -> go.Figure:
    hours = list(range(config.open_hour, config.close_hour))
    hour_labels = [f"{h}:00" for h in hours]

    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=hour_labels,
            y=result.hourly_satisfaction,
            mode="lines+markers",
            line=dict(color="#22c55e", width=2),
            fill="tozeroy",
            fillcolor="rgba(34, 197, 94, 0.2)",
        )
    )

    fig.add_hline(
        y=0.8,
        line_dash="dash",
        line_color="orange",
        annotation_text="目标线 0.8",
        annotation_position="top left",
    )

    fig.update_layout(
        title="每小时顾客满意度变化",
        xaxis_title="时间",
        yaxis_title="平均满意度",
        height=350,
        yaxis=dict(range=[0, 1.05]),
    )

    return fig


def create_dining_time_distribution(result: SimulationResult) -> go.Figure:
    if not result.satisfaction_scores:
        return go.Figure()

    dining_times = result.wait_times
    if not dining_times:
        return go.Figure()

    fig = go.Figure()

    fig.add_trace(
        go.Histogram(
            x=dining_times,
            nbinsx=25,
            marker_color="#1e3a5f",
            opacity=0.7,
            name="等位时间分布",
        )
    )

    fig.add_vline(
        x=result.average_wait_time,
        line_dash="dash",
        line_color="#ff6b35",
        annotation_text=f"均值: {result.average_wait_time:.1f}分",
        annotation_position="top right",
    )

    fig.add_vline(
        x=result.median_wait_time,
        line_dash="dot",
        line_color="#22c55e",
        annotation_text=f"中位数: {result.median_wait_time:.1f}分",
        annotation_position="top left",
    )

    fig.update_layout(
        title="混合分布拟合 - 等位时间分布（对数正态+指数）",
        xaxis_title="等位时间 (分钟)",
        yaxis_title="频次",
        height=350,
    )

    return fig


def create_reservation_gap_chart(
    result: SimulationResult, config: RestaurantConfig
) -> go.Figure:
    hours = list(range(config.open_hour, config.close_hour))
    hour_labels = [f"{h}:00" for h in hours]

    fig = make_subplots(
        rows=2, cols=1,
        subplot_titles=("预约 vs 实际到店", "未到店率对翻台率影响"),
        vertical_spacing=0.15,
    )

    fig.add_trace(
        go.Bar(
            x=hour_labels,
            y=result.hourly_reservations,
            name="预约数",
            marker_color="#1e3a5f",
        ),
        row=1, col=1,
    )

    fig.add_trace(
        go.Bar(
            x=hour_labels,
            y=result.hourly_no_shows,
            name="未到店数",
            marker_color="#ef4444",
        ),
        row=1, col=1,
    )

    shows = [
        r - n for r, n in zip(result.hourly_reservations, result.hourly_no_shows)
    ]
    fig.add_trace(
        go.Bar(
            x=hour_labels,
            y=shows,
            name="实际到店",
            marker_color="#22c55e",
        ),
        row=1, col=1,
    )

    no_show_rates = []
    for r, n in zip(result.hourly_reservations, result.hourly_no_shows):
        if r > 0:
            no_show_rates.append(round(n / r * 100, 1))
        else:
            no_show_rates.append(0)

    fig.add_trace(
        go.Scatter(
            x=hour_labels,
            y=no_show_rates,
            mode="lines+markers",
            name="未到店率 (%)",
            line=dict(color="#ff6b35", width=2),
        ),
        row=2, col=1,
    )

    fig.add_hline(
        y=config.reservation_config.no_show_rate * 100,
        line_dash="dash",
        line_color="red",
        annotation_text=f"基准未到店率 {config.reservation_config.no_show_rate*100:.0f}%",
        row=2, col=1,
    )

    fig.update_layout(
        title="预约-到店缺口分析",
        height=600,
        barmode="group",
    )

    return fig


def create_retention_analysis_chart(
    result: SimulationResult, config: RestaurantConfig
) -> go.Figure:
    fig = make_subplots(
        rows=1, cols=3,
        subplot_titles=("挽留效果", "挽留ROI", "挽留成本分析"),
    )

    labels = ["已发送", "已接受", "挽留成功"]
    values = [
        result.retention_offers_sent,
        result.retention_offers_accepted,
        result.retention_offers_accepted,
    ]
    colors = ["#1e3a5f", "#ff6b35", "#22c55e"]

    fig.add_trace(
        go.Bar(
            x=labels,
            y=values,
            marker_color=colors,
            text=[str(v) for v in values],
            textposition="auto",
            showlegend=False,
        ),
        row=1, col=1,
    )

    roi = (
        (result.retention_revenue_saved - result.retention_discount_cost)
        / result.retention_discount_cost * 100
        if result.retention_discount_cost > 0
        else 0
    )
    fig.add_trace(
        go.Indicator(
            mode="number+delta",
            value=roi,
            number=dict(suffix="%", font=dict(size=28)),
            delta=dict(position="bottom", reference=0),
            title=dict(text="挽留ROI", font=dict(size=14)),
        ),
        row=1, col=2,
    )

    cost_labels = ["挽留挽回营收", "优惠成本", "净挽留收益"]
    cost_values = [
        result.retention_revenue_saved,
        result.retention_discount_cost,
        result.retention_revenue_saved - result.retention_discount_cost,
    ]
    cost_colors = ["#22c55e", "#ef4444", "#1e3a5f"]

    fig.add_trace(
        go.Bar(
            x=cost_labels,
            y=cost_values,
            marker_color=cost_colors,
            text=[f"¥{v:,.0f}" for v in cost_values],
            textposition="auto",
            showlegend=False,
        ),
        row=1, col=3,
    )

    fig.update_layout(
        title=f"智能挽留策略分析 (成功率: {result.retention_success_rate:.0%})",
        height=400,
    )

    return fig


def create_dish_impact_chart(
    result: SimulationResult, config: RestaurantConfig
) -> go.Figure:
    if not result.dish_combination_impact:
        return go.Figure()

    dishes = list(result.dish_combination_impact.keys())
    avg_times = [result.dish_combination_impact[d]["avg_dining_time"] for d in dishes]
    counts = [result.dish_combination_impact[d]["count"] for d in dishes]
    turnover_impacts = [result.dish_combination_impact[d]["turnover_impact"] for d in dishes]

    fig = make_subplots(
        rows=1, cols=2,
        subplot_titles=("菜品类型 vs 平均用餐时长", "菜品翻台贡献度"),
    )

    colors_map = {
        "快餐简餐": "#22c55e",
        "家常炒菜": "#1e3a5f",
        "火锅烧烤": "#ff6b35",
        "宴席套餐": "#8b5cf6",
        "甜品饮品": "#eab308",
    }
    dish_colors = [colors_map.get(d, "#999999") for d in dishes]

    fig.add_trace(
        go.Bar(
            x=dishes,
            y=avg_times,
            marker_color=dish_colors,
            text=[f"{t:.1f}分" for t in avg_times],
            textposition="auto",
            showlegend=False,
        ),
        row=1, col=1,
    )

    fig.add_hline(
        y=result.average_dining_time,
        line_dash="dash",
        line_color="red",
        annotation_text=f"全局均值: {result.average_dining_time:.1f}分",
        row=1, col=1,
    )

    fig.add_trace(
        go.Bar(
            x=dishes,
            y=turnover_impacts,
            marker_color=dish_colors,
            text=[f"{t:.2f}" for t in turnover_impacts],
            textposition="auto",
            showlegend=False,
        ),
        row=1, col=2,
    )

    fig.update_layout(
        title="菜品组合对用餐时长的影响分析",
        height=400,
    )

    return fig


def create_no_show_turnover_impact(
    result: SimulationResult, config: RestaurantConfig
) -> go.Figure:
    if result.total_reservations == 0:
        return go.Figure()

    scenarios = ["当前状态", "无未到店", "未到店减半"]
    no_show_rates = [
        config.reservation_config.no_show_rate,
        0.0,
        config.reservation_config.no_show_rate / 2,
    ]

    current_turnover = result.table_turnover_rate
    total_tables = config.tables_2_seat + config.tables_4_seat + config.tables_6_seat
    operating_hours = config.close_hour - config.open_hour

    turnovers = []
    for ns_rate in no_show_rates:
        recovered = result.reservation_no_shows * (
            (config.reservation_config.no_show_rate - ns_rate)
            / config.reservation_config.no_show_rate
            if config.reservation_config.no_show_rate > 0
            else 0
        )
        projected = current_turnover + recovered / (total_tables * operating_hours)
        turnovers.append(round(projected, 3))

    fig = go.Figure()

    fig.add_trace(
        go.Bar(
            x=scenarios,
            y=turnovers,
            marker_color=["#1e3a5f", "#22c55e", "#ff6b35"],
            text=[f"{t:.3f}" for t in turnovers],
            textposition="auto",
        )
    )

    fig.update_layout(
        title=f"未到店率对翻台率影响 (当前影响: -{result.no_show_impact_on_turnover:.3f})",
        xaxis_title="场景",
        yaxis_title="翻台率 (次/桌/天)",
        height=400,
    )

    return fig
