import importlib.util

if importlib.util.find_spec("cupy") is not None:
    import cupy as np
    GPU_AVAILABLE = True
else:
    import numpy as np
    GPU_AVAILABLE = False


POTENTIAL_TYPES = ['lj', 'morse', 'coulomb']


def get_potential_config(potential_type='lj', **kwargs):
    """
    获取势函数配置
    
    参数:
        potential_type: 势函数类型 ('lj', 'morse', 'coulomb')
        **kwargs: 势函数参数
    
    返回:
        config: 势函数参数字典
    """
    default_configs = {
        'lj': {'epsilon': 1.0, 'sigma': 1.0, 'r_cut': 2.5},
        'morse': {'epsilon': 1.0, 'alpha': 12.0, 'r0': 1.0, 'r_cut': 2.5},
        'coulomb': {'k_coulomb': 1.0, 'r_cut': 2.5}
    }
    
    config = default_configs.get(potential_type, default_configs['lj']).copy()
    config.update(kwargs)
    config['type'] = potential_type
    
    return config


def lennard_jones_potential(r2, epsilon=1.0, sigma=1.0, r_cut=2.5):
    """
    计算Lennard-Jones势能
    
    参数:
        r2: 粒子间距离的平方
        epsilon: 势阱深度 (默认1.0, 约化单位)
        sigma: 粒子直径 (默认1.0, 约化单位)
        r_cut: 截断半径 (单位: sigma)
    
    返回:
        势能值
    """
    r_cut2 = r_cut ** 2
    mask = r2 < r_cut2
    
    if GPU_AVAILABLE and isinstance(r2, np.ndarray):
        result = np.zeros_like(r2)
    else:
        result = np.zeros(np.shape(r2))
    
    if np.any(mask):
        sr2 = (sigma ** 2) / r2[mask]
        sr6 = sr2 ** 3
        sr12 = sr6 ** 2
        result[mask] = 4.0 * epsilon * (sr12 - sr6)
    
    return result


def lennard_jones_force(r, r2, epsilon=1.0, sigma=1.0, r_cut=2.5):
    """
    计算Lennard-Jones力的大小 (沿连线方向)
    
    参数:
        r: 粒子间距离
        r2: 粒子间距离的平方
        epsilon: 势阱深度
        sigma: 粒子直径
        r_cut: 截断半径
    
    返回:
        力的大小 (F = -dV/dr)
    """
    r_cut2 = r_cut ** 2
    mask = r2 < r_cut2
    
    if GPU_AVAILABLE and isinstance(r2, np.ndarray):
        force = np.zeros_like(r2)
    else:
        force = np.zeros(np.shape(r2))
    
    if np.any(mask):
        sr2 = (sigma ** 2) / r2[mask]
        sr6 = sr2 ** 3
        sr12 = sr6 ** 2
        force[mask] = 24.0 * epsilon / r[mask] * (2.0 * sr12 - sr6)
    
    return force


def lennard_jones_force_vector(dr, r2, epsilon=1.0, sigma=1.0, r_cut=2.5):
    """
    计算Lennard-Jones力矢量
    
    参数:
        dr: 相对位移矢量 (N, dim)
        r2: 相对距离的平方 (N,)
        epsilon: 势阱深度
        sigma: 粒子直径
        r_cut: 截断半径
    
    返回:
        力矢量 (N, dim)
    """
    r_cut2 = r_cut ** 2
    mask = r2 < r_cut2
    
    dim = dr.shape[1] if len(dr.shape) > 1 else 1
    
    if GPU_AVAILABLE and isinstance(dr, np.ndarray):
        force_vectors = np.zeros_like(dr)
    else:
        force_vectors = np.zeros(np.shape(dr))
    
    if np.any(mask):
        r = np.sqrt(r2[mask])
        sr2 = (sigma ** 2) / r2[mask]
        sr6 = sr2 ** 3
        sr12 = sr6 ** 2
        f_mag = 24.0 * epsilon / r * (2.0 * sr12 - sr6)
        f_mag = f_mag.reshape(-1, 1)
        force_vectors[mask] = f_mag * dr[mask] / r.reshape(-1, 1)
    
    return force_vectors


