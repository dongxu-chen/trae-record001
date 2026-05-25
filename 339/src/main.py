import os
import sys
import time
import argparse
import random
from datetime import datetime
from typing import Dict, List, Optional
import threading

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from common.logger import get_logger
from common.utils import load_config

from messaging.event_producer import UserEventProducer
from messaging.event_consumer import UserEventConsumer
from flink.stream_processor import StreamProcessingJob
from spark.feature_engineering import FeatureEngineering
from spark.feature_window_aligner import FeatureWindowAligner
from model.cox_model import CoxSurvivalModel, ModelTrainer
from model.stratified_cox import StratifiedCoxModel, StratifiedModelTrainer
from redis.cache_manager import RedisCacheManager
from strategy.recommendation_engine import RecommendationEngine
from strategy.bandit_engine import BanditRecommendationEngine, BanditStrategy
from strategy.attribution_analyzer import TouchpointAttributionAnalyzer
from ab_testing.ab_test_manager import ABTestManager
from model.survival_analysis import SurvivalCurveComparator
from analysis.churn_reason_analyzer import ChurnReasonAnalyzer

logger = get_logger("ChurnPredictionSystem")


class ChurnPredictionSystem:
    def __init__(self, use_redis: bool = False, use_spark: bool = False,
                 use_stratified: bool = True, use_bandit: bool = True):
        self.config = load_config()
        logger.info("Initializing Churn Prediction System...")
        logger.info(f"  Stratified Model: {use_stratified}")
        logger.info(f"  Bandit Engine: {use_bandit}")

        self.cache = RedisCacheManager(use_redis=use_redis)
        self.use_stratified = use_stratified
        self.use_bandit = use_bandit

        if use_stratified:
            self.stratified_model = StratifiedCoxModel()
            self.stratified_trainer = StratifiedModelTrainer()
            self.model = self.stratified_model
            self.trainer = self.stratified_trainer
        else:
            self.model = CoxSurvivalModel()
            self.trainer = ModelTrainer()

        if use_bandit:
            self.bandit_engine = BanditRecommendationEngine(
                self.cache, strategy=BanditStrategy.THOMPSON_SAMPLING
            )
            self.recommendation_engine = self.bandit_engine
        else:
            self.recommendation_engine = RecommendationEngine(self.cache)
            self.bandit_engine = None

        self.ab_manager = ABTestManager(self.cache)
        self.window_aligner = FeatureWindowAligner(self.cache)
        self.survival_comparator = SurvivalCurveComparator(self.cache)
        self.attribution_analyzer = TouchpointAttributionAnalyzer(self.cache)
        self.churn_reason_analyzer = ChurnReasonAnalyzer(self.cache)

        self.producer: Optional[UserEventProducer] = None
        self.consumer: Optional[UserEventConsumer] = None
        self.stream_job: Optional[StreamProcessingJob] = None
        self.feature_engineer: Optional[FeatureEngineering] = None

        self.use_spark = use_spark
        self._running = False
        self._threads: List[threading.Thread] = []

        logger.info("System initialized successfully")

    def start_event_producer(self, events_per_second: int = 10, continuous: bool = True):
        logger.info("Starting Kafka event producer...")

        self.producer = UserEventProducer()
        self.producer.connect()

        if continuous:
            def run_producer():
                try:
                    self.producer.start_continuous_production(events_per_second)
                except Exception as e:
                    logger.error(f"Producer error: {e}")

            thread = threading.Thread(target=run_producer, daemon=True)
            thread.start()
            self._threads.append(thread)
            logger.info(f"Event producer started at {events_per_second} events/second")
        else:
            return self.producer

    def start_stream_processing(self):
        logger.info("Starting stream processing...")

        self.consumer = UserEventConsumer()
        self.consumer.connect(auto_offset_reset="latest")

        self.stream_job = StreamProcessingJob(
            kafka_consumer=self.consumer,
            risk_model=self.model,
            redis_manager=self.cache
        )

        def run_stream():
            try:
                self.stream_job.start(batch_size=100)
            except Exception as e:
                logger.error(f"Stream processing error: {e}")

        thread = threading.Thread(target=run_stream, daemon=True)
        thread.start()
        self._threads.append(thread)

        logger.info("Stream processing started")
        return self.stream_job

    def train_model(self, features_path: Optional[str] = None,
                   model_path: Optional[str] = None) -> Dict:
        logger.info("Starting model training...")

        fe = FeatureEngineering(use_spark=self.use_spark)

        if not features_path or not os.path.exists(features_path):
            logger.info("Generating training data...")
            features, metadata = fe.run_batch()
            features_path = "./data/features_latest.csv"
        else:
            features = self.trainer.load_features(features_path)

        metrics = self.trainer.train_and_save(features, model_path)

        if hasattr(self.trainer, 'model') and hasattr(self.trainer.model, 'global_feature_columns'):
            self.window_aligner.update_training_metadata(
                self.trainer.model.global_feature_columns
            )

        fe.close()

        if self.use_stratified:
            logger.info(f"Stratified model training complete. "
                       f"Strata: {metrics.get('num_strata', 0)}, "
                       f"Weighted C-index: {metrics['c_index']:.4f}")
        else:
            logger.info(f"Model training complete. C-index: {metrics['c_index']:.4f}")

        return metrics

    def load_model(self, model_path: Optional[str] = None) -> bool:
        success = self.model.load_model(model_path)
        if success:
            logger.info("Model loaded successfully")
        else:
            logger.warning("Failed to load model, will use heuristic predictions")
        return success

    def process_high_risk_users(self, limit: int = 100,
                                experiment_id: Optional[str] = None) -> List[str]:
        logger.info(f"Processing top {limit} high risk users...")

        if self.use_bandit:
            action_ids = self.bandit_engine.process_high_risk_users(limit=limit)
        else:
            ab_assignments = None
            if experiment_id:
                high_risk = self.cache.get_high_risk_users(limit=limit)
                user_ids = [u["user_id"] for u in high_risk]
                ab_assignments = self.ab_manager.batch_assign_variants(experiment_id, user_ids)

            action_ids = self.recommendation_engine.process_high_risk_users(
                limit=limit,
                ab_assignments=ab_assignments
            )

        logger.info(f"Executed {len(action_ids)} interventions")
        return action_ids

    def track_conversion(self, user_id: str, experiment_id: str):
        self.ab_manager.track_event(
            experiment_id=experiment_id,
            user_id=user_id,
            event_name="conversion_rate"
        )
        logger.info(f"Tracked conversion for user {user_id}")

    def get_user_risk(self, user_id: str) -> Dict:
        risk_data = self.cache.get_risk_score(user_id)
        features = self.cache.get_user_features(user_id)
        profile = self.cache.get_user_profile(user_id)
        actions = self.cache.get_user_actions(user_id)

        return {
            "user_id": user_id,
            "profile": profile,
            "features": features,
            "risk": risk_data,
            "recent_actions": actions,
            "is_high_risk": self.cache._execute(
                "sismember", "high_risk_users", user_id
            ) if hasattr(self.cache._in_memory, 'sismember') or self.cache.client
            else user_id in self.cache._execute("smembers", "high_risk_users")
        }

    def get_system_stats(self) -> Dict:
        cache_stats = self.cache.get_statistics()

        if self.use_bandit and self.bandit_engine:
            strategy_summary = self.bandit_engine.get_summary()
        else:
            strategy_summary = self.recommendation_engine.get_strategy_summary()

        stream_metrics = {}
        if self.stream_job:
            stream_metrics = self.stream_job.processor.get_metrics()

        window_report = self.window_aligner.generate_window_report()

        model_info = {
            "is_trained": self.model.is_trained if hasattr(self.model, 'is_trained') else False,
            "model_version": "2.0.0",
            "type": "stratified_cox" if self.use_stratified else "cox_ph",
        }

        if self.use_stratified and hasattr(self.model, 'get_strata_summary'):
            model_info["strata"] = self.model.get_strata_summary()

        return {
            "cache": cache_stats,
            "strategy": strategy_summary,
            "stream_processing": stream_metrics,
            "window_alignment": window_report,
            "model": model_info,
            "system": {
                "timestamp": datetime.now().isoformat(),
                "status": "running" if self._running else "stopped",
                "active_threads": len(self._threads)
            }
        }

    def run_demo(self, num_users: int = 200, num_events: int = 10000):
        logger.info("=" * 60)
        logger.info("RUNNING CHURN PREDICTION SYSTEM DEMO v3.0")
        logger.info(f"  Stratified Model: {self.use_stratified}")
        logger.info(f"  Bandit Engine: {self.use_bandit}")
        logger.info(f"  Survival Analysis: True")
        logger.info(f"  Attribution Analysis: True")
        logger.info(f"  Churn Reason Analysis: True")
        logger.info("=" * 60)

        logger.info("\n[Step 1] Generating synthetic training data...")
        fe = FeatureEngineering(use_spark=self.use_spark)
        users, events = fe.generate_synthetic_data(
            num_users=num_users,
            avg_events_per_user=int(num_events/num_users),
            churn_ratio=0.3
        )
        fe.save_synthetic_data(users, events, "./data/users.jsonl", "./data/events.jsonl")
        logger.info(f"Generated {len(users)} users and {len(events)} events")

        logger.info("\n[Step 2] Extracting features with sliding windows...")
        features = fe.extract_features_pandas(users, events)
        processed_features, metadata = fe.preprocess_features_pandas(features)
        fe.save_features(processed_features, "./data/features_latest.csv")
        logger.info(f"Extracted {len(metadata['all_features'])} features per user")

        for f in processed_features[:5]:
            self.window_aligner.extractor.user_features_cache = {}

        logger.info("\n[Step 3] Training model...")
        if self.use_stratified:
            logger.info("Using STRATIFIED Cox PH model...")
            metrics = self.stratified_trainer.train_and_save(
                processed_features, "./models/cox_model_stratified.pkl"
            )
            self.window_aligner.update_training_metadata(
                self.stratified_model.global_feature_columns
            )
            logger.info(f"Strata trained: {metrics.get('num_strata', 0)}")
            for name, data in metrics.get('strata', {}).items():
                logger.info(f"  {name}: samples={data.get('train_samples', 0)}, "
                           f"events={data.get('event_count', 0)}, "
                           f"C-index={data.get('c_index', 0):.4f}")
        else:
            logger.info("Using standard Cox PH model...")
            metrics = self.trainer.train_and_save(processed_features, "./models/cox_model.pkl")

        self.model = self.trainer.model
        logger.info(f"Model C-index: {metrics['c_index']:.4f}")
        logger.info(f"Cross-validation mean C-index: {metrics['cross_validation']['mean_c_index']:.4f}")

        logger.info("\n[Step 4] Checking feature window alignment...")
        sample_features = processed_features[0] if processed_features else {}
        alignment = self.window_aligner.check_window_alignment(sample_features)
        logger.info(f"  Window alignment: {'OK' if alignment['aligned'] else 'WARNING'}")
        for w in alignment.get('warnings', []):
            logger.warning(f"  {w.get('message', w)}")

        logger.info("\n[Step 5] Simulating real-time predictions...")
        high_risk_count = 0
        churned_users = [u for u in users if u["churned"]]

        for i, user in enumerate(churned_users[:25]):
            user_features = {}
            for f in processed_features:
                if f["user_id"] == user["user_id"]:
                    user_features = f
                    break

            if user_features:
                prediction = self.model.predict(user_features)
                prediction["user_id"] = user["user_id"]

                self.cache.store_user_profile(user["user_id"], {
                    "user_id": user["user_id"],
                    "user_level": user["user_level"],
                    "region": user["region"],
                    "total_spend": user["total_spend"]
                })
                self.cache.store_user_features(user["user_id"], user_features)
                self.cache.store_risk_score(user["user_id"], prediction)

                if prediction["risk_level"] == "high":
                    high_risk_count += 1
                    self.cache.tag_high_risk_user(user["user_id"], prediction)

                if i < 8:
                    stratum_info = prediction.get('stratum', 'N/A')
                    model_ver = prediction.get('model_version', 'N/A')
                    logger.info(f"  User {user['user_id']}: "
                               f"prob={prediction['churn_probability']:.2%}, "
                               f"risk={prediction['risk_level']}, "
                               f"days={prediction['expected_days_to_churn']:.1f}, "
                               f"stratum={stratum_info}, "
                               f"actual={user['churned']}")

        logger.info(f"\nTagged {high_risk_count} high risk users")

        logger.info("\n[Step 6] Running bandit recommendation engine...")
        if self.use_bandit:
            logger.info("Using Multi-Armed Bandit (Thompson Sampling)...")
            action_ids = self.bandit_engine.process_high_risk_users(limit=50)
            logger.info(f"Bandit executed {len(action_ids)} recommendations")

            bandit_summary = self.bandit_engine.get_summary()
            logger.info(f"Bandit Summary:")
            logger.info(f"  Strategy: {bandit_summary['strategy']}")
            logger.info(f"  Total Arms: {bandit_summary['total_arms']}")
            logger.info(f"  Impressions: {bandit_summary['total_impressions']}")
            logger.info(f"  Conversions: {bandit_summary['total_conversions']}")
        else:
            ab_manager = ABTestManager(self.cache)
            variants = [
                {"name": "Control", "traffic_split": 0.5, "is_control": True},
                {"name": "Aggressive Intervention", "traffic_split": 0.5, "is_control": False}
            ]
            exp = ab_manager.create_experiment(
                name="Churn Prevention Strategy Test",
                variants=variants,
                target_metrics=["conversion_rate", "churn_rate"]
            )
            ab_manager.start_experiment(exp.experiment_id)
            action_ids = self.process_high_risk_users(limit=50, experiment_id=exp.experiment_id)

        logger.info(f"Executed {len(action_ids)} recommendation actions")

        logger.info("\n[Step 7] Simulating conversions...")
        high_risk = self.cache.get_high_risk_users(limit=50)
        converted = 0
        for user in high_risk[:30]:
            if random.random() < 0.25:
                converted += 1
                self.track_conversion(user["user_id"], "sim_exp_001")
                if self.use_bandit:
                    self.bandit_engine.record_result(
                        user["user_id"],
                        "high:premium_offer:push",
                        1.0,
                        True
                    )
        logger.info(f"Simulated {converted} conversions from {len(high_risk[:30])} users")

        logger.info("\n[Step 8] System statistics...")
        stats = self.get_system_stats()
        logger.info(f"  Total users: {stats['cache']['total_users']}")
        logger.info(f"  High risk users: {stats['cache']['high_risk_users']}")
        logger.info(f"  Risk distribution: {stats['cache']['risk_distribution']}")
        if self.use_bandit:
            logger.info(f"  Bandit arms trained: {stats['strategy']['trained_arms']}/{stats['strategy']['total_arms']}")
            logger.info(f"  Bandit conversion rate: {stats['strategy']['overall_conversion_rate']:.2%}")

        logger.info("\n[Step 9] Running survival curve comparison...")
        try:
            import pandas as pd
            df_surv = pd.DataFrame(processed_features)
            
            if "user_level" in df_surv.columns and "duration" in df_surv.columns and "event" in df_surv.columns:
                surv_results = self.survival_comparator.fit_curves(
                    df_surv, group_columns=["user_level"]
                )
                
                if "curves" in surv_results and "user_level" in surv_results["curves"]:
                    curves = surv_results["curves"]["user_level"]
                    logger.info(f"  Fitted survival curves for {len(curves)} user level groups")
                    
                    for name, curve in sorted(curves.items()):
                        logger.info(f"    {name.upper()}: median={curve['median_survival']:.0f}d, "
                                   f"30d_survival={curve.get('survival_at_30d', 0)*100:.0f}%, "
                                   f"samples={curve['num_samples']}")
                    
                    if "comparisons" in surv_results and "user_level" in surv_results["comparisons"]:
                        comp = surv_results["comparisons"]["user_level"]
                        sig_tests = [p for p in comp.get("pairwise", []) if p["significant"]]
                        if sig_tests:
                            logger.info(f"  Found {len(sig_tests)} statistically significant group differences")
                            for test in sig_tests[:3]:
                                logger.info(f"    {test['groups'][0]} vs {test['groups'][1]}: "
                                           f"p={test['p_value']:.4f}, HR={test['hazard_ratio']:.2f}")
                    
                    surv_report = self.survival_comparator.generate_comparison_report()
                    for insight in surv_report["key_insights"][:3]:
                        logger.info(f"  Insight: {insight}")
        except Exception as e:
            logger.warning(f"Survival curve analysis skipped: {e}")

        logger.info("\n[Step 10] Generating synthetic feedback and tickets for churn reason analysis...")
        try:
            feedback_templates = [
                ("pricing", "The subscription is too expensive, I can't afford this cost anymore."),
                ("pricing", "The renewal price increased too much, not worth it."),
                ("product_issues", "The app keeps crashing every time I try to use it."),
                ("customer_service", "My support ticket has been open for 5 days with no response."),
                ("feature_request", "I wish there was a dark mode feature, it's hard to use at night."),
                ("ux_problems", "The interface is so confusing, I can't find anything."),
                ("billing_issues", "I was double charged this month, this is unacceptable."),
                ("competition", "I found a better alternative that's cheaper and has more features."),
                ("reliability", "The service was down for 2 days, very unreliable."),
            ]
            
            ticket_categories = ["Technical", "Billing", "Feature Request", "Account"]
            user_ids_all = [u["user_id"] for u in users]
            
            for i in range(200):
                uid = random.choice(user_ids_all)
                topic, content = feedback_templates[random.randint(0, len(feedback_templates)-1)]
                self.churn_reason_analyzer.add_feedback(
                    feedback_id=f"fb_{i:05d}",
                    user_id=uid,
                    feedback_type=random.choice(["survey", "review", "direct", "support"]),
                    content=content,
                    timestamp=time.time() - random.randint(0, 45) * 86400
                )
            
            for i in range(100):
                uid = random.choice(user_ids_all)
                category = random.choice(ticket_categories)
                created = time.time() - random.randint(0, 30) * 86400
                closed = created + random.randint(1, 72) * 3600 if random.random() < 0.7 else None
                _, desc = feedback_templates[random.randint(0, len(feedback_templates)-1)]
                
                self.churn_reason_analyzer.add_ticket(
                    ticket_id=f"ticket_{i:05d}",
                    user_id=uid,
                    category=category,
                    subcategory=category.lower().replace(" ", "_"),
                    description=desc,
                    priority=random.choices(["low", "medium", "high", "critical"], 
                                           weights=[0.3, 0.4, 0.2, 0.1])[0],
                    status=random.choice(["open", "closed", "pending"]),
                    created_at=created,
                    closed_at=closed
                )
            
            logger.info(f"  Generated {len(self.churn_reason_analyzer.feedback_entries)} feedback entries")
            logger.info(f"  Generated {len(self.churn_reason_analyzer.ticket_entries)} support tickets")
            
        except Exception as e:
            logger.warning(f"Feedback/ticket generation skipped: {e}")

        logger.info("\n[Step 11] Analyzing churn reasons...")
        try:
            churn_data_for_analysis = []
            for u in users:
                churn_data_for_analysis.append({
                    "user_id": u["user_id"],
                    "churned": int(u.get("churned", False)),
                    "churn_time": u.get("churn_time", time.time()) if u.get("churned") else None
                })
            
            reason_results = self.churn_reason_analyzer.analyze_churn_reasons(churn_data_for_analysis)
            
            logger.info(f"  Identified {len(reason_results.get('reasons', {}))} distinct churn reasons")
            
            if "top_reasons" in reason_results:
                for reason in reason_results["top_reasons"][:5]:
                    logger.info(f"    [{reason['category'].upper()}] {reason['reason_name']}: "
                               f"{reason['count']} users, churn={reason['churn_rate_percentage']}, "
                               f"risk={reason['elevated_risk']}, severity={reason['severity_label']}")
            
            if reason_results.get("trending_topics"):
                logger.info(f"\n  Trending topics:")
                for trend in reason_results["trending_topics"][:3]:
                    growth = f"{trend['growth_rate']*100:.0f}%" if trend['growth_rate'] != float('inf') else "NEW"
                    logger.info(f"    {trend['topic']}: {trend['current_count']} mentions (growth: {growth})")
            
            if reason_results.get("key_insights"):
                logger.info(f"\n  Key insights:")
                for insight in reason_results["key_insights"][:3]:
                    logger.info(f"    - {insight}")
            
            reason_report = self.churn_reason_analyzer.generate_churn_reason_report()
            logger.info(f"\n  Recommendations:")
            for rec in reason_report["recommendations"][:3]:
                logger.info(f"    [{rec['priority'].upper()}] {rec['area']}: {rec['action']}")
                
        except Exception as e:
            logger.warning(f"Churn reason analysis skipped: {e}")

        logger.info("\n[Step 12] Running touchpoint attribution analysis...")
        try:
            user_ids_all = [u["user_id"] for u in users]
            group_assignments = self.attribution_analyzer.assign_control_groups(user_ids_all)
            
            channels = ["push", "email", "sms", "in_app"]
            actions = ["discount_offer", "personalized_recommendation", "winback_campaign"]
            channel_costs = {"push": 0.1, "email": 0.5, "sms": 1.0, "in_app": 0.05}
            
            for i in range(400):
                uid = random.choice(user_ids_all)
                if group_assignments[uid] == "treatment":
                    channel = random.choices(channels, weights=[0.4, 0.3, 0.15, 0.15])[0]
                    action = random.choice(actions)
                    ts = time.time() - random.randint(0, 14) * 86400
                    
                    tp = self.attribution_analyzer.record_touchpoint(
                        user_id=uid,
                        channel=channel,
                        action_type=action,
                        timestamp=ts,
                        cost=channel_costs[channel]
                    )
                    
                    if random.random() < 0.3:
                        self.attribution_analyzer.record_response(
                            user_id=uid,
                            touchpoint_timestamp=tp.timestamp,
                            response_timestamp=tp.timestamp + random.randint(1, 72) * 3600
                        )
            
            churn_attribution_data = []
            for u in users:
                churn_attribution_data.append({
                    "user_id": u["user_id"],
                    "churned": int(u.get("churned", False))
                })
            
            attr_results = self.attribution_analyzer.analyze_treatment_effects(
                churn_attribution_data, group_assignments
            )
            
            overall = attr_results["overall"]
            logger.info(f"  Treatment size: {overall['treatment_size']}, Control size: {overall['control_size']}")
            logger.info(f"  Overall uplift: {overall['uplift_absolute']*100:.2f}% (relative: {overall['uplift_relative']*100:.1f}%)")
            logger.info(f"  Total churn prevented: {overall['churn_prevented']}")
            
            if "channel_attribution" in attr_results:
                logger.info(f"\n  Channel performance:")
                for channel, data in sorted(
                    attr_results["channel_attribution"].items(),
                    key=lambda x: x[1]["uplift"], reverse=True
                ):
                    uplift_pct = data['uplift'] * 100
                    roi_pct = data['roi'] * 100
                    sig = "✓" if data.get('is_significant', False) else " "
                    logger.info(f"    {sig} {channel.upper():8s}: uplift={uplift_pct:+.2f}%, "
                               f"ROI={roi_pct:+.1f}%, "
                               f"responses={data['responses']}/{data['total_touches']}, "
                               f"churn_prevented={data['churn_prevented']}")
            
            if attr_results.get("recommendations"):
                logger.info(f"\n  Attribution recommendations:")
                for rec in attr_results["recommendations"][:3]:
                    logger.info(f"    [{rec['priority'].upper()}] {rec['action']}")
            
            attr_report = self.attribution_analyzer.generate_attribution_report()
            for insight in attr_report["key_insights"][:2]:
                logger.info(f"    - {insight}")
                
        except Exception as e:
            logger.warning(f"Attribution analysis skipped: {e}")

        fe.close()

        logger.info("\n" + "=" * 60)
        logger.info("DEMO COMPLETED SUCCESSFULLY (v3.0 with Advanced Analytics)")
        logger.info("=" * 60)

        return {
            "model_metrics": metrics,
            "system_stats": stats
        }

    def start_full_system(self, events_per_second: int = 10):
        logger.info("Starting full churn prediction system...")
        self._running = True

        self.start_event_producer(events_per_second=events_per_second, continuous=True)
        time.sleep(2)
        self.start_stream_processing()

        logger.info("Full system started. Press Ctrl+C to stop.")

        try:
            while self._running:
                time.sleep(10)
                stats = self.get_system_stats()
                logger.info(f"System status - Users: {stats['cache']['total_users']}, "
                           f"High risk: {stats['cache']['high_risk_users']}, "
                           f"Events: {stats['stream_processing'].get('total_events_processed', 0)}")
        except KeyboardInterrupt:
            logger.info("Shutting down system...")
            self.stop()

    def stop(self):
        self._running = False

        if self.producer:
            self.producer.close()

        if self.stream_job:
            self.stream_job.stop()

        if self.consumer:
            self.consumer.close()

        for thread in self._threads:
            thread.join(timeout=5)

        logger.info("System stopped successfully")


