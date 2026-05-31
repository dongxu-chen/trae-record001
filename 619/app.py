import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import networkx as nx
from pyvis.network import Network
import streamlit.components.v1 as components
import tempfile
import os

from data_generator import DataGenerator
from graph_analyzer import GraphAnalyzer
from rule_engine import RuleEngine
from ml_detector import MLDetector
from fraud_scorer import FraudScorer
from gang_detector import GangDetector
from appeal_handler import AppealHandler
from pattern_tracker import PatternEvolutionTracker

st.set_page_config(
    page_title="电商刷单检测系统",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded"
)

RISK_COLORS = {
    "高风险": "#FF4B4B",
    "中风险": "#FFA500",
    "低风险": "#FFD700",
    "正常": "#00CC88"
}

RISK_EMOJIS = {
    "高风险": "🔴",
    "中风险": "🟠",
    "低风险": "🟡",
    "正常": "🟢"
}

ACTION_SEVERITY_COLORS = {
    "紧急": "#FF0000",
    "高": "#FF4B4B",
    "中": "#FFA500",
    "低": "#FFD700"
}


@st.cache_resource
def generate_and_analyze(n_normal, n_fraud, orders_normal, orders_fraud,
                         use_sampling, max_nodes, sampling_ratio,
                         is_promotion, promotion_scale, contamination):
    gen = DataGenerator(seed=42)
    data = gen.generate(
        n_normal_users=n_normal,
        n_fraud_users=n_fraud,
        orders_per_normal=orders_normal,
        orders_per_fraud=orders_fraud
    )

    analyzer = GraphAnalyzer(
        data["users"], data["devices"], data["ip_records"],
        data["addresses"], data["orders"],
        use_sampling=use_sampling,
        max_nodes=max_nodes,
        sampling_ratio=sampling_ratio
    )
    analyzer.build_graph()
    communities = analyzer.detect_communities()
    graph_features = analyzer.compute_user_graph_features()
    community_stats = analyzer.get_community_stats()
    sampling_stats = analyzer.get_sampling_stats()

    engine = RuleEngine(
        data["users"], data["orders"], data["devices"],
        data["ip_records"], data["addresses"], graph_features
    )
    rule_results = engine.evaluate_all()

    detector = MLDetector(data["users"], data["orders"], graph_features)
    detector.extract_features()
    ml_scores = detector.train_isolation_forest(contamination=contamination)
    cluster_stats = detector.cluster_users()

    scorer = FraudScorer(
        data["users"], data["orders"], rule_results,
        ml_scores, graph_features, community_stats,
        is_promotion=is_promotion,
        promotion_scale=promotion_scale
    )
    scored_df = scorer.compute_composite_scores()
    summary = scorer.get_summary()

    gang_detector = GangDetector(
        data["users"], data["orders"], data["devices"],
        data["ip_records"], data["addresses"], graph_features
    )
    gangs = gang_detector.detect_gangs(min_size=3)
    gang_summary = gang_detector.get_gang_summary()

    appeal_handler = AppealHandler(data["users"], data["orders"], scored_df)
    appeal_handler.generate_mock_appeals(n=15)

    pattern_tracker = PatternEvolutionTracker(
        data["orders"], data["users"], rule_results,
        gang_detector.gang_analysis
    )
    pattern_tracker.analyze_time_periods(period_days=15)
    pattern_tracker.extract_period_patterns()
    pattern_tracker.detect_pattern_changes(threshold=0.3)
    pattern_alerts = pattern_tracker.generate_alerts()

    return {
        "data": data,
        "analyzer": analyzer,
        "graph_features": graph_features,
        "community_stats": community_stats,
        "sampling_stats": sampling_stats,
        "rule_results": rule_results,
        "rule_engine": engine,
        "ml_scores": ml_scores,
        "ml_detector": detector,
        "cluster_stats": cluster_stats,
        "scorer": scorer,
        "scored_df": scored_df,
        "summary": summary,
        "gang_detector": gang_detector,
        "gang_summary": gang_summary,
        "appeal_handler": appeal_handler,
        "pattern_tracker": pattern_tracker,
        "pattern_alerts": pattern_alerts,
    }


def render_overview(summary, sampling_stats):
    st.subheader("📊 系统概览")

    if summary.get("is_promotion", False):
        st.success(f"🎉 当前为大促模式，阈值已放宽（系数：{summary.get('promotion_scale', 0.75)}）")

    if sampling_stats.get("sampled", False):
        st.info(f"📉 已启用图采样（原{sampling_stats['original_users']}用户 → 采样{sampling_stats['sampled_users']}用户）")

    cols = st.columns(5)
    metrics = [
        ("总用户数", summary["total_users"], "👥"),
        ("高风险", summary["high_risk"], "🔴"),
        ("中风险", summary["medium_risk"], "🟠"),
        ("低风险", summary["low_risk"], "🟡"),
        ("正常", summary["normal"], "🟢"),
    ]
    for col, (label, value, emoji) in zip(cols, metrics):
        col.metric(f"{emoji} {label}", value)

    cols2 = st.columns(3)
    with cols2[0]:
        st.metric("平均风险评分", summary["avg_score"])
    with cols2[1]:
        st.metric("最高风险评分", summary["max_score"])
    with cols2[2]:
        th = summary.get("thresholds", {})
        st.metric("高风险阈值", f"{th.get('high_risk', 70):.0f}")


