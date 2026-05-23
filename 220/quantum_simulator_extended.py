import numpy as np
from typing import List, Tuple, Dict, Optional
from collections import deque
from dataclasses import dataclass
from enum import Enum


class GateType(Enum):
    SINGLE = 1
    CNOT = 2
    CZ = 3
    SWAP = 4
    MEASURE = 5
    NOISE = 6


@dataclass
class CircuitGate:
    type: GateType
    name: str
    targets: List[int]
    controls: List[int] = None


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


class NoiseChannel:
    def __init__(self, name: str):
        self.name = name
    
    def apply(self, state: np.ndarray, qubit: int, num_qubits: int) -> np.ndarray:
        raise NotImplementedError


class BitFlipNoise(NoiseChannel):
    def __init__(self, probability: float):
        super().__init__("BitFlip")
        self.probability = probability
    
    def apply(self, state: np.ndarray, qubit: int, num_qubits: int) -> np.ndarray:
        if np.random.random() < self.probability:
            new_state = state.copy()
            n = num_qubits
            size = 2 ** n
            for state_idx in range(size):
                bit = (state_idx >> (n - 1 - qubit)) & 1
                new_idx = state_idx ^ (1 << (n - 1 - qubit))
                new_state[state_idx] = state[new_idx]
            return new_state
        return state


class PhaseFlipNoise(NoiseChannel):
    def __init__(self, probability: float):
        super().__init__("PhaseFlip")
        self.probability = probability
    
    def apply(self, state: np.ndarray, qubit: int, num_qubits: int) -> np.ndarray:
        if np.random.random() < self.probability:
            new_state = state.copy()
            n = num_qubits
            size = 2 ** n
            for state_idx in range(size):
                bit = (state_idx >> (n - 1 - qubit)) & 1
                if bit == 1:
                    new_state[state_idx] *= -1
            return new_state
        return state


class DepolarizingNoise(NoiseChannel):
    def __init__(self, probability: float):
        super().__init__("Depolarizing")
        self.probability = probability
    
    def apply(self, state: np.ndarray, qubit: int, num_qubits: int) -> np.ndarray:
        if np.random.random() < self.probability:
            error_type = np.random.randint(3)
            n = num_qubits
            size = 2 ** n
            
            if error_type == 0:
                new_state = state.copy()
                for state_idx in range(size):
                    new_idx = state_idx ^ (1 << (n - 1 - qubit))
                    new_state[state_idx] = state[new_idx]
                return new_state
            elif error_type == 1:
                new_state = state.copy()
                for state_idx in range(size):
                    bit = (state_idx >> (n - 1 - qubit)) & 1
                    if bit == 1:
                        new_state[state_idx] *= -1
                return new_state
            else:
                new_state = state.copy() * 1j
                for state_idx in range(size):
                    bit = (state_idx >> (n - 1 - qubit)) & 1
                    new_idx = state_idx ^ (1 << (n - 1 - qubit))
                    if bit == 1:
                        new_state[state_idx] = -1j * state[new_idx]
                    else:
                        new_state[state_idx] = 1j * state[new_idx]
                return new_state
        return state


class QuantumCircuitVisualizer:
    def __init__(self, num_qubits: int):
        self.num_qubits = num_qubits
        self.gates: List[CircuitGate] = []
    
    def add_gate(self, gate: CircuitGate):
        self.gates.append(gate)
    
    def _get_gate_symbol(self, gate: CircuitGate, qubit: int) -> str:
        if gate.type == GateType.SINGLE:
            if qubit == gate.targets[0]:
                return f"[{gate.name}]"
            return None
        
        elif gate.type == GateType.CNOT:
            if qubit == gate.controls[0]:
                return " o "
            elif qubit == gate.targets[0]:
                return "[X]"
            return None
        
        elif gate.type == GateType.CZ:
            if qubit == gate.controls[0]:
                return " o "
            elif qubit == gate.targets[0]:
                return " Z "
            return None
        
        elif gate.type == GateType.SWAP:
            if qubit in gate.targets:
                return " x "
            return None
        
        elif gate.type == GateType.MEASURE:
            if qubit == gate.targets[0]:
                return "[M]"
            return None
        
        elif gate.type == GateType.NOISE:
            if qubit == gate.targets[0]:
                return "[~]"
            return None
        
        return None
    
    def _draw_wire(self, qubit: int, gate_symbols: List[str]) -> str:
        wire = f"q{qubit}: "
        prev_symbol = None
        
        for i, symbols in enumerate(gate_symbols):
            symbol = symbols[qubit] if qubit < len(symbols) else None
            
            if symbol is None:
                if prev_symbol and ("o" in prev_symbol or "x" in prev_symbol):
                    wire += "-|-"
                else:
                    wire += "---"
            else:
                wire += symbol
            
            prev_symbol = symbol
            if i < len(gate_symbols) - 1:
                wire += "-"
        
        return wire
    
    def draw(self) -> str:
        if not self.gates:
            return "(Empty circuit)"
        
        gate_symbols = []
        
        for gate in self.gates:
            symbols = [None] * self.num_qubits
            for qubit in range(self.num_qubits):
                sym = self._get_gate_symbol(gate, qubit)
                symbols[qubit] = sym
            gate_symbols.append(symbols)
        
        lines = []
        for qubit in range(self.num_qubits):
            line = self._draw_wire(qubit, gate_symbols)
            lines.append(line)
        
        return "\n".join(lines)


