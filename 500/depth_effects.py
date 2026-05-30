import numpy as np
import cv2
from scipy.ndimage import gaussian_filter
from typing import Optional, Tuple

from lightfield import LightField
from depth_estimation import DepthEstimator


class FocalLengthSynthesizer:
    def __init__(self, light_field: LightField):
        self.lf = light_field
        self.estimator = DepthEstimator(light_field)
        self._depth_cache = None
        self._conf_cache = None

    def compute_depth(self, method: str = 'focus'):
        if method == 'focus':
            self._depth_cache, self._conf_cache = self.estimator.estimate_depth_from_focus()
        elif method == 'defocus':
            self._depth_cache, self._conf_cache = self.estimator.estimate_depth_from_defocus()
        else:
            self._depth_cache, self._conf_cache = self.estimator.estimate_disparity()

    def synthesize_focal_plane(self, alpha: float) -> np.ndarray:
        return self.estimator.refocus(alpha)

    def _normalize_depth(self, depth: np.ndarray) -> np.ndarray:
        d_min, d_max = depth.min(), depth.max()
        if d_max - d_min < 1e-8:
            return np.zeros_like(depth)
        return (depth - d_min) / (d_max - d_min)


class DepthOfFieldEffect:
    def __init__(self, light_field: LightField):
        self.lf = light_field
        self.center_view = light_field.get_center_view()
        self.focal_synth = FocalLengthSynthesizer(light_field)
        self._blur_kernels = {}

    def apply_bokeh(self, depth: np.ndarray,
                    focus_depth: float = 0.5,
                    aperture: float = 0.3,
                    max_blur: float = 10.0) -> np.ndarray:
        depth_norm = self.focal_synth._normalize_depth(depth)
        center_view = self.center_view

        blur_amount = np.abs(depth_norm - focus_depth)
        blur_sigma = blur_amount / (aperture + 1e-8) * max_blur
        blur_sigma = np.clip(blur_sigma, 0, max_blur)

        blurred = np.zeros_like(center_view, dtype=np.float32)
        weight_sum = np.zeros_like(center_view, dtype=np.float32)

        blur_levels = np.unique(np.round(blur_sigma * 2) / 2)
        blur_levels = blur_levels[blur_levels > 0]

        if len(blur_levels) == 0:
            return center_view.copy()

        for sigma in blur_levels:
            if sigma < 0.5:
                continue
            blurred_layer = gaussian_filter(center_view, sigma=sigma)
            mask = np.abs(blur_sigma - sigma) < 0.5
            blurred += blurred_layer * mask
            weight_sum += mask.astype(np.float32)

        focus_mask = blur_sigma < 0.5
        blurred += center_view * focus_mask
        weight_sum += focus_mask.astype(np.float32)

        result = blurred / (weight_sum + 1e-8)

        return result

    def apply_lens_blur(self, depth: np.ndarray,
                         focus_depth: float = 0.5,
                         f_stop: float = 2.8,
                         focal_length: float = 50.0) -> np.ndarray:
        depth_norm = self.focal_synth._normalize_depth(depth)

        result = np.zeros_like(self.center_view, dtype=np.float32)
        weights = np.zeros_like(self.center_view, dtype=np.float32)

        center_r = self.lf.num_rows // 2
        center_c = self.lf.num_cols // 2

        for y in range(self.lf.num_rows):
            for x in range(self.lf.num_cols):
                dr = y - center_r
                dc = x - center_c

                weight = 1.0 / (1.0 + np.sqrt(dr*dr + dc*dc))

                shift_x = int(dc * focal_length / f_stop)
                shift_y = int(dr * focal_length / f_stop)

                M = np.float32([[1, 0, shift_x], [0, 1, shift_y]])
                shifted = cv2.warpAffine(self.lf.images[y, x], M,
                                          (self.lf.width, self.lf.height))

                result += weight * shifted
                weights += weight

        return result / (weights + 1e-8)


