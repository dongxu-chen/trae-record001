import numpy as np
from quantum_simulator import QuantumState, QuantumCircuit, Hadamard, PauliX, CNOT


def example_1_single_qubit():
    print("=" * 60)
    print("示例 1: 单比特量子门操作")
    print("=" * 60)
    
    qc = QuantumCircuit(1)
    print(f"\n初始状态: {qc.run()}")
    
    qc.h(0)
    state = qc.run()
    print(f"\n施加 Hadamard 门后: {state}")
    print(f"概率分布: {state.get_probability_dict()}")
    
    qc.x(0)
    state = qc.run()
    print(f"\n施加 Pauli-X 门后: {state}")


def example_2_bell_state():
    print("\n" + "=" * 60)
    print("示例 2: Bell 态 (纠缠态)")
    print("=" * 60)
    
    qc = QuantumCircuit(2)
    qc.h(0)
    qc.cnot(0, 1)
    
    print(f"\n线路:")
    print(qc)
    
    state = qc.run()
    print(f"\n最终状态: {state}")
    print(f"概率分布: {state.get_probability_dict()}")


def example_3_measurement():
    print("\n" + "=" * 60)
    print("示例 3: 量子测量")
    print("=" * 60)
    
    qc = QuantumCircuit(1)
    qc.h(0)
    
    print("\n运行 10 次测量:")
    results, final_state = qc.measure(num_shots=10)
    print(f"测量结果: {results}")
    
    print("\n运行 1000 次测量的统计:")
    counts = qc.get_counts(num_shots=1000)
    for outcome, count in sorted(counts.items()):
        print(f"  |{outcome}⟩: {count} 次 ({count/10:.1f}%)")


def example_4_ghz_state():
    print("\n" + "=" * 60)
    print("示例 4: GHZ 态 (3 量子比特纠缠)")
    print("=" * 60)
    
    qc = QuantumCircuit(3)
    qc.h(0)
    qc.cnot(0, 1)
    qc.cnot(1, 2)
    
    state = qc.run()
    print(f"\nGHZ 状态: {state}")
    print(f"概率幅: {state.get_amplitudes()}")
    
    print("\n单次测量结果和坍缩后的状态:")
    outcome, collapsed = state.measure()
    print(f"  测量结果: {outcome}")
    print(f"  坍缩后状态: {collapsed}")


def example_5_single_qubit_measurement():
    print("\n" + "=" * 60)
    print("示例 5: 单个量子比特测量")
    print("=" * 60)
    
    qc = QuantumCircuit(2)
    qc.h(0)
    qc.x(1)
    
    state = qc.run()
    print(f"\n初始状态: {state}")
    
    print("\n测量量子比特 0:")
    outcome, collapsed = state.measure(qubit=0)
    print(f"  测量结果: {outcome}")
    print(f"  坍缩后状态: {collapsed}")


if __name__ == "__main__":
    np.random.seed(42)
    
    example_1_single_qubit()
    example_2_bell_state()
    example_3_measurement()
    example_4_ghz_state()
    example_5_single_qubit_measurement()
    
    print("\n" + "=" * 60)
    print("所有示例运行完成!")
    print("=" * 60)
