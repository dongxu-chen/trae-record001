import numpy as np
import pandas as pd
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

@dataclass
class IncentiveConfig:
    base_delivery_fee: float = 5.0
    urgency_bonus_multiplier: float = 1.5
    on_time_bonus: float = 2.0
    bundle_bonus_per_order: float = 1.0
    peak_hour_surcharge: float = 1.5
    peak_hours: List[int] = field(default_factory=lambda: [11, 12, 13, 17, 18, 19])
    distance_bonus_per_km: float = 0.5
    on_time_rate_threshold: float = 0.95
    rating_threshold: float = 4.7
    excellent_rider_bonus: float = 3.0
    max_daily_orders_for_balance: int = 12
    
@dataclass
class DeliveryIncentive:
    order_id: str
    rider_id: str
    base_fee: float
    urgency_bonus: float
    on_time_bonus: float
    bundle_bonus: float
    peak_hour_bonus: float
    distance_bonus: float
    quality_bonus: float
    total_incentive: float
    is_urgent: bool
    is_bundled: bool
    incentive_rank: int = 0
    
@dataclass
class RiderPerformance:
    rider_id: str
    on_time_rate: float
    avg_rating: float
    total_deliveries: int
    total_urgent_deliveries: int
    avg_delivery_time_min: float
    current_workload: int
    incentive_score: float = 0.0
    efficiency_score: float = 0.0

