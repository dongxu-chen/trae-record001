from quantum_simulator import QuantumSimulator
import numpy as np


def example_bell_state():
    print("=" * 60)
    print("示例1: 创建贝尔态 (Bell State)")
    print("=" * 60)
    
    qs = QuantumSimulator(2)
    print("初始状态:")
    qs.print_state()
    
    qs.h(0)
    print("\n应用 H 门到量子比特 0 后:")
    qs.print_state()
    
    qs.cnot(0, 1)
    print("\n应用 CNOT 门 (控制: 0, 目标: 1) 后:")
    qs.print_state()
    
    print("\n概率分布:")
    qs.print_probabilities()
    
    print("\n测量一次 (结果随机):")
    result = qs.measure_all()
    print(f"测量结果: |{result}>")
    print("\n测量后的状态:")
    qs.print_state()
    print()


def example_ghz_state():
    print("=" * 60)
    print("示例2: 创建 GHZ 态 (3量子比特)")
    print("=" * 60)
    
    qs = QuantumSimulator(3)
    print("初始状态:")
    qs.print_state()
    
    qs.h(0)
    qs.cnot(0, 1)
    qs.cnot(1, 2)
    
    print("\nGHZ 态:")
    qs.print_state()
    qs.print_probabilities()
    print()


def example_swap_gate():
    print("=" * 60)
    print("示例3: SWAP 门演示")
    print("=" * 60)
    
    qs = QuantumSimulator(2)
    qs.x(0)
    print("初始状态 (|01>):")
    qs.print_state()
    
    qs.swap(0, 1)
    print("\n应用 SWAP 门后 (应该变为 |10>):")
    qs.print_state()
    print()


def example_single_qubit_gates():
    print("=" * 60)
    print("示例4: 单量子比特门演示")
    print("=" * 60)
    
    qs = QuantumSimulator(1)
    print("初始状态 |0>:")
    qs.print_state()
    
    qs.x(0)
    print("\nX 门后 |1>:")
    qs.print_state()
    
    qs.h(0)
    print("\nH 门后 (叠加态):")
    qs.print_state()
    
    qs.z(0)
    print("\nZ 门后 (相位翻转):")
    qs.print_state()
    print()


def example_10_qubits():
    print("=" * 60)
    print("示例5: 10量子比特演示 (最大支持)")
    print("=" * 60)
    
    qs = QuantumSimulator(10)
    print(f"创建 {qs.num_qubits} 量子比特模拟器")
    print(f"状态向量维度: {len(qs.get_state_vector())}")
    
    qs.h(0)
    qs.h(1)
    qs.h(2)
    
    print("\n对前3个量子比特应用 H 门后的概率分布:")
    qs.print_probabilities()
    print()


def example_measurements():
    print("=" * 60)
    print("示例6: 多次测量统计")
    print("=" * 60)
    
    qs = QuantumSimulator(2)
    qs.h(0)
    qs.cnot(0, 1)
    
    print("贝尔态 |Φ+> = (|00> + |11>)/√2")
    print("进行 1000 次测量...")
    
    counts = {'00': 0, '01': 0, '10': 0, '11': 0}
    trials = 1000
    
    for _ in range(trials):
        temp_qs = QuantumSimulator(2)
        temp_qs.h(0)
        temp_qs.cnot(0, 1)
        result = temp_qs.measure_all()
        counts[result] += 1
    
    print(f"\n{trials} 次测量结果:")
    for state, count in counts.items():
        prob = count / trials
        print(f"  |{state}>: {count:4d} ({prob:.4f})")
    print()


if __name__ == "__main__":
    np.random.seed(42)
    
    example_bell_state()
    example_ghz_state()
    example_swap_gate()
    example_single_qubit_gates()
    example_10_qubits()
    example_measurements()
    
    print("=" * 60)
    print("所有示例运行完成!")
    print("=" * 60)
