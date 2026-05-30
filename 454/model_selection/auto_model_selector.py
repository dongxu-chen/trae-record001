import os
import sys
import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional
from datetime import datetime
import json
import pickle

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils import load_config, setup_logger, ensure_dir
from model_comparison import ModelComparator


class AutoModelSelector:
    def __init__(self, config_path: str = "configs/config.yaml"):
        self.config = load_config(config_path)
        self.logger = setup_logger("AutoModelSelector", self.config)
        self.selector_config = self.config["model_selection"]
        self.comparator = ModelComparator(config_path)
        self.current_deployed_model = None
        self.selection_history = []
        self.thresholds = self.selector_config.get("threshold", {})
        self.auto_deploy = self.selector_config.get("auto_deploy", False)

    def evaluate_model(self, model_name: str, test_metrics: Dict[str, float], 
                        online_metrics: Optional[Dict[str, float]] = None) -> Dict:
        self.comparator.add_model_result(model_name, test_metrics)

        evaluation = {
            "model_name": model_name,
            "test_metrics": test_metrics,
            "online_metrics": online_metrics,
            "meets_thresholds": True,
            "threshold_checks": {},
            "score": 0.0,
            "recommended": False
        }

        for metric, threshold in self.thresholds.items():
            actual_value = test_metrics.get(metric)
            if actual_value is not None:
                if metric in ["auc", "accuracy", "precision", "recall"]:
                    meets = actual_value >= threshold
                else:
                    meets = actual_value <= threshold

                evaluation["threshold_checks"][metric] = {
                    "value": actual_value,
                    "threshold": threshold,
                    "meets": meets
                }
                if not meets:
                    evaluation["meets_thresholds"] = False

        evaluation["score"] = self._calculate_composite_score(test_metrics, online_metrics)
        evaluation["timestamp"] = datetime.now().isoformat()

        self.logger.info(f"Evaluated model {model_name}: score={evaluation['score']:.4f}, meets_thresholds={evaluation['meets_thresholds']}")
        return evaluation

    def _calculate_composite_score(self, test_metrics: Dict[str, float], 
                                    online_metrics: Optional[Dict[str, float]]) -> float:
        primary_metric = self.selector_config["metrics"]["primary"]
        secondary_metrics = self.selector_config["metrics"].get("secondary", [])

        score = 0.0
        weights = {}

        weights[primary_metric] = 0.5
        secondary_weight = 0.5 / max(len(secondary_metrics), 1)
        for metric in secondary_metrics:
            weights[metric] = secondary_weight

        for metric, weight in weights.items():
            value = test_metrics.get(metric)
            if value is not None:
                if metric in ["auc", "accuracy", "precision", "recall"]:
                    score += value * weight
                else:
                    score += (1 / max(value, 0.001)) * weight

        if online_metrics:
            online_auc = online_metrics.get("auc", 0)
            score += online_auc * 0.2
            score *= 0.8

        return score

    def select_best_model(self, model_evaluations: List[Dict]) -> Dict:
        if not model_evaluations:
            return {"selected": None, "reason": "No models to evaluate"}

        valid_models = [m for m in model_evaluations if m["meets_thresholds"]]

        if not valid_models:
            best_model = max(model_evaluations, key=lambda x: x["score"])
            return {
                "selected": best_model["model_name"],
                "reason": "No models meet thresholds - selected best available",
                "meets_thresholds": False,
                "all_below_threshold": True
            }

        best_model = max(valid_models, key=lambda x: x["score"])
        best_model["recommended"] = True

        result = {
            "selected": best_model["model_name"],
            "score": best_model["score"],
            "meets_thresholds": True,
            "all_below_threshold": False,
            "test_metrics": best_model["test_metrics"],
            "reason": "Model meets all thresholds and has highest composite score"
        }

        self.selection_history.append({
            "timestamp": datetime.now().isoformat(),
            "selection": result,
            "candidates": [m["model_name"] for m in model_evaluations]
        })

        self.logger.info(f"Selected best model: {result['selected']} with score {result['score']:.4f}")
        return result

    def compare_with_baseline(self, candidate_model: str, baseline_model: str,
                               test_metrics_candidate: Dict, 
                               test_metrics_baseline: Dict) -> Dict:
        self.comparator.add_model_result(baseline_model, test_metrics_baseline, is_baseline=True)
        self.comparator.add_model_result(candidate_model, test_metrics_candidate)

        comparison = {
            "candidate": candidate_model,
            "baseline": baseline_model,
            "improvements": {},
            "regressions": {},
            "overall_recommendation": "hold"
        }

        primary_metric = self.selector_config["metrics"]["primary"]
        candidate_primary = test_metrics_candidate.get(primary_metric, 0)
        baseline_primary = test_metrics_baseline.get(primary_metric, 0)

        if primary_metric in ["auc", "accuracy", "precision", "recall"]:
            lift = (candidate_primary - baseline_primary) / max(baseline_primary, 1e-10)
        else:
            lift = (baseline_primary - candidate_primary) / max(baseline_primary, 1e-10)

        comparison["primary_metric_lift"] = lift

        if lift > 0.02:
            comparison["overall_recommendation"] = "deploy"
        elif lift > 0:
            comparison["overall_recommendation"] = "monitor"
        else:
            comparison["overall_recommendation"] = "reject"

        for metric in self.selector_config["metrics"].get("secondary", []):
            candidate_val = test_metrics_candidate.get(metric)
            baseline_val = test_metrics_baseline.get(metric)

            if candidate_val is not None and baseline_val is not None:
                if metric in ["auc", "accuracy", "precision", "recall"]:
                    diff = candidate_val - baseline_val
                else:
                    diff = baseline_val - candidate_val

                if diff > 0:
                    comparison["improvements"][metric] = diff
                else:
                    comparison["regressions"][metric] = diff

        self.logger.info(f"Comparison: {candidate_model} vs {baseline_model} - recommendation: {comparison['overall_recommendation']}")
        return comparison

    def auto_select_and_deploy(self, model_candidates: List[Dict], 
                                baseline_model: Optional[str] = None) -> Dict:
        evaluations = []
        for candidate in model_candidates:
            eval_result = self.evaluate_model(
                candidate["model_name"],
                candidate["test_metrics"],
                candidate.get("online_metrics")
            )
            evaluations.append(eval_result)

        selection = self.select_best_model(evaluations)

        if baseline_model:
            baseline_metrics = None
            for candidate in model_candidates:
                if candidate["model_name"] == baseline_model:
                    baseline_metrics = candidate["test_metrics"]
                    break

            if baseline_metrics and selection["selected"] != baseline_model:
                selected_metrics = selection.get("test_metrics", {})
                comparison = self.compare_with_baseline(
                    selection["selected"],
                    baseline_model,
                    selected_metrics,
                    baseline_metrics
                )
                selection["baseline_comparison"] = comparison

                if comparison["overall_recommendation"] == "deploy" and self.auto_deploy:
                    selection["auto_deployed"] = True
                    self.current_deployed_model = selection["selected"]
                    self.logger.info(f"Auto-deployed model: {selection['selected']}")
                else:
                    selection["auto_deployed"] = False
        elif self.auto_deploy and selection["meets_thresholds"]:
            selection["auto_deployed"] = True
            self.current_deployed_model = selection["selected"]

        self.save_selection_history()
        return selection

    def get_deployment_recommendation(self, model_name: str, 
                                        test_metrics: Dict, 
                                        online_metrics: Optional[Dict] = None) -> Dict:
        evaluation = self.evaluate_model(model_name, test_metrics, online_metrics)

        recommendation = {
            "model_name": model_name,
            "meets_requirements": evaluation["meets_thresholds"],
            "recommendation": "reject",
            "confidence": "low",
            "actions": []
        }

        if not evaluation["meets_thresholds"]:
            recommendation["actions"].append("Model does not meet minimum thresholds")
            recommendation["actions"].append("Review failed metrics: " + 
                ", ".join([k for k, v in evaluation["threshold_checks"].items() if not v["meets"]]))
        else:
            score = evaluation["score"]
            if score >= 0.8:
                recommendation["recommendation"] = "deploy"
                recommendation["confidence"] = "high"
                recommendation["actions"].append("Ready for production deployment")
            elif score >= 0.6:
                recommendation["recommendation"] = "ab_test"
                recommendation["confidence"] = "medium"
                recommendation["actions"].append("Recommended for A/B testing")
            else:
                recommendation["recommendation"] = "further_testing"
                recommendation["confidence"] = "low"
                recommendation["actions"].append("More offline testing recommended")

        return recommendation

    def save_selection_history(self, output_path: str = "data/processed/selection_history.json"):
        ensure_dir(os.path.dirname(output_path))
        with open(output_path, "w") as f:
            json.dump(self.selection_history, f, indent=2, default=str)
        self.logger.info(f"Selection history saved to {output_path}")

    def load_selection_history(self, input_path: str = "data/processed/selection_history.json"):
        if os.path.exists(input_path):
            with open(input_path, "r") as f:
                self.selection_history = json.load(f)
            self.logger.info(f"Loaded {len(self.selection_history)} selection records")


def main():
    print("Auto Model Selector Module")
    print("Use this module to automatically select and deploy the best model")


if __name__ == "__main__":
    main()
