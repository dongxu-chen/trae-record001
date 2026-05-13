import numpy as np


def read_xyz(file_path):
    """
    读取 XYZ 格式的初始结构文件

    Args:
        file_path (str): XYZ 文件路径

    Returns:
        positions (np.ndarray): 粒子位置数组，形状 (N, 3)
        elements (list): 粒子类型列表
        box (np.ndarray): 模拟盒子边界，形状 (3, 2)，如 box[:, 0] 为各维度最小值，box[:, 1] 为最大值
    """
    with open(file_path, 'r') as f:
        lines = f.readlines()

    n_particles = int(lines[0].strip())
    positions = np.zeros((n_particles, 3), dtype=np.float64)
    elements = []

    for i in range(n_particles):
        parts = lines[i + 2].split()
        elements.append(parts[0])
        positions[i] = [float(p) for p in parts[1:4]]

    box = np.array([[positions[:, dim].min(), positions[:, dim].max()] for dim in range(3)], dtype=np.float64)
    return positions, elements, box


def write_xyz(file_path, positions, elements, step, append=False):
    """
    将当前结构写入 XYZ 文件

    Args:
        file_path (str): 输出文件路径
        positions (np.ndarray): 粒子位置数组
        elements (list): 粒子类型列表
        step (int): 当前模拟步数
        append (bool): 是否追加写入
    """
    mode = 'a' if append else 'w'
    with open(file_path, mode) as f:
        f.write(f"{len(positions)}\n")
        f.write(f"Step: {step}\n")
        for elem, pos in zip(elements, positions):
            f.write(f"{elem} {pos[0]:.6f} {pos[1]:.6f} {pos[2]:.6f}\n")
