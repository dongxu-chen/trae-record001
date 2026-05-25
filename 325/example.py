import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from acoustic_simulator import (
    AcousticSimulator,
    RoomGeometry,
    SoundSource,
    DynamicSource,
    RT60Calculator,
    SoundFieldVisualizer
)

plt.rcParams['figure.dpi'] = 80
plt.rcParams['savefig.dpi'] = 100


def example_1_basic_simulation():
    """示例1: 基本声场模拟 - 单声源、单接收点"""
    print("\n" + "=" * 60)
    print("示例 1: 基本声场模拟")
    print("=" * 60)

    room = RoomGeometry(
        dimensions=np.array([5.0, 4.0, 3.0]),
        absorption=0.5,
        max_order=3,
        use_pra=False
    )

    simulator = AcousticSimulator(
        room_geometry=room,
        fs=44100,
        use_gpu=False
    )

    source = SoundSource(position=np.array([1.0, 1.0, 1.5]))
    source.generate_impulse(fs=44100)
    simulator.add_source(source)

    simulator.add_receiver(np.array([4.0, 3.0, 1.5]))

    print("正在计算镜像源...")
    mirror_sources, orders, _ = simulator.compute_mirror_sources(max_order=2)
    print(f"生成镜像源数量: {len(mirror_sources)}")
    print(f"最大反射阶数: {np.max(orders)}")

    print("正在计算脉冲响应...")
    ir = simulator.compute_impulse_responses(max_order=2, duration=1.0)
    print(f"脉冲响应形状: {ir.shape}")
    print(f"模拟耗时: {simulator.simulation_time:.3f}s")

    rt60_calc = RT60Calculator(fs=44100)
    rt60_result = rt60_calc.calculate_rt60(
        ir[0, 0, :],
        method="t30",
        freq_bands=np.array([125, 250, 500, 1000, 2000, 4000])
    )
    print(f"\nRT60 计算结果:")
    print(f"  总体 RT60 (T30): {rt60_result['rt60']:.3f}s")
    print(f"  T20: {rt60_result['t20']:.3f}s")
    print(f"  T30: {rt60_result['t30']:.3f}s")

    if 'rt60_bands' in rt60_result:
        for freq, rt in zip(rt60_result['frequencies'], rt60_result['rt60_bands']):
            print(f"  {freq}Hz: {rt:.3f}s")

    sabine_rt60 = rt60_calc.calculate_sabine_rt60(
        volume=room.get_volume(),
        surface_area=room.get_surface_area(),
        absorption_coeff=room.get_average_absorption()
    )
    print(f"\n理论 RT60 (Sabine): {sabine_rt60:.3f}s")

    visualizer = SoundFieldVisualizer()

    fig, axes = plt.subplots(2, 2, figsize=(14, 10))

    visualizer.plot_impulse_response(
        ir[0, 0, :], simulator.fs,
        title="Impulse Response (Receiver 0, Source 0)",
        ax=axes[0, 0], show=False
    )

    visualizer.plot_edc(
        rt60_result['edc'], simulator.fs, rt60=rt60_result['rt60'],
        title="Energy Decay Curve",
        ax=axes[0, 1], show=False
    )

    if 'rt60_bands' in rt60_result:
        visualizer.plot_rt60_frequency(
            rt60_result['frequencies'], rt60_result['rt60_bands'],
            title="RT60 by Frequency Band",
            ax=axes[1, 0], show=False
        )

    visualizer.plot_mirror_sources(
        mirror_sources,
        simulator.source_manager.get_positions(),
        np.array([rec.position for rec in simulator.receivers])[:, :3],
        room.dimensions,
        orders=orders,
        title="Mirror Sources (2D Projection)",
        ax=axes[1, 1], show=False
    )

    plt.tight_layout()
    plt.savefig('example_1_basic.png', dpi=100)
    print("\n结果已保存到 example_1_basic.png")
    plt.close()

    return simulator, ir, rt60_result


