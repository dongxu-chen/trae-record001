import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
from typing import Dict, Optional

plt.style.use('seaborn-v0_8-darkgrid')
sns.set_palette('husl')


def plot_price_sales_scatter(
    df: pd.DataFrame,
    interactive: bool = True
):
    if interactive:
        fig = px.scatter(
            df,
            x='effective_price',
            y='sales_quantity',
            color='is_promotion',
            size='advertising_spend',
            hover_data=['date', 'revenue', 'competitor_price'],
            title='价格 vs 销量散点图（区分促销期）',
            labels={
                'effective_price': '实际价格 (元)',
                'sales_quantity': '销售数量',
                'is_promotion': '是否促销',
                'advertising_spend': '广告投入'
            },
            color_discrete_map={0: '#FF6B6B', 1: '#4ECDC4'}
        )
        fig.update_layout(height=500)
        return fig
    else:
        fig, ax = plt.subplots(figsize=(10, 6))
        mask_promo = df['is_promotion'] == 1
        ax.scatter(
            df.loc[~mask_promo, 'effective_price'],
            df.loc[~mask_promo, 'sales_quantity'],
            c='#FF6B6B',
            alpha=0.6,
            label='非促销期'
        )
        ax.scatter(
            df.loc[mask_promo, 'effective_price'],
            df.loc[mask_promo, 'sales_quantity'],
            c='#4ECDC4',
            alpha=0.6,
            label='促销期'
        )
        ax.set_xlabel('实际价格 (元)')
        ax.set_ylabel('销售数量')
        ax.set_title('价格 vs 销量散点图')
        ax.legend()
        plt.tight_layout()
        return fig


