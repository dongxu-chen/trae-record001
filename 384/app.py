from __future__ import annotations

import io
from datetime import date, timedelta
from typing import Dict, List, Optional

import altair as alt
import numpy as np
import pandas as pd
import streamlit as st

from data_utils import (
    AGE_BUCKET_COLUMNS,
    GENDER_AGE_COLUMNS,
    generate_sample_competitors,
    generate_sample_data,
)
from lstm_model import (
    ALL_TARGETS,
    FEATURE_COLUMNS,
    PEAK_INCOME_TARGETS,
    PROFILE_TARGETS,
    train_lstm,
)
from recommender import (
    FEATURE_LABELS,
    generate_competitor_analysis,
    generate_recommendations,
)


st.set_page_config(
    page_title="主播直播数据预测平台",
    page_icon="🎥",
    layout="wide",
)

st.title("🎥 主播直播数据预测平台")
st.caption(
    "基于多任务 LSTM 模型，融合节假日与平台活动日历，预测峰值、收入、互动率与观众画像，"
    "提供互动模拟与竞品对比分析。"
)


DEFAULT_CATEGORY = "聊天"


REQUIRED_COLUMNS: List[str] = [
    "date", "start_hour", "weekday", "category", "duration_hours",
    "peak_viewers", "avg_viewers", "engagement_rate", "gift_income",
    "is_holiday", "platform_activity",
    "male_pct", "age_18_24", "age_25_34", "age_35_44", "age_45_plus",
]

PROFILE_DISPLAY_COLS = ["male_pct", "age_18_24", "age_25_34", "age_35_44", "age_45_plus"]


def validate_columns(df: pd.DataFrame) -> List[str]:
    return [c for c in REQUIRED_COLUMNS if c not in df.columns]


def coerce_types(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["date"] = pd.to_datetime(df["date"]).dt.strftime("%Y-%m-%d")
    for col in ["start_hour", "weekday", "peak_viewers", "avg_viewers"]:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype(int)
    for col in ["duration_hours", "engagement_rate", "gift_income", "platform_activity"]:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0).astype(float)
    df["is_holiday"] = pd.to_numeric(df["is_holiday"], errors="coerce").fillna(0).astype(int)
    for col in PROFILE_DISPLAY_COLS:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0).astype(float)
    df["category"] = df["category"].astype(str).fillna(DEFAULT_CATEGORY)
    df = df.sort_values("date").reset_index(drop=True)
    return df


@st.cache_data(show_spinner=False)
def load_sample_csv() -> bytes:
    df = generate_sample_data(n_days=60)
    buffer = io.StringIO()
    df.to_csv(buffer, index=False)
    return buffer.getvalue().encode("utf-8")


# ---------- Sidebar ----------
with st.sidebar:
    st.header("模型参数")
    seq_len = st.slider("历史窗口长度 (天)", 3, 21, 7)
    hidden_dim = st.selectbox("LSTM 隐藏层维度", [32, 64, 128], index=1)
    num_layers = st.selectbox("LSTM 层数", [1, 2, 3], index=1)
    epochs = st.slider("训练轮数", 10, 200, 80, 10)
    batch_size = st.selectbox("批次大小", [4, 8, 16, 32], index=1)
    learning_rate = st.number_input("学习率", 1e-5, 1e-2, 1e-3, format="%.4f")
    st.divider()
    st.download_button(
        "下载示例 CSV 模板",
        data=load_sample_csv(),
        file_name="sample_streamer_data.csv",
        mime="text/csv",
    )

# ---------- Main Tabs ----------
tab_data, tab_pred, tab_profile, tab_sim, tab_comp, tab_rec, tab_interp, tab_about = st.tabs([
    "📊 数据录入", "🔮 预测结果", "👥 观众画像", "🔬 互动模拟",
    "⚔️ 竞品分析", "💡 优化建议", "🔍 模型解释", "ℹ️ 关于",
])

if "dataset" not in st.session_state:
    st.session_state.dataset = generate_sample_data(n_days=30)
if "competitors" not in st.session_state:
    st.session_state.competitors = generate_sample_competitors()


