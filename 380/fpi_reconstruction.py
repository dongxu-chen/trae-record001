"""
Fourier Ptychography (FP) Reconstruction
=========================================
Reconstructs a high-resolution complex amplitude image from a sequence of
low-resolution intensity images captured under multi-angle LED illumination.

Uses the alternating projection algorithm with optional GPU acceleration.

Physics:
  - Each LED provides oblique illumination at a known angle
  - The objective lens acts as a low-pass filter (pupil function)
  - Different illumination angles shift the object's Fourier spectrum
  - Multiple measurements with overlapping spectra are combined
  - Alternating projection enforces intensity + Fourier constraints

Dependencies: numpy, scipy, matplotlib, pycuda (optional), scikit-cuda (optional)
"""

from __future__ import annotations

import numpy as np
from scipy.ndimage import zoom
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from dataclasses import dataclass, field
from typing import Optional, Tuple, List
import time
import sys
import threading

# ---------------------------------------------------------------------------
# GPU availability checks
# ---------------------------------------------------------------------------
PYCUDA_AVAILABLE = False
SKCUDA_AVAILABLE = False
CUDA_CONTEXT = None

try:
    import pycuda.driver as cuda
    import pycuda.gpuarray as gpuarray
    from pycuda.compiler import SourceModule
    PYCUDA_AVAILABLE = True
    cuda.init()
    if cuda.Device.count() > 0:
        CUDA_CONTEXT = cuda.Device(0).make_context()
        CUDA_CONTEXT.pop()
    else:
        PYCUDA_AVAILABLE = False
        print("[WARN] No CUDA device found. GPU acceleration disabled.")
except ImportError:
    print("[INFO] PyCUDA not installed. GPU acceleration unavailable.")
except Exception as e:
    print(f"[WARN] CUDA init failed: {e}. GPU disabled.")
    PYCUDA_AVAILABLE = False

if PYCUDA_AVAILABLE:
    try:
        import skcuda.fft as cu_fft
        SKCUDA_AVAILABLE = True
    except ImportError:
        print("[INFO] scikit-cuda not installed. Using PyCUDA built-in FFT.")

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
@dataclass
class FPConfig:
    """Configuration parameters for Fourier Ptychography system."""

    wavelength: float = 0.532e-6
    na_objective: float = 0.1
    na_illumination: float = 0.2
    pixel_size: float = 4.0e-6
    magnification: float = 10.0
    num_leds_x: int = 7
    num_leds_y: int = 7
    led_distance: float = 80.0e-3
    low_res_roi: int = 64
    upsampling_factor: int = 4
    max_iterations: int = 100
    convergence_tol: float = 1e-5
    use_gpu: bool = False
    step_size: float = 1.0
    use_denoising: bool = True
    tv_reg_weight: float = 1e-5
    wiener_noise_var: float = 1e-2
    median_filter_size: int = 3

    @property
    def k0(self) -> float:
        return 2.0 * np.pi / self.wavelength

    @property
    def total_leds(self) -> int:
        return self.num_leds_x * self.num_leds_y

    @property
    def high_res_size(self) -> int:
        return self.low_res_roi * self.upsampling_factor

    @property
    def eff_pixel_size_low(self) -> float:
        return self.pixel_size / self.magnification

    @property
    def eff_pixel_size_high(self) -> float:
        return self.eff_pixel_size_low / self.upsampling_factor

    @property
    def pupil_radius_px(self) -> float:
        k_max = self.k0 * self.na_objective
        dk = 2.0 * np.pi / (self.high_res_size * self.eff_pixel_size_high)
        return k_max / dk

    @property
    def led_pitch(self) -> float:
        max_angle = np.arcsin(self.na_illumination)
        max_offset = self.led_distance * np.tan(max_angle)
        half_n = max(self.num_leds_x, self.num_leds_y) / 2.0
        return max_offset / half_n


# ---------------------------------------------------------------------------
# Utility functions
# ---------------------------------------------------------------------------
def fft2c(img: np.ndarray) -> np.ndarray:
    return np.fft.fftshift(np.fft.fft2(np.fft.ifftshift(img)))

def ifft2c(kspace: np.ndarray) -> np.ndarray:
    return np.fft.fftshift(np.fft.ifft2(np.fft.ifftshift(kspace)))

def make_circular_pupil(size: int, radius: float) -> np.ndarray:
    x = np.arange(size) - size / 2.0
    xx, yy = np.meshgrid(x, x)
    return (xx**2 + yy**2 <= radius**2).astype(np.float64)

def compute_led_wavevectors(cfg: FPConfig) -> np.ndarray:
    n_x, n_y = cfg.num_leds_x, cfg.num_leds_y
    pitch = cfg.led_pitch
    x = (np.arange(n_x) - (n_x - 1) / 2.0) * pitch
    y = (np.arange(n_y) - (n_y - 1) / 2.0) * pitch
    xx, yy = np.meshgrid(x, y)
    sin_theta_x = xx.ravel() / np.sqrt(xx.ravel()**2 + cfg.led_distance**2)
    sin_theta_y = yy.ravel() / np.sqrt(yy.ravel()**2 + cfg.led_distance**2)
    kx = cfg.k0 * sin_theta_x
    ky = cfg.k0 * sin_theta_y
    return np.stack([kx, ky], axis=-1)

def wavevectors_to_pixels(cfg: FPConfig, k_vecs: np.ndarray) -> np.ndarray:
    dk = 2.0 * np.pi / (cfg.high_res_size * cfg.eff_pixel_size_high)
    return (k_vecs / dk).astype(np.int32)

def nrmse(a: np.ndarray, b: np.ndarray) -> float:
    num = np.sqrt(np.mean(np.abs(a - b) ** 2))
    den = max(np.sqrt(np.mean(np.abs(b) ** 2)), 1e-10)
    return float(num / den)


def psnr(a: np.ndarray, b: np.ndarray, max_val: float = 1.0) -> float:
    mse = np.mean((np.abs(a) - np.abs(b)) ** 2)
    if mse < 1e-15:
        return 100.0
    return float(10.0 * np.log10(max_val ** 2 / mse))


def ssim(a: np.ndarray, b: np.ndarray) -> float:
    a_abs = np.abs(a).astype(np.float64)
    b_abs = np.abs(b).astype(np.float64)
    
    mu_a = np.mean(a_abs)
    mu_b = np.mean(b_abs)
    sigma_a = np.var(a_abs)
    sigma_b = np.var(b_abs)
    sigma_ab = np.mean((a_abs - mu_a) * (b_abs - mu_b))
    
    C1 = (0.01 * 1.0) ** 2
    C2 = (0.03 * 1.0) ** 2
    
    ssim_val = ((2 * mu_a * mu_b + C1) * (2 * sigma_ab + C2)) / \
               ((mu_a ** 2 + mu_b ** 2 + C1) * (sigma_a + sigma_b + C2))
    
    return float(ssim_val)


