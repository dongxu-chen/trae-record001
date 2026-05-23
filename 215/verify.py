import sys
sys.path.insert(0, '.')

print("=" * 60)
print("分子动力学模拟框架验证")
print("=" * 60)

try:
    import numpy as np
    print("✓ NumPy 已导入")
except Exception as e:
    print(f"✗ NumPy 导入失败: {e}")
    sys.exit(1)

try:
    from potentials import lennard_jones_potential, lennard_jones_force
    print("✓ potentials 模块已导入")
    
    r_min = 2.0 ** (1.0/6.0)
    pe = lennard_jones_potential(np.array([r_min**2]), r_cut=3.0)
    assert abs(pe[0] + 1.0) < 1e-6, f"LJ势测试失败: {pe[0]}"
    print("  - Lennard-Jones势能测试通过")
except Exception as e:
    print(f"✗ potentials 模块测试失败: {e}")
    import traceback
    traceback.print_exc()

try:
    from integrators import VerletIntegrator
    print("✓ integrators 模块已导入")
    
    integrator = VerletIntegrator(dt=0.001)
    pos = np.array([[0.0, 0.0, 0.0]])
    vel = np.array([[1.0, 0.0, 0.0]])
    forces = np.array([[0.0, 0.0, 0.0]])
    
    new_pos, half_vel = integrator.step(pos, vel, forces)
    assert abs(new_pos[0,0] - 0.001) < 1e-10, f"Verlet积分测试失败"
    print("  - Verlet积分器测试通过")
except Exception as e:
    print(f"✗ integrators 模块测试失败: {e}")
    import traceback
    traceback.print_exc()

try:
    from neighbor_list import NeighborList
    print("✓ neighbor_list 模块已导入")
    
    positions = np.array([[0.0,0,0], [1.0,0,0], [3.0,0,0]])
    nl = NeighborList(r_cut=1.5, r_skin=0.0, box_length=10.0)
    neighbors = nl.build(positions)
    assert 1 in neighbors[0], "邻居列表测试失败"
    assert len(neighbors[2]) == 0, "邻居列表测试失败"
    print("  - 邻居列表测试通过")
except Exception as e:
    print(f"✗ neighbor_list 模块测试失败: {e}")
    import traceback
    traceback.print_exc()

try:
    from utils import pbc_wrap, calculate_temperature, get_box_length
    print("✓ utils 模块已导入")
    
    box = get_box_length(1000, 1.0, 3)
    assert abs(box**3 - 1000.0) < 1e-6, "盒子长度测试失败"
    
    wrapped = pbc_wrap(np.array([[12.0, -1.0, 5.0]]), 10.0)
    assert abs(wrapped[0,0] - 2.0) < 1e-6, "PBC包装测试失败"
    print("  - 工具函数测试通过")
except Exception as e:
    print(f"✗ utils 模块测试失败: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 60)
print("运行完整MD模拟测试...")
print("=" * 60)

try:
    from molecular_dynamics import MolecularDynamics
    
    md = MolecularDynamics(
        n_particles=64,
        temperature=1.0,
        density=0.8,
        dt=0.001,
        n_steps=1000,
        dim=3,
        seed=42
    )
    
    print(f"✓ MD系统初始化成功")
    print(f"  粒子数: {md.n_particles}")
    print(f"  盒子边长: {md.box_length:.4f}")
    print(f"  初始温度: {md.temperature:.4f}")
    print(f"  初始势能: {md.potential_energy:.4f}")
    print(f"  初始动能: {md.kinetic_energy:.4f}")
    
    print(f"\n运行模拟 (1000步)...")
    print(f"{'步':>6} | {'动能':>10} | {'势能':>10} | {'温度':>8}")
    print("-" * 50)
    
    for step in range(1, 1001):
        md.step()
        if step % 100 == 0:
            print(f"{step:>6d} | {md.kinetic_energy:>10.3f} | {md.potential_energy:>10.3f} | {md.temperature:>8.3f}")
    
    print("\n✓ 模拟运行成功!")
    
    history = md.get_energy_history()
    if len(history) > 0:
        temps = [h['temperature'] for h in history]
        energies = [h['total_energy'] for h in history]
        print(f"\n统计结果:")
        print(f"  平均温度: {np.mean(temps):.4f} ± {np.std(temps):.4f}")
        print(f"  平均总能: {np.mean(energies):.4f} ± {np.std(energies):.4f}")
        print(f"  邻居列表更新次数: {md.n_neighbor_updates}")
    
except Exception as e:
    print(f"✗ MD模拟测试失败: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 60)
print("验证完成!")
print("=" * 60)
