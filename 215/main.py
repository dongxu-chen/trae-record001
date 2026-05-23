import argparse
import json
import os
import sys

from molecular_dynamics import MolecularDynamics
from config import load_config, save_config, create_example_config, print_config
from potentials import POTENTIAL_TYPES


def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description='分子动力学模拟 - 支持LJ/Morse/Coulomb势 + Berendsen恒温 + XYZ轨迹',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
示例:
  # 使用配置文件
  python main.py --config config.json
  
  # 生成示例配置文件
  python main.py --example-config config.json
  
  # 命令行直接指定参数
  python main.py -n 256 -T 1.0 -rho 0.8 -s 50000 --potential morse
  
  # 启用Berendsen恒温器
  python main.py -n 108 --thermostat --tau 0.5 --target-temp 1.2
  
  # 保存XYZ轨迹
  python main.py -n 256 -s 10000 --save-trajectory --trajectory-file md_traj.xyz
  
  # 使用Coulomb势
  python main.py -n 100 --potential coulomb --k-coulomb 1.0
        '''
    )
    
    parser.add_argument('--config', type=str, default=None,
                        help='配置文件路径 (JSON/YAML)')
    parser.add_argument('--example-config', type=str, default=None,
                        help='生成示例配置文件')
    
    parser.add_argument('-n', '--n-particles', type=int, default=None,
                        help='粒子数')
    parser.add_argument('-T', '--temperature', type=float, default=None,
                        help='初始温度 (约化单位)')
    parser.add_argument('-rho', '--density', type=float, default=None,
                        help='数密度')
    parser.add_argument('-dt', '--timestep', type=float, default=None,
                        help='时间步长')
    parser.add_argument('-s', '--steps', type=int, default=None,
                        help='总模拟步数')
    parser.add_argument('-o', '--output-interval', type=int, default=None,
                        help='输出间隔步数')
    parser.add_argument('-rc', '--r-cut', type=float, default=None,
                        help='截断半径')
    parser.add_argument('-rs', '--r-skin', type=float, default=None,
                        help='邻居列表皮肤层厚度')
    parser.add_argument('-d', '--dim', type=int, default=None, choices=[2, 3],
                        help='维度 (2或3)')
    parser.add_argument('--gpu', action='store_true',
                        help='使用GPU加速 (需要CuPy)')
    parser.add_argument('--seed', type=int, default=None,
                        help='随机种子')
    
    parser.add_argument('--potential', type=str, default=None,
                        choices=POTENTIAL_TYPES,
                        help=f'势函数类型 ({", ".join(POTENTIAL_TYPES)})')
    parser.add_argument('--epsilon', type=float, default=None,
                        help='势阱深度 (LJ/Morse)')
    parser.add_argument('--sigma', type=float, default=None,
                        help='粒子直径 (LJ)')
    parser.add_argument('--alpha', type=float, default=None,
                        help='势能宽度参数 (Morse)')
    parser.add_argument('--r0', type=float, default=None,
                        help='平衡键长 (Morse)')
    parser.add_argument('--k-coulomb', type=float, default=None,
                        help='Coulomb常数')
    
    parser.add_argument('--thermostat', action='store_true',
                        help='启用恒温器')
    parser.add_argument('--thermostat-type', type=str, default='berendsen',
                        choices=['berendsen'],
                        help='恒温器类型')
    parser.add_argument('--tau', type=float, default=None,
                        help='Berendsen耦合时间常数')
    parser.add_argument('--target-temp', type=float, default=None,
                        help='恒温器目标温度')
    
    parser.add_argument('--save-trajectory', action='store_true',
                        help='保存轨迹数据')
    parser.add_argument('--trajectory-file', type=str, default=None,
                        help='轨迹输出文件名 (XYZ格式)')
    parser.add_argument('--include-velocities', action='store_true',
                        help='轨迹中包含速度')
    parser.add_argument('--include-forces', action='store_true',
                        help='轨迹中包含力')
    parser.add_argument('--element', type=str, default='Ar',
                        help='元素符号 (用于XYZ轨迹)')
    
    parser.add_argument('--output-file', type=str, default=None,
                        help='能量历史输出文件 (JSON)')
    parser.add_argument('--quiet', action='store_true',
                        help='静默模式')
    
    return parser.parse_args()


def main():
    args = parse_args()
    
    if args.example_config:
        create_example_config(args.example_config)
        return
    
    config = load_config(args.config) if args.config else None
    
    if config:
        system_cfg = config['system']
        sim_cfg = config['simulation']
        pot_cfg = config['potential']
        thermo_cfg = config['thermostat']
        output_cfg = config['output']
        comp_cfg = config['computing']
        
        n_particles = args.n_particles or system_cfg['n_particles']
        temperature = args.temperature or system_cfg['temperature']
        density = args.density or system_cfg['density']
        dt = args.timestep or sim_cfg['dt']
        n_steps = args.steps or sim_cfg['n_steps']
        output_interval = args.output_interval or sim_cfg['output_interval']
        seed = args.seed or sim_cfg['seed']
        
        potential_type = args.potential or pot_cfg['type']
        r_cut = args.r_cut or pot_cfg['r_cut']
        r_skin = args.r_skin or pot_cfg['r_skin']
        dim = args.dim or system_cfg['dim']
        
        use_gpu = args.gpu or comp_cfg['use_gpu']
        
        thermostat_enabled = args.thermostat or thermo_cfg['enabled']
        thermostat_type = args.thermostat_type
        tau = args.tau or thermo_cfg['tau']
        target_temperature = args.target_temp or thermo_cfg['target_temperature']
        
        save_traj = args.save_trajectory or output_cfg['save_trajectory']
        trajectory_file = args.trajectory_file or output_cfg['trajectory_file']
        include_velocities = args.include_velocities or output_cfg['include_velocities']
        include_forces = args.include_forces or output_cfg['include_forces']
        element = args.element or output_cfg['element']
        
        output_file = args.output_file or output_cfg['energy_file']
    else:
        n_particles = args.n_particles or 108
        temperature = args.temperature or 1.0
        density = args.density or 0.8
        dt = args.timestep or 0.001
        n_steps = args.steps or 10000
        output_interval = args.output_interval or 100
        seed = args.seed
        
        potential_type = args.potential or 'lj'
        r_cut = args.r_cut or 2.5
        r_skin = args.r_skin or 0.3
        dim = args.dim or 3
        
        use_gpu = args.gpu
        
        thermostat_enabled = args.thermostat
        thermostat_type = args.thermostat_type
        tau = args.tau or 0.1
        target_temperature = args.target_temp or temperature
        
        save_traj = args.save_trajectory
        trajectory_file = args.trajectory_file or 'trajectory.xyz'
        include_velocities = args.include_velocities
        include_forces = args.include_forces
        element = args.element
        
        output_file = args.output_file
    
    potential_config = {
        'type': potential_type,
        'r_cut': r_cut
    }
    if args.epsilon is not None:
        potential_config['epsilon'] = args.epsilon
    if args.sigma is not None:
        potential_config['sigma'] = args.sigma
    if args.alpha is not None:
        potential_config['alpha'] = args.alpha
    if args.r0 is not None:
        potential_config['r0'] = args.r0
    if args.k_coulomb is not None:
        potential_config['k_coulomb'] = args.k_coulomb
    
    md = MolecularDynamics(
        n_particles=n_particles,
        temperature=temperature,
        density=density,
        dt=dt,
        n_steps=n_steps,
        r_cut=r_cut,
        r_skin=r_skin,
        dim=dim,
        use_gpu=use_gpu,
        seed=seed,
        potential_type=potential_type,
        potential_config=potential_config,
        thermostat_enabled=thermostat_enabled,
        thermostat_type=thermostat_type,
        thermostat_tau=tau,
        target_temperature=target_temperature
    )
    
    energy_history = md.run(
        output_interval=output_interval,
        save_trajectory=save_traj,
        trajectory_file=trajectory_file,
        include_velocities=include_velocities,
        include_forces=include_forces,
        element=element,
        verbose=not args.quiet
    )
    
    if output_file:
        save_energy_history(energy_history, output_file)
    
    return md


def save_energy_history(energy_history, filename):
    """保存能量历史到JSON文件"""
    data = {
        'description': 'Molecular Dynamics Simulation Energy History',
        'columns': ['step', 'kinetic_energy', 'potential_energy', 'total_energy', 'temperature'],
        'data': energy_history
    }
    
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    if not os.environ.get('QUIET_MODE'):
        print(f"\n能量历史已保存到: {filename}")


if __name__ == '__main__':
    main()