def render_threshold_comparison(summary):
    st.subheader("⚖️ 阈值对比分析")

    default_th = {"high_risk": 70, "medium_risk": 45, "low_risk": 25}
    current_th = summary.get("thresholds", default_th)

    comp_data = {
        "风险等级": ["高风险", "中风险", "低风险"],
        "默认阈值": [70, 45, 25],
        "当前阈值": [current_th.get("high_risk", 70), current_th.get("medium_risk", 45), current_th.get("low_risk", 25)]
    }
    comp_df = pd.DataFrame(comp_data)

    fig = go.Figure(data=[
        go.Bar(name="默认阈值", x=comp_df["风险等级"], y=comp_df["默认阈值"], marker_color="#CCCCCC"),
        go.Bar(name="当前阈值", x=comp_df["风险等级"], y=comp_df["当前阈值"], marker_color="#FF6B6B")
    ])
    fig.update_layout(
        title="阈值对比",
        barmode="group",
        yaxis_title="阈值分数"
    )
    st.plotly_chart(fig, use_container_width=True)


def render_risk_distribution(scored_df):
    st.subheader("📈 风险分布分析")
    cols = st.columns(2)

    with cols[0]:
        risk_counts = scored_df["risk_level"].value_counts()
        fig_pie = px.pie(
            values=risk_counts.values,
            names=risk_counts.index,
            title="风险等级分布",
            color=risk_counts.index,
            color_discrete_map=RISK_COLORS,
            hole=0.4
        )
        fig_pie.update_traces(textposition="inside", textinfo="percent+label")
        st.plotly_chart(fig_pie, use_container_width=True)

    with cols[1]:
        fig_hist = px.histogram(
            scored_df, x="composite_score", nbins=30,
            title="综合风险评分分布",
            color="risk_level",
            color_discrete_map=RISK_COLORS,
            labels={"composite_score": "综合评分", "count": "用户数"}
        )
        st.plotly_chart(fig_hist, use_container_width=True)

    cols2 = st.columns(2)
    with cols2[0]:
        fig_box = px.box(
            scored_df, y="composite_score", x="risk_level",
            title="各风险等级评分箱线图",
            color="risk_level",
            color_discrete_map=RISK_COLORS,
            category_orders={"risk_level": ["正常", "低风险", "中风险", "高风险"]}
        )
        st.plotly_chart(fig_box, use_container_width=True)

    with cols2[1]:
        score_components = scored_df[["rule_score", "ml_score", "graph_score"]].mean()
        fig_radar = go.Figure(data=go.Scatterpolar(
            r=score_components.values,
            theta=["规则引擎", "ML模型", "图分析"],
            fill="toself",
            line_color="#FF6B6B"
        ))
        fig_radar.update_layout(
            polar=dict(radialaxis=dict(visible=True, range=[0, max(score_components.max(), 1)])),
            title="平均评分构成（雷达图）",
            showlegend=False
        )
        st.plotly_chart(fig_radar, use_container_width=True)


def render_score_table(scored_df):
    st.subheader("📋 风险用户排行")

    filter_level = st.multiselect(
        "筛选风险等级",
        ["高风险", "中风险", "低风险", "正常"],
        default=["高风险", "中风险"]
    )

    min_score = st.slider("最低综合评分", 0, 100, 25)

    filtered = scored_df[
        (scored_df["risk_level"].isin(filter_level)) &
        (scored_df["composite_score"] >= min_score)
    ]

    display_cols = [
        "user_id", "username", "register_date", "account_age_days",
        "rule_score", "ml_score", "graph_score", "composite_score",
        "risk_level", "n_risk_orders"
    ]

    if "raw_composite_score" in filtered.columns:
        display_cols.insert(8, "raw_composite_score")

    st.dataframe(
        filtered[display_cols].reset_index(drop=True),
        use_container_width=True,
        height=400
    )

    return filtered


