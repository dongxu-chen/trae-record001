import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import random
from geopy.distance import geodesic
import warnings
warnings.filterwarnings('ignore')

np.random.seed(42)
random.seed(42)

BEIJING_CENTER = (39.9042, 116.4074)

def generate_restaurants(n=50):
    restaurants = []
    for i in range(n):
        lat = BEIJING_CENTER[0] + np.random.normal(0, 0.03)
        lon = BEIJING_CENTER[1] + np.random.normal(0, 0.03)
        is_new_restaurant = np.random.choice([True, False], p=[0.2, 0.8])
        historical_on_time_rate = np.round(np.random.uniform(0.75, 0.98), 2)
        if is_new_restaurant:
            historical_on_time_rate = np.round(np.random.uniform(0.70, 0.85), 2)
            total_orders = np.random.randint(10, 100)
        else:
            total_orders = np.random.randint(100, 2000)
        
        restaurants.append({
            'restaurant_id': f'R{i+1:03d}',
            'name': f'餐厅{i+1}',
            'lat': lat,
            'lon': lon,
            'avg_prep_time': np.random.randint(10, 35),
            'food_type': np.random.choice(['快餐', '中餐', '西餐', '日料', '火锅', '烧烤']),
            'rating': np.round(np.random.uniform(3.5, 5.0), 1),
            'peak_hour_capacity': np.random.randint(5, 20),
            'is_new_restaurant': int(is_new_restaurant),
            'historical_on_time_rate': historical_on_time_rate,
            'total_orders_completed': total_orders
        })
    return pd.DataFrame(restaurants)

def generate_riders(n=30):
    riders = []
    for i in range(n):
        lat = BEIJING_CENTER[0] + np.random.normal(0, 0.04)
        lon = BEIJING_CENTER[1] + np.random.normal(0, 0.04)
        riders.append({
            'rider_id': f'Rider{i+1:03d}',
            'name': f'骑手{i+1}',
            'lat': lat,
            'lon': lon,
            'avg_speed': np.random.randint(20, 35),
            'experience': np.random.randint(1, 36),
            'rating': np.round(np.random.uniform(3.5, 5.0), 1),
            'on_time_rate': np.round(np.random.uniform(0.85, 0.98), 2),
            'status': np.random.choice(['空闲', '配送中'], p=[0.6, 0.4]),
            'current_orders': 0
        })
    df = pd.DataFrame(riders)
    df.loc[df['status'] == '配送中', 'current_orders'] = np.random.randint(1, 3, size=sum(df['status'] == '配送中'))
    return df

def generate_weather_data(base_date, days=7):
    weather_conditions = ['晴天', '多云', '小雨', '大雨', '雾', '雪']
    weather_weights = [0.4, 0.3, 0.15, 0.05, 0.07, 0.03]
    
    weather_records = []
    for day in range(days):
        date = base_date + timedelta(days=day)
        for hour in range(24):
            temp = np.random.normal(20, 8)
            wind_speed = np.random.uniform(0, 20)
            condition = np.random.choice(weather_conditions, p=weather_weights)
            
            weather_impact = 1.0
            if condition == '小雨':
                weather_impact = 1.15
            elif condition == '大雨':
                weather_impact = 1.35
            elif condition == '雾':
                weather_impact = 1.25
            elif condition == '雪':
                weather_impact = 1.40
            
            weather_records.append({
                'date': date,
                'hour': hour,
                'temperature': np.round(temp, 1),
                'wind_speed': np.round(wind_speed, 1),
                'weather_condition': condition,
                'weather_impact_factor': np.round(weather_impact, 2)
            })
    return pd.DataFrame(weather_records)

def generate_traffic_data(base_date, days=7):
    traffic_records = []
    for day in range(days):
        date = base_date + timedelta(days=day)
        is_weekend = date.weekday() >= 5
        
        for hour in range(24):
            base_traffic = 0.3
            
            if 7 <= hour <= 9:
                base_traffic = 0.9 if not is_weekend else 0.4
            elif 11 <= hour <= 13:
                base_traffic = 0.8
            elif 17 <= hour <= 19:
                base_traffic = 0.85 if not is_weekend else 0.6
            elif 21 <= hour <= 22:
                base_traffic = 0.5
            
            traffic = np.clip(base_traffic + np.random.normal(0, 0.1), 0, 1)
            
            traffic_records.append({
                'date': date,
                'hour': hour,
                'is_weekend': is_weekend,
                'traffic_index': np.round(traffic, 2),
                'traffic_impact_factor': np.round(1 + traffic * 0.5, 2)
            })
    return pd.DataFrame(traffic_records)

def calculate_distance(lat1, lon1, lat2, lon2):
    return geodesic((lat1, lon1), (lat2, lon2)).kilometers

