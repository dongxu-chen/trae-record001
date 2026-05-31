import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional
import warnings
warnings.filterwarnings('ignore')

GPU_AVAILABLE = False
NUMBA_CUDA_AVAILABLE = False
NUMBA_JIT_AVAILABLE = False
cupy = None

try:
    import cupy as cp
    GPU_AVAILABLE = True
except ImportError:
    GPU_AVAILABLE = False

try:
    from numba import cuda
    NUMBA_CUDA_AVAILABLE = cuda.is_available()
except Exception:
    NUMBA_CUDA_AVAILABLE = False


def is_gpu_available() -> bool:
    return GPU_AVAILABLE or NUMBA_CUDA_AVAILABLE


def get_device_info() -> Dict:
    info = {
        'cupy_available': GPU_AVAILABLE,
        'numba_cuda_available': NUMBA_CUDA_AVAILABLE,
        'gpu_available': is_gpu_available()
    }
    
    if GPU_AVAILABLE:
        try:
            dev = cp.cuda.Device(0)
            info['gpu_name'] = cp.cuda.runtime.getDeviceProperties(0)['name'].decode()
            info['gpu_memory_gb'] = dev.mem_info[1] / 1e9
            info['gpu_free_memory_gb'] = dev.mem_info[0] / 1e9
        except Exception:
            info['gpu_name'] = 'Unknown'
    
    return info


