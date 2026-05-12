import numpy as np

try:
    from mpi4py import MPI
    MPI_AVAILABLE = True
except ImportError:
    MPI_AVAILABLE = False

class EigenvalueSolver:
    def __init__(self, use_mpi=False):
        self.use_mpi = use_mpi and MPI_AVAILABLE
        if self.use_mpi:
            self.comm = MPI.COMM_WORLD
            self.rank = self.comm.Get_rank()
            self.size = self.comm.Get_size()
        else:
            self.comm = None
            self.rank = 0
            self.size = 1

    def solve(self, hamiltonian):
        eigenvalues, eigenvectors = np.linalg.eigh(hamiltonian)
        return eigenvalues, eigenvectors

    def _distribute_kpoints(self, k_points):
        if not self.use_mpi:
            return k_points, list(range(len(k_points)))
        num_k = len(k_points)
        indices = list(range(num_k))
        local_indices = indices[self.rank::self.size]
        local_k = k_points[local_indices]
        return local_k, local_indices

    def _gather_results(self, local_eigenvalues, local_eigenvectors, local_indices, num_k, num_bands, hamiltonian_size):
        if not self.use_mpi:
            return np.array(local_eigenvalues), np.array(local_eigenvectors)
        eigenvalues_full = np.zeros((num_k, num_bands), dtype=np.float64)
        eigenvectors_full = np.zeros((num_k, hamiltonian_size, hamiltonian_size), dtype=np.complex128)
        sendbuf_evals = np.array(local_eigenvalues, dtype=np.float64)
        sendbuf_evecs = np.array(local_eigenvectors, dtype=np.complex128)
        local_indices_np = np.array(local_indices, dtype=np.int32)
        all_indices = self.comm.allgather(local_indices_np)
        all_evals = self.comm.allgather(sendbuf_evals)
        all_evecs = self.comm.allgather(sendbuf_evecs)
        for idx_list, evals_list, evecs_list in zip(all_indices, all_evals, all_evecs):
            for i, idx in enumerate(idx_list):
                eigenvalues_full[idx] = evals_list[i]
                eigenvectors_full[idx] = evecs_list[i]
        return eigenvalues_full, eigenvectors_full

    def solve_all(self, hamiltonian_builder, k_points):
        num_k = len(k_points)
        local_k, local_indices = self._distribute_kpoints(k_points)
        local_eigenvalues = []
        local_eigenvectors = []
        for k in local_k:
            H = hamiltonian_builder.build(k)
            evals, evecs = self.solve(H)
            local_eigenvalues.append(evals)
            local_eigenvectors.append(evecs)
        if num_k > 0 and local_eigenvalues:
            num_bands = len(local_eigenvalues[0])
            hamiltonian_size = local_eigenvectors[0].shape[0]
        else:
            num_bands = 0
            hamiltonian_size = 8
        eigenvalues, eigenvectors = self._gather_results(
            local_eigenvalues, local_eigenvectors, local_indices,
            num_k, num_bands, hamiltonian_size
        )
        return eigenvalues, eigenvectors

    def get_band_structure(self, hamiltonian_builder, k_points):
        eigenvalues, _ = self.solve_all(hamiltonian_builder, k_points)
        return eigenvalues

    def get_band_structure_with_symmetry(self, hamiltonian_builder, k_points, irreducible_indices, symmetry_map=None):
        irred_k = k_points[irreducible_indices]
        irred_eigenvalues = self.get_band_structure(hamiltonian_builder, irred_k)
        num_k = len(k_points)
        num_bands = irred_eigenvalues.shape[1]
        eigenvalues = np.zeros((num_k, num_bands), dtype=np.float64)
        for idx, irred_idx in enumerate(irreducible_indices):
            eigenvalues[irred_idx] = irred_eigenvalues[idx]
        if symmetry_map is not None:
            for target_idx, source_idx in symmetry_map.items():
                eigenvalues[target_idx] = eigenvalues[source_idx]
        return eigenvalues

    def compute_spin_splitting(self, eigenvalues, hamiltonian_builder=None):
        num_k = eigenvalues.shape[0]
        num_bands = eigenvalues.shape[1]
        if num_bands < 16:
            return None
        splitting = np.zeros((num_k, 8))
        for pair_idx in range(8):
            splitting[:, pair_idx] = eigenvalues[:, 2 * pair_idx + 1] - eigenvalues[:, 2 * pair_idx]
        return splitting

    def analyze_spinor_eigenvectors(self, eigenvectors):
        num_k = eigenvectors.shape[0]
        num_bands = eigenvectors.shape[1]
        spin_expectation = np.zeros((num_k, num_bands, 3))
        sigma_x = np.array([[0, 1], [1, 0]], dtype=np.complex128)
        sigma_y = np.array([[0, -1j], [1j, 0]], dtype=np.complex128)
        sigma_z = np.array([[1, 0], [0, -1]], dtype=np.complex128)
        if num_bands == 16:
            spin_op = np.zeros((16, 16), dtype=np.complex128)
            for orb in range(8):
                spin_op[2*orb:2*orb+2, 2*orb:2*orb+2] = sigma_x
            spin_x_full = spin_op
            spin_op = np.zeros((16, 16), dtype=np.complex128)
            for orb in range(8):
                spin_op[2*orb:2*orb+2, 2*orb:2*orb+2] = sigma_y
            spin_y_full = spin_op
            spin_op = np.zeros((16, 16), dtype=np.complex128)
            for orb in range(8):
                spin_op[2*orb:2*orb+2, 2*orb:2*orb+2] = sigma_z
            spin_z_full = spin_op
            for k_idx in range(num_k):
                for band_idx in range(num_bands):
                    psi = eigenvectors[k_idx, :, band_idx]
                    spin_expectation[k_idx, band_idx, 0] = np.real(np.vdot(psi, spin_x_full @ psi))
                    spin_expectation[k_idx, band_idx, 1] = np.real(np.vdot(psi, spin_y_full @ psi))
                    spin_expectation[k_idx, band_idx, 2] = np.real(np.vdot(psi, spin_z_full @ psi))
        return spin_expectation

    def get_spin_splitting_info(self, eigenvalues, special_point_indices=None):
        num_bands = eigenvalues.shape[1]
        if num_bands < 16:
            return None
        info = {
            'max_splitting': np.max(eigenvalues[:, 1::2] - eigenvalues[:, ::2], axis=0),
            'min_splitting': np.min(eigenvalues[:, 1::2] - eigenvalues[:, ::2], axis=0),
            'avg_splitting': np.mean(eigenvalues[:, 1::2] - eigenvalues[:, ::2], axis=0),
        }
        if special_point_indices is not None:
            special_splitting = {}
            for label, idx in special_point_indices.items():
                if idx < eigenvalues.shape[0]:
                    special_splitting[label] = eigenvalues[idx, 1::2] - eigenvalues[idx, ::2]
            info['special_points'] = special_splitting
        return info

    def is_mpi_enabled(self):
        return self.use_mpi

    def get_mpi_info(self):
        if self.use_mpi:
            return {'rank': self.rank, 'size': self.size}
        return {'rank': 0, 'size': 1}
