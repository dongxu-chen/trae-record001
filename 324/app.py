import sys
import os
import numpy as np
import pandas as pd
from datetime import datetime, date
import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import GENRES, PLATFORMS, TIME_SLOTS, ACTOR_POPULARITY
from data_generator import generate_drama_basic_info, generate_episodic_ratings, generate_social_media_data
from sentiment_analyzer import analyze_sentiment, generate_comments, aggregate_episode_sentiment, get_top_keywords, generate_episode_comments_batch
from prediction_engine import RatingPredictionEngine
from utils import smooth_curve, calculate_trend

st.set_page_config(
    page_title="电视剧收视率预测系统",
    page_icon="📺",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
    <style>
    .main-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 25px;
        border-radius: 15px;
        margin-bottom: 25px;
        color: white;
        box-shadow: 0 4px 15px rgba(0,0,0,0.1);
    }
    .main-header h1 {
        color: white;
        margin: 0;
        font-size: 28px;
        font-weight: 700;
    }
    .main-header p {
        color: rgba(255,255,255,0.9);
        margin: 5px 0 0 0;
        font-size: 14px;
    }
    .section-card {
        background: white;
        padding: 20px;
        border-radius: 12px;
        box-shadow: 0 2px 10px rgba(0,0,0,0.08);
        margin-bottom: 20px;
    }
    .section-title {
        font-size: 18px;
        font-weight: 600;
        color: #333;
        margin-bottom: 15px;
        padding-bottom: 10px;
        border-bottom: 2px solid #f0f0f0;
    }
    .metric-box {
        background: linear-gradient(135deg, #f5f7fa 0%, #e4e8ec 100%);
        padding: 15px;
        border-radius: 10px;
        text-align: center;
        border-left: 4px solid #667eea;
    }
    .metric-value {
        font-size: 24px;
        font-weight: 700;
        color: #667eea;
    }
    .metric-label {
        font-size: 12px;
        color: #666;
        margin-top: 5px;
    }
    .recommendation-high {
        background: linear-gradient(135deg, #d4edda 0%, #c3e6cb 100%);
        padding: 15px;
        border-radius: 10px;
        border-left: 4px solid #28a745;
    }
    .recommendation-medium {
        background: linear-gradient(135deg, #fff3cd 0%, #ffeeba 100%);
        padding: 15px;
        border-radius: 10px;
        border-left: 4px solid #ffc107;
    }
    .recommendation-low {
        background: linear-gradient(135deg, #f8d7da 0%, #f5c6cb 100%);
        padding: 15px;
        border-radius: 10px;
        border-left: 4px solid #dc3545;
    }
    .peak-badge {
        background: linear-gradient(135deg, #ff6b6b 0%, #ee5a24 100%);
        color: white;
        padding: 3px 10px;
        border-radius: 20px;
        font-size: 11px;
        font-weight: 600;
    }
    .stButton button {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border: none;
        padding: 10px 25px;
        border-radius: 8px;
        font-weight: 600;
        width: 100%;
    }
    .stButton button:hover {
        opacity: 0.9;
        box-shadow: 0 4px 15px rgba(102, 126, 234, 0.4);
    }
    </style>
""", unsafe_allow_html=True)

@st.cache_resource(show_spinner=False)
def initialize_engine(num_dramas=30):
    engine = RatingPredictionEngine()
    with st.spinner("正在初始化预测模型，这可能需要几分钟..."):
        engine.train_models(num_dramas=num_dramas)
    return engine

def main():
    st.markdown("""
        <div class="main-header">
            <h1>📺 电视剧收视率预测系统</h1>
            <p>基于 XGBoost + LSTM + 情感分析的智能收视率预测与分析平台</p>
        </div>
    """, unsafe_allow_html=True)
    
    with st.sidebar:
        st.header("⚙️ 预测设置")
        
        drama_name = st.text_input("剧集名称", value="示例电视剧")
        
        genre = st.selectbox("题材", GENRES, index=0)
        platform = st.selectbox("播出平台", PLATFORMS, index=0)
        time_slot = st.selectbox("播出时段", TIME_SLOTS, index=0)
        actor_level = st.selectbox("演员阵容", list(ACTOR_POPULARITY.keys()), index=1)
        
        num_episodes = st.slider("集数", 12, 48, 40, step=4)
        
        col1, col2 = st.columns(2)
        with col1:
            production_budget = st.slider("制作预算(万)", 5000, 50000, 25000, step=1000)
        with col2:
            director_reputation = st.slider("导演声望", 0.3, 1.0, 0.7, step=0.1)
        
        is_sequel = st.checkbox("是否续集", value=False)
        
        st.subheader("📅 播出日期")
        start_date = st.date_input("首播日期", value=date(2024, 6, 1))
        
        st.subheader("📊 已知数据")
        n_known = st.slider("已知收视集数", 0, 20, 5)
        
        train_button = st.button("🚀 开始预测分析")
        
        st.markdown("---")
        st.caption("💡 系统使用XGBoost(60%) + LSTM(40%)加权集成预测")
    
    engine = initialize_engine(num_dramas=20)
    
    if train_button:
        run_prediction(
            engine, drama_name, genre, platform, time_slot, actor_level,
            num_episodes, production_budget, director_reputation, is_sequel,
            start_date, n_known
        )
    else:
        show_intro()

def show_intro():
    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">🎯 系统功能介绍</div>', unsafe_allow_html=True)
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown("""
        <div class="metric-box">
            <div class="metric-value">📈</div>
            <div class="metric-label">收视率曲线预测<br/>XGBoost + LSTM 加权融合</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown("""
        <div class="metric-box">
            <div class="metric-value">⚡</div>
            <div class="metric-label">爆点预测<br/>识别收视峰值集数</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown("""
        <div class="metric-box">
            <div class="metric-value">💬</div>
            <div class="metric-label">情感分析<br/>社交媒体评论情感挖掘</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        st.markdown("""
        <div class="metric-box">
            <div class="metric-value">✅</div>
            <div class="metric-label">续订建议<br/>多维度评分决策系统</div>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">🔧 技术架构</div>', unsafe_allow_html=True)
    
    st.markdown("""
    ### 核心模型
    - **XGBoost**: 处理剧集特征（题材、演员、平台、时段等）和社交媒体特征，擅长捕捉非线性关系
    - **LSTM**: 处理时间序列特征，学习收视率的时序依赖和趋势变化
    - **情感分析**: 基于词典的中文情感分析算法，分析社交媒体评论情感倾向
    - **模型集成**: 采用加权融合策略（XGBoost 60% + LSTM 40%）
    
    ### 输入特征
    | 类别 | 特征 |
    |------|------|
    | 剧集特征 | 题材、演员阵容、播出平台、播出时段、集数、制作预算、导演声望、是否续集 |
    | 历史数据 | 前N集收视率、收视率变化、移动平均 |
    | 社交媒体 | 发帖量、转发量、点赞量、评论量、搜索指数、情感得分 |
    | 时间特征 | 播出日期、星期几、是否周末、季节 |
    
    ### 输出指标
    - 📊 每集收视率预测曲线
    - ⚡ 收视爆点预测（哪集可能出现峰值）
    - ✅ 续订建议（百分制评分 + 决策建议）
    - 💬 社交媒体情感分析报告
    """)
    st.markdown('</div>', unsafe_allow_html=True)

def run_prediction(engine, drama_name, genre, platform, time_slot, actor_level,
                   num_episodes, production_budget, director_reputation, is_sequel,
                   start_date, n_known):
    
    drama_info = {
        'drama_id': 'CUSTOM001',
        'drama_name': drama_name,
        'genre': genre,
        'platform': platform,
        'time_slot': time_slot,
        'actor_level': actor_level,
        'num_episodes': num_episodes,
        'production_budget': production_budget,
        'director_reputation': director_reputation,
        'is_sequel': 1 if is_sequel else 0,
        'start_date': datetime(start_date.year, start_date.month, start_date.day)
    }
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    status_text.text("1/5 生成剧集数据...")
    dates, true_ratings = generate_episodic_ratings(drama_info)
    progress_bar.progress(20)
    
    status_text.text("2/5 生成社交媒体数据...")
    social_df = generate_social_media_data(drama_info, dates, true_ratings)
    progress_bar.progress(40)
    
    status_text.text("3/5 生成评论并进行情感分析...")
    comments_df = generate_episode_comments_batch(drama_info, dates, true_ratings)
    sentiment_stats = aggregate_episode_sentiment(comments_df)
    progress_bar.progress(60)
    
    status_text.text("4/5 执行收视率预测...")
    initial_ratings = true_ratings[:n_known] if n_known > 0 else []
    report = engine.generate_full_prediction_report(
        drama_info, dates, initial_ratings, social_df, comments_df
    )
    progress_bar.progress(80)
    
    status_text.text("5/5 生成分析报告...")
    eval_results = engine.get_model_evaluation(drama_info, dates, true_ratings, social_df, n_known)
    progress_bar.progress(100)
    
    status_text.empty()
    progress_bar.empty()
    
    display_results(report, comments_df, sentiment_stats, eval_results, true_ratings, n_known)

def display_results(report, comments_df, sentiment_stats, eval_results, true_ratings, n_known):
    drama_info = report['drama_info']
    
    st.markdown(f'<div class="section-card">', unsafe_allow_html=True)
    st.markdown(f'<div class="section-title">🎬 {drama_info["drama_name"]} - 预测概览</div>', unsafe_allow_html=True)
    
    col1, col2, col3, col4, col5 = st.columns(5)
    
    summary = report['prediction_summary']
    
    with col1:
        st.markdown(f"""
        <div class="metric-box">
            <div class="metric-value">{summary['avg_predicted']:.2f}%</div>
            <div class="metric-label">平均预测收视率</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
        <div class="metric-box">
            <div class="metric-value">{summary['max_predicted']:.2f}%</div>
            <div class="metric-label">最高预测收视率</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        trend_text = "↑ 上升" if summary['trend'] > 0.01 else ("↓ 下降" if summary['trend'] < -0.01 else "→ 平稳")
        trend_color = "#28a745" if summary['trend'] > 0.01 else ("#dc3545" if summary['trend'] < -0.01 else "#ffc107")
        st.markdown(f"""
        <div class="metric-box">
            <div class="metric-value" style="color: {trend_color}">{trend_text}</div>
            <div class="metric-label">收视趋势</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        st.markdown(f"""
        <div class="metric-box">
            <div class="metric-value">{summary['known_episodes']}/{summary['total_episodes']}</div>
            <div class="metric-label">已知/总集数</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col5:
        peak_count = len(report['peak_episodes'])
        st.markdown(f"""
        <div class="metric-box">
            <div class="metric-value">{peak_count}</div>
            <div class="metric-label">预测爆点数量</div>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "🎬 首播预测",
        "📈 收视率预测曲线",
        "⚡ 爆点预测分析",
        "✅ 续订建议",
        "💬 情感分析",
        "🔍 详细数据"
    ])
    
    with tab1:
        show_premiere_prediction(report)
    
    with tab2:
        show_ratings_chart(report, true_ratings, n_known, eval_results)
    
    with tab3:
        show_peak_analysis(report)
    
    with tab4:
        show_renewal_recommendation(report)
    
    with tab5:
        show_sentiment_analysis(report, comments_df, sentiment_stats)
    
    with tab6:
        show_detailed_data(report)

def show_ratings_chart(report, true_ratings, n_known, eval_results):
    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">📈 收视率预测曲线</div>', unsafe_allow_html=True)
    
    episodes = list(range(1, len(true_ratings) + 1))
    ensemble_preds = report['predictions']['ensemble_predictions']
    xgb_preds = report['predictions']['xgb_predictions']
    lstm_preds = report['predictions']['lstm_predictions']
    
    fig = go.Figure()
    
    fig.add_trace(go.Scatter(
        x=episodes[:n_known],
        y=true_ratings[:n_known],
        mode='lines+markers',
        name='已知真实收视率',
        line=dict(color='#28a745', width=3),
        marker=dict(size=8, color='#28a745', line=dict(width=2, color='white'))
    ))
    
    fig.add_trace(go.Scatter(
        x=episodes,
        y=ensemble_preds,
        mode='lines+markers',
        name='集成预测 (60% XGB + 40% LSTM)',
        line=dict(color='#667eea', width=3, dash='solid'),
        marker=dict(size=6, color='#667eea')
    ))
    
    fig.add_trace(go.Scatter(
        x=episodes,
        y=xgb_preds,
        mode='lines',
        name='XGBoost 预测',
        line=dict(color='#f39c12', width=2, dash='dash'),
        opacity=0.7
    ))
    
    fig.add_trace(go.Scatter(
        x=episodes,
        y=lstm_preds,
        mode='lines',
        name='LSTM 预测',
        line=dict(color='#e74c3c', width=2, dash='dot'),
        opacity=0.7
    ))
    
    if n_known > 0:
        fig.add_vline(
            x=n_known + 0.5,
            line_dash="dash",
            line_color="gray",
            annotation_text="预测起点"
        )
    
    peak_episodes = [p['episode'] for p in report['peak_episodes']]
    peak_ratings = [p['predicted_rating'] for p in report['peak_episodes']]
    if peak_episodes:
        fig.add_trace(go.Scatter(
            x=peak_episodes,
            y=peak_ratings,
            mode='markers',
            name='预测爆点',
            marker=dict(size=15, color='#e74c3c', symbol='star', line=dict(width=2, color='white')),
            text=[f'第{ep}集<br/>收视率: {rate:.2f}%' for ep, rate in zip(peak_episodes, peak_ratings)]
        ))
    
    fig.update_layout(
        title='收视率预测对比图',
        xaxis_title='集数',
        yaxis_title='收视率 (%)',
        height=500,
        hovermode='x unified',
        legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1),
        margin=dict(l=50, r=50, t=80, b=50)
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">📊 模型预测精度评估</div>', unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns(3)
    
    for i, (name, metrics) in enumerate(eval_results.items()):
        with [col1, col2, col3][i]:
            display_name = {
                'xgb_predictions': 'XGBoost',
                'lstm_predictions': 'LSTM',
                'ensemble_predictions': '集成模型'
            }.get(name, name)
            
            st.markdown(f"""
            <div class="metric-box">
                <div class="metric-value" style="font-size: 18px">{display_name}</div>
                <div style="margin-top: 10px;">
                    <div style="font-size: 14px; color: #666;">RMSE: <b>{metrics['rmse']:.4f}</b></div>
                    <div style="font-size: 14px; color: #666;">MAPE: <b>{metrics['mape']:.2f}%</b></div>
                </div>
            </div>
            """, unsafe_allow_html=True)
    
    st.caption("RMSE: 均方根误差（越小越好） | MAPE: 平均绝对百分比误差（越小越好）")
    st.markdown('</div>', unsafe_allow_html=True)

def show_peak_analysis(report):
    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">⚡ 爆点预测分析</div>', unsafe_allow_html=True)
    
    peak_episodes = report['peak_episodes']
    
    if not peak_episodes:
        st.info("未检测到明显的收视爆点，收视表现相对平稳。")
    else:
        cols = st.columns(min(3, len(peak_episodes)))
        
        for i, peak in enumerate(peak_episodes):
            with cols[i % len(cols)]:
                confidence_level = "高" if peak['confidence'] > 0.7 else ("中" if peak['confidence'] > 0.5 else "低")
                confidence_color = "#28a745" if peak['confidence'] > 0.7 else ("#ffc107" if peak['confidence'] > 0.5 else "#dc3545")
                
                st.markdown(f"""
                <div style="background: linear-gradient(135deg, #fff5f5 0%, #ffe0e0 100%); 
                            padding: 20px; border-radius: 12px; border: 2px solid #ff6b6b; text-align: center;">
                    <div style="font-size: 14px; color: #666; margin-bottom: 5px;">第 {peak['episode']} 集</div>
                    <div style="font-size: 32px; font-weight: 700; color: #e74c3c;">
                        {peak['predicted_rating']:.2f}%
                    </div>
                    <div style="font-size: 13px; color: #666; margin-top: 8px;">
                        较平均值 <span style="color: #e74c3c; font-weight: 600;">+{peak['increase_percent']:.1f}%</span>
                    </div>
                    <div style="margin-top: 10px;">
                        <span style="background: {confidence_color}; color: white; padding: 3px 10px; 
                                     border-radius: 20px; font-size: 11px; font-weight: 600;">
                            置信度: {confidence_level} ({peak['confidence']:.2f})
                        </span>
                    </div>
                </div>
                """, unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">📈 爆点原因分析</div>', unsafe_allow_html=True)
    
    reasons = [
        "📺 **剧情转折点**: 故事进入高潮阶段，关键冲突爆发",
        "🎭 **角色重大事件**: 主要角色命运发生重大变化",
        "💑 **感情线突破**: 核心CP关系出现关键进展",
        "🔍 **悬念揭晓**: 前期铺垫的悬念或谜题揭晓",
        "🎬 **制作亮点**: 某集在导演、演技或特效上有突出表现",
        "📢 **宣发加成**: 配合剧集播出的营销活动带动收视",
        "📅 **档期效应**: 节假日或特殊档期带来的收视红利",
        "🔥 **话题热度**: 社交媒体讨论热度带动收视增长"
    ]
    
    for reason in reasons:
        st.markdown(f"- {reason}")
    
    st.markdown('</div>', unsafe_allow_html=True)

def show_renewal_recommendation(report):
    renewal = report['renewal_recommendation']
    score = renewal['total_score']
    
    if score >= 65:
        box_class = 'recommendation-high'
        icon = '✅'
    elif score >= 40:
        box_class = 'recommendation-medium'
        icon = '⚠️'
    else:
        box_class = 'recommendation-low'
        icon = '❌'
    
    st.markdown(f'<div class="{box_class}">', unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col1:
        st.markdown(f"""
        <div style="text-align: center;">
            <div style="font-size: 60px;">{icon}</div>
            <div style="font-size: 48px; font-weight: 700; margin-top: 10px;">{score:.1f}</div>
            <div style="font-size: 14px; color: #666;">综合评分 / 100</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
        <div style="padding-left: 30px;">
            <div style="font-size: 24px; font-weight: 700; margin-bottom: 10px;">
                {renewal['recommendation']}
            </div>
            <div style="font-size: 14px; color: #666; margin-bottom: 15px;">
                决策置信度: <b>{renewal['confidence']}</b>
            </div>
            <div style="font-size: 14px;">
                <b>📝 关键依据:</b>
                <ul style="margin-top: 10px;">
                    {"".join(f"<li>{reason}</li>" for reason in renewal['key_reasons'])}
                </ul>
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        stats = renewal['summary_stats']
        st.markdown(f"""
        <div style="font-size: 13px;">
            <div style="margin-bottom: 8px;">📊 平均收视: <b>{stats['avg_rating']:.2f}%</b></div>
            <div style="margin-bottom: 8px;">📈 最高收视: <b>{stats['max_rating']:.2f}%</b></div>
            <div style="margin-bottom: 8px;">📉 最低收视: <b>{stats['min_rating']:.2f}%</b></div>
            <div style="margin-bottom: 8px;">↗️ 趋势: <b>{stats['rating_trend']:.4f}</b></div>
            <div style="margin-bottom: 8px;">💓 情感: <b>{stats['avg_sentiment']:.2f}</b></div>
            <div style="margin-bottom: 8px;">🔍 搜索指数: <b>{stats['avg_search_index']}</b></div>
            <div style="margin-bottom: 8px;">📱 发帖量: <b>{stats['total_post_volume']:,}</b></div>
            <div>⚖️ 稳定性: <b>{stats['stability_index']:.2f}</b></div>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">📊 评分维度详情</div>', unsafe_allow_html=True)
    
    factors = renewal['factors']
    
    factor_df = pd.DataFrame([
        {
            '维度': {
                'avg_rating': '平均收视率',
                'trend': '收视趋势',
                'peak_rating': '峰值收视率',
                'sentiment': '观众情感',
                'actor_level': '演员阵容',
                'is_sequel': '续集效应',
                'search_index': '搜索热度',
                'stability': '收视稳定性'
            }.get(k, k),
            '得分': v['score'],
            '权重': v['weight'],
            '实际值': str(v['value'])
        }
        for k, v in factors.items()
    ])
    
    fig = go.Figure()
    
    fig.add_trace(go.Bar(
        y=factor_df['维度'],
        x=factor_df['得分'],
        orientation='h',
        text=factor_df.apply(lambda x: f"{x['得分']}/{x['权重']}", axis=1),
        textposition='auto',
        marker=dict(
            color=factor_df['得分'],
            colorscale='RdYlGn',
            cmin=0,
            cmax=factor_df['权重'].max()
        ),
        base=0
    ))
    
    fig.update_layout(
        title='各维度得分详情 (得分/权重)',
        xaxis_title='得分',
        yaxis_title='维度',
        height=400,
        margin=dict(l=120, r=50, t=50, b=50)
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    st.dataframe(factor_df, use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)
    
    if 'revenue_analysis' in renewal:
        show_revenue_analysis(renewal['revenue_analysis'])

def show_revenue_analysis(revenue_analysis):
    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">💰 收益模型分析</div>', unsafe_allow_html=True)
    
    profit = revenue_analysis['profit_metrics']
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown(f"""
        <div class="metric-box">
            <div class="metric-value" style="font-size: 20px">
                {'📈' if profit['net_profit'] >= 0 else '📉'}
            </div>
            <div style="font-size: 18px; font-weight: 700; color: {'#28a745' if profit['net_profit'] >= 0 else '#dc3545'};">
                {profit['net_profit']/10000:.1f}万
            </div>
            <div class="metric-label">预计净利润</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
        <div class="metric-box">
            <div class="metric-value" style="font-size: 20px">📊</div>
            <div style="font-size: 18px; font-weight: 700; color: {'#28a745' if profit['roi'] >= 0.1 else '#dc3545'};">
                {profit['roi']*100:.1f}%
            </div>
            <div class="metric-label">投资回报率 (ROI)</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        payback = profit['payback_period_years']
        payback_text = f"{payback:.1f}年" if isinstance(payback, (int, float)) else payback
        st.markdown(f"""
        <div class="metric-box">
            <div class="metric-value" style="font-size: 20px">⏱️</div>
            <div style="font-size: 18px; font-weight: 700;">
                {payback_text}
            </div>
            <div class="metric-label">投资回收期</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        st.markdown(f"""
        <div class="metric-box">
            <div class="metric-value" style="font-size: 20px">📈</div>
            <div style="font-size: 18px; font-weight: 700; color: {'#28a745' if profit['net_margin'] >= 0.2 else '#ffc107'};">
                {profit['net_margin']*100:.1f}%
            </div>
            <div class="metric-label">净利率</div>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">📊 收入与成本构成</div>', unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    
    with col1:
        revenue_data = revenue_analysis['revenue_breakdown']
        fig_rev = go.Figure(data=[go.Pie(
            labels=list(revenue_data.keys()),
            values=list(revenue_data.values()),
            marker=dict(colors=['#667eea', '#764ba2', '#f093fb', '#f5576c']),
            textinfo='label+percent',
            textposition='inside'
        )])
        fig_rev.update_layout(title='收入构成', height=350)
        st.plotly_chart(fig_rev, use_container_width=True)
        
        st.markdown("""
        **收入来源说明:**
        - 💰 **广告收入**: 基于收视率计算的贴片广告收益
        - 📺 **版权费用**: 平台购买剧集的版权费
        - 🌍 **海外发行**: 海外市场发行收入（版权费×15%）
        - 🎮 **IP衍生**: 游戏、动漫等衍生产品收入（版权费×10%）
        """)
    
    with col2:
        cost_data = revenue_analysis['cost_breakdown']
        fig_cost = go.Figure(data=[go.Pie(
            labels=list(cost_data.keys()),
            values=list(cost_data.values()),
            marker=dict(colors=['#e74c3c', '#f39c12', '#e67e22']),
            textinfo='label+percent',
            textposition='inside'
        )])
        fig_cost.update_layout(title='成本构成', height=350)
        st.plotly_chart(fig_cost, use_container_width=True)
        
        total_rev = sum(revenue_data.values()) / 10000
        total_cost = sum(cost_data.values()) / 10000
        net_profit = profit['net_profit'] / 10000
        
        st.markdown(f"""
        **成本说明:**
        - 🎬 **制作成本**: {cost_data['制作成本']/10000:,.0f}万
        - 📋 **运营成本**: {cost_data['运营成本']/10000:,.0f}万 (营收×40%)
        - 💸 **税收**: {cost_data['税收']/10000:,.0f}万 (利润×25%)
        
        **核心指标:**
        - 总收入: **{total_rev:,.0f}** 万元
        - 总成本: **{total_cost:,.0f}** 万元
        - 净利润: **{net_profit:,.0f}** 万元
        """)
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">📈 收益评分维度</div>', unsafe_allow_html=True)
    
    revenue_score_df = pd.DataFrame([
        {'维度': 'ROI回报率', '得分': revenue_analysis['revenue_score'] * 0.3, '权重': 30, '满分': 30},
        {'维度': '净利润额', '得分': revenue_analysis['revenue_score'] * 0.25, '权重': 25, '满分': 25},
        {'维度': '投资回收期', '得分': revenue_analysis['revenue_score'] * 0.15, '权重': 15, '满分': 15},
        {'维度': '净利率', '得分': revenue_analysis['revenue_score'] * 0.2, '权重': 20, '满分': 20},
        {'维度': '收视调整', '得分': revenue_analysis['revenue_score'] * 0.1, '权重': 10, '满分': 10}
    ])
    
    fig = go.Figure(go.Bar(
        x=revenue_score_df['维度'],
        y=revenue_score_df['得分'],
        text=revenue_score_df.apply(lambda x: f"{x['得分']:.1f}/{x['满分']}", axis=1),
        textposition='auto',
        marker=dict(
            color=revenue_score_df['得分'],
            colorscale='Viridis',
            cmin=0,
            cmax=revenue_score_df['满分'].max()
        )
    ))
    
    fig.update_layout(
        title='收益模型评分构成 (满分90)',
        yaxis_title='得分',
        height=350
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    st.markdown(f"""
    **评分融合机制:**
    - 基础评分（收视+情感等）: **{revenue_analysis['base_score']:.1f}** / 100 (权重40%)
    - 收益评分（ROI+利润等）: **{revenue_analysis['revenue_score']:.1f}** / 90 (权重60%)
    - **最终综合评分**: **{revenue_analysis['combined_score']:.1f}** / 100
    """)
    
    st.markdown('</div>', unsafe_allow_html=True)

def show_premiere_prediction(report):
    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">🎬 首播收视率预测</div>', unsafe_allow_html=True)
    
    if report.get('premiere_prediction') is None or report.get('trailer_heat') is None:
        st.info("暂无首播预测数据，请重新生成预测。")
        st.markdown('</div>', unsafe_allow_html=True)
        return
    
    premiere = report['premiere_prediction']
    heat_df = report['trailer_heat']
    
    col1, col2, col3 = st.columns([1, 1, 1])
    
    with col1:
        st.markdown(f"""
        <div class="metric-box" style="border-left-color: #667eea;">
            <div style="font-size: 14px; color: #666; margin-bottom: 5px;">预测首播收视率</div>
            <div style="font-size: 36px; font-weight: 700; color: #667eea;">
                {premiere['predicted_rating']:.2f}%
            </div>
            <div style="font-size: 12px; color: #999; margin-top: 8px;">
                预测区间: [{premiere['lower_bound']:.2f}, {premiere['upper_bound']:.2f}]
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        confidence = premiere['confidence']
        conf_level = "高" if confidence > 0.75 else ("中" if confidence > 0.55 else "低")
        conf_color = "#28a745" if confidence > 0.75 else ("#ffc107" if confidence > 0.55 else "#dc3545")
        st.markdown(f"""
        <div class="metric-box" style="border-left-color: {conf_color};">
            <div style="font-size: 14px; color: #666; margin-bottom: 5px;">预测置信度</div>
            <div style="font-size: 36px; font-weight: 700; color: {conf_color};">
                {confidence:.1%}
            </div>
            <div style="font-size: 12px; color: #999; margin-top: 8px;">
                置信等级: {conf_level}
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        metrics = premiere['key_metrics']
        st.markdown(f"""
        <div class="metric-box" style="border-left-color: #f39c12;">
            <div style="font-size: 14px; color: #666; margin-bottom: 5px;">累计预告片播放</div>
            <div style="font-size: 28px; font-weight: 700; color: #f39c12;">
                {metrics['cumulative_views']:,}
            </div>
            <div style="font-size: 12px; color: #999; margin-top: 8px;">
                最终搜索指数: {metrics['final_search_index']:,}
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">🔥 预告片热度趋势（首播前30天）</div>', unsafe_allow_html=True)
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        fig = go.Figure()
        
        fig.add_trace(go.Scatter(
            x=heat_df['days_to_premiere'],
            y=heat_df['trailer_views'],
            mode='lines+markers',
            name='预告片播放量',
            line=dict(color='#667eea', width=2),
            fill='tozeroy',
            fillcolor='rgba(102, 126, 234, 0.1)'
        ))
        
        fig.add_trace(go.Scatter(
            x=heat_df['days_to_premiere'],
            y=heat_df['search_index'],
            mode='lines+markers',
            name='搜索指数',
            line=dict(color='#e74c3c', width=2),
            yaxis='y2'
        ))
        
        fig.update_layout(
            title='首播前热度变化',
            xaxis=dict(title='距首播天数', autorange='reversed'),
            yaxis=dict(title='预告片播放量', side='left'),
            yaxis2=dict(title='搜索指数', side='right', overlaying='y', showgrid=False),
            height=400,
            legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1),
            margin=dict(l=50, r=50, t=80, b=50)
        )
        
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        contribution = premiere['feature_contribution']
        contrib_df = pd.DataFrame([
            {'因素': {'trailer_heat': '预告片热度', 'cast_heat': '演员阵容', 
                     'platform': '播出平台', 'genre': '题材类型', 'marketing': '营销热度'}.get(k, k),
             '权重': v['weight'],
             '贡献度': v['contribution']}
            for k, v in contribution.items()
        ])
        
        fig = go.Figure(go.Bar(
            x=contrib_df['因素'],
            y=contrib_df['贡献度'],
            text=contrib_df.apply(lambda x: f"权重{x['权重']:.0%}<br>贡献{x['贡献度']:.2f}", axis=1),
            textposition='auto',
            marker=dict(
                color=['#667eea', '#764ba2', '#f093fb', '#f5576c', '#4facfe'],
            )
        ))
        
        fig.update_layout(
            title='各因素贡献度',
            yaxis_title='贡献系数',
            height=400
        )
        
        st.plotly_chart(fig, use_container_width=True)
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">📊 首播前热度指标详情</div>', unsafe_allow_html=True)
    
    heat_7d = heat_df.tail(7)
    
    metric_cols = st.columns(4)
    metrics_to_show = [
        ('累计播放量', heat_df['cumulative_trailer_views'].iloc[-1], '次'),
        ('7天平均播放', heat_7d['trailer_views'].mean(), '次'),
        ('话题阅读量', heat_7d['topic_reading'].sum(), '次'),
        ('热度动量', metrics['heat_momentum'], '%')
    ]
    
    for i, (name, value, unit) in enumerate(metrics_to_show):
        with metric_cols[i]:
            st.metric(name, f"{value:,.0f}{unit}")
    
    display_cols = ['days_to_premiere', 'trailer_views', 'search_index', 'topic_reading', 
                   'actor_heat', 'composite_heat_score', 'heat_momentum']
    col_names = ['距首播', '播放量', '搜索指数', '话题阅读', '演员热度', '综合热度', '热度动量%']
    
    display_df = heat_df[display_cols].tail(14).copy()
    display_df.columns = col_names
    display_df = display_df.sort_values('距首播')
    
    st.dataframe(display_df, use_container_width=True, height=300)
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    if report.get('time_gate_analysis') is not None:
        st.markdown('<div class="section-card">', unsafe_allow_html=True)
        st.markdown('<div class="section-title">⏰ LSTM时间间隔门分析</div>', unsafe_allow_html=True)
        
        time_gate = report['time_gate_analysis']
        
        col1, col2 = st.columns([1, 1])
        
        with col1:
            fig = go.Figure(go.Bar(
                x=time_gate['interval_days'],
                y=time_gate['information_retention'],
                text=time_gate['information_retention'].apply(lambda x: f"{x:.1f}%"),
                textposition='auto',
                marker=dict(
                    color=time_gate['information_retention'],
                    colorscale='RdYlGn',
                    cmin=0,
                    cmax=100
                )
            ))
            
            fig.update_layout(
                title='不同时间间隔的信息保留率',
                xaxis_title='时间间隔（天）',
                yaxis_title='信息保留率（%）',
                height=350
            )
            
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            st.markdown("""
            **时间间隔门原理:**
            
            LSTM时间间隔门通过显式建模相邻观测之间的时间间隔，实现对长期历史信息的动态衰减：
            
            1. **时间感知**: 计算每两个时间步之间的间隔天数
            2. **门控机制**: 根据间隔长度计算信息保留率
            3. **自适应衰减**: 
               - 间隔1天：保留约90%历史信息
               - 间隔3天：保留约75%历史信息  
               - 间隔7天：保留约60%历史信息
               - 间隔30天：仅保留约30%历史信息
            
            4. **可学习参数**: 衰减率可从数据中自动学习
            
            **优势**:
            - ✅ 更合理地处理周播、日播等不同播出模式
            - ✅ 长期间隔数据不会过度影响当前预测
            - ✅ 可适应不规则的播出时间安排
            """)
        
        st.markdown('</div>', unsafe_allow_html=True)

def show_sentiment_analysis(report, comments_df, sentiment_stats):
    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">💬 社交媒体情感分析</div>', unsafe_allow_html=True)
    
    episodes = sentiment_stats['episode'].tolist()
    
    fig = make_subplots(
        rows=2, cols=2,
        subplot_titles=('情感得分趋势', '情感类型分布', '情感得分分布', '评论数量趋势'),
        specs=[[{}, {}], [{}, {}]]
    )
    
    fig.add_trace(
        go.Scatter(
            x=episodes,
            y=sentiment_stats['avg_sentiment'],
            mode='lines+markers',
            name='平均情感得分',
            line=dict(color='#667eea', width=2),
            fill='tozeroy',
            fillcolor='rgba(102, 126, 234, 0.1)'
        ),
        row=1, col=1
    )
    
    type_counts = comments_df['type'].value_counts()
    fig.add_trace(
        go.Pie(
            labels=['正面', '中立', '负面'],
            values=[type_counts.get('positive', 0), type_counts.get('neutral', 0), type_counts.get('negative', 0)],
            marker=dict(colors=['#28a745', '#ffc107', '#dc3545']),
            textinfo='label+percent'
        ),
        row=1, col=2
    )
    
    fig.add_trace(
        go.Histogram(
            x=comments_df['sentiment'],
            nbinsx=20,
            marker=dict(color='#667eea', line=dict(width=1, color='white')),
            name='情感分布'
        ),
        row=2, col=1
    )
    
    fig.add_trace(
        go.Bar(
            x=episodes,
            y=sentiment_stats['comment_count'],
            marker=dict(color='#f39c12'),
            name='评论数量'
        ),
        row=2, col=2
    )
    
    fig.update_xaxes(title_text='集数', row=1, col=1)
    fig.update_xaxes(title_text='情感得分', row=2, col=1)
    fig.update_xaxes(title_text='集数', row=2, col=2)
    fig.update_yaxes(title_text='情感得分 (0-1)', row=1, col=1)
    fig.update_yaxes(title_text='评论数', row=2, col=1)
    fig.update_yaxes(title_text='评论数', row=2, col=2)
    
    fig.update_layout(height=700, showlegend=False)
    
    st.plotly_chart(fig, use_container_width=True)
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">🔍 热门关键词分析</div>', unsafe_allow_html=True)
    
    top_keywords = get_top_keywords(comments_df, top_n=15)
    
    if top_keywords:
        keywords_df = pd.DataFrame(top_keywords, columns=['关键词', '出现频次'])
        
        fig = go.Figure(go.Bar(
            x=keywords_df['出现频次'],
            y=keywords_df['关键词'],
            orientation='h',
            marker=dict(
                color=keywords_df['出现频次'],
                colorscale='Viridis'
            ),
            text=keywords_df['出现频次'],
            textposition='auto'
        ))
        
        fig.update_layout(
            title='高频关键词',
            xaxis_title='出现频次',
            yaxis_title='关键词',
            height=400,
            margin=dict(l=100, r=50, t=50, b=50)
        )
        
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("未检测到足够的关键词。")
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">📝 最新评论样本</div>', unsafe_allow_html=True)
    
    episode_to_show = st.selectbox("选择集数查看评论", episodes, index=len(episodes) - 1)
    episode_comments = comments_df[comments_df['episode'] == episode_to_show].head(20)
    
    for _, row in episode_comments.iterrows():
        sentiment_color = '#28a745' if row['type'] == 'positive' else ('#dc3545' if row['type'] == 'negative' else '#ffc107')
        type_label = '😊 正面' if row['type'] == 'positive' else ('😠 负面' if row['type'] == 'negative' else '😐 中立')
        
        st.markdown(f"""
        <div style="padding: 10px; margin-bottom: 8px; border-radius: 8px; 
                    border-left: 4px solid {sentiment_color}; background: #fafafa;">
            <div style="font-size: 14px; margin-bottom: 5px;">{row['comment']}</div>
            <div style="font-size: 12px; color: #999;">
                <span style="color: {sentiment_color}; font-weight: 600;">{type_label}</span>
                <span style="margin-left: 15px;">情感得分: {row['sentiment']:.2f}</span>
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">🤖 实时情感分析</div>', unsafe_allow_html=True)
    
    user_comment = st.text_input("输入一条评论进行情感分析", value="这部剧太好看了，演员演技在线！")
    
    if user_comment:
        sentiment_score = analyze_sentiment(user_comment)
        
        if sentiment_score >= 0.6:
            sentiment_type = '正面'
            sentiment_emoji = '😊'
            sentiment_color = '#28a745'
        elif sentiment_score >= 0.4:
            sentiment_type = '中立'
            sentiment_emoji = '😐'
            sentiment_color = '#ffc107'
        else:
            sentiment_type = '负面'
            sentiment_emoji = '😠'
            sentiment_color = '#dc3545'
        
        st.markdown(f"""
        <div style="text-align: center; padding: 20px;">
            <div style="font-size: 48px;">{sentiment_emoji}</div>
            <div style="font-size: 20px; font-weight: 600; color: {sentiment_color}; margin-top: 10px;">
                {sentiment_type}
            </div>
            <div style="font-size: 16px; color: #666; margin-top: 5px;">
                情感得分: <b>{sentiment_score:.2f}</b> (范围: 0.0 - 1.0)
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)

def show_detailed_data(report):
    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">🔍 每集详细数据</div>', unsafe_allow_html=True)
    
    details_df = report['episode_details'].copy()
    
    details_df['date'] = pd.to_datetime(details_df['date']).dt.strftime('%Y-%m-%d')
    
    column_mapping = {
        'episode': '集数',
        'date': '日期',
        'day_of_week': '星期',
        'is_weekend': '是否周末',
        'known_rating': '已知真实收视',
        'xgb_prediction': 'XGBoost预测',
        'lstm_prediction': 'LSTM预测',
        'ensemble_prediction': '集成预测',
        'is_peak': '是否爆点',
        'post_volume': '发帖量',
        'repost_volume': '转发量',
        'like_volume': '点赞量',
        'comment_volume': '评论量',
        'search_index': '搜索指数',
        'sentiment_score': '情感得分'
    }
    
    details_df = details_df.rename(columns=column_mapping)
    
    display_columns = [col for col in column_mapping.values() if col in details_df.columns]
    details_df = details_df[display_columns]
    
    def highlight_peaks(row):
        return ['background-color: #fff0f0; font-weight: bold' if row['是否爆点'] else '' for _ in row]
    
    st.dataframe(
        details_df.style.apply(highlight_peaks, axis=1),
        use_container_width=True,
        height=500
    )
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">📋 剧集基本信息</div>', unsafe_allow_html=True)
    
    drama_info = report['drama_info']
    
    info_df = pd.DataFrame([
        {'项目': '剧集名称', '值': drama_info['drama_name']},
        {'项目': '题材', '值': drama_info['genre']},
        {'项目': '播出平台', '值': drama_info['platform']},
        {'项目': '播出时段', '值': drama_info['time_slot']},
        {'项目': '演员阵容', '值': drama_info['actor_level']},
        {'项目': '总集数', '值': f"{drama_info['num_episodes']} 集"},
        {'项目': '制作预算', '值': f"{drama_info['production_budget']:,} 万元"},
        {'项目': '导演声望', '值': f"{drama_info['director_reputation']:.2f} / 1.0"},
        {'项目': '是否续集', '值': '是' if drama_info['is_sequel'] else '否'},
        {'项目': '首播日期', '值': drama_info['start_date'].strftime('%Y年%m月%d日') if isinstance(drama_info['start_date'], datetime) else str(drama_info['start_date'])}
    ])
    
    st.table(info_df)
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">📉 社交媒体热度趋势</div>', unsafe_allow_html=True)
    
    details_df = report['episode_details']
    episodes = details_df['episode'].tolist()
    
    fig = go.Figure()
    
    fig.add_trace(go.Scatter(
        x=episodes,
        y=details_df['search_index'],
        mode='lines+markers',
        name='搜索指数',
        yaxis='y',
        line=dict(color='#e74c3c', width=2)
    ))
    
    fig.add_trace(go.Scatter(
        x=episodes,
        y=details_df['post_volume'],
        mode='lines+markers',
        name='发帖量',
        yaxis='y2',
        line=dict(color='#3498db', width=2)
    ))
    
    fig.add_trace(go.Scatter(
        x=episodes,
        y=details_df['like_volume'],
        mode='lines+markers',
        name='点赞量',
        yaxis='y3',
        line=dict(color='#2ecc71', width=2)
    ))
    
    fig.update_layout(
        title='社交媒体热度多指标趋势',
        xaxis=dict(title='集数', domain=[0.3, 0.7]),
        yaxis=dict(title='搜索指数', side='left', position=0, showgrid=False),
        yaxis2=dict(title='发帖量', side='left', position=0.15, overlaying='y', showgrid=False),
        yaxis3=dict(title='点赞量', side='right', position=0.85, overlaying='y', showgrid=False),
        height=450,
        legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1)
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    st.markdown('</div>', unsafe_allow_html=True)

if __name__ == '__main__':
    main()
