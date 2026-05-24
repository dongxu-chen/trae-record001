import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

from gaussian_plume import GaussianPlumeModel
from terrain import Terrain
from plume_rise import HeatSourceModel, calculate_effective_stack_height_advanced
from adaptive_smoothing import AdaptiveSmoother
from visualization import Visualizer

def test_heat_source_model():
    print("=" * 60)
    print("测试1: 热源模型验证")
    print("=" * 60)

    v_s = 15.0
    d = 3.0
    T_s = 400.0
    T_a = 293.0

    heat_source = HeatSourceModel(v_s, d, T_s, T_a)

    print(f"\n输入参数:")
    print(f"  出口速度 v_s = {v_s} m/s")
    print(f"  烟囱直径 d = {d} m")
    print(f"  烟气温度 T_s = {T_s} K")
    print(f"  环境温度 T_a = {T_a} K")

    print(f"\n计算结果:")
    print(f"  烟气密度 ρ_s = {heat_source.rho_s:.4f} kg/m³")
    print(f"  空气密度 ρ_a = {heat_source.rho_a:.4f} kg/m³")
    print(f"  温度差 β = {heat_source.beta:.1f} K")
    print(f"  修正出口速度 w* = {heat_source.w_star:.2f} m/s")
    print(f"  浮力通量 F_b = {heat_source.F_b:.4f} m⁴/s³")
    print(f"  热释放率 Qh = {heat_source.Qh/1000:.2f} kW")
    print(f"  动量通量 M = {heat_source.M:.2f} kg·m/s²")
    print(f"  弗劳德数 F_r = {heat_source.F_r:.6f}")
    print(f"  理查德森数 R_i = {heat_source.R_i:.6f}")
    print(f"  特征长度 l_m = {heat_source.l_m:.1f} m")

    assert heat_source.beta == T_s - T_a, "温度差计算错误"
    assert heat_source.rho_s > 0, "烟气密度必须为正"
    assert heat_source.F_b > 0, "浮力通量必须为正"
    assert heat_source.Qh > 0, "热释放率必须为正"

    x_test = np.array([100, 500, 1000, 2000, 5000])
    delta_h_base = np.ones_like(x_test) * 100.0

    delta_h_temp_corrected = heat_source.correct_temperature_effect(delta_h_base, x_test)
    delta_h_vel_corrected = heat_source.correct_velocity_effect(delta_h_base, x_test, u=5.0)
    delta_h_full = heat_source.calculate_heat_source_correction(
        delta_h_base, x_test, u=5.0, stability_class='C'
    )

    print(f"\n修正效果验证 (基准Δh=100m):")
    print(f"  温度修正后: {delta_h_temp_corrected[2]:.2f} m (系数: {delta_h_temp_corrected[2]/100:.3f})")
    print(f"  速度修正后: {delta_h_vel_corrected[2]:.2f} m (系数: {delta_h_vel_corrected[2]/100:.3f})")
    print(f"  综合修正后: {delta_h_full[2]:.2f} m (系数: {delta_h_full[2]/100:.3f})")

    regime, x_m, x_star = heat_source.get_plume_regime(x_test, u=5.0, stability_class='C')
    print(f"\n抬升区域判断:")
    print(f"  动量区长度 x_m = {x_m:.1f} m")
    print(f"  近浮力区长度 x_star = {x_star:.1f} m")
    for i, x in enumerate(x_test):
        print(f"    x={x:5d} m -> {regime[i]}")

    print("\n✅ 热源模型测试通过!")
    return True

