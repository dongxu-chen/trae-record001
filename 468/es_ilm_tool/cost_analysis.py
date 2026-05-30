import logging
from datetime import datetime, timezone
from es_ilm_tool.es_client import ESClient
from es_ilm_tool.lifecycle import LifecycleEngine
from es_ilm_tool import config

logger = logging.getLogger(__name__)

TIER_COSTS = {
    "hot": config.COST_HOT_GB_PER_MONTH,
    "warm": config.COST_WARM_GB_PER_MONTH,
    "cold": config.COST_COLD_GB_PER_MONTH,
    "frozen": config.COST_FROZEN_GB_PER_MONTH,
}


class CostAnalyzer:
    def __init__(self):
        self.es = ESClient()
        self.engine = LifecycleEngine()

    def _get_tier_for_index(self, index_name: str) -> str:
        try:
            info = self.engine.get_index_info(index_name)
            return info.tier
        except Exception:
            return "hot"

    def _get_num_replicas(self, index_name: str) -> int:
        try:
            settings = self.es.get_index_settings(index_name)
            return int(settings.get("index", {}).get("number_of_replicas", 1))
        except Exception:
            return 1

    def calculate_index_cost(self, index_name: str) -> dict:
        try:
            info = self.engine.get_index_info(index_name)
            settings = self.es.get_index_settings(index_name)
            replicas = int(settings.get("index", {}).get("number_of_replicas", 1))
            tier = info.tier

            total_size_gb = info.size_gb * (1 + replicas)
            cost_per_gb = TIER_COSTS.get(tier, TIER_COSTS["hot"])
            monthly_cost = total_size_gb * cost_per_gb

            potential_savings = {}
            for target_tier, target_cost in TIER_COSTS.items():
                if target_tier != tier and TIER_COSTS.get(target_tier, 0) < cost_per_gb:
                    target_monthly = total_size_gb * target_cost
                    savings = monthly_cost - target_monthly
                    if savings > 0:
                        potential_savings[target_tier] = {
                            "monthly_cost": round(target_monthly, 4),
                            "monthly_savings": round(savings, 4),
                            "savings_percent": round((savings / monthly_cost) * 100, 2),
                        }

            return {
                "index": index_name,
                "tier": tier,
                "size_gb": round(info.size_gb, 4),
                "replicas": replicas,
                "total_size_gb": round(total_size_gb, 4),
                "doc_count": info.doc_count,
                "age_days": info.age_days,
                "cost_per_gb_per_month": cost_per_gb,
                "monthly_cost": round(monthly_cost, 4),
                "daily_cost": round(monthly_cost / 30, 4),
                "yearly_cost": round(monthly_cost * 12, 4),
                "currency": config.COST_CURRENCY,
                "potential_savings": potential_savings,
                "timestamp": datetime.now(tz=timezone.utc).isoformat(),
            }
        except Exception as e:
            logger.error("Failed to calculate cost for index %s: %s", index_name, e)
            return {"index": index_name, "error": str(e)}

    def calculate_cluster_cost(self) -> dict:
        indices = self.engine.list_all_indices("*")
        result = {
            "total_monthly_cost": 0,
            "total_daily_cost": 0,
            "total_yearly_cost": 0,
            "total_size_gb": 0,
            "total_doc_count": 0,
            "currency": config.COST_CURRENCY,
            "by_tier": {
                "hot": {"count": 0, "size_gb": 0, "monthly_cost": 0, "doc_count": 0},
                "warm": {"count": 0, "size_gb": 0, "monthly_cost": 0, "doc_count": 0},
                "cold": {"count": 0, "size_gb": 0, "monthly_cost": 0, "doc_count": 0},
                "frozen": {"count": 0, "size_gb": 0, "monthly_cost": 0, "doc_count": 0},
            },
            "most_expensive_indices": [],
            "timestamp": datetime.now(tz=timezone.utc).isoformat(),
        }

        index_costs = []
        for idx_dict in indices:
            name = idx_dict.get("name", "")
            cost_info = self.calculate_index_cost(name)
            if "error" in cost_info:
                continue

            tier = cost_info["tier"]
            if tier not in result["by_tier"]:
                tier = "hot"

            result["by_tier"][tier]["count"] += 1
            result["by_tier"][tier]["size_gb"] += cost_info["total_size_gb"]
            result["by_tier"][tier]["monthly_cost"] += cost_info["monthly_cost"]
            result["by_tier"][tier]["doc_count"] += cost_info["doc_count"]

            result["total_monthly_cost"] += cost_info["monthly_cost"]
            result["total_size_gb"] += cost_info["total_size_gb"]
            result["total_doc_count"] += cost_info["doc_count"]

            index_costs.append({
                "index": name,
                "monthly_cost": cost_info["monthly_cost"],
                "size_gb": cost_info["total_size_gb"],
                "tier": tier,
            })

        for tier in result["by_tier"]:
            result["by_tier"][tier]["size_gb"] = round(result["by_tier"][tier]["size_gb"], 4)
            result["by_tier"][tier]["monthly_cost"] = round(result["by_tier"][tier]["monthly_cost"], 4)

        result["total_monthly_cost"] = round(result["total_monthly_cost"], 4)
        result["total_daily_cost"] = round(result["total_monthly_cost"] / 30, 4)
        result["total_yearly_cost"] = round(result["total_monthly_cost"] * 12, 4)
        result["total_size_gb"] = round(result["total_size_gb"], 4)

        index_costs.sort(key=lambda x: x["monthly_cost"], reverse=True)
        result["most_expensive_indices"] = index_costs[:config.PERF_ANALYSIS_TOP_N]

        result["cost_rates"] = {
            "hot": config.COST_HOT_GB_PER_MONTH,
            "warm": config.COST_WARM_GB_PER_MONTH,
            "cold": config.COST_COLD_GB_PER_MONTH,
            "frozen": config.COST_FROZEN_GB_PER_MONTH,
        }

        return result

    def analyze_cost_optimization(self) -> dict:
        cluster_cost = self.calculate_cluster_cost()
        optimizations = []

        for idx_dict in self.engine.list_all_indices("*"):
            name = idx_dict.get("name", "")
            cost_info = self.calculate_index_cost(name)
            if "error" in cost_info:
                continue

            tier = cost_info["tier"]
            age = cost_info["age_days"]
            savings = cost_info.get("potential_savings", {})

            if tier == "hot" and age >= config.MIGRATE_TO_WARM_AGE_DAYS:
                warm_savings = savings.get("warm", {})
                if warm_savings:
                    optimizations.append({
                        "type": "migrate_to_warm",
                        "index": name,
                        "age_days": age,
                        "current_tier": "hot",
                        "target_tier": "warm",
                        "monthly_savings": warm_savings["monthly_savings"],
                        "savings_percent": warm_savings["savings_percent"],
                        "reason": f"Age {age}d exceeds warm threshold {config.MIGRATE_TO_WARM_AGE_DAYS}d",
                    })

            if tier in ("hot", "warm") and age >= config.MIGRATE_TO_COLD_AGE_DAYS:
                cold_savings = savings.get("cold", {})
                if cold_savings:
                    optimizations.append({
                        "type": "migrate_to_cold",
                        "index": name,
                        "age_days": age,
                        "current_tier": tier,
                        "target_tier": "cold",
                        "monthly_savings": cold_savings["monthly_savings"],
                        "savings_percent": cold_savings["savings_percent"],
                        "reason": f"Age {age}d exceeds cold threshold {config.MIGRATE_TO_COLD_AGE_DAYS}d",
                    })

            if tier in ("hot", "warm", "cold") and age >= config.FREEZE_AGE_DAYS:
                frozen_savings = savings.get("frozen", {})
                if frozen_savings:
                    optimizations.append({
                        "type": "freeze",
                        "index": name,
                        "age_days": age,
                        "current_tier": tier,
                        "target_tier": "frozen",
                        "monthly_savings": frozen_savings["monthly_savings"],
                        "savings_percent": frozen_savings["savings_percent"],
                        "reason": f"Age {age}d exceeds freeze threshold {config.FREEZE_AGE_DAYS}d",
                    })

            if age >= config.DELETE_AGE_DAYS:
                optimizations.append({
                    "type": "delete",
                    "index": name,
                    "age_days": age,
                    "current_tier": tier,
                    "target_tier": None,
                    "monthly_savings": cost_info["monthly_cost"],
                    "savings_percent": 100.0,
                    "reason": f"Age {age}d exceeds delete threshold {config.DELETE_AGE_DAYS}d",
                })

        total_savings = sum(opt["monthly_savings"] for opt in optimizations)
        optimizations.sort(key=lambda x: x["monthly_savings"], reverse=True)

        return {
            "cluster_cost": cluster_cost,
            "potential_optimizations": optimizations,
            "total_monthly_savings_potential": round(total_savings, 4),
            "optimization_count": len(optimizations),
            "currency": config.COST_CURRENCY,
            "timestamp": datetime.now(tz=timezone.utc).isoformat(),
        }

    def get_cost_forecast(self, months: int = 12) -> dict:
        cluster_cost = self.calculate_cluster_cost()
        forecast = []

        current_monthly = cluster_cost["total_monthly_cost"]
        total_size = cluster_cost["total_size_gb"]
        growth_rate = 0.05

        for month in range(1, months + 1):
            projected_size = total_size * (1 + growth_rate) ** month
            projected_cost = current_monthly * (1 + growth_rate) ** month

            optimized_cost = projected_cost
            warm_count = int(cluster_cost["by_tier"]["warm"]["count"] * (1 + growth_rate) ** month)
            cold_count = int(cluster_cost["by_tier"]["cold"]["count"] * (1 + growth_rate) ** month)
            if warm_count > 0 and cold_count > 0:
                warm_size = cluster_cost["by_tier"]["warm"]["size_gb"] * (1 + growth_rate) ** month
                cold_size = cluster_cost["by_tier"]["cold"]["size_gb"] * (1 + growth_rate) ** month
                optimized_cost = (
                    warm_size * config.COST_WARM_GB_PER_MONTH
                    + cold_size * config.COST_COLD_GB_PER_MONTH
                    + cluster_cost["by_tier"]["hot"]["size_gb"] * (1 + growth_rate) ** month * config.COST_HOT_GB_PER_MONTH
                )

            forecast.append({
                "month": month,
                "projected_size_gb": round(projected_size, 4),
                "projected_monthly_cost": round(projected_cost, 4),
                "optimized_monthly_cost": round(optimized_cost, 4),
                "savings": round(projected_cost - optimized_cost, 4),
                "savings_percent": round(((projected_cost - optimized_cost) / projected_cost) * 100, 2) if projected_cost > 0 else 0,
            })

        return {
            "current_monthly_cost": current_monthly,
            "current_size_gb": round(total_size, 4),
            "growth_rate_assumption": f"{growth_rate * 100}% per month",
            "forecast_period_months": months,
            "currency": config.COST_CURRENCY,
            "forecast": forecast,
            "total_projected_cost": round(sum(f["projected_monthly_cost"] for f in forecast), 4),
            "total_optimized_cost": round(sum(f["optimized_monthly_cost"] for f in forecast), 4),
            "total_savings_potential": round(sum(f["savings"] for f in forecast), 4),
            "timestamp": datetime.now(tz=timezone.utc).isoformat(),
        }
