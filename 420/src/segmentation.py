import cv2
import numpy as np
from typing import Optional, Tuple, List
from PyQt5.QtCore import QThread, pyqtSignal


class InstanceSegmenter:
    def __init__(self, use_gpu: bool = True):
        self.use_gpu = use_gpu
        self.segmentation_method = "background_subtraction"
        self.bg_subtractor = cv2.createBackgroundSubtractorMOG2(
            history=500, varThreshold=16, detectShadows=False
        )
        self.mask_blur_kernel = 21
        self.mask_threshold = 200
        self.min_contour_area = 500
        self.is_initialized = False
        self.frame_count = 0
        self.warmup_frames = 30

    def initialize(self):
        self.bg_subtractor = cv2.createBackgroundSubtractorMOG2(
            history=500, varThreshold=16, detectShadows=False
        )
        self.frame_count = 0
        self.is_initialized = False

    def segment(self, frame: np.ndarray) -> np.ndarray:
        h, w = frame.shape[:2]

        if self.segmentation_method == "background_subtraction":
            mask = self._background_subtraction(frame)
        elif self.segmentation_method == "color_based":
            mask = self._color_based_segmentation(frame)
        elif self.segmentation_method == "edge_based":
            mask = self._edge_based_segmentation(frame)
        else:
            mask = np.ones((h, w), dtype=np.uint8) * 255

        mask = cv2.GaussianBlur(mask, (self.mask_blur_kernel, self.mask_blur_kernel), 0)
        _, mask = cv2.threshold(mask, self.mask_threshold, 255, cv2.THRESH_BINARY)

        mask = self._remove_small_contours(mask)

        return mask

    def _background_subtraction(self, frame: np.ndarray) -> np.ndarray:
        h, w = frame.shape[:2]

        if not self.is_initialized:
            self.frame_count += 1
            if self.frame_count >= self.warmup_frames:
                self.is_initialized = True

        fg_mask = self.bg_subtractor.apply(frame, learningRate=0.001)
        return fg_mask

    def _color_based_segmentation(self, frame: np.ndarray) -> np.ndarray:
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

        lower_skin = np.array([0, 20, 70], dtype=np.uint8)
        upper_skin = np.array([20, 255, 255], dtype=np.uint8)

        mask = cv2.inRange(hsv, lower_skin, upper_skin)
        return mask

    def _edge_based_segmentation(self, frame: np.ndarray) -> np.ndarray:
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        gray = cv2.GaussianBlur(gray, (5, 5), 0)

        edges = cv2.Canny(gray, 30, 100)

        kernel = np.ones((15, 15), np.uint8)
        mask = cv2.dilate(edges, kernel, iterations=1)

        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        mask = np.zeros_like(mask)
        for contour in contours:
            if cv2.contourArea(contour) > self.min_contour_area:
                cv2.fillPoly(mask, [contour], 255)

        return mask

    def _remove_small_contours(self, mask: np.ndarray) -> np.ndarray:
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        result = np.zeros_like(mask)

        for contour in contours:
            area = cv2.contourArea(contour)
            if area > self.min_contour_area:
                cv2.fillPoly(result, [contour], 255)

        return result

    def get_fg_bg_regions(self, frame: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        mask = self.segment(frame)
        fg = cv2.bitwise_and(frame, frame, mask=mask)

        mask_inv = cv2.bitwise_not(mask)
        bg = cv2.bitwise_and(frame, frame, mask=mask_inv)

        return fg, bg

    def set_method(self, method: str):
        self.segmentation_method = method
        self.initialize()

    def set_parameters(self, threshold: int = 200, blur_kernel: int = 21, min_area: int = 500):
        self.mask_threshold = threshold
        self.mask_blur_kernel = max(3, blur_kernel)
        if self.mask_blur_kernel % 2 == 0:
            self.mask_blur_kernel += 1
        self.min_contour_area = min_area

    def get_available_methods(self) -> List[str]:
        return ["background_subtraction", "color_based", "edge_based", "none"]

    def get_mask_overlay(self, frame: np.ndarray, alpha: float = 0.5) -> np.ndarray:
        mask = self.segment(frame)
        mask_colored = cv2.cvtColor(mask, cv2.GRAY2BGR)
        mask_colored[mask > 0] = [0, 255, 0]

        overlay = cv2.addWeighted(frame, 1 - alpha, mask_colored, alpha, 0)
        return overlay
