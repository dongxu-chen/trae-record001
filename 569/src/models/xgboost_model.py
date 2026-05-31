import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.multioutput import MultiOutputRegressor
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
from sklearn.model_selection import cross_val_score, GridSearchCV
import joblib
import os
from typing import Dict, List, Tuple, Optional, Any
import warnings
warnings.filterwarnings('ignore')

from src.features.data_generator import SKILL_GROUPS, SKILL_GROUP_ORDER


class SingleGroupModel:
    def __init__(self, group_name: str, random_state: int = 42):
        self.group_name = group_name
        self.random_state = random_state
        self.model = None
        self.feature_names = None
        self.target_names = None
        self.is_trained = False
        
    def build_model(self, params: Optional[Dict] = None) -> MultiOutputRegressor:
        if params is None:
            params = {
                'n_estimators': 200,
                'max_depth': 6,
                'learning_rate': 0.05,
                'subsample': 0.8,
                'colsample_bytree': 0.8,
                'min_child_weight': 3,
                'reg_alpha': 0.1,
                'reg_lambda': 0.5,
                'random_state': self.random_state
            }
        
        base_model = xgb.XGBRegressor(
            objective='reg:squarederror',
            **params
        )
        
        self.model = MultiOutputRegressor(base_model)
        return self.model
    
    def train(self, X_train: np.ndarray, y_train: np.ndarray,
              feature_names: List[str], target_names: List[str],
              X_val: Optional[np.ndarray] = None, 
              y_val: Optional[np.ndarray] = None,
              verbose: bool = True) -> Dict:
        self.feature_names = feature_names
        self.target_names = target_names
        
        if self.model is None:
            self.build_model()
        
        self.model.fit(X_train, y_train)
        self.is_trained = True
        
        train_metrics = self.evaluate(X_train, y_train)
        
        if verbose:
            group_display = SKILL_GROUPS[self.group_name]['name']
            print(f"\n=== [{group_display}] 训练集评估 ===")
            for target, metrics in train_metrics.items():
                print(f"\n{target}:")
                print(f"  MSE: {metrics['mse']:.4f}")
                print(f"  MAE: {metrics['mae']:.4f}")
                print(f"  R2: {metrics['r2']:.4f}")
        
        if X_val is not None and y_val is not None:
            val_metrics = self.evaluate(X_val, y_val)
            if verbose:
                group_display = SKILL_GROUPS[self.group_name]['name']
                print(f"\n=== [{group_display}] 验证集评估 ===")
                for target, metrics in val_metrics.items():
                    print(f"\n{target}:")
                    print(f"  MSE: {metrics['mse']:.4f}")
                    print(f"  MAE: {metrics['mae']:.4f}")
                    print(f"  R2: {metrics['r2']:.4f}")
            return {'train': train_metrics, 'validation': val_metrics}
        
        return {'train': train_metrics}
    
    def evaluate(self, X: np.ndarray, y: np.ndarray) -> Dict[str, Dict[str, float]]:
        if not self.is_trained:
            raise ValueError(f"模型[{self.group_name}]未训练")
        
        y_pred = self.model.predict(X)
        
        results = {}
        for i, target in enumerate(self.target_names):
            y_true_i = y[:, i]
            y_pred_i = y_pred[:, i]
            
            results[target] = {
                'mse': mean_squared_error(y_true_i, y_pred_i),
                'mae': mean_absolute_error(y_true_i, y_pred_i),
                'r2': r2_score(y_true_i, y_pred_i),
                'rmse': np.sqrt(mean_squared_error(y_true_i, y_pred_i))
            }
        
        return results
    
    def predict(self, X: np.ndarray) -> np.ndarray:
        if not self.is_trained:
            raise ValueError(f"模型[{self.group_name}]未训练")
        
        predictions = self.model.predict(X)
        
        for i in range(predictions.shape[1]):
            if 'completion' in self.target_names[i]:
                predictions[:, i] = np.clip(predictions[:, i], 0, 1)
            elif 'attempts' in self.target_names[i]:
                predictions[:, i] = np.clip(predictions[:, i], 1, None)
        
        return predictions
    
    def predict_single(self, X: np.ndarray) -> Dict[str, float]:
        pred = self.predict(X)
        return {name: float(pred[0, i]) for i, name in enumerate(self.target_names)}
    
    def get_feature_importance(self) -> pd.DataFrame:
        if not self.is_trained:
            raise ValueError(f"模型[{self.group_name}]未训练")
        
        importances = []
        
        for i, target in enumerate(self.target_names):
            estimator = self.model.estimators_[i]
            feat_imp = estimator.feature_importances_
            
            for j, feat in enumerate(self.feature_names):
                importances.append({
                    'group': self.group_name,
                    'target': target,
                    'feature': feat,
                    'importance': feat_imp[j]
                })
        
        return pd.DataFrame(importances)
    
    def get_estimators(self) -> List:
        if not self.is_trained:
            raise ValueError(f"模型[{self.group_name}]未训练")
        return self.model.estimators_
    
    def cross_validate(self, X: np.ndarray, y: np.ndarray, 
                       cv: int = 5) -> Dict[str, Dict[str, float]]:
        if self.model is None:
            self.build_model()
        
        results = {}
        for i, target in enumerate(self.target_names):
            y_i = y[:, i]
            
            mse_scores = -cross_val_score(
                self.model.estimators_[i], X, y_i,
                cv=cv, scoring='neg_mean_squared_error'
            )
            mae_scores = -cross_val_score(
                self.model.estimators_[i], X, y_i,
                cv=cv, scoring='neg_mean_absolute_error'
            )
            r2_scores = cross_val_score(
                self.model.estimators_[i], X, y_i,
                cv=cv, scoring='r2'
            )
            
            results[target] = {
                'mse_mean': mse_scores.mean(),
                'mse_std': mse_scores.std(),
                'mae_mean': mae_scores.mean(),
                'mae_std': mae_scores.std(),
                'r2_mean': r2_scores.mean(),
                'r2_std': r2_scores.std()
            }
        
        return results
    
    def hyperparameter_tuning(self, X_train: np.ndarray, y_train: np.ndarray,
                              param_grid: Optional[Dict] = None,
                              cv: int = 3) -> Dict:
        if param_grid is None:
            param_grid = {
                'estimator__n_estimators': [100, 200, 300],
                'estimator__max_depth': [4, 6, 8],
                'estimator__learning_rate': [0.01, 0.05, 0.1],
                'estimator__subsample': [0.7, 0.8, 0.9],
                'estimator__min_child_weight': [1, 3, 5]
            }
        
        base_model = xgb.XGBRegressor(
            objective='reg:squarederror',
            random_state=self.random_state
        )
        multi_model = MultiOutputRegressor(base_model)
        
        grid_search = GridSearchCV(
            multi_model, param_grid, 
            cv=cv, scoring='neg_mean_squared_error',
            verbose=1, n_jobs=-1
        )
        
        grid_search.fit(X_train, y_train)
        
        self.model = grid_search.best_estimator_
        self.is_trained = True
        
        return {
            'best_params': grid_search.best_params_,
            'best_score': grid_search.best_score_,
            'cv_results': pd.DataFrame(grid_search.cv_results_)
        }


