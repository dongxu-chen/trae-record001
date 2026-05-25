import numpy as np
from ray import create_ray_bundle, create_collimated_rays
from optical_constants import refractive_index


class DiffractionPSF:
    def __init__(self, optical_system, ray_tracer=None):
        self.optical_system = optical_system
        self.ray_tracer = ray_tracer
        if ray_tracer is None:
            from ray_tracer import RayTracer
            self.ray_tracer = RayTracer(optical_system)

    def calculate_exit_pupil_phase(self, object_height=0.0, wavelength=0.587,
                                     max_height=10.0, num_rays=100,
                                     pupil_samples=256):
        z_min, _ = self.optical_system.get_z_extent()
        initial_z = z_min - 50
        rays = create_ray_bundle(
            object_height=object_height,
            num_rays=num_rays,
            max_height=max_height,
            wavelength=wavelength,
            initial_z=initial_z,
            distribution='radial'
        )
        traced = self.ray_tracer.trace_rays(rays)
        active_rays = [r for r in traced if r.active and r.final_position is not None]
        if len(active_rays) < 10:
            return None, None, None
        positions = np.array([r.final_position[:2] for r in active_rays])
        optical_path_lengths = np.array([r.get_path_length() for r in active_rays])
        entrance_positions = np.array([r.history[0][0][:2] for r in active_rays])
        entrance_heights = np.sqrt(entrance_positions[:, 0]**2 + entrance_positions[:, 1]**2)
        opd = optical_path_lengths - np.min(optical_path_lengths)
        opd_waves = opd / wavelength
        pupil_grid = np.zeros((pupil_samples, pupil_samples), dtype=complex)
        weight_grid = np.zeros((pupil_samples, pupil_samples))
        max_r = np.max(entrance_heights) if len(entrance_heights) > 0 else max_height
        for i, (h, opd_w) in enumerate(zip(entrance_heights, opd_waves)):
            x = entrance_positions[i, 0]
            y = entrance_positions[i, 1]
            ix = int((x / max_r + 1) * pupil_samples / 2)
            iy = int((y / max_r + 1) * pupil_samples / 2)
            ix = np.clip(ix, 0, pupil_samples - 1)
            iy = np.clip(iy, 0, pupil_samples - 1)
            phase = 2 * np.pi * opd_w
            pupil_grid[iy, ix] += np.exp(1j * phase)
            weight_grid[iy, ix] += 1
        valid = weight_grid > 0
        pupil_grid[valid] /= weight_grid[valid]
        return pupil_grid, max_r, opd_waves

    def calculate_psf_huygens(self, object_height=0.0, wavelength=0.587,
                               max_height=10.0, num_rays=200,
                               psf_size=64, pixel_size=1.0):
        z_min, _ = self.optical_system.get_z_extent()
        initial_z = z_min - 50
        rays = create_ray_bundle(
            object_height=object_height,
            num_rays=num_rays,
            max_height=max_height,
            wavelength=wavelength,
            initial_z=initial_z,
            distribution='radial'
        )
        traced = self.ray_tracer.trace_rays(rays)
        active_rays = [r for r in traced if r.active and r.final_position is not None]
        if len(active_rays) < 10:
            return np.zeros((psf_size, psf_size)), np.zeros(psf_size)
        final_positions = np.array([r.final_position[:2] for r in active_rays])
        optical_path_lengths = np.array([r.get_path_length() for r in active_rays])
        opd = optical_path_lengths - np.min(optical_path_lengths)
        psf = np.zeros((psf_size, psf_size), dtype=complex)
        x = np.linspace(-psf_size * pixel_size / 2, psf_size * pixel_size / 2, psf_size)
        y = np.linspace(-psf_size * pixel_size / 2, psf_size * pixel_size / 2, psf_size)
        X, Y = np.meshgrid(x, y)
        k = 2 * np.pi / wavelength
        for pos, opd_i in zip(final_positions, opd):
            dx = X - pos[0]
            dy = Y - pos[1]
            r = np.sqrt(dx**2 + dy**2)
            phase = k * (opd_i + np.sqrt(r**2 + 1e-10))
            psf += np.exp(1j * phase) / (r + 1e-10)
        psf_intensity = np.abs(psf)**2
        psf_intensity /= np.sum(psf_intensity)
        line_profile = psf_intensity[psf_size // 2, :]
        return psf_intensity, line_profile

    def calculate_psf_fft(self, object_height=0.0, wavelength=0.587,
                           max_height=10.0, num_rays=100,
                           pupil_samples=256, psf_size=128):
        pupil_grid, max_r, opd_waves = self.calculate_exit_pupil_phase(
            object_height=object_height, wavelength=wavelength,
            max_height=max_height, num_rays=num_rays,
            pupil_samples=pupil_samples
        )
        if pupil_grid is None:
            return np.zeros((psf_size, psf_size)), np.zeros(psf_size)
        padded_pupil = np.zeros((pupil_samples * 2, pupil_samples * 2), dtype=complex)
        pad_start = pupil_samples // 2
        padded_pupil[pad_start:pad_start + pupil_samples,
                     pad_start:pad_start + pupil_samples] = pupil_grid
        psf_field = np.fft.fftshift(np.fft.fft2(np.fft.ifftshift(padded_pupil)))
        psf_intensity = np.abs(psf_field)**2
        psf_intensity /= np.sum(psf_intensity)
        center = psf_intensity.shape[0] // 2
        half = psf_size // 2
        psf_cropped = psf_intensity[center - half:center + half,
                                    center - half:center + half]
        line_profile = psf_cropped[psf_size // 2, :]
        return psf_cropped, line_profile

    def calculate_mtf_from_psf(self, psf):
        otf = np.fft.fftshift(np.fft.fft2(np.fft.ifftshift(psf)))
        mtf = np.abs(otf)
        mtf /= mtf[mtf.shape[0] // 2, mtf.shape[1] // 2]
        return mtf

    def calculate_mtf(self, object_height=0.0, wavelength=0.587,
                       max_height=10.0, num_rays=100,
                       spatial_frequencies=None, num_samples=20,
                       method='geometric'):
        if method == 'geometric':
            return self._calculate_mtf_geometric(
                object_height=object_height, wavelength=wavelength,
                max_height=max_height, num_rays=num_rays,
                spatial_frequencies=spatial_frequencies,
                num_samples=num_samples
            )
        elif method == 'diffraction':
            return self._calculate_mtf_diffraction(
                object_height=object_height, wavelength=wavelength,
                max_height=max_height, num_rays=num_rays,
                spatial_frequencies=spatial_frequencies
            )
        else:
            raise ValueError(f"Unknown method: {method}. Use 'geometric' or 'diffraction'")

    def _calculate_mtf_geometric(self, object_height=0.0, wavelength=0.587,
                                  max_height=10.0, num_rays=200,
                                  spatial_frequencies=None, num_samples=20):
        from ray_tracer import ImageAnalysis
        analysis = ImageAnalysis(self.optical_system, self.ray_tracer)
        spot_data = analysis.get_spot_diagram(
            object_height=object_height, wavelengths=[wavelength],
            num_rays=num_rays, max_height=max_height
        )
        if wavelength not in spot_data or len(spot_data[wavelength]) == 0:
            if spatial_frequencies is None:
                spatial_frequencies = np.linspace(0, 100, num_samples)
            return spatial_frequencies, np.zeros_like(spatial_frequencies)
        positions = spot_data[wavelength]
        if spatial_frequencies is None:
            spatial_frequencies = np.linspace(0, 100, num_samples)
        mtf_values = []
        for freq in spatial_frequencies:
            if freq == 0:
                mtf_values.append(1.0)
                continue
            phase = 2 * np.pi * freq * positions[:, 0] / 1000
            otf = np.mean(np.exp(-1j * phase))
            mtf_values.append(np.abs(otf))
        return spatial_frequencies, np.array(mtf_values)

    def _calculate_mtf_diffraction(self, object_height=0.0, wavelength=0.587,
                                    max_height=10.0, num_rays=100,
                                    spatial_frequencies=None):
        psf, _ = self.calculate_psf_fft(
            object_height=object_height, wavelength=wavelength,
            max_height=max_height, num_rays=num_rays
        )
        mtf = self.calculate_mtf_from_psf(psf)
        ny, nx = mtf.shape
        mtf_line = mtf[ny // 2, nx // 2:]
        if spatial_frequencies is None:
            max_freq = 100
            spatial_frequencies = np.linspace(0, max_freq, len(mtf_line))
        else:
            indices = np.linspace(0, len(mtf_line) - 1, len(spatial_frequencies)).astype(int)
            mtf_line = mtf_line[indices]
        return spatial_frequencies, mtf_line

    def calculate_strehl_ratio(self, object_height=0.0, wavelength=0.587,
                                max_height=10.0, num_rays=200):
        psf, _ = self.calculate_psf_fft(
            object_height=object_height, wavelength=wavelength,
            max_height=max_height, num_rays=num_rays
        )
        peak_intensity = np.max(psf)
        strehl = peak_intensity * psf.size
        return strehl

    def calculate_airy_disk_radius(self, wavelength=0.587, f_number=3.0):
        return 1.22 * wavelength * f_number * 1e-3

    def calculate_diffraction_limited_mtf(self, spatial_frequencies,
                                            wavelength=0.587, f_number=3.0):
        cutoff_freq = 1 / (wavelength * f_number * 1e-3)
        sf_norm = spatial_frequencies / cutoff_freq
        mtf = np.zeros_like(sf_norm)
        valid = sf_norm <= 1.0
        mtf[valid] = (2 / np.pi) * (
            np.arccos(sf_norm[valid]) -
            sf_norm[valid] * np.sqrt(1 - sf_norm[valid]**2)
        )
        return spatial_frequencies, mtf