def example_2_multi_source_simulation():
    """示例2: 多声源模拟"""
    print("\n" + "=" * 60)
    print("示例 2: 多声源模拟")
    print("=" * 60)

    room = RoomGeometry(
        dimensions=np.array([6.0, 5.0]),
        absorption=[0.3, 0.3, 0.5, 0.5, 0.7, 0.7][:4],
        max_order=2,
        use_pra=False
    )

    simulator = AcousticSimulator(
        room_geometry=room,
        fs=44100,
        use_gpu=False
    )

    source1 = SoundSource(position=np.array([1.0, 1.0]), amplitude=1.0)
    source1.generate_tone(frequency=440, duration=0.5, fs=44100)
    simulator.add_source(source1)

    source2 = SoundSource(position=np.array([5.0, 1.0]), amplitude=0.8, delay=0.1)
    source2.generate_tone(frequency=880, duration=0.5, fs=44100)
    simulator.add_source(source2)

    source3 = SoundSource(position=np.array([3.0, 4.0]), amplitude=0.6, delay=0.2)
    source3.generate_noise(duration=0.5, fs=44100, noise_type="pink")
    simulator.add_source(source3)

    receiver_positions = simulator.add_receivers_grid(
        x_range=(0.5, 5.5),
        y_range=(0.5, 4.5),
        resolution=0.3
    )
    print(f"接收器网格数量: {len(receiver_positions)}")
    print(f"声源数量: {len(simulator.source_manager)}")

    print("正在计算声压分布...")
    frequencies = np.array([250, 500, 1000, 2000])
    pressure = simulator.compute_sound_pressure(frequencies)
    print(f"声压数据形状: {pressure.shape}")

    visualizer = SoundFieldVisualizer()

    fig, axes = plt.subplots(2, 2, figsize=(14, 12))

    for idx, (freq, ax) in enumerate(zip(frequencies, axes.flatten())):
        pressure_at_freq = np.abs(pressure[idx, :, :]).sum(axis=0)
        visualizer.plot_sound_pressure_heatmap(
            receiver_positions,
            pressure_at_freq,
            room.dimensions,
            frequency=freq,
            title=f"Sound Pressure Distribution",
            ax=ax, show=False, contour=True
        )

        source_pos = simulator.source_manager.get_positions()
        ax.scatter(source_pos[:, 0], source_pos[:, 1],
                  c='red', s=150, marker='*', edgecolors='black',
                  linewidths=2, label='Sources', zorder=10)
        if idx == 0:
            ax.legend()

    plt.tight_layout()
    plt.savefig('example_2_multi_source.png', dpi=100)
    print("\n结果已保存到 example_2_multi_source.png")
    plt.close()

    return simulator, pressure


