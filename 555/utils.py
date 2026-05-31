import numpy as np
import cv2
from depth_super_resolution import (
    align_depth_to_rgb,
    create_aligned_colored_depth,
    compute_depth_metrics,
    format_metrics_display,
    MetricsAccumulator,
    DepthSuperResolution,
)


def upsample_depth(depth_low, guidance_rgb=None, scale_factor=2, method="bilinear_guided", target_size=None):
    sr = DepthSuperResolution(method=method, scale_factor=scale_factor)
    return sr.upsample(depth_low, guidance_rgb, target_size)


def align_and_colorize(depth_map, rgb_image, colormap="turbo", dynamic_mapping=True, alpha_blend=0.0):
    depth_aligned, _ = align_depth_to_rgb(depth_map, rgb_image)
    return create_aligned_colored_depth(depth_aligned, rgb_image, colormap, dynamic_mapping, alpha_blend)


def colorize_depth(depth_map, colormap="turbo", dynamic_mapping=False, percentile_low=1.0, percentile_high=99.0):
    if depth_map is None or depth_map.size == 0:
        return np.zeros((1, 1, 3), dtype=np.uint8)

    depth_float = depth_map.astype(np.float32)

    if dynamic_mapping:
        low_val = np.percentile(depth_float, percentile_low)
        high_val = np.percentile(depth_float, percentile_high)

        if high_val - low_val > 1e-6:
            depth_clamped = np.clip(depth_float, low_val, high_val)
            depth_normalized = (depth_clamped - low_val) / (high_val - low_val)
        else:
            depth_normalized = np.zeros_like(depth_float)

        hist, bin_edges = np.histogram(depth_normalized, bins=256, range=(0, 1))
        cdf = np.cumsum(hist).astype(np.float32)
        cdf = cdf / cdf[-1] if cdf[-1] > 0 else cdf

        depth_indices = np.clip(depth_normalized * 255, 0, 255).astype(np.int32)
        depth_equalized = cdf[depth_indices]
        depth_u8 = np.clip(depth_equalized * 255, 0, 255).astype(np.uint8)
    else:
        depth_u8 = np.clip(depth_map * 255, 0, 255).astype(np.uint8)

    colormap_map = {
        "turbo": cv2.COLORMAP_TURBO,
        "magma": cv2.COLORMAP_MAGMA,
        "inferno": cv2.COLORMAP_INFERNO,
        "plasma": cv2.COLORMAP_PLASMA,
        "viridis": cv2.COLORMAP_VIRIDIS,
        "jet": cv2.COLORMAP_JET,
        "parula": cv2.COLORMAP_PARULA,
    }

    cm = colormap_map.get(colormap, cv2.COLORMAP_TURBO)
    colorized = cv2.applyColorMap(depth_u8, cm)
    return colorized


def colorize_depth_dynamic(depth_map, colormap="turbo", adaptive=False):
    if adaptive:
        return colorize_depth(depth_map, colormap=colormap, dynamic_mapping=True)

    h, w = depth_map.shape[:2]
    depth_flat = depth_map.ravel()

    hist, bins = np.histogram(depth_flat, bins=64, range=(0, 1))
    hist = hist.astype(np.float32) / hist.sum() if hist.sum() > 0 else hist

    median_idx = np.argmax(np.cumsum(hist) >= 0.5)
    median_depth = (median_idx + 0.5) / 64.0

    near_mask = depth_flat > (median_depth + 0.1)
    far_mask = depth_flat < (median_depth - 0.1)

    near_ratio = near_mask.mean()
    far_ratio = far_mask.mean()

    depth_normalized = depth_flat.copy()

    if near_ratio > 0.3 and far_ratio > 0.3:
        depth_normalized = np.clip(depth_flat, 0.05, 0.95)
        depth_normalized = (depth_normalized - depth_normalized.min()) / (depth_normalized.max() - depth_normalized.min() + 1e-10)

        low_clip = np.percentile(depth_flat, 3)
        high_clip = np.percentile(depth_flat, 97)
        if high_clip - low_clip > 0.2:
            depth_normalized = np.clip(depth_flat, low_clip, high_clip)
            depth_normalized = (depth_normalized - low_clip) / (high_clip - low_clip + 1e-10)

    depth_normalized = depth_normalized.reshape(h, w)
    return colorize_depth(depth_normalized, colormap=colormap, dynamic_mapping=adaptive)


def compute_texture_map(gray, window_size=15):
    gray_float = gray.astype(np.float32)
    mean = cv2.blur(gray_float, (window_size, window_size))
    mean_sq = cv2.blur(gray_float * gray_float, (window_size, window_size))
    variance = mean_sq - mean * mean
    variance = np.clip(variance, 0, None)
    stddev = np.sqrt(variance)

    texture_map = stddev / (stddev.max() + 1e-10)
    return texture_map.astype(np.float32)


