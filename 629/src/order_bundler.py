import numpy as np
import pandas as pd
from geopy.distance import geodesic
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

@dataclass
class Order:
    order_id: str
    restaurant_lat: float
    restaurant_lon: float
    user_lat: float
    user_lon: float
    prep_time_min: float
    order_time: datetime
    deadline: datetime
    priority: int = 1
    is_urgent: bool = False
    food_type: str = ''
    status: str = 'pending'
    assigned_rider: Optional[str] = None
    bundle_id: Optional[str] = None
    
    @property
    def restaurant_loc(self) -> Tuple[float, float]:
        return (self.restaurant_lat, self.restaurant_lon)
    
    @property
    def user_loc(self) -> Tuple[float, float]:
        return (self.user_lat, self.user_lon)
    
    @property
    def remaining_time(self) -> float:
        return max(0, (self.deadline - datetime.now()).total_seconds() / 60)

@dataclass
class Bundle:
    bundle_id: str
    orders: List[Order] = field(default_factory=list)
    rider_id: Optional[str] = None
    total_distance_km: float = 0.0
    estimated_time_min: float = 0.0
    route: List[Tuple[float, float]] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    
    def add_order(self, order: Order):
        order.bundle_id = self.bundle_id
        self.orders.append(order)
    
    @property
    def is_empty(self) -> bool:
        return len(self.orders) == 0
    
    @property
    def min_deadline(self) -> datetime:
        return min(o.deadline for o in self.orders)
    
    @property
    def avg_priority(self) -> float:
        return np.mean([o.priority for o in self.orders])

class OrderBundler:
    def __init__(self, max_orders_per_bundle: int = 3,
                 max_detour_ratio: float = 1.3,
                 max_time_window_min: int = 15):
        self.max_orders_per_bundle = max_orders_per_bundle
        self.max_detour_ratio = max_detour_ratio
        self.max_time_window_min = max_time_window_min
        
    def calculate_distance(self, loc1: Tuple[float, float], 
                          loc2: Tuple[float, float]) -> float:
        return geodesic(loc1, loc2).kilometers
    
    def calculate_direct_distance(self, order: Order) -> float:
        return self.calculate_distance(order.restaurant_loc, order.user_loc)
    
    def calculate_detour(self, bundle: Bundle, new_order: Order) -> float:
        if bundle.is_empty:
            return 0.0
        
        original_distance = bundle.total_distance_km
        
        temp_orders = bundle.orders + [new_order]
        temp_route = self.optimize_route(temp_orders)
        new_distance = temp_route['total_distance_km']
        
        detour = (new_distance - original_distance) / original_distance if original_distance > 0 else 0
        return detour
    
    def check_time_compatibility(self, bundle: Bundle, new_order: Order) -> bool:
        if bundle.is_empty:
            return True
        
        bundle_times = [o.order_time for o in bundle.orders]
        time_diff = abs((new_order.order_time - max(bundle_times)).total_seconds() / 60)
        
        if time_diff > self.max_time_window_min:
            return False
        
        if new_order.is_urgent:
            urgent_orders = [o for o in bundle.orders if o.is_urgent]
            if len(urgent_orders) >= 2:
                return False
        
        return True
    
    def check_deadline_compatibility(self, bundle: Bundle, new_order: Order,
                                   avg_speed_kmh: float = 25,
                                   traffic_factor: float = 1.0) -> bool:
        temp_orders = bundle.orders + [new_order]
        route = self.optimize_route(temp_orders)
        
        delivery_time = route['total_distance_km'] / avg_speed_kmh * 60 * traffic_factor
        
        min_deadline = min(o.deadline for o in temp_orders)
        expected_arrival = datetime.now() + timedelta(minutes=delivery_time)
        
        return expected_arrival <= min_deadline
    
    def optimize_route(self, orders: List[Order]) -> Dict:
        if len(orders) == 0:
            return {'total_distance_km': 0, 'route': [], 'order_sequence': []}
        
        restaurants = [(o.restaurant_lat, o.restaurant_lon, f'rest_{i}') 
                      for i, o in enumerate(orders)]
        users = [(o.user_lat, o.user_lon, f'user_{i}') 
                for i, o in enumerate(orders)]
        
        all_points = restaurants + users
        n = len(all_points)
        
        best_route = None
        best_distance = float('inf')
        best_sequence = None
        
        import itertools
        
        restaurant_indices = list(range(len(restaurants)))
        user_indices = list(range(len(restaurants), len(all_points)))
        
        for perm in itertools.permutations(range(n)):
            valid = True
            for i in range(len(restaurants)):
                rest_idx = restaurant_indices[i]
                user_idx = user_indices[i]
                if perm.index(rest_idx) > perm.index(user_idx):
                    valid = False
                    break
            
            if valid:
                distance = 0
                for i in range(len(perm) - 1):
                    p1 = all_points[perm[i]]
                    p2 = all_points[perm[i+1]]
                    distance += self.calculate_distance(p1[:2], p2[:2])
                
                if distance < best_distance:
                    best_distance = distance
                    best_route = [all_points[i][:2] for i in perm]
                    best_sequence = [all_points[i][2] for i in perm]
        
        return {
            'total_distance_km': best_distance,
            'route': best_route,
            'order_sequence': best_sequence
        }
    
    def calculate_bundle_savings(self, bundle: Bundle) -> Dict:
        if len(bundle.orders) < 2:
            return {'total_saving_km': 0, 'saving_per_order': 0, 'saving_ratio': 0}
        
        individual_distances = sum(self.calculate_direct_distance(o) for o in bundle.orders)
        bundled_distance = bundle.total_distance_km
        
        saving = individual_distances - bundled_distance
        saving_ratio = saving / individual_distances if individual_distances > 0 else 0
        
        return {
            'total_saving_km': round(saving, 2),
            'saving_per_order': round(saving / len(bundle.orders), 2),
            'saving_ratio': round(saving_ratio, 3)
        }
    
    def bundle_orders(self, orders: List[Order], 
                     riders: Optional[List[Dict]] = None) -> List[Bundle]:
        if not orders:
            return []
        
        pending_orders = sorted(orders, key=lambda o: (o.is_urgent, o.deadline))
        bundles = []
        
        while pending_orders:
            current_order = pending_orders.pop(0)
            
            best_bundle = None
            best_saving = -float('inf')
            
            for bundle in bundles:
                if len(bundle.orders) >= self.max_orders_per_bundle:
                    continue
                
                if not self.check_time_compatibility(bundle, current_order):
                    continue
                
                detour = self.calculate_detour(bundle, current_order)
                if detour > self.max_detour_ratio - 1:
                    continue
                
                if not self.check_deadline_compatibility(bundle, current_order):
                    continue
                
                temp_orders = bundle.orders + [current_order]
                route = self.optimize_route(temp_orders)
                saving = self.calculate_bundle_savings(Bundle(
                    bundle_id='temp', 
                    orders=temp_orders,
                    total_distance_km=route['total_distance_km']
                ))
                
                if saving['total_saving_km'] > best_saving:
                    best_saving = saving['total_saving_km']
                    best_bundle = (bundle, route)
            
            if best_bundle is not None and best_saving > 0:
                bundle, route = best_bundle
                bundle.add_order(current_order)
                bundle.total_distance_km = route['total_distance_km']
                bundle.route = route['route']
            else:
                new_bundle_id = f'BUNDLE-{len(bundles)+1:03d}'
                route = self.optimize_route([current_order])
                new_bundle = Bundle(
                    bundle_id=new_bundle_id,
                    orders=[current_order],
                    total_distance_km=route['total_distance_km'],
                    route=route['route']
                )
                current_order.bundle_id = new_bundle_id
                bundles.append(new_bundle)
        
        return bundles

