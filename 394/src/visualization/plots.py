import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots


def create_sleep_stage_hypnogram(stages, timestamps, epoch_duration=30):
    stage_mapping = {'清醒': 3, 'REM': 2, '浅睡': 1, '深睡': 0}
    y_values = [stage_mapping[s] for s in stages]
    time_hours = [t * epoch_duration / 3600 for t in timestamps]
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=time_hours,
        y=y_values,
        mode='lines',
        line=dict(shape='hv', width=2, color='#1f77b4'),
        fill='tozeroy',
        fillcolor='rgba(31, 119, 180, 0.3)'
    ))
    fig.update_layout(
        title='睡眠阶段时序图 (Hypnogram)',
        xaxis_title='睡眠时间 (小时)',
        yaxis_title='睡眠阶段',
        yaxis=dict(
            tickvals=[0, 1, 2, 3],
            ticktext=['深睡', '浅睡', 'REM', '清醒']
        ),
        height=400,
        template='plotly_white'
    )
    return fig


def create_sleep_stage_pie(stage_distribution):
    labels = list(stage_distribution.keys())
    values = [d['percentage'] for d in stage_distribution.values()]
    colors = ['#ff7f0e', '#2ca02c', '#1f77b4', '#d62728']
    fig = go.Figure(data=[go.Pie(
        labels=labels,
        values=values,
        hole=0.4,
        marker=dict(colors=colors),
        textinfo='label+percent',
        hovertemplate='%{label}<br>时间: %{customdata:.1f} 分钟<br>占比: %{percent}',
        customdata=[d['minutes'] for d in stage_distribution.values()]
    )])
    fig.update_layout(
        title='睡眠阶段分布',
        height=400,
        template='plotly_white'
    )
    return fig


def create_sleep_score_gauge(total_score, grade):
    fig = go.Figure(go.Indicator(
        mode="gauge+number+delta",
        value=total_score,
        domain={'x': [0, 1], 'y': [0, 1]},
        title={'text': f"睡眠质量评分 - {grade}", 'font': {'size': 24}},
        delta={'reference': 85},
        gauge={
            'axis': {'range': [0, 100]},
            'bar': {'color': '#1f77b4'},
            'steps': [
                {'range': [0, 50], 'color': '#ff4b5c'},
                {'range': [50, 60], 'color': '#ffa502'},
                {'range': [60, 70], 'color': '#ffd93d'},
                {'range': [70, 85], 'color': '#7bed9f'},
                {'range': [85, 100], 'color': '#2ed573'}
            ],
            'threshold': {
                'line': {'color': "red", 'width': 4},
                'thickness': 0.75,
                'value': 85
            }
        }
    ))
    fig.update_layout(height=300, template='plotly_white')
    return fig


def create_score_components_bar(score_components):
    labels = {
        'sleep_efficiency': '睡眠效率',
        'sleep_duration': '睡眠时长',
        'n3_sleep': '深睡(N3)',
        'rem_sleep': 'REM睡眠',
        'sleep_fragmentation': '睡眠连续性',
        'sleep_latency': '入睡潜伏期'
    }
    colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b']
    data = []
    for key, comp in score_components.items():
        data.append({
            'component': labels.get(key, key),
            'score': comp['score'],
            'weight': comp['weight']
        })
    df = pd.DataFrame(data)
    fig = go.Figure(data=[
        go.Bar(
            x=df['component'],
            y=df['score'],
            text=df['score'].round(1).astype(str),
            textposition='auto',
            marker_color=colors[:len(df)]
        )
    ])
    fig.update_layout(
        title='睡眠评分构成 (AASM校准)',
        yaxis_title='得分',
        yaxis_range=[0, 100],
        height=400,
        template='plotly_white'
    )
    return fig


def create_factor_impact_radar(factor_impacts):
    categories = list(factor_impacts.keys())
    values = [data['score'] for data in factor_impacts.values()]
    category_names = {
        'exercise': '运动',
        'exercise_history': '运动历史',
        'caffeine': '咖啡因',
        'alcohol': '饮酒',
        'stress': '压力',
        'bedtime_consistency': '作息规律'
    }
    categories_cn = [category_names.get(c, c) for c in categories]
    fig = go.Figure(data=go.Scatterpolar(
        r=values + [values[0]],
        theta=categories_cn + [categories_cn[0]],
        fill='toself',
        line_color='#1f77b4',
        fillcolor='rgba(31, 119, 180, 0.3)'
    ))
    fig.update_layout(
        polar=dict(
            radialaxis=dict(range=[0, 100]),
            angularaxis=dict(tickfont=dict(size=12))
        ),
        title='生活方式因素影响评估',
        height=400,
        template='plotly_white'
    )
    return fig


