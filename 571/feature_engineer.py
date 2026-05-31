import pandas as pd
import numpy as np
from datetime import datetime
from typing import Dict, List, Optional
from sklearn.preprocessing import LabelEncoder, StandardScaler
import joblib
import os


class FeatureEngineer:
    def __init__(self, config: dict = None):
        self.config = config or {
            "time_features": True,
            "user_features": True,
            "param_features": True,
            "historical_features": True,
            "rolling_window_size": 10,
        }
        self.encoders = {}
        self.scaler = None
        self.feature_columns = []
        self._init_encoders()

    def _init_encoders(self):
        self.encoders["endpoint"] = LabelEncoder()
        self.encoders["http_method"] = LabelEncoder()
        self.encoders["user_segment"] = LabelEncoder()
        self.encoders["param_complexity"] = LabelEncoder()

    def _fit_encoders(self, df: pd.DataFrame):
        self.encoders["endpoint"].fit(df["endpoint"])
        self.encoders["http_method"].fit(df["http_method"])
        self.encoders["user_segment"].fit(df["user_segment"])
        self.encoders["param_complexity"].fit(df["param_complexity"])

    def extract_time_features(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        df["hour"] = df["timestamp"].dt.hour
        df["day_of_week"] = df["timestamp"].dt.dayofweek
        df["day_of_month"] = df["timestamp"].dt.day
        df["is_peak_hour"] = ((df["hour"].between(9, 11)) | (df["hour"].between(14, 17)) & (df["day_of_week"] < 5)).astype(int)
        df["is_night_hour"] = df["hour"].between(0, 5).astype(int)
        df["is_weekend"] = (df["day_of_week"] >= 5).astype(int)
        df["hour_sin"] = np.sin(2 * np.pi * df["hour"] / 24)
        df["hour_cos"] = np.cos(2 * np.pi * df["hour"] / 24)
        df["dow_sin"] = np.sin(2 * np.pi * df["day_of_week"] / 7)
        df["dow_cos"] = np.cos(2 * np.pi * df["day_of_week"] / 7)
        return df

    def extract_user_features(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        
        user_request_count = df.groupby("user_id").cumcount() + 1
        df["user_request_count"] = user_request_count
        
        return df

    def extract_param_features(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        df["params_per_kb_ratio"] = df["param_count"] / (df["payload_size_kb"] + 1)
        df["is_complex_payload"] = (df["param_count"] > 8).astype(int)
        return df

    def extract_downstream_features(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        
        if "downstream_count" not in df.columns:
            df["downstream_count"] = 2
            df["downstream_degraded_count"] = 0
            df["downstream_max_latency_ms"] = 30
            df["downstream_total_latency_ms"] = 50
            df["has_downstream_degradation"] = False
            df["has_downstream_outage"] = False
        
        df["degraded_ratio"] = df["downstream_degraded_count"] / (df["downstream_count"] + 1)
        df["avg_downstream_latency"] = df["downstream_total_latency_ms"] / (df["downstream_count"] + 1)
        df["latency_per_downstream"] = df["downstream_max_latency_ms"] / (df["downstream_count"] + 1)
        df["has_downstream_issue"] = (df["has_downstream_degradation"] | df["has_downstream_outage"]).astype(int)
        
        return df

    def extract_dependency_impact_features(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        
        if "downstream_total_latency_ms" in df.columns:
            df["downstream_latency_ratio"] = df["downstream_total_latency_ms"] / (df["server_load"] * 1000 + 1)
            df["payload_vs_downstream_ratio"] = df["payload_size_kb"] / (df["downstream_total_latency_ms"] + 1)
        
        return df

    def extract_historical_features(self, df: pd.DataFrame, window_size: int = 10) -> pd.DataFrame:
        df = df.copy()
        df = df.sort_values("timestamp").reset_index(drop=True)
        
        df["rolling_mean_latency"] = df.groupby("endpoint")["response_time_ms"].transform(
            lambda x: x.rolling(window=window_size, min_periods=1).mean()
        )
        
        df["rolling_std_latency"] = df.groupby("endpoint")["response_time_ms"].transform(
            lambda x: x.rolling(window=window_size, min_periods=1).std().fillna(0)
        )
        
        df["ema_latency"] = df.groupby("endpoint")["response_time_ms"].transform(
            lambda x: x.ewm(span=window_size, adjust=False).mean()
        )
        
        endpoint_avg = df.groupby("endpoint")["response_time_ms"].transform("mean")
        df["endpoint_avg_latency"] = endpoint_avg
        
        return df

    def encode_categorical(self, df: pd.DataFrame, fit: bool = True) -> pd.DataFrame:
        df = df.copy()
        
        for col, encoder in self.encoders.items():
            if fit:
                df[f"{col}_encoded"] = encoder.fit_transform(df[col])
            else:
                try:
                    df[f"{col}_encoded"] = encoder.transform(df[col])
                except ValueError:
                    df[f"{col}_encoded"] = 0
        
        return df

    def get_historical_stats(self, df: pd.DataFrame) -> Dict:
        endpoint_group = df.groupby("endpoint")["response_time_ms"]
        stats = {
            "endpoint_avg": endpoint_group.mean().to_dict(),
            "endpoint_p95": endpoint_group.quantile(0.95).to_dict(),
            "endpoint_p99": endpoint_group.quantile(0.99).to_dict(),
            "endpoint_std": endpoint_group.std().fillna(0).to_dict(),
            "endpoint_min": endpoint_group.min().to_dict(),
            "endpoint_max": endpoint_group.max().to_dict(),
            "endpoint_count": endpoint_group.count().to_dict(),
            "user_segment_avg": df.groupby("user_segment")["response_time_ms"].mean().to_dict(),
            "global_avg": df["response_time_ms"].mean(),
            "global_p95": df["response_time_ms"].quantile(0.95),
            "global_p99": df["response_time_ms"].quantile(0.99),
            "global_std": df["response_time_ms"].std(),
        }
        return stats

    def fit_transform(self, df: pd.DataFrame, fit_encoders: bool = True) -> pd.DataFrame:
        df = df.copy()
        
        if self.config.get("time_features", True):
            df = self.extract_time_features(df)
        
        if self.config.get("user_features", True):
            df = self.extract_user_features(df)
        
        if self.config.get("param_features", True):
            df = self.extract_param_features(df)
        
        if self.config.get("downstream_features", True):
            df = self.extract_downstream_features(df)
        
        if self.config.get("dependency_impact_features", True):
            df = self.extract_dependency_impact_features(df)
        
        if self.config.get("historical_features", True) and "response_time_ms" in df.columns:
            df = self.extract_historical_features(
                df,
                window_size=self.config.get("rolling_window_size", 10)
            )
        
        df = self.encode_categorical(df, fit=fit_encoders)
        
        return df

    def transform_single(self, request_data: Dict, historical_stats: Dict) -> pd.DataFrame:
        timestamp = request_data.get("timestamp", datetime.now())
        if isinstance(timestamp, str):
            timestamp = pd.to_datetime(timestamp)

        df = pd.DataFrame([{
            "timestamp": timestamp,
            "endpoint": request_data.get("endpoint", "/api/unknown"),
            "http_method": request_data.get("http_method", "GET"),
            "user_segment": request_data.get("user_segment", "regular"),
            "user_id": request_data.get("user_id", "user_0"),
            "param_complexity": request_data.get("param_complexity", "simple"),
            "param_count": request_data.get("param_count", 2),
            "payload_size_kb": request_data.get("payload_size_kb", 5),
            "is_cached": request_data.get("is_cached", False),
            "server_load": request_data.get("server_load", 0.5),
            "downstream_count": request_data.get("downstream_count", 2),
            "downstream_degraded_count": request_data.get("downstream_degraded_count", 0),
            "downstream_max_latency_ms": request_data.get("downstream_max_latency_ms", 30),
            "downstream_total_latency_ms": request_data.get("downstream_total_latency_ms", 50),
            "has_downstream_degradation": request_data.get("has_downstream_degradation", False),
            "has_downstream_outage": request_data.get("has_downstream_outage", False),
        }])

        if self.config.get("time_features", True):
            df = self.extract_time_features(df)

        df["user_request_count"] = request_data.get("user_request_count", 1)

        if self.config.get("param_features", True):
            df = self.extract_param_features(df)

        if self.config.get("downstream_features", True):
            df = self.extract_downstream_features(df)

        if self.config.get("dependency_impact_features", True):
            df = self.extract_dependency_impact_features(df)

        df = self.encode_categorical(df, fit=False)

        endpoint = request_data.get("endpoint", "/api/unknown")
        df["endpoint_avg_latency"] = historical_stats["endpoint_avg"].get(endpoint, historical_stats["global_avg"])

        df["rolling_mean_latency"] = request_data.get("rolling_mean", historical_stats["global_avg"])
        df["rolling_std_latency"] = request_data.get("rolling_std", 0)
        df["ema_latency"] = request_data.get("ema", historical_stats["global_avg"])

        return df

    def get_feature_columns(self, df: pd.DataFrame) -> List[str]:
        exclude_cols = [
            "request_id", "timestamp", "endpoint", "http_method", 
            "user_segment", "user_id", "param_complexity",
            "response_time_ms"
        ]
        feature_cols = [col for col in df.columns if col not in exclude_cols]
        return feature_cols

    def prepare_for_training(self, df: pd.DataFrame):
        feature_cols = self.get_feature_columns(df)
        X = df[feature_cols].select_dtypes(include=[np.number]).fillna(0)
        y = df["response_time_ms"]
        return X, y

    def save(self, path: str = "./models/feature_engineer.joblib"):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        joblib.dump({
            "encoders": self.encoders,
            "config": self.config,
        }, path)

    @classmethod
    def load(cls, path: str = "./models/feature_engineer.joblib"):
        data = joblib.load(path)
        fe = cls(config=data["config"])
        fe.encoders = data["encoders"]
        return fe