import numpy as np
from scipy import interpolate, optimize
from scipy.ndimage import gaussian_filter1d
from typing import List, Tuple, Dict, Optional
import math


class CornerDetector:
    def __init__(self, angle_threshold: float = 120.0, min_corner_distance: int = 5):
        self.angle_threshold = angle_threshold
        self.min_corner_distance = min_corner_distance
        self.window_size = 3
    
    def detect_corners(self, points: np.ndarray) -> List[int]:
        if points is None or len(points) < self.window_size * 2 + 1:
            return []
        
        corner_indices = []
        n = len(points)
        
        for i in range(self.window_size, n - self.window_size):
            angle = self._calculate_local_angle(points, i)
            
            if angle < self.angle_threshold:
                is_local_min = True
                for j in range(max(0, i - self.min_corner_distance), 
                               min(n, i + self.min_corner_distance + 1)):
                    if j != i and j >= self.window_size and j < n - self.window_size:
                        other_angle = self._calculate_local_angle(points, j)
                        if other_angle < angle:
                            is_local_min = False
                            break
                
                if is_local_min:
                    corner_indices.append(i)
        
        corner_indices = self._merge_close_corners(corner_indices, points)
        
        return corner_indices
    
    def _calculate_local_angle(self, points: np.ndarray, center_idx: int) -> float:
        prev_idx = center_idx - self.window_size
        next_idx = center_idx + self.window_size
        
        p1 = points[prev_idx]
        p2 = points[center_idx]
        p3 = points[next_idx]
        
        v1 = p1 - p2
        v2 = p3 - p2
        
        dot = np.dot(v1, v2)
        norm_v1 = np.linalg.norm(v1)
        norm_v2 = np.linalg.norm(v2)
        
        if norm_v1 == 0 or norm_v2 == 0:
            return 180.0
        
        cos_angle = dot / (norm_v1 * norm_v2)
        cos_angle = max(-1.0, min(1.0, cos_angle))
        
        angle = np.degrees(np.arccos(cos_angle))
        return angle
    
    def _merge_close_corners(self, indices: List[int], points: np.ndarray) -> List[int]:
        if len(indices) < 2:
            return indices
        
        merged = [indices[0]]
        
        for idx in indices[1:]:
            last_idx = merged[-1]
            dist = np.linalg.norm(points[idx] - points[last_idx])
            
            if dist >= self.min_corner_distance:
                merged.append(idx)
            else:
                angle1 = self._calculate_local_angle(points, last_idx)
                angle2 = self._calculate_local_angle(points, idx)
                if angle2 < angle1:
                    merged[-1] = idx
        
        return merged
    
    def get_corner_strength(self, points: np.ndarray, corner_idx: int) -> float:
        angle = self._calculate_local_angle(points, corner_idx)
        return max(0.0, 180.0 - angle)
    
    def get_corner_mask(self, points: np.ndarray, corner_indices: List[int], 
                        keep_radius: int = 2) -> np.ndarray:
        mask = np.ones(len(points), dtype=bool)
        
        for corner_idx in corner_indices:
            start = max(0, corner_idx - keep_radius)
            end = min(len(points), corner_idx + keep_radius + 1)
            mask[start:end] = False
        
        return mask


