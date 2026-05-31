import cv2
import numpy as np
from typing import Tuple, Optional, Dict


class UnderwaterWhiteBalancer:
    @staticmethod
    def gray_world_red_compensation(img: np.ndarray, compensation_strength: float = 1.0) -> Tuple[np.ndarray, Dict]:
        result = img.copy().astype(np.float32)
        
        avg_r = np.mean(result[:, :, 2])
        avg_g = np.mean(result[:, :, 1])
        avg_b = np.mean(result[:, :, 0])
        avg_gray = (avg_r + avg_g + avg_b) / 3.0
        
        gw_r = avg_gray / (avg_r + 1e-6)
        gw_g = avg_gray / (avg_g + 1e-6)
        gw_b = avg_gray / (avg_b + 1e-6)
        
        r_ratio = avg_r / avg_gray
        b_ratio = avg_b / avg_gray
        
        red_compensation = 1.0
        if r_ratio < 0.8:
            red_compensation = 1.0 + (0.8 - r_ratio) * compensation_strength * 2.0
        
        blue_attenuation = 1.0
        if b_ratio > 1.2:
            blue_attenuation = 1.0 - (b_ratio - 1.2) * 0.3 * compensation_strength
        
        final_r = np.clip(gw_r * red_compensation, 1.0, 3.0)
        final_g = np.clip(gw_g, 0.8, 1.5)
        final_b = np.clip(gw_b * blue_attenuation, 0.5, 1.5)
        
        result[:, :, 2] = np.clip(result[:, :, 2] * final_r, 0, 255)
        result[:, :, 1] = np.clip(result[:, :, 1] * final_g, 0, 255)
        result[:, :, 0] = np.clip(result[:, :, 0] * final_b, 0, 255)
        
        info = {
            'gray_world_gains': (gw_r, gw_g, gw_b),
            'red_compensation': red_compensation,
            'blue_attenuation': blue_attenuation,
            'final_gains': (final_r, final_g, final_b),
            'r_ratio': r_ratio,
            'b_ratio': b_ratio
        }
        
        return result.astype(np.uint8), info
    
    @staticmethod
    def adaptive_red_channel_compensation(img: np.ndarray, water_type: str = 'clear') -> Tuple[np.ndarray, Dict]:
        result = img.copy().astype(np.float32)
        
        depth_based_compensation = {
            'clear': 1.2,
            'shallow': 1.3,
            'moderate': 1.5,
            'deep': 1.8,
            'turbid': 2.0
        }
        
        base_compensation = depth_based_compensation.get(water_type, 1.4)
        
        local_r = result[:, :, 2]
        local_g = result[:, :, 1]
        local_b = result[:, :, 0]
        
        r_g_ratio = local_r / (local_g + 1e-6)
        r_b_ratio = local_r / (local_b + 1e-6)
        
        avg_r_g_ratio = np.mean(r_g_ratio)
        target_ratio = 0.9
        
        if avg_r_g_ratio < target_ratio:
            compensation_factor = target_ratio / (avg_r_g_ratio + 1e-6)
            compensation_factor = np.clip(compensation_factor, 1.0, base_compensation)
        else:
            compensation_factor = 1.0
        
        result[:, :, 2] = np.clip(result[:, :, 2] * compensation_factor, 0, 255)
        
        b_compensation = np.clip(1.0 - (np.mean(local_b) / 255.0 - 0.5) * 0.5, 0.7, 1.0)
        result[:, :, 0] = np.clip(result[:, :, 0] * b_compensation, 0, 255)
        
        info = {
            'water_type': water_type,
            'r_compensation': compensation_factor,
            'b_compensation': b_compensation,
            'avg_r_g_ratio': avg_r_g_ratio
        }
        
        return result.astype(np.uint8), info
    
    @staticmethod
    def gray_world(img: np.ndarray) -> np.ndarray:
        result = img.copy().astype(np.float32)
        avg_r = np.mean(result[:, :, 2])
        avg_g = np.mean(result[:, :, 1])
        avg_b = np.mean(result[:, :, 0])
        avg_gray = (avg_r + avg_g + avg_b) / 3.0
        
        result[:, :, 2] = np.clip(result[:, :, 2] * (avg_gray / avg_r), 0, 255)
        result[:, :, 1] = np.clip(result[:, :, 1] * (avg_gray / avg_g), 0, 255)
        result[:, :, 0] = np.clip(result[:, :, 0] * (avg_gray / avg_b), 0, 255)
        
        return result.astype(np.uint8)


