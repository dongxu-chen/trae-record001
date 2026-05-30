import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from geopy.distance import geodesic
from typing import List, Dict, Tuple

class DelayWarningSystem:
    def __init__(self, warning_threshold=5, critical_threshold=15):
        self.warning_threshold = warning_threshold
        self.critical_threshold = critical_threshold
        self.delivery_tracking = {}
    
    def analyze_delay_risk(self, 
                           predicted_eta: float,
                           upper_bound: float,
                           distance_km: float,
                           traffic_condition: str,
                           weather: str,
                           courier_on_time_rate: float,
                           current_progress: float = 0,
                           elapsed_minutes: float = 0) -> Dict:
        
        delay_risk_score = 0
        risk_factors = []
        
        eta_uncertainty = (upper_bound - predicted_eta) / predicted_eta
        if eta_uncertainty > 0.3:
            delay_risk_score += 2
            risk_factors.append('ETA预测不确定性高')
        elif eta_uncertainty > 0.2:
            delay_risk_score += 1
            risk_factors.append('ETA存在一定不确定性')
        
        traffic_impact = {
            '畅通': 0, '缓行': 1, '拥堵': 2, '严重拥堵': 3
        }.get(traffic_condition, 0)
        delay_risk_score += traffic_impact
        if traffic_impact > 0:
            risk_factors.append(f'路况: {traffic_condition}')
        
        weather_impact = {
            '晴': 0, '多云': 0, '小雨': 1, '中雨': 2,
            '大雨': 3, '小雪': 1, '中雪': 2
        }.get(weather, 0)
        delay_risk_score += weather_impact
        if weather_impact > 0:
            risk_factors.append(f'天气: {weather}')
        
        if courier_on_time_rate < 0.85:
            delay_risk_score += 2
            risk_factors.append('配送员准时率较低')
        elif courier_on_time_rate < 0.9:
            delay_risk_score += 1
            risk_factors.append('配送员准时率一般')
        
        if current_progress > 0 and elapsed_minutes > 0:
            expected_progress = (elapsed_minutes / predicted_eta) * 100
            progress_gap = expected_progress - current_progress
            
            if progress_gap > 20:
                delay_risk_score += 3
                risk_factors.append('配送进度严重滞后')
            elif progress_gap > 10:
                delay_risk_score += 2
                risk_factors.append('配送进度滞后')
        
        if delay_risk_score >= 6:
            risk_level = '严重'
            warning_level = 'critical'
        elif delay_risk_score >= 4:
            risk_level = '高'
            warning_level = 'warning'
        elif delay_risk_score >= 2:
            risk_level = '中'
            warning_level = 'caution'
        else:
            risk_level = '低'
            warning_level = 'normal'
        
        estimated_delay = max(0, upper_bound - predicted_eta) * (delay_risk_score / 6)
        
        return {
            'risk_score': delay_risk_score,
            'risk_level': risk_level,
            'warning_level': warning_level,
            'risk_factors': risk_factors,
            'estimated_delay_minutes': round(estimated_delay, 1),
            'recommended_action': self._get_recommendation(warning_level, risk_factors)
        }
    
    def _get_recommendation(self, warning_level: str, risk_factors: List[str]) -> List[str]:
        recommendations = []
        
        if warning_level == 'critical':
            recommendations.append('立即联系配送员确认情况')
            recommendations.append('准备启动应急预案')
            recommendations.append('提前通知客户可能延迟')
        elif warning_level == 'warning':
            recommendations.append('密切关注配送进度')
            recommendations.append('考虑联系配送员确认')
        elif warning_level == 'caution':
            recommendations.append('保持正常监控')
        
        if '路况' in str(risk_factors):
            recommendations.append('建议规划备选路线')
        
        if '天气' in str(risk_factors):
            recommendations.append('提醒配送员注意安全')
        
        if '准时率' in str(risk_factors):
            recommendations.append('考虑分配经验更丰富的配送员')
        
        return recommendations

