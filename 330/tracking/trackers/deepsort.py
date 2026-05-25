"""
DeepSORT multi-target tracker with enhanced occlusion handling and dynamic thresholds.

Implements the cascade matching + appearance gating scheme of
*Simple Online and Realtime Tracking with a Deep Association Metric*
(Wojke et al., 2017), with the following enhancements:

* **Kalman prediction during occlusion**: occluded tracks continue to
  be propagated via the Kalman filter so they can be recovered later.
* **Appearance re-identification**: a rolling window of appearance
  features is kept per track and used to match detections that
  reappear after long occlusions.
* **Re-association after recovery**: occluded tracks that re-enter the
  scene are matched via an additional appearance-based matching stage
  using both motion and appearance cues.
* **Dynamic cascade thresholds**: matching thresholds adapt automatically
  based on scene density (number of active tracks per unit area).
"""

from __future__ import annotations

import itertools
import math
from collections import deque
from dataclasses import dataclass, field
from typing import Deque, Dict, List, Optional, Tuple

import cv2
import numpy as np
import torch

from ..tracker_base import BaseTracker, BBox
from ..utils import (
    IDSwitchDetector,
    KalmanFilter,
    linear_assignment,
    vectorized_iou,
)
from .reid import EmbeddingExtractor


Detection = Tuple[float, float, float, float]  # (x, y, w, h)


@dataclass
class Track:
    """Internal representation of a single target."""

    track_id: int
    mean: np.ndarray
    covariance: np.ndarray
    hits: int = 1
    age: int = 1
    time_since_update: int = 0
    state: str = "tentative"  # tentative | confirmed | occluded | deleted
    features: Deque[np.ndarray] = field(default_factory=lambda: deque(maxlen=100))
    occlusion_frames: int = 0
    last_seen_bbox: Optional[BBox] = None

    @property
    def bbox(self) -> BBox:
        x, y, a, h = self.mean[:4]
        w = a * h
        return (float(x - w / 2.0), float(y - h / 2.0), float(w), float(h))

    def to_xyah(self, bbox: Detection) -> np.ndarray:
        x, y, w, h = bbox
        return np.array([x + w / 2.0, y + h / 2.0, w / max(h, 1e-6), h], dtype=np.float64)


