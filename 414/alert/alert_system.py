import logging
import random
import time
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional

from config.config import ALERT_CONFIG
from utils.utils import current_timestamp_ms, generate_transaction_id
from core.redis_manager import RedisManager

logger = logging.getLogger(__name__)


class AlertSystem:
    def __init__(self, redis_manager: Optional[RedisManager] = None, config: Optional[Dict] = None):
        self.redis = redis_manager or RedisManager()
        self.config = config or ALERT_CONFIG
        self._alert_count = 0
        self._critical_count = 0
        self._warning_count = 0
        self._blocked_count = 0
        self._sms_verify_count = 0
        self._verified_count = 0

    def _generate_sms_code(self) -> str:
        return str(random.randint(100000, 999999))

    def generate_alert(
        self,
        transaction: Dict,
        scored: Dict,
        rule_results: Dict,
        decision: Dict,
    ) -> Optional[Dict]:
        action = decision.get("action", "ALLOW")

        if action == "BLOCK":
            level = "CRITICAL"
            self._critical_count += 1
            self._blocked_count += 1
        elif action == "SMS_VERIFY":
            level = "WARNING"
            self._warning_count += 1
            self._sms_verify_count += 1
        elif action == "VERIFY":
            level = "WARNING"
            self._warning_count += 1
            self._verified_count += 1
        else:
            level = "INFO"

        customer_id = transaction.get("customer_id", "unknown")
        rate_limit = self.redis.get_alert_rate_limit(customer_id)
        max_alerts = self.config.get("max_alerts_per_minute", 30)
        if rate_limit >= max_alerts:
            logger.warning("Alert rate limit exceeded for customer %s, suppressing alert", customer_id)
            return None

        sms_code = None
        if action == "SMS_VERIFY":
            sms_code = self._generate_sms_code()
            verify_id = decision.get("sms_verification", {}).get("verify_id", "")
            if verify_id:
                verify_data = self.redis.get(f"verification:{verify_id}")
                if isinstance(verify_data, dict):
                    verify_data["generated_code"] = sms_code
                    verify_data["code_expires_at"] = current_timestamp_ms() + 300000
                    self.redis.set(f"verification:{verify_id}", verify_data, ttl_seconds=300)

        alert_id = f"ALT-{generate_transaction_id()}"
        alert = {
            "alert_id": alert_id,
            "timestamp": current_timestamp_ms(),
            "datetime_utc": datetime.now(timezone.utc).isoformat(),
            "level": level,
            "action": action,
            "customer_id": customer_id,
            "transaction_id": transaction.get("transaction_id"),
            "merchant_id": transaction.get("merchant_id"),
            "amount": transaction.get("amount"),
            "currency": transaction.get("currency", "CNY"),
            "risk_level": decision.get("risk_level", "LOW"),
            "fraud_probability": decision.get("final_probability", 0),
            "base_probability": decision.get("base_probability", 0),
            "risk_multiplier": decision.get("risk_multiplier", 1.0),
            "triggered_rules": rule_results.get("triggered_rules", []),
            "rule_count": rule_results.get("rule_count", 0),
            "has_high_severity": rule_results.get("has_high_severity", False),
            "model_scores": scored.get("model_scores", {}),
            "disposition": {
                "action": action,
                "reason": decision.get("reason", ""),
                "should_block": decision.get("should_block", False),
                "should_sms_verify": decision.get("should_sms_verify", False),
                "should_monitor": decision.get("should_monitor", False),
                "should_allow": decision.get("should_allow", False),
            },
            "sms_verification": {
                "required": decision.get("should_sms_verify", False),
                "verify_id": decision.get("sms_verification", {}).get("verify_id"),
                "sms_code": sms_code,
                "already_verified": decision.get("sms_verification", {}).get("already_verified", False),
            } if decision.get("should_sms_verify", False) or decision.get("sms_verification", {}).get("already_verified") else None,
            "transaction_summary": {
                "category": transaction.get("category"),
                "channel": transaction.get("channel"),
                "city": transaction.get("city"),
                "is_international": transaction.get("is_international"),
                "device_type": transaction.get("device_type"),
                "ip_address": transaction.get("ip_address"),
                "is_recurring": transaction.get("is_recurring"),
            },
            "recommendations": self._generate_recommendations(decision, rule_results),
        }

        self._alert_count += 1
        self.redis.increment_alert_rate(customer_id, self.config.get("alert_cooldown_seconds", 60))
        self._send_alert(alert)

        logger.info(
            "Alert %s generated: [%s] %s for customer %s, tx=%s, prob=%.4f",
            alert_id, level, action, customer_id,
            transaction.get("transaction_id"), decision.get("final_probability", 0),
        )
        return alert

    def _generate_recommendations(self, decision: Dict, rule_results: Dict) -> List[str]:
        recommendations = []
        action = decision.get("action", "ALLOW")
        sms_verify = decision.get("should_sms_verify", False)

        if action == "BLOCK":
            recommendations.append("立即拦截交易")
            recommendations.append("冻结相关账户并通知风控团队")
            recommendations.append("联系持卡人确认交易合法性")
            recommendations.append("将商户标记为高风险进行监控")
        elif sms_verify:
            recommendations.append("发送短信验证码进行二次确认")
            recommendations.append("验证码有效期5分钟，最多3次输入机会")
            recommendations.append("验证通过自动放行，失败则拦截")
            recommendations.append("待人工审核交易详情")
        elif action == "VERIFY":
            recommendations.append("要求持卡人通过APP确认交易")
            recommendations.append("暂时挂起交易等待人工审核")
        elif action == "MONITOR":
            recommendations.append("增强该账户的交易监控频率")
            recommendations.append("关注后续类似交易行为")
            recommendations.append("定期更新该用户的风险评分")
        else:
            recommendations.append("正常放行交易")
            recommendations.append("持续常规监控")

        triggered_rules = rule_results.get("triggered_rules", [])
        rule_recommendations = {
            "amount_exceeds_high": "建议核实大额消费的用途",
            "amount_exceeds_medium": "建议关注中等金额的消费频率",
            "frequency_exceeds": "建议检查高频消费是否为盗刷",
            "geo_anomaly": "建议核实地理位置异常是否为本人操作",
            "new_merchant": "建议确认新商户的交易合法性",
            "odd_hours": "建议确认非工作时间交易",
            "velocity_anomaly": "建议核实短时间内多笔交易",
            "cross_border": "建议确认跨境交易的必要性",
            "high_risk_category": "建议关注高风险类别交易",
            "device_anomaly": "建议确认是否为常用设备操作",
        }
        for rule in triggered_rules:
            if rule in rule_recommendations:
                recommendations.append(rule_recommendations[rule])
        return recommendations

    def _send_alert(self, alert: Dict):
        try:
            webhook_url = self.config.get("webhook_url", "")
            if webhook_url:
                self._send_webhook(webhook_url, alert)
            if self.config.get("email_notification", False):
                self._send_email(alert)
            if alert.get("sms_verification", {}).get("required") and self.config.get("sms_notification", False):
                self._send_sms_verification(alert)
        except Exception as e:
            logger.warning("Failed to send alert via notification channels: %s", e)

    def _send_sms_verification(self, alert: Dict):
        sms_data = alert.get("sms_verification", {})
        code = sms_data.get("sms_code")
        verify_id = sms_data.get("verify_id")
        customer_id = alert.get("customer_id")
        amount = alert.get("amount")
        merchant = alert.get("merchant_id")
        logger.info(
            "[SMS SIMULATION] To %s: 验证码 %s 用于验证交易 %s (金额: %.2f, 商户: %s)",
            customer_id, code, verify_id, amount, merchant
        )

    def _send_webhook(self, url: str, alert: Dict):
        logger.debug("Sending webhook alert %s to %s", alert.get("alert_id"), url)

    def _send_email(self, alert: Dict):
        logger.debug("Sending email for alert %s", alert.get("alert_id"))

    def get_alert_stats(self) -> Dict:
        return {
            "total_alerts": self._alert_count,
            "critical_alerts": self._critical_count,
            "warning_alerts": self._warning_count,
            "blocked_transactions": self._blocked_count,
            "sms_verify_requested": self._sms_verify_count,
            "verified_transactions": self._verified_count,
        }

    def format_alert_report(self, alert: Dict) -> str:
        lines = [
            "=" * 60,
            f"  FRAUD ALERT REPORT - {alert.get('alert_id', 'N/A')}",
            "=" * 60,
            f"  Level:        {alert.get('level', 'N/A')}",
            f"  Action:       {alert.get('action', 'N/A')}",
            f"  Risk Level:   {alert.get('risk_level', 'N/A')}",
            f"  Time (UTC):   {alert.get('datetime_utc', 'N/A')}",
            "-" * 60,
            f"  Customer:     {alert.get('customer_id', 'N/A')}",
            f"  Transaction:  {alert.get('transaction_id', 'N/A')}",
            f"  Merchant:     {alert.get('merchant_id', 'N/A')}",
            f"  Amount:       {alert.get('currency', 'CNY')} {alert.get('amount', 0):.2f}",
            "-" * 60,
            f"  Fraud Prob:   {alert.get('fraud_probability', 0):.4f}",
            f"  Base Prob:    {alert.get('base_probability', 0):.4f}",
            f"  Multiplier:   {alert.get('risk_multiplier', 1.0):.2f}",
            f"  Rules Hit:    {alert.get('rule_count', 0)}",
        ]

        sms_verify = alert.get("sms_verification")
        if sms_verify and sms_verify.get("required"):
            lines.extend([
                "-" * 60,
                "  SMS Verification:",
                f"    Verify ID:  {sms_verify.get('verify_id', 'N/A')}",
                f"    SMS Code:   {sms_verify.get('sms_code', 'N/A')}",
                f"    Status:     AWAITING VERIFICATION",
            ])
        elif sms_verify and sms_verify.get("already_verified"):
            lines.extend([
                "-" * 60,
                "  SMS Verification:",
                f"    Status:     VERIFIED",
                f"    Verified At:{sms_verify.get('verified_at', 'N/A')}",
            ])

        lines.extend([
            "-" * 60,
            "  Triggered Rules:",
        ])
        for rule in alert.get("triggered_rules", []):
            lines.append(f"    - {rule}")
        lines.extend([
            "-" * 60,
            "  Disposition:",
            f"    Action: {alert.get('disposition', {}).get('action', 'N/A')}",
            f"    Reason: {alert.get('disposition', {}).get('reason', 'N/A')}",
            "-" * 60,
            "  Recommendations:",
        ])
        for rec in alert.get("recommendations", []):
            lines.append(f"    * {rec}")
        lines.append("=" * 60)
        return "\n".join(lines)
