import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import json
from datetime import datetime, timedelta
import time

from scoring_model import ComprehensiveScorer
from training_recommender import PersonalizedTrainingRecommender
from sample_data import sample_conversations
from realtime_quality_monitor import RealtimeQualityMonitor
from excellent_script_miner import ExcellentScriptMiner
from agent_ranking_system import AgentRankingSystem


st.set_page_config(
    page_title="客服对话质量评分系统",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)


@st.cache_resource
def load_models():
    scorer = ComprehensiveScorer()
    recommender = PersonalizedTrainingRecommender()
    monitor = RealtimeQualityMonitor()
    miner = ExcellentScriptMiner()
    ranker = AgentRankingSystem()
    return scorer, recommender, monitor, miner, ranker


def create_radar_chart(scores_dict):
    categories = list(scores_dict.keys())
    values = [v["score"] for v in scores_dict.values()]

    fig = go.Figure(data=go.Scatterpolar(
        r=values,
        theta=["响应速度", "用户满意度", "客服情绪归因"],
        fill='toself',
        line_color='rgb(0, 122, 255)',
        fillcolor='rgba(0, 122, 255, 0.3)'
    ))

    fig.update_layout(
        polar=dict(
            radialaxis=dict(
                visible=True,
                range=[0, 100]
            )),
        showlegend=False,
        height=400
    )
    return fig


def create_gauge_chart(score, title):
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=score,
        domain={'x': [0, 1], 'y': [0, 1]},
        title={'text': title, 'font': {'size': 14}},
        gauge={
            'axis': {'range': [0, 100], 'tickwidth': 1},
            'bar': {'color': "#007AFF"},
            'bgcolor': "white",
            'borderwidth': 2,
            'bordercolor': "lightgray",
            'steps': [
                {'range': [0, 60], 'color': '#FF6B6B'},
                {'range': [60, 80], 'color': '#FFD93D'},
                {'range': [80, 90], 'color': '#6BCB77'},
                {'range': [90, 100], 'color': '#4D96FF'}
            ],
            'threshold': {
                'line': {'color': "red", 'width': 4},
                'thickness': 0.75,
                'value': 80
            }
        }
    ))
    fig.update_layout(height=250)
    return fig


def get_grade_color(grade):
    colors = {
        'A': '#4D96FF',
        'B': '#6BCB77',
        'C': '#FFD93D',
        'D': '#FF9F45',
        'F': '#FF6B6B'
    }
    return colors.get(grade, '#666666')


def get_grade_description(grade):
    descriptions = {
        'A': '优秀 - 服务质量卓越，继续保持',
        'B': '良好 - 服务质量达标，有提升空间',
        'C': '一般 - 服务质量合格，需加强改进',
        'D': '待改进 - 服务质量存在明显问题',
        'F': '不合格 - 服务质量严重不达标'
    }
    return descriptions.get(grade, '未知')


def get_satisfaction_label(level):
    labels = {
        'very_satisfied': '😊 非常满意',
        'satisfied': '🙂 满意',
        'neutral': '😐 一般',
        'dissatisfied': '😕 不满意',
        'very_dissatisfied': '😠 非常不满意'
    }
    return labels.get(level, level)


def get_stability_label(level):
    labels = {
        'very_stable': '非常稳定',
        'stable': '稳定',
        'moderate': '一般',
        'unstable': '不稳定',
        'very_unstable': '非常不稳定'
    }
    return labels.get(level, level)


