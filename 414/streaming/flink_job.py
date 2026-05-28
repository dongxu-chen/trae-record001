import json
import logging
import time
from typing import Dict, List, Optional

try:
    from kafka import KafkaConsumer
    _KAFKA_AVAILABLE = True
except ImportError:
    _KAFKA_AVAILABLE = False
    KafkaConsumer = None

from config.config import KAFKA_CONFIG, FLINK_CONFIG
from utils.utils import current_timestamp_ms

logger = logging.getLogger(__name__)


class FlinkStreamProcessor:
    def __init__(self, scoring_engine, rule_engine, alert_system, kafka_config=None, flink_config=None):
        self.scoring_engine = scoring_engine
        self.rule_engine = rule_engine
        self.alert_system = alert_system
        self.kafka_config = kafka_config or KAFKA_CONFIG
        self.flink_config = flink_config or FLINK_CONFIG
        self._running = False

    def process_transaction(self, transaction: Dict) -> Dict:
        tx_id = transaction.get("transaction_id", "unknown")
        logger.debug("Processing transaction: %s", tx_id)
        try:
            scored = self.scoring_engine.score_transaction(transaction)
            rule_results = self.rule_engine.evaluate_rules(transaction, scored)
            final_decision = self.rule_engine.combine_scores(scored, rule_results)
            alert_result = None
            if final_decision.get("should_alert"):
                alert_result = self.alert_system.generate_alert(
                    transaction=transaction,
                    scored=scored,
                    rule_results=rule_results,
                    decision=final_decision,
                )
            result = {
                "transaction_id": tx_id,
                "customer_id": transaction.get("customer_id"),
                "timestamp": transaction.get("timestamp"),
                "processed_at": current_timestamp_ms(),
                "scored": scored,
                "rule_results": rule_results,
                "final_decision": final_decision,
                "alert": alert_result,
            }
            return result
        except Exception as e:
            logger.error("Error processing transaction %s: %s", tx_id, e)
            return {
                "transaction_id": tx_id,
                "customer_id": transaction.get("customer_id"),
                "timestamp": transaction.get("timestamp"),
                "processed_at": current_timestamp_ms(),
                "error": str(e),
                "final_decision": {"action": "ALLOW", "reason": "系统异常，默认放行", "risk_level": "LOW"},
                "scored": None,
                "rule_results": None,
                "alert": None,
            }

    def process_batch(self, transactions: List[Dict]) -> List[Dict]:
        results = []
        for tx in transactions:
            try:
                result = self.process_transaction(tx)
                results.append(result)
                self._emit_result(result)
            except Exception as e:
                logger.error("Error processing transaction %s: %s", tx.get("transaction_id"), e)
                result = {
                    "transaction_id": tx.get("transaction_id"),
                    "error": str(e),
                    "timestamp": tx.get("timestamp"),
                    "processed_at": current_timestamp_ms(),
                }
                results.append(result)
        return results

    def _emit_result(self, result: Dict):
        try:
            from streaming.kafka_producer import TransactionProducer
            producer = TransactionProducer()
            producer.send_scored(result)
            if result.get("alert"):
                producer.send_alert(result["alert"])
            producer.flush()
        except Exception as e:
            logger.warning("Failed to emit result: %s", e)

    def run_streaming_job(self):
        if not _KAFKA_AVAILABLE:
            logger.error("Kafka not available. Cannot start streaming job. Install kafka-python and run Kafka infrastructure.")
            return
        logger.info("Starting Flink-style streaming processing...")
        self._running = True
        consumer = KafkaConsumer(
            self.kafka_config["transaction_topic"],
            bootstrap_servers=self.kafka_config["bootstrap_servers"],
            group_id=self.kafka_config.get("group_id", "fraud_detection_group"),
            auto_offset_reset=self.kafka_config.get("auto_offset_reset", "latest"),
            enable_auto_commit=self.kafka_config.get("enable_auto_commit", True),
            value_deserializer=lambda m: json.loads(m.decode("utf-8")),
        )
        logger.info("Kafka consumer subscribed to topic: %s", self.kafka_config["transaction_topic"])
        try:
            for message in consumer:
                if not self._running:
                    break
                try:
                    transaction = message.value
                    result = self.process_transaction(transaction)
                    self._emit_result(result)
                except Exception as e:
                    logger.error("Error in stream processing: %s", e)
        except KeyboardInterrupt:
            logger.info("Stream processing interrupted")
        finally:
            self._running = False
            consumer.close()
            logger.info("Stream processing stopped")

    def stop(self):
        self._running = False
        logger.info("Stopping stream processor...")

    @property
    def running(self) -> bool:
        return self._running
