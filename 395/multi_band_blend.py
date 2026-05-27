import cv2
import numpy as np
from scipy.ndimage import distance_transform_edt, gaussian_filter
from typing import Tuple, List, Optional


class MultiBandBlender:
    def __init__(self, num_levels: int = 6, adaptive: bool = True,
                 gain_compensation: bool = True):
        self.num_levels = num_levels
        self.adaptive = adaptive
        self.gain_compensation = gain_compensation

    def build_gaussian_pyramid(self, img: np.ndarray) -> List[np.ndarray]:
        pyramid = [img.astype(np.float32)]
        for _ in range(self.num_levels - 1):
            img = cv2.pyrDown(img)
            pyramid.append(img.astype(np.float32))
        return pyramid

    def build_laplacian_pyramid(self, img: np.ndarray) -> List[np.ndarray]:
        gaussian_pyramid = self.build_gaussian_pyramid(img)
        laplacian_pyramid = []
        
        for i in range(self.num_levels - 1):
            size = (gaussian_pyramid[i].shape[1], gaussian_pyramid[i].shape[0])
            upsampled = cv2.pyrUp(gaussian_pyramid[i + 1], dstsize=size)
            laplacian = gaussian_pyramid[i] - upsampled
            laplacian_pyramid.append(laplacian)
        
        laplacian_pyramid.append(gaussian_pyramid[-1])
        return laplacian_pyramid

    def reconstruct_from_laplacian(self, pyramid: List[np.ndarray]) -> np.ndarray:
        img = pyramid[-1]
        for i in range(self.num_levels - 2, -1, -1):
            size = (pyramid[i].shape[1], pyramid[i].shape[0])
            img = cv2.pyrUp(img, dstsize=size)
            img = img + pyramid[i]
        return np.clip(img, 0, 255).astype(np.uint8)

    def create_weight_mask(self, mask: np.ndarray) -> np.ndarray:
        if len(mask.shape) == 3:
            mask = mask[:, :, 0]
        dist = distance_transform_edt(mask > 0)
        return dist

    def _compute_overlap_brightness(self, img1: np.ndarray, img2: np.ndarray,
                                    mask1: np.ndarray, mask2: np.ndarray) -> Tuple[float, float]:
        overlap_mask = (mask1 > 0) & (mask2 > 0)
        
        if np.sum(overlap_mask) < 10:
            return 1.0, 1.0
        
        gray1 = cv2.cvtColor(img1, cv2.COLOR_BGR2GRAY) if len(img1.shape) == 3 else img1
        gray2 = cv2.cvtColor(img2, cv2.COLOR_BGR2GRAY) if len(img2.shape) == 3 else img2
        
        mean1 = np.mean(gray1[overlap_mask])
        mean2 = np.mean(gray2[overlap_mask])
        
        return mean1, mean2

    def _adaptive_gain_compensation(self, img1: np.ndarray, img2: np.ndarray,
                                    mask1: np.ndarray, mask2: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        if not self.gain_compensation:
            return img1, img2
        
        mean1, mean2 = self._compute_overlap_brightness(img1, img2, mask1, mask2)
        
        if mean1 < 1.0 or mean2 < 1.0:
            return img1, img2
        
        ratio = mean2 / mean1
        
        if 0.85 <= ratio <= 1.15:
            return img1, img2
        
        target_mean = (mean1 + mean2) / 2.0
        
        img1_adjusted = img1.astype(np.float32) * (target_mean / (mean1 + 1e-8))
        img2_adjusted = img2.astype(np.float32) * (target_mean / (mean2 + 1e-8))
        
        return np.clip(img1_adjusted, 0, 255).astype(np.uint8), np.clip(img2_adjusted, 0, 255).astype(np.uint8)

    def _adaptive_num_levels(self, img1: np.ndarray, img2: np.ndarray,
                             mask1: np.ndarray, mask2: np.ndarray) -> int:
        if not self.adaptive:
            return self.num_levels
        
        overlap_mask = (mask1 > 0) & (mask2 > 0)
        if np.sum(overlap_mask) < 100:
            return min(4, self.num_levels)
        
        overlap_rows = np.any(overlap_mask, axis=1)
        overlap_cols = np.any(overlap_mask, axis=0)
        
        overlap_height = np.sum(overlap_rows)
        overlap_width = np.sum(overlap_cols)
        
        min_dim = min(overlap_height, overlap_width)
        
        if min_dim < 32:
            return 3
        elif min_dim < 64:
            return 4
        elif min_dim < 128:
            return 5
        else:
            return self.num_levels

    def blend_two_images(self, img1: np.ndarray, img2: np.ndarray,
                         mask1: np.ndarray, mask2: np.ndarray,
                         adaptive: Optional[bool] = None) -> np.ndarray:
        use_adaptive = self.adaptive if adaptive is None else adaptive
        
        if use_adaptive and self.gain_compensation:
            img1, img2 = self._adaptive_gain_compensation(img1, img2, mask1, mask2)
        
        if use_adaptive:
            original_levels = self.num_levels
            self.num_levels = self._adaptive_num_levels(img1, img2, mask1, mask2)
        
        weight1 = self.create_weight_mask(mask1)
        weight2 = self.create_weight_mask(mask2)
        
        weight_sum = weight1 + weight2 + 1e-8
        weight1 = weight1 / weight_sum
        weight2 = weight2 / weight_sum
        
        if len(img1.shape) == 3:
            weight1 = np.stack([weight1] * 3, axis=2)
            weight2 = np.stack([weight2] * 3, axis=2)
        
        lap1 = self.build_laplacian_pyramid(img1)
        lap2 = self.build_laplacian_pyramid(img2)
        
        weight_pyr1 = self.build_gaussian_pyramid(weight1)
        weight_pyr2 = self.build_gaussian_pyramid(weight2)
        
        blended_pyramid = []
        for i in range(self.num_levels):
            blended = lap1[i] * weight_pyr1[i] + lap2[i] * weight_pyr2[i]
            blended_pyramid.append(blended)
        
        result = self.reconstruct_from_laplacian(blended_pyramid)
        
        if use_adaptive:
            self.num_levels = original_levels
        
        return result

    def blend_multiple_images(self, images: List[np.ndarray],
                              masks: List[np.ndarray],
                              adaptive: Optional[bool] = None) -> np.ndarray:
        if len(images) == 1:
            return images[0]
        
        use_adaptive = self.adaptive if adaptive is None else adaptive
        
        if use_adaptive and self.gain_compensation and len(images) >= 2:
            images = self._multi_image_gain_compensation(images, masks)
        
        weights = []
        for mask in masks:
            w = self.create_weight_mask(mask)
            if len(images[0].shape) == 3:
                w = np.stack([w] * 3, axis=2)
            weights.append(w)
        
        weight_sum = np.sum(weights, axis=0) + 1e-8
        normalized_weights = [w / weight_sum for w in weights]
        
        lap_pyramids = [self.build_laplacian_pyramid(img) for img in images]
        weight_pyramids = [self.build_gaussian_pyramid(w) for w in normalized_weights]
        
        blended_pyramid = []
        for level in range(self.num_levels):
            blended = np.zeros_like(lap_pyramids[0][level])
            for i in range(len(images)):
                blended += lap_pyramids[i][level] * weight_pyramids[i][level]
            blended_pyramid.append(blended)
        
        return self.reconstruct_from_laplacian(blended_pyramid)

    def _multi_image_gain_compensation(self, images: List[np.ndarray], 
                                       masks: List[np.ndarray]) -> List[np.ndarray]:
        if len(images) < 2:
            return images
        
        means = []
        for i, (img, mask) in enumerate(zip(images, masks)):
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if len(img.shape) == 3 else img
            valid_mask = mask > 0
            if np.sum(valid_mask) > 0:
                means.append(np.mean(gray[valid_mask]))
            else:
                means.append(128.0)
        
        target_mean = np.mean(means)
        
        adjusted = []
        for img, mean in zip(images, means):
            if mean > 1.0:
                ratio = target_mean / mean
                if 0.7 <= ratio <= 1.4:
                    img_adjusted = img.astype(np.float32) * ratio
                    adjusted.append(np.clip(img_adjusted, 0, 255).astype(np.uint8))
                else:
                    adjusted.append(img)
            else:
                adjusted.append(img)
        
        return adjusted

    def simple_feather_blend(self, img1: np.ndarray, img2: np.ndarray,
                             mask1: np.ndarray, mask2: np.ndarray,
                             feather_width: int = 20) -> np.ndarray:
        if self.gain_compensation:
            img1, img2 = self._adaptive_gain_compensation(img1, img2, mask1, mask2)
        
        weight1 = self.create_weight_mask(mask1)
        weight2 = self.create_weight_mask(mask2)
        
        weight1 = np.clip(weight1 / feather_width, 0, 1)
        weight2 = np.clip(weight2 / feather_width, 0, 1)
        
        weight_sum = weight1 + weight2 + 1e-8
        weight1 = weight1 / weight_sum
        weight2 = weight2 / weight_sum
        
        if len(img1.shape) == 3:
            weight1 = np.stack([weight1] * 3, axis=2)
            weight2 = np.stack([weight2] * 3, axis=2)
        
        blended = img1.astype(np.float32) * weight1 + img2.astype(np.float32) * weight2
        return np.clip(blended, 0, 255).astype(np.uint8)

    def blend_blocks(self, blocks: List[np.ndarray], 
                     block_masks: List[np.ndarray],
                     overlap_width: int = 100) -> np.ndarray:
        if len(blocks) == 1:
            return blocks[0]
        
        result = blocks[0]
        result_mask = block_masks[0]
        
        for i in range(1, len(blocks)):
            current = blocks[i]
            current_mask = block_masks[i]
            
            if result.shape != current.shape:
                h = max(result.shape[0], current.shape[0])
                w = max(result.shape[1], current.shape[1])
                if len(result.shape) == 3:
                    new_result = np.zeros((h, w, 3), dtype=np.uint8)
                    new_result[:result.shape[0], :result.shape[1]] = result
                    result = new_result
                    
                    new_result_mask = np.zeros((h, w), dtype=np.uint8)
                    new_result_mask[:result_mask.shape[0], :result_mask.shape[1]] = result_mask
                    result_mask = new_result_mask
                    
                    new_current = np.zeros((h, w, 3), dtype=np.uint8)
                    new_current[:current.shape[0], :current.shape[1]] = current
                    current = new_current
                    
                    new_current_mask = np.zeros((h, w), dtype=np.uint8)
                    new_current_mask[:current_mask.shape[0], :current_mask.shape[1]] = current_mask
                    current_mask = new_current_mask
            
            result = self.blend_two_images(result, current, result_mask, current_mask)
            result_mask = (result_mask > 0) | (current_mask > 0)
            result_mask = (result_mask * 255).astype(np.uint8)
        
        return result
