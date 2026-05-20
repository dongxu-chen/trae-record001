import numpy as np
from typing import Callable, Optional, Tuple, Dict, List
import warnings
from scipy.interpolate import interp1d, griddata, Rbf
from pod import PODBasis


class OnlineEvaluator:
    def __init__(self, basis: PODBasis, training_parameters: np.ndarray,
                 training_coefficients: np.ndarray, dtype: np.dtype = np.float64):
        self.basis = basis
        self.training_parameters = np.asarray(training_parameters, dtype=dtype)
        self.training_coefficients = np.asarray(training_coefficients, dtype=dtype)
        self.dtype = dtype
        self._interpolator = None
        self._interp_method = None
        self._param_dim = (training_parameters.ndim 
                          if training_parameters.ndim > 1 else 1)

    def build_interpolator(self, method: str = 'linear', **kwargs) -> None:
        self._interp_method = method
        
        if self._param_dim == 1:
            params = self.training_parameters.flatten()
            self._interpolator = interp1d(
                params, self.training_coefficients.T,
                kind=method, fill_value='extrapolate',
                axis=0, **kwargs
            )
        else:
            if method in ['linear', 'cubic', 'nearest']:
                self._interpolator = lambda mu: griddata(
                    self.training_parameters, self.training_coefficients,
                    mu, method=method
                )
            elif method == 'rbf':
                rbf_funcs = []
                for i in range(self.training_coefficients.shape[1]):
                    rbf = Rbf(*self.training_parameters.T,
                             self.training_coefficients[:, i], **kwargs)
                    rbf_funcs.append(rbf)
                self._interpolator = lambda mu: np.array([f(*np.atleast_2d(mu).T) for f in rbf_funcs]).T
            else:
                raise ValueError(f"Unsupported interpolation method: {method}")

    def evaluate(self, parameter: np.ndarray, reshape: bool = True) -> np.ndarray:
        if self._interpolator is None:
            warnings.warn("Interpolator not built. Building default linear interpolator.")
            self.build_interpolator(method='linear')
        
        coeffs = self._interpolator(parameter)
        
        if coeffs.ndim > 1:
            coeffs = coeffs.flatten()
        
        snapshot = self.basis.reconstruct(coeffs)
        
        if reshape and hasattr(self.basis, '_snapshot_shape'):
            return snapshot.reshape(self.basis._snapshot_shape)
        
        return snapshot

    def batch_evaluate(self, parameters: np.ndarray) -> np.ndarray:
        if self._interpolator is None:
            self.build_interpolator(method='linear')
        
        parameters = np.asarray(parameters)
        n_eval = len(parameters)
        
        coeffs_batch = np.zeros((n_eval, self.training_coefficients.shape[1]), dtype=self.dtype)
        
        for i, mu in enumerate(parameters):
            coeffs_batch[i] = self._interpolator(mu)
        
        snapshots_flat = self.basis.reconstruct(coeffs_batch.T).T
        
        if hasattr(self.basis, '_snapshot_shape'):
            return snapshots_flat.reshape((n_eval,) + self.basis._snapshot_shape)
        
        return snapshots_flat


