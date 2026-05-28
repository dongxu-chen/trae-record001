import numpy as np
import cv2
from skimage.filters import threshold_niblack, threshold_sauvola
from skimage.morphology import disk, opening, closing, white_tophat, black_tophat
from skimage.restoration import estimate_sigma, denoise_wavelet
from typing import Tuple


def denoise_image(image: np.ndarray, method: str = "wavelet", sigma: float = None) -> np.ndarray:
    if image.ndim == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    else:
        gray = image.copy()

    if method == "wavelet":
        try:
            if sigma is None:
                sigma_est = estimate_sigma(gray)
            else:
                sigma_est = sigma
            denoised = denoise_wavelet(
                gray, sigma=sigma_est, mode="soft", wavelet_levels=3, method="BayesShrink"
            )
            denoised = np.clip(denoised * 255, 0, 255).astype(np.uint8)
        except (ImportError, ModuleNotFoundError):
            denoised = cv2.bilateralFilter(gray, d=9, sigmaColor=75, sigmaSpace=75)
    elif method == "bilateral":
        denoised = cv2.bilateralFilter(gray, d=9, sigmaColor=75, sigmaSpace=75)
    elif method == "gaussian":
        denoised = cv2.GaussianBlur(gray, (5, 5), 0)
    elif method == "median":
        denoised = cv2.medianBlur(gray, 3)
    else:
        denoised = gray

    return denoised


