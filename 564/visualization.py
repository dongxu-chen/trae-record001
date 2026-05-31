import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib
import seaborn as sns
from typing import Optional, List, Dict, Tuple
from plotly import graph_objects as go
from plotly.subplots import make_subplots
import warnings
warnings.filterwarnings('ignore')

matplotlib.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei']
matplotlib.rcParams['axes.unicode_minus'] = False

COLORS = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4', '#FFEAA7', '#DDA0DD']


def plot_source_profile(
    source_profile: pd.DataFrame,
    uncertainty_result=None,
    use_plotly: bool = True
):
    source_names = source_profile.index.tolist()
    species = source_profile.columns.tolist()
    n_sources = len(source_names)
    
    if use_plotly:
        fig = go.Figure()
        
        for i, source in enumerate(source_names):
            y = source_profile.loc[source].values
            error_y = None
            
            if uncertainty_result is not None:
                std = uncertainty_result.F_std[i]
                error_y = dict(
                    type='data',
                    array=std,
                    visible=True,
                    thickness=1,
                    width=4
                )
            
            fig.add_trace(go.Bar(
                x=species,
                y=y,
                name=source,
                marker_color=COLORS[i % len(COLORS)],
                error_y=error_y,
                opacity=0.85
            ))
        
        fig.update_layout(
            title=dict(
                text='污染源谱图',
                font=dict(size=20),
                x=0.5
            ),
            xaxis_title='污染物种类',
            yaxis_title='相对贡献比例',
            barmode='group',
            legend=dict(
                orientation='h',
                yanchor='bottom',
                y=1.02,
                xanchor='right',
                x=1
            ),
            height=500,
            template='plotly_white',
            hovermode='x unified'
        )
        
        return fig
    else:
        fig, ax = plt.subplots(figsize=(12, 6))
        x = np.arange(len(species))
        width = 0.25
        
        for i, source in enumerate(source_names):
            y = source_profile.loc[source].values
            ax.bar(x + i * width, y, width, label=source, 
                   color=COLORS[i % len(COLORS)], alpha=0.85)
            
            if uncertainty_result is not None:
                std = uncertainty_result.F_std[i]
                ax.errorbar(x + i * width, y, yerr=std, fmt='none', 
                            color='black', capsize=3, linewidth=0.8)
        
        ax.set_xlabel('污染物种类', fontsize=12)
        ax.set_ylabel('相对贡献比例', fontsize=12)
        ax.set_title('污染源谱图', fontsize=16, pad=20)
        ax.set_xticks(x + width * (n_sources - 1) / 2)
        ax.set_xticklabels(species)
        ax.legend(loc='upper right', bbox_to_anchor=(1.15, 1))
        ax.grid(axis='y', alpha=0.3)
        
        plt.tight_layout()
        return fig


def plot_source_contribution_timeseries(
    source_contribution: pd.DataFrame,
    uncertainty_result=None,
    use_plotly: bool = True
):
    source_names = source_contribution.columns.tolist()
    
    if use_plotly:
        fig = go.Figure()
        
        for i, source in enumerate(source_names):
            y = source_contribution[source].values
            
            if uncertainty_result is not None:
                upper = uncertainty_result.G_upper[:, i]
                lower = uncertainty_result.G_lower[:, i]
                
                fig.add_trace(go.Scatter(
                    x=source_contribution.index,
                    y=upper,
                    mode='lines',
                    line=dict(width=0),
                    showlegend=False,
                    name=f'{source}_上限'
                ))
                
                fig.add_trace(go.Scatter(
                    x=source_contribution.index,
                    y=lower,
                    mode='lines',
                    line=dict(width=0),
                    fillcolor=f'rgba{tuple(int(COLORS[i % len(COLORS)].lstrip("#")[j:j+2], 16) for j in (0, 2, 4)) + (0.2,)}',
                    fill='tonexty',
                    showlegend=False,
                    name=f'{source}_下限'
                ))
            
            fig.add_trace(go.Scatter(
                x=source_contribution.index,
                y=y,
                mode='lines',
                name=source,
                line=dict(color=COLORS[i % len(COLORS)], width=2),
                opacity=0.9
            ))
        
        fig.update_layout(
            title=dict(
                text='污染源贡献时间序列',
                font=dict(size=20),
                x=0.5
            ),
            xaxis_title='日期',
            yaxis_title='源贡献浓度 (μg/m³)',
            hovermode='x unified',
            legend=dict(
                orientation='h',
                yanchor='bottom',
                y=1.02,
                xanchor='right',
                x=1
            ),
            height=500,
            template='plotly_white'
        )
        
        return fig
    else:
        fig, ax = plt.subplots(figsize=(14, 6))
        
        for i, source in enumerate(source_names):
            y = source_contribution[source].values
            ax.plot(source_contribution.index, y, label=source,
                   color=COLORS[i % len(COLORS)], linewidth=2, alpha=0.9)
            
            if uncertainty_result is not None:
                upper = uncertainty_result.G_upper[:, i]
                lower = uncertainty_result.G_lower[:, i]
                ax.fill_between(source_contribution.index, lower, upper,
                               color=COLORS[i % len(COLORS)], alpha=0.2)
        
        ax.set_xlabel('日期', fontsize=12)
        ax.set_ylabel('源贡献浓度 (μg/m³)', fontsize=12)
        ax.set_title('污染源贡献时间序列', fontsize=16, pad=20)
        ax.legend(loc='upper right', bbox_to_anchor=(1.15, 1))
        ax.grid(alpha=0.3)
        
        plt.tight_layout()
        return fig


