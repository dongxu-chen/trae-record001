import numpy as np
from abc import ABC, abstractmethod


class Kernel(ABC):
    @abstractmethod
    def __call__(self, x1, x2):
        pass

    @abstractmethod
    def set_params(self, params):
        pass

    @abstractmethod
    def get_params(self):
        pass


class RBF(Kernel):
    def __init__(self, length_scale=1.0, sigma_f=1.0):
        self.length_scale = length_scale
        self.sigma_f = sigma_f

    def __call__(self, x1, x2):
        x1 = np.asarray(x1)
        x2 = np.asarray(x2)

        if x1.ndim == 1:
            x1 = x1.reshape(-1, 1)
        if x2.ndim == 1:
            x2 = x2.reshape(-1, 1)

        sqdist = np.sum(x1 ** 2, 1).reshape(-1, 1) + np.sum(x2 ** 2, 1) - 2 * np.dot(x1, x2.T)
        return self.sigma_f ** 2 * np.exp(-0.5 / self.length_scale ** 2 * sqdist)

    def set_params(self, params):
        self.length_scale = params[0]
        if len(params) > 1:
            self.sigma_f = params[1]

    def get_params(self):
        return np.array([self.length_scale, self.sigma_f])


class Linear(Kernel):
    def __init__(self, sigma_b=1.0, sigma_v=1.0, c=0.0):
        self.sigma_b = sigma_b
        self.sigma_v = sigma_v
        self.c = c

    def __call__(self, x1, x2):
        x1 = np.asarray(x1)
        x2 = np.asarray(x2)

        if x1.ndim == 1:
            x1 = x1.reshape(-1, 1)
        if x2.ndim == 1:
            x2 = x2.reshape(-1, 1)

        return self.sigma_b ** 2 + self.sigma_v ** 2 * np.dot(x1 - self.c, (x2 - self.c).T)

    def set_params(self, params):
        self.sigma_b = params[0]
        if len(params) > 1:
            self.sigma_v = params[1]
        if len(params) > 2:
            self.c = params[2]

    def get_params(self):
        return np.array([self.sigma_b, self.sigma_v, self.c])


class WhiteKernel(Kernel):
    def __init__(self, noise_level=1.0):
        self.noise_level = noise_level

    def __call__(self, x1, x2):
        x1 = np.asarray(x1)
        x2 = np.asarray(x2)

        if x1.ndim == 1:
            x1 = x1.reshape(-1, 1)
        if x2.ndim == 1:
            x2 = x2.reshape(-1, 1)

        n1, n2 = x1.shape[0], x2.shape[0]

        if x1 is x2 or np.array_equal(x1, x2):
            return self.noise_level ** 2 * np.eye(n1)
        else:
            return np.zeros((n1, n2))

    def set_params(self, params):
        self.noise_level = params[0]

    def get_params(self):
        return np.array([self.noise_level])


class SumKernel(Kernel):
    def __init__(self, *kernels):
        self.kernels = list(kernels)

    def __call__(self, x1, x2):
        result = self.kernels[0](x1, x2)
        for k in self.kernels[1:]:
            result = result + k(x1, x2)
        return result

    def set_params(self, params):
        idx = 0
        for kernel in self.kernels:
            n_params = len(kernel.get_params())
            kernel.set_params(params[idx:idx + n_params])
            idx += n_params

    def get_params(self):
        return np.concatenate([k.get_params() for k in self.kernels])
