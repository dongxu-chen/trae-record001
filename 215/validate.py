import sys
import os
import traceback

os.chdir(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, '.')

log_file = 'verification_log.txt'

with open(log_file, 'w', encoding='utf-8') as log:
    def log_print(msg):
        print(msg, flush=True)
        log.write(msg + '\n')
        log.flush()
    
    try:
        log_print('='*70)
        log_print('分子动力学模拟框架 - 验证报告')
        log_print('='*70)
        
        log_print('\n[1] 测试模块导入...')
        import numpy as np
        log_print('  ✓ NumPy 导入成功')
        
        from potentials import lennard_jones_potential, lennard_jones_force, lennard_jones_force_vector
        log_print('  ✓ potentials 模块导入成功')
        
        from integrators import VerletIntegrator
        log_print('  ✓ integrators 模块导入成功')
        
        from neighbor_list import NeighborList
        log_print('  ✓ neighbor_list 模块导入成功')
        
        from utils import (pbc_wrap, pbc_distance, initialize_fcc, initialize_velocities,
                          calculate_kinetic_energy, calculate_temperature, get_box_length)
        log_print('  ✓ utils 模块导入成功')
        
        from molecular_dynamics import MolecularDynamics
        log_print('  ✓ molecular_dynamics 模块导入成功')
        
        log_print('\n[2] 测试Lennard-Jones势...')
        r_min = 2.0 ** (1.0/6.0)
        pe = lennard_jones_potential(np.array([r_min**2]), r_cut=3.0)
        assert abs(pe[0] + 1.0) < 1e-6, f'LJ势最小值测试失败: {pe[0]}'
        log_print(f'  ✓ LJ势在r_min={r_min:.4f}处为{pe[0]:.6f} (正确: -1.0)')
        
        pe_cut = lennard_jones_potential(np.array([(2.5**2)]), r_cut=2.5)
        assert pe_cut[0] == 0.0, f'LJ势截断测试失败: {pe_cut[0]}'
        log_print(f'  ✓ LJ势截断测试通过 (r_cut=2.5)')
        
        f_at_min = lennard_jones_force(np.array([r_min]), np.array([r_min**2]), r_cut=3.0)
        assert abs(f_at_min[0]) < 1e-6, f'LJ力零点测试失败: {f_at_min[0]}'
        log_print(f'  ✓ LJ力在势阱处为零 (正确)')
        
        log_print('\n[3] 测试周期性边界条件...')
        box = 10.0
        wrapped = pbc_wrap(np.array([[12.0, -1.0, 5.0]]), box)
        assert abs(wrapped[0,0] - 2.0) < 1e-6
        assert abs(wrapped[0,1] - 9.0) < 1e-6
        log_print(f'  ✓ PBC包装: [12, -1, 5] -> [{wrapped[0,0]:.0f}, {wrapped[0,1]:.0f}, {wrapped[0,2]:.0f}]')
        
        dr = pbc_distance(np.array([[8.0, 0.0, 0.0]]), box)
        assert abs(dr[0,0] - (-2.0)) < 1e-6
        log_print(f'  ✓ 最小镜像距离: dr=[8,0,0] -> [{dr[0,0]:.0f}, {dr[0,1]:.0f}, {dr[0,2]:.0f}]')
        
        box_len = get_box_length(1000, 1.0, 3)
        assert abs(box_len**3 - 1000.0) < 1e-6
        log_print(f'  ✓ 盒子长度: N=1000, rho=1.0 -> L={box_len:.4f}')
        
        log_print('\n[4] 测试邻居列表...')
        test_pos = np.array([[0.0,0,0], [1.0,0,0], [3.0,0,0]])
        nl = NeighborList(r_cut=1.5, r_skin=0.0, box_length=10.0)
        neighbors = nl.build(test_pos)
        assert 1 in neighbors[0]
        assert len(neighbors[2]) == 0
        log_print(f'  ✓ 邻居列表: 粒子0邻居={list(neighbors[0])}, 粒子2邻居={list(neighbors[2])}')
        
        nl2 = NeighborList(r_cut=1.5, r_skin=0.5, box_length=10.0)
        nl2.build(test_pos)
        assert not nl2.need_update(test_pos)
        test_pos2 = test_pos.copy()
        test_pos2[0] += 0.3
        assert nl2.need_update(test_pos2)
        log_print(f'  ✓ 邻居列表更新检测正常')
        
        log_print('\n[5] 测试Verlet积分器...')
        integrator = VerletIntegrator(dt=0.001)
        pos = np.array([[0.0, 0.0, 0.0]])
        vel = np.array([[1.0, 0.0, 0.0]])
        forces = np.array([[0.0, 0.0, 0.0]])
        
        new_pos, half_vel = integrator.step(pos, vel, forces)
        assert abs(new_pos[0,0] - 0.001) < 1e-10
        new_vel = integrator.finalize_velocity(half_vel, forces)
        assert abs(new_vel[0,0] - 1.0) < 1e-10
        log_print(f'  ✓ Verlet积分: 匀速运动测试通过')
        
        log_print('\n[6] 测试FCC晶格初始化...')
        fcc_pos = initialize_fcc(32, 10.0, dim=3)
        assert fcc_pos.shape == (32, 3)
        assert np.all(fcc_pos >= 0) and np.all(fcc_pos <= 10.0)
        log_print(f'  ✓ FCC初始化: 32个粒子生成成功')
        
        log_print('\n[7] 测试速度初始化...')
        vel = initialize_velocities(100, temperature=1.0, dim=3, seed=42)
        temp = calculate_temperature(vel)
        assert abs(temp - 1.0) < 0.2
        log_print(f'  ✓ 速度初始化: 目标T=1.0, 实际T={temp:.4f}')
        
        log_print('\n' + '='*70)
        log_print('所有基础测试通过!')
        log_print('='*70)
        
        log_print('\n[8] 运行完整MD模拟...')
        md = MolecularDynamics(
            n_particles=64,
            temperature=1.0,
            density=0.8,
            dt=0.001,
            n_steps=2000,
            dim=3,
            seed=42
        )
        
        log_print(f'  系统参数:')
        log_print(f'    粒子数: {md.n_particles}')
        log_print(f'    盒子边长: {md.box_length:.4f}')
        log_print(f'    初始温度: {md.temperature:.4f}')
        log_print(f'    初始势能: {md.potential_energy:.4f}')
        log_print(f'    初始动能: {md.kinetic_energy:.4f}')
        
        log_print(f'\n  模拟进度 (每200步输出):')
        log_print(f'  {"步":>6} | {"动能":>10} | {"势能":>10} | {"总能":>10} | {"温度":>8}')
        log_print(f'  {"-"*56}')
        
        initial_energy = md.kinetic_energy + md.potential_energy
        
        for step in range(1, 2001):
            md.step()
            if step % 200 == 0:
                te = md.kinetic_energy + md.potential_energy
                log_print(f'  {step:>6d} | {md.kinetic_energy:>10.3f} | {md.potential_energy:>10.3f} | {te:>10.3f} | {md.temperature:>8.3f}')
        
        final_energy = md.kinetic_energy + md.potential_energy
        energy_drift = abs(final_energy - initial_energy) / abs(initial_energy)
        
        log_print(f'\n  模拟统计:')
        log_print(f'    邻居列表更新次数: {md.n_neighbor_updates}')
        log_print(f'    初始总能: {initial_energy:.4f}')
        log_print(f'    最终总能: {final_energy:.4f}')
        log_print(f'    能量漂移: {energy_drift:.6%}')
        
        log_print('\n' + '='*70)
        log_print('✓ MD模拟验证完成!')
        log_print('='*70)
        
    except Exception as e:
        log_print(f'\n✗ 错误: {e}')
        log_print(traceback.format_exc())
        sys.exit(1)

print('验证完成，结果已保存到 verification_log.txt')
