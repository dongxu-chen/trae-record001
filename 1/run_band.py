import numpy as np
import sys
from kpoints import KPointSampler
from hamiltonian import TightBindingHamiltonian
from solver import EigenvalueSolver

def print_separator(char='=', width=60):
    print(char * width)

def print_header(text):
    print_separator()
    print(f"{text:^60}")
    print_separator()

def main():
    use_mpi = '--mpi' in sys.argv
    use_soc = '--soc' in sys.argv
    use_symmetry = '--symmetry' in sys.argv
    solver = EigenvalueSolver(use_mpi=use_mpi)
    mpi_info = solver.get_mpi_info()
    if mpi_info['rank'] != 0:
        sampler = KPointSampler(lattice_constant=5.431)
        hamiltonian = TightBindingHamiltonian(lattice_constant=5.431, use_soc=use_soc)
        k_points = sampler.get_silicon_path(num_points_per_segment=30)
        solver.get_band_structure(hamiltonian, k_points)
        return None
    print_header("Quantum Mechanical Band Structure Calculation")
    print(f"System: Silicon (Si)")
    print(f"Lattice constant: 5.431 Å")
    print(f"Spin-Orbit Coupling (SOC): {'Enabled' if use_soc else 'Disabled'}")
    print(f"MPI parallel: {'Enabled' if solver.is_mpi_enabled() else 'Disabled'}")
    if solver.is_mpi_enabled():
        print(f"MPI processes: {mpi_info['size']}")
    if use_symmetry:
        print(f"Symmetry reduction: Enabled (time-reversal)")
    print()
    print(">> Step 1: Initializing modules...")
    sampler = KPointSampler(lattice_constant=5.431)
    hamiltonian = TightBindingHamiltonian(lattice_constant=5.431, use_soc=use_soc)
    h_size = hamiltonian.get_hamiltonian_size()
    print(f"   [OK] KPointSampler initialized")
    print(f"   [OK] TightBindingHamiltonian initialized")
    print(f"   [OK] EigenvalueSolver initialized")
    print(f"   [INFO] Hamiltonian size: {h_size} x {h_size}")
    if use_soc:
        print(f"   [INFO] SOC parameter λ = 0.044 eV")
    print()
    print(">> Step 2: Generating k-point path...")
    k_points = sampler.get_silicon_path(num_points_per_segment=30)
    num_k = k_points.shape[0]
    path_str = "G → X → U → K → G → L → W → X"
    print(f"   Path: {path_str}")
    print(f"   Total k-points: {num_k}")
    print(f"   Points per segment: 30")
    if use_symmetry:
        irred_indices, symmetry_map = sampler.get_irreducible_kpoints(k_points, use_time_reversal=True)
        num_irred = len(irred_indices)
        reduction = (1 - num_irred / num_k) * 100
        print(f"   Irreducible k-points: {num_irred} ({reduction:.1f}% reduction)")
    print()
    print(">> Step 3: Building Hamiltonians and solving eigenvalues...")
    if use_symmetry:
        eigenvalues = solver.get_band_structure_with_symmetry(
            hamiltonian, k_points, irred_indices, symmetry_map
        )
    else:
        eigenvalues = solver.get_band_structure(hamiltonian, k_points)
    num_bands = eigenvalues.shape[1]
    print(f"   [OK] Computed {num_bands} bands for {num_k} k-points")
    if use_soc:
        print(f"   [INFO] Bands are spin-split due to SOC")
    print()
    print_header("Band Structure Results")
    energy_min = np.min(eigenvalues)
    energy_max = np.max(eigenvalues)
    if use_soc:
        valence_max = np.max(eigenvalues[:, 7])
        conduction_min = np.min(eigenvalues[:, 8])
        vb_idx1, vb_idx2 = 5, 6
        cb_idx1, cb_idx2 = 8, 9
    else:
        valence_max = np.max(eigenvalues[:, 3])
        conduction_min = np.min(eigenvalues[:, 4])
    band_gap = conduction_min - valence_max
    print(f"{'Parameter':<30} {'Value (eV)':>20}")
    print_separator('-')
    print(f"{'Total bands':<30} {num_bands:>20}")
    print(f"{'Total k-points':<30} {num_k:>20}")
    print(f"{'Minimum energy':<30} {energy_min:>18.6f}")
    print(f"{'Maximum energy':<30} {energy_max:>18.6f}")
    print(f"{'Energy range':<30} {(energy_max - energy_min):>18.6f}")
    print_separator('-')
    print(f"{'Valence band maximum (VBM)':<30} {valence_max:>18.6f}")
    print(f"{'Conduction band minimum (CBM)':<30} {conduction_min:>18.6f}")
    print(f"{'Band gap (Eg)':<30} {band_gap:>18.6f}")
    print()
    if use_soc:
        print_header("Spin-Orbit Coupling Analysis")
        spin_splitting = solver.compute_spin_splitting(eigenvalues)
        if spin_splitting is not None:
            print(">> Spin splitting analysis (8 pairs):")
            avg_split = np.mean(spin_splitting, axis=0)
            max_split = np.max(spin_splitting, axis=0)
            print(f"{'Pair':<8} {'Avg Split (meV)':>16} {'Max Split (meV)':>16}")
            print_separator('-')
            for i in range(8):
                print(f"{i+1:<8} {avg_split[i]*1000:>14.2f}   {max_split[i]*1000:>14.2f}")
            print()
            print(">> Spin splitting at high-symmetry points (meV):")
            special_k = sampler.special_points
            for label, k_frac in special_k.items():
                dists = np.linalg.norm(k_points - k_frac, axis=1)
                idx = np.argmin(dists)
                if np.min(dists) < 1e-6:
                    split_at_k = eigenvalues[idx, 1::2] - eigenvalues[idx, ::2]
                    split_str = "  ".join([f"{s*1000:>7.2f}" for s in split_at_k[:4]])
                    print(f"   {label:2s}: {split_str}")
    print()
    print(">> Detailed band energies at high-symmetry points:")
    special_k = sampler.special_points
    for label, k_frac in special_k.items():
        dists = np.linalg.norm(k_points - k_frac, axis=1)
        idx = np.argmin(dists)
        if np.min(dists) < 1e-6:
            energies = eigenvalues[idx]
            if use_soc:
                print(f"   {label:2s}(↑↓): " + "  ".join([f"{e:>8.3f}" for e in energies[:8]]))
                print(f"   {label:2s}(↓↑): " + "  ".join([f"{e:>8.3f}" for e in energies[8:]]))
            else:
                print(f"   {label:2s}: " + "  ".join([f"{e:>8.3f}" for e in energies]))
    print()
    print_header("Calculation Completed Successfully")
    print("   Results are available in the returned dictionary.")
    print("   Usage options:")
    print("      --mpi      : Enable MPI parallel computing")
    print("      --soc      : Enable spin-orbit coupling")
    print("      --symmetry : Enable symmetry reduction")
    print("   Example: python run_band.py --soc --symmetry")
    print_separator()
    results = {
        'k_points': k_points,
        'eigenvalues': eigenvalues,
        'valence_max': valence_max,
        'conduction_min': conduction_min,
        'band_gap': band_gap,
        'num_bands': num_bands,
        'num_k': num_k,
        'energy_range': [energy_min, energy_max],
        'mpi_enabled': solver.is_mpi_enabled(),
        'mpi_size': mpi_info['size'],
        'soc_enabled': use_soc,
        'symmetry_enabled': use_symmetry,
    }
    if use_soc:
        results['spin_splitting'] = spin_splitting
    if use_symmetry:
        results['irreducible_indices'] = irred_indices
        results['symmetry_map'] = symmetry_map
    return results

if __name__ == "__main__":
    main()
