import numpy as np


class EulerFlux:
    def __init__(self, gamma=1.4, dim=1):
        self.gamma = gamma
        self.gamma1 = gamma - 1.0
        self.dim = dim

    def conservative_from_primitive(self, rho, u, p, v=0.0):
        if self.dim == 1:
            rho_u = rho * u
            E = p / self.gamma1 + 0.5 * rho * u**2
            return np.array([rho, rho_u, E], dtype=np.float64)
        else:
            rho_u = rho * u
            rho_v = rho * v
            E = p / self.gamma1 + 0.5 * rho * (u**2 + v**2)
            return np.array([rho, rho_u, rho_v, E], dtype=np.float64)

    def primitive_from_conservative(self, U):
        if self.dim == 1:
            rho = U[0]
            u = U[1] / rho
            E = U[2]
            p = self.gamma1 * (E - 0.5 * rho * u**2)
            return np.array([rho, u, p], dtype=np.float64)
        else:
            rho = U[0]
            u = U[1] / rho
            v = U[2] / rho
            E = U[3]
            p = self.gamma1 * (E - 0.5 * rho * (u**2 + v**2))
            return np.array([rho, u, v, p], dtype=np.float64)

    def flux_from_conservative(self, U):
        if self.dim == 1:
            rho = U[0]
            rho_u = U[1]
            E = U[2]
            u = rho_u / rho
            p = self.gamma1 * (E - 0.5 * rho * u**2)
            F = np.zeros_like(U)
            F[0] = rho_u
            F[1] = rho_u * u + p
            F[2] = u * (E + p)
            return F
        else:
            Fx = np.zeros_like(U)
            Fy = np.zeros_like(U)

            rho = U[0]
            rho_u = U[1]
            rho_v = U[2]
            E = U[3]
            u = rho_u / rho
            v = rho_v / rho
            p = self.gamma1 * (E - 0.5 * rho * (u**2 + v**2))

            Fx[0] = rho_u
            Fx[1] = rho_u * u + p
            Fx[2] = rho_u * v
            Fx[3] = u * (E + p)

            Fy[0] = rho_v
            Fy[1] = rho_u * v
            Fy[2] = rho_v * v + p
            Fy[3] = v * (E + p)

            return Fx, Fy

    def flux_from_primitive(self, rho, u, p, v=0.0):
        if self.dim == 1:
            E = p / self.gamma1 + 0.5 * rho * u**2
            F = np.zeros(3)
            F[0] = rho * u
            F[1] = rho * u**2 + p
            F[2] = u * (E + p)
            return F
        else:
            E = p / self.gamma1 + 0.5 * rho * (u**2 + v**2)
            Fx = np.zeros(4)
            Fy = np.zeros(4)

            Fx[0] = rho * u
            Fx[1] = rho * u**2 + p
            Fx[2] = rho * u * v
            Fx[3] = u * (E + p)

            Fy[0] = rho * v
            Fy[1] = rho * u * v
            Fy[2] = rho * v**2 + p
            Fy[3] = v * (E + p)

            return Fx, Fy

    def speed_of_sound(self, rho, p):
        return np.sqrt(self.gamma * p / rho)

    def wavespeeds_from_primitive(self, rho, u, p, v=0.0):
        c = self.speed_of_sound(rho, p)
        if self.dim == 1:
            return np.array([u - c, u, u + c], dtype=np.float64)
        else:
            return np.array([u - c, u, u, u + c], dtype=np.float64)

    def rotate_to_normal(self, U, normal):
        if self.dim == 1:
            return U

        nx, ny = normal
        W = self.primitive_from_conservative(U)
        rho, u, v, p = W

        u_n = u * nx + v * ny
        u_t = -u * ny + v * nx

        return self.conservative_from_primitive(rho, u_n, p, u_t)

    def rotate_from_normal(self, U, normal):
        if self.dim == 1:
            return U

        nx, ny = normal
        W = self.primitive_from_conservative(U)
        rho, u_n, u_t, p = W

        u = u_n * nx - u_t * ny
        v = u_n * ny + u_t * nx

        return self.conservative_from_primitive(rho, u, p, v)

    def rotate_flux_to_cartesian(self, F_rotated, normal):
        if self.dim == 1:
            return F_rotated

        F = F_rotated
        nx, ny = normal

        F_cart = np.zeros_like(F)
        F_cart[0] = F[0]
        F_cart[1] = F[1] * nx - F[2] * ny
        F_cart[2] = F[1] * ny + F[2] * nx
        F_cart[3] = F[3]

        return F_cart