class GroupedDifficultyModel:
    def __init__(self, random_state: int = 42):
        self.random_state = random_state
        self.models: Dict[str, SingleGroupModel] = {}
        self.feature_names = None
        self.is_trained = False
        
        for group in SKILL_GROUP_ORDER:
            self.models[group] = SingleGroupModel(group, random_state)
    
    def train_all(self, data_by_group: Dict[str, Dict[str, Any]],
                  verbose: bool = True) -> Dict[str, Dict]:
        results = {}
        
        for group in SKILL_GROUP_ORDER:
            if group not in data_by_group:
                continue
                
            data = data_by_group[group]
            model = self.models[group]
            
            results[group] = model.train(
                data['X_train'], data['y_train'],
                data['feature_names'], data['target_names'],
                X_val=data['X_test'], y_val=data['y_test'],
                verbose=verbose
            )
            
            if self.feature_names is None:
                self.feature_names = data['feature_names']
        
        self.is_trained = True
        return results
    
    def predict_all_groups(self, X: np.ndarray) -> Dict[str, np.ndarray]:
        if not self.is_trained:
            raise ValueError("模型未训练")
        
        predictions = {}
        for group in SKILL_GROUP_ORDER:
            predictions[group] = self.models[group].predict(X)
        return predictions
    
    def predict_single_all_groups(self, X: np.ndarray) -> Dict[str, Dict[str, float]]:
        predictions = {}
        for group in SKILL_GROUP_ORDER:
            predictions[group] = self.models[group].predict_single(X)
        return predictions
    
    def predict_group(self, X: np.ndarray, group: str) -> np.ndarray:
        if group not in self.models:
            raise ValueError(f"未知玩家分群: {group}")
        return self.models[group].predict(X)
    
    def predict_single_group(self, X: np.ndarray, group: str) -> Dict[str, float]:
        if group not in self.models:
            raise ValueError(f"未知玩家分群: {group}")
        return self.models[group].predict_single(X)
    
    def evaluate_all(self, data_by_group: Dict[str, Dict[str, Any]]) -> Dict[str, Dict]:
        results = {}
        for group, data in data_by_group.items():
            results[group] = self.models[group].evaluate(data['X_test'], data['y_test'])
        return results
    
    def get_all_feature_importance(self) -> pd.DataFrame:
        dfs = []
        for group in SKILL_GROUP_ORDER:
            dfs.append(self.models[group].get_feature_importance())
        return pd.concat(dfs, ignore_index=True)
    
    def compare_feature_importance(self, top_n: int = 10) -> pd.DataFrame:
        df_imp = self.get_all_feature_importance()
        summary = []
        
        for group in SKILL_GROUP_ORDER:
            for target in self.models[group].target_names:
                df_target = df_imp[
                    (df_imp['group'] == group) & 
                    (df_imp['target'] == target)
                ].sort_values('importance', ascending=False).head(top_n)
                
                for _, row in df_target.iterrows():
                    summary.append({
                        'group': group,
                        'group_name': SKILL_GROUPS[group]['name'],
                        'target': target,
                        'feature': row['feature'],
                        'importance': row['importance'],
                        'rank': _ + 1
                    })
        
        return pd.DataFrame(summary)
    
    def save(self, model_dir: str = "models") -> None:
        os.makedirs(model_dir, exist_ok=True)
        
        for group in SKILL_GROUP_ORDER:
            model_path = os.path.join(model_dir, f'model_{group}.pkl')
            metadata_path = os.path.join(model_dir, f'metadata_{group}.pkl')
            
            model = self.models[group]
            joblib.dump(model.model, model_path)
            joblib.dump({
                'feature_names': model.feature_names,
                'target_names': model.target_names,
                'group': group,
                'random_state': model.random_state,
                'is_trained': model.is_trained
            }, metadata_path)
        
        global_meta = {
            'feature_names': self.feature_names,
            'random_state': self.random_state,
            'is_trained': self.is_trained
        }
        joblib.dump(global_meta, os.path.join(model_dir, 'global_metadata.pkl'))
        
        print(f"分群模型已保存到 {model_dir}/")
    
    @classmethod
    def load(cls, model_dir: str = "models") -> 'GroupedDifficultyModel':
        if not os.path.exists(os.path.join(model_dir, 'global_metadata.pkl')):
            raise FileNotFoundError(f"模型文件不存在于 {model_dir}/")
        
        global_meta = joblib.load(os.path.join(model_dir, 'global_metadata.pkl'))
        
        instance = cls(random_state=global_meta['random_state'])
        instance.feature_names = global_meta['feature_names']
        instance.is_trained = global_meta['is_trained']
        
        for group in SKILL_GROUP_ORDER:
            model_path = os.path.join(model_dir, f'model_{group}.pkl')
            metadata_path = os.path.join(model_dir, f'metadata_{group}.pkl')
            
            if not os.path.exists(model_path) or not os.path.exists(metadata_path):
                continue
            
            metadata = joblib.load(metadata_path)
            model = SingleGroupModel(group, metadata['random_state'])
            model.model = joblib.load(model_path)
            model.feature_names = metadata['feature_names']
            model.target_names = metadata['target_names']
            model.is_trained = metadata['is_trained']
            
            instance.models[group] = model
        
        return instance


