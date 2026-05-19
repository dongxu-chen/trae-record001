import jax
import jax.numpy as jnp
from jax import jit, vmap, grad
import numpy as np
from typing import Optional, List, Tuple, Union, Callable, Dict
from .jax_core import (
    apply_gate_statevec, apply_two_qubit_gate,
    batch_apply_gate, batch_apply_two_qubit_gate,
    get_expectation_value, get_probabilities, batch_expectation,
    _H, _X, _Y, _Z, _CNOT, _CZ, _SWAP, _RX, _RY, _RZ, _U3, identity
)

Array = Union[jnp.ndarray, np.ndarray]

class Gate:
    def __init__(self, name: str, target_qubits: List[int]):
        self.name = name
        self.target_qubits = target_qubits
    
    def get_matrix(self, params: Optional[Array] = None) -> jnp.ndarray:
        raise NotImplementedError

class SingleQubitGate(Gate):
    def __init__(self, name: str, target_qubit: int):
        super().__init__(name, [target_qubit])
        self.target_qubit = target_qubit

class TwoQubitGate(Gate):
    def __init__(self, name: str, control_qubit: int, target_qubit: int):
        super().__init__(name, [control_qubit, target_qubit])
        self.control_qubit = control_qubit
        self.target_qubit = target_qubit

class ParametricSingleQubitGate(SingleQubitGate):
    def __init__(self, name: str, target_qubit: int, param_names: List[str]):
        super().__init__(name, target_qubit)
        self.param_names = param_names
        self.num_params = len(param_names)

class H(SingleQubitGate):
    def __init__(self, target_qubit: int):
        super().__init__("H", target_qubit)
    def get_matrix(self, params: Optional[Array] = None) -> jnp.ndarray:
        return _H

class X(SingleQubitGate):
    def __init__(self, target_qubit: int):
        super().__init__("X", target_qubit)
    def get_matrix(self, params: Optional[Array] = None) -> jnp.ndarray:
        return _X

class Y(SingleQubitGate):
    def __init__(self, target_qubit: int):
        super().__init__("Y", target_qubit)
    def get_matrix(self, params: Optional[Array] = None) -> jnp.ndarray:
        return _Y

class Z(SingleQubitGate):
    def __init__(self, target_qubit: int):
        super().__init__("Z", target_qubit)
    def get_matrix(self, params: Optional[Array] = None) -> jnp.ndarray:
        return _Z

class RX(ParametricSingleQubitGate):
    def __init__(self, target_qubit: int, param_name: str = "theta"):
        super().__init__("RX", target_qubit, [param_name])
    def get_matrix(self, params: Array) -> jnp.ndarray:
        return _RX(params[0])

class RY(ParametricSingleQubitGate):
    def __init__(self, target_qubit: int, param_name: str = "theta"):
        super().__init__("RY", target_qubit, [param_name])
    def get_matrix(self, params: Array) -> jnp.ndarray:
        return _RY(params[0])

class RZ(ParametricSingleQubitGate):
    def __init__(self, target_qubit: int, param_name: str = "theta"):
        super().__init__("RZ", target_qubit, [param_name])
    def get_matrix(self, params: Array) -> jnp.ndarray:
        return _RZ(params[0])

class U3(ParametricSingleQubitGate):
    def __init__(self, target_qubit: int, 
                 param_names: List[str] = ["theta", "phi", "lam"]):
        super().__init__("U3", target_qubit, param_names)
    def get_matrix(self, params: Array) -> jnp.ndarray:
        return _U3(params[0], params[1], params[2])

class CNOT(TwoQubitGate):
    def __init__(self, control_qubit: int, target_qubit: int):
        super().__init__("CNOT", control_qubit, target_qubit)
    def get_matrix(self, params: Optional[Array] = None) -> jnp.ndarray:
        return _CNOT

class CZ(TwoQubitGate):
    def __init__(self, control_qubit: int, target_qubit: int):
        super().__init__("CZ", control_qubit, target_qubit)
    def get_matrix(self, params: Optional[Array] = None) -> jnp.ndarray:
        return _CZ

class SWAP(TwoQubitGate):
    def __init__(self, qubit1: int, qubit2: int):
        super().__init__("SWAP", qubit1, qubit2)
    def get_matrix(self, params: Optional[Array] = None) -> jnp.ndarray:
        return _SWAP