def plot_elasticity_curve(
    elasticity_df: pd.DataFrame,
    interactive: bool = True,
    show_ci: bool = True
):
    has_ci = 'prob_ci_lower' in elasticity_df.columns and 'prob_ci_upper' in elasticity_df.columns
    has_promo_split = 'is_promotion' in elasticity_df.columns
    
    if has_promo_split:
        promo_df = elasticity_df[elasticity_df['is_promotion'] == 1]
        non_promo_df = elasticity_df[elasticity_df['is_promotion'] == 0]
    else:
        promo_df = elasticity_df
        non_promo_df = pd.DataFrame()
    
    if interactive:
        fig = make_subplots(
            rows=2, cols=2,
            subplot_titles=(
                '价格-购买概率曲线' + ('（Bootstrap 95% CI）' if show_ci and has_ci else ''),
                '价格-弹性系数曲线' + ('（Bootstrap 95% CI）' if show_ci and has_ci else ''),
                '弹性分布',
                '价格-边际收益曲线'
            ),
            vertical_spacing=0.12,
            horizontal_spacing=0.1
        )

        if has_promo_split:
            fig.add_trace(
                go.Scatter(
                    x=non_promo_df['price'],
                    y=non_promo_df['purchase_probability'],
                    mode='lines',
                    name='非促销期购买概率',
                    line=dict(color='#1f77b4', width=3)
                ),
                row=1, col=1
            )
            
            if show_ci and has_ci:
                fig.add_trace(
                    go.Scatter(
                        x=non_promo_df['price'],
                        y=non_promo_df['prob_ci_upper'],
                        mode='lines',
                        line=dict(color='rgba(31, 119, 180, 0.3)', width=0),
                        showlegend=False,
                        name='非促销期CI上限'
                    ),
                    row=1, col=1
                )
                fig.add_trace(
                    go.Scatter(
                        x=non_promo_df['price'],
                        y=non_promo_df['prob_ci_lower'],
                        mode='lines',
                        line=dict(color='rgba(31, 119, 180, 0.3)', width=0),
                        fill='tonexty',
                        fillcolor='rgba(31, 119, 180, 0.15)',
                        showlegend=False,
                        name='非促销期CI下限'
                    ),
                    row=1, col=1
                )
            
            fig.add_trace(
                go.Scatter(
                    x=promo_df['price'],
                    y=promo_df['purchase_probability'],
                    mode='lines',
                    name='促销期购买概率',
                    line=dict(color='#ff7f0e', width=3, dash='dash')
                ),
                row=1, col=1
            )
            
            if show_ci and has_ci:
                fig.add_trace(
                    go.Scatter(
                        x=promo_df['price'],
                        y=promo_df['prob_ci_upper'],
                        mode='lines',
                        line=dict(color='rgba(255, 127, 14, 0.3)', width=0),
                        showlegend=False,
                        name='促销期CI上限'
                    ),
                    row=1, col=1
                )
                fig.add_trace(
                    go.Scatter(
                        x=promo_df['price'],
                        y=promo_df['prob_ci_lower'],
                        mode='lines',
                        line=dict(color='rgba(255, 127, 14, 0.3)', width=0),
                        fill='tonexty',
                        fillcolor='rgba(255, 127, 14, 0.15)',
                        showlegend=False,
                        name='促销期CI下限'
                    ),
                    row=1, col=1
                )
        else:
            fig.add_trace(
                go.Scatter(
                    x=elasticity_df['price'],
                    y=elasticity_df['purchase_probability'],
                    mode='lines',
                    name='购买概率',
                    line=dict(color='#1f77b4', width=3)
                ),
                row=1, col=1
            )
            
            if show_ci and has_ci:
                fig.add_trace(
                    go.Scatter(
                        x=elasticity_df['price'],
                        y=elasticity_df['prob_ci_upper'],
                        mode='lines',
                        line=dict(color='rgba(31, 119, 180, 0.3)', width=0),
                        showlegend=False
                    ),
                    row=1, col=1
                )
                fig.add_trace(
                    go.Scatter(
                        x=elasticity_df['price'],
                        y=elasticity_df['prob_ci_lower'],
                        mode='lines',
                        line=dict(color='rgba(31, 119, 180, 0.3)', width=0),
                        fill='tonexty',
                        fillcolor='rgba(31, 119, 180, 0.15)',
                        showlegend=False
                    ),
                    row=1, col=1
                )

        if has_promo_split:
            fig.add_trace(
                go.Scatter(
                    x=non_promo_df['price'],
                    y=non_promo_df['point_elasticity'],
                    mode='lines',
                    name='非促销期点弹性',
                    line=dict(color='#1f77b4', width=3)
                ),
                row=1, col=2
            )
            
            if show_ci and 'elasticity_ci_lower' in non_promo_df.columns:
                fig.add_trace(
                    go.Scatter(
                        x=non_promo_df['price'],
                        y=non_promo_df['elasticity_ci_upper'],
                        mode='lines',
                        line=dict(color='rgba(31, 119, 180, 0.3)', width=0),
                        showlegend=False
                    ),
                    row=1, col=2
                )
                fig.add_trace(
                    go.Scatter(
                        x=non_promo_df['price'],
                        y=non_promo_df['elasticity_ci_lower'],
                        mode='lines',
                        line=dict(color='rgba(31, 119, 180, 0.3)', width=0),
                        fill='tonexty',
                        fillcolor='rgba(31, 119, 180, 0.15)',
                        showlegend=False
                    ),
                    row=1, col=2
                )
            
            fig.add_trace(
                go.Scatter(
                    x=promo_df['price'],
                    y=promo_df['point_elasticity'],
                    mode='lines',
                    name='促销期点弹性',
                    line=dict(color='#ff7f0e', width=3, dash='dash')
                ),
                row=1, col=2
            )
            
            if show_ci and 'elasticity_ci_lower' in promo_df.columns:
                fig.add_trace(
                    go.Scatter(
                        x=promo_df['price'],
                        y=promo_df['elasticity_ci_upper'],
                        mode='lines',
                        line=dict(color='rgba(255, 127, 14, 0.3)', width=0),
                        showlegend=False
                    ),
                    row=1, col=2
                )
                fig.add_trace(
                    go.Scatter(
                        x=promo_df['price'],
                        y=promo_df['elasticity_ci_lower'],
                        mode='lines',
                        line=dict(color='rgba(255, 127, 14, 0.3)', width=0),
                        fill='tonexty',
                        fillcolor='rgba(255, 127, 14, 0.15)',
                        showlegend=False
                    ),
                    row=1, col=2
                )
        else:
            fig.add_trace(
                go.Scatter(
                    x=elasticity_df['price'],
                    y=elasticity_df['point_elasticity'],
                    mode='lines',
                    name='点弹性',
                    line=dict(color='#ff7f0e', width=3)
                ),
                row=1, col=2
            )

        fig.add_hline(
            y=-1, line_dash="dash", line_color="red",
            annotation_text="单位弹性 (ε=-1)",
            row=1, col=2
        )

        if has_promo_split:
            for label, df_plot in [('非促销期', non_promo_df), ('促销期', promo_df)]:
                elasticity_counts = df_plot['elasticity_category'].value_counts().reset_index()
                elasticity_counts.columns = ['category', 'count']
                color_map = {
                    '极富弹性 (<-2)': '#d62728',
                    '富有弹性 (-2~-1)': '#ff7f0e',
                    '单位弹性 (-1~-0.5)': '#2ca02c',
                    '缺乏弹性 (-0.5~0)': '#1f77b4',
                    '无弹性 (>0)': '#9467bd'
                }

                fig.add_trace(
                    go.Bar(
                        x=elasticity_counts['category'],
                        y=elasticity_counts['count'],
                        name=f'{label}弹性分布',
                        marker_color=[color_map.get(c, '#7f7f7f') for c in elasticity_counts['category']],
                        opacity=0.7 if label == '促销期' else 1.0
                    ),
                    row=2, col=1
                )
        else:
            elasticity_counts = elasticity_df['elasticity_category'].value_counts().reset_index()
            elasticity_counts.columns = ['category', 'count']
            color_map = {
                '极富弹性 (<-2)': '#d62728',
                '富有弹性 (-2~-1)': '#ff7f0e',
                '单位弹性 (-1~-0.5)': '#2ca02c',
                '缺乏弹性 (-0.5~0)': '#1f77b4',
                '无弹性 (>0)': '#9467bd'
            }

            fig.add_trace(
                go.Bar(
                    x=elasticity_counts['category'],
                    y=elasticity_counts['count'],
                    name='弹性分布',
                    marker_color=[color_map.get(c, '#7f7f7f') for c in elasticity_counts['category']]
                ),
                row=2, col=1
            )

        if has_promo_split:
            revenue_non_promo = non_promo_df['price'] * non_promo_df['purchase_probability']
            revenue_promo = promo_df['price'] * promo_df['purchase_probability']
            
            fig.add_trace(
                go.Scatter(
                    x=non_promo_df['price'],
                    y=revenue_non_promo,
                    mode='lines',
                    name='非促销期预期收入指数',
                    line=dict(color='#1f77b4', width=3)
                ),
                row=2, col=2
            )
            
            fig.add_trace(
                go.Scatter(
                    x=promo_df['price'],
                    y=revenue_promo,
                    mode='lines',
                    name='促销期预期收入指数',
                    line=dict(color='#ff7f0e', width=3, dash='dash')
                ),
                row=2, col=2
            )
            
            max_rev_idx_non_promo = np.argmax(revenue_non_promo)
            max_rev_idx_promo = np.argmax(revenue_promo)
            
            fig.add_vline(
                x=non_promo_df['price'].iloc[max_rev_idx_non_promo],
                line_dash="dash", line_color="blue",
                annotation_text=f"非促销最优: ¥{non_promo_df['price'].iloc[max_rev_idx_non_promo]:.2f}",
                annotation_font_color="blue",
                row=2, col=2
            )
            
            fig.add_vline(
                x=promo_df['price'].iloc[max_rev_idx_promo],
                line_dash="dash", line_color="orange",
                annotation_text=f"促销最优: ¥{promo_df['price'].iloc[max_rev_idx_promo]:.2f}",
                annotation_font_color="orange",
                row=2, col=2
            )
        else:
            revenue = elasticity_df['price'] * elasticity_df['purchase_probability']
            fig.add_trace(
                go.Scatter(
                    x=elasticity_df['price'],
                    y=revenue,
                    mode='lines',
                    name='预期收入指数',
                    line=dict(color='#2ca02c', width=3)
                ),
                row=2, col=2
            )

            max_rev_idx = np.argmax(revenue)
            fig.add_vline(
                x=elasticity_df['price'].iloc[max_rev_idx],
                line_dash="dash", line_color="green",
                annotation_text=f"最优价格: ¥{elasticity_df['price'].iloc[max_rev_idx]:.2f}",
                row=2, col=2
            )

        fig.update_xaxes(title_text='价格 (元)', row=1, col=1)
        fig.update_xaxes(title_text='价格 (元)', row=1, col=2)
        fig.update_xaxes(title_text='弹性区间', row=2, col=1)
        fig.update_xaxes(title_text='价格 (元)', row=2, col=2)

        fig.update_yaxes(title_text='购买概率', row=1, col=1)
        fig.update_yaxes(title_text='价格弹性系数', row=1, col=2)
        fig.update_yaxes(title_text='样本数', row=2, col=1)
        fig.update_yaxes(title_text='收入指数', row=2, col=2)

        fig.update_layout(
            height=800,
            title_text='价格弹性分析综合图表（促销/非促销期分离）',
            showlegend=True,
            legend=dict(orientation="h", yanchor="bottom", y=-0.15, xanchor="center", x=0.5)
        )

        return fig
    else:
        fig, axes = plt.subplots(2, 2, figsize=(15, 12))

        if has_promo_split:
            axes[0, 0].plot(non_promo_df['price'], non_promo_df['purchase_probability'], 'b-', linewidth=2, label='非促销期')
            axes[0, 0].plot(promo_df['price'], promo_df['purchase_probability'], 'orange', linewidth=2, linestyle='--', label='促销期')
            
            if show_ci and has_ci:
                axes[0, 0].fill_between(non_promo_df['price'], non_promo_df['prob_ci_lower'], non_promo_df['prob_ci_upper'], alpha=0.2, color='blue')
                axes[0, 0].fill_between(promo_df['price'], promo_df['prob_ci_lower'], promo_df['prob_ci_upper'], alpha=0.2, color='orange')
            axes[0, 0].legend()
        else:
            axes[0, 0].plot(elasticity_df['price'], elasticity_df['purchase_probability'], 'b-', linewidth=2)
            if show_ci and has_ci:
                axes[0, 0].fill_between(elasticity_df['price'], elasticity_df['prob_ci_lower'], elasticity_df['prob_ci_upper'], alpha=0.2, color='blue')
        
        axes[0, 0].set_xlabel('价格 (元)')
        axes[0, 0].set_ylabel('购买概率')
        axes[0, 0].set_title('价格-购买概率曲线')

        if has_promo_split:
            axes[0, 1].plot(non_promo_df['price'], non_promo_df['point_elasticity'], 'b-', linewidth=2, label='非促销期')
            axes[0, 1].plot(promo_df['price'], promo_df['point_elasticity'], 'orange', linewidth=2, linestyle='--', label='促销期')
            
            if show_ci and 'elasticity_ci_lower' in non_promo_df.columns:
                axes[0, 1].fill_between(non_promo_df['price'], non_promo_df['elasticity_ci_lower'], non_promo_df['elasticity_ci_upper'], alpha=0.2, color='blue')
                axes[0, 1].fill_between(promo_df['price'], promo_df['elasticity_ci_lower'], promo_df['elasticity_ci_upper'], alpha=0.2, color='orange')
            axes[0, 1].legend()
        else:
            axes[0, 1].plot(elasticity_df['price'], elasticity_df['point_elasticity'], 'orange', linewidth=2)
        
        axes[0, 1].axhline(y=-1, color='r', linestyle='--', label='单位弹性 (ε=-1)')
        axes[0, 1].set_xlabel('价格 (元)')
        axes[0, 1].set_ylabel('价格弹性系数')
        axes[0, 1].set_title('价格-弹性系数曲线')

        elasticity_counts = elasticity_df['elasticity_category'].value_counts()
        colors = ['#d62728', '#ff7f0e', '#2ca02c', '#1f77b4', '#9467bd']
        axes[1, 0].bar(range(len(elasticity_counts)), elasticity_counts.values, color=colors)
        axes[1, 0].set_xticks(range(len(elasticity_counts)))
        axes[1, 0].set_xticklabels(elasticity_counts.index, rotation=45, ha='right')
        axes[1, 0].set_ylabel('样本数')
        axes[1, 0].set_title('弹性分布')

        if has_promo_split:
            revenue_non_promo = non_promo_df['price'] * non_promo_df['purchase_probability']
            revenue_promo = promo_df['price'] * promo_df['purchase_probability']
            
            axes[1, 1].plot(non_promo_df['price'], revenue_non_promo, 'b-', linewidth=2, label='非促销期')
            axes[1, 1].plot(promo_df['price'], revenue_promo, 'orange', linewidth=2, linestyle='--', label='促销期')
            axes[1, 1].legend()
            
            max_rev_idx_non_promo = np.argmax(revenue_non_promo)
            max_rev_idx_promo = np.argmax(revenue_promo)
            
            axes[1, 1].axvline(x=non_promo_df['price'].iloc[max_rev_idx_non_promo], color='b', linestyle='--',
                                label=f'非促销最优: ¥{non_promo_df["price"].iloc[max_rev_idx_non_promo]:.2f}')
            axes[1, 1].axvline(x=promo_df['price'].iloc[max_rev_idx_promo], color='orange', linestyle='--',
                                label=f'促销最优: ¥{promo_df["price"].iloc[max_rev_idx_promo]:.2f}')
        else:
            revenue = elasticity_df['price'] * elasticity_df['purchase_probability']
            axes[1, 1].plot(elasticity_df['price'], revenue, 'g-', linewidth=2)
            max_rev_idx = np.argmax(revenue)
            axes[1, 1].axvline(x=elasticity_df['price'].iloc[max_rev_idx], color='g', linestyle='--',
                                label=f'最优价格: ¥{elasticity_df["price"].iloc[max_rev_idx]:.2f}')
        
        axes[1, 1].set_xlabel('价格 (元)')
        axes[1, 1].set_ylabel('收入指数')
        axes[1, 1].set_title('价格-边际收益曲线')
        axes[1, 1].legend()

        plt.tight_layout()
        return fig


