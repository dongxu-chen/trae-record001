import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from collections import defaultdict, deque
from dataclasses import dataclass, field
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    import numpy as np
    import pandas as pd
    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False

from common.logger import get_logger
from common.utils import load_config, to_json_safe, parse_json_safe

logger = get_logger("FeatureWindowAligner")


@dataclass
class WindowConfig:
    window_days: int
    window_name: str
    feature_prefix: str
    training_window_match: bool = True
    decay_factor: float = 1.0


@dataclass
class FeatureMetadata:
    name: str
    window_days: int
    calculation_method: str
    training_used: bool
    importance: float = 0.0
    last_calculated: str = ""


class SlidingWindowFeatureExtractor:
    def __init__(self, window_days: List[int] = None):
        self.window_days = window_days or [1, 7, 14, 30]
        self.window_configs: Dict[int, WindowConfig] = {}
        
        for days in self.window_days:
            self.window_configs[days] = WindowConfig(
                window_days=days,
                window_name=f"{days}d",
                feature_prefix=f"window_{days}d_"
            )
        
        self.user_events: Dict[str, deque] = defaultdict(deque)
        self.user_profiles: Dict[str, Dict] = {}
        self.max_history_days = max(self.window_days) * 2
        
        self.event_counters = {
            "login": defaultdict(lambda: defaultdict(int)),
            "purchase": defaultdict(lambda: defaultdict(int)),
            "view": defaultdict(lambda: defaultdict(int)),
            "click": defaultdict(lambda: defaultdict(int)),
            "error": defaultdict(lambda: defaultdict(int)),
            "session_duration": defaultdict(lambda: defaultdict(float)),
            "purchase_amount": defaultdict(lambda: defaultdict(float)),
        }
        
        logger.info(f"SlidingWindowFeatureExtractor initialized with windows: {self.window_days}")

    def add_event(self, event: Dict) -> None:
        user_id = event.get("user_id", "")
        if not user_id:
            return

        event_time = event.get("event_time", time.time())
        if isinstance(event_time, str):
            try:
                event_time = datetime.fromisoformat(event_time).timestamp()
            except Exception:
                event_time = time.time()

        event_type = event.get("event_type", "")
        event_props = event.get("event_properties", {})

        if user_id not in self.user_events:
            self.user_events[user_id] = deque(maxlen=5000)

        self.user_events[user_id].append({
            "time": event_time,
            "type": event_type,
            "duration": event_props.get("session_duration", 0),
            "amount": event_props.get("purchase_amount", 0)
        })

        for window_days in self.window_days:
            window_start = event_time - window_days * 86400
            while self.user_events[user_id] and self.user_events[user_id][0]["time"] < window_start:
                self.user_events[user_id].popleft()

        if "user_profile" in event:
            self.user_profiles[user_id] = event["user_profile"]

        self._update_counters(user_id, event_time)

    def _update_counters(self, user_id: str, current_time: float) -> None:
        for window_days in self.window_days:
            window_start = current_time - window_days * 86400

            counters = {k: defaultdict(float) for k in self.event_counters}

            for ev in self.user_events.get(user_id, []):
                if ev["time"] >= window_start:
                    day_bucket = int((ev["time"] - window_start) / 86400)
                    counters[ev["type"]][day_bucket] += 1 if ev["type"] in ["login", "purchase", "view", "click", "error"] else 0
                    if ev["type"] == "login":
                        counters["session_duration"][day_bucket] += ev["duration"]
                    if ev["type"] == "purchase":
                        counters["purchase_amount"][day_bucket] += ev["amount"]

            self.event_counters["login"][user_id][window_days] = sum(counters["login"].values())
            self.event_counters["purchase"][user_id][window_days] = sum(counters["purchase"].values())
            self.event_counters["view"][user_id][window_days] = sum(counters["view"].values())
            self.event_counters["click"][user_id][window_days] = sum(counters["click"].values())
            self.event_counters["error"][user_id][window_days] = sum(counters["error"].values())
            self.event_counters["session_duration"][user_id][window_days] = sum(counters["session_duration"].values())
            self.event_counters["purchase_amount"][user_id][window_days] = sum(counters["purchase_amount"].values())

    def extract_user_features(self, user_id: str, current_time: Optional[float] = None) -> Dict:
        if current_time is None:
            current_time = time.time()

        features = {}
        profile = self.user_profiles.get(user_id, {})

        for window_days in self.window_days:
            prefix = f"window_{window_days}d_"

            login_count = self.event_counters["login"].get(user_id, {}).get(window_days, 0)
            purchase_count = self.event_counters["purchase"].get(user_id, {}).get(window_days, 0)
            view_count = self.event_counters["view"].get(user_id, {}).get(window_days, 0)
            click_count = self.event_counters["click"].get(user_id, {}).get(window_days, 0)
            error_count = self.event_counters["error"].get(user_id, {}).get(window_days, 0)
            total_events = login_count + purchase_count + view_count + click_count + error_count

            total_session = self.event_counters["session_duration"].get(user_id, {}).get(window_days, 0)
            total_purchase = self.event_counters["purchase_amount"].get(user_id, {}).get(window_days, 0)

            features[f"{prefix}total_events"] = total_events
            features[f"{prefix}login_count"] = login_count
            features[f"{prefix}purchase_count"] = purchase_count
            features[f"{prefix}view_count"] = view_count
            features[f"{prefix}click_count"] = click_count
            features[f"{prefix}error_count"] = error_count
            features[f"{prefix}error_rate"] = error_count / max(total_events, 1)
            features[f"{prefix}total_session"] = total_session
            features[f"{prefix}avg_session"] = total_session / max(login_count, 1)
            features[f"{prefix}total_purchase"] = total_purchase
            features[f"{prefix}avg_purchase"] = total_purchase / max(purchase_count, 1)
            features[f"{prefix}conversion_rate"] = purchase_count / max(login_count, 1)
            features[f"{prefix}click_through_rate"] = click_count / max(view_count, 1)

        last_event_time = 0
        for ev in self.user_events.get(user_id, []):
            if ev["time"] > last_event_time:
                last_event_time = ev["time"]

        days_since_last = (current_time - last_event_time) / 86400 if last_event_time > 0 else 30
        features["days_since_last_event"] = min(days_since_last, 60)

        total_events_30d = features.get("window_30d_total_events", 0)
        features["event_frequency"] = total_events_30d / 30.0

        if profile:
            signup_date = profile.get("signup_date", current_time)
            if isinstance(signup_date, (int, float)):
                features["days_since_signup"] = (current_time - signup_date) / 86400
            else:
                features["days_since_signup"] = 180

            total_spend = profile.get("total_spend", 0)
            features["total_spend"] = total_spend

            if total_events_30d > 0:
                first_event_time = min(ev["time"] for ev in self.user_events.get(user_id, []))
                features["days_between_first_last"] = (last_event_time - first_event_time) / 86400 if last_event_time > first_event_time else 0
            else:
                features["days_between_first_last"] = 0

            user_level = profile.get("user_level", "new")
            level_map = {"new": 0, "bronze": 1, "silver": 2, "gold": 3, "platinum": 4}
            if isinstance(user_level, str):
                features["user_level"] = level_map.get(user_level, 0)
            else:
                features["user_level"] = user_level

            region = profile.get("region", "unknown")
            region_map = {"north": 0, "south": 1, "east": 2, "west": 3, "central": 4}
            features["region"] = region_map.get(region, 0)

            channel = profile.get("channel", "organic")
            channel_map = {"organic": 0, "paid": 1, "referral": 2, "social": 3, "email": 4}
            features["channel"] = channel_map.get(channel, 0)

        features["user_id"] = user_id
        return features

    def batch_extract(self, user_ids: List[str]) -> Dict[str, Dict]:
        results = {}
        for user_id in user_ids:
            results[user_id] = self.extract_user_features(user_id)
        return results

    def get_metrics(self) -> Dict:
        return {
            "total_users_tracked": len(self.user_events),
            "total_events_tracked": sum(len(events) for events in self.user_events.values()),
            "windows": self.window_days,
            "max_history_days": self.max_history_days
        }


