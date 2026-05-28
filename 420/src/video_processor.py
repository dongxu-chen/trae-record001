import cv2
import time
import numpy as np
from collections import deque
from threading import Lock, Condition
from typing import Optional, Tuple, List
from PyQt5.QtCore import QThread, pyqtSignal, QMutex, QMutexLocker

from .style_transfer import StyleTransferModel, MultiStyleTransferModel
from .segmentation import InstanceSegmenter


RESOLUTION_PRESETS = {
    "360p": (360, 480),
    "480p": (480, 640),
    "720p": (720, 1280),
    "1080p": (1080, 1920),
}


class FrameBuffer:
    def __init__(self, max_size: int = 10):
        self.max_size = max_size
        self.buffer: deque = deque(maxlen=max_size)
        self.lock = Lock()
        self.condition = Condition(self.lock)
        self.frame_count = 0

    def add(self, frame: np.ndarray):
        with self.condition:
            if len(self.buffer) >= self.max_size:
                self.buffer.popleft()
            timestamp = time.time()
            self.buffer.append((frame, timestamp, self.frame_count))
            self.frame_count += 1
            self.condition.notify()

    def get(self, timeout: float = 1.0) -> Optional[Tuple[np.ndarray, float, int]]:
        with self.condition:
            if not self.buffer:
                if not self.condition.wait(timeout):
                    return None
            if self.buffer:
                return self.buffer.popleft()
            return None

    def get_latest(self) -> Optional[Tuple[np.ndarray, float, int]]:
        with self.lock:
            if self.buffer:
                return self.buffer.pop()
            return None

    def clear(self):
        with self.lock:
            self.buffer.clear()

    def size(self) -> int:
        with self.lock:
            return len(self.buffer)

    def is_full(self) -> bool:
        with self.lock:
            return len(self.buffer) >= self.max_size


class DynamicFPSController:
    def __init__(self, target_fps: int = 30, min_fps: int = 15, max_fps: int = 60):
        self.target_fps = target_fps
        self.min_fps = min_fps
        self.max_fps = max_fps
        self.current_fps = target_fps
        self.target_interval = 1.0 / target_fps
        self.smoothing_factor = 0.1
        self.avg_process_time = 0.0
        self.frame_times = deque(maxlen=30)
        self.adjustment_threshold = 0.1
        self.consecutive_adjustments = 0
        self.max_consecutive_adjustments = 5

    def update(self, process_time_ms: float, buffer_size: int, max_buffer_size: int):
        process_time_sec = process_time_ms / 1000.0

        if self.avg_process_time == 0:
            self.avg_process_time = process_time_sec
        else:
            self.avg_process_time = (
                self.smoothing_factor * process_time_sec +
                (1 - self.smoothing_factor) * self.avg_process_time
            )

        self.frame_times.append(process_time_ms)

        buffer_usage = buffer_size / max_buffer_size if max_buffer_size > 0 else 0

        if self.avg_process_time > 0:
            theoretical_fps = 1.0 / self.avg_process_time
        else:
            theoretical_fps = self.max_fps

        target_interval = self.target_interval

        if buffer_usage > 0.8 and self.current_fps > self.min_fps:
            new_fps = self.current_fps * 0.9
            new_fps = max(new_fps, self.min_fps)
            self._adjust_fps(new_fps)
        elif buffer_usage < 0.3 and self.current_fps < self.max_fps:
            new_fps = min(theoretical_fps * 0.9, self.max_fps)
            if new_fps > self.current_fps * (1 + self.adjustment_threshold):
                self._adjust_fps(new_fps)
        else:
            self.consecutive_adjustments = 0

        return self.current_fps

    def _adjust_fps(self, new_fps: float):
        if self.consecutive_adjustments >= self.max_consecutive_adjustments:
            return

        new_fps = max(self.min_fps, min(self.max_fps, new_fps))
        if abs(new_fps - self.current_fps) / self.current_fps > 0.05:
            self.current_fps = new_fps
            self.target_interval = 1.0 / self.current_fps
            self.consecutive_adjustments += 1
            print(f"FPS adjusted to: {self.current_fps:.1f}")

    def get_sleep_time(self) -> float:
        return max(0, self.target_interval - self.avg_process_time)

    def reset(self):
        self.avg_process_time = 0.0
        self.frame_times.clear()
        self.current_fps = self.target_fps
        self.target_interval = 1.0 / self.target_fps
        self.consecutive_adjustments = 0