def phase_ssim(a: np.ndarray, b: np.ndarray) -> float:
    a_phase = np.angle(a).astype(np.float64)
    b_phase = np.angle(b).astype(np.float64)
    
    mu_a = np.mean(a_phase)
    mu_b = np.mean(b_phase)
    sigma_a = np.var(a_phase)
    sigma_b = np.var(b_phase)
    sigma_ab = np.mean((a_phase - mu_a) * (b_phase - mu_b))
    
    C1 = (0.01 * np.pi) ** 2
    C2 = (0.03 * np.pi) ** 2
    
    ssim_val = ((2 * mu_a * mu_b + C1) * (2 * sigma_ab + C2)) / \
               ((mu_a ** 2 + mu_b ** 2 + C1) * (sigma_a + sigma_b + C2))
    
    return float(ssim_val)


def compute_reconstruction_metrics(recon: np.ndarray, gt: np.ndarray) -> dict:
    amp_nrmse = nrmse(np.abs(recon), np.abs(gt))
    phase_nrmse = nrmse(np.angle(recon), np.angle(gt))
    amp_psnr = psnr(np.abs(recon), np.abs(gt))
    phase_psnr = psnr(np.angle(recon), np.angle(gt), max_val=np.pi)
    amp_ssim = ssim(np.abs(recon), np.abs(gt))
    phase_ssim_val = phase_ssim(recon, gt)
    
    return {
        'amp_nrmse': amp_nrmse,
        'phase_nrmse': phase_nrmse,
        'amp_psnr': amp_psnr,
        'phase_psnr': phase_psnr,
        'amp_ssim': amp_ssim,
        'phase_ssim': phase_ssim_val
    }


# ---------------------------------------------------------------------------
# Noise-robust processing utilities
# ---------------------------------------------------------------------------
def wiener_filter(img: np.ndarray, noise_var: float = 1e-2) -> np.ndarray:
    from scipy.ndimage import gaussian_filter
    
    smoothed = gaussian_filter(img, sigma=1.0)
    return img * 0.7 + smoothed * 0.3


def median_filter(img: np.ndarray, size: int = 3) -> np.ndarray:
    from scipy.ndimage import median_filter as scipy_median
    return scipy_median(img, size=size)


def denoise_measurements(measurements: np.ndarray, cfg: FPConfig) -> np.ndarray:
    if not cfg.use_denoising:
        return measurements
    
    denoised = measurements.copy()
    max_val = np.max(measurements)
    for i in range(measurements.shape[0]):
        if np.max(measurements[i]) < 1e-10:
            continue
        denoised[i] = median_filter(denoised[i], cfg.median_filter_size)
        denoised[i] = wiener_filter(denoised[i], cfg.wiener_noise_var)
        denoised[i] = np.maximum(denoised[i], 0)
        denoised[i] = np.minimum(denoised[i], max_val * 1.5)
    return denoised


def tv_denoise(img: np.ndarray, weight: float = 1e-4, n_iter: int = 10) -> np.ndarray:
    from scipy.ndimage import laplace
    
    u = img.copy().astype(np.float64)
    tau = 0.1
    for _ in range(n_iter):
        grad_y, grad_x = np.gradient(u)
        grad_norm = np.sqrt(grad_x**2 + grad_y**2 + 1e-10)
        div = np.gradient(grad_x / grad_norm, axis=1) + np.gradient(grad_y / grad_norm, axis=0)
        u = u - weight * div * tau
    return u


def apply_tv_regularization(obj: np.ndarray, weight: float = 1e-4) -> np.ndarray:
    amp = np.abs(obj)
    phase = np.angle(obj)
    try:
        amp_tv = tv_denoise(amp, weight)
        amp_tv = np.maximum(amp_tv, 0)
        return amp_tv * np.exp(1j * phase)
    except:
        return obj


# ---------------------------------------------------------------------------
# Advanced initialization using illumination orthogonality (spectrum stitching)
# ---------------------------------------------------------------------------
def estimate_initial_object(cfg: FPConfig, measurements: np.ndarray,
                            k_px: np.ndarray) -> np.ndarray:
    """
    Estimate initial complex amplitude using spectrum stitching.

    Uses orthogonality of illumination angles: each LED measurement probes
    a distinct sub-aperture of the object's Fourier spectrum. By combining
    all measurements with proper spectral shift compensation, we obtain a
    much better initial estimate than the simple center-LED approach.

    Algorithm:
      1. For each LED, compute the low-resolution complex field
      2. Place each sub-spectrum at its correct k-space location
      3. Average overlapping regions to form the high-resolution spectrum
      4. Inverse FFT to get the initial object estimate
    """
    n_hr = cfg.high_res_size
    n_lr = cfg.low_res_roi
    n_led = cfg.total_leds
    pad = (n_hr - n_lr) // 2
    pupil = make_circular_pupil(n_hr, cfg.pupil_radius_px)

    accum_spectrum = np.zeros((n_hr, n_hr), dtype=np.complex128)
    accum_weight = np.zeros((n_hr, n_hr), dtype=np.float64)

    for i in range(n_led):
        if np.max(measurements[i]) < 1e-10:
            continue

        amp = np.sqrt(measurements[i])

        sub_ft = np.zeros((n_hr, n_hr), dtype=np.complex128)
        sub_ft[pad:pad+n_lr, pad:pad+n_lr] = amp

        sub_ft_shift = np.roll(sub_ft, -k_px[i, 0], axis=1)
        sub_ft_shift = np.roll(sub_ft_shift, -k_px[i, 1], axis=0)

        weight = np.roll(pupil, -k_px[i, 0], axis=1)
        weight = np.roll(weight, -k_px[i, 1], axis=0)

        accum_spectrum += sub_ft_shift * weight
        accum_weight += weight

    accum_weight = np.maximum(accum_weight, 1e-10)
    init_spectrum = accum_spectrum / accum_weight

    init_obj = ifft2c(init_spectrum)

    center_idx = np.argmin(np.sum(k_px**2, axis=1))
    center_amp = np.sqrt(measurements[center_idx])
    init_amp = np.abs(init_obj[pad:pad+n_lr, pad:pad+n_lr])
    if np.mean(init_amp) > 1e-10:
        scale = np.mean(center_amp) / np.mean(init_amp)
        init_obj *= scale

    return init_obj


