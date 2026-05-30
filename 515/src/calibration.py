import os
import glob
import numpy as np
import cv2
from scipy.optimize import least_squares, minimize
from typing import Optional, Tuple, List
from .distortion_models import (
    FisheyeProjectionType,
    create_projection_model,
    estimate_projection_type_from_fov,
)


class FisheyeCalibrator:
    def __init__(
        self,
        chessboard_size: Tuple[int, int] = (9, 6),
        square_size: float = 1.0,
    ):
        self.chessboard_size = chessboard_size
        self.square_size = square_size
        self.camera_matrix = None
        self.dist_coeffs = None
        self.rvecs = None
        self.tvecs = None
        self.focal_length = None
        self.center = None
        self.projection_type = None
        self.reprojection_error = None

    def _prepare_object_points(self) -> np.ndarray:
        objp = np.zeros(
            (1, self.chessboard_size[0] * self.chessboard_size[1], 3),
            dtype=np.float32,
        )
        objp[0, :, :2] = np.mgrid[
            0 : self.chessboard_size[0], 0 : self.chessboard_size[1]
        ].T.reshape(-1, 2)
        objp *= self.square_size
        return objp

    def calibrate_from_images(
        self,
        image_paths: List[str],
        projection_type: Optional[FisheyeProjectionType] = None,
        show_debug: bool = False,
    ) -> bool:
        objpoints = []
        imgpoints = []
        image_size = None

        objp = self._prepare_object_points()

        for image_path in image_paths:
            img = cv2.imread(image_path)
            if img is None:
                continue

            if image_size is None:
                image_size = (img.shape[1], img.shape[0])

            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

            ret, corners = cv2.findChessboardCorners(
                gray,
                self.chessboard_size,
                cv2.CALIB_CB_ADAPTIVE_THRESH
                + cv2.CALIB_CB_FAST_CHECK
                + cv2.CALIB_CB_NORMALIZE_IMAGE,
            )

            if ret:
                objpoints.append(objp)

                criteria = (
                    cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER,
                    100,
                    1e-3,
                )
                corners2 = cv2.cornerSubPix(gray, corners, (3, 3), (-1, -1), criteria)
                imgpoints.append(corners2)

                if show_debug:
                    img_debug = img.copy()
                    cv2.drawChessboardCorners(
                        img_debug, self.chessboard_size, corners2, ret
                    )
                    cv2.imshow("Chessboard", img_debug)
                    cv2.waitKey(500)

        if show_debug:
            cv2.destroyAllWindows()

        if len(objpoints) < 3:
            return False

        try:
            calibration_flags = (
                cv2.fisheye.CALIB_RECOMPUTE_EXTRINSIC
                + cv2.fisheye.CALIB_CHECK_COND
                + cv2.fisheye.CALIB_FIX_SKEW
            )
            K = np.zeros((3, 3))
            D = np.zeros((4, 1))
            rvecs = [np.zeros((1, 1, 3), dtype=np.float64) for _ in objpoints]
            tvecs = [np.zeros((1, 1, 3), dtype=np.float64) for _ in objpoints]

            criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 100, 1e-6)

            self.reprojection_error, K, D, rvecs, tvecs = cv2.fisheye.calibrate(
                objpoints,
                imgpoints,
                image_size,
                K,
                D,
                rvecs,
                tvecs,
                calibration_flags,
                criteria,
            )

            self.camera_matrix = K
            self.dist_coeffs = D
            self.rvecs = rvecs
            self.tvecs = tvecs
            self.focal_length = (K[0, 0] + K[1, 1]) / 2.0
            self.center = (K[0, 2], K[1, 2])

            if projection_type is None:
                fov = self._estimate_fov_from_calibration(image_size)
                self.projection_type = estimate_projection_type_from_fov(fov)
            else:
                self.projection_type = projection_type

            return True

        except Exception as e:
            print(f"Calibration failed: {e}")
            return False

    def _estimate_fov_from_calibration(self, image_size: Tuple[int, int]) -> float:
        if self.camera_matrix is None:
            return 180.0

        fx = self.camera_matrix[0, 0]
        fy = self.camera_matrix[1, 1]
        cx = self.camera_matrix[0, 2]
        cy = self.camera_matrix[1, 2]

        corners = np.array(
            [
                [0, 0],
                [image_size[0], 0],
                [0, image_size[1]],
                [image_size[0], image_size[1]],
            ],
            dtype=np.float32,
        )

        max_theta = 0
        for corner in corners:
            x = (corner[0] - cx) / fx
            y = (corner[1] - cy) / fy
            r = np.sqrt(x**2 + y**2)
            theta = 2.0 * np.arctan(r / 2.0)
            max_theta = max(max_theta, theta)

        return np.degrees(max_theta * 2)

    def get_projection_model(self):
        if self.focal_length is None or self.center is None:
            return None
        return create_projection_model(
            self.projection_type, self.focal_length, self.center
        )


