import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

st.set_page_config(
    page_title="用户活跃度预测系统",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'Arial Unicode MS']
plt.rcParams['axes.unicode_minus'] = False

from data_generator import generate_all_data
from feature_engineering import build_feature_matrix, select_features_by_importance
from model_training import UserActivityModel, train_full_pipeline
from analysis_engine import (
    SHAPAnalyzer, ChurnRiskScorer, RecommendationEngine,
    ActivityAttributor, CopyGenerator, GroupComparator,
    create_activity_curve, create_user_segmentation_plot
)


@st.cache_data(show_spinner=False)
def load_or_generate_data(n_users: int = 200, history_days: int = 30):
    with st.spinner('正在生成模拟用户行为数据...'):
        behavior_df, labels_df, channel_df, user_cycles = generate_all_data(
            n_users=n_users, history_days=history_days, random_seed=42
        )
    return behavior_df, labels_df, channel_df, user_cycles


@st.cache_data(show_spinner=False)
def build_features(behavior_df, labels_df, user_cycles, channel_df):
    with st.spinner('正在进行特征工程 (自适应窗口)...'):
        feature_matrix, all_feature_cols = build_feature_matrix(
            behavior_df, labels_df, user_cycles=user_cycles, channel_df=channel_df
        )
        top_features = select_features_by_importance(feature_matrix, all_feature_cols, top_k=30)
    return feature_matrix, all_feature_cols, top_features


@st.cache_resource(show_spinner=False)
def train_model(feature_matrix, top_features):
    with st.spinner('正在训练XGBoost预测模型...'):
        model, eval_results = train_full_pipeline(feature_matrix, top_features)
    return model, eval_results


@st.cache_data(show_spinner=False)
def generate_predictions(_model, feature_matrix, top_features, behavior_df):
    with st.spinner('正在生成预测结果...'):
        predictions = _model.predict(feature_matrix, top_features)
        future_predictions = _model.predict_future_7d(feature_matrix, top_features)

        X = feature_matrix[top_features].fillna(0)
        shap_analyzer = SHAPAnalyzer(_model.model, top_features)
        shap_analyzer.initialize_explainer(X.values)

        churn_scorer = ChurnRiskScorer(feature_matrix)
        churn_risk = churn_scorer.calculate_churn_risk(predictions)

        rec_engine = RecommendationEngine(feature_matrix=feature_matrix)
        recommendations = rec_engine.generate_recommendations(
            feature_matrix, churn_risk, predictions
        )

        attributor = ActivityAttributor(shap_analyzer, feature_matrix)

        copy_gen = CopyGenerator(feature_matrix, behavior_df)

        comparator = GroupComparator(feature_matrix)
        comparison_df = comparator.get_comparison_dataframe()
        group_insights = comparator.get_pattern_insights()

    return predictions, future_predictions, shap_analyzer, churn_risk, recommendations, attributor, copy_gen, comparator, comparison_df, group_insights


def plot_active_curve_plotly(behavior_df, future_predictions, user_id):
    user_behavior = behavior_df[behavior_df['user_id'] == user_id].copy()
    user_behavior['date'] = pd.to_datetime(user_behavior['date'])

    user_future = future_predictions[future_predictions['user_id'] == user_id].copy()

    user_behavior['activity_score'] = (
        user_behavior['login_count'] * 20 +
        user_behavior['session_duration_minutes'] / 60 * 30 +
        user_behavior['feature_usage_count'] * 2
    )
    user_behavior['activity_score'] = np.minimum(user_behavior['activity_score'], 100)

    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=user_behavior['date'],
        y=user_behavior['activity_score'],
        mode='lines+markers',
        name='历史活跃度',
        line=dict(color='#1f77b4', width=2),
        marker=dict(size=6, color='#1f77b4'),
        hovertemplate='日期: %{x}<br>活跃度: %{y:.1f}<extra></extra>'
    ))

    last_historical = user_behavior.iloc[-1]
    first_future = user_future.iloc[0]
    fig.add_trace(go.Scatter(
        x=[last_historical['date'], first_future['date']],
        y=[last_historical['activity_score'], first_future['activity_score']],
        mode='lines',
        name='_nolegend_',
        line=dict(color='#ff7f0e', width=2, dash='dot'),
        showlegend=False
    ))

    fig.add_trace(go.Scatter(
        x=user_future['date'],
        y=user_future['activity_score'],
        mode='lines+markers',
        name='预测活跃度',
        line=dict(color='#ff7f0e', width=2, dash='dash'),
        marker=dict(size=8, color='#ff7f0e', symbol='square'),
        hovertemplate='日期: %{x}<br>预测活跃度: %{y:.1f}<br>等级: %{customdata}<extra></extra>',
        customdata=user_future['predicted_level'].values
    ))

    fig.add_hline(y=60, line_dash="dot", line_color="green",
                  annotation_text="高活跃阈值 (60)", annotation_position="right")
    fig.add_hline(y=25, line_dash="dot", line_color="red",
                  annotation_text="低活跃阈值 (25)", annotation_position="right")

    fig.update_layout(
        title=f'用户 {user_id} 活跃度曲线 - 历史30天 & 未来7天预测',
        xaxis_title='日期',
        yaxis_title='活跃度评分',
        yaxis_range=[0, 105],
        hovermode='x unified',
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        height=500
    )

    return fig


