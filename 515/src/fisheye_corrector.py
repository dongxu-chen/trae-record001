from enum import Enum
import numpy as np
import cv2
from typing import Optional, Tuple, Union, List, Dict, Any
from scipy.interpolate import griddata
from .distortion_models import (
    FisheyeDistortionModel,
    FisheyeProjectionType,
    create_projection_model,
)
from .calibration import estimate_fisheye_params_auto


class CorrectionMethod(Enum):
    SPHERICAL_PROJECTION = "spherical"
    EQURECTANGULAR_PROJECTION = "equirectangular"
    PERSPECTIVE_PROJECTION = "perspective"


class BorderHandlingMode(Enum):
    FULL = "full"
    CROP = "crop"
    PAD = "pad"


class FisheyeCorrector:
    def __init__(
        self,
        distortion_model: Optional[FisheyeDistortionModel] = None,
        output_size: Optional[Tuple[int, int]] = None,
        method: CorrectionMethod = CorrectionMethod.SPHERICAL_PROJECTION,
        interpolation: int = cv2.INTER_LINEAR,
        border_mode: BorderHandlingMode = BorderHandlingMode.FULL,
        pad_value: Union[int, Tuple[int, int, int]] = 0,
    ):
        self.distortion_model = distortion_model
        self.output_size = output_size
        self.method = method
        self.interpolation = interpolation
        self.border_mode = border_mode
        self.pad_value = pad_value
        self.map_x = None
        self.map_y = None
        self._valid_mask = None
        self._is_initialized = False

    def set_distortion_model(self, model: FisheyeDistortionModel):
        self.distortion_model = model
        self._is_initialized = False

    def set_output_size(self, size: Tuple[int, int]):
        self.output_size = size
        self._is_initialized = False

    def set_method(self, method: CorrectionMethod):
        self.method = method
        self._is_initialized = False

    def set_border_mode(self, mode: BorderHandlingMode):
        self.border_mode = mode

    def set_pad_value(self, value: Union[int, Tuple[int, int, int]]):
        self.pad_value = value

    def _get_valid_bbox(self, mask: np.ndarray) -> Optional[Tuple[int, int, int, int]]:
        rows = np.any(mask, axis=1)
        cols = np.any(mask, axis=0)

        if not np.any(rows) or not np.any(cols):
            return None

        top, bottom = np.where(rows)[0][[0, -1]]
        left, right = np.where(cols)[0][[0, -1]]

        return top, bottom, left, right

    def _get_largest_valid_rect(self, mask: np.ndarray) -> Optional[Tuple[int, int, int, int]]:
        bbox = self._get_valid_bbox(mask)
        if bbox is None:
            return None

        top, bottom, left, right = bbox
        h, w = mask.shape

        center_h = (top + bottom) // 2
        center_w = (left + right) // 2

        max_size = min(bottom - top, right - left)
        half_size = max_size // 2

        new_top = max(0, center_h - half_size)
        new_bottom = min(h, center_h + half_size)
        new_left = max(0, center_w - half_size)
        new_right = min(w, center_w + half_size)

        actual_h = new_bottom - new_top
        actual_w = new_right - new_left
        actual_size = min(actual_h, actual_w)

        new_top = center_h - actual_size // 2
        new_bottom = new_top + actual_size
        new_left = center_w - actual_size // 2
        new_right = new_left + actual_size

        if new_top < 0 or new_bottom > h or new_left < 0 or new_right > w:
            return bbox

        return new_top, new_bottom, new_left, new_right

    def _compute_maps(
        self,
        input_size: Tuple[int, int],
        output_size: Optional[Tuple[int, int]] = None,
    ):
        if self.distortion_model is None:
            raise ValueError("Distortion model must be set before computing maps")

        h_in, w_in = input_size
        if output_size is None:
            if self.output_size is None:
                output_size = (int(h_in * 1.5), int(w_in * 1.5))
            else:
                output_size = self.output_size

        h_out, w_out = output_size

        if self.method == CorrectionMethod.SPHERICAL_PROJECTION:
            self._compute_spherical_maps(w_out, h_out, w_in, h_in)
        elif self.method == CorrectionMethod.EQURECTANGULAR_PROJECTION:
            self._compute_equirectangular_maps(w_out, h_out, w_in, h_in)
        elif self.method == CorrectionMethod.PERSPECTIVE_PROJECTION:
            self._compute_perspective_maps(w_out, h_out, w_in, h_in)
        else:
            raise ValueError(f"Unknown correction method: {self.method}")

        self._valid_mask = (self.map_x >= 0) & (self.map_y >= 0)
        self._is_initialized = True

    def _compute_spherical_maps(
        self, w_out: int, h_out: int, w_in: int, h_in: int
    ):
        y_out, x_out = np.mgrid[0:h_out, 0:w_out]

        cx_out = w_out / 2.0
        cy_out = h_out / 2.0

        x_norm = (x_out - cx_out) / cx_out
        y_norm = (y_out - cy_out) / cy_out

        r = np.sqrt(x_norm**2 + y_norm**2)
        valid = r <= 1.0

        theta = np.zeros_like(r)
        theta[valid] = np.arcsin(r[valid])

        phi = np.arctan2(y_norm, x_norm)

        angles = np.stack([theta, phi], axis=-1)
        pixels = self.distortion_model.angle_to_pixel(angles)

        self.map_x = pixels[..., 0].astype(np.float32)
        self.map_y = pixels[..., 1].astype(np.float32)

        self.map_x[~valid] = -1
        self.map_y[~valid] = -1

    def _compute_equirectangular_maps(
        self, w_out: int, h_out: int, w_in: int, h_in: int
    ):
        y_out, x_out = np.mgrid[0:h_out, 0:w_out]

        lon = (x_out / w_out - 0.5) * 2 * np.pi
        lat = (0.5 - y_out / h_out) * np.pi

        x = np.cos(lat) * np.cos(lon)
        y = np.cos(lat) * np.sin(lon)
        z = np.sin(lat)

        cartesian = np.stack([x, y, z], axis=-1)
        pixels = self.distortion_model.cartesian_to_pixel(cartesian)

        self.map_x = pixels[..., 0].astype(np.float32)
        self.map_y = pixels[..., 1].astype(np.float32)

    def _compute_perspective_maps(
        self, w_out: int, h_out: int, w_in: int, h_in: int
    ):
        y_out, x_out = np.mgrid[0:h_out, 0:w_out]

        cx_out = w_out / 2.0
        cy_out = h_out / 2.0

        f_out = min(w_out, h_out) / 2.0

        x_norm = (x_out - cx_out) / f_out
        y_norm = (y_out - cy_out) / f_out

        z = np.ones_like(x_norm)
        r = np.sqrt(x_norm**2 + y_norm**2 + z**2)

        x = x_norm / r
        y = y_norm / r
        z = z / r

        cartesian = np.stack([x, y, z], axis=-1)
        pixels = self.distortion_model.cartesian_to_pixel(cartesian)

        self.map_x = pixels[..., 0].astype(np.float32)
        self.map_y = pixels[..., 1].astype(np.float32)

        theta = np.arccos(z)
        max_theta = np.radians(120)
        valid = theta <= max_theta

        self.map_x[~valid] = -1
        self.map_y[~valid] = -1

    def correct(
        self,
        image: np.ndarray,
        output_size: Optional[Tuple[int, int]] = None,
        border_mode: int = cv2.BORDER_CONSTANT,
        border_value: Union[int, Tuple[int, int, int]] = 0,
        handling_mode: Optional[BorderHandlingMode] = None,
    ) -> np.ndarray:
        if self.distortion_model is None:
            params = estimate_fisheye_params_auto(image)
            self.distortion_model = params["model"]

        h_in, w_in = image.shape[:2]

        if not self._is_initialized or (
            output_size is not None and output_size != self.output_size
        ):
            self._compute_maps((h_in, w_in), output_size)

        if handling_mode is None:
            handling_mode = self.border_mode

        if len(image.shape) == 2:
            corrected = cv2.remap(
                image,
                self.map_x,
                self.map_y,
                self.interpolation,
                borderMode=border_mode,
                borderValue=border_value,
            )
        else:
            channels = cv2.split(image)
            corrected_channels = []
            for ch in channels:
                corrected_ch = cv2.remap(
                    ch,
                    self.map_x,
                    self.map_y,
                    self.interpolation,
                    borderMode=border_mode,
                    borderValue=border_value
                    if isinstance(border_value, int)
                    else border_value[0],
                )
                corrected_channels.append(corrected_ch)
            corrected = cv2.merge(corrected_channels)

        if handling_mode == BorderHandlingMode.FULL:
            return corrected

        if handling_mode == BorderHandlingMode.CROP:
            return self._apply_crop(corrected)

        elif handling_mode == BorderHandlingMode.PAD:
            return self._apply_pad(corrected, border_value)

        return corrected

    def _apply_crop(self, image: np.ndarray) -> np.ndarray:
        if self._valid_mask is None:
            return image

        bbox = self._get_largest_valid_rect(self._valid_mask)
        if bbox is None:
            return image

        top, bottom, left, right = bbox
        return image[top:bottom, left:right].copy()

    def _apply_pad(
        self,
        image: np.ndarray,
        pad_value: Union[int, Tuple[int, int, int]] = 0,
    ) -> np.ndarray:
        if self._valid_mask is None:
            return image

        h, w = image.shape[:2]

        mask = self._valid_mask.astype(np.uint8) * 255
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)

        contours, _ = cv2.findContours(
            mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )

        if len(contours) == 0:
            return image

        largest_contour = max(contours, key=cv2.contourArea)
        x, y, w_contour, h_contour = cv2.boundingRect(largest_contour)

        center_x = x + w_contour // 2
        center_y = y + h_contour // 2

        max_radius = max(w_contour, h_contour) // 2 + 10

        new_size = max_radius * 2
        pad_top = max(0, center_y - max_radius)
        pad_bottom = max(0, new_size - (center_y - max_radius) - h)
        pad_left = max(0, center_x - max_radius)
        pad_right = max(0, new_size - (center_x - max_radius) - w)

        if isinstance(pad_value, int):
            if len(image.shape) == 3:
                pad_value = (pad_value, pad_value, pad_value)

        padded = cv2.copyMakeBorder(
            image,
            pad_top,
            pad_bottom,
            pad_left,
            pad_right,
            cv2.BORDER_CONSTANT,
            value=pad_value,
        )

        return padded

    def correct_with_custom_rotation(
        self,
        image: np.ndarray,
        yaw: float = 0.0,
        pitch: float = 0.0,
        roll: float = 0.0,
        output_size: Optional[Tuple[int, int]] = None,
        handling_mode: Optional[BorderHandlingMode] = None,
    ) -> np.ndarray:
        if self.distortion_model is None:
            params = estimate_fisheye_params_auto(image)
            self.distortion_model = params["model"]

        h_in, w_in = image.shape[:2]
        if output_size is None:
            output_size = self.output_size or (int(h_in * 1.5), int(w_in * 1.5))
        h_out, w_out = output_size

        if handling_mode is None:
            handling_mode = self.border_mode

        yaw_rad = np.radians(yaw)
        pitch_rad = np.radians(pitch)
        roll_rad = np.radians(roll)

        Rz = np.array(
            [
                [np.cos(yaw_rad), -np.sin(yaw_rad), 0],
                [np.sin(yaw_rad), np.cos(yaw_rad), 0],
                [0, 0, 1],
            ]
        )
        Ry = np.array(
            [
                [np.cos(pitch_rad), 0, np.sin(pitch_rad)],
                [0, 1, 0],
                [-np.sin(pitch_rad), 0, np.cos(pitch_rad)],
            ]
        )
        Rx = np.array(
            [
                [1, 0, 0],
                [0, np.cos(roll_rad), -np.sin(roll_rad)],
                [0, np.sin(roll_rad), np.cos(roll_rad)],
            ]
        )
        R = Rz @ Ry @ Rx

        y_out, x_out = np.mgrid[0:h_out, 0:w_out]
        cx_out = w_out / 2.0
        cy_out = h_out / 2.0
        f_out = min(w_out, h_out) / 2.0

        x_norm = (x_out - cx_out) / f_out
        y_norm = (y_out - cy_out) / f_out
        z = np.ones_like(x_norm)

        points = np.stack([x_norm, y_norm, z], axis=-1)
        points = points @ R.T

        r = np.linalg.norm(points, axis=-1, keepdims=True)
        points_normalized = points / r

        pixels = self.distortion_model.cartesian_to_pixel(points_normalized)
        map_x = pixels[..., 0].astype(np.float32)
        map_y = pixels[..., 1].astype(np.float32)

        theta = np.arccos(points_normalized[..., 2])
        max_theta = np.radians(120)
        valid = theta <= max_theta
        map_x[~valid] = -1
        map_y[~valid] = -1

        if len(image.shape) == 2:
            corrected = cv2.remap(
                image, map_x, map_y, self.interpolation, borderMode=cv2.BORDER_CONSTANT
            )
        else:
            channels = cv2.split(image)
            corrected_channels = []
            for ch in channels:
                corrected_ch = cv2.remap(
                    ch, map_x, map_y, self.interpolation, borderMode=cv2.BORDER_CONSTANT
                )
                corrected_channels.append(corrected_ch)
            corrected = cv2.merge(corrected_channels)

        old_valid_mask = self._valid_mask
        self._valid_mask = valid

        if handling_mode == BorderHandlingMode.CROP:
            corrected = self._apply_crop(corrected)
        elif handling_mode == BorderHandlingMode.PAD:
            corrected = self._apply_pad(corrected, self.pad_value)

        self._valid_mask = old_valid_mask

        return corrected


