import numpy as np
from scipy import linalg
from typing import Tuple, Optional
from collections import deque

from hs_utils import (
    mirror_pad_image,
    regularized_covariance,
    safe_inverse_covariance,
    covariance_condition_number
)


class SlidingWindowRX:
    def __init__(self, window_size: int = 50, guard_size: int = 5, 
                 update_interval: int = 10, use_gpu: bool = False,
                 reg_lambda: float = 1e-4, reg_method: str = 'ridge',
                 boundary_mode: str = 'mirror'):
        self.window_size = window_size
        self.guard_size = guard_size
        self.update_interval = update_interval
        self.use_gpu = use_gpu
        self.reg_lambda = reg_lambda
        self.reg_method = reg_method
        self.boundary_mode = boundary_mode
        
        self.mean_vector = None
        self.cov_matrix = None
        self.cov_inv = None
        self._stats_buffer = deque(maxlen=update_interval)
        self._iteration = 0
        self._gpu_module = None
        self._padded_image = None
        self._pad_size = 0

        if use_gpu:
            self._init_gpu()

    def _init_gpu(self):
        try:
            from gpu_module import RXGPU
            self._gpu_module = RXGPU()
        except ImportError:
            print("Warning: GPU module not available, falling back to CPU")
            self.use_gpu = False

    def _pad_image(self, image: np.ndarray) -> np.ndarray:
        self._pad_size = self.window_size // 2
        if self.boundary_mode == 'mirror':
            return mirror_pad_image(image, self._pad_size)
        elif self.boundary_mode == 'symmetric':
            from hs_utils import symmetric_pad_image
            return symmetric_pad_image(image, self._pad_size, self._pad_size)
        elif self.boundary_mode == 'edge':
            from hs_utils import edge_pad_image
            return edge_pad_image(image, self._pad_size)
        elif self.boundary_mode == 'none':
            return image
        else:
            return mirror_pad_image(image, self._pad_size)

    def _extract_local_window(self, padded_image: np.ndarray, 
                               center_y: int, center_x: int) -> np.ndarray:
        pad_size = self._pad_size
        half_win = self.window_size // 2
        half_guard = self.guard_size // 2
        
        padded_y = center_y + pad_size
        padded_x = center_x + pad_size
        
        y_start = padded_y - half_win
        y_end = padded_y + half_win + 1
        x_start = padded_x - half_win
        x_end = padded_x + half_win + 1
        
        window = padded_image[y_start:y_end, x_start:x_end, :].copy()
        
        if self.guard_size > 0:
            win_h, win_w = window.shape[:2]
            center_win_y = win_h // 2
            center_win_x = win_w // 2
            
            gy_start = max(0, center_win_y - half_guard)
            gy_end = min(win_h, center_win_y + half_guard + 1)
            gx_start = max(0, center_win_x - half_guard)
            gx_end = min(win_w, center_win_x + half_guard + 1)
            
            mask = np.ones(window.shape[:2], dtype=bool)
            mask[gy_start:gy_end, gx_start:gx_end] = False
            window = window[mask]
        
        return window.reshape(-1, window.shape[-1])

    def _update_statistics(self, data: np.ndarray) -> None:
        n_samples = data.shape[0]
        n_features = data.shape[1]
        
        if n_samples < n_features:
            effective_reg = max(self.reg_lambda, 0.1)
        else:
            effective_reg = self.reg_lambda
        
        self.cov_matrix, self.mean_vector = regularized_covariance(
            data, reg_lambda=effective_reg, reg_method=self.reg_method
        )
        self.cov_inv = safe_inverse_covariance(self.cov_matrix)

    def _compute_rx_score(self, pixel: np.ndarray) -> float:
        centered = pixel - self.mean_vector
        return float(centered @ self.cov_inv @ centered.T)

    def detect_image(self, image: np.ndarray, step: int = 1) -> np.ndarray:
        h, w, bands = image.shape
        scores = np.zeros((h, w), dtype=np.float64)
        
        padded_image = self._pad_image(image)
        
        center_y = h // 2
        center_x = w // 2
        init_window = self._extract_local_window(padded_image, center_y, center_x)
        if len(init_window) > bands:
            self._update_statistics(init_window)
        else:
            flat_data = image.reshape(-1, bands)
            self._update_statistics(flat_data)
        
        for y in range(0, h, step):
            for x in range(0, w, step):
                if self._iteration % self.update_interval == 0:
                    local_window = self._extract_local_window(padded_image, y, x)
                    if len(local_window) > bands:
                        self._update_statistics(local_window)
                
                pixel = image[y, x, :]
                scores[y, x] = self._compute_rx_score(pixel)
                self._iteration += 1
        
        return scores

    def detect_pixel_stream(self, pixels: np.ndarray) -> np.ndarray:
        n_pixels, bands = pixels.shape
        scores = np.zeros(n_pixels, dtype=np.float64)
        
        init_size = min(n_pixels, max(self.window_size * self.window_size, bands + 1))
        self._update_statistics(pixels[:init_size])
        
        for i in range(n_pixels):
            if i % self.update_interval == 0 and i > 0:
                start_idx = max(0, i - self.window_size * self.window_size)
                window_data = pixels[start_idx:i]
                if len(window_data) > bands:
                    self._update_statistics(window_data)
            
            scores[i] = self._compute_rx_score(pixels[i])
        
        return scores

    def get_condition_number(self) -> Optional[float]:
        if self.cov_matrix is not None:
            return covariance_condition_number(self.cov_matrix)
        return None


