import numpy as np
import cv2
from scipy.ndimage import gaussian_filter, median_filter
from scipy.signal import medfilt2d
from typing import List, Tuple, Optional
from lightfield import LightField
from depth_estimation import DepthEstimator


class MultiViewFusion:
    def __init__(self, light_field: LightField):
        self.lf = light_field
        self.estimator = DepthEstimator(light_field)
        
    def compute_consistency_map(self, depth_maps: List[np.ndarray], 
                                threshold: float = 0.1) -> np.ndarray:
        if len(depth_maps) < 2:
            return np.ones_like(depth_maps[0])
        
        depth_stack = np.stack(depth_maps)
        mean_depth = np.mean(depth_stack, axis=0)
        std_depth = np.std(depth_stack, axis=0)
        
        consistency = np.exp(-(std_depth ** 2) / (2 * threshold ** 2))
        return np.clip(consistency, 0, 1)
    
    def weighted_fusion(self, depth_maps: List[np.ndarray], 
                        confidences: List[np.ndarray]) -> Tuple[np.ndarray, np.ndarray]:
        if len(depth_maps) != len(confidences):
            raise ValueError("Number of depth maps must match number of confidence maps")
        
        depth_stack = np.stack(depth_maps)
        conf_stack = np.stack(confidences)
        
        conf_sum = np.sum(conf_stack, axis=0) + 1e-8
        fused_depth = np.sum(depth_stack * conf_stack, axis=0) / conf_sum
        fused_conf = np.mean(conf_stack, axis=0)
        
        return fused_depth, fused_conf
    
    def bilateral_fusion(self, depth_maps: List[np.ndarray], 
                         confidences: List[np.ndarray],
                         guidance: Optional[np.ndarray] = None,
                         sigma_spatial: float = 5.0,
                         sigma_range: float = 0.1) -> Tuple[np.ndarray, np.ndarray]:
        fused_depth, fused_conf = self.weighted_fusion(depth_maps, confidences)
        
        if guidance is None:
            guidance = self.lf.get_center_view()
        
        guidance_uint8 = (guidance * 255).astype(np.uint8)
        depth_uint8 = ((fused_depth - fused_depth.min()) / 
                       (fused_depth.max() - fused_depth.min() + 1e-8) * 255).astype(np.uint8)
        
        smoothed = cv2.bilateralFilter(depth_uint8, d=9, 
                                       sigmaColor=int(sigma_range * 100),
                                       sigmaSpace=int(sigma_spatial))
        
        smoothed = smoothed.astype(np.float32) / 255.0
        smoothed = smoothed * (fused_depth.max() - fused_depth.min()) + fused_depth.min()
        
        return smoothed, fused_conf
    
    def cross_view_fusion(self, patch_size: int = 7) -> Tuple[np.ndarray, np.ndarray]:
        center_view = self.lf.get_center_view()
        all_depths = []
        all_confs = []
        
        for r in range(self.lf.num_rows):
            for c in range(self.lf.num_cols):
                if r == self.lf.num_rows // 2 and c == self.lf.num_cols // 2:
                    continue
                
                sub_lf = LightField(self.lf.images[r:r+1, c:c+1, :, :])
                sub_est = DepthEstimator(sub_lf)
                
                dr = r - self.lf.num_rows // 2
                dc = c - self.lf.num_cols // 2
                
                depth, conf = self.estimator.estimate_depth_from_focus(
                    num_planes=15, alpha_range=(-1.5, 1.5))
                
                M = np.float32([[1, 0, -dc * 5], [0, 1, -dr * 5]])
                depth_aligned = cv2.warpAffine(depth, M, 
                                               (self.lf.width, self.lf.height))
                conf_aligned = cv2.warpAffine(conf, M, 
                                              (self.lf.width, self.lf.height))
                
                all_depths.append(depth_aligned)
                all_confs.append(conf_aligned)
        
        if all_depths:
            fused_depth, fused_conf = self.weighted_fusion(all_depths, all_confs)
            consistency = self.compute_consistency_map(all_depths)
            fused_conf = fused_conf * consistency
        else:
            depth, conf = self.estimator.estimate_depth_from_focus()
            return depth, conf
        
        return fused_depth, fused_conf
    
    def multi_method_fusion(self, methods: List[str] = None) -> Tuple[np.ndarray, np.ndarray]:
        if methods is None:
            methods = ['focus', 'defocus', 'disparity']
        
        depth_maps = []
        confidences = []
        
        for method in methods:
            if method == 'focus':
                depth, conf = self.estimator.estimate_depth_from_focus()
            elif method == 'defocus':
                depth, conf = self.estimator.estimate_depth_from_defocus()
            elif method == 'disparity':
                depth, conf = self.estimator.estimate_disparity()
            else:
                continue
            
            depth_norm = (depth - depth.min()) / (depth.max() - depth.min() + 1e-8)
            depth_maps.append(depth_norm)
            confidences.append(conf)
        
        consistency = self.compute_consistency_map(depth_maps)
        fused_depth, fused_conf = self.weighted_fusion(depth_maps, confidences)
        fused_conf = fused_conf * consistency
        
        return fused_depth, fused_conf
    
    def refine_depth(self, depth: np.ndarray, confidence: np.ndarray,
                     confidence_threshold: float = 0.3) -> np.ndarray:
        mask = confidence > confidence_threshold
        
        refined = depth.copy()
        
        if np.sum(~mask) > 0:
            from scipy.interpolate import griddata
            
            y, x = np.mgrid[0:depth.shape[0], 0:depth.shape[1]]
            
            valid_points = np.column_stack([x[mask], y[mask]])
            valid_values = depth[mask]
            
            xi = np.column_stack([x[~mask], y[~mask]])
            
            if len(valid_points) > 3 and len(xi) > 0:
                try:
                    interpolated = griddata(valid_points, valid_values, xi, 
                                            method='linear', fill_value=np.mean(valid_values))
                    refined[~mask] = interpolated
                except:
                    pass
        
        refined = median_filter(refined, size=3)
        refined = gaussian_filter(refined, sigma=0.5)
        
        return refined