def plot_contribution_pie(
    source_contribution: pd.DataFrame,
    use_plotly: bool = True
):
    source_names = source_contribution.columns.tolist()
    avg_contribution = source_contribution.mean()
    
    if use_plotly:
        fig = go.Figure(data=[go.Pie(
            labels=source_names,
            values=avg_contribution.values,
            hole=0.4,
            marker=dict(colors=[COLORS[i % len(COLORS)] for i in range(len(source_names))]),
            textinfo='label+percent',
            textfont=dict(size=14),
            insidetextorientation='radial'
        )])
        
        fig.update_layout(
            title=dict(
                text='平均污染源贡献占比',
                font=dict(size=20),
                x=0.5
            ),
            height=500,
            template='plotly_white',
            showlegend=True
        )
        
        return fig
    else:
        fig, ax = plt.subplots(figsize=(8, 8))
        
        wedges, texts, autotexts = ax.pie(
            avg_contribution.values,
            labels=source_names,
            autopct='%1.1f%%',
            colors=[COLORS[i % len(COLORS)] for i in range(len(source_names))],
            wedgeprops=dict(width=0.4, edgecolor='white'),
            textprops=dict(fontsize=12)
        )
        
        ax.set_title('平均污染源贡献占比', fontsize=16, pad=20)
        
        plt.tight_layout()
        return fig


def plot_residual_analysis(
    X: np.ndarray,
    residuals: np.ndarray,
    scaled_residuals: np.ndarray,
    species: List[str],
    use_plotly: bool = True
):
    if use_plotly:
        fig = make_subplots(
            rows=2, cols=2,
            subplot_titles=('残差分布', '标准化残差分布', 
                           '观测值 vs 预测值', '残差Q-Q图'),
            vertical_spacing=0.15
        )
        
        for i, sp in enumerate(species[:4]):
            row = i // 2 + 1
            col = i % 2 + 1
            
            if i < 2:
                fig.add_trace(
                    go.Histogram(
                        x=scaled_residuals[:, i],
                        name=sp,
                        opacity=0.7,
                        nbinsx=30,
                        marker_color=COLORS[i % len(COLORS)]
                    ),
                    row=1, col=i+1
                )
                fig.update_xaxes(title_text='标准化残差', row=1, col=i+1)
                fig.update_yaxes(title_text='频数', row=1, col=i+1)
            else:
                j = i - 2
                predicted = X[:, j] - residuals[:, j]
                fig.add_trace(
                    go.Scatter(
                        x=predicted,
                        y=residuals[:, j],
                        mode='markers',
                        name=sp,
                        marker=dict(
                            color=COLORS[i % len(COLORS)],
                            size=6,
                            opacity=0.6
                        )
                    ),
                    row=2, col=j+1
                )
                fig.update_xaxes(title_text='预测值', row=2, col=j+1)
                fig.update_yaxes(title_text='残差', row=2, col=j+1)
        
        fig.update_layout(
            title=dict(
                text='模型残差分析',
                font=dict(size=20),
                x=0.5
            ),
            height=700,
            template='plotly_white',
            showlegend=False
        )
        
        return fig
    else:
        fig, axes = plt.subplots(2, 2, figsize=(14, 10))
        
        for i, ax in enumerate(axes.flat):
            if i < len(species):
                if i < 2:
                    ax.hist(scaled_residuals[:, i], bins=30, alpha=0.7,
                           color=COLORS[i % len(COLORS)], edgecolor='white')
                    ax.set_xlabel('标准化残差', fontsize=10)
                    ax.set_ylabel('频数', fontsize=10)
                    ax.set_title(f'{species[i]} 残差分布', fontsize=12)
                else:
                    j = i - 2
                    predicted = X[:, j] - residuals[:, j]
                    ax.scatter(predicted, residuals[:, j], alpha=0.6,
                              color=COLORS[i % len(COLORS)], s=30)
                    ax.axhline(y=0, color='red', linestyle='--', linewidth=0.8)
                    ax.set_xlabel('预测值', fontsize=10)
                    ax.set_ylabel('残差', fontsize=10)
                    ax.set_title(f'{species[j]} 残差散点图', fontsize=12)
                ax.grid(alpha=0.3)
        
        plt.suptitle('模型残差分析', fontsize=16, y=1.02)
        plt.tight_layout()
        return fig


def plot_concentration_heatmap(
    df_concentration: pd.DataFrame,
    use_plotly: bool = True
):
    corr_matrix = df_concentration.corr()
    
    if use_plotly:
        fig = go.Figure(data=go.Heatmap(
            z=corr_matrix.values,
            x=corr_matrix.columns,
            y=corr_matrix.index,
            colorscale='RdBu_r',
            zmin=-1,
            zmax=1,
            text=corr_matrix.values.round(3),
            texttemplate='%{text}',
            textfont=dict(size=12),
            hoverongaps=False
        ))
        
        fig.update_layout(
            title=dict(
                text='污染物浓度相关性热力图',
                font=dict(size=20),
                x=0.5
            ),
            xaxis_title='',
            yaxis_title='',
            height=500,
            template='plotly_white'
        )
        
        return fig
    else:
        fig, ax = plt.subplots(figsize=(10, 8))
        
        sns.heatmap(corr_matrix, annot=True, fmt='.3f', cmap='RdBu_r',
                   center=0, vmin=-1, vmax=1, ax=ax,
                   annot_kws={'size': 10}, cbar_kws={'shrink': 0.8})
        
        ax.set_title('污染物浓度相关性热力图', fontsize=16, pad=20)
        
        plt.tight_layout()
        return fig


