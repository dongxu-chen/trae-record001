import numpy as np
import sys

sys.path.insert(0, '.')

from eigenvalue_solver import (
    _HAS_SCIPY,
    power_method,
    qr_algorithm,
    jacobi_method,
    power_method_sparse,
    arnoldi_iteration,
    eig_sparse,
    eig,
    power_method_auto,
    verify_with_numpy,
    compare_results
)

print("=" * 70)
print("矩阵特征值并行计算库 v2.0 - 完整功能示例")
print("=" * 70)

np.random.seed(42)

print("\n" + "-" * 70)
print("第一部分: 稠密矩阵算法")
print("-" * 70)

print("\n1. 幂法求最大特征值 (带收敛判断)")
n = 50
A = np.random.randn(n, n)
A = (A + A.T) / 2

lambda_max, v = power_method(A, max_iter=5000, tol=1e-12)
print(f"   矩阵大小: {n}x{n}")
print(f"   最大特征值: {lambda_max:.8f}")

eigvals_np, _ = verify_with_numpy(A)
print(f"   NumPy验证: {eigvals_np[0]:.8f}")
print(f"   误差: {np.abs(lambda_max - eigvals_np[0]):.2e}")

print("\n2. QR算法求所有特征值 (Hessenberg预处理)")
n = 20
A = np.random.randn(n, n)

eigvals_qr = qr_algorithm(A, max_iter=1000, tol=1e-10)
eigvals_np, _ = verify_with_numpy(A)

error, _ = compare_results(eigvals_qr, eigvals_np)
print(f"   矩阵大小: {n}x{n}")
print(f"   最大特征值误差: {error:.2e}")

print("\n3. Jacobi方法 (带阈值参数) - 对称矩阵专用")
n = 30
A = np.random.randn(n, n)
A = (A + A.T) / 2

eigvals_jacobi, eigvecs_jacobi = jacobi_method(
    A, max_iter=10000, tol=1e-10, threshold=1e-6
)
eigvals_np, eigvecs_np = verify_with_numpy(A)
val_error, vec_error = compare_results(
    eigvals_jacobi, eigvals_np, eigvecs_jacobi, eigvecs_np
)
print(f"   矩阵大小: {n}x{n}")
print(f"   特征值误差: {val_error:.2e}")
print(f"   特征向量误差: {vec_error:.2e}")

if _HAS_SCIPY:
    import scipy.sparse as sp
    
    print("\n" + "-" * 70)
    print("第二部分: 稀疏矩阵算法")
    print("-" * 70)
    
    print("\n4. 稀疏幂法 (利用稀疏矩阵-向量乘法)")
    n = 200
    density = 0.1
    A_dense = np.random.randn(n, n)
    A_dense = (A_dense + A_dense.T) / 2
    A_sparse = sp.csr_matrix(A_dense)
    
    lambda_sparse, v_sparse = power_method_sparse(A_sparse)
    eigvals_np, _ = verify_with_numpy(A_dense)
    error = np.abs(lambda_sparse - eigvals_np[0])
    print(f"   矩阵大小: {n}x{n}, 稀疏度: {density:.0%}")
    print(f"   非零元素数: {A_sparse.nnz}")
    print(f"   最大特征值: {lambda_sparse:.8f}")
    print(f"   NumPy验证: {eigvals_np[0]:.8f}")
    print(f"   误差: {error:.2e}")
    
    print("\n5. Arnoldi迭代 - 求前k个特征值")
    n = 100
    k = 10
    A_dense = np.random.randn(n, n)
    A_sparse = sp.csr_matrix(A_dense)
    
    eigvals_arnoldi, eigvecs_arnoldi, _ = arnoldi_iteration(A_sparse, k=k)
    eigvals_np, _ = verify_with_numpy(A_dense)
    
    print(f"   矩阵大小: {n}x{n}, 求前{k}个特征值")
    print("   前5个特征值对比:")
    for i in range(min(5, k)):
        print(f"     {i+1}: Arnoldi={eigvals_arnoldi[i]:.6f}, NumPy={eigvals_np[i]:.6f}")
    
    print("\n6. eig_sparse - 支持多种排序选项")
    n = 50
    k = 6
    A_dense = np.random.randn(n, n)
    A_sparse = sp.csr_matrix(A_dense)
    
    which_options = ['LM', 'SM', 'LR', 'SR']
    option_names = {
        'LM': '最大模',
        'SM': '最小模',
        'LR': '最大实部',
        'SR': '最小实部'
    }
    
    print(f"   矩阵大小: {n}x{n}, 求前{k}个特征值")
    for which in which_options:
        eigvals, eigvecs = eig_sparse(A_sparse, k=k, which=which)
        print(f"   {option_names[which]} ({which}): {eigvals[0]:.4f}, {eigvals[1]:.4f}, {eigvals[2]:.4f}")
    
    print("\n7. power_method_auto - 自动检测矩阵类型")
    n = 100
    A_dense = np.random.randn(n, n)
    A_sparse = sp.csr_matrix(A_dense)
    
    lambda_dense, _ = power_method_auto(A_dense)
    lambda_sparse, _ = power_method_auto(A_sparse)
    eigvals_np, _ = verify_with_numpy(A_dense)
    
    print(f"   稠密矩阵: {lambda_dense:.6f}")
    print(f"   稀疏矩阵: {lambda_sparse:.6f}")
    print(f"   NumPy基准: {eigvals_np[0]:.6f}")

