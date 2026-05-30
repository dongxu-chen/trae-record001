import numpy as np
import cv2
from typing import Optional, Callable, Tuple
from color_transfer import (
    ColorSpace,
    reinhard_transfer,
    GMMColorTransfer,
    convert_to_color_space,
    convert_from_color_space,
    _channel_stats,
)


class VideoColorTransfer:
    def __init__(
        self,
        reference: np.ndarray,
        color_space: ColorSpace = ColorSpace.LAB,
        method: str = "reinhard",
        n_components: int = 3,
        blend: float = 1.0,
        ema_alpha: float = 0.3,
        preserve_details: bool = True,
    ):
        self.color_space = color_space
        self.method = method
        self.n_components = n_components
        self.blend = blend
        self.ema_alpha = ema_alpha
        self.preserve_details = preserve_details

        self.ref_mean, self.ref_std = self._compute_frame_stats(reference)
        self.prev_src_mean = None
        self.prev_src_std = None

        if method == "gmm":
            self.gmm = GMMColorTransfer(
                n_components=n_components,
                color_space=color_space,
            )
            self.gmm.fit(reference)
        else:
            self.gmm = None

    def _compute_frame_stats(self, frame: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        converted = convert_to_color_space(frame, self.color_space)
        pixels = converted.reshape(-1, 3)
        return _channel_stats(pixels)

    def _ema_update(self, current: np.ndarray, previous: np.ndarray) -> np.ndarray:
        return self.ema_alpha * current + (1 - self.ema_alpha) * previous

    def transfer_frame(self, frame: np.ndarray, frame_index: int = 0) -> np.ndarray:
        src_mean, src_std = self._compute_frame_stats(frame)

        if self.prev_src_mean is None or self.prev_src_std is None:
            smoothed_src_mean = src_mean
            smoothed_src_std = src_std
        else:
            smoothed_src_mean = self._ema_update(src_mean, self.prev_src_mean)
            smoothed_src_std = self._ema_update(src_std, self.prev_src_std)

        self.prev_src_mean = smoothed_src_mean
        self.prev_src_std = smoothed_src_std

        if self.method == "reinhard":
            converted = convert_to_color_space(frame, self.color_space).astype(np.float64)
            result = converted.copy()
            for c in range(3):
                result[:, :, c] = (
                    (converted[:, :, c] - smoothed_src_mean[c])
                    * (self.ref_std[c] / smoothed_src_std[c])
                    + self.ref_mean[c]
                )

            if 0.0 < self.blend < 1.0:
                result = converted * (1 - self.blend) + result * self.blend

            if self.color_space == ColorSpace.HSV:
                result[:, :, 0] = result[:, :, 0] % 180

            return convert_from_color_space(result, self.color_space, preserve_details=self.preserve_details)
        else:
            return self.gmm.transform(
                frame,
                blend=self.blend,
                preserve_details=self.preserve_details,
            )

    def process_video(
        self,
        input_path: str,
        output_path: str,
        progress_callback: Optional[Callable[[int, int], None]] = None,
        codec: str = "mp4v",
    ) -> dict:
        cap = cv2.VideoCapture(input_path)
        if not cap.isOpened():
            raise IOError(f"Cannot open video: {input_path}")

        fps = cap.get(cv2.CAP_PROP_FPS)
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

        fourcc = cv2.VideoWriter_fourcc(*codec)
        writer = cv2.VideoWriter(output_path, fourcc, fps, (width, height))

        self.prev_src_mean = None
        self.prev_src_std = None

        frame_index = 0
        while True:
            ret, frame = cap.read()
            if not ret:
                break

            transferred = self.transfer_frame(frame, frame_index=frame_index)
            writer.write(transferred)

            frame_index += 1
            if progress_callback is not None:
                progress_callback(frame_index, total_frames)

        cap.release()
        writer.release()

        return {
            "fps": fps,
            "total_frames": total_frames,
            "width": width,
            "height": height,
        }


def process_video_with_reference(
    input_video_path: str,
    output_video_path: str,
    reference: np.ndarray,
    color_space: ColorSpace = ColorSpace.LAB,
    method: str = "reinhard",
    ema_alpha: float = 0.3,
    blend: float = 1.0,
    n_components: int = 3,
    progress_callback: Optional[Callable[[int, int], None]] = None,
) -> dict:
    transfer = VideoColorTransfer(
        reference=reference,
        color_space=color_space,
        method=method,
        n_components=n_components,
        blend=blend,
        ema_alpha=ema_alpha,
    )
    return transfer.process_video(
        input_path=input_video_path,
        output_path=output_video_path,
        progress_callback=progress_callback,
    )
