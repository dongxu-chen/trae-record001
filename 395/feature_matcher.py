import cv2
import numpy as np
from typing import Tuple, List


class FeatureMatcher:
    def __init__(self, n_features: int = 5000, ratio_threshold: float = 0.75):
        self.sift = cv2.SIFT_create(nfeatures=n_features)
        self.ratio_threshold = ratio_threshold
        self.matcher = cv2.BFMatcher()

    def detect_and_compute(self, img: np.ndarray) -> Tuple[List[cv2.KeyPoint], np.ndarray]:
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if len(img.shape) == 3 else img
        keypoints, descriptors = self.sift.detectAndCompute(gray, None)
        return keypoints, descriptors

    def match_features(self, des1: np.ndarray, des2: np.ndarray) -> List[cv2.DMatch]:
        matches = self.matcher.knnMatch(des1, des2, k=2)
        good_matches = []
        for m, n in matches:
            if m.distance < self.ratio_threshold * n.distance:
                good_matches.append(m)
        return good_matches

    def get_matched_points(self, kp1: List[cv2.KeyPoint], kp2: List[cv2.KeyPoint],
                           matches: List[cv2.DMatch]) -> Tuple[np.ndarray, np.ndarray]:
        pts1 = np.float32([kp1[m.queryIdx].pt for m in matches]).reshape(-1, 1, 2)
        pts2 = np.float32([kp2[m.trainIdx].pt for m in matches]).reshape(-1, 1, 2)
        return pts1, pts2

    def draw_matches(self, img1: np.ndarray, img2: np.ndarray,
                     kp1: List[cv2.KeyPoint], kp2: List[cv2.KeyPoint],
                     matches: List[cv2.DMatch]) -> np.ndarray:
        return cv2.drawMatches(img1, kp1, img2, kp2, matches[:100], None,
                               flags=cv2.DrawMatchesFlags_NOT_DRAW_SINGLE_POINTS)
