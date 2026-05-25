import numpy as np
import cv2
import json
import os
from typing import Optional, Tuple, List, Dict
from dataclasses import dataclass, field


@dataclass
class CameraCalibrationConfig:
    fx: float = 525.0
    fy: float = 525.0
    cx: Optional[float] = None
    cy: Optional[float] = None
    image_width: int = 640
    image_height: int = 480
    distortion_coeffs: Optional[List[float]] = None
    depth_scale: float = 1.0
    min_metric_depth: float = 0.1
    max_metric_depth: float = 10.0
    calibration_file: Optional[str] = None
    apply_undistortion: bool = True


class CameraCalibrator:
    def __init__(self, config: CameraCalibrationConfig):
        self.config = config
        self.intrinsics = None
        self.distortion = None
        self._load_calibration()
    
    def _load_calibration(self):
        if self.config.calibration_file and os.path.exists(self.config.calibration_file):
            self._load_from_file(self.config.calibration_file)
        else:
            self._init_default_intrinsics()
    
    def _init_default_intrinsics(self):
        w = self.config.image_width
        h = self.config.image_height
        
        fx = self.config.fx
        fy = self.config.fy
        cx = self.config.cx if self.config.cx is not None else w / 2.0
        cy = self.config.cy if self.config.cy is not None else h / 2.0
        
        self.intrinsics = np.array([
            [fx, 0, cx],
            [0, fy, cy],
            [0, 0, 1]
        ], dtype=np.float64)
        
        if self.config.distortion_coeffs is not None:
            self.distortion = np.array(self.config.distortion_coeffs, dtype=np.float64)
        else:
            self.distortion = np.zeros((1, 5), dtype=np.float64)
        
        self._compute_undistortion_maps()
    
    def _load_from_file(self, filepath: str):
        with open(filepath, 'r') as f:
            calib_data = json.load(f)
        
        self.intrinsics = np.array(calib_data['intrinsics'], dtype=np.float64)
        self.distortion = np.array(calib_data.get('distortion', [0, 0, 0, 0, 0]), dtype=np.float64)
        
        self.config.fx = self.intrinsics[0, 0]
        self.config.fy = self.intrinsics[1, 1]
        self.config.cx = self.intrinsics[0, 2]
        self.config.cy = self.intrinsics[1, 2]
        
        self._compute_undistortion_maps()
    
    def _compute_undistortion_maps(self):
        w = self.config.image_width
        h = self.config.image_height
        
        self.map_x, self.map_y = cv2.initUndistortRectifyMap(
            self.intrinsics,
            self.distortion,
            None,
            self.intrinsics,
            (w, h),
            cv2.CV_32FC1
        )
    
    def undistort_image(self, image: np.ndarray) -> np.ndarray:
        if not self.config.apply_undistortion:
            return image.copy()
        
        if len(image.shape) == 2:
            return cv2.remap(image, self.map_x, self.map_y, cv2.INTER_LINEAR)
        else:
            return cv2.remap(image, self.map_x, self.map_y, cv2.INTER_LINEAR)
    
    def undistort_depth(self, depth_map: np.ndarray) -> np.ndarray:
        return self.undistort_image(depth_map)
    
    def pixel_to_metric(self, depth_map: np.ndarray) -> np.ndarray:
        return depth_map * self.config.depth_scale
    
    def metric_to_pixel(self, depth_map: np.ndarray) -> np.ndarray:
        return depth_map / self.config.depth_scale
    
    def relative_to_metric(self, relative_depth: np.ndarray, 
                           reference_distance: float = 1.0,
                           reference_point: Optional[Tuple[int, int]] = None) -> np.ndarray:
        if reference_point is not None:
            px, py = reference_point
            if 0 <= px < relative_depth.shape[1] and 0 <= py < relative_depth.shape[0]:
                rel_val = relative_depth[py, px]
                if rel_val > 0:
                    scale = reference_distance / rel_val
                else:
                    scale = reference_distance
            else:
                scale = reference_distance
        else:
            mask = (relative_depth > 0) & np.isfinite(relative_depth)
            if np.any(mask):
                median_rel = np.median(relative_depth[mask])
                scale = reference_distance / median_rel if median_rel > 0 else 1.0
            else:
                scale = 1.0
        
        metric_depth = relative_depth * scale
        metric_depth = np.clip(metric_depth, 
                              self.config.min_metric_depth, 
                              self.config.max_metric_depth)
        
        return metric_depth
    
    def backproject_to_3d(self, u: int, v: int, depth: float) -> np.ndarray:
        fx = self.intrinsics[0, 0]
        fy = self.intrinsics[1, 1]
        cx = self.intrinsics[0, 2]
        cy = self.intrinsics[1, 2]
        
        x = (u - cx) * depth / fx
        y = (v - cy) * depth / fy
        z = depth
        
        return np.array([x, y, z])
    
    def project_to_pixel(self, point_3d: np.ndarray) -> Tuple[int, int]:
        if point_3d[2] <= 0:
            return -1, -1
        
        fx = self.intrinsics[0, 0]
        fy = self.intrinsics[1, 1]
        cx = self.intrinsics[0, 2]
        cy = self.intrinsics[1, 2]
        
        u = int(round(point_3d[0] * fx / point_3d[2] + cx))
        v = int(round(point_3d[1] * fy / point_3d[2] + cy))
        
        return u, v
    
    def backproject_depth_map(self, depth_map: np.ndarray) -> np.ndarray:
        h, w = depth_map.shape
        
        fx = self.intrinsics[0, 0]
        fy = self.intrinsics[1, 1]
        cx = self.intrinsics[0, 2]
        cy = self.intrinsics[1, 2]
        
        u_coords, v_coords = np.meshgrid(np.arange(w), np.arange(h))
        
        valid_mask = (depth_map > 0) & np.isfinite(depth_map)
        
        x = (u_coords - cx) * depth_map / fx
        y = (v_coords - cy) * depth_map / fy
        z = depth_map
        
        points_3d = np.stack([x, y, z], axis=-1)
        
        return points_3d, valid_mask
    
    def calibrate_from_chessboard(self, 
                                   images: List[np.ndarray],
                                   chessboard_size: Tuple[int, int] = (9, 6),
                                   square_size: float = 0.025) -> Dict:
        objp = np.zeros((chessboard_size[0] * chessboard_size[1], 3), np.float32)
        objp[:, :2] = np.mgrid[0:chessboard_size[0], 0:chessboard_size[1]].T.reshape(-1, 2)
        objp *= square_size
        
        objpoints = []
        imgpoints = []
        
        for img in images:
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            ret, corners = cv2.findChessboardCorners(gray, chessboard_size, None)
            
            if ret:
                objpoints.append(objp)
                corners_refined = cv2.cornerSubPix(
                    gray, corners, (11, 11), (-1, -1),
                    (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 0.001)
                )
                imgpoints.append(corners_refined)
        
        if len(objpoints) < 10:
            raise RuntimeError(f"Need at least 10 valid images, got {len(objpoints)}")
        
        h, w = gray.shape
        ret, mtx, dist, rvecs, tvecs = cv2.calibrateCamera(
            objpoints, imgpoints, (w, h), None, None
        )
        
        self.intrinsics = mtx
        self.distortion = dist
        self.config.fx = mtx[0, 0]
        self.config.fy = mtx[1, 1]
        self.config.cx = mtx[0, 2]
        self.config.cy = mtx[1, 2]
        
        self._compute_undistortion_maps()
        
        return {
            'rms_error': ret,
            'num_images': len(objpoints),
            'intrinsics': mtx.tolist(),
            'distortion': dist.ravel().tolist()
        }
    
    def save_calibration(self, filepath: str):
        calib_data = {
            'intrinsics': self.intrinsics.tolist(),
            'distortion': self.distortion.ravel().tolist(),
            'fx': float(self.intrinsics[0, 0]),
            'fy': float(self.intrinsics[1, 1]),
            'cx': float(self.intrinsics[0, 2]),
            'cy': float(self.intrinsics[1, 2]),
            'image_width': self.config.image_width,
            'image_height': self.config.image_height
        }
        
        with open(filepath, 'w') as f:
            json.dump(calib_data, f, indent=4)
        
        print(f"Calibration saved to {filepath}")
    
    def get_intrinsics_matrix(self) -> np.ndarray:
        return self.intrinsics.copy()
    
    def get_distortion_coeffs(self) -> np.ndarray:
        return self.distortion.copy()
    
    def get_focal_lengths(self) -> Tuple[float, float]:
        return float(self.intrinsics[0, 0]), float(self.intrinsics[1, 1])
    
    def get_principal_point(self) -> Tuple[float, float]:
        return float(self.intrinsics[0, 2]), float(self.intrinsics[1, 2])


