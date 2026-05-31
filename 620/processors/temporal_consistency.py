import numpy as np
import cv2
from collections import deque
from config import TEMPORAL_CONFIG


class TemporalConsistency:
    def __init__(self, config=None):
        self.config = config or TEMPORAL_CONFIG
        self.method = self.config['method']
        self.alpha = self.config['alpha']
        self.flow_threshold = self.config['flow_threshold']
        self.consistency_weight = self.config['consistency_weight']
        
        self.enable_deflicker = self.config.get('enable_deflicker', True)
        self.deflicker_strength = self.config.get('deflicker_strength', 0.3)
        self.window_size = self.config.get('window_size', 5)
        
        self.prev_frame = None
        self.prev_warped = None
        self.prev_flow = None
        
        self.frame_buffer = deque(maxlen=self.window_size)
        self.brightness_history = deque(maxlen=self.window_size)
        self.warped_buffer = deque(maxlen=self.window_size)
        
    def reset(self):
        self.prev_frame = None
        self.prev_warped = None
        self.prev_flow = None
        self.frame_buffer.clear()
        self.brightness_history.clear()
        self.warped_buffer.clear()

    def _compute_optical_flow(self, prev_frame, curr_frame, method='farneback'):
        prev_gray = cv2.cvtColor((prev_frame * 255).astype(np.uint8), cv2.COLOR_BGR2GRAY)
        curr_gray = cv2.cvtColor((curr_frame * 255).astype(np.uint8), cv2.COLOR_BGR2GRAY)
        
        if method == 'farneback':
            flow = cv2.calcOpticalFlowFarneback(
                prev_gray, curr_gray, None,
                pyr_scale=0.5, levels=5, winsize=21,
                iterations=5, poly_n=7, poly_sigma=1.5, flags=0
            )
        elif method == 'tvl1':
            try:
                tvl1 = cv2.optflow.DualTVL1OpticalFlow_create()
                flow = tvl1.calc(prev_gray, curr_gray, None)
            except:
                flow = cv2.calcOpticalFlowFarneback(
                    prev_gray, curr_gray, None,
                    pyr_scale=0.5, levels=5, winsize=21,
                    iterations=5, poly_n=7, poly_sigma=1.5, flags=0
                )
        else:
            flow = cv2.calcOpticalFlowFarneback(
                prev_gray, curr_gray, None,
                pyr_scale=0.5, levels=5, winsize=21,
                iterations=5, poly_n=7, poly_sigma=1.5, flags=0
            )
        return flow

    def _warp_frame(self, frame, flow, border_mode=cv2.BORDER_REPLICATE):
        h, w = flow.shape[:2]
        flow_map_x, flow_map_y = np.meshgrid(np.arange(w), np.arange(h), indexing='ij')
        flow_map_x = flow_map_x.astype(np.float32).T + flow[..., 0]
        flow_map_y = flow_map_y.astype(np.float32).T + flow[..., 1]
        warped = cv2.remap(frame, flow_map_x, flow_map_y, cv2.INTER_LINEAR, borderMode=border_mode)
        return warped

    def _flow_guided_alignment(self, target_frame, reference_frame):
        flow = self._compute_optical_flow(reference_frame, target_frame)
        warped_reference = self._warp_frame(reference_frame, flow)
        
        flow_bw = self._compute_optical_flow(target_frame, reference_frame)
        warped_target = self._warp_frame(target_frame, flow_bw)
        
        fb_consistency = np.abs(warped_target - reference_frame).mean(axis=2)
        confidence = np.exp(-fb_consistency / 0.05)[..., np.newaxis]
        
        return warped_reference, confidence, flow

    def _detect_flicker(self, curr_frame):
        curr_brightness = curr_frame.mean()
        self.brightness_history.append(curr_brightness)
        
        if len(self.brightness_history) < 3:
            return 0.0
        
        brightness_array = np.array(self.brightness_history)
        grad = np.abs(np.gradient(brightness_array))
        flicker_score = np.mean(grad[-3:]) if len(grad) >= 3 else 0
        
        return flicker_score

    def _compute_brightness_correction(self, curr_frame):
        if len(self.frame_buffer) < 2:
            return curr_frame.astype(np.float32)
        
        curr_brightness = curr_frame.mean()
        history_brightness = np.mean([f.mean() for f in list(self.frame_buffer)[:-1]])
        
        brightness_ratio = history_brightness / (curr_brightness + 1e-8)
        brightness_ratio = np.clip(brightness_ratio, 0.9, 1.1)
        
        corrected = curr_frame.astype(np.float32) * brightness_ratio
        
        blend_alpha = min(1.0, len(self.frame_buffer) / self.window_size) * self.deflicker_strength
        result = blend_alpha * corrected + (1 - blend_alpha) * curr_frame.astype(np.float32)
        
        return np.clip(result, 0, 1)

    def _temporal_smooth_kernel(self, frames, flows=None):
        n = len(frames)
        if n == 0:
            return None
        if n == 1:
            return frames[0]
        
        center_idx = n // 2
        center_frame = frames[center_idx].astype(np.float32)
        
        result = np.zeros_like(center_frame)
        weight_sum = np.zeros_like(center_frame[..., 0:1])
        
        sigma_spatial = 10.0
        sigma_color = 0.1
        
        h, w = center_frame.shape[:2]
        y_coords, x_coords = np.meshgrid(np.arange(h), np.arange(w), indexing='ij')
        center_y, center_x = h // 2, w // 2
        
        for i, frame in enumerate(frames):
            frame_f32 = frame.astype(np.float32)
            
            if i != center_idx and flows is not None and i < len(flows):
                flow = flows[i]
                flow_mag = np.sqrt(flow[..., 0] ** 2 + flow[..., 1] ** 2)
                motion_weight = np.exp(-flow_mag / (self.flow_threshold + 1e-6))[..., np.newaxis]
            else:
                motion_weight = np.ones((h, w, 1), dtype=np.float32)
            
            color_diff = np.sum((frame_f32 - center_frame) ** 2, axis=2, keepdims=True)
            color_weight = np.exp(-color_diff / (2 * sigma_color ** 2))
            
            dist = np.sqrt((x_coords - center_x) ** 2 + (y_coords - center_y) ** 2)
            spatial_weight = np.exp(-dist ** 2 / (2 * sigma_spatial ** 2))[..., np.newaxis]
            
            temporal_dist = abs(i - center_idx)
            temporal_weight = np.exp(-temporal_dist / 2.0)
            
            combined_weight = motion_weight * color_weight * spatial_weight * temporal_weight
            
            result += frame_f32 * combined_weight
            weight_sum += combined_weight
        
        result = result / (weight_sum + 1e-8)
        return np.clip(result, 0, 1)

    def _method_flow_guided_smooth(self, curr_frame):
        if self.prev_frame is None:
            self.prev_frame = curr_frame.copy()
            self.frame_buffer.append(curr_frame.copy())
            return curr_frame.astype(np.float32)

        try:
            warped_prev, confidence, flow = self._flow_guided_alignment(curr_frame, self.prev_frame)
            
            self.warped_buffer.append(warped_prev)
            
            flicker_score = self._detect_flicker(curr_frame)
            need_deflicker = flicker_score > 0.01
            
            if need_deflicker and self.enable_deflicker:
                curr_corrected = self._compute_brightness_correction(curr_frame)
            else:
                curr_corrected = curr_frame.astype(np.float32)
            
            self.frame_buffer.append(curr_corrected.copy())
            
            if len(self.frame_buffer) >= 3:
                recent_frames = list(self.frame_buffer)
                smoothed = self._temporal_smooth_kernel(recent_frames)
                
                blend = confidence * self.alpha + (1 - confidence) * 0.1
                result = blend * warped_prev + (1 - blend) * smoothed
            else:
                result = confidence * self.alpha * warped_prev + (1 - confidence * self.alpha) * curr_corrected
            
            self.prev_warped = warped_prev
            self.prev_flow = flow
            
        except Exception as e:
            print(f"Flow guided smooth warning: {e}")
            result = curr_frame.astype(np.float32)
            self.frame_buffer.append(curr_frame.copy())

        self.prev_frame = curr_frame.copy()
        return np.clip(result, 0, 1).astype(np.float32)

    def _method_bidirectional_flow(self, curr_frame):
        if self.prev_frame is None:
            self.prev_frame = curr_frame.copy()
            self.frame_buffer.append(curr_frame.copy())
            return curr_frame.astype(np.float32)

        try:
            flow_fw = self._compute_optical_flow(self.prev_frame, curr_frame, method='farneback')
            warped_prev = self._warp_frame(self.prev_frame, flow_fw)
            
            flow_bw = self._compute_optical_flow(curr_frame, self.prev_frame, method='farneback')
            warped_curr = self._warp_frame(curr_frame, flow_bw)
            
            fb_error = np.abs(warped_curr - self.prev_frame).mean(axis=2, keepdims=True)
            occlusion_mask = (fb_error > 0.05).astype(np.float32)
            
            flow_mag = np.sqrt(flow_fw[..., 0] ** 2 + flow_fw[..., 1] ** 2)
            motion_confidence = np.exp(-flow_mag / 2.0)[..., np.newaxis]
            
            confidence = motion_confidence * (1 - occlusion_mask)
            
            flicker_score = self._detect_flicker(curr_frame)
            if flicker_score > 0.02 and self.enable_deflicker:
                curr_corrected = self._compute_brightness_correction(curr_frame)
            else:
                curr_corrected = curr_frame.astype(np.float32)
            
            self.frame_buffer.append(curr_corrected.copy())
            
            alpha = self.alpha * confidence
            result = alpha * warped_prev + (1 - alpha) * curr_corrected
            
            self.prev_warped = warped_prev
            self.prev_flow = flow_fw
            
        except Exception as e:
            print(f"Bidirectional flow warning: {e}")
            result = curr_frame.astype(np.float32)
            self.frame_buffer.append(curr_frame.copy())

        self.prev_frame = curr_frame.copy()
        return np.clip(result, 0, 1).astype(np.float32)

    def _method_deflicker_only(self, curr_frame):
        self.frame_buffer.append(curr_frame.copy())
        
        flicker_score = self._detect_flicker(curr_frame)
        
        if flicker_score > 0.01 and self.enable_deflicker:
            result = self._compute_brightness_correction(curr_frame)
        else:
            result = curr_frame.astype(np.float32)
        
        if len(self.frame_buffer) >= 3:
            recent_frames = list(self.frame_buffer)[-3:]
            weights = np.array([0.2, 0.3, 0.5])
            weighted_avg = np.zeros_like(result)
            for i, f in enumerate(recent_frames):
                weighted_avg += f.astype(np.float32) * weights[i]
            
            blend = min(flicker_score * 5, self.deflicker_strength)
            result = blend * weighted_avg + (1 - blend) * result
        
        return np.clip(result, 0, 1).astype(np.float32)

    def process(self, curr_frame):
        if self.method == 'optical_flow':
            return self._method_flow_guided_smooth(curr_frame)
        elif self.method == 'flow_guided':
            return self._method_flow_guided_smooth(curr_frame)
        elif self.method == 'bidirectional_flow':
            return self._method_bidirectional_flow(curr_frame)
        elif self.method == 'simple_average':
            return self._method_deflicker_only(curr_frame)
        elif self.method == 'rolling_guidance':
            return self._method_flow_guided_smooth(curr_frame)
        elif self.method == 'deep_flow':
            return self._method_bidirectional_flow(curr_frame)
        elif self.method == 'deflicker':
            return self._method_deflicker_only(curr_frame)
        else:
            return curr_frame.astype(np.float32)


def check_temporal_consistency(frames, threshold=0.1):
    if len(frames) < 2:
        return 1.0

    consistency_scores = []
    for i in range(1, len(frames)):
        diff = np.abs(frames[i].astype(np.float32) - frames[i-1].astype(np.float32)).mean()
        score = np.exp(-diff / threshold)
        consistency_scores.append(score)

    return np.mean(consistency_scores)


def compute_interframe_mse(prev_frame, curr_frame):
    return np.mean((prev_frame.astype(np.float32) - curr_frame.astype(np.float32)) ** 2)


def compute_flicker_metric(frames):
    if len(frames) < 3:
        return 0.0
    
    brightness = [f.mean() for f in frames]
    brightness = np.array(brightness)
    
    diffs = np.abs(np.diff(brightness))
    flicker_score = np.mean(diffs)
    
    return flicker_score
