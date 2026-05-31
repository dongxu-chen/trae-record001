import cv2
import numpy as np
import threading
from collections import deque
from typing import List, Optional, Tuple, Deque


class FrameProcessor:
    def __init__(self, target_size: Tuple[int, int] = (224, 224), window_size: int = 30):
        self._target_size = target_size
        self._window_size = window_size
        self._frame_buffer: Deque[Tuple[np.ndarray, float]] = deque(maxlen=window_size)
        self._lock = threading.Lock()
        self._mean = np.array([0.485, 0.456, 0.406], dtype=np.float32)
        self._std = np.array([0.229, 0.224, 0.225], dtype=np.float32)

    def process(self, frame: np.ndarray) -> np.ndarray:
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

    def add_frame(self, frame: np.ndarray, timestamp: float) -> None:
        with self._lock:
            processed_frame = self.process(frame)
            self._frame_buffer.append((processed_frame, timestamp))

    def assemble_clip(self, frames: Optional[List[Tuple[np.ndarray, float]]] = None) -> Optional[Tuple[np.ndarray, List[float]]]:
        try:
            if frames is None:
                with self._lock:
                    if len(self._frame_buffer) < self._window_size:
                        return None
                    frames = list(self._frame_buffer)

            if len(frames) < self._window_size:
                return None

            clip_frames = [f[0] for f in frames[-self._window_size:]]
            timestamps = [f[1] for f in frames[-self._window_size:]]

            clip_tensor = np.stack(clip_frames, axis=0)
            clip_tensor = clip_tensor.transpose(1, 0, 2, 3)

            return clip_tensor, timestamps
        except Exception as e:
            print(f"Error assembling clip: {e}")
            return None

    def sliding_window_sample(self, step: int = 1) -> List[Tuple[np.ndarray, List[float]]]:
        with self._lock:
            if len(self._frame_buffer) < self._window_size:
                return []

            all_frames = list(self._frame_buffer)
            clips = []

            for i in range(0, len(all_frames) - self._window_size + 1, step):
                window_frames = all_frames[i:i + self._window_size]
                clip = self.assemble_clip(window_frames)
                if clip is not None:
                    clips.append(clip)

            return clips

    def get_buffer_size(self) -> int:
        with self._lock:
            return len(self._frame_buffer)

    def clear_buffer(self) -> None:
        with self._lock:
            self._frame_buffer.clear()

    def is_ready(self) -> bool:
        with self._lock:
            return len(self._frame_buffer) >= self._window_size
