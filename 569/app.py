import streamlit as st
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import plotly.graph_objects as go
import plotly.express as px
from io import BytesIO
import sys
import os
import warnings
warnings.filterwarnings('ignore')

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.features.data_generator import (
    generate_full_dataset, load_datasets, save_datasets,
    SKILL_GROUPS, SKILL_GROUP_ORDER, get_target_columns_by_group
)
from src.features.preprocessing import (
    prepare_single_prediction, FEATURE_COLUMNS, 
    FeatureEngineer
)
from src.models.xgboost_model import (
    GroupedDifficultyModel, train_grouped_pipeline,
    SingleGroupModel
)
from src.analysis.shap_analysis import SHAPAnalyzer
from src.analysis.difficulty_scorer import (
    DifficultyScorer, DifficultyScore, DIFFICULTY_RATINGS,
    DEATH_ZONE_NAMES
)
from src.analysis.ab_testing import (
    ABTestAnalyzer, ABTestResult, simulate_ab_test_from_levels,
    generate_ab_test_report
)
from src.analysis.dynamic_difficulty import (
    DynamicDifficultyAdjuster, PlayerPerformance, DynamicAdjustmentResult
)
from src.analysis.level_generator import (
    LevelGenerator, GenerationConstraints, GeneratedLevel, LEVEL_TYPES
)
from src.analysis.churn_prediction import (
    ChurnPredictor, PlayerBehaviorData, ChurnPredictionResult
)

st.set_page_config(
    page_title="游戏关卡难度预测系统 - 分群版",
    page_icon="🎮",
    layout="wide",
    initial_sidebar_state="expanded"
)

plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'Arial Unicode MS']
plt.rcParams['axes.unicode_minus'] = False


@st.cache_resource(show_spinner="正在加载分群模型和数据...")
def load_or_train_grouped_model(force_retrain: bool = False):
    model_dir = "models"
    data_dir = "data"
    
    if not force_retrain:
        try:
            df_levels, df_players = load_datasets(data_dir)
            model = GroupedDifficultyModel.load(model_dir)
            engineer = FeatureEngineer.load(os.path.join(model_dir, 'feature_engineer.pkl'))
            
            if df_levels is None or df_players is None:
                raise FileNotFoundError("数据文件不存在")
            
            return model, engineer, df_levels, df_players
        except Exception as e:
            print(f"加载现有模型失败: {e}")
    
    with st.spinner("正在生成数据并训练分群模型..."):
        df_levels, df_players = generate_full_dataset(n_levels=200, n_players=1000)
        save_datasets(df_levels, df_players, data_dir)
        
        model, data_by_group = train_grouped_pipeline(
            df_levels, FEATURE_COLUMNS, use_actual=True, model_dir=model_dir
        )
        engineer = data_by_group[SKILL_GROUP_ORDER[0]]['engineer']
        
        return model, engineer, df_levels, df_players


def create_gauge_chart(value: float, title: str, max_val: float = 100, 
                       color: str = '#3498db') -> go.Figure:
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=value,
        domain={'x': [0, 1], 'y': [0, 1]},
        title={'text': title, 'font': {'size': 14}},
        gauge={
            'axis': {'range': [None, max_val]},
            'bar': {'color': color},
            'steps': [
                {'range': [0, max_val * 0.25], 'color': '#d4edda'},
                {'range': [max_val * 0.25, max_val * 0.5], 'color': '#fff3cd'},
                {'range': [max_val * 0.5, max_val * 0.75], 'color': '#ffeeba'},
                {'range': [max_val * 0.75, max_val], 'color': '#f8d7da'},
            ],
        }
    ))
    fig.update_layout(height=220, margin=dict(l=10, r=10, t=40, b=10))
    return fig


def create_radar_chart(scores_by_group: Dict[str, DifficultyScore]) -> go.Figure:
    categories = ['通关率得分', '尝试次数得分', '行为特征得分', '综合难度']
    
    fig = go.Figure()
    
    for group in SKILL_GROUP_ORDER:
        if group not in scores_by_group:
            continue
        score = scores_by_group[group]
        group_name = SKILL_GROUPS[group]['name']
        color = SKILL_GROUPS[group]['color']
        
        completion_score = (1 - score.completion_rate) * 100
        attempts_score = min(score.avg_attempts / 10 * 100, 100)
        behavioral_score = score.components.get('behavioral_score', 0)
        
        values = [completion_score, attempts_score, behavioral_score, score.score]
        
        fig.add_trace(go.Scatterpolar(
            r=values,
            theta=categories,
            fill='toself',
            name=group_name,
            line=dict(color=color),
            fillcolor=color,
            opacity=0.3
        ))
    
    fig.update_layout(
        polar=dict(
            radialaxis=dict(
                visible=True,
                range=[0, 100]
            )
        ),
        showlegend=True,
        title="各玩家分群难度构成雷达图"
    )
    
    return fig


def create_behavioral_chart(behavioral_data, group: str) -> go.Figure:
    death_zones = behavioral_data.death_zones
    zone_names = list(death_zones.keys())
    zone_values = [v * 100 for v in death_zones.values()]
    
    colors = ['#ef4444', '#f97316', '#eab308', '#84cc16', '#3b82f6']
    
    fig = go.Figure(go.Bar(
        x=zone_names,
        y=zone_values,
        marker_color=colors,
        text=[f"{v:.1f}%" for v in zone_values],
        textposition='auto',
    ))
    
    fig.update_layout(
        title=f"{SKILL_GROUPS[group]['name']} - 各区域死亡密度 (%)",
        xaxis_title="死亡区域",
        yaxis_title="死亡密度 (%)",
        yaxis=dict(range=[0, 80]),
        height=350
    )
    
    return fig


def main():
    st.sidebar.title("🎮 游戏关卡难度预测系统")
    st.sidebar.markdown("### 分群建模版")
    st.sidebar.markdown("---")
    
    page = st.sidebar.radio(
        "导航",
        ["📊 数据概览", "🎯 分群预测", "📈 难度评分", "💡 SHAP分析", "🧪 A/B测试", "📋 批量评估",
         "⚙️ 动态难度调整", "🎲 关卡生成", "⚠️ 流失预警"]
    )
    
    st.sidebar.markdown("---")
    
    force_retrain = st.sidebar.button("🔄 重新训练分群模型", key="retrain_btn")
    
    model, engineer, df_levels, df_players = load_or_train_grouped_model(force_retrain)
    
    if page == "📊 数据概览":
        data_overview_page(df_levels, df_players)
    elif page == "🎯 分群预测":
        grouped_prediction_page(model, engineer)
    elif page == "📈 难度评分":
        difficulty_scoring_page(model, engineer, df_levels)
    elif page == "💡 SHAP分析":
        shap_analysis_page(model, engineer, df_levels)
    elif page == "🧪 A/B测试":
        ab_testing_page(df_players)
    elif page == "📋 批量评估":
        batch_evaluation_page(model, engineer, df_levels)
    elif page == "⚙️ 动态难度调整":
        dynamic_difficulty_page(model, engineer)
    elif page == "🎲 关卡生成":
        level_generation_page(model, engineer)
    elif page == "⚠️ 流失预警":
        churn_prediction_page(model, engineer, df_levels, df_players)


def data_overview_page(df_levels: pd.DataFrame, df_players: pd.DataFrame):
    st.title("📊 数据概览")
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("关卡总数", len(df_levels))
    with col2:
        st.metric("玩家总数", df_players['player_id'].nunique())
    with col3:
        st.metric("游戏记录总数", len(df_players))
    with col4:
        overall_completion = df_players['completed'].mean()
        st.metric("总体通关率", f"{overall_completion:.1%}")
    
    st.markdown("---")
    
    st.subheader("👥 玩家分群分布")
    
    group_dist = df_players['skill_group'].value_counts().reset_index()
    group_dist.columns = ['skill_group', 'count']
    group_dist['group_name'] = group_dist['skill_group'].map(lambda x: SKILL_GROUPS[x]['name'])
    group_dist['color'] = group_dist['skill_group'].map(lambda x: SKILL_GROUPS[x]['color'])
    
    col_g1, col_g2 = st.columns([1, 1])
    with col_g1:
        fig = px.pie(
            group_dist, 
            values='count', 
            names='group_name',
            color='skill_group',
            color_discrete_map={g: SKILL_GROUPS[g]['color'] for g in SKILL_GROUP_ORDER},
            title='玩家技能分群分布'
        )
        st.plotly_chart(fig, use_container_width=True)
    
    with col_g2:
        group_stats = []
        for group in SKILL_GROUP_ORDER:
            group_data = df_players[df_players['skill_group'] == group]
            group_stats.append({
                '分群': SKILL_GROUPS[group]['name'],
                '玩家数': len(group_data['player_id'].unique()),
                '平均通关率': f"{group_data['completed'].mean():.1%}",
                '平均尝试次数': f"{group_data['attempts'].mean():.2f}",
                '愤怒流失率': f"{group_data['is_rage_quit'].mean():.1%}",
            })
        st.table(pd.DataFrame(group_stats))
    
    st.markdown("---")
    
    tab1, tab2, tab3 = st.tabs(["关卡数据", "玩家数据", "分群对比"])
    
    with tab1:
        st.subheader("关卡设计参数分布")
        
        fig, axes = plt.subplots(2, 4, figsize=(20, 10))
        axes = axes.flatten()
        
        for i, feat in enumerate(FEATURE_COLUMNS):
            ax = axes[i]
            sns.histplot(df_levels[feat], kde=True, ax=ax, bins=20)
            ax.set_title(feat, fontsize=12)
            ax.set_xlabel('')
            ax.set_ylabel('')
        
        plt.tight_layout()
        st.pyplot(fig)
        
        st.markdown("---")
        st.subheader("各分群通关率分布对比")
        
        fig, axes = plt.subplots(1, 3, figsize=(18, 5))
        for i, group in enumerate(SKILL_GROUP_ORDER):
            col = f'{group}_completion_rate'
            if col in df_levels.columns:
                sns.histplot(df_levels[col].dropna(), kde=True, ax=axes[i], bins=20, color=SKILL_GROUPS[group]['color'])
                axes[i].set_title(f"{SKILL_GROUPS[group]['name']} 通关率分布", fontsize=12)
                axes[i].axvline(df_levels[col].mean(), color='red', linestyle='--', label=f'均值: {df_levels[col].mean():.1%}')
                axes[i].legend()
        
        plt.tight_layout()
        st.pyplot(fig)
    
    with tab2:
        st.subheader("玩家行为数据")
        
        col_p1, col_p2 = st.columns(2)
        with col_p1:
            st.metric("平均尝试次数", f"{df_players['attempts'].mean():.2f}")
        with col_p2:
            avg_time = df_players['completion_time'].dropna().mean()
            st.metric("平均通关时间", f"{avg_time:.1f}秒")
        
        st.markdown("---")
        
        fig, axes = plt.subplots(1, 3, figsize=(18, 5))
        
        for i, group in enumerate(SKILL_GROUP_ORDER):
            group_data = df_players[df_players['skill_group'] == group]
            sns.boxplot(data=group_data, x='completed', y='attempts', ax=axes[i])
            axes[i].set_title(f"{SKILL_GROUPS[group]['name']} - 完成状态与尝试次数", fontsize=12)
            axes[i].set_xlabel("是否通关")
        
        plt.tight_layout()
        st.pyplot(fig)
    
    with tab3:
        st.subheader("各分群难度指标对比")
        
        comparison_data = []
        for group in SKILL_GROUP_ORDER:
            comp_col = f'actual_{group}_completion_rate'
            att_col = f'actual_{group}_avg_attempts'
            rage_col = f'actual_{group}_rage_quit_rate'
            
            if comp_col in df_levels.columns:
                comparison_data.append({
                    '分群': SKILL_GROUPS[group]['name'],
                    '平均通关率': f"{df_levels[comp_col].mean():.1%}",
                    '平均尝试次数': f"{df_levels[att_col].mean():.2f}",
                    '平均愤怒流失': f"{df_levels[rage_col].mean():.1%}",
                })
        
        if comparison_data:
            st.table(pd.DataFrame(comparison_data))
        
        st.markdown("---")
        st.subheader("关卡数据表")
        display_cols = ['level_id', 'base_difficulty_score'] + [
            f'{group}_completion_rate' for group in SKILL_GROUP_ORDER
        ] + [
            f'{group}_frustration_index' for group in SKILL_GROUP_ORDER
        ]
        available_cols = [c for c in display_cols if c in df_levels.columns]
        st.dataframe(df_levels[available_cols], use_container_width=True, height=400)