def create_attribution_bar(attribution):
    category_names = {
        'exercise': '运动',
        'exercise_history': '运动历史',
        'caffeine': '咖啡因',
        'alcohol': '饮酒',
        'stress': '压力',
        'bedtime_consistency': '作息规律'
    }
    data = []
    for factor, attr in attribution.items():
        data.append({
            'factor': category_names.get(factor, factor),
            'contribution': attr['contribution_percent'],
            'impact': attr['impact_magnitude']
        })
    df = pd.DataFrame(data).sort_values('contribution', ascending=True)
    fig = go.Figure(data=[
        go.Bar(
            y=df['factor'],
            x=df['contribution'],
            orientation='h',
            text=df['contribution'].round(1).astype(str) + '%',
            textposition='auto',
            marker_color=df['impact'].apply(lambda x: '#ff4b5c' if x > 30 else '#ffa502' if x > 15 else '#2ed573')
        )
    ])
    fig.update_layout(
        title='睡眠影响因素归因分析',
        xaxis_title='影响贡献比例 (%)',
        height=400,
        template='plotly_white'
    )
    return fig


def create_signal_comparison(hr_data, resp_data, act_data, sample_rate=1, max_points=1000):
    step = max(1, len(hr_data) // max_points)
    time_points = np.arange(0, len(hr_data), step) / (60 * sample_rate)
    fig = make_subplots(rows=3, cols=1, shared_xaxis=True,
                        subplot_titles=('心率 (BPM)', '呼吸率 (次/分)', '活动量'))
    fig.add_trace(go.Scatter(
        x=time_points,
        y=hr_data[::step],
        line=dict(color='#ff7f0e', width=1),
        name='心率'
    ), row=1, col=1)
    fig.add_trace(go.Scatter(
        x=time_points,
        y=resp_data[::step],
        line=dict(color='#2ca02c', width=1),
        name='呼吸率'
    ), row=2, col=1)
    fig.add_trace(go.Scatter(
        x=time_points,
        y=act_data[::step],
        line=dict(color='#1f77b4', width=1),
        name='活动量',
        fill='tozeroy'
    ), row=3, col=1)
    fig.update_layout(
        title='生理信号趋势',
        height=600,
        showlegend=False,
        template='plotly_white'
    )
    fig.update_xaxes(title_text='时间 (分钟)', row=3, col=1)
    return fig


def create_feature_importance_plot(feature_importance, top_n=15):
    df = feature_importance.head(top_n).sort_values('importance', ascending=True)
    fig = go.Figure(data=[
        go.Bar(
            y=df['feature'],
            x=df['importance'],
            orientation='h',
            marker_color='#1f77b4'
        )
    ])
    fig.update_layout(
        title=f'Top {top_n} 特征重要性 (XGBoost)',
        xaxis_title='重要性',
        height=500,
        template='plotly_white'
    )
    return fig


def create_shap_summary_plot(shap_importance, top_n=15):
    df = shap_importance.head(top_n).sort_values('shap_importance', ascending=True)
    fig = go.Figure(data=[
        go.Bar(
            y=df['feature'],
            x=df['shap_importance'],
            orientation='h',
            marker_color='#ff7f0e'
        )
    ])
    fig.update_layout(
        title=f'Top {top_n} SHAP特征重要性',
        xaxis_title='平均 |SHAP Value|',
        height=500,
        template='plotly_white'
    )
    return fig


def create_circadian_schedule_plot(schedule_data, chronotype_label):
    times = []
    activities = []
    phases = []
    for item in schedule_data:
        times.append(item['time'])
        activities.append(item['activity'])
        phases.append(item.get('phase', ''))

    fig = go.Figure(data=[
        go.Scatter(
            x=list(range(len(times))),
            y=[1] * len(times),
            mode='markers+text',
            marker=dict(size=15, color='#3B82F6'),
            text=activities,
            textposition='top center',
            textfont=dict(size=10)
        )
    ])

    annotations = []
    for i, (t, act, ph) in enumerate(zip(times, activities, phases)):
        annotations.append(dict(
            x=i, y=0.5,
            text=f"{t}<br>{ph}" if ph else t,
            showarrow=False,
            font=dict(size=9, color='#666')
        ))

    fig.update_layout(
        title=f'{chronotype_label} 最佳作息时间表',
        height=400,
        template='plotly_white',
        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        yaxis=dict(showgrid=False, zeroline=False, showticklabels=False, range=[0, 2]),
        annotations=annotations,
        showlegend=False
    )
    return fig


def create_circadian_alignment_gauge(alignment_score, chronotype_label):
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=alignment_score,
        domain={'x': [0, 1], 'y': [0, 1]},
        title={'text': f'生物钟对齐度 - {chronotype_label}', 'font': {'size': 20}},
        gauge={
            'axis': {'range': [0, 100]},
            'bar': {'color': '#3B82F6'},
            'steps': [
                {'range': [0, 40], 'color': '#ff4b5c'},
                {'range': [40, 70], 'color': '#ffa502'},
                {'range': [70, 100], 'color': '#2ed573'}
            ],
            'threshold': {
                'line': {'color': 'red', 'width': 3},
                'thickness': 0.75,
                'value': 80
            }
        }
    ))
    fig.update_layout(height=300, template='plotly_white')
    return fig