class DepthConverter:
    def __init__(self, calibrator: CameraCalibrator):
        self.calibrator = calibrator
    
    def relative_to_metric_depth(self, 
                                  relative_depth: np.ndarray,
                                  method: str = 'median',
                                  reference_distance: Optional[float] = None,
                                  reference_point: Optional[Tuple[int, int]] = None) -> np.ndarray:
        if method == 'point' and reference_point is not None and reference_distance is not None:
            return self.calibrator.relative_to_metric(
                relative_depth, reference_distance, reference_point
            )
        elif method == 'median':
            return self._median_scale_conversion(relative_depth, reference_distance)
        elif method == 'minmax':
            return self._minmax_scale_conversion(relative_depth, reference_distance)
        else:
            return relative_depth
    
    def _median_scale_conversion(self, 
                                  relative_depth: np.ndarray,
                                  reference_distance: Optional[float] = None) -> np.ndarray:
        mask = (relative_depth > 0) & np.isfinite(relative_depth)
        
        if not np.any(mask):
            return np.clip(relative_depth, 
                          self.calibrator.config.min_metric_depth,
                          self.calibrator.config.max_metric_depth)
        
        median_rel = np.median(relative_depth[mask])
        
        if reference_distance is not None:
            scale = reference_distance / median_rel if median_rel > 0 else 1.0
        else:
            scale = self.calibrator.config.depth_scale
        
        metric_depth = relative_depth * scale
        metric_depth = np.clip(metric_depth,
                              self.calibrator.config.min_metric_depth,
                              self.calibrator.config.max_metric_depth)
        
        return metric_depth
    
    def _minmax_scale_conversion(self,
                                  relative_depth: np.ndarray,
                                  reference_distance: Optional[float] = None) -> np.ndarray:
        mask = (relative_depth > 0) & np.isfinite(relative_depth)
        
        if not np.any(mask):
            return np.clip(relative_depth,
                          self.calibrator.config.min_metric_depth,
                          self.calibrator.config.max_metric_depth)
        
        min_rel = np.min(relative_depth[mask])
        max_rel = np.max(relative_depth[mask])
        
        if reference_distance is not None:
            target_max = reference_distance * 2
            target_min = self.calibrator.config.min_metric_depth
        else:
            target_max = self.calibrator.config.max_metric_depth
            target_min = self.calibrator.config.min_metric_depth
        
        if max_rel > min_rel:
            metric_depth = (relative_depth - min_rel) / (max_rel - min_rel)
            metric_depth = metric_depth * (target_max - target_min) + target_min
        else:
            metric_depth = np.full_like(relative_depth, target_min)
        
        metric_depth = np.clip(metric_depth,
                              self.calibrator.config.min_metric_depth,
                              self.calibrator.config.max_metric_depth)
        
        return metric_depth
    
    def get_depth_value_at_point(self, 
                                  depth_map: np.ndarray,
                                  u: int, v: int) -> float:
        if 0 <= v < depth_map.shape[0] and 0 <= u < depth_map.shape[1]:
            return float(depth_map[v, u])
        return 0.0
    
    def get_3d_point_at_pixel(self, 
                               depth_map: np.ndarray,
                               u: int, v: int) -> Optional[np.ndarray]:
        depth = self.get_depth_value_at_point(depth_map, u, v)
        if depth > 0 and np.isfinite(depth):
            return self.calibrator.backproject_to_3d(u, v, depth)
        return None
