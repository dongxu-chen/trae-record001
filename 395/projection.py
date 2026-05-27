import cv2
import numpy as np
from typing import Tuple


class ImageProjector:
    def __init__(self, focal_length: float = None):
        self.focal_length = focal_length

    def _estimate_focal_length(self, img_shape: Tuple[int, int]) -> float:
        h, w = img_shape[:2]
        return max(w, h) / 2.0

    def cylindrical_projection(self, img: np.ndarray) -> np.ndarray:
        h, w = img.shape[:2]
        f = self.focal_length if self.focal_length else self._estimate_focal_length(img.shape)
        
        x_c = w / 2
        y_c = h / 2
        
        y_coords, x_coords = np.mgrid[0:h, 0:w]
        
        theta = (x_coords - x_c) / f
        h_coords = (y_coords - y_c) / f
        
        x_proj = f * np.sin(theta)
        y_proj = f * h_coords
        z_proj = f * np.cos(theta)
        
        x_map = (x_proj * f / z_proj + x_c).astype(np.float32)
        y_map = (y_proj * f / z_proj + y_c).astype(np.float32)
        
        mask = (x_map >= 0) & (x_map < w) & (y_map >= 0) & (y_map < h)
        x_map[~mask] = -1
        y_map[~mask] = -1
        
        warped = cv2.remap(img, x_map, y_map, cv2.INTER_LINEAR,
                          borderMode=cv2.BORDER_CONSTANT)
        return warped

    def spherical_projection(self, img: np.ndarray) -> np.ndarray:
        h, w = img.shape[:2]
        f = self.focal_length if self.focal_length else self._estimate_focal_length(img.shape)
        
        x_c = w / 2
        y_c = h / 2
        
        y_coords, x_coords = np.mgrid[0:h, 0:w]
        
        theta = (x_coords - x_c) / f
        phi = (y_coords - y_c) / f
        
        x_proj = f * np.sin(theta) * np.cos(phi)
        y_proj = f * np.sin(phi)
        z_proj = f * np.cos(theta) * np.cos(phi)
        
        x_map = (x_proj * f / z_proj + x_c).astype(np.float32)
        y_map = (y_proj * f / z_proj + y_c).astype(np.float32)
        
        mask = (x_map >= 0) & (x_map < w) & (y_map >= 0) & (y_map < h)
        x_map[~mask] = -1
        y_map[~mask] = -1
        
        warped = cv2.remap(img, x_map, y_map, cv2.INTER_LINEAR,
                          borderMode=cv2.BORDER_CONSTANT)
        return warped

    def project_images(self, images: list, projection_type: str = 'cylindrical') -> list:
        projected = []
        for img in images:
            if projection_type == 'cylindrical':
                projected.append(self.cylindrical_projection(img))
            elif projection_type == 'spherical':
                projected.append(self.spherical_projection(img))
            else:
                projected.append(img)
        return projected

    def inverse_cylindrical_point(self, x: float, y: float,
                                  img_shape: Tuple[int, int]) -> Tuple[float, float]:
        h, w = img_shape[:2]
        f = self.focal_length if self.focal_length else self._estimate_focal_length(img_shape)
        x_c = w / 2
        y_c = h / 2
        
        theta = np.arcsin((x - x_c) / f)
        x_orig = f * theta + x_c
        y_orig = y
        
        return x_orig, y_orig
