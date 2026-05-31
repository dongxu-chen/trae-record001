import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
import os
import sys
import folium
from streamlit_folium import st_folium

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from data_generator import generate_all_data, BEIJING_CENTER
from feature_engineering import FeatureEngineer
from eta_model import ETAPredictor
from route_planner import RoutePlanner, Location
from time_series_forecast import TimeSeriesForecaster
from rider_recommender import RiderRecommender
from src.real_time_dispatcher import RealTimeDispatcher

st.set_page_config(
    page_title="外卖配送时间预测平台",
    page_icon="🛵",
    layout="wide"
)

@st.cache_resource
def load_or_generate_data():
    os.makedirs('data', exist_ok=True)
    os.makedirs('models', exist_ok=True)
    
    required_files = ['restaurants', 'riders', 'weather', 'traffic', 'orders']
    if not all(os.path.exists(f'data/{name}.csv') for name in required_files):
        with st.spinner('正在生成模拟数据...'):
            data = generate_all_data()
            for name, df in data.items():
                df.to_csv(f'data/{name}.csv', index=False, encoding='utf-8-sig')
    else:
        data = {
            'restaurants': pd.read_csv('data/restaurants.csv'),
            'riders': pd.read_csv('data/riders.csv'),
            'weather': pd.read_csv('data/weather.csv'),
            'traffic': pd.read_csv('data/traffic.csv'),
            'orders': pd.read_csv('data/orders.csv', parse_dates=['order_time'])
        }
    
    return data

@st.cache_resource
def train_models(_data):
    if os.path.exists('models/eta_model.pkl') and os.path.exists('models/feature_engineer.pkl'):
        fe = FeatureEngineer.load('models/feature_engineer.pkl')
        eta_model = ETAPredictor.load('models/eta_model.pkl')
        ts_forecaster = TimeSeriesForecaster()
        ts_forecaster.fit(_data['orders'])
    else:
        with st.spinner('正在训练模型...'):
            from feature_engineering import prepare_training_data
            from eta_model import train_and_save_model
            
            X, y, fe = prepare_training_data(_data['orders'])
            eta_model, metrics = train_and_save_model(X, y)
            fe.save('models/feature_engineer.pkl')
            
            ts_forecaster = TimeSeriesForecaster()
            ts_forecaster.fit(_data['orders'])
    
    return fe, eta_model, ts_forecaster

data = load_or_generate_data()
fe, eta_model, ts_forecaster = train_models(data)

route_planner = RoutePlanner()
rider_recommender = RiderRecommender()

if 'dispatcher' not in st.session_state:
    st.session_state.dispatcher = RealTimeDispatcher(update_interval_sec=10)
    st.session_state.dispatcher_active = False

dispatcher = st.session_state.dispatcher

st.title("🛵 外卖配送时间预测平台")
st.markdown("基于XGBoost + 路径规划 + 时序预测的智能配送预测系统")

tab1, tab2, tab3, tab4, tab5 = st.tabs(["📊 实时预测", "🗺️ 路径规划", "📈 时序预测", "👥 骑手推荐", "🚀 实时调度"])

