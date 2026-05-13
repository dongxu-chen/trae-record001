import numpy as np
from typing import Union, Tuple, Optional
from abc import ABC, abstractmethod


class GradientDistribution:
    """支持梯度计算的目标分布基类"""

    def log_pdf(self, x: np.ndarray) -> float:
        raise NotImplementedError

    def log_pdf_grad(self, x: np.ndarray) -> np.ndarray:
        raise NotImplementedError


class NormalGradient(GradientDistribution):
    """支持梯度计算的多维正态分布"""

    def __init__(
        self,
        mean: Union[float, np.ndarray],
        cov: Union[float, np.ndarray]
    ):
        self.mean = np.asarray(mean)
        self.cov = np.atleast_2d(cov)
        self.dim = self.mean.size
        self.inv_cov = np.linalg.inv(self.cov)
        self.det_cov = np.linalg.det(self.cov)

    def log_pdf(self, x: np.ndarray) -> float:
        x = np.asarray(x)
        diff = x - self.mean
        return -0.5 * (
            self.dim * np.log(2 * np.pi) +
            np.log(self.det_cov) +
            diff @ self.inv_cov @ diff
        )

    def log_pdf_grad(self, x: np.ndarray) -> np.ndarray:
        x = np.asarray(x)
        diff = x - self.mean
        return -self.inv_cov @ diff


class BananaGradient(GradientDistribution):
    """支持梯度计算的香蕉形分布"""

    def __init__(self, a: float = 1.0, b: float = 0.1):
        self.a = a
        self.b = b
        self.dim = 2

    def log_pdf(self, x: np.ndarray) -> float:
        x = np.asarray(x)
        x1, x2 = x[0], x[1]
        return -0.5 * (x1 ** 2 / self.a ** 2) - 0.5 * ((x2 - self.b * (x1 ** 2 - self.a ** 2)) ** 2)

    def log_pdf_grad(self, x: np.ndarray) -> np.ndarray:
        x = np.asarray(x)
        x1, x2 = x[0], x[1]
        
        dx1 = -x1 / self.a ** 2 + 2 * self.b * x1 * (x2 - self.b * (x1 ** 2 - self.a ** 2))
        dx2 = -(x2 - self.b * (x1 ** 2 - self.a ** 2))
        
        return np.array([dx1, dx2])


class MixtureGradient(GradientDistribution):
    """支持梯度计算的高斯混合分布"""

    def __init__(
        self,
        weights: np.ndarray,
        means: list,
        covs: list
    ):
        self.weights = np.asarray(weights)
        self.weights /= self.weights.sum()
        self.n_components = len(self.weights)
        self.means = [np.asarray(m) for m in means]
        self.covs = [np.atleast_2d(c) for c in covs]
        self.dim = self.means[0].size
        self.inv_covs = [np.linalg.inv(c) for c in self.covs]
        self.det_covs = [np.linalg.det(c) for c in self.covs]

    def log_pdf(self, x: np.ndarray) -> float:
        x = np.asarray(x)
        log_probs = []
        for w, m, inv_c, det_c in zip(
            self.weights, self.means, self.inv_covs, self.det_covs
        ):
            diff = x - m
            log_p = (
                -0.5 * self.dim * np.log(2 * np.pi) -
                0.5 * np.log(det_c) -
                0.5 * (diff @ inv_c @ diff)
            )
            log_probs.append(np.log(w) + log_p)
        max_log = max(log_probs)
        return max_log + np.log(sum(np.exp(lp - max_log) for lp in log_probs))

    def log_pdf_grad(self, x: np.ndarray) -> np.ndarray:
        x = np.asarray(x)
        
        component_log_probs = []
        component_grads = []
        
        for w, m, inv_c, det_c in zip(
            self.weights, self.means, self.inv_covs, self.det_covs
        ):
            diff = x - m
            log_p = (
                -0.5 * self.dim * np.log(2 * np.pi) -
                0.5 * np.log(det_c) -
                0.5 * (diff @ inv_c @ diff)
            )
            component_log_probs.append(np.log(w) + log_p)
            component_grads.append(-inv_c @ diff)
        
        component_log_probs = np.array(component_log_probs)
        component_grads = np.array(component_grads)
        
        max_log = np.max(component_log_probs)
        exp_probs = np.exp(component_log_probs - max_log)
        weights = exp_probs / np.sum(exp_probs)
        
        grad = np.zeros(self.dim)
        for i in range(self.n_components):
            grad += weights[i] * component_grads[i]
        
        return grad