# ======================================================
# Tab: 数据录入
# ======================================================
with tab_data:
    st.subheader("步骤 1：录入或上传历史直播数据")
    src_mode = st.radio(
        "数据来源",
        ["使用内置示例数据", "上传 CSV 文件", "手动编辑"],
        horizontal=True,
    )

    if src_mode == "使用内置示例数据":
        n_days = st.slider("生成记录天数", 15, 120, 45, key="sample_n")
        st.session_state.dataset = generate_sample_data(n_days=n_days)
        st.success(f"已生成 {len(st.session_state.dataset)} 条示例记录（含观众画像字段）。")
    elif src_mode == "上传 CSV 文件":
        uploaded = st.file_uploader("选择 CSV 文件", type=["csv"])
        if uploaded is not None:
            try:
                df_upload = pd.read_csv(uploaded)
                missing = validate_columns(df_upload)
                if missing:
                    st.error(f"CSV 缺少必要列：{', '.join(missing)}")
                else:
                    st.session_state.dataset = coerce_types(df_upload)
                    st.success(f"成功加载 {len(st.session_state.dataset)} 条记录。")
            except Exception as e:
                st.error(f"读取失败：{e}")
    else:
        st.caption("直接在下方表格中编辑，修改后点击『保存为数据集』。")
        base = st.session_state.dataset.tail(10).reset_index(drop=True)
        edited_df = st.data_editor(
            base,
            num_rows="dynamic",
            hide_index=True,
            use_container_width=True,
            key="data_editor",
        )
        if st.button("💾 保存编辑结果为数据集"):
            missing = validate_columns(edited_df)
            if missing:
                st.error(f"缺少必要列：{', '.join(missing)}")
            else:
                st.session_state.dataset = coerce_types(edited_df)
                st.success(f"已保存 {len(st.session_state.dataset)} 条记录。")

    st.divider()
    st.markdown("**当前数据集预览**")
    display_cols = [
        "date", "start_hour", "category", "duration_hours",
        "peak_viewers", "engagement_rate", "gift_income",
        "male_pct", "age_18_24", "age_25_34", "age_35_44", "age_45_plus",
    ]
    available_display = [c for c in display_cols if c in st.session_state.dataset.columns]
    st.dataframe(st.session_state.dataset[available_display], use_container_width=True, hide_index=True)

    with st.expander("📋 字段说明"):
        st.markdown(
            """
            | 列名 | 说明 |
            | --- | --- |
            | `date` | 直播日期，格式 YYYY-MM-DD |
            | `start_hour` | 开播小时（0-23） |
            | `weekday` | 星期几（0=周一, 6=周日） |
            | `is_holiday` | 是否节假日（0/1） |
            | `platform_activity` | 平台活动强度（0~1） |
            | `category` | 内容类别（游戏/音乐/聊天/户外/教育） |
            | `duration_hours` | 直播时长（小时） |
            | `peak_viewers` | 峰值观看人数 |
            | `avg_viewers` | 平均观看人数 |
            | `engagement_rate` | 互动率（0~1） |
            | `gift_income` | 礼物收入（元） |
            | `male_pct` | 男性观众占比（0~1） |
            | `age_18_24` | 18-24岁观众占比（0~1） |
            | `age_25_34` | 25-34岁观众占比（0~1） |
            | `age_35_44` | 35-44岁观众占比（0~1） |
            | `age_45_plus` | 45岁以上观众占比（0~1） |
            """
        )


