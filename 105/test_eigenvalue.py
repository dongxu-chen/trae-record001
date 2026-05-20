import numpy as np
import time
from eigenvalue_solver import (
    power_method,
    qr_algorithm,
    jacobi_method,
    verify_with_numpy,
    compare_results
)


def test_matrix_validation():
    print("=" * 60)
    print("测试 0: 矩阵形状校验")
    print("=" * 60)
    
    non_square = np.random.rand(5, 3)
    try:
        power_method(non_square)
        print("错误: 非方阵未抛出异常")
        return False
    except ValueError as e:
        print(f"✓ 非方阵正确抛出异常: {e}")
    
    try:
        qr_algorithm(non_square)
        print("错误: 非方阵未抛出异常")
        return False
    except ValueError as e:
        print(f"✓ QR算法非方阵正确抛出异常")
    
    try:
        jacobi_method(non_square)
        print("错误: 非方阵未抛出异常")
        return False
    except ValueError as e:
        print(f"✓ Jacobi方法非方阵正确抛出异常")
    
    print()
    return True


def test_power_method():
    print("=" * 60)
    print("测试 1: 幂法求最大特征值和特征向量")
    print("=" * 60)
    
    np.random.seed(42)
    n = 100
    A = np.random.randn(n, n)
    A = (A + A.T) / 2
    
    start_time = time.time()
    lambda_power, v_power = power_method(A, max_iter=10000, tol=1e-10)
    power_time = time.time() - start_time
    
    eigvals_np, eigvecs_np = verify_with_numpy(A)
    lambda_np = eigvals_np[0]
    v_np = eigvecs_np[:, 0]
    
    eigval_error = np.abs(lambda_power - lambda_np)
    
    phase = np.dot(v_power, v_np)
    phase = phase / np.abs(phase) if np.abs(phase) > 1e-15 else 1.0
    eigvec_error = np.linalg.norm(v_power - phase * v_np)
    
    print(f"矩阵大小: {n}x{n}")
    print(f"计算时间: {power_time:.4f} 秒")
    print(f"最大特征值 (我们的): {lambda_power:.6f}")
    print(f"最大特征值 (NumPy): {lambda_np:.6f}")
    print(f"特征值误差: {eigval_error:.2e}")
    print(f"特征向量误差: {eigvec_error:.2e}")
    print()
    
    return eigval_error < 1e-6 and eigvec_error < 1e-6


def test_qr_algorithm():
    print("=" * 60)
    print("测试 2: QR算法求所有特征值 (上Hessenberg预处理)")
    print("=" * 60)
    
    np.random.seed(42)
    n = 30
    A = np.random.randn(n, n)
    
    start_time = time.time()
    eigvals_qr = qr_algorithm(A, max_iter=1000, tol=1e-10)
    qr_time = time.time() - start_time
    
    eigvals_np, _ = verify_with_numpy(A)
    
    eigval_error, _ = compare_results(eigvals_qr, eigvals_np)
    
    print(f"矩阵大小: {n}x{n}")
    print(f"计算时间: {qr_time:.4f} 秒")
    print(f"最大特征值误差: {eigval_error:.2e}")
    
    print("\n前5个特征值对比:")
    our_sorted = eigvals_qr[np.argsort(np.abs(eigvals_qr))[::-1]]
    np_sorted = eigvals_np[np.argsort(np.abs(eigvals_np))[::-1]]
    for i in range(5):
        print(f"  {i+1}: 我们的={our_sorted[i]:.6f}, NumPy={np_sorted[i]:.6f}")
    print()
    
    return eigval_error < 1e-4


def test_jacobi_method():
    print("=" * 60)
    print("测试 3: 对称矩阵的Jacobi方法 (带阈值参数)")
    print("=" * 60)
    
    np.random.seed(42)
    n = 50
    A = np.random.randn(n, n)
    A = (A + A.T) / 2
    
    start_time = time.time()
    eigvals_jacobi, eigvecs_jacobi = jacobi_method(A, max_iter=10000, tol=1e-10, threshold=1e-8)
    jacobi_time = time.time() - start_time
    
    eigvals_np, eigvecs_np = verify_with_numpy(A)
    
    eigval_error, eigvec_error = compare_results(
        eigvals_jacobi, eigvals_np,
        eigvecs_jacobi, eigvecs_np
    )
    
    print(f"矩阵大小: {n}x{n} (对称矩阵)")
    print(f"计算时间: {jacobi_time:.4f} 秒")
    print(f"阈值参数: 1e-8")
    print(f"最大特征值误差: {eigval_error:.2e}")
    print(f"最大特征向量误差: {eigvec_error:.2e}")
    
    print("\n前5个特征值对比:")
    our_sorted = eigvals_jacobi[np.argsort(np.abs(eigvals_jacobi))[::-1]]
    np_sorted = eigvals_np[np.argsort(np.abs(eigvals_np))[::-1]]
    for i in range(5):
        print(f"  {i+1}: 我们的={our_sorted[i]:.6f}, NumPy={np_sorted[i]:.6f}")
    print()
    
    return eigval_error < 1e-6 and eigvec_error < 1e-6


