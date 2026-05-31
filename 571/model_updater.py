import numpy as np
import pandas as pd
from datetime import datetime
from typing import Dict, Optional, List, Tuple
from collections import deque
import os
import json
import threading
import logging

logger = logging.getLogger(__name__)


class ModelUpdater:
    def __init__(
        self,
        predictor=None,
        feature_engineer=None,
        redis_cache=None,
        config: dict = None
    ):
        self.predictor = predictor
        self.feature_engineer = feature_engineer
        self.redis_cache = redis_cache
        self.config = config or {
            "min_new_samples": 100,
            "max_new_samples": 5000,
            "update_interval_seconds": 3600,
            "performance_degradation_threshold": 0.05,
            "validation_split": 0.2,
            "rollback_enabled": True,
            "max_model_versions": 5,
            "incremental_learning_rate": 0.3,
            "drift_detection_enabled": True,
            "drift_window_size": 200,
            "drift_significance": 0.05,
        }

        self.new_data_buffer = deque(maxlen=self.config["max_new_samples"])
        self.model_version = 0
        self.model_history = deque(maxlen=self.config["max_model_versions"])
        self.update_count = 0
        self.last_update_time = None
        self.last_validation_metrics = None
        self.is_updating = False
        self._auto_update_thread = None
        self._stop_event = threading.Event()

        self._load_state()

    def _load_state(self):
        state_path = "./models/updater_state.json"
        if os.path.exists(state_path):
            try:
                with open(state_path, "r") as f:
                    state = json.load(f)
                self.model_version = state.get("version", 0)
                self.update_count = state.get("update_count", 0)
                self.last_update_time = state.get("last_update_time")
                self.last_validation_metrics = state.get("last_validation_metrics")
            except Exception as e:
                logger.warning(f"Could not load updater state: {e}")

    def _save_state(self):
        state_path = "./models/updater_state.json"
        os.makedirs(os.path.dirname(state_path), exist_ok=True)
        state = {
            "version": self.model_version,
            "update_count": self.update_count,
            "last_update_time": self.last_update_time,
            "last_validation_metrics": self.last_validation_metrics,
        }
        with open(state_path, "w") as f:
            json.dump(state, f, indent=2, default=str)

    def add_data_point(
        self,
        request_data: Dict,
        actual_response_time_ms: float
    ):
        data_point = {
            **request_data,
            "response_time_ms": actual_response_time_ms,
            "recorded_at": datetime.now().isoformat()
        }
        self.new_data_buffer.append(data_point)

        if self.redis_cache:
            self.redis_cache.store_request(request_data, actual_response_time_ms)

    def should_update(self) -> Tuple[bool, str]:
        buffer_size = len(self.new_data_buffer)
        min_samples = self.config["min_new_samples"]

        if buffer_size < min_samples:
            return False, f"Insufficient new data: {buffer_size}/{min_samples}"

        if self.is_updating:
            return False, "Update already in progress"

        if self.config["drift_detection_enabled"] and self._detect_concept_drift():
            return True, "Concept drift detected - urgent retraining needed"

        if self.last_update_time:
            time_since_update = (datetime.now() - datetime.fromisoformat(self.last_update_time)).total_seconds()
            if time_since_update >= self.config["update_interval_seconds"]:
                return True, f"Scheduled update ({time_since_update:.0f}s since last update)"
        else:
            return True, "First update"

        if self._check_performance_degradation():
            return True, "Performance degradation detected"

        return False, "No update needed"

    def _detect_concept_drift(self) -> bool:
        if len(self.new_data_buffer) < self.config["drift_window_size"]:
            return False

        recent_data = list(self.new_data_buffer)[-self.config["drift_window_size"]:]
        actual_times = [d["response_time_ms"] for d in recent_data]

        if self.predictor and self.predictor.training_metrics:
            training_mean = self.predictor.training_metrics.get("train", {}).get("mae", 0)
            recent_mean = np.mean(actual_times)

            if self.last_validation_metrics:
                baseline_mean = self.last_validation_metrics.get("mean_actual", recent_mean)
            else:
                baseline_mean = training_mean

            if baseline_mean > 0:
                relative_change = abs(recent_mean - baseline_mean) / (baseline_mean + 1e-8)
                if relative_change > self.config["drift_significance"]:
                    logger.info(f"Concept drift detected: {relative_change:.2%} change in mean response time")
                    return True

        return False

    def _check_performance_degradation(self) -> bool:
        if not self.last_validation_metrics or not self.predictor.training_metrics:
            return False

        current_rmse = self.predictor.training_metrics.get("test", {}).get("rmse", float("inf"))
        baseline_rmse = self.last_validation_metrics.get("rmse", current_rmse)

        if baseline_rmse > 0:
            degradation = (current_rmse - baseline_rmse) / baseline_rmse
            if degradation > self.config["performance_degradation_threshold"]:
                logger.info(f"Performance degradation: {degradation:.2%} RMSE increase")
                return True

        return False

    def update_model(
        self,
        base_data_path: str = "./data/api_requests.csv",
        force: bool = False
    ) -> Dict:
        if self.is_updating:
            return {"status": "error", "message": "Update already in progress"}

        should_update, reason = (True, "forced") if force else self.should_update()
        if not should_update:
            return {"status": "skipped", "message": reason}

        self.is_updating = True
        start_time = datetime.now()

        try:
            self._save_current_model_version()

            new_data = pd.DataFrame(list(self.new_data_buffer))
            if "timestamp" in new_data.columns:
                new_data["timestamp"] = pd.to_datetime(new_data["timestamp"])

            base_df = None
            if os.path.exists(base_data_path):
                try:
                    base_df = pd.read_csv(base_data_path, parse_dates=["timestamp"])
                except Exception:
                    base_df = None

            if base_df is not None and len(base_df) > 0:
                lr = self.config["incremental_learning_rate"]
                base_sample_size = int(len(new_data) * (1 - lr) / lr) if lr < 1 else len(base_df)
                base_sample = base_df.sample(n=min(base_sample_size, len(base_df)), random_state=42)
                combined_df = pd.concat([base_sample, new_data], ignore_index=True)
            else:
                combined_df = new_data

            combined_df = combined_df.sort_values("timestamp").reset_index(drop=True)

            df_features = self.feature_engineer.fit_transform(combined_df, fit_encoders=True)
            X, y = self.feature_engineer.prepare_for_training(df_features)

            from sklearn.model_selection import train_test_split
            from sklearn.metrics import mean_squared_error, r2_score

            X_train, X_test, y_train, y_test = train_test_split(
                X, y, test_size=self.config["validation_split"], random_state=42
            )

            old_metrics = None
            if self.predictor.model is not None:
                old_metrics = dict(self.predictor.training_metrics)

            new_metrics = self.predictor.train(X, y)

            validation_result = self._validate_update(new_metrics, old_metrics)

            if not validation_result["is_acceptable"] and self.config["rollback_enabled"]:
                self._rollback_model()
                self.is_updating = False
                return {
                    "status": "rolled_back",
                    "reason": validation_result["reason"],
                    "new_metrics": new_metrics,
                    "old_metrics": old_metrics,
                }

            self.model_version += 1
            self.update_count += 1
            self.last_update_time = datetime.now().isoformat()
            self.last_validation_metrics = {
                "rmse": new_metrics["test"]["rmse"],
                "r2": new_metrics["test"]["r2"],
                "mae": new_metrics["test"]["mae"],
                "mean_actual": float(y_test.mean()),
                "samples": len(combined_df),
            }

            self.feature_engineer.save("./models/feature_engineer.joblib")
            self.predictor.save("./models/response_time_model.joblib")
            self._save_state()

            self.new_data_buffer.clear()

            elapsed = (datetime.now() - start_time).total_seconds()

            return {
                "status": "success",
                "version": self.model_version,
                "reason": reason,
                "new_samples": len(new_data),
                "total_samples": len(combined_df),
                "metrics": new_metrics,
                "validation": validation_result,
                "elapsed_seconds": round(elapsed, 2),
                "timestamp": datetime.now().isoformat()
            }

        except Exception as e:
            logger.error(f"Model update failed: {e}")
            if self.config["rollback_enabled"]:
                self._rollback_model()
            return {"status": "error", "message": str(e)}

        finally:
            self.is_updating = False

    def _validate_update(self, new_metrics: Dict, old_metrics: Optional[Dict]) -> Dict:
        if old_metrics is None:
            return {"is_acceptable": True, "reason": "first_training"}

        new_rmse = new_metrics["test"]["rmse"]
        old_rmse = old_metrics.get("test", {}).get("rmse", float("inf"))
        new_r2 = new_metrics["test"]["r2"]
        old_r2 = old_metrics.get("test", {}).get("r2", 0)

        rmse_change = (new_rmse - old_rmse) / (old_rmse + 1e-8)
        r2_change = new_r2 - old_r2

        is_acceptable = True
        reasons = []

        if rmse_change > self.config["performance_degradation_threshold"]:
            is_acceptable = False
            reasons.append(f"RMSE increased by {rmse_change:.2%}")

        if r2_change < -0.05:
            is_acceptable = False
            reasons.append(f"R2 decreased by {abs(r2_change):.4f}")

        if new_r2 < 0.5:
            is_acceptable = False
            reasons.append(f"R2 too low: {new_r2:.4f}")

        return {
            "is_acceptable": is_acceptable,
            "reason": "; ".join(reasons) if reasons else "performance_acceptable",
            "rmse_change_percent": round(rmse_change * 100, 2),
            "r2_change": round(r2_change, 4),
            "new_rmse": round(new_rmse, 2),
            "old_rmse": round(old_rmse, 2),
            "new_r2": round(new_r2, 4),
            "old_r2": round(old_r2, 4),
        }

    def _save_current_model_version(self):
        version_path = f"./models/versions/v{self.model_version}"
        os.makedirs(version_path, exist_ok=True)

        if os.path.exists("./models/response_time_model.joblib"):
            import shutil
            shutil.copy2(
                "./models/response_time_model.joblib",
                f"{version_path}/response_time_model.joblib"
            )
        if os.path.exists("./models/feature_engineer.joblib"):
            import shutil
            shutil.copy2(
                "./models/feature_engineer.joblib",
                f"{version_path}/feature_engineer.joblib"
            )

        self.model_history.append({
            "version": self.model_version,
            "timestamp": datetime.now().isoformat(),
            "metrics": dict(self.predictor.training_metrics) if self.predictor.training_metrics else {},
        })

    def _rollback_model(self):
        if not self.model_history:
            logger.warning("No model history available for rollback")
            return

        last_version_info = self.model_history[-1]
        version = last_version_info["version"]
        version_path = f"./models/versions/v{version}"

        try:
            from predictor import ResponseTimePredictor
            from feature_engineer import FeatureEngineer

            model_path = f"{version_path}/response_time_model.joblib"
            fe_path = f"{version_path}/feature_engineer.joblib"

            if os.path.exists(model_path):
                self.predictor = ResponseTimePredictor.load(model_path)
            if os.path.exists(fe_path):
                self.feature_engineer = FeatureEngineer.load(fe_path)

            logger.info(f"Rolled back to model version {version}")
        except Exception as e:
            logger.error(f"Rollback failed: {e}")

    def start_auto_update(self):
        if self._auto_update_thread and self._auto_update_thread.is_alive():
            return {"status": "already_running"}

        self._stop_event.clear()
        self._auto_update_thread = threading.Thread(
            target=self._auto_update_loop,
            daemon=True
        )
        self._auto_update_thread.start()
        return {"status": "started", "interval_seconds": self.config["update_interval_seconds"]}

    def stop_auto_update(self):
        self._stop_event.set()
        if self._auto_update_thread:
            self._auto_update_thread.join(timeout=10)
        return {"status": "stopped"}

    def _auto_update_loop(self):
        while not self._stop_event.is_set():
            self._stop_event.wait(timeout=self.config["update_interval_seconds"])
            if self._stop_event.is_set():
                break

            try:
                should, reason = self.should_update()
                if should:
                    logger.info(f"Auto-update triggered: {reason}")
                    result = self.update_model()
                    logger.info(f"Auto-update result: {result['status']}")
            except Exception as e:
                logger.error(f"Auto-update error: {e}")

    def get_status(self) -> Dict:
        return {
            "model_version": self.model_version,
            "update_count": self.update_count,
            "last_update_time": self.last_update_time,
            "buffer_size": len(self.new_data_buffer),
            "min_samples_for_update": self.config["min_new_samples"],
            "is_updating": self.is_updating,
            "auto_update_running": self._auto_update_thread is not None and self._auto_update_thread.is_alive(),
            "last_validation_metrics": self.last_validation_metrics,
            "model_versions_available": len(self.model_history),
        }