import cv2
import numpy as np
from typing import Tuple, Optional, List
from dataclasses import dataclass


@dataclass
class InpaintingConfig:
    patch_size: int = 9
    alpha_threshold: float = 0.3
    max_iterations: int = 5000
    confidence_threshold: float = 0.01
    poisson_blending: bool = True
    use_telea: bool = True
    telea_radius: int = 5


class TextureSynthesizer:
    def __init__(self, config: Optional[InpaintingConfig] = None):
        self.config = config or InpaintingConfig()
    
    def detect_strong_reflection(
        self,
        image: np.ndarray,
        alpha_mask: Optional[np.ndarray] = None,
        reflection: Optional[np.ndarray] = None
    ) -> np.ndarray:
        h, w = image.shape[:2]
        strong_mask = np.zeros((h, w), dtype=np.uint8)
        
        if alpha_mask is not None:
            alpha_norm = alpha_mask.astype(np.float32) / 255.0 if alpha_mask.max() > 1 else alpha_mask
            strong_mask = (alpha_norm < self.config.alpha_threshold).astype(np.uint8) * 255
        
        if reflection is not None:
            reflection_gray = cv2.cvtColor(reflection, cv2.COLOR_RGB2GRAY)
            _, high_reflection = cv2.threshold(reflection_gray, 200, 255, cv2.THRESH_BINARY)
            strong_mask = cv2.bitwise_or(strong_mask, high_reflection)
        
        image_gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
        _, overexposed = cv2.threshold(image_gray, 240, 255, cv2.THRESH_BINARY)
        strong_mask = cv2.bitwise_or(strong_mask, overexposed)
        
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        strong_mask = cv2.dilate(strong_mask, kernel, iterations=2)
        strong_mask = cv2.morphologyEx(strong_mask, cv2.MORPH_CLOSE, kernel)
        
        return strong_mask
    
    def inpaint_telea(
        self,
        image: np.ndarray,
        mask: np.ndarray
    ) -> np.ndarray:
        mask_8u = mask.astype(np.uint8)
        inpainted = cv2.inpaint(image, mask_8u, self.config.telea_radius, cv2.INPAINT_TELEA)
        return inpainted
    
    def inpaint_ns(
        self,
        image: np.ndarray,
        mask: np.ndarray
    ) -> np.ndarray:
        mask_8u = mask.astype(np.uint8)
        inpainted = cv2.inpaint(image, mask_8u, self.config.telea_radius, cv2.INPAINT_NS)
        return inpainted
    
    def exemplar_based_inpainting(
        self,
        image: np.ndarray,
        mask: np.ndarray,
        reflection: Optional[np.ndarray] = None
    ) -> np.ndarray:
        h, w = image.shape[:2]
        image_float = image.astype(np.float32) / 255.0
        mask_float = mask.astype(np.float32) / 255.0
        
        confidence = 1.0 - mask_float.copy()
        data = np.zeros_like(mask_float)
        
        filled = mask_float < 0.5
        
        if reflection is not None:
            reflection_float = reflection.astype(np.float32) / 255.0
            image_input = image_float - 0.5 * reflection_float
            image_input = np.clip(image_input, 0, 1)
        else:
            image_input = image_float.copy()
        
        result = image_input.copy()
        
        patch_half = self.config.patch_size // 2
        iteration = 0
        
        while np.sum(mask_float > 0.5) > 0 and iteration < self.config.max_iterations:
            self._compute_data_term(data, result, mask_float, confidence, patch_half)
            
            priorities = confidence * data * mask_float
            
            max_val = np.max(priorities)
            if max_val < self.config.confidence_threshold:
                break
            
            target_y, target_x = np.unravel_index(np.argmax(priorities), priorities.shape)
            
            best_patch, best_match_y, best_match_x = self._find_best_patch(
                result, mask_float, target_y, target_x, patch_half
            )
            
            result = self._fill_patch(
                result, mask_float, confidence, data,
                best_patch, target_y, target_x, best_match_y, best_match_x, patch_half
            )
            
            mask_float[
                max(0, target_y - patch_half):min(h, target_y + patch_half + 1),
                max(0, target_x - patch_half):min(w, target_x + patch_half + 1)
            ] = 0
            
            iteration += 1
        
        result = (result * 255).astype(np.uint8)
        return result
    
    def _compute_data_term(
        self,
        data: np.ndarray,
        image: np.ndarray,
        mask: np.ndarray,
        confidence: np.ndarray,
        patch_half: int
    ):
        h, w = mask.shape
        data.fill(0)
        
        edges = self._compute_edges(image)
        
        for y in range(patch_half, h - patch_half):
            for x in range(patch_half, w - patch_half):
                if mask[y, x] > 0.5 and self._has_valid_neighbor(mask, y, x, patch_half):
                    normal = self._compute_normal(mask, y, x)
                    edge_val = edges[y, x]
                    data[y, x] = abs(edge_val[0] * normal[0] + edge_val[1] * normal[1]) + 1e-6
    
    def _compute_edges(self, image: np.ndarray) -> np.ndarray:
        gray = cv2.cvtColor((image * 255).astype(np.uint8), cv2.COLOR_RGB2GRAY)
        sobel_x = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
        sobel_y = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=3)
        return np.stack([sobel_x, sobel_y], axis=-1)
    
    def _compute_normal(self, mask: np.ndarray, y: int, x: int) -> Tuple[float, float]:
        h, w = mask.shape
        dx = 0
        dy = 0
        
        if x > 0 and x < w - 1:
            dx = mask[y, x + 1] - mask[y, x - 1]
        if y > 0 and y < h - 1:
            dy = mask[y + 1, x] - mask[y - 1, x]
        
        norm = np.sqrt(dx**2 + dy**2) + 1e-8
        return (-dy / norm, dx / norm)
    
    def _has_valid_neighbor(
        self,
        mask: np.ndarray,
        y: int,
        x: int,
        patch_half: int
    ) -> bool:
        h, w = mask.shape
        count = 0
        
        for dy in range(-patch_half, patch_half + 1):
            for dx in range(-patch_half, patch_half + 1):
                ny, nx = y + dy, x + dx
                if 0 <= ny < h and 0 <= nx < w:
                    if mask[ny, nx] < 0.5:
                        count += 1
        
        return count > 0
    
    def _find_best_patch(
        self,
        image: np.ndarray,
        mask: np.ndarray,
        target_y: int,
        target_x: int,
        patch_half: int
    ) -> Tuple[np.ndarray, int, int]:
        h, w = image.shape[:2]
        best_error = float('inf')
        best_patch = None
        best_y, best_x = 0, 0
        
        target_patch_mask = self._get_patch(mask, target_y, target_x, patch_half)
        valid_mask = target_patch_mask < 0.5
        
        if not np.any(valid_mask):
            return self._get_patch(image, target_y, target_x, patch_half), target_y, target_x
        
        target_patch = self._get_patch(image, target_y, target_x, patch_half)
        
        step = max(1, patch_half // 2)
        
        for y in range(patch_half, h - patch_half, step):
            for x in range(patch_half, w - patch_half, step):
                source_patch_mask = self._get_patch(mask, y, x, patch_half)
                
                if np.any(source_patch_mask > 0.5):
                    continue
                
                source_patch = self._get_patch(image, y, x, patch_half)
                
                error = np.sum(((target_patch - source_patch) ** 2) * valid_mask[..., np.newaxis])
                error /= np.sum(valid_mask) + 1e-8
                
                if error < best_error:
                    best_error = error
                    best_patch = source_patch
                    best_y, best_x = y, x
        
        if best_patch is None:
            best_patch = self._get_patch(image, target_y, target_x, patch_half)
        
        return best_patch, best_y, best_x
    
    def _get_patch(
        self,
        image: np.ndarray,
        y: int,
        x: int,
        patch_half: int
    ) -> np.ndarray:
        h, w = image.shape[:2]
        y1 = max(0, y - patch_half)
        y2 = min(h, y + patch_half + 1)
        x1 = max(0, x - patch_half)
        x2 = min(w, x + patch_half + 1)
        
        patch = image[y1:y2, x1:x2]
        
        expected_size = 2 * patch_half + 1
        if patch.shape[0] < expected_size or patch.shape[1] < expected_size:
            if len(image.shape) == 3:
                padded = np.zeros((expected_size, expected_size, image.shape[2]), dtype=image.dtype)
            else:
                padded = np.zeros((expected_size, expected_size), dtype=image.dtype)
            
            pad_top = patch_half - (y - y1)
            pad_left = patch_half - (x - x1)
            padded[pad_top:pad_top + patch.shape[0], pad_left:pad_left + patch.shape[1]] = patch
            return padded
        
        return patch
    
    def _fill_patch(
        self,
        result: np.ndarray,
        mask: np.ndarray,
        confidence: np.ndarray,
        data: np.ndarray,
        source_patch: np.ndarray,
        target_y: int,
        target_x: int,
        source_y: int,
        source_x: int,
        patch_half: int
    ) -> np.ndarray:
        h, w = result.shape[:2]
        new_result = result.copy()
        
        y1 = max(0, target_y - patch_half)
        y2 = min(h, target_y + patch_half + 1)
        x1 = max(0, target_x - patch_half)
        x2 = min(w, target_x + patch_half + 1)
        
        sy1 = source_y - (target_y - y1)
        sy2 = source_y + (y2 - target_y)
        sx1 = source_x - (target_x - x1)
        sx2 = source_x + (x2 - target_x)
        
        sy1 = max(0, min(h, sy1))
        sy2 = max(0, min(h, sy2))
        sx1 = max(0, min(w, sx1))
        sx2 = max(0, min(w, sx2))
        
        target_region = mask[y1:y2, x1:x2] > 0.5
        
        if np.any(target_region):
            source_region = source_patch[
                (y1 - (target_y - patch_half)):(y2 - (target_y - patch_half)),
                (x1 - (target_x - patch_half)):(x2 - (target_x - patch_half))
            ]
            
            source_region = source_region[:target_region.shape[0], :target_region.shape[1]]
            
            new_result[y1:y2, x1:x2][target_region] = source_region[target_region]
            
            avg_confidence = np.mean(confidence[sy1:sy2, sx1:sx2])
            confidence[y1:y2, x1:x2][target_region] = avg_confidence
        
        return new_result
    
    def poisson_blend(
        self,
        source: np.ndarray,
        target: np.ndarray,
        mask: np.ndarray
    ) -> np.ndarray:
        mask_8u = mask.astype(np.uint8)
        
        contours, _ = cv2.findContours(mask_8u, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        if len(contours) == 0:
            return target
        
        result = target.copy()
        
        for contour in contours:
            x, y, w, h = cv2.boundingRect(contour)
            
            center = (x + w // 2, y + h // 2)
            
            source_crop = source[y:y+h, x:x+w]
            target_crop = target[y:y+h, x:x+w]
            mask_crop = mask_8u[y:y+h, x:x+w]
            
            if source_crop.shape[0] == 0 or source_crop.shape[1] == 0:
                continue
            
            try:
                blended = cv2.seamlessClone(
                    source_crop, target_crop, mask_crop,
                    (w // 2, h // 2), cv2.NORMAL_CLONE
                )
                result[y:y+h, x:x+w] = blended
            except Exception:
                result[y:y+h, x:x+w][mask_crop > 0] = source_crop[mask_crop > 0]
        
        return result
    
    def restore_strong_reflection(
        self,
        image: np.ndarray,
        alpha_mask: Optional[np.ndarray] = None,
        reflection: Optional[np.ndarray] = None,
        initial_restoration: Optional[np.ndarray] = None
    ) -> Tuple[np.ndarray, np.ndarray]:
        strong_mask = self.detect_strong_reflection(image, alpha_mask, reflection)
        
        if np.sum(strong_mask > 0) == 0:
            return image if initial_restoration is None else initial_restoration, strong_mask
        
        base_image = initial_restoration if initial_restoration is not None else image
        
        if self.config.use_telea:
            inpainted = self.inpaint_telea(base_image, strong_mask)
        else:
            inpainted = self.exemplar_based_inpainting(base_image, strong_mask, reflection)
        
        if self.config.poisson_blending:
            inpainted = self.poisson_blend(inpainted, base_image, strong_mask)
        
        return inpainted, strong_mask
