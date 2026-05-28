import logging
import time
from typing import Dict, List, Optional

from config.config import RULE_ENGINE_CONFIG, DISPOSITION_CONFIG, FRAUD_THRESHOLDS
from utils.utils import current_hour_utc, haversine_km, current_timestamp_ms
from core.redis_manager import RedisManager

logger = logging.getLogger(__name__)


class RuleEngine:
    def __init__(self, redis_manager: Optional[RedisManager] = None, config: Optional[Dict] = None):
        self.redis = redis_manager or RedisManager()
        self.config = config or RULE_ENGINE_CONFIG
        self._rules = self._register_rules()

    def _register_rules(self) -> List[Dict]:
        return [
            {"name": "amount_exceeds_high", "type": "threshold", "severity": "high"},
            {"name": "amount_exceeds_medium", "type": "threshold", "severity": "medium"},
            {"name": "frequency_exceeds", "type": "velocity", "severity": "medium"},
            {"name": "geo_anomaly", "type": "geo", "severity": "high"},
            {"name": "new_merchant", "type": "merchant", "severity": "medium"},
            {"name": "odd_hours", "type": "temporal", "severity": "low"},
            {"name": "velocity_anomaly", "type": "velocity", "severity": "high"},
            {"name": "cross_border", "type": "geo", "severity": "medium"},
            {"name": "high_risk_category", "type": "category", "severity": "medium"},
            {"name": "device_anomaly", "type": "device", "severity": "low"},
        ]

    def evaluate_rules(self, transaction: Dict, scored: Dict) -> Dict:
        triggered_rules = []
        rule_adjustments = {}
        customer_id = transaction.get("customer_id", "")
        amount = float(transaction.get("amount", 0))
        high_threshold = self.config.get("amount_threshold_high", 10000)
        medium_threshold = self.config.get("amount_threshold_medium", 5000)
        if amount >= high_threshold:
            triggered_rules.append("amount_exceeds_high")
            rule_adjustments["amount_exceeds_high"] = {"multiplier": 1.5, "severity": "high"}
        elif amount >= medium_threshold:
            triggered_rules.append("amount_exceeds_medium")
            rule_adjustments["amount_exceeds_medium"] = {"multiplier": 1.2, "severity": "medium"}

        freq_window = self.config.get("transaction_frequency_window_seconds", 3600)
        freq_threshold = self.config.get("transaction_frequency_threshold", 10)
        tx_count_24h = transaction.get("transaction_count_24h", 0)
        if tx_count_24h >= freq_threshold:
            triggered_rules.append("frequency_exceeds")
            rule_adjustments["frequency_exceeds"] = {"multiplier": 1.3, "severity": "medium"}

        velocity = self.redis.get_customer_velocity(customer_id, window_seconds=self.config.get("velocity_check_window_seconds", 300))
        velocity_amount_threshold = self.config.get("velocity_check_amount_threshold", 5000)
        if velocity.get("total_amount", 0) >= velocity_amount_threshold and velocity.get("count", 0) >= 3:
            triggered_rules.append("velocity_anomaly")
            rule_adjustments["velocity_anomaly"] = {"multiplier": 1.5, "severity": "high"}

        customer_profile = self.redis.get_customer_profile(customer_id)
        if customer_profile:
            last_lat = customer_profile.get("last_latitude")
            last_lon = customer_profile.get("last_longitude")
            if last_lat and last_lon:
                distance = haversine_km(last_lat, last_lon, transaction.get("latitude", 0), transaction.get("longitude", 0))
                if distance > self.config.get("geo_distance_threshold_km", 500):
                    triggered_rules.append("geo_anomaly")
                    rule_adjustments["geo_anomaly"] = {"multiplier": 1.5, "severity": "high"}
        if transaction.get("is_international"):
            triggered_rules.append("cross_border")
            rule_adjustments["cross_border"] = {"multiplier": 1.3, "severity": "medium"}

        merchant_id = transaction.get("merchant_id", "")
        tx_history = self.redis.get_transaction_history(customer_id, limit=50)
        past_merchants = {t.get("merchant_id", "") for t in tx_history if isinstance(t, dict)}
        if merchant_id and merchant_id not in past_merchants and len(tx_history) > 5:
            triggered_rules.append("new_merchant")
            rule_adjustments["new_merchant"] = {"multiplier": self.config.get("new_merchant_risk_multiplier", 1.5), "severity": "medium"}

        hour = current_hour_utc()
        odd_start = self.config.get("odd_hours_start", 0)
        odd_end = self.config.get("odd_hours_end", 5)
        if odd_start <= hour <= odd_end:
            triggered_rules.append("odd_hours")
            rule_adjustments["odd_hours"] = {"multiplier": 1.2, "severity": "low"}

        high_risk_categories = {"gambling", "crypto", "adult", "luxury", "jewelry"}
        if transaction.get("category", "") in high_risk_categories:
            triggered_rules.append("high_risk_category")
            rule_adjustments["high_risk_category"] = {"multiplier": 1.3, "severity": "medium"}

        device = transaction.get("device_type", "")
        if customer_profile and customer_profile.get("primary_device"):
            if device != customer_profile["primary_device"]:
                triggered_rules.append("device_anomaly")
                rule_adjustments["device_anomaly"] = {"multiplier": 1.1, "severity": "low"}

        if velocity.get("count", 0) > 0:
            self.redis.record_velocity_entry(customer_id, amount, transaction.get("timestamp", time.time()))

        return {
            "triggered_rules": triggered_rules,
            "rule_adjustments": rule_adjustments,
            "rule_count": len(triggered_rules),
            "has_high_severity": any(
                adj.get("severity") == "high" for adj in rule_adjustments.values()
            ),
            "velocity": velocity,
        }

    def _check_sms_verified(self, customer_id: str, tx_id: str) -> Dict:
        verification_key = f"sms_verify:{customer_id}:{tx_id}"
        result = self.redis.get(verification_key)
        if result and isinstance(result, dict):
            return {
                "verified": result.get("verified", False),
                "verified_at": result.get("verified_at"),
                "method": result.get("method", "sms"),
            }
        return {"verified": False, "verified_at": None, "method": None}

    def _store_pending_verification(self, transaction: Dict, decision: Dict) -> str:
        tx_id = transaction.get("transaction_id", "")
        customer_id = transaction.get("customer_id", "")
        verify_id = f"VRF-{int(time.time())}-{tx_id[:8]}"
        verify_data = {
            "verify_id": verify_id,
            "transaction_id": tx_id,
            "customer_id": customer_id,
            "amount": transaction.get("amount"),
            "merchant_id": transaction.get("merchant_id"),
            "probability": decision.get("final_probability"),
            "created_at": current_timestamp_ms(),
            "expires_at": current_timestamp_ms() + 300000,
            "status": "PENDING",
        }
        self.redis.set(f"verification:{verify_id}", verify_data, ttl_seconds=300)
        self.redis.hset(f"customer:{customer_id}", "pending_verification", verify_id, ttl_seconds=300)
        return verify_id

    def combine_scores(self, scored: Dict, rule_results: Dict) -> Dict:
        fraud_prob = scored.get("fraud_probability", 0)
        adjustments = rule_results.get("rule_adjustments", {})
        max_multiplier = 1.0
        for adj in adjustments.values():
            if adj.get("multiplier", 1.0) > max_multiplier:
                max_multiplier = adj["multiplier"]
        adjusted_prob = min(fraud_prob * max_multiplier, 1.0)
        has_high_severity = rule_results.get("has_high_severity", False)
        rule_count = rule_results.get("rule_count", 0)
        block_threshold = DISPOSITION_CONFIG.get("block_threshold", 0.85)
        sms_verify_threshold = DISPOSITION_CONFIG.get("sms_verify_threshold", 0.60)
        monitor_threshold = DISPOSITION_CONFIG.get("monitor_threshold", 0.30)
        auto_block_rules = set(DISPOSITION_CONFIG.get("auto_block_rules", []))
        auto_sms_verify_rules = set(DISPOSITION_CONFIG.get("auto_sms_verify_rules", []))
        triggered_rules = set(rule_results.get("triggered_rules", []))
        auto_block = bool(triggered_rules & auto_block_rules) or adjusted_prob >= block_threshold
        auto_sms_verify = bool(triggered_rules & auto_sms_verify_rules) or adjusted_prob >= sms_verify_threshold

        customer_id = scored.get("customer_id", "")
        tx_id = scored.get("transaction_id", "")
        sms_result = self._check_sms_verified(customer_id, tx_id)
        already_verified = sms_result.get("verified", False)

        if auto_block:
            action = "BLOCK"
            reason = "交易拦截：高风险欺诈概率或高危规则触发"
        elif already_verified:
            action = "ALLOW"
            reason = "交易放行：已通过短信二次验证"
        elif auto_sms_verify:
            action = "SMS_VERIFY"
            reason = "需要验证：中等风险交易，发送短信二次确认"
        elif adjusted_prob >= monitor_threshold:
            action = "MONITOR"
            reason = "监控中：中低风险交易，持续关注"
        else:
            action = "ALLOW"
            reason = "交易放行：无显著风险"

        verify_id = None
        if action == "SMS_VERIFY":
            verify_id = self._store_pending_verification(
                transaction=scored,
                decision={
                    "final_probability": adjusted_prob,
                    "base_probability": fraud_prob,
                    "risk_multiplier": max_multiplier,
                },
            )

        should_alert = action in ("BLOCK", "SMS_VERIFY")
        risk_level = "HIGH" if action == "BLOCK" else ("MEDIUM" if action == "SMS_VERIFY" else ("LOW" if action == "MONITOR" else "NORMAL"))

        return {
            "final_probability": adjusted_prob,
            "base_probability": fraud_prob,
            "risk_multiplier": max_multiplier,
            "action": action,
            "risk_level": risk_level,
            "should_alert": should_alert,
            "should_block": action == "BLOCK",
            "should_sms_verify": action == "SMS_VERIFY",
            "should_monitor": action == "MONITOR",
            "should_allow": action == "ALLOW",
            "sms_verification": {
                "required": action == "SMS_VERIFY",
                "already_verified": already_verified,
                "verified_at": sms_result.get("verified_at"),
                "verify_id": verify_id,
            },
            "reason": reason,
            "triggered_rule_count": rule_count,
            "has_high_severity": has_high_severity,
            "block_threshold": block_threshold,
            "sms_verify_threshold": sms_verify_threshold,
            "monitor_threshold": monitor_threshold,
        }

    def get_rule_info(self, rule_name: str) -> Optional[Dict]:
        for rule in self._rules:
            if rule["name"] == rule_name:
                return rule
        return None

    def list_rules(self) -> List[Dict]:
        return self._rules.copy()

    def verify_sms_code(self, verify_id: str, code: str) -> Dict:
        verify_data = self.redis.get(f"verification:{verify_id}")
        if not verify_data:
            return {"success": False, "error": "Verification not found or expired"}
        correct_code = verify_data.get("generated_code", "123456")
        customer_id = verify_data.get("customer_id", "")
        tx_id = verify_data.get("transaction_id", "")

        if code == correct_code:
            verify_data["status"] = "VERIFIED"
            verify_data["verified_at"] = current_timestamp_ms()
            self.redis.set(f"verification:{verify_id}", verify_data, ttl_seconds=3600)
            self.redis.set(f"sms_verify:{customer_id}:{tx_id}", {
                "verified": True,
                "verified_at": current_timestamp_ms(),
                "method": "sms",
                "verify_id": verify_id,
            }, ttl_seconds=3600)
            self.redis.hset(f"customer:{customer_id}", "pending_verification", None)
            return {
                "success": True,
                "action": "ALLOW",
                "message": "验证通过，交易已放行",
                "verify_id": verify_id,
            }
        else:
            verify_data["status"] = "FAILED"
            verify_data["failed_attempts"] = verify_data.get("failed_attempts", 0) + 1
            self.redis.set(f"verification:{verify_id}", verify_data, ttl_seconds=300)
            return {
                "success": False,
                "action": "BLOCK",
                "message": "验证码错误",
                "verify_id": verify_id,
                "attempts_left": max(0, 3 - verify_data.get("failed_attempts", 0)),
            }

    def get_pending_verifications(self, customer_id: str) -> List[Dict]:
        pending = []
        pattern = f"verification:*"
        try:
            for key in self.redis.client.scan_iter(match=pattern):
                data = self.redis.get(key)
                if isinstance(data, dict) and data.get("customer_id") == customer_id and data.get("status") == "PENDING":
                    pending.append(data)
        except Exception as e:
            logger.warning("Failed to scan pending verifications: %s", e)
        return pending
