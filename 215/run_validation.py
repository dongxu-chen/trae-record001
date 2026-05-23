import sys
import os

os.chdir(r'd:\Trae\project\record001\215')
sys.path.insert(0, '.')

with open('validation_result.txt', 'w', encoding='utf-8') as f:
    try:
        f.write('开始验证...\n')
        f.flush()
        
        import numpy as np
        f.write('OK: numpy\n')
        f.flush()
        
        from potentials import (
            get_potential_config, compute_potential_energy, compute_force_vector,
            morse_potential, morse_force_vector,
            coulomb_potential, coulomb_force_vector,
            lennard_jones_potential, lennard_jones_force_vector
        )
        f.write('OK: potentials 导入\n')
        f.flush()
        
        r2 = np.array([1.0, 2.25, 4.0, 6.25])
        
        pe_lj = compute_potential_energy(r2, get_potential_config('lj', r_cut=3.0))
        f.write(f'LJ势能: {pe_lj}\n')
        f.flush()
        
        pe_morse = compute_potential_energy(r2, get_potential_config('morse', r_cut=3.0))
        f.write(f'Morse势能: {pe_morse}\n')
        f.flush()
        
        pe_coulomb = compute_potential_energy(r2, get_potential_config('coulomb', r_cut=3.0))
        f.write(f'Coulomb势能: {pe_coulomb}\n')
        f.flush()
        
        f.write('OK: 势函数测试通过\n')
        f.flush()
        
        from integrators import BerendsenThermostat, VerletIntegrator
        f.write('OK: integrators 导入\n')
        f.flush()
        
        thermostat = BerendsenThermostat(temperature=1.0, tau=0.1)
        velocities = np.random.randn(100, 3) * 0.5
        scaled_vel = thermostat.apply(velocities, dt=0.001, current_temperature=0.5)
        lambda_val = thermostat.get_lambda()
        f.write(f'Berendsen恒温器 lambda (低温): {lambda_val:.4f}\n')
        f.flush()
        
        scaled_vel2 = thermostat.apply(velocities, dt=0.001, current_temperature=1.5)
        lambda_val2 = thermostat.get_lambda()
        f.write(f'Berendsen恒温器 lambda (高温): {lambda_val2:.4f}\n')
        f.flush()
        
        f.write('OK: Berendsen恒温器测试通过\n')
        f.flush()
        
        from config import load_config, save_config, create_example_config
        f.write('OK: config 导入\n')
        f.flush()
        
        test_config_path = 'test_config_validation.json'
        create_example_config(test_config_path)
        config = load_config(test_config_path)
        f.write(f'配置加载成功: n_particles={config["system"]["n_particles"]}\n')
        f.flush()
        os.remove(test_config_path)
        
        f.write('OK: 配置文件测试通过\n')
        f.flush()
        
        from trajectory import XYZWriter, ExtendedXYZWriter, read_xyz
        f.write('OK: trajectory 导入\n')
        f.flush()
        
        test_xyz_path = 'test_traj_validation.xyz'
        positions = np.random.rand(10, 3) * 10.0
        velocities = np.random.randn(10, 3)
        
        with XYZWriter(test_xyz_path, element='Ar') as writer:
            writer.write_frame(positions, step=0, box_length=10.0)
            writer.write_frame(positions + 0.1, step=100, box_length=10.0)
        
        frames = read_xyz(test_xyz_path)
        f.write(f'XYZ轨迹测试: {len(frames)}帧, 每帧{frames[0]["n_atoms"]}原子\n')
        f.flush()
        os.remove(test_xyz_path)
        
        f.write('OK: XYZ轨迹测试通过\n')
        f.flush()
        
        from molecular_dynamics import MolecularDynamics
        f.write('OK: molecular_dynamics 导入\n')
        f.flush()
        
        f.write('\n--- 开始完整MD模拟测试 ---\n')
        f.flush()
        
        md_lj = MolecularDynamics(
            n_particles=32, temperature=1.0, density=0.8,
            dt=0.001, n_steps=500, potential_type='lj',
            thermostat_enabled=False, seed=42
        )
        history_lj = md_lj.run(output_interval=100, verbose=False)
        f.write(f'LJ模拟完成: 最终T={md_lj.temperature:.4f}, PE={md_lj.potential_energy:.4f}\n')
        f.flush()
        
        md_morse = MolecularDynamics(
            n_particles=32, temperature=1.0, density=0.8,
            dt=0.001, n_steps=500, potential_type='morse',
            potential_config={'type': 'morse', 'epsilon': 1.0, 'alpha': 12.0, 'r0': 1.0, 'r_cut': 2.5},
            thermostat_enabled=False, seed=42
        )
        history_morse = md_morse.run(output_interval=100, verbose=False)
        f.write(f'Morse模拟完成: 最终T={md_morse.temperature:.4f}, PE={md_morse.potential_energy:.4f}\n')
        f.flush()
        
        md_thermo = MolecularDynamics(
            n_particles=32, temperature=1.0, density=0.8,
            dt=0.001, n_steps=1000, potential_type='lj',
            thermostat_enabled=True, thermostat_type='berendsen',
            thermostat_tau=0.1, target_temperature=1.5,
            seed=42
        )
        history_thermo = md_thermo.run(output_interval=200, verbose=False)
        temps = [h['temperature'] for h in history_thermo]
        f.write(f'Berendsen恒温模拟: 温度变化={[f"{t:.3f}" for t in temps]}, 最终T={md_thermo.temperature:.3f}\n')
        f.flush()
        
        md_traj = MolecularDynamics(
            n_particles=32, temperature=1.0, density=0.8,
            dt=0.001, n_steps=500, potential_type='lj',
            thermostat_enabled=False, seed=42
        )
        traj_path = 'md_validation_traj.xyz'
        history_traj = md_traj.run(
            output_interval=100, save_trajectory=True,
            trajectory_file=traj_path, include_velocities=True,
            verbose=False
        )
        frames = read_xyz(traj_path)
        f.write(f'轨迹输出模拟: {len(frames)}帧已保存\n')
        f.flush()
        os.remove(traj_path)
        
        f.write('\n' + '='*60 + '\n')
        f.write('所有测试通过!\n')
        f.write('='*60 + '\n')
        
    except Exception as e:
        import traceback
        f.write(f'错误: {e}\n')
        f.write(traceback.format_exc())

print('验证完成，结果已保存到 validation_result.txt')