class CourierScheduler:
    def __init__(self, couriers_df: pd.DataFrame, courier_profiler=None):
        self.couriers = couriers_df.copy()
        self.courier_history = {}
        self.courier_profiler = courier_profiler
        self.avg_daily_load = couriers_df['avg_daily_deliveries'].mean() if 'avg_daily_deliveries' in couriers_df.columns else 35
    
    def calculate_load_balance_factor(self, current_load, avg_speed, status):
        optimal_load = min(6, max(2, int(avg_speed / 5)))
        
        if current_load == 0:
            return 1.15
        elif current_load < optimal_load:
            return 1.0 + (optimal_load - current_load) * 0.05
        elif current_load == optimal_load:
            return 1.0
        else:
            overload = current_load - optimal_load
            return max(0.6, 1.0 - overload * 0.12)
    
    def calculate_eta_competitiveness(self, estimated_time, all_estimates):
        if len(all_estimates) == 0:
            return 1.0
        
        min_time = min(all_estimates)
        max_time = max(all_estimates)
        
        if max_time == min_time:
            return 1.0
        
        normalized = 1 - (estimated_time - min_time) / (max_time - min_time)
        return 0.7 + normalized * 0.3
    
    def calculate_region_preference_factor(self, courier_id, pickup_lat, pickup_lon, dropoff_lat, dropoff_lon):
        if self.courier_profiler is None:
            return 1.0, None, None
        
        pickup_advantage = self.courier_profiler.get_courier_region_advantage(
            courier_id, pickup_lat, pickup_lon
        )
        dropoff_advantage = self.courier_profiler.get_courier_region_advantage(
            courier_id, dropoff_lat, dropoff_lon
        )
        
        overall_advantage = (pickup_advantage + dropoff_advantage) / 2
        
        profile = self.courier_profiler.get_courier_profile(courier_id)
        pref_regions = []
        avoid_regions = []
        
        if profile:
            for pref in profile.get('preferred_regions', []):
                pref_regions.append({
                    'region': pref['region_key'],
                    'speed_advantage': pref['speed_advantage_pct']
                })
            for avoid in profile.get('avoid_regions', []):
                avoid_regions.append({
                    'region': avoid['region_key'],
                    'speed_disadvantage': avoid['speed_advantage_pct']
                })
        
        region_details = {
            'pickup_advantage': round((pickup_advantage - 1) * 100, 1),
            'dropoff_advantage': round((dropoff_advantage - 1) * 100, 1),
            'overall_advantage_pct': round((overall_advantage - 1) * 100, 1),
            'preferred_regions': pref_regions[:3],
            'avoid_regions': avoid_regions[:2]
        }
        
        return overall_advantage, pickup_advantage, dropoff_advantage, region_details
    
    def calculate_courier_suitability(self, 
                                      courier: pd.Series,
                                      pickup_lat: float,
                                      pickup_lon: float,
                                      dropoff_lat: float,
                                      dropoff_lon: float,
                                      order_time: datetime,
                                      priority: str = 'normal',
                                      all_estimated_times: list = None) -> Dict:
        
        courier_pos = (courier['current_lat'], courier['current_lon'])
        pickup_pos = (pickup_lat, pickup_lon)
        distance_to_pickup = geodesic(courier_pos, pickup_pos).km
        
        delivery_distance = geodesic(pickup_pos, (dropoff_lat, dropoff_lon)).km
        
        travel_time_to_pickup = (distance_to_pickup / courier['avg_speed']) * 60
        
        load_balance_factor = self.calculate_load_balance_factor(
            courier['current_load'], 
            courier['avg_speed'],
            courier['status']
        )
        
        status_score = {'空闲': 1.0, '配送中': 0.7, '休息': 0.15}.get(courier['status'], 0.3)
        
        priority_weights = {
            'urgent': {'eta': 0.5, 'efficiency': 0.3, 'load': 0.2},
            'normal': {'eta': 0.35, 'efficiency': 0.35, 'load': 0.3},
            'low': {'eta': 0.2, 'efficiency': 0.3, 'load': 0.5}
        }
        weights = priority_weights.get(priority, priority_weights['normal'])
        
        eta_factor = max(0, 1 - travel_time_to_pickup / 60)
        
        efficiency_score = (
            courier['reliability_score'] * 0.4 +
            courier['on_time_rate'] * 0.4 +
            min(1.0, courier['experience_months'] / 36) * 0.2
        )
        
        eta_competitiveness = self.calculate_eta_competitiveness(
            travel_time_to_pickup, 
            all_estimated_times if all_estimated_times else []
        )
        
        region_factor, pickup_adv, dropoff_adv, region_details = self.calculate_region_preference_factor(
            courier['courier_id'], pickup_lat, pickup_lon, dropoff_lat, dropoff_lon
        )
        
        priority_weights = {
            'urgent': {'eta': 0.45, 'efficiency': 0.25, 'load': 0.15, 'region': 0.15},
            'normal': {'eta': 0.3, 'efficiency': 0.3, 'load': 0.25, 'region': 0.15},
            'low': {'eta': 0.2, 'efficiency': 0.3, 'load': 0.35, 'region': 0.15}
        }
        weights = priority_weights.get(priority, priority_weights['normal'])
        
        base_score = 100
        distance_penalty = distance_to_pickup * 2.5
        
        weighted_score = (
            eta_factor * weights['eta'] +
            efficiency_score * weights['efficiency'] +
            load_balance_factor * weights['load'] +
            region_factor * weights['region']
        ) * 100
        
        suitability_score = (base_score - distance_penalty) * weighted_score / 100
        suitability_score = suitability_score * status_score * eta_competitiveness
        
        estimated_total_time = travel_time_to_pickup + (delivery_distance / courier['avg_speed']) * 60
        
        adjusted_total_time = estimated_total_time / max(0.85, region_factor)
        
        load_status = self._get_load_status(courier['current_load'])
        
        return {
            'courier_id': courier['courier_id'],
            'suitability_score': round(suitability_score, 1),
            'distance_to_pickup_km': round(distance_to_pickup, 2),
            'travel_time_to_pickup_min': round(travel_time_to_pickup, 1),
            'estimated_total_time_min': round(adjusted_total_time, 1),
            'raw_eta_min': round(estimated_total_time, 1),
            'region_adjustment_pct': round((1 - region_factor) * 100, 1),
            'current_load': courier['current_load'],
            'load_status': load_status,
            'load_balance_factor': round(load_balance_factor, 2),
            'region_advantage_pct': region_details['overall_advantage_pct'] if region_details else 0,
            'pickup_region_adv': region_details['pickup_advantage'] if region_details else 0,
            'dropoff_region_adv': region_details['dropoff_advantage'] if region_details else 0,
            'preferred_regions': region_details['preferred_regions'] if region_details else [],
            'avoid_regions': region_details['avoid_regions'] if region_details else [],
            'status': courier['status'],
            'efficiency_score': round(efficiency_score, 2),
            'eta_competitiveness': round(eta_competitiveness, 2),
            'recommended': suitability_score >= 55 and load_status != '过载' and region_factor >= 0.85
        }
    
    def _get_load_status(self, load):
        if load == 0:
            return '空闲'
        elif load <= 3:
            return '低负载'
        elif load <= 5:
            return '正常'
        elif load <= 7:
            return '高负载'
        else:
            return '过载'
    
    def rank_couriers(self, 
                      pickup_lat: float,
                      pickup_lon: float,
                      dropoff_lat: float,
                      dropoff_lon: float,
                      order_time: datetime = None,
                      top_n: int = 5,
                      priority: str = 'normal') -> List[Dict]:
        
        if order_time is None:
            order_time = datetime.now()
        
        all_estimated_times = []
        for _, courier in self.couriers.iterrows():
            courier_pos = (courier['current_lat'], courier['current_lon'])
            pickup_pos = (pickup_lat, pickup_lon)
            distance_to_pickup = geodesic(courier_pos, pickup_pos).km
            travel_time_to_pickup = (distance_to_pickup / courier['avg_speed']) * 60
            all_estimated_times.append(travel_time_to_pickup)
        
        rankings = []
        for _, courier in self.couriers.iterrows():
            suitability = self.calculate_courier_suitability(
                courier, pickup_lat, pickup_lon, dropoff_lat, dropoff_lon, 
                order_time, priority, all_estimated_times
            )
            rankings.append(suitability)
        
        rankings.sort(key=lambda x: x['suitability_score'], reverse=True)
        
        return rankings[:top_n]
    
    def get_dispatch_recommendation(self, 
                                    pickup_lat: float,
                                    pickup_lon: float,
                                    dropoff_lat: float,
                                    dropoff_lon: float,
                                    order_time: datetime = None,
                                    priority: str = 'normal') -> Dict:
        
        rankings = self.rank_couriers(
            pickup_lat, pickup_lon, dropoff_lat, dropoff_lon, order_time, top_n=10, priority=priority
        )
        
        available_couriers = [r for r in rankings if r['status'] == '空闲']
        busy_but_good = [r for r in rankings if r['status'] == '配送中' and r['suitability_score'] >= 50]
        
        primary_recommendation = rankings[0] if rankings else None
        
        return {
            'primary_recommendation': primary_recommendation,
            'top_available': available_couriers[:3] if available_couriers else [],
            'alternative_options': busy_but_good[:2] if busy_but_good else [],
            'all_rankings': rankings[:5],
            'summary': {
                'total_couriers': len(self.couriers),
                'available_couriers': len(available_couriers),
                'avg_suitability': round(np.mean([r['suitability_score'] for r in rankings]), 1) if rankings else 0
            }
        }