def example_3_dynamic_source():
    """示例3: 动态声源模拟"""
    print("\n" + "=" * 60)
    print("示例 3: 动态声源模拟")
    print("=" * 60)

    room = RoomGeometry(
        dimensions=np.array([8.0, 6.0]),
        absorption=0.4,
        max_order=1,
        use_pra=False
    )

    simulator = AcousticSimulator(
        room_geometry=room,
        fs=16000,
        use_gpu=False
    )

    dynamic_source = DynamicSource(
        position=np.array([1.0, 3.0]),
        amplitude=1.0
    )
    dynamic_source.set_circular_trajectory(
        center=np.array([4.0, 3.0]),
        radius=2.0,
        angular_velocity=0.5 * np.pi,
        start_time=0.0,
        duration=4.0
    )
    dynamic_source.generate_tone(frequency=1000, duration=0.1, fs=16000)

    receiver_positions = simulator.add_receivers_grid(
        x_range=(1.0, 7.0),
        y_range=(1.0, 5.0),
        resolution=0.4
    )
    print(f"接收器数量: {len(receiver_positions)}")

    time_points = np.linspace(0, 4.0, 20)
    print("正在进行动态声源模拟...")
    results = simulator.simulate_dynamic_source(dynamic_source, time_points)
    print(f"模拟时间点: {len(time_points)}")
    print(f"源位置轨迹形状: {results['source_positions'].shape}")

    visualizer = SoundFieldVisualizer()

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 6))

    visualizer.plot_dynamic_source_trajectory(
        results['source_positions'],
        room.dimensions,
        receiver_positions=receiver_positions,
        title="Dynamic Source Trajectory",
        ax=ax1, show=False
    )

    pressure_flat = results['pressure_levels'][:, 0, 0, :]
    avg_pressure = np.mean(pressure_flat, axis=1)
    ax2.plot(time_points, avg_pressure, 'b-o', linewidth=2, markersize=6)
    ax2.set_xlabel('Time [s]')
    ax2.set_ylabel('Average SPL [dB]')
    ax2.set_title('Average Sound Pressure Level vs Time')
    ax2.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig('example_3_dynamic_source.png', dpi=100)
    print("\n结果已保存到 example_3_dynamic_source.png")
    plt.close()

    if len(time_points) >= 4:
        fig, axes = plt.subplots(2, 2, figsize=(14, 12))
        time_indices = [0, 6, 13, 19]

        for idx, (t_idx, ax) in enumerate(zip(time_indices, axes.flatten())):
            pressure_at_t = pressure_flat[t_idx]
            visualizer.plot_sound_pressure_heatmap(
                receiver_positions,
                pressure_at_t,
                room.dimensions,
                frequency=1000,
                title=f"SPL at t={time_points[t_idx]:.1f}s",
                ax=ax, show=False
            )

            ax.scatter([results['source_positions'][t_idx, 0]],
                      [results['source_positions'][t_idx, 1]],
                      c='red', s=200, marker='*', edgecolors='black',
                      linewidths=2, zorder=10)

        plt.tight_layout()
        plt.savefig('example_3_dynamic_heatmaps.png', dpi=100)
        print("动态热力图已保存到 example_3_dynamic_heatmaps.png")
        plt.close()

    return simulator, results