class ContourSmoother:
    def __init__(self, smooth_factor: float = 0.01):
        self.smooth_factor = smooth_factor
        self.corner_detector = CornerDetector()
    
    def gaussian_smooth(self, points: np.ndarray, sigma: float = 2.0, 
                       preserve_corners: bool = True) -> np.ndarray:
        if points is None or len(points) < 4:
            return points
        
        result = points.copy()
        
        if preserve_corners:
            corner_indices = self.corner_detector.detect_corners(points)
            if corner_indices:
                smooth_mask = self.corner_detector.get_corner_mask(points, corner_indices)
                
                points_closed = np.vstack([points, points[:3]])
                mask_closed = np.concatenate([smooth_mask, smooth_mask[:3]])
                
                smoothed_x = gaussian_filter1d(points_closed[:, 0].astype(float), sigma=sigma, mode='wrap')
                smoothed_y = gaussian_filter1d(points_closed[:, 1].astype(float), sigma=sigma, mode='wrap')
                
                smoothed = np.column_stack([smoothed_x, smoothed_y])
                
                for i in range(len(result)):
                    if smooth_mask[i]:
                        result[i] = smoothed[i]
                    else:
                        result[i] = points[i]
                
                return result[:len(points)]
        
        points_closed = np.vstack([points, points[:3]])
        
        smoothed_x = gaussian_filter1d(points_closed[:, 0].astype(float), sigma=sigma, mode='wrap')
        smoothed_y = gaussian_filter1d(points_closed[:, 1].astype(float), sigma=sigma, mode='wrap')
        
        smoothed = np.column_stack([smoothed_x, smoothed_y])
        
        return smoothed[:len(points)]
    
    def adaptive_smooth(self, points: np.ndarray, base_sigma: float = 2.0,
                       corner_sigma: float = 0.5) -> np.ndarray:
        if points is None or len(points) < 4:
            return points
        
        corner_indices = self.corner_detector.detect_corners(points)
        corner_strengths = np.zeros(len(points))
        
        for idx in corner_indices:
            strength = self.corner_detector.get_corner_strength(points, idx)
            corner_strengths[idx] = strength / 180.0
        
        sigma_field = np.full(len(points), base_sigma)
        for idx in corner_indices:
            strength = corner_strengths[idx]
            influence_radius = int(strength * 10) + 2
            for j in range(max(0, idx - influence_radius), 
                           min(len(points), idx + influence_radius + 1)):
                dist = abs(j - idx)
                if dist <= influence_radius:
                    decay = 1.0 - dist / (influence_radius + 1)
                    local_strength = strength * decay
                    sigma_field[j] = corner_sigma + (base_sigma - corner_sigma) * (1 - local_strength)
        
        result = points.copy().astype(float)
        for i in range(len(points)):
            window = int(sigma_field[i] * 3) + 1
            start = max(0, i - window)
            end = min(len(points), i + window + 1)
            
            weights = []
            for j in range(start, end):
                dist = abs(j - i)
                w = np.exp(-dist**2 / (2 * sigma_field[i]**2))
                weights.append(w)
            
            weights = np.array(weights) / sum(weights)
            result[i] = np.sum(points[start:end] * weights[:, np.newaxis], axis=0)
        
        return result
    
    def moving_average_smooth(self, points: np.ndarray, window_size: int = 5,
                             preserve_corners: bool = True) -> np.ndarray:
        if points is None or len(points) < window_size:
            return points
        
        result = points.copy()
        
        if preserve_corners:
            corner_indices = self.corner_detector.detect_corners(points)
            smooth_mask = self.corner_detector.get_corner_mask(points, corner_indices)
        else:
            smooth_mask = np.ones(len(points), dtype=bool)
        
        points_closed = np.vstack([points, points[:window_size]])
        
        kernel = np.ones(window_size) / window_size
        smoothed_x = np.convolve(points_closed[:, 0].astype(float), kernel, mode='valid')
        smoothed_y = np.convolve(points_closed[:, 1].astype(float), kernel, mode='valid')
        
        smoothed = np.column_stack([smoothed_x, smoothed_y])
        
        for i in range(len(result)):
            if smooth_mask[i]:
                result[i] = smoothed[i]
        
        return result[:len(points)]
    
    def spline_smooth(self, points: np.ndarray, s: float = 0.1,
                     preserve_corners: bool = True) -> np.ndarray:
        if points is None or len(points) < 4:
            return points
        
        if preserve_corners:
            corner_indices = self.corner_detector.detect_corners(points)
            
            if corner_indices:
                segments = []
                start_idx = 0
                
                corner_indices_sorted = sorted(corner_indices)
                
                for corner_idx in corner_indices_sorted:
                    if corner_idx - start_idx >= 3:
                        segments.append((start_idx, corner_idx))
                    start_idx = corner_idx
                
                if start_idx < len(points) - 1:
                    segments.append((start_idx, len(points)))
                
                smoothed = np.zeros_like(points, dtype=float)
                
                for start, end in segments:
                    seg_points = points[start:end]
                    if len(seg_points) >= 4:
                        tck, u = interpolate.splprep([seg_points[:, 0], seg_points[:, 1]], s=s, per=False)
                        seg_smoothed = np.array(interpolate.splev(np.linspace(0, 1, len(seg_points)), tck)).T
                        smoothed[start:end] = seg_smoothed
                    else:
                        smoothed[start:end] = seg_points
                
                for idx in corner_indices_sorted:
                    smoothed[idx] = points[idx]
                
                return smoothed
        
        t = np.linspace(0, 1, len(points))
        tck, u = interpolate.splprep([points[:, 0], points[:, 1]], s=s, per=True)
        smooth_points = np.array(interpolate.splev(np.linspace(0, 1, len(points)), tck)).T
        
        return smooth_points
    
    def reduce_points(self, points: np.ndarray, tolerance: float = 1.0,
                     preserve_corners: bool = True) -> np.ndarray:
        if points is None or len(points) < 3:
            return points
        
        corner_indices = []
        if preserve_corners:
            corner_indices = self.corner_detector.detect_corners(points)
        
        def perpendicular_distance(point, line_start, line_end):
            if np.array_equal(line_start, line_end):
                return np.linalg.norm(point - line_start)
            
            line_vec = line_end - line_start
            point_vec = point - line_start
            
            line_len = np.linalg.norm(line_vec)
            line_unitvec = line_vec / line_len
            point_vec_scaled = point_vec / line_len
            
            t = np.dot(line_unitvec, point_vec_scaled)
            t = max(0.0, min(1.0, t))
            
            nearest = line_start + t * line_vec
            return np.linalg.norm(point - nearest)
        
        def rdp_recursive(points, tolerance, forced_indices):
            if len(points) < 3:
                return points
            
            max_dist = 0.0
            index = 0
            is_forced = False
            
            for i in range(1, len(points) - 1):
                if i in forced_indices:
                    continue
                
                dist = perpendicular_distance(points[i], points[0], points[-1])
                if dist > max_dist:
                    index = i
                    max_dist = dist
            
            for i in forced_indices:
                if 0 < i < len(points) - 1:
                    dist = perpendicular_distance(points[i], points[0], points[-1])
                    if dist >= 0:
                        index = i
                        max_dist = max(max_dist, dist + tolerance)
                        is_forced = True
            
            if max_dist > tolerance or is_forced:
                left_forced = [i for i in forced_indices if i <= index]
                right_forced = [i - index for i in forced_indices if i >= index]
                
                left = rdp_recursive(points[:index + 1], tolerance, left_forced)
                right = rdp_recursive(points[index:], tolerance, right_forced)
                return np.vstack([left[:-1], right])
            else:
                return np.array([points[0], points[-1]])
        
        return rdp_recursive(points, tolerance, corner_indices)
    
    def remove_duplicates(self, points: np.ndarray, min_distance: float = 1.0) -> np.ndarray:
        if points is None or len(points) < 2:
            return points
        
        result = [points[0]]
        
        for point in points[1:]:
            last = result[-1]
            dist = np.linalg.norm(point - last)
            if dist >= min_distance:
                result.append(point)
        
        return np.array(result)


