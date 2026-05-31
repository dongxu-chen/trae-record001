import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
from scipy.stats import norm
from scipy import stats
import joblib
import os
from typing import Dict, Tuple, Optional, List
from datetime import datetime, timedelta
from collections import deque


class ResponseTimePredictor:
    def __init__(self, params: dict = None, warning_config: dict = None):
        self.params = params or {
            "objective": "reg:squarederror",
            "max_depth": 8,
            "learning_rate": 0.08,
            "n_estimators": 150,
            "subsample": 0.85,
            "colsample_bytree": 0.8,
            "random_state": 42,
        }
        self.warning_config = warning_config or {
            "enabled": True,
            "prediction_horizon_requests": 5,
            "warning_threshold_probability": 0.6,
            "critical_threshold_probability": 0.85,
            "trend_window_size": 10,
            "trend_slope_threshold": 0.15,
        }
        self.model = None
        self.feature_names = []
        self.training_metrics = {}
        self.dynamic_thresholds = {}
        self.threshold_percentile = 99
        self.threshold_safety_margin = 1.2
        self.min_history_for_threshold = 50
        self.prediction_history = deque(maxlen=50)

    def train(self, X: pd.DataFrame, y: pd.Series, test_size: float = 0.2) -> Dict:
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=test_size, random_state=self.params.get("random_state", 42)
        )

        self.feature_names = X_train.columns.tolist()

        self.model = xgb.XGBRegressor(**self.params)
        self.model.fit(
            X_train, y_train,
            eval_set=[(X_test, y_test)],
            verbose=False
        )

        y_pred_train = self.model.predict(X_train)
        y_pred_test = self.model.predict(X_test)

        self.training_metrics = {
            "train": {
                "mse": mean_squared_error(y_train, y_pred_train),
                "rmse": np.sqrt(mean_squared_error(y_train, y_pred_train)),
                "mae": mean_absolute_error(y_train, y_pred_train),
                "r2": r2_score(y_train, y_pred_train),
            },
            "test": {
                "mse": mean_squared_error(y_test, y_pred_test),
                "rmse": np.sqrt(mean_squared_error(y_test, y_pred_test)),
                "mae": mean_absolute_error(y_test, y_pred_test),
                "r2": r2_score(y_test, y_pred_test),
            }
        }

        return self.training_metrics

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        if self.model is None:
            raise ValueError("Model not trained. Call train() first.")
        
        X_aligned = X.reindex(columns=self.feature_names, fill_value=0)
        return self.model.predict(X_aligned)

    def predict_with_uncertainty(
        self, 
        X: pd.DataFrame, 
        num_bootstrap: int = 10
    ) -> Tuple[np.ndarray, np.ndarray]:
        if self.model is None:
            raise ValueError("Model not trained. Call train() first.")

        X_aligned = X.reindex(columns=self.feature_names, fill_value=0)
        
        base_prediction = self.model.predict(X_aligned)
        
        predictions = []
        for _ in range(num_bootstrap):
            noise = np.random.normal(0, self.training_metrics["test"]["rmse"] * 0.1, size=len(base_prediction))
            predictions.append(base_prediction + noise)
        
        predictions = np.array(predictions)
        mean_pred = np.mean(predictions, axis=0)
        std_pred = np.std(predictions, axis=0)
        
        return mean_pred, std_pred

    def calculate_dynamic_threshold(
        self,
        endpoint: str,
        historical_stats: Dict,
        percentile: Optional[int] = None,
        safety_margin: Optional[float] = None
    ) -> float:
        percentile = percentile or self.threshold_percentile
        safety_margin = safety_margin or self.threshold_safety_margin
        
        endpoint_p99 = historical_stats.get("endpoint_p99", {}).get(endpoint)
        endpoint_count = historical_stats.get("endpoint_count", {}).get(endpoint, 0)
        
        if endpoint_p99 is not None and endpoint_count >= self.min_history_for_threshold:
            threshold = endpoint_p99 * safety_margin
        else:
            threshold = historical_stats.get("global_p99", 3000) * safety_margin
        
        return threshold

    def update_dynamic_thresholds(self, historical_stats: Dict):
        endpoints = historical_stats.get("endpoint_p99", {}).keys()
        for endpoint in endpoints:
            self.dynamic_thresholds[endpoint] = self.calculate_dynamic_threshold(
                endpoint, historical_stats
            )

    def calculate_timeout_probability(
        self, 
        predictions: np.ndarray, 
        std_dev: np.ndarray,
        threshold: float
    ) -> np.ndarray:
        z_scores = (threshold - predictions) / (std_dev + 1e-8)
        timeout_prob = 1 - norm.cdf(z_scores)
        return np.clip(timeout_prob, 0, 1)

    def detect_anomaly(
        self,
        current_pred: float,
        historical_mean: float,
        historical_std: float,
        threshold: float = 2.5
    ) -> Tuple[bool, float]:
        z_score = abs(current_pred - historical_mean) / (historical_std + 1e-8)
        is_anomaly = z_score > threshold
        return is_anomaly, z_score

    def analyze_trend(
        self,
        prediction_history: List[float],
        window_size: Optional[int] = None
    ) -> Dict:
        window_size = window_size or self.warning_config["trend_window_size"]
        
        if len(prediction_history) < window_size:
            return {
                "has_trend": False,
                "slope": 0.0,
                "is_rising": False,
                "trend_strength": "none",
                "data_points": len(prediction_history)
            }
        
        recent_data = list(prediction_history)[-window_size:]
        x = np.arange(len(recent_data))
        slope, intercept, r_value, p_value, std_err = stats.linregress(x, recent_data)
        
        slope_percent = slope / (np.mean(recent_data) + 1e-8)
        
        is_rising = slope > 0
        has_significant_trend = abs(slope_percent) > self.warning_config["trend_slope_threshold"]
        
        trend_strength = "strong" if has_significant_trend and abs(slope_percent) > 0.3 else \
                         "moderate" if has_significant_trend else "weak"
        
        return {
            "has_trend": has_significant_trend,
            "slope": float(slope),
            "slope_percent": float(slope_percent),
            "is_rising": is_rising,
            "trend_strength": trend_strength,
            "r_squared": float(r_value ** 2),
            "p_value": float(p_value),
            "data_points": len(recent_data)
        }

    def predict_future_risks(
        self,
        current_pred: float,
        current_std: float,
        trend_info: Dict,
        dynamic_threshold: float,
        horizon: Optional[int] = None
    ) -> Dict:
        horizon = horizon or self.warning_config["prediction_horizon_requests"]
        
        future_predictions = []
        future_timeout_probs = []
        
        base_pred = current_pred
        slope = trend_info.get("slope", 0) if trend_info.get("is_rising", False) else 0
        
        for i in range(horizon):
            future_pred = base_pred + slope * (i + 1)
            future_std = current_std * (1 + i * 0.1)
            
            z_score = (dynamic_threshold - future_pred) / (future_std + 1e-8)
            timeout_prob = 1 - norm.cdf(z_score)
            
            future_predictions.append(float(future_pred))
            future_timeout_probs.append(float(np.clip(timeout_prob, 0, 1)))
        
        warning_threshold = self.warning_config["warning_threshold_probability"]
        critical_threshold = self.warning_config["critical_threshold_probability"]
        
        will_timeout_soon = any(p > warning_threshold for p in future_timeout_probs)
        steps_to_warning = next(
            (i + 1 for i, p in enumerate(future_timeout_probs) if p > warning_threshold),
            None
        )
        steps_to_critical = next(
            (i + 1 for i, p in enumerate(future_timeout_probs) if p > critical_threshold),
            None
        )
        
        return {
            "horizon_requests": horizon,
            "future_predictions": future_predictions,
            "future_timeout_probabilities": future_timeout_probs,
            "will_timeout_soon": will_timeout_soon,
            "steps_to_warning": steps_to_warning,
            "steps_to_critical": steps_to_critical,
            "max_future_timeout_prob": max(future_timeout_probs),
        }

    def generate_early_warning(
        self,
        current_timeout_prob: float,
        future_risk: Dict,
        trend_info: Dict
    ) -> Dict:
        warning_threshold = self.warning_config["warning_threshold_probability"]
        critical_threshold = self.warning_config["critical_threshold_probability"]
        
        warning_level = "normal"
        warning_type = []
        urgency = "low"
        
        if current_timeout_prob > critical_threshold:
            warning_level = "critical"
            warning_type.append("immediate_timeout_risk")
            urgency = "high"
        elif current_timeout_prob > warning_threshold:
            warning_level = "warning"
            warning_type.append("high_timeout_risk")
            urgency = "medium"
        
        if future_risk.get("will_timeout_soon"):
            if future_risk.get("steps_to_critical"):
                warning_level = "critical" if warning_level == "normal" else warning_level
                warning_type.append("impending_timeout")
                urgency = "high"
            elif future_risk.get("steps_to_warning"):
                warning_level = "warning" if warning_level == "normal" else warning_level
                warning_type.append("approaching_timeout")
                urgency = "medium"
        
        if trend_info.get("has_trend") and trend_info.get("is_rising") and trend_info.get("trend_strength") in ["moderate", "strong"]:
            warning_type.append("rising_response_time_trend")
            if warning_level == "normal":
                warning_level = "advisory"
                urgency = "low"
        
        return {
            "warning_level": warning_level,
            "warning_types": warning_type,
            "urgency": urgency,
            "recommended_actions": self._get_recommendations(warning_level, warning_type),
        }

    def _get_recommendations(self, warning_level: str, warning_types: List[str]) -> List[str]:
        recommendations = []
        
        if "immediate_timeout_risk" in warning_types or "impending_timeout" in warning_types:
            recommendations.append("Consider circuit breaker pattern to prevent cascading failures")
            recommendations.append("Enable rate limiting for affected endpoints")
        
        if "approaching_timeout" in warning_types:
            recommendations.append("Monitor downstream services for performance degradation")
            recommendations.append("Consider scaling up resources")
        
        if "rising_response_time_trend" in warning_types:
            recommendations.append("Investigate recent deployments or configuration changes")
            recommendations.append("Check database query performance and connection pools")
        
        if "high_timeout_risk" in warning_types:
            recommendations.append("Review recent error logs and performance metrics")
            recommendations.append("Consider optimizing slow database queries")
        
        if not recommendations:
            recommendations.append("Continue normal monitoring")
        
        return recommendations

    def get_feature_importance(self) -> Dict[str, float]:
        if self.model is None:
            raise ValueError("Model not trained. Call train() first.")
        
        importance = self.model.get_booster().get_score(importance_type="weight")
        return dict(sorted(importance.items(), key=lambda x: x[1], reverse=True))

    def predict_single(
        self,
        features: pd.DataFrame,
        historical_stats: Dict,
        endpoint: str,
        enable_early_warning: bool = True
    ) -> Dict:
        mean_pred, std_pred = self.predict_with_uncertainty(features)
        
        pred_ms = float(mean_pred[0])
        pred_std = float(std_pred[0])
        
        dynamic_threshold = self.calculate_dynamic_threshold(endpoint, historical_stats)
        
        timeout_prob = float(self.calculate_timeout_probability(
            np.array([pred_ms]), 
            np.array([pred_std]),
            dynamic_threshold
        )[0])
        
        endpoint_avg = historical_stats["endpoint_avg"].get(
            endpoint, 
            historical_stats["global_avg"]
        )
        endpoint_std = historical_stats.get("endpoint_std", {}).get(
            endpoint,
            pred_std
        )
        
        is_anomaly, anomaly_score = self.detect_anomaly(
            pred_ms,
            endpoint_avg,
            endpoint_std
        )
        
        self.prediction_history.append(pred_ms)
        
        early_warning = None
        future_risk = None
        trend_info = None
        
        if enable_early_warning and self.warning_config.get("enabled", True):
            trend_info = self.analyze_trend(list(self.prediction_history))
            future_risk = self.predict_future_risks(
                pred_ms, pred_std, trend_info, dynamic_threshold
            )
            early_warning = self.generate_early_warning(
                timeout_prob, future_risk, trend_info
            )
        
        return {
            "predicted_response_time_ms": round(pred_ms, 2),
            "prediction_std_ms": round(pred_std, 2),
            "dynamic_threshold_p99_ms": round(dynamic_threshold, 2),
            "timeout_probability": round(timeout_prob, 4),
            "is_anomaly": is_anomaly,
            "anomaly_score": round(anomaly_score, 2),
            "warning_level": early_warning["warning_level"] if early_warning else ("normal" if not is_anomaly else "advisory"),
            "confidence_interval": {
                "lower": round(max(0, pred_ms - 1.96 * pred_std), 2),
                "upper": round(pred_ms + 1.96 * pred_std, 2),
                "confidence": 0.95
            },
            "trend_analysis": trend_info,
            "future_risk_prediction": future_risk,
            "early_warning": early_warning,
            "timestamp": datetime.now().isoformat()
        }

    def save(self, path: str = "./models/response_time_model.joblib"):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        joblib.dump({
            "model": self.model,
            "params": self.params,
            "feature_names": self.feature_names,
            "training_metrics": self.training_metrics,
            "warning_config": self.warning_config,
            "dynamic_thresholds": self.dynamic_thresholds,
            "threshold_percentile": self.threshold_percentile,
            "threshold_safety_margin": self.threshold_safety_margin,
            "min_history_for_threshold": self.min_history_for_threshold,
        }, path)

    @classmethod
    def load(cls, path: str = "./models/response_time_model.joblib"):
        data = joblib.load(path)
        predictor = cls(
            params=data["params"],
            warning_config=data.get("warning_config")
        )
        predictor.model = data["model"]
        predictor.feature_names = data["feature_names"]
        predictor.training_metrics = data["training_metrics"]
        predictor.dynamic_thresholds = data.get("dynamic_thresholds", {})
        predictor.threshold_percentile = data.get("threshold_percentile", 99)
        predictor.threshold_safety_margin = data.get("threshold_safety_margin", 1.2)
        predictor.min_history_for_threshold = data.get("min_history_for_threshold", 50)
        return predictor