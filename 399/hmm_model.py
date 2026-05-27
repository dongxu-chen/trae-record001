import numpy as np
import pandas as pd
from hmmlearn import hmm
from scipy.stats import norm
from typing import Dict, List, Tuple, Optional
import joblib
import os


class ApplianceHMM:
    def __init__(self, 
                 n_states: int, 
                 power_levels: Optional[np.ndarray] = None,
                 name: str = "appliance"):
        self.n_states = n_states
        self.name = name
        self.power_levels = power_levels
        self.model = None
        self.is_fitted = False
    
    def fit(self, power_data: np.ndarray, n_iter: int = 100) -> 'ApplianceHMM':
        power_data = power_data.reshape(-1, 1)
        
        self.model = hmm.GaussianHMM(
            n_components=self.n_states,
            covariance_type="diag",
            n_iter=n_iter,
            random_state=42,
            tol=1e-3
        )
        
        self.model.fit(power_data)
        
        sorted_indices = np.argsort(self.model.means_.flatten())
        self.model.means_ = self.model.means_[sorted_indices]
        self.model.covars_ = self.model.covars_[sorted_indices]
        
        new_transmat = np.zeros_like(self.model.transmat_)
        for i in range(self.n_states):
            for j in range(self.n_states):
                new_transmat[i, j] = self.model.transmat_[sorted_indices[i], sorted_indices[j]]
        new_transmat = new_transmat / new_transmat.sum(axis=1, keepdims=True)
        self.model.transmat_ = new_transmat
        
        new_startprob = self.model.startprob_[sorted_indices]
        new_startprob = new_startprob / new_startprob.sum()
        self.model.startprob_ = new_startprob
        
        self.power_levels = self.model.means_.flatten()
        self.is_fitted = True
        
        return self
    
    def decode_states(self, power_data: np.ndarray) -> np.ndarray:
        if not self.is_fitted:
            raise RuntimeError("Model not fitted. Call fit() first.")
        
        power_data = power_data.reshape(-1, 1)
        logprob, states = self.model.decode(power_data, algorithm="viterbi")
        return states
    
    def get_power_from_states(self, states: np.ndarray) -> np.ndarray:
        if self.power_levels is None:
            raise RuntimeError("Power levels not available.")
        return self.power_levels[states]
    
    def save(self, filepath: str) -> None:
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        joblib.dump({
            'model': self.model,
            'n_states': self.n_states,
            'name': self.name,
            'power_levels': self.power_levels,
            'is_fitted': self.is_fitted
        }, filepath)
    
    @classmethod
    def load(cls, filepath: str) -> 'ApplianceHMM':
        data = joblib.load(filepath)
        instance = cls(
            n_states=data['n_states'],
            power_levels=data['power_levels'],
            name=data['name']
        )
        instance.model = data['model']
        instance.is_fitted = data['is_fitted']
        return instance


