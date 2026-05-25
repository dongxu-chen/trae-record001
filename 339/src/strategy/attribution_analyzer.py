import os
import sys
import time
import math
from typing import Dict, List, Optional, Tuple, Any
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    import numpy as np
    import pandas as pd
    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False

from common.logger import get_logger
from common.utils import load_config, safe_divide

logger = get_logger("AttributionAnalyzer")


@dataclass
class Touchpoint:
    user_id: str
    channel: str
    action_type: str
    timestamp: float
    cost: float = 0.0
    responded: bool = False
    response_delay_hours: float = 0.0


@dataclass
class ChannelAttributionResult:
    channel: str
    total_touches: int
    unique_users: int
    responses: int
    response_rate: float
    churn_prevented: int
    churn_rate_treated: float
    churn_rate_control: float
    uplift: float
    incremental_value: float
    cost_per_acquisition: float
    roi: float
    confidence: float
    statistical_significance: float


class TouchpointAttributionAnalyzer:
    def __init__(self, cache_manager=None):
        self.config = load_config()
        self.cache = cache_manager
        
        self.touchpoints: List[Touchpoint] = []
        self.user_touchpoints: Dict[str, List[Touchpoint]] = defaultdict(list)
        self.channel_results: Dict[str, ChannelAttributionResult] = {}
        
        self.attribution_window_days = self.config.get("attribution", {}).get(
            "attribution_window_days", 14
        )
        self.control_group_ratio = self.config.get("attribution", {}).get(
            "control_group_ratio", 0.2
        )
        
        self.channels = ["push", "email", "sms", "in_app"]
        self.action_types = ["discount_offer", "personalized_recommendation", 
                            "winback_campaign", "loyalty_reward", "feature_highlight"]
        
        logger.info("TouchpointAttributionAnalyzer initialized")

    def record_touchpoint(self, user_id: str, channel: str, action_type: str,
                         timestamp: Optional[float] = None, cost: float = 0.0) -> Touchpoint:
        timestamp = timestamp or time.time()
        touchpoint = Touchpoint(
            user_id=user_id,
            channel=channel,
            action_type=action_type,
            timestamp=timestamp,
            cost=cost
        )
        self.touchpoints.append(touchpoint)
        self.user_touchpoints[user_id].append(touchpoint)
        return touchpoint

    def record_response(self, user_id: str, touchpoint_timestamp: float,
                       response_timestamp: Optional[float] = None) -> bool:
        response_timestamp = response_timestamp or time.time()
        
        user_tps = self.user_touchpoints.get(user_id, [])
        for tp in user_tps:
            if abs(tp.timestamp - touchpoint_timestamp) < 1.0:
                tp.responded = True
                tp.response_delay_hours = (response_timestamp - touchpoint_timestamp) / 3600.0
                return True
        
        closest_tp = None
        min_delay = float('inf')
        for tp in user_tps:
            delay = response_timestamp - tp.timestamp
            if 0 < delay < self.attribution_window_days * 86400 and delay < min_delay:
                min_delay = delay
                closest_tp = tp
        
        if closest_tp:
            closest_tp.responded = True
            closest_tp.response_delay_hours = min_delay / 3600.0
            return True
        
        return False

    def assign_control_groups(self, user_ids: List[str]) -> Dict[str, str]:
        np.random.seed(42)
        assignments = {}
        
        for user_id in user_ids:
            assignments[user_id] = "control" if np.random.random() < self.control_group_ratio else "treatment"
        
        return assignments

    def analyze_treatment_effects(self, user_churn_data: List[Dict],
                                  group_assignments: Dict[str, str]) -> Dict[str, Any]:
        if not NUMPY_AVAILABLE:
            return {"error": "numpy/pandas not available"}
        
        df = pd.DataFrame(user_churn_data)
        df["group"] = df["user_id"].map(group_assignments)
        df["treated"] = df["group"] == "treatment"
        
        treated_df = df[df["treated"]]
        control_df = df[df["group"] == "control"]
        
        overall_churn_treated = treated_df["churned"].mean() if len(treated_df) > 0 else 0
        overall_churn_control = control_df["churned"].mean() if len(control_df) > 0 else 0
        overall_uplift = overall_churn_control - overall_churn_treated
        
        results = {
            "overall": {
                "treatment_size": len(treated_df),
                "control_size": len(control_df),
                "churn_rate_treated": float(overall_churn_treated),
                "churn_rate_control": float(overall_churn_control),
                "uplift_absolute": float(overall_uplift),
                "uplift_relative": float(safe_divide(overall_uplift, overall_churn_control, 0)),
                "churn_prevented": int(len(treated_df) * overall_uplift),
                "statistically_significant": self._is_significant(
                    treated_df["churned"], control_df["churned"]
                )
            },
            "by_channel": {},
            "by_action": {},
            "channel_attribution": {},
            "recommendations": []
        }
        
        for channel in self.channels:
            channel_users = [tp.user_id for tp in self.touchpoints if tp.channel == channel]
            channel_treated = treated_df[treated_df["user_id"].isin(channel_users)]
            
            if len(channel_treated) == 0 or len(control_df) == 0:
                continue
            
            churn_treated = channel_treated["churned"].mean()
            churn_control = control_df["churned"].mean()
            uplift = churn_control - churn_treated
            
            total_cost = sum(tp.cost for tp in self.touchpoints if tp.channel == channel)
            responses = sum(1 for tp in self.touchpoints if tp.channel == channel and tp.responded)
            touches = sum(1 for tp in self.touchpoints if tp.channel == channel)
            unique_users = len(set(tp.user_id for tp in self.touchpoints if tp.channel == channel))
            
            churn_prevented = int(len(channel_treated) * uplift)
            incremental_value = churn_prevented * self._estimate_user_value()
            cpa = safe_divide(total_cost, responses, float('inf'))
            roi = safe_divide(incremental_value - total_cost, total_cost, 0)
            
            channel_result = ChannelAttributionResult(
                channel=channel,
                total_touches=touches,
                unique_users=unique_users,
                responses=responses,
                response_rate=float(safe_divide(responses, touches, 0)),
                churn_prevented=churn_prevented,
                churn_rate_treated=float(churn_treated),
                churn_rate_control=float(churn_control),
                uplift=float(uplift),
                incremental_value=float(incremental_value),
                cost_per_acquisition=float(cpa),
                roi=float(roi),
                confidence=float(self._calc_confidence(channel_treated["churned"], control_df["churned"])),
                statistical_significance=float(self._calc_p_value(channel_treated["churned"], control_df["churned"]))
            )
            
            self.channel_results[channel] = channel_result
            results["channel_attribution"][channel] = self._result_to_dict(channel_result)
            
            results["by_channel"][channel] = {
                "churn_prevented": churn_prevented,
                "uplift": float(uplift),
                "roi": float(roi),
                "cost": total_cost,
                "incremental_value": float(incremental_value)
            }
        
        for action in self.action_types:
            action_users = [tp.user_id for tp in self.touchpoints if tp.action_type == action]
            action_treated = treated_df[treated_df["user_id"].isin(action_users)]
            
            if len(action_treated) == 0 or len(control_df) == 0:
                continue
            
            churn_treated = action_treated["churned"].mean()
            churn_control = control_df["churned"].mean()
            uplift = churn_control - churn_treated
            
            results["by_action"][action] = {
                "churn_prevented": int(len(action_treated) * uplift),
                "uplift": float(uplift),
                "response_rate": float(safe_divide(
                    sum(1 for tp in self.touchpoints if tp.action_type == action and tp.responded),
                    sum(1 for tp in self.touchpoints if tp.action_type == action),
                    0
                ))
            }
        
        results["recommendations"] = self._generate_recommendations(results)
        
        return results

    def run_multi_touch_attribution(self, user_id: str, churn_event_time: float) -> Dict[str, float]:
        user_tps = sorted(
            [tp for tp in self.user_touchpoints.get(user_id, [])
             if tp.timestamp < churn_event_time and 
                churn_event_time - tp.timestamp < self.attribution_window_days * 86400],
            key=lambda x: x.timestamp
        )
        
        if not user_tps:
            return {}
        
        attributions = defaultdict(float)
        n = len(user_tps)
        
        for i, tp in enumerate(user_tps):
            time_decay = np.exp(-0.1 * (churn_event_time - tp.timestamp) / 86400)
            position_weight = self._get_position_weight(i, n)
            
            weight = time_decay * position_weight
            attributions[tp.channel] += weight
            attributions[f"{tp.channel}_{tp.action_type}"] += weight
        
        total = sum(attributions.values())
        if total > 0:
            for key in attributions:
                attributions[key] = attributions[key] / total
        
        return dict(attributions)

    def generate_attribution_report(self) -> Dict[str, Any]:
        report = {
            "timestamp": datetime.now().isoformat(),
            "attribution_window_days": self.attribution_window_days,
            "total_touchpoints": len(self.touchpoints),
            "total_responses": sum(1 for tp in self.touchpoints if tp.responded),
            "unique_users_reached": len(self.user_touchpoints),
            "channel_performance": {},
            "best_performing_channels": [],
            "underperforming_channels": [],
            "action_effectiveness": {},
            "key_insights": []
        }
        
        for channel, result in sorted(
            self.channel_results.items(), key=lambda x: x[1].uplift, reverse=True
        ):
            report["channel_performance"][channel] = self._result_to_dict(result)
            
            if result.uplift > 0.05 and result.confidence > 0.8:
                report["best_performing_channels"].append({
                    "channel": channel,
                    "uplift": result.uplift,
                    "roi": result.roi
                })
                report["key_insights"].append(
                    f"{channel.upper()} channel delivers {result.uplift*100:.1f}% uplift "
                    f"with {result.roi*100:.0f}% ROI"
                )
            elif result.uplift < 0.01:
                report["underperforming_channels"].append({
                    "channel": channel,
                    "uplift": result.uplift,
                    "roi": result.roi
                })
        
        action_effectiveness = defaultdict(list)
        for tp in self.touchpoints:
            if tp.responded:
                action_effectiveness[tp.action_type].append(tp.response_delay_hours)
        
        for action, delays in action_effectiveness.items():
            report["action_effectiveness"][action] = {
                "avg_response_delay_hours": float(np.mean(delays)),
                "response_count": len(delays)
            }
        
        best_channel = max(
            self.channel_results.values(), key=lambda x: x.uplift
        ) if self.channel_results else None
        worst_channel = min(
            self.channel_results.values(), key=lambda x: x.uplift
        ) if self.channel_results else None
        
        if best_channel and worst_channel and best_channel.uplift > worst_channel.uplift:
            diff_pct = safe_divide(best_channel.uplift - worst_channel.uplift, 
                                  max(abs(worst_channel.uplift), 0.001), 0) * 100
            report["key_insights"].append(
                f"Best channel '{best_channel.channel}' outperforms worst "
                f"'{worst_channel.channel}' by {diff_pct:.0f}% in churn reduction"
            )
        
        return report

    def _get_position_weight(self, position: int, total: int) -> float:
        if total == 1:
            return 1.0
        if position == total - 1:
            return 0.5
        elif position == 0:
            return 0.3
        else:
            return 0.2 / (total - 2)

    def _estimate_user_value(self) -> float:
        return self.config.get("attribution", {}).get("average_user_value", 100.0)

    def _is_significant(self, treated: pd.Series, control: pd.Series) -> bool:
        return self._calc_p_value(treated, control) < 0.05

    def _calc_p_value(self, treated: pd.Series, control: pd.Series) -> float:
        if len(treated) < 5 or len(control) < 5:
            return 1.0
        
        p1 = treated.mean()
        p2 = control.mean()
        n1 = len(treated)
        n2 = len(control)
        
        p_pooled = (p1 * n1 + p2 * n2) / (n1 + n2)
        se_pooled = np.sqrt(p_pooled * (1 - p_pooled) * (1/n1 + 1/n2))
        
        if se_pooled == 0:
            return 1.0
        
        z_score = (p1 - p2) / se_pooled
        
        p_value = 2 * (1 - self._norm_cdf(abs(z_score)))
        return float(p_value)

    def _calc_confidence(self, treated: pd.Series, control: pd.Series) -> float:
        p_value = self._calc_p_value(treated, control)
        return float(1.0 - p_value)

    def _norm_cdf(self, x: float) -> float:
        return 0.5 * (1 + math.erf(x / np.sqrt(2)))

    def _result_to_dict(self, result: ChannelAttributionResult) -> Dict[str, Any]:
        return {
            "channel": result.channel,
            "total_touches": result.total_touches,
            "unique_users": result.unique_users,
            "responses": result.responses,
            "response_rate": result.response_rate,
            "churn_prevented": result.churn_prevented,
            "churn_rate_treated": result.churn_rate_treated,
            "churn_rate_control": result.churn_rate_control,
            "uplift": result.uplift,
            "uplift_percentage": f"{result.uplift*100:.1f}%",
            "incremental_value": result.incremental_value,
            "cost_per_acquisition": result.cost_per_acquisition,
            "roi": result.roi,
            "roi_percentage": f"{result.roi*100:.0f}%",
            "confidence": result.confidence,
            "statistical_significance": result.statistical_significance,
            "is_significant": result.statistical_significance < 0.05
        }

    def _generate_recommendations(self, results: Dict[str, Any]) -> List[Dict[str, Any]]:
        recommendations = []
        
        channel_attribution = results.get("channel_attribution", {})
        
        for channel, data in sorted(
            channel_attribution.items(), key=lambda x: x[1]["uplift"], reverse=True
        ):
            if data["uplift"] > 0.05 and data["confidence"] > 0.8:
                recommendations.append({
                    "type": "increase_budget",
                    "channel": channel,
                    "action": f"Increase investment in {channel}",
                    "rationale": f"Delivers {data['uplift']*100:.1f}% uplift with {data['roi']*100:.0f}% ROI",
                    "priority": "high"
                })
            elif data["uplift"] < 0.01 and data["confidence"] > 0.7:
                recommendations.append({
                    "type": "optimize_or_pause",
                    "channel": channel,
                    "action": f"Optimize or reduce investment in {channel}",
                    "rationale": f"Low uplift ({data['uplift']*100:.1f}%) and ROI ({data['roi']*100:.0f}%)",
                    "priority": "medium"
                })
        
        by_action = results.get("by_action", {})
        for action, data in sorted(
            by_action.items(), key=lambda x: x[1]["uplift"], reverse=True
        )[:3]:
            recommendations.append({
                "type": "promote_action",
                "action_type": action,
                "action": f"Prioritize {action} campaigns",
                "rationale": f"Prevents {data['churn_prevented']} churns with {data['uplift']*100:.1f}% uplift",
                "priority": "medium"
            })
        
        return recommendations