class RoeSolver(EulerFlux):
    def __init__(self, gamma=1.4, fix_entropy=True):
        super().__init__(gamma)
        self.fix_entropy = fix_entropy

    def solve(self, U_L, U_R):
        if U_L.ndim == 2:
            return self._solve_vectorized(U_L, U_R)
        return self._solve_single(U_L, U_R)

    def _solve_single(self, U_L, U_R):
        W_L = self.primitive_from_conservative(U_L)
        W_R = self.primitive_from_conservative(U_R)

        rho_L, u_L, p_L = W_L
        rho_R, u_R, p_R = W_R

        sqrt_rho_L = np.sqrt(rho_L)
        sqrt_rho_R = np.sqrt(rho_R)
        sqrt_sum = sqrt_rho_L + sqrt_rho_R

        rho_tilde = sqrt_rho_L * sqrt_rho_R
        u_tilde = (sqrt_rho_L * u_L + sqrt_rho_R * u_R) / sqrt_sum
        H_tilde = (
            sqrt_rho_L * (self.gamma * p_L / rho_L / self.gamma1 + 0.5 * u_L**2) +
            sqrt_rho_R * (self.gamma * p_R / rho_R / self.gamma1 + 0.5 * u_R**2)
        ) / sqrt_sum

        c_tilde = np.sqrt(self.gamma1 * (H_tilde - 0.5 * u_tilde**2))

        drho = rho_R - rho_L
        du = u_R - u_L
        dp = p_R - p_L

        alpha1 = (dp - rho_tilde * c_tilde * du) / (2.0 * c_tilde**2)
        alpha2 = drho - dp / c_tilde**2
        alpha3 = (dp + rho_tilde * c_tilde * du) / (2.0 * c_tilde**2)

        R = np.array([
            [1.0, 1.0, 1.0],
            [u_tilde - c_tilde, u_tilde, u_tilde + c_tilde],
            [H_tilde - u_tilde * c_tilde, 0.5 * u_tilde**2, H_tilde + u_tilde * c_tilde]
        ])

        lambda_hat = np.array([
            u_tilde - c_tilde,
            u_tilde,
            u_tilde + c_tilde
        ])

        F_L = self.flux_from_conservative(U_L)
        F_R = self.flux_from_conservative(U_R)

        if self.fix_entropy:
            c_L = self.speed_of_sound(rho_L, p_L)
            c_R = self.speed_of_sound(rho_R, p_R)
            lambda_L = np.array([u_L - c_L, u_L, u_L + c_L])
            lambda_R = np.array([u_R - c_R, u_R, u_R + c_R])

            lambda_hat_fixed = np.zeros(3)
            for k in range(3):
                if lambda_hat[k] >= lambda_R[k]:
                    lambda_hat_fixed[k] = lambda_R[k]
                elif lambda_hat[k] <= lambda_L[k]:
                    lambda_hat_fixed[k] = lambda_L[k]
                elif (lambda_L[k] <= 0.0) and (0.0 <= lambda_R[k]):
                    lambda_hat_fixed[k] = lambda_hat[k] * (lambda_R[k] - lambda_L[k]) / \
                        (lambda_hat[k] - lambda_L[k] + lambda_R[k] - lambda_hat[k])
                else:
                    lambda_hat_fixed[k] = lambda_hat[k]
            lambda_abs = np.abs(lambda_hat_fixed)
        else:
            lambda_abs = np.abs(lambda_hat)

        delta_F = R @ (alpha1 * lambda_abs[0] * np.eye(3)[:, 0] +
                       alpha2 * lambda_abs[1] * np.eye(3)[:, 1] +
                       alpha3 * lambda_abs[2] * np.eye(3)[:, 2])

        return 0.5 * (F_L + F_R - delta_F)

    def _solve_vectorized(self, U_L, U_R):
        n = U_L.shape[1]
        F = np.zeros_like(U_L)

        for i in range(n):
            F[:, i] = self._solve_single(U_L[:, i], U_R[:, i])

        return F


