import optuna
import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
import warnings
warnings.filterwarnings('ignore')

from .models import create_model, BaseForecaster
from .ensemble import EnsembleForecaster
from .model_interpretation import ModelInterpreter


class TimeSeriesAutoML:
    def __init__(self,
                 model_types: List[str] = None,
                 n_trials: int = 10,
                 metric: str = 'rmse',
                 direction: str = 'minimize',
                 cv_folds: int = 3,
                 two_stage_optimization: bool = True,
                 coarse_trials_ratio: float = 0.4):
        self.model_types = model_types or ['arima', 'prophet', 'xgboost', 'lstm']
        self.n_trials = n_trials
        self.metric = metric
        self.direction = direction
        self.cv_folds = cv_folds
        self.two_stage_optimization = two_stage_optimization
        self.coarse_trials_ratio = coarse_trials_ratio
        
        self.best_models: Dict[str, Tuple[BaseForecaster, Dict, float]] = {}
        self.best_model: BaseForecaster = None
        self.best_model_name: str = None
        self.best_params: Dict = None
        self.best_score: float = None
        self.study_results: Dict = {}
        
        self.ensemble: EnsembleForecaster = None
        self.ensemble_predictions: np.ndarray = None
        self.interpreter: ModelInterpreter = None

    def _get_param_space_coarse(self, model_type: str, trial: optuna.Trial) -> Dict:
        params = {}
        
        if model_type == 'arima':
            params['p'] = trial.suggest_int('p', 0, 5, step=1)
            params['d'] = trial.suggest_int('d', 0, 2)
            params['q'] = trial.suggest_int('q', 0, 5, step=1)
            params['P'] = trial.suggest_int('P', 0, 2)
            params['D'] = trial.suggest_int('D', 0, 1)
            params['Q'] = trial.suggest_int('Q', 0, 2)
            params['s'] = trial.suggest_categorical('s', [0, 7, 12])
            
        elif model_type == 'prophet':
            params['yearly_seasonality'] = trial.suggest_categorical('yearly_seasonality', [True, False])
            params['weekly_seasonality'] = trial.suggest_categorical('weekly_seasonality', [True, False])
            params['daily_seasonality'] = trial.suggest_categorical('daily_seasonality', [True, False])
            params['changepoint_prior_scale'] = trial.suggest_float('changepoint_prior_scale', 0.01, 0.3, log=True)
            
        elif model_type == 'xgboost':
            params['n_estimators'] = trial.suggest_int('n_estimators', 50, 300, step=50)
            params['max_depth'] = trial.suggest_int('max_depth', 3, 8, step=2)
            params['learning_rate'] = trial.suggest_categorical('learning_rate', [0.01, 0.05, 0.1, 0.2])
            params['subsample'] = trial.suggest_categorical('subsample', [0.7, 0.8, 0.9, 1.0])
            params['colsample_bytree'] = trial.suggest_categorical('colsample_bytree', [0.7, 0.8, 0.9, 1.0])
            
        elif model_type == 'lstm':
            params['units'] = trial.suggest_categorical('units', [32, 64, 128])
            params['dropout'] = trial.suggest_categorical('dropout', [0.1, 0.2, 0.3])
            params['epochs'] = trial.suggest_categorical('epochs', [30, 50, 70])
            params['batch_size'] = trial.suggest_categorical('batch_size', [16, 32, 64])
            params['sequence_length'] = trial.suggest_categorical('sequence_length', [7, 14, 21])
            
        return params

    def _get_param_space_fine(self, model_type: str, trial: optuna.Trial, 
                              best_coarse_params: Dict) -> Dict:
        params = {}
        
        if model_type == 'arima':
            base_p = best_coarse_params.get('p', 1)
            base_d = best_coarse_params.get('d', 1)
            base_q = best_coarse_params.get('q', 1)
            base_P = best_coarse_params.get('P', 0)
            base_D = best_coarse_params.get('D', 0)
            base_Q = best_coarse_params.get('Q', 0)
            
            params['p'] = trial.suggest_int('p', max(0, base_p - 1), min(5, base_p + 1))
            params['d'] = trial.suggest_int('d', max(0, base_d), min(2, base_d))
            params['q'] = trial.suggest_int('q', max(0, base_q - 1), min(5, base_q + 1))
            params['P'] = trial.suggest_int('P', max(0, base_P - 1), min(2, base_P + 1))
            params['D'] = trial.suggest_int('D', max(0, base_D), min(1, base_D))
            params['Q'] = trial.suggest_int('Q', max(0, base_Q - 1), min(2, base_Q + 1))
            params['s'] = trial.suggest_categorical('s', [0, 7, 12])
            
        elif model_type == 'prophet':
            base_cps = best_coarse_params.get('changepoint_prior_scale', 0.05)
            
            params['yearly_seasonality'] = best_coarse_params.get('yearly_seasonality', True)
            params['weekly_seasonality'] = best_coarse_params.get('weekly_seasonality', True)
            params['daily_seasonality'] = best_coarse_params.get('daily_seasonality', True)
            params['changepoint_prior_scale'] = trial.suggest_float(
                'changepoint_prior_scale', 
                max(0.001, base_cps * 0.5), 
                min(0.5, base_cps * 2), 
                log=True
            )
            
        elif model_type == 'xgboost':
            base_n = best_coarse_params.get('n_estimators', 100)
            base_md = best_coarse_params.get('max_depth', 3)
            base_lr = best_coarse_params.get('learning_rate', 0.1)
            base_ss = best_coarse_params.get('subsample', 0.8)
            base_cb = best_coarse_params.get('colsample_bytree', 0.8)
            
            params['n_estimators'] = trial.suggest_int('n_estimators', max(50, base_n - 50), min(500, base_n + 50))
            params['max_depth'] = trial.suggest_int('max_depth', max(2, base_md - 1), min(10, base_md + 1))
            params['learning_rate'] = trial.suggest_float('learning_rate', max(0.001, base_lr * 0.5), min(0.3, base_lr * 1.5), log=True)
            params['subsample'] = trial.suggest_float('subsample', max(0.6, base_ss - 0.1), min(1.0, base_ss + 0.1))
            params['colsample_bytree'] = trial.suggest_float('colsample_bytree', max(0.6, base_cb - 0.1), min(1.0, base_cb + 0.1))
            
        elif model_type == 'lstm':
            base_u = best_coarse_params.get('units', 64)
            base_d = best_coarse_params.get('dropout', 0.2)
            base_e = best_coarse_params.get('epochs', 50)
            base_sl = best_coarse_params.get('sequence_length', 10)
            
            params['units'] = trial.suggest_int('units', max(16, int(base_u * 0.7)), min(128, int(base_u * 1.3)))
            params['dropout'] = trial.suggest_float('dropout', max(0.1, base_d - 0.1), min(0.5, base_d + 0.1))
            params['epochs'] = trial.suggest_int('epochs', max(20, base_e - 20), min(100, base_e + 20))
            params['batch_size'] = trial.suggest_categorical('batch_size', [16, 32, 64])
            params['sequence_length'] = trial.suggest_int('sequence_length', max(5, base_sl - 3), min(30, base_sl + 3))
            
        return params

    def _get_param_space(self, model_type: str, trial: optuna.Trial) -> Dict:
        return self._get_param_space_coarse(model_type, trial)

    def _time_series_cv(self, y: pd.Series, X: pd.DataFrame, model_type: str,
                        params: Dict, forecast_horizon: int) -> float:
        scores = []
        n_samples = len(y)
        fold_size = (n_samples - forecast_horizon) // self.cv_folds
        
        for fold in range(self.cv_folds):
            train_end = n_samples - forecast_horizon - (self.cv_folds - fold - 1) * fold_size
            train_start = max(0, train_end - 3 * fold_size)
            
            if train_end - train_start < forecast_horizon:
                continue
            
            y_train_cv = y.iloc[train_start:train_end]
            y_test_cv = y.iloc[train_end:train_end + forecast_horizon]
            
            X_train_cv = X.iloc[train_start:train_end] if X is not None else None
            X_test_cv = X.iloc[train_end:train_end + forecast_horizon] if X is not None else None
            
            try:
                model = create_model(model_type, params)
                model.fit(y_train_cv, X_train_cv)
                y_pred_cv = model.predict(forecast_horizon, X_test_cv)
                
                y_pred_cv = y_pred_cv[:len(y_test_cv)]
                metrics = model.evaluate(y_test_cv, y_pred_cv)
                scores.append(metrics[self.metric])
            except Exception as e:
                continue
        
        return np.mean(scores) if scores else float('inf')

    def _objective(self, model_type: str, y: pd.Series, X: pd.DataFrame,
                   forecast_horizon: int):
        def objective_wrapper(trial: optuna.Trial) -> float:
            params = self._get_param_space(model_type, trial)
            score = self._time_series_cv(y, X, model_type, params, forecast_horizon)
            return score
        return objective_wrapper

    def _objective_with_params(self, model_type: str, y: pd.Series, X: pd.DataFrame,
                               forecast_horizon: int, param_func):
        def objective_wrapper(trial: optuna.Trial) -> float:
            params = param_func(trial)
            score = self._time_series_cv(y, X, model_type, params, forecast_horizon)
            return score
        return objective_wrapper

    def fit(self, y: pd.Series, X: pd.DataFrame = None, forecast_horizon: int = 7):
        for model_type in self.model_types:
            print(f"\n正在优化模型: {model_type.upper()}")
            
            if self.two_stage_optimization:
                coarse_trials = max(3, int(self.n_trials * self.coarse_trials_ratio))
                fine_trials = self.n_trials - coarse_trials
                
                print(f"  阶段1/2 - 粗略搜索 ({coarse_trials} 次试验)...")
                study_coarse = optuna.create_study(direction=self.direction)
                study_coarse.optimize(
                    self._objective_with_params(
                        model_type, y, X, forecast_horizon,
                        lambda t: self._get_param_space_coarse(model_type, t)
                    ),
                    n_trials=coarse_trials,
                    show_progress_bar=False
                )
                best_coarse_params = study_coarse.best_params
                best_coarse_score = study_coarse.best_value
                print(f"    粗略搜索最佳{self.metric.upper()}: {best_coarse_score:.4f}")
                
                print(f"  阶段2/2 - 精细搜索 ({fine_trials} 次试验)...")
                study_fine = optuna.create_study(direction=self.direction)
                study_fine.optimize(
                    self._objective_with_params(
                        model_type, y, X, forecast_horizon,
                        lambda t: self._get_param_space_fine(model_type, t, best_coarse_params)
                    ),
                    n_trials=fine_trials,
                    show_progress_bar=False
                )
                
                if (self.direction == 'minimize' and study_fine.best_value < best_coarse_score) or \
                   (self.direction == 'maximize' and study_fine.best_value > best_coarse_score):
                    best_params = study_fine.best_params
                    best_score = study_fine.best_value
                    print(f"    精细搜索改进: {best_coarse_score:.4f} -> {best_score:.4f}")
                else:
                    best_params = best_coarse_params
                    best_score = best_coarse_score
                    print(f"    保持粗略搜索结果")
                
                total_trials = len(study_coarse.trials) + len(study_fine.trials)
            else:
                study = optuna.create_study(direction=self.direction)
                study.optimize(
                    self._objective(model_type, y, X, forecast_horizon),
                    n_trials=self.n_trials,
                    show_progress_bar=False
                )
                best_params = study.best_params
                best_score = study.best_value
                total_trials = len(study.trials)
            
            best_model = create_model(model_type, best_params)
            best_model.fit(y, X)
            
            self.best_models[model_type] = (best_model, best_params, best_score)
            self.study_results[model_type] = {
                'best_params': best_params,
                'best_score': best_score,
                'trials': total_trials,
                'two_stage': self.two_stage_optimization
            }
            
            print(f"{model_type.upper()} 最终最佳{self.metric.upper()}: {best_score:.4f}")
        
        self._select_best_model()
        return self

    def _select_best_model(self):
        best_score = float('inf') if self.direction == 'minimize' else float('-inf')
        
        for model_type, (model, params, score) in self.best_models.items():
            if (self.direction == 'minimize' and score < best_score) or \
               (self.direction == 'maximize' and score > best_score):
                best_score = score
                self.best_model = model
                self.best_model_name = model_type
                self.best_params = params
                self.best_score = score

    def predict(self, horizon: int, X_test: pd.DataFrame = None) -> np.ndarray:
        if self.best_model is None:
            raise ValueError("模型未训练，请先调用 fit() 方法")
        
        return self.best_model.predict(horizon, X_test)

    def predict_with_model(self, model_name: str, horizon: int,
                           X_test: pd.DataFrame = None) -> np.ndarray:
        if model_name not in self.best_models:
            raise ValueError(f"模型 {model_name} 不存在")
        
        model, _, _ = self.best_models[model_name]
        return model.predict(horizon, X_test)

    def get_model_comparison(self) -> pd.DataFrame:
        comparison = []
        for model_type, (_, params, score) in self.best_models.items():
            comparison.append({
                'model': model_type.upper(),
                f'{self.metric}': score,
                'best_params': str(params)
            })
        return pd.DataFrame(comparison).sort_values(self.metric)

    def update_with_feedback(self, feedback_data: pd.Series, X_feedback: pd.DataFrame = None,
                             retrain_all: bool = False, model_type: str = None):
        if retrain_all:
            models_to_retrain = self.model_types
        elif model_type:
            models_to_retrain = [model_type]
        else:
            models_to_retrain = [self.best_model_name]
        
        for mt in models_to_retrain:
            if mt in self.best_models:
                _, params, _ = self.best_models[mt]
                model = create_model(mt, params)
                model.fit(feedback_data, X_feedback)
                self.best_models[mt] = (model, params, self.best_models[mt][2])
        
        self._select_best_model()
        return self

    def create_ensemble(self, y_val: pd.Series, X_val: pd.DataFrame = None,
                       horizon: int = 7, weight_method: str = 'rank') -> EnsembleForecaster:
        models_dict = {name: model for name, (model, _, _) in self.best_models.items()}
        
        self.ensemble = EnsembleForecaster(models_dict)
        self.ensemble.fit(y_val, X_val, horizon, weight_method)
        return self.ensemble

    def predict_ensemble(self, horizon: int, X_test: pd.DataFrame = None) -> np.ndarray:
        if self.ensemble is None:
            raise ValueError("集成模型未创建，请先调用 create_ensemble() 方法")
        
        self.ensemble_predictions = self.ensemble.predict(horizon, X_test)
        return self.ensemble_predictions

    def get_ensemble_weights(self) -> pd.DataFrame:
        if self.ensemble is None:
            return pd.DataFrame()
        return self.ensemble.get_weights_summary()

    def get_all_model_predictions(self, horizon: int, X_test: pd.DataFrame = None) -> pd.DataFrame:
        if self.ensemble is None:
            models_dict = {name: model for name, (model, _, _) in self.best_models.items()}
            temp_ensemble = EnsembleForecaster(models_dict)
            return temp_ensemble.get_model_predictions(horizon, X_test)
        return self.ensemble.get_model_predictions(horizon, X_test)

    def init_interpreter(self, feature_names: List[str]):
        self.interpreter = ModelInterpreter(feature_names)
        return self.interpreter

    def get_feature_importance(self, model_name: str = None, 
                              X: pd.DataFrame = None, y: pd.Series = None) -> pd.DataFrame:
        if self.interpreter is None:
            if X is not None:
                self.init_interpreter(X.columns.tolist())
            else:
                return pd.DataFrame()
        
        if model_name is None:
            model_name = self.best_model_name
        
        if model_name not in self.best_models:
            return pd.DataFrame()
        
        model, _, _ = self.best_models[model_name]
        return self.interpreter.get_feature_importance(model.model, model_name, X, y)