class GlobalBackgroundUpdater:
    def __init__(self, alpha: float = 0.01, use_gpu: bool = False,
                 reg_lambda: float = 1e-4, reg_method: str = 'ridge'):
        self.alpha = alpha
        self.use_gpu = use_gpu
        self.reg_lambda = reg_lambda
        self.reg_method = reg_method
        
        self.mean_vector = None
        self.cov_matrix = None
        self.cov_inv = None
        self._gpu_module = None
        self._n_samples = 0

        if use_gpu:
            self._init_gpu()

    def _init_gpu(self):
        try:
            from gpu_module import RXGPU
            self._gpu_module = RXGPU()
        except ImportError:
            print("Warning: GPU module not available, falling back to CPU")
            self.use_gpu = False

    def initialize(self, data: np.ndarray) -> None:
        if data.ndim == 3:
            data = data.reshape(-1, data.shape[-1])
        
        self._n_samples = data.shape[0]
        self.cov_matrix, self.mean_vector = regularized_covariance(
            data, reg_lambda=self.reg_lambda, reg_method=self.reg_method
        )
        self.cov_inv = safe_inverse_covariance(self.cov_matrix)

    def update(self, new_data: np.ndarray) -> None:
        if self.mean_vector is None:
            self.initialize(new_data)
            return

        if new_data.ndim == 3:
            new_data = new_data.reshape(-1, new_data.shape[-1])
        
        n_new = new_data.shape[0]
        new_cov, new_mean = regularized_covariance(
            new_data, reg_lambda=self.reg_lambda, reg_method=self.reg_method
        )
        
        eff_alpha = min(self.alpha, n_new / (self._n_samples + n_new))
        self.mean_vector = (1 - eff_alpha) * self.mean_vector + eff_alpha * new_mean
        self.cov_matrix = (1 - eff_alpha) * self.cov_matrix + eff_alpha * new_cov
        
        self.cov_matrix += self.reg_lambda * np.eye(self.cov_matrix.shape[0])
        self.cov_inv = safe_inverse_covariance(self.cov_matrix)
        
        self._n_samples += n_new

    def detect(self, data: np.ndarray) -> np.ndarray:
        if self.mean_vector is None:
            raise ValueError("Detector not initialized. Call initialize() first.")

        original_shape = data.shape
        if data.ndim == 3:
            data = data.reshape(-1, data.shape[-1])

        if self.use_gpu and self._gpu_module is not None:
            scores = self._gpu_module.compute_rx_scores_chunked(
                data, self.mean_vector, self.cov_inv
            )
        else:
            centered = data - self.mean_vector
            scores = np.sum(centered @ self.cov_inv * centered, axis=1)

        if len(original_shape) == 3:
            scores = scores.reshape(original_shape[:2])

        return scores

    def get_condition_number(self) -> Optional[float]:
        if self.cov_matrix is not None:
            return covariance_condition_number(self.cov_matrix)
        return None