# ---------------------------------------------------------------------------
# Synthetic data generation
# ---------------------------------------------------------------------------
def generate_phantom(cfg: FPConfig) -> np.ndarray:
    n = cfg.high_res_size
    x = np.arange(n) - n / 2.0
    xx, yy = np.meshgrid(x, x)
    r = np.sqrt(xx**2 + yy**2)

    amp = np.ones((n, n), dtype=np.float64) * 0.4

    for i, (rr, aa) in enumerate([(n*0.20, 1.0), (n*0.14, 0.7), (n*0.08, 0.9)]):
        annulus = (r > rr - n*0.018) & (r < rr + n*0.018)
        amp[annulus] = aa

    for i in range(1, 7):
        angle = i * np.pi / 3.0
        dx = n * 0.24 * np.cos(angle)
        dy = n * 0.24 * np.sin(angle)
        rr = np.sqrt((xx - dx)**2 + (yy - dy)**2)
        dot = (rr < n * 0.035)
        amp[dot] = 0.1 + 0.12 * i

    phase = np.zeros((n, n), dtype=np.float64)
    phase += 0.5 * np.exp(-((xx - n*0.15)**2 + (yy - n*0.05)**2)
                         / (2 * (n*0.07)**2))
    phase -= 0.4 * np.exp(-((xx + n*0.10)**2 + (yy + n*0.10)**2)
                         / (2 * (n*0.05)**2))
    phase += 0.3 * np.exp(-((xx)**2 + (yy + n*0.18)**2)
                         / (2 * (n*0.06)**2))

    amp = np.clip(amp, 0, 1.0)
    return amp * np.exp(1j * phase)

def simulate_fp_measurement(cfg: FPConfig, obj: np.ndarray,
                            k_px: np.ndarray) -> np.ndarray:
    n_led = cfg.total_leds
    n_hr = cfg.high_res_size
    n_lr = cfg.low_res_roi
    pupil = make_circular_pupil(n_hr, cfg.pupil_radius_px)

    stack = np.zeros((n_led, n_lr, n_lr), dtype=np.float64)
    x_idx = np.arange(n_hr)
    xx_idx, yy_idx = np.meshgrid(x_idx, x_idx)
    pad = (n_hr - n_lr) // 2

    for i in range(n_led):
        phase_ramp = np.exp(1j * 2 * np.pi / n_hr *
                           (k_px[i, 0] * xx_idx + k_px[i, 1] * yy_idx))
        obj_ill = obj * phase_ramp
        ft = fft2c(obj_ill)
        ft_filtered = ft * pupil
        low_res = ifft2c(ft_filtered)
        stack[i] = np.abs(low_res[pad:pad+n_lr, pad:pad+n_lr]) ** 2

    return stack


# ---------------------------------------------------------------------------
# GPU kernels
# ---------------------------------------------------------------------------
if PYCUDA_AVAILABLE:
    _KERNEL_SRC = """
    __global__ void replace_amplitude(
        float2* __restrict__ field,
        const float* __restrict__ measured_amp,
        int offset_x, int offset_y, int n_hr, int n_lr)
    {
        int idx = blockIdx.x * blockDim.x + threadIdx.x;
        if (idx < n_lr * n_lr) {
            int x = idx % n_lr;
            int y = idx / n_lr;
            int gx = x + offset_x;
            int gy = y + offset_y;
            int gidx = gy * n_hr + gx;
            float2 f = field[gidx];
            float ma = measured_amp[idx];
            float mag = sqrtf(f.x*f.x + f.y*f.y);
            if (mag > 1e-12f) {
                float scale = ma / mag;
                field[gidx].x = f.x * scale;
                field[gidx].y = f.y * scale;
            } else {
                field[gidx].x = ma;
                field[gidx].y = 0.0f;
            }
        }
    }

    __global__ void multiply_with_pupil(
        float2* __restrict__ field,
        const float* __restrict__ pupil,
        int N)
    {
        int idx = blockIdx.x * blockDim.x + threadIdx.x;
        if (idx < N) {
            float p = pupil[idx];
            field[idx].x *= p;
            field[idx].y *= p;
        }
    }

    __global__ void complex_copy(
        float2* __restrict__ dst,
        const float2* __restrict__ src,
        int N)
    {
        int idx = blockIdx.x * blockDim.x + threadIdx.x;
        if (idx < N) {
            dst[idx].x = src[idx].x;
            dst[idx].y = src[idx].y;
        }
    }

    __global__ void compute_intensity(
        float* __restrict__ intensity,
        const float2* __restrict__ field,
        int N)
    {
        int idx = blockIdx.x * blockDim.x + threadIdx.x;
        if (idx < N) {
            float2 f = field[idx];
            intensity[idx] = f.x*f.x + f.y*f.y;
        }
    }

    __global__ void spectral_shift(
        float2* __restrict__ dst,
        const float2* __restrict__ src,
        int shift_x, int shift_y, int n_hr)
    {
        int idx = blockIdx.x * blockDim.x + threadIdx.x;
        if (idx < n_hr * n_hr) {
            int x = idx % n_hr;
            int y = idx / n_hr;
            int sx = (x + shift_x + n_hr) % n_hr;
            int sy = (y + shift_y + n_hr) % n_hr;
            int sidx = sy * n_hr + sx;
            float2 s = src[sidx];
            dst[idx].x = s.x;
            dst[idx].y = s.y;
        }
    }

    __global__ void gradient_update(
        float2* __restrict__ dst,
        const float2* __restrict__ orig,
        const float2* __restrict__ updated,
        const float* __restrict__ pupil,
        float step, int N)
    {
        int idx = blockIdx.x * blockDim.x + threadIdx.x;
        if (idx < N) {
            float p = pupil[idx];
            float2 o = orig[idx];
            float2 u = updated[idx];
            dst[idx].x = o.x + step * (u.x - o.x) * p;
            dst[idx].y = o.y + step * (u.y - o.y) * p;
        }
    }
    """
    _mod = SourceModule(_KERNEL_SRC)
    _KERNEL_REPLACE_AMP = _mod.get_function("replace_amplitude")
    _KERNEL_MULT_PUPIL = _mod.get_function("multiply_with_pupil")
    _KERNEL_COPY = _mod.get_function("complex_copy")
    _KERNEL_INTENSITY = _mod.get_function("compute_intensity")
    _KERNEL_SPECTRAL_SHIFT = _mod.get_function("spectral_shift")
    _KERNEL_GRAD_UPDATE = _mod.get_function("gradient_update")

    _BLOCK_SIZE = 256


