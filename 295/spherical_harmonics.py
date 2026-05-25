import numpy as np
from scipy.special import factorial, roots_legendre, eval_jacobi


class SphericalHarmonics:
    def __init__(self, l_max: int = 64):
        if l_max < 0:
            raise ValueError("l_max must be non-negative")
        if l_max > 64:
            raise ValueError("l_max cannot exceed 64")
        self.l_max = l_max
        self._precompute_normalization()
        self._precompute_recurrence_coeffs()

    def _precompute_normalization(self):
        self._norm = {}
        for l in range(self.l_max + 1):
            self._norm[l] = {}
            for m in range(-l, l + 1):
                m_abs = abs(m)
                numerator = (2 * l + 1) * factorial(l - m_abs)
                denominator = 4 * np.pi * factorial(l + m_abs)
                self._norm[l][m] = np.sqrt(numerator / denominator)

    def _precompute_recurrence_coeffs(self):
        self._a_coeff = {}
        self._b_coeff = {}
        for l in range(self.l_max + 1):
            self._a_coeff[l] = {}
            self._b_coeff[l] = {}
            for m in range(l + 1):
                if l > m:
                    self._a_coeff[l][m] = np.sqrt((2 * l + 1) * (2 * l - 1) / ((l - m) * (l + m)))
                    self._b_coeff[l][m] = np.sqrt(((l + m - 1) * (l - m - 1) * (2 * l + 1)) /
                                                   ((2 * l - 3) * (l - m) * (l + m)))
                else:
                    self._a_coeff[l][m] = 0.0
                    self._b_coeff[l][m] = 0.0

    def associated_legendre_stable(self, l: int, m: int, x: np.ndarray) -> np.ndarray:
        if l < 0 or abs(m) > l:
            raise ValueError(f"Invalid l={l}, m={m}")
        if l > self.l_max:
            raise ValueError(f"l={l} exceeds l_max={self.l_max}")

        m_abs = abs(m)
        x = np.asarray(x, dtype=np.float64)
        sqrt_1mx2 = np.sqrt(1 - x**2)

        if l == 0 and m_abs == 0:
            return np.ones_like(x)

        p_mm = 1.0
        for i in range(1, m_abs + 1):
            p_mm *= -(2 * i - 1) * sqrt_1mx2

        if l == m_abs:
            result = p_mm
        elif l == m_abs + 1:
            result = x * (2 * m_abs + 1) * p_mm
        else:
            p_prev = p_mm
            p_curr = x * (2 * m_abs + 1) * p_mm

            for ll in range(m_abs + 2, l + 1):
                a = self._a_coeff[ll][m_abs]
                b = self._b_coeff[ll][m_abs]
                p_next = a * x * p_curr - b * p_prev
                p_prev = p_curr
                p_curr = p_next

            result = p_curr

        if m < 0:
            sign = (-1) ** m_abs
            result *= sign * factorial(l - m_abs) / factorial(l + m_abs)

        return result

    def associated_legendre(self, l: int, m: int, x: np.ndarray) -> np.ndarray:
        return self.associated_legendre_stable(l, m, x)

    def Ylm(self, l: int, m: int, theta: np.ndarray, phi: np.ndarray) -> np.ndarray:
        theta = np.asarray(theta, dtype=np.float64)
        phi = np.asarray(phi, dtype=np.float64)

        if theta.shape != phi.shape:
            raise ValueError("theta and phi must have the same shape")

        x = np.cos(theta)
        plm = self.associated_legendre(l, m, x)
        norm = self._norm[l][m]
        m_abs = abs(m)

        if m >= 0:
            phase = np.cos(m * phi) + 1j * np.sin(m * phi)
        else:
            phase = np.cos(m_abs * phi) - 1j * np.sin(m_abs * phi)
            phase *= (-1) ** m_abs

        return norm * plm * phase

    def Ylm_real(self, l: int, m: int, theta: np.ndarray, phi: np.ndarray) -> np.ndarray:
        theta = np.asarray(theta, dtype=np.float64)
        phi = np.asarray(phi, dtype=np.float64)

        if m == 0:
            return np.real(self.Ylm(l, 0, theta, phi))
        elif m > 0:
            return np.sqrt(2) * np.real(self.Ylm(l, m, theta, phi))
        else:
            return np.sqrt(2) * np.imag(self.Ylm(l, -m, theta, phi))

    def get_all_Ylm(self, theta: np.ndarray, phi: np.ndarray) -> dict:
        result = {}
        for l in range(self.l_max + 1):
            result[l] = {}
            for m in range(-l, l + 1):
                result[l][m] = self.Ylm(l, m, theta, phi)
        return result

    def spherical_integral_gauss_legendre(self, f: np.ndarray, theta: np.ndarray,
                                           phi: np.ndarray, weights: np.ndarray = None) -> float:
        f = np.asarray(f, dtype=np.complex128)
        theta = np.asarray(theta, dtype=np.float64)
        phi = np.asarray(phi, dtype=np.float64)

        if f.ndim == 1:
            n_theta = len(np.unique(theta))
            n_phi = len(np.unique(phi))
            f = f.reshape(n_theta, n_phi)
            theta_2d = theta.reshape(n_theta, n_phi)
            phi_2d = phi.reshape(n_theta, n_phi)
        else:
            theta_2d = theta
            phi_2d = phi
            n_theta, n_phi = f.shape

        if weights is not None:
            weights = np.asarray(weights, dtype=np.float64)
            if weights.ndim == 1:
                weights = weights[:, np.newaxis]
            dphi = 2 * np.pi / n_phi
            integrand = f * weights * dphi
            return np.sum(integrand)
        else:
            x_vals = np.cos(np.unique(theta_2d[:, 0]))
            x, gl_weights = roots_legendre(n_theta)

            dphi = np.diff(np.unique(phi_2d[0, :]))
            if len(dphi) > 0:
                dphi = dphi[0]
            else:
                dphi = 2 * np.pi / n_phi

            integrand = f * gl_weights[:, np.newaxis] * dphi
            return np.sum(integrand)

    def spherical_integral(self, f: np.ndarray, theta: np.ndarray, phi: np.ndarray,
                           weights: np.ndarray = None) -> float:
        return self.spherical_integral_gauss_legendre(f, theta, phi, weights)

    def expand(self, f: np.ndarray, theta: np.ndarray, phi: np.ndarray,
               weights: np.ndarray = None, reg_lambda: float = 0.0,
               reg_order: int = 2) -> dict:
        f = np.asarray(f, dtype=np.complex128)
        theta = np.asarray(theta, dtype=np.float64)
        phi = np.asarray(phi, dtype=np.float64)

        coefficients = {}
        n_coeffs = (self.l_max + 1) ** 2

        if reg_lambda > 0:
            ylm_matrix = np.zeros((f.size, n_coeffs), dtype=np.complex128)
            idx = 0
            for l in range(self.l_max + 1):
                for m in range(-l, l + 1):
                    ylm_matrix[:, idx] = self.Ylm(l, m, theta, phi).flatten()
                    idx += 1

            ylm_H = np.conj(ylm_matrix.T)
            regularization_matrix = np.zeros((n_coeffs, n_coeffs), dtype=np.complex128)
            idx = 0
            for l in range(self.l_max + 1):
                reg_factor = (l * (l + 1)) ** reg_order
                for m in range(-l, l + 1):
                    regularization_matrix[idx, idx] = reg_lambda * reg_factor
                    idx += 1

            lhs = ylm_H @ ylm_matrix + regularization_matrix
            rhs = ylm_H @ f.flatten()

            coeff_array = np.linalg.solve(lhs, rhs)
            coefficients = self.array_to_coefficients(coeff_array)
        else:
            for l in range(self.l_max + 1):
                coefficients[l] = {}
                for m in range(-l, l + 1):
                    ylm_conj = np.conj(self.Ylm(l, m, theta, phi))
                    integrand = f * ylm_conj
                    coefficients[l][m] = self.spherical_integral(integrand, theta, phi, weights)

        return coefficients

    def expand_tikhonov(self, f: np.ndarray, theta: np.ndarray, phi: np.ndarray,
                        reg_lambda: float = 1e-6, reg_order: int = 2,
                        weights: np.ndarray = None) -> dict:
        return self.expand(f, theta, phi, weights, reg_lambda, reg_order)

    def coefficients_to_array(self, coefficients: dict) -> np.ndarray:
        n_coeffs = (self.l_max + 1) ** 2
        coeff_array = np.zeros(n_coeffs, dtype=np.complex128)
        idx = 0
        for l in range(self.l_max + 1):
            for m in range(-l, l + 1):
                coeff_array[idx] = coefficients[l][m]
                idx += 1
        return coeff_array

    def array_to_coefficients(self, coeff_array: np.ndarray) -> dict:
        coefficients = {}
        idx = 0
        for l in range(self.l_max + 1):
            coefficients[l] = {}
            for m in range(-l, l + 1):
                coefficients[l][m] = coeff_array[idx]
                idx += 1
        return coefficients

    def reconstruct(self, coefficients: dict, theta: np.ndarray, phi: np.ndarray,
                     l_max_reconstruct: int = None) -> np.ndarray:
        theta = np.asarray(theta, dtype=np.float64)
        phi = np.asarray(phi, dtype=np.float64)

        if l_max_reconstruct is None:
            l_max_reconstruct = self.l_max
        l_max_reconstruct = min(l_max_reconstruct, self.l_max)

        result = np.zeros_like(theta, dtype=np.complex128)
        for l in range(l_max_reconstruct + 1):
            for m in range(-l, l + 1):
                result += coefficients[l][m] * self.Ylm(l, m, theta, phi)

        return result

    def power_spectrum(self, coefficients: dict) -> np.ndarray:
        power = np.zeros(self.l_max + 1)
        for l in range(self.l_max + 1):
            for m in range(-l, l + 1):
                power[l] += np.abs(coefficients[l][m]) ** 2
            power[l] /= (2 * l + 1)
        return power

    def cross_spectrum(self, coeffs1: dict, coeffs2: dict) -> np.ndarray:
        cross = np.zeros(self.l_max + 1, dtype=np.complex128)
        for l in range(self.l_max + 1):
            for m in range(-l, l + 1):
                cross[l] += np.conj(coeffs1[l][m]) * coeffs2[l][m]
            cross[l] /= (2 * l + 1)
        return cross


def generate_grid(n_theta: int, n_phi: int) -> tuple:
    theta = np.linspace(0, np.pi, n_theta)
    phi = np.linspace(0, 2 * np.pi, n_phi, endpoint=False)
    theta_grid, phi_grid = np.meshgrid(theta, phi, indexing='ij')
    return theta_grid, phi_grid


def generate_gauss_legendre_grid(n_theta: int, n_phi: int) -> tuple:
    x, weights = roots_legendre(n_theta)
    theta = np.arccos(x)
    phi = np.linspace(0, 2 * np.pi, n_phi, endpoint=False)
    theta_grid, phi_grid = np.meshgrid(theta, phi, indexing='ij')
    weights_grid, _ = np.meshgrid(weights, phi, indexing='ij')
    return theta_grid, phi_grid, weights_grid


def evaluate_on_grid(func, theta_grid: np.ndarray, phi_grid: np.ndarray) -> np.ndarray:
    return func(theta_grid, phi_grid)
