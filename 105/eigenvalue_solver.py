import numpy as np
import warnings
from numba import jit, prange, config

config.THREADING_LAYER = 'omp'

try:
    import scipy.sparse as sp
    _HAS_SCIPY = True
except ImportError:
    _HAS_SCIPY = False


def _is_sparse_matrix(A):
    if not _HAS_SCIPY:
        return False
    return sp.issparse(A)


def _check_square_matrix(A):
    if len(A.shape) != 2 or A.shape[0] != A.shape[1]:
        raise ValueError("输入必须是方阵")
    return A.shape[0]


@jit(nopython=True, parallel=True)
def _power_method_kernel(A, max_iter, tol):
    n = A.shape[0]
    v = np.random.rand(n)
    norm_v = np.linalg.norm(v)
    if norm_v < 1e-15:
        v = np.ones(n)
        norm_v = np.sqrt(n)
    v = v / norm_v
    
    lambda_old = 0.0
    converged = False
    
    for iter_idx in range(max_iter):
        Av = np.dot(A, v)
        lambda_new = np.dot(v, Av)
        norm_Av = np.linalg.norm(Av)
        
        if norm_Av < 1e-15:
            break
        
        v = Av / norm_Av
        
        if iter_idx > 0 and np.abs(lambda_new - lambda_old) < tol:
            converged = True
            break
        
        lambda_old = lambda_new
    
    return lambda_new, v, converged


def power_method(A, max_iter=10000, tol=1e-10):
    n = _check_square_matrix(A)
    
    if max_iter <= 0:
        raise ValueError("max_iter必须是正整数")
    if tol <= 0:
        raise ValueError("tol必须是正数")
    
    lambda_val, v, converged = _power_method_kernel(A, max_iter, tol)
    
    if not converged:
        import warnings
        warnings.warn(f"幂法在{max_iter}次迭代后未收敛，容差为{tol}")
    
    return lambda_val, v


@jit(nopython=True)
def householder_vector(x):
    n = x.shape[0]
    sigma = np.dot(x[1:], x[1:])
    v = np.copy(x)
    v[0] = 1.0
    
    if sigma == 0:
        beta = 0.0
    else:
        mu = np.sqrt(x[0] ** 2 + sigma)
        if x[0] <= 0:
            v[0] = x[0] - mu
        else:
            v[0] = -sigma / (x[0] + mu)
        beta = 2.0 * v[0] ** 2 / (sigma + v[0] ** 2)
        v = v / v[0]
    
    return v, beta


@jit(nopython=True, parallel=True)
def hessenberg_reduction(A):
    n = A.shape[0]
    H = np.copy(A)
    Q = np.eye(n)
    
    for k in range(n - 2):
        x = H[k + 1:, k]
        v, beta = householder_vector(x)
        m = n - k - 1
        H_sub = H[k + 1:, k:]
        v_col = v.reshape(-1, 1)
        v_row = v.reshape(1, -1)
        H[k + 1:, k:] = H_sub - beta * np.dot(v_col, np.dot(v_row, H_sub))
        
        H_left = H[:, k + 1:]
        H[:, k + 1:] = H_left - beta * np.dot(np.dot(H_left, v_col), v_row)
        
        Q_right = Q[:, k + 1:]
        Q[:, k + 1:] = Q_right - beta * np.dot(np.dot(Q_right, v_col), v_row)
    
    return H, Q


@jit(nopython=True, parallel=True)
def qr_decomposition_hessenberg(H):
    n = H.shape[0]
    Q = np.eye(n)
    R = np.copy(H)
    
    for k in range(n - 1):
        x = R[k:k + 2, k]
        r = np.sqrt(x[0] ** 2 + x[1] ** 2)
        if r < 1e-15:
            c, s = 1.0, 0.0
        else:
            c = x[0] / r
            s = -x[1] / r
        
        G = np.array([[c, -s], [s, c]])
        
        R[k:k + 2, k:] = np.dot(G, R[k:k + 2, k:])
        Q[:, k:k + 2] = np.dot(Q[:, k:k + 2], G.T)
    
    return Q, R