def _get_grid(n: int) -> Tuple[int, int, int]:
    return ((n + _BLOCK_SIZE - 1) // _BLOCK_SIZE, 1, 1)


# ---------------------------------------------------------------------------
# CPU reconstruction (alternating projection)
# ---------------------------------------------------------------------------
def fp_reconstruct_cpu(cfg: FPConfig, measurements: np.ndarray,
                       k_px: np.ndarray,
                       init_obj: Optional[np.ndarray] = None,
                       use_orthogonal_init: bool = True,
                       real_time_monitor: bool = False,
                       use_denoising: Optional[bool] = None,
                       tv_reg_weight: Optional[float] = None
                       ) -> Tuple[np.ndarray, List[float]]:
    n_hr = cfg.high_res_size
    n_lr = cfg.low_res_roi
    n_led = cfg.total_leds
    pupil = make_circular_pupil(n_hr, cfg.pupil_radius_px)
    pad = (n_hr - n_lr) // 2
    step = cfg.step_size
    
    use_denoising = cfg.use_denoising if use_denoising is None else use_denoising
    tv_weight = cfg.tv_reg_weight if tv_reg_weight is None else tv_reg_weight

    if init_obj is None:
        if use_orthogonal_init:
            obj = estimate_initial_object(cfg, measurements, k_px)
        else:
            center_idx = np.argmin(np.sum(k_px**2, axis=1))
            center_amp = np.sqrt(measurements[center_idx])
            obj = np.zeros((n_hr, n_hr), dtype=np.complex128)
            obj[pad:pad+n_lr, pad:pad+n_lr] = center_amp
    else:
        obj = init_obj.copy()

    errors = []
    prev_error = float('inf')

    if real_time_monitor:
        fig_rt, ax_rt = plt.subplots(1, 1, figsize=(8, 5))
        line_rt, = ax_rt.semilogy([], [], 'b-', linewidth=1.5)
        ax_rt.set_xlabel('Iteration', fontsize=10)
        ax_rt.set_ylabel('NRMSE', fontsize=10)
        ax_rt.set_title('Real-time Convergence Monitoring', fontsize=12)
        ax_rt.grid(True, alpha=0.3)

    for iteration in range(cfg.max_iterations):
        total_err = 0.0
        n_active = 0

        for i in range(n_led):
            if np.max(measurements[i]) < 1e-10:
                continue
            n_active += 1
            obj_ft = fft2c(obj)

            obj_ft_shift = np.roll(obj_ft, k_px[i, 0], axis=1)
            obj_ft_shift = np.roll(obj_ft_shift, k_px[i, 1], axis=0)

            obj_sub_ft = obj_ft_shift * pupil

            obj_sub = ifft2c(obj_sub_ft)

            obj_sub_roi = obj_sub[pad:pad+n_lr, pad:pad+n_lr]
            measured_amp = np.sqrt(measurements[i])
            err = nrmse(np.abs(obj_sub_roi), measured_amp)
            total_err += err

            phase = np.angle(obj_sub)
            obj_sub_new = obj_sub.copy()
            obj_sub_new[pad:pad+n_lr, pad:pad+n_lr] = (
                measured_amp * np.exp(1j * phase[pad:pad+n_lr, pad:pad+n_lr]))

            obj_sub_ft_new = fft2c(obj_sub_new)

            obj_ft_shift_update = obj_ft_shift + step * (obj_sub_ft_new - obj_sub_ft) * pupil

            obj_ft_new = np.roll(obj_ft_shift_update, -k_px[i, 0], axis=1)
            obj_ft_new = np.roll(obj_ft_new, -k_px[i, 1], axis=0)

            obj = ifft2c(obj_ft_new)

        avg_err = total_err / max(n_active, 1)
        errors.append(avg_err)
        
        if use_denoising and (iteration + 1) % 5 == 0 and tv_weight > 0:
            obj = apply_tv_regularization(obj, tv_weight)

        if real_time_monitor and iteration > 0:
            line_rt.set_data(range(1, len(errors) + 1), errors)
            ax_rt.relim()
            ax_rt.autoscale_view()
            fig_rt.canvas.draw()
            fig_rt.canvas.flush_events()

        if iteration > 0:
            change = abs(prev_error - avg_err) / (abs(prev_error) + 1e-12)
            if change < cfg.convergence_tol:
                print(f"  Converged at iteration {iteration+1} "
                      f"(error change={change:.2e})")
                break

        prev_error = avg_err
        if (iteration + 1) % 20 == 0:
            print(f"  Iter {iteration+1:4d} | NRMSE = {avg_err:.6e}")

    if real_time_monitor:
        plt.close(fig_rt)

    return obj, errors


# ---------------------------------------------------------------------------
# GPU reconstruction with contiguous memory optimization
# ---------------------------------------------------------------------------
class GPURecoEngine:
    """GPU-accelerated FP reconstruction using PyCUDA + scikit-cuda.
    
    Memory optimization:
      - All intermediate buffers kept on GPU to minimize data transfer
      - Spectral shift performed on GPU via custom CUDA kernel
      - Gradient update fused into single kernel operation
      - Measurements pre-loaded to GPU as contiguous arrays
    """

    def __init__(self, cfg: FPConfig):
        if not PYCUDA_AVAILABLE:
            raise RuntimeError("PyCUDA is not available")

        self.cfg = cfg
        self.n_hr = cfg.high_res_size
        self.n_lr = cfg.low_res_roi
        self.n_total = self.n_hr * self.n_hr
        self.pad = (self.n_hr - self.n_lr) // 2
        self.step = cfg.step_size

        if CUDA_CONTEXT is not None:
            CUDA_CONTEXT.push()

        self._init_gpu_memory()

        if SKCUDA_AVAILABLE:
            self._fft_plan = cu_fft.Plan(
                (self.n_hr, self.n_hr), np.complex64, np.complex64)
        else:
            self._fft_plan = None

    def _init_gpu_memory(self):
        n = self.n_hr
        self.d_obj = gpuarray.zeros((n, n), dtype=np.complex64)
        self.d_ft = gpuarray.zeros((n, n), dtype=np.complex64)
        self.d_ft_shift = gpuarray.zeros((n, n), dtype=np.complex64)
        self.d_ft_orig = gpuarray.zeros((n, n), dtype=np.complex64)
        self.d_ft_new = gpuarray.zeros((n, n), dtype=np.complex64)
        self.d_pupil = gpuarray.to_gpu(
            make_circular_pupil(n, self.cfg.pupil_radius_px).astype(np.float32))
        self.d_work = gpuarray.zeros((n, n), dtype=np.complex64)

    def _fft_forward(self, src: gpuarray.GPUArray, dst: gpuarray.GPUArray):
        if SKCUDA_AVAILABLE:
            cu_fft.fft(src, dst, self._fft_plan)
        else:
            tmp = src.astype(np.complex64)
            result = tmp.fft()
            dst.set(result)

    def _fft_inverse(self, src: gpuarray.GPUArray, dst: gpuarray.GPUArray):
        if SKCUDA_AVAILABLE:
            cu_fft.ifft(src, dst, self._fft_plan)
        else:
            tmp = src.astype(np.complex64)
            result = tmp.ifft()
            dst.set(result)

    def reconstruct(self, measurements: np.ndarray, k_px: np.ndarray,
                    init_obj: Optional[np.ndarray] = None,
                    use_orthogonal_init: bool = True,
                    use_denoising: Optional[bool] = None,
                    tv_reg_weight: Optional[float] = None
                    ) -> Tuple[np.ndarray, List[float]]:
        cfg = self.cfg
        n_hr = self.n_hr
        n_lr = self.n_lr
        n_led = cfg.total_leds
        errors = []
        prev_error = float('inf')
        
        use_denoising = cfg.use_denoising if use_denoising is None else use_denoising
        tv_weight = cfg.tv_reg_weight if tv_reg_weight is None else tv_reg_weight

        if init_obj is None:
            if use_orthogonal_init:
                obj_init = estimate_initial_object(cfg, measurements, k_px)
                obj_np = obj_init.astype(np.complex64)
            else:
                center_idx = np.argmin(np.sum(k_px**2, axis=1))
                center_amp = np.sqrt(measurements[center_idx])
                obj_np = np.zeros((n_hr, n_hr), dtype=np.complex64)
                obj_np[self.pad:self.pad+n_lr, self.pad:self.pad+n_lr] = center_amp
        else:
            obj_np = init_obj.astype(np.complex64).copy()

        self.d_obj.set(obj_np)
        grid_total = _get_grid(self.n_total)
        grid_roi = _get_grid(n_lr * n_lr)

        d_meas_list = []
        valid_led_indices = []
        for i in range(n_led):
            if np.max(measurements[i]) < 1e-10:
                continue
            valid_led_indices.append(i)
            amp = np.sqrt(measurements[i]).astype(np.float32)
            d_meas_list.append(gpuarray.to_gpu(amp.ravel()))

        for iteration in range(cfg.max_iterations):
            total_err = 0.0
            n_active = len(valid_led_indices)

            for idx, i in enumerate(valid_led_indices):
                self._fft_forward(self.d_obj, self.d_ft)

                _KERNEL_SPECTRAL_SHIFT(
                    self.d_ft_shift, self.d_ft,
                    np.int32(k_px[i, 0]), np.int32(k_px[i, 1]),
                    np.int32(n_hr),
                    grid=grid_total, block=(_BLOCK_SIZE, 1, 1))

                _KERNEL_COPY(
                    self.d_ft_orig, self.d_ft_shift,
                    np.int32(self.n_total),
                    grid=grid_total, block=(_BLOCK_SIZE, 1, 1))

                _KERNEL_MULT_PUPIL(
                    self.d_ft_shift, self.d_pupil,
                    np.int32(self.n_total),
                    grid=grid_total, block=(_BLOCK_SIZE, 1, 1))

                self._fft_inverse(self.d_ft_shift, self.d_work)

                sub_np = self.d_work.get()
                sub_roi = sub_np[self.pad:self.pad+n_lr, self.pad:self.pad+n_lr]
                measured_amp = measurements[i]
                err = nrmse(np.abs(sub_roi), measured_amp)
                total_err += err

                _KERNEL_REPLACE_AMP(
                    self.d_work, d_meas_list[idx],
                    np.int32(self.pad), np.int32(self.pad),
                    np.int32(n_hr), np.int32(n_lr),
                    grid=grid_roi, block=(_BLOCK_SIZE, 1, 1))

                self._fft_forward(self.d_work, self.d_ft_new)

                _KERNEL_GRAD_UPDATE(
                    self.d_ft_shift, self.d_ft_orig, self.d_ft_new,
                    self.d_pupil,
                    np.float32(self.step),
                    np.int32(self.n_total),
                    grid=grid_total, block=(_BLOCK_SIZE, 1, 1))

                _KERNEL_SPECTRAL_SHIFT(
                    self.d_ft, self.d_ft_shift,
                    np.int32(-k_px[i, 0]), np.int32(-k_px[i, 1]),
                    np.int32(n_hr),
                    grid=grid_total, block=(_BLOCK_SIZE, 1, 1))

                self._fft_inverse(self.d_ft, self.d_obj)

            avg_err = total_err / max(n_active, 1)
            errors.append(avg_err)
            
            if use_denoising and (iteration + 1) % 5 == 0 and tv_weight > 0:
                obj_current = self.d_obj.get()
                obj_current = apply_tv_regularization(obj_current, tv_weight)
                self.d_obj.set(obj_current.astype(np.complex64))

            if iteration > 0:
                change = abs(prev_error - avg_err) / (abs(prev_error) + 1e-12)
                if change < cfg.convergence_tol:
                    print(f"  Converged at iteration {iteration+1} "
                          f"(error change={change:.2e})")
                    break

            prev_error = avg_err
            if (iteration + 1) % 20 == 0:
                print(f"  Iter {iteration+1:4d} | NRMSE = {avg_err:.6e}")

        obj_final = self.d_obj.get()
        return obj_final, errors

    def cleanup(self):
        if CUDA_CONTEXT is not None:
            CUDA_CONTEXT.pop()


# ---------------------------------------------------------------------------
# Real-time convergence monitor
# ---------------------------------------------------------------------------
class ConvergenceMonitor:
    """Real-time error curve visualization during reconstruction.
    
    Displays live-updating convergence plot with:
      - Current NRMSE value
      - Error history curve (log scale)
      - Convergence rate indicator
    """

    def __init__(self, max_iterations: int, save_path: str = 'fp_convergence_live.png'):
        self.max_iterations = max_iterations
        self.save_path = save_path
        self.errors = []
        self.iterations = []
        
        self.fig, (self.ax1, self.ax2) = plt.subplots(1, 2, figsize=(14, 5))
        self.line1, = self.ax1.semilogy([], [], 'b-', linewidth=2, label='NRMSE')
        self.ax1.set_xlabel('Iteration', fontsize=12)
        self.ax1.set_ylabel('NRMSE (log scale)', fontsize=12)
        self.ax1.set_title('Real-time Convergence Monitoring', fontsize=14)
        self.ax1.grid(True, alpha=0.3, which='both')
        self.ax1.legend(fontsize=10)
        
        self.line2, = self.ax2.plot([], [], 'r-', linewidth=2, label='Error Change Rate')
        self.ax2.set_xlabel('Iteration', fontsize=12)
        self.ax2.set_ylabel('|ΔError| / Error', fontsize=12)
        self.ax2.set_title('Convergence Rate', fontsize=14)
        self.ax2.grid(True, alpha=0.3)
        self.ax2.legend(fontsize=10)
        
        self.status_text = self.fig.text(0.5, 0.02, '', ha='center', fontsize=12,
                                          bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))
        
        plt.tight_layout(rect=[0, 0.05, 1, 1])
        
    def update(self, iteration: int, error: float):
        """Update the monitor with new error value."""
        self.errors.append(error)
        self.iterations.append(iteration + 1)
        
        self.line1.set_data(self.iterations, self.errors)
        self.ax1.set_xlim(0, max(self.max_iterations, len(self.iterations) + 5))
        self.ax1.set_ylim(min(self.errors) * 0.5, max(self.errors) * 2)
        
        if len(self.errors) > 1:
            changes = [abs(self.errors[i] - self.errors[i-1]) / max(self.errors[i-1], 1e-15)
                      for i in range(1, len(self.errors))]
            self.line2.set_data(self.iterations[1:], changes)
            self.ax2.set_xlim(0, max(self.max_iterations, len(self.iterations) + 5))
            if max(changes) > 0:
                self.ax2.set_ylim(0, max(changes) * 1.2)
        
        current_change = 0
        if len(self.errors) > 1:
            current_change = abs(self.errors[-1] - self.errors[-2]) / max(self.errors[-2], 1e-15)
        
        self.status_text.set_text(
            f'Iteration: {iteration+1}/{self.max_iterations} | '
            f'NRMSE: {error:.6e} | '
            f'Change: {current_change:.6e} | '
            f'Status: {"Converged" if current_change < 1e-5 else "Running"}'
        )
        
        self.fig.canvas.draw()
        self.fig.canvas.flush_events()
        
    def save(self):
        """Save the final convergence plot."""
        self.fig.savefig(self.save_path, dpi=150, bbox_inches='tight')
        print(f"[INFO] Real-time convergence plot saved to {self.save_path}")
        plt.close(self.fig)


