import logging
import time
from collections import deque
from typing import Dict, List, Optional, Tuple

import numpy as np

from models.isolation_forest import IsolationForestModel
from models.ensemble import FraudDetectionEnsemble
from models.autoencoder import PersonalizedAutoencoder, _TF_AVAILABLE
from core.redis_manager import RedisManager

logger = logging.getLogger(__name__)


class OnlineLearner:
    def __init__(
        self,
        ensemble: FraudDetectionEnsemble,
        redis_manager: Optional[RedisManager] = None,
        config: Optional[Dict] = None,
    ):
        self.ensemble = ensemble
        self.redis = redis_manager or RedisManager()
        self.config = config or {
            "max_buffer_size": 1000,
            "min_samples_for_update": 50,
            "update_interval_seconds": 300,
            "learning_rate_decay": 0.95,
            "fraud_weight_boost": 5.0,
        }
        self._positive_buffer: deque = deque(maxlen=self.config["max_buffer_size"])
        self._negative_buffer: deque = deque(maxlen=self.config["max_buffer_size"])
        self._update_count = 0
        self._last_update_time = 0
        self._total_feedback = 0
        self._feedback_stats = {"confirmed_fraud": 0, "confirmed_legitimate": 0, "false_positive": 0}

    def record_feedback(
        self,
        transaction_features: np.ndarray,
        customer_id: str,
        is_fraud: bool,
        original_prediction: Optional[Dict] = None,
    ) -> Dict:
        if transaction_features.ndim == 1:
            transaction_features = transaction_features.reshape(1, -1)
        feedback_record = {
            "features": transaction_features[0].tolist(),
            "customer_id": customer_id,
            "is_fraud": is_fraud,
            "timestamp": time.time(),
            "original_prediction": original_prediction or {},
        }
        if is_fraud:
            self._positive_buffer.append(feedback_record)
            self._feedback_stats["confirmed_fraud"] += 1
        else:
            self._negative_buffer.append(feedback_record)
            self._feedback_stats["confirmed_legitimate"] += 1
        if original_prediction:
            orig_prob = original_prediction.get("combined_probability", 0)
            if not is_fraud and orig_prob >= 0.6:
                self._feedback_stats["false_positive"] += 1
        self._total_feedback += 1
        should_update = self._should_update()
        if should_update:
            update_result = self._perform_update()
            return {
                "feedback_recorded": True,
                "model_updated": True,
                "update_details": update_result,
                "feedback_stats": self._feedback_stats.copy(),
            }
        return {
            "feedback_recorded": True,
            "model_updated": False,
            "reason": "Insufficient samples or update interval not reached",
            "buffer_sizes": {
                "positive": len(self._positive_buffer),
                "negative": len(self._negative_buffer),
            },
            "feedback_stats": self._feedback_stats.copy(),
        }

    def _should_update(self) -> bool:
        now = time.time()
        if now - self._last_update_time < self.config["update_interval_seconds"]:
            return False
        min_samples = self.config["min_samples_for_update"]
        return len(self._positive_buffer) >= min_samples and len(self._negative_buffer) >= min_samples

    def _perform_update(self) -> Dict:
        logger.info("Performing online model update with %d positive and %d negative samples",
                     len(self._positive_buffer), len(self._negative_buffer))
        pos_features = np.array([r["features"] for r in self._positive_buffer], dtype=np.float32)
        neg_features = np.array([r["features"] for r in self._negative_buffer], dtype=np.float32)
        combined = np.vstack([pos_features, neg_features])
        labels = np.concatenate([
            np.ones(len(pos_features)),
            np.zeros(len(neg_features)),
        ])
        now = time.time()
        update_result = {
            "timestamp": now,
            "update_number": self._update_count + 1,
            "samples_used": len(combined),
            "fraud_samples": len(pos_features),
            "legitimate_samples": len(neg_features),
        }
        if_model = self.ensemble.if_model
        if if_model.scaler and if_model.model:
            try:
                if_model.scaler.partial_fit(combined)
                update_result["if_scaler_updated"] = True
            except Exception as e:
                logger.warning("Failed to update IF scaler: %s", e)
                update_result["if_scaler_updated"] = False
        if _TF_AVAILABLE:
            ae_model = self.ensemble.ae_model
            try:
                unique_customers = set(
                    [r["customer_id"] for r in self._positive_buffer] +
                    [r["customer_id"] for r in self._negative_buffer]
                )
                for cid in list(unique_customers)[:20]:
                    customer_features = np.array([
                        r["features"] for r in list(self._positive_buffer) + list(self._negative_buffer)
                        if r["customer_id"] == cid
                    ], dtype=np.float32)
                    if len(customer_features) >= 10:
                        ae_model.fine_tune_for_user(cid, customer_features)
                update_result["ae_adapters_updated"] = True
                update_result["ae_customers_updated"] = len(unique_customers)
            except Exception as e:
                logger.warning("Failed to update AE adapters: %s", e)
                update_result["ae_adapters_updated"] = False
        new_threshold = self._compute_adaptive_threshold(pos_features, neg_features)
        if new_threshold:
            self.ensemble.combined_threshold = new_threshold
            update_result["new_combined_threshold"] = new_threshold
        self._update_count += 1
        self._last_update_time = now
        self._positive_buffer.clear()
        self._negative_buffer.clear()
        logger.info("Online update #%d complete. New threshold: %.4f", self._update_count, new_threshold or self.ensemble.combined_threshold)
        return update_result

    def _compute_adaptive_threshold(
        self, pos_features: np.ndarray, neg_features: np.ndarray
    ) -> Optional[float]:
        if_model = self.ensemble.if_model
        if not if_model.model or not if_model.scaler:
            return None
        try:
            pos_scaled = if_model.scaler.transform(pos_features)
            neg_scaled = if_model.scaler.transform(neg_features)
            pos_scores = if_model.model.decision_function(pos_scaled)
            neg_scores = if_model.model.decision_function(neg_scaled)
            all_scores = np.concatenate([pos_scores, neg_scores])
            percentile = np.percentile(all_scores, 10)
            new_threshold = float(percentile)
            return new_threshold
        except Exception as e:
            logger.warning("Failed to compute adaptive threshold: %s", e)
            return None

    def adjust_user_threshold(
        self, customer_id: str, is_fraud: bool, original_prob: float
    ) -> Dict:
        if_model = self.ensemble.if_model
        current_threshold, has_threshold = if_model.get_user_threshold(customer_id)
        adjustment = 0.02 if is_fraud else -0.01
        new_threshold = current_threshold + adjustment
        new_threshold = max(-1.0, min(1.0, new_threshold))
        if customer_id in if_model._user_thresholds:
            if_model._user_thresholds[customer_id] = new_threshold
        return {
            "customer_id": customer_id,
            "old_threshold": current_threshold,
            "new_threshold": new_threshold,
            "adjustment": adjustment,
            "has_user_threshold": has_threshold,
        }

    def get_feedback_stats(self) -> Dict:
        return {
            "total_feedback": self._total_feedback,
            "confirmed_fraud": self._feedback_stats["confirmed_fraud"],
            "confirmed_legitimate": self._feedback_stats["confirmed_legitimate"],
            "false_positive": self._feedback_stats["false_positive"],
            "false_positive_rate": (
                self._feedback_stats["false_positive"] / max(self._total_feedback, 1)
            ),
            "model_updates": self._update_count,
            "last_update_time": self._last_update_time,
            "current_buffer_sizes": {
                "positive": len(self._positive_buffer),
                "negative": len(self._negative_buffer),
            },
            "ensemble_threshold": self.ensemble.combined_threshold,
        }

    def force_update(self) -> Dict:
        self._last_update_time = 0
        return self._perform_update()
