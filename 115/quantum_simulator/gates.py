import numpy as np
import warnings
from typing import List


class Gate:
    def __init__(self, name: str, matrix: np.ndarray, target_qubits: List[int]):
        self.name = name
        self.matrix = matrix.astype(np.complex64)
        self.target_qubits = target_qubits
    
    def apply(self, state: np.ndarray, num_qubits: int) -> np.ndarray:
        raise NotImplementedError
    
    @staticmethod
    def _reshape_state(state: np.ndarray, num_qubits: int) -> np.ndarray:
        shape = [2] * num_qubits
        return state.reshape(shape)
    
    @staticmethod
    def _flatten_state(state: np.ndarray) -> np.ndarray:
        return state.flatten()
    
    def __repr__(self) -> str:
        return f"{self.name}(qubits={self.target_qubits})"


class SingleQubitGate(Gate):
    def __init__(self, name: str, matrix: np.ndarray, target_qubit: int):
        super().__init__(name, matrix, [target_qubit])
        self.target_qubit = target_qubit
    
    def apply(self, state: np.ndarray, num_qubits: int) -> np.ndarray:
        if self.target_qubit >= num_qubits:
            raise ValueError(f"Target qubit {self.target_qubit} out of range for {num_qubits}-qubit state")
        
        new_state = np.zeros_like(state)
        target_mask = 1 << (num_qubits - 1 - self.target_qubit)
        
        for i in range(len(state)):
            target_val = (i >> (num_qubits - 1 - self.target_qubit)) & 1
            
            if target_val == 0:
                j0 = i
                j1 = i | target_mask
                new_state[j0] += self.matrix[0, 0] * state[i]
                new_state[j1] += self.matrix[1, 0] * state[i]
            else:
                j0 = i & ~target_mask
                j1 = i
                new_state[j0] += self.matrix[0, 1] * state[i]
                new_state[j1] += self.matrix[1, 1] * state[i]
        
        return new_state


class CNOT(Gate):
    def __init__(self, control_qubit: int, target_qubit: int):
        super().__init__("CNOT", None, [control_qubit, target_qubit])
        self.control_qubit = control_qubit
        self.target_qubit = target_qubit
    
    def apply(self, state: np.ndarray, num_qubits: int) -> np.ndarray:
        if self.control_qubit >= num_qubits or self.target_qubit >= num_qubits:
            raise ValueError(f"Qubit index out of range for {num_qubits}-qubit state")
        if self.control_qubit == self.target_qubit:
            raise ValueError("Control and target qubits must be different")
        
        new_state = np.zeros_like(state)
        
        for i in range(len(state)):
            control_val = (i >> (num_qubits - 1 - self.control_qubit)) & 1
            
            if control_val:
                target_mask = 1 << (num_qubits - 1 - self.target_qubit)
                j = i ^ target_mask
                new_state[j] = state[i]
            else:
                new_state[i] = state[i]
        
        return new_state


class Hadamard(SingleQubitGate):
    def __init__(self, target_qubit: int):
        H = np.array([[1, 1], [1, -1]], dtype=np.complex64) / np.sqrt(2)
        super().__init__("H", H, target_qubit)


class PauliX(SingleQubitGate):
    def __init__(self, target_qubit: int):
        X = np.array([[0, 1], [1, 0]], dtype=np.complex64)
        super().__init__("X", X, target_qubit)


class PauliY(SingleQubitGate):
    def __init__(self, target_qubit: int):
        Y = np.array([[0, -1j], [1j, 0]], dtype=np.complex64)
        super().__init__("Y", Y, target_qubit)


class PauliZ(SingleQubitGate):
    def __init__(self, target_qubit: int):
        Z = np.array([[1, 0], [0, -1]], dtype=np.complex64)
        super().__init__("Z", Z, target_qubit)


class CZ(Gate):
    def __init__(self, control_qubit: int, target_qubit: int):
        super().__init__("CZ", None, [control_qubit, target_qubit])
        self.control_qubit = control_qubit
        self.target_qubit = target_qubit
    
    def apply(self, state: np.ndarray, num_qubits: int) -> np.ndarray:
        if self.control_qubit >= num_qubits or self.target_qubit >= num_qubits:
            raise ValueError(f"Qubit index out of range for {num_qubits}-qubit state")
        if self.control_qubit == self.target_qubit:
            raise ValueError("Control and target qubits must be different")
        
        state_tensor = self._reshape_state(state, num_qubits)
        
        other_qubits = []
        for q in range(num_qubits):
            if q != self.control_qubit and q != self.target_qubit:
                other_qubits.append(q)
        
        new_axes = other_qubits + [self.control_qubit, self.target_qubit]
        
        if self.control_qubit < self.target_qubit:
            CZ_mat = np.array([
                [1, 0, 0, 0],
                [0, 1, 0, 0],
                [0, 0, 1, 0],
                [0, 0, 0, -1]
            ], dtype=np.complex64)
        else:
            CZ_mat = np.array([
                [1, 0, 0, 0],
                [0, 1, 0, 0],
                [0, 0, 1, 0],
                [0, 0, 0, -1]
            ], dtype=np.complex64)
        
        state_tensor = np.transpose(state_tensor, new_axes)
        
        original_shape = state_tensor.shape
        other_size = 2 ** len(other_qubits)
        state_matrix = state_tensor.reshape(other_size, 4)
        
        result_matrix = state_matrix @ CZ_mat.T
        result_tensor = result_matrix.reshape(original_shape)
        
        reverse_axes = [0] * num_qubits
        for i, axis in enumerate(new_axes):
            reverse_axes[axis] = i
        
        result_tensor = np.transpose(result_tensor, reverse_axes)
        
        return self._flatten_state(result_tensor)


class Toffoli(Gate):
    def __init__(self, control1: int, control2: int, target: int):
        TOFFOLI_mat = np.eye(8, dtype=np.complex64)
        TOFFOLI_mat[6:, 6:] = np.array([[0, 1], [1, 0]], dtype=np.complex64)
        super().__init__("Toffoli", TOFFOLI_mat, [control1, control2, target])
        self.controls = [control1, control2]
        self.target = target
    
    def apply(self, state: np.ndarray, num_qubits: int) -> np.ndarray:
        qubits = self.controls + [self.target]
        if any(q >= num_qubits for q in qubits):
            raise ValueError(f"Qubit index out of range for {num_qubits}-qubit state")
        if len(set(qubits)) != 3:
            raise ValueError("All qubits must be distinct")
        
        state_tensor = self._reshape_state(state, num_qubits)
        
        other_qubits = []
        for q in range(num_qubits):
            if q not in qubits:
                other_qubits.append(q)
        
        new_axes = other_qubits + qubits
        state_tensor = np.transpose(state_tensor, new_axes)
        
        original_shape = state_tensor.shape
        other_size = 2 ** len(other_qubits)
        state_matrix = state_tensor.reshape(other_size, 8)
        
        result_matrix = state_matrix @ self.matrix.T
        result_tensor = result_matrix.reshape(original_shape)
        
        reverse_axes = [0] * num_qubits
        for i, axis in enumerate(new_axes):
            reverse_axes[axis] = i
        
        result_tensor = np.transpose(result_tensor, reverse_axes)
        
        return self._flatten_state(result_tensor)