def test_advanced_plume_rise():
    print("\n" + "=" * 60)
    print("测试2: 高级烟羽抬升计算验证")
    print("=" * 60)

    x = np.linspace(10, 5000, 100)
    h_s = 100.0
    v_s = 15.0
    d = 3.0
    T_s = 400.0
    T_a = 293.0
    u = 5.0
    stability_class = 'C'

    H_e_adv, delta_h_adv, heat_source = calculate_effective_stack_height_advanced(
        x, h_s, v_s, d, T_s, T_a, u, stability_class
    )

    from plume_rise import calculate_effective_stack_height
    Qh = heat_source.Qh
    H_e_std, delta_h_std = calculate_effective_stack_height(
        x, h_s, Qh, v_s, d, T_s, T_a, u, stability_class
    )

    idx_1km = np.argmin(np.abs(x - 1000))
    idx_3km = np.argmin(np.abs(x - 3000))

    print(f"\n抬升高度对比:")
    print(f"  位置      标准模型Δh    高级模型Δh    差异     比例")
    print(f"  " + "-" * 65)
    for idx, name in [(idx_1km, "1 km"), (idx_3km, "3 km")]:
        diff = delta_h_adv[idx] - delta_h_std[idx]
        ratio = delta_h_adv[idx] / delta_h_std[idx] if delta_h_std[idx] > 0 else 0
        print(f"  {name:6s}  {delta_h_std[idx]:10.2f} m  {delta_h_adv[idx]:10.2f} m  {diff:+8.2f} m  {ratio:6.2f}x")

    print(f"\n最大抬升高度:")
    print(f"  标准模型: {np.max(delta_h_std):.2f} m @ x={x[np.argmax(delta_h_std)]:.0f} m")
    print(f"  高级模型: {np.max(delta_h_adv):.2f} m @ x={x[np.argmax(delta_h_adv)]:.0f} m")

    assert np.all(delta_h_adv >= 0), "抬升高度不能为负"
    assert np.all(H_e_adv >= h_s), "有效源高不能低于烟囱高度"
    assert not np.any(np.isnan(delta_h_adv)), "抬升高度不能包含NaN"

    print("\n✅ 高级烟羽抬升测试通过!")
    return True

def test_streamline_deflection():
    print("\n" + "=" * 60)
    print("测试3: 流线偏转模型验证")
    print("=" * 60)

    terrain = Terrain(x_min=0, x_max=5000, y_min=-1000, y_max=1000, resolution=100)
    terrain.add_hill(center_x=2000, center_y=0, height=150, radius=500)

    print("\n地形信息:")
    print(f"  山丘中心: (2000, 0), 高 150 m, 半径 500 m")
    print(f"  分辨率: {terrain.resolution} m")
    print(f"  网格大小: {terrain.height_map.shape}")

    stream_deflect = terrain.get_streamline_deflection(base_wind_direction=0.0)

    test_points = [(1000, 0), (2000, 0), (2000, 300), (3000, 0)]
    print(f"\n各点风场偏转角 (风速 u=5 m/s, 稳定度 C):")
    print(f"  位置          地形高度    风偏角       有效风速    斜率")
    print(f"  " + "-" * 70)

    for x, y in test_points:
        h_t = terrain.get_height(x, y)
        slope = stream_deflect.get_slope(x, y)
        wind_dir, eff_speed, deflection = stream_deflect.calculate_wind_deflection(
            x, y, u=5.0, stability_class='C'
        )
        print(f"  ({x:4d}, {y:4d})  {h_t:8.1f} m   {np.degrees(deflection):+8.2f}°   {eff_speed:8.2f} m/s  {slope:.4f}")

    print(f"\n流线追踪 (从 (0, 0) 出发):")
    streamline = stream_deflect.trace_streamline(
        0.0, 0.0, u=5.0, stability_class='C', max_distance=5000, step_size=100
    )
    print(f"  追踪点数: {len(streamline['x'])}")
    print(f"  最大偏转: {np.degrees(np.max(np.abs(streamline['deflection']))):.2f}°")
    print(f"  终点位置: ({streamline['x'][-1]:.1f}, {streamline['y'][-1]:.1f})")
    print(f"  实际距离: {streamline['distance'][-1]:.1f} m")

    deflect_result = stream_deflect.get_deflected_coordinates(
        np.array([1000, 2000, 3000]),
        np.array([0, 0, 0]),
        u=5.0, stability_class='C'
    )
    print(f"\n坐标偏转结果:")
    for i in range(3):
        print(f"  原始: ({[1000, 2000, 3000][i]:4d}, 0) -> "
              f"偏转: ({deflect_result['x_deflected'][i]:7.1f}, {deflect_result['y_deflected'][i]:+7.1f})")

    model = GaussianPlumeModel(
        Q=100.0, u=5.0, stability_class='C', h_s=100.0,
        terrain=terrain, use_streamline_deflection=True,
        use_advanced_plume_rise=True
    )

    C_with_deflect, _, _, _, _, extra = model.calculate_concentration(
        2000, 0, 0, v_s=15.0, d=3.0, T_s=400.0, T_a=293.0
    )

    model_no_deflect = GaussianPlumeModel(
        Q=100.0, u=5.0, stability_class='C', h_s=100.0,
        terrain=terrain, use_streamline_deflection=False,
        use_advanced_plume_rise=True
    )

    C_no_deflect, _, _, _, _, _ = model_no_deflect.calculate_concentration(
        2000, 0, 0, v_s=15.0, d=3.0, T_s=400.0, T_a=293.0
    )

    print(f"\n浓度对比 (x=2000m, y=0):")
    print(f"  有线偏转: {C_with_deflect:.6f} mg/m³")
    print(f"  无线偏转: {C_no_deflect:.6f} mg/m³")
    print(f"  相对差异: {(C_with_deflect - C_no_deflect)/C_no_deflect*100:+.2f}%")

    if extra is not None:
        print(f"  风场偏转角: {np.degrees(extra.get('wind_deflection', 0)):.2f}°")
        print(f"  地形修正系数: {extra.get('terrain_factor', 1.0):.4f}")

    print("\n✅ 流线偏转模型测试通过!")
    return True