class AdaptiveOnlineEvaluator(OnlineEvaluator):
    def __init__(self, basis: PODBasis, training_parameters: np.ndarray,
                 training_coefficients: np.ndarray, error_estimator: Optional[Callable] = None,
                 dtype: np.dtype = np.float64):
        super().__init__(basis, training_parameters, training_coefficients, dtype)
        self.error_estimator = error_estimator
        self.error_cache = {}
        self.evaluation_count = 0
        self._adaptive_data = {}

    def evaluate_with_error(self, parameter: np.ndarray) -> Tuple[np.ndarray, float]:
        parameter_tuple = tuple(np.atleast_1d(parameter))
        
        if parameter_tuple in self.error_cache:
            snapshot, error = self.error_cache[parameter_tuple]
            return snapshot, error
        
        snapshot = self.evaluate(parameter)
        
        if self.error_estimator is not None:
            error = self.error_estimator(snapshot, self.basis.basis)
        else:
            proj = self.basis.project(snapshot.flatten())
            recon = self.basis.reconstruct(proj)
            error = np.linalg.norm(snapshot.flatten() - recon)
        
        self.error_cache[parameter_tuple] = (snapshot, error)
        self.evaluation_count += 1
        
        return snapshot, error

    def adaptive_refinement(self, parameter: np.ndarray,
                           tolerance: float = 1e-3,
                           full_model: Optional[Callable] = None) -> Dict:
        snapshot, error = self.evaluate_with_error(parameter)
        
        result = {
            'parameter': parameter,
            'snapshot': snapshot,
            'error': error,
            'within_tolerance': error <= tolerance,
            'refinement_needed': error > tolerance
        }
        
        if error > tolerance and full_model is not None:
            new_snapshot = full_model(parameter)
            new_coeff = self.basis.project(new_snapshot.flatten())
            
            self.training_parameters = np.vstack([
                self.training_parameters, parameter
            ])
            self.training_coefficients = np.vstack([
                self.training_coefficients, new_coeff
            ])
            
            self.build_interpolator(method=self._interp_method)
            
            result.update({
                'new_snapshot_added': True,
                'new_snapshot': new_snapshot,
                'new_coefficients': new_coeff
            })
        
        return result


class ReducedOrderModel:
    def __init__(self, pod_basis: PODBasis, training_params: np.ndarray,
                 training_snapshots: np.ndarray):
        self.pod_basis = pod_basis
        self.training_params = training_params
        self.training_snapshots = training_snapshots
        
        self.training_coefficients = pod_basis.project(
            training_snapshots.reshape(len(training_snapshots), -1).T
        ).T
        
        self.online_evaluator = OnlineEvaluator(
            pod_basis, training_params, self.training_coefficients
        )
        
        self._reconstruction_errors = None
        self._speedup_data = {}

    def train(self, interp_method: str = 'linear', **kwargs) -> None:
        self.online_evaluator.build_interpolator(method=interp_method, **kwargs)

    def predict(self, parameter: np.ndarray) -> np.ndarray:
        return self.online_evaluator.evaluate(parameter)

    def predict_batch(self, parameters: np.ndarray) -> np.ndarray:
        return self.online_evaluator.batch_evaluate(parameters)

    def compute_reconstruction_errors(self) -> np.ndarray:
        reconstructed = self.predict_batch(self.training_params)
        errors = np.linalg.norm(
            self.training_snapshots.reshape(len(self.training_snapshots), -1) -
            reconstructed.reshape(len(reconstructed), -1),
            axis=1
        )
        self._reconstruction_errors = errors
        return errors

    def get_error_statistics(self) -> Dict:
        if self._reconstruction_errors is None:
            self.compute_reconstruction_errors()
        
        errors = self._reconstruction_errors
        return {
            'mean_error': float(np.mean(errors)),
            'std_error': float(np.std(errors)),
            'max_error': float(np.max(errors)),
            'min_error': float(np.min(errors)),
            'median_error': float(np.median(errors))
        }

    def estimate_speedup(self, full_model_time: float,
                        n_params: int = 100) -> Dict:
        import time
        
        params = np.random.rand(n_params, *self.training_params.shape[1:])
        
        start = time.time()
        self.predict_batch(params)
        reduced_time = time.time() - start
        
        full_time_total = full_model_time * n_params
        
        speedup = full_time_total / reduced_time
        
        self._speedup_data = {
            'full_model_time_per_eval': full_model_time,
            'reduced_model_time_total': reduced_time,
            'reduced_model_time_per_eval': reduced_time / n_params,
            'full_model_time_total': full_time_total,
            'speedup': speedup,
            'n_evaluations': n_params
        }
        
        return self._speedup_data

    def save(self, filename: str) -> None:
        np.savez(
            filename,
            training_params=self.training_params,
            training_coefficients=self.training_coefficients,
            reconstruction_errors=self._reconstruction_errors,
            speedup_data=np.array(list(self._speedup_data.items()), dtype=object)
        )
        self.pod_basis.save(filename + '_basis.npz')

    def load(self, filename: str) -> None:
        data = np.load(filename, allow_pickle=True)
        self.training_params = data['training_params']
        self.training_coefficients = data['training_coefficients']
        if 'reconstruction_errors' in data:
            self._reconstruction_errors = data['reconstruction_errors']
        if 'speedup_data' in data:
            self._speedup_data = dict(data['speedup_data'])
        
        self.pod_basis.load(filename + '_basis.npz')