def plot_feature_importance(
    importance_df: pd.DataFrame,
    interactive: bool = True,
    show_ci: bool = True
):
    has_ci = 'bootstrap_ci_lower' in importance_df.columns and 'bootstrap_ci_upper' in importance_df.columns
    
    df_plot = importance_df[importance_df['feature'] != 'const'].copy()
    df_plot = df_plot.sort_values('abs_coeff', ascending=True)

    if interactive:
        fig = go.Figure()

        colors = ['#d62728' if c < 0 else '#2ca02c' for c in df_plot['coefficient']]

        if show_ci and has_ci:
            fig.add_trace(
                go.Bar(
                    y=df_plot['feature'],
                    x=df_plot['coefficient'],
                    orientation='h',
                    marker_color=colors,
                    error_x=dict(
                        type='data',
                        symmetric=False,
                        array=df_plot['bootstrap_ci_upper'] - df_plot['coefficient'],
                        arrayminus=df_plot['coefficient'] - df_plot['bootstrap_ci_lower'],
                        color='gray',
                        thickness=1.5,
                        width=3
                    ),
                    text=df_plot.apply(
                        lambda row: f"系数: {row['coefficient']:.4f}<br>P值: {row['p_value']:.4f}<br>OR: {row['odds_ratio']:.4f}<br>95% CI: [{row.get('bootstrap_ci_lower', 'N/A'):.4f}, {row.get('bootstrap_ci_upper', 'N/A'):.4f}]",
                        axis=1
                    ),
                    hoverinfo='text',
                    name='系数'
                )
            )
        else:
            fig.add_trace(
                go.Bar(
                    y=df_plot['feature'],
                    x=df_plot['coefficient'],
                    orientation='h',
                    marker_color=colors,
                    text=df_plot.apply(
                        lambda row: f"系数: {row['coefficient']:.4f}<br>P值: {row['p_value']:.4f}<br>OR: {row['odds_ratio']:.4f}",
                        axis=1
                    ),
                    hoverinfo='text'
                )
            )

        fig.update_layout(
            title='特征重要性分析 (Logit模型系数)' + ('（Bootstrap 95% CI）' if show_ci and has_ci else ''),
            xaxis_title='回归系数',
            yaxis_title='特征',
            height=500
        )

        return fig
    else:
        fig, ax = plt.subplots(figsize=(12, 8))
        colors = ['#d62728' if c < 0 else '#2ca02c' for c in df_plot['coefficient']]
        y_pos = np.arange(len(df_plot))
        
        ax.barh(y_pos, df_plot['coefficient'], color=colors)
        
        if show_ci and has_ci:
            xerr_lower = df_plot['coefficient'] - df_plot['bootstrap_ci_lower']
            xerr_upper = df_plot['bootstrap_ci_upper'] - df_plot['coefficient']
            ax.errorbar(
                df_plot['coefficient'], y_pos,
                xerr=[xerr_lower.values, xerr_upper.values],
                fmt='none', color='gray', capsize=3
            )
        
        ax.set_yticks(y_pos)
        ax.set_yticklabels(df_plot['feature'])
        ax.set_xlabel('回归系数')
        ax.set_ylabel('特征')
        ax.set_title('特征重要性分析')
        ax.axvline(x=0, color='black', linewidth=0.5)
        plt.tight_layout()
        return fig


def plot_bootstrap_distribution(
    bootstrap_results: Dict,
    interactive: bool = True
):
    all_coeffs = bootstrap_results.get('all_coeffs', None)
    all_elasticities_promo = bootstrap_results.get('all_elasticities_promo', None)
    all_elasticities_non_promo = bootstrap_results.get('all_elasticities_non_promo', None)
    
    if interactive:
        fig = make_subplots(
            rows=1, cols=2,
            subplot_titles=(
                '价格弹性系数Bootstrap分布',
                '促销vs非促销弹性对比'
            )
        )
        
        if all_elasticities_non_promo is not None:
            valid_non_promo = all_elasticities_non_promo[~np.isnan(all_elasticities_non_promo)]
            fig.add_trace(
                go.Histogram(
                    x=valid_non_promo,
                    name='非促销期弹性',
                    opacity=0.7,
                    marker_color='#1f77b4',
                    nbinsx=50,
                    histnorm='probability density'
                ),
                row=1, col=1
            )
            
            ci_non_promo = bootstrap_results.get('elasticity_non_promo_ci', {})
            fig.add_vline(
                x=ci_non_promo.get('mean', np.nanmean(valid_non_promo)),
                line_dash="solid", line_color="blue", line_width=2,
                annotation_text=f"均值: {np.nanmean(valid_non_promo):.3f}",
                annotation_position="top",
                row=1, col=1
            )
            fig.add_vline(
                x=ci_non_promo.get('ci_lower', np.nanpercentile(valid_non_promo, 2.5)),
                line_dash="dash", line_color="blue",
                annotation_text=f"2.5%: {np.nanpercentile(valid_non_promo, 2.5):.3f}",
                row=1, col=1
            )
            fig.add_vline(
                x=ci_non_promo.get('ci_upper', np.nanpercentile(valid_non_promo, 97.5)),
                line_dash="dash", line_color="blue",
                annotation_text=f"97.5%: {np.nanpercentile(valid_non_promo, 97.5):.3f}",
                row=1, col=1
            )
        
        if all_elasticities_promo is not None:
            valid_promo = all_elasticities_promo[~np.isnan(all_elasticities_promo)]
            fig.add_trace(
                go.Histogram(
                    x=valid_promo,
                    name='促销期弹性',
                    opacity=0.6,
                    marker_color='#ff7f0e',
                    nbinsx=50,
                    histnorm='probability density'
                ),
                row=1, col=1
            )
            
            ci_promo = bootstrap_results.get('elasticity_promo_ci', {})
            fig.add_vline(
                x=ci_promo.get('mean', np.nanmean(valid_promo)),
                line_dash="solid", line_color="orange", line_width=2,
                annotation_text=f"促销均值: {np.nanmean(valid_promo):.3f}",
                annotation_position="top",
                row=1, col=1
            )
        
        fig.update_xaxes(title_text='价格弹性系数', row=1, col=1)
        fig.update_yaxes(title_text='概率密度', row=1, col=1)
        
        if all_elasticities_non_promo is not None and all_elasticities_promo is not None:
            valid_non_promo = all_elasticities_non_promo[~np.isnan(all_elasticities_non_promo)]
            valid_promo = all_elasticities_promo[~np.isnan(all_elasticities_promo)]
            
            fig.add_trace(
                go.Box(
                    y=valid_non_promo,
                    name='非促销期',
                    marker_color='#1f77b4',
                    boxmean=True
                ),
                row=1, col=2
            )
            
            fig.add_trace(
                go.Box(
                    y=valid_promo,
                    name='促销期',
                    marker_color='#ff7f0e',
                    boxmean=True
                ),
                row=1, col=2
            )
            
            fig.update_yaxes(title_text='价格弹性系数', row=1, col=2)
        
        fig.update_layout(
            height=500,
            title_text=f'Bootstrap稳健性检验 (N={bootstrap_results.get("n_bootstrap", 0)}, 有效={bootstrap_results.get("n_valid", 0)})',
            barmode='overlay'
        )
        
        return fig
    else:
        fig, axes = plt.subplots(1, 2, figsize=(15, 6))
        
        if all_elasticities_non_promo is not None:
            valid_non_promo = all_elasticities_non_promo[~np.isnan(all_elasticities_non_promo)]
            axes[0].hist(valid_non_promo, bins=50, alpha=0.7, density=True, color='#1f77b4', label='非促销期')
            
            ci_non_promo = bootstrap_results.get('elasticity_non_promo_ci', {})
            axes[0].axvline(x=ci_non_promo.get('mean', np.nanmean(valid_non_promo)), color='blue', linewidth=2, label='均值')
            axes[0].axvline(x=ci_non_promo.get('ci_lower', np.nanpercentile(valid_non_promo, 2.5)), color='blue', linestyle='--', label='95% CI')
            axes[0].axvline(x=ci_non_promo.get('ci_upper', np.nanpercentile(valid_non_promo, 97.5)), color='blue', linestyle='--')
        
        if all_elasticities_promo is not None:
            valid_promo = all_elasticities_promo[~np.isnan(all_elasticities_promo)]
            axes[0].hist(valid_promo, bins=50, alpha=0.6, density=True, color='#ff7f0e', label='促销期')
            
            ci_promo = bootstrap_results.get('elasticity_promo_ci', {})
            axes[0].axvline(x=ci_promo.get('mean', np.nanmean(valid_promo)), color='orange', linewidth=2, label='促销均值')
        
        axes[0].set_xlabel('价格弹性系数')
        axes[0].set_ylabel('概率密度')
        axes[0].set_title('Bootstrap弹性系数分布')
        axes[0].legend()
        
        if all_elasticities_non_promo is not None and all_elasticities_promo is not None:
            valid_non_promo = all_elasticities_non_promo[~np.isnan(all_elasticities_non_promo)]
            valid_promo = all_elasticities_promo[~np.isnan(all_elasticities_promo)]
            
            axes[1].boxplot([valid_non_promo, valid_promo], labels=['非促销期', '促销期'], showmeans=True)
            axes[1].set_ylabel('价格弹性系数')
            axes[1].set_title('促销vs非促销弹性箱线图')
        
        plt.tight_layout()
        return fig


