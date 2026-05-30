from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class GalleryAddRequest(BaseModel):
    track_id: str
    camera_id: str
    timestamp: float
    bbox: list[int] | None = Field(default=None, min_length=4, max_length=4)
    image_path: str | None = None
    metadata: dict[str, Any] | None = None


class GalleryAddResponse(BaseModel):
    item_id: str
    track_id: str
    camera_id: str
    timestamp: float


class GalleryBatchAddRequest(BaseModel):
    track_ids: list[str]
    camera_ids: list[str]
    timestamps: list[float]
    bboxes: list[list[int] | None] | None = None
    image_paths: list[str | None] | None = None
    metadata_list: list[dict[str, Any] | None] | None = None


class GalleryBatchAddResponse(BaseModel):
    items: list[GalleryAddResponse]
    count: int


class FeatureSearchRequest(BaseModel):
    feature: list[float]
    camera_id: str = ""
    timestamp: float = 0.0
    top_k: int = Field(default=10, ge=1, le=100)
    use_spatial_temporal: bool = True
    cross_camera_only: bool = False
    allowed_cameras: list[str] | None = None
    excluded_cameras: list[str] | None = None


class ImageSearchRequest(BaseModel):
    camera_id: str
    timestamp: float
    bbox: list[int] | None = Field(default=None, min_length=4, max_length=4)
    top_k: int = Field(default=10, ge=1, le=100)
    use_spatial_temporal: bool = True
    cross_camera_only: bool = False


class SearchResultItem(BaseModel):
    item_id: str
    track_id: str
    camera_id: str
    timestamp: float
    visual_score: float
    spatial_score: float
    temporal_score: float
    combined_score: float
    metadata: dict[str, Any] | None = None


class SearchResponse(BaseModel):
    results: list[SearchResultItem]
    query_camera: str
    query_timestamp: float
    total: int


class ExtractRequest(BaseModel):
    image_path: str
    bbox: list[int] | None = Field(default=None, min_length=4, max_length=4)


class ExtractResponse(BaseModel):
    feature: list[float]
    dimension: int


class GalleryItemResponse(BaseModel):
    item_id: str
    track_id: str
    camera_id: str
    timestamp: float
    bbox: list[int] | None = None
    image_path: str | None = None
    metadata: dict[str, Any] | None = None


class GalleryStatsResponse(BaseModel):
    total_items: int
    index_size: int
    cameras: dict[str, int]
    max_size: int
    lru_enabled: bool
    lru_ttl_seconds: float
    cleanup_interval_seconds: float


class CameraPositionRequest(BaseModel):
    positions: dict[str, list[float]]


class CameraPairConfigRequest(BaseModel):
    cam_from: str
    cam_to: str
    time_window: float | None = None
    spatial_weight: float | None = None
    temporal_weight: float | None = None
    transition_cost: float | None = None


class DeleteResponse(BaseModel):
    success: bool
    message: str


class ClearResponse(BaseModel):
    success: bool
    message: str


class SaveLoadResponse(BaseModel):
    success: bool
    message: str


class DomainAdaptationRequest(BaseModel):
    method: str = "feature"
    adaptation_strength: float = 0.1


class DomainAdaptationResponse(BaseModel):
    success: bool
    epochs_trained: int
    final_loss: float
    message: str
    is_adapted: bool


class CleanupResponse(BaseModel):
    success: bool
    expired_removed: int
    lru_evicted: int
    message: str


class TrajectoryPointResponse(BaseModel):
    item_id: str
    camera_id: str
    timestamp: float
    bbox: list[int] | None = None
    spatial_score: float
    temporal_score: float
    visual_score: float
    combined_score: float
    metadata: dict[str, Any] | None = None


class TrajectoryResponse(BaseModel):
    trajectory_id: str
    track_id: str
    points: list[TrajectoryPointResponse]
    created_at: float
    last_updated_at: float
    is_active: bool
    duration: float
    cameras: list[str]
    num_points: int
    merged_from: list[str]


class TrajectorySearchResponse(BaseModel):
    trajectory_id: str
    track_id: str
    score: float
    num_points: int
    cameras: list[str]


class TrajectoryListResponse(BaseModel):
    trajectories: list[TrajectoryResponse]
    total: int


class TrajectoryStatsResponse(BaseModel):
    total_trajectories: int
    active_trajectories: int
    cross_camera_trajectories: int
    tracks_mapped: int
    cameras: dict[str, int]


class MultiModalExtractRequest(BaseModel):
    image_path: str
    bbox: list[int] | None = Field(default=None, min_length=4, max_length=4)
    return_all: bool = False


class MultiModalExtractResponse(BaseModel):
    visual_feature: list[float]
    gait_feature: list[float] | None = None
    color_feature: list[float] | None = None
    fused_feature: list[float]
    weights: dict[str, float]
    total_dim: int


class MultiModalConfigResponse(BaseModel):
    enable_gait: bool
    enable_color: bool
    visual_dim: int
    gait_dim: int
    color_dim: int
    weights: dict[str, float]


class MultiModalWeightsRequest(BaseModel):
    visual_weight: float | None = None
    gait_weight: float | None = None
    color_weight: float | None = None


class SlidingWindowSearchRequest(BaseModel):
    feature: list[float]
    top_k: int = Field(default=10, ge=1, le=100)
    use_cache: bool = True


class SlidingWindowSearchResponse(BaseModel):
    query_timestamp: float
    results: list[SearchResultItem]
    window_size: int
    processing_time_ms: float
    cache_hit: bool


class SlidingWindowStatsResponse(BaseModel):
    window_size: int
    window_capacity: int
    index_size: int
    cache_size: int
    pending_queries: int
    real_time_enabled: bool


class HybridSearchRequest(BaseModel):
    feature: list[float]
    camera_id: str = ""
    timestamp: float = 0.0
    top_k: int = Field(default=10, ge=1, le=100)
    use_spatial_temporal: bool = True


class AsyncSearchRequest(BaseModel):
    feature: list[float]
    query_id: str
    top_k: int = Field(default=10, ge=1, le=100)


class AsyncSearchResponse(BaseModel):
    query_id: str
    status: str
    message: str


class AsyncSearchResultResponse(BaseModel):
    query_id: str
    status: str
    results: list[SearchResultItem] | None = None
    message: str