def test_adaptive_smoothing():
    print("\n" + "=" * 60)
    print("测试4: 自适应平滑验证")
    print("=" * 60)

    x = np.linspace(0, 10000, 50)
    y = np.linspace(-2000, 2000, 50)
    X, Y = np.meshgrid(x, y, indexing='ij')

    C = np.zeros_like(X)
    C[25, 25] = 100.0
    for i in range(50):
        for j in range(50):
            dist = np.sqrt((x[i] - 5000) ** 2 + (y[j]) ** 2)
            C[i, j] = 10.0 * np.exp(-dist / 1000) * (1 + 0.5 * np.sin(x[i] / 500) * np.sin(y[j] / 200))

    np.random.seed(42)
    C += 0.05 * np.random.randn(*C.shape)
    C = np.maximum(C, 0)

    grid_data = {
        'X': X, 'Y': Y, 'C': C, 'x': x, 'y': y,
        'smoothed': False
    }

    smoother = AdaptiveSmoother(
        gradient_threshold=0.05, min_sigma=0.3, max_sigma=1.5,
        edge_detection_method='combined'
    )

    edge_strength = smoother.detect_edges(C)
    sigma_field = smoother.calculate_sigma_field(C, edge_strength)

    print(f"\n数据统计:")
    print(f"  网格大小: {C.shape}")
    print(f"  浓度范围: [{np.min(C):.4f}, {np.max(C):.4f}]")
    print(f"  边缘强度范围: [{np.min(edge_strength):.4f}, {np.max(edge_strength):.4f}]")
    print(f"  sigma范围: [{np.min(sigma_field):.4f}, {np.max(sigma_field):.4f}]")

    high_grad_count = np.sum(edge_strength > 0.05)
    print(f"  高梯度像素: {high_grad_count} ({high_grad_count/C.size*100:.1f}%)")

    C_adaptive = smoother.adaptive_gaussian_smooth(C, log_transform=True)
    C_uniform = smoother.adaptive_gaussian_smooth(C, log_transform=False)

    metrics = smoother.calculate_detail_preservation_metric(C, C_adaptive)

    print(f"\n平滑效果评估:")
    print(f"  高梯度区MAE: {metrics['mae_high_gradient']:.6f}")
    print(f"  高梯度区相关系数: {metrics['correlation_high_gradient']:.4f}")
    print(f"  总体MAE: {metrics['overall_mae']:.6f}")
    print(f"  总体RMSE: {metrics['overall_rmse']:.6f}")

    assert metrics['correlation_high_gradient'] > 0.90, "高梯度区相关性太低，细节丢失严重"
    assert metrics['overall_mae'] < 1.0, "总体误差太大"

    print(f"\n平滑效果对比 (中心线):")
    mid_idx = len(y) // 2
    print(f"  位置      原始浓度    自适应平滑    均匀平滑")
    print(f"  " + "-" * 55)
    for x_pos in [1000, 3000, 5000, 7000, 9000]:
        x_idx = np.argmin(np.abs(x - x_pos))
        c_orig = C[x_idx, mid_idx]
        c_adapt = C_adaptive[x_idx, mid_idx]
        c_uni = C_uniform[x_idx, mid_idx]
        print(f"  {x_pos:5d} m   {c_orig:10.4f}    {c_adapt:10.4f}    {c_uni:10.4f}")

    grid_data_processed = smoother.process_concentration_grid(
        grid_data, use_log=True, interpolation_factor=1, smooth_method='adaptive_gaussian'
    )

    assert 'smoothing_metrics' in grid_data_processed, "缺少平滑评估指标"
    assert grid_data_processed['smoothed'] == True, "平滑标记错误"

    isopleth_points = [(1000, -200, 200), (1500, -250, 250), (2000, -300, 300),
                       (2500, -320, 320), (3000, -350, 350), (3500, -380, 380),
                       (4000, -400, 400), (4500, -420, 420), (5000, -450, 450)]

    smoothed_pts = smoother.smooth_isopleth_points(
        isopleth_points, smoothing_method='savgol', window_length=5, poly_order=2
    )

    print(f"\n等值线平滑对比:")
    for i in range(3):
        orig = isopleth_points[i + 3]
        smooth = smoothed_pts[i + 3]
        print(f"  x={orig[0]:4d} m: 原始 y=[{orig[1]:+6.1f}, {orig[2]:+6.1f}] -> "
              f"平滑 y=[{smooth[1]:+6.1f}, {smooth[2]:+6.1f}]")

    assert len(smoothed_pts) == len(isopleth_points), "平滑后点数不一致"

    print("\n✅ 自适应平滑测试通过!")
    return True

