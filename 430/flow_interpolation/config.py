from dataclasses import dataclass, field
from typing import Optional, Tuple
import torch


@dataclass
class InterpolationConfig:
    target_fps: int = 60
    source_fps: Optional[int] = None
    interpolation_method: str = 'raft'
    
    use_gpu: bool = True
    device: Optional[str] = None
    
    raft_model_path: Optional[str] = None
    raft_iters: int = 12
    raft_small: bool = False
    raft_mixed_precision: bool = False
    
    occlusion_detection: bool = True
    occlusion_threshold: float = 0.01
    bidirectional_flow: bool = True
    
    motion_blur: bool = True
    motion_blur_kernel_size: int = 11
    motion_blur_strength: float = 1.0
    motion_blur_threshold: float = 5.0
    
    alpha_blending: bool = True
    alpha: float = 0.5
    
    output_resolution: Optional[Tuple[int, int]] = None
    output_codec: str = 'libx264'
    output_pix_fmt: str = 'yuv420p'
    output_crf: int = 18
    output_preset: str = 'medium'
    
    batch_size: int = 1
    num_workers: int = 0
    frame_buffer_size: int = 10
    
    verbose: bool = False
    save_flow_visualization: bool = False
    
    enable_sr: bool = False
    sr_scale: int = 2
    sr_model_path: Optional[str] = None
    sr_use_esrgan: bool = True
    sr_first: bool = True
    
    smoothness: float = 0.5
    sharpness: float = 0.5
    strength_preset: Optional[str] = None
    
    enable_style_transfer: bool = False
    style_model_path: Optional[str] = None
    style_image_path: Optional[str] = None
    style_alpha: float = 1.0
    style_name: str = 'custom'
    
    def __post_init__(self):
        if self.device is None:
            self.device = 'cuda' if (self.use_gpu and torch.cuda.is_available()) else 'cpu'
        
        if self.use_gpu and not torch.cuda.is_available():
            print('Warning: GPU requested but CUDA not available, falling back to CPU')
            self.device = 'cpu'
            self.use_gpu = False
        
        if self.motion_blur and self.motion_blur_kernel_size % 2 == 0:
            self.motion_blur_kernel_size += 1
            if self.motion_blur_kernel_size < 3:
                self.motion_blur_kernel_size = 3
        
        if self.strength_preset is not None:
            presets = {
                'smooth': (0.8, 0.3),
                'balanced': (0.5, 0.5),
                'sharp': (0.3, 0.8),
                'cinematic': (0.7, 0.6),
                'gameplay': (0.2, 0.9)
            }
            if self.strength_preset in presets:
                self.smoothness, self.sharpness = presets[self.strength_preset]
        
        self.smoothness = max(0.0, min(1.0, self.smoothness))
        self.sharpness = max(0.0, min(1.0, self.sharpness))