def estimate_fov_from_image(
    image: np.ndarray,
) -> float:
    h, w = image.shape[:2]

    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image

    edges = cv2.Canny(gray, 50, 150)

    circles = cv2.HoughCircles(
        edges,
        cv2.HOUGH_GRADIENT,
        dp=1.2,
        minDist=min(w, h) // 4,
        param1=100,
        param2=30,
        minRadius=min(w, h) // 4,
        maxRadius=min(w, h) // 2,
    )

    if circles is not None:
        circles = np.round(circles[0, :]).astype("int")
        for (x, y, r) in circles:
            if r > min(w, h) // 3:
                max_radius = r
                center = (x, y)
                break
        else:
            max_radius = min(w, h) // 2
            center = (w // 2, h // 2)
    else:
        max_radius = min(w, h) // 2
        center = (w // 2, h // 2)

    corners = np.array(
        [
            [0, 0],
            [w, 0],
            [0, h],
            [w, h],
        ]
    )

    max_dist = 0
    for corner in corners:
        dist = np.sqrt((corner[0] - center[0]) ** 2 + (corner[1] - center[1]) ** 2)
        max_dist = max(max_dist, dist)

    if max_dist <= max_radius:
        fov = 180.0
    else:
        ratio = max_radius / max_dist
        fov = 180.0 * ratio

    return min(fov, 220.0)


def estimate_center_auto(
    image: np.ndarray,
) -> Tuple[float, float]:
    h, w = image.shape[:2]

    if len(image.shape) == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    else:
        gray = image.copy()

    blurred = cv2.GaussianBlur(gray, (15, 15), 0)

    _, thresh = cv2.threshold(blurred, 20, 255, cv2.THRESH_BINARY)

    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    if contours:
        largest_contour = max(contours, key=cv2.contourArea)
        M = cv2.moments(largest_contour)
        if M["m00"] != 0:
            cx = M["m10"] / M["m00"]
            cy = M["m01"] / M["m00"]
            return (cx, cy)

    return (w / 2.0, h / 2.0)


def estimate_focal_length_auto(
    image: np.ndarray,
    center: Tuple[float, float],
    fov_degrees: float = 180.0,
    projection_type: FisheyeProjectionType = FisheyeProjectionType.EQUISOLID,
) -> float:
    h, w = image.shape[:2]

    corners = np.array(
        [
            [0, 0],
            [w, 0],
            [0, h],
            [w, h],
        ],
        dtype=np.float64,
    )

    centered = corners - np.array(center)
    r = np.sqrt(centered[:, 0] ** 2 + centered[:, 1] ** 2)
    max_r = np.max(r)

    theta_max = np.radians(fov_degrees / 2.0)

    model = create_projection_model(projection_type, 1.0, (0, 0))
    r_normalized = model.project(np.array([theta_max]))[0]

    focal_length = max_r / r_normalized

    return focal_length


def _residual_function(
    params: np.ndarray,
    edges: List[np.ndarray],
    image_shape: Tuple[int, int],
) -> np.ndarray:
    cx, cy, f, fov = params
    center = (cx, cy)

    h, w = image_shape
    model = create_projection_model(
        FisheyeProjectionType.EQUISOLID, f, center
    )

    residuals = []
    theta_max = np.radians(fov / 2.0)

    for edge_points in edges:
        if len(edge_points) < 10:
            continue

        angles = model.pixel_to_angle(edge_points)
        thetas = angles[:, 0]

        edge_residuals = thetas - theta_max
        residuals.extend(edge_residuals)

    if len(residuals) == 0:
        return np.array([1e6])

    return np.array(residuals)


def estimate_fisheye_params_auto(
    image: np.ndarray,
    initial_fov: Optional[float] = None,
) -> dict:
    h, w = image.shape[:2]

    center = estimate_center_auto(image)

    if initial_fov is None:
        fov = estimate_fov_from_image(image)
    else:
        fov = initial_fov

    projection_type = estimate_projection_type_from_fov(fov)

    focal_length = estimate_focal_length_auto(image, center, fov, projection_type)

    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image
    edges = cv2.Canny(gray, 50, 150)
    edge_points = np.column_stack(np.where(edges > 0)).astype(np.float64)
    edge_points = edge_points[:, ::-1]

    if len(edge_points) > 500:
        indices = np.random.choice(len(edge_points), 500, replace=False)
        edge_points = edge_points[indices]

    try:
        initial_params = [center[0], center[1], focal_length, fov]
        lower_bounds = [w * 0.3, h * 0.3, focal_length * 0.5, 90.0]
        upper_bounds = [w * 0.7, h * 0.7, focal_length * 1.5, 220.0]

        result = least_squares(
            _residual_function,
            initial_params,
            bounds=(lower_bounds, upper_bounds),
            args=([edge_points], (h, w)),
            max_nfev=200,
        )

        optimized_params = result.x
        center = (optimized_params[0], optimized_params[1])
        focal_length = optimized_params[2]
        fov = optimized_params[3]
        projection_type = estimate_projection_type_from_fov(fov)

    except Exception as e:
        print(f"Optimization failed, using initial estimates: {e}")

    return {
        "center": center,
        "focal_length": focal_length,
        "fov_degrees": fov,
        "projection_type": projection_type,
        "model": create_projection_model(projection_type, focal_length, center),
    }


def estimate_params_from_multiple_images(
    image_paths: List[str],
) -> dict:
    centers = []
    focal_lengths = []
    fovs = []

    for path in image_paths:
        img = cv2.imread(path)
        if img is None:
            continue

        params = estimate_fisheye_params_auto(img)
        centers.append(params["center"])
        focal_lengths.append(params["focal_length"])
        fovs.append(params["fov_degrees"])

    if len(centers) == 0:
        raise ValueError("No valid images found")

    avg_center = (np.mean([c[0] for c in centers]), np.mean([c[1] for c in centers]))
    avg_focal = np.mean(focal_lengths)
    avg_fov = np.mean(fovs)
    projection_type = estimate_projection_type_from_fov(avg_fov)

    return {
        "center": avg_center,
        "focal_length": avg_focal,
        "fov_degrees": avg_fov,
        "projection_type": projection_type,
        "model": create_projection_model(projection_type, avg_focal, avg_center),
    }
