import logging
import os
from typing import Dict, List, Optional, Tuple

import numpy as np

from models.isolation_forest import IsolationForestModel
from models.autoencoder import PersonalizedAutoencoder, _TF_AVAILABLE
from config.config import MODEL_CONFIG, FRAUD_THRESHOLDS
from utils.utils import sigmoid

logger = logging.getLogger(__name__)


class FraudDetectionEnsemble:
    def __init__(self, config: Optional[Dict] = None):
        self.config = config or MODEL_CONFIG
        self.if_model = IsolationForestModel(config)
        self.ae_model = PersonalizedAutoencoder(config)
        if _TF_AVAILABLE:
            self._if_weight = 0.4
            self._ae_weight = 0.6
        else:
            self._if_weight = 1.0
            self._ae_weight = 0.0
            logger.warning("TensorFlow not available. Running in Isolation-Forest-only mode (weight=1.0).")
        self._combined_threshold = FRAUD_THRESHOLDS.get("combined_fraud_threshold", 0.70)

    def train(self, X: np.ndarray) -> "FraudDetectionEnsemble":
        logger.info("Training fraud detection ensemble...")
        self.if_model.train(X)
        if _TF_AVAILABLE:
            self.ae_model.train_base(X)
        else:
            logger.warning("Skipping Autoencoder training - TensorFlow not available")
        logger.info("Ensemble training complete")
        return self

    def _combined_probability(self, if_prob: np.ndarray, ae_prob: np.ndarray) -> np.ndarray:
        return self._if_weight * if_prob + self._ae_weight * ae_prob

    def predict(self, X: np.ndarray, customer_ids: Optional[List[str]] = None) -> Dict:
        if_labels, if_scores = self.if_model.predict(X, customer_ids)
        if customer_ids and len(customer_ids) == len(X):
            ae_labels = np.zeros(len(X), dtype=int)
            ae_errors = np.zeros(len(X))
            ae_probs = np.zeros(len(X))
            if_probs = self.if_model.fraud_probability(X, customer_ids)
            for i, cid in enumerate(customer_ids):
                ae_label, ae_error = self.ae_model.predict(X[i:i+1], cid)
                ae_labels[i] = ae_label[0]
                ae_errors[i] = ae_error[0]
                ae_probs[i] = self.ae_model.fraud_probability(X[i:i+1], cid)[0]
        else:
            ae_labels, ae_errors = self.ae_model.predict(X)
            if_probs = self.if_model.fraud_probability(X)
            ae_probs = self.ae_model.fraud_probability(X)

        combined_prob = self._combined_probability(if_probs, ae_probs)
        combined_labels = (combined_prob >= self._combined_threshold).astype(int)
        return {
            "isolation_forest": {
                "labels": if_labels,
                "scores": if_scores,
                "probability": if_probs,
            },
            "autoencoder": {
                "labels": ae_labels,
                "reconstruction_error": ae_errors,
                "probability": ae_probs,
            },
            "ensemble": {
                "probability": combined_prob,
                "labels": combined_labels,
                "threshold": self._combined_threshold,
            },
        }

    def fraud_probability(self, X: np.ndarray, customer_ids: Optional[List[str]] = None) -> np.ndarray:
        if_probs = self.if_model.fraud_probability(X, customer_ids)
        if customer_ids and len(customer_ids) == len(X):
            ae_probs = np.zeros(len(X))
            for i, cid in enumerate(customer_ids):
                ae_probs[i] = self.ae_model.fraud_probability(X[i:i+1], cid)[0]
        else:
            ae_probs = self.ae_model.fraud_probability(X)
        return self._combined_probability(if_probs, ae_probs)

    def score_transaction(self, transaction_features: np.ndarray, customer_id: Optional[str] = None) -> Dict:
        if transaction_features.ndim == 1:
            transaction_features = transaction_features.reshape(1, -1)

        if_result = self.if_model.score_for_customer(transaction_features, customer_id) if customer_id else None
        ae_result = self.ae_model.score_for_customer(transaction_features, customer_id) if customer_id and _TF_AVAILABLE else None

        if customer_id and if_result and ae_result:
            if_prob = if_result["probability"]
            ae_prob = ae_result["probability"]
            combined = self._combined_probability(np.array([if_prob]), np.array([ae_prob]))[0]
        elif customer_id and if_result:
            if_prob = if_result["probability"]
            combined = if_prob
        else:
            result = self.predict(transaction_features, [customer_id] if customer_id else None)
            if_prob = float(result["isolation_forest"]["probability"][0])
            ae_prob = float(result["autoencoder"]["probability"][0])
            combined = float(result["ensemble"]["probability"][0])
            if_result = {
                "score": float(result["isolation_forest"]["scores"][0]),
                "threshold": self.if_model.global_threshold,
                "has_user_threshold": False,
                "user_sample_count": 0,
                "probability": if_prob,
                "is_anomaly": bool(result["isolation_forest"]["labels"][0]),
                "label": int(result["isolation_forest"]["labels"][0]),
            }
            ae_result = {
                "reconstruction_error": float(result["autoencoder"]["reconstruction_error"][0]),
                "threshold": self.ae_model.global_threshold if _TF_AVAILABLE else 0,
                "has_user_adapter": False,
                "adapter_version": 0,
                "finetune_count": 0,
                "buffer_size": 0,
                "probability": ae_prob,
                "is_anomaly": bool(result["autoencoder"]["labels"][0]),
                "label": int(result["autoencoder"]["labels"][0]),
            }

        return {
            "if_probability": float(if_result["probability"]) if if_result else 0.0,
            "ae_probability": float(ae_result["probability"]) if ae_result else 0.0,
            "combined_probability": float(combined),
            "is_fraud": bool(combined >= self._combined_threshold),
            "ae_reconstruction_error": float(ae_result["reconstruction_error"]) if ae_result else 0.0,
            "if_score": float(if_result["score"]) if if_result else 0.0,
            "personalization": {
                "customer_id": customer_id,
                "if_user_threshold": float(if_result["threshold"]) if if_result else 0.0,
                "if_has_user_threshold": bool(if_result.get("has_user_threshold", False)) if if_result else False,
                "if_user_sample_count": int(if_result.get("user_sample_count", 0)) if if_result else 0,
                "ae_has_user_adapter": bool(ae_result.get("has_user_adapter", False)) if ae_result else False,
                "ae_adapter_version": int(ae_result.get("adapter_version", 0)) if ae_result else 0,
                "ae_finetune_count": int(ae_result.get("finetune_count", 0)) if ae_result else 0,
                "ae_buffer_size": int(ae_result.get("buffer_size", 0)) if ae_result else 0,
            },
        }

    def risk_level(self, probability: float) -> str:
        high = FRAUD_THRESHOLDS.get("high_risk_probability", 0.85)
        medium = FRAUD_THRESHOLDS.get("medium_risk_probability", 0.60)
        if probability >= high:
            return "HIGH"
        elif probability >= medium:
            return "MEDIUM"
        else:
            return "LOW"

    def load(self) -> bool:
        if_loaded = self.if_model.load()
        ae_loaded = self.ae_model.load() if _TF_AVAILABLE else True
        return if_loaded and ae_loaded

    def save(self) -> bool:
        if_saved = self.if_model.save()
        ae_saved = self.ae_model.save() if _TF_AVAILABLE else True
        return if_saved and ae_saved

    def is_trained(self) -> bool:
        if _TF_AVAILABLE:
            return self.if_model.is_trained() and self.ae_model.is_trained()
        return self.if_model.is_trained()

    def get_user_model_stats(self, customer_id: str) -> Dict:
        return {
            "customer_id": customer_id,
            "isolation_forest": self.if_model.get_user_stats(customer_id),
            "autoencoder": self.ae_model.get_user_stats(customer_id) if _TF_AVAILABLE else {},
            "if_weight": self._if_weight,
            "ae_weight": self._ae_weight,
            "has_personalized_model": (
                self.if_model.get_user_stats(customer_id).get("has_user_threshold", False)
                or (self.ae_model.get_user_stats(customer_id).get("has_adapter", False) if _TF_AVAILABLE else False)
            ),
        }

    def list_personalized_users(self) -> List[Dict]:
        if_users = {u["customer_id"]: u for u in self.if_model.list_users_with_thresholds()}
        ae_users = {u["customer_id"]: u for u in (self.ae_model.list_users_with_adapters() if _TF_AVAILABLE else [])}
        all_cids = set(if_users.keys()) | set(ae_users.keys())
        result = []
        for cid in all_cids:
            result.append({
                "customer_id": cid,
                "if": if_users.get(cid),
                "ae": ae_users.get(cid),
            })
        return result

    @property
    def combined_threshold(self) -> float:
        return self._combined_threshold

    @combined_threshold.setter
    def combined_threshold(self, value: float):
        self._combined_threshold = float(value)

    @property
    def if_weight(self) -> float:
        return self._if_weight

    @if_weight.setter
    def if_weight(self, value: float):
        self._if_weight = float(value)
        self._ae_weight = 1.0 - self._if_weight

    @property
    def ae_weight(self) -> float:
        return self._ae_weight

    @ae_weight.setter
    def ae_weight(self, value: float):
        self._ae_weight = float(value)
        self._if_weight = 1.0 - self._ae_weight
