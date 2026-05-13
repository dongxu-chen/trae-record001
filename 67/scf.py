import numpy as np
from atom import get_basis, ATOMIC_NUMBERS
from integral import (
    build_overlap_matrix,
    build_kinetic_matrix,
    build_nuclear_matrix,
    build_eri_matrix,
)


def lda_exchange_energy_density(rho):
    if rho <= 0:
        return 0.0
    Cx = -3.0 / 4.0 * (3.0 / np.pi) ** (1.0 / 3.0)
    return Cx * rho ** (4.0 / 3.0)


def lda_correlation_energy_density(rho):
    if rho <= 0:
        return 0.0
    
    A = 0.0310907
    B = 0.01554535
    C = -0.00244318
    D = 0.00654735
    beta1 = 1.0 / 2.0
    beta2 = 1.0 / 4.0
    
    rs = (3.0 / (4.0 * np.pi * rho)) ** (1.0 / 3.0)
    
    if rs < 1:
        G = A * np.log(rs) + B + C * rs * np.log(rs) + D * rs
    else:
        G = A / (1.0 + beta1 * np.sqrt(rs) + beta2 * rs)
    
    return G


def lda_exchange_potential(rho):
    if rho <= 0:
        return 0.0
    Cx = -3.0 / 4.0 * (3.0 / np.pi) ** (1.0 / 3.0)
    return (4.0 / 3.0) * Cx * rho ** (1.0 / 3.0)


def lda_correlation_potential(rho):
    if rho <= 0:
        return 0.0
    
    A = 0.0310907
    B = 0.01554535
    C = -0.00244318
    D = 0.00654735
    beta1 = 1.0 / 2.0
    beta2 = 1.0 / 4.0
    
    rs = (3.0 / (4.0 * np.pi * rho)) ** (1.0 / 3.0)
    
    if rs < 1:
        G = A * np.log(rs) + B + C * rs * np.log(rs) + D * rs
        dGdrs = A / rs + C * (np.log(rs) + 1.0) + D
    else:
        denominator = 1.0 + beta1 * np.sqrt(rs) + beta2 * rs
        G = A / denominator
        dGdrs = -A * (beta1 / (2.0 * np.sqrt(rs)) + beta2) / denominator ** 2
    
    drsdrho = - (3.0 / (4.0 * np.pi)) ** (1.0 / 3.0) / (3.0 * rho ** (4.0 / 3.0))
    
    return G + rho * dGdrs * drsdrho


class DIIS:
    def __init__(self, max_vectors=6, diis_start=3):
        self.max_vectors = max_vectors
        self.diis_start = diis_start
        self.error_vectors = []
        self.fock_matrices = []
        self.iteration = 0
    
    def reset(self):
        self.error_vectors = []
        self.fock_matrices = []
        self.iteration = 0
    
    def compute_error_vector(self, F, P, S):
        comm = F @ P @ S - S @ P @ F
        return comm.flatten()
    
    def update(self, F, P, S):
        self.iteration += 1
        error = self.compute_error_vector(F, P, S)
        error_norm = np.linalg.norm(error)
        
        self.error_vectors.append(error.copy())
        self.fock_matrices.append(F.copy())
        
        if len(self.error_vectors) > self.max_vectors:
            self.error_vectors.pop(0)
            self.fock_matrices.pop(0)
        
        return error_norm
    
    def extrapolate(self):
        if len(self.error_vectors) < self.diis_start:
            return None
        
        n = len(self.error_vectors)
        
        B = np.zeros((n + 1, n + 1), dtype=np.float64)
        for i in range(n):
            for j in range(n):
                B[i, j] = np.dot(self.error_vectors[i], self.error_vectors[j])
            B[i, n] = -1.0
            B[n, i] = -1.0
        B[n, n] = 0.0
        
        rhs = np.zeros(n + 1, dtype=np.float64)
        rhs[n] = -1.0
        
        try:
            c = np.linalg.solve(B, rhs)
        except np.linalg.LinAlgError:
            return None
        
        c = c[:-1]
        
        F_diis = np.zeros_like(self.fock_matrices[0], dtype=np.float64)
        for i in range(n):
            F_diis += c[i] * self.fock_matrices[i]
        
        return F_diis