class RepetitionCode:
    def __init__(self, num_repetitions: int = 3):
        if num_repetitions % 2 == 0:
            num_repetitions += 1
        self.num_repetitions = num_repetitions
        self.data_qubit = 0
    
    def encode(self, simulator, data_qubit: int):
        n = simulator.num_qubits
        if n < self.num_repetitions:
            raise ValueError(f"需要至少 {self.num_repetitions} 个量子比特")
        
        self.data_qubit = data_qubit
        
        for i in range(1, self.num_repetitions):
            target_qubit = (data_qubit + i) % n
            simulator.cnot(data_qubit, target_qubit)
    
    def detect_error(self, simulator) -> Tuple[bool, List[int]]:
        n = simulator.num_qubits
        syndrome = []
        
        temp_state = simulator.get_state_vector()
        size = 2 ** n
        
        parity_errors = []
        for i in range(self.num_repetitions - 1):
            q1 = (self.data_qubit + i) % n
            q2 = (self.data_qubit + i + 1) % n
            
            diff_count = 0
            for state_idx in range(size):
                b1 = (state_idx >> (n - 1 - q1)) & 1
                b2 = (state_idx >> (n - 1 - q2)) & 1
                if b1 != b2:
                    diff_count += abs(temp_state[state_idx]) ** 2
            
            if diff_count > 0.5:
                parity_errors.append(i)
        
        return len(parity_errors) > 0, parity_errors
    
    def correct_error(self, simulator, syndrome: List[int]):
        if not syndrome:
            return False
        
        error_qubit = syndrome[0] if len(syndrome) == 1 else syndrome[-1]
        target_qubit = (self.data_qubit + error_qubit + 1) % simulator.num_qubits
        
        simulator.x(target_qubit)
        return True
    
    def decode(self, simulator) -> int:
        temp_state = simulator.get_state_vector()
        n = simulator.num_qubits
        size = 2 ** n
        
        counts = [0, 0]
        for state_idx in range(size):
            votes = []
            for i in range(self.num_repetitions):
                q = (self.data_qubit + i) % n
                bit = (state_idx >> (n - 1 - q)) & 1
                votes.append(bit)
            
            majority = 1 if sum(votes) > len(votes) / 2 else 0
            counts[majority] += abs(temp_state[state_idx]) ** 2
        
        return 0 if counts[0] > counts[1] else 1


