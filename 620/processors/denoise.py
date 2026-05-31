import numpy as np
import cv2
from collections import deque
from utils.common import generate_weights
from config import DENOISE_CONFIG


class MultiFrameDenoiser:
    def __init__(self, config=None):
        self.config = config or DENOISE_CONFIG
        self.num_frames = self.config['num_frames']
        self.fusion_method = self.config['fusion_method']
        self.center_weight = self.config['center_weight']
        self.temporal_weight = self.config['temporal_weight']
        self.enable_flow_alignment = self.config.get('enable_flow_alignment', True)
        self.flow_method = self.config.get('flow_method', 'farneback')
        
        self.frame_buffer = deque(maxlen=self.num_frames)
        self.flow_cache = {}
        
        self.weights = generate_weights(
            self.num_frames,
            self.center_weight,
            self.temporal_weight
        )

    def reset(self):
        self.frame_buffer.clear()
        self.flow_cache = {}

    def add_frame(self, frame):
        self.frame_buffer.append(frame.copy())

    def is_ready(self):
        return len(self.frame_buffer) == self.num_frames

    def _compute_optical_flow(self, frame1, frame2):
        cache_key = (id(frame1), id(frame2))
        if cache_key in self.flow_cache:
            return self.flow_cache[cache_key]
        
        gray1 = cv2.cvtColor((frame1 * 255).astype(np.uint8), cv2.COLOR_BGR2GRAY)
        gray2 = cv2.cvtColor((frame2 * 255).astype(np.uint8), cv2.COLOR_BGR2GRAY)
        
        if self.flow_method == 'farneback':
            flow = cv2.calcOpticalFlowFarneback(
                gray1, gray2, None,
                pyr_scale=0.5, levels=4, winsize=17,
                iterations=4, poly_n=5, poly_sigma=1.2, flags=0
            )
        elif self.flow_method == 'tvl1':
            try:
                tvl1 = cv2.optflow.DualTVL1OpticalFlow_create()
                flow = tvl1.calc(gray1, gray2, None)
            except:
                flow = cv2.calcOpticalFlowFarneback(
                    gray1, gray2, None,
                    pyr_scale=0.5, levels=4, winsize=17,
                    iterations=4, poly_n=5, poly_sigma=1.2, flags=0
                )
        else:
            flow = cv2.calcOpticalFlowFarneback(
                gray1, gray2, None,
                pyr_scale=0.5, levels=4, winsize=17,
                iterations=4, poly_n=5, poly_sigma=1.2, flags=0
            )
        
        self.flow_cache[cache_key] = flow
        return flow

    def _warp_frame(self, frame, flow):
        h, w = flow.shape[:2]
        flow_map_x, flow_map_y = np.meshgrid(np.arange(w), np.arange(h), indexing='ij')
        flow_map_x = flow_map_x.astype(np.float32).T + flow[..., 0]
        flow_map_y = flow_map_y.astype(np.float32).T + flow[..., 1]
        warped = cv2.remap(frame, flow_map_x, flow_map_y, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
        return warped

    def _flow_guided_alignment(self, frames):
        center_idx = self.num_frames // 2
        center_frame = frames[center_idx].astype(np.float32)
        
        aligned_frames = []
        confidences = []
        
        for i, frame in enumerate(frames):
            if i == center_idx:
                aligned_frames.append(center_frame)
                confidences.append(np.ones_like(center_frame[..., 0:1]))
                continue
            
            try:
                frame_f32 = frame.astype(np.float32)
                
                flow_fw = self._compute_optical_flow(frame_f32, center_frame)
                warped_frame = self._warp_frame(frame_f32, flow_fw)
                
                flow_bw = self._compute_optical_flow(center_frame, frame_f32)
                warped_center = self._warp_frame(center_frame, flow_bw)
                
                fb_error = np.abs(warped_center - frame_f32).mean(axis=2, keepdims=True)
                confidence = np.exp(-fb_error / 0.05)
                
                flow_mag = np.sqrt(flow_fw[..., 0] ** 2 + flow_fw[..., 1] ** 2)
                motion_confidence = np.exp(-flow_mag / 5.0)[..., np.newaxis]
                
                combined_confidence = confidence * motion_confidence
                
                aligned_frames.append(warped_frame)
                confidences.append(combined_confidence)
                
            except Exception as e:
                print(f"Flow alignment warning: {e}")
                aligned_frames.append(frame.astype(np.float32))
                confidences.append(np.ones_like(center_frame[..., 0:1]) * 0.5)
        
        return aligned_frames, confidences

    def _weighted_average(self, frames):
        if self.enable_flow_alignment:
            aligned_frames, confidences = self._flow_guided_alignment(frames)
        else:
            aligned_frames = [f.astype(np.float32) for f in frames]
            confidences = [np.ones_like(f[..., 0:1]) for f in aligned_frames]
        
        result = np.zeros_like(aligned_frames[0])
        weight_sum = np.zeros_like(confidences[0])
        
        for i, (frame, conf) in enumerate(zip(aligned_frames, confidences)):
            weight = self.weights[i] * conf
            result += frame * weight
            weight_sum += weight
        
        return np.clip(result / (weight_sum + 1e-8), 0, 1).astype(np.float32)

    def _gaussian_fusion(self, frames):
        center_idx = self.num_frames // 2
        
        if self.enable_flow_alignment:
            aligned_frames, confidences = self._flow_guided_alignment(frames)
        else:
            aligned_frames = [f.astype(np.float32) for f in frames]
            confidences = [np.ones_like(f[..., 0:1]) for f in aligned_frames]
        
        center_frame = aligned_frames[center_idx]
        result = np.zeros_like(center_frame)
        weight_sum = np.zeros_like(center_frame[..., 0:1])

        for i, (frame, conf) in enumerate(zip(aligned_frames, confidences)):
            frame_f32 = frame.astype(np.float32)
            diff = np.abs(frame_f32 - center_frame)
            spatial_var = np.var(diff, axis=(0, 1), keepdims=True) + 1e-6
            color_weight = np.exp(-diff ** 2 / (2 * spatial_var))
            
            weight = self.weights[i] * conf * color_weight
            result += frame_f32 * weight
            weight_sum += weight

        return np.clip(result / (weight_sum + 1e-8), 0, 1).astype(np.float32)

    def _bilateral_fusion(self, frames):
        center_idx = self.num_frames // 2
        
        if self.enable_flow_alignment:
            aligned_frames, confidences = self._flow_guided_alignment(frames)
        else:
            aligned_frames = [f.astype(np.float32) for f in frames]
            confidences = [np.ones_like(f[..., 0:1]) for f in aligned_frames]
        
        center_frame = aligned_frames[center_idx]
        result = np.zeros_like(center_frame)
        weight_sum = np.zeros_like(center_frame[..., 0:1])

        sigma_color = 0.08
        sigma_space = 30.0

        h, w = center_frame.shape[:2]
        y_coords, x_coords = np.meshgrid(np.arange(h), np.arange(w), indexing='ij')

        for i, (frame, conf) in enumerate(zip(aligned_frames, confidences)):
            frame_f32 = frame.astype(np.float32)
            
            color_diff = np.sum((frame_f32 - center_frame) ** 2, axis=2, keepdims=True)
            color_weight = np.exp(-color_diff / (2 * sigma_color ** 2))

            center_y, center_x = h // 2, w // 2
            spatial_dist = np.sqrt((x_coords - center_x) ** 2 + (y_coords - center_y) ** 2)
            spatial_weight = np.exp(-spatial_dist ** 2 / (2 * sigma_space ** 2))
            spatial_weight = spatial_weight[..., np.newaxis]

            weight = self.weights[i] * conf * color_weight * spatial_weight
            result += frame_f32 * weight
            weight_sum += weight

        return np.clip(result / (weight_sum + 1e-8), 0, 1).astype(np.float32)

    def _adaptive_fusion(self, frames):
        center_idx = self.num_frames // 2
        
        if self.enable_flow_alignment:
            aligned_frames, confidences = self._flow_guided_alignment(frames)
        else:
            aligned_frames = [f.astype(np.float32) for f in frames]
            confidences = [np.ones_like(f[..., 0:1]) for f in aligned_frames]
        
        center_frame = aligned_frames[center_idx]

        motion_scores = []
        for i, frame in enumerate(aligned_frames):
            if i == center_idx:
                motion_scores.append(0.0)
            else:
                diff = np.abs(frame.astype(np.float32) - center_frame).mean()
                motion_scores.append(diff)

        motion_scores = np.array(motion_scores)
        adaptive_weights = np.exp(-motion_scores * 8) * self.weights
        adaptive_weights = adaptive_weights / adaptive_weights.sum()

        result = np.zeros_like(center_frame)
        weight_sum = np.zeros_like(center_frame[..., 0:1])
        
        for i, (frame, conf) in enumerate(zip(aligned_frames, confidences)):
            weight = adaptive_weights[i] * conf
            result += frame.astype(np.float32) * weight
            weight_sum += weight

        return np.clip(result / (weight_sum + 1e-8), 0, 1).astype(np.float32)

    def _flow_guided_patch_based(self, frames):
        center_idx = self.num_frames // 2
        
        if self.enable_flow_alignment:
            aligned_frames, confidences = self._flow_guided_alignment(frames)
        else:
            aligned_frames = [f.astype(np.float32) for f in frames]
            confidences = [np.ones_like(f[..., 0:1]) for f in aligned_frames]
        
        center_frame = aligned_frames[center_idx]
        result = np.zeros_like(center_frame)
        weight_sum = np.zeros_like(center_frame[..., 0:1])
        
        patch_size = 5
        half_patch = patch_size // 2
        sigma_patch = 0.1
        
        h, w = center_frame.shape[:2]
        
        for i, (frame, conf) in enumerate(zip(aligned_frames, confidences)):
            frame_f32 = frame.astype(np.float32)
            
            frame_blur = cv2.GaussianBlur(frame_f32, (patch_size, patch_size), 0)
            center_blur = cv2.GaussianBlur(center_frame, (patch_size, patch_size), 0)
            
            patch_diff = np.sum((frame_blur - center_blur) ** 2, axis=2, keepdims=True)
            patch_weight = np.exp(-patch_diff / (2 * sigma_patch ** 2))
            
            weight = self.weights[i] * conf * patch_weight
            result += frame_f32 * weight
            weight_sum += weight
        
        return np.clip(result / (weight_sum + 1e-8), 0, 1).astype(np.float32)

    def process(self, frame=None):
        if frame is not None:
            self.add_frame(frame)

        if not self.is_ready():
            if len(self.frame_buffer) > 0:
                return self.frame_buffer[-1].copy()
            return frame

        frames = list(self.frame_buffer)
        self.flow_cache = {}

        if self.fusion_method == 'weighted_average':
            return self._weighted_average(frames)
        elif self.fusion_method == 'gaussian':
            return self._gaussian_fusion(frames)
        elif self.fusion_method == 'bilateral':
            return self._bilateral_fusion(frames)
        elif self.fusion_method == 'adaptive':
            return self._adaptive_fusion(frames)
        elif self.fusion_method == 'flow_guided':
            return self._flow_guided_patch_based(frames)
        else:
            return self._weighted_average(frames)


def apply_bm3d_denoise(img, sigma=10):
    try:
        import bm3d
        img_uint8 = (img * 255).clip(0, 255).astype(np.uint8)
        denoised = bm3d.bm3d(img_uint8, sigma_psd=sigma)
        return denoised.astype(np.float32) / 255.0
    except ImportError:
        return img


def apply_non_local_means(img, h=10, template_window_size=7, search_window_size=21):
    img_uint8 = (img * 255).clip(0, 255).astype(np.uint8)
    if img.ndim == 3:
        denoised = cv2.fastNlMeansDenoisingColored(
            img_uint8, None, h, h, template_window_size, search_window_size
        )
    else:
        denoised = cv2.fastNlMeansDenoising(
            img_uint8, None, h, template_window_size, search_window_size
        )
    return denoised.astype(np.float32) / 255.0


def apply_gaussian_blur(img, kernel_size=5, sigma=1.0):
    return cv2.GaussianBlur(img, (kernel_size, kernel_size), sigma)


def compute_texture_complexity(img):
    gray = cv2.cvtColor((img * 255).astype(np.uint8), cv2.COLOR_BGR2GRAY)
    sobel_x = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
    sobel_y = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=3)
    gradient_mag = np.sqrt(sobel_x ** 2 + sobel_y ** 2)
    texture_score = np.mean(gradient_mag) / 255.0
    return texture_score
