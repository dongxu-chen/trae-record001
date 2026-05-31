import numpy as np
from scipy.signal import fftconvolve
from scipy.ndimage import gaussian_filter
from deconvolution import TiledFFTConvolver, calculate_psnr


class PSF3DGenerator:
    @staticmethod
    def gaussian_3d(size_xy=21, size_z=5, sigma_xy=2.0, sigma_z=1.0, normalize=True):
        z = np.linspace(-(size_z // 2), size_z // 2, size_z)
        y = np.linspace(-(size_xy // 2), size_xy // 2, size_xy)
        x = np.linspace(-(size_xy // 2), size_xy // 2, size_xy)
        zz, yy, xx = np.meshgrid(z, y, x, indexing='ij')
        psf = np.exp(-(xx ** 2 + yy ** 2) / (2 * sigma_xy ** 2)
                     - zz ** 2 / (2 * sigma_z ** 2))
        if normalize:
            psf = psf / psf.sum()
        return psf

    @staticmethod
    def estimate_3d_from_image(image_3d, psf_size_xy=21, psf_size_z=5):
        num_channels = image_3d.shape[0] if image_3d.ndim == 4 else 1
        if num_channels > 1:
            mean_img = np.mean(image_3d, axis=0)
        else:
            mean_img = image_3d

        mean_z_proj = np.mean(mean_img, axis=0)
        from psf_generator import PSFGenerator
        psf_xy = PSFGenerator.estimate_psf_from_image(mean_z_proj, 'autocorrelation', psf_size_xy)

        psf_z = np.ones(psf_size_z)
        psf_z = psf_z / psf_z.sum()

        psf_3d = np.zeros((psf_size_z, psf_size_xy, psf_size_xy))
        for z in range(psf_size_z):
            psf_3d[z] = psf_xy * psf_z[z]
        psf_3d = psf_3d / psf_3d.sum()
        return psf_3d


class RichardsonLucy3D:
    def __init__(self, psf_3d, num_iterations=50, convergence_threshold=1e-4,
                 tile_size_xy=256, tile_size_z=8):
        self.psf = psf_3d
        self.psf_rotated = psf_3d[::-1, ::-1, ::-1]
        self.num_iterations = num_iterations
        self.convergence_threshold = convergence_threshold
        self.tile_size_xy = tile_size_xy
        self.tile_size_z = tile_size_z
        self.convergence_history = []
        self.actual_iterations = 0

    def _prepare_fft(self, shape):
        sz, sy, sx = shape
        psf_padded = np.zeros(shape, dtype=np.float64)
        pz, py, px = self.psf.shape
        sz0, sy0, sx0 = (sz - pz) // 2, (sy - py) // 2, (sx - px) // 2
        psf_padded[sz0:sz0 + pz, sy0:sy0 + py, sx0:sx0 + px] = self.psf
        self.psf_fft = np.fft.fftn(np.fft.ifftshift(psf_padded))

        psf_rot_padded = np.zeros(shape, dtype=np.float64)
        psf_rot_padded[sz0:sz0 + pz, sy0:sy0 + py, sx0:sx0 + px] = self.psf_rotated
        self.psf_rotated_fft = np.fft.fftn(np.fft.ifftshift(psf_rot_padded))

    def _compute_residual_change_rate(self, prev, curr):
        if prev is None:
            return float('inf')
        diff = np.mean(np.abs(curr - prev))
        baseline = np.mean(np.abs(curr)) + 1e-10
        return diff / baseline

    def deconvolve(self, image, callback=None):
        image = image.astype(np.float64)
        image = np.clip(image, 1e-10, None)
        self._prepare_fft(image.shape)

        latent = np.ones_like(image) * np.mean(image)
        self.convergence_history = []
        residual_prev = None

        for i in range(self.num_iterations):
            latent_fft = np.fft.fftn(latent)
            convolved = np.real(np.fft.ifftn(latent_fft * self.psf_fft))
            convolved = np.clip(convolved, 1e-10, None)

            residual_curr = image / convolved
            change_rate = self._compute_residual_change_rate(residual_prev, residual_curr)
            self.convergence_history.append(change_rate)

            residual_fft = np.fft.fftn(residual_curr)
            correction = np.real(np.fft.ifftn(residual_fft * self.psf_rotated_fft))
            latent *= correction
            latent = np.clip(latent, 1e-10, None)

            residual_prev = residual_curr
            self.actual_iterations = i + 1

            if callback is not None:
                callback(i, self.num_iterations, latent, change_rate)

            if i >= 5 and change_rate < self.convergence_threshold:
                break

        return np.clip(latent, 0, 1)


class MultiChannelDeconvolver:
    def __init__(self, psf_list=None, num_iterations=50, convergence_threshold=1e-4):
        self.psf_list = psf_list
        self.num_iterations = num_iterations
        self.convergence_threshold = convergence_threshold
        self.results = []

    def deconvolve_channels(self, image, psf_list=None, callback=None):
        if psf_list is None:
            psf_list = self.psf_list

        if image.ndim == 3:
            image = image[np.newaxis, ...]

        num_channels = image.shape[0]
        result = np.zeros_like(image)

        for c in range(num_channels):
            if callback:
                callback(c, num_channels, None, 0, 'channel')

            if psf_list and c < len(psf_list):
                psf = psf_list[c]
            else:
                from psf_generator import PSFGenerator
                mean_img = np.mean(image[c], axis=0) if image[c].ndim == 3 else image[c]
                psf = PSFGenerator.estimate_psf_from_image(mean_img, 'autocorrelation', 21)

            if image[c].ndim == 3:
                rl = RichardsonLucy3D(psf if psf.ndim == 3 else PSF3DGenerator.gaussian_3d(),
                                       self.num_iterations, self.convergence_threshold)
                result[c] = rl.deconvolve(image[c])
            else:
                from deconvolution import RichardsonLucy
                rl = RichardsonLucy(psf, self.num_iterations, self.convergence_threshold)
                result[c] = rl.deconvolve(image[c])

            if callback:
                callback(c + 1, num_channels, result[c], 1, 'channel')

        return result

    def deconvolve_3d_channels(self, image_4d, psf_3d_list=None, callback=None):
        num_channels, nz, ny, nx = image_4d.shape
        result = np.zeros_like(image_4d)

        for c in range(num_channels):
            if callback:
                callback(c, num_channels, None, 0, 'channel_3d')

            psf_3d = psf_3d_list[c] if (psf_3d_list and c < len(psf_3d_list)) \
                else PSF3DGenerator.estimate_3d_from_image(image_4d[c:c+1])

            rl3d = RichardsonLucy3D(psf_3d, self.num_iterations, self.convergence_threshold)

            def iter_cb(iter_i, total, img, rate):
                if callback:
                    callback(c, num_channels, img, (iter_i + 1) / total, 'iter_3d')

            result[c] = rl3d.deconvolve(image_4d[c], callback=iter_cb)

            if callback:
                callback(c + 1, num_channels, result[c], 1, 'channel_3d_done')

        return result


class ZSliceDeconvolver:
    def __init__(self, psf_xy, psf_z=None, num_iterations=30, convergence_threshold=1e-4):
        self.psf_xy = psf_xy
        self.psf_z = psf_z if psf_z is not None else np.ones(3) / 3
        self.num_iterations = num_iterations
        self.convergence_threshold = convergence_threshold

    def deconvolve(self, image_3d, callback=None):
        nz, ny, nx = image_3d.shape
        result = image_3d.copy()

        for iteration in range(self.num_iterations):
            for z in range(nz):
                from deconvolution import RichardsonLucy
                rl = RichardsonLucy(self.psf_xy, num_iterations=3)
                result[z] = rl.deconvolve(result[z])

            residual = np.zeros_like(result)
            for y in range(ny):
                for x in range(nx):
                    line = result[:, y, x]
                    line_deconv = self._deconv_1d(line, self.psf_z)
                    residual[:, y, x] = line_deconv / np.clip(line, 1e-10, None)

            result *= np.clip(residual, 0.5, 2.0)

            if callback:
                callback(iteration, self.num_iterations, result, 0)

        return np.clip(result, 0, 1)

    @staticmethod
    def _deconv_1d(signal, kernel, iterations=5):
        result = signal.copy()
        kernel_rot = kernel[::-1]
        for _ in range(iterations):
            conv = np.convolve(result, kernel, mode='same')
            ratio = signal / np.clip(conv, 1e-10, None)
            correction = np.convolve(ratio, kernel_rot, mode='same')
            result *= correction
        return result


if __name__ == '__main__':
    print("3D Deconvolution module loaded")
