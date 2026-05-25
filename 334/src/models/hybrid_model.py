import numpy as np
import joblib
from sklearn.linear_model import Ridge, QuantileRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
import warnings
warnings.filterwarnings('ignore')


def hybrid_pinball_loss(y_true, y_pred, quantile):
    error = y_true - y_pred
    return np.mean(np.maximum(quantile * error, (quantile - 1) * error))


class HybridModel:
    def __init__(self, xgb_model, lstm_model, model_dir='models'):
        self.xgb_model = xgb_model
        self.lstm_model = lstm_model
        self.model_dir = model_dir
        self.meta_models = []
        self.quantile_meta_models = {}
        self.quantiles = [0.05, 0.1, 0.25, 0.5, 0.75, 0.9, 0.95]
        self._coverage_stats = None
        self.is_fitted_ = False

    def fit(self, X_struct, X_ts, y):
        print("\n" + "="*60)
        print("Training Hybrid Ensemble Model with Quantile Regression")
        print("="*60)
        
        X_train_s, X_val_s, X_train_t, X_val_t, y_train, y_val = train_test_split(
            X_struct, X_ts, y, test_size=0.3, random_state=42
        )
        
        xgb_pred_train = self.xgb_model.predict(X_train_s)
        lstm_pred_train = self.lstm_model.predict(X_train_t)
        
        xgb_pred_val = self.xgb_model.predict(X_val_s)
        lstm_pred_val = self.lstm_model.predict(X_val_t)
        
        ensemble_train = np.hstack([xgb_pred_train, lstm_pred_train])
        ensemble_val = np.hstack([xgb_pred_val, lstm_pred_val])
        
        print("\nTraining point prediction meta-models (Ridge)...")
        self.meta_models = []
        for i in range(2):
            meta = Ridge(alpha=1.0)
            meta.fit(ensemble_train, y_train[:, i])
            self.meta_models.append(meta)
        
        meta_pred_val = np.column_stack([
            meta.predict(ensemble_val) for meta in self.meta_models
        ])
        
        print("\nTraining quantile meta-models (Quantile Regression with Pinball Loss)...")
        print(f"Quantiles: {self.quantiles}")
        for q in self.quantiles:
            q_models = []
            for i in range(2):
                q_meta = QuantileRegressor(
                    quantile=q,
                    alpha=1.0,
                    solver='highs'
                )
                q_meta.fit(ensemble_train, y_train[:, i])
                q_models.append(q_meta)
            self.quantile_meta_models[q] = q_models
            
            q_pred_val = np.column_stack([
                meta.predict(ensemble_val) for meta in q_models
            ])
            pb_loss = np.mean([
                hybrid_pinball_loss(y_val[:, i], q_pred_val[:, i], q)
                for i in range(2)
            ])
            print(f"  Q{int(q*100):2d} Pinball Loss: {pb_loss:.4f}")
        
        xgb_mae = mean_absolute_error(y_val, xgb_pred_val)
        lstm_mae = mean_absolute_error(y_val, lstm_pred_val)
        hybrid_mae = mean_absolute_error(y_val, meta_pred_val)
        
        xgb_rmse = np.sqrt(mean_squared_error(y_val, xgb_pred_val))
        lstm_rmse = np.sqrt(mean_squared_error(y_val, lstm_pred_val))
        hybrid_rmse = np.sqrt(mean_squared_error(y_val, meta_pred_val))
        
        xgb_r2 = r2_score(y_val, xgb_pred_val)
        lstm_r2 = r2_score(y_val, lstm_pred_val)
        hybrid_r2 = r2_score(y_val, meta_pred_val)
        
        print("\nModel Performance Comparison:")
        print(f"{'Model':<15} {'MAE':>12} {'RMSE':>12} {'R2':>10}")
        print("-" * 50)
        print(f"{'XGBoost':<15} {xgb_mae:>12.2f} {xgb_rmse:>12.2f} {xgb_r2:>10.4f}")
        print(f"{'LSTM':<15} {lstm_mae:>12.2f} {lstm_rmse:>12.2f} {lstm_r2:>10.4f}")
        print(f"{'Hybrid':<15} {hybrid_mae:>12.2f} {hybrid_rmse:>12.2f} {hybrid_r2:>10.4f}")
        
        self._calculate_coverage(X_val_s, X_val_t, y_val)
        
        self.is_fitted_ = True
        return self

    def _calculate_coverage(self, X_val_s, X_val_t, y_val):
        xgb_val = self.xgb_model.predict(X_val_s)
        lstm_val = self.lstm_model.predict(X_val_t)
        ensemble_val = np.hstack([xgb_val, lstm_val])
        
        quantile_preds = {}
        for q in self.quantiles:
            quantile_preds[q] = np.column_stack([
                meta.predict(ensemble_val) for meta in self.quantile_meta_models[q]
            ])
        
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
        print("\nHybrid Model Quantile Coverage Verification:")
        for q, cov in coverage_stats.items():
            if isinstance(q, str):
                print(f"  {q}: {cov:.3f}")
            else:
                print(f"  Q{int(q*100):2d}: {cov:.3f} (expected: {q:.2f})")

    def predict(self, X_struct, X_ts):
        if not self.is_fitted_:
            raise RuntimeError("Hybrid model must be fitted before predict")
        
        xgb_pred = self.xgb_model.predict(X_struct)
        lstm_pred = self.lstm_model.predict(X_ts)
        
        ensemble = np.hstack([xgb_pred, lstm_pred])
        
        hybrid_pred = np.column_stack([
            meta.predict(ensemble) for meta in self.meta_models
        ])
        
        return hybrid_pred

    def predict_with_interval(self, X_struct, X_ts, confidence=0.9):
        if not self.is_fitted_:
            raise RuntimeError("Hybrid model must be fitted before predict")
        
        xgb_pred = self.xgb_model.predict(X_struct)
        lstm_pred = self.lstm_model.predict(X_ts)
        
        ensemble = np.hstack([xgb_pred, lstm_pred])
        hybrid_pred = np.column_stack([
            meta.predict(ensemble) for meta in self.meta_models
        ])
        
        lower_q = max(q for q in self.quantiles if q <= (1 - confidence) / 2)
        upper_q = min(q for q in self.quantiles if q >= 1 - (1 - confidence) / 2)
        
        lower_pred = np.column_stack([
            meta.predict(ensemble) for meta in self.quantile_meta_models[lower_q]
        ])
        upper_pred = np.column_stack([
            meta.predict(ensemble) for meta in self.quantile_meta_models[upper_q]
        ])
        
        lower_pred = np.minimum(lower_pred, hybrid_pred * 0.5)
        upper_pred = np.maximum(upper_pred, hybrid_pred * 1.5)
        
        quantile_preds = {}
        for q in self.quantiles:
            quantile_preds[q] = np.column_stack([
                meta.predict(ensemble) for meta in self.quantile_meta_models[q]
            ])
        
        interval_width = upper_pred - lower_pred
        relative_width = interval_width / (hybrid_pred + 1e-6)
        quality_score = np.maximum(0, 1 - np.mean(relative_width) * 0.5)
        
        return {
            'point': hybrid_pred,
            'lower': lower_pred,
            'upper': upper_pred,
            'confidence': confidence,
            'actual_quantiles': [lower_q, upper_q],
            'xgb_prediction': xgb_pred,
            'lstm_prediction': lstm_pred,
            'quantiles': quantile_preds,
            'coverage_stats': self._coverage_stats,
            'interval_quality_score': float(quality_score),
            'interval_width': interval_width.tolist()
        }

    def get_model_contributions(self, X_struct, X_ts):
        xgb_pred = self.xgb_model.predict(X_struct)
        lstm_pred = self.lstm_model.predict(X_ts)
        
        contributions = []
        for i, meta in enumerate(self.meta_models):
            coef = meta.coef_
            intercept = meta.intercept_
            contributions.append({
                'target': 'first_week' if i == 0 else 'total',
                'xgb_weight': float(coef[0]),
                'lstm_weight': float(coef[1]),
                'intercept': float(intercept)
            })
        
        return contributions

    def save(self, path):
        data = {
            'meta_models': self.meta_models,
            'quantile_meta_models': self.quantile_meta_models,
            'quantiles': self.quantiles,
            '_coverage_stats': self._coverage_stats,
            'is_fitted_': self.is_fitted_
        }
        joblib.dump(data, f'{self.model_dir}/{path}')

    @classmethod
    def load(cls, path, xgb_model, lstm_model, model_dir='models'):
        instance = cls(xgb_model, lstm_model, model_dir)
        data = joblib.load(f'{model_dir}/{path}')
        instance.meta_models = data['meta_models']
        instance.quantile_meta_models = data.get('quantile_meta_models', {})
        instance.quantiles = data.get('quantiles', instance.quantiles)
        instance._coverage_stats = data.get('_coverage_stats', None)
        instance.is_fitted_ = data['is_fitted_']
        return instance