def render_user_detail(scored_df, results):
    st.subheader("🔍 用户详细分析")
    user_id = st.selectbox(
        "选择用户查看详情",
        scored_df["user_id"].tolist(),
        format_func=lambda x: f"{x} - {scored_df[scored_df['user_id']==x]['username'].values[0]} ({scored_df[scored_df['user_id']==x]['risk_level'].values[0]})"
    )

    user_data = scored_df[scored_df["user_id"] == user_id].iloc[0]

    col1, col2 = st.columns([1, 2])

    with col1:
        st.markdown("#### 用户基本信息")
        risk_emoji = RISK_EMOJIS.get(user_data["risk_level"], "")
        st.write(f"**用户ID**: {user_data['user_id']}")
        st.write(f"**用户名**: {user_data['username']}")
        st.write(f"**注册日期**: {user_data['register_date']}")
        st.write(f"**账号天数**: {user_data['account_age_days']}天")
        st.write(f"**风险等级**: {risk_emoji} {user_data['risk_level']}")
        st.write(f"**风险订单数**: {user_data['n_risk_orders']}")

        if "raw_composite_score" in user_data and user_data["raw_composite_score"] != user_data["composite_score"]:
            st.info(f"原始评分: {user_data['raw_composite_score']} → 大促调整后: {user_data['composite_score']}")

        st.markdown("#### 评分详情")
        fig_gauge = go.Figure()
        fig_gauge.add_trace(go.Indicator(
            mode="gauge+number",
            value=user_data["composite_score"],
            domain={"x": [0, 1], "y": [0, 1]},
            title={"text": "综合风险评分"},
            gauge={
                "axis": {"range": [0, 100]},
                "bar": {"color": RISK_COLORS.get(user_data["risk_level"], "gray")},
                "steps": [
                    {"range": [0, 25], "color": "#E8F5E9"},
                    {"range": [25, 45], "color": "#FFF9C4"},
                    {"range": [45, 70], "color": "#FFE0B2"},
                    {"range": [70, 100], "color": "#FFCDD2"},
                ],
                "threshold": {
                    "line": {"color": "red", "width": 4},
                    "thickness": 0.75,
                    "value": 70
                }
            }
        ))
        fig_gauge.update_layout(height=250)
        st.plotly_chart(fig_gauge, use_container_width=True)

        score_data = pd.DataFrame({
            "评分维度": ["规则引擎", "ML模型", "图分析"],
            "分数": [user_data["rule_score"], user_data["ml_score"], user_data["graph_score"]]
        })
        fig_bar = px.bar(score_data, x="评分维度", y="分数", title="各维度评分",
                         color="分数", color_continuous_scale="Reds")
        fig_bar.update_layout(height=250)
        st.plotly_chart(fig_bar, use_container_width=True)

    with col2:
        st.markdown("#### 触发规则详情")
        rules = user_data["rule_details"]
        if rules:
            rules_df = pd.DataFrame(rules)
            st.dataframe(rules_df, use_container_width=True, height=200)
        else:
            st.info("未触发任何规则")

        col2a, col2b = st.columns(2)
        with col2a:
            st.markdown("#### 处理建议")
            for suggestion in user_data["suggestions"]:
                st.write(suggestion)

        with col2b:
            st.markdown("#### 强制执行措施")
            actions = user_data.get("enforcement_actions", [])
            if actions:
                action_df = pd.DataFrame(actions)
                for _, action in action_df.iterrows():
                    color = ACTION_SEVERITY_COLORS.get(action["severity"], "#999")
                    st.markdown(f'<span style="color:{color};font-weight:bold;">⚡ {action["action"]}</span> ({action["severity"]})', unsafe_allow_html=True)
            else:
                st.info("无强制执行措施")

        st.markdown("#### 关联用户")
        linked = user_data["linked_users"]
        if linked:
            linked_info = scored_df[scored_df["user_id"].isin(linked)][
                ["user_id", "username", "composite_score", "risk_level"]
            ]
            st.dataframe(linked_info.reset_index(drop=True), use_container_width=True, height=200)
        else:
            st.info("未发现关联用户")


def render_graph_analysis(results, scored_df):
    st.subheader("🕸️ 关联图分析")

    sampling_stats = results.get("sampling_stats", {})
    if sampling_stats.get("sampled", False):
        st.info(f"📉 已启用图采样：原{sampling_stats['original_users']}用户 → 采样{sampling_stats['sampled_users']}用户（刷单{sampling_stats.get('fraud_in_sample', 0)}人，正常{sampling_stats.get('normal_in_sample', 0)}人）")

    user_id = st.selectbox(
        "选择用户查看关联图",
        scored_df["user_id"].tolist(),
        key="graph_user",
        format_func=lambda x: f"{x} - {scored_df[scored_df['user_id']==x]['username'].values[0]}"
    )

    subgraph = results["analyzer"].get_subgraph_for_user(user_id, depth=2)

    if len(subgraph.nodes()) == 0:
        st.warning("该用户无关联图数据")
        return

    net = Network(height="500px", width="100%", bgcolor="#222222", font_color="white")
    net.heading = ""

    for node, data in subgraph.nodes(data=True):
        node_type = data.get("type", "unknown")
        if node_type == "user":
            color = "#FF4B4B" if scored_df[scored_df["user_id"] == node]["risk_level"].values[0] in ["高风险", "中风险"] else "#00CC88"
            label = data.get("username", node)
            size = 25
        elif node_type == "device":
            color = "#4ECDC4"
            label = f"📱{data.get('device_hash', '')[:6]}"
            size = 15
        elif node_type == "ip":
            color = "#FFE66D"
            label = f"🌐{data.get('ip_address', '')}"
            size = 15
        elif node_type == "address":
            color = "#A8E6CF"
            label = f"📦{data.get('address', '')[:10]}"
            size = 15
        else:
            color = "#95E1D3"
            label = node
            size = 10

        net.add_node(node, label=label, color=color, size=size, title=f"{node_type}: {label}")

    for u, v, data in subgraph.edges(data=True):
        relation = data.get("relation", "")
        net.add_edge(u, v, title=relation, color="#666666")

    net.repulsion(node_distance=150, central_gravity=0.2, spring_length=100)

    with tempfile.NamedTemporaryFile(delete=False, suffix=".html", mode="w", encoding="utf-8") as f:
        net.save_graph(f.name)
        html_path = f.name

    with open(html_path, "r", encoding="utf-8") as f:
        html_content = f.read()
    components.html(html_content, height=520)
    os.unlink(html_path)

    st.markdown("#### 社区检测统计")
    comm_stats = results["community_stats"]
    if comm_stats:
        comm_df = pd.DataFrame(comm_stats)
        comm_display = comm_df[["community_id", "member_count", "total_orders", "total_amount", "avg_account_age"]]
        comm_display.columns = ["社区ID", "成员数", "总订单数", "总金额", "平均账号天数"]
        st.dataframe(comm_display, use_container_width=True)

        fig_comm = px.scatter(
            comm_df, x="member_count", y="total_orders",
            size="total_amount", color="fraud_ratio",
            title="社区分布（颜色=刷单比例）",
            color_continuous_scale="Reds",
            labels={"member_count": "成员数", "total_orders": "总订单数", "fraud_ratio": "刷单比例"}
        )
        st.plotly_chart(fig_comm, use_container_width=True)
    else:
        st.info("未检测到明显社区结构")


