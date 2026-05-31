import streamlit as st
import pandas as pd
import numpy as np
import joblib
import sys
import os
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')

sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))
from feature_engineering import FeatureEngineer
from shap_explainer import FuelConsumptionExplainer
from quantile_trainer import QuantileFuelModel
from trip_manager import TripRecordManager
from anomaly_detector import FuelAnomalyDetector
from vehicle_health import VehicleHealthAnalyzer, SEVERITY_COLORS, SEVERITY_LABELS, CATEGORIES

st.set_page_config(
    page_title="汽车油耗预测系统 V3.0",
    page_icon="🚗",
    layout="wide",
    initial_sidebar_state="expanded"
)

@st.cache_resource
def load_models():
    model_dir = os.path.join(os.path.dirname(__file__), 'models')
    
    try:
        quantile_model = QuantileFuelModel.load(model_dir, quantiles=[0.05, 0.5, 0.95])
        fe = FeatureEngineer.load(os.path.join(model_dir, 'feature_engineer.pkl'))
        return quantile_model, fe, True
    except Exception as e:
        try:
            model = joblib.load(os.path.join(model_dir, 'fuel_model.pkl'))
            fe = FeatureEngineer.load(os.path.join(model_dir, 'feature_engineer.pkl'))
            return model, fe, False
        except Exception as e2:
            st.error(f"模型加载失败: {e2}")
            return None, None, False

@st.cache_resource
def get_explainer(_model, _fe, X_sample):
    explainer = FuelConsumptionExplainer(_model, _fe)
    explainer.fit_explainer(X_sample)
    return explainer

@st.cache_resource
def get_trip_manager():
    return TripRecordManager()

@st.cache_resource
def get_anomaly_detector():
    return FuelAnomalyDetector()

@st.cache_resource
def get_health_analyzer():
    return VehicleHealthAnalyzer()

def predict_with_quantile(quantile_model, fe, input_data):
    X = fe.transform(pd.DataFrame([input_data]))
    lower, median, upper = quantile_model.predict_interval(X)
    return lower[0], median[0], upper[0], X

def predict_standard(model, fe, input_data):
    X = fe.transform(pd.DataFrame([input_data]))
    prediction = model.predict(X)[0]
    return prediction, prediction - 0.5, prediction + 0.5, X

def get_comparison_data(model, fe, base_input, vehicle_types, engine_types, is_quantile=False):
    comparisons = []
    for vt in vehicle_types:
        for et in engine_types:
            input_copy = base_input.copy()
            input_copy['车型'] = vt
            input_copy['发动机类型'] = et
            if is_quantile:
                lower, median, upper, _ = predict_with_quantile(model, fe, input_copy)
                comparisons.append({
                    '车型': vt,
                    '发动机类型': et,
                    '预测油耗(L/100km)': round(median, 2),
                    '区间下限': round(lower, 2),
                    '区间上限': round(upper, 2)
                })
            else:
                pred, _, _, _ = predict_standard(model, fe, input_copy)
                comparisons.append({
                    '车型': vt,
                    '发动机类型': et,
                    '预测油耗(L/100km)': round(pred, 2)
                })
    return pd.DataFrame(comparisons)

def calculate_sensor_features_from_style(driving_style, acceleration_intensity, brake_frequency, 
                                          cruise_ratio, average_speed, idling_time_ratio):
    style_factor = {'温和': 0.3, '标准': 0.6, '激进': 0.9}[driving_style]
    accel_factor = (acceleration_intensity / 100) * 0.5 + 0.25
    brake_factor = (brake_frequency / 100) * 0.5 + 0.25
    
    longitudinal_accel_mean = (1.0 + style_factor * 2.5) * accel_factor
    longitudinal_accel_std = 0.5 + style_factor * 1.0
    lateral_accel_mean = 0.3 + style_factor * 1.5
    lateral_accel_std = 0.2 + style_factor * 0.8
    
    hard_accel_events = int(style_factor * 15 * accel_factor)
    hard_brake_events = int(style_factor * 12 * brake_factor)
    hard_turn_events = int(style_factor * 8)
    
    shift_frequency = 5 + style_factor * 15
    large_throttle_ratio = style_factor * 0.4 * accel_factor
    accel_change_rate = 0.5 + style_factor * 2.0
    
    if cruise_ratio > 0.5:
        cruise_factor = 1 - (cruise_ratio - 0.5)
        longitudinal_accel_mean *= cruise_factor
        hard_accel_events = max(0, int(hard_accel_events * cruise_factor))
        hard_brake_events = max(0, int(hard_brake_events * cruise_factor))
    
    return {
        '纵向加速度均值(m/s²)': round(longitudinal_accel_mean, 2),
        '纵向加速度标准差(m/s²)': round(longitudinal_accel_std, 2),
        '横向加速度均值(m/s²)': round(lateral_accel_mean, 2),
        '横向加速度标准差(m/s²)': round(lateral_accel_std, 2),
        '急加速事件次数': hard_accel_events,
        '急刹车事件次数': hard_brake_events,
        '急变道事件次数': hard_turn_events,
        '加减速切换频率(次/小时)': round(shift_frequency, 1),
        '怠速时间占比(%)': round(idling_time_ratio * 100, 1),
        '大油门持续占比(%)': round(large_throttle_ratio * 100, 1),
        '加速度变化率(m/s³)': round(accel_change_rate, 2)
    }

