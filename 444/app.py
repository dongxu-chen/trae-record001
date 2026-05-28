import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import streamlit as st
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime

from engine.detector import FakeFollowerDetector
from engine.network import NetworkAnalyzer
from engine.features import FEATURE_NAMES
from api.social_api import SocialMediaAPI
from models.data_models import FollowerRiskLevel
from utils.helpers import (
    generate_mock_followers,
    get_cleaning_recommendations,
    save_analysis_history,
    get_trend_data,
    format_utc_iso,
    get_utc_now,
    parse_utc_datetime,
)

st.set_page_config(
    page_title="虚假粉丝检测工具",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded",
)

RISK_COLORS = {
    FollowerRiskLevel.GENUINE.value: "#2ecc71",
    FollowerRiskLevel.SUSPICIOUS.value: "#f39c12",
    FollowerRiskLevel.LIKELY_FAKE.value: "#e74c3c",
    FollowerRiskLevel.FAKE.value: "#8e44ad",
}

RISK_LABELS = {
    FollowerRiskLevel.GENUINE.value: "真实用户",
    FollowerRiskLevel.SUSPICIOUS.value: "可疑",
    FollowerRiskLevel.LIKELY_FAKE.value: "疑似虚假",
    FollowerRiskLevel.FAKE.value: "虚假",
}


def init_session_state():
    if "detector" not in st.session_state:
        st.session_state.detector = FakeFollowerDetector()
    if "network_analyzer" not in st.session_state:
        st.session_state.network_analyzer = NetworkAnalyzer()
    if "analysis_results" not in st.session_state:
        st.session_state.analysis_results = None
    if "analysis_summary" not in st.session_state:
        st.session_state.analysis_summary = None
    if "followers_data" not in st.session_state:
        st.session_state.followers_data = None
    if "target_username" not in st.session_state:
        st.session_state.target_username = ""
    if "review_status" not in st.session_state:
        st.session_state.review_status = {}
    if "user_notes" not in st.session_state:
        st.session_state.user_notes = {}
    if "bought_analysis" not in st.session_state:
        st.session_state.bought_analysis = None
    if "interaction_analysis" not in st.session_state:
        st.session_state.interaction_analysis = None
    if "fake_groups" not in st.session_state:
        st.session_state.fake_groups = None


def sidebar_config():
    with st.sidebar:
        st.title("🔍 虚假粉丝检测工具")
        st.markdown("---")

        st.subheader("📡 数据源配置")
        data_source = st.radio(
            "选择数据来源",
            ["模拟数据（演示）", "Twitter API", "上传CSV文件"],
            index=0,
        )

        api_config = {}
        if data_source == "Twitter API":
            with st.expander("Twitter API 配置", expanded=True):
                api_config["bearer_token"] = st.text_input("Bearer Token", type="password")
                api_config["api_key"] = st.text_input("API Key", type="password")
                api_config["api_secret"] = st.text_input("API Secret", type="password")
                api_config["access_token"] = st.text_input("Access Token", type="password")
                api_config["access_token_secret"] = st.text_input("Access Token Secret", type="password")

        if data_source == "模拟数据（演示）":
            st.subheader("⚙️ 模拟参数")
            follower_count = st.slider("粉丝数量", 50, 500, 200, step=50)
            fake_ratio = st.slider("虚假粉丝比例", 0.05, 0.60, 0.30, step=0.05)
            target_username = st.text_input("目标用户名", "demo_user")
        elif data_source == "Twitter API":
            target_username = st.text_input("目标用户名", "")
            follower_count = st.slider("最大获取数量", 50, 1000, 200, step=50)
            fake_ratio = 0.3
        else:
            target_username = st.text_input("目标用户名", "csv_user")
            follower_count = 200
            fake_ratio = 0.3

        st.markdown("---")
        st.subheader("🧠 检测模型")
        model_type = st.selectbox("选择检测模型", ["无监督（Isolation Forest）", "有监督（Random Forest）", "启发式规则"])

        st.markdown("---")
        analyze_btn = st.button("🚀 开始分析", use_container_width=True, type="primary")

        return {
            "data_source": data_source,
            "api_config": api_config,
            "follower_count": follower_count,
            "fake_ratio": fake_ratio,
            "target_username": target_username,
            "model_type": model_type,
            "analyze_btn": analyze_btn,
        }


