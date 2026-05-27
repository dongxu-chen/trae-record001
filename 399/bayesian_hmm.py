import numpy as np
import pandas as pd
from scipy.stats import norm, gamma, dirichlet
from scipy.special import logsumexp
from typing import Dict, List, Tuple, Optional
import joblib
import os
import warnings
warnings.filterwarnings('ignore')


class DirichletProcessHMM:
    def __init__(self, 
                 alpha: float = 1.0,
                 max_states: int = 10,
                 name: str = "appliance"):
        self.alpha = alpha
        self.max_states = max_states
        self.name = name
        
        self.n_states = max_states
        self.effective_states = max_states
        
        self.transition_params = None
        self.emission_means = None
        self.emission_vars = None
        self.start_probs = None
        
        self.is_fitted = False
        self.state_weights = None
    
    def _init_params(self, data: np.ndarray):
        n_samples = len(data)
        
        sorted_data = np.sort(data)
        quantiles = np.linspace(0, 100, self.max_states + 2)[1:-1]
        self.emission_means = np.percentile(sorted_data, quantiles)
        
        data_range = np.max(data) - np.min(data)
        self.emission_vars = np.ones(self.max_states) * (data_range / (self.max_states * 2)) ** 2
        
        self.transition_params = np.ones((self.max_states, self.max_states)) * 0.1
        for i in range(self.max_states):
            self.transition_params[i, i] = 5.0
        
        self.start_probs = np.ones(self.max_states) / self.max_states
        
        self.state_weights = np.ones(self.max_states) / self.max_states
    
    def _emission_logprob(self, data: np.ndarray) -> np.ndarray:
        n_samples = len(data)
        log_probs = np.zeros((n_samples, self.max_states))
        
        for s in range(self.max_states):
            log_probs[:, s] = norm.logpdf(
                data, 
                loc=self.emission_means[s], 
                scale=np.sqrt(self.emission_vars[s]) + 1e-8
            )
        
        return log_probs
    
    def _forward(self, log_emission: np.ndarray) -> Tuple[np.ndarray, float]:
        n_samples = log_emission.shape[0]
        
        log_alpha = np.zeros((n_samples, self.max_states))
        log_alpha[0] = np.log(self.start_probs + 1e-10) + log_emission[0]
        
        trans_log = np.log(self.transition_params + 1e-10)
        
        for t in range(1, n_samples):
            for j in range(self.max_states):
                log_alpha[t, j] = logsumexp(log_alpha[t-1] + trans_log[:, j]) + log_emission[t, j]
        
        log_likelihood = logsumexp(log_alpha[-1])
        return log_alpha, log_likelihood
    
    def _backward(self, log_emission: np.ndarray) -> np.ndarray:
        n_samples = log_emission.shape[0]
        
        log_beta = np.zeros((n_samples, self.max_states))
        log_beta[-1] = 0.0
        
        trans_log = np.log(self.transition_params + 1e-10)
        
        for t in range(n_samples - 2, -1, -1):
            for i in range(self.max_states):
                log_beta[t, i] = logsumexp(trans_log[i, :] + log_emission[t+1, :] + log_beta[t+1, :])
        
        return log_beta
    
    def _compute_state_probs(self, log_alpha: np.ndarray, log_beta: np.ndarray) -> np.ndarray:
        log_gamma = log_alpha + log_beta
        log_gamma = log_gamma - logsumexp(log_gamma, axis=1, keepdims=True)
        return np.exp(log_gamma)
    
    def _compute_transition_probs(self, log_alpha: np.ndarray, log_beta: np.ndarray, 
                                   log_emission: np.ndarray) -> np.ndarray:
        n_samples = log_emission.shape[0]
        
        log_xi = np.zeros((n_samples - 1, self.max_states, self.max_states))
        trans_log = np.log(self.transition_params + 1e-10)
        
        for t in range(n_samples - 1):
            for i in range(self.max_states):
                for j in range(self.max_states):
                    log_xi[t, i, j] = log_alpha[t, i] + trans_log[i, j] + \
                                      log_emission[t+1, j] + log_beta[t+1, j]
            
            log_xi[t] = log_xi[t] - logsumexp(log_xi[t])
        
        return np.exp(log_xi)
    
    def _update_params(self, data: np.ndarray, gamma: np.ndarray, xi: np.ndarray):
        expected_trans = np.sum(xi, axis=0)
        
        for i in range(self.max_states):
            self.transition_params[i] = (expected_trans[i] + self.alpha / self.max_states)
            self.transition_params[i] /= self.transition_params[i].sum()
        
        for s in range(self.max_states):
            weighted_sum = np.sum(gamma[:, s] * data)
            weight_sum = np.sum(gamma[:, s])
            
            if weight_sum > 1e-6:
                self.emission_means[s] = weighted_sum / weight_sum
                self.emission_vars[s] = np.sum(gamma[:, s] * (data - self.emission_means[s]) ** 2) / weight_sum + 1e-6
        
        self.start_probs = gamma[0] + 1e-10
        self.start_probs /= self.start_probs.sum()
        
        self.state_weights = np.mean(gamma, axis=0)
        self._prune_states()
    
    def _prune_states(self, threshold: float = 0.01):
        active_states = self.state_weights > threshold
        n_active = np.sum(active_states)
        
        if n_active < self.max_states and n_active >= 2:
            self.effective_states = n_active
            
            active_idx = np.where(active_states)[0]
            
            self.emission_means = self.emission_means[active_idx]
            self.emission_vars = self.emission_vars[active_idx]
            self.transition_params = self.transition_params[active_idx][:, active_idx]
            self.transition_params = self.transition_params / self.transition_params.sum(axis=1, keepdims=True)
            self.start_probs = self.start_probs[active_idx]
            self.start_probs = self.start_probs / self.start_probs.sum()
            self.state_weights = self.state_weights[active_idx]
            
            self.n_states = n_active
            self.max_states = n_active
    
    def fit(self, data: np.ndarray, n_iter: int = 50, tol: float = 1e-4) -> 'DirichletProcessHMM':
        data = data.flatten()
        self._init_params(data)
        
        prev_ll = -np.inf
        
        for iteration in range(n_iter):
            log_emission = self._emission_logprob(data)
            log_alpha, log_likelihood = self._forward(log_emission)
            log_beta = self._backward(log_emission)
            
            gamma = self._compute_state_probs(log_alpha, log_beta)
            xi = self._compute_transition_probs(log_alpha, log_beta, log_emission)
            
            self._update_params(data, gamma, xi)
            
            if iteration > 0 and abs(log_likelihood - prev_ll) < tol:
                break
            
            prev_ll = log_likelihood
        
        sorted_idx = np.argsort(self.emission_means)
        self.emission_means = self.emission_means[sorted_idx]
        self.emission_vars = self.emission_vars[sorted_idx]
        self.transition_params = self.transition_params[sorted_idx][:, sorted_idx]
        self.transition_params = self.transition_params / self.transition_params.sum(axis=1, keepdims=True)
        self.start_probs = self.start_probs[sorted_idx]
        self.start_probs = self.start_probs / self.start_probs.sum()
        self.state_weights = self.state_weights[sorted_idx]
        
        self.is_fitted = True
        return self
    
    def decode_states(self, data: np.ndarray) -> np.ndarray:
        if not self.is_fitted:
            raise RuntimeError("Model not fitted. Call fit() first.")
        
        data = data.flatten()
        n_samples = len(data)
        
        log_emission = self._emission_logprob(data)
        log_alpha, _ = self._forward(log_emission)
        log_beta = self._backward(log_emission)
        
        gamma = self._compute_state_probs(log_alpha, log_beta)
        
        return np.argmax(gamma, axis=1)
    
    def get_power_from_states(self, states: np.ndarray) -> np.ndarray:
        if self.emission_means is None:
            raise RuntimeError("Power levels not available.")
        return self.emission_means[states]
    
    def get_state_info(self) -> Dict:
        return {
            'effective_states': self.effective_states,
            'power_levels': self.emission_means.tolist(),
            'state_weights': self.state_weights.tolist(),
            'transition_matrix': self.transition_params.tolist()
        }
    
    def save(self, filepath: str) -> None:
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        joblib.dump({
            'alpha': self.alpha,
            'max_states': self.max_states,
            'n_states': self.n_states,
            'effective_states': self.effective_states,
            'name': self.name,
            'transition_params': self.transition_params,
            'emission_means': self.emission_means,
            'emission_vars': self.emission_vars,
            'start_probs': self.start_probs,
            'state_weights': self.state_weights,
            'is_fitted': self.is_fitted
        }, filepath)
    
    @classmethod
    def load(cls, filepath: str) -> 'DirichletProcessHMM':
        data = joblib.load(filepath)
        instance = cls(
            alpha=data['alpha'],
            max_states=data['max_states'],
            name=data['name']
        )
        instance.n_states = data['n_states']
        instance.effective_states = data['effective_states']
        instance.transition_params = data['transition_params']
        instance.emission_means = data['emission_means']
        instance.emission_vars = data['emission_vars']
        instance.start_probs = data['start_probs']
        instance.state_weights = data['state_weights']
        instance.is_fitted = data['is_fitted']
        return instance


