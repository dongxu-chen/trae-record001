import warnings
from typing import Tuple, Optional
from ..backends import LinearAlgebraBackend, auto_select_backend, get_backend


def _check_square_matrix(A, backend: LinearAlgebraBackend):
    if len(A.shape) != 2 or A.shape[0] != A.shape[1]:
        raise ValueError("输入必须是方阵")
    return A.shape[0]


def power_method(A, max_iter: int = 10000, tol: float = 1e-10,
                 backend: Optional[LinearAlgebraBackend] = None):
    """幂法求最大特征值和对应特征向量

    Args:
        A: 输入矩阵
        max_iter: 最大迭代次数
        tol: 收敛容差
        backend: 线性代数后端，如果为None则自动选择

    Returns:
        (eigenvalue, eigenvector)
    """
    if backend is None:
        backend = auto_select_backend(A)

    n = _check_square_matrix(A, backend)

    if max_iter <= 0:
        raise ValueError("max_iter必须是正整数")
    if tol <= 0:
        raise ValueError("tol必须是正数")

    v = backend.random((n,))
    norm_v = backend.norm(v)
    if norm_v < 1e-15:
        v = backend.ones((n,))
        norm_v = backend.sqrt(n)
    v = v / norm_v

    lambda_old = 0.0
    converged = False

    for iter_idx in range(max_iter):
        if backend.is_sparse(A):
            Av = A.dot(v)
        else:
            Av = backend.dot(A, v)

        lambda_new = backend.dot(v, Av)
        norm_Av = backend.norm(Av)

        if norm_Av < 1e-15:
            break

        v = Av / norm_Av

        if iter_idx > 0 and backend.abs(lambda_new - lambda_old) < tol:
            converged = True
            break

        lambda_old = lambda_new

    if not converged:
        warnings.warn(f"幂法在{max_iter}次迭代后未收敛，容差为{tol}")

    return lambda_new, v


def qr_algorithm(A, max_iter: int = 1000, tol: float = 1e-10,
                 backend: Optional[LinearAlgebraBackend] = None):
    """QR算法求所有特征值

    Args:
        A: 输入矩阵
        max_iter: 最大迭代次数
        tol: 收敛容差
        backend: 线性代数后端，如果为None则自动选择

    Returns:
        eigenvalues: 特征值数组
    """
    if backend is None:
        backend = auto_select_backend(A)

    n = _check_square_matrix(A, backend)

    if max_iter <= 0:
        raise ValueError("max_iter必须是正整数")
    if tol <= 0:
        raise ValueError("tol必须是正数")

    Ak = backend.to_device(A.copy())
    converged = False

    for iter_idx in range(max_iter):
        Q, R = _qr_decomposition(Ak, backend)
        Ak_new = backend.dot(R, Q)

        off_diag = 0.0
        for i in range(n - 1):
            off_diag += backend.abs(Ak_new[i + 1, i]) ** 2

        if backend.sqrt(off_diag) < tol:
            Ak = Ak_new
            converged = True
            break

        Ak = Ak_new

    eigenvalues = backend.zeros((n,), dtype=backend.xp.complex128)
    i = 0
    while i < n:
        if i < n - 1 and backend.abs(Ak[i + 1, i]) > 1e-10:
            b = Ak[i, i] + Ak[i + 1, i + 1]
            c = Ak[i, i] * Ak[i + 1, i + 1] - Ak[i, i + 1] * Ak[i + 1, i]
            disc = b ** 2 - 4 * c
            if disc >= 0:
                eigenvalues[i] = (b + backend.sqrt(disc)) / 2
                eigenvalues[i + 1] = (b - backend.sqrt(disc)) / 2
            else:
                eigenvalues[i] = b / 2 + 1j * backend.sqrt(-disc) / 2
                eigenvalues[i + 1] = b / 2 - 1j * backend.sqrt(-disc) / 2
            i += 2
        else:
            eigenvalues[i] = Ak[i, i]
            i += 1

    if not converged:
        warnings.warn(f"QR算法在{max_iter}次迭代后未收敛，容差为{tol}")

    idx = backend.argsort(-backend.abs(eigenvalues))
    return eigenvalues[idx]


