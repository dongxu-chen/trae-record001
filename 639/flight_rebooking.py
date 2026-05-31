import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
from datetime import datetime, timedelta
import random

from data_generator import AIRLINES, AIRPORTS, generate_weather, generate_flow_control, get_sector_info


class AlternativeFlight:
    def __init__(self, flight_id: str, airline: str, airline_name: str,
                 departure_airport: str, arrival_airport: str,
                 departure_time: datetime, arrival_time: datetime,
                 estimated_delay_prob: float, estimated_delay_minutes: float,
                 price: float, cabin_class: str = '经济舱',
                 seats_available: int = 10):
        self.flight_id = flight_id
        self.airline = airline
        self.airline_name = airline_name
        self.departure_airport = departure_airport
        self.arrival_airport = arrival_airport
        self.departure_time = departure_time
        self.arrival_time = arrival_time
        self.estimated_delay_prob = estimated_delay_prob
        self.estimated_delay_minutes = estimated_delay_minutes
        self.price = price
        self.cabin_class = cabin_class
        self.seats_available = seats_available
        
    def to_dict(self) -> Dict:
        return {
            'flight_id': self.flight_id,
            'airline': self.airline,
            'airline_name': self.airline_name,
            'departure_airport': self.departure_airport,
            'arrival_airport': self.arrival_airport,
            'departure_time': self.departure_time.strftime('%H:%M'),
            'arrival_time': self.arrival_time.strftime('%H:%M'),
            'duration': str(self.arrival_time - self.departure_time),
            'estimated_delay_prob': round(self.estimated_delay_prob * 100, 1),
            'estimated_delay_minutes': round(self.estimated_delay_minutes, 1),
            'price': self.price,
            'cabin_class': self.cabin_class,
            'seats_available': self.seats_available
        }


