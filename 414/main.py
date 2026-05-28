import logging
import os
import random
import sys
import time
from typing import Dict, Optional

import numpy as np

from config.config import (
    KAFKA_CONFIG,
    REDIS_CONFIG,
    MODEL_CONFIG,
    FRAUD_THRESHOLDS,
    RULE_ENGINE_CONFIG,
    ALERT_CONFIG,
    TRANSACTION_SIMULATION,
    LOGGING_CONFIG,
    DISPOSITION_CONFIG,
    NETWORK_ANALYSIS_CONFIG,
    EXPLAINABILITY_CONFIG,
    ONLINE_LEARNING_CONFIG,
)
from utils.utils import setup_logging
from models.ensemble import FraudDetectionEnsemble
from models.isolation_forest import IsolationForestModel
from models.autoencoder import PersonalizedAutoencoder
from core.redis_manager import RedisManager
from core.rule_engine import RuleEngine
from core.scoring import ScoringEngine
from core.network_analyzer import NetworkAnalyzer
from core.explainability import ExplainabilityEngine
from core.online_learner import OnlineLearner
from alert.alert_system import AlertSystem
from streaming.kafka_producer import TransactionProducer
from streaming.flink_job import FlinkStreamProcessor

logger = logging.getLogger(__name__)


def generate_training_data(n_samples: int = 10000, n_features: int = 30) -> np.ndarray:
    logger.info("Generating %d training samples with %d features...", n_samples, n_features)
    np.random.seed(42)
    normal_data = np.random.randn(int(n_samples * 0.95), n_features) * 0.5 + 2.0
    fraud_data = np.random.randn(int(n_samples * 0.05), n_features) * 2.0 + 8.0
    data = np.vstack([normal_data, fraud_data])
    np.random.shuffle(data)
    return data.astype(np.float32)


def train_or_load_models(ensemble: FraudDetectionEnsemble, force_retrain: bool = False) -> bool:
    if not force_retrain and ensemble.load():
        logger.info("Pre-trained models loaded successfully")
        return True

    logger.info("Training new models...")
    X_train = generate_training_data(n_samples=50000, n_features=30)
    ensemble.train(X_train)
    ensemble.save()
    logger.info("Models trained and saved successfully")
    return True


def initialize_system(force_retrain: bool = False) -> Dict:
    setup_logging(LOGGING_CONFIG)
    logger.info("=" * 60)
    logger.info("  Credit Card Fraud Detection System - Initializing")
    logger.info("=" * 60)

    logger.info("[1/9] Initializing Redis connection...")
    redis_mgr = RedisManager(REDIS_CONFIG)
    if redis_mgr.ping():
        logger.info("  Redis connection: OK")
    else:
        logger.warning("  Redis connection: FAILED (continuing anyway)")

    logger.info("[2/9] Initializing fraud detection models...")
    ensemble = FraudDetectionEnsemble(MODEL_CONFIG)
    train_or_load_models(ensemble, force_retrain=force_retrain)
    logger.info("  Isolation Forest & Autoencoder: READY")

    logger.info("[3/9] Initializing rule engine...")
    rule_engine = RuleEngine(redis_manager=redis_mgr, config=RULE_ENGINE_CONFIG)
    logger.info("  Rule engine: READY (%d rules registered)", len(rule_engine.list_rules()))

    logger.info("[4/9] Initializing scoring engine...")
    scoring_engine = ScoringEngine(ensemble=ensemble, redis_manager=redis_mgr)
    logger.info("  Scoring engine: READY")

    logger.info("[5/9] Initializing alert system...")
    alert_system = AlertSystem(redis_manager=redis_mgr, config=ALERT_CONFIG)
    logger.info("  Alert system: READY")

    logger.info("[6/9] Initializing network analyzer...")
    network_analyzer = NetworkAnalyzer(redis_manager=redis_mgr)
    logger.info("  Network analyzer: READY")

    logger.info("[7/9] Initializing explainability engine...")
    explainability = ExplainabilityEngine(ensemble=ensemble)
    logger.info("  Explainability engine: READY")

    logger.info("[8/9] Initializing online learner...")
    online_learner = OnlineLearner(ensemble=ensemble, redis_manager=redis_mgr, config=ONLINE_LEARNING_CONFIG)
    logger.info("  Online learner: READY")

    logger.info("[9/9] Initializing stream processor...")
    stream_processor = FlinkStreamProcessor(
        scoring_engine=scoring_engine,
        rule_engine=rule_engine,
        alert_system=alert_system,
        kafka_config=KAFKA_CONFIG,
    )
    logger.info("  Stream processor: READY")

    logger.info("=" * 60)
    logger.info("  System Initialization Complete")
    logger.info("=" * 60)

    return {
        "redis_manager": redis_mgr,
        "ensemble": ensemble,
        "rule_engine": rule_engine,
        "scoring_engine": scoring_engine,
        "alert_system": alert_system,
        "network_analyzer": network_analyzer,
        "explainability": explainability,
        "online_learner": online_learner,
        "stream_processor": stream_processor,
    }


