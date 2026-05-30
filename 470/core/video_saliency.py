import os
import cv2
import numpy as np
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
from tqdm import tqdm
import time

from config import Config
from utils.helpers import save_image


def _lazy_import_inferencer():
    from core import SaliencyInferencer
    return SaliencyInferencer


@dataclass
class FrameResult:
    frame_idx: int
    original_frame: np.ndarray
    saliency_map: np.ndarray
    binary_mask: np.ndarray
    smoothed_saliency: Optional[np.ndarray] = None
    smoothed_mask: Optional[np.ndarray] = None
    processing_time: float = 0.0


@dataclass
class VideoResult:
    video_path: str
    fps: float
    total_frames: int
    frame_results: List[FrameResult] = field(default_factory=list)
    output_video_path: Optional[str] = None


class FrameSmoother:
    def __init__(self, method='temporal', window_size=5, alpha=0.6, beta=0.4):
        self.method = method
        self.window_size = window_size
        self.alpha = alpha
        self.beta = beta
        self.history: List[np.ndarray] = []
    
    def reset(self):
        self.history = []
    
    def smooth(self, current_saliency: np.ndarray, current_frame: Optional[np.ndarray] = None) -> np.ndarray:
        if self.method == 'temporal':
            return self._temporal_smooth(current_saliency)
        elif self.method == 'bilateral':
            return self._bilateral_temporal_smooth(current_saliency, current_frame)
        elif self.method == 'gaussian':
            return self._gaussian_temporal_smooth(current_saliency)
        elif self.method == 'flow':
            return self._flow_based_smooth(current_saliency, current_frame)
        else:
            return current_saliency
    
    def _temporal_smooth(self, current: np.ndarray) -> np.ndarray:
        self.history.append(current.copy())
        if len(self.history) > self.window_size:
            self.history.pop(0)
        
        if len(self.history) == 1:
            return current
        
        weights = np.linspace(0.2, 1.0, len(self.history))
        weights = weights / weights.sum()
        
        smoothed = np.zeros_like(current, dtype=np.float32)
        for i, frame in enumerate(self.history):
            smoothed += frame * weights[i]
        
        return smoothed
    
    def _bilateral_temporal_smooth(self, current: np.ndarray, current_frame: Optional[np.ndarray]) -> np.ndarray:
        self.history.append(current.copy())
        if len(self.history) > self.window_size:
            self.history.pop(0)
        
        if len(self.history) == 1 or current_frame is None:
            return current
        
        smoothed = np.zeros_like(current, dtype=np.float32)
        total_weight = 0.0
        
        current_gray = cv2.cvtColor(current_frame, cv2.COLOR_RGB2GRAY) if current_frame.ndim == 3 else current_frame
        
        for i, hist_sal in enumerate(self.history):
            temporal_weight = self.alpha ** (len(self.history) - 1 - i)
            
            if i < len(self.history) - 1:
                prev_sal = self.history[i]
                diff = np.abs(current - prev_sal)
                appearance_weight = np.exp(-diff * self.beta)
                weight = temporal_weight * appearance_weight
            else:
                weight = temporal_weight
            
            smoothed += hist_sal * weight
            total_weight += weight
        
        if total_weight > 0:
            smoothed /= total_weight
        
        return smoothed
    
    def _gaussian_temporal_smooth(self, current: np.ndarray) -> np.ndarray:
        self.history.append(current.copy())
        if len(self.history) > self.window_size:
            self.history.pop(0)
        
        if len(self.history) == 1:
            return current
        
        sigma = self.window_size / 6.0
        weights = np.exp(-(np.arange(len(self.history)) - len(self.history) + 1) ** 2 / (2 * sigma ** 2))
        weights = weights / weights.sum()
        
        smoothed = np.zeros_like(current, dtype=np.float32)
        for i, frame in enumerate(self.history):
            smoothed += frame * weights[i]
        
        return smoothed
    
    def _flow_based_smooth(self, current: np.ndarray, current_frame: Optional[np.ndarray]) -> np.ndarray:
        if current_frame is None or len(self.history) == 0:
            self.history.append(current.copy())
            if len(self.history) > self.window_size:
                self.history.pop(0)
            return current
        
        try:
            if not hasattr(self, '_prev_frame') or self._prev_frame is None:
                self._prev_frame = current_frame
                self.history.append(current.copy())
                if len(self.history) > self.window_size:
                    self.history.pop(0)
                return current
            
            prev_gray = cv2.cvtColor(self._prev_frame, cv2.COLOR_RGB2GRAY) if self._prev_frame.ndim == 3 else self._prev_frame
            curr_gray = cv2.cvtColor(current_frame, cv2.COLOR_RGB2GRAY) if current_frame.ndim == 3 else current_frame
            
            flow = cv2.calcOpticalFlowFarneback(
                prev_gray, curr_gray, None,
                pyr_scale=0.5, levels=3, winsize=15,
                iterations=3, poly_n=5, poly_sigma=1.2, flags=0
            )
            
            h, w = current.shape
            flow_map = np.zeros_like(current)
            
            for y in range(h):
                for x in range(w):
                    dx, dy = flow[y, x]
                    src_x = int(x - dx)
                    src_y = int(y - dy)
                    if 0 <= src_x < w and 0 <= src_y < h:
                        flow_map[y, x] = self.history[-1][src_y, src_x]
            
            warped = flow_map
            self._prev_frame = current_frame
            self.history.append(current.copy())
            if len(self.history) > self.window_size:
                self.history.pop(0)
            
            smoothed = self.alpha * current + (1 - self.alpha) * warped
            return smoothed
            
        except Exception as e:
            print(f"Flow-based smoothing failed, falling back to temporal: {e}")
            return self._temporal_smooth(current)


