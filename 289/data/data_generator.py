import random
import math
from datetime import datetime, timedelta
from typing import List, Dict
import asyncio
from .data_models import GPSData, TrafficData, StationHistory, BusState
from config import Config


class DataGenerator:
    def __init__(self):
        self.buses = {}
        self._initialize_buses()
        self.traffic_data = {}
        self.historical_data = []
    
    def _initialize_buses(self):
        bus_count = 0
        for route_id, route_info in Config.BUS_ROUTES.items():
            num_buses = 3
            for i in range(num_buses):
                bus_id = f"{route_id}_{i+1:02d}"
                stations = route_info['stations']
                start_idx = i * len(stations) // num_buses
                
                self.buses[bus_id] = {
                    'bus_id': bus_id,
                    'route_id': route_id,
                    'current_station_index': start_idx,
                    'progress': 0.0,
                    'lat': stations[start_idx]['lat'],
                    'lon': stations[start_idx]['lon'],
                    'speed': random.uniform(15, 25),
                    'heading': random.uniform(0, 360),
                    'last_update': datetime.now(),
                    'last_station_arrival': datetime.now() - timedelta(minutes=start_idx * 15)
                }
    
    def haversine_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        R = 6371000
        phi1 = math.radians(lat1)
        phi2 = math.radians(lat2)
        delta_phi = math.radians(lat2 - lat1)
        delta_lambda = math.radians(lon2 - lon1)
        
        a = math.sin(delta_phi/2)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda/2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        
        return R * c
    
    def generate_gps_data(self, bus_id: str) -> GPSData:
        bus = self.buses[bus_id]
        route_id = bus['route_id']
        stations = Config.BUS_ROUTES[route_id]['stations']
        
        current_idx = bus['current_station_index']
        next_idx = (current_idx + 1) % len(stations)
        
        current_station = stations[current_idx]
        next_station = stations[next_idx]
        
        segment_distance = self.haversine_distance(
            current_station['lat'], current_station['lon'],
            next_station['lat'], next_station['lon']
        )
        
        bus['progress'] += random.uniform(0.02, 0.05)
        
        if bus['progress'] >= 1.0:
            bus['progress'] = 0.0
            bus['current_station_index'] = next_idx
            bus['last_station_arrival'] = datetime.now()
            current_station = stations[next_idx]
            next_idx = (next_idx + 1) % len(stations)
            next_station = stations[next_idx]
        
        progress = bus['progress']
        lat = current_station['lat'] + (next_station['lat'] - current_station['lat']) * progress
        lon = current_station['lon'] + (next_station['lon'] - current_station['lon']) * progress
        
        base_speed = random.uniform(15, 30)
        traffic_factor = 1.0 - (self.get_traffic_level(route_id, current_idx) * 0.15)
        speed = max(5, base_speed * traffic_factor)
        
        heading = math.degrees(math.atan2(
            next_station['lat'] - current_station['lat'],
            next_station['lon'] - current_station['lon']
        ))
        
        bus['lat'] = lat
        bus['lon'] = lon
        bus['speed'] = speed
        bus['heading'] = heading
        
        return GPSData(
            bus_id=bus_id,
            route_id=route_id,
            lat=lat,
            lon=lon,
            speed=speed,
            timestamp=datetime.now(),
            heading=heading
        )
    
    def get_traffic_level(self, route_id: str, segment_idx: int) -> int:
        key = f"{route_id}_{segment_idx}"
        if key not in self.traffic_data:
            self.traffic_data[key] = {
                'level': random.randint(0, 3),
                'last_update': datetime.now()
            }
        
        traffic = self.traffic_data[key]
        if (datetime.now() - traffic['last_update']).total_seconds() > 60:
            change = random.choice([-1, 0, 0, 1])
            traffic['level'] = max(0, min(3, traffic['level'] + change))
            traffic['last_update'] = datetime.now()
        
        return traffic['level']
    
    def generate_traffic_data(self, route_id: str) -> List[TrafficData]:
        stations = Config.BUS_ROUTES[route_id]['stations']
        traffic_list = []
        
        for i in range(len(stations)):
            segment_id = f"SEG_{route_id}_{i:02d}"
            traffic_level = self.get_traffic_level(route_id, i)
            avg_speed = 30 - (traffic_level * 7)
            
            traffic_list.append(TrafficData(
                segment_id=segment_id,
                route_id=route_id,
                traffic_level=traffic_level,
                avg_speed=avg_speed,
                timestamp=datetime.now()
            ))
        
        return traffic_list
    
    def generate_passenger_data(self, bus_id: str, station_id: str, station_idx: int) -> PassengerData:
        bus = self.buses[bus_id]
        route_id = bus['route_id']
        
        if 'current_load' not in bus:
            bus['current_load'] = random.randint(20, 40)
        
        hour = datetime.now().hour
        is_peak = (7 <= hour <= 9) or (17 <= hour <= 19)
        
        base_alighting = random.randint(5, 15)
        base_boarding = random.randint(8, 20)
        
        if is_peak:
            base_alighting = int(base_alighting * 1.5)
            base_boarding = int(base_boarding * 1.8)
        
        alighting = min(bus['current_load'], int(random.gauss(base_alighting, 3)))
        boarding = int(random.gauss(base_boarding, 5))
        boarding = max(0, boarding)
        
        bus['current_load'] = bus['current_load'] - alighting + boarding
        bus['current_load'] = max(0, min(80, bus['current_load']))
        
        return PassengerData(
            bus_id=bus_id,
            route_id=route_id,
            station_id=station_id,
            boarding_count=boarding,
            alighting_count=alighting,
            current_load=bus['current_load']
        )
    
    def calculate_dwell_time(self, passenger_data: PassengerData, traffic_level: int) -> float:
        base_dwell = 10.0
        
        passenger_dwell = (passenger_data.boarding_count + passenger_data.alighting_count) * 1.5
        
        load_factor = passenger_data.current_load / passenger_data.max_capacity
        load_dwell = load_factor * 10.0
        
        traffic_dwell = traffic_level * 3.0
        
        total_dwell = base_dwell + passenger_dwell + load_dwell + traffic_dwell
        total_dwell = total_dwell + random.uniform(-2, 5)
        
        return max(8, min(120, total_dwell))
    
    def generate_station_history(self, bus_id: str, station_id: str, station_idx: int = 0) -> StationHistory:
        bus = self.buses[bus_id]
        route_id = bus['route_id']
        
        scheduled_time = bus['last_station_arrival']
        actual_delay = random.uniform(-120, 300)
        arrival_time = scheduled_time + timedelta(seconds=actual_delay)
        
        traffic_level = self.get_traffic_level(route_id, station_idx)
        passenger_data = self.generate_passenger_data(bus_id, station_id, station_idx)
        
        dwell_time = self.calculate_dwell_time(passenger_data, traffic_level)
        departure_time = arrival_time + timedelta(seconds=dwell_time)
        
        history = StationHistory(
            station_id=station_id,
            route_id=route_id,
            bus_id=bus_id,
            arrival_time=arrival_time,
            departure_time=departure_time,
            dwell_time=dwell_time,
            scheduled_arrival=scheduled_time,
            delay_seconds=actual_delay,
            passenger_data=passenger_data
        )
        
        self.historical_data.append(history)
        if len(self.historical_data) > 10000:
            self.historical_data = self.historical_data[-10000:]
        
        return history
    
    def get_all_gps_data(self) -> List[GPSData]:
        return [self.generate_gps_data(bus_id) for bus_id in self.buses.keys()]
    
    def get_bus_state(self, bus_id: str) -> BusState:
        bus = self.buses[bus_id]
        route_id = bus['route_id']
        stations = Config.BUS_ROUTES[route_id]['stations']
        
        current_idx = bus['current_station_index']
        next_idx = (current_idx + 1) % len(stations)
        next_station = stations[next_idx]
        
        distance_to_next = self.haversine_distance(
            bus['lat'], bus['lon'],
            next_station['lat'], next_station['lon']
        )
        
        gps_data = self.generate_gps_data(bus_id)
        
        return BusState(
            bus_id=bus_id,
            route_id=route_id,
            current_station_index=current_idx,
            next_station_index=next_idx,
            distance_to_next=distance_to_next,
            predicted_arrival=None,
            scheduled_arrival=None,
            delay_seconds=0.0,
            gps_data=gps_data
        )
    
    def generate_training_data(self, num_samples: int = 5000) -> List[Dict]:
        training_data = []
        
        for _ in range(num_samples):
            route_id = random.choice(list(Config.BUS_ROUTES.keys()))
            stations = Config.BUS_ROUTES[route_id]['stations']
            
            current_station_idx = random.randint(0, len(stations) - 2)
            distance = random.uniform(100, 2000)
            traffic_level = random.randint(0, 3)
            hour = random.randint(6, 22)
            day_of_week = random.randint(0, 6)
            
            dwell_time = random.uniform(10, 45)
            speed = max(5, random.uniform(15, 30) - (traffic_level * 7))
            travel_time = (distance / (speed * 1000 / 3600)) + dwell_time
            
            base_delay = random.uniform(-60, 120)
            traffic_delay = traffic_level * random.uniform(30, 90)
            peak_delay = 0
            if (7 <= hour <= 9) or (17 <= hour <= 19):
                peak_delay = random.uniform(30, 120)
            
            total_delay = base_delay + traffic_delay + peak_delay
            arrival_seconds = travel_time + total_delay
            
            sample = {
                'route_id': route_id,
                'current_station_idx': current_station_idx,
                'distance_to_next': distance,
                'traffic_level': traffic_level,
                'hour': hour,
                'day_of_week': day_of_week,
                'speed': speed,
                'dwell_time': dwell_time,
                'arrival_seconds': arrival_seconds
            }
            training_data.append(sample)
        
        return training_data
