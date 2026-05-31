import numpy as np
import pandas as pd
from typing import Tuple, List, Optional, Dict
from dataclasses import dataclass
from pmf_model import PMF
import warnings
warnings.filterwarnings('ignore')


@dataclass
class UncertaintyResult:
    F_mean: np.ndarray
    F_std: np.ndarray
    F_lower: np.ndarray
    F_upper: np.ndarray
    G_mean: np.ndarray
    G_std: np.ndarray
    G_lower: np.ndarray
    G_upper: np.ndarray
    bootstrap_runs: int
    Q_values: List[float]
    species: List[str]
    source_names: List[str]
    index: Optional[pd.Index] = None
    F_percentiles: Optional[dict] = None
    G_percentiles: Optional[dict] = None
    confidence_levels: Optional[List[int]] = None


DEFAULT_CONFIDENCE_LEVELS = [10, 50, 80, 90, 95]


class BootstrapAnalysis:
    def __init__(
        self,
        n_bootstrap: int = 100,
        n_factors: int = 3,
        max_iter: int = 5000,
        tol: float = 1e-6,
        random_state: Optional[int] = None,
        source_names: Optional[List[str]] = None,
        confidence_levels: Optional[List[int]] = None
    ):
        self.n_bootstrap = n_bootstrap
        self.n_factors = n_factors
        self.max_iter = max_iter
        self.tol = tol
        self.random_state = random_state
        self.source_names = source_names
        self.confidence_levels = confidence_levels or DEFAULT_CONFIDENCE_LEVELS
        
    def run(
        self,
        X: np.ndarray,
        U: np.ndarray,
        species: List[str],
        index: Optional[pd.Index] = None,
        base_F: Optional[np.ndarray] = None
    ) -> UncertaintyResult:
        n_samples, n_species = X.shape
        
        all_G = []
        all_F = []
        all_Q = []
        
        rng = np.random.RandomState(self.random_state)
        
        for i in range(self.n_bootstrap):
            sample_idx = rng.choice(n_samples, size=n_samples, replace=True)
            X_boot = X[sample_idx]
            U_boot = U[sample_idx]
            
            pmf = PMF(
                n_factors=self.n_factors,
                max_iter=self.max_iter,
                tol=self.tol,
                n_starts=5,
                random_state=self.random_state + i if self.random_state else None,
                source_names=self.source_names
            )
            
            try:
                pmf.fit(X_boot, U_boot, species)
                
                F_boot = pmf.result_.F
                G_boot_raw = pmf.result_.G
                
                if base_F is not None:
                    F_boot, perm = self._match_factors(F_boot, base_F)
                    G_boot_raw = G_boot_raw[:, perm]
                
                G_boot = np.zeros((n_samples, self.n_factors))
                for j, orig_j in enumerate(sample_idx):
                    G_boot[orig_j] += G_boot_raw[j]
                
                for k in range(n_samples):
                    count = np.sum(sample_idx == k)
                    if count > 0:
                        G_boot[k] /= count
                
                all_F.append(F_boot)
                all_G.append(G_boot)
                all_Q.append(pmf.result_.Q)
                
            except Exception as e:
                continue
        
        if len(all_F) == 0:
            raise ValueError("所有bootstrap运行均失败")
        
        all_F = np.array(all_F)
        all_G = np.array(all_G)
        all_Q = np.array(all_Q)
        
        F_mean = np.mean(all_F, axis=0)
        F_std = np.std(all_F, axis=0)
        G_mean = np.mean(all_G, axis=0)
        G_std = np.std(all_G, axis=0)
        
        F_percentiles = {}
        G_percentiles = {}
        for cl in self.confidence_levels:
            lower_p = (100 - cl) / 2
            upper_p = 100 - lower_p
            F_percentiles[cl] = {
                'lower': np.percentile(all_F, lower_p, axis=0),
                'upper': np.percentile(all_F, upper_p, axis=0)
            }
            G_percentiles[cl] = {
                'lower': np.percentile(all_G, lower_p, axis=0),
                'upper': np.percentile(all_G, upper_p, axis=0)
            }
        
        F_lower = F_percentiles[95]['lower'] if 95 in F_percentiles else F_percentiles[list(F_percentiles.keys())[0]]['lower']
        F_upper = F_percentiles[95]['upper'] if 95 in F_percentiles else F_percentiles[list(F_percentiles.keys())[0]]['upper']
        G_lower = G_percentiles[95]['lower'] if 95 in G_percentiles else G_percentiles[list(G_percentiles.keys())[0]]['lower']
        G_upper = G_percentiles[95]['upper'] if 95 in G_percentiles else G_percentiles[list(G_percentiles.keys())[0]]['upper']
        
        source_names = self.source_names or [f'源{i+1}' for i in range(self.n_factors)]
        
        return UncertaintyResult(
            F_mean=F_mean,
            F_std=F_std,
            F_lower=F_lower,
            F_upper=F_upper,
            G_mean=G_mean,
            G_std=G_std,
            G_lower=G_lower,
            G_upper=G_upper,
            bootstrap_runs=len(all_F),
            Q_values=all_Q.tolist(),
            species=species,
            source_names=source_names,
            index=index,
            F_percentiles=F_percentiles,
            G_percentiles=G_percentiles,
            confidence_levels=self.confidence_levels
        )
    
    def _match_factors(self, F_boot: np.ndarray, F_base: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        n_factors = F_boot.shape[0]
        permutation = np.zeros(n_factors, dtype=int)
        used = set()
        
        for i in range(n_factors):
            best_j = -1
            best_corr = -1
            
            for j in range(n_factors):
                if j in used:
                    continue
                
                corr = np.corrcoef(F_boot[i], F_base[j])[0, 1]
                if corr > best_corr:
                    best_corr = corr
                    best_j = j
            
            permutation[i] = best_j
            used.add(best_j)
        
        return F_boot[permutation], permutation


class DisplacementAnalysis:
    def __init__(
        self,
        n_factors: int = 3,
        dQ_step: float = 1.0,
        max_iter: int = 2000,
        random_state: Optional[int] = None
    ):
        self.n_factors = n_factors
        self.dQ_step = dQ_step
        self.max_iter = max_iter
        self.random_state = random_state
        
    def run(
        self,
        X: np.ndarray,
        U: np.ndarray,
        base_G: np.ndarray,
        base_F: np.ndarray,
        species: List[str]
    ) -> Dict:
        n_samples, n_species = X.shape
        base_Q = self._compute_Q(X, base_G, base_F, U)
        
        displacement_results = {
            'F_displacement': [],
            'G_displacement': [],
            'F_lower': [],
            'F_upper': [],
            'G_lower': [],
            'G_upper': [],
        }
        
        target_Q = base_Q + self.dQ_step
        
        for k in range(self.n_factors):
            for j in range(n_species):
                F_high, F_low = self._displace_element(
                    X, U, base_G, base_F, target_Q, 'F', k, j
                )
                displacement_results['F_displacement'].append((k, j, F_low, F_high))
            
            for i in range(n_samples):
                G_high, G_low = self._displace_element(
                    X, U, base_G, base_F, target_Q, 'G', i, k
                )
                displacement_results['G_displacement'].append((i, k, G_low, G_high))
        
        return displacement_results
    
    def _compute_Q(self, X: np.ndarray, G: np.ndarray, F: np.ndarray, U: np.ndarray) -> float:
        residual = X - G @ F
        scaled = residual / U
        return np.sum(scaled ** 2)
    
    def _displace_element(
        self,
        X: np.ndarray,
        U: np.ndarray,
        base_G: np.ndarray,
        base_F: np.ndarray,
        target_Q: float,
        matrix: str,
        row: int,
        col: int
    ) -> Tuple[float, float]:
        G = base_G.copy()
        F = base_F.copy()
        
        if matrix == 'F':
            base_val = F[row, col]
        else:
            base_val = G[row, col]
        
        delta = base_val * 0.1 if base_val > 0 else 0.01
        
        def get_Q(val):
            if matrix == 'F':
                F[row, col] = val
            else:
                G[row, col] = val
            return self._compute_Q(X, G, F, U)
        
        high_val = base_val
        while get_Q(high_val) < target_Q and high_val < base_val * 100:
            high_val += delta
            delta *= 1.1
        
        low_val = base_val
        delta = base_val * 0.1 if base_val > 0 else 0.01
        while get_Q(low_val) < target_Q and low_val > 0:
            low_val -= delta
            delta *= 1.1
            if low_val < 0:
                low_val = 0
                break
        
        return max(high_val, base_val), min(low_val, base_val)


def calculate_uncertainty_metrics(
    uncertainty_result: UncertaintyResult,
    confidence_level: Optional[int] = None
) -> pd.DataFrame:
    n_factors, n_species = uncertainty_result.F_mean.shape
    
    metrics = []
    for i in range(n_factors):
        for j in range(n_species):
            mean = uncertainty_result.F_mean[i, j]
            std = uncertainty_result.F_std[i, j]
            cv = (std / mean * 100) if mean > 0 else np.nan
            
            row = {
                '污染源': uncertainty_result.source_names[i],
                '物种': uncertainty_result.species[j],
                '平均值': mean,
                '标准差': std,
                '变异系数(%)': cv,
            }
            
            if uncertainty_result.F_percentiles is not None:
                cl_to_use = confidence_level if confidence_level in uncertainty_result.F_percentiles else 95
                if cl_to_use in uncertainty_result.F_percentiles:
                    row[f'{cl_to_use}%置信下限'] = uncertainty_result.F_percentiles[cl_to_use]['lower'][i, j]
                    row[f'{cl_to_use}%置信上限'] = uncertainty_result.F_percentiles[cl_to_use]['upper'][i, j]
            else:
                row['95%置信下限'] = uncertainty_result.F_lower[i, j]
                row['95%置信上限'] = uncertainty_result.F_upper[i, j]
            
            metrics.append(row)
    
    return pd.DataFrame(metrics)


def calculate_contribution_uncertainty(
    uncertainty_result: UncertaintyResult
) -> pd.DataFrame:
    n_samples = uncertainty_result.G_mean.shape[0]
    n_factors = uncertainty_result.G_mean.shape[1]
    
    source_names = uncertainty_result.source_names
    index = uncertainty_result.index or pd.RangeIndex(n_samples)
    
    data = []
    for i in range(n_samples):
        row = {'日期': index[i]}
        for k in range(n_factors):
            mean = uncertainty_result.G_mean[i, k]
            std = uncertainty_result.G_std[i, k]
            lower = uncertainty_result.G_lower[i, k]
            upper = uncertainty_result.G_upper[i, k]
            
            row[f'{source_names[k]}_平均值'] = mean
            row[f'{source_names[k]}_标准差'] = std
            row[f'{source_names[k]}_下限'] = lower
            row[f'{source_names[k]}_上限'] = upper
        
        data.append(row)
    
    return pd.DataFrame(data).set_index('日期')


def run_complete_uncertainty_analysis(
    X: np.ndarray,
    U: np.ndarray,
    species: List[str],
    n_factors: int = 3,
    n_bootstrap: int = 50,
    base_F: Optional[np.ndarray] = None,
    source_names: Optional[List[str]] = None,
    index: Optional[pd.Index] = None,
    random_state: Optional[int] = 42,
    confidence_levels: Optional[List[int]] = None
) -> UncertaintyResult:
    bootstrap = BootstrapAnalysis(
        n_bootstrap=n_bootstrap,
        n_factors=n_factors,
        max_iter=3000,
        tol=1e-6,
        random_state=random_state,
        source_names=source_names,
        confidence_levels=confidence_levels
    )
    
    result = bootstrap.run(X, U, species, index=index, base_F=base_F)
    
    return result


def get_confidence_interval_data(
    uncertainty_result: UncertaintyResult,
    confidence_level: int,
    source_idx: int
) -> Tuple[np.ndarray, np.ndarray]:
    if uncertainty_result.G_percentiles is None or confidence_level not in uncertainty_result.G_percentiles:
        return uncertainty_result.G_lower[:, source_idx], uncertainty_result.G_upper[:, source_idx]
    
    return (
        uncertainty_result.G_percentiles[confidence_level]['lower'][:, source_idx],
        uncertainty_result.G_percentiles[confidence_level]['upper'][:, source_idx]
    )