def build_density_matrix(C, n_occ, alpha=1.0):
    n_basis = C.shape[0]
    P = np.zeros((n_basis, n_basis), dtype=np.float64)
    for i in range(n_occ):
        P += alpha * np.outer(C[:, i], C[:, i])
    return P


def basis_product(basis1, basis2, point):
    val = 0.0
    n_prim1 = len(basis1.exponents)
    n_prim2 = len(basis2.exponents)
    
    for i in range(n_prim1):
        alpha1 = basis1.exponents[i]
        c1 = basis1.coefficients[i]
        n1 = basis1.norm_constants[i]
        
        for j in range(n_prim2):
            alpha2 = basis2.exponents[j]
            c2 = basis2.coefficients[j]
            n2 = basis2.norm_constants[j]
            
            r1 = point - basis1.center
            r2 = point - basis2.center
            
            g1 = n1 * c1 * np.exp(-alpha1 * np.dot(r1, r1))
            g2 = n2 * c2 * np.exp(-alpha2 * np.dot(r2, r2))
            
            val += g1 * g2
    
    return val


def compute_uks_energy(S, T, V, Pa, Pb, ERI, basis, atoms):
    n_basis = S.shape[0]
    P = Pa + Pb
    
    E_kinetic = np.sum(P * T)
    
    J = np.zeros((n_basis, n_basis), dtype=np.float64)
    for mu in range(n_basis):
        for nu in range(n_basis):
            for lam in range(n_basis):
                for sigma in range(n_basis):
                    J[mu, nu] += P[lam, sigma] * ERI[mu, nu, lam, sigma]
    
    E_coulomb = 0.5 * np.sum(P * J)
    
    E_xc = 0.0
    for i in range(len(atoms)):
        symbol, center = atoms[i]
        rho_a = 0.0
        rho_b = 0.0
        for mu in range(n_basis):
            for nu in range(n_basis):
                bp = basis_product(basis[mu], basis[nu], np.array(center))
                rho_a += Pa[mu, nu] * bp
                rho_b += Pb[mu, nu] * bp
        
        E_xc += (lda_exchange_energy_density(rho_a) + lda_exchange_energy_density(rho_b) +
                lda_correlation_energy_density(rho_a + rho_b))
    
    E_nuclear = 0.0
    for i in range(len(atoms)):
        for j in range(i + 1, len(atoms)):
            Zi = ATOMIC_NUMBERS[atoms[i][0]]
            Zj = ATOMIC_NUMBERS[atoms[j][0]]
            Ri = np.array(atoms[i][1])
            Rj = np.array(atoms[j][1])
            r = np.linalg.norm(Ri - Rj)
            E_nuclear += Zi * Zj / r
    
    E_total = E_kinetic + E_coulomb + E_xc + E_nuclear
    
    return E_total, E_kinetic, E_coulomb, E_xc, E_nuclear


def build_uks_xc_matrices(Pa, Pb, basis, atoms):
    n_basis = len(basis)
    V_xca = np.zeros((n_basis, n_basis), dtype=np.float64)
    V_xcb = np.zeros((n_basis, n_basis), dtype=np.float64)
    
    for i in range(len(atoms)):
        symbol, center = atoms[i]
        center = np.array(center)
        rho_a = 0.0
        rho_b = 0.0
        for mu in range(n_basis):
            for nu in range(n_basis):
                bp = basis_product(basis[mu], basis[nu], center)
                rho_a += Pa[mu, nu] * bp
                rho_b += Pb[mu, nu] * bp
        
        vx_a = lda_exchange_potential(rho_a)
        vx_b = lda_exchange_potential(rho_b)
        vc = lda_correlation_potential(rho_a + rho_b)
        
        vxc_a = vx_a + vc
        vxc_b = vx_b + vc
        
        for mu in range(n_basis):
            for nu in range(n_basis):
                bp = basis_product(basis[mu], basis[nu], center)
                V_xca[mu, nu] += vxc_a * bp
                V_xcb[mu, nu] += vxc_b * bp
    
    return V_xca, V_xcb


