import numpy as np
import cv2
from collections import deque


class VideoWhiteBalanceStabilizer:
    """
    Video white balance stabilizer with inter-frame temporal smoothing.
    
    Reduces flicker between frames by smoothing illuminant estimates
    over time using exponential moving average (EMA) or sliding window.
    """
    
    def __init__(self, 
                 method='gray_world', 
                 smoothing_method='ema',
                 alpha=0.1, 
                 window_size=10,
                 max_frame_jump=5.0,
                 stabilization=True):
        """
        Initialize video WB stabilizer.
        
        Args:
            method: Illuminant estimation method - 
                   'gray_world', 'perfect_reflection', 'shades_of_gray', 'nn'
            smoothing_method: Temporal smoothing - 'ema' or 'window'
            alpha: EMA smoothing factor (0-1). Lower = smoother but slower response
            window_size: Sliding window size for 'window' method
            max_frame_jump: Max allowed angular change (degrees) between frames
            stabilization: Enable/disable temporal smoothing
        """
        self.method = method
        self.smoothing_method = smoothing_method
        self.alpha = alpha
        self.window_size = window_size
        self.max_frame_jump = max_frame_jump
        self.stabilization = stabilization
        
        self._history = deque(maxlen=window_size)
        self._smoothed_illuminant = None
        self._prev_illuminant = None
        self._frame_count = 0
        self._illuminant_history = []
        
    def reset(self):
        self._history.clear()
        self._smoothed_illuminant = None
        self._prev_illuminant = None
        self._frame_count = 0
        self._illuminant_history = []
    
    def estimate_illuminant(self, frame):
        """
        Estimate illuminant for a single frame using configured method.
        
        Args:
            frame: Input BGR frame (H, W, 3) uint8
        
        Returns:
            illuminant: Estimated illuminant [R, G, B] normalized
        """
        from .algorithms import gray_world, perfect_reflection, shades_of_gray
        
        if self.method == 'gray_world':
            est = gray_world(frame)
        elif self.method == 'perfect_reflection':
            est = perfect_reflection(frame, percentile=99)
        elif self.method == 'shades_of_gray':
            est = shades_of_gray(frame, p=6)
        elif self.method == 'nn':
            from .nn_method import neural_network_estimation
            est_tuple = neural_network_estimation(frame, pretrained=True)
            est = est_tuple[0] if isinstance(est_tuple, tuple) else est_tuple
        else:
            est = gray_world(frame)
        
        return est
    
    def stabilize_illuminant(self, raw_illuminant):
        """
        Apply temporal smoothing to illuminant estimate.
        
        Args:
            raw_illuminant: Raw estimated illuminant [R, G, B]
        
        Returns:
            smoothed: Temporally smoothed illuminant
        """
        if not self.stabilization:
            return raw_illuminant
        
        if self._prev_illuminant is None:
            self._prev_illuminant = raw_illuminant
            self._smoothed_illuminant = raw_illuminant
            self._history.append(raw_illuminant)
            return raw_illuminant
        
        from .metrics import angular_error
        jump = angular_error(raw_illuminant, self._prev_illuminant)
        
        if jump > self.max_frame_jump:
            raw_illuminant = self._prev_illuminant + \
                           (raw_illuminant - self._prev_illuminant) * \
                           (self.max_frame_jump / (jump + 1e-8))
        
        if self.smoothing_method == 'ema':
            alpha = self.alpha
            if self._frame_count < 5:
                alpha = 1.0 - self._frame_count / 5.0
            
            self._smoothed_illuminant = alpha * raw_illuminant + \
                                      (1 - alpha) * self._smoothed_illuminant
        else:
            self._history.append(raw_illuminant)
            self._smoothed_illuminant = np.mean(self._history, axis=0)
        
        self._smoothed_illuminant = self._smoothed_illuminant / \
                                   (np.linalg.norm(self._smoothed_illuminant) + 1e-8)
        
        self._prev_illuminant = self._smoothed_illuminant
        
        return self._smoothed_illuminant
    
    def process_frame(self, frame):
        """
        Process a single video frame - estimate and stabilize illuminant.
        
        Args:
            frame: Input BGR frame (H, W, 3) uint8
        
        Returns:
            smoothed_illuminant: Temporally smoothed illuminant
            raw_illuminant: Raw estimated illuminant
            correction_info: Dict with frame info
        """
        self._frame_count += 1
        
        raw = self.estimate_illuminant(frame)
        smoothed = self.stabilize_illuminant(raw)
        
        self._illuminant_history.append({
            'frame': self._frame_count,
            'raw': raw.copy(),
            'smoothed': smoothed.copy()
        })
        
        info = {
            'frame': self._frame_count,
            'raw_illuminant': raw,
            'smoothed_illuminant': smoothed,
            'jump_deg': float(angular_error_compare(raw, self._prev_illuminant)) if self._prev_illuminant is not None else 0.0
        }
        
        return smoothed, raw, info
    
    def get_history(self):
        return self._illuminant_history
    
    def get_stability_metrics(self):
        if len(self._illuminant_history) < 2:
            return {'num_frames': len(self._illuminant_history)}
        
        raw_ests = [h['raw'] for h in self._illuminant_history]
        smooth_ests = [h['smoothed'] for h in self._illuminant_history]
        
        raw_jumps = []
        smooth_jumps = []
        
        for i in range(1, len(raw_ests)):
            raw_jumps.append(angular_error_compare(raw_ests[i], raw_ests[i-1]))
            smooth_jumps.append(angular_error_compare(smooth_ests[i], smooth_ests[i-1]))
        
        return {
            'num_frames': len(self._illuminant_history),
            'raw_mean_jump_deg': float(np.mean(raw_jumps)),
            'raw_max_jump_deg': float(np.max(raw_jumps)),
            'smooth_mean_jump_deg': float(np.mean(smooth_jumps)),
            'smooth_max_jump_deg': float(np.max(smooth_jumps)),
            'stability_improvement': float(np.mean(raw_jumps) / (np.mean(smooth_jumps) + 1e-8))
        }


