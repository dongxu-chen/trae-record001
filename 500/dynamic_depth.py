import numpy as np
from scipy.ndimage import gaussian_filter, median_filter
from typing import List, Tuple, Optional
from collections import deque

from lightfield import LightField
from depth_estimation import DepthEstimator


class TemporalSmoother:
    def __init__(self, window_size: int = 5, alpha: float = 0.3):
        self.window_size = window_size
        self.alpha = alpha
        self.depth_history = deque(maxlen=window_size)
        self.confidence_history = deque(maxlen=window_size)

    def update(self, depth: np.ndarray, confidence: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        self.depth_history.append(depth)
        self.confidence_history.append(confidence)

        if len(self.depth_history) == 1:
            return depth.copy(), confidence.copy()

        depth_arr = np.array(self.depth_history)
        conf_arr = np.array(self.confidence_history)

        weights = conf_arr / (conf_arr.sum(axis=0) + 1e-8)
        smoothed_depth = np.sum(depth_arr * weights, axis=0)

        smoothed_conf = np.mean(conf_arr, axis=0)

        return smoothed_depth, smoothed_conf

    def exponential_smooth(self, depth: np.ndarray, confidence: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        if len(self.depth_history) == 0:
            self.depth_history.append(depth)
            self.confidence_history.append(confidence)
            return depth.copy(), confidence.copy()

        prev_depth = self.depth_history[-1]
        prev_conf = self.confidence_history[-1]

        conf_weight = confidence / (confidence + prev_conf + 1e-8)
        alpha = self.alpha + (1 - self.alpha) * (1 - conf_weight)

        smoothed_depth = alpha * depth + (1 - alpha) * prev_depth
        smoothed_conf = 0.5 * (confidence + prev_conf)

        self.depth_history.append(depth)
        self.confidence_history.append(confidence)

        return smoothed_depth, smoothed_conf


class MotionCompensator:
    def __init__(self, height: int, width: int):
        self.height = height
        self.width = width
        self.prev_center_view = None
        self.flow = None

    def estimate_flow(self, current_view: np.ndarray) -> np.ndarray:
        if self.prev_center_view is None:
            self.prev_center_view = current_view.copy()
            return np.zeros((self.height, self.width, 2), dtype=np.float32)

        prev = (self.prev_center_view * 255).astype(np.uint8)
        curr = (current_view * 255).astype(np.uint8)

        flow = cv2.calcOpticalFlowFarneback(
            prev, curr, None,
            pyr_scale=0.5, levels=3, winsize=15,
            iterations=3, poly_n=5, poly_sigma=1.2, flags=0
        )

        self.prev_center_view = current_view.copy()
        self.flow = flow
        return flow

    def warp_depth(self, depth: np.ndarray, flow: np.ndarray) -> np.ndarray:
        h, w = depth.shape
        y, x = np.mgrid[0:h, 0:w]

        x_warp = x + flow[:, :, 0]
        y_warp = y + flow[:, :, 1]

        x_warp = np.clip(x_warp, 0, w - 1)
        y_warp = np.clip(y_warp, 0, h - 1)

        x0 = np.floor(x_warp).astype(int)
        y0 = np.floor(y_warp).astype(int)
        x1 = np.minimum(x0 + 1, w - 1)
        y1 = np.minimum(y0 + 1, h - 1)

        fx = x_warp - x0
        fy = y_warp - y0

        v00 = depth[y0, x0]
        v10 = depth[y0, x1]
        v01 = depth[y1, x0]
        v11 = depth[y1, x1]

        warped = (v00 * (1 - fx) * (1 - fy) +
                  v10 * fx * (1 - fy) +
                  v01 * (1 - fx) * fy +
                  v11 * fx * fy)

        return warped


class DynamicDepthEstimator:
    def __init__(self, light_field: LightField,
                 temporal_window: int = 5,
                 motion_threshold: float = 1.0):
        self.lf = light_field
        self.estimator = DepthEstimator(light_field)
        self.temporal_smoother = TemporalSmoother(window_size=temporal_window)
        self.motion_compensator = MotionCompensator(light_field.height, light_field.width)
        self.motion_threshold = motion_threshold
        self.frame_count = 0

    def process_frame(self, new_light_field: Optional[LightField] = None,
                      method: str = 'focus') -> Tuple[np.ndarray, np.ndarray]:
        if new_light_field is not None:
            self.lf = new_light_field
            self.estimator = DepthEstimator(new_light_field)

        center_view = self.lf.get_center_view()
        flow = self.motion_compensator.estimate_flow(center_view)

        motion_mag = np.sqrt(flow[:, :, 0] ** 2 + flow[:, :, 1] ** 2)
        motion_mask = motion_mag > self.motion_threshold
        motion_ratio = np.mean(motion_mask)

        if method == 'focus':
            depth, confidence = self.estimator.estimate_depth_from_focus()
        elif method == 'defocus':
            depth, confidence = self.estimator.estimate_depth_from_defocus()
        else:
            depth, confidence = self.estimator.estimate_disparity()

        if motion_ratio > 0.5:
            pass
        else:
            depth, confidence = self.temporal_smoother.exponential_smooth(depth, confidence)

        depth = median_filter(depth, size=3)
        depth = gaussian_filter(depth, sigma=0.5)

        self.frame_count += 1

        return depth, confidence

    def reset(self):
        self.temporal_smoother = TemporalSmooth(window_size=self.temporal_smoother.window_size)
        self.motion_compensator = MotionCompensator(self.lf.height, self.lf.width)
        self.frame_count = 0


try:
    import cv2
except ImportError:
    pass