class RouteOptimizer:
    @staticmethod
    def calculate_eta_with_routing(distance_km: float,
                                   traffic_factor: float,
                                   weather_factor: float,
                                   courier_avg_speed: float,
                                   num_stops: int = 0) -> Dict:
        
        base_time = (distance_km / courier_avg_speed) * 60
        
        stop_time = num_stops * 3
        
        adjusted_time = base_time * traffic_factor * weather_factor + stop_time
        
        confidence_interval = adjusted_time * 0.25
        
        return {
            'base_time_min': round(base_time, 1),
            'adjusted_time_min': round(adjusted_time, 1),
            'lower_bound_min': round(adjusted_time - confidence_interval, 1),
            'upper_bound_min': round(adjusted_time + confidence_interval, 1),
            'traffic_impact_pct': round((traffic_factor - 1) * 100, 1),
            'weather_impact_pct': round((weather_factor - 1) * 100, 1)
        }
    
    @staticmethod
    def optimize_multi_stop_route(stops: List[Tuple[float, float]], 
                                  start_point: Tuple[float, float]) -> Dict:
        current_point = start_point
        unvisited = list(range(len(stops)))
        route = []
        total_distance = 0
        
        while unvisited:
            distances = []
            for idx in unvisited:
                dist = geodesic(current_point, stops[idx]).km
                distances.append((idx, dist))
            
            distances.sort(key=lambda x: x[1])
            next_idx, dist = distances[0]
            
            route.append(next_idx)
            total_distance += dist
            current_point = stops[next_idx]
            unvisited.remove(next_idx)
        
        optimized_stops = [stops[i] for i in route]
        
        return {
            'optimized_order': route,
            'optimized_stops': optimized_stops,
            'total_distance_km': round(total_distance, 2),
            'start_point': start_point
        }