def run_demo(system: Dict, num_transactions: int = 50):
    logger.info("\n" + "=" * 60)
    logger.info("  Running Demo Mode - %d Simulated Transactions", num_transactions)
    logger.info("  [Personalized + SMS + Network + Explainability + Online Learning]")
    logger.info("=" * 60)

    producer = TransactionProducer()
    stream_processor = system["stream_processor"]
    alert_system = system["alert_system"]
    rule_engine = system["rule_engine"]
    ensemble = system["ensemble"]
    network_analyzer = system["network_analyzer"]
    explainability = system["explainability"]
    online_learner = system["online_learner"]

    customer_ids = [f"C{i:06d}" for i in range(1, 21)]
    blocked = 0
    sms_verify = 0
    allowed = 0
    monitored = 0
    explanation_count = 0
    network_alerts = 0

    for i in range(num_transactions):
        customer_id = random.choice(customer_ids)
        is_fraud = random.random() < 0.20

        if is_fraud:
            txn = producer._generate_fraud_transaction(customer_id)
        else:
            txn = producer._generate_normal_transaction(customer_id)

        network_analyzer.record_transaction(txn)

        result = stream_processor.process_transaction(txn)
        decision = result.get("final_decision", {})
        action = decision.get("action", "ALLOW")

        if action == "BLOCK":
            blocked += 1
        elif action == "SMS_VERIFY":
            sms_verify += 1
            verify_id = decision.get("sms_verification", {}).get("verify_id", "")
            if verify_id and random.random() < 0.7:
                verify_result = rule_engine.verify_sms_code(verify_id, "123456")
                if verify_result.get("success"):
                    logger.info("  [SMS Verify Success] %s -> %s", verify_id, verify_result.get("message"))
        elif action == "MONITOR":
            monitored += 1
        else:
            allowed += 1

        if i % 10 == 0 and i > 0:
            network_info = network_analyzer.check_related_to_fraud(customer_id)
            if network_info["is_in_fraud_ring"]:
                network_alerts += 1
                logger.info("  [Network Alert] %s in fraud ring: %d related users",
                             customer_id, network_info["related_users_count"])

        if i == 0 and result.get("scored"):
            features = np.array([
                result["scored"]["features"].get("amount", 0),
                0, 0, 0, 0, 0, 0, 0,
                result["scored"]["features"].get("is_international", False),
                0, 0,
                1.0 if result["scored"]["features"].get("channel") == "online" else 0.0,
                0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
            ], dtype=np.float32).reshape(1, -1)
            explanation = explainability.compute_feature_contribution(features, customer_id)
            if "top_risk_drivers" in explanation:
                explanation_count += 1
                logger.info("  [Explanation] %s", explanation.get("explanation_text", "N/A"))

        if i == 20:
            fake_features = np.random.randn(1, 30).astype(np.float32)
            feedback_result = online_learner.record_feedback(
                fake_features, customer_id, is_fraud=True,
                original_prediction={"combined_probability": 0.8}
            )
            logger.info("  [Online Learning] Feedback recorded: %s", feedback_result.get("feedback_recorded"))

        if i < 3 or is_fraud or action in ("BLOCK", "SMS_VERIFY"):
            alert = result.get("alert")
            if alert:
                logger.info("\n" + alert_system.format_alert_report(alert))

        if (i + 1) % 10 == 0:
            logger.info("  Processed: %d/%d | Blocked: %d | SMS: %d | Monitor: %d | Allowed: %d",
                         i + 1, num_transactions, blocked, sms_verify, monitored, allowed)
        time.sleep(0.02)

    producer.flush()
    producer.close()

    network_analysis = network_analyzer.analyze_network()

    logger.info("\n" + "=" * 60)
    logger.info("  Demo Complete - Enhanced Features Summary")
    logger.info("=" * 60)
    logger.info("  Total: %d | Blocked: %d | SMS Verify: %d | Monitor: %d | Allowed: %d",
                 num_transactions, blocked, sms_verify, monitored, allowed)
    logger.info("  Intervention Rate: %.2f%%", (blocked + sms_verify) / num_transactions * 100)

    logger.info("\n  [Network Analysis]")
    for k, v in network_analysis.items():
        if k != "rings_detail":
            logger.info("    %-25s: %s", k, v)
    if network_analysis.get("rings_detail"):
        logger.info("    Potential fraud rings:")
        for ring in network_analysis["rings_detail"][:3]:
            logger.info("      Ring: %s", ring)

    personalized_users = ensemble.list_personalized_users()
    if personalized_users:
        logger.info("\n  [Personalized Models] (%d users):", len(personalized_users))
        for pu in personalized_users[:5]:
            cid = pu["customer_id"]
            if_info = pu.get("if", {})
            ae_info = pu.get("ae", {})
            logger.info("    - %s: IF samples=%d, AE adapter=%s",
                         cid,
                         if_info.get("sample_count", 0) if if_info else 0,
                         "v" + str(ae_info.get("version", 0)) if ae_info else "N/A")

    logger.info("\n  [Online Learning Stats]")
    ol_stats = online_learner.get_feedback_stats()
    for k, v in ol_stats.items():
        logger.info("    %-25s: %s", k, v)

    logger.info("\n  [Explainability]")
    if_importance = explainability.compute_isolation_forest_importance(ensemble.if_model)
    if "top_features" in if_importance:
        logger.info("    Top 5 IF features: %s", if_importance["top_features"][:5])

    alert_stats = alert_system.get_alert_stats()
    logger.info("\n  [Alert Stats]")
    for k, v in alert_stats.items():
        logger.info("    %-25s: %s", k, v)

    logger.info("=" * 60)


