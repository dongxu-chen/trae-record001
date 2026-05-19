import jax
import jax.numpy as jnp
from jax import jit, vmap, grad
import numpy as np
from typing import Optional, List, Tuple, Union, Callable, Dict
from .circuit import ParametricQuantumCircuit, create_hardware_efficient_ansatz
from .jax_core import kronecker_product, _X, _Y, _Z, identity

Array = Union[jnp.ndarray, np.ndarray]

class Hamiltonian:
    def __init__(self, num_qubits: int):
        self.num_qubits = num_qubits
        self.terms: List[Tuple[float, List[Tuple[str, int]]]] = []
        self._matrix: Optional[jnp.ndarray] = None
    
    def add_term(self, coefficient: float, pauli_terms: List[Tuple[str, int]]):
        self.terms.append((coefficient, pauli_terms))
        self._matrix = None
        return self
    
    def get_matrix(self) -> jnp.ndarray:
        if self._matrix is not None:
            return self._matrix
        
        dim = 2 ** self.num_qubits
        H = jnp.zeros((dim, dim), dtype=jnp.complex64)
        
        for coeff, pauli_terms in self.terms:
            term_mat = jnp.eye(1, dtype=jnp.complex64)
            for i in range(self.num_qubits):
                pauli = 'I'
                for p, q in pauli_terms:
                    if q == i:
                        pauli = p
                        break
                
                if pauli == 'X':
                    term_mat = kronecker_product(term_mat, _X)
                elif pauli == 'Y':
                    term_mat = kronecker_product(term_mat, _Y)
                elif pauli == 'Z':
                    term_mat = kronecker_product(term_mat, _Z)
                else:
                    term_mat = kronecker_product(term_mat, identity(2))
            
            H = H + coeff * term_mat
        
        self._matrix = H
        return H
    
    def diagonalize(self) -> Tuple[jnp.ndarray, jnp.ndarray]:
        H = self.get_matrix()
        eigenvalues, eigenvectors = jnp.linalg.eigh(H)
        return eigenvalues, eigenvectors
    
    def get_ground_state_energy(self) -> float:
        eigenvalues, _ = self.diagonalize()
        return float(jnp.real(eigenvalues[0]))
    
    def get_expectation_fn(self) -> Callable:
        H = self.get_matrix()
        return lambda state: jnp.real(jnp.vdot(state, H @ state))

def create_ising_hamiltonian(num_qubits: int, 
                              J: float = 1.0, 
                              h: float = 0.0) -> Hamiltonian:
    H = Hamiltonian(num_qubits)
    for i in range(num_qubits - 1):
        H.add_term(J, [('Z', i), ('Z', i + 1)])
    for i in range(num_qubits):
        H.add_term(-h, [('X', i)])
    return H

def create_heisenberg_hamiltonian(num_qubits: int,
                                   Jx: float = 1.0,
                                   Jy: float = 1.0,
                                   Jz: float = 1.0) -> Hamiltonian:
    H = Hamiltonian(num_qubits)
    for i in range(num_qubits - 1):
        H.add_term(Jx, [('X', i), ('X', i + 1)])
        H.add_term(Jy, [('Y', i), ('Y', i + 1)])
        H.add_term(Jz, [('Z', i), ('Z', i + 1)])
    return H

def create_transverse_field_ising(num_qubits: int,
                                    J: float = 1.0,
                                    g: float = 1.0) -> Hamiltonian:
    H = Hamiltonian(num_qubits)
    for i in range(num_qubits - 1):
        H.add_term(-J, [('Z', i), ('Z', i + 1)])
    for i in range(num_qubits):
        H.add_term(-g, [('X', i)])
    return H

class VQE:
    def __init__(self,
                 ansatz: ParametricQuantumCircuit,
                 hamiltonian: Hamiltonian,
                 learning_rate: float = 0.01):
        self.ansatz = ansatz
        self.hamiltonian = hamiltonian
        self.learning_rate = learning_rate
        self.num_qubits = ansatz.num_qubits
        self.num_params = ansatz.num_params()
        self.H = hamiltonian.get_matrix()
        
        self._energy_fn = jit(self._energy)
        self._grad_fn = jit(grad(self._energy))
    
    def _energy(self, params: Array) -> float:
        state = self.ansatz.run(params)
        return jnp.real(jnp.vdot(state, self.H @ state))
    
    def energy(self, params: Array) -> float:
        return float(self._energy_fn(params))
    
    def gradient(self, params: Array) -> jnp.ndarray:
        return self._grad_fn(params)
    
    def optimize(self,
                 initial_params: Optional[Array] = None,
                 num_steps: int = 100,
                 callback: Optional[Callable[[int, float, jnp.ndarray], None]] = None,
                 optimizer: str = "adam") -> Tuple[jnp.ndarray, List[float]]:
        
        if initial_params is None:
            initial_params = jnp.array(np.random.randn(self.num_params) * 0.1)
        
        params = jnp.array(initial_params, dtype=jnp.float32)
        energy_history = []
        
        if optimizer.lower() == "adam":
            m = jnp.zeros_like(params)
            v = jnp.zeros_like(params)
            beta1 = 0.9
            beta2 = 0.999
            epsilon = 1e-8
            
            for step in range(num_steps):
                energy = float(self._energy_fn(params))
                energy_history.append(energy)
                
                if callback is not None:
                    callback(step, energy, params)
                
                grad = self._grad_fn(params)
                
                m = beta1 * m + (1 - beta1) * grad
                v = beta2 * v + (1 - beta2) * (grad ** 2)
                
                m_hat = m / (1 - beta1 ** (step + 1))
                v_hat = v / (1 - beta2 ** (step + 1))
                
                params = params - self.learning_rate * m_hat / (jnp.sqrt(v_hat) + epsilon)
        
        elif optimizer.lower() == "sgd":
            for step in range(num_steps):
                energy = float(self._energy_fn(params))
                energy_history.append(energy)
                
                if callback is not None:
                    callback(step, energy, params)
                
                grad = self._grad_fn(params)
                params = params - self.learning_rate * grad
        
        else:
            raise ValueError(f"Unknown optimizer: {optimizer}")
        
        return params, energy_history

