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

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils import load_config, setup_logger, ensure_dir


class FeatureImportance:
    def __init__(self, config_path: str = "configs/config.yaml"):
        self.config = load_config(config_path)
        self.logger = setup_logger("FeatureImportance", self.config)
        self.importance_scores = {}
        self.feature_names = []

    def set_feature_names(self, feature_names: List[str]):
        self.feature_names = feature_names

    def calculate_permutation_importance(self, model, X: pd.DataFrame, y: np.ndarray,
                                         metric_func, n_repeats: int = 5) -> Dict[str, float]:
        self.logger.info("Calculating permutation importance...")
        self.set_feature_names(X.columns.tolist())

        baseline_score = metric_func(y, model.predict(X) if hasattr(model, 'predict') else model(X))

        importances = np.zeros((len(X.columns), n_repeats))

        for feat_idx, feat_name in enumerate(X.columns):
            for repeat in range(n_repeats):
                X_permuted = X.copy()
                X_permuted[feat_name] = np.random.permutation(X_permuted[feat_name].values)

                if hasattr(model, 'predict'):
                    preds = model.predict(X_permuted)
                else:
                    preds = model(X_permuted)

                permuted_score = metric_func(y, preds)
                importances[feat_idx, repeat] = baseline_score - permuted_score

        mean_importances = np.mean(importances, axis=1)
        std_importances = np.std(importances, axis=1)

        for i, feat_name in enumerate(X.columns):
            self.importance_scores[feat_name] = {
                "importance": mean_importances[i],
                "std": std_importances[i],
                "normalized": mean_importances[i] / max(np.max(np.abs(mean_importances)), 1e-10)
            }

        self.logger.info(f"Permutation importance calculated for {len(X.columns)} features")
        return self.importance_scores

    def calculate_embedding_importance(self, embedding_weights: Dict[str, np.ndarray]) -> Dict[str, float]:
        self.logger.info("Calculating embedding-based importance...")

        for feat_name, weights in embedding_weights.items():
            norm = np.linalg.norm(weights, axis=1).mean()
            self.importance_scores[feat_name] = {
                "importance": norm,
                "std": np.std(np.linalg.norm(weights, axis=1)),
                "normalized": norm
            }

        if self.importance_scores:
            max_importance = max(v["importance"] for v in self.importance_scores.values())
            for feat_name in self.importance_scores:
                self.importance_scores[feat_name]["normalized"] /= max_importance

        return self.importance_scores

    def calculate_gradient_importance(self, model, X: pd.DataFrame, y: np.ndarray) -> Dict[str, float]:
        self.logger.info("Calculating gradient-based importance...")
        self.set_feature_names(X.columns.tolist())

        try:
            import tensorflow as tf

            X_tensor = tf.convert_to_tensor(X.values.astype(np.float32))
            y_tensor = tf.convert_to_tensor(y.astype(np.float32))

            with tf.GradientTape() as tape:
                tape.watch(X_tensor)
                predictions = model(X_tensor)
                loss = tf.keras.losses.binary_crossentropy(y_tensor, predictions)

            gradients = tape.gradient(loss, X_tensor)
            gradient_norms = tf.norm(gradients, axis=0).numpy()

            for i, feat_name in enumerate(X.columns):
                self.importance_scores[feat_name] = {
                    "importance": gradient_norms[i],
                    "std": 0,
                    "normalized": gradient_norms[i] / max(np.max(gradient_norms), 1e-10)
                }

            self.logger.info("Gradient importance calculated successfully")
        except Exception as e:
            self.logger.warning(f"Gradient calculation failed: {e}")

        return self.importance_scores

    def get_top_features(self, n: int = 10, method: str = "importance") -> List[Tuple[str, float]]:
        if not self.importance_scores:
            return []

        sorted_features = sorted(
            self.importance_scores.items(),
            key=lambda x: abs(x[1][method]),
            reverse=True
        )

        return [(feat, scores[method]) for feat, scores in sorted_features[:n]]

    def get_importance_dataframe(self) -> pd.DataFrame:
        if not self.importance_scores:
            return pd.DataFrame()

        data = []
        for feat_name, scores in self.importance_scores.items():
            data.append({
                "feature": feat_name,
                "importance": scores["importance"],
                "std": scores.get("std", 0),
                "normalized_importance": scores["normalized"]
            })

        df = pd.DataFrame(data)
        df = df.sort_values("importance", ascending=False).reset_index(drop=True)
        return df

    def plot_importance(self, n: int = 20, output_path: str = "reports/feature_importance.png"):
        ensure_dir(os.path.dirname(output_path))

        df = self.get_importance_dataframe()
        if df.empty:
            self.logger.warning("No importance scores to plot")
            return

        top_df = df.head(n)

        plt.figure(figsize=(12, 8))
        sns.barplot(x="importance", y="feature", data=top_df, palette="viridis")
        plt.title(f"Top {n} Feature Importance", fontsize=14)
        plt.xlabel("Importance Score")
        plt.ylabel("Feature")
        plt.tight_layout()
        plt.savefig(output_path, dpi=300, bbox_inches="tight")
        plt.close()

        self.logger.info(f"Feature importance plot saved to {output_path}")

    def group_importance_by_domain(self, feature_groups: Dict[str, List[str]]) -> Dict[str, float]:
        grouped_importance = {}

        for group_name, features in feature_groups.items():
            group_scores = []
            for feat in features:
                if feat in self.importance_scores:
                    group_scores.append(self.importance_scores[feat]["importance"])

            if group_scores:
                grouped_importance[group_name] = np.mean(group_scores)

        total = sum(grouped_importance.values())
        if total > 0:
            grouped_importance = {k: v / total for k, v in grouped_importance.items()}

        return grouped_importance

    def get_feature_groups(self) -> Dict[str, List[str]]:
        return {
            "user_profile": ["user_age", "user_gender", "user_level", "user_consumption_level",
                            "user_city_level", "user_device_type", "user_registration_days"],
            "user_behavior": ["user_active_days_7d", "user_click_count_7d", "user_impression_count_7d",
                             "user_ctr_7d", "user_category_preference"],
            "ad_features": ["ad_category", "ad_campaign_id", "ad_advertiser_id", "ad_ctr_history",
                           "ad_click_count_7d", "ad_impression_count_7d", "ad_price",
                           "ad_position", "ad_creative_type", "ad_is_new"],
            "context_features": ["context_hour", "context_day_of_week", "context_is_weekend",
                                "context_traffic_source", "context_network_type",
                                "context_app_version", "context_scene_id", "context_page_id"]
        }

    def save_importance_report(self, output_path: str = "reports/feature_importance_report.md"):
        ensure_dir(os.path.dirname(output_path))

        df = self.get_importance_dataframe()
        if df.empty:
            self.logger.warning("No importance scores to report")
            return

        top_10 = self.get_top_features(10)
        grouped = self.group_importance_by_domain(self.get_feature_groups())

        report_content = f"""# Feature Importance Report
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Executive Summary

This report summarizes the feature importance analysis for the CTR prediction model.

## Top 10 Most Important Features

| Rank | Feature | Importance | Normalized |
|------|---------|------------|------------|
"""

        for i, (feat, imp) in enumerate(top_10, 1):
            norm_imp = self.importance_scores[feat]["normalized"]
            report_content += f"| {i} | {feat} | {imp:.4f} | {norm_imp:.4f} |\n"

        report_content += """
## Feature Group Importance

| Group | Relative Importance |
|-------|---------------------|
"""

        for group, imp in sorted(grouped.items(), key=lambda x: x[1], reverse=True):
            report_content += f"| {group} | {imp*100:.2f}% |\n"

        report_content += f"""
## Full Feature List

Total features analyzed: {len(df)}

### Distribution Stats
- Mean importance: {df['importance'].mean():.4f}
- Std importance: {df['importance'].std():.4f}
- Max importance: {df['importance'].max():.4f}
- Min importance: {df['importance'].min():.4f}
"""

        with open(output_path, "w") as f:
            f.write(report_content)

        self.logger.info(f"Feature importance report saved to {output_path}")


def main():
    print("Feature Importance Module")
    print("Use this module to analyze and visualize feature importance")


if __name__ == "__main__":
    main()
