import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots

plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'Arial Unicode MS']
plt.rcParams['axes.unicode_minus'] = False

def plot_coefficients(coef_df, top_n=15):
    df_plot = coef_df.head(top_n).copy()
    df_plot = df_plot.sort_values('coef', ascending=True)
    
    colors = ['#e74c3c' if c > 0 else '#27ae60' for c in df_plot['coef']]
    
    fig = go.Figure()
    
    fig.add_trace(go.Bar(
        y=df_plot['feature'],
        x=df_plot['coef'],
        orientation='h',
        marker=dict(color=colors),
        text=[f"{c:.3f}" for c in df_plot['coef']],
        textposition='outside',
        hovertemplate=(
            '<b>%{y}</b><br>' +
            '系数: %{x:.3f}<br>' +
            '风险比: %{customdata[0]:.3f}<br>' +
            'P值: %{customdata[1]:.4f}<br>' +
            '显著性: %{customdata[2]}<extra></extra>'
        ),
        customdata=df_plot[['hazard_ratio', 'p_value', 'significance']].values
    ))
    
    fig.update_layout(
        title={
            'text': '特征影响系数 (Cox回归)',
            'x': 0.5,
            'xanchor': 'center'
        },
        xaxis_title='回归系数',
        yaxis_title='特征',
        height=max(400, 30 * len(df_plot)),
        margin=dict(l=200, r=100, t=80, b=40),
        shapes=[
            dict(
                type='line',
                x0=0, y0=0, x1=0, y1=1,
                yref='paper',
                line=dict(color='black', width=1, dash='dash')
            )
        ]
    )
    
    return fig

def plot_hazard_ratios(coef_df, top_n=15):
    df_plot = coef_df.head(top_n).copy()
    df_plot = df_plot.sort_values('hazard_ratio', ascending=True)
    
    fig = go.Figure()
    
    fig.add_trace(go.Scatter(
        y=df_plot['feature'],
        x=df_plot['hazard_ratio'],
        mode='markers',
        marker=dict(
            size=12,
            color=['#e74c3c' if hr > 1 else '#27ae60' for hr in df_plot['hazard_ratio']]
        ),
        error_x=dict(
            type='data',
            symmetric=False,
            array=df_plot['ci_upper'] - df_plot['hazard_ratio'],
            arrayminus=df_plot['hazard_ratio'] - df_plot['ci_lower'],
            color='gray'
        ),
        hovertemplate=(
            '<b>%{y}</b><br>' +
            '风险比: %{x:.3f}<br>' +
            '95%% CI: [%{customdata[0]:.3f}, %{customdata[1]:.3f}]<br>' +
            'P值: %{customdata[2]:.4f}<extra></extra>'
        ),
        customdata=df_plot[['ci_lower', 'ci_upper', 'p_value']].values
    ))
    
    fig.update_layout(
        title={
            'text': '特征风险比 (Hazard Ratio) - 95%置信区间',
            'x': 0.5,
            'xanchor': 'center'
        },
        xaxis_title='风险比 (HR > 1: 风险因素, HR < 1: 保护因素)',
        yaxis_title='特征',
        height=max(400, 30 * len(df_plot)),
        margin=dict(l=200, r=40, t=80, b=40),
        shapes=[
            dict(
                type='line',
                x0=1, y0=0, x1=1, y1=1,
                yref='paper',
                line=dict(color='black', width=1, dash='dash')
            )
        ]
    )
    
    return fig

