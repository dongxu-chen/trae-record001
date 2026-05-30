from __future__ import annotations

import logging
import time

import cv2
import numpy as np
from fastapi import APIRouter, File, HTTPException, UploadFile

from reid_service.gallery import GalleryManager
from reid_service.multi_modal import MultiModalFeatureExtractor
from reid_service.schemas import (
    AsyncSearchRequest,
    AsyncSearchResponse,
    AsyncSearchResultResponse,
    CameraPairConfigRequest,
    CameraPositionRequest,
    ClearResponse,
    CleanupResponse,
    DeleteResponse,
    DomainAdaptationRequest,
    DomainAdaptationResponse,
    ExtractRequest,
    ExtractResponse,
    FeatureSearchRequest,
    GalleryAddRequest,
    GalleryAddResponse,
    GalleryBatchAddRequest,
    GalleryBatchAddResponse,
    GalleryItemResponse,
    GalleryStatsResponse,
    HybridSearchRequest,
    ImageSearchRequest,
    MultiModalConfigResponse,
    MultiModalExtractRequest,
    MultiModalExtractResponse,
    MultiModalWeightsRequest,
    SaveLoadResponse,
    SearchResponse,
    SearchResultItem,
    SlidingWindowSearchRequest,
    SlidingWindowSearchResponse,
    SlidingWindowStatsResponse,
    TrajectoryListResponse,
    TrajectoryResponse,
    TrajectorySearchResponse,
    TrajectoryStatsResponse,
)
from reid_service.sliding_window import SlidingWindowEngine
from reid_service.trajectory_tracker import TrajectoryTracker

logger = logging.getLogger(__name__)
router = APIRouter()

gallery_manager: GalleryManager | None = None
trajectory_tracker: TrajectoryTracker | None = None
multi_modal_extractor: MultiModalFeatureExtractor | None = None
sliding_window_engine: SlidingWindowEngine | None = None


def set_gallery_manager(gm: GalleryManager) -> None:
    global gallery_manager
    gallery_manager = gm


def set_trajectory_tracker(tt: TrajectoryTracker) -> None:
    global trajectory_tracker
    trajectory_tracker = tt


def set_multi_modal_extractor(mm: MultiModalFeatureExtractor) -> None:
    global multi_modal_extractor
    multi_modal_extractor = mm


def set_sliding_window_engine(sw: SlidingWindowEngine) -> None:
    global sliding_window_engine
    sliding_window_engine = sw


def _get_gallery() -> GalleryManager:
    if gallery_manager is None:
        raise HTTPException(status_code=503, detail="Gallery manager not initialized")
    return gallery_manager


def _get_trajectory_tracker() -> TrajectoryTracker:
    if trajectory_tracker is None:
        raise HTTPException(status_code=503, detail="Trajectory tracker not initialized")
    return trajectory_tracker


def _get_multi_modal() -> MultiModalFeatureExtractor:
    if multi_modal_extractor is None:
        raise HTTPException(status_code=503, detail="Multi-modal extractor not initialized")
    return multi_modal_extractor


def _get_sliding_window() -> SlidingWindowEngine:
    if sliding_window_engine is None:
        raise HTTPException(status_code=503, detail="Sliding window engine not initialized")
    return sliding_window_engine


@router.post("/extract", response_model=ExtractResponse)
async def extract_feature(req: ExtractRequest):
    gm = _get_gallery()
    image = cv2.imread(req.image_path)
    if image is None:
        raise HTTPException(status_code=400, detail=f"Cannot read image: {req.image_path}")

    from reid_service.feature_extractor import ReidFeatureExtractor

    extractor: ReidFeatureExtractor = getattr(gm, "_feature_extractor", None)  # type: ignore
    if extractor is None:
        raise HTTPException(status_code=503, detail="Feature extractor not configured")

    bbox = tuple(req.bbox) if req.bbox else None
    feature = extractor.extract_from_video_frame(image, bbox)
    return ExtractResponse(feature=feature.tolist(), dimension=len(feature))


