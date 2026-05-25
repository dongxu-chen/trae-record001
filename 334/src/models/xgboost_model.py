import numpy as np
import xgboost as xgb
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
import joblib
import warnings
warnings.filterwarnings('ignore')


def xgb_pinball_loss(y_true, y_pred, quantile):
    error = y_true - y_pred
    return np.mean(np.maximum(quantile * error, (quantile - 1) * error))


class XGBoostModel:
    def __init__(self, model_dir='models', task='total'):
        self.model_dir = model_dir
        self.task = task
        self.model = None
        self.quantile_models = {}
        self.feature_importances_ = None
        self.feature_names_ = None
        self.quantiles = [0.05, 0.1, 0.25, 0.5, 0.75, 0.9, 0.95]
        self._coverage_stats = None

    def _build_base_model(self):
        return xgb.XGBRegressor(
            objective='reg:squarederror',
            n_estimators=200,
            max_depth=8,
            learning_rate=0.05,
            subsample=0.8,
            colsample_bytree=0.8,
            min_child_weight=5,
            reg_alpha=0.1,
            reg_lambda=1.0,
            random_state=42,
            verbosity=0
        )

    def _build_quantile_model(self, quantile):
        return xgb.XGBRegressor(
            objective='reg:quantileerror',
            quantile_alpha=quantile,
            n_estimators=150,
            max_depth=6,
            learning_rate=0.05,
            subsample=0.8,
            colsample_bytree=0.8,
            min_child_weight=5,
            random_state=42,
            verbosity=0
        )

    def fit(self, X, y, feature_names=None):
        self.feature_names_ = feature_names
        
        X_train, X_val, y_train, y_val = train_test_split(
            X, y, test_size=0.2, random_state=42
        )
        
        self.model = []
        for i in range(y.shape[1]):
            est = self._build_base_model()
            est.fit(
                X_train, y_train[:, i],
                eval_set=[(X_val, y_val[:, i])],
                verbose=False
            )
            self.model.append(est)
        
        print(f"\nXGBoost quantile model training (Pinball Loss)...")
        print(f"Quantiles: {self.quantiles}")
        for q in self.quantiles:
            q_models = []
            for i in range(y.shape[1]):
                q_est = self._build_quantile_model(q)
                q_est.fit(X_train, y_train[:, i], verbose=False)
                q_models.append(q_est)
            self.quantile_models[q] = q_models
            
            val_pred_q = np.column_stack([est.predict(X_val) for est in q_models])
            pinball_loss_val = np.mean([
                xgb_pinball_loss(y_val[:, i], val_pred_q[:, i], q)
                for i in range(y.shape[1])
            ])
            print(f"  Q{int(q*100):2d} Pinball Loss: {pinball_loss_val:.4f}")
        
        importances = []
        for est in self.model:
            importances.append(est.feature_importances_)
        self.feature_importances_ = np.mean(importances, axis=0)
        
        val_pred = self.predict(X_val)
        metrics = self._calculate_metrics(y_val, val_pred)
        print(f"\nXGBoost {self.task} model training completed.")
        print(f"  MAE: {metrics['mae']:.2f}, RMSE: {metrics['rmse']:.2f}, R2: {metrics['r2']:.4f}")
        
        self._calculate_coverage(X_val, y_val)
        
        return self

    def _calculate_coverage(self, X_val, y_val):
        quantile_preds = {}
        for q in self.quantiles:
            quantile_preds[q] = np.column_stack([est.predict(X_val) for est in self.quantile_models[q]])
        
        coverage_stats = {}
        
        for q in self.quantiles:
            covered = np.mean(y_val <= quantile_preds[q])
            coverage_stats[q] = covered
        
        for conf in [0.5, 0.8, 0.9, 0.95]:
            lower_q = (1 - conf) / 2
            upper_q = 1 - lower_q
            
            if lower_q in self.quantiles and upper_q in self.quantiles:
                lower = quantile_preds[lower_q]
                upper = quantile_preds[upper_q]
                
                covered = np.mean((y_val >= lower) & (y_val <= upper))
                coverage_stats[f'{int(conf*100)}%_interval'] = covered
        
        self._coverage_stats = coverage_stats
        print("\nXGBoost Quantile Coverage Verification:")
        for q, cov in coverage_stats.items():
            if isinstance(q, str):
                print(f"  {q}: {cov:.3f}")
            else:
                print(f"  Q{int(q*100):2d}: {cov:.3f} (expected: {q:.2f})")

    def predict(self, X):
        if self.model is None or len(self.model) == 0:
            raise RuntimeError("Model must be fitted before predict")
        predictions = [est.predict(X) for est in self.model]
        return np.column_stack(predictions)

    def predict_with_interval(self, X, confidence=0.9):
        if self.model is None or len(self.model) == 0:
            raise RuntimeError("Model must be fitted before predict")
        
        point_pred = self.predict(X)
        
        lower_q = max(q for q in self.quantiles if q <= (1 - confidence) / 2)
        upper_q = min(q for q in self.quantiles if q >= 1 - (1 - confidence) / 2)
        
        lower_pred = np.column_stack([est.predict(X) for est in self.quantile_models[lower_q]])
        upper_pred = np.column_stack([est.predict(X) for est in self.quantile_models[upper_q]])
        
        lower_pred = np.minimum(lower_pred, point_pred * 0.5)
        upper_pred = np.maximum(upper_pred, point_pred * 1.5)
        
        quantile_preds = {}
        for q in self.quantiles:
            quantile_preds[q] = np.column_stack([est.predict(X) for est in self.quantile_models[q]])
        
        return {
            'point': point_pred,
            'lower': lower_pred,
            'upper': upper_pred,
            'confidence': confidence,
            'actual_quantiles': [lower_q, upper_q],
            'quantiles': quantile_preds,
            'coverage_stats': self._coverage_stats
        }

    def get_feature_importance(self, top_n=20):
        if self.feature_importances_ is None:
            raise RuntimeError("Model must be fitted before getting feature importance")
        
        indices = np.argsort(self.feature_importances_)[::-1]
        names = np.array(self.feature_names_)[indices] if self.feature_names_ else np.array([f'feature_{i}' for i in indices])
        scores = self.feature_importances_[indices]
        
        return list(zip(names[:top_n], scores[:top_n]))

    def _calculate_metrics(self, y_true, y_pred):
        return {
            'mae': mean_absolute_error(y_true, y_pred),
            'rmse': np.sqrt(mean_squared_error(y_true, y_pred)),
            'r2': r2_score(y_true, y_pred)
        }

    def save(self, path):
        data = {
            'model': self.model,
            'quantile_models': self.quantile_models,
            'feature_importances_': self.feature_importances_,
            'feature_names_': self.feature_names_,
            'quantiles': self.quantiles,
            '_coverage_stats': self._coverage_stats
        }
        joblib.dump(data, f'{self.model_dir}/{path}')

    @classmethod
    def load(cls, path, model_dir='models', task='total'):
        instance = cls(model_dir=model_dir, task=task)
        data = joblib.load(f'{model_dir}/{path}')
        instance.model = data['model']
        instance.quantile_models = data['quantile_models']
        instance.feature_importances_ = data['feature_importances_']
        instance.feature_names_ = data['feature_names_']
        instance.quantiles = data.get('quantiles', instance.quantiles)
        instance._coverage_stats = data.get('_coverage_stats', None)
        return instance
