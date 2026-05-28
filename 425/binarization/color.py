import numpy as np
import cv2
from typing import Tuple, Dict, List
from skimage.filters import threshold_sauvola, threshold_niblack
from skimage.color import rgb2lab, lab2rgb


def binarize_color_channel(
    image: np.ndarray,
    method: str = "sauvola",
    channel: str = "l",
    preserve_color: bool = True,
    **kwargs,
) -> np.ndarray:
    if image.ndim != 3:
        raise ValueError("Input must be a 3-channel color image")

    if channel.lower() == "l":
        lab = rgb2lab(image.astype(np.float64) / 255.0)
        l_channel = lab[:, :, 0]
        l_norm = (l_channel / 100.0 * 255).astype(np.uint8)

        binary_l = _binarize_single_channel(l_norm, method, **kwargs)

        if preserve_color:
            lab[:, :, 0] = (binary_l / 255.0 * 100.0).astype(np.float64)
            result_rgb = lab2rgb(lab)
            result_rgb = (result_rgb * 255).astype(np.uint8)
            return result_rgb
        else:
            return binary_l

    elif channel.lower() in ["r", "g", "b"]:
        ch_idx = {"r": 2, "g": 1, "b": 0}[channel.lower()]
        single_ch = image[:, :, ch_idx]
        binary_ch = _binarize_single_channel(single_ch, method, **kwargs)

        if preserve_color:
            result = image.copy()
            result[:, :, ch_idx] = binary_ch
            return result
        else:
            return binary_ch

    elif channel.lower() == "gray":
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        binary = _binarize_single_channel(gray, method, **kwargs)
        if preserve_color:
            result = image.copy()
            for c in range(3):
                result[:, :, c] = cv2.bitwise_and(image[:, :, c], binary)
            return result
        else:
            return binary

    elif channel.lower() == "saturation":
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        s_channel = hsv[:, :, 1]
        binary_s = _binarize_single_channel(s_channel, method, **kwargs)
        if preserve_color:
            result = image.copy()
            mask = binary_s == 255
            for c in range(3):
                result[:, :, c] = np.where(mask, 255, result[:, :, c])
            return result
        else:
            return binary_s

    else:
        raise ValueError(f"Unsupported channel: {channel}")


def _binarize_single_channel(
    channel: np.ndarray,
    method: str,
    window_size: int = 15,
    k: float = 0.2,
    r: float = 128.0,
    block_size: int = 11,
    C: int = 2,
) -> np.ndarray:
    method = method.lower()
    if method == "sauvola":
        if window_size % 2 == 0:
            window_size += 1
        thresh = threshold_sauvola(channel, window_size=window_size, k=k, r=r)
        binary = (channel > thresh).astype(np.uint8) * 255
    elif method == "niblack":
        if window_size % 2 == 0:
            window_size += 1
        thresh = threshold_niblack(channel, window_size=window_size, k=k)
        binary = (channel > thresh).astype(np.uint8) * 255
    elif method == "otsu":
        _, binary = cv2.threshold(channel, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    elif method == "adaptive":
        if block_size % 2 == 0:
            block_size += 1
        binary = cv2.adaptiveThreshold(
            channel, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY, block_size, C
        )
    else:
        raise ValueError(f"Unsupported binarization method: {method}")
    return binary


def binarize_color_multi_channel(
    image: np.ndarray,
    method: str = "sauvola",
    combination: str = "intersection",
    preserve_color: bool = True,
    **kwargs,
) -> np.ndarray:
    if image.ndim != 3:
        raise ValueError("Input must be a 3-channel color image")

    lab = rgb2lab(image.astype(np.float64) / 255.0)
    l_channel = (lab[:, :, 0] / 100.0 * 255).astype(np.uint8)
    a_channel = ((lab[:, :, 1] + 128) / 256.0 * 255).astype(np.uint8)
    b_channel = ((lab[:, :, 2] + 128) / 256.0 * 255).astype(np.uint8)

    bin_l = _binarize_single_channel(l_channel, method, **kwargs)
    bin_a = _binarize_single_channel(a_channel, method, **kwargs)
    bin_b = _binarize_single_channel(b_channel, method, **kwargs)

    if combination == "intersection":
        combined = cv2.bitwise_and(cv2.bitwise_and(bin_l, bin_a), bin_b)
    elif combination == "union":
        combined = cv2.bitwise_or(cv2.bitwise_or(bin_l, bin_a), bin_b)
    elif combination == "majority":
        stacked = np.stack([bin_l, bin_a, bin_b], axis=2)
        combined = (np.sum(stacked == 255, axis=2) >= 2).astype(np.uint8) * 255
    elif combination == "l_weighted":
        combined = bin_l
    else:
        combined = bin_l

    if preserve_color:
        result = image.copy()
        mask_foreground = combined == 0
        for c in range(3):
            result[:, :, c] = np.where(mask_foreground, 0, 255)
        return result
    else:
        return combined


def binarize_color_by_clustering(
    image: np.ndarray,
    num_clusters: int = 3,
    preserve_color: bool = True,
    target_clusters: List[int] = None,
) -> np.ndarray:
    if image.ndim != 3:
        raise ValueError("Input must be a 3-channel color image")

    pixel_values = image.reshape((-1, 3)).astype(np.float32)
    criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 100, 0.2)
    _, labels, centers = cv2.kmeans(
        pixel_values, num_clusters, None, criteria, 10, cv2.KMEANS_PP_CENTERS
    )

    labels = labels.flatten()
    centers = np.uint8(centers)

    if target_clusters is None:
        gray_centers = cv2.cvtColor(centers.reshape(1, -1, 3), cv2.COLOR_BGR2GRAY).flatten()
        sorted_indices = np.argsort(gray_centers)
        target_clusters = [sorted_indices[0]]

    mask = np.zeros_like(labels, dtype=bool)
    for tc in target_clusters:
        mask = mask | (labels == tc)
    mask = mask.reshape(image.shape[:2])

    if preserve_color:
        result = image.copy()
        for c in range(3):
            result[:, :, c] = np.where(mask, image[:, :, c], 255)
        return result
    else:
        binary = np.zeros(image.shape[:2], dtype=np.uint8)
        binary[mask] = 0
        binary[~mask] = 255
        return binary


def preserve_colored_text(
    image: np.ndarray,
    binary_mask: np.ndarray,
    color_saturation_threshold: float = 30,
) -> np.ndarray:
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    s_channel = hsv[:, :, 1]
    v_channel = hsv[:, :, 2]

    color_mask = s_channel > color_saturation_threshold
    dark_mask = v_channel < 200
    colored_text_mask = color_mask & dark_mask

    result = cv2.cvtColor(binary_mask, cv2.COLOR_GRAY2BGR) if binary_mask.ndim == 2 else binary_mask.copy()
    result[colored_text_mask] = image[colored_text_mask]

    return result