import numpy as np
import time
from typing import Tuple, Optional

try:
    from numba import jit, prange, float32, int32
    NUMBA_AVAILABLE = True
except ImportError:
    NUMBA_AVAILABLE = False
    def jit(*args, **kwargs):
        def decorator(func):
            return func
        return decorator
    prange = range

print(f"Numba {'加速已启用' if NUMBA_AVAILABLE else '不可用，使用纯Numpy'}")


@jit(nopython=True, parallel=True, fastmath=True)
def refocus_numba(images: np.ndarray, alpha: float,
                   center_row: int, center_col: int) -> np.ndarray:
    num_rows, num_cols, height, width = images.shape
    refocused = np.zeros((height, width), dtype=float32)
    weight_sum = np.zeros((height, width), dtype=float32)

    for r in prange(num_rows):
        for c in range(num_cols):
            dr = r - center_row
            dc = c - center_col

            shift_y = int(dr * alpha * 2)
            shift_x = int(dc * alpha * 2)

            weight = 1.0 / (1.0 + abs(dr) + abs(dc))

            for y in range(height):
                src_y = y - shift_y
                if 0 <= src_y < height:
                    for x in range(width):
                        src_x = x - shift_x
                        if 0 <= src_x < width:
                            refocused[y, x] += weight * images[r, c, src_y, src_x]
                            weight_sum[y, x] += weight

    for y in prange(height):
        for x in range(width):
            if weight_sum[y, x] > 0:
                refocused[y, x] /= weight_sum[y, x]

    return refocused


@jit(nopython=True, parallel=True, fastmath=True)
def compute_laplacian_focus_numba(stack: np.ndarray) -> np.ndarray:
    num_planes, height, width = stack.shape
    focus = np.zeros((num_planes, height, width), dtype=float32)

    for p in prange(num_planes):
        for y in range(1, height - 1):
            for x in range(1, width - 1):
                lap = (-4 * stack[p, y, x] +
                       stack[p, y-1, x] + stack[p, y+1, x] +
                       stack[p, y, x-1] + stack[p, y, x+1])
                focus[p, y, x] = abs(lap)

    return focus


@jit(nopython=True, parallel=True, fastmath=True)
def compute_defocus_var_numba(images: np.ndarray, center_view: np.ndarray,
                               center_row: int, center_col: int,
                               patch_size: int) -> np.ndarray:
    num_rows, num_cols, height, width = images.shape
    variances = np.zeros((height, width), dtype=float32)
    count = 0

    for r in prange(num_rows):
        for c in range(num_cols):
            if r == center_row and c == center_col:
                continue
            count += 1
            for y in range(height):
                for x in range(width):
                    diff = images[r, c, y, x] - center_view[y, x]
                    variances[y, x] += diff * diff

    if count > 0:
        for y in prange(height):
            for x in range(width):
                variances[y, x] /= count

    half = patch_size // 2
    result = np.zeros((height, width), dtype=float32)

    for y in prange(height):
        for x in range(width):
            y0 = max(0, y - half)
            y1 = min(height, y + half + 1)
            x0 = max(0, x - half)
            x1 = min(width, x + half + 1)
            s = 0.0
            n = 0
            for yy in range(y0, y1):
                for xx in range(x0, x1):
                    s += variances[yy, xx]
                    n += 1
            result[y, x] = s / n if n > 0 else 0

    return result


@jit(nopython=True, parallel=True, fastmath=True)
def warp_affine_numba(image: np.ndarray, shift_x: int, shift_y: int) -> np.ndarray:
    height, width = image.shape
    result = np.zeros((height, width), dtype=float32)

    for y in prange(height):
        src_y = y - shift_y
        if 0 <= src_y < height:
            for x in range(width):
                src_x = x - shift_x
                if 0 <= src_x < width:
                    result[y, x] = image[src_y, src_x]

    return result


@jit(nopython=True, parallel=True, fastmath=True)
def box_filter_numba(image: np.ndarray, ksize: int) -> np.ndarray:
    height, width = image.shape
    result = np.zeros((height, width), dtype=float32)
    half = ksize // 2

    for y in prange(height):
        y0 = max(0, y - half)
        y1 = min(height, y + half + 1)
        for x in range(width):
            x0 = max(0, x - half)
            x1 = min(width, x + half + 1)
            s = 0.0
            n = 0
            for yy in range(y0, y1):
                for xx in range(x0, x1):
                    s += image[yy, xx]
                    n += 1
            result[y, x] = s / n if n > 0 else 0

    return result


@jit(nopython=True, parallel=True, fastmath=True)
def compute_disparity_cost_numba(images: np.ndarray, center_view: np.ndarray,
                                  center_row: int, center_col: int,
                                  disp_min: int, disp_max: int,
                                  patch_size: int) -> np.ndarray:
    num_rows, num_cols, height, width = images.shape
    num_disps = disp_max - disp_min
    cost_volume = np.zeros((num_disps, height, width), dtype=float32)

    for d_idx in prange(num_disps):
        d = disp_min + d_idx
        for r in range(num_rows):
            for c in range(num_cols):
                if r == center_row and c == center_col:
                    continue
                dr = r - center_row
                dc = c - center_col
                shift_x = int(dc * d)
                shift_y = int(dr * d)

                for y in range(height):
                    src_y = y - shift_y
                    if 0 <= src_y < height:
                        for x in range(width):
                            src_x = x - shift_x
                            if 0 <= src_x < width:
                                cost_volume[d_idx, y, x] += abs(
                                    images[r, c, src_y, src_x] - center_view[y, x]
                                )

    k = patch_size
    half = k // 2
    smoothed = np.zeros((num_disps, height, width), dtype=float32)

    for d in prange(num_disps):
        for y in range(height):
            y0 = max(0, y - half)
            y1 = min(height, y + half + 1)
            for x in range(width):
                x0 = max(0, x - half)
                x1 = min(width, x + half + 1)
                s = 0.0
                n = 0
                for yy in range(y0, y1):
                    for xx in range(x0, x1):
                        s += cost_volume[d, yy, xx]
                        n += 1
                smoothed[d, y, x] = s / n if n > 0 else 0

    return smoothed


class AcceleratedProcessor:
    def __init__(self, use_numba: bool = True):
        self.use_numba = use_numba and NUMBA_AVAILABLE

    def benchmark_refocus(self, images: np.ndarray, alpha: float,
                           center_row: int, center_col: int,
                           iterations: int = 10) -> Tuple[float, np.ndarray]:
        t0 = time.time()
        for _ in range(iterations):
            if self.use_numba:
                result = refocus_numba(images.astype(np.float32), alpha,
                                        center_row, center_col)
            else:
                result = self._refocus_numpy(images, alpha, center_row, center_col)
        elapsed = (time.time() - t0) / iterations
        return elapsed, result

    def _refocus_numpy(self, images: np.ndarray, alpha: float,
                        center_row: int, center_col: int) -> np.ndarray:
        num_rows, num_cols, height, width = images.shape
        refocused = np.zeros((height, width), dtype=np.float32)
        weight_sum = np.zeros((height, width), dtype=np.float32)

        for r in range(num_rows):
            for c in range(num_cols):
                dr = r - center_row
                dc = c - center_col
                shift_y = int(dr * alpha * 2)
                shift_x = int(dc * alpha * 2)
                weight = 1.0 / (1.0 + abs(dr) + abs(dc))

                rolled = np.roll(np.roll(images[r, c], shift_y, axis=0), shift_x, axis=1)
                refocused += weight * rolled
                weight_sum += weight

        return refocused / weight_sum
