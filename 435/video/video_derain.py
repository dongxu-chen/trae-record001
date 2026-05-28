import os
import cv2
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from typing import List, Tuple, Optional
from collections import deque

from config import Config
from models import build_model
from data import RainSynthesizer
from utils import calculate_psnr, calculate_ssim


class TemporalConsistencyLoss(nn.Module):
    def __init__(self, alpha: float = 0.5):
        super(TemporalConsistencyLoss, self).__init__()
        self.alpha = alpha
        self.l1_loss = nn.L1Loss()

    def forward(self, current_frame: torch.Tensor, previous_frame: torch.Tensor,
                flow: Optional[torch.Tensor] = None) -> torch.Tensor:
        if flow is None:
            return self.l1_loss(current_frame, previous_frame)
        
        warped_previous = self.warp_frame(previous_frame, flow)
        temporal_loss = self.l1_loss(current_frame, warped_previous)
        return temporal_loss

    def warp_frame(self, frame: torch.Tensor, flow: torch.Tensor) -> torch.Tensor:
        batch_size, _, height, width = frame.size()
        
        grid_y, grid_x = torch.meshgrid(
            torch.arange(height, device=frame.device),
            torch.arange(width, device=frame.device),
            indexing='ij'
        )
        
        grid = torch.stack([grid_x, grid_y], dim=-1).float()
        grid = grid.unsqueeze(0).repeat(batch_size, 1, 1, 1)
        
        flow = flow.permute(0, 2, 3, 1)
        grid = grid + flow
        
        grid_x_norm = 2.0 * grid[:, :, :, 0] / (width - 1) - 1.0
        grid_y_norm = 2.0 * grid[:, :, :, 1] / (height - 1) - 1.0
        grid_norm = torch.stack([grid_x_norm, grid_y_norm], dim=-1)
        
        warped = F.grid_sample(frame, grid_norm, mode='bilinear', padding_mode='border', align_corners=False)
        return warped


class OpticalFlowEstimator:
    def __init__(self, method: str = 'farneback'):
        self.method = method
        self.flow_estimator = None
        
        if method == 'dis':
            try:
                self.flow_estimator = cv2.optflow.DISOpticalFlow_create(cv2.optflow.DISOPTICAL_FLOW_PRESET_MEDIUM)
            except:
                self.method = 'farneback'

    def estimate_flow(self, prev_frame: np.ndarray, curr_frame: np.ndarray) -> np.ndarray:
        if len(prev_frame.shape) == 3:
            prev_gray = cv2.cvtColor(prev_frame, cv2.COLOR_RGB2GRAY)
            curr_gray = cv2.cvtColor(curr_frame, cv2.COLOR_RGB2GRAY)
        else:
            prev_gray = prev_frame
            curr_gray = curr_frame
        
        if self.method == 'farneback' or self.flow_estimator is None:
            flow = cv2.calcOpticalFlowFarneback(
                prev_gray, curr_gray, None,
                pyr_scale=0.5, levels=3, winsize=15,
                iterations=3, poly_n=5, poly_sigma=1.2, flags=0
            )
        else:
            flow = self.flow_estimator.calc(prev_gray, curr_gray, None)
        
        return flow


class VideoDerainer:
    def __init__(self, model: nn.Module, temporal_window: int = 3,
                 use_temporal_consistency: bool = True, device: torch.device = Config.DEVICE):
        self.model = model
        self.device = device
        self.temporal_window = temporal_window
        self.use_temporal_consistency = use_temporal_consistency
        
        self.frame_buffer = deque(maxlen=temporal_window)
        self.derained_buffer = deque(maxlen=temporal_window)
        
        self.flow_estimator = OpticalFlowEstimator(method='farneback')
        self.temporal_loss = TemporalConsistencyLoss()
        
        self.model.eval()

    def preprocess_frame(self, frame: np.ndarray) -> torch.Tensor:
        if frame.dtype != np.float32:
            frame = frame.astype(np.float32) / 255.0
        
        if len(frame.shape) == 2:
            frame = cv2.cvtColor(frame, cv2.COLOR_GRAY2RGB)
        elif frame.shape[2] == 4:
            frame = cv2.cvtColor(frame, cv2.COLOR_BGRA2RGB)
        elif frame.shape[2] == 3:
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        tensor = torch.from_numpy(frame).permute(2, 0, 1).unsqueeze(0)
        return tensor.to(self.device)

    def postprocess_frame(self, tensor: torch.Tensor) -> np.ndarray:
        frame = tensor.squeeze(0).permute(1, 2, 0).cpu().numpy()
        frame = np.clip(frame, 0, 1)
        frame = (frame * 255).astype(np.uint8)
        frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
        return frame

    def apply_temporal_smoothing(self, current_derained: torch.Tensor) -> torch.Tensor:
        if len(self.derained_buffer) == 0:
            return current_derained
        
        smoothed = current_derained.clone()
        weight_sum = 1.0
        
        for i, prev_derained in enumerate(reversed(self.derained_buffer)):
            weight = 1.0 / (i + 2)
            smoothed = smoothed + weight * prev_derained
            weight_sum += weight
        
        smoothed = smoothed / weight_sum
        return smoothed

    def process_frame(self, frame: np.ndarray) -> np.ndarray:
        input_tensor = self.preprocess_frame(frame)
        
        with torch.no_grad():
            derained_tensor = self.model(input_tensor)
            
            if self.use_temporal_consistency and len(self.derained_buffer) > 0:
                prev_derained = self.derained_buffer[-1]
                smoothed_tensor = self.apply_temporal_smoothing(derained_tensor)
                derained_tensor = 0.7 * derained_tensor + 0.3 * smoothed_tensor
        
        derained_frame = self.postprocess_frame(derained_tensor)
        
        self.frame_buffer.append(frame)
        self.derained_buffer.append(derained_tensor)
        
        return derained_frame

    def reset(self):
        self.frame_buffer.clear()
        self.derained_buffer.clear()


