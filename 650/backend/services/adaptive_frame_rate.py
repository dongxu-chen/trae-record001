import cv2
import numpy as np
import threading
from collections import deque
from typing import List, Optional, Tuple, Deque


class MotionEstimator:
    def __init__(self, grid_size: int = 20):
        self._grid_size = grid_size
        self._prev_frame: Optional[np.ndarray] = None
        self._prev_pts: Optional[np.ndarray] = None

    def calculate_motion_magnitude(
        self,
        current_frame: np.ndarray,
        prev_frame: Optional[np.ndarray] = None
    ) -> float:
        try:
            gray = cv2.cvtColor(current_frame, cv2.COLOR_BGR2GRAY)

            if prev_frame is not None:
                self._prev_frame = prev_frame
            elif self._prev_frame is None:
                self._prev_frame = gray
                return 0.0

            prev_gray = self._prev_frame if self._prev_frame.ndim == 2 else \
                cv2.cvtColor(self._prev_frame, cv2.COLOR_BGR2GRAY)

            flow = cv2.calcOpticalFlowFarneback(
                prev_gray, gray,
                None,
                0.5, 3, 15, 3, 5, 1.2, 0
            )

            magnitude, _ = cv2.cartToPolar(flow[..., 0], flow[..., 1])
            motion_mag = float(np.mean(magnitude))

            self._prev_frame = gray.copy()

            return motion_mag

        except Exception as e:
            print(f"Motion estimation error: {e}")
            return 0.0

    def reset(self) -> None:
        self._prev_frame = None
        self._prev_pts = None


class AdaptiveFrameRateController:
    def __init__(
        self,
        min_fps: int = 8,
        max_fps: int = 60,
        base_fps: int = 16,
        motion_threshold_low: float = 2.0,
        motion_threshold_high: float = 8.0,
        adaptation_speed: float = 0.3,
        window_size: int = 10
    ):
        self._min_fps = min_fps
        self._max_fps = max_fps
        self._base_fps = base_fps
        self._current_fps = base_fps
        self._motion_threshold_low = motion_threshold_low
        self._motion_threshold_high = motion_threshold_high
        self._adaptation_speed = adaptation_speed
        self._window_size = window_size

        self._motion_history: Deque[float] = deque(maxlen=window_size)
        self._motion_estimator = MotionEstimator()
        self._lock = threading.Lock()

        self._frame_count_since_last_sample = 0
        self._last_sample_time = 0.0

    def update_motion(self, frame: np.ndarray) -> float:
        with self._lock:
            motion_mag = self._motion_estimator.calculate_motion_magnitude(frame)
            self._motion_history.append(motion_mag)
            self._adapt_fps()
            return motion_mag

    def _adapt_fps(self) -> None:
        if len(self._motion_history) < 3:
            return

        avg_motion = np.mean(list(self._motion_history)[-3:])
        motion_variance = np.var(list(self._motion_history)[-5:]) if len(self._motion_history) >= 5 else 0

        target_fps = self._base_fps

        if avg_motion > self._motion_threshold_high:
            motion_factor = (avg_motion - self._motion_threshold_high) / 10.0
            target_fps = self._base_fps + (self._max_fps - self._base_fps) * min(1.0, motion_factor)
        elif avg_motion < self._motion_threshold_low:
            target_fps = self._min_fps + (self._base_fps - self._min_fps) * \
                (avg_motion / self._motion_threshold_low)

        if motion_variance > 5.0:
            target_fps *= 1.2

        target_fps = max(self._min_fps, min(self._max_fps, target_fps))

        self._current_fps = int(
            self._current_fps * (1 - self._adaptation_speed) +
            target_fps * self._adaptation_speed
        )

    def should_sample_frame(self, current_time: float) -> bool:
        with self._lock:
            if self._current_fps <= 0:
                return True

            sampling_interval = 1.0 / self._current_fps

            if current_time - self._last_sample_time >= sampling_interval:
                self._last_sample_time = current_time
                return True

            self._frame_count_since_last_sample += 1
            return False

    def get_current_fps(self) -> int:
        with self._lock:
            return self._current_fps

    def get_average_motion(self) -> float:
        with self._lock:
            if not self._motion_history:
                return 0.0
            return float(np.mean(list(self._motion_history)))

    def reset(self) -> None:
        with self._lock:
            self._current_fps = self._base_fps
            self._motion_history.clear()
            self._motion_estimator.reset()
            self._frame_count_since_last_sample = 0
            self._last_sample_time = 0.0


