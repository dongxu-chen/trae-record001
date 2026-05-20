import time
import numpy as np
from typing import List, Dict, Any
from .backends import LinearAlgebraBackend, get_backend, list_available_backends
from .solvers import power_method, qr_algorithm, arnoldi_iteration


class BenchmarkResult:
    """基准测试结果"""

    def __init__(self, name: str):
        self.name = name
        self.times: Dict[str, List[float]] = {}
        self.errors: Dict[str, List[float]] = {}
        self.metadata: Dict[str, Any] = {}

    def add_time(self, backend: str, elapsed: float):
        if backend not in self.times:
            self.times[backend] = []
        self.times[backend].append(elapsed)

    def add_error(self, backend: str, error: float):
        if backend not in self.errors:
            self.errors[backend] = []
        self.errors[backend].append(error)

    def get_stats(self, backend: str) -> Dict[str, float]:
        if backend not in self.times:
            return {}
        times = np.array(self.times[backend])
        return {
            'mean': np.mean(times),
            'std': np.std(times),
            'min': np.min(times),
            'max': np.max(times),
            'median': np.median(times),
        }

    def print_summary(self):
        print(f"\n{'='*60}")
        print(f"基准测试: {self.name}")
        print(f"{'='*60}")

        backends = list(self.times.keys())
        if not backends:
            print("  无测试结果")
            return

        print(f"\n{'后端':<15} {'平均时间(s)':<15} {'标准差(s)':<15} {'速度比'}")
        print("-" * 60)

        baseline = np.mean(self.times[backends[0]])

        for backend in backends:
            stats = self.get_stats(backend)
            speedup = baseline / stats['mean']
            print(f"{backend:<15} {stats['mean']:<15.4f} {stats['std']:<15.4f} {speedup:.2f}x")

        if self.errors:
            print(f"\n{'后端':<15} {'平均误差':<15}")
            print("-" * 40)
            for backend in backends:
                if backend in self.errors:
                    avg_error = np.mean(self.errors[backend])
                    print(f"{backend:<15} {avg_error:<15.2e}")


def benchmark_power_method(sizes: List[int] = [100, 500, 1000],
                           runs: int = 3) -> BenchmarkResult:
    """基准测试幂法

    Args:
        sizes: 矩阵规模列表
        runs: 每个规模运行次数

    Returns:
        BenchmarkResult对象
    """
    result = BenchmarkResult(f"幂法 (矩阵规模: {sizes})")
    result.metadata['sizes'] = sizes
    result.metadata['runs'] = runs

    backends = list_available_backends()

    for n in sizes:
        print(f"\n测试规模: {n}x{n}")

        np.random.seed(42)
        A_np = np.random.randn(n, n)
        A_np = (A_np + A_np.T) / 2

        for backend_name in backends:
            backend = get_backend(backend_name)
            if not backend.available:
                continue

            try:
                A = backend.to_device(A_np)

                errors = []
                times = []

                for run in range(runs):
                    start = time.time()
                    backend.synchronize()

                    eigval, eigvec = power_method(A, max_iter=1000, tol=1e-6, backend=backend)

                    backend.synchronize()
                    elapsed = time.time() - start
                    times.append(elapsed)

                    eigvals_ref, _ = backend.eig(A)
                    max_eigval = eigvals_ref[np.argmax(np.abs(eigvals_ref))]
                    error = np.abs(backend.to_host(eigval) - backend.to_host(max_eigval))
                    errors.append(error)

                avg_time = np.mean(times)
                avg_error = np.mean(errors)
                result.add_time(backend_name, avg_time)
                result.add_error(backend_name, avg_error)
                print(f"  {backend_name}: {avg_time:.4f}s, 误差: {avg_error:.2e}")

            except Exception as e:
                print(f"  {backend_name}: 失败 - {e}")

    return result