def run_analysis(config):
    detector = st.session_state.detector
    network_analyzer = st.session_state.network_analyzer

    with st.spinner("正在获取数据..."):
        if config["data_source"] == "模拟数据（演示）":
            followers = generate_mock_followers(
                count=config["follower_count"],
                fake_ratio=config["fake_ratio"],
                seed=42,
            )
        elif config["data_source"] == "Twitter API":
            api = SocialMediaAPI(
                platform="twitter",
                bearer_token=config["api_config"].get("bearer_token", ""),
                api_key=config["api_config"].get("api_key", ""),
                api_secret=config["api_config"].get("api_secret", ""),
                access_token=config["api_config"].get("access_token", ""),
                access_token_secret=config["api_config"].get("access_token_secret", ""),
            )
            if not api.authenticate():
                st.error("❌ Twitter API 认证失败，请检查API密钥配置。")
                st.info("💡 您可以使用模拟数据模式进行演示。")
                return
            followers = api.get_followers(config["target_username"], max_count=config["follower_count"])
            if not followers:
                st.error("❌ 未能获取粉丝数据，请检查用户名是否正确。")
                return
        else:
            st.info("📂 请在主面板上传CSV文件。")
            return

    st.session_state.followers_data = followers
    st.session_state.target_username = config["target_username"]

    with st.spinner("正在训练检测模型..."):
        from engine.features import extract_features, feature_vector_to_array

        feature_arrays = np.array([
            feature_vector_to_array(extract_features(f)) for f in followers
        ])

        if config["model_type"] == "无监督（Isolation Forest）":
            detector.train_unsupervised(feature_arrays)
        elif config["model_type"] == "有监督（Random Forest）":
            labels = np.array([
                1 if f.get("user_id", "").startswith("fake_") else 0
                for f in followers
            ])
            if len(np.unique(labels)) < 2:
                st.warning("有监督模型需要正负样本，切换到无监督模型。")
                detector.train_unsupervised(feature_arrays)
            else:
                detector.train_supervised(feature_arrays, labels)
        else:
            detector._is_trained = False

    with st.spinner("正在分析粉丝数据..."):
        results, summary = detector.analyze(followers)

    st.session_state.analysis_results = results
    st.session_state.analysis_summary = summary

    with st.spinner("正在分析购买粉丝模式..."):
        bought_analysis = detector.analyze_bought_followers(followers)
        st.session_state.bought_analysis = bought_analysis

    with st.spinner("正在评估互动质量..."):
        interaction_analysis = detector.analyze_interaction_quality(followers)
        st.session_state.interaction_analysis = interaction_analysis

    with st.spinner("正在增强检测结果..."):
        enhanced_results = detector.enhance_risk_with_advanced_analysis(results, followers)
        st.session_state.analysis_results = enhanced_results

        genuine = sum(1 for r in enhanced_results if r.risk_level == FollowerRiskLevel.GENUINE)
        suspicious = sum(1 for r in enhanced_results if r.risk_level == FollowerRiskLevel.SUSPICIOUS)
        likely_fake = sum(1 for r in enhanced_results if r.risk_level == FollowerRiskLevel.LIKELY_FAKE)
        fake = sum(1 for r in enhanced_results if r.risk_level == FollowerRiskLevel.FAKE)
        total = len(enhanced_results)
        fake_ratio = (likely_fake + fake) / max(total, 1)
        avg_fake_prob = np.mean([r.fake_probability for r in enhanced_results])
        risk_factor_counts = {}
        for r in enhanced_results:
            for rf in r.risk_factors:
                risk_factor_counts[rf] = risk_factor_counts.get(rf, 0) + 1

        summary.genuine_count = genuine
        summary.suspicious_count = suspicious
        summary.likely_fake_count = likely_fake
        summary.fake_count = fake
        summary.fake_ratio = fake_ratio
        summary.avg_fake_probability = float(avg_fake_prob)
        summary.top_risk_factors = dict(sorted(risk_factor_counts.items(), key=lambda x: x[1], reverse=True)[:10])
        st.session_state.analysis_summary = summary

    with st.spinner("正在构建社交网络..."):
        network_analyzer.build_graph(
            config["target_username"],
            followers,
            enhanced_results,
        )
        network_analyzer.add_simulated_interactions(followers, enhanced_results)
        fake_groups = network_analyzer.detect_fake_groups(min_group_size=5)
        st.session_state.fake_groups = fake_groups

    with st.spinner("正在保存分析记录..."):
        summary_dict = {
            "total_followers": summary.total_followers,
            "genuine_count": summary.genuine_count,
            "suspicious_count": summary.suspicious_count,
            "likely_fake_count": summary.likely_fake_count,
            "fake_count": summary.fake_count,
            "fake_ratio": summary.fake_ratio,
            "avg_fake_probability": summary.avg_fake_probability,
        }
        results_dict = [{"user_id": r.user_id, "risk_level": r.risk_level.value, "fake_probability": r.fake_probability} for r in results]
        save_analysis_history(config["target_username"], summary_dict, results_dict)


def render_overview(summary):
    st.subheader("📊 分析概览")

    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        st.metric("总粉丝数", summary.total_followers)
    with col2:
        st.metric("真实用户", summary.genuine_count, delta=f"{summary.genuine_count/summary.total_followers*100:.1f}%")
    with col3:
        st.metric("可疑用户", summary.suspicious_count, delta=f"{summary.suspicious_count/summary.total_followers*100:.1f}%")
    with col4:
        st.metric("疑似虚假", summary.likely_fake_count, delta=f"{summary.likely_fake_count/summary.total_followers*100:.1f}%")
    with col5:
        st.metric("虚假粉丝", summary.fake_count, delta=f"{summary.fake_count/summary.total_followers*100:.1f}%")

    st.markdown("---")

    col_chart1, col_chart2 = st.columns(2)

    with col_chart1:
        labels = [RISK_LABELS[k] for k in summary.risk_distribution.keys()]
        values = list(summary.risk_distribution.values())
        colors = [RISK_COLORS[k] for k in summary.risk_distribution.keys()]

        fig_pie = go.Figure(data=[go.Pie(
            labels=labels,
            values=values,
            marker=dict(colors=colors),
            textinfo="label+percent",
            hole=0.4,
        )])
        fig_pie.update_layout(
            title="粉丝风险分布",
            height=400,
            showlegend=True,
        )
        st.plotly_chart(fig_pie, use_container_width=True)

    with col_chart2:
        fig_gauge = go.Figure(go.Indicator(
            mode="gauge+number+delta",
            value=summary.fake_ratio * 100,
            domain={"x": [0, 1], "y": [0, 1]},
            title={"text": "虚假粉丝比例 (%)"},
            delta={"reference": 15},
            gauge={
                "axis": {"range": [None, 100]},
                "bar": {"color": "#e74c3c" if summary.fake_ratio > 0.3 else "#f39c12" if summary.fake_ratio > 0.15 else "#2ecc71"},
                "steps": [
                    {"range": [0, 15], "color": "#2ecc7133"},
                    {"range": [15, 30], "color": "#f39c1233"},
                    {"range": [30, 60], "color": "#e74c3c33"},
                    {"range": [60, 100], "color": "#8e44ad33"},
                ],
                "threshold": {
                    "line": {"color": "red", "width": 4},
                    "thickness": 0.75,
                    "value": 50,
                },
            },
        ))
        fig_gauge.update_layout(height=400)
        st.plotly_chart(fig_gauge, use_container_width=True)


