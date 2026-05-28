import os
import cv2
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from tqdm import tqdm


@dataclass
class VideoConfig:
    temporal_window: int = 5
    flow_method: str = 'farneback'
    consistency_weight: float = 0.4
    blend_factor: float = 0.3
    max_flow: float = 50.0
    gpu_acceleration: bool = False


class OpticalFlowEstimator:
    def __init__(self, method: str = 'farneback'):
        self.method = method
    
    def compute_flow(
        self,
        prev_frame: np.ndarray,
        curr_frame: np.ndarray
    ) -> np.ndarray:
        prev_gray = cv2.cvtColor(prev_frame, cv2.COLOR_RGB2GRAY) if len(prev_frame.shape) == 3 else prev_frame
        curr_gray = cv2.cvtColor(curr_frame, cv2.COLOR_RGB2GRAY) if len(curr_frame.shape) == 3 else curr_frame
        
        if self.method == 'farneback':
            flow = cv2.calcOpticalFlowFarneback(
                prev_gray, curr_gray, None,
                pyr_scale=0.5, levels=3, winsize=15,
                iterations=3, poly_n=5, poly_sigma=1.2, flags=0
            )
        elif self.method == 'lucas_kanade':
            flow = self._lucas_kanade_dense(prev_gray, curr_gray)
        else:
            flow = np.zeros((*prev_gray.shape[:2], 2), dtype=np.float32)
        
        return flow
    
    def _lucas_kanade_dense(
        self,
        prev_gray: np.ndarray,
        curr_gray: np.ndarray
    ) -> np.ndarray:
        h, w = prev_gray.shape
        flow = np.zeros((h, w, 2), dtype=np.float32)
        
        feature_params = dict(maxCorners=500, qualityLevel=0.01, minDistance=7, blockSize=7)
        lk_params = dict(winSize=(15, 15), maxLevel=2,
                        criteria=(cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 10, 0.03))
        
        p0 = cv2.goodFeaturesToTrack(prev_gray, **feature_params)
        if p0 is None:
            return flow
        
        p1, st, err = cv2.calcOpticalFlowPyrLK(prev_gray, curr_gray, p0, None, **lk_params)
        
        if p1 is None:
            return flow
        
        good_new = p1[st == 1]
        good_old = p0[st == 1]
        
        if len(good_new) < 4:
            return flow
        
        for new, old in zip(good_new, good_old):
            a, b = new.ravel()
            c, d = old.ravel()
            ix, iy = int(c), int(d)
            if 0 <= iy < h and 0 <= ix < w:
                flow[iy, ix] = [a - c, b - d]
        
        flow = cv2.GaussianBlur(flow, (15, 15), 0)
        return flow
    
    def warp_frame(
        self,
        frame: np.ndarray,
        flow: np.ndarray
    ) -> np.ndarray:
        h, w = frame.shape[:2]
        
        y_coords, x_coords = np.mgrid[0:h, 0:w]
        map_x = (x_coords.astype(np.float32) + flow[..., 0]).astype(np.float32)
        map_y = (y_coords.astype(np.float32) + flow[..., 1]).astype(np.float32)
        
        warped = cv2.remap(frame, map_x, map_y, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
        return warped
    
    def compute_flow_mask(self, flow: np.ndarray, max_flow: float = 50.0) -> np.ndarray:
        magnitude = np.sqrt(flow[..., 0]**2 + flow[..., 1]**2)
        mask = (magnitude < max_flow).astype(np.float32)
        return mask


class TemporalConsistencyFilter:
    def __init__(self, window_size: int = 5, blend_factor: float = 0.3):
        self.window_size = window_size
        self.blend_factor = blend_factor
        self.frame_buffer: List[np.ndarray] = []
        self.flow_buffer: List[np.ndarray] = []
    
    def reset(self):
        self.frame_buffer = []
        self.flow_buffer = []
    
    def add_frame(self, frame: np.ndarray, flow: Optional[np.ndarray] = None):
        self.frame_buffer.append(frame.copy())
        if flow is not None:
            self.flow_buffer.append(flow.copy())
        
        if len(self.frame_buffer) > self.window_size:
            self.frame_buffer.pop(0)
            if self.flow_buffer:
                self.flow_buffer.pop(0)
    
    def filter_frame(self, current_frame: np.ndarray) -> np.ndarray:
        if len(self.frame_buffer) < 2:
            self.add_frame(current_frame)
            return current_frame
        
        self.add_frame(current_frame)
        
        result = current_frame.astype(np.float32)
        total_weight = 1.0
        n = len(self.frame_buffer)
        
        for i in range(n - 1):
            past_frame = self.frame_buffer[i].astype(np.float32)
            distance = n - 1 - i
            weight = self.blend_factor ** distance
            
            if i < len(self.flow_buffer):
                flow = self.flow_buffer[i]
                flow_estimator = OpticalFlowEstimator()
                warped_past = flow_estimator.warp_frame(past_frame.astype(np.uint8), flow)
                warped_past = warped_past.astype(np.float32)
            else:
                warped_past = past_frame
            
            result += weight * warped_past
            total_weight += weight
        
        result = np.clip(result / total_weight, 0, 255).astype(np.uint8)
        return result


class TemporalAttentionFusion(nn.Module):
    def __init__(self, channels: int = 64):
        super().__init__()
        self.query_conv = nn.Conv2d(channels, channels // 8, kernel_size=1)
        self.key_conv = nn.Conv2d(channels, channels // 8, kernel_size=1)
        self.value_conv = nn.Conv2d(channels, channels, kernel_size=1)
        self.gamma = nn.Parameter(torch.zeros(1))
        self.softmax = nn.Softmax(dim=-1)
    
    def forward(
        self,
        current_feat: torch.Tensor,
        temporal_feats: List[torch.Tensor],
        temporal_masks: Optional[List[torch.Tensor]] = None
    ) -> torch.Tensor:
        B, C, H, W = current_feat.shape
        
        query = self.query_conv(current_feat).view(B, -1, H * W).permute(0, 2, 1)
        
        fused = current_feat
        for i, t_feat in enumerate(temporal_feats):
            key = self.key_conv(t_feat).view(B, -1, H * W)
            value = self.value_conv(t_feat).view(B, -1, H * W)
            
            attention = torch.bmm(query, key)
            attention = self.softmax(attention)
            
            out = torch.bmm(value, attention.permute(0, 2, 1))
            out = out.view(B, C, H, W)
            
            if temporal_masks is not None and i < len(temporal_masks):
                out = out * temporal_masks[i]
            
            fused = fused + self.gamma * out
        
        return fused


class VideoReflectionRemover:
    def __init__(self, config, model_path: Optional[str] = None, video_config: Optional[VideoConfig] = None):
        self.config = config
        self.video_config = video_config or VideoConfig()
        
        from core.reflectance_remover import ReflectionRemover
        self.frame_remover = ReflectionRemover(config, model_path)
        
        self.flow_estimator = OpticalFlowEstimator(method=self.video_config.flow_method)
        self.temporal_filter = TemporalConsistencyFilter(
            window_size=self.video_config.temporal_window,
            blend_factor=self.video_config.blend_factor
        )
        
        self._temporal_attention = None
    
    def _get_temporal_attention(self, channels: int, device: torch.device) -> TemporalAttentionFusion:
        if self._temporal_attention is None or self._temporal_attention.query_conv.in_channels != channels:
            self._temporal_attention = TemporalAttentionFusion(channels).to(device)
            self._temporal_attention.eval()
        return self._temporal_attention
    
    def process_video(
        self,
        input_path: str,
        output_path: str,
        progress_callback: Optional[callable] = None
    ) -> Dict:
        cap = cv2.VideoCapture(input_path)
        if not cap.isOpened():
            raise ValueError(f"Cannot open video: {input_path}")
        
        fps = cap.get(cv2.CAP_PROP_FPS)
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        
        os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else '.', exist_ok=True)
        writer = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
        
        self.temporal_filter.reset()
        
        prev_frame = None
        results_list = []
        processed_count = 0
        skipped_count = 0
        
        pbar = tqdm(range(total_frames), desc='Processing video')
        
        for frame_idx in pbar:
            ret, frame = cap.read()
            if not ret:
                break
            
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            
            from core.reflection_detector import ReflectionDetector
            has_reflection, confidence = ReflectionDetector.detect(frame_rgb)
            
            if not has_reflection:
                output_frame = frame
                skipped_count += 1
                flow = np.zeros((height, width, 2), dtype=np.float32)
            else:
                flow = np.zeros((height, width, 2), dtype=np.float32)
                if prev_frame is not None:
                    flow = self.flow_estimator.compute_flow(prev_frame, frame_rgb)
                    flow_mask = self.flow_estimator.compute_flow_mask(flow, self.video_config.max_flow)
                
                frame_result = self.frame_remover.remove_reflection(frame_rgb)
                restored = frame_result['transmission']
                
                if prev_frame is not None and self.video_config.consistency_weight > 0:
                    restored = self._apply_temporal_consistency(
                        restored, frame_rgb, flow, prev_frame
                    )
                
                output_frame = cv2.cvtColor(restored, cv2.COLOR_RGB2BGR)
                processed_count += 1
            
            self.temporal_filter.add_frame(frame_rgb, flow)
            
            writer.write(output_frame)
            prev_frame = frame_rgb.copy()
            
            if progress_callback:
                progress_callback(frame_idx, total_frames)
            
            pbar.set_postfix({
                'processed': processed_count,
                'skipped': skipped_count,
                'conf': f'{confidence:.2f}' if has_reflection else 'N/A'
            })
        
        cap.release()
        writer.release()
        
        return {
            'output_path': output_path,
            'total_frames': total_frames,
            'processed_frames': processed_count,
            'skipped_frames': skipped_count,
            'fps': fps,
            'resolution': (width, height)
        }
    
    def _apply_temporal_consistency(
        self,
        restored: np.ndarray,
        current_input: np.ndarray,
        flow: np.ndarray,
        prev_input: np.ndarray
    ) -> np.ndarray:
        weight = self.video_config.consistency_weight
        
        flow_mask = self.flow_estimator.compute_flow_mask(flow, self.video_config.max_flow)
        
        prev_restored_buffer = self.temporal_filter.frame_buffer[-1] if self.temporal_filter.frame_buffer else None
        
        if prev_restored_buffer is None:
            return restored
        
        warped_prev = self.flow_estimator.warp_frame(prev_restored_buffer, flow)
        
        flow_mask_3c = np.stack([flow_mask] * 3, axis=-1)
        
        blended = (1 - weight) * restored.astype(np.float32) + weight * warped_prev.astype(np.float32) * flow_mask_3c
        
        mask_sum = (1 - weight) + weight * flow_mask_3c
        mask_sum = np.where(mask_sum == 0, 1, mask_sum)
        
        blended = blended / mask_sum
        blended = np.clip(blended, 0, 255).astype(np.uint8)
        
        return blended
    
    def process_frames_batch(
        self,
        frames: List[np.ndarray],
        detect_reflection: bool = True
    ) -> List[Dict]:
        self.temporal_filter.reset()
        
        results = []
        prev_frame = None
        
        for idx, frame in enumerate(frames):
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB) if frame.shape[2] == 3 else frame
            
            if detect_reflection:
                from core.reflection_detector import ReflectionDetector
                has_refl, confidence = ReflectionDetector.detect(frame_rgb)
            else:
                has_refl = True
                confidence = 1.0
            
            flow = np.zeros((*frame_rgb.shape[:2], 2), dtype=np.float32)
            if prev_frame is not None:
                flow = self.flow_estimator.compute_flow(prev_frame, frame_rgb)
            
            if has_refl:
                frame_result = self.frame_remover.remove_reflection(frame_rgb)
                restored = frame_result['transmission']
                
                if prev_frame is not None and self.video_config.consistency_weight > 0:
                    restored = self._apply_temporal_consistency(
                        restored, frame_rgb, flow, prev_frame
                    )
                
                frame_result['transmission'] = restored
                frame_result['has_reflection'] = True
                frame_result['reflection_confidence'] = confidence
            else:
                frame_result = {
                    'input': frame_rgb,
                    'transmission': frame_rgb,
                    'reflection': np.zeros_like(frame_rgb),
                    'alpha': np.zeros(frame_rgb.shape[:2], dtype=np.uint8),
                    'has_reflection': False,
                    'reflection_confidence': confidence
                }
            
            self.temporal_filter.add_frame(frame_rgb, flow)
            prev_frame = frame_rgb.copy()
            
            results.append(frame_result)
        
        return results
