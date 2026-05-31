import numpy as np
import threading
from collections import deque
from typing import List, Tuple, Optional, Dict, Any
from scipy import signal
from scipy.ndimage import gaussian_filter1d


class PeakDetector:
    def __init__(
        self,
        min_distance: int = 10,
        min_prominence: float = 0.2,
        width_range: Tuple[int, int] = (3, 50)
    ):
        self._min_distance = min_distance
        self._min_prominence = min_prominence
        self._width_range = width_range

    def detect_peaks(
        self,
        confidence_curve: np.ndarray,
        height: Optional[float] = None
    ) -> Tuple[np.ndarray, Dict[str, np.ndarray]]:
        if len(confidence_curve) < 5:
            return np.array([]), {}

        peaks, properties = signal.find_peaks(
            confidence_curve,
            height=height,
            distance=self._min_distance,
            prominence=self._min_prominence,
            width=self._width_range
        )

        return peaks, properties

    def detect_valleys(
        self,
        confidence_curve: np.ndarray
    ) -> np.ndarray:
        if len(confidence_curve) < 5:
            return np.array([])

        inverted = -confidence_curve
        valleys, _ = signal.find_peaks(
            inverted,
            distance=self._min_distance,
            prominence=self._min_prominence * 0.5
        )

        return valleys


class BoundaryRegressor:
    def __init__(
        self,
        rising_edge_threshold: float = 0.3,
        falling_edge_threshold: float = 0.3,
        smooth_sigma: float = 1.5
    ):
        self._rising_edge_threshold = rising_edge_threshold
        self._falling_edge_threshold = falling_edge_threshold
        self._smooth_sigma = smooth_sigma

    def _compute_gradient(self, curve: np.ndarray) -> np.ndarray:
        if len(curve) < 2:
            return np.zeros_like(curve)
        return np.gradient(curve)

    def _smooth_curve(self, curve: np.ndarray) -> np.ndarray:
        if len(curve) < 3:
            return curve
        return gaussian_filter1d(curve, sigma=self._smooth_sigma)

    def find_rising_edge(
        self,
        confidence_curve: np.ndarray,
        peak_idx: int,
        search_left: int = 30
    ) -> int:
        if len(confidence_curve) == 0:
            return 0

        start_search = max(0, peak_idx - search_left)
        end_search = peak_idx

        smoothed = self._smooth_curve(confidence_curve[start_search:end_search + 1])
        gradient = self._compute_gradient(smoothed)

        if len(gradient) == 0:
            return start_search

        max_grad_idx = np.argmax(gradient)
        boundary_idx = start_search + max_grad_idx

        for i in range(boundary_idx, start_search - 1, -1):
            if confidence_curve[i] <= self._rising_edge_threshold:
                boundary_idx = i
                break

        return max(0, boundary_idx)

    def find_falling_edge(
        self,
        confidence_curve: np.ndarray,
        peak_idx: int,
        search_right: int = 30
    ) -> int:
        if len(confidence_curve) == 0:
            return 0

        start_search = peak_idx
        end_search = min(len(confidence_curve) - 1, peak_idx + search_right)

        if start_search >= end_search:
            return end_search

        smoothed = self._smooth_curve(confidence_curve[start_search:end_search + 1])
        gradient = self._compute_gradient(smoothed)

        if len(gradient) == 0:
            return end_search

        min_grad_idx = np.argmin(gradient)
        boundary_idx = start_search + min_grad_idx

        for i in range(boundary_idx, end_search + 1):
            if confidence_curve[i] <= self._falling_edge_threshold:
                boundary_idx = i
                break

        return min(len(confidence_curve) - 1, boundary_idx)

    def refine_boundary(
        self,
        confidence_curve: np.ndarray,
        boundary_idx: int,
        window_size: int = 5,
        is_rising: bool = True
    ) -> int:
        start = max(0, boundary_idx - window_size)
        end = min(len(confidence_curve) - 1, boundary_idx + window_size)

        if start >= end:
            return boundary_idx

        local_curve = confidence_curve[start:end + 1]
        gradient = self._compute_gradient(local_curve)

        if is_rising:
            refined_local = np.argmax(gradient)
        else:
            refined_local = np.argmin(gradient)

        return start + refined_local


