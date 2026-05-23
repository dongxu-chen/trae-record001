import numpy as np
from typing import List, Tuple, Dict, Optional
from collections import deque


class AliasTable:
    def __init__(self, probabilities: np.ndarray):
        n = len(probabilities)
        self.n = n
        self.prob = np.zeros(n, dtype=np.float64)
        self.alias = np.zeros(n, dtype=np.int64)
        
        scaled_probs = probabilities * n
        small = deque()
        large = deque()
        
        for i, p in enumerate(scaled_probs):
            if p < 1.0:
                small.append(i)
            else:
                large.append(i)
        
        while small and large:
            l = small.popleft()
            g = large.popleft()
            
            self.prob[l] = scaled_probs[l]
            self.alias[l] = g
            
            scaled_probs[g] = scaled_probs[g] + scaled_probs[l] - 1.0
            
            if scaled_probs[g] < 1.0:
                small.append(g)
            else:
                large.append(g)
        
        while large:
            g = large.popleft()
            self.prob[g] = 1.0
        
        while small:
            l = small.popleft()
            self.prob[l] = 1.0
    
    def sample(self) -> int:
        i = np.random.randint(self.n)
        if np.random.random() < self.prob[i]:
            return i
        else:
            return self.alias[i]


class GateSequence:
    def __init__(self, num_qubits: int):
        self.num_qubits = num_qubits
        self.size = 2 ** num_qubits
        self.operations = []
        self.cached_matrix: Optional[np.ndarray] = None
    
    def add_single_qubit_gate(self, gate: np.ndarray, target: int):
        self.operations.append(('single', gate, target))
        self.cached_matrix = None
    
    def add_cnot(self, control: int, target: int):
        self.operations.append(('cnot', control, target))
        self.cached_matrix = None
    
    def add_cz(self, control: int, target: int):
        self.operations.append(('cz', control, target))
        self.cached_matrix = None
    
    def add_swap(self, q1: int, q2: int):
        self.operations.append(('swap', q1, q2))
        self.cached_matrix = None
    
    def _build_matrix(self) -> np.ndarray:
        if self.cached_matrix is not None:
            return self.cached_matrix
        
        result = np.eye(self.size, dtype=complex)
        
        for op in self.operations:
            if op[0] == 'single':
                _, gate, target = op
                full_gate = 1.0
                for i in range(self.num_qubits):
                    if i == target:
                        full_gate = np.kron(full_gate, gate)
                    else:
                        full_gate = np.kron(full_gate, np.eye(2))
                result = full_gate @ result
            
            elif op[0] == 'cnot':
                _, control, target = op
                full_gate = np.eye(self.size, dtype=complex)
                n = self.num_qubits
                for state_idx in range(self.size):
                    control_bit = (state_idx >> (n - 1 - control)) & 1
                    if control_bit == 1:
                        new_state = state_idx ^ (1 << (n - 1 - target))
                        full_gate[state_idx, state_idx] = 0
                        full_gate[state_idx, new_state] = 1
                result = full_gate @ result
            
            elif op[0] == 'cz':
                _, control, target = op
                full_gate = np.eye(self.size, dtype=complex)
                n = self.num_qubits
                for state_idx in range(self.size):
                    control_bit = (state_idx >> (n - 1 - control)) & 1
                    target_bit = (state_idx >> (n - 1 - target)) & 1
                    if control_bit == 1 and target_bit == 1:
                        full_gate[state_idx, state_idx] = -1
                result = full_gate @ result
            
            elif op[0] == 'swap':
                _, q1, q2 = op
                if q1 == q2:
                    continue
                full_gate = np.zeros((self.size, self.size), dtype=complex)
                n = self.num_qubits
                for state_idx in range(self.size):
                    bit1 = (state_idx >> (n - 1 - q1)) & 1
                    bit2 = (state_idx >> (n - 1 - q2)) & 1
                    new_idx = state_idx
                    if bit1 != bit2:
                        new_idx ^= (1 << (n - 1 - q1))
                        new_idx ^= (1 << (n - 1 - q2))
                    full_gate[new_idx, state_idx] = 1
                result = full_gate @ result
        
        self.cached_matrix = result
        return result
    
    def apply(self, state: np.ndarray) -> np.ndarray:
        if not self.operations:
            return state
        
        if len(self.operations) == 1 and self.operations[0][0] != 'single':
            op = self.operations[0]
            n = self.num_qubits
            
            if op[0] == 'cnot':
                _, control, target = op
                new_state = state.copy()
                for state_idx in range(self.size):
                    control_bit = (state_idx >> (n - 1 - control)) & 1
                    if control_bit == 1:
                        new_idx = state_idx ^ (1 << (n - 1 - target))
                        new_state[state_idx] = state[new_idx]
                return new_state
            
            elif op[0] == 'cz':
                _, control, target = op
                new_state = state.copy()
                for state_idx in range(self.size):
                    control_bit = (state_idx >> (n - 1 - control)) & 1
                    target_bit = (state_idx >> (n - 1 - target)) & 1
                    if control_bit == 1 and target_bit == 1:
                        new_state[state_idx] *= -1
                return new_state
            
            elif op[0] == 'swap':
                _, q1, q2 = op
                if q1 == q2:
                    return state
                new_state = np.zeros_like(state)
                for state_idx in range(self.size):
                    bit1 = (state_idx >> (n - 1 - q1)) & 1
                    bit2 = (state_idx >> (n - 1 - q2)) & 1
                    new_idx = state_idx
                    if bit1 != bit2:
                        new_idx ^= (1 << (n - 1 - q1))
                        new_idx ^= (1 << (n - 1 - q2))
                    new_state[new_idx] = state[state_idx]
                return new_state
        
        matrix = self._build_matrix()
        return matrix @ state
    
    def clear(self):
        self.operations = []
        self.cached_matrix = None