class ParametricQuantumCircuit:
    def __init__(self, num_qubits: int):
        self.num_qubits = num_qubits
        self.gates: List[Gate] = []
        self._parametric_gates: List[ParametricSingleQubitGate] = []
        self._param_indices: List[Tuple[int, int]] = []
        self._total_params = 0
    
    def h(self, qubit: int):
        self.gates.append(H(qubit))
        return self
    
    def x(self, qubit: int):
        self.gates.append(X(qubit))
        return self
    
    def y(self, qubit: int):
        self.gates.append(Y(qubit))
        return self
    
    def z(self, qubit: int):
        self.gates.append(Z(qubit))
        return self
    
    def rx(self, qubit: int, param_name: Optional[str] = None):
        if param_name is None:
            param_name = f"theta_{len(self._parametric_gates)}"
        gate = RX(qubit, param_name)
        self.gates.append(gate)
        self._parametric_gates.append(gate)
        self._param_indices.append((len(self.gates) - 1, 0))
        self._total_params += 1
        return self
    
    def ry(self, qubit: int, param_name: Optional[str] = None):
        if param_name is None:
            param_name = f"theta_{len(self._parametric_gates)}"
        gate = RY(qubit, param_name)
        self.gates.append(gate)
        self._parametric_gates.append(gate)
        self._param_indices.append((len(self.gates) - 1, 0))
        self._total_params += 1
        return self
    
    def rz(self, qubit: int, param_name: Optional[str] = None):
        if param_name is None:
            param_name = f"theta_{len(self._parametric_gates)}"
        gate = RZ(qubit, param_name)
        self.gates.append(gate)
        self._parametric_gates.append(gate)
        self._param_indices.append((len(self.gates) - 1, 0))
        self._total_params += 1
        return self
    
    def u3(self, qubit: int, param_names: Optional[List[str]] = None):
        gate = U3(qubit, param_names)
        self.gates.append(gate)
        self._parametric_gates.append(gate)
        idx = len(self.gates) - 1
        self._param_indices.append((idx, 0))
        self._param_indices.append((idx, 1))
        self._param_indices.append((idx, 2))
        self._total_params += 3
        return self
    
    def cnot(self, control: int, target: int):
        self.gates.append(CNOT(control, target))
        return self
    
    def cz(self, control: int, target: int):
        self.gates.append(CZ(control, target))
        return self
    
    def swap(self, qubit1: int, qubit2: int):
        self.gates.append(SWAP(qubit1, qubit2))
        return self
    
    def num_params(self) -> int:
        return self._total_params
    
    def _apply_gates(self, state: jnp.ndarray, params: Optional[Array] = None) -> jnp.ndarray:
        if params is None:
            params = jnp.zeros(self._total_params)
        
        param_idx = 0
        for gate in self.gates:
            if isinstance(gate, ParametricSingleQubitGate):
                gate_params = params[param_idx:param_idx + gate.num_params]
                gate_mat = gate.get_matrix(gate_params)
                state = apply_gate_statevec(state, gate_mat, gate.target_qubit, self.num_qubits)
                param_idx += gate.num_params
            elif isinstance(gate, SingleQubitGate):
                gate_mat = gate.get_matrix()
                state = apply_gate_statevec(state, gate_mat, gate.target_qubit, self.num_qubits)
            elif isinstance(gate, TwoQubitGate):
                gate_mat = gate.get_matrix()
                state = apply_two_qubit_gate(state, gate_mat, gate.control_qubit, 
                                               gate.target_qubit, self.num_qubits)
        return state
    
    def run(self, params: Optional[Array] = None) -> jnp.ndarray:
        state = jnp.zeros(2 ** self.num_qubits, dtype=jnp.complex64)
        state = state.at[0].set(1.0 + 0.0j)
        return self._apply_gates(state, params)
    
    def run_batch(self, params_batch: Array) -> jnp.ndarray:
        if params_batch.ndim == 1:
            params_batch = params_batch[None, :]
        
        def single_run(params):
            state = jnp.zeros(2 ** self.num_qubits, dtype=jnp.complex64)
            state = state.at[0].set(1.0 + 0.0j)
            return self._apply_gates(state, params)
        
        return vmap(single_run)(params_batch)
    
    def expectation(self, observable: jnp.ndarray, params: Optional[Array] = None) -> float:
        state = self.run(params)
        return jnp.real(get_expectation_value(state, observable))
    
    def expectation_batch(self, observable: jnp.ndarray, params_batch: Array) -> jnp.ndarray:
        states = self.run_batch(params_batch)
        return jnp.real(batch_expectation(states, observable))
    
    def get_gradient_fn(self, observable: jnp.ndarray) -> Callable:
        def loss_fn(params):
            return self.expectation(observable, params)
        return jit(grad(loss_fn))
    
    def get_param_names(self) -> List[str]:
        names = []
        for gate in self._parametric_gates:
            names.extend(gate.param_names)
        return names
    
    def __len__(self) -> int:
        return len(self.gates)
    
    def __repr__(self) -> str:
        return f"ParametricQuantumCircuit({self.num_qubits} qubits, {len(self.gates)} gates, {self._total_params} params)"

def create_ansatz(num_qubits: int, depth: int) -> ParametricQuantumCircuit:
    qc = ParametricQuantumCircuit(num_qubits)
    
    param_idx = 0
    for d in range(depth):
        for q in range(num_qubits):
            qc.ry(q, f"theta_{param_idx}")
            param_idx += 1
        for q in range(num_qubits - 1):
            qc.cnot(q, q + 1)
        if depth > 1:
            for q in range(num_qubits):
                qc.rz(q, f"theta_{param_idx}")
                param_idx += 1
    
    return qc

def create_hardware_efficient_ansatz(num_qubits: int, depth: int, 
                                      entanglement: str = "linear") -> ParametricQuantumCircuit:
    qc = ParametricQuantumCircuit(num_qubits)
    
    param_idx = 0
    for d in range(depth):
        for q in range(num_qubits):
            qc.rx(q, f"rx_{param_idx}")
            param_idx += 1
            qc.rz(q, f"rz_{param_idx}")
            param_idx += 1
        
        if entanglement == "linear":
            for q in range(num_qubits - 1):
                qc.cnot(q, q + 1)
        elif entanglement == "full":
            for i in range(num_qubits):
                for j in range(i + 1, num_qubits):
                    qc.cnot(i, j)
    
    for q in range(num_qubits):
        qc.rx(q, f"rx_{param_idx}")
        param_idx += 1
        qc.rz(q, f"rz_{param_idx}")
        param_idx += 1
    
    return qc
