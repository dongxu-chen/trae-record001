import numpy as np
from typing import List, Optional, Tuple
from collections import deque
from scipy.spatial.distance import cdist
from scipy.optimize import linear_sum_assignment
from filterpy.kalman import KalmanFilter

from config import Config


def convert_bbox_to_z(bbox: np.ndarray) -> np.ndarray:
    w = bbox[2] - bbox[0]
    h = bbox[3] - bbox[1]
    x = bbox[0] + w / 2.
    y = bbox[1] + h / 2.
    s = w * h
    r = w / float(h)
    return np.array([x, y, s, r]).reshape((4, 1))


def convert_x_to_bbox(x: np.ndarray, score: Optional[float] = None) -> np.ndarray:
    w = np.sqrt(x[2] * x[3])
    h = x[2] / w
    if score is None:
        return np.array([x[0] - w / 2., x[1] - h / 2., x[0] + w / 2., x[1] + h / 2.]).reshape((1, 4))
    else:
        return np.array([x[0] - w / 2., x[1] - h / 2., x[0] + w / 2., x[1] + h / 2., score]).reshape((1, 5))


class KalmanBoxTracker:
    count = 0

    def __init__(self, bbox: np.ndarray, class_id: int, feature: np.ndarray):
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

        self.kf.R[2:, 2:] *= 10.
        self.kf.P[4:, 4:] *= 1000.
        self.kf.P *= 10.
        self.kf.Q[-1, -1] *= 0.01
        self.kf.Q[4:, 4:] *= 0.01

        self.kf.x[:4] = convert_bbox_to_z(bbox)

        self.time_since_update = 0
        self.id = KalmanBoxTracker.count
        KalmanBoxTracker.count += 1
        self.history: deque = deque(maxlen=Config.MAX_TRACK_LENGTH)
        self.hits = 0
        self.hit_streak = 0
        self.age = 0
        self.class_id = class_id
        self.features: deque = deque(maxlen=Config.NN_BUDGET)
        self.features.append(feature)
        self.trail: deque = deque(maxlen=Config.TRAIL_LENGTH)
        self.predicted_bbox_history: deque = deque(maxlen=10)
        self.measurement_residuals: deque = deque(maxlen=10)
        self.is_occluded = False
        self.occlusion_count = 0
        self.velocity = np.zeros(2)
        self.last_measurement = convert_bbox_to_z(bbox)
        self._update_trail()

    def _update_trail(self):
        bbox = convert_x_to_bbox(self.kf.x)[0]
        center_x = (bbox[0] + bbox[2]) / 2
        center_y = (bbox[1] + bbox[3]) / 2
        self.trail.append((center_x, center_y))

    def get_motion_uncertainty(self) -> float:
        return float(np.trace(self.kf.P[:2, :2]))

    def get_mean_feature(self) -> np.ndarray:
        if len(self.features) == 0:
            return np.zeros(128, dtype=np.float32)
        return np.mean(np.array(self.features), axis=0)

    def update(self, bbox: np.ndarray, class_id: int, feature: np.ndarray):
        prev_state = self.kf.x.copy()

        z = convert_bbox_to_z(bbox)
        residual = np.abs(z - self.last_measurement)
        self.measurement_residuals.append(np.linalg.norm(residual))

        self.kf.update(z)

        post_residual = np.abs(z - self.kf.x[:4])
        residual_norm = np.linalg.norm(post_residual)
        uncertainty = self.get_motion_uncertainty()

        self.is_occluded = (
            residual_norm > Config.MOTION_UNCERTAINTY_THRESHOLD or
            uncertainty > Config.MOTION_UNCERTAINTY_THRESHOLD * 2
        )
        if self.is_occluded:
            self.occlusion_count += 1
        else:
            self.occlusion_count = max(0, self.occlusion_count - 1)

        self.velocity = np.array([self.kf.x[4, 0], self.kf.x[5, 0]])

        self.time_since_update = 0
        self.history.clear()
        self.hits += 1
        self.hit_streak += 1
        self.class_id = class_id
        self.features.append(feature)
        self.last_measurement = z
        self._update_trail()

    def predict(self):
        if (self.kf.x[6] + self.kf.x[2]) <= 0:
            self.kf.x[6] *= 0.0

        if self.is_occluded and self.occlusion_count > 0:
            boost_factor = 1.0 + min(self.occlusion_count * 0.1, 0.5)
            self.kf.Q[4:6, 4:6] *= boost_factor

        self.kf.predict()
        self.age += 1
        if self.time_since_update > 0:
            self.hit_streak = 0
        self.time_since_update += 1

        predicted_bbox = convert_x_to_bbox(self.kf.x)
        self.predicted_bbox_history.append(predicted_bbox)
        self._update_trail()
        return predicted_bbox

    def get_state(self) -> np.ndarray:
        return convert_x_to_bbox(self.kf.x)

    def get_feature(self) -> np.ndarray:
        if self.is_occluded and len(self.features) > 1:
            return self.get_mean_feature()
        return self.features[-1]


