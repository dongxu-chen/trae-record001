import numpy as np
from typing import List, Tuple, Dict


class QuantumSimulator:
    def __init__(self, num_qubits: int):
        if num_qubits < 1 or num_qubits > 10:
            raise ValueError("Number of qubits must be between 1 and 10")
        
        self.num_qubits = num_qubits
        self.state = np.zeros(2 ** num_qubits, dtype=complex)
        self.state[0] = 1.0
        
        self._gates = {
            'H': np.array([[1, 1], [1, -1]]) / np.sqrt(2),
            'X': np.array([[0, 1], [1, 0]]),
            'Y': np.array([[0, -1j], [1j, 0]]),
            'Z': np.array([[1, 0], [0, -1]]),
            'S': np.array([[1, 0], [0, 1j]]),
            'T': np.array([[1, 0], [0, np.exp(1j * np.pi / 4)]])
        }
    
    def _apply_single_qubit_gate(self, gate: np.ndarray, target_qubit: int) -> None:
        if target_qubit < 0 or target_qubit >= self.num_qubits:
            raise ValueError(f"Invalid target qubit: {target_qubit}")
        
        full_gate = 1.0
        for i in range(self.num_qubits):
            if i == target_qubit:
                full_gate = np.kron(full_gate, gate)
            else:
                full_gate = np.kron(full_gate, np.eye(2))
        
        self.state = full_gate @ self.state
    
    def h(self, target_qubit: int) -> None:
        self._apply_single_qubit_gate(self._gates['H'], target_qubit)
    
    def x(self, target_qubit: int) -> None:
        self._apply_single_qubit_gate(self._gates['X'], target_qubit)
    
    def y(self, target_qubit: int) -> None:
        self._apply_single_qubit_gate(self._gates['Y'], target_qubit)
    
    def z(self, target_qubit: int) -> None:
        self._apply_single_qubit_gate(self._gates['Z'], target_qubit)
    
    def s(self, target_qubit: int) -> None:
        self._apply_single_qubit_gate(self._gates['S'], target_qubit)
    
    def t(self, target_qubit: int) -> None:
        self._apply_single_qubit_gate(self._gates['T'], target_qubit)
    
    def cnot(self, control_qubit: int, target_qubit: int) -> None:
        if control_qubit == target_qubit:
            raise ValueError("Control and target qubits must be different")
        if control_qubit < 0 or control_qubit >= self.num_qubits:
            raise ValueError(f"Invalid control qubit: {control_qubit}")
        if target_qubit < 0 or target_qubit >= self.num_qubits:
            raise ValueError(f"Invalid target qubit: {target_qubit}")
        
        n = self.num_qubits
        size = 2 ** n
        full_gate = np.eye(size, dtype=complex)
        
        for state_idx in range(size):
            control_bit = (state_idx >> (n - 1 - control_qubit)) & 1
            if control_bit == 1:
                target_bit = (state_idx >> (n - 1 - target_qubit)) & 1
                new_state = state_idx ^ (1 << (n - 1 - target_qubit))
                full_gate[state_idx, state_idx] = 0
                full_gate[state_idx, new_state] = 1
        
        self.state = full_gate @ self.state
    
    def cz(self, control_qubit: int, target_qubit: int) -> None:
        if control_qubit == target_qubit:
            raise ValueError("Control and target qubits must be different")
        if control_qubit < 0 or control_qubit >= self.num_qubits:
            raise ValueError(f"Invalid control qubit: {control_qubit}")
        if target_qubit < 0 or target_qubit >= self.num_qubits:
            raise ValueError(f"Invalid target qubit: {target_qubit}")
        
        n = self.num_qubits
        size = 2 ** n
        
        for state_idx in range(size):
            control_bit = (state_idx >> (n - 1 - control_qubit)) & 1
            target_bit = (state_idx >> (n - 1 - target_qubit)) & 1
            if control_bit == 1 and target_bit == 1:
                self.state[state_idx] *= -1
    
    def swap(self, qubit1: int, qubit2: int) -> None:
        if qubit1 == qubit2:
            return
        if qubit1 < 0 or qubit1 >= self.num_qubits:
            raise ValueError(f"Invalid qubit: {qubit1}")
        if qubit2 < 0 or qubit2 >= self.num_qubits:
            raise ValueError(f"Invalid qubit: {qubit2}")
        
        n = self.num_qubits
        new_state = np.zeros_like(self.state)
        
        for state_idx in range(2 ** n):
            bit1 = (state_idx >> (n - 1 - qubit1)) & 1
            bit2 = (state_idx >> (n - 1 - qubit2)) & 1
            
            new_idx = state_idx
            if bit1 != bit2:
                new_idx ^= (1 << (n - 1 - qubit1))
                new_idx ^= (1 << (n - 1 - qubit2))
            
            new_state[new_idx] = self.state[state_idx]
        
        self.state = new_state
    
    def measure(self, target_qubit: int) -> int:
        if target_qubit < 0 or target_qubit >= self.num_qubits:
            raise ValueError(f"Invalid target qubit: {target_qubit}")
        
        n = self.num_qubits
        prob_0 = 0.0
        
        for state_idx in range(2 ** n):
            if ((state_idx >> (n - 1 - target_qubit)) & 1) == 0:
                prob_0 += abs(self.state[state_idx]) ** 2
        
        result = 0 if np.random.random() < prob_0 else 1
        
        new_state = np.zeros_like(self.state)
        norm_factor = 0.0
        
        for state_idx in range(2 ** n):
            bit = (state_idx >> (n - 1 - target_qubit)) & 1
            if bit == result:
                new_state[state_idx] = self.state[state_idx]
                norm_factor += abs(self.state[state_idx]) ** 2
        
        self.state = new_state / np.sqrt(norm_factor)
        
        return result
    
    def measure_all(self) -> str:
        result = ''
        for i in range(self.num_qubits):
            result += str(self.measure(i))
        return result
    
    def get_probabilities(self) -> Dict[str, float]:
        probabilities = {}
        n = self.num_qubits
        
        for state_idx in range(2 ** n):
            prob = abs(self.state[state_idx]) ** 2
            if prob > 1e-15:
                binary = format(state_idx, f'0{n}b')
                probabilities[binary] = prob
        
        return probabilities
    
    def get_state_vector(self) -> np.ndarray:
        return self.state.copy()
    
    def reset(self) -> None:
        self.state = np.zeros(2 ** self.num_qubits, dtype=complex)
        self.state[0] = 1.0
    
    def print_state(self) -> None:
        print(f"State vector for {self.num_qubits} qubits:")
        for i, amp in enumerate(self.state):
            if abs(amp) > 1e-15:
                binary = format(i, f'0{self.num_qubits}b')
                print(f"  |{binary}>: {amp:.4f}")
    
    def print_probabilities(self) -> None:
        print("Probability distribution:")
        probs = self.get_probabilities()
        for state, prob in sorted(probs.items()):
            print(f"  |{state}>: {prob:.6f}")
