import sys
import os
import json

os.chdir(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, '.')

def test_all_features():
    results = []
    
    print('=' * 70)
    print('分子动力学模拟 - 新功能验证')
    print('=' * 70)
    
    # Test 1: 多种势函数
    print('\n[测试1] 多种势函数支持...')
    try:
        from potentials import (
            get_potential_config, compute_potential_energy, compute_force_vector,
            morse_potential, morse_force_vector,
            coulomb_potential, coulomb_force_vector,
            lennard_jones_potential, lennard_jones_force_vector
        )
        import numpy as np
        
        r2 = np.array([1.0, 2.25, 4.0, 6.25])
        
        # LJ势
        pe_lj = compute_potential_energy(r2, get_potential_config('lj', r_cut=3.0))
        assert pe_lj[0] < 0, 'LJ势在r=1应该为正'
        print(f'  ✓ Lennard-Jones势: PE={pe_lj}')
        
        # Morse势
        pe_morse = compute_potential_energy(r2, get_potential_config('morse', r_cut=3.0))
        assert pe_morse[0] > 0, 'Morse势在r=1应该为正'
        print(f'  ✓ Morse势: PE={pe_morse}')
        
        # Coulomb势
        pe_coulomb = compute_potential_energy(r2, get_potential_config('coulomb', r_cut=3.0))
        assert abs(pe_coulomb[0] - 1.0) < 1e-6, 'Coulomb势在r=1应为1.0'
        print(f'  ✓ Coulomb势: PE={pe_coulomb}')
        
        results.append(('势函数', True))
    except Exception as e:
        print(f'  ✗ 失败: {e}')
        import traceback
        traceback.print_exc()
        results.append(('势函数', False))
    
    # Test 2: Berendsen恒温器
    print('\n[测试2] Berendsen恒温器...')
    try:
        from integrators import BerendsenThermostat
        
        thermostat = BerendsenThermostat(temperature=1.0, tau=0.1)
        velocities = np.random.randn(100, 3) * 0.5
        current_temp = 0.5
        
        scaled_vel = thermostat.apply(velocities, dt=0.001, current_temperature=current_temp)
        lambda_val = thermostat.get_lambda()
        assert lambda_val > 1.0, f'温度低于目标时lambda应大于1，实际: {lambda_val}'
        print(f'  ✓ 低温时 lambda={lambda_val:.4f} (速度增大)')
        
        scaled_vel2 = thermostat.apply(velocities, dt=0.001, current_temperature=1.5)
        lambda_val2 = thermostat.get_lambda()
        assert lambda_val2 < 1.0, f'温度高于目标时lambda应小于1，实际: {lambda_val2}'
        print(f'  ✓ 高温时 lambda={lambda_val2:.4f} (速度减小)')
        
        results.append(('Berendsen恒温器', True))
    except Exception as e:
        print(f'  ✗ 失败: {e}')
        import traceback
        traceback.print_exc()
        results.append(('Berendsen恒温器', False))
    
    # Test 3: 配置文件系统
    print('\n[测试3] 配置文件系统...')
    try:
        from config import load_config, save_config, create_example_config, merge_config
        
        test_config_path = 'test_config.json'
        create_example_config(test_config_path)
        
        config = load_config(test_config_path)
        assert config['system']['n_particles'] == 256
        assert config['thermostat']['enabled'] == True
        print(f'  ✓ 配置文件加载成功')
        
        os.remove(test_config_path)
        results.append(('配置文件', True))
    except Exception as e:
        print(f'  ✗ 失败: {e}')
        import traceback
        traceback.print_exc()
        results.append(('配置文件', False))
    
    # Test 4: XYZ轨迹输出
    print('\n[测试4] XYZ轨迹输出...')
    try:
        from trajectory import XYZWriter, ExtendedXYZWriter, read_xyz
        
        test_xyz_path = 'test_trajectory.xyz'
        positions = np.random.rand(10, 3) * 10.0
        velocities = np.random.randn(10, 3)
        
        with XYZWriter(test_xyz_path, element='Ar') as writer:
            writer.write_frame(positions, step=0, box_length=10.0)
            writer.write_frame(positions + 0.1, step=100, box_length=10.0)
        
        frames = read_xyz(test_xyz_path)
        assert len(frames) == 2
        assert frames[0]['n_atoms'] == 10
        print(f'  ✓ XYZ轨迹写入和读取成功 (2帧, 10粒子)')
        
        os.remove(test_xyz_path)
        results.append(('XYZ轨迹', True))
    except Exception as e:
        print(f'  ✗ 失败: {e}')
        import traceback
        traceback.print_exc()
        results.append(('XYZ轨迹', False))
    
    # Test 5: 完整MD模拟 - LJ势
    print('\n[测试5] Lennard-Jones势完整模拟...')
    try:
        from molecular_dynamics import MolecularDynamics
        
        md_lj = MolecularDynamics(
            n_particles=32, temperature=1.0, density=0.8,
            dt=0.001, n_steps=1000, potential_type='lj',
            thermostat_enabled=False, seed=42
        )
        history_lj = md_lj.run(output_interval=200, verbose=False)
        
        assert len(history_lj) == 5
        print(f'  ✓ LJ势模拟完成: 最终T={md_lj.temperature:.4f}, PE={md_lj.potential_energy:.4f}')
        results.append(('LJ模拟', True))
    except Exception as e:
        print(f'  ✗ 失败: {e}')
        import traceback
        traceback.print_exc()
        results.append(('LJ模拟', False))
    
    # Test 6: 完整MD模拟 - Morse势
    print('\n[测试6] Morse势完整模拟...')
    try:
        md_morse = MolecularDynamics(
            n_particles=32, temperature=1.0, density=0.8,
            dt=0.001, n_steps=1000, potential_type='morse',
            potential_config={'type': 'morse', 'epsilon': 1.0, 'alpha': 12.0, 'r0': 1.0, 'r_cut': 2.5},
            thermostat_enabled=False, seed=42
        )
        history_morse = md_morse.run(output_interval=200, verbose=False)
        
        print(f'  ✓ Morse势模拟完成: 最终T={md_morse.temperature:.4f}, PE={md_morse.potential_energy:.4f}')
        results.append(('Morse模拟', True))
    except Exception as e:
        print(f'  ✗ 失败: {e}')
        import traceback
        traceback.print_exc()
        results.append(('Morse模拟', False))
    
    # Test 7: Berendsen恒温模拟
    print('\n[测试7] Berendsen恒温模拟...')
    try:
        md_thermo = MolecularDynamics(
            n_particles=32, temperature=1.0, density=0.8,
            dt=0.001, n_steps=2000, potential_type='lj',
            thermostat_enabled=True, thermostat_type='berendsen',
            thermostat_tau=0.1, target_temperature=1.5,
            seed=42
        )
        history_thermo = md_thermo.run(output_interval=200, verbose=False)
        
        temps = [h['temperature'] for h in history_thermo]
        print(f'  ✓ Berendsen恒温模拟完成')
        print(f'    温度变化: {[f"{t:.3f}" for t in temps[:5]]}... -> {temps[-1]:.3f}')
        print(f'    目标温度: 1.5, 最终温度: {md_thermo.temperature:.3f}')
        results.append(('Berendsen模拟', True))
    except Exception as e:
        print(f'  ✗ 失败: {e}')
        import traceback
        traceback.print_exc()
        results.append(('Berendsen模拟', False))
    
    # Test 8: 带轨迹输出的模拟
    print('\n[测试8] 带轨迹输出的模拟...')
    try:
        md_traj = MolecularDynamics(
            n_particles=32, temperature=1.0, density=0.8,
            dt=0.001, n_steps=1000, potential_type='lj',
            thermostat_enabled=False, seed=42
        )
        traj_path = 'md_test_traj.xyz'
        history_traj = md_traj.run(
            output_interval=200, save_trajectory=True,
            trajectory_file=traj_path, include_velocities=True,
            verbose=False
        )
        
        frames = read_xyz(traj_path)
        assert len(frames) == 6  # 0, 200, 400, 600, 800, 1000
        print(f'  ✓ 轨迹模拟完成: {len(frames)}帧已保存到 {traj_path}')
        
        os.remove(traj_path)
        results.append(('轨迹输出', True))
    except Exception as e:
        print(f'  ✗ 失败: {e}')
        import traceback
        traceback.print_exc()
        results.append(('轨迹输出', False))
    
    # Summary
    print('\n' + '=' * 70)
    print('测试结果汇总:')
    print('=' * 70)
    passed = 0
    failed = 0
    for name, success in results:
        status = '✓ 通过' if success else '✗ 失败'
        print(f'  {name}: {status}')
        if success:
            passed += 1
        else:
            failed += 1
    
    print(f'\n总计: {passed}/{len(results)} 通过, {failed}/{len(results)} 失败')
    print('=' * 70)
    
    return failed == 0


if __name__ == '__main__':
    success = test_all_features()
    sys.exit(0 if success else 1)
