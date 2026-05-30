import numpy as np
import cv2
from pathlib import Path
from typing import Tuple, List, Optional
from scipy.ndimage import sobel, gaussian_filter


class LightField:
    def __init__(self, images: np.ndarray, focal_length: float = 1.0, baseline: float = 1.0):
        if images.ndim != 4:
            raise ValueError("Light field images must be 4D: (num_rows, num_cols, height, width)")
        
        self.images = images
        self.num_rows = images.shape[0]
        self.num_cols = images.shape[1]
        self.height = images.shape[2]
        self.width = images.shape[3]
        self.focal_length = focal_length
        self.baseline = baseline
        
    @classmethod
    def from_directory(cls, directory: str, pattern: str = "*.png", 
                       grid_shape: Tuple[int, int] = None) -> 'LightField':
        dir_path = Path(directory)
        image_files = sorted(dir_path.glob(pattern))
        
        if not image_files:
            raise ValueError(f"No images found in {directory} with pattern {pattern}")
        
        sample_img = cv2.imread(str(image_files[0]), cv2.IMREAD_GRAYSCALE)
        if sample_img is None:
            raise ValueError(f"Could not read image: {image_files[0]}")
        
        height, width = sample_img.shape
        
        if grid_shape is None:
            n = int(np.sqrt(len(image_files)))
            grid_shape = (n, n)
        
        num_rows, num_cols = grid_shape
        images = np.zeros((num_rows, num_cols, height, width), dtype=np.float32)
        
        for idx, img_file in enumerate(image_files[:num_rows * num_cols]):
            row = idx // num_cols
            col = idx % num_cols
            img = cv2.imread(str(img_file), cv2.IMREAD_GRAYSCALE)
            if img is not None:
                images[row, col] = img.astype(np.float32) / 255.0
        
        return cls(images)
    
    @classmethod
    def generate_synthetic(cls, num_rows: int = 5, num_cols: int = 5, 
                           height: int = 256, width: int = 256,
                           num_depths: int = 3) -> 'LightField':
        images = np.zeros((num_rows, num_cols, height, width), dtype=np.float32)
        
        depth_layers = np.linspace(0.2, 0.8, num_depths)
        centers = [(0.3, 0.3), (0.7, 0.5), (0.5, 0.7)]
        radii = [0.15, 0.12, 0.18]
        intensities = [0.9, 0.7, 0.85]
        
        center_row = (num_rows - 1) / 2.0
        center_col = (num_cols - 1) / 2.0
        
        y, x = np.mgrid[0:height, 0:width]
        y_norm = y / height
        x_norm = x / width
        
        for r in range(num_rows):
            for c in range(num_cols):
                dr = (r - center_row) / num_rows
                dc = (c - center_col) / num_cols
                
                img = np.full((height, width), 0.1, dtype=np.float32)
                
                for depth, (cx, cy), radius, intensity in zip(depth_layers, centers, radii, intensities):
                    shift_x = dc * (1.0 - depth) * width * 0.3
                    shift_y = dr * (1.0 - depth) * height * 0.3
                    
                    cx_pixel = cx * width + shift_x
                    cy_pixel = cy * height + shift_y
                    
                    dist = np.sqrt((x_norm - cx_pixel/width)**2 + (y_norm - cy_pixel/height)**2)
                    mask = dist < radius
                    img[mask] = intensity
                
                noise = np.random.normal(0, 0.02, img.shape)
                images[r, c] = np.clip(img + noise, 0, 1)
        
        return cls(images)
    
    def get_view(self, row: int, col: int) -> np.ndarray:
        return self.images[row, col]
    
    def get_center_view(self) -> np.ndarray:
        center_row = self.num_rows // 2
        center_col = self.num_cols // 2
        return self.images[center_row, center_col]
    
    def get_epi(self, fixed_row: int, fixed_y: int) -> np.ndarray:
        return self.images[fixed_row, :, fixed_y, :]
    
    def extract_patch(self, row: int, col: int, y: int, x: int, 
                      patch_size: int = 7) -> np.ndarray:
        half = patch_size // 2
        y_start = max(0, y - half)
        y_end = min(self.height, y + half + 1)
        x_start = max(0, x - half)
        x_end = min(self.width, x + half + 1)
        return self.images[row, col, y_start:y_end, x_start:x_end]
    
    def to_color(self, image: np.ndarray) -> np.ndarray:
        return cv2.cvtColor((image * 255).astype(np.uint8), cv2.COLOR_GRAY2BGR)

    def compute_gradient_density(self, block_size: int = 8,
                                  low_texture_threshold: float = 0.02) -> Tuple[np.ndarray, np.ndarray]:
        center_view = self.get_center_view()
        grad_y = sobel(center_view, axis=0)
        grad_x = sobel(center_view, axis=1)
        grad_mag = np.sqrt(grad_y ** 2 + grad_x ** 2)

        h_blocks = self.height // block_size
        w_blocks = self.width // block_size
        density_map = np.zeros((self.height, self.width), dtype=np.float32)

        for by in range(h_blocks):
            for bx in range(w_blocks):
                y0 = by * block_size
                y1 = y0 + block_size
                x0 = bx * block_size
                x1 = x0 + block_size
                block_grad = grad_mag[y0:y1, x0:x1]
                density_map[y0:y1, x0:x1] = np.mean(block_grad)

        pad_h = self.height - h_blocks * block_size
        pad_w = self.width - w_blocks * block_size
        if pad_h > 0:
            last_row = density_map[h_blocks * block_size - 1, :]
            density_map[h_blocks * block_size:, :] = np.tile(last_row, (pad_h, 1))
        if pad_w > 0:
            last_col = density_map[:, w_blocks * block_size - 1]
            density_map[:, w_blocks * block_size:] = np.tile(last_col.reshape(-1, 1), (1, pad_w))

        density_map = gaussian_filter(density_map, sigma=block_size)

        max_density = density_map.max()
        if max_density > 0:
            density_map = density_map / max_density

        low_texture_mask = density_map < low_texture_threshold

        return density_map, low_texture_mask