def run_streaming_mode(system: Dict):
    logger.info("\n" + "=" * 60)
    logger.info("  Starting Real-time Stream Processing Mode")
    logger.info("  Press Ctrl+C to stop")
    logger.info("=" * 60)
    try:
        system["stream_processor"].run_streaming_job()
    except KeyboardInterrupt:
        logger.info("Stream processing stopped by user")


def run_producer_only(num_transactions: int = 10000, interval_ms: int = 50):
    logger.info("\n" + "=" * 60)
    logger.info("  Starting Transaction Producer Mode")
    logger.info("  Transactions: %d, Interval: %dms", num_transactions, interval_ms)
    logger.info("=" * 60)
    producer = TransactionProducer()
    try:
        producer.simulate_stream(
            num_transactions=num_transactions,
            interval_ms=interval_ms,
        )
    except KeyboardInterrupt:
        logger.info("Producer stopped by user")
    finally:
        producer.flush()
        producer.close()


def main():
    import argparse
    parser = argparse.ArgumentParser(
        description="Credit Card Fraud Detection - Real-time System",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py --mode demo              # Run demo with 50 transactions
  python main.py --mode demo -n 100       # Run demo with 100 transactions
  python main.py --mode stream            # Start real-time stream processing
  python main.py --mode producer          # Start transaction producer only
  python main.py --mode train             # Train models only
  python main.py --mode train --retrain   # Force retrain models
        """,
    )

    parser.add_argument(
        "--mode",
        choices=["demo", "stream", "producer", "train"],
        default="demo",
        help="Operating mode (default: demo)",
    )
    parser.add_argument(
        "-n", "--num-transactions",
        type=int,
        default=50,
        help="Number of transactions for demo mode (default: 50)",
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=50,
        help="Transaction interval in ms for producer mode (default: 50)",
    )
    parser.add_argument(
        "--retrain",
        action="store_true",
        help="Force retrain models even if pre-trained exist",
    )

    args = parser.parse_args()

    if args.mode == "train":
        setup_logging(LOGGING_CONFIG)
        ensemble = FraudDetectionEnsemble(MODEL_CONFIG)
        train_or_load_models(ensemble, force_retrain=args.retrain)
        logger.info("Model training complete")
        return

    system = initialize_system(force_retrain=args.retrain)

    if args.mode == "demo":
        run_demo(system, num_transactions=args.num_transactions)
    elif args.mode == "stream":
        run_streaming_mode(system)
    elif args.mode == "producer":
        run_producer_only(
            num_transactions=args.num_transactions,
            interval_ms=args.interval,
        )
    elif args.mode == "train":
        pass

    scoring_stats = system["scoring_engine"].get_stats()
    alert_stats = system["alert_system"].get_alert_stats()

    logger.info("\n" + "=" * 60)
    logger.info("  Final System Statistics")
    logger.info("=" * 60)
    logger.info("  Scoring Engine:")
    for k, v in scoring_stats.items():
        logger.info("    %-25s: %s", k, v)
    logger.info("  Alert System:")
    for k, v in alert_stats.items():
        logger.info("    %-25s: %s", k, v)
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
