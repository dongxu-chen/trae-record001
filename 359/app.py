import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import Config
from utils.map_api import MapAPI
from utils.weather_api import WeatherAPI
from utils.features import FeatureEngineer
from utils.holiday_model import HolidayModel
from utils.delay_analyzer import DelayAnalyzer
from utils.courier_comparison import CourierComparison
from model import DeliveryTimeModel


st.set_page_config(
    page_title="快递时效预测系统 - 完整版",
    page_icon="🚚",
    layout="wide"
)


@st.cache_resource
def load_model():
    model = DeliveryTimeModel()
    if os.path.exists(Config.MODEL_PATH):
        model.load()
        return model
    return None


@st.cache_data
def generate_and_train(use_cv=False, confidence_levels=None):
    from generate_data import generate_training_data
    df = generate_training_data(5000)
    df.to_csv(Config.DATA_PATH, index=False, encoding='utf-8-sig')
    
    model = DeliveryTimeModel(confidence_levels=confidence_levels)
    model.train(df, use_cross_validation=use_cv)
    model.save()
    return model


def format_hours(hours):
    if hours < 24:
        return f"{hours:.1f} 小时"
    days = hours // 24
    remaining_hours = hours % 24
    if remaining_hours < 1:
        return f"{int(days)} 天"
    return f"{int(days)} 天 {remaining_hours:.0f} 小时"


def get_precipitation_description(rate):
    if rate <= 0:
        return "无降水"
    elif rate < 0.1:
        return "微量降水"
    elif rate < 0.5:
        return "小雨"
    elif rate < 2.5:
        return "中雨"
    elif rate < 8:
        return "大雨"
    else:
        return "暴雨"


def get_delay_severity_description(severity):
    desc = {
        'normal': '正常 - 影响较小',
        'mild': '轻度延误 - 可接受',
        'moderate': '中度延误 - 建议加急',
        'severe': '严重延误 - 建议更换策略'
    }
    return desc.get(severity, severity)


def plot_precipitation_grid(grid_data):
    if not grid_data or 'points' not in grid_data:
        return None
    
    points = grid_data['points']
    df = pd.DataFrame(points)
    
    pivot_df = df.pivot_table(
        index='lat', 
        columns='lng', 
        values='precipitation',
        aggfunc='mean'
    )
    return pivot_df