# ---------------------------------------------------------------------------
# Visualization
# ---------------------------------------------------------------------------
def visualize_results(cfg: FPConfig, gt_obj: np.ndarray,
                      recon_obj: np.ndarray, errors: List[float],
                      recon_time: float, mode: str):
    fig, axes = plt.subplots(2, 4, figsize=(18, 8))

    ax = axes[0, 0]
    ax.imshow(np.abs(gt_obj), cmap='gray', origin='lower')
    ax.set_title('Ground Truth Amplitude', fontsize=10)
    ax.axis('off')

    ax = axes[1, 0]
    ax.imshow(np.angle(gt_obj), cmap='RdBu_r', origin='lower',
              vmin=-np.pi, vmax=np.pi)
    ax.set_title('Ground Truth Phase', fontsize=10)
    ax.axis('off')

    ax = axes[0, 1]
    ax.imshow(np.abs(recon_obj), cmap='gray', origin='lower')
    ax.set_title(f'Reconstructed Amplitude ({mode})', fontsize=10)
    ax.axis('off')

    ax = axes[1, 1]
    ax.imshow(np.angle(recon_obj), cmap='RdBu_r', origin='lower',
              vmin=-np.pi, vmax=np.pi)
    ax.set_title(f'Reconstructed Phase ({mode})', fontsize=10)
    ax.axis('off')

    ax = axes[0, 2]
    amp_err = np.abs(np.abs(gt_obj) - np.abs(recon_obj))
    ax.imshow(amp_err, cmap='hot', origin='lower')
    ax.set_title(f'|Amp Error| NRMSE={nrmse(np.abs(recon_obj), np.abs(gt_obj)):.4f}',
                 fontsize=9)
    ax.axis('off')

    ax = axes[1, 2]
    phase_err = np.abs(np.angle(gt_obj) - np.angle(recon_obj))
    ax.imshow(phase_err, cmap='hot', origin='lower')
    ax.set_title(f'|Phase Error| NRMSE={nrmse(np.angle(recon_obj), np.angle(gt_obj)):.4f}',
                 fontsize=9)
    ax.axis('off')

    ax = axes[0, 3]
    if len(errors) > 1:
        ax.semilogy(range(1, len(errors) + 1), errors, 'b-', linewidth=1.5)
    else:
        ax.plot(range(1, len(errors) + 1), errors, 'b-', linewidth=1.5)
    ax.set_xlabel('Iteration', fontsize=10)
    ax.set_ylabel('NRMSE', fontsize=10)
    ax.set_title(f'Convergence Curve ({mode}, {recon_time:.1f}s)', fontsize=10)
    ax.grid(True, alpha=0.3)

    ax = axes[1, 3]
    ax.axis('off')
    info_text = (
        f"System Parameters\n"
        f"  Wavelength: {cfg.wavelength*1e6:.2f} um\n"
        f"  Objective NA: {cfg.na_objective}\n"
        f"  Illumination NA: {cfg.na_illumination}\n"
        f"  Low-res ROI: {cfg.low_res_roi} px\n"
        f"  High-res: {cfg.high_res_size} px\n"
        f"  LEDs: {cfg.num_leds_x}x{cfg.num_leds_y}\n"
        f"  Upsampling: {cfg.upsampling_factor}x\n"
        f"  Pupil radius: {cfg.pupil_radius_px:.1f} px\n\n"
        f"Results ({mode})\n"
        f"  Time: {recon_time:.2f} s\n"
        f"  Iterations: {len(errors)}\n"
        f"  Final error: {errors[-1]:.6e}\n"
        f"  Amp NRMSE: {nrmse(np.abs(recon_obj), np.abs(gt_obj)):.4f}\n"
        f"  Phase NRMSE: {nrmse(np.angle(recon_obj), np.angle(gt_obj)):.4f}"
    )
    ax.text(0.05, 0.95, info_text, transform=ax.transAxes,
            fontsize=7.5, verticalalignment='top', fontfamily='monospace',
            bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))

    plt.tight_layout()
    fname = f'fp_reconstruction_{mode.lower()}.png'
    plt.savefig(fname, dpi=150, bbox_inches='tight')
    print(f"[INFO] Results saved to {fname}")
    plt.close()

