import cv2
import numpy as np
from typing import Dict, Any, Optional, Tuple, List, Union
from dataclasses import dataclass
from enum import Enum


class FillMethod(str, Enum):
    TELEA = 'telea'
    NS = 'navier_stokes'
    POISSON = 'poisson'
    CONTENT_AWARE = 'content_aware'
    SAMPLE = 'sample'


class BlendMode(str, Enum):
    NORMAL = 'normal'
    MULTIPLY = 'multiply'
    SCREEN = 'screen'
    OVERLAY = 'overlay'
    SOFT_LIGHT = 'soft_light'
    ALPHA = 'alpha'


@dataclass
class EditResult:
    original_image: np.ndarray
    edited_image: np.ndarray
    saliency_map: np.ndarray
    binary_mask: np.ndarray
    edit_type: str
    parameters: Dict[str, Any]


class SaliencyInpainter:
    def __init__(self, default_radius: int = 3):
        self.default_radius = default_radius
    
    def inpaint(self, image: np.ndarray, mask: np.ndarray, 
                method: FillMethod = FillMethod.TELEA,
                radius: Optional[int] = None) -> np.ndarray:
        if radius is None:
            radius = self.default_radius
        
        image_uint8 = (image * 255).astype(np.uint8) if image.dtype == np.float32 else image.astype(np.uint8)
        mask_uint8 = (mask * 255).astype(np.uint8) if mask.dtype == np.float32 else mask.astype(np.uint8)
        
        if image_uint8.ndim == 2:
            image_uint8 = cv2.cvtColor(image_uint8, cv2.COLOR_GRAY2BGR)
        elif image_uint8.shape[2] == 4:
            image_uint8 = cv2.cvtColor(image_uint8, cv2.COLOR_BGRA2BGR)
        
        if mask_uint8.ndim == 3:
            mask_uint8 = cv2.cvtColor(mask_uint8, cv2.COLOR_BGR2GRAY)
        
        if method == FillMethod.TELEA:
            result = cv2.inpaint(image_uint8, mask_uint8, radius, cv2.INPAINT_TELEA)
        elif method == FillMethod.NS:
            result = cv2.inpaint(image_uint8, mask_uint8, radius, cv2.INPAINT_NS)
        elif method == FillMethod.POISSON:
            result = self._poisson_inpaint(image_uint8, mask_uint8)
        elif method == FillMethod.CONTENT_AWARE:
            result = self._content_aware_inpaint(image_uint8, mask_uint8)
        elif method == FillMethod.SAMPLE:
            result = self._sample_based_inpaint(image_uint8, mask_uint8)
        else:
            result = cv2.inpaint(image_uint8, mask_uint8, radius, cv2.INPAINT_TELEA)
        
        if image.dtype == np.float32 or image.max() <= 1.0:
            result = result.astype(np.float32) / 255.0
        
        return result
    
    def _poisson_inpaint(self, image: np.ndarray, mask: np.ndarray) -> np.ndarray:
        h, w = image.shape[:2]
        result = image.copy()
        
        mask_binary = (mask > 127).astype(np.uint8)
        
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
        mask_dilated = cv2.dilate(mask_binary, kernel, iterations=2)
        boundary = mask_dilated - mask_binary
        
        for c in range(3):
            channel = image[:, :, c].astype(np.float64)
            result_channel = result[:, :, c].astype(np.float64)
            
            boundary_coords = np.where(boundary > 0)
            for y, x in zip(*boundary_coords):
                if mask_binary[y, x] == 0:
                    result_channel[y, x] = channel[y, x]
            
            for _ in range(100):
                new_result = result_channel.copy()
                mask_coords = np.where(mask_binary > 0)
                for y, x in zip(*mask_coords):
                    neighbors = []
                    if y > 0:
                        neighbors.append(result_channel[y-1, x])
                    if y < h-1:
                        neighbors.append(result_channel[y+1, x])
                    if x > 0:
                        neighbors.append(result_channel[y, x-1])
                    if x < w-1:
                        neighbors.append(result_channel[y, x+1])
                    if neighbors:
                        new_result[y, x] = np.mean(neighbors)
                result_channel = new_result
            
            result[:, :, c] = np.clip(result_channel, 0, 255).astype(np.uint8)
        
        return result
    
    def _content_aware_inpaint(self, image: np.ndarray, mask: np.ndarray) -> np.ndarray:
        h, w = image.shape[:2]
        mask_binary = (mask > 127).astype(np.uint8)
        
        result = image.copy()
        
        y_indices, x_indices = np.where(mask_binary > 0)
        
        if len(y_indices) == 0:
            return result
        
        y_min, y_max = y_indices.min(), y_indices.max()
        x_min, x_max = x_indices.min(), x_indices.max()
        
        region_h = y_max - y_min + 1
        region_w = x_max - x_min + 1
        
        search_margin = max(region_h, region_w)
        
        best_match = None
        best_score = float('inf')
        
        for sy in range(max(0, y_min - search_margin), min(h - region_h, y_max + search_margin), 5):
            for sx in range(max(0, x_min - search_margin), min(w - region_w, x_max + search_margin), 5):
                if mask_binary[sy:sy+region_h, sx:sx+region_w].sum() > 0:
                    continue
                
                sample_region = image[sy:sy+region_h, sx:sx+region_w]
                target_region = image[y_min:y_max+1, x_min:x_max+1]
                target_mask_3ch = np.stack([mask_binary[y_min:y_max+1, x_min:x_max+1]] * 3, axis=2)
                
                diff = np.abs(sample_region.astype(np.float32) - target_region.astype(np.float32))
                diff = diff * (1 - target_mask_3ch.astype(np.float32) / 255)
                score = diff.sum()
                
                if score < best_score:
                    best_score = score
                    best_match = sample_region
        
        if best_match is not None:
            blend_mask = mask_binary[y_min:y_max+1, x_min:x_max+1].astype(np.float32) / 255
            blend_mask = np.stack([blend_mask] * 3, axis=2)
            
            target_original = image[y_min:y_max+1, x_min:x_max+1].astype(np.float32)
            blended = best_match.astype(np.float32) * blend_mask + target_original * (1 - blend_mask)
            result[y_min:y_max+1, x_min:x_max+1] = blended.astype(np.uint8)
        
        return result
    
    def _sample_based_inpaint(self, image: np.ndarray, mask: np.ndarray) -> np.ndarray:
        h, w = image.shape[:2]
        mask_binary = (mask > 127).astype(np.uint8)
        result = image.copy()
        
        mask_coords = np.where(mask_binary > 0)
        non_mask_coords = np.where(mask_binary == 0)
        
        if len(non_mask_coords[0]) == 0:
            return result
        
        for y, x in zip(*mask_coords):
            min_dist = float('inf')
            nearest_color = np.zeros(3, dtype=np.uint8)
            
            for ny, nx in zip(*non_mask_coords):
                dist = (y - ny) ** 2 + (x - nx) ** 2
                if dist < min_dist:
                    min_dist = dist
                    nearest_color = image[ny, nx]
                if min_dist < 100:
                    break
            
            result[y, x] = nearest_color
        
        return result