def build_uks_fock_matrices(T, V, Pa, Pb, ERI, basis, atoms):
    n_basis = T.shape[0]
    P = Pa + Pb
    
    J = np.zeros((n_basis, n_basis), dtype=np.float64)
    Ka = np.zeros((n_basis, n_basis), dtype=np.float64)
    Kb = np.zeros((n_basis, n_basis), dtype=np.float64)
    
    for mu in range(n_basis):
        for nu in range(n_basis):
            for lam in range(n_basis):
                for sigma in range(n_basis):
                    J[mu, nu] += P[lam, sigma] * ERI[mu, nu, lam, sigma]
                    Ka[mu, nu] += Pa[lam, sigma] * ERI[mu, lam, nu, sigma]
                    Kb[mu, nu] += Pb[lam, sigma] * ERI[mu, lam, nu, sigma]
    
    V_xca, V_xcb = build_uks_xc_matrices(Pa, Pb, basis, atoms)
    
    Fa = T + V + J - Ka + V_xca
    Fb = T + V + J - Kb + V_xcb
    
    return Fa, Fb


def uks_cycle(atoms, charge=0, multiplicity=1, max_iter=100, tol=1e-6, 
               use_diis=True, diis_max_vectors=6, diis_start=3):
    basis = get_basis(atoms)
    n_basis = len(basis)
    
    total_electrons = sum(ATOMIC_NUMBERS[symbol] for symbol, _ in atoms) - charge
    n_alpha = (total_electrons + multiplicity - 1) // 2
    n_beta = total_electrons - n_alpha
    
    print(f"Number of basis functions: {n_basis}")
    print(f"Number of electrons: {total_electrons} (alpha: {n_alpha}, beta: {n_beta})")
    print(f"Multiplicity: {multiplicity}")
    print(f"Using DIIS: {use_diis}")
    print()
    
    S = build_overlap_matrix(basis)
    T = build_kinetic_matrix(basis)
    V = build_nuclear_matrix(basis, atoms)
    ERI = build_eri_matrix(basis)
    
    H_core = T + V
    
    eigvals, eigvecs = np.linalg.eigh(H_core)
    Ca = eigvecs
    Cb = eigvecs.copy()
    
    Pa = build_density_matrix(Ca, n_alpha, 1.0)
    Pb = build_density_matrix(Cb, n_beta, 1.0)
    
    diis_a = DIIS(max_vectors=diis_max_vectors, diis_start=diis_start)
    diis_b = DIIS(max_vectors=diis_max_vectors, diis_start=diis_start)
    
    print("Starting UKS SCF cycle...")
    print(f"{'Iteration':>10} {'Energy (Eh)':>20} {'ΔE':>20} {'Error':>20}")
    print("-" * 75)
    
    E_prev = 0.0
    prev_energy_diff = 0.0
    oscillation_count = 0
    use_damping = True
    damping_factor = 0.7
    
    for iteration in range(max_iter):
        Fa, Fb = build_uks_fock_matrices(T, V, Pa, Pb, ERI, basis, atoms)
        
        error_norm = 0.0
        if use_diis:
            error_a = diis_a.update(Fa, Pa, S)
            error_b = diis_b.update(Fb, Pb, S)
            error_norm = max(error_a, error_b)
            
            if iteration >= diis_start - 1 and len(diis_a.error_vectors) >= diis_a.diis_start:
                Fa_diis = diis_a.extrapolate()
                Fb_diis = diis_b.extrapolate()
                if Fa_diis is not None:
                    Fa = Fa_diis
                if Fb_diis is not None:
                    Fb = Fb_diis
        
        eigvals_a, eigvecs_a = np.linalg.eigh(Fa)
        eigvals_b, eigvecs_b = np.linalg.eigh(Fb)
        Ca = eigvecs_a
        Cb = eigvecs_b
        
        Pa_new = build_density_matrix(Ca, n_alpha, 1.0)
        Pb_new = build_density_matrix(Cb, n_beta, 1.0)
        
        E_total, E_kinetic, E_coulomb, E_xc, E_nuclear = compute_uks_energy(
            S, T, V, Pa_new, Pb_new, ERI, basis, atoms
        )
        
        delta_E = abs(E_total - E_prev)
        delta_P = max(np.linalg.norm(Pa_new - Pa), np.linalg.norm(Pb_new - Pb))
        
        energy_diff = E_total - E_prev
        if iteration > 0 and prev_energy_diff * energy_diff < 0:
            oscillation_count += 1
            if oscillation_count >= 2:
                damping_factor = max(0.3, damping_factor - 0.1)
                oscillation_count = 0
        else:
            if oscillation_count > 0:
                oscillation_count = max(0, oscillation_count - 1)
        
        prev_energy_diff = energy_diff
        
        if use_damping:
            Pa = damping_factor * Pa_new + (1 - damping_factor) * Pa
            Pb = damping_factor * Pb_new + (1 - damping_factor) * Pb
        else:
            Pa = Pa_new.copy()
            Pb = Pb_new.copy()
        
        E_prev = E_total
        
        if iteration >= diis_start and use_diis:
            print(f"{iteration+1:>10} {E_total:>20.10f} {delta_E:>20.10f} {error_norm:>20.10e}")
        else:
            print(f"{iteration+1:>10} {E_total:>20.10f} {delta_E:>20.10f} {'-':>20}")
        
        if delta_E < tol and delta_P < tol:
            print("\nUKS SCF converged!")
            break
    
    else:
        print("\nUKS SCF did not converge within maximum iterations!")
    
    return {
        'energy': E_total,
        'kinetic_energy': E_kinetic,
        'coulomb_energy': E_coulomb,
        'xc_energy': E_xc,
        'nuclear_energy': E_nuclear,
        'orbital_energies_alpha': eigvals_a,
        'orbital_energies_beta': eigvals_b,
        'coefficients_alpha': Ca,
        'coefficients_beta': Cb,
        'density_matrix_alpha': Pa,
        'density_matrix_beta': Pb,
        'overlap_matrix': S,
        'basis': basis,
        'atoms': atoms,
        'n_occ_alpha': n_alpha,
        'n_occ_beta': n_beta,
        'total_electrons': total_electrons,
        'multiplicity': multiplicity,
        'charge': charge,
        'is_uks': True,
    }


def scf_cycle(atoms, charge=0, max_iter=100, tol=1e-6, 
              use_diis=True, diis_max_vectors=6, diis_start=3):
    return uks_cycle(atoms, charge=charge, multiplicity=1, max_iter=max_iter, tol=tol,
                     use_diis=use_diis, diis_max_vectors=diis_max_vectors, diis_start=diis_start)


def run_scf(atoms, charge=0, multiplicity=1, max_iter=100, tol=1e-6,
            use_diis=True, diis_max_vectors=6, diis_start=3, force_uks=False):
    if force_uks:
        return uks_cycle(atoms, charge=charge, multiplicity=multiplicity, max_iter=max_iter, tol=tol,
                         use_diis=use_diis, diis_max_vectors=diis_max_vectors, diis_start=diis_start)
    if multiplicity == 1:
        return scf_cycle(atoms, charge=charge, max_iter=max_iter, tol=tol,
                         use_diis=use_diis, diis_max_vectors=diis_max_vectors, diis_start=diis_start)
    else:
        return uks_cycle(atoms, charge=charge, multiplicity=multiplicity, max_iter=max_iter, tol=tol,
                         use_diis=use_diis, diis_max_vectors=diis_max_vectors, diis_start=diis_start)
