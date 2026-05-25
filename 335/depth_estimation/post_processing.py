import numpy as np
import cv2
from typing import Optional, Tuple
from config.config import PostProcessingConfig


class DepthPostProcessor:
    def __init__(self, config: PostProcessingConfig):
        self.config = config

    def process(self, depth_map: np.ndarray, rgb_image: Optional[np.ndarray] = None) -> np.ndarray:
        if depth_map is None or depth_map.size == 0:
            raise ValueError("Invalid depth map")

        processed = depth_map.copy()

        if self.config.normalize:
            processed = self._normalize(processed)

        if self.config.apply_median_filter:
            processed = self._median_filter(processed)

        if self.config.apply_gaussian_filter:
            processed = self._gaussian_filter(processed)

        if self.config.apply_bilateral_filter and rgb_image is not None:
            processed = self._bilateral_filter(processed, rgb_image)

        if self.config.apply_edge_guided_filter and rgb_image is not None:
            processed = self._edge_guided_filter(processed, rgb_image)

        if self.config.fill_holes:
            processed = self._fill_holes(processed)

        processed = np.clip(processed, self.config.min_depth, self.config.max_depth)

        return processed

    def _normalize(self, depth_map: np.ndarray) -> np.ndarray:
        min_val = np.nanmin(depth_map)
        max_val = np.nanmax(depth_map)
        
        if max_val - min_val < 1e-6:
            return depth_map
        
        normalized = (depth_map - min_val) / (max_val - min_val)
        depth_range = self.config.max_depth - self.config.min_depth
        normalized = normalized * depth_range + self.config.min_depth
        
        return normalized

    def _bilateral_filter(self, depth_map: np.ndarray, rgb_image: np.ndarray) -> np.ndarray:
        if rgb_image.shape[:2] != depth_map.shape:
            rgb_resized = cv2.resize(rgb_image, (depth_map.shape[1], depth_map.shape[0]))
        else:
            rgb_resized = rgb_image

        depth_normalized = self._to_uint8(depth_map)
        rgb_for_filter = cv2.cvtColor(rgb_resized, cv2.COLOR_BGR2RGB)

        filtered = cv2.bilateralFilter(
            depth_normalized,
            d=self.config.bilateral_d,
            sigmaColor=self.config.bilateral_sigma_color,
            sigmaSpace=self.config.bilateral_sigma_space
        )

        return self._from_uint8(filtered, depth_map)

    def _median_filter(self, depth_map: np.ndarray) -> np.ndarray:
        kernel_size = self.config.median_kernel_size
        if kernel_size % 2 == 0:
            kernel_size += 1

        depth_normalized = self._to_uint8(depth_map)
        filtered = cv2.medianBlur(depth_normalized, kernel_size)
        return self._from_uint8(filtered, depth_map)

    def _gaussian_filter(self, depth_map: np.ndarray) -> np.ndarray:
        kernel_size = self.config.gaussian_kernel_size
        if kernel_size % 2 == 0:
            kernel_size += 1

        sigma = self.config.gaussian_sigma
        if sigma <= 0:
            sigma = 0.3 * ((kernel_size - 1) * 0.5 - 1) + 0.8

        depth_normalized = self._to_uint8(depth_map)
        filtered = cv2.GaussianBlur(depth_normalized, (kernel_size, kernel_size), sigma)
        return self._from_uint8(filtered, depth_map)

    def _edge_guided_filter(self, depth_map: np.ndarray, rgb_image: np.ndarray) -> np.ndarray:
        if rgb_image.shape[:2] != depth_map.shape:
            rgb_resized = cv2.resize(rgb_image, (depth_map.shape[1], depth_map.shape[0]))
        else:
            rgb_resized = rgb_image

        r = self.config.edge_guided_r
        eps = self.config.edge_guided_eps
        edge_weight = self.config.edge_guided_edge_weight

        depth_normalized = self._to_uint8(depth_map)
        depth_float = depth_normalized.astype(np.float32) / 255.0

        guide_gray = cv2.cvtColor(rgb_resized, cv2.COLOR_BGR2GRAY).astype(np.float32) / 255.0

        smoothed_depth = self._guided_filter(guide_gray, depth_float, r, eps)

        rgb_edges = self._detect_rgb_edges(rgb_resized)
        depth_edges = self._detect_depth_edges(depth_float)
        combined_edges = np.maximum(rgb_edges, depth_edges)

        edge_mask = self._compute_edge_mask(combined_edges)

        depth_gradient = self._compute_gradient_magnitude(depth_float)
        adaptive_edge_mask = self._adaptive_edge_threshold(edge_mask, depth_gradient)

        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
        edge_mask_dilated = cv2.dilate(adaptive_edge_mask, kernel, iterations=1)

        weight = edge_weight * edge_mask_dilated + (1 - edge_weight) * (1 - edge_mask_dilated)

        result = weight * depth_float + (1 - weight) * smoothed_depth

        result_uint8 = (result * 255.0).clip(0, 255).astype(np.uint8)
        return self._from_uint8(result_uint8, depth_map)

    def _guided_filter(self, guide: np.ndarray, input_img: np.ndarray, r: int, eps: float) -> np.ndarray:
        h, w = guide.shape

        mean_guide = cv2.boxFilter(guide, cv2.CV_64F, (r, r))
        mean_input = cv2.boxFilter(input_img, cv2.CV_64F, (r, r))
        mean_guide_input = cv2.boxFilter(guide * input_img, cv2.CV_64F, (r, r))
        mean_guide_sq = cv2.boxFilter(guide * guide, cv2.CV_64F, (r, r))

        var_guide = mean_guide_sq - mean_guide * mean_guide
        cov_guide_input = mean_guide_input - mean_guide * mean_input

        a = cov_guide_input / (var_guide + eps)
        b = mean_input - a * mean_guide

        mean_a = cv2.boxFilter(a, cv2.CV_64F, (r, r))
        mean_b = cv2.boxFilter(b, cv2.CV_64F, (r, r))

        q = mean_a * guide + mean_b
        return q.astype(np.float32)

    def _detect_rgb_edges(self, rgb_image: np.ndarray) -> np.ndarray:
        gray = cv2.cvtColor(rgb_image, cv2.COLOR_BGR2GRAY)
        
        sobel_x = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
        sobel_y = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=3)
        magnitude = np.sqrt(sobel_x ** 2 + sobel_y ** 2)
        
        magnitude = cv2.normalize(magnitude, None, 0, 1, cv2.NORM_MINMAX, dtype=cv2.CV_32F)
        return magnitude

    def _detect_depth_edges(self, depth_map: np.ndarray) -> np.ndarray:
        depth_norm = cv2.normalize(depth_map, None, 0, 255, cv2.NORM_MINMAX, dtype=cv2.CV_8U)
        sobel_x = cv2.Sobel(depth_norm, cv2.CV_64F, 1, 0, ksize=3)
        sobel_y = cv2.Sobel(depth_norm, cv2.CV_64F, 0, 1, ksize=3)
        magnitude = np.sqrt(sobel_x ** 2 + sobel_y ** 2)
        
        magnitude = cv2.normalize(magnitude, None, 0, 1, cv2.NORM_MINMAX, dtype=cv2.CV_32F)
        return magnitude

    def _compute_edge_mask(self, edge_magnitude: np.ndarray) -> np.ndarray:
        high_thresh = 0.15
        low_thresh = 0.05
        
        strong_edges = (edge_magnitude > high_thresh).astype(np.float32)
        weak_edges = ((edge_magnitude >= low_thresh) & (edge_magnitude <= high_thresh)).astype(np.float32)
        
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
        strong_dilated = cv2.dilate(strong_edges, kernel)
        
        edge_mask = strong_edges + weak_edges * strong_dilated
        edge_mask = (edge_mask > 0).astype(np.float32)
        
        return edge_mask

    def _adaptive_edge_threshold(self, edge_mask: np.ndarray, depth_gradient: np.ndarray) -> np.ndarray:
        local_mean = cv2.boxFilter(depth_gradient, cv2.CV_32F, (11, 11))
        local_std = cv2.boxFilter((depth_gradient - local_mean) ** 2, cv2.CV_32F, (11, 11))
        local_std = np.sqrt(local_std)
        
        adaptive_weight = 1.0 + 2.0 * local_std
        
        enhanced_mask = edge_mask * adaptive_weight
        enhanced_mask = np.clip(enhanced_mask, 0, 1)
        
        return enhanced_mask

    def _compute_gradient_magnitude(self, img: np.ndarray) -> np.ndarray:
        img_norm = cv2.normalize(img, None, 0, 255, cv2.NORM_MINMAX, dtype=cv2.CV_8U)
        gx = cv2.Sobel(img_norm, cv2.CV_64F, 1, 0, ksize=3)
        gy = cv2.Sobel(img_norm, cv2.CV_64F, 0, 1, ksize=3)
        magnitude = np.sqrt(gx ** 2 + gy ** 2)
        magnitude = cv2.normalize(magnitude, None, 0, 1, cv2.NORM_MINMAX, dtype=cv2.CV_32F)
        return magnitude

    def _fill_holes(self, depth_map: np.ndarray) -> np.ndarray:
        kernel_size = self.config.hole_fill_kernel
        if kernel_size % 2 == 0:
            kernel_size += 1

        mask = self._get_invalid_mask(depth_map)
        
        if not np.any(mask):
            return depth_map

        filled = self._inpaint_depth(depth_map, mask, kernel_size)
        
        mask_after = self._get_invalid_mask(filled)
        if np.any(mask_after):
            filled = self._dilate_fill(filled, mask_after, kernel_size)

        return filled

    def _get_invalid_mask(self, depth_map: np.ndarray) -> np.ndarray:
        mask = np.zeros(depth_map.shape, dtype=np.uint8)
        mask[np.isnan(depth_map)] = 1
        mask[np.isinf(depth_map)] = 1
        mask[depth_map < self.config.min_depth] = 1
        mask[depth_map > self.config.max_depth] = 1
        mask[depth_map <= 0] = 1
        return mask

    def _inpaint_depth(self, depth_map: np.ndarray, mask: np.ndarray, kernel_size: int) -> np.ndarray:
        depth_normalized = self._to_uint8(depth_map)
        
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (kernel_size, kernel_size))
        mask_dilated = cv2.dilate(mask, kernel, iterations=1)
        
        inpainted = cv2.inpaint(depth_normalized, mask_dilated, 3, cv2.INPAINT_TELEA)
        
        return self._from_uint8(inpainted, depth_map)

    def _dilate_fill(self, depth_map: np.ndarray, mask: np.ndarray, kernel_size: int) -> np.ndarray:
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (kernel_size, kernel_size))
        depth_filled = depth_map.copy()
        
        for _ in range(5):
            if not np.any(mask):
                break
            dilated = cv2.dilate(depth_filled, kernel)
            depth_filled[mask > 0] = dilated[mask > 0]
            mask = self._get_invalid_mask(depth_filled)
        
        if np.any(mask):
            depth_filled[mask > 0] = np.nanmean(depth_filled[mask == 0])

        return depth_filled

    @staticmethod
    def _to_uint8(depth_map: np.ndarray) -> np.ndarray:
        min_val = np.nanmin(depth_map)
        max_val = np.nanmax(depth_map)
        
        if max_val - min_val < 1e-6:
            return np.zeros_like(depth_map, dtype=np.uint8)
        
        normalized = (depth_map - min_val) / (max_val - min_val) * 255.0
        normalized = np.nan_to_num(normalized, nan=0, posinf=255, neginf=0)
        return normalized.astype(np.uint8)

    @staticmethod
    def _from_uint8(normalized: np.ndarray, original: np.ndarray) -> np.ndarray:
        min_val = np.nanmin(original)
        max_val = np.nanmax(original)
        
        if max_val - min_val < 1e-6:
            return original
        
        depth_float = normalized.astype(np.float32) / 255.0 * (max_val - min_val) + min_val
        return depth_float.astype(np.float32)

    @staticmethod
    def apply_colormap(depth_map: np.ndarray, colormap: int = cv2.COLORMAP_MAGMA) -> np.ndarray:
        if depth_map is None or depth_map.size == 0:
            raise ValueError("Invalid depth map")

        depth_normalized = DepthPostProcessor._to_uint8(depth_map)
        colored = cv2.applyColorMap(depth_normalized, colormap)
        return colored

    @staticmethod
    def compute_depth_edges(depth_map: np.ndarray, threshold: float = 1.0) -> np.ndarray:
        depth_norm = cv2.normalize(depth_map, None, 0, 255, cv2.NORM_MINMAX, dtype=cv2.CV_8U)
        grad_x = cv2.Sobel(depth_norm, cv2.CV_64F, 1, 0, ksize=3)
        grad_y = cv2.Sobel(depth_norm, cv2.CV_64F, 0, 1, ksize=3)
        magnitude = np.sqrt(grad_x ** 2 + grad_y ** 2)
        edges = (magnitude > threshold).astype(np.uint8) * 255
        return edges

    @staticmethod
    def smooth_with_edges(depth_map: np.ndarray, rgb_image: np.ndarray, 
                         edge_threshold: float = 30.0) -> np.ndarray:
        rgb_gray = cv2.cvtColor(rgb_image, cv2.COLOR_BGR2GRAY)
        rgb_edges = cv2.Canny(rgb_gray, 50, 150)
        
        depth_edges = DepthPostProcessor.compute_depth_edges(depth_map, edge_threshold)
        combined_edges = cv2.bitwise_or(rgb_edges, depth_edges)
        
        depth_normalized = DepthPostProcessor._to_uint8(depth_map)
        smoothed = cv2.bilateralFilter(depth_normalized, 9, 75, 75)
        
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
        edges_dilated = cv2.dilate(combined_edges, kernel, iterations=1)
        
        mask = edges_dilated > 0
        result = smoothed.copy()
        result[mask] = depth_normalized[mask]
        
        return DepthPostProcessor._from_uint8(result, depth_map)

    def get_pipeline_info(self) -> dict:
        return {
            "normalize": self.config.normalize,
            "min_depth": self.config.min_depth,
            "max_depth": self.config.max_depth,
            "bilateral_filter": self.config.apply_bilateral_filter,
            "median_filter": self.config.apply_median_filter,
            "gaussian_filter": self.config.apply_gaussian_filter,
            "edge_guided_filter": self.config.apply_edge_guided_filter,
            "edge_guided_r": self.config.edge_guided_r,
            "edge_guided_eps": self.config.edge_guided_eps,
            "hole_filling": self.config.fill_holes
        }
