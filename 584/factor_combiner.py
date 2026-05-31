import numpy as np
import pandas as pd
from typing import List, Dict, Tuple
from scipy.optimize import minimize
import warnings
warnings.filterwarnings('ignore')
from config import Config

class FactorCombiner:
    def __init__(self, method: str = 'equal_weight'):
        self.method = method
        self.weights = None
        self.optimization_history = []
    
    def calculate_correlation_matrix(self, factors: List[pd.Series]) -> pd.DataFrame:
        factor_df = pd.concat([f for f in factors], axis=1)
        return factor_df.corr()
    
    def select_low_correlation_factors(self, factors: List[pd.Series], 
                                      factor_names: List[str],
                                      max_corr: float = None) -> Tuple[List[int], List[str]]:
        max_corr = max_corr or Config.MAX_CORRELATION
        corr_matrix = self.calculate_correlation_matrix(factors)
        
        selected_indices = []
        selected_names = []
        
        for i in range(len(factors)):
            if i == 0:
                selected_indices.append(i)
                selected_names.append(factor_names[i])
            else:
                max_corr_with_selected = corr_matrix.iloc[i, selected_indices].abs().max()
                if max_corr_with_selected < max_corr:
                    selected_indices.append(i)
                    selected_names.append(factor_names[i])
        
        return selected_indices, selected_names
    
    def equal_weight(self, n_factors: int) -> np.ndarray:
        return np.ones(n_factors) / n_factors
    
    def ic_weight(self, ic_values: List[float]) -> np.ndarray:
        weights = np.array(ic_values)
        weights = np.maximum(weights, 0)
        if weights.sum() > 0:
            weights = weights / weights.sum()
        else:
            weights = np.ones(len(weights)) / len(weights)
        return weights
    
    def ir_weight(self, ir_values: List[float]) -> np.ndarray:
        weights = np.array(ir_values)
        weights = np.maximum(weights, 0)
        if weights.sum() > 0:
            weights = weights / weights.sum()
        else:
            weights = np.ones(len(weights)) / len(weights)
        return weights
    
    def max_ir_optimization(self, factors: List[pd.Series], 
                             forward_returns: pd.Series,
                             ic_values: List[float],
                             l2_reg: float = 0.01,
                             turnover_penalty: float = 0.0,
                             turnover_values: List[float] = None) -> np.ndarray:
        n = len(factors)
        factor_df = pd.concat([f for f in factors], axis=1)
        factor_cov = factor_df.cov().values
        
        self.optimization_history = []
        
        def objective(weights):
            portfolio_ic = np.dot(weights, np.array(ic_values))
            portfolio_risk = np.sqrt(np.dot(weights.T, np.dot(factor_cov, weights)) + 1e-8)
            l2_penalty = l2_reg * np.sum(weights ** 2)
            
            turnover_cost = 0.0
            if turnover_penalty > 0 and turnover_values is not None:
                turnover_cost = turnover_penalty * np.dot(weights, np.array(turnover_values))
            
            objective_value = portfolio_ic / portfolio_risk - l2_penalty - turnover_cost
            
            self.optimization_history.append({
                'weights': weights.copy(),
                'portfolio_ic': portfolio_ic,
                'portfolio_risk': portfolio_risk,
                'l2_penalty': l2_penalty,
                'turnover_cost': turnover_cost,
                'objective': objective_value
            })
            
            return -objective_value
        
        constraints = ({'type': 'eq', 'fun': lambda x: np.sum(x) - 1})
        bounds = tuple((0, 1) for _ in range(n))
        x0 = np.ones(n) / n
        
        result = minimize(objective, x0, method='SLSQP', bounds=bounds, constraints=constraints)
        
        weights = result.x
        weights = np.maximum(weights, 0)
        weights = weights / weights.sum()
        
        return weights
    
    def risk_parity_optimization(self, factors: List[pd.Series],
                                  l2_reg: float = 0.01) -> np.ndarray:
        n = len(factors)
        factor_df = pd.concat([f for f in factors], axis=1)
        factor_cov = factor_df.cov().values
        
        def objective(weights):
            weights = np.maximum(weights, 1e-8)
            weights = weights / weights.sum()
            
            portfolio_var = np.dot(weights.T, np.dot(factor_cov, weights))
            marginal_risk = np.dot(factor_cov, weights)
            risk_contribution = weights * marginal_risk / portfolio_var
            target_risk = 1.0 / n
            
            risk_parity_error = np.sum((risk_contribution - target_risk) ** 2)
            l2_penalty = l2_reg * np.sum(weights ** 2)
            
            return risk_parity_error + l2_penalty
        
        constraints = ({'type': 'eq', 'fun': lambda x: np.sum(x) - 1})
        bounds = tuple((1e-4, 1) for _ in range(n))
        x0 = np.ones(n) / n
        
        result = minimize(objective, x0, method='SLSQP', bounds=bounds, constraints=constraints)
        
        weights = result.x
        weights = weights / weights.sum()
        
        return weights
    
    def combine_factors(self, factors: List[pd.Series], 
                       factor_evaluations: List[Dict],
                       forward_returns: pd.Series,
                       method: str = None,
                       l2_reg: float = 0.01,
                       turnover_penalty: float = 0.0) -> Tuple[pd.Series, np.ndarray]:
        method = method or self.method
        
        ic_values = [evl['ic_mean'] for evl in factor_evaluations]
        ir_values = [evl['ir'] if not np.isnan(evl['ir']) else 0 for evl in factor_evaluations]
        turnover_values = [evl['turnover'] for evl in factor_evaluations]
        
        if method == 'equal_weight':
            weights = self.equal_weight(len(factors))
        elif method == 'ic_weight':
            weights = self.ic_weight(ic_values)
        elif method == 'ir_weight':
            weights = self.ir_weight(ir_values)
        elif method == 'max_ir':
            weights = self.max_ir_optimization(
                factors, forward_returns, ic_values, 
                l2_reg=l2_reg,
                turnover_penalty=turnover_penalty,
                turnover_values=turnover_values
            )
        elif method == 'risk_parity':
            weights = self.risk_parity_optimization(factors, l2_reg=l2_reg)
        else:
            weights = self.equal_weight(len(factors))
        
        combined_factor = pd.Series(0, index=factors[0].index)
        for i, factor in enumerate(factors):
            combined_factor += weights[i] * factor
        
        self.weights = weights
        return combined_factor, weights
    
    def get_weight_summary(self, factor_names: List[str]) -> pd.DataFrame:
        return pd.DataFrame({
            '因子': factor_names,
            '权重': self.weights
        }).round(4)
    
    def calculate_weight_stability(self, weights_history: List[np.ndarray]) -> float:
        if len(weights_history) < 2:
            return 1.0
        
        weights_matrix = np.array(weights_history)
        weight_std = np.std(weights_matrix, axis=0)
        weight_mean = np.mean(weights_matrix, axis=0)
        
        stability = 1 - np.mean(weight_std / (weight_mean + 1e-8))
        return max(0, stability)
