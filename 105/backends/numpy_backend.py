import numpy as np
from typing import Any, Tuple, Optional
from .base import LinearAlgebraBackend, Array


class NumPyBackend(LinearAlgebraBackend):
    """NumPy CPU后端"""

    def __init__(self):
        self._xp = np
        self._has_scipy = False
        self._sparse = None
        try:
            import scipy.sparse
            self._sparse = scipy.sparse
            self._has_scipy = True
        except ImportError:
            pass

    @property
    def name(self) -> str:
        return "numpy-cpu"

    @property
    def xp(self):
        return self._xp

    @property
    def available(self) -> bool:
        return True

    def to_device(self, array: Array) -> Array:
        if isinstance(array, np.ndarray):
            return array
        return np.asarray(array)

    def to_host(self, array: Array) -> Array:
        return np.asarray(array)

    def dot(self, a: Array, b: Array) -> Array:
        return np.dot(a, b)

    def norm(self, a: Array, axis: Optional[int] = None) -> Array:
        return np.linalg.norm(a, axis=axis)

    def eye(self, n: int, dtype: Any = None) -> Array:
        return np.eye(n, dtype=dtype)

    def zeros(self, shape: Tuple[int, ...], dtype: Any = None) -> Array:
        return np.zeros(shape, dtype=dtype)

    def ones(self, shape: Tuple[int, ...], dtype: Any = None) -> Array:
        return np.ones(shape, dtype=dtype)

    def random(self, shape: Tuple[int, ...]) -> Array:
        return np.random.rand(*shape)

    def sqrt(self, x: Array) -> Array:
        return np.sqrt(x)

    def abs(self, x: Array) -> Array:
        return np.abs(x)

    def real(self, x: Array) -> Array:
        return np.real(x)

    def imag(self, x: Array) -> Array:
        return np.imag(x)

    def conj(self, x: Array) -> Array:
        return np.conj(x)

    def cos(self, x: Array) -> Array:
        return np.cos(x)

    def sin(self, x: Array) -> Array:
        return np.sin(x)

    def atan2(self, y: Array, x: Array) -> Array:
        return np.arctan2(y, x)

    def argsort(self, x: Array) -> Array:
        return np.argsort(x)

    def sum(self, x: Array, axis: Optional[int] = None) -> Array:
        return np.sum(x, axis=axis)

    def diag(self, x: Array) -> Array:
        return np.diag(x)

    def eig(self, a: Array) -> Tuple[Array, Array]:
        return np.linalg.eig(a)

    def is_sparse(self, a: Array) -> bool:
        if not self._has_scipy:
            return False
        return self._sparse.issparse(a)

    def supports_sparse(self) -> bool:
        return self._has_scipy
