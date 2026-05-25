import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import cm
from acoustic_simulator import (
    AcousticSimulator,
    RoomGeometry,
    SoundSource,
    DynamicSource,
    AbsorptionBand,
    RT60Calculator,
    SoundFieldVisualizer,
    STANDARD_OCTAVE_BANDS,
    STANDARD_13_OCTAVE_BANDS,
)
from acoustic_simulator.visualization import n_mirrors_per_order
import time

plt.rcParams['figure.dpi'] = 80
plt.rcParams['savefig.dpi'] = 100


def example_1_adaptive_order():
    """示例1: 自适应镜像阶数算法演示"""
    print("\n" + "=" * 70)
    print("示例 1: 自适应镜像阶数算法")
    print("=" * 70)

    room_configs = [
        {"dims": np.array([4.0, 3.0, 2.5]), "absorption": 0.2, "name": "小房间 (吸声小)"},
        {"dims": np.array([8.0, 6.0, 3.5]), "absorption": 0.2, "name": "大房间 (吸声小)"},
        {"dims": np.array([8.0, 6.0, 3.5]), "absorption": 0.8, "name": "大房间 (吸声大)"},
    ]

    results = []
    for config in room_configs:
        room = RoomGeometry(
            dimensions=config["dims"],
            absorption=config["absorption"],
            adaptive_order=True,
            adaptive_order_db_threshold=60.0,
            use_pra=False
        )

        source_pos = np.array([1.0, 1.0, 1.2])
        receiver_pos = config["dims"] - np.array([1.0, 1.0, 1.2])

        order = room.compute_adaptive_max_order(source_pos, receiver_pos)
        n_mirrors = n_mirrors_per_order(order, 3)

        print(f"\n{config['name']}:")
        print(f"  房间尺寸: {config['dims']} m")
        print(f"  平均吸声系数: {config['absorption']:.2f}")
        print(f"  声源-接收点距离: {np.linalg.norm(source_pos - receiver_pos):.2f} m")
        print(f"  自适应最大阶数: {order}")
        print(f"  镜像源总数: {n_mirrors:,}")

        results.append({
            "config": config,
            "order": order,
            "n_mirrors": n_mirrors,
            "room": room,
            "source_pos": source_pos,
            "receiver_pos": receiver_pos,
        })

    visualizer = SoundFieldVisualizer()

    fig, axes = plt.subplots(1, 3, figsize=(18, 5))

    for idx, result in enumerate(results):
        ax = axes[idx]
        visualizer.plot_adaptive_order_analysis(
            result["source_pos"],
            result["receiver_pos"],
            result["config"]["dims"],
            max_order_range=(1, 8),
            ax=[ax, None],
            show=False
        )
        ax.set_title(result["config"]["name"], fontsize=11)

    plt.tight_layout()
    plt.savefig('v2_example_1_adaptive_order.png', dpi=100)
    print("\n自适应阶数分析图已保存到 v2_example_1_adaptive_order.png")
    plt.close()

    room = RoomGeometry(
        dimensions=np.array([5.0, 4.0, 3.0]),
        absorption=0.5,
        adaptive_order=True,
        use_pra=False
    )

    sim = AcousticSimulator(room, fs=16000, use_gpu=False)
    sim.add_source(SoundSource(position=np.array([1.0, 1.0, 1.5])))
    sim.add_receiver(np.array([4.0, 3.0, 1.5]))

    print("\n正在使用自适应阶数计算脉冲响应...")
    t0 = time.time()
    ir = sim.compute_impulse_responses(duration=1.0)
    t1 = time.time()

    print(f"模拟完成，使用最大阶数: {room.max_order}")
    print(f"计算耗时: {t1 - t0:.3f}s")
    print(f"镜像源数量: {len(sim.mirror_sources):,}")

    fig, ax = plt.subplots(figsize=(10, 4))
    visualizer.plot_impulse_response(
        ir[0, 0, :], sim.fs,
        title=f"Impulse Response (Adaptive Order = {room.max_order})",
        ax=ax, show=False
    )
    plt.tight_layout()
    plt.savefig('v2_example_1_ir.png', dpi=100)
    plt.close()

    return results


