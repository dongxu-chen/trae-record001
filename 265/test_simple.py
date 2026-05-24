import numpy as np
import sys

print("正在测试各模块导入...")
try:
    from stability import calculate_sigma_y, calculate_sigma_z, STABILITY_CLASSES
    print("  ✓ stability.py 导入成功")

    from plume_rise import calculate_combined_plume_rise, calculate_effective_stack_height
    print("  ✓ plume_rise.py 导入成功")

    from terrain import Terrain
    print("  ✓ terrain.py 导入成功")

    from gaussian_plume import GaussianPlumeModel
    print("  ✓ gaussian_plume.py 导入成功")

    from visualization import Visualizer
    print("  ✓ visualization.py 导入成功")
except Exception as e:
    print(f"  ✗ 导入失败: {e}")
    sys.exit(1)

print("\n正在测试稳定度模块...")
try:
    for sc in STABILITY_CLASSES:
        sigma_y = calculate_sigma_y(1000, sc)
        sigma_z = calculate_sigma_z(1000, sc)
        print(f"  稳定度 {sc}: σ_y={sigma_y:.2f}m, σ_z={sigma_z:.2f}m")
    print("  ✓ 稳定度模块测试通过")
except Exception as e:
    print(f"  ✗ 稳定度模块测试失败: {e}")
    sys.exit(1)

print("\n正在测试烟羽抬升模块...")
try:
    x = np.array([100, 500, 1000, 2000, 5000])
    Qh = 5000.0
    v_s = 15.0
    d = 3.0
    T_s = 400.0
    T_a = 293.0
    u = 5.0
    stability = 'C'

    H_e, delta_h = calculate_effective_stack_height(x, 100, Qh, v_s, d, T_s, T_a, u, stability)
    for i, xi in enumerate(x):
        print(f"  x={xi}m: Δh={delta_h[i]:.2f}m, H_e={H_e[i]:.2f}m")
    print("  ✓ 烟羽抬升模块测试通过")
except Exception as e:
    print(f"  ✗ 烟羽抬升模块测试失败: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n正在测试地形模块...")
try:
    terrain = Terrain(x_min=0, x_max=5000, y_min=-2000, y_max=2000, resolution=100)
    terrain.add_hill(2000, 0, 100, 500)

    h = terrain.get_height([0, 1000, 2000, 3000], [0, 0, 0, 0])
    print(f"  沿中心线地形高度: {h}")

    factor, h_t = terrain.calculate_terrain_factor(2000, 0, 150, 'C')
    print(f"  地形修正因子: {factor:.4f}")
    print("  ✓ 地形模块测试通过")
except Exception as e:
    print(f"  ✗ 地形模块测试失败: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n正在测试高斯烟羽模型...")
try:
    model = GaussianPlumeModel(Q=100.0, u=5.0, stability_class='C', h_s=100.0)

    C, H_e, delta_h, sigma_y, sigma_z = model.calculate_concentration(
        1000, 0, 0, Qh=5000, v_s=15, d=3, T_s=400, T_a=293
    )
    print(f"  x=1000m, y=0, z=0 处浓度: {C:.6f} mg/m³")
    print(f"  H_e={H_e:.2f}m, Δh={delta_h:.2f}m, σ_y={sigma_y:.2f}m, σ_z={sigma_z:.2f}m")

    max_result = model.calculate_max_concentration(
        x_range=(100, 5000), Qh=5000, v_s=15, d=3, T_s=400, T_a=293
    )
    print(f"  最大浓度: {max_result['max_C']:.6f} mg/m³ @ x={max_result['max_x']:.0f}m")

    grid_data = model.calculate_concentration_grid(
        (0, 5000), (-1000, 1000), z=0, resolution=50,
        Qh=5000, v_s=15, d=3, T_s=400, T_a=293
    )
    print(f"  网格数据形状: C={grid_data['C'].shape}, X={grid_data['X'].shape}")
    print(f"  浓度范围: [{grid_data['C'].min():.2e}, {grid_data['C'].max():.2e}]")
    print("  ✓ 高斯烟羽模型测试通过")
except Exception as e:
    print(f"  ✗ 高斯烟羽模型测试失败: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n正在测试带地形的高斯烟羽模型...")
try:
    terrain = Terrain(x_min=0, x_max=5000, y_min=-2000, y_max=2000, resolution=100)
    terrain.add_hill(2000, 0, 100, 500)

    model_with_terrain = GaussianPlumeModel(Q=100.0, u=5.0, stability_class='C', h_s=100.0, terrain=terrain)
    model_no_terrain = GaussianPlumeModel(Q=100.0, u=5.0, stability_class='C', h_s=100.0, terrain=None)

    C_with, H_e_w, _, _, _ = model_with_terrain.calculate_concentration(
        2000, 0, 0, Qh=5000, v_s=15, d=3, T_s=400, T_a=293
    )
    C_without, H_e_wo, _, _, _ = model_no_terrain.calculate_concentration(
        2000, 0, 0, Qh=5000, v_s=15, d=3, T_s=400, T_a=293
    )
    print(f"  山丘顶部 (2000,0):")
    print(f"    有地形: C={C_with:.6f} mg/m³, H_e={H_e_w:.2f}m")
    print(f"    无地形: C={C_without:.6f} mg/m³, H_e={H_e_wo:.2f}m")
    print(f"    相对差异: {abs(C_with - C_without) / max(C_without, 1e-10) * 100:.2f}%")
    print("  ✓ 带地形的高斯烟羽模型测试通过")
except Exception as e:
    print(f"  ✗ 带地形的高斯烟羽模型测试失败: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n" + "=" * 60)
print("所有模块测试通过! ✅")
print("=" * 60)
