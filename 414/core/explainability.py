import logging
from typing import Dict, List, Optional, Tuple

import numpy as np

from models.ensemble import FraudDetectionEnsemble
from models.isolation_forest import IsolationForestModel

logger = logging.getLogger(__name__)

FEATURE_NAMES = [
    "amount", "txn_count_24h", "txn_count_7d", "avg_amount_30d",
    "customer_age", "customer_tenure", "latitude", "longitude",
    "is_international", "is_recurring", "is_credit_card", "channel_online",
    "channel_mobile", "timestamp_norm", "gender_male", "merchant_hash",
    "ip_hash", "city_hash", "income_high", "income_medium",
    "income_low", "device_mobile", "category_high_risk", "category_very_high_risk",
    "currency_foreign", "amount_ratio", "amount_gt_10k", "amount_gt_5k",
    "velocity_24h", "velocity_7d",
]


class ExplainabilityEngine:
    def __init__(self, ensemble: Optional[FraudDetectionEnsemble] = None):
        self.ensemble = ensemble
        self._feature_names = FEATURE_NAMES
        self._baseline_values: Dict[str, float] = {}

    def set_baseline(self, features: np.ndarray):
        if features.ndim == 2:
            self._baseline_values = {
                name: float(np.mean(features[:, i]))
                for i, name in enumerate(self._feature_names)
                if i < features.shape[1]
            }
        logger.info("Baseline values computed from %d features", len(self._baseline_values))

    def compute_feature_contribution(
        self,
        transaction_features: np.ndarray,
        customer_id: Optional[str] = None,
    ) -> Dict:
        if self.ensemble is None:
            return {"error": "No ensemble model configured"}
        if transaction_features.ndim == 1:
            transaction_features = transaction_features.reshape(1, -1)
        base_result = self.ensemble.score_transaction(
            transaction_features.copy(), customer_id
        )
        base_prob = base_result["combined_probability"]
        contributions: List[Dict] = []
        n_features = min(transaction_features.shape[1], len(self._feature_names))
        for i in range(n_features):
            perturbed = transaction_features.copy()
            baseline = self._baseline_values.get(self._feature_names[i], 0.0)
            original_val = float(perturbed[0, i])
            perturbed[0, i] = baseline
            perturbed_result = self.ensemble.score_transaction(perturbed, customer_id)
            perturbed_prob = perturbed_result["combined_probability"]
            contribution = base_prob - perturbed_prob
            contributions.append({
                "feature_index": i,
                "feature_name": self._feature_names[i] if i < len(self._feature_names) else f"feature_{i}",
                "original_value": original_val,
                "baseline_value": baseline,
                "contribution": float(contribution),
                "absolute_contribution": float(abs(contribution)),
                "direction": "increase_risk" if contribution > 0 else "decrease_risk",
            })
        contributions.sort(key=lambda x: x["absolute_contribution"], reverse=True)
        total_abs_contrib = sum(c["absolute_contribution"] for c in contributions)
        if total_abs_contrib > 0:
            for c in contributions:
                c["relative_importance"] = c["absolute_contribution"] / total_abs_contrib
        else:
            for c in contributions:
                c["relative_importance"] = 0.0
        top_drivers = [
            {
                "feature": c["feature_name"],
                "contribution": c["contribution"],
                "importance": c["relative_importance"],
            }
            for c in contributions[:5]
        ]
        return {
            "customer_id": customer_id,
            "base_probability": base_prob,
            "total_features_analyzed": n_features,
            "top_risk_drivers": top_drivers,
            "top_risk_mitigators": [
                {
                    "feature": c["feature_name"],
                    "contribution": c["contribution"],
                    "importance": c["relative_importance"],
                }
                for c in contributions[-5:] if c["contribution"] < 0
            ],
            "all_contributions": contributions,
            "explanation_text": self._generate_explanation(base_prob, top_drivers),
        }

    def _generate_explanation(self, probability: float, top_drivers: List[Dict]) -> str:
        risk_level = "高风险" if probability >= 0.85 else ("中等风险" if probability >= 0.60 else "低风险")
        if not top_drivers:
            return f"该交易被评估为{risk_level}（概率={probability:.2%}）。"
        driver_names = "、".join(
            f"{d['feature']}({d['contribution']:+.3f})" for d in top_drivers[:3]
        )
        return (
            f"该交易被评估为{risk_level}（概率={probability:.2%}）。"
            f"主要风险因素: {driver_names}。"
        )

    def compute_isolation_forest_importance(self, if_model: IsolationForestModel) -> Dict:
        if if_model.model is None:
            return {"error": "IsolationForest model not trained"}
        n_features = if_model.model.n_features_in_
        importances = np.zeros(n_features)
        for estimator in if_model.model.estimators_:
            tree = estimator.tree_
            node_features = tree.feature
            for node_idx in range(tree.node_count):
                if node_features[node_idx] >= 0:
                    importances[node_features[node_idx]] += 1
        total = importances.sum()
        if total > 0:
            importances /= total
        feature_importance = []
        for i in range(min(n_features, len(self._feature_names))):
            feature_importance.append({
                "feature_index": i,
                "feature_name": self._feature_names[i] if i < len(self._feature_names) else f"feature_{i}",
                "importance": float(importances[i]),
            })
        feature_importance.sort(key=lambda x: x["importance"], reverse=True)
        return {
            "method": "IsolationForest_split_frequency",
            "total_estimators": len(if_model.model.estimators_),
            "feature_importance": feature_importance,
            "top_features": [f["feature_name"] for f in feature_importance[:10]],
        }

    def get_feature_names(self) -> List[str]:
        return self._feature_names.copy()
