import cv2
import numpy as np
from typing import Optional, List, Tuple
import time
from threading import Thread, Lock
from queue import Queue

from config import VIDEO_STREAM_WIDTH, VIDEO_STREAM_HEIGHT, VIDEO_STREAM_FPS
from .frame_handler import StreamFrame


class StreamSource:
    def __init__(
        self,
        source: int = 0,
        width: int = VIDEO_STREAM_WIDTH,
        height: int = VIDEO_STREAM_HEIGHT,
        fps: int = VIDEO_STREAM_FPS
    ):
        self.source = source
        self.width = width
        self.height = height
        self.fps = fps
        self._cap = None
        self._running = False
        self._frame_queue = Queue(maxsize=1)
        self._lock = Lock()
        self._thread = None
        self._frame_count = 0
        self._start_time = None
        self._actual_fps = 0.0

    @property
    def is_opened(self) -> bool:
        return self._cap is not None and self._cap.isOpened()

    @property
    def actual_fps(self) -> float:
        return self._actual_fps

    def open(self) -> bool:
        self._cap = cv2.VideoCapture(self.source)
        if not self._cap.isOpened():
            print(f"[ERROR] Cannot open video source: {self.source}")
            return False

        self._cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
        self._cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
        self._cap.set(cv2.CAP_PROP_FPS, self.fps)

        self._running = True
        self._start_time = time.time()
        self._frame_count = 0
        self._thread = Thread(target=self._read_frames, daemon=True)
        self._thread.start()

        return True

    def _read_frames(self):
        while self._running:
            ret, frame = self._cap.read()
            if not ret:
                print("[WARN] Failed to read frame")
                break

            self._frame_count += 1
            elapsed = time.time() - self._start_time
            if elapsed > 0:
                self._actual_fps = self._frame_count / elapsed

            frame_data = StreamFrame(
                frame=frame,
                timestamp=time.time()
            )

            with self._lock:
                if self._frame_queue.full():
                    try:
                        self._frame_queue.get_nowait()
                    except:
                        pass
                self._frame_queue.put(frame_data)

    def read(self, timeout: float = 1.0) -> Optional[StreamFrame]:
        try:
            return self._frame_queue.get(timeout=timeout)
        except:
            return None

    def release(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=2.0)
        if self._cap:
            self._cap.release()

    def get_info(self) -> dict:
        return {
            "source": self.source,
            "resolution": f"{self.width}x{self.height}",
            "target_fps": self.fps,
            "actual_fps": round(self._actual_fps, 2),
            "is_opened": self.is_opened,
            "frames_captured": self._frame_count
        }
