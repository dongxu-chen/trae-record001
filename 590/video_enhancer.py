import cv2
import numpy as np
from typing import Tuple, Optional, Callable, List, Dict
from underwater_enhancer import UnderwaterImageEnhancer, AdaptiveParameterEstimator
from threading import Thread
from queue import Queue
import time
from collections import deque


class TemporalSmoother:
    def __init__(self, smoothing_factor: float = 0.8, history_size: int = 5):
        self.smoothing_factor = smoothing_factor
        self.history_size = history_size
        self.param_history = deque(maxlen=history_size)
        self.current_smoothed = None
    
    def smooth(self, new_params: Dict[str, float]) -> Dict[str, float]:
        if self.current_smoothed is None:
            self.current_smoothed = new_params.copy()
        else:
            for key in new_params:
                if isinstance(new_params[key], (int, float)) and key in self.current_smoothed:
                    self.current_smoothed[key] = (
                        self.smoothing_factor * self.current_smoothed[key] +
                        (1 - self.smoothing_factor) * new_params[key]
                    )
        
        self.param_history.append(new_params)
        return self.current_smoothed.copy()
    
    def reset(self):
        self.param_history.clear()
        self.current_smoothed = None


class DehazeStrengthInterpolator:
    def __init__(self, max_change: float = 0.05, smoothing_window: int = 3):
        self.max_change = max_change
        self.smoothing_window = smoothing_window
        self.last_omega = None
        self.omega_history = deque(maxlen=smoothing_window)
    
    def interpolate(self, target_omega: float) -> float:
        if self.last_omega is None:
            self.last_omega = target_omega
            self.omega_history.append(target_omega)
            return target_omega
        
        delta = target_omega - self.last_omega
        
        if abs(delta) > self.max_change:
            delta = np.sign(delta) * self.max_change
        
        new_omega = self.last_omega + delta
        
        self.omega_history.append(new_omega)
        smoothed_omega = np.mean(self.omega_history)
        
        self.last_omega = smoothed_omega
        return smoothed_omega
    
    def reset(self):
        self.last_omega = None
        self.omega_history.clear()


class FrameBuffer:
    def __init__(self, buffer_size: int = 3):
        self.buffer_size = buffer_size
        self.frames = deque(maxlen=buffer_size)
    
    def add_frame(self, frame: np.ndarray):
        self.frames.append(frame)
    
    def get_blended_frame(self, weights: Optional[List[float]] = None) -> np.ndarray:
        if len(self.frames) == 0:
            raise ValueError("Buffer is empty")
        
        if weights is None:
            weights = np.linspace(0.3, 1.0, len(self.frames))
            weights = weights / weights.sum()
        
        blended = np.zeros_like(self.frames[0], dtype=np.float32)
        for frame, weight in zip(self.frames, weights):
            blended += frame.astype(np.float32) * weight
        
        return np.clip(blended, 0, 255).astype(np.uint8)
    
    def reset(self):
        self.frames.clear()