@router.post("/extract_upload", response_model=ExtractResponse)
async def extract_feature_upload(file: UploadFile = File(...)):
    gm = _get_gallery()
    contents = await file.read()
    nparr = np.frombuffer(contents, np.uint8)
    image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if image is None:
        raise HTTPException(status_code=400, detail="Cannot decode uploaded image")

    from reid_service.feature_extractor import ReidFeatureExtractor

    extractor: ReidFeatureExtractor = getattr(gm, "_feature_extractor", None)  # type: ignore
    if extractor is None:
        raise HTTPException(status_code=503, detail="Feature extractor not configured")

    feature = extractor.extract(image)
    return ExtractResponse(feature=feature.tolist(), dimension=len(feature))


@router.post("/domain_adapt/adapt", response_model=DomainAdaptationResponse)
async def adapt_to_target_domain(
    file: UploadFile = File(...),
    method: str = "feature",
):
    gm = _get_gallery()
    extractor = getattr(gm, "_feature_extractor", None)
    if extractor is None:
        raise HTTPException(status_code=503, detail="Feature extractor not configured")

    contents = await file.read()
    nparr = np.frombuffer(contents, np.uint8)
    image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if image is None:
        raise HTTPException(status_code=400, detail="Cannot decode uploaded image")

    result = extractor.adapt_to_target_domain([image], method=method)
    return DomainAdaptationResponse(
        success=result.success,
        epochs_trained=result.epochs_trained,
        final_loss=result.final_loss,
        message=result.message,
        is_adapted=extractor.domain_adapter.is_adapted if extractor.domain_adapter else False,
    )


@router.post("/domain_adapt/incremental", response_model=DomainAdaptationResponse)
async def incremental_adaptation(
    file: UploadFile = File(...),
    adaptation_strength: float = 0.1,
):
    gm = _get_gallery()
    extractor = getattr(gm, "_feature_extractor", None)
    if extractor is None:
        raise HTTPException(status_code=503, detail="Feature extractor not configured")

    contents = await file.read()
    nparr = np.frombuffer(contents, np.uint8)
    image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if image is None:
        raise HTTPException(status_code=400, detail="Cannot decode uploaded image")

    extractor.incremental_adapt([image], adaptation_strength)
    is_adapted = extractor.domain_adapter.is_adapted if extractor.domain_adapter else False
    return DomainAdaptationResponse(
        success=True,
        epochs_trained=0,
        final_loss=0.0,
        message="Incremental adaptation applied",
        is_adapted=is_adapted,
    )


@router.post("/domain_adapt/reset", response_model=DomainAdaptationResponse)
async def reset_adaptation():
    gm = _get_gallery()
    extractor = getattr(gm, "_feature_extractor", None)
    if extractor is None:
        raise HTTPException(status_code=503, detail="Feature extractor not configured")

    extractor.reset_adaptation()
    return DomainAdaptationResponse(
        success=True,
        epochs_trained=0,
        final_loss=0.0,
        message="Domain adaptation reset",
        is_adapted=False,
    )


@router.post("/gallery/add", response_model=GalleryAddResponse)
async def gallery_add(req: GalleryAddRequest):
    gm = _get_gallery()
    extractor = getattr(gm, "_feature_extractor", None)
    if extractor is None:
        raise HTTPException(status_code=503, detail="Feature extractor not configured")

    if req.image_path:
        image = cv2.imread(req.image_path)
        if image is None:
            raise HTTPException(
                status_code=400, detail=f"Cannot read image: {req.image_path}"
            )
        bbox = tuple(req.bbox) if req.bbox else None
        feature = extractor.extract_from_video_frame(image, bbox)
    else:
        raise HTTPException(status_code=400, detail="image_path is required")

    item = gm.add(
        feature=feature,
        track_id=req.track_id,
        camera_id=req.camera_id,
        timestamp=req.timestamp,
        bbox=req.bbox,
        image_path=req.image_path,
        metadata=req.metadata,
    )
    return GalleryAddResponse(
        item_id=item.item_id,
        track_id=item.track_id,
        camera_id=item.camera_id,
        timestamp=item.timestamp,
    )


