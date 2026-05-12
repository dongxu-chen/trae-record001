import numpy as np

try:
    import cupy as cp
    CUPY_AVAILABLE = True
except ImportError:
    CUPY_AVAILABLE = False
    import numpy as cp

from cuda_utils import get_array_module, synchronize


def minimum_image(r_vec, box_size):
    """
    计算最小镜像距离矢量

    采用正确的最小镜像约定：将位移矢量映射到 [-L/2, L/2) 范围

    Args:
        r_vec (np.ndarray): 原始位移矢量
        box_size (np.ndarray): 盒子大小

    Returns:
        np.ndarray: 最小镜像位移矢量
    """
    xp = get_array_module(r_vec)
    return r_vec - box_size * xp.round(r_vec / box_size)


def lj_potential(r2, sigma=1.0, epsilon=1.0, rc=2.5):
    """
    计算 Lennard-Jones 势能

    Args:
        r2 (float): 粒子间距离的平方
        sigma (float): LJ 作用参数 σ
        epsilon (float): LJ 作用参数 ε
        rc (float): 截断距离 (单位: σ)

    Returns:
        float: 势能值
    """
    xp = get_array_module(r2) if hasattr(r2, '__module__') else np
    rc2 = rc * rc

    sr2 = (sigma * sigma) / r2
    sr6 = sr2 * sr2 * sr2
    sr12 = sr6 * sr6
    u = 4.0 * epsilon * (sr12 - sr6)

    rc_sr2 = (sigma * sigma) / rc2
    rc_sr6 = rc_sr2 * rc_sr2 * rc_sr2
    rc_sr12 = rc_sr6 * rc_sr6
    u_correction = 4.0 * epsilon * (rc_sr12 - rc_sr6)

    return u - u_correction


def lj_force(r_vec, r2, sigma=1.0, epsilon=1.0, rc=2.5):
    """
    计算 Lennard-Jones 作用力

    Args:
        r_vec (np.ndarray): 粒子间位移矢量
        r2 (float): 粒子间距离的平方
        sigma (float): LJ 作用参数 σ
        epsilon (float): LJ 作用参数 ε
        rc (float): 截断距离

    Returns:
        np.ndarray: 作用力矢量
    """
    xp = get_array_module(r_vec)

    sr2 = (sigma * sigma) / r2
    sr6 = sr2 * sr2 * sr2
    sr12 = sr6 * sr6

    f_scalar = 24.0 * epsilon * (2.0 * sr12 - sr6) / r2
    return f_scalar * r_vec


def compute_forces_naive(positions, box, sigma=1.0, epsilon=1.0, rc=2.5):
    """
    朴素 O(N²) 方法计算所有粒子间的 LJ 力和势能

    自动检测是使用 NumPy 还是 CuPy

    Args:
        positions: 粒子位置 (Nx3)
        box: 模拟盒子 (3x2)
        sigma (float): LJ σ
        epsilon (float): LJ ε
        rc (float): 截断距离

    Returns:
        forces: 每个粒子受到的力
        potential: 总势能
    """
    xp = get_array_module(positions)
    n = positions.shape[0]
    forces = xp.zeros_like(positions)
    potential = xp.float64(0.0)
    box_size = xp.asarray(box[:, 1] - box[:, 0], dtype=xp.float64)

    rc2 = rc * rc
    sigma2 = sigma * sigma
    four_epsilon = 4.0 * epsilon
    twentyfour_epsilon = 24.0 * epsilon

    for i in range(n):
        for j in range(i + 1, n):
            r_vec = positions[i] - positions[j]
            r_vec -= box_size * xp.round(r_vec / box_size)
            r2 = xp.dot(r_vec, r_vec)

            if r2 > rc2:
                continue

            sr2 = sigma2 / r2
            sr6 = sr2 * sr2 * sr2
            sr12 = sr6 * sr6

            u = four_epsilon * (sr12 - sr6)
            potential += u

            f_scalar = twentyfour_epsilon * (2.0 * sr12 - sr6) / r2
            f_ij = f_scalar * r_vec
            forces[i] += f_ij
            forces[j] -= f_ij

    if xp is cp:
        synchronize()
        potential = float(potential)

    return forces, float(potential)


def compute_forces_gpu(positions, box, sigma=1.0, epsilon=1.0, rc=2.5):
    """
    GPU 优化的 LJ 力计算，使用向量化操作

    Args:
        positions (cp.ndarray): GPU 上的粒子位置 (Nx3)
        box: 模拟盒子
        sigma (float): LJ σ
        epsilon (float): LJ ε
        rc (float): 截断距离

    Returns:
        forces (cp.ndarray): 力
        potential (float): 势能
    """
    if not CUPY_AVAILABLE:
        raise RuntimeError("CuPy 未安装，无法使用 GPU 力计算")

    n = positions.shape[0]
    forces = cp.zeros((n, 3), dtype=cp.float64)
    potential = cp.float64(0.0)

    box_size = cp.asarray(box[:, 1] - box[:, 0], dtype=cp.float64)
    rc2 = rc * rc
    sigma2 = sigma * sigma
    four_epsilon = 4.0 * epsilon
    twentyfour_epsilon = 24.0 * epsilon

    for i in range(n):
        pos_i = positions[i]
        r_vec = positions[i + 1:] - pos_i
        r_vec = r_vec - box_size * cp.round(r_vec / box_size)
        r2 = cp.sum(r_vec * r_vec, axis=1)

        mask = r2 <= rc2
        if not cp.any(mask):
            continue

        r2_masked = r2[mask]
        r_vec_masked = r_vec[mask]

        sr2 = sigma2 / r2_masked
        sr6 = sr2 * sr2 * sr2
        sr12 = sr6 * sr6

        u = four_epsilon * (sr12 - sr6)
        potential += cp.sum(u)

        f_scalar = twentyfour_epsilon * (2.0 * sr12 - sr6) / r2_masked
        f_ij = f_scalar[:, cp.newaxis] * r_vec_masked

        forces[i] -= cp.sum(f_ij, axis=0)
        idx = cp.where(mask)[0] + (i + 1)
        for k, j in enumerate(idx):
            forces[j] += f_ij[k]

    synchronize()
    return forces, float(potential)