def render_risk_factors(summary):
    st.subheader("⚠️ 风险因素分析")

    if not summary.top_risk_factors:
        st.info("未发现明显风险因素。")
        return

    factor_labels = {
        "low_engagement": "互动率极低",
        "high_following_ratio": "关注/粉丝比异常",
        "new_account": "新注册账号",
        "no_profile_image": "无头像",
        "high_repost_ratio": "转发比例过高",
        "duplicate_content": "重复内容",
        "classic_bot_pattern": "典型机器人模式",
        "low_content_diversity": "内容多样性低",
        "empty_bio": "空简介",
    }

    factors = summary.top_risk_factors
    labels = [factor_labels.get(k, k) for k in factors.keys()]
    values = list(factors.values())

    fig = go.Figure(go.Bar(
        x=values,
        y=labels,
        orientation="h",
        marker_color=["#e74c3c" if v > summary.total_followers * 0.2 else "#f39c12" if v > summary.total_followers * 0.1 else "#3498db" for v in values],
    ))
    fig.update_layout(
        title="风险因素排名",
        xaxis_title="受影响账号数",
        height=max(300, len(labels) * 40),
        yaxis=dict(autorange="reversed"),
    )
    st.plotly_chart(fig, use_container_width=True)


def render_follower_details(results):
    st.subheader("📋 粉丝标注与人工审核")

    risk_filter = st.multiselect(
        "筛选风险等级",
        options=["genuine", "suspicious", "likely_fake", "fake"],
        default=["likely_fake", "fake"],
        format_func=lambda x: RISK_LABELS.get(x, x),
    )

    review_filter = st.multiselect(
        "筛选审核状态",
        options=["pending", "approved_keep", "approved_remove", "note_added"],
        default=["pending"],
        format_func=lambda x: {
            "pending": "待审核",
            "approved_keep": "审核通过（保留）",
            "approved_remove": "审核通过（移除）",
            "note_added": "已添加备注",
        }.get(x, x),
    )

    filtered = []
    for r in results:
        if r.risk_level.value not in risk_filter:
            continue
        review_status = st.session_state.review_status.get(r.user_id, "pending")
        if review_status not in review_filter:
            continue
        filtered.append(r)

    st.info(f"📌 当前筛选结果：{len(filtered)} 个账号，所有操作仅为标注，不会自动删除。")

    rows = []
    for r in filtered:
        review_status = st.session_state.review_status.get(r.user_id, "pending")
        status_label = {
            "pending": "🔴 待审核",
            "approved_keep": "🟢 保留",
            "approved_remove": "🔴 移除",
            "note_added": "🟡 有备注",
        }.get(review_status, "🔴 待审核")
        note = st.session_state.user_notes.get(r.user_id, "")
        rows.append({
            "审核状态": status_label,
            "用户ID": r.user_id,
            "用户名": r.username,
            "风险等级": RISK_LABELS.get(r.risk_level.value, r.risk_level.value),
            "虚假概率": f"{r.fake_probability:.2%}",
            "风险因素": ", ".join(r.risk_factors) if r.risk_factors else "无",
            "系统建议": r.recommendation,
            "审核备注": note,
        })

    if rows:
        df = pd.DataFrame(rows)
        st.dataframe(df, use_container_width=True, height=300)

        st.subheader("✍️ 单个账号人工审核")
        selected_user_id = st.selectbox(
            "选择账号进行审核",
            options=[r.user_id for r in filtered],
            format_func=lambda x: next((f"{r.username} ({x})" for r in filtered if r.user_id == x), x),
        )

        if selected_user_id:
            selected_result = next((r for r in filtered if r.user_id == selected_user_id), None)
            if selected_result:
                col1, col2 = st.columns([1, 1])
                with col1:
                    st.markdown(f"**用户名**: {selected_result.username}")
                    st.markdown(f"**用户ID**: {selected_result.user_id}")
                    st.markdown(f"**风险等级**: {RISK_LABELS.get(selected_result.risk_level.value, selected_result.risk_level.value)}")
                    st.markdown(f"**虚假概率**: {selected_result.fake_probability:.2%}")
                    st.markdown(f"**风险因素**: {', '.join(selected_result.risk_factors) if selected_result.risk_factors else '无'}")
                    st.markdown(f"**系统建议**: {selected_result.recommendation}")

                with col2:
                    current_status = st.session_state.review_status.get(selected_user_id, "pending")
                    new_status = st.selectbox(
                        "设置审核状态",
                        options=["pending", "approved_keep", "approved_remove"],
                        index=["pending", "approved_keep", "approved_remove"].index(current_status),
                        format_func=lambda x: {
                            "pending": "🔴 待审核",
                            "approved_keep": "🟢 确认真实（保留）",
                            "approved_remove": "🔴 确认虚假（标记移除）",
                        }.get(x, x),
                    )
                    if st.button("✅ 保存审核状态"):
                        st.session_state.review_status[selected_user_id] = new_status
                        if new_status != "pending":
                            st.success(f"已将 {selected_result.username} 标注为：{new_status}")
                            st.rerun()

                    current_note = st.session_state.user_notes.get(selected_user_id, "")
                    new_note = st.text_area("审核备注（可选）", value=current_note, height=100)
                    if st.button("💾 保存备注"):
                        st.session_state.user_notes[selected_user_id] = new_note
                        if new_note and new_status == "pending":
                            st.session_state.review_status[selected_user_id] = "note_added"
                        st.success("备注已保存")
                        st.rerun()

        st.subheader("📊 批量标注与导出")
        col_b1, col_b2, col_b3 = st.columns(3)
        with col_b1:
            if st.button(f"📌 将当前筛选的 {len(filtered)} 个账号标记为「待进一步审核」"):
                for r in filtered:
                    st.session_state.review_status[r.user_id] = "pending"
                st.success("已批量标注为待审核")
                st.rerun()
        with col_b2:
            if st.button(f"📌 将「虚假」级账号批量标记为「建议移除」"):
                count = 0
                for r in results:
                    if r.risk_level == FollowerRiskLevel.FAKE:
                        st.session_state.review_status[r.user_id] = "approved_remove"
                        count += 1
                st.success(f"已将 {count} 个「虚假」级账号标记为建议移除")
                st.rerun()
        with col_b3:
            if st.button("🔄 重置所有审核状态"):
                st.session_state.review_status = {}
                st.session_state.user_notes = {}
                st.success("已重置所有审核状态")
                st.rerun()

        export_rows = []
        for r in results:
            review_status = st.session_state.review_status.get(r.user_id, "pending")
            status_label = {
                "pending": "待审核",
                "approved_keep": "保留",
                "approved_remove": "移除",
                "note_added": "有备注",
            }.get(review_status, "待审核")
            export_rows.append({
                "用户ID": r.user_id,
                "用户名": r.username,
                "风险等级": RISK_LABELS.get(r.risk_level.value, r.risk_level.value),
                "虚假概率": f"{r.fake_probability:.2%}",
                "风险因素": ", ".join(r.risk_factors) if r.risk_factors else "无",
                "审核状态": status_label,
                "审核备注": st.session_state.user_notes.get(r.user_id, ""),
                "系统建议": r.recommendation,
            })
        export_df = pd.DataFrame(export_rows)
        csv = export_df.to_csv(index=False).encode("utf-8-sig")
        st.download_button(
            "📥 导出标注结果（含审核状态）",
            data=csv,
            file_name=f"fake_follower_review_{format_utc_iso(get_utc_now()).replace(':', '-')}.csv",
            mime="text/csv",
            help="导出CSV包含所有粉丝的风险标注和人工审核状态，可用于平台内批量管理。",
        )

        pending_count = sum(1 for r in results if st.session_state.review_status.get(r.user_id, "pending") == "pending")
        keep_count = sum(1 for r in results if st.session_state.review_status.get(r.user_id, "pending") == "approved_keep")
        remove_count = sum(1 for r in results if st.session_state.review_status.get(r.user_id, "pending") == "approved_remove")
        note_count = sum(1 for r in results if st.session_state.review_status.get(r.user_id, "pending") == "note_added")

        col_s1, col_s2, col_s3, col_s4 = st.columns(4)
        with col_s1:
            st.metric("待审核", pending_count)
        with col_s2:
            st.metric("已标注保留", keep_count)
        with col_s3:
            st.metric("已标注移除", remove_count)
        with col_s4:
            st.metric("已添加备注", note_count)

        st.warning("⚠️ 所有标注仅用于参考，不会自动删除任何粉丝。请在社交媒体平台内人工复核后，使用平台官方工具进行处理。")
    else:
        st.info("没有符合筛选条件的粉丝。")


