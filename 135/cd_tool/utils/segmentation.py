import cv2
import numpy as np
import torch
from typing import Optional, Tuple


class ChangeSegmenter:
    def __init__(self, threshold: float = 0.5, use_crf: bool = False):
        self.threshold = threshold
        self.use_crf = use_crf

    def segment(self, pred: np.ndarray, img1: Optional[np.ndarray] = None) -> np.ndarray:
        if isinstance(pred, torch.Tensor):
            pred = pred.cpu().numpy()
        if len(pred.shape) == 4:
            pred = pred.squeeze(1) if pred.shape[1] == 1 else pred[:, 1]
        elif len(pred.shape) == 3 and pred.shape[0] == 1:
            pred = pred.squeeze(0)
        mask = (pred > self.threshold).astype(np.uint8)
        return mask

    def post_process(self, mask: np.ndarray, 
                     min_area: int = 100, 
                     max_area: Optional[int] = None,
                     morphological_iterations: int = 1) -> np.ndarray:
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel, iterations=morphological_iterations)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel, iterations=morphological_iterations)
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        valid_contours = []
        for cnt in contours:
            area = cv2.contourArea(cnt)
            if area >= min_area and (max_area is None or area <= max_area):
                valid_contours.append(cnt)
        clean_mask = np.zeros_like(mask)
        cv2.drawContours(clean_mask, valid_contours, -1, 1, -1)
        return clean_mask

    def get_change_regions(self, mask: np.ndarray) -> list:
        contours, hierarchy = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        regions = []
        for cnt in contours:
            x, y, w, h = cv2.boundingRect(cnt)
            area = cv2.contourArea(cnt)
            regions.append({
                'bbox': (x, y, x + w, y + h),
                'center': (x + w // 2, y + h // 2),
                'area': area,
                'contour': cnt
            })
        return regions

    def visualize(self, img: np.ndarray, mask: np.ndarray, 
                  color: Tuple[int, int, int] = (0, 0, 255),
                  alpha: float = 0.5) -> np.ndarray:
        if len(img.shape) == 2:
            img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
        elif img.shape[2] == 1:
            img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
        if img.dtype != np.uint8:
            img = (img * 255).astype(np.uint8)
        mask_colored = np.zeros_like(img)
        mask_colored[mask > 0] = color
        blended = cv2.addWeighted(img, 1 - alpha, mask_colored, alpha, 0)
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        cv2.drawContours(blended, contours, -1, color, 2)
        return blended

    def otsu_threshold(self, diff: np.ndarray) -> np.ndarray:
        diff_norm = (diff * 255).astype(np.uint8)
        _, mask = cv2.threshold(diff_norm, 0, 1, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        return mask.astype(np.uint8)

    def adaptive_threshold(self, diff: np.ndarray, 
                           block_size: int = 11,
                           C: int = 2) -> np.ndarray:
        diff_norm = (diff * 255).astype(np.uint8)
        mask = cv2.adaptiveThreshold(diff_norm, 1, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                     cv2.THRESH_BINARY, block_size, C)
        return mask.astype(np.uint8)
