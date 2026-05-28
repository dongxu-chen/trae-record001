import numpy as np
import cv2
from typing import Dict, Tuple, List
from skimage.restoration import estimate_sigma
from skimage.filters import median
from skimage.morphology import disk


NOISE_TYPES = [
    "gaussian",
    "salt_pepper",
    "poisson",
    "periodic",
    "illumination_uneven",
    "blur",
    "jpeg_compression",
    "clean",
]


def detect_noise_type(
    image: np.ndarray,
    analyze_regions: int = 5,
) -> Dict[str, any]:
    if image.ndim == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    else:
        gray = image.copy()

    h, w = gray.shape
    gray_float = gray.astype(np.float64)

    results = {
        "noise_scores": {},
        "primary_noise": "clean",
        "recommended_method": "sauvola",
        "recommended_params": {},
        "details": {},
    }

    gaussian_score, gaussian_details = _detect_gaussian_noise(gray_float)
    results["noise_scores"]["gaussian"] = gaussian_score
    results["details"]["gaussian"] = gaussian_details

    sp_score, sp_details = _detect_salt_pepper_noise(gray_float)
    results["noise_scores"]["salt_pepper"] = sp_score
    results["details"]["salt_pepper"] = sp_details

    poisson_score, poisson_details = _detect_poisson_noise(gray_float)
    results["noise_scores"]["poisson"] = poisson_score
    results["details"]["poisson"] = poisson_details

    periodic_score, periodic_details = _detect_periodic_noise(gray_float)
    results["noise_scores"]["periodic"] = periodic_score
    results["details"]["periodic"] = periodic_details

    illum_score, illum_details = _detect_illumination_uneven(gray_float)
    results["noise_scores"]["illumination_uneven"] = illum_score
    results["details"]["illumination_uneven"] = illum_details

    blur_score, blur_details = _detect_blur(gray_float)
    results["noise_scores"]["blur"] = blur_score
    results["details"]["blur"] = blur_details

    jpeg_score, jpeg_details = _detect_jpeg_artifacts(gray)
    results["noise_scores"]["jpeg_compression"] = jpeg_score
    results["details"]["jpeg_compression"] = jpeg_details

    primary = max(results["noise_scores"], key=results["noise_scores"].get)
    max_score = results["noise_scores"][primary]

    if max_score < 0.15:
        results["primary_noise"] = "clean"
    else:
        results["primary_noise"] = primary

    results["recommended_method"], results["recommended_params"] = _recommend_binarization(
        results["noise_scores"], results["primary_noise"]
    )

    return results


def _detect_gaussian_noise(gray_float: np.ndarray) -> Tuple[float, Dict]:
    try:
        sigma_est = estimate_sigma(gray_float.astype(np.float32))
        sigma_norm = min(sigma_est / 50.0, 1.0)
        score = sigma_norm

        local_std = cv2.GaussianBlur(gray_float, (3, 3), 0)
        local_std = np.abs(gray_float - local_std)
        local_std_mean = np.mean(local_std) / 255.0

        score = 0.6 * sigma_norm + 0.4 * min(local_std_mean * 3, 1.0)

        return score, {"sigma_estimate": float(sigma_est), "local_noise_mean": float(local_std_mean)}
    except Exception:
        return 0.0, {"sigma_estimate": 0.0, "local_noise_mean": 0.0}


def _detect_salt_pepper_noise(gray_float: np.ndarray) -> Tuple[float, Dict]:
    h, w = gray_float.shape
    num_pixels = h * w

    salt_count = np.sum(gray_float > 250)
    pepper_count = np.sum(gray_float < 5)
    sp_ratio = (salt_count + pepper_count) / num_pixels

    median_filtered = cv2.medianBlur(gray_float.astype(np.uint8), 3)
    diff = np.abs(gray_float - median_filtered.astype(np.float64))
    mean_diff = np.mean(diff) / 255.0

    score = 0.7 * min(sp_ratio * 20, 1.0) + 0.3 * min(mean_diff * 4, 1.0)

    return score, {
        "salt_ratio": float(salt_count / num_pixels),
        "pepper_ratio": float(pepper_count / num_pixels),
        "sp_ratio": float(sp_ratio),
        "median_diff": float(mean_diff),
    }