class VQEWithNaturalGradient(VQE):
    def __init__(self,
                 ansatz: ParametricQuantumCircuit,
                 hamiltonian: Hamiltonian,
                 learning_rate: float = 0.01,
                 regularization: float = 1e-6):
        super().__init__(ansatz, hamiltonian, learning_rate)
        self.regularization = regularization
        self._fim_fn = jit(self._fisher_information_matrix)
    
    def _fisher_information_matrix(self, params: Array) -> jnp.ndarray:
        n_params = len(params)
        F = jnp.zeros((n_params, n_params), dtype=jnp.float32)
        
        state = self.ansatz.run(params)
        
        eps = 1e-4
        for i in range(n_params):
            params_i = params.at[i].add(eps)
            state_i_plus = self.ansatz.run(params_i)
            
            params_i = params.at[i].add(-eps)
            state_i_minus = self.ansatz.run(params_i)
            
            dpsi_i = (state_i_plus - state_i_minus) / (2 * eps)
            
            for j in range(i, n_params):
                params_j = params.at[j].add(eps)
                state_j_plus = self.ansatz.run(params_j)
                
                params_j = params.at[j].add(-eps)
                state_j_minus = self.ansatz.run(params_j)
                
                dpsi_j = (state_j_plus - state_j_minus) / (2 * eps)
                
                F_ij = 4 * jnp.real(jnp.vdot(dpsi_i, dpsi_j))
                F = F.at[i, j].set(F_ij)
                F = F.at[j, i].set(F_ij)
        
        return F
    
    def natural_gradient(self, params: Array) -> jnp.ndarray:
        grad = self._grad_fn(params)
        F = self._fim_fn(params)
        F = F + self.regularization * jnp.eye(len(params))
        natural_grad = jnp.linalg.solve(F, grad)
        return natural_grad
    
    def optimize(self,
                 initial_params: Optional[Array] = None,
                 num_steps: int = 100,
                 callback: Optional[Callable[[int, float, jnp.ndarray], None]] = None) -> Tuple[jnp.ndarray, List[float]]:
        
        if initial_params is None:
            initial_params = jnp.array(np.random.randn(self.num_params) * 0.1)
        
        params = jnp.array(initial_params, dtype=jnp.float32)
        energy_history = []
        
        for step in range(num_steps):
            energy = float(self._energy_fn(params))
            energy_history.append(energy)
            
            if callback is not None:
                callback(step, energy, params)
            
            natural_grad = self.natural_gradient(params)
            params = params - self.learning_rate * natural_grad
        
        return params, energy_history

class BatchVQE:
    def __init__(self,
                 ansatz: ParametricQuantumCircuit,
                 hamiltonians: List[Hamiltonian],
                 learning_rate: float = 0.01):
        self.ansatz = ansatz
        self.hamiltonians = hamiltonians
        self.learning_rate = learning_rate
        self.num_qubits = ansatz.num_qubits
        self.num_params = ansatz.num_params()
        
        self.Hs = jnp.stack([H.get_matrix() for H in hamiltonians])
        
        self._batch_energy_fn = jit(vmap(self._single_energy, in_axes=(0, None)))
        self._avg_energy_fn = jit(self._average_energy)
        self._avg_grad_fn = jit(grad(self._average_energy))
    
    def _single_energy(self, H: Array, params: Array) -> float:
        state = self.ansatz.run(params)
        return jnp.real(jnp.vdot(state, H @ state))
    
    def _average_energy(self, params: Array) -> float:
        energies = vmap(lambda H: self._single_energy(H, params))(self.Hs)
        return jnp.mean(energies)
    
    def energies(self, params: Array) -> jnp.ndarray:
        return self._batch_energy_fn(self.Hs, params)
    
    def optimize(self,
                 initial_params: Optional[Array] = None,
                 num_steps: int = 100,
                 callback: Optional[Callable[[int, float, jnp.ndarray], None]] = None) -> Tuple[jnp.ndarray, List[float]]:
        
        if initial_params is None:
            initial_params = jnp.array(np.random.randn(self.num_params) * 0.1)
        
        params = jnp.array(initial_params, dtype=jnp.float32)
        energy_history = []
        
        m = jnp.zeros_like(params)
        v = jnp.zeros_like(params)
        beta1 = 0.9
        beta2 = 0.999
        epsilon = 1e-8
        
        for step in range(num_steps):
            energy = float(self._avg_energy_fn(params))
            energy_history.append(energy)
            
            if callback is not None:
                callback(step, energy, params)
            
            grad = self._avg_grad_fn(params)
            
            m = beta1 * m + (1 - beta1) * grad
            v = beta2 * v + (1 - beta2) * (grad ** 2)
            
            m_hat = m / (1 - beta1 ** (step + 1))
            v_hat = v / (1 - beta2 ** (step + 1))
            
            params = params - self.learning_rate * m_hat / (jnp.sqrt(v_hat) + epsilon)
        
        return params, energy_history