def test_integrated_model():
    print("\n" + "=" * 60)
    print("测试5: 集成模型验证 - 所有功能联合")
    print("=" * 60)

    terrain = Terrain(x_min=0, x_max=8000, y_min=-1500, y_max=1500, resolution=80)
    terrain.add_hill(center_x=2500, center_y=300, height=120, radius=400)
    terrain.add_ridge(start_x=5000, start_y=-1000, end_x=5000, end_y=1000, height=100, width=300)

    model = GaussianPlumeModel(
        Q=100.0, u=5.0, stability_class='C', h_s=100.0,
        terrain=terrain, use_advanced_plume_rise=True,
        use_streamline_deflection=True
    )

    print("\n模型配置:")
    print(f"  源强 Q = 100 g/s")
    print(f"  风速 u = 5 m/s")
    print(f"  稳定度 = C (弱不稳定)")
    print(f"  烟囱高度 h_s = 100 m")
    print(f"  高级热源模型: 启用")
    print(f"  流线偏转模型: 启用")
    print(f"  自适应平滑: 启用")

    v_s = 15.0
    d = 3.0
    T_s = 400.0
    T_a = 293.0

    print(f"\n热源参数:")
    print(f"  出口速度 v_s = {v_s} m/s")
    print(f"  烟囱直径 d = {d} m")
    print(f"  烟气温度 T_s = {T_s} K")
    print(f"  环境温度 T_a = {T_a} K")

    x_test = np.array([500, 1000, 2500, 5000, 7500])
    y_test = np.zeros_like(x_test)
    z_test = np.zeros_like(x_test)

    C, H_e, delta_h, sigma_y, sigma_z, extra = model.calculate_concentration(
        x_test, y_test, z_test, v_s=v_s, d=d, T_s=T_s, T_a=T_a
    )

    print(f"\n计算结果:")
    print(f"  距离      浓度         有效源高    抬升高度    风偏角      地形系数")
    print(f"  " + "-" * 85)
    for i, x in enumerate(x_test):
        wd = np.degrees(extra['wind_deflection'][i]) if extra else 0
        tf = extra['terrain_factor'][i] if extra else 1.0
        print(f"  {x:5d} m   {C[i]:10.6f}    {H_e[i]:7.2f} m   {delta_h[i]:7.2f} m   {wd:+7.2f}°   {tf:.4f}")

    heat_params = model.get_heat_source_params(v_s=v_s, d=d, T_s=T_s, T_a=T_a)
    print(f"\n热源参数汇总:")
    print(f"  热释放率 Qh = {heat_params['Qh']/1000:.2f} kW")
    print(f"  浮力通量 F_b = {heat_params['F_b']:.4f} m⁴/s³")
    print(f"  特征长度 l_m = {heat_params['l_m']:.1f} m")

    x_range = (100, 8000)
    max_result = model.calculate_max_concentration(
        x_range, v_s=v_s, d=d, T_s=T_s, T_a=T_a
    )

    print(f"\n最大浓度分析:")
    print(f"  C_max = {max_result['max_C']:.6f} mg/m³ @ x = {max_result['max_x']:.0f} m")
    print(f"  H_e @ max = {max_result['H_e_at_max']:.2f} m")

    print("\n正在计算浓度场 (100x100)...")
    grid_data = model.calculate_concentration_grid(
        x_range, (-1500, 1500), z=0, resolution=50,
        v_s=v_s, d=d, T_s=T_s, T_a=T_a, apply_smoothing=True
    )

    print(f"  浓度场维度: {grid_data['C'].shape}")
    print(f"  浓度范围: [{np.nanmin(grid_data['C']):.6f}, {np.nanmax(grid_data['C']):.6f}] mg/m³")

    if grid_data.get('smoothing_metrics'):
        m = grid_data['smoothing_metrics']
        print(f"  平滑效果: 高梯度区相关系数 = {m['correlation_high_gradient']:.4f}")

    target_C = 0.01
    area, _ = model.calculate_footprint_area(
        target_C, x_range, (-1500, 1500),
        v_s=v_s, d=d, T_s=T_s, T_a=T_a
    )
    print(f"  浓度 ≥ {target_C} mg/m³ 面积: {area/1e6:.3f} km²")

    print("\n正在生成可视化图表...")
    viz = Visualizer(model)

    fig, axes = plt.subplots(2, 2, figsize=(14, 10))

    viz.plot_contour(grid_data, ax=axes[0, 0])
    axes[0, 0].set_title('浓度分布 (自适应平滑)')

    comparison = model.compare_plume_rise_models(
        x_range=(10, 5000), v_s=v_s, d=d, T_s=T_s, T_a=T_a
    )
    axes[0, 1].plot(comparison['x']/1000, comparison['delta_h_advanced'], 'b-', label='高级模型')
    axes[0, 1].plot(comparison['x']/1000, comparison['delta_h_standard'], 'r--', label='标准模型')
    axes[0, 1].set_xlabel('下风向距离 (km)')
    axes[0, 1].set_ylabel('抬升高度 (m)')
    axes[0, 1].set_title('抬升模型对比')
    axes[0, 1].legend()
    axes[0, 1].grid(True, alpha=0.3)

    viz.plot_centerline_profile(x_range, ax=axes[1, 0],
                                v_s=v_s, d=d, T_s=T_s, T_a=T_a)
    axes[1, 0].set_title('中心线浓度')

    if model.terrain is not None:
        viz.plot_streamline_deflection(u=5.0, stability_class='C',
                                       max_distance=8000, ax=axes[1, 1])
        axes[1, 1].set_title('流线偏转轨迹')

    plt.tight_layout()
    fig.savefig('test_integrated_model.png', dpi=150, bbox_inches='tight')
    plt.close()

    print("  已保存: test_integrated_model.png")

    assert not np.any(np.isnan(C)), "浓度包含NaN"
    assert np.all(C >= 0), "浓度不能为负"
    assert np.max(C) > 0, "浓度必须大于0"

    print("\n✅ 集成模型测试通过!")
    return True

