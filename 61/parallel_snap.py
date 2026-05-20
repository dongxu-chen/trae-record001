import numpy as np
from typing import Callable, List, Optional, Tuple, Dict, Any
import multiprocessing as mp
from functools import partial
import warnings


class ParallelSnapshotGenerator:
    def __init__(self, model: Callable, parameter_range: np.ndarray,
                 n_workers: Optional[int] = None, dtype: np.dtype = np.float64,
                 use_memmap: bool = False, memmap_path: str = 'parallel_snapshots.npy'):
        self.model = model
        self.parameter_range = parameter_range
        self.n_workers = n_workers if n_workers is not None else max(1, mp.cpu_count() - 1)
        self.dtype = dtype
        self.use_memmap = use_memmap
        self.memmap_path = memmap_path
        self.snapshots = None
        self.parameters = None
        self._snapshot_shape = None
        self._execution_info = {}

    def _get_snapshot_shape(self) -> tuple:
        if self._snapshot_shape is None:
            sample_mu = self.parameter_range[0]
            sample_snapshot = self.model(sample_mu)
            self._snapshot_shape = np.asarray(sample_snapshot).shape
        return self._snapshot_shape

    @staticmethod
    def _compute_single_snapshot(model: Callable, mu: Any) -> Tuple[np.ndarray, Any]:
        snapshot = np.asarray(model(mu))
        return snapshot, mu

    @staticmethod
    def _compute_time_snapshot(model: Callable, mu_time: Tuple[Any, float]) -> Tuple[np.ndarray, Tuple[Any, float]]:
        mu, t = mu_time
        snapshot = np.asarray(model(mu, t))
        return snapshot, (mu, t)

    def generate(self, time_steps: Optional[np.ndarray] = None,
                chunk_size: Optional[int] = None, verbose: bool = False) -> np.ndarray:
        shape = self._get_snapshot_shape()
        
        if time_steps is None:
            n_snapshots = len(self.parameter_range)
            param_iterator = self.parameter_range
            worker_func = self._compute_single_snapshot
        else:
            n_snapshots = len(self.parameter_range) * len(time_steps)
            param_iterator = [(mu, t) for mu in self.parameter_range for t in time_steps]
            worker_func = self._compute_time_snapshot
        
        if chunk_size is None:
            chunk_size = max(1, n_snapshots // self.n_workers)
        
        if self.use_memmap:
            self.snapshots = np.memmap(
                self.memmap_path, dtype=self.dtype, mode='w+',
                shape=(n_snapshots,) + shape
            )
        else:
            self.snapshots = np.zeros((n_snapshots,) + shape, dtype=self.dtype)
        
        self.parameters = np.zeros(n_snapshots, dtype=object)
        
        if verbose:
            print(f"Generating {n_snapshots} snapshots with {self.n_workers} workers...")
            print(f"Snapshot shape: {shape}")
        
        if self.n_workers > 1:
            with mp.Pool(processes=self.n_workers) as pool:
                results = list(pool.imap(
                    partial(worker_func, self.model),
                    param_iterator,
                    chunksize=chunk_size
                ))
            
            for i, (snapshot, param) in enumerate(results):
                self.snapshots[i] = snapshot.astype(self.dtype)
                self.parameters[i] = param
        else:
            for i, param in enumerate(param_iterator):
                snapshot, _ = worker_func(self.model, param)
                self.snapshots[i] = snapshot.astype(self.dtype)
                self.parameters[i] = param
        
        self._execution_info = {
            'n_snapshots': n_snapshots,
            'n_workers': self.n_workers,
            'chunk_size': chunk_size,
            'snapshot_shape': shape,
            'time_dependent': time_steps is not None
        }
        
        if verbose:
            print(f"Completed! Memory usage: {self.get_memory_usage():.2f} MB")
        
        return self.snapshots

    def generate_batched(self, batch_size: int = 10, time_steps: Optional[np.ndarray] = None,
                        verbose: bool = False) -> np.ndarray:
        shape = self._get_snapshot_shape()
        
        if time_steps is None:
            n_snapshots = len(self.parameter_range)
            all_params = self.parameter_range
            worker_func = self._compute_single_snapshot
        else:
            n_snapshots = len(self.parameter_range) * len(time_steps)
            all_params = [(mu, t) for mu in self.parameter_range for t in time_steps]
            worker_func = self._compute_time_snapshot
        
        self.snapshots = np.zeros((n_snapshots,) + shape, dtype=self.dtype)
        self.parameters = np.zeros(n_snapshots, dtype=object)
        
        n_batches = (n_snapshots + batch_size - 1) // batch_size
        
        if verbose:
            print(f"Generating {n_snapshots} snapshots in {n_batches} batches...")
        
        global_idx = 0
        for batch_idx in range(n_batches):
            start_idx = batch_idx * batch_size
            end_idx = min(start_idx + batch_size, n_snapshots)
            batch_params = all_params[start_idx:end_idx]
            
            if self.n_workers > 1 and len(batch_params) > 1:
                with mp.Pool(processes=self.n_workers) as pool:
                    results = list(pool.map(
                        partial(worker_func, self.model),
                        batch_params
                    ))
                
                for i, (snapshot, param) in enumerate(results):
                    self.snapshots[global_idx + i] = snapshot.astype(self.dtype)
                    self.parameters[global_idx + i] = param
            else:
                for i, param in enumerate(batch_params):
                    snapshot, _ = worker_func(self.model, param)
                    self.snapshots[global_idx + i] = snapshot.astype(self.dtype)
                    self.parameters[global_idx + i] = param
            
            global_idx += len(batch_params)
            
            if verbose:
                progress = (batch_idx + 1) / n_batches * 100
                print(f"  Batch {batch_idx + 1}/{n_batches} complete ({progress:.1f}%)")
        
        self._execution_info = {
            'n_snapshots': n_snapshots,
            'n_workers': self.n_workers,
            'batch_size': batch_size,
            'n_batches': n_batches,
            'snapshot_shape': shape,
            'time_dependent': time_steps is not None
        }
        
        return self.snapshots

    def adaptive_sampling(self, error_estimator: Optional[Callable] = None,
                         max_snapshots: int = 100, tol: float = 1e-3,
                         initial_samples: int = 10, verbose: bool = False) -> np.ndarray:
        shape = self._get_snapshot_shape()
        
        if error_estimator is None:
            error_estimator = lambda x, V: np.linalg.norm(x - V @ (V.T @ x))
        
        n_params = len(self.parameter_range)
        indices = np.random.choice(n_params, initial_samples, replace=False)
        selected_params = self.parameter_range[indices]
        
        snapshots = []
        for mu in selected_params:
            snapshots.append(np.asarray(self.model(mu), dtype=self.dtype))
        snapshots = np.array(snapshots)
        
        snapshot_matrix = snapshots.reshape(len(snapshots), -1).T
        from pod import PODBasis
        pod = PODBasis(snapshot_matrix)
        basis = pod.compute_basis(energy_threshold=0.99)
        
        remaining_indices = np.setdiff1d(np.arange(n_params), indices)
        errors = []
        
        for idx in remaining_indices:
            mu = self.parameter_range[idx]
            snapshot = np.asarray(self.model(mu), dtype=self.dtype)
            x = snapshot.flatten()
            error = error_estimator(x, basis)
            errors.append((error, idx, snapshot))
        
        errors.sort(key=lambda x: x[0], reverse=True)
        
        while len(snapshots) < max_snapshots and errors and errors[0][0] > tol:
            error, idx, snapshot = errors.pop(0)
            snapshots = np.vstack([snapshots, snapshot[np.newaxis, ...]])
            
            if len(snapshots) % 5 == 0:
                snapshot_matrix = snapshots.reshape(len(snapshots), -1).T
                pod = PODBasis(snapshot_matrix)
                basis = pod.compute_basis(energy_threshold=0.99)
                
                new_errors = []
                for e, i, s in errors:
                    x = s.flatten()
                    new_e = error_estimator(x, basis)
                    new_errors.append((new_e, i, s))
                errors = sorted(new_errors, key=lambda x: x[0], reverse=True)
        
        self.snapshots = snapshots
        self.parameters = selected_params.tolist() + [self.parameter_range[i] for _, i, _ in errors]
        
        if verbose:
            print(f"Adaptive sampling completed: {len(snapshots)} snapshots selected")
        
        return self.snapshots

    def get_snapshot_matrix(self, flatten: bool = True) -> np.ndarray:
        if self.snapshots is None:
            raise ValueError("No snapshots generated yet. Call generate() first.")
        
        if flatten:
            n_snapshots = self.snapshots.shape[0]
            return self.snapshots.reshape(n_snapshots, -1).T
        else:
            return self.snapshots.T

    def get_memory_usage(self) -> float:
        if self.snapshots is None:
            return 0.0
        return self.snapshots.nbytes / (1024 ** 2)

    def get_execution_info(self) -> Dict:
        return self._execution_info.copy()

    def save(self, filename: str, compression: bool = True) -> None:
        if self.snapshots is None:
            raise ValueError("No snapshots generated yet. Call generate() first.")
        
        save_data = {
            'snapshots': np.asarray(self.snapshots),
            'parameters': np.asarray(self.parameters),
            'execution_info': np.array(list(self._execution_info.items()), dtype=object)
        }
        if self._snapshot_shape is not None:
            save_data['snapshot_shape'] = np.array(self._snapshot_shape)
        
        save_func = np.savez_compressed if compression else np.savez
        save_func(filename, **save_data)

    def load(self, filename: str) -> None:
        data = np.load(filename, allow_pickle=True)
        self.snapshots = data['snapshots']
        self.parameters = data['parameters']
        if 'execution_info' in data:
            self._execution_info = dict(data['execution_info'])
        if 'snapshot_shape' in data:
            self._snapshot_shape = tuple(data['snapshot_shape'])
        self.dtype = self.snapshots.dtype


class DistributedSnapshotLoader:
    def __init__(self, file_pattern: str, n_files: int, dtype: np.dtype = np.float64):
        self.file_pattern = file_pattern
        self.n_files = n_files
        self.dtype = dtype
        self._metadata = []

    def load_metadata(self) -> List[Dict]:
        self._metadata = []
        for i in range(self.n_files):
            filename = self.file_pattern.format(i)
            with np.load(filename, allow_pickle=True) as data:
                info = {
                    'n_snapshots': data['snapshots'].shape[0],
                    'snapshot_shape': data['snapshots'].shape[1:],
                    'filename': filename
                }
                self._metadata.append(info)
        return self._metadata

    def load_all(self, workers: Optional[int] = None) -> np.ndarray:
        if not self._metadata:
            self.load_metadata()
        
        total_snapshots = sum(m['n_snapshots'] for m in self._metadata)
        snapshot_shape = self._metadata[0]['snapshot_shape']
        
        all_snapshots = np.zeros((total_snapshots,) + snapshot_shape, dtype=self.dtype)
        
        idx = 0
        for m in self._metadata:
            data = np.load(m['filename'], allow_pickle=True)
            n = m['n_snapshots']
            all_snapshots[idx:idx + n] = data['snapshots']
            idx += n
        
        return all_snapshots

    def load_range(self, start_idx: int, end_idx: int) -> np.ndarray:
        if not self._metadata:
            self.load_metadata()
        
        cumulative = np.cumsum([m['n_snapshots'] for m in self._metadata])
        
        snapshots_list = []
        current_idx = 0
        
        for i, m in enumerate(self._metadata):
            file_start = current_idx
            file_end = current_idx + m['n_snapshots']
            
            if file_end > start_idx and file_start < end_idx:
                data = np.load(m['filename'], allow_pickle=True)
                local_start = max(0, start_idx - file_start)
                local_end = min(m['n_snapshots'], end_idx - file_start)
                snapshots_list.append(data['snapshots'][local_start:local_end])
            
            current_idx = file_end
        
        return np.vstack(snapshots_list)


def compute_snapshots_parallel(model: Callable, params: np.ndarray,
                              n_workers: Optional[int] = None, **kwargs) -> np.ndarray:
    generator = ParallelSnapshotGenerator(model, params, n_workers=n_workers, **kwargs)
    return generator.generate()