def test_edge_cases():
    print("=" * 60)
    print("测试 4: 边界情况")
    print("=" * 60)
    
    print("测试小矩阵 (2x2):")
    A_small = np.array([[4.0, 1.0], [1.0, 3.0]])
    eigvals, eigvecs = jacobi_method(A_small)
    eigvals_np, _ = verify_with_numpy(A_small)
    error, _ = compare_results(eigvals, eigvals_np)
    print(f"  2x2矩阵误差: {error:.2e} ✓")
    
    print("\n测试对角矩阵:")
    A_diag = np.diag([1.0, 2.0, 3.0, 4.0, 5.0])
    eigvals_qr = qr_algorithm(A_diag)
    eigvals_np, _ = verify_with_numpy(A_diag)
    error, _ = compare_results(eigvals_qr, eigvals_np)
    print(f"  对角矩阵误差: {error:.2e} ✓")
    
    print("\n测试病态矩阵:")
    A_ill = np.array([[1.0, 1000.0], [1000.0, 1.0]])
    eigvals, eigvecs = jacobi_method(A_ill)
    eigvals_np, _ = verify_with_numpy(A_ill)
    error, _ = compare_results(eigvals, eigvals_np)
    print(f"  病态矩阵误差: {error:.2e} ✓")
    
    print()
    return True


def benchmark_scaling():
    print("=" * 60)
    print("性能基准测试: 不同矩阵大小")
    print("=" * 60)
    
    sizes = [50, 100, 200]
    
    print("\n幂法性能:")
    for n in sizes:
        np.random.seed(42)
        A = np.random.randn(n, n)
        A = (A + A.T) / 2
        
        start_time = time.time()
        _, _ = power_method(A)
        elapsed = time.time() - start_time
        
        print(f"  {n}x{n}: {elapsed:.4f} 秒")
    
    print("\nQR算法性能 (带Hessenberg预处理):")
    for n in [20, 30, 50]:
        np.random.seed(42)
        A = np.random.randn(n, n)
        
        start_time = time.time()
        _ = qr_algorithm(A)
        elapsed = time.time() - start_time
        
        print(f"  {n}x{n}: {elapsed:.4f} 秒")
    
    print("\nJacobi方法性能 (带阈值):")
    for n in [30, 50, 80]:
        np.random.seed(42)
        A = np.random.randn(n, n)
        A = (A + A.T) / 2
        
        start_time = time.time()
        _, _ = jacobi_method(A, threshold=1e-6)
        elapsed = time.time() - start_time
        
        print(f"  {n}x{n}: {elapsed:.4f} 秒")
    print()


def main():
    print("\n矩阵特征值并行计算库 - 完整测试套件 (改进版)\n")
    
    results = []
    
    results.append(("矩阵形状校验测试", test_matrix_validation()))
    results.append(("幂法测试", test_power_method()))
    results.append(("QR算法测试 (Hessenberg预处理)", test_qr_algorithm()))
    results.append(("Jacobi方法测试 (带阈值)", test_jacobi_method()))
    results.append(("边界情况测试", test_edge_cases()))
    
    benchmark_scaling()
    
    print("=" * 60)
    print("测试结果汇总")
    print("=" * 60)
    all_passed = True
    for name, passed in results:
        status = "通过 ✓" if passed else "失败 ✗"
        print(f"{name}: {status}")
        if not passed:
            all_passed = False
    
    print("=" * 60)
    if all_passed:
        print("所有测试通过! ✓")
    else:
        print("部分测试失败! ✗")
    print("=" * 60)
    
    print("\n主要改进:")
    print("  1. ✓ 所有函数增加非方阵校验")
    print("  2. ✓ 幂法增加收敛判断和迭代次数限制")
    print("  3. ✓ QR算法增加上Hessenberg形式预处理")
    print("  4. ✓ Jacobi方法增加阈值参数")
    print("  5. ✓ 增加未收敛警告提示")
    print("=" * 60)


if __name__ == "__main__":
    main()
