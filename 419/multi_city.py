import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from itertools import permutations, combinations

HUB_CITIES = ['北京', '上海', '广州', '深圳', '成都', '西安', '重庆', '杭州']

CITY_DISTANCES = {
    ('北京', '上海'): 1318,
    ('北京', '广州'): 2121,
    ('北京', '深圳'): 2160,
    ('北京', '成都'): 1800,
    ('北京', '西安'): 1200,
    ('北京', '重庆'): 1960,
    ('北京', '杭州'): 1279,
    ('上海', '广州'): 1420,
    ('上海', '深圳'): 1430,
    ('上海', '成都'): 1960,
    ('上海', '西安'): 1509,
    ('上海', '重庆'): 1700,
    ('上海', '杭州'): 190,
    ('广州', '深圳'): 147,
    ('广州', '成都'): 1540,
    ('广州', '西安'): 1530,
    ('广州', '重庆'): 1280,
    ('广州', '杭州'): 1250,
    ('深圳', '成都'): 1440,
    ('深圳', '西安'): 1740,
    ('深圳', '重庆'): 1290,
    ('深圳', '杭州'): 1260,
    ('成都', '西安'): 720,
    ('成都', '重庆'): 300,
    ('成都', '杭州'): 1900,
    ('西安', '重庆'): 790,
    ('西安', '杭州'): 1300,
    ('重庆', '杭州'): 1600
}

AIRLINE_HUBS = {
    '中国国航': ['北京', '成都', '上海', '深圳'],
    '东方航空': ['上海', '北京', '西安', '昆明'],
    '南方航空': ['广州', '北京', '乌鲁木齐', '重庆'],
    '海南航空': ['北京', '海口', '深圳', '西安'],
    '深圳航空': ['深圳', '北京', '广州', '成都'],
    '四川航空': ['成都', '重庆', '北京', '杭州']
}

TRANSFER_TIMES = {
    'short': 45,
    'medium': 90,
    'long': 120
}

def get_distance(city1, city2):
    key = tuple(sorted([city1, city2]))
    return CITY_DISTANCES.get(key, 1000)

def find_connecting_routes(origin, destination, date, max_connections=2):
    routes = []
    
    if (origin, destination) in [(k[0], k[1]) for k in CITY_DISTANCES.keys()] or \
       (destination, origin) in [(k[0], k[1]) for k in CITY_DISTANCES.keys()]:
        direct_dist = get_distance(origin, destination)
        routes.append({
            'type': '直飞',
            'segments': [(origin, destination)],
            'total_distance': direct_dist,
            'transfer_count': 0,
            'estimated_duration': max(1.5, direct_dist / 800)
        })
    
    if max_connections >= 1:
        for hub in HUB_CITIES:
            if hub == origin or hub == destination:
                continue
            
            seg1_dist = get_distance(origin, hub)
            seg2_dist = get_distance(hub, destination)
            
            if seg1_dist > 0 and seg2_dist > 0:
                total_dist = seg1_dist + seg2_dist
                duration = max(1.5, seg1_dist / 800) + max(1.5, seg2_dist / 800) + TRANSFER_TIMES['medium'] / 60
                
                routes.append({
                    'type': '中转',
                    'segments': [(origin, hub), (hub, destination)],
                    'transfer_city': hub,
                    'total_distance': total_dist,
                    'transfer_count': 1,
                    'transfer_time': TRANSFER_TIMES['medium'],
                    'estimated_duration': duration
                })
    
    if max_connections >= 2:
        for hub1 in HUB_CITIES:
            if hub1 == origin:
                continue
            for hub2 in HUB_CITIES:
                if hub2 == destination or hub2 == hub1:
                    continue
                
                seg1_dist = get_distance(origin, hub1)
                seg2_dist = get_distance(hub1, hub2)
                seg3_dist = get_distance(hub2, destination)
                
                if seg1_dist > 0 and seg2_dist > 0 and seg3_dist > 0:
                    total_dist = seg1_dist + seg2_dist + seg3_dist
                    duration = (max(1.5, seg1_dist / 800) + max(1.5, seg2_dist / 800) + 
                               max(1.5, seg3_dist / 800) + 2 * TRANSFER_TIMES['medium'] / 60)
                    
                    routes.append({
                        'type': '双中转',
                        'segments': [(origin, hub1), (hub1, hub2), (hub2, destination)],
                        'transfer_cities': [hub1, hub2],
                        'total_distance': total_dist,
                        'transfer_count': 2,
                        'transfer_time': 2 * TRANSFER_TIMES['medium'],
                        'estimated_duration': duration
                    })
    
    return routes

