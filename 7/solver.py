import numpy as np
import os
import threading
from scipy.sparse.linalg import spsolve, cg, minres, gmres
from scipy.sparse import csr_matrix, diags
from typing import Callable, Optional


def _set_num_threads(num_threads: int) -> None:
    if num_threads > 0:
        os.environ['OMP_NUM_THREADS'] = str(num_threads)
        os.environ['OPENBLAS_NUM_THREADS'] = str(num_threads)
        os.environ['MKL_NUM_THREADS'] = str(num_threads)
        os.environ['VECLIB_MAXIMUM_THREADS'] = str(num_threads)
        os.environ['NUMEXPR_NUM_THREADS'] = str(num_threads)


def _build_diagonal_preconditioner(K: csr_matrix) -> csr_matrix:
    diag = K.diagonal()
    diag_inv = np.where(diag != 0, 1.0 / diag, 1.0)
    return diags(diag_inv, 0)


def _build_ilu_preconditioner(K: csr_matrix, drop_tol: float = 1e-6) -> csr_matrix:
    try:
        from scipy.sparse.linalg import spilu
        ilu = spilu(K.tocsc(), drop_tol=drop_tol)
        M = ilu.solve
        return M
    except:
        return _build_diagonal_preconditioner(K)


class ParallelCG:
    def __init__(self, num_threads: int = 1):
        self.num_threads = num_threads
        self.lock = threading.Lock()
    
    def dot_product(self, a: np.ndarray, b: np.ndarray) -> float:
        return np.dot(a, b)
    
    def matvec(self, K, x: np.ndarray) -> np.ndarray:
        return K.dot(x)


def solve_linear_system(
    K: csr_matrix, 
    F: np.ndarray,
    method: str = 'auto',
    tol: float = 1e-10,
    maxiter: Optional[int] = None,
    preconditioner: str = 'jacobi',
    num_threads: int = 0
) -> np.ndarray:
    if num_threads > 0:
        _set_num_threads(num_threads)
        print(f"  使用线程数: {num_threads}")
    
    print("正在求解线性系统...")
    print(f"  矩阵大小: {K.shape}")
    print(f"  非零元素数: {K.nnz}")
    
    n = K.shape[0]
    if maxiter is None:
        maxiter = n * 10
    
    nnz_per_row = K.nnz / n
    
    if method == 'auto':
        if nnz_per_row < 20 and n < 10000:
            method = 'direct'
        else:
            method = 'cg'
    
    print(f"  求解方法: {method}")
    
    if preconditioner == 'jacobi':
        M = _build_diagonal_preconditioner(K)
    elif preconditioner == 'ilu':
        M = _build_ilu_preconditioner(K)
    else:
        M = None
    
    if method == 'direct':
        try:
            u = spsolve(K, F)
            print("  直接求解器完成")
        except MemoryError:
            print("  直接求解器内存不足，切换到迭代求解器 (CG)")
            if M is None:
                M = _build_diagonal_preconditioner(K)
            u, info = cg(K, F, tol=tol, maxiter=maxiter, M=M)
            if info == 0:
                print(f"  CG 迭代求解完成")
            elif info > 0:
                print(f"  警告: CG 在 {info} 次迭代后未收敛")
            else:
                print(f"  错误: CG 非法输入")
                
    elif method == 'cg':
        if M is None:
            M = _build_diagonal_preconditioner(K)
        u, info = cg(K, F, tol=tol, maxiter=maxiter, M=M)
        if info == 0:
            print(f"  CG 迭代求解完成")
        elif info > 0:
            print(f"  警告: CG 在 {info} 次迭代后未达到收敛容差 {tol}")
        else:
            print(f"  错误: CG 非法输入")
            
    elif method == 'minres':
        u, info = minres(K, F, tol=tol, maxiter=maxiter)
        if info == 0:
            print(f"  MINRES 迭代求解完成")
        else:
            print(f"  警告: MINRES 退出码 = {info}")
            
    elif method == 'gmres':
        u, info = gmres(K, F, tol=tol, maxiter=maxiter)
        if info == 0:
            print(f"  GMRES 迭代求解完成")
        else:
            print(f"  警告: GMRES 退出码 = {info}")
            
    elif method == 'bicgstab':
        try:
            from scipy.sparse.linalg import bicgstab
            u, info = bicgstab(K, F, tol=tol, maxiter=maxiter, M=M)
            if info == 0:
                print(f"  BiCGSTAB 迭代求解完成")
            else:
                print(f"  警告: BiCGSTAB 退出码 = {info}")
        except:
            print("  BiCGSTAB 不可用，切换到 CG")
            u, info = cg(K, F, tol=tol, maxiter=maxiter, M=M)
    else:
        raise ValueError(f"未知的求解方法: {method}，可选: direct, cg, minres, gmres, bicgstab")
    
    print("求解完成！")
    return u


def compute_l2_error(
    u: np.ndarray,
    exact_solution: Callable[[np.ndarray], np.ndarray],
    nodes: np.ndarray
) -> float:
    u_exact = exact_solution(nodes)
    error = u - u_exact
    l2_error = np.sqrt(np.mean(error**2))
    return l2_error


def verify_solution(u: np.ndarray) -> None:
    print(f"\n解的统计信息:")
    print(f"  最小值: {np.min(u):.6f}")
    print(f"  最大值: {np.max(u):.6f}")
    print(f"  平均值: {np.mean(u):.6f}")
    print(f"  标准差: {np.std(u):.6f}")
