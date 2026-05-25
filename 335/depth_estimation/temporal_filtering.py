import numpy as np
import cv2
from collections import deque
from typing import Optional, Tuple, List
from dataclasses import dataclass

from config.config import (
    TemporalSmoothingConfig,
    TemporalHoleFillingConfig,
    PostProcessingConfig,
)
from .post_processing import DepthPostProcessor


@dataclass
class FrameData:
    frame_index: int
    rgb_image: np.ndarray
    depth_map: np.ndarray
    invalid_mask: np.ndarray
    flow: Optional[np.ndarray] = None


class TemporalHoleFiller:
    def __init__(self, config: TemporalHoleFillingConfig, post_config: PostProcessingConfig):
        self.config = config
        self.post_config = post_config
        self.frame_history: deque = deque(maxlen=config.num_frames)
        self.frame_count = 0

    def process(self, depth_map: np.ndarray, rgb_image: np.ndarray) -> np.ndarray:
        self.frame_count += 1
        
        current_invalid = self._get_invalid_mask(depth_map)
        
        if not self.config.apply_temporal_hole_filling or len(self.frame_history) < self.config.min_valid_frames:
            self._add_to_history(rgb_image, depth_map, current_invalid)
            return depth_map
        
        filled = self._fill_holes_temporal(depth_map, rgb_image, current_invalid)
        
        if self.config.fallback_to_spatial:
            still_invalid = self._get_invalid_mask(filled)
            if np.any(still_invalid):
                filled = self._spatial_fallback(filled, still_invalid)
        
        self._add_to_history(rgb_image, filled, self._get_invalid_mask(filled))
        
        return filled

    def _fill_holes_temporal(self, depth_map: np.ndarray, rgb_image: np.ndarray, 
                            invalid_mask: np.ndarray) -> np.ndarray:
        if not np.any(invalid_mask):
            return depth_map
        
        filled = depth_map.copy()
        
        candidate_values = []
        candidate_weights = []
        
        for frame_data in self.frame_history:
            warped_depth, warped_mask, warp_weight = self._warp_previous_frame(
                frame_data, rgb_image, depth_map.shape
            )
            
            if warped_depth is None:
                continue
            
            valid_for_fill = warped_mask & invalid_mask
            
            if np.any(valid_for_fill):
                candidate_values.append(warped_depth)
                candidate_weights.append(warp_weight * valid_for_fill.astype(np.float32))
        
        if len(candidate_values) < self.config.min_valid_frames:
            return depth_map
        
        total_weight = np.sum(np.stack(candidate_weights), axis=0)
        min_valid_mask = total_weight > 0
        
        if not np.any(min_valid_mask & invalid_mask):
            return depth_map
        
        weighted_sum = np.zeros_like(depth_map, dtype=np.float32)
        for val, w in zip(candidate_values, candidate_weights):
            weighted_sum += val.astype(np.float32) * w
        
        final_fill = np.zeros_like(depth_map, dtype=np.float32)
        valid_total = total_weight > 1e-6
        final_fill[valid_total] = weighted_sum[valid_total] / total_weight[valid_total]
        
        fill_mask = invalid_mask & valid_total
        filled[fill_mask] = final_fill[fill_mask]
        
        return filled

    def _warp_previous_frame(self, prev_frame: FrameData, current_rgb: np.ndarray,
                            target_shape: Tuple[int, int]) -> Tuple[Optional[np.ndarray], np.ndarray, float]:
        try:
            if self.config.use_warping:
                flow = self._compute_optical_flow(prev_frame.rgb_image, current_rgb)
                
                h, w = target_shape
                y_coords, x_coords = np.mgrid[0:h, 0:w].astype(np.float32)
                
                map_x = x_coords + flow[..., 0]
                map_y = y_coords + flow[..., 1]
                
                warped_depth = cv2.remap(
                    prev_frame.depth_map.astype(np.float32),
                    map_x, map_y,
                    interpolation=cv2.INTER_LINEAR,
                    borderMode=cv2.BORDER_CONSTANT,
                    borderValue=0
                )
                
                warped_invalid = cv2.remap(
                    prev_frame.invalid_mask.astype(np.float32),
                    map_x, map_y,
                    interpolation=cv2.INTER_NEAREST,
                    borderMode=cv2.BORDER_CONSTANT,
                    borderValue=1
                ).astype(bool)
                
                flow_magnitude = np.linalg.norm(flow, axis=2)
                warp_weight = np.exp(-flow_magnitude / 10.0)
                avg_warp_weight = float(np.mean(warp_weight))
                
            else:
                warped_depth = prev_frame.depth_map.copy()
                warped_invalid = prev_frame.invalid_mask.copy()
                avg_warp_weight = 1.0
            
            warped_invalid = warped_invalid | self._get_invalid_mask(warped_depth)
            valid_mask = ~warped_invalid
            
            return warped_depth, valid_mask, avg_warp_weight
            
        except Exception as e:
            return None, np.zeros(target_shape, dtype=bool), 0.0

    def _compute_optical_flow(self, prev_rgb: np.ndarray, current_rgb: np.ndarray) -> np.ndarray:
        prev_gray = cv2.cvtColor(prev_rgb, cv2.COLOR_BGR2GRAY)
        curr_gray = cv2.cvtColor(current_rgb, cv2.COLOR_BGR2GRAY)
        
        if prev_gray.shape != curr_gray.shape:
            prev_gray = cv2.resize(prev_gray, (curr_gray.shape[1], curr_gray.shape[0]))
        
        flow = cv2.calcOpticalFlowFarneback(
            prev_gray, curr_gray,
            None,
            pyr_scale=0.5,
            levels=3,
            winsize=15,
            iterations=3,
            poly_n=5,
            poly_sigma=1.2,
            flags=0
        )
        
        return flow

    def _spatial_fallback(self, depth_map: np.ndarray, invalid_mask: np.ndarray) -> np.ndarray:
        if not np.any(invalid_mask):
            return depth_map
        
        depth_normalized = DepthPostProcessor._to_uint8(depth_map)
        mask_uint8 = invalid_mask.astype(np.uint8) * 255
        
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
        mask_dilated = cv2.dilate(mask_uint8, kernel, iterations=1)
        
        inpainted = cv2.inpaint(depth_normalized, mask_dilated, 3, cv2.INPAINT_TELEA)
        
        result = DepthPostProcessor._from_uint8(inpainted, depth_map)
        
        return result

    def _get_invalid_mask(self, depth_map: np.ndarray) -> np.ndarray:
        mask = np.zeros(depth_map.shape, dtype=bool)
        mask[np.isnan(depth_map)] = True
        mask[np.isinf(depth_map)] = True
        mask[depth_map < self.post_config.min_depth] = True
        mask[depth_map > self.post_config.max_depth] = True
        mask[depth_map <= 0] = True
        return mask

    def _add_to_history(self, rgb_image: np.ndarray, depth_map: np.ndarray, invalid_mask: np.ndarray) -> None:
        self.frame_history.append(FrameData(
            frame_index=self.frame_count,
            rgb_image=rgb_image.copy(),
            depth_map=depth_map.copy(),
            invalid_mask=invalid_mask.copy()
        ))

    def reset(self) -> None:
        self.frame_history.clear()
        self.frame_count = 0

    def get_stats(self) -> dict:
        return {
            "frame_count": self.frame_count,
            "history_size": len(self.frame_history),
            "max_history": self.config.num_frames,
            "min_valid_frames": self.config.min_valid_frames,
            "use_warping": self.config.use_warping
        }