def render_ml_analysis(results, scored_df):
    st.subheader("🤖 机器学习分析")
    detector = results["ml_detector"]
    features_df = detector.user_features_df

    if features_df is None:
        st.warning("ML特征未提取")
        return

    cols = st.columns(2)

    with cols[0]:
        fig_scatter = px.scatter(
            features_df, x="n_orders", y="avg_amount",
            color="ml_anomaly_score", color_continuous_scale="RdYlGn_r",
            title="订单数 vs 均价（颜色=ML异常评分）",
            hover_data=["user_id"],
            labels={"n_orders": "订单数", "avg_amount": "平均金额", "ml_anomaly_score": "ML异常评分"}
        )
        st.plotly_chart(fig_scatter, use_container_width=True)

    with cols[1]:
        fig_scatter2 = px.scatter(
            features_df, x="shared_device_count", y="shared_ip_count",
            color="ml_anomaly_score", color_continuous_scale="RdYlGn_r",
            title="共享设备数 vs 共享IP数（颜色=ML异常评分）",
            hover_data=["user_id"],
            labels={"shared_device_count": "共享设备数", "shared_ip_count": "共享IP数"}
        )
        st.plotly_chart(fig_scatter2, use_container_width=True)

    st.markdown("#### 特征分布对比（实际刷单 vs 正常）")
    feature_options = [
        "n_orders", "avg_amount", "avg_order_interval_h",
        "night_order_ratio", "shared_device_count", "shared_ip_count"
    ]
    feature_labels = {
        "n_orders": "订单数", "avg_amount": "平均金额",
        "avg_order_interval_h": "平均下单间隔(小时)",
        "night_order_ratio": "深夜下单比例",
        "shared_device_count": "共享设备数", "shared_ip_count": "共享IP数"
    }
    selected_feature = st.selectbox("选择特征", feature_options, format_func=lambda x: feature_labels.get(x, x))

    fig_violin = px.violin(
        features_df, y=selected_feature, x="is_fraud",
        title=f"{feature_labels.get(selected_feature, selected_feature)} 分布对比",
        color="is_fraud",
        box=True,
        labels={selected_feature: feature_labels.get(selected_feature, selected_feature), "is_fraud": "是否刷单"}
    )
    st.plotly_chart(fig_violin, use_container_width=True)

    if "cluster_label" in features_df.columns:
        st.markdown("#### DBSCAN聚类结果")
        cluster_counts = features_df["cluster_label"].value_counts().sort_index()
        fig_cluster = px.bar(
            x=cluster_counts.index.astype(str), y=cluster_counts.values,
            title="聚类分布", labels={"x": "簇编号", "y": "用户数"},
            color=cluster_counts.values, color_continuous_scale="Blues"
        )
        st.plotly_chart(fig_cluster, use_container_width=True)

        cluster_stats = results["cluster_stats"]
        if cluster_stats:
            cs_df = pd.DataFrame(cluster_stats).T
            cs_display = cs_df[["size", "fraud_ratio", "avg_orders", "avg_amount", "avg_shared_devices"]]
            cs_display.columns = ["大小", "刷单比例", "平均订单数", "平均金额", "平均共享设备数"]
            st.dataframe(cs_display, use_container_width=True)


def render_rule_analysis(results, scored_df):
    st.subheader("📏 规则引擎分析")
    rule_results = results["rule_results"]

    rule_counts = {}
    rule_total_scores = {}
    for user_id, rules in rule_results.items():
        for rule in rules:
            name = rule["rule_name"]
            rule_counts[name] = rule_counts.get(name, 0) + 1
            rule_total_scores[name] = rule_total_scores.get(name, 0) + rule["score"]

    cols = st.columns(2)
    with cols[0]:
        fig_rule_hit = px.bar(
            x=list(rule_counts.keys()), y=list(rule_counts.values()),
            title="规则命中次数统计",
            labels={"x": "规则名称", "y": "命中次数"},
            color=list(rule_counts.values()),
            color_continuous_scale="Oranges"
        )
        fig_rule_hit.update_xaxes(tickangle=30)
        st.plotly_chart(fig_rule_hit, use_container_width=True)

    with cols[1]:
        fig_rule_score = px.bar(
            x=list(rule_total_scores.keys()), y=list(rule_total_scores.values()),
            title="规则累计扣分统计",
            labels={"x": "规则名称", "y": "累计扣分"},
            color=list(rule_total_scores.values()),
            color_continuous_scale="Reds"
        )
        fig_rule_score.update_xaxes(tickangle=30)
        st.plotly_chart(fig_rule_score, use_container_width=True)

    scored_with_rules = scored_df.copy()
    scored_with_rules["rule_count"] = scored_with_rules["rule_details"].apply(len)
    fig_rule_vs_score = px.scatter(
        scored_with_rules, x="rule_count", y="composite_score",
        color="risk_level", color_discrete_map=RISK_COLORS,
        title="触发规则数 vs 综合评分",
        labels={"rule_count": "触发规则数", "composite_score": "综合评分"}
    )
    st.plotly_chart(fig_rule_vs_score, use_container_width=True)