# ======================================================
# Tab: 预测结果
# ======================================================
with tab_pred:
    st.subheader("步骤 2：训练多任务 LSTM 并预测")
    df = st.session_state.dataset
    missing = validate_columns(df)
    if missing:
        st.warning(f"数据字段不完整：{', '.join(missing)}")
    else:
        df = coerce_types(df)
        if len(df) < seq_len + 2:
            st.warning(f"数据条数不足，至少需要 {seq_len + 2} 条。当前：{len(df)} 条。")
        else:
            if st.button("🚀 训练模型并预测", type="primary"):
                with st.spinner("训练多任务 LSTM（共享底层 + 四个任务头）…"):
                    trained = train_lstm(
                        df,
                        seq_len=seq_len,
                        hidden_dim=int(hidden_dim),
                        num_layers=int(num_layers),
                        epochs=int(epochs),
                        batch_size=int(batch_size),
                        learning_rate=float(learning_rate),
                    )
                st.session_state.trained = trained

                peak, income = trained.predict_from_dataframe(df)
                engagement = trained.predict_engagement(df)
                profile = trained.predict_audience_profile(df)

                st.session_state.predicted_peak = peak
                st.session_state.predicted_income = income
                st.session_state.predicted_engagement = engagement
                st.session_state.predicted_profile = profile

                c1, c2, c3, c4 = st.columns(4)
                last_row = df.iloc[-1]
                c1.metric("下一场预测峰值", f"{int(peak):,}",
                          delta=f"{int(peak - last_row['peak_viewers']):+,} vs 上场")
                c2.metric("下一场预测收入", f"¥{income:,.2f}",
                          delta=f"¥{income - last_row['gift_income']:+,.2f} vs 上场")
                c3.metric("下一场预测互动率", f"{engagement:.4f}",
                          delta=f"{engagement - last_row['engagement_rate']:+.4f} vs 上场")
                c4.metric("历史平均峰值", f"{int(df['peak_viewers'].mean()):,}")

                st.markdown("**📈 预测与历史对比**")
                hist = df[["date", "peak_viewers", "gift_income", "engagement_rate"]].copy()
                next_date = pd.to_datetime(df["date"].iloc[-1]) + timedelta(days=1)
                pred_row = pd.DataFrame([{
                    "date": next_date.strftime("%Y-%m-%d"),
                    "peak_viewers": float(peak),
                    "gift_income": float(income),
                    "engagement_rate": float(engagement),
                    "类型": "预测",
                }])
                hist["类型"] = "历史"
                combined = pd.concat([hist.tail(20), pred_row], ignore_index=True)

                for metric, title in [
                    ("peak_viewers", "峰值观看人数"),
                    ("gift_income", "礼物收入"),
                    ("engagement_rate", "互动率"),
                ]:
                    chart = (
                        alt.Chart(combined)
                        .mark_line(point=True)
                        .encode(
                            x=alt.X("date:T", title="日期"),
                            y=alt.Y(metric, title=title),
                            color=alt.Color("类型:N", legend=alt.Legend(title="")),
                            tooltip=["date", metric, "类型"],
                        )
                        .properties(height=240, title=title)
                    )
                    st.altair_chart(chart, use_container_width=True)

                with st.expander("📉 训练损失曲线"):
                    loss_df = pd.DataFrame({
                        "epoch": list(range(1, len(trained.loss_history) + 1)),
                        "Total": trained.loss_history,
                        "Peak": trained.peak_loss_history,
                        "Income": trained.income_loss_history,
                        "Engagement": trained.engagement_loss_history,
                        "Profile": trained.profile_loss_history,
                    })
                    loss_long = loss_df.melt("epoch", var_name="Task", value_name="MSE")
                    chart_loss = (
                        alt.Chart(loss_long)
                        .mark_line()
                        .encode(x="epoch", y="MSE", color="Task")
                        .properties(height=300)
                    )
                    st.altair_chart(chart_loss, use_container_width=True)

                with st.expander("🧠 模型结构"):
                    st.code(str(trained.model))

                st.session_state.feature_importance = trained.feature_importance
                st.session_state.feature_columns = trained.feature_columns


