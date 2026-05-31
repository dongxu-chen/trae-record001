import numpy as np
from scipy import linalg
from typing import Tuple, Optional

from hs_utils import (
    regularized_covariance,
    safe_inverse_covariance,
    covariance_condition_number
)


class RXDetector:
    def __init__(self, use_gpu: bool = False, reg_lambda: float = 1e-4, 
                 reg_method: str = 'ridge', chunk_size: int = 10000):
        self.use_gpu = use_gpu
        self.reg_lambda = reg_lambda
        self.reg_method = reg_method
        self.chunk_size = chunk_size
        
        self.mean_vector = None
        self.cov_matrix = None
        self.cov_inv = None
        self._gpu_module = None

        if use_gpu:
            self._init_gpu()

    def _init_gpu(self):
        try:
            from gpu_module import RXGPU
            self._gpu_module = RXGPU(chunk_size=self.chunk_size)
        except ImportError:
            print("Warning: GPU module not available, falling back to CPU")
            self.use_gpu = False

    def fit(self, data: np.ndarray) -> None:
        if data.ndim == 3:
            data = data.reshape(-1, data.shape[-1])

        self.cov_matrix, self.mean_vector = regularized_covariance(
            data, reg_lambda=self.reg_lambda, reg_method=self.reg_method
        )
        self.cov_inv = safe_inverse_covariance(self.cov_matrix)

    def detect(self, data: np.ndarray) -> np.ndarray:
        if self.mean_vector is None or self.cov_inv is None:
            raise ValueError("Detector not fitted. Call fit() first.")

        original_shape = data.shape
        if data.ndim == 3:
            data = data.reshape(-1, data.shape[-1])

        if self.use_gpu and self._gpu_module is not None:
            scores = self._gpu_module.compute_rx_scores_chunked(
                data, self.mean_vector, self.cov_inv, chunk_size=self.chunk_size
            )
        else:
            n_samples = data.shape[0]
            scores = np.zeros(n_samples, dtype=np.float64)
            
            n_chunks = (n_samples + self.chunk_size - 1) // self.chunk_size
            
            for i in range(n_chunks):
                start_idx = i * self.chunk_size
                end_idx = min((i + 1) * self.chunk_size, n_samples)
                
                chunk = data[start_idx:end_idx]
                centered = chunk - self.mean_vector
                scores[start_idx:end_idx] = np.sum(centered @ self.cov_inv * centered, axis=1)

        if len(original_shape) == 3:
            scores = scores.reshape(original_shape[:2])

        return scores

    def fit_detect(self, data: np.ndarray) -> np.ndarray:
        self.fit(data)
        return self.detect(data)

    def get_condition_number(self) -> Optional[float]:
        if self.cov_matrix is not None:
            return covariance_condition_number(self.cov_matrix)
        return None