def main():
    st.title("🚚 快递时效预测系统")
    st.markdown("**完整版**: GBDT + 路网距离 + 网格降水量 + 分位数回归区间收窄 + 节假日影响 + 延误分析 + 快递对比")
    
    model = load_model()
    
    if model is None:
        st.warning("未检测到训练好的模型，点击下方按钮生成训练数据并训练模型")
        
        col1, col2 = st.columns(2)
        with col1:
            use_cv = st.checkbox("使用交叉验证训练", value=False)
        with col2:
            confidence_options = st.multiselect(
                "支持的置信水平",
                options=[80, 90, 95, 99],
                default=[80, 90, 95, 99]
            )
        
        if st.button("生成数据并训练模型", type="primary"):
            with st.spinner("正在生成训练数据并训练模型（约2-3分钟）..."):
                levels = [x/100 for x in confidence_options]
                model = generate_and_train(use_cv=use_cv, confidence_levels=levels)
            st.success("模型训练完成！")
            st.rerun()
        st.stop()
    
    holiday_model = HolidayModel()
    delay_analyzer = DelayAnalyzer()
    courier_comparison = CourierComparison()
    
    with st.sidebar:
        st.subheader("⚙️ 预测设置")
        confidence_level = st.select_slider(
            "置信水平",
            options=[80, 90, 95, 99],
            value=95,
            format_func=lambda x: f"{x}%"
        )
        show_all_intervals = st.checkbox("显示所有置信区间", value=True)
        enable_cache = st.checkbox("启用本地缓存", value=True)
        
        st.divider()
        st.subheader("📦 快递设置")
        package_weight = st.number_input("包裹重量 (kg)", min_value=0.5, max_value=100.0, value=1.0, step=0.5)
        service_type = st.selectbox(
            "服务类型",
            options=['standard', 'express', 'economy', 'same_day', 'next_day'],
            format_func=lambda x: {
                'standard': '标准快递',
                'express': '特快专递', 
                'economy': '经济快递',
                'same_day': '当日达',
                'next_day': '次日达'
            }[x],
            index=0
        )
        recommend_priority = st.selectbox(
            "推荐优先级",
            options=['balanced', 'speed', 'cost', 'reliability'],
            format_func=lambda x: {
                'balanced': '综合平衡',
                'speed': '时效优先',
                'cost': '价格优先',
                'reliability': '可靠性优先'
            }[x],
            index=0
        )
        
        st.divider()
        st.subheader("📊 缓存状态")
        map_api = MapAPI(use_mock=True, cache_enabled=enable_cache)
        cache_stats = map_api.get_cache_stats()
        st.metric("地址缓存", f"{cache_stats['geocode_count']} 条")
        st.metric("路线缓存", f"{cache_stats['route_count']} 条")
        
        if st.button("清除缓存", type="secondary"):
            map_api.clear_cache()
            st.success("缓存已清除")
            st.rerun()
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📦 寄件信息")
        from_city = st.selectbox(
            "寄件城市",
            options=list(Config.CITY_COORDS.keys()),
            index=0
        )
        from_address_detail = st.text_input(
            "寄件详细地址",
            value=f"{from_city}市朝阳区某某路88号"
        )
        from_address = f"{from_city}{from_address_detail}" if from_city not in from_address_detail else from_address_detail
        
        order_date = st.date_input("下单日期", value=datetime.now())
        order_time = st.time_input("下单时间", value=datetime.now().time())
        order_datetime = datetime.combine(order_date, order_time)
        
        holiday_info = holiday_model.get_holiday_info(order_datetime)
        if holiday_info['is_holiday']:
            st.info(f"🎉 {order_datetime.strftime('%Y-%m-%d')} 是 {holiday_info['holiday_name']}，快递量系数 {holiday_info['volume_factor']}x")
        elif holiday_info['days_until_holiday'] > 0 and holiday_info['days_until_holiday'] <= 14:
            st.info(f"📅 临近 {holiday_info['holiday_name']}（{holiday_info['days_until_holiday']}天后）")
    
    with col2:
        st.subheader("📍 收件信息")
        to_city = st.selectbox(
            "收件城市",
            options=list(Config.CITY_COORDS.keys()),
            index=1
        )
        to_address_detail = st.text_input(
            "收件详细地址",
            value=f"{to_city}市浦东新区某某路66号"
        )
        to_address = f"{to_city}{to_address_detail}" if to_city not in to_address_detail else to_address_detail
        
        st.subheader("⚡ 附加信息")
        busy_level = st.select_slider(
            "网点繁忙度",
            options=['空闲', '正常', '繁忙', '非常繁忙'],
            value='正常'
        )
        
        use_auto_weather = st.checkbox("自动获取网格天气", value=True)
        weather_api = WeatherAPI(use_mock=True)
        
        if use_auto_weather:
            to_coords = Config.CITY_COORDS[to_city]
            weather_info = weather_api.get_weather(to_city, coords=to_coords)
            
            weather = weather_info['weather']
            temperature = weather_info['temperature']
            humidity = weather_info['humidity']
            windpower = weather_info['windpower']
            precipitation_rate = weather_info.get('precipitation_rate', 0)
            precipitation_max = weather_info.get('precipitation_max', 0)
            precipitation_coverage = weather_info.get('precipitation_coverage', 0)
            precipitation_grid = weather_info.get('precipitation_grid')
            
            precip_desc = get_precipitation_description(precipitation_rate)
            st.info(
                f"🌤️ {to_city}天气: {weather}, {temperature}°C\n"
                f"💧 平均降水量: {precipitation_rate:.2f} mm/h ({precip_desc})\n"
                f"📊 降水覆盖: {precipitation_coverage:.0%}, 最大: {precipitation_max:.2f} mm/h"
            )
        else:
            weather = st.selectbox(
                "天气情况",
                options=['晴', '多云', '阴', '小雨', '中雨', '大雨', '雷阵雨', '小雪', '中雪', '雾', '霾'],
                index=0
            )
            temperature = st.slider("温度 (°C)", -20, 40, 20)
            humidity = st.slider("湿度 (%)", 0, 100, 50)
            windpower = st.slider("风力 (级)", 0, 10, 2)
            
            precipitation_rate = st.slider("平均降水量 (mm/h)", 0.0, 20.0, 0.0, step=0.1)
            precipitation_max = st.slider("最大降水量 (mm/h)", 0.0, 30.0, precipitation_rate, step=0.1)
            precipitation_coverage = st.slider("降水覆盖率", 0.0, 1.0, 0.0 if precipitation_rate == 0 else 0.5, step=0.05)
            precipitation_grid = None
    
    if st.button("预测送达时间", type="primary", use_container_width=True):
        with st.spinner("正在计算路线和预测时效..."):
            map_api = MapAPI(cache_enabled=enable_cache)
            route_info = map_api.calculate_distance(from_address, to_address)
            
            if route_info is None:
                st.error("无法获取路线信息，请检查地址输入")
                return
            
            is_from_cache = route_info.get('from_cache', False)
            
            weather_data = {
                'weather': weather,
                'temperature': temperature,
                'humidity': humidity,
                'windpower': str(windpower),
                'precipitation_rate': precipitation_rate,
                'precipitation_max': precipitation_max,
                'precipitation_coverage': precipitation_coverage,
                'precipitation_type': 'snow' if ('雪' in weather and temperature < 2) else ('rain' if '雨' in weather else 'none')
            }
            
            features, holiday_info_pred = FeatureEngineer.build_features(
                from_address,
                to_address,
                order_datetime,
                weather_data,
                busy_level,
                route_info
            )
            
            prediction = model.predict(features, confidence_level=confidence_level/100)
            
            expected_hours = features.get('expected_drive_hours', route_info['distance'] / 60) + 4
            delay_analysis = delay_analyzer.analyze(features, prediction['predicted_hours'], expected_hours)
            
            courier_results = courier_comparison.compare_couriers(
                base_hours=prediction['predicted_hours'],
                features_dict=features,
                weight=package_weight,
                distance=route_info['distance'],
                service_type=service_type
            )
            courier_recommendation = courier_comparison.recommend_courier(courier_results, priority=recommend_priority)
            
            st.divider()
            
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                cache_badge = "📦 (缓存)" if is_from_cache else ""
                st.metric(
                    label=f"📏 运输距离 {cache_badge}",
                    value=f"{route_info['distance']:.1f} km"
                )
            
            with col2:
                st.metric(
                    label="⏱️ 预计行驶时间",
                    value=f"{route_info['duration']:.1f} h"
                )
            
            with col3:
                st.metric(
                    label="💧 平均降水量",
                    value=f"{precipitation_rate:.2f} mm/h",
                    delta=f"覆盖 {precipitation_coverage:.0%}"
                )
            
            with col4:
                narrow_badge = "✂️ (已收窄)" if prediction['narrowed'] else ""
                st.metric(
                    label=f"📊 置信区间宽度 {narrow_badge}",
                    value=f"{prediction['interval_width']:.1f} h"
                )
            
            st.subheader("🎯 预测结果")
            
            pred_hours = prediction['predicted_hours']
            lower_hours = prediction['lower_bound']
            upper_hours = prediction['upper_bound']
            
            delivery_date = order_datetime + timedelta(hours=pred_hours)
            lower_date = order_datetime + timedelta(hours=lower_hours)
            upper_date = order_datetime + timedelta(hours=upper_hours)
            
            col_main, col_conf = st.columns([2, 1])
            
            with col_main:
                st.markdown(
                    f"""
                    <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                                padding: 30px; 
                                border-radius: 15px; 
                                color: white; 
                                text-align: center;">
                        <div style="font-size: 18px; opacity: 0.9;">预计送达时间</div>
                        <div style="font-size: 48px; font-weight: bold; margin: 10px 0;">
                            {format_hours(pred_hours)}
                        </div>
                        <div style="font-size: 16px; opacity: 0.85;">
                            预计到达: {delivery_date.strftime('%Y-%m-%d %H:%M')}
                        </div>
                        <div style="font-size: 14px; opacity: 0.75; margin-top: 10px;">
                            置信水平: {prediction['confidence_level']}
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )
            
            with col_conf:
                conf_level = prediction['confidence_level']
                st.markdown(
                    f"""
                    <div style="background: #f0f2f6; 
                                padding: 20px; 
                                border-radius: 15px; 
                                height: 100%;">
                        <div style="font-size: 14px; color: #666; margin-bottom: 10px;">
                            {conf_level} 置信区间 {'(已收窄)' if prediction['narrowed'] else ''}
                        </div>
                        <div style="font-size: 16px; font-weight: bold; color: #333;">
                            最快: {format_hours(lower_hours)}
                        </div>
                        <div style="font-size: 14px; color: #666; margin: 5px 0;">
                            {lower_date.strftime('%m-%d %H:%M')}
                        </div>
                        <div style="font-size: 16px; font-weight: bold; color: #333;">
                            最慢: {format_hours(upper_hours)}
                        </div>
                        <div style="font-size: 14px; color: #666; margin: 5px 0;">
                            {upper_date.strftime('%m-%d %H:%M')}
                        </div>
                        <div style="font-size: 14px; color: #888; margin-top: 10px; border-top: 1px solid #ddd; padding-top: 10px;">
                            区间宽度: {upper_hours - lower_hours:.1f} 小时
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )
            
            if show_all_intervals and prediction.get('all_intervals'):
                st.subheader("📊 多置信水平对比")
                interval_data = []
                for level_str, interval in prediction['all_intervals'].items():
                    interval_data.append({
                        '置信水平': level_str,
                        '下界 (小时)': round(interval['lower'], 1),
                        '上界 (小时)': round(interval['upper'], 1),
                        '区间宽度 (小时)': round(interval['upper'] - interval['lower'], 1)
                    })
                interval_df = pd.DataFrame(interval_data)
                st.dataframe(interval_df, use_container_width=True, hide_index=True)
                
                chart_data = []
                for level_str, interval in prediction['all_intervals'].items():
                    level_int = int(level_str.replace('%', ''))
                    chart_data.append({
                        '置信水平': level_int,
                        '下界': interval['lower'],
                        '预测值': pred_hours,
                        '上界': interval['upper']
                    })
                chart_df = pd.DataFrame(chart_data).set_index('置信水平')
                st.line_chart(chart_df)
            
            st.subheader("🎊 节假日影响")
            if holiday_info_pred.get('is_holiday'):
                st.warning(
                    f"📅 {holiday_info_pred['holiday_name']}期间："
                    f"快递量系数 {holiday_info_pred['volume_factor']}x，"
                    f"延误系数 {holiday_info_pred['delay_factor']}x"
                )
            elif holiday_info_pred.get('nearest_volume_factor', 1.0) > 1.0:
                st.info(
                    f"📅 临近 {holiday_info_pred['holiday_name']}，"
                    f"预计快递量 {holiday_info_pred['nearest_volume_factor']}x，"
                    f"延误 {holiday_info_pred['nearest_delay_factor']}x"
                )
            else:
                st.success("📅 当前为正常工作日，无节假日影响")
            
            volume_prediction = holiday_model.predict_volume_change(order_datetime, base_volume=10000)
            st.metric(
                "预计快递量", 
                f"{volume_prediction['predicted_volume']:.0f} 件",
                delta=f"{volume_prediction['volume_change_pct']:+.0f}%"
            )
            
            st.subheader("⚠️ 延误原因分析")
            col_delay1, col_delay2 = st.columns(2)
            
            with col_delay1:
                severity_desc = get_delay_severity_description(delay_analysis['severity'])
                st.markdown(f"**延误程度**: {severity_desc}")
                st.markdown(f"**延误小时数**: {delay_analysis['delay_hours']:.1f} 小时 ({delay_analysis['delay_pct']:.0f}%)")
                st.markdown(f"**主导因素**: :red[**{delay_analysis['dominant_factor_name']}**]")
            
            with col_delay2:
                contributions = delay_analyzer.get_factor_contribution(delay_analysis)
                contrib_data = [{'因素': c['factor_name'], '贡献占比': f"{c['contribution_pct']:.1f}%", '延误小时': f"{c['delay_hours']:.1f}h", '程度': c['level']} for c in contributions]
                st.dataframe(pd.DataFrame(contrib_data), use_container_width=True, hide_index=True)
            
            st.markdown("**因素详情**:")
            for factor_key, factor_data in delay_analysis['factors'].items():
                level_emoji = {'normal': '✅', 'mild': '⚠️', 'moderate': '🔶', 'severe': '🔴'}.get(factor_data['level'], '❓')
                st.markdown(f"{level_emoji} **{delay_analyzer._translate_factor_name(factor_key)}**: {factor_data['description']} (贡献 {factor_data['delay_hours']:.1f}h)")
            
            if delay_analysis['recommendations']:
                st.markdown("**💡 优化建议**:")
                for rec in delay_analysis['recommendations']:
                    priority_icon = {'high': '🔴', 'medium': '🟡', 'low': '🟢'}.get(rec['priority'], '⚪')
                    st.markdown(f"{priority_icon} {rec['content']}")
            
            st.subheader("🚚 快递公司时效对比")
            if courier_recommendation:
                st.success(f"**推荐快递公司: {courier_recommendation['recommended']}**")
                for reason in courier_recommendation['reasons']:
                    st.markdown(f"  - {reason}")
            
            courier_display_data = []
            for c in courier_results[:5]:
                courier_display_data.append({
                    '排名': c['rank'],
                    '快递公司': c['courier_name'],
                    '预计时效': f"{c['estimated_hours']:.1f}h ({c['estimated_days']:.1f}天)",
                    '预计费用': f"{c['estimated_fee']}元",
                    '可靠性': f"{c['reliability']*100:.0f}%",
                    '综合评分': c['overall_score'],
                    '适用场景': c['best_for']
                })
            st.dataframe(pd.DataFrame(courier_display_data), use_container_width=True, hide_index=True)
            
            st.subheader("🏆 各快递公司对比雷达")
            chart_couriers = courier_results[:4]
            radar_data = pd.DataFrame([
                {'快递公司': c['courier_name'], '指标': '时效评分', '值': c['speed_score']}
                for c in chart_couriers
            ] + [
                {'快递公司': c['courier_name'], '指标': '价格评分', '值': c['cost_score']}
                for c in chart_couriers
            ] + [
                {'快递公司': c['courier_name'], '指标': '可靠性评分', '值': c['reliability_score']}
                for c in chart_couriers
            ])
            st.bar_chart(radar_data.pivot(index='指标', columns='快递公司', values='值'))
            
            if precipitation_grid is not None:
                st.subheader("🌧️ 降水量网格分布 (20km半径)")
                grid_df = plot_precipitation_grid(precipitation_grid)
                if grid_df is not None and not grid_df.empty:
                    st.write(f"网格精度: {WeatherAPI.GRID_SIZE}° (~11km)")
                    st.dataframe(
                        grid_df.style.background_gradient(cmap='Blues', axis=None),
                        use_container_width=True
                    )
                    
                    grid_points = pd.DataFrame(precipitation_grid['points'])
                    if 'precipitation' in grid_points.columns:
                        scatter_data = grid_points[['lng', 'lat', 'precipitation']].rename(
                            columns={'precipitation': '降水量 (mm/h)'}
                        )
                        st.scatter_chart(
                            scatter_data,
                            x='lng',
                            y='lat',
                            size='降水量 (mm/h)',
                            color='降水量 (mm/h)',
                            use_container_width=True
                        )
            
            st.subheader("📊 特征重要性")
            importance_df = model.get_feature_importance(top_n=10)
            if importance_df is not None:
                st.bar_chart(
                    importance_df.set_index('feature')[['importance_pct']],
                    y_label='重要性 (%)'
                )
            
            st.subheader("🔍 影响因素分析")
            factor_expander = st.expander("查看详细影响因素", expanded=True)
            with factor_expander:
                col1, col2, col3, col4 = st.columns(4)
                
                time_features = FeatureEngineer.extract_time_features(order_datetime)
                with col1:
                    if time_features['is_weekend']:
                        st.warning("📅 周末下单，时效可能延长约10%")
                    else:
                        st.success("📅 工作日下单")
                
                with col2:
                    if time_features['is_night']:
                        st.warning("🌙 夜间下单，时效可能延长约30%")
                    else:
                        st.success("☀️ 日间下单")
                
                with col3:
                    if precipitation_rate > 2.5:
                        st.warning(f"🌧️ 强降水 ({precipitation_rate:.1f}mm/h)，时效显著受影响")
                    elif precipitation_rate > 0:
                        st.info(f"💧 有降水 ({precipitation_rate:.1f}mm/h)，时效可能受影响")
                    else:
                        st.success("☀️ 无降水天气")
                
                with col4:
                    if busy_level in ['繁忙', '非常繁忙']:
                        st.warning("🏭 网点繁忙，时效可能延长")
                    else:
                        st.success("🏭 网点运营正常")
                
                st.divider()
                col5, col6, col7, col8 = st.columns(4)
                
                with col5:
                    st.metric("天气影响系数", f"{features['weather_impact']:.2f}")
                with col6:
                    st.metric("繁忙影响系数", f"{features['busy_impact']:.2f}")
                with col7:
                    st.metric("降水影响系数", f"{1 + features['precipitation_impact']:.2f}")
                with col8:
                    st.metric("综合影响系数", f"{features['overall_impact']:.2f}")
                
                st.divider()
                holiday_features, _ = FeatureEngineer.extract_holiday_features(order_datetime)
                col9, col10, col11, col12 = st.columns(4)
                with col9:
                    st.metric("节假日延误系数", f"{holiday_features.get('holiday_delay_factor', 1.0):.2f}")
                with col10:
                    st.metric("快递量系数", f"{holiday_features.get('holiday_volume_factor', 1.0):.2f}")
                with col11:
                    st.metric("临近节假日", f"{holiday_features.get('days_until_holiday', -1)}天")
                with col12:
                    st.metric("电商促销", "是" if holiday_features.get('is_ecommerce_promo', 0) else "否")


if __name__ == '__main__':
    main()
