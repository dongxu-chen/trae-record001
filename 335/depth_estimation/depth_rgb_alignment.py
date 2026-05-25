import numpy as np
import cv2
from typing import Optional, Tuple, Dict
from dataclasses import dataclass

from .camera_calibration import CameraCalibrator


@dataclass
class AlignmentConfig:
    apply_alignment: bool = True
    rgb_offset_x: int = 0
    rgb_offset_y: int = 0
    scale_depth_to_rgb: bool = True
    interpolation: int = cv2.INTER_LINEAR
    generate_aligned_output: bool = True
    colormap: int = cv2.COLORMAP_JET
    alpha_blend: float = 0.5
    edge_threshold: float = 0.1


class DepthRGBAligner:
    def __init__(self, 
                 calibrator: CameraCalibrator,
                 config: AlignmentConfig = AlignmentConfig()):
        self.calibrator = calibrator
        self.config = config
    
    def align(self, rgb_image: np.ndarray, 
              depth_map: np.ndarray) -> Dict[str, np.ndarray]:
        h_rgb, w_rgb = rgb_image.shape[:2]
        h_depth, w_depth = depth_map.shape
        
        if (h_rgb != h_depth or w_rgb != w_depth) and self.config.scale_depth_to_rgb:
            depth_aligned = cv2.resize(
                depth_map, (w_rgb, h_rgb),
                interpolation=self.config.interpolation
            )
        else:
            depth_aligned = depth_map.copy()
        
        if self.config.rgb_offset_x != 0 or self.config.rgb_offset_y != 0:
            M = np.float32([
                [1, 0, self.config.rgb_offset_x],
                [0, 1, self.config.rgb_offset_y]
            ])
            rgb_image = cv2.warpAffine(
                rgb_image, M, (w_rgb, h_rgb),
                flags=self.config.interpolation,
                borderMode=cv2.BORDER_REPLICATE
            )
        
        return {
            'rgb_aligned': rgb_image,
            'depth_aligned': depth_aligned,
            'depth_colored': self._apply_colormap(depth_aligned)
        }
    
    def _apply_colormap(self, depth_map: np.ndarray) -> np.ndarray:
        depth_normalized = cv2.normalize(
            depth_map, None, 0, 255, 
            cv2.NORM_MINMAX, dtype=cv2.CV_8U
        )
        return cv2.applyColorMap(depth_normalized, self.config.colormap)
    
    def generate_aligned_depth_rgb(self, 
                                    rgb_image: np.ndarray,
                                    depth_map: np.ndarray) -> np.ndarray:
        aligned = self.align(rgb_image, depth_map)
        
        rgb_float = aligned['rgb_aligned'].astype(np.float32) / 255.0
        depth_color_float = aligned['depth_colored'].astype(np.float32) / 255.0
        
        alpha = self.config.alpha_blend
        blended = alpha * depth_color_float + (1 - alpha) * rgb_float
        blended = (blended * 255).astype(np.uint8)
        
        return blended
    
    def generate_depth_overlay(self,
                                rgb_image: np.ndarray,
                                depth_map: np.ndarray,
                                alpha: Optional[float] = None) -> np.ndarray:
        if alpha is None:
            alpha = self.config.alpha_blend
        
        h, w = rgb_image.shape[:2]
        
        if depth_map.shape[:2] != (h, w):
            depth_resized = cv2.resize(
                depth_map, (w, h),
                interpolation=cv2.INTER_LINEAR
            )
        else:
            depth_resized = depth_map
        
        depth_colored = self._apply_colormap(depth_resized)
        
        overlay = cv2.addWeighted(
            rgb_image, 1 - alpha,
            depth_colored, alpha, 0
        )
        
        return overlay
    
    def generate_edge_aware_overlay(self,
                                     rgb_image: np.ndarray,
                                     depth_map: np.ndarray,
                                     alpha: Optional[float] = None) -> np.ndarray:
        if alpha is None:
            alpha = self.config.alpha_blend
        
        h, w = rgb_image.shape[:2]
        
        if depth_map.shape[:2] != (h, w):
            depth_resized = cv2.resize(
                depth_map, (w, h),
                interpolation=cv2.INTER_LINEAR
            )
        else:
            depth_resized = depth_map
        
        depth_norm = cv2.normalize(
            depth_resized, None, 0, 255,
            cv2.NORM_MINMAX, dtype=cv2.CV_8U
        )
        
        gx = cv2.Sobel(depth_norm, cv2.CV_64F, 1, 0, ksize=3)
        gy = cv2.Sobel(depth_norm, cv2.CV_64F, 0, 1, ksize=3)
        magnitude = np.sqrt(gx ** 2 + gy ** 2)
        
        max_mag = np.max(magnitude)
        if max_mag > 0:
            edge_mask = magnitude / max_mag
        else:
            edge_mask = np.zeros_like(magnitude)
        
        edge_mask = (edge_mask > self.config.edge_threshold).astype(np.float32)
        edge_mask = cv2.GaussianBlur(edge_mask, (5, 5), 0)
        
        depth_colored = self._apply_colormap(depth_resized)
        
        rgb_float = rgb_image.astype(np.float32) / 255.0
        depth_float = depth_colored.astype(np.float32) / 255.0
        
        blend_weight = alpha * (1 - edge_mask[..., np.newaxis])
        overlay = rgb_float * (1 - blend_weight) + depth_float * blend_weight
        overlay = (overlay * 255).astype(np.uint8)
        
        return overlay
    
    def depth_to_rgb_color(self, 
                            depth_map: np.ndarray,
                            rgb_image: np.ndarray) -> np.ndarray:
        h, w = depth_map.shape[:2]
        
        if rgb_image.shape[:2] != (h, w):
            rgb_resized = cv2.resize(
                rgb_image, (w, h),
                interpolation=cv2.INTER_LINEAR
            )
        else:
            rgb_resized = rgb_image.copy()
        
        colored_depth = np.zeros((h, w, 3), dtype=np.float32)
        
        valid_mask = (depth_map > 0) & np.isfinite(depth_map)
        
        depth_min = np.min(depth_map[valid_mask]) if np.any(valid_mask) else 0
        depth_max = np.max(depth_map[valid_mask]) if np.any(valid_mask) else 1
        
        if depth_max > depth_min:
            normalized_depth = (depth_map - depth_min) / (depth_max - depth_min)
        else:
            normalized_depth = np.zeros_like(depth_map)
        
        colored_depth[..., 0] = normalized_depth * rgb_resized[..., 0]
        colored_depth[..., 1] = normalized_depth * rgb_resized[..., 1]
        colored_depth[..., 2] = normalized_depth * rgb_resized[..., 2]
        
        colored_depth[~valid_mask] = 0
        
        return (colored_depth * 255).astype(np.uint8)
    
    def generate_pointcloud_colored(self,
                                     rgb_image: np.ndarray,
                                     depth_map: np.ndarray) -> Dict:
        aligned = self.align(rgb_image, depth_map)
        depth_aligned = aligned['depth_aligned']
        rgb_aligned = aligned['rgb_aligned']
        
        points_3d, valid_mask = self.calibrator.backproject_depth_map(depth_aligned)
        
        rgb_normalized = rgb_aligned.astype(np.float32) / 255.0
        
        if len(rgb_normalized.shape) == 3:
            colors = rgb_normalized[valid_mask]
        else:
            colors = np.stack([
                rgb_normalized[valid_mask],
                rgb_normalized[valid_mask],
                rgb_normalized[valid_mask]
            ], axis=-1)
        
        return {
            'points': points_3d[valid_mask],
            'colors': colors,
            'valid_mask': valid_mask
        }
    
    def get_depth_at_rgb_pixel(self, 
                                depth_map: np.ndarray,
                                rgb_pixel: Tuple[int, int]) -> float:
        u, v = rgb_pixel
        
        if self.config.rgb_offset_x != 0 or self.config.rgb_offset_y != 0:
            u += self.config.rgb_offset_x
            v += self.config.rgb_offset_y
        
        u = max(0, min(u, depth_map.shape[1] - 1))
        v = max(0, min(v, depth_map.shape[0] - 1))
        
        return float(depth_map[v, u])
    
    def create_rgbd_image(self, 
                           rgb_image: np.ndarray,
                           depth_map: np.ndarray) -> np.ndarray:
        h_rgb, w_rgb = rgb_image.shape[:2]
        
        if depth_map.shape[:2] != (h_rgb, w_rgb):
            depth_resized = cv2.resize(
                depth_map, (w_rgb, h_rgb),
                interpolation=cv2.INTER_LINEAR
            )
        else:
            depth_resized = depth_map
        
        if len(rgb_image.shape) == 2:
            rgb_image = cv2.cvtColor(rgb_image, cv2.COLOR_GRAY2BGR)
        
        rgbd = np.zeros((h_rgb, w_rgb, 4), dtype=np.float32)
        rgbd[..., :3] = rgb_image.astype(np.float32) / 255.0
        rgbd[..., 3] = depth_resized
        
        return rgbd
    
    def save_aligned_output(self, 
                             rgb_image: np.ndarray,
                             depth_map: np.ndarray,
                             output_dir: str) -> Dict[str, str]:
        import os
        
        aligned = self.align(rgb_image, depth_map)
        
        os.makedirs(output_dir, exist_ok=True)
        
        rgb_path = os.path.join(output_dir, "rgb_aligned.png")
        depth_path = os.path.join(output_dir, "depth_aligned.png")
        depth_colored_path = os.path.join(output_dir, "depth_colored.png")
        overlay_path = os.path.join(output_dir, "overlay.png")
        
        cv2.imwrite(rgb_path, aligned['rgb_aligned'])
        
        depth_vis = cv2.normalize(
            aligned['depth_aligned'], None, 0, 255,
            cv2.NORM_MINMAX, dtype=cv2.CV_8U
        )
        cv2.imwrite(depth_path, depth_vis)
        
        cv2.imwrite(depth_colored_path, aligned['depth_colored'])
        
        overlay = self.generate_depth_overlay(rgb_image, depth_map)
        cv2.imwrite(overlay_path, overlay)
        
        return {
            'rgb': rgb_path,
            'depth': depth_path,
            'depth_colored': depth_colored_path,
            'overlay': overlay_path
        }