def create_age_percentile_chart(chart_data, age_group_label):
    percentiles = chart_data['percentile_values']
    labels = chart_data['percentile_labels']
    your_score = chart_data['your_score']
    mean_score = chart_data['mean_score']

    fig = go.Figure()

    fig.add_trace(go.Bar(
        x=labels,
        y=percentiles,
        name='同龄人百分位',
        marker_color='#93C5FD',
        opacity=0.7
    ))

    fig.add_hline(y=your_score, line_dash="dash", line_color="#EF4444", line_width=2,
                  annotation_text=f"您的评分: {your_score:.1f}",
                  annotation_position="top left")

    fig.add_hline(y=mean_score, line_dash="dot", line_color="#10B981", line_width=1,
                  annotation_text=f"同龄均值: {mean_score:.0f}",
                  annotation_position="bottom left")

    fig.update_layout(
        title=f'同龄人百分位分布 ({age_group_label})',
        xaxis_title='百分位',
        yaxis_title='睡眠评分',
        height=400,
        template='plotly_white'
    )
    return fig


def create_age_group_comparison_radar(stage_analysis, group_norm):
    categories = ['睡眠时长', '睡眠效率', '深睡比例', 'REM比例']
    your_values = [
        min(100, stage_analysis['total_sleep_duration'] / 9 * 100),
        stage_analysis['sleep_efficiency'],
        min(100, stage_analysis['stage_distribution']['深睡']['percentage'] / 23 * 100),
        min(100, stage_analysis['stage_distribution']['REM']['percentage'] / 25 * 100)
    ]
    group_values = [
        min(100, group_norm['mean_duration'] / 9 * 100),
        group_norm['mean_efficiency'],
        min(100, group_norm['mean_n3_pct'] / 23 * 100),
        min(100, group_norm['mean_rem_pct'] / 25 * 100)
    ]

    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(
        r=your_values + [your_values[0]],
        theta=categories + [categories[0]],
        fill='toself',
        name='您的数据',
        line_color='#3B82F6',
        fillcolor='rgba(59, 130, 246, 0.3)'
    ))
    fig.add_trace(go.Scatterpolar(
        r=group_values + [group_values[0]],
        theta=categories + [categories[0]],
        fill='toself',
        name='同龄均值',
        line_color='#F59E0B',
        fillcolor='rgba(245, 158, 11, 0.2)'
    ))
    fig.update_layout(
        polar=dict(radialaxis=dict(range=[0, 100])),
        title='您 vs 同龄人平均水平',
        height=400,
        template='plotly_white'
    )
    return fig


def create_prescription_timeline(prescription_data):
    if not prescription_data or 'schedule_adjustment' not in prescription_data:
        fig = go.Figure()
        fig.update_layout(
            title='作息调整方案',
            height=300,
            template='plotly_white'
        )
        return fig

    schedule = prescription_data['schedule_adjustment']
    bedtime = schedule.get('recommended_bedtime', 23.0)
    wakeup = schedule.get('recommended_wakeup', 7.0)
    target_hours = schedule.get('target_sleep_duration', 8.0)

    fig = go.Figure()

    sleep_start = bedtime
    sleep_end = bedtime + target_hours

    fig.add_trace(go.Bar(
        x=[target_hours],
        y=['睡眠'],
        orientation='h',
        base=sleep_start,
        marker_color='#3B82F6',
        name='推荐睡眠时段',
        text=f'{int(bedtime)}:{int((bedtime%1)*60):02d} - {int(wakeup)}:{int((wakeup%1)*60):02d}',
        textposition='inside'
    ))

    fig.update_layout(
        title='推荐作息时间线',
        xaxis_title='时间 (小时)',
        xaxis=dict(
            tickvals=list(range(0, 30, 2)),
            ticktext=[f'{h%24}:00' for h in range(0, 30, 2)]
        ),
        height=250,
        template='plotly_white',
        barmode='overlay'
    )
    return fig


def create_weekly_plan_timeline(weekly_plan):
    if not weekly_plan or 'weekly_goals' not in weekly_plan:
        fig = go.Figure()
        fig.update_layout(title='周计划', height=300, template='plotly_white')
        return fig

    goals = weekly_plan['weekly_goals']
    days = [g['day'] for g in goals]
    focuses = [g['focus'] for g in goals]
    descriptions = [g['goal'] for g in goals]

    colors = ['#3B82F6', '#10B981', '#F59E0B', '#EF4444', '#8B5CF6']

    fig = go.Figure(data=[
        go.Bar(
            x=days,
            y=[1] * len(days),
            text=[f'{d}<br>{f}' for d, f in zip(descriptions, focuses)],
            textposition='inside',
            textfont=dict(size=11),
            marker_color=colors[:len(days)]
        )
    ])

    fig.update_layout(
        title=f'睡眠改善周计划 ({weekly_plan.get("phase", "")})',
        yaxis=dict(showticklabels=False, showgrid=False),
        height=300,
        template='plotly_white'
    )
    return fig