def grouped_prediction_page(model: GroupedDifficultyModel, engineer: FeatureEngineer):
    st.title("🎯 分群难度预测")
    
    st.markdown("### 调整关卡参数，查看各玩家分群的预测结果")
    
    col1, col2 = st.columns([1, 1.5])
    
    with col1:
        st.markdown("#### 关卡设计参数")
        
        obstacle_density = st.slider("障碍密度", 0.05, 0.45, 0.25, 0.01)
        time_limit = st.slider("时间限制 (秒)", 30, 180, 90, 5)
        enemy_count = st.slider("敌人数量", 0, 15, 5, 1)
        platform_gap = st.slider("平台间距", 0.5, 3.0, 1.5, 0.1)
        moving_obstacle_ratio = st.slider("移动障碍比例", 0.0, 0.8, 0.3, 0.05)
        powerup_count = st.slider("道具数量", 0, 5, 2, 1)
        checkpoint_count = st.slider("检查点数量", 0, 4, 1, 1)
        level_length = st.slider("关卡长度", 50, 300, 150, 10)
        
        level_params = {
            'obstacle_density': obstacle_density,
            'time_limit': time_limit,
            'enemy_count': enemy_count,
            'platform_gap': platform_gap,
            'moving_obstacle_ratio': moving_obstacle_ratio,
            'powerup_count': powerup_count,
            'checkpoint_count': checkpoint_count,
            'level_length': level_length,
        }
        
        predict_btn = st.button("🔍 预测分群难度", type="primary", use_container_width=True)
    
    with col2:
        st.markdown("#### 各分群预测结果")
        
        if predict_btn or 'last_grouped_pred' not in st.session_state:
            X = prepare_single_prediction(level_params, engineer)
            predictions_by_group = model.predict_single_all_groups(X)
            st.session_state['last_grouped_pred'] = predictions_by_group
            st.session_state['last_grouped_params'] = level_params
        else:
            predictions_by_group = st.session_state['last_grouped_pred']
            level_params = st.session_state['last_grouped_params']
        
        cols = st.columns(3)
        for i, group in enumerate(SKILL_GROUP_ORDER):
            with cols[i]:
                group_name = SKILL_GROUPS[group]['name']
                color = SKILL_GROUPS[group]['color']
                pred = predictions_by_group[group]
                
                completion_rate = pred.get(
                    f'actual_{group}_completion_rate',
                    pred.get(f'{group}_completion_rate', 0)
                )
                avg_attempts = pred.get(
                    f'actual_{group}_avg_attempts',
                    pred.get(f'{group}_avg_attempts', 0)
                )
                
                st.markdown(f"#### <span style='color:{color}'>{group_name}</span>", unsafe_allow_html=True)
                st.metric("通关率", f"{completion_rate:.1%}")
                st.metric("平均尝试", f"{avg_attempts:.1f} 次")
        
        st.markdown("---")
        
        scorer = DifficultyScorer(target_completion_rate=0.6, target_avg_attempts=4.0)
        scores_by_group = scorer.calculate_score_for_all_groups(
            predictions_by_group, level_params
        )
        
        radar_fig = create_radar_chart(scores_by_group)
        st.plotly_chart(radar_fig, use_container_width=True)
        
        st.markdown("---")
        st.markdown("#### 各分群详细对比")
        
        comparison_rows = []
        for group in SKILL_GROUP_ORDER:
            score = scores_by_group[group]
            group_name = SKILL_GROUPS[group]['name']
            color = SKILL_GROUPS[group]['color']
            
            comparison_rows.append({
                '分群': group_name,
                '难度评分': f"{score.score:.1f}/100",
                '难度等级': f"<span style='color:{score.rating_color}'>{score.rating}</span>",
                '通关率': f"{score.completion_rate:.1%}",
                '平均尝试': f"{score.avg_attempts:.1f}",
                '预计流失率': f"{score.estimated_quit_rate:.1%}",
            })
        
        comparison_df = pd.DataFrame(comparison_rows)
        st.markdown(comparison_df.to_markdown(index=False), unsafe_allow_html=True)


def difficulty_scoring_page(model: GroupedDifficultyModel, engineer: FeatureEngineer,
                           df_levels: pd.DataFrame):
    st.title("📈 难度评分与量化调整建议")
    
    target_completion = st.slider("目标通关率", 0.3, 0.9, 0.6, 0.05)
    target_attempts = st.slider("目标平均尝试次数", 1.0, 10.0, 4.0, 0.5)
    
    selected_group = st.selectbox(
        "选择玩家分群",
        SKILL_GROUP_ORDER,
        format_func=lambda x: SKILL_GROUPS[x]['name']
    )
    
    scorer = DifficultyScorer(
        target_completion_rate=target_completion,
        target_avg_attempts=target_attempts
    )
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.markdown("#### 关卡参数")
        
        obstacle_density = st.slider("障碍密度", 0.05, 0.45, 0.30, 0.01, key="ds_obstacle")
        time_limit = st.slider("时间限制 (秒)", 30, 180, 80, 5, key="ds_time")
        enemy_count = st.slider("敌人数量", 0, 15, 8, 1, key="ds_enemy")
        platform_gap = st.slider("平台间距", 0.5, 3.0, 2.0, 0.1, key="ds_gap")
        moving_obstacle_ratio = st.slider("移动障碍比例", 0.0, 0.8, 0.4, 0.05, key="ds_moving")
        powerup_count = st.slider("道具数量", 0, 5, 1, 1, key="ds_powerup")
        checkpoint_count = st.slider("检查点数量", 0, 4, 0, 1, key="ds_checkpoint")
        level_length = st.slider("关卡长度", 50, 300, 180, 10, key="ds_length")
        
        level_params = {
            'obstacle_density': obstacle_density,
            'time_limit': time_limit,
            'enemy_count': enemy_count,
            'platform_gap': platform_gap,
            'moving_obstacle_ratio': moving_obstacle_ratio,
            'powerup_count': powerup_count,
            'checkpoint_count': checkpoint_count,
            'level_length': level_length,
        }
        
        score_btn = st.button("🎯 计算难度评分", type="primary", use_container_width=True)
    
    with col2:
        st.markdown("#### 难度评分结果")
        
        if score_btn or 'last_grouped_score' not in st.session_state:
            X = prepare_single_prediction(level_params, engineer)
            pred = model.predict_single_group(X, selected_group)
            
            completion_rate = pred.get(
                f'actual_{selected_group}_completion_rate',
                pred.get(f'{selected_group}_completion_rate', 0)
            )
            avg_attempts = pred.get(
                f'actual_{selected_group}_avg_attempts',
                pred.get(f'{selected_group}_avg_attempts', 0)
            )
            
            sample_behavioral = None
            if len(df_levels) > 0:
                sample_behavioral = df_levels.iloc[0]
            
            score = scorer.calculate_score(
                completion_rate, avg_attempts,
                level_params, sample_behavioral, selected_group
            )
            st.session_state['last_grouped_score'] = score
            st.session_state['last_grouped_score_params'] = level_params
            st.session_state['last_grouped_score_pred'] = pred
            st.session_state['last_grouped_score_group'] = selected_group
        else:
            score = st.session_state['last_grouped_score']
            level_params = st.session_state['last_grouped_score_params']
            pred = st.session_state['last_grouped_score_pred']
            selected_group = st.session_state['last_grouped_score_group']
        
        group_name = SKILL_GROUPS[selected_group]['name']
        group_color = SKILL_GROUPS[selected_group]['color']
        
        st.markdown(f"### 玩家分群: <span style='color:{group_color}'>{group_name}</span>", 
                   unsafe_allow_html=True)
        st.markdown(f"### 难度等级: :{score.rating_color}[{score.rating}]")
        
        fig_score = create_gauge_chart(
            score.score,
            "综合难度评分 (0-100)",
            100,
            score.rating_color
        )
        st.plotly_chart(fig_score, use_container_width=True)
        
        col_a, col_b, col_c = st.columns(3)
        with col_a:
            st.metric("通关率", f"{score.completion_rate:.1%}", 
                     delta=f"{(score.completion_rate - target_completion)*100:.1f}%")
        with col_b:
            st.metric("平均尝试", f"{score.avg_attempts:.1f}",
                     delta=f"{score.avg_attempts - target_attempts:.1f}",
                     delta_color='inverse')
        with col_c:
            st.metric("预计流失率", f"{score.estimated_quit_rate:.1%}")
    
    if score.behavioral_score is not None:
        st.markdown("---")
        st.subheader("📊 行为特征分析")
        
        col_b1, col_b2 = st.columns([1.2, 1])
        
        with col_b1:
            beh_fig = create_behavioral_chart(score.behavioral_score, selected_group)
            st.plotly_chart(beh_fig, use_container_width=True)
        
        with col_b2:
            st.markdown("#### 行为指标详情")
            
            beh = score.behavioral_score
            beh_metrics = [
                ("挫败指数", beh.frustration_index, 0.5, "指数越高玩家越容易产生挫败感"),
                ("愤怒流失率", beh.rage_quit_rate, 0.3, "因愤怒而放弃游戏的玩家比例"),
                ("连续失败率", beh.consecutive_fail_rate, 0.6, "玩家连续失败的概率"),
                ("死亡集中度", beh.death_concentration, 0.7, "死亡点的集中程度"),
                ("总死亡密度", beh.total_death_density, 0.6, "整体死亡率"),
                ("平均死亡位置", beh.avg_death_position, 0.5, "玩家死亡的平均位置 (0=开始, 1=结束)"),
            ]
            
            for name, value, threshold, desc in beh_metrics:
                color = "🔴" if value > threshold else "🟢" if value < threshold * 0.7 else "🟡"
                st.markdown(f"{color} **{name}**: {value:.2f}")
                st.caption(desc)
            
            st.markdown(f"**综合行为评分**: {beh.overall_behavioral_score:.2f}/1.0")
    
    st.markdown("---")
    st.subheader("💡 量化调整建议")
    
    if len(score.recommendations) == 0:
        st.success("✅ 当前关卡难度设计优秀，无需调整")
    else:
        for rec_idx, rec in enumerate(score.recommendations):
            priority_colors = {
                'high': '#ef4444',
                'medium': '#f97316',
                'low': '#3b82f6'
            }
            priority_labels = {
                'high': '高优先级',
                'medium': '中优先级',
                'low': '低优先级'
            }
            type_icons = {
                'danger': '🚨',
                'warning': '⚠️',
                'info': 'ℹ️',
                'success': '✅'
            }
            
            icon = type_icons.get(rec.get('type', 'info'), '💡')
            
            with st.expander(
                f"{icon} {rec['title']} - {priority_labels[rec['priority']]}", 
                expanded=rec['priority'] == 'high'
            ):
                if 'behavioral_issue' in rec:
                    st.markdown(f"**🎯 行为问题类型**: {rec.get('issue_type', '')}")
                    if 'current_value' in rec:
                        st.markdown(f"**当前值**: {rec['current_value']}")
                    if 'target_value' in rec:
                        st.markdown(f"**目标值**: {rec['target_value']}")
                    if 'primary_zone' in rec:
                        st.markdown(f"**主要问题区域**: {rec['primary_zone']} ({rec['zone_value']})")
                    if 'suggested_action' in rec:
                        st.markdown(f"**建议操作**: {rec['suggested_action']}")
                
                st.markdown(f"**描述**: {rec['description']}")
                
                if 'quantified_adjustments' in rec and rec['quantified_adjustments']:
                    st.markdown("#### 📝 量化调整方案")
                    adj_df = scorer.format_quantified_table(rec['quantified_adjustments'])
                    st.table(adj_df)
                    
                    total_impact = sum(adj.get('expected_completion_change', 0) for adj in rec['quantified_adjustments'])
                    attempts_impact = sum(adj.get('expected_attempts_change', 0) for adj in rec['quantified_adjustments'])
                    
                    st.info(f"""
                    **预期综合效果**:
                    - 通关率预计变化: {total_impact:+.1f}%
                    - 平均尝试次数预计变化: {attempts_impact:+.1f} 次
                    """)