def prepare_grouped_training_data(df_levels: pd.DataFrame,
                                 feature_columns: List[str],
                                 use_actual: bool = True,
                                 test_size: float = 0.2,
                                 random_state: int = 42) -> Dict[str, Dict[str, Any]]:
    from src.features.preprocessing import FeatureEngineer, prepare_training_data
    
    target_by_group = {}
    for group in SKILL_GROUP_ORDER:
        if use_actual:
            target_by_group[group] = [
                f'actual_{group}_completion_rate',
                f'actual_{group}_avg_attempts'
            ]
        else:
            target_by_group[group] = [
                f'{group}_completion_rate',
                f'{group}_avg_attempts'
            ]
    
    data_by_group = {}
    
    for group in SKILL_GROUP_ORDER:
        target_cols = target_by_group[group]
        
        df_clean = df_levels.dropna(subset=target_cols).copy()
        
        engineer = FeatureEngineer()
        df_features, feature_names = engineer.fit_transform(df_clean, feature_columns)
        
        X = df_features[feature_names].values
        y = df_clean[target_cols].values
        
        from sklearn.model_selection import train_test_split
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=test_size, random_state=random_state
        )
        
        data_by_group[group] = {
            'X_train': X_train,
            'X_test': X_test,
            'y_train': y_train,
            'y_test': y_test,
            'feature_names': feature_names,
            'target_names': target_cols,
            'engineer': engineer,
            'df_clean': df_clean
        }
    
    return data_by_group