class QuantumSimulatorOptimized:
    def __init__(self, num_qubits: int):
        if num_qubits < 1 or num_qubits > 10:
            raise ValueError("Number of qubits must be between 1 and 10")
        
        self.num_qubits = num_qubits
        self.size = 2 ** num_qubits
        self.state = np.zeros(self.size, dtype=complex)
        self.state[0] = 1.0
        
        self._gates = {
            'H': np.array([[1, 1], [1, -1]]) / np.sqrt(2),
            'X': np.array([[0, 1], [1, 0]]),
            'Y': np.array([[0, -1j], [1j, 0]]),
            'Z': np.array([[1, 0], [0, -1]]),
            'S': np.array([[1, 0], [0, 1j]]),
            'T': np.array([[1, 0], [0, np.exp(1j * np.pi / 4)]])
        }
        
        self.gate_sequence = GateSequence(num_qubits)
        self._alias_table: Optional[AliasTable] = None
        self._probs_cache: Optional[np.ndarray] = None
    
    def _flush_gates(self):
        if self.gate_sequence.operations:
            self.state = self.gate_sequence.apply(self.state)
            self.gate_sequence.clear()
            self._alias_table = None
            self._probs_cache = None
    
    def h(self, target_qubit: int) -> None:
        self.gate_sequence.add_single_qubit_gate(self._gates['H'], target_qubit)
    
    def x(self, target_qubit: int) -> None:
        self.gate_sequence.add_single_qubit_gate(self._gates['X'], target_qubit)
    
    def y(self, target_qubit: int) -> None:
        self.gate_sequence.add_single_qubit_gate(self._gates['Y'], target_qubit)
    
    def z(self, target_qubit: int) -> None:
        self.gate_sequence.add_single_qubit_gate(self._gates['Z'], target_qubit)
    
    def s(self, target_qubit: int) -> None:
        self.gate_sequence.add_single_qubit_gate(self._gates['S'], target_qubit)
    
    def t(self, target_qubit: int) -> None:
        self.gate_sequence.add_single_qubit_gate(self._gates['T'], target_qubit)
    
    def cnot(self, control_qubit: int, target_qubit: int) -> None:
        if control_qubit == target_qubit:
            raise ValueError("Control and target qubits must be different")
        if control_qubit < 0 or control_qubit >= self.num_qubits:
            raise ValueError(f"Invalid control qubit: {control_qubit}")
        if target_qubit < 0 or target_qubit >= self.num_qubits:
            raise ValueError(f"Invalid target qubit: {target_qubit}")
        
        self.gate_sequence.add_cnot(control_qubit, target_qubit)
    
    def cz(self, control_qubit: int, target_qubit: int) -> None:
        if control_qubit == target_qubit:
            raise ValueError("Control and target qubits must be different")
        if control_qubit < 0 or control_qubit >= self.num_qubits:
            raise ValueError(f"Invalid control qubit: {control_qubit}")
        if target_qubit < 0 or target_qubit >= self.num_qubits:
            raise ValueError(f"Invalid target qubit: {target_qubit}")
        
        self.gate_sequence.add_cz(control_qubit, target_qubit)
    
    def swap(self, qubit1: int, qubit2: int) -> None:
        if qubit1 < 0 or qubit1 >= self.num_qubits:
            raise ValueError(f"Invalid qubit: {qubit1}")
        if qubit2 < 0 or qubit2 >= self.num_qubits:
            raise ValueError(f"Invalid qubit: {qubit2}")
        
        if qubit1 != qubit2:
            self.gate_sequence.add_swap(qubit1, qubit2)
    
    def _get_probabilities(self) -> np.ndarray:
        self._flush_gates()
        if self._probs_cache is None:
            self._probs_cache = np.abs(self.state) ** 2
        return self._probs_cache
    
    def _build_alias_table(self) -> AliasTable:
        if self._alias_table is None:
            probs = self._get_probabilities()
            self._alias_table = AliasTable(probs)
        return self._alias_table
    
    def measure_sample(self) -> int:
        alias_table = self._build_alias_table()
        return alias_table.sample()
    
    def measure_all_samples(self, num_samples: int) -> np.ndarray:
        alias_table = self._build_alias_table()
        samples = np.array([alias_table.sample() for _ in range(num_samples)])
        return samples
    
    def measure(self, target_qubit: int) -> int:
        self._flush_gates()
        
        if target_qubit < 0 or target_qubit >= self.num_qubits:
            raise ValueError(f"Invalid target qubit: {target_qubit}")
        
        n = self.num_qubits
        prob_0 = 0.0
        
        for state_idx in range(self.size):
            if ((state_idx >> (n - 1 - target_qubit)) & 1) == 0:
                prob_0 += abs(self.state[state_idx]) ** 2
        
        result = 0 if np.random.random() < prob_0 else 1
        
        new_state = np.zeros_like(self.state)
        norm_factor = 0.0
        
        for state_idx in range(self.size):
            bit = (state_idx >> (n - 1 - target_qubit)) & 1
            if bit == result:
                new_state[state_idx] = self.state[state_idx]
                norm_factor += abs(self.state[state_idx]) ** 2
        
        self.state = new_state / np.sqrt(norm_factor)
        self._alias_table = None
        self._probs_cache = None
        
        return result
    
    def measure_all(self) -> str:
        self._flush_gates()
        idx = self.measure_sample()
        return format(idx, f'0{self.num_qubits}b')
    
    def get_probabilities(self) -> Dict[str, float]:
        self._flush_gates()
        probabilities = {}
        probs = self._get_probabilities()
        
        for state_idx in range(self.size):
            prob = probs[state_idx]
            if prob > 1e-15:
                binary = format(state_idx, f'0{self.num_qubits}b')
                probabilities[binary] = prob
        
        return probabilities
    
    def get_state_vector(self) -> np.ndarray:
        self._flush_gates()
        return self.state.copy()
    
    def reset(self) -> None:
        self.state = np.zeros(self.size, dtype=complex)
        self.state[0] = 1.0
        self.gate_sequence.clear()
        self._alias_table = None
        self._probs_cache = None
    
    def print_state(self) -> None:
        self._flush_gates()
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
