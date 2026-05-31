import numpy as np
import pandas as pd
from typing import Tuple, List, Optional
from dataclasses import dataclass, field
import warnings
warnings.filterwarnings('ignore')


@dataclass
class PMFResult:
    G: np.ndarray
    F: np.ndarray
    Q: float
    Q_history: List[float]
    n_factors: int
    species: List[str]
    source_names: List[str]
    residuals: np.ndarray
    scaled_residuals: np.ndarray


class PMF:
    def __init__(
        self,
        n_factors: int = 3,
        max_iter: int = 10000,
        tol: float = 1e-8,
        n_starts: int = 20,
        random_state: Optional[int] = None,
        source_names: Optional[List[str]] = None
    ):
        self.n_factors = n_factors
        self.max_iter = max_iter
        self.tol = tol
        self.n_starts = n_starts
        self.random_state = random_state
        self.source_names = source_names or [f'源{i+1}' for i in range(n_factors)]
        self.result_ = None
        
    def _initialize_matrices(self, n_samples: int, n_species: int) -> Tuple[np.ndarray, np.ndarray]:
        rng = np.random.RandomState(self.random_state)
        G = rng.rand(n_samples, self.n_factors)
        F = rng.rand(self.n_factors, n_species)
        return G, F
    
    def _compute_Q(self, X: np.ndarray, G: np.ndarray, F: np.ndarray, U: np.ndarray) -> float:
        residual = X - G @ F
        scaled = residual / U
        Q = np.sum(scaled ** 2)
        return Q
    
    def _update_g(self, X: np.ndarray, G: np.ndarray, F: np.ndarray, U: np.ndarray) -> np.ndarray:
        U_sq = U ** 2
        X_over_U = X / U_sq
        
        numerator = X_over_U @ F.T
        denominator = (G @ F) / U_sq @ F.T
        
        denominator = np.where(denominator <= 0, 1e-10, denominator)
        G_new = G * (numerator / denominator)
        return np.maximum(G_new, 0)
    
    def _update_f(self, X: np.ndarray, G: np.ndarray, F: np.ndarray, U: np.ndarray) -> np.ndarray:
        U_sq = U ** 2
        X_over_U = X / U_sq
        
        numerator = G.T @ X_over_U
        denominator = G.T @ ((G @ F) / U_sq)
        
        denominator = np.where(denominator <= 0, 1e-10, denominator)
        F_new = F * (numerator / denominator)
        return np.maximum(F_new, 0)
    
    def _normalize(self, G: np.ndarray, F: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        for k in range(self.n_factors):
            f_sum = np.sum(F[k, :])
            if f_sum > 0:
                F[k, :] = F[k, :] / f_sum
                G[:, k] = G[:, k] * f_sum
        return G, F
    
    def _fit_single(self, X: np.ndarray, U: np.ndarray) -> Tuple[np.ndarray, np.ndarray, float, List[float]]:
        n_samples, n_species = X.shape
        G, F = self._initialize_matrices(n_samples, n_species)
        
        Q_history = []
        Q_prev = self._compute_Q(X, G, F, U)
        Q_history.append(Q_prev)
        
        for i in range(self.max_iter):
            G = self._update_g(X, G, F, U)
            F = self._update_f(X, G, F, U)
            
            Q_curr = self._compute_Q(X, G, F, U)
            Q_history.append(Q_curr)
            
            if abs(Q_prev - Q_curr) / (Q_prev + 1e-10) < self.tol:
                break
                
            Q_prev = Q_curr
        
        G, F = self._normalize(G, F)
        return G, F, Q_curr, Q_history
    
    def fit(self, X: np.ndarray, U: Optional[np.ndarray] = None, species: Optional[List[str]] = None):
        n_samples, n_species = X.shape
        
        if U is None:
            U = 0.1 * X + 0.01 * np.mean(X, axis=0)
        
        if species is None:
            species = [f'物种{i+1}' for i in range(n_species)]
        
        best_Q = np.inf
        best_G = None
        best_F = None
        best_history = None
        
        for start in range(self.n_starts):
            if self.random_state is not None:
                self.random_state += 1
            G, F, Q, history = self._fit_single(X, U)
            
            if Q < best_Q:
                best_Q = Q
                best_G = G
                best_F = F
                best_history = history
        
        residuals = X - best_G @ best_F
        scaled_residuals = residuals / U
        
        self.result_ = PMFResult(
            G=best_G,
            F=best_F,
            Q=best_Q,
            Q_history=best_history,
            n_factors=self.n_factors,
            species=species,
            source_names=self.source_names,
            residuals=residuals,
            scaled_residuals=scaled_residuals
        )
        
        return self
    
    def transform(self, X_new: np.ndarray, U_new: Optional[np.ndarray] = None) -> np.ndarray:
        if self.result_ is None:
            raise ValueError("模型尚未拟合，请先调用fit方法")
        
        n_samples, n_species = X_new.shape
        
        if U_new is None:
            U_new = 0.1 * X_new + 0.01 * np.mean(X_new, axis=0)
        
        F = self.result_.F
        G = np.random.rand(n_samples, self.n_factors)
        
        Q_prev = self._compute_Q(X_new, G, F, U_new)
        
        for i in range(self.max_iter):
            G = self._update_g(X_new, G, F, U_new)
            Q_curr = self._compute_Q(X_new, G, F, U_new)
            
            if abs(Q_prev - Q_curr) / (Q_prev + 1e-10) < self.tol:
                break
            Q_prev = Q_curr
        
        return G
    
    def get_source_profile(self) -> pd.DataFrame:
        if self.result_ is None:
            raise ValueError("模型尚未拟合，请先调用fit方法")
        
        return pd.DataFrame(
            self.result_.F,
            index=self.result_.source_names,
            columns=self.result_.species
        )
    
    def get_source_contribution(self, index: Optional[pd.Index] = None) -> pd.DataFrame:
        if self.result_ is None:
            raise ValueError("模型尚未拟合，请先调用fit方法")
        
        df = pd.DataFrame(
            self.result_.G,
            columns=self.result_.source_names
        )
        
        if index is not None:
            df.index = index
        
        return df
    
    def get_statistics(self) -> dict:
        if self.result_ is None:
            raise ValueError("模型尚未拟合，请先调用fit方法")
        
        G = self.result_.G
        F = self.result_.F
        n_samples, n_species = G.shape[0], F.shape[1]
        n_params = self.n_factors * (n_samples + n_species)
        
        return {
            'Q值': self.result_.Q,
            'Q/自由度': self.result_.Q / (n_samples * n_species - n_params),
            '因子数': self.n_factors,
            '样本数': n_samples,
            '物种数': n_species,
            '迭代次数': len(self.result_.Q_history)
        }


@dataclass
class FactorSelectionResult:
    optimal_n_factors: int
    results: dict
    metrics: pd.DataFrame
    reason: str


def auto_select_factors(
    X: np.ndarray,
    U: Optional[np.ndarray] = None,
    species: Optional[List[str]] = None,
    min_factors: int = 2,
    max_factors: int = 8,
    n_runs: int = 10,
    max_iter: int = 5000,
    tol: float = 1e-6,
    random_state: Optional[int] = 42
) -> FactorSelectionResult:
    n_samples, n_species = X.shape
    
    if U is None:
        U = 0.1 * X + 0.01 * np.mean(X, axis=0)
    
    results = {}
    metrics_list = []
    
    for n_factors in range(min_factors, max_factors + 1):
        Q_values = []
        residual_stats = []
        stability_scores = []
        runs_data = []
        
        for run in range(n_runs):
            pmf = PMF(
                n_factors=n_factors,
                max_iter=max_iter,
                tol=tol,
                n_starts=3,
                random_state=random_state + run if random_state else None
            )
            pmf.fit(X, U, species)
            
            Q_values.append(pmf.result_.Q)
            runs_data.append({'G': pmf.result_.G, 'F': pmf.result_.F})
            
            scaled_res = pmf.result_.scaled_residuals
            residual_stats.append({
                'mean': np.mean(scaled_res),
                'std': np.std(scaled_res),
                'outlier_ratio': np.mean(np.abs(scaled_res) > 3)
            })
        
        Q_mean = np.mean(Q_values)
        Q_std = np.std(Q_values)
        Q_ratio = Q_mean / (n_samples * n_species - n_factors * (n_samples + n_species))
        
        explained_variance = calculate_explained_variance(X, runs_data[0]['G'], runs_data[0]['F'])
        
        stability_score = calculate_stability(runs_data)
        
        residual_mean = np.mean([r['mean'] for r in residual_stats])
        residual_std = np.mean([r['std'] for r in residual_stats])
        outlier_ratio = np.mean([r['outlier_ratio'] for r in residual_stats])
        
        metrics_list.append({
            '因子数': n_factors,
            'Q均值': Q_mean,
            'Q标准差': Q_std,
            'Q/自由度': Q_ratio,
            '解释方差(%)': explained_variance * 100,
            '稳定性得分': stability_score,
            '残差均值': residual_mean,
            '残差标准差': residual_std,
            '异常值比例(%)': outlier_ratio * 100
        })
        
        results[n_factors] = {
            'Q_values': Q_values,
            'residual_stats': residual_stats,
            'runs_data': runs_data,
            'Q_mean': Q_mean,
            'Q_std': Q_std,
            'Q_ratio': Q_ratio,
            'explained_variance': explained_variance,
            'stability_score': stability_score
        }
    
    metrics_df = pd.DataFrame(metrics_list)
    
    optimal_n = select_optimal_factor(metrics_df, min_factors, max_factors)
    
    reason = get_selection_reason(metrics_df, optimal_n)
    
    return FactorSelectionResult(
        optimal_n_factors=optimal_n,
        results=results,
        metrics=metrics_df,
        reason=reason
    )


def calculate_explained_variance(X: np.ndarray, G: np.ndarray, F: np.ndarray) -> float:
    X_pred = G @ F
    ss_total = np.sum(X ** 2)
    ss_residual = np.sum((X - X_pred) ** 2)
    return 1 - ss_residual / ss_total


def calculate_stability(runs_data: List[dict]) -> float:
    n_runs = len(runs_data)
    if n_runs < 2:
        return 1.0
    
    n_factors = runs_data[0]['F'].shape[0]
    n_species = runs_data[0]['F'].shape[1]
    
    F_reference = runs_data[0]['F']
    correlations = []
    
    for run in runs_data[1:]:
        F_curr = run['F']
        
        perm = find_best_permutation(F_reference, F_curr)
        F_curr_permuted = F_curr[perm]
        
        corr = np.corrcoef(F_reference.flatten(), F_curr_permuted.flatten())[0, 1]
        correlations.append(corr)
    
    return np.mean(correlations) if correlations else 1.0


def find_best_permutation(F1: np.ndarray, F2: np.ndarray) -> np.ndarray:
    n_factors = F1.shape[0]
    permutation = np.zeros(n_factors, dtype=int)
    used = set()
    
    for i in range(n_factors):
        best_j = -1
        best_corr = -1
        
        for j in range(n_factors):
            if j in used:
                continue
            corr = np.corrcoef(F1[i], F2[j])[0, 1]
            if corr > best_corr:
                best_corr = corr
                best_j = j
        
        permutation[i] = best_j
        used.add(best_j)
    
    return permutation


def select_optimal_factor(metrics_df: pd.DataFrame, min_factors: int, max_factors: int) -> int:
    metrics = metrics_df.copy()
    
    q_ratio = metrics['Q/自由度'].values
    stability = metrics['稳定性得分'].values
    explained_var = metrics['解释方差(%)'].values
    outlier_ratio = metrics['异常值比例(%)'].values
    
    q_scores = np.zeros(len(q_ratio))
    for i in range(len(q_ratio)):
        if 0.5 <= q_ratio[i] <= 2.0:
            q_scores[i] = 3
        elif 0.3 <= q_ratio[i] <= 3.0:
            q_scores[i] = 2
        elif q_ratio[i] > 0:
            q_scores[i] = 1
    
    stability_scores = np.where(stability >= 0.8, 3, np.where(stability >= 0.6, 2, 1))
    
    ev_diff = np.diff(explained_var)
    ev_scores = np.zeros(len(explained_var))
    ev_scores[0] = 2
    for i in range(1, len(ev_scores)):
        if i - 1 < len(ev_diff) and ev_diff[i-1] > 5:
            ev_scores[i] = 3
        elif i - 1 < len(ev_diff) and ev_diff[i-1] > 2:
            ev_scores[i] = 2
        else:
            ev_scores[i] = 1
    
    outlier_scores = np.where(outlier_ratio < 2, 3, np.where(outlier_ratio < 5, 2, 1))
    
    total_scores = q_scores + stability_scores + ev_scores + outlier_scores
    
    for i in range(1, len(total_scores)):
        total_scores[i] -= 0.1 * i
    
    optimal_idx = np.argmax(total_scores)
    return min_factors + optimal_idx


def get_selection_reason(metrics_df: pd.DataFrame, optimal_n: int) -> str:
    row = metrics_df[metrics_df['因子数'] == optimal_n].iloc[0]
    
    reasons = []
    reasons.append(f"Q/自由度 = {row['Q/自由度']:.3f}")
    reasons.append(f"解释方差 = {row['解释方差(%)']:.1f}%")
    reasons.append(f"稳定性得分 = {row['稳定性得分']:.3f}")
    reasons.append(f"异常值比例 = {row['异常值比例(%)']:.1f}%")
    
    return "; ".join(reasons)