def plot_kaplan_meier(kmf_results, group_col=None):
    fig = go.Figure()
    
    if isinstance(kmf_results, dict):
        colors = px.colors.qualitative.Plotly
        for i, (group, kmf) in enumerate(kmf_results.items()):
            color = colors[i % len(colors)]
            fig.add_trace(go.Scatter(
                x=kmf.survival_function_.index,
                y=kmf.survival_function_.values.flatten(),
                mode='lines',
                name=f'{group_col}: {group}',
                line=dict(color=color, width=2),
                hovertemplate=(
                    f'<b>{group_col}: {group}</b><br>' +
                    '时间: %{x}<br>' +
                    '留存概率: %{y:.3f}<extra></extra>'
                )
            ))
            
            ci = kmf.confidence_interval_
            fig.add_trace(go.Scatter(
                x=list(ci.index) + list(reversed(ci.index)),
                y=list(ci.iloc[:, 0]) + list(reversed(ci.iloc[:, 1])),
                fill='toself',
                fillcolor=f'rgba{tuple(int(color.lstrip("#")[i:i+2], 16) for i in (0, 2, 4)) + (0.2,)}',
                line=dict(color='rgba(255,255,255,0)'),
                hoverinfo='skip',
                showlegend=False
            ))
    else:
        kmf = kmf_results
        fig.add_trace(go.Scatter(
            x=kmf.survival_function_.index,
            y=kmf.survival_function_.values.flatten(),
            mode='lines',
            name='总体留存',
            line=dict(color='#3498db', width=2),
            hovertemplate=(
                '时间: %{x}<br>' +
                '留存概率: %{y:.3f}<extra></extra>'
            )
        ))
        
        ci = kmf.confidence_interval_
        fig.add_trace(go.Scatter(
            x=list(ci.index) + list(reversed(ci.index)),
            y=list(ci.iloc[:, 0]) + list(reversed(ci.iloc[:, 1])),
            fill='toself',
            fillcolor='rgba(52, 152, 219, 0.2)',
            line=dict(color='rgba(255,255,255,0)'),
            hoverinfo='skip',
            showlegend=False
        ))
    
    fig.update_layout(
        title={
            'text': 'Kaplan-Meier 留存曲线',
            'x': 0.5,
            'xanchor': 'center'
        },
        xaxis_title='时间',
        yaxis_title='留存概率',
        yaxis=dict(range=[0, 1]),
        height=500,
        margin=dict(l=60, r=40, t=80, b=40),
        legend=dict(
            orientation='h',
            yanchor='bottom',
            y=1.02,
            xanchor='right',
            x=1
        )
    )
    
    return fig

def plot_bootstrap_survival(bootstrap_df, bootstrap_matrix=None, n_curves_to_show=20):
    fig = go.Figure()
    
    if bootstrap_matrix is not None and n_curves_to_show > 0:
        n_samples = min(n_curves_to_show, bootstrap_matrix.shape[0])
        for i in range(n_samples):
            fig.add_trace(go.Scatter(
                x=bootstrap_df['time'],
                y=bootstrap_matrix[i],
                mode='lines',
                line=dict(color='rgba(150, 150, 150, 0.3)', width=1),
                showlegend=False,
                hoverinfo='skip'
            ))
    
    fig.add_trace(go.Scatter(
        x=bootstrap_df['time'],
        y=bootstrap_df['mean_survival'],
        mode='lines',
        name='均值留存',
        line=dict(color='#3498db', width=3),
        hovertemplate=(
            '时间: %{x:.1f}<br>' +
            '平均留存概率: %{y:.3f}<extra></extra>'
        )
    ))
    
    fig.add_trace(go.Scatter(
        x=list(bootstrap_df['time']) + list(reversed(bootstrap_df['time'])),
        y=list(bootstrap_df['ci_lower']) + list(reversed(bootstrap_df['ci_upper'])),
        fill='toself',
        fillcolor='rgba(52, 152, 219, 0.3)',
        line=dict(color='rgba(255,255,255,0)'),
        name='95% Bootstrap置信区间',
        hovertemplate=(
            '时间: %{x:.1f}<br>' +
            '置信区间: [%{customdata[0]:.3f}, %{customdata[1]:.3f}]<extra></extra>'
        ),
        customdata=bootstrap_df[['ci_lower', 'ci_upper']].values
    ))
    
    fig.add_trace(go.Scatter(
        x=bootstrap_df['time'],
        y=bootstrap_df['median_survival'],
        mode='lines',
        name='中位数留存',
        line=dict(color='#e74c3c', width=2, dash='dash'),
        hovertemplate=(
            '时间: %{x:.1f}<br>' +
            '中位数留存概率: %{y:.3f}<extra></extra>'
        )
    ))
    
    fig.update_layout(
        title={
            'text': 'Bootstrap留存曲线 (含95%置信区间)',
            'x': 0.5,
            'xanchor': 'center'
        },
        xaxis_title='时间',
        yaxis_title='留存概率',
        yaxis=dict(range=[0, 1]),
        height=550,
        margin=dict(l=60, r=40, t=80, b=40),
        legend=dict(
            orientation='h',
            yanchor='bottom',
            y=1.02,
            xanchor='right',
            x=1
        )
    )
    
    return fig

