"""
图像配准模块
使用SIFT特征点匹配和RANSAC几何验证实现高精度图像配准
"""

import numpy as np
import cv2
from typing import Tuple, Optional


class ImageRegistration:
    def __init__(self, feature_type='SIFT', max_features=5000,
                 good_match_ratio=0.75, ransac_threshold=5.0):
        self.feature_type = feature_type
        self.max_features = max_features
        self.good_match_ratio = good_match_ratio
        self.ransac_threshold = ransac_threshold

        if feature_type == 'SIFT':
            self.detector = cv2.SIFT_create(nfeatures=max_features)
        elif feature_type == 'ORB':
            self.detector = cv2.ORB_create(nfeatures=max_features)
        elif feature_type == 'AKAZE':
            self.detector = cv2.AKAZE_create()
        else:
            self.detector = cv2.SIFT_create(nfeatures=max_features)

        if feature_type in ['ORB', 'AKAZE']:
            self.matcher = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=False)
        else:
            self.matcher = cv2.BFMatcher(cv2.NORM_L2, crossCheck=False)

    def preprocess_image(self, image: np.ndarray) -> np.ndarray:
        if len(image.shape) == 3:
            if image.shape[0] >= 3:
                gray = np.zeros((image.shape[1], image.shape[2]), dtype=np.float32)
                for i in range(3):
                    gray += image[i]
                gray /= 3.0
            else:
                gray = image[0]
        else:
            gray = image

        gray = np.nan_to_num(gray, nan=0.0, posinf=255.0, neginf=0.0)
        gray = np.clip(gray, 0, 255)
        gray = gray.astype(np.uint8)

        return gray

    def detect_and_compute(self, image: np.ndarray):
        gray = self.preprocess_image(image)
        keypoints, descriptors = self.detector.detectAndCompute(gray, None)
        return keypoints, descriptors

    def match_features(self, des1: np.ndarray, des2: np.ndarray):
        if des1 is None or des2 is None:
            return []

        if len(des1) < 2 or len(des2) < 2:
            return []

        knn_matches = self.matcher.knnMatch(des1, des2, k=2)

        good_matches = []
        for match_pair in knn_matches:
            if len(match_pair) == 2:
                m, n = match_pair
                if m.distance < self.good_match_ratio * n.distance:
                    good_matches.append(m)

        return good_matches

    def estimate_homography(self, kp1: list, kp2: list, matches: list):
        if len(matches) < 4:
            return None, None

        src_pts = np.float32([kp1[m.queryIdx].pt for m in matches]).reshape(-1, 1, 2)
        dst_pts = np.float32([kp2[m.trainIdx].pt for m in matches]).reshape(-1, 1, 2)

        H, mask = cv2.findHomography(
            src_pts, dst_pts,
            cv2.RANSAC,
            self.ransac_threshold,
            maxIters=10000,
            confidence=0.995
        )

        return H, mask

    def estimate_affine(self, kp1: list, kp2: list, matches: list):
        if len(matches) < 3:
            return None, None

        src_pts = np.float32([kp1[m.queryIdx].pt for m in matches]).reshape(-1, 1, 2)
        dst_pts = np.float32([kp2[m.trainIdx].pt for m in matches]).reshape(-1, 1, 2)

        M, inliers = cv2.estimateAffinePartial2D(
            src_pts, dst_pts,
            method=cv2.RANSAC,
            ransacReprojThreshold=self.ransac_threshold,
            maxIters=10000,
            confidence=0.995,
            refineIters=10
        )

        return M, inliers

    def register_images(self, image1: np.ndarray, image2: np.ndarray,
                        method: str = 'homography') -> Tuple[np.ndarray, dict]:
        kp1, des1 = self.detect_and_compute(image1)
        kp2, des2 = self.detect_and_compute(image2)

        if kp1 is None or kp2 is None:
            print("警告: 无法检测到特征点，返回原图")
            return image2.copy(), {'status': 'failed', 'reason': 'no_keypoints'}

        matches = self.match_features(des1, des2)

        if len(matches) < 4:
            print(f"警告: 有效匹配点不足 ({len(matches)})，使用仿射变换")
            M, inliers = self.estimate_affine(kp1, kp2, matches)
            transform_type = 'affine'
        elif method == 'affine':
            M, inliers = self.estimate_affine(kp1, kp2, matches)
            transform_type = 'affine'
        else:
            H, mask = self.estimate_homography(kp1, kp2, matches)
            M = H
            inliers = mask
            transform_type = 'homography'

        if M is None:
            print("警告: 变换估计失败，返回原图")
            return image2.copy(), {'status': 'failed', 'reason': 'estimation_failed'}

        height, width = image2.shape[-2], image2.shape[-1]

        if transform_type == 'homography':
            registered = np.zeros_like(image2)
            if len(image2.shape) == 3:
                for c in range(image2.shape[0]):
                    registered[c] = cv2.warpPerspective(
                        image2[c], M, (width, height),
                        flags=cv2.INTER_LINEAR,
                        borderMode=cv2.BORDER_REPLICATE
                    )
            else:
                registered = cv2.warpPerspective(
                    image2, M, (width, height),
                    flags=cv2.INTER_LINEAR,
                    borderMode=cv2.BORDER_REPLICATE
                )
        else:
            registered = np.zeros_like(image2)
            if len(image2.shape) == 3:
                for c in range(image2.shape[0]):
                    registered[c] = cv2.warpAffine(
                        image2[c], M, (width, height),
                        flags=cv2.INTER_LINEAR,
                        borderMode=cv2.BORDER_REPLICATE
                    )
            else:
                registered = cv2.warpAffine(
                    image2, M, (width, height),
                    flags=cv2.INTER_LINEAR,
                    borderMode=cv2.BORDER_REPLICATE
                )

        status = {
            'status': 'success',
            'num_keypoints_img1': len(kp1),
            'num_keypoints_img2': len(kp2),
            'num_matches': len(matches),
            'num_inliers': int(np.sum(inliers)) if inliers is not None else 0,
            'transform_type': transform_type,
            'transform_matrix': M,
        }

        return registered, status

    def compute_registration_quality(self, kp1, kp2, matches, mask):
        if len(matches) == 0 or mask is None:
            return {}

        inlier_ratio = np.sum(mask) / len(mask) if len(mask) > 0 else 0

        src_pts = np.float32([kp1[m.queryIdx].pt for m in matches])
        dst_pts = np.float32([kp2[m.trainIdx].pt for m in matches])

        if np.sum(mask) > 4:
            inlier_src = src_pts[mask.ravel() == 1]
            inlier_dst = dst_pts[mask.ravel() == 1]

            if len(inlier_src) > 0 and len(inlier_dst) > 0:
                distances = np.sqrt(
                    np.sum((inlier_src - inlier_dst) ** 2, axis=1)
                )
                mean_error = np.mean(distances)
                std_error = np.std(distances)
                rmse = np.sqrt(np.mean(distances ** 2))
            else:
                mean_error = float('inf')
                std_error = float('inf')
                rmse = float('inf')
        else:
            mean_error = float('inf')
            std_error = float('inf')
            rmse = float('inf')

        return {
            'inlier_ratio': float(inlier_ratio),
            'mean_error': float(mean_error),
            'std_error': float(std_error),
            'rmse': float(rmse),
            'num_inliers': int(np.sum(mask)),
            'num_matches': len(matches),
        }

    def multi_modal_registration(self, image1: np.ndarray, image2: np.ndarray):
        best_registered = image2.copy()
        best_quality = float('inf')
        best_status = None

        for max_feat in [2000, 5000, 10000]:
            self.max_features = max_feat
            if self.feature_type == 'SIFT':
                self.detector = cv2.SIFT_create(nfeatures=max_feat)

            for ratio in [0.6, 0.7, 0.75, 0.8]:
                self.good_match_ratio = ratio

                registered, status = self.register_images(image1, image2)

                if status['status'] == 'success':
                    kp1, des1 = self.detect_and_compute(image1)
                    kp2, des2 = self.detect_and_compute(registered)
                    matches = self.match_features(des1, des2)

                    if len(matches) >= 4:
                        _, mask = self.estimate_homography(kp1, kp2, matches)
                        if mask is not None and np.sum(mask) > 4:
                            quality = self.compute_registration_quality(
                                kp1, kp2, matches, mask
                            )
                            if quality.get('rmse', float('inf')) < best_quality:
                                best_quality = quality['rmse']
                                best_registered = registered
                                best_status = status
                                best_status['quality'] = quality

        return best_registered, best_status