class RiderIncentiveSystem:
    def __init__(self, config: Optional[IncentiveConfig] = None):
        self.config = config or IncentiveConfig()
        self.incentive_history: List[DeliveryIncentive] = []
        self.rider_performance: Dict[str, RiderPerformance] = {}
        self.urgent_order_count: int = 0
        self.total_order_count: int = 0
        
    def calculate_delivery_incentive(self, order_info: Dict,
                                    rider_info: Dict,
                                    delivery_stats: Dict) -> DeliveryIncentive:
        is_urgent = order_info.get('is_urgent', False)
        is_peak_hour = datetime.now().hour in self.config.peak_hours
        is_bundled = order_info.get('bundle_size', 1) > 1
        distance_km = delivery_stats.get('distance_km', 3.0)
        bundle_size = order_info.get('bundle_size', 1)
        
        base_fee = self.config.base_delivery_fee
        
        urgency_bonus = 0
        if is_urgent:
            urgency_bonus = base_fee * (self.config.urgency_bonus_multiplier - 1)
            self.urgent_order_count += 1
        
        on_time_bonus = self.config.on_time_bonus
        
        bundle_bonus = self.config.bundle_bonus_per_order * (bundle_size - 1)
        
        peak_hour_bonus = 0
        if is_peak_hour:
            peak_hour_bonus = self.config.peak_hour_surcharge
        
        distance_bonus = max(0, distance_km - 2) * self.config.distance_bonus_per_km
        
        quality_bonus = 0
        rider_perf = self.rider_performance.get(rider_info['rider_id'])
        if rider_perf:
            if (rider_perf.on_time_rate >= self.config.on_time_rate_threshold and 
                rider_perf.avg_rating >= self.config.rating_threshold):
                quality_bonus = self.config.excellent_rider_bonus
        
        total_incentive = (base_fee + urgency_bonus + on_time_bonus + 
                          bundle_bonus + peak_hour_bonus + distance_bonus + 
                          quality_bonus)
        
        self.total_order_count += 1
        
        incentive = DeliveryIncentive(
            order_id=order_info['order_id'],
            rider_id=rider_info['rider_id'],
            base_fee=round(base_fee, 2),
            urgency_bonus=round(urgency_bonus, 2),
            on_time_bonus=round(on_time_bonus, 2),
            bundle_bonus=round(bundle_bonus, 2),
            peak_hour_bonus=round(peak_hour_bonus, 2),
            distance_bonus=round(distance_bonus, 2),
            quality_bonus=round(quality_bonus, 2),
            total_incentive=round(total_incentive, 2),
            is_urgent=is_urgent,
            is_bundled=is_bundled
        )
        
        self.incentive_history.append(incentive)
        
        return incentive
        
    def predict_urgent_order_cost(self, order_info: Dict) -> Dict:
        normal_incentive = self.calculate_delivery_incentive(
            {**order_info, 'is_urgent': False},
            {'rider_id': 'temp'},
            {'distance_km': order_info.get('distance_km', 3.0)}
        )
        
        urgent_incentive = self.calculate_delivery_incentive(
            {**order_info, 'is_urgent': True},
            {'rider_id': 'temp'},
            {'distance_km': order_info.get('distance_km', 3.0)}
        )
        
        cost_diff = urgent_incentive.total_incentive - normal_incentive.total_incentive
        system_wide_cost = cost_diff * 1.2
        
        return {
            'normal_incentive': normal_incentive.total_incentive,
            'urgent_incentive': urgent_incentive.total_incentive,
            'premium_per_order': round(cost_diff, 2),
            'system_wide_cost': round(system_wide_cost, 2),
            'recommendation': '建议通过提前调度减少加急' if cost_diff > 2 else '加急成本可控'
        }
        
    def recommend_dispatch_priority(self, pending_orders: List[Dict],
                                   available_riders: List[Dict]) -> List[Dict]:
        for rider in available_riders:
            rider_id = rider['rider_id']
            if rider_id not in self.rider_performance:
                self.rider_performance[rider_id] = RiderPerformance(
                    rider_id=rider_id,
                    on_time_rate=rider.get('on_time_rate', 0.9),
                    avg_rating=rider.get('rating', 4.5),
                    total_deliveries=rider.get('total_deliveries', 100),
                    total_urgent_deliveries=rider.get('urgent_deliveries', 10),
                    avg_delivery_time_min=rider.get('avg_delivery_time', 25),
                    current_workload=rider.get('current_orders', 0)
                )
            
            perf = self.rider_performance[rider_id]
            perf.current_workload = rider.get('current_orders', 0)
            
            perf.incentive_score = (
                perf.on_time_rate * 0.35 +
                (perf.avg_rating / 5.0) * 0.25 +
                min(1, perf.total_deliveries / 500) * 0.2 +
                (1 - min(1, perf.current_workload / self.config.max_daily_orders_for_balance)) * 0.2
            )
            
            perf.efficiency_score = (
                (1 - min(1, perf.avg_delivery_time_min / 45)) * 0.5 +
                (perf.total_deliveries / (perf.total_urgent_deliveries + 1)) * 0.3 +
                perf.on_time_rate * 0.2
            )
        
        recommendations = []
        for order in pending_orders:
            order_scores = []
            
            for rider in available_riders:
                perf = self.rider_performance[rider['rider_id']]
                
                eta_score = 1 - min(1, order.get('eta_min', 30) / 60)
                
                balance_penalty = 0
                if perf.current_workload >= self.config.max_daily_orders_for_balance:
                    balance_penalty = -0.3
                elif perf.current_workload >= 8:
                    balance_penalty = -0.1
                
                if order.get('is_urgent', False):
                    capacity_penalty = 0
                    if perf.current_workload >= 3:
                        capacity_penalty = -0.2
                        
                    dispatch_score = (
                        eta_score * 0.4 +
                        perf.efficiency_score * 0.35 +
                        balance_penalty +
                        capacity_penalty
                    )
                else:
                    dispatch_score = (
                        eta_score * 0.25 +
                        perf.incentive_score * 0.35 +
                        perf.efficiency_score * 0.25 +
                        balance_penalty
                    )
                
                order_scores.append({
                    'rider_id': rider['rider_id'],
                    'dispatch_score': round(dispatch_score, 3),
                    'eta_min': order.get('eta_min', 30),
                    'rider_workload': perf.current_workload,
                    'incentive_score': round(perf.incentive_score, 3),
                    'efficiency_score': round(perf.efficiency_score, 3),
                    'recommended_incentive': self.calculate_delivery_incentive(
                        order, rider, {'distance_km': order.get('distance_km', 3.0)}
                    ).total_incentive
                })
            
            order_scores.sort(key=lambda x: x['dispatch_score'], reverse=True)
            
            for i, score in enumerate(order_scores):
                score['rank'] = i + 1
                score['is_recommended'] = i == 0
            
            urgent_ratio = self.urgent_order_count / max(self.total_order_count, 1)
            if order.get('is_urgent', False) and urgent_ratio > 0.3:
                order_scores[0]['notes'] = '加急订单比例过高，建议后续提前调度'
            
            recommendations.append({
                'order_id': order['order_id'],
                'is_urgent': order.get('is_urgent', False),
                'candidate_riders': order_scores,
                'urgent_ratio': round(urgent_ratio, 3)
            })
        
        return recommendations
        
    def calculate_load_balance_reward(self, rider_id: str, 
                                     all_riders_workload: List[int]) -> float:
        avg_workload = np.mean(all_riders_workload)
        rider_workload = self.rider_performance[rider_id].current_workload
        
        deviation = abs(rider_workload - avg_workload)
        max_deviation = max(avg_workload, max(all_riders_workload) - avg_workload)
        
        balance_score = max(0, 1 - deviation / max(max_deviation, 1))
        balance_reward = balance_score * 2.0
        
        return round(balance_reward, 2)
        
    def get_system_wide_incentive_stats(self) -> Dict:
        if not self.incentive_history:
            return {}
            
        df = pd.DataFrame([{
            'order_id': i.order_id,
            'rider_id': i.rider_id,
            'total': i.total_incentive,
            'base': i.base_fee,
            'urgency': i.urgency_bonus,
            'bundle': i.bundle_bonus,
            'peak': i.peak_hour_bonus,
            'is_urgent': i.is_urgent,
            'is_bundled': i.is_bundled
        } for i in self.incentive_history])
        
        urgent_ratio = self.urgent_order_count / max(self.total_order_count, 1)
        
        return {
            'total_incentives_paid': round(df['total'].sum(), 2),
            'avg_incentive_per_order': round(df['total'].mean(), 2),
            'urgent_order_ratio': round(urgent_ratio, 3),
            'urgent_premium_total': round(df[df['is_urgent']]['urgency'].sum(), 2),
            'bundle_savings_total': round(len(df[df['is_bundled']]) * 1.5, 2),
            'estimated_savings_from_reduction': round(urgent_ratio * df['total'].sum() * 0.2, 2),
            'order_count': len(df)
        }
        
    def get_rider_incentive_rankings(self) -> pd.DataFrame:
        if not self.rider_performance:
            return pd.DataFrame()
            
        rankings = []
        for rider_id, perf in self.rider_performance.items():
            rider_incentives = [i for i in self.incentive_history if i.rider_id == rider_id]
            
            rankings.append({
                'rider_id': rider_id,
                'on_time_rate': perf.on_time_rate,
                'avg_rating': perf.avg_rating,
                'total_deliveries': perf.total_deliveries,
                'current_workload': perf.current_workload,
                'incentive_score': round(perf.incentive_score, 3),
                'efficiency_score': round(perf.efficiency_score, 3),
                'total_earned': round(sum(i.total_incentive for i in rider_incentives), 2),
                'avg_earning_per_order': round(
                    np.mean([i.total_incentive for i in rider_incentives]) if rider_incentives else 0, 2
                )
            })
            
        return pd.DataFrame(rankings).sort_values('incentive_score', ascending=False)

