import cv2
import numpy as np
import glob
import os
from typing import List, Tuple, Optional


class CameraCalibrator:
    def __init__(self, chessboard_size: Tuple[int, int] = (9, 6),
                 square_size: float = 1.0):
        self.chessboard_size = chessboard_size
        self.square_size = square_size
        
        self.camera_matrix = None
        self.dist_coeffs = None
        self.rvecs = None
        self.tvecs = None
        self.reproj_error = None
        
        self.objp = None
        self._prepare_object_points()

    def _prepare_object_points(self):
        objp = np.zeros((self.chessboard_size[0] * self.chessboard_size[1], 3), np.float32)
        objp[:, :2] = np.mgrid[0:self.chessboard_size[0], 
                               0:self.chessboard_size[1]].T.reshape(-1, 2)
        objp *= self.square_size
        self.objp = objp

    def detect_chessboard(self, image: np.ndarray, 
                          show_result: bool = False) -> Tuple[bool, Optional[np.ndarray]]:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image
        
        flags = cv2.CALIB_CB_ADAPTIVE_THRESH + cv2.CALIB_CB_NORMALIZE_IMAGE + cv2.CALIB_CB_FAST_CHECK
        ret, corners = cv2.findChessboardCorners(gray, self.chessboard_size, flags)
        
        if ret:
            criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 0.001)
            corners = cv2.cornerSubPix(gray, corners, (11, 11), (-1, -1), criteria)
            
            if show_result:
                cv2.drawChessboardCorners(image, self.chessboard_size, corners, ret)
            
            return True, corners
        
        return False, None

    def calibrate_from_images(self, image_paths: List[str], 
                              verbose: bool = True) -> Tuple[np.ndarray, np.ndarray]:
        objpoints = []
        imgpoints = []
        
        valid_images = []
        
        for i, path in enumerate(image_paths):
            img = cv2.imread(path)
            if img is None:
                continue
            
            ret, corners = self.detect_chessboard(img)
            
            if ret:
                objpoints.append(self.objp.copy())
                imgpoints.append(corners)
                valid_images.append(path)
                if verbose:
                    print(f'  检测成功: {os.path.basename(path)}')
            else:
                if verbose:
                    print(f'  检测失败: {os.path.basename(path)}')
        
        if len(objpoints) < 3:
            raise ValueError(f'至少需要3张有效标定图像，当前只有 {len(objpoints)} 张')
        
        if verbose:
            print(f'\n使用 {len(objpoints)} 张图像进行标定...')
        
        first_img = cv2.imread(image_paths[0])
        h, w = first_img.shape[:2]
        
        self.reproj_error, self.camera_matrix, self.dist_coeffs, self.rvecs, self.tvecs = \
            cv2.calibrateCamera(objpoints, imgpoints, (w, h), None, None)
        
        if verbose:
            print(f'重投影误差: {self.reproj_error:.4f}')
            print(f'相机矩阵:\n{self.camera_matrix}')
            print(f'畸变系数: {self.dist_coeffs.ravel()}')
        
        return self.camera_matrix, self.dist_coeffs

    def calibrate_from_chessboard_video(self, video_path: str, 
                                        max_frames: int = 50,
                                        frame_interval: int = 10,
                                        verbose: bool = True) -> Tuple[np.ndarray, np.ndarray]:
        cap = cv2.VideoCapture(video_path)
        
        if not cap.isOpened():
            raise ValueError(f'无法打开视频: {video_path}')
        
        objpoints = []
        imgpoints = []
        frame_count = 0
        valid_count = 0
        
        while valid_count < max_frames:
            ret, frame = cap.read()
            
            if not ret:
                break
            
            frame_count += 1
            
            if frame_count % frame_interval != 0:
                continue
            
            success, corners = self.detect_chessboard(frame)
            
            if success:
                objpoints.append(self.objp.copy())
                imgpoints.append(corners)
                valid_count += 1
                
                if verbose:
                    print(f'  帧 {frame_count}: 检测成功 (累计 {valid_count})')
        
        cap.release()
        
        if len(objpoints) < 3:
            raise ValueError(f'视频中只检测到 {len(objpoints)} 帧有效棋盘格，至少需要3帧')
        
        if verbose:
            print(f'\n使用 {len(objpoints)} 帧进行标定...')
        
        h, w = frame.shape[:2]
        
        self.reproj_error, self.camera_matrix, self.dist_coeffs, self.rvecs, self.tvecs = \
            cv2.calibrateCamera(objpoints, imgpoints, (w, h), None, None)
        
        if verbose:
            print(f'重投影误差: {self.reproj_error:.4f}')
            print(f'相机矩阵:\n{self.camera_matrix}')
            print(f'畸变系数: {self.dist_coeffs.ravel()}')
        
        return self.camera_matrix, self.dist_coeffs

    def undistort_image(self, image: np.ndarray) -> np.ndarray:
        if self.camera_matrix is None or self.dist_coeffs is None:
            return image
        
        h, w = image.shape[:2]
        newcameramtx, roi = cv2.getOptimalNewCameraMatrix(
            self.camera_matrix, self.dist_coeffs, (w, h), 0, (w, h))
        
        undistorted = cv2.undistort(image, self.camera_matrix, self.dist_coeffs, 
                                    None, newcameramtx)
        
        x, y, w, h = roi
        if w > 0 and h > 0:
            undistorted = undistorted[y:y+h, x:x+w]
        
        return undistorted

    def estimate_focal_length(self, image_shape: Tuple[int, int]) -> float:
        if self.camera_matrix is not None:
            fx = self.camera_matrix[0, 0]
            fy = self.camera_matrix[1, 1]
            return (fx + fy) / 2.0
        
        h, w = image_shape[:2]
        return max(w, h) / 2.0

    def save_calibration(self, filepath: str):
        if self.camera_matrix is None:
            raise ValueError('尚未进行标定')
        
        np.savez(filepath, 
                 camera_matrix=self.camera_matrix,
                 dist_coeffs=self.dist_coeffs,
                 reproj_error=self.reproj_error)
        print(f'标定参数已保存到: {filepath}')

    def load_calibration(self, filepath: str):
        if not os.path.exists(filepath):
            raise FileNotFoundError(f'标定文件不存在: {filepath}')
        
        data = np.load(filepath)
        self.camera_matrix = data['camera_matrix']
        self.dist_coeffs = data['dist_coeffs']
        self.reproj_error = float(data['reproj_error'])
        
        print(f'标定参数已从 {filepath} 加载')
        print(f'相机矩阵:\n{self.camera_matrix}')
        
        return self.camera_matrix, self.dist_coeffs

    def auto_calibrate_from_scene(self, images: List[np.ndarray],
                                  verbose: bool = True) -> Tuple[np.ndarray, np.ndarray]:
        if len(images) < 2:
            raise ValueError('需要至少2张图像进行自动标定')
        
        h, w = images[0].shape[:2]
        
        if self.camera_matrix is not None:
            if verbose:
                print('使用已有的标定参数')
            return self.camera_matrix, self.dist_coeffs
        
        if verbose:
            print('尝试从场景特征自动估计相机参数...')
        
        focal_length = self._estimate_focal_from_features(images)
        
        cx = w / 2.0
        cy = h / 2.0
        
        self.camera_matrix = np.array([
            [focal_length, 0, cx],
            [0, focal_length, cy],
            [0, 0, 1]
        ], dtype=np.float64)
        
        self.dist_coeffs = np.zeros((5, 1), dtype=np.float64)
        
        if verbose:
            print(f'估计焦距: {focal_length:.1f}')
            print(f'相机矩阵:\n{self.camera_matrix}')
        
        return self.camera_matrix, self.dist_coeffs

    def _estimate_focal_from_features(self, images: List[np.ndarray]) -> float:
        from feature_matcher import FeatureMatcher
        from homography import HomographyEstimator
        
        matcher = FeatureMatcher()
        estimator = HomographyEstimator()
        
        all_focals = []
        
        for i in range(len(images) - 1):
            img1 = images[i]
            img2 = images[i + 1]
            
            kp1, des1 = matcher.detect_and_compute(img1)
            kp2, des2 = matcher.detect_and_compute(img2)
            
            matches = matcher.match_features(des1, des2)
            
            if len(matches) < 20:
                continue
            
            pts1, pts2 = matcher.get_matched_points(kp1, kp2, matches)
            
            H, mask = estimator.estimate_homography(pts1, pts2)
            
            if H is None:
                continue
            
            inliers = mask.ravel() == 1
            pts1_inliers = pts1[inliers].reshape(-1, 2)
            pts2_inliers = pts2[inliers].reshape(-1, 2)
            
            if len(pts1_inliers) < 10:
                continue
            
            focal = self._focals_from_homography(H, pts1_inliers, pts2_inliers, img1.shape)
            
            if focal > 0:
                all_focals.append(focal)
        
        if all_focals:
            return np.median(all_focals)
        
        h, w = images[0].shape[:2]
        return max(w, h) / 2.0

    def _focals_from_homography(self, H: np.ndarray, 
                                pts1: np.ndarray, pts2: np.ndarray,
                                img_shape: Tuple[int, int]) -> float:
        h, w = img_shape[:2]
        cx, cy = w / 2.0, h / 2.0
        
        pts1_c = pts1 - np.array([cx, cy])
        pts2_c = pts2 - np.array([cx, cy])
        
        d1 = np.sqrt(np.sum(pts1_c ** 2, axis=1))
        d2 = np.sqrt(np.sum(pts2_c ** 2, axis=1))
        
        valid = (d1 > 0) & (d2 > 0)
        if np.sum(valid) < 10:
            return -1
        
        scale_ratios = d2[valid] / d1[valid]
        median_ratio = np.median(scale_ratios)
        
        estimated_focal = w / (2.0 * np.tan(np.pi / 6))
        
        return estimated_focal

    def correct_distortion(self, image: np.ndarray) -> np.ndarray:
        return self.undistort_image(image)
