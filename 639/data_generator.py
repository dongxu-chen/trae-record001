import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import random
from typing import Dict, List, Tuple

AIRLINES = {
    'CA': {'name': '中国国航', 'delay_rate': 0.28, 'compensation_base': 250},
    'MU': {'name': '东方航空', 'delay_rate': 0.32, 'compensation_base': 220},
    'CZ': {'name': '南方航空', 'delay_rate': 0.30, 'compensation_base': 230},
    'HU': {'name': '海南航空', 'delay_rate': 0.25, 'compensation_base': 280},
    '3U': {'name': '四川航空', 'delay_rate': 0.22, 'compensation_base': 300},
}

AIRPORTS = ['PEK', 'SHA', 'CAN', 'SZX', 'CTU', 'KMG', 'XIY', 'CKG', 'SHA', 'WUH']

AIRPORT_SECTORS = {
    'PEK': {'sector': '华北扇区A', 'congestion': 0.85, 'region': '华北'},
    'SHA': {'sector': '华东扇区B', 'congestion': 0.90, 'region': '华东'},
    'CAN': {'sector': '华南扇区C', 'congestion': 0.88, 'region': '华南'},
    'SZX': {'sector': '华南扇区C', 'congestion': 0.82, 'region': '华南'},
    'CTU': {'sector': '西南扇区D', 'congestion': 0.75, 'region': '西南'},
    'KMG': {'sector': '西南扇区E', 'congestion': 0.65, 'region': '西南'},
    'XIY': {'sector': '西北扇区F', 'congestion': 0.70, 'region': '西北'},
    'CKG': {'sector': '西南扇区D', 'congestion': 0.78, 'region': '西南'},
    'WUH': {'sector': '中南扇区G', 'congestion': 0.72, 'region': '中南'},
}

SECTOR_NAMES = ['华北扇区A', '华东扇区B', '华南扇区C', '西南扇区D', '西南扇区E', '西北扇区F', '中南扇区G']
REGIONS = ['华北', '华东', '华南', '西南', '西北', '中南']

WEATHER_CONDITIONS = {
    '晴朗': {'delay_factor': 0.1, 'weight': 0.45},
    '多云': {'delay_factor': 0.15, 'weight': 0.25},
    '小雨': {'delay_factor': 0.4, 'weight': 0.12},
    '中雨': {'delay_factor': 0.6, 'weight': 0.08},
    '雷暴': {'delay_factor': 0.85, 'weight': 0.05},
    '大雾': {'delay_factor': 0.9, 'weight': 0.03},
    '大雪': {'delay_factor': 0.95, 'weight': 0.02},
}

DELAY_REASONS = [
    '天气原因', '流量控制', '机械故障', '航空公司计划', 
    '机场保障', '旅客原因', '空中交通管制', '油料供应'
]


def generate_weather():
    conditions = list(WEATHER_CONDITIONS.keys())
    weights = [WEATHER_CONDITIONS[c]['weight'] for c in conditions]
    return random.choices(conditions, weights=weights)[0]


def generate_flow_control(airport=None):
    base_p = [0.5, 0.25, 0.18, 0.07]
    
    if airport and airport in AIRPORT_SECTORS:
        congestion = AIRPORT_SECTORS[airport]['congestion']
        adj_factor = congestion * 0.3
        base_p = [
            base_p[0] * (1 - adj_factor),
            base_p[1] * (1 + adj_factor * 0.5),
            base_p[2] * (1 + adj_factor),
            base_p[3] * (1 + adj_factor * 1.5)
        ]
        total = sum(base_p)
        base_p = [p / total for p in base_p]
    
    return np.random.choice(['无', '轻度', '中度', '重度'], p=base_p)


def get_sector_info(departure_airport, arrival_airport):
    dep_info = AIRPORT_SECTORS.get(departure_airport, {'sector': '未知', 'congestion': 0.5, 'region': '未知'})
    arr_info = AIRPORT_SECTORS.get(arrival_airport, {'sector': '未知', 'congestion': 0.5, 'region': '未知'})
    
    is_same_sector = (dep_info['sector'] == arr_info['sector'])
    is_same_region = (dep_info['region'] == arr_info['region'])
    
    sector_congestion = (dep_info['congestion'] + arr_info['congestion']) / 2
    
    cross_region_penalty = 0.0 if is_same_region else 0.15
    
    return {
        'departure_sector': dep_info['sector'],
        'arrival_sector': arr_info['sector'],
        'departure_region': dep_info['region'],
        'arrival_region': arr_info['region'],
        'is_same_sector': is_same_sector,
        'is_same_region': is_same_region,
        'sector_congestion': sector_congestion,
        'cross_region_penalty': cross_region_penalty
    }