class ApertureSynthesizer:
    def __init__(self, light_field: LightField):
        self.lf = light_field

    def synthesize_aperture(self, aperture_radius: float) -> np.ndarray:
        center_r = self.lf.num_rows // 2
        center_c = self.lf.num_cols // 2

        refocused = np.zeros((self.lf.height, self.lf.width), dtype=np.float32)
        weight_sum = 0.0

        for r in range(self.lf.num_rows):
            for c in range(self.lf.num_cols):
                dr = r - center_r
                dc = c - center_c
                dist = np.sqrt(dr*dr + dc*dc)

                if dist <= aperture_radius:
                    weight = 1.0 - dist / (aperture_radius + 1e-8)
                    refocused += weight * self.lf.images[r, c]
                    weight_sum += weight

        return refocused / (weight_sum + 1e-8)

    def refocus_with_aperture(self, alpha: float, aperture_radius: float) -> np.ndarray:
        center_r = self.lf.num_rows // 2
        center_c = self.lf.num_cols // 2

        refocused = np.zeros((self.lf.height, self.lf.width), dtype=np.float32)
        weight_sum = np.zeros((self.lf.height, self.lf.width), dtype=np.float32)

        for r in range(self.lf.num_rows):
            for c in range(self.lf.num_cols):
                dr = r - center_r
                dc = c - center_c
                dist = np.sqrt(dr*dr + dc*dc)

                if dist > aperture_radius:
                    continue

                shift_y = int(dr * alpha * 2)
                shift_x = int(dc * alpha * 2)

                M = np.float32([[1, 0, shift_x], [0, 1, shift_y]])
                shifted = cv2.warpAffine(self.lf.images[r, c], M,
                                          (self.lf.width, self.lf.height))

                weight = 1.0 / (1.0 + dist)
                refocused += weight * shifted
                weight_sum += weight

        return refocused / (weight_sum + 1e-8)


class RefocusStack:
    def __init__(self, light_field: LightField,
                 num_planes: int = 30,
                 alpha_range: Tuple[float, float] = (-3.0, 3.0)):
        self.lf = light_field
        self.estimator = DepthEstimator(light_field)
        self.alphas = np.linspace(alpha_range[0], alpha_range[1], num_planes)
        self.refocus_stack = None
        self._build_stack()

    def _build_stack(self):
        self.refocus_stack = np.zeros((len(self.alphas), self.lf.height, self.lf.width), dtype=np.float32)
        for i, alpha in enumerate(self.alphas):
            self.refocus_stack[i] = self.estimator.refocus(alpha)

    def get_refocused(self, alpha: float) -> np.ndarray:
        if alpha < self.alphas[0]:
            return self.refocus_stack[0]
        if alpha > self.alphas[-1]:
            return self.refocus_stack[-1]

        idx = np.searchsorted(self.alphas, alpha)
        if idx == 0:
            return self.refocus_stack[0]

        t = (alpha - self.alphas[idx-1]) / (self.alphas[idx] - self.alphas[idx-1])
        return (1 - t) * self.refocus_stack[idx-1] + t * self.refocus_stack[idx]

    def apply_dof_from_stack(self, depth: np.ndarray, focus_alpha: float) -> np.ndarray:
        depth_norm = (depth - depth.min()) / (depth.max() - depth.min() + 1e-8)
        alpha_indices = depth_norm * (len(self.alphas) - 1)
        alpha_indices = np.clip(alpha_indices, 0, len(self.alphas) - 1)

        idx_floor = np.floor(alpha_indices).astype(int)
        idx_ceil = np.minimum(idx_floor + 1, len(self.alphas) - 1)
        t = alpha_indices - idx_floor

        h, w = depth.shape
        result = np.zeros((h, w), dtype=np.float32)

        for y in range(h):
            for x in range(w):
                i0 = idx_floor[y, x]
                i1 = idx_ceil[y, x]
                ti = t[y, x]
                result[y, x] = (1 - ti) * self.refocus_stack[i0, y, x] + ti * self.refocus_stack[i1, y, x]

        return result
