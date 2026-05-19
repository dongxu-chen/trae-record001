import numpy as np
from typing import Callable, Optional, List, Union
from pod import PODBasis


class ReducedModel:
    def __init__(self, basis: PODBasis, full_model: Optional[Callable] = None):
        self.basis = basis
        self.full_model = full_model
        self.reduced_solutions = None
        self.full_solutions = None
        self._snapshot_shape = None

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

    def project(self, x: Union[np.ndarray, List[np.ndarray]]) -> np.ndarray:
        if isinstance(x, list):
            return np.array([self.project(xi) for xi in x])
        
        x_flat = self._flatten_snapshot(x)
        
        expected_dim = self.basis.basis.shape[0]
        if x_flat.shape[0] != expected_dim:
            raise ValueError(
                f"Snapshot dimension mismatch: got {x_flat.shape[0]}, "
                f"expected {expected_dim}. Basis shape: {self.basis.basis.shape}"
            )
        
        return self.basis.project(x_flat)

    def reconstruct(self, x_reduced: np.ndarray, reshape: bool = True) -> np.ndarray:
        x_reduced = np.asarray(x_reduced, dtype=self.basis.dtype)
        
        if x_reduced.ndim == 2:
            n_samples = x_reduced.shape[1]
            result = np.zeros((n_samples, self.basis.basis.shape[0]), dtype=self.basis.dtype)
            for i in range(n_samples):
                result[i] = self.basis.reconstruct(x_reduced[:, i])
            if reshape and self._snapshot_shape is not None:
                return result.reshape((n_samples,) + self._snapshot_shape)
            return result
        
        x_full = self.basis.reconstruct(x_reduced)
        
        if reshape and self._snapshot_shape is not None:
            return self._reshape_snapshot(x_full)
        return x_full

    def solve_reduced(self, parameter: np.ndarray, *args, **kwargs) -> np.ndarray:
        if self.full_model is None:
            raise ValueError("Full model not provided. Set full_model in constructor.")
        
        x_full = self.full_model(parameter, *args, **kwargs)
        x_reduced = self.project(x_full)
        return x_reduced

    def solve(self, parameter: np.ndarray, *args, **kwargs) -> np.ndarray:
        x_reduced = self.solve_reduced(parameter, *args, **kwargs)
        x_full = self.reconstruct(x_reduced)
        return x_full

    def offline_stage(self, parameters: np.ndarray, batch_size: Optional[int] = None, 
                      *args, **kwargs) -> None:
        if self.full_model is None:
            raise ValueError("Full model not provided. Set full_model in constructor.")
        
        n_params = len(parameters)
        
        if batch_size is None:
            batch_size = n_params
        
        self.reduced_solutions = []
        self.full_solutions = []
        
        for start_idx in range(0, n_params, batch_size):
            end_idx = min(start_idx + batch_size, n_params)
            batch_params = parameters[start_idx:end_idx]
            
            for mu in batch_params:
                x_full = self.full_model(mu, *args, **kwargs)
                x_reduced = self.project(x_full)
                self.reduced_solutions.append(x_reduced)
                self.full_solutions.append(x_full)
        
        self.reduced_solutions = np.array(self.reduced_solutions, dtype=self.basis.dtype)
        self.full_solutions = np.array(self.full_solutions, dtype=self.basis.dtype)

    def online_stage(self, parameter: np.ndarray, training_parameters: np.ndarray, 
                     method: str = 'interpolation', kind: str = 'linear',
                     *args, **kwargs) -> np.ndarray:
        if self.reduced_solutions is None:
            raise ValueError("Offline stage not completed. Call offline_stage() first.")
        
        if method == 'interpolation':
            from scipy.interpolate import interp1d
            
            if training_parameters.ndim == 1 and self.reduced_solutions.ndim == 2:
                interpolator = interp1d(
                    training_parameters, self.reduced_solutions.T,
                    kind=kind, fill_value='extrapolate', axis=0
                )
                x_reduced = interpolator(parameter).T
            else:
                raise NotImplementedError(
                    "Multi-dimensional interpolation requires parameter grid structure. "
                    "Consider using method='solve' instead."
                )
        elif method == 'solve':
            x_reduced = self.solve_reduced(parameter, *args, **kwargs)
        else:
            raise ValueError(f"Unknown method: {method}. Use 'interpolation' or 'solve'.")
        
        x_full = self.reconstruct(x_reduced)
        return x_full

    def galerkin_projection(self, operator: np.ndarray, rhs: Optional[np.ndarray] = None) -> tuple:
        V = self.basis.basis
        n_basis = V.shape[1]
        
        if operator.ndim == 2:
            expected_dim = V.shape[0]
            if operator.shape[0] != expected_dim or operator.shape[1] != expected_dim:
                raise ValueError(
                    f"Operator shape mismatch: got {operator.shape}, "
                    f"expected ({expected_dim}, {expected_dim})"
                )
            reduced_operator = V.T @ operator @ V
        else:
            raise ValueError(f"Operator must be 2D matrix, got {operator.ndim}D")
        
        reduced_rhs = None
        if rhs is not None:
            rhs = np.asarray(rhs, dtype=self.basis.dtype)
            if rhs.ndim == 1:
                if rhs.shape[0] != V.shape[0]:
                    raise ValueError(
                        f"RHS shape mismatch: got {rhs.shape}, "
                        f"expected ({V.shape[0]},)"
                    )
                reduced_rhs = V.T @ rhs
            elif rhs.ndim == 2:
                if rhs.shape[0] != V.shape[0]:
                    raise ValueError(
                        f"RHS shape mismatch: got {rhs.shape}, "
                        f"expected ({V.shape[0]}, ...)"
                    )
                reduced_rhs = V.T @ rhs
            else:
                raise ValueError(f"RHS must be 1D or 2D array, got {rhs.ndim}D")
        
        if reduced_rhs is None:
            return reduced_operator
        return reduced_operator, reduced_rhs

    def batch_project(self, snapshots: np.ndarray) -> np.ndarray:
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
                return (self.basis.basis.T @ snapshots_flat.T).T
            return (self.basis.basis.T @ snapshots.T).T
        else:
            n_snapshots = snapshots.shape[0]
            snapshots_flat = snapshots.reshape(n_snapshots, -1)
            if snapshots_flat.shape[1] != self.basis.basis.shape[0]:
                raise ValueError(
                    f"Flattened snapshot dimension mismatch: got {snapshots_flat.shape[1]}, "
                    f"expected {self.basis.basis.shape[0]}"
                )
            return (self.basis.basis.T @ snapshots_flat.T).T

    def batch_reconstruct(self, reduced_solutions: np.ndarray) -> np.ndarray:
        reduced_solutions = np.asarray(reduced_solutions, dtype=self.basis.dtype)
        
        if reduced_solutions.ndim == 2:
            n_snapshots = reduced_solutions.shape[0]
            if reduced_solutions.shape[1] != self.basis.basis.shape[1]:
                raise ValueError(
                    f"Reduced solution dimension mismatch: got {reduced_solutions.shape[1]}, "
                    f"expected {self.basis.basis.shape[1]}"
                )
            full_flat = (self.basis.basis @ reduced_solutions.T).T
            
            if self._snapshot_shape is not None:
                return full_flat.reshape((n_snapshots,) + self._snapshot_shape)
            return full_flat
        else:
            return self.reconstruct(reduced_solutions)

    def save(self, filename: str) -> None:
        save_data = {
            'reduced_solutions': self.reduced_solutions,
            'full_solutions': self.full_solutions,
        }
        if self._snapshot_shape is not None:
            save_data['snapshot_shape'] = np.array(self._snapshot_shape)
        
        np.savez(filename, **save_data)

    def load(self, filename: str) -> None:
        data = np.load(filename, allow_pickle=True)
        self.reduced_solutions = data['reduced_solutions']
        self.full_solutions = data['full_solutions']
        if 'snapshot_shape' in data:
            self._snapshot_shape = tuple(data['snapshot_shape'])