def register_image_pair(image1_path, image2_path, output_path=None,
                        method='SIFT', verbose=True):
    from data_loader import read_geotiff, write_geotiff

    img1, proj, geotransform, w, h, bands = read_geotiff(image1_path)
    img2, _, _, _, _, _ = read_geotiff(image2_path)

    registrar = ImageRegistration(feature_type=method)
    registered, status = registrar.register_images(img1, img2)

    if verbose:
        print(f"配准状态: {status.get('status', 'unknown')}")
        if status.get('status') == 'success':
            print(f"  特征点数(图1): {status.get('num_keypoints_img1', 0)}")
            print(f"  特征点数(图2): {status.get('num_keypoints_img2', 0)}")
            print(f"  匹配数: {status.get('num_matches', 0)}")
            print(f"  内点数: {status.get('num_inliers', 0)}")
            print(f"  变换类型: {status.get('transform_type', 'unknown')}")

            if 'quality' in status:
                q = status['quality']
                print(f"  内点比例: {q.get('inlier_ratio', 0):.4f}")
                print(f"  平均误差: {q.get('mean_error', 0):.2f}")
                print(f"  RMSE: {q.get('rmse', 0):.2f}")

    if output_path:
        write_geotiff(output_path, registered, proj, geotransform)

    return registered, status