def correct_fisheye_image(
    image: np.ndarray,
    method: CorrectionMethod = CorrectionMethod.SPHERICAL_PROJECTION,
    focal_length: Optional[float] = None,
    center: Optional[Tuple[float, float]] = None,
    projection_type: FisheyeProjectionType = FisheyeProjectionType.EQUISOLID,
    output_size: Optional[Tuple[int, int]] = None,
    auto_params: bool = True,
    handling_mode: BorderHandlingMode = BorderHandlingMode.FULL,
) -> np.ndarray:
    h, w = image.shape[:2]

    if focal_length is None or center is None or auto_params:
        params = estimate_fisheye_params_auto(image)
        model = params["model"]
    else:
        model = create_projection_model(projection_type, focal_length, center)

    corrector = FisheyeCorrector(
        distortion_model=model,
        output_size=output_size,
        method=method,
        border_mode=handling_mode,
    )

    return corrector.correct(image)


def correct_fisheye_with_params(
    image: np.ndarray,
    distortion_model: FisheyeDistortionModel,
    method: CorrectionMethod = CorrectionMethod.SPHERICAL_PROJECTION,
    output_size: Optional[Tuple[int, int]] = None,
    handling_mode: BorderHandlingMode = BorderHandlingMode.FULL,
) -> np.ndarray:
    corrector = FisheyeCorrector(
        distortion_model=distortion_model,
        output_size=output_size,
        method=method,
        border_mode=handling_mode,
    )
    return corrector.correct(image)