def visualize_inputs(cfg: FPConfig, measurements: np.ndarray):
    n_led = cfg.total_leds
    n_cols = min(n_led, 7)
    n_rows = (n_led + n_cols - 1) // n_cols

    fig, axes = plt.subplots(n_rows, n_cols, figsize=(3 * n_cols, 3 * n_rows))
    if n_rows == 1:
        axes = axes[None, :]

    for idx in range(n_led):
        r, c = divmod(idx, n_cols)
        ax = axes[r, c]
        ax.imshow(np.sqrt(measurements[idx]), cmap='gray', origin='lower')
        ax.set_title(f'LED {idx}', fontsize=8)
        ax.axis('off')

    for idx in range(n_led, n_rows * n_cols):
        r, c = divmod(idx, n_cols)
        axes[r, c].axis('off')

    plt.suptitle('Low-Resolution Intensity Measurements (√intensity)', fontsize=12)
    plt.tight_layout()
    plt.savefig('fp_input_measurements.png', dpi=150, bbox_inches='tight')
    print("[INFO] Input measurements saved to fp_input_measurements.png")
    plt.close()

def visualize_led_array(cfg: FPConfig, k_vecs: np.ndarray):
    fig, ax = plt.subplots(1, 1, figsize=(7, 6))
    colors = plt.cm.viridis(np.linspace(0, 1, cfg.total_leds))

    for i in range(cfg.total_leds):
        ax.scatter(k_vecs[i, 0], k_vecs[i, 1], c=colors[i], s=80,
                   edgecolors='black', linewidth=0.5, zorder=5)
        ax.annotate(str(i), (k_vecs[i, 0], k_vecs[i, 1]),
                    fontsize=6, ha='center', va='center', zorder=6)

    pupil_rad = cfg.k0 * cfg.na_objective
    circle = plt.Circle((0, 0), pupil_rad, fill=False, linestyle='--',
                         color='red', linewidth=2, label='Objective Pupil')
    ax.add_patch(circle)

    max_kx = np.max(np.abs(k_vecs[:, 0]))
    max_ky = np.max(np.abs(k_vecs[:, 1]))
    max_k = max(max_kx, max_ky) * 1.2
    ax.set_xlim(-max_k, max_k)
    ax.set_ylim(-max_k, max_k)
    ax.set_aspect('equal')
    ax.set_xlabel('kx (rad/m)', fontsize=11)
    ax.set_ylabel('ky (rad/m)', fontsize=11)
    ax.set_title('LED Illumination Wavevectors + Objective Pupil', fontsize=12)
    ax.legend(loc='upper right', fontsize=9)
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig('fp_led_wavevectors.png', dpi=150, bbox_inches='tight')
    print("[INFO] LED wavevectors saved to fp_led_wavevectors.png")
    plt.close()


