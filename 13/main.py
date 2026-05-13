import numpy as np
import time

from io import read_xyz, write_xyz
from force import compute_forces_naive, compute_forces_neighbor, compute_forces_gpu
from neighbor import NeighborList
from integrate import (
    velocity_verlet_step,
    compute_kinetic_energy,
    compute_temperature,
    velocity_rescale
)
from cuda_utils import is_gpu_available, to_gpu, to_cpu


def generate_fcc_lattice(n_unit_cells, lattice_constant=1.549, element='Ar'):
    """
    生成面心立方 (FCC) 晶格的初始结构

    Args:
        n_unit_cells (int): 每个维度的晶胞数
        lattice_constant (float): 晶格常数
        element (str): 原子类型

    Returns:
        positions (np.ndarray): 位置数组
        elements (list): 原子类型列表
        box (np.ndarray): 盒子边界
    """
    positions = []
    basis = np.array([
        [0.0, 0.0, 0.0],
        [0.5, 0.5, 0.0],
        [0.5, 0.0, 0.5],
        [0.0, 0.5, 0.5]
    ]) * lattice_constant

    for i in range(n_unit_cells):
        for j in range(n_unit_cells):
            for k in range(n_unit_cells):
                offset = np.array([i, j, k]) * lattice_constant
                for atom in basis:
                    positions.append(offset + atom)

    n_atoms = len(positions)
    positions = np.array(positions, dtype=np.float64)
    elements = [element] * n_atoms

    box_length = n_unit_cells * lattice_constant
    box = np.array([[0.0, box_length], [0.0, box_length], [0.0, box_length]], dtype=np.float64)

    return positions, elements, box


def run_md(use_gpu=False):
    """主分子动力学模拟函数"""
    n_unit_cells = 3
    positions_cpu, elements, box = generate_fcc_lattice(n_unit_cells, lattice_constant=1.549)
    n_particles = len(positions_cpu)

    print(f"系统粒子数: {n_particles}")
    print(f"盒子大小: {box[:, 1] - box[:, 0]}")

    if use_gpu and is_gpu_available():
        print("GPU 模式: 已启用")
        positions = to_gpu(positions_cpu)
        masses = to_gpu(np.ones(n_particles, dtype=np.float64) * 39.95)
    else:
        print("GPU 模式: 未启用 (使用 CPU)")
        positions = positions_cpu
        masses = np.ones(n_particles, dtype=np.float64) * 39.95

    sigma = 1.0
    epsilon = 1.0
    rc = 2.5

    velocities_cpu = np.random.normal(0, 1.0, (n_particles, 3))
    velocities_cpu -= np.mean(velocities_cpu, axis=0)
    velocities_cpu = velocity_rescale(velocities_cpu, np.ones(n_particles) * 39.95, target_temperature=1.0)

    if use_gpu and is_gpu_available():
        velocities = to_gpu(velocities_cpu)
    else:
        velocities = velocities_cpu

    dt = 0.001
    n_steps = 1000
    output_interval = 100
    use_neighbor_list = True

    neighbor_list = NeighborList(rc=rc, skin=0.3, use_gpu=use_gpu) if use_neighbor_list else None

    def force_func(pos):
        if use_neighbor_list:
            pos_cpu = to_cpu(pos)
            if neighbor_list.need_rebuild(pos_cpu, box):
                print("重建邻居列表...")
                neighbor_list.build_verlet(pos_cpu, box)
            return compute_forces_neighbor(pos, neighbor_list.get_neighbors(), box, sigma, epsilon, rc)
        else:
            if use_gpu and is_gpu_available():
                return compute_forces_gpu(pos, box, sigma, epsilon, rc)
            else:
                return compute_forces_naive(pos, box, sigma, epsilon, rc)

    forces, potential = force_func(positions)

    write_xyz('trajectory.xyz', positions_cpu, elements, step=0, append=False)

    print(f"{'步长':>8} {'动能':>12} {'势能':>12} {'总能':>12} {'温度':>10}")
    print("-" * 60)

    start_time = time.time()

    for step in range(n_steps):
        positions, velocities, forces, potential = velocity_verlet_step(
            positions, velocities, forces, box, masses, dt, force_func
        )

        velocities_cpu_step = to_cpu(velocities)
        ke = compute_kinetic_energy(velocities_cpu_step, np.ones(n_particles) * 39.95)
        total_e = ke + potential
        temp = compute_temperature(ke, n_particles)

        if step % output_interval == 0:
            print(f"{step:>8} {ke:>12.4f} {potential:>12.4f} {total_e:>12.4f} {temp:>10.4f}")
            positions_cpu_step = to_cpu(positions)
            write_xyz('trajectory.xyz', positions_cpu_step, elements, step=step, append=True)

    end_time = time.time()

    print("-" * 60)
    print(f"模拟完成！耗时: {end_time - start_time:.2f} 秒")


if __name__ == "__main__":
    np.random.seed(42)
    run_md(use_gpu=False)