def render_order_analysis(results, scored_df):
    st.subheader("📦 订单异常分析")
    data = results["data"]
    orders = data["orders"]

    cols = st.columns(2)
    with cols[0]:
        fig_hourly = px.histogram(
            orders, x="order_hour", nbins=24,
            title="订单时段分布",
            color="is_fraud",
            labels={"order_hour": "下单小时", "is_fraud": "是否刷单"},
            barmode="overlay"
        )
        st.plotly_chart(fig_hourly, use_container_width=True)

    with cols[1]:
        fig_amount = px.histogram(
            orders, x="amount", nbins=50,
            title="订单金额分布",
            color="is_fraud",
            labels={"amount": "订单金额", "is_fraud": "是否刷单"},
            barmode="overlay"
        )
        st.plotly_chart(fig_amount, use_container_width=True)

    cols2 = st.columns(2)
    with cols2[0]:
        fig_cat = px.histogram(
            orders, x="category",
            title="商品类目分布",
            color="is_fraud",
            labels={"category": "商品类目", "is_fraud": "是否刷单"},
            barmode="group"
        )
        st.plotly_chart(fig_cat, use_container_width=True)

    with cols2[1]:
        risk_order_users = scored_df[scored_df["n_risk_orders"] > 0]
        if len(risk_order_users) > 0:
            fig_risk_orders = px.bar(
                risk_order_users.head(20), x="user_id", y="n_risk_orders",
                title="风险订单数TOP20用户",
                color="risk_level", color_discrete_map=RISK_COLORS,
                labels={"n_risk_orders": "风险订单数"}
            )
            fig_risk_orders.update_xaxes(tickangle=45)
            st.plotly_chart(fig_risk_orders, use_container_width=True)


def render_model_performance(results, scored_df):
    st.subheader("🎯 模型效果评估")

    actual = scored_df["is_fraud_actual"].astype(int)
    predicted = (scored_df["composite_score"] >= results["summary"]["thresholds"]["medium_risk"]).astype(int)

    tp = ((actual == 1) & (predicted == 1)).sum()
    fp = ((actual == 0) & (predicted == 1)).sum()
    tn = ((actual == 0) & (predicted == 0)).sum()
    fn = ((actual == 1) & (predicted == 0)).sum()

    precision = tp / (tp + fp) if (tp + fp) > 0 else 0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0
    accuracy = (tp + tn) / (tp + fp + tn + fn)

    cols = st.columns(4)
    cols[0].metric("准确率 (Accuracy)", f"{accuracy:.2%}")
    cols[1].metric("精确率 (Precision)", f"{precision:.2%}")
    cols[2].metric("召回率 (Recall)", f"{recall:.2%}")
    cols[3].metric("F1分数", f"{f1:.2%}")

    cm = np.array([[tn, fp], [fn, tp]])
    fig_cm = px.imshow(
        cm, text_auto=True,
        x=["预测正常", "预测刷单"],
        y=["实际正常", "实际刷单"],
        title="混淆矩阵",
        color_continuous_scale="Blues"
    )
    st.plotly_chart(fig_cm, use_container_width=True)

    thresholds = np.arange(0, 100, 2)
    precisions = []
    recalls_list = []
    for t in thresholds:
        pred = (scored_df["composite_score"] >= t).astype(int)
        tp_t = ((actual == 1) & (pred == 1)).sum()
        fp_t = ((actual == 0) & (pred == 1)).sum()
        fn_t = ((actual == 1) & (pred == 0)).sum()
        p = tp_t / (tp_t + fp_t) if (tp_t + fp_t) > 0 else 0
        r = tp_t / (tp_t + fn_t) if (tp_t + fn_t) > 0 else 0
        precisions.append(p)
        recalls_list.append(r)

    fig_pr = go.Figure()
    fig_pr.add_trace(go.Scatter(x=list(thresholds), y=precisions, mode="lines", name="Precision"))
    fig_pr.add_trace(go.Scatter(x=list(thresholds), y=recalls_list, mode="lines", name="Recall"))
    fig_pr.update_layout(
        title="Precision-Recall vs 阈值",
        xaxis_title="评分阈值",
        yaxis_title="指标值"
    )
    st.plotly_chart(fig_pr, use_container_width=True)