def shap_analysis_page(model: GroupedDifficultyModel, engineer: FeatureEngineer, 
                       df_levels: pd.DataFrame):
    st.title("💡 SHAP 可解释性分析")
    
    selected_group = st.selectbox(
        "选择玩家分群",
        SKILL_GROUP_ORDER,
        format_func=lambda x: SKILL_GROUPS[x]['name'],
        key="shap_group"
    )
    
    @st.cache_resource(show_spinner="正在计算分群SHAP值...")
    def get_shap_for_group(_model, _engineer, df_levels, group):
        from src.features.preprocessing import prepare_grouped_training_data
        
        data_by_group = prepare_grouped_training_data(
            df_levels, FEATURE_COLUMNS, use_actual=True
        )
        
        group_data = data_by_group[group]
        single_model = _model.models[group]
        
        target_names = [t.replace(f'{group}_', '').replace(f'actual_{group}_', '') 
                       for t in group_data['target_names']]
        
        analyzer = SHAPAnalyzer(
            single_model.model,
            group_data['feature_names'],
            target_names
        )
        analyzer.initialize_explainers(group_data['X_train'])
        analyzer.compute_shap_values(group_data['X_test'])
        
        return analyzer, group_data
    
    analyzer, data = get_shap_for_group(model, engineer, df_levels, selected_group)
    
    target = st.selectbox(
        "选择目标变量",
        analyzer.target_names,
        format_func=lambda x: "通关率" if "completion" in x else "平均尝试次数",
        key="shap_target"
    )
    
    tab1, tab2, tab3, tab4 = st.tabs([
        "📊 特征重要性", 
        "🔍 摘要图", 
        "📈 依赖图",
        "💧 单个样本解释"
    ])
    
    with tab1:
        st.subheader("SHAP 特征重要性")
        
        df_imp = analyzer.get_feature_importance()
        df_target = df_imp[df_imp['target'] == target].head(15)
        
        fig = px.bar(
            df_target, 
            x='shap_importance', 
            y='feature',
            orientation='h',
            title=f'Top 15 特征重要性 - {SKILL_GROUPS[selected_group]["name"]} - {target}',
            color='shap_importance',
            color_continuous_scale='Viridis'
        )
        fig.update_layout(yaxis={'categoryorder': 'total ascending'}, height=500)
        st.plotly_chart(fig, use_container_width=True)
        
        st.markdown("---")
        st.markdown("#### 特征重要性数据表")
        st.dataframe(df_target, use_container_width=True)
    
    with tab2:
        st.subheader("SHAP 摘要图")
        
        fig, ax = plt.subplots(figsize=(12, 8))
        analyzer.plot_summary(data['X_test'], target, max_display=15, show=False)
        st.pyplot(fig)
        
        st.info("摘要图展示了每个特征对模型输出的影响分布。点的颜色表示特征值的高低，横向位置表示SHAP值的正负和大小。")
    
    with tab3:
        st.subheader("SHAP 依赖图")
        
        df_imp = analyzer.get_feature_importance()
        top_features = df_imp[df_imp['target'] == target]['feature'].head(5).tolist()
        
        feature = st.selectbox("选择特征", top_features, key="dep_feature")
        
        fig, ax = plt.subplots(figsize=(10, 6))
        analyzer.plot_dependence(data['X_test'], feature, target, show=False)
        st.pyplot(fig)
        
        st.info(f"依赖图展示了 {feature} 特征值变化时，SHAP值如何变化。颜色表示与另一个特征的交互效应。")
    
    with tab4:
        st.subheader("单个样本预测解释")
        
        sample_idx = st.slider("选择样本索引", 0, len(data['X_test']) - 1, 0, key="waterfall_sample")
        
        explanation = analyzer.explain_single_prediction(
            data['X_test'], sample_idx, target
        )
        
        col_e1, col_e2 = st.columns(2)
        with col_e1:
            st.metric("基准值", f"{explanation['base_value']:.4f}")
        with col_e2:
            st.metric("预测值", f"{explanation['prediction']:.4f}")
        
        fig, ax = plt.subplots(figsize=(10, 8))
        analyzer.plot_waterfall(data['X_test'], sample_idx, target, max_display=10, show=False)
        st.pyplot(fig)
        
        st.markdown("#### 特征贡献详情:")
        top_contrib = explanation['contributions'].head(10)
        st.dataframe(top_contrib, use_container_width=True)


def ab_testing_page(df_players: pd.DataFrame):
    st.title("🧪 A/B 测试分析")
    
    analyzer = ABTestAnalyzer(alpha=0.05)
    
    st.markdown("### 选择要对比的两个关卡")
    
    level_ids = sorted(df_players['level_id'].unique())
    
    col1, col2 = st.columns(2)
    with col1:
        level_a = st.selectbox("选择 A 组（对照组）", level_ids, index=0)
    with col2:
        level_b = st.selectbox("选择 B 组（测试组）", level_ids, index=min(10, len(level_ids)-1))
    
    st.markdown("---")
    
    col_a, col_b = st.columns(2)
    for group in SKILL_GROUP_ORDER:
        group_name = SKILL_GROUPS[group]['name']
        color = SKILL_GROUPS[group]['color']
        
        df_a_group = df_players[(df_players['level_id'] == level_a) & (df_players['skill_group'] == group)]
        df_b_group = df_players[(df_players['level_id'] == level_b) & (df_players['skill_group'] == group)]
        
        with col_a:
            if group == 'novice':
                st.markdown(f"#### {level_a} (A组)")
            st.markdown(f"**<span style='color:{color}'>{group_name}</span>**: "
                       f"{len(df_a_group)}人, "
                       f"通关率 {df_a_group['completed'].mean():.1%}, "
                       f"平均尝试 {df_a_group['attempts'].mean():.1f}",
                       unsafe_allow_html=True)
        
        with col_b:
            if group == 'novice':
                st.markdown(f"#### {level_b} (B组)")
            st.markdown(f"**<span style='color:{color}'>{group_name}</span>**: "
                       f"{len(df_b_group)}人, "
                       f"通关率 {df_b_group['completed'].mean():.1%}, "
                       f"平均尝试 {df_b_group['attempts'].mean():.1f}",
                       unsafe_allow_html=True)
    
    st.markdown("---")
    
    if st.button("🔬 运行分群 A/B 测试", type="primary", use_container_width=True):
        with st.spinner("正在执行分群统计检验..."):
            overall_results = simulate_ab_test_from_levels(df_players, level_a, level_b, analyzer)
            
            st.markdown("### 📊 整体测试结果")
            overall_report = generate_ab_test_report(overall_results)
            st.dataframe(overall_report, use_container_width=True, hide_index=True)
            
            st.markdown("---")
            st.markdown("### 👥 分群测试结果")
            
            for group in SKILL_GROUP_ORDER:
                group_name = SKILL_GROUPS[group]['name']
                color = SKILL_GROUPS[group]['color']
                
                df_a_group = df_players[(df_players['level_id'] == level_a) & (df_players['skill_group'] == group)]
                df_b_group = df_players[(df_players['level_id'] == level_b) & (df_players['skill_group'] == group)]
                
                if len(df_a_group) < 5 or len(df_b_group) < 5:
                    continue
                
                try:
                    metrics_config = [
                        {
                            'type': 'proportion',
                            'metric': f'{group_name}-通关率',
                            'successes_a': df_a_group['completed'].sum(),
                            'trials_a': len(df_a_group),
                            'successes_b': df_b_group['completed'].sum(),
                            'trials_b': len(df_b_group),
                            'variant_a': f'{level_a}-{group_name}',
                            'variant_b': f'{level_b}-{group_name}',
                        },
                        {
                            'type': 'continuous',
                            'metric': f'{group_name}-尝试次数',
                            'data_a': df_a_group['attempts'].values,
                            'data_b': df_b_group['attempts'].values,
                            'variant_a': f'{level_a}-{group_name}',
                            'variant_b': f'{level_b}-{group_name}',
                        }
                    ]
                    
                    group_results = analyzer.test_multiple_metrics(metrics_config)
                    
                    with st.expander(
                        f"📊 {group_name} 测试结果 (样本量: A={len(df_a_group)}, B={len(df_b_group)})",
                        expanded=True
                    ):
                        for result in group_results:
                            sig_color = "green" if result.is_significant else "orange"
                            icon = "✅" if result.is_significant else "⚠️"
                            
                            col_r1, col_r2, col_r3 = st.columns(3)
                            with col_r1:
                                st.metric(f"A组均值", f"{result.mean_a:.4f}")
                            with col_r2:
                                st.metric(f"B组均值", f"{result.mean_b:.4f}", 
                                         delta=f"{result.delta:+.4f}")
                            with col_r3:
                                st.metric("P值", f"{result.p_value:.4f}",
                                         delta_color="inverse")
                            
                            st.info(f"""
                            **{icon} 显著性**: {'显著' if result.is_significant else '不显著'}
                            **检验类型**: {result.test_type}
                            **95%置信区间**: [{result.confidence_interval[0]:.4f}, {result.confidence_interval[1]:.4f}]
                            **效应量**: {result.effect_size:.4f}
                            **统计功效**: {result.power:.2f}
                            **建议**: {result.recommendation}
                            """)
                except Exception as e:
                    st.warning(f"{group_name} 测试跳过: {e}")
    
    st.markdown("---")
    st.subheader("📐 样本量计算器")
    
    col_calc1, col_calc2, col_calc3 = st.columns(3)
    with col_calc1:
        baseline_rate = st.number_input("基线转化率", 0.1, 0.9, 0.6, 0.05)
    with col_calc2:
        min_effect = st.number_input("最小可检测效应", 0.05, 0.5, 0.1, 0.05)
    with col_calc3:
        power = st.number_input("统计功效", 0.7, 0.95, 0.8, 0.05)
    
    sample_size = analyzer.calculate_required_sample_size(baseline_rate, min_effect, power)
    
    st.info(f"""
    **所需样本量**:
    - A组: {sample_size['group_a']} 人
    - B组: {sample_size['group_b']} 人
    - 总计: {sample_size['total']} 人
    """)


