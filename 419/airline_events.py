import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import random

AIRLINES = ['中国国航', '东方航空', '南方航空', '海南航空', '深圳航空', '四川航空']

EVENT_TYPES = {
    '会员日': {'discount_range': (0.15, 0.30), 'probability': 0.3},
    '周年庆': {'discount_range': (0.20, 0.40), 'probability': 0.2},
    '促销活动': {'discount_range': (0.10, 0.25), 'probability': 0.5},
    '节日特惠': {'discount_range': (0.25, 0.45), 'probability': 0.4},
    '新航线促销': {'discount_range': (0.30, 0.50), 'probability': 0.15},
    '淡季促销': {'discount_range': (0.20, 0.35), 'probability': 0.35},
    '周末特惠': {'discount_range': (0.08, 0.18), 'probability': 0.25},
    '早鸟特惠': {'discount_range': (0.12, 0.28), 'probability': 0.3}
}

SEASONAL_EVENTS = {
    '春运': {'months': [1, 2], 'price_multiplier': (1.3, 1.6)},
    '暑假': {'months': [7, 8], 'price_multiplier': (1.2, 1.5)},
    '国庆': {'months': [9, 10], 'price_multiplier': (1.25, 1.55)},
    '五一': {'months': [4, 5], 'price_multiplier': (1.15, 1.4)},
    '双十一': {'months': [11], 'price_multiplier': (0.7, 0.85)},
    '双十二': {'months': [12], 'price_multiplier': (0.75, 0.9)},
    '春节后淡季': {'months': [3], 'price_multiplier': (0.7, 0.85)},
    '秋季淡季': {'months': [11], 'price_multiplier': (0.75, 0.9)}
}

AIRLINE_SPECIFIC_DATES = {
    '中国国航': {'member_day': 12, 'anniversary': (9, 15)},
    '东方航空': {'member_day': 18, 'anniversary': (6, 25)},
    '南方航空': {'member_day': 28, 'anniversary': (7, 1)},
    '海南航空': {'member_day': 8, 'anniversary': (4, 16)},
    '深圳航空': {'member_day': 22, 'anniversary': (11, 18)},
    '四川航空': {'member_day': 19, 'anniversary': (8, 28)}
}

def generate_airline_event_calendar(start_date='2024-01-01', end_date='2026-12-31'):
    date_range = pd.date_range(start=start_date, end=end_date, freq='D')
    
    events = []
    
    for single_date in date_range:
        year = single_date.year
        month = single_date.month
        day = single_date.day
        
        seasonal_effect = 1.0
        active_season = None
        for season, info in SEASONAL_EVENTS.items():
            if month in info['months']:
                multiplier = np.random.uniform(*info['price_multiplier'])
                if multiplier > seasonal_effect:
                    seasonal_effect = multiplier
                    active_season = season
        
        for airline in AIRLINES:
            event_type = None
            discount = 0
            airline_dates = AIRLINE_SPECIFIC_DATES.get(airline, {})
            
            if day == airline_dates.get('member_day'):
                event_type = '会员日'
                discount = np.random.uniform(*EVENT_TYPES[event_type]['discount_range'])
            
            anniv = airline_dates.get('anniversary')
            if anniv and month == anniv[0] and day == anniv[1]:
                event_type = '周年庆'
                discount = np.random.uniform(*EVENT_TYPES[event_type]['discount_range'])
            
            if event_type is None:
                for evt_type, evt_info in EVENT_TYPES.items():
                    if evt_type not in ['会员日', '周年庆'] and random.random() < evt_info['probability'] / 365:
                        event_type = evt_type
                        discount = np.random.uniform(*evt_info['discount_range'])
                        break
            
            if event_type or seasonal_effect != 1.0:
                events.append({
                    'date': single_date,
                    'airline': airline,
                    'event_type': event_type,
                    'discount': discount,
                    'seasonal_effect': seasonal_effect,
                    'season': active_season,
                    'combined_effect': seasonal_effect * (1 - discount) if discount > 0 else seasonal_effect
                })
    
    df = pd.DataFrame(events)
    return df

def get_event_features(date, airline=None):
    if isinstance(date, str):
        date = pd.to_datetime(date)
    
    features = {
        'is_member_day': 0,
        'is_anniversary': 0,
        'is_promotion': 0,
        'discount_amount': 0,
        'seasonal_effect': 1.0,
        'event_impact': 0
    }
    
    if airline and airline in AIRLINE_SPECIFIC_DATES:
        airline_dates = AIRLINE_SPECIFIC_DATES[airline]
        if date.day == airline_dates.get('member_day'):
            features['is_member_day'] = 1
            features['discount_amount'] = np.random.uniform(0.15, 0.30)
        
        anniv = airline_dates.get('anniversary')
        if anniv and date.month == anniv[0] and date.day == anniv[1]:
            features['is_anniversary'] = 1
            features['discount_amount'] = max(features['discount_amount'], np.random.uniform(0.20, 0.40))
    
    for season, info in SEASONAL_EVENTS.items():
        if date.month in info['months']:
            features['seasonal_effect'] = np.random.uniform(*info['price_multiplier'])
            break
    
    if features['is_member_day'] or features['is_anniversary']:
        features['is_promotion'] = 1
        features['event_impact'] = features['seasonal_effect'] * (1 - features['discount_amount'])
    else:
        features['event_impact'] = features['seasonal_effect']
    
    return features

def get_event_calendar_summary(year=None):
    if year is None:
        year = datetime.now().year
    
    data = []
    for month in range(1, 13):
        for airline in AIRLINES:
            airline_dates = AIRLINE_SPECIFIC_DATES.get(airline, {})
            member_day = airline_dates.get('member_day', None)
            anniversary = airline_dates.get('anniversary', None)
            
            data.append({
                'airline': airline,
                'month': month,
                'member_day': member_day,
                'anniversary_date': f"{anniversary[0]}/{anniversary[1]}" if anniversary else None
            })
    
    return pd.DataFrame(data)

if __name__ == '__main__':
    print('生成航司活动日历...')
    calendar = generate_airline_event_calendar('2025-01-01', '2025-12-31')
    print(f'生成 {len(calendar)} 条活动记录')
    print('\n活动类型分布:')
    print(calendar['event_type'].value_counts())
    print('\n季节影响分布:')
    print(calendar['season'].value_counts())
    
    print('\n测试获取特征:')
    test_date = pd.to_datetime('2025-07-12')
    features = get_event_features(test_date, '中国国航')
    print(f'{test_date} 中国国航特征:', features)
