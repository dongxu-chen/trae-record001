import torch
import torch.nn.functional as F
import numpy as np
from typing import Optional, Tuple, List

from .raft import (
    bilinear_warp,
    compute_occlusion_mask,
    compute_occlusion_mask_advanced,
    compute_occlusion_confidence,
    fill_occlusion_regions,
    adaptive_blend_frames,
    warp_flow
)
from .motion_blur import apply_anisotropic_motion_blur, apply_motion_blur_pyramid
from .config import InterpolationConfig


class FrameInterpolator:
    def __init__(self, config: InterpolationConfig, raft_model=None):
        self.config = config
        self.device = config.device
        self.raft_model = raft_model
        self._cache = {}
    
    def _clear_cache(self):
        self._cache.clear()
    
    def estimate_optical_flow(self, frame1: torch.Tensor, frame2: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
        if self.raft_model is None:
            raise ValueError('RAFT model is not initialized')
        
        if self.config.bidirectional_flow:
            flow_forward = self.raft_model.estimate_flow(frame1, frame2, iters=self.config.raft_iters)
            flow_backward = self.raft_model.estimate_flow(frame2, frame1, iters=self.config.raft_iters)
        else:
            flow_forward = self.raft_model.estimate_flow(frame1, frame2, iters=self.config.raft_iters)
            flow_backward = -flow_forward
        
        return flow_forward, flow_backward
    
    def get_occlusion_mask(self, flow_forward: torch.Tensor, flow_backward: torch.Tensor) -> Optional[torch.Tensor]:
        if not self.config.occlusion_detection:
            return None
        
        occlusion_mask = compute_occlusion_mask_advanced(
            flow_forward, flow_backward, 
            threshold=self.config.occlusion_threshold,
            edge_aware=True
        )
        
        return occlusion_mask
    
    def compute_intermediate_flow(self, flow_forward: torch.Tensor, 
                                  flow_backward: torch.Tensor,
                                  t: float) -> Tuple[torch.Tensor, torch.Tensor]:
        flow_t_forward = flow_forward * t
        flow_t_backward = flow_backward * (1 - t)
        
        return flow_t_forward, flow_t_backward
    
    def warp_frames(self, frame1: torch.Tensor, frame2: torch.Tensor,
                    flow_t_forward: torch.Tensor, flow_t_backward: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
        warped1 = bilinear_warp(frame1, flow_t_forward)
        warped2 = bilinear_warp(frame2, flow_t_backward)
        
        return warped1, warped2
    
    def blend_with_occlusion_handling(self, warped1: torch.Tensor, warped2: torch.Tensor,
                                       frame1: torch.Tensor, frame2: torch.Tensor,
                                       flow_forward: torch.Tensor, flow_backward: torch.Tensor,
                                       t: float, occlusion_mask: Optional[torch.Tensor]) -> torch.Tensor:
        if not self.config.occlusion_detection or occlusion_mask is None:
            alpha = t
            return (1 - alpha) * warped1 + alpha * warped2
        
        blended, confidence = adaptive_blend_frames(
            warped1, warped2, flow_forward, flow_backward, t
        )
        
        occluded_pixels = (occlusion_mask > 0.5).float()
        
        if occluded_pixels.sum() > 0:
            filled = fill_occlusion_regions(
                warped1, warped2,
                flow_forward, flow_backward,
                occlusion_mask,
                frame1, frame2, t
            )
            
            blended = blended * (1 - occluded_pixels) + filled * occluded_pixels
        
        return blended
    
    def apply_motion_blur(self, frame: torch.Tensor, 
                           flow_forward: torch.Tensor, flow_backward: torch.Tensor,
                           t: float) -> torch.Tensor:
        if not self.config.motion_blur:
            return frame
        
        avg_flow = flow_forward * t + flow_backward * (1 - t)
        
        blurred = apply_anisotropic_motion_blur(
            frame, avg_flow,
            kernel_size=self.config.motion_blur_kernel_size,
            strength=self.config.motion_blur_strength,
            threshold=self.config.motion_blur_threshold
        )
        
        return blurred
    
    def interpolate_frame(self, frame1: torch.Tensor, frame2: torch.Tensor, t: float = 0.5) -> torch.Tensor:
        flow_forward, flow_backward = self.estimate_optical_flow(frame1, frame2)
        
        occlusion_mask = self.get_occlusion_mask(flow_forward, flow_backward)
        
        flow_t_forward, flow_t_backward = self.compute_intermediate_flow(
            flow_forward, flow_backward, t
        )
        
        warped1, warped2 = self.warp_frames(frame1, frame2, flow_t_forward, flow_t_backward)
        
        blended = self.blend_with_occlusion_handling(
            warped1, warped2, frame1, frame2,
            flow_forward, flow_backward, t, occlusion_mask
        )
        
        blended = self.apply_motion_blur(blended, flow_forward, flow_backward, t)
        
        return blended
    
    def interpolate_multiple_frames(self, frame1: torch.Tensor, frame2: torch.Tensor,
                                     num_intermediate: int) -> List[torch.Tensor]:
        flow_forward, flow_backward = self.estimate_optical_flow(frame1, frame2)
        
        occlusion_mask = self.get_occlusion_mask(flow_forward, flow_backward)
        
        intermediate_frames = []
        
        for i in range(1, num_intermediate + 1):
            t = i / (num_intermediate + 1)
            
            flow_t_forward, flow_t_backward = self.compute_intermediate_flow(
                flow_forward, flow_backward, t
            )
            
            warped1, warped2 = self.warp_frames(frame1, frame2, flow_t_forward, flow_t_backward)
            
            blended = self.blend_with_occlusion_handling(
                warped1, warped2, frame1, frame2,
                flow_forward, flow_backward, t, occlusion_mask
            )
            
            blended = self.apply_motion_blur(blended, flow_forward, flow_backward, t)
            
            intermediate_frames.append(blended)
        
        return intermediate_frames
    
    def interpolate_sequence(self, frames: List[torch.Tensor], 
                              target_fps: int, source_fps: int) -> List[torch.Tensor]:
        if len(frames) < 2:
            return frames
        
        frames_to_insert = compute_frames_to_insert(source_fps, target_fps)
        
        if frames_to_insert == 0:
            return frames
        
        result = []
        
        for i in range(len(frames) - 1):
            frame1 = frames[i]
            frame2 = frames[i + 1]
            
            result.append(frame1)
            
            if frames_to_insert > 0:
                interpolated = self.interpolate_multiple_frames(
                    frame1, frame2, frames_to_insert
                )
                result.extend(interpolated)
        
        result.append(frames[-1])
        
        return result


def compute_frames_to_insert(source_fps: int, target_fps: int) -> int:
    if target_fps <= source_fps:
        return 0
    
    ratio = target_fps / source_fps
    frames_between = int(np.floor(ratio)) - 1
    
    return max(0, frames_between)


def compute_interpolation_timestamps(source_fps: int, target_fps: int) -> List[float]:
    frames_between = compute_frames_to_insert(source_fps, target_fps)
    
    if frames_between == 0:
        return []
    
    timestamps = [(i + 1) / (frames_between + 1) for i in range(frames_between)]
    return timestamps
