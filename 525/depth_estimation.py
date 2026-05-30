import numpy as np
import cv2
from typing import Tuple, Optional
from scipy.ndimage import gaussian_filter, median_filter
from scipy.signal import correlate2d


class EdgeGuidedFilter:
    def __init__(self, guidance: np.ndarray, radius: int = 8, eps: float = 0.01):
        if len(guidance.shape) == 3:
            self.guidance = guidance.astype(np.float32)
        else:
            self.guidance = guidance.astype(np.float32)[:, :, np.newaxis]
        self.radius = radius
        self.eps = eps
        self.h, self.w = self.guidance.shape[:2]
    
    def _box_filter(self, src: np.ndarray, r: int) -> np.ndarray:
        return cv2.boxFilter(src, -1, (2 * r + 1, 2 * r + 1), 
                             normalize=True, borderType=cv2.BORDER_REFLECT_101)
    
    def filter(self, src: np.ndarray) -> np.ndarray:
        src_f = src.astype(np.float32)
        h, w = self.h, self.w
        c = self.guidance.shape[2]
        
        mean_I = [self._box_filter(self.guidance[:, :, i], self.radius) for i in range(c)]
        var_I = np.zeros((h, w), dtype=np.float32)
        
        for i in range(c):
            I_sq = self.guidance[:, :, i] ** 2
            mean_I_sq = self._box_filter(I_sq, self.radius)
            var_I += mean_I_sq - mean_I[i] ** 2
        
        mean_p = self._box_filter(src_f, self.radius)
        
        mean_Ip = [self._box_filter(self.guidance[:, :, i] * src_f, self.radius) 
                    for i in range(c)]
        
        cov_Ip = np.zeros((h, w), dtype=np.float32)
        for i in range(c):
            cov_Ip += mean_Ip[i] - mean_I[i] * mean_p
        
        a = np.zeros((h, w, c), dtype=np.float32)
        for i in range(c):
            a[:, :, i] = cov_Ip / (var_I + self.eps)
        
        b = mean_p - np.sum(a * np.stack(mean_I, axis=-1), axis=-1)
        
        mean_a = np.stack([self._box_filter(a[:, :, i], self.radius) for i in range(c)], axis=-1)
        mean_b = self._box_filter(b, self.radius)
        
        result = np.sum(mean_a * self.guidance, axis=-1) + mean_b
        
        return result
    
    def filter_edge_preserving(self, src: np.ndarray, 
                                edge_threshold: float = 0.05,
                                iterations: int = 2) -> np.ndarray:
        result = src.astype(np.float32)
        
        edge_map = self._compute_edge_strength()
        edge_mask = (edge_map > edge_threshold).astype(np.float32)
        
        for _ in range(iterations):
            filtered = self.filter(result)
            
            alpha = 0.3 + 0.7 * edge_mask
            result = alpha * result + (1.0 - alpha) * filtered
        
        return result
    
    def _compute_edge_strength(self) -> np.ndarray:
        if self.guidance.shape[2] == 3:
            gray = cv2.cvtColor(self.guidance.astype(np.uint8), cv2.COLOR_BGR2GRAY)
        else:
            gray = self.guidance[:, :, 0].astype(np.uint8)
        
        grad_x = cv2.Sobel(gray.astype(np.float32), cv2.CV_32F, 1, 0, ksize=3)
        grad_y = cv2.Sobel(gray.astype(np.float32), cv2.CV_32F, 0, 1, ksize=3)
        edge = np.sqrt(grad_x ** 2 + grad_y ** 2)
        
        edge = edge / (edge.max() + 1e-6)
        
        return edge


