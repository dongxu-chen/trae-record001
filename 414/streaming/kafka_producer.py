import json
import logging
import random
import time
from typing import Dict, Optional

try:
    from kafka import KafkaProducer, errors
    _KAFKA_AVAILABLE = True
except ImportError:
    _KAFKA_AVAILABLE = False
    KafkaProducer = None
    errors = None

from config.config import KAFKA_CONFIG, TRANSACTION_SIMULATION
from utils.utils import generate_transaction_id, current_timestamp_ms, current_hour_utc

logger = logging.getLogger(__name__)


class TransactionProducer:
    def __init__(self, kafka_config: Optional[Dict] = None):
        self.config = kafka_config or KAFKA_CONFIG
        self._producer = None

    def _check_kafka(self):
        if not _KAFKA_AVAILABLE:
            raise RuntimeError(
                "kafka-python is not installed. Kafka operations unavailable. "
                "Install kafka-python: pip install kafka-python"
            )

    def _create_producer(self):
        self._check_kafka()
        try:
            producer = KafkaProducer(
                bootstrap_servers=self.config["bootstrap_servers"],
                acks=self.config.get("producer_acks", "all"),
                retries=self.config.get("retries", 3),
                value_serializer=lambda v: json.dumps(v, default=str).encode("utf-8"),
                key_serializer=lambda k: k.encode("utf-8") if k else None,
                max_in_flight_requests_per_connection=5,
                enable_idempotence=True,
            )
            logger.info("Kafka producer connected to %s", self.config["bootstrap_servers"])
            return producer
        except errors.NoBrokersAvailable as e:
            logger.error("No Kafka brokers available: %s", e)
            raise

    @property
    def producer(self):
        if self._producer is None:
            self._producer = self._create_producer()
        return self._producer

    def _generate_normal_transaction(self, customer_id: str) -> Dict:
        merchant_ids = [f"M{i:04d}" for i in range(1, 51)]
        categories = ["retail", "grocery", "dining", "transport", "entertainment", "utilities"]
        cities = [
            ("Beijing", 39.9, 116.4),
            ("Shanghai", 31.2, 121.5),
            ("Guangzhou", 23.1, 113.3),
            ("Shenzhen", 22.5, 114.1),
            ("Chengdu", 30.7, 104.1),
            ("Hangzhou", 30.3, 120.2),
        ]
        city_name, lat, lon = random.choice(cities)
        lat_jitter = random.gauss(0, 0.05)
        lon_jitter = random.gauss(0, 0.05)

        amount = round(random.uniform(
            TRANSACTION_SIMULATION.get("min_amount", 1.0),
            TRANSACTION_SIMULATION.get("max_normal_amount", 5000.0)
        ), 2)

        hour = current_hour_utc()

        return {
            "transaction_id": generate_transaction_id(),
            "customer_id": customer_id,
            "merchant_id": random.choice(merchant_ids),
            "amount": amount,
            "currency": "CNY",
            "timestamp": current_timestamp_ms(),
            "category": random.choice(categories),
            "latitude": round(lat + lat_jitter, 6),
            "longitude": round(lon + lon_jitter, 6),
            "city": city_name,
            "card_type": random.choice(["credit", "debit"]),
            "channel": random.choice(["online", "pos", "mobile"]),
            "is_recurring": random.random() < 0.15,
            "customer_age": random.randint(18, 75),
            "customer_gender": random.choice(["M", "F"]),
            "customer_income_level": random.choice(["low", "medium", "high"]),
            "customer_tenure_years": random.randint(0, 20),
            "transaction_count_24h": random.randint(0, 8),
            "transaction_count_7d": random.randint(0, 30),
            "avg_transaction_amount_30d": round(random.uniform(50, 3000), 2),
            "is_international": False,
            "device_type": random.choice(["ios", "android", "desktop", "tablet"]),
            "ip_address": f"{random.randint(1, 255)}.{random.randint(0, 255)}.{random.randint(0, 255)}.{random.randint(0, 255)}",
            "is_fraud": False,
        }

    def _generate_fraud_transaction(self, customer_id: str) -> Dict:
        txn = self._generate_normal_transaction(customer_id)
        fraud_type = random.choice([
            "large_amount",
            "unusual_merchant",
            "odd_hours",
            "geo_anomaly",
            "frequency_burst",
            "cross_border",
        ])

        if fraud_type == "large_amount":
            txn["amount"] = round(random.uniform(5000, TRANSACTION_SIMULATION.get("max_fraud_amount", 20000)), 2)
            txn["category"] = random.choice(["luxury", "electronics", "jewelry"])
            txn["merchant_id"] = f"F{random.randint(1000, 9999)}"
        elif fraud_type == "odd_hours":
            txn["amount"] = round(random.uniform(1000, 8000), 2)
        elif fraud_type == "geo_anomaly":
            txn["latitude"] = round(random.uniform(-90, 90), 6)
            txn["longitude"] = round(random.uniform(-180, 180), 6)
            txn["city"] = "Unknown"
            txn["is_international"] = True
        elif fraud_type == "frequency_burst":
            txn["transaction_count_24h"] = random.randint(15, 30)
            txn["transaction_count_7d"] = random.randint(40, 80)
        elif fraud_type == "cross_border":
            txn["is_international"] = True
            txn["currency"] = random.choice(["USD", "EUR", "GBP", "JPY"])
            txn["latitude"] = round(random.uniform(-90, 90), 6)
            txn["longitude"] = round(random.uniform(-180, 180), 6)
        elif fraud_type == "unusual_merchant":
            txn["merchant_id"] = f"S{random.randint(10000, 99999)}"
            txn["category"] = random.choice(["gambling", "crypto", "adult"])

        txn["is_fraud"] = True
        txn["fraud_type"] = fraud_type
        return txn

    def send_transaction(self, transaction: Dict) -> bool:
        if not _KAFKA_AVAILABLE:
            logger.debug("Kafka not available, skipping send for transaction %s", transaction.get("transaction_id"))
            return True
        try:
            future = self.producer.send(
                topic=self.config["transaction_topic"],
                key=transaction.get("customer_id"),
                value=transaction,
            )
            record_metadata = future.get(timeout=10)
            logger.debug(
                "Transaction %s sent to partition %d at offset %d",
                transaction.get("transaction_id"),
                record_metadata.partition,
                record_metadata.offset,
            )
            return True
        except errors.KafkaError as e:
            logger.error("Failed to send transaction %s: %s", transaction.get("transaction_id"), e)
            return False

    def send_alert(self, alert: Dict) -> bool:
        if not _KAFKA_AVAILABLE:
            logger.info("Kafka not available, skipping alert send for %s", alert.get("alert_id"))
            return True
        try:
            future = self.producer.send(
                topic=self.config["alert_topic"],
                key=alert.get("customer_id"),
                value=alert,
            )
            record_metadata = future.get(timeout=10)
            logger.info("Alert %s sent to partition %d", alert.get("alert_id"), record_metadata.partition)
            return True
        except errors.KafkaError as e:
            logger.error("Failed to send alert: %s", e)
            return False

    def send_scored(self, scored: Dict) -> bool:
        if not _KAFKA_AVAILABLE:
            logger.debug("Kafka not available, skipping scored send for %s", scored.get("transaction_id"))
            return True
        try:
            future = self.producer.send(
                topic=self.config["scored_topic"],
                key=scored.get("customer_id"),
                value=scored,
            )
            future.get(timeout=10)
            return True
        except errors.KafkaError as e:
            logger.error("Failed to send scored transaction: %s", e)
            return False

    def simulate_stream(
        self,
        num_transactions: Optional[int] = None,
        interval_ms: Optional[int] = None,
    ):
        num = num_transactions or TRANSACTION_SIMULATION.get("total_transactions", 100000)
        interval = interval_ms or TRANSACTION_SIMULATION.get("transaction_interval_ms", 100)
        fraud_prob = TRANSACTION_SIMULATION.get("fraud_transaction_probability", 0.05)

        customer_ids = [f"C{i:06d}" for i in range(1, 5001)]

        logger.info("Starting transaction simulation: %d transactions, %dms interval", num, interval)
        sent = 0
        for i in range(num):
            customer_id = random.choice(customer_ids)
            if random.random() < fraud_prob:
                txn = self._generate_fraud_transaction(customer_id)
            else:
                txn = self._generate_normal_transaction(customer_id)

            if self.send_transaction(txn):
                sent += 1

            if (i + 1) % 1000 == 0:
                logger.info("Sent %d/%d transactions", i + 1, num)

            time.sleep(interval / 1000.0)

        logger.info("Simulation complete. Sent %d transactions", sent)

    def flush(self):
        if self._producer:
            self._producer.flush()
            logger.info("Kafka producer flushed")

    def close(self):
        if self._producer:
            self._producer.close()
            self._producer = None
            logger.info("Kafka producer closed")
