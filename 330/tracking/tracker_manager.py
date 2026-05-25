"""
Unified multi-target tracker manager with occlusion handling and dynamic thresholds.

:class:`TrackerManager` orchestrates a set of per-target
:class:`BaseTracker` instances (KCF, CSRT, SiamRPN, etc.) and provides
an API that mirrors :class:`DeepSORTTracker` so that single-object and
multi-object trackers can be used interchangeably.

**Enhanced features**:

* **Kalman filter prediction during occlusion**: each track has its own
  Kalman filter that keeps predicting the target's position during
  occlusions, allowing the track to be recovered later.
* **Appearance re-identification**: appearance features are extracted
  for every detection and stored per track, enabling matching based on
  visual similarity when motion cues are insufficient.
* **Re-association after recovery**: occluded tracks are matched via a
  second association stage that uses both appearance and motion cues.
* **Dynamic cascade thresholds**: matching thresholds adapt automatically
  based on scene density (number of active tracks per unit area).
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Deque, Dict, List, Optional, Tuple

import cv2
import numpy as np
import torch

from .tracker_base import BaseTracker, BBox
from .trackers import KCFTracker, CSRTTracker, SiamRPNTracker, DeepSORTTracker
from .trackers.reid import EmbeddingExtractor
from .utils import (
    IDSwitchDetector,
    KalmanFilter,
    linear_assignment,
    vectorized_iou,
)


_TRACKER_FACTORIES = {
    "KCF": KCFTracker,
    "CSRT": CSRTTracker,
    "SiamRPN": SiamRPNTracker,
    "DeepSORT": DeepSORTTracker,
}


@dataclass
class _PerTargetState:
    tracker: BaseTracker
    bbox: BBox
    misses: int = 0
    confirmed: bool = False
    history: List[BBox] = field(default_factory=list)
    features: Deque[np.ndarray] = field(default_factory=lambda: Deque(maxlen=100))
    kf_mean: Optional[np.ndarray] = None
    kf_cov: Optional[np.ndarray] = None
    occlusion_frames: int = 0


class TrackerManager:
    """
    Multi-target tracker built on top of any :class:`BaseTracker`.

    Parameters
    ----------
    tracker_type:
        One of ``"KCF"``, ``"CSRT"``, ``"SiamRPN"``, ``"DeepSORT"``.
    iou_threshold:
        IoU threshold used to associate new detections to existing tracks.
    max_misses:
        Number of consecutive missed associations before a track is
        removed.
    n_init:
        Number of consecutive matches required before a track becomes
        *confirmed*.
    enable_kalman:
        Whether to use Kalman filter prediction for occlusion handling.
    enable_appearance:
        Whether to use appearance features for re-identification.
    enable_dynamic_thresholds:
        Automatically adjust matching thresholds based on scene density.
    lambda_:
        Weight of appearance cost vs. motion cost (0 = motion only, 1 =
        appearance only).
    device:
        ``"cpu"`` or ``"cuda"``.
    tracker_kwargs:
        Additional keyword arguments forwarded to the underlying
        per-target tracker.
    """

    def __init__(
        self,
        tracker_type: str = "CSRT",
        iou_threshold: float = 0.3,
        max_misses: int = 15,
        n_init: int = 3,
        enable_kalman: bool = True,
        enable_appearance: bool = True,
        enable_dynamic_thresholds: bool = True,
        lambda_: float = 0.5,
        device: str = "cpu",
        tracker_kwargs: Optional[dict] = None,
    ) -> None:
        if tracker_type not in _TRACKER_FACTORIES:
            raise ValueError(
                f"Unknown tracker_type {tracker_type!r}. "
                f"Choose from {sorted(_TRACKER_FACTORIES)}"
            )
        self.tracker_type = tracker_type
        self.base_iou_threshold = iou_threshold
        self.max_misses = max_misses
        self.n_init = n_init
        self.enable_kalman = enable_kalman
        self.enable_appearance = enable_appearance
        self.enable_dynamic_thresholds = enable_dynamic_thresholds
        self.lambda_ = lambda_

        self.device = torch.device(device if torch.cuda.is_available() or device == "cpu" else "cpu")
        self._factory = _TRACKER_FACTORIES[tracker_type]
        self._tracker_kwargs = dict(tracker_kwargs or {})

        self._tracks: Dict[int, _PerTargetState] = {}
        self._next_id = 1
        self._id_switch = IDSwitchDetector(iou_threshold=iou_threshold)
        self._switches: List[Tuple[int, int]] = []

        # Kalman filter (shared instance for all tracks)
        self._kf = KalmanFilter() if enable_kalman else None

        # Appearance feature extractor
        self._extractor: Optional[EmbeddingExtractor] = None
        if enable_appearance:
            self._extractor = EmbeddingExtractor().to(self.device).eval()

        # Dynamic threshold state
        self._current_iou_threshold = iou_threshold
        self._current_appearance_threshold = 0.3

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    @property
    def tracks(self) -> Dict[int, BBox]:
        """Return ``{track_id: bbox}`` for confirmed tracks."""
        return {tid: s.bbox for tid, s in self._tracks.items() if s.confirmed}

    @property
    def id_switches(self) -> List[Tuple[int, int]]:
        return list(self._switches)

    @property
    def current_thresholds(self) -> Dict[str, float]:
        """Return the currently active matching thresholds."""
        return {
            "iou_threshold": self._current_iou_threshold,
            "appearance_threshold": self._current_appearance_threshold,
        }

    def reset(self) -> None:
        self._tracks.clear()
        self._next_id = 1
        self._switches.clear()
        self._id_switch.reset()

    def update(
        self,
        frame: np.ndarray,
        detections: Optional[List[BBox]] = None,
    ) -> List[Tuple[int, BBox]]:
        """
        Run one frame of tracking.

        Parameters
        ----------
        frame:
            BGR image.
        detections:
            Optional list of detection boxes ``(x, y, w, h)`` supplied by
            an external detector.  When provided, the manager uses them to
            create new tracks and recover from occlusion.  When
            ``None``, the per-target trackers predict on their own.

        Returns
        -------
        List of ``(track_id, bbox)`` pairs for confirmed tracks.
        """
        detections = detections or []

        # 0. Update dynamic thresholds based on scene content
        self._update_dynamic_thresholds(frame, detections)

        # 1. Predict every track's state via Kalman filter (if enabled)
        if self._kf is not None:
            for state in self._tracks.values():
                if state.kf_mean is not None:
                    state.kf_mean, state.kf_cov = self._kf.predict(
                        state.kf_mean, state.kf_cov
                    )

        # 2. Predict every existing tracker, but do **not** overwrite the
        # track's authoritative bbox yet — that happens only after
        # association with a detection (or when no detections are available
        # at all).
        last_bboxes = {tid: state.bbox for tid, state in self._tracks.items()}
        predictions: Dict[int, BBox] = {}
        for tid, state in self._tracks.items():
            ok, bbox = state.tracker.update(frame)
            if ok:
                predictions[tid] = bbox

        # 3. Extract appearance features for all detections (if enabled)
        features: List[np.ndarray] = []
        if self._extractor is not None and detections:
            features = self._extract_features(frame, detections)

        # 4. First association stage: IoU-based matching with last-seen bboxes
        matched: List[Tuple[int, int]] = []
        unmatched_tracks: List[int] = []
        unmatched_detections: List[int] = []

        if detections:
            track_ids = list(self._tracks.keys())
            if track_ids:
                last = np.array([last_bboxes[tid] for tid in track_ids], dtype=np.float32)
                det_boxes = np.array(detections, dtype=np.float32)
                iou_mat = vectorized_iou(last, det_boxes)
                cost = 1.0 - iou_mat

                matches = linear_assignment(cost)

                matched_t: set[int] = set()
                matched_d: set[int] = set()
                for t_idx, d_idx in matches:
                    if cost[t_idx, d_idx] < (1.0 - self._current_iou_threshold):
                        matched.append((track_ids[t_idx], d_idx))
                        matched_t.add(track_ids[t_idx])
                        matched_d.add(d_idx)

                unmatched_tracks = [tid for tid in track_ids if tid not in matched_t]
                unmatched_detections = [i for i in range(len(detections)) if i not in matched_d]

                # Update matched tracks
                for tid, d_idx in matched:
                    state = self._tracks[tid]
                    det_bbox = tuple(float(v) for v in detections[d_idx])
                    state.bbox = det_bbox
                    state.history.append(det_bbox)
                    state.misses = 0
                    state.occlusion_frames = 0
                    state.confirmed = state.confirmed or (
                        state.history and len(state.history) >= self.n_init
                    )
                    if self._extractor is not None and features:
                        state.features.append(features[d_idx])
                    if self._kf is not None:
                        xyah = np.array(
                            [
                                det_bbox[0] + det_bbox[2] / 2.0,
                                det_bbox[1] + det_bbox[3] / 2.0,
                                det_bbox[2] / max(det_bbox[3], 1e-6),
                                det_bbox[3],
                            ],
                            dtype=np.float64,
                        )
                        if state.kf_mean is None:
                            state.kf_mean, state.kf_cov = self._kf.initiate(xyah)
                        else:
                            state.kf_mean, state.kf_cov = self._kf.update(
                                state.kf_mean, state.kf_cov, xyah
                            )
                    try:
                        state.tracker.init(frame, det_bbox)
                    except Exception:  # pragma: no cover
                        pass

                # 5. Second association stage: appearance + Kalman for unmatched
                if (
                    self._extractor is not None
                    and unmatched_tracks
                    and unmatched_detections
                ):
                    appearance_matched = self._match_by_appearance(
                        unmatched_tracks, unmatched_detections, detections, features
                    )
                    for tid, d_idx in appearance_matched:
                        if d_idx in unmatched_detections and tid in unmatched_tracks:
                            matched.append((tid, d_idx))
                            unmatched_tracks.remove(tid)
                            unmatched_detections.remove(d_idx)
                            state = self._tracks[tid]
                            det_bbox = tuple(float(v) for v in detections[d_idx])
                            state.bbox = det_bbox
                            state.history.append(det_bbox)
                            state.misses = 0
                            state.occlusion_frames = 0
                            state.confirmed = True  # Recovered from occlusion
                            state.features.append(features[d_idx])
                            if self._kf is not None:
                                xyah = np.array(
                                    [
                                        det_bbox[0] + det_bbox[2] / 2.0,
                                        det_bbox[1] + det_bbox[3] / 2.0,
                                        det_bbox[2] / max(det_bbox[3], 1e-6),
                                        det_bbox[3],
                                    ],
                                    dtype=np.float64,
                                )
                                if state.kf_mean is None:
                                    state.kf_mean, state.kf_cov = self._kf.initiate(xyah)
                                else:
                                    state.kf_mean, state.kf_cov = self._kf.update(
                                        state.kf_mean, state.kf_cov, xyah
                                    )
                            try:
                                state.tracker.init(frame, det_bbox)
                            except Exception:  # pragma: no cover
                                pass

                # 6. Spawn new tracks for remaining unmatched detections
                for d_idx in unmatched_detections:
                    self._spawn(frame, tuple(float(v) for v in detections[d_idx]), features[d_idx] if features else None)

                # 7. Increment miss counter for unmatched tracks
                for tid in unmatched_tracks:
                    state = self._tracks[tid]
                    state.misses += 1
                    state.occlusion_frames += 1

                    # Use Kalman prediction as the current bbox during occlusion
                    if self._kf is not None and state.kf_mean is not None:
                        x, y, a, h = state.kf_mean[:4]
                        w = a * h
                        state.bbox = (
                            float(x - w / 2.0),
                            float(y - h / 2.0),
                            float(w),
                            float(h),
                        )
                    elif tid in predictions:
                        # Fall back to tracker prediction
                        state.bbox = predictions[tid]

            else:
                # No existing tracks — all detections become new ones.
                for i, det in enumerate(detections):
                    feat = features[i] if features else None
                    self._spawn(frame, tuple(float(v) for v in det), feat)
        else:
            # Purely prediction mode — fall back to the tracker output.
            for tid, bbox in predictions.items():
                state = self._tracks[tid]
                state.bbox = bbox
                state.history.append(bbox)
                state.confirmed = state.confirmed or (
                    state.history and len(state.history) >= self.n_init
                )

        # 8. Prune tracks that have too many misses
        to_remove: List[int] = []
        for tid in list(self._tracks):
            if self._tracks[tid].misses > self.max_misses:
                to_remove.append(tid)
        for tid in to_remove:
            self._tracks.pop(tid, None)

        # 9. ID switch detection
        current = {tid: state.bbox for tid, state in self._tracks.items() if state.confirmed}
        self._switches.extend(self._id_switch.update(current))

        return [
            (tid, state.bbox)
            for tid, state in sorted(self._tracks.items())
            if state.confirmed
        ]

    # ------------------------------------------------------------------
    # Dynamic thresholding
    # ------------------------------------------------------------------
    def _update_dynamic_thresholds(
        self,
        frame: np.ndarray,
        detections: List[BBox],
    ) -> None:
        """Adapt thresholds based on scene density."""
        if not self.enable_dynamic_thresholds:
            return

        h, w = frame.shape[:2]
        n_tracks = len(self._tracks)
        n_dets = len(detections)

        area = h * w
        density = max(n_tracks, n_dets) / math.sqrt(area) if area > 0 else 0.0
        density_norm = min(1.0, density / 0.05)

        total = n_dets + n_tracks
        clutter = 0.0
        if total > 0:
            clutter = abs(n_dets - n_tracks) / total

        adjust = density_norm * 0.4 + clutter * 0.3

        self._current_iou_threshold = max(
            0.3, self.base_iou_threshold - adjust * 0.2
        )
        self._current_appearance_threshold = max(
            0.05, 0.3 - adjust * 0.1
        )

    # ------------------------------------------------------------------
    # Appearance-based matching
    # ------------------------------------------------------------------
    def _match_by_appearance(
        self,
        track_ids: List[int],
        det_indices: List[int],
        detections: List[BBox],
        features: List[np.ndarray],
    ) -> List[Tuple[int, int]]:
        """
        Match unmatched tracks to unmatched detections using appearance
        similarity combined with motion prediction from the Kalman filter.
        """
        if not track_ids or not det_indices:
            return []

        n_t = len(track_ids)
        n_d = len(det_indices)
        cost = np.zeros((n_t, n_d), dtype=np.float32)

        for i, tid in enumerate(track_ids):
            state = self._tracks[tid]
            if not state.features:
                cost[i, :] = 1e5
                continue

            mean_feat = np.mean(np.stack(state.features, axis=0), axis=0)
            mean_feat = mean_feat / (np.linalg.norm(mean_feat) + 1e-12)

            for j, d_idx in enumerate(det_indices):
                if d_idx >= len(features):
                    cost[i, j] = 1e5
                    continue
                det_feat = features[d_idx] / (np.linalg.norm(features[d_idx]) + 1e-12)
                appearance_cost = 1.0 - float(np.dot(mean_feat, det_feat))

                # Motion cost from Kalman filter
                motion_cost = 0.0
                if self._kf is not None and state.kf_mean is not None:
                    try:
                        proj_mean, proj_cov = self._kf.project(
                            state.kf_mean, state.kf_cov
                        )
                        inv_cov = np.linalg.inv(proj_cov)
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
                        motion_cost = min(float(diff @ inv_cov @ diff), 10.0) / 10.0
                    except np.linalg.LinAlgError:
                        motion_cost = 0.5

                # Combined cost: appearance weighted by lambda, motion by (1 - lambda)
                occ = state.occlusion_frames
                w = min(1.0, occ / max(self.max_misses, 1))
                lam = self.lambda_ * (1.0 - w) + 0.9 * w
                cost[i, j] = lam * appearance_cost + (1 - lam) * motion_cost

        matches = linear_assignment(cost)
        matched = []
        max_cost = self._current_appearance_threshold * 1.5
        for t_idx, d_idx in matches:
            if cost[t_idx, d_idx] < max_cost:
                matched.append((track_ids[t_idx], det_indices[d_idx]))
        return matched

    # ------------------------------------------------------------------
    # Feature extraction
    # ------------------------------------------------------------------
    def _extract_features(
        self, frame: np.ndarray, detections: List[BBox]
    ) -> List[np.ndarray]:
        if not detections or self._extractor is None:
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
            tensor = torch.from_numpy(crop).permute(2, 0, 1).float() / 255.0
            crops.append(tensor)

        batch = torch.stack(crops, dim=0).to(self.device)
        with torch.no_grad():
            embeddings = self._extractor(batch).cpu().numpy()
        return [embeddings[i] for i in range(len(detections))]

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------
    def _spawn(
        self,
        frame: np.ndarray,
        bbox: Tuple[float, float, float, float],
        feature: Optional[np.ndarray] = None,
    ) -> None:
        tracker = self._factory(**self._tracker_kwargs)
        ok = tracker.init(frame, bbox)
        if not ok:
            return
        state = _PerTargetState(tracker=tracker, bbox=bbox, history=[bbox])
        if self.n_init <= 1:
            state.confirmed = True
        if feature is not None:
            state.features.append(feature)
        if self._kf is not None:
            xyah = np.array(
                [
                    bbox[0] + bbox[2] / 2.0,
                    bbox[1] + bbox[3] / 2.0,
                    bbox[2] / max(bbox[3], 1e-6),
                    bbox[3],
                ],
                dtype=np.float64,
            )
            state.kf_mean, state.kf_cov = self._kf.initiate(xyah)
        self._tracks[self._next_id] = state
        self._next_id += 1