def plot_post_promotion_effect(
    post_promo_data: pd.DataFrame,
    interactive: bool = True
):
    if interactive:
        fig = make_subplots(
            rows=2, cols=1,
            subplot_titles=(
                '促销后需求回落趋势',
                '促销后逐日利润损失'
            ),
            shared_xaxes=True,
            vertical_spacing=0.08
        )
        
        fig.add_trace(
            go.Scatter(
                x=post_promo_data['day'],
                y=post_promo_data['normal_demand'],
                mode='lines',
                name='正常需求水平',
                line=dict(color='#1f77b4', width=2, dash='dash')
            ),
            row=1, col=1
        )
        
        fig.add_trace(
            go.Scatter(
                x=post_promo_data['day'],
                y=post_promo_data['adjusted_demand'],
                mode='lines+markers',
                name='实际预期需求',
                line=dict(color='#ff7f0e', width=3),
                marker=dict(size=6)
            ),
            row=1, col=1
        )
        
        fig.add_trace(
            go.Scatter(
                x=post_promo_data['day'],
                y=post_promo_data['decay_factor'] * 100,
                mode='lines',
                name='需求恢复因子 (%)',
                line=dict(color='#2ca02c', width=2),
                yaxis='y2'
            ),
            row=1, col=1
        )
        
        fig.add_trace(
            go.Bar(
                x=post_promo_data['day'],
                y=post_promo_data['profit_lost'],
                name='利润损失',
                marker_color='#d62728',
                opacity=0.7
            ),
            row=2, col=1
        )
        
        cumulative_loss = post_promo_data['profit_lost'].cumsum()
        fig.add_trace(
            go.Scatter(
                x=post_promo_data['day'],
                y=cumulative_loss,
                mode='lines',
                name='累计利润损失',
                line=dict(color='#d62728', width=3),
                yaxis='y2'
            ),
            row=2, col=1
        )
        
        fig.update_layout(
            height=700,
            title_text='促销延后效应分析（需求回落与利润损失）',
            showlegend=True
        )
        
        fig.update_xaxes(title_text='促销后天数', row=1, col=1)
        fig.update_xaxes(title_text='促销后天数', row=2, col=1)
        
        fig.update_yaxes(title_text='需求数量', row=1, col=1, secondary_y=False)
        fig.update_yaxes(title_text='恢复因子 (%)', row=1, col=1, secondary_y=True, range=[0, 100])
        fig.update_yaxes(title_text='当日利润损失 (元)', row=2, col=1, secondary_y=False)
        fig.update_yaxes(title_text='累计利润损失 (元)', row=2, col=1, secondary_y=True)
        
        return fig
    else:
        fig, axes = plt.subplots(2, 1, figsize=(14, 10), sharex=True)
        
        axes[0].plot(post_promo_data['day'], post_promo_data['normal_demand'], 'b--', linewidth=2, label='正常需求水平')
        axes[0].plot(post_promo_data['day'], post_promo_data['adjusted_demand'], 'orange', linewidth=3, marker='o', label='实际预期需求')
        axes[0].set_ylabel('需求数量')
        axes[0].set_title('促销后需求回落趋势')
        axes[0].legend()
        
        ax0_twin = axes[0].twinx()
        ax0_twin.plot(post_promo_data['day'], post_promo_data['decay_factor'] * 100, 'g-', linewidth=2, alpha=0.7, label='恢复因子')
        ax0_twin.set_ylabel('恢复因子 (%)')
        ax0_twin.set_ylim(0, 100)
        
        axes[1].bar(post_promo_data['day'], post_promo_data['profit_lost'], color='#d62728', alpha=0.7, label='当日利润损失')
        axes[1].set_xlabel('促销后天数')
        axes[1].set_ylabel('当日利润损失 (元)')
        axes[1].set_title('促销后逐日利润损失')
        
        ax1_twin = axes[1].twinx()
        cumulative_loss = post_promo_data['profit_lost'].cumsum()
        ax1_twin.plot(post_promo_data['day'], cumulative_loss, 'r-', linewidth=3, label='累计损失')
        ax1_twin.set_ylabel('累计利润损失 (元)')
        
        plt.tight_layout()
        return fig


def plot_sales_impact(
    impact_data: Dict,
    interactive: bool = True
):
    has_ci = 'predicted_sales_ci' in impact_data
    
    if interactive:
        fig = make_subplots(
            rows=1, cols=2,
            subplot_titles=('销量变化预测', '收入变化预测'),
            specs=[[{'type': 'indicator'}, {'type': 'indicator'}]]
        )

        sales_change_pct = impact_data['sales_change_pct'] * 100
        revenue_change_pct = impact_data['revenue_change_pct'] * 100

        sales_title = f"预测销量<br>(弹性系数: {impact_data['average_elasticity']:.2f}"
        if 'elasticity_ci' in impact_data:
            ci_low, ci_high = impact_data['elasticity_ci']
            sales_title += f"<br>95% CI: [{ci_low:.2f}, {ci_high:.2f}])"
        else:
            sales_title += ")"

        fig.add_trace(
            go.Indicator(
                mode="number+delta",
                value=impact_data['predicted_sales'],
                delta={'reference': impact_data['base_sales_estimate'],
                       'relative': True,
                       'valueformat': '.1%',
                       'increasing': {'color': '#2ca02c'},
                       'decreasing': {'color': '#d62728'}},
                title={'text': sales_title},
                number={'valueformat': ',.0f'}
            ),
            row=1, col=1
        )

        fig.add_trace(
            go.Indicator(
                mode="number+delta",
                value=impact_data['predicted_revenue'],
                delta={'reference': impact_data['base_revenue_estimate'],
                       'relative': True,
                       'valueformat': '.1%',
                       'increasing': {'color': '#2ca02c'},
                       'decreasing': {'color': '#d62728'}},
                title={'text': '预测收入' + ('<br>95% CI: [¥{:,.0f}, ¥{:,.0f}]'.format(
                    impact_data['predicted_revenue_ci'][0],
                    impact_data['predicted_revenue_ci'][1]
                ) if has_ci else '')},
                number={'prefix': '¥', 'valueformat': ',,.0f'}
            ),
            row=1, col=2
        )

        fig.update_layout(
            height=400,
            title_text=f"价格调整 {impact_data['price_change_pct']*100:+.1f}% 影响分析"
        )

        return fig
    else:
        fig, axes = plt.subplots(1, 2, figsize=(14, 5))

        categories = ['基准价格', '调整后价格']
        sales_values = [impact_data['base_sales_estimate'], impact_data['predicted_sales']]
        revenue_values = [impact_data['base_revenue_estimate'], impact_data['predicted_revenue']]

        sales_colors = ['#1f77b4', '#ff7f0e']
        axes[0].bar(categories, sales_values, color=sales_colors)
        
        if has_ci:
            sales_ci = impact_data['predicted_sales_ci']
            axes[0].errorbar(1, impact_data['predicted_sales'], 
                           yerr=[[impact_data['predicted_sales'] - sales_ci[0]], [sales_ci[1] - impact_data['predicted_sales']]],
                           fmt='none', color='black', capsize=10)
        
        axes[0].set_ylabel('销售数量')
        axes[0].set_title(f'销量变化预测\n变化: {impact_data["sales_change_pct"]*100:+.1f}%')
        for i, v in enumerate(sales_values):
            axes[0].text(i, v + max(sales_values)*0.01, f'{v:,.0f}', ha='center')

        revenue_colors = ['#1f77b4', '#ff7f0e']
        axes[1].bar(categories, revenue_values, color=revenue_colors)
        
        if has_ci:
            rev_ci = impact_data['predicted_revenue_ci']
            axes[1].errorbar(1, impact_data['predicted_revenue'],
                           yerr=[[impact_data['predicted_revenue'] - rev_ci[0]], [rev_ci[1] - impact_data['predicted_revenue']]],
                           fmt='none', color='black', capsize=10)
        
        axes[1].set_ylabel('收入 (元)')
        axes[1].set_title(f'收入变化预测\n变化: {impact_data["revenue_change_pct"]*100:+.1f}%')
        for i, v in enumerate(revenue_values):
            axes[1].text(i, v + max(revenue_values)*0.01, f'¥{v:,.0f}', ha='center')

        plt.tight_layout()
        return fig


