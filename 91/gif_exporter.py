import threading
from typing import List, Tuple, Optional, Callable

import numpy as np

try:
    from PIL import Image
    _PIL_AVAILABLE = True
except ImportError:
    _PIL_AVAILABLE = False


def pil_available() -> bool:
    return _PIL_AVAILABLE


def grid_to_rgb(
    data: np.ndarray,
    bg_color: Tuple[int, int, int] = (10, 10, 20),
    cell_color: Tuple[int, int, int] = (0, 255, 136)
) -> np.ndarray:
    h, w = data.shape
    rgb = np.zeros((h, w, 3), dtype=np.uint8)
    bg = np.array(bg_color, dtype=np.uint8)
    cell = np.array(cell_color, dtype=np.uint8)
    mask = data > 127
    rgb[..., :] = bg
    rgb[mask] = cell
    return rgb


def upscale_frame(frame: np.ndarray, scale: int) -> np.ndarray:
    if scale == 1:
        return frame
    h, w, c = frame.shape
    new_h, new_w = h * scale, w * scale
    up = np.zeros((new_h, new_w, c), dtype=np.uint8)
    for y in range(new_h):
        for x in range(new_w):
            up[y, x] = frame[y // scale, x // scale]
    return up


class GifExporter:
    def __init__(
        self,
        output_path: str,
        fps: int = 10,
        cell_color: Tuple[int, int, int] = (0, 255, 136),
        bg_color: Tuple[int, int, int] = (10, 10, 20),
        scale: int = 4
    ) -> None:
        if not _PIL_AVAILABLE:
            raise ImportError("Pillow is required for GIF export. Install with: pip install Pillow")
        self.output_path = output_path
        self.fps = fps
        self.duration = int(1000 / max(1, fps))
        self.cell_color = cell_color
        self.bg_color = bg_color
        self.scale = scale
        self.frames: List[Image.Image] = []
        self._frames_np: List[np.ndarray] = []
        self._lock = threading.Lock()
        self._worker = None

    def add_frame_from_grid(self, grid_data: np.ndarray) -> None:
        with self._lock:
            self._frames_np.append(grid_data.copy())

    def add_frame_from_rgb(self, rgb: np.ndarray) -> None:
        with self._lock:
            self._frames_np.append(rgb.copy())

    def _render_frames(self) -> None:
        with self._lock:
            data_list = list(self._frames_np)

        rendered = []
        for data in data_list:
            if data.ndim == 2:
                rgb = grid_to_rgb(data, self.bg_color, self.cell_color)
            else:
                rgb = data
            rgb = upscale_frame(rgb, self.scale)
            img = Image.fromarray(rgb, mode="RGB")
            rendered.append(img)

        with self._lock:
            self.frames = rendered

    def save(self, progress_callback: Optional[Callable[[int, int], None] = None) -> None:
        if not self._frames_np:
            raise ValueError("No frames to save.")

        self._render_frames()

        if progress_callback is not None:
            progress_callback(0, len(self.frames))

        first = self.frames[0]
        rest = self.frames[1:] if len(self.frames) > 1 else []

        for i, _ in enumerate(rest, start=1):
            if progress_callback is not None:
                progress_callback(i, len(self.frames))

        first.save(
            self.output_path,
            save_all=True,
            append_images=rest,
            duration=self.duration,
            loop=0
        )

        if progress_callback is not None:
            progress_callback(len(self.frames), len(self.frames))

    def clear(self) -> None:
        with self._lock:
            self._frames_np.clear()
            self.frames.clear()

    def frame_count(self) -> int:
        with self._lock:
            return len(self._frames_np)


def export_animation(
    output_path: str,
    steps: int,
    game_get_frame: Callable[[], Optional[np.ndarray]],
    game_step: Callable[[], None],
    fps: int = 10,
    scale: int = 4,
    cell_color: Tuple[int, int, int] = (0, 255, 136),
    bg_color: Tuple[int, int, int] = (10, 10, 20),
    progress_callback: Optional[Callable[[int, int], None] = None
) -> GifExporter:
    exporter = GifExporter(
        output_path, fps=fps, cell_color=cell_color, bg_color=bg_color, scale=scale)

    for i in range(steps):
        frame = game_get_frame()
        if frame is not None:
            exporter.add_frame_from_grid(frame)
        if progress_callback is not None:
            progress_callback(i, steps)
        game_step()

    last_frame = game_get_frame()
    if last_frame is not None:
        exporter.add_frame_from_grid(last_frame)

    exporter.save()
    return exporter