def generate_delay_alert(delivery_id: str,
                         risk_analysis: Dict,
                         predicted_eta: float) -> Dict:
    
    alert_priority = {
        'critical': 'P0',
        'warning': 'P1',
        'caution': 'P2',
        'normal': 'P3'
    }[risk_analysis['warning_level']]
    
    return {
        'delivery_id': delivery_id,
        'alert_priority': alert_priority,
        'alert_type': 'DELAY_WARNING' if risk_analysis['warning_level'] != 'normal' else 'NORMAL',
        'risk_level': risk_analysis['risk_level'],
        'risk_score': risk_analysis['risk_score'],
        'predicted_eta': predicted_eta,
        'estimated_delay': risk_analysis['estimated_delay_minutes'],
        'risk_factors': risk_analysis['risk_factors'],
        'recommendations': risk_analysis['recommended_action'],
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }

if __name__ == '__main__':
    from data_generator import generate_couriers_data
    
    print('测试延迟预警系统...')
    delay_system = DelayWarningSystem()
    risk = delay_system.analyze_delay_risk(
        predicted_eta=30.0,
        upper_bound=40.0,
        distance_km=8.5,
        traffic_condition='拥堵',
        weather='中雨',
        courier_on_time_rate=0.87
    )
    print('风险分析:', risk)
    
    print('\n测试配送员调度系统...')
    couriers_df = generate_couriers_data()
    scheduler = CourierScheduler(couriers_df)
    
    recommendation = scheduler.get_dispatch_recommendation(
        pickup_lat=31.2304,
        pickup_lon=121.4737,
        dropoff_lat=31.2500,
        dropoff_lon=121.5000,
        priority='normal'
    )
    print('首要推荐配送员:', recommendation['primary_recommendation'])
    print('可用配送员数量:', recommendation['summary']['available_couriers'])
