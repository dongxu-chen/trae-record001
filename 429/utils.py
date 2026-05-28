import pandas as pd
import numpy as np
from typing import Dict, List, Optional
import plotly.graph_objects as go
from plotly.subplots import make_subplots


def format_number(num: float, decimals: int = 2) -> str:
    if num is None:
        return "N/A"
    return f"{num:,.{decimals}f}"


def format_currency(num: float, decimals: int = 2) -> str:
    if num is None:
        return "N/A"
    return f"¥{num:,.{decimals}f}"


def get_risk_color(stockout_prob: float) -> str:
    if stockout_prob > 0.2:
        return "#ff4b4b"
    elif stockout_prob > 0.05:
        return "#ffa500"
    else:
        return "#00cc96"


def get_risk_label(stockout_prob: float) -> str:
    if stockout_prob > 0.2:
        return "高风险"
    elif stockout_prob > 0.05:
        return "中风险"
    else:
        return "低风险"


def plot_forecast(historical_data: pd.DataFrame, forecast: pd.DataFrame, 
                  future_forecast: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    
    fig.add_trace(go.Scatter(
        x=historical_data['ds'],
        y=historical_data['y'],
        mode='markers',
        name='历史销量',
        marker=dict(color='#636efa', size=4)
    ))
    
    fig.add_trace(go.Scatter(
        x=forecast['ds'],
        y=forecast['yhat'],
        mode='lines',
        name='预测销量',
        line=dict(color='#00cc96', width=2)
    ))
    
    fig.add_trace(go.Scatter(
        x=forecast['ds'],
        y=forecast['yhat_upper'],
        mode='lines',
        line=dict(color='rgba(0,204,150,0.3)', width=1),
        name='预测上限'
    ))
    
    fig.add_trace(go.Scatter(
        x=forecast['ds'],
        y=forecast['yhat_lower'],
        mode='lines',
        line=dict(color='rgba(0,204,150,0.3)', width=1),
        fill='tonexty',
        fillcolor='rgba(0,204,150,0.1)',
        name='预测下限'
    ))
    
    fig.update_layout(
        title='销量预测',
        xaxis_title='日期',
        yaxis_title='销量',
        hovermode='x unified',
        template='plotly_white',
        legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1)
    )
    
    return fig


def plot_inventory_simulation(daily_metrics: pd.DataFrame, reorder_point: float, 
                            safety_stock: float) -> go.Figure:
    fig = go.Figure()
    
    fig.add_trace(go.Scatter(
        x=daily_metrics['date'],
        y=daily_metrics['avg_stock'],
        mode='lines',
        name='平均库存',
        line=dict(color='#636efa', width=2)
    ))
    
    fig.add_trace(go.Scatter(
        x=daily_metrics['date'],
        y=daily_metrics['p95_stock'],
        mode='lines',
        line=dict(color='rgba(99,110,250,0.3)', width=1),
        name='95%分位库存'
    ))
    
    fig.add_trace(go.Scatter(
        x=daily_metrics['date'],
        y=daily_metrics['p5_stock'],
        mode='lines',
        line=dict(color='rgba(99,110,250,0.3)', width=1),
        fill='tonexty',
        fillcolor='rgba(99,110,250,0.1)',
        name='5%分位库存'
    ))
    
    fig.add_hline(
        y=reorder_point,
        line_dash="dash",
        line_color="#ffa500",
        annotation_text=f"补货点: {reorder_point:.1f}",
        annotation_position="bottom right"
    )
    
    fig.add_hline(
        y=safety_stock,
        line_dash="dot",
        line_color="#ff4b4b",
        annotation_text=f"安全库存: {safety_stock:.1f}",
        annotation_position="bottom right"
    )
    
    fig.update_layout(
        title='库存仿真结果',
        xaxis_title='日期',
        yaxis_title='库存水平',
        hovermode='x unified',
        template='plotly_white',
        legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1)
    )
    
    return fig


