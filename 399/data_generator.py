import numpy as np
import pandas as pd
from typing import Dict, Tuple, List
import warnings
warnings.filterwarnings('ignore')

APPLIANCE_PARAMS = {
    'air_conditioner': {
        'states': ['off', 'low', 'medium', 'high'],
        'power_levels': [0, 800, 1500, 2200],
        'transition_matrix': [
            [0.95, 0.03, 0.015, 0.005],
            [0.05, 0.85, 0.08, 0.02],
            [0.02, 0.10, 0.80, 0.08],
            [0.01, 0.05, 0.15, 0.79]
        ],
        'noise_std': 50,
        'daily_pattern': lambda h: 0.3 + 0.6 * np.exp(-((h - 14) ** 2) / 20)
    },
    'refrigerator': {
        'states': ['off', 'on'],
        'power_levels': [0, 150],
        'transition_matrix': [
            [0.7, 0.3],
            [0.4, 0.6]
        ],
        'noise_std': 10,
        'daily_pattern': lambda h: 0.5 + 0.1 * np.sin(h * np.pi / 12)
    },
    'washing_machine': {
        'states': ['off', 'washing', 'spinning'],
        'power_levels': [0, 500, 800],
        'transition_matrix': [
            [0.99, 0.008, 0.002],
            [0.1, 0.7, 0.2],
            [0.3, 0.0, 0.7]
        ],
        'noise_std': 30,
        'daily_pattern': lambda h: 0.01 + 0.05 * (1 if 8 <= h <= 20 else 0)
    },
    'lighting': {
        'states': ['off', 'dim', 'bright'],
        'power_levels': [0, 50, 150],
        'transition_matrix': [
            [0.90, 0.08, 0.02],
            [0.1, 0.70, 0.20],
            [0.05, 0.15, 0.80]
        ],
        'noise_std': 5,
        'daily_pattern': lambda h: 0.01 + 0.8 * (1 if 18 <= h <= 23 or 6 <= h <= 8 else 0.05)
    }
}


class ApplianceDataGenerator:
    def __init__(self, appliance_name: str):
        self.name = appliance_name
        params = APPLIANCE_PARAMS[appliance_name]
        self.states = params['states']
        self.power_levels = np.array(params['power_levels'])
        self.transition_matrix = np.array(params['transition_matrix'])
        self.noise_std = params['noise_std']
        self.daily_pattern = params['daily_pattern']
        self.n_states = len(self.states)
    
    def generate_series(self, n_samples: int, start_hour: int = 0, 
                        sample_interval_min: int = 1) -> Tuple[np.ndarray, np.ndarray]:
        states = np.zeros(n_samples, dtype=int)
        powers = np.zeros(n_samples)
        
        current_state = np.random.choice(self.n_states)
        states[0] = current_state
        
        for i in range(n_samples):
            hour = (start_hour + i * sample_interval_min / 60) % 24
            pattern_factor = self.daily_pattern(hour)
            
            if i > 0:
                trans_probs = self.transition_matrix[current_state].copy()
                if np.random.random() > pattern_factor:
                    trans_probs[0] += 0.3
                    trans_probs = trans_probs / trans_probs.sum()
                
                current_state = np.random.choice(self.n_states, p=trans_probs)
                states[i] = current_state
            
            base_power = self.power_levels[current_state]
            noise = np.random.normal(0, self.noise_std) if base_power > 0 else 0
            powers[i] = max(0, base_power + noise)
        
        return states, powers


def generate_aggregated_data(days: int = 7, 
                             sample_interval_min: int = 1,
                             noise_std: float = 30) -> pd.DataFrame:
    n_samples = days * 24 * 60 // sample_interval_min
    timestamps = pd.date_range(start='2024-01-01', 
                               periods=n_samples, 
                               freq=f'{sample_interval_min}min')
    
    appliance_data = {}
    total_power = np.zeros(n_samples)
    
    for appliance in APPLIANCE_PARAMS.keys():
        generator = ApplianceDataGenerator(appliance)
        states, powers = generator.generate_series(n_samples, sample_interval_min=sample_interval_min)
        appliance_data[appliance] = {
            'states': states,
            'powers': powers
        }
        total_power += powers
    
    total_power += np.random.normal(0, noise_std, n_samples)
    total_power = np.maximum(0, total_power)
    
    df = pd.DataFrame(index=timestamps)
    df['total_power'] = total_power
    
    for appliance in APPLIANCE_PARAMS.keys():
        df[f'{appliance}_power'] = appliance_data[appliance]['powers']
        df[f'{appliance}_state'] = appliance_data[appliance]['states']
    
    return df


def preprocess_data(df: pd.DataFrame, 
                    window_size: int = 60) -> Tuple[np.ndarray, np.ndarray]:
    total_power = df['total_power'].values
    
    n_windows = len(total_power) - window_size + 1
    X = np.zeros((n_windows, window_size))
    
    for i in range(n_windows):
        X[i] = total_power[i:i+window_size]
    
    X = (X - X.mean(axis=1, keepdims=True)) / (X.std(axis=1, keepdims=True) + 1e-8)
    
    appliance_columns = [col for col in df.columns if col.endswith('_power') and col != 'total_power']
    y = df[appliance_columns].values[window_size-1:]
    
    return X, y


def downsample_data(df: pd.DataFrame, 
                    target_interval_min: int = 5) -> pd.DataFrame:
    return df.resample(f'{target_interval_min}min').mean()


def split_data(df: pd.DataFrame, 
               train_ratio: float = 0.7, 
               val_ratio: float = 0.15) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    n = len(df)
    train_end = int(n * train_ratio)
    val_end = int(n * (train_ratio + val_ratio))
    
    train_df = df.iloc[:train_end]
    val_df = df.iloc[train_end:val_end]
    test_df = df.iloc[val_end:]
    
    return train_df, val_df, test_df


if __name__ == '__main__':
    print("Generating sample data...")
    df = generate_aggregated_data(days=7, sample_interval_min=1)
    print(f"Generated data shape: {df.shape}")
    print(f"Columns: {df.columns.tolist()}")
    print(f"\nSample data:")
    print(df.head())
    
    print(f"\nTotal power statistics:")
    print(df['total_power'].describe())
