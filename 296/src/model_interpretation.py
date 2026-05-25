import pandas as pd
import numpy as np
from typing import Dict, List, Tuple
import warnings
warnings.filterwarnings('ignore')


class ModelInterpreter:
    def __init__(self, feature_names: List[str]):
        self.feature_names = feature_names
        self.importance_df = None

    def get_xgboost_importance(self, model) -> pd.DataFrame:
        if hasattr(model, 'feature_importances_'):
            importance = model.feature_importances_
            importance_df = pd.DataFrame({
                'feature': self.feature_names,
                'importance': importance,
                'importance_pct': importance / importance.sum() * 100
            }).sort_values('importance', ascending=False)
            self.importance_df = importance_df
            return importance_df
        return pd.DataFrame()

    def get_arima_coefficients(self, model) -> pd.DataFrame:
        if hasattr(model, 'get_params'):
            params = model.get_params()
            order = params.get('order', (1, 1, 1))
            seasonal_order = params.get('seasonal_order', (0, 0, 0, 0))
            
            coef_data = []
            for i, p in enumerate(['AR', 'I', 'MA']):
                coef_data.append({
                    'feature': f'{p}(order_{i+1})',
                    'coefficient': order[i],
                    'type': 'Non-Seasonal'
                })
            for i, p in enumerate(['SAR', 'SI', 'SMA']):
                coef_data.append({
                    'feature': f'{p}(order_{i+1})',
                    'coefficient': seasonal_order[i],
                    'type': 'Seasonal'
                })
            
            return pd.DataFrame(coef_data)
        return pd.DataFrame()

    def get_prophet_components(self, model, forecast_df) -> pd.DataFrame:
        if hasattr(model, 'params'):
            components = []
            for col in ['trend', 'yearly', 'weekly', 'daily']:
                if col in forecast_df.columns:
                    comp_magnitude = np.abs(forecast_df[col]).mean()
                    components.append({
                        'component': col,
                        'magnitude': comp_magnitude,
                        'contribution_pct': comp_magnitude / np.abs(forecast_df['yhat']).mean() * 100
                    })
            return pd.DataFrame(components).sort_values('magnitude', ascending=False)
        return pd.DataFrame()

    def permutation_importance(self, model, X: pd.DataFrame, y: pd.Series, 
                              n_repeats: int = 5) -> pd.DataFrame:
        from sklearn.metrics import mean_squared_error
        
        baseline = mean_squared_error(y, model.predict(X))
        
        importance_scores = []
        
        for feature in self.feature_names:
            scores = []
            for _ in range(n_repeats):
                X_permuted = X.copy()
                X_permuted[feature] = np.random.permutation(X_permuted[feature])
                score = mean_squared_error(y, model.predict(X_permuted))
                scores.append(score - baseline)
            importance_scores.append({
                'feature': feature,
                'importance': np.mean(scores),
                'std': np.std(scores)
            })
        
        importance_df = pd.DataFrame(importance_scores).sort_values('importance', ascending=False)
        importance_df['importance_pct'] = importance_df['importance'] / importance_df['importance'].abs().sum() * 100
        return importance_df

    def get_feature_importance(self, model, model_name: str, 
                              X: pd.DataFrame = None, y: pd.Series = None) -> pd.DataFrame:
        model_name = model_name.lower()
        
        if model_name == 'xgboost':
            return self.get_xgboost_importance(model)
        elif model_name == 'arima':
            return self.get_arima_coefficients(model)
        elif model_name == 'lstm':
            return self._lstm_gradient_importance(model, X, y)
        else:
            if X is not None and y is not None:
                try:
                    return self.permutation_importance(model, X, y)
                except:
                    pass
        return pd.DataFrame()

    def _lstm_gradient_importance(self, model, X: pd.DataFrame, y: pd.Series) -> pd.DataFrame:
        import tensorflow as tf
        
        if X is None or not hasattr(model.model, 'layers'):
            return pd.DataFrame()
        
        X_tensor = tf.convert_to_tensor(X.values.astype(np.float32))
        
        with tf.GradientTape() as tape:
            tape.watch(X_tensor)
            predictions = model.model(X_tensor)
        
        gradients = tape.gradient(predictions, X_tensor)
        
        if gradients is not None:
            grad_magnitude = np.abs(gradients.numpy()).mean(axis=0)
            importance_df = pd.DataFrame({
                'feature': self.feature_names,
                'gradient_magnitude': grad_magnitude,
                'importance_pct': grad_magnitude / grad_magnitude.sum() * 100
            }).sort_values('gradient_magnitude', ascending=False)
            return importance_df
        
        return pd.DataFrame()

    def partial_dependence_plot(self, model, X: pd.DataFrame, feature: str, 
                               grid_resolution: int = 20) -> Tuple[np.ndarray, np.ndarray]:
        X_temp = X.copy()
        feature_values = np.linspace(X[feature].min(), X[feature].max(), grid_resolution)
        pd_values = []
        
        for val in feature_values:
            X_temp[feature] = val
            preds = model.predict(X_temp)
            pd_values.append(np.mean(preds))
        
        return feature_values, np.array(pd_values)
