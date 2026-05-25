from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, Dict
import json


@dataclass
class GPSData:
    bus_id: str
    route_id: str
    lat: float
    lon: float
    speed: float
    timestamp: datetime
    heading: float = 0.0
    
    def to_dict(self) -> Dict:
        return {
            'bus_id': self.bus_id,
            'route_id': self.route_id,
            'lat': self.lat,
            'lon': self.lon,
            'speed': self.speed,
            'timestamp': self.timestamp.isoformat(),
            'heading': self.heading
        }
    
    def to_json(self) -> str:
        return json.dumps(self.to_dict())


@dataclass
class TrafficData:
    segment_id: str
    route_id: str
    traffic_level: int
    avg_speed: float
    timestamp: datetime
    
    def to_dict(self) -> Dict:
        return {
            'segment_id': self.segment_id,
            'route_id': self.route_id,
            'traffic_level': self.traffic_level,
            'avg_speed': self.avg_speed,
            'timestamp': self.timestamp.isoformat()
        }


@dataclass
class PassengerData:
    bus_id: str
    route_id: str
    station_id: str
    boarding_count: int
    alighting_count: int
    current_load: int
    max_capacity: int = 80
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()
    
    def to_dict(self) -> Dict:
        return {
            'bus_id': self.bus_id,
            'route_id': self.route_id,
            'station_id': self.station_id,
            'boarding_count': self.boarding_count,
            'alighting_count': self.alighting_count,
            'current_load': self.current_load,
            'load_factor': self.current_load / self.max_capacity,
            'timestamp': self.timestamp.isoformat()
        }


@dataclass
class StationHistory:
    station_id: str
    route_id: str
    bus_id: str
    arrival_time: datetime
    departure_time: Optional[datetime]
    dwell_time: float
    scheduled_arrival: datetime
    delay_seconds: float
    passenger_data: Optional[PassengerData] = None
    
    def to_dict(self) -> Dict:
        return {
            'station_id': self.station_id,
            'route_id': self.route_id,
            'bus_id': self.bus_id,
            'arrival_time': self.arrival_time.isoformat(),
            'departure_time': self.departure_time.isoformat() if self.departure_time else None,
            'dwell_time': self.dwell_time,
            'scheduled_arrival': self.scheduled_arrival.isoformat(),
            'delay_seconds': self.delay_seconds,
            'passenger_data': self.passenger_data.to_dict() if self.passenger_data else None
        }


@dataclass
class BusState:
    bus_id: str
    route_id: str
    current_station_index: int
    next_station_index: int
    distance_to_next: float
    predicted_arrival: Optional[datetime]
    scheduled_arrival: Optional[datetime]
    delay_seconds: float = 0.0
    gps_data: Optional[GPSData] = None
    
    def to_dict(self) -> Dict:
        return {
            'bus_id': self.bus_id,
            'route_id': self.route_id,
            'current_station_index': self.current_station_index,
            'next_station_index': self.next_station_index,
            'distance_to_next': self.distance_to_next,
            'predicted_arrival': self.predicted_arrival.isoformat() if self.predicted_arrival else None,
            'scheduled_arrival': self.scheduled_arrival.isoformat() if self.scheduled_arrival else None,
            'delay_seconds': self.delay_seconds,
            'gps': self.gps_data.to_dict() if self.gps_data else None
        }


@dataclass
class PredictionResult:
    bus_id: str
    route_id: str
    station_id: str
    station_name: str
    predicted_arrival: datetime
    scheduled_arrival: datetime
    delay_seconds: float
    confidence: float
    traffic_level: int
    
    def to_dict(self) -> Dict:
        return {
            'bus_id': self.bus_id,
            'route_id': self.route_id,
            'station_id': self.station_id,
            'station_name': self.station_name,
            'predicted_arrival': self.predicted_arrival.isoformat(),
            'scheduled_arrival': self.scheduled_arrival.isoformat(),
            'delay_seconds': self.delay_seconds,
            'confidence': self.confidence,
            'traffic_level': self.traffic_level,
            'is_delayed': self.delay_seconds > 180,
            'is_early': self.delay_seconds < -60
        }
