import cv2
import threading
import queue
import time
from typing import Optional, Tuple, Dict
from enum import Enum


class SourceType(Enum):
    CAMERA = "camera"
    FILE = "file"


class VideoCapture:
    def __init__(self, max_queue_size: int = 100):
        self._cap: Optional[cv2.VideoCapture] = None
        self._source_type: Optional[SourceType] = None
        self._is_running: bool = False
        self._capture_thread: Optional[threading.Thread] = None
        self._frame_queue: queue.Queue = queue.Queue(maxsize=max_queue_size)
        self._lock = threading.Lock()
        self._fps: float = 0.0
        self._frame_count: int = 0
        self._width: int = 0
        self._height: int = 0
        self._start_time: float = 0.0

    def start(self, source_type: str, camera_index: int = 0, file_path: Optional[str] = None) -> None:
        with self._lock:
            if self._is_running:
                raise RuntimeError("Video capture is already running")

            self._source_type = SourceType(source_type)

            if self._source_type == SourceType.CAMERA:
                self._cap = cv2.VideoCapture(camera_index)
            elif self._source_type == SourceType.FILE:
                if not file_path:
                    raise ValueError("file_path must be provided for file source")
                self._cap = cv2.VideoCapture(file_path)
            else:
                raise ValueError(f"Unsupported source type: {source_type}")

            if not self._cap.isOpened():
                raise RuntimeError("Failed to open video source")

            self._width = int(self._cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            self._height = int(self._cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            self._fps = self._cap.get(cv2.CAP_PROP_FPS) or 30.0
            self._frame_count = 0
            self._start_time = time.time()
            self._is_running = True

            self._capture_thread = threading.Thread(target=self._capture_loop, daemon=True)
            self._capture_thread.start()

    def _capture_loop(self) -> None:
        while self._is_running and self._cap and self._cap.isOpened():
            try:
                ret, frame = self._cap.read()
                if not ret:
                    if self._source_type == SourceType.FILE:
                        break
                    time.sleep(0.01)
                    continue

                with self._lock:
                    self._frame_count += 1

                if not self._frame_queue.full():
                    timestamp = time.time()
                    self._frame_queue.put((frame, timestamp))
                else:
                    try:
                        self._frame_queue.get_nowait()
                        timestamp = time.time()
                        self._frame_queue.put((frame, timestamp))
                    except queue.Empty:
                        pass

            except Exception as e:
                print(f"Error in capture loop: {e}")
                time.sleep(0.1)

        with self._lock:
            self._is_running = False

    def read_frame(self, timeout: float = 1.0) -> Optional[Tuple]:
        try:
            return self._frame_queue.get(timeout=timeout)
        except queue.Empty:
            return None

    def stop(self) -> None:
        with self._lock:
            self._is_running = False

        if self._capture_thread:
            self._capture_thread.join(timeout=2.0)

        if self._cap:
            self._cap.release()
            self._cap = None

        with self._lock:
            while not self._frame_queue.empty():
                try:
                    self._frame_queue.get_nowait()
                except queue.Empty:
                    break

    def get_info(self) -> Dict:
        with self._lock:
            elapsed = time.time() - self._start_time if self._start_time > 0 else 0
            current_fps = self._frame_count / elapsed if elapsed > 0 else 0
            return {
                "source_type": self._source_type.value if self._source_type else None,
                "is_running": self._is_running,
                "width": self._width,
                "height": self._height,
                "fps": self._fps,
                "frame_count": self._frame_count,
                "current_fps": current_fps,
                "queue_size": self._frame_queue.qsize()
            }