def main():
    st.title("📊 客服对话质量评分系统")
    st.markdown("---")

    scorer, recommender, monitor, miner, ranker = load_models()

    with st.sidebar:
        st.header("⚙️ 功能导航")
        page = st.radio(
            "选择功能模块",
            ["单对话评分", "批量分析", "个性化培训", "手动输入", 
             "实时质检", "优秀话术", "客服排名", "数据统计"]
        )
        st.markdown("---")
        st.markdown("### 📖 使用说明")
        st.markdown("""
        1. **单对话评分**: 选择示例对话查看评分详情
        2. **批量分析**: 分析多个对话生成团队报告
        3. **个性化培训**: 分析个人弱项，推荐专项培训
        4. **手动输入**: 输入自定义对话进行评分
        5. **实时质检**: 对话进行中实时评分预警
        6. **优秀话术**: 自动提炼高评分对话话术
        7. **客服排名**: 多维度综合排名激励
        8. **数据统计**: 查看整体数据统计
        """)

    if page == "单对话评分":
        single_conversation_page(scorer, recommender)
    elif page == "批量分析":
        batch_analysis_page(scorer, recommender)
    elif page == "个性化培训":
        personalized_training_page(scorer, recommender)
    elif page == "手动输入":
        manual_input_page(scorer, recommender)
    elif page == "实时质检":
        realtime_monitor_page(scorer, monitor)
    elif page == "优秀话术":
        excellent_script_page(scorer, miner)
    elif page == "客服排名":
        agent_ranking_page(scorer, ranker)
    else:
        statistics_page(scorer, recommender)


def single_conversation_page(scorer, recommender):
    st.header("📝 单对话评分分析")

    conv_options = {f"对话 {i+1} - {c.get('agent_id', '未知')}": c
                    for i, c in enumerate(sample_conversations)}

    selected_conv = st.selectbox(
        "选择要分析的对话",
        list(conv_options.keys())
    )

    conversation = conv_options[selected_conv]

    with st.expander("📄 查看对话内容", expanded=True):
        for msg in conversation["messages"]:
            role = "👤 客户" if msg["role"] == "customer" else "🤖 客服"
            time_str = msg.get("timestamp", "")
            if time_str:
                try:
                    dt = datetime.fromisoformat(time_str.replace('Z', '+00:00'))
                    time_str = dt.strftime("%H:%M:%S")
                except:
                    pass
            st.markdown(f"**{role}** [{time_str}]")
            st.info(msg["content"])

    post_survey = conversation.get("post_survey")
    if post_survey:
        with st.expander("📋 结单后满意度调查", expanded=True):
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("满意度评分", f"{post_survey.get('satisfaction_score', 0)}/5")
            with col2:
                st.metric("解决评价", f"{post_survey.get('resolution_rating', 0)}/5")
            with col3:
                st.metric("态度评价", f"{post_survey.get('attitude_rating', 0)}/5")
            with col4:
                recommend = "✅ 是" if post_survey.get('would_recommend', False) else "❌ 否"
                st.metric("是否推荐", recommend)
            st.markdown(f"**客户评论**: {post_survey.get('comment', '无')}")

    if st.button("🔍 开始评分分析", type="primary"):
        with st.spinner("正在分析对话..."):
            result = scorer.score_conversation(conversation)
            time.sleep(1)

        st.success("分析完成！")
        st.markdown("---")

        col1, col2, col3 = st.columns([1, 1, 1])

        with col1:
            score = result["comprehensive_score"]
            grade = result["grade"]
            st.metric("综合评分", f"{score}", delta=grade)
            st.plotly_chart(create_gauge_chart(score, "综合评分"), use_container_width=True)

        with col2:
            st.metric("评级", grade)
            st.markdown(f"<h3 style='color: {get_grade_color(grade)}; text-align: center;'>{grade}</h3>", unsafe_allow_html=True)
            st.info(get_grade_description(grade))

        with col3:
            st.metric("对话轮次", result["summary"]["total_messages"])
            satisfaction_level = result["summary"].get("satisfaction_level", "unknown")
            st.metric("满意度水平", get_satisfaction_label(satisfaction_level))
            emotion_stability = result["summary"].get("emotion_stability", "unknown")
            st.metric("情绪稳定性", get_stability_label(emotion_stability))

        st.markdown("---")
        st.subheader("📊 维度评分详情")

        dim_scores = result["dimension_scores"]
        col1, col2, col3 = st.columns(3)

        with col1:
            speed_score = dim_scores["response_speed"]["score"]
            st.plotly_chart(create_gauge_chart(speed_score, "响应速度"), use_container_width=True)
            st.caption(f"权重: {dim_scores['response_speed']['weight']*100}%")

        with col2:
            satisfaction_score = dim_scores["customer_satisfaction"]["score"]
            st.plotly_chart(create_gauge_chart(satisfaction_score, "用户满意度"), use_container_width=True)
            st.caption(f"权重: {dim_scores['customer_satisfaction']['weight']*100}%")

        with col3:
            emotion_score = dim_scores["service_emotion"]["score"]
            st.plotly_chart(create_gauge_chart(emotion_score, "客服情绪归因"), use_container_width=True)
            st.caption(f"权重: {dim_scores['service_emotion']['weight']*100}%")

        st.subheader("🎯 雷达图分析")
        st.plotly_chart(create_radar_chart(dim_scores), use_container_width=True)

        st.markdown("---")
        st.subheader("⚠️ 扣分项说明")

        deductions = result["deductions"]
        if deductions:
            for d in deductions:
                severity_color = "#FF6B6B" if d["severity"] == "high" else "#FFD93D"
                with st.expander(f"【{d['category']}】 - 扣 {d['score_loss']} 分", expanded=True):
                    st.markdown(f"**严重程度**: :{severity_color}[{d['severity']}]")
                    st.markdown(f"**问题描述**: {d['description']}")
                    st.markdown(f"**改进建议**: {d['suggestion']}")
        else:
            st.success("✅ 无明显扣分项，服务质量优秀！")