def plot_uncertainty_analysis(
    uncertainty_result,
    use_plotly: bool = True
):
    source_names = uncertainty_result.source_names
    species = uncertainty_result.species
    
    if use_plotly:
        fig = make_subplots(
            rows=1, cols=2,
            subplot_titles=('源谱变异系数', 'Q值分布'),
            column_widths=[0.7, 0.3]
        )
        
        cv_data = []
        for i, source in enumerate(source_names):
            for j, sp in enumerate(species):
                mean = uncertainty_result.F_mean[i, j]
                std = uncertainty_result.F_std[i, j]
                cv = (std / mean * 100) if mean > 0 else np.nan
                cv_data.append({
                    'source': source,
                    'species': sp,
                    'cv': cv
                })
        
        cv_df = pd.DataFrame(cv_data)
        
        for i, source in enumerate(source_names):
            source_data = cv_df[cv_df['source'] == source]
            fig.add_trace(go.Bar(
                x=source_data['species'],
                y=source_data['cv'],
                name=source,
                marker_color=COLORS[i % len(COLORS)],
                opacity=0.85
            ), row=1, col=1)
        
        fig.add_trace(go.Histogram(
            x=uncertainty_result.Q_values,
            nbinsx=20,
            marker_color=COLORS[0],
            opacity=0.75,
            name='Q值'
        ), row=1, col=2)
        
        fig.update_xaxes(title_text='污染物', row=1, col=1)
        fig.update_yaxes(title_text='变异系数 (%)', row=1, col=1)
        fig.update_xaxes(title_text='Q值', row=1, col=2)
        fig.update_yaxes(title_text='频数', row=1, col=2)
        
        fig.update_layout(
            title=dict(
                text='不确定性分析结果',
                font=dict(size=20),
                x=0.5
            ),
            barmode='group',
            height=500,
            template='plotly_white',
            legend=dict(
                orientation='h',
                yanchor='bottom',
                y=1.02,
                xanchor='right',
                x=1
            )
        )
        
        return fig
    else:
        fig, axes = plt.subplots(1, 2, figsize=(14, 6))
        
        x = np.arange(len(species))
        width = 0.25
        
        for i, source in enumerate(source_names):
            cv = (uncertainty_result.F_std[i] / uncertainty_result.F_mean[i] * 100)
            axes[0].bar(x + i * width, cv, width, label=source,
                       color=COLORS[i % len(COLORS)], alpha=0.85)
        
        axes[0].set_xlabel('污染物', fontsize=12)
        axes[0].set_ylabel('变异系数 (%)', fontsize=12)
        axes[0].set_title('源谱变异系数', fontsize=14)
        axes[0].set_xticks(x + width * (len(source_names) - 1) / 2)
        axes[0].set_xticklabels(species)
        axes[0].legend()
        axes[0].grid(axis='y', alpha=0.3)
        
        axes[1].hist(uncertainty_result.Q_values, bins=20, alpha=0.75,
                    color=COLORS[0], edgecolor='white')
        axes[1].set_xlabel('Q值', fontsize=12)
        axes[1].set_ylabel('频数', fontsize=12)
        axes[1].set_title('Q值分布', fontsize=14)
        axes[1].grid(alpha=0.3)
        
        plt.suptitle('不确定性分析结果', fontsize=16, y=1.02)
        plt.tight_layout()
        return fig


def plot_monthly_contribution(
    source_contribution: pd.DataFrame,
    use_plotly: bool = True
):
    source_names = source_contribution.columns.tolist()
    
    monthly_avg = source_contribution.groupby(source_contribution.index.month).mean()
    monthly_avg.index = ['1月', '2月', '3月', '4月', '5月', '6月', 
                        '7月', '8月', '9月', '10月', '11月', '12月']
    
    if use_plotly:
        fig = go.Figure()
        
        for i, source in enumerate(source_names):
            fig.add_trace(go.Bar(
                x=monthly_avg.index,
                y=monthly_avg[source],
                name=source,
                marker_color=COLORS[i % len(COLORS)],
                opacity=0.85
            ))
        
        fig.update_layout(
            title=dict(
                text='各月平均污染源贡献',
                font=dict(size=20),
                x=0.5
            ),
            xaxis_title='月份',
            yaxis_title='平均源贡献浓度 (μg/m³)',
            barmode='stack',
            legend=dict(
                orientation='h',
                yanchor='bottom',
                y=1.02,
                xanchor='right',
                x=1
            ),
            height=500,
            template='plotly_white'
        )
        
        return fig
    else:
        fig, ax = plt.subplots(figsize=(12, 6))
        
        bottom = np.zeros(len(monthly_avg))
        for i, source in enumerate(source_names):
            ax.bar(monthly_avg.index, monthly_avg[source], bottom=bottom,
                  label=source, color=COLORS[i % len(COLORS)], alpha=0.85)
            bottom += monthly_avg[source].values
        
        ax.set_xlabel('月份', fontsize=12)
        ax.set_ylabel('平均源贡献浓度 (μg/m³)', fontsize=12)
        ax.set_title('各月平均污染源贡献', fontsize=16, pad=20)
        ax.legend(loc='upper right', bbox_to_anchor=(1.15, 1))
        ax.grid(axis='y', alpha=0.3)
        
        plt.tight_layout()
        return fig