class IterativeBezierFitter:
    def __init__(self, max_error: float = 1.0, max_iterations: int = 20):
        self.max_error = max_error
        self.max_iterations = max_iterations
    
    def _bezier_point(self, t: float, p0: np.ndarray, p1: np.ndarray, 
                     p2: np.ndarray, p3: np.ndarray) -> np.ndarray:
        return (1 - t)**3 * p0 + 3 * (1 - t)**2 * t * p1 + 3 * (1 - t) * t**2 * p2 + t**3 * p3
    
    def _compute_bezier_error(self, control_points: np.ndarray, 
                              data_points: np.ndarray, t_values: np.ndarray) -> float:
        p0, p1, p2, p3 = control_points[:2], control_points[2:4], control_points[4:6], control_points[6:8]
        
        total_error = 0.0
        for i, t in enumerate(t_values):
            bezier_pt = self._bezier_point(t, p0, p1, p2, p3)
            total_error += np.linalg.norm(bezier_pt - data_points[i])
        
        return total_error / len(data_points)
    
    def _optimize_control_points(self, data_points: np.ndarray, 
                                 initial_control: np.ndarray) -> Tuple[np.ndarray, float]:
        n = len(data_points)
        t_values = np.linspace(0, 1, n)
        
        def objective(params):
            return self._compute_bezier_error(params, data_points, t_values)
        
        bounds = [
            (data_points[0, 0] - 50, data_points[0, 0] + 50),
            (data_points[0, 1] - 50, data_points[0, 1] + 50),
            (data_points[:, 0].min() - 50, data_points[:, 0].max() + 50),
            (data_points[:, 1].min() - 50, data_points[:, 1].max() + 50),
            (data_points[:, 0].min() - 50, data_points[:, 0].max() + 50),
            (data_points[:, 1].min() - 50, data_points[:, 1].max() + 50),
            (data_points[-1, 0] - 50, data_points[-1, 0] + 50),
            (data_points[-1, 1] - 50, data_points[-1, 1] + 50),
        ]
        
        result = optimize.minimize(
            objective,
            initial_control,
            method='L-BFGS-B',
            bounds=bounds,
            options={'maxiter': 500, 'ftol': 1e-6}
        )
        
        optimized = result.x
        final_error = objective(optimized)
        
        return optimized, final_error
    
    def _refine_t_values(self, control_points: np.ndarray, 
                         data_points: np.ndarray) -> np.ndarray:
        p0, p1, p2, p3 = control_points[:2], control_points[2:4], control_points[4:6], control_points[6:8]
        
        t_values = []
        for point in data_points:
            best_t = 0.0
            min_dist = float('inf')
            
            for t in np.linspace(0, 1, 100):
                bezier_pt = self._bezier_point(t, p0, p1, p2, p3)
                dist = np.linalg.norm(bezier_pt - point)
                if dist < min_dist:
                    min_dist = dist
                    best_t = t
            
            t_values.append(best_t)
        
        return np.array(t_values)
    
    def fit_segment_iterative(self, points: np.ndarray, 
                             max_iterations: int = None) -> Tuple[Tuple, float, Dict]:
        if max_iterations is None:
            max_iterations = self.max_iterations
        
        n = len(points)
        if n < 2:
            return ((points[0], points[0], points[0], points[0]), 0.0, {'iterations': 0})
        
        p0 = points[0]
        p3 = points[-1]
        
        if n == 2:
            return ((p0, p0, p3, p3), 0.0, {'iterations': 0})
        
        p1 = p0 + (p3 - p0) * 0.33
        p2 = p0 + (p3 - p0) * 0.66
        
        initial_control = np.concatenate([p0, p1, p2, p3])
        
        current_control = initial_control
        current_error = float('inf')
        best_error = float('inf')
        best_control = current_control
        
        iteration_history = []
        
        for iteration in range(max_iterations):
            optimized, error = self._optimize_control_points(points, current_control)
            
            if error < best_error:
                best_error = error
                best_control = optimized
            
            iteration_history.append(error)
            
            if abs(current_error - error) < 1e-6 or error < self.max_error:
                current_control = optimized
                current_error = error
                break
            
            current_control = optimized
            current_error = error
        
        p0_opt, p1_opt, p2_opt, p3_opt = (
            best_control[:2], best_control[2:4], best_control[4:6], best_control[6:8]
        )
        
        return (
            (p0_opt, p1_opt, p2_opt, p3_opt),
            best_error,
            {
                'iterations': iteration + 1,
                'error_history': iteration_history,
                'final_error': best_error
            }
        )
    
    def fit_cubic_bezier_iterative(self, points: np.ndarray) -> Tuple[List[Tuple], Dict]:
        if points is None or len(points) < 2:
            return [], {'total_error': 0.0, 'segments': []}
        
        beziers = []
        segment_info = []
        n = len(points)
        
        i = 0
        total_error = 0.0
        
        while i < n - 1:
            max_length = min(30, n - i - 1)
            
            best_j = min(i + max_length, n - 1)
            best_error = float('inf')
            best_bezier = None
            best_info = None
            
            for j in range(min(i + 4, n - 1), min(i + max_length + 1, n)):
                segment = points[i:j + 1]
                bezier, error, info = self.fit_segment_iterative(segment)
                
                if error < best_error:
                    best_error = error
                    best_j = j
                    best_bezier = bezier
                    best_info = info
                
                if error < self.max_error:
                    break
            
            if best_error > self.max_error * 2:
                best_j = min(i + 4, n - 1)
                segment = points[i:best_j + 1]
                best_bezier, best_error, best_info = self.fit_segment_iterative(segment)
            
            beziers.append(best_bezier)
            segment_info.append({
                'start': i,
                'end': best_j,
                'error': best_error,
                'info': best_info
            })
            total_error += best_error
            i = best_j
        
        return beziers, {
            'total_error': total_error,
            'average_error': total_error / len(beziers) if beziers else 0.0,
            'segments': segment_info
        }


