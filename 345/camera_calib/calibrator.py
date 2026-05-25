"""Camera calibration using OpenCV.

Supports chessboard, symmetric circle-grid and asymmetric circle-grid
targets, mono and stereo (binocular) calibration, stereo rectification
and disparity computation, plus a quality report with per-view anomaly
flags and an overall confidence score.

Typical usage::

    calibrator = CameraCalibrator(pattern_size=(9, 6), square_size=25.0)
    for path in image_paths:
        calibrator.add_image(path)
    result = calibrator.calibrate()
    report = result.quality_report()
    print(report.confidence_score)
    result.save("calibration.json")
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional, Tuple

import cv2
import numpy as np


SUPPORTED_EXT = {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff"}


class PatternType(str, Enum):
    """Supported calibration target geometries."""

    CHESSBOARD = "chessboard"
    CIRCLES_SYMMETRIC = "circles_symmetric"
    CIRCLES_ASYMMETRIC = "circles_asymmetric"


@dataclass
class CalibrationResult:
    """Container for the output of :meth:`CameraCalibrator.calibrate`."""

    camera_matrix: np.ndarray
    dist_coeffs: np.ndarray
    rvecs: List[np.ndarray]
    tvecs: List[np.ndarray]
    reprojection_error: float
    per_view_errors: List[float]
    image_size: Tuple[int, int]
    pattern_size: Tuple[int, int]
    square_size: float
    image_paths: List[str]
    pattern_type: PatternType = PatternType.CHESSBOARD
    alpha: float = 0.5
    new_camera_matrix: Optional[np.ndarray] = None
    roi: Optional[Tuple[int, int, int, int]] = None

    # ---- Helpers ---------------------------------------------------------

    @property
    def focal_lengths_px(self) -> Tuple[float, float]:
        """Return ``(fx, fy)`` in pixels."""
        return float(self.camera_matrix[0, 0]), float(self.camera_matrix[1, 1])

    @property
    def principal_point_px(self) -> Tuple[float, float]:
        """Return ``(cx, cy)`` in pixels."""
        return float(self.camera_matrix[0, 2]), float(self.camera_matrix[1, 2])

    def undistort(self, image: np.ndarray, alpha: Optional[float] = None) -> np.ndarray:
        """Return an undistorted copy of *image*.

        Parameters
        ----------
        alpha:
            Scaling factor passed to ``cv2.getOptimalNewCameraMatrix``:
            ``0`` → crop to valid pixels only (no black border),
            ``1`` → keep the full original field of view (may include
            black borders), values in between give a balanced result.
            Defaults to the ``alpha`` stored with the result (0.5).
        """
        recompute = (alpha is not None and alpha != self.alpha) \
                    or self.new_camera_matrix is None
        if recompute:
            if alpha is not None:
                self.alpha = float(alpha)
            self._compute_new_camera_matrix(image.shape[:2][::-1])
        return cv2.undistort(
            image, self.camera_matrix, self.dist_coeffs, None, self.new_camera_matrix
        )

    def _compute_new_camera_matrix(self, image_size: Tuple[int, int]) -> None:
        newcameramtx, roi = cv2.getOptimalNewCameraMatrix(
            self.camera_matrix,
            self.dist_coeffs,
            image_size,
            self.alpha,
            image_size,
        )
        self.new_camera_matrix = newcameramtx
        self.roi = roi

    # ---- Quality report ------------------------------------------------

    def quality_report(self) -> "QualityReport":
        """Compute a :class:`QualityReport` for this calibration.

        The report combines reprojection-error statistics, a per-view
        anomaly flag (values above ``mean + 2 * std``), focal-length
        symmetry and an overall ``confidence_score`` in ``[0, 1]``.
        """
        return QualityReport.from_result(self)

    # ---- Serialisation ---------------------------------------------------

    def to_dict(self) -> Dict:
        data = {
            "camera_matrix": self.camera_matrix.tolist(),
            "dist_coeffs": self.dist_coeffs.ravel().tolist(),
            "rvecs": [r.ravel().tolist() for r in self.rvecs],
            "tvecs": [t.ravel().tolist() for t in self.tvecs],
            "reprojection_error": self.reprojection_error,
            "per_view_errors": self.per_view_errors,
            "image_size": list(self.image_size),
            "pattern_size": list(self.pattern_size),
            "square_size": self.square_size,
            "image_paths": self.image_paths,
            "pattern_type": self.pattern_type.value,
            "alpha": self.alpha,
            "focal_lengths_px": list(self.focal_lengths_px),
            "principal_point_px": list(self.principal_point_px),
        }
        if self.new_camera_matrix is not None:
            data["new_camera_matrix"] = self.new_camera_matrix.tolist()
        if self.roi is not None:
            data["roi"] = list(self.roi)
        return data

    def save(self, path: str) -> None:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2, ensure_ascii=False)

    @staticmethod
    def load(path: str) -> "CalibrationResult":
        with open(path, "r", encoding="utf-8") as f:
            d = json.load(f)
        return CalibrationResult(
            camera_matrix=np.array(d["camera_matrix"], dtype=np.float64),
            dist_coeffs=np.array(d["dist_coeffs"], dtype=np.float64).reshape(1, -1),
            rvecs=[np.array(r, dtype=np.float64).reshape(3, 1) for r in d["rvecs"]],
            tvecs=[np.array(t, dtype=np.float64).reshape(3, 1) for t in d["tvecs"]],
            reprojection_error=float(d["reprojection_error"]),
            per_view_errors=[float(e) for e in d["per_view_errors"]],
            image_size=tuple(d["image_size"]),
            pattern_size=tuple(d["pattern_size"]),
            square_size=float(d["square_size"]),
            image_paths=list(d["image_paths"]),
            pattern_type=PatternType(d.get("pattern_type", "chessboard")),
            alpha=float(d.get("alpha", 0.5)),
            new_camera_matrix=(
                np.array(d["new_camera_matrix"], dtype=np.float64)
                if "new_camera_matrix" in d and d["new_camera_matrix"] is not None
                else None
            ),
            roi=tuple(d["roi"]) if d.get("roi") else None,
        )


class CameraCalibrator:
    """Detect calibration pattern features and calibrate a camera.

    Supports chessboard, symmetric circle-grid and asymmetric
    circle-grid targets.

    Parameters
    ----------
    pattern_size:
        ``(nx, ny)`` – number of inner corners / circles in each direction.
    square_size:
        Physical size of a chessboard square / circle spacing in mm.
    pattern_type:
        One of :class:`PatternType`.
    """

    def __init__(
        self,
        pattern_size: Tuple[int, int] = (9, 6),
        square_size: float = 25.0,
        use_clahe: bool = True,
        clahe_clip: float = 2.0,
        clahe_grid: Tuple[int, int] = (8, 8),
        pattern_type: PatternType = PatternType.CHESSBOARD,
    ) -> None:
        if pattern_size[0] < 3 or pattern_size[1] < 3:
            raise ValueError("pattern_size must be at least (3, 3)")
        if square_size <= 0:
            raise ValueError("square_size must be positive")

        self.pattern_size: Tuple[int, int] = tuple(pattern_size)  # type: ignore[assignment]
        self.square_size: float = float(square_size)
        self.pattern_type: PatternType = pattern_type
        self.use_clahe: bool = bool(use_clahe)
        self.clahe: Optional[cv2.CLAHE] = None
        if self.use_clahe:
            clip = float(clahe_clip)
            grid = (int(clahe_grid[0]), int(clahe_grid[1]))
            if clip <= 0 or grid[0] <= 0 or grid[1] <= 0:
                raise ValueError("clahe_clip and clahe_grid must be positive")
            self.clahe = cv2.createCLAHE(clipLimit=clip, tileGridSize=grid)

        self._objp_template: np.ndarray = self._build_object_points()

        self._object_points: List[np.ndarray] = []
        self._image_points: List[np.ndarray] = []
        self._image_paths: List[str] = []
        self._image_size: Optional[Tuple[int, int]] = None
        self._annotated_images: Dict[str, np.ndarray] = {}
        self._preprocessed_images: Dict[str, np.ndarray] = {}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @property
    def num_valid_images(self) -> int:
        return len(self._image_points)

    @property
    def annotated_images(self) -> Dict[str, np.ndarray]:
        """Images with detected pattern features drawn on them."""
        return dict(self._annotated_images)

    @property
    def preprocessed_images(self) -> Dict[str, np.ndarray]:
        """CLAHE-enhanced grayscale images used for feature detection."""
        return dict(self._preprocessed_images)

    def reset(self) -> None:
        self._object_points.clear()
        self._image_points.clear()
        self._image_paths.clear()
        self._image_size = None
        self._annotated_images.clear()
        self._preprocessed_images.clear()

    def add_image(self, path: str) -> Tuple[bool, str]:
        """Detect and store calibration pattern features for *path*.

        Per-image failures are isolated and do not propagate to the caller
        (they are reported via the returned ``(success, message)`` tuple).

        Returns
        -------
        (success, message)
        """
        try:
            return self._add_image_internal(path)
        except Exception as exc:  # pragma: no cover - defensive
            return False, f"Unexpected error: {exc!r}"

    def _add_image_internal(self, path: str) -> Tuple[bool, str]:
        if not os.path.isfile(path):
            return False, f"File not found: {path}"

        ext = os.path.splitext(path)[1].lower()
        if ext not in SUPPORTED_EXT:
            return False, f"Unsupported format: {ext}"

        img = cv2.imread(path, cv2.IMREAD_COLOR)
        if img is None:
            return False, f"Failed to decode image: {path}"

        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        if self._image_size is None:
            self._image_size = (gray.shape[1], gray.shape[0])
        elif self._image_size != (gray.shape[1], gray.shape[0]):
            return False, (
                f"Image size mismatch for {path}: expected {self._image_size}, "
                f"got {(gray.shape[1], gray.shape[0])}"
            )

        # Adaptive histogram equalization to boost local contrast.
        gray_for_detect = gray
        if self.clahe is not None:
            gray_enhanced = self.clahe.apply(gray)
            self._preprocessed_images[path] = gray_enhanced
            gray_for_detect = gray_enhanced

        found, points = self._detect_pattern(gray_for_detect)
        if not found and self.clahe is not None:
            found, points = self._detect_pattern(gray)

        if not found:
            label = {
                PatternType.CHESSBOARD: "Chessboard",
                PatternType.CIRCLES_SYMMETRIC: "Symmetric circle grid",
                PatternType.CIRCLES_ASYMMETRIC: "Asymmetric circle grid",
            }[self.pattern_type]
            return False, f"{label} not detected in {path}"

        self._object_points.append(self._objp_template.copy())
        self._image_points.append(points)
        self._image_paths.append(path)

        annotated = img.copy()
        self._draw_pattern(annotated, points, found)
        self._annotated_images[path] = annotated

        return True, "OK"

    def _detect_pattern(self, gray: np.ndarray) -> Tuple[bool, np.ndarray]:
        """Dispatch detection to the correct OpenCV function."""
        if self.pattern_type == PatternType.CHESSBOARD:
            flags = (
                cv2.CALIB_CB_ADAPTIVE_THRESH
                + cv2.CALIB_CB_NORMALIZE_IMAGE
                + cv2.CALIB_CB_FAST_CHECK
            )
            found, corners = cv2.findChessboardCorners(
                gray, self.pattern_size, flags
            )
            if not found:
                return False, np.empty((0, 1, 2), dtype=np.float32)
            criteria = (
                cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER,
                30,
                0.001,
            )
            corners = cv2.cornerSubPix(gray, corners, (11, 11), (-1, -1), criteria)
            return True, corners

        if self.pattern_type == PatternType.CIRCLES_SYMMETRIC:
            flags = cv2.CALIB_CB_SYMMETRIC_GRID + cv2.CALIB_CB_CLUSTERING
            found, centers = cv2.findCirclesGrid(gray, self.pattern_size, flags)
            return bool(found), centers if found else np.empty((0, 1, 2), dtype=np.float32)

        if self.pattern_type == PatternType.CIRCLES_ASYMMETRIC:
            flags = cv2.CALIB_CB_ASYMMETRIC_GRID + cv2.CALIB_CB_CLUSTERING
            found, centers = cv2.findCirclesGrid(gray, self.pattern_size, flags)
            return bool(found), centers if found else np.empty((0, 1, 2), dtype=np.float32)

        raise ValueError(f"Unknown pattern_type: {self.pattern_type}")

    def _draw_pattern(
        self, image: np.ndarray, points: np.ndarray, found: bool
    ) -> None:
        if self.pattern_type == PatternType.CHESSBOARD:
            cv2.drawChessboardCorners(image, self.pattern_size, points, found)
        else:
            if found and points is not None and len(points) > 0:
                pts = points.reshape(-1, 2).astype(np.int32)
                for i, (x, y) in enumerate(pts):
                    cv2.circle(image, (int(x), int(y)), 6, (0, 255, 0), 2)
                    cv2.putText(
                        image, str(i), (int(x) + 6, int(y) - 6),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 255), 1,
                        cv2.LINE_AA,
                    )
                # Connect in order to visualize layout.
                for i in range(len(pts) - 1):
                    cv2.line(
                        image,
                        (int(pts[i][0]), int(pts[i][1])),
                        (int(pts[i + 1][0]), int(pts[i + 1][1])),
                        (255, 0, 0), 1,
                    )

    def add_images(self, paths: List[str]) -> List[Tuple[str, bool, str]]:
        """Add multiple images and return a list of ``(path, success, msg)``."""
        results: List[Tuple[str, bool, str]] = []
        for p in paths:
            ok, msg = self.add_image(p)
            results.append((p, ok, msg))
        return results

    def add_directory(self, directory: str) -> List[Tuple[str, bool, str]]:
        """Add every supported image file inside *directory*."""
        if not os.path.isdir(directory):
            raise FileNotFoundError(directory)
        paths = sorted(
            os.path.join(directory, f)
            for f in os.listdir(directory)
            if os.path.splitext(f)[1].lower() in SUPPORTED_EXT
        )
        return self.add_images(paths)

    def calibrate(self, alpha: float = 0.5) -> CalibrationResult:
        """Run calibration and return a :class:`CalibrationResult`.

        Parameters
        ----------
        alpha:
            Scaling factor for ``getOptimalNewCameraMatrix`` in the
            resulting :class:`CalibrationResult` (default ``0.5``,
            balanced between crop and full FOV).

        Raises
        ------
        RuntimeError
            If fewer than two valid images have been collected.
        """
        if not (0.0 <= float(alpha) <= 1.0):
            raise ValueError("alpha must be between 0.0 and 1.0")
        if self.num_valid_images < 2:
            raise RuntimeError(
                "At least 2 images with detected patterns are required "
                f"(found {self.num_valid_images})."
            )
        if self._image_size is None:
            raise RuntimeError("No images have been added yet.")

        h, w = (self._image_size[1], self._image_size[0])
        camera_matrix = np.eye(3, dtype=np.float64)
        dist_coeffs = np.zeros((5, 1), dtype=np.float64)

        flags = 0
        flags |= cv2.CALIB_FIX_K4
        flags |= cv2.CALIB_FIX_K5

        rms, camera_matrix, dist_coeffs, rvecs, tvecs = cv2.calibrateCamera(
            self._object_points,
            self._image_points,
            (w, h),
            camera_matrix,
            dist_coeffs,
            flags=flags,
            criteria=(
                cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER,
                100,
                1e-6,
            ),
        )

        per_view_errors = self._per_view_reprojection_errors(
            self._object_points, self._image_points, rvecs, tvecs,
            camera_matrix, dist_coeffs,
        )

        result = CalibrationResult(
            camera_matrix=camera_matrix,
            dist_coeffs=dist_coeffs,
            rvecs=list(rvecs),
            tvecs=list(tvecs),
            reprojection_error=float(rms),
            per_view_errors=per_view_errors,
            image_size=(w, h),
            pattern_size=self.pattern_size,
            square_size=self.square_size,
            image_paths=list(self._image_paths),
            pattern_type=self.pattern_type,
            alpha=float(alpha),
        )
        result._compute_new_camera_matrix((w, h))
        return result

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _build_object_points(self) -> np.ndarray:
        nx, ny = self.pattern_size
        if self.pattern_type == PatternType.CIRCLES_ASYMMETRIC:
            # Asymmetric grid: every second row is offset by half a spacing.
            n_points = nx * ny
            objp = np.zeros((n_points, 3), np.float32)
            idx = 0
            for j in range(ny):
                for i in range(nx):
                    x = i * self.square_size
                    y = j * self.square_size
                    if j % 2 == 1:
                        x += self.square_size / 2.0
                    objp[idx, 0] = x
                    objp[idx, 1] = y
                    idx += 1
            return objp

        # Chessboard or symmetric circle grid.
        objp = np.zeros((nx * ny, 3), np.float32)
        grid = np.mgrid[0:nx, 0:ny].T.reshape(-1, 2)
        objp[:, :2] = grid * self.square_size
        return objp

    @staticmethod
    def _per_view_reprojection_errors(
        object_points: List[np.ndarray],
        image_points: List[np.ndarray],
        rvecs: List[np.ndarray],
        tvecs: List[np.ndarray],
        camera_matrix: np.ndarray,
        dist_coeffs: np.ndarray,
    ) -> List[float]:
        errors: List[float] = []
        for objp, imgp, rvec, tvec in zip(
            object_points, image_points, rvecs, tvecs
        ):
            proj, _ = cv2.projectPoints(
                objp, rvec, tvec, camera_matrix, dist_coeffs
            )
            err = cv2.norm(imgp, proj, cv2.NORM_L2) / len(proj)
            errors.append(float(err))
        return errors


# ======================================================================
# Quality report
# ======================================================================


@dataclass
class QualityReport:
    """Statistical assessment of a :class:`CalibrationResult`.

    Attributes
    ----------
    num_views:
        Number of calibration views that contributed to the result.
    mean_error:
        Average per-view reprojection error in pixels.
    std_error:
        Standard deviation of per-view reprojection errors.
    min_error, max_error:
        Minimum / maximum per-view error.
    threshold:
        ``mean + 2 * std`` – views above this are flagged as anomalous.
    anomaly_indices:
        Indices of views whose reprojection error exceeds ``threshold``.
    anomaly_paths:
        File paths of the views flagged as anomalies.
    fx_fy_ratio:
        ``fx / fy`` – a value close to 1.0 indicates low pixel-aspect
        skew (good).
    principal_point_offset_px:
        Euclidean distance of ``(cx, cy)`` from the image centre.
    confidence_score:
        Score in ``[0, 1]`` aggregating all of the above metrics.
    confidence_label:
        Human-readable label (``Excellent`` / ``Good`` / ``Fair`` /
        ``Poor``).
    """

    num_views: int
    mean_error: float
    std_error: float
    min_error: float
    max_error: float
    threshold: float
    anomaly_indices: List[int]
    anomaly_paths: List[str]
    fx_fy_ratio: float
    principal_point_offset_px: float
    confidence_score: float
    confidence_label: str

    @staticmethod
    def from_result(result: CalibrationResult) -> "QualityReport":
        errors = np.asarray(result.per_view_errors, dtype=np.float64)
        n = len(errors)

        mean_err = float(errors.mean()) if n > 0 else 0.0
        std_err = float(errors.std(ddof=0)) if n > 1 else 0.0
        min_err = float(errors.min()) if n > 0 else 0.0
        max_err = float(errors.max()) if n > 0 else 0.0
        threshold = mean_err + 2.0 * std_err

        anomaly_indices = [
            i for i, e in enumerate(result.per_view_errors) if e > threshold
        ]
        anomaly_paths = [result.image_paths[i] for i in anomaly_indices]

        fx, fy = result.focal_lengths_px
        cx, cy = result.principal_point_px
        w, h = result.image_size
        aspect = fx / fy if fy != 0 else 1.0
        cx_offset = np.hypot(cx - w / 2.0, cy - h / 2.0)

        # ---- Confidence score ---------------------------------------
        # 1. RMS error: < 0.3 → full score, > 2.0 → zero.
        rmse = result.reprojection_error
        score_rms = max(0.0, min(1.0, (2.0 - rmse) / 1.7)) if rmse <= 2.0 else 0.0

        # 2. View count: ≥ 20 → full score, < 3 → zero.
        score_views = max(0.0, min(1.0, (n - 3) / 17.0)) if n >= 3 else 0.0

        # 3. Anomaly penalty.
        score_anomaly = 1.0
        if n > 0:
            score_anomaly = max(0.0, 1.0 - 2.0 * (len(anomaly_indices) / n))

        # 4. Focal-length symmetry (fx/fy ≈ 1).
        aspect_dev = abs(aspect - 1.0)
        score_aspect = max(0.0, 1.0 - aspect_dev / 0.05)  # >5% skew → 0

        # 5. Principal point offset penalty.
        diag = np.hypot(w, h)
        score_pp = max(0.0, 1.0 - (cx_offset / (diag * 0.08)))

        confidence = float(
            0.40 * score_rms
            + 0.20 * score_views
            + 0.15 * score_anomaly
            + 0.15 * score_aspect
            + 0.10 * score_pp
        )
        confidence = max(0.0, min(1.0, confidence))

        if confidence >= 0.85:
            label = "Excellent"
        elif confidence >= 0.70:
            label = "Good"
        elif confidence >= 0.50:
            label = "Fair"
        else:
            label = "Poor"

        return QualityReport(
            num_views=n,
            mean_error=mean_err,
            std_error=std_err,
            min_error=min_err,
            max_error=max_err,
            threshold=float(threshold),
            anomaly_indices=anomaly_indices,
            anomaly_paths=anomaly_paths,
            fx_fy_ratio=float(aspect),
            principal_point_offset_px=float(cx_offset),
            confidence_score=confidence,
            confidence_label=label,
        )

    def to_dict(self) -> Dict:
        return {
            "num_views": self.num_views,
            "mean_error": self.mean_error,
            "std_error": self.std_error,
            "min_error": self.min_error,
            "max_error": self.max_error,
            "threshold": self.threshold,
            "anomaly_indices": self.anomaly_indices,
            "anomaly_paths": self.anomaly_paths,
            "fx_fy_ratio": self.fx_fy_ratio,
            "principal_point_offset_px": self.principal_point_offset_px,
            "confidence_score": self.confidence_score,
            "confidence_label": self.confidence_label,
        }

    def format_text(self) -> str:
        lines = [
            "=== Calibration quality report ===",
            f"Views used           : {self.num_views}",
            f"Mean reproj. error   : {self.mean_error:.4f} px",
            f"Std deviation        : {self.std_error:.4f} px",
            f"Min / Max error      : {self.min_error:.4f} / {self.max_error:.4f} px",
            f"Anomaly threshold    : {self.threshold:.4f} px (mean + 2σ)",
            f"Anomalous views      : {len(self.anomaly_indices)}",
        ]
        for idx, path in zip(self.anomaly_indices, self.anomaly_paths):
            lines.append(f"  [{idx}] {path}")
        lines += [
            f"fx / fy ratio        : {self.fx_fy_ratio:.4f}",
            f"Principal offset     : {self.principal_point_offset_px:.2f} px",
            f"Confidence score     : {self.confidence_score * 100:.1f} %  ({self.confidence_label})",
        ]
        return "\n".join(lines)


# ======================================================================
# Stereo (binocular) calibration
# ======================================================================


@dataclass
class StereoCalibrationResult:
    """Output of :meth:`StereoCalibrator.calibrate`."""

    left: CalibrationResult
    right: CalibrationResult
    R: np.ndarray                # Rotation from left to right camera
    T: np.ndarray                # Translation vector (3x1)
    E: np.ndarray                # Essential matrix
    F: np.ndarray                # Fundamental matrix
    rms: float                   # Stereo calibration RMS error
    R1: Optional[np.ndarray] = None   # Rectification rotation (left)
    R2: Optional[np.ndarray] = None   # Rectification rotation (right)
    P1: Optional[np.ndarray] = None   # Projection (left)
    P2: Optional[np.ndarray] = None   # Projection (right)
    Q: Optional[np.ndarray] = None    # Disparity-to-depth matrix
    roi1: Optional[Tuple[int, int, int, int]] = None
    roi2: Optional[Tuple[int, int, int, int]] = None

    @property
    def baseline_mm(self) -> float:
        """Distance between camera optical centres in mm."""
        return float(np.linalg.norm(self.T))

    @property
    def focal_length_left_px(self) -> float:
        return float(self.P1[0, 0]) if self.P1 is not None else float("nan")

    @property
    def focal_length_right_px(self) -> float:
        return float(self.P2[0, 0]) if self.P2 is not None else float("nan")

    def disparity_to_depth_mm(self, disparity_px: float) -> float:
        """Convert disparity (pixels) to depth (mm).

        Uses the approximate relationship ``Z = f * B / d``, with
        ``f`` from the left projection matrix and ``B`` from ``T``.
        """
        if disparity_px <= 0:
            return float("inf")
        f = self.focal_length_left_px
        B = self.baseline_mm
        if f <= 0 or B <= 0:
            return float("nan")
        return f * B / float(disparity_px)

    def compute_disparity(
        self,
        left_img: np.ndarray,
        right_img: np.ndarray,
        num_disparities: int = 16 * 8,
        block_size: int = 9,
    ) -> np.ndarray:
        """Compute a disparity map for a rectified stereo pair.

        Parameters
        ----------
        left_img, right_img:
            BGR images captured simultaneously by the left / right
            cameras.  They should already be rectified (see
            :meth:`rectify`).
        """
        left_gray = cv2.cvtColor(left_img, cv2.COLOR_BGR2GRAY)
        right_gray = cv2.cvtColor(right_img, cv2.COLOR_BGR2GRAY)
        stereo = cv2.StereoSGBM_create(
            minDisparity=0,
            numDisparities=max(16, num_disparities // 16 * 16),
            blockSize=max(3, block_size if block_size % 2 == 1 else block_size + 1),
            P1=8 * 3 * block_size ** 2,
            P2=32 * 3 * block_size ** 2,
            disp12MaxDiff=1,
            uniquenessRatio=10,
            speckleWindowSize=100,
            speckleRange=2,
        )
        disp = stereo.compute(left_gray, right_gray).astype(np.float32) / 16.0
        return disp

    def rectify(
        self, left_img: np.ndarray, right_img: np.ndarray
    ) -> Tuple[np.ndarray, np.ndarray]:
        """Return ``(rectified_left, rectified_right)`` using precomputed
        rectification maps.  Raises ``RuntimeError`` if rectification
        parameters have not been computed."""
        if self.P1 is None or self.P2 is None or self.Q is None:
            raise RuntimeError("Rectify parameters not computed; call compute_rectification first.")
        h, w = left_img.shape[:2]
        map1x, map1y = cv2.initUndistortRectifyMap(
            self.left.camera_matrix, self.left.dist_coeffs,
            self.R1, self.P1, (w, h), cv2.CV_32FC1,
        )
        map2x, map2y = cv2.initUndistortRectifyMap(
            self.right.camera_matrix, self.right.dist_coeffs,
            self.R2, self.P2, (w, h), cv2.CV_32FC1,
        )
        left_rect = cv2.remap(left_img, map1x, map1y, cv2.INTER_LINEAR)
        right_rect = cv2.remap(right_img, map2x, map2y, cv2.INTER_LINEAR)
        return left_rect, right_rect

    def compute_rectification(self, alpha: float = 0.0) -> None:
        """Compute rectification rotations / projections / Q matrix.

        Parameters
        ----------
        alpha:
            Free scaling factor passed to
            ``cv2.stereoRectify``: ``0`` = crop to valid region,
            ``1`` = keep full original FOV.  Default ``0``, which
            produces a clean disparity map without black borders.
        """
        image_size = self.left.image_size
        R1, R2, P1, P2, Q, roi1, roi2 = cv2.stereoRectify(
            self.left.camera_matrix, self.left.dist_coeffs,
            self.right.camera_matrix, self.right.dist_coeffs,
            image_size, self.R, self.T,
            alpha=alpha,
        )
        self.R1 = R1
        self.R2 = R2
        self.P1 = P1
        self.P2 = P2
        self.Q = Q
        self.roi1 = tuple(int(v) for v in roi1)
        self.roi2 = tuple(int(v) for v in roi2)

    def to_dict(self) -> Dict:
        data = {
            "left": self.left.to_dict(),
            "right": self.right.to_dict(),
            "R": self.R.tolist(),
            "T": self.T.ravel().tolist(),
            "E": self.E.tolist(),
            "F": self.F.tolist(),
            "rms": self.rms,
            "baseline_mm": self.baseline_mm,
        }
        for key, val in (
            ("R1", self.R1), ("R2", self.R2),
            ("P1", self.P1), ("P2", self.P2),
            ("Q", self.Q),
        ):
            if val is not None:
                data[key] = val.tolist()
        if self.roi1 is not None:
            data["roi1"] = list(self.roi1)
        if self.roi2 is not None:
            data["roi2"] = list(self.roi2)
        return data

    def save(self, path: str) -> None:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2, ensure_ascii=False)


class StereoCalibrator:
    """Calibrate a stereo (binocular) camera rig.

    Typical usage::

        left_images  = ["left_01.png", "left_02.png", ...]
        right_images = ["right_01.png", "right_02.png", ...]

        sc = StereoCalibrator(pattern_size=(9, 6), square_size=25.0)
        for l, r in zip(left_images, right_images):
            sc.add_image_pair(l, r)
        result = sc.calibrate()
        result.compute_rectification()
        left_rect, right_rect = result.rectify(left_img, right_img)
        disp = result.compute_disparity(left_rect, right_rect)
    """

    def __init__(
        self,
        pattern_size: Tuple[int, int] = (9, 6),
        square_size: float = 25.0,
        pattern_type: PatternType = PatternType.CHESSBOARD,
        use_clahe: bool = True,
        clahe_clip: float = 2.0,
        clahe_grid: Tuple[int, int] = (8, 8),
    ) -> None:
        self.left_cal = CameraCalibrator(
            pattern_size=pattern_size,
            square_size=square_size,
            use_clahe=use_clahe,
            clahe_clip=clahe_clip,
            clahe_grid=clahe_grid,
            pattern_type=pattern_type,
        )
        self.right_cal = CameraCalibrator(
            pattern_size=pattern_size,
            square_size=square_size,
            use_clahe=use_clahe,
            clahe_clip=clahe_clip,
            clahe_grid=clahe_grid,
            pattern_type=pattern_type,
        )
        self.pattern_size = self.left_cal.pattern_size
        self.square_size = self.left_cal.square_size

        self._valid_pairs: List[Tuple[str, str]] = []

    # ------------------------------------------------------------------

    @property
    def num_valid_pairs(self) -> int:
        return len(self._valid_pairs)

    def reset(self) -> None:
        self.left_cal.reset()
        self.right_cal.reset()
        self._valid_pairs.clear()

    def add_image_pair(
        self, left_path: str, right_path: str
    ) -> Tuple[bool, str]:
        """Detect pattern features in both images; only add to the
        calibration set when *both* succeed."""
        l_ok, l_msg = self.left_cal.add_image(left_path)
        r_ok, r_msg = self.right_cal.add_image(right_path)

        if not l_ok and not r_ok:
            return False, f"Left: {l_msg}; Right: {r_msg}"
        if not l_ok:
            # Roll back the right image so indices stay aligned.
            self._rollback_last(self.right_cal)
            return False, f"Left failed: {l_msg}"
        if not r_ok:
            self._rollback_last(self.left_cal)
            return False, f"Right failed: {r_msg}"

        self._valid_pairs.append((left_path, right_path))
        return True, "OK"

    @staticmethod
    def _rollback_last(cal: CameraCalibrator) -> None:
        if cal._object_points:
            cal._object_points.pop()
            cal._image_points.pop()
            cal._image_paths.pop()

    def add_image_pairs(
        self, pairs: List[Tuple[str, str]]
    ) -> List[Tuple[str, str, bool, str]]:
        results: List[Tuple[str, str, bool, str]] = []
        for l, r in pairs:
            ok, msg = self.add_image_pair(l, r)
            results.append((l, r, ok, msg))
        return results

    def calibrate(
        self, alpha: float = 0.5, rectify_alpha: float = 0.0
    ) -> StereoCalibrationResult:
        """Run mono calibration for both cameras, then stereo calibration.

        Parameters
        ----------
        alpha:
            Scaling factor for the *mono* ``getOptimalNewCameraMatrix``
            (balanced by default – used for undistortion only).
        rectify_alpha:
            Scaling factor for ``cv2.stereoRectify`` (``0`` = crop to
            valid region, ``1`` = full FOV).  Default ``0``.
        """
        if self.num_valid_pairs < 2:
            raise RuntimeError(
                "At least 2 valid stereo pairs are required "
                f"(found {self.num_valid_pairs})."
            )

        left_res = self.left_cal.calibrate(alpha=alpha)
        right_res = self.right_cal.calibrate(alpha=alpha)

        image_size = left_res.image_size
        if image_size != right_res.image_size:
            raise RuntimeError(
                "Left and right image sizes differ; stereo calibration "
                "requires identical image sizes."
            )

        flags = 0
        flags |= cv2.CALIB_FIX_INTRINSIC
        flags |= cv2.CALIB_SAME_FOCAL_LENGTH

        rms, _, _, _, _, R, T, E, F = cv2.stereoCalibrate(
            self.left_cal._object_points,
            self.left_cal._image_points,
            self.right_cal._image_points,
            left_res.camera_matrix,
            left_res.dist_coeffs,
            right_res.camera_matrix,
            right_res.dist_coeffs,
            image_size,
            flags=flags,
            criteria=(
                cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER,
                100,
                1e-6,
            ),
        )

        stereo_result = StereoCalibrationResult(
            left=left_res,
            right=right_res,
            R=R,
            T=T,
            E=E,
            F=F,
            rms=float(rms),
        )
        try:
            stereo_result.compute_rectification(alpha=rectify_alpha)
        except Exception:  # pragma: no cover - rectification may fail
            pass
        return stereo_result
