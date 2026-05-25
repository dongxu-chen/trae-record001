import json
import os
import sys
import random
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from pyspark.sql import SparkSession, DataFrame
    from pyspark.sql import functions as F
    from pyspark.sql.types import (
        StructType, StructField, StringType, DoubleType, 
        LongType, IntegerType, TimestampType, MapType
    )
    from pyspark.ml.feature import (
        StringIndexer, OneHotEncoder, VectorAssembler, 
        MinMaxScaler, StandardScaler
    )
    from pyspark.ml import Pipeline
    SPARK_AVAILABLE = True
except ImportError:
    SPARK_AVAILABLE = False
    print("Warning: PySpark not available. Using fallback implementation.")

from common.logger import get_logger
from common.utils import (
    load_config,
    safe_divide,
    days_between,
    timestamp_to_datetime,
    datetime_to_timestamp,
    quantile,
    to_json_safe
)

logger = get_logger("SparkFeatureEngineering")


class FeatureEngineering:
    def __init__(self, use_spark: bool = True):
        self.config = load_config()
        self.spark_config = self.config["spark"]
        self.feature_config = self.config["features"]
        self.model_config = self.config["model"]
        
        self.use_spark = use_spark and SPARK_AVAILABLE
        self.spark = None
        
        if self.use_spark:
            self._init_spark()
        
        self.time_windows = self.feature_config["time_window_days"]
        self.event_types = self.feature_config["event_types"]
        self.aggregations = self.feature_config["aggregations"]
        
    def _init_spark(self):
        try:
            self.spark = (
                SparkSession.builder
                .master(self.spark_config["master"])
                .appName(self.spark_config["app_name"])
                .config("spark.executor.memory", self.spark_config["executor_memory"])
                .config("spark.driver.memory", self.spark_config["driver_memory"])
                .config("spark.sql.session.timeZone", "UTC")
                .getOrCreate()
            )
            logger.info("Spark session initialized successfully")
        except Exception as e:
            logger.warning(f"Failed to initialize Spark: {e}. Using fallback.")
            self.use_spark = False
    
    def generate_synthetic_data(self, num_users: int = 1000, 
                                avg_events_per_user: int = 50,
                                churn_ratio: float = 0.3) -> Tuple[List[Dict], List[Dict]]:
        logger.info(f"Generating synthetic data for {num_users} users...")
        
        regions = ["north", "south", "east", "west", "central"]
        channels = ["organic", "paid", "referral", "social", "email"]
        user_levels = ["new", "bronze", "silver", "gold", "platinum"]
        
        users = []
        events = []
        
        for user_idx in range(num_users):
            is_churned = random.random() < churn_ratio
            
            signup_days_ago = random.randint(30, 365)
            signup_date = datetime.now() - timedelta(days=signup_days_ago)
            
            user = {
                "user_id": f"user_{user_idx:06d}",
                "user_level": random.choice(user_levels),
                "region": random.choice(regions),
                "channel": random.choice(channels),
                "total_spend": round(random.uniform(0, 10000), 2),
                "signup_date": datetime_to_timestamp(signup_date),
                "churned": is_churned,
                "survival_days": 0
            }
            
            if is_churned:
                churn_days_after_signup = random.randint(7, signup_days_ago - 7)
                user["churn_date"] = datetime_to_timestamp(
                    signup_date + timedelta(days=churn_days_after_signup)
                )
                user["survival_days"] = churn_days_after_signup
                last_event_date = signup_date + timedelta(days=churn_days_after_signup - 1)
                num_events = min(avg_events_per_user, churn_days_after_signup * 2)
            else:
                user["churn_date"] = None
                user["survival_days"] = signup_days_ago
                last_event_date = datetime.now()
                num_events = avg_events_per_user
            
            users.append(user)
            
            event_dates = []
            current_date = signup_date
            while current_date <= last_event_date and len(event_dates) < num_events:
                if is_churned:
                    activity_decay = 1 - (len(event_dates) / num_events) * 0.8
                    if random.random() < activity_decay * 0.5:
                        event_dates.append(current_date)
                else:
                    if random.random() < 0.3:
                        event_dates.append(current_date)
                
                current_date += timedelta(days=random.randint(1, 7))
            
            for event_date in event_dates:
                event_type = random.choices(
                    self.event_types,
                    weights=[0.3, 0.1, 0.3, 0.2, 0.05, 0.05],
                    k=1
                )[0]
                
                event = {
                    "event_id": f"evt_{user_idx:06d}_{len(event_dates):04d}",
                    "user_id": user["user_id"],
                    "event_type": event_type,
                    "event_time": datetime_to_timestamp(event_date),
                    "user_profile": {
                        "user_level": user["user_level"],
                        "region": user["region"],
                        "channel": user["channel"],
                        "total_spend": user["total_spend"],
                        "signup_date": user["signup_date"]
                    },
                    "event_properties": {
                        "session_duration": random.randint(60, 3600) if event_type == "login" else 0,
                        "purchase_amount": round(random.uniform(10, 500), 2) if event_type == "purchase" else 0,
                        "error_code": random.choice([400, 404, 500]) if event_type == "error" else None
                    }
                }
                events.append(event)
        
        logger.info(f"Generated {len(users)} users and {len(events)} events")
        return users, events
    
    def save_synthetic_data(self, users: List[Dict], events: List[Dict], 
                          users_path: str, events_path: str):
        os.makedirs(os.path.dirname(users_path), exist_ok=True)
        os.makedirs(os.path.dirname(events_path), exist_ok=True)
        
        with open(users_path, "w", encoding="utf-8") as f:
            for user in users:
                f.write(to_json_safe(user) + "\n")
        
        with open(events_path, "w", encoding="utf-8") as f:
            for event in events:
                f.write(to_json_safe(event) + "\n")
        
        logger.info(f"Saved data to {users_path} and {events_path}")
    
    def load_data_pandas(self, users_path: str, events_path: str) -> Tuple[List[Dict], List[Dict]]:
        users = []
        events = []
        
        with open(users_path, "r", encoding="utf-8") as f:
            for line in f:
                user = json.loads(line.strip())
                users.append(user)
        
        with open(events_path, "r", encoding="utf-8") as f:
            for line in f:
                event = json.loads(line.strip())
                events.append(event)
        
        logger.info(f"Loaded {len(users)} users and {len(events)} events")
        return users, events
    
    def load_data_spark(self, users_path: str, events_path: str) -> Tuple["DataFrame", "DataFrame"]:
        if not self.use_spark:
            raise RuntimeError("Spark is not available")
        
        users_schema = StructType([
            StructField("user_id", StringType(), True),
            StructField("user_level", StringType(), True),
            StructField("region", StringType(), True),
            StructField("channel", StringType(), True),
            StructField("total_spend", DoubleType(), True),
            StructField("signup_date", DoubleType(), True),
            StructField("churned", IntegerType(), True),
            StructField("churn_date", DoubleType(), True),
            StructField("survival_days", IntegerType(), True)
        ])
        
        events_schema = StructType([
            StructField("event_id", StringType(), True),
            StructField("user_id", StringType(), True),
            StructField("event_type", StringType(), True),
            StructField("event_time", DoubleType(), True),
            StructField("user_profile", MapType(StringType(), StringType()), True),
            StructField("event_properties", MapType(StringType(), StringType()), True)
        ])
        
        users_df = self.spark.read.json(users_path, schema=users_schema)
        events_df = self.spark.read.json(events_path, schema=events_schema)
        
        logger.info(f"Loaded {users_df.count()} users and {events_df.count()} events")
        return users_df, events_df
    
    def extract_features_pandas(self, users: List[Dict], events: List[Dict]) -> List[Dict]:
        logger.info("Extracting features using pandas fallback...")
        
        user_events = defaultdict(list)
        for event in events:
            user_events[event["user_id"]].append(event)
        
        feature_list = []
        
        for user in users:
            user_id = user["user_id"]
            user_event_list = sorted(
                user_events.get(user_id, []), 
                key=lambda e: e["event_time"]
            )
            
            features = {
                "user_id": user_id,
                "duration": user["survival_days"],
                "event": 1 if user["churned"] else 0,
                "user_level": user["user_level"],
                "region": user["region"],
                "channel": user["channel"],
                "total_spend": user["total_spend"],
                "days_since_signup": user["survival_days"]
            }
            
            for window_days in self.time_windows:
                cutoff_date = datetime_to_timestamp(
                    datetime.now() - timedelta(days=window_days)
                )
                
                window_events = [
                    e for e in user_event_list 
                    if e["event_time"] >= cutoff_date
                ]
                
                prefix = f"window_{window_days}d"
                
                event_counts = defaultdict(int)
                total_session = 0
                total_purchase = 0
                error_count = 0
                
                for e in window_events:
                    event_counts[e["event_type"]] += 1
                    props = e.get("event_properties", {})
                    total_session += float(props.get("session_duration", 0) or 0)
                    total_purchase += float(props.get("purchase_amount", 0) or 0)
                    if e["event_type"] == "error":
                        error_count += 1
                
                features[f"{prefix}_total_events"] = len(window_events)
                features[f"{prefix}_login_count"] = event_counts.get("login", 0)
                features[f"{prefix}_purchase_count"] = event_counts.get("purchase", 0)
                features[f"{prefix}_view_count"] = event_counts.get("view", 0)
                features[f"{prefix}_click_count"] = event_counts.get("click", 0)
                features[f"{prefix}_error_count"] = error_count
                features[f"{prefix}_total_session"] = total_session
                features[f"{prefix}_total_purchase"] = total_purchase
                features[f"{prefix}_avg_session"] = safe_divide(
                    total_session, event_counts.get("login", 1)
                )
                features[f"{prefix}_avg_purchase"] = safe_divide(
                    total_purchase, event_counts.get("purchase", 1)
                )
                features[f"{prefix}_conversion_rate"] = safe_divide(
                    event_counts.get("purchase", 0),
                    event_counts.get("login", 1)
                )
                features[f"{prefix}_error_rate"] = safe_divide(
                    error_count, len(window_events)
                )
            
            if user_event_list:
                last_event = max(user_event_list, key=lambda e: e["event_time"])
                first_event = min(user_event_list, key=lambda e: e["event_time"])
                
                features["days_since_last_event"] = (
                    datetime_to_timestamp() - last_event["event_time"]
                ) / 86400
                features["days_between_first_last"] = (
                    last_event["event_time"] - first_event["event_time"]
                ) / 86400
                features["event_frequency"] = safe_divide(
                    len(user_event_list), features["days_between_first_last"] + 1
                )
                
                inter_event_times = []
                for i in range(1, len(user_event_list)):
                    diff = (user_event_list[i]["event_time"] - 
                            user_event_list[i-1]["event_time"]) / 86400
                    inter_event_times.append(diff)
                
                if inter_event_times:
                    features["avg_days_between_events"] = sum(inter_event_times) / len(inter_event_times)
                    features["std_days_between_events"] = (
                        sum((x - features["avg_days_between_events"]) ** 2 
                            for x in inter_event_times) / len(inter_event_times)
                    ) ** 0.5
                    features["median_days_between_events"] = quantile(inter_event_times, 0.5)
                else:
                    features["avg_days_between_events"] = 0
                    features["std_days_between_events"] = 0
                    features["median_days_between_events"] = 0
            else:
                features["days_since_last_event"] = user["survival_days"]
                features["days_between_first_last"] = 0
                features["event_frequency"] = 0
                features["avg_days_between_events"] = 0
                features["std_days_between_events"] = 0
                features["median_days_between_events"] = 0
            
            feature_list.append(features)
        
        logger.info(f"Extracted features for {len(feature_list)} users")
        return feature_list
    
    def extract_features_spark(self, users_df: "DataFrame", 
                               events_df: "DataFrame") -> "DataFrame":
        if not self.use_spark:
            raise RuntimeError("Spark is not available")
        
        logger.info("Extracting features using Spark...")
        
        reference_date = F.current_timestamp()
        
        for window_days in self.time_windows:
            window_start = reference_date - F.expr(f"INTERVAL {window_days} DAYS")
            
            window_df = events_df.filter(
                F.to_timestamp(F.col("event_time")) >= window_start
            )
            
            agg_exprs = [
                F.count("*").alias(f"window_{window_days}d_total_events"),
                F.sum(F.when(F.col("event_type") == "login", 1).otherwise(0)).alias(f"window_{window_days}d_login_count"),
                F.sum(F.when(F.col("event_type") == "purchase", 1).otherwise(0)).alias(f"window_{window_days}d_purchase_count"),
                F.sum(F.when(F.col("event_type") == "view", 1).otherwise(0)).alias(f"window_{window_days}d_view_count"),
                F.sum(F.when(F.col("event_type") == "click", 1).otherwise(0)).alias(f"window_{window_days}d_click_count"),
                F.sum(F.when(F.col("event_type") == "error", 1).otherwise(0)).alias(f"window_{window_days}d_error_count"),
                F.sum(F.col("event_properties.session_duration").cast(DoubleType())).alias(f"window_{window_days}d_total_session"),
                F.sum(F.col("event_properties.purchase_amount").cast(DoubleType())).alias(f"window_{window_days}d_total_purchase")
            ]
            
            window_agg = window_df.groupBy("user_id").agg(*agg_exprs)
            
            users_df = users_df.join(window_agg, on="user_id", how="left")
        
        event_stats = events_df.groupBy("user_id").agg(
            F.max("event_time").alias("last_event_time"),
            F.min("event_time").alias("first_event_time"),
            F.count("*").alias("total_events_count")
        )
        
        users_df = users_df.join(event_stats, on="user_id", how="left")
        
        users_df = users_df.withColumn(
            "days_since_last_event",
            F.datediff(reference_date, F.to_timestamp(F.col("last_event_time")))
        ).withColumn(
            "days_between_first_last",
            F.datediff(
                F.to_timestamp(F.col("last_event_time")),
                F.to_timestamp(F.col("first_event_time"))
            )
        ).withColumn(
            "event_frequency",
            F.col("total_events_count") / (F.col("days_between_first_last") + 1)
        ).withColumn(
            "duration",
            F.col("survival_days")
        ).withColumn(
            "event",
            F.col("churned").cast(IntegerType())
        )
        
        users_df = users_df.na.fill(0)
        
        logger.info(f"Extracted features for {users_df.count()} users")
        return users_df
    
    def preprocess_features_pandas(self, features: List[Dict]) -> Tuple[List[Dict], Dict]:
        logger.info("Preprocessing features...")
        
        from sklearn.preprocessing import StandardScaler, LabelEncoder
        import numpy as np
        
        feature_names = [k for k in features[0].keys() 
                        if k not in ["user_id", "duration", "event"]]
        
        numerical_features = []
        categorical_features = []
        
        for name in feature_names:
            values = [f[name] for f in features]
            if all(isinstance(v, (int, float)) for v in values):
                numerical_features.append(name)
            else:
                categorical_features.append(name)
        
        scaler = StandardScaler()
        
        numerical_values = np.array([
            [f[feat] for feat in numerical_features] for f in features
        ])
        
        scaled_numerical = scaler.fit_transform(numerical_values)
        
        label_encoders = {}
        categorical_encoded = {}
        
        for feat in categorical_features:
            le = LabelEncoder()
            values = [f[feat] for f in features]
            categorical_encoded[feat] = le.fit_transform(values)
            label_encoders[feat] = le
        
        processed = []
        for i, f in enumerate(features):
            processed_f = {
                "user_id": f["user_id"],
                "duration": f["duration"],
                "event": f["event"]
            }
            
            for j, feat in enumerate(numerical_features):
                processed_f[feat] = scaled_numerical[i, j]
            
            for feat in categorical_features:
                processed_f[feat] = categorical_encoded[feat][i]
            
            processed.append(processed_f)
        
        preprocessing_metadata = {
            "numerical_features": numerical_features,
            "categorical_features": categorical_features,
            "scaler": scaler,
            "label_encoders": label_encoders,
            "all_features": numerical_features + categorical_features
        }
        
        logger.info(f"Preprocessed {len(processed)} samples with {len(preprocessing_metadata['all_features'])} features")
        return processed, preprocessing_metadata
    
    def preprocess_features_spark(self, features_df: "DataFrame") -> Tuple["DataFrame", Dict]:
        if not self.use_spark:
            raise RuntimeError("Spark is not available")
        
        logger.info("Preprocessing features with Spark ML...")
        
        feature_cols = [c for c in features_df.columns 
                       if c not in ["user_id", "duration", "event", 
                                   "churned", "churn_date", "survival_days",
                                   "signup_date", "last_event_time", "first_event_time"]]
        
        categorical_cols = [c for c in feature_cols 
                          if dict(features_df.dtypes)[c] == "string"]
        numerical_cols = [c for c in feature_cols 
                         if c not in categorical_cols]
        
        stages = []
        
        for cat_col in categorical_cols:
            indexer = StringIndexer(
                inputCol=cat_col, 
                outputCol=f"{cat_col}_index",
                handleInvalid="keep"
            )
            encoder = OneHotEncoder(
                inputCol=f"{cat_col}_index",
                outputCol=f"{cat_col}_ohe"
            )
            stages.extend([indexer, encoder])
        
        ohe_cols = [f"{c}_ohe" for c in categorical_cols]
        assembler_input = numerical_cols + ohe_cols
        
        assembler = VectorAssembler(
            inputCols=assembler_input,
            outputCol="features_unscaled"
        )
        stages.append(assembler)
        
        scaler = StandardScaler(
            inputCol="features_unscaled",
            outputCol="features",
            withStd=True,
            withMean=True
        )
        stages.append(scaler)
        
        pipeline = Pipeline(stages=stages)
        pipeline_model = pipeline.fit(features_df)
        
        processed_df = pipeline_model.transform(features_df)
        
        preprocessing_metadata = {
            "numerical_features": numerical_cols,
            "categorical_features": categorical_cols,
            "pipeline_model": pipeline_model,
            "all_features": assembler_input
        }
        
        logger.info(f"Preprocessed features with {len(assembler_input)} dimensions")
        return processed_df, preprocessing_metadata
    
    def save_features(self, features: List[Dict], output_path: str):
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        import pandas as pd
        df = pd.DataFrame(features)
        df.to_csv(output_path, index=False, encoding="utf-8")
        
        logger.info(f"Saved features to {output_path}")
    
    def run_batch(self, users_path: Optional[str] = None, 
                  events_path: Optional[str] = None,
                  output_path: Optional[str] = None) -> Tuple[List[Dict], Dict]:
        if users_path is None:
            users_path = "./data/users.jsonl"
        if events_path is None:
            events_path = "./data/events.jsonl"
        if output_path is None:
            output_path = os.path.join(
                self.spark_config["feature_output_path"],
                f"features_{datetime.now().strftime('%Y%m%d')}.csv"
            )
        
        if not (os.path.exists(users_path) and os.path.exists(events_path)):
            logger.info("Data files not found. Generating synthetic data...")
            users, events = self.generate_synthetic_data(
                num_users=1000,
                avg_events_per_user=50
            )
            self.save_synthetic_data(users, events, users_path, events_path)
        else:
            users, events = self.load_data_pandas(users_path, events_path)
        
        features = self.extract_features_pandas(users, events)
        processed_features, metadata = self.preprocess_features_pandas(features)
        self.save_features(processed_features, output_path)
        
        return processed_features, metadata
    
    def close(self):
        if self.spark:
            self.spark.stop()
            logger.info("Spark session stopped")


