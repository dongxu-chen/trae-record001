from fastapi import APIRouter, HTTPException, Query, Depends
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta

from app.clients.skywalking import skywalking_client
from app.models.alert import (
    Alert,
    AlertRule,
    AlertCluster,
    InefficientRule,
    OptimizationSuggestion,
    AnalysisReport,
    RuleOptimizationResult,
    EvaluationResult,
)
from app.analysis.clustering import alert_clustering
from app.analysis.rule_analyzer import rule_analyzer
from app.analysis.optimizer import rule_optimizer
from app.analysis.evaluator import rule_evaluator
from app.analysis.rule_generator import rule_generator
from app.analysis.suppression_optimizer import suppression_optimizer
from app.analysis.alert_review import alert_reviewer
from app.config import settings

router = APIRouter(prefix="/api/v1", tags=["skywalking-alert-optimizer"])


@router.get("/health")
async def health_check():
    connection_ok = await skywalking_client.test_connection()
    return {
        "status": "healthy",
        "skywalking_connected": connection_ok,
        "mock_mode": skywalking_client.use_mock,
        "timestamp": datetime.now().isoformat(),
    }


@router.get("/alerts", response_model=List[Alert])
async def get_alerts(
    lookback_hours: int = Query(settings.default_lookback_hours, ge=1, le=720),
    rule_name: Optional[str] = None,
    service: Optional[str] = None,
    priority: Optional[str] = None,
):
    try:
        alerts_data = await skywalking_client.get_alerts(
            lookback_hours=lookback_hours,
            rule_name=rule_name,
            service=service,
            priority=priority,
        )
        alerts = [Alert(**item) for item in alerts_data]
        return alerts
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取告警数据失败: {str(e)}")


@router.get("/rules", response_model=List[AlertRule])
async def get_rules():
    try:
        rules_data = await skywalking_client.get_rules()
        rules = [AlertRule(**item) for item in rules_data]
        return rules
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取规则配置失败: {str(e)}")


@router.get("/alerts/clusters", response_model=Dict[str, Any])
async def get_alert_clusters(
    lookback_hours: int = Query(settings.default_lookback_hours, ge=1, le=720),
    min_samples: int = Query(5, ge=2, le=50),
    eps_time: float = Query(300.0, ge=60.0, le=3600.0),
):
    try:
        alerts_data = await skywalking_client.get_alerts(lookback_hours=lookback_hours)
        alerts = [Alert(**item) for item in alerts_data]

        if not alerts:
            return {"clusters": [], "summary": {"total_clusters": 0}}

        alert_clustering.min_samples = min_samples
        alert_clustering.eps_time = eps_time

        clusters = alert_clustering.cluster_alerts(alerts)
        similar_pairs = alert_clustering.find_similar_clusters(clusters)
        summary = alert_clustering.get_cluster_summary(clusters)

        return {
            "clusters": clusters,
            "similar_pairs": similar_pairs,
            "summary": summary,
            "total_alerts": len(alerts),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"告警聚类分析失败: {str(e)}")


@router.get("/rules/inefficient", response_model=Dict[str, Any])
async def get_inefficient_rules(
    lookback_hours: int = Query(settings.default_lookback_hours, ge=1, le=720),
    min_inefficiency_score: float = Query(0.3, ge=0.0, le=1.0),
):
    try:
        alerts_data = await skywalking_client.get_alerts(lookback_hours=lookback_hours)
        rules_data = await skywalking_client.get_rules()

        alerts = [Alert(**item) for item in alerts_data]
        rules = [AlertRule(**item) for item in rules_data]

        if not alerts:
            return {"inefficient_rules": [], "statistics": {}}

        clusters = alert_clustering.cluster_alerts(alerts)
        inefficient_rules = rule_analyzer.analyze_inefficient_rules(
            alerts, rules, clusters
        )

        filtered_rules = [
            r for r in inefficient_rules
            if r.inefficiency_score >= min_inefficiency_score
        ]

        statistics = rule_analyzer.get_overall_statistics(alerts, filtered_rules)

        return {
            "inefficient_rules": filtered_rules,
            "statistics": statistics,
            "total_alerts_analyzed": len(alerts),
            "total_rules_analyzed": len(rules),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"低效规则分析失败: {str(e)}")


