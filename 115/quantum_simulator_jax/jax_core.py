import jax
import jax.numpy as jnp
from jax import jit, vmap, grad
import numpy as np
from typing import Optional, List, Tuple, Union, Callable

Array = Union[jnp.ndarray, np.ndarray]

def identity(n: int) -> jnp.ndarray:
    return jnp.eye(n, dtype=jnp.complex64)

def kronecker_product(a: jnp.ndarray, b: jnp.ndarray) -> jnp.ndarray:
    return jnp.kron(a, b)

@jit
def apply_gate_statevec(state: jnp.ndarray, gate: jnp.ndarray, 
                        target_qubit: int, num_qubits: int) -> jnp.ndarray:
    state_tensor = state.reshape([2] * num_qubits)
    axes_before = list(range(target_qubit))
    axes_after = list(range(target_qubit + 1, num_qubits))
    new_axes = axes_before + axes_after + [target_qubit]
    state_tensor = jnp.transpose(state_tensor, new_axes)
    original_shape = state_tensor.shape
    state_matrix = state_tensor.reshape(-1, 2)
    result_matrix = state_matrix @ gate.T
    result_tensor = result_matrix.reshape(original_shape)
    reverse_axes = [0] * num_qubits
    for i, axis in enumerate(new_axes):
        reverse_axes[axis] = i
    result_tensor = jnp.transpose(result_tensor, reverse_axes)
    return result_tensor.flatten()

@jit
def apply_two_qubit_gate(state: jnp.ndarray, gate: jnp.ndarray,
                         control_qubit: int, target_qubit: int,
                         num_qubits: int) -> jnp.ndarray:
    state_tensor = state.reshape([2] * num_qubits)
    other_qubits = []
    for q in range(num_qubits):
        if q != control_qubit and q != target_qubit:
            other_qubits.append(q)
    new_axes = other_qubits + [control_qubit, target_qubit]
    state_tensor = jnp.transpose(state_tensor, new_axes)
    original_shape = state_tensor.shape
    other_size = 2 ** len(other_qubits)
    state_matrix = state_tensor.reshape(other_size, 4)
    result_matrix = state_matrix @ gate.T
    result_tensor = result_matrix.reshape(original_shape)
    reverse_axes = [0] * num_qubits
    for i, axis in enumerate(new_axes):
        reverse_axes[axis] = i
    result_tensor = jnp.transpose(result_tensor, reverse_axes)
    return result_tensor.flatten()

@jit
def batch_apply_gate(states: jnp.ndarray, gate: jnp.ndarray,
                     target_qubit: int, num_qubits: int) -> jnp.ndarray:
    return vmap(apply_gate_statevec, in_axes=(0, None, None, None))(
        states, gate, target_qubit, num_qubits
    )

@jit
def batch_apply_two_qubit_gate(states: jnp.ndarray, gate: jnp.ndarray,
                                control_qubit: int, target_qubit: int,
                                num_qubits: int) -> jnp.ndarray:
    return vmap(apply_two_qubit_gate, in_axes=(0, None, None, None, None))(
        states, gate, control_qubit, target_qubit, num_qubits
    )

def get_expectation_value(state: jnp.ndarray, observable: jnp.ndarray) -> complex:
    return jnp.vdot(state, observable @ state)

def get_probabilities(state: jnp.ndarray) -> jnp.ndarray:
    return jnp.abs(state) ** 2

@jit
def batch_expectation(states: jnp.ndarray, observable: jnp.ndarray) -> jnp.ndarray:
    return vmap(get_expectation_value, in_axes=(0, None))(states, observable)

def _Rx(theta: float) -> jnp.ndarray:
    return jnp.array([
        [jnp.cos(theta/2), -1j * jnp.sin(theta/2)],
        [-1j * jnp.sin(theta/2), jnp.cos(theta/2)]
    ], dtype=jnp.complex64)

def _Ry(theta: float) -> jnp.ndarray:
    return jnp.array([
        [jnp.cos(theta/2), -jnp.sin(theta/2)],
        [jnp.sin(theta/2), jnp.cos(theta/2)]
    ], dtype=jnp.complex64)

def _Rz(theta: float) -> jnp.ndarray:
    return jnp.array([
        [jnp.exp(-1j * theta/2), 0],
        [0, jnp.exp(1j * theta/2)]
    ], dtype=jnp.complex64)

def _U3(theta: float, phi: float, lam: float) -> jnp.ndarray:
    return jnp.array([
        [jnp.cos(theta/2), -jnp.exp(1j * lam) * jnp.sin(theta/2)],
        [jnp.exp(1j * phi) * jnp.sin(theta/2), 
         jnp.exp(1j * (phi + lam)) * jnp.cos(theta/2)]
    ], dtype=jnp.complex64)

_RX = jit(_Rx)
_RY = jit(_Ry)
_RZ = jit(_Rz)
_U3 = jit(_U3)

_H = jnp.array([[1, 1], [1, -1]], dtype=jnp.complex64) / jnp.sqrt(2)
_X = jnp.array([[0, 1], [1, 0]], dtype=jnp.complex64)
_Y = jnp.array([[0, -1j], [1j, 0]], dtype=jnp.complex64)
_Z = jnp.array([[1, 0], [0, -1]], dtype=jnp.complex64)
_CNOT = jnp.array([
    [1, 0, 0, 0],
    [0, 1, 0, 0],
    [0, 0, 0, 1],
    [0, 0, 1, 0]
], dtype=jnp.complex64)
_CZ = jnp.array([
    [1, 0, 0, 0],
    [0, 1, 0, 0],
    [0, 0, 1, 0],
    [0, 0, 0, -1]
], dtype=jnp.complex64)
_SWAP = jnp.array([
    [1, 0, 0, 0],
    [0, 0, 1, 0],
    [0, 1, 0, 0],
    [0, 0, 0, 1]
], dtype=jnp.complex64)