def batch_analysis_page(scorer, recommender):
    st.header("📈 批量分析报告")

    if st.button("🚀 分析所有示例对话", type="primary"):
        with st.spinner("正在批量分析..."):
            results = []
            for conv in sample_conversations:
                result = scorer.score_conversation(conv)
                results.append(result)

            batch_report = recommender.generate_batch_training_report(results)
            time.sleep(2)

        st.success(f"完成分析 {batch_report['total_conversations']} 条对话！")

        st.markdown("---")
        st.subheader("📊 整体概览")

        col1, col2, col3 = st.columns(3)
        with col1:
            avg_score = sum(r["comprehensive_score"] for r in results) / len(results)
            st.metric("平均综合评分", round(avg_score, 2))
        with col2:
            st.metric("客服人数", batch_report["total_agents"])
        with col3:
            st.metric("对话总数", batch_report["total_conversations"])

        st.markdown("---")
        st.subheader("🏆 评分分布")

        grades = [r["grade"] for r in results]
        grade_counts = pd.Series(grades).value_counts()
        dist_df = pd.DataFrame({"等级": grade_counts.index, "数量": grade_counts.values})
        fig = px.bar(dist_df, x="等级", y="数量", color="等级",
                     color_discrete_map={'A': '#4D96FF', 'B': '#6BCB77', 'C': '#FFD93D', 'D': '#FF9F45', 'F': '#FF6B6B'})
        st.plotly_chart(fig, use_container_width=True)

        st.markdown("---")
        st.subheader("📐 各维度平均分")

        avg_speed = sum(r["dimension_scores"]["response_speed"]["score"] for r in results) / len(results)
        avg_satisfaction = sum(r["dimension_scores"]["customer_satisfaction"]["score"] for r in results) / len(results)
        avg_emotion = sum(r["dimension_scores"]["service_emotion"]["score"] for r in results) / len(results)

        dim_df = pd.DataFrame({
            "维度": ["响应速度", "用户满意度", "客服情绪归因"],
            "平均分": [round(avg_speed, 2), round(avg_satisfaction, 2), round(avg_emotion, 2)]
        })
        fig = px.bar(dim_df, x="维度", y="平均分", color="维度", range_y=[0, 100])
        st.plotly_chart(fig, use_container_width=True)

        st.markdown("---")
        st.subheader("⚠️ 常见扣分项")

        all_deductions = []
        for r in results:
            all_deductions.extend(r.get("deductions", []))

        if all_deductions:
            ded_df = pd.DataFrame(all_deductions)
            ded_counts = ded_df["category"].value_counts()
            ded_count_df = pd.DataFrame({"扣分项": ded_counts.index, "次数": ded_counts.values})
            fig = px.pie(ded_count_df, values="次数", names="扣分项")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("无扣分项记录")

        st.markdown("---")
        st.subheader("👥 客服表现排名")

        agent_scores = {}
        for r in results:
            agent_id = r["agent_id"]
            if agent_id not in agent_scores:
                agent_scores[agent_id] = []
            agent_scores[agent_id].append(r["comprehensive_score"])

        agent_avg = {k: sum(v)/len(v) for k, v in agent_scores.items()}
        sorted_agents = sorted(agent_avg.items(), key=lambda x: x[1], reverse=True)

        col1, col2 = st.columns(2)

        with col1:
            st.markdown("#### 🌟 表现优秀")
            for agent, score in sorted_agents[:3]:
                st.markdown(f"- **{agent}**: {score:.2f} 分")

        with col2:
            st.markdown("#### 📉 需要改进")
            for agent, score in sorted_agents[-3:]:
                st.markdown(f"- **{agent}**: {score:.2f} 分")

        st.markdown("---")
        st.subheader("📋 详细结果列表")

        results_df = pd.DataFrame([
            {
                "对话ID": r["conversation_id"],
                "客服ID": r["agent_id"],
                "综合评分": r["comprehensive_score"],
                "等级": r["grade"],
                "响应速度": r["dimension_scores"]["response_speed"]["score"],
                "用户满意度": r["dimension_scores"]["customer_satisfaction"]["score"],
                "客服情绪归因": r["dimension_scores"]["service_emotion"]["score"],
                "满意度水平": get_satisfaction_label(r["summary"].get("satisfaction_level", "unknown"))
            }
            for r in results
        ])
        st.dataframe(results_df, use_container_width=True)