def create_panorama_from_fisheye(
    image: np.ndarray,
    distortion_model: Optional[FisheyeDistortionModel] = None,
    output_size: Tuple[int, int] = (1080, 2160),
) -> np.ndarray:
    if distortion_model is None:
        params = estimate_fisheye_params_auto(image)
        distortion_model = params["model"]

    corrector = FisheyeCorrector(
        distortion_model=distortion_model,
        output_size=output_size,
        method=CorrectionMethod.EQURECTANGULAR_PROJECTION,
    )

    return corrector.correct(image)


def fisheye_to_equirectangular(
    image: np.ndarray,
    distortion_model: Optional[FisheyeDistortionModel] = None,
    output_size: Optional[Tuple[int, int]] = None,
    yaw_offset: float = 0.0,
    pitch_offset: float = 0.0,
) -> np.ndarray:
    h, w = image.shape[:2]

    if distortion_model is None:
        params = estimate_fisheye_params_auto(image)
        distortion_model = params["model"]

    if output_size is None:
        output_size = (h, w * 2)
    h_out, w_out = output_size

    yaw_rad = np.radians(yaw_offset)
    pitch_rad = np.radians(pitch_offset)

    y_out, x_out = np.mgrid[0:h_out, 0:w_out]

    lon = (x_out / w_out - 0.5) * 2 * np.pi + yaw_rad
    lat = (0.5 - y_out / h_out) * np.pi + pitch_rad

    lat = np.clip(lat, -np.pi / 2 + 0.01, np.pi / 2 - 0.01)

    x = np.cos(lat) * np.cos(lon)
    y = np.cos(lat) * np.sin(lon)
    z = np.sin(lat)

    cartesian = np.stack([x, y, z], axis=-1)
    pixels = distortion_model.cartesian_to_pixel(cartesian)

    map_x = pixels[..., 0].astype(np.float32)
    map_y = pixels[..., 1].astype(np.float32)

    if len(image.shape) == 2:
        equirect = cv2.remap(
            image, map_x, map_y, cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT
        )
    else:
        channels = cv2.split(image)
        equirect_channels = []
        for ch in channels:
            equirect_ch = cv2.remap(
                ch, map_x, map_y, cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT
            )
            equirect_channels.append(equirect_ch)
        equirect = cv2.merge(equirect_channels)

    return equirect


