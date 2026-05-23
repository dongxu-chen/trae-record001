import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

output_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'md_test_output.txt')

f = open(output_file, 'w', encoding='utf-8')
old_stdout = sys.stdout
sys.stdout = f

try:
    import numpy as np
    from molecular_dynamics import MolecularDynamics
    
    print('=' * 60)
    print('分子动力学模拟框架 - 测试报告')
    print('=' * 60)
    print()
    
    print('1. 测试模块导入...')
    from potentials import lennard_jones_potential, lennard_jones_force
    from integrators import VerletIntegrator
    from neighbor_list import NeighborList
    from utils import pbc_wrap, calculate_temperature, get_box_length
    print('   ✓ 所有模块导入成功')
    print()
    
    print('2. 测试Lennard-Jones势...')
    r_min = 2.0 ** (1.0/6.0)
    pe = lennard_jones_potential(np.array([r_min**2]), r_cut=3.0)
    assert abs(pe[0] + 1.0) < 1e-6, f'LJ势测试失败: {pe[0]}'
    print(f'   ✓ LJ势在r_min={r_min:.4f}处值为{pe[0]:.6f} (正确)')
    
    pe_zero = lennard_jones_potential(np.array([1.0]), r_cut=3.0)
    assert abs(pe_zero[0]) < 1e-6, f'LJ势零点测试失败: {pe_zero[0]}'
    print(f'   ✓ LJ势在r=1.0处值为{pe_zero[0]:.6f} (正确)')
    print()
    
    print('3. 测试周期性边界条件...')
    wrapped = pbc_wrap(np.array([[12.0, -1.0, 5.0]]), 10.0)
    assert abs(wrapped[0,0] - 2.0) < 1e-6
    assert abs(wrapped[0,1] - 9.0) < 1e-6
    print(f'   ✓ PBC包装: [12, -1, 5] → [{wrapped[0,0]:.1f}, {wrapped[0,1]:.1f}, {wrapped[0,2]:.1f}]')
    
    box = get_box_length(1000, 1.0, 3)
    assert abs(box**3 - 1000.0) < 1e-6
    print(f'   ✓ 盒子长度: N=1000, ρ=1.0 → L={box:.4f}')
    print()
    
    print('4. 测试邻居列表...')
    positions = np.array([[0.0,0,0], [1.0,0,0], [3.0,0,0]])
    nl = NeighborList(r_cut=1.5, r_skin=0.0, box_length=10.0)
    neighbors = nl.build(positions)
    assert 1 in neighbors[0]
    assert len(neighbors[2]) == 0
    print(f'   ✓ 邻居列表: 粒子0的邻居={neighbors[0]}, 粒子2的邻居={neighbors[2]}')
    print()
    
    print('5. 初始化MD系统...')
    md = MolecularDynamics(
        n_particles=64,
        temperature=1.0,
        density=0.8,
        dt=0.001,
        n_steps=1000,
        dim=3,
        seed=42
    )
    print(f'   ✓ 系统初始化成功')
    print(f'     粒子数: {md.n_particles}')
    print(f'     盒子边长: {md.box_length:.4f}')
    print(f'     初始温度: {md.temperature:.4f}')
    print(f'     初始势能: {md.potential_energy:.4f}')
    print(f'     初始动能: {md.kinetic_energy:.4f}')
    print()
    
    print('6. 运行1000步MD模拟...')
    print(f'   {"步":>6} | {"动能":>10} | {"势能":>10} | {"总能":>10} | {"温度":>8}')
    print(f'   {"-"*60}')
    
    for step in range(1, 1001):
        md.step()
        if step % 100 == 0:
            te = md.kinetic_energy + md.potential_energy
            print(f'   {step:>6d} | {md.kinetic_energy:>10.3f} | {md.potential_energy:>10.3f} | {te:>10.3f} | {md.temperature:>8.3f}')
    
    print()
    print('   ✓ 模拟运行成功!')
    print(f'     邻居列表更新次数: {md.n_neighbor_updates}')
    print()
    
    print('7. 统计分析...')
    history = md.run(output_interval=100, verbose=False)
    if len(history) > 0:
        temps = [h['temperature'] for h in history]
        kes = [h['kinetic_energy'] for h in history]
        pes = [h['potential_energy'] for h in history]
        energies = [h['total_energy'] for h in history]
        
        print(f'   后1000步统计:')
        print(f'     平均温度: {np.mean(temps):.4f} ± {np.std(temps):.4f}')
        print(f'     平均动能: {np.mean(kes):.4f} ± {np.std(kes):.4f}')
        print(f'     平均势能: {np.mean(pes):.4f} ± {np.std(pes):.4f}')
        print(f'     平均总能: {np.mean(energies):.4f} ± {np.std(energies):.4f}')
        print(f'     总能相对涨落: {np.std(energies)/abs(np.mean(energies)):.6f}')
    print()
    
    print('=' * 60)
    print('所有测试通过! ✓')
    print('=' * 60)
    
    f.close()
    sys.stdout = old_stdout
    print('测试完成! 结果已写入 md_test_output.txt')
    
except Exception as e:
    import traceback
    f.write(f'\n错误: {e}\n')
    f.write(traceback.format_exc())
    f.close()
    sys.stdout = old_stdout
    print(f'测试失败! 错误已写入 md_test_output.txt')
    print(f'错误: {e}')
    traceback.print_exc()
