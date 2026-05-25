import pandas as pd
import numpy as np
from typing import Dict, Optional, List, Tuple
import logging
import warnings
warnings.filterwarnings('ignore')

try:
    import lightgbm as lgb
except ImportError:
    lgb = None

from sklearn.metrics import mean_absolute_error, mean_squared_error
from config import Config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class LightGBMModel:
    def __init__(self, config: Optional[Dict] = None):
        self.config = config or Config().get('models.lightgbm', {})
        self.model = None
        self.feature_cols = None
        self.target_col = 'quantity'
        self.product_id = None
        self.region = None
        self.warehouse = None

    def _prepare_data(self, df: pd.DataFrame, feature_cols: List[str],
                      target_col: str = 'quantity') -> Tuple[np.ndarray, np.ndarray]:
        X = df[feature_cols].values
        y = df[target_col].values
        return X, y

    def fit(self, train_df: pd.DataFrame, feature_cols: List[str],
            target_col: str = 'quantity',
            valid_df: Optional[pd.DataFrame] = None,
            product_id: str = None, region: str = None, warehouse: str = None) -> 'LightGBMModel':
        if lgb is None:
            raise ImportError("LightGBM is not installed. Please install it with: pip install lightgbm")

        self.feature_cols = feature_cols
        self.target_col = target_col
        self.product_id = product_id
        self.region = region
        self.warehouse = warehouse

        logger.info(f"Fitting LightGBM model for {product_id} - {region} - {warehouse}")
        logger.info(f"Number of features: {len(feature_cols)}")

        X_train, y_train = self._prepare_data(train_df, feature_cols, target_col)

        train_data = lgb.Dataset(X_train, label=y_train, feature_name=feature_cols)

        valid_sets = [train_data]
        if valid_df is not None and len(valid_df) > 0:
            X_valid, y_valid = self._prepare_data(valid_df, feature_cols, target_col)
            valid_data = lgb.Dataset(X_valid, label=y_valid,
                                     feature_name=feature_cols, reference=train_data)
            valid_sets.append(valid_data)

        params = {
            'num_leaves': self.config.get('num_leaves', 31),
            'max_depth': self.config.get('max_depth', -1),
            'learning_rate': self.config.get('learning_rate', 0.05),
            'n_estimators': self.config.get('n_estimators', 500),
            'objective': self.config.get('objective', 'regression'),
            'metric': self.config.get('metric', 'rmse'),
            'bagging_fraction': 0.8,
            'feature_fraction': 0.8,
            'bagging_freq': 5,
            'verbose': -1,
            'random_state': 42
        }

        callbacks = [
            lgb.early_stopping(stopping_rounds=self.config.get('early_stopping_rounds', 50)),
            lgb.log_evaluation(period=0)
        ]

        self.model = lgb.train(
            params,
            train_data,
            valid_sets=valid_sets,
            callbacks=callbacks
        )

        return self

    def predict(self, df: pd.DataFrame) -> pd.Series:
        if self.model is None:
            raise ValueError("Model has not been fitted yet")

        logger.info("Predicting with LightGBM model...")

        X = df[self.feature_cols].values
        predictions = self.model.predict(X, num_iteration=self.model.best_iteration)

        predictions = np.maximum(0, predictions)

        return pd.Series(predictions, index=df.index)

    def predict_with_interval(self, df: pd.DataFrame,
                               confidence: float = 0.95,
                               n_bootstraps: int = 100) -> pd.DataFrame:
        if self.model is None:
            raise ValueError("Model has not been fitted yet")

        logger.info(f"Predicting with {confidence * 100}% confidence interval...")

        point_forecast = self.predict(df)

        np.random.seed(42)
        bootstrap_preds = []

        for i in range(n_bootstraps):
            sample_idx = np.random.choice(len(df), size=len(df), replace=True)
            sample_df = df.iloc[sample_idx]
            X_sample = sample_df[self.feature_cols].values
            pred = self.model.predict(X_sample, num_iteration=self.model.best_iteration)
            bootstrap_preds.append(pred)

        bootstrap_preds = np.array(bootstrap_preds)
        alpha = (1 - confidence) / 2
        lower = np.percentile(bootstrap_preds, alpha * 100, axis=0)
        upper = np.percentile(bootstrap_preds, (1 - alpha) * 100, axis=0)

        result_df = pd.DataFrame({
            'date': df['date'].values,
            'forecast': point_forecast.values,
            'forecast_lower': np.maximum(0, lower),
            'forecast_upper': upper
        })

        if self.product_id:
            result_df['product_id'] = self.product_id
        if self.region:
            result_df['region'] = self.region
        if self.warehouse:
            result_df['warehouse'] = self.warehouse

        return result_df

    def evaluate(self, test_df: pd.DataFrame) -> Dict[str, float]:
        if self.model is None:
            raise ValueError("Model has not been fitted yet")

        logger.info("Evaluating LightGBM model...")

        y_pred = self.predict(test_df)
        y_true = test_df[self.target_col].values

        mape = np.mean(np.abs((y_true - y_pred) / np.maximum(y_true, 1))) * 100
        rmse = np.sqrt(mean_squared_error(y_true, y_pred))
        mae = mean_absolute_error(y_true, y_pred)

        metrics = {
            'mape': mape,
            'rmse': rmse,
            'mae': mae
        }

        logger.info(f"LightGBM model metrics: {metrics}")
        return metrics

    def get_feature_importance(self, importance_type: str = 'gain') -> pd.DataFrame:
        if self.model is None:
            raise ValueError("Model has not been fitted yet")

        importance = self.model.feature_importance(importance_type=importance_type)

        importance_df = pd.DataFrame({
            'feature': self.feature_cols,
            'importance': importance
        }).sort_values('importance', ascending=False)

        total_importance = importance_df['importance'].sum()
        if total_importance > 0:
            importance_df['importance_pct'] = importance_df['importance'] / total_importance * 100

        return importance_df

    def plot_feature_importance(self, top_n: int = 20, importance_type: str = 'gain'):
        try:
            import matplotlib.pyplot as plt
            importance_df = self.get_feature_importance(importance_type).head(top_n)

            plt.figure(figsize=(10, 8))
            plt.barh(importance_df['feature'], importance_df['importance'])
            plt.xlabel('Importance')
            plt.ylabel('Feature')
            plt.title(f'Top {top_n} Feature Importance')
            plt.tight_layout()
            return plt
        except Exception as e:
            logger.warning(f"Could not plot feature importance: {e}")
            return None

    def optimize_hyperparameters(self, train_df: pd.DataFrame, valid_df: pd.DataFrame,
                                  feature_cols: List[str], target_col: str = 'quantity',
                                  n_trials: int = 50) -> Dict:
        try:
            import optuna
        except ImportError:
            logger.warning("Optuna not installed, skipping hyperparameter optimization")
            return self.config

        logger.info(f"Optimizing hyperparameters with {n_trials} trials...")

        X_train, y_train = self._prepare_data(train_df, feature_cols, target_col)
        X_valid, y_valid = self._prepare_data(valid_df, feature_cols, target_col)

        def objective(trial):
            params = {
                'num_leaves': trial.suggest_int('num_leaves', 20, 300),
                'max_depth': trial.suggest_int('max_depth', -1, 20),
                'learning_rate': trial.suggest_float('learning_rate', 0.005, 0.3, log=True),
                'n_estimators': trial.suggest_int('n_estimators', 100, 1000),
                'min_child_samples': trial.suggest_int('min_child_samples', 5, 100),
                'subsample': trial.suggest_float('subsample', 0.5, 1.0),
                'colsample_bytree': trial.suggest_float('colsample_bytree', 0.5, 1.0),
                'reg_alpha': trial.suggest_float('reg_alpha', 0.0, 10.0),
                'reg_lambda': trial.suggest_float('reg_lambda', 0.0, 10.0),
            }

            model = lgb.LGBMRegressor(**params, random_state=42, verbose=-1)
            model.fit(X_train, y_train,
                      eval_set=[(X_valid, y_valid)],
                      callbacks=[lgb.early_stopping(50, verbose=False)])

            preds = model.predict(X_valid)
            rmse = np.sqrt(mean_squared_error(y_valid, preds))
            return rmse

        study = optuna.create_study(direction='minimize')
        study.optimize(objective, n_trials=n_trials)

        best_params = {**self.config, **study.best_params}
        self.config = best_params

        logger.info(f"Best hyperparameters: {best_params}")
        return best_params

    def save_model(self, filepath: str):
        if self.model is None:
            raise ValueError("Model has not been fitted yet")
        self.model.save_model(filepath)
        logger.info(f"Model saved to {filepath}")

    def load_model(self, filepath: str):
        if lgb is None:
            raise ImportError("LightGBM is not installed")
        self.model = lgb.Booster(model_file=filepath)
        logger.info(f"Model loaded from {filepath}")
        return self