def plot_promotion_simulation(
    simulation_results: pd.DataFrame,
    interactive: bool = True,
    include_net_profit: bool = True
):
    profit_col = 'net_profit_change' if include_net_profit and 'net_profit_change' in simulation_results.columns else 'profit_change'
    
    if interactive:
        fig = make_subplots(
            rows=2, cols=2,
            subplot_titles=(
                '折扣力度 vs 销量提升',
                '折扣力度 vs 收入/利润变化',
                '促销周期 vs 累计销量',
                '促销策略对比 (考虑延后效应)'
            ),
            vertical_spacing=0.15
        )

        discount_groups = simulation_results.groupby('discount_pct').agg({
            'sales_lift_pct': 'mean',
            'revenue_change_pct': 'mean',
            profit_col: 'mean'
        }).reset_index()

        fig.add_trace(
            go.Scatter(
                x=discount_groups['discount_pct'] * 100,
                y=discount_groups['sales_lift_pct'] * 100,
                mode='lines+markers',
                name='销量提升率',
                line=dict(color='#1f77b4', width=3),
                marker=dict(size=10)
            ),
            row=1, col=1
        )

        fig.add_trace(
            go.Scatter(
                x=discount_groups['discount_pct'] * 100,
                y=discount_groups['revenue_change_pct'] * 100,
                mode='lines+markers',
                name='收入变化率',
                line=dict(color='#ff7f0e', width=3),
                marker=dict(size=10)
            ),
            row=1, col=2
        )

        fig.add_trace(
            go.Scatter(
                x=discount_groups['discount_pct'] * 100,
                y=discount_groups[profit_col],
                mode='lines+markers',
                name='净利润变化',
                line=dict(color='#2ca02c', width=3),
                marker=dict(size=10)
            ),
            row=1, col=2
        )

        fig.add_hline(y=0, line_dash="dash", line_color="red", row=1, col=2)

        duration_groups = simulation_results.groupby('duration_days').agg({
            'cumulative_sales': 'mean',
            'post_promo_loss': 'mean'
        }).reset_index()

        fig.add_trace(
            go.Bar(
                x=duration_groups['duration_days'],
                y=duration_groups['cumulative_sales'],
                name='累计销量',
                marker_color='#1f77b4',
                offsetgroup=0
            ),
            row=2, col=1
        )

        if 'post_promo_loss' in duration_groups.columns:
            fig.add_trace(
                go.Bar(
                    x=duration_groups['duration_days'],
                    y=duration_groups['post_promo_loss'],
                    name='延后损失',
                    marker_color='#d62728',
                    offsetgroup=1
                ),
                row=2, col=1
            )

        strategy_groups = simulation_results.groupby('strategy').agg({
            'roi': 'mean',
            profit_col: 'mean'
        }).reset_index().sort_values(profit_col, ascending=False)

        fig.add_trace(
            go.Bar(
                x=strategy_groups['strategy'],
                y=strategy_groups[profit_col],
                name='净利润变化',
                marker_color=['#d62728' if r < 0 else '#2ca02c' for r in strategy_groups[profit_col]],
                offsetgroup=0
            ),
            row=2, col=2
        )

        fig.add_trace(
            go.Scatter(
                x=strategy_groups['strategy'],
                y=strategy_groups['roi'],
                mode='markers',
                name='ROI',
                marker=dict(color='#ff7f0e', size=12, symbol='diamond'),
                yaxis='y2'
            ),
            row=2, col=2
        )

        fig.update_xaxes(title_text='折扣力度 (%)', row=1, col=1)
        fig.update_xaxes(title_text='折扣力度 (%)', row=1, col=2)
        fig.update_xaxes(title_text='促销周期 (天)', row=2, col=1)
        fig.update_xaxes(title_text='促销策略', row=2, col=2)

        fig.update_yaxes(title_text='销量提升 (%)', row=1, col=1)
        fig.update_yaxes(title_text='变化率 (%) / 利润 (元)', row=1, col=2)
        fig.update_yaxes(title_text='销量 / 损失', row=2, col=1)
        fig.update_yaxes(title_text='净利润变化 (元)', row=2, col=2, secondary_y=False)
        fig.update_yaxes(title_text='ROI', row=2, col=2, secondary_y=True)

        fig.update_layout(
            height=800,
            title_text='促销模拟分析' + ('（含延后效应）' if include_net_profit else ''),
            showlegend=True,
            legend=dict(orientation="h", yanchor="bottom", y=-0.15, xanchor="center", x=0.5)
        )

        return fig
    else:
        fig, axes = plt.subplots(2, 2, figsize=(15, 12))

        discount_groups = simulation_results.groupby('discount_pct').agg({
            'sales_lift_pct': 'mean',
            'revenue_change_pct': 'mean',
            profit_col: 'mean'
        }).reset_index()

        axes[0, 0].plot(discount_groups['discount_pct'] * 100,
                        discount_groups['sales_lift_pct'] * 100,
                        'b-o', linewidth=2, markersize=8)
        axes[0, 0].set_xlabel('折扣力度 (%)')
        axes[0, 0].set_ylabel('销量提升 (%)')
        axes[0, 0].set_title('折扣力度 vs 销量提升')

        axes[0, 1].plot(discount_groups['discount_pct'] * 100,
                        discount_groups['revenue_change_pct'] * 100,
                        'orange', linewidth=2, marker='o', markersize=8, label='收入变化')
        axes[0, 1].plot(discount_groups['discount_pct'] * 100,
                        discount_groups[profit_col],
                        'g-', linewidth=2, marker='s', markersize=8, label='净利润变化')
        axes[0, 1].axhline(y=0, color='r', linestyle='--')
        axes[0, 1].set_xlabel('折扣力度 (%)')
        axes[0, 1].set_ylabel('变化率 (%) / 利润 (元)')
        axes[0, 1].set_title('折扣力度 vs 收入/利润变化')
        axes[0, 1].legend()

        duration_groups = simulation_results.groupby('duration_days').agg({
            'cumulative_sales': 'mean',
            'post_promo_loss': 'mean'
        }).reset_index()

        x = np.arange(len(duration_groups))
        width = 0.35
        axes[1, 0].bar(x - width/2, duration_groups['cumulative_sales'], width, label='累计销量', color='#1f77b4')
        if 'post_promo_loss' in duration_groups.columns:
            axes[1, 0].bar(x + width/2, duration_groups['post_promo_loss'], width, label='延后损失', color='#d62728')
        axes[1, 0].set_xlabel('促销周期 (天)')
        axes[1, 0].set_ylabel('销量 / 损失')
        axes[1, 0].set_title('促销周期 vs 累计销量与延后损失')
        axes[1, 0].set_xticks(x)
        axes[1, 0].set_xticklabels(duration_groups['duration_days'])
        axes[1, 0].legend()

        strategy_groups = simulation_results.groupby('strategy').agg({
            'roi': 'mean',
            profit_col: 'mean'
        }).reset_index().sort_values(profit_col, ascending=False)

        colors = ['#d62728' if r < 0 else '#2ca02c' for r in strategy_groups[profit_col]]
        axes[1, 1].bar(strategy_groups['strategy'],
                       strategy_groups[profit_col],
                       color=colors, label='净利润变化')
        axes[1, 1].set_xlabel('促销策略')
        axes[1, 1].set_ylabel('净利润变化 (元)')
        axes[1, 1].set_title('促销策略对比')
        axes[1, 1].tick_params(axis='x', rotation=45)
        axes[1, 1].axhline(y=0, color='black', linewidth=0.5)
        axes[1, 1].legend()

        ax_twin = axes[1, 1].twinx()
        ax_twin.plot(strategy_groups['strategy'], strategy_groups['roi'], 
                    'orange', linewidth=2, marker='D', markersize=8, label='ROI')
        ax_twin.set_ylabel('ROI')
        ax_twin.legend(loc='upper right')

        plt.tight_layout()
        return fig


