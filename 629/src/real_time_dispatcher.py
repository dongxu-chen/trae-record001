import numpy as np
import pandas as pd
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import threading
import time
import warnings
warnings.filterwarnings('ignore')

from src.order_bundler import OrderBundler, Bundle, Order
from src.realtime_eta_tracker import RealTimeETATracker, ETAUpdate
from src.rider_incentive import RiderIncentiveSystem, IncentiveConfig, DeliveryIncentive

@dataclass
class DispatchDecision:
    decision_id: str
    order_id: str
    rider_id: str
    bundle_id: Optional[str]
    assigned_at: datetime
    estimated_delivery_time: datetime
    total_incentive: float
    incentive_breakdown: Dict[str, float]
    route_optimization_saving_km: float
    eta_confidence: float
    priority_score: float
    recommendation_reason: str

@dataclass
class SystemMetrics:
    total_orders_processed: int = 0
    total_bundles_created: int = 0
    avg_bundle_size: float = 0.0
    total_distance_saved_km: float = 0.0
    urgent_order_ratio: float = 0.0
    avg_eta_accuracy: float = 0.0
    avg_rider_workload: float = 0.0
    total_incentives_paid: float = 0.0
    estimated_cost_savings: float = 0.0

class RealTimeDispatcher:
    def __init__(self, 
                 update_interval_sec: int = 30,
                 max_orders_per_bundle: int = 3,
                 max_detour_ratio: float = 1.3):
        self.order_bundler = OrderBundler(
            max_orders_per_bundle=max_orders_per_bundle,
            max_detour_ratio=max_detour_ratio
        )
        self.eta_tracker = RealTimeETATracker(
            update_interval_sec=update_interval_sec
        )
        self.incentive_system = RiderIncentiveSystem()
        
        self.pending_orders: Dict[str, Order] = {}
        self.active_bundles: Dict[str, Bundle] = {}
        self.dispatch_decisions: List[DispatchDecision] = []
        self.metrics = SystemMetrics()
        
        self._dispatch_thread = None
        self._is_running = False
        
        self.eta_tracker.register_callback(self._on_eta_update)
        
    def start(self):
        if self._is_running:
            return
        self._is_running = True
        self.eta_tracker.start_tracking()
        self._dispatch_thread = threading.Thread(target=self._dispatch_loop, daemon=True)
        self._dispatch_thread.start()
        
    def stop(self):
        self._is_running = False
        self.eta_tracker.stop_tracking()
        if self._dispatch_thread:
            self._dispatch_thread.join(timeout=5)
            
    def add_order(self, order_dict: Dict) -> str:
        order = Order(
            order_id=order_dict['order_id'],
            restaurant_lat=order_dict['restaurant_lat'],
            restaurant_lon=order_dict['restaurant_lon'],
            user_lat=order_dict['user_lat'],
            user_lon=order_dict['user_lon'],
            prep_time_min=order_dict.get('prep_time_min', 15),
            order_time=order_dict.get('order_time', datetime.now()),
            deadline=order_dict.get('deadline', datetime.now() + timedelta(minutes=45)),
            priority=order_dict.get('priority', 1),
            is_urgent=order_dict.get('is_urgent', False),
            food_type=order_dict.get('food_type', '')
        )
        
        self.pending_orders[order.order_id] = order
        self.metrics.total_orders_processed += 1
        
        return order.order_id
        
    def get_pending_orders_list(self) -> List[Order]:
        return list(self.pending_orders.values())
        
    def _dispatch_loop(self):
        while self._is_running:
            try:
                self._process_pending_orders()
                self._update_metrics()
            except Exception as e:
                print(f"Dispatch loop error: {e}")
                
            time.sleep(10)
            
    def _process_pending_orders(self):
        pending = self.get_pending_orders_list()
        if not pending:
            return
            
        bundles = self.order_bundler.bundle_orders(pending)
        self.metrics.total_bundles_created += len(bundles)
        
        bundle_sizes = [len(b.orders) for b in bundles]
        self.metrics.avg_bundle_size = np.mean(bundle_sizes) if bundle_sizes else 0
        
        for bundle in bundles:
            savings = self.order_bundler.calculate_bundle_savings(bundle)
            self.metrics.total_distance_saved_km += savings['total_saving_km']
            
            self.active_bundles[bundle.bundle_id] = bundle
            
            for order in bundle.orders:
                if order.order_id in self.pending_orders:
                    del self.pending_orders[order.order_id]
                    
    def dispatch_to_rider(self, bundle_id: str, rider_info: Dict,
                         rider_start_lat: float, rider_start_lon: float,
                         traffic_factor: float = 1.0, 
                         weather_factor: float = 1.0) -> List[DispatchDecision]:
        if bundle_id not in self.active_bundles:
            return []
            
        bundle = self.active_bundles[bundle_id]
        bundle.rider_id = rider_info['rider_id']
        
        decisions = []
        for i, order in enumerate(bundle.orders):
            distance = self.order_bundler.calculate_distance(
                order.restaurant_loc, order.user_loc
            )
            
            eta_min = max(10, (distance / 25) * 60 * traffic_factor + order.prep_time_min)
            eta_confidence = 0.9 - (0.05 * i)
            
            order_info = {
                'order_id': order.order_id,
                'is_urgent': order.is_urgent,
                'eta_min': eta_min,
                'distance_km': distance,
                'bundle_size': len(bundle.orders)
            }
            
            delivery_stats = {'distance_km': distance}
            
            incentive = self.incentive_system.calculate_delivery_incentive(
                order_info, rider_info, delivery_stats
            )
            
            decision = DispatchDecision(
                decision_id=f"DEC-{len(self.dispatch_decisions)+1:04d}",
                order_id=order.order_id,
                rider_id=rider_info['rider_id'],
                bundle_id=bundle_id,
                assigned_at=datetime.now(),
                estimated_delivery_time=datetime.now() + timedelta(minutes=eta_min),
                total_incentive=incentive.total_incentive,
                incentive_breakdown={
                    'base': incentive.base_fee,
                    'urgency': incentive.urgency_bonus,
                    'on_time': incentive.on_time_bonus,
                    'bundle': incentive.bundle_bonus,
                    'peak': incentive.peak_hour_bonus,
                    'distance': incentive.distance_bonus,
                    'quality': incentive.quality_bonus
                },
                route_optimization_saving_km=self.order_bundler.calculate_bundle_savings(bundle)['saving_per_order'],
                eta_confidence=round(eta_confidence, 2),
                priority_score=round(order.priority * (1.5 if order.is_urgent else 1.0), 2),
                recommendation_reason=self._generate_recommendation_reason(order, rider_info, bundle)
            )
            
            decisions.append(decision)
            self.dispatch_decisions.append(decision)
            
            delivery_info = {
                'order_id': order.order_id,
                'rider_id': rider_info['rider_id'],
                'rider_start_lat': rider_start_lat,
                'rider_start_lon': rider_start_lon,
                'restaurant_lat': order.restaurant_lat,
                'restaurant_lon': order.restaurant_lon,
                'user_lat': order.user_lat,
                'user_lon': order.user_lon,
                'prep_time_min': order.prep_time_min,
                'eta_min': eta_min,
                'rider_speed': rider_info.get('avg_speed', 25),
                'traffic_factor': traffic_factor,
                'weather_factor': weather_factor
            }
            
            self.eta_tracker.add_delivery(delivery_info)
            
        self.metrics.total_incentives_paid += sum(d.total_incentive for d in decisions)
        
        return decisions
        
    def _generate_recommendation_reason(self, order: Order, rider_info: Dict, bundle: Bundle) -> str:
        reasons = []
        
        if len(bundle.orders) > 1:
            reasons.append(f"顺路合并{len(bundle.orders)}单，节省配送距离")
            
        rider_rate = rider_info.get('on_time_rate', 0.9)
        if rider_rate >= 0.95:
            reasons.append(f"骑手准时率{int(rider_rate*100)}%，服务质量优秀")
            
        workload = rider_info.get('current_orders', 0)
        if workload <= 2:
            reasons.append(f"骑手当前仅{workload}单，负载均衡")
            
        if order.is_urgent:
            reasons.append("加急订单，优先配送")
            
        return "；".join(reasons) if reasons else "综合最优分配"
        
    def _on_eta_update(self, eta_update: ETAUpdate):
        if eta_update.eta_change_min > 5:
            print(f"⚠️ 订单{eta_update.order_id} ETA变化{eta_update.eta_change_min:+}分钟: "
                  f"{eta_update.current_status}，剩余{eta_update.updated_eta_min}分钟")
    
    def get_recommended_dispatch(self, available_riders: List[Dict]) -> List[Dict]:
        pending = self.get_pending_orders_list()
        if not pending or not available_riders:
            return []
            
        bundles = self.order_bundler.bundle_orders(pending)
        
        pending_orders_for_incentive = []
        for bundle in bundles:
            for order in bundle.orders:
                distance = self.order_bundler.calculate_distance(
                    order.restaurant_loc, order.user_loc
                )
                eta_min = max(10, (distance / 25) * 60 + order.prep_time_min)
                
                pending_orders_for_incentive.append({
                    'order_id': order.order_id,
                    'is_urgent': order.is_urgent,
                    'eta_min': eta_min,
                    'distance_km': distance,
                    'bundle_size': len(bundle.orders),
                    'bundle_id': bundle.bundle_id
                })
        
        recommendations = self.incentive_system.recommend_dispatch_priority(
            pending_orders_for_incentive, available_riders
        )
        
        for rec in recommendations:
            order = next(o for o in pending if o.order_id == rec['order_id'])
            rec['bundle_id'] = next((b.bundle_id for b in bundles if order in b.orders), None)
            rec['deadline'] = order.deadline
            rec['remaining_time'] = order.remaining_time
            
        return recommendations
        
    def _update_metrics(self):
        urgent_count = sum(1 for o in self.get_pending_orders_list() if o.is_urgent)
        total_pending = len(self.get_pending_orders_list())
        self.metrics.urgent_order_ratio = urgent_count / max(total_pending, 1)
        
        all_riders = list(self.incentive_system.rider_performance.values())
        if all_riders:
            self.metrics.avg_rider_workload = np.mean([r.current_workload for r in all_riders])
        
        eta_updates = list(self.eta_tracker.eta_history.values())
        if eta_updates:
            all_updates = [u for updates in eta_updates for u in updates]
            if all_updates:
                self.metrics.avg_eta_accuracy = np.mean([u.confidence for u in all_updates])
        
        stats = self.incentive_system.get_system_wide_incentive_stats()
        if stats:
            self.metrics.estimated_cost_savings = stats.get('estimated_savings_from_reduction', 0)
            
    def get_system_summary(self) -> Dict:
        self._update_metrics()
        
        return {
            'pending_orders': len(self.pending_orders),
            'active_bundles': len(self.active_bundles),
            'active_deliveries': len(self.eta_tracker.active_deliveries),
            'metrics': {
                'total_orders_processed': self.metrics.total_orders_processed,
                'total_bundles_created': self.metrics.total_bundles_created,
                'avg_bundle_size': round(self.metrics.avg_bundle_size, 2),
                'total_distance_saved_km': round(self.metrics.total_distance_saved_km, 2),
                'urgent_order_ratio': round(self.metrics.urgent_order_ratio, 3),
                'avg_eta_confidence': round(self.metrics.avg_eta_accuracy, 3),
                'avg_rider_workload': round(self.metrics.avg_rider_workload, 1),
                'total_incentives_paid': round(self.metrics.total_incentives_paid, 2),
                'estimated_cost_savings': round(self.metrics.estimated_cost_savings, 2)
            },
            'incentive_stats': self.incentive_system.get_system_wide_incentive_stats(),
            'active_deliveries': self.eta_tracker.get_active_deliveries_summary().to_dict('records') 
                if not self.eta_tracker.get_active_deliveries_summary().empty else []
        }
        
    def get_eta_trend_data(self, order_id: str) -> pd.DataFrame:
        return self.eta_tracker.get_eta_trend(order_id)