def example_4_rt60_comparison():
    """示例4: RT60计算方法比较"""
    print("\n" + "=" * 60)
    print("示例 4: RT60 计算方法比较")
    print("=" * 60)

    room = RoomGeometry(
        dimensions=np.array([6.0, 5.0, 3.0]),
        absorption=0.3,
        max_order=4,
        use_pra=False
    )

    simulator = AcousticSimulator(
        room_geometry=room,
        fs=44100,
        use_gpu=False
    )

    source = SoundSource(position=np.array([1.0, 1.0, 1.5]))
    source.generate_impulse(fs=44100)
    simulator.add_source(source)
    simulator.add_receiver(np.array([5.0, 4.0, 1.5]))

    print("正在计算脉冲响应...")
    ir = simulator.compute_impulse_responses(max_order=4, duration=2.0)

    rt60_calc = RT60Calculator(fs=44100)

    methods = ["t10", "t20", "t30", "lundeby", "interpolation"]
    rt60_values = {}

    print("\nRT60 计算结果:")
    for method in methods:
        result = rt60_calc.calculate_rt60(ir[0, 0, :], method=method)
        rt60_values[method.upper()] = result['rt60']
        print(f"  {method.upper():12s}: {result['rt60']:.4f}s")

    surface_areas = [
        6.0 * 3.0, 6.0 * 3.0,
        5.0 * 3.0, 5.0 * 3.0,
        6.0 * 5.0, 6.0 * 5.0
    ]
    absorption_coeffs = [0.3] * 6

    sabine = rt60_calc.calculate_sabine_rt60(
        room.get_volume(), room.get_surface_area(), 0.3
    )
    eyring = rt60_calc.calculate_eyring_rt60(
        room.get_volume(), room.get_surface_area(), 0.3
    )
    millington = rt60_calc.calculate_millington_sette_rt60(
        room.get_volume(), surface_areas, absorption_coeffs
    )
    fitzroy = rt60_calc.calculate_fitzroy_rt60(
        room.get_volume(), surface_areas, absorption_coeffs
    )

    rt60_values['Sabine'] = sabine
    rt60_values['Eyring'] = eyring
    rt60_values['Millington'] = millington
    rt60_values['Fitzroy'] = fitzroy

    print("\n理论模型 RT60:")
    print(f"  {'Sabine':12s}: {sabine:.4f}s")
    print(f"  {'Eyring':12s}: {eyring:.4f}s")
    print(f"  {'Millington':12s}: {millington:.4f}s")
    print(f"  {'Fitzroy':12s}: {fitzroy:.4f}s")

    visualizer = SoundFieldVisualizer()

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 6))

    measured_keys = [k for k in rt60_values.keys() if k in ['T10', 'T20', 'T30', 'LUNDEBY', 'INTERPOLATION']]
    theoretical_keys = [k for k in rt60_values.keys() if k in ['Sabine', 'Eyring', 'Millington', 'Fitzroy']]

    visualizer.plot_rt60_comparison(
        {k: rt60_values[k] for k in measured_keys},
        title="Measured RT60 Methods",
        ax=ax1, show=False
    )

    visualizer.plot_rt60_comparison(
        {k: rt60_values[k] for k in theoretical_keys},
        title="Theoretical RT60 Models",
        ax=ax2, show=False
    )

    plt.tight_layout()
    plt.savefig('example_4_rt60_comparison.png', dpi=100)
    print("\n结果已保存到 example_4_rt60_comparison.png")
    plt.close()

    modes = rt60_calc.analyze_room_modes(room.dimensions, max_freq=200)
    print(f"\n房间模式分析 (<=200Hz):")
    print(f"  模式数量: {len(modes['frequencies'])}")
    print(f"  平均模式间隔: {np.mean(modes['spacing']):.2f} Hz")
    print(f"  前10个模式频率: {modes['frequencies'][:10]}")

    fig, ax = plt.subplots(figsize=(12, 5))
    visualizer.plot_room_modes(
        modes['frequencies'], modes['spacing'],
        title="Room Modes Analysis (0-200 Hz)",
        ax=ax, show=False
    )
    plt.tight_layout()
    plt.savefig('example_4_room_modes.png', dpi=100)
    print("房间模式分析已保存到 example_4_room_modes.png")
    plt.close()

    return rt60_values, modes


def example_5_comprehensive_report():
    """示例5: 综合分析报告"""
    print("\n" + "=" * 60)
    print("示例 5: 综合分析报告")
    print("=" * 60)

    room = RoomGeometry(
        dimensions=np.array([5.0, 4.0, 3.0]),
        absorption=0.4,
        max_order=3,
        use_pra=False
    )

    simulator = AcousticSimulator(
        room_geometry=room,
        fs=44100,
        use_gpu=False
    )

    source = SoundSource(position=np.array([1.0, 1.0, 1.5]))
    source.generate_impulse(fs=44100)
    simulator.add_source(source)

    receiver_positions = simulator.add_receivers_grid(
        x_range=(0.5, 4.5),
        y_range=(0.5, 3.5),
        z_range=(1.0, 2.0),
        resolution=0.3
    )
    print(f"接收器数量: {len(receiver_positions)}")

    print("正在计算脉冲响应...")
    ir = simulator.compute_impulse_responses(max_order=3, duration=1.5)

    rt60_calc = RT60Calculator(fs=44100)
    rt60_result = rt60_calc.calculate_rt60(
        ir[0, 0, :], method="t30",
        freq_bands=np.array([125, 250, 500, 1000, 2000, 4000])
    )

    print("正在计算声压分布...")
    pressure = simulator.compute_sound_pressure(np.array([1000]))
    pressure_at_rec = np.abs(pressure[0, 0, :])

    clarity = rt60_calc.calculate_clarity(ir[0, 0, :])
    definition = rt60_calc.calculate_definition(ir[0, 0, :])
    center_time = rt60_calc.calculate_center_time(ir[0, 0, :])

    print(f"\n声学参数:")
    print(f"  清晰度 C50: {clarity:.2f} dB")
    print(f"  明晰度 D50: {definition:.2f} %")
    print(f"  中心时间 Ts: {center_time:.4f} s")

    visualizer = SoundFieldVisualizer()

    print("正在生成综合报告...")
    visualizer.create_comprehensive_report(
        ir[0, 0, :],
        simulator.fs,
        rt60_result,
        room.dimensions,
        receiver_positions,
        pressure_at_rec,
        save_path='example_5_comprehensive_report.png'
    )

    print("综合报告已保存到 example_5_comprehensive_report.png")

    return simulator, ir, rt60_result