def plot_stockout_risk(daily_metrics: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    
    colors = [get_risk_color(p) for p in daily_metrics['stockout_prob']]
    
    fig.add_trace(go.Bar(
        x=daily_metrics['date'],
        y=daily_metrics['stockout_prob'] * 100,
        marker_color=colors,
        name='缺货概率'
    ))
    
    fig.add_hline(
        y=5,
        line_dash="dash",
        line_color="#ffa500",
        annotation_text="中风险阈值 (5%)",
        annotation_position="right"
    )
    
    fig.add_hline(
        y=20,
        line_dash="dash",
        line_color="#ff4b4b",
        annotation_text="高风险阈值 (20%)",
        annotation_position="right"
    )
    
    fig.update_layout(
        title='每日缺货风险',
        xaxis_title='日期',
        yaxis_title='缺货概率 (%)',
        hovermode='x unified',
        template='plotly_white'
    )
    
    return fig


def plot_newsvendor_curve(demand_mean: float, demand_std: float, 
                        optimal_qty: float, critical_fractile: float) -> go.Figure:
    from scipy.stats import norm
    
    x = np.linspace(max(0, demand_mean - 4*demand_std), demand_mean + 4*demand_std, 200)
    pdf = norm.pdf(x, demand_mean, demand_std)
    cdf = norm.cdf(x, demand_mean, demand_std)
    
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    
    fig.add_trace(
        go.Scatter(x=x, y=pdf, name='需求分布', line=dict(color='#636efa', width=2)),
        secondary_y=False,
    )
    
    fig.add_trace(
        go.Scatter(x=x, y=cdf, name='累积分布', line=dict(color='#00cc96', width=2)),
        secondary_y=True,
    )
    
    fig.add_vline(
        x=optimal_qty,
        line_dash="dash",
        line_color="#ff4b4b",
        annotation_text=f"最优订货量: {optimal_qty:.1f}",
        annotation_position="top right"
    )
    
    fig.add_hline(
        y=critical_fractile,
        line_dash="dot",
        line_color="#ffa500",
        annotation_text=f"临界分位数: {critical_fractile:.2%}",
        annotation_position="right",
        secondary_y=True
    )
    
    fig.update_layout(
        title='报童模型 - 最优订货量分析',
        xaxis_title='需求量',
        template='plotly_white',
        legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1)
    )
    
    fig.update_yaxes(title_text="概率密度", secondary_y=False)
    fig.update_yaxes(title_text="累积概率", secondary_y=True)
    
    return fig


def validate_dataframe(df: pd.DataFrame, required_columns: List[str]) -> tuple:
    missing_columns = [col for col in required_columns if col not in df.columns]
    if missing_columns:
        return False, f"缺少必需列: {', '.join(missing_columns)}"
    
    if len(df) == 0:
        return False, "数据为空"
    
    return True, "数据验证通过"


def load_csv_upload(uploaded_file) -> pd.DataFrame:
    if uploaded_file is not None:
        try:
            df = pd.read_csv(uploaded_file)
            return df
        except Exception as e:
            raise ValueError(f"文件读取失败: {str(e)}")
    return None


def plot_scenario_comparison(scenario_results: List) -> go.Figure:
    from simulation import ScenarioResult
    
    fig = go.Figure()
    
    scenario_names = []
    stockout_rates = []
    avg_stocks = []
    avg_costs = []
    
    for result in scenario_results:
        sim = result.simulation_result
        scenario_names.append(result.scenario_name)
        stockout_rates.append(sim.stockout_rate * 100)
        avg_stocks.append(sim.average_stock)
        avg_costs.append(sim.average_cost)
    
    fig.add_trace(go.Bar(
        x=scenario_names,
        y=stockout_rates,
        name='缺货率 (%)',
        marker_color='#ff4b4b',
        text=[f"{rate:.1f}%" for rate in stockout_rates],
        textposition='auto'
    ))
    
    fig.add_trace(go.Bar(
        x=scenario_names,
        y=avg_stocks,
        name='平均库存',
        marker_color='#636efa',
        text=[f"{stock:.1f}" for stock in avg_stocks],
        textposition='auto',
        yaxis='y2'
    ))
    
    fig.update_layout(
        title='多场景对比分析',
        xaxis_title='场景',
        yaxis_title='缺货率 (%)',
        barmode='group',
        template='plotly_white',
        legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1),
        yaxis2=dict(
            title='平均库存',
            overlaying='y',
            side='right'
        )
    )
    
    return fig