class GPUFactorCalculator:
    def __init__(self, use_gpu: bool = True):
        self.use_gpu = use_gpu and is_gpu_available()
        self.device_info = get_device_info()
        
        if self.use_gpu and GPU_AVAILABLE:
            self.xp = cp
        else:
            self.xp = np
        
        if self.use_gpu:
            print(f"[GPU加速] 已启用GPU加速: {self.device_info.get('gpu_name', 'Unknown')}")
        else:
            print("[GPU加速] GPU不可用，使用CPU计算(Numba JIT优化)")
    
    def _to_gpu(self, arr: np.ndarray):
        if self.use_gpu and GPU_AVAILABLE:
            return cp.asarray(arr, dtype=np.float32)
        return arr.astype(np.float32)
    
    def _to_cpu(self, arr) -> np.ndarray:
        if self.use_gpu and GPU_AVAILABLE and isinstance(arr, cp.ndarray):
            return cp.asnumpy(arr)
        return np.asarray(arr)
    
    def rolling_mean_gpu(self, data: np.ndarray, window: int) -> np.ndarray:
        x = self._to_gpu(data)
        n = len(x)
        result = self.xp.full(n, np.nan, dtype=np.float32)
        
        if n < window:
            return self._to_cpu(result)
        
        cumsum = self.xp.cumsum(x)
        result[window - 1:] = (cumsum[window - 1:] - self.xp.concatenate([self.xp.array([0]), cumsum[:-window]])) / window
        
        return self._to_cpu(result)
    
    def rolling_std_gpu(self, data: np.ndarray, window: int) -> np.ndarray:
        x = self._to_gpu(data)
        n = len(x)
        result = self.xp.full(n, np.nan, dtype=np.float32)
        
        if n < window:
            return self._to_cpu(result)
        
        cumsum = self.xp.cumsum(x)
        cumsum2 = self.xp.cumsum(x ** 2)
        
        sum_x = cumsum[window - 1:] - self.xp.concatenate([self.xp.array([0]), cumsum[:-window]])
        sum_x2 = cumsum2[window - 1:] - self.xp.concatenate([self.xp.array([0]), cumsum2[:-window]])
        
        mean_x = sum_x / window
        var_x = sum_x2 / window - mean_x ** 2
        var_x = self.xp.maximum(var_x, 0)
        result[window - 1:] = self.xp.sqrt(var_x)
        
        return self._to_cpu(result)
    
    def rolling_rank_gpu(self, data: np.ndarray, window: int) -> np.ndarray:
        x = self._to_gpu(data)
        n = len(x)
        result = self.xp.full(n, np.nan, dtype=np.float32)
        
        for i in range(window - 1, n):
            window_data = x[i - window + 1:i + 1]
            sorted_idx = self.xp.argsort(window_data)
            ranks = self.xp.empty_like(sorted_idx, dtype=self.xp.float32)
            ranks[sorted_idx] = self.xp.arange(1, window + 1, dtype=self.xp.float32) / window
            result[i] = ranks[-1]
        
        return self._to_cpu(result)
    
    def rank_cross_section_gpu(self, data_2d: np.ndarray) -> np.ndarray:
        x = self._to_gpu(data_2d)
        
        sorted_idx = self.xp.argsort(x, axis=1)
        ranks = self.xp.empty_like(sorted_idx, dtype=self.xp.float32)
        n_cols = x.shape[1]
        rows = self.xp.arange(x.shape[0]).reshape(-1, 1)
        ranks[rows, sorted_idx] = self.xp.arange(1, n_cols + 1, dtype=self.xp.float32) / n_cols
        
        return self._to_cpu(ranks)
    
    def compute_ic_matrix_gpu(self, factor_matrix: np.ndarray,
                               returns_matrix: np.ndarray) -> np.ndarray:
        f = self._to_gpu(factor_matrix)
        r = self._to_gpu(returns_matrix)
        
        f_mean = f.mean(axis=1, keepdims=True)
        r_mean = r.mean(axis=1, keepdims=True)
        
        f_centered = f - f_mean
        r_centered = r - r_mean
        
        cov = (f_centered * r_centered).sum(axis=1)
        f_std = self.xp.sqrt((f_centered ** 2).sum(axis=1))
        r_std = self.xp.sqrt((r_centered ** 2).sum(axis=1))
        
        ic = cov / (f_std * r_std + 1e-8)
        
        return self._to_cpu(ic)
    
    def compute_factor_values_batch_gpu(self,
                                         close: np.ndarray,
                                         open_: np.ndarray,
                                         high: np.ndarray,
                                         low: np.ndarray,
                                         volume: np.ndarray,
                                         operations: List[str]) -> List[np.ndarray]:
        results = []
        
        c = self._to_gpu(close)
        o = self._to_gpu(open_)
        h = self._to_gpu(high)
        l = self._to_gpu(low)
        v = self._to_gpu(volume)
        
        for op in operations:
            if op == 'close/open':
                val = c / (o + 1e-8)
            elif op == 'high-low/close':
                val = (h - l) / (c + 1e-8)
            elif op == 'volume*close':
                val = v * c
            elif op == 'close/mean5':
                mean5 = self.rolling_mean_gpu(close, 5)
                val = c / (self._to_gpu(mean5) + 1e-8)
            elif op == 'std5/close':
                std5 = self.rolling_std_gpu(close, 5)
                val = self._to_gpu(std5) / (c + 1e-8)
            elif op == 'delta_close':
                val = self.xp.diff(c, prepend=c[0])
            elif op == 'rank_close':
                val = self.xp.argsort(self.xp.argsort(c)).astype(self.xp.float32) / len(c)
            else:
                val = c
            
            results.append(self._to_cpu(val))
        
        return results