def generate_orders(restaurants, riders, weather, traffic, n=2000):
    orders = []
    base_date = datetime(2024, 1, 1)
    
    for i in range(n):
        restaurant = restaurants.sample(1).iloc[0]
        rider = riders.sample(1).iloc[0]
        
        order_date = base_date + timedelta(days=np.random.randint(0, 7))
        hour_probs = [0.01]*6 + [0.02]*3 + [0.08]*2 + [0.03]*4 + [0.08]*2 + [0.06]*4 + [0.04]*3
        hour_probs = np.array(hour_probs) / sum(hour_probs)
        order_hour = np.random.choice(range(24), p=hour_probs)
        order_time = order_date.replace(hour=order_hour, minute=np.random.randint(0, 60))
        
        is_weekend = order_date.weekday() >= 5
        
        user_lat = BEIJING_CENTER[0] + np.random.normal(0, 0.04)
        user_lon = BEIJING_CENTER[1] + np.random.normal(0, 0.04)
        
        distance_rest_to_user = calculate_distance(
            restaurant['lat'], restaurant['lon'],
            user_lat, user_lon
        )
        distance_rider_to_rest = calculate_distance(
            rider['lat'], rider['lon'],
            restaurant['lat'], restaurant['lon']
        )
        total_distance = distance_rider_to_rest + distance_rest_to_user
        
        weather_row = weather[(weather['date'].dt.date == order_date.date()) & 
                              (weather['hour'] == order_hour)].iloc[0]
        traffic_row = traffic[(traffic['date'].dt.date == order_date.date()) & 
                              (traffic['hour'] == order_hour)].iloc[0]
        
        has_elevator = np.random.choice([True, False], p=[0.7, 0.3])
        floor = np.random.randint(1, 31)
        is_office_building = np.random.choice([True, False], p=[0.3, 0.7])
        
        elevator_wait = 0
        if not has_elevator:
            elevator_wait = floor * 0.5
        else:
            if is_office_building:
                elevator_wait = min(floor * 0.15 + np.random.exponential(1.5), 8)
            else:
                elevator_wait = min(floor * 0.1 + np.random.exponential(1), 5)
        
        peak_hour = (11 <= order_hour <= 13) or (17 <= order_hour <= 19)
        prep_time = restaurant['avg_prep_time']
        
        if restaurant['is_new_restaurant']:
            prep_variance = 1.2
            prep_time *= prep_variance
            delay_due_to_new = prep_time * (1 - restaurant['historical_on_time_rate']) * 0.5
            prep_time += delay_due_to_new
        else:
            if peak_hour:
                prep_time *= 1.3
            prep_time += np.random.normal(0, 3)
        
        rider_speed = rider['avg_speed'] * np.random.uniform(0.8, 1.1)
        travel_time = (total_distance / rider_speed) * 60
        
        base_delivery_time = prep_time + travel_time + elevator_wait
        final_delivery_time = (base_delivery_time * 
                               weather_row['weather_impact_factor'] * 
                               traffic_row['traffic_impact_factor'])
        
        final_delivery_time += np.random.normal(0, 5)
        final_delivery_time = max(20, final_delivery_time)
        
        delay_reasons = []
        delay_minutes = max(0, final_delivery_time - base_delivery_time)
        
        if weather_row['weather_impact_factor'] > 1.1:
            delay_reasons.append(f"天气影响({weather_row['weather_condition']})")
        if traffic_row['traffic_index'] > 0.6:
            delay_reasons.append("交通拥堵")
        if not has_elevator and floor > 5:
            delay_reasons.append("无电梯高楼层")
        if is_office_building and floor > 10:
            delay_reasons.append("写字楼电梯等待")
        if peak_hour:
            delay_reasons.append("用餐高峰期")
        if restaurant['is_new_restaurant']:
            delay_reasons.append("新餐厅备餐波动")
        
        orders.append({
            'order_id': f'ORD{i+1:06d}',
            'restaurant_id': restaurant['restaurant_id'],
            'rider_id': rider['rider_id'],
            'order_time': order_time,
            'order_hour': order_hour,
            'is_weekend': is_weekend,
            'is_peak_hour': peak_hour,
            'user_lat': user_lat,
            'user_lon': user_lon,
            'restaurant_lat': restaurant['lat'],
            'restaurant_lon': restaurant['lon'],
            'rider_start_lat': rider['lat'],
            'rider_start_lon': rider['lon'],
            'distance_km': np.round(total_distance, 2),
            'distance_rest_to_user_km': np.round(distance_rest_to_user, 2),
            'distance_rider_to_rest_km': np.round(distance_rider_to_rest, 2),
            'food_type': restaurant['food_type'],
            'prep_time_min': np.round(prep_time, 1),
            'rider_avg_speed': rider_speed,
            'has_elevator': has_elevator,
            'floor': floor,
            'is_office_building': int(is_office_building),
            'elevator_wait_min': np.round(elevator_wait, 1),
            'weather_condition': weather_row['weather_condition'],
            'weather_impact': weather_row['weather_impact_factor'],
            'traffic_index': traffic_row['traffic_index'],
            'traffic_impact': traffic_row['traffic_impact_factor'],
            'rider_experience_months': rider['experience'],
            'rider_rating': rider['rating'],
            'is_new_restaurant': restaurant['is_new_restaurant'],
            'restaurant_on_time_rate': restaurant['historical_on_time_rate'],
            'restaurant_total_orders': restaurant['total_orders_completed'],
            'delivery_time_min': np.round(final_delivery_time, 1),
            'delay_minutes': np.round(delay_minutes, 1),
            'delay_reasons': '; '.join(delay_reasons) if delay_reasons else '无'
        })
    
    return pd.DataFrame(orders)

def generate_all_data():
    print("正在生成餐厅数据...")
    restaurants = generate_restaurants(50)
    
    print("正在生成骑手数据...")
    riders = generate_riders(30)
    
    base_date = datetime(2024, 1, 1)
    print("正在生成天气数据...")
    weather = generate_weather_data(base_date, 7)
    
    print("正在生成交通数据...")
    traffic = generate_traffic_data(base_date, 7)
    
    print("正在生成订单数据...")
    orders = generate_orders(restaurants, riders, weather, traffic, 3000)
    
    print("数据生成完成!")
    return {
        'restaurants': restaurants,
        'riders': riders,
        'weather': weather,
        'traffic': traffic,
        'orders': orders
    }

if __name__ == '__main__':
    data = generate_all_data()
    for name, df in data.items():
        df.to_csv(f'data/{name}.csv', index=False, encoding='utf-8-sig')
        print(f"{name}: {len(df)} 条记录")
