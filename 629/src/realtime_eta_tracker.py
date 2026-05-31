import numpy as np
import pandas as pd
from geopy.distance import geodesic
from typing import List, Dict, Tuple, Optional, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass, field
import threading
import time
import warnings
warnings.filterwarnings('ignore')

@dataclass
class LocationUpdate:
    rider_id: str
    lat: float
    lon: float
    timestamp: datetime
    speed_kmh: float
    heading: float = 0.0
    accuracy_m: float = 10.0

@dataclass
class ETAUpdate:
    order_id: str
    rider_id: str
    current_lat: float
    current_lon: float
    updated_eta_min: float
    previous_eta_min: float
    eta_change_min: float
    remaining_distance_km: float
    current_status: str
    timestamp: datetime
    confidence: float = 0.9
    delay_reasons: List[str] = field(default_factory=list)

class RealTimeETATracker:
    def __init__(self, update_interval_sec: int = 30,
                 eta_model=None, feature_engineer=None):
        self.update_interval_sec = update_interval_sec
        self.eta_model = eta_model
        self.feature_engineer = feature_engineer
        self.rider_locations: Dict[str, LocationUpdate] = {}
        self.eta_history: Dict[str, List[ETAUpdate]] = {}
        self.active_deliveries: Dict[str, Dict] = {}
        self._tracking_thread = None
        self._is_tracking = False
        self._callbacks: List[Callable[[ETAUpdate], None]] = []
        
    def start_tracking(self):
        if self._is_tracking:
            return
        
        self._is_tracking = True
        self._tracking_thread = threading.Thread(target=self._tracking_loop, daemon=True)
        self._tracking_thread.start()
        
    def stop_tracking(self):
        self._is_tracking = False
        if self._tracking_thread:
            self._tracking_thread.join(timeout=5)
            
    def register_callback(self, callback: Callable[[ETAUpdate], None]):
        self._callbacks.append(callback)
        
    def add_delivery(self, delivery_info: Dict):
        order_id = delivery_info['order_id']
        self.active_deliveries[order_id] = {
            **delivery_info,
            'start_time': datetime.now(),
            'initial_eta': delivery_info.get('eta_min', 30),
            'eta_updates': []
        }
        self.eta_history[order_id] = []
        
    def remove_delivery(self, order_id: str):
        if order_id in self.active_deliveries:
            del self.active_deliveries[order_id]
            
    def update_rider_location(self, location: LocationUpdate):
        self.rider_locations[location.rider_id] = location
        
    def simulate_rider_movement(self, rider_id: str, 
                                start_lat: float, start_lon: float,
                                dest_lat: float, dest_lon: float,
                                speed_kmh: float = 25) -> LocationUpdate:
        if rider_id in self.rider_locations:
            last_loc = self.rider_locations[rider_id]
            lat, lon = last_loc.lat, last_loc.lon
        else:
            lat, lon = start_lat, start_lon
            
        distance_to_dest = geodesic((lat, lon), (dest_lat, dest_lon)).kilometers
        
        if distance_to_dest > 0.01:
            move_distance_km = (speed_kmh / 3600) * self.update_interval_sec
            
            ratio = min(move_distance_km / distance_to_dest, 1.0)
            new_lat = lat + (dest_lat - lat) * ratio
            new_lon = lon + (dest_lon - lon) * ratio
            
            heading = np.arctan2(dest_lat - lat, dest_lon - lon) * 180 / np.pi
        else:
            new_lat, new_lon = dest_lat, dest_lon
            heading = 0.0
            speed_kmh = 0
            
        location = LocationUpdate(
            rider_id=rider_id,
            lat=new_lat,
            lon=new_lon,
            timestamp=datetime.now(),
            speed_kmh=speed_kmh,
            heading=heading
        )
        
        self.update_rider_location(location)
        return location
        
    def calculate_distance(self, lat1: float, lon1: float, 
                          lat2: float, lon2: float) -> float:
        return geodesic((lat1, lon1), (lat2, lon2)).kilometers
        
    def update_eta(self, order_id: str,
                  traffic_factor: float = 1.0,
                  weather_factor: float = 1.0) -> Optional[ETAUpdate]:
        if order_id not in self.active_deliveries:
            return None
            
        delivery = self.active_deliveries[order_id]
        rider_id = delivery['rider_id']
        
        if rider_id not in self.rider_locations:
            return None
            
        rider_loc = self.rider_locations[rider_id]
        
        remaining_to_rest = self.calculate_distance(
            rider_loc.lat, rider_loc.lon,
            delivery['restaurant_lat'], delivery['restaurant_lon']
        )
        
        rest_to_user = self.calculate_distance(
            delivery['restaurant_lat'], delivery['restaurant_lon'],
            delivery['user_lat'], delivery['user_lon']
        )
        
        if remaining_to_rest > 0.05:
            current_phase = '前往餐厅'
            remaining_distance = remaining_to_rest + rest_to_user
        else:
            current_phase = '配送中'
            remaining_distance = self.calculate_distance(
                rider_loc.lat, rider_loc.lon,
                delivery['user_lat'], delivery['user_lon']
            )
        
        effective_speed = max(rider_loc.speed_kmh, 15)
        base_travel_time = (remaining_distance / effective_speed) * 60
        adjusted_travel_time = base_travel_time * traffic_factor * weather_factor
        
        if remaining_to_rest > 0.05:
            prep_remaining = max(0, delivery['prep_time_min'] - 
                                (datetime.now() - delivery['start_time']).total_seconds() / 60)
            total_eta = adjusted_travel_time + prep_remaining
        else:
            total_eta = adjusted_travel_time
        
        total_eta = max(1, total_eta)
        
        previous_eta = delivery['eta_updates'][-1].updated_eta_min if delivery['eta_updates'] else delivery['initial_eta']
        eta_change = total_eta - previous_eta
        
        delay_reasons = []
        if traffic_factor > 1.1:
            delay_reasons.append("交通拥堵")
        if weather_factor > 1.1:
            delay_reasons.append("天气影响")
        if eta_change > 5:
            delay_reasons.append("行程延误")
        
        confidence = max(0.6, 0.95 - remaining_distance * 0.02)
        
        eta_update = ETAUpdate(
            order_id=order_id,
            rider_id=rider_id,
            current_lat=rider_loc.lat,
            current_lon=rider_loc.lon,
            updated_eta_min=round(total_eta, 1),
            previous_eta_min=round(previous_eta, 1),
            eta_change_min=round(eta_change, 1),
            remaining_distance_km=round(remaining_distance, 2),
            current_status=current_phase,
            timestamp=datetime.now(),
            confidence=round(confidence, 2),
            delay_reasons=delay_reasons
        )
        
        delivery['eta_updates'].append(eta_update)
        self.eta_history[order_id].append(eta_update)
        
        for callback in self._callbacks:
            try:
                callback(eta_update)
            except Exception as e:
                print(f"Callback error: {e}")
        
        return eta_update
        
    def _tracking_loop(self):
        while self._is_tracking:
            try:
                for order_id in list(self.active_deliveries.keys()):
                    delivery = self.active_deliveries[order_id]
                    
                    self.simulate_rider_movement(
                        rider_id=delivery['rider_id'],
                        start_lat=delivery['rider_start_lat'],
                        start_lon=delivery['rider_start_lon'],
                        dest_lat=delivery['user_lat'],
                        dest_lon=delivery['user_lon'],
                        speed_kmh=delivery.get('rider_speed', 25)
                    )
                    
                    self.update_eta(
                        order_id,
                        traffic_factor=delivery.get('traffic_factor', 1.0),
                        weather_factor=delivery.get('weather_factor', 1.0)
                    )
                    
            except Exception as e:
                print(f"Tracking loop error: {e}")
                
            time.sleep(self.update_interval_sec)
            
    def get_active_deliveries_summary(self) -> pd.DataFrame:
        if not self.active_deliveries:
            return pd.DataFrame()
            
        summaries = []
        for order_id, delivery in self.active_deliveries.items():
            last_eta = delivery['eta_updates'][-1] if delivery['eta_updates'] else None
            
            summaries.append({
                'order_id': order_id,
                'rider_id': delivery['rider_id'],
                'status': last_eta.current_status if last_eta else '待配送',
                'current_eta_min': last_eta.updated_eta_min if last_eta else delivery['initial_eta'],
                'eta_change_min': last_eta.eta_change_min if last_eta else 0,
                'remaining_distance_km': last_eta.remaining_distance_km if last_eta else 0,
                'confidence': last_eta.confidence if last_eta else 0.9,
                'elapsed_time_min': (datetime.now() - delivery['start_time']).total_seconds() / 60
            })
            
        return pd.DataFrame(summaries)
        
    def get_eta_trend(self, order_id: str) -> pd.DataFrame:
        if order_id not in self.eta_history or not self.eta_history[order_id]:
            return pd.DataFrame()
            
        return pd.DataFrame([{
            'timestamp': u.timestamp,
            'eta_min': u.updated_eta_min,
            'remaining_distance_km': u.remaining_distance_km,
            'confidence': u.confidence
        } for u in self.eta_history[order_id]])

if __name__ == '__main__':
    tracker = RealTimeETATracker(update_interval_sec=2)
    
    delivery_info = {
        'order_id': 'ORD001',
        'rider_id': 'Rider001',
        'rider_start_lat': 39.9142,
        'rider_start_lon': 116.4174,
        'restaurant_lat': 39.9042,
        'restaurant_lon': 116.4074,
        'user_lat': 39.8942,
        'user_lon': 116.3974,
        'prep_time_min': 15,
        'eta_min': 35,
        'rider_speed': 25,
        'traffic_factor': 1.1,
        'weather_factor': 1.0
    }
    
    tracker.add_delivery(delivery_info)
    tracker.start_tracking()
    
    print("实时ETA跟踪测试 (运行5秒)...")
    time.sleep(5)
    
    tracker.stop_tracking()
    
    print("\n配送摘要:")
    print(tracker.get_active_deliveries_summary())
    
    print("\nETA趋势:")
    print(tracker.get_eta_trend('ORD001'))
