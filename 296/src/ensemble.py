import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
from scipy.optimize import minimize
import warnings
warnings.filterwarnings('ignore')

from .models import BaseForecaster


class EnsembleForecaster:
    def __init__(self, models: Dict[str, BaseForecaster] = None):
        self.models = models or {}
        self.weights = {}
        self.ensemble_name = 'Ensemble'
        self.fitted = False

    def add_model(self, name: str, model: BaseForecaster):
        self.models[name] = model

    def calculate_weights(self, y_true: pd.Series, predictions: Dict[str, np.ndarray],
                         method: str = 'rank') -> Dict[str, float]:
        model_names = list(predictions.keys())
        n_models = len(model_names)
        
        if n_models == 0:
            return {}
        
        if method == 'equal':
            return {name: 1.0 / n_models for name in model_names}
        
        elif method == 'rank':
            errors = []
            for name in model_names:
                pred = predictions[name][:len(y_true)]
                error = np.mean((y_true.values - pred) ** 2)
                errors.append((name, error))
            
            errors.sort(key=lambda x: x[1])
            ranks = np.arange(n_models, 0, -1)
            total_rank = ranks.sum()
            
            weights = {}
            for i, (name, _) in enumerate(errors):
                weights[name] = ranks[i] / total_rank
            return weights
        
        elif method == 'inverse_score':
            scores = []
            for name in model_names:
                pred = predictions[name][:len(y_true)]
                rmse = np.sqrt(np.mean((y_true.values - pred) ** 2))
                scores.append((name, 1.0 / (rmse + 1e-8)))
            
            total_score = sum(s for _, s in scores)
            return {name: s / total_score for name, s in scores}
        
        elif method == 'optimized':
            def objective(weights):
                weighted_pred = np.zeros_like(y_true.values, dtype=float)
                for i, name in enumerate(model_names):
                    pred = predictions[name][:len(y_true)]
                    weighted_pred += weights[i] * pred
                return np.mean((y_true.values - weighted_pred) ** 2)
            
            constraints = ({'type': 'eq', 'fun': lambda w: np.sum(w) - 1})
            bounds = [(0, 1)] * n_models
            initial_weights = np.array([1.0 / n_models] * n_models)
            
            result = minimize(objective, initial_weights, method='SLSQP', 
                            bounds=bounds, constraints=constraints)
            
            weights = {}
            for i, name in enumerate(model_names):
                weights[name] = max(0, result.x[i])
            
            total = sum(weights.values())
            return {name: w / total for name, w in weights.items()}
        
        else:
            return {name: 1.0 / n_models for name in model_names}

    def fit(self, y_val: pd.Series, X_val: pd.DataFrame = None, 
            horizon: int = 7, weight_method: str = 'rank'):
        predictions = {}
        for name, model in self.models.items():
            try:
                pred = model.predict(horizon, X_val)
                predictions[name] = pred
            except Exception as e:
                print(f"模型 {name} 预测失败: {e}")
        
        if len(predictions) == 0:
            raise ValueError("没有可用的模型进行集成")
        
        y_true_aligned = y_val.iloc[:horizon]
        self.weights = self.calculate_weights(y_true_aligned, predictions, weight_method)
        self.fitted = True
        return self

    def predict(self, horizon: int, X_test: pd.DataFrame = None) -> np.ndarray:
        if not self.models:
            raise ValueError("没有已添加的模型")
        
        if not self.weights:
            n_models = len(self.models)
            self.weights = {name: 1.0 / n_models for name in self.models.keys()}
        
        predictions = []
        model_weights = []
        
        for name, model in self.models.items():
            try:
                pred = model.predict(horizon, X_test)
                predictions.append(pred)
                model_weights.append(self.weights.get(name, 0))
            except Exception as e:
                print(f"模型 {name} 预测失败: {e}")
        
        if len(predictions) == 0:
            raise ValueError("没有模型成功预测")
        
        total_weight = sum(model_weights)
        if total_weight > 0:
            normalized_weights = [w / total_weight for w in model_weights]
        else:
            normalized_weights = [1.0 / len(predictions) for _ in predictions]
        
        min_len = min(len(p) for p in predictions)
        predictions_aligned = [p[:min_len] for p in predictions]
        
        ensemble_pred = np.zeros(min_len)
        for pred, weight in zip(predictions_aligned, normalized_weights):
            ensemble_pred += weight * pred
        
        return ensemble_pred

    def get_model_predictions(self, horizon: int, X_test: pd.DataFrame = None) -> pd.DataFrame:
        all_preds = {}
        
        for name, model in self.models.items():
            try:
                pred = model.predict(horizon, X_test)
                all_preds[name] = pred
            except Exception as e:
                print(f"模型 {name} 预测失败: {e}")
        
        return pd.DataFrame(all_preds)

    def get_weights_summary(self) -> pd.DataFrame:
        if not self.weights:
            return pd.DataFrame()
        
        summary = pd.DataFrame([
            {'model': name.upper(), 'weight': weight}
            for name, weight in self.weights.items()
        ]).sort_values('weight', ascending=False)
        summary['weight_pct'] = summary['weight'] * 100
        return summary
