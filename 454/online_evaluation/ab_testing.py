import os
import sys
import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional
from datetime import datetime
from scipy import stats
import json

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils import load_config, setup_logger, ensure_dir


class ABTestMetrics:
    def __init__(self):
        self.impressions = 0
        self.clicks = 0
        self.conversions = 0
        self.predictions = []
        self.labels = []
        self.prediction_scores = []

    def update(self, impression: Dict, click: bool = False, 
               conversion: bool = False, prediction_score: float = None):
        self.impressions += 1
        if click:
            self.clicks += 1
        if conversion:
            self.conversions += 1
        if prediction_score is not None:
            self.prediction_scores.append(prediction_score)
            self.labels.append(1 if click else 0)

    def get_ctr(self) -> float:
        return self.clicks / max(self.impressions, 1)

    def get_conversion_rate(self) -> float:
        return self.conversions / max(self.clicks, 1)

    def get_auc(self) -> float:
        if len(self.labels) < 2 or len(set(self.labels)) < 2:
            return 0.5

        from sklearn.metrics import roc_auc_score
        try:
            return roc_auc_score(self.labels, self.prediction_scores)
        except:
            return 0.5

    def get_log_loss(self) -> float:
        if len(self.labels) == 0:
            return 0.0

        from sklearn.metrics import log_loss
        eps = 1e-15
        predictions = np.clip(self.prediction_scores, eps, 1 - eps)
        try:
            return log_loss(self.labels, predictions)
        except:
            return 0.5

    def get_all_metrics(self) -> Dict[str, float]:
        return {
            "impressions": self.impressions,
            "clicks": self.clicks,
            "conversions": self.conversions,
            "ctr": self.get_ctr(),
            "conversion_rate": self.get_conversion_rate(),
            "auc": self.get_auc(),
            "log_loss": self.get_log_loss()
        }


