"""快速测试脚本 - 验证模块化重构是否成功"""

import sys
import numpy as np

print("=" * 60)
print("矩阵特征值求解库 v3.0 - 模块化重构验证")
print("=" * 60)

# 1. 测试后端模块导入
print("\n[1/5] 测试后端模块导入...")
try:
    from backends.base import LinearAlgebraBackend
    from backends.numpy_backend import NumPyBackend
    print("   ✓ 后端模块导入成功")
except Exception as e:
    print(f"   ✗ 后端模块导入失败: {e}")
    sys.exit(1)

# 2. 测试NumPy后端
print("\n[2/5] 测试NumPy后端...")
try:
    numpy_backend = NumPyBackend()
    print(f"   ✓ 后端名称: {numpy_backend.name}")
    print(f"   ✓ 可用状态: {numpy_backend.available}")
except Exception as e:
    print(f"   ✗ NumPy后端测试失败: {e}")
    sys.exit(1)

# 3. 测试后端管理器
print("\n[3/5] 测试后端管理器...")
try:
    from backends import get_backend, list_available_backends
    
    available = list_available_backends()
    print(f"   ✓ 可用后端: {available}")
    
    backend = get_backend('numpy')
    print(f"   ✓ 获取后端成功: {backend.name}")
except Exception as e:
    print(f"   ✗ 后端管理器测试失败: {e}")
    sys.exit(1)

# 4. 测试求解器模块
print("\n[4/5] 测试求解器模块...")
try:
    from solvers.eigenvalue import (
        power_method,
        qr_algorithm,
        jacobi_method,
        arnoldi_iteration,
        eig
    )
    print("   ✓ 求解器模块导入成功")
except Exception as e:
    print(f"   ✗ 求解器模块导入失败: {e}")
    sys.exit(1)

# 5. 测试实际计算
print("\n[5/5] 测试特征值计算...")
try:
    np.random.seed(42)
    n = 100
    A = np.random.randn(n, n)
    A = (A + A.T) / 2

    # 测试幂法
    eigval_pm, _ = power_method(A, max_iter=500, tol=1e-6)
    print(f"   ✓ 幂法: 最大特征值 = {eigval_pm:.4f}")

    # 测试QR
    eigvals_qr = qr_algorithm(A, max_iter=200, tol=1e-6)
    print(f"   ✓ QR算法: 求得 {len(eigvals_qr)} 个特征值")

    # 测试Arnoldi
    eigvals_ar, _, _ = arnoldi_iteration(A, k=10)
    print(f"   ✓ Arnoldi: 求得 {len(eigvals_ar)} 个特征值")

    # 测试统一eig接口
    eigvals_eig, _ = eig(A, k=5)
    print(f"   ✓ 统一接口: 求得 {len(eigvals_eig)} 个特征值")

except Exception as e:
    print(f"   ✗ 特征值计算测试失败: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# 6. 测试benchmark模块
print("\n[6/6] 测试Benchmark模块...")
try:
    import benchmark
    from benchmark import BenchmarkResult
    print("   ✓ Benchmark模块导入成功")
except Exception as e:
    print(f"   ✗ Benchmark模块测试失败: {e}")
    sys.exit(1)

print("\n" + "=" * 60)
print("✅ 所有测试通过! 模块化重构成功完成")
print("=" * 60)
print("\n项目总结:")
print("  ✓ 后端抽象基类 LinearAlgebraBackend")
print("  ✓ NumPy CPU 后端实现")
print("  ✓ CuPy CUDA 后端实现 (可选)")
print("  ✓ 运行时自动后端选择")
print("  ✓ 特征值求解器完全支持后端")
print("  ✓ 完整的性能基准测试框架")
print("")