def personalized_training_page(scorer, recommender):
    st.header("🎯 个性化培训分析")

    with st.spinner("正在加载分析数据..."):
        results = []
        for conv in sample_conversations:
            result = scorer.score_conversation(conv)
            results.append(result)

    agent_ids = sorted(list(set(r["agent_id"] for r in results)))

    selected_agent = st.selectbox(
        "选择客服进行个性化分析",
        agent_ids
    )

    if selected_agent:
        weakness_analysis = recommender.analyze_personal_weaknesses(results, selected_agent)
        training_plan = recommender.generate_personalized_training_plan(weakness_analysis)

        st.markdown("---")
        st.subheader(f"📊 {selected_agent} 综合表现")

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("对话数量", weakness_analysis["conversation_count"])
        with col2:
            st.metric("平均综合评分", weakness_analysis["avg_comprehensive_score"])
        with col3:
            st.info(weakness_analysis["overall_assessment"])

        st.markdown("---")
        st.subheader("💪 优势项目")

        strengths = weakness_analysis.get("strengths", [])
        if strengths:
            for s in strengths:
                st.success(f"✅ {s['dimension']}: {s['score']} 分 - {s['assessment']}")
        else:
            st.info("暂无明显优势项目，继续努力！")

        st.markdown("---")
        st.subheader("🎯 待改进项目（按优先级排序）")

        weaknesses = weakness_analysis.get("weaknesses", [])
        if weaknesses:
            for i, w in enumerate(weaknesses, 1):
                with st.expander(f"#{i} {w['dimension']} - 差距 {w['gap']} 分", expanded=True):
                    st.markdown(f"**当前得分**: {w['score']} 分")
                    st.markdown(f"**扣分次数**: {w['deduction_count']} 次")
                    if w.get("common_issues"):
                        st.markdown("**常见问题**:")
                        for issue in w["common_issues"]:
                            st.markdown(f"- {issue}")
        else:
            st.success("🎉 表现优秀，无明显待改进项目！")

        st.markdown("---")
        st.subheader("📚 个性化培训建议")

        modules = training_plan.get("recommended_modules", [])
        if modules:
            for m in modules:
                priority_label = "🔴 高优先级" if m["priority"] == "high" else "🟡 中优先级" if m["priority"] == "medium" else "🟢 低优先级"
                with st.expander(f"{priority_label} {m['title']} ({m['duration']})", expanded=True):
                    st.markdown(f"**针对弱项**: {m['target_weakness']}")
                    st.markdown(f"**预期提升**: {m['expected_improvement']}")
                    st.markdown(f"**目标分数**: {m['current_score']} → {m['target_score']}")
                    st.markdown("**培训内容**:")
                    for content in m["content"]:
                        st.markdown(f"- {content}")
                    st.markdown("**课后练习**:")
                    for exercise in m["practice_exercises"]:
                        st.markdown(f"- {exercise}")
        else:
            st.success("🎉 表现优秀，无需专项培训！")

        st.markdown("---")
        st.subheader("✅ 行动计划")

        actions = training_plan.get("action_items", [])
        if actions:
            action_df = pd.DataFrame(actions)
            st.dataframe(action_df, use_container_width=True)
        else:
            st.info("暂无特殊行动计划")

        st.markdown("---")
        st.subheader("🎯 改进目标（4周）")

        goals = training_plan.get("improvement_goals", [])
        if goals:
            for g in goals:
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.markdown(f"**{g['dimension']}**")
                with col2:
                    st.metric("当前", g["current_score"])
                with col3:
                    st.metric("目标", g["target_score"])
                with col4:
                    st.metric("提升目标", f"+{g['improvement_target']}")
        else:
            st.info("暂无改进目标")

        st.markdown("---")
        st.subheader("👥 团队共性问题分析")

        common_weaknesses = recommender.generate_batch_training_report(results).get("common_weaknesses", [])
        if common_weaknesses:
            for cw in common_weaknesses:
                st.warning(f"⚠️ {cw['dimension']} - 影响 {cw['affected_agents']} 人，平均 {cw['avg_score']} 分")
                st.markdown(f"**建议**: {cw['recommendation']}")
        else:
            st.success("团队表现均衡，无明显共性问题！")


