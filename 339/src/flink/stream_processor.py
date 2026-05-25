import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Callable, Tuple
from collections import defaultdict, deque
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from common.logger import get_logger
from common.utils import (
    load_config,
    parse_json_safe,
    to_json_safe,
    safe_divide,
    days_between,
    timestamp_to_datetime
)

logger = get_logger("FlinkStreamProcessor")

class UserEventAggregator:
    def __init__(self, time_windows: List[int]):
        self.time_windows = time_windows
        self.user_events: Dict[str, deque] = defaultdict(deque)
        self.user_profiles: Dict[str, Dict] = {}
        self.max_window_seconds = max(time_windows) * 24 * 3600
        
    def add_event(self, event: Dict) -> None:
        user_id = event["user_id"]
        
        if "user_profile" in event:
            self.user_profiles[user_id] = event["user_profile"]
        
        self.user_events[user_id].append(event)
        
        self._cleanup_old_events(user_id)
    
    def _cleanup_old_events(self, user_id: str) -> None:
        current_time = time.time()
        events = self.user_events[user_id]
        
        while events and (current_time - events[0]["event_time"]) > self.max_window_seconds:
            events.popleft()
    
    def get_user_features(self, user_id: str) -> Dict:
        if user_id not in self.user_events or not self.user_events[user_id]:
            return {}
        
        events = list(self.user_events[user_id])
        profile = self.user_profiles.get(user_id, {})
        current_time = time.time()
        
        features = {
            "user_id": user_id,
            "last_updated": current_time
        }
        
        if profile:
            features.update({
                f"profile_{k}": v for k, v in profile.items()
            })
        
        for window_days in self.time_windows:
            window_seconds = window_days * 24 * 3600
            window_events = [
                e for e in events 
                if (current_time - e["event_time"]) <= window_seconds
            ]
            
            prefix = f"window_{window_days}d"
            
            event_type_counts = defaultdict(int)
            total_session_duration = 0
            total_purchase_amount = 0
            error_count = 0
            
            for e in window_events:
                et = e["event_type"]
                event_type_counts[et] += 1
                
                props = e.get("event_properties", {})
                total_session_duration += props.get("session_duration", 0)
                total_purchase_amount += props.get("purchase_amount", 0)
                
                if et == "error":
                    error_count += 1
            
            features[f"{prefix}_total_events"] = len(window_events)
            features[f"{prefix}_unique_days"] = len(set(
                timestamp_to_datetime(e["event_time"]).date() 
                for e in window_events
            ))
            
            for et in ["login", "purchase", "view", "click", "logout", "error"]:
                features[f"{prefix}_event_{et}_count"] = event_type_counts.get(et, 0)
            
            features[f"{prefix}_total_session_duration"] = total_session_duration
            features[f"{prefix}_avg_session_duration"] = safe_divide(
                total_session_duration, event_type_counts.get("login", 1)
            )
            features[f"{prefix}_total_purchase_amount"] = total_purchase_amount
            features[f"{prefix}_avg_purchase_amount"] = safe_divide(
                total_purchase_amount, event_type_counts.get("purchase", 1)
            )
            features[f"{prefix}_error_count"] = error_count
            features[f"{prefix}_error_rate"] = safe_divide(
                error_count, len(window_events)
            )
            
            purchase_count = event_type_counts.get("purchase", 0)
            login_count = event_type_counts.get("login", 0)
            features[f"{prefix}_conversion_rate"] = safe_divide(purchase_count, login_count)
        
        if events:
            last_event_time = max(e["event_time"] for e in events)
            first_event_time = min(e["event_time"] for e in events)
            
            features["days_since_last_event"] = (current_time - last_event_time) / 86400
            features["days_since_first_event"] = (current_time - first_event_time) / 86400
            features["event_frequency"] = safe_divide(
                len(events), features["days_since_first_event"] + 1
            )
        
        if "signup_date" in profile:
            features["days_since_signup"] = days_between(
                timestamp_to_datetime(profile["signup_date"]),
                datetime.now()
            )
        
        return features
    
    def get_all_user_features(self) -> List[Dict]:
        return [
            self.get_user_features(user_id)
            for user_id in self.user_events.keys()
        ]


