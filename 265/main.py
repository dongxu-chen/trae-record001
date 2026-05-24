import numpy as np
import matplotlib.pyplot as plt
from gaussian_plume import GaussianPlumeModel
from terrain import Terrain
from visualization import Visualizer
from stability import STABILITY_DESCRIPTIONS
from adaptive_smoothing import AdaptiveSmoother

def example_advanced_heat_source():
    print("\n" + "=" * 60)
    print("示例5: 高级热源模型 - 温度和出口速度修正抬升")
    print("=" * 60)

    Q = 100.0
    u = 5.0
    stability_class = 'C'
    h_s = 100.0

    print(f"\n基础参数:")
    print(f"  源强 Q = {Q} g/s")
    print(f"  风速 u = {u} m/s")
    print(f"  大气稳定度 = {stability_class} ({STABILITY_DESCRIPTIONS[stability_class]})")
    print(f"  烟囱高度 h_s = {h_s} m")

    test_cases = [
        {'T_s': 350, 'v_s': 10, 'd': 2.5, 'label': '低温低速'},
        {'T_s': 400, 'v_s': 15, 'd': 3.0, 'label': '标准工况'},
        {'T_s': 450, 'v_s': 20, 'd': 3.5, 'label': '高温高速'},
        {'T_s': 500, 'v_s': 25, 'd': 4.0, 'label': '超高温高速'},
    ]

    T_a = 293.0

    print(f"\n环境温度 T_a = {T_a} K")
    print(f"\n{'工况':<12} {'T_s(K)':<8} {'v_s(m/s)':<10} {'d(m)':<6} {'Δβ(K)':<8} "
          f"{'Δh_adv(m)':<10} {'Δh_std(m)':<10} {'修正比例':<8}")
    print("-" * 80)

    results = []
    for case in test_cases:
        model = GaussianPlumeModel(
            Q=Q, u=u, stability_class=stability_class, h_s=h_s,
            use_advanced_plume_rise=True
        )

        comparison = model.compare_plume_rise_models(
            x_range=(10, 5000), v_s=case['v_s'], d=case['d'],
            T_s=case['T_s'], T_a=T_a, num_points=100
        )

        x_mid = 1000
        idx = np.argmin(np.abs(comparison['x'] - x_mid))
        delta_h_adv = comparison['delta_h_advanced'][idx]
        delta_h_std = comparison['delta_h_standard'][idx]
        ratio = delta_h_adv / delta_h_std if delta_h_std > 0 else 1.0
        delta_beta = case['T_s'] - T_a

        print(f"{case['label']:<12} {case['T_s']:<8} {case['v_s']:<10} {case['d']:<6} "
              f"{delta_beta:<8.0f} {delta_h_adv:<10.1f} {delta_h_std:<10.1f} {ratio:<8.2f}")

        results.append((case, comparison, model))

    viz = Visualizer(results[0][2])

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 6))

    colors = plt.cm.rainbow(np.linspace(0, 1, len(test_cases)))
    for i, (case, comparison, model) in enumerate(results):
        ax1.plot(comparison['x'] / 1000, comparison['delta_h_advanced'],
                color=colors[i], linewidth=2,
                label=f"{case['label']}: T_s={case['T_s']}K, v_s={case['v_s']}m/s")
        ax1.plot(comparison['x'] / 1000, comparison['delta_h_standard'],
                color=colors[i], linestyle='--', linewidth=1.5, alpha=0.6)

    ax1.plot([], [], 'k-', linewidth=2, label='高级模型')
    ax1.plot([], [], 'k--', linewidth=1.5, label='标准模型')
    ax1.set_xlabel('下风向距离 (km)')
    ax1.set_ylabel('抬升高度 Δh (m)')
    ax1.set_title('不同热源参数下的抬升高度对比')
    ax1.legend(loc='upper right', fontsize=8)
    ax1.grid(True, alpha=0.3)

    viz.plot_heat_source_params(
        v_s=test_cases[1]['v_s'], d=test_cases[1]['d'],
        T_s=test_cases[1]['T_s'], T_a=T_a, ax=ax2
    )

    plt.tight_layout()
    fig.savefig('advanced_heat_source.png', dpi=150, bbox_inches='tight')
    print("\n  已保存: advanced_heat_source.png")

    fig2 = plt.figure(figsize=(18, 12))
    gs = fig2.add_gridspec(2, 2, hspace=0.3, wspace=0.3)

    temperatures = [350, 400, 450, 500]
    for idx, T_s in enumerate(temperatures):
        ax = fig2.add_subplot(gs[idx // 2, idx % 2])
        model = GaussianPlumeModel(
            Q=Q, u=u, stability_class=stability_class, h_s=h_s,
            use_advanced_plume_rise=True
        )
        viz = Visualizer(model)
        viz.plot_plume_rise_advanced(
            x_range=(10, 5000), v_s=15, d=3, T_s=T_s, T_a=T_a, ax=ax
        )
        ax.set_title(f'T_s = {T_s} K (ΔT = {T_s - T_a:.0f} K)')

    plt.tight_layout()
    fig2.savefig('plume_rise_temperature_sweep.png', dpi=150, bbox_inches='tight')
    print("  已保存: plume_rise_temperature_sweep.png")

    plt.close('all')
    print("\n高级热源模型示例完成!")

def example_streamline_deflection():
    print("\n" + "=" * 60)
    print("示例6: 流线偏转模型 - 地形诱导风向变化")
    print("=" * 60)

    Q = 100.0
    u = 5.0
    stability_class = 'C'
    h_s = 100.0

    terrain = Terrain(x_min=0, x_max=10000, y_min=-2000, y_max=2000, resolution=50)
    terrain.add_hill(center_x=2500, center_y=500, height=200, radius=1000)
    terrain.add_ridge(start_x=5000, start_y=-1000, end_x=5000, end_y=1000, height=150, width=500)
    terrain.add_hill(center_x=7500, center_y=-500, height=180, radius=900)

    print("\n已创建复杂地形:")
    print("  - 山丘1: (2500, 500), 高 200 m, 半径 1000 m")
    print("  - 山脉: x=5000, 从 y=-1000 到 y=1000, 高 150 m")
    print("  - 山丘2: (7500, -500), 高 180 m, 半径 900 m")

    model_with_deflection = GaussianPlumeModel(
        Q=Q, u=u, stability_class=stability_class, h_s=h_s, terrain=terrain,
        use_advanced_plume_rise=True, use_streamline_deflection=True
    )

    model_without_deflection = GaussianPlumeModel(
        Q=Q, u=u, stability_class=stability_class, h_s=h_s, terrain=terrain,
        use_advanced_plume_rise=True, use_streamline_deflection=False
    )

    v_s = 15.0
    d = 3.0
    T_s = 400.0
    T_a = 293.0

    x_range = (0, 10000)
    y_range = (-2000, 2000)

    print("\n正在计算带流线偏转的浓度场...")
    grid_data_with = model_with_deflection.calculate_concentration_grid(
        x_range, y_range, z=0, resolution=100,
        v_s=v_s, d=d, T_s=T_s, T_a=T_a, apply_smoothing=True
    )

    print("正在计算无流线偏转的浓度场...")
    grid_data_without = model_without_deflection.calculate_concentration_grid(
        x_range, y_range, z=0, resolution=100,
        v_s=v_s, d=d, T_s=T_s, T_a=T_a, apply_smoothing=True
    )

    viz_with = Visualizer(model_with_deflection)
    viz_without = Visualizer(model_without_deflection)

    fig = plt.figure(figsize=(18, 16))
    gs = fig.add_gridspec(3, 2, hspace=0.3, wspace=0.3)

    ax1 = fig.add_subplot(gs[0, 0])
    viz_with.plot_contour(grid_data_with, ax=ax1,
                         title='有流线偏转的浓度分布')

    ax2 = fig.add_subplot(gs[0, 1])
    viz_without.plot_contour(grid_data_without, ax=ax2,
                            title='无流线偏转的浓度分布')

    ax3 = fig.add_subplot(gs[1, 0])
    viz_with.plot_streamline_deflection(
        u=u, stability_class=stability_class,
        max_distance=10000, step_size=50, ax=ax3
    )

    ax4 = fig.add_subplot(gs[1, 1])
    viz_with.plot_wind_deflection_field(
        u=u, stability_class=stability_class, ax=ax4
    )

    ax5 = fig.add_subplot(gs[2, 0])
    terrain.plot_terrain_profile(ax=ax5, use_3d=False)

    ax6 = fig.add_subplot(gs[2, 1])
    X = grid_data_with['X'] / 1000
    Y = grid_data_with['Y'] / 1000
    C_diff = grid_data_with['C'] - grid_data_without['C']
    rel_diff = np.where(grid_data_without['C'] > 1e-10,
                        C_diff / grid_data_without['C'] * 100, 0)

    max_rel = np.nanmax(np.abs(rel_diff))
    levels = np.linspace(-max_rel, max_rel, 21)
    diff_plot = ax6.contourf(X, Y, rel_diff, levels=levels,
                            cmap='RdBu_r', extend='both')
    plt.colorbar(diff_plot, ax=ax6, label='浓度相对差 (%)')
    ax6.set_xlabel('下风向距离 (km)')
    ax6.set_ylabel('横风向距离 (km)')
    ax6.set_title('流线偏转引起的浓度变化')
    ax6.grid(True, alpha=0.3)

    print(f"\n流线偏转影响分析:")
    print(f"  最大绝对浓度变化: {np.nanmax(np.abs(C_diff)):.6f} mg/m³")
    print(f"  最大相对浓度变化: {np.nanmax(np.abs(rel_diff)):.2f}%")
    print(f"  平均绝对浓度变化: {np.nanmean(np.abs(C_diff)):.6f} mg/m³")

    C_max_with = np.nanmax(grid_data_with['C'])
    C_max_without = np.nanmax(grid_data_without['C'])
    print(f"  最大浓度(有偏转): {C_max_with:.6f} mg/m³")
    print(f"  最大浓度(无偏转): {C_max_without:.6f} mg/m³")
    print(f"  最大浓度变化: {(C_max_with - C_max_without) / C_max_without * 100:.2f}%")

    plt.tight_layout()
    fig.savefig('streamline_deflection.png', dpi=150, bbox_inches='tight')
    print("\n  已保存: streamline_deflection.png")

    plt.close('all')
    print("\n流线偏转模型示例完成!")

def example_adaptive_smoothing():
    print("\n" + "=" * 60)
    print("示例7: 自适应平滑 - 高梯度区域保留细节")
    print("=" * 60)

    Q = 100.0
    u = 5.0
    stability_class = 'C'
    h_s = 100.0

    terrain = Terrain(x_min=0, x_max=10000, y_min=-2000, y_max=2000, resolution=50)
    terrain.add_hill(center_x=2000, center_y=0, height=250, radius=600)
    terrain.add_ridge(start_x=6000, start_y=-800, end_x=6000, end_y=800, height=200, width=300)

    model = GaussianPlumeModel(
        Q=Q, u=u, stability_class=stability_class, h_s=h_s, terrain=terrain,
        use_advanced_plume_rise=True, use_streamline_deflection=True
    )

    v_s = 15.0
    d = 3.0
    T_s = 400.0
    T_a = 293.0

    x_range = (0, 10000)
    y_range = (-2000, 2000)
    resolution = 100

    print("\n正在计算浓度场...")
    grid_data_original = model.calculate_concentration_grid(
        x_range, y_range, z=0, resolution=resolution,
        v_s=v_s, d=d, T_s=T_s, T_a=T_a, apply_smoothing=False
    )

    smoother = AdaptiveSmoother(
        gradient_threshold=0.05,
        min_sigma=0.3,
        max_sigma=3.0,
        edge_detection_method='combined'
    )

    print("\n正在应用不同的平滑方法...")

    grid_data_adaptive = smoother.process_concentration_grid(
        grid_data_original, use_log=True,
        interpolation_factor=1, smooth_method='adaptive_gaussian'
    )

    grid_data_uniform = smoother.process_concentration_grid(
        grid_data_original, use_log=True,
        interpolation_factor=1, smooth_method='gaussian'
    )

    grid_data_high_res = smoother.process_concentration_grid(
        grid_data_original, use_log=True,
        interpolation_factor=2, smooth_method='adaptive_gaussian'
    )

    metrics = grid_data_adaptive['smoothing_metrics']
    print(f"\n自适应平滑效果评估:")
    print(f"  高梯度像素数: {metrics['high_gradient_pixels']} "
          f"({metrics['high_gradient_ratio'] * 100:.1f}%)")
    print(f"  高梯度区MAE: {metrics['mae_high_gradient']:.3e} mg/m³")
    print(f"  高梯度区相关系数: {metrics['correlation_high_gradient']:.3f}")
    print(f"  总体MAE: {metrics['overall_mae']:.3e} mg/m³")
    print(f"  总体RMSE: {metrics['overall_rmse']:.3e} mg/m³")

    viz = Visualizer(model)

    fig = plt.figure(figsize=(18, 16))
    gs = fig.add_gridspec(3, 2, hspace=0.3, wspace=0.3)

    ax1 = fig.add_subplot(gs[0, 0])
    viz.plot_contour(grid_data_original, ax=ax1,
                     title='原始浓度数据 (无平滑)')

    ax2 = fig.add_subplot(gs[0, 1])
    viz.plot_contour(grid_data_uniform, ax=ax2,
                     title='均匀高斯平滑')

    ax3 = fig.add_subplot(gs[1, 0])
    viz.plot_contour(grid_data_adaptive, ax=ax3,
                     title='自适应高斯平滑')

    ax4 = fig.add_subplot(gs[1, 1])
    smoother.plot_edge_detection(grid_data_original['C'], ax=ax4)
    ax4[0].set_title('边缘强度检测')
    ax4[1].set_title('自适应平滑强度 (σ)')

    ax5 = fig.add_subplot(gs[2, 0])
    smoother.plot_smoothing_comparison(
        grid_data_original['C'], grid_data_adaptive['C'], ax=ax5
    )

    ax6 = fig.add_subplot(gs[2, 1])
    target_C = 0.01

    isopleth_original, _ = model.calculate_isopleth(
        target_C, x_range, y_range, z=0, resolution=resolution,
        v_s=v_s, d=d, T_s=T_s, T_a=T_a,
        smooth_isopleth=False, apply_grid_smoothing=False
    )

    isopleth_smoothed, _ = model.calculate_isopleth(
        target_C, x_range, y_range, z=0, resolution=resolution,
        v_s=v_s, d=d, T_s=T_s, T_a=T_a,
        smooth_isopleth=True, apply_grid_smoothing=True
    )

    viz.plot_contour(grid_data_adaptive, ax=ax6,
                     title=f'等值线对比 (C = {target_C} mg/m³)')

    if isopleth_original:
        x_orig = [p[0] / 1000 for p in isopleth_original]
        y_min_orig = [p[1] / 1000 for p in isopleth_original]
        y_max_orig = [p[2] / 1000 for p in isopleth_original]
        ax6.plot(x_orig, y_min_orig, 'r--', linewidth=1.5, alpha=0.7, label='原始等值线')
        ax6.plot(x_orig, y_max_orig, 'r--', linewidth=1.5, alpha=0.7)

    if isopleth_smoothed:
        x_smooth = [p[0] / 1000 for p in isopleth_smoothed]
        y_min_smooth = [p[1] / 1000 for p in isopleth_smoothed]
        y_max_smooth = [p[2] / 1000 for p in isopleth_smoothed]
        ax6.plot(x_smooth, y_min_smooth, 'g-', linewidth=2, label='平滑后等值线')
        ax6.plot(x_smooth, y_max_smooth, 'g-', linewidth=2)

    ax6.legend()

    plt.tight_layout()
    fig.savefig('adaptive_smoothing.png', dpi=150, bbox_inches='tight')
    print("\n  已保存: adaptive_smoothing.png")

    fig2, (ax_a, ax_b) = plt.subplots(1, 2, figsize=(16, 6))

    x_profile = grid_data_original['x'] / 1000
    mid_y_idx = len(grid_data_original['y']) // 2

    C_original = grid_data_original['C'][:, mid_y_idx]
    C_adaptive = grid_data_adaptive['C'][:, mid_y_idx]
    C_uniform = grid_data_uniform['C'][:, mid_y_idx]

    ax_a.semilogy(x_profile, C_original, 'k-', linewidth=1.5, label='原始数据', alpha=0.7)
    ax_a.semilogy(x_profile, C_adaptive, 'b-', linewidth=2, label='自适应平滑')
    ax_a.semilogy(x_profile, C_uniform, 'r--', linewidth=2, label='均匀平滑', alpha=0.7)
    ax_a.set_xlabel('下风向距离 (km)')
    ax_a.set_ylabel('浓度 (mg/m³)')
    ax_a.set_title('中心线浓度剖面对比')
    ax_a.legend()
    ax_a.grid(True, alpha=0.3, which='both')

    x_slice_idx = np.argmin(np.abs(grid_data_original['x'] - 2000))
    y_profile = grid_data_original['y'] / 1000

    C_original_slice = grid_data_original['C'][x_slice_idx, :]
    C_adaptive_slice = grid_data_adaptive['C'][x_slice_idx, :]
    C_uniform_slice = grid_data_uniform['C'][x_slice_idx, :]

    ax_b.semilogy(y_profile, C_original_slice, 'k-', linewidth=1.5, label='原始数据', alpha=0.7)
    ax_b.semilogy(y_profile, C_adaptive_slice, 'b-', linewidth=2, label='自适应平滑')
    ax_b.semilogy(y_profile, C_uniform_slice, 'r--', linewidth=2, label='均匀平滑', alpha=0.7)
    ax_b.set_xlabel('横风向距离 (km)')
    ax_b.set_ylabel('浓度 (mg/m³)')
    ax_b.set_title(f'x = {grid_data_original["x"][x_slice_idx]:.0f} m 处横风向剖面对比')
    ax_b.legend()
    ax_b.grid(True, alpha=0.3, which='both')

    plt.tight_layout()
    fig2.savefig('smoothing_profile_comparison.png', dpi=150, bbox_inches='tight')
    print("  已保存: smoothing_profile_comparison.png")

    fig3 = plt.figure(figsize=(12, 6))
    ax = fig3.add_subplot(111)
    viz.plot_contour(grid_data_high_res, ax=ax,
                    title=f'高分辨率自适应平滑 (分辨率 ×2, {grid_data_high_res["X"].shape[0]}×{grid_data_high_res["X"].shape[1]})')
    fig3.savefig('high_res_smoothing.png', dpi=150, bbox_inches='tight')
    print("  已保存: high_res_smoothing.png")

    plt.close('all')
    print("\n自适应平滑示例完成!")

def example_all_advanced_features():
    print("\n" + "=" * 60)
    print("示例8: 所有高级功能综合展示")
    print("=" * 60)

    Q = 100.0
    u = 5.0
    stability_class = 'C'
    h_s = 100.0

    terrain = Terrain(x_min=0, x_max=10000, y_min=-2000, y_max=2000, resolution=50)
    terrain.add_hill(center_x=2500, center_y=300, height=180, radius=700)
    terrain.add_ridge(start_x=5500, start_y=-1200, end_x=5500, end_y=1200, height=160, width=400)
    terrain.add_valley(center_x=8000, center_y=0, depth=80, radius=600)

    model = GaussianPlumeModel(
        Q=Q, u=u, stability_class=stability_class, h_s=h_s, terrain=terrain,
        use_advanced_plume_rise=True, use_streamline_deflection=True
    )

    v_s = 18.0
    d = 3.5
    T_s = 420.0
    T_a = 293.0

    print(f"\n模拟参数:")
    print(f"  源强 Q = {Q} g/s")
    print(f"  风速 u = {u} m/s")
    print(f"  大气稳定度 = {stability_class} ({STABILITY_DESCRIPTIONS[stability_class]})")
    print(f"  烟囱高度 h_s = {h_s} m")
    print(f"  烟气出口速度 v_s = {v_s} m/s")
    print(f"  烟囱直径 d = {d} m")
    print(f"  烟气温度 T_s = {T_s} K")
    print(f"  环境温度 T_a = {T_a} K")

    viz = Visualizer(model)

    print("\n正在生成综合分析图表...")
    fig = viz.plot_advanced_features(
        x_range=(100, 10000), y_range=(-2000, 2000),
        v_s=v_s, d=d, T_s=T_s, T_a=T_a
    )
    fig.savefig('all_advanced_features.png', dpi=150, bbox_inches='tight')
    print("  已保存: all_advanced_features.png")

    x_range = (100, 10000)
    max_result = model.calculate_max_concentration(
        x_range, v_s=v_s, d=d, T_s=T_s, T_a=T_a
    )

    target_C = 0.01
    area, grid_data = model.calculate_footprint_area(
        target_C, x_range, (-2000, 2000),
        v_s=v_s, d=d, T_s=T_s, T_a=T_a
    )

    heat_params = model.get_heat_source_params(v_s=v_s, d=d, T_s=T_s, T_a=T_a)

    print(f"\n综合分析结果:")
    print(f"  最大地面浓度: {max_result['max_C']:.6f} mg/m³")
    print(f"  最大浓度位置: x = {max_result['max_x']:.0f} m")
    print(f"  有效源高 (最大浓度处): {max_result['H_e_at_max']:.2f} m")
    print(f"  浓度 ≥ {target_C} mg/m³ 面积: {area/1e6:.2f} km²")
    print(f"  热释放率 Qh: {heat_params['Qh']/1000:.1f} kW")
    print(f"  浮力通量 F_b: {heat_params['F_b']:.2f} m⁴/s³")
    print(f"  特征抬升长度 l_m: {heat_params['l_m']:.0f} m")

    if 'extra_at_max' in max_result:
        extra = max_result['extra_at_max']
        print(f"  风场偏转角: {np.degrees(extra.get('wind_deflection', 0)):.2f}°")
        print(f"  有效风速: {extra.get('effective_speed', u):.2f} m/s")
        print(f"  地形修正系数: {extra.get('terrain_factor', 1.0):.3f}")

    plt.close('all')
    print("\n所有高级功能综合展示完成!")

def example_basic_simulation():
    print("=" * 60)
    print("示例1: 基础高斯烟羽扩散模拟")
    print("=" * 60)

    Q = 100.0
    u = 5.0
    stability_class = 'C'
    h_s = 100.0

    print(f"\n参数设置:")
    print(f"  源强 Q = {Q} g/s")
    print(f"  风速 u = {u} m/s")
    print(f"  大气稳定度 = {stability_class} ({STABILITY_DESCRIPTIONS[stability_class]})")
    print(f"  烟囱高度 h_s = {h_s} m")

    model = GaussianPlumeModel(Q=Q, u=u, stability_class=stability_class, h_s=h_s)

    Qh = 5000.0
    v_s = 15.0
    d = 3.0
    T_s = 400.0
    T_a = 293.0

    print(f"\n烟羽抬升参数:")
    print(f"  热释放率 Qh = {Qh} kJ/s")
    print(f"  烟气出口速度 v_s = {v_s} m/s")
    print(f"  烟囱直径 d = {d} m")
    print(f"  烟气温度 T_s = {T_s} K")
    print(f"  环境温度 T_a = {T_a} K")

    x_test = 1000.0
    y_test = 0.0
    z_test = 0.0

    result = model.calculate_concentration(
        x_test, y_test, z_test, v_s=v_s, d=d, T_s=T_s, T_a=T_a
    )
    C, H_e, delta_h, sigma_y, sigma_z = result[:5]

    print(f"\n在下风向 x={x_test} m, y={y_test} m, z={z_test} m 处:")
    print(f"  浓度 C = {C:.6f} mg/m³")
    print(f"  有效源高 H_e = {H_e:.2f} m")
    print(f"  抬升高度 Δh = {delta_h:.2f} m")
    print(f"  横向扩散参数 σ_y = {sigma_y:.2f} m")
    print(f"  垂直扩散参数 σ_z = {sigma_z:.2f} m")

    max_result = model.calculate_max_concentration(
        x_range=(100, 10000), v_s=v_s, d=d, T_s=T_s, T_a=T_a
    )

    print(f"\n最大浓度分析:")
    print(f"  最大浓度 C_max = {max_result['max_C']:.6f} mg/m³")
    print(f"  最大浓度位置 x_max = {max_result['max_x']:.0f} m")
    print(f"  最大浓度处有效源高 H_e = {max_result['H_e_at_max']:.2f} m")

    x_range = (0, 10000)
    y_range = (-2000, 2000)
    grid_data = model.calculate_concentration_grid(
        x_range, y_range, z=0, resolution=100,
        v_s=v_s, d=d, T_s=T_s, T_a=T_a
    )

    target_C = 0.01
    area, _ = model.calculate_footprint_area(
        target_C, x_range, y_range, z=0, resolution=100,
        v_s=v_s, d=d, T_s=T_s, T_a=T_a
    )

    print(f"\n影响范围分析:")
    print(f"  浓度 ≥ {target_C} mg/m³ 的区域面积 = {area/1e6:.2f} km²")

    viz = Visualizer(model)

    print("\n正在生成可视化图表...")
    fig1, ax1 = plt.subplots(figsize=(12, 8))
    viz.plot_contour(grid_data, ax=ax1)
    fig1.savefig('concentration_contour.png', dpi=150, bbox_inches='tight')
    print("  已保存: concentration_contour.png")

    fig2, ax2 = plt.subplots(figsize=(12, 6))
    viz.plot_centerline_profile(x_range=(100, 10000), ax=ax2,
                                v_s=v_s, d=d, T_s=T_s, T_a=T_a)
    fig2.savefig('centerline_profile.png', dpi=150, bbox_inches='tight')
    print("  已保存: centerline_profile.png")

    fig3 = viz.plot_all(grid_data, x_range=(100, 10000),
                        v_s=v_s, d=d, T_s=T_s, T_a=T_a)
    fig3.savefig('comprehensive_analysis.png', dpi=150, bbox_inches='tight')
    print("  已保存: comprehensive_analysis.png")

    target_concentration = 0.05
    fig4, ax4 = plt.subplots(figsize=(12, 8))
    ax4, isopleth_pts, _ = viz.plot_isopleth(
        target_concentration, x_range=x_range, y_range=y_range,
        v_s=v_s, d=d, T_s=T_s, T_a=T_a
    )
    fig4.savefig('isopleth_contour.png', dpi=150, bbox_inches='tight')
    print(f"  已保存: isopleth_contour.png (等值线: {target_concentration} mg/m³)")

    plt.close('all')
    print("\n基础模拟完成!")
    return model, grid_data

def example_terrain_correction():
    print("\n" + "=" * 60)
    print("示例2: 带地形修正的扩散模拟")
    print("=" * 60)

    Q = 100.0
    u = 5.0
    stability_class = 'C'
    h_s = 100.0

    terrain = Terrain(x_min=0, x_max=10000, y_min=-2000, y_max=2000, resolution=50)

    terrain.add_hill(center_x=3000, center_y=0, height=150, radius=800)
    terrain.add_ridge(start_x=5000, start_y=-1500, end_x=7000, end_y=1500, height=100, width=400)
    terrain.add_valley(center_x=1500, center_y=-800, depth=50, radius=500)

    print("\n已创建地形:")
    print("  - 山丘: 位于 (3000, 0), 高 150 m, 半径 800 m")
    print("  - 山脉: 从 (5000, -1500) 到 (7000, 1500), 高 100 m, 宽 400 m")
    print("  - 山谷: 位于 (1500, -800), 深 50 m, 半径 500 m")

    model_with_terrain = GaussianPlumeModel(
        Q=Q, u=u, stability_class=stability_class, h_s=h_s, terrain=terrain,
        use_streamline_deflection=True
    )

    model_without_terrain = GaussianPlumeModel(
        Q=Q, u=u, stability_class=stability_class, h_s=h_s, terrain=None
    )

    v_s = 15.0
    d = 3.0
    T_s = 400.0
    T_a = 293.0

    x_range = (0, 10000)
    y_range = (-2000, 2000)

    print("\n正在计算带地形修正的浓度场...")
    grid_data_with = model_with_terrain.calculate_concentration_grid(
        x_range, y_range, z=0, resolution=100,
        v_s=v_s, d=d, T_s=T_s, T_a=T_a
    )

    print("正在计算无地形修正的浓度场...")
    grid_data_without = model_without_terrain.calculate_concentration_grid(
        x_range, y_range, z=0, resolution=100,
        v_s=v_s, d=d, T_s=T_s, T_a=T_a
    )

    C_diff = grid_data_with['C'] - grid_data_without['C']
    rel_diff = np.where(grid_data_without['C'] > 1e-10,
                        np.abs(C_diff) / grid_data_without['C'] * 100, 0)

    print(f"\n地形影响分析:")
    print(f"  最大绝对浓度差: {np.nanmax(np.abs(C_diff)):.6f} mg/m³")
    print(f"  最大相对浓度差: {np.nanmax(rel_diff):.2f}%")
    print(f"  平均相对浓度差: {np.nanmean(rel_diff):.2f}%")

    viz_with = Visualizer(model_with_terrain)
    viz_without = Visualizer(model_without_terrain)

    fig = plt.figure(figsize=(18, 12))

    ax1 = plt.subplot(2, 2, 1)
    viz_with.plot_contour(grid_data_with, ax=ax1, title='有地形修正的浓度分布')

    ax2 = plt.subplot(2, 2, 2)
    viz_without.plot_contour(grid_data_without, ax=ax2, title='无地形修正的浓度分布')

    ax3 = plt.subplot(2, 2, 3)
    terrain.plot_terrain_profile(ax=ax3, use_3d=False)

    ax4 = plt.subplot(2, 2, 4)
    X = grid_data_with['X'] / 1000
    Y = grid_data_with['Y'] / 1000
    diff_plot = ax4.contourf(X, Y, rel_diff, levels=20, cmap='RdYlBu_r')
    plt.colorbar(diff_plot, ax=ax4, label='相对浓度差 (%)')
    ax4.set_xlabel('下风向距离 (km)')
    ax4.set_ylabel('横风向距离 (km)')
    ax4.set_title('地形引起的相对浓度差')
    ax4.grid(True, alpha=0.3)

    plt.tight_layout()
    fig.savefig('terrain_comparison.png', dpi=150, bbox_inches='tight')
    print("\n  已保存: terrain_comparison.png")

    x_test = 3000
    y_test = 0
    h_test = terrain.get_height(x_test, y_test)
    result_with = model_with_terrain.calculate_concentration(
        x_test, y_test, 0, v_s=v_s, d=d, T_s=T_s, T_a=T_a
    )
    C_with, H_e_with = result_with[0], result_with[1]
    result_without = model_without_terrain.calculate_concentration(
        x_test, y_test, 0, v_s=v_s, d=d, T_s=T_s, T_a=T_a
    )
    C_without, H_e_without = result_without[0], result_without[1]

    print(f"\n山丘顶部 (x={x_test} m, y={y_test} m, h={h_test:.1f} m):")
    print(f"  有地形: C = {C_with:.6f} mg/m³, H_e = {H_e_with:.2f} m")
    print(f"  无地形: C = {C_without:.6f} mg/m³, H_e = {H_e_without:.2f} m")

    plt.close('all')
    print("\n地形修正模拟完成!")
    return model_with_terrain, grid_data_with

def example_geographic_plot():
    print("\n" + "=" * 60)
    print("示例3: 地理坐标可视化")
    print("=" * 60)

    Q = 100.0
    u = 5.0
    stability_class = 'C'
    h_s = 100.0

    model = GaussianPlumeModel(Q=Q, u=u, stability_class=stability_class, h_s=h_s)

    v_s = 15.0
    d = 3.0
    T_s = 400.0
    T_a = 293.0

    x_range = (0, 10000)
    y_range = (-2000, 2000)
    grid_data = model.calculate_concentration_grid(
        x_range, y_range, z=0, resolution=50,
        v_s=v_s, d=d, T_s=T_s, T_a=T_a
    )

    viz = Visualizer(model)

    center_lon = 116.4
    center_lat = 39.9

    print(f"\n地理坐标中心: ({center_lon}°E, {center_lat}°N) - 北京附近")

    fig, ax = plt.subplots(figsize=(12, 10))
    result = viz.plot_geographic(grid_data, center_lon=center_lon, center_lat=center_lat, ax=ax)

    if result is not None:
        fig.savefig('geographic_distribution.png', dpi=150, bbox_inches='tight')
        print("  已保存: geographic_distribution.png")
    else:
        print("  跳过地理坐标图 (缺少依赖库)")

    plt.close('all')
    print("\n地理坐标可视化完成!")

def example_stability_analysis():
    print("\n" + "=" * 60)
    print("示例4: 大气稳定度影响分析")
    print("=" * 60)

    from stability import STABILITY_CLASSES, STABILITY_DESCRIPTIONS

    Q = 100.0
    u = 5.0
    h_s = 100.0

    v_s = 15.0
    d = 3.0
    T_s = 400.0
    T_a = 293.0

    results = {}
    for sc in STABILITY_CLASSES:
        model = GaussianPlumeModel(Q=Q, u=u, stability_class=sc, h_s=h_s,
                                  use_advanced_plume_rise=True)
        max_result = model.calculate_max_concentration(
            x_range=(100, 10000), v_s=v_s, d=d, T_s=T_s, T_a=T_a
        )
        results[sc] = max_result
        print(f"  {sc} ({STABILITY_DESCRIPTIONS[sc]:6s}): "
              f"C_max = {max_result['max_C']:.6f} mg/m³ @ x = {max_result['max_x']:.0f} m")

    model = GaussianPlumeModel(Q=Q, u=u, stability_class='D', h_s=h_s)
    viz = Visualizer(model)

    fig, ax = plt.subplots(figsize=(12, 6))
    viz.plot_stability_comparison(
        x_range=(100, 10000), v_s=v_s, d=d, T_s=T_s, T_a=T_a, ax=ax
    )
    fig.savefig('stability_comparison.png', dpi=150, bbox_inches='tight')
    print("\n  已保存: stability_comparison.png")

    fig, ax = plt.subplots(figsize=(10, 6))
    x_pos = np.arange(len(STABILITY_CLASSES))
    max_C_values = [results[sc]['max_C'] for sc in STABILITY_CLASSES]
    max_x_values = [results[sc]['max_x'] for sc in STABILITY_CLASSES]

    bars = ax.bar(x_pos, max_C_values, color='steelblue', alpha=0.7)
    ax.set_xlabel('大气稳定度等级')
    ax.set_ylabel('最大地面浓度 (mg/m³)')
    ax.set_title('不同稳定度下的最大地面浓度对比')
    ax.set_xticks(x_pos)
    ax.set_xticklabels([f'{sc}\n({STABILITY_DESCRIPTIONS[sc]})' for sc in STABILITY_CLASSES])
    ax.grid(True, alpha=0.3, axis='y')

    for i, bar in enumerate(bars):
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width() / 2, height,
                f'{height:.4f}\n@ {max_x_values[i]:.0f}m',
                ha='center', va='bottom', fontsize=8)

    plt.tight_layout()
    fig.savefig('stability_max_C.png', dpi=150, bbox_inches='tight')
    print("  已保存: stability_max_C.png")

    plt.close('all')
    print("\n稳定度影响分析完成!")

def interactive_calculation():
    print("\n" + "=" * 60)
    print("交互式浓度计算")
    print("=" * 60)

    try:
        print("\n请输入参数 (直接回车使用默认值):")

        Q = float(input("源强 Q (g/s) [默认 100]: ") or 100)
        u = float(input("风速 u (m/s) [默认 5]: ") or 5)
        stability_class = input("大气稳定度 (A/B/C/D/E/F) [默认 C]: ") or 'C'
        h_s = float(input("烟囱高度 h_s (m) [默认 100]: ") or 100)

        v_s = float(input("烟气出口速度 v_s (m/s) [默认 15]: ") or 15)
        d = float(input("烟囱直径 d (m) [默认 3]: ") or 3)
        T_s = float(input("烟气温度 T_s (K) [默认 400]: ") or 400)
        T_a = float(input("环境温度 T_a (K) [默认 293]: ") or 293)

        use_advanced = input("使用高级热源模型? (y/n) [默认 y]: ").lower() != 'n'
        use_deflect = input("使用流线偏转地形修正? (y/n) [默认 y]: ").lower() != 'n'
        use_smooth = input("使用自适应平滑? (y/n) [默认 y]: ").lower() != 'n'

        model = GaussianPlumeModel(
            Q=Q, u=u, stability_class=stability_class, h_s=h_s,
            use_advanced_plume_rise=use_advanced,
            use_streamline_deflection=use_deflect
        )

        while True:
            print("\n" + "-" * 40)
            x = float(input("下风向距离 x (m), 输入 -1 退出: "))
            if x == -1:
                break
            y = float(input("横风向距离 y (m) [默认 0]: ") or 0)
            z = float(input("计算高度 z (m) [默认 0]: ") or 0)

            result = model.calculate_concentration(
                x, y, z, v_s=v_s, d=d, T_s=T_s, T_a=T_a
            )
            C, H_e, delta_h, sigma_y, sigma_z, extra = result

            print(f"\n计算结果:")
            print(f"  位置: x={x:.0f} m, y={y:.0f} m, z={z:.0f} m")
            print(f"  浓度 C = {C:.6f} mg/m³")
            print(f"  有效源高 H_e = {H_e:.2f} m (抬升 Δh = {delta_h:.2f} m)")
            print(f"  σ_y = {sigma_y:.2f} m, σ_z = {sigma_z:.2f} m")

            if extra is not None:
                print(f"  地形修正系数 = {extra.get('terrain_factor', 1.0):.3f}")
                print(f"  风场偏转角 = {np.degrees(extra.get('wind_deflection', 0)):.2f}°")
                print(f"  有效风速 = {extra.get('effective_speed', u):.2f} m/s")

    except ValueError:
        print("输入错误，请输入有效的数值。")
    except KeyboardInterrupt:
        print("\n已退出交互式计算。")

def main():
    import argparse
    parser = argparse.ArgumentParser(description='大气污染物扩散模拟 - 高斯烟羽模型 (增强版)')
    parser.add_argument('--example', type=int, choices=[1, 2, 3, 4, 5, 6, 7, 8],
                        help='运行指定的示例 (1-8)')
    parser.add_argument('--all', action='store_true',
                        help='运行所有示例')
    parser.add_argument('--advanced', action='store_true',
                        help='只运行高级功能示例 (5-8)')
    parser.add_argument('--basic', action='store_true',
                        help='只运行基础示例 (1-4)')
    parser.add_argument('--interactive', action='store_true',
                        help='进入交互式计算模式')

    args = parser.parse_args()

    if args.interactive:
        interactive_calculation()
    elif args.all:
        example_basic_simulation()
        example_terrain_correction()
        example_geographic_plot()
        example_stability_analysis()
        example_advanced_heat_source()
        example_streamline_deflection()
        example_adaptive_smoothing()
        example_all_advanced_features()
        print("\n" + "=" * 60)
        print("所有示例运行完成! 请查看生成的图片文件。")
        print("=" * 60)
    elif args.advanced:
        example_advanced_heat_source()
        example_streamline_deflection()
        example_adaptive_smoothing()
        example_all_advanced_features()
        print("\n" + "=" * 60)
        print("高级功能示例运行完成!")
        print("=" * 60)
    elif args.basic:
        example_basic_simulation()
        example_terrain_correction()
        example_geographic_plot()
        example_stability_analysis()
        print("\n" + "=" * 60)
        print("基础示例运行完成!")
        print("=" * 60)
    elif args.example:
        examples = {
            1: example_basic_simulation,
            2: example_terrain_correction,
            3: example_geographic_plot,
            4: example_stability_analysis,
            5: example_advanced_heat_source,
            6: example_streamline_deflection,
            7: example_adaptive_smoothing,
            8: example_all_advanced_features,
        }
        examples[args.example]()
    else:
        parser.print_help()
        print("\n默认运行所有示例...")
        example_basic_simulation()
        example_terrain_correction()
        example_geographic_plot()
        example_stability_analysis()
        example_advanced_heat_source()
        example_streamline_deflection()
        example_adaptive_smoothing()
        example_all_advanced_features()
        print("\n" + "=" * 60)
        print("所有示例运行完成! 请查看生成的图片文件。")
        print("=" * 60)

if __name__ == '__main__':
    main()