class DepthEstimator:
    def __init__(self, lf_data: np.ndarray):
        self.lf_data = lf_data
        self.num_views_y, self.num_views_x = lf_data.shape[:2]
        self.h, self.w = lf_data.shape[2:4]
        self.center_vy = self.num_views_y // 2
        self.center_vx = self.num_views_x // 2
        
        center_view = self.lf_data[self.center_vy, self.center_vx]
        self._guided_filter = EdgeGuidedFilter(center_view, radius=8, eps=0.01)
        
    def estimate_depth_phase_shift(self, window_size: int = 15) -> np.ndarray:
        depth_map = np.zeros((self.h, self.w), dtype=np.float32)
        
        center_view = self._to_gray(self.lf_data[self.center_vy, self.center_vx])
        
        for vy in range(self.num_views_y):
            for vx in range(self.num_views_x):
                if vy == self.center_vy and vx == self.center_vx:
                    continue
                
                view = self._to_gray(self.lf_data[vy, vx])
                du = vx - self.center_vx
                dv = vy - self.center_vy
                
                disparity = self._compute_disparity_phase(center_view, view, window_size)
                
                if abs(du) > 0:
                    depth_map += disparity / du
                if abs(dv) > 0:
                    depth_map += disparity / dv
        
        depth_map /= (self.num_views_x * self.num_views_y - 1)
        
        depth_map = self._guided_filter.filter_edge_preserving(
            depth_map, edge_threshold=0.05, iterations=2
        )
        
        return self._normalize_depth(depth_map)
    
    def _compute_disparity_phase(self, img1: np.ndarray, img2: np.ndarray,
                                  window_size: int) -> np.ndarray:
        h, w = img1.shape
        disparity = np.zeros((h, w), dtype=np.float32)
        
        half_win = window_size // 2
        
        for y in range(half_win, h - half_win, window_size):
            for x in range(half_win, w - half_win, window_size):
                patch1 = img1[y - half_win:y + half_win + 1, x - half_win:x + half_win + 1]
                patch2 = img2[y - half_win:y + half_win + 1, x - half_win:x + half_win + 1]
                
                correlation = correlate2d(patch1, patch2, mode='same')
                _, _, _, max_loc = cv2.minMaxLoc(correlation)
                
                dx = max_loc[0] - half_win
                dy = max_loc[1] - half_win
                
                disp = np.sqrt(dx ** 2 + dy ** 2)
                disparity[y - half_win:y + half_win + 1, x - half_win:x + half_win + 1] = disp
        
        return disparity
    
    def estimate_depth_stereo(self, method: str = 'bm') -> np.ndarray:
        left_view = self.lf_data[self.center_vy, max(0, self.center_vx - 2)]
        right_view = self.lf_data[self.center_vy, min(self.num_views_x - 1, self.center_vx + 2)]
        
        left_gray = self._to_gray(left_view)
        right_gray = self._to_gray(right_view)
        
        if method == 'bm':
            stereo = cv2.StereoBM_create(numDisparities=128, blockSize=15)
            disparity = stereo.compute(left_gray, right_gray).astype(np.float32) / 16.0
        elif method == 'sgbm':
            stereo = cv2.StereoSGBM_create(
                minDisparity=0,
                numDisparities=128,
                blockSize=11,
                P1=8 * 3 * 11 ** 2,
                P2=32 * 3 * 11 ** 2,
                disp12MaxDiff=1,
                uniquenessRatio=10,
                speckleWindowSize=100,
                speckleRange=32
            )
            disparity = stereo.compute(left_gray, right_gray).astype(np.float32) / 16.0
        else:
            raise ValueError(f"Unknown method: {method}")
        
        disparity = np.clip(disparity, 0, None)
        
        disparity = self._guided_filter.filter_edge_preserving(
            disparity, edge_threshold=0.05, iterations=2
        )
        
        return self._normalize_depth(disparity)
    
    def estimate_depth_focus_stack(self, num_planes: int = 20) -> np.ndarray:
        from lf_refocus import LightFieldRefocus
        
        refocus = LightFieldRefocus(self.lf_data)
        focus_stack = refocus.focus_stack(num_planes)
        
        focus_measure = np.zeros((num_planes, self.h, self.w), dtype=np.float32)
        
        for i in range(num_planes):
            focus_measure[i] = self._focus_measure_laplacian(focus_stack[i])
        
        best_depth = np.argmax(focus_measure, axis=0).astype(np.float32)
        best_depth /= (num_planes - 1)
        
        best_depth = self._refine_depth(best_depth, focus_measure)
        
        return best_depth
    
    def _focus_measure_laplacian(self, image: np.ndarray) -> np.ndarray:
        gray = self._to_gray(image)
        laplacian = cv2.Laplacian(gray, cv2.CV_32F, ksize=3)
        return np.abs(laplacian)
    
    def _focus_measure_fft(self, image: np.ndarray) -> np.ndarray:
        gray = self._to_gray(image)
        fft = np.fft.fft2(gray)
        fft_shift = np.fft.fftshift(fft)
        magnitude = np.log(np.abs(fft_shift) + 1)
        
        h, w = magnitude.shape
        cy, cx = h // 2, w // 2
        y, x = np.ogrid[:h, :w]
        dist_from_center = np.sqrt((x - cx) ** 2 + (y - cy) ** 2)
        
        high_freq_mask = dist_from_center > min(h, w) // 4
        focus = np.mean(magnitude * high_freq_mask)
        
        return focus * np.ones_like(gray)
    
    def _refine_depth(self, depth_map: np.ndarray, 
                       focus_measure: np.ndarray) -> np.ndarray:
        num_planes = focus_measure.shape[0]
        
        refined = np.zeros_like(depth_map)
        
        for y in range(self.h):
            for x in range(self.w):
                best_idx = int(depth_map[y, x] * (num_planes - 1))
                
                if 0 < best_idx < num_planes - 1:
                    f0 = focus_measure[best_idx - 1, y, x]
                    f1 = focus_measure[best_idx, y, x]
                    f2 = focus_measure[best_idx + 1, y, x]
                    
                    if f1 > f0 and f1 > f2:
                        denom = 2 * (f0 - 2 * f1 + f2)
                        if abs(denom) > 1e-6:
                            offset = (f0 - f2) / denom
                            refined[y, x] = (best_idx + offset) / (num_planes - 1)
                        else:
                            refined[y, x] = depth_map[y, x]
                    else:
                        refined[y, x] = depth_map[y, x]
                else:
                    refined[y, x] = depth_map[y, x]
        
        refined = self._guided_filter.filter_edge_preserving(
            refined, edge_threshold=0.05, iterations=2
        )
        
        return refined
    
    def estimate_depth_epipolar(self) -> np.ndarray:
        depth_map = np.zeros((self.h, self.w), dtype=np.float32)
        
        for y in range(self.h):
            epi_slice = self.lf_data[:, :, y, :, :]
            epi_gray = np.mean(epi_slice, axis=-1)
            
            for x in range(self.w):
                line = epi_gray[:, :, x]
                
                slope = self._estimate_slope(line)
                depth_map[y, x] = slope
        
        depth_map = self._guided_filter.filter_edge_preserving(
            depth_map, edge_threshold=0.05, iterations=2
        )
        
        return self._normalize_depth(depth_map)
    
    def _estimate_slope(self, line_data: np.ndarray) -> float:
        num_views = line_data.shape[0]
        
        variance = np.var(line_data, axis=0)
        best_view = np.argmax(variance)
        
        center = num_views // 2
        if center == best_view:
            return 0.0
        
        return 1.0 / (best_view - center + 1e-6)
    
    def estimate_depth_cost_volume(self, max_disparity: int = 64) -> np.ndarray:
        cost_volume = np.zeros((max_disparity, self.h, self.w), dtype=np.float32)
        
        center_gray = self._to_gray(self.lf_data[self.center_vy, self.center_vx])
        
        for d in range(max_disparity):
            cost = np.zeros((self.h, self.w), dtype=np.float32)
            count = 0
            
            for vy in range(self.num_views_y):
                for vx in range(self.num_views_x):
                    if vy == self.center_vy and vx == self.center_vx:
                        continue
                    
                    du = vx - self.center_vx
                    dv = vy - self.center_vy
                    
                    view_gray = self._to_gray(self.lf_data[vy, vx])
                    
                    M = np.float32([[1, 0, du * d], [0, 1, dv * d]])
                    shifted = cv2.warpAffine(view_gray, M, (self.w, self.h), 
                                             flags=cv2.INTER_LINEAR,
                                             borderMode=cv2.BORDER_REPLICATE)
                    
                    cost += np.abs(center_gray.astype(np.float32) - shifted.astype(np.float32))
                    count += 1
            
            cost_volume[d] = cost / count
        
        disparity = np.argmin(cost_volume, axis=0).astype(np.float32)
        
        disparity = self._subpixel_refinement(cost_volume, disparity)
        
        disparity = self._guided_filter.filter_edge_preserving(
            disparity, edge_threshold=0.05, iterations=2
        )
        
        return self._normalize_depth(disparity)
    
    def _subpixel_refinement(self, cost_volume: np.ndarray, 
                              disparity: np.ndarray) -> np.ndarray:
        max_d = cost_volume.shape[0]
        refined = disparity.copy()
        
        for y in range(self.h):
            for x in range(self.w):
                d = int(disparity[y, x])
                if 0 < d < max_d - 1:
                    c0 = cost_volume[d-1, y, x]
                    c1 = cost_volume[d, y, x]
                    c2 = cost_volume[d+1, y, x]
                    
                    denom = c0 + c2 - 2 * c1
                    if abs(denom) > 1e-6:
                        offset = (c0 - c2) / (2 * denom)
                        refined[y, x] = d + offset
        
        return refined
    
    def _to_gray(self, image: np.ndarray) -> np.ndarray:
        if len(image.shape) == 3:
            return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        return image
    
    def _normalize_depth(self, depth_map: np.ndarray) -> np.ndarray:
        valid_mask = ~np.isnan(depth_map) & ~np.isinf(depth_map)
        
        if np.any(valid_mask):
            min_val = np.min(depth_map[valid_mask])
            max_val = np.max(depth_map[valid_mask])
            
            if max_val > min_val:
                depth_map[valid_mask] = (depth_map[valid_mask] - min_val) / (max_val - min_val)
            else:
                depth_map[valid_mask] = 0.5
        
        depth_map[~valid_mask] = 0
        
        return depth_map
    
    def apply_wls_filter(self, depth_map: np.ndarray, 
                          guidance_image: Optional[np.ndarray] = None,
                          lambda_val: float = 8000.0,
                          sigma: float = 1.0) -> np.ndarray:
        if guidance_image is None:
            guidance_image = self.lf_data[self.center_vy, self.center_vx]
        
        wls_filter = cv2.ximgproc.createDisparityWLSFilterGeneric(False)
        wls_filter.setLambda(lambda_val)
        wls_filter.setSigmaColor(sigma)
        
        depth_16u = (depth_map * 65535).astype(np.uint16)
        filtered = wls_filter.filter(depth_16u, guidance_image)
        
        return filtered.astype(np.float32) / 65535.0
    
    def apply_joint_bilateral_filter(self, depth_map: np.ndarray,
                                      guidance_image: Optional[np.ndarray] = None,
                                      sigma_color: float = 75.0,
                                      sigma_space: float = 75.0) -> np.ndarray:
        if guidance_image is None:
            guidance_image = self.lf_data[self.center_vy, self.center_vx]
        
        guidance_gray = self._to_gray(guidance_image)
        
        depth_norm = (depth_map * 255).astype(np.uint8)
        
        filtered = cv2.ximgproc.jointBilateralFilter(
            guidance_gray, depth_norm, -1, sigma_color, sigma_space
        )
        
        return filtered.astype(np.float32) / 255.0