def plot_schoenfeld_residuals(ph_test_df, violated_features=None):
    df_plot = ph_test_df.copy()
    df_plot = df_plot.sort_values('p', ascending=True)
    
    colors = []
    for idx, row in df_plot.iterrows():
        if violated_features and row['feature'] in violated_features:
            colors.append('#e74c3c')
        else:
            colors.append('#27ae60')
    
    fig = go.Figure()
    
    fig.add_trace(go.Bar(
        y=df_plot['feature'],
        x=-np.log10(df_plot['p']),
        orientation='h',
        marker=dict(color=colors),
        text=[f"p={p:.4f}{' ❌' if v else ' ✅'}" for p, v in zip(df_plot['p'], ~df_plot['satisfies_ph'])],
        textposition='outside',
        hovertemplate=(
            '<b>%{y}</b><br>' +
            '-log10(p值): %{x:.3f}<br>' +
            'P值: %{customdata[0]:.4f}<br>' +
            '检验统计量: %{customdata[1]:.3f}<br>' +
            '满足PH假设: %{customdata[2]}<extra></extra>'
        ),
        customdata=df_plot[['p', 'test_statistic', 'satisfies_ph']].values
    ))
    
    fig.add_shape(
        type='line',
        x0=-np.log10(0.05), y0=0, x1=-np.log10(0.05), y1=1,
        yref='paper',
        line=dict(color='#e74c3c', width=2, dash='dash')
    )
    
    fig.add_annotation(
        x=-np.log10(0.05) + 0.1,
        y=0.95,
        yref='paper',
        text='p=0.05 阈值',
        showarrow=False,
        font=dict(color='#e74c3c')
    )
    
    fig.update_layout(
        title={
            'text': 'Schoenfeld残差检验 - 比例风险假设验证',
            'x': 0.5,
            'xanchor': 'center'
        },
        xaxis_title='-log10(P值)，越高越显著违反PH假设',
        yaxis_title='特征',
        height=max(400, 30 * len(df_plot)),
        margin=dict(l=200, r=150, t=80, b=40)
    )
    
    return fig

def plot_risk_distribution(risk_scores, bins=30):
    fig = go.Figure()
    
    fig.add_trace(go.Histogram(
        x=risk_scores,
        nbinsx=bins,
        marker=dict(color='#3498db', line=dict(color='white', width=1)),
        hovertemplate=(
            '风险评分区间: %{x}<br>' +
            '用户数: %{y}<extra></extra>'
        )
    ))
    
    fig.update_layout(
        title={
            'text': '用户风险评分分布',
            'x': 0.5,
            'xanchor': 'center'
        },
        xaxis_title='风险评分 (相对风险)',
        yaxis_title='用户数',
        height=400,
        margin=dict(l=60, r=40, t=80, b=40)
    )
    
    return fig

def plot_survival_curves(surv_funcs, user_indices=None, max_curves=10):
    fig = go.Figure()
    
    if user_indices is None:
        indices = surv_funcs.columns[:max_curves]
    else:
        indices = [col for col in user_indices if col in surv_funcs.columns][:max_curves]
    
    colors = px.colors.qualitative.Plotly
    
    for i, col in enumerate(indices):
        color = colors[i % len(colors)]
        fig.add_trace(go.Scatter(
            x=surv_funcs.index,
            y=surv_funcs[col],
            mode='lines',
            name=f'用户 {col}',
            line=dict(color=color, width=2),
            hovertemplate=(
                f'<b>用户 {col}</b><br>' +
                '时间: %{x}<br>' +
                '留存概率: %{y:.3f}<extra></extra>'
            )
        ))
    
    fig.update_layout(
        title={
            'text': '个体用户生存曲线',
            'x': 0.5,
            'xanchor': 'center'
        },
        xaxis_title='时间',
        yaxis_title='留存概率',
        yaxis=dict(range=[0, 1]),
        height=500,
        margin=dict(l=60, r=40, t=80, b=40),
        legend=dict(
            orientation='h',
            yanchor='bottom',
            y=1.02,
            xanchor='right',
            x=1
        )
    )
    
    return fig