def generate_flight_data(n_samples=5000, start_date='2024-01-01'):
    np.random.seed(42)
    random.seed(42)
    
    start_dt = datetime.strptime(start_date, '%Y-%m-%d')
    dates = [start_dt + timedelta(days=np.random.randint(0, 365)) for _ in range(n_samples)]
    
    airline_codes = list(AIRLINES.keys())
    airlines = np.random.choice(airline_codes, n_samples)
    flight_numbers = [f"{a}{np.random.randint(1000, 9999)}" for a in airlines]
    
    departure_airports = np.random.choice(AIRPORTS, n_samples)
    arrival_airports = []
    for dep in departure_airports:
        arr_options = [a for a in AIRPORTS if a != dep]
        arrival_airports.append(np.random.choice(arr_options))
    
    departure_hours = np.random.randint(6, 24, n_samples)
    departure_minutes = np.random.randint(0, 60, n_samples)
    
    weather = [generate_weather() for _ in range(n_samples)]
    flow_control = [generate_flow_control(dep) for dep in departure_airports]
    
    sector_infos = [get_sector_info(dep, arr) for dep, arr in zip(departure_airports, arrival_airports)]
    
    historical_delays_7d = np.random.normal(18, 12, n_samples).clip(0, 120)
    historical_delays_30d = np.random.normal(22, 15, n_samples).clip(0, 150)
    
    is_weekend = [(d.weekday() >= 5) for d in dates]
    is_peak_season = [(d.month in [1, 2, 7, 8]) for d in dates]
    
    data = pd.DataFrame({
        'flight_id': flight_numbers,
        'airline': airlines,
        'departure_airport': departure_airports,
        'arrival_airport': arrival_airports,
        'date': dates,
        'departure_hour': departure_hours,
        'departure_minute': departure_minutes,
        'weather': weather,
        'flow_control': flow_control,
        'departure_sector': [s['departure_sector'] for s in sector_infos],
        'arrival_sector': [s['arrival_sector'] for s in sector_infos],
        'departure_region': [s['departure_region'] for s in sector_infos],
        'arrival_region': [s['arrival_region'] for s in sector_infos],
        'is_same_sector': [s['is_same_sector'] for s in sector_infos],
        'is_same_region': [s['is_same_region'] for s in sector_infos],
        'sector_congestion': [s['sector_congestion'] for s in sector_infos],
        'cross_region_penalty': [s['cross_region_penalty'] for s in sector_infos],
        'historical_delay_7d': historical_delays_7d.round(1),
        'historical_delay_30d': historical_delays_30d.round(1),
        'is_weekend': is_weekend,
        'is_peak_season': is_peak_season,
    })
    
    data = calculate_delay_and_compensation(data)
    
    return data


