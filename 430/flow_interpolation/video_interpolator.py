import os
import numpy as np
import torch
import torch.nn.functional as F
from typing import Optional, List, Tuple
from tqdm import tqdm

from .config import InterpolationConfig
from .raft import load_raft_model, flow_to_image
from .frame_interpolator import FrameInterpolator, compute_frames_to_insert, compute_interpolation_timestamps
from .video_io import (
    VideoReader, VideoWriter,
    frame_to_tensor, tensor_to_frame,
    get_video_info, check_ffmpeg_available
)


class VideoInterpolator:
    def __init__(self, config: Optional[InterpolationConfig] = None):
        self.config = config or InterpolationConfig()
        self.device = self.config.device
        self.raft_model = None
        self.frame_interpolator = None
        self._load_models()
    
    def _load_models(self):
        print(f'Loading RAFT model on {self.device}...')
        self.raft_model = load_raft_model(
            model_path=self.config.raft_model_path,
            small=self.config.raft_small,
            device=self.device
        )
        self.frame_interpolator = FrameInterpolator(self.config, self.raft_model)
        print('Models loaded successfully.')
    
    def _frame_to_tensor_gpu(self, frame_np: np.ndarray) -> torch.Tensor:
        frame_rgb = frame_np[:, :, ::-1].copy()
        tensor = torch.from_numpy(frame_rgb).permute(2, 0, 1).float()
        tensor = tensor.unsqueeze(0).to(self.device, non_blocking=True)
        return tensor
    
    def _tensor_to_frame_gpu(self, tensor: torch.Tensor) -> np.ndarray:
        tensor = tensor.squeeze(0).clamp(0, 255).byte()
        frame_rgb = tensor.permute(1, 2, 0).cpu().numpy()
        frame_bgr = frame_rgb[:, :, ::-1].copy()
        return frame_bgr
    
    def _resize_tensor_gpu(self, tensor: torch.Tensor, new_h: int, new_w: int) -> torch.Tensor:
        return F.interpolate(tensor, size=(new_h, new_w), mode='bilinear', align_corners=False)
    
    def _preprocess_batch(self, frames: List[np.ndarray], 
                          target_h: int, target_w: int) -> List[torch.Tensor]:
        tensors = []
        for frame in frames:
            tensor = self._frame_to_tensor_gpu(frame)
            if tensor.shape[2] != target_h or tensor.shape[3] != target_w:
                tensor = self._resize_tensor_gpu(tensor, target_h, target_w)
            tensors.append(tensor)
        return tensors
    
    def process_video(self, input_path: str, output_path: str) -> None:
        if not os.path.exists(input_path):
            raise FileNotFoundError(f'Input video not found: {input_path}')
        
        video_info = get_video_info(input_path)
        source_fps = self.config.source_fps or video_info.fps
        target_fps = self.config.target_fps
        
        if source_fps <= 0:
            source_fps = 24.0
            print(f'Warning: Invalid source FPS, using {source_fps}')
        
        frames_to_insert = compute_frames_to_insert(int(source_fps), int(target_fps))
        
        if frames_to_insert == 0:
            print(f'Target FPS ({target_fps}) <= Source FPS ({source_fps}), no interpolation needed.')
            return
        
        output_width = self.config.output_resolution[0] if self.config.output_resolution else video_info.width
        output_height = self.config.output_resolution[1] if self.config.output_resolution else video_info.height
        
        use_ffmpeg = check_ffmpeg_available()
        print(f'Using FFmpeg: {use_ffmpeg}')
        
        with VideoReader(input_path) as reader, \
             VideoWriter(output_path, output_width, output_height, target_fps,
                        codec=self.config.output_codec,
                        pixel_format=self.config.output_pix_fmt,
                        use_ffmpeg=use_ffmpeg,
                        crf=self.config.output_crf,
                        preset=self.config.output_preset) as writer:
            
            print(f'Interpolating video: {source_fps:.1f}fps -> {target_fps}fps')
            print(f'Frames to insert between each pair: {frames_to_insert}')
            print(f'Total frames: {video_info.frame_count}')
            
            prev_tensor = None
            prev_frame_np = None
            frame_count = 0
            
            pbar = tqdm(total=video_info.frame_count, desc='Processing')
            
            for frame in reader:
                frame_count += 1
                pbar.update(1)
                
                curr_tensor = self._frame_to_tensor_gpu(frame)
                
                if curr_tensor.shape[2] != output_height or curr_tensor.shape[3] != output_width:
                    curr_tensor = self._resize_tensor_gpu(curr_tensor, output_height, output_width)
                
                if prev_tensor is not None and prev_frame_np is not None:
                    if self.config.output_resolution is not None:
                        import cv2
                        prev_frame_np = cv2.resize(prev_frame_np, (output_width, output_height))
                    writer.write_frame(prev_frame_np)
                    
                    if frames_to_insert == 1:
                        interp_tensor = self.frame_interpolator.interpolate_frame(
                            prev_tensor, curr_tensor, t=0.5
                        )
                        interp_frame = self._tensor_to_frame_gpu(interp_tensor)
                        writer.write_frame(interp_frame)
                        
                        if self.config.save_flow_visualization and frame_count <= 5:
                            self._save_flow_visualization(
                                prev_tensor, curr_tensor, output_path, frame_count
                            )
                    else:
                        interp_tensors = self.frame_interpolator.interpolate_multiple_frames(
                            prev_tensor, curr_tensor, num_intermediate=frames_to_insert
                        )
                        for interp_tensor in interp_tensors:
                            interp_frame = self._tensor_to_frame_gpu(interp_tensor)
                            writer.write_frame(interp_frame)
                    
                    torch.cuda.synchronize() if self.device == 'cuda' else None
                
                prev_tensor = curr_tensor
                prev_frame_np = frame
            
            if prev_frame_np is not None:
                if self.config.output_resolution is not None:
                    import cv2
                    prev_frame_np = cv2.resize(prev_frame_np, (output_width, output_height))
                writer.write_frame(prev_frame_np)
            
            pbar.close()
        
        if self.device == 'cuda':
            torch.cuda.empty_cache()
        
        print(f'Video saved to: {output_path}')
    
    def process_video_batch(self, input_path: str, output_path: str, 
                            batch_size: int = 4) -> None:
        if not os.path.exists(input_path):
            raise FileNotFoundError(f'Input video not found: {input_path}')
        
        video_info = get_video_info(input_path)
        source_fps = self.config.source_fps or video_info.fps
        target_fps = self.config.target_fps
        
        if source_fps <= 0:
            source_fps = 24.0
            print(f'Warning: Invalid source FPS, using {source_fps}')
        
        frames_to_insert = compute_frames_to_insert(int(source_fps), int(target_fps))
        
        if frames_to_insert == 0:
            print(f'Target FPS ({target_fps}) <= Source FPS ({source_fps}), no interpolation needed.')
            return
        
        output_width = self.config.output_resolution[0] if self.config.output_resolution else video_info.width
        output_height = self.config.output_resolution[1] if self.config.output_resolution else video_info.height
        
        use_ffmpeg = check_ffmpeg_available()
        print(f'Using FFmpeg: {use_ffmpeg}')
        print(f'Batch size: {batch_size}')
        
        with VideoReader(input_path) as reader, \
             VideoWriter(output_path, output_width, output_height, target_fps,
                        codec=self.config.output_codec,
                        pixel_format=self.config.output_pix_fmt,
                        use_ffmpeg=use_ffmpeg,
                        crf=self.config.output_crf,
                        preset=self.config.output_preset) as writer:
            
            print(f'Interpolating video: {source_fps:.1f}fps -> {target_fps}fps')
            print(f'Frames to insert between each pair: {frames_to_insert}')
            print(f'Total frames: {video_info.frame_count}')
            
            frame_buffer = []
            pbar = tqdm(total=video_info.frame_count, desc='Processing')
            
            for frame in reader:
                frame_buffer.append(frame)
                pbar.update(1)
                
                if len(frame_buffer) >= batch_size + 1:
                    self._process_frame_batch(frame_buffer, frames_to_insert, 
                                              output_height, output_width, writer)
                    frame_buffer = [frame_buffer[-1]]
            
            if len(frame_buffer) >= 2:
                self._process_frame_batch(frame_buffer, frames_to_insert,
                                          output_height, output_width, writer)
            elif len(frame_buffer) == 1:
                last_frame = frame_buffer[0]
                if self.config.output_resolution is not None:
                    import cv2
                    last_frame = cv2.resize(last_frame, (output_width, output_height))
                writer.write_frame(last_frame)
            
            pbar.close()
        
        if self.device == 'cuda':
            torch.cuda.empty_cache()
        
        print(f'Video saved to: {output_path}')
    
    def _process_frame_batch(self, frames: List[np.ndarray], frames_to_insert: int,
                              output_h: int, output_w: int, writer: VideoWriter) -> None:
        tensors = self._preprocess_batch(frames, output_h, output_w)
        
        for i in range(len(tensors) - 1):
            frame_np = frames[i]
            if tensors[i].shape[2] != output_h or tensors[i].shape[3] != output_w:
                import cv2
                frame_np = cv2.resize(frame_np, (output_w, output_h))
            writer.write_frame(frame_np)
            
            if frames_to_insert == 1:
                interp_tensor = self.frame_interpolator.interpolate_frame(
                    tensors[i], tensors[i + 1], t=0.5
                )
                interp_frame = self._tensor_to_frame_gpu(interp_tensor)
                writer.write_frame(interp_frame)
            else:
                interp_tensors = self.frame_interpolator.interpolate_multiple_frames(
                    tensors[i], tensors[i + 1], num_intermediate=frames_to_insert
                )
                for interp_tensor in interp_tensors:
                    interp_frame = self._tensor_to_frame_gpu(interp_tensor)
                    writer.write_frame(interp_frame)
        
        if self.device == 'cuda':
            torch.cuda.synchronize()
    
    def _save_flow_visualization(self, frame1: torch.Tensor, frame2: torch.Tensor,
                                  output_path: str, frame_idx: int):
        import cv2
        flow_forward = self.raft_model.estimate_flow(frame1, frame2, iters=self.config.raft_iters)
        flow_img = flow_to_image(flow_forward)
        
        flow_dir = os.path.join(os.path.dirname(output_path), 'flow_vis')
        os.makedirs(flow_dir, exist_ok=True)
        flow_path = os.path.join(flow_dir, f'flow_{frame_idx:04d}.png')
        cv2.imwrite(flow_path, cv2.cvtColor(flow_img, cv2.COLOR_RGB2BGR))
    
    def interpolate_frame_pair(self, frame1_np: np.ndarray, frame2_np: np.ndarray,
                                t: float = 0.5) -> np.ndarray:
        frame1_tensor = self._frame_to_tensor_gpu(frame1_np)
        frame2_tensor = self._frame_to_tensor_gpu(frame2_np)
        
        interp_tensor = self.frame_interpolator.interpolate_frame(
            frame1_tensor, frame2_tensor, t=t
        )
        
        if self.device == 'cuda':
            torch.cuda.synchronize()
        
        return self._tensor_to_frame_gpu(interp_tensor)
    
    def interpolate_frame_tensor(self, frame1: torch.Tensor, frame2: torch.Tensor,
                                  t: float = 0.5) -> torch.Tensor:
        return self.frame_interpolator.interpolate_frame(frame1, frame2, t=t)
    
    def get_optical_flow(self, frame1_np: np.ndarray, frame2_np: np.ndarray) -> np.ndarray:
        frame1_tensor = self._frame_to_tensor_gpu(frame1_np)
        frame2_tensor = self._frame_to_tensor_gpu(frame2_np)
        
        flow = self.raft_model.estimate_flow(frame1_tensor, frame2_tensor, iters=self.config.raft_iters)
        
        if self.device == 'cuda':
            torch.cuda.synchronize()
        
        return flow.squeeze(0).cpu().numpy()
    
    def to(self, device: str):
        self.device = device
        self.config.device = device
        if self.raft_model is not None:
            self.raft_model = self.raft_model.to(device)
        return self
    
    def eval(self):
        if self.raft_model is not None:
            self.raft_model.eval()
        return self
    
    def train(self):
        if self.raft_model is not None:
            self.raft_model.train()
        return self