def render_network_graph():
    st.subheader("🌐 社交网络 - 聚集系数分析")

    network_analyzer = st.session_state.network_analyzer
    results = st.session_state.analysis_results

    stats = network_analyzer.get_network_stats()
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("节点数", stats["nodes"])
    with col2:
        st.metric("边数", stats["edges"])
    with col3:
        st.metric("平均聚集系数", f"{stats['avg_clustering']:.4f}")
    with col4:
        st.metric("虚假账号聚集系数", f"{stats['fake_avg_clustering']:.4f}")

    col5, col6 = st.columns(2)
    with col5:
        st.metric("真实账号聚集系数", f"{stats['genuine_avg_clustering']:.4f}")
    with col6:
        st.metric("虚假/真实账号比", f"{stats['fake_genuine_ratio']:.2f}")

    bucket_stats = network_analyzer.get_clustering_bucket_stats()
    bucket_rows = []
    for bucket, s in bucket_stats.items():
        if s["count"] > 0:
            bucket_rows.append({
                "风险等级": RISK_LABELS.get(bucket, bucket),
                "账号数": s["count"],
                "平均聚集系数": f"{s['avg']:.4f}",
                "中位数": f"{s['median']:.4f}",
                "75分位数": f"{s['p75']:.4f}",
            })
    if bucket_rows:
        st.markdown("**聚集系数按风险等级分布**")
        st.dataframe(pd.DataFrame(bucket_rows), use_container_width=True)

    clustering = network_analyzer.compute_clustering_coefficients()
    fig = go.Figure()
    for risk_level in ["genuine", "suspicious", "likely_fake", "fake"]:
        vals = []
        for r in results:
            if r.risk_level.value == risk_level and r.user_id in clustering:
                vals.append(clustering[r.user_id])
        if vals:
            fig.add_trace(go.Histogram(
                x=vals,
                name=RISK_LABELS.get(risk_level, risk_level),
                opacity=0.6,
                marker_color=RISK_COLORS.get(risk_level, "#888"),
                nbinsx=20,
            ))
    fig.update_layout(
        title="各风险等级聚集系数分布对比",
        xaxis_title="聚集系数 (Clustering Coefficient)",
        yaxis_title="数量",
        barmode="overlay",
        height=400,
    )
    st.plotly_chart(fig, use_container_width=True)

    st.info("💡 **聚集系数解读**：虚假粉丝通常形成更紧密的集群（聚集系数更高），因为它们之间有大量的相互关注，形成'刷粉圈'。真实用户的聚集系数分布更分散。")

    st.subheader("📊 粉丝网络可视化（简化版）")
    pos = network_analyzer.get_node_positions()
    if not pos:
        st.info("网络图为空。")
        return

    node_x = []
    node_y = []
    node_color = []
    node_size = []
    node_text = []
    for node, (x, y) in pos.items():
        node_x.append(x)
        node_y.append(y)
        node_data = network_analyzer.graph.nodes[node]
        risk = node_data.get("risk", "genuine")
        node_color.append(RISK_COLORS.get(risk, "#95a5a6"))
        node_type = node_data.get("type", "follower")
        clus = clustering.get(node, 0.0)
        node_size.append(20 if node_type == "target" else 5 + clus * 15)
        username = node_data.get("username", node)
        node_text.append(f"{username} ({RISK_LABELS.get(risk, risk)})<br>聚集系数: {clus:.3f}")

    edge_x = []
    edge_y = []
    for u, v in network_analyzer.graph.edges():
        if u in pos and v in pos:
            x0, y0 = pos[u]
            x1, y1 = pos[v]
            edge_x.extend([x0, x1, None])
            edge_y.extend([y0, y1, None])

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=edge_x, y=edge_y,
        line=dict(width=0.3, color="#888"),
        hoverinfo="none",
        mode="lines",
    ))
    fig.add_trace(go.Scatter(
        x=node_x, y=node_y,
        mode="markers",
        hoverinfo="text",
        text=node_text,
        marker=dict(
            showscale=False,
            color=node_color,
            size=node_size,
            line=dict(width=1, color="#fff"),
        ),
    ))
    fig.update_layout(
        title="粉丝网络关系图（节点大小表示聚集系数）",
        showlegend=True,
        height=550,
        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        plot_bgcolor="white",
    )
    for risk_val, color in RISK_COLORS.items():
        fig.add_trace(go.Scatter(
            x=[None],
            y=[None],
            mode="markers",
            name=RISK_LABELS.get(risk_val, risk_val),
            marker=dict(color=color, size=10),
            showlegend=True,
        ))
    st.plotly_chart(fig, use_container_width=True)


