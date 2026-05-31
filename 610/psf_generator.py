import numpy as np
from scipy.special import j1
from scipy.signal import fftconvolve
from scipy.ndimage import gaussian_filter


class PSFGenerator:
    @staticmethod
    def gaussian_psf(size, sigma=1.0, normalize=True):
        x = np.linspace(-(size // 2), size // 2, size)
        y = np.linspace(-(size // 2), size // 2, size)
        x, y = np.meshgrid(x, y)
        psf = np.exp(-(x ** 2 + y ** 2) / (2 * sigma ** 2))
        if normalize:
            psf = psf / psf.sum()
        return psf

    @staticmethod
    def airy_disk_psf(size, na=1.4, wavelength=0.5, pixel_size=0.1, normalize=True):
        x = np.linspace(-(size // 2), size // 2, size)
        y = np.linspace(-(size // 2), size // 2, size)
        x, y = np.meshgrid(x, y)
        r = np.sqrt(x ** 2 + y ** 2) * pixel_size
        k = (2 * np.pi * na) / wavelength
        v = k * r
        v[v == 0] = 1e-10
        airy = (2 * j1(v) / v) ** 2
        if normalize:
            airy = airy / airy.sum()
        return airy

    @staticmethod
    def disk_psf(size, radius=3, normalize=True):
        x = np.linspace(-(size // 2), size // 2, size)
        y = np.linspace(-(size // 2), size // 2, size)
        x, y = np.meshgrid(x, y)
        r = np.sqrt(x ** 2 + y ** 2)
        psf = np.where(r <= radius, 1.0, 0.0)
        if normalize:
            psf = psf / psf.sum()
        return psf

    @staticmethod
    def motion_blur_psf(size, length=5, angle=0, normalize=True):
        psf = np.zeros((size, size))
        center = size // 2
        angle_rad = np.deg2rad(angle)
        dx = np.cos(angle_rad)
        dy = np.sin(angle_rad)
        for i in range(length):
            x = int(center + i * dx - (length // 2) * dx)
            y = int(center + i * dy - (length // 2) * dy)
            if 0 <= x < size and 0 <= y < size:
                psf[y, x] = 1.0
        if normalize:
            psf = psf / psf.sum()
        return psf

    @staticmethod
    def estimate_psf_from_image(image, method='autocorrelation', psf_size=21):
        if method == 'autocorrelation':
            return PSFGenerator._estimate_autocorrelation(image, psf_size)
        elif method == 'cepstrum':
            return PSFGenerator._estimate_cepstrum(image, psf_size)
        elif method == 'edge_spread':
            return PSFGenerator._estimate_edge_spread(image, psf_size)
        else:
            raise ValueError(f"Unknown PSF estimation method: {method}")

    @staticmethod
    def _estimate_autocorrelation(image, psf_size):
        mean_val = np.mean(image)
        img_centered = image - mean_val
        spectrum = np.fft.fft2(img_centered)
        power_spectrum = np.abs(spectrum) ** 2
        log_power = np.log1p(power_spectrum)
        smoothed_log = gaussian_filter(log_power, sigma=3.0)
        inv_spectrum = np.exp(smoothed_log) - 1.0
        inv_spectrum = np.sqrt(inv_spectrum)
        autocorr = np.fft.fftshift(np.abs(np.fft.ifft2(inv_spectrum)))
        cy, cx = autocorr.shape[0] // 2, autocorr.shape[1] // 2
        half = psf_size // 2
        psf = autocorr[cy - half:cy + half + 1, cx - half:cx + half + 1]
        psf = np.clip(psf, 0, None)
        psf = gaussian_filter(psf, sigma=0.5)
        psf = psf / psf.sum()
        return psf

    @staticmethod
    def _estimate_cepstrum(image, psf_size):
        mean_val = np.mean(image)
        img_centered = image - mean_val
        spectrum = np.fft.fft2(img_centered)
        log_magnitude = np.log1p(np.abs(spectrum))
        cepstrum = np.fft.fftshift(np.abs(np.fft.ifft2(log_magnitude)))
        cy, cx = cepstrum.shape[0] // 2, cepstrum.shape[1] // 2
        half = psf_size // 2
        psf = cepstrum[cy - half:cy + half + 1, cx - half:cx + half + 1]
        psf = np.clip(psf, 0, None)
        psf = gaussian_filter(psf, sigma=0.8)
        psf = psf / psf.sum()
        return psf

    @staticmethod
    def _estimate_edge_spread(image, psf_size):
        grad_y, grad_x = np.gradient(image)
        edge_strength = np.sqrt(grad_x ** 2 + grad_y ** 2)
        esf = np.mean(edge_strength)
        sigma_est = max(1.0, psf_size / (2 * np.pi * max(esf, 0.01)))
        sigma_est = min(sigma_est, psf_size / 4.0)
        return PSFGenerator.gaussian_psf(psf_size, sigma=sigma_est)

    @staticmethod
    def blind_estimate_psf(image, psf_size=21, num_iterations=10,
                           initial_sigma=2.0, callback=None):
        image = image.astype(np.float64)
        psf = PSFGenerator.gaussian_psf(psf_size, sigma=initial_sigma)

        for i in range(num_iterations):
            from deconvolution import RichardsonLucy
            rl = RichardsonLucy(psf, num_iterations=3)
            latent = rl.deconvolve(image)
            latent_sharp = np.clip(latent, 0, None)

            new_psf = PSFGenerator._refine_psf(image, latent_sharp, psf, psf_size)
            psf = PSFGenerator._apply_psf_constraints(new_psf)

            if callback is not None:
                callback(i, num_iterations, psf)

        return psf

    @staticmethod
    def _refine_psf(observed, estimated_latent, current_psf, psf_size):
        psf_rotated = current_psf[::-1, ::-1]
        correction = fftconvolve(observed / np.clip(
            fftconvolve(estimated_latent, current_psf, mode='same'), 1e-10, None),
            psf_rotated, mode='same'
        )
        new_latent = estimated_latent * correction
        new_latent = np.clip(new_latent, 1e-10, None)

        h, w = observed.shape
        ph, pw = current_psf.shape
        psf_numerator = np.zeros_like(current_psf)
        psf_denominator = np.zeros_like(current_psf)

        for dy in range(ph):
            for dx in range(pw):
                y_start = max(0, dy - ph // 2)
                y_end = min(h, h + dy - ph // 2)
                x_start = max(0, dx - pw // 2)
                x_end = min(w, w + dx - pw // 2)
                ly_start = y_start - (dy - ph // 2)
                ly_end = y_end - (dy - ph // 2)
                lx_start = x_start - (dx - pw // 2)
                lx_end = x_end - (dx - pw // 2)
                if y_end > y_start and x_end > x_start:
                    psf_numerator[dy, dx] = np.sum(
                        observed[y_start:y_end, x_start:x_end] *
                        new_latent[ly_start:ly_end, lx_start:lx_end]
                    )
                    psf_denominator[dy, dx] = np.sum(
                        new_latent[ly_start:ly_end, lx_start:lx_end]
                    )

        psf_denominator = np.clip(psf_denominator, 1e-10, None)
        new_psf = psf_numerator / psf_denominator
        return new_psf

    @staticmethod
    def _apply_psf_constraints(psf):
        psf = np.clip(psf, 0, None)
        psf = gaussian_filter(psf, sigma=0.3)
        psf = psf / psf.sum()
        return psf
