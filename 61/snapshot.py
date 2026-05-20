import numpy as np
from typing import Callable, List, Optional, Union, Iterator
import os


class SnapshotGenerator:
    def __init__(self, model: Callable, parameter_range: np.ndarray, 
                 dtype: np.dtype = np.float64, use_memmap: bool = False,
                 memmap_path: str = 'snapshots_memmap.npy'):
        self.model = model
        self.parameter_range = parameter_range
        self.dtype = dtype
        self.use_memmap = use_memmap
        self.memmap_path = memmap_path
        self.snapshots = None
        self.parameters = None
        self._snapshot_shape = None

    def _get_snapshot_shape(self, *args, **kwargs) -> tuple:
        if self._snapshot_shape is None:
            sample_mu = self.parameter_range[0]
            sample_snapshot = self.model(sample_mu, *args, **kwargs)
            self._snapshot_shape = np.asarray(sample_snapshot).shape
        return self._snapshot_shape

    def generate(self, time_steps: Optional[np.ndarray] = None, 
                 chunk_size: Optional[int] = None) -> np.ndarray:
        shape = self._get_snapshot_shape()
        
        if time_steps is None:
            n_snapshots = len(self.parameter_range)
            param_iterator = self.parameter_range
        else:
            n_snapshots = len(self.parameter_range) * len(time_steps)
            param_iterator = [(mu, t) for mu in self.parameter_range for t in time_steps]
        
        if chunk_size is None or not self.use_memmap:
            chunk_size = n_snapshots
        
        if self.use_memmap:
            self.snapshots = np.memmap(
                self.memmap_path, dtype=self.dtype, mode='w+',
                shape=(n_snapshots,) + shape
            )
        else:
            self.snapshots = np.zeros((n_snapshots,) + shape, dtype=self.dtype)
        
        self.parameters = np.zeros(n_snapshots, dtype=object)
        
        for start_idx in range(0, n_snapshots, chunk_size):
            end_idx = min(start_idx + chunk_size, n_snapshots)
            chunk_indices = slice(start_idx, end_idx)
            
            chunk_snapshots = []
            chunk_params = []
            
            for i in range(start_idx, end_idx):
                if time_steps is None:
                    mu = param_iterator[i]
                    snapshot = self.model(mu)
                    param_val = mu
                else:
                    mu, t = param_iterator[i]
                    snapshot = self.model(mu, t)
                    param_val = (mu, t)
                
                chunk_snapshots.append(np.asarray(snapshot, dtype=self.dtype))
                chunk_params.append(param_val)
            
            self.snapshots[chunk_indices] = np.array(chunk_snapshots, dtype=self.dtype)
            self.parameters[start_idx:end_idx] = chunk_params
        
        return self.snapshots

    def generate_iterator(self, time_steps: Optional[np.ndarray] = None) -> Iterator[tuple]:
        if time_steps is None:
            for mu in self.parameter_range:
                snapshot = self.model(mu)
                yield np.asarray(snapshot, dtype=self.dtype), mu
        else:
            for mu in self.parameter_range:
                for t in time_steps:
                    snapshot = self.model(mu, t)
                    yield np.asarray(snapshot, dtype=self.dtype), (mu, t)

    def add_noise(self, noise_level: float = 0.01, inplace: bool = True) -> Optional[np.ndarray]:
        if self.snapshots is None:
            raise ValueError("No snapshots generated yet. Call generate() first.")
        
        noise = np.random.normal(0, noise_level, self.snapshots.shape).astype(self.dtype)
        
        if inplace:
            self.snapshots += noise
            if self.use_memmap:
                self.snapshots.flush()
            return None
        else:
            return self.snapshots + noise

    def subsample(self, indices: Union[List[int], np.ndarray], 
                  inplace: bool = True) -> Optional[np.ndarray]:
        if self.snapshots is None:
            raise ValueError("No snapshots generated yet. Call generate() first.")
        
        indices = np.asarray(indices)
        
        if inplace:
            if self.use_memmap:
                new_memmap = np.memmap(
                    self.memmap_path + '_subsampled', dtype=self.dtype, mode='w+',
                    shape=(len(indices),) + self.snapshots.shape[1:]
                )
                new_memmap[:] = self.snapshots[indices]
                new_memmap.flush()
                self.snapshots = new_memmap
            else:
                self.snapshots = self.snapshots[indices]
            
            if self.parameters is not None:
                self.parameters = self.parameters[indices]
            return None
        else:
            return self.snapshots[indices]

    def get_snapshot_matrix(self, flatten: bool = True) -> np.ndarray:
        if self.snapshots is None:
            raise ValueError("No snapshots generated yet. Call generate() first.")
        
        if flatten:
            n_snapshots = self.snapshots.shape[0]
            return self.snapshots.reshape(n_snapshots, -1).T
        else:
            return self.snapshots.T

    def save(self, filename: str, compression: bool = True) -> None:
        if self.snapshots is None:
            raise ValueError("No snapshots generated yet. Call generate() first.")
        
        save_func = np.savez_compressed if compression else np.savez
        save_func(filename, snapshots=np.asarray(self.snapshots), 
                  parameters=np.asarray(self.parameters))
        
        if self.use_memmap:
            del self.snapshots
            try:
                os.remove(self.memmap_path)
            except:
                pass

    def load(self, filename: str, use_memmap: Optional[bool] = None) -> None:
        data = np.load(filename, allow_pickle=True)
        snapshots = data['snapshots']
        
        if use_memmap is None:
            use_memmap = self.use_memmap
        
        if use_memmap:
            self.snapshots = np.memmap(
                self.memmap_path, dtype=snapshots.dtype, mode='w+',
                shape=snapshots.shape
            )
            self.snapshots[:] = snapshots[:]
            self.snapshots.flush()
        else:
            self.snapshots = snapshots
        
        self.parameters = data['parameters']
        self.dtype = self.snapshots.dtype

    def get_memory_usage(self) -> float:
        if self.snapshots is None:
            return 0.0
        return self.snapshots.nbytes / (1024 ** 2)