def plot_promotion_timeline(
    timeline_df: pd.DataFrame,
    interactive: bool = True
):
    if interactive:
        fig = make_subplots(
            rows=3, cols=1,
            subplot_titles=('促销期间销量走势（含延后效应）', '促销期间利润走势', '销量对比：实际vs正常水平'),
            shared_xaxes=True,
            vertical_spacing=0.05
        )

        colors = {'促销前': '#ff7f0e', '促销中': '#2ca02c', '促销后': '#1f77b4'}
        for period in ['促销前', '促销中', '促销后']:
            mask = timeline_df['period'] == period
            fig.add_trace(
                go.Scatter(
                    x=timeline_df[mask]['day'],
                    y=timeline_df[mask]['demand'],
                    mode='lines',
                    name=f'{period}需求',
                    line=dict(color=colors[period], width=3),
                    fill='tozeroy',
                    fillcolor=f'rgba{tuple(int(colors[period].lstrip("#")[i:i+2], 16) for i in (0, 2, 4)) + (0.2,)}'
                ),
                row=1, col=1
            )

        fig.add_trace(
            go.Scatter(
                x=timeline_df['day'],
                y=timeline_df['normal_demand'],
                mode='lines',
                name='正常需求水平',
                line=dict(color='gray', width=2, dash='dash')
            ),
            row=1, col=1
        )

        fig.add_trace(
            go.Scatter(
                x=timeline_df['day'],
                y=timeline_df['profit'],
                mode='lines',
                name='实际利润',
                line=dict(color='#2ca02c', width=3)
            ),
            row=2, col=1
        )

        fig.add_trace(
            go.Scatter(
                x=timeline_df['day'],
                y=timeline_df['normal_profit'],
                mode='lines',
                name='正常利润',
                line=dict(color='gray', width=2, dash='dash')
            ),
            row=2, col=1
        )

        fig.add_hline(y=0, line_dash="dash", line_color="red", row=2, col=1)

        fig.add_trace(
            go.Bar(
                x=timeline_df['day'],
                y=timeline_df['demand_lift_vs_normal'],
                name='销量差',
                marker_color=['#2ca02c' if v > 0 else '#d62728' for v in timeline_df['demand_lift_vs_normal']]
            ),
            row=3, col=1
        )

        fig.add_hline(y=0, line_dash="dash", line_color="black", row=3, col=1)

        fig.update_layout(
            height=900,
            title_text='促销全周期时间线分析（含延后效应）'
        )

        fig.update_xaxes(title_text='天数', row=3, col=1)

        fig.update_yaxes(title_text='需求数量', row=1, col=1)
        fig.update_yaxes(title_text='利润 (元)', row=2, col=1)
        fig.update_yaxes(title_text='销量差 (实际-正常)', row=3, col=1)

        return fig
    else:
        fig, axes = plt.subplots(3, 1, figsize=(14, 12), sharex=True)

        colors = {'促销前': '#ff7f0e', '促销中': '#2ca02c', '促销后': '#1f77b4'}
        for period in ['促销前', '促销中', '促销后']:
            mask = timeline_df['period'] == period
            axes[0].plot(timeline_df[mask]['day'], timeline_df[mask]['demand'], 
                        color=colors[period], linewidth=3, label=f'{period}需求')
        
        axes[0].plot(timeline_df['day'], timeline_df['normal_demand'], 
                    'gray', linestyle='--', linewidth=2, label='正常需求')
        axes[0].set_ylabel('需求数量')
        axes[0].set_title('促销期间销量走势（含延后效应）')
        axes[0].legend()

        axes[1].plot(timeline_df['day'], timeline_df['profit'], 'g-', linewidth=3, label='实际利润')
        axes[1].plot(timeline_df['day'], timeline_df['normal_profit'], 'gray', linestyle='--', linewidth=2, label='正常利润')
        axes[1].axhline(y=0, color='r', linestyle='--')
        axes[1].set_ylabel('利润 (元)')
        axes[1].set_title('促销期间利润走势')
        axes[1].legend()

        bar_colors = ['#2ca02c' if v > 0 else '#d62728' for v in timeline_df['demand_lift_vs_normal']]
        axes[2].bar(timeline_df['day'], timeline_df['demand_lift_vs_normal'], color=bar_colors)
        axes[2].axhline(y=0, color='black', linewidth=0.5)
        axes[2].set_xlabel('天数')
        axes[2].set_ylabel('销量差 (实际-正常)')
        axes[2].set_title('销量对比：实际vs正常水平')

        plt.tight_layout()
        return fig


def plot_time_series(
    df: pd.DataFrame,
    interactive: bool = True
):
    if interactive:
        fig = make_subplots(
            rows=3, cols=1,
            subplot_titles=('价格走势', '销量走势', '收入走势'),
            shared_xaxes=True,
            vertical_spacing=0.05
        )

        fig.add_trace(
            go.Scatter(
                x=df['date'],
                y=df['effective_price'],
                mode='lines',
                name='实际价格',
                line=dict(color='#1f77b4')
            ),
            row=1, col=1
        )

        promo_dates = df[df['is_promotion'] == 1]['date']
        for date in promo_dates:
            fig.add_vline(
                x=date, line_dash="dash", line_color="red", opacity=0.3,
                row=1, col=1
            )

        fig.add_trace(
            go.Scatter(
                x=df['date'],
                y=df['sales_quantity'],
                mode='lines',
                name='销量',
                line=dict(color='#2ca02c')
            ),
            row=2, col=1
        )

        fig.add_trace(
            go.Scatter(
                x=df['date'],
                y=df['revenue'],
                mode='lines',
                name='收入',
                line=dict(color='#ff7f0e')
            ),
            row=3, col=1
        )

        fig.update_layout(
            height=800,
            title_text='历史数据时间序列',
            showlegend=False
        )

        return fig
    else:
        fig, axes = plt.subplots(3, 1, figsize=(14, 10), sharex=True)

        axes[0].plot(df['date'], df['effective_price'], 'b-', linewidth=1.5)
        axes[0].set_ylabel('价格 (元)')
        axes[0].set_title('价格走势')

        promo_dates = df[df['is_promotion'] == 1]['date']
        for date in promo_dates:
            axes[0].axvline(x=date, color='r', linestyle='--', alpha=0.3)

        axes[1].plot(df['date'], df['sales_quantity'], 'g-', linewidth=1.5)
        axes[1].set_ylabel('销售数量')
        axes[1].set_title('销量走势')

        axes[2].plot(df['date'], df['revenue'], 'orange', linewidth=1.5)
        axes[2].set_ylabel('收入 (元)')
        axes[2].set_xlabel('日期')
        axes[2].set_title('收入走势')

        plt.tight_layout()
        return fig


def plot_heatmap_correlation(
    df: pd.DataFrame,
    interactive: bool = True
):
    corr_cols = [
        'effective_price', 'sales_quantity', 'revenue',
        'is_promotion', 'advertising_spend',
        'competitor_price', 'temperature'
    ]
    corr_matrix = df[corr_cols].corr()

    if interactive:
        fig = go.Figure(
            data=go.Heatmap(
                z=corr_matrix.values,
                x=corr_matrix.columns,
                y=corr_matrix.columns,
                text=corr_matrix.values.round(3),
                texttemplate="%{text}",
                textfont={"size": 10},
                colorscale='RdBu_r',
                zmid=0,
                zmin=-1,
                zmax=1
            )
        )

        fig.update_layout(
            title='变量相关性热力图',
            height=600,
            xaxis_title='',
            yaxis_title=''
        )

        return fig
    else:
        fig, ax = plt.subplots(figsize=(10, 8))
        sns.heatmap(corr_matrix, annot=True, cmap='RdBu_r', center=0,
                    vmin=-1, vmax=1, fmt='.3f', ax=ax)
        ax.set_title('变量相关性热力图')
        plt.tight_layout()
        return fig