if __name__ == '__main__':
    bundler = OrderBundler(max_orders_per_bundle=3, max_detour_ratio=1.3)
    
    base_time = datetime.now()
    orders = [
        Order(
            order_id='ORD001',
            restaurant_lat=39.9042, restaurant_lon=116.4074,
            user_lat=39.9142, user_lon=116.4174,
            prep_time_min=15,
            order_time=base_time,
            deadline=base_time + timedelta(minutes=45)
        ),
        Order(
            order_id='ORD002',
            restaurant_lat=39.9062, restaurant_lon=116.4094,
            user_lat=39.9162, user_lon=116.4194,
            prep_time_min=12,
            order_time=base_time + timedelta(minutes=5),
            deadline=base_time + timedelta(minutes=50)
        ),
        Order(
            order_id='ORD003',
            restaurant_lat=39.9022, restaurant_lon=116.4054,
            user_lat=39.8942, user_lon=116.3974,
            prep_time_min=18,
            order_time=base_time + timedelta(minutes=10),
            deadline=base_time + timedelta(minutes=55),
            is_urgent=True
        )
    ]
    
    bundles = bundler.bundle_orders(orders)
    
    print(f"生成 {len(bundles)} 个配送批次:")
    for bundle in bundles:
        savings = bundler.calculate_bundle_savings(bundle)
        print(f"\n批次 {bundle.bundle_id}:")
        print(f"  订单数: {len(bundle.orders)}")
        print(f"  订单ID: {[o.order_id for o in bundle.orders]}")
        print(f"  总距离: {bundle.total_distance_km:.2f} km")
        print(f"  节省距离: {savings['total_saving_km']:.2f} km ({savings['saving_ratio']:.1%})")
