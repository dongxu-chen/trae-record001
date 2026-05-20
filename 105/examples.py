"""矩阵特征值求解库 - 多后端支持示例"""

import numpy as np
import sys

sys.path.insert(0, '..')

from eigenvalue_solver import (
    power_method,
    qr_algorithm,
    jacobi_method,
    arnoldi_iteration,
    eig,
    get_backend,
    list_available_backends,
    benchmark,
)


def example_1_backend_selection():
    """示例1: 后端选择"""
    print("=" * 60)
    print("示例 1: 后端选择")
    print("=" * 60)

    print(f"\n可用后端: {list_available_backends()}")

    # 获取NumPy后端
    numpy_backend = get_backend('numpy')
    print(f"\nNumPy后端可用: {numpy_backend.available}")

    # 尝试获取CuPy后端
    try:
        cupy_backend = get_backend('cupy')
        print(f"CuPy后端可用: {cupy_backend.available}")
        if cupy_backend.available:
            print(f"  CUDA设备: {cupy_backend.xp.cuda.runtime.getDeviceCount()}")
    except Exception as e:
        print(f"CuPy后端不可用: {e}")


def example_2_power_method():
    """示例2: 幂法"""
    print("\n" + "=" * 60)
    print("示例 2: 幂法求最大特征值")
    print("=" * 60)

    np.random.seed(42)
    n = 500
    A = np.random.randn(n, n)
    A = (A + A.T) / 2

    print(f"\n矩阵大小: {n}x{n}")

    # 自动后端
    import time
    start = time.time()
    eigval_auto, eigvec_auto = power_method(A, max_iter=1000, tol=1e-6)
    time_auto = time.time() - start
    print(f"自动后端:")
    print(f"  最大特征值: {eigval_auto:.6f}")
    print(f"  用时: {time_auto:.4f}s")

    # NumPy后端
    start = time.time()
    eigval_np, eigvec_np = power_method(A, max_iter=1000, tol=1e-6, backend=get_backend('numpy'))
    time_np = time.time() - start
    print(f"NumPy后端:")
    print(f"  最大特征值: {eigval_np:.6f}")
    print(f"  用时: {time_np:.4f}s")


def example_3_arnoldi():
    """示例3: Arnoldi迭代"""
    print("\n" + "=" * 60)
    print("示例 3: Arnoldi迭代求前k个特征值")
    print("=" * 60)

    np.random.seed(42)
    n = 1000
    k = 20
    A = np.random.randn(n, n)

    print(f"\n矩阵大小: {n}x{n}, 求前{k}个特征值")

    import time
    start = time.time()
    eigvals, eigvecs, converged = arnoldi_iteration(A, k=k, max_iter=k+10, tol=1e-6)
    time_arnoldi = time.time() - start

    print(f"Arnoldi迭代:")
    print(f"  用时: {time_arnoldi:.4f}s")
    print(f"  收敛: {'是' if converged else '否'}")
    print(f"  前5个特征值:")
    for i in range(min(5, k)):
        print(f"    {i+1}: {eigvals[i]:.6f}")


def example_4_unified_eig():
    """示例4: 统一eig接口"""
    print("\n" + "=" * 60)
    print("示例 4: 统一eig接口 (自动算法选择)")
    print("=" * 60)

    np.random.seed(42)

    # 小矩阵 - 自动用QR
    n_small = 50
    A_small = np.random.randn(n_small, n_small)
    print(f"\n小矩阵 {n_small}x{n_small} - QR算法求全部特征值")

    import time
    start = time.time()
    eigvals_all, _ = eig(A_small)
    time_all = time.time() - start

    print(f"  特征值数量: {len(eigvals_all)}")
    print(f"  用时: {time_all:.4f}s")
    print(f"  前5个: {eigvals_all[:5]}")

    # 大矩阵 - 自动用Arnoldi
    n_large = 500
    k = 10
    A_large = np.random.randn(n_large, n_large)
    print(f"\n大矩阵 {n_large}x{n_large} - Arnoldi求前{k}个特征值")

    start = time.time()
    eigvals_k, eigvecs_k = eig(A_large, k=k)
    time_k = time.time() - start

    print(f"  特征值数量: {len(eigvals_k)}")
    print(f"  用时: {time_k:.4f}s")
    print(f"  前5个: {eigvals_k[:5]}")


def example_5_benchmark():
    """示例5: 性能基准测试"""
    print("\n" + "=" * 60)
    print("示例 5: 性能基准测试")
    print("=" * 60)

    print("\n运行幂法基准测试...")
    result = benchmark.benchmark_power_method(sizes=[100, 500], runs=2)
    result.print_summary()


def main():
    print("\n" + "=" * 60)
    print("矩阵特征值求解库 v3.0 - 多后端支持示例")
    print("=" * 60)

    example_1_backend_selection()
    example_2_power_method()
    example_3_arnoldi()
    example_4_unified_eig()
    # example_5_benchmark()  # 可选运行

    print("\n" + "=" * 60)
    print("所有示例运行完成!")
    print("=" * 60)


if __name__ == '__main__':
    main()