class ImageEditor:
    def __init__(self):
        self.inpainter = SaliencyInpainter()
    
    def _blend(self, base: np.ndarray, overlay: np.ndarray, mask: np.ndarray,
               mode: BlendMode = BlendMode.ALPHA) -> np.ndarray:
        if base.dtype != np.float32:
            base = base.astype(np.float32) / 255.0
        if overlay.dtype != np.float32:
            overlay = overlay.astype(np.float32) / 255.0
        if mask.dtype != np.float32:
            mask = mask.astype(np.float32)
        
        if mask.ndim == 2:
            mask = np.stack([mask] * 3, axis=2)
        
        if mode == BlendMode.NORMAL:
            result = overlay * mask + base * (1 - mask)
        elif mode == BlendMode.MULTIPLY:
            blended = base * overlay
            result = blended * mask + base * (1 - mask)
        elif mode == BlendMode.SCREEN:
            blended = 1 - (1 - base) * (1 - overlay)
            result = blended * mask + base * (1 - mask)
        elif mode == BlendMode.OVERLAY:
            blended = np.where(base < 0.5, 2 * base * overlay, 1 - 2 * (1 - base) * (1 - overlay))
            result = blended * mask + base * (1 - mask)
        elif mode == BlendMode.SOFT_LIGHT:
            blended = np.where(overlay < 0.5,
                               base - (1 - 2 * overlay) * base * (1 - base),
                               base + (2 * overlay - 1) * (np.sqrt(base) - base))
            result = blended * mask + base * (1 - mask)
        elif mode == BlendMode.ALPHA:
            result = overlay * mask + base * (1 - mask)
        else:
            result = overlay * mask + base * (1 - mask)
        
        return np.clip(result, 0, 1)
    
    def fill_salient_region(self, image: np.ndarray, saliency_map: np.ndarray,
                           binary_mask: Optional[np.ndarray] = None,
                           method: FillMethod = FillMethod.TELEA,
                           threshold: float = 0.5,
                           invert_mask: bool = False,
                           feather: int = 5) -> EditResult:
        if binary_mask is None:
            binary_mask = (saliency_map > threshold).astype(np.float32)
        
        if invert_mask:
            binary_mask = 1 - binary_mask
        
        if feather > 0:
            kernel_size = feather * 2 + 1
            binary_mask = cv2.GaussianBlur(binary_mask, (kernel_size, kernel_size), 0)
        
        mask_uint8 = (binary_mask * 255).astype(np.uint8)
        filled = self.inpainter.inpaint(image, mask_uint8, method=method)
        
        return EditResult(
            original_image=image,
            edited_image=filled,
            saliency_map=saliency_map,
            binary_mask=binary_mask,
            edit_type='fill',
            parameters={'method': method, 'threshold': threshold, 'invert': invert_mask, 'feather': feather}
        )
    
    def blur_salient_region(self, image: np.ndarray, saliency_map: np.ndarray,
                           binary_mask: Optional[np.ndarray] = None,
                           blur_type: str = 'gaussian',
                           kernel_size: int = 25,
                           sigma: float = 0,
                           threshold: float = 0.5,
                           invert_mask: bool = False,
                           feather: int = 5) -> EditResult:
        if binary_mask is None:
            binary_mask = (saliency_map > threshold).astype(np.float32)
        
        if invert_mask:
            binary_mask = 1 - binary_mask
        
        if feather > 0:
            kernel = feather * 2 + 1
            binary_mask = cv2.GaussianBlur(binary_mask, (kernel, kernel), 0)
        
        if blur_type == 'gaussian':
            blurred = cv2.GaussianBlur(image, (kernel_size, kernel_size), sigma)
        elif blur_type == 'median':
            blurred = cv2.medianBlur(image, kernel_size)
        elif blur_type == 'bilateral':
            blurred = cv2.bilateralFilter(image, kernel_size, sigma * 2, sigma)
        elif blur_type == 'motion':
            kernel = np.zeros((kernel_size, kernel_size))
            kernel[int((kernel_size - 1) / 2), :] = np.ones(kernel_size)
            kernel = kernel / kernel_size
            blurred = cv2.filter2D(image, -1, kernel)
        else:
            blurred = cv2.GaussianBlur(image, (kernel_size, kernel_size), sigma)
        
        result = self._blend(image, blurred, binary_mask, mode=BlendMode.ALPHA)
        
        return EditResult(
            original_image=image,
            edited_image=result,
            saliency_map=saliency_map,
            binary_mask=binary_mask,
            edit_type='blur',
            parameters={'blur_type': blur_type, 'kernel_size': kernel_size, 'sigma': sigma, 'threshold': threshold}
        )
    
    def replace_salient_region(self, image: np.ndarray, replacement: np.ndarray,
                              saliency_map: np.ndarray,
                              binary_mask: Optional[np.ndarray] = None,
                              threshold: float = 0.5,
                              invert_mask: bool = False,
                              feather: int = 5,
                              blend_mode: BlendMode = BlendMode.ALPHA) -> EditResult:
        if binary_mask is None:
            binary_mask = (saliency_map > threshold).astype(np.float32)
        
        if invert_mask:
            binary_mask = 1 - binary_mask
        
        if feather > 0:
            kernel = feather * 2 + 1
            binary_mask = cv2.GaussianBlur(binary_mask, (kernel, kernel), 0)
        
        if replacement.shape != image.shape:
            replacement = cv2.resize(replacement, (image.shape[1], image.shape[0]))
        
        result = self._blend(image, replacement, binary_mask, mode=blend_mode)
        
        return EditResult(
            original_image=image,
            edited_image=result,
            saliency_map=saliency_map,
            binary_mask=binary_mask,
            edit_type='replace',
            parameters={'blend_mode': blend_mode, 'threshold': threshold, 'invert': invert_mask}
        )
    
    def adjust_salient_region(self, image: np.ndarray, saliency_map: np.ndarray,
                             binary_mask: Optional[np.ndarray] = None,
                             brightness: float = 1.0,
                             contrast: float = 1.0,
                             saturation: float = 1.0,
                             hue_shift: float = 0.0,
                             threshold: float = 0.5,
                             invert_mask: bool = False,
                             feather: int = 5) -> EditResult:
        if binary_mask is None:
            binary_mask = (saliency_map > threshold).astype(np.float32)
        
        if invert_mask:
            binary_mask = 1 - binary_mask
        
        if feather > 0:
            kernel = feather * 2 + 1
            binary_mask = cv2.GaussianBlur(binary_mask, (kernel, kernel), 0)
        
        adjusted = image.copy().astype(np.float32)
        
        if image.dtype == np.uint8:
            adjusted = adjusted / 255.0
        
        adjusted = adjusted * contrast + (brightness - 1)
        
        if saturation != 1.0 or hue_shift != 0.0:
            hsv = cv2.cvtColor(adjusted, cv2.COLOR_RGB2HSV)
            hsv[:, :, 1] = hsv[:, :, 1] * saturation
            hsv[:, :, 0] = (hsv[:, :, 0] + hue_shift) % 180
            adjusted = cv2.cvtColor(hsv, cv2.COLOR_HSV2RGB)
        
        adjusted = np.clip(adjusted, 0, 1)
        
        mask_3ch = np.stack([binary_mask] * 3, axis=2)
        result = adjusted * mask_3ch + image.astype(np.float32) / 255.0 * (1 - mask_3ch)
        
        if image.dtype == np.uint8:
            result = (result * 255).astype(np.uint8)
        
        return EditResult(
            original_image=image,
            edited_image=result,
            saliency_map=saliency_map,
            binary_mask=binary_mask,
            edit_type='adjust',
            parameters={'brightness': brightness, 'contrast': contrast, 'saturation': saturation, 'hue_shift': hue_shift}
        )
    
    def stylize_salient_region(self, image: np.ndarray, saliency_map: np.ndarray,
                              style: str = 'sketch',
                              binary_mask: Optional[np.ndarray] = None,
                              threshold: float = 0.5,
                              invert_mask: bool = False,
                              feather: int = 5) -> EditResult:
        if binary_mask is None:
            binary_mask = (saliency_map > threshold).astype(np.float32)
        
        if invert_mask:
            binary_mask = 1 - binary_mask
        
        if feather > 0:
            kernel = feather * 2 + 1
            binary_mask = cv2.GaussianBlur(binary_mask, (kernel, kernel), 0)
        
        image_float = image.astype(np.float32) / 255.0 if image.dtype == np.uint8 else image
        
        if style == 'sketch':
            gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
            inv = 255 - gray
            blur = cv2.GaussianBlur(inv, (21, 21), 0)
            sketch = cv2.divide(gray, 255 - blur, scale=256)
            stylized = cv2.cvtColor(sketch, cv2.COLOR_GRAY2RGB)
            stylized = stylized.astype(np.float32) / 255.0
        elif style == 'oil_painting':
            stylized = cv2.ximgproc.anisotropicDiffusion(image, 0.1, 0.1, 5).astype(np.float32) / 255.0
        elif style == 'cartoon':
            gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
            gray = cv2.medianBlur(gray, 5)
            edges = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_MEAN_C,
                                         cv2.THRESH_BINARY, 9, 9)
            color = cv2.bilateralFilter(image, 9, 300, 300)
            edges = cv2.cvtColor(edges, cv2.COLOR_GRAY2RGB)
            stylized = cv2.bitwise_and(color, edges).astype(np.float32) / 255.0
        elif style == 'sepia':
            sepia_kernel = np.array([[0.272, 0.534, 0.131],
                                     [0.349, 0.686, 0.168],
                                     [0.393, 0.769, 0.189]])
            stylized = cv2.transform(image_float, sepia_kernel)
            stylized = np.clip(stylized, 0, 1)
        else:
            stylized = image_float
        
        mask_3ch = np.stack([binary_mask] * 3, axis=2)
        result = stylized * mask_3ch + image_float * (1 - mask_3ch)
        
        if image.dtype == np.uint8:
            result = (result * 255).astype(np.uint8)
        
        return EditResult(
            original_image=image,
            edited_image=result,
            saliency_map=saliency_map,
            binary_mask=binary_mask,
            edit_type='stylize',
            parameters={'style': style}
        )
    
    def create_composite(self, image: np.ndarray, saliency_map: np.ndarray,
                        background: np.ndarray,
                        binary_mask: Optional[np.ndarray] = None,
                        threshold: float = 0.5,
                        feather: int = 10) -> EditResult:
        if binary_mask is None:
            binary_mask = (saliency_map > threshold).astype(np.float32)
        
        if feather > 0:
            kernel = feather * 2 + 1
            binary_mask = cv2.GaussianBlur(binary_mask, (kernel, kernel), 0)
        
        if background.shape != image.shape:
            background = cv2.resize(background, (image.shape[1], image.shape[0]))
        
        image_float = image.astype(np.float32) / 255.0 if image.dtype == np.uint8 else image
        bg_float = background.astype(np.float32) / 255.0 if background.dtype == np.uint8 else background
        
        mask_3ch = np.stack([binary_mask] * 3, axis=2)
        result = image_float * mask_3ch + bg_float * (1 - mask_3ch)
        
        if image.dtype == np.uint8:
            result = (result * 255).astype(np.uint8)
        
        return EditResult(
            original_image=image,
            edited_image=result,
            saliency_map=saliency_map,
            binary_mask=binary_mask,
            edit_type='composite',
            parameters={'background': True, 'feather': feather}
        )


def fill_salient_region(image: np.ndarray, saliency_map: np.ndarray, **kwargs) -> EditResult:
    editor = ImageEditor()
    return editor.fill_salient_region(image, saliency_map, **kwargs)


def blur_salient_region(image: np.ndarray, saliency_map: np.ndarray, **kwargs) -> EditResult:
    editor = ImageEditor()
    return editor.blur_salient_region(image, saliency_map, **kwargs)


def replace_salient_region(image: np.ndarray, replacement: np.ndarray,
                          saliency_map: np.ndarray, **kwargs) -> EditResult:
    editor = ImageEditor()
    return editor.replace_salient_region(image, replacement, saliency_map, **kwargs)


def adjust_salient_region(image: np.ndarray, saliency_map: np.ndarray, **kwargs) -> EditResult:
    editor = ImageEditor()
    return editor.adjust_salient_region(image, saliency_map, **kwargs)
