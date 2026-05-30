import os
import sys
import numpy as np
import pandas as pd
from typing import Dict, List, Tuple
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime
import json

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils import load_config, setup_logger, ensure_dir


class ModelComparator:
    def __init__(self, config_path: str = "configs/config.yaml"):
        self.config = load_config(config_path)
        self.logger = setup_logger("ModelComparator", self.config)
        self.model_results = {}
        self.baseline_model = None

    def add_model_result(self, model_name: str, metrics: Dict[str, float], 
                        is_baseline: bool = False):
        self.model_results[model_name] = metrics.copy()
        if is_baseline:
            self.baseline_model = model_name
        self.logger.info(f"Added results for model: {model_name}")

    def add_model_from_history(self, model_name: str, history: Dict, is_baseline: bool = False):
        metrics = {}
        for key, values in history.items():
            if not key.startswith("val_"):
                metrics[f"final_{key}"] = values[-1] if isinstance(values, list) else values

        self.add_model_result(model_name, metrics, is_baseline)

    def get_model_metric(self, model_name: str, metric_name: str) -> float:
        if model_name not in self.model_results:
            return None
        return self.model_results[model_name].get(metric_name)

    def compare_metric(self, metric_name: str, higher_is_better: bool = True) -> pd.DataFrame:
        data = []
        for model_name, metrics in self.model_results.items():
            value = metrics.get(metric_name)
            baseline_value = None
            lift = None

            if self.baseline_model and self.baseline_model in self.model_results:
                baseline_value = self.model_results[self.baseline_model].get(metric_name)
                if baseline_value and baseline_value != 0:
                    lift = (value - baseline_value) / baseline_value * 100

            data.append({
                "model": model_name,
                metric_name: value,
                "baseline_value": baseline_value,
                "lift_pct": lift,
                "is_baseline": model_name == self.baseline_model
            })

        df = pd.DataFrame(data)
        df = df.sort_values(metric_name, ascending=not higher_is_better).reset_index(drop=True)
        return df

    def get_comparison_dataframe(self) -> pd.DataFrame:
        all_metrics = set()
        for metrics in self.model_results.values():
            all_metrics.update(metrics.keys())

        data = []
        for model_name, metrics in self.model_results.items():
            row = {"model": model_name}
            for metric in all_metrics:
                row[metric] = metrics.get(metric)
            data.append(row)

        return pd.DataFrame(data)

    def get_best_model(self, primary_metric: str = "final_auc", 
                       secondary_metrics: List[str] = None,
                       higher_is_better: bool = True) -> Tuple[str, Dict]:
        if not self.model_results:
            return None, {}

        comparison_df = self.compare_metric(primary_metric, higher_is_better)
        best_model_row = comparison_df.iloc[0]
        best_model_name = best_model_row["model"]

        result = {
            "model": best_model_name,
            primary_metric: best_model_row[primary_metric],
            "all_metrics": self.model_results[best_model_name]
        }

        if secondary_metrics:
            result["secondary_metrics"] = {
                metric: self.model_results[best_model_name].get(metric)
                for metric in secondary_metrics
            }

        return best_model_name, result

    def plot_metric_comparison(self, metric_name: str, output_path: str,
                               higher_is_better: bool = True):
        ensure_dir(os.path.dirname(output_path))

        comparison_df = self.compare_metric(metric_name, higher_is_better)

        plt.figure(figsize=(12, 6))
        colors = ["#ff6b6b" if m == self.baseline_model else "#4ecdc4" 
                  for m in comparison_df["model"]]

        sns.barplot(x="model", y=metric_name, data=comparison_df, palette=colors)
        plt.title(f"Model Comparison - {metric_name}", fontsize=14)
        plt.xlabel("Model")
        plt.ylabel(metric_name)
        plt.xticks(rotation=45)

        for i, row in comparison_df.iterrows():
            if row["lift_pct"] is not None and not row["is_baseline"]:
                plt.text(i, row[metric_name], 
                        f"{row['lift_pct']:+.1f}%", 
                        ha="center", va="bottom")

        plt.tight_layout()
        plt.savefig(output_path, dpi=300, bbox_inches="tight")
        plt.close()

        self.logger.info(f"Metric comparison plot saved to {output_path}")

    def plot_training_curves(self, histories: Dict[str, Dict], metric_name: str = "auc",
                              output_path: str = "reports/training_curves.png"):
        ensure_dir(os.path.dirname(output_path))

        plt.figure(figsize=(12, 6))

        for model_name, history in histories.items():
            if metric_name in history:
                plt.plot(history[metric_name], label=f"{model_name} (train)", linewidth=2)
            val_metric = f"val_{metric_name}"
            if val_metric in history:
                plt.plot(history[val_metric], label=f"{model_name} (val)", linewidth=2, linestyle="--")

        plt.title(f"Training Curves - {metric_name}", fontsize=14)
        plt.xlabel("Epoch")
        plt.ylabel(metric_name)
        plt.legend()
        plt.grid(True, alpha=0.3)
        plt.tight_layout()
        plt.savefig(output_path, dpi=300, bbox_inches="tight")
        plt.close()

        self.logger.info(f"Training curves plot saved to {output_path}")

    def generate_comparison_report(self, output_path: str = "reports/model_comparison_report.md"):
        ensure_dir(os.path.dirname(output_path))

        comparison_df = self.get_comparison_dataframe()
        best_model, best_result = self.get_best_model()

        report_content = f"""# Model Comparison Report
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Executive Summary

**Best Model:** {best_model}

### Best Model Metrics
"""

        for metric, value in best_result.get("all_metrics", {}).items():
            report_content += f"- **{metric}**: {value}\n"

        report_content += f"""

## Model Comparison Table

{comparison_df.to_markdown(index=False)}

## Performance Analysis

"""

        if self.baseline_model:
            report_content += f"""### Baseline Model: {self.baseline_model}

| Model | AUC Lift | Log Loss Change |
|-------|----------|-----------------|
"""
            for model_name in self.model_results:
                if model_name != self.baseline_model:
                    auc_lift = self._calculate_lift(model_name, "final_auc", True)
                    log_loss_change = self._calculate_lift(model_name, "final_log_loss", False)
                    report_content += f"| {model_name} | {auc_lift:+.2f}% | {log_loss_change:+.4f} |\n"

        report_content += """
## Recommendations

Based on the comparison analysis:
1. The best performing model should be considered for production deployment
2. Further A/B testing is recommended to validate online performance
3. Monitor model drift and retrain periodically
"""

        with open(output_path, "w") as f:
            f.write(report_content)

        self.logger.info(f"Model comparison report saved to {output_path}")

    def _calculate_lift(self, model_name: str, metric_name: str, higher_is_better: bool) -> float:
        if not self.baseline_model or self.baseline_model not in self.model_results:
            return 0

        model_value = self.model_results[model_name].get(metric_name, 0)
        baseline_value = self.model_results[self.baseline_model].get(metric_name, 0)

        if baseline_value == 0:
            return 0

        if higher_is_better:
            return (model_value - baseline_value) / baseline_value * 100
        else:
            return (baseline_value - model_value) / baseline_value * 100

    def save_results(self, output_path: str = "data/processed/model_comparison_results.json"):
        ensure_dir(os.path.dirname(output_path))

        data = {
            "timestamp": datetime.now().isoformat(),
            "baseline_model": self.baseline_model,
            "model_results": self.model_results,
            "best_model": self.get_best_model()[0]
        }

        with open(output_path, "w") as f:
            json.dump(data, f, indent=2, default=str)

        self.logger.info(f"Model comparison results saved to {output_path}")


def main():
    print("Model Comparison Module")
    print("Use this module to compare model performance")


if __name__ == "__main__":
    main()