def iou_batch(bb_test: np.ndarray, bb_gt: np.ndarray) -> np.ndarray:
    bb_gt = np.expand_dims(bb_gt, 0)
    bb_test = np.expand_dims(bb_test, 1)

    xx1 = np.maximum(bb_test[..., 0], bb_gt[..., 0])
    yy1 = np.maximum(bb_test[..., 1], bb_gt[..., 1])
    xx2 = np.minimum(bb_test[..., 2], bb_gt[..., 2])
    yy2 = np.minimum(bb_test[..., 3], bb_gt[..., 3])

    w = np.maximum(0., xx2 - xx1)
    h = np.maximum(0., yy2 - yy1)
    wh = w * h

    o = wh / ((bb_test[..., 2] - bb_test[..., 0]) * (bb_test[..., 3] - bb_test[..., 1])
              + (bb_gt[..., 2] - bb_gt[..., 0]) * (bb_gt[..., 3] - bb_gt[..., 1]) - wh)
    return o


def motion_distance(
    tracks: List[KalmanBoxTracker],
    detections: np.ndarray,
    track_indices: List[int],
    detection_indices: List[int],
) -> np.ndarray:
    if len(track_indices) == 0 or len(detection_indices) == 0:
        return np.empty((len(track_indices), len(detection_indices)))

    cost_matrix = np.zeros((len(track_indices), len(detection_indices)))

    for i, t_idx in enumerate(track_indices):
        track = tracks[t_idx]
        predicted_bbox = track.get_state()[0]
        pred_center = np.array([
            (predicted_bbox[0] + predicted_bbox[2]) / 2,
            (predicted_bbox[1] + predicted_bbox[3]) / 2,
        ])
        pred_size = np.array([
            predicted_bbox[2] - predicted_bbox[0],
            predicted_bbox[3] - predicted_bbox[1],
        ])

        uncertainty = track.get_motion_uncertainty()
        uncertainty_scale = 1.0 / (1.0 + uncertainty * 0.1)

        for j, d_idx in enumerate(detection_indices):
            det = detections[d_idx]
            det_center = np.array([(det[0] + det[2]) / 2, (det[1] + det[3]) / 2])
            det_size = np.array([det[2] - det[0], det[3] - det[1]])

            center_dist = np.linalg.norm(pred_center - det_center)
            size_dist = np.linalg.norm(pred_size - det_size)

            norm_center = center_dist / (np.mean(pred_size) + 1e-6)
            norm_size = size_dist / (np.mean(pred_size) + 1e-6)

            cost_matrix[i, j] = (norm_center + 0.5 * norm_size) * uncertainty_scale

    return cost_matrix


def feature_distance(
    tracks: List[KalmanBoxTracker],
    features: np.ndarray,
    track_indices: List[int],
    detection_indices: List[int],
) -> np.ndarray:
    if len(track_indices) == 0 or len(detection_indices) == 0:
        return np.empty((len(track_indices), len(detection_indices)))

    track_features = []
    for i in track_indices:
        track = tracks[i]
        feat = track.get_feature()
        if track.is_occluded and len(track.features) > 2:
            feat = track.get_mean_feature()
        track_features.append(feat)
    track_features = np.array(track_features)
    det_features = features[detection_indices]

    if track_features.ndim == 1:
        track_features = track_features.reshape(1, -1)
    if det_features.ndim == 1:
        det_features = det_features.reshape(1, -1)

    track_features = track_features / (np.linalg.norm(track_features, axis=1, keepdims=True) + 1e-6)
    det_features = det_features / (np.linalg.norm(det_features, axis=1, keepdims=True) + 1e-6)

    similarity = np.dot(track_features, det_features.T)
    cost_matrix = 1.0 - similarity

    for i, t_idx in enumerate(track_indices):
        if tracks[t_idx].is_occluded:
            cost_matrix[i, :] *= 0.7

    return cost_matrix


