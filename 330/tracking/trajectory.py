"""
Trajectory analysis: motion patterns, velocity statistics and clustering.

Given a sequence of per-frame ``(track_id, bbox)`` pairs this module
computes per-track statistics, extracts motion descriptors and clusters
trajectories into common movement patterns.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------
@dataclass
class Trajectory:
    """Complete trajectory for a single track."""

    track_id: int
    frames: List[int] = field(default_factory=list)
    positions: List[Tuple[float, float]] = field(default_factory=list)
    bboxes: List[Tuple[float, float, float, float]] = field(default_factory=list)

    @property
    def n_points(self) -> int:
        return len(self.frames)

    @property
    def duration_frames(self) -> int:
        if not self.frames:
            return 0
        return self.frames[-1] - self.frames[0]

    @property
    def start(self) -> Optional[Tuple[float, float]]:
        return self.positions[0] if self.positions else None

    @property
    def end(self) -> Optional[Tuple[float, float]]:
        return self.positions[-1] if self.positions else None

    @property
    def displacement(self) -> float:
        if len(self.positions) < 2:
            return 0.0
        x0, y0 = self.positions[0]
        x1, y1 = self.positions[-1]
        return float(np.hypot(x1 - x0, y1 - y0))

    @property
    def path_length(self) -> float:
        if len(self.positions) < 2:
            return 0.0
        pts = np.array(self.positions, dtype=np.float64)
        diffs = np.diff(pts, axis=0)
        return float(np.sqrt((diffs * diffs).sum(axis=1)).sum())

    @property
    def straightness(self) -> float:
        """1.0 = perfectly straight, 0.0 = very convoluted."""
        path = self.path_length
        if path < 1e-6:
            return 0.0
        return self.displacement / path

    def velocities(self, fps: float = 30.0) -> np.ndarray:
        """Return per-frame speed (pixels/second)."""
        if len(self.positions) < 2:
            return np.array([], dtype=np.float64)
        pts = np.array(self.positions, dtype=np.float64)
        diffs = np.diff(pts, axis=0)
        speeds = np.sqrt((diffs * diffs).sum(axis=1)) * fps
        return speeds

    def acceleration(self, fps: float = 30.0) -> np.ndarray:
        """Return per-frame acceleration magnitude (pixels/s^2)."""
        v = self.velocities(fps)
        if len(v) < 2:
            return np.array([], dtype=np.float64)
        return np.diff(v) * fps

    def descriptor(self, fps: float = 30.0, n_bins: int = 8) -> np.ndarray:
        """
        Motion descriptor: histogram of movement directions + mean speed.

        Returns a ``n_bins + 3``-dimensional vector used for clustering.
        """
        if len(self.positions) < 2:
            return np.zeros(n_bins + 3, dtype=np.float64)

        pts = np.array(self.positions, dtype=np.float64)
        diffs = np.diff(pts, axis=0)
        angles = np.arctan2(diffs[:, 1], diffs[:, 0])
        hist, _ = np.histogram(
            angles, bins=n_bins, range=(-np.pi, np.pi), density=True
        )

        v = self.velocities(fps)
        if len(v) == 0:
            mean_v, std_v = 0.0, 0.0
        else:
            mean_v = float(np.mean(v))
            std_v = float(np.std(v))

        return np.concatenate([hist, [self.straightness, mean_v, std_v]])


@dataclass
class TrackStatistics:
    """Summary statistics for a set of trajectories."""

    n_tracks: int
    mean_duration: float
    mean_displacement: float
    mean_path_length: float
    mean_straightness: float
    mean_speed: float
    std_speed: float
    mean_acceleration: float
    clusters: Optional[List[int]] = None
    n_clusters: int = 0
    cluster_centers: Optional[np.ndarray] = None


# ---------------------------------------------------------------------------
# Trajectory builder
# ---------------------------------------------------------------------------
class TrajectoryBuilder:
    """
    Incrementally build trajectories from per-frame tracking results.

    Parameters
    ----------
    min_points:
        Minimum number of points to keep a trajectory.
    """

    def __init__(self, min_points: int = 3) -> None:
        self.min_points = min_points
        self._trajs: Dict[int, Trajectory] = {}

    def update(
        self,
        frame_id: int,
        tracks: Sequence[Tuple[int, Tuple[float, float, float, float]]],
    ) -> None:
        for tid, bbox in tracks:
            traj = self._trajs.setdefault(tid, Trajectory(track_id=tid))
            x, y, w, h = bbox
            traj.frames.append(frame_id)
            traj.positions.append((x + w / 2.0, y + h / 2.0))
            traj.bboxes.append(bbox)

    def trajectories(self) -> List[Trajectory]:
        return [t for t in self._trajs.values() if t.n_points >= self.min_points]

    def reset(self) -> None:
        self._trajs.clear()


# ---------------------------------------------------------------------------
# Clustering
# ---------------------------------------------------------------------------
class TrajectoryClusterer:
    """
    Cluster trajectories into common motion patterns.

    Uses k-means on the motion descriptors from
    :meth:`Trajectory.descriptor`.

    Parameters
    ----------
    n_clusters:
        Number of clusters.  ``None`` = auto-detect via silhouette score.
    max_clusters:
        Maximum clusters when auto-detecting.
    random_state:
        Seed for reproducibility.
    """

    def __init__(
        self,
        n_clusters: Optional[int] = None,
        max_clusters: int = 6,
        random_state: int = 42,
    ) -> None:
        self.n_clusters = n_clusters
        self.max_clusters = max_clusters
        self.random_state = random_state
        self._labels: Optional[np.ndarray] = None
        self._centers: Optional[np.ndarray] = None
        self._n_clusters: int = 0

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    @property
    def labels(self) -> Optional[np.ndarray]:
        return self._labels

    @property
    def centers(self) -> Optional[np.ndarray]:
        return self._centers

    def fit(self, trajectories: Sequence[Trajectory], fps: float = 30.0) -> np.ndarray:
        """
        Cluster trajectories.

        Returns
        -------
        ``labels`` array aligned with the input trajectories.
        """
        if not trajectories:
            self._labels = np.array([], dtype=np.int32)
            self._n_clusters = 0
            return self._labels

        X = np.stack([t.descriptor(fps) for t in trajectories])
        X = np.nan_to_num(X, nan=0.0, posinf=0.0, neginf=0.0)

        n_samples = X.shape[0]
        if n_samples == 1:
            self._labels = np.array([0], dtype=np.int32)
            self._n_clusters = 1
            self._centers = X.copy()
            return self._labels

        # Normalize
        mean = X.mean(axis=0)
        std = X.std(axis=0) + 1e-6
        X_norm = (X - mean) / std

        k = self.n_clusters
        if k is None:
            k = self._select_k(X_norm, n_samples)
        k = max(1, min(k, n_samples))

        # Simple k-means (no scipy dependency)
        rng = np.random.default_rng(self.random_state)
        idx = rng.choice(n_samples, size=k, replace=False)
        centers = X_norm[idx].copy()

        for _ in range(50):
            dists = np.linalg.norm(X_norm[:, None, :] - centers[None, :, :], axis=2)
            labels = np.argmin(dists, axis=1)
            new_centers = np.zeros_like(centers)
            for j in range(k):
                mask = labels == j
                if mask.any():
                    new_centers[j] = X_norm[mask].mean(axis=0)
                else:
                    new_centers[j] = centers[j]
            if np.allclose(centers, new_centers):
                break
            centers = new_centers

        self._labels = labels.astype(np.int32)
        self._centers = centers * std + mean  # de-normalise
        self._n_clusters = k
        return self._labels

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _select_k(self, X: np.ndarray, n_samples: int) -> int:
        best_k = 1
        best_score = -1.0
        max_k = min(self.max_clusters, n_samples - 1)
        if max_k < 2:
            return 1

        rng = np.random.default_rng(self.random_state)

        for k in range(2, max_k + 1):
            idx = rng.choice(n_samples, size=k, replace=False)
            centers = X[idx].copy()
            for _ in range(30):
                dists = np.linalg.norm(X[:, None, :] - centers[None, :, :], axis=2)
                labels = np.argmin(dists, axis=1)
                new_centers = np.zeros_like(centers)
                for j in range(k):
                    mask = labels == j
                    if mask.any():
                        new_centers[j] = X[mask].mean(axis=0)
                    else:
                        new_centers[j] = centers[j]
                if np.allclose(centers, new_centers):
                    break
                centers = new_centers

            # Silhouette-like score: ratio of inter/intra cluster distance
            intra = 0.0
            for j in range(k):
                mask = labels == j
                if mask.sum() > 1:
                    pts = X[mask]
                    c = pts.mean(axis=0)
                    intra += np.linalg.norm(pts - c, axis=1).mean()
            intra /= max(k, 1)

            inter = 0.0
            for a in range(k):
                for b in range(a + 1, k):
                    inter += np.linalg.norm(centers[a] - centers[b])
            inter /= max(k * (k - 1) / 2, 1)

            score = (inter - intra) / max(inter, 1e-6) if inter > 0 else 0.0
            if score > best_score:
                best_score = score
                best_k = k

        return best_k


# ---------------------------------------------------------------------------
# Analyzer
# ---------------------------------------------------------------------------
class TrajectoryAnalyzer:
    """
    High-level analyzer: builds trajectories, computes statistics and
    (optionally) clusters motion patterns.

    Usage::

        analyzer = TrajectoryAnalyzer()
        for frame_id, tracks in enumerate(per_frame_tracks):
            analyzer.update(frame_id, tracks)
        stats = analyzer.compute_stats()
        clusters = analyzer.cluster()
    """

    def __init__(
        self,
        min_points: int = 3,
        fps: float = 30.0,
        n_clusters: Optional[int] = None,
        max_clusters: int = 6,
    ) -> None:
        self.fps = fps
        self.builder = TrajectoryBuilder(min_points=min_points)
        self.clusterer = TrajectoryClusterer(n_clusters=n_clusters, max_clusters=max_clusters)

    def update(
        self,
        frame_id: int,
        tracks: Sequence[Tuple[int, Tuple[float, float, float, float]]],
    ) -> None:
        self.builder.update(frame_id, tracks)

    def trajectories(self) -> List[Trajectory]:
        return self.builder.trajectories()

    def compute_stats(self) -> TrackStatistics:
        """Return aggregate statistics over all trajectories."""
        trajs = self.trajectories()
        if not trajs:
            return TrackStatistics(
                n_tracks=0,
                mean_duration=0.0,
                mean_displacement=0.0,
                mean_path_length=0.0,
                mean_straightness=0.0,
                mean_speed=0.0,
                std_speed=0.0,
                mean_acceleration=0.0,
            )

        durations = [t.duration_frames / self.fps for t in trajs]
        displacements = [t.displacement for t in trajs]
        path_lengths = [t.path_length for t in trajs]
        straightnesses = [t.straightness for t in trajs]

        all_velocities = np.concatenate([t.velocities(self.fps) for t in trajs if t.n_points > 1]) if any(t.n_points > 1 for t in trajs) else np.array([])
        all_accels = np.concatenate([t.acceleration(self.fps) for t in trajs if t.n_points > 2]) if any(t.n_points > 2 for t in trajs) else np.array([])

        return TrackStatistics(
            n_tracks=len(trajs),
            mean_duration=float(np.mean(durations)) if durations else 0.0,
            mean_displacement=float(np.mean(displacements)) if displacements else 0.0,
            mean_path_length=float(np.mean(path_lengths)) if path_lengths else 0.0,
            mean_straightness=float(np.mean(straightnesses)) if straightnesses else 0.0,
            mean_speed=float(np.mean(all_velocities)) if len(all_velocities) else 0.0,
            std_speed=float(np.std(all_velocities)) if len(all_velocities) else 0.0,
            mean_acceleration=float(np.mean(np.abs(all_accels))) if len(all_accels) else 0.0,
        )

    def cluster(self) -> Tuple[List[int], int]:
        """
        Cluster trajectories into motion patterns.

        Returns
        -------
        ``(labels, n_clusters)``.
        """
        trajs = self.trajectories()
        if not trajs:
            return [], 0
        labels = self.clusterer.fit(trajs, self.fps)
        return list(labels), self.clusterer._n_clusters

    def reset(self) -> None:
        self.builder.reset()