def create_vr_panorama(
    fisheye_images: List[np.ndarray],
    distortion_model: Optional[FisheyeDistortionModel] = None,
    output_size: Tuple[int, int] = (1080, 2160),
    blend_width: int = 50,
) -> np.ndarray:
    if len(fisheye_images) == 0:
        raise ValueError("No input images provided")

    if distortion_model is None:
        params = estimate_fisheye_params_auto(fisheye_images[0])
        distortion_model = params["model"]

    h_out, w_out = output_size
    panorama = np.zeros((h_out, w_out, 3), dtype=np.float32)
    weight_sum = np.zeros((h_out, w_out, 1), dtype=np.float32)

    for idx, image in enumerate(fisheye_images):
        angle_offset = (idx / len(fisheye_images)) * 360.0
        equirect = fisheye_to_equirectangular(
            image,
            distortion_model=distortion_model,
            output_size=output_size,
            yaw_offset=angle_offset,
        )

        equirect_float = equirect.astype(np.float32)

        weight = np.ones((h_out, w_out, 1), dtype=np.float32)
        if blend_width > 0:
            fade = np.linspace(0, 1, blend_width)
            weight[:, :blend_width, 0] *= fade
            weight[:, -blend_width:, 0] *= fade[::-1]

        panorama += equirect_float * weight
        weight_sum += weight

    weight_sum = np.maximum(weight_sum, 1e-6)
    panorama = (panorama / weight_sum).astype(np.uint8)

    return panorama