def associate_detections_to_trackers(
    detections: np.ndarray,
    features: np.ndarray,
    trackers: List[KalmanBoxTracker],
    max_cosine_distance: float = Config.MAX_COSINE_DISTANCE,
    max_iou_distance: float = Config.MAX_IOU_DISTANCE,
) -> Tuple[List[Tuple[int, int]], List[int], List[int]]:
    if len(trackers) == 0:
        return [], list(range(len(detections))), []

    tracker_indices = list(range(len(trackers)))
    detection_indices = list(range(len(detections)))

    feature_cost = feature_distance(trackers, features, tracker_indices, detection_indices)
    motion_cost = motion_distance(trackers, detections, tracker_indices, detection_indices)
    iou_cost = 1.0 - iou_batch(detections, np.array([t.get_state()[0] for t in trackers]))
    iou_cost = iou_cost.T

    w_feat = Config.FEATURE_MATCH_WEIGHT
    w_mot = Config.MOTION_PREDICT_WEIGHT
    w_iou = Config.IOU_MATCH_WEIGHT

    max_motion = np.max(motion_cost) if motion_cost.size > 0 else 1.0
    if max_motion > 0:
        motion_cost_norm = motion_cost / max_motion
    else:
        motion_cost_norm = motion_cost

    combined_cost = (
        w_feat * feature_cost
        + w_mot * motion_cost_norm
        + w_iou * iou_cost
    )

    for i, t_idx in enumerate(tracker_indices):
        track = trackers[t_idx]
        if track.is_occluded:
            occlusion_factor = 1.0 + min(track.occlusion_count * 0.1, 0.5)
            combined_cost[i, :] *= occlusion_factor
            combined_cost[i, :] = (
                0.2 * feature_cost[i, :]
                + 0.5 * motion_cost_norm[i, :]
                + 0.3 * iou_cost[i, :]
            )
        if track.time_since_update > 3:
            combined_cost[i, :] *= 1.5

    combined_cost[feature_cost > max_cosine_distance] = 1e5
    combined_cost[iou_cost > max_iou_distance] = 1e5

    if motion_cost_norm.size > 0:
        max_motion_thresh = 0.8
        combined_cost[motion_cost_norm > max_motion_thresh] = np.minimum(
            combined_cost[motion_cost_norm > max_motion_thresh],
            1e4
        )

    row_ind, col_ind = linear_sum_assignment(combined_cost)

    matched_indices = []
    unmatched_detections = []
    unmatched_trackers = []

    for i, j in zip(row_ind, col_ind):
        if combined_cost[i, j] < 1e4:
            matched_indices.append((i, j))

    matched_tracker_ids = {m[0] for m in matched_indices}
    matched_detection_ids = {m[1] for m in matched_indices}

    for d in detection_indices:
        if d not in matched_detection_ids:
            unmatched_detections.append(d)

    for t in tracker_indices:
        if t not in matched_tracker_ids:
            unmatched_trackers.append(t)

    unmatched_trackers_second = []
    for t in unmatched_trackers:
        track = trackers[t]
        if track.is_occluded and track.occlusion_count > 0 and track.hit_streak > 5:
            best_iou = 0
            best_d = -1
            for d in unmatched_detections:
                iou_val = iou_batch(
                    detections[d:d+1],
                    np.array([track.get_state()[0]])
                )[0, 0]
                if iou_val > best_iou and iou_val > 0.1:
                    best_iou = iou_val
                    best_d = d
            if best_d >= 0:
                matched_indices.append((t, best_d))
                unmatched_detections.remove(best_d)
                continue
        unmatched_trackers_second.append(t)

    return matched_indices, unmatched_detections, unmatched_trackers_second


