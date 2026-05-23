from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime


class BusGPSData(BaseModel):
    bus_id: str = Field(..., description="公交车ID")
    route_id: str = Field(..., description="线路号")
    longitude: float = Field(..., description="经度")
    latitude: float = Field(..., description="纬度")
    timestamp: datetime = Field(..., description="时间戳")


class GridDensity(BaseModel):
    grid_id: str
    lon_min: float
    lon_max: float
    lat_min: float
    lat_max: float
    center_lon: float
    center_lat: float
    count: int
    density: float


class TimeWindowData(BaseModel):
    time_start: datetime
    time_end: datetime
    grid_densities: List[GridDensity]
    congestion_segments: List[dict]


class HeatmapResponse(BaseModel):
    city: str
    time_windows: List[TimeWindowData]
    time_range: dict
    grid_size: float
    congestion_threshold: float


class UploadResponse(BaseModel):
    success: bool
    message: str
    record_count: int
    time_range: Optional[dict] = None
