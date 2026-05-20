import cv2
import numpy as np
from typing import Optional, Tuple, List, Dict, Any


class AdaptiveCLAHE:
    def __init__(self, base_clip_limit: float = 2.0, base_tile_grid: Tuple[int, int] = (8, 8),
                 auto_tune: bool = True):
        self.base_clip_limit = base_clip_limit
        self.base_tile_grid = base_tile_grid
        self.auto_tune = auto_tune
        self.clahe_instances = {}

    def _analyze_image(self, image: np.ndarray) -> Dict[str, float]:
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image

        hist = cv2.calcHist([gray], [0], None, [256], [0, 256])
        hist = hist / hist.sum()

        entropy = -np.sum(hist * np.log2(hist + 1e-10))
        std = np.std(gray)
        mean = np.mean(gray)
        contrast = std / (mean + 1e-10)

        p5, p95 = np.percentile(gray, [5, 95])
        dynamic_range = p95 - p5

        return {
            'entropy': float(entropy),
            'std': float(std),
            'mean': float(mean),
            'contrast': float(contrast),
            'dynamic_range': float(dynamic_range),
            'brightness': float(mean / 255.0)
        }

    def _get_adaptive_params(self, stats: Dict[str, float]) -> Tuple[float, Tuple[int, int]]:
        clip_limit = self.base_clip_limit
        tile_grid = self.base_tile_grid

        if self.auto_tune:
            if stats['contrast'] < 0.2:
                clip_limit = self.base_clip_limit * 1.5
            elif stats['contrast'] > 0.5:
                clip_limit = self.base_clip_limit * 0.7

            if stats['entropy'] < 4.0:
                clip_limit = max(clip_limit * 1.3, 1.0)
            elif stats['entropy'] > 7.0:
                clip_limit = max(clip_limit * 0.8, 1.0)

            if stats['brightness'] < 0.3 or stats['brightness'] > 0.7:
                tile_grid = (16, 16)
            elif stats['dynamic_range'] < 50:
                tile_grid = (4, 4)

        return clip_limit, tile_grid

    def _get_clahe(self, clip_limit: float, tile_grid: Tuple[int, int]) -> cv2.CLAHE:
        key = (round(clip_limit, 1), tile_grid)
        if key not in self.clahe_instances:
            self.clahe_instances[key] = cv2.createCLAHE(
                clipLimit=clip_limit,
                tileGridSize=tile_grid
            )
        return self.clahe_instances[key]

    def apply(self, image: np.ndarray) -> np.ndarray:
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image

        stats = self._analyze_image(gray)
        clip_limit, tile_grid = self._get_adaptive_params(stats)
        clahe = self._get_clahe(clip_limit, tile_grid)

        enhanced = clahe.apply(gray)
        return enhanced


class MultiScaleCLAHE:
    def __init__(self, scales: Optional[List[Tuple[int, int]]] = None,
                 weights: Optional[List[float]] = None):
        if scales is None:
            self.scales = [(4, 4), (8, 8), (16, 16)]
        else:
            self.scales = scales

        if weights is None:
            self.weights = [0.3, 0.5, 0.2]
        else:
            self.weights = weights

        self.clahe_instances = {}
        for scale in self.scales:
            self.clahe_instances[scale] = cv2.createCLAHE(clipLimit=2.0, tileGridSize=scale)

    def apply(self, image: np.ndarray) -> np.ndarray:
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image

        enhanced = np.zeros_like(gray, dtype=np.float32)
        total_weight = sum(self.weights)

        for scale, weight in zip(self.scales, self.weights):
            clahe = self.clahe_instances[scale]
            scaled_enhanced = clahe.apply(gray).astype(np.float32)
            enhanced += scaled_enhanced * (weight / total_weight)

        return np.clip(enhanced, 0, 255).astype(np.uint8)