if __name__ == '__main__':
    incentive_system = RiderIncentiveSystem()
    
    pending_orders = [
        {'order_id': 'ORD001', 'is_urgent': True, 'eta_min': 25, 'distance_km': 3.5},
        {'order_id': 'ORD002', 'is_urgent': False, 'eta_min': 30, 'distance_km': 2.8, 'bundle_size': 2},
        {'order_id': 'ORD003', 'is_urgent': False, 'eta_min': 28, 'distance_km': 4.2}
    ]
    
    available_riders = [
        {'rider_id': 'R001', 'on_time_rate': 0.97, 'rating': 4.8, 'total_deliveries': 520, 'current_orders': 2},
        {'rider_id': 'R002', 'on_time_rate': 0.92, 'rating': 4.5, 'total_deliveries': 280, 'current_orders': 1},
        {'rider_id': 'R003', 'on_time_rate': 0.98, 'rating': 4.9, 'total_deliveries': 850, 'current_orders': 4}
    ]
    
    print("加急订单成本预测:")
    cost = incentive_system.predict_urgent_order_cost(pending_orders[0])
    for k, v in cost.items():
        print(f"  {k}: {v}")
    
    print("\n调度推荐:")
    recommendations = incentive_system.recommend_dispatch_priority(pending_orders, available_riders)
    for rec in recommendations:
        print(f"\n订单 {rec['order_id']} (加急: {rec['is_urgent']}):")
        for rider in rec['candidate_riders'][:3]:
            marker = "★" if rider['is_recommended'] else " "
            print(f"  {marker} 骑手{rider['rider_id']}: 得分{rider['dispatch_score']}, "
                  f"预计奖励¥{rider['recommended_incentive']}")
    
    print("\n系统激励统计:")
    stats = incentive_system.get_system_wide_incentive_stats()
    for k, v in stats.items():
        print(f"  {k}: {v}")
