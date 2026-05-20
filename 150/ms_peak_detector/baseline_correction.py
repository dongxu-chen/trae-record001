import numpy as np
from scipy import signal
from scipy.ndimage import minimum_filter1d, maximum_filter1d
from scipy.sparse import spdiags, eye
from scipy.sparse.linalg import spsolve


class BaselineCorrector:
    def __init__(self, method: str = "segmented_asls"):
        self.method = method
        self.baseline = None
    
    def correct(self, mz: np.ndarray, intensity: np.ndarray, **kwargs) -> np.ndarray:
        if self.method == "asls":
            return self._asls_correction(intensity, **kwargs)
        elif self.method == "segmented_asls":
            return self._segmented_asls_correction(intensity, **kwargs)
        elif self.method == "rolling_min":
            return self._rolling_min_correction(intensity, **kwargs)
        elif self.method == "tophat":
            return self._tophat_correction(intensity, **kwargs)
        elif self.method == "snip":
            return self._snip_correction(intensity, **kwargs)
        else:
            raise ValueError(f"Unknown method: {self.method}")
    
    def _segmented_asls_correction(self, intensity: np.ndarray, 
                                    segment_size: int = 1000,
                                    overlap: int = 200,
                                    lam: float = 1e5, 
                                    p: float = 0.001, 
                                    niter: int = 10) -> np.ndarray:
        L = len(intensity)
        baseline = np.zeros(L)
        
        if L <= segment_size:
            return self._asls_correction(intensity, lam, p, niter)
        
        num_segments = (L - overlap) // (segment_size - overlap) + 1
        weights = np.zeros(L)
        
        for i in range(num_segments):
            start = i * (segment_size - overlap)
            end = min(start + segment_size, L)
            
            if end - start < 10:
                continue
            
            segment = intensity[start:end]
            segment_baseline = self._sparse_asls(segment, lam, p, niter)
            
            taper = np.ones(end - start)
            if i > 0:
                taper[:overlap] = np.linspace(0, 1, overlap)
            if i < num_segments - 1:
                taper[-overlap:] = np.linspace(1, 0, overlap)
            
            baseline[start:end] += segment_baseline * taper
            weights[start:end] += taper
        
        weights[weights == 0] = 1
        baseline = baseline / weights
        
        self.baseline = baseline
        return intensity - baseline
    
    def _sparse_asls(self, intensity: np.ndarray, lam: float, p: float, niter: int) -> np.ndarray:
        L = len(intensity)
        
        D = eye(L, format='csr')
        D = D[1:] - D[:-1]
        D2 = D[1:] - D[:-1]
        
        w = np.ones(L)
        
        for _ in range(niter):
            W = spdiags(w, 0, L, L, format='csr')
            Z = W + lam * D2.T @ D2
            baseline = spsolve(Z, w * intensity)
            w = p * (intensity > baseline) + (1 - p) * (intensity < baseline)
        
        return baseline
    
    def _asls_correction(self, intensity: np.ndarray, lam: float = 1e5, p: float = 0.001, niter: int = 10) -> np.ndarray:
        L = len(intensity)
        
        D = eye(L, format='csr')
        D = D[1:] - D[:-1]
        D2 = D[1:] - D[:-1]
        
        w = np.ones(L)
        for _ in range(niter):
            W = spdiags(w, 0, L, L, format='csr')
            Z = W + lam * D2.T @ D2
            baseline = spsolve(Z, w * intensity)
            w = p * (intensity > baseline) + (1 - p) * (intensity < baseline)
        
        self.baseline = baseline
        return intensity - baseline
    
    def _rolling_min_correction(self, intensity: np.ndarray, window_size: int = 51) -> np.ndarray:
        baseline = minimum_filter1d(intensity, size=window_size)
        baseline = maximum_filter1d(baseline, size=window_size // 2)
        self.baseline = baseline
        return intensity - baseline
    
    def _tophat_correction(self, intensity: np.ndarray, window_size: int = 51) -> np.ndarray:
        structure = np.ones(window_size)
        baseline = signal.medfilt(intensity, kernel_size=window_size)
        self.baseline = baseline
        return intensity - baseline
    
    def _snip_correction(self, intensity: np.ndarray, max_iter: int = 30) -> np.ndarray:
        y = np.copy(intensity)
        for j in range(max_iter, 0, -1):
            for i in range(j, len(y) - j):
                y[i] = min(y[i], (y[i - j] + y[i + j]) / 2)
        self.baseline = y
        return intensity - y
    
    def get_baseline(self) -> np.ndarray:
        if self.baseline is None:
            raise ValueError("Baseline not computed. Run correct() first.")
        return self.baseline
