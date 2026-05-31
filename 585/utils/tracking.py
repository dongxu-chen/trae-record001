import numpy as np
from typing import List, Optional, Tuple, Dict
from collections import OrderedDict
from dataclasses import dataclass, field
from scipy.optimize import linear_sum_assignment

try:
    from filterpy.kalman import KalmanFilter
    HAS_FILTERPY = True
except ImportError:
    HAS_FILTERPY = False


@dataclass
class TrackedPerson:
    track_id: int
    bbox: np.ndarray
    keypoints: List[Optional[object]]
    hits: int = 0
    age: int = 0
    time_since_update: int = 0
    kalman_filter: Optional[object] = None
    history: List[np.ndarray] = field(default_factory=list)


class KalmanTracker:
    def __init__(self, bbox: np.ndarray):
        if not HAS_FILTERPY:
            raise ImportError("filterpy is required for Kalman tracking")
        
        self.kf = KalmanFilter(dim_x=7, dim_z=4)
        self.kf.F = np.array([
            [1, 0, 0, 0, 1, 0, 0],
            [0, 1, 0, 0, 0, 1, 0],
            [0, 0, 1, 0, 0, 0, 1],
            [0, 0, 0, 1, 0, 0, 0],
            [0, 0, 0, 0, 1, 0, 0],
            [0, 0, 0, 0, 0, 1, 0],
            [0, 0, 0, 0, 0, 0, 1]
        ])
        self.kf.H = np.array([
            [1, 0, 0, 0, 0, 0, 0],
            [0, 1, 0, 0, 0, 0, 0],
            [0, 0, 1, 0, 0, 0, 0],
            [0, 0, 0, 1, 0, 0, 0]
        ])
        
        self.kf.R[2:, 2:] *= 10.0
        self.kf.P[4:, 4:] *= 1000.0
        self.kf.P *= 10.0
        self.kf.Q[-1, -1] *= 0.01
        self.kf.Q[4:, 4:] *= 0.01
        
        self.kf.x[:4] = self._convert_bbox_to_z(bbox)
    
    def _convert_bbox_to_z(self, bbox: np.ndarray) -> np.ndarray:
        x, y, w, h = bbox
        return np.array([x + w/2, y + h/2, w, h]).reshape(4, 1)
    
    def _convert_x_to_bbox(self, x: np.ndarray) -> np.ndarray:
        cx, cy, w, h = x[:4].flatten()
        return np.array([cx - w/2, cy - h/2, w, h])
    
    def predict(self) -> np.ndarray:
        if self.kf.x[6] + self.kf.x[2] <= 0:
            self.kf.x[6] *= 0.0
        self.kf.predict()
        return self._convert_x_to_bbox(self.kf.x)
    
    def update(self, bbox: np.ndarray):
        self.kf.update(self._convert_bbox_to_z(bbox))
    
    def get_state(self) -> np.ndarray:
        return self._convert_x_to_bbox(self.kf.x)


def iou(bbox1: np.ndarray, bbox2: np.ndarray) -> float:
    x1, y1, w1, h1 = bbox1
    x2, y2, w2, h2 = bbox2
    
    x1_max, y1_max = x1 + w1, y1 + h1
    x2_max, y2_max = x2 + w2, y2 + h2
    
    inter_x = max(x1, x2)
    inter_y = max(y1, y2)
    inter_x_max = min(x1_max, x2_max)
    inter_y_max = min(y1_max, y2_max)
    
    inter_w = max(0, inter_x_max - inter_x)
    inter_h = max(0, inter_y_max - inter_y)
    inter_area = inter_w * inter_h
    
    area1 = w1 * h1
    area2 = w2 * h2
    
    union_area = area1 + area2 - inter_area
    
    if union_area == 0:
        return 0.0
    
    return inter_area / union_area


def bbox_center_distance(bbox1: np.ndarray, bbox2: np.ndarray) -> float:
    cx1 = bbox1[0] + bbox1[2] / 2
    cy1 = bbox1[1] + bbox1[3] / 2
    cx2 = bbox2[0] + bbox2[2] / 2
    cy2 = bbox2[1] + bbox2[3] / 2
    
    return np.sqrt((cx1 - cx2) ** 2 + (cy1 - cy2) ** 2)


def keypoints_distance(kpts1: List[Optional[object]], 
                        kpts2: List[Optional[object]]) -> float:
    valid_kpts = []
    for k1, k2 in zip(kpts1, kpts2):
        if k1 is not None and k2 is not None:
            dist = np.sqrt((k1.x - k2.x) ** 2 + (k1.y - k2.y) ** 2)
            valid_kpts.append(dist)
    
    if len(valid_kpts) == 0:
        return float('inf')
    
    return float(np.mean(valid_kpts))