try:
    from numba import jit as _jit
    
    @_jit(nopython=True, cache=True)
    def _rolling_mean_numba_core(data, window):
        n = len(data)
        result = np.empty(n, dtype=np.float32)
        for i in range(n):
            result[i] = np.nan
        if n < window:
            return result
        cumsum = np.empty(n + 1, dtype=np.float32)
        cumsum[0] = 0.0
        for i in range(n):
            cumsum[i + 1] = cumsum[i] + data[i]
        for i in range(window - 1, n):
            result[i] = (cumsum[i + 1] - cumsum[i + 1 - window]) / window
        return result
    
    @_jit(nopython=True, cache=True)
    def _rolling_std_numba_core(data, window):
        n = len(data)
        result = np.empty(n, dtype=np.float32)
        for i in range(n):
            result[i] = np.nan
        if n < window:
            return result
        cumsum = np.empty(n + 1, dtype=np.float32)
        cumsum2 = np.empty(n + 1, dtype=np.float32)
        cumsum[0] = 0.0
        cumsum2[0] = 0.0
        for i in range(n):
            cumsum[i + 1] = cumsum[i] + data[i]
            cumsum2[i + 1] = cumsum2[i] + data[i] * data[i]
        for i in range(window - 1, n):
            s = cumsum[i + 1] - cumsum[i + 1 - window]
            s2 = cumsum2[i + 1] - cumsum2[i + 1 - window]
            mean_val = s / window
            var_val = s2 / window - mean_val * mean_val
            if var_val < 0.0:
                var_val = 0.0
            result[i] = np.sqrt(var_val)
        return result
    
    @_jit(nopython=True, cache=True)
    def _rank_cross_section_numba_core(data_2d):
        n_rows = data_2d.shape[0]
        n_cols = data_2d.shape[1]
        result = np.zeros((n_rows, n_cols), dtype=np.float32)
        for i in range(n_rows):
            sorted_idx = np.argsort(data_2d[i])
            for rank_val in range(n_cols):
                idx = sorted_idx[rank_val]
                result[i, idx] = np.float32(rank_val + 1) / np.float32(n_cols)
        return result
    
    @_jit(nopython=True, cache=True)
    def _compute_ic_numba_core(factor_data, return_data):
        n_periods = factor_data.shape[0]
        n_assets = factor_data.shape[1]
        ic_values = np.zeros(n_periods, dtype=np.float32)
        for i in range(n_periods):
            f_mean = 0.0
            r_mean = 0.0
            for j in range(n_assets):
                f_mean += factor_data[i, j]
                r_mean += return_data[i, j]
            f_mean = f_mean / n_assets
            r_mean = r_mean / n_assets
            cov_val = 0.0
            f_var = 0.0
            r_var = 0.0
            for j in range(n_assets):
                fd = factor_data[i, j] - f_mean
                rd = return_data[i, j] - r_mean
                cov_val += fd * rd
                f_var += fd * fd
                r_var += rd * rd
            f_std = np.sqrt(f_var)
            r_std = np.sqrt(r_var)
            if f_std > 1e-8 and r_std > 1e-8:
                ic_values[i] = cov_val / (f_std * r_std)
            else:
                ic_values[i] = 0.0
        return ic_values
    
    @_jit(nopython=True, cache=True)
    def _compute_turnover_numba_core(ranks_2d):
        n_rows = ranks_2d.shape[0]
        n_cols = ranks_2d.shape[1]
        turnover = np.zeros(n_rows - 1, dtype=np.float32)
        for i in range(n_rows - 1):
            s = 0.0
            for j in range(n_cols):
                s += abs(ranks_2d[i + 1, j] - ranks_2d[i, j])
            turnover[i] = s / n_cols
        return turnover
    
    def _rolling_mean_numba(data, window):
        return _rolling_mean_numba_core(data.astype(np.float32), np.int64(window))
    
    def _rolling_std_numba(data, window):
        return _rolling_std_numba_core(data.astype(np.float32), np.int64(window))
    
    def _rank_cross_section_numba(data_2d):
        return _rank_cross_section_numba_core(data_2d.astype(np.float32))
    
    def _compute_ic_numba(factor_data, return_data):
        return _compute_ic_numba_core(factor_data.astype(np.float32), return_data.astype(np.float32))
    
    def _compute_turnover_numba(ranks_2d):
        return _compute_turnover_numba_core(ranks_2d.astype(np.float32))
    
    NUMBA_JIT_AVAILABLE = True