class ROMPipeline:
    def __init__(self, model: Callable, parameter_range: np.ndarray):
        self.model = model
        self.parameter_range = parameter_range
        self.snapshots = None
        self.pod_basis = None
        self.rom = None
        self.pipeline_steps = []

    def run_offline(self, n_train: int = 50, method: str = 'svd',
                   energy_threshold: float = 0.99, verbose: bool = False) -> None:
        if verbose:
            print("=== Offline Phase ===")
        
        train_idx = np.linspace(0, len(self.parameter_range) - 1, n_train, dtype=int)
        train_params = self.parameter_range[train_idx]
        
        if verbose:
            print(f"1. Generating {n_train} training snapshots...")
        
        self.snapshots = np.array([self.model(mu) for mu in train_params])
        snapshot_matrix = self.snapshots.reshape(n_train, -1).T
        
        if verbose:
            print(f"2. Computing POD basis (energy threshold = {energy_threshold})...")
        
        self.pod_basis = PODBasis(snapshot_matrix)
        self.pod_basis.compute_basis(method=method, energy_threshold=energy_threshold)
        
        if verbose:
            print(f"   Basis rank: {self.pod_basis.get_rank()}")
            print(f"   Energy captured: {self.pod_basis.get_energy():.4f}")
        
        if verbose:
            print("3. Building reduced order model...")
        
        self.rom = ReducedOrderModel(self.pod_basis, train_params, self.snapshots)
        self.rom.train(interp_method='linear')
        
        if verbose:
            print("Offline phase completed!")
        
        self.pipeline_steps.extend(['offline'])

    def run_online(self, test_params: np.ndarray,
                   full_model: Optional[Callable] = None,
                   verbose: bool = False) -> Dict:
        if self.rom is None:
            raise ValueError("Offline phase not completed. Call run_offline() first.")
        
        if verbose:
            print("\n=== Online Phase ===")
            print(f"Evaluating {len(test_params)} parameters...")
        
        predictions = self.rom.predict_batch(test_params)
        
        results = {
            'parameters': test_params,
            'predictions': predictions,
            'errors': None,
            'statistics': None
        }
        
        if full_model is not None:
            if verbose:
                print("Computing errors against full model...")
            
            true_solutions = np.array([full_model(mu) for mu in test_params])
            errors = np.linalg.norm(
                true_solutions.reshape(len(true_solutions), -1) -
                predictions.reshape(len(predictions), -1),
                axis=1
            )
            results['true_solutions'] = true_solutions
            results['errors'] = errors
            
            stats = {
                'mean_error': float(np.mean(errors)),
                'max_error': float(np.max(errors)),
                'mean_relative_error': float(np.mean(errors / np.linalg.norm(
                    true_solutions.reshape(len(true_solutions), -1), axis=1
                )))
            }
            results['statistics'] = stats
        
        if verbose:
            if results['statistics'] is not None:
                print(f"Mean error: {stats['mean_error']:.2e}")
                print(f"Max error: {stats['max_error']:.2e}")
            print("Online phase completed!")
        
        self.pipeline_steps.extend(['online'])
        
        return results


def create_rom_from_snapshots(snapshots: np.ndarray, parameters: np.ndarray,
                             energy_threshold: float = 0.99) -> ReducedOrderModel:
    snapshot_matrix = snapshots.reshape(len(snapshots), -1).T
    pod_basis = PODBasis(snapshot_matrix)
    pod_basis.compute_basis(energy_threshold=energy_threshold)
    
    rom = ReducedOrderModel(pod_basis, parameters, snapshots)
    rom.train()
    
    return rom