def plot_source_contribution_with_events(
    source_contribution: pd.DataFrame,
    events: List,
    uncertainty_result=None,
    confidence_level: int = 90,
    use_plotly: bool = True
):
    source_names = source_contribution.columns.tolist()
    
    if use_plotly:
        fig = go.Figure()
        
        for i, source in enumerate(source_names):
            y = source_contribution[source].values
            
            if uncertainty_result is not None:
                if uncertainty_result.G_percentiles is not None and confidence_level in uncertainty_result.G_percentiles:
                    upper = uncertainty_result.G_percentiles[confidence_level]['upper'][:, i]
                    lower = uncertainty_result.G_percentiles[confidence_level]['lower'][:, i]
                else:
                    upper = uncertainty_result.G_upper[:, i]
                    lower = uncertainty_result.G_lower[:, i]
                
                fig.add_trace(go.Scatter(
                    x=source_contribution.index,
                    y=upper,
                    mode='lines',
                    line=dict(width=0),
                    showlegend=False,
                    name=f'{source}_上限'
                ))
                
                fig.add_trace(go.Scatter(
                    x=source_contribution.index,
                    y=lower,
                    mode='lines',
                    line=dict(width=0),
                    fillcolor=f'rgba{tuple(int(COLORS[i % len(COLORS)].lstrip("#")[j:j+2], 16) for j in (0, 2, 4)) + (0.2,)}',
                    fill='tonexty',
                    showlegend=False,
                    name=f'{source}_下限'
                ))
            
            fig.add_trace(go.Scatter(
                x=source_contribution.index,
                y=y,
                mode='lines',
                name=source,
                line=dict(color=COLORS[i % len(COLORS)], width=2),
                opacity=0.9
            ))
        
        event_colors = ['red', 'orange', 'green', 'purple', 'brown']
        for j, event in enumerate(events):
            fig.add_vrect(
                x0=event.start_date,
                x1=event.end_date,
                fillcolor=event_colors[j % len(event_colors)],
                opacity=0.15,
                layer="below",
                line_width=0,
                annotation_text=event.event_id,
                annotation_position="top left"
            )
        
        fig.update_layout(
            title=dict(
                text='污染源贡献时间序列（带事件标注）',
                font=dict(size=20),
                x=0.5
            ),
            xaxis_title='日期',
            yaxis_title='源贡献浓度 (μg/m³)',
            hovermode='x unified',
            legend=dict(
                orientation='h',
                yanchor='bottom',
                y=1.02,
                xanchor='right',
                x=1
            ),
            height=500,
            template='plotly_white'
        )
        
        return fig
    else:
        fig, ax = plt.subplots(figsize=(14, 6))
        
        for i, source in enumerate(source_names):
            y = source_contribution[source].values
            ax.plot(source_contribution.index, y, label=source,
                   color=COLORS[i % len(COLORS)], linewidth=2, alpha=0.9)
            
            if uncertainty_result is not None:
                if uncertainty_result.G_percentiles is not None and confidence_level in uncertainty_result.G_percentiles:
                    upper = uncertainty_result.G_percentiles[confidence_level]['upper'][:, i]
                    lower = uncertainty_result.G_percentiles[confidence_level]['lower'][:, i]
                else:
                    upper = uncertainty_result.G_upper[:, i]
                    lower = uncertainty_result.G_lower[:, i]
                ax.fill_between(source_contribution.index, lower, upper,
                               color=COLORS[i % len(COLORS)], alpha=0.2)
        
        event_colors = ['red', 'orange', 'green', 'purple', 'brown']
        for j, event in enumerate(events):
            ax.axvspan(event.start_date, event.end_date, 
                      alpha=0.15, color=event_colors[j % len(event_colors)])
            ax.text(event.start_date, ax.get_ylim()[1] * 0.95, 
                    f"{event.event_id}", 
                    color=event_colors[j % len(event_colors)],
                    fontsize=9, ha='left')
        
        ax.set_xlabel('日期', fontsize=12)
        ax.set_ylabel('源贡献浓度 (μg/m³)', fontsize=12)
        ax.set_title('污染源贡献时间序列（带事件标注）', fontsize=16, pad=20)
        ax.legend(loc='upper right', bbox_to_anchor=(1.15, 1))
        ax.grid(alpha=0.3)
        
        plt.tight_layout()
        return fig


