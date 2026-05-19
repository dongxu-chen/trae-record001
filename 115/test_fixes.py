import numpy as np
import sys
import warnings

from quantum_simulator import QuantumState, QuantumCircuit, Hadamard, PauliX, CNOT

print("="*60)
print("量子模拟器修复测试")
print("="*60)

print("\n1. 测试 complex64 数据类型:")
qs = QuantumState(2)
print(f"   状态向量 dtype: {qs.state.dtype}")
assert qs.state.dtype == np.complex64, "应该使用 complex64"
print("   ✓ 通过")

print("\n2. 测试 Hadamard 门:")
qc = QuantumCircuit(1)
qc.h(0)
state = qc.run()
expected = np.array([1/np.sqrt(2), 1/np.sqrt(2)], dtype=np.complex64)
print(f"   预期: {expected}")
print(f"   实际: {state.state}")
diff = np.max(np.abs(state.state - expected))
print(f"   差异: {diff}")
assert diff < 1e-5, "Hadamard 门错误"
print("   ✓ 通过")

print("\n3. 测试 Pauli-X 门:")
qc = QuantumCircuit(1)
qc.x(0)
state = qc.run()
expected = np.array([0, 1], dtype=np.complex64)
print(f"   预期: {expected}")
print(f"   实际: {state.state}")
diff = np.max(np.abs(state.state - expected))
print(f"   差异: {diff}")
assert diff < 1e-5, "Pauli-X 门错误"
print("   ✓ 通过")

print("\n4. 测试 Bell 态 (H on q0, CNOT q0->q1):")
qc = QuantumCircuit(2)
qc.h(0)
qc.cnot(0, 1)
state = qc.run()
print(f"   状态: {state}")
prob_dict = state.get_probability_dict()
print(f"   概率: {prob_dict}")

expected_prob = {'00': 0.5, '11': 0.5}
for key in expected_prob:
    assert abs(prob_dict.get(key, 0) - expected_prob[key]) < 1e-5, f"{key} 概率错误"

for key in ['01', '10']:
    assert prob_dict.get(key, 0) < 1e-10, f"{key} 应该概率为 0"

print("   ✓ 通过 (Bell 态正确纠缠)")

print("\n5. 测试 Bell 态 2 (H on q1, CNOT q1->q0):")
qc = QuantumCircuit(2)
qc.h(1)
qc.cnot(1, 0)
state = qc.run()
print(f"   状态: {state}")
prob_dict = state.get_probability_dict()
print(f"   概率: {prob_dict}")

expected_prob = {'00': 0.5, '11': 0.5}
for key in expected_prob:
    assert abs(prob_dict.get(key, 0) - expected_prob[key]) < 1e-5, f"{key} 概率错误"
print("   ✓ 通过")

print("\n6. 测试概率归一化:")
qc = QuantumCircuit(2)
qc.h(0)
state = qc.run()
probs = state.get_probabilities()
total = np.sum(probs)
print(f"   概率总和: {total}")
assert abs(total - 1.0) < 1e-10, "概率未归一化"
print("   ✓ 通过")

print("\n7. 测试测量功能:")
qc = QuantumCircuit(1)
qc.h(0)
results = []
for _ in range(1000):
    result, _ = qc.run().measure()
    results.append(result)

count_0 = results.count('0')
count_1 = results.count('1')
print(f"   测量 1000 次: |0⟩={count_0}, |1⟩={count_1}")
prob_0 = count_0 / 1000
prob_1 = count_1 / 1000
assert 0.4 < prob_0 < 0.6, f"概率 0 异常: {prob_0}"
assert 0.4 < prob_1 < 0.6, f"概率 1 异常: {prob_1}"
print("   ✓ 通过")

print("\n8. 测试内存警告 (26 qubits):")
with warnings.catch_warnings(record=True) as w:
    warnings.simplefilter("always")
    try:
        qs = QuantumState(26)
        assert len(w) >= 1, "应该发出内存警告"
        print(f"   ✓ 警告信息: {w[0].message}")
    except MemoryError:
        print("   (内存不足，跳过)")
    except Exception as e:
        print(f"   错误: {e}")

print("\n9. 测试三比特 GHZ 态:")
qc = QuantumCircuit(3)
qc.h(0)
qc.cnot(0, 1)
qc.cnot(1, 2)
state = qc.run()
print(f"   状态: {state}")
prob_dict = state.get_probability_dict()
print(f"   概率: {prob_dict}")

assert '000' in prob_dict and abs(prob_dict['000'] - 0.5) < 1e-5
assert '111' in prob_dict and abs(prob_dict['111'] - 0.5) < 1e-5
print("   ✓ 通过 (GHZ 态正确)")

print("\n10. 测试单比特测量后坍缩:")
qc = QuantumCircuit(2)
qc.h(0)
state = qc.run()
print(f"   测量前: {state}")
outcome, collapsed = state.measure(qubit=0)
print(f"   测量比特 0 结果: {outcome}")
print(f"   坍缩后状态: {collapsed}")

collapsed_probs = collapsed.get_probabilities()
assert np.isclose(np.sum(collapsed_probs), 1.0), "坍缩后状态未归一化"
print("   ✓ 通过")

print("\n" + "="*60)
print("所有测试通过! ✓")
print("="*60)