class DeepSORTTracker(BaseTracker):
    """
    Multi-target tracker based on DeepSORT with occlusion handling and
    dynamic thresholds.

    Parameters
    ----------
    max_age:
        Number of missed detections before a track is deleted.
    n_init:
        Number of consecutive hits required to mark a track *confirmed*.
    iou_threshold:
        IoU threshold used for the IoU matching stage.
    max_iou_distance:
        Maximum allowed Mahalanobis-gated IoU distance.
    max_appearance_distance:
        Maximum cosine distance for appearance matching.
    lambda_:
        Weight of the appearance cost in the combined cost matrix.
    device:
        ``"cpu"`` or ``"cuda"``.
    enable_dynamic_thresholds:
        Automatically adjust matching thresholds based on scene density.
    """

    name = "DeepSORT"

    def __init__(
        self,
        max_age: int = 30,
        n_init: int = 3,
        iou_threshold: float = 0.3,
        max_iou_distance: float = 0.7,
        max_appearance_distance: float = 0.2,
        lambda_: float = 0.98,
        device: str = "cpu",
        enable_dynamic_thresholds: bool = True,
    ) -> None:
        super().__init__()
        self.max_age = max_age
        self.n_init = n_init
        self.base_iou_threshold = iou_threshold
        self.base_max_iou_distance = max_iou_distance
        self.base_max_appearance_distance = max_appearance_distance
        self.lambda_ = lambda_
        self.enable_dynamic_thresholds = enable_dynamic_thresholds

        self.device = torch.device(device if torch.cuda.is_available() else "cpu")
        self._kf = KalmanFilter()
        self._extractor = EmbeddingExtractor().to(self.device).eval()
        self._tracks: Dict[int, Track] = {}
        self._next_id = 1
        self._id_switch = IDSwitchDetector(iou_threshold=0.3)
        self._switches: List[Tuple[int, int]] = []

        # Dynamic threshold state
        self._current_iou_threshold = iou_threshold
        self._current_max_appearance_distance = max_appearance_distance
        self._current_max_iou_distance = max_iou_distance

    # ------------------------------------------------------------------
    # BaseTracker API
    # ------------------------------------------------------------------
    def _init(self, frame: np.ndarray, bbox: BBox) -> bool:
        self._validate_bbox(bbox)
        self._tracks.clear()
        self._next_id = 1
        self._switches.clear()
        self.multi_update(frame, [bbox])
        return True

    def _update(self, frame: np.ndarray) -> Tuple[bool, BBox]:
        results = self.multi_update(frame, [])
        if results:
            return True, results[0][1]
        return False, (0.0, 0.0, 0.0, 0.0)

    # ------------------------------------------------------------------
    # Dynamic thresholding
    # ------------------------------------------------------------------
    @property
    def current_thresholds(self) -> Dict[str, float]:
        """Return the currently active matching thresholds."""
        return {
            "iou_threshold": self._current_iou_threshold,
            "max_appearance_distance": self._current_max_appearance_distance,
            "max_iou_distance": self._current_max_iou_distance,
        }

    def _update_dynamic_thresholds(
        self,
        frame: np.ndarray,
        active_tracks: Dict[int, Track],
        detections: List[Detection],
    ) -> None:
        """Adapt thresholds based on scene density and number of targets."""
        if not self.enable_dynamic_thresholds:
            return

        h, w = frame.shape[:2]
        n_tracks = len(active_tracks)
        n_dets = len(detections)

        # Scene density: number of active targets per unit area (normalised)
        area = h * w
        density = max(n_tracks, n_dets) / math.sqrt(area) if area > 0 else 0.0

        # Density in [0, ~0.1] for typical scenes — map to [0, 1]
        density_norm = min(1.0, density / 0.05)

        # Clutter: ratio of unmatched detections to total detections
        total = n_dets + n_tracks
        clutter = 0.0
        if total > 0:
            clutter = abs(n_dets - n_tracks) / total

        # Adjust thresholds — denser / more cluttered scenes require
        # stricter matching to avoid false associations.
        adjust = density_norm * 0.4 + clutter * 0.3

        self._current_iou_threshold = max(
            0.3, self.base_iou_threshold - adjust * 0.2
        )
        self._current_max_appearance_distance = max(
            0.05, self.base_max_appearance_distance - adjust * 0.1
        )
        self._current_max_iou_distance = max(
            0.3, self.base_max_iou_distance - adjust * 0.15
        )

    # ------------------------------------------------------------------
    # Multi-target API
    # ------------------------------------------------------------------
    @property
    def tracks(self) -> Dict[int, Track]:
        return dict(self._tracks)

    @property
    def id_switches(self) -> List[Tuple[int, int]]:
        return list(self._switches)

    def multi_update(
        self,
        frame: np.ndarray,
        detections: List[Detection],
    ) -> List[Tuple[int, BBox]]:
        """
        Advance the tracker to the next *frame*.
        """
        # 0. Update dynamic thresholds based on scene content
        active = {tid: t for tid, t in self._tracks.items() if t.state in ("confirmed", "occluded")}
        self._update_dynamic_thresholds(frame, active, detections)

        # 1. Predict existing tracks (including occluded ones) via Kalman filter
        for track in self._tracks.values():
            track.mean, track.covariance = self._kf.predict(
                track.mean, track.covariance
            )
            track.age += 1
            track.time_since_update += 1

        # 2. Extract appearance features for all detections
        features = self._extract_features(frame, detections) if detections else []

        # 3. First pass: match confirmed non-occluded tracks via cascade
        confirmed = [tid for tid, t in self._tracks.items() if t.state == "confirmed"]
        occluded = [tid for tid, t in self._tracks.items() if t.state == "occluded"]

        matched, unmatched_tracks, unmatched_detections = self._match_cascade(
            confirmed, detections, features
        )

        # 4. Second pass: match remaining detections to occluded tracks
        # using appearance similarity + Kalman prediction
        if occluded and unmatched_detections:
            rematched, still_unmatched_t, still_unmatched_d = self._match_occluded(
                occluded, unmatched_detections, detections, features
            )
            matched.extend(rematched)
            unmatched_tracks = list(set(unmatched_tracks) | set(still_unmatched_t))
            unmatched_detections = list(still_unmatched_d)

        # 5. Third pass: IoU matching for remaining confirmed tracks AND tentative tracks
        remaining_tracks = list(set(unmatched_tracks) | {
            tid for tid, t in self._tracks.items() if t.state == "tentative"
        })
        if remaining_tracks and unmatched_detections:
            iou_matched, iou_unmatched_t, iou_unmatched_d = self._match_iou(
                remaining_tracks, unmatched_detections, detections
            )
            matched.extend(iou_matched)
            unmatched_tracks = [tid for tid in unmatched_tracks if tid in iou_unmatched_t]
            unmatched_tracks.extend([tid for tid in remaining_tracks if tid in iou_unmatched_t and tid not in unmatched_tracks])
            unmatched_detections = list(iou_unmatched_d)

        # 6. Update matched tracks
        for track_id, det_idx in matched:
            track = self._tracks[track_id]
            bbox = detections[det_idx]
            xyah = np.array(
                [
                    bbox[0] + bbox[2] / 2.0,
                    bbox[1] + bbox[3] / 2.0,
                    bbox[2] / max(bbox[3], 1e-6),
                    bbox[3],
                ],
                dtype=np.float64,
            )
            track.mean, track.covariance = self._kf.update(
                track.mean, track.covariance, xyah
            )
            if features:
                track.features.append(features[det_idx])
            track.hits += 1
            track.time_since_update = 0
            track.occlusion_frames = 0
            track.last_seen_bbox = bbox
            if track.state == "tentative" and track.hits >= self.n_init:
                track.state = "confirmed"
            elif track.state == "occluded":
                # Recovered from occlusion — restore to confirmed
                track.state = "confirmed"

        # 7. Handle unmatched tracks
        for track_id in unmatched_tracks:
            track = self._tracks.get(track_id)
            if track is None:
                continue
            if track.state == "tentative" and track.time_since_update >= self.n_init:
                track.state = "deleted"
            elif track.time_since_update > self.max_age:
                track.state = "deleted"
            elif track.state == "confirmed":
                track.state = "occluded"
                track.occlusion_frames += 1
            elif track.state == "occluded":
                track.occlusion_frames += 1

        # 8. Spawn new tracks for unmatched detections
        for det_idx in unmatched_detections:
            bbox = detections[det_idx]
            xyah = np.array(
                [
                    bbox[0] + bbox[2] / 2.0,
                    bbox[1] + bbox[3] / 2.0,
                    bbox[2] / max(bbox[3], 1e-6),
                    bbox[3],
                ],
                dtype=np.float64,
            )
            mean, covariance = self._kf.initiate(xyah)
            tid = self._next_id
            self._next_id += 1
            track = Track(track_id=tid, mean=mean, covariance=covariance)
            if features:
                track.features.append(features[det_idx])
            track.last_seen_bbox = bbox
            self._tracks[tid] = track

        # 9. Prune deleted tracks and detect ID switches
        self._tracks = {tid: t for tid, t in self._tracks.items() if t.state != "deleted"}
        current_bboxes = {
            tid: t.bbox for tid, t in self._tracks.items()
            if t.state in ("confirmed", "occluded")
        }
        self._switches.extend(self._id_switch.update(current_bboxes))

        # 10. Return confirmed outputs
        return [
            (tid, self._tracks[tid].bbox)
            for tid in sorted(self._tracks)
            if self._tracks[tid].state == "confirmed"
        ]

    # ------------------------------------------------------------------
    # Matching stages
    # ------------------------------------------------------------------
    def _match_cascade(
        self,
        track_ids: List[int],
        detections: List[Detection],
        features: List[np.ndarray],
    ) -> Tuple[List[Tuple[int, int]], List[int], List[int]]:
        """
        Cascade matching: match detections to confirmed tracks using
        appearance + motion cost, prioritising tracks seen more recently.
        """
        if not track_ids or not detections:
            return [], list(track_ids), list(range(len(detections)))

        track_list = [self._tracks[i] for i in track_ids]
        cost = self._cost_matrix(track_list, detections, features)

        matched: List[Tuple[int, int]] = []
        unmatched_t: set[int] = set(range(len(track_ids)))
        unmatched_d: set[int] = set(range(len(detections)))

        matches = linear_assignment(cost)
        for t_idx, d_idx in matches:
            if cost[t_idx, d_idx] < self._current_max_appearance_distance:
                matched.append((track_ids[t_idx], d_idx))
                unmatched_t.discard(t_idx)
                unmatched_d.discard(d_idx)

        unmatched_track_ids = [track_ids[i] for i in unmatched_t]
        return matched, unmatched_track_ids, list(unmatched_d)

    def _match_occluded(
        self,
        occluded_ids: List[int],
        det_indices: List[int],
        detections: List[Detection],
        features: List[np.ndarray],
    ) -> Tuple[List[Tuple[int, int]], List[int], List[int]]:
        """
        Appearance-based matching for occluded tracks to help with
        re-identification after occlusion.  Uses a combination of
        appearance similarity (cosine distance to a rolling average of
        past features) and motion prediction from the Kalman filter.
        """
        if not occluded_ids or not det_indices:
            return [], list(occluded_ids), list(det_indices)

        n_t = len(occluded_ids)
        n_d = len(det_indices)
        appearance_cost = np.full((n_t, n_d), 1e5, dtype=np.float32)
        motion_cost = np.full((n_t, n_d), 1e5, dtype=np.float32)

        for i, tid in enumerate(occluded_ids):
            track = self._tracks[tid]
            if not track.features:
                continue
            mean_feat = np.mean(np.stack(track.features, axis=0), axis=0)
            mean_feat = mean_feat / (np.linalg.norm(mean_feat) + 1e-12)
            for j, d_idx in enumerate(det_indices):
                if d_idx >= len(features):
                    continue
                feat = features[d_idx] / (np.linalg.norm(features[d_idx]) + 1e-12)
                appearance_cost[i, j] = 1.0 - float(np.dot(mean_feat, feat))

        # Motion cost: Mahalanobis distance from Kalman prediction
        for i, tid in enumerate(occluded_ids):
            track = self._tracks[tid]
            try:
                proj_mean, proj_cov = self._kf.project(track.mean, track.covariance)
                inv_cov = np.linalg.inv(proj_cov)
            except np.linalg.LinAlgError:
                continue
            for j, d_idx in enumerate(det_indices):
                det = detections[d_idx]
                xyah = np.array(
                    [
                        det[0] + det[2] / 2.0,
                        det[1] + det[3] / 2.0,
                        det[2] / max(det[3], 1e-6),
                        det[3],
                    ],
                    dtype=np.float64,
                )
                diff = xyah - proj_mean
                motion_cost[i, j] = min(float(diff @ inv_cov @ diff), self._current_max_iou_distance)

        # Occlusion-aware weighting: the longer the occlusion, the more
        # we rely on appearance vs. motion.
        combined = np.zeros_like(appearance_cost)
        for i, tid in enumerate(occluded_ids):
            occ = self._tracks[tid].occlusion_frames
            w = min(1.0, occ / max(self.max_age, 1))
            lam = self.lambda_ * (1.0 - w) + 0.99 * w
            combined[i] = lam * appearance_cost[i] + (1 - lam) * motion_cost[i]

        matches = linear_assignment(combined)

        matched: List[Tuple[int, int]] = []
        unmatched_t: set[int] = set(range(n_t))
        unmatched_d: set[int] = set(range(n_d))

        # For occluded tracks we allow a slightly looser appearance gate.
        max_cost = self._current_max_appearance_distance * 1.5
        for t_idx, d_idx in matches:
            if combined[t_idx, d_idx] < max_cost:
                matched.append((occluded_ids[t_idx], det_indices[d_idx]))
                unmatched_t.discard(t_idx)
                unmatched_d.discard(d_idx)

        unmatched_track_ids = [occluded_ids[i] for i in unmatched_t]
        unmatched_det_ids = [det_indices[i] for i in unmatched_d]
        return matched, unmatched_track_ids, unmatched_det_ids

    def _match_iou(
        self,
        track_ids: List[int],
        det_indices: List[int],
        detections: List[Detection],
    ) -> Tuple[List[Tuple[int, int]], List[int], List[int]]:
        """IoU-based matching for remaining confirmed tracks."""
        if not track_ids or not det_indices:
            return [], list(track_ids), list(det_indices)

        track_boxes = np.array([self._tracks[tid].bbox for tid in track_ids], dtype=np.float32)
        det_boxes = np.array([detections[i] for i in det_indices], dtype=np.float32)
        iou_mat = vectorized_iou(track_boxes, det_boxes)
        cost = 1.0 - iou_mat

        matches = linear_assignment(cost)

        matched: List[Tuple[int, int]] = []
        unmatched_t: set[int] = set(range(len(track_ids)))
        unmatched_d: set[int] = set(range(len(det_indices)))

        max_cost = 1.0 - self._current_iou_threshold
        for t_idx, d_idx in matches:
            if cost[t_idx, d_idx] < max_cost:
                matched.append((track_ids[t_idx], det_indices[d_idx]))
                unmatched_t.discard(t_idx)
                unmatched_d.discard(d_idx)

        unmatched_track_ids = [track_ids[i] for i in unmatched_t]
        unmatched_det_ids = [det_indices[i] for i in unmatched_d]
        return matched, unmatched_track_ids, unmatched_det_ids

    # ------------------------------------------------------------------
    # Cost matrix
    # ------------------------------------------------------------------
    def _cost_matrix(
        self,
        track_list: List[Track],
        detections: List[Detection],
        features: List[np.ndarray],
    ) -> np.ndarray:
        """Combined motion + appearance cost matrix."""
        n_tracks = len(track_list)
        n_dets = len(detections)
        appearance_cost = np.full((n_tracks, n_dets), 1e5, dtype=np.float32)
        motion_cost = np.full((n_tracks, n_dets), 1e5, dtype=np.float32)

        for i, track in enumerate(track_list):
            if not track.features:
                continue
            track_feat = np.mean(np.stack(track.features, axis=0), axis=0)
            track_feat = track_feat / (np.linalg.norm(track_feat) + 1e-12)
            for j in range(n_dets):
                if j >= len(features):
                    continue
                det_feat = features[j] / (np.linalg.norm(features[j]) + 1e-12)
                appearance_cost[i, j] = 1.0 - float(np.dot(track_feat, det_feat))

        for i, track in enumerate(track_list):
            proj_mean, proj_cov = self._kf.project(track.mean, track.covariance)
            try:
                inv_cov = np.linalg.inv(proj_cov)
            except np.linalg.LinAlgError:
                continue
            for j, det in enumerate(detections):
                xyah = np.array(
                    [
                        det[0] + det[2] / 2.0,
                        det[1] + det[3] / 2.0,
                        det[2] / max(det[3], 1e-6),
                        det[3],
                    ],
                    dtype=np.float64,
                )
                diff = xyah - proj_mean
                motion_cost[i, j] = min(float(diff @ inv_cov @ diff), self._current_max_iou_distance)

        return self.lambda_ * appearance_cost + (1 - self.lambda_) * motion_cost

    # ------------------------------------------------------------------
    # Feature extraction
    # ------------------------------------------------------------------
    def _extract_features(
        self, frame: np.ndarray, detections: List[Detection]
    ) -> List[np.ndarray]:
        if not detections:
            return []

        h, w = self._extractor.input_h, self._extractor.input_w
        crops = []
        for (x, y, bw, bh) in detections:
            x1 = max(0, int(round(x)))
            y1 = max(0, int(round(y)))
            x2 = min(frame.shape[1], int(round(x + bw)))
            y2 = min(frame.shape[0], int(round(y + bh)))
            if x2 <= x1 or y2 <= y1:
                crop = np.zeros((h, w, 3), dtype=np.uint8)
            else:
                crop = frame[y1:y2, x1:x2]
                crop = cv2.resize(crop, (w, h), interpolation=cv2.INTER_LINEAR)
            tensor = (
                torch.from_numpy(crop).permute(2, 0, 1).float() / 255.0
            )
            crops.append(tensor)

        batch = torch.stack(crops, dim=0).to(self.device)
        with torch.no_grad():
            embeddings = self._extractor(batch).cpu().numpy()
        return [embeddings[i] for i in range(len(detections))]

    # ------------------------------------------------------------------
    # Reset
    # ------------------------------------------------------------------
    def _reset(self) -> None:
        self._tracks.clear()
        self._next_id = 1
        self._switches.clear()
        self._id_switch.reset()