def numerical_gradient(
    func,
    x: np.ndarray,
    eps: float = 1e-5
) -> np.ndarray:
    """数值梯度（中心差分）"""
    x = np.asarray(x, dtype=float)
    dim = x.size
    grad = np.zeros(dim)
    
    for i in range(dim):
        x_plus = x.copy()
        x_plus[i] += eps
        x_minus = x.copy()
        x_minus[i] -= eps
        
        grad[i] = (func(x_plus) - func(x_minus)) / (2 * eps)
    
    return grad


class HamiltonianMonteCarlo:
    """Hamiltonian Monte Carlo 采样器"""

    def __init__(
        self,
        target: GradientDistribution,
        step_size: float = 0.1,
        n_steps: int = 10,
        mass_matrix: Optional[np.ndarray] = None
    ):
        self.target = target
        self.step_size = step_size
        self.n_steps = n_steps
        self.dim = target.dim
        
        if mass_matrix is None:
            self.mass_matrix = np.eye(self.dim)
        else:
            self.mass_matrix = np.asarray(mass_matrix)
        
        self.inv_mass = np.linalg.inv(self.mass_matrix)
        
        self.current = None
        self.current_log_pdf = None
        self.accepted = 0
        self.total = 0

    def _kinetic_energy(self, p: np.ndarray) -> float:
        return 0.5 * p @ self.inv_mass @ p

    def _leapfrog(
        self,
        q: np.ndarray,
        p: np.ndarray
    ) -> Tuple[np.ndarray, np.ndarray]:
        q = q.copy()
        p = p.copy()
        
        grad = self.target.log_pdf_grad(q)
        p = p + 0.5 * self.step_size * grad
        
        for _ in range(self.n_steps):
            q = q + self.step_size * self.inv_mass @ p
            grad = self.target.log_pdf_grad(q)
            p = p + self.step_size * grad
        
        p = p - 0.5 * self.step_size * grad
        
        return q, p

    def step(self, initial: Optional[np.ndarray] = None) -> Tuple[np.ndarray, bool]:
        if initial is not None:
            self.current = np.asarray(initial).copy()
            self.current_log_pdf = self.target.log_pdf(self.current)
        
        q0 = self.current.copy()
        p0 = np.random.multivariate_normal(np.zeros(self.dim), self.mass_matrix)
        
        q, p = self._leapfrog(q0, p0)
        
        current_H = -self.current_log_pdf + self._kinetic_energy(p0)
        proposed_log_pdf = self.target.log_pdf(q)
        proposed_H = -proposed_log_pdf + self._kinetic_energy(p)
        
        log_alpha = current_H - proposed_H
        
        accepted = np.log(np.random.uniform()) < log_alpha
        
        if accepted:
            self.current = q
            self.current_log_pdf = proposed_log_pdf
            self.accepted += 1
        
        self.total += 1
        return self.current.copy(), accepted

    def sample(
        self,
        n_samples: int,
        initial: np.ndarray,
        burn_in: int = 0,
        thin: int = 1
    ) -> np.ndarray:
        self.current = np.asarray(initial).copy()
        self.current_log_pdf = self.target.log_pdf(self.current)
        self.accepted = 0
        self.total = 0
        
        samples = []
        
        for i in range(burn_in + n_samples * thin):
            sample, _ = self.step()
            if i >= burn_in and (i - burn_in) % thin == 0:
                samples.append(sample)
        
        return np.array(samples)

    def acceptance_rate(self) -> float:
        if self.total == 0:
            return 0.0
        return self.accepted / self.total