# ======================================================
# Tab: 观众画像
# ======================================================
with tab_profile:
    st.subheader("👥 观众画像预测")
    st.caption("预测下一场直播的观众性别与年龄分布。")

    df = st.session_state.dataset
    missing = validate_columns(df)
    if "predicted_profile" not in st.session_state:
        st.info("请先在『预测结果』页训练模型。")
    elif missing:
        st.warning(f"数据字段不完整：{', '.join(missing)}")
    else:
        profile = st.session_state.predicted_profile
        prof_dict = profile.to_dict()

        col_g, col_a = st.columns(2)
        with col_g:
            st.markdown("### 性别分布")
            gender_df = pd.DataFrame({
                "性别": ["男性", "女性"],
                "占比(%)": [prof_dict["男性占比"], prof_dict["女性占比"]],
            })
            chart_g = (
                alt.Chart(gender_df)
                .mark_arc(innerRadius=60)
                .encode(
                    theta="占比(%):Q",
                    color="性别:N",
                    tooltip=["性别", "占比(%)"],
                )
                .properties(height=320, title="预测观众性别分布")
            )
            st.altair_chart(chart_g, use_container_width=True)

        with col_a:
            st.markdown("### 年龄分布")
            age_df = pd.DataFrame({
                "年龄段": ["18-24岁", "25-34岁", "35-44岁", "45岁+"],
                "占比(%)": [prof_dict["18-24岁"], prof_dict["25-34岁"], prof_dict["35-44岁"], prof_dict["45岁+"]],
            })
            chart_a = (
                alt.Chart(age_df)
                .mark_bar()
                .encode(
                    x=alt.X("占比(%):Q", title="占比 (%)"),
                    y=alt.Y("年龄段:N", title="", sort=None),
                    color=alt.Color("年龄段:N", legend=None),
                    tooltip=["年龄段", "占比(%)"],
                )
                .properties(height=320, title="预测观众年龄分布")
            )
            st.altair_chart(chart_a, use_container_width=True)

        st.markdown("### 历史观众画像均值 vs 预测")
        hist_male = df["male_pct"].mean() * 100
        hist_ages = [df[c].mean() * 100 for c in AGE_BUCKET_COLUMNS]
        compare_df = pd.DataFrame({
            "类别": ["男性", "女性", "18-24岁", "25-34岁", "35-44岁", "45岁+"],
            "历史平均(%)": [hist_male, 100 - hist_male] + hist_ages,
            "预测(%)": [prof_dict["男性占比"], prof_dict["女性占比"],
                      prof_dict["18-24岁"], prof_dict["25-34岁"],
                      prof_dict["35-44岁"], prof_dict["45岁+"]],
        })
        compare_long = compare_df.melt("类别", var_name="类型", value_name="占比(%)")
        chart_cmp = (
            alt.Chart(compare_long)
            .mark_bar()
            .encode(
                x=alt.X("类别:N", title=""),
                y=alt.Y("占比(%):Q", title="占比 (%)"),
                color="类型:N",
                xOffset="类型:N",
                tooltip=["类别", "类型", "占比(%)"],
            )
            .properties(height=340, title="历史均值 vs 预测对比")
        )
        st.altair_chart(chart_cmp, use_container_width=True)

        st.markdown("### 📊 预测画像数值")
        st.dataframe(pd.DataFrame([prof_dict]), use_container_width=True, hide_index=True)

        if abs(prof_dict["男性占比"] - 50) > 20:
            st.info("💡 观众性别分布偏差较大，可针对性选择内容和话题。")
        if prof_dict["18-24岁"] + prof_dict["25-34岁"] > 70:
            st.info("💡 核心观众为年轻群体，可加强潮流话题、短视频联动、互动玩法。")
        elif prof_dict["35-44岁"] + prof_dict["45岁+"] > 40:
            st.info("💡 核心观众为成熟群体，可加强深度内容、知识分享、品质生活。")


