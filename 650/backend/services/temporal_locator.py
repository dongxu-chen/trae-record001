import numpy as np
import threading
from collections import deque
from typing import List, Tuple, Optional, Dict, Any


class TemporalLocator:
    def __init__(
        self,
        window_size: int = 30,
        min_duration: float = 0.5,
        merge_threshold: float = 0.3,
        high_threshold: float = 0.7,
        low_threshold: float = 0.3
    ):
        self._window_size = window_size
        self._min_duration = min_duration
        self._merge_threshold = merge_threshold
        self._high_threshold = high_threshold
        self._low_threshold = low_threshold

        self._prediction_history: deque = deque(maxlen=window_size * 10)
        self._timestamp_history: deque = deque(maxlen=window_size * 10)
        self._lock = threading.Lock()

        self._gaussian_kernel = self._create_gaussian_kernel(sigma=1.5)
        self._active_actions: List[Dict[str, Any]] = []

    def _create_gaussian_kernel(self, sigma: float = 1.5, size: int = 5) -> np.ndarray:
        x = np.linspace(-(size // 2), size // 2, size)
        kernel = np.exp(-x**2 / (2 * sigma**2))
        return kernel / kernel.sum()

    def _gaussian_smooth(self, values: np.ndarray) -> np.ndarray:
        if len(values) < len(self._gaussian_kernel):
            return values
        return np.convolve(values, self._gaussian_kernel, mode='same')

    def update(self, prediction: np.ndarray, timestamp: float) -> None:
        with self._lock:
            if prediction.ndim > 1:
                prediction = prediction[0]

            self._prediction_history.append(prediction)
            self._timestamp_history.append(timestamp)

    def _double_threshold_detection(
        self,
        confidences: np.ndarray,
        timestamps: np.ndarray
    ) -> List[Tuple[float, float, int, float]]:
        if len(confidences) == 0:
            return []

        num_classes = confidences.shape[1] if confidences.ndim > 1 else 1
        detected_segments = []

        for class_idx in range(num_classes):
            class_conf = confidences[:, class_idx] if confidences.ndim > 1 else confidences

            smoothed_conf = self._gaussian_smooth(class_conf)

            high_mask = smoothed_conf >= self._high_threshold
            low_mask = smoothed_conf >= self._low_threshold

            segments = []
            current_segment = None

            for i in range(len(smoothed_conf)):
                if high_mask[i] and current_segment is None:
                    current_segment = {
                        'start_idx': i,
                        'confidences': [smoothed_conf[i]]
                    }
                elif current_segment is not None:
                    if low_mask[i]:
                        current_segment['confidences'].append(smoothed_conf[i])
                    else:
                        if len(current_segment['confidences']) > 0:
                            end_idx = i - 1
                            start_time = timestamps[current_segment['start_idx']]
                            end_time = timestamps[end_idx]
                            avg_conf = np.mean(current_segment['confidences'])

                            if end_time - start_time >= self._min_duration:
                                segments.append((
                                    start_time,
                                    end_time,
                                    class_idx,
                                    avg_conf
                                ))

                        current_segment = None

            if current_segment is not None and len(current_segment['confidences']) > 0:
                end_idx = len(smoothed_conf) - 1
                start_time = timestamps[current_segment['start_idx']]
                end_time = timestamps[end_idx]
                avg_conf = np.mean(current_segment['confidences'])

                if end_time - start_time >= self._min_duration:
                    segments.append((
                        start_time,
                        end_time,
                        class_idx,
                        avg_conf
                    ))

            detected_segments.extend(segments)

        return detected_segments

    def _merge_segments(
        self,
        segments: List[Tuple[float, float, int, float]]
    ) -> List[Tuple[float, float, int, float]]:
        if len(segments) <= 1:
            return segments

        segments.sort(key=lambda x: (x[2], x[0]))

        merged = []
        current_group = [segments[0]]

        for i in range(1, len(segments)):
            seg = segments[i]
            last_seg = current_group[-1]

            if seg[2] == last_seg[2] and seg[0] - last_seg[1] <= self._merge_threshold:
                current_group.append(seg)
            else:
                if len(current_group) == 1:
                    merged.append(current_group[0])
                else:
                    start_time = current_group[0][0]
                    end_time = current_group[-1][1]
                    action = current_group[0][2]
                    avg_conf = np.mean([s[3] for s in current_group])
                    merged.append((start_time, end_time, action, avg_conf))
                current_group = [seg]

        if len(current_group) == 1:
            merged.append(current_group[0])
        else:
            start_time = current_group[0][0]
            end_time = current_group[-1][1]
            action = current_group[0][2]
            avg_conf = np.mean([s[3] for s in current_group])
            merged.append((start_time, end_time, action, avg_conf))

        return merged

    def _filter_segments(
        self,
        segments: List[Tuple[float, float, int, float]]
    ) -> List[Tuple[float, float, int, float]]:
        filtered = []

        for seg in segments:
            start_time, end_time, action, avg_conf = seg
            duration = end_time - start_time

            if duration >= self._min_duration:
                filtered.append(seg)

        return filtered

    def detect_actions(self) -> List[Dict[str, Any]]:
        with self._lock:
            if len(self._prediction_history) < self._window_size:
                return []

            predictions = np.array(list(self._prediction_history))
            timestamps = np.array(list(self._timestamp_history))

            if predictions.ndim == 1:
                predictions = predictions.reshape(-1, 1)

            segments = self._double_threshold_detection(predictions, timestamps)
            segments = self._merge_segments(segments)
            segments = self._filter_segments(segments)

            actions = []
            for seg in segments:
                start_time, end_time, action, avg_conf = seg
                actions.append({
                    "start_time": float(start_time),
                    "end_time": float(end_time),
                    "action": int(action),
                    "avg_confidence": float(avg_conf),
                    "duration": float(end_time - start_time)
                })

            return actions

    def get_smoothed_predictions(self) -> Optional[Tuple[np.ndarray, np.ndarray]]:
        with self._lock:
            if len(self._prediction_history) == 0:
                return None

            predictions = np.array(list(self._prediction_history))
            timestamps = np.array(list(self._timestamp_history))

            if predictions.ndim == 1:
                predictions = predictions.reshape(-1, 1)

            smoothed = np.zeros_like(predictions)
            for class_idx in range(predictions.shape[1]):
                smoothed[:, class_idx] = self._gaussian_smooth(predictions[:, class_idx])

            return smoothed, timestamps

    def get_history_size(self) -> int:
        with self._lock:
            return len(self._prediction_history)

    def clear_history(self) -> None:
        with self._lock:
            self._prediction_history.clear()
            self._timestamp_history.clear()
            self._active_actions.clear()

    def is_ready(self) -> bool:
        with self._lock:
            return len(self._prediction_history) >= self._window_size
