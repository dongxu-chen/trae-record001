from dataclasses import dataclass, field
from typing import List, Optional, Dict


@dataclass
class Customer:
    id: int
    x: float
    y: float
    demand: float
    ready_time: float
    due_time: float
    service_time: float = 0.0
    node_id: Optional[int] = None
    assigned_depot: Optional[int] = None


@dataclass
class Depot:
    id: int
    x: float
    y: float
    num_vehicles: int = 5
    vehicle_capacity: float = 100.0
    node_id: Optional[int] = None


@dataclass
class TrafficFactor:
    hour_of_day: int = 12
    congestion_level: str = "normal"
    congestion_matrix: Optional[List[List[float]]] = None
    road_speed_factors: Dict[str, float] = field(default_factory=dict)

    def get_factor(self, day_type: str = "weekday") -> float:
        factors = {
            "low": 0.8,
            "normal": 1.0,
            "medium": 1.3,
            "high": 1.6,
            "severe": 2.0,
        }
        base = factors.get(self.congestion_level, 1.0)
        
        hour_factors = {
            0: 0.6, 1: 0.5, 2: 0.5, 3: 0.6, 4: 0.7, 5: 0.8,
            6: 1.4, 7: 1.8, 8: 2.0, 9: 1.6, 10: 1.2, 11: 1.1,
            12: 1.3, 13: 1.2, 14: 1.1, 15: 1.2, 16: 1.5, 17: 1.9,
            18: 1.7, 19: 1.3, 20: 1.0, 21: 0.8, 22: 0.7, 23: 0.6,
        }
        
        if day_type == "weekend":
            hour_factors = {k: v * 0.7 for k, v in hour_factors.items()}
        
        hour_factor = hour_factors.get(self.hour_of_day, 1.0)
        return base * hour_factor


@dataclass
class CarbonConfig:
    enabled: bool = True
    emission_factor: float = 0.27
    fuel_efficiency: float = 8.0
    carbon_price_per_ton: float = 50.0


@dataclass
class VehicleRoute:
    vehicle_id: int
    customer_ids: List[int] = field(default_factory=list)
    distances: List[float] = field(default_factory=list)
    arrival_times: List[float] = field(default_factory=list)
    departure_times: List[float] = field(default_factory=list)
    total_distance: float = 0.0
    total_demand: float = 0.0
    waiting_time: float = 0.0
    lateness: float = 0.0
    carbon_emission: float = 0.0
    depot_id: int = 0
    travel_times: List[float] = field(default_factory=list)
    traffic_adjusted_times: List[float] = field(default_factory=list)

    @property
    def load_rate(self) -> float:
        return self.total_demand / self._capacity if hasattr(self, "_capacity") and self._capacity > 0 else 0.0

    @property
    def is_feasible(self) -> bool:
        return self.lateness <= 1e-8


@dataclass
class Solution:
    routes: List[VehicleRoute] = field(default_factory=list)
    total_distance: float = 0.0
    total_waiting_time: float = 0.0
    total_lateness: float = 0.0
    used_vehicles: int = 0
    avg_load_rate: float = 0.0
    is_feasible: bool = True
    total_carbon_emission: float = 0.0
    carbon_cost: float = 0.0
    depot_assignments: Dict[int, List[int]] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "total_distance": round(self.total_distance, 2),
            "total_waiting_time": round(self.total_waiting_time, 2),
            "total_lateness": round(self.total_lateness, 2),
            "used_vehicles": self.used_vehicles,
            "avg_load_rate": round(self.avg_load_rate * 100, 2),
            "is_feasible": self.is_feasible,
            "total_carbon_emission": round(self.total_carbon_emission, 2),
            "carbon_cost": round(self.carbon_cost, 2),
            "depot_assignments": {str(k): v for k, v in self.depot_assignments.items()},
            "routes": [
                {
                    "vehicle_id": r.vehicle_id,
                    "depot_id": r.depot_id,
                    "customer_ids": r.customer_ids,
                    "arrival_times": [round(t, 2) for t in r.arrival_times],
                    "departure_times": [round(t, 2) for t in r.departure_times],
                    "distances": [round(d, 2) for d in r.distances],
                    "total_distance": round(r.total_distance, 2),
                    "total_demand": round(r.total_demand, 2),
                    "waiting_time": round(r.waiting_time, 2),
                    "lateness": round(r.lateness, 2),
                    "load_rate": round(r.load_rate, 4),
                    "is_feasible": r.is_feasible,
                    "carbon_emission": round(r.carbon_emission, 4),
                    "travel_times": [round(t, 2) for t in r.travel_times],
                }
                for r in self.routes
            ],
        }


@dataclass
class ProblemData:
    depots: List[Depot]
    customers: List[Customer]
    distance_matrix: Optional[List[List[float]]] = None
    time_matrix: Optional[List[List[float]]] = None
    traffic_factor: Optional[TrafficFactor] = None
    carbon_config: Optional[CarbonConfig] = None
    is_multi_depot: bool = False

    @property
    def num_customers(self) -> int:
        return len(self.customers)

    @property
    def num_depots(self) -> int:
        return len(self.depots)

    @property
    def total_vehicles(self) -> int:
        return sum(d.num_vehicles for d in self.depots)

    @property
    def primary_depot(self) -> Depot:
        return self.depots[0] if self.depots else None