# ======================================================
# Tab: 互动模拟
# ======================================================
with tab_sim:
    st.subheader("🔬 互动率优化模拟")
    st.caption("调整某个参数，模拟预测互动率的变化，辅助找到最优运营策略。")

    df = st.session_state.dataset
    if "trained" not in st.session_state:
        st.info("请先在『预测结果』页训练模型。")
    else:
        trained = st.session_state.trained
        df = coerce_types(df)

        adjustable_features: Dict[str, str] = {
            "start_hour": "开播时段 (小时，0-23)",
            "duration_hours": "直播时长 (小时)",
            "platform_activity": "平台活动强度 (0-1)",
            "is_holiday": "是否节假日 (0/1)",
        }

        col1, col2 = st.columns([1, 2])
        with col1:
            st.markdown("### ⚙️ 参数调整")
            feature_key = st.selectbox(
                "选择要调整的参数",
                list(adjustable_features.keys()),
                format_func=lambda k: adjustable_features[k],
            )
            current_val = float(df[feature_key].iloc[-1])
            st.markdown(f"**当前值**：`{current_val}`")

            if feature_key == "start_hour":
                new_val = st.slider("新开播时段", 0, 23, int(current_val), 1)
            elif feature_key == "duration_hours":
                new_val = st.slider("新直播时长", 0.5, 12.0, float(current_val), 0.5)
            elif feature_key == "platform_activity":
                new_val = st.slider("平台活动强度", 0.0, 1.0, float(current_val), 0.1)
            else:
                new_val = st.selectbox("是否节假日", [0, 1], index=int(current_val))

            simulate = st.button("🔍 运行模拟", type="primary")

        with col2:
            if simulate:
                with st.spinner("模拟中…"):
                    result = trained.simulate_engagement_change(df, feature_key, float(new_val))

                st.markdown("### 📊 模拟结果")

                s1, s2, s3 = st.columns(3)
                s1.metric(
                    "互动率变化",
                    f"{result['engagement_pct_change']:+.1f}%",
                    delta=f"{result['engagement_delta']:+.4f}",
                )
                s2.metric(
                    "峰值变化",
                    f"{int(result['new_peak']):,}",
                    delta=f"{int(result['new_peak'] - result['base_peak']):+,}",
                )
                s3.metric(
                    "收入变化",
                    f"¥{result['new_income']:,.2f}",
                    delta=f"¥{result['new_income'] - result['base_income']:+,.2f}",
                )

                sim_df = pd.DataFrame([
                    {"指标": "互动率", "调整前": f"{result['base_engagement']:.4f}", "调整后": f"{result['new_engagement']:.4f}",
                     "变化": f"{result['engagement_pct_change']:+.1f}%"},
                    {"指标": "峰值观看人数", "调整前": f"{int(result['base_peak']):,}", "调整后": f"{int(result['new_peak']):,}",
                     "变化": f"{int(result['new_peak'] - result['base_peak']):+,}"},
                    {"指标": "礼物收入", "调整前": f"¥{result['base_income']:,.2f}", "调整后": f"¥{result['new_income']:,.2f}",
                     "变化": f"¥{result['new_income'] - result['base_income']:+,.2f}"},
                ])
                st.dataframe(sim_df, use_container_width=True, hide_index=True)

                if result["engagement_pct_change"] > 5:
                    st.success(f"✅ 将 `{adjustable_features[feature_key]}` 调整为 `{new_val}` 可提升互动率约 {result['engagement_pct_change']:.1f}%，建议尝试！")
                elif result["engagement_pct_change"] < -5:
                    st.error(f"⚠️ 将 `{adjustable_features[feature_key]}` 调整为 `{new_val}` 会导致互动率下降约 {abs(result['engagement_pct_change']):.1f}%，不建议。")
                else:
                    st.info(f"ℹ️ 调整 `{adjustable_features[feature_key]}` 对互动率影响不大（{result['engagement_pct_change']:+.1f}%），可综合考虑其他因素。")
            else:
                st.info("👈 选择参数并调整值，点击『运行模拟』查看效果。")

        with st.expander("📖 模拟说明"):
            st.markdown(
                """
                - 模拟原理：取最近 `seq_len` 场直播数据作为输入序列，
                  将最后一场的指定参数替换为新值，重新运行多任务 LSTM 预测。
                - 对比原始预测结果与修改后预测结果的差异，展示互动率、峰值、收入的变化。
                - 注意：模拟仅反映单参数变化的影响，实际直播效果受多因素综合作用。
                - 可多次调整不同参数组合，找到最优策略。
                """
            )