def main():
    fe = FeatureEngineering(use_spark=False)
    
    logger.info("1. Generate synthetic data")
    logger.info("2. Extract features from existing data")
    logger.info("3. Run full batch pipeline")
    
    choice = input("Enter your choice (1-3): ").strip()
    
    if choice == "1":
        num_users = int(input("Enter number of users: "))
        avg_events = int(input("Enter average events per user: "))
        
        users, events = fe.generate_synthetic_data(
            num_users=num_users,
            avg_events_per_user=avg_events
        )
        
        fe.save_synthetic_data(users, events, "./data/users.jsonl", "./data/events.jsonl")
        
        churned_count = sum(1 for u in users if u["churned"])
        logger.info(f"Generated {len(users)} users ({churned_count} churned, "
                   f"{churned_count/len(users)*100:.1f}%) and {len(events)} events")
    
    elif choice == "2":
        users, events = fe.load_data_pandas("./data/users.jsonl", "./data/events.jsonl")
        features = fe.extract_features_pandas(users, events)
        
        output_path = "./data/features_latest.csv"
        fe.save_features(features, output_path)
        
        logger.info(f"Sample features for first user:")
        for k, v in sorted(features[0].items())[:20]:
            logger.info(f"  {k}: {v}")
    
    elif choice == "3":
        features, metadata = fe.run_batch()
        
        logger.info(f"Features shape: {len(features)} samples, {len(metadata['all_features'])} features")
        logger.info(f"Numerical features: {metadata['numerical_features'][:5]}...")
        logger.info(f"Categorical features: {metadata['categorical_features']}")
        
        events = sum(1 for f in features if f["event"] == 1)
        logger.info(f"Churned samples: {events}/{len(features)} ({events/len(features)*100:.1f}%)")
    
    fe.close()


if __name__ == "__main__":
    main()
