import logging
import os
from collections import deque
from typing import Dict, List, Optional, Tuple

import joblib
import numpy as np
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler

from config.config import MODEL_CONFIG, FRAUD_THRESHOLDS
from utils.utils import normalize_features

logger = logging.getLogger(__name__)


class IsolationForestModel:
    def __init__(self, config: Optional[Dict] = None):
        self.config = config or MODEL_CONFIG
        self.model: Optional[IsolationForest] = None
        self.scaler: Optional[StandardScaler] = None
        self._global_threshold = FRAUD_THRESHOLDS.get("isolation_forest_anomaly_threshold", -0.5)
        self._is_trained = False
        self._user_score_buffers: Dict[str, deque] = {}
        self._user_thresholds: Dict[str, float] = {}
        self._user_counts: Dict[str, int] = {}
        self._min_samples_for_user_threshold = self.config.get("if_min_user_samples", 20)
        self._dynamic_quantile = self.config.get("if_dynamic_quantile", 5)
        self._max_buffer_size = self.config.get("if_max_user_buffer", 500)

    def train(self, X: np.ndarray) -> "IsolationForestModel":
        logger.info("Training IsolationForest on %d samples with %d features", X.shape[0], X.shape[1])
        self.scaler = StandardScaler()
        X_scaled = self.scaler.fit_transform(X)
        self.model = IsolationForest(
            n_estimators=self.config.get("if_n_estimators", 100),
            max_samples=self.config.get("if_max_samples", "auto"),
            contamination="auto",
            random_state=42,
            n_jobs=-1,
            verbose=0,
        )
        self.model.fit(X_scaled)
        scores = self.model.decision_function(X_scaled)
        self._global_threshold = np.percentile(scores, self._dynamic_quantile)
        self._is_trained = True
        logger.info(
            "IsolationForest trained. Global threshold=%.4f (q=%d), Score range=[%.4f, %.4f]",
            self._global_threshold, self._dynamic_quantile, scores.min(), scores.max()
        )
        return self

    def _update_user_stats(self, customer_id: str, score: float) -> Tuple[float, bool]:
        if customer_id not in self._user_score_buffers:
            self._user_score_buffers[customer_id] = deque(maxlen=self._max_buffer_size)
            self._user_counts[customer_id] = 0
            self._user_thresholds[customer_id] = self._global_threshold
        self._user_score_buffers[customer_id].append(score)
        self._user_counts[customer_id] += 1
        count = self._user_counts[customer_id]
        has_user_threshold = False
        if count >= self._min_samples_for_user_threshold:
            user_scores = np.array(self._user_score_buffers[customer_id])
            self._user_thresholds[customer_id] = np.percentile(user_scores, self._dynamic_quantile)
            has_user_threshold = True
        return self._user_thresholds[customer_id], has_user_threshold

    def get_user_threshold(self, customer_id: str) -> Tuple[float, bool]:
        if customer_id in self._user_thresholds:
            return self._user_thresholds[customer_id], self._user_counts.get(customer_id, 0) >= self._min_samples_for_user_threshold
        return self._global_threshold, False

    def predict(self, X: np.ndarray, customer_ids: Optional[List[str]] = None) -> Tuple[np.ndarray, np.ndarray]:
        if not self._is_trained:
            raise RuntimeError("IsolationForest model not trained")
        X_scaled = normalize_features(X, self.scaler)
        scores = self.model.decision_function(X_scaled)
        labels = np.zeros(len(scores), dtype=int)
        if customer_ids and len(customer_ids) == len(scores):
            for i, (score, cid) in enumerate(zip(scores, customer_ids)):
                threshold, _ = self._update_user_stats(cid, score)
                labels[i] = 1 if score < threshold else 0
        else:
            labels = (scores < self._global_threshold).astype(int)
        return labels, scores

    def anomaly_score(self, X: np.ndarray) -> np.ndarray:
        if not self._is_trained:
            raise RuntimeError("IsolationForest model not trained")
        X_scaled = normalize_features(X, self.scaler)
        return self.model.decision_function(X_scaled)

    def fraud_probability(self, X: np.ndarray, customer_ids: Optional[List[str]] = None) -> np.ndarray:
        scores = self.anomaly_score(X)
        if customer_ids and len(customer_ids) == len(scores):
            probs = np.zeros(len(scores), dtype=np.float32)
            for i, (score, cid) in enumerate(zip(scores, customer_ids)):
                threshold, has_user = self.get_user_threshold(cid)
                if has_user:
                    diff = threshold - score
                    user_prob = 1.0 / (1.0 + np.exp(diff * 10))
                    probs[i] = user_prob
                else:
                    probs[i] = 1.0 / (1.0 + np.exp(score * -10))
            return np.clip(probs, 0.0, 1.0)
        else:
            probs = 1.0 / (1.0 + np.exp(scores * -10))
            return np.clip(probs, 0.0, 1.0)

    def score_for_customer(self, X: np.ndarray, customer_id: str) -> Dict:
        if X.ndim == 1:
            X = X.reshape(1, -1)
        scores = self.anomaly_score(X)
        score = float(scores[0])
        threshold, has_user = self._update_user_stats(customer_id, score)
        prob = 1.0 / (1.0 + np.exp((threshold - score) * 10)) if has_user else 1.0 / (1.0 + np.exp(score * -10))
        label = 1 if score < threshold else 0
        return {
            "score": score,
            "threshold": threshold,
            "has_user_threshold": has_user,
            "user_sample_count": self._user_counts.get(customer_id, 0),
            "probability": float(np.clip(prob, 0.0, 1.0)),
            "is_anomaly": bool(label),
            "label": int(label),
        }

    @property
    def global_threshold(self) -> float:
        return self._global_threshold

    @property
    def user_count(self) -> int:
        return len(self._user_thresholds)

    def get_user_stats(self, customer_id: str) -> Dict:
        return {
            "threshold": self._user_thresholds.get(customer_id, self._global_threshold),
            "sample_count": self._user_counts.get(customer_id, 0),
            "has_user_threshold": self._user_counts.get(customer_id, 0) >= self._min_samples_for_user_threshold,
            "buffer_size": len(self._user_score_buffers.get(customer_id, deque())),
        }

    def list_users_with_thresholds(self) -> List[Dict]:
        return [
            {
                "customer_id": cid,
                "threshold": thr,
                "sample_count": self._user_counts[cid],
                "buffer_size": len(self._user_score_buffers[cid]),
            }
            for cid, thr in self._user_thresholds.items()
        ]

    def save(self, path: Optional[str] = None) -> bool:
        path = path or self.config.get("isolation_forest_path")
        if not path:
            path = os.path.join("models", "saved", "isolation_forest.joblib")
        try:
            save_dir = os.path.dirname(path)
            if save_dir and not os.path.exists(save_dir):
                os.makedirs(save_dir, exist_ok=True)
            user_data = {
                cid: {
                    "threshold": thr,
                    "count": self._user_counts.get(cid, 0),
                    "scores": list(self._user_score_buffers.get(cid, deque())),
                }
                for cid, thr in self._user_thresholds.items()
            }
            data = {
                "model": self.model,
                "scaler": self.scaler,
                "global_threshold": self._global_threshold,
                "config": self.config,
                "user_data": user_data,
            }
            joblib.dump(data, path)
            logger.info("IsolationForest model saved to %s (users: %d)", path, len(user_data))
            return True
        except Exception as e:
            logger.error("Failed to save IsolationForest model: %s", e)
            return False

    def load(self, path: Optional[str] = None) -> bool:
        path = path or self.config.get("isolation_forest_path")
        if not path or not os.path.exists(path):
            logger.warning("IsolationForest model file not found: %s", path)
            return False
        try:
            data = joblib.load(path)
            self.model = data.get("model")
            self.scaler = data.get("scaler")
            self._global_threshold = data.get("global_threshold", self._global_threshold)
            if data.get("config"):
                self.config.update(data["config"])
            user_data = data.get("user_data", {})
            self._user_score_buffers = {}
            self._user_thresholds = {}
            self._user_counts = {}
            for cid, ud in user_data.items():
                self._user_thresholds[cid] = ud.get("threshold", self._global_threshold)
                self._user_counts[cid] = ud.get("count", 0)
                self._user_score_buffers[cid] = deque(ud.get("scores", []), maxlen=self._max_buffer_size)
            self._is_trained = True
            logger.info("IsolationForest model loaded from %s (users: %d)", path, len(user_data))
            return True
        except Exception as e:
            logger.error("Failed to load IsolationForest model: %s", e)
            return False

    def is_trained(self) -> bool:
        return self._is_trained
