import numpy as np
import time
from quantum_simulator import QuantumSimulator
from quantum_simulator_optimized import QuantumSimulatorOptimized


def test_correctness():
    print("=" * 60)
    print("正确性验证测试")
    print("=" * 60)
    
    np.random.seed(42)
    
    print("\n测试1: 贝尔态")
    qs1 = QuantumSimulator(2)
    qs2 = QuantumSimulatorOptimized(2)
    
    qs1.h(0)
    qs1.cnot(0, 1)
    qs2.h(0)
    qs2.cnot(0, 1)
    
    state1 = qs1.get_state_vector()
    state2 = qs2.get_state_vector()
    
    assert np.allclose(state1, state2), f"贝尔态不匹配!\n{state1}\n{state2}"
    print("  ✓ 贝尔态正确")
    
    print("\n测试2: GHZ态")
    qs1 = QuantumSimulator(3)
    qs2 = QuantumSimulatorOptimized(3)
    
    qs1.h(0)
    qs1.cnot(0, 1)
    qs1.cnot(1, 2)
    qs2.h(0)
    qs2.cnot(0, 1)
    qs2.cnot(1, 2)
    
    state1 = qs1.get_state_vector()
    state2 = qs2.get_state_vector()
    
    assert np.allclose(state1, state2), "GHZ态不匹配!"
    print("  ✓ GHZ态正确")
    
    print("\n测试3: SWAP门")
    qs1 = QuantumSimulator(2)
    qs2 = QuantumSimulatorOptimized(2)
    
    qs1.x(0)
    qs1.swap(0, 1)
    qs2.x(0)
    qs2.swap(0, 1)
    
    state1 = qs1.get_state_vector()
    state2 = qs2.get_state_vector()
    
    assert np.allclose(state1, state2), "SWAP门不匹配!"
    print("  ✓ SWAP门正确")
    
    print("\n测试4: CZ门")
    qs1 = QuantumSimulator(2)
    qs2 = QuantumSimulatorOptimized(2)
    
    qs1.h(0)
    qs1.h(1)
    qs1.cz(0, 1)
    qs2.h(0)
    qs2.h(1)
    qs2.cz(0, 1)
    
    state1 = qs1.get_state_vector()
    state2 = qs2.get_state_vector()
    
    assert np.allclose(state1, state2), "CZ门不匹配!"
    print("  ✓ CZ门正确")
    
    print("\n测试5: 所有单量子比特门")
    gates = ['h', 'x', 'y', 'z', 's', 't']
    for gate_name in gates:
        qs1 = QuantumSimulator(1)
        qs2 = QuantumSimulatorOptimized(1)
        
        getattr(qs1, gate_name)(0)
        getattr(qs2, gate_name)(0)
        
        state1 = qs1.get_state_vector()
        state2 = qs2.get_state_vector()
        
        assert np.allclose(state1, state2), f"{gate_name.upper()}门不匹配!"
    print("  ✓ 所有单量子比特门正确")
    
    print("\n测试6: 概率分布")
    qs1 = QuantumSimulator(3)
    qs2 = QuantumSimulatorOptimized(3)
    
    qs1.h(0)
    qs1.h(1)
    qs2.h(0)
    qs2.h(1)
    
    probs1 = qs1.get_probabilities()
    probs2 = qs2.get_probabilities()
    
    for key in probs1:
        assert abs(probs1[key] - probs2[key]) < 1e-10, f"概率不匹配: {key}"
    print("  ✓ 概率分布正确")
    
    print("\n测试7: 别名表采样统计")
    qs = QuantumSimulatorOptimized(2)
    qs.h(0)
    qs.cnot(0, 1)
    
    samples = 10000
    counts = {'00': 0, '01': 0, '10': 0, '11': 0}
    
    for _ in range(samples):
        result = qs.measure_all()
        qs.reset()
        qs.h(0)
        qs.cnot(0, 1)
        counts[result] += 1
    
    assert counts['00'] > 4000 and counts['00'] < 6000, f"00采样异常: {counts['00']}"
    assert counts['11'] > 4000 and counts['11'] < 6000, f"11采样异常: {counts['11']}"
    assert counts['01'] < 100 and counts['10'] < 100, f"01/10采样异常: {counts['01']}, {counts['10']}"
    print("  ✓ 别名表采样统计正确")
    
    print("\n" + "=" * 60)
    print("所有正确性测试通过!")
    print("=" * 60)


