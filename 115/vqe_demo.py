import numpy as np
import matplotlib.pyplot as plt
try:
    import jax
    import jax.numpy as jnp
    print(f"JAX version: {jax.__version__}")
    print(f"Available devices: {jax.devices()}")
except ImportError:
    print("JAX not available! Please install JAX first.")
    print("For CPU: pip install jax jaxlib")
    print("For GPU: see https://github.com/google/jax#installation")
    exit(1)

import sys
sys.path.insert(0, '.')

from quantum_simulator_jax import (
    ParametricQuantumCircuit,
    create_hardware_efficient_ansatz,
    create_transverse_field_ising,
    create_ising_hamiltonian,
    VQE
)

print("\n" + "="*70)
print("JAX Quantum Simulator - VQE Demo")
print("="*70)

def demo_1_basic_circuit():
    print("\n1. Basic Parametric Circuit Demo")
    print("-"*50)
    
    qc = ParametricQuantumCircuit(2)
    qc.rx(0)
    qc.ry(1)
    qc.cnot(0, 1)
    
    print(f"Circuit: {qc}")
    print(f"Number of parameters: {qc.num_params()}")
    
    params = jnp.array([np.pi/4, np.pi/2])
    state = qc.run(params)
    
    print(f"Final state shape: {state.shape}")
    print(f"First few amplitudes: {state[:4]}")
    
    probs = jnp.abs(state)**2
    print(f"Probabilities sum: {jnp.sum(probs):.6f}")
    
    return qc

def demo_2_vqe_ising():
    print("\n2. VQE: Transverse Field Ising Model")
    print("-"*50)
    
    num_qubits = 3
    J = 1.0
    g = 1.0
    
    H = create_transverse_field_ising(num_qubits, J, g)
    print(f"Hamiltonian shape: {H.get_matrix().shape}")
    
    exact_energy = H.get_ground_state_energy()
    print(f"Exact ground state energy: {exact_energy:.6f}")
    
    ansatz = create_hardware_efficient_ansatz(num_qubits, depth=2, entanglement="linear")
    print(f"Ansatz: {ansatz}")
    print(f"Number of parameters: {ansatz.num_params()}")
    
    vqe = VQE(ansatz, H, learning_rate=0.05)
    
    initial_params = jnp.array(np.random.randn(ansatz.num_params()) * 0.1)
    print(f"Initial parameters shape: {initial_params.shape}")
    initial_energy = vqe.energy(initial_params)
    print(f"Initial energy: {initial_energy:.6f}")
    
    energy_history = []
    
    def callback(step, energy, params):
        energy_history.append(energy)
        if step % 20 == 0:
            print(f"Step {step:4d}: Energy = {energy:.6f}")
    
    print("\nStarting optimization...")
    final_params, history = vqe.optimize(
        initial_params=initial_params,
        num_steps=200,
        callback=callback,
        optimizer="adam"
    )
    
    final_energy = vqe.energy(final_params)
    print(f"\nFinal energy: {final_energy:.6f}")
    print(f"Error: {abs(final_energy - exact_energy):.6f}")
    
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.plot(history, label='VQE Energy')
    ax.axhline(y=exact_energy, color='r', linestyle='--', label='Exact Energy')
    ax.set_xlabel('Optimization Step')
    ax.set_ylabel('Energy')
    ax.set_title('VQE Optimization Progress')
    ax.legend()
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig('vqe_optimization.png', dpi=150)
    print("\nOptimization plot saved to 'vqe_optimization.png'")
    
    return vqe, final_params, history, exact_energy