def plot_user_segmentation_plotly(predictions, churn_risk):
    merged = predictions.merge(churn_risk, on='user_id')

    color_map = {'high': '#2ca02c', 'medium': '#ff7f0e', 'low': '#d62728'}

    fig = go.Figure()

    for level in ['high', 'medium', 'low']:
        subset = merged[merged['predicted_level'] == level]
        fig.add_trace(go.Scatter(
            x=subset['activity_score'],
            y=subset['churn_risk_score'],
            mode='markers',
            name=f'预测{level}活跃',
            marker=dict(
                color=color_map[level],
                size=10,
                line=dict(width=1, color='white')
            ),
            text=subset['user_id'],
            hovertemplate=(
                '用户: %{text}<br>'
                '活跃度: %{x:.1f}<br>'
                '流失风险: %{y:.1f}<extra></extra>'
            )
        ))

    fig.add_vline(x=60, line_dash="dash", line_color="gray", opacity=0.5)
    fig.add_vline(x=25, line_dash="dash", line_color="gray", opacity=0.5)
    fig.add_hline(y=70, line_dash="dash", line_color="red", opacity=0.5)
    fig.add_hline(y=40, line_dash="dash", line_color="orange", opacity=0.5)

    fig.add_annotation(x=80, y=85, text="高活跃高风险", showarrow=False, font=dict(color="red", size=11))
    fig.add_annotation(x=80, y=15, text="高活跃低风险<br>(核心用户)", showarrow=False, font=dict(color="green", size=11))
    fig.add_annotation(x=10, y=85, text="低活跃高风险<br>(流失预警)", showarrow=False, font=dict(color="red", size=11))
    fig.add_annotation(x=10, y=15, text="低活跃低风险", showarrow=False, font=dict(color="gray", size=11))

    fig.update_layout(
        title='用户分群矩阵 - 活跃度 vs 流失风险',
        xaxis_title='预测活跃度评分',
        yaxis_title='流失风险评分',
        height=600,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )

    return fig


def plot_feature_importance_plotly(feature_importance_df, top_k=15):
    df = feature_importance_df.head(top_k).copy()

    fig = go.Figure(go.Bar(
        x=df['importance'],
        y=df['feature'],
        orientation='h',
        marker=dict(color=df['importance'], colorscale='Viridis'),
        hovertemplate='特征: %{y}<br>重要性: %{x:.4f}<extra></extra>'
    ))

    fig.update_layout(
        title=f'Top {top_k} 特征重要性 (XGBoost)',
        xaxis_title='重要性',
        yaxis_title='特征',
        yaxis=dict(autorange='reversed'),
        height=500
    )

    return fig


def plot_shap_importance_plotly(shap_importance_df, top_k=15):
    df = shap_importance_df.head(top_k).copy()

    fig = go.Figure(go.Bar(
        x=df['shap_importance'],
        y=df['feature'],
        orientation='h',
        marker=dict(color=df['shap_importance'], colorscale='RdYlGn_r'),
        hovertemplate='特征: %{y}<br>SHAP重要性: %{x:.4f}<extra></extra>'
    ))

    fig.update_layout(
        title=f'Top {top_k} SHAP特征重要性',
        xaxis_title='平均|SHAP值|',
        yaxis_title='特征',
        yaxis=dict(autorange='reversed'),
        height=500
    )

    return fig


def plot_risk_distribution(churn_risk):
    risk_counts = churn_risk['risk_level'].value_counts().reindex(['high', 'medium', 'low'])

    fig = go.Figure(data=[go.Pie(
        labels=['高风险', '中风险', '低风险'],
        values=risk_counts.values,
        hole=0.4,
        marker=dict(colors=['#d62728', '#ff7f0e', '#2ca02c']),
        textinfo='label+percent',
        textfont_size=14
    )])

    fig.update_layout(
        title='用户流失风险分布',
        annotations=[dict(text='风险等级', x=0.5, y=0.5, font_size=16, showarrow=False)]
    )

    return fig


def plot_active_level_distribution(predictions):
    level_counts = predictions['predicted_level'].value_counts().reindex(['high', 'medium', 'low'])

    fig = go.Figure(data=[go.Bar(
        x=['高活跃', '中活跃', '低活跃'],
        y=level_counts.values,
        marker_color=['#2ca02c', '#ff7f0e', '#d62728'],
        text=level_counts.values,
        textposition='auto',
    )])

    fig.update_layout(
        title='未来7天预测活跃等级分布',
        xaxis_title='活跃等级',
        yaxis_title='用户数',
        height=400
    )

    return fig