def render_gang_detection(results, scored_df):
    st.subheader("👥 刷单团伙识别")

    gang_summary = results.get("gang_summary", [])

    if not gang_summary:
        st.info("未检测到明显的刷单团伙")
        return

    cols = st.columns(4)
    cols[0].metric("检测到团伙数", len(gang_summary))
    high_risk = [g for g in gang_summary if "高危" in g["risk_level"]]
    cols[1].metric("高危团伙数", len(high_risk))
    medium_risk = [g for g in gang_summary if "中危" in g["risk_level"]]
    cols[2].metric("中危团伙数", len(medium_risk))
    total_members = sum(g["member_count"] for g in gang_summary)
    cols[3].metric("团伙总人数", total_members)

    st.markdown("#### 团伙列表")
    gang_df = pd.DataFrame(gang_summary)
    display_cols = [
        "gang_id", "risk_level", "member_count", "fraud_count", "fraud_ratio",
        "total_orders", "total_amount", "shared_device_count",
        "shared_ip_count", "shared_address_count", "first_seen", "last_seen"
    ]
    gang_display = gang_df[display_cols].copy()
    gang_display.columns = [
        "团伙ID", "风险等级", "成员数", "刷单人数", "刷单比例",
        "总订单", "总金额", "共享设备数", "共享IP数", "共享地址数",
        "首次出现", "最后活跃"
    ]
    st.dataframe(gang_display, use_container_width=True, height=300)

    selected_gang = st.selectbox(
        "选择团伙查看详情",
        [f"团伙{g['gang_id']} - {g['risk_level']} ({g['member_count']}人)" for g in gang_summary]
    )

    if selected_gang:
        gang_id = int(selected_gang.split("团伙")[1].split(" - ")[0])
        gang_data = gang_df[gang_df["gang_id"] == gang_id].iloc[0]

        col1, col2 = st.columns([1, 1])

        with col1:
            st.markdown("#### 团伙基本信息")
            st.write(f"**团伙ID**: {gang_data['gang_id']}")
            st.write(f"**风险等级**: {gang_data['risk_level']}")
            st.write(f"**成员数**: {gang_data['member_count']}人")
            st.write(f"**刷单人数**: {gang_data['fraud_count']}人 ({gang_data['fraud_ratio']:.0%})")
            st.write(f"**总订单**: {gang_data['total_orders']}单")
            st.write(f"**总金额**: ¥{gang_data['total_amount']:.2f}")
            st.write(f"**活动周期**: {gang_data['first_seen']} ~ {gang_data['last_seen']}")

            st.markdown("#### 作案手法")
            for mo in gang_data["modus_operandi"]:
                st.markdown(f"- 🔹 {mo}")

            st.markdown("#### 核心成员")
            for member in gang_data["key_members"]:
                user_info = scored_df[scored_df["user_id"] == member].iloc[0]
                st.write(f"- {member} ({user_info['username']}) - {user_info['risk_level']} - 评分: {user_info['composite_score']}")

        with col2:
            st.markdown("#### 团伙成员分布")
            members = gang_data["members"]
            member_info = scored_df[scored_df["user_id"].isin(members)]

            fig_members = px.scatter(
                member_info, x="composite_score", y="n_risk_orders",
                color="risk_level", color_discrete_map=RISK_COLORS,
                hover_data=["username", "rule_score", "ml_score"],
                size="composite_score",
                title="成员评分 vs 风险订单数",
                labels={"composite_score": "综合评分", "n_risk_orders": "风险订单数"}
            )
            st.plotly_chart(fig_members, use_container_width=True)

            gang_detector = results["gang_detector"]
            network_data = gang_detector.get_gang_network_data(gang_id)

            if network_data and network_data["edges"]:
                st.markdown("#### 成员关联网络")
                net = Network(height="350px", width="100%", bgcolor="#222222", font_color="white")
                net.heading = ""

                for member in network_data["members"]:
                    user_risk = member_info[member_info["user_id"] == member]["risk_level"].values[0]
                    color = RISK_COLORS.get(user_risk, "#999")
                    net.add_node(
                        member,
                        label=member[-4:],
                        color=color,
                        size=20,
                        title=member
                    )

                for u1, u2, rel in network_data["edges"]:
                    net.add_edge(u1, u2, title=rel, color="#666")

                net.repulsion(node_distance=120, central_gravity=0.3)

                with tempfile.NamedTemporaryFile(delete=False, suffix=".html", mode="w", encoding="utf-8") as f:
                    net.save_graph(f.name)
                    html_path = f.name

                with open(html_path, "r", encoding="utf-8") as f:
                    html_content = f.read()
                components.html(html_content, height=370)
                os.unlink(html_path)


