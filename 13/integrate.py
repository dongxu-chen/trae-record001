import numpy as np

try:
    import cupy as cp
    CUPY_AVAILABLE = True
except ImportError:
    CUPY_AVAILABLE = False
    import numpy as cp

from cuda_utils import get_array_module, synchronize, to_cpu


def velocity_verlet_step(positions, velocities, forces, box, masses, dt, force_func):
    """
    执行一步 Velocity Verlet 积分

    Velocity Verlet 算法:
    1. r(t + dt) = r(t) + v(t) * dt + f(t) * dt^2 / (2 * m)
    2. f(t + dt) = 更新力
    3. v(t + dt) = v(t) + (f(t) + f(t + dt)) * dt / (2 * m)

    自动检测 CPU/GPU

    Args:
        positions: 当前位置 (Nx3)
        velocities: 当前速度 (Nx3)
        forces: 当前受力 (Nx3)
        box: 模拟盒子
        masses: 每个粒子的质量 (N,)
        dt: 时间步长
        force_func: 力计算函数

    Returns:
        positions_new: 更新后的位置
        velocities_new: 更新后的速度
        forces_new: 更新后的力
        potential_new: 新的势能
    """
    xp = get_array_module(positions)
    dt2 = dt * dt
    n = positions.shape[0]
    box_size = xp.asarray(box[:, 1] - box[:, 0], dtype=xp.float64)
    box_min = xp.asarray(box[:, 0], dtype=xp.float64)

    positions_new = positions + velocities * dt
    masses_arr = xp.asarray(masses) if isinstance(masses, np.ndarray) else masses
    if len(masses_arr.shape) == 1:
        masses_broadcast = masses_arr[:, xp.newaxis]
    else:
        masses_broadcast = masses_arr
    positions_new = positions_new + forces * dt2 / (2.0 * masses_broadcast)

    positions_new = box_min + (positions_new - box_min) % box_size

    forces_new, potential_new = force_func(positions_new)

    velocities_new = velocities.copy()
    velocities_new = velocities_new + (forces + forces_new) * dt / (2.0 * masses_broadcast)

    if xp is cp:
        synchronize()

    return positions_new, velocities_new, forces_new, potential_new


def compute_kinetic_energy(velocities, masses):
    """
    计算系统动能

    支持 CPU/GPU

    Args:
        velocities: 粒子速度 (Nx3)
        masses: 粒子质量 (N,)

    Returns:
        float: 总动能
    """
    xp = get_array_module(velocities)

    if isinstance(masses, np.ndarray) and xp is cp:
        masses = xp.asarray(masses)

    masses_2d = masses[:, xp.newaxis] if len(masses.shape) == 1 else masses

    ke = 0.5 * xp.sum(masses_2d * velocities * velocities)

    if xp is cp:
        synchronize()
        ke = float(ke)

    return float(ke)


def compute_temperature(kinetic_energy, n_particles):
    """
    根据动能计算温度（自由度假设为 3N-3，简化为 3N）

    Args:
        kinetic_energy (float): 动能
        n_particles (int): 粒子数

    Returns:
        float: 温度
    """
    k_b = 1.0
    return 2.0 * kinetic_energy / (3.0 * n_particles * k_b)


def velocity_rescale(velocities, masses, target_temperature):
    """
    速度重标度（简单温度控制），保持系统总动量为零

    为防止动量漂移：
    1. 先计算并去除质心速度
    2. 对热运动速度进行标度
    3. 保持质心速度为零

    支持 CPU/GPU

    Args:
        velocities: 当前速度
        masses: 粒子质量
        target_temperature: 目标温度

    Returns:
        重标度后的速度
    """
    xp = get_array_module(velocities)

    if isinstance(masses, np.ndarray) and xp is cp:
        masses = xp.asarray(masses)

    if xp is cp:
        return _velocity_rescale_gpu(velocities, masses, target_temperature)
    else:
        return _velocity_rescale_cpu(velocities, masses, target_temperature)


def _velocity_rescale_cpu(velocities, masses, target_temperature):
    """CPU 版本速度重标度"""
    n = len(masses)
    total_mass = np.sum(masses)

    v_cm = np.sum(masses[:, np.newaxis] * velocities, axis=0) / total_mass
    v_thermal = velocities - v_cm

    ke_thermal = 0.0
    for i in range(n):
        v2 = np.dot(v_thermal[i], v_thermal[i])
        ke_thermal += 0.5 * masses[i] * v2

    current_temp = 2.0 * ke_thermal / (3.0 * n)

    if current_temp > 0:
        scale = np.sqrt(target_temperature / current_temp)
        return v_thermal * scale
    return v_thermal


def _velocity_rescale_gpu(velocities, masses, target_temperature):
    """GPU 版本速度重标度"""
    n = velocities.shape[0]
    total_mass = cp.sum(masses)

    v_cm = cp.sum(masses[:, cp.newaxis] * velocities, axis=0) / total_mass
    v_thermal = velocities - v_cm

    masses_2d = masses[:, cp.newaxis]
    ke_thermal = 0.5 * cp.sum(masses_2d * v_thermal * v_thermal)

    current_temp = 2.0 * ke_thermal / (3.0 * n)
    current_temp_scalar = float(current_temp)

    if current_temp_scalar > 0:
        scale = cp.sqrt(target_temperature / current_temp)
        result = v_thermal * scale
        synchronize()
        return result

    synchronize()
    return v_thermal
