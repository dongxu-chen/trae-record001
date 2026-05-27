import cv2
import numpy as np
from typing import Tuple, Optional


class HomographyEstimator:
    def __init__(self, ransac_threshold: float = 3.0, confidence: float = 0.999,
                 max_iters: int = 10000, reproj_threshold: float = 2.0):
        self.ransac_threshold = ransac_threshold
        self.confidence = confidence
        self.max_iters = max_iters
        self.reproj_threshold = reproj_threshold

    def estimate_homography(self, pts1: np.ndarray, pts2: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        H, mask = cv2.findHomography(pts2, pts1, cv2.RANSAC,
                                     self.ransac_threshold, None,
                                     maxIters=self.max_iters, 
                                     confidence=self.confidence)
        
        if H is not None and mask is not None:
            mask = self._refine_inliers(pts1, pts2, H, mask)
        
        return H, mask

    def _refine_inliers(self, pts1: np.ndarray, pts2: np.ndarray, 
                        H: np.ndarray, mask: np.ndarray) -> np.ndarray:
        inliers = mask.ravel() == 1
        if np.sum(inliers) < 10:
            return mask
        
        pts1_inliers = pts1[inliers]
        pts2_inliers = pts2[inliers]
        
        pts2_transformed = cv2.perspectiveTransform(pts2_inliers, H)
        
        reproj_errors = np.sum((pts1_inliers - pts2_transformed) ** 2, axis=2).ravel()
        
        refined_mask = np.zeros_like(mask)
        good_inliers = reproj_errors < self.reproj_threshold ** 2
        
        inlier_indices = np.where(inliers)[0]
        refined_mask[inlier_indices[good_inliers]] = 1
        
        if np.sum(refined_mask) >= 10:
            H_refined, _ = cv2.findHomography(
                pts2[refined_mask.ravel() == 1], 
                pts1[refined_mask.ravel() == 1], 
                0
            )
            if H_refined is not None:
                return refined_mask
        
        return mask

    def warp_image(self, img: np.ndarray, H: np.ndarray,
                   output_size: Tuple[int, int]) -> np.ndarray:
        return cv2.warpPerspective(img, H, output_size,
                                   flags=cv2.INTER_LINEAR,
                                   borderMode=cv2.BORDER_CONSTANT)

    def get_warped_size_and_offset(self, img: np.ndarray, H: np.ndarray) -> Tuple[Tuple[int, int], Tuple[int, int]]:
        h, w = img.shape[:2]
        corners = np.float32([[0, 0], [0, h], [w, h], [w, 0]]).reshape(-1, 1, 2)
        warped_corners = cv2.perspectiveTransform(corners, H)
        
        x_min = int(np.floor(np.min(warped_corners[:, :, 0])))
        x_max = int(np.ceil(np.max(warped_corners[:, :, 0])))
        y_min = int(np.floor(np.min(warped_corners[:, :, 1])))
        y_max = int(np.ceil(np.max(warped_corners[:, :, 1])))
        
        output_size = (x_max - x_min, y_max - y_min)
        offset = (-x_min, -y_min)
        
        return output_size, offset

    def adjust_homography_for_offset(self, H: np.ndarray, offset: Tuple[int, int]) -> np.ndarray:
        H_adjusted = H.copy()
        H_adjusted[0, 2] += offset[0]
        H_adjusted[1, 2] += offset[1]
        return H_adjusted

    def estimate_translation(self, pts1: np.ndarray, pts2: np.ndarray) -> np.ndarray:
        if len(pts1) < 2 or len(pts2) < 2:
            return np.eye(3)
        
        mean1 = np.mean(pts1.reshape(-1, 2), axis=0)
        mean2 = np.mean(pts2.reshape(-1, 2), axis=0)
        
        dx = mean1[0] - mean2[0]
        dy = mean1[1] - mean2[1]
        
        H = np.array([[1, 0, dx],
                      [0, 1, dy],
                      [0, 0, 1]], dtype=np.float64)
        return H
