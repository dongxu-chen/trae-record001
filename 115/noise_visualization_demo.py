import numpy as np
import sys
sys.path.insert(0, '.')

from quantum_simulator import (QuantumCircuit, create_bell_state,
                                plot_bloch_sphere, plot_bloch_sphere_multiple,
                                plot_probability_histogram, plot_state_probabilities,
                                plot_noise_comparison,
                                state_to_density_matrix, partial_trace,
                                get_bloch_coordinates)

print("=" * 70)
print("量子模拟器噪声和可视化演示")
print("=" * 70)

print("\n1. 演示 1: 单量子比特布洛赫球可视化")
print("-" * 70)

qc1 = QuantumCircuit(1)
state_0 = qc1.run()
print(f"|0⟩ 状态:", state_0)

qc1.h(0)
state_plus = qc1.run()
print(f"|+⟩ 状态:", state_plus)

qc2 = QuantumCircuit(1)
qc2.x(0)
state_1 = qc2.run()
print(f"|1⟩ 状态:", state_1)

try:
    sphere = plot_bloch_sphere_multiple(
        [state_0, state_plus, state_1],
        labels=['|0⟩', '|+⟩', '|1⟩'],
        colors=['blue', 'green', 'red'],
        show=False
    )
    sphere.fig.savefig('bloch_single_qubit.png', dpi=150, bbox_inches='tight')
    print("✓ 布洛赫球已保存到 bloch_single_qubit.png")
except Exception as e:
    print(f"绘图失败: {e}")

print("\n2. 演示 2: Bell态概率直方图（无噪声）")
print("-" * 70)

qc_bell = create_bell_state()
state_bell = qc_bell.run()
print(f"Bell 态:", state_bell)
print(f"概率分布:", state_bell.get_probability_dict())

try:
    plot_state_probabilities(
        state_bell,
        title="Bell State Probabilities (No Noise)",
        show=False,
        save_path='bell_no_noise.png'
    )
    print("✓ Bell 态概率直方图已保存到 bell_no_noise.png")
except Exception as e:
    print(f"绘图失败: {e}")

print("\n3. 演示 3: 带噪声的 Bell 态")
print("-" * 70)

qc_noisy = QuantumCircuit(2)
qc_noisy.h(0)
qc_noisy.cnot(0, 1)
qc_noisy.add_depolarizing_noise(0.1, [0, 1])

state_noisy = qc_noisy.run()
print(f"带噪声的 Bell 态概率:", state_noisy.get_probability_dict())

try:
    plot_state_probabilities(
        state_noisy,
        title="Bell State with Depolarizing Noise (p=0.1)",
        color='orange',
        show=False,
        save_path='bell_with_noise.png'
    )
    print("✓ 带噪声的 Bell 态概率直方图已保存到 bell_with_noise.png")
except Exception as e:
    print(f"绘图失败: {e}")

print("\n4. 演示 4: 噪声对纠缠的影响")
print("-" * 70)

print("不同噪声强度下的测量结果:")
for p in [0, 0.05, 0.1, 0.2]:
    qc = QuantumCircuit(2)
    qc.h(0)
    qc.cnot(0, 1)
    if p > 0:
        qc.add_depolarizing_noise(p, [0, 1])
    counts = qc.get_counts(num_shots=1000)
    fid = counts.get('00', 0) + counts.get('11', 0)
    fid_pct = fid / 10
    print(f"  p = {p:.2f}: 纠缠保真度 = {fid_pct:.1f}%")

print("\n5. 演示 5: 振幅阻尼噪声")
print("-" * 70)

gamma = 0.2
qc_damping = QuantumCircuit(1)
qc_damping.h(0)
qc_damping.add_amplitude_damping_noise(gamma, 0)
state_damped = qc_damping.run()
print(f"振幅阻尼后概率 (gamma={gamma}):")
print(f"  {state_damped.get_probability_dict()}")

print("\n6. 演示 6: Bell 态的量子比特 0 在布洛赫球上")
print("-" * 70)

print(" 无噪声 Bell 态 qubit 0:")
rho = state_to_density_matrix(state_bell.get_state_vector())
rho_0 = partial_trace(rho, [0], 2)
x, y, z = get_bloch_coordinates(rho_0)
print(f"  Bloch 坐标: ({x:.4f}, {y:.4f}, {z:.4f})")

print("\n7. 演示 7: 噪声轨迹演示")
print("-" * 70)

print(" 模拟 Hadamard 门后加去极化噪声的轨迹:")
trajectory_points = []
for p in np.linspace(0, 0.5, 10):
    qc = QuantumCircuit(1)
    qc.h(0)
    if p > 0:
        qc.add_depolarizing_noise(p, 0)
    state = qc.run()
    rho = state_to_density_matrix(state.get_state_vector())
    x, y, z = get_bloch_coordinates(rho)
    trajectory_points.append((x, y, z))
    print(f"  p={p:.2f}: ({x:.4f}, {y:.4f}, {z:.4f})")

try:
    from quantum_simulator import BlochSphere
    sphere = BlochSphere(figsize=(8, 8))
    sphere.add_trajectory(trajectory_points, color='red')
    sphere.fig.savefig('bloch_trajectory.png', dpi=150, bbox_inches='tight')
    print("✓ 布洛赫球轨迹已保存到 bloch_trajectory.png")
except Exception as e:
    print(f"绘图失败: {e}")

print("\n8. 演示 8: 噪声对比绘图")
print("-" * 70)

qc_clean = QuantumCircuit(2)
qc_clean.h(0)
qc_clean.cnot(0, 1)

try:
    plot_noise_comparison(
        qc_clean,
        [
            ("No Noise", 0),
            ("Depolarizing", 0.05),
            ("Amplitude Damping", 0.1),
        ],
        num_shots=2000,
        show=False,
        save_path='noise_comparison.png'
    )
    print("✓ 噪声对比图已保存到 noise_comparison.png")
except Exception as e:
    print(f"绘图失败: {e}")

print("\n" + "=" * 70)
print("所有演示完成！")
print("=" * 70)
