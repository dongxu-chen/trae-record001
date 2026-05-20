import sys
import numpy as np

try:
    from quantum_simulator import QuantumState, QuantumCircuit
    print("✓ 导入成功")
except Exception as e:
    print(f"✗ 导入失败: {e}")
    sys.exit(1)

try:
    qc = QuantumCircuit(1)
    qc.h(0)
    state = qc.run()
    print(f"✓ 单比特测试通过: {state}")
except Exception as e:
    print(f"✗ 单比特测试失败: {e}")
    sys.exit(1)

try:
    qc = QuantumCircuit(2)
    qc.h(0)
    qc.cnot(0, 1)
    state = qc.run()
    print(f"✓ Bell态测试通过: {state}")
except Exception as e:
    print(f"✗ Bell态测试失败: {e}")
    sys.exit(1)

try:
    qc = QuantumCircuit(1)
    qc.h(0)
    results, _ = qc.measure(num_shots=5)
    print(f"✓ 测量测试通过: {results}")
except Exception as e:
    print(f"✗ 测量测试失败: {e}")
    sys.exit(1)

print("\n" + "="*40)
print("所有测试通过! ✓")
print("="*40)