with tab1:
    st.header("实时ETA预测")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("订单信息")
        
        restaurants = data['restaurants']
        restaurant_names = restaurants['name'].tolist()
        selected_restaurant = st.selectbox("选择餐厅", restaurant_names)
        
        rest_info = restaurants[restaurants['name'] == selected_restaurant].iloc[0]
        
        food_types = ['快餐', '中餐', '西餐', '日料', '火锅', '烧烤']
        food_type = st.selectbox("餐品类型", food_types, 
                               index=food_types.index(rest_info['food_type']))
        
        prep_time = st.slider("预计备餐时间(分钟)", 5, 45, int(rest_info['avg_prep_time']))
        
        st.info(f"🏪 餐厅信息 | 准时率: {rest_info['historical_on_time_rate']:.1%} | "
                f"累计订单: {rest_info['total_orders_completed']} | "
                f"{'新餐厅 ⚠️' if rest_info['is_new_restaurant'] else '成熟餐厅'}")
        
        st.subheader("配送地址")
        user_lat = st.number_input("用户纬度", value=BEIJING_CENTER[0] + 0.01, format="%.4f")
        user_lon = st.number_input("用户经度", value=BEIJING_CENTER[1] + 0.01, format="%.4f")
        
        floor = st.number_input("楼层", 1, 30, 5)
        has_elevator = st.checkbox("有电梯", value=True)
        is_office_building = st.checkbox("写字楼", value=False, 
                                        help="写字楼电梯等待时间通常更长")
        
        elevator_wait = 0
        if not has_elevator:
            elevator_wait = floor * 0.5
        else:
            if is_office_building:
                elevator_wait = min(floor * 0.15 + 1.5, 8)
            else:
                elevator_wait = min(floor * 0.1 + 1, 5)
    
    with col2:
        st.subheader("环境因素")
        
        order_hour = st.slider("下单时间", 0, 23, 12)
        is_peak_hour = 1 if (11 <= order_hour <= 13) or (17 <= order_hour <= 19) else 0
        
        weather_conditions = ['晴天', '多云', '小雨', '大雨', '雾', '雪']
        weather = st.selectbox("天气状况", weather_conditions)
        
        weather_impact_map = {
            '晴天': 1.0,
            '多云': 1.0,
            '小雨': 1.15,
            '大雨': 1.25,
            '雾': 1.20,
            '雪': 1.35
        }
        weather_impact = weather_impact_map[weather]
        
        traffic_level = st.slider("交通状况 (0=畅通, 1=拥堵)", 0.0, 1.0, 0.5)
        traffic_impact = 1 + traffic_level * 0.5
        
        st.subheader("餐厅特征修正")
        is_new_restaurant = st.checkbox("启用新餐厅偏差修正", 
                                       value=bool(rest_info['is_new_restaurant']),
                                       help="新餐厅备餐时间波动较大，需要额外预留时间")
        
        restaurant_on_time_rate = st.slider("餐厅历史准时率", 0.70, 1.00, 
                                           float(rest_info['historical_on_time_rate']),
                                           help="准时率越低，备餐时间需要预留越多")
    
    if st.button("预测送达时间", type="primary"):
        riders = data['riders']
        rider = riders.sample(1).iloc[0]
        
        distance_rider_to_rest = route_planner.calculate_distance(
            Location(rider['lat'], rider['lon']),
            Location(rest_info['lat'], rest_info['lon'])
        )
        distance_rest_to_user = route_planner.calculate_distance(
            Location(rest_info['lat'], rest_info['lon']),
            Location(user_lat, user_lon)
        )
        total_distance = distance_rider_to_rest + distance_rest_to_user
        
        is_weekend = datetime.now().weekday() >= 5
        
        adjusted_prep_time = prep_time
        if is_new_restaurant:
            adjusted_prep_time *= 1.2
            adjusted_prep_time += prep_time * (1 - restaurant_on_time_rate) * 0.5
        
        elevator_x_floor = elevator_wait * floor
        office_x_floor = int(is_office_building) * floor
        office_x_elevator = int(is_office_building) * (1 - int(has_elevator))
        prep_x_on_time_rate = adjusted_prep_time * (1 - restaurant_on_time_rate)
        on_time_x_peak = restaurant_on_time_rate * is_peak_hour
        new_rest_x_prep = int(is_new_restaurant) * adjusted_prep_time
        
        complexity_components = [
            weather_impact,
            traffic_impact,
            is_peak_hour * 0.3,
            (1 - int(has_elevator)) * 0.2,
            int(is_office_building) * 0.15,
            int(is_new_restaurant) * 0.2,
            (1 - restaurant_on_time_rate) * 0.25
        ]
        complexity_score = sum(complexity_components)
        
        input_data = pd.DataFrame([{
            'distance_km': total_distance,
            'distance_rest_to_user_km': distance_rest_to_user,
            'distance_rider_to_rest_km': distance_rider_to_rest,
            'prep_time_min': adjusted_prep_time,
            'elevator_wait_min': elevator_wait,
            'floor': floor,
            'has_elevator': int(has_elevator),
            'weather_impact': weather_impact,
            'traffic_impact': traffic_impact,
            'traffic_index': traffic_level,
            'order_hour': order_hour,
            'is_weekend': int(is_weekend),
            'is_peak_hour': is_peak_hour,
            'rider_avg_speed': rider['avg_speed'],
            'rider_experience_months': rider['experience'],
            'rider_rating': rider['rating'],
            'food_type_encoded': food_types.index(food_type),
            'weather_condition_encoded': weather_conditions.index(weather),
            'time_of_day_encoded': 2 if is_peak_hour else 1,
            'distance_x_weather': total_distance * weather_impact,
            'distance_x_traffic': total_distance * traffic_impact,
            'prep_x_peak': adjusted_prep_time * is_peak_hour,
            'elevator_x_floor': elevator_x_floor,
            'office_x_floor': office_x_floor,
            'office_x_elevator': office_x_elevator,
            'prep_x_on_time_rate': prep_x_on_time_rate,
            'on_time_x_peak': on_time_x_peak,
            'new_rest_x_prep': new_rest_x_prep,
            'is_new_restaurant': int(is_new_restaurant),
            'restaurant_on_time_rate': restaurant_on_time_rate,
            'is_office_building': int(is_office_building),
            'complexity_score': complexity_score
        }])
        
        eta_result = eta_model.predict_single(input_data)
        
        baseline_eta = prep_time + (total_distance / rider['avg_speed']) * 60 + elevator_wait
        delay_analysis = eta_model.analyze_delay_factors(input_data, eta_result['predicted_eta'], baseline_eta)
        
        st.markdown("---")
        
        result_col1, result_col2, result_col3 = st.columns(3)
        
        with result_col1:
            st.metric("预计送达时间", f"{eta_result['predicted_eta']} 分钟")
            st.caption(f"置信区间: {eta_result['lower_bound']} - {eta_result['upper_bound']} 分钟")
        
        with result_col2:
            st.metric("配送距离", f"{total_distance:.2f} km")
            st.caption(f"备餐: {prep_time}分钟 | 电梯等待: {elevator_wait:.1f}分钟")
        
        with result_col3:
            confidence = max(0, 100 - eta_result['confidence_range'] * 2)
            st.metric("预测置信度", f"{confidence:.0f}%")
            st.caption(f"预测范围: ±{eta_result['confidence_range']/2:.1f}分钟")
        
        st.markdown("---")
        st.subheader("📊 ETA置信区间可视化")
        
        fig = go.Figure()
        
        fig.add_trace(go.Indicator(
            mode="number+gauge",
            value=eta_result['predicted_eta'],
            domain={'x': [0, 1], 'y': [0, 1]},
            title={'text': "预计送达时间 (分钟)"},
            gauge={
                'shape': "bullet",
                'axis': {'range': [0, 60]},
                'threshold': {
                    'line': {'color': "red", 'width': 2},
                    'thickness': 0.75,
                    'value': 45
                },
                'steps': [
                    {'range': [0, eta_result['lower_bound']], 'color': "lightgray"},
                    {'range': [eta_result['lower_bound'], eta_result['upper_bound']], 'color': "gray"},
                    {'range': [eta_result['upper_bound'], 60], 'color': "lightgray"}
                ],
                'bar': {'color': "black", 'thickness': 0.3},
            }
        ))
        
        st.plotly_chart(fig, use_container_width=True)
        
        st.subheader("⏱️ 延迟因素分析")
        if delay_analysis['delay_reasons']:
            for reason in delay_analysis['delay_reasons']:
                st.info(f"⚠️ {reason}")
            
            if delay_analysis['feature_impact']:
                impact_df = pd.DataFrame({
                    '因素': list(delay_analysis['feature_impact'].keys()),
                    '延迟时间(分钟)': list(delay_analysis['feature_impact'].values())
                })
                
                fig = px.bar(impact_df, x='因素', y='延迟时间(分钟)',
                            title='各因素对延迟的影响',
                            color='延迟时间(分钟)',
                            color_continuous_scale='Reds')
                st.plotly_chart(fig, use_container_width=True)
        else:
            st.success("✅ 无显著延迟因素")