print("\n" + "-" * 70)
print("第三部分: 统一接口 eig() - 自动算法选择")
print("-" * 70)

print("\n8. 小矩阵 - 自动用QR算法求全部特征值")
n_small = 20
A_small = np.random.randn(n_small, n_small)

eigvals_small, _ = eig(A_small)
print(f"   矩阵大小: {n_small}x{n_small}")
print(f"   特征值数量: {len(eigvals_small)}")

print("\n9. 大矩阵 - 指定k, 自动用Arnoldi求前k个")
n_large = 200
k = 10
A_large = np.random.randn(n_large, n_large)

eigvals_large, eigvecs_large = eig(A_large, k=k)
print(f"   矩阵大小: {n_large}x{n_large}")
print(f"   特征值数量: {len(eigvals_large)}")

if _HAS_SCIPY:
    print("\n10. 稀疏矩阵 - 自动用稀疏Arnoldi")
    import scipy.sparse as sp
    n_sparse = 500
    k = 10
    A_sparse = sp.random(n_sparse, n_sparse, density=0.05, format='csr')
    
    eigvals_sparse, eigvecs_sparse = eig(A_sparse, k=k)
    print(f"   矩阵大小: {n_sparse}x{n_sparse}")
    print(f"   非零元素数: {A_sparse.nnz}")
    print(f"   特征值数量: {len(eigvals_sparse)}")

print("\n" + "=" * 70)
print("API 快速参考")
print("=" * 70)
print("\n幂法:")
print("  power_method(A, max_iter=10000, tol=1e-10)      - 稠密矩阵")
print("  power_method_sparse(A, max_iter=10000, tol=1e-10) - 稀疏矩阵")
print("  power_method_auto(A, max_iter=10000, tol=1e-10)   - 自动检测")

print("\n全特征值:")
print("  qr_algorithm(A, max_iter=1000, tol=1e-10)         - QR算法")
print("  jacobi_method(A, max_iter=10000, tol=1e-10, threshold=None) - 对称矩阵")

print("\n前k个特征值:")
print("  arnoldi_iteration(A, k, max_iter=None, tol=1e-10) - Arnoldi迭代")
print("  eig_sparse(A, k=6, which='LM')                   - 稀疏矩阵专用")

print("\n统一接口 (推荐):")
print("  eig(A, k=None, which='LM')                        - 自动选择算法")
print("    - 稀疏矩阵: eig_sparse")
print("    - 稠密矩阵且k<N: Arnoldi")
print("    - 稠密矩阵且k=None: QR")

print("\n验证工具:")
print("  verify_with_numpy(A)                              - NumPy基准")
print("  compare_results(our, np)                         - 结果对比")
print("=" * 70)