class RebookingRecommender:
    def __init__(self):
        self.base_flight_duration = self._init_flight_durations()
        
    def _init_flight_durations(self) -> Dict[Tuple[str, str], int]:
        durations = {}
        for dep in AIRPORTS:
            for arr in AIRPORTS:
                if dep != arr:
                    base_time = random.randint(90, 180)
                    durations[(dep, arr)] = base_time
        return durations
    
    def estimate_flight_delay(self, airline: str, dep_airport: str, arr_airport: str,
                              departure_hour: int, weather: str, 
                              flow_control: str, hist_30d: float) -> Tuple[float, float]:
        airline_info = AIRLINES[airline]
        
        weather_factor = {
            '晴朗': 0.1, '多云': 0.15, '小雨': 0.4, '中雨': 0.6,
            '雷暴': 0.85, '大雾': 0.9, '大雪': 0.95
        }.get(weather, 0.2)
        
        flow_factor = {'无': 0.1, '轻度': 0.3, '中度': 0.5, '重度': 0.75}.get(flow_control, 0.2)
        
        hour_factor = 0.3 if 7 <= departure_hour <= 9 else \
                      0.35 if 17 <= departure_hour <= 20 else 0.15
        
        hist_factor = min(hist_30d / 100, 0.5)
        sector_info = get_sector_info(dep_airport, arr_airport)
        sector_congestion = sector_info['sector_congestion']
        
        delay_prob = (airline_info['delay_rate'] * 0.5 + 
                     weather_factor * 0.25 + 
                     flow_factor * 0.25 + 
                     hour_factor * 0.15 +
                     hist_factor * 0.2 +
                     sector_congestion * 0.15)
        delay_prob = min(0.95, max(0.05, delay_prob))
        
        if delay_prob > 0.5:
            delay_minutes = 30 + delay_prob * 120 + weather_factor * 60
        else:
            delay_minutes = delay_prob * 60
        
        return delay_prob, delay_minutes
    
    def generate_alternative_flights(self, 
                                     original_dep_airport: str,
                                     original_arr_airport: str,
                                     original_date: datetime.date,
                                     original_departure_hour: int,
                                     original_departure_minute: int,
                                     weather: str = '晴朗',
                                     flow_control: str = '无',
                                     max_search_hours: int = 12,
                                     num_flights: int = 8,
                                     airlines_filter: List[str] = None) -> List[AlternativeFlight]:
        
        alternatives = []
        route_key = (original_dep_airport, original_arr_airport)
        base_duration = self.base_flight_duration.get(route_key, 120)
        
        original_time = datetime.combine(original_date, 
                                         datetime.min.time().replace(
                                             hour=original_departure_hour, 
                                             minute=original_departure_minute
                                         ))
        
        airline_codes = airlines_filter or list(AIRLINES.keys())
        
        for i in range(num_flights):
            airline = random.choice(airline_codes)
            airline_name = AIRLINES[airline]['name']
            
            offset_hours = random.uniform(-2, max_search_hours)
            dep_time = original_time + timedelta(hours=offset_hours)
            dep_time = dep_time.replace(minute=random.choice([0, 15, 30, 45]))
            
            if dep_time.hour < 6 or dep_time.hour >= 24:
                dep_time = dep_time.replace(hour=max(6, min(23, dep_time.hour)))
            
            arr_time = dep_time + timedelta(minutes=base_duration + random.randint(-10, 20))
            
            flight_weather = generate_weather()
            flight_flow = generate_flow_control(original_dep_airport)
            
            hist_30d = random.uniform(10, 40)
            delay_prob, delay_minutes = self.estimate_flight_delay(
                airline, original_dep_airport, original_arr_airport,
                dep_time.hour, flight_weather, flight_flow, hist_30d
            )
            
            base_price = 500 + base_duration * 3
            price_adj = 1.0
            if offset_hours < 1:
                price_adj = 1.3
            elif offset_hours < 3:
                price_adj = 1.15
            
            if airline in ['CA', 'MU', 'CZ']:
                price_adj *= 1.1
            
            price = int(base_price * price_adj * (0.9 + random.random() * 0.3))
            
            cabin_classes = ['经济舱', '超级经济舱', '商务舱']
            cabin_class = random.choices(cabin_classes, weights=[0.7, 0.2, 0.1])[0]
            if cabin_class == '超级经济舱':
                price = int(price * 1.5)
            elif cabin_class == '商务舱':
                price = int(price * 2.5)
            
            flight = AlternativeFlight(
                flight_id=f"{airline}{random.randint(1000, 9999)}",
                airline=airline,
                airline_name=airline_name,
                departure_airport=original_dep_airport,
                arrival_airport=original_arr_airport,
                departure_time=dep_time,
                arrival_time=arr_time,
                estimated_delay_prob=delay_prob,
                estimated_delay_minutes=delay_minutes,
                price=price,
                cabin_class=cabin_class,
                seats_available=random.randint(1, 20)
            )
            
            alternatives.append(flight)
        
        alternatives.sort(key=lambda x: x.departure_time)
        
        return alternatives
    
    def calculate_rebooking_score(self, flight: AlternativeFlight,
                                   original_departure: datetime,
                                   original_delay_minutes: float,
                                   priority: str = 'balanced') -> Dict:
        time_diff = (flight.departure_time - original_departure).total_seconds() / 3600
        
        if time_diff < 0:
            time_score = 100 + time_diff * 10
        elif time_diff < 2:
            time_score = 100 - time_diff * 10
        elif time_diff < 6:
            time_score = 80 - (time_diff - 2) * 5
        else:
            time_score = max(0, 60 - (time_diff - 6) * 3)
        
        reliability_score = (1 - flight.estimated_delay_prob) * 100
        
        price_score = max(0, 100 - (flight.price - 500) / 20)
        
        on_time_improvement = max(0, original_delay_minutes - flight.estimated_delay_minutes)
        improvement_score = min(100, on_time_improvement * 2)
        
        if priority == 'time':
            weights = {'time': 0.4, 'reliability': 0.3, 'price': 0.15, 'improvement': 0.15}
        elif priority == 'reliability':
            weights = {'time': 0.2, 'reliability': 0.45, 'price': 0.15, 'improvement': 0.2}
        elif priority == 'price':
            weights = {'time': 0.2, 'reliability': 0.2, 'price': 0.45, 'improvement': 0.15}
        else:
            weights = {'time': 0.25, 'reliability': 0.3, 'price': 0.25, 'improvement': 0.2}
        
        total_score = (
            time_score * weights['time'] +
            reliability_score * weights['reliability'] +
            price_score * weights['price'] +
            improvement_score * weights['improvement']
        )
        
        return {
            'time_score': round(time_score, 1),
            'reliability_score': round(reliability_score, 1),
            'price_score': round(price_score, 1),
            'improvement_score': round(improvement_score, 1),
            'total_score': round(total_score, 1)
        }
    
    def recommend_rebooking(self, alternatives: List[AlternativeFlight],
                             original_departure: datetime,
                             original_delay_minutes: float,
                             priority: str = 'balanced',
                             top_n: int = 5) -> List[Dict]:
        scored_flights = []
        
        for flight in alternatives:
            scores = self.calculate_rebooking_score(
                flight, original_departure, original_delay_minutes, priority
            )
            
            flight_dict = flight.to_dict()
            flight_dict.update(scores)
            
            delay_level = '高' if flight.estimated_delay_prob > 0.5 else '中' if flight.estimated_delay_prob > 0.3 else '低'
            
            flight_dict['recommendation_level'] = self._get_recommendation_level(
                scores['total_score'], delay_level
            )
            
            scored_flights.append(flight_dict)
        
        scored_flights.sort(key=lambda x: x['total_score'], reverse=True)
        
        return scored_flights[:top_n]
    
    def _get_recommendation_level(self, total_score: float, delay_level: str) -> str:
        if delay_level == '高':
            threshold_adjust = -10
        elif delay_level == '低':
            threshold_adjust = 10
        else:
            threshold_adjust = 0
        
        if total_score >= 75 + threshold_adjust:
            return '强烈推荐'
        elif total_score >= 60 + threshold_adjust:
            return '推荐'
        elif total_score >= 45 + threshold_adjust:
            return '可考虑'
        else:
            return '不推荐'
    
    def get_best_recommendation(self, scored_flights: List[Dict]) -> Optional[Dict]:
        for flight in scored_flights:
            if flight['recommendation_level'] in ['强烈推荐', '推荐']:
                return flight
        return scored_flights[0] if scored_flights else None


