
import numpy as np
from scipy.ndimage import map_coordinates, gaussian_filter
import cv2
from collections import deque

from phase_correlation import PhaseCorrelationRegistrator


class VideoStabilizer:
    def __init__(self, smoothing_window=30, max_correction=50.0):
        self.registrator = PhaseCorrelationRegistrator()
        self.smoothing_window = smoothing_window
        self.max_correction = max_correction
        
        self.frame_transforms = []
        self.smoothed_transforms = []
        self.cumulative_transform = np.zeros(3)
        
        self.dx_buffer = deque(maxlen=smoothing_window)
        self.dy_buffer = deque(maxlen=smoothing_window)
        self.angle_buffer = deque(maxlen=smoothing_window)
    
    def _preprocess_frame(self, frame):
        if len(frame.shape) == 3:
            gray = np.mean(frame, axis=2)
        else:
            gray = frame.copy()
        
        gray = gray.astype(np.float32)
        
        return gray
    
    def estimate_frame_transform(self, prev_frame, curr_frame):
        prev_gray = self._preprocess_frame(prev_frame)
        curr_gray = self._preprocess_frame(curr_frame)
        
        rows, cols = prev_gray.shape
        
        try:
            angle, scale, _ = self.registrator.estimate_rotation_scale(prev_gray, curr_gray)
            
            curr_rotated = self._rotate_image(curr_gray, -angle)
            
            dx, dy, _ = self.registrator.estimate_translation(prev_gray, curr_rotated)
        except:
            dx, dy, angle = 0.0, 0.0, 0.0
        
        dx = np.clip(dx, -self.max_correction, self.max_correction)
        dy = np.clip(dy, -self.max_correction, self.max_correction)
        angle = np.clip(angle, -10.0, 10.0)
        
        return dx, dy, angle
    
    def _rotate_image(self, img, angle):
        rows, cols = img.shape
        center = (cols // 2, rows // 2)
        
        M = cv2.getRotationMatrix2D(center, angle, 1.0)
        rotated = cv2.warpAffine(
            img.astype(np.float32), M, (cols, rows),
            flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_CONSTANT, borderValue=0
        )
        
        return rotated.astype(np.float32)
    
    def _smooth_transform(self, dx, dy, angle):
        self.dx_buffer.append(dx)
        self.dy_buffer.append(dy)
        self.angle_buffer.append(angle)
        
        weights = np.linspace(0.1, 1.0, len(self.dx_buffer))
        weights = weights / weights.sum()
        
        smooth_dx = np.average(self.dx_buffer, weights=weights)
        smooth_dy = np.average(self.dy_buffer, weights=weights)
        smooth_angle = np.average(self.angle_buffer, weights=weights)
        
        return smooth_dx, smooth_dy, smooth_angle
    
    def _apply_stabilization_transform(self, frame, dx, dy, angle):
        if len(frame.shape) == 3:
            rows, cols, channels = frame.shape
            stabilized = np.zeros_like(frame)
            
            for c in range(channels):
                stabilized[:, :, c] = self._warp_single_channel(
                    frame[:, :, c], -dx, -dy, -angle
                )
        else:
            rows, cols = frame.shape
            stabilized = self._warp_single_channel(frame, -dx, -dy, -angle)
        
        return stabilized
    
    def _warp_single_channel(self, img, dx, dy, angle):
        rows, cols = img.shape
        
        center_y = rows // 2
        center_x = cols // 2
        
        angle_rad = np.deg2rad(angle)
        cos_theta = np.cos(angle_rad)
        sin_theta = np.sin(angle_rad)
        
        y_grid, x_grid = np.mgrid[0:rows, 0:cols]
        
        y_centered = y_grid - center_y - dy
        x_centered = x_grid - center_x - dx
        
        src_y = cos_theta * y_centered + sin_theta * x_centered + center_y
        src_x = -sin_theta * y_centered + cos_theta * x_centered + center_x
        
        coords = np.vstack([src_y.ravel(), src_x.ravel()])
        warped = map_coordinates(
            img.astype(np.float32), coords, order=3, mode='constant', cval=0
        )
        warped = warped.reshape(rows, cols)
        
        return warped.astype(img.dtype)
    
    def stabilize_frame(self, prev_frame, curr_frame):
        dx, dy, angle = self.estimate_frame_transform(prev_frame, curr_frame)
        
        smooth_dx, smooth_dy, smooth_angle = self._smooth_transform(dx, dy, angle)
        
        correction_dx = dx - smooth_dx
        correction_dy = dy - smooth_dy
        correction_angle = angle - smooth_angle
        
        self.cumulative_transform += np.array([correction_dx, correction_dy, correction_angle])
        
        stabilized = self._apply_stabilization_transform(
            curr_frame, 
            self.cumulative_transform[0], 
            self.cumulative_transform[1], 
            self.cumulative_transform[2]
        )
        
        transform_info = {
            'raw_transform': (dx, dy, angle),
            'smoothed_transform': (smooth_dx, smooth_dy, smooth_angle),
            'correction': (correction_dx, correction_dy, correction_angle),
            'cumulative': (self.cumulative_transform[0], self.cumulative_transform[1], self.cumulative_transform[2])
        }
        
        return stabilized, transform_info
    
    def stabilize_video(self, frames, show_progress=False):
        if len(frames) < 2:
            return frames, []
        
        stabilized_frames = [frames[0].copy()]
        transform_history = []
        
        self.reset()
        
        for i in range(1, len(frames)):
            prev_frame = frames[i-1]
            curr_frame = frames[i]
            
            stabilized, transform_info = self.stabilize_frame(prev_frame, curr_frame)
            stabilized_frames.append(stabilized)
            transform_history.append(transform_info)
            
            if show_progress and i % 10 == 0:
                print(f"Stabilized frame {i}/{len(frames)}")
        
        return stabilized_frames, transform_history
    
    def stabilize_video_file(self, input_path, output_path=None):
        cap = cv2.VideoCapture(input_path)
        
        if not cap.isOpened():
            raise ValueError(f"Cannot open video file: {input_path}")
        
        fps = cap.get(cv2.CAP_PROP_FPS)
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        
        frames = []
        for i in range(total_frames):
            ret, frame = cap.read()
            if not ret:
                break
            frames.append(frame)
        
        cap.release()
        
        stabilized_frames, transform_history = self.stabilize_video(frames, show_progress=True)
        
        if output_path is not None:
            fourcc = cv2.VideoWriter_fourcc(*'XVID')
            out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
            
            for frame in stabilized_frames:
                if frame.dtype != np.uint8:
                    frame = np.clip(frame, 0, 255).astype(np.uint8)
                out.write(frame)
            
            out.release()
            print(f"Stabilized video saved to {output_path}")
        
        return stabilized_frames, transform_history
    
    def get_stability_metrics(self, transform_history):
        if not transform_history:
            return {}
        
        raw_dx = [t['raw_transform'][0] for t in transform_history]
        raw_dy = [t['raw_transform'][1] for t in transform_history]
        raw_angle = [t['raw_transform'][2] for t in transform_history]
        
        smooth_dx = [t['smoothed_transform'][0] for t in transform_history]
        smooth_dy = [t['smoothed_transform'][1] for t in transform_history]
        smooth_angle = [t['smoothed_transform'][2] for t in transform_history]
        
        metrics = {
            'raw_translation_std': np.std(np.sqrt(np.array(raw_dx)**2 + np.array(raw_dy)**2)),
            'smooth_translation_std': np.std(np.sqrt(np.array(smooth_dx)**2 + np.array(smooth_dy)**2)),
            'raw_rotation_std': np.std(raw_angle),
            'smooth_rotation_std': np.std(smooth_angle),
            'stability_improvement_translation': 1.0 - (np.std(np.sqrt(np.array(smooth_dx)**2 + np.array(smooth_dy)**2)) / 
                                                      np.std(np.sqrt(np.array(raw_dx)**2 + np.array(raw_dy)**2)) + 1e-12),
            'stability_improvement_rotation': 1.0 - (np.std(smooth_angle) / (np.std(raw_angle) + 1e-12))
        }
        
        return metrics
    
    def reset(self):
        self.frame_transforms = []
        self.smoothed_transforms = []
        self.cumulative_transform = np.zeros(3)
        self.dx_buffer.clear()
        self.dy_buffer.clear()
        self.angle_buffer.clear()