def angular_error_compare(est, ref):
    est = np.asarray(est, dtype=np.float32)
    ref = np.asarray(ref, dtype=np.float32)
    
    if est.ndim == 0:
        return float(est)
    if est.ndim == 1:
        est = est.reshape(1, 3)
    if ref.ndim == 0:
        return float(ref)
    if ref.ndim == 1:
        ref = ref.reshape(1, 3)
    
    if est.shape[1] != 3 or ref.shape[1] != 3:
        return 0.0
    
    est_n = est / (np.linalg.norm(est, axis=1, keepdims=True) + 1e-8)
    ref_n = ref / (np.linalg.norm(ref, axis=1, keepdims=True) + 1e-8)
    
    dot = np.sum(est_n * ref_n, axis=1)
    dot = np.clip(dot, -1, 1)
    err = np.degrees(np.arccos(dot))
    
    return err[0] if len(err) == 1 else err


def stabilize_video_frames(frames, 
                           method='gray_world',
                           smoothing_method='ema',
                           alpha=0.1,
                           window_size=10,
                           max_frame_jump=5.0):
    """
    Stabilize illuminant estimation across a sequence of video frames.
    
    Args:
        frames: List of BGR frames (N, H, W, 3)
        method: Estimation method name
        smoothing_method: 'ema' or 'window'
        alpha: EMA smoothing factor
        window_size: Window size for window method
        max_frame_jump: Max jump between frames (degrees)
    
    Returns:
        smoothed_illuminants: List of smoothed illuminant estimates
        raw_illuminants: List of raw illuminant estimates
        stabilizer: VideoWhiteBalanceStabilizer instance
    """
    stabilizer = VideoWhiteBalanceStabilizer(
        method=method,
        smoothing_method=smoothing_method,
        alpha=alpha,
        window_size=window_size,
        max_frame_jump=max_frame_jump
    )
    
    smoothed = []
    raw = []
    
    for frame in frames:
        s, r, _ = stabilizer.process_frame(frame)
        smoothed.append(s)
        raw.append(r)
    
    return smoothed, raw, stabilizer


def correct_video_white_balance(video_path, 
                                output_path=None,
                                method='gray_world',
                                smoothing_method='ema',
                                alpha=0.1,
                                max_frame_jump=3.0,
                                display=False):
    """
    Apply stabilized white balance correction to a video file.
    
    Args:
        video_path: Path to input video file
        output_path: Path to save corrected video (optional)
        method: WB estimation method
        smoothing_method: Temporal smoothing method
        alpha: EMA smoothing factor
        max_frame_jump: Max angular jump allowed
        display: Whether to display video during processing
    
    Returns:
        results: Dict with processing results
    """
    cap = cv2.VideoCapture(video_path)
    
    if not cap.isOpened():
        raise FileNotFoundError(f"Cannot open video: {video_path}")
    
    fps = cap.get(cv2.CAP_PROP_FPS)
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    
    writer = None
    if output_path is not None:
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        writer = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
    
    stabilizer = VideoWhiteBalanceStabilizer(
        method=method,
        smoothing_method=smoothing_method,
        alpha=alpha,
        max_frame_jump=max_frame_jump
    )
    
    from .white_balance import correct_white_balance
    from .visualization import rgb_to_temperature
    
    frame_idx = 0
    raw_illuminants = []
    smoothed_illuminants = []
    cct_values = []
    
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        
        smoothed, raw, info = stabilizer.process_frame(frame)
        
        corrected = correct_white_balance(frame, smoothed)
        
        raw_illuminants.append(raw)
        smoothed_illuminants.append(smoothed)
        cct, _ = rgb_to_temperature(smoothed)
        cct_values.append(cct)
        
        if display:
            display_frame = corrected.copy()
            cv2.putText(display_frame, 
                       f"CCT: {cct:.0f}K | Frame: {frame_idx}",
                       (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
            cv2.imshow('Stabilized WB', display_frame)
            
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
        
        if writer is not None:
            writer.write(corrected)
        
        frame_idx += 1
        if frame_idx % 100 == 0:
            print(f"Processed {frame_idx}/{total_frames} frames")
    
    cap.release()
    if writer is not None:
        writer.release()
    if display:
        cv2.destroyAllWindows()
    
    metrics = stabilizer.get_stability_metrics()
    metrics['total_frames'] = frame_idx
    metrics['mean_cct'] = float(np.mean(cct_values))
    metrics['std_cct'] = float(np.std(cct_values))
    
    return {
        'raw_illuminants': np.array(raw_illuminants),
        'smoothed_illuminants': np.array(smoothed_illuminants),
        'cct_values': np.array(cct_values),
        'metrics': metrics,
        'stabilizer': stabilizer
    }
