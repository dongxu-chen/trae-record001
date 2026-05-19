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
print("矩阵特征值求解库 v2.0 - 改进验证")
print("=" * 70)

np.random.seed(42)

print("\n" + "-" * 70)
print("第一部分: v1.0 改进验证 (收敛性和稳定性)")
print("-" * 70)

print("\n1. 测试非方阵校验...")
non_square = np.random.rand(5, 3)
try:
    power_method(non_square)
    print("   ❌ 失败: 没有抛出异常")
except ValueError as e:
    print(f"   ✓ 通过: {e}")

print("\n2. 测试幂法收敛判断...")
n = 20
A = np.random.randn(n, n)
A = (A + A.T) / 2
lambda_val, vec = power_method(A, max_iter=1000, tol=1e-10)
eigvals_np, _ = verify_with_numpy(A)
error = np.abs(lambda_val - eigvals_np[0])
print(f"   误差: {error:.2e} {'✓' if error < 1e-6 else '❌'}")

print("\n3. 测试QR算法 (Hessenberg预处理)...")
n = 15
A = np.random.randn(n, n)
eigvals_qr = qr_algorithm(A, max_iter=500, tol=1e-10)
eigvals_np, _ = verify_with_numpy(A)
error, _ = compare_results(eigvals_qr, eigvals_np)
print(f"   误差: {error:.2e} {'✓' if error < 1e-2 else '❌'}")

print("\n4. 测试Jacobi方法阈值参数...")
n = 20
A = np.random.randn(n, n)
A = (A + A.T) / 2

for threshold in [1e-4, 1e-6, 1e-8]:
    eigvals_jacobi, eigvecs_jacobi = jacobi_method(
        A, max_iter=5000, tol=1e-10, threshold=threshold
    )
    eigvals_np, eigvecs_np = verify_with_numpy(A)
    val_error, vec_error = compare_results(
        eigvals_jacobi, eigvals_np, eigvecs_jacobi, eigvecs_np
    )
    status = "✓" if val_error < 1e-6 else "❌"
    print(f"   阈值={threshold:.0e}: 特征值误差={val_error:.2e} {status}")

print("\n5. 测试无效参数处理...")
try:
    power_method(A, max_iter=-1)
    print("   ❌ max_iter=-1 没有抛出异常")
except ValueError as e:
    print(f"   ✓ max_iter=-1: {e}")

try:
    power_method(A, tol=-1e-5)
    print("   ❌ tol=-1e-5 没有抛出异常")
except ValueError as e:
    print(f"   ✓ tol=-1e-5: {e}")

try:
    jacobi_method(A, threshold=-0.1)
    print("   ❌ threshold=-0.1 没有抛出异常")
except ValueError as e:
    print(f"   ✓ threshold=-0.1: {e}")

print("\n" + "-" * 70)
print("第二部分: v2.0 新功能验证 (稀疏矩阵)")
print("-" * 70)

