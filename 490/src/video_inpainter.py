import os
import torch
import numpy as np
import cv2
from tqdm import tqdm
from typing import Optional, Tuple, Dict, List

from .inpainter import ImageInpainter
from .utils import (load_image, save_image, img2tensor, tensor2img,
                    create_directory, poisson_blend)


class OpticalFlowEstimator:
    def __init__(self):
        self.gmc = None
    
    def compute_flow(self, prev_frame, curr_frame, method='farneback'):
        if isinstance(prev_frame, torch.Tensor):
            prev_frame = tensor2img(prev_frame)
        if isinstance(curr_frame, torch.Tensor):
            curr_frame = tensor2img(curr_frame)
        
        prev_gray = (prev_frame * 255).astype(np.uint8) if prev_frame.max() <= 1.0 else prev_frame.astype(np.uint8)
        curr_gray = (curr_frame * 255).astype(np.uint8) if curr_frame.max() <= 1.0 else curr_frame.astype(np.uint8)
        
        if len(prev_gray.shape) == 3:
            prev_gray = cv2.cvtColor(prev_gray, cv2.COLOR_RGB2GRAY)
        if len(curr_gray.shape) == 3:
            curr_gray = cv2.cvtColor(curr_gray, cv2.COLOR_RGB2GRAY)
        
        if method == 'farneback':
            flow = cv2.calcOpticalFlowFarneback(
                prev_gray, curr_gray, None,
                pyr_scale=0.5, levels=3, winsize=15,
                iterations=3, poly_n=5, poly_sigma=1.2, flags=0
            )
        elif method == 'raft':
            flow = self._compute_raft_flow(prev_gray, curr_gray)
        else:
            flow = cv2.calcOpticalFlowFarneback(
                prev_gray, curr_gray, None,
                pyr_scale=0.5, levels=3, winsize=15,
                iterations=3, poly_n=5, poly_sigma=1.2, flags=0
            )
        
        return flow
    
    def _compute_raft_flow(self, prev_gray, curr_gray):
        return cv2.calcOpticalFlowFarneback(
            prev_gray, curr_gray, None,
            pyr_scale=0.5, levels=3, winsize=15,
            iterations=3, poly_n=5, poly_sigma=1.2, flags=0
        )
    
    def warp_frame(self, frame, flow):
        h, w = flow.shape[:2]
        
        grid_x, grid_y = np.meshgrid(np.arange(w), np.arange(h))
        
        new_x = (grid_x + flow[:, :, 0]).astype(np.float32)
        new_y = (grid_y + flow[:, :, 1]).astype(np.float32)
        
        warped = cv2.remap(frame, new_x, new_y, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
        
        return warped
    
    def warp_mask(self, mask, flow):
        if mask.ndim == 3 and mask.shape[2] == 1:
            mask_2d = mask[:, :, 0]
        elif mask.ndim == 3:
            mask_2d = mask[:, :, 0]
        else:
            mask_2d = mask
        
        mask_uint8 = (mask_2d * 255).astype(np.uint8)
        warped = self.warp_frame(mask_uint8, flow)
        
        _, warped_binary = cv2.threshold(warped, 127, 255, cv2.THRESH_BINARY)
        
        return warped_binary.astype(np.float32) / 255.0


class TemporalConsistency:
    def __init__(self, blend_weight=0.7, temporal_window=3):
        self.blend_weight = blend_weight
        self.temporal_window = temporal_window
    
    def blend_frames(self, current_result, warped_prev, mask, weight=None):
        if weight is None:
            weight = self.blend_weight
        
        if mask.ndim == 2:
            mask_3d = mask[:, :, np.newaxis]
        elif mask.ndim == 3 and mask.shape[2] == 1:
            mask_3d = mask
        else:
            mask_3d = mask
        
        blended = current_result * (1 - weight * mask_3d) + warped_prev * weight * mask_3d
        
        return blended
    
    def temporal_average(self, frames, weights=None):
        if not frames:
            return None
        
        if weights is None:
            weights = [1.0 / len(frames)] * len(frames)
        
        total_weight = sum(weights)
        weights = [w / total_weight for w in weights]
        
        result = np.zeros_like(frames[0])
        for frame, w in zip(frames, weights):
            result += frame * w
        
        return result
    
    def compute_flow_confidence(self, flow, mask):
        if mask.ndim == 2:
            mask_2d = mask
        elif mask.ndim == 3:
            mask_2d = mask[:, :, 0]
        else:
            mask_2d = mask
        
        flow_magnitude = np.sqrt(flow[:, :, 0] ** 2 + flow[:, :, 1] ** 2)
        
        mean_mag = np.mean(flow_magnitude)
        std_mag = np.std(flow_magnitude)
        
        threshold = mean_mag + 2 * std_mag
        
        confidence = np.where(flow_magnitude < threshold, 1.0, 0.0)
        
        boundary_mask = self._dilate_mask(mask_2d, radius=5)
        confidence = confidence * (1 - boundary_mask * 0.3)
        
        return confidence
    
    def _dilate_mask(self, mask, radius=5):
        mask_uint8 = (mask * 255).astype(np.uint8)
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (radius * 2 + 1, radius * 2 + 1))
        dilated = cv2.dilate(mask_uint8, kernel, iterations=1)
        boundary = (dilated - mask_uint8).astype(np.float32) / 255.0
        return boundary


