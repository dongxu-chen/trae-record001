import json
import os


DEFAULT_CONFIG = {
    'system': {
        'n_particles': 108,
        'temperature': 1.0,
        'density': 0.8,
        'dim': 3,
        'mass': 1.0
    },
    'simulation': {
        'dt': 0.001,
        'n_steps': 10000,
        'output_interval': 100,
        'seed': None
    },
    'potential': {
        'type': 'lj',
        'epsilon': 1.0,
        'sigma': 1.0,
        'alpha': 12.0,
        'r0': 1.0,
        'k_coulomb': 1.0,
        'r_cut': 2.5,
        'r_skin': 0.3
    },
    'thermostat': {
        'enabled': False,
        'type': 'berendsen',
        'tau': 0.1,
        'target_temperature': 1.0
    },
    'output': {
        'energy_file': 'energy_history.json',
        'trajectory_file': 'trajectory.xyz',
        'save_trajectory': True,
        'trajectory_format': 'xyz',
        'include_velocities': True,
        'include_forces': False,
        'element': 'Ar'
    },
    'computing': {
        'use_gpu': False,
        'use_neighbor_list': True
    }
}


def load_config(config_path=None):
    """
    加载配置文件
    
    支持JSON和YAML格式
    
    参数:
        config_path: 配置文件路径
    
    返回:
        config: 配置字典
    """
    if config_path is None:
        return DEFAULT_CONFIG.copy()
    
    if not os.path.exists(config_path):
        print(f'警告: 配置文件 {config_path} 不存在，使用默认配置')
        return DEFAULT_CONFIG.copy()
    
    with open(config_path, 'r', encoding='utf-8') as f:
        if config_path.endswith('.yaml') or config_path.endswith('.yml'):
            try:
                import yaml
                config = yaml.safe_load(f)
            except ImportError:
                print('警告: 未安装PyYAML，尝试用JSON解析')
                f.seek(0)
                config = json.load(f)
        else:
            config = json.load(f)
    
    merged_config = merge_config(DEFAULT_CONFIG.copy(), config)
    
    return merged_config


def merge_config(default, override):
    """
    递归合并配置
    
    参数:
        default: 默认配置
        override: 覆盖配置
    
    返回:
        合并后的配置
    """
    result = default.copy()
    
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = merge_config(result[key], value)
        else:
            result[key] = value
    
    return result


def save_config(config, output_path):
    """
    保存配置到文件
    
    参数:
        config: 配置字典
        output_path: 输出文件路径
    """
    with open(output_path, 'w', encoding='utf-8') as f:
        if output_path.endswith('.yaml') or output_path.endswith('.yml'):
            try:
                import yaml
                yaml.dump(config, f, default_flow_style=False, allow_unicode=True)
            except ImportError:
                json.dump(config, f, indent=2, ensure_ascii=False)
        else:
            json.dump(config, f, indent=2, ensure_ascii=False)


def create_example_config(output_path='config.json'):
    """
    创建示例配置文件
    
    参数:
        output_path: 输出路径
    """
    config = {
        'system': {
            'n_particles': 256,
            'temperature': 1.0,
            'density': 0.8,
            'dim': 3
        },
        'simulation': {
            'dt': 0.001,
            'n_steps': 50000,
            'output_interval': 100,
            'seed': 42
        },
        'potential': {
            'type': 'lj',
            'epsilon': 1.0,
            'sigma': 1.0,
            'r_cut': 2.5,
            'r_skin': 0.3
        },
        'thermostat': {
            'enabled': True,
            'type': 'berendsen',
            'tau': 0.5,
            'target_temperature': 1.0
        },
        'output': {
            'energy_file': 'md_energy.json',
            'trajectory_file': 'md_traj.xyz',
            'save_trajectory': True,
            'element': 'Ar'
        }
    }
    
    save_config(config, output_path)
    print(f'示例配置已保存到: {output_path}')


def print_config(config, indent=0):
    """
    打印配置
    
    参数:
        config: 配置字典
        indent: 缩进
    """
    prefix = '  ' * indent
    for key, value in config.items():
        if isinstance(value, dict):
            print(f'{prefix}{key}:')
            print_config(value, indent + 1)
        else:
            print(f'{prefix}{key}: {value}')


def get_md_params(config):
    """
    从配置中提取MD模拟参数
    
    参数:
        config: 配置字典
    
    返回:
        md_params: MolecularDynamics构造参数
    """
    return {
        'n_particles': config['system']['n_particles'],
        'temperature': config['system']['temperature'],
        'density': config['system']['density'],
        'dt': config['simulation']['dt'],
        'n_steps': config['simulation']['n_steps'],
        'r_cut': config['potential']['r_cut'],
        'r_skin': config['potential']['r_skin'],
        'dim': config['system']['dim'],
        'use_gpu': config['computing']['use_gpu'],
        'seed': config['simulation']['seed']
    }


def get_potential_config(config):
    """
    从配置中提取势函数参数
    
    参数:
        config: 配置字典
    
    返回:
        potential_config: 势函数配置字典
    """
    pconfig = config['potential'].copy()
    return pconfig


def get_thermostat_config(config):
    """
    从配置中提取恒温器参数
    
    参数:
        config: 配置字典
    
    返回:
        thermostat_config: 恒温器配置字典
    """
    return config['thermostat'].copy()


if __name__ == '__main__':
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == '--example':
        output = sys.argv[2] if len(sys.argv) > 2 else 'config.json'
        create_example_config(output)
    else:
        print('默认配置:')
        print('=' * 60)
        print_config(DEFAULT_CONFIG)
        print('=' * 60)
        print('\n使用 --example [filename] 生成示例配置文件')