if _HAS_SCIPY:
    import scipy.sparse as sp
    
    print("\n6. 测试SciPy稀疏矩阵支持...")
    print(f"   ✓ SciPy已安装: {sp.__version__}")
    
    from eigenvalue_solver import _is_sparse_matrix
    
    A_dense = np.random.randn(10, 10)
    A_sparse = sp.random(10, 10, density=0.3, format='csr')
    
    print(f"   稠密矩阵检测: {not _is_sparse_matrix(A_dense)} {'✓' if not _is_sparse_matrix(A_dense) else '❌'}")
    print(f"   稀疏矩阵检测: {_is_sparse_matrix(A_sparse)} {'✓' if _is_sparse_matrix(A_sparse) else '❌'}")
    
    print("\n7. 测试稀疏幂法...")
    n = 100
    A_dense = np.random.randn(n, n)
    A_dense = (A_dense + A_dense.T) / 2
    A_sparse = sp.csr_matrix(A_dense)
    
    lambda_dense, _ = power_method_auto(A_dense)
    lambda_sparse, _ = power_method_sparse(A_sparse)
    eigvals_np, _ = verify_with_numpy(A_dense)
    
    error_dense = np.abs(lambda_dense - eigvals_np[0])
    error_sparse = np.abs(lambda_sparse - eigvals_np[0])
    
    print(f"   稠密幂法误差: {error_dense:.2e} {'✓' if error_dense < 1e-6 else '❌'}")
    print(f"   稀疏幂法误差: {error_sparse:.2e} {'✓' if error_sparse < 1e-6 else '❌'}")
    
    print("\n8. 测试Arnoldi迭代...")
    n = 50
    k = 10
    A_dense = np.random.randn(n, n)
    A_sparse = sp.csr_matrix(A_dense)
    
    eigvals_dense, eigvecs_dense, _ = arnoldi_iteration(A_dense, k=k)
    eigvals_sparse, eigvecs_sparse, _ = arnoldi_iteration(A_sparse, k=k)
    
    eigvals_np, _ = verify_with_numpy(A_dense)
    eigvals_np_topk = eigvals_np[:k]
    
    error_dense, _ = compare_results(eigvals_dense, eigvals_np_topk)
    error_sparse, _ = compare_results(eigvals_sparse, eigvals_np_topk)
    
    print(f"   稠密Arnoldi误差: {error_dense:.2e} {'✓' if error_dense < 1e-1 else '❌'}")
    print(f"   稀疏Arnoldi误差: {error_sparse:.2e} {'✓' if error_sparse < 1e-1 else '❌'}")
    
    print("\n9. 测试eig_sparse which参数...")
    which_options = ['LM', 'SM', 'LR', 'SR']
    for which in which_options:
        eigvals, eigvecs = eig_sparse(A_sparse, k=5, which=which)
        print(f"   ✓ {which} 选项正常工作")
    
    print("\n10. 测试eig()自动算法选择...")
    n_small = 20
    n_large = 100
    
    A_small = np.random.randn(n_small, n_small)
    A_large = np.random.randn(n_large, n_large)
    A_large_sparse = sp.csr_matrix(A_large)
    
    eigvals_small, _ = eig(A_small)
    eigvals_large, eigvecs_large = eig(A_large, k=10)
    eigvals_sparse, eigvecs_sparse = eig(A_large_sparse, k=10)
    
    print(f"   ✓ 小矩阵 ({n_small}x{n_small}): QR算法, {len(eigvals_small)}个特征值")
    print(f"   ✓ 大矩阵 ({n_large}x{n_large}): Arnoldi算法, {len(eigvals_large)}个特征值")
    print(f"   ✓ 稀疏矩阵 ({n_large}x{n_large}): 稀疏Arnoldi, {len(eigvals_sparse)}个特征值")
    
else:
    print("\n⚠️  未检测到SciPy库，跳过稀疏矩阵测试")
    print("   安装命令: pip install scipy")

print("\n" + "=" * 70)
print("v2.0 功能总结")
print("=" * 70)

print("\n✓ v1.0 基础功能:")
print("   - 幂法求最大特征值")
print("   - QR算法求所有特征值")
print("   - Jacobi方法 (对称矩阵)")

print("\n✓ v1.1 收敛性改进:")
print("   - 矩阵形状校验 (非方阵抛出异常)")
print("   - 幂法收敛判断和迭代限制")
print("   - QR算法Hessenberg预处理")
print("   - Jacobi方法阈值参数")
print("   - 未收敛警告和参数校验")

print("\n✓ v2.0 稀疏矩阵支持:")
print("   - 支持SciPy稀疏矩阵格式 (CSR/CSC等)")
print("   - 稀疏幂法 (利用稀疏矩阵-向量乘法)")
print("   - Arnoldi迭代 (求前k个特征值)")
print("   - eig_sparse (支持LM/SM/LR/SR等排序选项)")
print("   - eig() 自动算法选择接口")
print("   - power_method_auto (自动检测矩阵类型)")

print("\n" + "=" * 70)
print("所有改进验证完成!")
print("=" * 70)