def calculate_delay_and_compensation(df, policy_adjuster=None):
    delay_minutes = []
    delay_reason = []
    is_delayed = []
    compensation = []
    
    for idx, row in df.iterrows():
        airline_info = AIRLINES[row['airline']]
        weather_factor = WEATHER_CONDITIONS[row['weather']]['delay_factor']
        
        flow_map = {'无': 0.1, '轻度': 0.3, '中度': 0.5, '重度': 0.75}
        flow_factor = flow_map[row['flow_control']]
        
        sector_congestion = row.get('sector_congestion', 0.5)
        cross_region_penalty = row.get('cross_region_penalty', 0)
        is_same_sector = row.get('is_same_sector', True)
        
        sector_flow_factor = flow_factor * (1 + sector_congestion * 0.5)
        if not is_same_sector:
            sector_flow_factor *= 1.2
        
        hour_factor = 0.3 if 7 <= row['departure_hour'] <= 9 else \
                      0.35 if 17 <= row['departure_hour'] <= 20 else 0.15
        
        weekend_factor = 0.1 if row['is_weekend'] else 0
        season_factor = 0.15 if row['is_peak_season'] else 0
        hist_factor = (row['historical_delay_30d'] / 100) * 0.3
        
        base_prob = (airline_info['delay_rate'] * 0.5 + 
                    weather_factor * 0.25 + 
                    sector_flow_factor * 0.3 + 
                    hour_factor * 0.15 + 
                    weekend_factor + season_factor + hist_factor +
                    cross_region_penalty)
        
        delay_prob = min(0.95, base_prob)
        delayed = np.random.random() < delay_prob
        
        if delayed:
            base_delay = 30 + np.random.exponential(60)
            delay = base_delay * (1 + weather_factor * 0.8 + sector_flow_factor * 0.7 + cross_region_penalty)
            delay = int(min(delay, 600))
            
            reasons_weights = [
                weather_factor * 2,
                sector_flow_factor * 2.5,
                0.1,
                0.15,
                0.1,
                0.05,
                sector_flow_factor * 1.5,
                0.08
            ]
            reasons_weights = [w / sum(reasons_weights) for w in reasons_weights]
            reason = np.random.choice(DELAY_REASONS, p=reasons_weights)
            
            comp = calculate_compensation(delay, airline_info['compensation_base'], reason, policy_adjuster)
            
        else:
            delay = 0
            reason = '无延误'
            comp = 0
        
        delay_minutes.append(delay)
        delay_reason.append(reason)
        is_delayed.append(delayed)
        compensation.append(comp)
    
    df['delay_minutes'] = delay_minutes
    df['delay_reason'] = delay_reason
    df['is_delayed'] = is_delayed
    df['compensation'] = compensation
    
    return df


def calculate_compensation(delay_minutes, base_rate, delay_reason, policy_adjuster=None):
    if delay_minutes < 30:
        return 0
    
    base_multipliers = {
        '天气原因': 0.8,
        '流量控制': 0.7,
        '机械故障': 1.5,
        '航空公司计划': 1.3,
        '机场保障': 1.1,
        '旅客原因': 0.5,
        '空中交通管制': 0.9,
        '油料供应': 1.2,
    }
    
    base_thresholds = [
        (240, 4),
        (180, 3),
        (120, 2),
        (60, 1),
        (0, 0.5)
    ]
    
    if policy_adjuster:
        multipliers = policy_adjuster.adjust_reason_multipliers(base_multipliers)
        thresholds = policy_adjuster.adjust_delay_thresholds(base_thresholds)
        base_rate = policy_adjuster.adjust_base_rate(base_rate)
    else:
        multipliers = base_multipliers
        thresholds = base_thresholds
    
    multiplier = multipliers.get(delay_reason, 1.0)
    
    comp = 0
    for threshold, ratio in thresholds:
        if delay_minutes >= threshold:
            comp = base_rate * ratio
            break
    
    if policy_adjuster:
        comp = policy_adjuster.apply_final_adjustment(comp, delay_minutes, delay_reason)
    
    return int(max(0, comp * multiplier))


def generate_airline_comparison_data():
    comparison = []
    for code, info in AIRLINES.items():
        base_on_time = (1 - info['delay_rate']) * 100
        base_comp = info['compensation_base']
        
        comparison.append({
            'airline_code': code,
            'airline_name': info['name'],
            'on_time_rate': base_on_time,
            'service_quality': round(7.5 + np.random.random() * 2, 1),
            'compensation_adequacy': round(5 + base_comp / 50 + np.random.random(), 1),
            'flight_network': round(7 + np.random.random() * 2.5, 1),
            'baggage_handling': round(6.5 + np.random.random() * 3, 1),
            'customer_satisfaction': round(8.5 - info['delay_rate'] * 5 + np.random.random(), 1),
            'avg_compensation': base_comp * 1.2,
            'customer_rating': round(8.5 - info['delay_rate'] * 5 + np.random.random(), 1)
        })
    return pd.DataFrame(comparison)


if __name__ == '__main__':
    df = generate_flight_data(n_samples=10000)
    df.to_csv('flight_delay_data.csv', index=False, encoding='utf-8-sig')
    print(f"生成数据完成，共 {len(df)} 条记录")
    print(f"延误率: {(df['is_delayed'].mean() * 100):.1f}%")
    print(f"平均延误时长: {df['delay_minutes'].mean():.1f} 分钟")
    print(f"平均赔付金额: {df['compensation'].mean():.1f} 元")
