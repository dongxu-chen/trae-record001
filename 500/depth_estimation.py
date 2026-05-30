import numpy as np
import cv2
from scipy.ndimage import gaussian_filter, laplace, sobel
from scipy.signal import convolve2d
from typing import Tuple, Optional
from lightfield import LightField

try:
    from gpu_accel import refocus_numba, compute_defocus_var_numba
    ACCEL_AVAILABLE = True
except ImportError:
    ACCEL_AVAILABLE = False


class DepthEstimator:
    def __init__(self, light_field: LightField, use_accelerated: bool = True):
        self.lf = light_field
        self.center_row = light_field.num_rows // 2
        self.center_col = light_field.num_cols // 2
        self._gradient_density = None
        self._low_texture_mask = None
        self.use_accelerated = use_accelerated and ACCEL_AVAILABLE
        if self.use_accelerated:
            self._images_float32 = self.lf.images.astype(np.float32)

    def _ensure_gradient_density(self):
        if self._gradient_density is None:
            self._gradient_density, self._low_texture_mask = \
                self.lf.compute_gradient_density()

    def compute_adaptive_alphas(self, alpha_range: Tuple[float, float],
                                 base_planes: int = 20,
                                 density: Optional[np.ndarray] = None) -> np.ndarray:
        if density is None:
            self._ensure_gradient_density()
            density = self._gradient_density

        alpha_min, alpha_max = alpha_range
        total_range = alpha_max - alpha_min

        mean_density = np.mean(density)
        if mean_density > 0.7:
            num_planes = min(base_planes * 2, base_planes + 20)
        elif mean_density > 0.3:
            num_planes = base_planes
        else:
            num_planes = max(base_planes // 2, 5)

        uniform = np.linspace(alpha_min, alpha_max, num_planes)

        grad_cdf = np.cumsum(density.flatten())
        grad_cdf = grad_cdf / grad_cdf[-1]

        n_quantiles = num_planes
        targets = np.linspace(0, 1, n_quantiles)
        quantile_alphas = np.interp(targets, grad_cdf,
                                     np.linspace(alpha_min, alpha_max, len(grad_cdf)))

        adaptive = np.sort(np.unique(np.concatenate([uniform, quantile_alphas])))

        return adaptive
        
    def refocus(self, alpha: float, patch_size: int = 7) -> np.ndarray:
        if self.use_accelerated:
            return refocus_numba(self._images_float32, alpha,
                                  self.center_row, self.center_col)

        refocused = np.zeros((self.lf.height, self.lf.width), dtype=np.float32)
        weight_sum = np.zeros((self.lf.height, self.lf.width), dtype=np.float32)
        
        for r in range(self.lf.num_rows):
            for c in range(self.lf.num_cols):
                dr = r - self.center_row
                dc = c - self.center_col
                
                shift_y = int(dr * alpha * 2)
                shift_x = int(dc * alpha * 2)
                
                M = np.float32([[1, 0, shift_x], [0, 1, shift_y]])
                shifted = cv2.warpAffine(self.lf.images[r, c], M, 
                                        (self.lf.width, self.lf.height))
                
                weight = 1.0 / (1.0 + abs(dr) + abs(dc))
                refocused += weight * shifted
                weight_sum += weight
        
        return refocused / weight_sum
    
    def compute_focus_measure(self, image: np.ndarray, method: str = 'laplacian') -> np.ndarray:
        if method == 'laplacian':
            fm = np.abs(laplace(image))
        elif method == 'sobel':
            grad_x = sobel(image, axis=0)
            grad_y = sobel(image, axis=1)
            fm = np.sqrt(grad_x**2 + grad_y**2)
        elif method == 'variance':
            kernel = np.ones((7, 7)) / 49
            mean = convolve2d(image, kernel, mode='same')
            sqr_mean = convolve2d(image**2, kernel, mode='same')
            fm = sqr_mean - mean**2
        elif method == 'tenengrad':
            grad_x = sobel(image, axis=0, ksize=3)
            grad_y = sobel(image, axis=1, ksize=3)
            fm = grad_x**2 + grad_y**2
        else:
            raise ValueError(f"Unknown focus measure: {method}")
        
        return fm
    
    def estimate_depth_from_focus(self, num_planes: int = 20, 
                                  alpha_range: Tuple[float, float] = (-2.0, 2.0),
                                  focus_method: str = 'laplacian',
                                  adaptive: bool = True) -> Tuple[np.ndarray, np.ndarray]:
        self._ensure_gradient_density()

        if adaptive:
            alphas = self.compute_adaptive_alphas(alpha_range, num_planes)
        else:
            alphas = np.linspace(alpha_range[0], alpha_range[1], num_planes)

        focus_stack = np.zeros((len(alphas), self.lf.height, self.lf.width), dtype=np.float32)
        
        for i, alpha in enumerate(alphas):
            refocused = self.refocus(alpha)
            focus_stack[i] = self.compute_focus_measure(refocused, focus_method)
        
        focus_stack = gaussian_filter(focus_stack, sigma=(0.5, 1, 1))
        
        depth_indices = np.argmax(focus_stack, axis=0)
        depth_values = alphas[depth_indices]
        
        max_focus = np.max(focus_stack, axis=0)
        mean_focus = np.mean(focus_stack, axis=0)
        confidence = max_focus / (mean_focus + 1e-8)
        confidence = np.clip(confidence / np.percentile(confidence, 95), 0, 1)

        low_texture_penalty = self._gradient_density
        confidence = confidence * (1.0 - 0.7 * (1.0 - low_texture_penalty))

        return depth_values, confidence
    
    def estimate_depth_from_defocus(self, patch_size: int = 11, 
                                     sigma_range: Tuple[float, float] = (0.5, 5.0)) -> Tuple[np.ndarray, np.ndarray]:
        self._ensure_gradient_density()
        center_view = self.lf.get_center_view()

        if self.use_accelerated:
            local_var = compute_defocus_var_numba(
                self._images_float32, center_view.astype(np.float32),
                self.center_row, self.center_col, patch_size
            )
        else:
            variances = np.zeros((self.lf.height, self.lf.width), dtype=np.float32)
            kernel = np.ones((patch_size, patch_size)) / (patch_size ** 2)
            
            for r in range(self.lf.num_rows):
                for c in range(self.lf.num_cols):
                    if r == self.center_row and c == self.center_col:
                        continue
                    diff = self.lf.images[r, c] - center_view
                    variances += diff ** 2
            
            variances /= (self.lf.num_rows * self.lf.num_cols - 1)
            local_var = convolve2d(variances, kernel, mode='same')
        
        depth = 1.0 / (local_var + 1e-6)
        depth = (depth - depth.min()) / (depth.max() - depth.min() + 1e-8)
        
        sharpness = self.compute_focus_measure(center_view, 'variance')
        confidence = np.clip(sharpness / (np.percentile(sharpness, 90) + 1e-8), 0, 1)

        low_texture_penalty = self._gradient_density
        confidence = confidence * (1.0 - 0.7 * (1.0 - low_texture_penalty))
        
        return depth, confidence
    
    def estimate_disparity(self, patch_size: int = 15, 
                           disparity_range: Tuple[int, int] = (-10, 10)) -> Tuple[np.ndarray, np.ndarray]:
        self._ensure_gradient_density()
        center_view = self.lf.get_center_view()
        disp_min, disp_max = disparity_range
        num_disps = disp_max - disp_min

        if self.use_accelerated:
            try:
                from gpu_accel import compute_disparity_cost_numba
                cost_volume = compute_disparity_cost_numba(
                    self._images_float32, center_view.astype(np.float32),
                    self.center_row, self.center_col,
                    disp_min, disp_max, patch_size
                )
            except ImportError:
                cost_volume = self._compute_disparity_numpy(
                    center_view, disp_min, disp_max, num_disps, patch_size
                )
        else:
            cost_volume = self._compute_disparity_numpy(
                center_view, disp_min, disp_max, num_disps, patch_size
            )
        
        cost_volume = gaussian_filter(cost_volume, sigma=(1, 2, 2))
        
        disp_indices = np.argmin(cost_volume, axis=0)
        disparities = disp_indices + disp_min
        
        min_cost = np.min(cost_volume, axis=0)
        sorted_costs = np.sort(cost_volume, axis=0)
        if sorted_costs.shape[0] > 1:
            confidence = 1.0 - (sorted_costs[0] / (sorted_costs[1] + 1e-8))
        else:
            confidence = np.ones_like(min_cost)
        confidence = np.clip(confidence, 0, 1)

        low_texture_penalty = self._gradient_density
        confidence = confidence * (1.0 - 0.7 * (1.0 - low_texture_penalty))
        
        return disparities, confidence

    def _compute_disparity_numpy(self, center_view, disp_min, disp_max, num_disps, patch_size):
        cost_volume = np.zeros((num_disps, self.lf.height, self.lf.width), dtype=np.float32)
        
        for r in range(self.lf.num_rows):
            for c in range(self.lf.num_cols):
                if r == self.center_row and c == self.center_col:
                    continue
                
                for d_idx, d in enumerate(range(disp_min, disp_max)):
                    dr = r - self.center_row
                    dc = c - self.center_col
                    
                    shift_x = int(dc * d)
                    shift_y = int(dr * d)
                    
                    M = np.float32([[1, 0, shift_x], [0, 1, shift_y]])
                    shifted = cv2.warpAffine(self.lf.images[r, c], M, 
                                            (self.lf.width, self.lf.height))
                    
                    sad = np.abs(shifted - center_view)
                    sad = cv2.boxFilter(sad, -1, (patch_size, patch_size))
                    cost_volume[d_idx] += sad
        
        return cost_volume
