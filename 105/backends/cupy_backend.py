from typing import Any, Tuple, Optional
from .base import LinearAlgebraBackend, Array


class CuPyBackend(LinearAlgebraBackend):
    """CuPy CUDA后端"""

    def __init__(self):
        self._available = False
        self._xp = None
        self._has_cupyx = False
        self._sparse = None

        try:
            import cupy
            self._xp = cupy
            self._available = True

            try:
                import cupyx.scipy.sparse
                self._sparse = cupyx.scipy.sparse
                self._has_cupyx = True
            except ImportError:
                pass
        except ImportError:
            pass

    @property
    def name(self) -> str:
        return "cupy-cuda"

    @property
    def xp(self):
        if not self._available:
            raise ImportError("CuPy is not available")
        return self._xp

    @property
    def available(self) -> bool:
        return self._available

    def to_device(self, array: Array) -> Array:
        if not self._available:
            raise ImportError("CuPy is not available")

        if hasattr(array, '__module__') and 'cupy' in array.__module__:
            return array

        return self._xp.asarray(array)

    def to_host(self, array: Array) -> Array:
        if not self._available:
            raise ImportError("CuPy is not available")

        if hasattr(array, 'get'):
            return array.get()
        import numpy as np
        return np.asarray(array)

    def dot(self, a: Array, b: Array) -> Array:
        return self._xp.dot(a, b)

    def norm(self, a: Array, axis: Optional[int] = None) -> Array:
        return self._xp.linalg.norm(a, axis=axis)

    def eye(self, n: int, dtype: Any = None) -> Array:
        return self._xp.eye(n, dtype=dtype)

    def zeros(self, shape: Tuple[int, ...], dtype: Any = None) -> Array:
        return self._xp.zeros(shape, dtype=dtype)

    def ones(self, shape: Tuple[int, ...], dtype: Any = None) -> Array:
        return self._xp.ones(shape, dtype=dtype)

    def random(self, shape: Tuple[int, ...]) -> Array:
        return self._xp.random.rand(*shape)

    def sqrt(self, x: Array) -> Array:
        return self._xp.sqrt(x)

    def abs(self, x: Array) -> Array:
        return self._xp.abs(x)

    def real(self, x: Array) -> Array:
        return self._xp.real(x)

    def imag(self, x: Array) -> Array:
        return self._xp.imag(x)

    def conj(self, x: Array) -> Array:
        return self._xp.conj(x)

    def cos(self, x: Array) -> Array:
        return self._xp.cos(x)

    def sin(self, x: Array) -> Array:
        return self._xp.sin(x)

    def atan2(self, y: Array, x: Array) -> Array:
        return self._xp.arctan2(y, x)

    def argsort(self, x: Array) -> Array:
        return self._xp.argsort(x)

    def sum(self, x: Array, axis: Optional[int] = None) -> Array:
        return self._xp.sum(x, axis=axis)

    def diag(self, x: Array) -> Array:
        return self._xp.diag(x)

    def eig(self, a: Array) -> Tuple[Array, Array]:
        return self._xp.linalg.eig(a)

    def is_sparse(self, a: Array) -> bool:
        if not self._has_cupyx:
            return False
        return self._sparse.issparse(a)

    def supports_sparse(self) -> bool:
        return self._has_cupyx

    def synchronize(self):
        if self._available:
            self._xp.cuda.Device().synchronize()
