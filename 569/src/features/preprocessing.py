import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler, MinMaxScaler
from sklearn.model_selection import train_test_split
from typing import Tuple, List, Dict, Optional
import joblib
import os


FEATURE_COLUMNS = [
    'obstacle_density',
    'time_limit',
    'enemy_count',
    'platform_gap',
    'moving_obstacle_ratio',
    'powerup_count',
    'checkpoint_count',
    'level_length'
]

TARGET_COLUMNS = [
    'actual_completion_rate',
    'actual_avg_attempts'
]

TARGET_COLUMNS_SIMULATED = [
    'completion_rate',
    'avg_attempts'
]


class FeatureEngineer:
    def __init__(self):
        self.scaler = StandardScaler()
        self.fitted = False
    
    def create_interaction_features(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        
        df['obstacle_enemy_interaction'] = df['obstacle_density'] * df['enemy_count']
        df['time_obstacle_interaction'] = (180 - df['time_limit']) / 180 * df['obstacle_density']
        df['moving_density_interaction'] = df['moving_obstacle_ratio'] * df['obstacle_density']
        df['gap_length_interaction'] = df['platform_gap'] * df['level_length'] / 100
        df['powerup_checkpoint_bonus'] = df['powerup_count'] + df['checkpoint_count'] * 1.5
        df['enemy_moving_interaction'] = df['enemy_count'] * df['moving_obstacle_ratio']
        
        df['time_pressure_index'] = (180 - df['time_limit']) / 180
        df['total_threat'] = df['obstacle_density'] * df['level_length'] + df['enemy_count'] * 2
        
        df['difficulty_components'] = (
            df['obstacle_density'] * 0.25 +
            df['time_pressure_index'] * 0.2 +
            df['enemy_count'] / 15 * 0.2 +
            df['moving_obstacle_ratio'] * 0.15 +
            df['platform_gap'] / 3 * 0.1 +
            df['level_length'] / 300 * 0.1
        )
        
        return df
    
    def create_nonlinear_features(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        
        df['obstacle_density_sqrt'] = np.sqrt(df['obstacle_density'])
        df['enemy_count_sqrt'] = np.sqrt(df['enemy_count'])
        df['time_limit_inv'] = 1 / (df['time_limit'] / 30)
        df['platform_gap_sq'] = df['platform_gap'] ** 2
        
        return df
    
    def create_binned_features(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        
        df['density_bin'] = pd.cut(
            df['obstacle_density'],
            bins=[0, 0.15, 0.3, 0.45, 1.0],
            labels=['low', 'medium', 'high', 'extreme']
        )
        
        df['time_bin'] = pd.cut(
            df['time_limit'],
            bins=[0, 60, 100, 140, 180],
            labels=['very_short', 'short', 'medium', 'long']
        )
        
        df['enemy_bin'] = pd.cut(
            df['enemy_count'],
            bins=[-1, 3, 7, 11, 15],
            labels=['none', 'few', 'some', 'many']
        )
        
        df = pd.get_dummies(df, columns=['density_bin', 'time_bin', 'enemy_bin'], 
                           drop_first=True)
        
        return df
    
    def fit_transform(self, df: pd.DataFrame, feature_columns: List[str]) -> Tuple[pd.DataFrame, List[str]]:
        df = df.copy()
        
        df = self.create_interaction_features(df)
        df = self.create_nonlinear_features(df)
        df = self.create_binned_features(df)
        
        all_features = feature_columns + [
            'obstacle_enemy_interaction',
            'time_obstacle_interaction',
            'moving_density_interaction',
            'gap_length_interaction',
            'powerup_checkpoint_bonus',
            'enemy_moving_interaction',
            'time_pressure_index',
            'total_threat',
            'difficulty_components',
            'obstacle_density_sqrt',
            'enemy_count_sqrt',
            'time_limit_inv',
            'platform_gap_sq'
        ]
        
        bin_cols = [c for c in df.columns if c.startswith(('density_bin_', 'time_bin_', 'enemy_bin_'))]
        all_features += bin_cols
        
        numeric_features = [f for f in all_features if f not in bin_cols]
        df[numeric_features] = self.scaler.fit_transform(df[numeric_features])
        
        self.fitted = True
        self.feature_names = all_features
        
        return df, all_features
    
    def transform(self, df: pd.DataFrame, feature_columns: List[str]) -> Tuple[pd.DataFrame, List[str]]:
        if not self.fitted:
            raise ValueError("FeatureEngineer未拟合，请先调用fit_transform")
        
        df = df.copy()
        
        df = self.create_interaction_features(df)
        df = self.create_nonlinear_features(df)
        df = self.create_binned_features(df)
        
        all_features = self.feature_names
        
        numeric_features = [f for f in all_features if not f.startswith(('density_bin_', 'time_bin_', 'enemy_bin_'))]
        df[numeric_features] = self.scaler.transform(df[numeric_features])
        
        bin_cols = [c for c in df.columns if c.startswith(('density_bin_', 'time_bin_', 'enemy_bin_'))]
        for col in [c for c in all_features if c.startswith(('density_bin_', 'time_bin_', 'enemy_bin_'))]:
            if col not in df.columns:
                df[col] = 0
        
        return df, all_features
    
    def save(self, path: str) -> None:
        joblib.dump({
            'scaler': self.scaler,
            'fitted': self.fitted,
            'feature_names': self.feature_names
        }, path)
    
    @classmethod
    def load(cls, path: str) -> 'FeatureEngineer':
        data = joblib.load(path)
        engineer = cls()
        engineer.scaler = data['scaler']
        engineer.fitted = data['fitted']
        engineer.feature_names = data['feature_names']
        return engineer


def prepare_training_data(df: pd.DataFrame, 
                          feature_columns: List[str] = FEATURE_COLUMNS,
                          target_columns: List[str] = None,
                          use_actual: bool = True,
                          test_size: float = 0.2,
                          random_state: int = 42) -> Dict:
    if target_columns is None:
        target_columns = TARGET_COLUMNS if use_actual else TARGET_COLUMNS_SIMULATED
    
    df_clean = df.dropna(subset=target_columns).copy()
    
    engineer = FeatureEngineer()
    df_features, feature_names = engineer.fit_transform(df_clean, feature_columns)
    
    X = df_features[feature_names].values
    y = df_clean[target_columns].values
    
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=test_size, random_state=random_state,
        stratify=None
    )
    
    train_indices = df_clean.index[:len(X_train)]
    test_indices = df_clean.index[len(X_train):]
    
    return {
        'X_train': X_train,
        'X_test': X_test,
        'y_train': y_train,
        'y_test': y_test,
        'feature_names': feature_names,
        'target_names': target_columns,
        'engineer': engineer,
        'train_indices': train_indices,
        'test_indices': test_indices,
        'df_clean': df_clean
    }


def prepare_single_prediction(level_params: Dict, 
                              engineer: FeatureEngineer,
                              feature_columns: List[str] = FEATURE_COLUMNS) -> np.ndarray:
    df = pd.DataFrame([level_params])
    df_features, feature_names = engineer.transform(df, feature_columns)
    return df_features[feature_names].values


def get_feature_importance_from_correlation(df: pd.DataFrame, 
                                            feature_columns: List[str],
                                            target_columns: List[str]) -> pd.DataFrame:
    corr_data = []
    
    for target in target_columns:
        for feature in feature_columns:
            corr = df[feature].corr(df[target])
            corr_data.append({
                'target': target,
                'feature': feature,
                'correlation': corr,
                'abs_correlation': abs(corr)
            })
    
    return pd.DataFrame(corr_data).sort_values('abs_correlation', ascending=False)


if __name__ == "__main__":
    from data_generator import generate_full_dataset
    
    print("生成数据...")
    df_levels, df_players = generate_full_dataset(n_levels=200, n_players=500)
    
    print("\n预处理数据...")
    data = prepare_training_data(df_levels, use_actual=True)
    
    print(f"\n训练集大小: {data['X_train'].shape}")
    print(f"测试集大小: {data['X_test'].shape}")
    print(f"特征数量: {len(data['feature_names'])}")
    print(f"目标变量: {data['target_names']}")
    
    print("\n特征相关性分析:")
    corr_df = get_feature_importance_from_correlation(
        df_levels, FEATURE_COLUMNS, TARGET_COLUMNS
    )
    print(corr_df.head(10))
