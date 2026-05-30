import numpy as np
import cv2
from sklearn.mixture import GaussianMixture
from enum import Enum
from typing import Optional, Tuple, List


__all__ = [
    "ColorSpace",
    "convert_to_color_space",
    "convert_from_color_space",
    "reinhard_transfer",
    "GMMColorTransfer",
    "create_region_mask",
    "create_color_range_mask",
    "create_segmentation_mask",
    "feather_mask",
    "mask_weighted_blend",
    "local_color_transfer",
    "multi_region_transfer",
    "selective_color_transfer",
    "_channel_stats",
    "_clahe_enhance",
]


class ColorSpace(Enum):
    LAB = "lab"
    RGB = "rgb"
    HSV = "hsv"
    YCRCB = "ycrcb"


def convert_to_color_space(image: np.ndarray, color_space: ColorSpace) -> np.ndarray:
    img = image.astype(np.float64) / 255.0
    if color_space == ColorSpace.LAB:
        return cv2.cvtColor((img * 255).astype(np.uint8), cv2.COLOR_BGR2Lab).astype(np.float64)
    elif color_space == ColorSpace.RGB:
        return cv2.cvtColor((img * 255).astype(np.uint8), cv2.COLOR_BGR2RGB).astype(np.float64)
    elif color_space == ColorSpace.HSV:
        return cv2.cvtColor((img * 255).astype(np.uint8), cv2.COLOR_BGR2HSV).astype(np.float64)
    elif color_space == ColorSpace.YCRCB:
        return cv2.cvtColor((img * 255).astype(np.uint8), cv2.COLOR_BGR2YCrCb).astype(np.float64)
    else:
        raise ValueError(f"Unsupported color space: {color_space}")


def convert_from_color_space(
    image: np.ndarray,
    color_space: ColorSpace,
    preserve_details: bool = True,
) -> np.ndarray:
    if color_space == ColorSpace.LAB:
        ranges = np.array([[0, 255], [-128, 127], [-128, 127]], dtype=np.float64)
    elif color_space == ColorSpace.RGB:
        ranges = np.array([[0, 255], [0, 255], [0, 255]], dtype=np.float64)
    elif color_space == ColorSpace.HSV:
        ranges = np.array([[0, 179], [0, 255], [0, 255]], dtype=np.float64)
    elif color_space == ColorSpace.YCRCB:
        ranges = np.array([[0, 255], [0, 255], [0, 255]], dtype=np.float64)
    else:
        raise ValueError(f"Unsupported color space: {color_space}")

    img = image.copy().astype(np.float64)

    if preserve_details:
        for c in range(3):
            ch_min, ch_max = ranges[c]
            channel = img[:, :, c]
            actual_min, actual_max = np.min(channel), np.max(channel)
            if actual_min < ch_min or actual_max > ch_max:
                if actual_max > actual_min:
                    scale = (ch_max - ch_min) / (actual_max - actual_min)
                    offset = ch_min - actual_min * scale
                    channel = channel * scale + offset
                else:
                    channel = np.clip(channel, ch_min, ch_max)
            img[:, :, c] = channel
    else:
        for c in range(3):
            ch_min, ch_max = ranges[c]
            img[:, :, c] = np.clip(img[:, :, c], ch_min, ch_max)

    img = np.round(img).astype(np.uint8)

    if color_space == ColorSpace.LAB:
        return cv2.cvtColor(img, cv2.COLOR_Lab2BGR)
    elif color_space == ColorSpace.RGB:
        return cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
    elif color_space == ColorSpace.HSV:
        return cv2.cvtColor(img, cv2.COLOR_HSV2BGR)
    elif color_space == ColorSpace.YCRCB:
        return cv2.cvtColor(img, cv2.COLOR_YCrCb2BGR)


def _clahe_enhance(image: np.ndarray, clip_limit: float = 2.0, grid_size: int = 8) -> np.ndarray:
    lab = cv2.cvtColor(image, cv2.COLOR_BGR2Lab)
    l, a, b = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=clip_limit, tileGridSize=(grid_size, grid_size))
    l = clahe.apply(l)
    lab_enhanced = cv2.merge([l, a, b])
    return cv2.cvtColor(lab_enhanced, cv2.COLOR_Lab2BGR)


