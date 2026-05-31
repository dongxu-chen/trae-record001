import numpy as np
from scipy.ndimage import gaussian_filter


class FFTWave:
    SPECTRUM_PHILLIPS = 'phillips'
    SPECTRUM_JONSWAP = 'jonswap'
    SPECTRUM_PM = 'pm'

    def __init__(self, grid_size=256, patch_size=100.0, spectrum_type='phillips'):
        self.grid_size = grid_size
        self.patch_size = patch_size
        self.wind_speed = 30.0
        self.wind_direction = np.array([1.0, 0.0])
        self.wave_amplitude = 0.0002
        self.choppy_factor = 1.5
        self.spectrum_type = spectrum_type
        self.jonswap_gamma = 3.3
        self.jonswap_sigma_a = 0.07
        self.jonswap_sigma_b = 0.09

        self.random_phases = np.random.uniform(
            0.0, 2.0 * np.pi,
            (self.grid_size, self.grid_size)
        )
        self._init_h0()

    def _spectrum(self, kx, ky):
        if self.spectrum_type == self.SPECTRUM_JONSWAP:
            return self._jonswap_spectrum(kx, ky)
        elif self.spectrum_type == self.SPECTRUM_PM:
            return self._pm_spectrum(kx, ky)
        else:
            return self._phillips_spectrum(kx, ky)

    def _phillips_spectrum(self, kx, ky):
        k = np.sqrt(kx**2 + ky**2)
        if k < 1e-6:
            return 0.0

        k_norm = np.array([kx, ky]) / k

        wind_dot_k = np.dot(k_norm, self.wind_direction)
        wind_dot_k_sq = wind_dot_k * wind_dot_k

        L = self.wind_speed ** 2 / 9.81

        kL = k * L
        exp_term = np.exp(-1.0 / (kL * kL))

        k2 = k * k
        k4 = k2 * k2

        damp = 0.001
        l = damp * L
        kl = k * l
        damp_term = np.exp(-kl * kl)

        return self.wave_amplitude * exp_term * wind_dot_k_sq / k4 * damp_term

    def _pm_spectrum(self, kx, ky):
        k = np.sqrt(kx**2 + ky**2)
        if k < 1e-6:
            return 0.0

        k_norm = np.array([kx, ky]) / k
        cos_theta = np.dot(k_norm, self.wind_direction)

        alpha = 0.0081
        g = 9.81
        omega_p = g / self.wind_speed

        S_omega = (alpha * g**2 / omega_p**5) * \
            np.exp(-1.25 * (omega_p / (k * self.wind_speed + 1e-6))**4)

        directional = np.clip(cos_theta, 0.0, 1.0)**2

        k_step = (2.0 * np.pi / self.patch_size)
        S_k = S_omega * self._dispersion(kx, ky) * k_step / (2.0 * k + 1e-6)

        return S_k * directional * self.wave_amplitude * 0.5

    def _jonswap_spectrum(self, kx, ky):
        k = np.sqrt(kx**2 + ky**2)
        if k < 1e-6:
            return 0.0

        k_norm = np.array([kx, ky]) / k
        cos_theta = np.dot(k_norm, self.wind_direction)

        g = 9.81
        U = self.wind_speed
        omega_p = 0.877 * g / U

        omega = self._dispersion(kx, ky)

        alpha = 0.076 * (U**2 / (g * 200.0))**0.22
        if alpha < 0.005:
            alpha = 0.005

        sigma = self.jonswap_sigma_a if omega <= omega_p else self.jonswap_sigma_b

        r = np.exp(-((omega - omega_p)**2) / (2.0 * sigma**2 * omega_p**2))
        gamma_peak = self.jonswap_gamma ** r

        S_omega = (alpha * g**2 / omega**5) * \
            np.exp(-1.25 * (omega_p / omega)**4) * gamma_peak

        directional = np.clip(cos_theta, 0.0, 1.0)**2

        k_step = (2.0 * np.pi / self.patch_size)
        S_k = S_omega * omega * k_step / (2.0 * k + 1e-6)

        return S_k * directional * self.wave_amplitude * 400.0

    def _init_h0(self):
        self.h0 = np.zeros((self.grid_size, self.grid_size), dtype=np.complex128)
        self.h0_conj = np.zeros((self.grid_size, self.grid_size), dtype=np.complex128)

        half_size = self.grid_size // 2

        for y in range(self.grid_size):
            for x in range(self.grid_size):
                kx = (x - half_size) * (2.0 * np.pi / self.patch_size)
                ky = (y - half_size) * (2.0 * np.pi / self.patch_size)

                spectrum = self._spectrum(kx, ky)
                sqrt_spectrum = np.sqrt(abs(spectrum) * 0.5)

                xi = np.random.normal(0.0, 1.0)
                eta = np.random.normal(0.0, 1.0)

                self.h0[y, x] = sqrt_spectrum * (xi + 1j * eta)

                x_conj = self.grid_size - x
                y_conj = self.grid_size - y
                if x_conj >= self.grid_size:
                    x_conj = 0
                if y_conj >= self.grid_size:
                    y_conj = 0
                self.h0_conj[y_conj, x_conj] = sqrt_spectrum * (xi - 1j * eta)

    def _dispersion(self, kx, ky):
        k_len = np.sqrt(kx**2 + ky**2)
        return np.sqrt(9.81 * k_len)

    def set_spectrum_type(self, spectrum_type):
        if spectrum_type != self.spectrum_type:
            self.spectrum_type = spectrum_type
            self.random_phases = np.random.uniform(
                0.0, 2.0 * np.pi,
                (self.grid_size, self.grid_size)
            )
            self._init_h0()

    def compute_wave_height(self, time):
        half_size = self.grid_size // 2
        h_t = np.zeros((self.grid_size, self.grid_size), dtype=np.complex128)

        for y in range(self.grid_size):
            for x in range(self.grid_size):
                kx = (x - half_size) * (2.0 * np.pi / self.patch_size)
                ky = (y - half_size) * (2.0 * np.pi / self.patch_size)

                omega = self._dispersion(kx, ky)
                phase = omega * time + self.random_phases[y, x]
                exp_term = np.cos(phase) + 1j * np.sin(phase)
                exp_conj_term = np.cos(phase) - 1j * np.sin(phase)

                x_conj = self.grid_size - x
                y_conj = self.grid_size - y
                if x_conj >= self.grid_size:
                    x_conj = 0
                if y_conj >= self.grid_size:
                    y_conj = 0

                h_t[y, x] = self.h0[y, x] * exp_term + \
                    self.h0_conj[y_conj, x_conj] * exp_conj_term

        heights = np.fft.ifft2(h_t)
        return np.real(heights) * self.grid_size

    def compute_choppy_displacement(self, time):
        half_size = self.grid_size // 2
        dx_t = np.zeros((self.grid_size, self.grid_size), dtype=np.complex128)
        dz_t = np.zeros((self.grid_size, self.grid_size), dtype=np.complex128)

        for y in range(self.grid_size):
            for x in range(self.grid_size):
                kx = (x - half_size) * (2.0 * np.pi / self.patch_size)
                ky = (y - half_size) * (2.0 * np.pi / self.patch_size)

                k_len = np.sqrt(kx**2 + ky**2)
                if k_len < 1e-6:
                    continue

                omega = self._dispersion(kx, ky)
                phase = omega * time + self.random_phases[y, x]
                exp_term = np.cos(phase) + 1j * np.sin(phase)
                exp_conj_term = np.cos(phase) - 1j * np.sin(phase)

                x_conj = self.grid_size - x
                y_conj = self.grid_size - y
                if x_conj >= self.grid_size:
                    x_conj = 0
                if y_conj >= self.grid_size:
                    y_conj = 0

                h_val = self.h0[y, x] * exp_term + \
                    self.h0_conj[y_conj, x_conj] * exp_conj_term

                dx_t[y, x] = -1j * (kx / k_len) * h_val * self.choppy_factor
                dz_t[y, x] = -1j * (ky / k_len) * h_val * self.choppy_factor

        dx = np.real(np.fft.ifft2(dx_t)) * self.grid_size
        dz = np.real(np.fft.ifft2(dz_t)) * self.grid_size

        return dx, dz

    def compute_normals(self, heights):
        normals = np.zeros((self.grid_size, self.grid_size, 3), dtype=np.float32)

        scale = self.patch_size / self.grid_size

        for y in range(self.grid_size):
            for x in range(self.grid_size):
                x_prev = (x - 1) % self.grid_size
                x_next = (x + 1) % self.grid_size
                y_prev = (y - 1) % self.grid_size
                y_next = (y + 1) % self.grid_size

                dhdx = (heights[y, x_next] - heights[y, x_prev]) / (2.0 * scale)
                dhdy = (heights[y_next, x] - heights[y_prev, x]) / (2.0 * scale)

                normal = np.array([-dhdx, 1.0, -dhdy])
                normal_len = np.linalg.norm(normal)
                if normal_len > 1e-6:
                    normal = normal / normal_len

                normals[y, x] = normal

        return normals

    def compute_foam(self, heights, threshold=0.7, time=0.0):
        grad_x = np.gradient(heights, axis=1)
        grad_y = np.gradient(heights, axis=0)
        gradient_mag = np.sqrt(grad_x**2 + grad_y**2)

        max_grad = np.max(gradient_mag)
        if max_grad > 0:
            gradient_mag = gradient_mag / max_grad

        jacobian = self._compute_jacobian(heights)
        jacobian = np.clip(jacobian, 0.0, 1.0)

        foam = np.where((gradient_mag > threshold) | (jacobian < 0.3), 1.0, 0.0)

        foam = self._advect_foam(foam, grad_x, grad_y, time)

        foam = gaussian_filter(foam, sigma=1.2)

        return foam

    def _compute_jacobian(self, heights):
        dx = np.gradient(heights, axis=1)
        dy = np.gradient(heights, axis=0)
        dxx = np.gradient(dx, axis=1)
        dyy = np.gradient(dy, axis=0)
        dxy = np.gradient(dx, axis=0)

        jacobian = (1 + dxx) * (1 + dyy) - dxy * dxy
        jacobian = (jacobian - jacobian.min()) / \
            (jacobian.max() - jacobian.min() + 1e-6)

        return jacobian

    def _advect_foam(self, foam, vel_x, vel_y, time):
        advected = np.copy(foam)
        rows, cols = foam.shape

        flow_speed = 0.1
        for y in range(rows):
            for x in range(cols):
                offset_x = int(vel_x[y, x] * flow_speed * 20)
                offset_y = int(vel_y[y, x] * flow_speed * 20)

                src_x = np.clip(x + offset_x, 0, cols - 1)
                src_y = np.clip(y + offset_y, 0, rows - 1)

                advected[y, x] = foam[src_y, src_x]

        return np.maximum(foam, advected * 0.5)

    def get_height_at(self, world_x, world_z, heights):
        half_grid = heights.shape[0] / 2
        scale = heights.shape[0] / 1.0

        gx = int(world_x / (1.0 / scale) + half_grid)
        gz = int(world_z / (1.0 / scale) + half_grid)

        gx = np.clip(gx, 0, heights.shape[1] - 2)
        gz = np.clip(gz, 0, heights.shape[0] - 2)

        fx = (world_x / (1.0 / scale) + half_grid) - gx
        fz = (world_z / (1.0 / scale) + half_grid) - gz

        h00 = heights[gz, gx]
        h10 = heights[gz, gx + 1]
        h01 = heights[gz + 1, gx]
        h11 = heights[gz + 1, gx + 1]

        h = h00 * (1 - fx) * (1 - fz) + h10 * fx * (1 - fz) + \
            h01 * (1 - fx) * fz + h11 * fx * fz

        return h

    def get_normal_at(self, world_x, world_z, heights):
        half_grid = heights.shape[0] / 2
        grid_size = heights.shape[0]
        scale = 1.0 / (1.0 / (1.0 / grid_size * 1.0))

        eps = 1.0
        h_xp = self.get_height_at(world_x + eps, world_z, heights)
        h_xn = self.get_height_at(world_x - eps, world_z, heights)
        h_zp = self.get_height_at(world_x, world_z + eps, heights)
        h_zn = self.get_height_at(world_x, world_z - eps, heights)

        dhdx = (h_xp - h_xn) / (2.0 * eps)
        dhdz = (h_zp - h_zn) / (2.0 * eps)

        normal = np.array([-dhdx, 1.0, -dhdz])
        normal_len = np.linalg.norm(normal)
        if normal_len > 1e-6:
            normal = normal / normal_len

        return normal