class HLLSolver(EulerFlux):
    def __init__(self, gamma=1.4):
        super().__init__(gamma)

    def compute_wave_speeds(self, W_L, W_R):
        rho_L, u_L, p_L = W_L
        rho_R, u_R, p_R = W_R

        c_L = self.speed_of_sound(rho_L, p_L)
        c_R = self.speed_of_sound(rho_R, p_R)

        p_star = 0.5 * (p_L + p_R) - 0.125 * (rho_L + rho_R) * (c_L + c_R) * (u_R - u_L)

        if p_star >= p_L:
            q_L = np.sqrt(1.0 + (self.gamma + 1.0) / (2.0 * self.gamma) * (p_star / p_L - 1.0))
        else:
            q_L = 1.0

        if p_star >= p_R:
            q_R = np.sqrt(1.0 + (self.gamma + 1.0) / (2.0 * self.gamma) * (p_star / p_R - 1.0))
        else:
            q_R = 1.0

        S_L = u_L - c_L * q_L
        S_R = u_R + c_R * q_R

        return S_L, S_R

    def solve(self, U_L, U_R):
        if U_L.ndim == 2:
            return self._solve_vectorized(U_L, U_R)
        return self._solve_single(U_L, U_R)

    def _solve_single(self, U_L, U_R):
        W_L = self.primitive_from_conservative(U_L)
        W_R = self.primitive_from_conservative(U_R)

        S_L, S_R = self.compute_wave_speeds(W_L, W_R)

        F_L = self.flux_from_conservative(U_L)
        F_R = self.flux_from_conservative(U_R)

        if S_L >= 0.0:
            return F_L
        elif S_R <= 0.0:
            return F_R
        else:
            return (S_R * F_L - S_L * F_R + S_L * S_R * (U_R - U_L)) / (S_R - S_L)

    def _solve_vectorized(self, U_L, U_R):
        n = U_L.shape[1]
        F = np.zeros_like(U_L)

        for i in range(n):
            F[:, i] = self._solve_single(U_L[:, i], U_R[:, i])

        return F


