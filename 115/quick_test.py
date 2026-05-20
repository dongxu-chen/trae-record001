import numpy as np
import sys
import warnings

sys.path.insert(0, '.')

from quantum_simulator import QuantumState, QuantumCircuit

print("="*50)
print("快速测试")
print("="*50)

print("\n1. 测试数据类型:")
qs = QuantumState(2)
print(f"   dtype: {qs.state.dtype}")
assert qs.state.dtype == np.complex64
print("   ✓ complex64 正确")

print("\n2. 测试 Bell 态:")
qc = QuantumCircuit(2)
qc.h(0)
qc.cnot(0, 1)
state = qc.run()
print(f"   状态: {state}")
probs = state.get_probability_dict()
print(f"   概率: {probs}")

expected_keys = ['00', '11']
for key in expected_keys:
    assert key in probs, f"缺少 {key}"
    assert abs(probs[key] - 0.5) < 0.01, f"{key} 概率错误"
print("   ✓ Bell 态正确")

print("\n3. 测试概率归一化:")
probs_arr = state.get_probabilities()
total = np.sum(probs_arr)
print(f"   概率总和: {total}")
assert abs(total - 1.0) < 1e-10
print("   ✓ 归一化正确")

print("\n4. 测试内存警告:")
with warnings.catch_warnings(record=True) as w:
    warnings.simplefilter("always")
    try:
        qs26 = QuantumState(26)
        if len(w) > 0:
            print(f"   ✓ 警告: {w[0].message}")
        else:
            print("   ! 未发出警告")
    except Exception as e:
        print(f"   (内存不足: {e})")

print("\n" + "="*50)
print("测试完成!")
print("="*50)
