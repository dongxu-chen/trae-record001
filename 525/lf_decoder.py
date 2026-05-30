import numpy as np
import cv2
from typing import Tuple, Optional


class LightFieldDecoder:
    def __init__(self, lenslet_pitch: float = 16.0, pattern: str = 'hexagonal'):
        self.lenslet_pitch = lenslet_pitch
        self.pattern = pattern
        self.lenslet_centers = None
        self.image_size = None
        self.num_lenses_x = 0
        self.num_lenses_y = 0
        
    def detect_lenslet_array(self, raw_image: np.ndarray) -> Tuple[np.ndarray, int, int]:
        if len(raw_image.shape) == 3:
            gray = cv2.cvtColor(raw_image, cv2.COLOR_BGR2GRAY)
        else:
            gray = raw_image.copy()
        
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        
        thresh = cv2.adaptiveThreshold(
            blurred, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
            cv2.THRESH_BINARY_INV, 11, 2
        )
        
        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        centers = []
        for contour in contours:
            M = cv2.moments(contour)
            if M['m00'] > 0:
                cx = int(M['m10'] / M['m00'])
                cy = int(M['m01'] / M['m00'])
                centers.append([cx, cy])
        
        centers = np.array(centers)
        
        if len(centers) > 100:
            self.lenslet_centers = centers
            self.num_lenses_x = len(np.unique(centers[:, 0]))
            self.num_lenses_y = len(np.unique(centers[:, 1]))
            self.image_size = raw_image.shape[:2]
        else:
            self._generate_grid_centers(raw_image.shape)
        
        return self.lenslet_centers, self.num_lenses_x, self.num_lenses_y
    
    def _generate_grid_centers(self, image_shape: Tuple[int, int]):
        h, w = image_shape[:2]
        pitch = int(self.lenslet_pitch)
        
        x_coords = np.arange(pitch // 2, w - pitch // 2, pitch)
        y_coords = np.arange(pitch // 2, h - pitch // 2, pitch)
        
        centers = []
        for y in y_coords:
            for x in x_coords:
                centers.append([x, y])
        
        self.lenslet_centers = np.array(centers)
        self.num_lenses_x = len(x_coords)
        self.num_lenses_y = len(y_coords)
        self.image_size = (h, w)
    
    def extract_subaperture_images(self, raw_image: np.ndarray, 
                                    num_views_x: int = 9, 
                                    num_views_y: int = 9) -> np.ndarray:
        if self.lenslet_centers is None:
            self.detect_lenslet_array(raw_image)
        
        h, w = raw_image.shape[:2]
        half_pitch = int(self.lenslet_pitch // 2)
        
        center_x = num_views_x // 2
        center_y = num_views_y // 2
        
        subapertures = np.zeros(
            (num_views_y, num_views_x, h, w, 3) if len(raw_image.shape) == 3 
            else (num_views_y, num_views_x, h, w),
            dtype=np.uint8
        )
        
        step = self.lenslet_pitch / max(num_views_x, num_views_y)
        
        for vy in range(num_views_y):
            for vx in range(num_views_x):
                offset_x = (vx - center_x) * step
                offset_y = (vy - center_y) * step
                
                shifted = self._shift_and_integrate(raw_image, offset_x, offset_y, half_pitch)
                subapertures[vy, vx] = shifted
        
        return subapertures
    
    def _shift_and_integrate(self, image: np.ndarray, 
                              offset_x: float, offset_y: float, 
                              radius: int) -> np.ndarray:
        h, w = image.shape[:2]
        result = np.zeros_like(image, dtype=np.float32)
        count = np.zeros((h, w), dtype=np.float32)
        
        for center in self.lenslet_centers:
            cx, cy = center
            src_x = int(cx + offset_x)
            src_y = int(cy + offset_y)
            
            x1 = max(0, cx - radius)
            x2 = min(w, cx + radius)
            y1 = max(0, cy - radius)
            y2 = min(h, cy + radius)
            
            src_x1 = max(0, src_x - radius)
            src_x2 = min(w, src_x + radius)
            src_y1 = max(0, src_y - radius)
            src_y2 = min(h, src_y + radius)
            
            dx1 = x1 - (cx - radius)
            dx2 = (cx + radius) - x2
            dy1 = y1 - (cy - radius)
            dy2 = (cy + radius) - y2
            
            patch = image[src_y1:src_y2, src_x1:src_x2]
            result[y1:y2, x1:x2] += patch
            count[y1:y2, x1:x2] += 1
        
        count[count == 0] = 1
        if len(image.shape) == 3:
            result = result / count[:, :, np.newaxis]
        else:
            result = result / count
        
        return np.clip(result, 0, 255).astype(np.uint8)
    
    def decode_raw_lightfield(self, raw_image: np.ndarray, 
                               num_views: int = 9) -> np.ndarray:
        if self.pattern == 'hexagonal':
            return self._decode_hexagonal(raw_image, num_views)
        else:
            return self._decode_rectangular(raw_image, num_views)
    
    def _decode_rectangular(self, raw_image: np.ndarray, num_views: int) -> np.ndarray:
        h, w = raw_image.shape[:2]
        pitch = int(self.lenslet_pitch)
        
        num_lenses_x = w // pitch
        num_lenses_y = h // pitch
        
        sub_h = pitch
        sub_w = pitch
        
        lf_data = np.zeros(
            (num_views, num_views, num_lenses_y, num_lenses_x, 3) 
            if len(raw_image.shape) == 3 
            else (num_views, num_views, num_lenses_y, num_lenses_x),
            dtype=np.uint8
        )
        
        step = pitch // num_views
        half_v = num_views // 2
        
        for ly in range(num_lenses_y):
            for lx in range(num_lenses_x):
                lens_y = ly * pitch + pitch // 2
                lens_x = lx * pitch + pitch // 2
                
                for vy in range(num_views):
                    for vx in range(num_views):
                        py = lens_y + (vy - half_v) * step
                        px = lens_x + (vx - half_v) * step
                        
                        if 0 <= py < h and 0 <= px < w:
                            lf_data[vy, vx, ly, lx] = raw_image[int(py), int(px)]
        
        return lf_data
    
    def _decode_hexagonal(self, raw_image: np.ndarray, num_views: int) -> np.ndarray:
        return self._decode_rectangular(raw_image, num_views)
    
    def get_epipolar_image(self, lf_data: np.ndarray, 
                            y_idx: Optional[int] = None,
                            view_row: int = 0) -> np.ndarray:
        if y_idx is None:
            y_idx = lf_data.shape[2] // 2
        
        epi = lf_data[view_row, :, y_idx, :, :]
        epi = np.transpose(epi, (1, 0, 2))
        
        return epi
    
    def calibrate_from_checkerboard(self, calibration_images: list, 
                                      grid_size: Tuple[int, int] = (9, 6)):
        objp = np.zeros((grid_size[0] * grid_size[1], 3), np.float32)
        objp[:, :2] = np.mgrid[0:grid_size[0], 0:grid_size[1]].T.reshape(-1, 2)
        
        objpoints = []
        imgpoints = []
        
        for img in calibration_images:
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if len(img.shape) == 3 else img
            ret, corners = cv2.findChessboardCorners(gray, grid_size, None)
            
            if ret:
                objpoints.append(objp)
                imgpoints.append(corners)
        
        if len(objpoints) > 0:
            ret, mtx, dist, rvecs, tvecs = cv2.calibrateCamera(
                objpoints, imgpoints, gray.shape[::-1], None, None
            )
            return mtx, dist
        
        return None, None


def create_synthetic_lightfield(image_path: str, 
                                 num_views: int = 9,
                                 disparity: float = 5.0) -> np.ndarray:
    img = cv2.imread(image_path)
    if img is None:
        raise ValueError(f"Cannot load image from {image_path}")
    
    h, w = img.shape[:2]
    lf_data = np.zeros((num_views, num_views, h, w, 3), dtype=np.uint8)
    
    half_v = num_views // 2
    
    for vy in range(num_views):
        for vx in range(num_views):
            dx = (vx - half_v) * disparity
            dy = (vy - half_v) * disparity
            
            M = np.float32([[1, 0, dx], [0, 1, dy]])
            shifted = cv2.warpAffine(img, M, (w, h), borderMode=cv2.BORDER_REPLICATE)
            lf_data[vy, vx] = shifted
    
    return lf_data


def create_gradient_lightfield(size: Tuple[int, int] = (256, 256),
                                num_views: int = 9,
                                num_lenses: int = 32) -> np.ndarray:
    h, w = size
    lf_data = np.zeros((num_views, num_views, num_lenses, num_lenses, 3), dtype=np.uint8)
    
    for vy in range(num_views):
        for vx in range(num_views):
            for ly in range(num_lenses):
                for lx in range(num_lenses):
                    r = int(255 * ly / num_lenses)
                    g = int(255 * lx / num_lenses)
                    b = int(255 * (vx + vy) / (2 * num_views))
                    lf_data[vy, vx, ly, lx] = [b, g, r]
    
    return lf_data