@router.post("/gallery/add_with_feature", response_model=GalleryAddResponse)
async def gallery_add_with_feature(
    track_id: str,
    camera_id: str,
    timestamp: float,
    feature: list[float],
    bbox: list[int] | None = None,
    image_path: str | None = None,
):
    gm = _get_gallery()
    feature_arr = np.array(feature, dtype=np.float32)
    item = gm.add(
        feature=feature_arr,
        track_id=track_id,
        camera_id=camera_id,
        timestamp=timestamp,
        bbox=bbox,
        image_path=image_path,
    )
    return GalleryAddResponse(
        item_id=item.item_id,
        track_id=item.track_id,
        camera_id=item.camera_id,
        timestamp=item.timestamp,
    )


@router.post("/gallery/add_image", response_model=GalleryAddResponse)
async def gallery_add_image(
    file: UploadFile = File(...),
    track_id: str = "",
    camera_id: str = "",
    timestamp: float = 0.0,
    bbox: str | None = None,
):
    gm = _get_gallery()
    extractor = getattr(gm, "_feature_extractor", None)
    if extractor is None:
        raise HTTPException(status_code=503, detail="Feature extractor not configured")

    contents = await file.read()
    nparr = np.frombuffer(contents, np.uint8)
    image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if image is None:
        raise HTTPException(status_code=400, detail="Cannot decode uploaded image")

    parsed_bbox = None
    if bbox:
        parsed_bbox = [int(x) for x in bbox.split(",")]

    feature = extractor.extract_from_video_frame(
        image, tuple(parsed_bbox) if parsed_bbox else None
    )

    item = gm.add(
        feature=feature,
        track_id=track_id,
        camera_id=camera_id,
        timestamp=timestamp,
        bbox=parsed_bbox,
    )
    return GalleryAddResponse(
        item_id=item.item_id,
        track_id=item.track_id,
        camera_id=item.camera_id,
        timestamp=item.timestamp,
    )


@router.delete("/gallery/{item_id}", response_model=DeleteResponse)
async def gallery_remove(item_id: str):
    gm = _get_gallery()
    success = gm.remove(item_id)
    if not success:
        raise HTTPException(status_code=404, detail=f"Item {item_id} not found")
    return DeleteResponse(success=True, message=f"Removed item {item_id}")


@router.get("/gallery/{item_id}", response_model=GalleryItemResponse)
async def gallery_get(item_id: str, touch: bool = True):
    gm = _get_gallery()
    item = gm.get(item_id, touch=touch)
    if item is None:
        raise HTTPException(status_code=404, detail=f"Item {item_id} not found")
    return GalleryItemResponse(
        item_id=item.item_id,
        track_id=item.track_id,
        camera_id=item.camera_id,
        timestamp=item.timestamp,
        bbox=item.bbox,
        image_path=item.image_path,
        metadata=item.metadata,
    )


@router.get("/gallery/stats", response_model=GalleryStatsResponse)
async def gallery_stats():
    gm = _get_gallery()
    stats = gm.get_stats()
    return GalleryStatsResponse(**stats)


@router.post("/gallery/clear", response_model=ClearResponse)
async def gallery_clear():
    gm = _get_gallery()
    gm.clear()
    return ClearResponse(success=True, message="Gallery cleared")


@router.post("/gallery/cleanup", response_model=CleanupResponse)
async def gallery_cleanup():
    gm = _get_gallery()
    results = gm.perform_cleanup()
    return CleanupResponse(
        success=True,
        expired_removed=results["expired_removed"],
        lru_evicted=results["lru_evicted"],
        message=f"Cleanup complete: expired={results['expired_removed']}, evicted={results['lru_evicted']}",
    )


