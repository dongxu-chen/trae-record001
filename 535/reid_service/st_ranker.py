from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from typing import Any

from config import STRankerConfig, CameraPairConfig

logger = logging.getLogger(__name__)


@dataclass
class TrackRecord:
    track_id: str
    camera_id: str
    timestamp: float
    feature: list[float] | None = None
    bbox: tuple[int, int, int, int] | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class RankedResult:
    track_id: str
    camera_id: str
    timestamp: float
    visual_score: float
    spatial_score: float
    temporal_score: float
    combined_score: float
    metadata: dict[str, Any] = field(default_factory=dict)


class SpatioTemporalRanker:
    def __init__(self, config: STRankerConfig | None = None):
        self.config = config or STRankerConfig()
        self.camera_positions: dict[str, tuple[float, float]] = self.config.camera_positions.copy()
        self.camera_transition_costs: dict[tuple[str, str], float] = {}
        self.camera_pair_configs: dict[tuple[str, str], CameraPairConfig] = (
            self.config.camera_pair_configs.copy()
        )
        if self.config.camera_transition_matrix:
            self._load_transition_matrix(self.config.camera_transition_matrix)

    def set_camera_position(
        self, camera_id: str, position: tuple[float, float]
    ) -> None:
        self.camera_positions[camera_id] = position
        logger.debug(f"Set camera {camera_id} position to {position}")

    def set_camera_positions(
        self, positions: dict[str, tuple[float, float]]
    ) -> None:
        self.camera_positions.update(positions)
        logger.info(f"Set positions for {len(positions)} cameras")

    def set_transition_cost(
        self, cam_from: str, cam_to: str, cost: float
    ) -> None:
        self.camera_transition_costs[(cam_from, cam_to)] = cost
        pair_cfg = self._get_pair_config(cam_from, cam_to)
        pair_cfg.transition_cost = cost

    def set_pair_config(
        self,
        cam_from: str,
        cam_to: str,
        time_window: float | None = None,
        spatial_weight: float | None = None,
        temporal_weight: float | None = None,
        transition_cost: float | None = None,
    ) -> None:
        key = (cam_from, cam_to)
        if key not in self.camera_pair_configs:
            self.camera_pair_configs[key] = CameraPairConfig(
                time_window=self.config.default_time_window,
                spatial_weight=self.config.default_spatial_weight,
                temporal_weight=self.config.default_temporal_weight,
            )
        cfg = self.camera_pair_configs[key]
        if time_window is not None:
            cfg.time_window = time_window
        if spatial_weight is not None:
            cfg.spatial_weight = spatial_weight
        if temporal_weight is not None:
            cfg.temporal_weight = temporal_weight
        if transition_cost is not None:
            cfg.transition_cost = transition_cost
            self.camera_transition_costs[key] = transition_cost
        logger.info(
            f"Updated pair config {cam_from}->{cam_to}: "
            f"time_window={cfg.time_window}, "
            f"spatial_weight={cfg.spatial_weight}, "
            f"temporal_weight={cfg.temporal_weight}"
        )

    def _get_pair_config(self, cam_from: str, cam_to: str) -> CameraPairConfig:
        key = (cam_from, cam_to)
        if key in self.camera_pair_configs:
            return self.camera_pair_configs[key]
        return CameraPairConfig(
            time_window=self.config.default_time_window,
            spatial_weight=self.config.default_spatial_weight,
            temporal_weight=self.config.default_temporal_weight,
        )

    def _load_transition_matrix(self, matrix: dict) -> None:
        for key, value in matrix.items():
            cam_from, cam_to = key.split("->")
            cam_from = cam_from.strip()
            cam_to = cam_to.strip()
            cost = float(value)
            self.camera_transition_costs[(cam_from, cam_to)] = cost
            self.set_pair_config(cam_from, cam_to, transition_cost=cost)

    def compute_spatial_score(
        self, query_camera: str, gallery_camera: str
    ) -> float:
        if query_camera == gallery_camera:
            return 1.0

        transition_key = (query_camera, gallery_camera)
        if transition_key in self.camera_transition_costs:
            cost = self.camera_transition_costs[transition_key]
            return math.exp(-cost)

        if (
            query_camera in self.camera_positions
            and gallery_camera in self.camera_positions
        ):
            pos_q = self.camera_positions[query_camera]
            pos_g = self.camera_positions[gallery_camera]
            distance = math.sqrt(
                (pos_q[0] - pos_g[0]) ** 2 + (pos_q[1] - pos_g[1]) ** 2
            )
            return math.exp(-distance / 100.0)

        return 0.5

    def compute_temporal_score(
        self, query_time: float, gallery_time: float, time_window: float
    ) -> float:
        time_diff = abs(query_time - gallery_time)
        if time_diff > time_window:
            return 0.0
        return math.exp(-time_diff / time_window)

    def compute_combined_score(
        self,
        visual_score: float,
        spatial_score: float,
        temporal_score: float,
        spatial_weight: float,
        temporal_weight: float,
    ) -> float:
        visual_weight = self.config.visual_weight
        total_w = visual_weight + spatial_weight + temporal_weight
        if total_w <= 0:
            return visual_score
        return (
            visual_weight * visual_score
            + spatial_weight * spatial_score
            + temporal_weight * temporal_score
        ) / total_w

    def rank(
        self,
        query: TrackRecord,
        candidates: list[TrackRecord],
        visual_scores: list[float] | None = None,
        top_k: int = 10,
    ) -> list[RankedResult]:
        if not candidates:
            return []

        results = []
        for i, candidate in enumerate(candidates):
            vis_score = visual_scores[i] if visual_scores and i < len(visual_scores) else 0.0

            pair_cfg = self._get_pair_config(query.camera_id, candidate.camera_id)

            spatial_score = self.compute_spatial_score(
                query.camera_id, candidate.camera_id
            )
            temporal_score = self.compute_temporal_score(
                query.timestamp, candidate.timestamp, pair_cfg.time_window
            )
            combined = self.compute_combined_score(
                vis_score,
                spatial_score,
                temporal_score,
                pair_cfg.spatial_weight,
                pair_cfg.temporal_weight,
            )

            results.append(
                RankedResult(
                    track_id=candidate.track_id,
                    camera_id=candidate.camera_id,
                    timestamp=candidate.timestamp,
                    visual_score=vis_score,
                    spatial_score=spatial_score,
                    temporal_score=temporal_score,
                    combined_score=combined,
                    metadata=candidate.metadata,
                )
            )

        results.sort(key=lambda x: x.combined_score, reverse=True)
        return results[:top_k]

    def rank_with_camera_filter(
        self,
        query: TrackRecord,
        candidates: list[TrackRecord],
        visual_scores: list[float] | None = None,
        top_k: int = 10,
        allowed_cameras: set[str] | None = None,
        excluded_cameras: set[str] | None = None,
    ) -> list[RankedResult]:
        filtered_candidates = []
        filtered_scores = []

        for i, candidate in enumerate(candidates):
            if allowed_cameras and candidate.camera_id not in allowed_cameras:
                continue
            if excluded_cameras and candidate.camera_id in excluded_cameras:
                continue
            filtered_candidates.append(candidate)
            if visual_scores and i < len(visual_scores):
                filtered_scores.append(visual_scores[i])

        return self.rank(
            query,
            filtered_candidates,
            filtered_scores if filtered_scores else None,
            top_k,
        )

    def rank_cross_camera(
        self,
        query: TrackRecord,
        candidates: list[TrackRecord],
        visual_scores: list[float] | None = None,
        top_k: int = 10,
    ) -> list[RankedResult]:
        cross_candidates = []
        cross_scores = []

        for i, candidate in enumerate(candidates):
            if candidate.camera_id == query.camera_id:
                continue
            cross_candidates.append(candidate)
            if visual_scores and i < len(visual_scores):
                cross_scores.append(visual_scores[i])

        return self.rank(
            query,
            cross_candidates,
            cross_scores if cross_scores else None,
            top_k,
        )
