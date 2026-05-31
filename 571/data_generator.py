import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import List, Dict
import random


class DataGenerator:
    def __init__(self, seed: int = 42):
        np.random.seed(seed)
        random.seed(seed)
        
        self.api_endpoints = [
            "/api/users",
            "/api/orders",
            "/api/products",
            "/api/payments",
            "/api/inventory",
            "/api/reports",
            "/api/auth/login",
            "/api/search",
        ]
        
        self.user_segments = ["new", "regular", "vip", "internal", "bot"]
        self.http_methods = ["GET", "POST", "PUT", "DELETE"]
        self.param_complexity = ["simple", "medium", "complex"]
        
        self.endpoint_base_latency = {
            "/api/users": 150,
            "/api/orders": 250,
            "/api/products": 100,
            "/api/payments": 400,
            "/api/inventory": 180,
            "/api/reports": 800,
            "/api/auth/login": 300,
            "/api/search": 350,
        }
        
        self.segment_latency_factor = {
            "new": 1.0,
            "regular": 0.9,
            "vip": 0.8,
            "internal": 0.7,
            "bot": 1.3,
        }
        
        self.complexity_factor = {
            "simple": 1.0,
            "medium": 1.5,
            "complex": 2.2,
        }

        self.downstream_dependencies = {
            "/api/users": ["db_users", "cache_redis"],
            "/api/orders": ["db_orders", "db_users", "queue_kafka"],
            "/api/products": ["db_products", "search_elasticsearch"],
            "/api/payments": ["db_payments", "gateway_stripe", "queue_kafka"],
            "/api/inventory": ["db_inventory", "cache_redis"],
            "/api/reports": ["db_orders", "db_products", "s3_storage"],
            "/api/auth/login": ["db_users", "oauth_service"],
            "/api/search": ["search_elasticsearch", "db_products"],
        }
        
        self.downstream_services = [
            "db_users", "db_orders", "db_products", "db_payments", "db_inventory",
            "cache_redis", "queue_kafka", "search_elasticsearch", "s3_storage",
            "gateway_stripe", "oauth_service"
        ]
        
        self.downstream_base_latency = {
            "db_users": 25,
            "db_orders": 35,
            "db_products": 20,
            "db_payments": 45,
            "db_inventory": 22,
            "cache_redis": 5,
            "queue_kafka": 15,
            "search_elasticsearch": 30,
            "s3_storage": 50,
            "gateway_stripe": 100,
            "oauth_service": 40,
        }
        
        self.downstream_degradation_prob = 0.08
        self.downstream_outage_prob = 0.02

    def _generate_timestamp(self, start_date: datetime, end_date: datetime) -> datetime:
        delta = end_date - start_date
        random_seconds = random.randint(0, int(delta.total_seconds()))
        return start_date + timedelta(seconds=random_seconds)

    def _is_peak_hour(self, dt: datetime) -> bool:
        hour = dt.hour
        day = dt.weekday()
        is_weekday = day < 5
        is_peak = (9 <= hour <= 11) or (14 <= hour <= 17)
        return is_weekday and is_peak

    def _is_night_hour(self, dt: datetime) -> bool:
        hour = dt.hour
        return 0 <= hour <= 5

    def _generate_downstream_status(self, endpoint: str) -> Dict:
        dependencies = self.downstream_dependencies.get(endpoint, [])
        status_info = {
            "downstream_count": len(dependencies),
            "downstream_degraded_count": 0,
            "downstream_max_latency_ms": 0,
            "downstream_total_latency_ms": 0,
            "has_downstream_degradation": False,
            "has_downstream_outage": False,
        }
        
        for service in dependencies:
            base_latency = self.downstream_base_latency.get(service, 20)
            rand = random.random()
            
            if rand < self.downstream_outage_prob:
                status_info["has_downstream_outage"] = True
                status_info["downstream_degraded_count"] += 1
                service_latency = base_latency * 10
            elif rand < self.downstream_outage_prob + self.downstream_degradation_prob:
                status_info["has_downstream_degradation"] = True
                status_info["downstream_degraded_count"] += 1
                service_latency = base_latency * 3
            else:
                service_latency = base_latency + np.random.normal(0, base_latency * 0.2)
            
            status_info["downstream_total_latency_ms"] += service_latency
            status_info["downstream_max_latency_ms"] = max(status_info["downstream_max_latency_ms"], service_latency)
        
        return status_info

    def _generate_response_time(self, row: Dict) -> float:
        base_latency = self.endpoint_base_latency[row["endpoint"]]
        segment_factor = self.segment_latency_factor[row["user_segment"]]
        complexity_factor = self.complexity_factor[row["param_complexity"]]
        
        response_time = base_latency * segment_factor * complexity_factor
        
        if self._is_peak_hour(row["timestamp"]):
            response_time *= 1.8
        
        if self._is_night_hour(row["timestamp"]):
            response_time *= 0.6
        
        response_time += row.get("downstream_total_latency_ms", 0)
        
        if row.get("has_downstream_outage", False):
            response_time *= 2.5
        elif row.get("has_downstream_degradation", False):
            response_time *= 1.5
        
        response_time += np.random.normal(0, 20)
        
        if random.random() < 0.05:
            response_time *= 3
        
        return max(10, response_time)

    def generate_data(
        self,
        num_samples: int = 10000,
        start_date: datetime = None,
        end_date: datetime = None,
    ) -> pd.DataFrame:
        if start_date is None:
            start_date = datetime.now() - timedelta(days=30)
        if end_date is None:
            end_date = datetime.now()

        data = []
        
        for _ in range(num_samples):
            timestamp = self._generate_timestamp(start_date, end_date)
            endpoint = random.choice(self.api_endpoints)
            user_segment = random.choice(self.user_segments)
            http_method = random.choice(self.http_methods)
            param_complexity = random.choice(self.param_complexity)
            param_count = {
                "simple": random.randint(1, 3),
                "medium": random.randint(4, 8),
                "complex": random.randint(9, 15),
            }[param_complexity]
            payload_size_kb = {
                "simple": random.randint(1, 10),
                "medium": random.randint(11, 50),
                "complex": random.randint(51, 200),
            }[param_complexity]
            
            downstream_status = self._generate_downstream_status(endpoint)
            
            row = {
                "request_id": f"req_{random.randint(100000, 999999)}",
                "timestamp": timestamp,
                "endpoint": endpoint,
                "http_method": http_method,
                "user_segment": user_segment,
                "user_id": f"user_{random.randint(1, 1000)}",
                "param_complexity": param_complexity,
                "param_count": param_count,
                "payload_size_kb": payload_size_kb,
                "is_cached": random.random() < 0.3,
                "server_load": round(random.uniform(0.2, 0.9), 2),
                **downstream_status,
            }
            
            row["response_time_ms"] = self._generate_response_time(row)
            data.append(row)

        df = pd.DataFrame(data)
        df = df.sort_values("timestamp").reset_index(drop=True)
        
        return df

    def save_data(self, df: pd.DataFrame, path: str = "./data/api_requests.csv"):
        import os
        os.makedirs(os.path.dirname(path), exist_ok=True)
        df.to_csv(path, index=False)
        print(f"Data saved to {path}, shape: {df.shape}")

    def load_data(self, path: str = "./data/api_requests.csv") -> pd.DataFrame:
        return pd.read_csv(path, parse_dates=["timestamp"])


if __name__ == "__main__":
    generator = DataGenerator()
    df = generator.generate_data(num_samples=20000)
    generator.save_data(df)
    print("\nSample data:")
    print(df.head())
    print("\nResponse time statistics:")
    print(df["response_time_ms"].describe())