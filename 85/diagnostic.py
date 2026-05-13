import numpy as np
import math
from typing import List, Tuple, Dict


def effective_sample_size(samples: np.ndarray) -> np.ndarray:
    """计算有效样本量 (ESS)"""
    samples = np.asarray(samples)
    if samples.ndim == 1:
        samples = samples.reshape(-1, 1)
    
    n, dim = samples.shape
    ess = np.zeros(dim)
    
    for d in range(dim):
        series = samples[:, d]
        mean_est = np.mean(series)
        var_est = np.var(series, ddof=1)
        
        if var_est == 0:
            ess[d] = n
            continue
        
        max_lag = min(int(n / 2), 2000)
        acf = autocorrelation(series, max_lag=max_lag)
        
        sum_acf = 1.0
        for k in range(1, max_lag + 1):
            if k > 1 and acf[k] + acf[k - 1] < 0:
                break
            sum_acf += 2.0 * acf[k]
        
        ess[d] = n / sum_acf if sum_acf > 0 else 0.0
    
    return ess


def autocorrelation(series: np.ndarray, max_lag: int = None) -> np.ndarray:
    """计算自相关函数"""
    series = np.asarray(series)
    n = len(series)
    if max_lag is None:
        max_lag = int(n / 2)
    
    series_centered = series - np.mean(series)
    acf = np.zeros(max_lag + 1)
    
    for lag in range(max_lag + 1):
        if lag == 0:
            acf[lag] = 1.0
        else:
            numerator = np.sum(series_centered[lag:] * series_centered[:-lag])
            denominator = np.sum(series_centered ** 2)
            acf[lag] = numerator / denominator if denominator != 0 else 0.0
    
    return acf


def gelman_rubin(chains: List[np.ndarray]) -> np.ndarray:
    """Gelman-Rubin 收敛诊断"""
    m = len(chains)
    if m < 2:
        raise ValueError("Gelman-Rubin 需要至少 2 条链")
    
    chain_lengths = [len(chain) for chain in chains]
    if not all(l == chain_lengths[0] for l in chain_lengths):
        raise ValueError("所有链的长度必须相同")
    
    n = chain_lengths[0]
    chains = np.array(chains)
    
    if chains.ndim == 2:
        chains = chains[:, :, np.newaxis]
    
    dim = chains.shape[2]
    r_hat = np.zeros(dim)
    
    for d in range(dim):
        chain_means = np.mean(chains[:, :, d], axis=1)
        grand_mean = np.mean(chain_means)
        
        B_over_n = np.sum((chain_means - grand_mean) ** 2) / (m - 1)
        W = np.mean(np.var(chains[:, :, d], axis=1, ddof=1))
        
        var_plus = ((n - 1) / n) * W + ((m + 1) / m) * B_over_n
        r_hat[d] = np.sqrt(var_plus / W)
    
    return r_hat


def geweke_test(
    samples: np.ndarray,
    first_frac: float = 0.1,
    last_frac: float = 0.5
) -> Tuple[np.ndarray, np.ndarray]:
    """Geweke 收敛检验"""
    samples = np.asarray(samples)
    if samples.ndim == 1:
        samples = samples.reshape(-1, 1)
    
    n, dim = samples.shape
    
    n1 = int(n * first_frac)
    n2 = int(n * last_frac)
    
    if n1 < 10 or n2 < 10:
        raise ValueError("样本太小，无法进行 Geweke 检验")
    
    z_scores = np.zeros(dim)
    
    for d in range(dim):
        series = samples[:, d]
        
        mean1 = np.mean(series[:n1])
        mean2 = np.mean(series[-n2:])
        
        var1 = spectral_variance(series[:n1])
        var2 = spectral_variance(series[-n2:])
        
        if var1 + var2 > 0:
            z_scores[d] = (mean1 - mean2) / np.sqrt(var1 + var2)
        else:
            z_scores[d] = 0.0
    
    p_values = 2.0 * (1.0 - np.array([
        0.5 * (1 + math.erf(zs / np.sqrt(2))) if zs >= 0
        else 0.5 * (1 + math.erf(-zs / np.sqrt(2)))
        for zs in z_scores
    ]))
    
    return z_scores, p_values


def spectral_variance(series: np.ndarray) -> float:
    """估计谱方差"""
    n = len(series)
    if n == 0:
        return 0.0
    
    acf = autocorrelation(series, max_lag=int(n / 2))
    var_est = np.var(series, ddof=1)
    
    if var_est == 0:
        return 0.0
    
    lag = 0
    while lag < len(acf) - 1:
        if np.abs(acf[lag + 1]) < 0.05 or (lag + 1) % 2 == 1:
            pass
        lag += 1
    
    m = min(int(n / 2), 1000)
    sum_val = 1.0
    for k in range(1, m):
        sum_val += 2.0 * acf[k] * (1 - k / (m + 1))
    
    return var_est * sum_val


def trace_plot_stats(samples: np.ndarray) -> Dict[str, np.ndarray]:
    """计算 trace plot 相关统计量"""
    samples = np.asarray(samples)
    if samples.ndim == 1:
        samples = samples.reshape(-1, 1)
    
    n, dim = samples.shape
    
    stats = {
        'mean': np.mean(samples, axis=0),
        'std': np.std(samples, axis=0),
        'min': np.min(samples, axis=0),
        'max': np.max(samples, axis=0),
        'quantiles_25': np.percentile(samples, 25, axis=0),
        'quantiles_50': np.percentile(samples, 50, axis=0),
        'quantiles_75': np.percentile(samples, 75, axis=0)
    }
    
    return stats


def split_r_hat(chain: np.ndarray, split: int = 2) -> np.ndarray:
    """计算单链的 split-R-hat"""
    chain = np.asarray(chain)
    if chain.ndim == 1:
        chain = chain.reshape(-1, 1)
    
    n = len(chain)
    chunk_size = n // split
    
    chains = []
    for i in range(split):
        start = i * chunk_size
        end = start + chunk_size
        chains.append(chain[start:end])
    
    return gelman_rubin(chains)