@router.post("/search/feature", response_model=SearchResponse)
async def search_by_feature(req: FeatureSearchRequest):
    gm = _get_gallery()
    feature = np.array(req.feature, dtype=np.float32)

    allowed = set(req.allowed_cameras) if req.allowed_cameras else None
    excluded = set(req.excluded_cameras) if req.excluded_cameras else None

    results = gm.query(
        query_feature=feature,
        query_camera_id=req.camera_id,
        query_timestamp=req.timestamp,
        top_k=req.top_k,
        use_spatial_temporal=req.use_spatial_temporal,
        cross_camera_only=req.cross_camera_only,
        allowed_cameras=allowed,
        excluded_cameras=excluded,
    )

    return SearchResponse(
        results=[
            SearchResultItem(
                item_id=r.item_id,
                track_id=r.track_id,
                camera_id=r.camera_id,
                timestamp=r.timestamp,
                visual_score=r.visual_score,
                spatial_score=r.spatial_score,
                temporal_score=r.temporal_score,
                combined_score=r.combined_score,
                metadata=r.metadata,
            )
            for r in results
        ],
        query_camera=req.camera_id,
        query_timestamp=req.timestamp,
        total=len(results),
    )


@router.post("/search/image", response_model=SearchResponse)
async def search_by_image(
    file: UploadFile = File(...),
    camera_id: str = "",
    timestamp: float = 0.0,
    bbox: str | None = None,
    top_k: int = 10,
    use_spatial_temporal: bool = True,
    cross_camera_only: bool = False,
):
    gm = _get_gallery()
    extractor = getattr(gm, "_feature_extractor", None)
    if extractor is None:
        raise HTTPException(status_code=503, detail="Feature extractor not configured")

    contents = await file.read()
    nparr = np.frombuffer(contents, np.uint8)
    image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if image is None:
        raise HTTPException(status_code=400, detail="Cannot decode uploaded image")

    parsed_bbox = None
    if bbox:
        parsed_bbox = [int(x) for x in bbox.split(",")]

    feature = extractor.extract_from_video_frame(
        image, tuple(parsed_bbox) if parsed_bbox else None
    )

    results = gm.query(
        query_feature=feature,
        query_camera_id=camera_id,
        query_timestamp=timestamp,
        top_k=top_k,
        use_spatial_temporal=use_spatial_temporal,
        cross_camera_only=cross_camera_only,
    )

    return SearchResponse(
        results=[
            SearchResultItem(
                item_id=r.item_id,
                track_id=r.track_id,
                camera_id=r.camera_id,
                timestamp=r.timestamp,
                visual_score=r.visual_score,
                spatial_score=r.spatial_score,
                temporal_score=r.temporal_score,
                combined_score=r.combined_score,
                metadata=r.metadata,
            )
            for r in results
        ],
        query_camera=camera_id,
        query_timestamp=timestamp,
        total=len(results),
    )


@router.post("/camera/positions", response_model=SaveLoadResponse)
async def set_camera_positions(req: CameraPositionRequest):
    gm = _get_gallery()
    positions = {k: tuple(v) for k, v in req.positions.items()}
    gm.ranker.set_camera_positions(positions)
    return SaveLoadResponse(
        success=True,
        message=f"Set positions for {len(positions)} cameras",
    )


@router.post("/camera/pair_config", response_model=SaveLoadResponse)
async def set_camera_pair_config(req: CameraPairConfigRequest):
    gm = _get_gallery()
    gm.ranker.set_pair_config(
        cam_from=req.cam_from,
        cam_to=req.cam_to,
        time_window=req.time_window,
        spatial_weight=req.spatial_weight,
        temporal_weight=req.temporal_weight,
        transition_cost=req.transition_cost,
    )
    return SaveLoadResponse(
        success=True,
        message=f"Updated pair config: {req.cam_from} -> {req.cam_to}",
    )


@router.post("/gallery/save", response_model=SaveLoadResponse)
async def gallery_save():
    gm = _get_gallery()
    gm.save()
    return SaveLoadResponse(success=True, message="Gallery saved")


@router.post("/gallery/load", response_model=SaveLoadResponse)
async def gallery_load():
    gm = _get_gallery()
    gm.load()
    return SaveLoadResponse(success=True, message="Gallery loaded")


