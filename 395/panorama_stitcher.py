import cv2
import numpy as np
from typing import List, Tuple, Optional
from feature_matcher import FeatureMatcher
from homography import HomographyEstimator
from projection import ImageProjector
from multi_band_blend import MultiBandBlender


class PanoramaStitcher:
    def __init__(self, projection_type: str = 'plane',
                 blend_type: str = 'multiband',
                 focal_length: Optional[float] = None,
                 use_block_stitching: bool = True,
                 block_size: int = 2000,
                 block_overlap: int = 200):
        self.projection_type = projection_type
        self.blend_type = blend_type
        self.use_block_stitching = use_block_stitching
        self.block_size = block_size
        self.block_overlap = block_overlap
        
        self.feature_matcher = FeatureMatcher()
        self.homography_estimator = HomographyEstimator()
        self.projector = ImageProjector(focal_length=focal_length)
        self.blender = MultiBandBlender(adaptive=True, gain_compensation=True)
        
        self.images = []
        self.keypoints = []
        self.descriptors = []
        self.homographies = []
        self.warped_images = []
        self.warped_masks = []
        
        self.block_stitcher = BlockStitcher(self.blender, block_size, block_overlap)

    def load_images(self, image_paths: List[str]) -> List[np.ndarray]:
        self.images = []
        for path in image_paths:
            img = cv2.imread(path)
            if img is not None:
                self.images.append(img)
        return self.images

    def set_images(self, images: List[np.ndarray]):
        self.images = images

    def extract_features(self):
        self.keypoints = []
        self.descriptors = []
        for img in self.images:
            kp, des = self.feature_matcher.detect_and_compute(img)
            self.keypoints.append(kp)
            self.descriptors.append(des)

    def estimate_homographies(self) -> List[np.ndarray]:
        self.homographies = [np.eye(3)]
        
        for i in range(1, len(self.images)):
            matches = self.feature_matcher.match_features(
                self.descriptors[i], self.descriptors[i-1])
            
            if len(matches) < 10:
                raise ValueError(f"Insufficient matches between image {i} and {i-1}")
            
            pts_i, pts_prev = self.feature_matcher.get_matched_points(
                self.keypoints[i], self.keypoints[i-1], matches)
            
            H, mask = self.homography_estimator.estimate_homography(pts_prev, pts_i)
            
            if H is None:
                H = self.homography_estimator.estimate_translation(pts_prev, pts_i)
            
            H_total = self.homographies[i-1] @ H
            self.homographies.append(H_total)
        
        return self.homographies

    def _adjust_homographies_for_center(self):
        if len(self.homographies) == 0:
            return
        
        center_idx = len(self.images) // 2
        H_center_inv = np.linalg.inv(self.homographies[center_idx])
        
        for i in range(len(self.homographies)):
            self.homographies[i] = H_center_inv @ self.homographies[i]

    def _get_panorama_size(self) -> Tuple[Tuple[int, int], Tuple[int, int]]:
        all_corners = []
        
        for i, img in enumerate(self.images):
            h, w = img.shape[:2]
            corners = np.float32([[0, 0], [0, h], [w, h], [w, 0]]).reshape(-1, 1, 2)
            warped_corners = cv2.perspectiveTransform(corners, self.homographies[i])
            all_corners.append(warped_corners)
        
        all_corners = np.concatenate(all_corners, axis=0)
        
        x_min = int(np.floor(np.min(all_corners[:, :, 0])))
        x_max = int(np.ceil(np.max(all_corners[:, :, 0])))
        y_min = int(np.floor(np.min(all_corners[:, :, 1])))
        y_max = int(np.ceil(np.max(all_corners[:, :, 1])))
        
        output_size = (x_max - x_min, y_max - y_min)
        offset = (-x_min, -y_min)
        
        return output_size, offset

    def warp_images(self):
        if self.projection_type in ['cylindrical', 'spherical']:
            self.images = self.projector.project_images(self.images, self.projection_type)
            self.extract_features()
            self.estimate_homographies()
        
        self._adjust_homographies_for_center()
        
        output_size, offset = self._get_panorama_size()
        
        offset_H = np.array([[1, 0, offset[0]],
                             [0, 1, offset[1]],
                             [0, 0, 1]])
        
        self.warped_images = []
        self.warped_masks = []
        
        for i, img in enumerate(self.images):
            H_adjusted = offset_H @ self.homographies[i]
            
            warped = cv2.warpPerspective(img, H_adjusted, output_size,
                                         flags=cv2.INTER_LINEAR,
                                         borderMode=cv2.BORDER_CONSTANT)
            
            mask = np.ones(img.shape[:2], dtype=np.uint8) * 255
            warped_mask = cv2.warpPerspective(mask, H_adjusted, output_size,
                                              flags=cv2.INTER_NEAREST,
                                              borderMode=cv2.BORDER_CONSTANT)
            
            self.warped_images.append(warped)
            self.warped_masks.append(warped_mask)

    def blend_images(self) -> np.ndarray:
        if len(self.warped_images) == 0:
            raise ValueError("No warped images to blend")
        
        if self.use_block_stitching and self._should_use_block_stitching():
            return self.block_stitcher.stitch_large_panorama(
                self.warped_images, self.warped_masks, self.blend_type)
        
        if self.blend_type == 'multiband':
            return self.blender.blend_multiple_images(self.warped_images, self.warped_masks)
        elif self.blend_type == 'feather':
            return self._feather_blend()
        elif self.blend_type == 'simple':
            return self._simple_blend()
        else:
            return self.blender.blend_multiple_images(self.warped_images, self.warped_masks)

    def _should_use_block_stitching(self) -> bool:
        if len(self.warped_images) == 0:
            return False
        
        h, w = self.warped_images[0].shape[:2]
        return max(h, w) > self.block_size

    def _simple_blend(self) -> np.ndarray:
        result = np.zeros_like(self.warped_images[0])
        count = np.zeros(self.warped_images[0].shape[:2], dtype=np.int32)
        
        for img, mask in zip(self.warped_images, self.warped_masks):
            mask_3d = (mask > 0)[:, :, np.newaxis]
            result = result + np.where(mask_3d, img, 0)
            count = count + (mask > 0).astype(np.int32)
        
        count = np.maximum(count, 1)[:, :, np.newaxis]
        result = (result / count).astype(np.uint8)
        
        return result

    def _feather_blend(self) -> np.ndarray:
        result = np.zeros_like(self.warped_images[0], dtype=np.float32)
        total_weight = np.zeros(self.warped_images[0].shape[:2], dtype=np.float32)
        
        for img, mask in zip(self.warped_images, self.warped_masks):
            weight = self.blender.create_weight_mask(mask)
            weight = weight / (np.max(weight) + 1e-8)
            
            weight_3d = weight[:, :, np.newaxis]
            result += img.astype(np.float32) * weight_3d
            total_weight += weight
        
        total_weight = np.maximum(total_weight, 1e-8)[:, :, np.newaxis]
        result = result / total_weight
        
        return np.clip(result, 0, 255).astype(np.uint8)

    def stitch(self, image_paths: Optional[List[str]] = None,
               images: Optional[List[np.ndarray]] = None) -> np.ndarray:
        if image_paths is not None:
            self.load_images(image_paths)
        elif images is not None:
            self.set_images(images)
        
        if len(self.images) < 2:
            raise ValueError("Need at least 2 images to stitch")
        
        self.extract_features()
        self.estimate_homographies()
        self.warp_images()
        
        return self.blend_images()

    def get_match_visualization(self, idx1: int, idx2: int) -> np.ndarray:
        if idx1 >= len(self.images) or idx2 >= len(self.images):
            raise ValueError("Image index out of range")
        
        matches = self.feature_matcher.match_features(
            self.descriptors[idx1], self.descriptors[idx2])
        
        return self.feature_matcher.draw_matches(
            self.images[idx1], self.images[idx2],
            self.keypoints[idx1], self.keypoints[idx2], matches)

    def crop_black_borders(self, img: np.ndarray) -> np.ndarray:
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if len(img.shape) == 3 else img
        mask = gray > 0
        
        coords = np.argwhere(mask)
        if coords.size == 0:
            return img
        
        y_min, x_min = coords.min(axis=0)
        y_max, x_max = coords.max(axis=0)
        
        return img[y_min:y_max+1, x_min:x_max+1]