def plot_factor_selection_metrics(
    factor_metrics: pd.DataFrame,
    use_plotly: bool = True
):
    if use_plotly:
        fig = make_subplots(
            rows=2, cols=2,
            subplot_titles=('Q/自由度 vs 因子数', '解释方差 vs 因子数',
                           '稳定性得分 vs 因子数', '异常值比例 vs 因子数')
        )
        
        x = factor_metrics['因子数'].values
        
        fig.add_trace(
            go.Scatter(
                x=x,
                y=factor_metrics['Q/自由度'].values,
                mode='lines+markers',
                name='Q/自由度',
                line=dict(color=COLORS[0], width=2),
                marker=dict(size=8)
            ),
            row=1, col=1
        )
        fig.add_hline(y=1.5, line_dash="dash", line_color="red", 
                     annotation_text="阈值=1.5", row=1, col=1)
        
        fig.add_trace(
            go.Scatter(
                x=x,
                y=factor_metrics['解释方差(%)'].values,
                mode='lines+markers',
                name='解释方差(%)',
                line=dict(color=COLORS[1], width=2),
                marker=dict(size=8)
            ),
            row=1, col=2
        )
        
        fig.add_trace(
            go.Scatter(
                x=x,
                y=factor_metrics['稳定性得分'].values,
                mode='lines+markers',
                name='稳定性得分',
                line=dict(color=COLORS[2], width=2),
                marker=dict(size=8)
            ),
            row=2, col=1
        )
        fig.add_hline(y=0.8, line_dash="dash", line_color="red",
                     annotation_text="阈值=0.8", row=2, col=1)
        
        fig.add_trace(
            go.Scatter(
                x=x,
                y=factor_metrics['异常值比例(%)'].values,
                mode='lines+markers',
                name='异常值比例(%)',
                line=dict(color=COLORS[3], width=2),
                marker=dict(size=8)
            ),
            row=2, col=2
        )
        
        fig.update_xaxes(title_text='因子数', row=1, col=1)
        fig.update_xaxes(title_text='因子数', row=1, col=2)
        fig.update_xaxes(title_text='因子数', row=2, col=1)
        fig.update_xaxes(title_text='因子数', row=2, col=2)
        
        fig.update_layout(
            title=dict(
                text='因子数选择评估指标',
                font=dict(size=18),
                x=0.5
            ),
            height=600,
            template='plotly_white',
            showlegend=False
        )
        
        return fig
    else:
        fig, axes = plt.subplots(2, 2, figsize=(14, 10))
        
        x = factor_metrics['因子数'].values
        
        axes[0, 0].plot(x, factor_metrics['Q/自由度'], 
                       color=COLORS[0], linewidth=2, marker='o', markersize=8)
        axes[0, 0].axhline(y=1.5, color='red', linestyle='--', label='阈值=1.5')
        axes[0, 0].set_title('Q/自由度 vs 因子数', fontsize=12)
        axes[0, 0].grid(alpha=0.3)
        axes[0, 0].legend()
        
        axes[0, 1].plot(x, factor_metrics['解释方差(%)'], 
                       color=COLORS[1], linewidth=2, marker='o', markersize=8)
        axes[0, 1].set_title('解释方差 vs 因子数', fontsize=12)
        axes[0, 1].grid(alpha=0.3)
        
        axes[1, 0].plot(x, factor_metrics['稳定性得分'], 
                       color=COLORS[2], linewidth=2, marker='o', markersize=8)
        axes[1, 0].axhline(y=0.8, color='red', linestyle='--', label='阈值=0.8')
        axes[1, 0].set_title('稳定性得分 vs 因子数', fontsize=12)
        axes[1, 0].grid(alpha=0.3)
        axes[1, 0].legend()
        
        axes[1, 1].plot(x, factor_metrics['异常值比例(%)'], 
                       color=COLORS[3], linewidth=2, marker='o', markersize=8)
        axes[1, 1].set_title('异常值比例 vs 因子数', fontsize=12)
        axes[1, 1].grid(alpha=0.3)
        
        plt.suptitle('因子数选择评估指标', fontsize=16, y=1.02)
        plt.tight_layout()
        return fig


def plot_event_timeline(
    events: List,
    use_plotly: bool = True
):
    if use_plotly:
        fig = go.Figure()
        
        for i, event in enumerate(events):
            fig.add_trace(go.Scatter(
                x=[event.start_date, event.end_date],
                y=[i, i],
                mode='lines',
                line=dict(width=10, color=COLORS[i % len(COLORS)]),
                name=event.event_id,
                hovertext=f"{event.event_type}<br>{event.description}<br>置信度: {event.confidence:.2f}",
                hoverinfo='text'
            ))
        
        fig.update_layout(
            title=dict(
                text='排放事件时间线',
                font=dict(size=18),
                x=0.5
            ),
            xaxis_title='日期',
            yaxis_title='事件',
            height=400,
            template='plotly_white',
            yaxis=dict(
                tickmode='array',
                tickvals=list(range(len(events))),
                ticktext=[e.event_id for e in events]
            )
        )
        
        return fig
    else:
        fig, ax = plt.subplots(figsize=(14, max(4, len(events)*0.5 + 2)))
        
        for i, event in enumerate(events):
            ax.hlines(i, xmin=event.start_date, xmax=event.end_date, 
                     linewidth=8, color=COLORS[i % len(COLORS)])
            ax.text(event.start_date, i + 0.1, 
                    f"{event.event_type} ({event.confidence:.2f})", 
                    fontsize=10)
        
        ax.set_yticks(list(range(len(events))))
        ax.set_yticklabels([e.event_id for e in events])
        ax.set_xlabel('日期', fontsize=12)
        ax.set_title('排放事件时间线', fontsize=16, pad=20)
        ax.grid(axis='x', alpha=0.3)
        
        plt.tight_layout()
        return fig