class MultiPersonTracker:
    def __init__(self, max_age: int = 30, min_hits: int = 3, 
                 iou_threshold: float = 0.3, use_kalman: bool = True):
        self.max_age = max_age
        self.min_hits = min_hits
        self.iou_threshold = iou_threshold
        self.use_kalman = use_kalman and HAS_FILTERPY
        
        self.tracks: Dict[int, TrackedPerson] = OrderedDict()
        self.next_id = 0
    
    def update(self, detections: List[object]) -> List[TrackedPerson]:
        if len(detections) == 0:
            tracks_to_remove = []
            for track_id, track in self.tracks.items():
                track.time_since_update += 1
                track.age += 1
                if track.time_since_update > self.max_age:
                    tracks_to_remove.append(track_id)
                if self.use_kalman and track.kalman_filter is not None:
                    track.kalman_filter.predict()
            
            for track_id in tracks_to_remove:
                del self.tracks[track_id]
            
            return self._get_active_tracks()
        
        detection_bboxes = np.array([np.array(d.bbox) for d in detections])
        detection_keypoints = [d.keypoints for d in detections]
        
        if len(self.tracks) == 0:
            for i in range(len(detections)):
                self._create_track(detection_bboxes[i], detection_keypoints[i])
            return self._get_active_tracks()
        
        track_bboxes = []
        track_ids = []
        for track_id, track in self.tracks.items():
            if self.use_kalman and track.kalman_filter is not None:
                predicted_bbox = track.kalman_filter.predict()
            else:
                predicted_bbox = track.bbox
            track_bboxes.append(predicted_bbox)
            track_ids.append(track_id)
        
        track_bboxes = np.array(track_bboxes)
        
        cost_matrix = self._compute_cost_matrix(
            track_bboxes, detection_bboxes,
            [t.keypoints for t in self.tracks.values()],
            detection_keypoints
        )
        
        if cost_matrix.size > 0:
            track_indices, det_indices = linear_sum_assignment(cost_matrix)
        else:
            track_indices, det_indices = [], []
        
        matched_tracks = set()
        matched_detections = set()
        
        for track_idx, det_idx in zip(track_indices, det_indices):
            if cost_matrix[track_idx, det_idx] < 1.0:
                track_id = track_ids[track_idx]
                self._update_track(track_id, detection_bboxes[det_idx], detection_keypoints[det_idx])
                matched_tracks.add(track_id)
                matched_detections.add(det_idx)
        
        for track_id in list(self.tracks.keys()):
            if track_id not in matched_tracks:
                self.tracks[track_id].time_since_update += 1
                self.tracks[track_id].age += 1
                if self.tracks[track_id].time_since_update > self.max_age:
                    del self.tracks[track_id]
        
        for det_idx in range(len(detections)):
            if det_idx not in matched_detections:
                self._create_track(detection_bboxes[det_idx], detection_keypoints[det_idx])
        
        return self._get_active_tracks()
    
    def _compute_cost_matrix(self, track_bboxes: np.ndarray, 
                            det_bboxes: np.ndarray,
                            track_keypoints: List[List[Optional[object]]],
                            det_keypoints: List[List[Optional[object]]]) -> np.ndarray:
        num_tracks = len(track_bboxes)
        num_dets = len(det_bboxes)
        
        if num_tracks == 0 or num_dets == 0:
            return np.zeros((0, 0))
        
        cost_matrix = np.ones((num_tracks, num_dets))
        
        for i in range(num_tracks):
            for j in range(num_dets):
                iou_score = iou(track_bboxes[i], det_bboxes[j])
                if iou_score >= self.iou_threshold:
                    kpt_dist = keypoints_distance(track_keypoints[i], det_keypoints[j])
                    normalized_dist = min(kpt_dist / 100.0, 1.0)
                    cost_matrix[i, j] = 0.5 * (1 - iou_score) + 0.5 * normalized_dist
        
        return cost_matrix
    
    def _create_track(self, bbox: np.ndarray, keypoints: List[Optional[object]]):
        kalman = None
        if self.use_kalman:
            try:
                kalman = KalmanTracker(bbox)
            except Exception:
                kalman = None
        
        track = TrackedPerson(
            track_id=self.next_id,
            bbox=bbox.copy(),
            keypoints=keypoints,
            hits=1,
            age=1,
            time_since_update=0,
            kalman_filter=kalman,
            history=[bbox.copy()]
        )
        
        self.tracks[self.next_id] = track
        self.next_id += 1
    
    def _update_track(self, track_id: int, bbox: np.ndarray, 
                      keypoints: List[Optional[object]]):
        track = self.tracks[track_id]
        track.bbox = bbox.copy()
        track.keypoints = keypoints
        track.hits += 1
        track.age += 1
        track.time_since_update = 0
        
        if track.kalman_filter is not None:
            track.kalman_filter.update(bbox)
            track.bbox = track.kalman_filter.get_state()
        
        track.history.append(track.bbox.copy())
        if len(track.history) > 100:
            track.history = track.history[-100:]
    
    def _get_active_tracks(self) -> List[TrackedPerson]:
        return [t for t in self.tracks.values() 
                if t.hits >= self.min_hits or t.age <= self.max_age]
    
    def reset(self):
        self.tracks.clear()
        self.next_id = 0
