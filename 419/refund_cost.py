import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

FARE_TYPES = {
    'economy_discount': {
        'name': '经济舱折扣票',
        'refund_fee_rate': [0.3, 0.2, 0.1, 0.05],
        'change_fee_rate': [0.2, 0.15, 0.1, 0.05],
        'no_show_fee': 1.0,
        'refund_before_departure': True,
        'change_before_departure': True,
        'description': '最低折扣，退改签费用最高'
    },
    'economy_standard': {
        'name': '经济舱标准票',
        'refund_fee_rate': [0.15, 0.1, 0.05, 0],
        'change_fee_rate': [0.1, 0.05, 0, 0],
        'no_show_fee': 0.5,
        'refund_before_departure': True,
        'change_before_departure': True,
        'description': '标准经济舱，退改签费用适中'
    },
    'economy_flexible': {
        'name': '经济舱全价票',
        'refund_fee_rate': [0, 0, 0, 0],
        'change_fee_rate': [0, 0, 0, 0],
        'no_show_fee': 0.1,
        'refund_before_departure': True,
        'change_before_departure': True,
        'description': '全价经济舱，免费退改签'
    },
    'business_discount': {
        'name': '商务舱折扣票',
        'refund_fee_rate': [0.2, 0.15, 0.1, 0.05],
        'change_fee_rate': [0.15, 0.1, 0.05, 0],
        'no_show_fee': 0.3,
        'refund_before_departure': True,
        'change_before_departure': True,
        'description': '商务舱折扣票'
    },
    'business_standard': {
        'name': '商务舱标准票',
        'refund_fee_rate': [0.1, 0.05, 0, 0],
        'change_fee_rate': [0.05, 0, 0, 0],
        'no_show_fee': 0.1,
        'refund_before_departure': True,
        'change_before_departure': True,
        'description': '商务舱标准票，退改签优惠'
    },
    'first_class': {
        'name': '头等舱',
        'refund_fee_rate': [0, 0, 0, 0],
        'change_fee_rate': [0, 0, 0, 0],
        'no_show_fee': 0,
        'refund_before_departure': True,
        'change_before_departure': True,
        'description': '头等舱，免费退改签'
    }
}

TIME_THRESHOLDS = [
    ('before_7_days', 7, '出发前7天以上'),
    ('before_3_7_days', 3, '出发前3-7天'),
    ('before_1_3_days', 1, '出发前1-3天'),
    ('before_24h', 0, '出发前24小时内')
]

AIRLINE_SPECIFIC_POLICIES = {
    '中国国航': {
        'economy_discount': {'refund_multiplier': 1.0, 'change_multiplier': 1.0},
        'economy_standard': {'refund_multiplier': 0.8, 'change_multiplier': 0.8},
        'free_cancellation_window': 24
    },
    '东方航空': {
        'economy_discount': {'refund_multiplier': 1.1, 'change_multiplier': 1.0},
        'economy_standard': {'refund_multiplier': 0.9, 'change_multiplier': 0.8},
        'free_cancellation_window': 24
    },
    '南方航空': {
        'economy_discount': {'refund_multiplier': 1.0, 'change_multiplier': 0.9},
        'economy_standard': {'refund_multiplier': 0.8, 'change_multiplier': 0.7},
        'free_cancellation_window': 48
    },
    '海南航空': {
        'economy_discount': {'refund_multiplier': 1.2, 'change_multiplier': 1.1},
        'economy_standard': {'refund_multiplier': 0.9, 'change_multiplier': 0.9},
        'free_cancellation_window': 24
    },
    '深圳航空': {
        'economy_discount': {'refund_multiplier': 1.0, 'change_multiplier': 1.0},
        'economy_standard': {'refund_multiplier': 0.85, 'change_multiplier': 0.8},
        'free_cancellation_window': 24
    },
    '四川航空': {
        'economy_discount': {'refund_multiplier': 0.9, 'change_multiplier': 0.9},
        'economy_standard': {'refund_multiplier': 0.8, 'change_multiplier': 0.75},
        'free_cancellation_window': 36
    }
}

def get_time_category(departure_date: datetime, 
                      current_date: Optional[datetime] = None) -> Tuple[int, str]:
    if current_date is None:
        current_date = datetime.now()
    
    days_to_departure = (departure_date - current_date).total_seconds() / 86400
    
    if days_to_departure >= 7:
        return 0, '出发前7天以上'
    elif days_to_departure >= 3:
        return 1, '出发前3-7天'
    elif days_to_departure >= 1:
        return 2, '出发前1-3天'
    else:
        return 3, '出发前24小时内'