def enhance_edges_adaptive(
    image_bgr,
    method="canny",
    base_low=30,
    base_high=90,
    texture_window=15,
    texture_threshold=0.25,
    min_enhancement=0.3,
    max_enhancement=1.0,
):
    if image_bgr is None or image_bgr.size == 0:
        return None

    gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)

    texture_map = compute_texture_map(gray, window_size=texture_window)

    h, w = gray.shape[:2]
    low_thresh_map = base_low + (texture_threshold - texture_map) * base_low
    high_thresh_map = base_high + (texture_threshold - texture_map) * base_high
    low_thresh_map = np.clip(low_thresh_map, base_low * min_enhancement, base_low * max_enhancement)
    high_thresh_map = np.clip(high_thresh_map, base_high * min_enhancement, base_high * max_enhancement)

    if method == "canny":
        edges = np.zeros((h, w), dtype=np.uint8)

        texture_bins = 4
        for t in range(texture_bins):
            t_min = t / texture_bins
            t_max = (t + 1) / texture_bins
            mask = (texture_map >= t_min) & (texture_map < t_max)
            if np.any(mask):
                enhancement = max_enhancement - (max_enhancement - min_enhancement) * (t_min + t_max) / 2.0
                cur_low = int(base_low * enhancement)
                cur_high = int(base_high * enhancement)
                cur_low = max(10, min(cur_low, 200))
                cur_high = max(30, min(cur_high, 255))
                cur_edges = cv2.Canny(gray, cur_low, cur_high)
                edges[mask] = cur_edges[mask]

    elif method == "sobel":
        sobel_x = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
        sobel_y = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=3)
        edges_mag = np.sqrt(sobel_x ** 2 + sobel_y ** 2)

        texture_weight = min_enhancement + (1.0 - texture_map) * (max_enhancement - min_enhancement)
        edges_mag = edges_mag * texture_weight

        mean_mag = edges_mag.mean()
        std_mag = edges_mag.std()
        threshold = mean_mag + std_mag * 0.5
        edges = (edges_mag > threshold).astype(np.uint8) * 255
        edges = edges.astype(np.uint8)

    elif method == "laplacian":
        laplacian = cv2.Laplacian(gray, cv2.CV_64F)
        edges_mag = np.abs(laplacian)

        texture_weight = min_enhancement + (1.0 - texture_map) * (max_enhancement - min_enhancement)
        edges_mag = edges_mag * texture_weight

        edges = np.clip(edges_mag, 0, 255).astype(np.uint8)

    else:
        edges = enhance_edges_adaptive(
            image_bgr, "canny", base_low, base_high, texture_window,
            texture_threshold, min_enhancement, max_enhancement
        )

    return edges


def enhance_edges(image_bgr, method="canny", low_threshold=50, high_threshold=150, adaptive=False, **kwargs):
    if adaptive:
        return enhance_edges_adaptive(image_bgr, method=method, base_low=low_threshold, base_high=high_threshold, **kwargs)

    gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)

    if method == "canny":
        edges = cv2.Canny(gray, low_threshold, high_threshold)
    elif method == "sobel":
        sobel_x = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
        sobel_y = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=3)
        edges = np.sqrt(sobel_x ** 2 + sobel_y ** 2)
        edges = np.clip(edges, 0, 255).astype(np.uint8)
    elif method == "laplacian":
        edges = cv2.Laplacian(gray, cv2.CV_64F)
        edges = np.clip(np.abs(edges), 0, 255).astype(np.uint8)
    else:
        edges = cv2.Canny(gray, low_threshold, high_threshold)

    return edges


def overlay_edges_on_depth(depth_colorized, edges, alpha=0.3, color=(0, 255, 0)):
    overlay = depth_colorized.copy()
    edge_mask = edges > 0
    overlay[edge_mask] = (
        (1 - alpha) * depth_colorized[edge_mask].astype(np.float32)
        + alpha * np.array(color, dtype=np.float32)
    ).astype(np.uint8)
    return overlay


def resize_depth(depth_map, target_size):
    return cv2.resize(depth_map, target_size, interpolation=cv2.INTER_LINEAR)


def blend_depth_maps(depth1, depth2, alpha=0.5):
    d1 = cv2.resize(depth1, (depth2.shape[1], depth2.shape[0]))
    return (alpha * d1 + (1 - alpha) * depth2).astype(np.float32)


def compute_depth_gradients(depth_map):
    grad_x = cv2.Sobel(depth_map, cv2.CV_64F, 1, 0, ksize=3)
    grad_y = cv2.Sobel(depth_map, cv2.CV_64F, 0, 1, ksize=3)
    magnitude = np.sqrt(grad_x ** 2 + grad_y ** 2)
    magnitude = (magnitude - magnitude.min()) / (magnitude.max() - magnitude.min() + 1e-10)
    return magnitude.astype(np.float32)


def temporal_smooth(depth_prev, depth_curr, alpha=0.7):
    if depth_prev is None:
        return depth_curr
    h, w = depth_curr.shape[:2]
    depth_prev_resized = cv2.resize(depth_prev, (w, h))
    return (alpha * depth_prev_resized + (1 - alpha) * depth_curr).astype(np.float32)


def create_side_by_side(image_bgr, depth_colorized, separator=True):
    h1, w1 = image_bgr.shape[:2]
    h2, w2 = depth_colorized.shape[:2]
    target_h = max(h1, h2)
    img1 = cv2.resize(image_bgr, (int(w1 * target_h / h1), target_h))
    img2 = cv2.resize(depth_colorized, (int(w2 * target_h / h2), target_h))

    if separator:
        sep = np.ones((target_h, 4, 3), dtype=np.uint8) * 255
        return np.hstack([img1, sep, img2])
    return np.hstack([img1, img2])