def plot_multiple_confidence_intervals(
    source_contribution: pd.DataFrame,
    uncertainty_result,
    source_idx: int = 0,
    confidence_levels: List[int] = None,
    use_plotly: bool = True
):
    source_name = source_contribution.columns[source_idx]
    confidence_levels = confidence_levels or [50, 80, 90, 95]
    
    if use_plotly:
        fig = go.Figure()
        
        colors = [
            'rgba(255, 107, 107',
            'rgba(78, 205, 196', 
            'rgba(69, 183, 209',
            'rgba(150, 206, 180'
        ]
        
        for i, cl in enumerate(confidence_levels):
            if uncertainty_result.G_percentiles is not None and cl in uncertainty_result.G_percentiles:
                upper = uncertainty_result.G_percentiles[cl]['upper'][:, source_idx]
                lower = uncertainty_result.G_percentiles[cl]['lower'][:, source_idx]
            else:
                upper = uncertainty_result.G_upper[:, source_idx]
                lower = uncertainty_result.G_lower[:, source_idx]
            
            alpha = 0.1 + 0.1 * i
            
            fig.add_trace(go.Scatter(
                x=source_contribution.index,
                y=upper,
                mode='lines',
                line=dict(width=0),
                showlegend=False
            ))
            
            fig.add_trace(go.Scatter(
                x=source_contribution.index,
                y=lower,
                mode='lines',
                line=dict(width=0),
                fillcolor=f'{colors[i % len(colors)]}, {alpha})',
                fill='tonexty',
                name=f'{cl}% CI'
            ))
        
        fig.add_trace(go.Scatter(
            x=source_contribution.index,
            y=source_contribution[source_name].values,
            mode='lines',
            name='均值',
            line=dict(color='#667eea', width=2)
        ))
        
        fig.update_layout(
            title=dict(
                text=f'{source_name} 多置信区间对比',
                font=dict(size=18),
                x=0.5
            ),
            xaxis_title='日期',
            yaxis_title='源贡献浓度 (μg/m³)',
            height=500,
            template='plotly_white'
        )
        
        return fig
    else:
        fig, ax = plt.subplots(figsize=(14, 6))
        
        colors = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4']
        
        for i, cl in enumerate(confidence_levels):
            if uncertainty_result.G_percentiles is not None and cl in uncertainty_result.G_percentiles:
                upper = uncertainty_result.G_percentiles[cl]['upper'][:, source_idx]
                lower = uncertainty_result.G_percentiles[cl]['lower'][:, source_idx]
            else:
                upper = uncertainty_result.G_upper[:, source_idx]
                lower = uncertainty_result.G_lower[:, source_idx]
            
            alpha = 0.1 + 0.1 * i
            ax.fill_between(source_contribution.index, lower, upper, 
                          alpha=alpha, color=colors[i % len(colors)], label=f'{cl}% CI')
        
        ax.plot(source_contribution.index, source_contribution[source_name].values, 
                color='#667eea', linewidth=2, label='均值')
        
        ax.set_xlabel('日期', fontsize=12)
        ax.set_ylabel('源贡献浓度 (μg/m³)', fontsize=12)
        ax.set_title(f'{source_name} 多置信区间对比', fontsize=16, pad=20)
        ax.legend()
        ax.grid(alpha=0.3)
        
        plt.tight_layout()
        return fig


def plot_spatial_heatmap(
    spatial_result,
    source_idx: int = 0,
    use_plotly: bool = True
):
    source_name = spatial_result.source_names[source_idx]
    grid_lat = spatial_result.grid_lat
    grid_lon = spatial_result.grid_lon
    grid_data = spatial_result.grid_data[source_name]
    points = spatial_result.points
    
    if use_plotly:
        fig = go.Figure()
        
        fig.add_trace(go.Heatmap(
            z=grid_data,
            x=grid_lon[0, :],
            y=grid_lat[:, 0],
            colorscale='Viridis',
            hoverongaps=False,
            colorbar=dict(title='源贡献浓度'),
            opacity=0.8
        ))
        
        point_lats = [p.latitude for p in points]
        point_lons = [p.longitude for p in points]
        point_values = [p.source_contributions.get(source_name, 0) for p in points]
        point_names = [p.site_name for p in points]
        
        fig.add_trace(go.Scatter(
            x=point_lons,
            y=point_lats,
            mode='markers',
            marker=dict(
                size=12,
                color='red',
                line=dict(width=2, color='white')
            ),
            text=[f"{name}: {val:.2f}" for name, val in zip(point_names, point_values)],
            hoverinfo='text',
            name='监测站'
        ))
        
        fig.update_layout(
            title=dict(
                text=f'{source_name} 空间分布热力图',
                font=dict(size=18),
                x=0.5
            ),
            xaxis_title='经度',
            yaxis_title='纬度',
            height=600,
            template='plotly_white'
        )
        
        return fig
    else:
        fig, ax = plt.subplots(figsize=(10, 8))
        
        im = ax.pcolormesh(grid_lon, grid_lat, grid_data, cmap='viridis', alpha=0.8)
        plt.colorbar(im, ax=ax, label='源贡献浓度')
        
        point_lats = [p.latitude for p in points]
        point_lons = [p.longitude for p in points]
        ax.scatter(point_lons, point_lats, c='red', s=100, edgecolors='white', zorder=5, label='监测站')
        
        ax.set_xlabel('经度', fontsize=12)
        ax.set_ylabel('纬度', fontsize=12)
        ax.set_title(f'{source_name} 空间分布热力图', fontsize=16, pad=20)
        ax.legend()
        
        plt.tight_layout()
        return fig