# ---------------------------------------------------------------------------
# Parameter auto-tuning (grid search)
# ---------------------------------------------------------------------------
@dataclass
class SearchParam:
    name: str
    values: List[Any]


def grid_search(cfg_base: FPConfig, measurements: np.ndarray,
                k_px: np.ndarray, gt_obj: np.ndarray,
                param_grid: List[SearchParam],
                metric: str = 'amp_nrmse',
                max_iter_per_search: int = 30
                ) -> Tuple[dict, List[dict]]:
    """
    Grid search for optimal FP reconstruction parameters.
    
    Args:
        cfg_base: Base configuration
        measurements: Low-resolution intensity measurements
        k_px: LED wavevectors in pixel units
        gt_obj: Ground truth complex object (for metric calculation)
        param_grid: List of parameters to search
        metric: Metric to optimize ('amp_nrmse', 'amp_psnr', 'amp_ssim', etc.)
        max_iter_per_search: Max iterations per search run
    
    Returns:
        best_params: Dictionary of best parameter values
        all_results: List of all search results with metrics
    """
    from itertools import product
    
    param_names = [p.name for p in param_grid]
    param_values = [p.values for p in param_grid]
    
    all_results = []
    best_score = float('inf') if 'nrmse' in metric else -float('inf')
    best_params = {}
    
    cfg_search = FPConfig()
    for key, value in cfg_base.__dict__.items():
        setattr(cfg_search, key, value)
    cfg_search.max_iterations = max_iter_per_search
    
    total_runs = np.prod([len(v) for v in param_values])
    print(f"\n[Grid Search] Starting parameter search ({total_runs} runs)...")
    print(f"  Optimizing for: {metric}")
    
    for run_idx, values in enumerate(product(*param_values)):
        for name, val in zip(param_names, values):
            setattr(cfg_search, name, val)
        
        print(f"  Run {run_idx+1}/{total_runs}: "
              f"{', '.join([f'{n}={v}' for n, v in zip(param_names, values)])}")
        
        try:
            recon, errs = fp_reconstruct_cpu(
                cfg_search, measurements, k_px,
                use_orthogonal_init=True,
                real_time_monitor=False
            )
            
            metrics = compute_reconstruction_metrics(recon, gt_obj)
            metrics['final_error'] = errs[-1] if len(errs) > 0 else float('nan')
            metrics['n_iterations'] = len(errs)
            
            for name, val in zip(param_names, values):
                metrics[f'param_{name}'] = val
            
            all_results.append(metrics)
            
            current_score = metrics[metric]
            if 'nrmse' in metric:
                if current_score < best_score:
                    best_score = current_score
                    best_params = {name: val for name, val in zip(param_names, values)}
            else:
                if current_score > best_score:
                    best_score = current_score
                    best_params = {name: val for name, val in zip(param_names, values)}
            
            print(f"    {metric}: {current_score:.6f} | Best: {best_score:.6f}")
            
        except Exception as e:
            print(f"    FAILED: {e}")
    
    print(f"\n[Grid Search] Complete!")
    print(f"  Best parameters: {best_params}")
    print(f"  Best {metric}: {best_score:.6f}")
    
    return best_params, all_results


def default_param_grid() -> List[SearchParam]:
    """Default parameter search grid for FP reconstruction."""
    return [
        SearchParam('step_size', [0.5, 0.8, 1.0]),
        SearchParam('tv_reg_weight', [0.0, 1e-5, 1e-4, 1e-3]),
        SearchParam('use_denoising', [True, False]),
    ]