class HLLCSolver(EulerFlux):
    def __init__(self, gamma=1.4):
        super().__init__(gamma)

    def _estimate_pm(self, W_L, W_R):
        rho_L, u_L, p_L = W_L
        rho_R, u_R, p_R = W_R
        c_L = self.speed_of_sound(rho_L, p_L)
        c_R = self.speed_of_sound(rho_R, p_R)

        q_L = rho_L * c_L
        q_R = rho_R * c_R

        p_pvrs = 0.5 * (p_L + p_R) + 0.5 * (u_L - u_R) * (q_L + q_R)
        p_star = max(p_pvrs, 0.0)

        return p_star

    def _compute_wave_speeds(self, W_L, W_R, p_star):
        rho_L, u_L, p_L = W_L
        rho_R, u_R, p_R = W_R
        c_L = self.speed_of_sound(rho_L, p_L)
        c_R = self.speed_of_sound(rho_R, p_R)
        gamma = self.gamma

        if p_star > p_L:
            f_L = np.sqrt(1.0 + (gamma + 1.0) / (2.0 * gamma) * (p_star / p_L - 1.0))
        else:
            f_L = 1.0

        if p_star > p_R:
            f_R = np.sqrt(1.0 + (gamma + 1.0) / (2.0 * gamma) * (p_star / p_R - 1.0))
        else:
            f_R = 1.0

        S_L = u_L - c_L * f_L
        S_R = u_R + c_R * f_R

        return S_L, S_R

    def solve(self, U_L, U_R):
        if U_L.ndim == 2:
            return self._solve_vectorized(U_L, U_R)
        return self._solve_single(U_L, U_R)

    def _solve_single(self, U_L, U_R):
        W_L = self.primitive_from_conservative(U_L)
        W_R = self.primitive_from_conservative(U_R)

        rho_L, u_L, p_L = W_L
        rho_R, u_R, p_R = W_R

        c_L = self.speed_of_sound(rho_L, p_L)
        c_R = self.speed_of_sound(rho_R, p_R)
        gamma = self.gamma
        gamma1 = self.gamma1

        F_L = self.flux_from_conservative(U_L)
        F_R = self.flux_from_conservative(U_R)

        if u_L + c_L <= 0.0:
            return F_L
        if u_R - c_R >= 0.0:
            return F_R

        q_L = rho_L * c_L
        q_R = rho_R * c_R

        p_star = 0.5 * (p_L + p_R) + 0.5 * (u_L - u_R) * (q_L + q_R)
        p_star = max(p_star, 0.0)

        if p_star > p_L:
            f_L = np.sqrt(1.0 + (gamma + 1.0) / (2.0 * gamma) * (p_star / p_L - 1.0))
        else:
            f_L = 1.0

        if p_star > p_R:
            f_R = np.sqrt(1.0 + (gamma + 1.0) / (2.0 * gamma) * (p_star / p_R - 1.0))
        else:
            f_R = 1.0

        S_L = u_L - c_L * f_L
        S_R = u_R + c_R * f_R

        if S_L >= 0.0:
            return F_L
        if S_R <= 0.0:
            return F_R

        S_star = (p_R - p_L + rho_L * u_L * (S_L - u_L) - rho_R * u_R * (S_R - u_R)) / \
                 (rho_L * (S_L - u_L) - rho_R * (S_R - u_R))

        if S_star >= 0.0:
            dU_L = np.array([
                1.0,
                S_star,
                U_L[2] / U_L[0] + (S_star - u_L) * (S_star + p_L / (rho_L * (S_L - u_L)))
            ])
            coeff_L = rho_L * (S_L - u_L) / (S_L - S_star)
            U_star_L = coeff_L * dU_L
            return F_L + S_L * (U_star_L - U_L)
        else:
            dU_R = np.array([
                1.0,
                S_star,
                U_R[2] / U_R[0] + (S_star - u_R) * (S_star + p_R / (rho_R * (S_R - u_R)))
            ])
            coeff_R = rho_R * (S_R - u_R) / (S_R - S_star)
            U_star_R = coeff_R * dU_R
            return F_R + S_R * (U_star_R - U_R)

    def _solve_vectorized(self, U_L, U_R):
        n = U_L.shape[1]
        F = np.zeros_like(U_L)

        for i in range(n):
            F[:, i] = self._solve_single(U_L[:, i], U_R[:, i])

        return F


class LaxFriedrichsSolver(EulerFlux):
    def __init__(self, gamma=1.4):
        super().__init__(gamma)

    def solve(self, U_L, U_R):
        if U_L.ndim == 2:
            return self._solve_vectorized(U_L, U_R)
        return self._solve_single(U_L, U_R)

    def _solve_single(self, U_L, U_R):
        W_L = self.primitive_from_conservative(U_L)
        W_R = self.primitive_from_conservative(U_R)

        rho_L, u_L, p_L = W_L
        rho_R, u_R, p_R = W_R

        c_L = self.speed_of_sound(rho_L, p_L)
        c_R = self.speed_of_sound(rho_R, p_R)

        max_speed = max(abs(u_L) + c_L, abs(u_R) + c_R)

        F_L = self.flux_from_conservative(U_L)
        F_R = self.flux_from_conservative(U_R)

        return 0.5 * (F_L + F_R - max_speed * (U_R - U_L))

    def _solve_vectorized(self, U_L, U_R):
        n = U_L.shape[1]
        F = np.zeros_like(U_L)

        for i in range(n):
            F[:, i] = self._solve_single(U_L[:, i], U_R[:, i])

        return F


def create_flux_solver(solver_type='roe', gamma=1.4, **kwargs):
    if solver_type == 'roe':
        return RoeSolver(gamma=gamma, **kwargs)
    elif solver_type == 'hll':
        return HLLSolver(gamma=gamma)
    elif solver_type == 'hllc':
        return HLLCSolver(gamma=gamma)
    elif solver_type == 'lax':
        return LaxFriedrichsSolver(gamma=gamma)
    else:
        raise ValueError(f"Unknown flux solver type: {solver_type}")