class VideoProcessor:
    def __init__(self, use_adaptive: bool = True, frame_skip: int = 0,
                 use_temporal_smoothing: bool = True, 
                 smoothing_factor: float = 0.85,
                 max_omega_change: float = 0.03,
                 use_frame_blending: bool = False,
                 **kwargs):
        self.enhancer = UnderwaterImageEnhancer(use_adaptive=use_adaptive, **kwargs)
        self.frame_skip = frame_skip
        self.frame_count = 0
        self.last_enhanced = None
        self._running = False
        self._thread = None
        self._frame_queue = Queue(maxsize=5)
        self._result_queue = Queue(maxsize=5)
        
        self.use_temporal_smoothing = use_temporal_smoothing
        self.use_frame_blending = use_frame_blending
        
        if use_temporal_smoothing:
            self.temporal_smoother = TemporalSmoother(smoothing_factor=smoothing_factor)
            self.dehaze_interpolator = DehazeStrengthInterpolator(max_change=max_omega_change)
        
        if use_frame_blending:
            self.frame_buffer = FrameBuffer(buffer_size=3)
        
        self.param_estimator = AdaptiveParameterEstimator()
    
    def process_frame(self, frame: np.ndarray) -> Tuple[np.ndarray, dict]:
        if self.frame_skip > 0:
            self.frame_count += 1
            if self.frame_count % (self.frame_skip + 1) != 0 and self.last_enhanced is not None:
                return self.last_enhanced[0], self.last_enhanced[1]
        
        if self.use_temporal_smoothing and self.enhancer.use_adaptive:
            raw_params = self.param_estimator.get_adaptive_params(
                frame, 
                use_water_estimation=self.enhancer.use_water_estimation
            )
            
            smoothed_params = self.temporal_smoother.smooth(raw_params)
            
            if 'omega' in smoothed_params:
                smoothed_params['omega'] = self.dehaze_interpolator.interpolate(smoothed_params['omega'])
            
            result, info = self.enhancer.enhance(frame, frame_params=smoothed_params)
            info['temporal_smoothed_params'] = smoothed_params
            info['raw_params'] = raw_params
        else:
            result, info = self.enhancer.enhance(frame)
        
        if self.use_frame_blending:
            self.frame_buffer.add_frame(result)
            result = self.frame_buffer.get_blended_frame()
        
        self.last_enhanced = (result, info)
        return result, info
    
    def reset_temporal_state(self):
        if hasattr(self, 'temporal_smoother'):
            self.temporal_smoother.reset()
        if hasattr(self, 'dehaze_interpolator'):
            self.dehaze_interpolator.reset()
        if hasattr(self, 'frame_buffer'):
            self.frame_buffer.reset()
    
    def process_video_file(self, 
                          input_path: str, 
                          output_path: str, 
                          progress_callback: Optional[Callable[[float, int, int], None]] = None,
                          display_fps: bool = False,
                          reset_temporal_state: bool = True) -> dict:
        cap = cv2.VideoCapture(input_path)
        if not cap.isOpened():
            raise ValueError(f"Cannot open video file: {input_path}")
        
        fps = cap.get(cv2.CAP_PROP_FPS)
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
        
        if reset_temporal_state:
            self.reset_temporal_state()
        
        frame_idx = 0
        start_time = time.time()
        processing_times = []
        
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break
            
            frame_start = time.time()
            enhanced, info = self.process_frame(frame)
            frame_time = time.time() - frame_start
            processing_times.append(frame_time)
            
            out.write(enhanced)
            
            frame_idx += 1
            if progress_callback:
                progress = frame_idx / total_frames if total_frames > 0 else 0
                progress_callback(progress, frame_idx, total_frames)
            
            if display_fps and frame_idx % 10 == 0:
                elapsed = time.time() - start_time
                current_fps = frame_idx / elapsed
                print(f"Processed: {frame_idx}/{total_frames}, FPS: {current_fps:.1f}")
        
        cap.release()
        out.release()
        
        avg_time = np.mean(processing_times) if processing_times else 0
        total_time = time.time() - start_time
        
        return {
            'input_path': input_path,
            'output_path': output_path,
            'fps': fps,
            'resolution': (width, height),
            'total_frames': frame_idx,
            'avg_frame_time': avg_time,
            'total_time': total_time,
            'processing_fps': frame_idx / total_time if total_time > 0 else 0,
            'temporal_smoothing_used': self.use_temporal_smoothing
        }
    
    def _capture_worker(self, source):
        cap = cv2.VideoCapture(source)
        while self._running:
            ret, frame = cap.read()
            if ret:
                if not self._frame_queue.full():
                    self._frame_queue.put(frame)
            else:
                time.sleep(0.01)
        cap.release()
    
    def _process_worker(self):
        while self._running:
            if not self._frame_queue.empty():
                frame = self._frame_queue.get()
                enhanced, info = self.process_frame(frame)
                if not self._result_queue.full():
                    self._result_queue.put((enhanced, info))
            else:
                time.sleep(0.001)
    
    def start_stream(self, source=0):
        self._running = True
        self._thread_capture = Thread(target=self._capture_worker, args=(source,), daemon=True)
        self._thread_process = Thread(target=self._process_worker, daemon=True)
        self._thread_capture.start()
        self._thread_process.start()
    
    def stop_stream(self):
        self._running = False
        if hasattr(self, '_thread_capture'):
            self._thread_capture.join(timeout=1.0)
        if hasattr(self, '_thread_process'):
            self._thread_process.join(timeout=1.0)
    
    def get_latest_frame(self) -> Tuple[Optional[np.ndarray], Optional[dict]]:
        if not self._result_queue.empty():
            return self._result_queue.get()
        return None, None


