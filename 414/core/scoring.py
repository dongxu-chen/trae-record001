import logging
import time
from typing import Dict, List, Optional

import numpy as np

from models.ensemble import FraudDetectionEnsemble
from core.redis_manager import RedisManager
from config.config import FRAUD_THRESHOLDS
from utils.utils import current_timestamp_ms

logger = logging.getLogger(__name__)


class ScoringEngine:
    def __init__(
        self,
        ensemble: FraudDetectionEnsemble,
        redis_manager: Optional[RedisManager] = None,
    ):
        self.ensemble = ensemble
        self.redis = redis_manager or RedisManager()
        self._txn_count = 0
        self._fraud_count = 0
        self._start_time = current_timestamp_ms()

    def _extract_features(self, transaction: Dict) -> np.ndarray:
        features = [
            float(transaction.get("amount", 0)),
            float(transaction.get("transaction_count_24h", 0)),
            float(transaction.get("transaction_count_7d", 0)),
            float(transaction.get("avg_transaction_amount_30d", 0)),
            float(transaction.get("customer_age", 30)),
            float(transaction.get("customer_tenure_years", 5)),
            float(transaction.get("latitude", 0)),
            float(transaction.get("longitude", 0)),
            1.0 if transaction.get("is_international") else 0.0,
            1.0 if transaction.get("is_recurring") else 0.0,
            1.0 if transaction.get("card_type") == "credit" else 0.0,
            1.0 if transaction.get("channel") == "online" else 0.0,
            1.0 if transaction.get("channel") == "mobile" else 0.0,
            float(transaction.get("timestamp", 0)) / 1e12,
            1.0 if transaction.get("customer_gender") == "M" else 0.0,
            float(hash(transaction.get("merchant_id", "")) % 10000) / 10000.0,
            float(hash(transaction.get("ip_address", "")) % 10000) / 10000.0,
            float(hash(transaction.get("city", "")) % 1000) / 1000.0,
            1.0 if transaction.get("customer_income_level") == "high" else 0.0,
            1.0 if transaction.get("customer_income_level") == "medium" else 0.0,
            1.0 if transaction.get("customer_income_level") == "low" else 0.0,
            1.0 if transaction.get("device_type") in ["ios", "android"] else 0.0,
            1.0 if transaction.get("category") in ["luxury", "electronics", "jewelry"] else 0.0,
            1.0 if transaction.get("category") in ["gambling", "crypto", "adult"] else 0.0,
            1.0 if transaction.get("currency") != "CNY" else 0.0,
            float(transaction.get("amount", 0)) / max(transaction.get("avg_transaction_amount_30d", 1), 1),
            1.0 if float(transaction.get("amount", 0)) > 10000 else 0.0,
            1.0 if float(transaction.get("amount", 0)) > 5000 else 0.0,
            float(transaction.get("transaction_count_24h", 0)) / 24.0,
            float(transaction.get("transaction_count_7d", 0)) / 168.0,
        ]
        return np.array(features, dtype=np.float32)

    def score_transaction(self, transaction: Dict) -> Dict:
        features = self._extract_features(transaction)
        customer_id = transaction.get("customer_id", "")
        model_result = self.ensemble.score_transaction(features, customer_id)
        risk_level = self.ensemble.risk_level(model_result["combined_probability"])
        self._txn_count += 1
        if model_result["is_fraud"]:
            self._fraud_count += 1
        scored = {
            "transaction_id": transaction.get("transaction_id"),
            "customer_id": customer_id,
            "merchant_id": transaction.get("merchant_id"),
            "amount": transaction.get("amount"),
            "timestamp": transaction.get("timestamp"),
            "scored_at": current_timestamp_ms(),
            "model_scores": model_result,
            "risk_level": risk_level,
            "is_fraud": model_result["is_fraud"],
            "fraud_probability": model_result["combined_probability"],
            "features": {
                "amount": transaction.get("amount"),
                "category": transaction.get("category"),
                "is_international": transaction.get("is_international"),
                "city": transaction.get("city"),
                "channel": transaction.get("channel"),
            },
            "personalization": model_result.get("personalization", {}),
        }
        self._cache_scored(scored)
        return scored

    def _cache_scored(self, scored: Dict):
        try:
            tx_id = scored.get("transaction_id", "")
            self.redis.cache_scored_transaction(tx_id, scored, ttl=3600)
            customer_id = scored.get("customer_id", "")
            prob = scored.get("fraud_probability", 0)
            self.redis.set_customer_fraud_score(customer_id, prob)
            self.redis.add_transaction_to_history(customer_id, {
                "tx_id": tx_id,
                "amount": scored.get("amount"),
                "risk": scored.get("risk_level"),
                "prob": prob,
                "ts": scored.get("scored_at"),
            })
        except Exception as e:
            logger.warning("Failed to cache scored transaction: %s", e)

    def get_stats(self) -> Dict:
        elapsed_ms = current_timestamp_ms() - self._start_time
        elapsed_s = max(elapsed_ms / 1000.0, 1)
        return {
            "total_transactions": self._txn_count,
            "fraud_detected": self._fraud_count,
            "fraud_rate": self._fraud_count / max(self._txn_count, 1),
            "throughput_tps": self._txn_count / elapsed_s,
            "uptime_seconds": elapsed_s,
            "model_threshold": self.ensemble.combined_threshold,
        }