@jit(nopython=True, parallel=True)
def _qr_algorithm_kernel(H, max_iter, tol):
    n = H.shape[0]
    Ak = np.copy(H)
    converged = False
    
    for iter_idx in range(max_iter):
        Q, R = qr_decomposition_hessenberg(Ak)
        Ak_new = np.dot(R, Q)
        
        off_diag = 0.0
        for i in prange(n - 1):
            off_diag += Ak_new[i + 1, i] ** 2
        
        if np.sqrt(off_diag) < tol:
            Ak = Ak_new
            converged = True
            break
        
        Ak = Ak_new
    
    eigenvalues = np.zeros(n, dtype=np.complex128)
    i = 0
    while i < n:
        if i < n - 1 and np.abs(Ak[i + 1, i]) > 1e-10:
            b = Ak[i, i] + Ak[i + 1, i + 1]
            c = Ak[i, i] * Ak[i + 1, i + 1] - Ak[i, i + 1] * Ak[i + 1, i]
            disc = b ** 2 - 4 * c
            if disc >= 0:
                eigenvalues[i] = (b + np.sqrt(disc)) / 2
                eigenvalues[i + 1] = (b - np.sqrt(disc)) / 2
            else:
                eigenvalues[i] = b / 2 + 1j * np.sqrt(-disc) / 2
                eigenvalues[i + 1] = b / 2 - 1j * np.sqrt(-disc) / 2
            i += 2
        else:
            eigenvalues[i] = Ak[i, i]
            i += 1
    
    return eigenvalues, converged


def qr_algorithm(A, max_iter=1000, tol=1e-10):
    n = _check_square_matrix(A)
    
    if max_iter <= 0:
        raise ValueError("max_iter必须是正整数")
    if tol <= 0:
        raise ValueError("tol必须是正数")
    
    H, _ = hessenberg_reduction(A)
    
    eigenvalues, converged = _qr_algorithm_kernel(H, max_iter, tol)
    
    if not converged:
        import warnings
        warnings.warn(f"QR算法在{max_iter}次迭代后未收敛，容差为{tol}")
    
    return eigenvalues


@jit(nopython=True, parallel=True)
def _jacobi_method_kernel(A, max_iter, tol, threshold):
    n = A.shape[0]
    Ak = np.copy(A)
    V = np.eye(n)
    converged = False
    
    for iter_idx in range(max_iter):
        max_off = 0.0
        p, q = 0, 1
        
        for i in prange(n):
            for j in range(i + 1, n):
                abs_val = np.abs(Ak[i, j])
                if abs_val > max_off and abs_val > threshold:
                    max_off = abs_val
                    p, q = i, j
        
        if max_off < tol:
            converged = True
            break
        
        App = Ak[p, p]
        Aqq = Ak[q, q]
        Apq = Ak[p, q]
        
        if np.abs(Apq) < 1e-15:
            theta = 0.0
        else:
            theta = 0.5 * np.arctan2(2 * Apq, Aqq - App)
        
        c = np.cos(theta)
        s = np.sin(theta)
        
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
    
    eigenvalues = np.diag(Ak)
    idx = np.argsort(np.abs(eigenvalues))[::-1]
    eigenvalues = eigenvalues[idx]
    eigenvectors = V[:, idx]
    
    return eigenvalues, eigenvectors, converged


def jacobi_method(A, max_iter=10000, tol=1e-10, threshold=None):
    n = _check_square_matrix(A)
    
    if max_iter <= 0:
        raise ValueError("max_iter必须是正整数")
    if tol <= 0:
        raise ValueError("tol必须是正数")
    
    if threshold is None:
        threshold = tol
    
    if threshold < 0:
        raise ValueError("threshold必须是非负数")
    
    A_sym = (A + A.T) / 2
    if not np.allclose(A, A_sym, atol=1e-10):
        import warnings
        warnings.warn("输入矩阵不是对称矩阵，已自动对称化")
    
    eigenvalues, eigenvectors, converged = _jacobi_method_kernel(A_sym, max_iter, tol, threshold)
    
    if not converged:
        import warnings
        warnings.warn(f"Jacobi方法在{max_iter}次迭代后未收敛，容差为{tol}")
    
    return eigenvalues, eigenvectors