class PrecisionTemporalLocator:
    def __init__(
        self,
        num_classes: int = 8,
        min_duration: float = 0.3,
        max_duration: float = 10.0,
        peak_min_distance: int = 15,
        peak_min_prominence: float = 0.15,
        rising_edge_threshold: float = 0.25,
        falling_edge_threshold: float = 0.25,
        smooth_sigma: float = 2.0,
        history_size: int = 500
    ):
        self._num_classes = num_classes
        self._min_duration = min_duration
        self._max_duration = max_duration
        self._history_size = history_size

        self._peak_detector = PeakDetector(
            min_distance=peak_min_distance,
            min_prominence=peak_min_prominence
        )
        self._boundary_regressor = BoundaryRegressor(
            rising_edge_threshold=rising_edge_threshold,
            falling_edge_threshold=falling_edge_threshold,
            smooth_sigma=smooth_sigma
        )

        self._confidence_matrix: deque = deque(maxlen=history_size)
        self._timestamp_history: deque = deque(maxlen=history_size)
        self._lock = threading.Lock()

        self._detected_actions: List[Dict[str, Any]] = []
        self._last_processed_idx = 0

        self._gaussian_sigma = 2.0

    def update(self, predictions: np.ndarray, timestamp: float) -> None:
        with self._lock:
            if predictions.ndim == 1:
                if len(predictions) != self._num_classes:
                    confidences = np.zeros(self._num_classes, dtype=np.float32)
                    confidences[0] = float(predictions[0]) if len(predictions) > 0 else 0.0
                else:
                    confidences = predictions.astype(np.float32)
            else:
                confidences = predictions[0].astype(np.float32)

            if len(confidences) < self._num_classes:
                padded = np.zeros(self._num_classes, dtype=np.float32)
                padded[:len(confidences)] = confidences
                confidences = padded

            self._confidence_matrix.append(confidences)
            self._timestamp_history.append(timestamp)

    def _idx_to_time(self, idx: int) -> float:
        if idx < 0 or idx >= len(self._timestamp_history):
            return 0.0
        return self._timestamp_history[idx]

    def _smooth_confidence_curve(self, curve: np.ndarray) -> np.ndarray:
        if len(curve) < 3:
            return curve
        return gaussian_filter1d(curve, sigma=self._gaussian_sigma)

    def _detect_action_segments_for_class(
        self,
        class_idx: int,
        confidences: np.ndarray,
        timestamps: np.ndarray
    ) -> List[Dict[str, Any]]:
        if len(confidences) < 10:
            return []

        smoothed = self._smooth_confidence_curve(confidences)

        height_threshold = np.mean(smoothed) + np.std(smoothed) * 0.5
        height_threshold = max(0.3, height_threshold)

        peaks, peak_props = self._peak_detector.detect_peaks(
            smoothed,
            height=height_threshold
        )

        if len(peaks) == 0:
            return []

        segments = []

        for i, peak_idx in enumerate(peaks):
            peak_confidence = float(smoothed[peak_idx])

            start_idx = self._boundary_regressor.find_rising_edge(
                smoothed, peak_idx, search_left=40
            )
            end_idx = self._boundary_regressor.find_falling_edge(
                smoothed, peak_idx, search_right=40
            )

            start_idx = self._boundary_regressor.refine_boundary(
                smoothed, start_idx, window_size=8, is_rising=True
            )
            end_idx = self._boundary_regressor.refine_boundary(
                smoothed, end_idx, window_size=8, is_rising=False
            )

            start_time = self._idx_to_time(start_idx)
            end_time = self._idx_to_time(end_idx)
            duration = end_time - start_time

            if duration < self._min_duration:
                continue
            if duration > self._max_duration:
                end_time = start_time + self._max_duration
                duration = self._max_duration

            segment_confidences = smoothed[start_idx:end_idx + 1]
            if len(segment_confidences) > 0:
                avg_confidence = float(np.mean(segment_confidences))
                peak_confidence = float(np.max(segment_confidences))
            else:
                avg_confidence = peak_confidence
                peak_confidence = peak_confidence

            segment = {
                'class_idx': class_idx,
                'start_idx': start_idx,
                'end_idx': end_idx,
                'start_time': float(start_time),
                'end_time': float(end_time),
                'duration': float(duration),
                'avg_confidence': avg_confidence,
                'peak_confidence': peak_confidence,
                'peak_time': float(self._idx_to_time(peak_idx))
            }

            segments.append(segment)

        return segments

    def _merge_overlapping_segments(
        self,
        segments: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        if len(segments) <= 1:
            return segments

        segments.sort(key=lambda x: (x['class_idx'], x['start_time']))

        merged = []
        i = 0

        while i < len(segments):
            current = segments[i]
            j = i + 1

            while j < len(segments):
                next_seg = segments[j]

                if next_seg['class_idx'] != current['class_idx']:
                    break

                overlap = current['end_time'] - next_seg['start_time']

                if overlap >= -0.1:
                    current['end_time'] = max(current['end_time'], next_seg['end_time'])
                    current['end_idx'] = max(current['end_idx'], next_seg['end_idx'])
                    current['duration'] = current['end_time'] - current['start_time']

                    current['avg_confidence'] = (
                        current['avg_confidence'] * current['duration'] +
                        next_seg['avg_confidence'] * next_seg['duration']
                    ) / (current['duration'] + next_seg['duration'])

                    current['peak_confidence'] = max(
                        current['peak_confidence'],
                        next_seg['peak_confidence']
                    )
                else:
                    break

                j += 1

            merged.append(current)
            i = j

        return merged

    def _remove_duplicate_segments(
        self,
        segments: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        segments.sort(key=lambda x: x['peak_confidence'], reverse=True)

        unique_segments = []
        used_indices = set()

        for seg in segments:
            seg_key = (seg['class_idx'], seg['start_idx'], seg['end_idx'])
            if seg_key in used_indices:
                continue

            is_duplicate = False
            for existing in unique_segments:
                if existing['class_idx'] != seg['class_idx']:
                    continue

                overlap_start = max(seg['start_time'], existing['start_time'])
                overlap_end = min(seg['end_time'], existing['end_time'])
                overlap_duration = max(0, overlap_end - overlap_start)

                if overlap_duration > 0:
                    overlap_ratio = overlap_duration / min(
                        seg['duration'], existing['duration']
                    )
                    if overlap_ratio > 0.7:
                        is_duplicate = True
                        break

            if not is_duplicate:
                unique_segments.append(seg)
                used_indices.add(seg_key)

        unique_segments.sort(key=lambda x: x['start_time'])
        return unique_segments

    def detect_actions(self) -> List[Dict[str, Any]]:
        with self._lock:
            if len(self._confidence_matrix) < 20:
                return []

            conf_matrix = np.array(list(self._confidence_matrix))
            timestamps = np.array(list(self._timestamp_history))

            all_segments = []

            for class_idx in range(self._num_classes):
                class_confidences = conf_matrix[:, class_idx]
                segments = self._detect_action_segments_for_class(
                    class_idx, class_confidences, timestamps
                )
                all_segments.extend(segments)

            all_segments = self._merge_overlapping_segments(all_segments)
            all_segments = self._remove_duplicate_segments(all_segments)

            new_actions = []
            for seg in all_segments:
                if seg['start_idx'] >= self._last_processed_idx - 5:
                    action = {
                        'start_time': seg['start_time'],
                        'end_time': seg['end_time'],
                        'action': seg['class_idx'],
                        'avg_confidence': seg['avg_confidence'],
                        'peak_confidence': seg['peak_confidence'],
                        'duration': seg['duration'],
                        'peak_time': seg['peak_time']
                    }
                    new_actions.append(action)

            if len(self._timestamp_history) > 0:
                self._last_processed_idx = len(self._timestamp_history) - 1

            return new_actions

    def get_confidence_curve(self, class_idx: int) -> Optional[Tuple[np.ndarray, np.ndarray]]:
        with self._lock:
            if len(self._confidence_matrix) == 0:
                return None

            conf_matrix = np.array(list(self._confidence_matrix))
            timestamps = np.array(list(self._timestamp_history))

            if class_idx >= conf_matrix.shape[1]:
                return None

            return conf_matrix[:, class_idx], timestamps

    def get_history_size(self) -> int:
        with self._lock:
            return len(self._confidence_matrix)

    def clear_history(self) -> None:
        with self._lock:
            self._confidence_matrix.clear()
            self._timestamp_history.clear()
            self._detected_actions.clear()
            self._last_processed_idx = 0

    def is_ready(self) -> bool:
        with self._lock:
            return len(self._confidence_matrix) >= 30