def get_priority_description(priority: str) -> str:
    descriptions = {
        'time': '时间优先：优先选择起飞时间接近原航班的选项',
        'reliability': '准点优先：优先选择准点率最高的航班',
        'price': '价格优先：优先选择价格最低的选项',
        'balanced': '综合平衡：在时间、准点率、价格间寻求平衡'
    }
    return descriptions.get(priority, '')


if __name__ == '__main__':
    recommender = RebookingRecommender()
    
    print("=== 测试改签推荐 ===")
    
    today = datetime.now().date()
    alternatives = recommender.generate_alternative_flights(
        original_dep_airport='PEK',
        original_arr_airport='SHA',
        original_date=today,
        original_departure_hour=10,
        original_departure_minute=0,
        max_search_hours=8,
        num_flights=6
    )
    
    print(f"\n生成 {len(alternatives)} 个备选航班")
    
    original_departure = datetime.combine(today, datetime.min.time().replace(hour=10, minute=0))
    scored = recommender.recommend_rebooking(
        alternatives, original_departure, original_delay_minutes=90, priority='balanced'
    )
    
    print("\nTop 3 推荐航班:")
    for i, flight in enumerate(scored[:3], 1):
        print(f"{i}. {flight['flight_id']} {flight['airline_name']}")
        print(f"   时间: {flight['departure_time']} - {flight['arrival_time']}")
        print(f"   延误概率: {flight['estimated_delay_prob']}%")
        print(f"   价格: ¥{flight['price']} ({flight['cabin_class']})")
        print(f"   综合评分: {flight['total_score']} - {flight['recommendation_level']}")
        print()