class EdgeFlux2D:
    def __init__(self, base_solver):
        self.base = base_solver
        self.gamma = base_solver.gamma
        self.gamma1 = base_solver.gamma1
        self.dim = 2

    def _convert_to_1d_solver_input(self, U):
        if len(U) == 4:
            rho = U[0]
            u = U[1] / rho
            v = U[2] / rho
            E = U[3]
            p = self.gamma1 * (E - 0.5 * rho * (u**2 + v**2))
            E_1d = p / self.gamma1 + 0.5 * rho * u**2
            return np.array([rho, rho * u, E_1d])
        return U

    def _convert_to_2d_state(self, U_1d, v):
        rho = U_1d[0]
        u = U_1d[1] / rho
        E_1d = U_1d[2]
        p = self.gamma1 * (E_1d - 0.5 * rho * u**2)
        E = p / self.gamma1 + 0.5 * rho * (u**2 + v**2)
        return np.array([rho, rho * u, rho * v, E])

    def solve_edge_flux(self, U_L, U_R, normal, edge_length=1.0):
        nx, ny = normal

        rho_L = U_L[0]
        u_L = U_L[1] / rho_L
        v_L = U_L[2] / rho_L
        E_L = U_L[3]
        p_L = self.gamma1 * (E_L - 0.5 * rho_L * (u_L**2 + v_L**2))

        rho_R = U_R[0]
        u_R = U_R[1] / rho_R
        v_R = U_R[2] / rho_R
        E_R = U_R[3]
        p_R = self.gamma1 * (E_R - 0.5 * rho_R * (u_R**2 + v_R**2))

        u_n_L = u_L * nx + v_L * ny
        u_t_L = -u_L * ny + v_L * nx

        u_n_R = u_R * nx + v_R * ny
        u_t_R = -u_R * ny + v_R * nx

        E_L_rot = p_L / self.gamma1 + 0.5 * rho_L * u_n_L**2
        E_R_rot = p_R / self.gamma1 + 0.5 * rho_R * u_n_R**2

        U_L_rot = np.array([rho_L, rho_L * u_n_L, E_L_rot])
        U_R_rot = np.array([rho_R, rho_R * u_n_R, E_R_rot])

        F_rot_1d = self.base.solve(U_L_rot, U_R_rot)

        F_rot = np.zeros(4)
        F_rot[0] = F_rot_1d[0]
        F_rot[1] = F_rot_1d[1]

        rho_star = F_rot_1d[0]
        if abs(rho_star) > 1e-10:
            u_t_star = (rho_L * u_t_L * max(0.0, u_n_L) + rho_R * u_t_R * max(0.0, -u_n_R)) / \
                       (rho_L * max(0.0, u_n_L) + rho_R * max(0.0, -u_n_R) + 1e-10)
        else:
            u_t_star = 0.5 * (u_t_L + u_t_R)

        F_rot[2] = rho_star * u_t_star
        F_rot[3] = F_rot_1d[2]

        F_cart = np.zeros(4)
        F_cart[0] = F_rot[0]
        F_cart[1] = F_rot[1] * nx - F_rot[2] * ny
        F_cart[2] = F_rot[1] * ny + F_rot[2] * nx
        F_cart[3] = F_rot[3]

        return F_cart * edge_length

    def compute_max_speed(self, U, normal):
        rho = U[0]
        u = U[1] / rho
        v = U[2] / rho
        E = U[3]
        p = self.gamma1 * (E - 0.5 * rho * (u**2 + v**2))

        nx, ny = normal
        u_n = u * nx + v * ny
        c = np.sqrt(self.gamma * p / rho)

        return abs(u_n) + c