def verify_with_numpy(A):
    _check_square_matrix(A)
    eigvals_np, eigvecs_np = np.linalg.eig(A)
    
    idx = np.argsort(np.abs(eigvals_np))[::-1]
    eigvals_np = eigvals_np[idx]
    eigvecs_np = eigvecs_np[:, idx]
    
    return eigvals_np, eigvecs_np


def compare_results(our_eigvals, np_eigvals, our_eigvecs=None, np_eigvecs=None, tolerance=1e-6):
    our_eigvals_sorted = our_eigvals[np.argsort(np.abs(our_eigvals))[::-1]]
    np_eigvals_sorted = np_eigvals[np.argsort(np.abs(np_eigvals))[::-1]]
    
    eigval_error = np.max(np.abs(our_eigvals_sorted - np_eigvals_sorted))
    
    eigvec_error = None
    if our_eigvecs is not None and np_eigvecs is not None:
        eigvec_errors = []
        for i in range(len(our_eigvals_sorted)):
            our_vec = our_eigvecs[:, i]
            np_vec = np_eigvecs[:, i]
            phase = np.dot(our_vec.conj(), np_vec)
            phase = phase / np.abs(phase) if np.abs(phase) > 1e-15 else 1.0
            eigvec_errors.append(np.linalg.norm(our_vec - phase * np_vec))
        eigvec_error = np.max(eigvec_errors)
    
    return eigval_error, eigvec_error


def _sparse_power_method_kernel(A, max_iter, tol):
    n = A.shape[0]
    v = np.random.rand(n)
    norm_v = np.linalg.norm(v)
    if norm_v < 1e-15:
        v = np.ones(n)
        norm_v = np.sqrt(n)
    v = v / norm_v
    
    lambda_old = 0.0
    converged = False
    
    for iter_idx in range(max_iter):
        Av = A.dot(v)
        lambda_new = np.dot(v, Av)
        norm_Av = np.linalg.norm(Av)
        
        if norm_Av < 1e-15:
            break
        
        v = Av / norm_Av
        
        if iter_idx > 0 and np.abs(lambda_new - lambda_old) < tol:
            converged = True
            break
        
        lambda_old = lambda_new
    
    return lambda_new, v, converged


def power_method_sparse(A, max_iter=10000, tol=1e-10):
    if not _HAS_SCIPY:
        raise ImportError("稀疏矩阵支持需要SciPy库，请先安装: pip install scipy")
    
    if not _is_sparse_matrix(A):
        raise ValueError("输入必须是SciPy稀疏矩阵 (CSR/CSC等)")
    
    n = _check_square_matrix(A)
    
    if max_iter <= 0:
        raise ValueError("max_iter必须是正整数")
    if tol <= 0:
        raise ValueError("tol必须是正数")
    
    lambda_val, v, converged = _sparse_power_method_kernel(A, max_iter, tol)
    
    if not converged:
        warnings.warn(f"稀疏幂法在{max_iter}次迭代后未收敛，容差为{tol}")
    
    return lambda_val, v