def test_performance():
    print("\n" + "=" * 60)
    print("性能测试")
    print("=" * 60)
    
    np.random.seed(42)
    
    print("\n测试1: CNOT门性能 (8量子比特)")
    n_qubits = 8
    
    qs1 = QuantumSimulator(n_qubits)
    qs2 = QuantumSimulatorOptimized(n_qubits)
    
    start = time.time()
    for _ in range(100):
        qs1.cnot(0, 7)
        qs1.reset()
    time_original = time.time() - start
    
    start = time.time()
    for _ in range(100):
        qs2.cnot(0, 7)
        qs2.get_state_vector()
        qs2.reset()
    time_optimized = time.time() - start
    
    print(f"  原始版本: {time_original:.4f}s")
    print(f"  优化版本: {time_optimized:.4f}s")
    print(f"  加速比: {time_original/time_optimized:.2f}x")
    
    print("\n测试2: 多门序列合并性能 (5量子比特)")
    n_qubits = 5
    
    qs1 = QuantumSimulator(n_qubits)
    qs2 = QuantumSimulatorOptimized(n_qubits)
    
    start = time.time()
    for _ in range(50):
        qs1.h(0)
        qs1.cnot(0, 1)
        qs1.h(2)
        qs1.cnot(2, 3)
        qs1.h(4)
        qs1.reset()
    time_original = time.time() - start
    
    start = time.time()
    for _ in range(50):
        qs2.h(0)
        qs2.cnot(0, 1)
        qs2.h(2)
        qs2.cnot(2, 3)
        qs2.h(4)
        qs2.get_state_vector()
        qs2.reset()
    time_optimized = time.time() - start
    
    print(f"  原始版本: {time_original:.4f}s")
    print(f"  优化版本: {time_optimized:.4f}s")
    print(f"  加速比: {time_original/time_optimized:.2f}x")
    
    print("\n测试3: 采样性能 (10量子比特, 10000次采样)")
    n_qubits = 10
    n_samples = 10000
    
    qs1 = QuantumSimulator(n_qubits)
    qs2 = QuantumSimulatorOptimized(n_qubits)
    
    for i in range(5):
        qs1.h(i)
        qs2.h(i)
    
    start = time.time()
    for _ in range(n_samples):
        qs1.measure_all()
        qs1.reset()
        for i in range(5):
            qs1.h(i)
    time_original = time.time() - start
    
    start = time.time()
    qs2._flush_gates()
    for _ in range(n_samples):
        qs2.measure_sample()
    time_optimized = time.time() - start
    
    print(f"  原始版本: {time_original:.4f}s ({n_samples/time_original:.0f} samples/s)")
    print(f"  优化版本: {time_optimized:.4f}s ({n_samples/time_optimized:.0f} samples/s)")
    print(f"  加速比: {time_original/time_optimized:.2f}x")
    
    print("\n" + "=" * 60)
    print("性能测试完成!")
    print("=" * 60)


def demo_optimized_features():
    print("\n" + "=" * 60)
    print("优化功能演示")
    print("=" * 60)
    
    print("\n1. 门序列缓存演示:")
    qs = QuantumSimulatorOptimized(3)
    print("   添加门序列...")
    qs.h(0)
    qs.cnot(0, 1)
    qs.h(2)
    print(f"   待执行门数量: {len(qs.gate_sequence.operations)}")
    
    print("\n   第一次访问状态向量 (触发门合并执行)...")
    state1 = qs.get_state_vector()
    print(f"   待执行门数量: {len(qs.gate_sequence.operations)}")
    
    print("\n   再次添加相同门序列...")
    qs.h(0)
    qs.cnot(0, 1)
    qs.h(2)
    print(f"   待执行门数量: {len(qs.gate_sequence.operations)}")
    
    print("\n2. 别名表采样演示:")
    qs = QuantumSimulatorOptimized(4)
    for i in range(4):
        qs.h(i)
    qs._flush_gates()
    
    print("   构建别名表...")
    alias_table = qs._build_alias_table()
    print(f"   别名表大小: {alias_table.n}")
    
    print("\n   快速采样 5 次:")
    for i in range(5):
        sample = qs.measure_sample()
        print(f"     采样 {i+1}: |{format(sample, '04b')}>")
    
    print("\n" + "=" * 60)
    print("优化功能演示完成!")
    print("=" * 60)


if __name__ == "__main__":
    test_correctness()
    test_performance()
    demo_optimized_features()
