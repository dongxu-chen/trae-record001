import numpy as np
import matplotlib.pyplot as plt
from matplotlib import cm
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from acoustic_simulator import (
    RoomGeometry,
    SoundSource,
    AcousticSimulator,
    RT60Calculator,
    SoundFieldVisualizer,
    AbsorptionBand,
    STANDARD_OCTAVE_BANDS,
    Auralizer,
    RoomOptimizer,
    MATERIAL_DATABASE,
)

plt.rcParams['font.sans-serif'] = ['SimHei', 'Arial Unicode MS', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False


def example_6_scattering_model():
    """示例6: 散射模型 - 非完全镜面反射"""
    print("\n" + "=" * 70)
    print("示例 6: 散射模型 - 非完全镜面反射")
    print("=" * 70)

    room_dims = np.array([6.0, 5.0, 3.5])
    source_pos = np.array([1.5, 1.5, 1.7])
    receiver_pos = np.array([4.5, 3.5, 1.7])

    scattering_values = [0.0, 0.2, 0.5, 0.8]
    results = []

    for scat in scattering_values:
        room = RoomGeometry(
            dimensions=room_dims,
            absorption=0.3,
            scattering=scat,
            max_order=3,
            adaptive_order=False,
            use_pra=False
        )

        sim = AcousticSimulator(room, fs=16000, use_gpu=False)
        sim.add_source(SoundSource(position=source_pos))
        sim.add_receiver(receiver_pos)

        band_irs = sim.compute_band_impulse_responses(max_order=3, duration=0.8)
        ir = np.sum(band_irs[0, 0, :, :], axis=0)

        rt60_calc = RT60Calculator(fs=16000)
        rt60_result = rt60_calc.calculate_rt60_from_band_irs(
            band_irs[0, 0, :, :],
            room.frequencies,
            method="t30"
        )

        energy = np.sum(ir ** 2)
        peak_time = np.argmax(np.abs(ir)) / 16000

        results.append({
            'scattering': scat,
            'ir': ir,
            'rt60': rt60_result['rt60_bands'],
            'energy': energy,
            'peak_time': peak_time
        })

        print(f"\n散射系数={scat:.1f}:")
        print(f"  总能量: {energy:.6e}")
        print(f"  峰值时间: {peak_time * 1000:.1f} ms")
        print(f"  各频带RT60: {[f'{t:.2f}s' for t in rt60_result['rt60_bands']]}")

    fig, axes = plt.subplots(2, 2, figsize=(16, 10))

    colors = cm.viridis(np.linspace(0, 1, len(scattering_values)))

    ax1 = axes[0, 0]
    for i, (res, color) in enumerate(zip(results, colors)):
        t = np.arange(len(res['ir'])) / 16000
        ax1.plot(t, res['ir'] + i * 0.0002, color=color,
                linewidth=1, label=f's={res["scattering"]:.1f}')
    ax1.set_xlabel('时间 [s]')
    ax1.set_ylabel('幅值 (偏移)')
    ax1.set_title('脉冲响应对比 (不同散射系数)')
    ax1.grid(True, alpha=0.3)
    ax1.legend()
    ax1.set_xlim(0, 0.3)

    ax2 = axes[0, 1]
    energies = [r['energy'] for r in results]
    ax2.plot(scattering_values, energies, 'bo-', linewidth=2, markersize=8)
    ax2.set_xlabel('散射系数')
    ax2.set_ylabel('总能量')
    ax2.set_title('散射系数对总能量的影响')
    ax2.grid(True, alpha=0.3)

    ax3 = axes[1, 0]
    for i, (res, color) in enumerate(zip(results, colors)):
        ax3.plot(STANDARD_OCTAVE_BANDS, res['rt60'], 'o-',
                color=color, linewidth=2, markersize=6,
                label=f's={res["scattering"]:.1f}')
    ax3.set_xscale('log')
    ax3.set_xlabel('频率 [Hz]')
    ax3.set_ylabel('RT60 [s]')
    ax3.set_title('各频带混响时间对比')
    ax3.grid(True, alpha=0.3, which='both')
    ax3.legend()
    for freq in STANDARD_OCTAVE_BANDS:
        ax3.axvline(freq, color='gray', linestyle=':', linewidth=0.5, alpha=0.2)

    ax4 = axes[1, 1]
    peak_times = [r['peak_time'] * 1000 for r in results]
    ax4.plot(scattering_values, peak_times, 'ro-', linewidth=2, markersize=8)
    ax4.set_xlabel('散射系数')
    ax4.set_ylabel('峰值到达时间 [ms]')
    ax4.set_title('散射系数对峰值时间的影响')
    ax4.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig('v3_example_6_scattering.png', dpi=100)
    print("\n散射模型分析图已保存到 v3_example_6_scattering.png")
    plt.close()

    return results


def example_7_auralization():
    """示例7: 可听化 - 脉冲响应与干声卷积"""
    print("\n" + "=" * 70)
    print("示例 7: 可听化 - 脉冲响应与干声卷积")
    print("=" * 70)

    room = RoomGeometry(
        dimensions=np.array([5.0, 4.0, 3.0]),
        absorption=0.4,
        scattering=0.3,
        max_order=3,
        adaptive_order=False,
        use_pra=False
    )

    sim = AcousticSimulator(room, fs=44100, use_gpu=False)
    sim.add_source(SoundSource(position=np.array([1.0, 1.0, 1.5])))
    sim.add_receiver(np.array([4.0, 3.0, 1.5]))

    print("\n正在计算脉冲响应...")
    band_irs = sim.compute_band_impulse_responses(max_order=3, duration=1.0)
    ir = np.sum(band_irs[0, 0, :, :], axis=0)
    print(f"IR长度: {len(ir)} 采样点, {len(ir)/44100:.3f}s")

    auralizer = Auralizer(fs=44100)

    signal_types = ["sine", "speech_like", "pink_noise"]
    results = []

    for sig_type in signal_types:
        print(f"\n正在处理信号类型: {sig_type}")

        result = auralizer.auralize(
            ir,
            dry_signal_type=sig_type,
            dry_duration=2.0,
            dry_frequency=440.0
        )

        result.normalize()

        wav_path = f"v3_example_7_{sig_type}_wet.wav"
        auralizer.save_wav(wav_path, result.wet_signal)

        dry_path = f"v3_example_7_{sig_type}_dry.wav"
        auralizer.save_wav(dry_path, result.dry_signal)

        results.append({
            'type': sig_type,
            'result': result,
            'dry_path': dry_path,
            'wet_path': wav_path
        })

        print(f"  干声时长: {len(result.dry_signal)/44100:.2f}s")
        print(f"  湿声时长: {len(result.wet_signal)/44100:.2f}s")
        print(f"  峰值幅值: {result.get_peak_amplitude():.4f}")
        print(f"  已保存: {wav_path}")

    print("\n正在处理频带可听化...")
    dry_signal = auralizer.generate_dry_signal("pink_noise", duration=2.0)
    band_result = auralizer.auralize_bands(
        band_irs,
        dry_signal,
        room.frequencies
    )
    band_result.normalize()
    band_wav_path = "v3_example_7_band_auralization.wav"
    auralizer.save_wav(band_wav_path, band_result.wet_signal)
    print(f"频带可听化结果已保存: {band_wav_path}")

    fig, axes = plt.subplots(3, 2, figsize=(16, 12))

    for i, res in enumerate(results):
        ax_time = axes[i, 0]
        t_dry = np.arange(len(res['result'].dry_signal)) / 44100
        t_wet = np.arange(len(res['result'].wet_signal)) / 44100

        ax_time.plot(t_dry, res['result'].dry_signal, 'b-', alpha=0.6, label='干声', linewidth=0.8)
        ax_time.plot(t_wet, res['result'].wet_signal, 'r-', alpha=0.6, label='湿声', linewidth=0.8)
        ax_time.set_xlabel('时间 [s]')
        ax_time.set_ylabel('幅值')
        ax_time.set_title(f'信号对比 - {res["type"]}')
        ax_time.grid(True, alpha=0.3)
        ax_time.legend()
        ax_time.set_xlim(0, min(2.5, t_wet[-1]))

        ax_spec = axes[i, 1]
        nfft = 2048
        if len(res['result'].wet_signal) >= nfft:
            wet_spec = np.abs(np.fft.rfft(res['result'].wet_signal[:nfft]))
            freqs = np.fft.rfftfreq(nfft, 1/44100)
            ax_spec.semilogx(freqs, 20 * np.log10(wet_spec / np.max(wet_spec) + 1e-10),
                           'r-', linewidth=0.8, label='湿声')

            dry_spec = np.abs(np.fft.rfft(res['result'].dry_signal[:nfft]))
            ax_spec.semilogx(freqs, 20 * np.log10(dry_spec / np.max(dry_spec) + 1e-10),
                           'b-', linewidth=0.8, label='干声')

            ax_spec.set_xlabel('频率 [Hz]')
            ax_spec.set_ylabel('相对幅值 [dB]')
            ax_spec.set_title(f'频谱对比 - {res["type"]}')
            ax_spec.grid(True, alpha=0.3, which='both')
            ax_spec.legend()
            ax_spec.set_ylim(-80, 5)

    plt.tight_layout()
    plt.savefig('v3_example_7_auralization.png', dpi=100)
    print("\n可听化分析图已保存到 v3_example_7_auralization.png")
    plt.close()

    return results


def example_8_room_optimization():
    """示例8: 房间优化建议 - 吸声材料布置推荐"""
    print("\n" + "=" * 70)
    print("示例 8: 房间优化建议 - 吸声材料布置推荐")
    print("=" * 70)

    room_configs = [
        {
            'name': '小控制室',
            'dims': np.array([4.0, 3.5, 2.8]),
            'absorption': 0.15,
            'room_type': 'studio'
        },
        {
            'name': '大会议室',
            'dims': np.array([12.0, 8.0, 3.5]),
            'absorption': 0.1,
            'room_type': 'office'
        },
        {
            'name': '家庭影院',
            'dims': np.array([6.0, 5.0, 3.0]),
            'absorption': 0.2,
            'room_type': 'home_theater'
        }
    ]

    all_results = []

    for config in room_configs:
        print(f"\n{'─' * 50}")
        print(f"分析房间: {config['name']}")
        print(f"{'─' * 50}")

        room = RoomGeometry(
            dimensions=config['dims'],
            absorption=config['absorption'],
            scattering=0.2,
            use_pra=False
        )

        print(f"房间尺寸: {room.dimensions} m")
        print(f"房间容积: {room.get_volume():.1f} m³")
        print(f"总表面积: {room.get_surface_area():.1f} m²")

        optimizer = RoomOptimizer(room)

        print(f"\n材料数据库可用材料 ({len(MATERIAL_DATABASE)} 种):")
        for i, (name, mat) in enumerate(MATERIAL_DATABASE.items()):
            if i < 5:
                avg_abs = np.mean(mat.absorption_coefficients)
                print(f"  {name}: {mat.description}, 平均吸声={avg_abs:.2f}, ¥{mat.cost_per_sqm:.0f}/m²")

        analysis = optimizer.analyze_room(room_type=config['room_type'])

        optimizer.print_analysis_report(analysis)

        print("\n正在模拟优化效果...")
        sim_result = optimizer.simulate_optimization(analysis.suggestions)

        print(f"\n优化前 vs 优化后 RT60 对比:")
        print(f"{'频率(Hz)':>10} {'优化前(s)':>10} {'优化后(s)':>10} {'改善(s)':>10}")
        print("-" * 45)
        for i, freq in enumerate(room.frequencies):
            print(f"{freq:>10.0f} {sim_result['current_rt60'][i]:>10.3f} "
                  f"{sim_result['optimized_rt60'][i]:>10.3f} "
                  f"{sim_result['improvement'][i]:>10.3f}")

        print(f"\n总处理面积: {sim_result['total_area']:.1f} m²")
        print(f"总预估费用: ¥{sim_result['total_cost']:.0f}")

        all_results.append({
            'name': config['name'],
            'room': room,
            'analysis': analysis,
            'sim_result': sim_result
        })

    fig, axes = plt.subplots(2, 2, figsize=(16, 10))

    colors = cm.tab10(np.linspace(0, 1, len(all_results)))

    ax1 = axes[0, 0]
    for i, res in enumerate(all_results):
        ax1.plot(STANDARD_OCTAVE_BANDS, res['analysis'].rt60_current, 'o-',
                color=colors[i], linewidth=2, markersize=6,
                label=f'{res["name"]} - 当前')
        ax1.plot(STANDARD_OCTAVE_BANDS, res['analysis'].rt60_target, '--',
                color=colors[i], linewidth=1.5,
                label=f'{res["name"]} - 目标')
    ax1.set_xscale('log')
    ax1.set_xlabel('频率 [Hz]')
    ax1.set_ylabel('RT60 [s]')
    ax1.set_title('各房间RT60当前值与目标值对比')
    ax1.grid(True, alpha=0.3, which='both')
    ax1.legend(loc='upper right', fontsize=8)
    for freq in STANDARD_OCTAVE_BANDS:
        ax1.axvline(freq, color='gray', linestyle=':', linewidth=0.5, alpha=0.2)

    ax2 = axes[0, 1]
    for i, res in enumerate(all_results):
        ax2.plot(STANDARD_OCTAVE_BANDS, res['sim_result']['improvement'], 's-',
                color=colors[i], linewidth=2, markersize=6,
                label=res['name'])
    ax2.set_xscale('log')
    ax2.set_xlabel('频率 [Hz]')
    ax2.set_ylabel('RT60改善量 [s]')
    ax2.set_title('各频带RT60预计改善量')
    ax2.grid(True, alpha=0.3, which='both')
    ax2.legend()

    ax3 = axes[1, 0]
    room_names = [r['name'] for r in all_results]
    grades = [r['analysis'].overall_grade for r in all_results]
    grade_scores = {'A': 5, 'B': 4, 'C': 3, 'D': 2, 'F': 1}
    scores = [grade_scores.get(g, 0) for g in grades]
    bars = ax3.bar(room_names, scores, color=colors, alpha=0.7)
    ax3.set_ylabel('声学评分')
    ax3.set_title('房间声学整体评价等级')
    ax3.set_ylim(0, 6)
    ax3.set_yticks([1, 2, 3, 4, 5])
    ax3.set_yticklabels(['F', 'D', 'C', 'B', 'A'])
    for bar, grade in zip(bars, grades):
        height = bar.get_height()
        ax3.text(bar.get_x() + bar.get_width() / 2., height + 0.1,
                f'Grade {grade}', ha='center', va='bottom', fontweight='bold')

    ax4 = axes[1, 1]
    costs = [r['sim_result']['total_cost'] for r in all_results]
    areas = [r['sim_result']['total_area'] for r in all_results]
    x = np.arange(len(room_names))
    width = 0.35
    ax4.bar(x - width/2, costs, width, label='预估费用 (¥)', color='steelblue', alpha=0.7)
    ax4_twin = ax4.twinx()
    ax4_twin.bar(x + width/2, areas, width, label='处理面积 (m²)', color='coral', alpha=0.7)
    ax4.set_xticks(x)
    ax4.set_xticklabels(room_names)
    ax4.set_ylabel('预估费用 [¥]')
    ax4_twin.set_ylabel('处理面积 [m²]')
    ax4.set_title('优化方案费用与面积对比')
    lines1, labels1 = ax4.get_legend_handles_labels()
    lines2, labels2 = ax4_twin.get_legend_handles_labels()
    ax4.legend(lines1 + lines2, labels1 + labels2, loc='upper left')

    plt.tight_layout()
    plt.savefig('v3_example_8_optimization.png', dpi=100)
    print("\n房间优化分析图已保存到 v3_example_8_optimization.png")
    plt.close()

    return all_results


def main():
    """运行所有 v3 示例"""
    print("=" * 70)
    print("声场模拟工具 v3.0 - 散射模型、可听化、房间优化")
    print("=" * 70)

    try:
        example_6_scattering_model()
    except Exception as e:
        print(f"示例6执行出错: {e}")
        import traceback
        traceback.print_exc()

    try:
        example_7_auralization()
    except Exception as e:
        print(f"示例7执行出错: {e}")
        import traceback
        traceback.print_exc()

    try:
        example_8_room_optimization()
    except Exception as e:
        print(f"示例8执行出错: {e}")
        import traceback
        traceback.print_exc()

    print("\n" + "=" * 70)
    print("所有 v3 示例运行完成!")
    print("=" * 70)


if __name__ == "__main__":
    import matplotlib
    matplotlib.use('Agg')
    main()