class ImageEnhancer:
    def __init__(self, clip_limit: float = 2.0, tile_grid_size: Tuple[int, int] = (8, 8),
                 use_adaptive_clahe: bool = True, use_multiscale: bool = False,
                 auto_tune: bool = True):
        self.clip_limit = clip_limit
        self.tile_grid_size = tile_grid_size
        self.use_adaptive_clahe = use_adaptive_clahe
        self.use_multiscale = use_multiscale
        self.auto_tune = auto_tune

        self.clahe = cv2.createCLAHE(clipLimit=clip_limit, tileGridSize=tile_grid_size)

        if use_adaptive_clahe:
            self.adaptive_clahe = AdaptiveCLAHE(
                base_clip_limit=clip_limit,
                base_tile_grid=tile_grid_size,
                auto_tune=auto_tune
            )

        if use_multiscale:
            self.multiscale_clahe = MultiScaleCLAHE()

    def contrast_stretching(self, image: np.ndarray, percentiles: Tuple[int, int] = (1, 99)) -> np.ndarray:
        if len(image.shape) == 3:
            image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        p1, p99 = np.percentile(image, percentiles)
        if p99 == p1:
            return image

        stretched = np.clip((image - p1) / (p99 - p1) * 255, 0, 255).astype(np.uint8)
        return stretched

    def clahe_enhance(self, image: np.ndarray) -> np.ndarray:
        if len(image.shape) == 3:
            image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        enhanced = self.clahe.apply(image)
        return enhanced

    def adaptive_clahe_enhance(self, image: np.ndarray) -> np.ndarray:
        if hasattr(self, 'adaptive_clahe'):
            return self.adaptive_clahe.apply(image)
        return self.clahe_enhance(image)

    def multiscale_clahe_enhance(self, image: np.ndarray) -> np.ndarray:
        if hasattr(self, 'multiscale_clahe'):
            return self.multiscale_clahe.apply(image)
        return self.clahe_enhance(image)

    def unsharp_mask(self, image: np.ndarray, sigma: float = 1.0, amount: float = 1.5) -> np.ndarray:
        if len(image.shape) == 3:
            image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        blurred = cv2.GaussianBlur(image, (0, 0), sigma)
        sharpened = cv2.addWeighted(image, 1 + amount, blurred, -amount, 0)
        return sharpened

    def gamma_correction(self, image: np.ndarray, gamma: Optional[float] = None) -> np.ndarray:
        if len(image.shape) == 3:
            image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        if gamma is None:
            mean = np.mean(image)
            if mean < 64:
                gamma = 0.8
            elif mean > 192:
                gamma = 1.5
            else:
                gamma = 1.2

        inv_gamma = 1.0 / gamma
        table = np.array([((i / 255.0) ** inv_gamma) * 255 for i in range(256)]).astype(np.uint8)
        corrected = cv2.LUT(image, table)
        return corrected

    def adaptive_histogram_equalization(self, image: np.ndarray) -> np.ndarray:
        if len(image.shape) == 3:
            image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        img_yuv = cv2.cvtColor(cv2.merge([image, image, image]), cv2.COLOR_BGR2YUV)
        img_yuv[:, :, 0] = self.clahe.apply(img_yuv[:, :, 0])
        enhanced = cv2.cvtColor(img_yuv, cv2.COLOR_YUV2BGR)
        return enhanced

    def bilateral_denoise(self, image: np.ndarray) -> np.ndarray:
        if len(image.shape) == 3:
            image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        denoised = cv2.bilateralFilter(image, d=9, sigmaColor=75, sigmaSpace=75)
        return denoised

    def enhance_xray(self, image: np.ndarray, pipeline: Optional[list] = None) -> np.ndarray:
        if pipeline is None:
            if self.use_multiscale:
                pipeline = ['multiscale_clahe_enhance', 'unsharp_mask', 'gamma_correction']
            elif self.use_adaptive_clahe:
                pipeline = ['adaptive_clahe_enhance', 'unsharp_mask', 'gamma_correction']
            else:
                pipeline = ['clahe_enhance', 'unsharp_mask', 'gamma_correction']

        result = image.copy()
        for step in pipeline:
            if hasattr(self, step):
                result = getattr(self, step)(result)

        return result

    def batch_enhance(self, images: list, pipeline: Optional[list] = None) -> list:
        return [self.enhance_xray(img, pipeline) for img in images]

    def get_image_stats(self, image: np.ndarray) -> Dict[str, Any]:
        if hasattr(self, 'adaptive_clahe'):
            return self.adaptive_clahe._analyze_image(image)
        return {}
