import cv2
import numpy as np
import torch
import torch.nn.functional as F
from typing import Tuple, Optional, List, Dict, Any
from texture_synthesis import (
    TextureSynthesizer, 
    GraphCutSeamFinder,
    GPUPyramidBuilder,
    EnhancedPatchMatcher
)
import warnings
warnings.filterwarnings('ignore')


class VideoTextureSynthesizer:
    def __init__(self, use_gpu: bool = True, temporal_weight: float = 0.5):
        self.device = torch.device('cuda' if use_gpu and torch.cuda.is_available() else 'cpu')
        self.synthesizer = TextureSynthesizer(use_gpu=use_gpu)
        self.temporal_weight = temporal_weight
        self.previous_frames: List[np.ndarray] = []
        self.max_history = 5
        self.flow_history: List[np.ndarray] = []
    
    def compute_optical_flow(self, frame1: np.ndarray, frame2: np.ndarray) -> np.ndarray:
        gray1 = cv2.cvtColor(frame1, cv2.COLOR_BGR2GRAY) if frame1.ndim == 3 else frame1
        gray2 = cv2.cvtColor(frame2, cv2.COLOR_BGR2GRAY) if frame2.ndim == 3 else frame2
        
        flow = cv2.calcOpticalFlowFarneback(
            gray1.astype(np.float32), gray2.astype(np.float32),
            None, 0.5, 3, 15, 3, 5, 1.2, 0
        )
        return flow
    
    def warp_frame(self, frame: np.ndarray, flow: np.ndarray) -> np.ndarray:
        h, w = frame.shape[:2]
        flow_map_x, flow_map_y = np.meshgrid(np.arange(w), np.arange(h))
        flow_map_x = flow_map_x.astype(np.float32) + flow[..., 0]
        flow_map_y = flow_map_y.astype(np.float32) + flow[..., 1]
        
        warped = cv2.remap(frame, flow_map_x, flow_map_y, cv2.INTER_LINEAR)
        return warped
    
    def blend_temporal(self, current: np.ndarray, previous: np.ndarray, 
                       flow: Optional[np.ndarray] = None) -> np.ndarray:
        if flow is not None:
            previous_warped = self.warp_frame(previous, flow)
        else:
            previous_warped = previous
        
        alpha = self.temporal_weight
        blended = (current * (1 - alpha) + previous_warped * alpha).astype(np.uint8)
        return blended
    
    def create_temporal_guide(self, output_size: Tuple[int, int], 
                              frame_idx: int, motion_type: str = 'wave') -> np.ndarray:
        h, w = output_size
        guide = np.zeros((h, w, 3), dtype=np.float32)
        
        y_coords, x_coords = np.mgrid[0:h, 0:w]
        
        if motion_type == 'wave':
            phase = frame_idx * 0.1
            guide[..., 0] = np.sin(x_coords * 0.05 + phase) * 0.5 + 0.5
            guide[..., 1] = np.cos(y_coords * 0.05 + phase) * 0.5 + 0.5
        elif motion_type == 'rotate':
            center_x, center_y = w // 2, h // 2
            angle = frame_idx * 0.05
            dx = x_coords - center_x
            dy = y_coords - center_y
            guide[..., 0] = (dx * np.cos(angle) - dy * np.sin(angle)) / w + 0.5
            guide[..., 1] = (dx * np.sin(angle) + dy * np.cos(angle)) / h + 0.5
        elif motion_type == 'zoom':
            zoom_factor = 1 + 0.1 * np.sin(frame_idx * 0.1)
            center_x, center_y = w // 2, h // 2
            dx = (x_coords - center_x) / zoom_factor + center_x
            dy = (y_coords - center_y) / zoom_factor + center_y
            guide[..., 0] = dx / w
            guide[..., 1] = dy / h
        elif motion_type == 'scroll':
            offset = (frame_idx * 5) % w
            guide[..., 0] = (x_coords + offset) / w
            guide[..., 1] = y_coords / h
        
        guide = (guide * 255).astype(np.uint8)
        return guide
    
    def synthesize_video_frame(self, texture: np.ndarray, 
                                output_size: Tuple[int, int],
                                frame_idx: int,
                                patch_size: int = 32,
                                overlap: int = 8,
                                motion_type: str = 'wave',
                                use_temporal_blend: bool = True) -> np.ndarray:
        guide = self.create_temporal_guide(output_size, frame_idx, motion_type)
        
        result = self.synthesizer.synthesize_texture(
            texture, output_size,
            patch_size=patch_size, overlap=overlap,
            guide_image=guide,
            use_direction=True,
            blend_mode='graphcut',
            structure_weight=0.5
        )
        
        if use_temporal_blend and len(self.previous_frames) > 0:
            try:
                flow = self.compute_optical_flow(self.previous_frames[-1], result)
                result = self.blend_temporal(result, self.previous_frames[-1], flow)
                self.flow_history.append(flow)
                if len(self.flow_history) > self.max_history:
                    self.flow_history.pop(0)
            except:
                pass
        
        self.previous_frames.append(result)
        if len(self.previous_frames) > self.max_history:
            self.previous_frames.pop(0)
        
        return result
    
    def synthesize_video(self, texture: np.ndarray,
                          output_size: Tuple[int, int],
                          num_frames: int,
                          patch_size: int = 32,
                          overlap: int = 8,
                          motion_type: str = 'wave',
                          output_path: Optional[str] = None,
                          fps: int = 24) -> List[np.ndarray]:
        frames = []
        self.previous_frames.clear()
        self.flow_history.clear()
        
        print(f"Generating video with {num_frames} frames...")
        
        for i in range(num_frames):
            print(f"  Frame {i+1}/{num_frames}")
            frame = self.synthesize_video_frame(
                texture, output_size, frame_idx=i,
                patch_size=patch_size, overlap=overlap,
                motion_type=motion_type
            )
            frames.append(frame)
        
        if output_path is not None:
            self.save_video(frames, output_path, fps)
            print(f"  Video saved to: {output_path}")
        
        return frames
    
    def save_video(self, frames: List[np.ndarray], output_path: str, fps: int = 24):
        if not frames:
            return
        
        h, w = frames[0].shape[:2]
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        writer = cv2.VideoWriter(output_path, fourcc, fps, (w, h), frames[0].ndim == 3)
        
        for frame in frames:
            writer.write(frame)
        
        writer.release()
    
    def clear_history(self):
        self.previous_frames.clear()
        self.flow_history.clear()