def evaluate_correction_quality(
    original_image: np.ndarray,
    corrected_image: np.ndarray,
    model: FisheyeDistortionModel,
) -> Dict[str, Any]:
    from .self_calibration import (
        detect_line_segments,
        compute_straightness_error,
        sample_line_points,
    )

    h_orig, w_orig = original_image.shape[:2]
    h_corr, w_corr = corrected_image.shape[:2]

    line_segments = detect_line_segments(original_image, max_segments=50)

    straightness_errors = []
    segment_lengths = []

    if len(line_segments) > 0:
        for segment in line_segments:
            if segment.length < 30:
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
                straightness_errors.append(error)
                segment_lengths.append(segment.length)
            except Exception:
                continue

    if len(corrected_image.shape) == 3:
        gray_corrected = cv2.cvtColor(corrected_image, cv2.COLOR_BGR2GRAY)
    else:
        gray_corrected = corrected_image

    valid_pixels = np.sum(gray_corrected > 5)
    total_pixels = h_corr * w_corr
    frame_retention_ratio = valid_pixels / total_pixels

    if len(straightness_errors) > 0:
        errors = np.array(straightness_errors)
        lengths = np.array(segment_lengths)
        weighted_error = np.sum(errors * lengths) / np.sum(lengths) if np.sum(lengths) > 0 else 0.0
        quality_score = max(0.0, 1.0 - weighted_error / 5.0)

        result = {
            "quality_score": quality_score,
            "mean_straightness_error": float(np.mean(errors)),
            "median_straightness_error": float(np.median(errors)),
            "max_straightness_error": float(np.max(errors)),
            "weighted_straightness_error": float(weighted_error),
            "frame_retention_ratio": float(frame_retention_ratio),
            "valid_pixels": int(valid_pixels),
            "total_pixels": int(total_pixels),
            "num_segments_analyzed": len(errors),
            "original_resolution": (h_orig, w_orig),
            "corrected_resolution": (h_corr, w_corr),
            "area_ratio": (h_corr * w_corr) / (h_orig * w_orig),
        }
    else:
        result = {
            "quality_score": 0.0,
            "mean_straightness_error": 0.0,
            "median_straightness_error": 0.0,
            "max_straightness_error": 0.0,
            "weighted_straightness_error": 0.0,
            "frame_retention_ratio": float(frame_retention_ratio),
            "valid_pixels": int(valid_pixels),
            "total_pixels": int(total_pixels),
            "num_segments_analyzed": 0,
            "original_resolution": (h_orig, w_orig),
            "corrected_resolution": (h_corr, w_corr),
            "area_ratio": (h_corr * w_corr) / (h_orig * w_orig),
        }

    return result