def calculate_refund_cost(original_price: float, fare_type: str, 
                          departure_date: datetime, 
                          current_date: Optional[datetime] = None,
                          airline: Optional[str] = None,
                          is_no_show: bool = False) -> Dict:
    if fare_type not in FARE_TYPES:
        raise ValueError(f"未知舱位类型: {fare_type}")
    
    fare_info = FARE_TYPES[fare_type]
    time_idx, time_desc = get_time_category(departure_date, current_date)
    
    if is_no_show:
        refund_rate = 1 - fare_info['no_show_fee']
        refund_amount = original_price * refund_rate
        fee_amount = original_price * fare_info['no_show_fee']
        
        return {
            'fare_type': fare_info['name'],
            'time_category': '误机(No Show)',
            'original_price': original_price,
            'refund_rate': round(refund_rate * 100, 1),
            'refund_amount': round(refund_amount, 0),
            'fee_amount': round(fee_amount, 0),
            'fee_rate': round(fare_info['no_show_fee'] * 100, 1),
            'can_refund': True,
            'description': f"误机后退票，收取{fare_info['no_show_fee']*100:.0f}%费用"
        }
    
    if not fare_info['refund_before_departure']:
        return {
            'fare_type': fare_info['name'],
            'time_category': time_desc,
            'original_price': original_price,
            'refund_rate': 0,
            'refund_amount': 0,
            'fee_amount': original_price,
            'fee_rate': 100,
            'can_refund': False,
            'description': '该舱位不支持退票'
        }
    
    base_fee_rate = fare_info['refund_fee_rate'][time_idx]
    
    if airline and airline in AIRLINE_SPECIFIC_POLICIES:
        policy = AIRLINE_SPECIFIC_POLICIES[airline]
        if fare_type in policy:
            base_fee_rate *= policy[fare_type].get('refund_multiplier', 1.0)
    
    fee_amount = original_price * base_fee_rate
    refund_amount = original_price - fee_amount
    
    return {
        'fare_type': fare_info['name'],
        'time_category': time_desc,
        'original_price': original_price,
        'refund_rate': round((1 - base_fee_rate) * 100, 1),
        'refund_amount': round(refund_amount, 0),
        'fee_amount': round(fee_amount, 0),
        'fee_rate': round(base_fee_rate * 100, 1),
        'can_refund': True,
        'description': f"{time_desc}退票，收取{base_fee_rate*100:.0f}%费用"
    }

def calculate_change_cost(original_price: float, new_price: float,
                          fare_type: str, departure_date: datetime,
                          current_date: Optional[datetime] = None,
                          airline: Optional[str] = None) -> Dict:
    if fare_type not in FARE_TYPES:
        raise ValueError(f"未知舱位类型: {fare_type}")
    
    fare_info = FARE_TYPES[fare_type]
    time_idx, time_desc = get_time_category(departure_date, current_date)
    
    if not fare_info['change_before_departure']:
        return {
            'fare_type': fare_info['name'],
            'time_category': time_desc,
            'original_price': original_price,
            'new_price': new_price,
            'change_fee': 0,
            'price_difference': max(0, new_price - original_price),
            'total_cost': max(0, new_price - original_price),
            'can_change': False,
            'description': '该舱位不支持改期'
        }
    
    base_fee_rate = fare_info['change_fee_rate'][time_idx]
    
    if airline and airline in AIRLINE_SPECIFIC_POLICIES:
        policy = AIRLINE_SPECIFIC_POLICIES[airline]
        if fare_type in policy:
            base_fee_rate *= policy[fare_type].get('change_multiplier', 1.0)
    
    change_fee = original_price * base_fee_rate
    price_difference = max(0, new_price - original_price)
    total_cost = change_fee + price_difference
    
    return {
        'fare_type': fare_info['name'],
        'time_category': time_desc,
        'original_price': original_price,
        'new_price': new_price,
        'change_fee': round(change_fee, 0),
        'change_fee_rate': round(base_fee_rate * 100, 1),
        'price_difference': round(price_difference, 0),
        'total_cost': round(total_cost, 0),
        'can_change': True,
        'description': f"{time_desc}改期，手续费{base_fee_rate*100:.0f}%"
    }

def compare_fare_options(price_range: Tuple[float, float], 
                         departure_date: datetime,
                         airline: Optional[str] = None,
                         current_date: Optional[datetime] = None) -> List[Dict]:
    min_price, max_price = price_range
    
    options = []
    
    fare_mapping = [
        ('economy_discount', 0.6, '最优惠选择'),
        ('economy_standard', 0.8, '性价比之选'),
        ('economy_flexible', 1.0, '灵活之选'),
        ('business_discount', 1.5, '商务折扣'),
        ('business_standard', 2.0, '商务舒适'),
        ('first_class', 3.0, '豪华体验')
    ]
    
    for fare_type, price_multiplier, label in fare_mapping:
        estimated_price = min_price * price_multiplier
        
        if estimated_price > max_price * 1.5:
            continue
        
        refund_info = calculate_refund_cost(
            estimated_price, fare_type, departure_date, current_date, airline
        )
        
        change_info = calculate_change_cost(
            estimated_price, estimated_price * 1.1, fare_type,
            departure_date, current_date, airline
        )
        
        flexibility_score = calculate_flexibility_score(fare_type)
        
        options.append({
            'fare_type': fare_type,
            'fare_name': FARE_TYPES[fare_type]['name'],
            'label': label,
            'estimated_price': round(estimated_price, 0),
            'price_multiplier': price_multiplier,
            'refund_info': refund_info,
            'change_info': change_info,
            'flexibility_score': flexibility_score,
            'description': FARE_TYPES[fare_type]['description'],
            'recommendation': get_fare_recommendation(fare_type, estimated_price)
        })
    
    options.sort(key=lambda x: x['estimated_price'])
    
    return options

