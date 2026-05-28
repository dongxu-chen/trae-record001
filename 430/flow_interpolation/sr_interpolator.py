import torch
import torch.nn.functional as F
import numpy as np
from typing import Optional, Tuple, List

from .raft import bilinear_warp, compute_occlusion_mask_advanced, adaptive_blend_frames, fill_occlusion_regions
from .super_resolution import SuperResolutionProcessor, create_sr_processor
from .style_transfer import StyleTransferProcessor, create_style_processor
from .motion_blur import apply_anisotropic_motion_blur
from .config import InterpolationConfig
from .frame_interpolator import FrameInterpolator


class InterpolationStrengthController:
    def __init__(self, smoothness: float = 0.5, sharpness: float = 0.5):
        self.smoothness = smoothness
        self.sharpness = sharpness
        self._validate()
    
    def _validate(self):
        self.smoothness = max(0.0, min(1.0, self.smoothness))
        self.sharpness = max(0.0, min(1.0, self.sharpness))
    
    def get_flow_weight(self) -> float:
        return 0.5 + 0.5 * self.smoothness
    
    def get_blend_alpha(self) -> float:
        return 0.3 + 0.4 * self.sharpness
    
    def get_motion_blur_strength(self) -> float:
        return 0.5 + 0.5 * self.smoothness
    
    def get_motion_blur_threshold(self) -> float:
        return 2.0 + 8.0 * (1 - self.sharpness)
    
    def get_occlusion_threshold(self) -> float:
        return 0.005 + 0.015 * (1 - self.sharpness)
    
    def get_raft_iters(self, base_iters: int = 12) -> int:
        return max(6, int(base_iters * (0.5 + 0.5 * self.sharpness)))
    
    def set_balance(self, smoothness: float = None, sharpness: float = None):
        if smoothness is not None:
            self.smoothness = smoothness
        if sharpness is not None:
            self.sharpness = sharpness
        self._validate()
    
    def get_preset(self, preset: str = 'balanced'):
        presets = {
            'smooth': (0.8, 0.3),
            'balanced': (0.5, 0.5),
            'sharp': (0.3, 0.8),
            'cinematic': (0.7, 0.6),
            'gameplay': (0.2, 0.9)
        }
        if preset in presets:
            self.smoothness, self.sharpness = presets[preset]
        return self
    
    def get_description(self) -> str:
        if self.smoothness > 0.7:
            smooth_desc = "非常平滑"
        elif self.smoothness > 0.4:
            smooth_desc = "平衡"
        else:
            smooth_desc = "清晰锐利"
        
        if self.sharpness > 0.7:
            sharp_desc = "高清晰度"
        elif self.sharpness > 0.4:
            sharp_desc = "标准"
        else:
            sharp_desc = "柔和"
        
        return f"平滑度: {smooth_desc} ({self.smoothness:.1f}), 清晰度: {sharp_desc} ({self.sharpness:.1f})"


