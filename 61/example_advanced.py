import numpy as np
from snapshot import SnapshotGenerator
from pod import PODBasis
from reduced_model import ReducedModel
from error_est import ErrorEstimator
from parallel_snap import ParallelSnapshotGenerator
from online import ROMPipeline, ReducedOrderModel


def example_model(mu):
    n = 100
    x = np.linspace(0, 1, n)
    return np.sin(mu * np.pi * x) + 0.5 * np.cos(2 * mu * np.pi * x) + 0.1 * np.sin(5 * mu * np.pi * x)


def main():
    print("=" * 70)
    print("POD 模型降阶库 - 高级功能示例")
    print("=" * 70)
    
    parameter_range = np.linspace(0.5, 3.0, 50)
    
    print("\n" + "=" * 70)
    print("1. 自适应基维数选择与能量百分比截断")
    print("=" * 70)
    
    snapshot_gen = SnapshotGenerator(example_model, parameter_range)
    snapshots = snapshot_gen.generate()
    snapshot_matrix = snapshot_gen.get_snapshot_matrix()
    print(f"快照矩阵形状: {snapshot_matrix.shape}")
    
    pod_basis = PODBasis(snapshot_matrix)
    
    print("\n--- 不同能量阈值的比较 ---")
    for energy_pct in [90, 95, 99, 99.9]:
        basis = pod_basis.compute_basis(energy_percentage=energy_pct)
        print(f"能量 {energy_pct}%: 基维数 = {pod_basis.get_rank()}, "
              f"实际能量 = {pod_basis.get_energy():.4f}")
    
    print("\n--- 自适应基维数选择 ---")
    basis_adaptive = pod_basis.compute_basis(adaptive=True, min_rank=3, max_rank=20)
    print(f"自适应基维数: {pod_basis.get_rank()}")
    print(f"捕获能量: {pod_basis.get_energy():.4f}")
    
    print("\n--- 最优基维数搜索 ---")
    optimal_result = pod_basis.find_optimal_rank(target_energy=0.99, max_rank_penalty=0.001)
    print(f"最优基维数: {optimal_result['optimal_rank']}")
    print(f"最优能量: {optimal_result['energy_at_optimal']:.4f}")
    print(f"最优分数: {optimal_result['score']:.4f}")
    
    print("\n" + "=" * 70)
    print("2. 残差上界估计")
    print("=" * 70)
    
    error_estimator = ErrorEstimator(pod_basis)
    
    n = snapshot_matrix.shape[0]
    operator = np.eye(n) + 0.01 * np.random.randn(n, n)
    rhs = example_model(1.5)
    
    bound_info = error_estimator.get_residual_upper_bound(operator, rhs, rank=5)
    print(f"残差上界分析 (rank = 5):")
    print(f"  总上界: {bound_info['total_upper_bound']:.4e}")
    print(f"  连续性界: {bound_info['continuity_bound']:.4e}")
    print(f"  截断界1: {bound_info['truncation_bound1']:.4e}")
    print(f"  截断界2: {bound_info['truncation_bound2']:.4e}")
    print(f"  算子范数: {bound_info['operator_norm']:.4f}")
    
    print("\n--- 后验误差界 ---")
    residual_norm = np.linalg.norm(operator @ rhs)
    posterior_bound = error_estimator.get_a_posteriori_error_bound(residual_norm, operator, rank=5)
    print(f"  误差界: {posterior_bound['error_bound']:.4e}")
    print(f"  残差范数: {posterior_bound['residual_norm']:.4e}")
    
    print("\n--- 收敛率估计 ---")
    conv_rate = error_estimator.compute_convergence_rate(max_rank=15)
    print(f"  估计收敛率: {conv_rate['convergence_rate']:.4f}")
    
    print("\n" + "=" * 70)
    print("3. 并行快照计算")
    print("=" * 70)
    
    print("生成快照 (单进程)...")
    import time
    start = time.time()
    snapshots_serial = snapshot_gen.generate()
    time_serial = time.time() - start
    print(f"串行时间: {time_serial:.4f} 秒")
    
    print("\n生成快照 (并行)...")
    parallel_gen = ParallelSnapshotGenerator(example_model, parameter_range, n_workers=2)
    start = time.time()
    snapshots_parallel = parallel_gen.generate(verbose=False)
    time_parallel = time.time() - start
    print(f"并行时间: {time_parallel:.4f} 秒")
    print(f"加速比: {time_serial / time_parallel:.2f}x")
    
    exec_info = parallel_gen.get_execution_info()
    print(f"执行信息: {exec_info}")
    
    print("\n--- 批量并行生成 ---")
    start = time.time()
    snapshots_batched = parallel_gen.generate_batched(batch_size=10, verbose=False)
    time_batched = time.time() - start
    print(f"批量并行时间: {time_batched:.4f} 秒")
    
    print("\n--- 自适应采样 ---")
    adaptive_gen = ParallelSnapshotGenerator(example_model, parameter_range, n_workers=1)
    start = time.time()
    snapshots_adaptive = adaptive_gen.adaptive_sampling(
        max_snapshots=20, tol=1e-2, initial_samples=5, verbose=False
    )
    time_adaptive = time.time() - start
    print(f"自适应采样时间: {time_adaptive:.4f} 秒")
    print(f"选择的快照数: {len(snapshots_adaptive)}")
    
    print("\n" + "=" * 70)
    print("4. 离线-在线阶段分离")
    print("=" * 70)
    
    pipeline = ROMPipeline(example_model, parameter_range)
    
    print("\n--- 离线阶段 ---")
    start = time.time()
    pipeline.run_offline(n_train=20, energy_threshold=0.99, verbose=True)
    time_offline = time.time() - start
    print(f"离线阶段总时间: {time_offline:.4f} 秒")
    
    print("\n--- 在线阶段 ---")
    test_params = np.linspace(0.6, 2.9, 100)
    start = time.time()
    results = pipeline.run_online(test_params, full_model=example_model, verbose=True)
    time_online = time.time() - start
    print(f"在线阶段总时间: {time_online:.4f} 秒")
    print(f"平均每次评估: {time_online / len(test_params):.6f} 秒")
    
    if results['statistics'] is not None:
        print(f"\n在线阶段误差统计:")
        print(f"  平均误差: {results['statistics']['mean_error']:.4e}")
        print(f"  最大误差: {results['statistics']['max_error']:.4e}")
        print(f"  平均相对误差: {results['statistics']['mean_relative_error']:.4e}")
    
    print("\n--- 重建误差统计 ---")
    error_stats = pipeline.rom.get_error_statistics()
    for key, value in error_stats.items():
        print(f"  {key}: {value:.4e}")
    
    print("\n--- 加速比估计 ---")
    avg_full_time = time_serial / len(parameter_range)
    speedup_info = pipeline.rom.estimate_speedup(avg_full_time, n_params=100)
    print(f"  完整模型平均时间: {speedup_info['full_model_time_per_eval']:.4f} 秒")
    print(f"  降阶模型平均时间: {speedup_info['reduced_model_time_per_eval']:.6f} 秒")
    print(f"  估计加速比: {speedup_info['speedup']:.2f}x")
    
    print("\n" + "=" * 70)
    print("5. 完整POD工作流程")
    print("=" * 70)
    
    print("\n步骤1: 生成快照")
    params_train = np.linspace(0.5, 3.0, 30)
    gen = ParallelSnapshotGenerator(example_model, params_train, n_workers=2)
    snaps = gen.generate(verbose=False)
    print(f"  训练快照数: {len(snaps)}")
    
    print("\n步骤2: 计算POD基 (自适应选择)")
    snap_matrix = snaps.reshape(len(snaps), -1).T
    pod = PODBasis(snap_matrix)
    pod.compute_basis(adaptive=True, min_rank=2, max_rank=15)
    print(f"  基维数: {pod.get_rank()}")
    print(f"  能量捕获: {pod.get_energy():.4f}")
    
    print("\n步骤3: 构建降阶模型")
    rom = ReducedOrderModel(pod, params_train, snaps)
    rom.train(interp_method='linear')
    print("  降阶模型已训练")
    
    print("\n步骤4: 在线评估")
    mu_test = 1.75
    prediction = rom.predict(mu_test)
    true_sol = example_model(mu_test)
    error = np.linalg.norm(prediction - true_sol)
    print(f"  测试参数: mu = {mu_test}")
    print(f"  预测误差: {error:.4e}")
    
    print("\n" + "=" * 70)
    print("所有高级功能演示完成!")
    print("=" * 70)


if __name__ == "__main__":
    main()