class WhiteBalancer(UnderwaterWhiteBalancer):
    @staticmethod
    def simple_white_balance(img: np.ndarray, percentile: float = 0.5) -> np.ndarray:
        result = img.copy().astype(np.float32)
        
        for channel in range(3):
            flat = result[:, :, channel].flatten()
            low = np.percentile(flat, percentile)
            high = np.percentile(flat, 100 - percentile)
            result[:, :, channel] = np.clip((result[:, :, channel] - low) * 255.0 / (high - low + 1e-6), 0, 255)
        
        return result.astype(np.uint8)
    
    @staticmethod
    def underwater_color_correction(img: np.ndarray, red_boost: float = 1.2, blue_scale: float = 0.9) -> np.ndarray:
        result = img.copy().astype(np.float32)
        
        result[:, :, 2] = np.clip(result[:, :, 2] * red_boost, 0, 255)
        result[:, :, 0] = np.clip(result[:, :, 0] * blue_scale, 0, 255)
        
        return result.astype(np.uint8)


class WaterQualityEstimator:
    @staticmethod
    def estimate_turbidity(img: np.ndarray) -> float:
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(gray, 30, 100)
        edge_density = np.sum(edges > 0) / (edges.shape[0] * edges.shape[1])
        turbidity = 1.0 - min(edge_density * 10, 1.0)
        return turbidity
    
    @staticmethod
    def estimate_color_attenuation(img: np.ndarray) -> Dict[str, float]:
        avg_r = np.mean(img[:, :, 2])
        avg_g = np.mean(img[:, :, 1])
        avg_b = np.mean(img[:, :, 0])
        
        r_attenuation = 1.0 - (avg_r / 255.0)
        g_attenuation = 1.0 - (avg_g / 255.0)
        b_attenuation = 1.0 - (avg_b / 255.0)
        
        return {
            'r_attenuation': r_attenuation,
            'g_attenuation': g_attenuation,
            'b_attenuation': b_attenuation,
            'r_g_ratio': avg_r / (avg_g + 1e-6),
            'r_b_ratio': avg_r / (avg_b + 1e-6)
        }
    
    @staticmethod
    def estimate_water_depth(img: np.ndarray) -> str:
        avg_r = np.mean(img[:, :, 2])
        avg_b = np.mean(img[:, :, 0])
        b_r_ratio = avg_b / (avg_r + 1e-6)
        
        if b_r_ratio < 1.2:
            return 'shallow'
        elif b_r_ratio < 1.8:
            return 'moderate'
        elif b_r_ratio < 2.5:
            return 'deep'
        else:
            return 'very_deep'
    
    @staticmethod
    def estimate_water_type(img: np.ndarray) -> str:
        turbidity = WaterQualityEstimator.estimate_turbidity(img)
        depth = WaterQualityEstimator.estimate_water_depth(img)
        
        if turbidity > 0.7:
            return 'turbid'
        elif turbidity > 0.5:
            return 'murky'
        elif depth == 'shallow':
            return 'clear'
        elif depth == 'moderate':
            return 'coastal'
        else:
            return 'oceanic'
    
    @classmethod
    def estimate_water_quality(cls, img: np.ndarray) -> Dict:
        turbidity = cls.estimate_turbidity(img)
        attenuation = cls.estimate_color_attenuation(img)
        depth = cls.estimate_water_depth(img)
        water_type = cls.estimate_water_type(img)
        
        dark = DarkChannelPrior(patch_size=15).get_dark_channel(img.astype(np.float32))
        haze_level = np.mean(dark) / 255.0
        
        depth_scores = {'shallow': 0.2, 'moderate': 0.5, 'deep': 0.8, 'very_deep': 1.0}
        depth_score = depth_scores.get(depth, 0.5)
        
        overall_quality = 1.0 - (turbidity * 0.4 + haze_level * 0.4 + depth_score * 0.2)
        
        return {
            'turbidity': turbidity,
            'haze_level': haze_level,
            'depth': depth,
            'water_type': water_type,
            'color_attenuation': attenuation,
            'overall_quality': overall_quality
        }
    
    @classmethod
    def get_dynamic_attenuation_params(cls, img: np.ndarray) -> Dict:
        quality = cls.estimate_water_quality(img)
        turbidity = quality['turbidity']
        depth = quality['depth']
        
        depth_factors = {
            'shallow': 1.1,
            'moderate': 1.4,
            'deep': 1.7,
            'very_deep': 2.0
        }
        
        red_attenuation = depth_factors.get(depth, 1.4) * (1.0 + turbidity * 0.3)
        blue_attenuation = 0.9 - turbidity * 0.2
        omega = 0.8 + turbidity * 0.15
        gamma = 0.9 + (1.0 - quality['overall_quality']) * 0.3
        
        return {
            'red_boost': np.clip(red_attenuation, 1.0, 2.5),
            'blue_scale': np.clip(blue_attenuation, 0.6, 1.0),
            'omega': np.clip(omega, 0.75, 0.98),
            'gamma': np.clip(gamma, 0.7, 1.3),
            'water_quality': quality
        }