class BlockStitcher:
    def __init__(self, blender: MultiBandBlender, block_size: int = 2000, 
                 block_overlap: int = 200):
        self.blender = blender
        self.block_size = block_size
        self.block_overlap = block_overlap

    def stitch_large_panorama(self, warped_images: List[np.ndarray], 
                               warped_masks: List[np.ndarray],
                               blend_type: str = 'multiband') -> np.ndarray:
        if len(warped_images) == 0:
            raise ValueError("No images to stitch")
        
        h, w = warped_images[0].shape[:2]
        
        if max(h, w) <= self.block_size:
            return self.blender.blend_multiple_images(warped_images, warped_masks)
        
        if w > h:
            return self._stitch_horizontal_blocks(warped_images, warped_masks, blend_type)
        else:
            return self._stitch_vertical_blocks(warped_images, warped_masks, blend_type)

    def _stitch_horizontal_blocks(self, warped_images: List[np.ndarray], 
                                   warped_masks: List[np.ndarray],
                                   blend_type: str = 'multiband') -> np.ndarray:
        h, w = warped_images[0].shape[:2]
        overlap = self.block_overlap
        block_w = self.block_size
        
        blocks = []
        block_masks = []
        
        x_start = 0
        while x_start < w:
            x_end = min(x_start + block_w, w)
            
            block_images = []
            for img in warped_images:
                block_images.append(img[:, x_start:x_end])
            
            block_masks_list = []
            for mask in warped_masks:
                block_masks_list.append(mask[:, x_start:x_end])
            
            if blend_type == 'multiband':
                blended_block = self.blender.blend_multiple_images(block_images, block_masks_list)
            elif blend_type == 'feather':
                blended_block = self._simple_block_blend(block_images, block_masks_list, feather=True)
            else:
                blended_block = self._simple_block_blend(block_images, block_masks_list, feather=False)
            
            blocks.append(blended_block)
            
            mask_block = np.zeros((h, x_end - x_start), dtype=np.uint8)
            for mask in block_masks_list:
                mask_block = mask_block | mask
            block_masks.append(mask_block)
            
            if x_end >= w:
                break
            
            x_start = x_end - overlap
        
        return self._merge_horizontal_blocks(blocks, block_masks, overlap)

    def _stitch_vertical_blocks(self, warped_images: List[np.ndarray], 
                                 warped_masks: List[np.ndarray],
                                 blend_type: str = 'multiband') -> np.ndarray:
        h, w = warped_images[0].shape[:2]
        overlap = self.block_overlap
        block_h = self.block_size
        
        blocks = []
        block_masks = []
        
        y_start = 0
        while y_start < h:
            y_end = min(y_start + block_h, h)
            
            block_images = []
            for img in warped_images:
                block_images.append(img[y_start:y_end, :])
            
            block_masks_list = []
            for mask in warped_masks:
                block_masks_list.append(mask[y_start:y_end, :])
            
            if blend_type == 'multiband':
                blended_block = self.blender.blend_multiple_images(block_images, block_masks_list)
            elif blend_type == 'feather':
                blended_block = self._simple_block_blend(block_images, block_masks_list, feather=True)
            else:
                blended_block = self._simple_block_blend(block_images, block_masks_list, feather=False)
            
            blocks.append(blended_block)
            
            mask_block = np.zeros((y_end - y_start, w), dtype=np.uint8)
            for mask in block_masks_list:
                mask_block = mask_block | mask
            block_masks.append(mask_block)
            
            if y_end >= h:
                break
            
            y_start = y_end - overlap
        
        return self._merge_vertical_blocks(blocks, block_masks, overlap)

    def _merge_horizontal_blocks(self, blocks: List[np.ndarray], 
                                  block_masks: List[np.ndarray],
                                  overlap: int) -> np.ndarray:
        if len(blocks) == 1:
            return blocks[0]
        
        result = blocks[0]
        result_mask = block_masks[0]
        
        for i in range(1, len(blocks)):
            current = blocks[i]
            current_mask = block_masks[i]
            
            h = result.shape[0]
            w_result = result.shape[1]
            w_current = current.shape[1]
            w_total = w_result + w_current - overlap
            
            merged = np.zeros((h, w_total, 3), dtype=np.uint8)
            merged_mask = np.zeros((h, w_total), dtype=np.uint8)
            
            merged[:, :w_result] = result
            merged_mask[:, :w_result] = result_mask
            
            overlap_region = merged[:, w_result - overlap:w_result].copy()
            overlap_mask = merged_mask[:, w_result - overlap:w_result].copy()
            
            new_overlap_region = current[:, :overlap]
            new_overlap_mask = current_mask[:, :overlap]
            
            blended_overlap = self.blender.blend_two_images(
                overlap_region, new_overlap_region,
                overlap_mask, new_overlap_mask
            )
            
            merged[:, w_result - overlap:w_result] = blended_overlap
            merged[:, w_result:] = current[:, overlap:]
            merged_mask[:, w_result - overlap:] = (overlap_mask > 0) | (new_overlap_mask > 0)
            merged_mask[:, w_result:] = merged_mask[:, w_result:] | (current_mask[:, overlap:] > 0)
            
            result = merged
            result_mask = (merged_mask * 255).astype(np.uint8)
        
        return result

    def _merge_vertical_blocks(self, blocks: List[np.ndarray], 
                                block_masks: List[np.ndarray],
                                overlap: int) -> np.ndarray:
        if len(blocks) == 1:
            return blocks[0]
        
        result = blocks[0]
        result_mask = block_masks[0]
        
        for i in range(1, len(blocks)):
            current = blocks[i]
            current_mask = block_masks[i]
            
            w = result.shape[1]
            h_result = result.shape[0]
            h_current = current.shape[0]
            h_total = h_result + h_current - overlap
            
            merged = np.zeros((h_total, w, 3), dtype=np.uint8)
            merged_mask = np.zeros((h_total, w), dtype=np.uint8)
            
            merged[:h_result, :] = result
            merged_mask[:h_result, :] = result_mask
            
            overlap_region = merged[h_result - overlap:h_result, :].copy()
            overlap_mask = merged_mask[h_result - overlap:h_result, :].copy()
            
            new_overlap_region = current[:overlap, :]
            new_overlap_mask = current_mask[:overlap, :]
            
            blended_overlap = self.blender.blend_two_images(
                overlap_region, new_overlap_region,
                overlap_mask, new_overlap_mask
            )
            
            merged[h_result - overlap:h_result, :] = blended_overlap
            merged[h_result:, :] = current[overlap:, :]
            merged_mask[h_result - overlap:, :] = (overlap_mask > 0) | (new_overlap_mask > 0)
            merged_mask[h_result:, :] = merged_mask[h_result:, :] | (current_mask[overlap:, :] > 0)
            
            result = merged
            result_mask = (merged_mask * 255).astype(np.uint8)
        
        return result

    def _simple_block_blend(self, images: List[np.ndarray], 
                            masks: List[np.ndarray],
                            feather: bool = True) -> np.ndarray:
        if len(images) == 1:
            return images[0]
        
        if feather:
            result = np.zeros_like(images[0], dtype=np.float32)
            total_weight = np.zeros(images[0].shape[:2], dtype=np.float32)
            
            for img, mask in zip(images, masks):
                weight = self.blender.create_weight_mask(mask)
                weight = weight / (np.max(weight) + 1e-8)
                
                if len(img.shape) == 3:
                    weight = np.stack([weight] * 3, axis=2)
                
                result += img.astype(np.float32) * weight
                total_weight += weight[:, :, 0] if len(img.shape) == 3 else weight
            
            total_weight = np.maximum(total_weight, 1e-8)
            if len(images[0].shape) == 3:
                total_weight = np.stack([total_weight] * 3, axis=2)
            
            result = result / total_weight
            return np.clip(result, 0, 255).astype(np.uint8)
        else:
            result = np.zeros_like(images[0])
            count = np.zeros(images[0].shape[:2], dtype=np.int32)
            
            for img, mask in zip(images, masks):
                mask_3d = (mask > 0)[:, :, np.newaxis] if len(img.shape) == 3 else (mask > 0)
                result = result + np.where(mask_3d, img, 0)
                count = count + (mask > 0).astype(np.int32)
            
            count = np.maximum(count, 1)
            if len(images[0].shape) == 3:
                count = count[:, :, np.newaxis]
            
            return (result / count).astype(np.uint8)