@router.get("/trajectory/{trajectory_id}", response_model=TrajectoryResponse)
async def get_trajectory(trajectory_id: str):
    tt = _get_trajectory_tracker()
    traj = tt.get_trajectory(trajectory_id)
    if traj is None:
        raise HTTPException(status_code=404, detail=f"Trajectory {trajectory_id} not found")

    return TrajectoryResponse(
        trajectory_id=traj.trajectory_id,
        track_id=traj.track_id,
        points=[
            TrajectoryPointResponse(
                item_id=p.item_id,
                camera_id=p.camera_id,
                timestamp=p.timestamp,
                bbox=p.bbox,
                spatial_score=p.spatial_score,
                temporal_score=p.temporal_score,
                visual_score=p.visual_score,
                combined_score=p.combined_score,
                metadata=p.metadata,
            )
            for p in traj.points
        ],
        created_at=traj.created_at,
        last_updated_at=traj.last_updated_at,
        is_active=traj.is_active,
        duration=traj.duration(),
        cameras=traj.get_cameras(),
        num_points=len(traj.points),
        merged_from=traj.merged_from,
    )


@router.get("/trajectory/track/{track_id}", response_model=TrajectoryResponse)
async def get_trajectory_by_track(track_id: str):
    tt = _get_trajectory_tracker()
    traj = tt.get_trajectory_by_track(track_id)
    if traj is None:
        raise HTTPException(status_code=404, detail=f"Trajectory for track {track_id} not found")

    return TrajectoryResponse(
        trajectory_id=traj.trajectory_id,
        track_id=traj.track_id,
        points=[
            TrajectoryPointResponse(
                item_id=p.item_id,
                camera_id=p.camera_id,
                timestamp=p.timestamp,
                bbox=p.bbox,
                spatial_score=p.spatial_score,
                temporal_score=p.temporal_score,
                visual_score=p.visual_score,
                combined_score=p.combined_score,
                metadata=p.metadata,
            )
            for p in traj.points
        ],
        created_at=traj.created_at,
        last_updated_at=traj.last_updated_at,
        is_active=traj.is_active,
        duration=traj.duration(),
        cameras=traj.get_cameras(),
        num_points=len(traj.points),
        merged_from=traj.merged_from,
    )


@router.get("/trajectory/list", response_model=TrajectoryListResponse)
async def list_trajectories(
    active_only: bool = True,
    cross_camera_only: bool = False,
    min_points: int = 1,
    limit: int = 100,
):
    tt = _get_trajectory_tracker()
    trajectories = tt.get_active_trajectories(
        min_points=min_points, cross_camera_only=cross_camera_only
    )
    if not active_only:
        from reid_service.trajectory_tracker import Trajectory
        all_traj = list(tt._trajectories.values())
        trajectories = [t for t in all_traj if len(t.points) >= min_points]
        if cross_camera_only:
            trajectories = [t for t in trajectories if len(t.get_cameras()) > 1]

    trajectories = trajectories[:limit]
    return TrajectoryListResponse(
        trajectories=[
            TrajectoryResponse(
                trajectory_id=t.trajectory_id,
                track_id=t.track_id,
                points=[
                    TrajectoryPointResponse(
                        item_id=p.item_id,
                        camera_id=p.camera_id,
                        timestamp=p.timestamp,
                        bbox=p.bbox,
                        spatial_score=p.spatial_score,
                        temporal_score=p.temporal_score,
                        visual_score=p.visual_score,
                        combined_score=p.combined_score,
                        metadata=p.metadata,
                    )
                    for p in t.points
                ],
                created_at=t.created_at,
                last_updated_at=t.last_updated_at,
                is_active=t.is_active,
                duration=t.duration(),
                cameras=t.get_cameras(),
                num_points=len(t.points),
                merged_from=t.merged_from,
            )
            for t in trajectories
        ],
        total=len(trajectories),
    )