class QuantumSimulatorExtended:
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
        
        self.visualizer = QuantumCircuitVisualizer(num_qubits)
        self._alias_table: Optional[AliasTable] = None
        self._probs_cache: Optional[np.ndarray] = None
        self.classical_bits = {}
    
    def _apply_single_qubit_gate(self, gate: np.ndarray, target_qubit: int) -> None:
        full_gate = 1.0
        for i in range(self.num_qubits):
            if i == target_qubit:
                full_gate = np.kron(full_gate, gate)
            else:
                full_gate = np.kron(full_gate, np.eye(2))
        self.state = full_gate @ self.state
        self._alias_table = None
        self._probs_cache = None
    
    def h(self, target_qubit: int) -> None:
        self.visualizer.add_gate(CircuitGate(GateType.SINGLE, 'H', [target_qubit]))
        self._apply_single_qubit_gate(self._gates['H'], target_qubit)
    
    def x(self, target_qubit: int) -> None:
        self.visualizer.add_gate(CircuitGate(GateType.SINGLE, 'X', [target_qubit]))
        self._apply_single_qubit_gate(self._gates['X'], target_qubit)
    
    def y(self, target_qubit: int) -> None:
        self.visualizer.add_gate(CircuitGate(GateType.SINGLE, 'Y', [target_qubit]))
        self._apply_single_qubit_gate(self._gates['Y'], target_qubit)
    
    def z(self, target_qubit: int) -> None:
        self.visualizer.add_gate(CircuitGate(GateType.SINGLE, 'Z', [target_qubit]))
        self._apply_single_qubit_gate(self._gates['Z'], target_qubit)
    
    def s(self, target_qubit: int) -> None:
        self.visualizer.add_gate(CircuitGate(GateType.SINGLE, 'S', [target_qubit]))
        self._apply_single_qubit_gate(self._gates['S'], target_qubit)
    
    def t(self, target_qubit: int) -> None:
        self.visualizer.add_gate(CircuitGate(GateType.SINGLE, 'T', [target_qubit]))
        self._apply_single_qubit_gate(self._gates['T'], target_qubit)
    
    def cnot(self, control_qubit: int, target_qubit: int) -> None:
        self.visualizer.add_gate(CircuitGate(GateType.CNOT, 'CNOT', [target_qubit], [control_qubit]))
        
        n = self.num_qubits
        new_state = self.state.copy()
        for state_idx in range(self.size):
            control_bit = (state_idx >> (n - 1 - control_qubit)) & 1
            if control_bit == 1:
                new_idx = state_idx ^ (1 << (n - 1 - target_qubit))
                new_state[state_idx] = self.state[new_idx]
        self.state = new_state
        self._alias_table = None
        self._probs_cache = None
    
    def cz(self, control_qubit: int, target_qubit: int) -> None:
        self.visualizer.add_gate(CircuitGate(GateType.CZ, 'CZ', [target_qubit], [control_qubit]))
        
        n = self.num_qubits
        for state_idx in range(self.size):
            control_bit = (state_idx >> (n - 1 - control_qubit)) & 1
            target_bit = (state_idx >> (n - 1 - target_qubit)) & 1
            if control_bit == 1 and target_bit == 1:
                self.state[state_idx] *= -1
        self._alias_table = None
        self._probs_cache = None
    
    def swap(self, qubit1: int, qubit2: int) -> None:
        if qubit1 == qubit2:
            return
        self.visualizer.add_gate(CircuitGate(GateType.SWAP, 'SWAP', [qubit1, qubit2]))
        
        n = self.num_qubits
        new_state = np.zeros_like(self.state)
        for state_idx in range(self.size):
            bit1 = (state_idx >> (n - 1 - qubit1)) & 1
            bit2 = (state_idx >> (n - 1 - qubit2)) & 1
            new_idx = state_idx
            if bit1 != bit2:
                new_idx ^= (1 << (n - 1 - qubit1))
                new_idx ^= (1 << (n - 1 - qubit2))
            new_state[new_idx] = self.state[state_idx]
        self.state = new_state
        self._alias_table = None
        self._probs_cache = None
    
    def apply_noise(self, qubit: int, noise_channel: NoiseChannel) -> None:
        self.visualizer.add_gate(CircuitGate(GateType.NOISE, noise_channel.name, [qubit]))
        self.state = noise_channel.apply(self.state, qubit, self.num_qubits)
        self._alias_table = None
        self._probs_cache = None
    
    def bit_flip_noise(self, qubit: int, probability: float) -> None:
        self.apply_noise(qubit, BitFlipNoise(probability))
    
    def phase_flip_noise(self, qubit: int, probability: float) -> None:
        self.apply_noise(qubit, PhaseFlipNoise(probability))
    
    def depolarizing_noise(self, qubit: int, probability: float) -> None:
        self.apply_noise(qubit, DepolarizingNoise(probability))
    
    def _get_probabilities(self) -> np.ndarray:
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
    
    def measure(self, target_qubit: int, classical_bit: int = None) -> int:
        if classical_bit is not None:
            self.visualizer.add_gate(CircuitGate(GateType.MEASURE, 'M', [target_qubit]))
        
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
        
        if classical_bit is not None:
            self.classical_bits[classical_bit] = result
        
        return result
    
    def measure_all(self) -> str:
        result = ''
        for i in range(self.num_qubits):
            self.visualizer.add_gate(CircuitGate(GateType.MEASURE, 'M', [i]))
        
        idx = self.measure_sample()
        return format(idx, f'0{self.num_qubits}b')
    
    def get_probabilities(self) -> Dict[str, float]:
        probabilities = {}
        probs = self._get_probabilities()
        
        for state_idx in range(self.size):
            prob = probs[state_idx]
            if prob > 1e-15:
                binary = format(state_idx, f'0{self.num_qubits}b')
                probabilities[binary] = prob
        
        return probabilities
    
    def get_state_vector(self) -> np.ndarray:
        return self.state.copy()
    
    def reset(self) -> None:
        self.state = np.zeros(self.size, dtype=complex)
        self.state[0] = 1.0
        self.visualizer = QuantumCircuitVisualizer(self.num_qubits)
        self._alias_table = None
        self._probs_cache = None
        self.classical_bits = {}
    
    def print_circuit(self) -> None:
        print("量子电路图:")
        print(self.visualizer.draw())
        print()
    
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
