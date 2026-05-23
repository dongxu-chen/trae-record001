import numpy as np
from quantum_simulator_extended import (
    QuantumSimulatorExtended,
    RepetitionCode,
    BitFlipNoise,
    PhaseFlipNoise,
    DepolarizingNoise
)


def demo_circuit_visualization():
    print("=" * 70)
    print("演示1: 量子电路ASCII可视化")
    print("=" * 70)
    
    print("\n1.1 贝尔态电路:")
    qs = QuantumSimulatorExtended(2)
    qs.h(0)
    qs.cnot(0, 1)
    qs.print_circuit()
    
    print("1.2 GHZ态电路 (3量子比特):")
    qs = QuantumSimulatorExtended(3)
    qs.h(0)
    qs.cnot(0, 1)
    qs.cnot(1, 2)
    qs.print_circuit()
    
    print("1.3 包含多种门的复杂电路:")
    qs = QuantumSimulatorExtended(4)
    qs.h(0)
    qs.x(1)
    qs.cnot(0, 2)
    qs.cz(1, 3)
    qs.swap(2, 3)
    qs.h(3)
    qs.print_circuit()


def demo_noise_channels():
    print("=" * 70)
    print("演示2: 噪声通道模拟")
    print("=" * 70)
    
    np.random.seed(42)
    
    print("\n2.1 比特翻转噪声 (Bit Flip Noise):")
    qs = QuantumSimulatorExtended(1)
    qs.x(0)
    print("初始状态 (|1>):")
    qs.print_state()
    
    print("\n应用 50% 概率的比特翻转噪声:")
    results = {'|0>': 0, '|1>': 0}
    for _ in range(1000):
        qs_temp = QuantumSimulatorExtended(1)
        qs_temp.x(0)
        qs_temp.bit_flip_noise(0, 0.5)
        state = qs_temp.get_state_vector()
        if abs(state[0]) > 0.5:
            results['|0>'] += 1
        else:
            results['|1>'] += 1
    
    print(f"  1000次实验结果: {results}")
    print(f"  翻转到|0>: {results['|0>']}次 ({results['|0>']/10}%)")
    
    print("\n2.2 相位翻转噪声 (Phase Flip Noise):")
    qs = QuantumSimulatorExtended(1)
    qs.h(0)
    print("初始状态 (|+> = (|0>+|1>)/√2):")
    qs.print_state()
    
    qs.phase_flip_noise(0, 1.0)
    print("应用 100% 相位翻转噪声后 (|-> = (|0>-|1>)/√2):")
    qs.print_state()
    
    print("\n2.3 去极化噪声 (Depolarizing Noise):")
    qs = QuantumSimulatorExtended(2)
    qs.h(0)
    qs.cnot(0, 1)
    print("初始贝尔态:")
    qs.print_state()
    
    qs.depolarizing_noise(0, 0.3)
    print("应用 30% 去极化噪声后:")
    qs.print_state()


