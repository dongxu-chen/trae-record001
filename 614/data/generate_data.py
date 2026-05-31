import pandas as pd
import numpy as np
import random
from datetime import datetime

random.seed(42)
np.random.seed(42)

n_samples = 15000

vehicle_types = ['轿车', 'SUV', 'MPV', '皮卡', '跑车']
engine_types = ['自然吸气', '涡轮增压', '混动', '插电混动']
fuel_types = ['汽油', '柴油']
road_types = ['城市道路', '高速公路', '乡村公路', '山区公路']
traffic_conditions = ['畅通', '缓行', '拥堵', '严重拥堵']
weather_conditions = ['晴天', '雨天', '雪天', '雾天']
driving_styles = ['温和', '标准', '激进']
transmission_types = ['手动', '自动', 'CVT', '双离合']

data = []

for i in range(n_samples):
    vehicle_type = random.choice(vehicle_types)
    engine_type = random.choice(engine_types)
    fuel_type = random.choice(fuel_types)
    road_type = random.choice(road_types)
    traffic_condition = random.choice(traffic_conditions)
    weather_condition = random.choice(weather_conditions)
    driving_style = random.choice(driving_styles)
    transmission_type = random.choice(transmission_types)
    
    displacement = round(np.random.uniform(1.0, 4.0), 1)
    curb_weight = round(np.random.uniform(1200, 2500), 0)
    horsepower = round(np.random.uniform(100, 400), 0)
    average_speed = round(np.random.uniform(20, 120), 1)
    speed_variance = round(np.random.uniform(5, 40), 1)
    acceleration_intensity = round(np.random.uniform(0.1, 0.9), 2)
    braking_frequency = round(np.random.uniform(0.1, 0.8), 2)
    cruise_control_ratio = round(np.random.uniform(0, 0.8), 2)
    elevation_change = round(np.random.uniform(0, 500), 0)
    temperature = round(np.random.uniform(-10, 40), 1)
    tire_pressure = round(np.random.uniform(2.0, 3.0), 1)
    ac_usage = random.choice([0, 1])
    passenger_count = random.randint(1, 5)
    cargo_weight = round(np.random.uniform(0, 200), 0)
    
    style_factor_map = {'温和': 0.3, '标准': 0.6, '激进': 0.9}
    style_base = style_factor_map[driving_style]
    
    longitudinal_accel_mean = round(np.random.uniform(0.5, 4.0) * style_base, 3)
    longitudinal_accel_std = round(np.random.uniform(0.2, 1.5) * style_base, 3)
    lateral_accel_mean = round(np.random.uniform(0.2, 2.5) * style_base, 3)
    lateral_accel_std = round(np.random.uniform(0.1, 1.0) * style_base, 3)
    
    hard_accel_events = int(np.random.poisson(3 * style_base))
    hard_brake_events = int(np.random.poisson(2 * style_base))
    hard_turn_events = int(np.random.poisson(1.5 * style_base))
    
    accel_decel_switch_freq = round(np.random.uniform(5, 30) * style_base, 1)
    idle_time_ratio = round(np.random.uniform(0.05, 0.3) * (1.5 - style_base), 3)
    high_accel_duration = round(np.random.uniform(0, 0.2) * style_base, 3)
    jerk_mean = round(np.random.uniform(0.5, 3.0) * style_base, 3)
    
    base_fuel_consumption = {
        '轿车': 7.0,
        'SUV': 9.5,
        'MPV': 9.0,
        '皮卡': 10.5,
        '跑车': 12.0
    }[vehicle_type]
    
    base_fuel_consumption += {
        '自然吸气': 0,
        '涡轮增压': 0.5,
        '混动': -2.5,
        '插电混动': -3.5
    }[engine_type]
    
    base_fuel_consumption += {
        '汽油': 0,
        '柴油': -1.0
    }[fuel_type]
    
    base_fuel_consumption += (displacement - 2.0) * 1.2
    base_fuel_consumption += (curb_weight - 1500) / 200
    base_fuel_consumption += (horsepower - 200) / 100
    
    road_factor = {
        '城市道路': 2.0,
        '高速公路': -1.0,
        '乡村公路': 0.5,
        '山区公路': 2.5
    }[road_type]
    
    traffic_factor = {
        '畅通': 0,
        '缓行': 1.5,
        '拥堵': 3.5,
        '严重拥堵': 5.0
    }[traffic_condition]
    
    weather_factor = {
        '晴天': 0,
        '雨天': 0.5,
        '雪天': 1.5,
        '雾天': 1.0
    }[weather_condition]
    
    style_factor = {
        '温和': -1.0,
        '标准': 0,
        '激进': 2.0
    }[driving_style]
    
    fuel_consumption = base_fuel_consumption + road_factor + traffic_factor + weather_factor + style_factor
    fuel_consumption += speed_variance * 0.05
    fuel_consumption += acceleration_intensity * 3.0
    fuel_consumption += braking_frequency * 2.0
    fuel_consumption -= cruise_control_ratio * 1.5
    fuel_consumption += elevation_change * 0.003
    fuel_consumption += ac_usage * 0.8
    fuel_consumption += passenger_count * 0.15
    fuel_consumption += cargo_weight * 0.005
    fuel_consumption += abs(temperature - 25) * 0.03
    
    fuel_consumption += longitudinal_accel_mean * 0.4
    fuel_consumption += longitudinal_accel_std * 0.3
    fuel_consumption += lateral_accel_mean * 0.2
    fuel_consumption += lateral_accel_std * 0.15
    fuel_consumption += hard_accel_events * 0.08
    fuel_consumption += hard_brake_events * 0.1
    fuel_consumption += hard_turn_events * 0.05
    fuel_consumption += accel_decel_switch_freq * 0.03
    fuel_consumption += idle_time_ratio * 2.0
    fuel_consumption += high_accel_duration * 3.0
    fuel_consumption += jerk_mean * 0.2
    
    if tire_pressure < 2.2:
        fuel_consumption += 0.5
    elif tire_pressure > 2.8:
        fuel_consumption -= 0.2
    
    fuel_consumption += np.random.normal(0, 0.3)
    fuel_consumption = max(3.0, min(25.0, fuel_consumption))
    
    data.append({
        '车型': vehicle_type,
        '发动机类型': engine_type,
        '燃油类型': fuel_type,
        '变速箱类型': transmission_type,
        '排量(L)': displacement,
        '整备质量(kg)': curb_weight,
        '马力(hp)': horsepower,
        '路况类型': road_type,
        '交通状况': traffic_condition,
        '天气状况': weather_condition,
        '环境温度(℃)': temperature,
        '驾驶风格': driving_style,
        '平均车速(km/h)': average_speed,
        '车速波动': speed_variance,
        '加速强度': acceleration_intensity,
        '刹车频率': braking_frequency,
        '定速巡航占比': cruise_control_ratio,
        '海拔变化(m)': elevation_change,
        '胎压(bar)': tire_pressure,
        '空调使用': ac_usage,
        '乘客人数': passenger_count,
        '行李重量(kg)': cargo_weight,
        '纵向加速度均值(m/s²)': longitudinal_accel_mean,
        '纵向加速度标准差(m/s²)': longitudinal_accel_std,
        '横向加速度均值(m/s²)': lateral_accel_mean,
        '横向加速度标准差(m/s²)': lateral_accel_std,
        '急加速事件次数': hard_accel_events,
        '急刹车事件次数': hard_brake_events,
        '急变道事件次数': hard_turn_events,
        '加减速切换频率(次/小时)': accel_decel_switch_freq,
        '怠速时间占比': idle_time_ratio,
        '大油门持续占比': high_accel_duration,
        '加速度变化率均值(m/s³)': jerk_mean,
        '百公里油耗(L)': round(fuel_consumption, 2)
    })

df = pd.DataFrame(data)
df.to_csv('d:\\Trae\\project\\record001\\614\\data\\fuel_consumption_data.csv', index=False, encoding='utf-8-sig')
print(f"数据集生成完成，共 {len(df)} 条记录")
print(f"油耗范围: {df['百公里油耗(L)'].min():.2f} - {df['百公里油耗(L)'].max():.2f} L/100km")
print(f"平均油耗: {df['百公里油耗(L)'].mean():.2f} L/100km")