def manual_input_page(scorer, recommender):
    st.header("✏️ 手动输入对话")

    st.markdown("### 输入对话内容")

    with st.form("manual_conversation"):
        agent_id = st.text_input("客服ID", value="agent_manual")
        customer_id = st.text_input("客户ID", value="customer_manual")

        st.markdown("#### 对话内容（每行一条消息）")
        st.markdown("格式: `角色: 内容` (角色=客户/客服)")
        st.markdown("示例:")
        st.code("客户: 你好，我想查询一下订单\n客服: 您好，请提供一下您的订单号")

        conversation_text = st.text_area(
            "输入对话",
            height=300,
            placeholder="客户: 你好，我想咨询退款政策\n客服: 您好，关于退款政策..."
        )

        st.markdown("#### 结单后满意度调查（可选）")
        col1, col2, col3 = st.columns(3)
        with col1:
            satisfaction_score = st.slider("整体满意度", 1, 5, 3)
        with col2:
            resolution_rating = st.slider("问题解决评价", 1, 5, 3)
        with col3:
            attitude_rating = st.slider("服务态度评价", 1, 5, 3)
        would_recommend = st.checkbox("客户是否愿意推荐")
        comment = st.text_input("客户评论")

        submit_button = st.form_submit_button("🔍 开始分析", type="primary")

    if submit_button and conversation_text.strip():
        messages = []
        base_time = datetime.now()

        for i, line in enumerate(conversation_text.strip().split('\n')):
            line = line.strip()
            if not line:
                continue

            if ':' in line:
                role_str, content = line.split(':', 1)
                role_str = role_str.strip()
                content = content.strip()

                role = "customer" if "客户" in role_str else "service"
                timestamp = (base_time + timedelta(seconds=i * 30)).isoformat()

                messages.append({
                    "role": role,
                    "content": content,
                    "timestamp": timestamp
                })

        if messages:
            post_survey = {
                "satisfaction_score": satisfaction_score,
                "resolution_rating": resolution_rating,
                "attitude_rating": attitude_rating,
                "would_recommend": would_recommend,
                "comment": comment
            } if satisfaction_score != 3 or resolution_rating != 3 or attitude_rating != 3 else None

            conversation = {
                "id": "manual_001",
                "agent_id": agent_id,
                "customer_id": customer_id,
                "timestamp": datetime.now().isoformat(),
                "messages": messages,
                "post_survey": post_survey
            }

            with st.spinner("正在分析..."):
                result = scorer.score_conversation(conversation)

            st.success("分析完成！")

            st.markdown("---")
            st.subheader("📊 分析结果")

            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("综合评分", result["comprehensive_score"])
            with col2:
                st.metric("评级", result["grade"])
            with col3:
                st.metric("对话轮次", result["summary"]["total_messages"])

            st.markdown("---")
            st.subheader("📐 各维度评分")

            dim_scores = result["dimension_scores"]
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("响应速度", dim_scores["response_speed"]["score"])
            with col2:
                st.metric("用户满意度", dim_scores["customer_satisfaction"]["score"])
            with col3:
                st.metric("客服情绪归因", dim_scores["service_emotion"]["score"])

            st.markdown("---")
            st.subheader("⚠️ 扣分项")

            if result["deductions"]:
                for d in result["deductions"]:
                    st.warning(f"【{d['category']}】{d['description']}")
            else:
                st.success("✅ 无扣分项")


