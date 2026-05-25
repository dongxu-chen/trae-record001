from typing import Dict, List, Optional, Tuple

from config import config
from src.redis_client import RedisClient


class TrafficLayer:
    def __init__(self):
        self.redis_client = RedisClient()
        self.layers = config.traffic.layers

    def classify(self, ctr: float, cvr: float, user_value: float = 0.0) -> Tuple[str, Dict]:
        score = ctr * 0.6 + cvr * 0.3 + user_value * 0.1
        for layer in self.layers:
            if score >= layer["min_ctr"]:
                return layer["name"], layer
        return self.layers[-1]["name"], self.layers[-1]

    def get_layer_multiplier(self, layer_name: str) -> float:
        for layer in self.layers:
            if layer["name"] == layer_name:
                return layer["bid_multiplier"]
        return 1.0

    def get_layer_budget_share(self, layer_name: str) -> float:
        for layer in self.layers:
            if layer["name"] == layer_name:
                return layer["budget_share"]
        return 0.0

    def allocate_budget(self, campaign_id: str, total_budget: float) -> Dict[str, float]:
        budget_alloc = {}
        for layer in self.layers:
            layer_budget = total_budget * layer["budget_share"]
            budget_alloc[layer["name"]] = layer_budget
            self.redis_client.set_traffic_layer_counter(layer["name"], campaign_id, layer_budget)
        return budget_alloc

    def get_layer_budget_remaining(self, layer_name: str, campaign_id: str) -> float:
        stats = self.redis_client.get_traffic_layer_stats(layer_name, campaign_id)
        return float(stats.get("value", 0.0))

    def consume_layer_budget(self, layer_name: str, campaign_id: str, amount: float) -> bool:
        remaining = self.get_layer_budget_remaining(layer_name, campaign_id)
        if remaining >= amount:
            self.redis_client.set_traffic_layer_counter(layer_name, campaign_id, -amount)
            return True
        return False

    def record_layer_impression(self, layer_name: str, campaign_id: str) -> None:
        key = f"traffic:layer:{layer_name}:{campaign_id}"
        with self.redis_client.get_client() as r:
            r.hincrbyfloat(key, "impressions", 1)

    def record_layer_click(self, layer_name: str, campaign_id: str) -> None:
        key = f"traffic:layer:{layer_name}:{campaign_id}"
        with self.redis_client.get_client() as r:
            r.hincrbyfloat(key, "clicks", 1)

    def record_layer_cost(self, layer_name: str, campaign_id: str, cost: float) -> None:
        key = f"traffic:layer:{layer_name}:{campaign_id}"
        with self.redis_client.get_client() as r:
            r.hincrbyfloat(key, "cost", cost)

    def get_layer_performance(self, layer_name: str, campaign_id: str) -> Dict[str, float]:
        stats = self.redis_client.get_traffic_layer_stats(layer_name, campaign_id)
        impressions = float(stats.get("impressions", 0))
        clicks = float(stats.get("clicks", 0))
        cost = float(stats.get("cost", 0))
        ctr = clicks / impressions if impressions > 0 else 0
        cpc = cost / clicks if clicks > 0 else 0
        return {
            "impressions": impressions,
            "clicks": clicks,
            "cost": cost,
            "ctr": ctr,
            "cpc": cpc,
            "remaining_budget": float(stats.get("value", 0)),
        }

    def get_all_layers_performance(self, campaign_id: str) -> Dict[str, Dict[str, float]]:
        result = {}
        for layer in self.layers:
            result[layer["name"]] = self.get_layer_performance(layer["name"], campaign_id)
        return result

    def dynamic_adjust_multiplier(self, layer_name: str, campaign_id: str) -> float:
        perf = self.get_layer_performance(layer_name, campaign_id)
        ctr = perf["ctr"]
        base_multiplier = self.get_layer_multiplier(layer_name)
        if ctr > 0.05:
            return min(base_multiplier * 1.2, 2.0)
        elif ctr < 0.01:
            return max(base_multiplier * 0.8, 0.5)
        return base_multiplier