class DepthEstimator:
    def __init__(self, max_depth_range: float = 10.0, num_bins: int = 5):
        self.max_depth_range = max_depth_range
        self.num_bins = num_bins
    
    def estimate_depth_map(self, img: np.ndarray) -> np.ndarray:
        h, w = img.shape[:2]
        
        r_channel = img[:, :, 2].astype(np.float32)
        g_channel = img[:, :, 1].astype(np.float32)
        b_channel = img[:, :, 0].astype(np.float32)
        
        brightness = (r_channel + g_channel + b_channel) / (3.0 * 255.0 + 1e-6)
        
        dcp = DarkChannelPrior(patch_size=15)
        dark = dcp.get_dark_channel(img.astype(np.float32))
        
        saturation_r = b_channel / (g_channel + 1e-6)
        depth_saturation = 1.0 - np.clip(saturation_r / 3.0, 0, 1)
        
        depth_map = dark / 255.0 * 0.5 + (1.0 - brightness) * 0.3 + depth_saturation * 0.2
        
        depth_map = cv2.GaussianBlur(depth_map, (21, 21), 5)
        
        depth_map = (depth_map - depth_map.min()) / (depth_map.max() - depth_map.min() + 1e-6)
        
        return depth_map
    
    def depth_guided_enhance(self, img: np.ndarray, depth_map: np.ndarray,
                             near_strength: float = 0.6,
                             far_strength: float = 1.4) -> Tuple[np.ndarray, Dict]:
        result = img.copy().astype(np.float32)
        
        strength_map = near_strength + (far_strength - near_strength) * depth_map
        strength_map_3c = np.stack([strength_map] * 3, axis=2)
        
        blur_map = depth_map * 0.8
        blur_map_3c = np.stack([blur_map] * 3, axis=2)
        
        mean_val = np.mean(result, axis=(0, 1), keepdims=True)
        enhanced = result + (result - mean_val) * (strength_map_3c - 1.0)
        
        blurred = cv2.GaussianBlur(result, (15, 15), 5)
        enhanced = enhanced * (1 - blur_map_3c) + blurred * blur_map_3c
        
        r_channel = result[:, :, 2]
        red_compensation = 1.0 + depth_map * 0.5
        enhanced[:, :, 2] = np.clip(enhanced[:, :, 2] * np.stack([red_compensation], axis=2).squeeze(-1) , 0, 255)
        
        result = np.clip(enhanced, 0, 255).astype(np.uint8)
        
        info = {
            'depth_map_stats': {
                'min': float(depth_map.min()),
                'max': float(depth_map.max()),
                'mean': float(depth_map.mean())
            },
            'near_strength': near_strength,
            'far_strength': far_strength
        }
        
        return result, info
    
    def get_depth_weighted_params(self, depth_map: np.ndarray) -> Dict[str, np.ndarray]:
        near_omega = 0.85
        far_omega = 0.98
        omega_map = near_omega + (far_omega - near_omega) * depth_map
        
        near_gamma = 1.0
        far_gamma = 0.7
        gamma_map = near_gamma + (far_gamma - near_gamma) * depth_map
        
        near_red = 1.2
        far_red = 2.0
        red_map = near_red + (far_red - near_red) * depth_map
        
        return {
            'omega_map': omega_map,
            'gamma_map': gamma_map,
            'red_boost_map': red_map
        }