# ======================================================
# Tab: 竞品分析
# ======================================================
with tab_comp:
    st.subheader("⚔️ 竞品直播间分析")
    st.caption("输入竞品数据，对比预测结果与竞品表现，辅助策略调整。")

    comp_tab1, comp_tab2 = st.tabs(["📝 竞品数据录入", "📊 对比分析"])

    with comp_tab1:
        comp_mode = st.radio(
            "竞品数据来源",
            ["使用内置示例竞品", "上传 CSV", "手动编辑"],
            horizontal=True,
        )
        if comp_mode == "使用内置示例竞品":
            st.session_state.competitors = generate_sample_competitors()
            st.success("已加载 5 个示例竞品数据。")
        elif comp_mode == "上传 CSV":
            comp_uploaded = st.file_uploader("上传竞品 CSV", type=["csv"], key="comp_upload")
            if comp_uploaded is not None:
                try:
                    comp_df = pd.read_csv(comp_uploaded)
                    required_comp = ["competitor_name", "category", "avg_peak_viewers",
                                     "avg_gift_income", "avg_engagement_rate"]
                    missing_comp = [c for c in required_comp if c not in comp_df.columns]
                    if missing_comp:
                        st.error(f"缺少列：{', '.join(missing_comp)}")
                    else:
                        st.session_state.competitors = comp_df
                        st.success(f"已加载 {len(comp_df)} 个竞品。")
                except Exception as e:
                    st.error(f"读取失败：{e}")
        else:
            st.caption("直接编辑下方竞品数据表格：")
            edited_comp = st.data_editor(
                st.session_state.competitors,
                num_rows="dynamic",
                hide_index=True,
                use_container_width=True,
                key="comp_editor",
            )
            if st.button("💾 保存竞品数据"):
                st.session_state.competitors = edited_comp
                st.success("竞品数据已保存。")

        st.markdown("**当前竞品数据预览**")
        st.dataframe(st.session_state.competitors, use_container_width=True, hide_index=True)

    with comp_tab2:
        our_df = st.session_state.dataset
        comp_df = st.session_state.competitors
        if comp_df.empty:
            st.warning("请先录入竞品数据。")
        else:
            peak_val = st.session_state.get("predicted_peak", None)
            income_val = st.session_state.get("predicted_income", None)
            eng_val = st.session_state.get("predicted_engagement", None)

            if peak_val is None:
                st.info("请先在『预测结果』页训练模型以获取预测数据进行对比。")
                peak_val = float(our_df["peak_viewers"].mean())
                income_val = float(our_df["gift_income"].mean())
                eng_val = float(our_df["engagement_rate"].mean())

            report = generate_competitor_analysis(
                our_df,
                comp_df,
                our_predicted_peak=peak_val,
                our_predicted_income=income_val,
                our_predicted_engagement=eng_val,
            )

            st.markdown("### 📊 指标对比")
            gap_data = []
            for g in report.gaps:
                gap_data.append({
                    "指标": g.metric,
                    "我方预测/均值": f"{g.our_value:,.2f}",
                    "竞品平均": f"{g.competitor_avg:,.2f}",
                    "差距": f"{g.gap:+,.2f}",
                    "百分比": f"{g.pct_gap:+.1f}%",
                    "建议": g.advice,
                })
            st.dataframe(pd.DataFrame(gap_data), use_container_width=True, hide_index=True)

            col1, col2 = st.columns(2)
            with col1:
                st.markdown("### 🎯 同赛道竞品")
                if report.same_category_competitors:
                    st.info(f"与您同类别的竞品：**{', '.join(report.same_category_competitors)}**")
                else:
                    st.info("暂无同类别竞品数据。")

                st.markdown("### 🏆 头部对标")
                st.success(f"需关注：{report.top_benchmark}")

            with col2:
                st.markdown("### 📝 综合评价")
                st.markdown(report.summary)

            st.markdown("### 📈 雷达图对比（我方 vs 竞品均值 vs 头部）")
            top_comp = comp_df.loc[comp_df["avg_gift_income"].idxmax()]
            radar_df = pd.DataFrame([
                {"维度": "峰值", "我方": peak_val / max(comp_df["avg_peak_viewers"].max(), 1) * 100,
                 "竞品均值": comp_df["avg_peak_viewers"].mean() / max(comp_df["avg_peak_viewers"].max(), 1) * 100,
                 "头部": top_comp["avg_peak_viewers"] / max(comp_df["avg_peak_viewers"].max(), 1) * 100},
                {"维度": "收入", "我方": income_val / max(comp_df["avg_gift_income"].max(), 1) * 100,
                 "竞品均值": comp_df["avg_gift_income"].mean() / max(comp_df["avg_gift_income"].max(), 1) * 100,
                 "头部": top_comp["avg_gift_income"] / max(comp_df["avg_gift_income"].max(), 1) * 100},
                {"维度": "互动率", "我方": eng_val * 100 / max(comp_df["avg_engagement_rate"].max() * 100, 1) * 100,
                 "竞品均值": comp_df["avg_engagement_rate"].mean() * 100 / max(comp_df["avg_engagement_rate"].max() * 100, 1) * 100,
                 "头部": top_comp["avg_engagement_rate"] * 100 / max(comp_df["avg_engagement_rate"].max() * 100, 1) * 100},
            ])
            radar_long = radar_df.melt("维度", var_name="对比", value_name="归一化得分")
            chart_radar = (
                alt.Chart(radar_long)
                .mark_bar()
                .encode(
                    x=alt.X("维度:N", title=""),
                    y=alt.Y("归一化得分:Q", title="归一化得分 (%)"),
                    color="对比:N",
                    xOffset="对比:N",
                    tooltip=["维度", "对比", "归一化得分"],
                )
                .properties(height=340, title="我方 vs 竞品均值 vs 头部（归一化到 100）")
            )
            st.altair_chart(chart_radar, use_container_width=True)