class SRFrameInterpolator:
    def __init__(self, config: InterpolationConfig, raft_model=None, 
                 sr_processor: SuperResolutionProcessor = None,
                 style_processor: StyleTransferProcessor = None):
        self.config = config
        self.device = config.device
        self.frame_interpolator = FrameInterpolator(config, raft_model)
        self.sr_processor = sr_processor
        self.style_processor = style_processor
        self.strength_controller = InterpolationStrengthController(
            smoothness=0.5, sharpness=0.5
        )
    
    def set_strength(self, smoothness: float = None, sharpness: float = None, preset: str = None):
        if preset is not None:
            self.strength_controller.get_preset(preset)
        else:
            self.strength_controller.set_balance(smoothness, sharpness)
        
        self.config.motion_blur_strength = self.strength_controller.get_motion_blur_strength()
        self.config.motion_blur_threshold = self.strength_controller.get_motion_blur_threshold()
        self.config.occlusion_threshold = self.strength_controller.get_occlusion_threshold()
        self.config.raft_iters = self.strength_controller.get_raft_iters(self.config.raft_iters)
        
        print(f"插帧强度设置: {self.strength_controller.get_description()}")
    
    def _interpolate_sr(self, frame1: torch.Tensor, frame2: torch.Tensor, 
                        t: float = 0.5, sr_first: bool = True) -> torch.Tensor:
        if self.sr_processor is None:
            return self.frame_interpolator.interpolate_frame(frame1, frame2, t)
        
        if sr_first:
            sr_frame1 = self.sr_processor.upscale(frame1)
            sr_frame2 = self.sr_processor.upscale(frame2)
            interp_frame = self.frame_interpolator.interpolate_frame(sr_frame1, sr_frame2, t)
        else:
            interp_frame = self.frame_interpolator.interpolate_frame(frame1, frame2, t)
            sr_frame = self.sr_processor.upscale(interp_frame)
            interp_frame = sr_frame
        
        return interp_frame
    
    def interpolate_frame(self, frame1: torch.Tensor, frame2: torch.Tensor, 
                          t: float = 0.5, use_sr: bool = True, 
                          use_style: bool = False, style_alpha: float = 1.0) -> torch.Tensor:
        if use_sr and self.sr_processor is not None:
            result = self._interpolate_sr(frame1, frame2, t)
        else:
            result = self.frame_interpolator.interpolate_frame(frame1, frame2, t)
        
        if use_style and self.style_processor is not None:
            result = self.style_processor.transfer(result, style_alpha)
        
        return result
    
    def interpolate_multiple_frames(self, frame1: torch.Tensor, frame2: torch.Tensor,
                                     num_intermediate: int, use_sr: bool = True,
                                     use_style: bool = False, style_alpha: float = 1.0) -> List[torch.Tensor]:
        if use_sr and self.sr_processor is not None:
            sr_frame1 = self.sr_processor.upscale(frame1)
            sr_frame2 = self.sr_processor.upscale(frame2)
            
            intermediate_frames = []
            for i in range(1, num_intermediate + 1):
                t = i / (num_intermediate + 1)
                interp = self.frame_interpolator.interpolate_frame(sr_frame1, sr_frame2, t)
                if use_style and self.style_processor is not None:
                    interp = self.style_processor.transfer(interp, style_alpha)
                intermediate_frames.append(interp)
            
            return intermediate_frames
        else:
            intermediate_frames = self.frame_interpolator.interpolate_multiple_frames(
                frame1, frame2, num_intermediate
            )
            
            if use_style and self.style_processor is not None:
                intermediate_frames = [
                    self.style_processor.transfer(frame, style_alpha)
                    for frame in intermediate_frames
                ]
            
            return intermediate_frames
    
    def create_slow_motion(self, frames: List[torch.Tensor], slow_factor: float = 2.0,
                           use_sr: bool = True, use_style: bool = False,
                           style_alpha: float = 1.0) -> List[torch.Tensor]:
        if len(frames) < 2:
            return frames
        
        num_intermediate = int(slow_factor) - 1
        
        result = []
        for i in range(len(frames) - 1):
            frame1 = frames[i]
            frame2 = frames[i + 1]
            
            if use_sr and self.sr_processor is not None:
                frame1_out = self.sr_processor.upscale(frame1)
            else:
                frame1_out = frame1
            
            if use_style and self.style_processor is not None:
                frame1_out = self.style_processor.transfer(frame1_out, style_alpha)
            
            result.append(frame1_out)
            
            if num_intermediate > 0:
                interpolated = self.interpolate_multiple_frames(
                    frame1, frame2, num_intermediate, use_sr, use_style, style_alpha
                )
                result.extend(interpolated)
        
        last_frame = frames[-1]
        if use_sr and self.sr_processor is not None:
            last_frame = self.sr_processor.upscale(last_frame)
        if use_style and self.style_processor is not None:
            last_frame = self.style_processor.transfer(last_frame, style_alpha)
        result.append(last_frame)
        
        return result
    
    def to(self, device: str):
        self.device = device
        self.frame_interpolator.device = device
        if self.sr_processor is not None:
            self.sr_processor.to(device)
        if self.style_processor is not None:
            self.style_processor.to(device)
        return self
    
    def eval(self):
        self.frame_interpolator.raft_model.eval()
        if self.sr_processor is not None:
            self.sr_processor.eval()
        if self.style_processor is not None:
            self.style_processor.eval()
        return self
    
    def train(self):
        self.frame_interpolator.raft_model.train()
        if self.sr_processor is not None:
            self.sr_processor.train()
        if self.style_processor is not None:
            self.style_processor.train()
        return self


