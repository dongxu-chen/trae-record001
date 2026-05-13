import numpy as np
from abc import ABC, abstractmethod
from typing import Union


class Proposal(ABC):
    """提议分布抽象基类"""

    @abstractmethod
    def propose(self, current: np.ndarray) -> np.ndarray:
        pass

    @abstractmethod
    def log_transition_prob(
        self, current: np.ndarray, proposed: np.ndarray
    ) -> float:
        pass

    @property
    @abstractmethod
    def is_symmetric(self) -> bool:
        pass


class NormalProposal(Proposal):
    """多维正态提议分布（随机游走）"""

    def __init__(
        self,
        scale: Union[float, np.ndarray] = 1.0
    ):
        self.scale = np.asarray(scale)

    def propose(self, current: np.ndarray) -> np.ndarray:
        current = np.asarray(current)
        return current + np.random.normal(0, self.scale, size=current.shape)

    def log_transition_prob(
        self, current: np.ndarray, proposed: np.ndarray
    ) -> float:
        current = np.asarray(current)
        proposed = np.asarray(proposed)
        diff = proposed - current
        dim = current.size
        scale_sq = self.scale ** 2
        log_p = (
            -0.5 * dim * np.log(2 * np.pi) -
            0.5 * dim * np.log(scale_sq) -
            0.5 * np.sum(diff ** 2) / scale_sq
        )
        return log_p

    @property
    def is_symmetric(self) -> bool:
        return True


class UniformProposal(Proposal):
    """多维均匀提议分布（Metropolis算法）"""

    def __init__(
        self,
        width: Union[float, np.ndarray] = 1.0
    ):
        self.width = np.asarray(width)
        self.half_width = self.width / 2.0

    def propose(self, current: np.ndarray) -> np.ndarray:
        current = np.asarray(current)
        return current + np.random.uniform(
            -self.half_width, self.half_width, size=current.shape
        )

    def log_transition_prob(
        self, current: np.ndarray, proposed: np.ndarray
    ) -> float:
        current = np.asarray(current)
        proposed = np.asarray(proposed)
        diff = np.abs(proposed - current)
        if np.all(diff <= self.half_width):
            return -np.sum(np.log(self.width))
        return -np.inf

    @property
    def is_symmetric(self) -> bool:
        return True


class IndependentNormalProposal(Proposal):
    """独立正态提议分布（不依赖当前状态）"""

    def __init__(
        self,
        mean: Union[float, np.ndarray] = 0.0,
        cov: Union[float, np.ndarray] = 1.0
    ):
        self.mean = np.asarray(mean)
        self.cov = np.atleast_2d(cov)
        self.dim = self.mean.size
        self.inv_cov = np.linalg.inv(self.cov)
        self.det_cov = np.linalg.det(self.cov)

    def propose(self, current: np.ndarray) -> np.ndarray:
        return np.random.multivariate_normal(self.mean, self.cov)

    def log_transition_prob(
        self, current: np.ndarray, proposed: np.ndarray
    ) -> float:
        current = np.asarray(current)
        proposed = np.asarray(proposed)
        diff = proposed - self.mean
        log_p = (
            -0.5 * self.dim * np.log(2 * np.pi) -
            0.5 * np.log(self.det_cov) -
            0.5 * (diff @ self.inv_cov @ diff)
        )
        return log_p

    @property
    def is_symmetric(self) -> bool:
        return False


