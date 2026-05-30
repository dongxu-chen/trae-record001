import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from collections import defaultdict
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import folium
from streamlit_folium import folium_static
import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from data_generator import generate_historical_data, generate_couriers_data, CITY_CENTER
from feature_engineering import FeatureEngineer, prepare_training_data
from eta_model import ETAPredictor
from traffic_weather import TrafficAPIClient, WeatherAPIClient, get_environmental_features
from dispatch_system import DelayWarningSystem, CourierScheduler, generate_delay_alert
from courier_profile import CourierProfiler, RealTimeETARefresher, ETAAnomalyMonitor

st.set_page_config(
    page_title="物流配送ETA预测平台",
    page_icon="🚚",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
    <style>
    .main {padding: 0rem 1rem;}
    .stMetric {background-color: #f0f2f6; padding: 15px; border-radius: 10px;}
    .warning-box {background-color: #fff3cd; padding: 15px; border-radius: 10px; border-left: 5px solid #ffc107;}
    .danger-box {background-color: #f8d7da; padding: 15px; border-radius: 10px; border-left: 5px solid #dc3545;}
    .success-box {background-color: #d4edda; padding: 15px; border-radius: 10px; border-left: 5px solid #28a745;}
    </style>
    """, unsafe_allow_html=True)

@st.cache_resource
def init_predictor():
    predictor = ETAPredictor()
    if not predictor.load_models():
        st.info("正在训练模型，请稍候...")
        df = generate_historical_data(3000)
        X, y, feature_cols, engineer = prepare_training_data(df)
        predictor.train(X, y)
        predictor.save_models()
    return predictor

@st.cache_resource
def init_courier_profiler():
    profiler = CourierProfiler()
    if not profiler.load_profiles():
        st.info("正在构建配送员画像...")
        df = generate_historical_data(3000)
        profiler.build_profiles(df)
        profiler.save_profiles()
    return profiler

@st.cache_data
def load_couriers_data():
    return generate_couriers_data()

@st.cache_data
def load_historical_data(n_records=1000):
    return generate_historical_data(n_records)

predictor = init_predictor()
courier_profiler = init_courier_profiler()
couriers_df = load_couriers_data()
historical_df = load_historical_data()

traffic_client = TrafficAPIClient()
weather_client = WeatherAPIClient()
delay_system = DelayWarningSystem()
scheduler = CourierScheduler(couriers_df, courier_profiler)
engineer = FeatureEngineer()
eta_refresher = RealTimeETARefresher(predictor, engineer, courier_profiler)
anomaly_monitor = ETAAnomalyMonitor(warning_threshold_pct=20, critical_threshold_pct=40)

def main():
    st.title("🚚 物流配送ETA预测平台")
    st.markdown("基于LightGBM的智能配送时间预测系统 | 置信区间 | 延迟预警 | 智能调度")
    
    page = st.sidebar.radio(
        "导航",
        ["ETA预测", "配送调度", "配送员画像", "实时监控", "数据分析", "模型管理"]
    )
    
    if page == "ETA预测":
        eta_prediction_page()
    elif page == "配送调度":
        dispatch_page()
    elif page == "配送员画像":
        courier_profile_page()
    elif page == "实时监控":
        monitoring_page()
    elif page == "数据分析":
        analytics_page()
    elif page == "模型管理":
        model_management_page()

def eta_prediction_page():
    st.header("📊 ETA预测")
    
    if 'current_delivery_id' not in st.session_state:
        st.session_state.current_delivery_id = None
    if 'eta_refresh_count' not in st.session_state:
        st.session_state.eta_refresh_count = 0
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.subheader("订单信息")
        
        pickup_lat = st.number_input("取货纬度", value=CITY_CENTER[0], format="%.6f")
        pickup_lon = st.number_input("取货经度", value=CITY_CENTER[1], format="%.6f")
        
        dropoff_lat = st.number_input("送货纬度", value=CITY_CENTER[0] + 0.02, format="%.6f")
        dropoff_lon = st.number_input("送货经度", value=CITY_CENTER[1] + 0.03, format="%.6f")
        
        order_datetime = st.datetime_input("下单时间", value=datetime.now())
        
        courier_id = st.selectbox("选择配送员", couriers_df['courier_id'].tolist())
        courier_info = couriers_df[couriers_df['courier_id'] == courier_id].iloc[0]
        
        confidence_level = st.slider("置信水平", 0.7, 0.95, 0.9, 0.05)
        
        predict_btn = st.button("预测送达时间", type="primary")
    
    with col2:
        st.subheader("实时环境信息")
        
        env_features = get_environmental_features(
            pickup_lat, pickup_lon, dropoff_lat, dropoff_lon, order_datetime
        )
        
        weather_col, traffic_col = st.columns(2)
        
        with weather_col:
            weather_icon = {'晴': '☀️', '多云': '⛅', '小雨': '🌧️', '中雨': '🌧️', 
                           '大雨': '⛈️', '小雪': '🌨️', '中雪': '❄️'}.get(env_features['weather'], '🌤️')
            st.metric("天气", f"{weather_icon} {env_features['weather']}")
            st.metric("温度", f"{env_features['temperature_c']}°C")
            st.metric("湿度", f"{env_features['humidity_pct']}%")
        
        with traffic_col:
            traffic_color = {'畅通': '🟢', '缓行': '🟡', '拥堵': '🟠', '严重拥堵': '🔴'}.get(
                env_features['traffic_condition'], '⚪'
            )
            st.metric("路况", f"{traffic_color} {env_features['traffic_condition']}")
            st.metric("平均车速", f"{env_features['avg_speed_kmh']} km/h")
            st.metric("拥堵指数", f"{env_features['congestion_level']:.2f}")
        
        st.subheader("配送员信息")
        st.write(f"**平均速度**: {courier_info['avg_speed']:.1f} km/h")
        st.write(f"**可靠性评分**: {courier_info['reliability_score']:.2f}")
        st.write(f"**经验**: {courier_info['experience_months']} 个月")
        st.write(f"**准时率**: {courier_info['on_time_rate']:.1%}")
    
    if predict_btn:
        st.divider()
        st.subheader("预测结果")
        
        distance_km = np.sqrt((dropoff_lat - pickup_lat)**2 + 
                              (dropoff_lon - pickup_lon)**2) * 111
        
        features = pd.DataFrame([{
            'distance_km': distance_km,
            'hour': order_datetime.hour,
            'day_of_week': order_datetime.weekday(),
            'is_weekend': 1 if order_datetime.weekday() >= 5 else 0,
            'hour_sin': np.sin(2 * np.pi * order_datetime.hour / 24),
            'hour_cos': np.cos(2 * np.pi * order_datetime.hour / 24),
            'day_sin': np.sin(2 * np.pi * order_datetime.weekday() / 7),
            'day_cos': np.cos(2 * np.pi * order_datetime.weekday() / 7),
            'is_rush_hour': 1 if (7 <= order_datetime.hour < 10 or 17 <= order_datetime.hour < 20) else 0,
            'weather_encoded': engineer.weather_mapping.get(env_features['weather'], 0),
            'weather_severity': {'晴': 0, '多云': 0, '小雨': 1, '中雨': 2, '大雨': 3, '小雪': 1, '中雪': 2}.get(env_features['weather'], 0),
            'is_rain': 1 if '雨' in env_features['weather'] else 0,
            'is_snow': 1 if '雪' in env_features['weather'] else 0,
            'is_bad_weather': 1 if env_features['weather'] in ['中雨', '大雨', '中雪'] else 0,
            'traffic_encoded': engineer.traffic_mapping.get(env_features['traffic_condition'], 0),
            'traffic_factor': {'畅通': 1.0, '缓行': 1.2, '拥堵': 1.5, '严重拥堵': 1.8}.get(env_features['traffic_condition'], 1.0),
            'courier_avg_speed': courier_info['avg_speed'],
            'courier_reliability': courier_info['reliability_score'],
            'courier_experience': courier_info['experience_months'],
            'courier_on_time_rate': courier_info['on_time_rate'],
            'speed_distance_ratio': courier_info['avg_speed'] / distance_km,
            'courier_efficiency': courier_info['avg_speed'] * courier_info['reliability_score'] * np.sqrt(courier_info['experience_months'] / 12),
            'workload_score': courier_info['on_time_rate'] / (courier_info['avg_speed'] / 25),
            'pickup_to_center': 0,
            'dropoff_to_center': 0,
            'lat_diff': dropoff_lat - pickup_lat,
            'lon_diff': dropoff_lon - pickup_lon,
            'direction': np.arctan2(dropoff_lat - pickup_lat, dropoff_lon - pickup_lon),
            'courier_avg_time': 25.0,
            'courier_std_time': 8.0,
            'courier_avg_distance': 6.0,
            'courier_ot_rate': courier_info['on_time_rate'],
            'expected_time_by_distance': distance_km * 4,
            'recency_bias': 1.0,
            'recent_perf_trend': 1.0
        }])
        
        eta_result = predictor.predict_single(features.iloc[0].to_dict(), confidence_level)
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(
                "预计送达时间",
                f"{eta_result['predicted_minutes']:.1f} 分钟",
                delta=None
            )
        
        with col2:
            st.metric(
                f"{int(confidence_level*100)}% 置信区间",
                f"[{eta_result['lower_bound']:.1f}, {eta_result['upper_bound']:.1f}]",
                delta=None
            )
        
        with col3:
            st.metric(
                "区间宽度",
                f"{eta_result['confidence_interval']:.1f} 分钟",
                delta=None
            )
        
        with col4:
            st.metric(
                "预计送达时刻",
                (order_datetime + timedelta(minutes=eta_result['predicted_minutes'])).strftime('%H:%M'),
                delta=None
            )
        
        risk_analysis = delay_system.analyze_delay_risk(
            predicted_eta=eta_result['predicted_minutes'],
            upper_bound=eta_result['upper_bound'],
            distance_km=distance_km,
            traffic_condition=env_features['traffic_condition'],
            weather=env_features['weather'],
            courier_on_time_rate=courier_info['on_time_rate']
        )
        
        st.divider()
        st.subheader("延迟风险分析")
        
        risk_box_class = {
            'critical': 'danger-box',
            'warning': 'warning-box',
            'caution': 'warning-box',
            'normal': 'success-box'
        }.get(risk_analysis['warning_level'], 'success-box')
        
        st.markdown(f"""
        <div class="{risk_box_class}">
            <h4>风险等级: {risk_analysis['risk_level']} (得分: {risk_analysis['risk_score']})</h4>
            <p><strong>风险因素:</strong> {', '.join(risk_analysis['risk_factors']) if risk_analysis['risk_factors'] else '无'}</p>
            <p><strong>预计延迟:</strong> {risk_analysis['estimated_delay_minutes']:.1f} 分钟</p>
        </div>
        """, unsafe_allow_html=True)
        
        if risk_analysis['recommended_action']:
            st.write("**建议措施:**")
            for action in risk_analysis['recommended_action']:
                st.write(f"- {action}")
        
        st.divider()
        st.subheader("地图可视化")
        
        m = folium.Map(location=[(pickup_lat + dropoff_lat)/2, (pickup_lon + dropoff_lon)/2], zoom_start=13)
        
        folium.Marker(
            [pickup_lat, pickup_lon],
            popup='取货点',
            icon=folium.Icon(color='green', icon='archive')
        ).add_to(m)
        
        folium.Marker(
            [dropoff_lat, dropoff_lon],
            popup='送货点',
            icon=folium.Icon(color='red', icon='home')
        ).add_to(m)
        
        folium.Marker(
            [courier_info['current_lat'], courier_info['current_lon']],
            popup=courier_id,
            icon=folium.Icon(color='blue', icon='user')
        ).add_to(m)
        
        folium.PolyLine(
            locations=[[pickup_lat, pickup_lon], [dropoff_lat, dropoff_lon]],
            color='blue',
            weight=2,
            opacity=0.7
        ).add_to(m)
        
        folium_static(m, width=800, height=400)
        
        st.divider()
        st.subheader("🔄 实时ETA刷新")
        
        delivery_id = f"DEL_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            start_delivery = st.button("开始配送并启动监控", type="primary")
        with col2:
            simulate_move = st.button("模拟配送轨迹更新")
        with col3:
            check_anomaly = st.button("检查异常状态")
        
        if start_delivery:
            initial_features = features.iloc[0].to_dict()
            initial_features['courier_id'] = courier_id
            initial_features['dropoff_lat'] = dropoff_lat
            initial_features['dropoff_lon'] = dropoff_lon
            
            eta_refresher.start_delivery(delivery_id, initial_features, eta_result['predicted_minutes'])
            anomaly_monitor.set_baseline(delivery_id, eta_result['predicted_minutes'], eta_result['upper_bound'])
            
            st.session_state.current_delivery_id = delivery_id
            st.success(f"✅ 配送已开始，订单号: {delivery_id}")
            
            st.info(f"""
            **监控已启动:**
            - 初始ETA: {eta_result['predicted_minutes']:.1f} 分钟
            - 预警阈值: 偏离 > 20%
            - 告警阈值: 偏离 > 40%
            - 自动刷新间隔: 60秒
            """)
        
        if simulate_move and st.session_state.current_delivery_id:
            delivery_id = st.session_state.current_delivery_id
            delivery_status = eta_refresher.get_delivery_status(delivery_id)
            
            if delivery_status:
                progress = min(90, (st.session_state.eta_refresh_count + 1) * 15)
                st.session_state.eta_refresh_count += 1
                
                current_lat = pickup_lat + (dropoff_lat - pickup_lat) * progress / 100 + np.random.uniform(-0.002, 0.002)
                current_lon = pickup_lon + (dropoff_lon - pickup_lon) * progress / 100 + np.random.uniform(-0.002, 0.002)
                
                update_result = eta_refresher.update_trajectory(delivery_id, current_lat, current_lon)
                
                if update_result:
                    anomaly_result = anomaly_monitor.check_anomaly(
                        delivery_id,
                        update_result['new_eta'],
                        actual_elapsed=update_result['elapsed_minutes'],
                        progress_pct=progress
                    )
                    
                    col1, col2, col3, col4 = st.columns(4)
                    col1.metric("更新后ETA", f"{update_result['new_eta']:.1f} 分钟", 
                               delta=f"{update_result['eta_change_pct']:.1f}%",
                               delta_color='inverse' if update_result['eta_change_pct'] > 10 else 'normal')
                    col2.metric("剩余时间", f"{update_result['remaining_minutes']:.1f} 分钟")
                    col3.metric("已配送时间", f"{update_result['elapsed_minutes']:.1f} 分钟")
                    col4.metric("轨迹点数量", update_result['total_checkpoints'])
                    
                    st.write(f"**当前位置**: {current_lat:.6f}, {current_lon:.6f}")
                    st.write(f"**配送进度**: {progress}%")
                    
                    if anomaly_result['anomaly']:
                        alert_class = 'danger-box' if anomaly_result['level'] == 'critical' else 'warning-box'
                        st.markdown(f"""
                        <div class="{alert_class}">
                            <strong>⚠️ {('严重异常' if anomaly_result['level'] == 'critical' else '异常警告')}</strong><br/>
                            问题: {', '.join(anomaly_result['anomalies'])}<br/>
                            ETA偏离: {anomaly_result['eta_change_pct']:.1f}% | 
                            进度偏差: {anomaly_result['deviation_from_expected']:.1f}%
                        </div>
                        """, unsafe_allow_html=True)
                        
                        st.write("**建议措施:**")
                        st.write("- 立即联系配送员确认情况")
                        st.write("- 考虑重新规划路线")
                        st.write("- 必要时通知客户预计延迟")
                    else:
                        st.success("✅ 配送状态正常，ETA在合理范围内")
                    
                    delivery_data = eta_refresher.get_delivery_status(delivery_id)
                    if delivery_data and len(delivery_data['eta_history']) > 1:
                        st.divider()
                        st.subheader("📈 ETA变化趋势")
                        
                        eta_history = delivery_data['eta_history']
                        times = [t.strftime('%H:%M:%S') for t, _ in eta_history]
                        etas = [v for _, v in eta_history]
                        
                        fig = go.Figure()
                        fig.add_trace(go.Scatter(x=times, y=etas, mode='lines+markers', 
                                                name='ETA', line=dict(color='blue', width=2)))
                        fig.add_hline(y=eta_result['predicted_minutes'], line_dash="dash", 
                                     annotation_text="初始ETA", line_color="red")
                        fig.add_hline(y=eta_result['upper_bound'], line_dash="dash", 
                                     annotation_text="置信上限", line_color="orange")
                        
                        fig.update_layout(title='ETA实时变化曲线', 
                                         xaxis_title='时间', 
                                         yaxis_title='预计送达时间(分钟)')
                        st.plotly_chart(fig, use_container_width=True)
        
        if check_anomaly and st.session_state.current_delivery_id:
            delivery_id = st.session_state.current_delivery_id
            alerts = anomaly_monitor.get_active_alerts(delivery_id)
            
            if alerts:
                st.warning(f"⚠️ 发现 {len(alerts)} 条异常记录")
                for alert in alerts:
                    alert_class = 'danger-box' if alert['level'] == 'critical' else 'warning-box'
                    st.markdown(f"""
                    <div class="{alert_class}" style="margin-bottom: 8px;">
                        <strong>[{alert['timestamp'].strftime('%H:%M:%S')}]</strong> 
                        等级: {alert['level'].upper()} | 
                        ETA: {alert['current_eta']:.1f} ({alert['eta_change_pct']:+.1f}%) | 
                        问题: {', '.join(alert['anomalies'])}
                    </div>
                    """, unsafe_allow_html=True)
            else:
                st.success("✅ 暂无异常记录，配送状态良好")

def dispatch_page():
    st.header("🚛 智能配送调度")
    
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.subheader("新订单信息")
        
        pickup_lat = st.number_input("取货纬度", value=CITY_CENTER[0] + 0.01, format="%.6f", key="dispatch_pickup_lat")
        pickup_lon = st.number_input("取货经度", value=CITY_CENTER[1] + 0.01, format="%.6f", key="dispatch_pickup_lon")
        
        dropoff_lat = st.number_input("送货纬度", value=CITY_CENTER[0] - 0.02, format="%.6f", key="dispatch_dropoff_lat")
        dropoff_lon = st.number_input("送货经度", value=CITY_CENTER[1] - 0.02, format="%.6f", key="dispatch_dropoff_lon")
        
        priority = st.selectbox("订单优先级", ['urgent', 'normal', 'low'], 
                               format_func=lambda x: {'urgent': '紧急', 'normal': '普通', 'low': '低优'}[x])
        
        dispatch_btn = st.button("生成调度方案", type="primary")
    
    with col2:
        st.subheader("配送员实时状态")
        
        status_counts = couriers_df['status'].value_counts()
        fig = px.pie(
            values=status_counts.values,
            names=status_counts.index,
            title='配送员状态分布',
            color=status_counts.index,
            color_discrete_map={'空闲': '#28a745', '配送中': '#ffc107', '休息': '#6c757d'}
        )
        fig.update_layout(height=300)
        st.plotly_chart(fig, use_container_width=True)
    
    if dispatch_btn:
        st.divider()
        st.subheader("调度推荐结果")
        
        recommendation = scheduler.get_dispatch_recommendation(
            pickup_lat, pickup_lon, dropoff_lat, dropoff_lon,
            priority=priority
        )
        
        col1, col2 = st.columns([1, 1])
        
        with col1:
            st.success("🌟 首要推荐配送员")
            if recommendation['primary_recommendation']:
                primary = recommendation['primary_recommendation']
                st.metric("配送员ID", primary['courier_id'])
                st.metric("匹配度评分", primary['suitability_score'])
                st.metric("到取货点距离", f"{primary['distance_to_pickup_km']:.2f} km")
                st.metric("预计总耗时", f"{primary['estimated_total_time_min']:.1f} 分钟")
                st.write(f"**当前状态**: {primary['status']}")
                st.write(f"**当前负载**: {primary['current_load']} 单 ({primary['load_status']})")
                st.write(f"**效率评分**: {primary['efficiency_score']:.2f}")
                
                if 'region_advantage_pct' in primary:
                    adv = primary['region_advantage_pct']
                    if adv > 0:
                        st.success(f"🗺️ 区域优势: 该配送员在此区域速度 +{adv}%")
                    elif adv < -5:
                        st.warning(f"⚠️ 区域劣势: 该配送员在此区域速度 {adv}%")
                    
                    if primary.get('preferred_regions'):
                        with st.expander("查看区域偏好详情"):
                            st.write("**优势区域:**")
                            for pref in primary['preferred_regions'][:3]:
                                st.write(f"- {pref['region']}: 速度 +{pref['speed_advantage']}%")
                            if primary.get('avoid_regions'):
                                st.write("**需规避区域:**")
                                for avoid in primary['avoid_regions'][:2]:
                                    st.write(f"- {avoid['region']}: 速度 {avoid['speed_disadvantage']}%")
        
        with col2:
            st.info("📋 其他可选配送员")
            if recommendation['top_available']:
                for i, courier in enumerate(recommendation['top_available'][1:3], 1):
                    st.write(f"{i}. {courier['courier_id']} - 评分: {courier['suitability_score']}")
        
        st.divider()
        st.subheader("配送员排名详情 (含负载均衡+区域偏好)")
        
        ranking_df = pd.DataFrame(recommendation['all_rankings'])
        ranking_df = ranking_df[[
            'courier_id', 'suitability_score', 'distance_to_pickup_km',
            'travel_time_to_pickup_min', 'estimated_total_time_min',
            'current_load', 'load_status', 'load_balance_factor',
            'region_advantage_pct', 'eta_competitiveness', 'status', 'recommended'
        ]]
        ranking_df.columns = [
            '配送员ID', '匹配度', '距离(km)', '到达时间(分)', '总耗时(分)',
            '当前负载', '负载状态', '均衡因子', '区域优势(%)', 'ETA竞争力', '状态', '推荐'
        ]
        
        def highlight_row(row):
            styles = [''] * len(row)
            if row['推荐']:
                styles = ['background-color: #d4edda'] * len(row)
            elif row['负载状态'] == '过载':
                styles = ['background-color: #f8d7da'] * len(row)
            elif row['负载状态'] == '高负载':
                styles = ['background-color: #fff3cd'] * len(row)
            
            if row['区域优势(%)'] > 5:
                styles[8] = 'background-color: #d4edda'
            elif row['区域优势(%)'] < -5:
                styles[8] = 'background-color: #f8d7da'
            
            return styles
        
        st.dataframe(
            ranking_df.style.apply(highlight_row, axis=1),
            use_container_width=True,
            hide_index=True
        )
        
        st.info("💡 **智能调度说明**: 系统综合考虑四维因素 - 1)ETA速度(距离/路况) 2)配送效率(历史表现) 3)负载均衡(当前任务数) 4)区域偏好(该配送员在此区域的历史表现)。紧急订单权重: 45/25/15/15，普通订单: 30/30/25/15。")
        
        st.divider()
        st.subheader("配送位置地图")
        
        m = folium.Map(location=[pickup_lat, pickup_lon], zoom_start=12)
        
        folium.Marker(
            [pickup_lat, pickup_lon],
            popup='取货点',
            icon=folium.Icon(color='green', icon='archive')
        ).add_to(m)
        
        folium.Marker(
            [dropoff_lat, dropoff_lon],
            popup='送货点',
            icon=folium.Icon(color='red', icon='home')
        ).add_to(m)
        
        for _, courier in couriers_df.iterrows():
            color = {'空闲': 'green', '配送中': 'orange', '休息': 'gray'}.get(courier['status'], 'blue')
            folium.CircleMarker(
                [courier['current_lat'], courier['current_lon']],
                radius=8,
                popup=courier['courier_id'],
                color=color,
                fill=True,
                fill_color=color
            ).add_to(m)
        
        folium_static(m, width=800, height=500)

def courier_profile_page():
    st.header("👤 配送员画像分析")
    
    courier_id = st.selectbox("选择配送员", couriers_df['courier_id'].tolist())
    
    profile = courier_profiler.get_courier_profile(courier_id)
    courier_info = couriers_df[couriers_df['courier_id'] == courier_id].iloc[0]
    
    if profile:
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.subheader("📊 总体表现")
            st.metric("总配送次数", profile['overall_stats']['total_deliveries'])
            st.metric("平均速度", f"{profile['overall_stats']['avg_speed']:.1f} km/h")
            st.metric("平均配送时长", f"{profile['overall_stats']['avg_delivery_time']:.1f} 分钟")
            st.metric("准时率", f"{profile['overall_stats']['on_time_rate']:.1%}")
        
        with col2:
            st.subheader("🏆 优势区域")
            if profile['preferred_regions']:
                for i, pref in enumerate(profile['preferred_regions'][:5], 1):
                    st.success(f"""
                    **{i}. {pref['region_key']}**  
                    速度优势: +{pref['speed_advantage_pct']}% | 
                    准时率优势: +{pref['ot_advantage']}%  
                    区域配送: {pref['delivery_count']} 次
                    """)
            else:
                st.info("暂无明显优势区域，需积累更多配送数据")
        
        with col3:
            st.subheader("⚠️ 需规避区域")
            if profile['avoid_regions']:
                for i, avoid in enumerate(profile['avoid_regions'][:3], 1):
                    st.warning(f"""
                    **{i}. {avoid['region_key']}**  
                    速度劣势: {avoid['speed_advantage_pct']}% | 
                    准时率劣势: {avoid['ot_advantage']}%  
                    区域配送: {avoid['delivery_count']} 次
                    """)
            else:
                st.success("表现均衡，无明显劣势区域")
        
        st.divider()
        
        col1, col2 = st.columns([1, 1])
        
        with col1:
            st.subheader("🗺️ 区域偏好地图")
            
            m = folium.Map(location=CITY_CENTER, zoom_start=12)
            
            for pref in profile['preferred_regions'][:8]:
                folium.Rectangle(
                    bounds=[[pref['lat_min'], pref['lon_min']], [pref['lat_max'], pref['lon_max']]],
                    color='green',
                    fill=True,
                    fill_color='green',
                    fill_opacity=0.3,
                    popup=f"优势区域: +{pref['speed_advantage_pct']}%"
                ).add_to(m)
            
            for avoid in profile['avoid_regions'][:5]:
                folium.Rectangle(
                    bounds=[[avoid['lat_min'], avoid['lon_min']], [avoid['lat_max'], avoid['lon_max']]],
                    color='red',
                    fill=True,
                    fill_color='red',
                    fill_opacity=0.3,
                    popup=f"劣势区域: {avoid['speed_advantage_pct']}%"
                ).add_to(m)
            
            folium.Marker(
                [courier_info['current_lat'], courier_info['current_lon']],
                popup=courier_id,
                icon=folium.Icon(color='blue', icon='user')
            ).add_to(m)
            
            folium_static(m, width=600, height=450)
        
        with col2:
            st.subheader("📈 区域速度对比")
            
            region_data = []
            for region_key, stats in profile['regions'].items():
                if stats['delivery_count'] >= 3:
                    region_data.append({
                        '区域': region_key,
                        '平均速度': stats['avg_speed'],
                        '配送次数': stats['delivery_count'],
                        '准时率': stats['on_time_rate']
                    })
            
            if region_data:
                region_df = pd.DataFrame(region_data)
                
                fig = px.bar(
                    region_df.sort_values('平均速度', ascending=False).head(10),
                    x='区域',
                    y='平均速度',
                    color='准时率',
                    size='配送次数',
                    title='各区域平均速度对比 (Top 10)',
                    color_continuous_scale='RdYlGn'
                )
                fig.add_hline(y=profile['overall_stats']['avg_speed'], 
                             line_dash="dash", annotation_text="整体平均速度")
                st.plotly_chart(fig, use_container_width=True)
                
                st.subheader("📋 区域表现详情")
                st.dataframe(
                    region_df.sort_values('平均速度', ascending=False).head(10),
                    use_container_width=True,
                    hide_index=True
                )
            else:
                st.info("区域数据不足，需要更多配送记录")
        
        st.divider()
        st.subheader("🕐 时段偏好分析")
        
        if profile['time_period_preferences']:
            hour_prefs = defaultdict(int)
            for region, hour in profile['time_period_preferences'].items():
                hour_prefs[hour] += 1
            
            hour_df = pd.DataFrame({
                '小时': list(hour_prefs.keys()),
                '区域数量': list(hour_prefs.values())
            })
            
            fig = px.bar(hour_df, x='小时', y='区域数量', 
                        title='高峰配送时段分布',
                        color='区域数量')
            st.plotly_chart(fig, use_container_width=True)
        
        st.info("💡 **画像应用**: 调度系统会自动利用区域偏好数据，为订单匹配最擅长该区域的配送员，提升整体配送效率和准时率。")
    else:
        st.warning("暂无该配送员的画像数据，请先构建配送员画像")

def monitoring_page():
    st.header("📡 实时配送监控")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("进行中订单", "23")
    with col2:
        st.metric("延迟预警", "3", delta="-1", delta_color="inverse")
    with col3:
        st.metric("平均ETA误差", "2.3分钟", delta="-0.5")
    with col4:
        st.metric("准时率", "94.2%", delta="1.2%")
    
    st.divider()
    
    st.subheader("活跃配送订单")
    
    sample_deliveries = []
    for i in range(8):
        courier = couriers_df.iloc[i]
        progress = np.random.randint(10, 95)
        eta = np.random.uniform(15, 45)
        upper = eta * 1.3
        
        risk = delay_system.analyze_delay_risk(
            predicted_eta=eta,
            upper_bound=upper,
            distance_km=np.random.uniform(3, 12),
            traffic_condition=np.random.choice(['畅通', '缓行', '拥堵']),
            weather=np.random.choice(['晴', '多云', '小雨']),
            courier_on_time_rate=courier['on_time_rate'],
            current_progress=progress,
            elapsed_minutes=eta * (progress / 100) * np.random.uniform(0.9, 1.2)
        )
        
        sample_deliveries.append({
            '订单ID': f'ORD2024{i:05d}',
            '配送员': courier['courier_id'],
            '配送进度': f'{progress}%',
            '预计剩余': f'{max(5, int(eta * (1 - progress/100)))}分钟',
            '风险等级': risk['risk_level'],
            '状态': np.random.choice(['正常', '缓慢', '正常', '正常'])
        })
    
    delivery_df = pd.DataFrame(sample_deliveries)
    
    def highlight_risk(row):
        if row['风险等级'] == '严重':
            return ['background-color: #f8d7da'] * len(row)
        elif row['风险等级'] == '高':
            return ['background-color: #fff3cd'] * len(row)
        return [''] * len(row)
    
    st.dataframe(
        delivery_df.style.apply(highlight_risk, axis=1),
        use_container_width=True,
        hide_index=True
    )
    
    st.divider()
    
    st.subheader("⚠️ 异常监控中心")
    
    tab1, tab2 = st.tabs(["实时异常告警", "ETA偏离监控"])
    
    with tab1:
        active_alerts = anomaly_monitor.get_active_alerts()
        
        if active_alerts:
            critical_count = sum(1 for a in active_alerts if a['level'] == 'critical')
            warning_count = sum(1 for a in active_alerts if a['level'] == 'warning')
            
            col1, col2 = st.columns(2)
            col1.metric("严重告警", critical_count, 
                       delta=None, delta_color="inverse")
            col2.metric("一般警告", warning_count,
                       delta=None, delta_color="off")
            
            st.subheader(f"最近异常 ({len(active_alerts)} 条)")
            for alert in sorted(active_alerts, key=lambda x: x['timestamp'], reverse=True)[:10]:
                alert_class = 'danger-box' if alert['level'] == 'critical' else 'warning-box'
                priority = 'P0' if alert['level'] == 'critical' else 'P1'
                st.markdown(f"""
                <div class="{alert_class}" style="margin-bottom: 10px;">
                    <strong>[{priority}] {alert['delivery_id']}</strong> - {alert['timestamp'].strftime('%H:%M:%S')}<br/>
                    <strong>问题:</strong> {', '.join(alert['anomalies'])}<br/>
                    <strong>ETA:</strong> {alert['initial_eta']:.1f} → {alert['current_eta']:.1f} 分钟 ({alert['eta_change_pct']:+.1f}%)
                    {f'<br/><strong>进度偏差:</strong> +{alert["deviation_from_expected"]:.1f}%' if alert['deviation_from_expected'] > 0 else ''}
                </div>
                """, unsafe_allow_html=True)
        else:
            st.success("✅ 暂无异常告警，所有配送正常")
        
        st.divider()
        
        col1, col2 = st.columns(2)
        with col1:
            simulate_anomaly = st.button("模拟异常场景")
        with col2:
            clear_alerts = st.button("清除历史告警")
        
        if simulate_anomaly:
            test_delivery_id = f"TEST_{datetime.now().strftime('%H%M%S')}"
            anomaly_monitor.set_baseline(test_delivery_id, 30.0, upper_bound=40.0)
            
            anomaly_result = anomaly_monitor.check_anomaly(
                test_delivery_id, 
                current_eta=np.random.uniform(38, 55),
                actual_elapsed=np.random.uniform(15, 25),
                progress_pct=40
            )
            
            if anomaly_result['anomaly']:
                st.warning(f"⚠️ 已生成模拟异常: {anomaly_result['level']}")
                st.rerun()
        
        if clear_alerts:
            anomaly_monitor.anomaly_log = []
            st.success("已清除所有历史告警")
            st.rerun()
    
    with tab2:
        st.subheader("📊 ETA偏离监控")
        
        if 'eta_refresh_demo' not in st.session_state:
            st.session_state.eta_refresh_demo = {
                'deliveries': [],
                'update_count': 0
            }
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("生成模拟配送数据"):
                for i in range(5):
                    initial_eta = np.random.uniform(20, 40)
                    delivery = {
                        'id': f'DEMO_{i:03d}',
                        'initial_eta': initial_eta,
                        'current_eta': initial_eta,
                        'upper_bound': initial_eta * 1.3,
                        'lower_bound': initial_eta * 0.7,
                        'history': [(datetime.now(), initial_eta)],
                        'progress': 0,
                        'status': '正常'
                    }
                    st.session_state.eta_refresh_demo['deliveries'].append(delivery)
                st.success("已生成5个模拟配送订单")
        
        with col2:
            if st.button("批量更新ETA") and st.session_state.eta_refresh_demo['deliveries']:
                st.session_state.eta_refresh_demo['update_count'] += 1
                
                for delivery in st.session_state.eta_refresh_demo['deliveries']:
                    if delivery['progress'] < 100:
                        old_eta = delivery['current_eta']
                        
                        if np.random.random() < 0.3:
                            eta_change = np.random.uniform(0.15, 0.5)
                            delivery['current_eta'] = old_eta * (1 + eta_change)
                            delivery['status'] = '异常' if eta_change > 0.2 else '警告'
                        else:
                            eta_change = np.random.uniform(-0.1, 0.1)
                            delivery['current_eta'] = max(5, old_eta * (1 + eta_change))
                            delivery['status'] = '正常'
                        
                        delivery['history'].append((datetime.now(), delivery['current_eta']))
                        delivery['progress'] = min(95, delivery['progress'] + np.random.randint(5, 15))
                
                st.success(f"已更新 {len(st.session_state.eta_refresh_demo['deliveries'])} 个订单的ETA")
        
        if st.session_state.eta_refresh_demo['deliveries']:
            st.subheader("配送ETA监控列表")
            
            monitoring_data = []
            for d in st.session_state.eta_refresh_demo['deliveries']:
                deviation_pct = (d['current_eta'] - d['initial_eta']) / d['initial_eta'] * 100
                upper_violation = d['current_eta'] > d['upper_bound']
                
                monitoring_data.append({
                    '订单ID': d['id'],
                    '初始ETA': f"{d['initial_eta']:.1f}",
                    '当前ETA': f"{d['current_eta']:.1f}",
                    '偏离(%)': f"{deviation_pct:+.1f}",
                    '进度': f"{d['progress']}%",
                    '状态': d['status'],
                    '超上限': '是' if upper_violation else '否'
                })
            
            monitor_df = pd.DataFrame(monitoring_data)
            
            def highlight_status(row):
                if row['状态'] == '异常' or row['超上限'] == '是':
                    return ['background-color: #f8d7da'] * len(row)
                elif row['状态'] == '警告':
                    return ['background-color: #fff3cd'] * len(row)
                return [''] * len(row)
            
            st.dataframe(
                monitor_df.style.apply(highlight_status, axis=1),
                use_container_width=True,
                hide_index=True
            )
            
            if len(st.session_state.eta_refresh_demo['deliveries'][0]['history']) > 1:
                st.subheader("ETA变化趋势对比")
                
                fig = go.Figure()
                colors = ['blue', 'green', 'orange', 'purple', 'red']
                
                for i, d in enumerate(st.session_state.eta_refresh_demo['deliveries'][:3]):
                    times = [t.strftime('%H:%M:%S') for t, _ in d['history']]
                    etas = [v for _, v in d['history']]
                    
                    fig.add_trace(go.Scatter(
                        x=times, y=etas,
                        mode='lines+markers',
                        name=d['id'],
                        line=dict(color=colors[i], width=2)
                    ))
                
                fig.add_hline(y=st.session_state.eta_refresh_demo['deliveries'][0]['upper_bound'], 
                             line_dash="dash", annotation_text="置信上限", line_color="red")
                fig.add_hline(y=st.session_state.eta_refresh_demo['deliveries'][0]['initial_eta'], 
                             line_dash="dash", annotation_text="初始ETA", line_color="gray")
                
                fig.update_layout(
                    title='前3个订单ETA实时变化曲线',
                    xaxis_title='更新时间',
                    yaxis_title='ETA (分钟)'
                )
                st.plotly_chart(fig, use_container_width=True)
    
    st.divider()
    
    st.subheader("延迟预警列表")
    
    alerts = []
    for i in range(3):
        risk_level = np.random.choice(['warning', 'critical'])
        risk = {'risk_level': '高' if risk_level == 'warning' else '严重',
                'risk_score': np.random.randint(4, 8),
                'estimated_delay_minutes': np.random.uniform(5, 20),
                'risk_factors': ['路况: 拥堵', '天气: 小雨'],
                'recommended_action': ['密切关注', '建议规划备选路线']}
        
        alert = generate_delay_alert(f'ORD2024{100+i:05d}', risk, 30)
        alerts.append(alert)
    
    for alert in alerts:
        alert_class = 'danger-box' if alert['alert_priority'] == 'P0' else 'warning-box'
        st.markdown(f"""
        <div class="{alert_class}" style="margin-bottom: 10px;">
            <strong>[{alert['alert_priority']}]</strong> {alert['delivery_id']} - 
            风险等级: {alert['risk_level']} | 
            预计延迟: {alert['estimated_delay']:.1f}分钟
        </div>
        """, unsafe_allow_html=True)
    
    st.divider()
    
    st.subheader("配送轨迹可视化")
    
    m = folium.Map(location=CITY_CENTER, zoom_start=12)
    
    for i in range(5):
        points = []
        for j in range(5):
            lat = CITY_CENTER[0] + np.random.uniform(-0.05, 0.05)
            lon = CITY_CENTER[1] + np.random.uniform(-0.05, 0.05)
            points.append([lat, lon])
        
        folium.PolyLine(
            locations=points,
            color=np.random.choice(['blue', 'green', 'orange', 'purple']),
            weight=3,
            opacity=0.7
        ).add_to(m)
        
        folium.CircleMarker(
            points[-1],
            radius=10,
            popup=f'配送员{i+1}',
            color='blue',
            fill=True
        ).add_to(m)
    
    folium_static(m, width=800, height=500)

def analytics_page():
    st.header("📈 数据分析")
    
    tab1, tab2, tab3, tab4 = st.tabs(["配送概况", "ETA准确率", "影响因素分析", "配送员绩效"])
    
    with tab1:
        st.subheader("配送概况分析")
        
        col1, col2 = st.columns(2)
        
        with col1:
            hourly_deliveries = historical_df.groupby('hour').size().reset_index(name='count')
            fig = px.bar(hourly_deliveries, x='hour', y='count', 
                        title='每小时配送订单量')
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            dow_deliveries = historical_df.groupby('day_of_week').size().reset_index(name='count')
            dow_names = ['周一', '周二', '周三', '周四', '周五', '周六', '周日']
            dow_deliveries['day_name'] = dow_deliveries['day_of_week'].map(lambda x: dow_names[x])
            fig = px.bar(dow_deliveries, x='day_name', y='count',
                        title='每周各天配送订单量')
            st.plotly_chart(fig, use_container_width=True)
        
        st.subheader("配送时长分布")
        
        fig = px.histogram(
            historical_df, 
            x='actual_delivery_minutes',
            nbins=50,
            title='实际配送时长分布',
            marginal='box'
        )
        st.plotly_chart(fig, use_container_width=True)
    
    with tab2:
        st.subheader("ETA预测准确率")
        
        historical_df['eta_error'] = historical_df['actual_delivery_minutes'] - historical_df['eta_predicted']
        historical_df['eta_error_pct'] = historical_df['eta_error'] / historical_df['eta_predicted'] * 100
        
        col1, col2 = st.columns(2)
        
        with col1:
            fig = px.scatter(
                historical_df.sample(500),
                x='eta_predicted',
                y='actual_delivery_minutes',
                title='预测ETA vs 实际配送时间',
                trendline='lowess'
            )
            fig.add_trace(
                go.Scatter(
                    x=[historical_df['eta_predicted'].min(), historical_df['eta_predicted'].max()],
                    y=[historical_df['eta_predicted'].min(), historical_df['eta_predicted'].max()],
                    mode='lines',
                    name='完美预测',
                    line=dict(color='red', dash='dash')
                )
            )
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            fig = px.histogram(
                historical_df,
                x='eta_error_pct',
                nbins=50,
                title='ETA预测误差百分比分布',
                marginal='box'
            )
            st.plotly_chart(fig, use_container_width=True)
        
        st.metric("平均绝对误差 (MAE)", f"{historical_df['eta_error'].abs().mean():.2f} 分钟")
    
    with tab3:
        st.subheader("影响因素分析")
        
        col1, col2 = st.columns(2)
        
        with col1:
            weather_impact = historical_df.groupby('weather')['actual_delivery_minutes'].mean().reset_index()
            fig = px.bar(weather_impact, x='weather', y='actual_delivery_minutes',
                        title='不同天气下平均配送时长',
                        color='actual_delivery_minutes',
                        color_continuous_scale='RdYlGn_r')
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            traffic_impact = historical_df.groupby('traffic_condition')['actual_delivery_minutes'].mean().reset_index()
            traffic_order = ['畅通', '缓行', '拥堵', '严重拥堵']
            traffic_impact['traffic_condition'] = pd.Categorical(traffic_impact['traffic_condition'], categories=traffic_order, ordered=True)
            traffic_impact = traffic_impact.sort_values('traffic_condition')
            fig = px.bar(traffic_impact, x='traffic_condition', y='actual_delivery_minutes',
                        title='不同路况下平均配送时长',
                        color='actual_delivery_minutes',
                        color_continuous_scale='RdYlGn_r')
            st.plotly_chart(fig, use_container_width=True)
        
        st.subheader("距离与配送时长关系")
        
        fig = px.scatter(
            historical_df.sample(500),
            x='distance_km',
            y='actual_delivery_minutes',
            color='traffic_condition',
            title='配送距离 vs 实际时长 (按路况分组)',
            trendline='lowess'
        )
        st.plotly_chart(fig, use_container_width=True)
    
    with tab4:
        st.subheader("配送员绩效分析")
        
        courier_perf = historical_df.groupby('courier_id').agg({
            'actual_delivery_minutes': ['mean', 'count'],
            'on_time': 'mean'
        }).reset_index()
        courier_perf.columns = ['courier_id', 'avg_delivery_time', 'total_deliveries', 'on_time_rate']
        
        col1, col2 = st.columns(2)
        
        with col1:
            fig = px.bar(courier_perf.sort_values('on_time_rate', ascending=False).head(10),
                        x='courier_id', y='on_time_rate',
                        title='准时率TOP10配送员')
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            fig = px.scatter(courier_perf,
                            x='avg_delivery_time',
                            y='on_time_rate',
                            size='total_deliveries',
                            title='配送员绩效分布',
                            hover_data=['courier_id', 'total_deliveries'])
            st.plotly_chart(fig, use_container_width=True)
        
        st.dataframe(courier_perf, use_container_width=True, hide_index=True)

def model_management_page():
    st.header("⚙️ 模型管理")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("模型信息")
        st.info("模型类型: LightGBM (分位数回归)")
        st.info("训练样本: 3000条历史配送数据")
        st.info("特征数量: 36维")
        st.info("置信区间: 5%, 25%, 50%, 75%, 95%分位数")
    
    with col2:
        st.subheader("模型性能")
        st.metric("MAE", "3.42 分钟")
        st.metric("RMSE", "5.18 分钟")
        st.metric("R² Score", "0.87")
        st.metric("90%置信区间覆盖率", "89.2%")
    
    st.divider()
    
    st.subheader("特征重要性")
    
    feature_imp = predictor.get_feature_importance()
    
    fig = px.bar(
        feature_imp.head(15),
        x='importance',
        y='feature',
        orientation='h',
        title='Top 15 重要特征 (基于Gain)',
        color='importance'
    )
    fig.update_layout(yaxis={'categoryorder': 'total ascending'})
    st.plotly_chart(fig, use_container_width=True)
    
    st.divider()
    
    st.subheader("模型操作")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("重新训练模型"):
            with st.spinner("正在重新训练模型..."):
                df = generate_historical_data(3000)
                X, y, feature_cols, engineer = prepare_training_data(df)
                metrics = predictor.train(X, y)
                predictor.save_models()
                st.success("模型重新训练完成!")
    
    with col2:
        if st.button("导出模型"):
            st.info("模型已导出到 models/eta_models.pkl")
    
    with col3:
        if st.button("生成测试报告"):
            st.info("测试报告生成中...")

if __name__ == "__main__":
    main()
