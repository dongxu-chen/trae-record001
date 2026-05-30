import numpy as np
import cv2
from typing import Tuple, Optional, Callable
from scipy.ndimage import map_coordinates


class LightFieldRefocus:
    def __init__(self, lf_data: np.ndarray, focal_depth_range: Tuple[float, float] = (-5.0, 5.0)):
        self.lf_data = lf_data
        self.num_views_y, self.num_views_x = lf_data.shape[0], lf_data.shape[1]
        self.img_h, self.img_w = lf_data.shape[2], lf_data.shape[3]
        self.focal_depth_range = focal_depth_range
        self.center_vy = self.num_views_y // 2
        self.center_vx = self.num_views_x // 2
        self._saturation_threshold = 250.0
        self._consistency_sigma = 30.0
        
    def _compute_highlight_mask(self, view: np.ndarray) -> np.ndarray:
        max_ch = np.max(view, axis=-1)
        return (max_ch >= self._saturation_threshold).astype(np.float32)
    
    def _compute_adaptive_weight_map(self, shifted: np.ndarray, 
                                      center_ref: np.ndarray,
                                      aperture_weight: float) -> np.ndarray:
        h, w = shifted.shape[:2]
        
        sat_mask = self._compute_highlight_mask(shifted)
        sat_penalty = 1.0 - sat_mask * 0.85
        
        if center_ref is not None:
            diff = np.abs(shifted - center_ref)
            color_diff = np.mean(diff, axis=-1)
            consistency = np.exp(-color_diff ** 2 / (2 * self._consistency_sigma ** 2))
            consistency = np.clip(consistency, 0.1, 1.0)
        else:
            consistency = np.ones((h, w), dtype=np.float32)
        
        max_ch = np.max(shifted, axis=-1)
        brightness_factor = 1.0 - 0.3 * np.clip((max_ch - 200.0) / 55.0, 0, 1)
        
        weight_map = aperture_weight * sat_penalty * consistency * brightness_factor
        
        return weight_map
    
    def refocus(self, alpha: float, 
                aperture_size: float = 1.0,
                interpolation: str = 'bilinear',
                adaptive_weight: bool = True) -> np.ndarray:
        alpha = np.clip(alpha, self.focal_depth_range[0], self.focal_depth_range[1])
        
        result = np.zeros((self.img_h, self.img_w, 3), dtype=np.float32)
        weight_sum = np.zeros((self.img_h, self.img_w), dtype=np.float32)
        
        radius = int(min(self.num_views_x, self.num_views_y) // 2 * aperture_size)
        
        center_view = self.lf_data[self.center_vy, self.center_vx].astype(np.float32)
        center_ref = None
        
        if adaptive_weight:
            center_ref = center_view
        
        for vy in range(self.num_views_y):
            for vx in range(self.num_views_x):
                du = vx - self.center_vx
                dv = vy - self.center_vy
                
                if abs(du) > radius or abs(dv) > radius:
                    continue
                
                ap_weight = self._aperture_weight(du, dv, radius)
                if ap_weight <= 0:
                    continue
                
                shift_x = du * alpha
                shift_y = dv * alpha
                
                shifted = self._shift_image(self.lf_data[vy, vx], shift_x, shift_y, interpolation)
                
                if adaptive_weight:
                    w_map = self._compute_adaptive_weight_map(shifted, center_ref, ap_weight)
                    result += shifted * w_map[:, :, np.newaxis]
                    weight_sum += w_map
                else:
                    result += shifted * ap_weight
                    weight_sum += ap_weight
        
        weight_sum[weight_sum == 0] = 1
        result = result / weight_sum[:, :, np.newaxis]
        
        return np.clip(result, 0, 255).astype(np.uint8)
    
    def _shift_image(self, image: np.ndarray, 
                      shift_x: float, shift_y: float,
                      interpolation: str = 'bilinear') -> np.ndarray:
        h, w = image.shape[:2]
        
        x_coords, y_coords = np.meshgrid(np.arange(w), np.arange(h))
        
        x_shifted = x_coords - shift_x
        y_shifted = y_coords - shift_y
        
        x_shifted = np.clip(x_shifted, 0, w - 1)
        y_shifted = np.clip(y_shifted, 0, h - 1)
        
        if interpolation == 'bilinear':
            x0 = np.floor(x_shifted).astype(np.int32)
            x1 = x0 + 1
            y0 = np.floor(y_shifted).astype(np.int32)
            y1 = y0 + 1
            
            x1 = np.clip(x1, 0, w - 1)
            y1 = np.clip(y1, 0, h - 1)
            
            fx = x_shifted - x0
            fy = y_shifted - y0
            
            if len(image.shape) == 3:
                fx = fx[:, :, np.newaxis]
                fy = fy[:, :, np.newaxis]
            
            result = (image[y0, x0] * (1 - fx) * (1 - fy) +
                     image[y0, x1] * fx * (1 - fy) +
                     image[y1, x0] * (1 - fx) * fy +
                     image[y1, x1] * fx * fy)
        else:
            x_int = np.round(x_shifted).astype(np.int32)
            y_int = np.round(y_shifted).astype(np.int32)
            result = image[y_int, x_int]
        
        return result.astype(np.float32)
    
    def _aperture_weight(self, du: int, dv: int, radius: int) -> float:
        dist = np.sqrt(du ** 2 + dv ** 2)
        if dist > radius:
            return 0.0
        return 1.0 - (dist / radius) ** 2
    
    def refocus_fast(self, alpha: float, aperture_size: float = 1.0,
                      adaptive_weight: bool = True) -> np.ndarray:
        alpha = np.clip(alpha, self.focal_depth_range[0], self.focal_depth_range[1])
        
        result = np.zeros((self.img_h, self.img_w, 3), dtype=np.float32)
        weight_sum = np.zeros((self.img_h, self.img_w), dtype=np.float32)
        
        radius = int(min(self.num_views_x, self.num_views_y) // 2 * aperture_size)
        
        vy_coords = np.arange(self.num_views_y) - self.center_vy
        vx_coords = np.arange(self.num_views_x) - self.center_vx
        
        center_ref = None
        if adaptive_weight:
            center_ref = self.lf_data[self.center_vy, self.center_vx].astype(np.float32)
        
        for vy, dy in enumerate(vy_coords):
            for vx, dx in enumerate(vx_coords):
                if abs(dx) > radius or abs(dy) > radius:
                    continue
                
                ap_weight = self._aperture_weight(dx, dy, radius)
                if ap_weight <= 0:
                    continue
                
                M = np.float32([[1, 0, dx * alpha], [0, 1, dy * alpha]])
                shifted = cv2.warpAffine(
                    self.lf_data[vy, vx].astype(np.float32), 
                    M, (self.img_w, self.img_h),
                    flags=cv2.INTER_LINEAR,
                    borderMode=cv2.BORDER_CONSTANT
                )
                
                if adaptive_weight and center_ref is not None:
                    w_map = self._compute_adaptive_weight_map(shifted, center_ref, ap_weight)
                    result += shifted * w_map[:, :, np.newaxis]
                    weight_sum += w_map
                else:
                    result += shifted * ap_weight
                    weight_sum += ap_weight
        
        weight_sum[weight_sum == 0] = 1
        result = result / weight_sum[:, :, np.newaxis]
        
        return np.clip(result, 0, 255).astype(np.uint8)
    
    def focus_stack(self, num_planes: int = 10, 
                     aperture_size: float = 1.0) -> np.ndarray:
        alphas = np.linspace(self.focal_depth_range[0], self.focal_depth_range[1], num_planes)
        stack = []
        
        for alpha in alphas:
            focused = self.refocus_fast(alpha, aperture_size)
            stack.append(focused)
        
        return np.array(stack)
    
    def all_in_focus(self, focus_stack: Optional[np.ndarray] = None,
                      num_planes: int = 10) -> Tuple[np.ndarray, np.ndarray]:
        if focus_stack is None:
            focus_stack = self.focus_stack(num_planes)
        
        focus_measure = self._compute_focus_measure(focus_stack)
        
        best_idx = np.argmax(focus_measure, axis=0)
        
        h, w = focus_stack.shape[1:3]
        all_focus = np.zeros((h, w, 3), dtype=np.uint8)
        
        for i in range(focus_stack.shape[0]):
            mask = (best_idx == i)
            all_focus[mask] = focus_stack[i, mask]
        
        depth_map = best_idx.astype(np.float32) / (num_planes - 1)
        
        return all_focus, depth_map
    
    def _compute_focus_measure(self, stack: np.ndarray) -> np.ndarray:
        num_planes, h, w = stack.shape[:3]
        focus_measure = np.zeros((num_planes, h, w), dtype=np.float32)
        
        for i in range(num_planes):
            gray = cv2.cvtColor(stack[i], cv2.COLOR_BGR2GRAY)
            laplacian = cv2.Laplacian(gray, cv2.CV_32F)
            focus_measure[i] = np.abs(laplacian)
            
            focus_measure[i] = cv2.GaussianBlur(focus_measure[i], (5, 5), 0)
        
        return focus_measure
    
    def refocus_with_depth(self, target_depth: float,
                            depth_map: np.ndarray,
                            aperture_size: float = 1.0,
                            adaptive_weight: bool = True) -> np.ndarray:
        result = np.zeros((self.img_h, self.img_w, 3), dtype=np.float32)
        weight_sum = np.zeros((self.img_h, self.img_w), dtype=np.float32)
        
        radius = int(min(self.num_views_x, self.num_views_y) // 2 * aperture_size)
        
        center_ref = None
        if adaptive_weight:
            center_ref = self.lf_data[self.center_vy, self.center_vx].astype(np.float32)
        
        for vy in range(self.num_views_y):
            for vx in range(self.num_views_x):
                du = vx - self.center_vx
                dv = vy - self.center_vy
                
                if abs(du) > radius or abs(dv) > radius:
                    continue
                
                ap_weight = self._aperture_weight(du, dv, radius)
                if ap_weight <= 0:
                    continue
                
                alpha_map = (depth_map - target_depth) * 10.0
                
                shift_x = du * alpha_map
                shift_y = dv * alpha_map
                
                shifted = self._shift_image_per_pixel(self.lf_data[vy, vx], shift_x, shift_y)
                
                if adaptive_weight and center_ref is not None:
                    center_shifted_x = self._shift_image_per_pixel(
                        self.lf_data[self.center_vy, self.center_vx], 
                        np.zeros_like(shift_x), np.zeros_like(shift_y)
                    )
                    w_map = self._compute_adaptive_weight_map(shifted, center_shifted_x, ap_weight)
                    result += shifted * w_map[:, :, np.newaxis]
                    weight_sum += w_map
                else:
                    result += shifted * ap_weight
                    weight_sum += ap_weight
        
        weight_sum[weight_sum == 0] = 1
        result = result / weight_sum[:, :, np.newaxis]
        
        return np.clip(result, 0, 255).astype(np.uint8)
    
    def _shift_image_per_pixel(self, image: np.ndarray,
                                shift_x: np.ndarray,
                                shift_y: np.ndarray) -> np.ndarray:
        h, w = image.shape[:2]
        
        x_coords, y_coords = np.meshgrid(np.arange(w), np.arange(h))
        
        x_shifted = x_coords - shift_x
        y_shifted = y_coords - shift_y
        
        x_shifted = np.clip(x_shifted, 0, w - 1)
        y_shifted = np.clip(y_shifted, 0, h - 1)
        
        x0 = np.floor(x_shifted).astype(np.int32)
        x1 = x0 + 1
        y0 = np.floor(y_shifted).astype(np.int32)
        y1 = y0 + 1
        
        x1 = np.clip(x1, 0, w - 1)
        y1 = np.clip(y1, 0, h - 1)
        
        fx = x_shifted - x0
        fy = y_shifted - y0
        
        fx = fx[:, :, np.newaxis]
        fy = fy[:, :, np.newaxis]
        
        result = (image[y0, x0] * (1 - fx) * (1 - fy) +
                 image[y0, x1] * fx * (1 - fy) +
                 image[y1, x0] * (1 - fx) * fy +
                 image[y1, x1] * fx * fy)
        
        return result.astype(np.float32)
    
    def get_disparity_map(self, method: str = 'block_matching') -> np.ndarray:
        center_view = self.lf_data[self.center_vy, self.center_vx]
        left_view = self.lf_data[self.center_vy, max(0, self.center_vx - 2)]
        right_view = self.lf_data[self.center_vy, min(self.num_views_x - 1, self.center_vx + 2)]
        
        if method == 'block_matching':
            disparity = self._stereo_block_matching(left_view, right_view)
        else:
            disparity = self._phase_correlation_disparity()
        
        return disparity
    
    def _stereo_block_matching(self, left: np.ndarray, right: np.ndarray,
                                block_size: int = 15,
                                max_disparity: int = 64) -> np.ndarray:
        left_gray = cv2.cvtColor(left, cv2.COLOR_BGR2GRAY)
        right_gray = cv2.cvtColor(right, cv2.COLOR_BGR2GRAY)
        
        stereo = cv2.StereoBM_create(numDisparities=max_disparity, blockSize=block_size)
        disparity = stereo.compute(left_gray, right_gray).astype(np.float32) / 16.0
        
        disparity = cv2.medianBlur(disparity, 5)
        
        return disparity
    
    def _phase_correlation_disparity(self) -> np.ndarray:
        disparity = np.zeros((self.img_h, self.img_w), dtype=np.float32)
        center_view = self.lf_data[self.center_vy, self.center_vx]
        
        for vy in range(self.num_views_y):
            for vx in range(self.num_views_x):
                if vy == self.center_vy and vx == self.center_vx:
                    continue
                
                dx = vx - self.center_vx
                dy = vy - self.center_vy
                
                if dx == 0 and dy == 0:
                    continue
                
                view = self.lf_data[vy, vx]
                flow = cv2.calcOpticalFlowFarneback(
                    cv2.cvtColor(center_view, cv2.COLOR_BGR2GRAY),
                    cv2.cvtColor(view, cv2.COLOR_BGR2GRAY),
                    None, 0.5, 3, 15, 3, 5, 1.2, 0
                )
                
                disp = np.sqrt(flow[..., 0] ** 2 + flow[..., 1] ** 2)
                disparity += disp / np.sqrt(dx ** 2 + dy ** 2)
        
        disparity /= (self.num_views_x * self.num_views_y - 1)
        
        return disparity
    
    def synthetic_aperture(self, center_point: Tuple[int, int],
                            window_size: int = 5) -> np.ndarray:
        cx, cy = center_point
        
        result = np.zeros_like(self.lf_data[0, 0], dtype=np.float32)
        weight_sum = 0
        
        for vy in range(self.num_views_y):
            for vx in range(self.num_views_x):
                du = vx - self.center_vx
                dv = vy - self.center_vy
                
                sample_x = cx + du * window_size
                sample_y = cy + dv * window_size
                
                if 0 <= sample_x < self.img_w and 0 <= sample_y < self.img_h:
                    result += self.lf_data[vy, vx].astype(np.float32)
                    weight_sum += 1
        
        if weight_sum > 0:
            result /= weight_sum
        
        return np.clip(result, 0, 255).astype(np.uint8)


class ShearTransformRefocus:
    def __init__(self, lf_data: np.ndarray):
        self.lf_data = lf_data
        self.num_views_y, self.num_views_x = lf_data.shape[:2]
        self.h, self.w = lf_data.shape[2:4]
        
    def refocus(self, alpha: float) -> np.ndarray:
        lf_4d = self.lf_data.transpose(0, 1, 2, 3, 4)
        
        result = np.zeros((self.h, self.w, 3), dtype=np.float32)
        
        for vy in range(self.num_views_y):
            for vx in range(self.num_views_x):
                u = vx - self.num_views_x // 2
                v = vy - self.num_views_y // 2
                
                shifted = np.roll(self.lf_data[vy, vx], int(u * alpha), axis=1)
                shifted = np.roll(shifted, int(v * alpha), axis=0)
                
                result += shifted.astype(np.float32)
        
        result /= (self.num_views_x * self.num_views_y)
        
        return np.clip(result, 0, 255).astype(np.uint8)


class FocusTracker:
    def __init__(self, refocus_engine: LightFieldRefocus,
                 depth_map: Optional[np.ndarray] = None):
        self.refocus = refocus_engine
        self.depth_map = depth_map
        self.trackers = {}
        self._next_id = 0
        self._prev_gray = None
        self._trajectory_history = {}
    
    def add_target(self, bbox: Tuple[int, int, int, int],
                    tracker_type: str = 'csrt') -> int:
        tid = self._next_id
        self._next_id += 1
        
        center_view = self.refocus.lf_data[self.refocus.center_vy, self.refocus.center_vx]
        
        if tracker_type == 'csrt':
            tracker = cv2.TrackerCSRT_create()
        elif tracker_type == 'kcf':
            tracker = cv2.TrackerKCF_create()
        else:
            tracker = cv2.TrackerMIL_create()
        
        tracker.init(center_view, bbox)
        self.trackers[tid] = tracker
        self._trajectory_history[tid] = []
        
        return tid
    
    def add_target_point(self, point: Tuple[int, int],
                          window: int = 30,
                          tracker_type: str = 'csrt') -> int:
        x, y = point
        bbox = (x - window, y - window, window * 2, window * 2)
        return self.add_target(bbox, tracker_type)
    
    def update(self, frame: Optional[np.ndarray] = None) -> dict:
        if frame is None:
            frame = self.refocus.lf_data[self.refocus.center_vy, self.refocus.center_vx]
        
        results = {}
        
        for tid, tracker in list(self.trackers.items()):
            ok, bbox = tracker.update(frame)
            if ok:
                x, y, w, h = bbox
                cx, cy = x + w / 2, y + h / 2
                alpha = self._compute_local_alpha(frame, int(cx), int(cy), int(w), int(h))
                results[tid] = {
                    'bbox': bbox,
                    'center': (cx, cy),
                    'alpha': alpha,
                    'active': True
                }
                self._trajectory_history[tid].append((cx, cy, alpha))
            else:
                results[tid] = {'active': False}
        
        return results
    
    def _compute_local_alpha(self, frame: np.ndarray,
                              cx: int, cy: int,
                              bw: int, bh: int,
                              num_steps: int = 15) -> float:
        x1 = max(0, cx - bw // 2)
        x2 = min(frame.shape[1], cx + bw // 2)
        y1 = max(0, cy - bh // 2)
        y2 = min(frame.shape[0], cy + bh // 2)
        
        if self.depth_map is not None:
            roi = self.depth_map[y1:y2, x1:x2]
            if roi.size > 0:
                median_depth = np.median(roi)
                return median_depth * (self.refocus.focal_depth_range[1] - 
                                       self.refocus.focal_depth_range[0]) + self.refocus.focal_depth_range[0]
        
        alphas = np.linspace(self.refocus.focal_depth_range[0],
                             self.refocus.focal_depth_range[1], num_steps)
        best_alpha = 0.0
        best_sharpness = -1.0
        
        for alpha in alphas:
            img = self.refocus.refocus_fast(alpha, aperture_size=0.6)
            roi = img[y1:y2, x1:x2]
            s = evaluate_sharpness(roi)
            if s > best_sharpness:
                best_sharpness = s
                best_alpha = alpha
        
        return best_alpha
    
    def refocus_tracked(self, frame: Optional[np.ndarray] = None,
                         aperture_size: float = 1.0) -> Tuple[np.ndarray, dict]:
        tracking = self.update(frame)
        
        if not tracking:
            return self.refocus.refocus_fast(0.0, aperture_size), {}
        
        active_targets = {tid: r for tid, r in tracking.items() if r.get('active', False)}
        
        if not active_targets:
            return self.refocus.refocus_fast(0.0, aperture_size), tracking
        
        if len(active_targets) == 1:
            tid = list(active_targets.keys())[0]
            alpha = active_targets[tid]['alpha']
            result = self.refocus.refocus_fast(alpha, aperture_size)
        else:
            result = self._refocus_multi_target(active_targets, aperture_size)
        
        return result, tracking
    
    def _refocus_multi_target(self, targets: dict,
                               aperture_size: float = 1.0) -> np.ndarray:
        depth_map = np.full((self.refocus.img_h, self.refocus.img_w), 0.5, dtype=np.float32)
        
        for tid, info in targets.items():
            cx, cy = info['center']
            bw, bh = info['bbox'][2], info['bbox'][3]
            alpha_norm = (info['alpha'] - self.refocus.focal_depth_range[0]) / \
                         (self.refocus.focal_depth_range[1] - self.refocus.focal_depth_range[0] + 1e-6)
            
            x1 = max(0, int(cx - bw // 2))
            x2 = min(self.refocus.img_w, int(cx + bw // 2))
            y1 = max(0, int(cy - bh // 2))
            y2 = min(self.refocus.img_h, int(cy + bh // 2))
            
            depth_map[y1:y2, x1:x2] = alpha_norm
        
        if self.depth_map is not None:
            mask = np.ones_like(depth_map, dtype=bool)
            for tid, info in targets.items():
                cx, cy = info['center']
                bw, bh = info['bbox'][2], info['bbox'][3]
                x1 = max(0, int(cx - bw // 2))
                x2 = min(self.refocus.img_w, int(cx + bw // 2))
                y1 = max(0, int(cy - bh // 2))
                y2 = min(self.refocus.img_h, int(cy + bh // 2))
                mask[y1:y2, x1:x2] = False
            depth_map[mask] = self.depth_map[mask]
        
        result = self.refocus.refocus_with_depth(0.5, depth_map, aperture_size)
        return result
    
    def get_trajectory(self, tid: int) -> list:
        return self._trajectory_history.get(tid, [])
    
    def draw_trajectories(self, image: np.ndarray,
                           max_length: int = 50) -> np.ndarray:
        vis = image.copy()
        colors = [(0, 255, 0), (0, 0, 255), (255, 0, 0),
                  (255, 255, 0), (255, 0, 255)]
        
        for tid, history in self._trajectory_history.items():
            if not history:
                continue
            color = colors[tid % len(colors)]
            pts = history[-max_length:]
            for i in range(1, len(pts)):
                p1 = (int(pts[i-1][0]), int(pts[i-1][1]))
                p2 = (int(pts[i][0]), int(pts[i][1]))
                cv2.line(vis, p1, p2, color, 2)
        
        return vis


class AllInFocusSynthesizer:
    def __init__(self, refocus_engine: LightFieldRefocus):
        self.refocus = refocus_engine
    
    def synthesize(self, num_planes: int = 20,
                    blend_sigma: float = 2.0,
                    edge_aware: bool = True) -> Tuple[np.ndarray, np.ndarray]:
        focus_stack = self.refocus.focus_stack(num_planes, aperture_size=1.0)
        focus_measure = self.refocus._compute_focus_measure(focus_stack)
        
        if edge_aware:
            weight_map = self._compute_edge_aware_weights(focus_measure, blend_sigma)
        else:
            weight_map = self._compute_gaussian_weights(focus_measure, blend_sigma)
        
        all_focus = self._blend_focus_stack(focus_stack, weight_map)
        
        depth_map = self._extract_depth(weight_map, num_planes)
        
        return all_focus, depth_map
    
    def _compute_edge_aware_weights(self, focus_measure: np.ndarray,
                                     sigma: float) -> np.ndarray:
        num_planes, h, w = focus_measure.shape
        
        softened = np.zeros_like(focus_measure)
        for i in range(num_planes):
            softened[i] = cv2.GaussianBlur(focus_measure[i], (0, 0), sigma)
        
        max_fm = np.max(softened, axis=0, keepdims=True)
        shifted = softened - max_fm + 10.0
        
        weights = np.exp(shifted * 5.0)
        weight_sum = np.sum(weights, axis=0, keepdims=True)
        weight_sum[weight_sum == 0] = 1
        weights = weights / weight_sum
        
        return weights
    
    def _compute_gaussian_weights(self, focus_measure: np.ndarray,
                                   sigma: float) -> np.ndarray:
        num_planes, h, w = focus_measure.shape
        
        for i in range(num_planes):
            focus_measure[i] = cv2.GaussianBlur(focus_measure[i], (0, 0), sigma)
        
        best_idx = np.argmax(focus_measure, axis=0)
        weights = np.zeros_like(focus_measure)
        
        for i in range(num_planes):
            weights[i] = np.exp(-((best_idx - i) ** 2) / (2 * 1.5 ** 2))
        
        weight_sum = np.sum(weights, axis=0, keepdims=True)
        weight_sum[weight_sum == 0] = 1
        weights = weights / weight_sum
        
        return weights
    
    def _blend_focus_stack(self, focus_stack: np.ndarray,
                            weights: np.ndarray) -> np.ndarray:
        num_planes, h, w, c = focus_stack.shape
        
        result = np.zeros((h, w, c), dtype=np.float32)
        
        for i in range(num_planes):
            w3 = weights[i][:, :, np.newaxis]
            result += focus_stack[i].astype(np.float32) * w3
        
        return np.clip(result, 0, 255).astype(np.uint8)
    
    def _extract_depth(self, weights: np.ndarray,
                        num_planes: int) -> np.ndarray:
        indices = np.arange(num_planes, dtype=np.float32).reshape(-1, 1, 1)
        depth_map = np.sum(weights * indices, axis=0)
        depth_map = depth_map / (num_planes - 1)
        
        return depth_map
    
    def synthesize_multi_band(self, num_planes: int = 20,
                               num_bands: int = 4) -> Tuple[np.ndarray, np.ndarray]:
        focus_stack = self.refocus.focus_stack(num_planes, aperture_size=1.0)
        focus_measure = self.refocus._compute_focus_measure(focus_stack)
        
        all_focus = np.zeros((self.refocus.img_h, self.refocus.img_w, 3), dtype=np.float32)
        depth_map = np.zeros((self.refocus.img_h, self.refocus.img_w), dtype=np.float32)
        
        planes_per_band = num_planes // num_bands
        
        for band in range(num_bands):
            start = band * planes_per_band
            end = min(start + planes_per_band + 1, num_planes)
            
            if start >= num_planes:
                break
            
            band_fm = focus_measure[start:end]
            band_stack = focus_stack[start:end]
            
            best_local = np.argmax(band_fm, axis=0)
            band_weight = np.max(band_fm, axis=0)
            
            for li in range(end - start):
                mask = (best_local == li)
                gi = start + li
                all_focus[mask] = band_stack[li, mask].astype(np.float32)
                depth_map[mask] = gi / (num_planes - 1)
            
            band_weight = cv2.GaussianBlur(band_weight, (5, 5), 0)
        
        all_focus = np.clip(all_focus, 0, 255).astype(np.uint8)
        
        return all_focus, depth_map
    
    def synthesize_laplacian(self, num_planes: int = 15,
                              levels: int = 3) -> Tuple[np.ndarray, np.ndarray]:
        focus_stack = self.refocus.focus_stack(num_planes, aperture_size=1.0)
        focus_measure = self.refocus._compute_focus_measure(focus_stack)
        
        best_idx = np.argmax(focus_measure, axis=0)
        depth_map = best_idx.astype(np.float32) / (num_planes - 1)
        
        result = self._laplacian_blend(focus_stack, best_idx, levels)
        
        return result, depth_map
    
    def _laplacian_blend(self, focus_stack: np.ndarray,
                          best_idx: np.ndarray,
                          levels: int) -> np.ndarray:
        num_planes, h, w, c = focus_stack.shape
        
        gauss_pyramids = []
        for i in range(num_planes):
            gp = [focus_stack[i].astype(np.float32)]
            for _ in range(levels):
                gp.append(cv2.pyrDown(gp[-1]))
            gauss_pyramids.append(gp)
        
        laplacian_pyramids = []
        for i in range(num_planes):
            lp = []
            for l in range(levels):
                expanded = cv2.pyrUp(gauss_pyramids[i][l + 1],
                                      dstsize=(gauss_pyramids[i][l].shape[1],
                                               gauss_pyramids[i][l].shape[0]))
                lap = gauss_pyramids[i][l] - expanded
                lp.append(lap)
            lp.append(gauss_pyramids[i][levels])
            laplacian_pyramids.append(lp)
        
        blended_pyramid = []
        for l in range(levels + 1):
            scale = 2 ** l
            lh, lw = laplacian_pyramids[0][l].shape[:2]
            
            idx_layer = best_idx[::scale, ::scale][:lh, :lw]
            
            blended = np.zeros_like(laplacian_pyramids[0][l])
            for i in range(num_planes):
                mask = (idx_layer == i)
                mask_f = mask.astype(np.float32)
                if l < levels:
                    mask_f = cv2.GaussianBlur(mask_f, (5, 5), 1.0)
                if len(laplacian_pyramids[i][l].shape) == 3:
                    mask_f = mask_f[:, :, np.newaxis]
                blended += laplacian_pyramids[i][l] * mask_f
            
            blended_pyramid.append(blended)
        
        result = blended_pyramid[-1]
        for l in range(levels - 1, -1, -1):
            result = cv2.pyrUp(result, dstsize=(blended_pyramid[l].shape[1],
                                                  blended_pyramid[l].shape[0]))
            result += blended_pyramid[l]
        
        return np.clip(result, 0, 255).astype(np.uint8)


class DepthOfFieldExtender:
    def __init__(self, refocus_engine: LightFieldRefocus,
                 depth_map: Optional[np.ndarray] = None):
        self.refocus = refocus_engine
        self.depth_map = depth_map
    
    def extend_dof(self, target_alpha: float = 0.0,
                    depth_range: float = 0.3,
                    aperture_size: float = 1.0,
                    num_layers: int = 7) -> np.ndarray:
        if self.depth_map is None:
            from depth_estimation import DepthEstimator
            estimator = DepthEstimator(self.refocus.lf_data)
            self.depth_map = estimator.estimate_depth_focus_stack(num_planes=10)
        
        alpha_norm = (target_alpha - self.refocus.focal_depth_range[0]) / \
                     (self.refocus.focal_depth_range[1] - self.refocus.focal_depth_range[0] + 1e-6)
        
        in_focus_mask = np.exp(-((self.depth_map - alpha_norm) ** 2) / (2 * depth_range ** 2))
        
        alphas = np.linspace(
            self.refocus.focal_depth_range[0],
            self.refocus.focal_depth_range[1],
            num_layers
        )
        
        layer_weights = np.zeros((num_layers, self.refocus.img_h, self.refocus.img_w), dtype=np.float32)
        for i, alpha in enumerate(alphas):
            a_norm = (alpha - self.refocus.focal_depth_range[0]) / \
                     (self.refocus.focal_depth_range[1] - self.refocus.focal_depth_range[0] + 1e-6)
            layer_weights[i] = np.exp(-((self.depth_map - a_norm) ** 2) / (2 * (depth_range * 1.5) ** 2))
        
        weight_sum = np.sum(layer_weights, axis=0, keepdims=True)
        weight_sum[weight_sum == 0] = 1
        layer_weights = layer_weights / weight_sum
        
        result = np.zeros((self.refocus.img_h, self.refocus.img_w, 3), dtype=np.float32)
        for i, alpha in enumerate(alphas):
            focused = self.refocus.refocus_fast(alpha, aperture_size).astype(np.float32)
            result += focused * layer_weights[i][:, :, np.newaxis]
        
        return np.clip(result, 0, 255).astype(np.uint8)
    
    def shallow_dof(self, focus_depth: float = 0.5,
                     dof_width: float = 0.05,
                     aperture_size: float = 1.0,
                     aperture_shape: str = 'circular') -> np.ndarray:
        if self.depth_map is None:
            from depth_estimation import DepthEstimator
            estimator = DepthEstimator(self.refocus.lf_data)
            self.depth_map = estimator.estimate_depth_focus_stack(num_planes=10)
        
        in_focus = np.exp(-((self.depth_map - focus_depth) ** 2) / (2 * dof_width ** 2))
        
        alpha_target = focus_depth * (self.refocus.focal_depth_range[1] - 
                                       self.refocus.focal_depth_range[0]) + \
                       self.refocus.focal_depth_range[0]
        focused = self.refocus.refocus_fast(alpha_target, aperture_size).astype(np.float32)
        
        defocused = self._simulate_defocus(focused, self.depth_map, focus_depth,
                                            aperture_size, aperture_shape)
        
        result = focused * in_focus[:, :, np.newaxis] + \
                 defocused * (1 - in_focus[:, :, np.newaxis])
        
        return np.clip(result, 0, 255).astype(np.uint8)
    
    def _simulate_defocus(self, focused: np.ndarray, depth_map: np.ndarray,
                           focus_depth: float, aperture_size: float,
                           aperture_shape: str) -> np.ndarray:
        defocus_amount = np.abs(depth_map - focus_depth)
        
        max_radius = min(self.refocus.num_views_x, self.refocus.num_views_y) // 2
        defocus_radius = (defocus_amount * max_radius * aperture_size).astype(np.int32)
        defocus_radius = np.clip(defocus_radius, 0, max_radius)
        
        result = np.zeros_like(focused)
        
        radius_levels = np.unique(defocus_radius)
        for r in radius_levels:
            if r == 0:
                mask = (defocus_radius == r)
                result[mask] = focused[mask]
                continue
            
            kernel_size = 2 * r + 1
            if kernel_size % 2 == 0:
                kernel_size += 1
            
            if aperture_shape == 'circular':
                kernel = self._circular_kernel(r)
            elif aperture_shape == 'hexagonal':
                kernel = self._hexagonal_kernel(r)
            elif aperture_shape == 'star':
                kernel = self._star_kernel(r)
            else:
                kernel = self._circular_kernel(r)
            
            blurred = cv2.filter2D(focused.astype(np.float32), -1, kernel)
            
            mask = (defocus_radius == r)
            result[mask] = blurred[mask]
        
        return result
    
    def _circular_kernel(self, radius: int) -> np.ndarray:
        size = 2 * radius + 1
        kernel = np.zeros((size, size), dtype=np.float32)
        center = radius
        for y in range(size):
            for x in range(size):
                dist = np.sqrt((x - center) ** 2 + (y - center) ** 2)
                if dist <= radius:
                    kernel[y, x] = 1.0
        
        if kernel.sum() > 0:
            kernel /= kernel.sum()
        return kernel
    
    def _hexagonal_kernel(self, radius: int) -> np.ndarray:
        size = 2 * radius + 1
        kernel = np.zeros((size, size), dtype=np.float32)
        center = radius
        
        for y in range(size):
            for x in range(size):
                dx = abs(x - center)
                dy = abs(y - center)
                
                if dy <= radius and dx <= radius:
                    if dy <= radius / 2 or dx <= radius - dy:
                        kernel[y, x] = 1.0
        
        if kernel.sum() > 0:
            kernel /= kernel.sum()
        return kernel
    
    def _star_kernel(self, radius: int) -> np.ndarray:
        size = 2 * radius + 1
        kernel = np.zeros((size, size), dtype=np.float32)
        center = radius
        
        for y in range(size):
            for x in range(size):
                dx = x - center
                dy = y - center
                
                on_axis = (abs(dx) < 1 and abs(dy) <= radius) or \
                          (abs(dy) < 1 and abs(dx) <= radius)
                on_diag = abs(abs(dx) - abs(dy)) < 1 and \
                          abs(dx) <= radius
                
                if on_axis or on_diag:
                    kernel[y, x] = 1.0
        
        if kernel.sum() > 0:
            kernel /= kernel.sum()
        return kernel
    
    def bokeh_render(self, focus_depth: float = 0.5,
                      dof_width: float = 0.05,
                      aperture_shape: str = 'circular',
                      aperture_size: float = 1.0,
                      highlight_boost: float = 1.5) -> np.ndarray:
        if self.depth_map is None:
            from depth_estimation import DepthEstimator
            estimator = DepthEstimator(self.refocus.lf_data)
            self.depth_map = estimator.estimate_depth_focus_stack(num_planes=10)
        
        alpha_target = focus_depth * (self.refocus.focal_depth_range[1] - 
                                       self.refocus.focal_depth_range[0]) + \
                       self.refocus.focal_depth_range[0]
        focused = self.refocus.refocus_fast(alpha_target, aperture_size).astype(np.float32)
        
        center_view = self.refocus.lf_data[self.refocus.center_vy, self.refocus.center_vx].astype(np.float32)
        
        defocus_amount = np.abs(self.depth_map - focus_depth)
        max_radius = min(self.refocus.num_views_x, self.refocus.num_views_y) // 2
        defocus_radius = (defocus_amount * max_radius * aperture_size).astype(np.int32)
        defocus_radius = np.clip(defocus_radius, 0, max_radius)
        
        max_ch = np.max(center_view, axis=-1)
        highlight_mask = (max_ch > 200).astype(np.float32)
        highlight_factor = 1.0 + (highlight_boost - 1.0) * highlight_mask
        
        bokeh_result = np.zeros_like(center_view)
        
        radius_levels = sorted(np.unique(defocus_radius), reverse=True)
        
        for r in radius_levels:
            if r == 0:
                mask = (defocus_radius == r)
                bokeh_result[mask] = focused[mask]
                continue
            
            kernel_size = 2 * r + 1
            if kernel_size % 2 == 0:
                kernel_size += 1
            
            if aperture_shape == 'circular':
                kernel = self._circular_kernel(r)
            elif aperture_shape == 'hexagonal':
                kernel = self._hexagonal_kernel(r)
            else:
                kernel = self._star_kernel(r)
            
            blurred = cv2.filter2D(center_view, -1, kernel)
            
            boosted = blurred * highlight_factor[:, :, np.newaxis]
            boosted = np.clip(boosted, 0, 255)
            
            mask = (defocus_radius == r)
            bokeh_result[mask] = boosted[mask]
        
        in_focus = np.exp(-((self.depth_map - focus_depth) ** 2) / (2 * dof_width ** 2))
        result = focused * in_focus[:, :, np.newaxis] + \
                 bokeh_result * (1 - in_focus[:, :, np.newaxis])
        
        return np.clip(result, 0, 255).astype(np.uint8)


def evaluate_sharpness(image: np.ndarray) -> float:
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    laplacian = cv2.Laplacian(gray, cv2.CV_64F)
    return np.var(laplacian)


def auto_focus(refocus_engine: LightFieldRefocus,
                search_range: Tuple[float, float] = (-3.0, 3.0),
                num_steps: int = 20) -> Tuple[float, np.ndarray]:
    alphas = np.linspace(search_range[0], search_range[1], num_steps)
    sharpness_values = []
    
    for alpha in alphas:
        img = refocus_engine.refocus_fast(alpha)
        sharpness = evaluate_sharpness(img)
        sharpness_values.append(sharpness)
    
    best_idx = np.argmax(sharpness_values)
    best_alpha = alphas[best_idx]
    best_image = refocus_engine.refocus_fast(best_alpha)
    
    return best_alpha, best_image