def statistics_page(scorer, recommender):
    st.header("📉 数据统计中心")

    with st.spinner("加载统计数据..."):
        results = []
        for conv in sample_conversations:
            result = scorer.score_conversation(conv)
            results.append(result)

    st.markdown("### 📊 系统评分分布说明")

    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        st.markdown("<h3 style='color: #4D96FF; text-align: center;'>A</h3>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center;'>90-100分<br>优秀</p>", unsafe_allow_html=True)
    with col2:
        st.markdown("<h3 style='color: #6BCB77; text-align: center;'>B</h3>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center;'>80-89分<br>良好</p>", unsafe_allow_html=True)
    with col3:
        st.markdown("<h3 style='color: #FFD93D; text-align: center;'>C</h3>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center;'>70-79分<br>一般</p>", unsafe_allow_html=True)
    with col4:
        st.markdown("<h3 style='color: #FF9F45; text-align: center;'>D</h3>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center;'>60-69分<br>待改进</p>", unsafe_allow_html=True)
    with col5:
        st.markdown("<h3 style='color: #FF6B6B; text-align: center;'>F</h3>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center;'><60分<br>不合格</p>", unsafe_allow_html=True)

    st.markdown("---")
    st.subheader("⚖️ 评分权重配置")

    weights_df = pd.DataFrame({
        "评分维度": ["响应速度", "用户满意度", "客服情绪归因"],
        "权重": ["25%", "40%", "35%"],
        "说明": [
            "基于客服响应客户消息的平均时长计算",
            "基于结单后满意度调查数据，或对话内容估计",
            "分析客服情绪，剔除客户激怒因素后归因评分"
        ]
    })
    st.table(weights_df)

    st.markdown("---")
    st.subheader("📈 团队整体表现")

    avg_score = sum(r["comprehensive_score"] for r in results) / len(results)
    avg_speed = sum(r["dimension_scores"]["response_speed"]["score"] for r in results) / len(results)
    avg_satisfaction = sum(r["dimension_scores"]["customer_satisfaction"]["score"] for r in results) / len(results)
    avg_emotion = sum(r["dimension_scores"]["service_emotion"]["score"] for r in results) / len(results)

    col1, col2 = st.columns(2)

    with col1:
        st.metric("平均综合评分", round(avg_score, 2))
        st.metric("对话总数", len(results))

    with col2:
        st.metric("响应速度平均分", round(avg_speed, 2))
        st.metric("用户满意度平均分", round(avg_satisfaction, 2))
        st.metric("客服情绪归因平均分", round(avg_emotion, 2))

    st.markdown("---")
    st.subheader("💡 系统说明")

    with st.expander("响应速度评分规则", expanded=False):
        st.markdown("""
        - **理想响应时间**: ≤ 30秒 → 100分
        - **评分公式**: 响应时间超过30秒后线性扣分
        - **最大扣分**: 响应时间 ≥ 300秒 → 40分
        - **计算方式**: 统计所有客服回复的平均响应时间
        """)

    with st.expander("用户满意度评分规则", expanded=False):
        st.markdown("""
        - **优先使用结单调查数据**: 包含满意度评分、解决评价、态度评价
        - **推荐加分**: 客户愿意推荐可额外加分
        - **评论情感分析**: 客户评论文本情感倾向加分
        - **无调查数据时**: 基于对话内容关键词估计满意度
        """)

    with st.expander("客服情绪归因评分规则", expanded=False):
        st.markdown("""
        - **客户激怒检测**: 识别客户是否有激怒、辱骂、负面情绪
        - **情绪归因调整**: 客户先激怒的情况下，客服负面情绪扣分减轻
        - **礼貌用语检测**: 识别"您好"、"请"、"谢谢"等礼貌用语
        - **负面用语检测**: 识别不礼貌、不耐烦等负面表达
        - **综合评分**: 情感分析(40%) + 礼貌程度(60%)，剔除客户因素影响
        """)

    with st.expander("个性化培训推荐规则", expanded=False):
        st.markdown("""
        - **个人弱项分析**: 分析客服历史对话，找出得分低于70分的维度
        - **专项培训匹配**: 根据弱项类型匹配对应的专项培训模块
        - **分级培训内容**: 低分(＜60)推荐基础培训，中等分(60-75)推荐进阶培训
        - **行动计划**: 针对每个弱项生成具体的、可执行的改进行动
        - **改进目标**: 设置4周内具体可衡量的改进目标
        """)


