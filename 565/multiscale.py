import numpy as np
from typing import List, Dict, Optional, Tuple
from scipy.ndimage import gaussian_filter, uniform_filter

from hsrx_detector import RXDetector
from hs_utils import (
    regularized_covariance,
    safe_inverse_covariance,
    mirror_pad_image
)


class MultiScaleRX:
    def __init__(self, window_sizes: List[int] = None,
                 reg_lambda: float = 1e-4, reg_method: str = 'ridge',
                 fusion_method: str = 'max',
                 use_gpu: bool = False, chunk_size: int = 10000):
        if window_sizes is None:
            window_sizes = [15, 31, 51, 71]

        self.window_sizes = sorted(window_sizes)
        self.reg_lambda = reg_lambda
        self.reg_method = reg_method
        self.fusion_method = fusion_method
        self.use_gpu = use_gpu
        self.chunk_size = chunk_size

        self.scale_scores = {}
        self.fused_scores = None
        self._detectors = {}

    def _compute_scale_scores(self, image: np.ndarray, window_size: int) -> np.ndarray:
        scale_label = f"w{window_size}"

        if window_size == 0:
            detector = RXDetector(
                use_gpu=self.use_gpu,
                reg_lambda=self.reg_lambda,
                reg_method=self.reg_method,
                chunk_size=self.chunk_size
            )
            scores = detector.fit_detect(image)
            return scores

        from sliding_window import SlidingWindowRX

        guard_size = max(3, window_size // 6)
        update_interval = max(5, (window_size * window_size) // 20)

        detector = SlidingWindowRX(
            window_size=window_size,
            guard_size=guard_size,
            update_interval=update_interval,
            use_gpu=self.use_gpu,
            reg_lambda=self.reg_lambda,
            reg_method=self.reg_method,
            boundary_mode='mirror'
        )

        step = max(1, window_size // 20)
        scores = detector.detect_image(image, step=step)

        if step > 1:
            from scipy.ndimage import zoom
            h, w = image.shape[:2]
            zoom_factors = (h / scores.shape[0], w / scores.shape[1])
            scores = zoom(scores, zoom_factors, order=1)
            scores = scores[:h, :w]

        self._detectors[scale_label] = detector
        return scores

    def _normalize_scores(self, scores: np.ndarray) -> np.ndarray:
        p_min = np.percentile(scores, 1)
        p_max = np.percentile(scores, 99)
        if p_max - p_min < 1e-10:
            return np.zeros_like(scores)
        clipped = np.clip(scores, p_min, p_max)
        return (clipped - p_min) / (p_max - p_min)

    def _fuse_scores(self, score_dict: Dict[str, np.ndarray]) -> np.ndarray:
        normalized = {}
        for key, scores in score_dict.items():
            normalized[key] = self._normalize_scores(scores)

        stacked = np.stack(list(normalized.values()), axis=-1)

        if self.fusion_method == 'max':
            return np.max(stacked, axis=-1)
        elif self.fusion_method == 'mean':
            return np.mean(stacked, axis=-1)
        elif self.fusion_method == 'weighted':
            weights = np.array([1.0 / (i + 1) for i in range(len(normalized))])
            weights = weights / np.sum(weights)
            return np.tensordot(stacked, weights, axes=([-1], [0]))
        elif self.fusion_method == 'product':
            return np.prod(stacked, axis=-1) ** (1.0 / stacked.shape[-1])
        elif self.fusion_method == 'adapt':
            variances = [np.var(s) for s in normalized.values()]
            total_var = sum(variances) + 1e-10
            weights = np.array(variances) / total_var
            return np.tensordot(stacked, weights, axes=([-1], [0]))
        else:
            raise ValueError(f"Unknown fusion method: {self.fusion_method}")

    def detect(self, image: np.ndarray) -> np.ndarray:
        h, w, bands = image.shape

        self.scale_scores['global'] = self._compute_scale_scores(image, window_size=0)

        for ws in self.window_sizes:
            label = f"w{ws}"
            self.scale_scores[label] = self._compute_scale_scores(image, ws)

        self.fused_scores = self._fuse_scores(self.scale_scores)
        return self.fused_scores

    def get_scale_scores(self) -> Dict[str, np.ndarray]:
        return self.scale_scores.copy()

    def get_scale_labels(self) -> List[str]:
        return list(self.scale_scores.keys())

    def get_dominant_scale(self, scores: np.ndarray, threshold_percentile: float = 95) -> np.ndarray:
        threshold = np.percentile(self.fused_scores, threshold_percentile)
        anomaly_mask = self.fused_scores > threshold

        h, w = anomaly_mask.shape
        scale_map = np.zeros((h, w), dtype=int)

        scale_list = list(self.scale_scores.keys())
        normalized = {}
        for key, s in self.scale_scores.items():
            normalized[key] = self._normalize_scores(s)

        for y in range(h):
            for x in range(w):
                if anomaly_mask[y, x]:
                    best_scale = 0
                    best_score = -1
                    for i, key in enumerate(scale_list):
                        if normalized[key][y, x] > best_score:
                            best_score = normalized[key][y, x]
                            best_scale = i
                    scale_map[y, x] = best_scale

        return scale_map, scale_list


class MultiScaleGaussianRX:
    def __init__(self, sigma_list: List[float] = None,
                 reg_lambda: float = 1e-4, reg_method: str = 'ridge',
                 use_gpu: bool = False, chunk_size: int = 10000):
        if sigma_list is None:
            sigma_list = [1.0, 2.0, 4.0, 8.0]

        self.sigma_list = sigma_list
        self.reg_lambda = reg_lambda
        self.reg_method = reg_method
        self.use_gpu = use_gpu
        self.chunk_size = chunk_size

        self.scale_scores = {}
        self.fused_scores = None

    def detect(self, image: np.ndarray) -> np.ndarray:
        h, w, bands = image.shape

        for sigma in self.sigma_list:
            if sigma > 0:
                smoothed = np.zeros_like(image)
                for b in range(bands):
                    smoothed[:, :, b] = gaussian_filter(image[:, :, b], sigma=sigma)
            else:
                smoothed = image.copy()

            detector = RXDetector(
                use_gpu=self.use_gpu,
                reg_lambda=self.reg_lambda,
                reg_method=self.reg_method,
                chunk_size=self.chunk_size
            )
            scores = detector.fit_detect(smoothed)
            self.scale_scores[f"sigma_{sigma}"] = scores

        detector = RXDetector(
            use_gpu=self.use_gpu,
            reg_lambda=self.reg_lambda,
            reg_method=self.reg_method,
            chunk_size=self.chunk_size
        )
        self.scale_scores['original'] = detector.fit_detect(image)

        stacked = np.stack(list(self.scale_scores.values()), axis=-1)
        p_min = np.percentile(stacked, 1)
        p_max = np.percentile(stacked, 99)
        if p_max - p_min > 1e-10:
            stacked = np.clip(stacked, p_min, p_max)
            stacked = (stacked - p_min) / (p_max - p_min)
        else:
            stacked = np.zeros_like(stacked)

        self.fused_scores = np.max(stacked, axis=-1)
        return self.fused_scores

    def get_scale_scores(self) -> Dict[str, np.ndarray]:
        return self.scale_scores.copy()
