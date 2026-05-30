import os
import sys
import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional
from datetime import datetime
import json
import time
from collections import deque

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils import load_config, setup_logger, ensure_dir


class MetricsTracker:
    def __init__(self, window_size: int = 10000):
        self.window_size = window_size
        self.predictions = deque(maxlen=window_size)
        self.labels = deque(maxlen=window_size)
        self.timestamps = deque(maxlen=window_size)
        self.model_versions = deque(maxlen=window_size)

    def update(self, prediction: float, label: int, model_version: str = "v1"):
        self.predictions.append(prediction)
        self.labels.append(label)
        self.timestamps.append(time.time())
        self.model_versions.append(model_version)

    def get_window_metrics(self) -> Dict[str, float]:
        if len(self.labels) == 0:
            return {"count": 0}

        preds = np.array(self.predictions)
        labels = np.array(self.labels)

        eps = 1e-15
        preds_clipped = np.clip(preds, eps, 1 - eps)

        accuracy = np.mean((preds > 0.5).astype(int) == labels)

        from sklearn.metrics import roc_auc_score, log_loss
        try:
            auc = roc_auc_score(labels, preds) if len(set(labels)) > 1 else 0.5
        except:
            auc = 0.5

        try:
            log_loss_val = log_loss(labels, preds_clipped)
        except:
            log_loss_val = 0.5

        return {
            "count": len(labels),
            "accuracy": accuracy,
            "auc": auc,
            "log_loss": log_loss_val,
            "mean_prediction": np.mean(preds),
            "positive_rate": np.mean(labels),
            "throughput": len(labels) / max((time.time() - self.timestamps[0]), 1) if self.timestamps else 0
        }


class OnlineEvaluator:
    def __init__(self, config_path: str = "configs/config.yaml"):
        self.config = load_config(config_path)
        self.logger = setup_logger("OnlineEvaluator", self.config)
        self.model_metrics = {}
        self.global_tracker = MetricsTracker(window_size=50000)
        self.start_time = datetime.now()
        self.total_predictions = 0

    def register_model(self, model_name: str):
        if model_name not in self.model_metrics:
            self.model_metrics[model_name] = MetricsTracker(window_size=20000)
            self.logger.info(f"Registered model for online evaluation: {model_name}")

    def record_prediction(self, model_name: str, prediction: float, label: Optional[int] = None):
        self.register_model(model_name)

        self.global_tracker.update(prediction, label if label is not None else 0, model_name)
        self.model_metrics[model_name].update(prediction, label if label is not None else 0, model_name)
        self.total_predictions += 1

    def record_label(self, prediction_id: str, label: int):
        pass

    def get_model_metrics(self, model_name: str) -> Dict[str, float]:
        if model_name in self.model_metrics:
            return self.model_metrics[model_name].get_window_metrics()
        return {}

    def get_all_model_metrics(self) -> Dict[str, Dict[str, float]]:
        return {
            model_name: tracker.get_window_metrics()
            for model_name, tracker in self.model_metrics.items()
        }

    def get_global_metrics(self) -> Dict[str, float]:
        metrics = self.global_tracker.get_window_metrics()
        metrics["total_predictions"] = self.total_predictions
        metrics["running_minutes"] = (datetime.now() - self.start_time).total_seconds() / 60
        return metrics

    def compare_models(self, model_names: List[str] = None) -> pd.DataFrame:
        if model_names is None:
            model_names = list(self.model_metrics.keys())

        comparison_data = []
        for model_name in model_names:
            metrics = self.get_model_metrics(model_name)
            metrics["model"] = model_name
            comparison_data.append(metrics)

        return pd.DataFrame(comparison_data)

    def get_best_model(self, metric: str = "auc", higher_is_better: bool = True) -> Tuple[str, float]:
        if not self.model_metrics:
            return None, 0.0

        best_model = None
        best_value = float("-inf") if higher_is_better else float("inf")

        for model_name, tracker in self.model_metrics.items():
            metrics = tracker.get_window_metrics()
            value = metrics.get(metric, 0)

            if higher_is_better:
                if value > best_value:
                    best_value = value
                    best_model = model_name
            else:
                if value < best_value:
                    best_value = value
                    best_model = model_name

        return best_model, best_value

    def save_metrics(self, output_path: str = "data/processed/online_metrics.json"):
        ensure_dir(os.path.dirname(output_path))

        data = {
            "timestamp": datetime.now().isoformat(),
            "global_metrics": self.get_global_metrics(),
            "model_metrics": self.get_all_model_metrics(),
            "best_model": self.get_best_model()
        }

        with open(output_path, "w") as f:
            json.dump(data, f, indent=2)

        self.logger.info(f"Online metrics saved to {output_path}")
        return data

    def print_dashboard(self):
        print("\n" + "="*70)
        print("Online Evaluation Dashboard")
        print("="*70)

        global_metrics = self.get_global_metrics()
        print(f"\nGlobal Metrics:")
        print(f"  Total Predictions: {global_metrics.get('total_predictions', 0):,}")
        print(f"  Running Time: {global_metrics.get('running_minutes', 0):.1f} minutes")
        print(f"  Window AUC: {global_metrics.get('auc', 0):.4f}")
        print(f"  Window Log Loss: {global_metrics.get('log_loss', 0):.4f}")

        print(f"\nModel Comparison:")
        comparison_df = self.compare_models()
        if not comparison_df.empty:
            print(comparison_df.to_string(index=False))

        best_model, best_auc = self.get_best_model("auc")
        print(f"\nBest Model (by AUC): {best_model} ({best_auc:.4f})")
        print("="*70 + "\n")


def main():
    evaluator = OnlineEvaluator()

    np.random.seed(42)
    models = ["deepfm_v1", "mmoe_v1", "deepfm_v2"]

    print("Simulating online predictions...")
    for i in range(5000):
        for model in models:
            pred = np.random.beta(2 + np.random.randint(0, 5), 20)
            label = np.random.binomial(1, pred * 1.5)
            evaluator.record_prediction(model, pred, label)

    evaluator.print_dashboard()


if __name__ == "__main__":
    main()