@router.post("/trajectory/search", response_model=list[TrajectorySearchResponse])
async def search_trajectories(
    feature: list[float],
    camera_id: str = "",
    timestamp: float = 0.0,
    top_k: int = 10,
    cross_camera_only: bool = False,
):
    tt = _get_trajectory_tracker()
    feat = np.array(feature, dtype=np.float32)
    results = tt.search_trajectories(
        feature=feat,
        camera_id=camera_id,
        timestamp=timestamp,
        top_k=top_k,
        cross_camera_only=cross_camera_only,
    )
    return [
        TrajectorySearchResponse(
            trajectory_id=t.trajectory_id,
            track_id=t.track_id,
            score=round(score, 6),
            num_points=len(t.points),
            cameras=t.get_cameras(),
        )
        for t, score in results
    ]


@router.get("/trajectory/stats", response_model=TrajectoryStatsResponse)
async def trajectory_stats():
    tt = _get_trajectory_tracker()
    stats = tt.get_stats()
    return TrajectoryStatsResponse(**stats)


@router.post("/multimodal/extract", response_model=MultiModalExtractResponse)
async def extract_multimodal(req: MultiModalExtractRequest):
    mm = _get_multi_modal()
    image = cv2.imread(req.image_path)
    if image is None:
        raise HTTPException(status_code=400, detail=f"Cannot read image: {req.image_path}")

    bbox = tuple(req.bbox) if req.bbox else None
    result = mm.extract(image, bbox=bbox, return_all=True)

    if isinstance(result, np.ndarray):
        fused = result.tolist()
        visual = result.tolist()
        gait = None
        color = None
        weights = {}
    else:
        fused = result.fused_feature.tolist() if result.fused_feature is not None else result.visual_feature.tolist()
        visual = result.visual_feature.tolist()
        gait = result.gait_feature.tolist() if result.gait_feature is not None else None
        color = result.color_feature.tolist() if result.color_feature is not None else None
        weights = result.weights

    total_dim = len(fused)
    return MultiModalExtractResponse(
        visual_feature=visual,
        gait_feature=gait,
        color_feature=color,
        fused_feature=fused,
        weights=weights,
        total_dim=total_dim,
    )


@router.post("/multimodal/extract_upload", response_model=MultiModalExtractResponse)
async def extract_multimodal_upload(
    file: UploadFile = File(...),
    bbox: str | None = None,
    return_all: bool = False,
):
    mm = _get_multi_modal()
    contents = await file.read()
    nparr = np.frombuffer(contents, np.uint8)
    image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if image is None:
        raise HTTPException(status_code=400, detail="Cannot decode uploaded image")

    parsed_bbox = None
    if bbox:
        parsed_bbox = tuple([int(x) for x in bbox.split(",")])

    result = mm.extract(image, bbox=parsed_bbox, return_all=True)

    if isinstance(result, np.ndarray):
        fused = result.tolist()
        visual = result.tolist()
        gait = None
        color = None
        weights = {}
    else:
        fused = result.fused_feature.tolist() if result.fused_feature is not None else result.visual_feature.tolist()
        visual = result.visual_feature.tolist()
        gait = result.gait_feature.tolist() if result.gait_feature is not None else None
        color = result.color_feature.tolist() if result.color_feature is not None else None
        weights = result.weights

    total_dim = len(fused)
    return MultiModalExtractResponse(
        visual_feature=visual,
        gait_feature=gait,
        color_feature=color,
        fused_feature=fused,
        weights=weights,
        total_dim=total_dim,
    )


@router.get("/multimodal/config", response_model=MultiModalConfigResponse)
async def get_multimodal_config():
    mm = _get_multi_modal()
    cfg = mm.get_config()
    return MultiModalConfigResponse(**cfg)


@router.post("/multimodal/weights", response_model=MultiModalConfigResponse)
async def set_multimodal_weights(req: MultiModalWeightsRequest):
    mm = _get_multi_modal()
    mm.set_weights(
        visual_weight=req.visual_weight,
        gait_weight=req.gait_weight,
        color_weight=req.color_weight,
    )
    cfg = mm.get_config()
    return MultiModalConfigResponse(**cfg)