class CameraCapture(QThread):
    frame_captured = pyqtSignal(np.ndarray)

    def __init__(self, camera_index: int = 0):
        super().__init__()
        self.camera_index = camera_index
        self.cap: Optional[cv2.VideoCapture] = None
        self.is_running = False
        self.resolution: Optional[Tuple[int, int]] = None
        self.fps = 30
        self.frame_count = 0
        self.last_fps_update = time.time()
        self.current_fps = 0
        self.frame_buffer: Optional[FrameBuffer] = None

    def set_frame_buffer(self, buffer: FrameBuffer):
        self.frame_buffer = buffer

    def open(self, resolution: Optional[Tuple[int, int]] = None, fps: int = 30) -> bool:
        self.cap = cv2.VideoCapture(self.camera_index, cv2.CAP_DSHOW)
        if not self.cap.isOpened():
            self.cap = cv2.VideoCapture(self.camera_index)

        if not self.cap.isOpened():
            print(f"Failed to open camera {self.camera_index}")
            return False

        if resolution is not None:
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, resolution[1])
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, resolution[0])
            self.resolution = resolution

        self.cap.set(cv2.CAP_PROP_FPS, fps)
        self.fps = fps

        actual_width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        actual_height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        self.resolution = (actual_height, actual_width)
        print(f"Camera opened: {self.resolution[1]}x{self.resolution[0]} @ {fps}fps")

        self.is_running = True
        return True

    def run(self):
        while self.is_running:
            if self.cap is None:
                time.sleep(0.01)
                continue

            ret, frame = self.cap.read()
            if not ret:
                time.sleep(0.001)
                continue

            if self.frame_buffer is not None:
                self.frame_buffer.add(frame)

            self.frame_count += 1
            if time.time() - self.last_fps_update >= 1.0:
                self.current_fps = self.frame_count
                self.frame_count = 0
                self.last_fps_update = time.time()

            self.frame_captured.emit(frame)

    def read(self) -> Optional[np.ndarray]:
        if self.frame_buffer is not None:
            result = self.frame_buffer.get(timeout=0.01)
            if result is not None:
                return result[0]
        return None

    def get_current_fps(self) -> int:
        return self.current_fps

    def get_resolution(self) -> Tuple[int, int]:
        return self.resolution

    def close(self):
        self.is_running = False
        self.wait()
        if self.cap is not None:
            self.cap.release()
            self.cap = None
        print("Camera closed")

    @staticmethod
    def list_available_cameras(max_index: int = 5) -> List[int]:
        available = []
        for i in range(max_index):
            cap = cv2.VideoCapture(i)
            if cap.isOpened():
                available.append(i)
                cap.release()
        return available