class BayesianHMMLoadDisaggregator:
    def __init__(self, appliance_names: List[str], max_states_per_appliance: int = 10):
        self.appliance_names = appliance_names
        self.max_states_per_appliance = max_states_per_appliance
        self.models: Dict[str, DirichletProcessHMM] = {}
        self.is_fitted = False
    
    def fit(self, 
            aggregated_power: np.ndarray, 
            individual_powers: Dict[str, np.ndarray]) -> 'BayesianHMMLoadDisaggregator':
        
        for appliance in self.appliance_names:
            if appliance in individual_powers:
                print(f"Training Bayesian HMM for {appliance}...")
                model = DirichletProcessHMM(
                    alpha=1.0, 
                    max_states=self.max_states_per_appliance,
                    name=appliance
                )
                model.fit(individual_powers[appliance], n_iter=30)
                
                info = model.get_state_info()
                print(f"  {appliance}: learned {info['effective_states']} states "
                      f"(max: {self.max_states_per_appliance})")
                print(f"  Power levels: {[round(p, 1) for p in info['power_levels']]}")
                
                self.models[appliance] = model
        
        self.is_fitted = True
        return self
    
    def disaggregate(self, 
                     aggregated_power: np.ndarray,
                     method: str = 'multi_scale') -> Dict[str, np.ndarray]:
        if not self.is_fitted:
            raise RuntimeError("Models not fitted. Call fit() first.")
        
        if method == 'multi_scale':
            return self._disaggregate_multi_scale(aggregated_power)
        elif method == 'combinatorial':
            return self._disaggregate_combinatorial(aggregated_power)
        else:
            raise ValueError(f"Unknown method: {method}")
    
    def _disaggregate_combinatorial(self, aggregated_power: np.ndarray) -> Dict[str, np.ndarray]:
        n_samples = len(aggregated_power)
        
        appliance_list = list(self.models.keys())
        all_power_levels = []
        
        for appliance in appliance_list:
            levels = self.models[appliance].emission_means
            all_power_levels.append(levels)
        
        from itertools import product
        all_combos = list(product(*all_power_levels))
        combo_sums = np.array([sum(c) for c in all_combos])
        
        states_history = {app: np.zeros(n_samples, dtype=int) for app in appliance_list}
        
        for i in range(n_samples):
            target = aggregated_power[i]
            closest_idx = np.argmin(np.abs(combo_sums - target))
            closest_combo = all_combos[closest_idx]
            
            for j, appliance in enumerate(appliance_list):
                levels = self.models[appliance].emission_means
                states_history[appliance][i] = np.argmin(np.abs(levels - closest_combo[j]))
        
        results = {}
        for appliance in appliance_list:
            model = self.models[appliance]
            smoothed_states = self._smooth_states(states_history[appliance], model.n_states)
            results[appliance] = model.get_power_from_states(smoothed_states)
        
        return results
    
    def _disaggregate_multi_scale(self, aggregated_power: np.ndarray) -> Dict[str, np.ndarray]:
        scales = [5, 15, 30]
        n_samples = len(aggregated_power)
        
        scale_results = {}
        for scale in scales:
            if scale == 1:
                scale_data = aggregated_power
            else:
                scale_data = np.convolve(aggregated_power, np.ones(scale)/scale, mode='same')
            
            scale_results[scale] = self._disaggregate_combinatorial(scale_data)
        
        results = {}
        for appliance in self.models.keys():
            weighted_sum = np.zeros(n_samples)
            weights = np.zeros(n_samples)
            
            for scale in scales:
                weight = 1.0 / scale
                weighted_sum += scale_results[scale][appliance] * weight
                weights += weight
            
            results[appliance] = weighted_sum / weights
        
        return results
    
    def _smooth_states(self, states: np.ndarray, n_states: int, window: int = 5) -> np.ndarray:
        from scipy.ndimage import median_filter
        return median_filter(states, size=window)
    
    def get_model_info(self) -> Dict:
        info = {}
        for appliance, model in self.models.items():
            info[appliance] = model.get_state_info()
        return info
    
    def save_models(self, directory: str) -> None:
        os.makedirs(directory, exist_ok=True)
        for name, model in self.models.items():
            model.save(os.path.join(directory, f'{name}_bayesian_hmm.pkl'))
    
    @classmethod
    def load_models(cls, directory: str, appliance_names: List[str]) -> 'BayesianHMMLoadDisaggregator':
        disaggregator = cls(appliance_names)
        for appliance in appliance_names:
            filepath = os.path.join(directory, f'{appliance}_bayesian_hmm.pkl')
            if os.path.exists(filepath):
                disaggregator.models[appliance] = DirichletProcessHMM.load(filepath)
        disaggregator.is_fitted = True
        return disaggregator


if __name__ == '__main__':
    from data_generator import generate_aggregated_data
    
    print("Generating test data...")
    df = generate_aggregated_data(days=3, sample_interval_min=5)
    
    appliance_names = ['air_conditioner', 'refrigerator', 'washing_machine', 'lighting']
    
    individual_powers = {}
    for app in appliance_names:
        individual_powers[app] = df[f'{app}_power'].values
    
    print("\nTraining Bayesian HMM disaggregator...")
    disaggregator = BayesianHMMLoadDisaggregator(appliance_names, max_states_per_appliance=8)
    disaggregator.fit(df['total_power'].values, individual_powers)
    
    print("\nModel info:")
    model_info = disaggregator.get_model_info()
    for app, info in model_info.items():
        print(f"  {app}: {info['effective_states']} states")
    
    print("\nDisaggregating with multi-scale method...")
    results = disaggregator.disaggregate(df['total_power'].values, method='multi_scale')
    
    print("\nDisaggregation results:")
    for app, powers in results.items():
        print(f"  {app}: mean={np.mean(powers):.1f}W, max={np.max(powers):.1f}W")
