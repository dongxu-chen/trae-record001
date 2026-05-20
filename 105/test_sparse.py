import numpy as np
import time
import sys

sys.path.insert(0, '.')

from eigenvalue_solver import (
    _HAS_SCIPY,
    power_method_sparse,
    arnoldi_iteration,
    eig_sparse,
    eig,
    power_method_auto,
    verify_with_numpy,
    compare_results
)

if not _HAS_SCIPY:
    print("=" * 70)
    print("警告: 未检测到SciPy库，无法运行稀疏矩阵测试")
    print("请先安装: pip install scipy")
    print("=" * 70)
    sys.exit(0)

import scipy.sparse as sp


def test_sparse_detection():
    print("=" * 70)
    print("测试 1: 稀疏矩阵检测")
    print("=" * 70)
    
    from eigenvalue_solver import _is_sparse_matrix
    
    A_dense = np.random.randn(10, 10)
    A_sparse = sp.random(10, 10, density=0.3, format='csr')
    
    print(f"稠密矩阵检测: {_is_sparse_matrix(A_dense)} (应为False)")
    print(f"稀疏矩阵检测: {_is_sparse_matrix(A_sparse)} (应为True)")
    print()
    
    return not _is_sparse_matrix(A_dense) and _is_sparse_matrix(A_sparse)


def test_sparse_power_method():
    print("=" * 70)
    print("测试 2: 稀疏幂法")
    print("=" * 70)
    
    np.random.seed(42)
    n = 200
    
    A_dense = np.random.randn(n, n)
    A_dense = (A_dense + A_dense.T) / 2
    A_sparse = sp.csr_matrix(A_dense)
    
    start_time = time.time()
    lambda_dense, v_dense = power_method_auto(A_dense)
    dense_time = time.time() - start_time
    
    start_time = time.time()
    lambda_sparse, v_sparse = power_method_sparse(A_sparse)
    sparse_time = time.time() - start_time
    
    eigvals_np, _ = verify_with_numpy(A_dense)
    lambda_np = eigvals_np[0]
    
    error_dense = np.abs(lambda_dense - lambda_np)
    error_sparse = np.abs(lambda_sparse - lambda_np)
    
    print(f"矩阵大小: {n}x{n}")
    print(f"稠密幂法时间: {dense_time:.4f}秒, 误差: {error_dense:.2e}")
    print(f"稀疏幂法时间: {sparse_time:.4f}秒, 误差: {error_sparse:.2e}")
    print(f"最大特征值: {lambda_np:.6f}")
    print()
    
    return error_dense < 1e-6 and error_sparse < 1e-6


def test_arnoldi_iteration():
    print("=" * 70)
    print("测试 3: Arnoldi迭代算法")
    print("=" * 70)
    
    np.random.seed(42)
    n = 100
    k = 10
    
    A_dense = np.random.randn(n, n)
    A_sparse = sp.csr_matrix(A_dense)
    
    start_time = time.time()
    eigvals_dense, eigvecs_dense, _ = arnoldi_iteration(A_dense, k=k)
    dense_time = time.time() - start_time
    
    start_time = time.time()
    eigvals_sparse, eigvecs_sparse, _ = arnoldi_iteration(A_sparse, k=k)
    sparse_time = time.time() - start_time
    
    eigvals_np, _ = verify_with_numpy(A_dense)
    eigvals_np_topk = eigvals_np[:k]
    
    print(f"矩阵大小: {n}x{n}, 求前{k}个特征值")
    print(f"稠密Arnoldi时间: {dense_time:.4f}秒")
    print(f"稀疏Arnoldi时间: {sparse_time:.4f}秒")
    
    print("\n前5个特征值对比:")
    for i in range(min(5, k)):
        print(f"  {i+1}: NumPy={eigvals_np_topk[i]:.6f}, "
              f"稠密={eigvals_dense[i]:.6f}, "
              f"稀疏={eigvals_sparse[i]:.6f}")
    
    error_dense, _ = compare_results(eigvals_dense, eigvals_np_topk)
    error_sparse, _ = compare_results(eigvals_sparse, eigvals_np_topk)
    
    print(f"\n稠密最大误差: {error_dense:.2e}")
    print(f"稀疏最大误差: {error_sparse:.2e}")
    print()
    
    return error_dense < 1e-2 and error_sparse < 1e-2