# ======================================================
# Tab: 优化建议
# ======================================================
with tab_rec:
    st.subheader("💡 优化建议（模型解释 + 历史数据结合）")
    df = st.session_state.dataset
    missing = validate_columns(df)
    if missing:
        st.warning(f"数据字段不完整：{', '.join(missing)}")
    else:
        df = coerce_types(df)

        fi = st.session_state.get("feature_importance", None)
        fc = st.session_state.get("feature_columns", FEATURE_COLUMNS)
        rec = generate_recommendations(df, feature_importance=fi, feature_columns=fc)

        col1, col2 = st.columns(2)
        with col1:
            st.markdown("### 🕒 最佳开播时段")
            st.info(f"**{rec.optimal_hour}:00**")
            st.markdown(f"推荐星期：**{', '.join(rec.best_weekdays)}**")
            st.markdown(f"推荐时长：**{rec.recommended_duration:.1f} 小时**")
        with col2:
            st.markdown("### 🎯 内容方向")
            st.success(rec.content_direction)

        if rec.key_drivers:
            st.markdown("### 🔑 关键驱动因素（模型识别）")
            driver_df = pd.DataFrame({
                "因素": rec.key_drivers,
                "重要度排名": list(range(1, len(rec.key_drivers) + 1)),
            })
            st.dataframe(driver_df, use_container_width=True, hide_index=True)

        col_h, col_a = st.columns(2)
        with col_h:
            st.markdown("### 🎊 节假日策略")
            st.info(rec.holiday_advice)
        with col_a:
            st.markdown("### 🎪 平台活动策略")
            st.info(rec.activity_advice)

        st.markdown("### 📝 综合建议")
        st.markdown(rec.reason)

        st.markdown("### 📊 分时段数据表现")
        hour_stats = (
            df.groupby("start_hour")[["peak_viewers", "gift_income", "engagement_rate"]]
            .mean()
            .reset_index()
        )
        st.dataframe(hour_stats, use_container_width=True, hide_index=True)

        st.markdown("### 🏷️ 各内容类别表现")
        cat_stats = (
            df.groupby("category")[["peak_viewers", "gift_income", "engagement_rate"]]
            .mean()
            .reset_index()
            .sort_values("gift_income", ascending=False)
        )
        st.dataframe(cat_stats, use_container_width=True, hide_index=True)


