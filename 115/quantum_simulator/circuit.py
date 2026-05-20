import numpy as np
from typing import List, Tuple, Union, Optional
from .quantum_state import QuantumState
from .gates import Gate, Hadamard, PauliX, PauliY, PauliZ, CNOT, CZ, Toffoli
from .noise import NoiseChannel, DepolarizingNoise, AmplitudeDampingNoise, PhaseDampingNoise


class QuantumCircuit:
    def __init__(self, num_qubits: int):
        if num_qubits <= 0:
            raise ValueError("Number of qubits must be positive")
        
        self.num_qubits = num_qubits
        self.gates: List[Gate] = []
        self.noise_channels: List[Tuple[NoiseChannel, List[int]]] = []
        self._noise_after_gates = False
        self._initial_state = QuantumState(num_qubits)
    
    def h(self, qubit: int):
        self.gates.append(Hadamard(qubit))
        if self._noise_after_gates and self._default_noise:
            for noise, qubits in self._default_noise:
                if qubit in qubits:
                    self.noise_channels.append((noise, [qubit]))
        return self
    
    def x(self, qubit: int):
        self.gates.append(PauliX(qubit))
        if self._noise_after_gates and self._default_noise:
            for noise, qubits in self._default_noise:
                if qubit in qubits:
                    self.noise_channels.append((noise, [qubit]))
        return self
    
    def y(self, qubit: int):
        self.gates.append(PauliY(qubit))
        if self._noise_after_gates and self._default_noise:
            for noise, qubits in self._default_noise:
                if qubit in qubits:
                    self.noise_channels.append((noise, [qubit]))
        return self
    
    def z(self, qubit: int):
        self.gates.append(PauliZ(qubit))
        if self._noise_after_gates and self._default_noise:
            for noise, qubits in self._default_noise:
                if qubit in qubits:
                    self.noise_channels.append((noise, [qubit]))
        return self
    
    def cnot(self, control: int, target: int):
        self.gates.append(CNOT(control, target))
        if self._noise_after_gates and self._default_noise:
            for noise, qubits in self._default_noise:
                for q in [control, target]:
                    if q in qubits:
                        self.noise_channels.append((noise, [q]))
        return self
    
    def cz(self, control: int, target: int):
        self.gates.append(CZ(control, target))
        if self._noise_after_gates and self._default_noise:
            for noise, qubits in self._default_noise:
                for q in [control, target]:
                    if q in qubits:
                        self.noise_channels.append((noise, [q]))
        return self
    
    def toffoli(self, control1: int, control2: int, target: int):
        self.gates.append(Toffoli(control1, control2, target))
        if self._noise_after_gates and self._default_noise:
            for noise, qubits in self._default_noise:
                for q in [control1, control2, target]:
                    if q in qubits:
                        self.noise_channels.append((noise, [q]))
        return self
    
    def add_gate(self, gate: Gate):
        if any(q >= self.num_qubits for q in gate.target_qubits):
            raise ValueError(f"Gate qubits out of range for {self.num_qubits}-qubit circuit")
        self.gates.append(gate)
        return self
    
    def add_noise(self, noise: NoiseChannel, qubits: Union[int, List[int]]):
        if isinstance(qubits, int):
            qubits = [qubits]
        
        for q in qubits:
            if q >= self.num_qubits:
                raise ValueError(f"Qubit {q} out of range for {self.num_qubits}-qubit circuit")
        
        self.noise_channels.append((noise, qubits))
        return self
    
    def add_depolarizing_noise(self, p: float, qubits: Union[int, List[int]]):
        noise = DepolarizingNoise(p)
        return self.add_noise(noise, qubits)
    
    def add_amplitude_damping_noise(self, gamma: float, qubits: Union[int, List[int]]):
        noise = AmplitudeDampingNoise(gamma)
        return self.add_noise(noise, qubits)
    
    def add_phase_damping_noise(self, gamma: float, qubits: Union[int, List[int]]):
        noise = PhaseDampingNoise(gamma)
        return self.add_noise(noise, qubits)
    
    def enable_noise_after_gates(self, noise: Optional[NoiseChannel] = None, 
                                  qubits: Optional[List[int]] = None):
        self._noise_after_gates = True
        if noise is None:
            noise = DepolarizingNoise(0.01)
        if qubits is None:
            qubits = list(range(self.num_qubits))
        self._default_noise = [(noise, qubits)]
        return self
    
    def disable_noise_after_gates(self):
        self._noise_after_gates = False
        self._default_noise = None
        return self
    
    def set_initial_state(self, state: Union[QuantumState, np.ndarray]):
        if isinstance(state, np.ndarray):
            qs = QuantumState(self.num_qubits)
            qs.set_state_vector(state)
            self._initial_state = qs
        elif isinstance(state, QuantumState):
            if state.num_qubits != self.num_qubits:
                raise ValueError(f"Initial state must have {self.num_qubits} qubits")
            self._initial_state = state
        else:
            raise TypeError("Initial state must be QuantumState or numpy array")
        return self
    
    def run(self, apply_noise: bool = True) -> QuantumState:
        state = self._initial_state.get_state_vector()
        
        noise_idx = 0
        for gate in self.gates:
            state = gate.apply(state, self.num_qubits)
            
            if apply_noise and noise_idx < len(self.noise_channels):
                while noise_idx < len(self.noise_channels):
                    noise, qubits = self.noise_channels[noise_idx]
                    for q in qubits:
                        state = noise.apply(state, q, self.num_qubits)
                    noise_idx += 1
        
        if apply_noise:
            while noise_idx < len(self.noise_channels):
                noise, qubits = self.noise_channels[noise_idx]
                for q in qubits:
                    state = noise.apply(state, q, self.num_qubits)
                noise_idx += 1
        
        result = QuantumState(self.num_qubits)
        result.set_state_vector(state)
        return result
    
    def run_and_measure(self, num_shots: int = 1, apply_noise: bool = True) -> Tuple[List[str], QuantumState]:
        final_state = self.run(apply_noise)
        results = []
        
        for _ in range(num_shots):
            result, _ = final_state.measure()
            results.append(result)
        
        return results, final_state
    
    def measure(self, qubit: Union[int, None] = None, num_shots: int = 1, 
                apply_noise: bool = True) -> Tuple[List[str], QuantumState]:
        final_state = self.run(apply_noise)
        results = []
        
        for _ in range(num_shots):
            result, _ = final_state.measure(qubit)
            results.append(result)
        
        return results, final_state
    
    def get_counts(self, num_shots: int = 1000, apply_noise: bool = True) -> dict:
        results, _ = self.run_and_measure(num_shots, apply_noise)
        counts = {}
        for result in results:
            counts[result] = counts.get(result, 0) + 1
        return counts
    
    def reset(self):
        self.gates = []
        self.noise_channels = []
        self._noise_after_gates = False
        self._initial_state = QuantumState(self.num_qubits)
        return self
    
    def __len__(self) -> int:
        return len(self.gates)
    
    def __str__(self) -> str:
        if not self.gates and not self.noise_channels:
            return f"QuantumCircuit({self.num_qubits} qubits, no gates)"
        
        circuit_str = [f"QuantumCircuit({self.num_qubits} qubits):"]
        for i, gate in enumerate(self.gates):
            circuit_str.append(f"  [{i}] {gate}")
        
        if self.noise_channels:
            circuit_str.append("  Noise channels:")
            for i, (noise, qubits) in enumerate(self.noise_channels):
                circuit_str.append(f"    [{i}] {noise} on qubits {qubits}")
        
        return '\n'.join(circuit_str)
    
    def __repr__(self) -> str:
        return f"QuantumCircuit(num_qubits={self.num_qubits}, num_gates={len(self.gates)}, num_noise={len(self.noise_channels)})"


def create_bell_state() -> QuantumCircuit:
    qc = QuantumCircuit(2)
    qc.h(0)
    qc.cnot(0, 1)
    return qc


def create_ghz_state(num_qubits: int = 3) -> QuantumCircuit:
    qc = QuantumCircuit(num_qubits)
    qc.h(0)
    for i in range(num_qubits - 1):
        qc.cnot(i, i + 1)
    return qc


def create_noisy_bell_state(p_depol: float = 0.05) -> QuantumCircuit:
    qc = QuantumCircuit(2)
    qc.h(0)
    qc.add_depolarizing_noise(p_depol, 0)
    qc.cnot(0, 1)
    qc.add_depolarizing_noise(p_depol, [0, 1])
    return qc
