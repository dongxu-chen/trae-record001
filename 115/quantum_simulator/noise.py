import numpy as np
from typing import List, Optional, Tuple


class NoiseChannel:
    def __init__(self, name: str, kraus_operators: List[np.ndarray]):
        self.name = name
        self.kraus_operators = [k.astype(np.complex64) for k in kraus_operators]
        self._verify_completeness()
    
    def _verify_completeness(self):
        sum_k = sum(np.conj(k.T) @ k for k in self.kraus_operators)
        if not np.allclose(sum_k, np.eye(2, dtype=np.complex64)):
            raise ValueError(f"Kraus operators for {self.name} do not satisfy completeness relation")
    
    def apply(self, state: np.ndarray, target_qubit: int, num_qubits: int) -> np.ndarray:
        raise NotImplementedError


class DepolarizingNoise(NoiseChannel):
    def __init__(self, p: float):
        if not 0 <= p <= 1:
            raise ValueError("Probability p must be between 0 and 1")
        
        self.p = p
        I = np.eye(2, dtype=np.complex64)
        X = np.array([[0, 1], [1, 0]], dtype=np.complex64)
        Y = np.array([[0, -1j], [1j, 0]], dtype=np.complex64)
        Z = np.array([[1, 0], [0, -1]], dtype=np.complex64)
        
        kraus = [
            np.sqrt(1 - 3 * p / 4) * I,
            np.sqrt(p / 4) * X,
            np.sqrt(p / 4) * Y,
            np.sqrt(p / 4) * Z
        ]
        
        super().__init__(f"Depolarizing(p={p})", kraus)
    
    def apply(self, state: np.ndarray, target_qubit: int, num_qubits: int) -> np.ndarray:
        return _apply_single_qubit_kraus(state, self.kraus_operators, target_qubit, num_qubits)


class AmplitudeDampingNoise(NoiseChannel):
    def __init__(self, gamma: float):
        if not 0 <= gamma <= 1:
            raise ValueError("Damping parameter gamma must be between 0 and 1")
        
        self.gamma = gamma
        K0 = np.array([[1, 0], [0, np.sqrt(1 - gamma)]], dtype=np.complex64)
        K1 = np.array([[0, np.sqrt(gamma)], [0, 0]], dtype=np.complex64)
        
        super().__init__(f"AmplitudeDamping(gamma={gamma})", [K0, K1])
    
    def apply(self, state: np.ndarray, target_qubit: int, num_qubits: int) -> np.ndarray:
        return _apply_single_qubit_kraus(state, self.kraus_operators, target_qubit, num_qubits)


class PhaseDampingNoise(NoiseChannel):
    def __init__(self, gamma: float):
        if not 0 <= gamma <= 1:
            raise ValueError("Damping parameter gamma must be between 0 and 1")
        
        self.gamma = gamma
        K0 = np.array([[1, 0], [0, np.sqrt(1 - gamma)]], dtype=np.complex64)
        K1 = np.array([[0, 0], [0, np.sqrt(gamma)]], dtype=np.complex64)
        
        super().__init__(f"PhaseDamping(gamma={gamma})", [K0, K1])
    
    def apply(self, state: np.ndarray, target_qubit: int, num_qubits: int) -> np.ndarray:
        return _apply_single_qubit_kraus(state, self.kraus_operators, target_qubit, num_qubits)


def _apply_single_qubit_kraus(state: np.ndarray, kraus_ops: List[np.ndarray], 
                              target_qubit: int, num_qubits: int) -> np.ndarray:
    new_state = np.zeros_like(state)
    target_mask = 1 << (num_qubits - 1 - target_qubit)
    
    for K in kraus_ops:
        temp_state = np.zeros_like(state)
        for i in range(len(state)):
            target_val = (i >> (num_qubits - 1 - target_qubit)) & 1
            
            if target_val == 0:
                j0 = i
                j1 = i | target_mask
                temp_state[j0] += K[0, 0] * state[i]
                temp_state[j1] += K[1, 0] * state[i]
            else:
                j0 = i & ~target_mask
                j1 = i
                temp_state[j0] += K[0, 1] * state[i]
                temp_state[j1] += K[1, 1] * state[i]
        
        new_state += temp_state
    
    return new_state


def apply_noise_to_density_matrix(rho: np.ndarray, kraus_ops: List[np.ndarray],
                                  target_qubit: int, num_qubits: int) -> np.ndarray:
    new_rho = np.zeros_like(rho)
    
    for K in kraus_ops:
        K_big = _expand_single_qubit_operator(K, target_qubit, num_qubits)
        new_rho += K_big @ rho @ np.conj(K_big.T)
    
    return new_rho


def _expand_single_qubit_operator(op: np.ndarray, target_qubit: int, num_qubits: int) -> np.ndarray:
    dim = 2 ** num_qubits
    result = np.zeros((dim, dim), dtype=np.complex64)
    
    target_mask = 1 << (num_qubits - 1 - target_qubit)
    
    for i in range(dim):
        target_val_i = (i >> (num_qubits - 1 - target_qubit)) & 1
        for j in range(dim):
            target_val_j = (j >> (num_qubits - 1 - target_qubit)) & 1
            other_i = i & ~target_mask
            other_j = j & ~target_mask
            
            if other_i == other_j:
                result[i, j] = op[target_val_i, target_val_j]
    
    return result


def state_to_density_matrix(state: np.ndarray) -> np.ndarray:
    return np.outer(state, np.conj(state))


def partial_trace(rho: np.ndarray, keep_qubits: List[int], num_qubits: int) -> np.ndarray:
    keep_qubits = sorted(keep_qubits)
    trace_out = [q for q in range(num_qubits) if q not in keep_qubits]
    
    if not trace_out:
        return rho.copy()
    
    new_shape = [2, 2] * num_qubits
    rho_tensor = rho.reshape(new_shape)
    
    for q in sorted(trace_out, reverse=True):
        idx1 = 2 * q
        idx2 = 2 * q + 1
        rho_tensor = np.trace(rho_tensor, axis1=idx1, axis2=idx2)
    
    keep_dim = 2 ** len(keep_qubits)
    return rho_tensor.reshape(keep_dim, keep_dim)


def get_bloch_coordinates(rho: np.ndarray) -> Tuple[float, float, float]:
    if rho.shape != (2, 2):
        raise ValueError("Density matrix must be 2x2")
    
    X = np.array([[0, 1], [1, 0]], dtype=np.complex64)
    Y = np.array([[0, -1j], [1j, 0]], dtype=np.complex64)
    Z = np.array([[1, 0], [0, -1]], dtype=np.complex64)
    
    x = float(np.real(np.trace(rho @ X)))
    y = float(np.real(np.trace(rho @ Y)))
    z = float(np.real(np.trace(rho @ Z)))
    
    return x, y, z


def state_to_bloch_coordinates(state: np.ndarray) -> Tuple[float, float, float]:
    if len(state) != 2:
        raise ValueError("State must be a single qubit state vector")
    
    rho = state_to_density_matrix(state)
    return get_bloch_coordinates(rho)