class ColorRestorer:
    def __init__(self, attenuation_coeffs: Optional[Dict[str, float]] = None):
        default_coeffs = {
            'r_attenuation': 0.8,
            'g_attenuation': 0.3,
            'b_attenuation': 0.1,
            'scattering_r': 0.01,
            'scattering_g': 0.04,
            'scattering_b': 0.1
        }
        self.attenuation_coeffs = attenuation_coeffs or default_coeffs
    
    def estimate_underwater_attenuation(self, img: np.ndarray) -> Dict[str, np.ndarray]:
        h, w = img.shape[:2]
        
        r_channel = img[:, :, 2].astype(np.float32) / 255.0
        g_channel = img[:, :, 1].astype(np.float32) / 255.0
        b_channel = img[:, :, 0].astype(np.float32) / 255.0
        
        center_y, center_x = h // 2, w // 2
        
        ref_r = np.percentile(r_channel, 90)
        ref_g = np.percentile(g_channel, 90)
        ref_b = np.percentile(b_channel, 90)
        
        r_attenuation = np.clip(ref_r / (r_channel + 1e-6), 1.0, 5.0)
        g_attenuation = np.clip(ref_g / (g_channel + 1e-6), 1.0, 3.0)
        b_attenuation = np.clip(ref_b / (b_channel + 1e-6), 0.8, 2.0)
        
        return {
            'r_attenuation': r_attenuation,
            'g_attenuation': g_attenuation,
            'b_attenuation': b_attenuation,
            'ref_values': (ref_r, ref_g, ref_b)
        }
    
    def inverse_attenuation_correction(self, img: np.ndarray, 
                                       depth_map: Optional[np.ndarray] = None,
                                       strength: float = 1.0) -> Tuple[np.ndarray, Dict]:
        result = img.copy().astype(np.float32)
        
        attenuation = self.estimate_underwater_attenuation(img)
        
        if depth_map is not None:
            depth_factor = 1.0 + depth_map * 0.5
            r_gain = attenuation['r_attenuation'] * depth_factor * strength
            g_gain = np.clip(attenuation['g_attenuation'] * (0.5 + 0.5 * strength), 1.0, 2.0)
            b_gain = attenuation['b_attenuation'] ** (1.0 / (1.0 + strength * 0.5))
        else:
            r_gain = attenuation['r_attenuation'] * strength
            g_gain = np.clip(attenuation['g_attenuation'] * (0.5 + 0.5 * strength), 1.0, 2.0)
            b_gain = attenuation['b_attenuation'] ** (1.0 / (1.0 + strength * 0.5))
        
        r_gain = np.clip(r_gain, 1.0, 4.0)
        g_gain = np.clip(g_gain, 1.0, 2.5)
        b_gain = np.clip(b_gain, 0.5, 1.5)
        
        result[:, :, 2] = np.clip(result[:, :, 2] * r_gain, 0, 255)
        result[:, :, 1] = np.clip(result[:, :, 1] * g_gain, 0, 255)
        result[:, :, 0] = np.clip(result[:, :, 0] * b_gain, 0, 255)
        
        result = np.clip(result, 0, 255).astype(np.uint8)
        
        info = {
            'r_gain_mean': float(np.mean(r_gain)),
            'g_gain_mean': float(np.mean(g_gain)),
            'b_gain_mean': float(np.mean(b_gain)),
            'ref_values': attenuation['ref_values'],
            'strength': strength
        }
        
        return result, info
    
    def wavelength_compensation(self, img: np.ndarray, 
                                 depth_map: Optional[np.ndarray] = None) -> Tuple[np.ndarray, Dict]:
        result = img.copy().astype(np.float32) / 255.0
        
        r = result[:, :, 2]
        g = result[:, :, 1]
        b = result[:, :, 0]
        
        wavelength_factors = {
            'red': {'absorption': 0.4, 'scatter': 0.02},
            'green': {'absorption': 0.05, 'scatter': 0.05},
            'blue': {'absorption': 0.01, 'scatter': 0.15}
        }
        
        if depth_map is not None:
            depth_normalized = depth_map
        else:
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY).astype(np.float32) / 255.0
            depth_normalized = 1.0 - gray
            depth_normalized = (depth_normalized - depth_normalized.min()) / (depth_normalized.max() - depth_normalized.min() + 1e-6)
        
        r_compensation = np.exp(wavelength_factors['red']['absorption'] * depth_normalized * 3.0)
        g_compensation = np.exp(wavelength_factors['green']['absorption'] * depth_normalized * 1.0)
        b_scatter_reduction = 1.0 - wavelength_factors['blue']['scatter'] * depth_normalized
        
        r_restored = np.clip(r * r_compensation, 0, 1)
        g_restored = np.clip(g * g_compensation, 0, 1)
        b_restored = np.clip(b * b_scatter_reduction, 0, 1)
        
        result[:, :, 2] = r_restored
        result[:, :, 1] = g_restored
        result[:, :, 0] = b_restored
        
        result = np.clip(result * 255, 0, 255).astype(np.uint8)
        
        info = {
            'r_compensation_mean': float(np.mean(r_compensation)),
            'g_compensation_mean': float(np.mean(g_compensation)),
            'b_scatter_reduction_mean': float(np.mean(b_scatter_reduction))
        }
        
        return result, info
    
    def restore_colors(self, img: np.ndarray, 
                       depth_map: Optional[np.ndarray] = None,
                       strength: float = 1.0) -> Tuple[np.ndarray, Dict]:
        step1, info1 = self.inverse_attenuation_correction(img, depth_map, strength)
        
        step2, info2 = self.wavelength_compensation(step1, depth_map)
        
        combined_info = {
            'attenuation_correction': info1,
            'wavelength_compensation': info2,
            'steps': ['inverse_attenuation', 'wavelength_compensation']
        }
        
        return step2, combined_info


