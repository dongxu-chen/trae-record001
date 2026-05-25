import time
import math
from typing import Dict, List, Optional, Tuple

from config import config
from src.redis_client import RedisClient


class FrequencyController:
    def __init__(self):
        self.redis_client = RedisClient()
        self.limits = config.frequency.limits
        self.decay_factor = config.frequency.decay_factor

    def can_show(self, user_id: str, ad_id: str) -> Tuple[bool, List[str], Dict[str, int]]:
        allowed, violated, counts = self.redis_client.check_sliding_window_limits(user_id, ad_id)
        return allowed, violated, counts

    def record_impression(self, user_id: str, ad_id: str) -> Tuple[Dict[str, int], Dict[str, bool]]:
        counts, within_limits = self.redis_client.record_impression_sliding_window(user_id, ad_id)
        return counts, within_limits

    def get_sliding_window_details(
        self,
        user_id: str,
        ad_id: str,
        window: Optional[str] = None,
    ) -> Dict:
        if window:
            windows = [(window, self.limits.get(window, (0, 3600))[1])]
        else:
            windows = [(name, ttl) for name, (limit, ttl) in self.limits.items()]
        
        details = {}
        for window_name, window_seconds in windows:
            counts = self.redis_client.get_sliding_window_count(
                user_id, ad_id, window_name, window_seconds
            )
            timestamps = self.redis_client.get_sliding_window_timestamps(
                user_id, ad_id, window_name, window_seconds
            )
            limit = self.limits.get(window_name, (0, 0))[0]
            
            time_since_first = None
            time_since_last = None
            impressions_per_hour = 0.0
            
            if timestamps:
                now = int(time.time() * 1000)
                time_since_first = (now - min(timestamps)) / 1000
                time_since_last = (now - max(timestamps)) / 1000
                
                if time_since_first > 0:
                    impressions_per_hour = counts / (time_since_first / 3600)
            
            details[window_name] = {
                "count": counts,
                "limit": limit,
                "remaining": max(0, limit - counts),
                "utilization": counts / limit if limit > 0 else 0,
                "timestamps": timestamps,
                "time_since_first_seconds": time_since_first,
                "time_since_last_seconds": time_since_last,
                "impressions_per_hour": impressions_per_hour,
                "window_seconds": window_seconds,
            }
        
        return details if window else details

    def calculate_time_decay_penalty(self, user_id: str, ad_id: str) -> float:
        total_penalty = 1.0
        window_details = self.get_sliding_window_details(user_id, ad_id)
        
        for window_name, details in window_details.items():
            count = details["count"]
            limit = details["limit"]
            
            if count > 0 and limit > 0:
                ratio = count / limit
                decay = self.decay_factor ** (ratio * 2)
                
                time_since_last = details["time_since_last_seconds"]
                if time_since_last is not None:
                    window_seconds = details["window_seconds"]
                    time_recovery = min(1.0, time_since_last / (window_seconds * 0.5))
                    decay = decay * (1 - time_recovery * 0.5) + time_recovery * 0.5
                
                total_penalty *= decay
        
        return max(0.1, total_penalty)

    def get_frequency_decay_penalty(self, user_id: str, ad_id: str) -> float:
        return self.calculate_time_decay_penalty(user_id, ad_id)

    def calculate_frequency_forecast(
        self,
        user_id: str,
        ad_id: str,
        next_hours: int = 24,
    ) -> Dict[str, Dict]:
        window_details = self.get_sliding_window_details(user_id, ad_id)
        forecast = {}
        
        for window_name, details in window_details.items():
            current_count = details["count"]
            limit = details["limit"]
            window_seconds = details["window_seconds"]
            impressions_per_hour = details["impressions_per_hour"]
            
            estimated_total = current_count + impressions_per_hour * next_hours
            projected_utilization = estimated_total / limit if limit > 0 else 0
            hours_to_limit = float('inf')
            
            if impressions_per_hour > 0 and limit > current_count:
                hours_to_limit = (limit - current_count) / impressions_per_hour
            
            forecast[window_name] = {
                "current_count": current_count,
                "limit": limit,
                "impressions_per_hour": impressions_per_hour,
                "forecast_hours": next_hours,
                "estimated_total": estimated_total,
                "projected_utilization": projected_utilization,
                "hours_to_limit": hours_to_limit,
                "will_exceed_limit": projected_utilization > 1.0,
            }
        
        return forecast

    def get_optimal_bid_adjustment(
        self,
        user_id: str,
        ad_id: str,
        base_bid: float,
        predicted_ctr: float,
    ) -> Tuple[float, Dict]:
        allowed, violated, counts = self.can_show(user_id, ad_id)
        
        if not allowed:
            return 0.0, {
                "allowed": False,
                "violated_windows": violated,
                "counts": counts,
                "reason": "FREQUENCY_LIMIT_EXCEEDED",
            }
        
        decay_penalty = self.calculate_time_decay_penalty(user_id, ad_id)
        forecast = self.calculate_frequency_forecast(user_id, ad_id, next_hours=1)
        
        forecast_factor = 1.0
        for window_name, forecast_info in forecast.items():
            if forecast_info["will_exceed_limit"]:
                hours_to_limit = forecast_info["hours_to_limit"]
                if hours_to_limit < 1:
                    forecast_factor *= max(0.3, hours_to_limit)
                elif hours_to_limit < 6:
                    forecast_factor *= 0.8
        
        forecast_details = {
            "allowed": True,
            "counts": counts,
            "decay_penalty": decay_penalty,
            "forecast_factor": forecast_factor,
            "frequency_forecast": forecast,
            "window_details": self.get_sliding_window_details(user_id, ad_id),
        }
        
        final_adjustment = decay_penalty * forecast_factor
        return max(0.0, min(1.0, final_adjustment)), forecast_details

    def get_bid_adjustment(self, user_id: str, ad_id: str) -> float:
        adjustment, _ = self.get_optimal_bid_adjustment(user_id, ad_id, 0.0, 0.0)
        return adjustment

    def get_user_frequency_summary(self, user_id: str, ad_id: str) -> Dict:
        allowed, violated, counts = self.can_show(user_id, ad_id)
        decay_penalty = self.calculate_time_decay_penalty(user_id, ad_id)
        window_details = self.get_sliding_window_details(user_id, ad_id)
        forecast = self.calculate_frequency_forecast(user_id, ad_id)
        
        return {
            "user_id": user_id,
            "ad_id": ad_id,
            "allowed": allowed,
            "violated_windows": violated,
            "current_counts": counts,
            "decay_penalty": decay_penalty,
            "bid_adjustment": self.get_bid_adjustment(user_id, ad_id),
            "window_details": window_details,
            "frequency_forecast": forecast,
        }

    def reset_frequency(self, user_id: str, ad_id: str) -> None:
        for window_name in self.limits.keys():
            key = self.redis_client._get_sliding_window_key(user_id, ad_id, window_name)
            self.redis_client.delete_key(key)

    def get_all_user_ads(self, user_id: str) -> List[str]:
        pattern = f"freq:sw:{user_id}:*"
        keys = self.redis_client.get_all_keys(pattern)
        ad_ids = set()
        for key in keys:
            parts = key.split(":")
            if len(parts) >= 4:
                ad_ids.add(parts[3])
        return list(ad_ids)

    def get_campaign_frequency_stats(self, ad_id: str) -> Dict[str, Dict]:
        pattern = f"freq:sw:*:{ad_id}:*"
        keys = self.redis_client.get_all_keys(pattern)
        stats = {}
        for key in keys:
            parts = key.split(":")
            if len(parts) >= 5:
                user_id = parts[2]
                window = parts[4]
                window_seconds = self.limits.get(window, (0, 3600))[1]
                count = self.redis_client.get_sliding_window_count(user_id, ad_id, window, window_seconds)
                if window not in stats:
                    stats[window] = {"total_users": 0, "total_impressions": 0, "avg_frequency": 0.0}
                stats[window]["total_users"] += 1
                stats[window]["total_impressions"] += count
        for window in stats:
            if stats[window]["total_users"] > 0:
                stats[window]["avg_frequency"] = stats[window]["total_impressions"] / stats[window]["total_users"]
        return stats

    def get_frequency_distribution(
        self,
        ad_id: str,
        window: str = "24h",
    ) -> Dict[int, int]:
        window_seconds = self.limits.get(window, (0, 86400))[1]
        pattern = f"freq:sw:*:{ad_id}:{window}"
        keys = self.redis_client.get_all_keys(pattern)
        
        distribution = {}
        for key in keys:
            parts = key.split(":")
            if len(parts) >= 5:
                user_id = parts[2]
                count = self.redis_client.get_sliding_window_count(user_id, ad_id, window, window_seconds)
                bucket = min(count, 10)
                distribution[bucket] = distribution.get(bucket, 0) + 1
        
        return dict(sorted(distribution.items()))