class HMMLoadDisaggregator:
    def __init__(self, appliance_config: Dict[str, int]):
        self.appliance_config = appliance_config
        self.models: Dict[str, ApplianceHMM] = {}
        self.is_fitted = False
    
    def fit(self, 
            aggregated_power: np.ndarray, 
            individual_powers: Dict[str, np.ndarray]) -> 'HMMLoadDisaggregator':
        
        for appliance, n_states in self.appliance_config.items():
            if appliance in individual_powers:
                print(f"Training HMM for {appliance}...")
                model = ApplianceHMM(n_states=n_states, name=appliance)
                model.fit(individual_powers[appliance])
                self.models[appliance] = model
        
        self.is_fitted = True
        return self
    
    def disaggregate(self, 
                     aggregated_power: np.ndarray,
                     method: str = 'viterbi_combinatorial') -> Dict[str, np.ndarray]:
        if not self.is_fitted:
            raise RuntimeError("Models not fitted. Call fit() first.")
        
        if method == 'viterbi_combinatorial':
            return self._disaggregate_combinatorial(aggregated_power)
        elif method == 'iterative':
            return self._disaggregate_iterative(aggregated_power)
        else:
            raise ValueError(f"Unknown method: {method}")
    
    def _disaggregate_iterative(self, 
                                aggregated_power: np.ndarray) -> Dict[str, np.ndarray]:
        remaining_power = aggregated_power.copy()
        results = {}
        
        sorted_appliances = sorted(
            self.appliance_config.keys(),
            key=lambda x: -np.max(self.models[x].power_levels)
        )
        
        for appliance in sorted_appliances:
            model = self.models[appliance]
            states = model.decode_states(remaining_power)
            power = model.get_power_from_states(states)
            results[appliance] = power
            remaining_power = np.maximum(0, remaining_power - power)
        
        return results
    
    def _disaggregate_combinatorial(self, 
                                     aggregated_power: np.ndarray) -> Dict[str, np.ndarray]:
        n_samples = len(aggregated_power)
        n_appliances = len(self.models)
        
        appliance_list = list(self.models.keys())
        state_combinations = []
        
        for appliance in appliance_list:
            levels = self.models[appliance].power_levels
            state_combinations.append(levels)
        
        from itertools import product
        all_combos = list(product(*state_combinations))
        combo_sums = np.array([sum(c) for c in all_combos])
        
        states_history = {app: np.zeros(n_samples, dtype=int) for app in appliance_list}
        
        for i in range(n_samples):
            target = aggregated_power[i]
            closest_idx = np.argmin(np.abs(combo_sums - target))
            closest_combo = all_combos[closest_idx]
            
            for j, appliance in enumerate(appliance_list):
                levels = self.models[appliance].power_levels
                states_history[appliance][i] = np.argmin(np.abs(levels - closest_combo[j]))
        
        results = {}
        for appliance in appliance_list:
            model = self.models[appliance]
            smoothed_states = self._smooth_states(states_history[appliance], model.n_states)
            results[appliance] = model.get_power_from_states(smoothed_states)
        
        return results
    
    def _smooth_states(self, states: np.ndarray, n_states: int, window: int = 5) -> np.ndarray:
        from scipy.ndimage import median_filter
        return median_filter(states, size=window)
    
    def save_models(self, directory: str) -> None:
        os.makedirs(directory, exist_ok=True)
        for name, model in self.models.items():
            model.save(os.path.join(directory, f'{name}_hmm.pkl'))
    
    @classmethod
    def load_models(cls, directory: str, appliance_config: Dict[str, int]) -> 'HMMLoadDisaggregator':
        disaggregator = cls(appliance_config)
        for appliance in appliance_config.keys():
            filepath = os.path.join(directory, f'{appliance}_hmm.pkl')
            if os.path.exists(filepath):
                disaggregator.models[appliance] = ApplianceHMM.load(filepath)
        disaggregator.is_fitted = True
        return disaggregator


def estimate_performance(ground_truth: Dict[str, np.ndarray],
                         predictions: Dict[str, np.ndarray]) -> Dict[str, Dict[str, float]]:
    results = {}
    
    for appliance in ground_truth.keys():
        if appliance in predictions:
            y_true = ground_truth[appliance]
            y_pred = predictions[appliance]
            
            mae = np.mean(np.abs(y_true - y_pred))
            rmse = np.sqrt(np.mean((y_true - y_pred) ** 2))
            mape = np.mean(np.abs((y_true - y_pred) / (y_true + 1e-8))) * 100
            
            ss_res = np.sum((y_true - y_pred) ** 2)
            ss_tot = np.sum((y_true - np.mean(y_true)) ** 2)
            r2 = 1 - (ss_res / (ss_tot + 1e-8))
            
            results[appliance] = {
                'MAE': mae,
                'RMSE': rmse,
                'MAPE': mape,
                'R2': r2
            }
    
    return results


if __name__ == '__main__':
    from data_generator import generate_aggregated_data
    
    print("Generating test data...")
    df = generate_aggregated_data(days=3, sample_interval_min=5)
    
    appliance_config = {
        'air_conditioner': 4,
        'refrigerator': 2,
        'washing_machine': 3,
        'lighting': 3
    }
    
    individual_powers = {}
    for app in appliance_config.keys():
        individual_powers[app] = df[f'{app}_power'].values
    
    print("Training HMM disaggregator...")
    disaggregator = HMMLoadDisaggregator(appliance_config)
    disaggregator.fit(df['total_power'].values, individual_powers)
    
    print("Disaggregating...")
    results = disaggregator.disaggregate(df['total_power'].values, method='combinatorial')
    
    print("\nPerformance metrics:")
    performance = estimate_performance(individual_powers, results)
    for app, metrics in performance.items():
        print(f"\n{app}:")
        for metric, value in metrics.items():
            print(f"  {metric}: {value:.2f}")