class FisheyeCorrector:
    def __init__(self, camera_matrix: Optional[np.ndarray] = None,
                 dist_coeffs: Optional[np.ndarray] = None,
                 balance: float = 0.0):
        self.camera_matrix = camera_matrix
        self.dist_coeffs = dist_coeffs
        self.balance = balance
        self._map1 = None
        self._map2 = None
        self._calibrated = False
    
    def calibrate_from_image(self, img: np.ndarray, 
                             corner_count: Tuple[int, int] = (9, 6),
                             square_size: float = 1.0) -> bool:
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        ret, corners = cv2.findChessboardCorners(gray, corner_count, None)
        
        if not ret:
            return False
        
        criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 0.001)
        corners2 = cv2.cornerSubPix(gray, corners, (11, 11), (-1, -1), criteria)
        
        objp = np.zeros((corner_count[0] * corner_count[1], 3), np.float32)
        objp[:, :2] = np.mgrid[0:corner_count[0], 0:corner_count[1]].T.reshape(-1, 2)
        objp *= square_size
        
        objpoints = [objp]
        imgpoints = [corners2]
        
        ret, mtx, dist, rvecs, tvecs = cv2.calibrateCamera(objpoints, imgpoints, gray.shape[::-1], None, None)
        
        if ret:
            self.camera_matrix = mtx
            self.dist_coeffs = dist
            self._calibrated = True
            self._map1 = None
            self._map2 = None
            return True
        
        return False
    
    def set_calibration(self, camera_matrix: np.ndarray, dist_coeffs: np.ndarray):
        self.camera_matrix = camera_matrix
        self.dist_coeffs = dist_coeffs
        self._calibrated = True
        self._map1 = None
        self._map2 = None
    
    def auto_calibrate(self, img: np.ndarray, k1: float = -0.3, k2: float = 0.1,
                       p1: float = 0.0, p2: float = 0.0, k3: float = 0.0) -> None:
        h, w = img.shape[:2]
        
        fx = w
        fy = w
        cx = w / 2.0
        cy = h / 2.0
        
        self.camera_matrix = np.array([
            [fx, 0, cx],
            [0, fy, cy],
            [0, 0, 1]
        ], dtype=np.float64)
        
        self.dist_coeffs = np.array([k1, k2, p1, p2, k3], dtype=np.float64)
        self._calibrated = True
        self._map1 = None
        self._map2 = None
    
    def correct(self, img: np.ndarray) -> Tuple[np.ndarray, Dict]:
        if not self._calibrated:
            self.auto_calibrate(img)
        
        h, w = img.shape[:2]
        
        if self._map1 is None or self._map2 is None:
            new_camera_matrix, roi = cv2.getOptimalNewCameraMatrix(
                self.camera_matrix, self.dist_coeffs, (w, h), self.balance, (w, h)
            )
            
            self._map1, self._map2 = cv2.initUndistortRectifyMap(
                self.camera_matrix, self.dist_coeffs, None, new_camera_matrix,
                (w, h), cv2.CV_32FC1
            )
            
            self._new_camera_matrix = new_camera_matrix
            self._roi = roi
        
        result = cv2.remap(img, self._map1, self._map2, cv2.INTER_LINEAR)
        
        info = {
            'calibrated': self._calibrated,
            'roi': self._roi if hasattr(self, '_roi') else (0, 0, w, h),
            'distortion_model': 'fisheye'
        }
        
        return result, info
    
    def correct_and_crop(self, img: np.ndarray) -> Tuple[np.ndarray, Dict]:
        corrected, info = self.correct(img)
        
        if hasattr(self, '_roi') and self._roi is not None:
            x, y, w, h = self._roi
            if w > 0 and h > 0:
                corrected = corrected[y:y+h, x:x+w]
                info['cropped'] = True
                info['crop_region'] = (x, y, w, h)
            else:
                info['cropped'] = False
        else:
            info['cropped'] = False
        
        return corrected, info
    
    def estimate_distortion(self, img: np.ndarray) -> Dict[str, float]:
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        h, w = gray.shape
        
        edges = cv2.Canny(gray, 50, 150)
        
        lines = cv2.HoughLinesP(edges, 1, np.pi / 180, threshold=100,
                                minLineLength=50, maxLineGap=10)
        
        if lines is None or len(lines) < 4:
            return {'estimated_k1': -0.3, 'confidence': 0.0, 'num_lines': 0}
        
        curvatures = []
        for line in lines:
            x1, y1, x2, y2 = line[0]
            dx = x2 - x1
            dy = y2 - y1
            length = np.sqrt(dx**2 + dy**2) + 1e-6
            
            mid_x = (x1 + x2) / 2.0 - w / 2.0
            mid_y = (y1 + y2) / 2.0 - h / 2.0
            
            dist_from_center = np.sqrt(mid_x**2 + mid_y**2) / (min(w, h) / 2.0 + 1e-6)
            
            deviation = abs(dx * dy) / (length**2 + 1e-6)
            curvatures.append(deviation * dist_from_center)
        
        avg_curvature = np.mean(curvatures) if curvatures else 0
        
        estimated_k1 = -avg_curvature * 5.0
        estimated_k1 = np.clip(estimated_k1, -1.0, 0.0)
        
        confidence = min(len(lines) / 20.0, 1.0)
        
        return {
            'estimated_k1': estimated_k1,
            'confidence': confidence,
            'num_lines': len(lines),
            'avg_curvature': avg_curvature
        }