def calculate_multi_city_price(route_info, model, departure_date, airline=None):
    from prediction import prepare_prediction_data_enhanced
    
    total_price = 0
    segment_prices = []
    
    for i, (seg_origin, seg_dest) in enumerate(route_info['segments']):
        route_key = f'{seg_origin}-{seg_dest}'
        
        try:
            segment_date = departure_date + timedelta(hours=i * 4)
            feature_data = prepare_prediction_data_enhanced(
                route_key, segment_date, airline=airline
            )
            price = model.predict_with_xgboost(feature_data)[0]
            
            segment_prices.append({
                'segment': f'{seg_origin}-{seg_dest}',
                'price': price,
                'date': segment_date
            })
            total_price += price
        except:
            base_price = 500 + get_distance(seg_origin, seg_dest) * 0.4
            segment_prices.append({
                'segment': f'{seg_origin}-{seg_dest}',
                'price': base_price,
                'date': departure_date
            })
            total_price += base_price
    
    if route_info['transfer_count'] == 1:
        total_price *= 0.85
    elif route_info['transfer_count'] >= 2:
        total_price *= 0.75
    
    total_price *= np.random.uniform(0.9, 1.1)
    
    return round(total_price, 0), segment_prices

def recommend_multi_city_itineraries(origin, destination, departure_date, model, 
                                     max_connections=2, top_n=5, airline=None):
    if isinstance(departure_date, str):
        departure_date = pd.to_datetime(departure_date)
    
    all_routes = find_connecting_routes(origin, destination, departure_date, max_connections)
    
    results = []
    for route in all_routes:
        total_price, segment_prices = calculate_multi_city_price(
            route, model, departure_date, airline
        )
        
        price_per_km = total_price / route['total_distance'] if route['total_distance'] > 0 else 0
        
        score = calculate_route_score(route, total_price)
        
        results.append({
            **route,
            'total_price': total_price,
            'segment_prices': segment_prices,
            'price_per_km': price_per_km,
            'score': score
        })
    
    results.sort(key=lambda x: x['score'], reverse=True)
    
    return results[:top_n]

def calculate_route_score(route, total_price):
    base_score = 1000
    
    price_penalty = total_price / 10
    
    transfer_penalty = route['transfer_count'] * 150
    
    duration_penalty = route['estimated_duration'] * 20
    
    distance_factor = route['total_distance'] / 1000
    
    score = base_score - price_penalty - transfer_penalty - duration_penalty + distance_factor * 10
    
    return max(0, score)

def find_open_jaw_trip(city1, city2, city3, date1, date2, model, airline=None):
    itinerary1, _ = calculate_multi_city_price(
        {'segments': [(city1, city2)], 'total_distance': get_distance(city1, city2), 
         'transfer_count': 0, 'estimated_duration': 2},
        model, date1, airline
    )
    
    itinerary2, _ = calculate_multi_city_price(
        {'segments': [(city2, city3)], 'total_distance': get_distance(city2, city3),
         'transfer_count': 0, 'estimated_duration': 2},
        model, date2, airline
    )
    
    return {
        'type': '开口程',
        'segments': [(city1, city2), (city2, city3)],
        'total_price': itinerary1 + itinerary2,
        'savings': 0.1 * (itinerary1 + itinerary2)
    }

def get_airline_transfer_info(airline, hub):
    min_transfer = 45
    if airline in ['中国国航', '东方航空', '南方航空']:
        min_transfer = 40
    elif airline in ['海南航空']:
        min_transfer = 50
    
    return {
        'min_transfer_time': min_transfer,
        'hub_operations': AIRLINE_HUBS.get(airline, []),
        'is_hub': hub in AIRLINE_HUBS.get(airline, []),
        'through_check_in': hub in AIRLINE_HUBS.get(airline, [])
    }

if __name__ == '__main__':
    print('测试多城市联运功能...')
    
    routes = find_connecting_routes('北京', '三亚', '2025-08-15', max_connections=1)
    print(f'找到 {len(routes)} 条航线:')
    for route in routes:
        print(f"  {route['type']}: {route['segments']}, 距离: {route['total_distance']}km, 时长: {route['estimated_duration']:.1f}h")
    
    print('\n开口程测试:')
    print(find_open_jaw_trip('北京', '上海', '广州', '2025-08-15', '2025-08-20', None))
