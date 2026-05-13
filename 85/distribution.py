import numpy as np
from abc import ABC, abstractmethod
from typing import Union, Tuple


class Distribution(ABC):
    """目标分布抽象基类"""

    @abstractmethod
    def log_pdf(self, x: np.ndarray) -> float:
        pass

    def pdf(self, x: np.ndarray) -> float:
        return np.exp(self.log_pdf(x))


class NormalDistribution(Distribution):
    """多维正态分布作为目标分布"""

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


class UniformDistribution(Distribution):
    """多维均匀分布"""

    def __init__(
        self,
        low: Union[float, np.ndarray],
        high: Union[float, np.ndarray]
    ):
        self.low = np.asarray(low)
        self.high = np.asarray(high)
        self.dim = self.low.size
        self.volume = np.prod(self.high - self.low)

    def log_pdf(self, x: np.ndarray) -> float:
        x = np.asarray(x)
        if np.all(x >= self.low) and np.all(x <= self.high):
            return -np.log(self.volume)
        return -np.inf


class MixtureOfNormals(Distribution):
    """高斯混合分布"""

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


class BananaDistribution(Distribution):
    """香蕉形分布，用于测试MCMC"""

    def __init__(self, a: float = 1.0, b: float = 0.1):
        self.a = a
        self.b = b

    def log_pdf(self, x: np.ndarray) -> float:
        x = np.asarray(x)
        x1, x2 = x[0], x[1]
        log_p = (
            -0.5 * (x1 ** 2 / self.a ** 2) +
            -0.5 * ((x2 - self.b * (x1 ** 2 - self.a ** 2)) ** 2)
        )
        return log_p
