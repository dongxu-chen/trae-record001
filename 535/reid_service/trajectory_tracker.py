from __future__ import annotations

import logging
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from typing import Any

import numpy as np

from config import TrajectoryConfig
from reid_service.gallery import GalleryItem, SearchResult
from reid_service.st_ranker import SpatioTemporalRanker

logger = logging.getLogger(__name__)


@dataclass
class TrajectoryPoint:
    item_id: str
    camera_id: str
    timestamp: float
    bbox: list[int] | None = None
    feature: np.ndarray | None = None
    spatial_score: float = 0.0
    temporal_score: float = 0.0
    visual_score: float = 0.0
    combined_score: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "item_id": self.item_id,
            "camera_id": self.camera_id,
            "timestamp": self.timestamp,
            "bbox": self.bbox,
            "spatial_score": round(self.spatial_score, 6),
            "temporal_score": round(self.temporal_score, 6),
            "visual_score": round(self.visual_score, 6),
            "combined_score": round(self.combined_score, 6),
            "metadata": self.metadata,
        }


@dataclass
class Trajectory:
    trajectory_id: str
    track_id: str
    points: list[TrajectoryPoint] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    last_updated_at: float = field(default_factory=time.time)
    is_active: bool = True
    merged_from: list[str] = field(default_factory=list)

    def add_point(self, point: TrajectoryPoint) -> None:
        self.points.append(point)
        self.last_updated_at = time.time()
        self.points.sort(key=lambda p: p.timestamp)

    def get_latest_point(self) -> TrajectoryPoint | None:
        return self.points[-1] if self.points else None

    def get_earliest_point(self) -> TrajectoryPoint | None:
        return self.points[0] if self.points else None

    def get_cameras(self) -> list[str]:
        return sorted({p.camera_id for p in self.points})

    def duration(self) -> float:
        if not self.points:
            return 0.0
        return self.points[-1].timestamp - self.points[0].timestamp

    def to_dict(self) -> dict:
        return {
            "trajectory_id": self.trajectory_id,
            "track_id": self.track_id,
            "points": [p.to_dict() for p in self.points],
            "created_at": self.created_at,
            "last_updated_at": self.last_updated_at,
            "is_active": self.is_active,
            "duration": self.duration(),
            "cameras": self.get_cameras(),
            "num_points": len(self.points),
            "merged_from": self.merged_from,
        }


