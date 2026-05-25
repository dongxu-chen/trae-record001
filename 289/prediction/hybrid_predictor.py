import math
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from collections import defaultdict
from .kalman_filter import BusKalmanTracker
from .xgboost_predictor import XGBoostPredictor
from data.data_generator import DataGenerator
from data.data_models import PredictionResult, GPSData
from config import Config


class DispatchSuggestion:
    def __init__(self):
        self.route_id = ''
        self.suggestion_type = ''
        self.current_interval = 0.0
        self.suggested_interval = 0.0
        self.extra_buses_needed = 0
        self.reason = ''
        self.priority = 'low'
        self.timestamp = None
    
    def to_dict(self) -> Dict:
        return {
            'route_id': self.route_id,
            'suggestion_type': self.suggestion_type,
            'current_interval': self.current_interval,
            'suggested_interval': self.suggested_interval,
            'extra_buses_needed': self.extra_buses_needed,
            'reason': self.reason,
            'priority': self.priority,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None
        }


class HybridPredictor:
    def __init__(self):
        self.kalman_tracker = BusKalmanTracker()
        self.xgboost_predictor = XGBoostPredictor()
        self.data_generator = DataGenerator()
        self.prediction_history = {}
        
        self.segment_travel_history: Dict[str, List[Dict]] = defaultdict(list)
        self.segment_delay_stats: Dict[str, Dict] = {}
        self._initialize_segment_stats()
        
        self.dispatch_history: Dict[str, List[datetime]] = defaultdict(list)
        self.last_dispatch_suggestions: List[DispatchSuggestion] = []
        
        self.announcement_triggered: Dict[str, set] = defaultdict(set)
    
    def _initialize_segment_stats(self):
        for route_id, route_info in Config.BUS_ROUTES.items():
            num_segments = len(route_info['stations']) - 1
            for i in range(num_segments):
                segment_id = f"{route_id}_seg_{i}"
                self.segment_delay_stats[segment_id] = {
                    'segment_id': segment_id,
                    'route_id': route_id,
                    'from_station': route_info['stations'][i]['name'],
                    'to_station': route_info['stations'][i+1]['name'],
                    'total_trips': 0,
                    'delayed_trips': 0,
                    'avg_delay': 0.0,
                    'max_delay': 0.0,
                    'on_time_rate': 1.0,
                    'delay_distribution': {'early': 0, 'on_time': 0, 'late': 0, 'very_late': 0}
                }
    
    def _get_stop_light_density(self, route_id: str, segment_idx: int) -> float:
        route_info = Config.BUS_ROUTES.get(route_id, {})
        stop_light_densities = route_info.get('stop_light_density', [])
        if segment_idx < len(stop_light_densities):
            return stop_light_densities[segment_idx]
        return 1.0
    
    def update_bus_gps(self, gps_data: GPSData, route_id: str = None, segment_idx: int = 0):
        traffic_level = self.data_generator.get_traffic_level(route_id, segment_idx) if route_id else 0
        stop_light_density = self._get_stop_light_density(route_id, segment_idx) if route_id else 1.0
        
        self.kalman_tracker.update_bus(
            gps_data.bus_id,
            gps_data.lat,
            gps_data.lon,
            gps_data.speed,
            gps_data.heading,
            route_id=route_id,
            segment_idx=segment_idx,
            traffic_level=traffic_level,
            stop_light_density=stop_light_density
        )
    
    def haversine_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        R = 6371000
        phi1 = math.radians(lat1)
        phi2 = math.radians(lat2)
        delta_phi = math.radians(lat2 - lat1)
        delta_lambda = math.radians(lon2 - lon1)
        
        a = math.sin(delta_phi/2)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda/2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        
        return R * c
    
    def record_segment_travel(self, route_id: str, segment_idx: int, 
                             actual_travel_time: float, scheduled_travel_time: float):
        segment_id = f"{route_id}_seg_{segment_idx}"
        delay = actual_travel_time - scheduled_travel_time
        
        self.segment_travel_history[segment_id].append({
            'timestamp': datetime.now(),
            'actual_time': actual_travel_time,
            'scheduled_time': scheduled_travel_time,
            'delay': delay
        })
        
        if len(self.segment_travel_history[segment_id]) > 1000:
            self.segment_travel_history[segment_id] = self.segment_travel_history[segment_id][-1000:]
        
        self._update_segment_stats(segment_id, delay)
    
    def _update_segment_stats(self, segment_id: str, delay: float):
        if segment_id not in self.segment_delay_stats:
            return
        
        stats = self.segment_delay_stats[segment_id]
        stats['total_trips'] += 1
        
        if delay < -60:
            stats['delay_distribution']['early'] += 1
        elif delay <= 180:
            stats['delay_distribution']['on_time'] += 1
        elif delay <= 300:
            stats['delay_distribution']['late'] += 1
            stats['delayed_trips'] += 1
        else:
            stats['delay_distribution']['very_late'] += 1
            stats['delayed_trips'] += 1
        
        stats['avg_delay'] = ((stats['avg_delay'] * (stats['total_trips'] - 1) + delay) 
                              / stats['total_trips'])
        stats['max_delay'] = max(stats['max_delay'], delay)
        stats['on_time_rate'] = (
            (stats['delay_distribution']['on_time'] + stats['delay_distribution']['early']) 
            / stats['total_trips']
        )
    
    def get_delay_high_risk_segments(self, top_n: int = 5) -> List[Dict]:
        sorted_segments = sorted(
            self.segment_delay_stats.values(),
            key=lambda x: x.get('avg_delay', 0),
            reverse=True
        )
        return sorted_segments[:top_n]
    
    def predict_next_station(self, bus_id: str, route_id: str, 
                           current_station_idx: int, 
                           current_lat: float, current_lon: float,
                           speed: float,
                           passenger_load_factor: float = 0.5,
                           boarding_count: int = 10,
                           alighting_count: int = 8) -> PredictionResult:
        stations = Config.BUS_ROUTES[route_id]['stations']
        next_station_idx = (current_station_idx + 1) % len(stations)
        next_station = stations[next_station_idx]
        
        distance_to_next = self.haversine_distance(
            current_lat, current_lon,
            next_station['lat'], next_station['lon']
        )
        
        traffic_level = self.data_generator.get_traffic_level(route_id, current_station_idx)
        stop_light_density = self._get_stop_light_density(route_id, current_station_idx)
        
        stop_light_delay = stop_light_density * 30 * (1 + traffic_level * 0.2)
        
        dwell_time = 10.0 + (boarding_count + alighting_count) * 1.5 + passenger_load_factor * 10.0 + traffic_level * 3.0
        
        kalman_estimation = self.kalman_tracker.estimate_arrival_time(
            bus_id,
            next_station['lat'],
            next_station['lon'],
            distance_to_next,
            route_id=route_id,
            segment_idx=current_station_idx,
            stop_light_delay=stop_light_delay
        )
        
        xgb_prediction, xgb_confidence = self.xgboost_predictor.predict_arrival_time(
            route_id=route_id,
            current_station_idx=current_station_idx,
            distance_to_next=distance_to_next,
            traffic_level=traffic_level,
            speed=speed,
            dwell_time=dwell_time,
            stop_light_density=stop_light_density,
            passenger_load_factor=passenger_load_factor,
            boarding_count=boarding_count,
            alighting_count=alighting_count
        )
        
        if kalman_estimation is not None:
            kalman_weight = 0.35
            xgb_weight = 0.65
            final_prediction = kalman_estimation * kalman_weight + xgb_prediction * xgb_weight
            confidence = xgb_confidence * 0.85 + 0.15
        else:
            final_prediction = xgb_prediction
            confidence = xgb_confidence
        
        final_prediction += passenger_load_factor * 10.0
        
        predicted_arrival = datetime.now() + timedelta(seconds=final_prediction)
        
        scheduled_interval = Config.BUS_ROUTES[route_id]['scheduled_interval'] * 60
        base_scheduled = datetime.now() + timedelta(seconds=scheduled_interval * (next_station_idx - current_station_idx))
        scheduled_arrival = base_scheduled
        
        delay_seconds = (predicted_arrival - scheduled_arrival).total_seconds()
        
        result = PredictionResult(
            bus_id=bus_id,
            route_id=route_id,
            station_id=next_station['id'],
            station_name=next_station['name'],
            predicted_arrival=predicted_arrival,
            scheduled_arrival=scheduled_arrival,
            delay_seconds=delay_seconds,
            confidence=confidence,
            traffic_level=traffic_level
        )
        
        result.stop_light_density = stop_light_density
        result.stop_light_delay = stop_light_delay
        
        if bus_id not in self.prediction_history:
            self.prediction_history[bus_id] = []
        self.prediction_history[bus_id].append({
            'timestamp': datetime.now(),
            'prediction': final_prediction,
            'kalman': kalman_estimation,
            'xgboost': xgb_prediction,
            'stop_light_density': stop_light_density
        })
        
        if len(self.prediction_history[bus_id]) > 100:
            self.prediction_history[bus_id] = self.prediction_history[bus_id][-100:]
        
        return result
    
    def predict_all_stations(self, bus_id: str, route_id: str,
                           current_station_idx: int,
                           current_lat: float, current_lon: float,
                           speed: float, num_stations: int = 3) -> List[PredictionResult]:
        predictions = []
        stations = Config.BUS_ROUTES[route_id]['stations']
        
        for i in range(num_stations):
            target_idx = (current_station_idx + 1 + i) % len(stations)
            
            if i == 0:
                pred = self.predict_next_station(
                    bus_id, route_id, current_station_idx,
                    current_lat, current_lon, speed
                )
                predictions.append(pred)
            else:
                prev_pred = predictions[-1]
                distance = self.haversine_distance(
                    stations[target_idx - 1]['lat'], stations[target_idx - 1]['lon'],
                    stations[target_idx]['lat'], stations[target_idx]['lon']
                )
                
                traffic_level = self.data_generator.get_traffic_level(route_id, target_idx - 1)
                stop_light_density = self._get_stop_light_density(route_id, target_idx - 1)
                
                xgb_pred, confidence = self.xgboost_predictor.predict_arrival_time(
                    route_id=route_id,
                    current_station_idx=target_idx - 1,
                    distance_to_next=distance,
                    traffic_level=traffic_level,
                    speed=speed,
                    stop_light_density=stop_light_density
                )
                
                predicted_arrival = prev_pred.predicted_arrival + timedelta(seconds=xgb_pred)
                scheduled_arrival = prev_pred.scheduled_arrival + timedelta(
                    seconds=Config.BUS_ROUTES[route_id]['scheduled_interval'] * 60
                )
                delay_seconds = (predicted_arrival - scheduled_arrival).total_seconds()
                
                predictions.append(PredictionResult(
                    bus_id=bus_id,
                    route_id=route_id,
                    station_id=stations[target_idx]['id'],
                    station_name=stations[target_idx]['name'],
                    predicted_arrival=predicted_arrival,
                    scheduled_arrival=scheduled_arrival,
                    delay_seconds=delay_seconds,
                    confidence=confidence * (1 - i * 0.1),
                    traffic_level=traffic_level
                ))
        
        return predictions
    
    def get_punctuality_stats(self, route_id: Optional[str] = None) -> Dict:
        history_data = self.data_generator.historical_data
        
        if route_id:
            history_data = [h for h in history_data if h.route_id == route_id]
        
        if not history_data:
            return {
                'total': 0,
                'on_time': 0,
                'early': 0,
                'delayed': 0,
                'on_time_rate': 0.0,
                'avg_delay': 0.0,
                'segment_stats': [],
                'high_risk_segments': []
            }
        
        total = len(history_data)
        on_time = sum(1 for h in history_data if abs(h.delay_seconds) <= 180)
        early = sum(1 for h in history_data if h.delay_seconds < -180)
        delayed = sum(1 for h in history_data if h.delay_seconds > 180)
        avg_delay = sum(h.delay_seconds for h in history_data) / total
        
        segment_stats = []
        for seg_id, stats in self.segment_delay_stats.items():
            if route_id and stats['route_id'] != route_id:
                continue
            segment_stats.append(stats)
        
        high_risk_segments = self.get_delay_high_risk_segments(5)
        if route_id:
            high_risk_segments = [s for s in high_risk_segments if s['route_id'] == route_id]
        
        return {
            'total': total,
            'on_time': on_time,
            'early': early,
            'delayed': delayed,
            'on_time_rate': on_time / total if total > 0 else 0,
            'avg_delay': avg_delay,
            'segment_stats': segment_stats,
            'high_risk_segments': high_risk_segments
        }
    
    def record_bus_dispatch(self, route_id: str):
        self.dispatch_history[route_id].append(datetime.now())
        if len(self.dispatch_history[route_id]) > 20:
            self.dispatch_history[route_id] = self.dispatch_history[route_id][-20:]
    
    def calculate_headway(self, route_id: str) -> float:
        dispatches = self.dispatch_history.get(route_id, [])
        if len(dispatches) < 2:
            return Config.BUS_ROUTES[route_id]['scheduled_interval'] * 60
        
        intervals = []
        for i in range(1, len(dispatches)):
            interval = (dispatches[i] - dispatches[i-1]).total_seconds()
            intervals.append(interval)
        
        return sum(intervals) / len(intervals)
    
    def generate_dispatch_suggestions(self) -> List[Dict]:
        suggestions = []
        
        for route_id, route_info in Config.BUS_ROUTES.items():
            scheduled_interval = route_info['scheduled_interval'] * 60
            current_headway = self.calculate_headway(route_id)
            
            route_buses = [b for b in self.data_generator.buses.values() if b['route_id'] == route_id]
            avg_passenger_load = 0
            if route_buses:
                loads = [b.get('current_load', 40) for b in route_buses]
                avg_passenger_load = sum(loads) / len(loads) / 80
            
            max_delay = 0
            for bus_id in [b['bus_id'] for b in route_buses]:
                if bus_id in self.data_generator.buses:
                    bus = self.data_generator.buses[bus_id]
                    pred = self.predict_next_station(
                        bus_id, route_id, bus['current_station_index'],
                        bus['lat'], bus['lon'], bus['speed']
                    )
                    max_delay = max(max_delay, pred.delay_seconds)
            
            suggestion = DispatchSuggestion()
            suggestion.route_id = route_id
            suggestion.timestamp = datetime.now()
            suggestion.current_interval = current_headway
            
            if current_headway > scheduled_interval * 1.5 and avg_passenger_load > 0.7:
                suggestion.suggestion_type = 'add_bus'
                suggestion.suggested_interval = scheduled_interval * 0.8
                suggestion.extra_buses_needed = 1
                suggestion.reason = f'发车间隔过大({round(current_headway/60, 1)}分钟)且乘客量高({round(avg_passenger_load*100)}%)'
                suggestion.priority = 'high'
            elif current_headway > scheduled_interval * 1.3 or avg_passenger_load > 0.85:
                suggestion.suggestion_type = 'increase_frequency'
                suggestion.suggested_interval = scheduled_interval * 0.9
                suggestion.extra_buses_needed = 0
                suggestion.reason = f'建议增加发车频率，当前间隔{round(current_headway/60, 1)}分钟'
                suggestion.priority = 'medium'
            elif max_delay > 300 and avg_passenger_load > 0.6:
                suggestion.suggestion_type = 'express_service'
                suggestion.suggested_interval = scheduled_interval
                suggestion.extra_buses_needed = 1
                suggestion.reason = f'线路严重延误，建议加开快车'
                suggestion.priority = 'medium'
            else:
                continue
            
            suggestions.append(suggestion.to_dict())
        
        self.last_dispatch_suggestions = suggestions
        return suggestions
    
    def check_announcement_triggers(self) -> List[Dict]:
        announcements = []
        
        for bus_id, bus in self.data_generator.buses.items():
            route_id = bus['route_id']
            stations = Config.BUS_ROUTES[route_id]['stations']
            current_idx = bus['current_station_index']
            
            prediction = self.predict_next_station(
                bus_id, route_id, current_idx,
                bus['lat'], bus['lon'], bus['speed']
            )
            
            eta_seconds = (prediction.predicted_arrival - datetime.now()).total_seconds()
            
            trigger_thresholds = [180, 60, 10]
            station_id = prediction.station_id
            
            for threshold in trigger_thresholds:
                trigger_key = f"{station_id}_{threshold}"
                if trigger_key not in self.announcement_triggered[bus_id]:
                    if 0 < eta_seconds <= threshold + 5:
                        announcements.append({
                            'bus_id': bus_id,
                            'route_id': route_id,
                            'route_name': Config.BUS_ROUTES[route_id]['name'],
                            'station_id': station_id,
                            'station_name': prediction.station_name,
                            'eta_seconds': round(eta_seconds),
                            'trigger_type': f'arrival_{threshold}s',
                            'message': self._generate_announcement_message(
                                Config.BUS_ROUTES[route_id]['name'],
                                prediction.station_name,
                                round(eta_seconds)
                            ),
                            'timestamp': datetime.now().isoformat()
                        })
                        self.announcement_triggered[bus_id].add(trigger_key)
        
        return announcements
    
    def _generate_announcement_message(self, route_name: str, station_name: str, eta_seconds: int) -> str:
        if eta_seconds > 60:
            minutes = round(eta_seconds / 60)
            return f"{route_name}路公交车即将到达{station_name}，预计还需{minutes}分钟"
        elif eta_seconds > 10:
            return f"{route_name}路公交车即将到达{station_name}，请做好乘车准备"
        else:
            return f"{route_name}路公交车已到达{station_name}"
    
    def get_delay_warnings(self) -> List[Dict]:
        warnings = []
        
        for bus_id, bus in self.data_generator.buses.items():
            route_id = bus['route_id']
            stations = Config.BUS_ROUTES[route_id]['stations']
            current_idx = bus['current_station_index']
            
            prediction = self.predict_next_station(
                bus_id, route_id, current_idx,
                bus['lat'], bus['lon'], bus['speed']
            )
            
            if prediction.delay_seconds > Config.DELAY_WARNING_THRESHOLD:
                warnings.append({
                    'bus_id': bus_id,
                    'route_id': route_id,
                    'route_name': Config.BUS_ROUTES[route_id]['name'],
                    'station': prediction.station_name,
                    'delay_seconds': prediction.delay_seconds,
                    'predicted_arrival': prediction.predicted_arrival.isoformat(),
                    'severity': 'high' if prediction.delay_seconds > 300 else 'medium',
                    'traffic_level': prediction.traffic_level
                })
        
        return warnings