@router.get("/rules/optimize", response_model=Dict[str, Any])
async def get_optimization_suggestions(
    lookback_hours: int = Query(settings.default_lookback_hours, ge=1, le=720),
    min_confidence: float = Query(0.5, ge=0.0, le=1.0),
):
    try:
        alerts_data = await skywalking_client.get_alerts(lookback_hours=lookback_hours)
        rules_data = await skywalking_client.get_rules()

        alerts = [Alert(**item) for item in alerts_data]
        rules = [AlertRule(**item) for item in rules_data]

        if not alerts or not rules:
            return {"suggestions": [], "summary": {"total_suggestions": 0}}

        clusters = alert_clustering.cluster_alerts(alerts)
        inefficient_rules = rule_analyzer.analyze_inefficient_rules(
            alerts, rules, clusters
        )

        suggestions = rule_optimizer.generate_optimization_suggestions(
            alerts, inefficient_rules, rules, clusters
        )

        filtered_suggestions = [
            s for s in suggestions if s.confidence >= min_confidence
        ]

        summary = rule_optimizer.get_optimization_summary(filtered_suggestions)

        return {
            "suggestions": filtered_suggestions,
            "summary": summary,
            "total_alerts_analyzed": len(alerts),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"生成优化建议失败: {str(e)}")


@router.get("/rules/evaluate", response_model=Dict[str, Any])
async def evaluate_optimizations(
    lookback_hours: int = Query(settings.default_lookback_hours, ge=1, le=720),
):
    try:
        alerts_data = await skywalking_client.get_alerts(lookback_hours=lookback_hours)
        rules_data = await skywalking_client.get_rules()

        alerts = [Alert(**item) for item in alerts_data]
        rules = [AlertRule(**item) for item in rules_data]

        if not alerts or not rules:
            return {"evaluation_results": [], "overall": {}}

        clusters = alert_clustering.cluster_alerts(alerts)
        inefficient_rules = rule_analyzer.analyze_inefficient_rules(
            alerts, rules, clusters
        )
        suggestions = rule_optimizer.generate_optimization_suggestions(
            alerts, inefficient_rules, rules, clusters
        )

        evaluation_results = rule_evaluator.evaluate_optimization(
            alerts, suggestions, rules
        )
        overall_evaluation = rule_evaluator.get_overall_evaluation(evaluation_results)

        return {
            "evaluation_results": evaluation_results,
            "overall_evaluation": overall_evaluation,
            "total_evaluated_rules": len(suggestions),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"优化效果评估失败: {str(e)}")


@router.post("/rules/compare-configs", response_model=List[Dict[str, Any]])
async def compare_rule_configs(
    rule_name: str,
    configs: List[Dict[str, Any]],
    lookback_hours: int = Query(settings.default_lookback_hours, ge=1, le=720),
):
    try:
        alerts_data = await skywalking_client.get_alerts(lookback_hours=lookback_hours)
        alerts = [Alert(**item) for item in alerts_data]

        if not alerts:
            return []

        comparison = rule_evaluator.compare_configs(alerts, rule_name, configs)
        return comparison
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"配置对比失败: {str(e)}")


@router.get("/analysis/report", response_model=Dict[str, Any])
async def get_full_analysis_report(
    lookback_hours: int = Query(settings.default_lookback_hours, ge=1, le=720),
):
    try:
        alerts_data = await skywalking_client.get_alerts(lookback_hours=lookback_hours)
        rules_data = await skywalking_client.get_rules()

        alerts = [Alert(**item) for item in alerts_data]
        rules = [AlertRule(**item) for item in rules_data]

        if not alerts:
            return {
                "analysis_period": {
                    "start": int(
                        (datetime.now() - timedelta(hours=lookback_hours)).timestamp()
                        * 1000
                    ),
                    "end": int(datetime.now().timestamp() * 1000),
                },
                "total_alerts": 0,
                "unique_rules": 0,
                "clusters": [],
                "inefficient_rules": [],
                "optimization_suggestions": [],
                "overall_summary": {},
            }

        clusters = alert_clustering.cluster_alerts(alerts)
        inefficient_rules = rule_analyzer.analyze_inefficient_rules(
            alerts, rules, clusters
        )
        suggestions = rule_optimizer.generate_optimization_suggestions(
            alerts, inefficient_rules, rules, clusters
        )
        evaluation_results = rule_evaluator.evaluate_optimization(
            alerts, suggestions, rules
        )

        overall_stats = rule_analyzer.get_overall_statistics(alerts, inefficient_rules)
        optimization_summary = rule_optimizer.get_optimization_summary(suggestions)
        evaluation_summary = rule_evaluator.get_overall_evaluation(evaluation_results)

        timestamps = [a.start_time for a in alerts]

        report = {
            "analysis_period": {
                "start": int(min(timestamps)) if timestamps else 0,
                "end": int(max(timestamps)) if timestamps else 0,
                "lookback_hours": lookback_hours,
            },
            "total_alerts": len(alerts),
            "unique_rules": len(set(a.rule_name for a in alerts)),
            "unique_services": len(set(a.service for a in alerts)),
            "clusters": clusters,
            "cluster_summary": alert_clustering.get_cluster_summary(clusters),
            "inefficient_rules": inefficient_rules,
            "optimization_suggestions": suggestions,
            "evaluation_results": evaluation_results,
            "overall_summary": {
                **overall_stats,
                "optimization": optimization_summary,
                "evaluation": evaluation_summary,
                "generated_at": datetime.now().isoformat(),
            },
        }

        return report
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"生成分析报告失败: {str(e)}")