def _qr_decomposition(A, backend: LinearAlgebraBackend):
    """简单的QR分解"""
    n = A.shape[0]
    Q = backend.eye(n)
    R = A.copy()

    for k in range(n - 1):
        x = R[k:, k]
        v, beta = _householder_vector(x, backend)
        m = n - k

        v_col = v.reshape(-1, 1)
        v_row = v.reshape(1, -1)
        R[k:, k:] = R[k:, k:] - beta * backend.dot(v_col, backend.dot(v_row, R[k:, k:]))
        Q[:, k:] = Q[:, k:] - beta * backend.dot(Q[:, k:], backend.dot(v_col, v_row))

    return Q, R


def _householder_vector(x, backend: LinearAlgebraBackend):
    n = x.shape[0]
    sigma = backend.dot(x[1:], x[1:])
    v = backend.xp.copy(x)
    v[0] = 1.0

    if sigma == 0:
        beta = 0.0
    else:
        mu = backend.sqrt(x[0] ** 2 + sigma)
        if x[0] <= 0:
            v[0] = x[0] - mu
        else:
            v[0] = -sigma / (x[0] + mu)
        beta = 2.0 * v[0] ** 2 / (sigma + v[0] ** 2)
        v = v / v[0]

    return v, beta


def jacobi_method(A, max_iter: int = 10000, tol: float = 1e-10,
                  threshold: Optional[float] = None,
                  backend: Optional[LinearAlgebraBackend] = None):
    """Jacobi方法求对称矩阵的特征值和特征向量

    Args:
        A: 输入对称矩阵
        max_iter: 最大迭代次数
        tol: 收敛容差
        threshold: 旋转阈值，只旋转大于此值的非对角元
        backend: 线性代数后端，如果为None则自动选择

    Returns:
        (eigenvalues, eigenvectors)
    """
    if backend is None:
        backend = auto_select_backend(A)

    n = _check_square_matrix(A, backend)

    if max_iter <= 0:
        raise ValueError("max_iter必须是正整数")
    if tol <= 0:
        raise ValueError("tol必须是正数")

    if threshold is None:
        threshold = tol

    if threshold < 0:
        raise ValueError("threshold必须是非负数")

    Ak = backend.to_device(A.copy())
    V = backend.eye(n)
    converged = False

    for iter_idx in range(max_iter):
        max_off = 0.0
        p, q = 0, 1

        for i in range(n):
            for j in range(i + 1, n):
                abs_val = backend.abs(Ak[i, j])
                if abs_val > max_off and abs_val > threshold:
                    max_off = abs_val
                    p, q = i, j

        if max_off < tol:
            converged = True
            break

        App = Ak[p, p]
        Aqq = Ak[q, q]
        Apq = Ak[p, q]

        if backend.abs(Apq) < 1e-15:
            theta = 0.0
        else:
            theta = 0.5 * backend.atan2(2 * Apq, Aqq - App)

        c = backend.cos(theta)
        s = backend.sin(theta)

        for i in range(n):
            if i != p and i != q:
                Aip = Ak[i, p]
                Aiq = Ak[i, q]
                Ak[i, p] = c * Aip + s * Aiq
                Ak[i, q] = -s * Aip + c * Aiq
                Ak[p, i] = Ak[i, p]
                Ak[q, i] = Ak[i, q]

        Ak[p, p] = c * c * App + 2 * c * s * Apq + s * s * Aqq
        Ak[q, q] = s * s * App - 2 * c * s * Apq + c * c * Aqq
        Ak[p, q] = 0.0
        Ak[q, p] = 0.0

        for i in range(n):
            Vip = V[i, p]
            Viq = V[i, q]
            V[i, p] = c * Vip + s * Viq
            V[i, q] = -s * Vip + c * Viq

    eigenvalues = backend.diag(Ak)
    idx = backend.argsort(-backend.abs(eigenvalues))
    eigenvalues = eigenvalues[idx]
    eigenvectors = V[:, idx]

    if not converged:
        warnings.warn(f"Jacobi方法在{max_iter}次迭代后未收敛，容差为{tol}")

    return eigenvalues, eigenvectors