def get_risk_color(level):
    if level == 'high':
        return '#d62728'
    elif level == 'medium':
        return '#ff7f0e'
    else:
        return '#2ca02c'


def get_active_color(level):
    if level == 'high':
        return '#2ca02c'
    elif level == 'medium':
        return '#ff7f0e'
    else:
        return '#d62728'


def main():
    st.title("📊 用户活跃度预测系统")
    st.markdown("---")

    with st.sidebar:
        st.header("⚙️ 系统设置")

        n_users = st.slider("模拟用户数量", min_value=50, max_value=500, value=200, step=50)
        history_days = st.slider("历史数据天数", min_value=14, max_value=60, value=30, step=7)

        st.markdown("---")
        st.header("👤 用户筛选")

        risk_filter = st.multiselect(
            "流失风险等级",
            options=['high', 'medium', 'low'],
            default=['high', 'medium', 'low'],
            format_func=lambda x: {'high': '高风险', 'medium': '中风险', 'low': '低风险'}[x]
        )

        active_filter = st.multiselect(
            "预测活跃等级",
            options=['high', 'medium', 'low'],
            default=['high', 'medium', 'low'],
            format_func=lambda x: {'high': '高活跃', 'medium': '中活跃', 'low': '低活跃'}[x]
        )

        st.markdown("---")
        if st.button("🔄 重新生成数据", type="primary"):
            st.cache_data.clear()
            st.cache_resource.clear()
            st.rerun()

    try:
        behavior_df, labels_df, channel_df, user_cycles = load_or_generate_data(n_users=n_users, history_days=history_days)
        feature_matrix, all_feature_cols, top_features = build_features(behavior_df, labels_df, user_cycles, channel_df)
        model, eval_results = train_model(feature_matrix, top_features)
        predictions, future_predictions, shap_analyzer, churn_risk, recommendations, attributor, copy_gen, comparator, comparison_df, group_insights = generate_predictions(
            model, feature_matrix, top_features, behavior_df
        )

        merged_data = predictions.merge(churn_risk, on='user_id').merge(recommendations, on='user_id')

        filtered_data = merged_data[
            merged_data['risk_level'].isin(risk_filter) &
            merged_data['predicted_level'].isin(active_filter)
        ]

        tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8 = st.tabs([
            "📈 总览看板",
            "👤 用户详情",
            "📉 活跃曲线",
            "⚠️ 流失风险",
            "📊 活跃度归因",
            "✍️ 促活文案",
            "📋 群组对比",
            "🔍 模型解释"
        ])

        with tab1:
            st.header("📈 数据总览")

            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric(
                    "总用户数",
                    f"{len(filtered_data):,}",
                    delta=f"准确率: {eval_results['accuracy']:.1%}"
                )
            with col2:
                high_risk_count = (filtered_data['risk_level'] == 'high').sum()
                st.metric(
                    "高流失风险用户",
                    f"{high_risk_count:,}",
                    delta=f"{high_risk_count/len(filtered_data):.1%}",
                    delta_color="inverse"
                )
            with col3:
                high_active_count = (filtered_data['predicted_level'] == 'high').sum()
                st.metric(
                    "预测高活跃用户",
                    f"{high_active_count:,}",
                    delta=f"{high_active_count/len(filtered_data):.1%}"
                )
            with col4:
                avg_risk = filtered_data['churn_risk_score'].mean()
                st.metric(
                    "平均流失风险",
                    f"{avg_risk:.1f}",
                    delta="需关注" if avg_risk > 40 else "健康",
                    delta_color="inverse" if avg_risk > 40 else "normal"
                )

            st.markdown("---")

            col5, col6 = st.columns(2)
            with col5:
                st.plotly_chart(plot_active_level_distribution(predictions), use_container_width=True)
            with col6:
                st.plotly_chart(plot_risk_distribution(churn_risk), use_container_width=True)

            st.markdown("---")
            st.subheader("🔍 模型性能")

            col7, col8 = st.columns(2)
            with col7:
                st.metric("测试集准确率", f"{eval_results['accuracy']:.2%}")
                st.metric("加权F1分数", f"{eval_results['f1_weighted']:.4f}")
            with col8:
                st.metric("加权精确率", f"{eval_results['precision_weighted']:.4f}")
                st.metric("加权召回率", f"{eval_results['recall_weighted']:.4f}")

            st.plotly_chart(
                plot_feature_importance_plotly(eval_results['feature_importance'], top_k=15),
                use_container_width=True
            )

        with tab2:
            st.header("👤 用户详情分析")

            user_list = sorted(filtered_data['user_id'].tolist())
            selected_user = st.selectbox(
                "选择用户",
                options=user_list,
                format_func=lambda x: f"{x}"
            )

            if selected_user:
                user_data = filtered_data[filtered_data['user_id'] == selected_user].iloc[0]
                user_features = feature_matrix[feature_matrix['user_id'] == selected_user].iloc[0]

                col9, col10, col11 = st.columns(3)
                with col9:
                    active_color = get_active_color(user_data['predicted_level'])
                    st.markdown(f"""
                    <div style="padding: 20px; border-radius: 10px; background-color: {active_color}20; border: 2px solid {active_color};">
                        <h3 style="margin: 0; color: {active_color};">预测活跃等级</h3>
                        <h1 style="margin: 10px 0 0 0; color: {active_color};">
                            {'高' if user_data['predicted_level'] == 'high' else '中' if user_data['predicted_level'] == 'medium' else '低'}
                        </h1>
                        <p style="margin: 5px 0 0 0; font-size: 14px;">
                            活跃度评分: <b>{user_data['activity_score']:.1f}</b>
                        </p>
                    </div>
                    """, unsafe_allow_html=True)

                with col10:
                    risk_color = get_risk_color(user_data['risk_level'])
                    st.markdown(f"""
                    <div style="padding: 20px; border-radius: 10px; background-color: {risk_color}20; border: 2px solid {risk_color};">
                        <h3 style="margin: 0; color: {risk_color};">流失风险等级</h3>
                        <h1 style="margin: 10px 0 0 0; color: {risk_color};">
                            {'高' if user_data['risk_level'] == 'high' else '中' if user_data['risk_level'] == 'medium' else '低'}
                        </h1>
                        <p style="margin: 5px 0 0 0; font-size: 14px;">
                            风险评分: <b>{user_data['churn_risk_score']:.1f}</b>
                        </p>
                    </div>
                    """, unsafe_allow_html=True)

                with col11:
                    st.markdown(f"""
                    <div style="padding: 20px; border-radius: 10px; background-color: #1f77b420; border: 2px solid #1f77b4;">
                        <h3 style="margin: 0; color: #1f77b4;">预测置信度</h3>
                        <h1 style="margin: 10px 0 0 0; color: #1f77b4;">
                            {user_data['confidence']:.1%}
                        </h1>
                        <p style="margin: 5px 0 0 0; font-size: 14px;">
                            模型信心: <b>{'高' if user_data['confidence'] > 0.8 else '中' if user_data['confidence'] > 0.5 else '低'}</b>
                        </p>
                    </div>
                    """, unsafe_allow_html=True)

                st.markdown("---")
                st.subheader("📊 用户行为特征")

                col12, col13, col14, col15 = st.columns(4)
                col12.metric("登录频率", f"{user_features['login_frequency']:.1%}")
                col13.metric("距上次登录", f"{int(user_features['days_since_last_login'])} 天")
                col14.metric("平均会话时长", f"{user_features['avg_session_duration']:.1f} 分钟")
                col15.metric("功能多样性", f"{user_features['feature_diversity_score']:.1%}")

                col16, col17, col18, col19 = st.columns(4)
                col16.metric("近7天活跃天数", f"{int(user_features['active_days_last_7d'])} 天")
                col17.metric("近14天活跃天数", f"{int(user_features['active_days_last_14d'])} 天")
                col18.metric("当前登录连续", f"{int(user_features['current_login_streak'])} 天")
                col19.metric("最长登录连续", f"{int(user_features['max_login_streak'])} 天")

                st.markdown("---")
                st.subheader("🔄 自适应周期 & 渠道偏好")

                col_cycle1, col_cycle2 = st.columns(2)
                with col_cycle1:
                    if 'detected_cycle_days' in user_features.index:
                        cycle_days = int(user_features['detected_cycle_days'])
                        st.metric("检测活跃周期", f"{cycle_days} 天",
                                  delta="短周期→高活跃" if cycle_days <= 3 else "长周期→需关注")
                    else:
                        st.metric("检测活跃周期", "N/A")

                with col_cycle2:
                    if 'preferred_channel' in user_features.index:
                        pref_ch = user_features['preferred_channel']
                        ch_names = {'email': '邮件', 'push': '推送', 'sms': '短信',
                                    'in_app': '产品内', 'wechat': '微信', 'community': '社区'}
                        pref_name = ch_names.get(pref_ch, pref_ch)
                        sec_ch = user_features.get('second_channel', 'email')
                        sec_name = ch_names.get(sec_ch, sec_ch)
                        st.metric("偏好触达渠道", f"{pref_name} + {sec_name}")
                    else:
                        st.metric("偏好触达渠道", "推送 + 邮件")

                if 'channel_diversity' in user_features.index:
                    ch_div = user_features['channel_diversity']
                    st.caption(f"渠道多样性: {ch_div:.1%} — {'用户偏好集中' if ch_div < 0.3 else '用户多渠道活跃'}")

                st.markdown("---")
                st.subheader("⚠️ 风险因素")
                for factor in user_data['risk_factors']:
                    st.warning(f"🔴 {factor}")

                st.markdown("---")
                st.subheader("📋 触达建议")

                for i, rec in enumerate(user_data['recommendations'], 1):
                    priority_color = {'高': '#d62728', '中': '#ff7f0e', '低': '#2ca02c'}.get(rec['priority'], '#1f77b4')
                    with st.expander(f"建议 {i}: {rec['title']}"):
                        channel_detail = rec.get('channel_preference_detail', {})
                        conf_label = channel_detail.get('confidence', 'medium')
                        conf_color = '#2ca02c' if conf_label == 'high' else '#ff7f0e'
                        original_ch = rec.get('original_channel', rec['channel'])

                        st.markdown(f"""
                        **优先级**: <span style="color:{priority_color}; font-weight:bold;">{rec['priority']}</span>
                        <br>
                        **推荐触达渠道**: <span style="color:{conf_color}; font-weight:bold;">{rec['channel']}</span>
                        {'(基于用户偏好学习)' if 'preferred_channel' in rec else ''}
                        <br>
                        **默认渠道**: {original_ch}
                        <br>
                        **建议内容**: {rec['suggestion']}
                        """, unsafe_allow_html=True)

                        if channel_detail:
                            ch_names = {'email': '邮件', 'push': '推送', 'sms': '短信',
                                        'in_app': '产品内', 'wechat': '微信', 'community': '社区'}
                            primary = ch_names.get(channel_detail.get('primary_channel', ''), channel_detail.get('primary_channel', ''))
                            secondary = ch_names.get(channel_detail.get('secondary_channel', ''), channel_detail.get('secondary_channel', ''))
                            st.caption(f"偏好置信度: {conf_label} | 主渠道: {primary} | 辅渠道: {secondary}")

        with tab3:
            st.header("📉 活跃度曲线分析")

            user_list_curve = sorted(filtered_data['user_id'].tolist())
            selected_user_curve = st.selectbox(
                "选择用户查看曲线",
                options=user_list_curve,
                key="curve_user",
                format_func=lambda x: f"{x}"
            )

            if selected_user_curve:
                st.plotly_chart(
                    plot_active_curve_plotly(behavior_df, future_predictions, selected_user_curve),
                    use_container_width=True
                )

                user_future = future_predictions[future_predictions['user_id'] == selected_user_curve]
                st.subheader("📅 未来7天详细预测")

                future_display = user_future[['date', 'activity_score', 'predicted_level']].copy()
                future_display['date'] = future_display['date'].dt.strftime('%Y-%m-%d')
                future_display.columns = ['日期', '预测活跃度', '预测等级']

                def highlight_level(s):
                    return [f'color: {get_active_color(v)}; font-weight: bold'
                            if v in ['high', 'medium', 'low'] else '' for v in s]

                st.dataframe(
                    future_display.style.apply(highlight_level, subset=['预测等级']),
                    use_container_width=True,
                    hide_index=True
                )

            st.markdown("---")
            st.subheader("👥 用户分群矩阵")
            st.plotly_chart(
                plot_user_segmentation_plotly(predictions, churn_risk),
                use_container_width=True
            )

        with tab4:
            st.header("⚠️ 流失风险分析 (分群独立阈值)")

            st.info("""
            **分群独立阈值说明**：不同用户群体使用不同的风险判定标准。
            - 🔴 高活跃用户：高风险阈值50，中风险阈值25（更敏感，稍有下降即预警）
            - 🟠 中活跃用户：高风险阈值60，中风险阈值30
            - 🟡 低活跃用户：高风险阈值70，中风险阈值40
            - ⚪ 流失风险用户：高风险阈值70，中风险阈值40（更宽容）
            """)

            col20, col21 = st.columns(2)
            with col20:
                risk_score_hist = px.histogram(
                    churn_risk, x='churn_risk_score', nbins=20,
                    title='流失风险评分分布',
                    color_discrete_sequence=['#ff7f0e']
                )
                risk_score_hist.add_vline(x=70, line_dash="dash", line_color="red",
                                          annotation_text="高风险阈值")
                risk_score_hist.add_vline(x=40, line_dash="dash", line_color="orange",
                                          annotation_text="中风险阈值")
                st.plotly_chart(risk_score_hist, use_container_width=True)

            with col21:
                avg_risk_by_level = filtered_data.groupby('predicted_level')['churn_risk_score'].mean().reset_index()
                avg_risk_by_level['predicted_level'] = avg_risk_by_level['predicted_level'].map(
                    {'high': '高活跃', 'medium': '中活跃', 'low': '低活跃'}
                )
                avg_risk_fig = px.bar(
                    avg_risk_by_level, x='predicted_level', y='churn_risk_score',
                    title='各活跃等级平均流失风险',
                    color='predicted_level',
                    color_discrete_map={'高活跃': '#2ca02c', '中活跃': '#ff7f0e', '低活跃': '#d62728'}
                )
                st.plotly_chart(avg_risk_fig, use_container_width=True)

            st.markdown("---")
            st.subheader("📋 高风险用户列表 (需立即关注)")

            high_risk_users = filtered_data[filtered_data['risk_level'] == 'high'].copy()
            high_risk_users = high_risk_users.sort_values('churn_risk_score', ascending=False)

            display_cols = [
                'user_id', 'predicted_level', 'activity_score',
                'churn_risk_score', 'risk_factors'
            ]
            high_risk_display = high_risk_users[display_cols].copy()
            high_risk_display.columns = [
                '用户ID', '预测等级', '活跃度', '风险评分', '风险因素'
            ]
            high_risk_display['风险因素'] = high_risk_display['风险因素'].apply(
                lambda x: '; '.join(x)
            )

            st.dataframe(
                high_risk_display.style.format({
                    '活跃度': '{:.1f}',
                    '风险评分': '{:.1f}'
                }).applymap(
                    lambda v: f'color: {get_active_color(v)}; font-weight: bold',
                    subset=['预测等级']
                ),
                use_container_width=True,
                hide_index=True
            )

            st.markdown("---")
            st.subheader("📈 批量触达建议")

            risk_summary = filtered_data.groupby('risk_level').agg({
                'user_id': 'count',
                'churn_risk_score': 'mean'
            }).reset_index()
            risk_summary['risk_level'] = risk_summary['risk_level'].map(
                {'high': '高风险', 'medium': '中风险', 'low': '低风险'}
            )

            for _, row in risk_summary.iterrows():
                if row['risk_level'] == '高风险':
                    st.error(f"""
                    **{row['risk_level']}用户群 ({int(row['user_id'])}人, 平均风险 {row['churn_risk_score']:.1f})**
                    - 建议立即启动召回计划，发送个性化召回邮件和推送
                    - 提供专属回归优惠，如会员延长、功能解锁等
                    - 安排客服主动联系，了解流失原因
                    """)
                elif row['risk_level'] == '中风险':
                    st.warning(f"""
                    **{row['risk_level']}用户群 ({int(row['user_id'])}人, 平均风险 {row['churn_risk_score']:.1f})**
                    - 建议发送参与度提升邮件，推荐新功能和使用技巧
                    - 启动功能引导计划，展示更多产品价值
                    - 邀请参与用户调研，收集产品反馈
                    """)
                else:
                    st.success(f"""
                    **{row['risk_level']}用户群 ({int(row['user_id'])}人, 平均风险 {row['churn_risk_score']:.1f})**
                    - 建议维持现有互动频率，持续培养用户习惯
                    - 高活跃用户可邀请加入忠诚用户计划
                    - 中低活跃用户可推送个性化内容推荐
                    """)

        with tab5:
            st.header("📊 活跃度归因分析")
            st.info("基于SHAP值分析影响用户活跃度的关键行为，识别正向驱动因素和负向拖累因素")

            user_list_attr = sorted(filtered_data['user_id'].tolist())
            selected_user_attr = st.selectbox(
                "选择用户查看归因分析",
                options=user_list_attr,
                key="attr_user",
                format_func=lambda x: f"{x}"
            )

            if selected_user_attr:
                attr_result = attributor.attribute_user(selected_user_attr, top_k=8)

                st.markdown(f"### 📝 归因总结")
                st.success(f"**{attr_result['summary']}**")

                st.markdown("---")
                st.subheader("🔍 关键行为归因")

                attr_df = pd.DataFrame(attr_result['attributions'])
                if len(attr_df) > 0:
                    attr_df['颜色'] = attr_df['direction'].apply(
                        lambda x: '#2ca02c' if x == 'positive' else '#d62728'
                    )

                    col_pos, col_neg = st.columns(2)

                    with col_pos:
                        st.markdown("#### ✅ 正向驱动因素")
                        pos_attr = attr_df[attr_df['direction'] == 'positive']
                        if len(pos_attr) > 0:
                            for _, row in pos_attr.iterrows():
                                st.markdown(f"""
                                <div style="padding: 10px; margin: 5px 0; border-radius: 8px; background-color: #2ca02c15; border-left: 4px solid #2ca02c;">
                                    <b>{row['behavior']}</b>
                                    <br><span style="font-size: 12px;">
                                    影响强度: {row['impact_label']} | SHAP值: {row['shap_value']:.4f}
                                    <br>{row['description']}
                                    </span>
                                </div>
                                """, unsafe_allow_html=True)
                        else:
                            st.info("无明显正向驱动因素")

                    with col_neg:
                        st.markdown("#### ⚠️ 负向拖累因素")
                        neg_attr = attr_df[attr_df['direction'] == 'negative']
                        if len(neg_attr) > 0:
                            for _, row in neg_attr.iterrows():
                                st.markdown(f"""
                                <div style="padding: 10px; margin: 5px 0; border-radius: 8px; background-color: #d6272815; border-left: 4px solid #d62728;">
                                    <b>{row['behavior']}</b>
                                    <br><span style="font-size: 12px;">
                                    影响强度: {row['impact_label']} | SHAP值: {row['shap_value']:.4f}
                                    <br>{row['description']}
                                    </span>
                                </div>
                                """, unsafe_allow_html=True)
                        else:
                            st.info("无明显负向拖累因素")

                st.markdown("---")
                st.subheader("📈 分类别影响汇总")
                cat_impact = attr_result['category_impact']
                if cat_impact:
                    cat_rows = []
                    for cat, data in cat_impact.items():
                        cat_rows.append({
                            '影响类别': cat,
                            '正向影响': round(data['positive'], 4),
                            '负向影响': round(data['negative'], 4),
                            '净影响': round(data['net_impact'], 4),
                            '主导方向': '正向' if data['dominant'] == 'positive' else '负向',
                            '说明': data['description']
                        })
                    cat_df = pd.DataFrame(cat_rows)
                    st.dataframe(
                        cat_df.style.applymap(
                            lambda v: 'color: #2ca02c; font-weight: bold' if v == '正向' else
                                     'color: #d62728; font-weight: bold' if v == '负向' else '',
                            subset=['主导方向']
                        ),
                        use_container_width=True,
                        hide_index=True
                    )

        with tab6:
            st.header("✍️ 个性化促活文案生成")
            st.info("根据用户行为模式和画像特征，自动生成个性化促活文案")

            user_list_copy = sorted(filtered_data['user_id'].tolist())
            selected_user_copy = st.selectbox(
                "选择用户生成文案",
                options=user_list_copy,
                key="copy_user",
                format_func=lambda x: f"{x}"
            )

            if selected_user_copy:
                user_attr = attributor.attribute_user(selected_user_copy, top_k=5)
                copy_result = copy_gen.generate_copy(selected_user_copy, user_attr)

                user_segment = feature_matrix[feature_matrix['user_id'] == selected_user_copy]['user_segment'].iloc[0]
                segment_names = {
                    'high_active': '高活跃用户',
                    'medium_active': '中活跃用户',
                    'low_active': '低活跃用户',
                    'churn_risk': '流失风险用户'
                }

                col_profile, col_primary = st.columns([1, 2])

                with col_profile:
                    st.markdown("### 👤 用户画像")
                    st.info(f"""
                    **用户分群**: {segment_names.get(user_segment, user_segment)}
                    <br>**文案语气**: {copy_result['tone']}
                    <br>**问候风格**: {copy_result['greeting']}
                    """, unsafe_allow_html=True)

                with col_primary:
                    st.markdown("### 🎯 主推文案")
                    st.success(f"### {copy_result['primary_copy']}")
                    st.caption("此文案已根据用户特征和归因分析自动优化")

                st.markdown("---")
                st.subheader("📝 备选文案方案")

                for i, copy_item in enumerate(copy_result['copies'], 1):
                    with st.expander(f"方案 {i}: {copy_item['behavior_type']} ({copy_item['level_label']})"):
                        st.markdown(f"""
                        **文案内容**: {copy_item['copy']}
                        <br>**行为维度**: {copy_item['behavior_type']}
                        <br>**用户水平**: {copy_item['level_label']}
                        <br>**对应指标**: {copy_item['metric_value']}
                        """, unsafe_allow_html=True)

                st.markdown("---")
                st.subheader("💡 文案使用建议")
                st.info("""
                1. **主推文案**可直接用于短信/推送通知标题
                2. **备选文案**可作为邮件正文/APP内消息的不同版本进行A/B测试
                3. 建议结合**渠道偏好**选择最佳触达渠道
                4. 可根据活动目标调整文案侧重点（召回/活跃/转化）
                """)

        with tab7:
            st.header("📋 群组对比分析")
            st.info("对比不同用户群体的活跃模式差异，识别提升机会点")

            st.markdown("### 📊 核心指标对比")
            if len(comparison_df) > 0:
                st.dataframe(
                    comparison_df.style.applymap(
                        lambda x: 'color: #2ca02c' if '高活跃用户' in str(x) else
                                 'color: #d62728' if '流失风险用户' in str(x) else '',
                        subset=['指标']
                    ),
                    use_container_width=True,
                    hide_index=True
                )
            else:
                st.warning("暂无对比数据")

            st.markdown("---")
            st.subheader("🔍 差异洞察与建议")

            if group_insights:
                for i, insight in enumerate(group_insights, 1):
                    severity_color = {'high': '#d62728', 'medium': '#ff7f0e', 'low': '#2ca02c'}.get(insight['severity'], '#1f77b4')
                    severity_label = {'high': '高', 'medium': '中', 'low': '低'}.get(insight['severity'], '中')

                    with st.expander(f"洞察 {i}: {insight['metric']} (优先级: {severity_label})"):
                        st.markdown(f"""
                        <div style="padding: 15px; border-radius: 8px; background-color: {severity_color}15; border-left: 4px solid {severity_color};">
                            <b>现象</b>: {insight['insight']}
                            <br><b>建议</b>: {insight['recommendation']}
                        </div>
                        """, unsafe_allow_html=True)
            else:
                st.success("各群体表现均衡，无显著差异")

            st.markdown("---")
            st.subheader("📈 可视化对比")

            viz_metric = st.selectbox(
                "选择对比指标",
                options=['登录频率', '平均会话时长(分钟)', '功能多样性', '近7天活跃天数', '距上次登录(天)']
            )

            metric_col_map = {
                '登录频率': 'login_frequency',
                '平均会话时长(分钟)': 'avg_session_duration',
                '功能多样性': 'feature_diversity_score',
                '近7天活跃天数': 'active_days_last_7d',
                '距上次登录(天)': 'days_since_last_login',
            }
            metric_col = metric_col_map.get(viz_metric, 'login_frequency')

            if metric_col in feature_matrix.columns:
                viz_data = feature_matrix.groupby('user_segment')[metric_col].mean().reset_index()
                viz_data['segment_name'] = viz_data['user_segment'].map({
                    'high_active': '高活跃', 'medium_active': '中活跃',
                    'low_active': '低活跃', 'churn_risk': '流失风险'
                })

                viz_fig = go.Figure(go.Bar(
                    x=viz_data['segment_name'],
                    y=viz_data[metric_col],
                    marker_color=['#2ca02c', '#ff7f0e', '#d62728', '#9467bd'],
                    text=viz_data[metric_col].round(2),
                    textposition='auto',
                ))
                viz_fig.update_layout(
                    title=f'各群体{viz_metric}对比',
                    yaxis_title=viz_metric,
                    height=400
                )
                st.plotly_chart(viz_fig, use_container_width=True)

        with tab8:
            st.header("🔍 模型可解释性分析 (SHAP)")

            shap_importance = shap_analyzer.get_feature_importance(feature_matrix, top_k=20)
            st.plotly_chart(
                plot_shap_importance_plotly(shap_importance, top_k=15),
                use_container_width=True
            )

            st.markdown("---")
            st.subheader("📊 SHAP Summary Plot")
            with st.spinner('生成SHAP分析图表...'):
                summary_buf = shap_analyzer.get_summary_plot(feature_matrix, max_display=15)
                st.image(summary_buf, use_container_width=True, caption='SHAP特征重要性蜂群图')

            st.markdown("---")
            st.subheader("👤 单用户SHAP Force Plot")

            user_list_shap = sorted(filtered_data['user_id'].tolist())
            selected_user_shap = st.selectbox(
                "选择用户查看SHAP解释",
                options=user_list_shap,
                key="shap_user",
                format_func=lambda x: f"{x}"
            )

            if selected_user_shap:
                user_idx = feature_matrix[feature_matrix['user_id'] == selected_user_shap].index[0]

                col22, col23 = st.columns([1, 1])
                with col22:
                    force_buf = shap_analyzer.get_force_plot(feature_matrix, user_idx=user_idx)
                    st.image(force_buf, use_container_width=True, caption='SHAP Force Plot')

                with col23:
                    user_shap = shap_analyzer.get_user_shap_values(feature_matrix, user_idx=user_idx)
                    user_shap['影响方向'] = user_shap['shap_value'].apply(
                        lambda x: '正向' if x > 0 else '负向'
                    )
                    user_shap['shap_abs'] = user_shap['shap_value'].abs()

                    st.dataframe(
                        user_shap[['feature', 'feature_value', 'shap_value', '影响方向']].head(10).style.format({
                            'feature_value': '{:.3f}',
                            'shap_value': '{:.4f}'
                        }).applymap(
                            lambda v: 'color: green' if v == '正向' else 'color: red',
                            subset=['影响方向']
                        ),
                        use_container_width=True,
                        hide_index=True
                    )

                    st.info("💡 **SHAP值解释**: 正值表示该特征推高了预测结果，负值表示该特征拉低了预测结果。绝对值越大，影响越强。")

    except Exception as e:
        st.error(f"系统运行出错: {str(e)}")
        st.exception(e)
        st.info("请点击左侧'重新生成数据'按钮重试。")


if __name__ == '__main__':
    main()
