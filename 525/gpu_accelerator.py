import numpy as np
import cv2
from typing import Tuple, Optional
import warnings

try:
    import cupy as cp
    CUPY_AVAILABLE = True
except ImportError:
    CUPY_AVAILABLE = False
    warnings.warn("CuPy not available. GPU acceleration will be disabled.")

try:
    from numba import cuda, jit, prange
    NUMBA_AVAILABLE = True
except ImportError:
    NUMBA_AVAILABLE = False
    warnings.warn("Numba not available. Some GPU/CPU optimizations disabled.")


class GPULightFieldRefocus:
    TILE_X = 16
    TILE_Y = 16
    ALIGN_BYTES = 32
    
    def __init__(self, lf_data: np.ndarray, use_gpu: bool = True):
        self.lf_data = lf_data
        self.num_views_y, self.num_views_x = lf_data.shape[:2]
        self.h, self.w = lf_data.shape[2:4]
        self.center_vy = self.num_views_y // 2
        self.center_vx = self.num_views_x // 2
        self.use_gpu = use_gpu and (CUPY_AVAILABLE or NUMBA_AVAILABLE)
        
        self.w_aligned = int(np.ceil(self.w * 4 / self.ALIGN_BYTES) * self.ALIGN_BYTES // 4)
        self.h_aligned = int(np.ceil(self.h * 4 / self.ALIGN_BYTES) * self.ALIGN_BYTES // 4)
        
        if self.use_gpu and CUPY_AVAILABLE:
            self.lf_data_gpu = self._upload_aligned(lf_data)
    
    def _upload_aligned(self, lf_data: np.ndarray) -> 'cp.ndarray':
        lf_float = lf_data.astype(np.float32)
        ny, nx, h, w, c = lf_float.shape
        w_a = self.w_aligned
        h_a = self.h_aligned
        
        aligned = cp.zeros((ny, nx, h_a, w_a, c), dtype=cp.float32)
        for vy in range(ny):
            for vx in range(nx):
                aligned[vy, vx, :h, :w, :] = cp.asarray(lf_float[vy, vx])
        
        return aligned
    
    def refocus_cupy(self, alpha: float, aperture_size: float = 1.0) -> np.ndarray:
        if not CUPY_AVAILABLE:
            warnings.warn("CuPy not available, falling back to CPU.")
            return self._refocus_cpu(alpha, aperture_size)
        
        radius = int(min(self.num_views_x, self.num_views_y) // 2 * aperture_size)
        
        h_a, w_a = self.h_aligned, self.w_aligned
        tile_x, tile_y = self.TILE_X, self.TILE_Y
        
        result_gpu = cp.zeros((h_a, w_a, 3), dtype=cp.float32)
        weight_sum_gpu = cp.zeros((h_a, w_a), dtype=cp.float32)
        
        ny_tiles = (h_a + tile_y - 1) // tile_y
        nx_tiles = (w_a + tile_x - 1) // tile_x
        
        for vy in range(self.num_views_y):
            for vx in range(self.num_views_x):
                du = vx - self.center_vx
                dv = vy - self.center_vy
                
                if abs(du) > radius or abs(dv) > radius:
                    continue
                
                dist = cp.sqrt(du ** 2 + dv ** 2)
                if dist > radius:
                    continue
                
                weight = 1.0 - (dist / radius) ** 2
                if weight <= 0:
                    continue
                
                shift_x = du * alpha
                shift_y = dv * alpha
                
                view = self.lf_data_gpu[vy, vx]
                
                for ty in range(ny_tiles):
                    for tx in range(nx_tiles):
                        y0 = ty * tile_y
                        x0 = tx * tile_x
                        y1 = min(y0 + tile_y, h_a)
                        x1 = min(x0 + tile_x, w_a)
                        
                        tile_h = y1 - y0
                        tile_w = x1 - x0
                        
                        y_coords = cp.arange(y0, y1, dtype=cp.float32).reshape(-1, 1)
                        x_coords = cp.arange(x0, x1, dtype=cp.float32).reshape(1, -1)
                        
                        y_src = cp.clip(y_coords - shift_y, 0, self.h - 1)
                        x_src = cp.clip(x_coords - shift_x, 0, self.w - 1)
                        
                        iy0 = cp.floor(y_src).astype(cp.int32)
                        iy1 = cp.minimum(iy0 + 1, self.h - 1)
                        ix0 = cp.floor(x_src).astype(cp.int32)
                        ix1 = cp.minimum(ix0 + 1, self.w - 1)
                        
                        fy = (y_src - iy0)[:, :, cp.newaxis]
                        fx = (x_src - ix0)[:, :, cp.newaxis]
                        
                        iy0b = cp.broadcast_to(iy0[:, :, cp.newaxis], (tile_h, tile_w, 3))
                        iy1b = cp.broadcast_to(iy1[:, :, cp.newaxis], (tile_h, tile_w, 3))
                        ix0b = cp.broadcast_to(ix0[:, :, cp.newaxis], (tile_h, tile_w, 3))
                        ix1b = cp.broadcast_to(ix1[:, :, cp.newaxis], (tile_h, tile_w, 3))
                        
                        v00 = view[iy0, ix0]
                        v01 = view[iy0, ix1]
                        v10 = view[iy1, ix0]
                        v11 = view[iy1, ix1]
                        
                        interp = (v00 * (1 - fx) * (1 - fy) +
                                  v01 * fx * (1 - fy) +
                                  v10 * (1 - fx) * fy +
                                  v11 * fx * fy)
                        
                        result_gpu[y0:y1, x0:x1] += interp * weight
                        weight_sum_gpu[y0:y1, x0:x1] += weight
        
        weight_sum_gpu = cp.where(weight_sum_gpu == 0, 1, weight_sum_gpu)
        result_gpu = result_gpu / weight_sum_gpu[:, :, cp.newaxis]
        
        result = cp.asnumpy(result_gpu[:self.h, :self.w])
        return np.clip(result, 0, 255).astype(np.uint8)
    
    def _refocus_cpu(self, alpha: float, aperture_size: float = 1.0) -> np.ndarray:
        from lf_refocus import LightFieldRefocus
        refocus = LightFieldRefocus(self.lf_data)
        return refocus.refocus_fast(alpha, aperture_size)
    
    def refocus_numba(self, alpha: float, aperture_size: float = 1.0) -> np.ndarray:
        if not NUMBA_AVAILABLE:
            warnings.warn("Numba not available, falling back to CPU.")
            return self._refocus_cpu(alpha, aperture_size)
        
        radius = int(min(self.num_views_x, self.num_views_y) // 2 * aperture_size)
        
        lf_float = self.lf_data.astype(np.float32)
        result = np.zeros((self.h, self.w, 3), dtype=np.float32)
        weight_sum = np.zeros((self.h, self.w), dtype=np.float32)
        
        tile_y, tile_x = self.TILE_Y, self.TILE_X
        ny_tiles = (self.h + tile_y - 1) // tile_y
        nx_tiles = (self.w + tile_x - 1) // tile_x
        
        self._numba_refocus_tiled(
            lf_float, result, weight_sum,
            alpha, radius,
            self.num_views_y, self.num_views_x,
            self.center_vy, self.center_vx,
            self.h, self.w,
            tile_y, tile_x,
            ny_tiles, nx_tiles
        )
        
        weight_sum[weight_sum == 0] = 1
        result = result / weight_sum[:, :, np.newaxis]
        
        return np.clip(result, 0, 255).astype(np.uint8)
    
    @staticmethod
    @jit(nopython=True, parallel=True)
    def _numba_refocus_tiled(lf_data, result, weight_sum, alpha, radius,
                              num_views_y, num_views_x, center_vy, center_vx,
                              h, w, tile_y, tile_x, ny_tiles, nx_tiles):
        for tile_idx in prange(ny_tiles * nx_tiles):
            ty = tile_idx // nx_tiles
            tx = tile_idx % nx_tiles
            
            y_start = ty * tile_y
            x_start = tx * tile_x
            y_end = min(y_start + tile_y, h)
            x_end = min(x_start + tile_x, w)
            
            tile_result = np.zeros((tile_y, tile_x, 3), dtype=np.float32)
            tile_weight = np.zeros((tile_y, tile_x), dtype=np.float32)
            
            for vy in range(num_views_y):
                for vx in range(num_views_x):
                    du = vx - center_vx
                    dv = vy - center_vy
                    
                    if abs(du) > radius or abs(dv) > radius:
                        continue
                    
                    dist = np.sqrt(du ** 2 + dv ** 2)
                    if dist > radius:
                        continue
                    
                    weight = 1.0 - (dist / radius) ** 2
                    if weight <= 0:
                        continue
                    
                    shift_x = du * alpha
                    shift_y = dv * alpha
                    
                    for ly in range(y_end - y_start):
                        y = y_start + ly
                        y_shifted = y - shift_y
                        y_shifted = max(0.0, min(float(h - 1), y_shifted))
                        iy0 = int(np.floor(y_shifted))
                        iy1 = min(iy0 + 1, h - 1)
                        fy = y_shifted - iy0
                        
                        for lx in range(x_end - x_start):
                            x = x_start + lx
                            x_shifted = x - shift_x
                            x_shifted = max(0.0, min(float(w - 1), x_shifted))
                            ix0 = int(np.floor(x_shifted))
                            ix1 = min(ix0 + 1, w - 1)
                            fx = x_shifted - ix0
                            
                            for c in range(3):
                                val = (lf_data[vy, vx, iy0, ix0, c] * (1 - fx) * (1 - fy) +
                                       lf_data[vy, vx, iy0, ix1, c] * fx * (1 - fy) +
                                       lf_data[vy, vx, iy1, ix0, c] * (1 - fx) * fy +
                                       lf_data[vy, vx, iy1, ix1, c] * fx * fy)
                                tile_result[ly, lx, c] += val * weight
                            
                            tile_weight[ly, lx] += weight
            
            for ly in range(y_end - y_start):
                for lx in range(x_end - x_start):
                    y = y_start + ly
                    x = x_start + lx
                    for c in range(3):
                        result[y, x, c] = tile_result[ly, lx, c]
                    weight_sum[y, x] = tile_weight[ly, lx]
    
    def focus_stack_cupy(self, num_planes: int = 10,
                          aperture_size: float = 1.0,
                          depth_range: Tuple[float, float] = (-3.0, 3.0)) -> np.ndarray:
        alphas = np.linspace(depth_range[0], depth_range[1], num_planes)
        stack = []
        
        for alpha in alphas:
            if CUPY_AVAILABLE and self.use_gpu:
                focused = self.refocus_cupy(alpha, aperture_size)
            else:
                focused = self._refocus_cpu(alpha, aperture_size)
            stack.append(focused)
        
        return np.array(stack)


def to_gpu(arr: np.ndarray) -> Optional['cp.ndarray']:
    if CUPY_AVAILABLE:
        return cp.asarray(arr)
    return None


def to_cpu(arr: 'cp.ndarray') -> np.ndarray:
    if CUPY_AVAILABLE and isinstance(arr, cp.ndarray):
        return cp.asnumpy(arr)
    return arr


class GPUFilter:
    @staticmethod
    def gaussian_blur_cupy(image: np.ndarray, sigma: float = 1.0) -> np.ndarray:
        if not CUPY_AVAILABLE:
            return cv2.GaussianBlur(image, (0, 0), sigma)
        
        image_gpu = cp.asarray(image.astype(np.float32))
        
        size = int(2 * np.ceil(3 * sigma) + 1)
        x = cp.arange(size) - size // 2
        g = cp.exp(-x ** 2 / (2 * sigma ** 2))
        g = g / g.sum()
        
        for c in range(image_gpu.shape[2]):
            temp = cp.convolve(image_gpu[:, :, c].flatten(), g, mode='same')
            temp = temp.reshape(image_gpu.shape[0], image_gpu.shape[1])
            image_gpu[:, :, c] = cp.convolve(temp.T.flatten(), g, mode='same').reshape(
                image_gpu.shape[1], image_gpu.shape[0]
            ).T
        
        return cp.asnumpy(image_gpu).astype(np.uint8)
    
    @staticmethod
    @jit(nopython=True, parallel=True)
    def fast_bilateral_filter(image: np.ndarray, sigma_color: float = 75.0,
                               sigma_space: float = 75.0) -> np.ndarray:
        h, w = image.shape[:2]
        result = np.zeros_like(image, dtype=np.float32)
        
        radius = int(np.ceil(sigma_space * 2))
        
        for y in prange(h):
            for x in range(w):
                total_weight = 0.0
                sum_pixel = np.zeros(3, dtype=np.float32)
                
                for dy in range(-radius, radius + 1):
                    for dx in range(-radius, radius + 1):
                        ny = y + dy
                        nx = x + dx
                        
                        if 0 <= ny < h and 0 <= nx < w:
                            space_dist = dx * dx + dy * dy
                            color_dist = np.sum((image[y, x] - image[ny, nx]) ** 2)
                            
                            weight = np.exp(-space_dist / (2 * sigma_space ** 2) -
                                           color_dist / (2 * sigma_color ** 2))
                            
                            sum_pixel += image[ny, nx] * weight
                            total_weight += weight
                
                if total_weight > 0:
                    result[y, x] = sum_pixel / total_weight
        
        return result.astype(np.uint8)


class FastDepthEstimation:
    @staticmethod
    @jit(nopython=True, parallel=True)
    def fast_disparity(left: np.ndarray, right: np.ndarray,
                        max_disparity: int = 64,
                        block_size: int = 11) -> np.ndarray:
        h, w = left.shape
        half_block = block_size // 2
        disparity = np.zeros((h, w), dtype=np.float32)
        
        for y in prange(half_block, h - half_block):
            for x in range(half_block, w - half_block):
                best_sad = 1e9
                best_d = 0
                
                for d in range(max_disparity):
                    if x - d < half_block:
                        continue
                    
                    sad = 0.0
                    for by in range(-half_block, half_block + 1):
                        for bx in range(-half_block, half_block + 1):
                            sad += abs(int(left[y + by, x + bx]) - 
                                      int(right[y + by, x + bx - d]))
                    
                    if sad < best_sad:
                        best_sad = sad
                        best_d = d
                
                disparity[y, x] = best_d
        
        return disparity


def check_gpu_available() -> dict:
    info = {
        'cupy_available': CUPY_AVAILABLE,
        'numba_available': NUMBA_AVAILABLE,
        'cuda_available': False,
        'gpu_count': 0
    }
    
    if CUPY_AVAILABLE:
        try:
            info['cuda_available'] = cp.cuda.is_available()
            info['gpu_count'] = cp.cuda.runtime.getDeviceCount()
            if info['gpu_count'] > 0:
                info['gpu_name'] = cp.cuda.Device(0).name()
        except:
            pass
    
    if NUMBA_AVAILABLE:
        try:
            info['numba_cuda'] = cuda.is_available()
        except:
            info['numba_cuda'] = False
    
    return info


def benchmark_refocus(lf_data: np.ndarray, alpha: float = 0.0) -> dict:
    import time
    
    results = {}
    
    from lf_refocus import LightFieldRefocus
    refocus_cpu = LightFieldRefocus(lf_data)
    
    start = time.time()
    _ = refocus_cpu.refocus_fast(alpha)
    results['cpu_time'] = time.time() - start
    
    gpu_refocus = GPULightFieldRefocus(lf_data, use_gpu=True)
    
    if CUPY_AVAILABLE:
        start = time.time()
        _ = gpu_refocus.refocus_cupy(alpha)
        results['cupy_time'] = time.time() - start
        results['cupy_speedup'] = results['cpu_time'] / results['cupy_time']
    
    if NUMBA_AVAILABLE:
        start = time.time()
        _ = gpu_refocus.refocus_numba(alpha)
        results['numba_time'] = time.time() - start
        results['numba_speedup'] = results['cpu_time'] / results['numba_time']
    
    return results
