from typing import List, Dict, Any
import numpy as np
from datetime import datetime, timedelta


class AgentRankingSystem:
    def __init__(self):
        self.weights = {
            "comprehensive": 0.35,
            "customer_satisfaction": 0.25,
            "service_emotion": 0.20,
            "response_speed": 0.10,
            "script_quality": 0.10
        }
        
        self.badge_rules = {
            "gold": {"threshold": 90, "icon": "🥇", "name": "金牌客服"},
            "silver": {"threshold": 80, "icon": "🥈", "name": "银牌客服"},
            "bronze": {"threshold": 70, "icon": "🥉", "name": "铜牌客服"}
        }

    def calculate_agent_rankings(self, all_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        agent_data = self._aggregate_agent_data(all_results)
        
        rankings = []
        for agent_id, data in agent_data.items():
            final_score = self._calculate_final_score(data)
            badge = self._get_badge(final_score)
            rankings.append({
                "agent_id": agent_id,
                "final_score": round(final_score, 2),
                "badge": badge,
                "metrics": data,
                "rank": 0
            })
        
        rankings.sort(key=lambda x: x["final_score"], reverse=True)
        for i, r in enumerate(rankings):
            r["rank"] = i + 1
        
        return {
            "rankings": rankings,
            "total_agents": len(rankings),
            "avg_team_score": round(np.mean([r["final_score"] for r in rankings]), 2),
            "badge_distribution": self._get_badge_distribution(rankings),
            "top_performers": rankings[:3],
            "needs_improvement": rankings[-3:] if len(rankings) > 3 else []
        }

    def _aggregate_agent_data(self, all_results: List[Dict[str, Any]]) -> Dict[str, Dict]:
        agent_data = {}
        
        for result in all_results:
            agent_id = result["agent_id"]
            if agent_id not in agent_data:
                agent_data[agent_id] = {
                    "conversation_count": 0,
                    "comprehensive_scores": [],
                    "satisfaction_scores": [],
                    "emotion_scores": [],
                    "speed_scores": [],
                    "deduction_count": 0,
                    "high_score_count": 0
                }
            
            data = agent_data[agent_id]
            data["conversation_count"] += 1
            data["comprehensive_scores"].append(result["comprehensive_score"])
            data["satisfaction_scores"].append(result["dimension_scores"]["customer_satisfaction"]["score"])
            data["emotion_scores"].append(result["dimension_scores"]["service_emotion"]["score"])
            data["speed_scores"].append(result["dimension_scores"]["response_speed"]["score"])
            data["deduction_count"] += len(result.get("deductions", []))
            
            if result["comprehensive_score"] >= 85:
                data["high_score_count"] += 1
        
        for agent_id, data in agent_data.items():
            data["avg_comprehensive"] = round(np.mean(data["comprehensive_scores"]), 2)
            data["avg_satisfaction"] = round(np.mean(data["satisfaction_scores"]), 2)
            data["avg_emotion"] = round(np.mean(data["emotion_scores"]), 2)
            data["avg_speed"] = round(np.mean(data["speed_scores"]), 2)
            data["high_score_rate"] = round(data["high_score_count"] / data["conversation_count"] * 100, 2)
            data["deductions_per_conv"] = round(data["deduction_count"] / data["conversation_count"], 2)
            data["script_quality_score"] = self._calculate_script_quality_score(data)
        
        return agent_data

    def _calculate_script_quality_score(self, data: Dict) -> float:
        base_score = 70.0
        
        base_score += data["high_score_rate"] * 0.2
        base_score -= data["deductions_per_conv"] * 5
        
        if data["avg_emotion"] >= 80:
            base_score += 10
        
        return min(100, max(0, base_score))

    def _calculate_final_score(self, data: Dict) -> float:
        score = (
            data["avg_comprehensive"] * self.weights["comprehensive"] +
            data["avg_satisfaction"] * self.weights["customer_satisfaction"] +
            data["avg_emotion"] * self.weights["service_emotion"] +
            data["avg_speed"] * self.weights["response_speed"] +
            data["script_quality_score"] * self.weights["script_quality"]
        )
        
        bonus = 0
        if data["high_score_rate"] >= 80:
            bonus += 3
        elif data["high_score_rate"] >= 60:
            bonus += 1.5
        
        if data["deductions_per_conv"] < 0.5:
            bonus += 2
        
        return min(100, score + bonus)

    def _get_badge(self, score: float) -> Dict[str, str]:
        if score >= self.badge_rules["gold"]["threshold"]:
            return self.badge_rules["gold"]
        elif score >= self.badge_rules["silver"]["threshold"]:
            return self.badge_rules["silver"]
        elif score >= self.badge_rules["bronze"]["threshold"]:
            return self.badge_rules["bronze"]
        else:
            return {"threshold": 0, "icon": "💪", "name": "新秀客服"}

    def _get_badge_distribution(self, rankings: List[Dict]) -> Dict[str, int]:
        distribution = {"gold": 0, "silver": 0, "bronze": 0, "rookie": 0}
        for r in rankings:
            badge_name = r["badge"]["name"]
            if "金牌" in badge_name:
                distribution["gold"] += 1
            elif "银牌" in badge_name:
                distribution["silver"] += 1
            elif "铜牌" in badge_name:
                distribution["bronze"] += 1
            else:
                distribution["rookie"] += 1
        return distribution

    def get_dimension_rankings(self, all_results: List[Dict[str, Any]], 
                                dimension: str) -> List[Dict[str, Any]]:
        agent_data = self._aggregate_agent_data(all_results)
        
        dimension_map = {
            "comprehensive": "avg_comprehensive",
            "satisfaction": "avg_satisfaction",
            "emotion": "avg_emotion",
            "speed": "avg_speed"
        }
        
        key = dimension_map.get(dimension, "avg_comprehensive")
        
        rankings = []
        for agent_id, data in agent_data.items():
            rankings.append({
                "agent_id": agent_id,
                "score": data[key],
                "conversation_count": data["conversation_count"]
            })
        
        rankings.sort(key=lambda x: x["score"], reverse=True)
        for i, r in enumerate(rankings):
            r["rank"] = i + 1
        
        return rankings

    def generate_incentive_recommendations(self, rankings: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        recommendations = []
        
        for r in rankings:
            agent_id = r["agent_id"]
            score = r["final_score"]
            badge = r["badge"]
            
            incentives = []
            
            if "金牌" in badge["name"]:
                incentives.append("🌟 月度之星荣誉称号")
                incentives.append("💰 绩效奖金 +20%")
                incentives.append("📚 优先参加进阶培训")
                incentives.append("🎯 纳入骨干人才培养计划")
            elif "银牌" in badge["name"]:
                incentives.append("✨ 优秀员工表彰")
                incentives.append("💰 绩效奖金 +10%")
                incentives.append("📚 专业技能培训名额")
            elif "铜牌" in badge["name"]:
                incentives.append("👍 良好表现认可")
                incentives.append("📚 基础能力提升培训")
                incentives.append("🎯 一对一导师指导")
            else:
                incentives.append("💪 加油！持续进步")
                incentives.append("📚 新人成长培训")
                incentives.append("🎯 设置月度进步目标")
            
            next_badge = self._get_next_badge(score)
            if next_badge:
                gap = round(next_badge["threshold"] - score, 2)
                incentives.append(f"📈 距离{next_badge['name']}还差 {gap} 分")
            
            recommendations.append({
                "agent_id": agent_id,
                "current_badge": badge,
                "score": score,
                "incentives": incentives,
                "next_goal": next_badge
            })
        
        return recommendations

    def _get_next_badge(self, current_score: float) -> Dict[str, Any]:
        if current_score < 70:
            return self.badge_rules["bronze"]
        elif current_score < 80:
            return self.badge_rules["silver"]
        elif current_score < 90:
            return self.badge_rules["gold"]
        else:
            return None

    def get_team_trend_analysis(self, all_results: List[Dict[str, Any]], 
                                  period_days: int = 30) -> Dict[str, Any]:
        current_date = datetime.now()
        period_start = current_date - timedelta(days=period_days)
        
        scores_by_date = {}
        for result in all_results:
            try:
                conv_date = datetime.fromisoformat(result["timestamp"].replace('Z', '+00:00'))
                date_key = conv_date.strftime("%Y-%m-%d")
                if conv_date >= period_start:
                    if date_key not in scores_by_date:
                        scores_by_date[date_key] = []
                    scores_by_date[date_key].append(result["comprehensive_score"])
            except:
                continue
        
        if not scores_by_date:
            return {"trend": "stable", "change": 0}
        
        sorted_dates = sorted(scores_by_date.keys())
        if len(sorted_dates) >= 2:
            first_week_avg = np.mean([
                score for date in sorted_dates[:7] 
                for score in scores_by_date[date]
            ])
            last_week_avg = np.mean([
                score for date in sorted_dates[-7:] 
                for score in scores_by_date[date]
            ])
            change_pct = round((last_week_avg - first_week_avg) / first_week_avg * 100, 2)
            
            if change_pct > 5:
                trend = "up"
            elif change_pct < -5:
                trend = "down"
            else:
                trend = "stable"
        else:
            change_pct = 0
            trend = "stable"
        
        return {
            "trend": trend,
            "change_pct": change_pct,
            "daily_scores": {
                date: round(np.mean(scores), 2) 
                for date, scores in scores_by_date.items()
            }
        }
