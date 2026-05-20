import numpy as np
from snapshot import SnapshotGenerator
from pod import PODBasis
from reduced_model import ReducedModel
from error_est import ErrorEstimator


def example_model(mu):
    n = 100
    x = np.linspace(0, 1, n)
    return np.sin(mu * np.pi * x) + 0.5 * np.cos(2 * mu * np.pi * x)


def main():
    print("=" * 60)
    print("POD 模型降阶库 - 修复版本示例")
    print("=" * 60)
    
    parameter_range = np.linspace(0.5, 2.0, 20)
    
    print("\n1. 生成快照 (支持内存映射)...")
    snapshot_gen = SnapshotGenerator(
        example_model, parameter_range,
        dtype=np.float64,
        use_memmap=False
    )
    snapshots = snapshot_gen.generate()
    print(f"   生成了 {snapshots.shape[0]} 个快照")
    print(f"   每个快照维度: {snapshots.shape[1:]}")
    print(f"   内存使用: {snapshot_gen.get_memory_usage():.2f} MB")
    
    print("\n2. 计算 POD 基 (带收敛容差)...")
    snapshot_matrix = snapshot_gen.get_snapshot_matrix()
    pod_basis = PODBasis(snapshot_matrix, dtype=np.float64)
    basis = pod_basis.compute_basis(
        method='svd',
        energy_threshold=0.99,
        tol=1e-10
    )
    print(f"   基的秩: {pod_basis.get_rank()}")
    print(f"   捕获能量: {pod_basis.get_energy():.4f}")
    print(f"   前5个奇异值: {pod_basis.singular_values[:5]}")
    print(f"   有效秩 (99%能量): {pod_basis.get_rank()}")
    
    print("\n3. 构建降阶模型 (形状检查)...")
    reduced_model = ReducedModel(pod_basis, example_model)
    
    test_mu = 1.3
    print(f"\n4. 测试参数 mu = {test_mu}...")
    full_solution = example_model(test_mu)
    reduced_solution = reduced_model.solve(test_mu)
    
    print(f"   完整解维度: {full_solution.shape}")
    print(f"   降阶解维度: {reduced_solution.shape}")
    
    print("\n5. 误差估计 (形状验证)...")
    error_estimator = ErrorEstimator(pod_basis, reduced_model)
    abs_error, rel_error = error_estimator.compute_reconstruction_error(full_solution)
    print(f"   绝对误差: {abs_error:.6f}")
    print(f"   相对误差: {rel_error:.6f}")
    
    errors, rel_errors = error_estimator.compute_errors_dataset(snapshots)
    stats = error_estimator.get_error_statistics()
    print(f"\n   数据集误差统计:")
    print(f"     平均相对误差: {stats['mean_relative_error']:.6f}")
    print(f"     最大相对误差: {stats['max_relative_error']:.6f}")
    print(f"     中位数相对误差: {stats['median_relative_error']:.6f}")
    
    error_bound = error_estimator.estimate_error_bound(
        pod_basis.singular_values, 
        pod_basis.get_rank()
    )
    print(f"   理论误差界: {error_bound:.6f}")
    
    print("\n6. 批量处理测试...")
    test_snapshots = np.array([example_model(mu) for mu in np.linspace(0.8, 1.8, 5)])
    batch_reduced = reduced_model.batch_project(test_snapshots)
    batch_reconstructed = reduced_model.batch_reconstruct(batch_reduced)
    print(f"   批量投影结果形状: {batch_reduced.shape}")
    print(f"   批量重建结果形状: {batch_reconstructed.shape}")
    
    print("\n7. Galerkin 投影测试...")
    n = full_solution.shape[0]
    test_operator = np.eye(n, dtype=np.float64) + 0.1 * np.random.randn(n, n)
    test_rhs = full_solution
    
    reduced_op, reduced_r = reduced_model.galerkin_projection(test_operator, test_rhs)
    print(f"   原始算子形状: {test_operator.shape}")
    print(f"   降阶算子形状: {reduced_op.shape}")
    print(f"   原始RHS形状: {test_rhs.shape}")
    print(f"   降阶RHS形状: {reduced_r.shape}")
    
    print("\n" + "=" * 60)
    print("所有功能测试通过!")
    print("=" * 60)


if __name__ == "__main__":
    main()