def plot_cross_elasticity_heatmap(
    heatmap_data: Dict,
    interactive: bool = True
):
    z_data = heatmap_data.get('z', [])
    text_data = heatmap_data.get('text', [])
    x_labels = heatmap_data.get('x_labels', [])
    y_labels = heatmap_data.get('y_labels', [])
    categories = heatmap_data.get('categories', [])
    
    if interactive:
        fig = go.Figure(data=go.Heatmap(
            z=z_data,
            x=x_labels,
            y=y_labels,
            text=text_data,
            texttemplate='%{text}',
            textfont={"size": 10},
            hovertemplate='影响商品: %{y}<br>调价商品: %{x}<br>交叉弹性: %{z:.3f}<extra></extra>',
            colorscale='RdBu_r',
            zmid=0,
            zmin=-1,
            zmax=1,
            colorbar=dict(title='交叉弹性系数')
        ))
        
        unique_cats = list(dict.fromkeys(categories))
        if len(unique_cats) > 1:
            shapes = []
            current_idx = 0
            for cat in unique_cats:
                count = categories.count(cat)
                shapes.append(dict(
                    type="rect",
                    xref="x",
                    yref="y",
                    x0=current_idx - 0.5,
                    y0=current_idx - 0.5,
                    x1=current_idx + count - 0.5,
                    y1=current_idx + count - 0.5,
                    line=dict(color="black", width=2),
                    fillcolor="rgba(0,0,0,0)"
                ))
                current_idx += count
            
            fig.update_layout(shapes=shapes)
        
        fig.update_layout(
            title='品类间交叉弹性热力图',
            xaxis_title='调价商品（价格变动）',
            yaxis_title='受影响商品（销量变化）',
            height=600,
            width=700
        )
        
        return fig
    else:
        fig, ax = plt.subplots(figsize=(10, 8))
        sns.heatmap(z_data, annot=True, cmap='RdBu_r', center=0,
                    vmin=-1, vmax=1, fmt='.3f', ax=ax,
                    xticklabels=x_labels, yticklabels=y_labels)
        ax.set_title('品类间交叉弹性热力图')
        ax.set_xlabel('调价商品（价格变动）')
        ax.set_ylabel('受影响商品（销量变化）')
        plt.tight_layout()
        return fig


def plot_cross_elasticity_impact(
    impact_df: pd.DataFrame,
    interactive: bool = True
):
    df_plot = impact_df.copy()
    df_plot = df_plot.sort_values('sales_change_pct', ascending=True)
    
    colors = ['#d62728' if x < 0 else '#2ca02c' for x in df_plot['sales_change_pct']]
    
    if interactive:
        fig = go.Figure()
        
        fig.add_trace(go.Bar(
            x=df_plot['sales_change_pct'] * 100,
            y=df_plot['product_name'],
            orientation='h',
            marker_color=colors,
            text=df_plot['impact_type'],
            hovertemplate='<b>%{y}</b><br>销量变化: %{x:.1f}%<br>影响类型: %{text}<extra></extra>',
            error_x=dict(
                type='data',
                symmetric=False,
                array=(df_plot['sales_change_pct_upper'] - df_plot['sales_change_pct']) * 100,
                arrayminus=(df_plot['sales_change_pct'] - df_plot['sales_change_pct_lower']) * 100,
                color='gray'
            )
        ))
        
        fig.add_vline(x=0, line_dash="dash", line_color="black")
        
        fig.update_layout(
            title='调价对各商品销量影响',
            xaxis_title='预计销量变化 (%)',
            yaxis_title='商品名称',
            height=500,
            showlegend=False
        )
        
        return fig
    else:
        fig, ax = plt.subplots(figsize=(10, 6))
        y_pos = np.arange(len(df_plot))
        ax.barh(y_pos, df_plot['sales_change_pct'] * 100, color=colors)
        ax.set_yticks(y_pos)
        ax.set_yticklabels(df_plot['product_name'])
        ax.set_xlabel('预计销量变化 (%)')
        ax.set_title('调价对各商品销量影响')
        ax.axvline(x=0, color='black', linewidth=0.5)
        plt.tight_layout()
        return fig


def plot_dynamic_pricing_comparison(
    comparison_df: pd.DataFrame,
    all_results: Optional[Dict] = None,
    interactive: bool = True
):
    if interactive:
        fig = make_subplots(
            rows=1, cols=2,
            subplot_titles=('不同策略收益对比', '策略累计利润趋势'),
            specs=[[{'type': 'bar'}, {'type': 'xy'}]]
        )
        
        colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd']
        
        for i, (_, row) in enumerate(comparison_df.iterrows()):
            fig.add_trace(
                go.Bar(
                    name=row['description'],
                    x=['总收入', '总利润', '考虑交叉影响收入'],
                    y=[row['total_revenue'], row['total_profit'], row['net_revenue']],
                    text=[f"{row['total_revenue']/10000:.1f}万", 
                          f"{row['total_profit']/10000:.1f}万",
                          f"{row['net_revenue']/10000:.1f}万"],
                    textposition='auto',
                    marker_color=colors[i % len(colors)],
                    hovertemplate=f'<b>{row["description"]}</b><br>%{{x}}: %{{y:,.0f}}元<extra></extra>'
                ),
                row=1, col=1
            )
        
        if all_results is not None:
            for i, (strategy_key, result) in enumerate(all_results.items()):
                sim_data = result['simulation_data']
                cumulative_profit = sim_data['profit'].cumsum()
                fig.add_trace(
                    go.Scatter(
                        x=sim_data['day'],
                        y=cumulative_profit,
                        name=result['strategy'].strategy_type.value,
                        line=dict(color=colors[i % len(colors)], width=2),
                        hovertemplate='第%{x}天<br>累计利润: %{y:,.0f}元<extra></extra>'
                    ),
                    row=1, col=2
                )
        
        fig.update_layout(
            title='动态定价策略对比分析',
            height=550,
            barmode='group'
        )
        
        return fig
    else:
        fig, axes = plt.subplots(1, 2, figsize=(14, 6))
        
        x = np.arange(len(comparison_df))
        width = 0.25
        
        axes[0].bar(x - width, comparison_df['total_revenue'], width, label='总收入')
        axes[0].bar(x, comparison_df['total_profit'], width, label='总利润')
        axes[0].bar(x + width, comparison_df['net_revenue'], width, label='含交叉影响')
        axes[0].set_ylabel('金额 (元)')
        axes[0].set_title('不同策略收益对比')
        axes[0].set_xticks(x)
        axes[0].set_xticklabels(comparison_df['description'], rotation=45, ha='right')
        axes[0].legend()
        
        if all_results is not None:
            colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd']
            for i, (strategy_key, result) in enumerate(all_results.items()):
                sim_data = result['simulation_data']
                cumulative_profit = sim_data['profit'].cumsum()
                axes[1].plot(sim_data['day'], cumulative_profit, 
                            label=result['strategy'].strategy_type.value,
                            color=colors[i % len(colors)], linewidth=2)
            axes[1].set_xlabel('模拟天数')
            axes[1].set_ylabel('累计利润 (元)')
            axes[1].set_title('策略累计利润趋势')
            axes[1].legend()
        
        plt.tight_layout()
        return fig