def main():
    print("\n" + "#" * 60)
    print("#  大气污染物扩散模拟 - 高级功能单元测试")
    print("#" * 60)

    tests = [
        test_heat_source_model,
        test_advanced_plume_rise,
        test_streamline_deflection,
        test_adaptive_smoothing,
        test_integrated_model,
    ]

    results = []
    for test in tests:
        try:
            result = test()
            results.append((test.__name__, result, None))
        except Exception as e:
            results.append((test.__name__, False, str(e)))
            print(f"\n❌ {test.__name__} 测试失败: {e}")
            import traceback
            traceback.print_exc()

    print("\n" + "#" * 60)
    print("#  测试汇总")
    print("#" * 60)

    passed = sum(1 for _, r, _ in results if r)
    failed = sum(1 for _, r, _ in results if not r)

    print(f"\n总计: {len(tests)} 个测试, {passed} 个通过, {failed} 个失败\n")

    for name, result, error in results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"  {name:40s} {status}")
        if error:
            print(f"      错误: {error}")

    print(f"\n成功率: {passed/len(tests)*100:.1f}%")

    if failed == 0:
        print("\n🎉 所有测试通过!")
    else:
        print(f"\n⚠️  有 {failed} 个测试失败，请检查错误信息。")

    return failed == 0

if __name__ == '__main__':
    success = main()
    exit(0 if success else 1)