def plot_emission_reduction(
    reduction_result,
    pollutant: str = 'PM2.5',
    use_plotly: bool = True
):
    if use_plotly:
        fig = go.Figure()
        
        original = reduction_result.original_concentration[pollutant]
        reduced = reduction_result.reduced_concentration[pollutant]
        
        fig.add_trace(go.Scatter(
            x=original.index,
            y=original.values,
            mode='lines',
            name='原始浓度',
            line=dict(color=COLORS[0], width=2)
        ))
        
        fig.add_trace(go.Scatter(
            x=reduced.index,
            y=reduced.values,
            mode='lines',
            name='减排后浓度',
            line=dict(color=COLORS[1], width=2)
        ))
        
        fig.add_trace(go.Scatter(
            x=reduced.index,
            y=original.values - reduced.values,
            mode='lines',
            name='减排量',
            line=dict(color=COLORS[2], width=2, dash='dash'),
            yaxis='y2'
        ))
        
        fig.update_layout(
            title=dict(
                text=f'{pollutant} 减排效果模拟',
                font=dict(size=18),
                x=0.5
            ),
            xaxis_title='日期',
            yaxis_title='浓度 (μg/m³)',
            height=500,
            template='plotly_white',
            yaxis2=dict(
                title='减排量 (μg/m³)',
                overlaying='y',
                side='right'
            ),
            legend=dict(
                orientation='h',
                yanchor='bottom',
                y=1.02,
                xanchor='right',
                x=1
            )
        )
        
        return fig
    else:
        fig, ax1 = plt.subplots(figsize=(14, 6))
        
        original = reduction_result.original_concentration[pollutant]
        reduced = reduction_result.reduced_concentration[pollutant]
        reduction = original - reduced
        
        ax1.plot(original.index, original.values, label='原始浓度', 
                color=COLORS[0], linewidth=2)
        ax1.plot(reduced.index, reduced.values, label='减排后浓度', 
                color=COLORS[1], linewidth=2)
        
        ax1.set_xlabel('日期', fontsize=12)
        ax1.set_ylabel('浓度 (μg/m³)', fontsize=12)
        ax1.tick_params(axis='y')
        ax1.grid(alpha=0.3)
        
        ax2 = ax1.twinx()
        ax2.plot(original.index, reduction.values, label='减排量', 
                color=COLORS[2], linewidth=2, linestyle='--')
        ax2.set_ylabel('减排量 (μg/m³)', fontsize=12)
        ax2.tick_params(axis='y')
        
        lines1, labels1 = ax1.get_legend_handles_labels()
        lines2, labels2 = ax2.get_legend_handles_labels()
        ax1.legend(lines1 + lines2, labels1 + labels2, 
                  loc='upper right', bbox_to_anchor=(1.15, 1))
        
        ax1.set_title(f'{pollutant} 减排效果模拟', fontsize=16, pad=20)
        
        plt.tight_layout()
        return fig


def plot_reduction_comparison(
    comparison_df: pd.DataFrame,
    use_plotly: bool = True
):
    if use_plotly:
        fig = go.Figure()
        
        fig.add_trace(go.Bar(
            x=comparison_df['场景名称'],
            y=comparison_df['总减排率(%)'].astype(float),
            name='总减排率(%)',
            marker_color=COLORS[0],
            opacity=0.8
        ))
        
        fig.add_trace(go.Bar(
            x=comparison_df['场景名称'],
            y=comparison_df['PM2.5减排率(%)'].astype(float),
            name='PM2.5减排率(%)',
            marker_color=COLORS[1],
            opacity=0.8
        ))
        
        fig.update_layout(
            title=dict(
                text='不同减排场景效果对比',
                font=dict(size=18),
                x=0.5
            ),
            xaxis_title='减排场景',
            yaxis_title='减排率 (%)',
            barmode='group',
            height=500,
            template='plotly_white',
            legend=dict(
                orientation='h',
                yanchor='bottom',
                y=1.02,
                xanchor='right',
                x=1
            )
        )
        
        return fig
    else:
        fig, ax = plt.subplots(figsize=(12, 6))
        
        x = np.arange(len(comparison_df))
        width = 0.35
        
        ax.bar(x - width/2, comparison_df['总减排率(%)'].astype(float), width, 
               label='总减排率(%)', color=COLORS[0], alpha=0.8)
        ax.bar(x + width/2, comparison_df['PM2.5减排率(%)'].astype(float), width, 
               label='PM2.5减排率(%)', color=COLORS[1], alpha=0.8)
        
        ax.set_xlabel('减排场景', fontsize=12)
        ax.set_ylabel('减排率 (%)', fontsize=12)
        ax.set_title('不同减排场景效果对比', fontsize=16, pad=20)
        ax.set_xticks(x)
        ax.set_xticklabels(comparison_df['场景名称'], rotation=45, ha='right')
        ax.legend()
        ax.grid(axis='y', alpha=0.3)
        
        plt.tight_layout()
        return fig


