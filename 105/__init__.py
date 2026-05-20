"""矩阵特征值并行计算库

支持多种后端（NumPy, CuPy），多种算法（幂法, QR, Jacobi, Arnoldi），
以及自动后端选择和性能基准测试。

使用示例:
    from eigenvalues import eig, power_method, get_backend
    import numpy as np

    # 自动后端选择
    A = np.random.randn(100, 100)
    eigvals, eigvecs = eig(A, k=10)  # 自动选择算法

    # 显式指定后端
    eigval, eigvec = power_method(A, backend=get_backend('cupy'))
"""

from .backends import (
    LinearAlgebraBackend,
    NumPyBackend,
    CuPyBackend,
    get_backend,
    list_available_backends,
    set_default_backend,
    auto_select_backend,
)
from .solvers import (
    power_method,
    qr_algorithm,
    jacobi_method,
    arnoldi_iteration,
    eig,
)
from . import benchmark

__all__ = [
    # Backends
    'LinearAlgebraBackend',
    'NumPyBackend',
    'CuPyBackend',
    'get_backend',
    'list_available_backends',
    'set_default_backend',
    'auto_select_backend',

    # Solvers
    'power_method',
    'qr_algorithm',
    'jacobi_method',
    'arnoldi_iteration',
    'eig',

    # Benchmark
    'benchmark',
]

__version__ = '3.0.0'