def plot_holiday_effects(holiday_effects: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    
    fig.add_trace(go.Bar(
        x=holiday_effects['ds'],
        y=holiday_effects['holidays'],
        name='节假日效应',
        marker_color='#ffa500'
    ))
    
    fig.update_layout(
        title='节假日对销量的影响',
        xaxis_title='日期',
        yaxis_title='销量增量',
        template='plotly_white'
    )
    
    return fig


def plot_cost_optimization(cost_params: Dict) -> go.Figure:
    fig = go.Figure()
    
    params = [
        ('预估持有成本', cost_params.get('estimated_holding_cost', 0)),
        ('预估缺货成本', cost_params.get('estimated_stockout_cost', 0)),
        ('最优持有成本', cost_params.get('optimal_holding_cost', 0)),
        ('最优缺货成本', cost_params.get('optimal_stockout_cost', 0))
    ]
    
    names = [p[0] for p in params]
    values = [p[1] for p in params]
    colors = ['#636efa', '#ff4b4b', '#00cc96', '#ffa500']
    
    fig.add_trace(go.Bar(
        x=names,
        y=values,
        marker_color=colors,
        text=[f"¥{v:.2f}" for v in values],
        textposition='auto'
    ))
    
    fig.update_layout(
        title='成本参数优化对比',
        xaxis_title='参数类型',
        yaxis_title='成本 (元)',
        template='plotly_white'
    )
    
    return fig


def plot_extreme_risk_analysis(extreme_result: Dict) -> go.Figure:
    fig = go.Figure()
    
    risk_levels = [
        ('缺货>5天概率', extreme_result.get('prob_more_than_5_days', 0) * 100),
        ('缺货>10天概率', extreme_result.get('prob_more_than_10_days', 0) * 100),
        ('缺货>20天概率', extreme_result.get('prob_more_than_20_days', 0) * 100)
    ]
    
    names = [r[0] for r in risk_levels]
    probs = [r[1] for r in risk_levels]
    
    fig.add_trace(go.Bar(
        x=names,
        y=probs,
        marker_color=['#ffa500', '#ff6b6b', '#c92a2a'],
        text=[f"{p:.1f}%" for p in probs],
        textposition='auto'
    ))
    
    fig.update_layout(
        title='极端场景缺货风险分析',
        xaxis_title='风险等级',
        yaxis_title='概率 (%)',
        template='plotly_white'
    )
    
    return fig


def plot_holiday_calendar(holidays_df: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    
    for _, holiday in holidays_df.iterrows():
        start_date = holiday['ds'] + pd.Timedelta(days=holiday['lower_window'])
        end_date = holiday['ds'] + pd.Timedelta(days=holiday['upper_window'])
        
        fig.add_trace(go.Scatter(
            x=[start_date, end_date],
            y=[holiday['holiday'], holiday['holiday']],
            mode='lines',
            line=dict(width=10),
            name=holiday['holiday'],
            hovertemplate=f"{holiday['holiday']}<br>需求提升: {holiday['demand_boost']:.1f}x"
        ))
    
    fig.update_layout(
        title='电商大促节假日日历',
        xaxis_title='日期',
        yaxis_title='节假日',
        template='plotly_white',
        showlegend=False,
        height=400
    )
    
    return fig


from typing import List

def plot_multi_echelon_inventory(multi_echelon_plan: dict) -> go.Figure:
    fig = go.Figure()
    
    warehouse = multi_echelon_plan.get('warehouse', {})
    stores = multi_echelon_plan.get('stores', {})
    
    locations = [warehouse.get('name', '仓库')] + list(stores.keys())
    current_stocks = [warehouse.get('current_stock', 0)] + [s.get('current_stock', 0) for s in stores.values()]
    safety_stocks = [warehouse.get('safety_stock', 0)] + [s.get('safety_stock', 0) for s in stores.values()]
    reorder_points = [warehouse.get('reorder_point', 0)] + [s.get('reorder_point', 0) for s in stores.values()]
    
    fig.add_trace(go.Bar(
        x=locations,
        y=current_stocks,
        name='当前库存',
        marker_color='#636efa'
    ))
    
    fig.add_trace(go.Bar(
        x=locations,
        y=safety_stocks,
        name='安全库存',
        marker_color='#00cc96'
    ))
    
    fig.add_trace(go.Scatter(
        x=locations,
        y=reorder_points,
        mode='lines+markers',
        name='补货点',
        line=dict(color='#ffa500', width=2, dash='dash')
    ))
    
    fig.update_layout(
        title='多级库存分布',
        xaxis_title='位置',
        yaxis_title='库存数量',
        barmode='group',
        template='plotly_white',
        legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1)
    )
    
    return fig


def plot_supplier_variability(supplier_analysis: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    
    if len(supplier_analysis) > 0:
        colors = []
        for risk in supplier_analysis['risk_level']:
            if risk == 'high':
                colors.append('#ff4b4b')
            elif risk == 'medium':
                colors.append('#ffa500')
            else:
                colors.append('#00cc96')
        
        fig.add_trace(go.Bar(
            x=supplier_analysis['supplier_name'],
            y=supplier_analysis['variability_score'] * 100,
            name='变异系数 (%)',
            marker_color=colors,
            text=[f"{v:.1f}%" for v in supplier_analysis['variability_score'] * 100],
            textposition='auto'
        ))
        
        fig.add_trace(go.Scatter(
            x=supplier_analysis['supplier_name'],
            y=supplier_analysis['on_time_rate'] * 100,
            mode='lines+markers',
            name='准时率 (%)',
            line=dict(color='#636efa', width=2),
            yaxis='y2',
            text=[f"{v:.1f}%" for v in supplier_analysis['on_time_rate'] * 100],
            textposition='top center'
        ))
    
    fig.update_layout(
        title='供应商交期变异分析',
        xaxis_title='供应商',
        yaxis_title='变异系数 (%)',
        template='plotly_white',
        legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1),
        yaxis2=dict(
            title='准时率 (%)',
            overlaying='y',
            side='right',
            range=[0, 100]
        )
    )
    
    return fig


def plot_safety_stock_adjustment(adjustment_data: dict) -> go.Figure:
    fig = go.Figure()
    
    items = ['基础安全库存', '调整后安全库存', '最终安全库存']
    values = [
        adjustment_data.get('base_safety_stock', 0),
        adjustment_data.get('adjusted_safety_stock', 0),
        adjustment_data.get('final_safety_stock', 0)
    ]
    colors = ['#636efa', '#ffa500', '#ff4b4b']
    
    fig.add_trace(go.Bar(
        x=items,
        y=values,
        marker_color=colors,
        text=[f"{v:.1f}" for v in values],
        textposition='auto'
    ))
    
    fig.update_layout(
        title='安全库存调整对比',
        xaxis_title='阶段',
        yaxis_title='安全库存数量',
        template='plotly_white'
    )
    
    return fig


def plot_inventory_health_gauge(health_score: dict) -> go.Figure:
    score = health_score.get('overall_score', 0)
    color = health_score.get('health_color', '#636efa')
    level = health_score.get('health_level', '未知')
    
    fig = go.Figure(go.Indicator(
        mode="gauge+number+delta",
        value=score,
        domain={'x': [0, 1], 'y': [0, 1]},
        title={'text': f"库存健康度: {level}"},
        delta={'reference': 70, 'increasing': {'color': '#00cc96'}, 'decreasing': {'color': '#ff4b4b'}},
        gauge={
            'axis': {'range': [0, 100], 'tickwidth': 1, 'tickcolor': "darkblue"},
            'bar': {'color': color, 'thickness': 0.3},
            'bgcolor': "white",
            'borderwidth': 2,
            'bordercolor': "gray",
            'steps': [
                {'range': [0, 30], 'color': '#ffe0e0'},
                {'range': [30, 50], 'color': '#fff3e0'},
                {'range': [50, 70], 'color': '#e3f2fd'},
                {'range': [70, 85], 'color': '#e8f5e9'},
                {'range': [85, 100], 'color': '#c8e6c9'}
            ],
            'threshold': {
                'line': {'color': "red", 'width': 4},
                'thickness': 0.75,
                'value': 50
            }
        }
    ))
    
    fig.update_layout(
        template='plotly_white',
        height=400
    )
    
    return fig


def plot_health_metrics(health_score: dict) -> go.Figure:
    metrics = health_score.get('metrics', [])
    
    if not metrics:
        return go.Figure()
    
    fig = go.Figure()
    
    names = [m['name'] for m in metrics]
    scores = [m['score'] for m in metrics]
    weights = [m['weight'] * 100 for m in metrics]
    
    colors = []
    for score in scores:
        if score >= 85:
            colors.append('#00cc96')
        elif score >= 70:
            colors.append('#636efa')
        elif score >= 50:
            colors.append('#ffa500')
        elif score >= 30:
            colors.append('#ff6b6b')
        else:
            colors.append('#c92a2a')
    
    fig.add_trace(go.Bar(
        x=names,
        y=scores,
        name='得分',
        marker_color=colors,
        text=[f"{s:.0f}" for s in scores],
        textposition='auto'
    ))
    
    fig.add_trace(go.Scatter(
        x=names,
        y=weights,
        mode='lines+markers',
        name='权重 (%)',
        line=dict(color='#ffa500', width=2),
        yaxis='y2'
    ))
    
    fig.update_layout(
        title='库存健康度指标分析',
        xaxis_title='指标',
        yaxis_title='得分',
        template='plotly_white',
        legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1),
        yaxis2=dict(
            title='权重 (%)',
            overlaying='y',
            side='right',
            range=[0, 50]
        )
    )
    
    return fig


def plot_transfer_plan(transfers: list) -> go.Figure:
    fig = go.Figure()
    
    if transfers:
        for i, transfer in enumerate(transfers):
            fig.add_trace(go.Bar(
                x=[f"{transfer['from']} → {transfer['to']}"],
                y=[transfer['quantity']],
                name=f"调拨 {i+1}",
                marker_color='#636efa' if transfer['cost_per_unit'] < 1 else '#ff6b6b',
                text=[f"{transfer['quantity']:.0f}件<br>成本: ¥{transfer.get('total_cost', 0):.0f}"],
                textposition='auto'
            ))
    
    fig.update_layout(
        title='库存调拨计划',
        xaxis_title='调拨方向',
        yaxis_title='调拨数量',
        template='plotly_white',
        showlegend=False
    )
    
    return fig