class RealTimeEnhancer:
    def __init__(self, use_adaptive: bool = True, downscale_factor: float = 1.0, **kwargs):
        self.processor = VideoProcessor(use_adaptive=use_adaptive, **kwargs)
        self.downscale_factor = downscale_factor
        self.running = False
    
    def run_camera(self, camera_id: int = 0, window_name: str = "Underwater Enhancement"):
        cap = cv2.VideoCapture(camera_id)
        if not cap.isOpened():
            raise ValueError(f"Cannot open camera {camera_id}")
        
        self.running = True
        
        try:
            while self.running:
                ret, frame = cap.read()
                if not ret:
                    break
                
                if self.downscale_factor != 1.0:
                    h, w = frame.shape[:2]
                    frame = cv2.resize(frame, (int(w * self.downscale_factor), int(h * self.downscale_factor)))
                
                enhanced, info = self.processor.process_frame(frame)
                
                combined = np.hstack((frame, enhanced))
                
                if info and info.get('adaptive_params'):
                    params = info['adaptive_params']
                    text = f"Haze: {params['haze_level']:.2f} | Bright: {params['brightness']:.2f}"
                    cv2.putText(combined, text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 
                               0.6, (255, 255, 255), 2)
                
                cv2.imshow(window_name, combined)
                
                key = cv2.waitKey(1) & 0xFF
                if key == ord('q'):
                    break
                elif key == ord('s'):
                    self._save_snapshot(frame, enhanced)
        
        finally:
            cap.release()
            cv2.destroyAllWindows()
    
    def _save_snapshot(self, original: np.ndarray, enhanced: np.ndarray):
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        cv2.imwrite(f"original_{timestamp}.jpg", original)
        cv2.imwrite(f"enhanced_{timestamp}.jpg", enhanced)
        print(f"Saved snapshots: original_{timestamp}.jpg, enhanced_{timestamp}.jpg")


class FrameComparator:
    @staticmethod
    def create_comparison_grid(frames: List[np.ndarray], labels: List[str], 
                               cols: int = 2, scale: float = 1.0) -> np.ndarray:
        if len(frames) != len(labels):
            raise ValueError("Number of frames must match number of labels")
        
        if scale != 1.0:
            frames = [cv2.resize(f, None, fx=scale, fy=scale) for f in frames]
        
        rows = (len(frames) + cols - 1) // cols
        h, w = frames[0].shape[:2]
        
        grid = np.zeros((rows * h, cols * w, 3), dtype=np.uint8)
        
        for idx, (frame, label) in enumerate(zip(frames, labels)):
            r = idx // cols
            c = idx % cols
            
            if frame.shape[2] == 1:
                frame = cv2.cvtColor(frame, cv2.COLOR_GRAY2BGR)
            
            grid[r*h:(r+1)*h, c*w:(c+1)*w] = frame
            
            cv2.putText(grid, label, (c*w + 10, r*h + 30), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
        
        return grid
    
    @staticmethod
    def create_before_after(original: np.ndarray, enhanced: np.ndarray, 
                           title: bool = True) -> np.ndarray:
        combined = np.hstack((original, enhanced))
        
        if title:
            h, w = original.shape[:2]
            cv2.putText(combined, "Original", (10, 30), 
                       cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
            cv2.putText(combined, "Enhanced", (w + 10, 30), 
                       cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
        
        return combined
