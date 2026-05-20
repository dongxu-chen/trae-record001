import numpy as np
import sys
sys.path.insert(0, '.')

print("=" * 60)
print("噪声和可视化功能测试")
print("=" * 60)

print("\n1. 测试噪声模块导入:")
try:
    from quantum_simulator import (NoiseChannel, DepolarizingNoise,
                                   AmplitudeDampingNoise, PhaseDampingNoise)
    print("  ✓ 噪声模块导入成功")
except Exception as e:
    print(f"  ✗ 导入失败: {e}")

print("\n2. 测试退极化噪声:")
try:
    noise = DepolarizingNoise(p=0.1)
    print(f"  ✓ 创建成功: {noise.name}")
    print(f"  ✓ Kraus 算子数量: {len(noise.kraus_operators)}")
except Exception as e:
    print(f"  ✗ 测试失败: {e}")

print("\n3. 测试振幅阻尼噪声:")
try:
    noise = AmplitudeDampingNoise(gamma=0.2)
    print(f"  ✓ 创建成功: {noise.name}")
    print(f"  ✓ Kraus 算子数量: {len(noise.kraus_operators)}")
except Exception as e:
    print(f"  ✗ 测试失败: {e}")

print("\n4. 测试密度矩阵和偏迹:")
try:
    from quantum_simulator import state_to_density_matrix, partial_trace
    
    qc = QuantumCircuit(2)
    qc.h(0)
    qc.cnot(0, 1)
    state = qc.run()
    rho = state_to_density_matrix(state.get_state_vector())
    print(f"  ✓ 密度矩阵形状: {rho.shape}")
    
    rho_0 = partial_trace(rho, [0], 2)
    print(f"  ✓ qubit 0 偏迹形状: {rho_0.shape}")
except Exception as e:
    print(f"  ✗ 测试失败: {e}")

print("\n5. 测试布洛赫坐标:")
try:
    from quantum_simulator import get_bloch_coordinates
    
    rho_0 = partial_trace(rho, [0], 2)
    x, y, z = get_bloch_coordinates(rho_0)
    print(f"  ✓ Bell 态 qubit 0 坐标: ({x:.4f}, {y:.4f}, {z:.4f})")
except Exception as e:
    print(f"  ✗ 测试失败: {e}")

print("\n6. 测试量子线路添加噪声:")
try:
    qc = QuantumCircuit(2)
    qc.h(0)
    qc.cnot(0, 1)
    qc.add_depolarizing_noise(0.1, [0, 1])
    print(f"  ✓ 噪声添加成功")
    print(f"  ✓ 噪声通道数量: {len(qc.noise_channels)}")
    
    state = qc.run()
    print(f"  ✓ 带噪声状态概率: {state.get_probability_dict()}")
except Exception as e:
    print(f"  ✗ 测试失败: {e}")

print("\n7. 测试振幅阻尼噪声应用:")
try:
    qc = QuantumCircuit(1)
    qc.h(0)
    qc.add_amplitude_damping_noise(0.5, 0)
    state = qc.run()
    print(f"  ✓ 振幅阻尼后概率: {state.get_probability_dict()}")
except Exception as e:
    print(f"  ✗ 测试失败: {e}")

print("\n8. 测试可视化模块导入:")
try:
    from quantum_simulator import (BlochSphere, plot_bloch_sphere,
                                   plot_probability_histogram)
    print("  ✓ 可视化模块导入成功")
except ImportError as e:
    print(f"  ! matplotlib 未安装: {e}")
except Exception as e:
    print(f"  ✗ 导入失败: {e}")

print("\n9. 测试启用每道门后自动添加噪声:")
try:
    qc = QuantumCircuit(2)
    qc.enable_noise_after_gates(
        DepolarizingNoise(0.01),
        qubits=[0, 1]
    )
    qc.h(0)
    qc.cnot(0, 1)
    print(f"  ✓ 启用自动噪声成功")
    print(f"  ✓ 门操作数量: {len(qc.gates)}")
    print(f"  ✓ 噪声通道数量: {len(qc.noise_channels)}")
except Exception as e:
    print(f"  ✗ 测试失败: {e}")

print("\n" + "=" * 60)
print("所有功能测试完成！")
print("=" * 60)