class BezierConverter:
    def __init__(self, max_error: float = 2.0):
        self.max_error = max_error
        self.iterative_fitter = IterativeBezierFitter(max_error=max_error)
    
    def fit_cubic_bezier(self, points: np.ndarray, use_iterative: bool = True) -> List[Tuple]:
        if use_iterative:
            beziers, _ = self.iterative_fitter.fit_cubic_bezier_iterative(points)
            return beziers
        else:
            return self._fit_simple(points)
    
    def _fit_simple(self, points: np.ndarray) -> List[Tuple]:
        if points is None or len(points) < 2:
            return []
        
        beziers = []
        n = len(points)
        
        i = 0
        while i < n - 1:
            max_length = min(30, n - i - 1)
            
            best_j = min(i + max_length, n - 1)
            best_error = float('inf')
            
            for j in range(min(i + 4, n - 1), min(i + max_length + 1, n)):
                segment = points[i:j + 1]
                bezier, error = self._fit_segment_simple(segment)
                if error < best_error:
                    best_error = error
                    best_j = j
                    best_bezier = bezier
                if error < self.max_error:
                    break
            
            if best_error > self.max_error * 2:
                best_j = min(i + 4, n - 1)
                segment = points[i:best_j + 1]
                best_bezier, _ = self._fit_segment_simple(segment)
            
            beziers.append(best_bezier)
            i = best_j
        
        return beziers
    
    def _fit_segment_simple(self, points: np.ndarray) -> Tuple[Tuple, float]:
        n = len(points)
        
        if n < 2:
            return (points[0], points[0], points[0], points[0]), 0.0
        
        p0 = points[0]
        p3 = points[-1]
        
        if n == 2:
            return (p0, p0, p3, p3), 0.0
        
        t = np.linspace(0, 1, n)
        
        p1 = p0 + (p3 - p0) * 0.33
        p2 = p0 + (p3 - p0) * 0.66
        
        error = 0.0
        for i in range(n):
            bezier_point = (1 - t[i])**3 * p0 + 3 * (1 - t[i])**2 * t[i] * p1 + 3 * (1 - t[i]) * t[i]**2 * p2 + t[i]**3 * p3
            error += np.linalg.norm(bezier_point - points[i])
        
        return (p0, p1, p2, p3), error / n


