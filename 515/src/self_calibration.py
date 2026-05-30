import os
import numpy as np
import cv2
from typing import Optional, Tuple, List, Dict, Any
from scipy.optimize import minimize, least_squares
from scipy.stats import trim_mean
from .distortion_models import (
    FisheyeDistortionModel,
    FisheyeProjectionType,
    create_projection_model,
    estimate_projection_type_from_fov,
)


class LineSegment:
    def __init__(self, points: np.ndarray, length: float, angle: float):
        self.points = points
        self.length = length
        self.angle = angle


def detect_line_segments(
    image: np.ndarray,
    min_length: int = 30,
    max_segments: int = 200,
) -> List[LineSegment]:
    if len(image.shape) == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    else:
        gray = image.copy()

    gray = cv2.GaussianBlur(gray, (3, 3), 0)

    lsd = cv2.createLineSegmentDetector(
        refine=cv2.LSD_REFINE_STD,
        scale=0.8,
        sigma_scale=0.6,
        quant=2.0,
        ang_th=22.5,
        log_eps=0.0,
        density_th=0.7,
        n_bins=1024,
    )

    lines, width, prec, nfa = lsd.detect(gray)

    if lines is None or len(lines) == 0:
        edges = cv2.Canny(gray, 50, 150, apertureSize=3)
        lines = cv2.HoughLinesP(
            edges,
            rho=1,
            theta=np.pi / 180,
            threshold=50,
            minLineLength=min_length,
            maxLineGap=10,
        )

        if lines is None:
            return []

        segments = []
        for line in lines:
            x1, y1, x2, y2 = line[0]
            points = np.array([[x1, y1], [x2, y2]], dtype=np.float64)
            length = np.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)
            if length >= min_length:
                angle = np.arctan2(y2 - y1, x2 - x1)
                segments.append(LineSegment(points, length, angle))

        return segments[:max_segments]

    segments = []
    for line in lines:
        x1, y1, x2, y2 = line[0]
        points = np.array([[x1, y1], [x2, y2]], dtype=np.float64)
        length = np.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)
        if length >= min_length:
            angle = np.arctan2(y2 - y1, x2 - x1)
            segments.append(LineSegment(points, length, angle))

    segments.sort(key=lambda s: s.length, reverse=True)
    return segments[:max_segments]


def sample_line_points(
    segment: LineSegment,
    num_samples: int = 20,
) -> np.ndarray:
    x1, y1 = segment.points[0]
    x2, y2 = segment.points[1]

    t = np.linspace(0, 1, num_samples)
    x = x1 + t * (x2 - x1)
    y = y1 + t * (y2 - y1)

    return np.stack([x, y], axis=-1)


def compute_straightness_error(
    points: np.ndarray,
) -> float:
    if len(points) < 3:
        return 0.0

    p1 = points[0]
    p2 = points[-1]

    line_vec = p2 - p1
    line_len = np.linalg.norm(line_vec)

    if line_len < 1e-6:
        return 0.0

    line_vec_norm = line_vec / line_len

    vecs = points - p1
    cross = np.cross(vecs, line_vec_norm)
    distances = np.abs(cross)

    return np.mean(distances)


def _self_calibration_residuals(
    params: np.ndarray,
    line_segments: List[LineSegment],
    image_shape: Tuple[int, int],
    projection_type: FisheyeProjectionType,
    num_samples: int = 20,
) -> np.ndarray:
    cx, cy, f = params

    try:
        model = create_projection_model(projection_type, f, (cx, cy))
    except Exception:
        return np.full(100, 1e6)

    residuals = []

    for segment in line_segments:
        if segment.length < 30:
            continue

        points = sample_line_points(segment, num_samples)

        try:
            angles = model.pixel_to_angle(points)
            theta = angles[..., 0]
            phi = angles[..., 1]

            mask = theta < np.pi / 2.2
            if not np.any(mask):
                continue

            theta = theta[mask]
            phi = phi[mask]

            if len(theta) < 5:
                continue

            x_undist = theta * np.cos(phi)
            y_undist = theta * np.sin(phi)
            undist_points = np.stack([x_undist, y_undist], axis=-1)

            error = compute_straightness_error(undist_points)
            weight = min(segment.length / 100.0, 2.0)
            residuals.append(error * weight)

        except Exception:
            continue

    if len(residuals) == 0:
        return np.full(100, 1e6)

    return np.array(residuals)