def render_appeal_handling(results):
    st.subheader("📝 申诉处理中心")

    appeal_handler = results["appeal_handler"]
    appeal_stats = appeal_handler.get_appeal_statistics()

    cols = st.columns(5)
    cols[0].metric("申诉总数", appeal_stats["total"])
    cols[1].metric("待审核", appeal_stats["pending"],
                   delta=f"{appeal_stats['pending']}件", delta_color="off")
    cols[2].metric("已通过", appeal_stats["approved"])
    cols[3].metric("部分通过", appeal_stats["partial"])
    cols[4].metric("申诉通过率", f"{appeal_stats['approval_rate']:.0%}")

    st.markdown("---")

    col1, col2 = st.columns([1, 2])

    with col1:
        st.markdown("#### 提交申诉")
        order_id = st.text_input("订单号", placeholder="请输入订单号")
        submitter = st.selectbox("申诉方", ["商家", "买家", "平台"])
        appeal_reason = st.text_area(
            "申诉理由",
            placeholder="请详细说明申诉理由，如：正常交易凭证、物流记录、聊天记录等"
        )
        evidence = st.text_area(
            "证据说明",
            placeholder="描述提供的证据材料，如：聊天截图、物流凭证、支付凭证等"
        )

        if st.button("提交申诉", use_container_width=True):
            if not order_id or not appeal_reason:
                st.warning("请填写订单号和申诉理由")
            else:
                appeal, msg = appeal_handler.create_appeal(
                    order_id, appeal_reason, evidence, submitter
                )
                if appeal:
                    st.success(f"申诉提交成功！申诉号：{appeal['appeal_id']}")
                    st.rerun()
                else:
                    st.error(msg)

    with col2:
        st.markdown("#### 申诉列表")
        status_filter = st.multiselect(
            "筛选状态",
            ["待审核", "已审核"],
            default=["待审核"]
        )

        appeals = appeal_handler.get_appeals_by_status()
        if status_filter:
            appeals = [a for a in appeals if a["status"] in status_filter]

        if appeals:
            appeal_df = pd.DataFrame(appeals)
            display_cols = [
                "appeal_id", "order_id", "submitter_role",
                "status", "original_risk_level", "submit_time",
                "final_decision"
            ]
            display_df = appeal_df[display_cols].copy()
            display_df.columns = [
                "申诉号", "订单号", "申诉方", "状态",
                "原风险等级", "提交时间", "最终裁定"
            ]
            st.dataframe(display_df, use_container_width=True, height=300)

            selected_appeal = st.selectbox(
                "选择申诉进行审核",
                [f"{a['appeal_id']} - {a['order_id']} ({a['status']})" for a in appeals]
            )

            if selected_appeal:
                appeal_id = selected_appeal.split(" - ")[0]
                appeal = next((a for a in appeals if a["appeal_id"] == appeal_id), None)

                if appeal:
                    st.markdown("#### 申诉详情")
                    st.write(f"**申诉号**: {appeal['appeal_id']}")
                    st.write(f"**订单号**: {appeal['order_id']}")
                    st.write(f"**用户ID**: {appeal['user_id']}")
                    st.write(f"**申诉方**: {appeal['submitter_role']}")
                    st.write(f"**提交时间**: {appeal['submit_time']}")
                    st.write(f"**原风险等级**: {appeal['original_risk_level']}")
                    st.markdown(f"**申诉理由**: {appeal['appeal_reason']}")
                    st.markdown(f"**证据说明**: {appeal['evidence']}")

                    if appeal["status"] == "待审核":
                        st.markdown("#### 审核处理")
                        reviewer = st.text_input("审核人", value="系统管理员")
                        decision = st.selectbox(
                            "审核结果",
                            ["通过", "部分通过", "驳回"]
                        )
                        comment = st.text_area("审核意见")

                        if st.button("完成审核", use_container_width=True):
                            appeal_handler.review_appeal(
                                appeal_id, decision, reviewer, comment
                            )
                            st.success("审核完成！")
                            st.rerun()
                    else:
                        st.markdown("#### 审核结果")
                        st.write(f"**审核人**: {appeal['reviewer']}")
                        st.write(f"**审核时间**: {appeal['review_time']}")
                        st.write(f"**最终裁定**: {appeal['final_decision']}")
                        st.write(f"**调整后风险等级**: {appeal['adjusted_risk_level']}")
                        st.markdown(f"**审核意见**: {appeal['review_comment']}")
        else:
            st.info("暂无申诉记录")


def render_pattern_evolution(results):
    st.subheader("📈 刷单模式演化追踪")

    pattern_tracker = results["pattern_tracker"]
    alerts = results.get("pattern_alerts", [])

    if alerts:
        st.markdown("#### ⚠️ 系统告警")
        for alert in alerts:
            alert_color = "#FF4B4B" if alert["level"] == "critical" else "#FFA500"
            alert_icon = "🚨" if alert["level"] == "critical" else "⚠️"
            st.markdown(
                f'<div style="padding: 10px; background-color: {alert_color}20; '
                f'border-left: 4px solid {alert_color}; border-radius: 4px;">'
                f'{alert_icon} <b>{alert["period"]}</b> - {alert["summary"]}'
                f'</div>',
                unsafe_allow_html=True
            )
            with st.expander("查看详情"):
                for detail in alert["details"]:
                    if isinstance(detail, dict):
                        st.write(f"- {detail.get('metric', '')}: {detail.get('direction', '')} {detail.get('change_pct', 0):.0%}")
                    else:
                        st.write(f"- {detail}")
            st.markdown("<br>", unsafe_allow_html=True)

    st.markdown("#### 关键指标趋势")
    trend_df = pattern_tracker.get_pattern_trend_data()

    if not trend_df.empty:
        metric_options = [
            "avg_order_amount", "low_value_ratio",
            "night_order_ratio", "new_account_ratio", "total_orders"
        ]
        metric_labels = {
            "avg_order_amount": "平均订单金额",
            "low_value_ratio": "低价单占比(%)",
            "night_order_ratio": "深夜单占比(%)",
            "new_account_ratio": "新账号占比(%)",
            "total_orders": "订单总量"
        }

        cols = st.columns(2)
        for i, metric in enumerate(["avg_order_amount", "total_orders"]):
            with cols[i]:
                fig = px.line(
                    trend_df, x="period", y=metric,
                    title=metric_labels[metric],
                    markers=True
                )
                st.plotly_chart(fig, use_container_width=True)

        cols2 = st.columns(3)
        for i, metric in enumerate(["low_value_ratio", "night_order_ratio", "new_account_ratio"]):
            with cols2[i]:
                fig = px.line(
                    trend_df, x="period", y=metric,
                    title=metric_labels[metric],
                    markers=True
                )
                st.plotly_chart(fig, use_container_width=True)

    st.markdown("#### 规则命中趋势")
    rule_trend_df = pattern_tracker.get_rule_trend_data()
    if not rule_trend_df.empty:
        rule_trend_melted = rule_trend_df.melt(
            id_vars=["period"], var_name="rule", value_name="count"
        )

        fig_rule = px.line(
            rule_trend_melted, x="period", y="count", color="rule",
            title="各规则命中数变化趋势",
            markers=True
        )
        st.plotly_chart(fig_rule, use_container_width=True)

    st.markdown("#### 各时段模式对比")
    patterns = pattern_tracker.pattern_history
    if patterns:
        comparison_data = []
        for p in patterns:
            comparison_data.append({
                "时段": f"P{p['period_id']}",
                "订单数": p["total_orders"],
                "用户数": p["unique_users"],
                "均价": p["avg_order_amount"],
                "低价单占比": f"{p['low_value_ratio']:.1%}",
                "深夜单占比": f"{p['night_order_ratio']:.1%}",
                "新账号占比": f"{p['new_account_ratio']:.1%}",
                "TOP规则": ", ".join([r[0] for r in p["top_rules"][:2]]),
            })
        comparison_df = pd.DataFrame(comparison_data)
        st.dataframe(comparison_df, use_container_width=True)

    changes = pattern_tracker.changes
    if changes:
        st.markdown("#### 📊 模式变化检测")
        for change in changes:
            with st.expander(f"{change['date_range']} - 检测到{len(change['changes'])}项变化"):
                for c in change["changes"]:
                    if "change_pct" in c:
                        arrow = "↑" if c["direction"] == "上升" else "↓"
                        st.write(
                            f"{arrow} {c['metric']}: {c['prev_value']} → {c['curr_value']} "
                            f"({c['direction']}{abs(c['change_pct']):.0%})"
                        )
                    else:
                        st.write(f"✨ {c['metric']}: {', '.join(c['details'])}")


