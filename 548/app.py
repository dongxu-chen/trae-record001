import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

from config import config
from data_generator import ServerDataGenerator
from prophet_predictor import ResourcePredictor
from anomaly_detector import AnomalyDetector
from capacity_planner import CapacityPlanner
from app_resource_manager import AppResourceManager
from auto_scaler import AutoScaler
from resource_optimizer import ResourceOptimizer
from utils import format_timestamp, get_resource_status, calculate_statistics

st.set_page_config(
    page_title="服务器资源水位预测系统",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
    <style>
    .main {
        background-color: #f8f9fa;
    }
    .metric-card {
        background-color: white;
        padding: 20px;
        border-radius: 10px;
        box-shadow: 0 2px 10px rgba(0,0,0,0.1);
    }
    .warning-box {
        background-color: #fff3cd;
        border-left: 5px solid #ffc107;
        padding: 15px;
        margin: 10px 0;
    }
    .critical-box {
        background-color: #f8d7da;
        border-left: 5px solid #dc3545;
        padding: 15px;
        margin: 10px 0;
    }
    .success-box {
        background-color: #d4edda;
        border-left: 5px solid #28a745;
        padding: 15px;
        margin: 10px 0;
    }
    .stPlotlyChart {
        background-color: white;
        border-radius: 10px;
        padding: 10px;
        box-shadow: 0 2px 10px rgba(0,0,0,0.1);
    }
    </style>
""", unsafe_allow_html=True)

st.title("📊 服务器资源水位预测系统")
st.markdown("---")

@st.cache_data(ttl=3600, max_entries=5)
def load_or_generate_data(days: int = 30, seed: int = 42):
    generator = ServerDataGenerator(seed=seed)
    df = generator.generate_historical_data(days=days)
    return df

@st.cache_resource(ttl=3600)
def train_predictor(df: pd.DataFrame):
    predictor = ResourcePredictor()
    predictor.fit(df)
    return predictor

@st.cache_data(ttl=3600)
def get_forecasts(_predictor: ResourcePredictor, hours: int = 24):
    forecasts = {}
    for resource_type in config.resources.keys():
        forecasts[resource_type] = _predictor.get_threshold_forecast(resource_type, hours)
    return forecasts

@st.cache_data(ttl=3600)
def get_forecast_summaries(_predictor: ResourcePredictor, hours: int = 24):
    summaries = {}
    for resource_type in config.resources.keys():
        summaries[resource_type] = _predictor.get_forecast_summary(resource_type, hours)
    return summaries

@st.cache_data(ttl=3600)
def detect_anomalies(df: pd.DataFrame, forecasts: dict, _predictor: ResourcePredictor):
    anomaly_results = {}
    detector = AnomalyDetector()
    for resource_type in config.resources.keys():
        anomaly_df = detector.detect_all_anomalies(
            df, resource_type, forecasts[resource_type], predictor=_predictor)
        anomaly_df = detector.analyze_anomaly_severity(anomaly_df, resource_type)
        summary = detector.get_anomaly_summary(anomaly_df, resource_type)
        anomaly_results[resource_type] = {
            'data': anomaly_df,
            'summary': summary
        }
    return anomaly_results

@st.cache_data(ttl=3600)
def generate_capacity_report(df: pd.DataFrame, forecast_summaries: dict):
    planner = CapacityPlanner()
    report = planner.get_overall_capacity_summary(df, forecast_summaries)
    return report

with st.sidebar:
    st.header("⚙️ 配置参数")
    st.subheader("数据设置")
    historical_days = st.slider("历史数据天数", 7, 60, 30)
    prediction_hours = st.slider("预测小时数", 6, 72, 24)
    random_seed = st.number_input("随机种子", min_value=0, max_value=9999, value=42)

    st.subheader("模型参数")
    changepoint_prior = st.slider("突变点敏感度", 0.001, 0.5, 0.05, 0.001, format="%.3f")
    seasonality_prior = st.slider("季节性强度", 0.1, 20.0, 10.0, 0.1)

    st.subheader("阈值设置")
    for resource_type, res_config in config.resources.items():
        st.markdown(f"**{res_config.name}**")
        col1, col2 = st.columns(2)
        with col1:
            warning_th = st.number_input(
                f"警告阈值({resource_type})",
                min_value=50.0, max_value=95.0,
                value=res_config.warning_threshold,
                key=f"warn_{resource_type}"
            )
        with col2:
            critical_th = st.number_input(
                f"危险阈值({resource_type})",
                min_value=60.0, max_value=100.0,
                value=res_config.critical_threshold,
                key=f"crit_{resource_type}"
            )
        res_config.warning_threshold = warning_th
        res_config.critical_threshold = critical_th

    st.markdown("---")
    st.subheader("📋 功能导航")
    page = st.radio(
        "选择页面",
        ["📈 实时监控", "🔮 趋势预测", "🔍 异常检测", "📅 周期分析",
         "💡 容量规划", "⚙️ 自动扩容", "🔗 资源竞争", "📉 资源优化",
         "📊 数据详情"]
    )

    if st.button("🔄 重新生成数据"):
        st.cache_data.clear()
        st.cache_resource.clear()
        st.success("数据已重新生成！")

config.changepoint_prior_scale = changepoint_prior
config.seasonality_prior_scale = seasonality_prior
config.prediction_hours = prediction_hours

with st.spinner("正在加载数据并训练预测模型..."):
    df = load_or_generate_data(days=historical_days, seed=random_seed)
    predictor = train_predictor(df)
    forecasts = get_forecasts(predictor, hours=prediction_hours)
    forecast_summaries = get_forecast_summaries(predictor, hours=prediction_hours)
    anomaly_results = detect_anomalies(df, forecasts, predictor)
    capacity_report = generate_capacity_report(df, forecast_summaries)

@st.cache_resource(ttl=3600)
def get_app_resource_manager():
    return AppResourceManager()

@st.cache_resource(ttl=3600)
def get_auto_scaler():
    return AutoScaler()

@st.cache_resource(ttl=3600)
def get_resource_optimizer():
    return ResourceOptimizer()

app_manager = get_app_resource_manager()
auto_scaler = get_auto_scaler()
resource_optimizer = get_resource_optimizer()

def plot_resource_forecast(resource_type: str, hours: int = 24):
    res_config = config.resources[resource_type]
    color = config.color_palette[resource_type]
    forecast = forecasts[resource_type]

    now = datetime.now()
    plot_start = now - timedelta(hours=48)
    forecast_data = forecast[forecast['ds'] >= plot_start].copy()
    historical = forecast_data[forecast_data['ds'] <= now]
    future = forecast_data[forecast_data['ds'] > now]

    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=historical['ds'],
        y=historical['yhat'],
        mode='lines',
        name='历史实际值',
        line=dict(color=color, width=2),
        hovertemplate='时间: %{x}<br>值: %{y:.1f}%<extra></extra>'
    ))

    fig.add_trace(go.Scatter(
        x=future['ds'],
        y=future['yhat'],
        mode='lines',
        name='预测值',
        line=dict(color=config.color_palette['prediction'], width=2, dash='dash'),
        hovertemplate='时间: %{x}<br>预测值: %{y:.1f}%<extra></extra>'
    ))

    fig.add_trace(go.Scatter(
        x=pd.concat([future['ds'], future['ds'][::-1]]),
        y=pd.concat([future['yhat_upper'], future['yhat_lower'][::-1]]),
        fill='toself',
        fillcolor=config.color_palette['prediction'],
        opacity=0.2,
        line=dict(color='rgba(255,255,255,0)'),
        name='置信区间',
        hovertemplate='时间: %{x}<br>范围: %{y:.1f}%<extra></extra>'
    ))

    fig.add_hline(
        y=res_config.warning_threshold,
        line_dash="dash",
        line_color=config.color_palette['warning'],
        annotation_text=f"警告阈值 ({res_config.warning_threshold}%)",
        annotation_position="bottom right"
    )

    fig.add_hline(
        y=res_config.critical_threshold,
        line_dash="dash",
        line_color=config.color_palette['critical'],
        annotation_text=f"危险阈值 ({res_config.critical_threshold}%)",
        annotation_position="top right"
    )

    fig.add_vline(
        x=now,
        line_dash="solid",
        line_color="gray",
        opacity=0.5,
        annotation_text="现在",
        annotation_position="top left"
    )

    fig.update_layout(
        title=f"{res_config.name} - 历史数据与{hours}小时预测",
        xaxis_title="时间",
        yaxis_title=f"使用率 ({res_config.unit})",
        template=config.plotly_template,
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        yaxis=dict(range=[0, 100])
    )

    return fig

def plot_anomaly_detection(resource_type: str):
    anomaly_data = anomaly_results[resource_type]['data']
    color = config.color_palette[resource_type]
    res_config = config.resources[resource_type]

    last_7_days = anomaly_data[anomaly_data['ds'] >= (datetime.now() - timedelta(days=7))]

    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=last_7_days['ds'],
        y=last_7_days[resource_type],
        mode='lines',
        name='正常数据',
        line=dict(color=color, width=1.5),
        hovertemplate='时间: %{x}<br>值: %{y:.1f}%<extra></extra>'
    ))

    anomalies = last_7_days[last_7_days['is_anomaly']]
    if len(anomalies) > 0:
        critical_anoms = anomalies[anomalies['severity'] == 'critical']
        warning_anoms = anomalies[anomalies['severity'] == 'warning']
        low_anoms = anomalies[anomalies['severity'] == 'low']

        if len(critical_anoms) > 0:
            fig.add_trace(go.Scatter(
                x=critical_anoms['ds'],
                y=critical_anoms[resource_type],
                mode='markers',
                name='严重异常',
                marker=dict(color=config.color_palette['critical'], size=10, symbol='x'),
                hovertemplate='时间: %{x}<br>值: %{y:.1f}%<br>分数: %{customdata}<extra></extra>',
                customdata=critical_anoms['anomaly_score']
            ))

        if len(warning_anoms) > 0:
            fig.add_trace(go.Scatter(
                x=warning_anoms['ds'],
                y=warning_anoms[resource_type],
                mode='markers',
                name='警告异常',
                marker=dict(color=config.color_palette['warning'], size=8, symbol='triangle-up'),
                hovertemplate='时间: %{x}<br>值: %{y:.1f}%<br>分数: %{customdata}<extra></extra>',
                customdata=warning_anoms['anomaly_score']
            ))

        if len(low_anoms) > 0:
            fig.add_trace(go.Scatter(
                x=low_anoms['ds'],
                y=low_anoms[resource_type],
                mode='markers',
                name='一般异常',
                marker=dict(color=config.color_palette['anomaly'], size=6, symbol='circle'),
                hovertemplate='时间: %{x}<br>值: %{y:.1f}%<br>分数: %{customdata}<extra></extra>',
                customdata=low_anoms['anomaly_score']
            ))

    fig.update_layout(
        title=f"{res_config.name} - 异常检测结果 (近7天)",
        xaxis_title="时间",
        yaxis_title=f"使用率 ({res_config.unit})",
        template=config.plotly_template,
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )

    return fig

def plot_seasonality(resource_type: str):
    components = predictor.get_sliding_window_components(resource_type)
    res_config = config.resources[resource_type]

    col1, col2 = st.columns(2)

    with col1:
        daily_pattern = components['daily']
        fig_daily = go.Figure()
        fig_daily.add_trace(go.Scatter(
            x=daily_pattern['hour'], y=daily_pattern['daily'],
            mode='lines+markers', name='平均使用率',
            line=dict(color=config.color_palette[resource_type], width=2),
            hovertemplate='小时: %{x}:00<br>均值: %{y:.1f}%<extra></extra>'
        ))
        fig_daily.add_trace(go.Scatter(
            x=daily_pattern['hour'],
            y=daily_pattern['daily'] + daily_pattern['std'],
            mode='lines', line=dict(width=0), showlegend=False
        ))
        fig_daily.add_trace(go.Scatter(
            x=daily_pattern['hour'],
            y=daily_pattern['daily'] - daily_pattern['std'],
            mode='lines', line=dict(width=0), showlegend=False,
            fill='tonexty', fillcolor=config.color_palette[resource_type],
            opacity=0.15, name='标准差范围'
        ))
        fig_daily.update_layout(
            title=f"{res_config.name} - 日周期性模式（滑动窗口）",
            xaxis_title="小时",
            yaxis_title="使用率 (%)",
            template=config.plotly_template,
            xaxis=dict(tickmode='linear', tick0=0, dtick=2)
        )
        st.plotly_chart(fig_daily, use_container_width=True)

    with col2:
        weekly_pattern = components['weekly']
        fig_weekly = go.Figure()
        fig_weekly.add_trace(go.Bar(
            x=weekly_pattern['dayname'],
            y=weekly_pattern['weekly'],
            marker_color=config.color_palette[resource_type],
            hovertemplate='星期: %{x}<br>均值: %{y:.1f}%<extra></extra>'
        ))
        fig_weekly.add_trace(go.Scatter(
            x=weekly_pattern['dayname'],
            y=weekly_pattern['weekly'] + weekly_pattern['std'],
            mode='lines', line=dict(width=0), showlegend=False
        ))
        fig_weekly.add_trace(go.Scatter(
            x=weekly_pattern['dayname'],
            y=weekly_pattern['weekly'] - weekly_pattern['std'],
            mode='lines', line=dict(width=0), showlegend=False,
            fill='tonexty', fillcolor=config.color_palette[resource_type],
            opacity=0.15, name='标准差范围'
        ))
        fig_weekly.update_layout(
            title=f"{res_config.name} - 周周期性模式（滑动窗口）",
            xaxis_title="星期",
            yaxis_title="使用率 (%)",
            template=config.plotly_template
        )
        st.plotly_chart(fig_weekly, use_container_width=True)

def display_metric_cards():
    col1, col2, col3 = st.columns(3)

    for idx, (resource_type, res_config) in enumerate(config.resources.items()):
        current_value = round(df[resource_type].iloc[-1], 2)
        status, color = get_resource_status(current_value, resource_type)
        summary = forecast_summaries[resource_type]
        anomaly_count = anomaly_results[resource_type]['summary']['anomaly_count']

        with [col1, col2, col3][idx]:
            st.markdown(f"""
                <div class="metric-card">
                    <h3 style="color: {color}; margin: 0;">{res_config.name}</h3>
                    <h1 style="font-size: 36px; margin: 10px 0; color: {color};">
                        {current_value}{res_config.unit}
                    </h1>
                    <p style="margin: 5px 0; color: #666;">
                        状态: <span style="color: {color}; font-weight: bold;">{status.upper()}</span>
                    </p>
                    <p style="margin: 5px 0; color: #666;">
                        预测峰值: {summary['max_predicted']}{res_config.unit}
                    </p>
                    <p style="margin: 5px 0; color: #666;">
                        异常点数: {anomaly_count}
                    </p>
                </div>
            """, unsafe_allow_html=True)

def display_alerts():
    has_critical = False
    has_warning = False

    critical_messages = []
    warning_messages = []

    for resource_type, res_config in config.resources.items():
        summary = forecast_summaries[resource_type]

        if summary['first_critical_time']:
            has_critical = True
            time_str = format_timestamp(summary['first_critical_time'])
            critical_messages.append(
                f"🔴 **{res_config.name}**: 预计 {time_str} 将达到 {summary['max_predicted']}%，"
                f"超过危险阈值 {res_config.critical_threshold}%"
            )

        if summary['first_warning_time'] and not summary['first_critical_time']:
            has_warning = True
            time_str = format_timestamp(summary['first_warning_time'])
            warning_messages.append(
                f"⚠️ **{res_config.name}**: 预计 {time_str} 将达到 {summary['max_predicted']}%，"
                f"超过警告阈值 {res_config.warning_threshold}%"
            )

    if has_critical:
        st.markdown('<div class="critical-box">', unsafe_allow_html=True)
        st.markdown("### 🚨 危险预警")
        for msg in critical_messages:
            st.markdown(msg)
        st.markdown('</div>', unsafe_allow_html=True)

    if has_warning:
        st.markdown('<div class="warning-box">', unsafe_allow_html=True)
        st.markdown("### ⚠️ 警告提醒")
        for msg in warning_messages:
            st.markdown(msg)
        st.markdown('</div>', unsafe_allow_html=True)

    if not has_critical and not has_warning:
        st.markdown('<div class="success-box">', unsafe_allow_html=True)
        st.markdown("### ✅ 系统状态正常")
        st.markdown("未来24小时内所有资源使用率预计均在安全范围内。")
        st.markdown('</div>', unsafe_allow_html=True)

if page == "📈 实时监控":
    st.header("📈 实时监控面板")

    st.subheader("📊 当前资源状态")
    display_metric_cards()

    st.markdown("---")

    st.subheader("🔔 预警信息")
    display_alerts()

    st.markdown("---")

    st.subheader("📈 资源趋势预测")
    tab1, tab2, tab3 = st.tabs(["CPU使用率", "内存使用率", "磁盘使用率"])

    with tab1:
        fig_cpu = plot_resource_forecast('cpu', prediction_hours)
        st.plotly_chart(fig_cpu, use_container_width=True)

    with tab2:
        fig_memory = plot_resource_forecast('memory', prediction_hours)
        st.plotly_chart(fig_memory, use_container_width=True)

    with tab3:
        fig_disk = plot_resource_forecast('disk', prediction_hours)
        st.plotly_chart(fig_disk, use_container_width=True)

    st.markdown("---")

    st.subheader("📋 预测摘要")
    summary_data = []
    for resource_type, res_config in config.resources.items():
        s = forecast_summaries[resource_type]
        summary_data.append({
            '资源类型': res_config.name,
            '预测最大值': f"{s['max_predicted']}{res_config.unit}",
            '预测最小值': f"{s['min_predicted']}{res_config.unit}",
            '预测平均值': f"{s['mean_predicted']}{res_config.unit}",
            '超警告次数': s['warning_count'],
            '超危险次数': s['critical_count'],
            '首次预警时间': format_timestamp(s['first_warning_time']) if s['first_warning_time'] else '无',
            '首次危险时间': format_timestamp(s['first_critical_time']) if s['first_critical_time'] else '无'
        })
    st.table(pd.DataFrame(summary_data))

elif page == "🔮 趋势预测":
    st.header("🔮 趋势预测分析")

    selected_resource = st.selectbox(
        "选择要分析的资源",
        list(config.resources.keys()),
        format_func=lambda x: config.resources[x].name
    )

    st.markdown("---")

    col1, col2 = st.columns([3, 1])

    with col1:
        fig = plot_resource_forecast(selected_resource, prediction_hours)
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.markdown("### 📊 预测统计")
        summary = forecast_summaries[selected_resource]
        res_config = config.resources[selected_resource]

        st.metric("预测最大值", f"{summary['max_predicted']}{res_config.unit}")
        st.metric("预测最小值", f"{summary['min_predicted']}{res_config.unit}")
        st.metric("预测平均值", f"{summary['mean_predicted']}{res_config.unit}")
        st.metric("超警告次数", summary['warning_count'])
        st.metric("超危险次数", summary['critical_count'])

        if summary['first_warning_time']:
            st.warning(f"首次预警: {format_timestamp(summary['first_warning_time'])}")
        if summary['first_critical_time']:
            st.error(f"首次危险: {format_timestamp(summary['first_critical_time'])}")

    st.markdown("---")

    st.subheader("📈 趋势分解")
    forecast = forecasts[selected_resource]
    forecast_recent = forecast.tail(288)

    fig_trend = go.Figure()
    fig_trend.add_trace(go.Scatter(
        x=forecast_recent['ds'], y=forecast_recent['trend'],
        name='趋势', line=dict(color='#e74c3c', width=2)
    ))
    fig_trend.add_trace(go.Scatter(
        x=forecast_recent['ds'], y=forecast_recent['daily'],
        name='日周期', line=dict(color='#3498db', width=2)
    ))
    fig_trend.add_trace(go.Scatter(
        x=forecast_recent['ds'], y=forecast_recent['weekly'],
        name='周周期', line=dict(color='#2ecc71', width=2)
    ))
    fig_trend.update_layout(
        title=f"{res_config.name} - 趋势分解",
        xaxis_title="时间",
        yaxis_title="影响值 (%)",
        template=config.plotly_template
    )
    st.plotly_chart(fig_trend, use_container_width=True)

elif page == "🔍 异常检测":
    st.header("🔍 异常检测分析")

    selected_resource = st.selectbox(
        "选择要分析的资源",
        list(config.resources.keys()),
        format_func=lambda x: config.resources[x].name
    )

    st.markdown("---")

    fig_anomaly = plot_anomaly_detection(selected_resource)
    st.plotly_chart(fig_anomaly, use_container_width=True)

    st.markdown("---")

    col1, col2, col3 = st.columns(3)
    anomaly_summary = anomaly_results[selected_resource]['summary']

    with col1:
        st.metric("总数据点数", anomaly_summary['total_points'])
        st.metric("异常点数量", anomaly_summary['anomaly_count'])

    with col2:
        st.metric("异常率", f"{anomaly_summary['anomaly_rate_percent']}%")
        st.metric("残差异常数", anomaly_summary.get('residual_anomaly_count', 0))

    with col3:
        if 'residual_stats' in anomaly_summary:
            rs = anomaly_summary['residual_stats']
            st.metric("残差均值", rs['mean'])
            st.metric("残差标准差", rs['std'])

    if 'residual_stats' in anomaly_summary:
        st.markdown("---")
        st.subheader("📊 季节性分解残差分析")
        rs = anomaly_summary['residual_stats']
        st.info(
            f"残差是去除趋势和季节性成分后的剩余部分。残差均值={rs['mean']}，"
            f"标准差={rs['std']}。只有残差异常才是真正的异常，"
            f"而非季节性高峰导致的正常波动。"
        )

    st.markdown("---")

    st.subheader("📋 异常检测方法分布")
    anomaly_types = anomaly_summary['anomaly_types']
    method_names = {
        'residual_iqr': '残差IQR',
        'residual_zscore': '残差Z-score',
        'residual_rolling': '残差滑动窗口',
        'residual_iforest': '残差孤立森林',
        'prophet_interval': 'Prophet区间'
    }
    display_methods = []
    display_counts = []
    for key, label in method_names.items():
        if key in anomaly_types:
            display_methods.append(label)
            display_counts.append(anomaly_types[key])
    method_data = pd.DataFrame({
        '检测方法': display_methods,
        '检测到的异常数': display_counts
    })
    fig_methods = px.bar(
        method_data, x='检测方法', y='检测到的异常数',
        color='检测到的异常数',
        color_continuous_scale='Reds',
        title='各检测方法发现的异常数量（基于季节性分解残差）'
    )
    fig_methods.update_layout(template=config.plotly_template)
    st.plotly_chart(fig_methods, use_container_width=True)

    st.markdown("---")

    st.subheader("🕐 最近异常记录")
    recent_anomalies = anomaly_summary['recent_anomalies']
    if recent_anomalies:
        anomaly_table = []
        for anom in recent_anomalies:
            row = {
                '时间': format_timestamp(anom['timestamp']),
                '值': f"{anom['value']}%",
                '异常分数': anom['score'],
                '检测方法': ', '.join(anom['methods'])
            }
            if 'deviation_percent' in anom:
                row['偏差(%)'] = f"{anom['deviation_percent']:.1f}%"
            if 'residual' in anom:
                row['残差'] = f"{anom['residual']:.2f}"
            anomaly_table.append(row)
        st.table(pd.DataFrame(anomaly_table))
    else:
        st.info("暂无异常记录")

elif page == "📅 周期分析":
    st.header("📅 动态周期性模式分析")

    st.info(
        "本页面使用**动态滑动窗口**分析资源使用的周期性模式，能够自适应模式变化。"
        "相比静态分解，滑动窗口可以捕捉模式漂移，识别趋势变化，评估模式稳定性。"
    )

    st.markdown("---")

    for resource_type in config.resources.keys():
        res_config = config.resources[resource_type]

        st.subheader(f"📊 {res_config.name} - 动态周期性分析")

        patterns = predictor.detect_periodic_patterns(resource_type)

        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("日峰值时段", f"{patterns['daily_peak_hour']}:00")
        with col2:
            st.metric("日谷值时段", f"{patterns['daily_valley_hour']}:00")
        with col3:
            st.metric("日波动幅度", f"{patterns['daily_amplitude']}%")
        with col4:
            st.metric("周波动幅度", f"{patterns['weekly_amplitude']}%")

        stability_col1, stability_col2, stability_col3, stability_col4 = st.columns(4)
        with stability_col1:
            stability_color = '#2ecc71' if patterns['daily_stability'] >= 0.8 else (
                '#f1c40f' if patterns['daily_stability'] >= 0.6 else '#e74c3c')
            st.metric("日模式稳定性", f"{patterns['daily_stability']:.1%}")
        with stability_col2:
            st.metric("周模式稳定性", f"{patterns['weekly_stability']:.1%}")
        with stability_col3:
            overall_stability = patterns['overall_stability']
            overall_color = {'stable': '#2ecc71', 'moderate': '#f1c40f', 'volatile': '#e74c3c'}
            st.metric("整体稳定性", overall_stability.upper())
        with stability_col4:
            st.metric("模式漂移次数", patterns['pattern_shifts_detected'])

        st.markdown(f"**周峰值日**: {patterns['weekly_peak_day']} | **周谷值日**: {patterns['weekly_valley_day']} | "
                    f"**分析窗口数**: {patterns['n_windows_analyzed']}")

        plot_seasonality(resource_type)

        st.markdown("---")
        st.subheader(f"📈 {res_config.name} - 模式演进趋势")
        evolution = predictor.get_pattern_evolution(resource_type)
        if len(evolution) > 1:
            fig_evo = go.Figure()
            fig_evo.add_trace(go.Scatter(
                x=evolution['window_start'], y=evolution['daily_amplitude'],
                mode='lines+markers', name='日波动幅度',
                line=dict(color=config.color_palette[resource_type], width=2)
            ))
            fig_evo.add_trace(go.Scatter(
                x=evolution['window_start'], y=evolution['weekly_amplitude'],
                mode='lines+markers', name='周波动幅度',
                line=dict(color=config.color_palette['prediction'], width=2)
            ))
            fig_evo.update_layout(
                title=f"{res_config.name} - 周期性模式随时间变化",
                xaxis_title="窗口起始时间",
                yaxis_title="波动幅度 (%)",
                template=config.plotly_template,
                legend=dict(orientation="h", yanchor="bottom", y=1.02)
            )
            st.plotly_chart(fig_evo, use_container_width=True)
        else:
            st.info("数据量不足以展示模式演进（需要至少2个滑动窗口）")

        st.markdown("---")

    st.subheader("💡 周期性洞察（动态滑动窗口）")
    for resource_type in config.resources.keys():
        res_config = config.resources[resource_type]
        patterns = predictor.detect_periodic_patterns(resource_type)
        peak = patterns['daily_peak_hour']
        valley = patterns['daily_valley_hour']
        stability = patterns['overall_stability']

        stability_note = ""
        if stability == 'volatile':
            stability_note = " ⚠️ 模式波动较大，建议缩短监控周期"
        elif stability == 'moderate':
            stability_note = " 📊 模式存在一定变化，建议持续观察"

        st.markdown(f"""
        **{res_config.name}**{stability_note}:
        - 建议在 {valley}:00-{valley+2 if valley+2 < 24 else 0}:00 安排批处理任务和系统维护
        - 在 {peak}:00-{peak+2 if peak+2 < 24 else 0}:00 高峰时段前确保资源充足
        - 周末负载较低，可考虑进行性能测试和数据备份
        - 模式稳定性评分: {patterns['overall_stability_score']:.1%}
        """)

elif page == "💡 容量规划":
    st.header("💡 容量规划建议（含安全缓冲）")

    overall_risk = capacity_report['overall_risk']
    overall_urgency = capacity_report['overall_urgency']
    safety_buffer = capacity_report.get('safety_buffer_percent', config.safety_buffer_percent)

    st.markdown(f"🔧 **当前安全缓冲设置**: {safety_buffer}% — 所有容量计算均已预留此余量")

    risk_colors = {
        'low': '#2ecc71',
        'medium': '#f1c40f',
        'high': '#e67e22',
        'critical': '#e74c3c'
    }

    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f"""
        <div class="metric-card" style="border-left: 5px solid {risk_colors[overall_risk]};">
            <h3>整体风险等级</h3>
            <h1 style="color: {risk_colors[overall_risk]}; font-size: 32px;">
                {overall_risk.upper()}
            </h1>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown(f"""
        <div class="metric-card" style="border-left: 5px solid {risk_colors[overall_urgency]};">
            <h3>处理紧急程度</h3>
            <h1 style="color: {risk_colors[overall_urgency]}; font-size: 32px;">
                {overall_urgency.upper()}
            </h1>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("---")

    for resource_type, report in capacity_report['reports'].items():
        res_config = config.resources[resource_type]

        with st.expander(f"📊 {res_config.name} - 详细分析报告", expanded=True):
            col1, col2 = st.columns(2)

            with col1:
                st.subheader("📈 趋势分析")
                trend = report['trend_analysis']
                st.write(f"- **当前值**: {trend['current_value']}%")
                st.write(f"- **趋势方向**: {trend['trend_direction']}")
                st.write(f"- **日增长率**: {trend['slope_per_day']}%/天")
                st.write(f"- **30天预测**: {trend['predicted_30d']}% (含缓冲: {trend.get('predicted_30d_with_buffer', 'N/A')}%)")
                st.write(f"- **90天预测**: {trend['predicted_90d']}% (含缓冲: {trend.get('predicted_90d_with_buffer', 'N/A')}%)")
                st.write(f"- **有效警告阈值**: {trend.get('warning_threshold_with_buffer', 'N/A')}% (原始{res_config.warning_threshold}%-{safety_buffer}%)")
                st.write(f"- **有效危险阈值**: {trend.get('critical_threshold_with_buffer', 'N/A')}% (原始{res_config.critical_threshold}%-{safety_buffer}%)")
                if trend['days_to_warning']:
                    st.warning(f"- 预计 {trend['days_to_warning']} 天后达到有效警告阈值（含缓冲）")
                if trend['days_to_critical']:
                    st.error(f"- 预计 {trend['days_to_critical']} 天后达到有效危险阈值（含缓冲）")

            with col2:
                st.subheader("💾 容量余量")
                headroom = report['capacity_headroom']
                st.write(f"- **平均使用率**: {headroom['utilization_current']}%")
                st.write(f"- **峰值使用率(P95)**: {headroom['utilization_peak']}%")
                st.write(f"- **平均余量**: {headroom['headroom_average']}% (有效: {headroom.get('effective_headroom_average', 'N/A')}%)")
                st.write(f"- **峰值余量**: {headroom['headroom_peak']}% (有效: {headroom.get('effective_headroom_peak', 'N/A')}%)")
                st.write(f"- **警告缓冲**: {headroom['warning_buffer']}% (已扣{safety_buffer}%安全缓冲)")
                st.write(f"- **危险缓冲**: {headroom['critical_buffer']}% (已扣{safety_buffer}%安全缓冲)")
                st.write(f"- **安全缓冲**: {headroom.get('safety_buffer_percent', safety_buffer)}%")

            st.markdown("---")
            st.subheader("⏰ 高峰时段分析")
            peak = report['peak_hour_analysis']
            peak_hours_str = ', '.join([f"{h}:00" for h in peak['peak_hours']])
            st.write(f"- **高峰时段**: {peak_hours_str}")
            st.write(f"- **工作日峰值**: {peak['peak_value_weekday']}%")
            st.write(f"- **周末峰值**: {peak['peak_value_weekend']}%")
            st.write(f"- **周末降幅**: {peak['peak_reduction_percent']}%")
            st.write(f"- **建议工作日容量（含{safety_buffer}%缓冲）**: {peak.get('recommended_capacity_weekday', 'N/A')}%")
            st.write(f"- **建议周末容量（含{safety_buffer}%缓冲）**: {peak.get('recommended_capacity_weekend', 'N/A')}%")

            st.markdown("---")
            st.subheader("💡 扩容建议")
            recs = report['recommendations']

            urgency_color = risk_colors[recs['urgency']]
            st.markdown(f"""
            <div style="background-color: {urgency_color}20; padding: 10px; border-radius: 5px; margin-bottom: 10px;">
                <strong>紧急程度:</strong> <span style="color: {urgency_color};">{recs['urgency'].upper()}</span> |
                <strong>风险等级:</strong> <span style="color: {risk_colors[recs['risk_level']]};">{recs['risk_level'].upper()}</span>
            </div>
            """, unsafe_allow_html=True)

            for rec in recs['recommendations']:
                emoji = {'immediate': '🔴', 'urgent': '🟠', 'capacity': '🟡', 'trend': '🔵', 'maintenance': '🟢'}
                st.markdown(f"""
                {emoji.get(rec['type'], '📌')} **优先级 {rec['priority']}**: {rec['action']}
                - 原因: {rec['reason']}
                - 影响: {rec['impact']}
                """)

            cost = recs['estimated_cost']
            st.markdown("---")
            st.subheader("💰 成本估算")
            col_cost1, col_cost2, col_cost3 = st.columns(3)
            with col_cost1:
                st.metric("当前月成本", f"¥{cost['monthly_current']}")
            with col_cost2:
                st.metric("建议月成本", f"¥{cost['monthly_proposed']}",
                         f"+¥{cost['monthly_increase']}")
            with col_cost3:
                st.metric("年增加成本", f"¥{cost['annual_increase']}")

            if cost['scaling_factor_percent'] > 0:
                st.info(f"建议扩容比例: {cost['scaling_factor_percent']}%（含{safety_buffer}%安全缓冲）")

            if 'safety_buffer_cost' in cost:
                st.caption(f"安全缓冲额外成本: ¥{cost['safety_buffer_cost']}/月")

        st.markdown("---")

elif page == "⚙️ 自动扩容":
    st.header("⚙️ 自动扩容集成")

    st.info(
        "基于预测结果自动触发资源扩容，提前应对预期的负载高峰。"
        "支持冷却机制避免频繁调整，可配置缩扩容步长和阈值。"
    )

    st.markdown("---")

    col_status1, col_status2, col_status3 = st.columns(3)
    for idx, (resource_type, res_config) in enumerate(config.resources.items()):
        policy = auto_scaler.policies[resource_type]
        current_cap = auto_scaler.current_capacity[resource_type]
        efficiency = auto_scaler.get_resource_efficiency_score(forecasts[resource_type], resource_type)
        in_cooldown = auto_scaler._is_in_cooldown(resource_type)
        cooldown_remaining = auto_scaler._get_cooldown_remaining(resource_type)

        cap_color = '#2ecc71' if efficiency >= 70 else ('#f1c40f' if efficiency >= 40 else '#e74c3c')
        with [col_status1, col_status2, col_status3][idx]:
            st.markdown(f"""
            <div class="metric-card" style="border-left: 5px solid {cap_color};">
                <h3>{res_config.name}</h3>
                <h2 style="color: {cap_color};">{current_cap:.0f}%</h2>
                <p>效率评分: <span style="color: {cap_color}; font-weight: bold;">{efficiency:.1f}</span></p>
                <p>状态: <span style="color: {'#e74c3c' if in_cooldown else '#2ecc71'};">
                    {'冷却中' if in_cooldown else '正常'}
                </span></p>
                {f'<p>冷却剩余: {cooldown_remaining}分钟</p>' if in_cooldown else ''}
            </div>
            """, unsafe_allow_html=True)

    st.markdown("---")

    st.subheader("📋 扩容计划")
    current_values = {r: df[r].iloc[-1] for r in config.resources.keys()}
    scaling_plan = auto_scaler.get_scaling_plan(forecasts, current_values, prediction_hours)

    pending_actions = scaling_plan['actions']
    if pending_actions:
        st.warning(f"⚠️ 检测到 {len(pending_actions)} 个待执行的扩容操作")
        for action in pending_actions:
            action_color = '#e74c3c' if action.action_type == 'scale_up' else (
                '#2ecc71' if action.action_type == 'scale_down' else '#f1c40f')
            action_label = {'scale_up': '⬆️ 扩容', 'scale_down': '⬇️ 缩容', 'cooldown': '⏸️ 冷却'}
            st.markdown(f"""
            <div class="metric-card" style="border-left: 5px solid {action_color};">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <div>
                        <h4 style="margin: 0;">{action_label.get(action.action_type, action.action_type)} - {config.resources[action.resource_type].name}</h4>
                        <p style="margin: 5px 0;">{action.reason}</p>
                        <p style="margin: 5px 0; color: #666;">
                            {action.current_capacity:.0f}% → {action.target_capacity:.0f}%
                            ({'+' if action.change_percent > 0 else ''}{action.change_percent:.1f}%)
                        </p>
                    </div>
                    <div>
                        <button class="stButton">执行</button>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.success("✅ 当前无需扩容操作，所有资源运行在最优容量")

    st.markdown("---")

    for resource_type, summary in scaling_plan['summary'].items():
        res_config = config.resources[resource_type]
        with st.expander(f"📊 {res_config.name} - 扩容详情", expanded=False):
            col1, col2 = st.columns(2)
            with col1:
                st.write(f"- **当前容量**: {summary['current_capacity']:.0f}%")
                st.write(f"- **预测峰值**: {summary['max_predicted']:.1f}%")
                st.write(f"- **有效峰值百分比**: {summary['effective_max_percent']:.1f}%")
                st.write(f"- **冷却中**: {'是' if summary['in_cooldown'] else '否'}")
            with col2:
                st.write(f"- **将触发扩容**: {'是' if summary['will_scale_up'] else '否'}")
                st.write(f"- **将触发缩容**: {'是' if summary['will_scale_down'] else '否'}")
                if summary['cooldown_remaining'] is not None:
                    st.write(f"- **冷却剩余**: {summary['cooldown_remaining']} 分钟")

    st.markdown("---")

    st.subheader("📜 扩容历史记录")
    history_df = auto_scaler.get_scaling_history_df(limit=20)
    if len(history_df) > 0:
        st.dataframe(history_df, use_container_width=True, hide_index=True)
    else:
        st.info("暂无扩容历史记录")

    st.markdown("---")

    st.subheader("⚡ 模拟自动扩容")
    if st.button("运行 24 小时自动扩容模拟"):
        with st.spinner("正在模拟..."):
            simulation = auto_scaler.simulate_auto_scaling(df, forecasts, 24)

            sim_col1, sim_col2, sim_col3 = st.columns(3)
            with sim_col1:
                st.metric("扩容操作次数", simulation['total_scale_ups'])
            with sim_col2:
                st.metric("缩容操作次数", simulation['total_scale_downs'])
            with sim_col3:
                total_changes = simulation['total_scale_ups'] + simulation['total_scale_downs']
                st.metric("总调整次数", total_changes)

            st.markdown("#### 容量变化")
            timeline_df = pd.DataFrame([
                {'时间': t['timestamp'], 'CPU': t['capacity']['cpu'],
                 '内存': t['capacity']['memory'], '磁盘': t['capacity']['disk']}
                for t in simulation['timeline']
            ])
            fig_sim = px.line(timeline_df, x='时间', y=['CPU', '内存', '磁盘'],
                              title='24小时模拟容量变化')
            fig_sim.update_layout(template=config.plotly_template)
            st.plotly_chart(fig_sim, use_container_width=True)

            auto_scaler.reset()

    st.markdown("---")
    st.subheader("🔧 扩容策略配置")
    for resource_type, res_config in config.resources.items():
        with st.expander(f"{res_config.name} 策略", expanded=False):
            policy = auto_scaler.policies[resource_type]
            col_p1, col_p2 = st.columns(2)
            with col_p1:
                enabled = st.checkbox("启用自动扩容", value=policy.enabled,
                                     key=f"enable_{resource_type}")
                scale_up_th = st.number_input("扩容阈值(%)", min_value=50.0, max_value=95.0,
                                              value=policy.scale_up_threshold,
                                              key=f"up_th_{resource_type}")
                scale_up_step = st.number_input("扩容步长(%)", min_value=5.0, max_value=50.0,
                                                value=policy.scale_up_step,
                                                key=f"up_step_{resource_type}")
                min_inst = st.number_input("最小实例数", min_value=1, max_value=5,
                                          value=policy.min_instances,
                                          key=f"min_inst_{resource_type}")
            with col_p2:
                cooldown = st.number_input("冷却时间(分钟)", min_value=5, max_value=120,
                                           value=policy.cooldown_minutes,
                                           key=f"cooldown_{resource_type}")
                scale_down_th = st.number_input("缩容阈值(%)", min_value=10.0, max_value=50.0,
                                                value=policy.scale_down_threshold,
                                                key=f"down_th_{resource_type}")
                scale_down_step = st.number_input("缩容步长(%)", min_value=5.0, max_value=30.0,
                                                  value=policy.scale_down_step,
                                                  key=f"down_step_{resource_type}")
                max_inst = st.number_input("最大实例数", min_value=1, max_value=20,
                                          value=policy.max_instances,
                                          key=f"max_inst_{resource_type}")
            if st.button("更新策略", key=f"update_policy_{resource_type}"):
                auto_scaler.update_policy(
                    resource_type,
                    enabled=enabled,
                    scale_up_threshold=scale_up_th,
                    scale_down_threshold=scale_down_th,
                    scale_up_step=scale_up_step,
                    scale_down_step=scale_down_step,
                    cooldown_minutes=cooldown,
                    min_instances=min_inst,
                    max_instances=max_inst
                )
                st.success(f"{res_config.name} 策略已更新！")

elif page == "🔗 资源竞争":
    st.header("🔗 跨应用资源竞争分析")

    st.info(
        "分析多个应用之间的资源使用相关性，识别资源竞争风险，"
        "为应用隔离和容量分配提供依据。"
    )

    st.markdown("---")

    st.subheader("📱 应用列表")
    apps_df = pd.DataFrame([
        {'应用ID': app.app_id, '应用名称': app.name, '优先级': app.priority,
         'SLA': f"{app.sla_requirement}%", '描述': app.description,
         '标签': ', '.join(app.tags)}
        for app in app_manager.apps.values()
    ])
    st.table(apps_df)

    st.markdown("---")

    st.subheader("📊 资源使用雷达图")
    radar_df = app_manager.get_resource_contention_radar(df)

    fig_radar = go.Figure()
    app_colors = ['#3498DB', '#9B59B6', '#E67E22', '#1ABC9C', '#F39C12']

    for idx, row in radar_df.iterrows():
        fig_radar.add_trace(go.Scatterpolar(
            r=[row['cpu'], row['memory'], row['disk']],
            theta=['CPU', '内存', '磁盘'],
            fill='toself',
            name=row['app_name'],
            line=dict(color=app_colors[idx % len(app_colors)]),
            opacity=0.6
        ))

    fig_radar.update_layout(
        polar=dict(radialaxis=dict(visible=True, range=[0, 100])),
        title="各应用资源使用分布",
        template=config.plotly_template
    )
    st.plotly_chart(fig_radar, use_container_width=True)

    st.markdown("---")

    selected_resource = st.selectbox(
        "选择资源类型查看相关性",
        list(config.resources.keys()),
        format_func=lambda x: config.resources[x].name
    )

    col_comp1, col_comp2 = st.columns(2)

    with col_comp1:
        st.subheader("🔗 相关性矩阵")
        corr_matrix = app_manager.calculate_cross_app_correlation(df, selected_resource)
        fig_corr = px.imshow(
            corr_matrix,
            text_auto=True,
            color_continuous_scale='RdBu_r',
            title=f'{config.resources[selected_resource].name} - 应用间相关性',
            zmin=-1, zmax=1
        )
        fig_corr.update_layout(template=config.plotly_template)
        st.plotly_chart(fig_corr, use_container_width=True)

    with col_comp2:
        st.subheader("⚠️ 资源竞争检测")
        competitions = app_manager.detect_resource_competition(df, selected_resource)

        if competitions:
            for comp in competitions:
                severity_color = '#e74c3c' if comp.impact_score >= 0.8 else (
                    '#f1c40f' if comp.impact_score >= 0.6 else '#3498db')
                app1_name = app_manager.apps[comp.competing_apps[0]].name
                app2_name = app_manager.apps[comp.competing_apps[1]].name

                st.markdown(f"""
                <div class="metric-card" style="border-left: 5px solid {severity_color}; margin-bottom: 10px;">
                    <h5 style="margin: 0 0 5px 0;">{app1_name} ↔ {app2_name}</h5>
                    <p style="margin: 2px 0;"><strong>相关系数:</strong> {comp.correlation:.3f}</p>
                    <p style="margin: 2px 0;"><strong>影响评分:</strong> {comp.impact_score:.3f}</p>
                    <p style="margin: 5px 0 0 0; font-size: 14px;">{comp.recommendation}</p>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.success("✅ 未检测到明显的资源竞争")

    st.markdown("---")

    st.subheader("📈 水位影响分析")
    impact_analysis = app_manager.analyze_app_water_level_impact(df, forecast_summaries)

    for resource_type, impact in impact_analysis.items():
        res_config = config.resources[resource_type]
        with st.expander(f"{res_config.name} - 影响分析", expanded=True):
            col_i1, col_i2, col_i3 = st.columns(3)
            with col_i1:
                st.metric("整体使用率", f"{impact['overall_utilization']:.1f}%")
            with col_i2:
                warn_icon = "⚠️" if impact['will_exceed_warning'] else "✅"
                st.metric(f"{warn_icon} 超警告", "是" if impact['will_exceed_warning'] else "否")
            with col_i3:
                crit_icon = "🔴" if impact['will_exceed_critical'] else "✅"
                st.metric(f"{crit_icon} 超危险", "是" if impact['will_exceed_critical'] else "否")

            if impact['high_risk_applications']:
                st.warning(f"高风险应用: {', '.join([app_manager.apps[a].name for a in impact['high_risk_applications']])}")

            st.markdown("**各应用资源使用:**")
            usage_data = []
            for app_id, usage in impact['app_resource_usage'].items():
                usage_data.append({
                    '应用名称': usage['app_name'],
                    '优先级': usage['priority'],
                    '分配比例(%)': usage['share'] * 100,
                    '平均使用率(%)': usage['mean'],
                    '峰值使用率(%)': usage['peak'],
                    '最大使用率(%)': usage['max']
                })
            st.table(pd.DataFrame(usage_data))

    st.markdown("---")
    st.subheader("🎯 建议资源分配")
    total_resources = {r: 100.0 for r in config.resources.keys()}
    allocation = app_manager.simulate_resource_allocation(total_resources, df)

    alloc_data = []
    for app_id, resources in allocation.items():
        row = {'应用': app_manager.apps[app_id].name}
        for r, v in resources.items():
            row[f'{config.resources[r].name}(%)'] = v
        alloc_data.append(row)
    st.table(pd.DataFrame(alloc_data))

elif page == "📉 资源优化":
    st.header("📉 资源优化与闲置识别")

    st.info(
        "自动识别闲置资源和过度配置，提供降配建议，优化资源利用率，降低成本。"
        "闲置检测基于最近72小时的使用数据，阈值20%。"
    )

    st.markdown("---")

    with st.spinner("正在分析资源使用情况..."):
        opt_report = resource_optimizer.generate_optimization_report(df, forecast_summaries)

    idle_resources = opt_report['idle_resources']
    suggestions = opt_report['suggestions']
    opt_summary = opt_report['summary']

    col_opt1, col_opt2, col_opt3, col_opt4 = st.columns(4)
    with col_opt1:
        st.metric("优化建议总数", opt_summary['total_suggestions'])
    with col_opt2:
        st.metric("高优先级", opt_summary['high_priority_count'], delta_color="inverse")
    with col_opt3:
        st.metric("闲置资源数", len(idle_resources))
    with col_opt4:
        st.metric("预计总节省", f"{opt_summary['estimated_total_savings_percent']:.1f}%")

    st.markdown("---")

    if idle_resources:
        st.subheader("🔴 闲置资源检测")
        for idle in idle_resources:
            severity_colors = {'critical': '#e74c3c', 'high': '#e67e22', 'medium': '#f1c40f'}
            color = severity_colors.get(idle.severity, '#95a5a6')

            st.markdown(f"""
            <div class="metric-card" style="border-left: 5px solid {color}; margin-bottom: 10px;">
                <div style="display: flex; justify-content: space-between; align-items: flex-start;">
                    <div style="flex: 1;">
                        <h4 style="margin: 0 0 8px 0;">{idle.app_name} - {config.resources[idle.resource_type].name}</h4>
                        <p style="margin: 2px 0;">
                            <strong>严重程度:</strong> <span style="color: {color};">{idle.severity.upper()}</span> |
                            <strong>闲置时长:</strong> {idle.idle_hours:.0f}小时
                        </p>
                        <p style="margin: 2px 0;">
                            <strong>均值/峰值/最大:</strong> {idle.avg_usage:.1f}% / {idle.peak_usage:.1f}% / {idle.max_usage:.1f}%
                        </p>
                        <p style="margin: 2px 0;">
                            <strong>当前配置:</strong> {idle.current_allocation:.1f}% →
                            <strong>建议配置:</strong> <span style="color: #2ecc71;">{idle.suggested_allocation:.1f}%</span>
                            <strong>(可节省 {idle.potential_savings_percent:.1f}%)</strong>
                        </p>
                        <p style="margin: 8px 0 0 0; font-size: 14px;">{idle.recommendation}</p>
                    </div>
                    <div style="margin-left: 20px;">
                        <button class="stButton">应用建议</button>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("---")

    st.subheader("💡 优化建议")

    category_names = {
        'idle_resource': '🔴 闲置资源',
        'over_provisioned': '🟡 过度配置',
        'scheduling': '🔵 调度优化',
        'storage': '💾 存储优化',
        'network': '🌐 网络优化'
    }

    for category in ['idle_resource', 'over_provisioned', 'scheduling', 'storage', 'network']:
        category_sug = [s for s in suggestions if s.category == category]
        if category_sug:
            with st.expander(f"{category_names.get(category, category)} ({len(category_sug)}条)", expanded=True):
                for sug in category_sug:
                    priority_color = '#e74c3c' if sug.priority == 1 else (
                        '#e67e22' if sug.priority == 2 else '#2ecc71')
                    effort_label = {'low': '低', 'medium': '中', 'high': '高'}

                    col_s1, col_s2 = st.columns([3, 1])
                    with col_s1:
                        st.markdown(f"""
                        <div style="padding: 10px; border-left: 3px solid {priority_color}; margin: 5px 0;">
                            <p style="margin: 0; font-weight: bold;">
                                [优先级 {sug.priority}] {sug.description}
                            </p>
                            <p style="margin: 5px 0 0 0; color: #666; font-size: 14px;">
                                {sug.expected_impact}
                                | 实施难度: {effort_label.get(sug.implementation_effort, sug.implementation_effort)}
                            </p>
                        </div>
                        """, unsafe_allow_html=True)
                    with col_s2:
                        st.metric("预计节省", f"{sug.estimated_savings:.1f}%")

    st.markdown("---")

    st.subheader("📊 资源使用分布")
    usage_dist = resource_optimizer.get_resource_usage_distribution(df)
    st.dataframe(usage_dist, use_container_width=True, hide_index=True)

    st.markdown("---")

    st.subheader("📈 各应用资源使用对比")
    all_app_data = app_manager.generate_all_apps_data(df)

    selected_resource_for_chart = st.selectbox(
        "选择资源类型",
        list(config.resources.keys()),
        format_func=lambda x: config.resources[x].name,
        key="opt_resource_chart"
    )

    fig_box = px.box(
        all_app_data, x='app_name', y=selected_resource_for_chart,
        color='app_name',
        title=f'各应用{config.resources[selected_resource_for_chart].name}分布',
        labels={'app_name': '应用名称',
                selected_resource_for_chart: '使用率(%)'}
    )
    fig_box.update_layout(template=config.plotly_template, showlegend=False)
    st.plotly_chart(fig_box, use_container_width=True)

elif page == "📊 数据详情":
    st.header("📊 数据详情与统计")

    st.subheader("📋 原始数据预览")
    st.dataframe(
        df.sort_values('ds', ascending=False).head(100),
        use_container_width=True,
        hide_index=True
    )

    st.markdown("---")

    st.subheader("📈 统计信息")
    col1, col2, col3 = st.columns(3)

    for idx, (resource_type, res_config) in enumerate(config.resources.items()):
        stats = calculate_statistics(df[resource_type])
        with [col1, col2, col3][idx]:
            st.markdown(f"**{res_config.name}**")
            st.write(f"- 平均值: {stats['mean']}%")
            st.write(f"- 中位数: {stats['median']}%")
            st.write(f"- 最大值: {stats['max']}%")
            st.write(f"- 最小值: {stats['min']}%")
            st.write(f"- 标准差: {stats['std']}%")
            st.write(f"- P95: {stats['p95']}%")
            st.write(f"- P99: {stats['p99']}%")

    st.markdown("---")

    st.subheader("📉 资源分布直方图")
    selected_resource = st.selectbox(
        "选择资源",
        list(config.resources.keys()),
        format_func=lambda x: config.resources[x].name,
        key="hist_select"
    )

    fig_hist = px.histogram(
        df, x=selected_resource, nbins=50,
        color_discrete_sequence=[config.color_palette[selected_resource]],
        title=f"{config.resources[selected_resource].name} - 分布直方图",
        marginal="box"
    )
    fig_hist.update_layout(
        xaxis_title=f"使用率 (%)",
        yaxis_title="频数",
        template=config.plotly_template
    )
    st.plotly_chart(fig_hist, use_container_width=True)

    st.markdown("---")

    st.subheader("🔄 资源相关性分析")
    corr_matrix = df[['cpu', 'memory', 'disk']].corr()
    fig_corr = px.imshow(
        corr_matrix,
        text_auto=True,
        color_continuous_scale='RdBu_r',
        title='资源使用相关性热力图',
        zmin=-1, zmax=1
    )
    fig_corr.update_layout(template=config.plotly_template)
    st.plotly_chart(fig_corr, use_container_width=True)

st.markdown("---")
st.caption(f"📊 服务器资源水位预测系统 | 数据更新时间: {format_timestamp(datetime.now())}")