with tab2:
    st.header("路径规划")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("起点与终点")
        
        rider_lat = st.number_input("骑手纬度", value=BEIJING_CENTER[0] + 0.02, format="%.4f", key='rider_lat')
        rider_lon = st.number_input("骑手经度", value=BEIJING_CENTER[1] + 0.02, format="%.4f", key='rider_lon')
        
        restaurants = data['restaurants']
        rest_names = restaurants['name'].tolist()
        selected_rest = st.selectbox("选择餐厅", rest_names, key='route_rest')
        rest_info = restaurants[restaurants['name'] == selected_rest].iloc[0]
        
        user_lat_r = st.number_input("用户纬度", value=BEIJING_CENTER[0] - 0.01, format="%.4f", key='user_lat_r')
        user_lon_r = st.number_input("用户经度", value=BEIJING_CENTER[1] - 0.01, format="%.4f", key='user_lon_r')
        
        avg_speed = st.slider("平均速度(km/h)", 15, 40, 25, key='route_speed')
        traffic_factor = st.slider("交通系数", 1.0, 1.5, 1.1, key='route_traffic')
        weather_factor = st.slider("天气系数", 1.0, 1.4, 1.0, key='route_weather')
    
    with col2:
        st.subheader("配送路径")
        
        rider_loc = Location(rider_lat, rider_lon, "骑手")
        rest_loc = Location(rest_info['lat'], rest_info['lon'], selected_rest)
        user_loc = Location(user_lat_r, user_lon_r, "用户")
        
        route_result = route_planner.plan_delivery_route(
            rider_loc, rest_loc, user_loc, avg_speed, traffic_factor, weather_factor
        )
        
        m = folium.Map(location=[BEIJING_CENTER[0], BEIJING_CENTER[1]], zoom_start=13)
        
        folium.Marker([rider_lat, rider_lon], popup="骑手位置", 
                     icon=folium.Icon(color='blue', icon='motorcycle', prefix='fa')).add_to(m)
        folium.Marker([rest_info['lat'], rest_info['lon']], popup=selected_rest, 
                     icon=folium.Icon(color='orange', icon='utensils', prefix='fa')).add_to(m)
        folium.Marker([user_lat_r, user_lon_r], popup="用户", 
                     icon=folium.Icon(color='green', icon='home', prefix='fa')).add_to(m)
        
        route_coords = route_result['route_coordinates']
        folium.PolyLine(route_coords, color='red', weight=3, opacity=0.8).add_to(m)
        
        st_folium(m, height=400, use_container_width=True)
    
    st.markdown("---")
    
    stat1, stat2, stat3, stat4 = st.columns(4)
    stat1.metric("骑手到餐厅", f"{route_result['distance_rider_to_rest_km']} km", 
                f"{route_result['travel_time_rider_to_rest_min']} 分钟")
    stat2.metric("餐厅到用户", f"{route_result['distance_rest_to_user_km']} km",
                f"{route_result['travel_time_rest_to_user_min']} 分钟")
    stat3.metric("总距离", f"{route_result['total_distance_km']} km")
    stat4.metric("总行驶时间", f"{route_result['total_travel_time_min']} 分钟")

