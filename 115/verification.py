import numpy as np
import warnings
import sys
sys.path.insert(0, '.')

from quantum_simulator import QuantumState, QuantumCircuit

print("="*70)
print("量子模拟器修复验证")
print("="*70)

tests_passed = 0
tests_total = 0

def test(name, condition):
    global tests_passed, tests_total
    tests_total += 1
    if condition:
        print(f"✓ {name}")
        tests_passed += 1
    else:
        print(f"✗ {name}")

print("\n1. 数据类型验证:")
qs = QuantumState(2)
test("使用 complex64", qs.state.dtype == np.complex64)
test("初始状态正确", np.isclose(qs.state[0], 1.0) and np.allclose(qs.state[1:], 0))

print("\n2. 单比特门验证:")
qc = QuantumCircuit(1)
qc.x(0)
state = qc.run()
test("Pauli-X 门 (|0⟩→|1⟩)", np.isclose(state.state[1], 1.0))

qc = QuantumCircuit(1)
qc.h(0)
state = qc.run()
expected = np.array([1/np.sqrt(2), 1/np.sqrt(2)], dtype=np.complex64)
test("Hadamard 门 (|+⟩ 叠加态)", np.allclose(np.abs(state.state), np.abs(expected)))

print("\n3. CNOT 门验证:")
qc = QuantumCircuit(2)
qc.x(0)
qc.cnot(0, 1)
state = qc.run()
test("CNOT(0,1): |01⟩→|11⟩ (控制位=1时翻转)", np.isclose(state.state[3], 1.0))

qc = QuantumCircuit(2)
qc.x(1)
qc.cnot(1, 0)
state = qc.run()
test("CNOT(1,0): |10⟩→|11⟩ (控制位=1时翻转)", np.isclose(state.state[3], 1.0))

qc = QuantumCircuit(2)
qc.cnot(0, 1)
state = qc.run()
test("CNOT 不影响控制位=0 的状态", np.isclose(state.state[0], 1.0))

print("\n4. Bell 态验证:")
qc = QuantumCircuit(2)
qc.h(0)
qc.cnot(0, 1)
state = qc.run()
probs = state.get_probability_dict()
test("Bell 态 |00⟩ 概率 0.5", abs(probs.get('00', 0) - 0.5) < 0.01)
test("Bell 态 |11⟩ 概率 0.5", abs(probs.get('11', 0) - 0.5) < 0.01)
test("Bell 态 |01⟩ 概率 ~0", probs.get('01', 0) < 0.01)
test("Bell 态 |10⟩ 概率 ~0", probs.get('10', 0) < 0.01)

print("\n5. 概率归一化验证:")
qc = QuantumCircuit(3)
qc.h(0)
qc.h(1)
qc.cnot(0, 2)
state = qc.run()
total_prob = np.sum(np.abs(state.state)**2)
test("概率总和 = 1", abs(total_prob - 1.0) < 1e-10)

probs = state.get_probabilities()
test("get_probabilities() 归一化", abs(np.sum(probs) - 1.0) < 1e-10)

print("\n6. 测量验证:")
qc = QuantumCircuit(1)
qc.h(0)
state = qc.run()
result, collapsed = state.measure()
test("测量结果为 '0' 或 '1'", result in ['0', '1'])

collapsed_probs = collapsed.get_probabilities()
test("坍缩后状态归一化", abs(np.sum(collapsed_probs) - 1.0) < 1e-10)
test("坍缩后状态为经典态", np.max(collapsed_probs) > 0.99)

print("\n7. 内存警告验证:")
with warnings.catch_warnings(record=True) as w:
    warnings.simplefilter("always")
    try:
        qs_big = QuantumState(26)
        test("N>25 时发出警告", len(w) > 0)
    except MemoryError:
        print("  (内存不足，跳过)")
        tests_total -= 1

print("\n8. GHZ 态验证:")
qc = QuantumCircuit(3)
qc.h(0)
qc.cnot(0, 1)
qc.cnot(1, 2)
state = qc.run()
probs = state.get_probability_dict()
test("GHZ 态 |000⟩ 概率 0.5", abs(probs.get('000', 0) - 0.5) < 0.01)
test("GHZ 态 |111⟩ 概率 0.5", abs(probs.get('111', 0) - 0.5) < 0.01)

print("\n" + "="*70)
print(f"测试结果: {tests_passed}/{tests_total} 测试通过")
print("="*70)

if tests_passed == tests_total:
    print("\n🎉 所有测试通过！量子模拟器已成功修复！")
else:
    print(f"\n⚠️  {tests_total - tests_passed} 个测试失败")