def main():
    parser = argparse.ArgumentParser(description="Churn Prediction System v3.0")
    parser.add_argument("--mode", type=str, default="demo",
                       choices=["demo", "train", "predict", "stream", "full", "abtest", "bandit", "stratified", 
                                "survival", "attribution", "reason_analysis"],
                       help="Operating mode")
    parser.add_argument("--use-redis", action="store_true",
                       help="Use Redis instead of in-memory cache")
    parser.add_argument("--use-spark", action="store_true",
                       help="Use Spark for feature engineering")
    parser.add_argument("--no-stratified", action="store_true",
                       help="Disable stratified model")
    parser.add_argument("--no-bandit", action="store_true",
                       help="Disable bandit engine, use rules-based")
    parser.add_argument("--num-users", type=int, default=200,
                       help="Number of users for demo/training")
    parser.add_argument("--num-events", type=int, default=10000,
                       help="Number of events for demo")
    parser.add_argument("--events-per-second", type=int, default=10,
                       help="Event production rate")
    parser.add_argument("--model-path", type=str, default="./models/cox_model.pkl",
                       help="Path to model file")
    parser.add_argument("--features-path", type=str, default="./data/features_latest.csv",
                       help="Path to features CSV")
    parser.add_argument("--bandit-strategy", type=str, default="thompson",
                       choices=["thompson", "epsilon", "ucb"],
                       help="Bandit strategy")

    args = parser.parse_args()

    use_stratified = not args.no_stratified
    use_bandit = not args.no_bandit

    print("=" * 60)
    print("USER CHURN PREDICTION SYSTEM v3.0")
    print("=" * 60)
    print(f"Mode: {args.mode}")
    print(f"Model: {'Stratified Cox' if use_stratified else 'Standard Cox'}")
    print(f"Recommendation: {'Bandit (MAB)' if use_bandit else 'Rules-based'}")
    print(f"Survival Analysis: Enabled")
    print(f"Attribution Analysis: Enabled")
    print(f"Churn Reason Analysis: Enabled")
    print(f"Redis: {'Enabled' if args.use_redis else 'In-memory only'}")
    print(f"Spark: {'Enabled' if args.use_spark else 'Disabled'}")
    print("=" * 60)

    system = ChurnPredictionSystem(
        use_redis=args.use_redis,
        use_spark=args.use_spark,
        use_stratified=use_stratified,
        use_bandit=use_bandit
    )

    try:
        if args.mode == "demo":
            system.run_demo(num_users=args.num_users, num_events=args.num_events)

        elif args.mode == "train":
            metrics = system.train_model(
                features_path=args.features_path,
                model_path=args.model_path
            )
            print("\nTraining Results:")
            print(f"  C-index: {metrics['c_index']:.4f}")
            print(f"  CV Mean C-index: {metrics['cross_validation']['mean_c_index']:.4f}")
            if use_stratified:
                print(f"  Strata: {metrics.get('num_strata', 0)}")
                for name, data in metrics.get('strata', {}).items():
                    print(f"    {name}: C-index={data.get('c_index', 0):.4f}, samples={data.get('train_samples', 0)}")

        elif args.mode == "predict":
            system.load_model(args.model_path)

            while True:
                user_id = input("\nEnter user ID (or 'quit' to exit): ").strip()
                if user_id.lower() == "quit":
                    break

                risk = system.get_user_risk(user_id)
                print(f"\nUser: {user_id}")
                if risk["risk"]:
                    print(f"  Churn Probability: {risk['risk']['churn_probability']:.2%}")
                    print(f"  Risk Level: {risk['risk']['risk_level'].upper()}")
                    print(f"  Expected Days to Churn: {risk['risk']['expected_days_to_churn']:.1f}")
                    print(f"  Risk Score: {risk['risk']['risk_score']:.0f}")
                    if 'stratum' in risk['risk']:
                        print(f"  Stratum: {risk['risk']['stratum']}")
                else:
                    print("  No risk data available")

        elif args.mode == "stream":
            system.load_model(args.model_path)
            system.start_stream_processing()

            try:
                while True:
                    time.sleep(5)
            except KeyboardInterrupt:
                pass

        elif args.mode == "full":
            system.load_model(args.model_path)
            system.start_full_system(events_per_second=args.events_per_second)

        elif args.mode == "abtest":
            ab_manager = ABTestManager(system.cache)
            experiments = ab_manager.list_experiments()

            print(f"\nAvailable experiments ({len(experiments)}):")
            for i, exp in enumerate(experiments[:10], 1):
                print(f"  {i}. {exp['name']} [{exp['status']}]")

            if not experiments:
                print("\nNo experiments found. Create one using the demo mode.")

        elif args.mode == "bandit":
            if not use_bandit:
                print("Error: --no-bandit flag is set, cannot run bandit mode.")
                return

            system.bandit_engine.update_strategy(BanditStrategy(args.bandit_strategy))
            print(f"\nBandit Engine - Strategy: {args.bandit_strategy}")
            summary = system.bandit_engine.get_summary()
            print(f"  Total Arms: {summary['total_arms']}")
            print(f"  Trained Arms: {summary['trained_arms']}")
            print(f"  Impressions: {summary['total_impressions']}")
            print(f"  Conversions: {summary['total_conversions']}")
            print(f"  Overall Conversion Rate: {summary['overall_conversion_rate']:.2%}")

            print("\nBest Arms by Risk Level:")
            for risk_level, data in summary['best_arms_by_risk_level'].items():
                if data['best_arm']:
                    parts = data['best_arm'].split(":")
                    print(f"  {risk_level.upper()}: {parts[1]} via {parts[2]} (reward: {data['best_reward']:.3f})")

        elif args.mode == "stratified":
            if not use_stratified:
                print("Error: --no-stratified flag is set, cannot run stratified mode.")
                return

            summary = system.stratified_model.get_strata_summary()
            print(f"\nStratified Model Summary:")
            print(f"  Total Strata: {summary['total_strata']}")
            print(f"  Has Fallback: {summary['has_fallback']}")
            print("\n  Strata Details:")
            for name, data in summary.get('strata', {}).items():
                print(f"    {name:20s}: trained={data['is_trained']}, "
                     f"samples={data['train_samples']}, "
                     f"events={data['event_count']}, "
                     f"C-index={data['c_index']:.4f}")

        elif args.mode == "survival":
            print("\n" + "=" * 60)
            print("SURVIVAL CURVE COMPARISON MODE")
            print("=" * 60)
            
            fe = FeatureEngineering(use_spark=args.use_spark)
            users, events = fe.generate_synthetic_data(
                num_users=args.num_users,
                avg_events_per_user=int(args.num_events/args.num_users),
                churn_ratio=0.3
            )
            features = fe.extract_features_pandas(users, events)
            processed_features, metadata = fe.preprocess_features_pandas(features)
            
            import pandas as pd
            df_surv = pd.DataFrame(processed_features)
            
            print(f"\nFitting survival curves for {len(df_surv)} users...")
            surv_results = system.survival_comparator.fit_curves(
                df_surv, group_columns=["user_level", "region", "channel"]
            )
            
            for group_col, curves in surv_results.get("curves", {}).items():
                print(f"\n--- {group_col.upper()} ---")
                for name, curve in sorted(curves.items()):
                    print(f"  {name:15s}: median={curve['median_survival']:.0f}d, "
                          f"30d={curve.get('survival_at_30d', 0)*100:.0f}%, "
                          f"events={curve['num_events']}/{curve['num_samples']}")
            
            report = system.survival_comparator.generate_comparison_report()
            print(f"\nKey Insights:")
            for insight in report["key_insights"]:
                print(f"  - {insight}")
            
            fe.close()

        elif args.mode == "attribution":
            print("\n" + "=" * 60)
            print("TOUCHPOINT ATTRIBUTION ANALYSIS MODE")
            print("=" * 60)
            
            fe = FeatureEngineering(use_spark=args.use_spark)
            users, events = fe.generate_synthetic_data(
                num_users=args.num_users,
                avg_events_per_user=int(args.num_events/args.num_users),
                churn_ratio=0.3
            )
            
            user_ids_all = [u["user_id"] for u in users]
            group_assignments = system.attribution_analyzer.assign_control_groups(user_ids_all)
            
            import random
            channels = ["push", "email", "sms", "in_app"]
            actions = ["discount_offer", "personalized_recommendation", "winback_campaign"]
            channel_costs = {"push": 0.1, "email": 0.5, "sms": 1.0, "in_app": 0.05}
            
            print(f"\nGenerating synthetic touchpoints...")
            for i in range(500):
                uid = random.choice(user_ids_all)
                if group_assignments[uid] == "treatment":
                    channel = random.choices(channels, weights=[0.4, 0.3, 0.15, 0.15])[0]
                    action = random.choice(actions)
                    ts = time.time() - random.randint(0, 14) * 86400
                    
                    tp = system.attribution_analyzer.record_touchpoint(
                        user_id=uid, channel=channel, action_type=action,
                        timestamp=ts, cost=channel_costs[channel]
                    )
                    
                    if random.random() < 0.3:
                        system.attribution_analyzer.record_response(
                            user_id=uid, touchpoint_timestamp=tp.timestamp,
                            response_timestamp=tp.timestamp + random.randint(1, 72) * 3600
                        )
            
            churn_data = [{"user_id": u["user_id"], "churned": int(u.get("churned", False))} for u in users]
            
            print(f"\nAnalyzing treatment effects for {len(churn_data)} users...")
            attr_results = system.attribution_analyzer.analyze_treatment_effects(
                churn_data, group_assignments
            )
            
            overall = attr_results["overall"]
            print(f"\nOverall Results:")
            print(f"  Treatment: {overall['treatment_size']}, Control: {overall['control_size']}")
            print(f"  Churn rate - Treated: {overall['churn_rate_treated']*100:.1f}%")
            print(f"  Churn rate - Control: {overall['churn_rate_control']*100:.1f}%")
            print(f"  Uplift: {overall['uplift_absolute']*100:.2f}% (relative: {overall['uplift_relative']*100:.1f}%)")
            print(f"  Churn prevented: {overall['churn_prevented']}")
            
            print(f"\nChannel Performance:")
            for channel, data in sorted(
                attr_results["channel_attribution"].items(),
                key=lambda x: x[1]["uplift"], reverse=True
            ):
                print(f"  {channel.upper():8s}: uplift={data['uplift_percentage']:>7s}, "
                      f"ROI={data['roi_percentage']:>7s}, responses={data['responses']}")
            
            print(f"\nRecommendations:")
            for rec in attr_results["recommendations"][:5]:
                print(f"  [{rec['priority'].upper()}] {rec['action']}")
            
            fe.close()

        elif args.mode == "reason_analysis":
            print("\n" + "=" * 60)
            print("CHURN REASON ANALYSIS MODE")
            print("=" * 60)
            
            fe = FeatureEngineering(use_spark=args.use_spark)
            users, events = fe.generate_synthetic_data(
                num_users=args.num_users,
                avg_events_per_user=int(args.num_events/args.num_users),
                churn_ratio=0.3
            )
            
            import random
            feedback_templates = [
                ("pricing", "The subscription is too expensive for my budget."),
                ("product_issues", "The app keeps crashing on my device."),
                ("customer_service", "Support takes forever to respond to my issues."),
                ("billing_issues", "I was charged incorrectly on my last bill."),
                ("ux_problems", "The interface is confusing and hard to navigate."),
                ("competition", "I found a better service with more features."),
                ("feature_request", "Missing key features I need for my workflow."),
                ("reliability", "The service has been very unreliable lately."),
            ]
            
            ticket_categories = ["Technical", "Billing", "Feature Request", "Account"]
            user_ids_all = [u["user_id"] for u in users]
            
            print(f"\nGenerating synthetic feedback and tickets...")
            for i in range(300):
                uid = random.choice(user_ids_all)
                topic, content = feedback_templates[random.randint(0, len(feedback_templates)-1)]
                system.churn_reason_analyzer.add_feedback(
                    feedback_id=f"fb_{i:05d}", user_id=uid,
                    feedback_type=random.choice(["survey", "review", "direct"]),
                    content=content,
                    timestamp=time.time() - random.randint(0, 60) * 86400
                )
            
            for i in range(150):
                uid = random.choice(user_ids_all)
                category = random.choice(ticket_categories)
                created = time.time() - random.randint(0, 30) * 86400
                closed = created + random.randint(1, 72) * 3600 if random.random() < 0.7 else None
                _, desc = feedback_templates[random.randint(0, len(feedback_templates)-1)]
                
                system.churn_reason_analyzer.add_ticket(
                    ticket_id=f"ticket_{i:05d}", user_id=uid,
                    category=category, subcategory=category.lower().replace(" ", "_"),
                    description=desc,
                    priority=random.choice(["low", "medium", "high", "critical"]),
                    status=random.choice(["open", "closed", "pending"]),
                    created_at=created, closed_at=closed
                )
            
            churn_data = [
                {"user_id": u["user_id"], "churned": int(u.get("churned", False)),
                 "churn_time": u.get("churn_time", time.time()) if u.get("churned") else None}
                for u in users
            ]
            
            print(f"\nAnalyzing churn reasons for {len(churn_data)} users...")
            reason_results = system.churn_reason_analyzer.analyze_churn_reasons(churn_data)
            
            print(f"\nTop Churn Reasons:")
            for reason in reason_results["top_reasons"][:5]:
                print(f"  [{reason['category'].upper()}] {reason['reason_name']:20s}: "
                      f"users={reason['count']:3d}, churn={reason['churn_rate_percentage']:>4s}, "
                      f"risk={reason['elevated_risk']:>6s}, severity={reason['severity_label']}")
            
            if reason_results.get("trending_topics"):
                print(f"\nTrending Topics (past 2 weeks):")
                for trend in reason_results["trending_topics"][:5]:
                    growth = f"{trend['growth_rate']*100:.0f}%" if trend['growth_rate'] != float('inf') else "NEW"
                    print(f"  {trend['topic']:25s}: {trend['current_count']:3d} mentions (growth: {growth})")
            
            print(f"\nKey Insights:")
            for insight in reason_results["key_insights"]:
                print(f"  - {insight}")
            
            reason_report = system.churn_reason_analyzer.generate_churn_reason_report()
            print(f"\nRecommendations:")
            for rec in reason_report["recommendations"][:5]:
                print(f"  [{rec['priority'].upper()}] {rec['area']:20s}: {rec['action']}")
            
            fe.close()

    except Exception as e:
        logger.error(f"System error: {e}", exc_info=True)
        raise

    finally:
        system.stop()


if __name__ == "__main__":
    main()