def demo_3_batch_simulation():
    print("\n3. Batch Simulation Demo")
    print("-"*50)
    
    num_qubits = 2
    qc = ParametricQuantumCircuit(num_qubits)
    qc.rx(0)
    qc.ry(1)
    qc.cnot(0, 1)
    
    num_batch = 100
    params_batch = jnp.array(np.random.randn(num_batch, qc.num_params()))
    print(f"Batch params shape: {params_batch.shape}")
    
    states_batch = qc.run_batch(params_batch)
    print(f"Batch states shape: {states_batch.shape}")
    
    Z = jnp.array([[1, 0], [0, -1]], dtype=jnp.complex64)
    ZZ = jnp.kron(Z, Z)
    
    energies = qc.expectation_batch(ZZ, params_batch)
    print(f"Batch energies shape: {energies.shape}")
    print(f"Energy range: [{energies.min():.4f}, {energies.max():.4f}]")
    
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.hist(energies, bins=30, alpha=0.7, color='skyblue', edgecolor='black')
    ax.set_xlabel('Energy')
    ax.set_ylabel('Count')
    ax.set_title('Distribution of Energies from Random Parameters')
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig('energy_distribution.png', dpi=150)
    print("Energy distribution plot saved to 'energy_distribution.png'")
    
    return energies

def demo_4_gradient_check():
    print("\n4. Automatic Differentiation Check")
    print("-"*50)
    
    num_qubits = 2
    H = create_transverse_field_ising(num_qubits, 1.0, 1.0)
    ansatz = create_hardware_efficient_ansatz(num_qubits, depth=1)
    vqe = VQE(ansatz, H, learning_rate=0.01)
    
    params = jnp.array(np.random.randn(ansatz.num_params()) * 0.1)
    grad = vqe.gradient(params)
    print(f"Gradient shape: {grad.shape}")
    print(f"Gradient norm: {jnp.linalg.norm(grad):.6f}")
    
    eps = 1e-4
    grad_approx = np.zeros_like(params)
    for i in range(len(params)):
        params_plus = params.at[i].add(eps)
        params_minus = params.at[i].add(-eps)
        E_plus = vqe.energy(params_plus)
        E_minus = vqe.energy(params_minus)
        grad_approx[i] = (E_plus - E_minus) / (2 * eps)
    
    grad_error = jnp.max(jnp.abs(grad - grad_approx))
    print(f"Max gradient error: {grad_error:.2e}")
    if grad_error < 1e-4:
        print("✓ Gradient check passed!")
    else:
        print("✗ Gradient check failed!")

def demo_5_scaling_study():
    print("\n5. Performance Scaling Study")
    print("-"*50)
    
    qubit_counts = [2, 3, 4]
    times = []
    
    import time
    
    for n in qubit_counts:
        H = create_transverse_field_ising(n, 1.0, 1.0)
        ansatz = create_hardware_efficient_ansatz(n, depth=2)
        vqe = VQE(ansatz, H, learning_rate=0.05)
        
        params = jnp.array(np.random.randn(ansatz.num_params()) * 0.1)
        _ = vqe.energy(params)
        
        start = time.time()
        for _ in range(100):
            _ = vqe.energy(params)
        elapsed = time.time() - start
        per_call = elapsed / 100 * 1000
        times.append(per_call)
        
        print(f"{n} qubits: {per_call:.2f} ms per energy evaluation")
    
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.plot(qubit_counts, times, 'o-', linewidth=2, markersize=8)
    ax.set_xlabel('Number of Qubits')
    ax.set_ylabel('Time per Energy Evaluation (ms)')
    ax.set_title('VQE Performance Scaling')
    ax.grid(True, alpha=0.3)
    ax.set_yscale('log')
    plt.tight_layout()
    plt.savefig('scaling_plot.png', dpi=150)
    print("Scaling plot saved to 'scaling_plot.png'")

def main():
    try:
        demo_1_basic_circuit()
        demo_2_vqe_ising()
        demo_3_batch_simulation()
        demo_4_gradient_check()
        demo_5_scaling_study()
        
        print("\n" + "="*70)
        print("All demos completed successfully!")
        print("="*70)
        
    except KeyboardInterrupt:
        print("\nDemo interrupted by user.")
    except Exception as e:
        print(f"\nError during demo: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
