import numpy as np
import sys
sys.path.insert(0, '.')

from quantum_simulator import QuantumCircuit

print("="*60)
print("CNOT 门调试")
print("="*60)

print("\n状态索引约定:")
print("  索引 0: |00⟩ = q1=0, q0=0")
print("  索引 1: |01⟩ = q1=0, q0=1")
print("  索引 2: |10⟩ = q1=1, q0=0")
print("  索引 3: |11⟩ = q1=1, q0=1")

print("\n1. 测试: X on q0")
qc = QuantumCircuit(2)
qc.x(0)
state = qc.run()
print(f"   预期: |01⟩ (索引 1)")
print(f"   实际: {state}")
print(f"   状态向量: {state.state}")

print("\n2. 测试: X on q1")
qc = QuantumCircuit(2)
qc.x(1)
state = qc.run()
print(f"   预期: |10⟩ (索引 2)")
print(f"   实际: {state}")
print(f"   状态向量: {state.state}")

print("\n3. 测试: H on q0")
qc = QuantumCircuit(2)
qc.h(0)
state = qc.run()
print(f"   预期: (|00⟩ + |01⟩)/√2")
print(f"   实际: {state}")

print("\n4. 测试: H on q1")
qc = QuantumCircuit(2)
qc.h(1)
state = qc.run()
print(f"   预期: (|00⟩ + |10⟩)/√2")
print(f"   实际: {state}")

print("\n5. 测试 CNOT(control=0, target=1) on |+0⟩ = (|00⟩+|10⟩)/√2")
print("   预期 Bell 态: (|00⟩ + |11⟩)/√2")
qc = QuantumCircuit(2)
qc.h(0)
qc.cnot(0, 1)
state = qc.run()
print(f"   实际: {state}")
print(f"   概率: {state.get_probability_dict()}")

print("\n6. 测试 CNOT(control=1, target=0) on |0+⟩ = (|00⟩+|01⟩)/√2")
print("   预期 Bell 态: (|00⟩ + |11⟩)/√2")
qc = QuantumCircuit(2)
qc.h(1)
qc.cnot(1, 0)
state = qc.run()
print(f"   实际: {state}")
print(f"   概率: {state.get_probability_dict()}")