class FlinkStreamProcessor:
    def __init__(self):
        self.config = load_config()
        self.flink_config = self.config["flink"]
        self.kafka_config = self.config["kafka"]
        self.feature_config = self.config["features"]
        
        self.parallelism = self.flink_config["parallelism"]
        self.checkpoint_interval = self.flink_config["checkpoint_interval"]
        
        self.aggregator = UserEventAggregator(
            self.feature_config["time_window_days"]
        )
        
        self.risk_callbacks: List[Callable] = []
        self.processed_count = 0
        self.last_checkpoint_time = time.time()
        
        self._init_state_store()
    
    def _init_state_store(self):
        self.state = {
            "user_sessions": defaultdict(dict),
            "window_aggregates": defaultdict(dict),
            "metrics": {
                "total_events": 0,
                "events_per_second": 0,
                "window_start": time.time()
            }
        }
    
    def register_risk_callback(self, callback: Callable[[Dict], None]):
        self.risk_callbacks.append(callback)
    
    def process_event(self, event: Dict) -> Optional[Dict]:
        try:
            event = self._validate_event(event)
            if not event:
                return None
            
            self.processed_count += 1
            self.state["metrics"]["total_events"] += 1
            
            enriched_event = self._enrich_event(event)
            
            self.aggregator.add_event(enriched_event)
            
            features = self.aggregator.get_user_features(event["user_id"])
            
            if features and self.processed_count % 100 == 0:
                self._checkpoint()
            
            result = {
                "event": enriched_event,
                "features": features,
                "processing_time": time.time()
            }
            
            for callback in self.risk_callbacks:
                try:
                    callback(result)
                except Exception as e:
                    logger.error(f"Error in callback: {e}")
            
            return result
            
        except Exception as e:
            logger.error(f"Error processing event: {e}")
            return None
    
    def _validate_event(self, event: Dict) -> Optional[Dict]:
        required = ["event_id", "user_id", "event_type", "event_time"]
        for field in required:
            if field not in event:
                logger.warning(f"Missing field {field} in event")
                return None
        
        return event
    
    def _enrich_event(self, event: Dict) -> Dict:
        enriched = event.copy()
        
        enriched["processing_timestamp"] = time.time()
        
        event_type = event["event_type"]
        
        if event_type == "login":
            user_id = event["user_id"]
            self.state["user_sessions"][user_id] = {
                "start_time": event["event_time"],
                "last_activity": event["event_time"],
                "events_count": 1
            }
        elif event_type == "logout":
            user_id = event["user_id"]
            session = self.state["user_sessions"].get(user_id, {})
            if session:
                session_duration = event["event_time"] - session.get("start_time", event["event_time"])
                enriched["session_duration_calculated"] = session_duration
        
        enriched["is_weekend"] = timestamp_to_datetime(
            event["event_time"]
        ).weekday() >= 5
        
        enriched["hour_of_day"] = timestamp_to_datetime(
            event["event_time"]
        ).hour
        
        return enriched
    
    def _checkpoint(self):
        current_time = time.time()
        elapsed = current_time - self.state["metrics"]["window_start"]
        
        self.state["metrics"]["events_per_second"] = (
            self.state["metrics"]["total_events"] / elapsed if elapsed > 0 else 0
        )
        
        if current_time - self.last_checkpoint_time >= self.checkpoint_interval / 1000:
            logger.info(f"Checkpoint - Processed: {self.processed_count}, "
                       f"EPS: {self.state['metrics']['events_per_second']:.2f}")
            self.last_checkpoint_time = current_time
    
    def process_batch(self, events: List[Dict]) -> List[Dict]:
        results = []
        for event in events:
            result = self.process_event(event)
            if result:
                results.append(result)
        return results
    
    def get_user_risk_data(self, user_id: str) -> Dict:
        features = self.aggregator.get_user_features(user_id)
        
        return {
            "user_id": user_id,
            "features": features,
            "active_session": self.state["user_sessions"].get(user_id),
            "risk_score": None,
            "risk_level": None,
            "churn_probability": None,
            "expected_days_to_churn": None
        }
    
    def get_metrics(self) -> Dict:
        current_time = time.time()
        elapsed = current_time - self.state["metrics"]["window_start"]
        
        return {
            "total_events_processed": self.processed_count,
            "active_users": len(self.aggregator.user_events),
            "events_per_second": (
                self.processed_count / elapsed if elapsed > 0 else 0
            ),
            "uptime_seconds": elapsed,
            "processed_events": self.state["metrics"]["total_events"]
        }
    
    def get_high_risk_users(self, threshold_days: int = 7) -> List[str]:
        high_risk = []
        current_time = time.time()
        
        for user_id, events in self.aggregator.user_events.items():
            if not events:
                continue
            
            last_event = max(events, key=lambda e: e["event_time"])
            days_since = (current_time - last_event["event_time"]) / 86400
            
            if days_since >= threshold_days:
                high_risk.append(user_id)
        
        return high_risk
    
    def export_features(self, output_path: str) -> None:
        import csv
        
        features_list = self.aggregator.get_all_user_features()
        
        if not features_list:
            logger.warning("No features to export")
            return
        
        fieldnames = sorted(set().union(*[f.keys() for f in features_list]))
        
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        with open(output_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(features_list)
        
        logger.info(f"Exported features for {len(features_list)} users to {output_path}")


class StreamProcessingJob:
    def __init__(self, kafka_consumer, risk_model=None, redis_manager=None):
        self.config = load_config()
        self.processor = FlinkStreamProcessor()
        self.consumer = kafka_consumer
        self.risk_model = risk_model
        self.redis_manager = redis_manager
        self.running = False
        
        self.processor.register_risk_callback(self._risk_callback)
    
    def _risk_callback(self, result: Dict):
        if self.risk_model and result["features"]:
            try:
                prediction = self.risk_model.predict(result["features"])
                
                result.update(prediction)
                
                if self.redis_manager:
                    self.redis_manager.store_risk_score(
                        result["event"]["user_id"],
                        prediction
                    )
                    
                    if prediction.get("risk_level") == "high":
                        self.redis_manager.tag_high_risk_user(
                            result["event"]["user_id"],
                            prediction
                        )
                
                logger.debug(f"User {result['event']['user_id']} - "
                            f"Risk: {prediction.get('risk_level')}, "
                            f"Prob: {prediction.get('churn_probability', 0):.4f}, "
                            f"Days: {prediction.get('expected_days_to_churn', 0):.1f}")
                            
            except Exception as e:
                logger.error(f"Error in risk prediction: {e}")
    
    def start(self, batch_size: int = 100):
        logger.info("Starting stream processing job")
        self.running = True
        
        try:
            while self.running:
                events = self.consumer.poll(timeout_ms=1000, max_records=batch_size)
                
                if events:
                    results = self.processor.process_batch(events)
                    
                    if self.redis_manager:
                        for result in results:
                            if result["features"]:
                                self.redis_manager.store_user_features(
                                    result["event"]["user_id"],
                                    result["features"]
                                )
                    
                    processed = len(results)
                    if processed > 0:
                        logger.debug(f"Processed {processed} events")
                        
        except KeyboardInterrupt:
            logger.info("Stopping stream processing job")
        finally:
            self.stop()
    
    def stop(self):
        self.running = False
        metrics = self.processor.get_metrics()
        logger.info(f"Stream processing stopped. Metrics: {metrics}")


def main():
    from messaging.event_consumer import UserEventConsumer
    
    consumer = UserEventConsumer()
    consumer.connect(auto_offset_reset="latest")
    
    job = StreamProcessingJob(consumer)
    
    logger.info("1. Process stream and show metrics")
    logger.info("2. Process events and export features")
    logger.info("3. Show high risk users")
    
    choice = input("Enter your choice (1-3): ").strip()
    
    if choice == "1":
        try:
            count = 0
            while True:
                events = consumer.poll(timeout_ms=1000)
                if events:
                    job.processor.process_batch(events)
                    count += len(events)
                    
                    if count % 100 == 0:
                        metrics = job.processor.get_metrics()
                        print(f"\rProcessed: {metrics['total_events_processed']}, "
                              f"Users: {metrics['active_users']}, "
                              f"EPS: {metrics['events_per_second']:.2f}", end="")
        except KeyboardInterrupt:
            print()
    elif choice == "2":
        count = 0
        target = int(input("Enter number of events to process: "))
        
        while count < target:
            events = consumer.poll(timeout_ms=1000)
            if events:
                job.processor.process_batch(events)
                count += len(events)
                print(f"\rProcessed {count}/{target} events", end="")
        
        print()
        output_path = "./data/features_realtime.csv"
        job.processor.export_features(output_path)
    elif choice == "3":
        threshold = int(input("Enter inactivity threshold (days): "))
        
        count = 0
        target = 1000
        logger.info(f"Processing {target} events to build user profile...")
        
        while count < target:
            events = consumer.poll(timeout_ms=1000)
            if events:
                job.processor.process_batch(events)
                count += len(events)
        
        high_risk = job.processor.get_high_risk_users(threshold)
        logger.info(f"Found {len(high_risk)} high risk users (inactive > {threshold} days)")
        
        for i, user_id in enumerate(high_risk[:10]):
            data = job.processor.get_user_risk_data(user_id)
            print(f"{i+1}. {user_id}: days_since_last={data['features'].get('days_since_last_event', 0):.1f}")
    
    consumer.close()


if __name__ == "__main__":
    main()
