import numpy as np
import pandas as pd
import shap
import matplotlib.pyplot as plt
import seaborn as sns
import os


class SHAPAnalyzer:
    def __init__(self, classifier):
        self.classifier = classifier
        self.explainer = None
        self.shap_values = None
        self.expected_value = None

    def initialize_explainer(self, X_sample):
        X_scaled = self.classifier.scaler.transform(X_sample)
        self.explainer = shap.TreeExplainer(self.classifier.model)
        self.shap_values = self.explainer.shap_values(X_scaled)
        self.expected_value = self.explainer.expected_value
        return self.shap_values

    def get_feature_importance(self, X_sample, top_n=15):
        if self.shap_values is None:
            self.initialize_explainer(X_sample)
        shap_sum = np.abs(self.shap_values).mean(axis=0)
        importance_df = pd.DataFrame({
            'feature': self.classifier.feature_names,
            'shap_importance': shap_sum
        }).sort_values('shap_importance', ascending=False)
        return importance_df.head(top_n)

    def plot_summary(self, X_sample, save_path=None, max_display=15):
        if self.shap_values is None:
            self.initialize_explainer(X_sample)
        X_scaled = self.classifier.scaler.transform(X_sample)
        plt.figure(figsize=(12, 8))
        shap.summary_plot(
            self.shap_values,
            X_scaled,
            feature_names=self.classifier.feature_names,
            max_display=max_display,
            plot_type='bar',
            show=False
        )
        plt.tight_layout()
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            plt.close()
        else:
            plt.show()

    def plot_beeswarm(self, X_sample, class_idx=0, save_path=None, max_display=15):
        if self.shap_values is None:
            self.initialize_explainer(X_sample)
        X_scaled = self.classifier.scaler.transform(X_sample)
        plt.figure(figsize=(12, 8))
        shap.summary_plot(
            self.shap_values,
            X_scaled,
            feature_names=self.classifier.feature_names,
            max_display=max_display,
            show=False
        )
        plt.tight_layout()
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            plt.close()
        else:
            plt.show()

    def get_single_prediction_explanation(self, X_single):
        if self.shap_values is None:
            self.initialize_explainer(X_single)
        X_scaled = self.classifier.scaler.transform(X_single)
        shap_values_single = self.explainer.shap_values(X_scaled)[0]
        explanation = pd.DataFrame({
            'feature': self.classifier.feature_names,
            'feature_value': X_single.iloc[0].values,
            'shap_value': shap_values_single,
            'abs_shap': np.abs(shap_values_single)
        }).sort_values('abs_shap', ascending=False)
        return explanation

    def plot_waterfall(self, X_single, sample_idx=0, save_path=None, max_display=10):
        if self.explainer is None:
            self.initialize_explainer(X_single)
        X_scaled = self.classifier.scaler.transform(X_single)
        shap_values_single = self.explainer.shap_values(X_scaled)
        plt.figure(figsize=(10, 8))
        shap.waterfall_plot(
            shap.Explanation(
                values=shap_values_single[sample_idx],
                base_values=self.expected_value,
                data=X_scaled[sample_idx],
                feature_names=self.classifier.feature_names
            ),
            max_display=max_display,
            show=False
        )
        plt.tight_layout()
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            plt.close()
        else:
            plt.show()

    def analyze_sleep_stage_contributions(self, X_sample, predictions):
        if self.shap_values is None:
            self.initialize_explainer(X_sample)
        stage_contributions = {}
        for stage_idx, stage_name in enumerate(self.classifier.class_names):
            stage_mask = predictions == stage_idx
            if np.any(stage_mask):
                stage_shap = np.abs(self.shap_values[stage_mask]).mean(axis=0)
                stage_contributions[stage_name] = pd.DataFrame({
                    'feature': self.classifier.feature_names,
                    'importance': stage_shap
                }).sort_values('importance', ascending=False)
        return stage_contributions