def create_segmentation_mask(
    image: np.ndarray,
    method: str = "kmeans",
    n_segments: int = 3,
    target_regions: Optional[List[int]] = None,
    rect: Optional[Tuple[int, int, int, int]] = None,
) -> np.ndarray:
    h, w = image.shape[:2]

    if method == "kmeans":
        pixels = image.reshape(-1, 3).astype(np.float32)
        criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 100, 0.2)
        _, labels, centers = cv2.kmeans(
            pixels, n_segments, None, criteria, 10, cv2.KMEANS_PP_CENTERS
        )
        labels = labels.reshape(h, w)

        if target_regions is None:
            center_sums = np.sum(centers, axis=1)
            target_regions = [int(np.argmax(center_sums))]

        mask = np.zeros((h, w), dtype=np.uint8)
        for region in target_regions:
            mask[labels == region] = 255
        return mask

    elif method == "grabcut":
        if rect is None:
            rect = (10, 10, w - 20, h - 20)

        mask = np.zeros((h, w), dtype=np.uint8)
        bgd_model = np.zeros((1, 65), np.float64)
        fgd_model = np.zeros((1, 65), np.float64)

        cv2.grabCut(
            image, mask, rect, bgd_model, fgd_model, 5, cv2.GC_INIT_WITH_RECT
        )

        result_mask = np.where((mask == 2) | (mask == 0), 0, 255).astype(np.uint8)
        return result_mask

    elif method == "color":
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        lower = np.array([0, 50, 50])
        upper = np.array([179, 255, 255])
        mask = cv2.inRange(hsv, lower, upper)
        return mask

    elif method == "saliency":
        saliency = cv2.saliency.StaticSaliencySpectralResidual_create()
        success, saliency_map = saliency.computeSaliency(image)
        saliency_map = (saliency_map * 255).astype(np.uint8)
        _, mask = cv2.threshold(saliency_map, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        return mask

    else:
        raise ValueError(f"Unknown segmentation method: {method}")


def feather_mask(
    mask: np.ndarray,
    feather_radius: int = 15,
    fade_only: bool = True,
) -> np.ndarray:
    if feather_radius <= 0:
        return mask.astype(np.float64)

    kernel_size = 2 * feather_radius + 1
    mask_float = mask.astype(np.float64) / 255.0

    blurred = cv2.GaussianBlur(mask_float, (kernel_size, kernel_size), feather_radius)

    if fade_only:
        mask_bool = mask_float > 0
        result = np.where(mask_bool, np.minimum(mask_float + blurred, 1.0), blurred)
    else:
        result = blurred

    return (result * 255).astype(np.uint8)


def mask_weighted_blend(
    original: np.ndarray,
    transferred: np.ndarray,
    feathered_mask: np.ndarray,
) -> np.ndarray:
    if feathered_mask.dtype != np.float64:
        mask_float = feathered_mask.astype(np.float64) / 255.0
    else:
        mask_float = feathered_mask

    if len(mask_float.shape) == 2:
        mask_float = np.expand_dims(mask_float, axis=2)

    result = original.astype(np.float64) * (1 - mask_float) + \
             transferred.astype(np.float64) * mask_float
    return np.clip(result, 0, 255).astype(np.uint8)


def _channel_stats(pixels: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    mean = np.mean(pixels, axis=0)
    std = np.std(pixels, axis=0)
    std[std < 1e-6] = 1e-6
    return mean, std


def reinhard_transfer(
    source: np.ndarray,
    reference: np.ndarray,
    color_space: ColorSpace = ColorSpace.LAB,
    source_mask: Optional[np.ndarray] = None,
    reference_mask: Optional[np.ndarray] = None,
    blend: float = 1.0,
    auto_segment: Optional[str] = None,
    n_segments: int = 3,
    feather_radius: int = 0,
    preserve_details: bool = True,
) -> np.ndarray:
    src_cs = convert_to_color_space(source, color_space)
    ref_cs = convert_to_color_space(reference, color_space)

    h, w = source.shape[:2]
    ref_resized = cv2.resize(reference, (w, h))
    ref_cs = convert_to_color_space(ref_resized, color_space)

    seg_mask = None
    if auto_segment is not None:
        seg_mask = create_segmentation_mask(
            source, method=auto_segment, n_segments=n_segments
        )
        if source_mask is None:
            source_mask = seg_mask
        else:
            source_mask = cv2.bitwise_and(source_mask, seg_mask)

    if source_mask is not None:
        src_pixels = src_cs[source_mask > 0]
    else:
        src_pixels = src_cs.reshape(-1, 3)

    if reference_mask is not None:
        ref_mask_resized = cv2.resize(reference_mask, (w, h))
        ref_pixels = ref_cs[ref_mask_resized > 0]
    else:
        ref_pixels = ref_cs.reshape(-1, 3)

    if len(src_pixels) == 0 or len(ref_pixels) == 0:
        return source.copy()

    src_mean, src_std = _channel_stats(src_pixels)
    ref_mean, ref_std = _channel_stats(ref_pixels)

    result = src_cs.copy().astype(np.float64)

    if source_mask is not None:
        mask_bool = source_mask > 0
        for c in range(3):
            channel = result[:, :, c]
            transferred = (channel - src_mean[c]) * (ref_std[c] / src_std[c]) + ref_mean[c]
            result[:, :, c] = np.where(mask_bool, transferred, channel)
    else:
        for c in range(3):
            result[:, :, c] = (result[:, :, c] - src_mean[c]) * (ref_std[c] / src_std[c]) + ref_mean[c]

    if 0.0 < blend < 1.0:
        result = src_cs * (1 - blend) + result * blend

    if color_space == ColorSpace.HSV:
        result[:, :, 0] = result[:, :, 0] % 180

    result_bgr = convert_from_color_space(result, color_space, preserve_details=preserve_details)

    if feather_radius > 0 and source_mask is not None:
        feathered = feather_mask(source_mask, feather_radius=feather_radius)
        result_bgr = mask_weighted_blend(source, result_bgr, feathered)

    return result_bgr


class GMMColorTransfer:
    def __init__(
        self,
        n_components: int = 3,
        color_space: ColorSpace = ColorSpace.LAB,
        max_iter: int = 100,
        covariance_type: str = "full",
    ):
        self.n_components = n_components
        self.color_space = color_space
        self.max_iter = max_iter
        self.covariance_type = covariance_type
        self.ref_gmm: Optional[GaussianMixture] = None
        self.ref_means_: Optional[np.ndarray] = None
        self.ref_covs_: Optional[np.ndarray] = None

    def fit(self, reference: np.ndarray, mask: Optional[np.ndarray] = None):
        ref_cs = convert_to_color_space(reference, self.color_space)
        if mask is not None:
            pixels = ref_cs[mask > 0]
        else:
            pixels = ref_cs.reshape(-1, 3)

        if len(pixels) < self.n_components * 10:
            self.n_components = max(1, len(pixels) // 10)

        self.ref_gmm = GaussianMixture(
            n_components=self.n_components,
            max_iter=self.max_iter,
            covariance_type=self.covariance_type,
            random_state=42,
        )
        self.ref_gmm.fit(pixels)
        self.ref_means_ = self.ref_gmm.means_.copy()
        self.ref_covs_ = self.ref_gmm.covariances_.copy()
        return self

    def transform(
        self,
        source: np.ndarray,
        source_mask: Optional[np.ndarray] = None,
        blend: float = 1.0,
        auto_segment: Optional[str] = None,
        n_segments: int = 3,
        feather_radius: int = 0,
        preserve_details: bool = True,
    ) -> np.ndarray:
        if self.ref_gmm is None:
            raise RuntimeError("Call fit() before transform()")

        src_cs = convert_to_color_space(source, self.color_space)
        h, w = source.shape[:2]

        if auto_segment is not None:
            seg_mask = create_segmentation_mask(
                source, method=auto_segment, n_segments=n_segments
            )
            if source_mask is None:
                source_mask = seg_mask
            else:
                source_mask = cv2.bitwise_and(source_mask, seg_mask)

        if source_mask is not None:
            mask_bool = source_mask > 0
            src_pixels = src_cs[mask_bool]
        else:
            src_pixels = src_cs.reshape(-1, 3)
            mask_bool = np.ones((h, w), dtype=bool)

        if len(src_pixels) == 0:
            return source.copy()

        src_gmm = GaussianMixture(
            n_components=self.n_components,
            max_iter=self.max_iter,
            covariance_type=self.covariance_type,
            random_state=42,
        )
        src_gmm.fit(src_pixels)

        src_labels = src_gmm.predict(src_pixels)

        transferred = src_pixels.copy().astype(np.float64)
        for k in range(self.n_components):
            src_k = src_pixels[src_labels == k]
            if len(src_k) == 0:
                continue

            src_mean_k = np.mean(src_k, axis=0)
            src_std_k = np.std(src_k, axis=0)
            src_std_k[src_std_k < 1e-6] = 1e-6

            distances = np.linalg.norm(src_gmm.means_[k] - self.ref_means_, axis=1)
            closest_ref = np.argmin(distances)

            ref_mean_k = self.ref_means_[closest_ref]
            ref_labels = self.ref_gmm.predict(src_k)
            ref_k_mask = ref_labels == closest_ref
            if np.any(ref_k_mask):
                ref_std_k = np.std(src_k[ref_k_mask], axis=0) if np.sum(ref_k_mask) > 1 else np.sqrt(np.diag(self.ref_covs_[closest_ref]))
            else:
                ref_std_k = np.sqrt(np.diag(self.ref_covs_[closest_ref]))

            ref_std_k[ref_std_k < 1e-6] = 1e-6

            transferred[src_labels == k] = (
                (src_k - src_mean_k) * (ref_std_k / src_std_k) + ref_mean_k
            )

        result = src_cs.copy().astype(np.float64)
        if source_mask is not None:
            for c in range(3):
                channel = result[:, :, c]
                transferred_channel = np.zeros_like(channel)
                transferred_channel[mask_bool] = transferred[:, c]
                result[:, :, c] = np.where(mask_bool, transferred_channel, channel)
        else:
            result = transferred.reshape(h, w, 3)

        if 0.0 < blend < 1.0:
            result = src_cs * (1 - blend) + result * blend

        if self.color_space == ColorSpace.HSV:
            result[:, :, 0] = result[:, :, 0] % 180

        result_bgr = convert_from_color_space(result, self.color_space, preserve_details=preserve_details)

        if feather_radius > 0 and source_mask is not None:
            feathered = feather_mask(source_mask, feather_radius=feather_radius)
            result_bgr = mask_weighted_blend(source, result_bgr, feathered)

        return result_bgr

    def fit_transform(
        self,
        source: np.ndarray,
        reference: np.ndarray,
        source_mask: Optional[np.ndarray] = None,
        reference_mask: Optional[np.ndarray] = None,
        blend: float = 1.0,
        auto_segment: Optional[str] = None,
        n_segments: int = 3,
        feather_radius: int = 0,
        preserve_details: bool = True,
    ) -> np.ndarray:
        self.fit(reference, mask=reference_mask)
        return self.transform(
            source,
            source_mask=source_mask,
            blend=blend,
            auto_segment=auto_segment,
            n_segments=n_segments,
            feather_radius=feather_radius,
            preserve_details=preserve_details,
        )


def create_region_mask(
    image_shape: Tuple[int, int],
    regions: List[Tuple[int, int, int, int]],
) -> np.ndarray:
    mask = np.zeros(image_shape[:2], dtype=np.uint8)
    for x1, y1, x2, y2 in regions:
        x1, x2 = min(x1, x2), max(x1, x2)
        y1, y2 = min(y1, y2), max(y1, y2)
        mask[y1:y2, x1:x2] = 255
    return mask


def create_color_range_mask(
    image: np.ndarray,
    color_space: ColorSpace,
    lower: np.ndarray,
    upper: np.ndarray,
) -> np.ndarray:
    converted = convert_to_color_space(image, color_space)
    mask = np.all((converted >= lower) & (converted <= upper), axis=2).astype(np.uint8) * 255
    return mask


def local_color_transfer(
    source: np.ndarray,
    reference: np.ndarray,
    source_mask: np.ndarray,
    reference_mask: np.ndarray,
    color_space: ColorSpace = ColorSpace.LAB,
    method: str = "reinhard",
    n_components: int = 3,
    blend: float = 1.0,
    feather_radius: int = 15,
    preserve_details: bool = True,
) -> np.ndarray:
    h, w = source.shape[:2]
    ref_resized = cv2.resize(reference, (w, h))
    ref_mask_resized = cv2.resize(reference_mask, (w, h))

    if method == "reinhard":
        result = reinhard_transfer(
            source, ref_resized, color_space,
            source_mask=source_mask,
            reference_mask=ref_mask_resized,
            blend=blend,
            feather_radius=feather_radius,
            preserve_details=preserve_details,
        )
    elif method == "gmm":
        gmm = GMMColorTransfer(
            n_components=n_components,
            color_space=color_space,
        )
        result = gmm.fit_transform(
            source, ref_resized,
            source_mask=source_mask,
            reference_mask=ref_mask_resized,
            blend=blend,
            feather_radius=feather_radius,
            preserve_details=preserve_details,
        )
    else:
        raise ValueError(f"Unknown method: {method}. Use 'reinhard' or 'gmm'.")

    return result


def multi_region_transfer(
    source: np.ndarray,
    reference: np.ndarray,
    source_masks: List[np.ndarray],
    reference_masks: List[np.ndarray],
    color_space: ColorSpace = ColorSpace.LAB,
    method: str = "reinhard",
    n_components: int = 3,
    blend: float = 1.0,
    feather_radius: int = 15,
    preserve_details: bool = True,
) -> np.ndarray:
    h, w = source.shape[:2]
    result = source.copy()

    for src_mask, ref_mask in zip(source_masks, reference_masks):
        src_mask_resized = cv2.resize(src_mask, (w, h)) if src_mask.shape[:2] != (h, w) else src_mask
        ref_mask_resized = cv2.resize(ref_mask, (w, h))

        transferred = local_color_transfer(
            source, reference,
            src_mask_resized, ref_mask_resized,
            color_space=color_space,
            method=method,
            n_components=n_components,
            blend=blend,
            feather_radius=feather_radius,
            preserve_details=preserve_details,
        )

        if feather_radius > 0:
            feathered = feather_mask(src_mask_resized, feather_radius=feather_radius)
            result = mask_weighted_blend(result, transferred, feathered)
        else:
            mask_bool = src_mask_resized > 0
            for c in range(3):
                result[:, :, c] = np.where(mask_bool, transferred[:, :, c], result[:, :, c])

    return result


def selective_color_transfer(
    source: np.ndarray,
    reference: np.ndarray,
    target_hue_range: Tuple[float, float],
    color_space: ColorSpace = ColorSpace.LAB,
    method: str = "reinhard",
    n_components: int = 3,
    blend: float = 1.0,
    feather_radius: int = 10,
    preserve_details: bool = True,
) -> np.ndarray:
    hsv = cv2.cvtColor(source, cv2.COLOR_BGR2HSV).astype(np.float64)
    h, w = source.shape[:2]

    lower_h, upper_h = target_hue_range
    if lower_h <= upper_h:
        mask = ((hsv[:, :, 0] >= lower_h) & (hsv[:, :, 0] <= upper_h)).astype(np.uint8) * 255
    else:
        mask = ((hsv[:, :, 0] >= lower_h) | (hsv[:, :, 0] <= upper_h)).astype(np.uint8) * 255

    ref_h, ref_w = reference.shape[:2]
    ref_mask = np.ones((ref_h, ref_w), dtype=np.uint8) * 255

    return local_color_transfer(
        source, reference,
        mask, ref_mask,
        color_space=color_space,
        method=method,
        n_components=n_components,
        blend=blend,
        feather_radius=feather_radius,
        preserve_details=preserve_details,
    )