@router.put("/rules/{rule_id}")
async def update_rule(rule_id: int, rule_config: Dict[str, Any]):
    try:
        result = await skywalking_client.update_rule(rule_id, rule_config)
        return {"success": True, "data": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"更新规则失败: {str(e)}")


@router.get("/metrics/{metric_name}")
async def get_metrics(
    metric_name: str,
    service: Optional[str] = None,
    duration_hours: int = Query(24, ge=1, le=168),
):
    try:
        metrics_data = await skywalking_client.get_metrics(
            metric_name=metric_name, service=service, duration_hours=duration_hours
        )
        return {"metric_name": metric_name, "values": metrics_data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取指标数据失败: {str(e)}")


@router.get("/rules/generate")
async def generate_rules(
    lookback_hours: int = Query(settings.default_lookback_hours, ge=1, le=720),
    min_confidence: float = Query(0.6, ge=0.0, le=1.0),
):
    try:
        alerts_data = await skywalking_client.get_alerts(lookback_hours=lookback_hours)
        rules_data = await skywalking_client.get_rules()

        alerts = [Alert(**item) for item in alerts_data]
        rules = [AlertRule(**item) for item in rules_data]

        if not alerts:
            return {"generated_rules": [], "fault_events": [], "statistics": {}}

        clusters = alert_clustering.cluster_alerts(alerts)

        result = rule_generator.generate_rules(
            alerts, rules, clusters
        )

        filtered_rules = [
            r for r in result["generated_rules"]
            if r.confidence >= min_confidence
        ]

        result["generated_rules"] = filtered_rules
        result["total_alerts_analyzed"] = len(alerts)
        result["existing_rules_count"] = len(rules)

        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"生成规则失败: {str(e)}")


@router.post("/rules/generate/{rule_name}/apply")
async def apply_generated_rule(rule_name: str):
    try:
        alerts_data = await skywalking_client.get_alerts(lookback_hours=720)
        rules_data = await skywalking_client.get_rules()

        alerts = [Alert(**item) for item in alerts_data]
        rules = [AlertRule(**item) for item in rules_data]

        clusters = alert_clustering.cluster_alerts(alerts)
        result = rule_generator.generate_rules(alerts, rules, clusters)

        target_rule = None
        for rule in result["generated_rules"]:
            if rule.rule_name == rule_name:
                target_rule = rule
                break

        if not target_rule:
            raise HTTPException(status_code=404, detail=f"未找到生成规则: {rule_name}")

        template = rule_generator.get_rule_template(target_rule)
        new_rule_id = max(r.id for r in rules) + 1 if rules else 1
        template["id"] = new_rule_id

        return {
            "success": True,
            "rule": template,
            "message": "规则模板已生成，可直接导入SkyWalking",
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"应用生成规则失败: {str(e)}")


@router.get("/alerts/suppressions")
async def get_alert_suppressions(
    lookback_hours: int = Query(settings.default_lookback_hours, ge=1, le=720),
    min_confidence: float = Query(0.6, ge=0.0, le=1.0),
):
    try:
        alerts_data = await skywalking_client.get_alerts(lookback_hours=lookback_hours)
        rules_data = await skywalking_client.get_rules()

        alerts = [Alert(**item) for item in alerts_data]
        rules = [AlertRule(**item) for item in rules_data]

        if not alerts:
            return {
                "suppression_rules": [],
                "storm_patterns": [],
                "dependency_graph": {},
                "statistics": {},
            }

        clusters = alert_clustering.cluster_alerts(alerts)

        result = suppression_optimizer.optimize_suppressions(
            alerts, rules, clusters
        )

        filtered_rules = [
            r for r in result["suppression_rules"]
            if r.confidence >= min_confidence
        ]

        result["suppression_rules"] = filtered_rules
        result["total_alerts_analyzed"] = len(alerts)

        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"分析告警抑制失败: {str(e)}")