def compute_forces_neighbor(positions, neighbors, box, sigma=1.0, epsilon=1.0, rc=2.5):
    """
    使用邻居列表计算 LJ 力和势能

    自动检测 CPU/GPU

    Args:
        positions: 粒子位置
        neighbors: 邻居列表 (list for CPU, 或 索引对数组 for GPU)
        box: 模拟盒子
        sigma (float): LJ σ
        epsilon (float): LJ ε
        rc (float): 截断距离

    Returns:
        forces: 每个粒子受到的力
        potential: 总势能
    """
    xp = get_array_module(positions)
    n = positions.shape[0]
    box_size = xp.asarray(box[:, 1] - box[:, 0], dtype=xp.float64)

    forces = xp.zeros((n, 3), dtype=xp.float64)
    potential = xp.float64(0.0)

    rc2 = rc * rc
    sigma2 = sigma * sigma
    four_epsilon = 4.0 * epsilon
    twentyfour_epsilon = 24.0 * epsilon

    if xp is cp and CUPY_AVAILABLE:
        return _compute_forces_neighbor_gpu(positions, neighbors, box_size,
                                            sigma, epsilon, rc)
    else:
        return _compute_forces_neighbor_cpu(positions, neighbors, box_size,
                                            sigma, epsilon, rc)


def _compute_forces_neighbor_cpu(positions, neighbors, box_size, sigma, epsilon, rc):
    """CPU 版本邻居列表力计算"""
    n = positions.shape[0]
    forces = np.zeros((n, 3), dtype=np.float64)
    potential = 0.0

    rc2 = rc * rc
    sigma2 = sigma * sigma
    four_epsilon = 4.0 * epsilon
    twentyfour_epsilon = 24.0 * epsilon

    for i in range(n):
        for j in neighbors[i]:
            if j <= i:
                continue
            r_vec = positions[i] - positions[j]
            r_vec -= box_size * np.round(r_vec / box_size)
            r2 = np.dot(r_vec, r_vec)

            if r2 > rc2:
                continue

            sr2 = sigma2 / r2
            sr6 = sr2 * sr2 * sr2
            sr12 = sr6 * sr6

            u = four_epsilon * (sr12 - sr6)
            potential += u

            f_scalar = twentyfour_epsilon * (2.0 * sr12 - sr6) / r2
            f_ij = f_scalar * r_vec
            forces[i] += f_ij
            forces[j] -= f_ij

    return forces, potential


def _compute_forces_neighbor_gpu(positions, neighbors, box_size, sigma, epsilon, rc):
    """GPU 版本邻居列表力计算"""
    n = positions.shape[0]
    forces = cp.zeros((n, 3), dtype=cp.float64)
    potential = cp.float64(0.0)

    rc2 = rc * rc
    sigma2 = sigma * sigma
    four_epsilon = 4.0 * epsilon
    twentyfour_epsilon = 24.0 * epsilon

    neighbor_pairs = []
    for i in range(n):
        for j in neighbors[i]:
            if j > i:
                neighbor_pairs.append([i, j])

    if len(neighbor_pairs) == 0:
        return forces, 0.0

    pairs = cp.array(neighbor_pairs, dtype=cp.int32)
    n_pairs = pairs.shape[0]

    i_idx = pairs[:, 0]
    j_idx = pairs[:, 1]

    r_vec = positions[i_idx] - positions[j_idx]
    r_vec = r_vec - box_size * cp.round(r_vec / box_size)
    r2 = cp.sum(r_vec * r_vec, axis=1)

    mask = r2 <= rc2
    if not cp.any(mask):
        synchronize()
        return forces, 0.0

    r2_masked = r2[mask]
    r_vec_masked = r_vec[mask]
    i_masked = i_idx[mask]
    j_masked = j_idx[mask]

    sr2 = sigma2 / r2_masked
    sr6 = sr2 * sr2 * sr2
    sr12 = sr6 * sr6

    u = four_epsilon * (sr12 - sr6)
    potential = cp.sum(u)

    f_scalar = twentyfour_epsilon * (2.0 * sr12 - sr6) / r2_masked
    f_ij = f_scalar[:, cp.newaxis] * r_vec_masked

    for k in range(f_ij.shape[0]):
        forces[i_masked[k]] += f_ij[k]
        forces[j_masked[k]] -= f_ij[k]

    synchronize()
    return forces, float(potential)
