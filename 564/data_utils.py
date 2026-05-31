import numpy as np
import pandas as pd
from typing import Tuple, List, Optional
from datetime import datetime, timedelta


def generate_simulated_data(
    n_samples: int = 365,
    start_date: str = '2024-01-01',
    random_state: int = 42
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    rng = np.random.RandomState(random_state)
    
    species = ['PM2.5', 'PM10', 'NO2', 'SO2', 'O3']
    n_species = len(species)
    
    source_names = ['工业源', '交通源', '扬尘源']
    n_sources = len(source_names)
    
    true_source_profile = np.array([
        [0.35, 0.25, 0.20, 0.15, 0.05],
        [0.25, 0.15, 0.40, 0.05, 0.15],
        [0.30, 0.45, 0.10, 0.05, 0.10],
    ])
    
    true_source_profile = true_source_profile / true_source_profile.sum(axis=1, keepdims=True)
    
    dates = pd.date_range(start=start_date, periods=n_samples, freq='D')
    
    true_contribution = np.zeros((n_samples, n_sources))
    
    for i in range(n_samples):
        month = dates[i].month
        
        if 11 <= month or month <= 2:
            industrial = 80 + rng.normal(0, 20)
        elif 3 <= month <= 5 or 9 <= month <= 10:
            industrial = 55 + rng.normal(0, 15)
        else:
            industrial = 35 + rng.normal(0, 10)
        
        is_weekday = dates[i].weekday() < 5
        if is_weekday:
            traffic = 70 + rng.normal(0, 15)
        else:
            traffic = 40 + rng.normal(0, 10)
        
        if 3 <= month <= 5:
            dust = 60 + rng.normal(0, 20)
        elif 6 <= month <= 8:
            dust = 25 + rng.normal(0, 8)
        else:
            dust = 35 + rng.normal(0, 12)
        
        true_contribution[i] = [max(industrial, 5), max(traffic, 5), max(dust, 5)]
    
    X_true = true_contribution @ true_source_profile
    
    noise_level = 0.10
    noise = rng.normal(0, noise_level, X_true.shape) * X_true
    X = np.maximum(X_true + noise, 0)
    
    U = 0.1 * X + 0.05 * np.mean(X, axis=0)
    
    df_concentration = pd.DataFrame(X, columns=species, index=dates)
    df_uncertainty = pd.DataFrame(U, columns=species, index=dates)
    
    df_concentration.index.name = '日期'
    df_uncertainty.index.name = '日期'
    
    return df_concentration, df_uncertainty


def load_data_from_file(file_path: str) -> Tuple[pd.DataFrame, Optional[pd.DataFrame]]:
    if file_path.endswith('.csv'):
        df = pd.read_csv(file_path)
    elif file_path.endswith('.xlsx'):
        df = pd.read_excel(file_path)
    else:
        raise ValueError("不支持的文件格式，请上传CSV或Excel文件")
    
    if '日期' in df.columns:
        df['日期'] = pd.to_datetime(df['日期'])
        df.set_index('日期', inplace=True)
    elif df.columns[0].lower() in ['date', 'time', 'datetime']:
        df.rename(columns={df.columns[0]: '日期'}, inplace=True)
        df['日期'] = pd.to_datetime(df['日期'])
        df.set_index('日期', inplace=True)
    
    species = ['PM2.5', 'PM10', 'NO2', 'SO2', 'O3']
    existing_species = [s for s in species if s in df.columns]
    
    if len(existing_species) < 2:
        raise ValueError("数据中应至少包含PM2.5、PM10、NO2、SO2、O3中的两种污染物")
    
    df_concentration = df[existing_species].copy()
    
    uncertainty_cols = [f'{s}_U' for s in existing_species]
    existing_uncertainty = [u for u in uncertainty_cols if u in df.columns]
    
    if len(existing_uncertainty) == len(existing_species):
        df_uncertainty = df[existing_uncertainty].copy()
        df_uncertainty.columns = existing_species
    else:
        df_uncertainty = None
    
    df_concentration = df_concentration.dropna()
    
    if df_uncertainty is not None:
        df_uncertainty = df_uncertainty.loc[df_concentration.index]
    
    return df_concentration, df_uncertainty


def preprocess_data(
    df_concentration: pd.DataFrame,
    df_uncertainty: Optional[pd.DataFrame] = None,
    uncertainty_method: str = 'default'
) -> Tuple[np.ndarray, np.ndarray, List[str], pd.Index]:
    species = df_concentration.columns.tolist()
    index = df_concentration.index
    
    X = df_concentration.values.astype(float)
    
    if df_uncertainty is not None:
        U = df_uncertainty.values.astype(float)
    else:
        if uncertainty_method == 'default':
            U = 0.1 * X + 0.01 * np.mean(X, axis=0)
        elif uncertainty_method == 'relative':
            U = 0.15 * X
        elif uncertainty_method == 'absolute':
            U = np.full_like(X, 5.0)
        else:
            U = 0.1 * X + 0.01 * np.mean(X, axis=0)
    
    U = np.maximum(U, 1e-10)
    X = np.maximum(X, 0)
    
    return X, U, species, index


def calculate_source_contribution_percent(G: np.ndarray) -> np.ndarray:
    total = G.sum(axis=1, keepdims=True)
    total[total == 0] = 1
    return G / total * 100


def calculate_species_contribution(F: np.ndarray, G: np.ndarray, species_idx: int) -> np.ndarray:
    contribution = G * F[:, species_idx]
    total = contribution.sum(axis=1, keepdims=True)
    total[total == 0] = 1
    return contribution / total * 100


def identify_source_type(F: np.ndarray, species: List[str]) -> List[str]:
    source_types = []
    
    pm25_idx = species.index('PM2.5') if 'PM2.5' in species else -1
    pm10_idx = species.index('PM10') if 'PM10' in species else -1
    no2_idx = species.index('NO2') if 'NO2' in species else -1
    so2_idx = species.index('SO2') if 'SO2' in species else -1
    o3_idx = species.index('O3') if 'O3' in species else -1
    
    for i in range(F.shape[0]):
        profile = F[i]
        
        features = {}
        if pm25_idx >= 0:
            features['PM2.5'] = profile[pm25_idx]
        if pm10_idx >= 0:
            features['PM10'] = profile[pm10_idx]
        if no2_idx >= 0:
            features['NO2'] = profile[no2_idx]
        if so2_idx >= 0:
            features['SO2'] = profile[so2_idx]
        if o3_idx >= 0:
            features['O3'] = profile[o3_idx]
        
        scores = {
            '工业源': 0,
            '交通源': 0,
            '扬尘源': 0,
        }
        
        if 'SO2' in features and features['SO2'] > 0.12:
            scores['工业源'] += 3
        if 'NO2' in features and features['NO2'] > 0.3:
            scores['交通源'] += 3
        if 'PM10' in features and features['PM10'] > 0.35:
            scores['扬尘源'] += 3
            
        if 'PM2.5' in features and 0.25 <= features['PM2.5'] <= 0.4:
            scores['工业源'] += 1
        if 'PM2.5' in features and features['PM2.5'] > 0.2:
            scores['交通源'] += 1
        if 'PM2.5' in features and features['PM2.5'] > 0.2:
            scores['扬尘源'] += 1
            
        if 'O3' in features and features['O3'] > 0.1:
            scores['交通源'] += 1
            scores['工业源'] += 0.5
        
        best_source = max(scores, key=scores.get)
        if scores[best_source] == 0:
            best_source = f'源{i+1}'
        
        source_types.append(best_source)
    
    return source_types


def get_data_summary(df: pd.DataFrame) -> pd.DataFrame:
    summary = pd.DataFrame({
        '样本数': [len(df)] * len(df.columns),
        '平均值': df.mean().round(2),
        '标准差': df.std().round(2),
        '最小值': df.min().round(2),
        '中位数': df.median().round(2),
        '最大值': df.max().round(2),
        '缺失值': df.isnull().sum().values,
    }, index=df.columns)
    
    return summary