def plot_quantile_interval(lower, median, upper):
    fig, ax = plt.subplots(figsize=(10, 2))
    
    ax.barh(['油耗区间'], [upper - lower], left=[lower], height=0.3, color='#e3f2fd', alpha=0.8)
    ax.plot([median], [0], 'ro', markersize=10, label=f'中位数: {median:.2f}')
    ax.plot([lower], [0], 'bo', markersize=8, label=f'下限: {lower:.2f}')
    ax.plot([upper], [0], 'bo', markersize=8, label=f'上限: {upper:.2f}')
    
    ax.set_xlim(lower - 0.5, upper + 0.5)
    ax.set_ylim(-0.5, 0.5)
    ax.set_xlabel('百公里油耗 (L)')
    ax.set_yticks([])
    ax.set_title(f'90% 预测区间: [{lower:.2f}, {upper:.2f}] L/100km')
    ax.legend(loc='upper right')
    ax.grid(axis='x', alpha=0.3)
    
    return fig

def main():
    st.title("🚗 汽车油耗预测系统 V3.0")
    st.markdown("**XGBoost分位数回归 + 加速度传感器融合 + 行程记录 + 异常检测 + 车辆健康**")
    
    model, fe, is_quantile = load_models()
    
    if model is None:
        st.warning("模型未加载，请先运行训练脚本")
        return
    
    trip_manager = get_trip_manager()
    anomaly_detector = get_anomaly_detector()
    health_analyzer = get_health_analyzer()
    
    sample_input = pd.DataFrame([{
        '车型': '紧凑型车',
        '发动机类型': '涡轮增压',
        '排量(L)': 2.0,
        '最大功率(kW)': 150,
        '整备质量(kg)': 1400,
        '变速箱类型': '自动',
        '驱动方式': '前驱',
        '平均车速(km/h)': 50,
        '路况': '城市道路',
        '交通状况': '畅通',
        '天气': '晴天',
        '空调使用': '否',
        '驾驶风格': '标准',
        '加速强度': 50,
        '刹车频率': 50,
        '定速巡航占比': 0.1,
        '怠速时间占比': 0.1,
        '纵向加速度均值(m/s²)': 1.0,
        '纵向加速度标准差(m/s²)': 0.5,
        '横向加速度均值(m/s²)': 0.5,
        '横向加速度标准差(m/s²)': 0.3,
        '急加速事件次数': 3,
        '急刹车事件次数': 2,
        '急变道事件次数': 1,
        '加减速切换频率(次/小时)': 10,
        '大油门持续占比(%)': 10,
        '加速度变化率(m/s³)': 1.0
    }])
    
    X_sample = fe.transform(sample_input)
    explainer = get_explainer(model, fe, X_sample)
    
    tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8 = st.tabs([
        "📊 油耗预测", "📡 传感器数据", "💡 个性化建议", "🚙 车型对比", "🔬 模型解释",
        "📝 行程记录", "⚠️ 异常检测", "🔧 车辆健康"
    ])
    
    with tab1:
        st.header("📊 油耗预测")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("车辆参数")
            vehicle_type = st.selectbox("车型", ['紧凑型车', '中型车', 'SUV', 'MPV', '跑车'], index=0)
            engine_type = st.selectbox("发动机类型", ['自然吸气', '涡轮增压', '混合动力'], index=1)
            displacement = st.slider("排量(L)", 1.0, 5.0, 2.0, 0.1)
            max_power = st.slider("最大功率(kW)", 60, 300, 150, 10)
            weight = st.slider("整备质量(kg)", 1000, 2500, 1400, 50)
            transmission = st.selectbox("变速箱类型", ['手动', '自动', '双离合', 'CVT'], index=1)
            drive_type = st.selectbox("驱动方式", ['前驱', '后驱', '四驱'], index=0)
        
        with col2:
            st.subheader("行驶工况与驾驶习惯")
            avg_speed = st.slider("平均车速(km/h)", 10, 120, 50, 5)
            road_condition = st.selectbox("路况", ['城市道路', '高速公路', '乡村道路', '山路'], index=0)
            traffic = st.selectbox("交通状况", ['畅通', '轻度拥堵', '中度拥堵', '严重拥堵'], index=0)
            weather = st.selectbox("天气", ['晴天', '雨天', '雪天', '高温', '低温'], index=0)
            ac_usage = st.selectbox("空调使用", ['否', '是'], index=0)
        
        st.subheader("驾驶习惯")
        driving_style = st.select_slider("驾驶风格", ['温和', '标准', '激进'], value='标准')
        acceleration_intensity = st.slider("加速强度", 0, 100, 50)
        brake_frequency = st.slider("刹车频率", 0, 100, 50)
        cruise_ratio = st.slider("定速巡航占比", 0.0, 1.0, 0.1, 0.05)
        idling_ratio = st.slider("怠速时间占比", 0.0, 0.5, 0.1, 0.05)
        
        sensor_features = calculate_sensor_features_from_style(
            driving_style, acceleration_intensity, brake_frequency,
            cruise_ratio, avg_speed, idling_ratio
        )
        
        if st.button("开始预测", type="primary", use_container_width=True):
            input_data = {
                '车型': vehicle_type,
                '发动机类型': engine_type,
                '排量(L)': displacement,
                '最大功率(kW)': max_power,
                '整备质量(kg)': weight,
                '变速箱类型': transmission,
                '驱动方式': drive_type,
                '平均车速(km/h)': avg_speed,
                '路况': road_condition,
                '交通状况': traffic,
                '天气': weather,
                '空调使用': ac_usage,
                '驾驶风格': driving_style,
                '加速强度': acceleration_intensity,
                '刹车频率': brake_frequency,
                '定速巡航占比': cruise_ratio,
                '怠速时间占比': idling_ratio,
                **sensor_features
            }
            
            if is_quantile:
                lower, median, upper, X = predict_with_quantile(model, fe, input_data)
                st.session_state['lower_pred'] = lower
                st.session_state['median_pred'] = median
                st.session_state['upper_pred'] = upper
                st.session_state['last_X'] = X
                st.session_state['sensor_features'] = sensor_features
                st.session_state['input_data'] = input_data
                
                cal_factor = trip_manager.get_calibration_factor()
                if cal_factor != 1.0:
                    adjusted_median = median * cal_factor
                    adjusted_lower = lower * cal_factor
                    adjusted_upper = upper * cal_factor
                    st.info(f"💡 已应用实际油耗校准因子: {cal_factor:.2f}x")
                    median, lower, upper = adjusted_median, adjusted_lower, adjusted_upper
                
                st.success("预测完成!")
                
                st.subheader("预测结果")
                col_res1, col_res2, col_res3 = st.columns(3)
                col_res1.metric("预测油耗 (中位数)", f"{median:.2f} L/100km")
                col_res2.metric("90% 预测区间", f"{lower:.2f} ~ {upper:.2f}")
                col_res3.metric("区间宽度", f"{upper - lower:.2f} L")
                
                st.pyplot(plot_quantile_interval(lower, median, upper))
                
                fuel_price = 7.5
                st.subheader("费用估算")
                col_cost1, col_cost2 = st.columns(2)
                col_cost1.metric("每百公里油费", f"¥ {median * fuel_price:.2f}")
                col_cost2.metric("每公里油费", f"¥ {median * fuel_price / 100:.3f}")
                
            else:
                prediction, lower, upper, X = predict_standard(model, fe, input_data)
                st.session_state['median_pred'] = prediction
                st.session_state['last_X'] = X
                st.session_state['sensor_features'] = sensor_features
                st.session_state['input_data'] = input_data
                
                st.success("预测完成!")
                st.metric("预测油耗", f"{prediction:.2f} L/100km")
    
    with tab2:
        st.header("📡 传感器数据")
        
        if 'sensor_features' in st.session_state:
            sensor_data = st.session_state['sensor_features']
            
            col_s1, col_s2 = st.columns(2)
            
            with col_s1:
                st.subheader("加速度统计")
                accel_df = pd.DataFrame({
                    '指标': ['纵向加速度均值', '纵向加速度标准差', '横向加速度均值', '横向加速度标准差'],
                    '数值(m/s²)': [
                        sensor_data['纵向加速度均值(m/s²)'],
                        sensor_data['纵向加速度标准差(m/s²)'],
                        sensor_data['横向加速度均值(m/s²)'],
                        sensor_data['横向加速度标准差(m/s²)']
                    ]
                })
                st.dataframe(accel_df, use_container_width=True)
            
            with col_s2:
                st.subheader("激烈驾驶事件")
                event_df = pd.DataFrame({
                    '事件类型': ['急加速', '急刹车', '急变道', '加减速切换频率'],
                    '次数': [
                        sensor_data['急加速事件次数'],
                        sensor_data['急刹车事件次数'],
                        sensor_data['急变道事件次数'],
                        sensor_data['加减速切换频率(次/小时)']
                    ]
                })
                st.dataframe(event_df, use_container_width=True)
            
            st.subheader("驾驶平稳性指标")
            col_m1, col_m2, col_m3 = st.columns(3)
            col_m1.metric("怠速时间占比", f"{sensor_data['怠速时间占比(%)']:.1f}%")
            col_m2.metric("大油门持续占比", f"{sensor_data['大油门持续占比(%)']:.1f}%")
            col_m3.metric("加速度变化率", f"{sensor_data['加速度变化率(m/s³)']:.2f} m/s³")
            
            st.subheader("传感器融合雷达图")
            categories = ['纵向加速', '横向加速', '急加速', '急刹车', '急变道', '平稳性']
            values = [
                min(100, sensor_data['纵向加速度均值(m/s²)'] / 3 * 100),
                min(100, sensor_data['横向加速度均值(m/s²)'] / 2 * 100),
                min(100, sensor_data['急加速事件次数'] / 10 * 100),
                min(100, sensor_data['急刹车事件次数'] / 8 * 100),
                min(100, sensor_data['急变道事件次数'] / 5 * 100),
                max(0, 100 - sensor_data['加减速切换频率(次/小时)'] / 20 * 100)
            ]
            
            fig, ax = plt.subplots(figsize=(8, 8), subplot_kw=dict(projection='polar'))
            angles = np.linspace(0, 2 * np.pi, len(categories), endpoint=False)
            values += values[:1]
            angles = np.concatenate((angles, [angles[0]]))
            
            ax.plot(angles, values, 'o-', linewidth=2, label='当前驾驶')
            ax.fill(angles, values, alpha=0.25)
            ax.set_thetagrids(angles[:-1] * 180/np.pi, categories)
            ax.set_ylim(0, 100)
            ax.set_title("驾驶行为传感器特征雷达图")
            ax.legend(loc='upper right', bbox_to_anchor=(1.3, 1.1))
            st.pyplot(fig)
            
            with st.expander("传感器判定规则说明"):
                st.markdown("""
                - **急加速**: 纵向加速度 > 2.5 m/s²
                - **急刹车**: 纵向减速度 > 3.0 m/s²  
                - **急变道**: 横向加速度 > 2.0 m/s²
                - **平稳性**: 基于加减速切换频率计算
                """)
        else:
            st.info("请先在「油耗预测」标签页进行预测")
    
    with tab3:
        st.header("💡 个性化节油建议")
        
        if 'last_X' in st.session_state and 'input_data' in st.session_state:
            analysis = explainer.get_personalized_driving_analysis(
                st.session_state['last_X'], 
                st.session_state['input_data']
            )
            
            col_score1, col_score2 = st.columns(2)
            
            with col_score1:
                score = analysis['overall_score']
                st.metric("综合驾驶评分", f"{score:.0f}/100", 
                         delta="优秀" if score >= 80 else "良好" if score >= 60 else "需改进")
                
                fig = explainer.plot_radar_chart(analysis, save_path=None)
                st.pyplot(fig)
            
            with col_score2:
                st.subheader("各维度分析")
                for dim, data in analysis['dimensions'].items():
                    with st.expander(f"{dim} - {data['score']:.0f}分"):
                        st.write(f"**评价**: {data['assessment']}")
                        st.write(f"**建议**: {data['recommendation']}")
                        st.write(f"**油耗影响**: {data['fuel_impact']:.2f} L/100km")
            
            st.subheader("🎯 驾驶弱点与改进优先级")
            
            if len(analysis['weaknesses']) > 0:
                for i, weakness in enumerate(analysis['weaknesses'][:3], 1):
                    col_w1, col_w2, col_w3 = st.columns([2, 1, 1])
                    with col_w1:
                        st.markdown(f"**Top {i}: {weakness['dimension']}**")
                        st.caption(weakness['issue'])
                    with col_w2:
                        st.metric("油耗影响", f"+{weakness['fuel_impact']:.2f}L")
                    with col_w3:
                        st.metric("可节省", f"{weakness['potential_savings']:.2f}L")
            else:
                st.success("🎉 驾驶习惯良好，未发现明显弱点!")
            
            st.subheader("📋 综合改进方案")
            
            total_savings = sum(w['potential_savings'] for w in analysis['weaknesses'])
            st.info(f"💡 如按建议改进，预计可节省油耗: **{total_savings:.2f} L/100km**")
            
            for suggestion in analysis['suggestions']:
                st.markdown(f"- {suggestion}")
                
        else:
            st.info("请先在「油耗预测」标签页进行预测")
    
    with tab4:
        st.header("🚙 车型对比")
        
        if 'input_data' in st.session_state:
            vehicle_types = ['紧凑型车', '中型车', 'SUV', 'MPV']
            engine_types = ['自然吸气', '涡轮增压']
            
            comparison_df = get_comparison_data(
                model, fe, st.session_state['input_data'],
                vehicle_types, engine_types, is_quantile
            )
            
            st.subheader("油耗对比表")
            st.dataframe(comparison_df, use_container_width=True)
            
            st.subheader("油耗对比图表")
            fig, ax = plt.subplots(figsize=(10, 6))
            
            x = np.arange(len(vehicle_types))
            width = 0.25
            
            for i, et in enumerate(engine_types):
                vals = comparison_df[comparison_df['发动机类型'] == et]['预测油耗(L/100km)'].values
                ax.bar(x + i * width, vals, width, label=et)
                
                if is_quantile:
                    lowers = comparison_df[comparison_df['发动机类型'] == et]['区间下限'].values
                    uppers = comparison_df[comparison_df['发动机类型'] == et]['区间上限'].values
                    ax.errorbar(x + i * width, vals, 
                               yerr=[np.array(vals) - np.array(lowers), 
                                     np.array(uppers) - np.array(vals)],
                               fmt='none', color='black', capsize=5, alpha=0.5)
            
            ax.set_xlabel('车型')
            ax.set_ylabel('预测油耗 (L/100km)')
            ax.set_title('不同车型与发动机类型的油耗对比 (含预测区间)')
            ax.set_xticks(x + width)
            ax.set_xticklabels(vehicle_types)
            ax.legend()
            ax.grid(axis='y', alpha=0.3)
            
            st.pyplot(fig)
            
        else:
            st.info("请先在「油耗预测」标签页进行预测")
    
    with tab5:
        st.header("🔬 模型解释 (SHAP)")
        
        if 'last_X' in st.session_state:
            col_shap1, col_shap2 = st.columns(2)
            
            with col_shap1:
                st.subheader("特征重要性 Top 10")
                feature_importance = explainer.get_feature_importance(top_n=10)
                
                fig1, ax1 = plt.subplots(figsize=(10, 8))
                feature_importance.sort_values('shap_importance').plot.barh(x='feature', y='shap_importance', ax=ax1)
                ax1.set_xlabel('SHAP 重要性 (平均影响幅度)')
                ax1.set_ylabel('特征')
                ax1.set_title('Top 10 影响油耗的特征')
                st.pyplot(fig1)
            
            with col_shap2:
                st.subheader("本次预测贡献分析")
                explanation = explainer.get_single_prediction_explanation(st.session_state['last_X'])
                top_explanation = explanation.head(8)
                
                fig2, ax2 = plt.subplots(figsize=(10, 8))
                colors = ['#4CAF50' if x < 0 else '#F44336' for x in top_explanation['shap_value']]
                top_explanation.plot.barh(x='feature', y='shap_value', ax=ax2, color=colors)
                ax2.axvline(x=0, color='black', linestyle='-', linewidth=0.5)
                ax2.set_xlabel('SHAP 值 (对油耗的影响 L)')
                ax2.set_ylabel('特征')
                ax2.set_title('主要特征对本次预测的贡献')
                ax2.legend(['降低油耗', '增加油耗'], loc='lower right')
                st.pyplot(fig2)
            
            st.subheader("特征解释表")
            explanation_display = explanation.copy()
            explanation_display['影响方向'] = explanation_display['shap_value'].apply(
                lambda x: '🔴 增加油耗' if x > 0 else '🟢 降低油耗'
            )
            explanation_display['shap_value'] = explanation_display['shap_value'].round(3)
            st.dataframe(explanation_display[['feature', 'shap_value', '影响方向']].head(15), use_container_width=True)
            
        else:
            st.info("请先在「油耗预测」标签页进行预测")
    
    with tab6:
        st.header("📝 行程与加油记录")
        
        stats = trip_manager.get_statistics()
        
        col_stat1, col_stat2, col_stat3, col_stat4 = st.columns(4)
        col_stat1.metric("总行程数", stats['total_trips'])
        col_stat2.metric("总行驶距离", f"{stats['total_distance_km']:.0f} km")
        col_stat3.metric("总加油量", f"{stats['total_fuel_l']:.1f} L")
        col_stat4.metric("总油费", f"¥ {stats['total_cost']:.0f}")
        
        if stats['calibrated_consumption'] > 0:
            st.success(f"📊 实际校准平均油耗: {stats['calibrated_consumption']:.2f} L/100km")
            cal_factor = stats['calibrated_consumption'] / 8.0
            st.info(f"校准因子: {cal_factor:.2f}x (已自动应用到预测)")
        
        tab_trip, tab_refuel = st.tabs(["行程记录", "加油记录"])
        
        with tab_trip:
            st.subheader("添加行程记录")
            with st.form("add_trip_form"):
                col_t1, col_t2 = st.columns(2)
                with col_t1:
                    trip_date = st.date_input("日期")
                    distance = st.number_input("行驶距离(km)", 0.0, 1000.0, 50.0)
                    fuel_used = st.number_input("实际用油(L)", 0.0, 100.0, 5.0)
                    avg_speed = st.number_input("平均速度(km/h)", 0, 120, 50)
                with col_t2:
                    road_type = st.selectbox("路况", ['城市道路', '高速公路', '乡村道路', '山路'])
                    traffic = st.selectbox("交通状况", ['畅通', '轻度拥堵', '中度拥堵', '严重拥堵'])
                    duration = st.number_input("行驶时间(分钟)", 0, 480, 60)
                    notes = st.text_input("备注")
                
                submit_trip = st.form_submit_button("保存行程")
                if submit_trip:
                    actual_fc = (fuel_used / distance * 100) if distance > 0 else 0
                    trip_data = {
                        'date': trip_date.strftime('%Y-%m-%d'),
                        'distance_km': distance,
                        'fuel_used_l': fuel_used,
                        'actual_fuel_consumption': round(actual_fc, 2),
                        'avg_speed': avg_speed,
                        'duration_min': duration,
                        'road_type': road_type,
                        'traffic_condition': traffic,
                        'notes': notes
                    }
                    trip_id = trip_manager.add_trip(trip_data)
                    st.success(f"行程已保存! ID: {trip_id}")
                    st.rerun()
            
            st.subheader("最近行程")
            recent_trips = trip_manager.get_recent_trips(20)
            if len(recent_trips) > 0:
                st.dataframe(recent_trips[['date', 'distance_km', 'fuel_used_l', 'actual_fuel_consumption', 
                                          'avg_speed', 'road_type', 'notes']], use_container_width=True)
            else:
                st.info("暂无行程记录")
        
        with tab_refuel:
            st.subheader("添加加油记录")
            with st.form("add_refuel_form"):
                col_r1, col_r2 = st.columns(2)
                with col_r1:
                    refuel_date = st.date_input("加油日期")
                    fuel_amount = st.number_input("加油量(L)", 0.0, 80.0, 40.0)
                    fuel_price = st.number_input("油价(元/L)", 5.0, 10.0, 7.5)
                    odometer = st.number_input("当前里程(km)", 0, 500000, 10000)
                with col_r2:
                    is_full = st.checkbox("加满油箱", value=True)
                    station = st.text_input("加油站")
                    notes_refuel = st.text_input("备注")
                
                submit_refuel = st.form_submit_button("保存加油记录")
                if submit_refuel:
                    total_cost = fuel_amount * fuel_price
                    refuel_data = {
                        'date': refuel_date.strftime('%Y-%m-%d'),
                        'fuel_amount_l': fuel_amount,
                        'fuel_price': fuel_price,
                        'total_cost': total_cost,
                        'odometer_km': odometer,
                        'is_full_tank': is_full,
                        'station_name': station,
                        'notes': notes_refuel
                    }
                    refuel_id, calc_fc = trip_manager.add_refuel(refuel_data)
                    if calc_fc > 0:
                        st.success(f"加油记录已保存! 计算油耗: {calc_fc:.2f} L/100km")
                    else:
                        st.success("加油记录已保存! (距离太短，无法计算油耗)")
                    st.rerun()
            
            st.subheader("加油历史")
            all_refuels = trip_manager.get_all_refuels()
            if len(all_refuels) > 0:
                st.dataframe(all_refuels[['date', 'fuel_amount_l', 'fuel_price', 'total_cost', 
                                         'odometer_km', 'calculated_fuel_consumption', 'station_name']], 
                            use_container_width=True)
            else:
                st.info("暂无加油记录")
    
    with tab7:
        st.header("⚠️ 油耗异常检测")
        
        if st.button("🔍 检测异常", type="primary"):
            anomalies = anomaly_detector.detect_anomalies()
            if len(anomalies) > 0:
                st.warning(f"检测到 {len(anomalies)} 个异常!")
            else:
                st.success("未检测到异常")
            st.rerun()
        
        trend = anomaly_detector.get_trend_analysis()
        if trend:
            col_trend1, col_trend2, col_trend3 = st.columns(3)
            trend_emoji = "📈" if trend['trend'] == 'rising' else "📉" if trend['trend'] == 'falling' else "➡️"
            col_trend1.metric("油耗趋势", f"{trend_emoji} {trend['trend']}")
            col_trend2.metric("变化幅度", f"{trend['trend_percent']:+.1f}%")
            col_trend3.metric("近期平均", f"{trend['recent_avg']:.2f} L")
        
        unack_anomalies = anomaly_detector.get_anomalies(acknowledged=False)
        if len(unack_anomalies) > 0:
            st.subheader(f"🚨 未处理异常 ({len(unack_anomalies)})")
            
            for _, anomaly in unack_anomalies.iterrows():
                severity_color = SEVERITY_COLORS.get(anomaly['severity'], '#f59e0b')
                severity_label = SEVERITY_LABELS.get(anomaly['severity'], '中等')
                
                with st.expander(f"{anomaly['date']} - {severity_label.upper()}", expanded=True):
                    st.markdown(f"<span style='color:{severity_color}'><strong>严重度: {severity_label}</strong></span>", 
                               unsafe_allow_html=True)
                    st.write(f"**描述**: {anomaly['description']}")
                    col_a1, col_a2, col_a3 = st.columns(3)
                    col_a1.metric("实际油耗", f"{anomaly['fuel_consumption']:.2f} L")
                    col_a2.metric("基线油耗", f"{anomaly['baseline_consumption']:.2f} L")
                    col_a3.metric("偏离", f"+{anomaly['deviation_percent']:.1f}%")
                    
                    if st.button("标记已处理", key=f"ack_{anomaly['anomaly_id']}"):
                        anomaly_detector.acknowledge_anomaly(anomaly['anomaly_id'])
                        st.rerun()
        else:
            st.success("✅ 没有未处理的异常")
        
        st.subheader("📊 异常检测统计")
        all_anomalies = anomaly_detector.get_anomalies(acknowledged=True)
        col_astat1, col_astat2 = st.columns(2)
        col_astat1.metric("总异常数", len(all_anomalies))
        col_astat2.metric("已处理", len(all_anomalies[all_anomalies['is_acknowledged'] == True]))
        
        if len(all_anomalies) > 0:
            st.subheader("历史异常")
            st.dataframe(all_anomalies[['date', 'severity', 'description', 'fuel_consumption', 
                                       'deviation_percent', 'is_acknowledged']], use_container_width=True)
    
    with tab8:
        st.header("🔧 车辆健康诊断")
        
        health_report = health_analyzer.generate_health_report()
        
        col_h1, col_h2, col_h3 = st.columns(3)
        status_emoji = "🟢" if health_report['health_status'] == 'good' else \
                      "🟡" if health_report['health_status'] == 'fair' else \
                      "🟠" if health_report['health_status'] == 'warning' else "🔴"
        col_h1.metric("健康状态", f"{status_emoji} {health_report['health_status'].upper()}")
        col_h2.metric("健康评分", f"{health_report['health_score']:.0f}/100")
        col_h3.metric("故障码数量", health_report['active_dtc_count'])
        
        if health_report['total_fuel_impact_pct'] > 0:
            st.warning(f"⚠️ 当前故障预计增加油耗: {health_report['total_fuel_impact_pct']:.1f}%")
        
        tab_add_dtc, tab_active, tab_search = st.tabs(["添加故障码", "当前故障", "故障码查询"])
        
        with tab_add_dtc:
            st.subheader("添加故障码 (DTC)")
            dtc_code = st.text_input("故障码 (如 P0300)", "").upper()
            dtc_notes = st.text_area("备注")
            
            if st.button("添加故障码", type="primary"):
                if dtc_code:
                    dtc_id, dtc_info = health_analyzer.add_dtc(dtc_code, dtc_notes)
                    if dtc_info:
                        st.success(f"已添加 {dtc_code}: {dtc_info['description']}")
                        st.info(f"预计油耗影响: +{dtc_info['fuel_impact_pct']}%")
                    else:
                        st.warning(f"已添加未知故障码 {dtc_code}")
                    st.rerun()
        
        with tab_active:
            active_dtcs = health_analyzer.get_active_dtcs()
            
            if len(active_dtcs) > 0:
                st.subheader(f"当前激活故障码 ({len(active_dtcs)})")
                
                for _, dtc in active_dtcs.iterrows():
                    severity_color = SEVERITY_COLORS.get(dtc['severity'], '#f59e0b')
                    severity_label = SEVERITY_LABELS.get(dtc['severity'], '中等')
                    
                    dtc_info = health_analyzer.lookup_dtc(dtc['dtc_code'])
                    
                    with st.expander(f"{dtc['dtc_code']} - {severity_label}", expanded=True):
                        st.markdown(f"<span style='color:{severity_color}'><strong>严重度: {severity_label}</strong></span>", 
                                   unsafe_allow_html=True)
                        st.write(f"**描述**: {dtc['description']}")
                        st.write(f"**检测日期**: {dtc['date']}")
                        
                        if dtc_info:
                            st.write(f"**油耗影响**: +{dtc_info['fuel_impact_pct']}%")
                            st.write(f"**可能症状**: {', '.join(dtc_info['symptoms'])}")
                        
                        if st.button("清除故障码", key=f"clear_{dtc['dtc_id']}"):
                            health_analyzer.clear_dtc(dtc['dtc_id'])
                            st.success("故障码已清除")
                            st.rerun()
            else:
                st.success("✅ 没有激活的故障码，车辆状态良好!")
            
            st.subheader("💡 维护建议")
            recommendations = health_analyzer.get_maintenance_recommendations()
            if len(recommendations) > 0:
                for rec in recommendations:
                    sev_color = SEVERITY_COLORS.get(rec['severity'], '#f59e0b')
                    with st.container():
                        st.markdown(f"**[{rec['priority']}] {rec['code']}**")
                        st.markdown(f"<span style='color:{sev_color}'>{rec['description']}</span>", 
                                   unsafe_allow_html=True)
                        st.write(f"建议操作: {rec['action']}")
                        st.info(f"修复后预计可节省油耗: ~{rec['fuel_savings_estimate']}%")
                        st.markdown("---")
            else:
                st.info("暂无维护建议")
        
        with tab_search:
            st.subheader("故障码数据库查询")
            search_keyword = st.text_input("搜索故障码或描述", "")
            
            if search_keyword:
                results = health_analyzer.search_dtc_by_keyword(search_keyword)
                if results:
                    for r in results:
                        sev_color = SEVERITY_COLORS.get(r['severity'], '#f59e0b')
                        sev_label = SEVERITY_LABELS.get(r['severity'], '中等')
                        cat_label = CATEGORIES.get(r['category'], '其他')
                        
                        with st.expander(f"{r['code']} - {r['description']}"):
                            st.write(f"**严重度**: :{sev_color}[{sev_label}]")
                            st.write(f"**系统**: {cat_label}")
                            st.write(f"**油耗影响**: +{r['fuel_impact_pct']}%")
                            st.write(f"**症状**: {', '.join(r['symptoms'])}")
                else:
                    st.info("未找到匹配的故障码")
    
    st.markdown("---")
    st.caption("汽车油耗预测系统 V3.0 | XGBoost分位数回归 + 加速度传感器融合 + 行程记录 + 异常检测 + 车辆健康")

if __name__ == "__main__":
    main()
