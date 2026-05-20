import numpy as np
from typing import Optional, Tuple, Dict
from pod import PODBasis
from reduced_model import ReducedModel


class ErrorEstimator:
    def __init__(self, basis: PODBasis, reduced_model: Optional[ReducedModel] = None):
        self.basis = basis
        self.reduced_model = reduced_model
        self.errors = None
        self.relative_errors = None
        self._snapshot_shape = None
        self._residual_bounds_cache = {}

    def _flatten_snapshot(self, x: np.ndarray) -> np.ndarray:
        x = np.asarray(x, dtype=self.basis.dtype)
        if x.ndim > 1:
            if self._snapshot_shape is None:
                self._snapshot_shape = x.shape
            return x.flatten()
        return x

    def _reshape_snapshot(self, x_flat: np.ndarray) -> np.ndarray:
        if self._snapshot_shape is not None:
            return x_flat.reshape(self._snapshot_shape)
        return x_flat

    def compute_reconstruction_error(self, x: np.ndarray, 
                                    x_reconstructed: Optional[np.ndarray] = None) -> Tuple[float, float]:
        x_flat = self._flatten_snapshot(x)
        
        if x_reconstructed is None:
            x_reduced = self.basis.project(x_flat)
            x_reconstructed = self.basis.reconstruct(x_reduced)
        else:
            x_reconstructed = self._flatten_snapshot(x_reconstructed)
        
        expected_dim = self.basis.basis.shape[0]
        if x_flat.shape[0] != expected_dim:
            raise ValueError(
                f"Snapshot dimension mismatch: got {x_flat.shape[0]}, "
                f"expected {expected_dim}"
            )
        if x_reconstructed.shape[0] != expected_dim:
            raise ValueError(
                f"Reconstructed snapshot dimension mismatch: got {x_reconstructed.shape[0]}, "
                f"expected {expected_dim}"
            )
        
        error = np.linalg.norm(x_flat - x_reconstructed)
        norm_x = np.linalg.norm(x_flat)
        relative_error = error / norm_x if norm_x > 0 else 0.0
        
        return error, relative_error

    def compute_errors_dataset(self, snapshots: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        snapshots = np.asarray(snapshots, dtype=self.basis.dtype)
        
        if snapshots.ndim == 2:
            n_snapshots, dim = snapshots.shape
            if dim != self.basis.basis.shape[0]:
                snapshots_flat = snapshots.reshape(n_snapshots, -1)
                if snapshots_flat.shape[1] != self.basis.basis.shape[0]:
                    raise ValueError(
                        f"Cannot reshape snapshots to match basis dimension. "
                        f"Basis expects {self.basis.basis.shape[0]}, "
                        f"snapshots have {snapshots_flat.shape[1]} features."
                    )
                snapshots = snapshots_flat
        else:
            n_snapshots = snapshots.shape[0]
            snapshots = snapshots.reshape(n_snapshots, -1)
            if snapshots.shape[1] != self.basis.basis.shape[0]:
                raise ValueError(
                    f"Flattened snapshot dimension mismatch: got {snapshots.shape[1]}, "
                    f"expected {self.basis.basis.shape[0]}"
                )
        
        self.errors = np.zeros(n_snapshots, dtype=self.basis.dtype)
        self.relative_errors = np.zeros(n_snapshots, dtype=self.basis.dtype)
        
        reduced = self.basis.project(snapshots.T)
        reconstructed = self.basis.reconstruct(reduced)
        
        errors = np.linalg.norm(snapshots - reconstructed.T, axis=1)
        norms = np.linalg.norm(snapshots, axis=1)
        
        self.errors = errors
        self.relative_errors = np.where(norms > 0, errors / norms, 0.0)
        
        return self.errors, self.relative_errors

    def residual_based_error(self, operator: np.ndarray, rhs: np.ndarray, 
                             x_reduced: np.ndarray) -> Tuple[float, float]:
        if self.reduced_model is None:
            raise ValueError("Reduced model not provided. Set reduced_model in constructor.")
        
        x_full = self.reduced_model.reconstruct(x_reduced)
        x_full_flat = self._flatten_snapshot(x_full)
        
        rhs_flat = self._flatten_snapshot(rhs)
        
        if operator.ndim != 2:
            raise ValueError(f"Operator must be 2D matrix, got {operator.ndim}D")
        
        expected_dim = self.basis.basis.shape[0]
        if operator.shape[0] != expected_dim or operator.shape[1] != expected_dim:
            raise ValueError(
                f"Operator shape mismatch: got {operator.shape}, "
                f"expected ({expected_dim}, {expected_dim})"
            )
        
        residual = np.linalg.norm(operator @ x_full_flat - rhs_flat)
        norm_rhs = np.linalg.norm(rhs_flat)
        relative_residual = residual / norm_rhs if norm_rhs > 0 else 0.0
        
        return residual, relative_residual

    def get_residual_upper_bound(self, operator: np.ndarray, rhs: np.ndarray,
                                rank: Optional[int] = None, tol: float = 1e-10) -> Dict:
        if self.basis.singular_values is None:
            raise ValueError("Singular values not available. Compute basis first.")
        
        if rank is None:
            rank = self.basis.get_rank()
        
        S = self.basis.singular_values
        r = min(rank, len(S))
        
        sigma_truncated = S[r] if r < len(S) else 0.0
        
        rhs_norm = np.linalg.norm(rhs)
        
        V = self.basis.basis
        P_perp = np.eye(V.shape[0], dtype=self.basis.dtype) - V @ V.T
        rhs_perp_norm = np.linalg.norm(P_perp @ rhs)
        
        try:
            op_norm = np.linalg.norm(operator, 2)
        except:
            op_norm = np.linalg.norm(operator, 'fro')
        
        if sigma_truncated > tol:
            continuity_bound = rhs_norm * op_norm / sigma_truncated
        else:
            continuity_bound = np.inf
        
        truncation_bound_1 = rhs_perp_norm / sigma_truncated if sigma_truncated > tol else np.inf
        truncation_bound_2 = np.sqrt(np.sum(S[r:] ** 2)) if r < len(S) else 0.0
        
        total_bound = continuity_bound + truncation_bound_1 + truncation_bound_2
        
        return {
            'total_upper_bound': total_bound,
            'continuity_bound': continuity_bound,
            'truncation_bound1': truncation_bound_1,
            'truncation_bound2': truncation_bound_2,
            'truncated_singular_value': sigma_truncated,
            'operator_norm': op_norm,
            'rhs_perp_norm': rhs_perp_norm,
            'rhs_norm': rhs_norm,
            'rank': r
        }

    def get_a_posteriori_error_bound(self, residual_norm: float, operator: np.ndarray,
                                    rank: Optional[int] = None, tol: float = 1e-10) -> Dict:
        if self.basis.singular_values is None:
            raise ValueError("Singular values not available. Compute basis first.")
        
        if rank is None:
            rank = self.basis.get_rank()
        
        S = self.basis.singular_values
        r = min(rank, len(S))
        
        sigma_min = S[r - 1] if r > 0 else 0.0
        
        try:
            op_norm_inv = 1.0 / np.linalg.norm(operator, 2)
        except:
            op_norm_inv = 1.0 / (np.linalg.norm(operator, 'fro') + tol)
        
        if sigma_min > tol:
            error_bound = residual_norm * op_norm_inv
        else:
            error_bound = np.inf
        
        return {
            'error_bound': error_bound,
            'residual_norm': residual_norm,
            'sigma_min': sigma_min,
            'operator_inv_norm': op_norm_inv,
            'rank': r
        }

    def get_greedy_error_indicator(self, candidate_snapshot: np.ndarray,
                                  current_rank: Optional[int] = None) -> float:
        x_flat = self._flatten_snapshot(candidate_snapshot)
        
        if current_rank is None:
            current_rank = self.basis.get_rank()
        
        V = self.basis.basis[:, :current_rank]
        P_perp = np.eye(V.shape[0], dtype=self.basis.dtype) - V @ V.T
        
        indicator = np.linalg.norm(P_perp @ x_flat)
        
        return indicator

    def get_error_statistics(self) -> Dict:
        if self.errors is None or self.relative_errors is None:
            raise ValueError("Errors not computed yet. Call compute_errors_dataset() first.")
        
        return {
            'mean_error': float(np.mean(self.errors)),
            'std_error': float(np.std(self.errors)),
            'max_error': float(np.max(self.errors)),
            'min_error': float(np.min(self.errors)),
            'mean_relative_error': float(np.mean(self.relative_errors)),
            'std_relative_error': float(np.std(self.relative_errors)),
            'max_relative_error': float(np.max(self.relative_errors)),
            'min_relative_error': float(np.min(self.relative_errors)),
            'median_relative_error': float(np.median(self.relative_errors))
        }

    def a_posteriori_error(self, mu: np.ndarray, full_solution: np.ndarray, 
                           *args, **kwargs) -> Tuple[float, float]:
        if self.reduced_model is None:
            raise ValueError("Reduced model not provided. Set reduced_model in constructor.")
        
        reduced_solution = self.reduced_model.solve(mu, *args, **kwargs)
        
        full_flat = self._flatten_snapshot(full_solution)
        reduced_flat = self._flatten_snapshot(reduced_solution)
        
        if full_flat.shape[0] != reduced_flat.shape[0]:
            raise ValueError(
                f"Solution dimension mismatch: full solution has {full_flat.shape[0]} dims, "
                f"reduced solution has {reduced_flat.shape[0]} dims"
            )
        
        error = np.linalg.norm(full_flat - reduced_flat)
        norm_full = np.linalg.norm(full_flat)
        relative_error = error / norm_full if norm_full > 0 else 0.0
        
        return error, relative_error

    def estimate_error_bound(self, singular_values: np.ndarray, rank: int, 
                            tol: float = 1e-10) -> float:
        singular_values = np.asarray(singular_values, dtype=self.basis.dtype)
        
        valid_sv = singular_values[singular_values > tol]
        
        if len(valid_sv) <= rank:
            return 0.0
        
        error_bound = np.sqrt(np.sum(valid_sv[rank:] ** 2))
        return float(error_bound)

    def compute_effective_rank(self, threshold: float = 0.99) -> int:
        if self.basis.cumulative_energy is None:
            raise ValueError("Cumulative energy not available. Compute basis first.")
        
        effective_rank = np.argmax(self.basis.cumulative_energy >= threshold) + 1
        return int(effective_rank)

    def compute_convergence_rate(self, max_rank: Optional[int] = None) -> Dict:
        if self.basis.singular_values is None:
            raise ValueError("Singular values not available. Compute basis first.")
        
        S = self.basis.singular_values
        if max_rank is None:
            max_rank = len(S)
        
        errors = np.zeros(max_rank - 1)
        ranks = np.arange(1, max_rank)
        
        for i, r in enumerate(ranks):
            errors[i] = np.sqrt(np.sum(S[r:] ** 2))
        
        log_r = np.log(ranks + 1)
        log_e = np.log(errors + 1e-15)
        
        convergence_rate = -np.polyfit(log_r, log_e, 1)[0]
        
        return {
            'ranks': ranks,
            'errors': errors,
            'convergence_rate': float(convergence_rate),
            'log_r': log_r,
            'log_e': log_e
        }

    def save(self, filename: str) -> None:
        save_data = {
            'errors': self.errors,
            'relative_errors': self.relative_errors,
        }
        if self._snapshot_shape is not None:
            save_data['snapshot_shape'] = np.array(self._snapshot_shape)
        
        np.savez(filename, **save_data)

    def load(self, filename: str) -> None:
        data = np.load(filename, allow_pickle=True)
        self.errors = data['errors']
        self.relative_errors = data['relative_errors']
        if 'snapshot_shape' in data:
            self._snapshot_shape = tuple(data['snapshot_shape'])