class TemporalSmoother:
    def __init__(self, config: TemporalSmoothingConfig):
        self.config = config
        self.previous_depth: Optional[np.ndarray] = None
        self.previous_rgb: Optional[np.ndarray] = None
        self.depth_history: deque = deque(maxlen=config.max_history)
        self.frame_count = 0

    def process(self, depth_map: np.ndarray, rgb_image: Optional[np.ndarray] = None) -> np.ndarray:
        self.frame_count += 1
        
        if not self.config.apply_temporal_smoothing:
            return depth_map
        
        if self.previous_depth is None:
            self._update_history(depth_map, rgb_image)
            return depth_map
        
        smoothed = self._exponential_smoothing(depth_map, rgb_image)
        
        self._update_history(smoothed, rgb_image)
        
        return smoothed

    def _exponential_smoothing(self, current_depth: np.ndarray, 
                                current_rgb: Optional[np.ndarray]) -> np.ndarray:
        alpha = self.config.alpha
        
        if self.config.adaptive_alpha and current_rgb is not None and self.previous_rgb is not None:
            alpha = self._compute_adaptive_alpha(current_depth, current_rgb)
        
        if self.config.motion_compensation and current_rgb is not None and self.previous_rgb is not None:
            warped_prev = self._motion_compensate(current_depth, current_rgb)
            if warped_prev is not None:
                smoothed = alpha * current_depth + (1 - alpha) * warped_prev
            else:
                smoothed = alpha * current_depth + (1 - alpha) * self.previous_depth
        else:
            smoothed = alpha * current_depth + (1 - alpha) * self.previous_depth
        
        if self.config.edge_threshold > 0:
            smoothed = self._edge_aware_smoothing(smoothed, current_depth, current_rgb)
        
        return smoothed.astype(np.float32)

    def _compute_adaptive_alpha(self, current_depth: np.ndarray, current_rgb: np.ndarray) -> float:
        base_alpha = self.config.alpha
        
        motion = self._compute_motion(current_rgb)
        depth_change = self._compute_depth_change(current_depth)
        
        motion_factor = min(motion / self.config.motion_threshold, 1.0)
        depth_factor = min(depth_change / (self.config.edge_threshold * 10), 1.0)
        
        alpha = base_alpha + (1.0 - base_alpha) * max(motion_factor, depth_factor)
        alpha = max(0.1, min(0.9, alpha))
        
        return alpha

    def _compute_motion(self, current_rgb: np.ndarray) -> float:
        if self.previous_rgb is None:
            return 0.0
        
        prev_gray = cv2.cvtColor(self.previous_rgb, cv2.COLOR_BGR2GRAY).astype(np.float32)
        curr_gray = cv2.cvtColor(current_rgb, cv2.COLOR_BGR2GRAY).astype(np.float32)
        
        if prev_gray.shape != curr_gray.shape:
            prev_gray = cv2.resize(prev_gray, (curr_gray.shape[1], curr_gray.shape[0]))
        
        diff = np.abs(curr_gray - prev_gray)
        mean_diff = float(np.mean(diff))
        
        return mean_diff

    def _compute_depth_change(self, current_depth: np.ndarray) -> float:
        if self.previous_depth is None:
            return 0.0
        
        prev_depth = self.previous_depth
        curr_depth = current_depth
        
        if prev_depth.shape != curr_depth.shape:
            prev_depth = cv2.resize(prev_depth, (curr_depth.shape[1], curr_depth.shape[0]))
        
        valid_mask = (~np.isnan(prev_depth)) & (~np.isnan(curr_depth))
        if not np.any(valid_mask):
            return 0.0
        
        diff = np.abs(curr_depth[valid_mask] - prev_depth[valid_mask])
        mean_diff = float(np.mean(diff))
        
        return mean_diff

    def _motion_compensate(self, current_depth: np.ndarray, current_rgb: np.ndarray) -> Optional[np.ndarray]:
        try:
            prev_gray = cv2.cvtColor(self.previous_rgb, cv2.COLOR_BGR2GRAY)
            curr_gray = cv2.cvtColor(current_rgb, cv2.COLOR_BGR2GRAY)
            
            if prev_gray.shape != curr_gray.shape:
                prev_gray = cv2.resize(prev_gray, (curr_gray.shape[1], curr_gray.shape[0]))
            
            flow = cv2.calcOpticalFlowFarneback(
                prev_gray, curr_gray,
                None,
                pyr_scale=0.5,
                levels=2,
                winsize=10,
                iterations=2,
                poly_n=5,
                poly_sigma=1.1,
                flags=0
            )
            
            flow_magnitude = np.mean(np.linalg.norm(flow, axis=2))
            if flow_magnitude > self.config.motion_threshold * 2:
                return None
            
            h, w = current_depth.shape
            y_coords, x_coords = np.mgrid[0:h, 0:w].astype(np.float32)
            
            map_x = x_coords + flow[..., 0]
            map_y = y_coords + flow[..., 1]
            
            warped_prev = cv2.remap(
                self.previous_depth.astype(np.float32),
                map_x, map_y,
                interpolation=cv2.INTER_LINEAR,
                borderMode=cv2.BORDER_REPLICATE
            )
            
            return warped_prev
            
        except Exception:
            return None

    def _edge_aware_smoothing(self, smoothed: np.ndarray, current_depth: np.ndarray,
                             current_rgb: Optional[np.ndarray]) -> np.ndarray:
        depth_edges = self._detect_depth_edges(current_depth)
        
        if current_rgb is not None:
            rgb_edges = self._detect_rgb_edges(current_rgb)
            combined_edges = np.maximum(depth_edges, rgb_edges)
        else:
            combined_edges = depth_edges
        
        edge_mask = combined_edges > self.config.edge_threshold
        
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
        edge_mask = cv2.dilate(edge_mask.astype(np.uint8), kernel).astype(bool)
        
        result = smoothed.copy()
        result[edge_mask] = current_depth[edge_mask]
        
        return result

    def _detect_depth_edges(self, depth_map: np.ndarray) -> np.ndarray:
        depth_clean = np.nan_to_num(depth_map, nan=0.0)
        depth_norm = cv2.normalize(depth_clean, None, 0, 255, cv2.NORM_MINMAX, dtype=cv2.CV_8U)
        gx = cv2.Sobel(depth_norm, cv2.CV_64F, 1, 0, ksize=3)
        gy = cv2.Sobel(depth_norm, cv2.CV_64F, 0, 1, ksize=3)
        magnitude = np.sqrt(gx ** 2 + gy ** 2)
        magnitude = cv2.normalize(magnitude, None, 0, 1, cv2.NORM_MINMAX, dtype=cv2.CV_32F)
        return magnitude

    def _detect_rgb_edges(self, rgb_image: np.ndarray) -> np.ndarray:
        gray = cv2.cvtColor(rgb_image, cv2.COLOR_BGR2GRAY)
        gx = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
        gy = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=3)
        magnitude = np.sqrt(gx ** 2 + gy ** 2)
        magnitude = cv2.normalize(magnitude, None, 0, 1, cv2.NORM_MINMAX, dtype=cv2.CV_32F)
        return magnitude

    def _update_history(self, depth_map: np.ndarray, rgb_image: Optional[np.ndarray]) -> None:
        self.previous_depth = depth_map.copy()
        if rgb_image is not None:
            self.previous_rgb = rgb_image.copy()
        self.depth_history.append(depth_map.copy())

    def reset(self) -> None:
        self.previous_depth = None
        self.previous_rgb = None
        self.depth_history.clear()
        self.frame_count = 0

    def get_stats(self) -> dict:
        return {
            "frame_count": self.frame_count,
            "history_size": len(self.depth_history),
            "alpha": self.config.alpha,
            "adaptive_alpha": self.config.adaptive_alpha,
            "motion_compensation": self.config.motion_compensation
        }


class TemporalFilterPipeline:
    def __init__(self, 
                 smoothing_config: TemporalSmoothingConfig,
                 hole_filling_config: TemporalHoleFillingConfig,
                 post_config: PostProcessingConfig):
        self.smoother = TemporalSmoother(smoothing_config)
        self.hole_filler = TemporalHoleFiller(hole_filling_config, post_config)

    def process(self, depth_map: np.ndarray, rgb_image: np.ndarray) -> np.ndarray:
        result = self.hole_filler.process(depth_map, rgb_image)
        result = self.smoother.process(result, rgb_image)
        return result

    def reset(self) -> None:
        self.smoother.reset()
        self.hole_filler.reset()

    def get_stats(self) -> dict:
        return {
            "smoothing": self.smoother.get_stats(),
            "hole_filling": self.hole_filler.get_stats()
        }