class NUTS:
    """No-U-Turn Sampler (NUTS)"""

    def __init__(
        self,
        target,
        step_size: float = 0.1,
        max_tree_depth: int = 10,
        mass_matrix=None
    ):
        self.target = target
        self.step_size = step_size
        self.max_tree_depth = max_tree_depth
        self.dim = target.dim
        
        if mass_matrix is None:
            self.mass_matrix = np.eye(self.dim)
        else:
            self.mass_matrix = np.asarray(mass_matrix)
        
        self.inv_mass = np.linalg.inv(self.mass_matrix)
        self._divergent_count = 0
        self._tree_depth_count = 0
        self.current = None
        self.current_log_pdf = None
        self.accepted = 0
        self.total = 0

    def _kinetic_energy(self, p: np.ndarray) -> float:
        return 0.5 * p @ self.inv_mass @ p

    def _leapfrog(
        self,
        q: np.ndarray,
        p: np.ndarray,
        eps: float
    ):
        q = q.copy()
        p = p.copy()
        
        grad = self.target.log_pdf_grad(q)
        p += 0.5 * eps * grad
        
        q += eps * self.inv_mass @ p
        grad = self.target.log_pdf_grad(q)
        p += eps * grad
        
        q += eps * self.inv_mass @ p
        grad = self.target.log_pdf_grad(q)
        p += 0.5 * eps * grad
        
        return q, p

    def _build_tree(
        self,
        q: np.ndarray,
        p: np.ndarray,
        u: float,
        v: int,
        j: int
    ):
        if j == 0:
            q_prime, p_prime = self._leapfrog(q, p, v * self.step_size)
            log_pdf_prime = self.target.log_pdf(q_prime)
            H_prime = -log_pdf_prime + self._kinetic_energy(p_prime)
            H = -self.target.log_pdf(q) + self._kinetic_energy(p)
            
            n_prime = int(u <= np.exp(H - H_prime))
            s_prime = int(u < np.exp(100 + H - H_prime))
            
            return q_prime, p_prime, q_prime, p_prime, q_prime, n_prime, s_prime, 1
        
        q_minus, p_minus, q_plus, p_plus, q_prime, n_prime, s_prime, alpha_prime = \
            self._build_tree(q, p, u, v, j - 1)
        
        if s_prime == 1:
            if v == -1:
                q_minus, p_minus, _, _, q_double_prime, n_double_prime, s_double_prime, alpha_double = \
                    self._build_tree(q_minus, p_minus, u, v, j - 1)
            else:
                _, _, q_plus, p_plus, q_double_prime, n_double_prime, s_double_prime, alpha_double = \
                    self._build_tree(q_plus, p_plus, u, v, j - 1)
            
            if s_double_prime == 1 and np.random.uniform() < n_double_prime / (n_prime + n_double_prime):
                q_prime = q_double_prime
            
            n_prime += n_double_prime
            
            s_prime = s_double_prime * int(
                np.dot(q_plus - q_minus, p_minus) >= 0 and
                np.dot(q_plus - q_minus, p_plus) >= 0
            )
            
            alpha_prime += alpha_double
        
        return q_minus, p_minus, q_plus, p_plus, q_prime, n_prime, s_prime, alpha_prime

    def step(self, initial=None) -> np.ndarray:
        """执行一次 NUTS 迭代"""
        if initial is not None:
            self.current = np.asarray(initial).copy()
            self.current_log_pdf = self.target.log_pdf(self.current)
        
        q0 = self.current.copy()
        p0 = np.random.multivariate_normal(np.zeros(self.dim), self.mass_matrix)
        u = np.random.uniform(0, np.exp(-self._kinetic_energy(p0) + self.current_log_pdf))
        
        q_minus, q_plus = q0.copy(), q0.copy()
        p_minus, p_plus = p0.copy(), p0.copy()
        j = 0
        n = 1
        s = 1
        q_new = q0.copy()
        
        while s == 1 and j < self.max_tree_depth:
            v = 1 if np.random.uniform() < 0.5 else -1
            
            if v == -1:
                q_minus, p_minus, _, _, q_prime, n_prime, s_prime, _ = \
                    self._build_tree(q_minus, p_minus, u, v, j)
            else:
                _, _, q_plus, p_plus, q_prime, n_prime, s_prime, _ = \
                    self._build_tree(q_plus, p_plus, u, v, j)
            
            if s_prime == 1 and np.random.uniform() < n_prime / n:
                q_new = q_prime
            
            n += n_prime
            
            s = s_prime * int(
                np.dot(q_plus - q_minus, p_minus) >= 0 and
                np.dot(q_plus - q_minus, p_plus) >= 0
            )
            j += 1
        
        if s == 0:
            self._divergent_count += 1
        
        self._tree_depth_count = j
        self.current = q_new
        self.current_log_pdf = self.target.log_pdf(q_new)
        self.accepted += 1
        self.total += 1
        
        return self.current.copy()

    def sample(
        self,
        n_samples: int,
        initial: np.ndarray,
        burn_in: int = 0,
        thin: int = 1
    ) -> np.ndarray:
        """执行 NUTS 采样"""
        self.current = np.asarray(initial).copy()
        self.current_log_pdf = self.target.log_pdf(self.current)
        self.accepted = 0
        self.total = 0
        
        samples = []
        
        for i in range(burn_in + n_samples * thin):
            sample = self.step()
            if i >= burn_in and (i - burn_in) % thin == 0:
                samples.append(sample)
        
        return np.array(samples)

    def acceptance_rate(self) -> float:
        if self.total == 0:
            return 0.0
        return 1.0

