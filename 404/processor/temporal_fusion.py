import cv2
import numpy as np
from typing import List, Dict, Optional, Tuple
from collections import deque, defaultdict
from dataclasses import dataclass, field
import time

from detector.yolo_detector import DetectionResult


@dataclass
class TrackedDetection:
    detection: DetectionResult
    frame_id: int
    timestamp: float
    track_id: int = -1
    age: int = 0
    hit_count: int = 1
    confidence_history: List[float] = field(default_factory=list)


@dataclass
class StabilizedResult:
    detection: DetectionResult
    track_id: int
    smoothed_confidence: float
    existence_confidence: float
    frames_seen: int
    is_stable: bool


class TemporalFusion:
    def __init__(
        self,
        window_size: int = 5,
        min_frames_for_stable: int = 3,
        min_hit_ratio: float = 0.6,
        iou_threshold: float = 0.3,
        max_age: int = 2,
        enable_voting: bool = True,
        enable_smoothing: bool = True
    ):
        self.window_size = window_size
        self.min_frames_for_stable = min_frames_for_stable
        self.min_hit_ratio = min_hit_ratio
        self.iou_threshold = iou_threshold
        self.max_age = max_age
        self.enable_voting = enable_voting
        self.enable_smoothing = enable_smoothing

        self.frame_buffer: deque = deque(maxlen=window_size)
        self.tracks: Dict[int, TrackedDetection] = {}
        self.next_track_id = 0
        self.current_frame_id = 0

        self.class_votes: Dict[int, Dict[int, List[float]]] = defaultdict(lambda: defaultdict(list))

    def _calculate_iou(self, bbox1: List[int], bbox2: List[int]) -> float:
        x1 = max(bbox1[0], bbox2[0])
        y1 = max(bbox1[1], bbox2[1])
        x2 = min(bbox1[2], bbox2[2])
        y2 = min(bbox1[3], bbox2[3])

        w = max(0, x2 - x1)
        h = max(0, y2 - y1)
        inter = w * h

        area1 = (bbox1[2] - bbox1[0]) * (bbox1[3] - bbox1[1])
        area2 = (bbox2[2] - bbox2[0]) * (bbox2[3] - bbox2[1])
        union = area1 + area2 - inter

        return inter / union if union > 0 else 0

    def _match_detections(
        self,
        detections: List[DetectionResult],
        tracks: Dict[int, TrackedDetection]
    ) -> Tuple[List[int], List[int], List[int]]:
        if not tracks:
            return [], [], list(range(len(detections)))

        track_ids = list(tracks.keys())
        num_dets = len(detections)
        num_tracks = len(track_ids)

        if num_dets == 0 or num_tracks == 0:
            return [], [], list(range(num_dets))

        iou_matrix = np.zeros((num_dets, num_tracks))
        for i, det in enumerate(detections):
            for j, tid in enumerate(track_ids):
                iou_matrix[i, j] = self._calculate_iou(det.bbox, tracks[tid].detection.bbox)

        matched_dets = []
        matched_tracks = []

        while np.max(iou_matrix) > self.iou_threshold:
            idx = np.unravel_index(np.argmax(iou_matrix), iou_matrix.shape)
            det_idx, track_idx = idx[0], idx[1]

            matched_dets.append(det_idx)
            matched_tracks.append(track_ids[track_idx])

            iou_matrix[det_idx, :] = 0
            iou_matrix[:, track_idx] = 0

        unmatched_dets = [i for i in range(num_dets) if i not in matched_dets]

        return matched_dets, matched_tracks, unmatched_dets

    def _smooth_bbox(
        self,
        history: List[List[int]],
        weights: Optional[List[float]] = None
    ) -> List[int]:
        if not history:
            return [0, 0, 0, 0]

        if weights is None:
            weights = [1.0] * len(history)

        total_weight = sum(weights)
        if total_weight == 0:
            return history[-1]

        x1 = int(sum(h[0] * w for h, w in zip(history, weights)) / total_weight)
        y1 = int(sum(h[1] * w for h, w in zip(history, weights)) / total_weight)
        x2 = int(sum(h[2] * w for h, w in zip(history, weights)) / total_weight)
        y2 = int(sum(h[3] * w for h, w in zip(history, weights)) / total_weight)

        return [x1, y1, x2, y2]

    def _smooth_confidence(self, history: List[float]) -> float:
        if not history:
            return 0.0

        weights = np.linspace(0.5, 1.0, len(history))
        weights = weights / weights.sum()

        return float(np.sum(np.array(history) * weights))

    def process(
        self,
        detections: List[DetectionResult],
        timestamp: Optional[float] = None
    ) -> List[StabilizedResult]:
        self.current_frame_id += 1
        current_time = timestamp or time.time()

        matched_dets, matched_tracks, unmatched_dets = self._match_detections(detections, self.tracks)

        for det_idx, track_id in zip(matched_dets, matched_tracks):
            det = detections[det_idx]
            track = self.tracks[track_id]

            track.detection = det
            track.frame_id = self.current_frame_id
            track.timestamp = current_time
            track.age = 0
            track.hit_count += 1
            track.confidence_history.append(det.confidence)
            if len(track.confidence_history) > self.window_size:
                track.confidence_history.pop(0)

            self.class_votes[track_id][det.class_id].append(det.confidence)

        for det_idx in unmatched_dets:
            det = detections[det_idx]
            new_track = TrackedDetection(
                detection=det,
                frame_id=self.current_frame_id,
                timestamp=current_time,
                track_id=self.next_track_id,
                confidence_history=[det.confidence]
            )
            self.tracks[self.next_track_id] = new_track
            self.class_votes[self.next_track_id][det.class_id].append(det.confidence)
            self.next_track_id += 1

        dead_tracks = []
        for track_id, track in self.tracks.items():
            track.age += 1
            if track.age > self.max_age:
                dead_tracks.append(track_id)

        for track_id in dead_tracks:
            del self.tracks[track_id]
            if track_id in self.class_votes:
                del self.class_votes[track_id]

        frame_data = {
            "frame_id": self.current_frame_id,
            "timestamp": current_time,
            "detections": detections,
            "tracks": dict(self.tracks)
        }
        self.frame_buffer.append(frame_data)

        return self._generate_stabilized_results()

    def _generate_stabilized_results(self) -> List[StabilizedResult]:
        results = []

        for track_id, track in self.tracks.items():
            if track.age > 0:
                continue

            hit_ratio = track.hit_count / (self.current_frame_id - track.frame_id + track.hit_count + 1)
            is_stable = track.hit_count >= self.min_frames_for_stable and hit_ratio >= self.min_hit_ratio

            smoothed_conf = self._smooth_confidence(track.confidence_history) if self.enable_smoothing else track.detection.confidence

            if self.enable_voting and track_id in self.class_votes:
                class_votes = self.class_votes[track_id]
                if class_votes:
                    voted_class_id = max(class_votes.keys(), key=lambda k: sum(class_votes[k]))
                    total_votes = sum(sum(v) for v in class_votes.values())
                    existence_conf = sum(class_votes.get(voted_class_id, [0])) / total_votes if total_votes > 0 else 0

                    if voted_class_id != track.detection.class_id:
                        track.detection.class_id = voted_class_id
                        from config import TRAFFIC_SIGN_CLASSES, CLASS_ZH_CN
                        if voted_class_id < len(TRAFFIC_SIGN_CLASSES):
                            track.detection.class_name = TRAFFIC_SIGN_CLASSES[voted_class_id]
                            track.detection.class_name_zh = CLASS_ZH_CN.get(track.detection.class_name, track.detection.class_name)
            else:
                existence_conf = smoothed_conf

            bbox_history = []
            for frame in list(self.frame_buffer)[-self.window_size:]:
                if track_id in frame["tracks"]:
                    bbox_history.append(frame["tracks"][track_id].detection.bbox)

            if len(bbox_history) >= 2 and self.enable_smoothing:
                weights = list(range(1, len(bbox_history) + 1))
                smoothed_bbox = self._smooth_bbox(bbox_history, weights)
                track.detection.bbox = smoothed_bbox

            result = StabilizedResult(
                detection=track.detection,
                track_id=track_id,
                smoothed_confidence=smoothed_conf,
                existence_confidence=existence_conf,
                frames_seen=track.hit_count,
                is_stable=is_stable
            )
            results.append(result)

        return results

    def get_tracking_stats(self) -> Dict:
        active_tracks = sum(1 for t in self.tracks.values() if t.age == 0)
        stable_tracks = sum(
            1 for t in self.tracks.values()
            if t.hit_count >= self.min_frames_for_stable
            and t.hit_count / max(1, (self.current_frame_id - t.frame_id + t.hit_count + 1)) >= self.min_hit_ratio
        )

        return {
            "current_frame": self.current_frame_id,
            "total_tracks": self.next_track_id,
            "active_tracks": active_tracks,
            "stable_tracks": stable_tracks,
            "window_size": self.window_size,
            "temporal_fusion_enabled": True
        }

    def reset(self):
        self.frame_buffer.clear()
        self.tracks.clear()
        self.class_votes.clear()
        self.next_track_id = 0
        self.current_frame_id = 0