@router.post("/sliding_window/search", response_model=SlidingWindowSearchResponse)
async def sliding_window_search(req: SlidingWindowSearchRequest):
    sw = _get_sliding_window()
    feat = np.array(req.feature, dtype=np.float32)
    result = sw.search(feat, top_k=req.top_k, use_cache=req.use_cache)

    gm = _get_gallery()
    results_with_meta = []
    for item_id, score in result.results:
        item = gm.get(item_id, touch=False)
        if item:
            results_with_meta.append(
                SearchResultItem(
                    item_id=item.item_id,
                    track_id=item.track_id,
                    camera_id=item.camera_id,
                    timestamp=item.timestamp,
                    visual_score=score,
                    spatial_score=0.0,
                    temporal_score=0.0,
                    combined_score=score,
                    metadata=item.metadata,
                )
            )

    return SlidingWindowSearchResponse(
        query_timestamp=result.query_timestamp,
        results=results_with_meta,
        window_size=result.window_size,
        processing_time_ms=result.processing_time_ms,
        cache_hit=result.cache_hit,
    )


@router.post("/sliding_window/hybrid_search", response_model=SearchResponse)
async def hybrid_search(req: HybridSearchRequest):
    sw = _get_sliding_window()
    gm = _get_gallery()
    feat = np.array(req.feature, dtype=np.float32)

    results = sw.hybrid_search(
        query_feature=feat,
        query_camera_id=req.camera_id,
        query_timestamp=req.timestamp,
        top_k=req.top_k,
        use_spatial_temporal=req.use_spatial_temporal,
    )

    return SearchResponse(
        results=[
            SearchResultItem(
                item_id=r.item_id,
                track_id=r.track_id,
                camera_id=r.camera_id,
                timestamp=r.timestamp,
                visual_score=r.visual_score,
                spatial_score=r.spatial_score,
                temporal_score=r.temporal_score,
                combined_score=r.combined_score,
                metadata=r.metadata,
            )
            for r in results
        ],
        query_camera=req.camera_id,
        query_timestamp=req.timestamp,
        total=len(results),
    )


@router.post("/sliding_window/async_search", response_model=AsyncSearchResponse)
async def async_search(req: AsyncSearchRequest):
    sw = _get_sliding_window()
    feat = np.array(req.feature, dtype=np.float32)
    sw.async_search(feat, query_id=req.query_id, top_k=req.top_k)
    return AsyncSearchResponse(
        query_id=req.query_id,
        status="pending",
        message="Query submitted for async processing",
    )


@router.get("/sliding_window/async_result/{query_id}", response_model=AsyncSearchResultResponse)
async def get_async_result(query_id: str):
    sw = _get_sliding_window()
    result = sw.get_async_result(query_id)

    if result is None:
        return AsyncSearchResultResponse(
            query_id=query_id,
            status="pending",
            message="Result not ready yet",
        )

    gm = _get_gallery()
    results_with_meta = []
    for item_id, score in result.results:
        item = gm.get(item_id, touch=False)
        if item:
            results_with_meta.append(
                SearchResultItem(
                    item_id=item.item_id,
                    track_id=item.track_id,
                    camera_id=item.camera_id,
                    timestamp=item.timestamp,
                    visual_score=score,
                    spatial_score=0.0,
                    temporal_score=0.0,
                    combined_score=score,
                    metadata=item.metadata,
                )
            )

    return AsyncSearchResultResponse(
        query_id=query_id,
        status="completed",
        results=results_with_meta,
        message="Query completed",
    )


@router.get("/sliding_window/stats", response_model=SlidingWindowStatsResponse)
async def sliding_window_stats():
    sw = _get_sliding_window()
    stats = sw.get_stats()
    return SlidingWindowStatsResponse(**stats)


@router.get("/health")
async def health():
    gm = _get_gallery()
    tt = _get_trajectory_tracker()
    sw = _get_sliding_window()

    sw_stats = sw.get_stats()
    tt_stats = tt.get_stats()

    return {
        "status": "healthy",
        "gallery": {
            "size": gm.size(),
            "index_size": gm.search_engine.size(),
        },
        "trajectory": tt_stats,
        "sliding_window": sw_stats,
    }
