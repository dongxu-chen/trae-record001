import numpy as np
import cv2
from scipy import signal, fftpack
from scipy.ndimage import convolve, rotate
import matplotlib.pyplot as plt
import os
from typing import Tuple, Optional, List


class MotionDeblur:
    def __init__(self):
        pass

    def generate_motion_kernel(self, length: int, angle: float, size: int = None) -> np.ndarray:
        if size is None:
            size = int(np.ceil(length)) + 2
            if size % 2 == 0:
                size += 1
        
        kernel = np.zeros((size, size), dtype=np.float32)
        center = size // 2
        
        angle_rad = np.deg2rad(angle)
        dx = np.cos(angle_rad)
        dy = np.sin(angle_rad)
        
        for i in range(length):
            x = int(round(center + dx * (i - length / 2)))
            y = int(round(center + dy * (i - length / 2)))
            if 0 <= x < size and 0 <= y < size:
                kernel[y, x] = 1.0
        
        kernel /= kernel.sum()
        return kernel

    def generate_variable_motion_kernel(self, start_length: int, end_length: int, 
                                         start_angle: float, end_angle: float,
                                         size: int = None, num_segments: int = 10) -> np.ndarray:
        if size is None:
            max_len = max(start_length, end_length)
            size = int(np.ceil(max_len)) + 4
            if size % 2 == 0:
                size += 1
        
        kernel = np.zeros((size, size), dtype=np.float32)
        center = size // 2
        
        for i in range(num_segments):
            t = i / (num_segments - 1)
            length = start_length + t * (end_length - start_length)
            angle = start_angle + t * (end_angle - start_angle)
            
            angle_rad = np.deg2rad(angle)
            dx = np.cos(angle_rad)
            dy = np.sin(angle_rad)
            
            for j in range(int(length) // num_segments + 1):
                pos = (length / 2) * (2 * t - 1)
                x = int(round(center + dx * pos))
                y = int(round(center + dy * pos))
                if 0 <= x < size and 0 <= y < size:
                    kernel[y, x] += 1.0
        
        if kernel.sum() > 0:
            kernel /= kernel.sum()
        return kernel

    def generate_accelerated_motion_kernel(self, init_length: int, acceleration: float, 
                                           angle: float, duration: int = 20,
                                           size: int = None) -> np.ndarray:
        if size is None:
            max_len = int(init_length + 0.5 * acceleration * duration**2)
            size = max_len + 4
            if size % 2 == 0:
                size += 1
        
        kernel = np.zeros((size, size), dtype=np.float32)
        center = size // 2
        angle_rad = np.deg2rad(angle)
        
        v = 0
        for t in range(duration):
            v += acceleration
            displacement = v * t
            
            x = int(round(center + np.cos(angle_rad) * displacement))
            y = int(round(center + np.sin(angle_rad) * displacement))
            if 0 <= x < size and 0 <= y < size:
                kernel[y, x] += max(0.1, v)
        
        if kernel.sum() > 0:
            kernel /= kernel.sum()
        return kernel

    def generate_rotation_motion_kernel(self, max_radius: int, start_angle: float, 
                                         end_angle: float, center_offset: Tuple[int, int] = (0, 0),
                                         size: int = None) -> np.ndarray:
        if size is None:
            size = 2 * max_radius + 5
            if size % 2 == 0:
                size += 1
        
        kernel = np.zeros((size, size), dtype=np.float32)
        center = (size // 2 + center_offset[0], size // 2 + center_offset[1])
        
        num_steps = int(abs(end_angle - start_angle) * 2) + 10
        for i in range(num_steps):
            t = i / max(1, num_steps - 1)
            angle = start_angle + t * (end_angle - start_angle)
            angle_rad = np.deg2rad(angle)
            
            for r in range(1, max_radius):
                x = int(round(center[0] + r * np.cos(angle_rad)))
                y = int(round(center[1] + r * np.sin(angle_rad)))
                if 0 <= x < size and 0 <= y < size:
                    kernel[y, x] += 1.0 / r
        
        if kernel.sum() > 0:
            kernel /= kernel.sum()
        return kernel

    def apply_spatially_varying_blur(self, image: np.ndarray, 
                                      kernel_map: np.ndarray) -> np.ndarray:
        h, w = image.shape[:2]
        num_kernels = kernel_map.shape[0]
        grid_h = int(np.sqrt(num_kernels))
        grid_w = num_kernels // grid_h
        
        patch_h = h // grid_h
        patch_w = w // grid_w
        
        result = np.zeros_like(image, dtype=np.float32)
        weight_map = np.zeros((h, w), dtype=np.float32)
        
        k_idx = 0
        for i in range(grid_h):
            for j in range(grid_w):
                y_start = i * patch_h
                y_end = min((i + 1) * patch_h, h)
                x_start = j * patch_w
                x_end = min((j + 1) * patch_w, w)
                
                kernel = kernel_map[k_idx]
                kh, kw = kernel.shape
                
                pad_top = kh // 2
                pad_bottom = kh - pad_top
                pad_left = kw // 2
                pad_right = kw - pad_left
                
                if len(image.shape) == 3:
                    for c in range(3):
                        patch = image[y_start:y_end, x_start:x_end, c].astype(np.float32)
                        padded = np.pad(patch, ((pad_top, pad_bottom), (pad_left, pad_right)), mode='reflect')
                        blurred = convolve(padded, kernel)
                        result[y_start:y_end, x_start:x_end, c] += blurred[pad_top:pad_top+(y_end-y_start), 
                                                                           pad_left:pad_left+(x_end-x_start)]
                else:
                    patch = image[y_start:y_end, x_start:x_end].astype(np.float32)
                    padded = np.pad(patch, ((pad_top, pad_bottom), (pad_left, pad_right)), mode='reflect')
                    blurred = convolve(padded, kernel)
                    result[y_start:y_end, x_start:x_end] += blurred[pad_top:pad_top+(y_end-y_start), 
                                                                     pad_left:pad_left+(x_end-x_start)]
                
                weight_map[y_start:y_end, x_start:x_end] += 1.0
                k_idx += 1
        
        weight_map[weight_map == 0] = 1.0
        if len(image.shape) == 3:
            result /= weight_map[:, :, np.newaxis]
        else:
            result /= weight_map
        
        return np.clip(result, 0, 255).astype(np.uint8)

    def generate_piecewise_linear_kernels(self, image_shape: Tuple[int, int],
                                          params_list: List[Tuple[int, float]],
                                          grid_size: Tuple[int, int] = (2, 2)) -> np.ndarray:
        h, w = image_shape[:2]
        grid_h, grid_w = grid_size
        num_kernels = grid_h * grid_w
        
        kernels = []
        for i in range(grid_h):
            for j in range(grid_w):
                t_i = i / max(1, grid_h - 1)
                t_j = j / max(1, grid_w - 1)
                t = (t_i + t_j) / 2
                
                if len(params_list) >= 2:
                    idx = int(t * (len(params_list) - 1))
                    idx = min(idx, len(params_list) - 2)
                    t_local = t * (len(params_list) - 1) - idx
                    
                    length = params_list[idx][0] + t_local * (params_list[idx+1][0] - params_list[idx][0])
                    angle = params_list[idx][1] + t_local * (params_list[idx+1][1] - params_list[idx][1])
                else:
                    length, angle = params_list[0]
                
                kernel = self.generate_motion_kernel(int(length), angle)
                kernels.append(kernel)
        
        max_kh = max(k.shape[0] for k in kernels)
        max_kw = max(k.shape[1] for k in kernels)
        
        kernel_map = np.zeros((num_kernels, max_kh, max_kw), dtype=np.float32)
        for i, k in enumerate(kernels):
            kh, kw = k.shape
            pad_h1 = (max_kh - kh) // 2
            pad_h2 = max_kh - kh - pad_h1
            pad_w1 = (max_kw - kw) // 2
            pad_w2 = max_kw - kw - pad_w1
            kernel_map[i] = np.pad(k, ((pad_h1, pad_h2), (pad_w1, pad_w2)), mode='constant')
        
        return kernel_map

    def deblur_spatially_varying(self, image: np.ndarray, 
                                  kernel_map: np.ndarray,
                                  method: str = 'wiener',
                                  grid_size: Tuple[int, int] = (2, 2)) -> np.ndarray:
        h, w = image.shape[:2]
        grid_h, grid_w = grid_size
        patch_h = h // grid_h
        patch_w = w // grid_w
        
        result = np.zeros_like(image, dtype=np.float32)
        weight_map = np.zeros((h, w), dtype=np.float32)
        
        k_idx = 0
        for i in range(grid_h):
            for j in range(grid_w):
                y_start = max(0, i * patch_h - 10)
                y_end = min(h, (i + 1) * patch_h + 10)
                x_start = max(0, j * patch_w - 10)
                x_end = min(w, (j + 1) * patch_w + 10)
                
                kernel = kernel_map[k_idx]
                
                if len(image.shape) == 3:
                    patch_result = np.zeros((y_end-y_start, x_end-x_start, 3), dtype=np.float32)
                    for c in range(3):
                        patch = image[y_start:y_end, x_start:x_end, c]
                        if method == 'wiener':
                            patch_result[:, :, c] = self._wiener_deblur_channel(patch, kernel, 0.01)
                        else:
                            patch_result[:, :, c] = self._rl_deblur_channel(patch, kernel, 20)
                else:
                    patch = image[y_start:y_end, x_start:x_end]
                    if method == 'wiener':
                        patch_result = self._wiener_deblur_channel(patch, kernel, 0.01)
                    else:
                        patch_result = self._rl_deblur_channel(patch, kernel, 20)
                
                inner_y0 = i * patch_h - y_start
                inner_y1 = (i + 1) * patch_h - y_start
                inner_x0 = j * patch_w - x_start
                inner_x1 = (j + 1) * patch_w - x_start
                
                out_y0 = i * patch_h
                out_y1 = min((i + 1) * patch_h, h)
                out_x0 = j * patch_w
                out_x1 = min((j + 1) * patch_w, w)
                
                window_y = np.hanning(out_y1 - out_y0)
                window_x = np.hanning(out_x1 - out_x0)
                window_2d = np.outer(window_y, window_x).astype(np.float32)
                window_2d /= window_2d.max()
                
                if len(image.shape) == 3:
                    patch_inner = patch_result[inner_y0:inner_y1, inner_x0:inner_x1]
                    result[out_y0:out_y1, out_x0:out_x1] += patch_inner * window_2d[:, :, np.newaxis]
                else:
                    patch_inner = patch_result[inner_y0:inner_y1, inner_x0:inner_x1]
                    result[out_y0:out_y1, out_x0:out_x1] += patch_inner * window_2d
                
                weight_map[out_y0:out_y1, out_x0:out_x1] += window_2d
                k_idx += 1
        
        weight_map[weight_map == 0] = 1.0
        if len(image.shape) == 3:
            result /= weight_map[:, :, np.newaxis]
        else:
            result /= weight_map
        
        return np.clip(result, 0, 255).astype(np.uint8)

    def apply_motion_blur(self, image: np.ndarray, kernel: np.ndarray) -> np.ndarray:
        if len(image.shape) == 3:
            result = np.zeros_like(image, dtype=np.float32)
            for i in range(3):
                result[:, :, i] = convolve(image[:, :, i].astype(np.float32), kernel)
            return np.clip(result, 0, 255).astype(np.uint8)
        else:
            result = convolve(image.astype(np.float32), kernel)
            return np.clip(result, 0, 255).astype(np.uint8)

    def estimate_noise_autocorrelation(self, image: np.ndarray, kernel: np.ndarray) -> float:
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image.copy()
        
        gray_float = gray.astype(np.float32)
        h, w = gray_float.shape
        kh, kw = kernel.shape
        
        pad_h = h + kh - 1
        pad_w = w + kw - 1
        
        kernel_padded = np.zeros((pad_h, pad_w), dtype=np.float32)
        kernel_padded[:kh, :kw] = kernel
        kernel_padded = fftpack.ifftshift(kernel_padded)
        
        kernel_fft = fftpack.fft2(kernel_padded)
        h_conj_sq = np.abs(kernel_fft) ** 2
        
        image_padded = np.zeros((pad_h, pad_w), dtype=np.float32)
        image_padded[:h, :w] = gray_float
        image_fft = fftpack.fft2(image_padded)
        image_power = np.abs(image_fft) ** 2
        
        image_ac = np.real(fftpack.ifft2(image_power))
        image_ac = fftpack.fftshift(image_ac)
        
        center_y, center_x = pad_h // 2, pad_w // 2
        
        corner_size = min(32, h // 4, w // 4)
        if corner_size < 4:
            return 0.01
        
        corners = [
            image_ac[:corner_size, :corner_size],
            image_ac[:corner_size, -corner_size:],
            image_ac[-corner_size:, :corner_size],
            image_ac[-corner_size:, -corner_size:]
        ]
        
        corner_values = []
        for corner in corners:
            corner_values.extend(corner.flatten())
        corner_values = np.array(corner_values)
        
        noise_power_est = np.median(np.abs(corner_values))
        signal_power_est = np.mean(image_power)
        
        noise_power_est *= signal_power_est / (np.mean(np.abs(image_ac)) + 1e-10)
        
        K_est = noise_power_est / (signal_power_est + 1e-10)
        K_est = np.clip(K_est, 1e-4, 0.1)
        
        return float(K_est)

    def wiener_deblur(self, image: np.ndarray, kernel: np.ndarray, K: float = None) -> np.ndarray:
        if K is None:
            K = self.estimate_noise_autocorrelation(image, kernel)
        
        if len(image.shape) == 3:
            result = np.zeros_like(image, dtype=np.float32)
            for i in range(3):
                result[:, :, i] = self._wiener_deblur_channel(image[:, :, i], kernel, K)
            return np.clip(result, 0, 255).astype(np.uint8)
        else:
            result = self._wiener_deblur_channel(image, kernel, K)
            return np.clip(result, 0, 255).astype(np.uint8)

    def _wiener_deblur_channel(self, image: np.ndarray, kernel: np.ndarray, K: float) -> np.ndarray:
        h, w = image.shape
        kh, kw = kernel.shape
        
        pad_h = h + kh - 1
        pad_w = w + kw - 1
        
        image_padded = np.zeros((pad_h, pad_w), dtype=np.float32)
        image_padded[:h, :w] = image.astype(np.float32)
        
        kernel_padded = np.zeros((pad_h, pad_w), dtype=np.float32)
        kernel_padded[:kh, :kw] = kernel
        kernel_padded = fftpack.ifftshift(kernel_padded)
        
        image_fft = fftpack.fft2(image_padded)
        kernel_fft = fftpack.fft2(kernel_padded)
        
        kernel_abs = np.abs(kernel_fft) ** 2
        wiener_filter = np.conj(kernel_fft) / (kernel_abs + K)
        
        result_fft = image_fft * wiener_filter
        result = np.real(fftpack.ifft2(result_fft))
        
        return result[:h, :w]

    def richardson_lucy_deblur(self, image: np.ndarray, kernel: np.ndarray, 
                                iterations: int = 50) -> np.ndarray:
        if len(image.shape) == 3:
            result = np.zeros_like(image, dtype=np.float32)
            for i in range(3):
                result[:, :, i] = self._rl_deblur_channel(image[:, :, i], kernel, iterations)
            return np.clip(result, 0, 255).astype(np.uint8)
        else:
            result = self._rl_deblur_channel(image, kernel, iterations)
            return np.clip(result, 0, 255).astype(np.uint8)

    def _rl_deblur_channel(self, image: np.ndarray, kernel: np.ndarray, 
                           iterations: int) -> np.ndarray:
        image_float = image.astype(np.float32) / 255.0
        estimate = np.full_like(image_float, 0.5)
        
        kernel_flip = np.flipud(np.fliplr(kernel))
        
        for _ in range(iterations):
            est_conv = convolve(estimate, kernel)
            relative_blur = image_float / (est_conv + 1e-10)
            error_est = convolve(relative_blur, kernel_flip)
            estimate *= error_est
        
        return estimate * 255.0

    def _initialize_blind_kernel(self, image: np.ndarray, kernel_size: int) -> np.ndarray:
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image.copy()
        
        try:
            est_length, est_angle = self.estimate_motion_parameters(image)
            est_length = max(3, min(est_length, kernel_size - 2))
            kernel = self.generate_motion_kernel(int(est_length), est_angle, size=kernel_size)
            return kernel
        except Exception:
            kernel = np.zeros((kernel_size, kernel_size), dtype=np.float32)
            center = kernel_size // 2
            kernel[center, :] = 1.0
            kernel /= kernel.sum()
            return kernel

    def blind_deconvolution(self, image: np.ndarray, init_kernel: np.ndarray = None,
                            iterations: int = 20, kernel_size: int = 15,
                            regularization: float = 1e-4, damping: float = 0.2,
                            adaptive: bool = True,
                            early_stop: bool = True, tol: float = 1e-5) -> Tuple[np.ndarray, np.ndarray]:
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image.copy()
        
        if init_kernel is None:
            if adaptive:
                kernel = self._initialize_blind_kernel(image, kernel_size)
            else:
                kernel = np.ones((kernel_size, kernel_size), dtype=np.float32)
                kernel /= kernel.sum()
        else:
            kernel = init_kernel.copy()
        
        image_float = gray.astype(np.float32) / 255.0
        estimate = image_float.copy()
        
        prev_estimate = estimate.copy()
        prev_kernel = kernel.copy()
        
        loss_history = []
        
        for iteration in range(iterations):
            kernel_flip = np.flipud(np.fliplr(kernel))
            
            est_conv = convolve(estimate, kernel)
            relative_blur = image_float / (est_conv + 1e-10)
            error_est = convolve(relative_blur, kernel_flip)
            
            grad_image = estimate * (error_est - 1.0)
            grad_image -= regularization * estimate
            
            estimate_new = estimate + damping * grad_image
            estimate_new = np.clip(estimate_new, 1e-10, 1.0)
            
            kernel_update = signal.correlate2d(relative_blur, estimate, mode='valid')
            if kernel_update.shape[0] > kernel.shape[0] or kernel_update.shape[1] > kernel.shape[1]:
                kernel_update = kernel_update[:kernel.shape[0], :kernel.shape[1]]
            
            grad_kernel = kernel * (kernel_update - 1.0)
            grad_kernel -= regularization * kernel
            
            kernel_new = kernel + damping * grad_kernel
            kernel_new = np.clip(kernel_new, 0, None)
            
            if kernel_new.sum() > 0:
                kernel_new /= kernel_new.sum()
            
            if early_stop and iteration > 2:
                loss = np.mean((image_float - convolve(estimate, kernel))**2)
                loss_history.append(loss)
                
                if len(loss_history) >= 3:
                    loss_improvement = abs(loss_history[-2] - loss_history[-1])
                    if loss_improvement < tol * loss_history[-1]:
                        break
            
            estimate = estimate_new
            kernel = kernel_new
        
        if len(image.shape) == 3:
            result = np.zeros_like(image, dtype=np.float32)
            for i in range(3):
                result[:, :, i] = self._rl_deblur_channel(image[:, :, i], kernel, 15)
            deblurred = np.clip(result, 0, 255).astype(np.uint8)
        else:
            deblurred = np.clip(estimate * 255, 0, 255).astype(np.uint8)
        
        return deblurred, kernel

    def _radon_transform(self, image: np.ndarray, theta: np.ndarray = None) -> Tuple[np.ndarray, np.ndarray]:
        if theta is None:
            theta = np.arange(0, 180, 1.0)
        
        h, w = image.shape
        diagonal = int(np.ceil(np.sqrt(h**2 + w**2)))
        pad_h = (diagonal - h) // 2
        pad_w = (diagonal - w) // 2
        
        padded = np.zeros((diagonal, diagonal), dtype=np.float32)
        padded[pad_h:pad_h+h, pad_w:pad_w+w] = image
        
        radon_img = np.zeros((diagonal, len(theta)), dtype=np.float32)
        
        for i, angle in enumerate(theta):
            rotated = rotate(padded, -angle, reshape=False, order=1, mode='constant', cval=0)
            radon_img[:, i] = rotated.sum(axis=0)
        
        return radon_img, theta

    def estimate_motion_parameters(self, image: np.ndarray) -> Tuple[float, float]:
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image.copy()
        
        gray = cv2.GaussianBlur(gray, (3, 3), 0)
        gray_float = gray.astype(np.float32)
        
        f = fftpack.fft2(gray_float)
        fshift = fftpack.fftshift(f)
        magnitude_spectrum = np.abs(fshift)
        h, w = magnitude_spectrum.shape
        center_y, center_x = h // 2, w // 2
        mask_radius = min(h, w) // 8
        Y, X = np.ogrid[:h, :w]
        dist = np.sqrt((X - center_x)**2 + (Y - center_y)**2)
        magnitude_spectrum[dist < mask_radius] = 0
        spectrum_norm = cv2.normalize(magnitude_spectrum, None, 0, 1, cv2.NORM_MINMAX)
        
        theta_coarse = np.arange(0, 180, 1.0)
        radon_img, _ = self._radon_transform(spectrum_norm, theta_coarse)
        
        col_variance = np.var(radon_img, axis=0)
        dominant_idx = np.argmax(col_variance)
        coarse_angle = theta_coarse[dominant_idx]
        
        theta_fine = np.arange(coarse_angle - 2, coarse_angle + 2.01, 0.1)
        theta_fine = theta_fine[(theta_fine >= 0) & (theta_fine < 180)]
        if len(theta_fine) > 0:
            radon_fine, _ = self._radon_transform(spectrum_norm, theta_fine)
            col_var_fine = np.var(radon_fine, axis=0)
            fine_idx = np.argmax(col_var_fine)
            motion_angle = theta_fine[fine_idx]
        else:
            motion_angle = coarse_angle
        
        blur_angle = motion_angle + 90
        if blur_angle >= 180:
            blur_angle -= 180
        
        cepstrum = np.abs(fftpack.ifft2(np.log(np.abs(f) + 1e-10)))
        cepstrum_shift = fftpack.fftshift(cepstrum)
        
        cep_h, cep_w = cepstrum_shift.shape
        cep_center_y, cep_center_x = cep_h // 2, cep_w // 2
        
        mask_size = 5
        Y_cep, X_cep = np.ogrid[:cep_h, :cep_w]
        dist_cep = np.sqrt((X_cep - cep_center_x)**2 + (Y_cep - cep_center_y)**2)
        cepstrum_shift[dist_cep < mask_size] = 0
        
        angle_rad = np.deg2rad(blur_angle)
        max_r = min(cep_h, cep_w) // 3
        
        neg_profile = []
        pos_profile = []
        for r in range(3, max_r):
            dx = int(round(r * np.cos(angle_rad)))
            dy = int(round(r * np.sin(angle_rad)))
            
            nx = cep_center_x - dx
            ny = cep_center_y - dy
            if 0 <= nx < cep_w and 0 <= ny < cep_h:
                neg_profile.append(cepstrum_shift[ny, nx])
            
            px = cep_center_x + dx
            py = cep_center_y + dy
            if 0 <= px < cep_w and 0 <= py < cep_h:
                pos_profile.append(cepstrum_shift[py, px])
        
        estimated_length = 15.0
        
        if len(neg_profile) > 5:
            neg_profile = np.array(neg_profile)
            peaks_neg = np.where((neg_profile[1:-1] > neg_profile[:-2]) & 
                                (neg_profile[1:-1] > neg_profile[2:]))[0] + 1
            if len(peaks_neg) > 0:
                strongest_peak = peaks_neg[np.argmax(neg_profile[peaks_neg])]
                estimated_length = float(strongest_peak + 3)
                estimated_length = max(5, min(60, estimated_length))
        
        if len(pos_profile) > 5:
            pos_profile = np.array(pos_profile)
            peaks_pos = np.where((pos_profile[1:-1] > pos_profile[:-2]) & 
                                (pos_profile[1:-1] > pos_profile[2:]))[0] + 1
            if len(peaks_pos) > 0:
                strongest_peak = peaks_pos[np.argmax(pos_profile[peaks_pos])]
                length_pos = float(strongest_peak + 3)
                length_pos = max(5, min(60, length_pos))
                estimated_length = (estimated_length + length_pos) / 2
        
        return estimated_length, float(blur_angle)

    def suppress_ringing(self, image: np.ndarray, kernel: np.ndarray, 
                         method: str = 'edgetaper') -> np.ndarray:
        if method == 'edgetaper':
            return self._edge_taper(image, kernel)
        elif method == 'wiener':
            return self.wiener_deblur(image, kernel, K=0.05)
        elif method == 'bilateral':
            return self._bilateral_denoise(image, kernel)
        elif method == 'guided':
            return self._guided_filter_denoise(image, kernel)
        elif method == 'edge_preserving':
            return self._edge_preserving_filter(image, kernel)
        else:
            return image

    def _bilateral_denoise(self, image: np.ndarray, kernel: np.ndarray,
                           d: int = 9, sigma_color: float = 75, sigma_space: float = 75) -> np.ndarray:
        kh, kw = kernel.shape
        kernel_extent = max(kh, kw)
        
        sigma_space = max(sigma_space, kernel_extent * 3)
        
        if len(image.shape) == 3:
            result = cv2.bilateralFilter(image, d, sigma_color, sigma_space)
        else:
            result = cv2.bilateralFilter(image, d, sigma_color, sigma_space)
        return result

    def _guided_filter(self, I: np.ndarray, p: np.ndarray, r: int, eps: float) -> np.ndarray:
        mean_I = cv2.boxFilter(I, cv2.CV_32F, (r, r))
        mean_p = cv2.boxFilter(p, cv2.CV_32F, (r, r))
        mean_Ip = cv2.boxFilter(I * p, cv2.CV_32F, (r, r))
        var_I = cv2.boxFilter(I * I, cv2.CV_32F, (r, r)) - mean_I * mean_I
        
        cov_Ip = mean_Ip - mean_I * mean_p
        
        a = cov_Ip / (var_I + eps)
        b = mean_p - a * mean_I
        
        mean_a = cv2.boxFilter(a, cv2.CV_32F, (r, r))
        mean_b = cv2.boxFilter(b, cv2.CV_32F, (r, r))
        
        q = mean_a * I + mean_b
        return q

    def _guided_filter_denoise(self, image: np.ndarray, kernel: np.ndarray,
                               radius: int = 8, eps: float = 0.01) -> np.ndarray:
        if len(image.shape) == 3:
            result = np.zeros_like(image, dtype=np.float32)
            for i in range(3):
                channel = image[:, :, i].astype(np.float32) / 255.0
                guide = channel.copy()
                filtered = self._guided_filter(guide, channel, radius, eps)
                result[:, :, i] = np.clip(filtered * 255, 0, 255)
            return result.astype(np.uint8)
        else:
            channel = image.astype(np.float32) / 255.0
            guide = channel.copy()
            filtered = self._guided_filter(guide, channel, radius, eps)
            return np.clip(filtered * 255, 0, 255).astype(np.uint8)

    def _edge_preserving_filter(self, image: np.ndarray, kernel: np.ndarray,
                                sigma_s: float = 60, sigma_r: float = 0.4,
                                num_iterations: int = 3) -> np.ndarray:
        if len(image.shape) == 3:
            result = image.astype(np.float32)
            for _ in range(num_iterations):
                for i in range(3):
                    channel = result[:, :, i].astype(np.uint8)
                    filtered = cv2.ximgproc.dtFilter(
                        channel, channel, sigma_s, sigma_r
                    )
                    result[:, :, i] = filtered.astype(np.float32)
            return np.clip(result, 0, 255).astype(np.uint8)
        else:
            result = image.astype(np.float32)
            channel = result.astype(np.uint8)
            for _ in range(num_iterations):
                channel = cv2.ximgproc.dtFilter(channel, channel, sigma_s, sigma_r)
                result = channel.astype(np.float32)
            return np.clip(result, 0, 255).astype(np.uint8)

    def _edge_taper(self, image: np.ndarray, kernel: np.ndarray) -> np.ndarray:
        if len(image.shape) == 3:
            result = np.zeros_like(image, dtype=np.float32)
            for i in range(3):
                result[:, :, i] = self._edge_taper_channel(image[:, :, i], kernel)
            return np.clip(result, 0, 255).astype(np.uint8)
        else:
            result = self._edge_taper_channel(image, kernel)
            return np.clip(result, 0, 255).astype(np.uint8)

    def _edge_taper_channel(self, image: np.ndarray, kernel: np.ndarray) -> np.ndarray:
        h, w = image.shape
        kh, kw = kernel.shape
        
        pad_h = kh // 2
        pad_w = kw // 2
        
        image_float = image.astype(np.float32)
        
        taper_h = np.hanning(kh * 2)[:kh]
        taper_w = np.hanning(kw * 2)[:kw]
        
        taper_2d = np.outer(taper_h, taper_w)
        taper_2d = taper_2d / taper_2d.max()
        
        window = np.ones((h, w), dtype=np.float32)
        
        window[:pad_h, :pad_w] = np.minimum.outer(taper_h[:pad_h], taper_w[:pad_w])
        window[:pad_h, -pad_w:] = np.minimum.outer(taper_h[:pad_h], taper_w[-pad_w:][::-1])
        window[-pad_h:, :pad_w] = np.minimum.outer(taper_h[-pad_h:][::-1], taper_w[:pad_w])
        window[-pad_h:, -pad_w:] = np.minimum.outer(taper_h[-pad_h:][::-1], taper_w[-pad_w:][::-1])
        
        for i in range(pad_h):
            window[i, pad_w:-pad_w] = taper_h[i]
            window[-i-1, pad_w:-pad_w] = taper_h[i]
        
        for j in range(pad_w):
            window[pad_h:-pad_h, j] = taper_w[j]
            window[pad_h:-pad_h, -j-1] = taper_w[j]
        
        return image_float * window

    def batch_process(self, input_dir: str, output_dir: str, 
                      method: str = 'wiener', 
                      auto_params: bool = True,
                      length: float = 15, 
                      angle: float = 0,
                      suppress_ringing_method: str = 'edgetaper') -> List[str]:
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        supported_ext = ('.jpg', '.jpeg', '.png', '.bmp', '.tiff')
        image_files = [f for f in os.listdir(input_dir) if f.lower().endswith(supported_ext)]
        
        processed_files = []
        
        for filename in image_files:
            input_path = os.path.join(input_dir, filename)
            output_path = os.path.join(output_dir, f'deblurred_{filename}')
            
            image = cv2.imread(input_path)
            if image is None:
                continue
            
            if auto_params:
                est_length, est_angle = self.estimate_motion_parameters(image)
                kernel = self.generate_motion_kernel(int(est_length), est_angle)
            else:
                kernel = self.generate_motion_kernel(int(length), angle)
            
            if suppress_ringing_method:
                image_processed = self.suppress_ringing(image, kernel, method=suppress_ringing_method)
            else:
                image_processed = image
            
            if method == 'wiener':
                deblurred = self.wiener_deblur(image_processed, kernel)
            elif method == 'rl':
                deblurred = self.richardson_lucy_deblur(image_processed, kernel)
            elif method == 'blind':
                deblurred, _ = self.blind_deconvolution(image_processed)
            else:
                deblurred = image_processed
            
            cv2.imwrite(output_path, deblurred)
            processed_files.append(output_path)
        
        return processed_files

    def evaluate_sharpness(self, image: np.ndarray) -> float:
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image.copy()
        
        gray = gray.astype(np.float32)
        
        laplacian = cv2.Laplacian(gray, cv2.CV_32F)
        sharpness = np.var(laplacian)
        
        return float(sharpness)

    def evaluate_contrast(self, image: np.ndarray) -> float:
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image.copy()
        
        gray = gray.astype(np.float32)
        
        contrast = np.std(gray)
        
        return float(contrast)

    def evaluate_noise_level(self, image: np.ndarray) -> float:
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image.copy()
        
        gray = gray.astype(np.float32)
        
        h, w = gray.shape
        block_size = 8
        variances = []
        
        for i in range(0, h - block_size, block_size):
            for j in range(0, w - block_size, block_size):
                block = gray[i:i+block_size, j:j+block_size]
                var = np.var(block)
                variances.append(var)
        
        if len(variances) > 0:
            noise_est = np.percentile(variances, 10)
        else:
            noise_est = 0.0
        
        return float(noise_est)

    def evaluate_ringing(self, image: np.ndarray) -> float:
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image.copy()
        
        gray = gray.astype(np.float32)
        
        edges = cv2.Canny(gray.astype(np.uint8), 50, 150)
        
        f = fftpack.fft2(gray)
        fshift = fftpack.fftshift(f)
        magnitude = np.log(np.abs(fshift) + 1)
        
        h, w = magnitude.shape
        center_y, center_x = h // 2, w // 2
        
        mask_radius = min(h, w) // 8
        Y, X = np.ogrid[:h, :w]
        dist_from_center = np.sqrt((X - center_x)**2 + (Y - center_y)**2)
        
        high_freq_mask = dist_from_center > mask_radius
        
        high_freq_energy = np.sum(magnitude[high_freq_mask])
        total_energy = np.sum(magnitude)
        
        if total_energy > 0:
            ringing_score = high_freq_energy / total_energy
        else:
            ringing_score = 0.0
        
        edge_density = np.sum(edges) / (h * w)
        ringing_score = ringing_score * (1.0 + edge_density)
        
        return float(ringing_score)

    def evaluate_brisque(self, image: np.ndarray) -> float:
        try:
            if len(image.shape) == 3:
                gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            else:
                gray = image.copy()
            
            gray = gray.astype(np.uint8)
            
            model_path = 'brisque_model_live.yml'
            range_path = 'brisque_range_live.yml'
            
            if not os.path.exists(model_path) or not os.path.exists(range_path):
                return self._calculate_simple_brisque(gray)
            
            try:
                quality = cv2.quality.QualityBRISQUE_compute(image, model_path, range_path)
                return float(quality[0])
            except Exception:
                return self._calculate_simple_brisque(gray)
        except Exception:
            if len(image.shape) == 3:
                gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            else:
                gray = image.copy()
            return self._calculate_simple_brisque(gray)

    def _calculate_simple_brisque(self, gray: np.ndarray) -> float:
        gray = gray.astype(np.float32)
        
        features = []
        
        mu = cv2.GaussianBlur(gray, (7, 7), 7/6)
        sigma = np.sqrt(cv2.GaussianBlur((gray - mu)**2, (7, 7), 7/6) + 1e-10)
        
        struct_dis = (gray - mu) / (sigma + 1)
        
        alpha = np.mean(np.abs(struct_dis))
        beta = np.mean(struct_dis**2)
        
        features.append(alpha)
        features.append(beta)
        
        for scale in [2, 4]:
            scaled = cv2.resize(gray, (gray.shape[1]//scale, gray.shape[0]//scale))
            mu_s = cv2.GaussianBlur(scaled, (7, 7), 7/6)
            sigma_s = np.sqrt(cv2.GaussianBlur((scaled - mu_s)**2, (7, 7), 7/6) + 1e-10)
            struct_dis_s = (scaled - mu_s) / (sigma_s + 1)
            
            alpha_s = np.mean(np.abs(struct_dis_s))
            beta_s = np.mean(struct_dis_s**2)
            features.append(alpha_s)
            features.append(beta_s)
        
        features = np.array(features)
        
        sharpness = self.evaluate_sharpness(gray)
        noise = self.evaluate_noise_level(gray)
        
        score = 50.0
        score -= 0.1 * sharpness
        score += 0.5 * noise
        
        if beta > 1.5:
            score += 10.0
        if beta < 0.8:
            score -= 5.0
        
        return float(np.clip(score, 0, 100))

    def evaluate_niqe(self, image: np.ndarray) -> float:
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image.copy()
        
        gray = gray.astype(np.float32)
        
        patches = []
        patch_size = 32
        h, w = gray.shape
        
        for i in range(0, h - patch_size, patch_size // 2):
            for j in range(0, w - patch_size, patch_size // 2):
                patch = gray[i:i+patch_size, j:j+patch_size]
                patches.append(patch)
        
        if len(patches) == 0:
            patches = [gray]
        
        features = []
        for patch in patches:
            mu = np.mean(patch)
            sigma = np.std(patch)
            
            normalized_patch = (patch - mu) / (sigma + 1e-10)
            skewness = np.mean(normalized_patch**3)
            kurtosis = np.mean(normalized_patch**4) - 3
            
            laplacian = cv2.Laplacian(patch, cv2.CV_32F)
            lap_var = np.var(laplacian)
            
            sobelx = cv2.Sobel(patch, cv2.CV_32F, 1, 0, ksize=3)
            sobely = cv2.Sobel(patch, cv2.CV_32F, 0, 1, ksize=3)
            gradient_mag = np.sqrt(sobelx**2 + sobely**2)
            grad_mean = np.mean(gradient_mag)
            
            features.append([sigma, abs(skewness), kurtosis, lap_var, grad_mean])
        
        features = np.array(features)
        mean_features = np.median(features, axis=0)
        
        natural_mu = np.array([50, 0.3, 0.5, 500, 15])
        natural_sigma = np.array([20, 0.2, 0.5, 300, 10])
        
        normalized = np.abs(mean_features - natural_mu) / (natural_sigma + 1e-10)
        normalized = np.clip(normalized, 0, 3)
        score = np.mean(normalized)
        
        score = 20 + 20 * score
        
        return float(np.clip(score, 0, 100))

    def evaluate_overall_quality(self, image: np.ndarray) -> dict:
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image.copy()
        
        sharpness = self.evaluate_sharpness(gray)
        contrast = self.evaluate_contrast(gray)
        noise = self.evaluate_noise_level(gray)
        ringing = self.evaluate_ringing(gray)
        brisque = self.evaluate_brisque(gray)
        niqe = self.evaluate_niqe(gray)
        
        sharpness_norm = np.clip(sharpness / 1000.0, 0, 1)
        contrast_norm = np.clip(contrast / 80.0, 0, 1)
        noise_norm = np.clip(1.0 - noise / 200.0, 0, 1)
        ringing_norm = np.clip(1.0 - ringing * 10, 0, 1)
        brisque_norm = np.clip(1.0 - brisque / 100.0, 0, 1)
        niqe_norm = np.clip(1.0 - niqe / 100.0, 0, 1)
        
        weights = [0.25, 0.15, 0.2, 0.2, 0.1, 0.1]
        overall_score = (
            weights[0] * sharpness_norm +
            weights[1] * contrast_norm +
            weights[2] * noise_norm +
            weights[3] * ringing_norm +
            weights[4] * brisque_norm +
            weights[5] * niqe_norm
        ) * 100.0
        
        quality_level = 'Excellent' if overall_score >= 80 else \
                        'Good' if overall_score >= 60 else \
                        'Fair' if overall_score >= 40 else \
                        'Poor' if overall_score >= 20 else 'Bad'
        
        return {
            'sharpness': sharpness,
            'contrast': contrast,
            'noise_level': noise,
            'ringing_level': ringing,
            'brisque_score': brisque,
            'niqe_score': niqe,
            'overall_score': float(overall_score),
            'quality_level': quality_level
        }

    def visualize_results(self, original: np.ndarray, blurred: np.ndarray, 
                          deblurred: np.ndarray, kernel: np.ndarray = None,
                          save_path: str = None):
        num_plots = 3
        if kernel is not None:
            num_plots = 4
        
        fig, axes = plt.subplots(1, num_plots, figsize=(5 * num_plots, 5))
        
        if num_plots == 3:
            ax1, ax2, ax3 = axes
        else:
            ax1, ax2, ax3, ax4 = axes
        
        if len(original.shape) == 3:
            original_rgb = cv2.cvtColor(original, cv2.COLOR_BGR2RGB)
            blurred_rgb = cv2.cvtColor(blurred, cv2.COLOR_BGR2RGB)
            deblurred_rgb = cv2.cvtColor(deblurred, cv2.COLOR_BGR2RGB)
        else:
            original_rgb = original
            blurred_rgb = blurred
            deblurred_rgb = deblurred
        
        ax1.imshow(original_rgb)
        ax1.set_title('Original Image')
        ax1.axis('off')
        
        ax2.imshow(blurred_rgb)
        ax2.set_title('Blurred Image')
        ax2.axis('off')
        
        ax3.imshow(deblurred_rgb)
        ax3.set_title('Deblurred Image')
        ax3.axis('off')
        
        if kernel is not None:
            ax4.imshow(kernel, cmap='gray')
            ax4.set_title('Motion Kernel')
            ax4.axis('off')
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=150, bbox_inches='tight')
        
        plt.show()


def main():
    deblur = MotionDeblur()
    
    test_image = np.zeros((300, 400, 3), dtype=np.uint8)
    test_image[:] = [200, 200, 200]
    cv2.rectangle(test_image, (100, 100), (200, 200), (255, 0, 0), -1)
    cv2.circle(test_image, (300, 150), 50, (0, 255, 0), -1)
    cv2.putText(test_image, 'TEST', (50, 250), cv2.FONT_HERSHEY_SIMPLEX, 2, (0, 0, 255), 3)
    
    true_length = 25
    true_angle = 30
    kernel = deblur.generate_motion_kernel(length=true_length, angle=true_angle)
    
    blurred = deblur.apply_motion_blur(test_image, kernel)
    
    est_length, est_angle = deblur.estimate_motion_parameters(blurred)
    print(f"True parameters: length={true_length}, angle={true_angle}")
    print(f"Estimated parameters (Radon transform): length={est_length:.1f}, angle={est_angle:.1f}")
    
    K_auto = deblur.estimate_noise_autocorrelation(blurred, kernel)
    print(f"Auto-estimated Wiener K value: {K_auto:.4f}")
    
    deblurred_wiener_auto = deblur.wiener_deblur(blurred, kernel)
    deblurred_rl = deblur.richardson_lucy_deblur(blurred, kernel, iterations=30)
    
    deblurred_bilateral = deblur.suppress_ringing(blurred, kernel, method='bilateral')
    deblurred_guided = deblur.suppress_ringing(blurred, kernel, method='guided')
    
    print("\nDeblurring methods:")
    print("- Wiener with auto-estimated K: completed")
    print("- Richardson-Lucy: completed")
    print("- Bilateral filter ringing suppression: completed")
    print("- Guided filter ringing suppression: completed")
    
    deblur.visualize_results(test_image, blurred, deblurred_wiener_auto, kernel)
    
    print("\nAll improvements applied:")
    print("1. Radon transform for precise motion direction detection")
    print("2. Autocorrelation-based noise estimation for adaptive Wiener K")
    print("3. Edge-preserving filters (bilateral, guided) for ringing suppression")


if __name__ == "__main__":
    main()
