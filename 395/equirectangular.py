import cv2
import numpy as np
from typing import Tuple, List, Optional


class EquirectangularProjector:
    def __init__(self, output_width: int = 4096, 
                 output_height: Optional[int] = None):
        self.output_width = output_width
        self.output_height = output_height if output_height else output_width // 2
        
        self.map_x = None
        self.map_y = None
        self._initialize_mapping()

    def _initialize_mapping(self):
        h = self.output_height
        w = self.output_width
        
        y_coords, x_coords = np.mgrid[0:h, 0:w]
        
        lon = (x_coords / w) * 2 * np.pi - np.pi
        lat = (y_coords / h) * np.pi - np.pi / 2
        
        self.map_x = (lon * 180 / np.pi).astype(np.float32)
        self.map_y = (lat * 180 / np.pi).astype(np.float32)

    def spherical_to_equirectangular(self, spherical_image: np.ndarray) -> np.ndarray:
        h, w = spherical_image.shape[:2]
        
        if len(spherical_image.shape) == 3:
            channels = spherical_image.shape[2]
            output = np.zeros((self.output_height, self.output_width, channels), 
                             dtype=np.uint8)
        else:
            output = np.zeros((self.output_height, self.output_width), 
                             dtype=np.uint8)
        
        src_x = self.map_x * w / 360.0 + w / 2
        src_y = (self.map_y + 90) * h / 180.0
        
        src_x = np.clip(src_x, 0, w - 1).astype(np.float32)
        src_y = np.clip(src_y, 0, h - 1).astype(np.float32)
        
        output = cv2.remap(spherical_image, src_x, src_y, cv2.INTER_LINEAR,
                          borderMode=cv2.BORDER_WRAP)
        
        return output

    def equirectangular_to_spherical(self, equirect_img: np.ndarray,
                                     spherical_size: Tuple[int, int]) -> np.ndarray:
        h, w = equirect_img.shape[:2]
        sh, sw = spherical_size
        
        y_coords, x_coords = np.mgrid[0:sh, 0:sw]
        
        lon = (x_coords / sw) * 2 * np.pi - np.pi
        lat = (y_coords / sh) * np.pi - np.pi / 2
        
        src_x = (lon + np.pi) / (2 * np.pi) * w
        src_y = (lat + np.pi / 2) / np.pi * h
        
        src_x = src_x.astype(np.float32)
        src_y = src_y.astype(np.float32)
        
        output = cv2.remap(equirect_img, src_x, src_y, cv2.INTER_LINEAR,
                          borderMode=cv2.BORDER_WRAP)
        
        return output

    def perspective_to_equirectangular(self, perspective_img: np.ndarray,
                                       fov_h: float = 90.0,
                                       fov_v: float = 60.0,
                                       yaw: float = 0.0,
                                       pitch: float = 0.0,
                                       roll: float = 0.0) -> np.ndarray:
        h, w = perspective_img.shape[:2]
        
        fov_h_rad = np.radians(fov_h)
        fov_v_rad = np.radians(fov_v)
        yaw_rad = np.radians(yaw)
        pitch_rad = np.radians(pitch)
        roll_rad = np.radians(roll)
        
        y_coords, x_coords = np.mgrid[0:self.output_height, 0:self.output_width]
        
        lon = (x_coords / self.output_width) * 2 * np.pi - np.pi
        lat = (y_coords / self.output_height) * np.pi - np.pi / 2
        
        x = np.cos(lat) * np.sin(lon)
        y = np.sin(lat)
        z = np.cos(lat) * np.cos(lon)
        
        cos_p, sin_p = np.cos(pitch_rad), np.sin(pitch_rad)
        cos_y, sin_y = np.cos(yaw_rad), np.sin(yaw_rad)
        cos_r, sin_r = np.cos(roll_rad), np.sin(roll_rad)
        
        x1 = x * cos_y - z * sin_y
        y1 = y
        z1 = x * sin_y + z * cos_y
        
        x2 = x1
        y2 = y1 * cos_p - z1 * sin_p
        z2 = y1 * sin_p + z1 * cos_p
        
        x3 = x2 * cos_r - y2 * sin_r
        y3 = x2 * sin_r + y2 * cos_r
        z3 = z2
        
        f_x = w / (2 * np.tan(fov_h_rad / 2))
        f_y = h / (2 * np.tan(fov_v_rad / 2))
        
        valid = z3 > 0.1
        
        src_x = np.where(valid, x3 / z3 * f_x + w / 2, -1)
        src_y = np.where(valid, y3 / z3 * f_y + h / 2, -1)
        
        src_x = src_x.astype(np.float32)
        src_y = src_y.astype(np.float32)
        
        if len(perspective_img.shape) == 3:
            channels = perspective_img.shape[2]
            output = np.zeros((self.output_height, self.output_width, channels), 
                             dtype=np.uint8)
        else:
            output = np.zeros((self.output_height, self.output_width), 
                             dtype=np.uint8)
        
        output = cv2.remap(perspective_img, src_x, src_y, cv2.INTER_LINEAR,
                          borderMode=cv2.BORDER_CONSTANT)
        
        return output

    def stitch_to_equirectangular(self, images: List[np.ndarray],
                                  camera_params: Optional[List[dict]] = None) -> np.ndarray:
        if len(images) == 0:
            raise ValueError('需要至少一张图像')
        
        if camera_params is None:
            camera_params = [{} for _ in range(len(images))]
        
        if len(camera_params) != len(images):
            raise ValueError('相机参数数量必须与图像数量匹配')
        
        result = None
        
        for img, params in zip(images, camera_params):
            equirect = self.perspective_to_equirectangular(img, **params)
            
            if result is None:
                result = equirect
            else:
                mask_equirect = (equirect > 0).any(axis=2) if len(equirect.shape) == 3 else equirect > 0
                mask_result = (result > 0).any(axis=2) if len(result.shape) == 3 else result > 0
                
                result = np.where(mask_equirect[:, :, np.newaxis] if len(result.shape) == 3 
                                  else mask_equirect[:, :, np.newaxis],
                                  equirect, result)
        
        if result is None:
            result = np.zeros((self.output_height, self.output_width, 3), dtype=np.uint8)
        
        return result

    def rotate_equirectangular(self, equirect_img: np.ndarray,
                               yaw: float = 0.0,
                               pitch: float = 0.0,
                               roll: float = 0.0) -> np.ndarray:
        h, w = equirect_img.shape[:2]
        
        yaw_rad = np.radians(yaw)
        pitch_rad = np.radians(pitch)
        roll_rad = np.radians(roll)
        
        y_coords, x_coords = np.mgrid[0:h, 0:w]
        
        lon = (x_coords / w) * 2 * np.pi - np.pi
        lat = (y_coords / h) * np.pi - np.pi / 2
        
        x = np.cos(lat) * np.sin(lon)
        y = np.sin(lat)
        z = np.cos(lat) * np.cos(lon)
        
        cos_p, sin_p = np.cos(pitch_rad), np.sin(pitch_rad)
        cos_y, sin_y = np.cos(yaw_rad), np.sin(yaw_rad)
        cos_r, sin_r = np.cos(roll_rad), np.sin(roll_rad)
        
        x1 = x * cos_y - z * sin_y
        y1 = y
        z1 = x * sin_y + z * cos_y
        
        x2 = x1
        y2 = y1 * cos_p - z1 * sin_p
        z2 = y1 * sin_p + z1 * cos_p
        
        x3 = x2 * cos_r - y2 * sin_r
        y3 = x2 * sin_r + y2 * cos_r
        z3 = z2
        
        lon_new = np.arctan2(x3, z3)
        lat_new = np.arcsin(np.clip(y3, -1, 1))
        
        src_x = (lon_new + np.pi) / (2 * np.pi) * w
        src_y = (lat_new + np.pi / 2) / np.pi * h
        
        src_x = src_x.astype(np.float32)
        src_y = src_y.astype(np.float32)
        
        output = cv2.remap(equirect_img, src_x, src_y, cv2.INTER_LINEAR,
                          borderMode=cv2.BORDER_WRAP)
        
        return output

    def crop_horizon(self, equirect_img: np.ndarray,
                     horizon_ratio: float = 0.5) -> np.ndarray:
        h, w = equirect_img.shape[:2]
        center_y = int(h * horizon_ratio)
        crop_height = min(h, int(w * 0.5))
        
        y_start = max(0, center_y - crop_height // 2)
        y_end = min(h, y_start + crop_height)
        
        return equirect_img[y_start:y_end, :]

    def resize_equirectangular(self, equirect_img: np.ndarray,
                               target_width: int) -> np.ndarray:
        ratio = target_width / equirect_img.shape[1]
        target_height = int(equirect_img.shape[0] * ratio)
        return cv2.resize(equirect_img, (target_width, target_height))

    def get_thumbnail(self, equirect_img: np.ndarray,
                      thumb_width: int = 1024) -> np.ndarray:
        return self.resize_equirectangular(equirect_img, thumb_width)


class Panorama360Stitcher:
    def __init__(self, output_width: int = 4096):
        self.equirect_projector = EquirectangularProjector(output_width=output_width)
        self.camera_calibrator = None
        
    def set_calibration(self, camera_matrix: np.ndarray, 
                        dist_coeffs: np.ndarray):
        from camera_calibration import CameraCalibrator
        self.camera_calibrator = CameraCalibrator()
        self.camera_calibrator.camera_matrix = camera_matrix
        self.camera_calibrator.dist_coeffs = dist_coeffs

    def stitch_360(self, images: List[np.ndarray],
                   angles: Optional[List[float]] = None,
                   fov: Optional[float] = None) -> np.ndarray:
        if len(images) == 0:
            raise ValueError('需要至少一张图像')
        
        if angles is None:
            angle_step = 360.0 / len(images)
            angles = [i * angle_step for i in range(len(images))]
        
        if fov is None:
            fov = 360.0 / len(images) * 1.2
        
        if self.camera_calibrator:
            undistorted = []
            for img in images:
                undistorted.append(self.camera_calibrator.undistort_image(img))
            images = undistorted
        
        camera_params = []
        for angle in angles:
            params = {
                'fov_h': fov,
                'fov_v': fov * 0.6,
                'yaw': angle,
                'pitch': 0.0,
                'roll': 0.0
            }
            camera_params.append(params)
        
        return self.equirect_projector.stitch_to_equirectangular(images, camera_params)

    def blend_360_seams(self, equirect_img: np.ndarray,
                        num_views: int = 6) -> np.ndarray:
        h, w = equirect_img.shape[:2]
        
        seam_width = int(w / num_views * 0.1)
        
        for i in range(num_views):
            seam_x = int(w * i / num_views)
            
            x_start = max(0, seam_x - seam_width)
            x_end = min(w, seam_x + seam_width)
            
            for c in range(3):
                region = equirect_img[:, x_start:x_end, c].astype(np.float32)
                
                blur = cv2.GaussianBlur(region, (seam_width * 2 + 1, 1), 0)
                
                equirect_img[:, x_start:x_end, c] = blur.astype(np.uint8)
        
        return equirect_img

    def generate_360_preview(self, equirect_img: np.ndarray,
                              output_size: Tuple[int, int] = (800, 400)) -> np.ndarray:
        preview = cv2.resize(equirect_img, output_size)
        return preview