def arnoldi_iteration(A, k, max_iter=None, tol=1e-10, reortho=True):
    if not _HAS_SCIPY:
        raise ImportError("稀疏矩阵支持需要SciPy库，请先安装: pip install scipy")
    
    is_sparse = _is_sparse_matrix(A)
    n = _check_square_matrix(A)
    
    if k <= 0 or k > n:
        raise ValueError(f"k必须在1到{n}之间")
    
    if max_iter is None:
        max_iter = k + 10
    
    m = min(k + 1, n)
    V = np.zeros((n, m), dtype=np.complex128 if np.iscomplexobj(A) else np.float64)
    H = np.zeros((m, m - 1), dtype=np.complex128 if np.iscomplexobj(A) else np.float64)
    
    v = np.random.rand(n)
    v = v / np.linalg.norm(v)
    V[:, 0] = v
    
    converged = False
    
    for j in range(m - 1):
        if is_sparse:
            w = A.dot(V[:, j])
        else:
            w = np.dot(A, V[:, j])
        
        for i in range(j + 1):
            H[i, j] = np.dot(V[:, i].conj(), w)
            w = w - H[i, j] * V[:, i]
        
        if reortho and j > 0:
            for i in range(j + 1):
                r = np.dot(V[:, i].conj(), w)
                H[i, j] += r
                w = w - r * V[:, i]
        
        H[j + 1, j] = np.linalg.norm(w)
        
        if H[j + 1, j] < tol:
            converged = True
            break
        
        V[:, j + 1] = w / H[j + 1, j]
    
    H = H[:j + 2, :j + 1]
    V = V[:, :j + 1]
    
    eigvals_H, eigvecs_H = np.linalg.eig(H[:-1, :])
    
    idx = np.argsort(np.abs(eigvals_H))[::-1]
    eigvals = eigvals_H[idx[:k]]
    eigvecs = np.dot(V[:, :-1], eigvecs_H[:, idx[:k]])
    
    for i in range(min(k, eigvecs.shape[1])):
        eigvecs[:, i] = eigvecs[:, i] / np.linalg.norm(eigvecs[:, i])
    
    return eigvals, eigvecs, converged


def eig_sparse(A, k=6, which='LM', max_iter=None, tol=1e-10):
    if not _HAS_SCIPY:
        raise ImportError("稀疏矩阵支持需要SciPy库，请先安装: pip install scipy")
    
    if not _is_sparse_matrix(A):
        raise ValueError("输入必须是SciPy稀疏矩阵 (CSR/CSC等)")
    
    n = _check_square_matrix(A)
    
    if k <= 0 or k >= n:
        raise ValueError(f"k必须在1到{n-1}之间")
    
    if which not in ['LM', 'SM', 'LR', 'SR', 'LI', 'SI']:
        raise ValueError("which必须是: 'LM' (最大模), 'SM' (最小模), 'LR' (最大实部), 'SR' (最小实部), 'LI' (最大虚部), 'SI' (最小虚部)")
    
    eigvals, eigvecs, _ = arnoldi_iteration(A, k, max_iter=max_iter, tol=tol)
    
    if which == 'LM':
        idx = np.argsort(np.abs(eigvals))[::-1]
    elif which == 'SM':
        idx = np.argsort(np.abs(eigvals))
    elif which == 'LR':
        idx = np.argsort(eigvals.real)[::-1]
    elif which == 'SR':
        idx = np.argsort(eigvals.real)
    elif which == 'LI':
        idx = np.argsort(eigvals.imag)[::-1]
    else:
        idx = np.argsort(eigvals.imag)
    
    eigvals = eigvals[idx[:k]]
    eigvecs = eigvecs[:, idx[:k]]
    
    return eigvals, eigvecs


def eig(A, k=None, which='LM', max_iter=None, tol=1e-10):
    n = _check_square_matrix(A)
    
    is_sparse = _is_sparse_matrix(A)
    
    if is_sparse:
        if k is None:
            k = min(6, n - 1)
        return eig_sparse(A, k=k, which=which, max_iter=max_iter, tol=tol)
    else:
        if k is not None and k < n:
            eigvals, eigvecs, _ = arnoldi_iteration(A, k, max_iter=max_iter, tol=tol)
            return eigvals, eigvecs
        else:
            eigvals = qr_algorithm(A, max_iter=1000 if max_iter is None else max_iter, tol=tol)
            idx = np.argsort(np.abs(eigvals))[::-1]
            return eigvals[idx], None


def power_method_auto(A, max_iter=10000, tol=1e-10):
    if _is_sparse_matrix(A):
        return power_method_sparse(A, max_iter=max_iter, tol=tol)
    else:
        return power_method(A, max_iter=max_iter, tol=tol)

