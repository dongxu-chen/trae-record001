import cv2
import numpy as np
import os
from collections import deque
from dark_channel_dehazer import DarkChannelDehazer


class VideoDehazer:
    def __init__(self, dehazer=None, smooth_window=5, max_strength_smooth=0.3,
                 temporal_smooth=True, show_progress=True, enhance_enabled=False,
                 enhance_strength=0.5):
        self.dehazer = dehazer if dehazer else DarkChannelDehazer()
        self.smooth_window = smooth_window
        self.strength_smooth = max_strength_smooth
        self.temporal_smooth = temporal_smooth
        self.show_progress = show_progress
        self.enhance_enabled = enhance_enabled
        self.enhance_strength = enhance_strength
        self._haze_density_history = deque(maxlen=smooth_window)
        self._strength_history = deque(maxlen=smooth_window)
        self._atmospheric_light_history = deque(maxlen=smooth_window)
        self._frame_count = 0
        self.last_haze_density = None
        self.last_smoothed_strength = None
        self.last_atmospheric_light = None

    def reset(self):
        self._haze_density_history.clear()
        self._strength_history.clear()
        self._atmospheric_light_history.clear()
        self._frame_count = 0
        self.last_haze_density = None
        self.last_smoothed_strength = None
        self.last_atmospheric_light = None

    def _smooth_value(self, history, new_value, smooth_factor=None):
        if smooth_factor is None:
            smooth_factor = self.strength_smooth
        if len(history) == 0:
            return new_value
        if smooth_factor >= 1.0:
            return np.mean(list(history) + [new_value])
        else:
            alpha = smooth_factor
            last_value = history[-1]
            return last_value * (1 - alpha) + new_value * alpha

    def _temporal_smooth_haze_density(self, haze_density):
        if not self.temporal_smooth:
            return haze_density
        if len(self._haze_density_history) == 0:
            smoothed = haze_density
        else:
            alpha = 0.3
            smoothed = self._haze_density_history[-1] * (1 - alpha) + haze_density * alpha
        self._haze_density_history.append(smoothed)
        return smoothed

    def _temporal_smooth_atmospheric_light(self, atmospheric_light):
        if not self.temporal_smooth:
            return atmospheric_light
        if len(self._atmospheric_light_history) == 0:
            smoothed = atmospheric_light
        else:
            alpha = 0.2
            smoothed = self._atmospheric_light_history[-1] * (1 - alpha) + atmospheric_light * alpha
        self._atmospheric_light_history.append(smoothed)
        return smoothed

    def dehaze_frame(self, frame):
        self._frame_count += 1
        if hasattr(self.dehazer, 'estimate_haze_density'):
            haze_density = self.dehazer.estimate_haze_density(frame)
            smoothed_haze_density = self._temporal_smooth_haze_density(haze_density)
        else:
            haze_density = 0.5
            smoothed_haze_density = 0.5
        if hasattr(self.dehazer, 'dehaze_with_info_and_enhance') and self.enhance_enabled:
            enhanced, dehazed, info = self.dehazer.dehaze_with_info_and_enhance(frame, enhance_strength=self.enhance_strength)
            result = enhanced
        elif hasattr(self.dehazer, 'dehaze_and_enhance') and self.enhance_enabled:
            enhanced, dehazed = self.dehazer.dehaze_and_enhance(frame, enhance_strength=self.enhance_strength)
            result = enhanced
        else:
            result = self.dehazer.dehaze(frame)
            dehazed = result
        self.last_haze_density = smoothed_haze_density
        info_dict = {
            'frame': self._frame_count,
            'haze_density': haze_density,
            'smoothed_haze_density': smoothed_haze_density,
            'enhanced': self.enhance_enabled
        }
        return result, info_dict

    def process_video(self, input_path: str, output_path: str, 
                   start_frame: int = 0, max_frames: int = None):
        if not os.path.exists(input_path):
            raise FileNotFoundError(f"Video file not found: {input_path}")
        cap = cv2.VideoCapture(input_path)
        if not cap.isOpened():
            raise ValueError(f"Cannot open video file: {input_path}")
        fps = cap.get(cv2.CAP_PROP_FPS)
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
        if not out.isOpened():
            raise ValueError(f"Cannot create output video file: {output_path}")
        self.reset()
        frame_idx = 0
        processed_count = 0
        if self.show_progress:
            print(f"\nProcessing video: {input_path}")
            print(f"  Resolution: {width}x{height}")
            print(f"  FPS: {fps:.1f}")
            print(f"  Total frames: {total_frames}")
            print(f"  Output: {output_path}")
            print("\nProcessing...")
        try:
            while True:
                ret, frame = cap.read()
                if not ret:
                    break
                if frame_idx < start_frame:
                    frame_idx += 1
                    continue
                if max_frames is not None and processed_count >= max_frames:
                    break
                dehazed_frame, info = self.dehaze_frame(frame)
                out.write(dehazed_frame)
                processed_count += 1
                frame_idx += 1
                if self.show_progress and processed_count % 10 == 0:
                    progress = frame_idx / total_frames * 100
                    haze = info.get('smoothed_haze_density', 0)
                    print(f"  Frame {frame_idx}/{total_frames} ({progress:.1f}%) | haze_density={haze:.3f}")
        finally:
            cap.release()
            out.release()
        if self.show_progress:
            print(f"\nCompleted! Processed {processed_count} frames.")
            print(f"Output saved to: {output_path}")
        return {
            'input_path': input_path,
            'output_path': output_path,
            'total_frames': total_frames,
            'processed_frames': processed_count,
            'fps': fps,
            'resolution': (width, height)
        }

    def process_video_with_preview(self, input_path: str, output_path: str = None,
                                display_fps: int = 30):
        if not os.path.exists(input_path):
            raise FileNotFoundError(f"Video file not found: {input_path}")
        cap = cv2.VideoCapture(input_path)
        if not cap.isOpened():
            raise ValueError(f"Cannot open video file: {input_path}")
        fps = cap.get(cv2.CAP_PROP_FPS)
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        out = None
        if output_path:
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
        self.reset()
        frame_idx = 0
        delay = int(1000 // display_fps)
        print(f"\nVideo Preview Mode (press 'q' to quit)")
        print(f"  Resolution: {width}x{height}")
        print(f"  Total frames: {total_frames}")
        try:
            while True:
                ret, frame = cap.read()
                if not ret:
                    break
                dehazed_frame, info = self.dehaze_frame(frame)
                combined = np.hstack((frame, dehazed_frame))
                cv2.putText(combined, f"Frame: {frame_idx}", (10, 30),
                            cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255, 2), 2)
                cv2.putText(combined, f"Haze: {info.get('smoothed_haze_density', 0):.3f}", (10, 70),
                            cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255, 2), 2)
                cv2.imshow('Original | Dehazed', combined)
                if out:
                    out.write(dehazed_frame)
                frame_idx += 1
                if cv2.waitKey(delay) & 0xFF == ord('q'):
                    break
        finally:
            cap.release()
            if out:
                out.release()
            cv2.destroyAllWindows()
        return {
            'input_path': input_path,
            'output_path': output_path,
            'processed_frames': frame_idx
        }


