import numpy as np
import cv2
from typing import Tuple, Optional


class ThermalColorMapper:
    def __init__(self, colormap: str = 'jet'):
        self.colormap = colormap
        self.colormaps = {
            'jet': cv2.COLORMAP_JET,
            'hot': cv2.COLORMAP_HOT,
            'inferno': cv2.COLORMAP_INFERNO,
            'plasma': cv2.COLORMAP_PLASMA,
            'magma': cv2.COLORMAP_MAGMA,
            'turbo': cv2.COLORMAP_TURBO,
            'ironbow': self._ironbow_colormap,
            'rainbow': cv2.COLORMAP_RAINBOW
        }
    
    def _ironbow_colormap(self, img_gray: np.ndarray) -> np.ndarray:
        img_norm = img_gray.astype(np.float32) / 255.0
        
        colormap = np.zeros((256, 3), dtype=np.uint8)
        for i in range(256):
            val = i / 255.0
            if val < 0.25:
                r = 0
                g = 0
                b = int(val * 4 * 255)
            elif val < 0.5:
                r = 0
                g = int((val - 0.25) * 4 * 255)
                b = 255
            elif val < 0.75:
                r = int((val - 0.5) * 4 * 255)
                g = 255
                b = int((0.75 - val) * 4 * 255)
            else:
                r = 255
                g = int((1 - val) * 4 * 255)
                b = 0
            colormap[i] = [b, g, r]
        
        return colormap[img_gray]
    
    def apply_colormap(self, 
                       img_gray: np.ndarray, 
                       enhance_contrast: bool = True,
                       temperature_range: Optional[Tuple[float, float]] = None) -> np.ndarray:
        if img_gray.ndim == 3:
            img_gray = img_gray.squeeze()
        
        if img_gray.max() <= 1.0:
            img_gray = (img_gray * 255).astype(np.uint8)
        
        if temperature_range is not None:
            min_temp, max_temp = temperature_range
            img_gray = np.clip(img_gray, min_temp, max_temp)
            img_gray = ((img_gray - min_temp) / (max_temp - min_temp) * 255).astype(np.uint8)
        
        if enhance_contrast:
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
            img_gray = clahe.apply(img_gray)
        
        if callable(self.colormaps[self.colormap]):
            return self.colormaps[self.colormap](img_gray)
        else:
            return cv2.applyColorMap(img_gray, self.colormaps[self.colormap])


class ThermalEnhancer:
    def __init__(self, colormap: str = 'jet'):
        self.color_mapper = ThermalColorMapper(colormap)
    
    def enhance(self, 
                sr_image: np.ndarray,
                lr_image: Optional[np.ndarray] = None,
                hr_image: Optional[np.ndarray] = None,
                colormap: Optional[str] = None,
                enhance_contrast: bool = True,
                show_temperature_scale: bool = True,
                temperature_range: Optional[Tuple[float, float]] = None) -> np.ndarray:
        if colormap is not None:
            self.color_mapper.colormap = colormap
        
        sr_color = self.color_mapper.apply_colormap(
            sr_image, 
            enhance_contrast=enhance_contrast,
            temperature_range=temperature_range
        )
        
        if show_temperature_scale:
            sr_color = self._add_temperature_scale(sr_color, temperature_range)
        
        if lr_image is not None and hr_image is not None:
            comparison = self._create_comparison_view(lr_image, sr_image, hr_image)
            return comparison, sr_color
        
        return sr_color
    
    def _add_temperature_scale(self, 
                                img_color: np.ndarray, 
                                temperature_range: Optional[Tuple[float, float]] = None) -> np.ndarray:
        h, w = img_color.shape[:2]
        scale_width = 30
        scale_margin = 10
        
        scale_img = np.zeros((h, scale_width, 3), dtype=np.uint8)
        for i in range(h):
            val = int(255 - (i / h) * 255)
            scale_img[i, :] = self.color_mapper.apply_colormap(
                np.array([[val]], dtype=np.uint8), 
                enhance_contrast=False
            )[0, 0]
        
        result = np.zeros((h, w + scale_width + scale_margin, 3), dtype=np.uint8)
        result[:, :w] = img_color
        result[:, w + scale_margin:] = scale_img
        
        if temperature_range is not None:
            min_temp, max_temp = temperature_range
            font = cv2.FONT_HERSHEY_SIMPLEX
            cv2.putText(result, f'{max_temp:.1f}°', (w + scale_margin + scale_width + 5, 15),
                       font, 0.4, (255, 255, 255), 1)
            cv2.putText(result, f'{min_temp:.1f}°', (w + scale_margin + scale_width + 5, h - 5),
                       font, 0.4, (255, 255, 255), 1)
        
        return result
    
    def _create_comparison_view(self, 
                                 lr_image: np.ndarray,
                                 sr_image: np.ndarray,
                                 hr_image: np.ndarray) -> np.ndarray:
        if lr_image.ndim == 3:
            lr_image = lr_image.squeeze()
        if sr_image.ndim == 3:
            sr_image = sr_image.squeeze()
        if hr_image.ndim == 3:
            hr_image = hr_image.squeeze()
        
        if lr_image.max() <= 1.0:
            lr_image = (lr_image * 255).astype(np.uint8)
            sr_image = (sr_image * 255).astype(np.uint8)
            hr_image = (hr_image * 255).astype(np.uint8)
        
        lr_color = self.color_mapper.apply_colormap(lr_image, enhance_contrast=True)
        sr_color = self.color_mapper.apply_colormap(sr_image, enhance_contrast=True)
        hr_color = self.color_mapper.apply_colormap(hr_image, enhance_contrast=True)
        
        h, w = hr_color.shape[:2]
        lr_color = cv2.resize(lr_color, (w, h), interpolation=cv2.INTER_NEAREST)
        
        comparison = np.hstack([lr_color, sr_color, hr_color])
        
        font = cv2.FONT_HERSHEY_SIMPLEX
        cv2.putText(comparison, 'LR Input', (10, 20), font, 0.6, (255, 255, 255), 2)
        cv2.putText(comparison, 'SR Output', (w + 10, 20), font, 0.6, (255, 255, 255), 2)
        cv2.putText(comparison, 'HR Ground Truth', (2 * w + 10, 20), font, 0.6, (255, 255, 255), 2)
        
        return comparison


def create_thermal_heatmap(image: np.ndarray, 
                            colormap: str = 'jet',
                            enhance_contrast: bool = True) -> np.ndarray:
    enhancer = ThermalEnhancer(colormap)
    return enhancer.enhance(image, enhance_contrast=enhance_contrast)


def batch_thermal_enhance(input_dir: str, 
                           output_dir: str,
                           colormap: str = 'jet',
                           enhance_contrast: bool = True) -> None:
    import os
    from tqdm import tqdm
    
    enhancer = ThermalEnhancer(colormap)
    os.makedirs(output_dir, exist_ok=True)
    
    image_files = sorted([f for f in os.listdir(input_dir) 
                         if f.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.tiff'))])
    
    for img_file in tqdm(image_files, desc="Thermal Enhancement"):
        img_path = os.path.join(input_dir, img_file)
        img = cv2.imread(img_path, cv2.IMREAD_GRAYSCALE)
        
        enhanced = enhancer.enhance(img, enhance_contrast=enhance_contrast)
        
        save_path = os.path.join(output_dir, f'heatmap_{img_file}')
        cv2.imwrite(save_path, enhanced)