def arnoldi_iteration(A, k: int, max_iter: Optional[int] = None,
                      tol: float = 1e-10, reortho: bool = True,
                      backend: Optional[LinearAlgebraBackend] = None):
    """Arnoldi迭代求前k个特征值

    Args:
        A: 输入矩阵
        k: 求前k个特征值
        max_iter: 最大迭代次数
        tol: 收敛容差
        reortho: 是否进行重新正交化
        backend: 线性代数后端，如果为None则自动选择

    Returns:
        (eigenvalues, eigenvectors, converged)
    """
    if backend is None:
        backend = auto_select_backend(A)

    n = _check_square_matrix(A, backend)

    if k <= 0 or k > n:
        raise ValueError(f"k必须在1到{n}之间")

    if max_iter is None:
        max_iter = k + 10

    m = min(k + 1, n)
    dtype = backend.xp.complex128 if backend.xp.iscomplexobj(A) else backend.xp.float64
    V = backend.zeros((n, m), dtype=dtype)
    H = backend.zeros((m, m - 1), dtype=dtype)

    v = backend.random((n,))
    v = v / backend.norm(v)
    V[:, 0] = v

    converged = False

    is_sparse = backend.is_sparse(A)

    for j in range(m - 1):
        if is_sparse:
            w = A.dot(V[:, j])
        else:
            w = backend.dot(A, V[:, j])

        for i in range(j + 1):
            H[i, j] = backend.dot(backend.conj(V[:, i]), w)
            w = w - H[i, j] * V[:, i]

        if reortho and j > 0:
            for i in range(j + 1):
                r = backend.dot(backend.conj(V[:, i]), w)
                H[i, j] += r
                w = w - r * V[:, i]

        H[j + 1, j] = backend.norm(w)

        if H[j + 1, j] < tol:
            converged = True
            break

        V[:, j + 1] = w / H[j + 1, j]

    eigvals_H, eigvecs_H = backend.eig(H[:-1, :])

    idx = backend.argsort(-backend.abs(eigvals_H))
    eigvals = eigvals_H[idx[:k]]
    eigvecs = backend.dot(V[:, :-1], eigvecs_H[:, idx[:k]])

    for i in range(min(k, eigvecs.shape[1])):
        eigvecs[:, i] = eigvecs[:, i] / backend.norm(eigvecs[:, i])

    return eigvals, eigvecs, converged


def eig(A, k: Optional[int] = None, which: str = 'LM',
        max_iter: Optional[int] = None, tol: float = 1e-10,
        backend: Optional[LinearAlgebraBackend] = None):
    """统一的特征值求解接口

    自动根据矩阵类型和规模选择合适的算法

    Args:
        A: 输入矩阵
        k: 前k个特征值（None表示求全部）
        which: 排序方式: 'LM'(最大模), 'SM'(最小模), 'LR'(最大实部), etc.
        max_iter: 最大迭代次数
        tol: 收敛容差
        backend: 线性代数后端

    Returns:
        (eigenvalues, eigenvectors)
    """
    if backend is None:
        backend = auto_select_backend(A)

    n = _check_square_matrix(A, backend)
    is_sparse = backend.is_sparse(A)

    if is_sparse or (k is not None and k < n):
        eigvals, eigvecs, _ = arnoldi_iteration(
            A, k if k is not None else min(6, n - 1),
            max_iter=max_iter, tol=tol, backend=backend
        )
    else:
        eigvals = qr_algorithm(A, max_iter=1000 if max_iter is None else max_iter,
                               tol=tol, backend=backend)
        eigvecs = None

    if which == 'SM':
        idx = backend.argsort(backend.abs(eigvals))
    elif which == 'LR':
        idx = backend.argsort(-backend.real(eigvals))
    elif which == 'SR':
        idx = backend.argsort(backend.real(eigvals))
    elif which == 'LI':
        idx = backend.argsort(-backend.imag(eigvals))
    elif which == 'SI':
        idx = backend.argsort(backend.imag(eigvals))
    else:
        idx = backend.argsort(-backend.abs(eigvals))

    eigvals = eigvals[idx]
    if eigvecs is not None:
        eigvecs = eigvecs[:, idx]

    return eigvals, eigvecs