if __name__ == '__main__':
    dispatcher = RealTimeDispatcher(update_interval_sec=2)
    
    base_time = datetime.now()
    for i in range(5):
        dispatcher.add_order({
            'order_id': f'ORD{i+1:03d}',
            'restaurant_lat': 39.9042 + np.random.uniform(-0.02, 0.02),
            'restaurant_lon': 116.4074 + np.random.uniform(-0.02, 0.02),
            'user_lat': 39.9142 + np.random.uniform(-0.02, 0.02),
            'user_lon': 116.4174 + np.random.uniform(-0.02, 0.02),
            'prep_time_min': 15 + np.random.randint(-3, 5),
            'order_time': base_time + timedelta(minutes=i*3),
            'deadline': base_time + timedelta(minutes=45 + i*3),
            'is_urgent': i == 0
        })
    
    riders = [
        {'rider_id': 'R001', 'on_time_rate': 0.97, 'rating': 4.8, 'total_deliveries': 520, 'current_orders': 2, 'avg_speed': 25},
        {'rider_id': 'R002', 'on_time_rate': 0.92, 'rating': 4.5, 'total_deliveries': 280, 'current_orders': 1, 'avg_speed': 28},
        {'rider_id': 'R003', 'on_time_rate': 0.98, 'rating': 4.9, 'total_deliveries': 850, 'current_orders': 4, 'avg_speed': 23}
    ]
    
    print("待处理订单数:", len(dispatcher.get_pending_orders_list()))
    
    print("\n调度推荐:")
    recommendations = dispatcher.get_recommended_dispatch(riders)
    for rec in recommendations[:3]:
        top_rider = rec['candidate_riders'][0]
        print(f"  订单{rec['order_id']}(加急:{rec['is_urgent']}) → 推荐骑手{top_rider['rider_id']}, "
              f"预计奖励¥{top_rider['recommended_incentive']}")
    
    dispatcher.start()
    print("\n调度系统已启动，运行3秒...")
    time.sleep(3)
    
    summary = dispatcher.get_system_summary()
    print("\n系统摘要:")
    for k, v in summary['metrics'].items():
        print(f"  {k}: {v}")
    
    dispatcher.stop()
    print("\n调度系统已停止")