class DarkChannelPrior:
    def __init__(self, patch_size: int = 15, omega: float = 0.95, t0: float = 0.1):
        self.patch_size = patch_size
        self.omega = omega
        self.t0 = t0
    
    def get_dark_channel(self, img: np.ndarray) -> np.ndarray:
        min_channel = np.min(img, axis=2)
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (self.patch_size, self.patch_size))
        dark = cv2.erode(min_channel, kernel)
        return dark
    
    def estimate_atmospheric_light(self, img: np.ndarray, dark: np.ndarray, top_pixels: float = 0.001) -> np.ndarray:
        h, w = dark.shape
        num_pixels = h * w
        num_brightest = int(max(num_pixels * top_pixels, 1))
        
        dark_flat = dark.flatten()
        indices = np.argsort(dark_flat)[-num_brightest:]
        
        img_flat = img.reshape(-1, 3)
        A = np.mean(img_flat[indices], axis=0)
        return A
    
    def estimate_transmission(self, img: np.ndarray, A: np.ndarray) -> np.ndarray:
        normalized = img.astype(np.float32) / A
        dark = self.get_dark_channel(normalized)
        t = 1.0 - self.omega * dark
        return t
    
    def refine_transmission(self, img: np.ndarray, t: np.ndarray, guide_rate: int = 60, eps: float = 1e-3) -> np.ndarray:
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY).astype(np.float32) / 255.0
        t_refined = self.guided_filter(gray, t, guide_rate, eps)
        return t_refined
    
    def guided_filter(self, I: np.ndarray, p: np.ndarray, r: int, eps: float) -> np.ndarray:
        mean_I = cv2.boxFilter(I, cv2.CV_64F, (r, r))
        mean_p = cv2.boxFilter(p, cv2.CV_64F, (r, r))
        mean_Ip = cv2.boxFilter(I * p, cv2.CV_64F, (r, r))
        cov_Ip = mean_Ip - mean_I * mean_p
        
        mean_II = cv2.boxFilter(I * I, cv2.CV_64F, (r, r))
        var_I = mean_II - mean_I * mean_I
        
        a = cov_Ip / (var_I + eps)
        b = mean_p - a * mean_I
        
        mean_a = cv2.boxFilter(a, cv2.CV_64F, (r, r))
        mean_b = cv2.boxFilter(b, cv2.CV_64F, (r, r))
        
        q = mean_a * I + mean_b
        return q
    
    def recover(self, img: np.ndarray, t: np.ndarray, A: np.ndarray) -> np.ndarray:
        t = np.maximum(t, self.t0)
        t = np.expand_dims(t, axis=2)
        result = (img.astype(np.float32) - A) / t + A
        result = np.clip(result, 0, 255)
        return result.astype(np.uint8)
    
    def enhance(self, img: np.ndarray) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        img_float = img.astype(np.float32)
        dark = self.get_dark_channel(img_float)
        A = self.estimate_atmospheric_light(img_float, dark)
        t = self.estimate_transmission(img_float, A)
        t_refined = self.refine_transmission(img, t)
        result = self.recover(img_float, t_refined, A)
        return result, t_refined, A


