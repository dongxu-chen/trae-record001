from pydantic import BaseModel
from typing import Optional


class ZoneInfo(BaseModel):
    zone_id: str
    name: str
    total_spots: int
    walk_distance_from_entrance_a: float
    walk_distance_from_entrance_b: float


class SensorReading(BaseModel):
    zone_id: str
    total_spots: int
    occupied_spots: int
    available_spots: int
    occupancy_rate: float
    timestamp: str
    event_impact: Optional[dict] = None


class PredictionPoint(BaseModel):
    timestamp: str
    available_spots: float
    confidence: float
    event_impact: Optional[float] = None


class PredictionResult(BaseModel):
    zone_id: str
    predictions: list[PredictionPoint]
    model_type: str
    accuracy_metrics: dict[str, float]
    active_events: list[dict]


class AlternativeZone(BaseModel):
    zone_id: str
    score: float
    reason: str


class GuidanceResult(BaseModel):
    recommended_zone: str
    estimated_wait_minutes: float
    confidence: float
    walking_distance: float
    reason: str
    alternatives: list[AlternativeZone]
    utility_score: float


class GuidanceFeedback(BaseModel):
    recommended_zone: str
    actual_zone: Optional[str] = None
    entrance: str
    walking_distance: float = 0
    success: bool = True


class EventCreate(BaseModel):
    event_type: str
    title: str
    event_date: str
    start_hour: int
    end_hour: int
    impact_zone_ids: str
    impact_factor: float = 1.5
    description: Optional[str] = None


class EventInfo(BaseModel):
    id: int
    event_type: str
    title: str
    event_date: str
    start_hour: int
    end_hour: int
    impact_zone_ids: str
    impact_factor: float
    description: Optional[str]
    created_at: str


class ReservationCreate(BaseModel):
    zone_id: str
    vehicle_plate: str
    arrival_time: str
    duration_hours: float = 2.0


class ReservationInfo(BaseModel):
    id: int
    zone_id: str
    vehicle_plate: str
    reserved_spot: int
    arrival_time: str
    duration_hours: float
    status: str
    price: float
    created_at: str


class ZonePricing(BaseModel):
    zone_id: str
    base_price: float
    current_price: float
    surge_factor: float
    demand_level: str
    hourly_rate: float
    updated_at: str


class NavigationRequest(BaseModel):
    zone_id: str
    entrance: str = "A"
    vehicle_plate: Optional[str] = None


class NavigationRoute(BaseModel):
    zone_id: str
    entrance: str
    driving_distance: float
    driving_time_minutes: float
    walking_distance: float
    walking_time_minutes: float
    turn_by_turn: list[dict]
    estimated_arrival: str
    push_status: str
    push_target: str