def tail_correction(r_cut=2.5, rho=0.0):
    """
    势能的长程修正
    
    参数:
        r_cut: 截断半径
        rho: 数密度
    
    返回:
        每个粒子的修正势能
    """
    sr3 = (1.0 / r_cut) ** 3
    sr9 = sr3 ** 3
    return (8.0 / 3.0) * np.pi * rho * (sr9 / 3.0 - sr3)


def pressure_tail_correction(r_cut=2.5, rho=0.0):
    """
    压强的长程修正
    
    参数:
        r_cut: 截断半径
        rho: 数密度
    
    返回:
        压强修正值
    """
    sr3 = (1.0 / r_cut) ** 3
    sr9 = sr3 ** 3
    return (16.0 / 3.0) * np.pi * rho ** 2 * (2.0 * sr9 / 3.0 - sr3)


def morse_potential(r2, epsilon=1.0, alpha=12.0, r0=1.0, r_cut=2.5):
    """
    计算Morse势能
    
    V(r) = epsilon * [exp(-2*alpha*(r-r0)) - 2*exp(-alpha*(r-r0))]
    
    参数:
        r2: 粒子间距离的平方
        epsilon: 势阱深度
        alpha: 势能宽度参数
        r0: 平衡键长
        r_cut: 截断半径
    
    返回:
        势能值
    """
    r_cut2 = r_cut ** 2
    mask = r2 < r_cut2
    
    if GPU_AVAILABLE and isinstance(r2, np.ndarray):
        result = np.zeros_like(r2)
    else:
        result = np.zeros(np.shape(r2))
    
    if np.any(mask):
        r = np.sqrt(r2[mask])
        dr = r - r0
        exp_term = np.exp(-alpha * dr)
        result[mask] = epsilon * (exp_term ** 2 - 2.0 * exp_term)
    
    return result


def morse_force(r, r2, epsilon=1.0, alpha=12.0, r0=1.0, r_cut=2.5):
    """
    计算Morse力的大小 (沿连线方向)
    
    F(r) = -dV/dr = 2*epsilon*alpha * [exp(-2*alpha*(r-r0)) - exp(-alpha*(r-r0))]
    
    参数:
        r: 粒子间距离
        r2: 粒子间距离的平方
        epsilon: 势阱深度
        alpha: 势能宽度参数
        r0: 平衡键长
        r_cut: 截断半径
    
    返回:
        力的大小
    """
    r_cut2 = r_cut ** 2
    mask = r2 < r_cut2
    
    if GPU_AVAILABLE and isinstance(r2, np.ndarray):
        force = np.zeros_like(r2)
    else:
        force = np.zeros(np.shape(r2))
    
    if np.any(mask):
        r_masked = r[mask]
        dr = r_masked - r0
        exp_term = np.exp(-alpha * dr)
        force[mask] = 2.0 * epsilon * alpha * (exp_term ** 2 - exp_term)
    
    return force


def morse_force_vector(dr, r2, epsilon=1.0, alpha=12.0, r0=1.0, r_cut=2.5):
    """
    计算Morse力矢量
    
    参数:
        dr: 相对位移矢量 (N, dim)
        r2: 相对距离的平方 (N,)
        epsilon: 势阱深度
        alpha: 势能宽度参数
        r0: 平衡键长
        r_cut: 截断半径
    
    返回:
        力矢量 (N, dim)
    """
    r_cut2 = r_cut ** 2
    mask = r2 < r_cut2
    
    if GPU_AVAILABLE and isinstance(dr, np.ndarray):
        force_vectors = np.zeros_like(dr)
    else:
        force_vectors = np.zeros(np.shape(dr))
    
    if np.any(mask):
        r = np.sqrt(r2[mask])
        dr_masked = dr[mask]
        exp_term = np.exp(-alpha * (r - r0))
        f_mag = 2.0 * epsilon * alpha * (exp_term ** 2 - exp_term)
        f_mag = f_mag.reshape(-1, 1)
        force_vectors[mask] = f_mag * dr_masked / r.reshape(-1, 1)
    
    return force_vectors


def coulomb_potential(r2, k_coulomb=1.0, r_cut=2.5):
    """
    计算Coulomb势能
    
    V(r) = k_coulomb * q1 * q2 / r
    注意: 电荷乘积需在外部计算，此处假设单位电荷
    
    参数:
        r2: 粒子间距离的平方
        k_coulomb: Coulomb常数 (约化单位)
        r_cut: 截断半径
    
    返回:
        势能值
    """
    r_cut2 = r_cut ** 2
    mask = r2 < r_cut2
    
    if GPU_AVAILABLE and isinstance(r2, np.ndarray):
        result = np.zeros_like(r2)
    else:
        result = np.zeros(np.shape(r2))
    
    if np.any(mask):
        r = np.sqrt(r2[mask])
        result[mask] = k_coulomb / r
    
    return result