class VideoSaliencyDetector:
    def __init__(self, model_name='basnet', use_tensorrt=None, use_dynamic_batch=True):
        SaliencyInferencer = _lazy_import_inferencer()
        self.inferencer = SaliencyInferencer(
            model_name=model_name,
            pretrained=False,
            use_tensorrt=use_tensorrt,
            use_dynamic_batch=use_dynamic_batch
        )
        self.smoother = FrameSmoother()
    
    def set_smoothing_method(self, method='temporal', window_size=5, alpha=0.6, beta=0.4):
        self.smoother = FrameSmoother(
            method=method,
            window_size=window_size,
            alpha=alpha,
            beta=beta
        )
    
    def process_frame(self, frame: np.ndarray, smooth=True, refine_method='guided') -> FrameResult:
        start_time = time.time()
        
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB) if frame.ndim == 3 and frame.shape[2] == 3 else frame
        
        result = self.inferencer.predict(
            frame_rgb,
            refine_method=refine_method,
            measure_time=False
        )
        
        processing_time = time.time() - start_time
        
        frame_result = FrameResult(
            frame_idx=0,
            original_frame=frame_rgb,
            saliency_map=result['saliency_map'],
            binary_mask=result['binary_mask'],
            processing_time=processing_time
        )
        
        if smooth:
            frame_result.smoothed_saliency = self.smoother.smooth(
                result['saliency_map'],
                frame_rgb
            )
            frame_result.smoothed_mask = (frame_result.smoothed_saliency > Config.THRESHOLD).astype(np.float32)
        
        return frame_result
    
    def process_video(self, video_path: str, output_dir: Optional[str] = None,
                      start_frame: int = 0, end_frame: Optional[int] = None,
                      stride: int = 1, smooth: bool = True,
                      refine_method: str = 'guided',
                      save_results: bool = True,
                      show_progress: bool = True) -> VideoResult:
        if not os.path.exists(video_path):
            raise FileNotFoundError(f"Video not found: {video_path}")
        
        if output_dir is None:
            output_dir = os.path.join(Config.OUTPUT_DIR, 'video_results')
        
        os.makedirs(output_dir, exist_ok=True)
        
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise ValueError(f"Failed to open video: {video_path}")
        
        fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        
        if end_frame is None:
            end_frame = total_frames
        
        end_frame = min(end_frame, total_frames)
        
        print(f"Processing video: {os.path.basename(video_path)}")
        print(f"  FPS: {fps:.2f}")
        print(f"  Total frames: {total_frames}")
        print(f"  Resolution: {width}x{height}")
        print(f"  Frame range: {start_frame} - {end_frame} (stride={stride})")
        print(f"  Smoothing: {'ON' if smooth else 'OFF'}")
        print()
        
        self.smoother.reset()
        
        video_result = VideoResult(
            video_path=video_path,
            fps=fps,
            total_frames=total_frames
        )
        
        frame_idx = 0
        processed_count = 0
        
        if show_progress:
            pbar = tqdm(total=(end_frame - start_frame + stride - 1) // stride, desc="Processing frames")
        
        while frame_idx < end_frame:
            ret, frame = cap.read()
            if not ret:
                break
            
            if frame_idx >= start_frame and frame_idx % stride == 0:
                frame_result = self.process_frame(frame, smooth=smooth, refine_method=refine_method)
                frame_result.frame_idx = frame_idx
                video_result.frame_results.append(frame_result)
                
                if save_results:
                    self._save_frame_result(frame_result, output_dir, frame_idx)
                
                processed_count += 1
                if show_progress:
                    pbar.update(1)
            
            frame_idx += 1
        
        cap.release()
        if show_progress:
            pbar.close()
        
        if save_results and len(video_result.frame_results) > 0:
            output_video_path = self._create_output_video(video_result, output_dir, width, height, fps)
            video_result.output_video_path = output_video_path
        
        avg_time = np.mean([r.processing_time for r in video_result.frame_results]) if video_result.frame_results else 0
        print(f"\nProcessing complete!")
        print(f"  Processed frames: {len(video_result.frame_results)}")
        print(f"  Avg processing time per frame: {avg_time * 1000:.1f} ms")
        print(f"  Processing speed: {1 / avg_time:.1f} FPS" if avg_time > 0 else "")
        
        return video_result
    
    def _save_frame_result(self, frame_result: FrameResult, output_dir: str, frame_idx: int):
        frame_dir = os.path.join(output_dir, 'frames')
        os.makedirs(frame_dir, exist_ok=True)
        
        filename = f'frame_{frame_idx:06d}'
        
        saliency_path = os.path.join(frame_dir, f'{filename}_saliency.png')
        save_image((frame_result.saliency_map * 255).astype(np.uint8), saliency_path)
        
        if frame_result.smoothed_saliency is not None:
            smoothed_path = os.path.join(frame_dir, f'{filename}_smoothed.png')
            save_image((frame_result.smoothed_saliency * 255).astype(np.uint8), smoothed_path)
        
        mask_path = os.path.join(frame_dir, f'{filename}_mask.png')
        save_image((frame_result.binary_mask * 255).astype(np.uint8), mask_path)
    
    def _create_output_video(self, video_result: VideoResult, output_dir: str,
                            width: int, height: int, fps: float) -> str:
        print("\nCreating output video...")
        
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        
        combined_width = width * 3
        combined_height = height
        
        output_path = os.path.join(output_dir, 'saliency_video.mp4')
        writer = cv2.VideoWriter(output_path, fourcc, fps, (combined_width, combined_height))
        
        for frame_result in tqdm(video_result.frame_results, desc="Writing video"):
            original = frame_result.original_frame
            
            saliency = frame_result.saliency_map
            saliency_colored = cv2.applyColorMap((saliency * 255).astype(np.uint8), cv2.COLORMAP_JET)
            saliency_colored = cv2.cvtColor(saliency_colored, cv2.COLOR_BGR2RGB)
            
            if frame_result.smoothed_saliency is not None:
                smoothed = frame_result.smoothed_saliency
            else:
                smoothed = frame_result.saliency_map
            
            smoothed_colored = cv2.applyColorMap((smoothed * 255).astype(np.uint8), cv2.COLORMAP_JET)
            smoothed_colored = cv2.cvtColor(smoothed_colored, cv2.COLOR_BGR2RGB)
            
            combined = np.hstack([original, saliency_colored, smoothed_colored])
            
            if combined.shape[2] == 3:
                combined_bgr = cv2.cvtColor(combined, cv2.COLOR_RGB2BGR)
            else:
                combined_bgr = combined
            
            writer.write(combined_bgr)
        
        writer.release()
        print(f"Output video saved to: {output_path}")
        
        return output_path
    
    def extract_salient_clips(self, video_result: VideoResult, 
                             threshold: float = 0.3, 
                             min_duration: float = 1.0) -> List[Dict[str, Any]]:
        if not video_result.frame_results:
            return []
        
        fps = video_result.fps
        min_frames = int(min_duration * fps)
        
        salient_scores = []
        for result in video_result.frame_results:
            if result.smoothed_saliency is not None:
                score = result.smoothed_saliency.mean()
            else:
                score = result.saliency_map.mean()
            salient_scores.append((result.frame_idx, score))
        
        clips = []
        clip_start = None
        
        for i, (frame_idx, score) in enumerate(salient_scores):
            if score > threshold:
                if clip_start is None:
                    clip_start = i
            else:
                if clip_start is not None:
                    clip_end = i
                    if clip_end - clip_start >= min_frames:
                        start_time = salient_scores[clip_start][0] / fps
                        end_time = salient_scores[clip_end - 1][0] / fps
                        avg_score = np.mean([s[1] for s in salient_scores[clip_start:clip_end]])
                        clips.append({
                            'start_frame': salient_scores[clip_start][0],
                            'end_frame': salient_scores[clip_end - 1][0],
                            'start_time': start_time,
                            'end_time': end_time,
                            'duration': end_time - start_time,
                            'avg_saliency': avg_score
                        })
                    clip_start = None
        
        if clip_start is not None:
            clip_end = len(salient_scores)
            if clip_end - clip_start >= min_frames:
                start_time = salient_scores[clip_start][0] / fps
                end_time = salient_scores[-1][0] / fps
                avg_score = np.mean([s[1] for s in salient_scores[clip_start:]])
                clips.append({
                    'start_frame': salient_scores[clip_start][0],
                    'end_frame': salient_scores[-1][0],
                    'start_time': start_time,
                    'end_time': end_time,
                    'duration': end_time - start_time,
                    'avg_saliency': avg_score
                })
        
        return clips


def smooth_saliency_sequence(saliency_maps: List[np.ndarray], 
                            method: str = 'temporal',
                            window_size: int = 5) -> List[np.ndarray]:
    smoother = FrameSmoother(method=method, window_size=window_size)
    smoothed = []
    
    for sal in saliency_maps:
        smoothed.append(smoother.smooth(sal))
    
    return smoothed