class ContrastEnhancer:
    @staticmethod
    def clahe(img: np.ndarray, clip_limit: float = 2.0, tile_grid_size: Tuple[int, int] = (8, 8)) -> np.ndarray:
        lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)
        
        clahe = cv2.createCLAHE(clipLimit=clip_limit, tileGridSize=tile_grid_size)
        l_enhanced = clahe.apply(l)
        
        lab_enhanced = cv2.merge((l_enhanced, a, b))
        result = cv2.cvtColor(lab_enhanced, cv2.COLOR_LAB2BGR)
        return result
    
    @staticmethod
    def gamma_correction(img: np.ndarray, gamma: float = 1.0) -> np.ndarray:
        inv_gamma = 1.0 / gamma
        table = np.array([((i / 255.0) ** inv_gamma) * 255 for i in np.arange(0, 256)]).astype(np.uint8)
        return cv2.LUT(img, table)
    
    @staticmethod
    def sharpen(img: np.ndarray, strength: float = 1.0) -> np.ndarray:
        kernel = np.array([[-1, -1, -1],
                          [-1,  9, -1],
                          [-1, -1, -1]]) * strength
        result = cv2.filter2D(img, -1, kernel)
        return np.clip(result, 0, 255)


class AdaptiveParameterEstimator:
    @staticmethod
    def estimate_color_cast(img: np.ndarray) -> Tuple[float, float, float]:
        avg_r = np.mean(img[:, :, 2])
        avg_g = np.mean(img[:, :, 1])
        avg_b = np.mean(img[:, :, 0])
        
        total = avg_r + avg_g + avg_b + 1e-6
        r_ratio = avg_r / total
        g_ratio = avg_g / total
        b_ratio = avg_b / total
        
        return r_ratio, g_ratio, b_ratio
    
    @staticmethod
    def estimate_brightness(img: np.ndarray) -> float:
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        return np.mean(gray) / 255.0
    
    @staticmethod
    def estimate_contrast(img: np.ndarray) -> float:
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        return np.std(gray) / 128.0
    
    @staticmethod
    def estimate_haze_level(img: np.ndarray) -> float:
        dark = DarkChannelPrior(patch_size=15).get_dark_channel(img.astype(np.float32))
        haze_level = np.mean(dark) / 255.0
        return haze_level
    
    @classmethod
    def get_adaptive_params(cls, img: np.ndarray, use_water_estimation: bool = True) -> dict:
        if use_water_estimation:
            water_params = WaterQualityEstimator.get_dynamic_attenuation_params(img)
            quality = water_params['water_quality']
            
            contrast = cls.estimate_contrast(img)
            brightness = cls.estimate_brightness(img)
            
            clahe_clip = 1.5 + contrast * 1.5
            
            return {
                'red_boost': water_params['red_boost'],
                'blue_scale': water_params['blue_scale'],
                'gamma': water_params['gamma'],
                'omega': water_params['omega'],
                'clahe_clip': np.clip(clahe_clip, 1.0, 3.0),
                'haze_level': quality['haze_level'],
                'brightness': brightness,
                'contrast': contrast,
                'turbidity': quality['turbidity'],
                'depth': quality['depth'],
                'water_type': quality['water_type'],
                'water_quality': quality['overall_quality'],
                'use_water_estimation': True
            }
        else:
            r_ratio, g_ratio, b_ratio = cls.estimate_color_cast(img)
            brightness = cls.estimate_brightness(img)
            contrast = cls.estimate_contrast(img)
            haze_level = cls.estimate_haze_level(img)
            
            red_boost = 1.0 + (0.5 - r_ratio) * 2.0
            blue_scale = 1.0 - (b_ratio - 0.33) * 0.5
            
            gamma = 1.0
            if brightness < 0.3:
                gamma = 0.7
            elif brightness > 0.7:
                gamma = 1.3
            
            omega = 0.85 + haze_level * 0.15
            clahe_clip = 1.5 + contrast * 1.5
            
            return {
                'red_boost': np.clip(red_boost, 0.8, 1.8),
                'blue_scale': np.clip(blue_scale, 0.7, 1.1),
                'gamma': np.clip(gamma, 0.6, 1.5),
                'omega': np.clip(omega, 0.8, 1.0),
                'clahe_clip': np.clip(clahe_clip, 1.0, 3.0),
                'haze_level': haze_level,
                'brightness': brightness,
                'contrast': contrast,
                'use_water_estimation': False
            }