def plot_pricing_timeline(
    simulation_data: pd.DataFrame,
    interactive: bool = True
):
    if interactive:
        fig = make_subplots(
            rows=3, cols=1,
            shared_xaxes=True,
            vertical_spacing=0.05,
            subplot_titles=('价格变化趋势', '销量预测', '每日利润')
        )
        
        fig.add_trace(
            go.Scatter(
                x=simulation_data['date'],
                y=simulation_data['price'],
                mode='lines',
                name='定价',
                line=dict(color='#1f77b4', width=2),
                fill='tozeroy'
            ),
            row=1, col=1
        )
        
        fig.add_trace(
            go.Scatter(
                x=simulation_data['date'],
                y=simulation_data['competitor_price'],
                mode='lines',
                name='竞品价格',
                line=dict(color='#ff7f0e', width=2, dash='dash')
            ),
            row=1, col=1
        )
        
        fig.add_trace(
            go.Bar(
                x=simulation_data['date'],
                y=simulation_data['predicted_sales'],
                name='预测销量',
                marker_color='#2ca02c',
                opacity=0.7
            ),
            row=2, col=1
        )
        
        fig.add_trace(
            go.Scatter(
                x=simulation_data['date'],
                y=simulation_data['base_sales'],
                mode='lines',
                name='基准销量',
                line=dict(color='gray', dash='dash')
            ),
            row=2, col=1
        )
        
        colors = ['#d62728' if p < 0 else '#2ca02c' for p in simulation_data['profit']]
        fig.add_trace(
            go.Bar(
                x=simulation_data['date'],
                y=simulation_data['profit'],
                name='每日利润',
                marker_color=colors,
                opacity=0.8
            ),
            row=3, col=1
        )
        
        fig.add_hline(y=0, line_dash="dash", line_color="black", row=3, col=1)
        
        fig.update_layout(
            title='动态定价模拟时间线',
            height=700,
            showlegend=True
        )
        
        return fig
    else:
        fig, axes = plt.subplots(3, 1, figsize=(12, 10), sharex=True)
        
        axes[0].plot(simulation_data['date'], simulation_data['price'], 
                    label='定价', color='#1f77b4', linewidth=2)
        axes[0].plot(simulation_data['date'], simulation_data['competitor_price'],
                    label='竞品价格', color='#ff7f0e', linestyle='--', linewidth=2)
        axes[0].set_ylabel('价格 (元)')
        axes[0].set_title('价格变化趋势')
        axes[0].legend()
        
        axes[1].bar(simulation_data['date'], simulation_data['predicted_sales'],
                   alpha=0.7, color='#2ca02c', label='预测销量')
        axes[1].plot(simulation_data['date'], simulation_data['base_sales'],
                    color='gray', linestyle='--', label='基准销量')
        axes[1].set_ylabel('销量')
        axes[1].set_title('销量预测')
        axes[1].legend()
        
        colors = ['#d62728' if p < 0 else '#2ca02c' for p in simulation_data['profit']]
        axes[2].bar(simulation_data['date'], simulation_data['profit'],
                   color=colors, alpha=0.8, label='每日利润')
        axes[2].axhline(y=0, color='black', linestyle='--', linewidth=0.5)
        axes[2].set_xlabel('日期')
        axes[2].set_ylabel('利润 (元)')
        axes[2].set_title('每日利润')
        axes[2].legend()
        
        plt.tight_layout()
        return fig


def plot_price_thresholds(
    detector_results: Dict,
    price_segments: pd.DataFrame,
    df: pd.DataFrame,
    interactive: bool = True
):
    thresholds = detector_results.get('thresholds', []) if 'thresholds' in detector_results else []
    threshold_prices = [t['threshold_price'] for t in thresholds]
    
    if interactive:
        fig = make_subplots(
            rows=2, cols=1,
            shared_xaxes=True,
            vertical_spacing=0.05,
            subplot_titles=('价格-销量散点图与阈值检测', '价格区间弹性对比')
        )
        
        fig.add_trace(
            go.Scatter(
                x=df['effective_price'],
                y=df['sales_quantity'],
                mode='markers',
                name='历史数据',
                marker=dict(
                    color=df['is_promotion'],
                    colorscale='Viridis',
                    size=8,
                    opacity=0.6
                ),
                hovertemplate='价格: %{x:.2f}元<br>销量: %{y}<extra></extra>'
            ),
            row=1, col=1
        )
        
        for i, threshold in enumerate(thresholds):
            price = threshold['threshold_price']
            conf = threshold.get('confidence', 0.5)
            methods = ','.join(threshold.get('detection_methods', []))
            fig.add_vline(
                x=price,
                line_dash="dash",
                line_color="red",
                opacity=0.3 + conf * 0.5,
                annotation_text=f"{price:.0f}元 ({conf:.0%})",
                annotation_position="top",
                row=1, col=1
            )
        
        segment_data = detector_results.get('elasticity', {}).get('elasticity_profile', [])
        if segment_data and len(segment_data) > 0:
            ep_df = pd.DataFrame(segment_data)
            fig.add_trace(
                go.Scatter(
                    x=ep_df['price'],
                    y=ep_df['elasticity'],
                    mode='lines+markers',
                    name='滚动弹性',
                    line=dict(color='#ff7f0e', width=2),
                    yaxis='y2'
                ),
                row=1, col=1
            )
        
        x_labels = []
        for _, seg in price_segments.iterrows():
            x_labels.append(f'{seg["price_range_lower"]:.0f}-{seg["price_range_upper"]:.0f}元')
        
        valid_segments = price_segments[price_segments['price_elasticity'].notna()]
        
        fig.add_trace(
            go.Bar(
                x=x_labels,
                y=valid_segments['price_elasticity'],
                name='区间弹性',
                marker_color='#1f77b4',
                text=[f'{e:.3f}' for e in valid_segments['price_elasticity']],
                textposition='auto'
            ),
            row=2, col=1
        )
        
        fig.add_hline(y=-1, line_dash="dash", line_color="red", 
                     annotation_text="单位弹性线", row=2, col=1)
        
        fig.update_layout(
            title='价格阈值检测与心理价位分析',
            height=700
        )
        
        return fig
    else:
        fig, axes = plt.subplots(2, 1, figsize=(12, 8), sharex=True)
        
        scatter = axes[0].scatter(df['effective_price'], df['sales_quantity'],
                                 c=df['is_promotion'], cmap='viridis',
                                 alpha=0.6, s=60)
        axes[0].set_ylabel('销量')
        axes[0].set_title('价格-销量散点图与阈值检测')
        
        for i, threshold in enumerate(thresholds):
            price = threshold['threshold_price']
            conf = threshold.get('confidence', 0.5)
            axes[0].axvline(x=price, color='red', linestyle='--',
                          alpha=0.3 + conf * 0.5, linewidth=1 + conf)
            axes[0].text(price, axes[0].get_ylim()[1] * 0.95,
                        f'{price:.0f}元\n({conf:.0%})',
                        ha='center', va='top', fontsize=8)
        
        x_labels = []
        for _, seg in price_segments.iterrows():
            x_labels.append(f'{seg["price_range_lower"]:.0f}-{seg["price_range_upper"]:.0f}元')
        
        valid_segments = price_segments[price_segments['price_elasticity'].notna()]
        x_pos = np.arange(len(valid_segments))
        axes[1].bar(x_pos, valid_segments['price_elasticity'], color='#1f77b4')
        axes[1].set_xticks(x_pos)
        axes[1].set_xticklabels(x_labels, rotation=45, ha='right')
        axes[1].axhline(y=-1, color='red', linestyle='--', label='单位弹性')
        axes[1].set_ylabel('价格弹性')
        axes[1].set_title('价格区间弹性对比')
        axes[1].legend()
        
        plt.tight_layout()
        return fig


def plot_price_segments_comparison(
    segment_data: Dict,
    interactive: bool = True
):
    labels = segment_data.get('segment_labels', [])
    avg_sales = segment_data.get('avg_sales', [])
    avg_price = segment_data.get('avg_price', [])
    elasticities = segment_data.get('elasticities', [])
    
    if interactive:
        fig = make_subplots(
            rows=2, cols=1,
            shared_xaxes=True,
            vertical_spacing=0.05,
            subplot_titles=('各价格区间平均销量', '各价格区间弹性系数')
        )
        
        colors = ['#2ca02c' if e < -1 else '#ff7f0e' if e < -0.5 else '#d62728' for e in elasticities]
        
        fig.add_trace(
            go.Bar(
                x=labels,
                y=avg_sales,
                name='平均销量',
                marker_color='#1f77b4',
                text=[f'{s:.0f}' for s in avg_sales],
                textposition='auto'
            ),
            row=1, col=1
        )
        
        fig.add_trace(
            go.Bar(
                x=labels,
                y=elasticities,
                name='价格弹性',
                marker_color=colors,
                text=[f'{e:.3f}' for e in elasticities],
                textposition='auto'
            ),
            row=2, col=1
        )
        
        fig.add_hline(y=-1, line_dash="dash", line_color="red",
                     annotation_text="单位弹性线", row=2, col=1)
        
        fig.update_layout(
            title='价格区间特征对比',
            height=600,
            showlegend=False
        )
        
        return fig
    else:
        fig, axes = plt.subplots(2, 1, figsize=(12, 8), sharex=True)
        
        x_pos = np.arange(len(labels))
        axes[0].bar(x_pos, avg_sales, color='#1f77b4')
        axes[0].set_ylabel('平均销量')
        axes[0].set_title('各价格区间平均销量')
        
        colors = ['#2ca02c' if e < -1 else '#ff7f0e' if e < -0.5 else '#d62728' for e in elasticities]
        axes[1].bar(x_pos, elasticities, color=colors)
        axes[1].axhline(y=-1, color='red', linestyle='--', label='单位弹性')
        axes[1].set_xticks(x_pos)
        axes[1].set_xticklabels(labels, rotation=45, ha='right')
        axes[1].set_ylabel('价格弹性')
        axes[1].set_title('各价格区间弹性系数')
        axes[1].legend()
        
        plt.tight_layout()
        return fig