def render_feature_distribution():
    st.subheader("📈 特征分布分析")

    followers = st.session_state.followers_data
    results = st.session_state.analysis_results

    from engine.features import extract_features, feature_vector_to_array

    genuine_features = []
    fake_features = []
    for f, r in zip(followers, results):
        fv = extract_features(f)
        arr = feature_vector_to_array(fv)
        if r.risk_level in (FollowerRiskLevel.FAKE, FollowerRiskLevel.LIKELY_FAKE):
            fake_features.append(arr)
        else:
            genuine_features.append(arr)

    selected_feature = st.selectbox(
        "选择特征",
        options=FEATURE_NAMES,
        index=FEATURE_NAMES.index("engagement_rate"),
    )

    feat_idx = FEATURE_NAMES.index(selected_feature)
    genuine_vals = [g[feat_idx] for g in genuine_features if len(g) > feat_idx]
    fake_vals = [f[feat_idx] for f in fake_features if len(f) > feat_idx]

    fig = go.Figure()
    fig.add_trace(go.Histogram(
        x=genuine_vals,
        name="真实用户",
        opacity=0.7,
        marker_color="#2ecc71",
        nbinsx=30,
    ))
    fig.add_trace(go.Histogram(
        x=fake_vals,
        name="虚假用户",
        opacity=0.7,
        marker_color="#e74c3c",
        nbinsx=30,
    ))
    fig.update_layout(
        title=f"特征分布: {selected_feature}",
        barmode="overlay",
        xaxis_title=selected_feature,
        yaxis_title="数量",
        height=400,
    )
    st.plotly_chart(fig, use_container_width=True)


def render_trend():
    st.subheader("📉 历史趋势变化")

    trend_df = get_trend_data()
    if trend_df.empty:
        st.info("暂无历史分析数据。完成首次分析后将显示趋势图。")
        return

    col1, col2 = st.columns(2)

    with col1:
        fig_ratio = go.Figure()
        fig_ratio.add_trace(go.Scatter(
            x=trend_df["timestamp"],
            y=trend_df["fake_ratio"] * 100,
            mode="lines+markers",
            name="虚假粉丝比例",
            line=dict(color="#e74c3c", width=2),
            fill="tozeroy",
            fillcolor="rgba(231,76,60,0.1)",
        ))
        fig_ratio.update_layout(
            title="虚假粉丝比例趋势",
            xaxis_title="时间",
            yaxis_title="虚假比例 (%)",
            height=350,
        )
        st.plotly_chart(fig_ratio, use_container_width=True)

    with col2:
        fig_dist = go.Figure()
        fig_dist.add_trace(go.Scatter(x=trend_df["timestamp"], y=trend_df["genuine_count"], mode="lines+markers", name="真实用户", line=dict(color="#2ecc71")))
        fig_dist.add_trace(go.Scatter(x=trend_df["timestamp"], y=trend_df["suspicious_count"], mode="lines+markers", name="可疑用户", line=dict(color="#f39c12")))
        fig_dist.add_trace(go.Scatter(x=trend_df["timestamp"], y=trend_df["likely_fake_count"], mode="lines+markers", name="疑似虚假", line=dict(color="#e74c3c")))
        fig_dist.add_trace(go.Scatter(x=trend_df["timestamp"], y=trend_df["fake_count"], mode="lines+markers", name="虚假粉丝", line=dict(color="#8e44ad")))
        fig_dist.update_layout(
            title="各类粉丝数量趋势",
            xaxis_title="时间",
            yaxis_title="数量",
            height=350,
        )
        st.plotly_chart(fig_dist, use_container_width=True)


def render_recommendations(summary):
    st.subheader("💡 审核建议")

    risk_factor_counts = summary.top_risk_factors
    recommendations = get_cleaning_recommendations(summary.fake_ratio, risk_factor_counts)

    for i, rec in enumerate(recommendations):
        if "严重警告" in rec or "立即" in rec:
            icon = "🔴"
        elif "警告" in rec or "优先" in rec or "高风险" in rec:
            icon = "🟠"
        elif "注意" in rec or "观察" in rec or "定期" in rec:
            icon = "🟡"
        else:
            icon = "🟢"
        st.markdown(f"{icon} {rec}")