def realtime_monitor_page(scorer, monitor):
    st.header("🔴 实时质检预警")
    
    st.markdown("### 对话进行中实时质量监控，发现问题及时预警")
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.subheader("📝 实时对话模拟")
        
        if "realtime_messages" not in st.session_state:
            st.session_state.realtime_messages = []
        
        with st.form("realtime_input"):
            role = st.selectbox("角色", ["客户", "客服"])
            content = st.text_area("输入消息内容", height=100)
            submit_msg = st.form_submit_button("发送消息")
            
            if submit_msg and content.strip():
                new_message = {
                    "role": "customer" if role == "客户" else "service",
                    "content": content,
                    "timestamp": datetime.now().isoformat()
                }
                st.session_state.realtime_messages.append(new_message)
        
        if st.button("🔄 清空对话"):
            st.session_state.realtime_messages = []
            st.rerun()
    
    with col2:
        st.subheader("⚠️ 实时质量评分")
        
        if st.session_state.realtime_messages:
            latest_msg = st.session_state.realtime_messages[-1]
            history = st.session_state.realtime_messages[:-1]
            
            result = monitor.analyze_realtime_message(history, latest_msg)
            
            score = result["current_quality_score"]
            st.metric("当前质量评分", score)
            
            color = "#4CAF50" if score >= 80 else "#FF9800" if score >= 60 else "#F44336"
            st.markdown(f"<h3 style='color: {color}; text-align: center;'>{score} 分</h3>", unsafe_allow_html=True)
            
            if result["warning_count"] > 0:
                st.error(f"⚠️ 发现 {result['warning_count']} 个预警")
                for warning in result["warnings"]:
                    severity_color = "#F44336" if warning["severity"] == "high" else "#FF9800"
                    st.markdown(f"<span style='color: {severity_color};'>【{warning['type']}】{warning['message']}</span>", unsafe_allow_html=True)
                    st.info(f"💡 建议: {warning['suggestion']}")
            else:
                st.success("✅ 对话质量良好")
            
            st.markdown("### 💡 改进建议")
            for suggestion in result["suggestions"]:
                st.write(f"- {suggestion}")
        else:
            st.info("请在左侧输入消息开始实时质检")
    
    st.markdown("---")
    st.subheader("📋 对话历史")
    
    for i, msg in enumerate(st.session_state.realtime_messages):
        role_icon = "👤 客户" if msg["role"] == "customer" else "🤖 客服"
        time_str = datetime.fromisoformat(msg["timestamp"]).strftime("%H:%M:%S")
        st.markdown(f"**{role_icon} [{time_str}]**")
        st.info(msg["content"])