def self_calibrate_from_lines(
    image: np.ndarray,
    initial_center: Optional[Tuple[float, float]] = None,
    initial_focal: Optional[float] = None,
    projection_type: Optional[FisheyeProjectionType] = None,
    min_line_length: int = 40,
    max_segments: int = 150,
    num_samples: int = 25,
    verbose: bool = False,
) -> Dict[str, Any]:
    h, w = image.shape[:2]

    if initial_center is None:
        from .calibration import estimate_center_auto

        initial_center = estimate_center_auto(image)

    if initial_focal is None:
        from .calibration import estimate_focal_length_auto, estimate_fov_from_image

        fov = estimate_fov_from_image(image)
        initial_focal = estimate_focal_length_auto(
            image, initial_center, fov_degrees=fov
        )

    if projection_type is None:
        from .calibration import estimate_fov_from_image

        fov = estimate_fov_from_image(image)
        projection_type = estimate_projection_type_from_fov(fov)

    if verbose:
        print("Detecting line segments...")

    line_segments = detect_line_segments(
        image, min_length=min_line_length, max_segments=max_segments
    )

    if verbose:
        print(f"Found {len(line_segments)} line segments")

    if len(line_segments) < 5:
        if verbose:
            print("Not enough line segments, falling back to edge-based estimation")
        from .calibration import estimate_fisheye_params_auto

        return estimate_fisheye_params_auto(image)

    long_segments = [s for s in line_segments if s.length >= min_line_length]
    if len(long_segments) < 5:
        long_segments = line_segments[: min(10, len(line_segments))]

    if verbose:
        print(f"Using {len(long_segments)} segments for calibration")

    initial_params = [initial_center[0], initial_center[1], initial_focal]

    lower_bounds = [w * 0.25, h * 0.25, initial_focal * 0.4]
    upper_bounds = [w * 0.75, h * 0.75, initial_focal * 1.6]

    try:
        if verbose:
            print("Optimizing distortion parameters...")

        result = least_squares(
            _self_calibration_residuals,
            initial_params,
            bounds=(lower_bounds, upper_bounds),
            args=(long_segments, (h, w), projection_type, num_samples),
            max_nfev=300,
            verbose=2 if verbose else 0,
        )

        optimized_params = result.x
        center = (optimized_params[0], optimized_params[1])
        focal_length = optimized_params[2]

        final_residual = np.mean(np.abs(result.fun))

        if verbose:
            print(f"Optimization complete. Mean residual: {final_residual:.4f}")

        model = create_projection_model(projection_type, focal_length, center)

        from .calibration import estimate_fov_from_image

        fov = estimate_fov_from_image(image)

        return {
            "center": center,
            "focal_length": focal_length,
            "fov_degrees": fov,
            "projection_type": projection_type,
            "model": model,
            "mean_residual": final_residual,
            "num_segments_used": len(long_segments),
            "method": "line_self_calibration",
        }

    except Exception as e:
        if verbose:
            print(f"Optimization failed: {e}, falling back to edge-based estimation")

        from .calibration import estimate_fisheye_params_auto

        result = estimate_fisheye_params_auto(image)
        result["method"] = "edge_based_fallback"
        return result


def self_calibrate_from_multiple_images(
    image_paths: List[str],
    projection_type: Optional[FisheyeProjectionType] = None,
    verbose: bool = False,
) -> Dict[str, Any]:
    all_centers = []
    all_focals = []
    all_residuals = []

    for i, path in enumerate(image_paths):
        img = cv2.imread(path)
        if img is None:
            continue

        if verbose:
            print(f"\nProcessing image {i+1}/{len(image_paths)}: {os.path.basename(path)}")

        result = self_calibrate_from_lines(
            img,
            projection_type=projection_type,
            verbose=verbose,
        )

        all_centers.append(result["center"])
        all_focals.append(result["focal_length"])
        if "mean_residual" in result:
            all_residuals.append(result["mean_residual"])

    if len(all_centers) == 0:
        raise ValueError("No valid images found for calibration")

    if len(all_centers) >= 3:
        center = (trim_mean([c[0] for c in all_centers], 0.1), trim_mean([c[1] for c in all_centers], 0.1))
        focal_length = trim_mean(all_focals, 0.1)
    else:
        center = (np.mean([c[0] for c in all_centers]), np.mean([c[1] for c in all_centers]))
        focal_length = np.mean(all_focals)

    if all_residuals:
        mean_residual = np.mean(all_residuals)
    else:
        mean_residual = None

    from .calibration import estimate_fov_from_image

    first_img = cv2.imread(image_paths[0])
    fov = estimate_fov_from_image(first_img)

    if projection_type is None:
        projection_type = estimate_projection_type_from_fov(fov)

    model = create_projection_model(projection_type, focal_length, center)

    return {
        "center": center,
        "focal_length": focal_length,
        "fov_degrees": fov,
        "projection_type": projection_type,
        "model": model,
        "mean_residual": mean_residual,
        "num_images": len(all_centers),
        "method": "multi_image_line_self_calibration",
    }


def evaluate_calibration_quality(
    image: np.ndarray,
    model: FisheyeDistortionModel,
    num_segments: int = 50,
) -> Dict[str, Any]:
    line_segments = detect_line_segments(image, max_segments=num_segments)

    if len(line_segments) == 0:
        return {"quality_score": 0.0, "num_segments": 0}

    errors = []
    lengths = []

    for segment in line_segments:
        if segment.length < 20:
            continue

        points = sample_line_points(segment, 15)

        try:
            angles = model.pixel_to_angle(points)
            theta = angles[..., 0]
            phi = angles[..., 1]

            mask = theta < np.pi / 2.2
            if np.sum(mask) < 5:
                continue

            theta = theta[mask]
            phi = phi[mask]

            x_undist = theta * np.cos(phi)
            y_undist = theta * np.sin(phi)
            undist_points = np.stack([x_undist, y_undist], axis=-1)

            error = compute_straightness_error(undist_points)
            errors.append(error)
            lengths.append(segment.length)

        except Exception:
            continue

    if len(errors) == 0:
        return {"quality_score": 0.0, "num_segments": 0}

    errors = np.array(errors)
    lengths = np.array(lengths)

    weighted_error = np.sum(errors * lengths) / np.sum(lengths)
    quality_score = max(0.0, 1.0 - weighted_error / 5.0)

    return {
        "quality_score": quality_score,
        "mean_error": np.mean(errors),
        "weighted_error": weighted_error,
        "num_segments": len(errors),
        "errors": errors,
    }