def plot_risk_groups(groups_df):
    group_stats = groups_df.groupby('risk_group').agg({
        'user_id': 'count',
        'risk_score': ['mean', 'median', 'min', 'max'],
        'churn_prob_30d': 'mean',
        'churn_prob_90d': 'mean'
    }).round(3)
    group_stats.columns = ['_'.join(col).strip() for col in group_stats.columns.values]
    group_stats = group_stats.reset_index()
    
    group_order = ['高风险', '中风险', '低风险']
    group_stats['risk_group'] = pd.Categorical(group_stats['risk_group'], categories=group_order, ordered=True)
    group_stats = group_stats.sort_values('risk_group')
    
    fig = make_subplots(
        rows=1, cols=2,
        subplot_titles=('各风险组用户数量', '各风险组30天流失概率'),
        specs=[[{"type": "pie"}, {"type": "bar"}]]
    )
    
    colors = {'高风险': '#e74c3c', '中风险': '#f39c12', '低风险': '#27ae60'}
    
    fig.add_trace(
        go.Pie(
            labels=group_stats['risk_group'],
            values=group_stats['user_id_count'],
            marker=dict(colors=[colors[g] for g in group_stats['risk_group']]),
            textinfo='label+percent',
            hole=0.4
        ),
        row=1, col=1
    )
    
    fig.add_trace(
        go.Bar(
            x=group_stats['risk_group'],
            y=group_stats['churn_prob_30d_mean'],
            marker=dict(color=[colors[g] for g in group_stats['risk_group']]),
            text=[f'{v:.1%}' for v in group_stats['churn_prob_30d_mean']],
            textposition='outside'
        ),
        row=1, col=2
    )
    
    fig.update_layout(
        title={
            'text': '用户风险分群统计',
            'x': 0.5,
            'xanchor': 'center'
        },
        height=500,
        margin=dict(l=60, r=40, t=100, b=40),
        showlegend=False
    )
    
    fig.update_yaxes(title_text='30天平均流失概率', row=1, col=2)
    
    return fig

def plot_feature_importance(importance_df, top_n=10):
    df_plot = importance_df.head(top_n).copy()
    df_plot = df_plot.sort_values('importance', ascending=True)
    
    colors = ['#e74c3c' if d == 'Risk Factor' else '#27ae60' for d in df_plot['direction']]
    
    fig = go.Figure()
    
    fig.add_trace(go.Bar(
        y=df_plot['feature'],
        x=df_plot['importance'],
        orientation='h',
        marker=dict(color=colors),
        text=[f"{v:.3f}" for v in df_plot['importance']],
        textposition='outside',
        hovertemplate=(
            '<b>%{y}</b><br>' +
            '重要性: %{x:.3f}<br>' +
            '类型: %{customdata}<extra></extra>'
        ),
        customdata=df_plot['direction'].replace({'Risk Factor': '风险因素', 'Protective Factor': '保护因素'}).values
    ))
    
    fig.update_layout(
        title={
            'text': '特征重要性排序',
            'x': 0.5,
            'xanchor': 'center'
        },
        xaxis_title='重要性 (|系数|)',
        yaxis_title='特征',
        height=max(400, 30 * len(df_plot)),
        margin=dict(l=200, r=100, t=80, b=40)
    )
    
    return fig

def plot_heatmap(df, feature_cols, max_features=15):
    cols = feature_cols[:max_features]
    corr_matrix = df[cols].corr()
    
    fig = go.Figure(data=go.Heatmap(
        z=corr_matrix.values,
        x=corr_matrix.columns,
        y=corr_matrix.columns,
        colorscale='RdBu',
        zmid=0,
        text=corr_matrix.values.round(2),
        texttemplate='%{text}',
        textfont={"size": 10},
        hovertemplate=(
            '<b>%{x}</b> vs <b>%{y}</b><br>' +
            '相关系数: %{z:.3f}<extra></extra>'
        )
    ))
    
    fig.update_layout(
        title={
            'text': '特征相关性热力图',
            'x': 0.5,
            'xanchor': 'center'
        },
        height=max(500, 30 * len(cols)),
        margin=dict(l=200, r=40, t=80, b=200),
        xaxis=dict(tickangle=-45)
    )
    
    return fig