class GlyphOptimizer:
    def __init__(self):
        self.smoother = ContourSmoother()
        self.bezier_converter = BezierConverter()
        self.corner_detector = CornerDetector()
    
    def optimize_glyph(self, points: np.ndarray, 
                      use_corner_preservation: bool = True,
                      use_iterative_fitting: bool = True) -> dict:
        if points is None or len(points) == 0:
            return None
        
        corner_indices = []
        if use_corner_preservation:
            corner_indices = self.corner_detector.detect_corners(points)
        
        smoothed = self.smoother.gaussian_smooth(
            points, sigma=1.5, preserve_corners=use_corner_preservation
        )
        smoothed = self.smoother.remove_duplicates(smoothed, min_distance=0.5)
        
        reduced = self.smoother.reduce_points(
            smoothed, tolerance=0.5, preserve_corners=use_corner_preservation
        )
        
        beziers, fitting_info = self.bezier_converter.iterative_fitter.fit_cubic_bezier_iterative(reduced)
        
        bounds = self._calculate_bounds(smoothed)
        
        corner_info = []
        for idx in corner_indices:
            corner_info.append({
                'index': idx,
                'point': points[idx].tolist(),
                'strength': self.corner_detector.get_corner_strength(points, idx)
            })
        
        return {
            'original_points': points,
            'smoothed_points': smoothed,
            'reduced_points': reduced,
            'bezier_curves': beziers,
            'bounds': bounds,
            'corners': corner_info,
            'fitting_info': fitting_info
        }
    
    def _calculate_bounds(self, points: np.ndarray) -> dict:
        if points is None or len(points) == 0:
            return {'x_min': 0, 'y_min': 0, 'x_max': 0, 'y_max': 0, 'width': 0, 'height': 0}
        
        x_min, y_min = np.min(points, axis=0)
        x_max, y_max = np.max(points, axis=0)
        
        return {
            'x_min': x_min,
            'y_min': y_min,
            'x_max': x_max,
            'y_max': y_max,
            'width': x_max - x_min,
            'height': y_max - y_min
        }
    
    def scale_to_font_units(self, points: np.ndarray, target_size: int = 600) -> np.ndarray:
        if points is None or len(points) == 0:
            return points
        
        bounds = self._calculate_bounds(points)
        current_size = max(bounds['width'], bounds['height'])
        
        if current_size == 0:
            return points
        
        scale = target_size / current_size
        
        scaled = points * scale
        
        return scaled
    
    def center_glyph(self, points: np.ndarray, canvas_size: int = 1000, baseline: int = 200) -> np.ndarray:
        if points is None or len(points) == 0:
            return points
        
        bounds = self._calculate_bounds(points)
        
        center_x = (bounds['x_min'] + bounds['x_max']) / 2
        center_y = (bounds['y_min'] + bounds['y_max']) / 2
        
        target_x = canvas_size / 2
        target_y = baseline + (bounds['height'] / 2)
        
        offset_x = target_x - center_x
        offset_y = target_y - center_y
        
        centered = points + np.array([offset_x, offset_y])
        
        return centered