except Exception:
    NUMBA_JIT_AVAILABLE = False
    
    def _rolling_mean_numba(data, window):
        return pd.Series(data).rolling(window).mean().values.astype(np.float32)
    
    def _rolling_std_numba(data, window):
        return pd.Series(data).rolling(window).std().values.astype(np.float32)
    
    def _rank_cross_section_numba(data_2d):
        return pd.DataFrame(data_2d).rank(axis=1, pct=True).values.astype(np.float32)
    
    def _compute_ic_numba(factor_data, return_data):
        ics = []
        for i in range(factor_data.shape[0]):
            ic = np.corrcoef(factor_data[i], return_data[i])[0, 1]
            ics.append(ic)
        return np.array(ics, dtype=np.float32)
    
    def _compute_turnover_numba(ranks_2d):
        diff = np.abs(np.diff(ranks_2d, axis=0))
        return diff.mean(axis=1).astype(np.float32)
    
    NUMBA_JIT_AVAILABLE = False


class AcceleratedFactorOps:
    def __init__(self, use_gpu: bool = True):
        self.gpu_calc = GPUFactorCalculator(use_gpu=use_gpu)
        self.use_gpu = self.gpu_calc.use_gpu
    
    def rolling_mean(self, data: np.ndarray, window: int) -> np.ndarray:
        if self.use_gpu and GPU_AVAILABLE:
            return self.gpu_calc.rolling_mean_gpu(data, window)
        return _rolling_mean_numba(data, window)
    
    def rolling_std(self, data: np.ndarray, window: int) -> np.ndarray:
        if self.use_gpu and GPU_AVAILABLE:
            return self.gpu_calc.rolling_std_gpu(data, window)
        return _rolling_std_numba(data, window)
    
    def rank_cross_section(self, data_2d: np.ndarray) -> np.ndarray:
        if self.use_gpu and GPU_AVAILABLE:
            return self.gpu_calc.rank_cross_section_gpu(data_2d)
        return _rank_cross_section_numba(data_2d)
    
    def compute_ic(self, factor_data: np.ndarray, return_data: np.ndarray) -> np.ndarray:
        if self.use_gpu and GPU_AVAILABLE:
            return self.gpu_calc.compute_ic_matrix_gpu(factor_data, return_data)
        return _compute_ic_numba(factor_data, return_data)
    
    def compute_turnover(self, ranks_2d: np.ndarray) -> np.ndarray:
        return _compute_turnover_numba(ranks_2d)
    
    def compute_factor_pipeline(self, factor: pd.Series, 
                                 forward_returns: pd.Series,
                                 windows: List[int] = [5, 10, 20]) -> Dict:
        factor_unstacked = factor.unstack(level='asset')
        returns_unstacked = forward_returns.unstack(level='asset') if isinstance(forward_returns.index, pd.MultiIndex) else forward_returns
        
        factor_matrix = factor_unstacked.values.astype(np.float32)
        
        results = {
            'rolling_means': {},
            'rolling_stds': {},
            'ic_series': None,
            'turnover': None
        }
        
        for w in windows:
            means = np.zeros_like(factor_matrix)
            stds = np.zeros_like(factor_matrix)
            
            for col in range(factor_matrix.shape[1]):
                means[:, col] = self.rolling_mean(factor_matrix[:, col], w)
                stds[:, col] = self.rolling_std(factor_matrix[:, col], w)
            
            results['rolling_means'][w] = means
            results['rolling_stds'][w] = stds
        
        ranks = self.rank_cross_section(factor_matrix)
        results['turnover'] = self.compute_turnover(ranks)
        
        if isinstance(forward_returns.index, pd.MultiIndex):
            returns_matrix = returns_unstacked.values.astype(np.float32)
            mask = ~(np.isnan(factor_matrix) | np.isnan(returns_matrix))
            f_clean = np.where(mask, factor_matrix, 0)
            r_clean = np.where(mask, returns_matrix, 0)
            results['ic_series'] = self.compute_ic(f_clean, r_clean)
        
        return results