with tab3:
    st.header("时序预测")
    
    col1, col2 = st.columns(2)
    
    with col1:
        target_date = st.date_input("预测起始日期", datetime.now())
        hours_ahead = st.slider("预测小时数", 6, 48, 24)
    
    with col2:
        forecast_type = st.radio("预测类型", ["订单需求预测", "配送时长趋势"])
    
    if forecast_type == "订单需求预测":
        hourly_pred = ts_forecaster.predict_hourly_demand(target_date, hours_ahead)
        
        st.subheader("未来时段订单需求预测")
        
        fig = go.Figure()
        
        fig.add_trace(go.Bar(
            x=hourly_pred['timestamp'],
            y=hourly_pred['predicted_orders'],
            name='预测订单量',
            marker_color='rgba(55, 83, 109, 0.7)'
        ))
        
        fig.add_trace(go.Scatter(
            x=hourly_pred['timestamp'],
            y=hourly_pred['avg_delivery_time'],
            name='平均配送时间',
            yaxis='y2',
            line=dict(color='red', width=2)
        ))
        
        fig.update_layout(
            title='订单需求与配送时间预测',
            xaxis_title='时间',
            yaxis_title='订单数量',
            yaxis2=dict(
                title='配送时间(分钟)',
                overlaying='y',
                side='right'
            ),
            legend=dict(orientation='h', y=1.1)
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        st.subheader("详细预测数据")
        display_df = hourly_pred.copy()
        display_df['timestamp'] = display_df['timestamp'].dt.strftime('%Y-%m-%d %H:00')
        st.dataframe(display_df[['timestamp', 'predicted_orders', 'avg_delivery_time', 'is_weekend']],
                    use_container_width=True)
    
    else:
        daily_trend = ts_forecaster.predict_delivery_time_trend(target_date, 7)
        
        st.subheader("未来7天配送时长趋势")
        
        fig = go.Figure()
        
        fig.add_trace(go.Scatter(
            x=daily_trend['date'],
            y=daily_trend['avg_delivery_time'],
            name='平均配送时间',
            fill='tozeroy',
            line=dict(color='blue')
        ))
        
        fig.add_trace(go.Scatter(
            x=daily_trend['date'],
            y=daily_trend['peak_delivery_time'],
            name='高峰配送时间',
            line=dict(color='red', dash='dash')
        ))
        
        fig.update_layout(
            title='配送时长趋势预测',
            xaxis_title='日期',
            yaxis_title='配送时间(分钟)'
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        peak_hours = ts_forecaster.get_peak_hours()
        st.subheader("历史高峰时段分析")
        st.dataframe(peak_hours, use_container_width=True)

with tab4:
    st.header("骑手推荐")
    st.markdown("**多目标优化**: ETA + 负载均衡 + 服务质量")
    
    col1, col2 = st.columns(2)
    
    with col1:
        restaurants = data['restaurants']
        rest_names = restaurants['name'].tolist()
        selected_rest = st.selectbox("选择餐厅", rest_names, key='rider_rest')
        rest_info = restaurants[restaurants['name'] == selected_rest].iloc[0]
        
        user_lat_rec = st.number_input("用户纬度", value=BEIJING_CENTER[0] - 0.01, format="%.4f", key='rec_lat')
        user_lon_rec = st.number_input("用户经度", value=BEIJING_CENTER[1] - 0.01, format="%.4f", key='rec_lon')
        
        order_hour_rec = st.slider("下单时间", 0, 23, 12, key='rec_hour')
        prep_time_rec = st.slider("备餐时间", 5, 40, 20, key='rec_prep')
    
    with col2:
        weather_rec = st.selectbox("天气", weather_conditions, key='rec_weather')
        weather_impact_rec = weather_impact_map[weather_rec]
        
        traffic_rec = st.slider("交通状况", 0.0, 1.0, 0.3, key='rec_traffic')
        traffic_impact_rec = 1 + traffic_rec * 0.5
        
        top_k = st.slider("推荐数量", 3, 10, 5)
        
        st.subheader("目标权重设置")
        eta_weight = st.slider("ETA权重", 0.0, 1.0, 0.5, 0.05,
                              help="送达时间的重要程度")
        load_balance_weight = st.slider("负载均衡权重", 0.0, 1.0, 0.3, 0.05,
                                       help="骑手工作负载均衡的重要程度")
        quality_weight = st.slider("服务质量权重", 0.0, 1.0, 0.2, 0.05,
                                  help="骑手服务质量的重要程度")
    
    if st.button("推荐骑手", key='rec_button'):
        riders = data['riders']
        
        recommendations = rider_recommender.recommend_with_eta(
            riders,
            rest_info['lat'], rest_info['lon'],
            user_lat_rec, user_lon_rec,
            order_hour_rec, prep_time_rec,
            weather_impact_rec, traffic_impact_rec,
            top_k,
            eta_weight=eta_weight,
            load_balance_weight=load_balance_weight,
            quality_weight=quality_weight
        )
        
        st.subheader("🏆 推荐骑手列表")
        
        for idx, (_, rider) in enumerate(recommendations.iterrows(), 1):
            pareto_badge = " ⭐帕累托最优" if rider['is_pareto_optimal'] else ""
            with st.expander(f"#{idx} {rider['name']} - 预计ETA: {rider['total_eta_min']}分钟{pareto_badge}"):
                col_r1, col_r2, col_r3, col_r4 = st.columns(4)
                
                with col_r1:
                    st.metric("综合评分", f"{rider['composite_score']:.2f}")
                    st.metric("ETA评分", f"{rider['eta_score']:.2f}")
                
                with col_r2:
                    st.metric("负载均衡评分", f"{rider['load_balance_score']:.2f}")
                    st.metric("质量评分", f"{rider['quality_score_norm']:.2f}")
                
                with col_r3:
                    st.metric("距离餐厅", f"{rider['distance_km']} km")
                    st.metric("平均速度", f"{rider['avg_speed']} km/h")
                
                with col_r4:
                    st.metric("准时率", f"{rider['on_time_rate']:.1%}")
                    st.metric("当前订单", rider['current_orders'])
                
                st.caption(f"状态: {rider['status']} | 评分: {rider['rating']}⭐ | 经验: {rider['experience_months']}月")
        
        st.subheader("📊 多目标评分对比")
        
        plot_df = recommendations.melt(
            id_vars=['name'], 
            value_vars=['eta_score', 'load_balance_score', 'quality_score_norm'],
            var_name='指标', value_name='评分'
        )
        
        fig = px.bar(plot_df, x='name', y='评分', color='指标',
                    title='骑手多目标评分对比',
                    barmode='group',
                    color_discrete_map={
                        'eta_score': '#1f77b4',
                        'load_balance_score': '#2ca02c', 
                        'quality_score_norm': '#ff7f0e'
                    },
                    labels={'name': '骑手姓名'})
        st.plotly_chart(fig, use_container_width=True)
        
        st.subheader("⏱️ ETA对比")
        
        fig2 = px.bar(recommendations, x='name', y='total_eta_min',
                     title='骑手预计送达时间对比',
                     color='composite_score',
                     color_continuous_scale='Greens',
                     labels={'name': '骑手姓名', 'total_eta_min': '预计ETA(分钟)', 
                            'composite_score': '综合评分'},
                     text='total_eta_min')
        fig2.update_traces(texttemplate='%{text}分钟', textposition='outside')
        st.plotly_chart(fig2, use_container_width=True)
        
        st.subheader("📋 骑手工作负载统计")
        workload_stats = rider_recommender.get_rider_workload_stats(riders)
        
        stat_s1, stat_s2, stat_s3, stat_s4 = st.columns(4)
        stat_s1.metric("总骑手数", workload_stats['total_riders'])
        stat_s2.metric("空闲骑手", workload_stats['idle_riders'])
        stat_s3.metric("配送中", workload_stats['busy_riders'])
        stat_s4.metric("利用率", f"{workload_stats['utilization_rate']:.1%}")
        
        st.subheader("📈 工作负载分布")
        workload_dist = workload_stats['workload_distribution']
        dist_df = pd.DataFrame({
            '负载等级': list(workload_dist.keys()),
            '骑手数量': list(workload_dist.values())
        })
        fig3 = px.pie(dist_df, values='骑手数量', names='负载等级',
                      title='骑手工作负载分布')
        st.plotly_chart(fig3, use_container_width=True)

with tab5:
    st.header("🚀 实时调度系统")
    st.markdown("**顺路合并 + 实时ETA刷新 + 激励调度**")
    
    col_ctrl1, col_ctrl2, col_ctrl3 = st.columns(3)
    
    with col_ctrl1:
        if st.button("▶️ 启动调度系统" if not st.session_state.dispatcher_active else "⏹️ 停止调度系统",
                    type="primary"):
            if not st.session_state.dispatcher_active:
                dispatcher.start()
                st.session_state.dispatcher_active = True
                st.success("调度系统已启动")
            else:
                dispatcher.stop()
                st.session_state.dispatcher_active = False
                st.warning("调度系统已停止")
    
    with col_ctrl2:
        refresh_interval = st.slider("刷新间隔(秒)", 5, 60, 10,
                                    help="实时ETA刷新间隔")
    
    with col_ctrl3:
        max_bundle_size = st.slider("最大合单数", 1, 5, 3,
                                   help="每个配送批次最多合并的订单数")
    
    st.markdown("---")
    
    tab5a, tab5b, tab5c = st.tabs(["📦 订单合并", "⏱️ 实时ETA跟踪", "💰 骑手激励"])
    
    with tab5a:
        st.subheader("📦 订单顺路合并")
        
        col_a1, col_a2 = st.columns(2)
        
        with col_a1:
            st.markdown("**添加测试订单**")
            rest_select = st.selectbox("选择餐厅", data['restaurants']['name'].tolist(), key='bundler_rest')
            rest_info = data['restaurants'][data['restaurants']['name'] == rest_select].iloc[0]
            
            user_lat_b = st.number_input("用户纬度", value=BEIJING_CENTER[0] + 0.01, format="%.4f", key='bundler_lat')
            user_lon_b = st.number_input("用户经度", value=BEIJING_CENTER[1] + 0.01, format="%.4f", key='bundler_lon')
            
            prep_time_b = st.slider("备餐时间", 5, 45, 15, key='bundler_prep')
            is_urgent_b = st.checkbox("加急订单", value=False, key='bundler_urgent')
            
            if st.button("➕ 添加订单"):
                order_id = f"ORD{len(dispatcher.get_pending_orders_list())+1:04d}"
                dispatcher.add_order({
                    'order_id': order_id,
                    'restaurant_lat': rest_info['lat'],
                    'restaurant_lon': rest_info['lon'],
                    'user_lat': user_lat_b,
                    'user_lon': user_lon_b,
                    'prep_time_min': prep_time_b,
                    'is_urgent': is_urgent_b,
                    'food_type': rest_info['food_type']
                })
                st.success(f"订单 {order_id} 已添加")
            
            if st.button("🔄 批量生成订单"):
                for i in range(5):
                    order_id = f"ORD{len(dispatcher.get_pending_orders_list())+1:04d}"
                    rand_rest = data['restaurants'].sample(1).iloc[0]
                    dispatcher.add_order({
                        'order_id': order_id,
                        'restaurant_lat': rand_rest['lat'] + np.random.uniform(-0.01, 0.01),
                        'restaurant_lon': rand_rest['lon'] + np.random.uniform(-0.01, 0.01),
                        'user_lat': BEIJING_CENTER[0] + np.random.uniform(0, 0.05),
                        'user_lon': BEIJING_CENTER[1] + np.random.uniform(0, 0.05),
                        'prep_time_min': 15 + np.random.randint(-3, 10),
                        'is_urgent': np.random.choice([True, False], p=[0.2, 0.8])
                    })
                st.success("已生成5个测试订单")
        
        with col_a2:
            st.markdown("**待处理订单**")
            pending = dispatcher.get_pending_orders_list()
            if pending:
                pending_df = pd.DataFrame([{
                    '订单ID': o.order_id,
                    '加急': '✅' if o.is_urgent else '❌',
                    '备餐时间': f"{o.prep_time_min}分钟",
                    '剩余时间': f"{o.remaining_time:.0f}分钟",
                    '优先级': o.priority
                } for o in pending])
                st.dataframe(pending_df, use_container_width=True, hide_index=True)
            else:
                st.info("暂无待处理订单")
        
        st.markdown("---")
        st.subheader("🚚 调度推荐")
        
        available_riders = []
        for _, rider in data['riders'].iterrows():
            available_riders.append({
                'rider_id': rider['rider_id'],
                'on_time_rate': rider['on_time_rate'],
                'rating': rider['rating'],
                'total_deliveries': rider['total_deliveries'],
                'current_orders': rider['current_orders'],
                'avg_speed': rider['avg_speed']
            })
        
        if st.button("🔍 生成调度推荐"):
            recommendations = dispatcher.get_recommended_dispatch(available_riders[:10])
            
            if recommendations:
                for rec in recommendations[:5]:
                    top_rider = rec['candidate_riders'][0]
                    urgency_icon = "🚨" if rec['is_urgent'] else "📦"
                    
                    with st.expander(f"{urgency_icon} 订单{rec['order_id']} → 推荐骑手{top_rider['rider_id']} | "
                                   f"预计奖励¥{top_rider['recommended_incentive']}"):
                        rec_df = pd.DataFrame(rec['candidate_riders'][:5])
                        rec_df_display = rec_df[[
                            'rider_id', 'dispatch_score', 'eta_min', 'rider_workload',
                            'incentive_score', 'efficiency_score', 'recommended_incentive', 'rank'
                        ]].copy()
                        rec_df_display.columns = [
                            '骑手ID', '调度得分', 'ETA(分钟)', '当前订单',
                            '激励得分', '效率得分', '预计奖励(元)', '排名'
                        ]
                        
                        def highlight_best(row):
                            return ['background-color: #d4edda' if row['排名'] == 1 else '' for _ in row]
                        
                        st.dataframe(
                            rec_df_display.style.apply(highlight_best, axis=1),
                            use_container_width=True, hide_index=True
                        )
                        
                        if 'notes' in top_rider:
                            st.warning(f"📝 {top_rider['notes']}")
            else:
                st.info("暂无推荐，请先添加订单")
    
    with tab5b:
        st.subheader("⏱️ 实时ETA跟踪")
        
        summary = dispatcher.get_system_summary()
        
        col_m1, col_m2, col_m3, col_m4 = st.columns(4)
        col_m1.metric("待处理订单", summary['pending_orders'])
        col_m2.metric("活跃批次", summary['active_bundles'])
        col_m3.metric("配送中", summary['active_deliveries'])
        col_m4.metric("ETA置信度", f"{summary['metrics']['avg_eta_confidence']:.1%}")
        
        st.markdown("---")
        
        if summary['active_deliveries']:
            st.subheader("📡 实时配送状态")
            
            deliveries_df = pd.DataFrame(summary['active_deliveries'])
            if not deliveries_df.empty:
                status_color = {'前往餐厅': '#fff3cd', '配送中': '#d1ecf1', '待配送': '#e2e3e5'}
                
                def color_status(s):
                    return [f'background-color: {status_color.get(s["status"], "white")}'] * len(s)
                
                deliveries_display = deliveries_df[[
                    'order_id', 'rider_id', 'status', 'current_eta_min',
                    'eta_change_min', 'remaining_distance_km', 'confidence', 'elapsed_time_min'
                ]].copy()
                deliveries_display.columns = [
                    '订单ID', '骑手ID', '状态', '当前ETA(分钟)',
                    'ETA变化(分钟)', '剩余距离(km)', '置信度', '已用时(分钟)'
                ]
                
                st.dataframe(
                    deliveries_display.style.apply(color_status, axis=1),
                    use_container_width=True, hide_index=True
                )
                
                st.subheader("📈 ETA趋势")
                tracking_orders = [d['order_id'] for d in summary['active_deliveries']]
                if tracking_orders:
                    selected_order = st.selectbox("选择订单查看ETA趋势", tracking_orders)
                    trend_data = dispatcher.get_eta_trend_data(selected_order)
                    
                    if not trend_data.empty:
                        fig_eta = go.Figure()
                        
                        fig_eta.add_trace(go.Scatter(
                            x=trend_data['timestamp'],
                            y=trend_data['eta_min'],
                            mode='lines+markers',
                            name='ETA(分钟)',
                            line=dict(color='#1f77b4', width=3)
                        ))
                        
                        fig_eta.add_trace(go.Scatter(
                            x=trend_data['timestamp'],
                            y=trend_data['remaining_distance_km'],
                            mode='lines+markers',
                            name='剩余距离(km)',
                            yaxis='y2',
                            line=dict(color='#ff7f0e', width=2, dash='dash')
                        ))
                        
                        fig_eta.update_layout(
                            title=f'订单 {selected_order} ETA实时趋势',
                            xaxis_title='时间',
                            yaxis_title='ETA(分钟)',
                            yaxis2=dict(
                                title='剩余距离(km)',
                                overlaying='y',
                                side='right'
                            ),
                            legend=dict(orientation='h', y=1.1)
                        )
                        
                        st.plotly_chart(fig_eta, use_container_width=True)
            else:
                st.info("暂无进行中的配送")
        else:
            st.info("暂无进行中的配送，请先分配订单")
    
    with tab5c:
        st.subheader("💰 骑手激励系统")
        
        incentive_stats = dispatcher.incentive_system.get_system_wide_incentive_stats()
        
        if incentive_stats:
            col_i1, col_i2, col_i3, col_i4 = st.columns(4)
            col_i1.metric("累计激励支出", f"¥{incentive_stats['total_incentives_paid']:.2f}")
            col_i2.metric("单均奖励", f"¥{incentive_stats['avg_incentive_per_order']:.2f}")
            col_i3.metric("加急订单占比", f"{incentive_stats['urgent_order_ratio']:.1%}")
            col_i4.metric("预计节省成本", f"¥{incentive_stats['estimated_savings_from_reduction']:.2f}")
        
        st.markdown("---")
        
        col_p1, col_p2 = st.columns(2)
        
        with col_p1:
            st.subheader("📊 加急成本预测")
            test_distance = st.slider("配送距离(km)", 1.0, 10.0, 3.0, key='cost_dist')
            bundle_size = st.slider("合单数", 1, 3, 1, key='cost_bundle')
            
            cost_pred = dispatcher.incentive_system.predict_urgent_order_cost({
                'order_id': 'TEST',
                'distance_km': test_distance,
                'bundle_size': bundle_size
            })
            
            cost_df = pd.DataFrame([
                {'项目': '普通配送奖励', '金额(元)': cost_pred['normal_incentive']},
                {'项目': '加急配送奖励', '金额(元)': cost_pred['urgent_incentive']},
                {'项目': '加急溢价', '金额(元)': cost_pred['premium_per_order']},
                {'项目': '系统额外成本', '金额(元)': cost_pred['system_wide_cost']}
            ])
            
            st.dataframe(cost_df, use_container_width=True, hide_index=True)
            st.info(f"💡 {cost_pred['recommendation']}")
            
        with col_p2:
            st.subheader("🏆 骑手激励排名")
            rankings = dispatcher.incentive_system.get_rider_incentive_rankings()
            
            if not rankings.empty:
                rank_display = rankings[[
                    'rider_id', 'on_time_rate', 'avg_rating', 'total_deliveries',
                    'current_workload', 'incentive_score', 'total_earned', 'avg_earning_per_order'
                ]].head(10).copy()
                rank_display.columns = [
                    '骑手ID', '准时率', '评分', '累计配送',
                    '当前负载', '激励得分', '累计收入(元)', '单均收入(元)'
                ]
                
                st.dataframe(
                    rank_display.style.background_gradient(subset=['激励得分'], cmap='Greens'),
                    use_container_width=True, hide_index=True
                )
            else:
                st.info("暂无骑手激励数据")
        
        st.markdown("---")
        st.subheader("📈 激励构成分析")
        
        if incentive_stats and incentive_stats.get('order_count', 0) > 0:
            incentive_breakdown = pd.DataFrame({
                '奖励类型': ['基础配送费', '加急补贴', '准时奖励', '合并奖励', '高峰补贴', '距离补贴', '质量奖励'],
                '金额(元)': [
                    incentive_stats['order_count'] * 5.0,
                    incentive_stats['urgent_premium_total'],
                    incentive_stats['order_count'] * 2.0,
                    incentive_stats['bundle_savings_total'],
                    incentive_stats['order_count'] * 0.5,
                    max(0, (incentive_stats['avg_incentive_per_order'] - 5) * 0.3 * incentive_stats['order_count']),
                    incentive_stats['order_count'] * 0.8
                ]
            })
            
            fig_inc = px.bar(incentive_breakdown, x='奖励类型', y='金额(元)',
                           title='激励类型金额分布',
                           color='奖励类型',
                           text='金额(元)')
            fig_inc.update_traces(texttemplate='¥%{text:.0f}', textposition='outside')
            st.plotly_chart(fig_inc, use_container_width=True)
        
        st.markdown("---")
        st.subheader("🎯 系统优化指标")
        
        metrics_df = pd.DataFrame([
            {'指标': '累计节省距离', '数值': f"{summary['metrics']['total_distance_saved_km']:.2f} km", '状态': '✅'},
            {'指标': '平均每单节省', '数值': f"{summary['metrics']['total_distance_saved_km'] / max(summary['metrics']['total_bundles_created'], 1):.2f} km", '状态': '✅'},
            {'指标': '平均批次大小', '数值': f"{summary['metrics']['avg_bundle_size']:.2f} 单/批", '状态': '✅'},
            {'指标': '加急订单占比', '数值': f"{summary['metrics']['urgent_order_ratio']:.1%}", 
             '状态': '⚠️' if summary['metrics']['urgent_order_ratio'] > 0.3 else '✅'},
            {'指标': '骑手平均负载', '数值': f"{summary['metrics']['avg_rider_workload']:.1f} 单", '状态': '✅'},
            {'指标': '预计成本节省', '数值': f"¥{summary['metrics']['estimated_cost_savings']:.2f}", '状态': '💰'}
        ])
        
        st.dataframe(metrics_df, use_container_width=True, hide_index=True)

st.sidebar.header("📊 系统概览")
st.sidebar.metric("历史订单数", len(data['orders']))
st.sidebar.metric("合作餐厅数", len(data['restaurants']))
st.sidebar.metric("注册骑手上", len(data['riders']))

st.sidebar.markdown("---")
st.sidebar.subheader("🔧 模型信息")
st.sidebar.info("""
- **预测模型**: XGBoost
- **置信区间**: 分位数回归 (10%-90%)
- **特征数量**: 30+特征
- **多目标优化**: ETA(50%) + 负载(30%) + 质量(20%)
""")

st.sidebar.markdown("---")
st.sidebar.subheader("✨ 新增功能")
st.sidebar.success("""
**第一阶段:**
- 🏪 餐厅历史准时率特征
- 🏢 写字楼标识 & 楼层特征
- ⚖️ 多目标优化骑手推荐
- 📊 帕累托最优标识

**第二阶段:**
- 📦 订单顺路合并优化
- ⏱️ 实时ETA刷新(30秒)
- 💰 骑手激励调度系统
- 🚀 综合实时调度平台
""")