class FeatureWindowAligner:
    def __init__(self, cache_manager=None):
        self.config = load_config()
        self.cache = cache_manager
        
        self.model_config = self.config.get("model", {})
        self.prediction_window = self.model_config.get("prediction_window_days", 30)
        self.feature_windows = self.config.get("features", {}).get("time_windows", [1, 7, 14, 30])
        
        self.extractor = SlidingWindowFeatureExtractor(self.feature_windows)
        
        self.training_window_config: Dict[str, Dict] = {}
        self._load_training_config()
        
        self.alignment_report: Dict[str, Any] = {}
        
        logger.info(f"FeatureWindowAligner initialized. Prediction window: {self.prediction_window}d, Feature windows: {self.feature_windows}")

    def _load_training_config(self):
        model_path = self.model_config.get("model_path", "./models/cox_model.pkl")
        base, ext = os.path.splitext(model_path)
        config_path = f"{base}_feature_config.json"
        
        if os.path.exists(config_path):
            try:
                with open(config_path, "r") as f:
                    self.training_window_config = json.load(f)
                logger.info(f"Loaded training feature config from {config_path}")
            except Exception as e:
                logger.warning(f"Failed to load feature config: {e}")

    def _save_training_config(self, feature_columns: List[str], feature_metadata: Dict):
        model_path = self.model_config.get("model_path", "./models/cox_model.pkl")
        base, ext = os.path.splitext(model_path)
        config_path = f"{base}_feature_config.json"
        
        os.makedirs(os.path.dirname(config_path), exist_ok=True)
        
        config = {
            "training_timestamp": datetime.now().isoformat(),
            "prediction_window_days": self.prediction_window,
            "feature_windows": self.feature_windows,
            "feature_columns": feature_columns,
            "feature_metadata": feature_metadata,
            "window_alignment": {
                "model_trained_on": [f"window_{d}d" for d in self.feature_windows],
                "prediction_window": f"{self.prediction_window}d",
                "realtime_windows": [f"window_{d}d" for d in self.feature_windows]
            }
        }
        
        try:
            with open(config_path, "w") as f:
                json.dump(config, f, indent=2, default=str)
            logger.info(f"Saved training feature config to {config_path}")
        except Exception as e:
            logger.warning(f"Failed to save feature config: {e}")

    def add_event(self, event: Dict):
        self.extractor.add_event(event)

    def extract_features(self, user_id: str) -> Dict:
        return self.extractor.extract_user_features(user_id)

    def batch_extract(self, user_ids: List[str]) -> Dict[str, Dict]:
        return self.extractor.batch_extract(user_ids)

    def check_window_alignment(self, current_features: Dict) -> Dict:
        report = {
            "aligned": True,
            "mismatches": [],
            "warnings": [],
            "info": []
        }

        if not self.training_window_config:
            report["warnings"].append({
                "type": "no_training_config",
                "message": "No training config found. Run training first."
            })
            report["aligned"] = False
            return report

        training_columns = set(self.training_window_config.get("feature_columns", []))
        current_columns = set(current_features.keys())

        missing_in_current = training_columns - current_columns
        extra_in_current = current_columns - training_columns

        if missing_in_current:
            report["mismatches"].append({
                "type": "missing_features",
                "features": list(missing_in_current),
                "count": len(missing_in_current)
            })
            report["aligned"] = False

        if extra_in_current:
            report["warnings"].append({
                "type": "extra_features",
                "features": list(extra_in_current)[:20],
                "count": len(extra_in_current),
                "message": "These features were not in training data"
            })

        training_windows = set(self.training_window_config.get("feature_windows", []))
        current_windows = set(self.feature_windows)
        
        if training_windows != current_windows:
            report["warnings"].append({
                "type": "window_mismatch",
                "training_windows": list(training_windows),
                "current_windows": list(current_windows),
                "message": "Feature windows differ from training"
            })

        pred_window = self.training_window_config.get("prediction_window_days", 30)
        if pred_window != self.prediction_window:
            report["warnings"].append({
                "type": "prediction_window_mismatch",
                "training_prediction_window": pred_window,
                "current_prediction_window": self.prediction_window,
                "message": "Prediction window has changed since training"
            })

        self.alignment_report = report
        return report

    def align_features(self, features: Dict) -> Dict:
        if not self.training_window_config:
            return features

        training_columns = self.training_window_config.get("feature_columns", [])
        
        aligned_features = {}
        for col in training_columns:
            aligned_features[col] = features.get(col, 0)

        for key, value in features.items():
            if key not in aligned_features and key not in ["user_id", "duration", "event"]:
                aligned_features[key] = value

        return aligned_features

    def generate_window_report(self) -> Dict:
        return {
            "extractor_metrics": self.extractor.get_metrics(),
            "training_config": {
                "available": bool(self.training_window_config),
                "prediction_window_days": self.training_window_config.get("prediction_window_days", None),
                "feature_windows": self.training_window_config.get("feature_windows", []),
                "num_features": len(self.training_window_config.get("feature_columns", [])),
                "trained_at": self.training_window_config.get("training_timestamp", None)
            },
            "current_config": {
                "prediction_window_days": self.prediction_window,
                "feature_windows": self.feature_windows,
                "num_extractable_features": len(self.feature_windows) * 13 + 5
            },
            "alignment": self.alignment_report
        }

    def update_training_metadata(self, feature_columns: List[str], feature_importance: Dict = None):
        feature_metadata = {}
        for col in feature_columns:
            window_days = None
            for d in self.feature_windows:
                if col.startswith(f"window_{d}d_"):
                    window_days = d
                    break
            
            feature_metadata[col] = {
                "window_days": window_days,
                "used_in_training": True,
                "importance": feature_importance.get(col, {}).get("importance", 0) if feature_importance else 0
            }

        self._save_training_config(feature_columns, feature_metadata)
        logger.info(f"Updated training metadata for {len(feature_columns)} features")