def render_bought_follower_detection():
    st.subheader("💰 购买粉丝检测")

    analysis = st.session_state.bought_analysis
    if not analysis:
        st.info("暂无购买粉丝分析数据")
        return

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        score = analysis.get("bought_score", 0)
        if score > 0.7:
            status_color = "#e74c3c"
            status_text = "高风险"
        elif score > 0.4:
            status_color = "#f39c12"
            status_text = "中风险"
        else:
            status_color = "#2ecc71"
            status_text = "低风险"
        st.metric("购买粉丝评分", f"{score:.1%}")
        st.markdown(f"<p style='color: {status_color}; font-weight: bold;'>{status_text}</p>", unsafe_allow_html=True)

    with col2:
        st.metric("新账号比例", f"{analysis.get('new_account_ratio', 0):.1%}")

    with col3:
        avg_age = analysis.get('avg_account_age_days', 0)
        st.metric("平均账号年龄", f"{avg_age:.0f} 天")

    with col4:
        has_burst = analysis.get('has_burst_pattern', False)
        st.metric("注册爆发模式", "是" if has_burst else "否")

    st.markdown("---")

    if analysis.get("bursts"):
        st.markdown("#### 🚨 检测到的注册爆发期")
        bursts = analysis["bursts"]
        for i, burst in enumerate(bursts, 1):
            with st.expander(f"爆发期 {i} - {burst['account_count']} 个账号"):
                col_a, col_b, col_c = st.columns(3)
                with col_a:
                    st.info(f"**开始时间**: {burst['start_date'][:10]}")
                with col_b:
                    st.info(f"**结束时间**: {burst['end_date'][:10]}")
                with col_c:
                    st.warning(f"**超出预期**: {burst['over_expected_ratio']:.1f}x")

    followers = st.session_state.followers_data
    if followers:
        st.markdown("#### 📊 注册时间分布")
        reg_dates = []
        for f in followers:
            dt = parse_utc_datetime(f.get("registration_date"))
            if dt:
                reg_dates.append(dt)

        if reg_dates:
            import pandas as pd
            df_dates = pd.DataFrame({"registration_date": reg_dates})
            df_dates["date"] = df_dates["registration_date"].dt.to_period("W")
            date_counts = df_dates.groupby("date").size().reset_index(name="count")
            date_counts["date_str"] = date_counts["date"].astype(str)

            import plotly.graph_objects as go
            fig = go.Figure()
            fig.add_trace(go.Bar(x=date_counts["date_str"], y=date_counts["count"], name="注册数量", marker_color="#3498db"))
            fig.add_trace(go.Scatter(x=date_counts["date_str"], y=date_counts["count"], mode="lines", name="趋势", line=dict(color="#e74c3c")))
            fig.update_layout(title="按周统计的粉丝注册分布", xaxis_title="注册时间（周）", yaxis_title="账号数量", height=400)
            st.plotly_chart(fig, use_container_width=True)

    st.markdown("---")
    st.markdown("#### ℹ️ 购买粉丝判定说明")
    st.markdown("""
    - **注册爆发**: 短时间内大量账号同时关注，是购买粉丝的典型特征
    - **新账号比例**: 大量注册时间不足30天的账号，风险较高
    - **账号年龄**: 平均年龄小于60天，且集中在特定时间段，高度可疑
    """)


def render_interaction_quality():
    st.subheader("💬 互动质量评估")

    analysis = st.session_state.interaction_analysis
    if not analysis:
        st.info("暂无互动质量分析数据")
        return

    col1, col2, col3 = st.columns(3)
    with col1:
        avg_score = analysis.get("avg_quality_score", 0)
        st.metric("平均互动质量分", f"{avg_score:.1%}")
        if avg_score < 0.4:
            st.markdown("<p style='color: #e74c3c; font-weight: bold;'>整体质量低</p>", unsafe_allow_html=True)
        elif avg_score < 0.6:
            st.markdown("<p style='color: #f39c12; font-weight: bold;'>质量一般</p>", unsafe_allow_html=True)
        else:
            st.markdown("<p style='color: #2ecc71; font-weight: bold;'>质量良好</p>", unsafe_allow_html=True)

    with col2:
        st.metric("低质量比例", f"{analysis.get('low_quality_ratio', 0):.1%}")

    with col3:
        st.metric("高质量比例", f"{analysis.get('high_quality_ratio', 0):.1%}")

    st.markdown("---")

    st.markdown("#### 📊 互动质量分布")
    import plotly.graph_objects as go

    buckets = {
        "极低 (<20%)": 0,
        "低 (20-40%)": 0,
        "中 (40-60%)": 0,
        "高 (60-80%)": 0,
        "极高 (>80%)": 0,
    }

    for metrics in analysis["follower_scores"].values():
        score = metrics["quality_score"]
        if score < 0.2:
            buckets["极低 (<20%)"] += 1
        elif score < 0.4:
            buckets["低 (20-40%)"] += 1
        elif score < 0.6:
            buckets["中 (40-60%)"] += 1
        elif score < 0.8:
            buckets["高 (60-80%)"] += 1
        else:
            buckets["极高 (>80%)"] += 1

    colors = ["#e74c3c", "#e67e22", "#f1c40f", "#2ecc71", "#27ae60"]
    fig = go.Figure(go.Bar(x=list(buckets.keys()), y=list(buckets.values()), marker_color=colors))
    fig.update_layout(title="互动质量分级分布", xaxis_title="质量等级", yaxis_title="账号数量", height=350)
    st.plotly_chart(fig, use_container_width=True)

    st.markdown("---")

    st.markdown("#### 🧩 质量构成分析")
    all_scores = list(analysis["follower_scores"].values())
    if all_scores:
        col_a, col_b, col_c, col_d = st.columns(4)
        with col_a:
            avg_eng = float(np.mean([s.get("engagement_component", 0) for s in all_scores]))
            st.metric("互动率成分", f"{avg_eng:.1%}")
        with col_b:
            avg_orig = float(np.mean([s.get("content_originality", 0) for s in all_scores]))
            st.metric("内容原创性", f"{avg_orig:.1%}")
        with col_c:
            avg_natural = float(np.mean([s.get("interaction_naturalness", 0) for s in all_scores]))
            st.metric("互动自然度", f"{avg_natural:.1%}")
        with col_d:
            avg_pattern = float(np.mean([s.get("activity_pattern", 0) for s in all_scores]))
            st.metric("活动模式", f"{avg_pattern:.1%}")

    st.markdown("---")

    st.markdown("#### 🔍 低质量账号案例")
    low_quality_users = []
    results = st.session_state.analysis_results
    follower_map = {f.get("user_id"): f for f in st.session_state.followers_data or []}

    for user_id, metrics in analysis["follower_scores"].items():
        if metrics["quality_score"] < 0.3 and len(low_quality_users) < 10:
            follower = follower_map.get(user_id, {})
            result = next((r for r in results if r.user_id == user_id), None)
            low_quality_users.append({
                "user_id": user_id,
                "username": follower.get("username", ""),
                "quality_score": metrics["quality_score"],
                "flags": metrics.get("flags", []),
                "fake_prob": result.fake_probability if result else 0,
            })

    if low_quality_users:
        import pandas as pd
        df_low = pd.DataFrame(low_quality_users)
        df_low["quality_score"] = df_low["quality_score"].apply(lambda x: f"{x:.1%}")
        df_low["fake_prob"] = df_low["fake_prob"].apply(lambda x: f"{x:.1%}")
        df_low["flags"] = df_low["flags"].apply(lambda x: ", ".join(x) if x else "-")
        df_low.columns = ["用户ID", "用户名", "质量分", "问题标记", "虚假概率"]
        st.dataframe(df_low, use_container_width=True)

    st.markdown("---")
    st.markdown("#### ℹ️ 互动质量说明")
    st.markdown("""
    - **互动率成分**: 真实的点赞、评论、转发率（机器人往往互动率异常低或异常高）
    - **内容原创性**: 原创内容比例（机器人多为转发或重复内容）
    - **互动自然度**: 是否有正常的@提及、话题标签使用
    - **活动模式**: 发布频率和时间分布是否自然（机器人常有规律性爆发）
    """)


