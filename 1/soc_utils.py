import numpy as np

def get_pauli_matrices():
    sigma_x = np.array([[0, 1], [1, 0]], dtype=np.complex128)
    sigma_y = np.array([[0, -1j], [1j, 0]], dtype=np.complex128)
    sigma_z = np.array([[1, 0], [0, -1]], dtype=np.complex128)
    return {'x': sigma_x, 'y': sigma_y, 'z': sigma_z}

def get_spin_orbit_matrix(orbitals_per_site=4, lambda_soc=0.044):
    sigma = get_pauli_matrices()
    L = np.zeros((3, orbitals_per_site, orbitals_per_site), dtype=np.complex128)
    sqrt2 = np.sqrt(2)
    L[0, 1, 2] = 1j / sqrt2
    L[0, 2, 1] = -1j / sqrt2
    L[0, 2, 3] = 1j / sqrt2
    L[0, 3, 2] = -1j / sqrt2
    L[1, 1, 2] = -1 / sqrt2
    L[1, 2, 1] = -1 / sqrt2
    L[1, 2, 3] = 1 / sqrt2
    L[1, 3, 2] = 1 / sqrt2
    L[2, 1, 3] = 1j
    L[2, 3, 1] = -1j
    L_soc = np.zeros((orbitals_per_site, orbitals_per_site), dtype=np.complex128)
    for alpha in range(3):
        for beta in range(3):
            L_soc += L[alpha] @ L[beta] * sigma[['x', 'y', 'z'][beta]][alpha, alpha]
    H_soc_onsite = lambda_soc / 2.0 * L_soc
    return H_soc_onsite

def build_soc_hamiltonian(H0, lambda_soc=0.044):
    n_orb = H0.shape[0]
    if n_orb != 8:
        raise ValueError(f"Expected 8 orbitals without spin, got {n_orb}")
    n_orb_spin = 16
    H = np.zeros((n_orb_spin, n_orb_spin), dtype=np.complex128)
    H[:8, :8] = H0
    H[8:, 8:] = H0
    sigma = get_pauli_matrices()
    L = np.zeros((3, 4, 4), dtype=np.complex128)
    sqrt2 = np.sqrt(2)
    L[0, 1, 2] = 1j / sqrt2
    L[0, 2, 1] = -1j / sqrt2
    L[0, 2, 3] = 1j / sqrt2
    L[0, 3, 2] = -1j / sqrt2
    L[1, 1, 2] = -1 / sqrt2
    L[1, 2, 1] = -1 / sqrt2
    L[1, 2, 3] = 1 / sqrt2
    L[1, 3, 2] = 1 / sqrt2
    L[2, 1, 3] = 1j
    L[2, 3, 1] = -1j
    H_soc_atom = np.zeros((8, 8), dtype=np.complex128)
    for alpha in range(3):
        for beta in range(3):
            sigma_ab = sigma[['x', 'y', 'z'][beta]][alpha, alpha]
            for i in range(4):
                for j in range(4):
                    val = L[alpha, i, j] * sigma_ab * lambda_soc / 2.0
                    H_soc_atom[i, j] += val
                    H_soc_atom[i + 4, j + 4] += val
    for i in range(8):
        for j in range(8):
            soc_val = H_soc_atom[i, j]
            H[i, j] += soc_val
            H[i + 8, j + 8] += soc_val
    for a in range(2):
        for b in range(2):
            sigma_ab = 0.0
            if a == 0 and b == 1:
                sigma_ab = 1.0
            elif a == 1 and b == 0:
                sigma_ab = 1.0
            elif a == 0 and b == 0:
                sigma_ab = 1.0
            elif a == 1 and b == 1:
                sigma_ab = -1.0
    return H

def get_si_lambda_soc():
    return 0.044

def get_irreducible_kpoints(k_points, tol=1e-6):
    unique_indices = []
    seen = []
    for i, k in enumerate(k_points):
        is_equiv = False
        for s in seen:
            if np.linalg.norm(k - s) < tol:
                is_equiv = True
                break
            k_neg = -s
            if np.linalg.norm(k - k_neg) < tol:
                is_equiv = True
                break
        if not is_equiv:
            unique_indices.append(i)
            seen.append(k)
    return np.array(unique_indices)

def expand_irreducible_results(irreducible_indices, irreducible_evals, total_num_k, symmetry_map=None):
    num_bands = irreducible_evals.shape[1]
    eigenvalues = np.zeros((total_num_k, num_bands), dtype=np.float64)
    for idx, irred_idx in enumerate(irreducible_indices):
        eigenvalues[irred_idx] = irreducible_evals[idx]
    if symmetry_map is not None:
        for target_idx, source_idx in symmetry_map.items():
            eigenvalues[target_idx] = eigenvalues[source_idx]
    return eigenvalues

def compute_spin_splitting(eigenvalues, num_pairs=4):
    num_k = eigenvalues.shape[0]
    num_bands = eigenvalues.shape[1]
    if num_bands < 2 * num_pairs:
        raise ValueError(f"Need at least {2 * num_pairs} bands for {num_pairs} pairs")
    splitting = np.zeros((num_k, num_pairs))
    for i in range(num_pairs):
        splitting[:, i] = eigenvalues[:, 2 * i + 1] - eigenvalues[:, 2 * i]
    return splitting

def find_degenerate_bands(eigenvalues, tol=1e-4):
    num_k = eigenvalues.shape[0]
    num_bands = eigenvalues.shape[1]
    degenerate_pairs = []
    for k in range(num_k):
        for i in range(num_bands):
            for j in range(i + 1, num_bands):
                if abs(eigenvalues[k, i] - eigenvalues[k, j]) < tol:
                    degenerate_pairs.append((k, i, j))
    return degenerate_pairs