def batch_evaluation_page(model: GroupedDifficultyModel, engineer: FeatureEngineer,
                          df_levels: pd.DataFrame):
    st.title("📋 关卡批量评估")
    
    selected_group = st.selectbox(
        "选择评估分群",
        ['all'] + SKILL_GROUP_ORDER,
        format_func=lambda x: '全部分群' if x == 'all' else SKILL_GROUPS[x]['name'],
        key="batch_group"
    )
    
    target_completion = st.slider("目标通关率", 0.3, 0.9, 0.6, 0.05, key="batch_target")
    target_attempts = st.slider("目标平均尝试次数", 1.0, 10.0, 4.0, 0.5, key="batch_target_att")
    
    scorer = DifficultyScorer(
        target_completion_rate=target_completion,
        target_avg_attempts=target_attempts
    )
    
    if st.button("🚀 批量预测并评估", type="primary", use_container_width=True):
        with st.spinner("正在批量预测..."):
            from src.features.preprocessing import prepare_grouped_training_data
            
            data_by_group = prepare_grouped_training_data(
                df_levels, FEATURE_COLUMNS, use_actual=True
            )
            
            all_results = []
            
            for group in SKILL_GROUP_ORDER:
                if selected_group != 'all' and group != selected_group:
                    continue
                    
                group_data = data_by_group[group]
                predictions = model.predict_group(group_data['X_train'], group)
                
                for i in range(len(predictions)):
                    completion_rate = predictions[i, 0]
                    avg_attempts = predictions[i, 1]
                    
                    level_row = group_data['df_clean'].iloc[i]
                    level_params = level_row[FEATURE_COLUMNS].to_dict()
                    
                    score = scorer.calculate_score(
                        completion_rate, avg_attempts,
                        level_params, level_row, group
                    )
                    
                    all_results.append({
                        'level_id': level_row.get('level_id', f'Level_{i+1}'),
                        'skill_group': group,
                        'group_name': SKILL_GROUPS[group]['name'],
                        'difficulty_score': score.score,
                        'difficulty_rating': score.rating,
                        'predicted_completion_rate': completion_rate,
                        'predicted_avg_attempts': avg_attempts,
                        'estimated_quit_rate': score.estimated_quit_rate,
                        'num_recommendations': len(score.recommendations),
                        'high_priority_changes': sum(
                            1 for r in score.recommendations 
                            if r.get('priority') == 'high'
                        ),
                        'has_behavioral_issues': any(
                            r.get('behavioral_issue', False) for r in score.recommendations
                        ),
                        'frustration_index': score.behavioral_score.frustration_index if score.behavioral_score else None,
                        'rage_quit_rate': score.behavioral_score.rage_quit_rate if score.behavioral_score else None,
                    })
            
            eval_df = pd.DataFrame(all_results)
            st.session_state['batch_eval'] = eval_df
    
    if 'batch_eval' in st.session_state:
        eval_df = st.session_state['batch_eval']
        
        st.markdown("---")
        st.subheader("📊 评估概览")
        
        if selected_group == 'all':
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("评估关卡数", len(eval_df['level_id'].unique()))
            with col2:
                avg_score = eval_df['difficulty_score'].mean()
                st.metric("平均难度评分", f"{avg_score:.1f}")
            with col3:
                need_urgent = (eval_df['high_priority_changes'] > 0).sum()
                st.metric("需紧急调整", need_urgent)
            with col4:
                behavioral_issues = eval_df['has_behavioral_issues'].sum()
                st.metric("有行为问题", behavioral_issues)
            
            st.markdown("---")
            st.subheader("📈 各分群难度分布")
            
            fig = px.box(
                eval_df,
                x='group_name',
                y='difficulty_score',
                color='group_name',
                color_discrete_map={SKILL_GROUPS[g]['name']: SKILL_GROUPS[g]['color'] for g in SKILL_GROUP_ORDER},
                title='各玩家分群难度评分分布',
                points='outliers'
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("评估关卡数", len(eval_df))
            with col2:
                avg_score = eval_df['difficulty_score'].mean()
                st.metric("平均难度评分", f"{avg_score:.1f}")
            with col3:
                need_urgent = (eval_df['high_priority_changes'] > 0).sum()
                st.metric("需紧急调整", need_urgent)
            with col4:
                behavioral_issues = eval_df['has_behavioral_issues'].sum()
                st.metric("有行为问题", behavioral_issues)
        
        st.markdown("---")
        st.subheader("🎯 难度等级统计")
        
        rating_counts = eval_df['difficulty_rating'].value_counts().reset_index()
        rating_counts.columns = ['难度等级', '数量']
        
        fig = px.pie(
            rating_counts,
            values='数量',
            names='难度等级',
            title='难度等级分布',
            color='难度等级',
            color_discrete_map={
                '简单': '#22c55e',
                '较易': '#84cc16',
                '中等': '#eab308',
                '较难': '#f97316',
                '困难': '#ef4444',
                '专家': '#9333ea',
            }
        )
        st.plotly_chart(fig, use_container_width=True)
        
        st.markdown("---")
        st.subheader("⚠️ 最需要调整的关卡")
        
        worst_levels = eval_df[eval_df['high_priority_changes'] > 0].copy()
        worst_levels = worst_levels.sort_values('difficulty_score', ascending=False).head(10)
        
        if not worst_levels.empty:
            display_cols = ['level_id', 'group_name', 'difficulty_score', 'difficulty_rating',
                          'predicted_completion_rate', 'high_priority_changes', 'frustration_index']
            st.dataframe(
                worst_levels[display_cols].style.background_gradient(
                    subset=['difficulty_score'], cmap='Reds'
                ),
                use_container_width=True
            )
        else:
            st.success("✅ 所有关卡设计良好，无需紧急调整")
        
        st.markdown("---")
        st.subheader("📋 评估详情表")
        
        filter_rating = st.multiselect(
            "筛选难度等级",
            eval_df['difficulty_rating'].unique(),
            default=eval_df['difficulty_rating'].unique()
        )
        
        if 'group_name' in eval_df.columns:
            filter_group = st.multiselect(
                "筛选分群",
                eval_df['group_name'].unique(),
                default=eval_df['group_name'].unique()
            )
            filtered_df = eval_df[
                eval_df['difficulty_rating'].isin(filter_rating) &
                eval_df['group_name'].isin(filter_group)
            ]
        else:
            filtered_df = eval_df[eval_df['difficulty_rating'].isin(filter_rating)]
        
        def highlight_urgent(row):
            if row['high_priority_changes'] > 0:
                return ['background-color: #fee2e2'] * len(row)
            return [''] * len(row)
        
        styled_df = filtered_df.style.apply(highlight_urgent, axis=1)
        st.dataframe(styled_df, use_container_width=True, height=400)
        
        st.markdown("---")
        st.subheader("⬇️ 下载评估报告")
        
        csv = eval_df.to_csv(index=False).encode('utf-8')
        st.download_button(
            "📥 下载 CSV 报告",
            csv,
            "level_difficulty_evaluation_grouped.csv",
            "text/csv",
            key='download-csv'
        )


def dynamic_difficulty_page(model, engineer):
    st.title("⚙️ 动态难度调整")
    
    st.markdown("### 根据玩家实时表现动态调整关卡难度")
    
    col1, col2 = st.columns(2)
    with col1:
        target_completion = st.slider("目标通关率", 0.3, 0.9, 0.6, 0.05, key="dd_target_comp")
    with col2:
        target_attempts = st.slider("目标平均尝试次数", 1.0, 10.0, 4.0, 0.5, key="dd_target_att")
    
    st.markdown("---")
    
    st.subheader("👤 玩家表现数据")
    
    col_p1, col_p2, col_p3 = st.columns(3)
    with col_p1:
        player_id = st.text_input("玩家ID", "Player_001")
        skill_group = st.selectbox("玩家分群", SKILL_GROUP_ORDER, 
                                   format_func=lambda x: SKILL_GROUPS[x]['name'], key="dd_skill")
    with col_p2:
        completion_rate = st.slider("当前通关率", 0.0, 1.0, 0.35, 0.05, key="dd_comp")
        avg_attempts = st.slider("当前平均尝试次数", 1.0, 15.0, 8.0, 0.5, key="dd_att")
    with col_p3:
        play_duration = st.number_input("游戏时长(分钟)", 1.0, 120.0, 15.0, 1.0, key="dd_duration")
    
    st.markdown("##### 最近表现趋势")
    col_r1, col_r2 = st.columns(2)
    with col_r1:
        recent_completions = st.multiselect(
            "最近10次通关情况",
            options=[True, False],
            default=[False, False, True, False, False, True, False, False, False, False],
            format_func=lambda x: "✅ 通关" if x else "❌ 失败",
            key="dd_recent_comp"
        )
    with col_r2:
        recent_attempts = st.text_input(
            "最近10次尝试次数(逗号分隔)",
            "5,8,3,10,12,2,7,9,11,13",
            key="dd_recent_att"
        )
    
    st.markdown("##### 死亡区域分布")
    col_d1, col_d2, col_d3 = st.columns(3)
    with col_d1:
        obstacle_deaths = st.slider("障碍物区域死亡", 0, 20, 8, key="dd_obstacle")
        enemy_deaths = st.slider("敌人区域死亡", 0, 20, 5, key="dd_enemy")
    with col_d2:
        platform_deaths = st.slider("平台跳跃死亡", 0, 20, 3, key="dd_platform")
        time_deaths = st.slider("时间压力死亡", 0, 20, 2, key="dd_time")
    with col_d3:
        moving_deaths = st.slider("移动障碍死亡", 0, 20, 6, key="dd_moving")
    
    death_zones = {
        'obstacle_zone': obstacle_deaths,
        'enemy_zone': enemy_deaths,
        'platform_zone': platform_deaths,
        'time_zone': time_deaths,
        'moving_zone': moving_deaths,
    }
    
    st.markdown("---")
    
    st.subheader("🎮 当前关卡参数")
    
    col_params = st.columns(4)
    current_params = {}
    param_labels = {
        'obstacle_density': '障碍密度',
        'time_limit': '时间限制(秒)',
        'enemy_count': '敌人数量',
        'platform_gap': '平台间距',
        'moving_obstacle_ratio': '移动障碍比例',
        'powerup_count': '道具数量',
        'checkpoint_count': '检查点数量',
    }
    
    for i, (param, label) in enumerate(list(param_labels.items())[:4]):
        with col_params[i]:
            current_params[param] = st.number_input(label, value=0.3 if param == 'obstacle_density' else 10 if param == 'enemy_count' else 90 if param == 'time_limit' else 1.5, key=f"dd_param_{param}")
    
    col_params2 = st.columns(3)
    for i, (param, label) in enumerate(list(param_labels.items())[4:]):
        with col_params2[i]:
            current_params[param] = st.number_input(label, value=0.2 if param == 'moving_obstacle_ratio' else 1 if param == 'powerup_count' else 2, key=f"dd_param_{param}")
    
    current_params['level_length'] = st.number_input("关卡长度", 50, 300, 150, key="dd_length")
    
    st.markdown("---")
    
    if st.button("🔄 生成动态难度调整建议", type="primary", use_container_width=True):
        with st.spinner("正在分析玩家表现并生成调整建议..."):
            try:
                attempts_list = [int(x.strip()) for x in recent_attempts.split(',') if x.strip()]
            except:
                attempts_list = [5, 8, 3, 10, 12]
            
            performance = PlayerPerformance(
                player_id=player_id,
                skill_group=skill_group,
                completion_rate=completion_rate,
                avg_attempts=avg_attempts,
                recent_attempts=attempts_list,
                recent_completions=recent_completions,
                death_zones=death_zones,
                play_duration=play_duration,
                timestamp=pd.Timestamp.now().timestamp()
            )
            
            adjuster = DynamicDifficultyAdjuster(
                target_completion_rate=target_completion,
                target_avg_attempts=target_attempts
            )
            
            result = adjuster.adjust_difficulty(performance, current_params)
            
            st.session_state['dd_result'] = result
            st.session_state['dd_performance'] = performance
            st.session_state['dd_adjuster'] = adjuster
    
    if 'dd_result' in st.session_state:
        result = st.session_state['dd_result']
        performance = st.session_state['dd_performance']
        adjuster = st.session_state['dd_adjuster']
        
        st.markdown("---")
        st.subheader("📊 调整结果")
        
        col_res1, col_res2, col_res3, col_res4 = st.columns(4)
        with col_res1:
            risk_color = '#ef4444' if result.risk_level == 'high' else '#f59e0b' if result.risk_level == 'medium' else '#22c55e'
            st.metric("风险等级", result.risk_level.replace('low', '低').replace('medium', '中').replace('high', '高'))
        with col_res2:
            st.metric("调整强度", f"{result.adjustment_strength:.0%}")
        with col_res3:
            st.metric("预期通关率", f"{result.expected_outcome['new_completion_rate']:.1%}", 
                      delta=f"{result.expected_outcome['total_completion_change']:+.1f}%")
        with col_res4:
            st.metric("预期尝试次数", f"{result.expected_outcome['new_avg_attempts']:.1f}",
                      delta=f"{result.expected_outcome['total_attempts_change']:+.1f}")
        
        st.markdown("---")
        st.subheader("📈 表现分析")
        
        col_ana1, col_ana2 = st.columns(2)
        with col_ana1:
            trend = performance.get_recent_trend()
            trend_desc = {1: '上升', 0: '稳定', -1: '下降'}[trend['trend']]
            st.info(f"📊 表现趋势: {trend_desc} (斜率: {trend['slope']:.3f}, 波动: {trend['volatility']:.2f})")
            
            gap = result.performance_summary['gap']
            st.info(f"📉 通关率差距: 目标{target_completion:.0%} vs 当前{completion_rate:.1%} (差距 {gap['completion_gap']:+.1%})")
        
        with col_ana2:
            total_deaths = sum(death_zones.values())
            if total_deaths > 0:
                worst_zone = max(death_zones, key=death_zones.get)
                zone_names = {
                    'obstacle_zone': '障碍物区域',
                    'enemy_zone': '敌人区域',
                    'platform_zone': '平台跳跃区',
                    'time_zone': '时间压力区',
                    'moving_zone': '移动障碍区',
                }
                st.warning(f"💀 主要死亡区域: {zone_names[worst_zone]} ({death_zones[worst_zone]}次, 占比 {death_zones[worst_zone]/total_deaths:.0%})")
        
        if result.adjustments:
            st.markdown("---")
            st.subheader("🔧 量化调整建议")
            
            adj_rows = []
            for adj in result.adjustments:
                adj_rows.append({
                    '参数名称': adj.feature_name,
                    '调整方向': f"{adj.action} {adj.adjustment_percent:.0f}%",
                    '当前值': f"{adj.current_value:.3f}" if isinstance(adj.current_value, float) else str(adj.current_value),
                    '建议值': f"{adj.suggested_value:.3f}" if isinstance(adj.suggested_value, float) else str(adj.suggested_value),
                    '预期通关率变化': f"{adj.expected_impact['completion_rate_change']:+.1f}%",
                    '预期尝试变化': f"{adj.expected_impact['avg_attempts_change']:+.1f}次",
                    '调整原因': adj.reason,
                    '置信度': f"{adj.confidence:.0%}",
                })
            
            adj_df = pd.DataFrame(adj_rows)
            st.table(adj_df)
            
            st.markdown("---")
            st.subheader("📋 调整后参数")
            
            col_new1, col_new2 = st.columns(2)
            with col_new1:
                st.markdown("##### 当前参数")
                for feat, val in current_params.items():
                    name = param_labels.get(feat, feat)
                    st.text(f"{name}: {val}")
            
            with col_new2:
                st.markdown("##### 调整后参数")
                for feat, val in result.adjusted_params.items():
                    name = param_labels.get(feat, feat)
                    if feat in [a.feature for a in result.adjustments]:
                        st.success(f"{name}: {val} ✅")
                    else:
                        st.text(f"{name}: {val}")
            
            st.markdown("---")
            st.subheader("🎯 模拟调整效果")
            
            with st.spinner("正在进行蒙特卡洛模拟..."):
                simulation = adjuster.simulate_adjustment_impact(performance, current_params)
            
            col_sim1, col_sim2, col_sim3 = st.columns(3)
            with col_sim1:
                st.metric("模拟预期通关率", f"{simulation['mean_completion']:.1%}",
                         delta=f"{(simulation['mean_completion'] - completion_rate) * 100:+.1f}%")
                st.caption(f"90%置信区间: {simulation['lower_completion']:.1%} ~ {simulation['upper_completion']:.1%}")
            with col_sim2:
                st.metric("模拟预期尝试次数", f"{simulation['mean_attempts']:.1f}",
                         delta=f"{simulation['mean_attempts'] - avg_attempts:+.1f}")
                st.caption(f"90%置信区间: {simulation['lower_attempts']:.1f} ~ {simulation['upper_attempts']:.1f}")
            with col_sim3:
                st.metric("调整成功概率", f"{simulation['success_probability']:.0%}")
            
            fig = go.Figure()
            sim_x = list(range(len(simulation['simulations'])))
            sim_comp = [s[0] * 100 for s in simulation['simulations']]
            sim_att = [s[1] for s in simulation['simulations']]
            
            fig.add_trace(go.Scatter(
                x=sim_x, y=sim_comp, mode='markers',
                name='通关率(%)', yaxis='y',
                marker=dict(color='#3b82f6', size=6, opacity=0.6)
            ))
            fig.add_trace(go.Scatter(
                x=sim_x, y=sim_att, mode='markers',
                name='尝试次数', yaxis='y2',
                marker=dict(color='#f97316', size=6, opacity=0.6)
            ))
            
            fig.update_layout(
                title='蒙特卡洛模拟 - 100次调整效果预测',
                xaxis_title='模拟次数',
                yaxis=dict(title='通关率(%)', side='left'),
                yaxis2=dict(title='尝试次数', side='right', overlaying='y'),
                height=350,
                legend=dict(orientation='h', y=1.1)
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.success("✅ 当前难度设置合理，无需调整")


def level_generation_page(model, engineer):
    st.title("🎲 关卡自动生成")
    
    st.markdown("### 根据难度目标自动生成关卡参数")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        target_difficulty = st.slider("目标难度", 0.0, 1.0, 0.5, 0.05, key="lg_target")
        n_levels = st.number_input("生成关卡数量", 1, 20, 5, 1, key="lg_n")
    with col2:
        skill_group = st.selectbox("目标玩家分群", SKILL_GROUP_ORDER,
                                   format_func=lambda x: SKILL_GROUPS[x]['name'], key="lg_skill")
        level_type = st.selectbox("关卡类型", list(LEVEL_TYPES.keys()),
                                   format_func=lambda x: LEVEL_TYPES[x]['name'], key="lg_type")
    with col3:
        generation_mode = st.radio("生成模式", ["单类型生成", "多样化生成", "难度曲线生成"], key="lg_mode")
    
    st.markdown("---")
    st.subheader("🔒 约束条件 (可选)")
    
    col_c1, col_c2 = st.columns(2)
    with col_c1:
        min_obstacle = st.slider("最小障碍密度", 0.05, 0.45, 0.05, 0.05, key="lg_min_obs")
        max_obstacle = st.slider("最大障碍密度", 0.05, 0.45, 0.45, 0.05, key="lg_max_obs")
        min_enemy = st.slider("最小敌人数量", 0, 15, 0, 1, key="lg_min_enemy")
        max_enemy = st.slider("最大敌人数量", 0, 15, 15, 1, key="lg_max_enemy")
    with col_c2:
        min_time = st.slider("最小时间限制(秒)", 30, 180, 30, 5, key="lg_min_time")
        max_time = st.slider("最大时间限制(秒)", 30, 180, 180, 5, key="lg_max_time")
        require_powerups = st.checkbox("必须包含道具", key="lg_req_pw")
        require_checkpoints = st.checkbox("必须包含检查点", key="lg_req_cp")
    
    if generation_mode == "难度曲线生成":
        st.markdown("---")
        st.subheader("📈 难度曲线设置")
        col_curve1, col_curve2 = st.columns(2)
        with col_curve1:
            start_diff = st.slider("起始难度", 0.0, 1.0, 0.2, 0.05, key="lg_start")
            end_diff = st.slider("结束难度", 0.0, 1.0, 0.8, 0.05, key="lg_end")
        with col_curve2:
            curve_type = st.selectbox("曲线类型", ["linear", "exponential", "sigmoid"],
                                       format_func=lambda x: {"linear": "线性", "exponential": "指数", "sigmoid": "S型"}[x],
                                       key="lg_curve")
    
    st.markdown("---")
    
    if st.button("🎯 生成关卡", type="primary", use_container_width=True):
        with st.spinner("正在生成关卡参数..."):
            constraints = GenerationConstraints(
                min_obstacle_density=min_obstacle,
                max_obstacle_density=max_obstacle,
                min_time_limit=min_time,
                max_time_limit=max_time,
                min_enemy_count=min_enemy,
                max_enemy_count=max_enemy,
                require_powerups=require_powerups,
                require_checkpoints=require_checkpoints
            )
            
            generator = LevelGenerator(model=model, engineer=engineer)
            
            if generation_mode == "难度曲线生成":
                levels = generator.generate_level_curve(
                    n_levels=n_levels,
                    start_difficulty=start_diff,
                    end_difficulty=end_diff,
                    skill_group=skill_group,
                    curve_type=curve_type,
                    constraints=constraints
                )
            elif generation_mode == "多样化生成":
                levels = generator.generate_multiple_levels(
                    n_levels=n_levels,
                    target_difficulty=target_difficulty,
                    skill_group=skill_group,
                    constraints=constraints,
                    diverse=True
                )
            else:
                levels = []
                for i in range(n_levels):
                    level = generator.generate_level(
                        target_difficulty=target_difficulty,
                        skill_group=skill_group,
                        level_type=level_type,
                        constraints=constraints,
                        level_id=f"Gen_{i+1:03d}",
                        max_attempts=50
                    )
                    if level:
                        levels.append(level)
            
            st.session_state['generated_levels'] = levels
            st.session_state['generator'] = generator
    
    if 'generated_levels' in st.session_state:
        levels = st.session_state['generated_levels']
        generator = st.session_state['generator']
        
        if not levels:
            st.error("未能生成满足条件的关卡，请放宽约束条件")
        else:
            st.markdown("---")
            st.subheader(f"✅ 成功生成 {len(levels)} 个关卡")
            
            levels_df = generator.levels_to_dataframe(levels)
            display_cols = ['level_id', 'level_type_name', 'target_skill_name', 
                           'obstacle_density', 'time_limit', 'enemy_count',
                           'completion_rate', 'avg_attempts', 'difficulty_score', 
                           'difficulty_rating', 'generation_score']
            display_df = levels_df[display_cols].copy()
            display_df['completion_rate'] = (display_df['completion_rate'] * 100).round(1).astype(str) + '%'
            display_df['avg_attempts'] = display_df['avg_attempts'].round(1)
            display_df['difficulty_score'] = display_df['difficulty_score'].round(1)
            display_df['generation_score'] = (display_df['generation_score'] * 100).round(0).astype(int).astype(str) + '%'
            
            st.dataframe(display_df, use_container_width=True, height=300)
            
            st.markdown("---")
            st.subheader("📊 生成质量分析")
            
            col_g1, col_g2, col_g3 = st.columns(3)
            avg_gen_score = np.mean([l.generation_score for l in levels])
            avg_diff_score = np.mean([l.difficulty_score for l in levels])
            avg_comp = np.mean([l.predicted_metrics['completion_rate'] for l in levels])
            
            with col_g1:
                st.metric("平均生成质量", f"{avg_gen_score:.0%}")
            with col_g2:
                st.metric("平均难度评分", f"{avg_diff_score:.1f}/100")
            with col_g3:
                st.metric("平均预期通关率", f"{avg_comp:.1%}")
            
            if generation_mode == "难度曲线生成":
                fig = go.Figure()
                fig.add_trace(go.Scatter(
                    x=list(range(1, len(levels) + 1)),
                    y=[l.difficulty_score for l in levels],
                    mode='lines+markers',
                    name='难度评分',
                    line=dict(color='#3b82f6', width=3),
                    marker=dict(size=8)
                ))
                fig.add_trace(go.Scatter(
                    x=list(range(1, len(levels) + 1)),
                    y=[l.predicted_metrics['completion_rate'] * 100 for l in levels],
                    mode='lines+markers',
                    name='通关率(%)',
                    line=dict(color='#22c55e', width=2, dash='dash'),
                    marker=dict(size=6),
                    yaxis='y2'
                ))
                fig.update_layout(
                    title='难度曲线 - 关卡难度 progression',
                    xaxis_title='关卡序号',
                    yaxis=dict(title='难度评分', range=[0, 100]),
                    yaxis2=dict(title='通关率(%)', range=[0, 100], overlaying='y', side='right'),
                    height=400
                )
                st.plotly_chart(fig, use_container_width=True)
            
            st.markdown("---")
            st.subheader("🎮 查看详情")
            
            selected_level_idx = st.selectbox(
                "选择关卡查看详细信息",
                range(len(levels)),
                format_func=lambda i: f"{levels[i].level_id} - {LEVEL_TYPES[levels[i].level_type]['name']} (评分: {levels[i].generation_score:.0%})",
                key="lg_select"
            )
            
            selected_level = levels[selected_level_idx]
            
            col_det1, col_det2 = st.columns(2)
            with col_det1:
                st.markdown("##### 📋 关卡参数")
                for feat, val in selected_level.params.items():
                    name = {
                        'obstacle_density': '障碍密度',
                        'time_limit': '时间限制(秒)',
                        'enemy_count': '敌人数量',
                        'platform_gap': '平台间距',
                        'moving_obstacle_ratio': '移动障碍比例',
                        'powerup_count': '道具数量',
                        'checkpoint_count': '检查点数量',
                        'level_length': '关卡长度',
                    }.get(feat, feat)
                    st.text(f"{name}: {val}")
            
            with col_det2:
                st.markdown("##### 📊 预测指标")
                st.metric("预期通关率", f"{selected_level.predicted_metrics['completion_rate']:.1%}")
                st.metric("预期平均尝试", f"{selected_level.predicted_metrics['avg_attempts']:.1f}次")
                st.metric("难度评分", f"{selected_level.difficulty_score:.1f}/100 ({selected_level.difficulty_rating})")
                st.metric("生成质量", f"{selected_level.generation_score:.0%}")
            
            if selected_level.generation_notes:
                with col_det2:
                    st.markdown("##### 📝 生成备注")
                    for note in selected_level.generation_notes:
                        st.warning(note)
            
            st.markdown("---")
            st.subheader("⚠️ 行为风险预测")
            
            risk = selected_level.behavioral_risk
            col_risk1, col_risk2, col_risk3 = st.columns(3)
            with col_risk1:
                st.metric("挫败指数", f"{risk['frustration_index']:.2f}")
            with col_risk2:
                st.metric("愤怒流失率", f"{risk['rage_quit_rate']:.1%}")
            with col_risk3:
                st.metric("死亡集中度", f"{risk['death_concentration']:.2f}")
            
            fig = go.Figure(go.Bar(
                x=list(risk['death_zones'].keys()),
                y=[v * 100 for v in risk['death_zones'].values()],
                text=[f"{v:.1f}%" for v in risk['death_zones'].values()],
                textposition='auto',
                marker_color=['#ef4444', '#f97316', '#eab308', '#84cc16', '#3b82f6']
            ))
            fig.update_layout(
                title='预期各区域死亡密度分布 (%)',
                xaxis_title='死亡区域',
                yaxis_title='死亡密度 (%)',
                height=300
            )
            st.plotly_chart(fig, use_container_width=True)
            
            st.markdown("---")
            st.subheader("⬇️ 导出生成结果")
            
            csv = levels_df.to_csv(index=False).encode('utf-8')
            st.download_button(
                "📥 下载 CSV 格式关卡数据",
                csv,
                f"generated_levels_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.csv",
                "text/csv",
                key='download-levels'
            )


def churn_prediction_page(model, engineer, df_levels, df_players):
    st.title("⚠️ 流失预警分析")
    
    st.markdown("### 预测高难度导致的玩家流失风险")
    
    tab1, tab2, tab3 = st.tabs(["🔍 单玩家分析", "👥 批量风险检测", "📊 风险分布统计"])
    
    with tab1:
        st.subheader("🔍 单玩家流失风险分析")
        
        col_p1, col_p2, col_p3 = st.columns(3)
        with col_p1:
            player_id = st.text_input("玩家ID", "Player_001", key="churn_pid")
            skill_group = st.selectbox("玩家分群", SKILL_GROUP_ORDER,
                                       format_func=lambda x: SKILL_GROUPS[x]['name'], key="churn_skill")
            level_id = st.text_input("关卡ID", "Level_001", key="churn_level")
        with col_p2:
            completion_rate = st.slider("通关率", 0.0, 1.0, 0.3, 0.05, key="churn_comp")
            avg_attempts = st.slider("平均尝试次数", 1.0, 15.0, 7.0, 0.5, key="churn_att")
            play_duration = st.number_input("本次游戏时长(分钟)", 1.0, 120.0, 10.0, 1.0, key="churn_dur")
        with col_p3:
            level_difficulty = st.slider("关卡难度", 0.0, 1.0, 0.7, 0.05, key="churn_diff")
            session_count = st.number_input("累计游戏次数", 1, 100, 5, 1, key="churn_session")
            days_since_last = st.number_input("距上次游戏(天)", 0, 30, 2, 1, key="churn_days")
        
        st.markdown("##### 最近游戏记录")
        col_r1, col_r2 = st.columns(2)
        with col_r1:
            recent_completions = st.multiselect(
                "最近10次通关情况",
                options=[True, False],
                default=[False, False, False, True, False, False, False, False, False, True],
                format_func=lambda x: "✅ 通关" if x else "❌ 失败",
                key="churn_recent_comp"
            )
            recent_attempts_str = st.text_input(
                "最近10次尝试次数(逗号分隔)",
                "8,12,10,3,15,9,11,13,14,2",
                key="churn_recent_att"
            )
        with col_r2:
            frustration_events = st.number_input("挫败事件次数", 0, 20, 8, 1, key="churn_frustr")
            consecutive_failures = st.number_input("连续失败次数", 0, 20, 5, 1, key="churn_consec")
            rage_quits = st.number_input("愤怒退出次数", 0, 10, 2, 1, key="churn_rage")
            total_play_time = st.number_input("累计游戏时长(小时)", 1.0, 200.0, 15.0, 1.0, key="churn_total")
        
        st.markdown("##### 死亡区域分布")
        col_d1, col_d2, col_d3 = st.columns(3)
        with col_d1:
            d_obstacle = st.slider("障碍物死亡", 0, 30, 12, key="churn_d_obs")
            d_enemy = st.slider("敌人死亡", 0, 30, 8, key="churn_d_enemy")
        with col_d2:
            d_platform = st.slider("平台死亡", 0, 30, 5, key="churn_d_plat")
            d_time = st.slider("时间死亡", 0, 30, 3, key="churn_d_time")
        with col_d3:
            d_moving = st.slider("移动障碍死亡", 0, 30, 10, key="churn_d_moving")
        
        death_zones = {
            'obstacle_zone': d_obstacle,
            'enemy_zone': d_enemy,
            'platform_zone': d_platform,
            'time_zone': d_time,
            'moving_zone': d_moving,
        }
        
        if st.button("🔍 分析流失风险", type="primary", use_container_width=True, key="churn_analyze"):
            with st.spinner("正在分析玩家流失风险..."):
                try:
                    attempts_list = [int(x.strip()) for x in recent_attempts_str.split(',') if x.strip()]
                except:
                    attempts_list = [5, 8, 10, 3, 12]
                
                player_data = PlayerBehaviorData(
                    player_id=player_id,
                    skill_group=skill_group,
                    level_id=level_id,
                    completion_rate=completion_rate,
                    avg_attempts=avg_attempts,
                    play_duration=play_duration,
                    recent_completions=recent_completions,
                    recent_attempts=attempts_list,
                    death_zones=death_zones,
                    frustration_events=frustration_events,
                    consecutive_failures=consecutive_failures,
                    rage_quits=rage_quits,
                    session_count=session_count,
                    days_since_last_play=days_since_last,
                    total_play_time=total_play_time,
                    level_difficulty=level_difficulty,
                    timestamp=pd.Timestamp.now().timestamp()
                )
                
                predictor = ChurnPredictor()
                result = predictor.predict_churn(player_data)
                
                st.session_state['churn_result'] = result
                st.session_state['churn_data'] = player_data
                st.session_state['churn_predictor'] = predictor
        
        if 'churn_result' in st.session_state:
            result = st.session_state['churn_result']
            player_data = st.session_state['churn_data']
            predictor = st.session_state['churn_predictor']
            
            st.markdown("---")
            st.subheader("📊 流失风险分析结果")
            
            risk_level = result.risk_level
            risk_color = {
                'low': '#22c55e',
                'medium': '#f59e0b',
                'high': '#ef4444'
            }[risk_level]
            risk_text = {
                'low': '低风险',
                'medium': '中风险',
                'high': '高风险'
            }[risk_level]
            
            col_r1, col_r2, col_r3, col_r4 = st.columns(4)
            with col_r1:
                fig_risk = create_gauge_chart(
                    result.churn_risk * 100, "流失概率 (%)", 100, risk_color
                )
                st.plotly_chart(fig_risk, use_container_width=True)
            with col_r2:
                st.metric("风险等级", risk_text)
                st.metric("干预优先级", f"{'紧急' if result.intervention_priority == 1 else '中等' if result.intervention_priority == 2 else '低'}")
            with col_r3:
                st.metric("预期留存改善", f"{result.expected_retention_impact:.0%}")
                if result.risk_factors.overall_risk > 0.5:
                    st.warning("⚠️ 建议立即干预")
                else:
                    st.success("✅ 风险可控")
            with col_r4:
                dominant = result.risk_factors.get_dominant_factors(0.5)
                if dominant:
                    st.markdown("##### 主要风险因素")
                    for name, val, desc in dominant[:3]:
                        st.progress(val, text=f"{name}: {val:.0%}")
            
            st.markdown("---")
            st.subheader("📈 风险因素分析")
            
            contributions = result.feature_contributions
            fig = go.Figure(go.Bar(
                x=list(contributions.values()),
                y=list(contributions.keys()),
                orientation='h',
                text=[f"{v:.0%}" for v in contributions.values()],
                textposition='auto',
                marker_color=[risk_color if v > 0.6 else '#f59e0b' if v > 0.4 else '#22c55e' for v in contributions.values()]
            ))
            fig.update_layout(
                title='各风险因素贡献度',
                xaxis_title='风险值',
                xaxis=dict(range=[0, 1]),
                height=350
            )
            st.plotly_chart(fig, use_container_width=True)
            
            if result.warnings:
                st.markdown("---")
                st.subheader("⚠️ 风险警告")
                
                for warning in result.warnings:
                    warn_color = {
                        'critical': '#ef4444',
                        'warning': '#f59e0b',
                        'info': '#3b82f6'
                    }.get(warning.level, '#6b7280')
                    
                    urgency_icon = {
                        'immediate': '🚨',
                        'high': '⚡',
                        'medium': '⚠️',
                        'low': 'ℹ️'
                    }.get(warning.urgency, 'ℹ️')
                    
                    st.markdown(f"""
                    <div style="padding: 15px; border-radius: 10px; background-color: {warn_color}20; border-left: 4px solid {warn_color};">
                        <b>{urgency_icon} {warning.message}</b><br>
                        <small>风险值: {warning.risk_score:.0%} | 紧急度: {warning.urgency}</small><br>
                        <small>建议: {warning.suggested_action}</small>
                    </div>
                    """, unsafe_allow_html=True)
            
            st.markdown("---")
            st.subheader("🎯 留存策略建议")
            
            strategy = result.retention_strategy
            
            if strategy['immediate_actions']:
                st.markdown("##### 🔴 立即执行 (24小时内)")
                for action in strategy['immediate_actions']:
                    priority_icon = {'critical': '🔴', 'high': '🟠'}[action.get('priority', 'high')]
                    st.markdown(f"""
                    <div style="padding: 10px; margin: 5px 0; background-color: #fef2f2; border-radius: 8px;">
                        <b>{priority_icon} {action['action']}</b>: {action['target']}<br>
                        <small>预期效果: {action['expected_impact']}</small>
                    </div>
                    """, unsafe_allow_html=True)
            
            if strategy['short_term_actions']:
                st.markdown("##### 🟡 短期执行 (1周内)")
                for action in strategy['short_term_actions']:
                    st.markdown(f"""
                    <div style="padding: 10px; margin: 5px 0; background-color: #fffbeb; border-radius: 8px;">
                        <b>🟡 {action['action']}</b>: {action['target']}<br>
                        <small>预期效果: {action['expected_impact']}</small>
                    </div>
                    """, unsafe_allow_html=True)
            
            if strategy['long_term_actions']:
                st.markdown("##### 🟢 长期优化 (1个月内)")
                for action in strategy['long_term_actions']:
                    st.markdown(f"""
                    <div style="padding: 10px; margin: 5px 0; background-color: #f0fdf4; border-radius: 8px;">
                        <b>🟢 {action['action']}</b>: {action['target']}<br>
                        <small>预期效果: {action['expected_impact']}</small>
                    </div>
                    """, unsafe_allow_html=True)
            
            if strategy['personalized_suggestions']:
                st.markdown("##### 💡 个性化建议")
                for suggestion in strategy['personalized_suggestions']:
                    st.info(suggestion)
            
            st.markdown("---")
            st.subheader("🎲 干预效果模拟")
            
            intervention_type = st.selectbox(
                "选择干预类型",
                ["难度降低", "增加道具", "情绪安抚", "综合干预"],
                key="churn_intervention"
            )
            
            if st.button("🔬 模拟干预效果", key="churn_simulate"):
                with st.spinner("正在进行蒙特卡洛模拟..."):
                    sim_result = predictor.simulate_intervention_impact(
                        player_data, intervention_type, n_simulations=200
                    )
                    
                    col_s1, col_s2, col_s3 = st.columns(3)
                    with col_s1:
                        st.metric("原始风险", f"{sim_result['base_risk']:.0%}")
                    with col_s2:
                        st.metric("预期风险", f"{sim_result['mean_new_risk']:.0%}",
                                 delta=f"{sim_result['risk_reduction']:-.0%}")
                    with col_s3:
                        st.metric("干预成功率", f"{sim_result['success_probability']:.0%}")
                    
                    fig = go.Figure()
                    fig.add_trace(go.Histogram(
                        x=[r * 100 for r in sim_result['simulations']],
                        nbinsx=20,
                        name='模拟风险分布',
                        marker_color='#3b82f6',
                        opacity=0.7
                    ))
                    fig.add_vline(
                        x=sim_result['base_risk'] * 100,
                        line_dash="dash",
                        line_color="#ef4444",
                        annotation_text="原始风险",
                        annotation_position="top right"
                    )
                    fig.add_vline(
                        x=sim_result['mean_new_risk'] * 100,
                        line_dash="dash",
                        line_color="#22c55e",
                        annotation_text="预期风险",
                        annotation_position="top left"
                    )
                    fig.update_layout(
                        title='200次蒙特卡洛模拟 - 干预后风险分布',
                        xaxis_title='流失风险 (%)',
                        yaxis_title='频次',
                        height=350
                    )
                    st.plotly_chart(fig, use_container_width=True)
    
    with tab2:
        st.subheader("👥 批量风险检测")
        
        n_players = st.slider("检测玩家数量", 10, 200, 50, 10, key="churn_batch_n")
        min_risk = st.selectbox("最低风险等级", ["medium", "high"],
                               format_func=lambda x: "中等风险及以上" if x == "medium" else "高风险",
                               key="churn_batch_min")
        
        if st.button("🔍 批量检测高风险玩家", type="primary", key="churn_batch"):
            with st.spinner(f"正在检测 {n_players} 名玩家的流失风险..."):
                players_data = []
                np.random.seed(42)
                
                for i in range(n_players):
                    group = np.random.choice(SKILL_GROUP_ORDER, p=[0.3, 0.5, 0.2])
                    completion = np.random.uniform(0.1, 0.9)
                    difficulty = np.random.uniform(0.2, 0.9)
                    
                    if difficulty > 0.7 and completion < 0.3:
                        frustration = np.random.randint(3, 15)
                        consecutive = np.random.randint(2, 10)
                        rage = np.random.randint(0, 5)
                    else:
                        frustration = np.random.randint(0, 5)
                        consecutive = np.random.randint(0, 3)
                        rage = np.random.randint(0, 1)
                    
                    player = PlayerBehaviorData(
                        player_id=f"Player_{i+1:03d}",
                        skill_group=group,
                        level_id=f"Level_{np.random.randint(1, 50):03d}",
                        completion_rate=completion,
                        avg_attempts=np.random.uniform(1, 15),
                        play_duration=np.random.uniform(5, 60),
                        recent_completions=[bool(np.random.random() < completion) for _ in range(10)],
                        recent_attempts=[np.random.randint(1, 15) for _ in range(10)],
                        death_zones={
                            'obstacle_zone': np.random.randint(0, 15),
                            'enemy_zone': np.random.randint(0, 15),
                            'platform_zone': np.random.randint(0, 10),
                            'time_zone': np.random.randint(0, 8),
                            'moving_zone': np.random.randint(0, 12),
                        },
                        frustration_events=frustration,
                        consecutive_failures=consecutive,
                        rage_quits=rage,
                        session_count=np.random.randint(1, 50),
                        days_since_last_play=np.random.randint(0, 21),
                        total_play_time=np.random.uniform(1, 100),
                        level_difficulty=difficulty,
                        timestamp=pd.Timestamp.now().timestamp()
                    )
                    players_data.append(player)
                
                predictor = ChurnPredictor()
                at_risk = predictor.identify_at_risk_players(players_data, min_risk_level=min_risk)
                
                st.session_state['churn_batch'] = at_risk
                st.session_state['churn_predictor'] = predictor
                st.session_state['churn_batch_all'] = predictor.batch_predict(players_data)
        
        if 'churn_batch' in st.session_state:
            at_risk = st.session_state['churn_batch']
            all_results = st.session_state['churn_batch_all']
            predictor = st.session_state['churn_predictor']
            
            if not at_risk:
                st.success("✅ 未发现符合条件的高风险玩家")
            else:
                st.markdown(f"#### 发现 {len(at_risk)} 名高风险玩家")
                
                batch_rows = []
                for r in at_risk:
                    dominant = r.risk_factors.get_dominant_factors(0.6)
                    top_factor = dominant[0][0] if dominant else "综合因素"
                    
                    batch_rows.append({
                        '玩家ID': r.player_id,
                        '分群': SKILL_GROUPS[r.skill_group]['name'],
                        '流失概率': f"{r.churn_probability:.1%}",
                        '风险等级': {'low': '低', 'medium': '中', 'high': '高'}[r.risk_level],
                        '主要风险': top_factor,
                        '优先级': r.intervention_priority,
                        '通关率': f"{all_results[at_risk.index(r)].performance_summary['current_completion_rate']:.1%}" if r in at_risk else "N/A",
                        '建议成功率': f"{r.expected_retention_impact:.0%}",
                    })
                
                batch_df = pd.DataFrame(batch_rows)
                st.dataframe(batch_df, use_container_width=True, height=400)
                
                st.markdown("---")
                st.subheader("📊 风险分布统计")
                
                distribution = predictor.get_risk_distribution(all_results)
                
                col_d1, col_d2, col_d3, col_d4 = st.columns(4)
                with col_d1:
                    st.metric("分析玩家总数", distribution['total_players'])
                with col_d2:
                    st.metric("高风险玩家", f"{distribution['high_risk_count']}人", 
                             f"{distribution['high_risk_percent']:.1f}%")
                with col_d3:
                    st.metric("中风险玩家", f"{distribution['medium_risk_count']}人",
                             f"{distribution['medium_risk_percent']:.1f}%")
                with col_d4:
                    st.metric("平均风险值", f"{distribution['avg_risk']:.1%}")
                
                if distribution['by_skill_group']:
                    st.markdown("##### 各分群风险分布")
                    group_risk_rows = []
                    for group_name, data in distribution['by_skill_group'].items():
                        group_risk_rows.append({
                            '分群': group_name,
                            '玩家数': data['total'],
                            '高风险': f"{data['high_risk']}人",
                            '中风险': f"{data['medium_risk']}人",
                            '低风险': f"{data['low_risk']}人",
                            '平均风险': f"{data['avg_risk']:.1%}",
                        })
                    st.table(pd.DataFrame(group_risk_rows))
                
                if distribution['top_warnings']:
                    st.markdown("##### 最常见警告类型")
                    warn_df = pd.DataFrame(distribution['top_warnings'], columns=['警告类型', '出现次数'])
                    st.table(warn_df)
                
                st.markdown("---")
                st.subheader("⬇️ 下载风险报告")
                
                report_rows = []
                for r in all_results:
                    report_rows.append({
                        'player_id': r.player_id,
                        'skill_group': r.skill_group,
                        'churn_probability': r.churn_probability,
                        'risk_level': r.risk_level,
                        'intervention_priority': r.intervention_priority,
                        'difficulty_stress': r.risk_factors.difficulty_stress,
                        'frustration_risk': r.risk_factors.frustration_risk,
                        'boredom_risk': r.risk_factors.boredom_risk,
                        'behavior_risk': r.risk_factors.behavior_risk,
                        'engagement_risk': r.risk_factors.engagement_risk,
                        'skill_progress_risk': r.risk_factors.skill_progress_risk,
                        'num_warnings': len(r.warnings),
                    })
                
                report_df = pd.DataFrame(report_rows)
                csv = report_df.to_csv(index=False).encode('utf-8')
                st.download_button(
                    "📥 下载完整风险报告 CSV",
                    csv,
                    f"churn_risk_report_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    "text/csv",
                    key='download-churn-report'
                )
    
    with tab3:
        st.subheader("📊 整体流失风险分布")
        
        if df_players is not None and len(df_players) > 0:
            col_t1, col_t2 = st.columns(2)
            
            with col_t1:
                st.markdown("##### 各分群愤怒流失率")
                group_rage = df_players.groupby('skill_group')['is_rage_quit'].mean().reset_index()
                group_rage['group_name'] = group_rage['skill_group'].map(lambda x: SKILL_GROUPS[x]['name'])
                group_rage['color'] = group_rage['skill_group'].map(lambda x: SKILL_GROUPS[x]['color'])
                
                fig = go.Figure(go.Bar(
                    x=group_rage['group_name'],
                    y=group_rage['is_rage_quit'] * 100,
                    marker_color=group_rage['color'],
                    text=[f"{v:.1f}%" for v in group_rage['is_rage_quit'] * 100],
                    textposition='auto',
                ))
                fig.update_layout(
                    title='各技能分群愤怒流失率 (%)',
                    yaxis_title='愤怒流失率 (%)',
                    height=350
                )
                st.plotly_chart(fig, use_container_width=True)
            
            with col_t2:
                st.markdown("##### 失败次数与流失关系")
                if 'attempts' in df_players.columns and 'is_rage_quit' in df_players.columns:
                    rage_by_attempts = df_players.groupby(pd.cut(df_players['attempts'], bins=[0, 2, 5, 10, 20, 100]))['is_rage_quit'].mean()
                    rage_by_attempts = rage_by_attempts.reset_index()
                    rage_by_attempts.columns = ['attempts_bin', 'rage_rate']
                    rage_by_attempts['attempts_bin'] = rage_by_attempts['attempts_bin'].astype(str)
                    
                    fig = go.Figure(go.Line(
                        x=rage_by_attempts['attempts_bin'],
                        y=rage_by_attempts['rage_rate'] * 100,
                        mode='lines+markers',
                        line=dict(color='#ef4444', width=3),
                        marker=dict(size=10)
                    ))
                    fig.update_layout(
                        title='尝试次数与愤怒流失率关系',
                        xaxis_title='尝试次数区间',
                        yaxis_title='愤怒流失率 (%)',
                        height=350
                    )
                    st.plotly_chart(fig, use_container_width=True)
            
            st.markdown("---")
            
            if 'base_difficulty_score' in df_players.columns:
                col_d1, col_d2 = st.columns(2)
                
                with col_d1:
                    st.markdown("##### 难度评分与流失关系")
                    df_players['difficulty_bin'] = pd.cut(df_players['base_difficulty_score'], bins=10)
                    rage_by_diff = df_players.groupby('difficulty_bin')['is_rage_quit'].mean().reset_index()
                    rage_by_diff['difficulty_bin'] = rage_by_diff['difficulty_bin'].astype(str)
                    
                    fig = go.Figure(go.Scatter(
                        x=rage_by_diff['difficulty_bin'],
                        y=rage_by_diff['is_rage_quit'] * 100,
                        mode='lines+markers',
                        line=dict(color='#f97316', width=3),
                        marker=dict(size=10)
                    ))
                    fig.update_layout(
                        title='关卡难度与愤怒流失率',
                        xaxis_title='难度评分区间',
                        yaxis_title='愤怒流失率 (%)',
                        height=350
                    )
                    st.plotly_chart(fig, use_container_width=True)
                
                with col_d2:
                    st.markdown("##### 挫败指数分布")
                    if 'novice_frustration_index' in df_players.columns:
                        fig = go.Figure()
                        for group in SKILL_GROUP_ORDER:
                            col = f'{group}_frustration_index'
                            if col in df_players.columns:
                                fig.add_trace(go.Histogram(
                                    x=df_players[col] * 100,
                                    name=SKILL_GROUPS[group]['name'],
                                    marker_color=SKILL_GROUPS[group]['color'],
                                    opacity=0.6,
                                    nbinsx=20
                                ))
                        fig.update_layout(
                            title='各分群挫败指数分布',
                            xaxis_title='挫败指数 (%)',
                            yaxis_title='频次',
                            barmode='overlay',
                            height=350
                        )
                        st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("请先生成游戏数据以查看流失风险分布统计")


if __name__ == "__main__":
    main()