class VideoProcessor(QThread):
    frame_ready = pyqtSignal(np.ndarray, float)
    fps_updated = pyqtSignal(float)
    buffer_status = pyqtSignal(int, int)
    complexity_updated = pyqtSignal(float)

    def __init__(self, camera_index: int = 0, parent=None):
        super().__init__(parent)
        self.camera = CameraCapture(camera_index)
        self.style_model: Optional[StyleTransferModel] = None
        self.multi_style_model: Optional[MultiStyleTransferModel] = None
        self.segmenter: Optional[InstanceSegmenter] = None
        self.is_running = False
        self.style_strength = 1.0
        self.processing_resolution: Optional[Tuple[int, int]] = (480, 640)
        self.target_fps = 30
        self.frame_times = deque(maxlen=30)
        self.paused = False
        self.show_original = False
        self.skip_frames = 0
        self.max_skip_frames = 3

        self.use_multi_style = False
        self.use_segmentation = False
        self.bg_style_name: Optional[str] = None
        self.show_mask_overlay = False

        self.frame_buffer = FrameBuffer(max_size=5)
        self.camera.set_frame_buffer(self.frame_buffer)
        self.fps_controller = DynamicFPSController(target_fps=target_fps)

    def set_style_model(self, model: Optional[StyleTransferModel]):
        self.style_model = model

    def set_multi_style_model(self, model: Optional[MultiStyleTransferModel]):
        self.multi_style_model = model

    def set_segmenter(self, segmenter: Optional[InstanceSegmenter]):
        self.segmenter = segmenter

    def set_use_multi_style(self, use: bool):
        self.use_multi_style = use

    def set_use_segmentation(self, use: bool):
        self.use_segmentation = use
        if self.segmenter is not None:
            self.segmenter.initialize()

    def set_bg_style_name(self, style_name: Optional[str]):
        self.bg_style_name = style_name

    def set_show_mask_overlay(self, show: bool):
        self.show_mask_overlay = show

    def set_style_strength(self, strength: float):
        self.style_strength = max(0.0, min(1.0, strength))

    def set_processing_resolution(self, resolution: Optional[Tuple[int, int]]):
        self.processing_resolution = resolution

    def set_paused(self, paused: bool):
        self.paused = paused

    def set_show_original(self, show: bool):
        self.show_original = show

    def start_capture(self, resolution: Optional[Tuple[int, int]] = None, fps: int = 30) -> bool:
        self.target_fps = fps
        self.fps_controller = DynamicFPSController(target_fps=fps)
        success = self.camera.open(resolution, fps)
        if success:
            self.is_running = True
            self.camera.start()
            self.start()
        return success

    def stop_capture(self):
        self.is_running = False
        self.wait()
        self.camera.close()
        self.frame_buffer.clear()
        self.fps_controller.reset()

    def run(self):
        last_process_time = 0
        frame_idx = 0

        while self.is_running:
            if self.paused:
                time.sleep(0.01)
                continue

            buffer_size = self.frame_buffer.size()
            self.buffer_status.emit(buffer_size, self.frame_buffer.max_size)

            if buffer_size > self.frame_buffer.max_size * 0.7:
                frame_data = self.frame_buffer.get_latest()
                if frame_data is None:
                    time.sleep(0.001)
                    continue
            else:
                frame_data = self.frame_buffer.get(timeout=0.01)
                if frame_data is None:
                    time.sleep(0.001)
                    continue

            frame, capture_time, frame_number = frame_data

            frame_age = time.time() - capture_time
            if frame_age > 0.2 and buffer_size > 2:
                continue

            if self.skip_frames > 0 and buffer_size > self.frame_buffer.max_size * 0.8:
                self.skip_frames -= 1
                continue

            start_time = time.time()

            if self.show_original:
                stylized_frame = frame
            elif self.use_multi_style and self.multi_style_model is not None:
                try:
                    mask = None
                    if self.use_segmentation and self.segmenter is not None:
                        mask = self.segmenter.segment(frame)

                    stylized_frame = self.multi_style_model.stylize(
                        frame,
                        strength=self.style_strength,
                        target_size=self.processing_resolution,
                        segmentation_mask=mask,
                        bg_style_name=self.bg_style_name
                    )

                    if self.show_mask_overlay and mask is not None:
                        mask_colored = cv2.cvtColor(mask, cv2.COLOR_GRAY2BGR)
                        mask_colored[mask > 0] = [0, 255, 0]
                        stylized_frame = cv2.addWeighted(stylized_frame, 0.8, mask_colored, 0.2, 0)

                    if self.multi_style_model.auto_strength:
                        complexity = self.multi_style_model.complexity_analyzer.get_smoothed_complexity()
                        self.complexity_updated.emit(complexity)
                except Exception as e:
                    print(f"Multi-style transfer error: {e}")
                    stylized_frame = frame
            elif self.style_model is not None:
                try:
                    stylized_frame = self.style_model.stylize(
                        frame,
                        strength=self.style_strength,
                        target_size=self.processing_resolution
                    )
                except Exception as e:
                    print(f"Style transfer error: {e}")
                    stylized_frame = frame
            else:
                stylized_frame = frame

            process_time = (time.time() - start_time) * 1000
            self.frame_times.append(process_time)
            avg_process_time = sum(self.frame_times) / len(self.frame_times)

            current_fps = self.fps_controller.update(
                process_time, buffer_size, self.frame_buffer.max_size
            )
            self.fps_updated.emit(current_fps)

            self.frame_ready.emit(stylized_frame, process_time)

            if buffer_size > self.frame_buffer.max_size * 0.9:
                self.skip_frames = min(self.max_skip_frames, self.skip_frames + 1)
            elif buffer_size < self.frame_buffer.max_size * 0.3:
                self.skip_frames = max(0, self.skip_frames - 1)

            sleep_time = self.fps_controller.get_sleep_time()
            if sleep_time > 0:
                time.sleep(sleep_time)

            last_process_time = process_time
            frame_idx += 1

    def get_camera_fps(self) -> int:
        return self.camera.get_current_fps()

    def get_camera_resolution(self) -> Tuple[int, int]:
        return self.camera.get_resolution()