class VideoInpainter:
    def __init__(self, 
                 model_name: str = 'partialconv',
                 device: str = None,
                 image_size: Tuple[int, int] = (256, 256),
                 poisson_blend_method: str = 'mixed',
                 temporal_weight: float = 0.6,
                 temporal_window: int = 3,
                 flow_method: str = 'farneback'):
        
        self.inpainter = ImageInpainter(
            model_name=model_name,
            device=device,
            image_size=image_size,
            poisson_blend_method=poisson_blend_method
        )
        
        self.image_size = image_size
        self.flow_estimator = OpticalFlowEstimator()
        self.temporal = TemporalConsistency(
            blend_weight=temporal_weight,
            temporal_window=temporal_window
        )
        self.flow_method = flow_method
        self.temporal_window = temporal_window
        self.temporal_weight = temporal_weight
    
    def inpaint_video(self,
                      video_path: str,
                      output_path: str,
                      mask: Optional[np.ndarray] = None,
                      mask_type: str = 'random',
                      mask_path: Optional[str] = None,
                      start_frame: int = 0,
                      end_frame: int = -1,
                      blend_method: str = 'mixed',
                      use_temporal: bool = True,
                      output_fps: Optional[int] = None,
                      output_codec: str = 'mp4v') -> Dict:
        
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise ValueError(f"Cannot open video: {video_path}")
        
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        fps = cap.get(cv2.CAP_PROP_FPS)
        orig_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        orig_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        
        if output_fps is None:
            output_fps = fps
        
        if end_frame < 0:
            end_frame = total_frames
        
        end_frame = min(end_frame, total_frames)
        num_frames = end_frame - start_frame
        
        print(f"Video: {orig_w}x{orig_h}, {fps:.1f}fps, {total_frames} frames")
        print(f"Processing frames {start_frame} to {end_frame} ({num_frames} frames)")
        
        if mask_path is not None:
            mask_img = cv2.imread(mask_path, cv2.IMREAD_GRAYSCALE)
            if mask_img is not None:
                mask_img = cv2.resize(mask_img, (orig_w, orig_h))
                mask = mask_img.astype(np.float32) / 255.0
            else:
                mask = None
        
        if mask is None:
            from .mask_generator import MaskGenerator
            mask_gen = MaskGenerator(height=orig_h, width=orig_w)
            mask = mask_gen.generate_mask(mask_type)
        
        if mask.ndim == 2:
            mask = mask[:, :, np.newaxis]
        
        fourcc = cv2.VideoWriter_fourcc(*output_codec)
        out = cv2.VideoWriter(output_path, fourcc, output_fps, (orig_w, orig_h))
        
        cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame)
        
        prev_frame = None
        prev_result = None
        history = []
        
        frame_results = []
        
        for frame_idx in tqdm(range(num_frames), desc="Video Inpainting"):
            ret, frame = cap.read()
            if not ret:
                break
            
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0
            
            resized_frame = cv2.resize(frame_rgb, (self.image_size[1], self.image_size[0]))
            resized_mask = cv2.resize(mask, (self.image_size[1], self.image_size[0]),
                                       interpolation=cv2.INTER_NEAREST)
            
            current_result = self.inpainter.inpaint(resized_frame, resized_mask)
            
            if use_temporal and prev_frame is not None and prev_result is not None:
                prev_frame_resized = cv2.resize(prev_frame, (self.image_size[1], self.image_size[0]))
                prev_result_resized = cv2.resize(prev_result, (self.image_size[1], self.image_size[0]))
                
                flow = self.flow_estimator.compute_flow(
                    prev_frame_resized, resized_frame, method=self.flow_method
                )
                
                warped_prev = self.flow_estimator.warp_frame(prev_result_resized, flow)
                
                flow_confidence = self.temporal.compute_flow_confidence(flow, resized_mask)
                
                blend_w = self.temporal_weight * flow_confidence
                if blend_w.ndim == 2:
                    blend_w = blend_w[:, :, np.newaxis]
                
                mask_2d = resized_mask
                if mask_2d.ndim == 3:
                    mask_2d = mask_2d[:, :, 0]
                mask_3d = mask_2d[:, :, np.newaxis]
                
                current_result = current_result * (1 - blend_w * mask_3d) + warped_prev * blend_w * mask_3d
                
                history.append(current_result)
                if len(history) > self.temporal_window:
                    history.pop(0)
                
                if len(history) >= 2:
                    weights = [1.0 / (i + 1) for i in range(len(history))]
                    weights[-1] *= 2
                    temporal_avg = self.temporal.temporal_average(history, weights)
                    
                    alpha = 0.3
                    current_result = current_result * (1 - alpha) + temporal_avg * alpha
            
            result_full = cv2.resize(current_result, (orig_w, orig_h))
            
            result_bgr = cv2.cvtColor((result_full * 255).astype(np.uint8), cv2.COLOR_RGB2BGR)
            out.write(result_bgr)
            
            prev_frame = frame_rgb
            prev_result = result_full
            
            frame_results.append({
                'frame_idx': frame_idx + start_frame,
                'psnr': None,
            })
        
        cap.release()
        out.release()
        
        print(f"\nVideo saved to: {output_path}")
        
        return {
            'output_path': output_path,
            'num_frames': num_frames,
            'fps': output_fps,
            'frame_results': frame_results
        }
    
    def inpaint_video_from_directory(self,
                                      frames_dir: str,
                                      output_path: str,
                                      mask: Optional[np.ndarray] = None,
                                      mask_type: str = 'random',
                                      fps: int = 30,
                                      use_temporal: bool = True) -> Dict:
        from .utils import get_image_list
        
        frame_paths = get_image_list(frames_dir)
        if not frame_paths:
            raise ValueError(f"No images found in {frames_dir}")
        
        print(f"Found {len(frame_paths)} frames in {frames_dir}")
        
        first_frame = load_image(frame_paths[0], normalize=True)
        h, w = first_frame.shape[:2]
        
        if mask is None:
            from .mask_generator import MaskGenerator
            mask_gen = MaskGenerator(height=h, width=w)
            mask = mask_gen.generate_mask(mask_type)
        
        if mask.ndim == 2:
            mask = mask[:, :, np.newaxis]
        
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(output_path, fourcc, fps, (w, h))
        
        prev_frame = None
        prev_result = None
        history = []
        
        for idx, frame_path in enumerate(tqdm(frame_paths, desc="Frame Inpainting")):
            frame = load_image(frame_path, normalize=True)
            
            if frame.shape[:2] != (h, w):
                frame = cv2.resize(frame, (w, h))
            
            current_result = self.inpainter.inpaint(frame, mask)
            
            if use_temporal and prev_frame is not None and prev_result is not None:
                flow = self.flow_estimator.compute_flow(
                    prev_frame, frame, method=self.flow_method
                )
                
                warped_prev = self.flow_estimator.warp_frame(prev_result, flow)
                
                flow_confidence = self.temporal.compute_flow_confidence(flow, mask)
                
                blend_w = self.temporal_weight * flow_confidence
                if blend_w.ndim == 2:
                    blend_w = blend_w[:, :, np.newaxis]
                
                mask_2d = mask
                if mask_2d.ndim == 3:
                    mask_2d = mask_2d[:, 0, 0] if mask_2d.shape[2] == 1 else mask_2d[:, :, 0]
                mask_3d = mask if mask.ndim == 3 else mask[:, :, np.newaxis]
                
                current_result = current_result * (1 - blend_w * mask_3d) + warped_prev * blend_w * mask_3d
                
                history.append(current_result)
                if len(history) > self.temporal_window:
                    history.pop(0)
                
                if len(history) >= 2:
                    weights = [1.0 / (i + 1) for i in range(len(history))]
                    weights[-1] *= 2
                    temporal_avg = self.temporal.temporal_average(history, weights)
                    alpha = 0.3
                    current_result = current_result * (1 - alpha) + temporal_avg * alpha
            
            result_bgr = cv2.cvtColor((current_result * 255).astype(np.uint8), cv2.COLOR_RGB2BGR)
            out.write(result_bgr)
            
            prev_frame = frame
            prev_result = current_result
        
        out.release()
        
        print(f"\nVideo saved to: {output_path}")
        
        return {
            'output_path': output_path,
            'num_frames': len(frame_paths),
            'fps': fps
        }