def demo_repetition_code():
    print("=" * 70)
    print("演示3: 量子纠错码 - 重复码")
    print("=" * 70)
    
    np.random.seed(123)
    
    print("\n3.1 编码演示:")
    qs = QuantumSimulatorExtended(3)
    code = RepetitionCode(num_repetitions=3)
    
    print("初始状态 |0>:")
    qs.print_state()
    
    print("\n编码 (3量子比特重复码):")
    code.encode(qs, 0)
    qs.print_circuit()
    qs.print_state()
    
    print("\n3.2 纠错演示:")
    qs = QuantumSimulatorExtended(3)
    code = RepetitionCode(num_repetitions=3)
    qs.x(0)
    code.encode(qs, 0)
    
    print("编码后的 |111> 状态:")
    qs.print_state()
    
    print("\n模拟中间量子比特发生比特翻转错误:")
    qs.x(1)
    qs.print_state()
    
    print("检测错误...")
    has_error, syndrome = code.detect_error(qs)
    print(f"  检测到错误: {has_error}")
    print(f"  症候 (syndrome): {syndrome}")
    
    if has_error:
        print("纠正错误...")
        code.correct_error(qs, syndrome)
        print("纠正后的状态:")
        qs.print_state()
    
    decoded = code.decode(qs)
    print(f"解码结果: |{decoded}>")
    
    print("\n3.3 纠错成功率统计 (1000次实验):")
    success_without_code = 0
    success_with_code = 0
    error_prob = 0.3
    trials = 1000
    
    for _ in range(trials):
        qs_raw = QuantumSimulatorExtended(1)
        qs_raw.x(0)
        qs_raw.bit_flip_noise(0, error_prob)
        state = qs_raw.get_state_vector()
        if abs(state[1]) > abs(state[0]):
            success_without_code += 1
    
    for _ in range(trials):
        qs_ec = QuantumSimulatorExtended(3)
        code = RepetitionCode(3)
        qs_ec.x(0)
        code.encode(qs_ec, 0)
        
        for qubit in range(3):
            if np.random.random() < error_prob:
                qs_ec.x(qubit)
        
        has_error, syndrome = code.detect_error(qs_ec)
        if has_error:
            code.correct_error(qs_ec, syndrome)
        
        decoded = code.decode(qs_ec)
        if decoded == 1:
            success_with_code += 1
    
    print(f"  错误概率: {error_prob*100}%")
    print(f"  无纠错成功率: {success_without_code/trials*100:.1f}%")
    print(f"  有纠错成功率: {success_with_code/trials*100:.1f}%")
    print(f"  纠错增益: {(success_with_code - success_without_code)/trials*100:.1f}%")


def demo_noisy_circuit_with_visualization():
    print("=" * 70)
    print("演示4: 含噪声的电路可视化")
    print("=" * 70)
    
    print("\n带噪声的贝尔态制备电路:")
    qs = QuantumSimulatorExtended(2)
    qs.h(0)
    qs.bit_flip_noise(0, 0.1)
    qs.cnot(0, 1)
    qs.phase_flip_noise(1, 0.05)
    qs.print_circuit()
    
    print("状态:")
    qs.print_state()
    qs.print_probabilities()


def demo_5_qubit_repetition_code():
    print("\n" + "=" * 70)
    print("演示5: 5量子比特重复码 (更强的纠错能力)")
    print("=" * 70)
    
    np.random.seed(456)
    
    error_prob = 0.25
    trials = 1000
    success_3bit = 0
    success_5bit = 0
    
    for _ in range(trials):
        qs = QuantumSimulatorExtended(3)
        code = RepetitionCode(3)
        qs.x(0)
        code.encode(qs, 0)
        
        for qubit in range(3):
            if np.random.random() < error_prob:
                qs.x(qubit)
        
        has_error, syndrome = code.detect_error(qs)
        if has_error:
            code.correct_error(qs, syndrome)
        
        if code.decode(qs) == 1:
            success_3bit += 1
    
    for _ in range(trials):
        qs = QuantumSimulatorExtended(5)
        code = RepetitionCode(5)
        qs.x(0)
        code.encode(qs, 0)
        
        for qubit in range(5):
            if np.random.random() < error_prob:
                qs.x(qubit)
        
        has_error, syndrome = code.detect_error(qs)
        if has_error:
            code.correct_error(qs, syndrome)
        
        if code.decode(qs) == 1:
            success_5bit += 1
    
    print(f"错误概率: {error_prob*100}%")
    print(f"3量子比特重复码成功率: {success_3bit/trials*100:.1f}%")
    print(f"5量子比特重复码成功率: {success_5bit/trials*100:.1f}%")
    print(f"更多冗余带来的增益: {(success_5bit - success_3bit)/trials*100:.1f}%")


if __name__ == "__main__":
    demo_circuit_visualization()
    demo_noise_channels()
    demo_repetition_code()
    demo_noisy_circuit_with_visualization()
    demo_5_qubit_repetition_code()
    
    print("\n" + "=" * 70)
    print("所有演示完成!")
    print("=" * 70)