def generate_correction_grid(
    input_size: Tuple[int, int],
    distortion_model: FisheyeDistortionModel,
    grid_spacing: int = 50,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    h, w = input_size

    x_lines = np.arange(0, w, grid_spacing)
    y_lines = np.arange(0, h, grid_spacing)

    distorted_x = []
    distorted_y = []

    for y in y_lines:
        points = np.stack([np.arange(w), np.full(w, y)], axis=-1)
        angles = distortion_model.pixel_to_angle(points)
        theta = angles[..., 0]
        phi = angles[..., 1]

        r = theta
        x_corr = r * np.cos(phi) + w / 2
        y_corr = r * np.sin(phi) + h / 2

        distorted_x.append(x_corr)
        distorted_y.append(y_corr)

    for x in x_lines:
        points = np.stack([np.full(h, x), np.arange(h)], axis=-1)
        angles = distortion_model.pixel_to_angle(points)
        theta = angles[..., 0]
        phi = angles[..., 1]

        r = theta
        x_corr = r * np.cos(phi) + w / 2
        y_corr = r * np.sin(phi) + h / 2

        distorted_x.append(x_corr)
        distorted_y.append(y_corr)

    return (
        np.array(distorted_x[: len(y_lines)]),
        np.array(distorted_y[: len(y_lines)]),
        np.array(distorted_x[len(y_lines) :]),
        np.array(distorted_y[len(y_lines) :]),
    )