def calculate_flexibility_score(fare_type: str) -> float:
    fare_info = FARE_TYPES[fare_type]
    
    refund_scores = [1 - r for r in fare_info['refund_fee_rate']]
    avg_refund_score = sum(refund_scores) / len(refund_scores)
    
    change_scores = [1 - c for c in fare_info['change_fee_rate']]
    avg_change_score = sum(change_scores) / len(change_scores)
    
    no_show_score = 1 - fare_info['no_show_fee']
    
    total_score = (avg_refund_score * 0.4 + avg_change_score * 0.4 + no_show_score * 0.2) * 100
    
    return round(total_score, 1)

def get_fare_recommendation(fare_type: str, price: float) -> str:
    if fare_type == 'economy_discount':
        return '适合行程确定、预算有限的旅客'
    elif fare_type == 'economy_standard':
        return '适合大多数旅客，平衡价格和灵活性'
    elif fare_type == 'economy_flexible':
        return '适合行程可能变动的商务旅客'
    elif fare_type == 'business_discount':
        return '适合追求舒适度但预算有限的旅客'
    elif fare_type == 'business_standard':
        return '适合商务出行，需要灵活改签的旅客'
    elif fare_type == 'first_class':
        return '适合追求极致舒适和最大灵活性的旅客'
    return ''

def simulate_refund_scenarios(original_price: float, fare_type: str,
                              departure_date: datetime) -> List[Dict]:
    scenarios = []
    
    scenario_dates = [
        (departure_date - timedelta(days=14), '出发前14天'),
        (departure_date - timedelta(days=7), '出发前7天'),
        (departure_date - timedelta(days=3), '出发前3天'),
        (departure_date - timedelta(days=1), '出发前1天'),
        (departure_date - timedelta(hours=6), '出发前6小时'),
        (departure_date + timedelta(hours=1), '误机后')
    ]
    
    for scenario_date, label in scenario_dates:
        is_no_show = scenario_date > departure_date
        
        result = calculate_refund_cost(
            original_price, fare_type, departure_date, 
            scenario_date, is_no_show=is_no_show
        )
        
        scenarios.append({
            'scenario': label,
            'scenario_date': scenario_date.strftime('%Y-%m-%d %H:%M'),
            **result
        })
    
    return scenarios

def calculate_breakeven_point(discounted_price: float, full_price: float,
                              fare_type_discount: str, fare_type_full: str,
                              departure_date: datetime) -> Dict:
    discount_refund = calculate_refund_cost(
        discounted_price, fare_type_discount, departure_date,
        departure_date - timedelta(days=7)
    )
    
    full_refund = calculate_refund_cost(
        full_price, fare_type_full, departure_date,
        departure_date - timedelta(days=7)
    )
    
    price_diff = full_price - discounted_price
    refund_diff = full_refund['refund_amount'] - discount_refund['refund_amount']
    
    if refund_diff <= 0:
        breakeven_probability = 100
    else:
        breakeven_probability = (price_diff / refund_diff) * 100
    
    return {
        'discounted_price': discounted_price,
        'full_price': full_price,
        'price_savings': price_diff,
        'refund_diff': refund_diff,
        'breakeven_probability': round(min(100, breakeven_probability), 1),
        'recommendation': f"如果退票概率超过{min(100, breakeven_probability):.0f}%，选择全价票更划算"
    }

if __name__ == '__main__':
    print('测试退改签成本计算...')
    
    departure_date = datetime.now() + timedelta(days=10)
    
    print('\n退票费用计算:')
    result = calculate_refund_cost(1000, 'economy_discount', departure_date)
    print(f"折扣经济舱: {result}")
    
    result = calculate_refund_cost(1000, 'economy_flexible', departure_date)
    print(f"全价经济舱: {result}")
    
    print('\n改期费用计算:')
    result = calculate_change_cost(1000, 1200, 'economy_discount', departure_date)
    print(f"折扣经济舱改期: {result}")
    
    print('\n舱位对比:')
    options = compare_fare_options((800, 1500), departure_date)
    for opt in options:
        print(f"  {opt['fare_name']}: ¥{opt['estimated_price']}, 灵活度: {opt['flexibility_score']}")
    
    print('\n退票场景模拟:')
    scenarios = simulate_refund_scenarios(1000, 'economy_discount', departure_date)
    for sc in scenarios:
        print(f"  {sc['scenario']}: 退款¥{sc['refund_amount']}, 手续费¥{sc['fee_amount']}")