def excellent_script_page(scorer, miner):
    st.header("💬 优秀话术推荐")
    
    with st.spinner("正在分析高评分对话话术..."):
        results = []
        for conv in sample_conversations:
            result = scorer.score_conversation(conv)
            results.append(result)
        
        script_analysis = miner.mine_excellent_scripts(results)
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.subheader("📊 话术质量概览")
        st.metric("高评分对话数", script_analysis["total_high_score"])
        st.metric("高评分占比", f"{script_analysis['high_score_ratio']}%")
        st.info(script_analysis["analysis"])
    
    with col2:
        st.subheader("🎯 场景话术推荐")
        scenario = st.selectbox(
            "选择场景查看推荐话术",
            ["通用", "投诉处理", "退款咨询", "技术支持"]
        )
        
        scenario_map = {
            "通用": "general", "投诉处理": "complaint", "退款咨询": "refund", "技术支持": "technical"}
        recommended = miner.get_script_for_scenario(scenario_map[scenario])
        
        for i, script in enumerate(recommended, 1):
            st.success(f"推荐话术 {i}: {script}")
    
    st.markdown("---")
    st.subheader("📚 优秀话术分类")
    
    for rec in script_analysis["recommended_scripts"]:
        with st.expander(f"【{rec['category']}】({rec['example_count']}条例子)", expanded=True):
            st.markdown(f"**最佳实践**: {rec['best_practice']}")
            st.markdown("**优秀话术示例:**")
            for i, script in enumerate(rec["top_scripts"], 1):
                st.write(f"{i}. {script}")


def agent_ranking_page(scorer, ranker):
    st.header("🏆 客服排名榜")
    
    with st.spinner("正在计算客服排名..."):
        results = []
        for conv in sample_conversations:
            result = scorer.score_conversation(conv)
            results.append(result)
        
        ranking_data = ranker.calculate_agent_rankings(results)
        incentives = ranker.generate_incentive_recommendations(ranking_data["rankings"])
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("客服总数", ranking_data["total_agents"])
    with col2:
        st.metric("团队平均分", ranking_data["avg_team_score"])
    with col3:
        badges = ranking_data["badge_distribution"]
        st.markdown(f"🥇 金牌: {badges['gold']} 🥈 银牌: {badges['silver']} 🥉 铜牌: {badges['bronze']}")
    
    st.markdown("---")
    st.subheader("📊 综合排名")
    
    ranking_df = pd.DataFrame([
        {
            "排名": r["rank"],
            "客服ID": r["agent_id"],
            "徽章": f"{r['badge']['icon']} {r['badge']['name']}",
            "综合得分": r["final_score"],
            "对话数": r["metrics"]["conversation_count"],
            "用户满意度": r["metrics"]["avg_satisfaction"],
            "情绪管理": r["metrics"]["avg_emotion"]
        }
        for r in ranking_data["rankings"]
    ])
    st.dataframe(ranking_df, use_container_width=True, hide_index=True)
    
    st.markdown("---")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("🌟 表现优秀客服")
        for agent in ranking_data["top_performers"]:
            st.success(f"{agent['badge']['icon']} {agent['agent_id']} - {agent['final_score']} 分")
            st.caption(f"对话数: {agent['metrics']['conversation_count']} | 满意度: {agent['metrics']['avg_satisfaction']}")
    
    with col2:
        st.subheader("💪 激励建议")
        for inc in incentives[:3]:
            with st.expander(f"{inc['agent_id']} 的激励"):
                st.markdown(f"**当前徽章**: {inc['current_badge']['icon']} {inc['current_badge']['name']}")
                st.markdown("**激励措施:**")
                for item in inc["incentives"]:
                    st.write(f"- {item}")
    
    st.markdown("---")
    st.subheader("📈 维度排名")
    dim_option = st.selectbox(
        "选择维度",
        ["综合", "用户满意度", "情绪管理", "响应速度"]
    )
    
    dim_map = {"综合": "comprehensive", "用户满意度": "satisfaction", "情绪管理": "emotion", "响应速度": "speed"}
    dim_rankings = ranker.get_dimension_rankings(results, dim_map[dim_option])
    
    dim_df = pd.DataFrame([
        {"排名": r["rank"], "客服ID": r["agent_id"], "得分": r["score"], "对话数": r["conversation_count"]}
        for r in dim_rankings
    ])
    st.dataframe(dim_df, use_container_width=True, hide_index=True)


if __name__ == "__main__":
    main()