class UnderwaterImageEnhancer:
    def __init__(self, use_adaptive: bool = True, use_water_estimation: bool = True, 
                 use_advanced_white_balance: bool = True,
                 use_depth_estimation: bool = True,
                 use_color_restoration: bool = True,
                 use_fisheye_correction: bool = False,
                 **kwargs):
        self.use_adaptive = use_adaptive
        self.use_water_estimation = use_water_estimation
        self.use_advanced_white_balance = use_advanced_white_balance
        self.use_depth_estimation = use_depth_estimation
        self.use_color_restoration = use_color_restoration
        self.use_fisheye_correction = use_fisheye_correction
        self.params = kwargs
        self.white_balancer = WhiteBalancer()
        self.contrast_enhancer = ContrastEnhancer()
        self.adaptive_estimator = AdaptiveParameterEstimator()
        self.water_quality_estimator = WaterQualityEstimator()
        self.depth_estimator = DepthEstimator()
        self.color_restorer = ColorRestorer()
        self.fisheye_corrector = FisheyeCorrector()
    
    def enhance(self, img: np.ndarray, use_adaptive: Optional[bool] = None, 
                frame_params: Optional[dict] = None) -> Tuple[np.ndarray, dict]:
        if img is None:
            raise ValueError("Input image is None")
        
        if len(img.shape) != 3 or img.shape[2] != 3:
            raise ValueError("Input image must be a 3-channel BGR image")
        
        use_adaptive = self.use_adaptive if use_adaptive is None else use_adaptive
        
        if frame_params is not None:
            params = frame_params
            wb_info = None
        elif use_adaptive:
            adaptive_params = self.adaptive_estimator.get_adaptive_params(
                img, 
                use_water_estimation=self.use_water_estimation
            )
            params = {**self.params, **adaptive_params}
            wb_info = None
        else:
            params = {
                'red_boost': self.params.get('red_boost', 1.3),
                'blue_scale': self.params.get('blue_scale', 0.9),
                'gamma': self.params.get('gamma', 1.0),
                'omega': self.params.get('omega', 0.95),
                'clahe_clip': self.params.get('clahe_clip', 2.0),
                **self.params
            }
            wb_info = None
        
        depth_map = None
        depth_info = None
        if self.use_depth_estimation and frame_params is None:
            depth_map = self.depth_estimator.estimate_depth_map(img)
        
        if self.use_color_restoration and frame_params is None:
            color_strength = self.params.get('color_restoration_strength', 1.0)
            step1, color_info = self.color_restorer.restore_colors(
                img, depth_map=depth_map, strength=color_strength
            )
        elif self.use_advanced_white_balance and frame_params is None:
            comp_strength = self.params.get('compensation_strength', 1.0)
            step1, wb_info = self.white_balancer.gray_world_red_compensation(
                img, 
                compensation_strength=comp_strength
            )
            color_info = None
        else:
            step1 = self.white_balancer.underwater_color_correction(
                img, 
                red_boost=params['red_boost'], 
                blue_scale=params['blue_scale']
            )
            wb_info = None
            color_info = None
        
        if self.use_depth_estimation and depth_map is not None and frame_params is None:
            near_strength = self.params.get('near_strength', 0.6)
            far_strength = self.params.get('far_strength', 1.4)
            step2, depth_info = self.depth_estimator.depth_guided_enhance(
                step1, depth_map,
                near_strength=near_strength,
                far_strength=far_strength
            )
        else:
            step2 = step1
        
        dcp = DarkChannelPrior(
            patch_size=self.params.get('patch_size', 15),
            omega=params['omega'],
            t0=self.params.get('t0', 0.1)
        )
        step3, _, _ = dcp.enhance(step2)
        
        step4 = self.contrast_enhancer.clahe(step3, clip_limit=params['clahe_clip'])
        
        step5 = self.contrast_enhancer.gamma_correction(step4, gamma=params['gamma'])
        
        result = self.contrast_enhancer.sharpen(step5, strength=self.params.get('sharpen_strength', 0.5))
        
        fisheye_info = None
        if self.use_fisheye_correction:
            result, fisheye_info = self.fisheye_corrector.correct(result)
        
        steps = []
        if self.use_color_restoration and color_info is not None:
            steps.append('color_restoration')
        elif self.use_advanced_white_balance:
            steps.append('advanced_white_balance')
        else:
            steps.append('color_correction')
        if self.use_depth_estimation and depth_info is not None:
            steps.append('depth_guided')
        steps.extend(['dcp_dehaze', 'clahe', 'gamma', 'sharpen'])
        if self.use_fisheye_correction:
            steps.append('fisheye_correction')
        
        info = {
            'adaptive_params': params if use_adaptive else None,
            'white_balance_info': wb_info,
            'color_restoration_info': color_info,
            'depth_info': depth_info,
            'fisheye_info': fisheye_info,
            'steps': steps
        }
        
        return result, info