class ABTestRunner:
    def __init__(self, config_path: str = "configs/config.yaml"):
        self.config = load_config(config_path)
        self.logger = setup_logger("ABTestRunner", self.config)
        self.ab_config = self.config["ab_testing"]
        self.metrics = {
            "control": ABTestMetrics(),
            "treatment": ABTestMetrics()
        }
        self.experiment_start_time = None
        self.experiment_id = f"exp_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    def start_experiment(self):
        self.experiment_start_time = datetime.now()
        self.logger.info(f"AB experiment {self.experiment_id} started at {self.experiment_start_time}")

    def assign_group(self, user_id: str) -> str:
        import hashlib
        hash_val = int(hashlib.md5(user_id.encode()).hexdigest()[:8], 16)
        traffic_split = self.ab_config["traffic_split"]
        threshold = traffic_split["control"] * (2**32)
        return "control" if hash_val < threshold else "treatment"

    def record_impression(self, user_id: str, ad_id: str, 
                           prediction_score: float = None, 
                           ab_group: str = None) -> str:
        if ab_group is None:
            ab_group = self.assign_group(user_id)

        self.metrics[ab_group].update(
            {"user_id": user_id, "ad_id": ad_id},
            click=False,
            conversion=False,
            prediction_score=prediction_score
        )

        return ab_group

    def record_click(self, user_id: str, ad_id: str, ab_group: str):
        if ab_group in self.metrics:
            self.metrics[ab_group].clicks += 1
            self.metrics[ab_group].labels[-1] = 1

    def record_conversion(self, user_id: str, ad_id: str, ab_group: str):
        if ab_group in self.metrics:
            self.metrics[ab_group].conversions += 1

    def get_group_metrics(self, group: str) -> Dict[str, float]:
        return self.metrics[group].get_all_metrics()

    def get_all_metrics(self) -> Dict[str, Dict[str, float]]:
        return {
            group: self.get_group_metrics(group)
            for group in ["control", "treatment"]
        }

    def perform_statistical_test(self, metric_name: str = "ctr") -> Dict:
        control_metrics = self.get_group_metrics("control")
        treatment_metrics = self.get_group_metrics("treatment")

        control_value = control_metrics[metric_name]
        treatment_value = treatment_metrics[metric_name]

        control_impressions = control_metrics["impressions"]
        treatment_impressions = treatment_metrics["impressions"]

        min_impressions = self.ab_config.get("min_impressions", 10000)
        if control_impressions < min_impressions or treatment_impressions < min_impressions:
            return {
                "metric": metric_name,
                "control_value": control_value,
                "treatment_value": treatment_value,
                "lift": (treatment_value - control_value) / max(control_value, 1e-10) if control_value != 0 else 0,
                "significant": False,
                "p_value": None,
                "confidence_interval": None,
                "message": f"Insufficient data. Need at least {min_impressions} impressions per group."
            }

        control_successes = int(control_metrics["clicks"])
        treatment_successes = int(treatment_metrics["clicks"])
        control_trials = control_impressions
        treatment_trials = treatment_impressions

        pooled_p = (control_successes + treatment_successes) / (control_trials + treatment_trials)
        se = np.sqrt(pooled_p * (1 - pooled_p) * (1/control_trials + 1/treatment_trials))
        z_score = (treatment_value - control_value) / se
        p_value = 2 * (1 - stats.norm.cdf(abs(z_score)))

        lift = (treatment_value - control_value) / max(control_value, 1e-10)

        ci_low = (treatment_value - control_value) - 1.96 * se
        ci_high = (treatment_value - control_value) + 1.96 * se

        significance_level = self.ab_config.get("significance_level", 0.05)
        significant = p_value < significance_level

        return {
            "metric": metric_name,
            "control_value": control_value,
            "treatment_value": treatment_value,
            "absolute_diff": treatment_value - control_value,
            "lift": lift,
            "z_score": z_score,
            "p_value": p_value,
            "confidence_interval": [ci_low, ci_high],
            "significant": significant,
            "significance_level": significance_level
        }

    def get_experiment_summary(self) -> Dict:
        metrics_list = self.ab_config.get("metrics", ["ctr", "auc", "log_loss"])
        results = {}

        for metric in metrics_list:
            if metric in ["ctr", "conversion_rate"]:
                results[metric] = self.perform_statistical_test(metric)

        summary = {
            "experiment_id": self.experiment_id,
            "start_time": self.experiment_start_time.isoformat() if self.experiment_start_time else None,
            "duration_minutes": (datetime.now() - self.experiment_start_time).total_seconds() / 60 if self.experiment_start_time else 0,
            "metrics": results,
            "group_sizes": {
                "control": self.metrics["control"].impressions,
                "treatment": self.metrics["treatment"].impressions
            }
        }

        return summary

    def save_results(self, output_path: str = "data/processed/ab_test_results.json"):
        ensure_dir(os.path.dirname(output_path))
        summary = self.get_experiment_summary()

        with open(output_path, "w") as f:
            json.dump(summary, f, indent=2, default=str)

        self.logger.info(f"AB test results saved to {output_path}")
        return summary

    def print_summary(self):
        summary = self.get_experiment_summary()
        print("\n" + "="*60)
        print(f"AB Experiment Summary: {summary['experiment_id']}")
        print("="*60)
        print(f"Duration: {summary['duration_minutes']:.2f} minutes")
        print(f"Control impressions: {summary['group_sizes']['control']}")
        print(f"Treatment impressions: {summary['group_sizes']['treatment']}")
        print("\nMetric Results:")

        for metric_name, result in summary["metrics"].items():
            print(f"\n  {metric_name.upper()}:")
            print(f"    Control: {result['control_value']:.4f}")
            print(f"    Treatment: {result['treatment_value']:.4f}")
            print(f"    Lift: {result['lift']*100:.2f}%")
            print(f"    P-value: {result.get('p_value', 'N/A')}")
            print(f"    Significant: {result.get('significant', 'N/A')}")

        print("="*60 + "\n")


def main():
    ab_test = ABTestRunner()
    ab_test.start_experiment()

    np.random.seed(42)
    for i in range(1000):
        user_id = f"user_{i}"
        ad_id = f"ad_{np.random.randint(0, 100)}"
        pred_score = np.random.beta(2, 20)

        group = ab_test.record_impression(user_id, ad_id, pred_score)

        baseline_ctr = 0.05 if group == "control" else 0.07
        if np.random.random() < baseline_ctr:
            ab_test.record_click(user_id, ad_id, group)

    ab_test.print_summary()


if __name__ == "__main__":
    main()