def plot_intervention_simulation(intervention_result):
    fig = go.Figure()
    
    fig.add_trace(go.Scatter(
        x=intervention_result['times'],
        y=intervention_result['original_survival'],
        mode='lines',
        name='干预前留存率',
        line=dict(color='#e74c3c', width=3),
        hovertemplate=(
            '时间: %{x:.1f}天<br>' +
            '留存率: %{y:.3f}<extra></extra>'
        )
    ))
    
    fig.add_trace(go.Scatter(
        x=intervention_result['times'],
        y=intervention_result['modified_survival'],
        mode='lines',
        name='干预后留存率',
        line=dict(color='#27ae60', width=3),
        hovertemplate=(
            '时间: %{x:.1f}天<br>' +
            '留存率: %{y:.3f}<extra></extra>'
        )
    ))
    
    fig.add_shape(
        type='line',
        x0=30, y0=0, x1=30, y1=1,
        yref='paper',
        line=dict(color='#3498db', width=2, dash='dash'),
        name='30天'
    )
    
    fig.add_annotation(
        x=30,
        y=1.02,
        yref='paper',
        text='30天',
        showarrow=False,
        font=dict(color='#3498db')
    )
    
    fig.update_layout(
        title={
            'text': f"干预效果模拟 - {intervention_result['feature']}",
            'x': 0.5,
            'xanchor': 'center'
        },
        xaxis_title='时间 (天)',
        yaxis_title='留存概率',
        yaxis=dict(range=[0, 1]),
        height=500,
        margin=dict(l=60, r=40, t=80, b=40),
        legend=dict(
            orientation='h',
            yanchor='bottom',
            y=1.02,
            xanchor='right',
            x=1
        )
    )
    
    return fig

def plot_intervention_comparison(intervention_options, top_n=5):
    df_plot = intervention_options.head(top_n).copy()
    df_plot = df_plot.sort_values('churn_reduction_30d', ascending=True)
    
    colors = ['#3498db' if t == '提升保护因素' else '#9b59b6' for t in df_plot['intervention_type']]
    
    fig = go.Figure()
    
    fig.add_trace(go.Bar(
        y=df_plot['feature'],
        x=df_plot['churn_reduction_30d'] * 100,
        orientation='h',
        marker=dict(color=colors),
        text=[f"{v:.1f}%" for v in df_plot['churn_reduction_30d'] * 100],
        textposition='outside',
        hovertemplate=(
            '<b>%{y}</b><br>' +
            '干预类型: %{customdata[0]}<br>' +
            '流失率降低: %{x:.1f}%<br>' +
            '风险降低: %{customdata[1]:.1f}%<br>' +
            '当前值: %{customdata[2]:.2f} → 目标值: %{customdata[3]:.2f}<extra></extra>'
        ),
        customdata=df_plot[['intervention_type', 'risk_reduction', 'current_value', 'target_value']].values
    ))
    
    fig.update_layout(
        title={
            'text': '最佳干预措施推荐 (按30天流失率降低排序)',
            'x': 0.5,
            'xanchor': 'center'
        },
        xaxis_title='预期30天流失率降低 (%)',
        yaxis_title='干预特征',
        height=max(400, 30 * len(df_plot)),
        margin=dict(l=200, r=100, t=80, b=40)
    )
    
    return fig