class VideoProcessor:
    def __init__(self, config: InterpolationConfig, raft_model=None,
                 sr_processor: SuperResolutionProcessor = None,
                 style_processor: StyleTransferProcessor = None):
        self.config = config
        self.device = config.device
        self.sr_interpolator = SRFrameInterpolator(
            config, raft_model, sr_processor, style_processor
        )
        self.sr_processor = sr_processor
        self.style_processor = style_processor
    
    def set_sr_processor(self, sr_processor: SuperResolutionProcessor):
        self.sr_processor = sr_processor
        self.sr_interpolator.sr_processor = sr_processor
    
    def set_style_processor(self, style_processor: StyleTransferProcessor):
        self.style_processor = style_processor
        self.sr_interpolator.style_processor = style_processor
    
    def set_style_image(self, style_path: str):
        if self.style_processor is not None:
            self.style_processor.set_style_from_path(style_path)
    
    def set_strength(self, smoothness: float = None, sharpness: float = None, preset: str = None):
        self.sr_interpolator.set_strength(smoothness, sharpness, preset)
    
    def process_video_sr(self, input_path: str, output_path: str,
                         sr_scale: int = 2, use_sr: bool = True,
                         use_style: bool = False, style_alpha: float = 1.0) -> None:
        import os
        import cv2
        from tqdm import tqdm
        from .video_io import VideoReader, VideoWriter, get_video_info, check_ffmpeg_available
        
        if not os.path.exists(input_path):
            raise FileNotFoundError(f'Input video not found: {input_path}')
        
        video_info = get_video_info(input_path)
        source_fps = self.config.source_fps or video_info.fps
        target_fps = self.config.target_fps
        
        if source_fps <= 0:
            source_fps = 24.0
        
        frames_to_insert = max(0, int(target_fps // source_fps) - 1)
        
        output_width = video_info.width * sr_scale if use_sr else video_info.width
        output_height = video_info.height * sr_scale if use_sr else video_info.height
        
        if self.config.output_resolution is not None:
            output_width, output_height = self.config.output_resolution
        
        use_ffmpeg = check_ffmpeg_available()
        
        with VideoReader(input_path) as reader, \
             VideoWriter(output_path, output_width, output_height, target_fps,
                        codec=self.config.output_codec,
                        pixel_format=self.config.output_pix_fmt,
                        use_ffmpeg=use_ffmpeg,
                        crf=self.config.output_crf,
                        preset=self.config.output_preset) as writer:
            
            print(f'Processing: {source_fps:.1f}fps -> {target_fps}fps')
            if use_sr:
                print(f'Super-resolution: {video_info.width}x{video_info.height} -> {output_width}x{output_height}')
            if use_style:
                print(f'Style transfer: enabled (alpha={style_alpha})')
            
            prev_frame_np = None
            pbar = tqdm(total=video_info.frame_count, desc='Processing')
            
            for frame in reader:
                pbar.update(1)
                
                curr_tensor = torch.from_numpy(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)).permute(2, 0, 1).float()
                curr_tensor = curr_tensor.unsqueeze(0).to(self.device)
                
                if prev_frame_np is not None:
                    prev_tensor = torch.from_numpy(cv2.cvtColor(prev_frame_np, cv2.COLOR_BGR2RGB)).permute(2, 0, 1).float()
                    prev_tensor = prev_tensor.unsqueeze(0).to(self.device)
                    
                    if use_sr and self.sr_processor is not None:
                        prev_out = self.sr_processor.upscale(prev_tensor)
                    else:
                        prev_out = prev_tensor
                    
                    if use_style and self.style_processor is not None:
                        prev_out = self.style_processor.transfer(prev_out, style_alpha)
                    
                    out_frame = prev_out.squeeze(0).clamp(0, 255).byte().permute(1, 2, 0).cpu().numpy()
                    out_frame = cv2.cvtColor(out_frame, cv2.COLOR_RGB2BGR)
                    writer.write_frame(out_frame)
                    
                    if frames_to_insert > 0:
                        interpolated = self.sr_interpolator.interpolate_multiple_frames(
                            prev_tensor, curr_tensor, frames_to_insert, 
                            use_sr=use_sr, use_style=use_style, style_alpha=style_alpha
                        )
                        for interp_tensor in interpolated:
                            out_frame = interp_tensor.squeeze(0).clamp(0, 255).byte().permute(1, 2, 0).cpu().numpy()
                            out_frame = cv2.cvtColor(out_frame, cv2.COLOR_RGB2BGR)
                            writer.write_frame(out_frame)
                
                prev_frame_np = frame
            
            if prev_frame_np is not None:
                if use_sr and self.sr_processor is not None:
                    prev_tensor = torch.from_numpy(cv2.cvtColor(prev_frame_np, cv2.COLOR_BGR2RGB)).permute(2, 0, 1).float()
                    prev_tensor = prev_tensor.unsqueeze(0).to(self.device)
                    prev_out = self.sr_processor.upscale(prev_tensor)
                    if use_style and self.style_processor is not None:
                        prev_out = self.style_processor.transfer(prev_out, style_alpha)
                    out_frame = prev_out.squeeze(0).clamp(0, 255).byte().permute(1, 2, 0).cpu().numpy()
                    out_frame = cv2.cvtColor(out_frame, cv2.COLOR_RGB2BGR)
                else:
                    out_frame = prev_frame_np
                writer.write_frame(out_frame)
            
            pbar.close()
        
        print(f'Video saved to: {output_path}')
    
    def to(self, device: str):
        self.device = device
        self.sr_interpolator.to(device)
        return self