class AdaptiveFrameProcessor:
    def __init__(
        self,
        target_size: Tuple[int, int] = (224, 224),
        min_fps: int = 8,
        max_fps: int = 60,
        base_fps: int = 16,
        window_size: int = 60
    ):
        self._target_size = target_size
        self._window_size = window_size

        self._frame_controller = AdaptiveFrameRateController(
            min_fps=min_fps,
            max_fps=max_fps,
            base_fps=base_fps
        )

        self._raw_buffer: Deque[Tuple[np.ndarray, float]] = deque(maxlen=window_size * 2)
        self._processed_buffer: Deque[Tuple[np.ndarray, float]] = deque(maxlen=window_size)
        self._lock = threading.Lock()

        self._mean = np.array([0.485, 0.456, 0.406], dtype=np.float32)
        self._std = np.array([0.229, 0.224, 0.225], dtype=np.float32)

    def add_frame(self, frame: np.ndarray, timestamp: float) -> bool:
        with self._lock:
            motion_mag = self._frame_controller.update_motion(frame)

            self._raw_buffer.append((frame.copy(), timestamp))

            if self._frame_controller.should_sample_frame(timestamp):
                processed_frame = self._process_frame(frame)
                self._processed_buffer.append((processed_frame, timestamp))
                return True

            return False

    def _process_frame(self, frame: np.ndarray) -> np.ndarray:
        try:
            if frame is None:
                raise ValueError("Frame is None")

            processed = cv2.resize(frame, self._target_size)
            processed = cv2.cvtColor(processed, cv2.COLOR_BGR2RGB)
            processed = processed.astype(np.float32) / 255.0
            processed = (processed - self._mean) / self._std
            processed = processed.transpose(2, 0, 1)

            return processed
        except Exception as e:
            print(f"Error processing frame: {e}")
            raise

    def get_current_fps(self) -> int:
        with self._lock:
            return self._frame_controller.get_current_fps()

    def get_motion_level(self) -> float:
        with self._lock:
            return self._frame_controller.get_average_motion()

    def assemble_clip(
        self,
        num_frames: int = 16,
        sampling_rate: int = 1
    ) -> Optional[Tuple[np.ndarray, List[float]]]:
        with self._lock:
            if len(self._processed_buffer) < num_frames * sampling_rate:
                return None

            frames = list(self._processed_buffer)
            indices = list(range(0, num_frames * sampling_rate, sampling_rate))
            selected_frames = [frames[-num_frames * sampling_rate + i] for i in indices]

            clip_frames = [f[0] for f in selected_frames]
            timestamps = [f[1] for f in selected_frames]

            clip_tensor = np.stack(clip_frames, axis=0)
            clip_tensor = clip_tensor.transpose(1, 0, 2, 3)

            return clip_tensor, timestamps

    def sliding_window_sample(
        self,
        step: int = 8,
        num_frames: int = 16,
        sampling_rate: int = 1
    ) -> List[Tuple[np.ndarray, List[float]]]:
        with self._lock:
            required_frames = num_frames * sampling_rate
            if len(self._processed_buffer) < required_frames:
                return []

            all_frames = list(self._processed_buffer)
            clips = []

            for i in range(0, len(all_frames) - required_frames + 1, step):
                indices = list(range(i, i + num_frames * sampling_rate, sampling_rate))
                if indices[-1] >= len(all_frames):
                    break

                selected_frames = [all_frames[j] for j in indices]
                clip_frames = [f[0] for f in selected_frames]
                timestamps = [f[1] for f in selected_frames]

                clip_tensor = np.stack(clip_frames, axis=0)
                clip_tensor = clip_tensor.transpose(1, 0, 2, 3)

                clips.append((clip_tensor, timestamps))

            return clips

    def get_buffer_size(self) -> int:
        with self._lock:
            return len(self._processed_buffer)

    def clear_buffer(self) -> None:
        with self._lock:
            self._raw_buffer.clear()
            self._processed_buffer.clear()
            self._frame_controller.reset()

    def is_ready(self, num_frames: int = 16, sampling_rate: int = 1) -> bool:
        with self._lock:
            return len(self._processed_buffer) >= num_frames * sampling_rate