def plot_weather_correlation(
    corr_matrix: pd.DataFrame,
    use_plotly: bool = True
):
    if use_plotly:
        fig = go.Figure(data=go.Heatmap(
            z=corr_matrix.values,
            x=corr_matrix.columns,
            y=corr_matrix.index,
            colorscale='RdBu_r',
            zmin=-1,
            zmax=1,
            text=corr_matrix.values.round(3),
            texttemplate='%{text}',
            textfont=dict(size=12),
            hoverongaps=False
        ))
        
        fig.update_layout(
            title=dict(
                text='污染源-气象因子相关性热力图',
                font=dict(size=18),
                x=0.5
            ),
            xaxis_title='气象因子',
            yaxis_title='污染源',
            height=500,
            template='plotly_white'
        )
        
        return fig
    else:
        fig, ax = plt.subplots(figsize=(10, 6))
        
        sns.heatmap(corr_matrix, annot=True, fmt='.3f', cmap='RdBu_r',
                   center=0, vmin=-1, vmax=1, ax=ax,
                   annot_kws={'size': 10}, cbar_kws={'shrink': 0.8})
        
        ax.set_xlabel('气象因子', fontsize=12)
        ax.set_ylabel('污染源', fontsize=12)
        ax.set_title('污染源-气象因子相关性热力图', fontsize=16, pad=20)
        
        plt.tight_layout()
        return fig


def plot_seasonal_variation(
    seasonal_data: pd.DataFrame,
    use_plotly: bool = True
):
    sources = seasonal_data['污染源'].unique()
    seasons = ['春季', '夏季', '秋季', '冬季']
    
    if use_plotly:
        fig = go.Figure()
        
        for i, source in enumerate(sources):
            source_data = seasonal_data[seasonal_data['污染源'] == source]
            season_order = [s for s in seasons if s in source_data['季节'].values]
            source_data = source_data.set_index('季节').loc[season_order]
            
            fig.add_trace(go.Bar(
                x=source_data.index,
                y=source_data['平均贡献'],
                name=source,
                marker_color=COLORS[i % len(COLORS)],
                opacity=0.85,
                error_y=dict(
                    type='data',
                    array=source_data['贡献标准差'],
                    visible=True
                )
            ))
        
        fig.update_layout(
            title=dict(
                text='污染源贡献季节变化',
                font=dict(size=18),
                x=0.5
            ),
            xaxis_title='季节',
            yaxis_title='平均源贡献浓度 (μg/m³)',
            barmode='group',
            height=500,
            template='plotly_white',
            legend=dict(
                orientation='h',
                yanchor='bottom',
                y=1.02,
                xanchor='right',
                x=1
            )
        )
        
        return fig
    else:
        fig, ax = plt.subplots(figsize=(12, 6))
        
        x = np.arange(len(seasons))
        width = 0.8 / len(sources)
        
        for i, source in enumerate(sources):
            source_data = seasonal_data[seasonal_data['污染源'] == source]
            season_order = [s for s in seasons if s in source_data['季节'].values]
            source_data = source_data.set_index('季节').loc[season_order]
            
            ax.bar(x + i * width - width * (len(sources) - 1) / 2,
                   source_data['平均贡献'],
                   width,
                   label=source,
                   color=COLORS[i % len(COLORS)],
                   alpha=0.85,
                   yerr=source_data['贡献标准差'],
                   capsize=3)
        
        ax.set_xlabel('季节', fontsize=12)
        ax.set_ylabel('平均源贡献浓度 (μg/m³)', fontsize=12)
        ax.set_title('污染源贡献季节变化', fontsize=16, pad=20)
        ax.set_xticks(x)
        ax.set_xticklabels(season_order)
        ax.legend()
        ax.grid(axis='y', alpha=0.3)
        
        plt.tight_layout()
        return fig


def plot_wind_rose(
    wind_data: pd.DataFrame,
    source_name: str,
    use_plotly: bool = True
):
    if use_plotly:
        fig = go.Figure()
        
        speed_levels = wind_data['风速等级'].unique()
        
        for i, speed in enumerate(speed_levels):
            level_data = wind_data[wind_data['风速等级'] == speed]
            fig.add_trace(go.Barpolar(
                r=level_data['平均贡献'],
                theta=level_data['风向角度'],
                name=speed,
                marker_color=COLORS[i % len(COLORS)],
                opacity=0.7
            ))
        
        fig.update_layout(
            title=dict(
                text=f'{source_name} 风向玫瑰图',
                font=dict(size=18),
                x=0.5
            ),
            height=500,
            template='plotly_white',
            polar=dict(
                radialaxis=dict(
                    title='平均源贡献',
                    showticklabels=True
                ),
                angularaxis=dict(
                    ticktext=['N', 'NE', 'E', 'SE', 'S', 'SW', 'W', 'NW'],
                    tickvals=[0, 45, 90, 135, 180, 225, 270, 315]
                )
            )
        )
        
        return fig
    else:
        fig = plt.figure(figsize=(10, 8))
        ax = fig.add_subplot(111, projection='polar')
        
        speed_levels = wind_data['风速等级'].unique()
        width = 2 * np.pi / 8
        
        for i, speed in enumerate(speed_levels):
            level_data = wind_data[wind_data['风速等级'] == speed]
            angles = np.deg2rad(level_data['风向角度'])
            
            ax.bar(angles, level_data['平均贡献'],
                   width=width,
                   alpha=0.7,
                   color=COLORS[i % len(COLORS)],
                   label=speed)
        
        ax.set_theta_zero_location('N')
        ax.set_theta_direction(-1)
        ax.set_xticks(np.deg2rad([0, 45, 90, 135, 180, 225, 270, 315]))
        ax.set_xticklabels(['N', 'NE', 'E', 'SE', 'S', 'SW', 'W', 'NW'])
        ax.set_ylabel('平均源贡献')
        ax.set_title(f'{source_name} 风向玫瑰图', fontsize=16, pad=20)
        ax.legend()
        
        plt.tight_layout()
        return fig