def suppress_texture(
    image: np.ndarray,
    method: str = "median",
    kernel_size: int = 7,
    sigma: float = 2.0,
) -> np.ndarray:
    if image.ndim == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    else:
        gray = image.copy()

    if method == "median":
        if kernel_size % 2 == 0:
            kernel_size += 1
        result = cv2.medianBlur(gray, kernel_size)
    elif method == "gaussian":
        if kernel_size % 2 == 0:
            kernel_size += 1
        result = cv2.GaussianBlur(gray, (kernel_size, kernel_size), sigma)
    elif method == "bilateral":
        if kernel_size % 2 == 0:
            kernel_size += 1
        result = cv2.bilateralFilter(gray, kernel_size, sigma * 10, sigma * 10)
    elif method == "morph":
        se = disk(kernel_size // 2)
        opened = opening(gray.astype(np.float64) / 255.0, se)
        result = (opened * 255).astype(np.uint8)
    elif method == "wavelet":
        try:
            sigma_est = estimate_sigma(gray) if sigma is None else sigma
            denoised = denoise_wavelet(
                gray, sigma=sigma_est, mode="soft", wavelet_levels=2, method="BayesShrink"
            )
            result = np.clip(denoised * 255, 0, 255).astype(np.uint8)
        except (ImportError, ModuleNotFoundError):
            result = cv2.medianBlur(gray, 7 if kernel_size % 2 == 1 else 9)
    else:
        result = gray

    return result


def background_estimation_morph(
    image: np.ndarray,
    kernel_size: int = 51,
    suppress_texture_first: bool = True,
    texture_kernel: int = 7,
    texture_method: str = "median",
    smooth_sigma: float = 3.0,
) -> np.ndarray:
    if image.ndim == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    else:
        gray = image.copy()

    if suppress_texture_first:
        gray = suppress_texture(gray, method=texture_method, kernel_size=texture_kernel)

    se = disk(kernel_size // 2)
    bg_float = closing(gray.astype(np.float64) / 255.0, se)
    bg = (bg_float * 255).astype(np.uint8)

    if smooth_sigma > 0:
        ksize = int(smooth_sigma * 6) + 1 if smooth_sigma > 0 else 0
        if ksize % 2 == 0:
            ksize += 1
        bg = cv2.GaussianBlur(bg, (ksize, ksize), smooth_sigma)

    return bg


def background_estimation_poly(
    image: np.ndarray,
    degree: int = 2,
    suppress_texture_first: bool = True,
    texture_kernel: int = 7,
    texture_method: str = "median",
    downsample: int = 4,
) -> np.ndarray:
    if image.ndim == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    else:
        gray = image.copy()

    h, w = gray.shape

    if suppress_texture_first:
        gray = suppress_texture(gray, method=texture_method, kernel_size=texture_kernel)

    if downsample > 1:
        ds_h = max(h // downsample, 4)
        ds_w = max(w // downsample, 4)
        gray_ds = cv2.resize(gray, (ds_w, ds_h), interpolation=cv2.INTER_AREA)
    else:
        ds_h, ds_w = h, w
        gray_ds = gray

    y_indices, x_indices = np.meshgrid(np.arange(ds_h), np.arange(ds_w), indexing="ij")
    x_flat = x_indices.flatten().astype(np.float64)
    y_flat = y_indices.flatten().astype(np.float64)
    z_flat = gray_ds.flatten().astype(np.float64)

    if degree == 1:
        A = np.column_stack([x_flat, y_flat, np.ones_like(x_flat)])
    elif degree == 2:
        A = np.column_stack(
            [x_flat ** 2, y_flat ** 2, x_flat * y_flat, x_flat, y_flat, np.ones_like(x_flat)]
        )
    else:
        A = np.column_stack(
            [
                x_flat ** 3, y_flat ** 3, x_flat ** 2 * y_flat, x_flat * y_flat ** 2,
                x_flat ** 2, y_flat ** 2, x_flat * y_flat, x_flat, y_flat,
                np.ones_like(x_flat),
            ]
        )

    coeffs, _, _, _ = np.linalg.lstsq(A, z_flat, rcond=None)

    if downsample > 1:
        y_full, x_full = np.meshgrid(np.arange(h), np.arange(w), indexing="ij")
        x_full_flat = x_full.flatten().astype(np.float64)
        y_full_flat = y_full.flatten().astype(np.float64)
        if degree == 1:
            A_full = np.column_stack([x_full_flat, y_full_flat, np.ones_like(x_full_flat)])
        elif degree == 2:
            A_full = np.column_stack(
                [x_full_flat ** 2, y_full_flat ** 2, x_full_flat * y_full_flat,
                 x_full_flat, y_full_flat, np.ones_like(x_full_flat)]
            )
        else:
            A_full = np.column_stack(
                [
                    x_full_flat ** 3, y_full_flat ** 3, x_full_flat ** 2 * y_full_flat,
                    x_full_flat * y_full_flat ** 2, x_full_flat ** 2, y_full_flat ** 2,
                    x_full_flat * y_full_flat, x_full_flat, y_full_flat,
                    np.ones_like(x_full_flat),
                ]
            )
        bg_flat = A_full @ coeffs
        bg = bg_flat.reshape(h, w)
    else:
        bg_flat = A @ coeffs
        bg = bg_flat.reshape(h, w)

    bg = np.clip(bg, 0, 255).astype(np.uint8)
    return bg


def remove_background(
    image: np.ndarray, bg: np.ndarray, method: str = "divide"
) -> np.ndarray:
    if image.ndim == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    else:
        gray = image.copy()

    gray_f = gray.astype(np.float64)
    bg_f = bg.astype(np.float64)
    bg_f = np.maximum(bg_f, 1.0)

    if method == "divide":
        result = (gray_f / bg_f) * 255.0
    elif method == "subtract":
        result = gray_f - bg_f + 128.0
    else:
        result = gray_f

    result = np.clip(result, 0, 255).astype(np.uint8)
    return result


def sauvola_threshold(
    image: np.ndarray,
    window_size: int = 15,
    k: float = 0.2,
    r: float = 128.0,
) -> np.ndarray:
    if image.ndim == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    else:
        gray = image.copy()

    if window_size % 2 == 0:
        window_size += 1

    thresh_sauvola = threshold_sauvola(
        gray, window_size=window_size, k=k, r=r
    )
    binary = (gray > thresh_sauvola).astype(np.uint8) * 255
    return binary


def niblack_threshold(
    image: np.ndarray,
    window_size: int = 15,
    k: float = -0.2,
) -> np.ndarray:
    if image.ndim == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    else:
        gray = image.copy()

    if window_size % 2 == 0:
        window_size += 1

    thresh_niblack = threshold_niblack(
        gray, window_size=window_size, k=k
    )
    binary = (gray > thresh_niblack).astype(np.uint8) * 255
    return binary


def otsu_threshold(image: np.ndarray) -> np.ndarray:
    if image.ndim == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    else:
        gray = image.copy()

    _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    return binary


def adaptive_threshold(
    image: np.ndarray,
    block_size: int = 11,
    C: int = 2,
    method: str = "gaussian",
) -> np.ndarray:
    if image.ndim == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    else:
        gray = image.copy()

    if block_size % 2 == 0:
        block_size += 1

    if method == "gaussian":
        adaptive_method = cv2.ADAPTIVE_THRESH_GAUSSIAN_C
    else:
        adaptive_method = cv2.ADAPTIVE_THRESH_MEAN_C

    binary = cv2.adaptiveThreshold(
        gray, 255, adaptive_method, cv2.THRESH_BINARY, block_size, C
    )
    return binary


def binarize_pipeline(
    image: np.ndarray,
    method: str = "sauvola",
    denoise: bool = True,
    denoise_method: str = "wavelet",
    bg_estimation: str = "none",
    bg_kernel_size: int = 51,
    bg_degree: int = 2,
    bg_texture_suppress: bool = True,
    bg_texture_kernel: int = 7,
    bg_texture_method: str = "median",
    bg_smooth_sigma: float = 3.0,
    bg_downsample: int = 4,
    window_size: int = 15,
    k: float = 0.2,
    r: float = 128.0,
    block_size: int = 11,
    C: int = 2,
    post_process: bool = True,
    morph_kernel: int = 1,
) -> np.ndarray:
    if image.ndim == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    else:
        gray = image.copy()

    if denoise:
        gray = denoise_image(gray, method=denoise_method)

    if bg_estimation == "morph":
        bg = background_estimation_morph(
            gray,
            kernel_size=bg_kernel_size,
            suppress_texture_first=bg_texture_suppress,
            texture_kernel=bg_texture_kernel,
            texture_method=bg_texture_method,
            smooth_sigma=bg_smooth_sigma,
        )
        gray = remove_background(gray, bg, method="divide")
    elif bg_estimation == "poly":
        bg = background_estimation_poly(
            gray,
            degree=bg_degree,
            suppress_texture_first=bg_texture_suppress,
            texture_kernel=bg_texture_kernel,
            texture_method=bg_texture_method,
            downsample=bg_downsample,
        )
        gray = remove_background(gray, bg, method="divide")

    method = method.lower()
    if method == "sauvola":
        binary = sauvola_threshold(gray, window_size=window_size, k=k, r=r)
    elif method == "niblack":
        binary = niblack_threshold(gray, window_size=window_size, k=k)
    elif method == "otsu":
        binary = otsu_threshold(gray)
    elif method == "adaptive":
        binary = adaptive_threshold(gray, block_size=block_size, C=C)
    else:
        binary = sauvola_threshold(gray, window_size=window_size, k=k, r=r)

    if post_process and morph_kernel > 0:
        if morph_kernel % 2 == 0:
            morph_kernel += 1
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (morph_kernel, morph_kernel))
        binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)
        binary = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel)

    return binary