def visualize_grid_search(results: List[dict], best_params: dict,
                          metric: str = 'amp_nrmse',
                          save_path: str = 'fp_grid_search.png'):
    """Visualize grid search results."""
    if not results:
        return
    
    param_keys = [k for k in results[0].keys() if k.startswith('param_')]
    n_params = len(param_keys)
    
    if n_params == 0:
        return
    
    fig, axes = plt.subplots(1, n_params, figsize=(5 * n_params, 4))
    if n_params == 1:
        axes = [axes]
    
    for idx, pkey in enumerate(param_keys):
        ax = axes[idx]
        pname = pkey.replace('param_', '')
        
        unique_vals = sorted(set([r[pkey] for r in results]))
        means = []
        stds = []
        
        for val in unique_vals:
            scores = [r[metric] for r in results if r[pkey] == val]
            means.append(np.mean(scores))
            stds.append(np.std(scores))
        
        x_pos = np.arange(len(unique_vals))
        ax.bar(x_pos, means, yerr=stds, alpha=0.7, capsize=5, color='steelblue')
        ax.set_xticks(x_pos)
        ax.set_xticklabels([str(v) for v in unique_vals], rotation=45, ha='right')
        ax.set_xlabel(pname, fontsize=11)
        ax.set_ylabel(metric, fontsize=11)
        ax.set_title(f'{metric} vs {pname}', fontsize=12)
        ax.grid(True, alpha=0.3, axis='y')
    
    plt.tight_layout()
    plt.savefig(save_path, dpi=150, bbox_inches='tight')
    print(f"[INFO] Grid search visualization saved to {save_path}")
    plt.close()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    print("=" * 60)
    print("  Fourier Ptychography (FP) Reconstruction")
    print("  Alternating Projection + Multi-Angle Illumination")
    print("=" * 60)

    cfg = FPConfig()
    cfg.max_iterations = 50
    print(f"\n[System Configuration]")
    print(f"  Wavelength:        {cfg.wavelength*1e6:.2f} um")
    print(f"  Objective NA:      {cfg.na_objective}")
    print(f"  Illumination NA:   {cfg.na_illumination}")
    print(f"  Pixel size:        {cfg.pixel_size*1e6:.1f} um")
    print(f"  Magnification:     {cfg.magnification}x")
    print(f"  Low-res ROI:       {cfg.low_res_roi} px")
    print(f"  High-res size:     {cfg.high_res_size} px")
    print(f"  LED array:         {cfg.num_leds_x}x{cfg.num_leds_y} "
          f"= {cfg.total_leds} LEDs")
    print(f"  LED pitch:         {cfg.led_pitch*1e3:.2f} mm")
    print(f"  LED distance:      {cfg.led_distance*1e3:.1f} mm")
    print(f"  Pupil radius:      {cfg.pupil_radius_px:.1f} px")
    print(f"  Max iterations:    {cfg.max_iterations}")
    print(f"  Convergence tol:   {cfg.convergence_tol}")
    print(f"  Step size:         {cfg.step_size}")
    print(f"  GPU available:     {PYCUDA_AVAILABLE}")
    print(f"  Denoising:         {cfg.use_denoising}")
    print(f"  TV reg weight:     {cfg.tv_reg_weight}")
    print(f"  Init method:       Orthogonal spectrum stitching")

    noise_level = 0.05
    run_grid_search = False

    # ---- Step 1: Generate ground truth phantom ----
    print("\n[1/6] Generating synthetic complex amplitude phantom...")
    gt_obj = generate_phantom(cfg)
    print(f"  Ground truth shape: {gt_obj.shape}, dtype: {gt_obj.dtype}")

    # ---- Step 2: Compute LED wavevectors ----
    print("\n[2/6] Computing LED illumination wavevectors...")
    k_vecs = compute_led_wavevectors(cfg)
    k_px = wavevectors_to_pixels(cfg, k_vecs)
    kx_range = (k_vecs[:, 0].min(), k_vecs[:, 0].max())
    ky_range = (k_vecs[:, 1].min(), k_vecs[:, 1].max())
    print(f"  kx range: [{kx_range[0]:.3e}, {kx_range[1]:.3e}] rad/m")
    print(f"  ky range: [{ky_range[0]:.3e}, {ky_range[1]:.3e}] rad/m")
    print(f"  Pupil k-radius: {cfg.k0 * cfg.na_objective:.3e} rad/m")

    visualize_led_array(cfg, k_vecs)

    # ---- Step 3: Simulate measurements with noise ----
    print("\n[3/6] Simulating low-resolution intensity measurements...")
    t0 = time.time()
    measurements_clean = simulate_fp_measurement(cfg, gt_obj, k_px)
    t_sim = time.time() - t0
    print(f"  Clean measurements shape: {measurements_clean.shape}")
    print(f"  Simulation time: {t_sim:.3f} s")

    noise = np.random.normal(0, noise_level, measurements_clean.shape)
    measurements = np.maximum(measurements_clean + noise, 0)
    peak_signal = np.max(measurements_clean)
    noise_power = np.mean(noise**2)
    input_snr = 10 * np.log10(peak_signal**2 / noise_power) if noise_power > 0 else 100.0
    print(f"  Added noise level: {noise_level*100:.1f}%")
    print(f"  Input SNR: {input_snr:.2f} dB")

    visualize_inputs(cfg, measurements)

    # ---- Step 4: Optional parameter grid search ----
    best_params = None
    if run_grid_search:
        print("\n[4/6] Parameter Grid Search...")
        param_grid = default_param_grid()
        best_params, all_results = grid_search(
            cfg, measurements, k_px, gt_obj,
            param_grid=param_grid,
            metric='amp_nrmse',
            max_iter_per_search=20
        )
        visualize_grid_search(all_results, best_params, metric='amp_nrmse')

        for key, val in best_params.items():
            setattr(cfg, key, val)
        print(f"  Updated cfg with best parameters: {best_params}")
    else:
        print("\n[4/6] Parameter Grid Search: SKIPPED")

    # ---- Step 5: CPU Reconstruction with denoising ----
    print("\n[5/6] CPU Reconstruction (alternating projection)...")
    print(f"  Initialization: Orthogonal spectrum stitching")
    print(f"  Denoising: {cfg.use_denoising} | TV reg: {cfg.tv_reg_weight}")
    
    if cfg.use_denoising:
        print("  Pre-denoising measurements (median + Wiener filter)...")
        measurements_denoised = denoise_measurements(measurements, cfg)
    else:
        measurements_denoised = measurements
    
    t0 = time.time()
    recon_cpu, errors_cpu = fp_reconstruct_cpu(
        cfg, measurements_denoised, k_px,
        use_orthogonal_init=True,
        real_time_monitor=False
    )
    t_cpu = time.time() - t0
    
    metrics = compute_reconstruction_metrics(recon_cpu, gt_obj)
    
    print(f"  CPU reconstruction time: {t_cpu:.2f} s")
    print(f"  Final measurement NRMSE: {errors_cpu[-1]:.6e}")
    print(f"\n  [Quality Metrics vs Ground Truth]")
    print(f"  Amplitude:")
    print(f"    NRMSE: {metrics['amp_nrmse']:.4f}")
    print(f"    PSNR:  {metrics['amp_psnr']:.2f} dB")
    print(f"    SSIM:  {metrics['amp_ssim']:.4f}")
    print(f"  Phase:")
    print(f"    NRMSE: {metrics['phase_nrmse']:.4f}")
    print(f"    PSNR:  {metrics['phase_psnr']:.2f} dB")
    print(f"    SSIM:  {metrics['phase_ssim']:.4f}")

    visualize_results(cfg, gt_obj, recon_cpu, errors_cpu, t_cpu, "CPU")

    # ---- Step 6: GPU Reconstruction (if available) ----
    if PYCUDA_AVAILABLE:
        print("\n[6/6] GPU Reconstruction (PyCUDA + scikit-cuda)...")
        try:
            gpu_engine = GPURecoEngine(cfg)
            t0 = time.time()
            recon_gpu, errors_gpu = gpu_engine.reconstruct(
                measurements_denoised, k_px,
                use_denoising=cfg.use_denoising,
                tv_reg_weight=cfg.tv_reg_weight
            )
            t_gpu = time.time() - t0
            
            metrics_gpu = compute_reconstruction_metrics(recon_gpu, gt_obj)
            
            print(f"  GPU reconstruction time: {t_gpu:.2f} s")
            if t_gpu > 0:
                print(f"  Speedup vs CPU: {t_cpu / t_gpu:.1f}x")
            print(f"  Final measurement NRMSE: {errors_gpu[-1]:.6e}")
            print(f"\n  [GPU Quality Metrics vs Ground Truth]")
            print(f"  Amplitude:")
            print(f"    NRMSE: {metrics_gpu['amp_nrmse']:.4f}")
            print(f"    PSNR:  {metrics_gpu['amp_psnr']:.2f} dB")
            print(f"    SSIM:  {metrics_gpu['amp_ssim']:.4f}")
            print(f"  Phase:")
            print(f"    NRMSE: {metrics_gpu['phase_nrmse']:.4f}")
            print(f"    PSNR:  {metrics_gpu['phase_psnr']:.2f} dB")
            print(f"    SSIM:  {metrics_gpu['phase_ssim']:.4f}")

            visualize_results(cfg, gt_obj, recon_gpu, errors_gpu, t_gpu, "GPU")
            gpu_engine.cleanup()
        except Exception as e:
            print(f"  GPU reconstruction failed: {e}")
            import traceback
            traceback.print_exc()
            print("  Skipping GPU path.")
    else:
        print("\n[6/6] GPU Reconstruction: SKIPPED")
        print("  Install PyCUDA + scikit-cuda to enable GPU acceleration.")
        print("  CPU path completed successfully.")

    print("\n" + "=" * 60)
    print("  Reconstruction complete.")
    print("  Output files:")
    print("    - fp_led_wavevectors.png")
    print("    - fp_input_measurements.png")
    print("    - fp_reconstruction_cpu.png")
    if PYCUDA_AVAILABLE:
        print("    - fp_reconstruction_gpu.png")
    if run_grid_search:
        print("    - fp_grid_search.png")
    print("=" * 60)


if __name__ == '__main__':
    main()