def render_fake_groups():
    st.subheader("👥 虚假粉丝群组检测")

    groups = st.session_state.fake_groups
    network_analyzer = st.session_state.network_analyzer

    if not groups:
        st.info("未检测到明显的虚假粉丝群组")
        return

    group_metrics = network_analyzer.get_group_metrics(groups)

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("检测到群组数", group_metrics["total_groups"])
    with col2:
        st.metric("最大群组规模", group_metrics["largest_group_size"])
    with col3:
        st.metric("平均群组大小", f"{group_metrics['avg_group_size']:.0f}")
    with col4:
        st.metric("群组内账号占比", f"{group_metrics['grouped_ratio']:.1%}")

    st.markdown("---")

    st.markdown("#### 📋 检测到的虚假群组")
    results = st.session_state.analysis_results
    follower_map = {f.get("user_id"): f for f in st.session_state.followers_data or []}
    result_map = {r.user_id: r for r in results}

    for i, group in enumerate(groups, 1):
        with st.expander(f"群组 {i} - {group['size']} 个账号 (核心等级: {group['core_level']})"):
            col_a, col_b, col_c = st.columns(3)
            with col_a:
                st.info(f"**群组密度**: {group['density']:.2f}")
            with col_b:
                st.info(f"**平均连接数**: {group['avg_degree']:.1f}")
            with col_c:
                st.warning(f"**虚假比例**: {group['fake_ratio']:.0%}")

            group_users = []
            for node_id in group["nodes"][:20]:
                follower = follower_map.get(node_id, {})
                result = result_map.get(node_id)
                group_users.append({
                    "username": follower.get("username", ""),
                    "user_id": node_id,
                    "fake_prob": result.fake_probability if result else 0,
                    "risk_level": result.risk_level.value if result else "unknown",
                })

            import pandas as pd
            df_group = pd.DataFrame(group_users)
            df_group["fake_prob"] = df_group["fake_prob"].apply(lambda x: f"{x:.1%}")
            df_group.columns = ["用户名", "用户ID", "虚假概率", "风险等级"]
            st.dataframe(df_group, use_container_width=True)

            if len(group["nodes"]) > 20:
                st.caption(f"... 还有 {len(group['nodes']) - 20} 个账号未显示")

    st.markdown("---")
    st.markdown("#### ℹ️ 虚假群组说明")
    st.markdown("""
    - **核心等级**: 使用k-core算法计算，等级越高表示群组连接越紧密
    - **群组密度**: 群组内实际连接数与最大可能连接数的比值（0-1）
    - **识别原理**: 购买的粉丝往往会相互关注形成密集子图
    - **处理建议**: 群组内账号建议批量标记审核，它们很可能来自同一个粉丝工厂
    """)


