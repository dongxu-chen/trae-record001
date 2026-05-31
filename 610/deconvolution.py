import numpy as np
from scipy.signal import fftconvolve
from scipy.ndimage import gaussian_filter
import time


class TiledFFTConvolver:
    def __init__(self, tile_size=256, overlap=64):
        self.tile_size = tile_size
        self.overlap = overlap

    def _get_tile_coords(self, h, w):
        step = max(1, self.tile_size - self.overlap)
        tiles = []
        y = 0
        while y < h:
            x = 0
            while x < w:
                y_start = max(0, y - self.overlap // 2)
                y_end = min(h, y_start + self.tile_size)
                x_start = max(0, x - self.overlap // 2)
                x_end = min(w, x_start + self.tile_size)
                if y_end > y_start and x_end > x_start:
                    tiles.append((y_start, y_end, x_start, x_end))
                x += step
            y += step
        if not tiles:
            tiles.append((0, h, 0, w))
        return tiles

    def convolve2d_tiled(self, image, psf_spatial, tile_coords=None):
        h, w = image.shape
        if tile_coords is None:
            tile_coords = self._get_tile_coords(h, w)

        result = np.zeros((h, w), dtype=np.float64)
        weight = np.zeros((h, w), dtype=np.float64)

        for y_start, y_end, x_start, x_end in tile_coords:
            ph, pw = psf_spatial.shape
            margin_y = ph // 2
            margin_x = pw // 2

            src_y0 = max(0, y_start - margin_y)
            src_y1 = min(h, y_end + margin_y)
            src_x0 = max(0, x_start - margin_x)
            src_x1 = min(w, x_end + margin_x)

            src_tile = image[src_y0:src_y1, src_x0:src_x1]
            conv_full = fftconvolve(src_tile, psf_spatial, mode='same')

            dst_y0 = y_start - src_y0
            dst_y1 = dst_y0 + (y_end - y_start)
            dst_x0 = x_start - src_x0
            dst_x1 = dst_x0 + (x_end - x_start)
            conv_tile = conv_full[dst_y0:dst_y1, dst_x0:dst_x1]

            th = y_end - y_start
            tw = x_end - x_start
            fade_y = self._fade_window(th)
            fade_x = self._fade_window(tw)
            fade_2d = np.outer(fade_y, fade_x)

            result[y_start:y_end, x_start:x_end] += conv_tile * fade_2d
            weight[y_start:y_end, x_start:x_end] += fade_2d

        weight = np.clip(weight, 1e-10, None)
        return result / weight

    @staticmethod
    def _fade_window(size):
        ramp = min(size // 2, 64)
        window = np.ones(size)
        if ramp > 1:
            window[:ramp] = 0.5 - 0.5 * np.cos(np.pi * np.arange(ramp) / ramp)
            window[-ramp:] = 0.5 + 0.5 * np.cos(np.pi * np.arange(ramp) / ramp)
        return window


class RichardsonLucy:
    def __init__(self, psf, num_iterations=50, convergence_threshold=1e-4,
                 use_gpu=False, tile_size=256):
        self.psf = psf
        self.psf_rotated = psf[::-1, ::-1]
        self.num_iterations = num_iterations
        self.convergence_threshold = convergence_threshold
        self.use_gpu = use_gpu
        self.psf_fft = None
        self.psf_rotated_fft = None
        self.convergence_history = []
        self.actual_iterations = 0
        self.tile_size = tile_size
        self.tiled_convolver = TiledFFTConvolver(tile_size=tile_size)

    def _prepare_fft(self, image_shape):
        psf_padded = np.zeros(image_shape, dtype=np.float64)
        ph, pw = self.psf.shape
        h, w = image_shape
        start_h = (h - ph) // 2
        start_w = (w - pw) // 2
        psf_padded[start_h:start_h + ph, start_w:start_w + pw] = self.psf
        self.psf_fft = np.fft.fft2(np.fft.ifftshift(psf_padded))

        psf_rotated_padded = np.zeros(image_shape, dtype=np.float64)
        psf_rotated_padded[start_h:start_h + ph, start_w:start_w + pw] = self.psf_rotated
        self.psf_rotated_fft = np.fft.fft2(np.fft.ifftshift(psf_rotated_padded))

    def _compute_residual(self, latent, image):
        latent_fft = np.fft.fft2(latent)
        convolved = np.real(np.fft.ifft2(latent_fft * self.psf_fft))
        convolved = np.clip(convolved, 1e-10, None)
        residual = image / convolved
        return residual, convolved

    def _compute_residual_change_rate(self, residual_prev, residual_curr):
        if residual_prev is None:
            return float('inf')
        diff = np.mean(np.abs(residual_curr - residual_prev))
        baseline = np.mean(np.abs(residual_curr)) + 1e-10
        return diff / baseline

    def deconvolve(self, image, callback=None):
        image = image.astype(np.float64)
        image = np.clip(image, 1e-10, None)
        self._prepare_fft(image.shape)

        latent = np.ones_like(image) * np.mean(image)
        self.convergence_history = []
        self.actual_iterations = 0
        residual_prev = None

        for i in range(self.num_iterations):
            residual_curr, convolved = self._compute_residual(latent, image)
            change_rate = self._compute_residual_change_rate(residual_prev, residual_curr)
            self.convergence_history.append(change_rate)

            relative_blur_fft = np.fft.fft2(residual_curr)
            correction = np.real(np.fft.ifft2(relative_blur_fft * self.psf_rotated_fft))
            latent_new = latent * correction
            latent_new = np.clip(latent_new, 1e-10, None)

            latent = latent_new
            residual_prev = residual_curr
            self.actual_iterations = i + 1

            if callback is not None:
                callback(i, self.num_iterations, latent, change_rate)

            if i >= 3 and change_rate < self.convergence_threshold:
                break

        return np.clip(latent, 0, 1)

    def deconvolve_tiled(self, image, callback=None):
        image = image.astype(np.float64)
        image = np.clip(image, 1e-10, None)
        h, w = image.shape

        tile_coords = self.tiled_convolver._get_tile_coords(h, w)
        self.convergence_history = []
        self.actual_iterations = 0

        latent = np.ones_like(image) * np.mean(image)
        residual_prev = None

        for i in range(self.num_iterations):
            convolved = self.tiled_convolver.convolve2d_tiled(
                latent, self.psf, tile_coords
            )
            convolved = np.clip(convolved, 1e-10, None)

            residual_curr = image / convolved
            change_rate = self._compute_residual_change_rate(residual_prev, residual_curr)
            self.convergence_history.append(change_rate)

            correction = self.tiled_convolver.convolve2d_tiled(
                residual_curr, self.psf_rotated, tile_coords
            )

            latent_new = latent * correction
            latent_new = np.clip(latent_new, 1e-10, None)
            latent = latent_new
            residual_prev = residual_curr
            self.actual_iterations = i + 1

            if callback is not None:
                callback(i, self.num_iterations, latent, change_rate)

            if i >= 3 and change_rate < self.convergence_threshold:
                break

        return np.clip(latent, 0, 1)


class RichardsonLucyGPU:
    def __init__(self, psf, num_iterations=50, convergence_threshold=1e-4,
                 tile_size=256):
        self.psf = psf.astype(np.float64)
        self.psf_rotated = psf[::-1, ::-1].astype(np.float64)
        self.num_iterations = num_iterations
        self.convergence_threshold = convergence_threshold
        self.psf_fft = None
        self.psf_rotated_fft = None
        self.convergence_history = []
        self.actual_iterations = 0
        self.tile_size = tile_size
        self.tiled_convolver = TiledFFTConvolver(tile_size=tile_size)

    def _prepare_fft(self, image_shape):
        psf_padded = np.zeros(image_shape, dtype=np.float64)
        ph, pw = self.psf.shape
        h, w = image_shape
        start_h = (h - ph) // 2
        start_w = (w - pw) // 2
        psf_padded[start_h:start_h + ph, start_w:start_w + pw] = self.psf
        self.psf_fft = np.fft.fft2(np.fft.ifftshift(psf_padded))

        psf_rotated_padded = np.zeros(image_shape, dtype=np.float64)
        psf_rotated_padded[start_h:start_h + ph, start_w:start_w + pw] = self.psf_rotated
        self.psf_rotated_fft = np.fft.fft2(np.fft.ifftshift(psf_rotated_padded))

    def _compute_residual_change_rate(self, residual_prev, residual_curr):
        if residual_prev is None:
            return float('inf')
        diff = np.mean(np.abs(residual_curr - residual_prev))
        baseline = np.mean(np.abs(residual_curr)) + 1e-10
        return diff / baseline

    def deconvolve(self, image, callback=None):
        try:
            from numba import cuda
            if not cuda.is_available():
                raise ImportError("CUDA not available")
            return self._deconvolve_gpu(image, callback)
        except (ImportError, Exception):
            print("CUDA not available, falling back to CPU...")
            rl = RichardsonLucy(self.psf, self.num_iterations,
                                self.convergence_threshold)
            return rl.deconvolve(image, callback)

    def _deconvolve_gpu(self, image, callback=None):
        image = image.astype(np.float64)
        image = np.clip(image, 1e-10, None)
        self._prepare_fft(image.shape)

        latent = np.ones_like(image) * np.mean(image)
        self.convergence_history = []
        self.actual_iterations = 0
        residual_prev = None

        for i in range(self.num_iterations):
            latent_fft = np.fft.fft2(latent)
            convolved = np.real(np.fft.ifft2(latent_fft * self.psf_fft))
            convolved = np.clip(convolved, 1e-10, None)

            residual_curr = image / convolved
            change_rate = self._compute_residual_change_rate(residual_prev, residual_curr)
            self.convergence_history.append(change_rate)

            relative_blur_fft = np.fft.fft2(residual_curr)
            correction = np.real(np.fft.ifft2(relative_blur_fft * self.psf_rotated_fft))
            latent *= correction
            latent = np.clip(latent, 1e-10, None)

            residual_prev = residual_curr
            self.actual_iterations = i + 1

            if callback is not None:
                callback(i, self.num_iterations, latent, change_rate)

            if i >= 3 and change_rate < self.convergence_threshold:
                break

        return np.clip(latent, 0, 1)


class BlindRichardsonLucy:
    def __init__(self, psf_size=21, num_outer_iterations=10,
                 num_inner_iterations=30, convergence_threshold=1e-4,
                 initial_sigma=2.0, use_gpu=False, tile_size=256):
        self.psf_size = psf_size
        self.num_outer_iterations = num_outer_iterations
        self.num_inner_iterations = num_inner_iterations
        self.convergence_threshold = convergence_threshold
        self.initial_sigma = initial_sigma
        self.use_gpu = use_gpu
        self.tile_size = tile_size
        self.estimated_psf = None
        self.psf_history = []

    def deconvolve(self, image, callback=None):
        from psf_generator import PSFGenerator
        image = image.astype(np.float64)

        psf = PSFGenerator.estimate_psf_from_image(image, method='autocorrelation',
                                                     psf_size=self.psf_size)
        self.psf_history = [psf.copy()]

        if self.use_gpu:
            rl_class = RichardsonLucyGPU
        else:
            rl_class = RichardsonLucy

        for outer_i in range(self.num_outer_iterations):
            rl = rl_class(psf, num_iterations=self.num_inner_iterations,
                          convergence_threshold=self.convergence_threshold,
                          tile_size=self.tile_size)
            latent = rl.deconvolve(image)

            psf = PSFGenerator._refine_psf(image, np.clip(latent, 1e-10, None),
                                            psf, self.psf_size)
            psf = PSFGenerator._apply_psf_constraints(psf)
            self.psf_history.append(psf.copy())
            self.estimated_psf = psf

            if callback is not None:
                callback(outer_i, self.num_outer_iterations, latent, psf)

        rl_final = rl_class(psf, num_iterations=self.num_inner_iterations * 2,
                             convergence_threshold=self.convergence_threshold,
                             tile_size=self.tile_size)
        final = rl_final.deconvolve(image)
        self.estimated_psf = psf
        return final, psf


def calculate_mse(image1, image2):
    return np.mean((image1 - image2) ** 2)


def calculate_psnr(image1, image2, max_val=1.0):
    mse = calculate_mse(image1, image2)
    if mse == 0:
        return float('inf')
    return 20 * np.log10(max_val / np.sqrt(mse))


if __name__ == '__main__':
    from psf_generator import PSFGenerator
    import cv2

    test_img = np.zeros((256, 256))
    for i in range(10):
        x, y = np.random.randint(30, 226, 2)
        r = np.random.randint(2, 6)
        test_img = cv2.circle(test_img, (x, y), r, 1.0, -1)
    test_img = gaussian_filter(test_img, sigma=0.5)

    psf = PSFGenerator.gaussian_psf(21, sigma=3.0)
    blurred = fftconvolve(test_img, psf, mode='same')
    blurred += np.random.normal(0, 0.01, blurred.shape)
    blurred = np.clip(blurred, 0, 1)

    start_time = time.time()
    rl = RichardsonLucy(psf, num_iterations=100, convergence_threshold=1e-4)
    deconvolved = rl.deconvolve(blurred)
    elapsed = time.time() - start_time

    print(f"CPU Time: {elapsed:.3f}s")
    print(f"Actual iterations: {rl.actual_iterations}")
    print(f"PSNR: {calculate_psnr(test_img, deconvolved):.2f} dB")

    start_time = time.time()
    blind = BlindRichardsonLucy(psf_size=21, num_outer_iterations=5,
                                 num_inner_iterations=20)
    blind_result, est_psf = blind.deconvolve(blurred)
    elapsed = time.time() - start_time
    print(f"\nBlind deconv time: {elapsed:.3f}s")
    print(f"Blind PSNR: {calculate_psnr(test_img, blind_result):.2f} dB")
