import redis
import json
import numpy as np
from datetime import datetime
from typing import Dict, List, Optional, Any
from collections import deque


class RedisCache:
    def __init__(
        self,
        host: str = "localhost",
        port: int = 6379,
        db: int = 0,
        password: Optional[str] = None,
        history_window: int = 1000,
        downstream_services: List[str] = None
    ):
        self.host = host
        self.port = port
        self.db = db
        self.password = password
        self.history_window = history_window
        self.downstream_services = downstream_services or []
        self.client = None
        self._connect()

    def _connect(self):
        try:
            self.client = redis.Redis(
                host=self.host,
                port=self.port,
                db=self.db,
                password=self.password,
                decode_responses=True
            )
            self.client.ping()
            print("Connected to Redis successfully")
        except redis.ConnectionError:
            print("Warning: Could not connect to Redis. Using in-memory cache.")
            self.client = None
            self._init_memory_cache()

    def _init_memory_cache(self):
        self._memory_data = {
            "history": deque(maxlen=self.history_window),
            "predictions": {},
            "stats": {},
            "downstream_services": {},
            "warnings": deque(maxlen=100),
            "prediction_history": {},
            "timeout_recommendations": {},
            "root_cause_results": deque(maxlen=200),
            "model_versions": deque(maxlen=10),
        }

    def is_connected(self) -> bool:
        return self.client is not None

    def update_downstream_service_status(
        self,
        service_name: str,
        status: str,
        latency_ms: float,
        health_score: float = 1.0
    ):
        status_data = {
            "service_name": service_name,
            "status": status,
            "latency_ms": latency_ms,
            "health_score": health_score,
            "last_updated": datetime.now().isoformat()
        }
        
        if self.client:
            key = f"downstream:{service_name}"
            self.client.setex(key, 300, json.dumps(status_data))
            
            history_key = f"downstream_history:{service_name}"
            self.client.lpush(history_key, json.dumps(status_data))
            self.client.ltrim(history_key, 0, 99)
        else:
            self._memory_data["downstream_services"][service_name] = status_data

    def get_downstream_service_status(self, service_name: str) -> Optional[Dict]:
        if self.client:
            key = f"downstream:{service_name}"
            result = self.client.get(key)
            return json.loads(result) if result else None
        else:
            return self._memory_data["downstream_services"].get(service_name)

    def get_all_downstream_statuses(self) -> Dict[str, Dict]:
        if self.client:
            statuses = {}
            for service in self.downstream_services:
                status = self.get_downstream_service_status(service)
                if status:
                    statuses[service] = status
            return statuses
        else:
            return dict(self._memory_data["downstream_services"])

    def get_downstream_status_for_endpoint(
        self,
        endpoint: str,
        endpoint_dependencies: Dict[str, List[str]]
    ) -> Dict:
        dependencies = endpoint_dependencies.get(endpoint, [])
        
        total_latency = 0
        degraded_count = 0
        has_issue = False
        min_health = 1.0
        status_details = []
        
        for service in dependencies:
            status = self.get_downstream_service_status(service)
            if status:
                total_latency += status.get("latency_ms", 0)
                health = status.get("health_score", 1.0)
                min_health = min(min_health, health)
                
                if status.get("status") != "healthy":
                    degraded_count += 1
                    has_issue = True
                
                status_details.append(status)
            else:
                status_details.append({
                    "service_name": service,
                    "status": "unknown",
                    "latency_ms": 20,
                    "health_score": 0.8
                })
                total_latency += 20
        
        return {
            "downstream_count": len(dependencies),
            "downstream_degraded_count": degraded_count,
            "downstream_max_latency_ms": max([s.get("latency_ms", 0) for s in status_details]) if status_details else 0,
            "downstream_total_latency_ms": total_latency,
            "has_downstream_degradation": has_issue and degraded_count > 0,
            "has_downstream_outage": any(s.get("status") == "outage" for s in status_details),
            "downstream_min_health": min_health,
            "details": status_details
        }

    def store_warning(self, warning_data: Dict):
        if self.client:
            key = f"warning:{warning_data.get('warning_id', datetime.now().timestamp())}"
            self.client.setex(key, 86400, json.dumps(warning_data))
            
            warnings_key = "recent_warnings"
            self.client.lpush(warnings_key, json.dumps(warning_data))
            self.client.ltrim(warnings_key, 0, 99)
        else:
            self._memory_data["warnings"].append(warning_data)

    def get_recent_warnings(self, limit: int = 20) -> List[Dict]:
        if self.client:
            warnings_key = "recent_warnings"
            warnings = self.client.lrange(warnings_key, 0, limit - 1)
            return [json.loads(w) for w in warnings]
        else:
            return list(self._memory_data["warnings"])[-limit:]

    def get_endpoint_warnings(self, endpoint: str, limit: int = 10) -> List[Dict]:
        all_warnings = self.get_recent_warnings(limit=100)
        endpoint_warnings = [w for w in all_warnings if w.get("endpoint") == endpoint]
        return endpoint_warnings[:limit]

    def append_prediction_history(self, endpoint: str, predicted_value: float):
        if self.client:
            key = f"pred_history:{endpoint}"
            self.client.lpush(key, predicted_value)
            self.client.ltrim(key, 0, 49)
        else:
            if endpoint not in self._memory_data["prediction_history"]:
                self._memory_data["prediction_history"][endpoint] = deque(maxlen=50)
            self._memory_data["prediction_history"][endpoint].append(predicted_value)

    def get_prediction_history(self, endpoint: str, limit: int = 10) -> List[float]:
        if self.client:
            key = f"pred_history:{endpoint}"
            history = self.client.lrange(key, 0, limit - 1)
            return [float(h) for h in history]
        else:
            history = self._memory_data["prediction_history"].get(endpoint, deque(maxlen=50))
            return list(history)[-limit:]

    def store_request(self, request_data: Dict, response_time: float):
        record = {
            "timestamp": datetime.now().isoformat(),
            "request": request_data,
            "response_time_ms": response_time
        }
        
        if self.client:
            key = f"request:{request_data.get('request_id', datetime.now().timestamp())}"
            self.client.setex(key, 86400, json.dumps(record))
            
            history_key = f"history:{request_data.get('endpoint', 'unknown')}"
            self.client.lpush(history_key, json.dumps(record))
            self.client.ltrim(history_key, 0, self.history_window - 1)
        else:
            self._memory_data["history"].append(record)

    def get_endpoint_history(self, endpoint: str, limit: int = 100) -> List[Dict]:
        if self.client:
            history_key = f"history:{endpoint}"
            history = self.client.lrange(history_key, 0, limit - 1)
            return [json.loads(h) for h in history]
        else:
            return list(self._memory_data["history"])[-limit:]

    def get_endpoint_stats(self, endpoint: str) -> Dict[str, float]:
        cache_key = f"stats:{endpoint}"
        
        if self.client:
            cached = self.client.get(cache_key)
            if cached:
                return json.loads(cached)
        
        history = self.get_endpoint_history(endpoint, limit=self.history_window)
        
        if not history:
            return {
                "avg": 0,
                "std": 0,
                "p95": 0,
                "count": 0
            }
        
        response_times = [h["response_time_ms"] for h in history]
        
        stats = {
            "avg": float(np.mean(response_times)),
            "std": float(np.std(response_times)),
            "p95": float(np.percentile(response_times, 95)),
            "count": len(response_times)
        }
        
        if self.client:
            self.client.setex(cache_key, 300, json.dumps(stats))
        
        return stats

    def store_prediction(self, request_id: str, prediction_result: Dict):
        if self.client:
            key = f"prediction:{request_id}"
            self.client.setex(key, 3600, json.dumps(prediction_result))
        else:
            self._memory_data["predictions"][request_id] = prediction_result

    def get_prediction(self, request_id: str) -> Optional[Dict]:
        if self.client:
            key = f"prediction:{request_id}"
            result = self.client.get(key)
            return json.loads(result) if result else None
        else:
            return self._memory_data["predictions"].get(request_id)

    def update_historical_stats(self, historical_stats: Dict):
        if self.client:
            self.client.set("historical_stats", json.dumps(historical_stats))
        else:
            self._memory_data["stats"] = historical_stats

    def get_historical_stats(self) -> Dict:
        if self.client:
            result = self.client.get("historical_stats")
            return json.loads(result) if result else {}
        else:
            return self._memory_data.get("stats", {})

    def get_rolling_stats(self, endpoint: str, window: int = 10) -> Dict[str, float]:
        history = self.get_endpoint_history(endpoint, limit=window)
        
        if not history:
            return {
                "rolling_mean": 0,
                "rolling_std": 0,
                "ema": 0
            }
        
        response_times = [h["response_time_ms"] for h in history]
        
        ema = response_times[0]
        alpha = 2 / (window + 1)
        for rt in response_times[1:]:
            ema = alpha * rt + (1 - alpha) * ema
        
        return {
            "rolling_mean": float(np.mean(response_times)),
            "rolling_std": float(np.std(response_times)),
            "ema": float(ema)
        }

    def increment_user_request_count(self, user_id: str) -> int:
        if self.client:
            key = f"user_count:{user_id}"
            count = self.client.incr(key)
            self.client.expire(key, 86400)
            return count
        else:
            return 1

    def get_user_request_count(self, user_id: str) -> int:
        if self.client:
            key = f"user_count:{user_id}"
            count = self.client.get(key)
            return int(count) if count else 0
        else:
            return 1

    def flush_all(self):
        if self.client:
            self.client.flushdb()

    def store_timeout_recommendation(self, endpoint: str, recommendation: Dict):
        if self.client:
            key = f"timeout_rec:{endpoint}"
            self.client.setex(key, 3600, json.dumps(recommendation, default=str))
        else:
            self._memory_data["timeout_recommendations"][endpoint] = recommendation

    def get_timeout_recommendation(self, endpoint: str) -> Optional[Dict]:
        if self.client:
            key = f"timeout_rec:{endpoint}"
            result = self.client.get(key)
            return json.loads(result) if result else None
        else:
            return self._memory_data["timeout_recommendations"].get(endpoint)

    def store_root_cause_result(self, analysis_id: str, analysis: Dict):
        if self.client:
            key = f"root_cause:{analysis_id}"
            self.client.setex(key, 86400, json.dumps(analysis, default=str))
            
            history_key = "recent_root_causes"
            self.client.lpush(history_key, json.dumps({
                "analysis_id": analysis_id,
                "endpoint": analysis.get("endpoint", ""),
                "severity": analysis.get("severity", ""),
                "deviation_percent": analysis.get("deviation_percent", 0),
                "timestamp": analysis.get("timestamp", datetime.now().isoformat())
            }, default=str))
            self.client.ltrim(history_key, 0, 99)
        else:
            self._memory_data["root_cause_results"].append({
                "analysis_id": analysis_id,
                **analysis
            })

    def get_recent_root_causes(self, limit: int = 20) -> List[Dict]:
        if self.client:
            history_key = "recent_root_causes"
            results = self.client.lrange(history_key, 0, limit - 1)
            return [json.loads(r) for r in results]
        else:
            return list(self._memory_data["root_cause_results"])[-limit:]

    def store_model_version(self, version_info: Dict):
        if self.client:
            key = f"model_version:{version_info.get('version', 0)}"
            self.client.set(key, json.dumps(version_info, default=str))
            
            versions_key = "model_version_history"
            self.client.lpush(versions_key, json.dumps(version_info, default=str))
            self.client.ltrim(versions_key, 0, 9)
        else:
            self._memory_data["model_versions"].append(version_info)

    def get_model_versions(self, limit: int = 10) -> List[Dict]:
        if self.client:
            versions_key = "model_version_history"
            results = self.client.lrange(versions_key, 0, limit - 1)
            return [json.loads(r) for r in results]
        else:
            return list(self._memory_data["model_versions"])[-limit:]