def train_grouped_pipeline(df_levels: pd.DataFrame,
                          feature_columns: List[str],
                          use_actual: bool = True,
                          model_dir: str = "models") -> Tuple[GroupedDifficultyModel, Dict[str, Dict[str, Any]]]:
    print("=== 分群模型训练流程 ===")
    
    print("\n数据预处理...")
    data_by_group = prepare_grouped_training_data(
        df_levels, feature_columns, use_actual
    )
    
    for group in SKILL_GROUP_ORDER:
        data = data_by_group[group]
        group_name = SKILL_GROUPS[group]['name']
        print(f"\n  {group_name}: {len(data['feature_names'])} 特征, "
              f"训练集 {len(data['X_train'])} 样本, "
              f"测试集 {len(data['X_test'])} 样本")
    
    print("\n训练分群模型...")
    model = GroupedDifficultyModel()
    results = model.train_all(data_by_group, verbose=True)
    
    print("\n=== 交叉验证 ===")
    for group in SKILL_GROUP_ORDER:
        data = data_by_group[group]
        group_name = SKILL_GROUPS[group]['name']
        single_model = model.models[group]
        
        X_all = np.vstack([data['X_train'], data['X_test']])
        y_all = np.vstack([data['y_train'], data['y_test']])
        
        cv_results = single_model.cross_validate(X_all, y_all, cv=5)
        
        for target, metrics in cv_results.items():
            print(f"\n  [{group_name}] {target}:")
            print(f"    R2: {metrics['r2_mean']:.4f} ± {metrics['r2_std']:.4f}")
    
    print("\n保存模型...")
    model.save(model_dir)
    
    first_group = SKILL_GROUP_ORDER[0]
    data_by_group[first_group]['engineer'].save(
        os.path.join(model_dir, 'feature_engineer.pkl')
    )
    
    return model, data_by_group


def train_overall_model(df_levels: pd.DataFrame,
                       use_actual: bool = True,
                       do_tuning: bool = False,
                       model_dir: str = "models"):
    from src.features.preprocessing import prepare_training_data
    
    target_columns = ['actual_completion_rate', 'actual_avg_attempts'] if use_actual \
        else ['completion_rate', 'avg_attempts']
    
    feature_columns = [
        'obstacle_density', 'time_limit', 'enemy_count',
        'platform_gap', 'moving_obstacle_ratio',
        'powerup_count', 'checkpoint_count', 'level_length'
    ]
    
    print("=== 整体模型训练 ===")
    data = prepare_training_data(df_levels, feature_columns, target_columns, use_actual)
    
    model = SingleGroupModel('overall')
    model.build_model()
    
    if do_tuning:
        print("\n超参数调优...")
        model.hyperparameter_tuning(data['X_train'], data['y_train'], cv=3)
    else:
        model.train(
            data['X_train'], data['y_train'],
            data['feature_names'], data['target_names'],
            X_val=data['X_test'], y_val=data['y_test']
        )
    
    return model, data


if __name__ == "__main__":
    import sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    
    from src.features.data_generator import generate_full_dataset
    from src.features.preprocessing import FEATURE_COLUMNS
    
    print("生成测试数据...")
    df_levels, df_players = generate_full_dataset(n_levels=100, n_players=300)
    
    print("\n训练分群模型...")
    model, data_by_group = train_grouped_pipeline(
        df_levels, FEATURE_COLUMNS, use_actual=True
    )
    
    print("\n=== 分群模型预测测试 ===")
    sample_level = df_levels.iloc[0:1]
    from src.features.preprocessing import prepare_single_prediction
    
    engineer = data_by_group['intermediate']['engineer']
    sample_params = sample_level[FEATURE_COLUMNS].iloc[0].to_dict()
    X = prepare_single_prediction(sample_params, engineer)
    
    print("\n各分群预测结果:")
    for group in SKILL_GROUP_ORDER:
        group_name = SKILL_GROUPS[group]['name']
        pred = model.predict_single_group(X, group)
        print(f"\n  {group_name}:")
        for k, v in pred.items():
            clean_k = k.replace(f'actual_{group}_', '').replace(f'{group}_', '')
            if 'completion' in clean_k:
                print(f"    {clean_k}: {v:.1%}")
            else:
                print(f"    {clean_k}: {v:.2f}")
    
    print("\n=== 特征重要性对比 ===")
    comparison = model.compare_feature_importance(top_n=5)
    for group in SKILL_GROUP_ORDER:
        group_name = SKILL_GROUPS[group]['name']
        print(f"\n{group_name} 最重要特征:")
        group_data = comparison[comparison['group'] == group].head(5)
        for _, row in group_data.iterrows():
            print(f"  {row['rank']}. {row['feature']}: {row['importance']:.4f}")