# ======================================================
# Tab: 模型解释
# ======================================================
with tab_interp:
    st.subheader("🔍 模型可解释性分析")
    st.caption("基于梯度敏感度的特征重要度分析，揭示模型最关注的输入特征。")

    fi = st.session_state.get("feature_importance", None)
    fc = st.session_state.get("feature_columns", FEATURE_COLUMNS)

    if fi is None:
        st.info("请先在『预测结果』页训练模型。")
    else:
        labels = [FEATURE_LABELS.get(col, col) for col in fc]
        imp_df = pd.DataFrame({
            "特征": labels,
            "重要度": fi,
        }).sort_values("重要度", ascending=False)

        chart_imp = (
            alt.Chart(imp_df)
            .mark_bar()
            .encode(
                x=alt.X("重要度:Q", title="归一化重要度"),
                y=alt.Y("特征:N", title="", sort="-x"),
                color=alt.Color("重要度:Q", legend=None),
                tooltip=["特征", alt.Tooltip("重要度", format=".4f")],
            )
            .properties(height=400)
        )
        st.altair_chart(chart_imp, use_container_width=True)

        top3 = imp_df.head(3)["特征"].tolist()
        st.markdown(
            f"模型预测最关注的前 3 个特征是 **{', '.join(top3)}**。"
            " 运营中应重点关注这些因素的优化。"
        )

        if "is_holiday" in fc and "platform_activity" in fc:
            h_idx = fc.index("is_holiday")
            a_idx = fc.index("platform_activity")
            h_imp = fi[h_idx]
            a_imp = fi[a_idx]
            if h_imp > 0.08 or a_imp > 0.08:
                st.markdown(
                    f"**节假日与活动影响**：节假日重要度 {h_imp:.4f}，"
                    f"平台活动重要度 {a_imp:.4f}，外部日历因素对预测有显著影响。"
                )
            else:
                st.markdown(
                    f"**节假日与活动影响**：节假日重要度 {h_imp:.4f}，"
                    f"平台活动重要度 {a_imp:.4f}，当前样本中外部日历因素影响较小。"
                )

        with st.expander("📖 方法说明"):
            st.markdown(
                """
                - 采用 **梯度敏感度（Gradient Sensitivity）**：计算模型输出对各输入特征的梯度绝对值，
                  在时间维度上平均后归一化，得到每个特征的相对重要度。
                - 这与 SHAP 类似但计算效率更高，适合 LSTM 序列模型。
                - 重要度高的特征意味着模型认为它对预测影响更大，运营时应优先优化。
                """
            )


# ======================================================
# Tab: 关于
# ======================================================
with tab_about:
    st.subheader("关于本平台")
    st.markdown(
        """
        ### 🧠 模型架构
        **多任务 LSTM**（4 个任务头）：
        - **共享底层 LSTM 编码器**：提取 9 维输入特征的时序模式
        - **峰值头**：预测下一场直播的峰值观看人数
        - **收入头**：预测下一场直播的礼物收入
        - **互动率头**：预测下一场直播的互动率（用于模拟优化）
        - **画像头**：预测观众性别 + 4 个年龄段分布

        ### 📥 输入特征 (9 维)
        `start_hour`, `weekday`, `is_holiday`, `platform_activity`,
        `duration_hours`, `avg_viewers`, `engagement_rate`, `gift_income`, `peak_viewers`

        ### 📤 预测目标 (8 维)
        `peak_viewers`, `gift_income`, `engagement_rate`,
        `male_pct`, `age_18_24`, `age_25_34`, `age_35_44`, `age_45_plus`

        ### 🔧 核心功能
        1. **多任务预测**：一次训练同时输出峰值、收入、互动率、观众画像
        2. **节假日/活动日历**：内置 2026 年节假日与平台大促标记
        3. **互动率模拟**：调整参数预测互动率变化，辅助运营决策
        4. **竞品对比分析**：对比我方预测与竞品数据，识别差距与机会
        5. **模型可解释性**：梯度敏感度分析，揭示关键驱动因素
        6. **优化建议**：结合历史统计 + 模型解释，给出科学建议

        ### 🛠️ 技术栈
        Python 3、PyTorch、Pandas、Streamlit、Altair、scikit-learn
        """
    )