@router.post("/alerts/suppressions/simulate")
async def simulate_suppressions(
    lookback_hours: int = Query(settings.default_lookback_hours, ge=1, le=720),
):
    try:
        alerts_data = await skywalking_client.get_alerts(lookback_hours=lookback_hours)
        rules_data = await skywalking_client.get_rules()

        alerts = [Alert(**item) for item in alerts_data]
        rules = [AlertRule(**item) for item in rules_data]

        if not alerts:
            return {
                "original_count": 0,
                "suppressed_count": 0,
                "remaining_count": 0,
                "reduction_percent": 0.0,
                "suppression_details": [],
            }

        clusters = alert_clustering.cluster_alerts(alerts)
        opt_result = suppression_optimizer.optimize_suppressions(
            alerts, rules, clusters
        )

        sim_result = suppression_optimizer.simulate_suppression(
            alerts, opt_result["suppression_rules"]
        )

        return sim_result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"模拟告警抑制失败: {str(e)}")


@router.get("/alerts/review")
async def get_alert_review(
    lookback_hours: int = Query(settings.default_lookback_hours, ge=1, le=720),
    granularity: str = Query("hourly", regex="^(hourly|daily)$"),
    apply_optimizations: bool = Query(True),
    apply_suppressions: bool = Query(True),
):
    try:
        alerts_data = await skywalking_client.get_alerts(lookback_hours=lookback_hours)
        rules_data = await skywalking_client.get_rules()

        alerts = [Alert(**item) for item in alerts_data]
        rules = [AlertRule(**item) for item in rules_data]

        if not alerts:
            return {
                "review_period": {"start": 0, "end": 0},
                "time_series": [],
                "by_rule": [],
                "by_service": [],
                "by_priority": [],
                "summary": {"total_original": 0, "total_optimized": 0},
                "recommendations": [],
            }

        from app.analysis.alert_review import ReviewGranularity
        gran = ReviewGranularity(granularity)

        suggestions = []
        suppression_rules = None

        if apply_optimizations:
            clusters = alert_clustering.cluster_alerts(alerts)
            inefficient_rules = rule_analyzer.analyze_inefficient_rules(
                alerts, rules, clusters
            )
            suggestions = rule_optimizer.generate_optimization_suggestions(
                alerts, inefficient_rules, rules, clusters
            )

        if apply_suppressions:
            clusters = alert_clustering.cluster_alerts(alerts) if not suggestions else clusters
            opt_result = suppression_optimizer.optimize_suppressions(
                alerts, rules, clusters
            )
            suppression_rules = opt_result["suppression_rules"]

        report = alert_reviewer.generate_review_report(
            original_alerts=alerts,
            suggestions=suggestions,
            suppression_rules=suppression_rules,
            granularity=gran,
        )

        return report.model_dump()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"生成告警复盘失败: {str(e)}")


@router.get("/alerts/review/export")
async def export_alert_review(
    lookback_hours: int = Query(settings.default_lookback_hours, ge=1, le=720),
    format: str = Query("json", regex="^(json|csv)$"),
    granularity: str = Query("hourly", regex="^(hourly|daily)$"),
):
    try:
        alerts_data = await skywalking_client.get_alerts(lookback_hours=lookback_hours)
        rules_data = await skywalking_client.get_rules()

        alerts = [Alert(**item) for item in alerts_data]
        rules = [AlertRule(**item) for item in rules_data]

        if not alerts:
            return {"data": "", "format": format}

        from app.analysis.alert_review import ReviewGranularity
        gran = ReviewGranularity(granularity)

        clusters = alert_clustering.cluster_alerts(alerts)
        inefficient_rules = rule_analyzer.analyze_inefficient_rules(
            alerts, rules, clusters
        )
        suggestions = rule_optimizer.generate_optimization_suggestions(
            alerts, inefficient_rules, rules, clusters
        )

        report = alert_reviewer.generate_review_report(
            original_alerts=alerts,
            suggestions=suggestions,
            granularity=gran,
        )

        exported = alert_reviewer.export_report_data(report, format=format)

        return {"data": exported, "format": format}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"导出复盘报告失败: {str(e)}")
