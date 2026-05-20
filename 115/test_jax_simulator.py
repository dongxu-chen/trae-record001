import sys
import numpy as np

print("="*60)
print("JAX Quantum Simulator Test")
print("="*60)

try:
    import jax
    import jax.numpy as jnp
    print(f"✓ JAX version: {jax.__version__}")
    print(f"✓ Available devices: {jax.devices()}")
except ImportError as e:
    print(f"✗ JAX import failed: {e}")
    print("Please install JAX:")
    print("  pip install jax jaxlib")
    sys.exit(1)

sys.path.insert(0, '.')

try:
    from quantum_simulator_jax import (
        ParametricQuantumCircuit,
        create_hardware_efficient_ansatz,
        create_transverse_field_ising,
        VQE
    )
    print("✓ All modules imported successfully")
except ImportError as e:
    print(f"✗ Module import failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n1. Testing ParametricQuantumCircuit...")
try:
    qc = ParametricQuantumCircuit(2)
    qc.rx(0)
    qc.ry(1)
    qc.cnot(0, 1)
    print(f"  ✓ Circuit created: {qc}")
    print(f"  ✓ Number of parameters: {qc.num_params()}")
    
    params = jnp.array([0.5, 0.5])
    state = qc.run(params)
    print(f"  ✓ State shape: {state.shape}")
    print(f"  ✓ Probability sum: {jnp.sum(jnp.abs(state)**2):.6f}")
except Exception as e:
    print(f"  ✗ Failed: {e}")
    import traceback
    traceback.print_exc()

print("\n2. Testing Hamiltonian...")
try:
    H = create_transverse_field_ising(num_qubits=3, J=1.0, g=1.0)
    H_mat = H.get_matrix()
    print(f"  ✓ Hamiltonian shape: {H_mat.shape}")
    
    exact_energy = H.get_ground_state_energy()
    print(f"  ✓ Exact ground energy: {exact_energy:.6f}")
except Exception as e:
    print(f"  ✗ Failed: {e}")
    import traceback
    traceback.print_exc()

print("\n3. Testing VQE initialization...")
try:
    num_qubits = 3
    H = create_transverse_field_ising(num_qubits, 1.0, 1.0)
    ansatz = create_hardware_efficient_ansatz(num_qubits, depth=2)
    print(f"  ✓ Ansatz created: {ansatz}")
    
    vqe = VQE(ansatz, H, learning_rate=0.05)
    print(f"  ✓ VQE initialized")
    
    params = jnp.array(np.random.randn(ansatz.num_params()) * 0.1)
    energy = vqe.energy(params)
    print(f"  ✓ Energy computed: {energy:.6f}")
    
    grad = vqe.gradient(params)
    print(f"  ✓ Gradient computed, shape: {grad.shape}")
except Exception as e:
    print(f"  ✗ Failed: {e}")
    import traceback
    traceback.print_exc()

print("\n4. Testing Batch Simulation...")
try:
    num_qubits = 2
    qc = ParametricQuantumCircuit(num_qubits)
    qc.rx(0)
    qc.ry(1)
    qc.cnot(0, 1)
    
    params_batch = jnp.array(np.random.randn(10, qc.num_params()))
    states_batch = qc.run_batch(params_batch)
    print(f"  ✓ Batch states shape: {states_batch.shape}")
except Exception as e:
    print(f"  ✗ Failed: {e}")
    import traceback
    traceback.print_exc()

print("\n5. Testing Quick VQE Optimization...")
try:
    num_qubits = 2
    H = create_transverse_field_ising(num_qubits, 1.0, 1.0)
    ansatz = create_hardware_efficient_ansatz(num_qubits, depth=1)
    vqe = VQE(ansatz, H, learning_rate=0.1)
    
    initial_params = jnp.array(np.random.randn(ansatz.num_params()) * 0.1)
    final_params, history = vqe.optimize(
        initial_params=initial_params,
        num_steps=50,
        optimizer="adam"
    )
    
    initial_energy = history[0]
    final_energy = history[-1]
    exact_energy = H.get_ground_state_energy()
    
    print(f"  ✓ Initial energy: {initial_energy:.6f}")
    print(f"  ✓ Final energy:   {final_energy:.6f}")
    print(f"  ✓ Exact energy:   {exact_energy:.6f}")
    print(f"  ✓ Final error:    {abs(final_energy - exact_energy):.6f}")
    
    if abs(final_energy - exact_energy) < 0.1:
        print("  ✓ Optimization successful!")
    else:
        print("  ⚠ Optimization may need more steps")
except Exception as e:
    print(f"  ✗ Failed: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "="*60)
print("All tests completed!")
print("="*60)
