import uuid
import json
from datetime import datetime
from typing import Dict, List, Any, Optional

from config import (
    INDUSTRY_MONITORING_CONFIG, INDUSTRY_RISK_BASELINES,
    get_industry_config, get_industry_baseline
)


class PostLoanMonitor:
    def __init__(self):
        self.alerts: Dict[str, List[Dict[str, Any]]] = {}
        self.baseline_scores: Dict[str, float] = {}
        self.score_history: Dict[str, List[Dict[str, Any]]] = {}
        self.company_industries: Dict[str, str] = {}

    def register_loan(
        self, company_id: str, baseline_score: float, industry: str = "default"
    ) -> None:
        self.baseline_scores[company_id] = baseline_score
        self.company_industries[company_id] = industry

        if company_id not in self.score_history:
            self.score_history[company_id] = []
        self.score_history[company_id].append({
            "score": baseline_score,
            "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "event": "initial_assessment"
        })
        if company_id not in self.alerts:
            self.alerts[company_id] = []

    def _get_industry_config(self, company_id: str) -> dict:
        industry = self.company_industries.get(company_id, "default")
        return get_industry_config(industry), industry

    def _get_industry_baseline(self, company_id: str) -> dict:
        industry = self.company_industries.get(company_id, "default")
        return get_industry_baseline(industry), industry

    def update_score(self, company_id: str, new_score: float) -> List[Dict[str, Any]]:
        industry_config, industry = self._get_industry_config(company_id)
        baseline = self.baseline_scores.get(company_id, new_score)
        score_change = new_score - baseline

        self.score_history[company_id].append({
            "score": new_score,
            "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "event": "periodic_update"
        })

        new_alerts = []

        alert_threshold = industry_config.get("score_drop_alert_threshold", 50)
        warning_threshold = industry_config.get("score_warning_threshold", 30)

        if score_change <= -alert_threshold:
            alert = self._create_score_change_alert(
                company_id, baseline, new_score, score_change, "critical", industry
            )
            new_alerts.append(alert)
            self.alerts[company_id].append(alert)
        elif score_change <= -warning_threshold:
            alert = self._create_score_change_alert(
                company_id, baseline, new_score, score_change, "warning", industry
            )
            new_alerts.append(alert)
            self.alerts[company_id].append(alert)

        return new_alerts

    def report_negative_event(
        self,
        company_id: str,
        event_type: str,
        description: str,
        event_date: str = None
    ) -> Dict[str, Any]:
        if event_date is None:
            event_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        industry_config, industry = self._get_industry_config(company_id)
        event_weights = industry_config.get("negative_event_weight", {})
        impact_score = event_weights.get(event_type, 10)

        alert_level = self._determine_alert_level(impact_score)

        alert = {
            "alert_id": str(uuid.uuid4()),
            "company_id": company_id,
            "alert_type": event_type,
            "alert_level": alert_level,
            "description": description,
            "event_date": event_date,
            "impact_score": impact_score,
            "industry": industry,
            "recommended_action": self._get_recommended_action(event_type, alert_level),
            "status": "active"
        }

        if company_id not in self.alerts:
            self.alerts[company_id] = []
        self.alerts[company_id].append(alert)

        current_score = self._get_latest_score(company_id)
        adjusted_score = max(0, current_score - impact_score * 0.5)
        self.score_history[company_id].append({
            "score": adjusted_score,
            "date": event_date,
            "event": f"negative_event_{event_type}"
        })

        return alert

    def generate_monitoring_report(self, company_id: str) -> Dict[str, Any]:
        baseline = self.baseline_scores.get(company_id, 0)
        current = self._get_latest_score(company_id)
        score_change = current - baseline

        industry = self.company_industries.get(company_id, "default")
        industry_baseline_info = get_industry_baseline(industry)

        company_alerts = self.alerts.get(company_id, [])
        active_alerts = [a for a in company_alerts if a.get("status") == "active"]

        industry_warning_line = self._calculate_industry_warning_line(
            industry, current, score_change, active_alerts
        )

        risk_assessment = self._assess_risk(current, score_change, active_alerts, industry)

        return {
            "company_id": company_id,
            "industry": industry,
            "current_score": round(current, 2),
            "baseline_score": round(baseline, 2),
            "score_change": round(score_change, 2),
            "score_change_percent": round((score_change / baseline) * 100, 2) if baseline > 0 else 0,
            "industry_baseline_score": industry_baseline_info.get("baseline_score", 600),
            "industry_warning_line": industry_warning_line,
            "alert_count": len(active_alerts),
            "alerts": active_alerts,
            "risk_assessment": risk_assessment,
            "monitoring_status": self._get_monitoring_status(
                score_change, active_alerts, industry
            ),
            "score_history": self.score_history.get(company_id, [])[-10:],
            "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

    def get_industry_warning_lines(self) -> Dict[str, Dict[str, Any]]:
        result = {}
        for industry, baseline_info in INDUSTRY_RISK_BASELINES.items():
            industry_config = get_industry_config(industry)
            baseline_score = baseline_info.get("baseline_score", 600)
            volatility = baseline_info.get("volatility", 0.18)
            warning_drop = industry_config.get("score_warning_threshold", 30)
            alert_drop = industry_config.get("score_drop_alert_threshold", 50)

            result[industry] = {
                "baseline_score": baseline_score,
                "volatility": volatility,
                "warning_line": round(baseline_score - baseline_score * volatility, 1),
                "critical_line": round(baseline_score - baseline_score * volatility * 1.5, 1),
                "score_drop_warning_threshold": warning_drop,
                "score_drop_alert_threshold": alert_drop,
                "check_interval_days": industry_config.get("check_interval_days", 30),
            }
        return result

    def get_all_alerts(self, company_id: str = None, alert_level: str = None) -> List[Dict[str, Any]]:
        result = []
        if company_id:
            alerts = self.alerts.get(company_id, [])
        else:
            for cid, alist in self.alerts.items():
                result.extend(alist)
            return result

        for alert in alerts:
            if alert_level is None or alert["alert_level"] == alert_level:
                result.append(alert)

        return result

    def dismiss_alert(self, alert_id: str) -> bool:
        for cid, alerts in self.alerts.items():
            for alert in alerts:
                if alert["alert_id"] == alert_id:
                    alert["status"] = "dismissed"
                    return True
        return False

    def update_company_industry(self, company_id: str, industry: str) -> None:
        self.company_industries[company_id] = industry

    def _create_score_change_alert(
        self, company_id: str, baseline: float, current: float, change: float,
        alert_level: str, industry: str
    ) -> Dict[str, Any]:
        direction = "下降" if change < 0 else "上升"

        return {
            "alert_id": str(uuid.uuid4()),
            "company_id": company_id,
            "alert_type": "score_change",
            "alert_level": alert_level,
            "industry": industry,
            "description": f"信用评分{direction}：{baseline:.0f} → {current:.0f}（变化：{change:+.1f}）",
            "event_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "impact_score": abs(change),
            "recommended_action": self._get_score_change_action(change, alert_level),
            "status": "active"
        }

    def _determine_alert_level(self, impact_score: float) -> str:
        if impact_score >= 60:
            return "critical"
        elif impact_score >= 30:
            return "warning"
        else:
            return "info"

    def _get_recommended_action(self, event_type: str, alert_level: str) -> str:
        actions = {
            "lawsuit": "立即核实诉讼情况，评估对企业经营的影响，要求企业提供诉讼进展报告",
            "executed_person": "重点关注，评估是否影响还款能力，考虑要求增加担保或提前还款",
            "tax_arrears": "核实欠税金额和原因，评估对企业信用的影响，要求限期补缴",
            "abnormal_operation": "深入调查经营异常原因，增加现场检查频率，评估持续经营能力",
            "administrative_penalty": "核实处罚原因和金额，评估对企业合规性的影响",
            "contract_breach": "评估违约对企业声誉和供应链的影响，关注后续合同履行情况",
            "patent_invalidation": "评估专利失效对企业核心竞争力的影响，关注知识产权布局",
        }
        return actions.get(event_type, "持续关注该事件进展，评估对企业信用的影响")

    def _get_score_change_action(self, change: float, alert_level: str) -> str:
        if change < 0:
            if alert_level == "critical":
                return "信用评分大幅下降，建议立即进行风险评估，考虑调整授信策略或要求追加担保"
            else:
                return "信用评分出现下降，建议加强监测频率，关注企业经营状况变化"
        else:
            if alert_level == "critical":
                return "信用评分大幅上升，可考虑提升客户等级，适当增加授信额度"
            else:
                return "信用评分有所提升，可维持现有授信政策"

    def _calculate_industry_warning_line(
        self, industry: str, current: float, score_change: float,
        alerts: List[Dict]
    ) -> float:
        baseline_info = get_industry_baseline(industry)
        baseline = baseline_info.get("baseline_score", 600)
        volatility = baseline_info.get("volatility", 0.18)
        return round(baseline - baseline * volatility, 1)

    def _assess_risk(
        self, current_score: float, score_change: float,
        alerts: List[Dict], industry: str
    ) -> str:
        baseline_info = get_industry_baseline(industry)
        industry_baseline = baseline_info.get("baseline_score", 600)
        volatility = baseline_info.get("volatility", 0.18)

        warning_line = industry_baseline - industry_baseline * volatility
        critical_line = industry_baseline - industry_baseline * volatility * 1.5

        if current_score >= industry_baseline and score_change >= 0:
            return "低风险"
        elif current_score >= warning_line and score_change > -industry_baseline * volatility * 0.5:
            return "中等风险"
        elif current_score >= critical_line:
            return "较高风险"
        else:
            return "高风险"

    def _get_monitoring_status(
        self, score_change: float, alerts: List[Dict], industry: str
    ) -> str:
        industry_config = get_industry_config(industry)
        alert_threshold = industry_config.get("score_drop_alert_threshold", 50)
        warning_threshold = industry_config.get("score_warning_threshold", 30)

        critical_alerts = [a for a in alerts if a["alert_level"] == "critical"]
        if critical_alerts or score_change <= -alert_threshold:
            return "需紧急关注"
        elif alerts or score_change <= -warning_threshold:
            return "重点监测"
        elif score_change < 0:
            return "常规监测"
        else:
            return "正常"

    def _get_latest_score(self, company_id: str) -> float:
        history = self.score_history.get(company_id, [])
        if history:
            return history[-1]["score"]
        return self.baseline_scores.get(company_id, 500)


_global_monitor = PostLoanMonitor()


def get_monitor() -> PostLoanMonitor:
    return _global_monitor