def render_csv_upload():
    st.subheader("📂 上传CSV文件")
    st.markdown("""
    CSV文件应包含以下列（列名不区分大小写）：
    - `user_id`, `username`, `followers_count`, `following_count`, `posts_count`
    - 可选列：`bio`, `registration_date`, `is_verified`, `has_profile_image`, `engagement_rate`
    - 注册时间格式：ISO格式（如 `2024-01-15T10:30:00Z` 或 `2024-01-15`）
    """)

    uploaded_file = st.file_uploader("选择CSV文件", type=["csv"])
    if uploaded_file is not None:
        try:
            df = pd.read_csv(uploaded_file)
            st.dataframe(df.head(), use_container_width=True)

            if st.button("处理上传数据"):
                followers = []
                for _, row in df.iterrows():
                    reg_date_raw = str(row.get("registration_date", row.get("Registration_Date", ""))) or None
                    reg_date_parsed = parse_utc_datetime(reg_date_raw)
                    reg_date_formatted = format_utc_iso(reg_date_parsed)

                    follower = {
                        "user_id": str(row.get("user_id", row.get("User_ID", f"csv_{_}"))),
                        "username": str(row.get("username", row.get("Username", f"user_{_}"))),
                        "display_name": str(row.get("display_name", row.get("Display_Name", ""))),
                        "bio": str(row.get("bio", row.get("Bio", ""))),
                        "avatar_url": "",
                        "registration_date": reg_date_formatted,
                        "followers_count": int(row.get("followers_count", row.get("Followers_Count", 0))),
                        "following_count": int(row.get("following_count", row.get("Following_Count", 0))),
                        "posts_count": int(row.get("posts_count", row.get("Posts_Count", 0))),
                        "likes_count": int(row.get("likes_count", row.get("Likes_Count", 0))),
                        "is_verified": bool(row.get("is_verified", row.get("Is_Verified", False))),
                        "is_protected": bool(row.get("is_protected", row.get("Is_Protected", False))),
                        "has_profile_image": bool(row.get("has_profile_image", row.get("Has_Profile_Image", True))),
                        "engagement_rate": float(row.get("engagement_rate", row.get("Engagement_Rate", 0.05))),
                        "bio_length": len(str(row.get("bio", row.get("Bio", "")))),
                        "repost_ratio": float(row.get("repost_ratio", row.get("Repost_Ratio", 0.2))),
                        "mention_ratio": float(row.get("mention_ratio", row.get("Mention_Ratio", 0.1))),
                        "hashtag_ratio": float(row.get("hashtag_ratio", row.get("Hashtag_Ratio", 0.1))),
                        "content_diversity": float(row.get("content_diversity", row.get("Content_Diversity", 0.5))),
                        "activity_regularity": float(row.get("activity_regularity", row.get("Activity_Regularity", 0.5))),
                        "duplicate_content_ratio": float(row.get("duplicate_content_ratio", row.get("Duplicate_Content_Ratio", 0.1))),
                    }
                    followers.append(follower)

                st.session_state.followers_data = followers

                detector = st.session_state.detector
                from engine.features import extract_features, feature_vector_to_array
                feature_arrays = np.array([feature_vector_to_array(extract_features(f)) for f in followers])
                detector.train_unsupervised(feature_arrays)

                results, summary = detector.analyze(followers)
                st.session_state.analysis_results = results
                st.session_state.analysis_summary = summary

                network_analyzer = st.session_state.network_analyzer
                network_analyzer.build_graph(st.session_state.target_username, followers, results)
                network_analyzer.add_simulated_interactions(followers, results)

                summary_dict = {
                    "total_followers": summary.total_followers,
                    "genuine_count": summary.genuine_count,
                    "suspicious_count": summary.suspicious_count,
                    "likely_fake_count": summary.likely_fake_count,
                    "fake_count": summary.fake_count,
                    "fake_ratio": summary.fake_ratio,
                    "avg_fake_probability": summary.avg_fake_probability,
                }
                save_analysis_history(st.session_state.target_username, summary_dict, [])

                st.success(f"✅ 成功处理 {len(followers)} 个粉丝数据！")
                st.rerun()
        except Exception as e:
            st.error(f"处理文件时出错: {str(e)}")


def main():
    init_session_state()
    config = sidebar_config()

    if config["data_source"] == "上传CSV文件" and config["analyze_btn"]:
        st.warning("请在主面板上传CSV文件后点击处理按钮。")

    if config["analyze_btn"] and config["data_source"] != "上传CSV文件":
        run_analysis(config)

    if config["data_source"] == "上传CSV文件" and not st.session_state.analysis_results:
        render_csv_upload()

    if st.session_state.analysis_results and st.session_state.analysis_summary:
        tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8, tab9 = st.tabs([
            "📊 分析概览",
            "⚠️ 风险因素",
            "📋 粉丝详情",
            "🌐 网络分析",
            "📈 特征分布",
            "📉 历史趋势",
            "💰 购买粉丝检测",
            "💬 互动质量",
            "👥 虚假群组",
        ])

        summary = st.session_state.analysis_summary
        results = st.session_state.analysis_results

        with tab1:
            render_overview(summary)
            st.markdown("---")
            render_recommendations(summary)

        with tab2:
            render_risk_factors(summary)

        with tab3:
            render_follower_details(results)

        with tab4:
            render_network_graph()

        with tab5:
            render_feature_distribution()

        with tab6:
            render_trend()

        with tab7:
            render_bought_follower_detection()

        with tab8:
            render_interaction_quality()

        with tab9:
            render_fake_groups()
    elif not config["analyze_btn"]:
        st.markdown("""
        <div style='text-align: center; padding: 80px 20px;'>
            <h1>🔍 社交媒体虚假粉丝检测工具</h1>
            <p style='font-size: 18px; color: #666;'>
                分析粉丝账号属性，识别虚假/僵尸粉丝<br>
                支持注册时间、内容质量、关注/粉丝比例、互动率等多维度分析
            </p>
            <div style='margin-top: 40px; text-align: left; max-width: 600px; margin-left: auto; margin-right: auto;'>
                <h3>🚀 快速开始</h3>
                <ol>
                    <li>在左侧选择数据来源（模拟数据可直接演示）</li>
                    <li>调整参数并点击「开始分析」</li>
                    <li>查看分析结果、聚集系数分布图、趋势变化</li>
                    <li>系统自动标注可疑账号，人工审核后导出标注列表</li>
                </ol>
                <h3>📊 核心功能</h3>
                <ul>
                    <li><b>多维度特征分析</b>：账号年龄、互动率、内容质量、关注比例等16项指标</li>
                    <li><b>机器学习检测</b>：Isolation Forest 无监督 + Random Forest 有监督</li>
                    <li><b>聚集系数网络分析</b>：NetworkX 计算各节点聚集系数，识别虚假粉丝集群（高效O(n)复杂度）</li>
                    <li><b>UTC标准化时间</b>：注册时间统一转换为UTC，消除时区差异</li>
                    <li><b>历史趋势追踪</b>：记录每次分析结果，监控风险账号比例变化</li>
                    <li><b>人工审核工作流</b>：系统自动标注，人工逐个/批量审核，支持备注，避免误删</li>
                    <li><b>标注导出</b>：导出含审核状态的CSV，使用平台官方工具处理</li>
                </ul>
                <div style='margin-top: 20px; padding: 15px; background: #fff3cd; border-radius: 8px;'>
                    <b>⚠️ 安全说明</b>：本工具仅进行标注和分析，不会自动删除任何粉丝。
                    所有清理操作需您在社交媒体平台内人工复核后手动执行。
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)


if __name__ == "__main__":
    main()