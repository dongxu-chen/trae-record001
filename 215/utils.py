import importlib.util

if importlib.util.find_spec("cupy") is not None:
    import cupy as np
    GPU_AVAILABLE = True
else:
    import numpy as np
    GPU_AVAILABLE = False


def pbc_wrap(positions, box_length):
    """
    应用周期性边界条件，使用最近镜像法将位置限制在盒子内
    
    算法: 对于每个分量 x:
        wrapped_x = x - box_length * round(x / box_length)
    
    这确保粒子总是被映射到最近的镜像位置
    
    参数:
        positions: 粒子位置 (N, dim)
        box_length: 盒子边长
    
    返回:
        包装后的位置，范围 [-box_length/2, box_length/2] 或 [0, box_length]
    """
    return positions - box_length * np.round(positions / box_length)


def pbc_wrap_to_positive(positions, box_length):
    """
    应用周期性边界条件，将位置限制在 [0, box_length) 范围内
    
    参数:
        positions: 粒子位置 (N, dim)
        box_length: 盒子边长
    
    返回:
        包装后的位置，范围 [0, box_length)
    """
    wrapped = pbc_wrap(positions, box_length)
    return wrapped + box_length * (wrapped < 0).astype(wrapped.dtype)


def pbc_distance(dr, box_length):
    """
    计算PBC下的最小距离矢量
    
    参数:
        dr: 位移矢量
        box_length: 盒子边长
    
    返回:
        最小距离矢量
    """
    return dr - box_length * np.round(dr / box_length)


def initialize_fcc(n_particles, box_length, dim=3):
    """
    面心立方(FCC)晶格初始化
    
    参数:
        n_particles: 粒子数
        box_length: 盒子边长
        dim: 维度 (默认3维)
    
    返回:
        初始化的位置 (N, dim)
    """
    n_per_side = int(round((n_particles / 4) ** (1/3))) if dim == 3 else int(round(np.sqrt(n_particles / 2)))
    
    if dim == 3:
        if 4 * n_per_side ** 3 < n_particles:
            n_per_side += 1
    else:
        if 2 * n_per_side ** 2 < n_particles:
            n_per_side += 1
    
    a = box_length / n_per_side
    
    if dim == 3:
        basis = np.array([[0, 0, 0], [0.5, 0.5, 0], [0.5, 0, 0.5], [0, 0.5, 0.5]])
        positions = []
        for i in range(n_per_side):
            for j in range(n_per_side):
                for k in range(n_per_side):
                    for base in basis:
                        pos = np.array([i, j, k]) + base
                        positions.append(pos * a)
    else:
        basis = np.array([[0, 0], [0.5, 0.5]])
        positions = []
        for i in range(n_per_side):
            for j in range(n_per_side):
                for base in basis:
                    pos = np.array([i, j]) + base
                    positions.append(pos * a)
    
    positions = np.array(positions[:n_particles])
    return positions


def initialize_random(n_particles, box_length, dim=3, seed=None):
    """
    随机初始化位置
    
    参数:
        n_particles: 粒子数
        box_length: 盒子边长
        dim: 维度
        seed: 随机种子
    
    返回:
        初始化的位置
    """
    if seed is not None:
        np.random.seed(seed)
    return np.random.uniform(0, box_length, (n_particles, dim))


def initialize_velocities(n_particles, temperature, dim=3, seed=None, use_gpu=False):
    """
    按Maxwell-Boltzmann分布初始化速度
    
    参数:
        n_particles: 粒子数
        temperature: 温度
        dim: 维度
        seed: 随机种子
        use_gpu: 是否使用GPU
    
    返回:
        初始化的速度
    """
    if seed is not None:
        if use_gpu and GPU_AVAILABLE:
            np.random.seed(seed)
        else:
            if GPU_AVAILABLE:
                import numpy as np_cpu
                np_cpu.random.seed(seed)
                velocities = np_cpu.random.normal(0, np.sqrt(temperature), (n_particles, dim))
                velocities = np.array(velocities)
                return velocities
            else:
                np.random.seed(seed)
    
    velocities = np.random.normal(0, np.sqrt(temperature), (n_particles, dim))
    velocities = remove_center_of_mass(velocities)
    velocities = rescale_velocities(velocities, temperature)
    
    return velocities


def remove_center_of_mass(velocities):
    """
    移除质心速度
    
    参数:
        velocities: 速度 (N, dim)
    
    返回:
        去除质心后的速度
    """
    com_velocity = np.mean(velocities, axis=0)
    return velocities - com_velocity


def rescale_velocities(velocities, target_temperature):
    """
    重新缩放速度以达到目标温度
    
    参数:
        velocities: 速度 (N, dim)
        target_temperature: 目标温度
    
    返回:
        缩放后的速度
    """
    current_temp = calculate_temperature(velocities)
    if current_temp > 0:
        scale = np.sqrt(target_temperature / current_temp)
        return velocities * scale
    return velocities


def calculate_kinetic_energy(velocities, mass=1.0):
    """
    计算动能
    
    参数:
        velocities: 速度 (N, dim)
        mass: 粒子质量
    
    返回:
        总动能
    """
    return 0.5 * mass * np.sum(velocities ** 2)


def calculate_temperature(velocities, mass=1.0):
    """
    计算温度 (基于动能均分定理)
    
    参数:
        velocities: 速度 (N, dim)
        mass: 粒子质量
    
    返回:
        温度
    """
    n_particles = velocities.shape[0]
    dim = velocities.shape[1]
    dof = dim * n_particles - dim  # 减去质心自由度
    kinetic_energy = calculate_kinetic_energy(velocities, mass)
    return 2.0 * kinetic_energy / dof


def calculate_pressure(positions, forces, box_length, temperature):
    """
    计算压强 (基于virial定理)
    
    参数:
        positions: 位置 (N, dim)
        forces: 力 (N, dim)
        box_length: 盒子边长
        temperature: 温度
    
    返回:
        压强
    """
    n_particles = positions.shape[0]
    volume = box_length ** positions.shape[1]
    
    virial = np.sum(positions * forces)
    pressure = (n_particles * temperature + virial / positions.shape[1]) / volume
    
    return pressure


def apply_pbc(positions, box_length):
    """
    应用周期性边界条件 (别名函数)
    """
    return pbc_wrap(positions, box_length)


def minimum_image_distance(dr, box_length):
    """
    最小镜像距离 (别名函数)
    """
    return pbc_distance(dr, box_length)


def get_box_length(n_particles, density, dim=3):
    """
    根据粒子数和密度计算盒子边长
    
    参数:
        n_particles: 粒子数
        density: 数密度
        dim: 维度
    
    返回:
        盒子边长
    """
    volume = n_particles / density
    return volume ** (1.0 / dim)


def get_array_module(array):
    """
    获取数组所在的模块 (numpy或cupy)
    """
    if hasattr(array, '__module__') and 'cupy' in array.__module__:
        return np
    else:
        import numpy
        return numpy


def to_cpu(array):
    """
    将数组转换到CPU
    """
    if GPU_AVAILABLE and hasattr(array, 'get'):
        return array.get()
    return array


def to_gpu(array):
    """
    将数组转换到GPU
    """
    if GPU_AVAILABLE:
        return np.array(array)
    return array