def _detect_poisson_noise(gray_float: np.ndarray) -> Tuple[float, Dict]:
    patches = _sample_patches(gray_float, patch_size=16, num_patches=20)
    var_mean_ratios = []

    for patch in patches:
        patch_mean = np.mean(patch)
        patch_var = np.var(patch)
        if patch_mean > 1:
            ratio = patch_var / patch_mean
            var_mean_ratios.append(ratio)

    if not var_mean_ratios:
        return 0.0, {"var_mean_ratio": 0.0}

    avg_ratio = np.mean(var_mean_ratios)
    score = min(abs(avg_ratio - 1.0) / 3.0, 1.0)

    return score, {"var_mean_ratio": float(avg_ratio)}


def _detect_periodic_noise(gray_float: np.ndarray) -> Tuple[float, Dict]:
    h, w = gray_float.shape

    fft = np.fft.fft2(gray_float)
    fft_shifted = np.fft.fftshift(fft)
    magnitude = np.abs(fft_shifted)

    center_h, center_w = h // 2, w // 2
    radius = min(h, w) // 4

    yy, xx = np.ogrid[:h, :w]
    dist_from_center = np.sqrt((xx - center_w) ** 2 + (yy - center_h) ** 2)

    mask_ring = (dist_from_center > radius) & (dist_from_center < min(h, w) // 2 - 5)
    ring_magnitude = magnitude[mask_ring]

    if len(ring_magnitude) == 0:
        return 0.0, {"peak_ratio": 0.0}

    mean_ring = np.mean(ring_magnitude)
    std_ring = np.std(ring_magnitude)

    if mean_ring > 0:
        peak_ratio = std_ring / mean_ring
    else:
        peak_ratio = 0

    score = min(peak_ratio / 5.0, 1.0)

    return score, {"peak_ratio": float(peak_ratio), "mean_magnitude": float(mean_ring)}


def _detect_illumination_uneven(gray_float: np.ndarray) -> Tuple[float, Dict]:
    h, w = gray_float.shape

    large_kernel = max(h, w) // 10
    if large_kernel % 2 == 0:
        large_kernel += 1
    if large_kernel < 5:
        large_kernel = 5

    bg_estimate = cv2.GaussianBlur(gray_float, (large_kernel, large_kernel), 0)
    bg_normalized = gray_float / (bg_estimate + 1e-8)

    bg_std = np.std(bg_estimate) / 255.0
    correction_std = np.std(bg_normalized)

    score = min(bg_std * 3, 1.0)

    return score, {
        "bg_std": float(bg_std),
        "correction_std": float(correction_std),
        "bg_min": float(np.min(bg_estimate)),
        "bg_max": float(np.max(bg_estimate)),
    }


def _detect_blur(gray_float: np.ndarray) -> Tuple[float, Dict]:
    laplacian = cv2.Laplacian(gray_float.astype(np.uint8), cv2.CV_64F)
    laplacian_var = np.var(laplacian)

    sobel_x = cv2.Sobel(gray_float, cv2.CV_64F, 1, 0, ksize=3)
    sobel_y = cv2.Sobel(gray_float, cv2.CV_64F, 0, 1, ksize=3)
    gradient_mag = np.sqrt(sobel_x ** 2 + sobel_y ** 2)
    gradient_mean = np.mean(gradient_mag) / 255.0

    if laplacian_var < 100:
        blur_score = 1.0
    elif laplacian_var < 1000:
        blur_score = (1000 - laplacian_var) / 900.0
    else:
        blur_score = 0.0

    combined_score = 0.6 * blur_score + 0.4 * (1 - min(gradient_mean * 3, 1.0))

    return combined_score, {
        "laplacian_variance": float(laplacian_var),
        "gradient_mean": float(gradient_mean),
    }


def _detect_jpeg_artifacts(gray: np.ndarray) -> Tuple[float, Dict]:
    h, w = gray.shape

    blocks_h, blocks_w = h // 8, w // 8
    if blocks_h < 2 or blocks_w < 2:
        return 0.0, {"block_artifact_score": 0.0}

    block_errors = []
    for i in range(1, blocks_h):
        row = i * 8
        if row < h:
            diff = np.abs(gray[row, :].astype(np.float64) - gray[row - 1, :].astype(np.float64))
            block_errors.append(np.mean(diff))

    for j in range(1, blocks_w):
        col = j * 8
        if col < w:
            diff = np.abs(gray[:, col].astype(np.float64) - gray[:, col - 1].astype(np.float64))
            block_errors.append(np.mean(diff))

    if not block_errors:
        return 0.0, {"block_artifact_score": 0.0}

    avg_block_diff = np.mean(block_errors)
    score = min(avg_block_diff / 20.0, 1.0)

    return score, {"block_artifact_score": float(score), "avg_block_diff": float(avg_block_diff)}


def _sample_patches(
    image: np.ndarray, patch_size: int = 16, num_patches: int = 20
) -> List[np.ndarray]:
    h, w = image.shape
    patches = []

    max_y = h - patch_size
    max_x = w - patch_size

    if max_y < 0 or max_x < 0:
        return [image]

    for _ in range(num_patches):
        y = np.random.randint(0, max_y)
        x = np.random.randint(0, max_x)
        patches.append(image[y:y + patch_size, x:x + patch_size])

    return patches


def _recommend_binarization(
    noise_scores: Dict[str, float],
    primary_noise: str,
) -> Tuple[str, Dict]:
    illum_score = noise_scores.get("illumination_uneven", 0)
    gaussian_score = noise_scores.get("gaussian", 0)
    sp_score = noise_scores.get("salt_pepper", 0)
    blur_score = noise_scores.get("blur", 0)
    periodic_score = noise_scores.get("periodic", 0)

    params = {}

    if primary_noise == "clean":
        method = "otsu" if illum_score < 0.2 else "sauvola"
        params = {"window_size": 15, "k": 0.2}

    elif primary_noise == "illumination_uneven":
        if illum_score > 0.5:
            method = "sauvola"
            params = {
                "window_size": 25,
                "k": 0.25,
                "bg_estimation": "morph",
                "bg_texture_suppress": True,
            }
        else:
            method = "niblack"
            params = {"window_size": 19, "k": -0.15}

    elif primary_noise == "gaussian":
        method = "sauvola"
        params = {
            "window_size": 21,
            "k": 0.3,
            "denoise": True,
            "denoise_method": "wavelet",
        }

    elif primary_noise == "salt_pepper":
        method = "adaptive"
        params = {
            "block_size": 21,
            "C": 3,
            "denoise": True,
            "denoise_method": "median",
            "post_process": True,
            "morph_kernel": 2,
        }

    elif primary_noise == "blur":
        if blur_score > 0.5:
            method = "sauvola"
            params = {"window_size": 31, "k": 0.15}
        else:
            method = "sauvola"
            params = {"window_size": 21, "k": 0.2}

    elif primary_noise == "periodic":
        method = "sauvola"
        params = {
            "window_size": 25,
            "k": 0.25,
            "denoise": True,
            "denoise_method": "wavelet",
        }

    elif primary_noise == "poisson":
        method = "niblack"
        params = {"window_size": 21, "k": -0.1}

    elif primary_noise == "jpeg_compression":
        method = "sauvola"
        params = {
            "window_size": 19,
            "k": 0.25,
            "denoise": True,
            "denoise_method": "bilateral",
        }

    else:
        method = "sauvola"
        params = {"window_size": 15, "k": 0.2}

    return method, params