def example_2_band_absorption():
    """示例2: 频带吸声系数模型"""
    print("\n" + "=" * 70)
    print("示例 2: 频带吸声系数模型")
    print("=" * 70)

    frequencies = STANDARD_OCTAVE_BANDS
    print(f"标准倍频程: {frequencies}")

    abs_coeffs_wall = np.array([0.1, 0.15, 0.2, 0.3, 0.4, 0.5, 0.6])
    abs_coeffs_floor = np.array([0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8])
    abs_coeffs_ceiling = np.array([0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7])

    absorption_2d = np.array([
        abs_coeffs_wall,
        abs_coeffs_wall,
        abs_coeffs_wall,
        abs_coeffs_wall,
        abs_coeffs_floor,
        abs_coeffs_ceiling,
    ])

    print(f"\n墙面吸声系数形状: {absorption_2d.shape} (6 walls x 7 bands)")
    print("各频带吸声系数:")
    for i, freq in enumerate(frequencies):
        print(f"  {freq:4.0f}Hz: 墙={absorption_2d[0, i]:.2f}, 地板={absorption_2d[4, i]:.2f}, 天花板={absorption_2d[5, i]:.2f}")

    abs_band = AbsorptionBand(frequencies=frequencies, coefficients=absorption_2d.mean(axis=0))

    room = RoomGeometry(
        dimensions=np.array([6.0, 5.0, 3.0]),
        absorption=absorption_2d,
        adaptive_order=True,
        band_type="octave",
        use_pra=False
    )

    print(f"\n房间频带数量: {room.n_bands}")
    print(f"各墙面面积: {room.get_wall_surface_areas()}")

    sim = AcousticSimulator(room, fs=16000, use_gpu=False)
    sim.add_source(SoundSource(position=np.array([1.0, 1.0, 1.5])))
    sim.add_receiver(np.array([5.0, 4.0, 1.5]))

    print("\n正在计算各频带脉冲响应...")
    t0 = time.time()
    band_irs = sim.compute_band_impulse_responses(duration=1.5)
    t1 = time.time()

    print(f"频带IR形状: {band_irs.shape} (receivers x sources x bands x samples)")
    print(f"计算耗时: {t1 - t0:.3f}s")

    rt60_calc = RT60Calculator(fs=16000)

    rt60_measured = rt60_calc.calculate_rt60_from_band_irs(
        band_irs[0, 0, :, :],
        frequencies,
        method="t30"
    )

    rt60_sabine = rt60_calc.calculate_rt60_theoretical_bands(room, method="sabine")
    rt60_eyring = rt60_calc.calculate_rt60_theoretical_bands(room, method="eyring")

    print("\n各频带 RT60 计算结果:")
    print(f"{'频率':>8} {'实测 T30':>12} {'Sabine':>12} {'Eyring':>12}")
    print("-" * 50)
    for i, freq in enumerate(frequencies):
        print(f"{freq:>7.0f}Hz {rt60_measured['rt60_bands'][i]:>11.3f}s {rt60_sabine['rt60_bands'][i]:>11.3f}s {rt60_eyring['rt60_bands'][i]:>11.3f}s")

    visualizer = SoundFieldVisualizer()

    fig = plt.figure(figsize=(18, 12))
    gs = fig.add_gridspec(2, 2, hspace=0.3, wspace=0.3)

    ax1 = fig.add_subplot(gs[0, 0])
    visualizer.plot_band_impulse_responses(
        band_irs[0, 0, :, :],
        frequencies,
        sim.fs,
        title="Impulse Responses by Frequency Band",
        axs=[ax1] + [None] * 6,
        show=False
    )

    ax2 = fig.add_subplot(gs[0, 1])
    visualizer.plot_band_edc_comparison(
        rt60_measured['edc_bands'],
        frequencies,
        rt60_bands=rt60_measured['rt60_bands'],
        fs=sim.fs,
        title="EDC Comparison by Frequency Band",
        ax=ax2,
        show=False
    )

    ax3 = fig.add_subplot(gs[1, :])
    rt60_data = {
        'Measured (T30)': rt60_measured['rt60_bands'],
        'Sabine Theory': rt60_sabine['rt60_bands'],
        'Eyring Theory': rt60_eyring['rt60_bands'],
    }
    visualizer.plot_rt60_band_comparison(
        rt60_data,
        frequencies,
        title="RT60 Comparison by Frequency Band",
        ax=ax3,
        show=False
    )

    plt.tight_layout()
    plt.savefig('v2_example_2_band_absorption.png', dpi=100)
    print("\n频带吸声分析图已保存到 v2_example_2_band_absorption.png")
    plt.close()

    return band_irs, rt60_measured


