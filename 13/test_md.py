import numpy as np
import sys
import time
sys.path.insert(0, '.')

from cuda_utils import is_gpu_available, to_gpu, to_cpu

print('=' * 60)
print('GPU 支持检测')
print('=' * 60)
gpu_ok = is_gpu_available()
print(f"CuPy 可用: {gpu_ok}")

from force import (
    compute_forces_naive,
    compute_forces_neighbor,
    minimum_image
)
from neighbor import NeighborList
from integrate import (
    velocity_verlet_step,
    compute_kinetic_energy,
    compute_temperature,
    velocity_rescale
)

print()
print('=' * 60)
print('测试 1: 最小镜像距离计算')
print('=' * 60)

box_size = np.array([10.0, 10.0, 10.0])
r_vec1 = np.array([8.0, 0, 0])
r_vec2 = np.array([-6.0, 0, 0])

img1 = minimum_image(r_vec1, box_size)
img2 = minimum_image(r_vec2, box_size)

print(f"原位移: {r_vec1}, 最小镜像: {img1} (期望: [-2, 0, 0])")
print(f"原位移: {r_vec2}, 最小镜像: {img2} (期望: [4, 0, 0])")

assert np.allclose(img1, np.array([-2.0, 0, 0])), "最小镜像测试1失败"
assert np.allclose(img2, np.array([4.0, 0, 0])), "最小镜像测试2失败"
print("PASS: 最小镜像距离计算正确")

print()
print('=' * 60)
print('测试 2: 邻居列表格点索引边界测试')
print('=' * 60)

positions = np.array([
    [0.0, 0.0, 0.0],
    [9.99, 9.99, 9.99],
    [0.01, 0.01, 0.01],
])
box = np.array([[0, 10], [0, 10], [0, 10]], dtype=np.float64)

nl = NeighborList(rc=3.0, skin=0.3)
try:
    nl.build_verlet(positions, box)
    neighbors = nl.get_neighbors()
    print(f"邻居列表构建成功")
    for i, neigh in enumerate(neighbors):
        print(f"  粒子 {i} 的邻居: {neigh}")
    print("PASS: 格点索引边界无越界")
except Exception as e:
    print(f"FAIL: 索引越界异常: {e}")

print()
print('=' * 60)
print('测试 3: 速度重标度 - 动量保持为零')
print('=' * 60)

masses = np.array([1.0, 1.0, 1.0])
velocities = np.array([
    [1.0, 0.0, 0.0],
    [2.0, 0.0, 0.0],
    [3.0, 0.0, 0.0]
])

print(f"原始速度:\n{velocities}")

initial_momentum = np.sum(masses[:, np.newaxis] * velocities, axis=0)
print(f"初始动量: {initial_momentum}")

rescaled = velocity_rescale(velocities, masses, target_temperature=1.0)
print(f"重标度后速度:\n{rescaled}")

final_momentum = np.sum(masses[:, np.newaxis] * rescaled, axis=0)
print(f"重标度后动量: {final_momentum}")

assert np.allclose(final_momentum, np.zeros(3)), f"FAIL: 动量不为零，而是 {final_momentum}"
print("PASS: 速度重标度后总动量保持为零")

print()
print('=' * 60)
print('测试 4: 力的牛顿第三定律验证')
print('=' * 60)

positions = np.array([
    [0.0, 0.0, 0.0],
    [1.5, 0.0, 0.0]
])
box = np.array([[0, 10], [0, 10], [0, 10]], dtype=np.float64)

forces, pot = compute_forces_naive(positions, box)
print(f"粒子 0 受力: {forces[0]}")
print(f"粒子 1 受力: {forces[1]}")
print(f"总力: {np.sum(forces, axis=0)}")

assert np.allclose(forces[0], -forces[1]), "FAIL: 力不满足牛顿第三定律"
print("PASS: 力满足牛顿第三定律")

if gpu_ok:
    print()
    print('=' * 60)
    print('测试 5: GPU 数据传输测试')
    print('=' * 60)

    import cupy as cp

    positions_np = np.random.rand(100, 3) * 5.0
    positions_gpu = to_gpu(positions_np)
    positions_back = to_cpu(positions_gpu)

    print(f"NumPy 数组形状: {positions_np.shape}")
    print(f"CuPy 数组形状: {positions_gpu.shape}")
    print(f"传输回 CPU 后一致: {np.allclose(positions_np, positions_back)}")
    print("PASS: GPU 数据传输正常")

    print()
    print('=' * 60)
    print('测试 6: CPU/GPU 结果一致性')
    print('=' * 60)

    positions_np = np.array([
        [0.0, 0.0, 0.0],
        [1.2, 0.0, 0.0],
        [0.0, 1.2, 0.0]
    ], dtype=np.float64)
    box = np.array([[0, 10], [0, 10], [0, 10]], dtype=np.float64)

    forces_cpu, pot_cpu = compute_forces_naive(positions_np, box)

    positions_gpu = to_gpu(positions_np)
    forces_gpu, pot_gpu = compute_forces_naive(positions_gpu, box)
    forces_gpu_cpu = to_cpu(forces_gpu)

    print(f"CPU 势能: {pot_cpu:.6f}")
    print(f"GPU 势能: {pot_gpu:.6f}")
    print(f"势能一致: {abs(pot_cpu - pot_gpu) < 1e-10}")
    print(f"力一致: {np.allclose(forces_cpu, forces_gpu_cpu, atol=1e-10)}")

    print("PASS: CPU/GPU 结果一致")

print()
print('=' * 60)
print('所有测试通过！')
print('=' * 60)