def plot_warning_trend(trend_df):
    fig = go.Figure()
    
    fig.add_trace(go.Scatter(
        x=trend_df['date'],
        y=trend_df['high_risk'],
        mode='lines+markers',
        name='高危',
        line=dict(color='#e74c3c', width=2),
        marker=dict(size=6)
    ))
    
    fig.add_trace(go.Scatter(
        x=trend_df['date'],
        y=trend_df['medium_risk'],
        mode='lines+markers',
        name='中危',
        line=dict(color='#f39c12', width=2),
        marker=dict(size=6)
    ))
    
    fig.add_trace(go.Scatter(
        x=trend_df['date'],
        y=trend_df['low_risk'],
        mode='lines+markers',
        name='低危',
        line=dict(color='#27ae60', width=2),
        marker=dict(size=6)
    ))
    
    fig.add_trace(go.Scatter(
        x=trend_df['date'],
        y=trend_df['total'],
        mode='lines',
        name='总计',
        line=dict(color='#3498db', width=3, dash='dash'),
        marker=dict(size=8)
    ))
    
    fig.update_layout(
        title={
            'text': '流失预警趋势 (近30天)',
            'x': 0.5,
            'xanchor': 'center'
        },
        xaxis_title='日期',
        yaxis_title='预警用户数',
        height=450,
        margin=dict(l=60, r=40, t=80, b=40),
        legend=dict(
            orientation='h',
            yanchor='bottom',
            y=1.02,
            xanchor='right',
            x=1
        )
    )
    
    return fig

def plot_strategy_roi(strategies):
    df_plot = pd.DataFrame(strategies)
    df_plot = df_plot.sort_values('adjusted_roi', ascending=True)
    
    colors = []
    for s in df_plot['urgency']:
        if s == 'high':
            colors.append('#e74c3c')
        elif s == 'medium':
            colors.append('#f39c12')
        else:
            colors.append('#27ae60')
    
    fig = go.Figure()
    
    fig.add_trace(go.Scatter(
        x=df_plot['adjusted_roi'],
        y=df_plot['name'],
        mode='markers',
        marker=dict(
            size=df_plot['expected_churn_reduction'] * 1000,
            color=colors,
            sizemode='area',
            sizeref=0.1,
            line=dict(color='white', width=2)
        ),
        text=[f"ROI: {roi:.1f}x | 成本: ¥{cost}" for roi, cost in zip(df_plot['adjusted_roi'], df_plot['cost_per_user'])],
        textposition='top center',
        hovertemplate=(
            '<b>%{y}</b><br>' +
            '类型: %{customdata[0]}<br>' +
            '预期ROI: %{x:.1f}x<br>' +
            '预期流失降低: %{customdata[1]:.1%}<br>' +
            '单用户成本: ¥%{customdata[2]}<br>' +
            '有效期: %{customdata[3]}天<extra></extra>'
        ),
        customdata=df_plot[['type', 'expected_churn_reduction', 'cost_per_user', 'duration_days']].values
    ))
    
    fig.update_layout(
        title={
            'text': '留存策略ROI分析 (气泡大小=流失降低效果)',
            'x': 0.5,
            'xanchor': 'center'
        },
        xaxis_title='预期ROI (倍数)',
        yaxis_title='策略名称',
        height=max(400, 35 * len(df_plot)),
        margin=dict(l=200, r=40, t=80, b=40)
    )
    
    return fig

def plot_campaign_allocation(campaign_plan):
    plan_df = pd.DataFrame(campaign_plan['strategies'])
    
    fig = make_subplots(
        rows=1, cols=2,
        specs=[[{"type": "pie"}, {"type": "bar"}]],
        subplot_titles=('预算分配', '预期挽救用户数')
    )
    
    colors = px.colors.qualitative.Plotly
    
    fig.add_trace(
        go.Pie(
            labels=plan_df['strategy'],
            values=plan_df['total_cost'],
            marker=dict(colors=colors[:len(plan_df)]),
            textinfo='label+percent',
            hole=0.4
        ),
        row=1, col=1
    )
    
    fig.add_trace(
        go.Bar(
            x=plan_df['strategy'],
            y=plan_df['expected_users_saved'],
            marker=dict(color=colors[:len(plan_df)]),
            text=[f"{v:.0f}人" for v in plan_df['expected_users_saved']],
            textposition='outside'
        ),
        row=1, col=2
    )
    
    fig.update_layout(
        title={
            'text': f"{campaign_plan['risk_group']}组活动方案 (总预算: ¥{campaign_plan['used_budget']:,.0f})",
            'x': 0.5,
            'xanchor': 'center'
        },
        height=500,
        margin=dict(l=60, r=40, t=100, b=40),
        showlegend=False
    )
    
    fig.update_yaxes(title_text='预期挽救用户数', row=1, col=2)
    
    return fig