def example_3_optimized_dynamic():
    """示例3: 优化的动态声源模拟 - 预计算+插值"""
    print("\n" + "=" * 70)
    print("示例 3: 优化的动态声源模拟 (预计算 + 插值)")
    print("=" * 70)

    room = RoomGeometry(
        dimensions=np.array([8.0, 6.0]),
        absorption=0.4,
        max_order=2,
        adaptive_order=False,
        use_pra=False
    )

    sim = AcousticSimulator(room, fs=8000, use_gpu=False)

    dynamic_source = DynamicSource(position=np.array([1.0, 3.0]))
    dynamic_source.set_circular_trajectory(
        center=np.array([4.0, 3.0]),
        radius=2.5,
        angular_velocity=0.5 * np.pi,
        start_time=0.0,
        duration=4.0
    )
    dynamic_source.generate_impulse(fs=8000)

    sim.add_source(dynamic_source)

    receiver_positions = sim.add_receivers_grid(
        x_range=(1.0, 7.0),
        y_range=(1.0, 5.0),
        resolution=0.5
    )
    print(f"接收器数量: {len(receiver_positions)}")

    n_time_steps = 100
    time_points = np.linspace(0, 4.0, n_time_steps)

    print(f"\n时间步数量: {n_time_steps}")

    print("\n方法1: 原始方法 (每个时间步重新计算)...")
    t0 = time.time()
    results_original = sim.simulate_dynamic_source(
        dynamic_source, time_points,
        use_optimized=False,
        max_order=2,
        duration=0.5
    )
    t1 = time.time()
    time_original = t1 - t0
    print(f"原始方法耗时: {time_original:.3f}s")

    print("\n方法2: 优化方法 (预计算+插值)...")
    t0 = time.time()
    sim.precompute_static_part(max_order=2)
    t_pre = time.time() - t0
    print(f"预计算耗时: {t_pre:.3f}s")

    t0 = time.time()
    results_optimized = sim.simulate_dynamic_source(
        dynamic_source, time_points,
        use_optimized=True,
        max_order=2,
        duration=0.5
    )
    t1 = time.time()
    time_optimized = t1 - t0
    print(f"优化方法耗时: {time_optimized:.3f}s")
    print(f"总耗时: {time_optimized + t_pre:.3f}s")

    speedup = time_original / max(time_optimized + t_pre, 1e-6)
    print(f"\n加速比: {speedup:.2f}x")

    precomputed = results_optimized.get('precomputed_ir')
    if precomputed:
        print(f"插值点数量: {len(precomputed.time_points)}")
        print(f"插值时间点: {precomputed.time_points}")

    ir_orig = results_original['impulse_responses'][50, 0, 0, :1000]
    ir_opt = results_optimized['impulse_responses'][50, 0, 0, :1000]
    mae = np.mean(np.abs(ir_orig - ir_opt))
    max_error = np.max(np.abs(ir_orig - ir_opt))
    print(f"\nIR 平均绝对误差: {mae:.6f}")
    print(f"IR 最大误差: {max_error:.6f}")

    visualizer = SoundFieldVisualizer()

    fig, axes = plt.subplots(2, 2, figsize=(16, 12))

    visualizer.plot_dynamic_source_trajectory(
        results_optimized['source_positions'],
        room.dimensions,
        receiver_positions=receiver_positions,
        title="Dynamic Source Trajectory",
        ax=axes[0, 0],
        show=False
    )

    if precomputed:
        axes[0, 0].scatter(precomputed.source_positions[:, 0],
                          precomputed.source_positions[:, 1],
                          c='red', s=150, marker='x', linewidths=3,
                          label='Interpolation Points', zorder=15)
        axes[0, 0].legend()

    t = sim.get_time_axis(duration=0.5)[:1000]
    axes[0, 1].plot(t, ir_orig, 'b-', linewidth=1.5, label='Original', alpha=0.7)
    axes[0, 1].plot(t, ir_opt, 'r--', linewidth=1.5, label='Optimized', alpha=0.7)
    axes[0, 1].set_xlabel('Time [s]')
    axes[0, 1].set_ylabel('Amplitude')
    axes[0, 1].set_title('IR Comparison (t=2.0s)')
    axes[0, 1].grid(True, alpha=0.3)
    axes[0, 1].legend()

    pressure_orig = results_original['pressure_levels'][:, 0, 0, :].mean(axis=1)
    pressure_opt = results_optimized['pressure_levels'][:, 0, 0, :].mean(axis=1)

    axes[1, 0].plot(time_points, pressure_orig, 'b-', linewidth=2, label='Original', alpha=0.7)
    axes[1, 0].plot(time_points, pressure_opt, 'r--', linewidth=2, label='Optimized', alpha=0.7)
    axes[1, 0].set_xlabel('Time [s]')
    axes[1, 0].set_ylabel('Average SPL [dB]')
    axes[1, 0].set_title('Sound Pressure Level vs Time')
    axes[1, 0].grid(True, alpha=0.3)
    axes[1, 0].legend()

    methods = ['Original\n(100 steps)', 'Optimized\n(Precompute + 20 interp)']
    times = [time_original, time_optimized + t_pre]
    bars = axes[1, 1].bar(methods, times, color=['steelblue', 'orange'], alpha=0.8)
    axes[1, 1].set_ylabel('Time [s]')
    axes[1, 1].set_title(f'Performance Comparison (Speedup: {speedup:.2f}x)')
    axes[1, 1].grid(True, alpha=0.3, axis='y')
    for bar, t_val in zip(bars, times):
        axes[1, 1].text(bar.get_x() + bar.get_width() / 2., bar.get_height(),
                       f'{t_val:.2f}s', ha='center', va='bottom', fontsize=12)

    plt.tight_layout()
    plt.savefig('v2_example_3_dynamic_optimized.png', dpi=100)
    print("\n动态声源优化对比图已保存到 v2_example_3_dynamic_optimized.png")
    plt.close()

    fig, axes = plt.subplots(2, 3, figsize=(18, 10))
    time_indices = [0, 20, 40, 60, 80, 99]

    for idx, (t_idx, ax) in enumerate(zip(time_indices, axes.flatten())):
        pressure_at_t = results_optimized['pressure_levels'][t_idx, 0, 0, :]
        visualizer.plot_sound_pressure_heatmap(
            receiver_positions,
            pressure_at_t,
            room.dimensions,
            frequency=1000,
            title=f"t={time_points[t_idx]:.2f}s",
            ax=ax,
            show=False
        )
        ax.scatter([results_optimized['source_positions'][t_idx, 0]],
                  [results_optimized['source_positions'][t_idx, 1]],
                  c='red', s=200, marker='*', edgecolors='black',
                  linewidths=2, zorder=10)

    plt.tight_layout()
    plt.savefig('v2_example_3_dynamic_heatmaps.png', dpi=100)
    print("动态声压热力图已保存到 v2_example_3_dynamic_heatmaps.png")
    plt.close()

    return results_original, results_optimized