class RoeSolver2D(EulerFlux):
    def __init__(self, gamma=1.4, fix_entropy=True):
        super().__init__(gamma, dim=2)
        self.fix_entropy = fix_entropy

    def solve(self, U_L, U_R):
        return self._solve_single(U_L, U_R)

    def _solve_single(self, U_L, U_R):
        W_L = self.primitive_from_conservative(U_L)
        W_R = self.primitive_from_conservative(U_R)

        rho_L, u_L, v_L, p_L = W_L
        rho_R, u_R, v_R, p_R = W_R

        sqrt_rho_L = np.sqrt(rho_L)
        sqrt_rho_R = np.sqrt(rho_R)
        sqrt_sum = sqrt_rho_L + sqrt_rho_R

        rho_tilde = sqrt_rho_L * sqrt_rho_R
        u_tilde = (sqrt_rho_L * u_L + sqrt_rho_R * u_R) / sqrt_sum
        v_tilde = (sqrt_rho_L * v_L + sqrt_rho_R * v_R) / sqrt_sum

        H_L = (self.gamma * p_L / rho_L) / self.gamma1 + 0.5 * (u_L**2 + v_L**2)
        H_R = (self.gamma * p_R / rho_R) / self.gamma1 + 0.5 * (u_R**2 + v_R**2)
        H_tilde = (sqrt_rho_L * H_L + sqrt_rho_R * H_R) / sqrt_sum

        q_tilde = u_tilde**2 + v_tilde**2
        c_tilde = np.sqrt(self.gamma1 * (H_tilde - 0.5 * q_tilde))

        drho = rho_R - rho_L
        du = u_R - u_L
        dv = v_R - v_L
        dp = p_R - p_L

        alpha1 = (dp - rho_tilde * c_tilde * du) / (2.0 * c_tilde**2)
        alpha2 = drho - dp / c_tilde**2
        alpha3 = rho_tilde * dv
        alpha4 = (dp + rho_tilde * c_tilde * du) / (2.0 * c_tilde**2)

        F_L, _ = self.flux_from_conservative(U_L)
        F_R, _ = self.flux_from_conservative(U_R)

        R = np.array([
            [1.0, 1.0, 0.0, 1.0],
            [u_tilde - c_tilde, u_tilde, 0.0, u_tilde + c_tilde],
            [v_tilde, v_tilde, 1.0, v_tilde],
            [H_tilde - u_tilde * c_tilde, 0.5 * q_tilde, v_tilde, H_tilde + u_tilde * c_tilde]
        ])

        lambda_hat = np.array([
            u_tilde - c_tilde,
            u_tilde,
            u_tilde,
            u_tilde + c_tilde
        ])

        lambda_abs = np.abs(lambda_hat)

        delta_F = (R @ (np.diag(lambda_abs) @ np.array([alpha1, alpha2, alpha3, alpha4])))

        return 0.5 * (F_L + F_R - delta_F)

    def solve_edge_flux(self, U_L, U_R, normal, edge_length=1.0):
        nx, ny = normal
        n_mag = np.sqrt(nx**2 + ny**2)
        if n_mag > 0:
            nx = nx / n_mag
            ny = ny / n_mag

        U_L_rot = self._rotate_to_normal(U_L, nx, ny)
        U_R_rot = self._rotate_to_normal(U_R, nx, ny)

        F_rot = self.solve(U_L_rot, U_R_rot)

        F_cart = self._rotate_flux_from_normal(F_rot, nx, ny)

        return F_cart * edge_length

    def _rotate_to_normal(self, U, nx, ny):
        W = self.primitive_from_conservative(U)
        rho, u, v, p = W

        u_n = u * nx + v * ny
        u_t = -u * ny + v * nx

        return self.conservative_from_primitive(rho, u_n, p, u_t)

    def _rotate_flux_from_normal(self, F_rot, nx, ny):
        F_cart = np.zeros(4)
        F_cart[0] = F_rot[0]
        F_cart[1] = F_rot[1] * nx - F_rot[2] * ny
        F_cart[2] = F_rot[1] * ny + F_rot[2] * nx
        F_cart[3] = F_rot[3]
        return F_cart

    def compute_max_speed(self, U, normal):
        rho = U[0]
        u = U[1] / rho
        v = U[2] / rho
        E = U[3]
        p = self.gamma1 * (E - 0.5 * rho * (u**2 + v**2))

        nx, ny = normal
        u_n = u * nx + v * ny
        c = np.sqrt(self.gamma * p / rho)

        return abs(u_n) + c


def create_2d_flux_solver(solver_type='roe', gamma=1.4, **kwargs):
    if solver_type == 'roe':
        return RoeSolver2D(gamma=gamma, **kwargs)
    else:
        base = create_flux_solver(solver_type, gamma=gamma, **kwargs)
        return EdgeFlux2D(base)