def main():
    st.title("🔍 电商刷单检测系统")
    st.markdown("---")

    with st.sidebar:
        st.header("⚙️ 参数配置")

        st.markdown("### 🎉 大促模式")
        is_promotion = st.toggle("启用大促模式", value=False,
                                  help="大促期间放宽评分标准，阈值自动调整")
        promotion_scale = st.slider("大促放宽系数", 0.50, 0.95, 0.75, 0.05,
                                     help="数值越小越宽松，如0.75表示原始评分*0.75")

        st.markdown("### 📉 图采样配置")
        use_sampling = st.toggle("启用图采样", value=True,
                                  help="大数据量下启用采样降低内存占用")
        max_nodes = st.slider("采样触发阈值", 500, 10000, 5000, 100,
                               help="用户数超过此值时启动采样")
        sampling_ratio = st.slider("采样比例", 0.10, 0.80, 0.30, 0.05,
                                    help="保留的用户比例")

        st.markdown("### 数据生成参数")
        n_normal = st.slider("正常用户数", 50, 500, 200, 10)
        n_fraud = st.slider("刷单用户数", 5, 100, 40, 5)
        orders_normal = st.slider("正常用户平均订单数", 1, 10, 3)
        orders_fraud = st.slider("刷单用户平均订单数", 5, 30, 12)

        st.markdown("### 模型参数")
        contamination = st.slider("Isolation Forest污染率", 0.05, 0.30, 0.15, 0.01)

        if st.button("🔄 重新生成数据并分析", use_container_width=True):
            st.cache_resource.clear()

    results = generate_and_analyze(
        n_normal, n_fraud, orders_normal, orders_fraud,
        use_sampling, max_nodes, sampling_ratio,
        is_promotion, promotion_scale, contamination
    )
    scored_df = results["scored_df"]
    summary = results["summary"]
    sampling_stats = results.get("sampling_stats", {})

    tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8, tab9, tab10, tab11 = st.tabs([
        "📊 系统概览", "⚖️ 阈值对比", "📈 风险分布", "📋 风险排行",
        "🔍 用户详情", "🕸️ 关联图", "🤖 ML分析", "📏 规则分析",
        "👥 团伙识别", "📝 申诉处理", "📈 模式演化"
    ])

    with tab1:
        render_overview(summary, sampling_stats)
        st.markdown("---")
        render_order_analysis(results, scored_df)

    with tab2:
        render_threshold_comparison(summary)

    with tab3:
        render_risk_distribution(scored_df)

    with tab4:
        filtered = render_score_table(scored_df)

    with tab5:
        render_user_detail(scored_df, results)

    with tab6:
        render_graph_analysis(results, scored_df)

    with tab7:
        render_ml_analysis(results, scored_df)
        st.markdown("---")
        render_model_performance(results, scored_df)

    with tab8:
        render_rule_analysis(results, scored_df)

    with tab9:
        render_gang_detection(results, scored_df)

    with tab10:
        render_appeal_handling(results)

    with tab11:
        render_pattern_evolution(results)

    st.sidebar.markdown("---")
    st.sidebar.markdown("### 系统信息")
    st.sidebar.write(f"总用户: {summary['total_users']}")
    st.sidebar.write(f"总订单: {len(results['data']['orders'])}")
    st.sidebar.write(f"团伙数: {len(results.get('gang_summary', []))}")
    st.sidebar.write(f"申诉数: {len(getattr(results['appeal_handler'], 'appeals', []))}")
    st.sidebar.write(f"规则数: 10")
    if is_promotion:
        st.sidebar.success(f"🎉 大促模式已启用（系数: {promotion_scale}）")
    if sampling_stats.get("sampled", False):
        st.sidebar.info(f"📉 图采样已启用（{sampling_stats['sampled_users']}/{sampling_stats['original_users']}）")


if __name__ == "__main__":
    main()