def example_4_13_octave_bands():
    """示例4: 1/3倍频程带模型"""
    print("\n" + "=" * 70)
    print("示例 4: 1/3 倍频程带模型")
    print("=" * 70)

    frequencies = STANDARD_13_OCTAVE_BANDS
    print(f"1/3倍频程数量: {len(frequencies)}")
    print(f"频率范围: {frequencies[0]:.0f} - {frequencies[-1]:.0f} Hz")

    alpha = 0.1 + 0.6 * (frequencies / 1000) ** 0.5
    alpha = np.clip(alpha, 0.05, 0.95)

    abs_band = AbsorptionBand(frequencies=frequencies, coefficients=alpha)

    room = RoomGeometry(
        dimensions=np.array([5.0, 4.0, 3.0]),
        absorption=abs_band,
        adaptive_order=True,
        band_type="1/3_octave",
        frequencies=frequencies,
        use_pra=False
    )

    print(f"\n房间频带数量: {room.n_bands}")
    print(f"平均吸声系数随频率递增: {room.absorption_band.coefficients}")

    sim = AcousticSimulator(room, fs=32000, use_gpu=False)
    sim.add_source(SoundSource(position=np.array([1.0, 1.0, 1.5])))
    sim.add_receiver(np.array([4.0, 3.0, 1.5]))

    print("\n正在计算1/3倍频程脉冲响应...")
    band_irs = sim.compute_band_impulse_responses(max_order=2, duration=1.0)
    print(f"频带IR形状: {band_irs.shape}")

    rt60_calc = RT60Calculator(fs=32000)
    rt60_result = rt60_calc.calculate_rt60_from_band_irs(
        band_irs[0, 0, :, :],
        frequencies,
        method="t30"
    )

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 10))

    visualizer = SoundFieldVisualizer()

    ax1.semilogx(frequencies, rt60_result['rt60_bands'], 'bo-',
                linewidth=2, markersize=6, label='RT60 (T30)')
    ax1.set_xlabel('Frequency [Hz]')
    ax1.set_ylabel('RT60 [s]')
    ax1.set_title('RT60 for 1/3 Octave Bands')
    ax1.grid(True, alpha=0.3, which='both')
    ax1.legend()
    ax1.set_ylim(bottom=0)

    for freq in frequencies:
        ax1.axvline(freq, color='gray', linestyle=':', linewidth=0.5, alpha=0.2)

    n_colors = (len(frequencies) + 1) // 2
    colors = cm.viridis(np.linspace(0, 1, n_colors))
    for i in range(0, len(frequencies), 2):
        ir = band_irs[0, 0, i, :500]
        t = np.arange(len(ir)) / sim.fs
        ax2.plot(t, ir + i * 0.0005, color=colors[i // 2],
                linewidth=1, label=f'{frequencies[i]:.0f}Hz')
    ax2.set_xlabel('Time [s]')
    ax2.set_ylabel('Amplitude (offset)')
    ax2.set_title('1/3 Octave Band Impulse Responses (offset for clarity)')
    ax2.grid(True, alpha=0.3)
    ax2.legend(loc='upper right', fontsize=8, ncol=2)

    plt.tight_layout()
    plt.savefig('v2_example_4_13_octave.png', dpi=100)
    print("\n1/3倍频程分析图已保存到 v2_example_4_13_octave.png")
    plt.close()

    return band_irs, rt60_result


def example_5_comparison():
    """示例5: 固定阶数 vs 自适应阶数性能对比"""
    print("\n" + "=" * 70)
    print("示例 5: 固定阶数 vs 自适应阶数性能对比")
    print("=" * 70)

    room_dims = np.array([6.0, 5.0, 3.5])
    source_pos = np.array([1.0, 1.0, 1.5])
    receiver_pos = np.array([5.0, 4.0, 2.0])

    fixed_orders = [1, 2, 3, 4, 5, 6]
    results = []

    for max_order in fixed_orders:
        room = RoomGeometry(
            dimensions=room_dims,
            absorption=0.5,
            max_order=max_order,
            adaptive_order=False,
            use_pra=False
        )

        sim = AcousticSimulator(room, fs=16000, use_gpu=False)
        sim.add_source(SoundSource(position=source_pos))
        sim.add_receiver(receiver_pos)

        t0 = time.time()
        ir = sim.compute_impulse_responses(duration=1.0)
        t1 = time.time()

        n_mirrors = len(sim.mirror_sources)
        ir_energy = np.sum(ir[0, 0, :] ** 2)

        results.append({
            'order': max_order,
            'time': t1 - t0,
            'n_mirrors': n_mirrors,
            'energy': ir_energy,
        })

        print(f"阶数 {max_order}: 镜像源={n_mirrors:>6,}, 时间={t1-t0:.3f}s, 能量={ir_energy:.6e}")

    room_adaptive = RoomGeometry(
        dimensions=room_dims,
        absorption=0.5,
        adaptive_order=True,
        adaptive_order_db_threshold=60.0,
        use_pra=False
    )

    adaptive_order = room_adaptive.compute_adaptive_max_order(source_pos, receiver_pos)

    sim_adaptive = AcousticSimulator(room_adaptive, fs=16000, use_gpu=False)
    sim_adaptive.add_source(SoundSource(position=source_pos))
    sim_adaptive.add_receiver(receiver_pos)

    t0 = time.time()
    ir_adaptive = sim_adaptive.compute_impulse_responses(duration=1.0)
    t1 = time.time()

    adaptive_result = {
        'order': adaptive_order,
        'time': t1 - t0,
        'n_mirrors': len(sim_adaptive.mirror_sources),
        'energy': np.sum(ir_adaptive[0, 0, :] ** 2),
    }

    print(f"\n自适应阶数 {adaptive_order}: 镜像源={adaptive_result['n_mirrors']:>6,}, 时间={adaptive_result['time']:.3f}s, 能量={adaptive_result['energy']:.6e}")

    orders = [r['order'] for r in results]
    times = [r['time'] for r in results]
    mirrors = [r['n_mirrors'] for r in results]
    energies = np.array([r['energy'] for r in results])
    energies_rel = 10 * np.log10(energies / max(energies) + 1e-10)

    fig, axes = plt.subplots(1, 3, figsize=(18, 5))

    axes[0].plot(orders, times, 'bo-', linewidth=2, markersize=8, label='Fixed Order')
    axes[0].plot([adaptive_order], [adaptive_result['time']], 'r*',
                markersize=20, markeredgecolor='black', label='Adaptive Order')
    axes[0].set_xlabel('Max Reflection Order')
    axes[0].set_ylabel('Computation Time [s]')
    axes[0].set_title('Computation Time vs Order')
    axes[0].grid(True, alpha=0.3)
    axes[0].legend()

    axes[1].semilogy(orders, mirrors, 'go-', linewidth=2, markersize=8, label='Fixed Order')
    axes[1].semilogy([adaptive_order], [adaptive_result['n_mirrors']], 'r*',
                    markersize=20, markeredgecolor='black', label='Adaptive Order')
    axes[1].set_xlabel('Max Reflection Order')
    axes[1].set_ylabel('Number of Mirror Sources')
    axes[1].set_title('Mirror Sources vs Order')
    axes[1].grid(True, alpha=0.3)
    axes[1].legend()

    axes[2].plot(orders, energies_rel, 'mo-', linewidth=2, markersize=8, label='Fixed Order')
    axes[2].plot([adaptive_order], [10 * np.log10(adaptive_result['energy'] / max(energies) + 1e-10)], 'r*',
                markersize=20, markeredgecolor='black', label='Adaptive Order')
    axes[2].axhline(-60, color='k', linestyle='--', label='-60 dB threshold')
    axes[2].set_xlabel('Max Reflection Order')
    axes[2].set_ylabel('Relative Energy [dB]')
    axes[2].set_title('Energy Convergence')
    axes[2].grid(True, alpha=0.3)
    axes[2].legend()

    plt.tight_layout()
    plt.savefig('v2_example_5_performance.png', dpi=100)
    print("\n性能对比图已保存到 v2_example_5_performance.png")
    plt.close()

    return results, adaptive_result


def main():
    """运行所有 v2 示例"""
    print("=" * 70)
    print("声场模拟工具 v2.0 - 新功能示例")
    print("=" * 70)

    try:
        example_1_adaptive_order()
    except Exception as e:
        print(f"示例1执行出错: {e}")
        import traceback
        traceback.print_exc()

    try:
        example_2_band_absorption()
    except Exception as e:
        print(f"示例2执行出错: {e}")
        import traceback
        traceback.print_exc()

    try:
        example_3_optimized_dynamic()
    except Exception as e:
        print(f"示例3执行出错: {e}")
        import traceback
        traceback.print_exc()

    try:
        example_4_13_octave_bands()
    except Exception as e:
        print(f"示例4执行出错: {e}")
        import traceback
        traceback.print_exc()

    try:
        example_5_comparison()
    except Exception as e:
        print(f"示例5执行出错: {e}")
        import traceback
        traceback.print_exc()

    print("\n" + "=" * 70)
    print("所有 v2 示例运行完成!")
    print("=" * 70)


if __name__ == "__main__":
    main()