def create_synthetic_hazy_video(clear_video_path: str, output_path: str,
                             haze_level: float = 0.6,
                             haze_variation: float = 0.2):
    if not os.path.exists(clear_video_path):
        raise FileNotFoundError(f"Video file not found: {clear_video_path}")
    cap = cv2.VideoCapture(clear_video_path)
    if not cap.isOpened():
        raise ValueError(f"Cannot open video file: {clear_video_path}")
    fps = cap.get(cv2.CAP_PROP_FPS)
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
    if not out.isOpened():
            raise ValueError(f"Cannot create output video file: {output_path}")
    frame_idx = 0
    print(f"\nCreating synthetic hazy video...")
    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            phase = frame_idx / total_frames * 2 * np.pi
            current_haze = haze_level + np.sin(phase) * haze_variation
            current_haze = np.clip(current_haze, 0.1, 0.9)
            frame_float = frame.astype(np.float32) / 255.0
            atmospheric = np.ones_like(frame_float) * 0.85
            transmission = 1.0 - current_haze
            hazy = frame_float * transmission + atmospheric * (1 - transmission)
            hazy = np.clip(hazy * 255, 0, 255).astype(np.uint8)
            out.write(hazy)
            frame_idx += 1
            if frame_idx % 100 == 0:
                print(f"  Frame {frame_idx}/{total_frames}")
    finally:
        cap.release()
        out.release()
    print(f"Done! Output saved to: {output_path}")
    return {
        'output_path': output_path,
        'total_frames': frame_idx,
        'haze_level': haze_level,
        'haze_variation': haze_variation
    }


def evaluate_video_dehazing(original_video_path: str, dehazed_video_path: str,
                      sample_interval: int = 30) -> dict:
    from utils import evaluate_dehazing, print_evaluation_report
    if not os.path.exists(original_video_path) or not os.path.exists(dehazed_video_path):
        raise FileNotFoundError("Video files not found")
    cap_orig = cv2.VideoCapture(original_video_path)
    cap_dehazed = cv2.VideoCapture(dehazed_video_path)
    total_frames = min(
        int(cap_orig.get(cv2.CAP_PROP_FRAME_COUNT)),
        int(cap_dehazed.get(cv2.CAP_PROP_FRAME_COUNT))
    )
    metrics_list = []
    frame_idx = 0
    print(f"\nEvaluating video dehazing quality...")
    try:
        while True:
            ret1, frame1 = cap_orig.read()
            ret2, frame2 = cap_dehazed.read()
            if not ret1 or not ret2:
                break
            if frame_idx % sample_interval == 0:
                metrics = evaluate_dehazing(frame1, frame2)
                metrics_list.append(metrics)
                if frame_idx % (sample_interval * 10) == 0:
                    print(f"  Frame {frame_idx}/{total_frames}")
            frame_idx += 1
    finally:
        cap_orig.release()
        cap_dehazed.release()
    if len(metrics_list) == 0:
        return {}
    avg_metrics = {}
    for key in metrics_list[0].keys():
        values = [m[key] for m in metrics_list]
        avg_metrics[key] = np.mean(values)
    print_evaluation_report(avg_metrics, "Video Dehazing Evaluation (Average)")
    return avg_metrics
