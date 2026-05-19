import numpy as np
import warnings
from typing import Union, Tuple


class QuantumState:
    def __init__(self, num_qubits: int):
        if num_qubits <= 0:
            raise ValueError("Number of qubits must be positive")
        
        if num_qubits > 25:
            memory_mb = (2 ** num_qubits) * 8 / (1024 * 1024)  # complex64 = 8 bytes
            warnings.warn(
                f"Creating {num_qubits}-qubit state requires ~{memory_mb:.1f} MB of memory. "
                f"For N > 25, consider using sparse representation or distributed computing.",
                UserWarning
            )
        
        self.num_qubits = num_qubits
        self.state = np.zeros(2 ** num_qubits, dtype=np.complex64)
        self.state[0] = 1.0
    
    def get_state_vector(self) -> np.ndarray:
        return self.state.copy()
    
    def set_state_vector(self, state: np.ndarray):
        if state.shape != (2 ** self.num_qubits,):
            raise ValueError(f"State vector must have shape ({2 ** self.num_qubits},)")
        
        norm = np.sum(np.abs(state) ** 2)
        if not np.isclose(norm, 1.0):
            state = state / np.sqrt(norm)
        
        self.state = state.astype(np.complex64)
    
    def get_probabilities(self) -> np.ndarray:
        probs = np.abs(self.state) ** 2
        total = np.sum(probs)
        if not np.isclose(total, 1.0) and total > 0:
            probs = probs / total
        return probs
    
    def get_probability_dict(self) -> dict:
        probs = self.get_probabilities()
        prob_dict = {}
        for i in range(len(probs)):
            if probs[i] > 1e-15:
                bitstring = format(i, f'0{self.num_qubits}b')
                prob_dict[bitstring] = float(probs[i])
        return prob_dict
    
    def get_amplitudes(self) -> dict:
        amp_dict = {}
        for i in range(len(self.state)):
            if abs(self.state[i]) > 1e-15:
                bitstring = format(i, f'0{self.num_qubits}b')
                amp_dict[bitstring] = self.state[i]
        return amp_dict
    
    def measure(self, qubit: Union[int, None] = None) -> Tuple[str, 'QuantumState']:
        if qubit is None:
            return self._measure_all()
        return self._measure_single(qubit)
    
    def _measure_all(self) -> Tuple[str, 'QuantumState']:
        probs = self.get_probabilities()
        result_idx = np.random.choice(len(probs), p=probs)
        bitstring = format(result_idx, f'0{self.num_qubits}b')
        
        new_state = QuantumState(self.num_qubits)
        new_state_vector = np.zeros_like(self.state)
        new_state_vector[result_idx] = 1.0
        new_state.set_state_vector(new_state_vector)
        
        return bitstring, new_state
    
    def _measure_single(self, qubit: int) -> Tuple[str, 'QuantumState']:
        if qubit < 0 or qubit >= self.num_qubits:
            raise ValueError(f"Qubit index must be between 0 and {self.num_qubits - 1}")
        
        mask = 1 << (self.num_qubits - 1 - qubit)
        
        prob_0 = 0.0
        prob_1 = 0.0
        probs = np.abs(self.state) ** 2
        for i in range(len(self.state)):
            if i & mask:
                prob_1 += probs[i]
            else:
                prob_0 += probs[i]
        
        total_prob = prob_0 + prob_1
        if total_prob > 0 and not np.isclose(total_prob, 1.0):
            prob_0 = prob_0 / total_prob
            prob_1 = prob_1 / total_prob
        
        outcome = '1' if np.random.random() < prob_1 else '0'
        
        new_state = self.state.copy()
        for i in range(len(new_state)):
            if outcome == '0' and (i & mask):
                new_state[i] = 0
            elif outcome == '1' and not (i & mask):
                new_state[i] = 0
        
        norm = np.sum(np.abs(new_state) ** 2)
        if norm > 0:
            new_state = new_state / np.sqrt(norm)
        
        collapsed_state = QuantumState(self.num_qubits)
        collapsed_state.set_state_vector(new_state)
        
        return outcome, collapsed_state
    
    def __str__(self) -> str:
        amp_dict = self.get_amplitudes()
        terms = []
        for bitstring, amp in sorted(amp_dict.items()):
            real = float(amp.real)
            imag = float(amp.imag)
            if abs(imag) < 1e-10:
                term = f"{real:.4f}|{bitstring}⟩"
            elif abs(real) < 1e-10:
                sign = '-' if imag < 0 else ''
                term = f"{sign}{abs(imag):.4f}j|{bitstring}⟩"
            else:
                sign = '+' if imag > 0 else '-'
                term = f"({real:.4f}{sign}{abs(imag):.4f}j)|{bitstring}⟩"
            terms.append(term)
        return ' + '.join(terms) if terms else '0'
    
    def __repr__(self) -> str:
        return f"QuantumState({self.num_qubits} qubits)"