def coulomb_force(r, r2, k_coulomb=1.0, r_cut=2.5):
    """
    计算Coulomb力的大小 (沿连线方向)
    
    F(r) = -dV/dr = k_coulomb / r^2
    
    参数:
        r: 粒子间距离
        r2: 粒子间距离的平方
        k_coulomb: Coulomb常数
        r_cut: 截断半径
    
    返回:
        力的大小
    """
    r_cut2 = r_cut ** 2
    mask = r2 < r_cut2
    
    if GPU_AVAILABLE and isinstance(r2, np.ndarray):
        force = np.zeros_like(r2)
    else:
        force = np.zeros(np.shape(r2))
    
    if np.any(mask):
        force[mask] = k_coulomb / r2[mask]
    
    return force


def coulomb_force_vector(dr, r2, k_coulomb=1.0, r_cut=2.5):
    """
    计算Coulomb力矢量
    
    参数:
        dr: 相对位移矢量 (N, dim)
        r2: 相对距离的平方 (N,)
        k_coulomb: Coulomb常数
        r_cut: 截断半径
    
    返回:
        力矢量 (N, dim)
    """
    r_cut2 = r_cut ** 2
    mask = r2 < r_cut2
    
    if GPU_AVAILABLE and isinstance(dr, np.ndarray):
        force_vectors = np.zeros_like(dr)
    else:
        force_vectors = np.zeros(np.shape(dr))
    
    if np.any(mask):
        r = np.sqrt(r2[mask])
        dr_masked = dr[mask]
        f_mag = k_coulomb / r2[mask]
        f_mag = f_mag.reshape(-1, 1)
        force_vectors[mask] = f_mag * dr_masked / r.reshape(-1, 1)
    
    return force_vectors


def compute_potential_energy(r2, potential_config):
    """
    根据配置计算势能 (统一接口)
    
    参数:
        r2: 粒子间距离的平方
        potential_config: 势函数配置字典
    
    返回:
        势能值
    """
    ptype = potential_config.get('type', 'lj')
    
    if ptype == 'lj':
        return lennard_jones_potential(
            r2, 
            epsilon=potential_config.get('epsilon', 1.0),
            sigma=potential_config.get('sigma', 1.0),
            r_cut=potential_config.get('r_cut', 2.5)
        )
    elif ptype == 'morse':
        return morse_potential(
            r2,
            epsilon=potential_config.get('epsilon', 1.0),
            alpha=potential_config.get('alpha', 12.0),
            r0=potential_config.get('r0', 1.0),
            r_cut=potential_config.get('r_cut', 2.5)
        )
    elif ptype == 'coulomb':
        return coulomb_potential(
            r2,
            k_coulomb=potential_config.get('k_coulomb', 1.0),
            r_cut=potential_config.get('r_cut', 2.5)
        )
    else:
        return lennard_jones_potential(r2)


def compute_force_vector(dr, r2, potential_config):
    """
    根据配置计算力矢量 (统一接口)
    
    参数:
        dr: 相对位移矢量
        r2: 相对距离的平方
        potential_config: 势函数配置字典
    
    返回:
        力矢量
    """
    ptype = potential_config.get('type', 'lj')
    
    if ptype == 'lj':
        return lennard_jones_force_vector(
            dr, r2,
            epsilon=potential_config.get('epsilon', 1.0),
            sigma=potential_config.get('sigma', 1.0),
            r_cut=potential_config.get('r_cut', 2.5)
        )
    elif ptype == 'morse':
        return morse_force_vector(
            dr, r2,
            epsilon=potential_config.get('epsilon', 1.0),
            alpha=potential_config.get('alpha', 12.0),
            r0=potential_config.get('r0', 1.0),
            r_cut=potential_config.get('r_cut', 2.5)
        )
    elif ptype == 'coulomb':
        return coulomb_force_vector(
            dr, r2,
            k_coulomb=potential_config.get('k_coulomb', 1.0),
            r_cut=potential_config.get('r_cut', 2.5)
        )
    else:
        return lennard_jones_force_vector(dr, r2)