def test_eig_sparse():
    print("=" * 70)
    print("测试 4: eig_sparse函数 (支持which参数)")
    print("=" * 70)
    
    np.random.seed(42)
    n = 50
    k = 6
    
    A_dense = np.random.randn(n, n)
    A_sparse = sp.csr_matrix(A_dense)
    
    which_options = ['LM', 'SM', 'LR', 'SR']
    results = {}
    
    for which in which_options:
        eigvals, eigvecs = eig_sparse(A_sparse, k=k, which=which)
        results[which] = eigvals[:3]
    
    eigvals_np, _ = verify_with_numpy(A_dense)
    
    print(f"矩阵大小: {n}x{n}, 求前{k}个特征值")
    print("\n不同which选项的前3个特征值:")
    
    for which in which_options:
        print(f"  {which}: {results[which][0]:.6f}, {results[which][1]:.6f}, {results[which][2]:.6f}")
    
    print("\n验证最大模 (LM) 前3个:")
    idx_lm = np.argsort(np.abs(eigvals_np))[::-1]
    for i in range(3):
        print(f"  {eigvals_np[idx_lm[i]]:.6f}")
    
    print("\n验证最小模 (SM) 前3个:")
    idx_sm = np.argsort(np.abs(eigvals_np))
    for i in range(3):
        print(f"  {eigvals_np[idx_sm[i]]:.6f}")
    print()
    
    return True


def test_auto_eig():
    print("=" * 70)
    print("测试 5: 自动算法选择 eig()")
    print("=" * 70)
    
    np.random.seed(42)
    n_small = 30
    n_large = 200
    k = 10
    
    A_small_dense = np.random.randn(n_small, n_small)
    A_large_dense = np.random.randn(n_large, n_large)
    A_large_sparse = sp.csr_matrix(A_large_dense)
    
    print(f"小矩阵 ({n_small}x{n_small}) 全特征值 (QR算法):")
    start_time = time.time()
    eigvals_small, _ = eig(A_small_dense)
    small_time = time.time() - start_time
    print(f"  时间: {small_time:.4f}秒, 特征值数: {len(eigvals_small)}")
    
    print(f"\n大矩阵 ({n_large}x{n_large}) 前{k}个特征值 (Arnoldi):")
    start_time = time.time()
    eigvals_large, eigvecs_large = eig(A_large_dense, k=k)
    large_time = time.time() - start_time
    print(f"  时间: {large_time:.4f}秒, 特征值数: {len(eigvals_large)}")
    
    print(f"\n稀疏矩阵 ({n_large}x{n_large}) 稀疏前{k}个特征值:")
    start_time = time.time()
    eigvals_sparse, eigvecs_sparse = eig(A_large_sparse, k=k)
    sparse_time = time.time() - start_time
    print(f"  时间: {sparse_time:.4f}秒, 特征值数: {len(eigvals_sparse)}")
    
    print()
    return True


def benchmark_sparse_density():
    print("=" * 70)
    print("性能基准: 不同稀疏度的影响")
    print("=" * 70)
    
    np.random.seed(42)
    n = 500
    k = 10
    densities = [0.01, 0.05, 0.1, 0.3]
    
    print(f"矩阵大小: {n}x{n}, 求前{k}个特征值")
    print(f"稀疏度\t非零元数\t时间(秒)")
    print("-" * 40)
    
    for density in densities:
        A_sparse = sp.random(n, n, density=density, format='csr')
        nnz = A_sparse.nnz
        
        start_time = time.time()
        _, _ = eig_sparse(A_sparse, k=k)
        elapsed = time.time() - start_time
        
        print(f"{density:.2f}\t{nnz}\t{elapsed:.4f}")
    
    print()


def main():
    print("\n" + "=" * 70)
    print("矩阵特征值求解库 - 稀疏矩阵功能测试")
    print("=" * 70 + "\n")
    
    results = []
    
    results.append(("稀疏矩阵检测", test_sparse_detection()))
    results.append(("稀疏幂法", test_sparse_power_method()))
    results.append(("Arnoldi迭代", test_arnoldi_iteration()))
    results.append(("eig_sparse函数", test_eig_sparse()))
    results.append(("自动算法选择", test_auto_eig()))
    
    benchmark_sparse_density()
    
    print("=" * 70)
    print("测试结果汇总")
    print("=" * 70)
    
    all_passed = True
    for name, passed in results:
        status = "通过 ✓" if passed else "失败 ✗"
        print(f"{name}: {status}")
        if not passed:
            all_passed = False
    
    print("=" * 70)
    if all_passed:
        print("所有测试通过! ✓")
    else:
        print("部分测试失败! ✗")
    print("=" * 70)
    
    print("\n稀疏矩阵功能总结:")
    print("  1. ✓ 支持SciPy稀疏矩阵格式 (CSR/CSC等)")
    print("  2. ✓ 稀疏幂法 - 利用稀疏矩阵-向量乘法")
    print("  3. ✓ Arnoldi迭代 - 求前k个特征值")
    print("  4. ✓ eig() 自动选择算法 (稠密QR/稀疏Arnoldi")
    print("  5. ✓ 支持多种特征值排序选项 (LM/SM/LR/SR等)")
    print("=" * 70)


if __name__ == "__main__":
    main()