def create_guided_depth_refinement(depth_map: np.ndarray,
                                     guidance: np.ndarray,
                                     iterations: int = 3) -> np.ndarray:
    result = depth_map.copy()
    
    for _ in range(iterations):
        result = cv2.ximgproc.guidedFilter(
            guidance, result.astype(np.float32), 9, 0.1
        )
    
    return result


def fuse_depth_maps(depth_maps: list, weights: Optional[list] = None) -> np.ndarray:
    if weights is None:
        weights = [1.0] * len(depth_maps)
    
    total_weight = sum(weights)
    weights = [w / total_weight for w in weights]
    
    fused = np.zeros_like(depth_maps[0], dtype=np.float32)
    
    for depth_map, weight in zip(depth_maps, weights):
        fused += depth_map * weight
    
    return fused


def depth_to_pointcloud(depth_map: np.ndarray,
                         image: np.ndarray,
                         focal_length: float = 500.0,
                         scale: float = 1.0) -> Tuple[np.ndarray, np.ndarray]:
    h, w = depth_map.shape
    cx, cy = w // 2, h // 2
    
    y_coords, x_coords = np.mgrid[0:h, 0:w]
    
    x_3d = (x_coords - cx) * depth_map * scale / focal_length
    y_3d = (y_coords - cy) * depth_map * scale / focal_length
    z_3d = depth_map * scale
    
    points = np.stack([x_3d, y_3d, z_3d], axis=-1)
    colors = image.reshape(-1, 3) if len(image.shape) == 3 else None
    
    return points.reshape(-1, 3), colors


def save_pointcloud_ply(filename: str, points: np.ndarray, colors: Optional[np.ndarray] = None):
    with open(filename, 'w') as f:
        f.write("ply\n")
        f.write("format ascii 1.0\n")
        f.write(f"element vertex {len(points)}\n")
        f.write("property float x\n")
        f.write("property float y\n")
        f.write("property float z\n")
        if colors is not None:
            f.write("property uchar red\n")
            f.write("property uchar green\n")
            f.write("property uchar blue\n")
        f.write("end_header\n")
        
        for i in range(len(points)):
            line = f"{points[i, 0]} {points[i, 1]} {points[i, 2]}"
            if colors is not None:
                line += f" {int(colors[i, 2])} {int(colors[i, 1])} {int(colors[i, 0])}"
            f.write(line + "\n")