class VideoRainRemover:
    def __init__(self, checkpoint_path: str = None, temporal_window: int = 3):
        self.device = Config.DEVICE
        self.model = build_model('resnet')
        
        if checkpoint_path and os.path.exists(checkpoint_path):
            from train import load_checkpoint
            self.model, _, _, _ = load_checkpoint(self.model, None, checkpoint_path)
            print(f"Loaded model from {checkpoint_path}")
        
        self.derainer = VideoDerainer(
            model=self.model,
            temporal_window=temporal_window,
            use_temporal_consistency=True,
            device=self.device
        )

    def process_video(self, input_path: str, output_path: str,
                     show_progress: bool = True) -> dict:
        if not os.path.exists(input_path):
            raise FileNotFoundError(f"Video file not found: {input_path}")
        
        cap = cv2.VideoCapture(input_path)
        if not cap.isOpened():
            raise ValueError(f"Could not open video file: {input_path}")
        
        fps = cap.get(cv2.CAP_PROP_FPS)
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
        
        self.derainer.reset()
        frame_count = 0
        
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            
            derained_frame = self.derainer.process_frame(frame)
            out.write(derained_frame)
            
            frame_count += 1
            if show_progress and frame_count % 10 == 0:
                progress = (frame_count / total_frames) * 100
                print(f"Processing: {frame_count}/{total_frames} frames ({progress:.1f}%)", end='\r')
        
        cap.release()
        out.release()
        
        if show_progress:
            print(f"\nVideo processing completed. {frame_count} frames processed.")
        
        return {
            'input_path': input_path,
            'output_path': output_path,
            'fps': fps,
            'width': width,
            'height': height,
            'total_frames': frame_count
        }

    def process_video_with_synthetic_rain(self, input_path: str, output_path: str,
                                          intensity: str = 'medium',
                                          show_progress: bool = True) -> dict:
        if not os.path.exists(input_path):
            raise FileNotFoundError(f"Video file not found: {input_path}")
        
        rain_synthesizer = RainSynthesizer(intensity=intensity)
        
        cap = cv2.VideoCapture(input_path)
        if not cap.isOpened():
            raise ValueError(f"Could not open video file: {input_path}")
        
        fps = cap.get(cv2.CAP_PROP_FPS)
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        rainy_path = output_path.replace('.mp4', '_rainy.mp4')
        derained_path = output_path.replace('.mp4', '_derained.mp4')
        
        out_rainy = cv2.VideoWriter(rainy_path, fourcc, fps, (width, height))
        out_derained = cv2.VideoWriter(derained_path, fourcc, fps, (width, height))
        
        self.derainer.reset()
        frame_count = 0
        
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            rainy_frame = rain_synthesizer(frame_rgb)
            rainy_frame_bgr = cv2.cvtColor((rainy_frame * 255).astype(np.uint8), cv2.COLOR_RGB2BGR)
            
            derained_frame = self.derainer.process_frame(rainy_frame_bgr)
            
            out_rainy.write(rainy_frame_bgr)
            out_derained.write(derained_frame)
            
            frame_count += 1
            if show_progress and frame_count % 10 == 0:
                progress = (frame_count / total_frames) * 100
                print(f"Processing: {frame_count}/{total_frames} frames ({progress:.1f}%)", end='\r')
        
        cap.release()
        out_rainy.release()
        out_derained.release()
        
        if show_progress:
            print(f"\nVideo processing completed. {frame_count} frames processed.")
        
        return {
            'input_path': input_path,
            'rainy_path': rainy_path,
            'derained_path': derained_path,
            'rain_intensity': intensity,
            'fps': fps,
            'width': width,
            'height': height,
            'total_frames': frame_count
        }