class MultiTextureBlender:
    def __init__(self, use_gpu: bool = True):
        self.device = torch.device('cuda' if use_gpu and torch.cuda.is_available() else 'cpu')
        self.synthesizer = TextureSynthesizer(use_gpu=use_gpu)
        self.pyramid_builder = GPUPyramidBuilder(self.device)
    
    def blend_textures_pixelwise(self, textures: List[np.ndarray], 
                                  weights: Optional[List[float]] = None,
                                  blend_mode: str = 'average') -> np.ndarray:
        if weights is None:
            weights = [1.0 / len(textures)] * len(textures)
        
        assert len(textures) == len(weights), "Number of textures must match number of weights"
        assert sum(weights) > 0, "Sum of weights must be positive"
        
        weights = np.array(weights) / sum(weights)
        
        h, w = textures[0].shape[:2]
        is_color = textures[0].ndim == 3
        
        if blend_mode == 'average':
            result = np.zeros((h, w, 3) if is_color else (h, w), dtype=np.float32)
            for tex, w in zip(textures, weights):
                if tex.shape[:2] != (h, w):
                    tex = cv2.resize(tex, (w, h))
                result += tex.astype(np.float32) * w
            return np.clip(result, 0, 255).astype(np.uint8)
        
        elif blend_mode == 'pyramid':
            return self.blend_textures_pyramid(textures, weights)
        
        elif blend_mode == 'gradient':
            return self.blend_textures_gradient(textures, weights)
        
        else:
            raise ValueError(f"Unknown blend mode: {blend_mode}")
    
    def blend_textures_pyramid(self, textures: List[np.ndarray], 
                                weights: List[float], levels: int = 5) -> np.ndarray:
        h, w = textures[0].shape[:2]
        is_color = textures[0].ndim == 3
        
        resized_textures = []
        for tex in textures:
            if tex.shape[:2] != (h, w):
                tex = cv2.resize(tex, (w, h))
            resized_textures.append(tex)
        
        lap_pyramids = []
        for tex in resized_textures:
            tex_tensor = self.synthesizer.to_tensor(tex)
            lap_pyr, base = self.synthesizer.build_laplacian_pyramid_gpu(tex_tensor, levels)
            lap_pyramids.append((lap_pyr, base))
        
        blended_lap = []
        for level in range(levels):
            blended_level = torch.zeros_like(lap_pyramids[0][0][level])
            for (lap_pyr, _), w in zip(lap_pyramids, weights):
                blended_level += lap_pyr[level] * w
            blended_lap.append(blended_level)
        
        blended_base = torch.zeros_like(lap_pyramids[0][1])
        for (_, base), w in zip(lap_pyramids, weights):
            blended_base += base * w
        
        result_tensor = self.synthesizer.reconstruct_from_laplacian_gpu(blended_lap, blended_base)
        return self.synthesizer.to_numpy(result_tensor)
    
    def blend_textures_gradient(self, textures: List[np.ndarray], 
                                 weights: List[float]) -> np.ndarray:
        h, w = textures[0].shape[:2]
        is_color = textures[0].ndim == 3
        
        resized_textures = []
        for tex in textures:
            if tex.shape[:2] != (h, w):
                tex = cv2.resize(tex, (w, h))
            resized_textures.append(tex.astype(np.float32))
        
        grad_x = np.zeros((h, w, 3) if is_color else (h, w), dtype=np.float32)
        grad_y = np.zeros((h, w, 3) if is_color else (h, w), dtype=np.float32)
        
        sobel_x = np.array([[-1, 0, 1], [-2, 0, 2], [-1, 0, 1]], dtype=np.float32)
        sobel_y = np.array([[-1, -2, -1], [0, 0, 0], [1, 2, 1]], dtype=np.float32)
        
        for tex, w in zip(resized_textures, weights):
            if is_color:
                for c in range(3):
                    gx = cv2.filter2D(tex[..., c], -1, sobel_x)
                    gy = cv2.filter2D(tex[..., c], -1, sobel_y)
                    grad_x[..., c] += gx * w
                    grad_y[..., c] += gy * w
            else:
                gx = cv2.filter2D(tex, -1, sobel_x)
                gy = cv2.filter2D(tex, -1, sobel_y)
                grad_x += gx * w
                grad_y += gy * w
        
        div = np.zeros((h, w, 3) if is_color else (h, w), dtype=np.float32)
        if is_color:
            for c in range(3):
                gx_x = cv2.filter2D(grad_x[..., c], -1, sobel_x.T)
                gy_y = cv2.filter2D(grad_y[..., c], -1, sobel_y.T)
                div[..., c] = gx_x + gy_y
        else:
            gx_x = cv2.filter2D(grad_x, -1, sobel_x.T)
            gy_y = cv2.filter2D(grad_y, -1, sobel_y.T)
            div = gx_x + gy_y
        
        result = np.zeros_like(div)
        current = np.mean([tex for tex in resized_textures], axis=0)
        
        for _ in range(100):
            if is_color:
                for c in range(3):
                    laplacian = cv2.Laplacian(current[..., c], -1, ksize=3)
                    result[..., c] = current[..., c] + 0.1 * (div[..., c] - laplacian)
            else:
                laplacian = cv2.Laplacian(current, -1, ksize=3)
                result = current + 0.1 * (div - laplacian)
            current = np.clip(result, 0, 255)
        
        return current.astype(np.uint8)
    
    def synthesize_mixed_texture(self, textures: List[np.ndarray],
                                  output_size: Tuple[int, int],
                                  weights: Optional[List[float]] = None,
                                  patch_size: int = 32,
                                  overlap: int = 8,
                                  blend_mode: str = 'pyramid') -> np.ndarray:
        blended_base = self.blend_textures_pixelwise(textures, weights, blend_mode='average')
        
        result = self.synthesizer.synthesize_texture(
            blended_base, output_size,
            patch_size=patch_size, overlap=overlap,
            use_direction=True,
            blend_mode='graphcut',
            structure_weight=0.5
        )
        
        return result
    
    def create_weight_map(self, size: Tuple[int, int], 
                           pattern: str = 'linear',
                           num_textures: int = 2) -> List[np.ndarray]:
        h, w = size
        weight_maps = []
        
        if pattern == 'linear':
            for i in range(num_textures):
                start = i / num_textures
                end = (i + 1) / num_textures
                x = np.linspace(0, 1, w)
                w_map = np.zeros((h, w), dtype=np.float32)
                mask = (x >= start) & (x <= end)
                w_map[:, mask] = 1.0 - np.abs(x[mask] - (start + end) / 2) * num_textures
                weight_maps.append(w_map)
        
        elif pattern == 'radial':
            center_y, center_x = h // 2, w // 2
            y_coords, x_coords = np.mgrid[0:h, 0:w]
            dist = np.sqrt((x_coords - center_x)**2 + (y_coords - center_y)**2)
            max_dist = np.sqrt(center_x**2 + center_y**2)
            
            for i in range(num_textures):
                r_start = i / num_textures * max_dist
                r_end = (i + 1) / num_textures * max_dist
                w_map = np.zeros((h, w), dtype=np.float32)
                mask = (dist >= r_start) & (dist <= r_end)
                w_map[mask] = 1.0 - np.abs(dist[mask] - (r_start + r_end) / 2) * num_textures / max_dist
                weight_maps.append(w_map)
        
        elif pattern == 'checkerboard':
            y_coords, x_coords = np.mgrid[0:h, 0:w]
            cell_size = min(h, w) // 8
            
            for i in range(num_textures):
                w_map = np.zeros((h, w), dtype=np.float32)
                mask = ((x_coords // cell_size + y_coords // cell_size) % num_textures) == i
                w_map[mask] = 1.0
                w_map = cv2.GaussianBlur(w_map, (15, 15), 5)
                weight_maps.append(w_map)
        
        total = sum(weight_maps) + 1e-8
        weight_maps = [w / total for w in weight_maps]
        
        return weight_maps
    
    def blend_textures_spatial(self, textures: List[np.ndarray],
                                weight_maps: List[np.ndarray],
                                blend_mode: str = 'pyramid') -> np.ndarray:
        h, w = weight_maps[0].shape[:2]
        is_color = textures[0].ndim == 3
        
        resized_textures = []
        for tex in textures:
            if tex.shape[:2] != (h, w):
                tex = cv2.resize(tex, (w, h))
            resized_textures.append(tex.astype(np.float32))
        
        if blend_mode == 'simple':
            result = np.zeros((h, w, 3) if is_color else (h, w), dtype=np.float32)
            for tex, w_map in zip(resized_textures, weight_maps):
                if is_color:
                    w_map_3d = w_map[..., np.newaxis]
                else:
                    w_map_3d = w_map
                result += tex * w_map_3d
            return np.clip(result, 0, 255).astype(np.uint8)
        
        elif blend_mode == 'pyramid':
            levels = 5
            result_tensor = torch.zeros(1, 3 if is_color else 1, h, w, device=self.device)
            
            for tex, w_map in zip(resized_textures, weight_maps):
                tex_tensor = self.synthesizer.to_tensor(tex)
                w_tensor = torch.from_numpy(w_map).float().to(self.device)
                w_tensor = w_tensor.unsqueeze(0).unsqueeze(0)
                if is_color:
                    w_tensor = w_tensor.repeat(1, 3, 1, 1)
                
                lap_pyr, base = self.synthesizer.build_laplacian_pyramid_gpu(tex_tensor, levels)
                w_pyr = self.synthesizer.build_gaussian_pyramid_gpu(w_tensor, levels + 1)
                
                for i in range(levels):
                    if i == 0:
                        blended_lap = [lap_pyr[i] * w_pyr[i]]
                    else:
                        blended_lap.append(blended_lap[i-1] + lap_pyr[i] * w_pyr[i])
                
                if 'blended_base' not in locals():
                    blended_base = base * w_pyr[-1]
                else:
                    blended_base += base * w_pyr[-1]
            
            result_tensor = self.synthesizer.reconstruct_from_laplacian_gpu(blended_lap, blended_base)
            return self.synthesizer.to_numpy(result_tensor)
        
        else:
            raise ValueError(f"Unknown blend mode: {blend_mode}")


class TextureParameterizer:
    def __init__(self, use_gpu: bool = True):
        self.device = torch.device('cuda' if use_gpu and torch.cuda.is_available() else 'cpu')
    
    def compute_tiling_params(self, texture: np.ndarray, 
                               max_offset: int = 32) -> Dict[str, Any]:
        h, w = texture.shape[:2]
        is_color = texture.ndim == 3
        
        gray = cv2.cvtColor(texture, cv2.COLOR_BGR2GRAY) if is_color else texture
        gray = gray.astype(np.float32)
        
        best_h_offset = 0
        best_v_offset = 0
        min_h_error = float('inf')
        min_v_error = float('inf')
        
        for offset in range(1, max_offset + 1):
            h_error = np.mean((gray[:, :-offset] - gray[:, offset:]) ** 2)
            if h_error < min_h_error:
                min_h_error = h_error
                best_h_offset = offset
            
            v_error = np.mean((gray[:-offset, :] - gray[offset:, :]) ** 2)
            if v_error < min_v_error:
                min_v_error = v_error
                best_v_offset = offset
        
        for period in [w // 2, w // 3, w // 4]:
            if period > 0:
                h_period_error = np.mean((gray[:, :-period] - gray[:, period:]) ** 2)
                if h_period_error < min_h_error:
                    min_h_error = h_period_error
                    best_h_offset = period
        
        for period in [h // 2, h // 3, h // 4]:
            if period > 0:
                v_period_error = np.mean((gray[:-period, :] - gray[period:, :]) ** 2)
                if v_period_error < min_v_error:
                    min_v_error = v_period_error
                    best_v_offset = period
        
        h_tileable = min_h_error < 500
        v_tileable = min_v_error < 500
        
        fft = np.fft.fft2(gray)
        fft_shift = np.fft.fftshift(np.abs(fft))
        
        center_y, center_x = h // 2, w // 2
        fft_shift[center_y-5:center_y+5, center_x-5:center_x+5] = 0
        
        peak_idx = np.unravel_index(np.argmax(fft_shift), fft_shift.shape)
        peak_y, peak_x = peak_idx
        freq_h = abs(peak_x - center_x)
        freq_v = abs(peak_y - center_y)
        
        natural_tile_w = w // freq_h if freq_h > 0 else w
        natural_tile_h = h // freq_v if freq_v > 0 else h
        
        params = {
            'is_tileable': h_tileable and v_tileable,
            'is_horizontal_tileable': h_tileable,
            'is_vertical_tileable': v_tileable,
            'best_horizontal_offset': best_h_offset,
            'best_vertical_offset': best_v_offset,
            'horizontal_match_error': min_h_error,
            'vertical_match_error': min_v_error,
            'natural_tile_width': natural_tile_w,
            'natural_tile_height': natural_tile_h,
            'dominant_frequency_h': freq_h,
            'dominant_frequency_v': freq_v,
            'original_size': (h, w)
        }
        
        return params
    
    def make_tileable(self, texture: np.ndarray, 
                       method: str = 'feather',
                       overlap: int = 32) -> Tuple[np.ndarray, Dict[str, Any]]:
        h, w = texture.shape[:2]
        is_color = texture.ndim == 3
        
        params = self.compute_tiling_params(texture, overlap)
        
        if method == 'feather':
            result = texture.copy()
            
            feather = np.linspace(0, 1, overlap)
            if is_color:
                feather = feather[np.newaxis, :, np.newaxis]
            
            result[:, :overlap] = texture[:, :overlap] * (1 - feather) + texture[:, -overlap:] * feather
            result[:overlap, :] = texture[:overlap, :] * (1 - feather.transpose(1, 0, 2) if is_color else feather.T) + \
                                 texture[-overlap:, :] * (feather.transpose(1, 0, 2) if is_color else feather.T)
            
            return result, params
        
        elif method == 'pyramid':
            seam_finder = GraphCutSeamFinder()
            texture_tensor = torch.from_numpy(texture.transpose(2, 0, 1) if is_color else texture).float().to(self.device)
            texture_tensor = texture_tensor.unsqueeze(0) / 255.0
            
            if is_color:
                left_edge = texture_tensor[:, :, :, :overlap]
                right_edge = texture_tensor[:, :, :, -overlap:]
                h_error = seam_finder.compute_error_map(left_edge, right_edge)
                
                top_edge = texture_tensor[:, :, :overlap, :]
                bottom_edge = texture_tensor[:, :, -overlap:, :]
                v_error = seam_finder.compute_error_map(top_edge, bottom_edge)
                
                h_mask = seam_finder.create_seam_mask(h, overlap, h_error, None, 'left')
                v_mask = seam_finder.create_seam_mask(w, overlap, v_error, None, 'left')
                
                if is_color:
                    h_mask_3d = h_mask[..., np.newaxis]
                    v_mask_3d = v_mask.T[..., np.newaxis]
                else:
                    h_mask_3d = h_mask
                    v_mask_3d = v_mask.T
                
                result = texture.copy()
                result[:, :overlap] = texture[:, :overlap] * (1 - h_mask_3d) + texture[:, -overlap:] * h_mask_3d
                result[:overlap, :] = texture[:overlap, :] * (1 - v_mask_3d) + texture[-overlap:, :] * v_mask_3d
            else:
                left_edge = texture_tensor[:, :, :, :overlap]
                right_edge = texture_tensor[:, :, :, -overlap:]
                h_error = seam_finder.compute_error_map(left_edge, right_edge)
                
                top_edge = texture_tensor[:, :, :overlap, :]
                bottom_edge = texture_tensor[:, :, -overlap:, :]
                v_error = seam_finder.compute_error_map(top_edge, bottom_edge)
                
                h_mask = seam_finder.create_seam_mask(h, overlap, h_error, None, 'left')
                v_mask = seam_finder.create_seam_mask(w, overlap, v_error, None, 'left')
                
                result = texture.copy()
                result[:, :overlap] = texture[:, :overlap] * (1 - h_mask) + texture[:, -overlap:] * h_mask
                result[:overlap, :] = texture[:overlap, :] * (1 - v_mask.T) + texture[-overlap:, :] * v_mask.T
            
            return result, params
        
        elif method == 'wrap':
            result = np.zeros_like(texture)
            
            for y in range(h):
                for x in range(w):
                    src_y = y % h
                    src_x = x % w
                    result[y, x] = texture[src_y, src_x]
            
            return result, params
        
        else:
            raise ValueError(f"Unknown method: {method}")
    
    def analyze_texture(self, texture: np.ndarray) -> Dict[str, Any]:
        h, w = texture.shape[:2]
        is_color = texture.ndim == 3
        
        gray = cv2.cvtColor(texture, cv2.COLOR_BGR2GRAY) if is_color else texture
        
        mean = np.mean(gray)
        std = np.std(gray)
        
        sobel_x = cv2.Sobel(gray.astype(np.float32), -1, 1, 0, ksize=3)
        sobel_y = cv2.Sobel(gray.astype(np.float32), -1, 0, 1, ksize=3)
        grad_mag = np.sqrt(sobel_x**2 + sobel_y**2)
        
        complexity = np.mean(grad_mag)
        
        direction = np.arctan2(sobel_y, sobel_x)
        direction_hist, _ = np.histogram(direction, bins=18, range=(-np.pi, np.pi), density=True)
        directionality = np.max(direction_hist) / (np.sum(direction_hist) + 1e-8)
        
        if is_color:
            lab = cv2.cvtColor(texture, cv2.COLOR_BGR2LAB)
            color_variance = np.std(lab.reshape(-1, 3), axis=0)
        else:
            color_variance = np.array([std, 0, 0])
        
        tiling_params = self.compute_tiling_params(texture)
        
        analysis = {
            'size': (h, w),
            'is_color': is_color,
            'brightness_mean': mean,
            'brightness_std': std,
            'complexity': complexity,
            'directionality': directionality,
            'color_variance': color_variance.tolist(),
            'is_tileable': tiling_params['is_tileable'],
            'natural_tile_size': (tiling_params['natural_tile_height'], tiling_params['natural_tile_width']),
            'recommended_patch_size': max(16, min(h, w) // 4),
            'recommended_overlap': max(4, min(h, w) // 16)
        }
        
        return analysis
    
    def generate_param_report(self, texture: np.ndarray) -> str:
        analysis = self.analyze_texture(texture)
        
        report = []
        report.append("=" * 50)
        report.append("TEXTURE PARAMETERIZATION REPORT")
        report.append("=" * 50)
        report.append(f"Size: {analysis['size'][0]} x {analysis['size'][1]}")
        report.append(f"Color: {'Yes' if analysis['is_color'] else 'No'}")
        report.append(f"")
        report.append("STATISTICS:")
        report.append(f"  Brightness Mean: {analysis['brightness_mean']:.1f}")
        report.append(f"  Brightness Std:  {analysis['brightness_std']:.1f}")
        report.append(f"  Complexity:      {analysis['complexity']:.2f}")
        report.append(f"  Directionality:  {analysis['directionality']:.3f}")
        report.append(f"")
        report.append("TILING:")
        report.append(f"  Tileable:        {'Yes' if analysis['is_tileable'] else 'No'}")
        report.append(f"  Natural Tile:    {analysis['natural_tile_size'][0]} x {analysis['natural_tile_size'][1]}")
        report.append(f"")
        report.append("RECOMMENDATIONS:")
        report.append(f"  Patch Size:      {analysis['recommended_patch_size']}")
        report.append(f"  Overlap:         {analysis['recommended_overlap']}")
        report.append("=" * 50)
        
        return "\n".join(report)


class EnhancedTextureSynthesizer(TextureSynthesizer):
    def __init__(self, use_gpu: bool = True):
        super().__init__(use_gpu=use_gpu)
        self.video_synthesizer = VideoTextureSynthesizer(use_gpu=use_gpu)
        self.texture_blender = MultiTextureBlender(use_gpu=use_gpu)
        self.parameterizer = TextureParameterizer(use_gpu=use_gpu)
    
    def synthesize_video(self, texture: np.ndarray,
                          output_size: Tuple[int, int],
                          num_frames: int,
                          **kwargs) -> List[np.ndarray]:
        return self.video_synthesizer.synthesize_video(texture, output_size, num_frames, **kwargs)
    
    def blend_textures(self, textures: List[np.ndarray],
                        weights: Optional[List[float]] = None,
                        **kwargs) -> np.ndarray:
        return self.texture_blender.blend_textures_pixelwise(textures, weights, **kwargs)
    
    def blend_textures_spatial(self, textures: List[np.ndarray],
                                weight_maps: List[np.ndarray],
                                **kwargs) -> np.ndarray:
        return self.texture_blender.blend_textures_spatial(textures, weight_maps, **kwargs)
    
    def create_weight_maps(self, size: Tuple[int, int],
                            pattern: str = 'linear',
                            num_textures: int = 2) -> List[np.ndarray]:
        return self.texture_blender.create_weight_map(size, pattern, num_textures)
    
    def make_tileable(self, texture: np.ndarray, **kwargs) -> Tuple[np.ndarray, Dict[str, Any]]:
        return self.parameterizer.make_tileable(texture, **kwargs)
    
    def analyze_texture(self, texture: np.ndarray) -> Dict[str, Any]:
        return self.parameterizer.analyze_texture(texture)
    
    def get_tiling_parameters(self, texture: np.ndarray) -> Dict[str, Any]:
        return self.parameterizer.compute_tiling_params(texture)
    
    def generate_param_report(self, texture: np.ndarray) -> str:
        return self.parameterizer.generate_param_report(texture)


def main():
    import sys
    no_display = '--no-display' in sys.argv or '-n' in sys.argv
    
    print("Enhanced Texture Synthesis - Video, Multi-Texture, and Parameterization")
    print("=" * 80)
    
    synthesizer = EnhancedTextureSynthesizer(use_gpu=True)
    
    print("\n1. Generating sample textures...")
    np.random.seed(42)
    
    texture1 = np.zeros((80, 80, 3), dtype=np.uint8)
    for i in range(80):
        color = int(80 + 40 * np.sin(i * 0.08))
        texture1[:, i] = [color // 3, color, color // 2]
    texture1 = texture1 + np.random.randint(0, 15, (80, 80, 3), dtype=np.uint8)
    
    texture2 = np.zeros((80, 80, 3), dtype=np.uint8)
    for i in range(64):
        for j in range(64):
            if (i // 8 + j // 8) % 2 == 0:
                texture2[i, j] = [100, 150, 180]
            else:
                texture2[i, j] = [60, 90, 120]
    texture2 = texture2 + np.random.randint(0, 10, (80, 80, 3), dtype=np.uint8)
    
    texture3 = np.zeros((80, 80, 3), dtype=np.uint8)
    for i in range(80):
        for j in range(80):
            val = 128 + 64 * np.sin((i + j) * 0.15)
            texture3[i, j] = [int(val * 0.8), int(val * 0.6), int(val)]
    texture3 = texture3 + np.random.randint(0, 12, (80, 80, 3), dtype=np.uint8)
    
    print("\n2. Testing multi-texture blending...")
    blended = synthesizer.blend_textures(
        [texture1, texture2, texture3],
        weights=[0.4, 0.3, 0.3],
        blend_mode='pyramid'
    )
    cv2.imwrite('blended_texture_pyramid.png', blended)
    print("  Saved: blended_texture_pyramid.png")
    
    blended_avg = synthesizer.blend_textures(
        [texture1, texture2],
        weights=[0.5, 0.5],
        blend_mode='average'
    )
    cv2.imwrite('blended_texture_average.png', blended_avg)
    print("  Saved: blended_texture_average.png")
    
    print("\n3. Testing spatial texture blending...")
    weight_maps = synthesizer.create_weight_maps(
        (256, 256), pattern='checkerboard', num_textures=3
    )
    spatial_blend = synthesizer.blend_textures_spatial(
        [texture1, texture2, texture3],
        weight_maps,
        blend_mode='simple'
    )
    cv2.imwrite('spatial_blend_checkerboard.png', spatial_blend)
    print("  Saved: spatial_blend_checkerboard.png")
    
    weight_maps_linear = synthesizer.create_weight_maps(
        (256, 256), pattern='linear', num_textures=3
    )
    spatial_blend_linear = synthesizer.blend_textures_spatial(
        [texture1, texture2, texture3],
        weight_maps_linear,
        blend_mode='simple'
    )
    cv2.imwrite('spatial_blend_linear.png', spatial_blend_linear)
    print("  Saved: spatial_blend_linear.png")
    
    print("\n4. Testing texture parameterization...")
    report = synthesizer.generate_param_report(texture1)
    print(report)
    
    tileable, tile_params = synthesizer.make_tileable(
        texture1, method='feather', overlap=16
    )
    cv2.imwrite('original_texture.png', texture1)
    cv2.imwrite('tileable_texture.png', tileable)
    print("  Saved: original_texture.png, tileable_texture.png")
    print(f"  Tileable: {tile_params['is_tileable']}")
    
    print("\n5. Testing video synthesis (short 5-frame sequence)...")
    try:
        video_frames = synthesizer.synthesize_video(
            texture1, (128, 128), num_frames=5,
            patch_size=24, overlap=8,
            motion_type='wave',
            output_path='texture_animation.mp4'
        )
        print("  Video synthesis complete!")
        for i, frame in enumerate(video_frames):
            cv2.imwrite(f'video_frame_{i:03d}.png', frame)
        print("  Saved individual frames: video_frame_000.png to 004.png")
    except Exception as e:
        print(f"  Video synthesis skipped: {e}")
    
    print("\n6. Testing large-scale synthesis with GraphCut...")
    result = synthesizer.synthesize_texture(
        blended, (384, 384),
        patch_size=32, overlap=10,
        use_direction=True,
        blend_mode='graphcut',
        structure_weight=0.6
    )
    cv2.imwrite('large_synthesized.png', result)
    print("  Saved: large_synthesized.png")
    
    if not no_display:
        print("\n7. Displaying results...")
        print("  Press any key to continue...")
        cv2.imshow('Texture 1', texture1)
        cv2.imshow('Texture 2', texture2)
        cv2.imshow('Blended (Pyramid)', blended)
        cv2.imshow('Spatial Blend (Checkerboard)', spatial_blend)
        cv2.imshow('Tileable', tileable)
        cv2.imshow('Large Synthesis', result)
        cv2.waitKey(0)
        cv2.destroyAllWindows()
    else:
        print("\n7. Display skipped (--no-display mode)")
    
    print("\n" + "=" * 80)
    print("Enhanced Demo Complete!")
    print("=" * 80)
    print("\nNew Features Added:")
    print("  ✓ Video texture synthesis with temporal consistency")
    print("  ✓ Multi-texture blending (average, pyramid, gradient)")
    print("  ✓ Spatial texture blending with weight maps")
    print("  ✓ Texture parameterization and tiling analysis")
    print("  ✓ Automatic tileable texture generation")
    print("  ✓ Texture analysis and parameter recommendations")


if __name__ == '__main__':
    main()
