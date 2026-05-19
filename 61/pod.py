import numpy as np
from typing import Optional, Tuple, List, Dict
import warnings


class PODBasis:
    def __init__(self, snapshot_matrix: np.ndarray, dtype: np.dtype = np.float64):
        self.snapshot_matrix = np.asarray(snapshot_matrix, dtype=dtype)
        self.dtype = dtype
        self.basis = None
        self.singular_values = None
        self.cumulative_energy = None
        self._method_used = None
        self._truncation_info = {}

    def compute_basis(self, method: str = 'svd', rank: Optional[int] = None, 
                     energy_threshold: Optional[float] = None,
                     energy_percentage: Optional[float] = None,
                     tol: float = 1e-10, maxiter: int = 1000,
                     random_state: Optional[int] = None,
                     adaptive: bool = False,
                     min_rank: int = 1,
                     max_rank: Optional[int] = None) -> np.ndarray:
        self._method_used = method
        
        if method == 'svd':
            U, S, Vh = self._compute_svd(tol=tol)
        elif method == 'randomized_svd':
            U, S, Vh = self._compute_randomized_svd(
                rank=rank, random_state=random_state, n_iter=maxiter
            )
        elif method == 'correlation':
            U, S = self._compute_correlation_basis(tol=tol, maxiter=maxiter)
            Vh = None
        else:
            raise ValueError(
                f"Unknown method: {method}. Use 'svd', 'randomized_svd', or 'correlation'."
            )
        
        self.singular_values = S
        
        valid_mask = S > tol
        U = U[:, valid_mask]
        S = S[valid_mask]
        
        total_energy = np.sum(S ** 2)
        if total_energy > 0:
            self.cumulative_energy = np.cumsum(S ** 2) / total_energy
        else:
            self.cumulative_energy = np.ones_like(S)
        
        if energy_percentage is not None:
            energy_threshold = energy_percentage / 100.0
        
        selected_rank = self._select_rank(
            U, S, rank=rank, energy_threshold=energy_threshold,
            adaptive=adaptive, min_rank=min_rank, max_rank=max_rank, tol=tol
        )
        
        self.basis = U[:, :selected_rank]
        
        self._truncation_info = {
            'method': method,
            'selected_rank': selected_rank,
            'total_ranks': len(S),
            'energy_captured': self.cumulative_energy[selected_rank - 1] if selected_rank > 0 else 0.0,
            'energy_threshold': energy_threshold,
            'tol': tol
        }
        
        self._validate_basis()
        return self.basis

    def _select_rank(self, U: np.ndarray, S: np.ndarray, rank: Optional[int] = None,
                     energy_threshold: Optional[float] = None, adaptive: bool = False,
                     min_rank: int = 1, max_rank: Optional[int] = None,
                     tol: float = 1e-10) -> int:
        n_modes = len(S)
        
        if max_rank is None:
            max_rank = n_modes
        max_rank = min(max_rank, n_modes)
        min_rank = max(min_rank, 1)
        
        if rank is not None:
            selected_rank = max(min_rank, min(rank, max_rank))
        elif energy_threshold is not None:
            if len(self.cumulative_energy) > 0:
                selected_rank = np.argmax(self.cumulative_energy >= energy_threshold) + 1
                selected_rank = max(min_rank, min(selected_rank, max_rank))
            else:
                selected_rank = min_rank
        elif adaptive:
            selected_rank = self._adaptive_rank_selection(S, min_rank, max_rank, tol)
        else:
            selected_rank = n_modes
        
        return selected_rank

    def _adaptive_rank_selection(self, S: np.ndarray, min_rank: int, max_rank: int,
                                 tol: float = 1e-10) -> int:
        S_squared = S ** 2
        total_energy = np.sum(S_squared)
        
        if total_energy < tol:
            return min_rank
        
        log_S = np.log(S + tol)
        diff_log = np.abs(np.diff(log_S))
        
        if len(diff_log) > 0:
            significant_drop_idx = np.argmax(diff_log) + 1
            selected_rank = max(min_rank, min(significant_drop_idx, max_rank))
        else:
            selected_rank = min_rank
        
        candidates = [selected_rank]
        for threshold in [0.90, 0.95, 0.99, 0.999]:
            r = np.argmax(self.cumulative_energy >= threshold) + 1
            candidates.append(r)
        
        candidate_energies = [self.cumulative_energy[min(r - 1, len(self.cumulative_energy) - 1)] 
                             for r in candidates]
        gains = np.diff(candidate_energies)
        
        if len(gains) > 0:
            dim_gain_idx = np.argmax(gains < 0.01)
            selected_rank = candidates[dim_gain_idx]
        
        selected_rank = max(min_rank, min(selected_rank, max_rank))
        return selected_rank

    def _compute_svd(self, tol: float = 1e-10) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        m, n = self.snapshot_matrix.shape
        
        if m > n:
            U, S, Vh = np.linalg.svd(self.snapshot_matrix, full_matrices=False)
        else:
            U, S, Vh = np.linalg.svd(self.snapshot_matrix, full_matrices=False)
        
        S = np.maximum(S, 0)
        
        return U.astype(self.dtype), S.astype(self.dtype), Vh.astype(self.dtype)

    def _compute_randomized_svd(self, rank: Optional[int] = None, n_oversamples: int = 10,
                                n_iter: int = 5, random_state: Optional[int] = None) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        m, n = self.snapshot_matrix.shape
        
        if rank is None:
            rank = min(m, n) // 2
        
        k = min(rank + n_oversamples, m, n)
        
        if random_state is not None:
            np.random.seed(random_state)
        
        Omega = np.random.randn(n, k).astype(self.dtype)
        Y = self.snapshot_matrix @ Omega
        
        for _ in range(n_iter):
            Y = self.snapshot_matrix @ (self.snapshot_matrix.T @ Y)
        
        Q, _ = np.linalg.qr(Y, mode='reduced')
        
        B = Q.T @ self.snapshot_matrix
        U_small, S, Vh = np.linalg.svd(B, full_matrices=False)
        U = Q @ U_small
        
        return U.astype(self.dtype), S.astype(self.dtype), Vh.astype(self.dtype)

    def _compute_correlation_basis(self, tol: float = 1e-10, maxiter: int = 1000) -> Tuple[np.ndarray, np.ndarray]:
        C = self.snapshot_matrix @ self.snapshot_matrix.T
        
        try:
            eigenvalues, eigenvectors = np.linalg.eigh(C)
        except np.linalg.LinAlgError:
            C_reg = C + tol * np.eye(C.shape[0], dtype=self.dtype)
            eigenvalues, eigenvectors = np.linalg.eigh(C_reg)
        
        idx = eigenvalues.argsort()[::-1]
        eigenvalues = eigenvalues[idx]
        eigenvectors = eigenvectors[:, idx]
        
        eigenvalues = np.maximum(eigenvalues, 0)
        S = np.sqrt(eigenvalues)
        
        valid_mask = S > tol
        eigenvectors = eigenvectors[:, valid_mask]
        S = S[valid_mask]
        
        return eigenvectors.astype(self.dtype), S.astype(self.dtype)

    def _validate_basis(self) -> None:
        if self.basis is None or self.basis.shape[1] == 0:
            warnings.warn("Basis is empty. Try reducing energy_threshold or increasing rank.")
            return
        
        n = self.basis.shape[1]
        if n < min(self.snapshot_matrix.shape):
            warnings.warn(f"Basis rank ({n}) is less than expected. Check SVD convergence.")
        
        ortho_error = np.linalg.norm(self.basis.T @ self.basis - np.eye(n, dtype=self.dtype))
        if ortho_error > 1e-6:
            warnings.warn(f"Basis may not be orthogonal. Orthogonality error: {ortho_error:.2e}")

    def get_rank(self) -> int:
        if self.basis is None:
            raise ValueError("Basis not computed yet. Call compute_basis() first.")
        return self.basis.shape[1]

    def get_energy(self, rank: Optional[int] = None) -> float:
        if self.cumulative_energy is None:
            raise ValueError("Basis not computed yet. Call compute_basis() first.")
        
        if rank is None:
            rank = self.get_rank()
        
        if rank <= 0:
            return 0.0
        
        rank = min(rank, len(self.cumulative_energy))
        return self.cumulative_energy[rank - 1]

    def get_truncation_info(self) -> Dict:
        return self._truncation_info.copy()

    def find_optimal_rank(self, target_energy: float = 0.99,
                         max_rank_penalty: float = 0.001) -> Dict:
        if self.cumulative_energy is None:
            raise ValueError("Cumulative energy not available. Compute basis first.")
        
        n_modes = len(self.cumulative_energy)
        energies = self.cumulative_energy
        ranks = np.arange(1, n_modes + 1)
        
        scores = energies - max_rank_penalty * ranks
        optimal_idx = np.argmax(scores)
        optimal_rank = ranks[optimal_idx]
        
        return {
            'optimal_rank': optimal_rank,
            'energy_at_optimal': energies[optimal_idx],
            'score': scores[optimal_idx],
            'energy_curve': energies,
            'score_curve': scores
        }

    def project(self, x: np.ndarray) -> np.ndarray:
        if self.basis is None:
            raise ValueError("Basis not computed yet. Call compute_basis() first.")
        
        x = np.asarray(x, dtype=self.dtype)
        
        if x.ndim == 1:
            if x.shape[0] != self.basis.shape[0]:
                raise ValueError(
                    f"Vector shape {x.shape} does not match basis shape {self.basis.shape}"
                )
            return self.basis.T @ x
        elif x.ndim == 2:
            if x.shape[0] != self.basis.shape[0]:
                raise ValueError(
                    f"Matrix shape {x.shape} does not match basis shape {self.basis.shape}"
                )
            return self.basis.T @ x
        else:
            raise ValueError(f"Expected 1D or 2D array, got {x.ndim}D")

    def reconstruct(self, x_reduced: np.ndarray) -> np.ndarray:
        if self.basis is None:
            raise ValueError("Basis not computed yet. Call compute_basis() first.")
        
        x_reduced = np.asarray(x_reduced, dtype=self.dtype)
        
        if x_reduced.ndim == 1:
            if x_reduced.shape[0] != self.basis.shape[1]:
                raise ValueError(
                    f"Reduced vector shape {x_reduced.shape} does not match basis rank {self.basis.shape[1]}"
                )
            return self.basis @ x_reduced
        elif x_reduced.ndim == 2:
            if x_reduced.shape[0] != self.basis.shape[1]:
                raise ValueError(
                    f"Reduced matrix shape {x_reduced.shape} does not match basis rank {self.basis.shape[1]}"
                )
            return self.basis @ x_reduced
        else:
            raise ValueError(f"Expected 1D or 2D array, got {x_reduced.ndim}D")

    def incremental_update(self, new_snapshots: np.ndarray, method: str = 'svd',
                          adaptive_rank: bool = True) -> None:
        if self.basis is None:
            self.snapshot_matrix = np.hstack([self.snapshot_matrix, new_snapshots])
            self.compute_basis(method=method, adaptive=adaptive_rank)
            return
        
        new_snapshots = np.asarray(new_snapshots, dtype=self.dtype)
        
        proj_new = self.project(new_snapshots)
        recon_new = self.reconstruct(proj_new)
        residual = new_snapshots - recon_new
        
        Q, _ = np.linalg.qr(residual, mode='reduced')
        
        if Q.shape[1] > 0:
            m1 = self.basis.shape[1]
            m2 = Q.shape[1]
            
            A11 = np.diag(self.singular_values[:m1])
            A12 = self.basis.T @ new_snapshots
            A21 = Q.T @ self.basis @ np.diag(self.singular_values[:m1])
            A22 = Q.T @ new_snapshots
            
            A = np.block([[A11, A12], [A21, A22]])
            
            U_small, S_new, _ = np.linalg.svd(A, full_matrices=False)
            
            self.basis = np.hstack([self.basis, Q]) @ U_small
            self.singular_values = S_new
            
            total_energy = np.sum(S_new ** 2)
            self.cumulative_energy = np.cumsum(S_new ** 2) / total_energy
            
            if adaptive_rank:
                new_rank = self._adaptive_rank_selection(
                    S_new, min_rank=1, max_rank=len(S_new)
                )
                self.basis = self.basis[:, :new_rank]
                self.singular_values = self.singular_values[:new_rank]
            
            self._validate_basis()

    def save(self, filename: str) -> None:
        if self.basis is None:
            raise ValueError("Basis not computed yet. Call compute_basis() first.")
        
        np.savez(
            filename, 
            basis=self.basis, 
            singular_values=self.singular_values,
            cumulative_energy=self.cumulative_energy, 
            method_used=self._method_used,
            truncation_info=np.array(list(self._truncation_info.items()), dtype=object)
        )

    def load(self, filename: str) -> None:
        data = np.load(filename, allow_pickle=True)
        self.basis = data['basis']
        self.singular_values = data['singular_values']
        self.cumulative_energy = data['cumulative_energy']
        if 'method_used' in data:
            self._method_used = str(data['method_used'])
        if 'truncation_info' in data:
            self._truncation_info = dict(data['truncation_info'])
        self.dtype = self.basis.dtype