class DeepSORT:
    def __init__(
        self,
        max_age: Optional[int] = None,
        n_init: Optional[int] = None,
        nn_budget: Optional[int] = None,
        max_cosine_distance: Optional[float] = None,
    ):
        self.max_age = max_age or Config.MAX_AGE
        self.n_init = n_init or Config.N_INIT
        self.nn_budget = nn_budget or Config.NN_BUDGET
        self.max_cosine_distance = max_cosine_distance or Config.MAX_COSINE_DISTANCE

        self.tracks: List[KalmanBoxTracker] = []
        self.last_update_bboxes: Optional[np.ndarray] = None
        self.last_update_features: Optional[np.ndarray] = None
        self.interpolation_enabled = Config.MOTION_INTERPOLATION_ENABLE

    def update(
        self,
        bboxes: np.ndarray,
        confidences: np.ndarray,
        class_ids: np.ndarray,
        features: np.ndarray,
    ) -> List[dict]:
        if len(bboxes) == 0:
            for track in self.tracks:
                track.predict()

            self.tracks = [track for track in self.tracks if track.time_since_update <= self.max_age]

            return self._get_active_tracks()

        for track in self.tracks:
            track.predict()

        matched_indices, unmatched_detections, unmatched_trackers = associate_detections_to_trackers(
            bboxes, features, self.tracks, self.max_cosine_distance
        )

        for track_idx, det_idx in matched_indices:
            self.tracks[track_idx].update(bboxes[det_idx], class_ids[det_idx], features[det_idx])

        for det_idx in unmatched_detections:
            new_track = KalmanBoxTracker(bboxes[det_idx], class_ids[det_idx], features[det_idx])
            self.tracks.append(new_track)

        self.tracks = [track for track in self.tracks if track.time_since_update <= self.max_age]

        self.last_update_bboxes = bboxes.copy()
        self.last_update_features = features.copy()

        return self._get_active_tracks()

    def predict_only(self) -> List[dict]:
        for track in self.tracks:
            track.predict()

        self.tracks = [track for track in self.tracks if track.time_since_update <= self.max_age]

        return self._get_active_tracks()

    def interpolate_bbox(
        self,
        prev_bbox: np.ndarray,
        curr_pred_bbox: np.ndarray,
        alpha: float,
    ) -> np.ndarray:
        if not self.interpolation_enabled:
            return curr_pred_bbox

        interpolated = prev_bbox * (1 - alpha) + curr_pred_bbox * alpha
        return interpolated

    def get_interpolated_tracks(self, alpha: float = 1.0) -> List[dict]:
        active_tracks = []
        for track in self.tracks:
            if track.hit_streak >= self.n_init or track.hits < self.n_init:
                bbox = track.get_state()[0]

                if self.interpolation_enabled and track.time_since_update > 0 and len(track.predicted_bbox_history) >= 2:
                    prev_bbox = track.predicted_bbox_history[-2][0]
                    curr_bbox = bbox
                    bbox = self.interpolate_bbox(prev_bbox, curr_bbox, alpha)

                track_info = {
                    "id": track.id,
                    "bbox": bbox,
                    "class_id": track.class_id,
                    "confidence": 1.0,
                    "trail": list(track.trail),
                    "age": track.age,
                    "hits": track.hits,
                    "is_predicted": track.time_since_update > 0,
                    "time_since_update": track.time_since_update,
                }
                active_tracks.append(track_info)
        return active_tracks

    def _get_active_tracks(self) -> List[dict]:
        active_tracks = []
        for track in self.tracks:
            if track.hit_streak >= self.n_init or track.hits < self.n_init:
                bbox = track.get_state()[0]
                active_tracks.append({
                    "id": track.id,
                    "bbox": bbox,
                    "class_id": track.class_id,
                    "confidence": 1.0,
                    "trail": list(track.trail),
                    "age": track.age,
                    "hits": track.hits,
                    "is_predicted": track.time_since_update > 0,
                    "time_since_update": track.time_since_update,
                })
        return active_tracks

    def reset(self):
        self.tracks = []
        KalmanBoxTracker.count = 0
        self.last_update_bboxes = None
        self.last_update_features = None