def benchmark_arnoldi(sizes: List[int] = [100, 500, 1000],
                      k: int = 10, runs: int = 3) -> BenchmarkResult:
    """基准测试Arnoldi迭代

    Args:
        sizes: 矩阵规模列表
        k: 求前k个特征值
        runs: 每个规模运行次数

    Returns:
        BenchmarkResult对象
    """
    result = BenchmarkResult(f"Arnoldi迭代 (k={k}, 规模: {sizes})")
    result.metadata['sizes'] = sizes
    result.metadata['k'] = k
    result.metadata['runs'] = runs

    backends = list_available_backends()

    for n in sizes:
        print(f"\n测试规模: {n}x{n}, k={k}")

        np.random.seed(42)
        A_np = np.random.randn(n, n)

        for backend_name in backends:
            backend = get_backend(backend_name)
            if not backend.available:
                continue

            try:
                A = backend.to_device(A_np)

                errors = []
                times = []

                for run in range(runs):
                    start = time.time()
                    backend.synchronize()

                    eigvals, eigvecs, _ = arnoldi_iteration(A, k=k, max_iter=k+10, tol=1e-6, backend=backend)

                    backend.synchronize()
                    elapsed = time.time() - start
                    times.append(elapsed)

                    eigvals_ref, _ = backend.eig(A)
                    idx_ref = np.argsort(np.abs(backend.to_host(eigvals_ref)))[::-1][:k]
                    eigvals_ref = eigvals_ref[idx_ref]

                    idx_test = np.argsort(np.abs(backend.to_host(eigvals)))[::-1]
                    eigvals_test = eigvals[idx_test]

                    error = np.mean(np.abs(backend.to_host(eigvals_test[:k]) - backend.to_host(eigvals_ref)))
                    errors.append(error)

                avg_time = np.mean(times)
                avg_error = np.mean(errors)
                result.add_time(backend_name, avg_time)
                result.add_error(backend_name, avg_error)
                print(f"  {backend_name}: {avg_time:.4f}s, 平均误差: {avg_error:.2e}")

            except Exception as e:
                print(f"  {backend_name}: 失败 - {e}")

    return result


def benchmark_qr(sizes: List[int] = [50, 100, 200],
                 runs: int = 3) -> BenchmarkResult:
    """基准测试QR算法

    Args:
        sizes: 矩阵规模列表
        runs: 每个规模运行次数

    Returns:
        BenchmarkResult对象
    """
    result = BenchmarkResult(f"QR算法 (矩阵规模: {sizes})")
    result.metadata['sizes'] = sizes
    result.metadata['runs'] = runs

    backends = list_available_backends()

    for n in sizes:
        print(f"\n测试规模: {n}x{n}")

        np.random.seed(42)
        A_np = np.random.randn(n, n)

        for backend_name in backends:
            backend = get_backend(backend_name)
            if not backend.available:
                continue

            try:
                A = backend.to_device(A_np)

                errors = []
                times = []

                for run in range(runs):
                    start = time.time()
                    backend.synchronize()

                    eigvals = qr_algorithm(A, max_iter=500, tol=1e-6, backend=backend)

                    backend.synchronize()
                    elapsed = time.time() - start
                    times.append(elapsed)

                    eigvals_ref, _ = backend.eig(A)
                    idx_ref = np.argsort(np.abs(backend.to_host(eigvals_ref)))[::-1]
                    eigvals_ref = eigvals_ref[idx_ref]

                    idx_test = np.argsort(np.abs(backend.to_host(eigvals)))[::-1]
                    eigvals_test = eigvals[idx_test]

                    error = np.mean(np.abs(backend.to_host(eigvals_test) - backend.to_host(eigvals_ref)))
                    errors.append(error)

                avg_time = np.mean(times)
                avg_error = np.mean(errors)
                result.add_time(backend_name, avg_time)
                result.add_error(backend_name, avg_error)
                print(f"  {backend_name}: {avg_time:.4f}s, 平均误差: {avg_error:.2e}")

            except Exception as e:
                print(f"  {backend_name}: 失败 - {e}")

    return result


def run_all_benchmarks():
    """运行所有基准测试"""
    print("=" * 60)
    print("特征值求解器 - 性能基准测试")
    print("=" * 60)

    print(f"\n可用后端: {list_available_backends()}")

    results = []

    print("\n" + "=" * 60)
    print("1. 幂法基准测试")
    print("=" * 60)
    result = benchmark_power_method(sizes=[100, 500, 1000], runs=3)
    results.append(('power_method', result))
    result.print_summary()

    print("\n" + "=" * 60)
    print("2. QR算法基准测试")
    print("=" * 60)
    result = benchmark_qr(sizes=[50, 100, 200], runs=3)
    results.append(('qr_algorithm', result))
    result.print_summary()

    print("\n" + "=" * 60)
    print("3. Arnoldi迭代基准测试")
    print("=" * 60)
    result = benchmark_arnoldi(sizes=[100, 500, 1000], k=10, runs=3)
    results.append(('arnoldi', result))
    result.print_summary()

    print("\n" + "=" * 60)
    print("总体性能总结")
    print("=" * 60)

    return results


if __name__ == '__main__':
    run_all_benchmarks()