def main():
    aligner = FeatureWindowAligner()

    print("=" * 60)
    print("FEATURE WINDOW ALIGNER")
    print("=" * 60)

    print("\n" + "-" * 60)
    print("SIMULATING USER EVENT STREAM")
    print("-" * 60)

    user_ids = [f"window_user_{i:03d}" for i in range(10)]
    event_types = ["login", "purchase", "view", "click", "error"]

    import random
    for i in range(200):
        event = {
            "event_id": f"evt_{i}",
            "user_id": random.choice(user_ids),
            "event_type": random.choices(event_types, weights=[0.3, 0.1, 0.3, 0.2, 0.1])[0],
            "event_time": time.time() - random.randint(0, 30) * 86400,
            "event_properties": {
                "session_duration": random.randint(60, 3600),
                "purchase_amount": round(random.uniform(10, 500), 2)
            },
            "user_profile": {
                "user_level": random.choice(["new", "bronze", "silver", "gold", "platinum"]),
                "total_spend": random.uniform(0, 5000),
                "signup_date": time.time() - random.randint(30, 365) * 86400,
                "region": random.choice(["north", "south", "east", "west"]),
                "channel": random.choice(["organic", "paid", "referral"])
            }
        }
        aligner.add_event(event)

    print(f"Added 200 events for {len(user_ids)} users")

    print("\n" + "-" * 60)
    print("EXTRACTING SLIDING WINDOW FEATURES")
    print("-" * 60)

    for uid in user_ids[:3]:
        features = aligner.extract_features(uid)
        print(f"\nUser: {uid}")
        print(f"  1d events: {features.get('window_1d_total_events', 0)}")
        print(f"  7d events: {features.get('window_7d_total_events', 0)}")
        print(f"  14d events: {features.get('window_14d_total_events', 0)}")
        print(f"  30d events: {features.get('window_30d_total_events', 0)}")
        print(f"  Days since last: {features.get('days_since_last_event', 0):.1f}")
        print(f"  Event frequency: {features.get('event_frequency', 0):.4f}")
        print(f"  Total features: {len(features)}")

    print("\n" + "-" * 60)
    print("WINDOW ALIGNMENT REPORT")
    print("-" * 60)

    sample_features = aligner.extract_features(user_ids[0])
    alignment = aligner.check_window_alignment(sample_features)
    print(f"\n  Aligned: {alignment['aligned']}")
    for w in alignment.get("warnings", []):
        print(f"  Warning: {w.get('message', w)}")

    report = aligner.generate_window_report()
    print(f"\n  Training config available: {report['training_config']['available']}")
    print(f"  Current prediction window: {report['current_config']['prediction_window_days']}d")
    print(f"  Feature windows: {report['current_config']['feature_windows']}")
    print(f"  Total extractable features: {report['current_config']['num_extractable_features']}")

    print("\n" + "-" * 60)
    print("UPDATING TRAINING METADATA")
    print("-" * 60)

    sample_columns = [f"window_{d}d_{metric}" for d in [1, 7, 14, 30] 
                      for metric in ["total_events", "login_count", "purchase_count", 
                                      "error_rate", "total_session", "total_purchase"]]
    sample_columns.extend(["days_since_last_event", "event_frequency", "days_since_signup",
                          "user_level", "total_spend", "region"])

    feature_importance = {col: {"importance": random.random()} for col in sample_columns}
    aligner.update_training_metadata(sample_columns, feature_importance)
    print(f"Updated training metadata for {len(sample_columns)} features")

    alignment = aligner.check_window_alignment(sample_features)
    print(f"After update - Aligned: {alignment['aligned']}")

    print("\n" + "=" * 60)


if __name__ == "__main__":
    main()