class TrajectoryTracker:
    def __init__(
        self,
        ranker: SpatioTemporalRanker,
        config: TrajectoryConfig | None = None,
    ):
        self.config = config or TrajectoryConfig()
        self.ranker = ranker
        self._trajectories: dict[str, Trajectory] = {}
        self._track_to_trajectory: dict[str, str] = {}
        self._camera_trajectories: dict[str, set[str]] = defaultdict(set)
        self._next_trajectory_id: int = 0
        self._recent_gallery_items: deque[GalleryItem] = deque(maxlen=1000)

        logger.info(
            f"TrajectoryTracker initialized: cross_camera={self.config.enable_cross_camera_tracking}, "
            f"max_age={self.config.max_trajectory_age}s"
        )

    def _generate_trajectory_id(self) -> str:
        self._next_trajectory_id += 1
        return f"traj_{self._next_trajectory_id:08d}"

    def _get_next_cameras(self, camera_id: str) -> set[str]:
        if not self.config.camera_graph:
            return set()
        return set(self.config.camera_graph.get(camera_id, []))

    def _predict_next_appearance(
        self, trajectory: Trajectory, current_time: float
    ) -> dict[str, tuple[float, float]]:
        predictions = {}
        latest = trajectory.get_latest_point()
        if not latest:
            return predictions

        next_cameras = self._get_next_cameras(latest.camera_id)
        if not next_cameras:
            return predictions

        time_since_last = current_time - latest.timestamp

        for cam in next_cameras:
            pair_cfg = self.ranker.config.get_pair_config(latest.camera_id, cam)
            expected_time = latest.timestamp + pair_cfg.time_window * 0.5
            time_deviation = abs(current_time - expected_time)
            temporal_score = np.exp(-time_deviation / pair_cfg.time_window)

            spatial_score = self.ranker.compute_spatial_score(latest.camera_id, cam)

            predictions[cam] = (temporal_score, spatial_score)

        return predictions

    def add_gallery_item(
        self,
        item: GalleryItem,
        feature: np.ndarray,
        search_results: list[SearchResult],
    ) -> str:
        self._recent_gallery_items.append(item)

        matched_trajectory_id = self._match_to_trajectory(
            item, feature, search_results
        )

        if matched_trajectory_id:
            trajectory = self._trajectories[matched_trajectory_id]
            point = TrajectoryPoint(
                item_id=item.item_id,
                camera_id=item.camera_id,
                timestamp=item.timestamp,
                bbox=item.bbox,
                feature=feature,
                metadata=item.metadata,
            )
            trajectory.add_point(point)
            self._camera_trajectories[item.camera_id].add(trajectory.trajectory_id)

            if item.track_id and item.track_id != trajectory.track_id:
                self._track_to_trajectory[item.track_id] = trajectory.trajectory_id

            logger.info(
                f"Added point to trajectory {trajectory.trajectory_id}: "
                f"cam={item.camera_id}, t={item.timestamp}, total_points={len(trajectory.points)}"
            )
        else:
            trajectory_id = self._create_new_trajectory(item, feature)
            matched_trajectory_id = trajectory_id

        self._try_merge_trajectories(matched_trajectory_id)
        self._cleanup_old_trajectories()

        return matched_trajectory_id

    def _match_to_trajectory(
        self,
        item: GalleryItem,
        feature: np.ndarray,
        search_results: list[SearchResult],
    ) -> str | None:
        if not search_results:
            return None

        current_time = item.timestamp

        candidate_trajectories = []

        for result in search_results:
            traj_id = self._track_to_trajectory.get(result.track_id)
            if traj_id and traj_id in self._trajectories:
                traj = self._trajectories[traj_id]
                if not traj.is_active:
                    continue

                latest_point = traj.get_latest_point()
                if not latest_point:
                    continue

                time_gap = item.timestamp - latest_point.timestamp
                if time_gap > self.config.max_track_gap:
                    continue

                pair_cfg = self.ranker.config.get_pair_config(
                    latest_point.camera_id, item.camera_id
                )
                spatial_score = self.ranker.compute_spatial_score(
                    latest_point.camera_id, item.camera_id
                )
                temporal_score = self.ranker.compute_temporal_score(
                    latest_point.timestamp, item.timestamp, pair_cfg.time_window
                )

                pair_weight = spatial_score * pair_cfg.spatial_weight + temporal_score * pair_cfg.temporal_weight
                combined = (
                    pair_cfg.spatial_weight * spatial_score
                    + pair_cfg.temporal_weight * temporal_score
                    + self.ranker.config.visual_weight * result.visual_score
                ) / (
                    pair_cfg.spatial_weight
                    + pair_cfg.temporal_weight
                    + self.ranker.config.visual_weight
                )

                candidate_trajectories.append((traj_id, combined, result))

        if not candidate_trajectories:
            return None

        candidate_trajectories.sort(key=lambda x: x[1], reverse=True)
        best_traj_id, best_score, best_result = candidate_trajectories[0]

        if best_score < self.config.trajectory_merge_threshold:
            return None

        best_trajectory = self._trajectories[best_traj_id]
        for point in best_trajectory.points:
            if point.item_id == best_result.item_id:
                point.visual_score = best_result.visual_score
                point.spatial_score = best_result.spatial_score
                point.temporal_score = best_result.temporal_score
                point.combined_score = best_result.combined_score
                break

        return best_traj_id

    def _create_new_trajectory(
        self, item: GalleryItem, feature: np.ndarray
    ) -> str:
        trajectory_id = self._generate_trajectory_id()
        point = TrajectoryPoint(
            item_id=item.item_id,
            camera_id=item.camera_id,
            timestamp=item.timestamp,
            bbox=item.bbox,
            feature=feature,
            metadata=item.metadata,
        )
        trajectory = Trajectory(
            trajectory_id=trajectory_id,
            track_id=item.track_id or trajectory_id,
            points=[point],
        )
        self._trajectories[trajectory_id] = trajectory
        self._track_to_trajectory[item.track_id or trajectory_id] = trajectory_id
        self._camera_trajectories[item.camera_id].add(trajectory_id)

        logger.info(
            f"Created new trajectory {trajectory_id}: track={trajectory.track_id}, "
            f"cam={item.camera_id}, t={item.timestamp}"
        )
        return trajectory_id

    def _try_merge_trajectories(self, current_trajectory_id: str) -> None:
        current_traj = self._trajectories.get(current_trajectory_id)
        if not current_traj or len(current_traj.points) < self.config.min_track_length:
            return

        current_cameras = set(current_traj.get_cameras())
        current_track_id = current_traj.track_id

        candidates = []
        for traj_id, traj in self._trajectories.items():
            if traj_id == current_trajectory_id:
                continue
            if not traj.is_active:
                continue
            if traj.track_id != current_track_id:
                continue
            if current_cameras.intersection(traj.get_cameras()):
                candidates.append(traj_id)

        for traj_id in candidates:
            traj = self._trajectories[traj_id]
            latest_curr = current_traj.get_latest_point()
            earliest_other = traj.get_earliest_point()

            if (
                latest_curr
                and earliest_other
                and latest_curr.timestamp <= earliest_other.timestamp
            ):
                time_gap = earliest_other.timestamp - latest_curr.timestamp
                if time_gap <= self.config.max_track_gap:
                    current_traj.points.extend(traj.points)
                    current_traj.points.sort(key=lambda p: p.timestamp)
                    current_traj.merged_from.append(traj_id)
                    traj.is_active = False

                    for point in traj.points:
                        self._track_to_trajectory[
                            current_traj.track_id
                        ] = current_trajectory_id

                    logger.info(
                        f"Merged trajectory {traj_id} into {current_trajectory_id}: "
                        f"total_points={len(current_traj.points)}"
                    )

    def _cleanup_old_trajectories(self) -> int:
        current_time = time.time()
        removed = 0

        for traj_id in list(self._trajectories.keys()):
            traj = self._trajectories[traj_id]
            age = current_time - traj.last_updated_at
            if age > self.config.max_trajectory_age:
                traj.is_active = False
                if age > self.config.max_trajectory_age * 2:
                    self._trajectories.pop(traj_id, None)
                    for cam, traj_set in self._camera_trajectories.items():
                        traj_set.discard(traj_id)
                    removed += 1

        if removed > 0:
            logger.info(f"Cleaned up {removed} old trajectories")
        return removed

    def get_trajectory(self, trajectory_id: str) -> Trajectory | None:
        return self._trajectories.get(trajectory_id)

    def get_trajectory_by_track(self, track_id: str) -> Trajectory | None:
        traj_id = self._track_to_trajectory.get(track_id)
        return self._trajectories.get(traj_id) if traj_id else None

    def get_trajectories_by_camera(
        self, camera_id: str, active_only: bool = True
    ) -> list[Trajectory]:
        traj_ids = self._camera_trajectories.get(camera_id, set())
        trajectories = [
            self._trajectories[tid]
            for tid in traj_ids
            if tid in self._trajectories
            and (not active_only or self._trajectories[tid].is_active)
        ]
        return sorted(trajectories, key=lambda t: t.last_updated_at, reverse=True)

    def get_active_trajectories(
        self, min_points: int = 1, cross_camera_only: bool = False
    ) -> list[Trajectory]:
        trajectories = [
            traj
            for traj in self._trajectories.values()
            if traj.is_active and len(traj.points) >= min_points
        ]
        if cross_camera_only:
            trajectories = [
                traj for traj in trajectories if len(traj.get_cameras()) > 1
            ]
        return sorted(trajectories, key=lambda t: t.last_updated_at, reverse=True)

    def get_stats(self) -> dict[str, Any]:
        active = [t for t in self._trajectories.values() if t.is_active]
        cross_cam = [t for t in active if len(t.get_cameras()) > 1]
        return {
            "total_trajectories": len(self._trajectories),
            "active_trajectories": len(active),
            "cross_camera_trajectories": len(cross_cam),
            "tracks_mapped": len(self._track_to_trajectory),
            "cameras": {
                cam: len(tids) for cam, tids in self._camera_trajectories.items()
            },
        }

    def search_trajectories(
        self,
        feature: np.ndarray,
        camera_id: str,
        timestamp: float,
        top_k: int = 10,
        cross_camera_only: bool = False,
    ) -> list[tuple[Trajectory, float]]:
        trajectories = self.get_active_trajectories(
            min_points=self.config.min_track_length,
            cross_camera_only=cross_camera_only,
        )
        if not trajectories:
            return []

        scores = []
        for traj in trajectories:
            avg_score = 0.0
            count = 0
            for point in traj.points:
                if point.feature is not None:
                    sim = np.dot(feature, point.feature)
                    pair_cfg = self.ranker.config.get_pair_config(
                        point.camera_id, camera_id
                    )
                    spatial_score = self.ranker.compute_spatial_score(
                        point.camera_id, camera_id
                    )
                    temporal_score = self.ranker.compute_temporal_score(
                        point.timestamp, timestamp, pair_cfg.time_window
                    )
                    combined = (
                        self.ranker.config.visual_weight * sim
                        + pair_cfg.spatial_weight * spatial_score
                        + pair_cfg.temporal_weight * temporal_score
                    ) / (
                        self.ranker.config.visual_weight
                        + pair_cfg.spatial_weight
                        + pair_cfg.temporal_weight
                    )
                    avg_score += combined
                    count += 1
            if count > 0:
                scores.append((traj, avg_score / count))

        scores.sort(key=lambda x: x[1], reverse=True)
        return scores[:top_k]

    def clear(self) -> None:
        self._trajectories.clear()
        self._track_to_trajectory.clear()
        self._camera_trajectories.clear()
        self._recent_gallery_items.clear()
        self._next_trajectory_id = 0
        logger.info("Cleared trajectory tracker")