def main():
    if not NUMPY_AVAILABLE:
        print("numpy/pandas not available. Cannot run attribution demo.")
        return
    
    print("=" * 70)
    print("TOUCHPOINT ATTRIBUTION ANALYZER")
    print("=" * 70)
    
    analyzer = TouchpointAttributionAnalyzer()
    
    print("\n" + "-" * 70)
    print("Generating synthetic touchpoint data...")
    print("-" * 70)
    
    np.random.seed(42)
    n_users = 300
    user_ids = [f"user_{i:04d}" for i in range(n_users)]
    
    group_assignments = analyzer.assign_control_groups(user_ids)
    
    channels = ["push", "email", "sms", "in_app"]
    actions = ["discount_offer", "personalized_recommendation", "winback_campaign"]
    channel_costs = {"push": 0.1, "email": 0.5, "sms": 1.0, "in_app": 0.05}
    
    for i in range(500):
        user_id = np.random.choice(user_ids)
        if group_assignments[user_id] == "treatment":
            channel = np.random.choice(channels, p=[0.4, 0.3, 0.15, 0.15])
            action = np.random.choice(actions)
            timestamp = time.time() - np.random.randint(0, 14) * 86400
            
            tp = analyzer.record_touchpoint(
                user_id=user_id,
                channel=channel,
                action_type=action,
                timestamp=timestamp,
                cost=channel_costs[channel]
            )
            
            if np.random.random() < 0.3:
                analyzer.record_response(
                    user_id=user_id,
                    touchpoint_timestamp=tp.timestamp,
                    response_timestamp=tp.timestamp + np.random.randint(1, 72) * 3600
                )
    
    churn_data = []
    for user_id in user_ids:
        base_churn = 0.35
        if group_assignments[user_id] == "treatment":
            user_tps = analyzer.user_touchpoints.get(user_id, [])
            if user_tps:
                channel_effect = {
                    "push": 0.85, "email": 0.75, "sms": 0.7, "in_app": 0.9
                }
                min_effect = min(channel_effect.get(tp.channel, 1.0) for tp in user_tps)
                churn_prob = base_churn * min_effect
            else:
                churn_prob = base_churn
        else:
            churn_prob = base_churn
        
        churned = np.random.random() < churn_prob
        churn_data.append({
            "user_id": user_id,
            "churned": int(churned),
            "group": group_assignments[user_id]
        })
    
    print(f"Generated {len(analyzer.touchpoints)} touchpoints for {n_users} users")
    
    print("\n" + "-" * 70)
    print("Analyzing treatment effects...")
    print("-" * 70)
    
    results = analyzer.analyze_treatment_effects(churn_data, group_assignments)
    
    print(f"\nOverall Results:")
    overall = results["overall"]
    print(f"  Treatment size: {overall['treatment_size']}, Control size: {overall['control_size']}")
    print(f"  Churn rate - Treated: {overall['churn_rate_treated']*100:.1f}%")
    print(f"  Churn rate - Control: {overall['churn_rate_control']*100:.1f}%")
    print(f"  Uplift: {overall['uplift_absolute']*100:.2f}% (relative: {overall['uplift_relative']*100:.1f}%)")
    print(f"  Churn prevented: {overall['churn_prevented']}")
    print(f"  Statistically significant: {overall['statistically_significant']}")
    
    print("\n" + "-" * 70)
    print("CHANNEL PERFORMANCE")
    print("-" * 70)
    
    for channel, data in sorted(
        results["channel_attribution"].items(), key=lambda x: x[1]["uplift"], reverse=True
    ):
        print(f"\n  {channel.upper()}:")
        print(f"    Touches: {data['total_touches']}, Responses: {data['responses']}")
        print(f"    Response rate: {data['response_rate']*100:.1f}%")
        print(f"    Uplift: {data['uplift_percentage']}")
        print(f"    Churn prevented: {data['churn_prevented']}")
        print(f"    ROI: {data['roi_percentage']}")
        print(f"    Confidence: {data['confidence']*100:.0f}%")
        print(f"    Significant: {data['is_significant']}")
    
    print("\n" + "-" * 70)
    print("RECOMMENDATIONS")
    print("-" * 70)
    
    for rec in results["recommendations"][:5]:
        print(f"\n  [{rec['priority'].upper()}] {rec['action']}")
        print(f"    Rationale: {rec['rationale']}")
    
    print("\n" + "-" * 70)
    print("MULTI-TOUCH ATTRIBUTION EXAMPLE")
    print("-" * 70)
    
    sample_user = user_ids[0]
    attr = analyzer.run_multi_touch_attribution(sample_user, time.time())
    print(f"\n  User: {sample_user}")
    for channel, weight in sorted(attr.items(), key=lambda x: x[1], reverse=True):
        print(f"    {channel}: {weight*100:.1f}%")
    
    print("\n" + "-" * 70)
    print("ATTRIBUTION REPORT")
    print("-" * 70)
    
    report = analyzer.generate_attribution_report()
    for insight in report["key_insights"]:
        print(f"  - {insight}")
    
    print("\n" + "=" * 70)


if __name__ == "__main__":
    main()