def example_6_gpu_acceleration():
    """示例6: GPU加速演示"""
    print("\n" + "=" * 60)
    print("示例 6: GPU 加速演示")
    print("=" * 60)

    from acoustic_simulator import GPUAccelerator

    gpu = GPUAccelerator(use_gpu=True, backend="auto")

    print(f"\n设备信息: {gpu.device_info}")
    print(f"GPU 可用: {gpu.is_gpu_available}")
    print(f"后端: {gpu.backend}")

    n_sources = 1000
    n_receivers = 500
    n_dim = 3

    sources = np.random.rand(n_sources, n_dim) * 10.0
    receivers = np.random.rand(n_receivers, n_dim) * 10.0

    print(f"\n测试配置: {n_sources} 声源, {n_receivers} 接收器")

    import time

    start = time.time()
    distances_gpu = gpu.parallel_distance_calculation(sources, receivers)
    gpu_time = time.time() - start
    print(f"距离计算 (GPU/NumPy): {gpu_time:.4f}s")

    start = time.time()
    diff = sources[:, np.newaxis, :] - receivers[np.newaxis, :, :]
    distances_cpu = np.sqrt(np.sum(diff ** 2, axis=-1))
    cpu_time = time.time() - start
    print(f"距离计算 (纯NumPy): {cpu_time:.4f}s")

    if cpu_time > 0:
        print(f"加速比: {cpu_time / gpu_time:.2f}x")

    n_freq = 100
    frequencies = np.linspace(100, 4000, n_freq)

    start = time.time()
    pressure_gpu = gpu.parallel_pressure_calculation(
        distances_gpu, frequencies, absorption=0.1
    )
    gpu_pressure_time = time.time() - start
    print(f"\n声压计算 (GPU/NumPy): {gpu_pressure_time:.4f}s")

    print(f"输出形状: {pressure_gpu.shape}")

    return gpu


def main():
    """运行所有示例"""
    print("=" * 70)
    print("声场模拟工具 - 示例程序")
    print("=" * 70)

    try:
        example_1_basic_simulation()
    except Exception as e:
        print(f"示例1执行出错: {e}")
        import traceback
        traceback.print_exc()

    try:
        example_2_multi_source_simulation()
    except Exception as e:
        print(f"示例2执行出错: {e}")
        import traceback
        traceback.print_exc()

    try:
        example_3_dynamic_source()
    except Exception as e:
        print(f"示例3执行出错: {e}")
        import traceback
        traceback.print_exc()

    try:
        example_4_rt60_comparison()
    except Exception as e:
        print(f"示例4执行出错: {e}")
        import traceback
        traceback.print_exc()

    try:
        example_5_comprehensive_report()
    except Exception as e:
        print(f"示例5执行出错: {e}")
        import traceback
        traceback.print_exc()

    try:
        example_6_gpu_acceleration()
    except Exception as e:
        print(f"示例6执行出错: {e}")
        import traceback
        traceback.print_exc()

    print("\n" + "=" * 70)
    print("所有示例运行完成!")
    print("=" * 70)


if __name__ == "__main__":
    main()
